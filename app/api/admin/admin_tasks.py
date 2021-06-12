import uuid
import logging
from typing import List, Dict

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends
from . import admin_checker, router, logger
from ... import schema, auth, db
from ...config import settings


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
    response_model=Dict[uuid.UUID, schema.Task],
    response_model_include=schema.Task.get_include_fieds(True),
    response_model_exclude=schema.Task.get_exclude_fields(),
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
        logger.critical(f"Какой-то еблан {user.short_desc()} ПЫТАЛСЯ сбросить таски на проде, ахтунг!")
        return "Ты ебанулся, на проде эту хуйню запускать?!"

    for _, task in (await db.get_all_tasks()).items():
        task.pwned_by.clear()

    for _, ur in (await db.get_all_users()).items():
        ur.solved_tasks.clear()
    await db.recalc_scoreboard()
    return "ok"


@router.get(
    "/unsolve_task/{task_id}",
    response_model=schema.Task,
    response_model_include=schema.Task.get_include_fieds(True),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_admin_task_unsolve(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    logger.warning(f"Unsolving task: {task.short_desc()} by {user.short_desc()}")
    return await db.unsolve_task(task)


@router.post(
    "/task",
    response_model=schema.Task,
    response_model_include=schema.Task.get_include_fieds(True),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_admin_task_create(new_task: schema.TaskForm, user: schema.User = Depends(admin_checker)):
    task = await db.insert_task(new_task, user)
    logger.debug(f"New task: {new_task}, result={task}")
    return task


@router.get(
    "/task/{task_id}",
    response_model=schema.Task,
    response_model_include=schema.Task.get_include_fieds(True),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_admin_task_get(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    return task


@router.post(
    "/task/{task_id}",
    response_model=schema.Task,
    response_model_include=schema.Task.get_include_fieds(True),
    response_model_exclude=schema.Task.get_exclude_fields(),
)
async def api_admin_task_edit(new_task: schema.Task, task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    task = await db.update_task(task, new_task)  # TODO: remove bullshit.
    return task


@router.get("/task/delete/{task_id}")
async def api_admin_task_delete(task: schema.Task = Depends(get_task), user: schema.User = Depends(admin_checker)):
    await db.remove_task(task)
    logger.warning(f"[{user.short_desc()}] removing task {task}")
    return "ok"


@router.get("/task/delete_all")
async def api_admin_task_delete_all(user: schema.User = Depends(admin_checker)):
    if not settings.DEBUG:  # danger function!
        logger.critical(f"Какой-то еблан {user.short_desc()} ПЫТАЛСЯ УДАЛИТЬ таски на проде, ахтунг!")
        return "пащоль в жёпу (c) химичка Димона"

    logger.critical(f"[{user.short_desc()}] removing EVERYTHING")
    tasks = await db.get_all_tasks()
    for task in tasks:
        await db.remove_task(task)
    return "ok, you dead."


# TODO: А можно ли это сделать нормально?


class InternalObjTasksList(schema.BaseModel):
    tasks: List[uuid.UUID]


@router.post("/tasks/bulk_unhide")
async def api_admin_tasks_bulk_unhide(tasks: InternalObjTasksList, user: schema.User = Depends(admin_checker)):
    ret = {}
    for task_id in tasks.tasks:
        task = await db.get_task_uuid(task_id)
        if task:
            task.hidden = not task.hidden
            ret[task.task_id] = task.hidden
    return ret


class InternalObjTasksListDecay(InternalObjTasksList):
    tasks: List[uuid.UUID]
    decay: int


# not work.
@router.post("/tasks/bulk_edit_decay")
async def api_admin_tasks_bulk_edit_decay(tasks: InternalObjTasksListDecay, user: schema.User = Depends(admin_checker)):
    ret = {}
    for task_id in tasks.tasks:
        task = await db.get_task_uuid(task_id)
        if task:
            if task.scoring.classtype == schema.scoring.DynamicKKSScoring:
                task.scoring.decay = tasks.decay
                ret[task.task_id] = task.scoring.decay
    return ret
