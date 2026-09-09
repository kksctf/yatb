# ruff: noqa: S101, S106, ANN201 # this is a __test file__

from fastapi import status

from yatb import schema

from . import ClientEx, app, test_auth
from . import client as client_cl

client = client_cl

FLAG = "debug_block_test_flag"


def _make_visible_task(client: ClientEx) -> schema.Task:
    task = client.create_task(
        task_name="DebugBlockTask",
        category="web",
        scoring=schema.StaticScoring(static_points=1337),
        description="task for the admin debug block",
        flag=schema.StaticFlag(flag_base="kks", flag=FLAG),
    )
    task.hidden = False
    return client.modify_task(task)


def test_debug_block_for_admin(client: ClientEx):
    test_auth.test_admin(client)
    task = _make_visible_task(client)

    resp = client.get(app.url_path_for("api_admin_task_debug", task_id=task.task_id))
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert "task-debug" in resp.text, resp.text
    assert "debug-secret" in resp.text, resp.text
    assert FLAG in resp.text, resp.text


def test_no_debug_block_for_user(client: ClientEx):
    test_auth.test_admin(client)
    task = _make_visible_task(client)

    client.simple_register_raw(username="Rubikoid_user", password="123456789")

    resp = client.get(app.url_path_for("api_admin_task_debug", task_id=task.task_id))
    assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.text
    assert FLAG not in resp.text, resp.text

    resp = client.get(app.url_path_for("tasks_page"))
    assert resp.status_code == status.HTTP_200_OK, resp.text
    # the card itself is rendered, only the debug parts are gone
    assert task.task_name in resp.text, resp.text
    assert "task-debug" not in resp.text, resp.text
    assert "debug-secret" not in resp.text, resp.text
    assert FLAG not in resp.text, resp.text
