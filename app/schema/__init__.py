import logging

from ..utils.log_helper import get_logger

logger = get_logger("schema")

# isort: off
from .ebasemodel import EBaseModel  # noqa

from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth  # noqa
from .flags import DynamicKKSFlag, Flag, StaticFlag  # noqa
from .scoring import DynamicKKSScoring, Scoring, StaticScoring  # noqa
from .user import User  # noqa
from .task import Task, TaskForm  # noqa

# isort: on


class FlagForm(EBaseModel):
    flag: str


# for i in [Task, User]:
#     logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
