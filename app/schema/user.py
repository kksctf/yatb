import datetime
import uuid
from typing import ClassVar, Literal, Self

from pydantic import Field, model_validator

from ..utils.log_helper import get_logger
from .auth import ANNOTATED_TYPING_AUTH
from .auth.auth_base import AuthBase
from .ebasemodel import EBaseModel

logger = get_logger("schema.user")


class User(EBaseModel):
    __public_fields__: ClassVar = {
        "user_id",
        "username",
        "score",
        "solved_tasks",
        "affilation",
        "country",
        "profile_pic",
    }
    __admin_only_fields__: ClassVar = {
        "is_admin",
        "auth_source",
    }
    __private_fields__: ClassVar = set()

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    username: str = "unknown"

    score: int = 0

    solved_tasks: dict[uuid.UUID, datetime.datetime] = {}  # uuid or task :hm
    is_admin: bool = False

    affilation: str = ""
    country: str = ""

    profile_pic: str | None = None

    auth_source: ANNOTATED_TYPING_AUTH  # type: ignore

    @property
    def au_s(self) -> AuthBase.AuthModel:  # WTF: dirty hack... ;(
        return self.auth_source

    @model_validator(mode="after")
    def setup_fields(self) -> Self:
        self.username = self.au_s.generate_username()
        if self.admin_checker():
            logger.warning(f"Promoting {self} to admin")
            self.is_admin = True

        return self

    def admin_checker(self) -> bool:
        return self.au_s.is_admin()

    def get_last_solve_time(self) -> tuple[uuid.UUID, datetime.datetime] | tuple[Literal[""], datetime.datetime]:
        if len(self.solved_tasks) > 0:
            return max(self.solved_tasks.items(), key=lambda x: x[1])

        return ("", datetime.datetime.fromtimestamp(0, tz=datetime.UTC))

    def short_desc(self) -> str:
        return f"user_id={self.user_id} username={self.username} authsrc={self.au_s.classtype}"
