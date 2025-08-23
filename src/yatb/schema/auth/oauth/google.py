from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import Request, Response
from pydantic_settings import SettingsConfigDict

from yatb.ebasemodelv2 import Admin, Public
from yatb.utils.log_helper import get_logger

from .base import OAuth

logger = get_logger("schema.auth.oauth.google")


class GoogleOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        classtype: Public[Literal["GoogleOAuth"]] = "GoogleOAuth"

        id: Admin[str]
        email: Admin[str]

        family_name: Admin[str | None] = None
        name: Admin[str | None] = None
        picture: Admin[str | None] = None
        given_name: Admin[str | None] = None
        verified_email: Admin[bool | None] = None

        def is_admin(self) -> bool:
            return (
                self.id in GoogleOAuth.auth_settings.ADMIN_IDS or self.email in GoogleOAuth.auth_settings.ADMIN_EMAILS
            )

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "id"

        def generate_username(self) -> str:
            # return self.given_name or self.name or self.email
            return self.email

    class Form(OAuth.Form):
        async def populate(self, req: Request, resp: Response) -> "GoogleOAuth.AuthModel":
            async with aiohttp.ClientSession() as session:
                oauth_token = await self.get_token(req, GoogleOAuth, session)
                user_data = await (
                    await session.get(
                        GoogleOAuth.auth_settings.API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")

                model = GoogleOAuth.AuthModel.model_validate(user_data)

                return model

    class AuthSettings(OAuth.OAuthSettings):
        ADMIN_IDS: list[str] = []  # noqa: RUF012
        ADMIN_EMAILS: list[str] = []  # noqa: RUF012
        ENDPOINT: str = "https://accounts.google.com/o/oauth2/v2/auth"
        TOKEN_ENDPOINT: str = "https://oauth2.googleapis.com/token"
        API_ENDPOINT: str = "https://www.googleapis.com/oauth2/v2/userinfo"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_GOOGLE_")

    scope: ClassVar = (
        "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile openid"
    )

    auth_settings: ClassVar[AuthSettings] = AuthSettings()
    router_params: ClassVar = {
        "path": "/google_callback",
        "name": "api_auth_google_callback",
        "methods": ["GET"],
    }
