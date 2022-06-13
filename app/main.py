from typing import List, Dict, Optional
from datetime import timedelta

import asyncio
import aiohttp
import uuid
import os
import sys
import pickle

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, OAuth2

from . import app, auth, db, schema, root_logger
from .config import settings
from .api import api_tasks

"""
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # start_time = time.time()
    response = await call_next(request)
    # process_time = time.time() - start_time
    # response.headers["X-Process-Time"] = str(process_time)
    return response
"""

if settings.DEBUG:
    try:
        root_logger.warning("Timing debug loadeding")

        from asgi_server_timing import ServerTimingMiddleware  # noqa
        import fastapi  # noqa
        import pydantic  # noqa

        app.add_middleware(
            ServerTimingMiddleware,
            calls_to_track={
                "1deps": (fastapi.routing.solve_dependencies,),
                "2main": (fastapi.routing.run_endpoint_function,),
                # "3valid": (pydantic.fields.ModelField.validate,),
                "4encode": (fastapi.encoders.jsonable_encoder,),
                "5render": (
                    fastapi.responses.JSONResponse.render,
                    fastapi.responses.ORJSONResponse.render,
                    fastapi.responses.HTMLResponse.render,
                    fastapi.responses.PlainTextResponse.render,
                ),
                "6tasks": (api_tasks.api_tasks_get,),
                "6task": (api_tasks.api_task_get,),
            },
        )
        root_logger.warning("Timing debug loaded")

    except Exception:
        pass
