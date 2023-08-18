import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt

from . import schema
from .config import settings
from .db.beanie import UserDB
from .utils.log_helper import get_logger

logger = get_logger("auth")


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        *,
        scheme_name: str | None = None,
        scopes: dict | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        scopes = scopes or {}

        flows = OAuthFlowsModel()  # password={"tokenUrl": tokenUrl, "scopes": scopes}
        super().__init__(flows=flows, scheme_name=scheme_name, description=description, auto_error=auto_error)

    async def __call__(self, request: Request) -> str:
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


oauth2_scheme = OAuth2PasswordBearerWithCookie()


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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> schema.User:
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


async def get_current_user_safe(request: Request) -> schema.User | None:
    user = None
    try:
        user = await get_current_user(await oauth2_scheme(request))
    except HTTPException:
        user = None

    return user
