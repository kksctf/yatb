import uuid
from typing import Dict

from fastapi import Depends, HTTPException, status

from ... import db, schema
from ...config import settings
from . import admin_checker, logger, router


async def get_task(task_id: uuid.UUID) -> schema.Task:
    task = await db.get_task_uuid(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.get(
    "/tasks",
    response_model=Dict[uuid.UUID, schema.Task.admin_model()],
)
async def api_admin_tasks(user: schema.User = Depends(admin_checker)):
    all_tasks = await db.get_all_tasks()
    return all_tasks


@router.get("/recalc_scoreboard")
async def api_admin_recalc_scoreboard(user: schema.User = Depends(admin_checker)):
    await db.recalc_scoreboard()
    return None


@router.get("/unsolve_tasks")
async def api_admin_unsolve_tasks(user: schema.User = Depends(admin_checker)):
    if not settings.DEBUG:
        logger.critical(f"Какой-то гений {user.short_desc()} ПЫТАЛСЯ сбросить таски на проде!")
        return "Нет."

    for _, task in (await db.get_all_tasks()).items():
        task.pwned_by.clear()

    for _, ur in (await db.get_all_users()).items():
        ur.solved_tasks.clear()
    await db.recalc_scoreboard()
    return "ok"


@router.get(
    "/unsolve_task/{task_id}",
    response_model=schema.Task.admin_model(),
)
async def api_admin_task_unsolve(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    logger.warning(f"Unsolving task: {task.short_desc()} by {user.short_desc()}")
    return await db.unsolve_task(task)


@router.post(
    "/task",
    response_model=schema.Task.admin_model(),
)
async def api_admin_task_create(new_task: schema.TaskForm, user: schema.User = Depends(admin_checker)):
    task = await db.insert_task(new_task, user)
    logger.debug(f"New task: {new_task}, result={task}")
    return task


@router.get("/task/delete_all")
async def api_admin_task_delete_all(user: schema.User = Depends(admin_checker)):
    if not settings.DEBUG:  # danger function!
        logger.critical(f"Какой-то гений {user.short_desc()} ПЫТАЛСЯ УДАЛИТЬ таски на проде!")
        return "нет."

    logger.critical(f"[{user.short_desc()}] removing EVERYTHING")
    tasks = await db.get_all_tasks()
    for task in list(tasks.values()):
        await db.remove_task(task)
    return "ok, you dead."


@router.get("/task/delete/{task_id}")
async def api_admin_task_delete(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    await db.remove_task(task)
    logger.warning(f"[{user.short_desc()}] removing task {task}")
    return "ok"


@router.get(
    "/task/{task_id}",
    response_model=schema.Task.admin_model(),
)
async def api_admin_task_get(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    return task


@router.post(
    "/task/{task_id}",
    response_model=schema.Task.admin_model(),
)
async def api_admin_task_edit(
    new_task: schema.Task, task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)
):
    task = await db.update_task(task, new_task)  # TODO: remove bullshit.
    return task


# TODO: А можно ли это сделать нормально?


# class InternalObjTasksList(schema.EBaseModel):
#     tasks: List[uuid.UUID]


# @router.post("/tasks/bulk_unhide")
# async def api_admin_tasks_bulk_unhide(tasks: InternalObjTasksList, user: schema.User = Depends(admin_checker)):
#     ret = {}
#     for task_id in tasks.tasks:
#         task = await db.get_task_uuid(task_id)
#         if task:
#             task.hidden = not task.hidden
#             ret[task.task_id] = task.hidden
#     return ret


# class InternalObjTasksListDecay(InternalObjTasksList):
#     tasks: List[uuid.UUID]
#     decay: int


# not work.
# @router.post("/tasks/bulk_edit_decay")
# async def api_admin_tasks_bulk_edit_decay(
#     tasks: InternalObjTasksListDecay,
#     user: schema.User = Depends(admin_checker),
# ):
#     ret = {}
#     for task_id in tasks.tasks:
#         task = await db.get_task_uuid(task_id)
#         if task:
#             if task.scoring.classtype == schema.scoring.DynamicKKSScoring:
#                 task.scoring.decay = tasks.decay
#                 ret[task.task_id] = task.scoring.decay
#     return ret
