import gettext
import shutil
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from babel.messages.catalog import Catalog
from babel.messages.extract import extract
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jinja2 import DictLoader

from contrib.update_private_catalog import private_template, update_private_catalogs
from yatb import i18n
from yatb.ui import UISettingsMiddleware, get_ui_state


def test_private_catalog_update(tmp_path: Path):
    directory = tmp_path / "ru" / "LC_MESSAGES"
    directory.mkdir(parents=True)
    public = Catalog(locale="ru")
    public.add("Public", "Общее")
    public.add("Override", "Общее")
    public.add("Promoted", "Общее")
    private = Catalog(locale="ru")
    private.add("Override", "Замена")
    private.add("Promoted", "Приватное")
    private.add("Removed", "Удалено")
    extracted = Catalog()
    for message in ["Public", "Override", "Promoted", "New"]:
        extracted.add(message)
    template = tmp_path / "all.pot"
    for path, catalog in [
        (directory / "messages.po", public),
        (directory / "private.po", private),
        (template, extracted),
    ]:
        with path.open("wb") as stream:
            write_po(stream, catalog)
    public_before = (directory / "messages.po").read_bytes()
    update_private_catalogs(template, tmp_path)
    update_private_catalogs(template, tmp_path)
    assert (directory / "messages.po").read_bytes() == public_before
    with (directory / "private.po").open("rb") as stream:
        result = read_po(stream, locale="ru")
    assert result.get("Public") is None
    new = result.get("New")
    override = result.get("Override")
    promoted = result.get("Promoted")
    assert new is not None
    assert override is not None
    assert promoted is not None
    assert new.string == ""
    assert override.string == "Замена"
    assert promoted.string == "Приватное"
    assert "Removed" in result.obsolete


def test_filter_context_and_plurals():
    extracted, public, private = Catalog(), Catalog(), Catalog()
    for catalog in [extracted, public]:
        catalog.add(("item", "items"))
        catalog.add("Open", context="verb")
    extracted.add("Open", context="adjective")
    private.add(("item", "items"))
    result = private_template(extracted, public, private)
    item = result.get("item")
    assert item is not None
    assert item.id == ("item", "items")
    assert result.get("Open", "verb") is None
    assert result.get("Open", "adjective") is not None


@pytest.mark.parametrize("with_private", [False, True])
def test_runtime_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, with_private: bool):
    directory = tmp_path / "en" / "LC_MESSAGES"
    directory.mkdir(parents=True)
    public = Catalog(locale="en")
    public.add("Shared", "Public")
    public.add("Public only", "Public fallback")
    public.add(("item", "items"), ("public item", "public items"))
    private = Catalog(locale="en")
    private.add("Shared", "Private")
    private.add("Private only", "Private addition")
    private.add(("item", "items"), ("private item", "private items"))
    catalogs = {"messages": public}
    if with_private:
        catalogs["private"] = private
    for domain, catalog in catalogs.items():
        with (directory / f"{domain}.mo").open("wb") as stream:
            write_mo(stream, catalog)
    monkeypatch.setattr(i18n, "_LOCALE_DIR", tmp_path)
    translation = i18n._load_translation("en")  # noqa: SLF001
    assert translation.gettext("Shared") == ("Private" if with_private else "Public")
    assert translation.gettext("Public only") == "Public fallback"
    assert translation.gettext("Private only") == ("Private addition" if with_private else "Private only")
    assert translation.gettext("Unknown") == "Unknown"
    assert translation.ngettext("item", "items", 2) == ("private items" if with_private else "public items")


@pytest.mark.parametrize("method", ["python", "jinja2"])
def test_common_extraction(method: str):
    source = b'_("Shared"); ngettext("item", "items", 2)'
    if method == "jinja2":
        source = b'{{ _("Shared") }} {{ ngettext("item", "items", 2) }}'
    messages = [entry[1] for entry in extract(method, BytesIO(source))]
    assert messages == ["Shared", ("item", "items")]


@pytest.mark.parametrize(
    ("query", "cookie", "theme", "expected", "preference"),
    [
        ("ru", "en", "dark", "ru", "ru"),
        (None, "auto", "neon", "ru", "auto"),
        ("bad", "en", "light", "en", "en"),
        (None, "bad", "auto", "ru", "auto"),
    ],
)
def test_ui_preferences(query: str | None, cookie: str, theme: str, expected: str, preference: str):
    app = FastAPI()
    app.add_middleware(UISettingsMiddleware)

    @app.get("/")
    async def state(request: Request) -> dict:
        ui = get_ui_state(request)
        assert ui.lang == i18n.get_lang()
        return {"lang": ui.lang, "preference": ui.lang_pref, "theme": ui.theme}

    with TestClient(app) as client:
        client.cookies.update({"lang": cookie, "theme": theme})
        response = client.get("/", params={"lang": query} if query else {}, headers={"Accept-Language": "ru"})
    assert response.json() == {
        "lang": expected,
        "preference": preference,
        "theme": "auto" if theme == "neon" else theme,
    }
    assert ("set-cookie" in response.headers) == (query == "ru")


def test_initial_private_catalog(tmp_path: Path):
    directory = tmp_path / "en" / "LC_MESSAGES"
    directory.mkdir(parents=True)
    public = Catalog(locale="en")
    public.add("Shared", "Public")
    with (directory / "messages.po").open("wb") as stream:
        write_po(stream, public)
    template = tmp_path / "all.pot"
    with template.open("wb") as stream:
        write_po(stream, public)
    update_private_catalogs(template, tmp_path)
    assert not (directory / "private.po").exists()
    public.add("Private only")
    with template.open("wb") as stream:
        write_po(stream, public)
    update_private_catalogs(template, tmp_path)
    with (directory / "private.po").open("rb") as stream:
        private = read_po(stream, locale="en")
    assert private.get("Private only") is not None
    assert private.get("Shared") is None


def test_ui_state_template_context(monkeypatch: pytest.MonkeyPatch):
    from yatb.view.util import response_generator, templates

    for name in templates.env.list_templates():
        templates.env.get_template(name)
    monkeypatch.setattr(
        templates.env,
        "loader",
        DictLoader({"probe.jhtml": "{{ ui.lang }}|{{ ui.lang_pref }}|{{ ui.theme }}|{{ current_language() }}"}),
    )
    monkeypatch.setitem(templates.env.globals, "current_language", i18n.get_lang)
    app = FastAPI()
    app.add_middleware(UISettingsMiddleware)

    @app.get("/")
    async def page(request: Request):  # noqa: ANN202
        return await response_generator(request, "probe.jhtml")

    with TestClient(app) as client:
        assert client.get("/", headers={"Accept-Language": "ru"}).text == "ru|auto|auto|ru"
        client.cookies.set("theme", "dark")
        assert client.get("/?lang=en").text == "en|en|dark|en"


@pytest.mark.parametrize("mode", ["public", "private", "invalid"])
def test_wheel_compiles_private_catalog(tmp_path: Path, mode: str):
    root = Path(__file__).resolve().parents[1]
    for name in ["pyproject.toml", "README.md", "LICENSE"]:
        shutil.copy(root / name, tmp_path / name)
    for name in ["src", "contrib"]:
        shutil.copytree(
            root / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("*.mo", "__pycache__", ".pybabel.info"),
        )
    private = Catalog(locale="en", fuzzy=False)
    private.add("Shared", "Private")
    if mode == "invalid":
        private.add("Hello %(name)s", "Hello %(wrong)s", flags=["python-format"])
    path = tmp_path / "src/yatb/locale/en/LC_MESSAGES/private.po"
    if mode != "public":
        with path.open("wb") as stream:
            write_po(stream, private)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if mode == "invalid":
        assert result.returncode != 0
        assert "Failed to compile" in result.stderr
        return
    assert result.returncode == 0, result.stdout + result.stderr
    wheel = next((tmp_path / "dist").glob("*.whl"))
    with ZipFile(wheel) as archive:
        assert "yatb/locale/en/LC_MESSAGES/messages.mo" in archive.namelist()
        if mode == "public":
            assert "yatb/locale/en/LC_MESSAGES/private.mo" not in archive.namelist()
            return
        translation = gettext.GNUTranslations(BytesIO(archive.read("yatb/locale/en/LC_MESSAGES/private.mo")))
    assert translation.gettext("Shared") == "Private"
