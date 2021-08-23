import uuid
from datetime import timedelta
from typing import Callable, List, Literal, Optional, Type

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


def generic_handler_generator(cls: Type[schema.auth.AuthBase]) -> Callable:
    async def generic_handler(
        req: Request,
        resp: Response,
        form: "schema.auth.AuthBase.Form" = Depends(),
    ) -> Literal["ok"]:

        model = await form.populate(req, resp)

        user = await db.get_user_uniq_field(cls.AuthModel, model.get_uniq_field())
        if user is None:
            user = await db.insert_user(model)
            metrics.users.inc()

        metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

        access_token = auth.create_user_token(user)
        resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        resp.status_code = status.HTTP_303_SEE_OTHER
        resp.headers["Location"] = req.url_for("index")

        return "ok"

    generic_handler.__annotations__["form"] = cls.Form
    return generic_handler


async def api_auth_simple_login(req: Request, resp: Response, form: schema.SimpleAuth.Form = Depends()):
    model = await form.populate(req, resp)
    user = await db.get_user_uniq_field(schema.SimpleAuth.AuthModel, model.get_uniq_field())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


async def api_auth_simple_register(req: Request, resp: Response, form: schema.SimpleAuth.Form = Depends()):
    model = await form.populate(req, resp)
    user = await db.get_user_uniq_field(schema.SimpleAuth.AuthModel, model.get_uniq_field())
    if user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Username exists",
        )

    user = await db.insert_user(model)
    metrics.users.inc()

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


for auth_way in schema.auth.ENABLED_AUTH_WAYS:
    if auth_way != schema.auth.SimpleAuth:
        router.add_api_route(
            endpoint=generic_handler_generator(auth_way),
            **auth_way.router_params,
        )
    else:
        router.add_api_route(
            endpoint=api_auth_simple_login,
            path="/simple_login",
            name="api_auth_simple_login",
            methods=["POST"],
            **auth_way.router_params,
        )
        router.add_api_route(
            endpoint=api_auth_simple_register,
            path="/simple_register",
            name="api_auth_simple_register",
            methods=["POST"],
            **auth_way.router_params,
        )
