import cyclopts
import rich.console
from pydantic_settings import BaseSettings
from rich.console import Console


class Settings(BaseSettings):
    server: str


settings = Settings()  # pyright: ignore[reportCallIssue]
c = rich.console.Console()
app = cyclopts.App()


if __name__ == "__main__":
    app()
