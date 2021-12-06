import datetime
import hmac
import logging
from typing import Callable, Hashable, List, Optional, Type, Union

import aiohttp
from fastapi import HTTPException, Query, Request, Response, status, APIRouter
from pydantic import BaseSettings, Extra, validator

from ...config import settings
from .. import EBaseModel, Literal

logger = logging.getLogger("yatb.schema.auth")


class AuthBase(object):
    class AuthModel(EBaseModel):
        classtype: Literal["AuthBase"] = "AuthBase"

        def is_admin(self) -> bool:
            # raise NotImplementedError("AuthBase.is_admin not implemented")
            return False

        def get_uniq_field(self) -> Hashable:
            return None

        def generate_username(self) -> str:
            # raise NotImplementedError("AuthBase.generate_username not implemented")
            return "undefined"

    class Form(EBaseModel):
        async def populate(self, req: Request, resp: Response) -> "AuthBase.AuthModel":
            # raise NotImplementedError("AuthBase.Form.populate not implemented")
            return AuthBase.AuthModel()

    class AuthSettings(BaseSettings):
        class BaseConfig:
            env_file = "yatb.env"
            env_file_encoding = "utf-8"

    auth_settings = AuthSettings()
    router_params = {
        "path": "/base_handler",
        "name": "api_auth_base_handler",
        "methods": ["GET"],
    }

    @classmethod
    async def setup(cls) -> None:
        # router.add_api_route(
        #     f"{cls.handler_name}",
        # )
        return None

    @classmethod
    def generate_html(cls: Type["AuthBase"], url_for: Callable) -> str:
        return """"""

    @classmethod
    def generate_script(cls: Type["AuthBase"], url_for: Callable) -> str:
        return """"""


from .oauth import CTFTimeOAuth, GithubOAuth, DiscordOAuth, OAuth  # noqa
from .simple import SimpleAuth  # noqa
from .tg import TelegramAuth  # noqa

# commented out due to 'AuthBase.AuthModel' is a base class, and nothing in childs would be used
TYPING_AUTH = Union[
    AuthBase.AuthModel,
    # SimpleAuth.AuthModel,
    # TelegramAuth.AuthModel,
    # OAuth.AuthModel,
    # CTFTimeOAuth.AuthModel,
]
ENABLED_AUTH_WAYS = [
    CTFTimeOAuth,
    SimpleAuth,
    TelegramAuth,
    GithubOAuth,
    DiscordOAuth,
]
