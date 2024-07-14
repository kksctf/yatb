import asyncio
from pathlib import Path

from loguru import logger
from .connectors.kub import KubeConnector


async def test(x: KubeConnector):
    # await x.test()

    src = Path("dynamic_tasks_app") / "tests" / "examples" / "builder"
    src = src.resolve()
    await x.api.build(src)

    # await x.test()


async def main():
    x = KubeConnector()
    await x.init()
    try:
        await test(x)
    finally:
        await x.close()


if __name__ == "__main__":
    asyncio.run(main())
