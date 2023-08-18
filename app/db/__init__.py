import os
import pickle
from datetime import datetime

from pydantic import BaseModel

from .. import app, db, schema
from ..config import settings
from ..utils.log_helper import get_logger
from .beanie import TaskDB, UserDB

logger = get_logger("db")


class FileDB:
    _db = None
    _index = None

    def __init__(self):
        self.reset_db()

    def reset_db(self):
        self._index = {
            "tasks": {},
            "users": {},
            "short_urls": {},
        }
        self._db = {
            "tasks": {},
            "users": {},
        }

    def generate_index(self):
        for i, v in self._db["tasks"].items():
            self._index["tasks"][v.task_id] = self.update_task(v)

        for i, v in self._db["users"].items():
            self._index["users"][v.user_id] = self.update_user(v)

    def update_task(self, task: schema.Task):
        # regenerate markdown
        task.description_html = schema.Task.regenerate_md(task.description)

        return task

    def update_user(self, user: schema.User):
        # FIXME: говнокод & быстрофикс.
        if isinstance(user.auth_source, dict):
            original_au = user.auth_source
            cls: schema.auth.AuthBase.AuthModel = getattr(schema.auth, user.auth_source["classtype"]).AuthModel
            user.auth_source = cls.model_validate(user.auth_source)
            logger.warning(f"Found & fixed broken auth source: {original_au} -> {user.auth_source}")

        # admin promote
        if user.admin_checker() and not user.is_admin:
            logger.warning(f"INIT: Promoting {user} to admin")
            user.is_admin = True

        return user


_db = FileDB()


@app.on_event("startup")
async def startup_event():
    return
    global _db
    if settings.DB_NAME is None:
        _db.reset_db()
        logger.warning("TESTING_FileDB loaded")
        return

    if not os.path.exists(settings.DB_NAME):
        _db._db = {
            "tasks": {},
            "users": {},
        }
    else:
        try:
            with open(settings.DB_NAME, "rb") as f:
                _db._db = pickle.load(f)
        except Exception as ex:
            _db._db = {
                "tasks": {},
                "users": {},
            }
            logger.error(f"Loading db exception, fallback to empty, {ex}")

    _db.generate_index()
    logger.warning("FileDB loaded")
    # logger.debug(f"FileDB: {_db._db}")
    # logger.debug(f"FileDBIndex: {_db._index}")


@app.on_event("shutdown")
async def shutdown_event():
    return
    global _db
    if settings.DB_NAME is None:
        return
    save_path = settings.DB_NAME / "ressurect_db.db" if settings.DB_NAME.is_dir() else settings.DB_NAME
    with open(settings.DB_NAME, "wb") as f:
        pickle.dump(_db._db, f)
    logger.warning("FileDB saved")


def update_entry(obj: BaseModel, data: dict):
    for i in data:
        if i in obj.__fields__:
            setattr(obj, i, data[i])



# from .db_tasks import *  # noqa
# from .db_users import *  # noqa
