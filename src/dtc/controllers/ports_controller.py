import random
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import cycle
from types import TracebackType

from loguru import logger

from ..config import settings


@dataclass
class HostPortPair:
    host: str
    port: int


class PortsEnv:
    ports_controller: "PortsController"
    tracking_ports: list[HostPortPair]

    def __init__(self, ports_controller: "PortsController") -> None:
        self.ports_controller = ports_controller
        self.tracking_ports = []

    async def get_port(self) -> HostPortPair:
        hp = self.ports_controller._get_host_and_port()
        self.tracking_ports.append(hp)
        return hp

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        logger.info(f"Cleaning ports: {self.tracking_ports = }")

        for port in self.tracking_ports:
            self.ports_controller._free_port(port)
        self.tracking_ports.clear()

        return None


class PortsController:
    occupated_ports: dict[str, list[int]]
    external_ips: Iterator[str]

    def __init__(self) -> None:
        self.occupated_ports = defaultdict(list)
        self.external_ips = cycle(settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING.keys())

    def get_env(self) -> PortsEnv:
        return PortsEnv(self)

    def _get_host_and_port(self) -> HostPortPair:
        host = next(self.external_ips)
        occupated_ports = self.occupated_ports[host]

        while (port := random.randint(settings.PORT_START, settings.PORT_END)) in occupated_ports:  # noqa: S311
            logger.info(f"Found occupated port: {port} ;( ")

        occupated_ports.append(port)
        logger.info(f"Found free {host}:{port}")
        return HostPortPair(host, port)

    def _free_port(self, pair: HostPortPair) -> None:
        occupated_ports = self.occupated_ports[pair.host]
        occupated_ports.remove(pair.port)

    async def close(self):
        pass
