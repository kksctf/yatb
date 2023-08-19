import uuid
from typing import Annotated, Mapping

from fastapi import APIRouter, Cookie, Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from ... import auth, schema
from ...config import settings
from ...db.beanie import TaskDB, UserDB
from ...utils.log_helper import get_logger
from . import CURR_ADMIN, logger, router


async def api_admin_users_internal() -> Mapping[uuid.UUID, schema.User]:
    all_users = await UserDB.get_all()
    return all_users


async def api_admin_user_get_internal(user_id: uuid.UUID) -> schema.User:
    user = await UserDB.find_by_user_uuid(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


class PasswordChangeForm(BaseModel):
    new_password: str


@router.get("/user/{user_id}")
async def api_admin_user(user_id: uuid.UUID, user: CURR_ADMIN) -> schema.User.admin_model:
    ret_user = await api_admin_user_get_internal(user_id)
    return ret_user


@router.post("/user/{user_id}")
async def api_admin_user_edit(new_user: schema.User, user_id: uuid.UUID, user: CURR_ADMIN) -> schema.User.admin_model:
    new_user = await db.update_user_admin(user_id, new_user)
    return new_user


@router.get("/users/me")
async def api_admin_users_me(user: CURR_ADMIN) -> schema.User.admin_model:
    return user


@router.get("/users")
async def api_admin_users(user: CURR_ADMIN) -> Mapping[uuid.UUID, schema.User.admin_model]:
    all_users = await api_admin_users_internal()
    return all_users


@router.post("/user/{user_id}/password")
async def api_admin_user_edit_password(
    new_password: PasswordChangeForm,
    admin: CURR_ADMIN,
    user: schema.User = Depends(api_admin_user_get_internal),
) -> schema.User.admin_model:
    au = user.auth_source
    if not isinstance(au, schema.auth.SimpleAuth.AuthModel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not login-passw sourced",
        )
    au.password_hash = schema.auth.simple.hash_password(new_password.new_password)
    return user


@router.delete("/user/{user_id}")
async def api_admin_user_delete(
    admin: CURR_ADMIN,
    user: schema.User = Depends(api_admin_user_get_internal),
) -> str:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not exist",
        )

    if len(user.solved_tasks) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user have solved tasks",
        )
    await db.delete_user(user)
    return "deleted"
