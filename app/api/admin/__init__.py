import logging

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends, APIRouter
from ... import auth, config, schema, db


async def admin_checker(user: schema.User = Depends(auth.get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No.",
        )
    return user


logger = logging.getLogger("yatb.api.admin")
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/save_db")
async def save_db(user: schema.User = Depends(admin_checker)):
    await db.shutdown_event()
    logger.warning(f"DB saved by {user.short_desc()}")


from . import admin_users  # noqa
from . import admin_tasks  # noqa
