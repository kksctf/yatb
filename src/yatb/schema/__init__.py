from pydantic import BaseModel

from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth
from .flags import DynamicKKSFlag, Flag, FlagCheckResult, StaticFlag
from .ids import TaskID, UserID
from .scoring import DynamicKKSScoring, Scoring, StaticScoring
from .task import DynamicTaskFeatures, DynamicTaskInfo, FlagUnion, ScoringUnion, Task, TaskForm
from .ui import LangPref, Theme, UISettings
from .user import ExtraInfo, User


class FlagForm(BaseModel):
    flag: str


# for i in [Task, User]:
#     logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
