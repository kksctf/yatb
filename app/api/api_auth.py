import uuid
from datetime import timedelta
from typing import List, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.responses import RedirectResponse

from .. import auth, db, schema
from ..config import settings
from ..utils import metrics
from . import logger

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# =============== ONLY DEBUG ===============


@router.post("/login")
async def api_auth_simple_login(resp: Response, form_data: schema.UserForm):
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No.",
        )
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


@router.post("/register")
async def api_auth_simple_register(resp: Response, form_data: schema.UserForm):
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No.",
        )
    if await db.check_user(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Username exists",
        )
    user = await db.insert_user(form_data.username, form_data.password)

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


# =============== ONLY DEBUG ===============


@router.get("/oauth_callback")
async def api_oauth_callback(req: Request, resp: Response, code: str, state: str):
    async with aiohttp.ClientSession() as session:
        oauth_token = await (
            await session.post(
                settings.OAUTH_TOKEN_ENDPOINT,
                params={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": req.url_for("api_oauth_callback"),
                    "client_id": settings.OAUTH_CLIENT_ID,
                    "client_secret": settings.OAUTH_CLIENT_SECRET,
                },
            )
        ).json()
        logger.debug(f"oauth token data: {oauth_token}")
        if "access_token" not in oauth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CTFTime error",
            )

        user_data = await (await session.get(settings.OAUTH_API_ENDPOINT, headers={"Authorization": f"Bearer {oauth_token['access_token']}"})).json()
        logger.debug(f"User api token data: {user_data}")
        if "team" not in user_data or "id" not in user_data["team"] or "name" not in user_data["team"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CTFTime error",
            )

        user = await db.get_user_oauth_id(user_data["team"]["id"])
        if user is None:
            user = await db.insert_oauth_user(user_data["team"]["id"], user_data["team"]["name"], user_data["team"].get("country", ""))
            metrics.users.inc()

        metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

        access_token = auth.create_user_token(user)
        resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        resp.status_code = status.HTTP_307_TEMPORARY_REDIRECT
        resp.headers["Location"] = req.url_for("index")
    return "ok"
