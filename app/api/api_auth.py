import uuid
from datetime import timedelta
from typing import Callable, List, Literal, Optional, Type, cast

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


async def check_for_existing_model(
    model: schema.auth.AuthBase.AuthModel,
    check_for_class: Type[schema.auth.AuthBase.AuthModel],
):
    username = model.generate_username()
    user_by_username = await db.get_user(username)
    if user_by_username and not isinstance(user_by_username.auth_source, check_for_class):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team already exists. If you want to migrate between password <-> ctftime auth, contact orgs",
        )


def generic_handler_generator(cls: Type[schema.auth.AuthBase]) -> Callable:
    """
    This is a little crazy "generic generator" for handling universal auth way.
    Should work for most of possible authentification ways.
    """

    async def generic_handler(
        req: Request,
        resp: Response,
        form: "schema.auth.AuthBase.Form" = Depends(),
    ) -> Literal["ok"]:

        # create model from form.
        model = await form.populate(req, resp)

        # check for team with same name, but from other reg source.
        await check_for_existing_model(model, cls.AuthModel)

        # extract primary (unique) field from model, and check
        # is user with that field exists
        user = await db.get_user_uniq_field(cls.AuthModel, model.get_uniq_field())
        if user is None:
            # if not: create new user
            user = await db.insert_user(model)
            metrics.users.inc()
        else:
            # if exist: check for admin
            if user.admin_checker() and not user.is_admin:
                logger.warning(f"Promoting old {user} to admin")
                user.is_admin = True

        metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

        # create token for user, and put it in cookie
        access_token = auth.create_user_token(user)
        resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        resp.status_code = status.HTTP_303_SEE_OTHER
        resp.headers["Location"] = req.url_for("index")

        return "ok"

    generic_handler.__annotations__["form"] = cls.Form
    return generic_handler


async def api_auth_simple_login(req: Request, resp: Response, form: schema.SimpleAuth.Form = Depends()):
    # almost the same generic, but for login/password form, due to additional login.
    model = await form.populate(req, resp)
    user = await db.get_user_uniq_field(schema.SimpleAuth.AuthModel, model.get_uniq_field())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    auth_source = cast(schema.SimpleAuth.AuthModel, user.auth_source)
    if not form.check_password(auth_source):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


async def api_auth_simple_register(req: Request, resp: Response, form: schema.SimpleAuth.Form = Depends()):
    # almost the same generic, but for login/password form, due to additional login.
    model = await form.populate(req, resp)

    # check for team with same name, but from other reg source.
    await check_for_existing_model(model, schema.SimpleAuth.AuthModel)

    user = await db.get_user_uniq_field(schema.SimpleAuth.AuthModel, model.get_uniq_field())
    if user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team exists",
        )

    user = await db.insert_user(model)
    metrics.users.inc()

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


# Create routes for all enabled auth ways
# also, handle login/password way especially...
for auth_way in schema.auth.ENABLED_AUTH_WAYS:
    if auth_way != schema.auth.SimpleAuth:
        router.add_api_route(
            endpoint=generic_handler_generator(auth_way),
            **auth_way.router_params,
        )
    else:
        router.add_api_route(  # noqa: E1132 # this is intended way
            endpoint=api_auth_simple_login,
            path="/simple_login",
            name="api_auth_simple_login",
            methods=["POST"],
            **auth_way.router_params,
        )
        router.add_api_route(  # noqa: E1132 # this is intended way
            endpoint=api_auth_simple_register,
            path="/simple_register",
            name="api_auth_simple_register",
            methods=["POST"],
            **auth_way.router_params,
        )
