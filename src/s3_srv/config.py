from os import environ

from pydantic_settings import BaseSettings, SettingsConfigDict

S3_CONFIG_OVERRIDE = environ.get("S3_CONFIG_OVERRIDE", "yatb.env")


class S3Settings(BaseSettings):
    S3_HOST: str
    S3_PORT: int = 80

    S3_ACCESS: str
    S3_SECRET: str

    S3_HTTPS: bool = True
    S3_REGION: str | None = None

    STATIC_BUCKET_NAME: str = "static-files"
    TASKS_BUCKET_NAME: str = "dynamic-tasks-build-source"
    BUILD_RESULT_BUCKET_NAME: str = "dynamic-tasks-build-results"

    @property
    def s3_endpoint(self) -> str:
        if self.S3_HOST.count(":") > 1:
            return f"[{self.S3_HOST}]:{self.S3_PORT}"

        return f"{self.S3_HOST}:{self.S3_PORT}"

    model_config = SettingsConfigDict(
        env_file=S3_CONFIG_OVERRIDE,
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = S3Settings()  # pyright: ignore[reportCallIssue]
