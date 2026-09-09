import hashlib
import hmac
import os
from collections.abc import Callable
from typing import ClassVar, Literal, Self

from fastapi import HTTPException, Request, Response, status
from pydantic_settings import SettingsConfigDict

from yatb.config import settings
from yatb.ebasemodelv2.types import Admin, Private, Public
from yatb.utils.log_helper import get_logger

from .base import AuthBase

logger = get_logger("schema.auth")


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or os.urandom(32)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt, pw_hash


def check_password(salt: bytes, pw_hash: bytes, password: str) -> bool:
    return hmac.compare_digest(pw_hash, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000))


class SimpleAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        classtype: Public[Literal["SimpleAuth"]] = "SimpleAuth"

        username: Admin[str]
        password_hash: Private[tuple[bytes, bytes]]

        def is_admin(self) -> bool:
            if settings.DEBUG and self.username == SimpleAuth.auth_settings.DEBUG_USERNAME:
                return True
            return False

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "username"

        def generate_username(self) -> str:
            return self.username

    class Form(AuthBase.Form):
        username: str
        password: str

        def check_password(self, model: "SimpleAuth.AuthModel") -> bool:
            return check_password(model.password_hash[0], model.password_hash[1], self.password)

        def check_valid(self) -> bool:
            if settings.DEBUG:
                return True

            if (
                len(self.username) < SimpleAuth.auth_settings.MIN_USERNAME_LEN
                or len(self.username) > SimpleAuth.auth_settings.MAX_USERNAME_LEN
            ):
                return False

            if len(self.password) < SimpleAuth.auth_settings.MIN_PASSWORD_LEN:
                return False

            return True

        async def populate(self, req: Request, resp: Response) -> "SimpleAuth.AuthModel":
            if not self.check_valid():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid data",
                )
            password_hash = hash_password(self.password)
            return SimpleAuth.AuthModel(username=self.username, password_hash=password_hash)

    class AuthSettings(AuthBase.AuthSettings):
        DEBUG_USERNAME: str = "Rubikoid"

        MIN_PASSWORD_LEN: int = 8
        MIN_USERNAME_LEN: int = 2
        MAX_USERNAME_LEN: int = 64

        model_config = SettingsConfigDict(AuthBase.AuthSettings.model_config, env_prefix="AUTH_SIMPLE_")

    auth_settings: ClassVar[AuthSettings] = AuthSettings()
    router_params: ClassVar = {}

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        if not settings.DEBUG:
            login_resrictions = (
                f"minlength='{cls.auth_settings.MIN_USERNAME_LEN}' "
                f"maxlength='{cls.auth_settings.MAX_USERNAME_LEN}' "
                "required"
            )
            passw_resrictions = f"required minlength='{cls.auth_settings.MIN_PASSWORD_LEN}'"
        else:
            login_resrictions = ""
            passw_resrictions = ""

        debug_form = f"""
        <details class="box my-4" open>
          <summary class="has-text-weight-semibold">Debug helpers</summary>
          <div class="mt-3 has-text-left">
            <div class="field is-grouped">
              <p class="control">
                <button type="button" class="button is-small is-warning js-debug-preset"
                        data-username="{cls.auth_settings.DEBUG_USERNAME}" data-password="123">
                  Admin ({cls.auth_settings.DEBUG_USERNAME})
                </button>
              </p>
              <p class="control">
                <button type="button" class="button is-small is-success js-debug-preset"
                        data-username="" data-password="12321">
                  Generic per-browser user
                </button>
              </p>
            </div>

            <form id="debug-auth-form"
                  action="{url_for("api_auth_simple_login")}"
                  method="post">
              <div class="field">
                <label class="label" for="debug-auth-username">Username</label>
                <div class="control">
                  <input id="debug-auth-username" class="input" name="username"
                         value="{cls.auth_settings.DEBUG_USERNAME}" autocomplete="off">
                </div>
              </div>

              <div class="field">
                <label class="label" for="debug-auth-password">Password</label>
                <div class="control">
                  <input id="debug-auth-password" class="input" type="text" name="password"
                         value="123" autocomplete="off">
                </div>
              </div>

              <div class="field is-grouped">
                <p class="control">
                  <button type="submit" class="button is-warning"
                          formaction="{url_for("api_auth_simple_login")}"
                          hx-post="{url_for("api_auth_simple_login")}"
                          hx-include="closest form"
                          hx-swap="none">
                    Login
                  </button>
                </p>
                <p class="control">
                  <button type="submit" class="button is-warning"
                          formaction="{url_for("api_auth_simple_register")}"
                          hx-post="{url_for("api_auth_simple_register")}"
                          hx-include="closest form"
                          hx-swap="none">
                    Register
                  </button>
                </p>
              </div>
            </form>

          </div>
        </details>
        """

        return f"""
        Login:<br>

        <form
            action="{url_for("api_auth_simple_login")}"
            method="post"
            hx-post="{url_for("api_auth_simple_login")}"
            hx-swap="none">
            <input type="text" name="username" value="" placeholder="username" {login_resrictions}>
            <input type="password" name="password" value="" placeholder="password" {passw_resrictions}>
            <button class="button is-warning is-fullwidth">
                Login
            </button>
        </form>

        Register:<br>
        <form
            action="{url_for("api_auth_simple_register")}"
            method="post"
            hx-post="{url_for("api_auth_simple_register")}"
            hx-swap="none">
            <input type="text" name="username" value="" placeholder="username" {login_resrictions}>
            <input type="password" name="password" value="" placeholder="password" {passw_resrictions}>
            <button class="button is-warning is-fullwidth">
                Register
            </button>
        </form>
        """ + (debug_form if settings.DEBUG else "")

    @classmethod
    def generate_script(cls: type[Self], url_for: Callable) -> str:
        debug_script = """
          (function () {
            var form = document.getElementById("debug-auth-form");
            if (!form) return;

            function cyrb53(str, seed = 0) {
              let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
              for (let i = 0, ch; i < str.length; i++) {
                ch = str.charCodeAt(i);
                h1 = Math.imul(h1 ^ ch, 2654435761);
                h2 = Math.imul(h2 ^ ch, 1597334677);
              }
              h1 ^= h1 >>> 16; h1 = Math.imul(h1, 2246822507);
              h1 ^= h1 >>> 13; h1 = Math.imul(h1, 3266489909);
              h2 ^= h2 >>> 16; h2 = Math.imul(h2, 2246822507);
              h2 ^= h2 >>> 13; h2 = Math.imul(h2, 3266489909);
              return 4294967296 * (2097151 & h2) + (h1 >>> 0);
            }
            function generateToken() {
              const data = `${screen.width}.${screen.height}.${navigator.userAgent}`;
              return `user${cyrb53(data)}`;
            }

            document.querySelectorAll(".js-debug-preset").forEach(function (el) {
              el.addEventListener("click", function () {
                form.username.value = el.dataset.username || generateToken();
                form.password.value = el.dataset.password;
              });
            });
          })();
        """
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
        """ + (debug_script if settings.DEBUG else "")
