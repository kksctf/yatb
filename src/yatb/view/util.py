import asyncio
import datetime
from collections.abc import Mapping
from pathlib import Path

from fastapi import BackgroundTasks, Request
from fastapi.routing import APIRoute as _APIRoute
from fastapi.templating import Jinja2Templates
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from yatb import i18n, schema
from yatb.config import settings
from yatb.ui import get_ui_state

_base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=_base_path / "templates")

templates.env.add_extension("jinja2.ext.i18n")
# The translation machinery (private + messages chain, current_lang) lives in `i18n`
# so it is importable from plain Python handlers too. i18n.translate/ntranslate read
# the language from i18n.current_lang, which response_generator sets inside the
# executor thread right before rendering.
templates.env.install_gettext_callables(gettext=i18n.translate, ngettext=i18n.ntranslate, newstyle=True)


def route_generator(req: Request, base_path: str = "/api", *, ignore_admin: bool = True) -> dict[str, str]:
    router: Router = req.scope["router"]
    ret = {}
    for r in router.routes:
        if not isinstance(r, _APIRoute):
            continue
        if not r.path.startswith(base_path):
            continue
        if ignore_admin and r.path.startswith(f"{base_path}/admin"):
            continue

        dummy_params = {i: f"NONE_{i}" for i in set(r.param_convertors.keys())}
        ret[r.name] = str(req.url_for(r.name, **dummy_params))
    return ret


async def response_generator(  # noqa: PLR0913 # impossible to fix
    req: Request,
    filename: str,
    context: dict = {},  # noqa: B006 # iknew.
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTasks | None = None,
    *,
    ignore_admin: bool = True,
) -> _TemplateResponse:
    ui = get_ui_state(req)
    context_base = {
        "request": req,
        "ui": ui,
        "api_list": route_generator(req, ignore_admin=ignore_admin),
    }
    context_base.update(context)

    def _render() -> _TemplateResponse:
        # ContextVar must be set in the executor thread: values set in the async
        # context (or in BaseHTTPMiddleware) do not propagate here.
        token = i18n.set_lang(ui.lang)
        try:
            return templates.TemplateResponse(
                name=filename,
                context=context_base,
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
            )
        finally:
            i18n.current_lang.reset(token)

    return await asyncio.get_running_loop().run_in_executor(None, _render)


def version_string() -> str:
    return f"kks-tb-{settings.VERSION}"


templates.env.globals["version_string"] = version_string
templates.env.globals["len"] = len
templates.env.globals["template_format_time"] = schema.task.template_format_time
templates.env.globals["set"] = set
templates.env.globals["str"] = str
templates.env.globals["isinstance"] = isinstance
templates.env.globals["enumerate"] = enumerate

templates.env.globals["DEBUG"] = settings.DEBUG
templates.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templates.env.globals["CTF_NAME"] = settings.CTF_NAME
templates.env.globals["EVENT_START_TIME"] = settings.EVENT_START_TIME
templates.env.globals["EVENT_END_TIME"] = settings.EVENT_END_TIME
templates.env.globals["NOW"] = lambda: datetime.datetime.now(datetime.UTC)
