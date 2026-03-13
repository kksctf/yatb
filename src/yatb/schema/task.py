import datetime
import uuid
from collections.abc import Sequence
from typing import Annotated, TypeAlias
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, computed_field

from yatb import config
from yatb.config import settings
from yatb.ebasemodelv2 import Admin, EBaseModelV2, Public
from yatb.shared.dtc.models import DynamicTaskFeatures
from yatb.utils import md
from yatb.utils.log_helper import get_logger

from .flags import DynamicKKSFlag, StaticFlag
from .ids import ModelTaskID, TaskID, TaskIDField, UserID
from .scoring import DynamicKKSScoring, StaticScoring
from .user import User

logger = get_logger("schema.task")

TARGET_TZ = ZoneInfo("Europe/Moscow")


def template_format_time(date: datetime.datetime) -> str:  # from alb1or1x_shit.py
    if Task.is_date_after_migration(date):
        localized_date = date.astimezone(tz=TARGET_TZ)
        # return date.strftime("%H:%M:%S.%f %d.%m.%Y")  # str(round(date.timestamp(), 2))
        t = datetime.datetime.now(tz=datetime.UTC) - date
        return f"{Task.humanize_time(t)} ago / {localized_date.strftime('%H:%M:%S')}"
    return "unknown"


# https://github.com/pydantic/pydantic/issues/11552
ScoringUnion: TypeAlias = Annotated[  # noqa: UP040
    StaticScoring | DynamicKKSScoring,
    Field(discriminator="classtype"),
]
FlagUnion: TypeAlias = Annotated[  # noqa: UP040
    StaticFlag | DynamicKKSFlag,
    Field(discriminator="classtype"),
]


class DynamicTaskInfo(EBaseModelV2):
    features: Admin[DynamicTaskFeatures]
    service_info: Admin[tuple[str, str] | None] = None
    builder_info: Admin[tuple[str, str] | None] = None
    s3_url: Admin[str | None] = None
    vm_ports: Admin[list[int]] = []


class Task(EBaseModelV2):
    task_id: Public[ModelTaskID] = TaskIDField

    task_name: Public[str]
    category: Public[str]

    scoring: Public[ScoringUnion]

    description: Admin[str]
    description_html: Public[str]

    flag: Admin[FlagUnion]

    pwned_by: Public[dict[UserID, datetime.datetime]] = {}  # noqa: RUF012

    hidden: Admin[bool] = True

    author: Public[str]

    dti: Admin[DynamicTaskInfo | None] = None

    req_tasks: Admin[list[TaskID]] = []

    @computed_field
    @property
    def points(self) -> Public[int]:
        return self.scoring.points

    @computed_field
    @property
    def solves(self) -> Public[int]:
        return len(self.pwned_by)

    # @computed_field
    @property
    def color_category(self) -> str:
        if self.category.lower() == "crypto":
            return "crypto"

        if self.category.lower() == "web":
            return "web"

        if self.category.lower() in ["binary", "reverse", "pwn", "rev"]:
            return "binary"

        if self.category.lower() == "forensic":
            return "forensic"

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
        if self.hidden:  # noqa: SIM103
            return False

        if self.req_tasks:
            if not user:
                return False

            # every element of self.req_tasks is in user.solved_tasks
            # i.e. user solved all of tasks in req.tasks
            return set(self.req_tasks) <= set(user.solved_tasks)

        return True

    def is_solved_by(self, user: User) -> bool:
        return user and user.user_id in self.pwned_by

    @staticmethod
    def regenerate_md(content: str) -> str:
        return md.markdownCSS(content, config.MD_CLASSES_TASKS, config.MD_ATTRS_TASKS)

    @staticmethod
    def is_date_after_migration(dt: datetime.datetime) -> bool:
        migration_time = datetime.datetime.fromtimestamp(1605065347, tz=datetime.UTC)
        if dt > migration_time:  # noqa: SIM103
            return True
        return False

    # TODO: @Rubikoid, move this code somewhere else?
    @staticmethod
    def humanize_time(delta: datetime.timedelta) -> str:  # noqa: PLR0911
        dt = datetime.datetime.min.replace(tzinfo=datetime.UTC) + delta  # timedelta to datetime conversion :shrug:

        if dt.year > 1:
            return f"{dt.year - 1} year{'' if dt.year == 2 else 's'}"  # noqa: PLR2004
        if dt.month > 1:
            return f"{dt.month - 1} month{'' if dt.month == 2 else 's'}"  # noqa: PLR2004
        if dt.day > 1:
            return f"{dt.day - 1} day{'' if dt.day == 2 else 's'}"  # noqa: PLR2004
        if dt.hour > 0:
            return f"{dt.hour} hour{'' if dt.hour == 1 else 's'}"
        if dt.minute > 0:
            return f"{dt.minute} minute{'' if dt.minute == 1 else 's'}"
        if dt.second > 0:
            return f"{dt.second} second{'' if dt.second == 1 else 's'}"
        return ""

    def last_pwned_str(self) -> tuple[UserID, str] | None:
        if not self.pwned_by:
            return None

        last_pwn = max(self.pwned_by.items(), key=lambda x: x[1])

        last_time = datetime.datetime.now(tz=datetime.UTC) - last_pwn[1]
        result_time = Task.humanize_time(last_time) if Task.is_date_after_migration(last_pwn[1]) else "unknown"

        return last_pwn[0], result_time

    def first_pwned_str(self) -> tuple[UserID, str] | None:
        if not self.pwned_by:
            return None

        first_pwn = min(self.pwned_by.items(), key=lambda x: x[1])
        result_time = template_format_time(first_pwn[1])

        return first_pwn[0], result_time

    def short_desc(self) -> str:
        return f"task_id={self.task_id} task_name={self.task_name} hidden={self.hidden} points={self.scoring.points}"


class TaskForm(BaseModel):
    task_id: TaskID | None = None

    task_name: str
    category: str
    scoring: ScoringUnion
    description: str
    flag: FlagUnion
    author: str = ""

    dti: DynamicTaskInfo | None = None

    req_tasks: Sequence[TaskID] = []

    def to_task[T: Task](self, cls: type[T], author: User) -> T:
        str_author = self.author if self.author != "" else f"@{author.username}"
        if not str_author.startswith("@"):
            str_author = f"@{str_author}"

        task = cls(
            task_name=self.task_name,
            category=self.category,
            scoring=self.scoring,
            description=self.description,
            description_html=cls.regenerate_md(self.description),
            flag=self.flag,
            author=str_author,
            dti=self.dti,
            req_tasks=list(self.req_tasks),
        )

        # WTF: shitcode
        if self.task_id:
            task.task_id = self.task_id

        return task
