import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from .. import auth, schema
from ..config import settings
from ..db.beanie import TaskDB
from ..utils import metrics, tg
from ..ws import ws_manager
from . import logger

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/")
async def api_tasks_get(user: auth.CURR_USER_SAFE) -> list[schema.Task.public_model]:
    tasks = await TaskDB.get_all()
    tasks = tasks.values()
    tasks = filter(lambda x: x.visible_for_user(user), tasks)
    return list(tasks)


class BRMessage(schema.EBaseModel):
    task_name: str
    user_name: str
    points: int
    is_fb: bool


@router.post("/submit_flag")
async def api_task_submit_flag(flag: schema.FlagForm, user: auth.CURR_USER) -> uuid.UUID:
    if datetime.now(tz=UTC) < settings.EVENT_START_TIME:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="CTF has not started yet",
        )

    task = await TaskDB.find_by_flag(flag.flag, user)
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


@router.get("/{task_id}")
async def api_task_get(task_id: uuid.UUID, user: auth.CURR_USER_SAFE) -> schema.Task.public_model:
    task = await TaskDB.find_by_task_uuid(task_id)
    if not task or not task.visible_for_user(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No task",
        )
    return task
