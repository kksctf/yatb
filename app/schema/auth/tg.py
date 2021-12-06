import datetime
import hashlib
import hmac
from typing import Callable, List, Optional, Type
import aiohttp

from fastapi import HTTPException, Query, status, Request, Response
from pydantic import BaseSettings, Extra, validator

from ...config import settings
from .. import EBaseModel, Literal
from . import AuthBase, logger


class TelegramAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        __admin_only_fields__ = {
            "tg_id",
            "tg_username",
            "tg_first_name",
            "tg_last_name",
        }
        classtype: Literal["TelegramAuth"] = "TelegramAuth"

        tg_id: int
        tg_username: Optional[str] = None
        tg_first_name: str
        tg_last_name: Optional[str] = None

        def is_admin(self) -> bool:
            is_admin: bool = False
            if self.tg_username and self.tg_username.lower() in TelegramAuth.auth_settings.ADMIN_USERNAMES:
                is_admin = True
            if self.tg_id in TelegramAuth.auth_settings.ADMIN_UIDS:
                is_admin = True
            return is_admin

        def get_uniq_field(self) -> int:
            return self.tg_id

        def generate_username(self) -> str:
            return self.tg_first_name + (" " + self.tg_last_name if self.tg_last_name else "")

    class Form(AuthBase.Form):
        id: int = Query(...)

        first_name: str = Query(...)

        last_name: Optional[str] = Query(None)
        username: Optional[str] = Query(None)
        photo_url: Optional[str] = Query(None)

        auth_date: int = Query(...)

        hash: str = Query(...)

        @validator("auth_date")
        def check_date(cls, date, values, **kwargs):
            rdate = datetime.datetime.fromtimestamp(date)
            if (datetime.datetime.now() - rdate).total_seconds() > 60 * 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bad date",
                )
            return date

        @validator("hash")
        def check_hash(cls, hash, values, **kwargs):
            bot_sha = hashlib.sha256(TelegramAuth.auth_settings.BOT_TOKEN.encode()).digest()

            hash_check_string = "\n".join(f"{i}={values[i]}" for i in sorted(values.keys()) if values[i] is not None)
            hash_check = hmac.new(bot_sha, hash_check_string.encode(), digestmod="sha256")
            if hash_check.hexdigest() != hash:
                logger.warning(f"hash check failed for {hash_check.hexdigest()} != {hash}, {values}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bad hash",
                )
            return hash

        async def populate(self, req: Request, resp: Response) -> "TelegramAuth.AuthModel":
            return TelegramAuth.AuthModel(
                tg_id=self.id,
                tg_first_name=self.first_name,
                tg_last_name=self.last_name,
                tg_username=self.username,
            )

    class AuthSettings(BaseSettings):
        BOT_TOKEN: str = ""
        BOT_USERNAME: str = ""

        ADMIN_USERNAMES: List[str] = []
        ADMIN_UIDS: List[int] = []

        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_TG_"

    auth_settings = AuthSettings()
    router_params = {
        "path": "/tg_callback",
        "name": "api_auth_tg_callback",
        "methods": ["GET"],
    }

    @classmethod
    def generate_html(cls: Type["TelegramAuth"], url_for: Callable) -> str:
        return f"""
        <script async src="https://telegram.org/js/telegram-widget.js?15"
        data-telegram-login="{ cls.auth_settings.BOT_USERNAME }"
        data-size="large" data-userpic="true" data-auth-url="{ url_for(cls.router_params["name"]) }"
        data-request-access="write"></script>
        """

    @classmethod
    def generate_script(cls: Type["TelegramAuth"], url_for: Callable) -> str:
        return """"""
