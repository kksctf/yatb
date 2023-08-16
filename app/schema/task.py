import datetime
import uuid
from typing import Annotated, ClassVar

from pydantic import Extra, Field, computed_field, validator

from .. import config
from ..config import settings
from ..utils import md
from . import EBaseModel, User, logger
from .flags import DynamicKKSFlag, Flag, StaticFlag
from .scoring import DynamicKKSScoring, Scoring, StaticScoring


def template_format_time(date: datetime.datetime) -> str:  # from alb1or1x_shit.py
    if Task.is_date_after_migration(date):
        # return date.strftime("%H:%M:%S.%f %d.%m.%Y")  # str(round(date.timestamp(), 2))
        t = datetime.datetime.now(tz=datetime.UTC) - date
        return f"{Task.humanize_time(t)} ago / {date.strftime('%H:%M:%S')}"
    return "unknown"


ScoringUnion = Annotated[Scoring | StaticScoring | DynamicKKSScoring, Field(discriminator="classtype")]
FlagUnion = Annotated[Flag | StaticFlag | DynamicKKSFlag, Field(discriminator="classtype")]


class Task(EBaseModel):
    __public_fields__: ClassVar = {
        "task_id",
        "task_name",
        "category",
        "scoring",
        "description_html",
        "author",
        "pwned_by",
    }
    __admin_only_fields__: ClassVar = {
        "description",
        "flag",
        "hidden",
    }

    task_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    task_name: str
    category: str

    scoring: ScoringUnion

    description: str
    description_html: str

    flag: FlagUnion

    pwned_by: dict[uuid.UUID, datetime.datetime] = {}

    hidden: bool = True

    author: str

    # @computed_field
    @property
    def color_category(self) -> str:
        if self.category.lower() == "crypto":
            return "crypto"
        elif self.category.lower() == "web":
            return "web"
        elif self.category.lower() in ["binary", "reverse", "pwn"]:
            return "binary"
        return "other"

    def visible_for_user(self, user: User | None = None) -> bool:
        # if admin: always display task.
        if user and user.is_admin:
            return True

        # if event not started yet
        if datetime.datetime.now(tz=datetime.UTC) <= settings.EVENT_START_TIME:
            return False

        # if task is hidden and no user/not admin:
        # always hide
        if self.hidden:
            return False

        return True

    @staticmethod
    def regenerate_md(content: str) -> str:
        return md.markdownCSS(content, config.MD_CLASSES_TASKS, config.MD_ATTRS_TASKS)

    @staticmethod
    def is_date_after_migration(dt: datetime.datetime) -> bool:
        migration_time = datetime.datetime.fromtimestamp(1605065347, tz=datetime.UTC)
        if dt > migration_time:
            return True
        return False

    # TODO: @Rubikoid, move this code somewhere else?
    @staticmethod
    def humanize_time(delta: datetime.timedelta) -> str:
        dt = datetime.datetime.min + delta  # timedelta to datetime conversion :shrug:
        if dt.year > 1:
            return f"{dt.year - 1} year{'' if dt.year == 2 else 's'}"
        if dt.month > 1:
            return f"{dt.month - 1} month{'' if dt.month == 2 else 's'}"
        if dt.day > 1:
            return f"{dt.day - 1} day{'' if dt.day == 2 else 's'}"
        elif dt.hour > 0:
            return f"{dt.hour} hour{'' if dt.hour == 1 else 's'}"
        elif dt.minute > 0:
            return f"{dt.minute} minute{'' if dt.minute == 1 else 's'}"
        elif dt.second > 0:
            return f"{dt.second} second{'' if dt.second == 1 else 's'}"
        return ""

    def last_pwned_str(self) -> tuple[uuid.UUID, str]:
        last_pwn = max(self.pwned_by.items(), key=lambda x: x[1])

        last_time = datetime.datetime.now(tz=datetime.UTC) - last_pwn[1]
        result_time = Task.humanize_time(last_time) if Task.is_date_after_migration(last_pwn[1]) else "unknown"

        return last_pwn[0], result_time

    def first_pwned_str(self) -> tuple[uuid.UUID, str]:
        first_pwn = min(self.pwned_by.items(), key=lambda x: x[1])
        result_time = template_format_time(first_pwn[1])

        return first_pwn[0], result_time

    def short_desc(self) -> str:
        return f"task_id={self.task_id} task_name={self.task_name} hidden={self.hidden} points={self.scoring.points}"


class TaskForm(EBaseModel):
    task_name: str
    category: str
    scoring: ScoringUnion
    description: str
    flag: FlagUnion
    author: str = ""
