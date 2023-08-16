import logging

from fastapi import APIRouter, Cookie, Depends, FastAPI, Header, HTTPException, Query, Request, Response, status

from ... import auth, config, db, schema
from ...utils.log_helper import get_logger

_fake_admin_user = schema.User(
    username="token_bot",
    is_admin=True,
    auth_source=schema.auth.SimpleAuth.AuthModel(username="token_bot", password_hash=(b"\x00", b"\x00")),
)


async def admin_checker(
    user: schema.User | None = Depends(auth.get_current_user_safe),
    token_header: str | None = Header(None, alias="X-Token"),
    token_query: str | None = Query(None, alias="token"),
) -> schema.User:
    if user and user.is_admin:
        return user
    if token_header and token_header == config.settings.API_TOKEN:
        return _fake_admin_user
    if token_query and token_query == config.settings.API_TOKEN:
        return _fake_admin_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No.",
    )


logger = get_logger("api.admin")
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/save_db")
async def save_db(user: schema.User = Depends(admin_checker)):
    await db.shutdown_event()
    logger.warning(f"DB saved by {user.short_desc()}")


@router.delete("/cleanup_db")
async def api_detele_everything_but_tasks(admin: schema.User = Depends(admin_checker)):
    if not config.settings.DEBUG:
        logger.error(f"{admin} чистить юзеров на проде")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unacceptable",
        )

    for user in list((await db.get_all_users()).values()):
        if not user.is_admin:
            await db.delete_user(user)

    for task in (await db.get_all_tasks()).values():
        task.pwned_by.clear()


from . import admin_tasks  # noqa
from . import admin_users  # noqa
