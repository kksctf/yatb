import contextvars
import gettext
from pathlib import Path
from typing import TypeGuard, get_args

from babel.core import negotiate_locale

from yatb.ui_types import Language

SUPPORTED = get_args(Language)
DEFAULT: Language = "en"

# Bridges the per-request language into the synchronous gettext callables used
# during Jinja rendering. Rendering runs in a thread-pool executor, so the value
# is also set inside the render function (see view/util.py); it is set here too so
# plain Python request handlers calling _() see the request language.
current_lang: contextvars.ContextVar[Language] = contextvars.ContextVar("current_lang", default=DEFAULT)


def get_lang() -> Language:
    return current_lang.get()


def set_lang(lang: Language) -> contextvars.Token[Language]:
    return current_lang.set(lang)


_LOCALE_DIR = Path(__file__).parent / "locale"


def _load_translation(lang: str) -> gettext.NullTranslations:
    base = gettext.translation("messages", localedir=_LOCALE_DIR, languages=[lang], fallback=True)
    private = gettext.translation("private", localedir=_LOCALE_DIR, languages=[lang], fallback=True)
    private.add_fallback(base)
    return private


TRANSLATIONS = {lang: _load_translation(lang) for lang in SUPPORTED}


def translate(message: str) -> str:
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS[DEFAULT]).gettext(message)


def ntranslate(singular: str, plural: str, n: int) -> str:
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS[DEFAULT]).ngettext(singular, plural, n)


_ = translate


def is_language(value: str | None) -> TypeGuard[Language]:
    return value in SUPPORTED


def detect_lang(header: str | None) -> Language:
    if header:
        langs = [lang.partition(";")[0].strip() for lang in header.split(",")]
        match = negotiate_locale(langs, SUPPORTED)
        if is_language(match):
            return match
    return DEFAULT
