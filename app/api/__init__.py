import logging
from fastapi import APIRouter
from .. import config, schema

logger = logging.getLogger("yatb.api")
router = APIRouter(
    prefix="/api",
    tags=["api"],
)


from . import api_auth  # noqa
from . import api_users  # noqa
from . import api_tasks  # noqa

from . import admin  # noqa

api_users.router.include_router(api_auth.router)
router.include_router(api_users.router)
router.include_router(api_tasks.router)
router.include_router(admin.router)
