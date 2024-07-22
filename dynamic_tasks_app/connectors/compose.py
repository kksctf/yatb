from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from loguru import logger
from pydantic import AfterValidator, BaseModel, BeforeValidator, ValidationInfo, field_validator, validator

from ..utils.pydantic_yaml import parse_yaml_file_as


def fix_relative_path(v: Path, info: ValidationInfo) -> Path:
    if not info.context:
        raise Exception("Something went wrong")

    source_path: Path = info.context["source_path"]
    return (source_path / v).resolve()


@dataclass
class PortInfo:
    # external_port: int
    internal_port: int


def parse_port_info(v: str) -> PortInfo:
    if v.count(":") > 1:
        raise ValueError(f"Parsing {v!r} error: specifying ip's is not supported")
    ports = v.split(":")
    if len(ports) == 2:  # noqa: PLR2004
        return PortInfo(int(ports[1]))
    return PortInfo(int(ports[0]))


RelateivePath = Annotated[Path, AfterValidator(fix_relative_path)]
Port = Annotated[PortInfo, BeforeValidator(parse_port_info)]


class ServiceBuild(BaseModel):
    context: RelateivePath
    dockerfile: RelateivePath = Path("Dockerfile")


class Service(BaseModel):
    image: str | None = None

    build: ServiceBuild | RelateivePath | None = None

    command: list[str] | str | None = None

    ports: list[Port] = []

    @property
    def prepared_command(self) -> list[str] | None:
        if not self.command:
            return None

        if isinstance(self.command, str):
            return self.command.split(" ")

        return self.command


class Compose(BaseModel):
    version: str

    services: dict[str, Service]


def load_compose(source: Path) -> Compose:
    yaml = source / "docker-compose.yml"
    assert source.is_absolute()
    assert source.is_dir()
    assert yaml.exists()

    compose = parse_yaml_file_as(Compose, yaml, context={"source_path": source})
    return compose
