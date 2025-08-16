import uuid
from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from yatb import schema
from yatb.auth import CURR_ADMIN
from yatb.db import UserDB

from . import router


async def api_admin_users_internal() -> Mapping[uuid.UUID, schema.User]:
    all_users = await UserDB.get_all()
    return all_users


async def get_user(user_id: uuid.UUID) -> UserDB:
    user = await UserDB.find_by_user_uuid(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


CURR_USER = Annotated[UserDB, Depends(get_user)]


class PasswordChangeForm(BaseModel):
    new_password: str


@router.get("/user/{user_id}")
async def api_admin_user(admin: CURR_ADMIN, user: CURR_USER) -> schema.User.admin_model:
    return user


@router.post("/user/{user_id}")
async def api_admin_user_edit(new_user: schema.User, user_id: uuid.UUID, admin: CURR_ADMIN) -> schema.User.admin_model:
    # new_user = await db.update_user_admin(user_id, new_user)
    raise Exception

    return new_user


@router.get("/users/me")
async def api_admin_users_me(admin: CURR_ADMIN) -> schema.User.admin_model:
    return admin


@router.get("/users")
async def api_admin_users(admin: CURR_ADMIN) -> Mapping[uuid.UUID, schema.User.admin_model]:
    all_users = await api_admin_users_internal()
    return all_users


@router.post("/user/{user_id}/password")
async def api_admin_user_edit_password(
    new_password: PasswordChangeForm,
    admin: CURR_ADMIN,
    user: CURR_USER,
) -> schema.User.admin_model:
    au = user.auth_source
    if not isinstance(au, schema.auth.SimpleAuth.AuthModel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not login-passw sourced",
        )
    au.password_hash = schema.auth.simple.hash_password(new_password.new_password)
    return user


@router.get("/user/{user_id}/score")
async def api_admin_user_recalc_score(
    admin: CURR_ADMIN,
    user: CURR_USER,
) -> schema.User.admin_model:
    await user.recalc_score_one()
    return user


@router.delete("/user/{user_id}")
async def api_admin_user_delete(
    admin: CURR_ADMIN,
    user: CURR_USER,
) -> str:
    raise Exception

    if len(user.solved_tasks) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user have solved tasks",
        )
    # await db.delete_user(user)
    return "deleted"
