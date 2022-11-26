import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
from random import randint
from itertools import groupby
from copy import deepcopy as copy

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.routing import APIRoute, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import parse_obj_as
from starlette.routing import Router

from .. import auth, db, schema
from ..api import api_tasks as api_tasks
from ..api import api_users as api_users
from ..config import settings

logger = logging.getLogger("yatb.view")

_base_path = os.path.dirname(os.path.abspath(__file__))
templ = Jinja2Templates(directory=os.path.join(_base_path, "templates"))

router = APIRouter(
    prefix="",
    tags=["view"],
)


def route_generator(req: Request, base_path="/api", ignore_admin=True) -> Dict[str, str]:
    router: Router = req.scope["router"]
    ret = {}
    for r in router.routes:  # type: ignore # i'm 100% sure, that there should be only APIRoute objects
        r: APIRoute
        if r.path.startswith(base_path):
            if ignore_admin and r.path.startswith(f"{base_path}/admin"):
                continue
            dummy_params = {i: f"NONE_{i}" for i in set(r.param_convertors.keys())}
            ret[r.name] = req.url_for(name=r.name, **dummy_params)
    return ret


def response_generator(
        req: Request,
        filename: str,
        context: dict = {},
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background=None,
        ignore_admin=True,
) -> Response:
    context_base = {
        "request": req,
        "api_list": route_generator(req, ignore_admin=ignore_admin),
    }
    context_base.update(context)
    return templ.TemplateResponse(
        name=filename,
        context=context_base,
        status_code=status_code,
        headers=headers,
        media_type=media_type,
        background=background,
    )


def version_string():
    return f"kks-tb-{settings.VERSION}"


templ.env.globals["version_string"] = version_string
templ.env.globals["len"] = len
templ.env.globals["template_format_time"] = schema.task.template_format_time
templ.env.globals["set"] = set
templ.env.globals["isinstance"] = isinstance

templ.env.globals["DEBUG"] = settings.DEBUG
templ.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templ.env.globals["CTF_NAME"] = settings.CTF_NAME

from . import admin  # noqa

router.include_router(admin.router)


@router.get("/")
@router.get("/index")
async def index(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user_safe)):
    return await tasks_get_all(req, resp, user)


@router.get("/dockyard")
async def dockyard(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user)):
    if not req.query_params.get('task'):
        return 'Task name empty', 400

    return response_generator(
        req,
        "dockyard.jhtml",
        headers={'Set-Cookie': f'token={req.cookies.get("access_token")}'}
    )


@router.get("/about")
async def about_get(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user_safe)):
    return response_generator(
        req,
        "about.jhtml",
        {
            "request": req,
            "curr_user": user
        },
    )


@router.get("/tasks")
async def tasks_get_all(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user_safe)):
    tasks_list = await api_tasks.api_tasks_get(user)
    user_id = ''
    if user:
        user_id = user.user_id

    for i, task in enumerate(tasks_list):
        task = copy(task)
        task.description = task.description.replace('$USER_ID', str(user_id))
        task.description_html = task.description_html.replace('$USER_ID', str(user_id))
        tasks_list[i] = task

    return response_generator(
        req,
        "tasks.jhtml",
        {
            "request": req,
            "curr_user": user,
            "tasks": tasks_list,
        },
    )


@router.get("/scoreboard")
async def scoreboard_get(req: Request, resp: Response, r_user: schema.User = Depends(auth.get_current_user_safe)):
    scoreboard = await api_users.api_scoreboard_get_internal()
    r = lambda: randint(0, 255)

    # names = json.dumps(sorted([y.strftime('%Y-%m-%d | %H:%M') for x in scoreboard for y in x.solved_tasks.values() if x.solves_history != [0]]))
    if scoreboard:
        # names = [x for x in range(max([len(x.solved_tasks) for x in scoreboard]) + 1)]
        # solves_history = json.dumps(solves_history)
        dates = []  # X AXIS
        min_date = settings.EVENT_START_TIME
        max_date = settings.EVENT_END_TIME

        for i in range(((max_date - min_date).days * 24) + 1):
            dates.append(min_date + timedelta(hours=i + 3))  # Well, welcome to GMT + 3

        for i, x in enumerate(dates):
            dates[i] = dates[i].strftime('%d-%m-%Y %H')

        tsh = []

        for user in scoreboard[:10]:
            user_border_color = '#%02X%02X%02X' % (r(), r(), r())
            user_background_color = (r(), r(), r(), 1)
            grouped = groupby([{
                'score': x['score'],
                'solved_at': (x['solved_at'] + timedelta(hours=3)).strftime('%d-%m-%Y %H'),
                'uuid': x['uuid']
            } for x in user.solves_history], lambda z: z['solved_at'])
            grouped = [{'date': x, 'data': list(z)} for x, z in grouped]

            for i, x in enumerate(dates):
                if not [z for z in grouped if z['date'] == x]:
                    grouped.append({'date': x, 'data': [{
                        'score': 0
                    }]})

            grouped = sorted(grouped, key=lambda x: x['date'])

            result = [{'solved_at': x, 'score': 0} for x in dates]
            # ShitCode  / Fastfix
            if grouped[0]['date'] == '26-11-2022 09':
                grouped[0]['date'] = (datetime.strptime(grouped[0]['date'], '%d-%m-%Y %H') + timedelta(hours=3)).strftime(
                    '%d-%m-%Y %H')
                del grouped[1]
            for i, group in enumerate(grouped):
                r_i = [result.index(x) for x in result if x['solved_at'] == group['date']][0]
                if r_i != 0:
                    result[r_i]['score'] = result[r_i - 1]['score'] + sum([x['score'] for x in group['data']])
                else:
                    result[r_i]['score'] = sum([x['score'] for x in group['data']])

            # for i in range(1, len(result) - 1):
            #     result[i - 1]['score'] = r2[]

            c_d = datetime.utcnow() + timedelta(hours=3)

            rem = [x for x in result if datetime.strptime(x['solved_at'], '%d-%m-%Y %H') > c_d]
            [result.remove(x) for x in rem]

            result = [x['score'] for x in sorted(result, key=lambda x: x['solved_at'])]
            if sum(result) == 0:
                result = [0]

            tsh.append({"label": user.username,
                        "data": result,
                        "borderColor": user_border_color,
                        "backgroundColor": user_background_color})

        solves_history = tsh
    else:
        solves_history = [],
        dates = []

    solves_history = json.dumps(solves_history)

    return response_generator(
        req,
        "scoreboard.jhtml",
        {
            "request": req,
            "curr_user": r_user,
            "scoreboard": scoreboard,
            "solved_history": solves_history,
            "x_axis": dates,
            "enumerate": enumerate,
            "len": len
        },
    )


@router.get("/login")
async def login_get(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user_safe)):
    return response_generator(
        req,
        "login.jhtml",
        {
            "request": req,
            "curr_user": user,
            "auth_ways": schema.auth.ENABLED_AUTH_WAYS,
        },
    )


@router.get("/tasks/{task_id}")
async def tasks_get_task(
        req: Request,
        resp: Response,
        task_id: uuid.UUID,
        user: schema.User = Depends(auth.get_current_user_safe),
):
    task = await api_tasks.api_task_get(task_id, user)

    user_id = ''

    if user:
        user_id = user.user_id
    task = copy(task)
    task.description = task.description.replace('$USER_ID', str(user_id))
    task.description_html = task.description_html.replace('$USER_ID', str(user_id))

    return response_generator(
        req,
        "task.jhtml",
        {
            "request": req,
            "curr_user": user,
            "selected_task": task,
        },
    )
