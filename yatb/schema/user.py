import datetime
import uuid
from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, model_validator

from ..ebasemodelv2 import Admin, EBaseModelV2, Private, Public
from ..ebasemodelv2 import PresentationLevel as P
from ..utils.log_helper import get_logger
from .auth import ANNOTATED_TYPING_AUTH
from .auth.auth_base import AuthBase

logger = get_logger("schema.user")


class ExtraInfo(EBaseModelV2):
    affilation: Public[str] = ""
    country: Public[str] = ""
    profile_pic: Public[str | None] = None


class User(EBaseModelV2):
    user_id: Public[uuid.UUID] = Field(default_factory=uuid.uuid4)

    username: Public[str] = "unknown"

    score: Public[int] = 0

    solved_tasks: Public[dict[uuid.UUID, datetime.datetime]] = {}  # noqa: RUF012

    is_admin: Admin[bool] = False

    auth_source: Admin[ANNOTATED_TYPING_AUTH]  # pyright: ignore[reportInvalidTypeForm]

    @property
    def au_s(self) -> AuthBase.AuthModel:  # WTF: dirty hack... ;(
        return self.auth_source

    @model_validator(mode="after")
    def setup_fields(self) -> Self:
        self.username = self.au_s.generate_username()
        if self.admin_checker() and not self.is_admin:
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
