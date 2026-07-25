from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from yatb.config import settings
from yatb.db import TaskDB, UserDB
from yatb.schema import TaskID
from yatb.utils import metrics, tg
from yatb.utils.log_helper import get_logger
from yatb.ws import ws_manager

logger = get_logger("services.flags")


class FlagOutcome(StrEnum):
    """Every way a flag submission can end.

    This enum is the point of the module: before it, the outcomes lived as five scattered
    `raise HTTPException` calls plus one `return`, so each caller had to re-derive "what
    kind of thing just happened" from an HTTP status code. That is how ALREADY_SOLVED
    (202) ended up rendered as a red error toast in the navbar.
    """

    OK = "ok"
    ALREADY_SOLVED = "already_solved"
    BAD_FLAG = "bad_flag"
    NOT_STARTED = "not_started"
    DESYNC = "desync"


class FlagResult(BaseModel):
    # TaskDB is a beanie Document, not a pydantic-friendly field type.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    outcome: FlagOutcome
    task_id: TaskID | None = None
    # Carried so callers can render the task card / interpolate points without a second
    # DB round-trip. Absent for BAD_FLAG and NOT_STARTED, where there is no known task.
    task: TaskDB | None = None


class BRMessage(BaseModel):
    task_name: str
    user_name: str
    points: int
    is_fb: bool


async def submit_flag(user: UserDB, flag: str) -> FlagResult:
    """Check a flag and apply its side effects. Never raises for a business outcome."""
    if not user.is_admin and datetime.now(tz=UTC) < settings.EVENT_START_TIME:
        return FlagResult(outcome=FlagOutcome.NOT_STARTED)

    cleaned_flag = flag.strip()
    task = await TaskDB.find_by_flag(cleaned_flag, user)
    if task:
        logger.info(f"{user.short_desc()} state=found task with flag flag={cleaned_flag!r}, task={task.short_desc()}")
    else:
        logger.info(f"{user.short_desc()} state=not_found task with flag={cleaned_flag!r}")
        metrics.bad_solves_per_user.labels(user_id=user.user_id, username=user.username).inc()

    if not task or not (visible := task.visible_for_user(user)):
        if task and not visible:  # pyright: ignore[reportPossiblyUnboundVariable] # boolean things is hard for pylance
            logger.warning(f"Someone {user.short_desc()} trying to solve hidden task {task}")
        # Deliberately the same outcome either way: telling the two apart would leak the
        # existence of hidden tasks to anyone willing to brute-force flags.
        return FlagResult(outcome=FlagOutcome.BAD_FLAG)

    if task.task_id in user.solved_tasks or user.user_id in task.pwned_by:
        return await _resolve_already_solved(user, task)

    metrics.solves_per_task.labels(task_id=task.task_id, task_name=task.task_name).inc()
    metrics.solves_per_user.labels(user_id=user.user_id, username=user.username).inc()

    task_id = await user.solve_task_bw(task)

    # TODO: maybe this is counter-UX...
    if task.dti:
        # The dynamic-tasks client still lives under `api/`, so importing it at module
        # scope would point a service at a router package. Deferred until actually needed;
        # moving the client into a layer of its own is a separate job.
        from yatb.api.api_dynamic_tasks import UserTaskPair, get_client_safe

        if client := get_client_safe():
            await client.stop(UserTaskPair(task=task, user=user))

    msg = BRMessage(
        task_name=task.task_name,
        user_name=user.display_name,
        points=task.scoring.points,
        is_fb=len(task.pwned_by) == 1,
    )
    await ws_manager.broadcast(msg.model_dump_json())

    if len(task.pwned_by) == 1:
        try:
            tg.display_fb_msg(task, user)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"tg_exception exception='{ex}'")

    return FlagResult(outcome=FlagOutcome.OK, task_id=task_id, task=task)


async def _resolve_already_solved(user: UserDB, task: TaskDB) -> FlagResult:
    """Tell an ordinary re-submit apart from a half-written solve.

    `user.solved_tasks` and `task.pwned_by` are two sides of the same fact, written
    separately. If only one side is set, the score is wrong and needs recomputing — that
    is a different thing to say to the player than "you already solved this".
    """
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
        return FlagResult(outcome=FlagOutcome.DESYNC, task_id=task.task_id, task=task)

    return FlagResult(outcome=FlagOutcome.ALREADY_SOLVED, task_id=task.task_id, task=task)
