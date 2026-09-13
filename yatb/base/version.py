import subprocess
from pathlib import Path

__version__ = "0.7.2"


def get_version(*, debug: bool = False, commit: str | None = None) -> str:
    root = Path(__file__).resolve().parents[2]
    if (root / ".git").exists():
        version = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()[:8]  # noqa: S603, S607
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=root):  # noqa: S603, S607
            version += "-Modified"
    else:
        version = __version__
        if commit:
            version += f"-{commit[:8]}"
    return f"{version}-{'dev' if debug else 'prod'}"
