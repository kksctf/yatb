from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import TypeGuard, TypeVar, overload

from lightkube.core import resource as r
from lightkube.core.async_client import AsyncClient
from lightkube.core.client import AllNamespacedResource, GlobalResource
from lightkube.core.exceptions import ObjectDeleted
from lightkube.models.apps_v1 import DeploymentSpec
from lightkube.models.batch_v1 import JobSpec
from lightkube.models.core_v1 import (
    PodSpec,
    PodTemplateSpec,
    ServicePort,
    ServiceSpec,
)
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta
from lightkube.resources.apps_v1 import Deployment
from lightkube.resources.batch_v1 import Job
from lightkube.resources.core_v1 import Service
from lightkube.types import CascadeType
from loguru import logger


class ImpossibleError(Exception):
    pass


class NonOptMeta(ObjectMeta):
    name: str
    namespace: str


def check_meta(metadata: ObjectMeta | None) -> TypeGuard[NonOptMeta]:
    return bool(metadata and metadata.name and metadata.namespace)


_T = TypeVar("_T", bound=r.NamespacedResource)


class AsyncClientEx(AsyncClient):
    @overload
    async def wait_ex(
        self,
        res: type[GlobalResource],
        name: str,
        *,
        cb: Callable[[dict], bool],
    ) -> GlobalResource: ...

    @overload
    async def wait_ex(
        self,
        res: type[AllNamespacedResource],
        name: str,
        *,
        cb: Callable[[dict], bool],
        namespace: str | None = None,
    ) -> AllNamespacedResource: ...

    async def wait_ex(
        self,
        res,  # type[GlobalResource] | type[AllNamespacedResource]
        name: str,
        *,
        cb: Callable[[dict], bool],
        namespace: str | None = None,
    ):
        """
        Wait for specified conditions, but better.

        **parameters**

        * **res** - Resource kind.
        * **name** - Name of resource to wait for.
        * **namespace** - *(optional)* Name of the namespace containing the object (Only for namespaced resources).
        """

        kind = r.api_info(res).plural
        full_name = f"{kind}/{name}"

        watch = self.watch(
            res,
            namespace=namespace,  # pyright: ignore[reportArgumentType]
            fields={"metadata.name": name},
        )
        try:
            async for op, obj in watch:
                if obj.status is None:
                    continue

                if op == "DELETED":
                    raise ObjectDeleted(full_name)

                try:
                    status = obj.status.to_dict()
                except AttributeError:
                    status = obj.status

                if cb(status):
                    return obj
        finally:
            # we ensure the async generator is closed before returning
            await watch.aclose()  # pyright: ignore[reportAttributeAccessIssue]

    def simple_job(self, name: str, namespace: str, pod_spec: PodSpec) -> Job:
        return Job(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=JobSpec(
                template=PodTemplateSpec(
                    metadata=ObjectMeta(labels={"app.kubernetes.io/name": name}),
                    spec=pod_spec,
                ),
            ),
        )

    def simple_deployment(self, name: str, namespace: str, pod_spec: PodSpec, replicas: int = 1) -> Deployment:
        return Deployment(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=DeploymentSpec(
                replicas=replicas,
                selector=LabelSelector(matchLabels={"app.kubernetes.io/name": name}),
                template=PodTemplateSpec(
                    metadata=ObjectMeta(labels={"app.kubernetes.io/name": name}),
                    spec=pod_spec,
                ),
            ),
        )

    def simple_service(
        self, name: str, namespace: str, external_port: int, target_port: int, external_ips: list[str]
    ) -> Service:
        return Service(
            metadata=ObjectMeta(
                name=name,
                namespace=namespace,
            ),
            spec=ServiceSpec(
                # type="LoadBalancer",
                # allocateLoadBalancerNodePorts=False,
                # type="NodePort",
                externalIPs=external_ips,
                selector={"app.kubernetes.io/name": name},
                ports=[ServicePort(port=external_port, targetPort=target_port)],
            ),
        )

    @asynccontextmanager
    async def ctx(
        self,
        resource: _T,
        *,
        grace_period: int | None = None,
        cascade: CascadeType | None = None,
    ) -> AsyncGenerator[_T, None]:
        res = await self.create(resource)

        # FIXME: make this better. I don't want to do it now.
        meta: ObjectMeta = res.metadata  # pyright: ignore[reportAttributeAccessIssue]
        if not check_meta(meta):
            raise ImpossibleError(f"{res = }")

        try:
            yield res
        finally:
            await self.delete(
                type(resource),
                meta.name,
                namespace=meta.namespace,
                grace_period=grace_period,  # pyright: ignore[reportArgumentType] # lib
                cascade=cascade,  # pyright: ignore[reportArgumentType] # lib
            )
            logger.info(f"Cleaned '{type(resource).__name__}/{meta.namespace}.{meta.name}'")
