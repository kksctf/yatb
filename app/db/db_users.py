from app.db import update_entry
import uuid
import logging
from typing import Hashable, List, Dict, Optional, Type

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


async def get_user_uniq_field(base: Type[schema.auth.AuthBase.AuthModel], field: Hashable) -> schema.User:
    from . import _db

    for i in _db._index["users"]:
        if (
            type(_db._index["users"][i].auth_source) == base
            and _db._index["users"][i].auth_source.get_uniq_field() == field
        ):
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


async def check_user_uniq_field(base: Type[schema.auth.AuthBase.AuthModel], field: Hashable) -> bool:
    from . import _db

    for i in _db._index["users"]:
        if (
            type(_db._index["users"][i].auth_source) == base
            and _db._index["users"][i].auth_source.get_uniq_field() == field
        ):
            return True
    return False


async def insert_user(auth: schema.auth.TYPING_AUTH):
    from . import _db

    # WTF: SHITCODE or not.... :thonk:
    user = schema.User(auth_source=auth)
    _db._db["users"][user.user_id] = user
    _db._index["users"][user.user_id] = user
    return user


"""
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
"""


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

    async def delete_user(user: schema.User):
        from . import _db

        del _db._db["users"][user.user_id]
        del _db._index["users"][user.user_id]