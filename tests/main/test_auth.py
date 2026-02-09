from fastapi import status

from yatb import schema

from . import ClientEx, app, enable_debug
from . import client as client_cl

client = client_cl

LoginForm = schema.SimpleAuth.Form


def test_register(client: ClientEx):
    resp = client.simple_register_raw(username="Rubikoid", password="123456789")
    client.check_page_after_login("Rubikoid", resp)


def test_login(client: ClientEx):
    test_register(client)
    resp = client.simple_login_raw(username="Rubikoid", password="123456789")
    client.check_page_after_login("Rubikoid", resp)


def test_admin(client: ClientEx):
    # need to enable debug here, because `Rubikoid-as-default-admin` is debug feature
    with enable_debug():
        test_login(client)

    resp = client.get(app.url_path_for("api_admin_users_me"))
    # print(resp.json())
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json()["is_admin"] is True, resp.json()
    assert resp.json()["username"] == "Rubikoid", resp.json()


def test_not_admin_without_debug(client: ClientEx):
    test_login(client)
    resp = client.get(app.url_path_for("api_admin_users_me"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.text


def test_admin_fail(client: ClientEx):
    with enable_debug():
        resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123456789")
        client.check_page_after_login("Not_Rubikoid", resp1)

        resp2 = client.simple_login_raw(username="Not_Rubikoid", password="123456789")
        client.check_page_after_login("Not_Rubikoid", resp2)

        resp3 = client.get(app.url_path_for("api_admin_users_me"))
        assert resp3.status_code == status.HTTP_403_FORBIDDEN, resp3.text


def test_not_existing_user(client: ClientEx):
    resp1 = client.post(
        app.url_path_for("api_auth_simple_login"),
        data=LoginForm(username="Not_Existing_Account", password="123456789").model_dump(mode="json"),
    )
    assert resp1.status_code == status.HTTP_401_UNAUTHORIZED, resp1.text


def test_invalid_password(client: ClientEx):
    resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123456789")
    client.check_page_after_login("Not_Rubikoid", resp1)

    resp2 = client.simple_login_raw(username="Not_Rubikoid", password="1234567890")
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED, resp2.text


def test_register_existing_user(client: ClientEx):
    resp1 = client.simple_register_raw(username="Not_Rubikoid", password="123456789")
    client.check_page_after_login("Not_Rubikoid", resp1)

    resp2 = client.simple_register_raw(username="Not_Rubikoid", password="1234567890")
    assert resp2.status_code == status.HTTP_403_FORBIDDEN, resp2.text
