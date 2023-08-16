from ..utils.log_helper import get_logger
from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth
from .ebasemodel import EBaseModel
from .flags import DynamicKKSFlag, Flag, StaticFlag
from .scoring import DynamicKKSScoring, Scoring, StaticScoring
from .task import Task, TaskForm
from .user import User

logger = get_logger("schema")


class FlagForm(EBaseModel):
    flag: str


# for i in [Task, User]:
#     logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
