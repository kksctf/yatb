import datetime
from pathlib import Path
import subprocess
from typing import List, Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
    TOKEN_PATH: str = "/api/users/login"

    # bot token for notifications
    BOT_TOKEN: Optional[str] = None
    CHAT_ID: int = 0

    # event time. should be in UTC
    EVENT_START_TIME: datetime.datetime = datetime.datetime(1077, 12, 12, 9, 0)
    EVENT_END_TIME: datetime.datetime = datetime.datetime(2077, 12, 13, 9, 0)

    # database name
    DB_NAME: Path = Path(".") / "file_db.db"

    # JWT settings
    JWT_SECRET_KEY: str = "CHANGE_ME_OR_DIE13434523465"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 2  # two days
    FLAG_SIGN_KEY: str = "YOU_ALSO_NEED_TO_CHANGE_ME"

    # rename docs. Why? Idk, but you maybe want this
    FASTAPI_DOCS_URL: str = "/docs"
    FASTAPI_REDOC_URL: str = "/redoc"
    FASTAPI_OPENAPI_URL: str = "/openapi.json"

    # if you enable metrics - you must change that URL, metrics can expose some sensitive info
    MONITORING_URL: str = "/metrics"

    # version magic
    VERSION: str = ""
    COMMIT: Optional[str] = None

    FLAG_BASE: str = "kks"
    CTF_NAME: str = "YATB-dev"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.version_solver()

    def version_solver(self):
        if (Path(".") / ".git").exists():
            self.VERSION += subprocess.check_output(["git", "rev-parse", "HEAD"]).decode()[:8]
            self.VERSION += "-Modified" if len(subprocess.check_output(["git", "status", "--porcelain"])) > 0 else ""
        else:
            self.VERSION += "a0.5.2"
            if self.COMMIT:
                self.VERSION += f"-{self.COMMIT[:8]}"

        if self.DEBUG:
            self.VERSION += "-dev"
        else:
            self.VERSION += "-prod"

    class Config:
        env_prefix = "YATB_"
        env_file = "yatb.env"
        env_file_encoding = "utf-8"


settings = Settings()

# ==== CLASSES FOR MD RENDERER ====
MD_CLASSES_TASKS = {
    "p": "card-text",
}

MD_ATTRS_TASKS = {
    "a": {
        "target": "_blank",
        "rel": "noopener noreferrer",
        # "class": "btn btn-outline-primary btn-sm col-auto m-1 flex-fill"
    }
}
# ==== CLASSES FOR MD RENDERER ====
