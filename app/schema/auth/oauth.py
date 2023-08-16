import datetime
import hmac
from typing import Callable, Dict, Hashable, List, Optional, Type, Literal
import aiohttp

from fastapi import HTTPException, Query, status, Request, Response
from fastapi.security import oauth2
from pydantic import BaseSettings, Extra, validator

from ...config import settings
from .. import EBaseModel
from . import AuthBase, logger


class OAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        classtype: Literal["OAuth"] = "OAuth"

    class Form(AuthBase.Form):
        code: str = Query(...)
        state: str = Query(...)

        async def get_token(self, req: Request, cls: Type["OAuth"], session: aiohttp.ClientSession):
            oauth_token = await (
                await session.post(
                    cls.auth_settings.OAUTH_TOKEN_ENDPOINT,
                    params={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": req.url_for(cls.router_params["name"]),
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

    class OAuthSettings(BaseSettings):
        OAUTH_ADMIN_IDS: List[int] = []
        OAUTH_CLIENT_ID: str = ""
        OAUTH_CLIENT_SECRET: str = ""
        OAUTH_ENDPOINT: str = ""
        OAUTH_TOKEN_ENDPOINT: str = ""
        OAUTH_API_ENDPOINT: str = ""

        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_OAUTH_"

    auth_settings = OAuthSettings()
    scope = ""
    router_params = {
        "path": "/oauth_callback",
        "name": "api_auth_oauth_callback",
        "methods": ["GET"],
    }

    @classmethod
    async def setup(cls) -> None:
        return await super().setup()

    @classmethod
    def generate_html(cls: Type["OAuth"], url_for: Callable) -> str:
        return (
            f"""<a href='{cls.auth_settings.OAUTH_ENDPOINT}?response_type=code&scope={cls.scope}&state=TEST_STATE&"""
            + f"""client_id={cls.auth_settings.OAUTH_CLIENT_ID}&"""
            + f"""redirect_uri={url_for(name=cls.router_params["name"])}'>Login using {cls.__name__}</a>"""
        )


class CTFTimeOAuth_Team(EBaseModel):
    __admin_only_fields__ = {
        "id",
        "name",
        "country",
        "logo",
    }
    id: int
    name: str
    country: Optional[str]
    logo: Optional[str]


class CTFTimeOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__ = {"team"}
        classtype: Literal["CTFTimeOAuth"] = "CTFTimeOAuth"

        team: CTFTimeOAuth_Team

        def is_admin(self) -> bool:
            return self.team.id in CTFTimeOAuth.auth_settings.OAUTH_ADMIN_IDS

        def get_uniq_field(self) -> int:
            return self.team.id

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
                return CTFTimeOAuth.AuthModel.parse_obj(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: List[int] = [32621]  # id of org team at ctftime. Default is for kks, change it ;)
        OAUTH_ENDPOINT: str = "https://oauth.ctftime.org/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://oauth.ctftime.org/token"
        OAUTH_API_ENDPOINT: str = "https://oauth.ctftime.org/user"

        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_CTFTIME_"

    auth_settings = AuthSettings()
    scope = "team:read"
    router_params = {
        "path": "/ctftime_callback",
        "name": "api_auth_ctftime_callback",
        "methods": ["GET"],
    }


class GithubOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__ = {
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
        name: Optional[str]
        email: Optional[str]
        url: str

        def is_admin(self) -> bool:
            return self.id in GithubOAuth.auth_settings.OAUTH_ADMIN_IDS

        def get_uniq_field(self) -> int:
            return self.id

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
                return GithubOAuth.AuthModel.parse_obj(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: List[int] = []
        OAUTH_ENDPOINT: str = "https://github.com/login/oauth/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://github.com/login/oauth/access_token"
        OAUTH_API_ENDPOINT: str = "https://api.github.com/user"

        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_GITHUB_"

    auth_settings = AuthSettings()
    scope = "user:email,user:read"
    router_params = {
        "path": "/github_callback",
        "name": "api_auth_github_callback",
        "methods": ["GET"],
    }


class DiscordOAuth(OAuth):
    class AuthModel(OAuth.AuthModel):
        __admin_only_fields__ = {
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

        def get_uniq_field(self) -> int:
            return self.id

        def generate_username(self) -> str:
            return self.username

    class Form(OAuth.Form):
        async def get_token(self, req: Request, cls: Type["OAuth"], session: aiohttp.ClientSession):
            oauth_token = await (
                await session.post(
                    cls.auth_settings.OAUTH_TOKEN_ENDPOINT,
                    data={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": req.url_for(cls.router_params["name"]),
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
                return DiscordOAuth.AuthModel.parse_obj(user_data)

    class AuthSettings(OAuth.OAuthSettings):
        OAUTH_ADMIN_IDS: List[int] = []
        OAUTH_ENDPOINT: str = "https://discord.com/api/oauth2/authorize"
        OAUTH_TOKEN_ENDPOINT: str = "https://discord.com/api/oauth2/token"
        OAUTH_API_ENDPOINT: str = "https://discord.com/api/users/@me"

        class Config(AuthBase.AuthSettings.BaseConfig):
            env_prefix = "AUTH_DISCORD_"

    auth_settings = AuthSettings()
    scope = "identify"
    router_params = {
        "path": "/discord_callback",
        "name": "api_auth_discord_callback",
        "methods": ["GET"],
    }
