import typing
from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response

from yatb import schema
from yatb.app import app
from yatb.config import settings
from yatb.db import db
from yatb.schema.feature_flags import active_feature_flags

settings.DB_NAME = "yatb_testing"
active_feature_flags.force_rename = False

LoginForm = schema.SimpleAuth.Form


class ClientExRaw(TestClient):
    def __enter__(self) -> typing.Self:
        super().__enter__()
        self.drop_db()
        return self

    def simple_register_raw(self, username: str, password: str) -> Response:
        return self.post(
            app.url_path_for("api_auth_simple_register"),
            data=LoginForm(username=username, password=password).model_dump(mode="json"),
        )

    def simple_login_raw(self, username: str, password: str) -> Response:
        return self.post(
            app.url_path_for("api_auth_simple_login"),
            data=LoginForm(username=username, password=password).model_dump(mode="json"),
        )

    def check_page_after_login(self, username: str, resp: Response) -> None:
        assert resp.status_code == status.HTTP_200_OK, resp.text
        assert "sampl3_fl4g" in resp.text, resp.text
        assert f"""<a class="navbar-item" href="http://testserver/profile">{username}</a>""" in resp.text, resp.text

    def create_task_raw(
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
            data=schema.FlagForm(flag=flag).model_dump(mode="json"),
        )

    def get_me_raw(self) -> Response:
        return self.get(app.url_path_for("api_users_me"))

    def drop_db(self) -> None:
        with self._portal_factory() as portal:
            print("Drop DB")
            portal.call(db.reset_db)


class ClientEx(ClientExRaw):
    # def simple_register(self, username: str, password: str) -> schema.User:
    #     resp = self.simple_register_raw(username=username, password=password)
    #     resp.raise_for_status()
    #     return schema.User.public_model().model_validate(resp.json())

    # def simple_login(self, username: str, password: str) -> schema.User:
    #     resp = self.simple_login_raw(username=username, password=password)
    #     resp.raise_for_status()
    #     return schema.User.public_model().model_validate(resp.json())

    def create_task(
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

        return schema.Task.admin_model.model_validate(resp.json())

    def modify_task(self, task: schema.Task) -> schema.Task:
        resp = self.modify_task_raw(task=task)
        resp.raise_for_status()

        return schema.Task.admin_model.model_validate(resp.json())

    def get_me(self) -> schema.User:
        resp = self.get_me_raw()
        resp.raise_for_status()

        return schema.User.public_model.model_validate(resp.json())


@pytest.fixture
def client() -> typing.Generator[ClientEx, typing.Any, None]:
    print("Client init")
    client = ClientEx(app).__enter__()

    yield client

    print("Client shutdown")
    client.__exit__()


@contextmanager
def enable_debug() -> typing.Generator[None, typing.Any, None]:
    settings.DEBUG = True
    try:
        yield
    finally:
        settings.DEBUG = False
