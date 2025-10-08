from typing import Annotated

from fastapi import Depends, HTTPException, status

from yatb import auth, schema
from yatb.db import TaskDB


async def get_task(task_id: schema.TaskID, user: auth.CURR_USER_SAFE) -> TaskDB:
    task = await TaskDB.find_by_task_uuid(task_id)
    if not task or not task.visible_for_user(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No task",
        )
    return task


async def get_tasks(user: auth.CURR_USER_SAFE) -> list[TaskDB]:
    tasks = await TaskDB.get_all()
    tasks = tasks.values()
    tasks = filter(lambda x: x.visible_for_user(user), tasks)
    return list(tasks)


CURRENT_TASK = Annotated[TaskDB, Depends(get_task)]
VISIBLE_TASKS = Annotated[list[TaskDB], Depends(get_tasks)]
