from dataclasses import dataclass
from typing import cast, get_args

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from yatb import i18n
from yatb.ui_types import LangPref, Language, Theme


@dataclass(frozen=True)
class UIState:
    lang: Language
    lang_pref: LangPref
    theme: Theme


def get_ui_state(request: Request) -> UIState:
    state = request.state.ui
    if not isinstance(state, UIState):
        raise TypeError("UISettingsMiddleware must provide UIState")
    return state


def set_pref_cookie(response: Response, name: str, value: str) -> None:
    if value == "auto":
        response.delete_cookie(name, samesite="lax")
    else:
        response.set_cookie(name, value, max_age=60 * 60 * 24 * 365, samesite="lax")


class UISettingsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        query_lang = request.query_params.get("lang")
        preference = query_lang if i18n.is_language(query_lang) else request.cookies.get("lang")
        theme = request.cookies.get("theme")
        state = UIState(
            lang=preference
            if i18n.is_language(preference)
            else i18n.detect_lang(request.headers.get("accept-language")),
            lang_pref=preference if i18n.is_language(preference) else "auto",
            theme=cast("Theme", theme) if theme in get_args(Theme) else "auto",
        )
        request.state.ui = state
        token = i18n.set_lang(state.lang)
        try:
            response = await call_next(request)
        finally:
            i18n.current_lang.reset(token)
        if i18n.is_language(query_lang):
            set_pref_cookie(response, "lang", query_lang)
        return response
