import cyclopts
import rich.console
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    server: str = "http://127.0.0.1:8000"


settings = Settings()  # pyright: ignore[reportCallIssue]
c = rich.console.Console()
app = cyclopts.App()


if __name__ == "__main__":
    app()
