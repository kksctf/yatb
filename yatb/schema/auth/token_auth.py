import hashlib
import hmac
import os
from collections.abc import Callable
from typing import ClassVar, Hashable, Literal, Self

from fastapi import HTTPException, Request, Response, status
from pydantic_settings import SettingsConfigDict

from ...config import settings
from ...utils.log_helper import get_logger
from ..ebasemodel import EBaseModel
from .auth_base import AuthBase

logger = get_logger("schema.auth")


class TokenAuth:
    FAKE: bool = True

    class AuthModel(AuthBase.AuthModel):
        __public_fields__ = {"classtype"}
        __admin_only_fields__: ClassVar = {
            "username",
        }

        classtype: Literal["AuthBase"] = "AuthBase"

        username: str

        def is_admin(self) -> bool:
            return True

        def get_uniq_field(self) -> Hashable:
            return getattr(self, self.get_uniq_field_name())

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "username"

        def generate_username(self) -> str:
            return self.username

    class Form(AuthBase.Form):
        async def populate(self, req: Request, resp: Response) -> "AuthBase.AuthModel":
            raise Exception("No.")

    class AuthSettings(AuthBase.AuthSettings):
        pass

    auth_settings: ClassVar[AuthSettings] = AuthSettings()

    router_params: ClassVar = {}

    @classmethod
    async def setup(cls: type[Self]) -> None:
        return None

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        return """"""

    @classmethod
    def generate_script(cls: type[Self], url_for: Callable) -> str:
        return """"""
