import asyncio
import json
import textwrap
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import TypeGuard, TypeVar, overload

from lightkube import operators as op
from lightkube.core import resource as r
from lightkube.core.async_client import AsyncClient
from lightkube.core.client import AllNamespacedResource, GlobalResource
from lightkube.core.exceptions import ObjectDeleted
from lightkube.models.apps_v1 import DeploymentSpec
from lightkube.models.batch_v1 import JobSpec
from lightkube.models.core_v1 import (
    PersistentVolumeClaimSpec,
    PodSpec,
    PodTemplateSpec,
    ServicePort,
    ServiceSpec,
    VolumeResourceRequirements,
)
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta
from lightkube.resources.apps_v1 import Deployment
from lightkube.resources.batch_v1 import Job
from lightkube.resources.core_v1 import PersistentVolumeClaim, Pod, Service
from lightkube.types import CascadeType
from loguru import logger

from ...utils.asc import async_first
from .calico import IPPool
from .calico import models as cm
from .kubevirt import VirtualMachineInstance
from .kubevirt import models as km  # DomainSpec, Memory, VirtualMachineInstanceSpec, Volume


class ImpossibleError(Exception):
    pass


class NonOptMeta(ObjectMeta):
    name: str
    namespace: str


def check_meta(metadata: ObjectMeta | None) -> TypeGuard[NonOptMeta]:
    return bool(metadata and metadata.name and metadata.namespace)


_T = TypeVar("_T", bound=r.NamespacedResource)
_TG = TypeVar("_TG", bound=r.GlobalResource)


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

    def simple_pod(self, name: str, namespace: str, pod_spec: PodSpec) -> Pod:
        return Pod(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=pod_spec,
        )

    def simple_deployment(
        self,
        name: str,
        namespace: str,
        pod_spec: PodSpec,
        replicas: int = 1,
        *,
        extra_pod_meta: Mapping = {},
    ) -> Deployment:
        return Deployment(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=DeploymentSpec(
                replicas=replicas,
                selector=LabelSelector(matchLabels={"app.kubernetes.io/name": name}),
                template=PodTemplateSpec(
                    metadata=ObjectMeta(labels={"app.kubernetes.io/name": name}, **extra_pod_meta),
                    spec=pod_spec,
                ),
            ),
        )

    def simple_service(
        self,
        name: str,
        namespace: str,
        external_port: int,
        target_port: int,
        external_ips: list[str],
        name_suffix: str = "",
        selector: str = "app.kubernetes.io/name",
        protocol: str = "TCP",
    ) -> Service:
        return Service(
            metadata=ObjectMeta(
                name=f"{name}{name_suffix}",
                namespace=namespace,
            ),
            spec=ServiceSpec(
                # type="LoadBalancer",
                # allocateLoadBalancerNodePorts=False,
                # type="NodePort",
                externalIPs=external_ips,
                selector={selector: name},
                ports=[ServicePort(port=external_port, targetPort=target_port, protocol=protocol)],
                ipFamilyPolicy="PreferDualStack",
            ),
        )

    def simple_internal_service(
        self,
        name: str,
        namespace: str,
        target_port: int,
        selector: str = "app.kubernetes.io/name",
    ) -> Service:
        return Service(
            metadata=ObjectMeta(
                name=name,
                namespace=namespace,
            ),
            spec=ServiceSpec(
                selector={selector: name},
                ports=[ServicePort(port=target_port, targetPort=target_port)],
                ipFamilyPolicy="PreferDualStack",
            ),
        )

    def simple_volume(
        self,
        name: str,
        namespace: str,
        *,
        size: str = "128Mi",
    ) -> PersistentVolumeClaim:
        return PersistentVolumeClaim(
            metadata=ObjectMeta(
                name=name,
                namespace=namespace,
            ),
            spec=PersistentVolumeClaimSpec(
                accessModes=["ReadWriteOnce"],
                storageClassName="local-path",
                resources=VolumeResourceRequirements(
                    requests={"storage": size},
                ),
            ),
        )
        # return PersistentVolume(
        #     metadata=ObjectMeta(
        #         name=name,
        #         namespace=namespace,
        #     ),
        #     spec=PersistentVolumeSpec(
        #         capacity={"storage": size},
        #         accessModes=["ReadWriteOnce"],
        #         persistentVolumeReclaimPolicy="Delete",
        #         storageClassName="local-storage", # idk
        #         local=
        #     ),
        # )

    def simple_vm(
        self,
        name: str,
        namespace: str,
        *,
        image: str,
        # custm: str,
        cpu: int = 1,
        memory: str = "1.5Gi",
        user_data_raw: dict = {},
        ports: dict[str, int] = {},
    ) -> VirtualMachineInstance:
        user_data = f"""\
        #cloud-config
        {json.dumps(user_data_raw, indent=None)}
        """
        return VirtualMachineInstance(
            metadata=ObjectMeta(
                name=name,
                namespace=namespace,
                labels={
                    "kubevirt.io/domain": name,
                },
            ),
            spec=km.VirtualMachineInstanceSpec(
                domain=km.DomainSpec(
                    cpu=km.CPU(cores=cpu),
                    memory=km.Memory(guest=memory),
                    devices=km.Devices(
                        interfaces=[
                            km.Interface(
                                name="default",
                                masquerade={},
                                ports=[km.Port(name=i, port=v) for i, v in ports.items()],
                            ),
                        ],
                        disks=[
                            km.Disk(
                                name="disk",
                                disk=km.DiskTarget(bus="virtio"),
                                bootOrder=1,
                            ),
                            # km.Disk(
                            #     name="custm",
                            #     cdrom=km.CDRomTarget(bus="sata"),
                            # ),
                        ],
                    ),
                ),
                networks=[
                    km.Network(name="default", pod=km.PodNetwork()),
                ],
                volumes=[
                    km.Volume(
                        name="disk",
                        containerDisk=km.ContainerDiskSource(
                            # image="registry.local/drive/windows-1:latest",
                            image=image,
                            path="/disk/drive.qcow2",
                        ),
                        # hostDisk=km.HostDisk(
                        #     # path="/etc/test-image/nixos.qcow2",
                        #     # path="/nix/store/rv0ilnns8rs3bxdlab5l6697jnwcm9z5-debian-12-generic-amd64.qcow2",
                        #     path="/debian.qcow2",
                        #     type="Disk",
                        # ),
                    ),
                    km.Volume(
                        name="cloudinitvolume",
                        cloudInitNoCloud=km.CloudInitNoCloudSource(
                            userData=textwrap.dedent(user_data),
                        ),
                    ),
                    # km.Volume(
                    #     name="virtio-drivers",
                    #     containerDisk=km.ContainerDiskSource(image="quay.io/kubevirt/virtio-container-disk"),
                    # ),
                    # km.Volume(
                    #     name="custm",
                    #     # containerDisk=km.ContainerDiskSource(image="registry.local/drive/windows-1-custm:latest"),
                    #     containerDisk=km.ContainerDiskSource(image=custm),
                    # ),
                ],
            ),
        )

    def simple_ip_pool(
        self,
        name: str,
        *,
        cidr: str,
        automatic: bool = True,
        block_size: int = 26,
    ) -> IPPool:
        return IPPool(
            metadata=ObjectMeta(
                name=f"pool-{name}",
            ),
            spec=cm.IPPoolSpec(
                blockSize=block_size,
                cidr=cidr,
                natOutgoing=True,
                assignmentMode="Automatic" if automatic else "Manual",
            ),
        )

    async def find_pod(self, job: Job) -> Pod:
        if not check_meta(job.metadata):
            raise ImpossibleError

        return await async_first(
            self.list(
                Pod,
                labels={"app.kubernetes.io/name": op.equal(job.metadata.name)},
                namespace=job.metadata.namespace,
            ),
        )

    async def find_volume(self, name: str, namespace: str) -> PersistentVolumeClaim:
        return await self.get(PersistentVolumeClaim, name, namespace=namespace)

    async def wait_for_job_ready_with_logs(
        self,
        job: Job,
        *,
        timeout: float = 240,
    ):
        if not check_meta(job.metadata):
            raise ImpossibleError

        logger.info(f"Wait for job '{job.metadata.namespace}.{job.metadata.name}' ready")
        async with asyncio.timeout(timeout):
            await self.wait_ex(
                Job,
                job.metadata.name,
                namespace=job.metadata.namespace,
                cb=lambda x: x.get("ready", 0) == 1,
            )

        job_pod = await self.find_pod(job)

        if not check_meta(job_pod.metadata):
            raise ImpossibleError

        pod_info = f"'{job_pod.metadata.namespace}.{job_pod.metadata.name}'"
        logger.info(f"Waiting for job's pod {pod_info} be ready")
        job_pod = await self.wait(
            Pod,
            job_pod.metadata.name,
            for_conditions=["PodReadyToStartContainers"],
            namespace=job_pod.metadata.namespace,
        )

        if not check_meta(job_pod.metadata):
            raise ImpossibleError

        logger.info(
            f"Pod {pod_info} ready",
        )
        async for line in self.log(
            job_pod.metadata.name,
            namespace=job_pod.metadata.namespace,
            follow=True,
            newlines=False,
        ):
            logger.trace(f"Running {pod_info}: {line}")

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

    @asynccontextmanager
    async def ctx_global(
        self,
        resource: _TG,
        *,
        grace_period: int | None = None,
        cascade: CascadeType | None = None,
    ) -> AsyncGenerator[_TG, None]:
        res = await self.create(resource)

        # FIXME: make this better. I don't want to do it now.
        meta: ObjectMeta = res.metadata  # pyright: ignore[reportAttributeAccessIssue]
        name = meta.name
        if not isinstance(name, str):
            raise ImpossibleError(f"{res = }")

        try:
            yield res
        finally:
            await self.delete(
                res=type(resource),
                name=name,
                grace_period=grace_period,  # pyright: ignore[reportArgumentType] # lib
                cascade=cascade,  # pyright: ignore[reportArgumentType] # lib
            )  # type: ignore
            logger.info(f"Cleaned '{type(resource).__name__}/{meta.name}'")
