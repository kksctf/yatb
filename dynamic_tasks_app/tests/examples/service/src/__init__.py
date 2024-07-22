from fastapi import FastAPI
import os

from fastapi.responses import PlainTextResponse

FLAG = os.environ.get("FLAG", "flag{example}")


app = FastAPI()


@app.get("/flag")
async def flag() -> PlainTextResponse:
    return PlainTextResponse(f"Flag: {FLAG}")


@app.get("/")
async def index() -> PlainTextResponse:
    return PlainTextResponse("Alive")
