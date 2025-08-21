from collections.abc import Callable
from typing import ClassVar, Literal, Self

import aiohttp
from fastapi import HTTPException, Query, Request, Response, status
from pydantic_settings import SettingsConfigDict

from yatb.ebasemodelv2 import Public
from yatb.utils.log_helper import get_logger

from ..base import AuthBase

logger = get_logger("schema.auth.oauth")


class OAuth(AuthBase):
    class AuthModel(AuthBase.AuthModel):
        classtype: Public[Literal["OAuth"]] = "OAuth"

    class Form(AuthBase.Form):
        code: str = Query(...)
        state: str = Query(...)

        async def get_token(self, req: Request, cls: type["OAuth"], session: aiohttp.ClientSession) -> dict:
            oauth_token = await (
                await session.post(
                    str(cls.auth_settings.TOKEN_ENDPOINT),
                    params={
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": str(req.url_for(cls.router_params["name"])),  # pyright: ignore[reportArgumentType]
                        "client_id": cls.auth_settings.CLIENT_ID,
                        "client_secret": cls.auth_settings.CLIENT_SECRET,
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
        ADMIN_IDS: list[int] = []
        CLIENT_ID: str = ""
        CLIENT_SECRET: str = ""
        ENDPOINT: str = ""
        TOKEN_ENDPOINT: str = ""
        API_ENDPOINT: str = ""

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
            f"""<a href='{cls.auth_settings.ENDPOINT}?response_type=code&scope={cls.scope}&state=TEST_STATE&"""
            f"""client_id={cls.auth_settings.CLIENT_ID}&"""
            f"""redirect_uri={url_for(cls.router_params["name"])}'>Login using {cls.__name__}</a>"""
        )
