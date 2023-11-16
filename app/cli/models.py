import random
import string
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, RootModel

from .. import schema


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


class FileTask(BaseModel):
    task_name: str
    flag: str
    is_gulag: bool = False

    author: str = "none"
    category: str | None = None

    def get_raw(self, category_name: str, description: str) -> RawTask:
        return RawTask(
            task_name=self.task_name,
            category=self.category or category_name,
            description=description,
            flag=self.flag,
            author=self.author,
        )


AllUsers = RootModel[dict[uuid.UUID, UserPrivate]]
AllTasks = RootModel[dict[uuid.UUID, schema.Task]]
