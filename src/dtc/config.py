import datetime
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_TOKEN = "default_token_CHANGE_ME"  # noqa: S105 # intended

DEFAULT_TTL = datetime.timedelta(hours=1)


class DefaultTokenError(ValueError):
    pass


class Settings(BaseSettings):
    DEBUG: bool = False
    TESTING: bool = False

    KUBE_CONFIG_PATH: Path | None = None
    KUBE_CONFIG_SERVER_OVERRIDE: str | None = None

    S3_HOST_KANIKO: str
    S3_PORT_KANIKO: int

    DOCKER_REGISTRY_HOST: str
    DOCKER_REGISTRY_PORT: int
    DOCKER_REGISTRY_HOST_LOCAL: str | None = None
    DOCKER_REGISTRY_PORT_LOCAL: int | None = None

    EXTERNAL_TO_INTERNAL_IPS_MAPPING: dict[str, list[str]]

    PORT_START: int = 20000
    PORT_END: int = 40000

    S3_PROXY_HOST: str = ""

    ADMIN_PASSWORD: str = _DEFAULT_TOKEN

    ASYNC_WORKERS_COUNT: int = 8

    DYNAMIC_TASKS_ETCD: str
    DYNAMIC_TASKS_ETCD_PORT: int = 2379

    EXTERNAL_DOCKER_REGISTRY: str = "ghcr.io"

    VPN_PORT_START: int = 11337
    VPN_PORT_END: int = 12337

    VPN_USER_NET: str = "10.10.0.0/16"
    VPN_TASK_NET: str = "10.100.0.0/16"
    VPN_TASK_VPN_NET: str = "10.200.0.0/16"
    VPN_TASK_PREFIX_LEN: int = 28
    VPN_USER_NET_PREFIX: int = 16

    DO_WORK: bool = True

    @property
    def kube_config_path(self) -> str | None:
        if not self.KUBE_CONFIG_PATH:
            return None

        return str(self.KUBE_CONFIG_PATH.expanduser().resolve())

    @model_validator(mode="after")
    def check_non_default_tokens(self) -> Self:
        if self.DEBUG or self.TESTING:
            return self

        token_check_list = ["ADMIN_PASSWORD"]
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
