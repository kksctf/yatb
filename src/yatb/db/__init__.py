from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from yatb.config import settings
from yatb.utils.log_helper import get_logger

from .task import TaskDB
from .user import UserDB

logger = get_logger("db.task")


class DBClient:
    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase

    async def init(self) -> None:
        self.client = AsyncIOMotorClient(str(settings.MONGO), tz_aware=True)
        self.db = self.client[settings.DB_NAME]
        await init_beanie(
            database=self.db,
            document_models=[TaskDB, UserDB],
        )
        logger.info("Beanie init ok")

    async def close(self) -> None:
        logger.info("DB close ok")

    async def reset_db(self) -> None:
        if not (settings.DEBUG or settings.TESTING):
            logger.warning(f"DB Reset without debug ({settings.DEBUG = }) or testing {settings.TESTING = }")
            return

        await self.client.drop_database(settings.DB_NAME)


db = DBClient()
