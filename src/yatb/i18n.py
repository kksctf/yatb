import contextlib
import contextvars
import gettext
from pathlib import Path

from babel.core import negotiate_locale
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

SUPPORTED = ["en", "ru"]
DEFAULT = "en"

# Bridges the per-request language into the synchronous gettext callables used
# during Jinja rendering. Rendering runs in a thread-pool executor, so the value
# is also set inside the render function (see view/util.py); it is set here too so
# plain Python request handlers calling p_()/translate() see the request language.
current_lang: contextvars.ContextVar[str] = contextvars.ContextVar("current_lang", default=DEFAULT)


def get_lang() -> str:
    return current_lang.get()


def set_lang(lang: str) -> contextvars.Token[str]:
    return current_lang.set(lang)


_LOCALE_DIR = Path(__file__).parent / "locale"


def _load_translation(lang: str) -> gettext.NullTranslations:
    base = gettext.translation("messages", localedir=_LOCALE_DIR, languages=[lang], fallback=True)
    # The `private` domain ships only on the private branch. Additive chain: public string
    # -> messages, private-only -> private, unknown -> msgid. Absent in open-source builds.
    with contextlib.suppress(FileNotFoundError):
        base.add_fallback(gettext.translation("private", localedir=_LOCALE_DIR, languages=[lang]))
    return base


TRANSLATIONS = {lang: _load_translation(lang) for lang in SUPPORTED}


def translate(message: str) -> str:
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS[DEFAULT]).gettext(message)


def ntranslate(singular: str, plural: str, n: int) -> str:
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS[DEFAULT]).ngettext(singular, plural, n)


# `p_`/`np_` are runtime-identical to the public `_`/`ngettext` (same messages+private
# chain). The only difference is the extraction keyword: strings called through p_/np_
# are routed to the private catalog and kept out of the public messages.po.
p_ = translate
np_ = ntranslate


def detect_lang(header: str | None) -> str:
    if header:
        langs = [lang.partition(";")[0].strip() for lang in header.split(",")]
        match = negotiate_locale(langs, SUPPORTED)
        if match:
            return match
    return DEFAULT


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # priority: explicit query override -> cookie -> Accept-Language -> default
        query_lang = request.query_params.get("lang")
        lang = query_lang
        if lang not in SUPPORTED:
            lang = request.cookies.get("lang")
        if lang not in SUPPORTED:
            lang = detect_lang(request.headers.get("accept-language"))
        request.state.lang = lang
        set_lang(lang)  # so p_()/translate() in async handlers see the request language

        resp = await call_next(request)

        # persist an explicit query choice so it survives navigation
        if query_lang in SUPPORTED:
            resp.set_cookie("lang", query_lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp
