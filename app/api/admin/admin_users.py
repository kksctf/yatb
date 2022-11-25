import uuid
from typing import List, Dict

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel
from . import admin_checker, router, logger
from ... import schema, auth, config, db


async def api_admin_users_internal() -> Dict[uuid.UUID, schema.User]:
    all_users = await db.get_all_users()
    return all_users


async def api_admin_user_get_internal(user_id: uuid.UUID) -> schema.User:
    user = await db.get_user_uuid(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


class PasswordChangeForm(BaseModel):
    new_password: str


@router.get(
    "/user/{user_id}",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_user(user_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    ret_user = await api_admin_user_get_internal(user_id)
    return ret_user


@router.post(
    "/user/{user_id}",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_user_edit(new_user: schema.User, user_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    new_user = await db.update_user_admin(user_id, new_user)
    return new_user


@router.post(
    "/user/{user_id}/password",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_user_edit_password(
        new_password: PasswordChangeForm,
        user: schema.User = Depends(api_admin_user_get_internal),
        admin: schema.User = Depends(admin_checker),
):
    au = user.auth_source
    if not isinstance(au, schema.auth.SimpleAuth.AuthModel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not login-passw sourced",
        )
    au.password_hash = schema.auth.simple.hash_password(new_password.new_password)
    return user


@router.get(
    "/users/me",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_users_me(user: schema.User = Depends(admin_checker)):
    return user


@router.get(
    "/users",
    response_model=Dict[uuid.UUID, schema.User],
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_users(user: schema.User = Depends(admin_checker)):
    all_users = await api_admin_users_internal()
    return all_users

@router.delete(
    "/user/{user_id}",
    response_model=str,
    response_model_include=schema.User.get_include_fieds(True),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_admin_user_delete(
    user_id: uuid.UUID,
    user: schema.User = Depends(api_admin_user_get_internal),
    admin: schema.User = Depends(admin_checker),
):
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