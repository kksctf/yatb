import pytest
import uuid
from . import client as client_cl, app, test_auth, TestClient
from .. import schema

client = client_cl


def test_task_create(client: TestClient):
    test_auth.test_admin(client)
    resp1 = client.post(
        app.url_path_for("api_admin_task_create"),
        data=schema.TaskForm(
            task_name="TestTast1",
            category="web",
            scoring=schema.StaticScoring(static_points=1337),
            description="test_task_decription",
            flag=schema.StaticFlag(flag_base="kks", flag="test_task"),
        ).json(),
        headers={"Content-Type": "application/json"},
    )
    assert resp1.status_code == 200, resp1.text

    resp2 = client.post(
        app.url_path_for("api_admin_task_create"),
        data=schema.TaskForm(
            task_name="TestTast2",
            category="pwn",
            scoring=schema.StaticScoring(static_points=1338),
            description="second_test_task_description",
            flag=schema.StaticFlag(flag_base="kks", flag="other_test_task"),
        ).json(),
        headers={"Content-Type": "application/json"},
    )
    assert resp2.status_code == 200, resp2.text

    resp3 = client.get(app.url_path_for("api_admin_tasks"))
    assert resp3.status_code == 200, resp3.text
    assert resp1.json()["task_id"] in resp3.json(), resp3.json()
    assert resp2.json()["task_id"] in resp3.json(), resp3.json()

    resp4 = client.get(app.url_path_for("api_tasks_get"))
    assert resp4.status_code == 200, resp4.text
    assert len(resp4.json()) == 2, resp4.json()

    for task_id, task in resp3.json().items():
        task_obj = schema.Task(**task)
        task_obj.hidden = False
        resp_show = client.post(
            app.url_path_for("api_admin_task_edit", task_id=str(task_obj.task_id)), data=task_obj.json(), headers={"Content-Type": "application/json"}
        )
        assert resp_show.status_code == 200, f"{task['task_name']} {resp_show.text}"

    resp5 = client.get(app.url_path_for("api_tasks_get"))
    assert resp5.status_code == 200, resp4.text
    assert "flag" not in resp5.json()[0]
    assert "flag" not in resp5.json()[1]

    assert resp5.json()[0]["task_id"] in [resp1.json()["task_id"], resp2.json()["task_id"]], resp4.json()
    assert resp5.json()[1]["task_id"] in [resp1.json()["task_id"], resp2.json()["task_id"]], resp4.json()
