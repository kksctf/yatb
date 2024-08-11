import random
import string
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, RootModel

from .. import schema
from .base import settings


class UserPublic(schema.EBaseModel):
    user_id: uuid.UUID
    username: str

    score: int
    solved_tasks: dict[uuid.UUID, datetime]


class UserPrivate(UserPublic):
    is_admin: bool


@dataclass
class RawUser:
    username: str
    password: str = "0"

    def generate_password(self) -> None:
        self.password = "".join(random.choices(string.ascii_letters, k=16))  # noqa: S311 # i. knew.


@dataclass
class RawTask:
    task_name: str
    category: str
    description: str

    flag: str

    author: str = ""

    dynamic_task_type: schema.DynamicTaskInfo | None = None


class FileTask(BaseModel):
    name: str
    description: str

    author: str
    category: str

    flag: str

    server_port: int | None = None

    is_http: bool = True
    domain_prefix: str | None = None

    @property
    def full_name(self) -> str:
        return self.name


class State(BaseModel):
    task_to_uuid: dict[Path, uuid.UUID] = {}


AllUsers = RootModel[dict[uuid.UUID, UserPrivate]]
AllTasks = RootModel[dict[uuid.UUID, schema.Task]]
