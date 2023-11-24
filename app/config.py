import datetime
import subprocess
from pathlib import Path
from typing import Self

from pydantic import MongoDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_TOKEN = "default_token_CHANGE_ME"  # noqa: S105 # intended


class DefaultTokenError(ValueError):
    pass


class Settings(BaseSettings):
    DEBUG: bool = False
    PROFILING: bool = False

    TOKEN_PATH: str = "/api/users/login"

    # bot token for notifications
    BOT_TOKEN: str | None = None
    CHAT_ID: int | None = None

    # event time. should be in UTC
    EVENT_START_TIME: datetime.datetime = datetime.datetime(1077, 12, 12, 9, 0, tzinfo=datetime.UTC)
    EVENT_END_TIME: datetime.datetime = datetime.datetime(2077, 12, 13, 9, 0, tzinfo=datetime.UTC)

    # database name
    DB_NAME: str = "yatb"
    MONGO: MongoDsn = "mongodb://root:root@127.0.0.1:27017"  # type: ignore

    # JWT settings
    JWT_SECRET_KEY: str = _DEFAULT_TOKEN
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 2  # two days
    FLAG_SIGN_KEY: str = _DEFAULT_TOKEN

    # rename docs. Why? Idk, but you maybe want this
    FASTAPI_DOCS_URL: str = "/docs"
    FASTAPI_REDOC_URL: str = "/redoc"
    FASTAPI_OPENAPI_URL: str = "/openapi.json"

    # if you enable metrics - you must change that URL, metrics can expose some sensitive info
    MONITORING_URL: str = "/metrics"

    # version magic
    VERSION: str = ""
    COMMIT: str | None = None

    FLAG_BASE: str = "kks"
    CTF_NAME: str = "YATB-dev"

    API_TOKEN: str = _DEFAULT_TOKEN
    WS_API_TOKEN: str = _DEFAULT_TOKEN

    ENABLED_AUTH_WAYS: list[str] = [  # noqa: RUF012
        "SimpleAuth",
        "TelegramAuth",
        "CTFTimeOAuth",
        "GithubOAuth",
        "DiscordOAuth",
    ]

    @model_validator(mode="after")
    def check_non_default_tokens(self) -> Self:
        if self.DEBUG:
            return self

        token_check_list = ["JWT_SECRET_KEY", "FLAG_SIGN_KEY", "API_TOKEN", "WS_API_TOKEN"]
        for token_name in token_check_list:
            if getattr(self, token_name) == _DEFAULT_TOKEN:
                raise DefaultTokenError(f"Field '{token_name}' have default token value")

        return self

    @model_validator(mode="after")
    def __version_solver__(self) -> Self:
        if (Path() / ".git").exists():
            self.VERSION += subprocess.check_output(["git", "rev-parse", "HEAD"]).decode()[:8]  # noqa: S607, S603
            self.VERSION += (
                "-Modified"
                if len(subprocess.check_output(["git", "status", "--porcelain"])) > 0  # noqa: S603, S607
                else ""
            )
        else:
            self.VERSION += "0.6.2a2"
            if self.COMMIT:
                self.VERSION += f"-{self.COMMIT[:8]}"

        if self.DEBUG:
            self.VERSION += "-dev"
        else:
            self.VERSION += "-prod"

        return self

    model_config = SettingsConfigDict(
        # env_prefix="YATB_",
        env_file="yatb.env",
        env_file_encoding="utf-8",
        extra="allow",
    )


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
