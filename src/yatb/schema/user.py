import datetime
from typing import Literal, Self

from pydantic import Field, computed_field, model_validator

from yatb.ebasemodelv2 import Admin, EBaseModelV2, Public
from yatb.utils.log_helper import get_logger

from .auth import ANNOTATED_TYPING_AUTH
from .auth.base import AuthBase
from .ids import ModelUserID, TaskID, UserIDField
from .ui import UISettings

logger = get_logger("schema.user")


class ExtraInfo(EBaseModelV2):
    """Tier-2: public profile data, only editable while logged in."""

    affiliation: Public[str] = ""
    country: Public[str] = ""  # ISO 3166-1 alpha-2, or "" for unset
    profile_pic: Public[str | None] = None  # not editable yet


class User(EBaseModelV2):
    user_id: Public[ModelUserID] = UserIDField

    username: Public[str] = "unknown"

    score: Public[int] = 0

    solved_tasks: Public[dict[TaskID, datetime.datetime]] = {}  # noqa: RUF012

    is_admin: Admin[bool] = False

    auth_source: Admin[ANNOTATED_TYPING_AUTH]  # pyright: ignore[reportInvalidTypeForm]

    extra_info: Public[ExtraInfo] = Field(default_factory=ExtraInfo)

    settings: Public[UISettings] = Field(default_factory=UISettings)

    @property
    def au_s(self) -> AuthBase.AuthModel:  # WTF: dirty hack... ;(
        return self.auth_source

    @computed_field
    @property
    def display_name(self) -> Public[str]:
        return self.username

    @model_validator(mode="after")
    def setup_fields(self) -> Self:
        self.username = self.au_s.generate_username()

        if self.admin_checker() and not self.is_admin:
            logger.warning(f"Promoting {self} to admin")
            self.is_admin = True

        return self

    def admin_checker(self) -> bool:
        return self.au_s.is_admin()

    def get_last_solve_time(self) -> tuple[TaskID, datetime.datetime] | tuple[Literal[""], datetime.datetime]:
        if len(self.solved_tasks) > 0:
            return max(self.solved_tasks.items(), key=lambda x: x[1])

        return ("", datetime.datetime.fromtimestamp(0, tz=datetime.UTC))

    def short_desc(self) -> str:
        return f"user_id={self.user_id} username={self.username} authsrc={self.au_s.classtype}"
