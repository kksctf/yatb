from fastapi import APIRouter

from yatb.utils.log_helper import get_logger

logger = get_logger("api")
router = APIRouter(prefix="/api")

from . import auth  # noqa
from . import admin  # noqa
from . import settings  # noqa
from . import tasks  # noqa
from . import users  # noqa
from . import api_dynamic_tasks  # noqa

users.router.include_router(auth.router)
users.router.include_router(settings.router)

router.include_router(users.router)
router.include_router(tasks.router)
router.include_router(api_dynamic_tasks.router)
router.include_router(admin.router)
