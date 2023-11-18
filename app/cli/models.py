import random
import string
import uuid
from dataclasses import dataclass
from datetime import datetime

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


class FileTask(BaseModel):
    name: str
    description: str

    author: str
    category: str

    flag: str
    is_gulag: bool = False

    warmup: bool = False
    server_port: int | None = None

    is_http: bool = True
    domain_prefix: str | None = None

    @property
    def full_name(self) -> str:
        return self.name

    def get_raw(self) -> RawTask:
        name = self.full_name

        description = self.description.strip().strip('"').strip("'")

        if self.server_port:
            if self.is_http:
                if self.domain_prefix:
                    server_addr = f"https://{self.domain_prefix}.{settings.tasks_domain}/"
                else:
                    server_addr = f"http://{settings.tasks_ip}:{self.server_port}"

                description += "\n\n---\n\n"
                description += '<div class="card-text row d-flex justify-content-between">'
                description += (
                    f"<a class='col-auto m-1 flex-fill' "
                    f"href='{server_addr}' rel='noopener noreferrer' "
                    f"target='_blank'>{server_addr}</a>\n"
                )
                description += "</div>"
            else:
                description += (
                    "\n\n---\n\n"
                    f"`nc {settings.tasks_ip} {self.server_port}`"
                    "\n"  #
                )

        flag = self.flag
        if flag.startswith(settings.flag_base + "{") and flag.endswith("}"):
            flag = flag.removeprefix(settings.flag_base + "{")
            flag = flag.removesuffix("}")

        return RawTask(
            task_name=name,
            category=self.category,
            description=description,
            flag=flag,
            author=self.author,
        )


AllUsers = RootModel[dict[uuid.UUID, UserPrivate]]
AllTasks = RootModel[dict[uuid.UUID, schema.Task]]
