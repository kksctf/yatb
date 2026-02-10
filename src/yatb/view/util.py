import asyncio
import datetime
import gettext
from collections.abc import Mapping
from pathlib import Path

from fastapi import BackgroundTasks, Request
from fastapi.routing import APIRoute as _APIRoute
from fastapi.templating import Jinja2Templates
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from yatb import i18n, schema
from yatb.config import settings

_base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=_base_path / "templates")

TRANSLATIONS = {
    lang: gettext.translation(
        domain="messages",
        localedir=Path(__file__).parent.parent / "locale",
        languages=[lang],
        fallback=True,
    )
    for lang in i18n.SUPPORTED
}


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
    context_base = {
        "request": req,
        "api_list": route_generator(req, ignore_admin=ignore_admin),
    }
    context_base.update(context)
    return await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: templates.TemplateResponse(
            name=filename,
            context=context_base,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        ),
    )


def version_string() -> str:
    return f"kks-tb-{settings.VERSION}"


def _(text: str, request: Request) -> str:
    return TRANSLATIONS[request.state.lang].gettext(text)


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

templates.env.globals["_"] = _
