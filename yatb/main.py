from . import app, root_logger
from .api import api_tasks
from .config import settings

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
        import fastapi  # noqa
        import pydantic  # noqa
        from asgi_server_timing import ServerTimingMiddleware  # noqa # type: ignore

        root_logger.warning("Timing debug loading")

        app.add_middleware(
            ServerTimingMiddleware,
            calls_to_track={
                "1deps": (fastapi.routing.solve_dependencies,),  # type: ignore
                "2main": (fastapi.routing.run_endpoint_function,),
                # "3valid": (pydantic.fields.ModelField.validate,),
                "4encode": (fastapi.encoders.jsonable_encoder,),  # type: ignore
                "5render": (
                    fastapi.responses.JSONResponse.render,
                    fastapi.responses.ORJSONResponse.render,
                    fastapi.responses.HTMLResponse.render,
                    fastapi.responses.PlainTextResponse.render,
                ),
                # "6tasks": (api_tasks.api_tasks_get,),
                # "6task": (api_tasks.api_task_get,),
            },
        )
        root_logger.warning("Timing debug loaded")

    except ModuleNotFoundError:
        root_logger.warning("No timing extensions found")

if settings.PROFILING:
    try:
        from fastapi import Request
        from fastapi.responses import HTMLResponse
        from pyinstrument import Profiler

        root_logger.warning("pyinstrument loading")

        @app.middleware("http")
        async def profile_request(request: Request, call_next):
            profiling = request.query_params.get("profile", False)
            if profiling:
                profiler = Profiler(async_mode="enabled")  # interval=settings.profiling_interval
                profiler.start()
                await call_next(request)
                profiler.stop()
                return HTMLResponse(profiler.output_html())
            else:
                return await call_next(request)

        root_logger.warning("pyinstrument loaded")

    except ModuleNotFoundError:
        root_logger.warning("No pyinstrument found")
