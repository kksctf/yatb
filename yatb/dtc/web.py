from contextlib import asynccontextmanager

from fastapi import FastAPI

from yatb.base.version import get_version

from .config import settings
from .connectors.kub import KubeConnector

# WTF: tmp for dev
connector = KubeConnector()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with connector:
        yield


app = FastAPI(
    lifespan=lifespan,
    version=get_version(debug=settings.DEBUG, commit=settings.COMMIT),
    #     middleware=[process_exception],
)

from . import view

app.include_router(view.api_rotuer)
app.include_router(view.base_router)
