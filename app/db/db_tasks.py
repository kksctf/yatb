from app.schema.user import User
import uuid
import logging
from datetime import datetime
from asyncio import Lock

# import markdown2

from typing import List, Dict, Union, Optional

from .. import schema
from ..schema.flags import StaticFlag, DynamicKKSFlag, Flag
from ..config import settings
from ..utils import md, metrics

from . import update_entry, db_users

logger = logging.getLogger("yatb.db.tasks")
db_lock = Lock()


async def get_task_uuid(uuid: uuid.UUID) -> schema.Task:
    from . import _db

    if uuid in _db._index["tasks"]:
        return _db._index["tasks"][uuid]


async def get_all_tasks() -> Dict[uuid.UUID, schema.Task]:
    from . import _db

    return _db._index["tasks"]


async def check_task_uuid(uuid: uuid.UUID) -> bool:
    from . import _db

    return uuid in _db._index["tasks"]


async def insert_task(new_task: schema.TaskForm, author: schema.User) -> schema.Task:
    from . import _db

    # task = schema.Task.parse_obj(new_task)  # WTF: SHITCODE
    task = schema.Task(
        task_name=new_task.task_name,
        category=new_task.category,
        scoring=new_task.scoring,
        description=new_task.description,
        description_html=schema.Task.regenerate_md(new_task.description),
        flag=new_task.flag,
        author=(new_task.author if new_task.author != "" else f"@{author.username}"),
    )

    _db._db["tasks"][task.task_id] = task
    _db._index["tasks"][task.task_id] = task
    return task


async def update_task(task: schema.Task, new_task: schema.Task) -> schema.Task:
    from . import _db

    logger.debug(f"Update task {task} to {new_task}")

    update_entry(
        task,
        new_task.dict(
            exclude={
                "task_id",
                "description_html",
                "scoring",
                "flag",
                "pwned_by",
            }
        ),
    )
    task.scoring = new_task.scoring  # fix for json-ing scoring on edit
    task.flag = new_task.flag  # fix for json-ing flag on edit

    logger.debug(f"Resulting task={task}")
    task.description_html = schema.Task.regenerate_md(task.description)
    return task


async def remove_task(task: schema.Task):
    from . import _db

    # TODO: recalc score and something else.
    await unsolve_task(task)
    del _db._db["tasks"][task.task_id]
    del _db._index["tasks"][task.task_id]


async def find_task_by_flag(flag: str, user: schema.User) -> Union[schema.Task, None]:
    from . import _db

    for task_id, task in _db._db["tasks"].items():
        task: schema.Task  # strange solution, but no other ideas
        if task.flag.flag_checker(flag, user):
            return task

    return None


async def solve_task(task: schema.Task, solver: schema.User):
    if solver.is_admin and not settings.DEBUG:  # if you admin, you can't solve task.
        return task.task_id

    if datetime.utcnow() > settings.EVENT_END_TIME:
        return task.task_id

    #  WTF: UNTEDTED: i belive this will work as a monkey patch for rAcE c0nDiTioN
    global db_lock
    async with db_lock:
        # add references
        solv_time = datetime.now()
        solver.solved_tasks[task.task_id] = solv_time
        task.pwned_by[solver.user_id] = solv_time

        # get previous score
        prev_score = task.scoring.points
        solver.score += prev_score

        # if do_recalc, recalc all the scoreboard... only users, who solved task
        do_recalc = task.scoring.solve_task()
        if do_recalc:
            new_score = task.scoring.points
            diff = prev_score - new_score
            logger.info(f"Solve task: {task.short_desc()}, oldscore={prev_score}, newscore={new_score}, diff={diff}")
            for solver_id in task.pwned_by:
                solver_recalc = await db_users.get_user_uuid(solver_id)
                solver_recalc.score -= diff
                metrics.score_per_user.labels(user_id=solver_recalc.user_id, username=solver_recalc.username).set(solver_recalc.score)

    return task.task_id


async def unsolve_task(task: schema.Task) -> schema.Task:
    # add references
    global db_lock
    async with db_lock:
        task.pwned_by.clear()
        # TODO: оптимизировать эту ебатеку
        for _, user in (await db_users.get_all_users()).items():
            if task.task_id in user.solved_tasks:
                user.solved_tasks.pop(task.task_id)
        # task.scoring

    await recalc_scoreboard()
    return task


async def recalc_user_score(user: schema.User, _task_cache: Dict[uuid.UUID, schema.Task] = None):
    if _task_cache is None:
        _task_cache = {}
    old_score = user.score
    user.score = 0
    for task_id in user.solved_tasks:
        if task_id not in _task_cache:
            _task_cache[task_id] = await get_task_uuid(task_id)
        if _task_cache[task_id] is None:
            continue
        user.score += _task_cache[task_id].scoring.points
    if old_score != user.score:
        logger.warning(f"Recalc: smth wrong with {user.short_desc()}, {old_score} != {user.score}!")


async def recalc_scoreboard():
    _task_cache: Dict[uuid.UUID, schema.Task] = {}
    global db_lock
    async with db_lock:
        for _, user in (await db_users.get_all_users()).items():
            await recalc_user_score(user, _task_cache)
