from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import HTTPException, Request, Response, status
from pydantic_settings import SettingsConfigDict

from yatb.ebasemodelv2 import Admin, Public
from yatb.utils.log_helper import get_logger

from ..base import RouterParams
from .base import OAuth

logger = get_logger("schema.auth.oauth.ctftime")


class DiscordOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        classtype: Public[Literal["DiscordOAuth"]] = "DiscordOAuth"

        id: Admin[int]
        username: Admin[str]
        discriminator: Admin[str]

        def is_admin(self) -> bool:
            return self.id in DiscordOAuth.auth_settings.ADMIN_IDS

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "id"

        def generate_username(self) -> str:
            return self.username

    class Form(OAuth.Form):
        async def get_token(self, req: Request, cls: type["OAuth"], session: aiohttp.ClientSession):
            oauth_token = await (
                await session.post(
                    str(cls.auth_settings.TOKEN_ENDPOINT),
                    data={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": str(req.url_for(cls.router_params["name"])),  # type: ignore
                        "client_id": cls.auth_settings.CLIENT_ID,
                        "client_secret": cls.auth_settings.CLIENT_SECRET,
                        "scope": DiscordOAuth.scope,
                    },
                    headers={"Accept": "application/json"},
                )
            ).json()
            logger.debug(f"oauth token data: {oauth_token}")
            if "access_token" not in oauth_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OAuth error",
                )
            return oauth_token

        async def populate(self, req: Request, resp: Response) -> "DiscordOAuth.AuthModel":
            async with aiohttp.ClientSession() as session:
                oauth_token = await self.get_token(req, DiscordOAuth, session)
                user_data = await (
                    await session.get(
                        DiscordOAuth.auth_settings.API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return DiscordOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        ADMIN_IDS: list[int] = []
        ENDPOINT: str = "https://discord.com/api/oauth2/authorize"
        TOKEN_ENDPOINT: str = "https://discord.com/api/oauth2/token"
        API_ENDPOINT: str = "https://discord.com/api/users/@me"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_DISCORD_")

    scope: ClassVar = "identify"
    auth_settings: ClassVar = AuthSettings()

    router_params: ClassVar[RouterParams] = {
        "path": "/discord_callback",
        "name": "api_auth_discord_callback",
        "methods": ["GET"],
    }
