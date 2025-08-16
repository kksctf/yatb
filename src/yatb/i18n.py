from babel.core import negotiate_locale
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

SUPPORTED = ["en", "ru"]
DEFAULT = "en"


def detect_lang(header: str | None) -> str:
    if header:
        langs = [lang.partition(";")[0].strip() for lang in header.split(",")]
        match = negotiate_locale(langs, SUPPORTED)
        if match:
            return match
    return DEFAULT


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # explicit query override has priority
        lang = request.query_params.get("lang")
        if lang not in SUPPORTED:
            lang = detect_lang(request.headers.get("accept-language"))
        request.state.lang = lang
        resp = await call_next(request)
        return resp
