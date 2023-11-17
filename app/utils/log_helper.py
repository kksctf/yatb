import logging
from pathlib import Path
from typing import ClassVar

from ..config import settings

APP_NAME = "yatb"
MODULES = [
    "init",
    "schema",
    "schema.auth",
    "schema.scoring",
    "schema.user",
    "schema.task",
    "auth",
    "api",
    "api.admin",
    "db",
    "db.tasks",
    "db.users",
    "db.beanie",
    "view",
]


def get_logger(
    module_name: str,
    *,
    app_name: str = APP_NAME,
) -> logging.Logger:
    return logging.getLogger(f"{app_name}.{module_name}")


class DebugFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    raw_format = (
        "{green}{{asctime}}{r} | {level}{{levelname:<8s}}{r} | {{name}} | {{filename}}:{{lineno}} | {{message}}"
    )

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: grey,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    FMTS: dict[int, logging.Formatter] = {}

    def get_formatter(self, levelno: int) -> logging.Formatter:
        if levelno not in self.FMTS:
            log_color = self.COLORS.get(levelno)
            log_fmt = self.raw_format.format(
                level=log_color,
                grey=self.grey,
                green=self.green,
                yellow=self.yellow,
                red=self.red,
                bold_red=self.bold_red,
                r=self.reset,
            )
            self.FMTS[levelno] = logging.Formatter(log_fmt, style="{")

        return self.FMTS[levelno]

    def format(self, record):  # noqa: A003
        return self.get_formatter(record.levelno).format(record)


def setup_loggers(
    base_name: str = APP_NAME,
    base_folder: Path | None = None,  # Path("logs"),
    modules: list[str] | tuple[str] = ("init",),
    root_format: str = "level=%(levelname)s | module=%(name)s | msg=%(message)s",
    module_format: str = "level=%(levelname)s | msg=%(message)s ",
    root_formatter: logging.Formatter | None = None,
    module_formatter: logging.Formatter | None = None,
) -> logging.Logger:
    if base_folder and not base_folder.exists():
        base_folder.mkdir(parents=True)

    root_formatter = root_formatter or logging.Formatter(root_format)
    module_formatter = module_formatter or logging.Formatter(module_format)

    root_logger = logging.getLogger(base_name)
    root_logger.setLevel(logging.DEBUG)

    if base_folder:
        fh = logging.FileHandler(base_folder / f"{base_name}.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(root_formatter)
        root_logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    ch.setFormatter(root_formatter)
    root_logger.addHandler(ch)

    for module in modules:
        module_logger = logging.getLogger(f"{base_name}.{module}")
        module_logger.setLevel(logging.DEBUG)

        if base_folder:
            fh = logging.FileHandler(base_folder / f"{base_name}.{module}.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(module_formatter)
            module_logger.addHandler(fh)

    return root_logger


if settings.DEBUG:
    root_logger = setup_loggers(
        base_name=APP_NAME,
        modules=MODULES,
        root_formatter=DebugFormatter(),
    )
else:
    root_logger = setup_loggers(
        base_name=APP_NAME,
        base_folder=Path("logs"),
        modules=MODULES,
        root_format="level=%(levelname)s time=%(asctime)s module=%(name)s at=%(funcName)s:%(lineno)d msg='%(message)s'",
        module_format="level=%(levelname)s time=%(asctime)s at=%(funcName)s:%(lineno)d msg='%(message)s'",
    )

logging.getLogger(APP_NAME).propagate = False
