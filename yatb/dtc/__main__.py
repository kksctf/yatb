import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TypeVar

from cyclopts import App
from lightkube.core import resource as r
from lightkube.models.core_v1 import (
    Container,
    EmptyDirVolumeSource,
    PodSpec,
    Volume,
    VolumeMount,
)
from lightkube.resources.core_v1 import Pod
from loguru import logger

from .config import settings
from .connectors.kub import KubeConnector
from .connectors.kub.client import check_meta

_T = TypeVar("_T", bound=r.NamespacedResource)
_TG = TypeVar("_TG", bound=r.GlobalResource)

app = App("dynamic_tasks_app helper")

extra = [
    (Path(__file__).resolve().parent / "extra" / "builder", "yatb-k8s-builder-base"),
    (Path(__file__).resolve().parent / "extra" / "openvpn", "yatb-k8s-openvpn"),
]


@app.command()
async def build(
    docker_login: str,
    docker_password: str,
    source: Path = Path(__file__).resolve().parent / "extra" / "builder",
    name: str = "yatb-k8s-builder-base",
    tag: str = "latest",
    registry: str = f"{settings.EXTERNAL_DOCKER_REGISTRY}/rubikoid",
) -> None:
    source = source.resolve()

    async with AsyncExitStack() as exit_stack:
        x = await exit_stack.enter_async_context(KubeConnector(run_workers=False))

        secrets = []
        if registry == f"{settings.EXTERNAL_DOCKER_REGISTRY}/rubikoid":
            raw_docker_json_secret = x.api.docker_config_json_secret(docker_login, docker_password)
            docker_json_secret = await exit_stack.enter_async_context(raw_docker_json_secret)
            secrets.append(docker_json_secret)

        await x.api.build(
            name,
            source,
            destination_override=f"{registry}/{name}:{tag}",
            secrets=secrets,
        )


@app.command()
async def build_all(
    docker_login: str,
    docker_password: str,
    tag: str = "latest",
    registry: str = f"{settings.EXTERNAL_DOCKER_REGISTRY}/rubikoid",
) -> None:
    async with AsyncExitStack() as exit_stack:
        x = await exit_stack.enter_async_context(KubeConnector(run_workers=False))

        secrets = []
        if registry == f"{settings.EXTERNAL_DOCKER_REGISTRY}/rubikoid":
            raw_docker_json_secret = x.api.docker_config_json_secret(docker_login, docker_password)
            docker_json_secret = await exit_stack.enter_async_context(raw_docker_json_secret)
            secrets.append(docker_json_secret)

        for source, name in extra:
            source = source.resolve()  # noqa: PLW2901

            await x.api.build(
                name,
                source,
                destination_override=f"{registry}/{name}:{tag}",
                secrets=secrets,
            )


# @app.command()
# async def run_service(
#     src: Path,
#     name: str | None = None,
#     flag: str | None = None,
#     *,
#     skip_build: bool = False,
# ) -> None:
#     src = src.resolve()
#     compose = load_compose(src)

#     name = name or src.name
#     flag = flag or "flag{TEST}"

#     async with KubeConnector() as x:
#         stack = await x.api.service(
#             name,
#             compose,
#             flag,
#             host="192.168.1.44",
#             port=31337,
#             skip_build=skip_build,
#         )
#         input("...?>")
#         await stack.aclose()


# @app.command()
# async def test_service() -> None:
#     src = Path("dynamic_tasks_app") / "tests" / "examples" / "service"
#     src = src.resolve()

#     compose = load_compose(src)

#     name = "test-serivce"
#     flag = "flag{TEST}"

#     async with KubeConnector() as x:
#         stack = await x.api.service(
#             name,
#             compose,
#             flag,
#             host="192.168.1.44",
#             port=31337,
#         )
#         input("...?>")
#         await stack.aclose()


@app.command()
async def run_oneshot(
    src: Path,
    name: str | None = None,
    flag: str | None = None,
) -> None:
    src = src.resolve()

    async with KubeConnector(run_workers=False) as x:
        await x.api.oneshot(
            name or "testing",
            src,
            env={
                "FLAG": flag or "mshp{sample_flag}",
                "BACKEND_URL": "http://TODO",
                "RANDOM_STRING_SEQ": "c38b5ov23t5ov2iu3t5",
            },
            s3_prefix="rubikoid/test",
        )


@app.command()
async def run_vm() -> None:
    external_ips = ["202:ae5d:1f6b:bac7:2b4e:304c:ef7:47ca", "192.168.10.44"]
    async with AsyncExitStack() as exit_stack:
        x = await exit_stack.enter_async_context(KubeConnector(run_workers=False))

        async def m(r: _T) -> _T:
            return await exit_stack.enter_async_context(x.api.client.ctx(r))

        async def mg(r: _TG) -> _TG:
            return await exit_stack.enter_async_context(x.api.client.ctx_global(r))

        ns_name, ns = await exit_stack.enter_async_context(
            x.api.run_in_ns(
                "test",
                # prefix="vm",
            ),
        )

        ipv4pool = await mg(
            x.api.client.simple_ip_pool(
                f"{ns_name}-v4",
                cidr="10.100.0.0/26",  # .1-.62
                automatic=False,
            ),
        )
        ipv6pool = await mg(
            x.api.client.simple_ip_pool(
                f"{ns_name}-v6",
                cidr="2001:cafe:10::/112",
            ),
        )

        if not ns.metadata:
            raise Exception

        if not ipv4pool.metadata or not ipv4pool.metadata.name:
            raise Exception

        if not ipv6pool.metadata or not ipv6pool.metadata.name:
            raise Exception

        if not ns.metadata.annotations:
            ns.metadata.annotations = {}

        # ns.metadata.annotations["cni.projectcalico.org/ipv4pools"] = f'["{ippool.metadata.name}"]'
        # ns = await x.api.client.apply(ns)

        patch = {
            "metadata": {
                "annotations": {
                    "cni.projectcalico.org/ipv4pools": f'["{ipv4pool.metadata.name}"]',
                    "cni.projectcalico.org/ipv6pools": f'["{ipv6pool.metadata.name}"]',
                },
            },
        }
        ns = await x.api.client.patch(type(ns), name=ns_name, obj=patch)

        # ovpn, ovpn_svc = await x.api.openvpn(
        #     ns,
        #     ip_in_cluster="10.100.0.5",
        #     vpn_net="10.200.0.1",  # .1-.14
        #     stack=exit_stack,
        #     external_ips=external_ips,
        # )

        # vm = await m(
        #     x.api.client.simple_vm(
        #         name="testing-vm",
        #         namespace=ns_name,
        #         ip_in_cluster="10.100.0.10",
        #     ),
        # )

        svc = await m(
            x.api.client.simple_service(
                name="testing-vm",
                namespace=ns_name,
                external_port=30000,
                target_port=3389,
                external_ips=external_ips,
                selector="kubevirt.io/domain",
                name_suffix="-rdp",
            ),
        )

        # svc1 = await m(
        #     x.api.client.simple_service(
        #         name="testing-vm",
        #         namespace=ns_name,
        #         external_port=445,
        #         target_port=445,
        #         external_ips=["202:ae5d:1f6b:bac7:2b4e:304c:ef7:47ca", "192.168.10.44"],
        #         selector="kubevirt.io/domain",
        #         name_suffix="-smb",
        #     ),
        # )

        # print(f"{ovpn = } \n")

        # print(f"{ovpn_svc = } \n")

        # print(f"{vm = } \n")

        # print()
        # print(f"{svc = }")

        # print()
        # print(f"{svc1 = }")

        input(">?")


@app.command()
async def cat(image: str, cmd: str) -> None:
    async with AsyncExitStack() as exit_stack:
        x = await exit_stack.enter_async_context(KubeConnector(run_workers=False))

        async def m(r: _T) -> _T:
            return await exit_stack.enter_async_context(x.api.client.ctx(r))

        async def mg(r: _TG) -> _TG:
            return await exit_stack.enter_async_context(x.api.client.ctx_global(r))

        ns_name, ns = await exit_stack.enter_async_context(x.api.run_in_ns("file-extractor"))

        pod = x.api.client.simple_pod(
            "file-extractor",
            namespace=ns_name,
            pod_spec=PodSpec(
                containers=[
                    Container(
                        name="target",
                        image=image,
                        command=["/errr"],
                        volumeMounts=[
                            VolumeMount(
                                name="shared-volume",
                                mountPath="/disk",
                            ),
                        ],
                    ),
                    Container(
                        name="helper",
                        image="busybox",
                        command=["sh", "-c", f"{cmd}"],
                        volumeMounts=[
                            VolumeMount(
                                name="shared-volume",
                                mountPath="/mnt",
                            ),
                        ],
                    ),
                ],
                volumes=[
                    Volume(name="shared-volume", emptyDir=EmptyDirVolumeSource()),
                ],
            ),
        )
        async with x.api.client.ctx(pod) as pod:
            if not check_meta(pod.metadata):
                raise Exception

            logger.info(f"Wait for pod '{pod.metadata.namespace}.{pod.metadata.name}' ready")
            async with asyncio.timeout(60):
                await x.api.client.wait(
                    Pod,
                    pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    for_conditions=["PodReadyToStartContainers"],
                )

            async for line in x.api.client.log(
                pod.metadata.name,
                namespace=pod.metadata.namespace,
                container="helper",
                follow=True,
                newlines=False,
            ):
                logger.trace(f"{line}")


@app.command()
async def test():
    async with KubeConnector() as x:
        pass
        # await x.test()


if __name__ == "__main__":
    app()
