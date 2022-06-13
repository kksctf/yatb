import binascii
import datetime
import hashlib
import hmac
import os
import uuid
from typing import Dict, List, Optional, Type, Union

from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Extra, validator

from ..config import settings
from .auth import TYPING_AUTH
from . import EBaseModel, logger, md


class User(EBaseModel):
    __public_fields__ = {
        "user_id",
        "username",
        "score",
        "solved_tasks",
        "affilation",
        "country",
        "profile_pic",
    }
    __admin_only_fields__ = {
        "is_admin",
        "oauth_id",
    }
    __private_fields__ = {}

    user_id: uuid.UUID = None  # type: ignore # yes i know, but factory in pydantic needed this shit.

    username: str = "unknown"

    score: int = 0

    solved_tasks: Dict[uuid.UUID, datetime.datetime] = {}  # uuid or task :hm
    is_admin: bool = False

    affilation: str = ""
    country: str = ""

    profile_pic: Optional[str] = None

    auth_source: TYPING_AUTH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = self.auth_source.generate_username()

    def admin_checker(self):
        return self.auth_source.is_admin()

    @validator("user_id", pre=True, always=True)
    def set_id(cls, v):
        return v or uuid.uuid4()

    def get_last_solve_time(self):
        if len(self.solved_tasks) > 0:
            return max(self.solved_tasks.items(), key=lambda x: x[1])
        else:
            return ("", datetime.datetime.fromtimestamp(0))

    def short_desc(self):
        return f"id={self.user_id}; name={self.username}; src={self.auth_source.classtype}"
