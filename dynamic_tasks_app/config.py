import datetime
from pathlib import Path
from typing import Self
from uuid import UUID

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_TOKEN = "default_token_CHANGE_ME"  # noqa: S105 # intended

DEFAULT_TTL = datetime.timedelta(hours=1)


class DefaultTokenError(ValueError):
    pass


class Settings(BaseSettings):
    DEBUG: bool = False
    TESTING: bool = False

    FLAG_SIGN_KEY: str = _DEFAULT_TOKEN

    DYNAMIC_TASKS_CONTROLLER_TOKEN: str | None = None

    KUBE_CONFIG_PATH: Path | None = None

    S3_HOST: str
    S3_PORT: int = 80
    S3_ACCESS: str
    S3_SECRET: str

    EXTERNAL_IPS: list[str]
    PORT_START: int = 20000
    PORT_END: int = 40000

    UUID_TO_PATH_MAPPING: dict[UUID, Path] = {}

    @property
    def kube_config_path(self) -> str | None:
        if not self.KUBE_CONFIG_PATH:
            return None

        return str(self.KUBE_CONFIG_PATH.expanduser().resolve())

    @property
    def s3_endpoint(self) -> str:
        return f"{self.S3_HOST}:{self.S3_PORT}"

    @model_validator(mode="after")
    def check_non_default_tokens(self) -> Self:
        if self.DEBUG or self.TESTING:
            return self

        token_check_list = ["FLAG_SIGN_KEY"]
        for token_name in token_check_list:
            if getattr(self, token_name) == _DEFAULT_TOKEN:
                raise DefaultTokenError(f"Field '{token_name}' have default token value")

        return self

    model_config = SettingsConfigDict(
        env_file="yatb.env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
