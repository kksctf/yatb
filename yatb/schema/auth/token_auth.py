from collections.abc import Callable, Hashable
from typing import ClassVar, Literal, Self

from fastapi import Request, Response

from ...ebasemodelv2.types import Admin, Public
from ...utils.log_helper import get_logger
from .base import AuthBase

logger = get_logger("schema.auth")


class TokenAuth(AuthBase):
    FAKE: bool = True

    class AuthModel(AuthBase.AuthModel):
        __admin_only_fields__: ClassVar = {
            "username",
        }

        classtype: Public[Literal["AuthBase"]] = "AuthBase"

        username: Admin[str]

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
            raise Exception("No.")  # noqa: TRY002

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
