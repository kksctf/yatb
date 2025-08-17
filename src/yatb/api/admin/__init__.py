from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from yatb import auth, schema
from yatb.auth import CURR_ADMIN
from yatb.config import settings
from yatb.db import TaskDB, UserDB
from yatb.utils.log_helper import get_logger

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
    if not settings.DEBUG and admin != auth._fake_admin_user:
        logger.error(f"{admin} чистить юзеров на проде")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unacceptable",
        )

    for user in (await UserDB.get_all()).values():
        if not user.is_admin:
            await user.delete()

    for task in (await TaskDB.get_all()).values():
        task.pwned_by.clear()
        await task.save()


@router.delete("/db")
async def api_detele_everything(admin: CURR_ADMIN, *, force: bool = False) -> None:
    if not settings.DEBUG and admin != auth._fake_admin_user:
        logger.error(f"{admin} чистит бд!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unacceptable",
        )

    for user in (await UserDB.get_all()).values():
        if user.is_admin:
            continue
        if len(user.solved_tasks) and not force:
            continue

        await user.delete()

    for task in (await TaskDB.get_all()).values():
        if len(task.pwned_by) and not force:
            continue

        await task.delete()


from . import admin_tasks  # noqa
from . import admin_users  # noqa
