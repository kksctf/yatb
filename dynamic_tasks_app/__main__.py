import asyncio
from pathlib import Path

from cyclopts import App
from loguru import logger

from .connectors.compose import load_compose
from .connectors.kub import KubeConnector

app = App("dynamic_tasks_app helper")


@app.command()
async def build(
    docker_login: str,
    docker_password: str,
    source: Path = Path(__file__).resolve().parent / "extra",
    name: str = "yatb-k8s-builder-base",
    tag: str = "latest",
) -> None:
    async with (
        KubeConnector() as x,
        x.api.docker_config_json_secret(docker_login, docker_password) as docker_json_secret,
    ):
        await x.api.build(
            name,
            source,
            destination_override=f"rubikoid/yatb-k8s-builder-base:{tag}",
            secrets=[docker_json_secret],
        )


@app.command()
async def run_service(
    src: Path,
    name: str | None = None,
    flag: str | None = None,
) -> None:
    src = src.resolve()
    compose = load_compose(src)

    name = name or src.name
    flag = flag or "crab{TEST}"

    async with KubeConnector() as x:
        await x.api.service(name, compose, "flag{TEST}")


@app.command()
async def test():
    async with KubeConnector() as x:
        src = Path("dynamic_tasks_app") / "tests" / "examples" / "service"
        src = src.resolve()
        compose = load_compose(src)
        await x.api.service("test-svc", compose, "flag{TEST}")

        await x.test()

        # src = Path("dynamic_tasks_app") / "tests" / "examples" / "builder"
        # src = src.resolve()
        # name = "test-image"

        # await x.api.build(name, src)


if __name__ == "__main__":
    app()
