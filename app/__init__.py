import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import utils
from .config import settings

app = FastAPI(
    docs_url=settings.FASTAPI_DOCS_URL,
    redoc_url=settings.FASTAPI_REDOC_URL,
    openapi_url=settings.FASTAPI_OPENAPI_URL,
)

_base_path = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_base_path / "view" / "static"), name="static")

root_logger = utils.log_helper.root_logger

loggers = [logging.getLogger()]  # get the root logger
loggers = loggers + [logging.getLogger(name) for name in logging.root.manager.loggerDict]

# for i in loggers:
#     print(f"LOGGER: {i}")

from . import api  # noqa
from . import main  # noqa
from . import view  # noqa

app.include_router(api.router)
app.include_router(view.router)

# prometheus
from prometheus_fastapi_instrumentator import Instrumentator  # noqa

expose_url = settings.MONITORING_URL

instrumentator = Instrumentator(
    excluded_handlers=[".*admin.*", expose_url],
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
)
instrumentator.instrument(app).expose(app, endpoint=expose_url)
# utils.metrics.bad_solves_per_user

"""
@app.on_event("startup")
def startup_event():
    metrics.load_all_metrics()


@app.on_event("shutdown")
def shutdown_event():
    metrics.save_all_metrics()
"""
