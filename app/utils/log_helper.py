import os
import logging

from typing import List


# logging.basicConfig(level=logging.WARNING,
#                     format="%(asctime)s - ROOT_%(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s")


def generate_loggers(
    base_name: str = "yatb",
    base_folder: str = "logs",
    modules: List[str] = ["schema", "api"],
    # root_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    root_format: str = "level=%(levelname)s time=%(asctime)s module=%(name)s at=%(funcName)s:%(lineno)d msg=%(message)s",
    # module_format: str = "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    module_format: str = "level=%(levelname)s time=%(asctime)s at=%(funcName)s:%(lineno)d msg=%(message)s",
):
    if not os.path.exists(base_folder):
        os.mkdir(base_folder)

    root_logger = logging.getLogger(base_name)
    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(root_format)
    fh = logging.FileHandler(os.path.join(base_folder, f"{base_name}.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    root_logger.addHandler(ch)
    root_logger.addHandler(fh)

    for module in modules:
        logger = logging.getLogger(f"{base_name}.{module}")
        logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(os.path.join(base_folder, f"{base_name}.{module}.log"), encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        # ch = logging.StreamHandler()
        # ch.setLevel(logging.WARNING)

        formatter = logging.Formatter(module_format)
        # ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # logger.addHandler(ch)
        logger.addHandler(fh)
        # logger = logging.getLogger("uvicorn.error")

    return root_logger
