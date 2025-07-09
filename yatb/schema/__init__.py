from ..utils.log_helper import get_logger
from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth
from .ebasemodelv2 import EBaseModelV2
from .flags import DynamicKKSFlag, Flag, StaticFlag
from .scoring import DynamicKKSScoring, Scoring, StaticScoring
from .task import FlagUnion, ScoringUnion, Task, TaskForm
from .user import User


__all__ = [
    "FlagForm",
    "Task",
    "TaskForm",
    "User",
]

logger = get_logger("schema")


class FlagForm(EBaseModelV2):
    flag: str


# for i in [Task, User]:
#     logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
