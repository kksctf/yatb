import typer
from rich.console import Console

files_domain = "http://127.0.0.1:9999"
base_url = "http://127.0.0.1:8080"
FLAG_BASE = "kks"

tapp = typer.Typer()
c = Console()
