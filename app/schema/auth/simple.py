import hashlib
import hmac
import os
from collections.abc import Callable
from typing import ClassVar, Literal, Self

from fastapi import HTTPException, Request, Response, status
from pydantic_settings import SettingsConfigDict

from ...config import settings
from ...utils.log_helper import get_logger
from ..ebasemodel import EBaseModel
from .auth_base import AuthBase

logger = get_logger("schema.auth")


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or os.urandom(32)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt, pw_hash


def check_password(salt: bytes, pw_hash: bytes, password: str) -> bool:
    return hmac.compare_digest(pw_hash, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000))


class SimpleAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        __admin_only_fields__: ClassVar = {
            "username",
        }
        __private_fields__: ClassVar = {
            "password_hash",
        }
        classtype: Literal["SimpleAuth"] = "SimpleAuth"

        username: str
        password_hash: tuple[bytes, bytes]

        def is_admin(self) -> bool:
            if settings.DEBUG and self.username == SimpleAuth.auth_settings.DEBUG_USERNAME:
                return True
            return False

        def get_uniq_field(self) -> str:
            return self.username

        def generate_username(self) -> str:
            return self.username

    class Form(AuthBase.Form):
        class _Internal(EBaseModel):
            username: str
            password: str

        internal: _Internal

        def check_password(self, model: "SimpleAuth.AuthModel") -> bool:
            return check_password(model.password_hash[0], model.password_hash[1], self.internal.password)

        def check_valid(self) -> bool:
            if settings.DEBUG:
                return True
            if (
                len(self.internal.username) < SimpleAuth.auth_settings.MIN_USERNAME_LEN
                or len(self.internal.username) > SimpleAuth.auth_settings.MAX_USERNAME_LEN
            ):
                return False
            if len(self.internal.password) < SimpleAuth.auth_settings.MIN_PASSWORD_LEN:
                return False
            return True

        async def populate(self, req: Request, resp: Response) -> "SimpleAuth.AuthModel":
            if not self.check_valid():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid data",
                )
            password_hash = hash_password(self.internal.password)
            return SimpleAuth.AuthModel(username=self.internal.username, password_hash=password_hash)

    class AuthSettings(AuthBase.AuthSettings):
        DEBUG_USERNAME: str = "Rubikoid"

        MIN_PASSWORD_LEN: int = 8
        MIN_USERNAME_LEN: int = 2
        MAX_USERNAME_LEN: int = 32

        model_config = SettingsConfigDict(AuthBase.AuthSettings.model_config, env_prefix="AUTH_SIMPLE_")

    auth_settings: ClassVar[AuthSettings] = AuthSettings()
    router_params: ClassVar = {}

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        if not settings.DEBUG:
            login_resrictions = "minlength='2' maxlength='32'"
            passw_resrictions = "minlength='8'"
        else:
            login_resrictions = ""
            passw_resrictions = ""
        return f"""
        Login:<br>
        <form class="login_form">
            <input type="text" name="username" value="" placeholder="username" {login_resrictions}>
            <input type="password" name="password" value="" placeholder="password" {passw_resrictions}>
            <button class="w-100 btn btn-warning mt-1" type="submit">Login</button>
        </form>

        Register:<br>
        <form class="register_form">
            <input type="text" name="username" value="" placeholder="username" {login_resrictions}>
            <input type="password" name="password" value="" placeholder="password" {passw_resrictions}>
            <button class="w-100 btn btn-warning mt-1" type="submit">Register</button>
        </form>
        """

    @classmethod
    def generate_script(cls: type[Self], url_for: Callable) -> str:
        return """
        $(".login_form").submit(function(event) {
            event.preventDefault();
            req(api_list["api_auth_simple_login"], { data: getFormData(this), })
                .then(get_json)
                .then(redirect, nok_toast_generator("login"))
        });

        $(".register_form").submit(function(event) {
            event.preventDefault();
            req(api_list["api_auth_simple_register"], { data: getFormData(this), })
                .then(get_json)
                .then(redirect, nok_toast_generator("register"))
        });
        """
