import uuid
from typing import Annotated, Mapping

from beanie import BulkWriter
from beanie.operators import Set
from fastapi import Depends, HTTPException, status

from ... import schema
from ...config import settings
from ...db.beanie import TaskDB, UserDB
from . import CURR_ADMIN, logger, router


async def get_task(task_id: uuid.UUID) -> TaskDB:
    task = await TaskDB.find_by_task_uuid(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


CURR_TASK = Annotated[TaskDB, Depends(get_task)]


@router.get("/tasks")
async def api_admin_tasks(user: CURR_ADMIN) -> Mapping[uuid.UUID, schema.Task.admin_model]:
    all_tasks = await TaskDB.get_all()
    return all_tasks


@router.get("/recalc_scoreboard")
async def api_admin_recalc_scoreboard(user: CURR_ADMIN):
    await UserDB.recalc_scoreboard()
    return None


@router.get("/unsolve_tasks")
async def api_admin_unsolve_tasks(user: CURR_ADMIN) -> str:
    if not settings.DEBUG:
        logger.critical(f"Какой-то гений {user.short_desc()} ПЫТАЛСЯ сбросить таски на проде!")
        return "Нет."

    async with BulkWriter() as bw:
        for task in (await TaskDB.get_all()).values():
            task.pwned_by.clear()
            await task.update(Set({str(TaskDB.pwned_by): task.pwned_by}), bulk_writer=bw)

        logger.info(f"{bw.operations = }")

    async with BulkWriter() as bw:
        for user in (await UserDB.get_all()).values():
            user.solved_tasks.clear()
            await user.update(Set({str(UserDB.solved_tasks): user.solved_tasks}), bulk_writer=bw)

        logger.info(f"{bw.operations = }")

    await UserDB.recalc_scoreboard()
    return "ok"


@router.get("/unsolve_task/{task_id}")
async def api_admin_task_unsolve(task: CURR_TASK, user: CURR_ADMIN) -> schema.Task.admin_model:
    logger.warning(f"Unsolving task: {task.short_desc()} by {user.short_desc()}")
    # return await db.unsolve_task(task)
    raise NotImplementedError


@router.post("/task")
async def api_admin_task_create(new_task: schema.TaskForm, user: CURR_ADMIN) -> schema.Task.admin_model:
    task = await TaskDB.populate(new_task, user)
    logger.debug(f"New task: {new_task}, result={task}")
    return task


@router.get("/task/delete_all")
async def api_admin_task_delete_all(user: CURR_ADMIN):
    raise NotImplementedError

    # if not settings.DEBUG:  # danger function!
    #     logger.critical(f"Какой-то гений {user.short_desc()} ПЫТАЛСЯ УДАЛИТЬ таски на проде!")
    #     return "нет."

    # logger.critical(f"[{user.short_desc()}] removing EVERYTHING")
    # tasks = await db.get_all_tasks()
    # for task in list(tasks.values()):
    #     await db.remove_task(task)
    # return "ok, you dead."


@router.get("/task/delete/{task_id}")
async def api_admin_task_delete(task: CURR_TASK, user: CURR_ADMIN):
    raise NotImplementedError

    # await db.remove_task(task)
    # logger.warning(f"[{user.short_desc()}] removing task {task}")
    # return "ok"


@router.get("/task/{task_id}")
async def api_admin_task_get(task: CURR_TASK, user: CURR_ADMIN) -> schema.Task.admin_model:
    return task


@router.post("/task/{task_id}")
async def api_admin_task_edit(new_task: schema.Task, task: CURR_TASK, user: CURR_ADMIN) -> schema.Task.admin_model:
    task = await task.update_entry(new_task)  # TODO: remove bullshit.
    return task


# TODO: А можно ли это сделать нормально?


# class InternalObjTasksList(schema.EBaseModel):
#     tasks: List[uuid.UUID]


# @router.post("/tasks/bulk_unhide")
# async def api_admin_tasks_bulk_unhide(tasks: InternalObjTasksList, user: CURR_ADMIN):
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
#     user: CURR_ADMIN,
# ):
#     ret = {}
#     for task_id in tasks.tasks:
#         task = await db.get_task_uuid(task_id)
#         if task:
#             if task.scoring.classtype == schema.scoring.DynamicKKSScoring:
#                 task.scoring.decay = tasks.decay
#                 ret[task.task_id] = task.scoring.decay
#     return ret
