import datetime
import hashlib
import hmac
import os
from typing import Callable, Hashable, List, Optional, Tuple, Type

import aiohttp
from fastapi import Body, HTTPException, Query, Request, Response, status
from pydantic import BaseSettings, Extra, validator

from ...config import settings
from .. import EBaseModel, Literal
from . import AuthBase, logger


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    salt = salt or os.urandom(32)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt, pw_hash


def check_password(salt: bytes, pw_hash: bytes, password: str) -> bool:
    return hmac.compare_digest(pw_hash, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000))


class SimpleAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        __admin_only_fields__ = {
            "username",
            "password_hash",
        }
        classtype: Literal["SimpleAuth"] = "SimpleAuth"

        username: str
        password_hash: Tuple[bytes, bytes]

        def is_admin(self) -> bool:
            if settings.DEBUG and self.username == "Rubikoid":
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

        def get_hashed_password(self, salt: Optional[bytes] = None):
            return hash_password(self.internal.password, salt)

        async def populate(self, req: Request, resp: Response) -> "SimpleAuth.AuthModel":
            password_hash = self.get_hashed_password()
            return SimpleAuth.AuthModel(username=self.internal.username, password_hash=password_hash)

    class AuthSettings(BaseSettings):
        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_SIMPLE_"

    auth_settings = AuthSettings()
    router_params = {}

    @classmethod
    def generate_html(cls: Type["SimpleAuth"], url_for: Callable) -> str:
        return """
        Login:<br>
        <form class="login_form">
            <input type="text" name="username" value="" placeholder="team name">
            <input type="password" name="password" value="" placeholder="password">
            <button class="w-100 btn btn-warning mt-1" type="submit">Login</button>
        </form>

        Register:<br>
        <form class="register_form">
            <input type="text" name="username" value="" placeholder="team name">
            <input type="password" name="password" value="" placeholder="password">
            <button class="w-100 btn btn-warning mt-1" type="submit">Register</button>
        </form>
        """

    @classmethod
    def generate_script(cls: Type["SimpleAuth"], url_for: Callable) -> str:
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