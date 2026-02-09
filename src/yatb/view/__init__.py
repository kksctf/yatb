import asyncio
import datetime
import gettext
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias

from fastapi import BackgroundTasks, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute as _APIRoute
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from yatb import auth, i18n, schema
from yatb.api import tasks
from yatb.config import settings
from yatb.db.task import TaskDB
from yatb.db.user import UserDB
from yatb.schema.feature_flags import active_feature_flags
from yatb.utils import md
from yatb.utils.httpx import IS_HTTPX
from yatb.utils.log_helper import get_logger

logger = get_logger("view")

_base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=_base_path / "templates")

TRANSLATIONS = {
    lang: gettext.translation(
        domain="messages",
        localedir=Path(__file__).parent.parent / "locale",
        languages=[lang],
        fallback=True,
    )
    for lang in i18n.SUPPORTED
}

router = APIRouter(
    prefix="",
    tags=["view"],
)


def route_generator(req: Request, base_path: str = "/api", *, ignore_admin: bool = True) -> dict[str, str]:
    router: Router = req.scope["router"]
    ret = {}
    for r in router.routes:
        if not isinstance(r, _APIRoute):
            continue
        if not r.path.startswith(base_path):
            continue
        if ignore_admin and r.path.startswith(f"{base_path}/admin"):
            continue

        dummy_params = {i: f"NONE_{i}" for i in set(r.param_convertors.keys())}
        ret[r.name] = str(req.url_for(r.name, **dummy_params))
    return ret


async def response_generator(  # noqa: PLR0913 # impossible to fix
    req: Request,
    filename: str,
    context: dict = {},  # noqa: B006 # iknew.
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTasks | None = None,
    *,
    ignore_admin: bool = True,
) -> _TemplateResponse:
    context_base = {
        "request": req,
        "api_list": route_generator(req, ignore_admin=ignore_admin),
    }
    context_base.update(context)
    return await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: templates.TemplateResponse(
            name=filename,
            context=context_base,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        ),
    )


def version_string() -> str:
    return f"kks-tb-{settings.VERSION}"


def _(text: str, request: Request) -> str:
    return TRANSLATIONS[request.state.lang].gettext(text)


templates.env.globals["version_string"] = version_string
templates.env.globals["len"] = len
templates.env.globals["template_format_time"] = schema.task.template_format_time
templates.env.globals["set"] = set
templates.env.globals["str"] = str
templates.env.globals["isinstance"] = isinstance
templates.env.globals["enumerate"] = enumerate

templates.env.globals["DEBUG"] = settings.DEBUG
templates.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templates.env.globals["CTF_NAME"] = settings.CTF_NAME
templates.env.globals["EVENT_START_TIME"] = settings.EVENT_START_TIME
templates.env.globals["EVENT_END_TIME"] = settings.EVENT_END_TIME
templates.env.globals["NOW"] = lambda: datetime.datetime.now(datetime.UTC)

templates.env.globals["_"] = _

from . import admin  # noqa

router.include_router(admin.router)


@dataclass
class _Cache:
    user_id_to_username: dict[schema.UserID, str]


async def get_cache(request: Request) -> _Cache:
    users = await UserDB.get_all_projected(UserDB.ScoreboardProjection)
    uid2name = {uuid: user.display_name for uuid, user in users.items()}

    return _Cache(user_id_to_username=uid2name)


Cache: TypeAlias = Annotated[_Cache, Depends(get_cache)]


@router.get("/")
@router.get("/index")
async def index(request: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(request, "index.jhtml", {"curr_user": user})


@router.get("/tasks")
async def tasks_page(
    req: Request,
    is_httpx: IS_HTTPX,
    cache: Cache,
    user: auth.CURR_USER_SAFE,
    tasks: tasks.VISIBLE_TASKS,
    show_solved: bool | None = Query(default=None),
    category: list[str] | None = Query(None),
) -> HTMLResponse:
    categories = {t.category for t in tasks}

    if not is_httpx:
        return await response_generator(
            req,
            "tasks.jhtml",
            {
                "curr_user": user,
                "tasks": tasks,
                "categories": categories,
                "uid2name": cache.user_id_to_username,
            },
        )

    tasks = [t for t in tasks if t.category in (category or [])]

    if not show_solved and user:
        tasks = [t for t in tasks if not t.is_solved_by(user)]

    return await response_generator(
        req,
        "partials/task_container.jhtml",
        {
            "curr_user": user,
            "tasks": tasks,
            "uid2name": cache.user_id_to_username,
        },
    )


@router.get("/tasks/{task_id}")
async def one_task_page(
    req: Request,
    cache: Cache,
    task: tasks.CURRENT_TASK,
    user: auth.CURR_USER_SAFE,
) -> HTMLResponse:
    return await response_generator(
        req,
        "task.jhtml",
        {
            "curr_user": user,
            "selected_task": task,
            "uid2name": cache.user_id_to_username,
        },
    )


def _build_scoreboard_context(
    request: Request,
    scoreboard: list[UserDB.ScoreboardProjection],
    tasks_list: list[schema.Task],
    *,
    solution_route_name: str,
    solution_route_params: Mapping[str, object] | None = None,
) -> dict[str, object]:
    sorted_tasks = sorted(tasks_list, key=lambda t: (t.scoring.points, t.category))
    task_index: dict[schema.TaskID, int] = {}
    task_name: dict[schema.TaskID, str] = {}
    task_url: dict[schema.TaskID, str] = {}
    task_points: dict[schema.TaskID, int] = {}

    for idx, task in enumerate(sorted_tasks, start=1):
        task_index[task.task_id] = idx
        task_name[task.task_id] = task.task_name
        task_url[task.task_id] = str(request.url_for("one_task_page", task_id=task.task_id))
        task_points[task.task_id] = task.points

    compact_rows = []
    for idx, sb_user in enumerate(scoreboard):
        position = idx + 1

        last_task = None
        if sb_user.solved_tasks:
            last_task_id, last_solve_time = sb_user.get_last_solve_time()
            if last_task_id and last_task_id in task_index:
                last_task = {
                    "index": task_index[last_task_id],
                    "name": task_name[last_task_id],
                    "url": task_url[last_task_id],
                    "points": task_points[last_task_id],
                    "time": schema.task.template_format_time(last_solve_time),
                }

        route_params = dict(solution_route_params or {})
        route_params["user_id"] = sb_user.user_id
        solved_indexes = sorted(task_index[task_id] for task_id in sb_user.solved_tasks if task_id in task_index)

        compact_rows.append(
            {
                "position": position,
                "display_name": sb_user.display_name,
                "score": sb_user.score,
                "user_id": str(sb_user.user_id),
                "solved_count": len(sb_user.solved_tasks),
                "last_task": last_task,
                "solutions_url": str(request.url_for(solution_route_name, **route_params)),
                "solved_indexes_csv": ",".join(str(i) for i in solved_indexes),
            },
        )

    return {
        "compact_rows": compact_rows,
        "users_total": len(scoreboard),
        "tasks_total": len(sorted_tasks),
    }


def _build_compare_context(
    request: Request,
    scoreboard: list[UserDB.ScoreboardProjection],
    tasks_list: list[schema.Task],
    *,
    user_a: schema.UserID | None,
    user_b: schema.UserID | None,
) -> dict[str, object]:
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


@router.get("/scoreboard")
async def scoreboard_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
) -> HTMLResponse:
    scoreboard = list(await UserDB.get_filtered_projected_scoreboard())
    context = _build_scoreboard_context(
        request,
        scoreboard,
        list(tasks),
        solution_route_name="scoreboard_solutions_page",
    )

    return await response_generator(
        request,
        "scoreboard.jhtml",
        {
            "curr_user": user,
            "legend_url": str(request.url_for("scoreboard_legend_page")),
            "compare_url": str(request.url_for("scoreboard_compare_page")),
            **context,
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
    del user
    context = _build_task_legend_context(request, list(tasks))
    return await response_generator(request, "partials/scoreboard_legend.jhtml", context)


@router.get("/scoreboard_solutions/{user_id}")
async def scoreboard_solutions_page(
    request: Request,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
    user_id: schema.UserID,
) -> HTMLResponse:
    del user
    scoreboard = await UserDB.get_filtered_projected_scoreboard()
    user_row = next((row for row in scoreboard if row.user_id == user_id), None)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    context = _build_user_solutions_context(request, user_row, list(tasks))
    return await response_generator(request, "partials/scoreboard_solutions.jhtml", context)


@router.get("/profile")
async def profile_page(request: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(
        request,
        "profile.jhtml",
        {
            "curr_user": user,
        },
    )


@router.get("/login")
async def login_page(req: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(
        req,
        "login.jhtml",
        {
            "curr_user": user,
            "auth_ways": [i for i in schema.auth.ENABLED_AUTH_WAYS if not i.FAKE],
        },
    )
