import uuid

from pydantic import BaseModel, RootModel

from yatb import schema


class FileTask(BaseModel):
    name: str
    description: str

    @property
    def full_name(self) -> str:
        return self.name

    def get_form(self) -> schema.TaskForm:
        return schema.TaskForm()


AllUsers = RootModel[dict[uuid.UUID, schema.User.admin_model]]
AllTasks = RootModel[dict[uuid.UUID, schema.Task.admin_model]]
