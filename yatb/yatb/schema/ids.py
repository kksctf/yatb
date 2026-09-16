import uuid
from typing import Annotated, NewType

from pydantic import Field

TaskID = NewType("TaskID", uuid.UUID)
TaskIDField = Field(default_factory=lambda: TaskID(uuid.uuid4()))
type ModelTaskID = Annotated[TaskID, TaskIDField]

UserID = NewType("UserID", uuid.UUID)
UserIDField = Field(default_factory=lambda: UserID(uuid.uuid4()))
type ModelUserID = Annotated[UserID, UserIDField]
