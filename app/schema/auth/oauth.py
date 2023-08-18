from collections.abc import Callable
from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import HTTPException, Query, Request, Response, status
from pydantic_settings import SettingsConfigDict

from ...utils.log_helper import get_logger
from ..ebasemodel import EBaseModel
from .auth_base import AuthBase, RouterParams

logger = get_logger("schema.auth")


class OAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        classtype: Literal["OAuth"] = "OAuth"

    class Form(AuthBase.Form):
        code: str = Query(...)
        state: str = Query(...)

        async def get_token(self, req: Request, cls: type["OAuth"], session: aiohttp.ClientSession) -> dict:
            oauth_token = await (
                await session.post(
                    cls.auth_settings.OAUTH_TOKEN_ENDPOINT,
                    params={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": req.url_for(cls.router_params["name"]),  # type: ignore
                        "client_id": cls.auth_settings.OAUTH_CLIENT_ID,
                        "client_secret": cls.auth_settings.OAUTH_CLIENT_SECRET,
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

        async def populate(self, req: Request, resp: Response) -> "OAuth.AuthModel":
            # raise NotImplementedError("OAuth.Form.populate not implemented")
            return OAuth.AuthModel()

    class OAuthSettings(AuthBase.AuthSettings):
        OAUTH_ADMIN_IDS: list[int] = []
        OAUTH_CLIENT_ID: str = ""
        OAUTH_CLIENT_SECRET: str = ""
        OAUTH_ENDPOINT: str = ""
        OAUTH_TOKEN_ENDPOINT: str = ""
        OAUTH_API_ENDPOINT: str = ""

        model_config = SettingsConfigDict(AuthBase.AuthSettings.model_config, env_prefix="AUTH_OAUTH_")

    scope: ClassVar[str] = ""

    auth_settings: ClassVar[OAuthSettings] = OAuthSettings()
    router_params: ClassVar = {
        "path": "/oauth_callback",
        "name": "api_auth_oauth_callback",
        "methods": ["GET"],
    }

    @classmethod
    async def setup(cls) -> None:
        return await super().setup()

    @classmethod
    def generate_html(cls: type[Self], url_for: Callable) -> str:
        return (
            f"""<a href='{cls.auth_settings.OAUTH_ENDPOINT}?response_type=code&scope={cls.scope}&state=TEST_STATE&"""
            f"""client_id={cls.auth_settings.OAUTH_CLIENT_ID}&"""
            f"""redirect_uri={url_for(cls.router_params["name"])}'>Login using {cls.__name__}</a>"""
        )


class CTFTimeOAuth_Team(EBaseModel):
    __admin_only_fields__: ClassVar = {
        "id",
        "name",
        "country",
        "logo",
    }

    id: int
    name: str
    country: str | None
    logo: str | None


class CTFTimeOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__: ClassVar = {"team"}
        classtype: Literal["CTFTimeOAuth"] = "CTFTimeOAuth"

        team: CTFTimeOAuth_Team

        def is_admin(self) -> bool:
            return self.team.id in CTFTimeOAuth.auth_settings.OAUTH_ADMIN_IDS

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
                        CTFTimeOAuth.auth_settings.OAUTH_API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return CTFTimeOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: list[int] = [32621]  # id of org team at ctftime. Default is for kks, change it ;)
        OAUTH_ENDPOINT: str = "https://oauth.ctftime.org/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://oauth.ctftime.org/token"
        OAUTH_API_ENDPOINT: str = "https://oauth.ctftime.org/user"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_CTFTIME_")

    scope: ClassVar = "team:read"

    auth_settings: ClassVar = AuthSettings()
    router_params: ClassVar[RouterParams] = {
        "path": "/ctftime_callback",
        "name": "api_auth_ctftime_callback",
        "methods": ["GET"],
    }


class GithubOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__: ClassVar = {
            "id",
            "login",
            "avatar_url",
            "name",
            "email",
            "url",
        }
        classtype: Literal["GithubOAuth"] = "GithubOAuth"

        id: int
        login: str
        avatar_url: str
        name: str | None
        email: str | None
        url: str

        def is_admin(self) -> bool:
            return self.id in GithubOAuth.auth_settings.OAUTH_ADMIN_IDS

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
                        GithubOAuth.auth_settings.OAUTH_API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return GithubOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: list[int] = []
        OAUTH_ENDPOINT: str = "https://github.com/login/oauth/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://github.com/login/oauth/access_token"
        OAUTH_API_ENDPOINT: str = "https://api.github.com/user"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_GITHUB_")

    scope: ClassVar = "user:email,user:read"

    auth_settings: ClassVar = AuthSettings()
    router_params: ClassVar = {
        "path": "/github_callback",
        "name": "api_auth_github_callback",
        "methods": ["GET"],
    }


class DiscordOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__: ClassVar = {
            "id",
            "username",
            "discriminator",
        }
        classtype: Literal["DiscordOAuth"] = "DiscordOAuth"

        id: int
        username: str
        discriminator: str

        def is_admin(self) -> bool:
            return self.id in DiscordOAuth.auth_settings.OAUTH_ADMIN_IDS

        @classmethod
        def get_uniq_field_name(cls: type[Self]) -> str:
            return "id"

        def generate_username(self) -> str:
            return self.username

    class Form(OAuth.Form):
        async def get_token(self, req: Request, cls: type["OAuth"], session: aiohttp.ClientSession):
            oauth_token = await (
                await session.post(
                    cls.auth_settings.OAUTH_TOKEN_ENDPOINT,
                    data={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": req.url_for(cls.router_params["name"]),  # type: ignore
                        "client_id": cls.auth_settings.OAUTH_CLIENT_ID,
                        "client_secret": cls.auth_settings.OAUTH_CLIENT_SECRET,
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
                        DiscordOAuth.auth_settings.OAUTH_API_ENDPOINT,
                        headers={"Authorization": f"Bearer {oauth_token['access_token']}"},
                    )
                ).json()
                logger.debug(f"User api token data: {user_data}")
                return DiscordOAuth.AuthModel.model_validate(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: list[int] = []
        OAUTH_ENDPOINT: str = "https://discord.com/api/oauth2/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://discord.com/api/oauth2/token"
        OAUTH_API_ENDPOINT: str = "https://discord.com/api/users/@me"

        model_config = SettingsConfigDict(OAuth.OAuthSettings.model_config, env_prefix="AUTH_DISCORD_")

    scope: ClassVar = "identify"
    auth_settings: ClassVar = AuthSettings()

    router_params: ClassVar[RouterParams] = {
        "path": "/discord_callback",
        "name": "api_auth_discord_callback",
        "methods": ["GET"],
    }
