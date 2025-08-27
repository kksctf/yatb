import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, status
from pydantic import BaseModel

from yatb import auth, schema
from yatb.config import settings
from yatb.db import TaskDB
from yatb.utils import metrics, tg
from yatb.ws import ws_manager

from . import logger
from .api_dynamic_tasks import UserTaskPair, get_client_safe
from .utils import CURRENT_TASK, VISIBLE_TASKS

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


class BRMessage(BaseModel):
    task_name: str
    user_name: str
    points: int
    is_fb: bool


@router.get("/")
async def api_tasks_get(tasks: VISIBLE_TASKS) -> list[schema.Task.public_model]:
    return tasks


@router.get("/{task_id}")
async def api_task_get(task: CURRENT_TASK) -> schema.Task.public_model:
    return task


@router.post("/submit_flag")
async def api_task_submit_flag(flag: Annotated[schema.FlagForm, Form()], user: auth.CURR_USER) -> uuid.UUID:
    if not user.is_admin and datetime.now(tz=UTC) < settings.EVENT_START_TIME:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="CTF has not started yet",
        )

    cleaned_flag = flag.flag.strip()
    task = await TaskDB.find_by_flag(cleaned_flag, user)
    if task:
        logger.info(f"{user.short_desc()} state=found task with flag flag={cleaned_flag!r}, task={task.short_desc()}")
    else:
        logger.info(f"{user.short_desc()} state=not_found task with flag={cleaned_flag!r}")
        metrics.bad_solves_per_user.labels(user_id=user.user_id, username=user.username).inc()

    if not task or not (visible := task.visible_for_user(user)):
        if task and not visible:  # pyright: ignore[reportPossiblyUnboundVariable] # boolean things is hard for pylance
            logger.warning(f"Someone {user.short_desc()} trying to solve hidden task {task}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bad flag",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bad flag",
        )

    if task.task_id in user.solved_tasks or user.user_id in task.pwned_by:
        _task_yes_user_not = task.task_id in user.solved_tasks and user.user_id not in task.pwned_by
        _user_yes_task_not = task.task_id not in user.solved_tasks and user.user_id in task.pwned_by
        if _task_yes_user_not or _user_yes_task_not:
            logger.warning(
                f"Wtf, user and task misreferenced!!! {task} {user} {_task_yes_user_not = } {_user_yes_task_not = }"
            )
            if _task_yes_user_not:
                # user.solved_tasks.remove(task.task_id)
                pass
            if _user_yes_task_not:
                # task.pwned_by.remove(user.solved_tasks)
                pass

            await user.recalc_score_one()
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

    ret = await user.solve_task_bw(task)

    # TODO: maybe this is counter-UX...
    if task.dti and (client := get_client_safe()):
        await client.stop(UserTaskPair(task=task, user=user))

    msg = BRMessage(
        task_name=task.task_name,
        user_name=user.username,
        points=task.scoring.points,
        is_fb=len(task.pwned_by) == 1,
    )

    await ws_manager.broadcast(msg.model_dump_json())

    if len(task.pwned_by) == 1:
        try:
            tg.display_fb_msg(task, user)
        except Exception as ex:  # noqa: W0703, PIE786
            logger.error(f"tg_exception exception='{ex}'")

    return ret
