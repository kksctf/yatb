import uuid
from typing import Annotated, NewType, TypeAlias

from pydantic import Field

TaskID = NewType("TaskID", uuid.UUID)
TaskIDField = Field(default_factory=lambda: TaskID(uuid.uuid4()))
ModelTaskID: TypeAlias = Annotated[TaskID, TaskIDField]  # noqa: UP040

UserID = NewType("UserID", uuid.UUID)
UserIDField = Field(default_factory=lambda: UserID(uuid.uuid4()))
ModelUserID: TypeAlias = Annotated[UserID, UserIDField]  # noqa: UP040
