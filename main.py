#!/usr/bin/env python3
from app import app

if __name__ == "__main__":
    import uvicorn

    dev = 1
    if dev == 0:
        # use this one
        uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
    if dev == 1:
        uvicorn.run("main:app", host="127.0.0.1", port=8080, log_level="debug", reload=False, debug=False)
    if dev == 2:
        uvicorn.run("main:app", host="127.0.0.1", port=8080, log_level="debug", workers=2)
