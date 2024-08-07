import asyncio
from contextlib import AsyncExitStack
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
    registry: str = "docker.io/rubikoid",
) -> None:
    source = source.resolve()

    async with AsyncExitStack() as exit_stack:
        x = await exit_stack.enter_async_context(KubeConnector())

        secrets = []
        if registry == "docker.io/rubikoid":
            raw_docker_json_secret = x.api.docker_config_json_secret(docker_login, docker_password)
            docker_json_secret = await exit_stack.enter_async_context(raw_docker_json_secret)
            secrets.append(docker_json_secret)

        await x.api.build(
            name,
            source,
            destination_override=f"{registry}/{name}:{tag}",
            secrets=secrets,
        )


@app.command()
async def run_service(
    src: Path,
    name: str | None = None,
    flag: str | None = None,
    *,
    skip_build: bool = False,
) -> None:
    src = src.resolve()
    compose = load_compose(src)

    name = name or src.name
    flag = flag or "flag{TEST}"

    async with KubeConnector() as x:
        stack = await x.api.service(
            name,
            compose,
            flag,
            host=x.api._BASE_IP,
            port=31337,
            skip_build=skip_build,
        )
        input("...?>")
        await stack.aclose()


@app.command()
async def test_service() -> None:
    src = Path("dynamic_tasks_app") / "tests" / "examples" / "service"
    src = src.resolve()

    compose = load_compose(src)

    name = "test-serivce"
    flag = "flag{TEST}"

    async with KubeConnector() as x:
        stack = await x.api.service(
            name,
            compose,
            flag,
            host=x.api._BASE_IP,
            port=31337,
        )
        input("...?>")
        await stack.aclose()


@app.command()
async def test():
    async with KubeConnector() as x:
        await x.test()


if __name__ == "__main__":
    app()
