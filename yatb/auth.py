import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, TypeAlias

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt

from . import schema
from .config import settings
from .db import UserDB
from .utils.log_helper import get_logger

logger = get_logger("auth")

_fake_admin_user = schema.User(
    username="token_bot",
    is_admin=True,
    auth_source=schema.auth.TokenAuth.AuthModel(username="hardcoded_token"),
)


async def token_puller(request: Request) -> str:
    authorization_cookie = request.cookies.get("access_token", None)
    authorization_header = request.headers.get("X-Auth-Token", None)

    if not authorization_cookie and not authorization_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No cookie or header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, param = get_authorization_scheme_param(authorization_header or authorization_cookie)
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return param


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=15)) -> str:
    to_encode = data.copy()

    expire = datetime.now(tz=UTC) + expires_delta
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_user_token(user: schema.User) -> str:
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"user_id": str(user.user_id)},
        expires_delta=access_token_expires,
    )


async def get_current_user(token: Annotated[str, Depends(token_puller)]) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id: str | None = None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])  # no "alg:none"
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError as ex:
        raise credentials_exception from ex

    user = await UserDB.find_by_user_uuid(uuid.UUID(user_id))
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_safe(request: Request) -> UserDB | None:
    user = None
    try:
        user = await get_current_user(await token_puller(request))
    except HTTPException:
        user = None

    return user


async def admin_checker(
    user: "CURR_USER_SAFE",
    token_header: str | None = Header(None, alias="X-Token"),
    token_query: str | None = Query(None, alias="token"),
) -> schema.User:
    if user and user.is_admin:
        return user

    if token_header and token_header == settings.API_TOKEN:
        return _fake_admin_user
    if token_query and token_query == settings.API_TOKEN:
        return _fake_admin_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No.",
    )


# https://github.com/fastapi/fastapi/issues/10719, https://github.com/fastapi/fastapi/pull/13920
CURR_USER: TypeAlias = Annotated[UserDB, Depends(get_current_user)]
CURR_USER_SAFE: TypeAlias = Annotated[UserDB | None, Depends(get_current_user_safe)]
CURR_ADMIN: TypeAlias = Annotated[UserDB, Depends(admin_checker)]
