from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ... import auth, schema
from ...config import settings
from ...db.beanie import TaskDB, UserDB
from ...utils.log_helper import get_logger

_fake_admin_user = schema.User(
    username="token_bot",
    is_admin=True,
    auth_source=schema.auth.TokenAuth.AuthModel(username="hardcoded_token"),
)


async def admin_checker(
    user: auth.CURR_USER_SAFE,
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


CURR_ADMIN = Annotated[schema.User, Depends(admin_checker)]

logger = get_logger("api.admin")
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


# @router.get("/save_db")
# async def save_db(user: CURR_ADMIN):
#     await db.shutdown_event()
#     logger.warning(f"DB saved by {user.short_desc()}")


@router.delete("/db_users")
async def api_detele_everything_but_tasks(admin: CURR_ADMIN) -> None:
    if not settings.DEBUG:
        logger.error(f"{admin} чистить юзеров на проде")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unacceptable",
        )

    for user in (await UserDB.get_all()).values():
        if not user.is_admin:
            await user.delete()  # type: ignore # WTF: great library

    for task in (await TaskDB.get_all()).values():
        task.pwned_by.clear()
        await task.save()  # type: ignore # WTF: great library


@router.delete("/db")
async def api_detele_everything(admin: CURR_ADMIN) -> None:
    if not settings.DEBUG:
        logger.error(f"{admin} чистить бд")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unacceptable",
        )

    for user in (await UserDB.get_all()).values():
        if not user.is_admin:
            await user.delete()  # type: ignore # WTF: great library

    for task in (await TaskDB.get_all()).values():
        await task.delete()  # type: ignore # WTF: great library


from . import admin_tasks  # noqa
from . import admin_users  # noqa
