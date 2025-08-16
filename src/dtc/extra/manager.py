#!/usr/bin/env python3
# just a very simple builder

import rich
from cyclopts import App
from cyclopts.config import Env

app = App(
    "Task building manager",
    config=Env(""),
)
c = rich.console.Console()


@app.command()
def run(
    flag: str,
):
    c.log(f"Building task with {flag = }")
    

if __name__ == "__main__":
    app()
