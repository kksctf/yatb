from fastapi import status

from yatb.app import app

from . import ClientEx
from . import client as client_cl

client = client_cl

UI_URL = app.url_path_for("api_settings_ui_set")
PROFILE_URL = app.url_path_for("api_settings_profile_set")


def _register(client: ClientEx, username: str = "Rubikoid") -> None:
    resp = client.simple_register_raw(username=username, password="123456789")
    client.check_page_after_login(username, resp)


def test_ui_anon_sets_cookies_only(client: ClientEx):
    resp = client.post(UI_URL, data={"theme": "dark"})
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert client.cookies.get("theme") == "dark", client.cookies


def test_ui_logged_in_persists_to_db(client: ClientEx):
    _register(client)

    resp = client.post(UI_URL, data={"theme": "dark", "lang": "ru"})
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert client.cookies.get("theme") == "dark", client.cookies
    assert client.cookies.get("lang") == "ru", client.cookies

    me = client.get_me()
    assert me.settings.theme == "dark", me
    assert me.settings.lang == "ru", me


def test_login_applies_stored_settings_to_cookies(client: ClientEx):
    """Server wins: whatever this browser picked while logged out is overwritten."""
    _register(client)
    client.post(UI_URL, data={"theme": "dark"})

    # log out, then pick the opposite theme anonymously — let the server write the cookie
    # itself, so it carries the same domain/path the login response will overwrite.
    client.get(app.url_path_for("api_users_logout"))
    client.post(UI_URL, data={"theme": "light"})
    assert client.cookies.get("theme") == "light", client.cookies

    resp = client.simple_login_raw(username="Rubikoid", password="123456789")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert client.cookies.get("theme") == "dark", client.cookies


def test_ui_auto_clears_cookie(client: ClientEx):
    client.post(UI_URL, data={"theme": "dark"})
    assert client.cookies.get("theme") == "dark", client.cookies

    client.post(UI_URL, data={"theme": "auto"})
    assert client.cookies.get("theme") is None, client.cookies


def test_ui_patch_keeps_untouched_field_for_anon(client: ClientEx):
    """The menu posts one control at a time: changing the language must not reset the theme."""
    client.post(UI_URL, data={"theme": "dark"})
    client.post(UI_URL, data={"lang": "ru"})

    assert client.cookies.get("theme") == "dark", client.cookies
    assert client.cookies.get("lang") == "ru", client.cookies


def test_ui_patch_keeps_untouched_field_for_user(client: ClientEx):
    _register(client)
    client.post(UI_URL, data={"theme": "dark"})
    client.post(UI_URL, data={"lang": "ru"})

    me = client.get_me()
    assert me.settings.theme == "dark", me
    assert me.settings.lang == "ru", me


def test_lang_change_asks_for_refresh(client: ClientEx):
    resp = client.post(UI_URL, data={"lang": "ru"})
    assert resp.headers.get("HX-Refresh") == "true", resp.headers

    # theme is applied client-side, so it must not force a reload
    resp = client.post(UI_URL, data={"theme": "dark"})
    assert "HX-Refresh" not in resp.headers, resp.headers


def test_ui_rejects_unknown_theme(client: ClientEx):
    resp = client.post(UI_URL, data={"theme": "neon"})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp.text


def test_profile_requires_login(client: ClientEx):
    resp = client.post(PROFILE_URL, data={"affiliation": "KKS", "country": "RU"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED, resp.text


def test_profile_saves_extra_info(client: ClientEx):
    _register(client)

    resp = client.post(PROFILE_URL, data={"affiliation": "  KKS  ", "country": "ru"})
    assert resp.status_code == status.HTTP_200_OK, resp.text

    me = client.get_me()
    assert me.extra_info.affiliation == "KKS", me
    assert me.extra_info.country == "RU", me


def test_profile_rejects_unknown_country(client: ClientEx):
    _register(client)

    resp = client.post(PROFILE_URL, data={"affiliation": "KKS", "country": "XX"})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp.text


def test_profile_keeps_profile_pic(client: ClientEx):
    """profile_pic is not part of the form, so saving the form must not wipe it."""
    _register(client)

    with client._portal_factory() as portal:  # noqa: SLF001
        portal.call(_set_profile_pic, "Rubikoid", "http://example.com/pic.png")

    resp = client.post(PROFILE_URL, data={"affiliation": "KKS", "country": "RU"})
    assert resp.status_code == status.HTTP_200_OK, resp.text

    me = client.get_me()
    assert me.extra_info.profile_pic == "http://example.com/pic.png", me
    assert me.extra_info.affiliation == "KKS", me


async def _set_profile_pic(username: str, url: str) -> None:
    from yatb.db import UserDB

    user = await UserDB.find_by_username(username)
    assert user is not None
    user.extra_info.profile_pic = url
    await user.save()
