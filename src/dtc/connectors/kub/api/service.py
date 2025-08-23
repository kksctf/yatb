from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path

from lightkube.models.core_v1 import (
    Container,
    ContainerPort,
    EnvVar,
    EnvVarSource,
    PodSpec,
    SecretKeySelector,
)
from lightkube.models.core_v1 import ResourceRequirements as kResourceRequirements
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import Namespace, Secret, Service
from loguru import logger

from dtc.config import settings
from dtc.connectors.compose import Compose
from dtc.controllers.ports_controller import PortsEnv

from ..client import ImpossibleError, check_meta
from .base import KubeApiBase


class KubeApiService(KubeApiBase):
    async def service(
        self,
        name: str,
        ns: Namespace,
        ns_name: str,
        compose: Compose,
        flag: str,
        *,
        # ip_in_cluster: str | None = None,
        stack: AsyncExitStack,
        ports_env: PortsEnv,
        skip_build: bool = False,
        extra_env: Mapping[str, str] = {},
        # extra_route: tuple[str, str] | None = None,
    ) -> Namespace:
        # images: dict[str, str] = {}
        containers: dict[str, Container] = {}

        # build stage
        for svc_name, svc in compose.services.items():
            # if it is a VM description: just go away
            if svc.vm:
                continue

            if not svc.build:
                if not svc.image:
                    raise Exception("no")
                image = svc.image
            elif isinstance(svc.build, Path):
                # TODO: do not build on every run
                image = await self.build(f"{name}-{svc_name}", svc.build, skip_build=skip_build)
            else:
                image = await self.build(
                    f"{name}-{svc_name}",
                    svc.build.context,
                    dockerfile=svc.build.dockerfile,
                    skip_build=skip_build,
                )

            # TODO: eww
            image = self.fix_image_name(image)

            env: list[EnvVar] = []
            for env_key, env_value in list(svc.parsed_env.items()) + list(extra_env.items()):
                if env_key == "FLAG":  # WTF: monkeypatch or production ready?????
                    continue

                env.append(
                    EnvVar(
                        name=env_key,
                        value=env_value,
                    ),
                )

            logger.trace(f"Creating container for {svc_name = } with {env = }")

            # create container descriptor thing
            containers[svc_name] = Container(
                name=svc_name,
                image=image,
                args=svc.prepared_command,
                ports=[ContainerPort(port.internal_port) for port in svc.ports]
                + [ContainerPort(port) for port in svc.expose],
                env=env,
                resources=kResourceRequirements(
                    requests=svc.resource.requests.model_dump(),
                    limits=svc.resource.limits.model_dump(),
                ),
            )

        # define function for container patching
        def patch_container(container: Container, secret: Secret, key: str) -> Container:
            if not check_meta(secret.metadata):
                raise ImpossibleError

            if container.env is None:
                container.env = []

            container.env.append(
                EnvVar(
                    name=key,
                    valueFrom=EnvVarSource(
                        secretKeyRef=SecretKeySelector(
                            name=secret.metadata.name,
                            key=key,
                        ),
                    ),
                ),
            )

            return container

        flag_secret = await stack.enter_async_context(
            self.client.ctx(
                Secret(
                    metadata=ObjectMeta(
                        name=f"{name}-flag",
                        namespace=ns_name,
                    ),
                    immutable=True,
                    stringData={"FLAG": flag},
                ),
            ),
        )

        # run stage
        services: list[Service] = []

        for svc_name, container in containers.items():
            svc = compose.services[svc_name]
            if svc.vm:  # don't do this on VMs... for now?
                continue

            patch_container(container, flag_secret, "FLAG")

            # TODO: instead of creating thousands of services, make one service with multiple
            # ServicePort

            for exposing_port in svc.expose:
                service = self.client.ctx(
                    self.client.simple_internal_service(
                        svc_name,
                        ns_name,
                        exposing_port,
                    ),
                )
                service = await stack.enter_async_context(service)
                services.append(service)

            for port in svc.ports:
                public_hp = await ports_env.get_port()
                service = self.client.ctx(
                    self.client.simple_service(
                        svc_name,
                        ns_name,
                        public_hp.port,
                        port.internal_port,
                        settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING[public_hp.host],
                        name_suffix="-public",
                    ),
                )
                service = await stack.enter_async_context(service)
                services.append(service)

            deployment = self.client.ctx(
                self.client.simple_deployment(
                    svc_name,
                    ns_name,
                    PodSpec(
                        containers=[container],
                    ),
                ),
            )
            await stack.enter_async_context(deployment)

        for service in services:
            if not service.spec or not service.spec.ports:
                raise ImpossibleError

            if not service.spec.externalIPs:
                logger.info(f"Service without externalIPs {service.spec = } (99% this is ok)")
                continue

            # logger.info(f"{service = }")

            addr = f"http://{service.spec.externalIPs[0]}:{service.spec.ports[0].port}"

            logger.info(
                f"Started at {service.spec.externalIPs} -> {[i.port for i in service.spec.ports]}; "
                f"{addr = }; "  # ...
                f"{service.spec.clusterIPs = }",
            )

        return ns
