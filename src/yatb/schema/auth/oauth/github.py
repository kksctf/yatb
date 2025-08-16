from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import Request, Response
from pydantic_settings import SettingsConfigDict

from yatb.ebasemodelv2 import Admin, Public
from yatb.utils.log_helper import get_logger

from .base import OAuth

logger = get_logger("schema.auth.oauth.ctftime")


class GithubOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        classtype: Public[Literal["GithubOAuth"]] = "GithubOAuth"

        id: Admin[int]
        login: Admin[str]
        avatar_url: Admin[str]
        name: Admin[str | None]
        email: Admin[str | None]
        url: Admin[str]

        def is_admin(self) -> bool:
            return self.id in GithubOAuth.auth_settings.ADMIN_IDS

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "id"

        def generate_username(self) -> str:
            return self.name or self.login

    class Form(OAuth.Form):
        async def populate(self, req: Request, resp: Response) -> "GithubOAuth.AuthModel":
            async with aiohttp.ClientSession() as session:
                oauth_token = await self.get_token(req, GithubOAuth, session)
                user_data = await (
                    await session.get(
                        GithubOAuth.auth_settings.API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return GithubOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        ADMIN_IDS: list[int] = []
        ENDPOINT: str = "https://github.com/login/oauth/authorize"
        TOKEN_ENDPOINT: str = "https://github.com/login/oauth/access_token"
        API_ENDPOINT: str = "https://api.github.com/user"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_GITHUB_")

    scope: ClassVar = "user:email,user:read"

    auth_settings: ClassVar = AuthSettings()
    router_params: ClassVar = {
        "path": "/github_callback",
        "name": "api_auth_github_callback",
        "methods": ["GET"],
    }
