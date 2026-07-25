# ruff: noqa: S101, S106, ANN201 # this is a __test file__

import json

from fastapi import status

from yatb import schema

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
    test_auth.test_admin(client)

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

    client.simple_register_raw(username="Rubikoid_user", password="123456789")

    resp1 = client.solve_task_raw("test_task")
    assert resp1.status_code == status.HTTP_200_OK, resp1.text
    assert resp1.json() == {"task_id": str(tasks[0].task_id), "already_solved": False}, resp1.text

    resp2 = client.solve_task_raw("kks{other_test_task}")
    assert resp2.status_code == status.HTTP_200_OK, resp2.text
    assert resp2.json() == {"task_id": str(tasks[1].task_id), "already_solved": False}, resp2.text

    resp3 = client.solve_task_raw("more_other_test_task}")
    assert resp3.status_code == status.HTTP_200_OK, resp3.text
    assert resp3.json() == {"task_id": str(tasks[2].task_id), "already_solved": False}, resp3.text

    me = client.get_me()
    assert me.score == sum(task.scoring.points for task in tasks.values()), f"{me = }"


def test_task_resolve_is_not_an_error(client: ClientEx):
    """A flag you already own is a 200, not a failure.

    It used to be a 202, which the navbar could only read as "not 200" and therefore
    rendered as a red error toast.
    """
    test_auth.test_admin(client)

    task = client.create_task(
        task_name="ResolveTask",
        category="web",
        scoring=schema.StaticScoring(static_points=100),
        description="resolve",
        flag=schema.StaticFlag(flag_base="kks", flag="resolve_me"),
    )
    task.hidden = False
    task = client.modify_task(task)

    client.simple_register_raw(username="resolver_user", password="123456789")

    first = client.solve_task_raw("resolve_me")
    assert first.status_code == status.HTTP_200_OK, first.text
    assert first.json() == {"task_id": str(task.task_id), "already_solved": False}, first.text

    again = client.solve_task_raw("resolve_me")
    assert again.status_code == status.HTTP_200_OK, again.text
    assert again.json() == {"task_id": str(task.task_id), "already_solved": True}, again.text

    # Re-submitting must not pay out twice.
    me = client.get_me()
    assert me.score == task.scoring.points, f"{me = }"


def test_task_solve_bad_flag(client: ClientEx):
    test_auth.test_admin(client)
    client.simple_register_raw(username="wrong_flag_user", password="123456789")

    resp = client.solve_task_raw("no_such_flag_anywhere")
    assert resp.status_code == status.HTTP_404_NOT_FOUND, resp.text


def test_ui_submit_flag_toasts(client: ClientEx):
    """The htmx twin answers with a toast instead of a status code to interpret."""
    test_auth.test_admin(client)

    task = client.create_task(
        task_name="ToastTask",
        category="web",
        scoring=schema.StaticScoring(static_points=100),
        description="toast",
        flag=schema.StaticFlag(flag_base="kks", flag="toast_me"),
    )
    task.hidden = False
    task = client.modify_task(task)

    client.simple_register_raw(username="toast_user", password="123456789")

    url = app.url_path_for("ui_task_submit_flag")

    accepted = client.post(url, data={"flag": "toast_me"})
    assert accepted.status_code == status.HTTP_200_OK, accepted.text
    trigger = json.loads(accepted.headers["HX-Trigger"])
    assert trigger["yatb:toast"]["kind"] == "success", trigger
    assert trigger["yatb:flag-accepted"] is True, trigger
    # The card comes back as an out-of-band swap so the JS never has to rebuild it.
    assert f'id="task-{task.task_id}"' in accepted.text, accepted.text
    assert 'hx-swap-oob="true"' in accepted.text, accepted.text

    again = client.post(url, data={"flag": "toast_me"})
    assert again.status_code == status.HTTP_200_OK, again.text
    trigger = json.loads(again.headers["HX-Trigger"])
    assert trigger["yatb:toast"]["kind"] == "info", trigger

    wrong = client.post(url, data={"flag": "definitely_not_a_flag"})
    assert wrong.status_code == status.HTTP_200_OK, wrong.text
    trigger = json.loads(wrong.headers["HX-Trigger"])
    assert trigger["yatb:toast"]["kind"] == "danger", trigger
    # A wrong flag stays in the box, so no accept event rides along.
    assert "yatb:flag-accepted" not in trigger, trigger
