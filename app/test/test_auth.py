import pytest
import datetime
import hmac
import hashlib

from . import client as client_cl, app, TestClient
from .. import schema, config

client = client_cl


def test_register(client: TestClient):
    resp = client.post(app.url_path_for("api_users_register"), json=schema.UserForm(username="Rubikoid", password="123").dict())
    assert resp.status_code == 200, resp.text
    assert resp.text == '"ok"', resp.text


def test_login(client: TestClient):
    test_register(client)
    resp = client.post(app.url_path_for("api_token"), json=schema.UserForm(username="Rubikoid", password="123").dict())
    assert resp.status_code == 200, resp.text
    assert resp.text == '"ok"', resp.text


def test_admin(client: TestClient):
    test_login(client)
    resp = client.get(app.url_path_for("api_admin_users_me"))
    # print(resp.json())
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_admin"] is True, resp.json()
    assert resp.json()["username"] == "Rubikoid", resp.json()


def test_admin_fail(client: TestClient):
    resp1 = client.post(app.url_path_for("api_users_register"), json=schema.UserForm(username="Not_Rubikoid", password="123").dict())
    assert resp1.status_code == 200, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.post(app.url_path_for("api_token"), json=schema.UserForm(username="Not_Rubikoid", password="123").dict())
    assert resp2.status_code == 200, resp2.text
    assert resp2.text == '"ok"', resp2.text

    resp3 = client.get(app.url_path_for("api_admin_users_me"))
    assert resp3.status_code == 403, resp3.text


def test_not_existing_user(client: TestClient):
    resp1 = client.post(app.url_path_for("api_token"), json=schema.UserForm(username="Not_Existing_Account", password="123").dict())
    assert resp1.status_code == 401, resp1.text


def test_invalid_password(client: TestClient):
    resp1 = client.post(app.url_path_for("api_users_register"), json=schema.UserForm(username="Not_Rubikoid", password="123").dict())
    assert resp1.status_code == 200, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.post(app.url_path_for("api_token"), json=schema.UserForm(username="Not_Rubikoid", password="1234").dict())
    assert resp2.status_code == 401, resp2.text


def test_register_existing_user(client: TestClient):
    resp1 = client.post(app.url_path_for("api_users_register"), json=schema.UserForm(username="Not_Rubikoid", password="123").dict())
    assert resp1.status_code == 200, resp1.text
    assert resp1.text == '"ok"', resp1.text

    resp2 = client.post(app.url_path_for("api_users_register"), json=schema.UserForm(username="Not_Rubikoid", password="1234").dict())
    assert resp2.status_code == 403, resp2.text
