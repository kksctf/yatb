from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from yatb import auth
from yatb.schema import FlagModel, Task, TaskID
from yatb.services.flags import FlagOutcome, submit_flag

from .utils import CURRENT_TASK, VISIBLE_TASKS

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


class SubmitFlagResult(BaseModel):
    task_id: TaskID
    # A correct flag for a task you already own is not a failure, so it is a 200 with this
    # flag set rather than a status code the caller has to interpret.
    already_solved: bool


@router.get("/")
async def api_tasks_get(tasks: VISIBLE_TASKS) -> list[Task.public_model]:
    return tasks


@router.get("/{task_id}")
async def api_task_get(task: CURRENT_TASK) -> Task.public_model:
    return task


@router.post("/submit_flag")
async def api_task_submit_flag(flag: FlagModel, user: auth.CURR_USER) -> SubmitFlagResult:
    """Pure JSON API. The htmx-facing twin lives in `view/actions.py`."""
    result = await submit_flag(user, flag.flag)

    match result.outcome:
        case FlagOutcome.OK | FlagOutcome.ALREADY_SOLVED:
            # task_id is always set on these two outcomes.
            return SubmitFlagResult(
                task_id=result.task_id,  # pyright: ignore[reportArgumentType]
                already_solved=result.outcome is FlagOutcome.ALREADY_SOLVED,
            )

        case FlagOutcome.NOT_STARTED:
            raise HTTPException(
                status_code=status.HTTP_425_TOO_EARLY,
                detail="CTF has not started yet",
            )

        case FlagOutcome.BAD_FLAG:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bad flag",
            )

        case FlagOutcome.DESYNC:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task and user references are out of sync, please submit the flag again",
            )
