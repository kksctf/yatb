import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from . import api, i18n, main, view
from .config import settings
from .db import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    try:
        yield
    finally:
        await db.close()


app = FastAPI(
    docs_url=settings.FASTAPI_DOCS_URL,
    redoc_url=settings.FASTAPI_REDOC_URL,
    openapi_url=settings.FASTAPI_OPENAPI_URL,
    lifespan=lifespan,
)
app.add_middleware(i18n.LocaleMiddleware)

_base_path = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_base_path / "view" / "static"), name="static")

loggers = [logging.getLogger()]  # get the root logger
loggers = loggers + [logging.getLogger(name) for name in logging.root.manager.loggerDict]

main.setup_utils(app)
app.include_router(api.router)
app.include_router(view.router)
app.include_router(view.admin.api_rotuer)

expose_url = settings.MONITORING_URL

instrumentator = Instrumentator(
    excluded_handlers=[".*admin.*", expose_url],
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
)
instrumentator.instrument(app).expose(app, endpoint=expose_url)
