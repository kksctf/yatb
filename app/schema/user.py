from typing import List, Dict, Optional, Union, Type
from fastapi import Query, HTTPException, status
from pydantic import BaseModel, validator, Extra

import uuid
import datetime
import hashlib
import hmac

from . import EBaseModel, logger, md, config


class User(EBaseModel):
    __public_fields__ = {
        "user_id",
        "username",
        "score",
        "solved_tasks",
        "affilation",
        "country",
        "profile_pic"
    }
    __admin_only_fields__ = {
        "is_admin",
        "oauth_id",
    }
    __private_fields__ = {
        "password_hash",
    }

    user_id: uuid.UUID = None

    username: str
    password_hash: Optional[str] = None

    score: int = 0

    solved_tasks: Dict[uuid.UUID, datetime.datetime] = {}  # uuid or task :hm
    is_admin: bool = False

    affilation: str = ""
    country: str = ""

    profile_pic: Optional[str] = None

    oauth_id: int = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.admin_checker():
            logger.warning(f"Promoting {self} to admin")
            self.is_admin = True

    def admin_checker(self):
        if (self.oauth_id == -1 and self.username == "Rubikoid"):
            return True

        if self.oauth_id in config.OAUTH_ADMIN_IDs:  # TODO: to config
            return True

        return False

    @validator('user_id', pre=True, always=True)
    def set_id(cls, v):
        return v or uuid.uuid4()

    def get_last_solve_time(self):
        if len(self.solved_tasks) > 0:
            return max(self.solved_tasks.items(), key=lambda x: x[1])
        else:
            return ("", datetime.datetime.fromtimestamp(0))

    def short_desc(self):
        return f"id={self.user_id};name={self.username}"


class UserForm(EBaseModel):
    username: str
    password: str


class UserUpdateForm(EBaseModel):
    username: str
    affilation: str
    country: str
