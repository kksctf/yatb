import typer
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="yatb.env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
tapp = typer.Typer()
c = Console()
