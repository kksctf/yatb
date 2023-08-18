# ruff: noqa: S101, S106, ANN201, T201 # this is a __test file__

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from .. import app, config, schema
from ..config import settings

# this disables real connection to db/creating db-in-file, and forces to use only in-memory db
settings.DB_NAME = None  # type: ignore

LoginForm = schema.SimpleAuth.Form._Internal  # noqa: SLF001


class ClientExRaw(TestClient):
    def simple_register_raw(self, username: str, password: str) -> Response:
        return self.post(
            app.url_path_for("api_auth_simple_register"),
            json=LoginForm(username=username, password=password).model_dump(mode="json"),
        )

    def simple_login_raw(self, username: str, password: str) -> Response:
        return self.post(
            app.url_path_for("api_auth_simple_login"),
            json=LoginForm(username=username, password=password).model_dump(mode="json"),
        )

    def create_task_raw(  # noqa: PLR0913
        self,
        task_name: str,
        category: str,
        scoring: schema.ScoringUnion,
        description: str,
        flag: schema.FlagUnion,
    ) -> Response:
        return self.post(
            app.url_path_for("api_admin_task_create"),
            json=schema.TaskForm(
                task_name=task_name,
                category=category,
                scoring=scoring,
                description=description,
                flag=flag,
            ).model_dump(mode="json"),
        )

    def modify_task_raw(self, task: schema.Task) -> Response:
        return self.post(
            app.url_path_for("api_admin_task_edit", task_id=task.task_id),
            json=task.model_dump(mode="json"),
        )

    def solve_task_raw(self, flag: str) -> Response:
        return self.post(
            app.url_path_for("api_task_submit_flag"),
            json=schema.FlagForm(flag=flag).model_dump(mode="json"),
        )

    def get_me_raw(self) -> Response:
        return self.get(app.url_path_for("api_users_me"))


class ClientEx(ClientExRaw):
    # def simple_register(self, username: str, password: str) -> schema.User:
    #     resp = self.simple_register_raw(username=username, password=password)
    #     resp.raise_for_status()
    #     return schema.User.public_model().model_validate(resp.json())

    # def simple_login(self, username: str, password: str) -> schema.User:
    #     resp = self.simple_login_raw(username=username, password=password)
    #     resp.raise_for_status()
    #     return schema.User.public_model().model_validate(resp.json())

    def create_task(  # noqa: PLR0913
        self,
        task_name: str,
        category: str,
        scoring: schema.ScoringUnion,
        description: str,
        flag: schema.FlagUnion,
    ) -> schema.Task:
        resp = self.create_task_raw(
            task_name=task_name,
            category=category,
            scoring=scoring,
            description=description,
            flag=flag,
        )
        resp.raise_for_status()

        return schema.Task.admin_model().model_validate(resp.json())

    def modify_task(self, task: schema.Task) -> schema.Task:
        resp = self.modify_task_raw(task=task)
        resp.raise_for_status()

        return schema.Task.admin_model().model_validate(resp.json())

    def get_me(self) -> schema.User:
        resp = self.get_me_raw()
        resp.raise_for_status()

        return schema.User.public_model().model_validate(resp.json())


@pytest.fixture()
def client(request):
    print("Client init")
    client = ClientEx(app).__enter__()

    yield client

    print("Client shutdown")
    client.__exit__()


# from . import test_auth  # noqa
# from . import test_main  # noqa
