from pymongo import MongoClient
from pymongo.database import Database

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class MongoConnectionProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: MongoClient | None = None

    def get_database(self) -> Database:
        # used for handing out the one shared client, opened lazily on first use
        if self._client is None:
            self._client = MongoClient(self._settings.mongo_uri, serverSelectionTimeoutMS=10_000, tz_aware=True)
            logger.info("mongo_connected", extra={"database": self._settings.mongo_database})
        return self._client[self._settings.mongo_database]

    def check_health(self) -> bool:
        # used at startup so a missing container fails loudly instead of at partition forty
        try:
            self.get_database().client.admin.command("ping")
            return True
        except Exception as error:
            logger.error("mongo_unreachable", extra={"reason": str(error)})
            return False

    def close(self) -> None:
        # used on shutdown so a cli run does not leave sockets open
        if self._client is not None:
            self._client.close()
            self._client = None
