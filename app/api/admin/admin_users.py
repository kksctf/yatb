import uuid
from typing import List, Dict

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends
from . import admin_checker, router, logger
from ... import schema, auth, config, db


async def api_admin_users_internal() -> Dict[uuid.UUID, schema.User]:
    all_users = await db.get_all_users()
    return all_users


async def api_admin_user_get_internal(user_id: uuid.UUID) -> schema.User:
    user = await db.get_user_uuid(user_id)
    return user


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
