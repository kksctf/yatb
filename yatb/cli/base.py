import typer
from pydantic_settings import BaseSettings
from rich.console import Console


class Settings(BaseSettings):
    files_url: str = "http://127.0.0.1:9999"
    base_url: str = "http://127.0.0.1:8080"

    tasks_ip: str = "127.0.0.1"

    tasks_domain: str = "tasks.kksctf.ru"
    flag_base: str = "kks"


settings = Settings()
tapp = typer.Typer()
c = Console()
