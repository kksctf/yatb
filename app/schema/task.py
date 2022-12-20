import datetime
import time
import uuid
from typing import Dict, List, Optional, Type, Union

import humanize
from pydantic import Extra, Field, validator

from ..config import settings
from ..utils import md
from . import EBaseModel, User, config, logger
from .flags import DynamicKKSFlag, Flag, StaticFlag
from .scoring import DynamicKKSScoring, Scoring, StaticScoring


def template_format_time(date: datetime.datetime) -> str:  # from alb1or1x_shit.py
    if Task.is_date_after_migration(date):
        # return date.strftime("%H:%M:%S.%f %d.%m.%Y")  # str(round(date.timestamp(), 2))
        t = datetime.datetime.now() - date
        ret = f"{Task.humanize_time(t)} ago / {date.strftime('%H:%M:%S')}"
        return ret
    else:
        return "unknown"


class Task(EBaseModel):
    __public_fields__ = {
        "task_id": ...,
        "task_name": ...,
        "category": ...,
        "scoring": Scoring,
        "description_html": ...,
        "author": ...,
        "pwned_by": ...,
    }
    __admin_only_fields__ = {
        "description": ...,
        "flag": Flag,
        "hidden": ...,
    }

    task_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    task_name: str
    category: str

    # due to https://github.com/tiangolo/fastapi/issues/86#issuecomment-478275969, order of items in union matters!
    scoring: Union[Scoring, StaticScoring, DynamicKKSScoring]  # = Scoring()

    description: str
    description_html: str

    flag: Union[Flag, StaticFlag, DynamicKKSFlag]

    pwned_by: Dict[uuid.UUID, datetime.datetime] = {}

    hidden: bool = True

    author: str

    @property
    def color_category(self) -> str:
        if self.category.lower() == "crypto":
            return "crypto"
        elif self.category.lower() == "web":
            return "web"
        elif self.category.lower() in ["binary", "reverse", "pwn"]:
            return "binary"
        return "other"

    def visible_for_user(self, user: Optional[User] = None) -> bool:
        # if admin: always display task.
        if user and user.is_admin:
            return True

        # if event not started yet
        if datetime.datetime.utcnow() <= settings.EVENT_START_TIME:
            return False

        # if task is hidden and no user/not admin:
        # always hide
        if self.hidden:
            return False

        return True

    # @validator('description_html', pre=True, always=True)
    # def set_html(cls, v):
    #     return v or markdown2.markdown(cls.description)

    @staticmethod
    def regenerate_md(content: str) -> str:
        return md.markdownCSS(content, config.MD_CLASSES_TASKS, config.MD_ATTRS_TASKS)

    # it's time for crazy solution.
    # Taken from https://github.com/samuelcolvin/pydantic/issues/619#issuecomment-635784061
    @validator("scoring", pre=True)
    def validate_scoring(cls, value):  # noqa: E0213, N805
        if isinstance(value, EBaseModel):
            return value
        if not isinstance(value, dict):
            raise ValueError("value must be dict")

        classtype = value.get("classtype")
        if classtype == "Scoring":
            return Scoring(**value)
        elif classtype == "StaticScoring":
            return StaticScoring(**value)
        elif classtype == "DynamicKKSScoring":
            return DynamicKKSScoring(**value)
        else:
            raise ValueError(f"Unkonwn classtype {classtype}")

    @validator("flag", pre=True)
    def validate_flag(cls, value):  # noqa: E0213, N805
        if isinstance(value, EBaseModel):
            return value
        if not isinstance(value, dict):
            raise ValueError("value must be dict")

        classtype = value.get("classtype")
        if classtype == "Flag":
            return Flag(**value)
        elif classtype == "StaticFlag":
            return StaticFlag(**value)
        elif classtype == "DynamicKKSFlag":
            return DynamicKKSFlag(**value)
        else:
            raise ValueError(f"Unkonwn classtype {classtype}")

    @staticmethod
    def is_date_after_migration(dt: datetime.datetime) -> bool:
        migration_time = datetime.datetime.fromtimestamp(1605065347)
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

    def last_pwned_str(self):
        last_pwn = max(self.pwned_by.items(), key=lambda x: x[1])

        last_time = datetime.datetime.now() - last_pwn[1]
        result_time = Task.humanize_time(last_time) if Task.is_date_after_migration(last_pwn[1]) else "unknown"

        return last_pwn[0], result_time

    def first_pwned_str(self):
        first_pwn = min(self.pwned_by.items(), key=lambda x: x[1])
        result_time = template_format_time(first_pwn[1])

        return first_pwn[0], result_time

    def short_desc(self):
        return f"task_id={self.task_id} task_name={self.task_name} hidden={self.hidden} points={self.scoring.points}"


class TaskForm(EBaseModel):
    task_name: str
    category: str
    scoring: Union[Scoring, StaticScoring, DynamicKKSScoring]
    description: str
    flag: Union[Flag, StaticFlag, DynamicKKSFlag]
    author: str = ""
