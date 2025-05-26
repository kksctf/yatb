# ruff: noqa: S101, S106, ANN201 # this is a __test file__

from fastapi import status

from .. import schema
from . import ClientEx, app, test_auth
from . import client as client_cl

client = client_cl


def test_task_create(client: ClientEx):
    test_auth.test_admin(client)

    resp1 = client.create_task_raw(
        task_name="TestTast1",
        category="web",
        scoring=schema.StaticScoring(static_points=1337),
        description="test_task_decription",
        flag=schema.StaticFlag(flag_base="kks", flag="test_task"),
    )
    assert resp1.status_code == status.HTTP_200_OK, resp1.text

    resp2 = client.create_task_raw(
        task_name="TestTast2",
        category="pwn",
        scoring=schema.StaticScoring(static_points=1338),
        description="second_test_task_description",
        flag=schema.StaticFlag(flag_base="kks", flag="other_test_task"),
    )
    assert resp2.status_code == status.HTTP_200_OK, resp2.text

    resp1_1 = client.get(app.url_path_for("api_admin_task_get", task_id=resp1.json()["task_id"]))
    assert resp1_1.status_code == status.HTTP_200_OK, resp1_1.text
    assert resp1_1.json()["task_id"] == resp1.json()["task_id"], resp1.json()
    assert resp1_1.json()["task_name"] == "TestTast1", resp1.json()
    assert resp1_1.json()["category"] == "web", resp1.json()
    assert resp1_1.json()["description"] == "test_task_decription", resp1.json()

    resp3 = client.get(app.url_path_for("api_admin_tasks"))
    assert resp3.status_code == status.HTTP_200_OK, resp3.text
    assert resp1.json()["task_id"] in resp3.json(), resp3.json()
    assert resp2.json()["task_id"] in resp3.json(), resp3.json()

    resp4 = client.get(app.url_path_for("api_tasks_get"))
    assert resp4.status_code == status.HTTP_200_OK, resp4.text
    assert len(resp4.json()) == 2, resp4.json()  # noqa: PLR2004

    for task in resp3.json().values():
        task_obj = schema.Task(**task)
        task_obj.hidden = False
        resp_show = client.post(
            app.url_path_for("api_admin_task_edit", task_id=task_obj.task_id),
            json=task_obj.model_dump(mode="json"),
        )
        assert resp_show.status_code == status.HTTP_200_OK, f"{task['task_name']} {resp_show.text}"

    resp5 = client.get(app.url_path_for("api_tasks_get"))
    assert resp5.status_code == status.HTTP_200_OK, resp5.text
    assert "flag" not in resp5.json()[0]
    assert "flag" not in resp5.json()[1]
    assert "flag" not in resp5.text

    assert resp5.json()[0]["task_id"] in [resp1.json()["task_id"], resp2.json()["task_id"]], resp4.json()
    assert resp5.json()[1]["task_id"] in [resp1.json()["task_id"], resp2.json()["task_id"]], resp4.json()


def test_task_solve(client: ClientEx):
    client.simple_register_raw(username="Rubikoid", password="123")

    tasks: dict[int, schema.Task] = {}  # fake array ;)
    tasks[0] = client.create_task(
        task_name="TestTast1",
        category="web",
        scoring=schema.StaticScoring(static_points=1337),
        description="test_task_decription",
        flag=schema.StaticFlag(flag_base="kks", flag="test_task"),
    )
    tasks[1] = client.create_task(
        task_name="TestTast2",
        category="pwn",
        scoring=schema.StaticScoring(static_points=1338),
        description="second_test_task_description",
        flag=schema.StaticFlag(flag_base="kks", flag="other_test_task"),
    )
    tasks[2] = client.create_task(
        task_name="TestTast2",
        category="pwn",
        scoring=schema.StaticScoring(static_points=1339),
        description="second_test_task_description",
        flag=schema.StaticFlag(flag_base="kks", flag="more_other_test_task"),
    )

    for i, task in tasks.items():
        task.hidden = False
        tasks[i] = client.modify_task(task)
        task = tasks[i]
        assert not task.hidden, f"{task = }"

    client.simple_register_raw(username="Rubikoid_user", password="123")

    resp1 = client.solve_task_raw("test_task")
    assert resp1.status_code == status.HTTP_200_OK, resp1.text
    assert resp1.text.replace('"', "") == str(tasks[0].task_id), resp1.text

    resp2 = client.solve_task_raw("kks{other_test_task}")
    assert resp2.status_code == status.HTTP_200_OK, resp2.text
    assert resp2.text.replace('"', "") == str(tasks[1].task_id), resp2.text

    resp3 = client.solve_task_raw("more_other_test_task}")
    assert resp3.status_code == status.HTTP_200_OK, resp3.text
    assert resp3.text.replace('"', "") == str(tasks[2].task_id), resp3.text

    me = client.get_me()
    assert me.score == sum(task.scoring.points for task in tasks.values()), f"{me = }"
