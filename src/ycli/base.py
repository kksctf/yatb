import cyclopts
import rich.console
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    UPSTREAM: str = "http://127.0.0.1:8000"
    PUBLIC_FILES_DOMAIN: str = "http://127.0.0.1:8001"

    model_config = SettingsConfigDict(
        env_file="yatb.env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
c = rich.console.Console()
app = cyclopts.App()

if __name__ == "__main__":
    app()
