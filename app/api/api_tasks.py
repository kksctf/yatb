from datetime import datetime
import uuid
from typing import List, Union

from fastapi import Depends, HTTPException, status, APIRouter

from . import logger
from .. import schema, auth, db, utils
from ..config import settings
from ..utils import metrics, tg

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get(
    "/",
    response_model=List[schema.Task],
    response_model_include=schema.Task.get_include_fieds(False),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_tasks_get(user: schema.User = Depends(auth.get_current_user_safe)):
    tasks = await db.get_all_tasks()
    tasks = tasks.values()
    tasks = filter(lambda x: x.visible_for_user(user), tasks)
    return list(tasks)


@router.post("/submit_flag")
async def api_task_submit_flag(flag: schema.FlagForm, user: schema.User = Depends(auth.get_current_user)):
    if datetime.utcnow() < settings.EVENT_START_TIME:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="CTF has not started yet",
        )

    task = await db.find_task_by_flag(flag.flag, user)
    if task:
        logger.info(f"{user.short_desc()} state=found task with flag flag={flag.flag}, task={task.short_desc()}.")
    else:
        logger.info(f"{user.short_desc()} state=not_found task with flag={flag.flag}")
        metrics.bad_solves_per_user.labels(user_id=user.user_id, username=user.username).inc()

    if not task or not task.visible_for_user(user):
        if task and not task.visible_for_user(user):
            logger.warning(f"Кто-то {user} попытался решить хидден таск {task}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ты как колпак снял, зачем таск решаешь?!",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bad flag",
        )

    if task.task_id in user.solved_tasks or user.user_id in task.pwned_by:
        _task_yes_user_not = task.task_id in user.solved_tasks and user.user_id not in task.pwned_by
        _user_yes_task_not = task.task_id not in user.solved_tasks and user.user_id in task.pwned_by
        if _task_yes_user_not or _user_yes_task_not:
            logger.warning(f"Wtf, user and task misreferenced!!! {task} {user}")
            if _task_yes_user_not:
                # user.solved_tasks.remove(task.task_id)
                pass
            if _user_yes_task_not:
                # task.pwned_by.remove(user.solved_tasks)
                pass
            await db.recalc_user_score(user)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="пятисотОЧКА!!1<br>Попробуйте решить таск ещё раз.",
            )
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="You already solved this task",
        )
    else:
        metrics.solves_per_task.labels(task_id=task.task_id, task_name=task.task_name).inc()
        metrics.solves_per_user.labels(user_id=user.user_id, username=user.username).inc()

    ret = await db.solve_task(task, user)

    if len(task.pwned_by) == 1:
        pass  # tg.display_fb_msg(task, user)

    return ret


@router.get(
    "/{task_id}",
    response_model=schema.Task,
    response_model_include=schema.Task.get_include_fieds(False),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_task_get(task_id: uuid.UUID, user: schema.User = Depends(auth.get_current_user)):
    task = await db.get_task_uuid(task_id)
    if not task or not task.visible_for_user(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No task",
        )
    return task
