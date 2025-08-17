import datetime
import hashlib
import hmac
from collections.abc import Callable
from typing import ClassVar, Literal, Self

from fastapi import HTTPException, Query, Request, Response, status
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from ...ebasemodelv2.types import Admin, Public
from ...utils.log_helper import get_logger
from .base import AuthBase

logger = get_logger("schema.auth")


class TelegramAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        classtype: Public[Literal["TelegramAuth"]] = "TelegramAuth"

        tg_id: Admin[int]
        tg_username: Admin[str | None] = None
        tg_first_name: Admin[str]
        tg_last_name: Admin[str | None] = None

        def is_admin(self) -> bool:
            is_admin: bool = False

            if self.tg_username and self.tg_username.lower() in TelegramAuth.auth_settings.ADMIN_USERNAMES:
                is_admin = True
            if self.tg_id in TelegramAuth.auth_settings.ADMIN_UIDS:
                is_admin = True

            return is_admin

        # @model_validator(mode="after")
        # def disallow_not_admins(self) -> Self:
        #     if not self.is_admin():
        #         raise HTTPException(
        #             status_code=status.HTTP_403_FORBIDDEN,
        #             detail="This only for admins",
        #         )

        #     return self

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "tg_id"

        def generate_username(self) -> str:
            return self.tg_first_name + (" " + self.tg_last_name if self.tg_last_name else "")

    class Form(AuthBase.Form):
        id: int = Query(...)

        first_name: str = Query(...)

        last_name: str | None = Query(None)
        username: str | None = Query(None)
        photo_url: str | None = Query(None)

        auth_date: int = Query(...)

        hash: str = Query(...)

        @field_validator("auth_date", mode="after")
        @classmethod
        def check_date(cls: type[Self], date: int) -> int:
            rdate = datetime.datetime.fromtimestamp(date, tz=datetime.UTC)

            if (datetime.datetime.now(tz=datetime.UTC) - rdate).total_seconds() > 60 * 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bad date",
                )

            return date

        @model_validator(mode="after")
        def check_hash(self) -> Self:  # noqa: E0213, N805
            bot_sha = hashlib.sha256(TelegramAuth.auth_settings.BOT_TOKEN.encode()).digest()

            hash_check_string = "\n".join(
                f"{i}={attr_value}"
                for i in sorted(
                    [
                        "id",
                        "first_name",
                        "last_name",
                        "username",
                        "photo_url",
                        "auth_date",
                    ],
                )
                if (attr_value := getattr(self, i)) is not None
            )
            hash_check = hmac.new(bot_sha, hash_check_string.encode(), digestmod="sha256")
            if hash_check.hexdigest() != self.hash:
                logger.warning(f"hash check failed for {hash_check.hexdigest()} != {self.hash}, {self}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bad hash",
                )

            return self

        async def populate(self, req: Request, resp: Response) -> "TelegramAuth.AuthModel":
            return TelegramAuth.AuthModel(
                tg_id=self.id,
                tg_first_name=self.first_name,
                tg_last_name=self.last_name,
                tg_username=self.username,
            )

    class AuthSettings(AuthBase.AuthSettings):
        BOT_TOKEN: str = ""
        BOT_USERNAME: str = ""

        ADMIN_USERNAMES: list[str] = []
        ADMIN_UIDS: list[int] = []

        model_config = SettingsConfigDict(AuthBase.AuthSettings.model_config, env_prefix="AUTH_TG_")

    auth_settings: ClassVar[AuthSettings] = AuthSettings()
    router_params: ClassVar = {
        "path": "/tg_callback",
        "name": "api_auth_tg_callback",
        "methods": ["GET"],
    }

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        return f"""
        <script async src="https://telegram.org/js/telegram-widget.js?15"
        data-telegram-login="{cls.auth_settings.BOT_USERNAME}"
        data-size="large" data-userpic="true" data-auth-url="{url_for(cls.router_params["name"])}"
        data-request-access="write"></script>
        """

    @classmethod
    def generate_script(cls: type[Self], url_for: Callable) -> str:
        return """
        (function() {
            // $('#auth_button_TelegramAuth').css('display', 'none');

            var secretCode = [73, 68, 68, 81, 68];
            var inputSequence = [];

            $(document).keydown(function(e) {
                // Add the pressed key's code to the sequence
                inputSequence.push(e.which);

                // Keep the sequence length equal to the secret code length
                if (inputSequence.length > secretCode.length) {
                    inputSequence.shift();
                }

                // Check if the sequence matches
                if (JSON.stringify(inputSequence) === JSON.stringify(secretCode)) {
                    // Remove display: none from all elements with inline style display:none
                    $('#auth_button_TelegramAuth').css('display', '');
                    inputSequence = [];
                }
            });
        })();
        """
