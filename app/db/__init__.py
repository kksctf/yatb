from datetime import datetime
import os
import pickle
import uuid
import logging

from pydantic import BaseModel
from typing import List

from .. import app, schema, db
from ..config import settings

real_logger = logging.getLogger("yatb.db")


class FileDB(object):
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
        migration_datetime = datetime.now()

        for i, v in self._db["tasks"].items():
            self._index["tasks"][v.task_id] = self.migrate_task(v, migration_datetime)

        for i, v in self._db["users"].items():
            self._index["users"][v.user_id] = self.migrate_user(v, migration_datetime)

    def migrate_task(self, task: schema.Task, migration_datetime: datetime):
        # regenerate markdown
        task.description_html = schema.Task.regenerate_md(task.description)

        # 25.09.2020 migration
        if "hidden" not in task.__fields__:
            task.hidden = False

        # 25.11.2020 migration, for task authors
        if "author" not in task.__fields__:
            task.author = "@kksctf"  # uuid.UUID(int=0)  # zero guid

        # 11.11.2020 migration from list to dict in pwned_by/solved_tasks
        if isinstance(task.pwned_by, list):
            old = task.pwned_by
            task.pwned_by = {i: migration_datetime for i in old}

        return task

    def migrate_user(self, user: schema.User, migration_datetime: datetime):
        # 11.11.2020 migration from list to dict in pwned_by/solved_tasks
        if isinstance(user.solved_tasks, list):
            old = user.solved_tasks
            user.solved_tasks = {i: migration_datetime for i in old}

        if isinstance(user.auth_source, dict):
            original_au = user.auth_source
            cls: schema.auth.AuthBase.AuthModel = getattr(schema.auth, user.auth_source["classtype"]).AuthModel
            user.auth_source = cls.parse_obj(user.auth_source)
            real_logger.warning(f"Found & fixed broken auth source: {original_au} -> {user.auth_source}")

        # admin promote
        if user.admin_checker() and not user.is_admin:
            real_logger.warning(f"INIT: Promoting {user} to admin")
            user.is_admin = True

        return user


_db = FileDB()


@app.on_event("startup")
async def startup_event():
    global _db
    if settings.DB_NAME is None:
        _db.reset_db()
        real_logger.warning("TESTING_FileDB loaded")
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
            real_logger.error(f"Loading db exception, fallback to empty, {ex}")

    _db.generate_index()
    real_logger.warning("FileDB loaded")
    # logger.debug(f"FileDB: {_db._db}")
    # logger.debug(f"FileDBIndex: {_db._index}")


@app.on_event("shutdown")
async def shutdown_event():
    global _db
    if settings.DB_NAME is None:
        return
    with open(settings.DB_NAME, "wb") as f:
        pickle.dump(_db._db, f)
    real_logger.warning("FileDB saved")


def update_entry(obj: BaseModel, data: dict):
    for i in data:
        if i in obj.__fields__:
            setattr(obj, i, data[i])


from .db_users import *  # noqa
from .db_tasks import *  # noqa
