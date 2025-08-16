import random
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import cycle

from loguru import logger

from ..config import settings


@dataclass
class HostPortPair:
    host: str
    port: int


class PortsController:
    occupated_ports: dict[str, list[int]]
    external_ips: Iterator[str]

    def __init__(self) -> None:
        self.occupated_ports = defaultdict(list)
        self.external_ips = cycle(settings.EXTERNAL_IPS)

    def get_host_and_port(self) -> HostPortPair:
        host = next(self.external_ips)
        occupated_ports = self.occupated_ports[host]

        while (port := random.randint(settings.PORT_START, settings.PORT_END)) in occupated_ports:  # noqa: S311
            logger.info(f"Found occupated port: {port} ;( ")

        occupated_ports.append(port)
        logger.info(f"Found free {host}:{port}")
        return HostPortPair(host, port)

    def free_port(self, pair: HostPortPair) -> None:
        occupated_ports = self.occupated_ports[pair.host]
        occupated_ports.remove(pair.port)

    async def close(self):
        pass
