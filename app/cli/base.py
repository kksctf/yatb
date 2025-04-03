import typer
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console


class Settings(BaseSettings):
    BASE_URL: str = "http://127.0.0.1:9000"
    FILES_BASE: str = "http://127.0.0.1:9001"

    FLAG_BASE: str = "flag"

    model_config = SettingsConfigDict(
        env_file="yatb.env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
tapp = typer.Typer()
c = Console()
