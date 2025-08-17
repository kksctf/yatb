import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from .. import auth
from ..db.beanie import TaskDB


async def get_task(task_id: uuid.UUID, user: auth.CURR_USER_SAFE) -> TaskDB:
    task = await TaskDB.find_by_task_uuid(task_id)
    if not task or not task.visible_for_user(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No task",
        )
    return task


CURRENT_TASK = Annotated[TaskDB, Depends(get_task)]
