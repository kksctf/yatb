from typing import Annotated, Literal

from beanie.operators import Set
from fastapi import APIRouter, Form, Request, Response
from pydantic import BaseModel, field_validator

from yatb import auth, i18n
from yatb.db import UserDB
from yatb.i18n import translate as _
from yatb.schema.ui import LangPref, Theme, UISettings
from yatb.schema.user import ExtraInfo
from yatb.toasts import Toast, ToastKind, toast_header
from yatb.utils.countries import VALID_COUNTRIES

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

AFFILIATION_MAX_LEN = 128


class UISettingsPatch(BaseModel):
    """Tier-1 patch: the menu posts one control at a time, so both fields are optional."""

    theme: Theme | None = None
    lang: LangPref | None = None


class ExtraInfoForm(BaseModel):
    """Tier-2 form: the whole block is saved at once."""

    affiliation: str = ""
    country: str = ""

    @field_validator("affiliation")
    @classmethod
    def _trim_affiliation(cls, value: str) -> str:
        value = value.strip()
        if len(value) > AFFILIATION_MAX_LEN:
            raise ValueError(f"affiliation is longer than {AFFILIATION_MAX_LEN} characters")
        return value

    @field_validator("country")
    @classmethod
    def _check_country(cls, value: str) -> str:
        value = value.strip().upper()
        if value and value not in VALID_COUNTRIES:
            raise ValueError("unknown country code")
        return value


def _set_pref_cookie(resp: Response, name: str, value: str) -> None:
    # "auto" is the absence of a choice, so it is stored as the absence of a cookie —
    # that way LocaleMiddleware falls back to Accept-Language / prefers-color-scheme.
    if value == i18n.AUTO:
        resp.delete_cookie(name, samesite="lax")
    else:
        resp.set_cookie(name, value, max_age=i18n.COOKIE_MAX_AGE, samesite="lax")


def apply_ui_settings_cookies(resp: Response, ui: UISettings) -> None:
    _set_pref_cookie(resp, "lang", ui.lang)
    _set_pref_cookie(resp, "theme", ui.theme)


@router.post("/ui")
async def api_settings_ui_set(
    req: Request,
    resp: Response,
    user: auth.CURR_USER_SAFE,
    patch: Annotated[UISettingsPatch, Form()],
) -> Literal["ok"]:
    """Tier-1. Works without a login: anonymous visitors get cookies only."""
    # The menu posts one control at a time, so the untouched fields have to be carried
    # over: from the DB when there is a user, otherwise from the cookies this request
    # arrived with (LocaleMiddleware already validated them). Falling back to defaults
    # here would reset the theme every time the language is changed, and vice versa.
    current = user.settings if user else UISettings(theme=req.state.theme, lang=req.state.lang_pref)
    merged = current.model_copy(update=patch.model_dump(exclude_none=True))

    apply_ui_settings_cookies(resp, merged)

    if user:
        user.settings = merged
        await user.update(Set({UserDB.settings: merged}))

    # Language is baked into the rendered HTML, so the page has to come back from the server.
    # No toast either: HX-Refresh throws the page (and any toast on it) away immediately.
    if patch.lang is not None:
        resp.headers["HX-Refresh"] = "true"
        return "ok"

    resp.headers.update(toast_header(Toast(kind=ToastKind.SUCCESS, message=_("Settings saved."))))
    return "ok"


@router.post("/profile")
async def api_settings_profile_set(
    user: auth.CURR_USER,
    form: Annotated[ExtraInfoForm, Form()],
) -> ExtraInfo:
    """Tier-2. Meaningless without an account, so it requires one."""
    # Merge instead of replacing: profile_pic is not part of the form and must survive.
    updated = user.extra_info.model_copy(update=form.model_dump())

    user.extra_info = updated
    await user.update(Set({UserDB.extra_info: updated}))

    return updated
