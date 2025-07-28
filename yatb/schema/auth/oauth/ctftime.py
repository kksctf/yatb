from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import Request, Response
from pydantic_settings import SettingsConfigDict

from ....ebasemodelv2 import Admin, EBaseModelV2, Public
from ....utils.log_helper import get_logger

from ..base import RouterParams
from .base import OAuth

logger = get_logger("schema.auth.oauth.ctftime")


class CTFTimeOAuthTeam(EBaseModelV2):
    id: Admin[int]
    name: Admin[str]
    country: Admin[str | None]
    logo: Admin[str | None]


class CTFTimeOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        classtype: Public[Literal["CTFTimeOAuth"]] = "CTFTimeOAuth"

        team: Admin[CTFTimeOAuthTeam]

        def is_admin(self) -> bool:
            return self.team.id in CTFTimeOAuth.auth_settings.ADMIN_IDS

        def get_uniq_field(self) -> int:
            return self.team.id

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "team.id"

        def generate_username(self) -> str:
            return self.team.name

    class Form(OAuth.Form):
        async def populate(self, req: Request, resp: Response) -> "CTFTimeOAuth.AuthModel":
            async with aiohttp.ClientSession() as session:
                oauth_token = await self.get_token(req, CTFTimeOAuth, session)
                user_data = await (
                    await session.get(
                        CTFTimeOAuth.auth_settings.API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return CTFTimeOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        ADMIN_IDS: list[int] = [32621]  # id of org team at ctftime. Default is for kks, change it ;)
        ENDPOINT: str = "https://oauth.ctftime.org/authorize"
        TOKEN_ENDPOINT: str = "https://oauth.ctftime.org/token"
        API_ENDPOINT: str = "https://oauth.ctftime.org/user"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_CTFTIME_")

    scope: ClassVar = "team:read"

    auth_settings: ClassVar = AuthSettings()
    router_params: ClassVar[RouterParams] = {
        "path": "/ctftime_callback",
        "name": "api_auth_ctftime_callback",
        "methods": ["GET"],
    }
