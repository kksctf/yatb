import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated

from fastapi import HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from yatb import auth, schema
from yatb.api import tasks
from yatb.db.user import UserDB
from yatb.schema.ids import UserID
from yatb.utils.log_helper import get_logger

from .util import response_generator

logger = get_logger("view.scoreboard")

router = APIRouter(
    prefix="/scoreboard",
    tags=["scoreboard"],
)


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskRow:
    idx: int

    name: str
    url: str

    points: int
    time: str

    fb: UserID | None


@dataclass(frozen=True, kw_only=True, slots=True)
class ScoreboardRow:
    user_id: UserID
    display_name: str

    position: int
    score: int
    solved_count: int
    fb_count: int
    fb_tasks: list[TaskRow]

    last_task: TaskRow | None

    solutions_url: str

    solved_indexes_csv: str


@dataclass(frozen=True, kw_only=True, slots=True)
class ScoreboardContext:
    compact_rows: list[ScoreboardRow]
    users_total: int
    tasks_total: int


def _build_scoreboard_context(
    request: Request,
    scoreboard: list[UserDB.ScoreboardProjection],
    tasks_list: list[schema.Task],
    *,
    solution_route_name: str = "scoreboard_solutions_page",
    solution_route_params: Mapping[str, object] | None = None,
) -> ScoreboardContext:
    # NEUROSLOP
    # (but a little less now...)

    sorted_tasks = sorted(tasks_list, key=lambda t: (t.scoring.points, t.category))
    task_index: dict[schema.TaskID, TaskRow] = {}

    for idx, task in enumerate(sorted_tasks, start=1):
        first_pwn = task.first_pwned_str()
        task_index[task.task_id] = TaskRow(
            idx=idx,
            name=task.task_name,
            url=str(request.url_for("one_task_page", task_id=task.task_id)),
            points=task.points,
            time="",
            fb=first_pwn[0] if first_pwn else None,
        )

    first_bloods_by_user: dict[schema.UserID, int] = {}
    first_blood_tasks_by_user: dict[schema.UserID, list[schema.TaskID]] = {}
    for task in sorted_tasks:
        if not task.pwned_by:
            continue

        first_solver_id = min(task.pwned_by.items(), key=lambda x: x[1])[0]
        first_bloods_by_user[first_solver_id] = first_bloods_by_user.get(first_solver_id, 0) + 1
        first_blood_tasks_by_user.setdefault(first_solver_id, []).append(task.task_id)

    compact_rows: list[ScoreboardRow] = []
    for idx, sb_user in enumerate(scoreboard):
        position = idx + 1

        last_task: TaskRow | None = None
        if sb_user.solved_tasks:
            last_task_id, last_solve_time = sb_user.get_last_solve_time()
            if last_task_id and last_task_id in task_index:
                last_task = dataclasses.replace(
                    task_index[last_task_id],
                    time=schema.task.template_format_time(last_solve_time),
                )

        route_params = dict(solution_route_params or {})
        route_params["user_id"] = sb_user.user_id
        solved_indexes = sorted(task_index[task_id].idx for task_id in sb_user.solved_tasks if task_id in task_index)
        fb_count = sum(1 for task in task_index.values() if task.fb == sb_user.user_id)
        fb_tasks = [task_index[task_id] for task_id in first_blood_tasks_by_user.get(sb_user.user_id, [])]

        compact_rows.append(
            ScoreboardRow(
                user_id=sb_user.user_id,
                display_name=sb_user.display_name,
                position=position,
                score=sb_user.score,
                solved_count=len(sb_user.solved_tasks),
                fb_count=fb_count,
                fb_tasks=fb_tasks,
                last_task=last_task,
                solutions_url=str(request.url_for(solution_route_name, **route_params)),
                solved_indexes_csv=",".join(str(i) for i in solved_indexes),
            ),
        )

    return ScoreboardContext(
        compact_rows=compact_rows,
        users_total=len(scoreboard),
        tasks_total=len(sorted_tasks),
    )


def _build_compare_context(
    request: Request,
    scoreboard: list[UserDB.ScoreboardProjection],
    tasks_list: list[schema.Task],
    *,
    user_a: schema.UserID | None,
    user_b: schema.UserID | None,
) -> dict[str, object]:
    # NEUROSLOP

    sorted_tasks = sorted(tasks_list, key=lambda t: (t.scoring.points, t.category))
    users = [
        {
            "user_id": str(row.user_id),
            "display_name": row.display_name,
            "score": row.score,
        }
        for row in scoreboard
    ]

    user_map = {str(row.user_id): row for row in scoreboard}
    user_a_str = str(user_a) if user_a else ""
    user_b_str = str(user_b) if user_b else ""

    row_a = user_map.get(user_a_str)
    row_b = user_map.get(user_b_str)

    chips: list[dict[str, object]] = []
    if row_a and row_b:
        for idx, task in enumerate(sorted_tasks, start=1):
            a_solved = task.task_id in row_a.solved_tasks
            b_solved = task.task_id in row_b.solved_tasks

            if a_solved and b_solved:
                state = "both"
            elif a_solved:
                state = "only-a"
            elif b_solved:
                state = "only-b"
            else:
                state = "none"

            chips.append(
                {
                    "state": state,
                    "title": f"{task.task_name} | {task.points} | {task.category}",
                    "url": str(request.url_for("one_task_page", task_id=task.task_id)),
                    "index": idx,
                },
            )

    return {
        "users": users,
        "selected_a": user_a_str,
        "selected_b": user_b_str,
        "row_a": row_a,
        "row_b": row_b,
        "chips": chips,
        "tasks_total": len(sorted_tasks),
    }


def _build_task_legend_context(
    request: Request,
    tasks_list: list[schema.Task],
) -> dict[str, object]:
    # NEUROSLOP

    sorted_tasks = sorted(tasks_list, key=lambda t: (t.scoring.points, t.category))
    task_legend: list[dict[str, object]] = []

    for idx, task in enumerate(sorted_tasks, start=1):
        task_legend.append(
            {
                "index": idx,
                "name": task.task_name,
                "points": task.points,
                "category": str(task.category),
                "url": str(request.url_for("one_task_page", task_id=task.task_id)),
            },
        )

    return {"task_legend": task_legend}


def _build_user_solutions_context(
    request: Request,
    user_row: UserDB.ScoreboardProjection,
    tasks_list: list[schema.Task],
) -> dict[str, object]:
    # NEUROSLOP

    sorted_tasks = sorted(tasks_list, key=lambda t: (t.scoring.points, t.category))
    last_task_id = user_row.get_last_solve_time()[0] if user_row.solved_tasks else None

    chips = []
    for task in sorted_tasks:
        first_solver = task.first_pwned_str()
        chips.append(
            {
                "title": f"{task.task_name} | {task.points} | {task.category}",
                "url": str(request.url_for("one_task_page", task_id=task.task_id)),
                "solved": task.task_id in user_row.solved_tasks,
                "is_last": task.task_id == last_task_id,
                "is_first": bool(first_solver) and first_solver[0] == user_row.user_id,
            },
        )

    return {"chips": chips}


@router.get("/")
async def scoreboard_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
) -> HTMLResponse:
    scoreboard = list(await UserDB.get_filtered_projected_scoreboard())
    context = _build_scoreboard_context(request, scoreboard, list(tasks))

    return await response_generator(
        request,
        "scoreboard.jhtml",
        {
            "curr_user": user,
            "legend_url": str(request.url_for("scoreboard_legend_page")),
            "compare_url": str(request.url_for("scoreboard_compare_page")),
            "ctx": context,
        },
    )


@router.get("/scoreboard_compare")
async def scoreboard_compare_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
    user_a: Annotated[schema.UserID | None, Query()] = None,
    user_b: Annotated[schema.UserID | None, Query()] = None,
) -> HTMLResponse:
    scoreboard = list(await UserDB.get_filtered_projected_scoreboard())
    if not user_a and user and any(row.user_id == user.user_id for row in scoreboard):
        user_a = user.user_id
    if not user_a and scoreboard:
        user_a = scoreboard[0].user_id
    if not user_b:
        for row in scoreboard:
            if not user_a or row.user_id != user_a:
                user_b = row.user_id
                break

    context = _build_compare_context(
        request,
        scoreboard,
        list(tasks),
        user_a=user_a,
        user_b=user_b,
    )

    return await response_generator(
        request,
        "scoreboard_compare.jhtml",
        {
            "curr_user": user,
            **context,
        },
    )


@router.get("/scoreboard_legend")
async def scoreboard_legend_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
) -> HTMLResponse:
    context = _build_task_legend_context(request, list(tasks))
    return await response_generator(request, "partials/scoreboard_legend.jhtml", context)


@router.get("/scoreboard_solutions/{user_id}")
async def scoreboard_solutions_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
    user_id: schema.UserID,
) -> HTMLResponse:
    scoreboard = await UserDB.get_filtered_projected_scoreboard()
    user_row = next((row for row in scoreboard if row.user_id == user_id), None)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    context = _build_user_solutions_context(request, user_row, list(tasks))
    return await response_generator(request, "partials/scoreboard_solutions.jhtml", context)
