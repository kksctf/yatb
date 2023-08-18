# ruff: noqa: S101, S106, ANN201 # this is a __test file__

from fastapi import status

from .. import config, schema
from . import ClientEx, app
from . import client as client_cl

client = client_cl

LoginForm = schema.SimpleAuth.Form._Internal  # noqa: SLF001


def test_register(client: ClientEx):
    resp = client.simple_register_raw(username="Rubikoid", password="123")

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.text == '"ok"', resp.text


def test_login(client: ClientEx):
    test_register(client)
    resp = client.simple_login_raw(username="Rubikoid", password="123")

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.text == '"ok"', resp.text


def test_admin(client: ClientEx):
    # config.settings.DEBUG = True
    test_login(client)
    # config.settings.DEBUG = False
    resp = client.get(app.url_path_for("api_admin_users_me"))
    # print(resp.json())
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json()["is_admin"] is True, resp.json()
    assert resp.json()["username"] == "Rubikoid", resp.json()


def test_admin_fail(client: ClientEx):
    resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123")
    assert resp1.status_code == status.HTTP_200_OK, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.simple_login_raw(username="Not_Rubikoid", password="123")
    assert resp2.status_code == status.HTTP_200_OK, resp2.text
    assert resp2.text == '"ok"', resp2.text

    resp3 = client.get(app.url_path_for("api_admin_users_me"))
    assert resp3.status_code == status.HTTP_403_FORBIDDEN, resp3.text


def test_not_existing_user(client: ClientEx):
    resp1 = client.post(
        app.url_path_for("api_auth_simple_login"),
        json=LoginForm(username="Not_Existing_Account", password="123").model_dump(mode="json"),
    )
    assert resp1.status_code == status.HTTP_401_UNAUTHORIZED, resp1.text


def test_invalid_password(client: ClientEx):
    resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123")
    assert resp1.status_code == status.HTTP_200_OK, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.simple_login_raw(username="Not_Rubikoid", password="1234")
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED, resp2.text


def test_register_existing_user(client: ClientEx):
    resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123")
    assert resp1.status_code == status.HTTP_200_OK, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.simple_register_raw(username="Not_Rubikoid", password="1234")
    assert resp2.status_code == status.HTTP_403_FORBIDDEN, resp2.text
