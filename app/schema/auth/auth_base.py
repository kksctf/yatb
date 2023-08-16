from collections.abc import Callable, Hashable
from typing import ClassVar, Literal, Self, TypeAlias

from fastapi import Request, Response
from pydantic_settings import BaseSettings, SettingsConfigDict

from .. import EBaseModel

RouterParams: TypeAlias = dict[str, str | object]


class AuthBase:
    class AuthModel(EBaseModel):
        __public_fields__ = {"classtype"}

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
        model_config = SettingsConfigDict(
            env_file="yatb.env",
            env_file_encoding="utf-8",
        )

    auth_settings: ClassVar[AuthSettings] = AuthSettings()
    router_params: ClassVar[RouterParams] = {
        "path": "/base_handler",
        "name": "api_auth_base_handler",
        "methods": ["GET"],
    }

    @classmethod
    async def setup(cls: type[Self]) -> None:
        # router.add_api_route(
        #     f"{cls.handler_name}",
        # )
        return None

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        return """"""

    @classmethod
    def generate_script(cls: type[Self], url_for: Callable) -> str:
        return """"""
