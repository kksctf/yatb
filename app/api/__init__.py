import logging

from fastapi import APIRouter

from .. import config, schema
from ..utils.log_helper import get_logger

logger = get_logger("api")
router = APIRouter(
    prefix="/api",
    tags=["api"],
)


from . import admin  # noqa
from . import api_auth  # noqa
from . import api_tasks  # noqa
from . import api_users  # noqa

api_users.router.include_router(api_auth.router)
router.include_router(api_users.router)
router.include_router(api_tasks.router)
router.include_router(admin.router)
