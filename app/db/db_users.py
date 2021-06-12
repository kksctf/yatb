from app.db import update_entry
import uuid
import logging
from typing import List, Dict, Optional

from .. import schema

logger = logging.getLogger("yatb.db.users")

# logger.debug(f"GlobalUsers, FileDB: {_db}")


async def get_user(username: str) -> Optional[schema.User]:
    from . import _db

    for i in _db._index["users"]:
        if _db._index["users"][i].username == username:
            return _db._index["users"][i]
    return None


async def get_user_uuid(uuid: uuid.UUID) -> Optional[schema.User]:
    from . import _db

    if uuid in _db._index["users"]:
        return _db._index["users"][uuid]


async def get_user_oauth_id(id: int) -> schema.User:
    from . import _db

    if id == -1:
        return None
    for i in _db._index["users"]:
        if _db._index["users"][i].oauth_id == id:
            return _db._index["users"][i]
    return None


async def get_all_users() -> Dict[uuid.UUID, schema.User]:
    from . import _db

    return _db._db["users"]


async def check_user(username: str) -> bool:
    from . import _db

    for i in _db._index["users"]:
        if _db._index["users"][i].username == username:
            return True
    return False


async def check_user_uuid(uuid: uuid.UUID) -> bool:
    from . import _db

    return uuid in _db._index["users"]


async def check_user_oauth_id(id: int) -> bool:
    from . import _db

    if id == -1:
        return False
    for i in _db._index["users"]:
        if _db._index["users"][i].oauth_id == id:
            return True
    return False


async def insert_user(username: str, password: str):
    from . import _db

    # WTF: SHITCODE
    user = schema.User(
        username=username,
        password_hash=password,
    )
    _db._db["users"][user.user_id] = user
    _db._index["users"][user.user_id] = user
    return user


async def insert_oauth_user(oauth_id: int, username: str, country: str):
    from . import _db

    # WTF: SHITCODE
    user = schema.User(
        username=username,
        password_hash=None,
        country=country,
        oauth_id=oauth_id,
    )
    _db._db["users"][user.user_id] = user
    _db._index["users"][user.user_id] = user
    return user


async def dynamic_flags_for_new_usr(user: schema.User):
    from . import _db

    for task_id, task in _db._db["tasks"].items():
        task: schema.Task
        if task.flag.dynamic_type_checker:
            task.flag.flag_for_all(user.username, task.flag.flag_value + user.hash_value() + "}")


async def update_user(user_id: uuid.UUID, new_user: schema.UserUpdateForm):
    from . import _db

    user: schema.User = _db._index["users"][user_id]
    user.parse_obj(new_user)  # WTF: crazy updater?


async def update_user_admin(user_id: uuid.UUID, new_user: schema.User):
    from . import _db

    user: schema.User = _db._index["users"][user_id]
    logger.debug(f"Update user {user} to {new_user}")

    update_entry(
        user,
        new_user.dict(
            exclude={
                "user_id",
                "password_hash",
                "score",
                "solved_tasks",
                "oauth_id",
            }
        ),
    )
    # user.parse_obj(new_user)
    logger.debug(f"Resulting user={user}")
    return user


async def set_flag_for_all(task: schema.Task):

    from . import _db

    for user_id, user in _db._db["users"].items():
        user: schema.User
        task.flag.flag_for_all(user.username, task.flag.flag_value + user.hash_value() + "}")
