from typing import ClassVar

from lightkube.codecs import resource_registry
from lightkube.core import resource as res

from . import models as m


class VirtualMachineInstanceStatus(res.NamespacedSubResource, m.VirtualMachineInstanceStatus):
    _api_info = res.ApiInfo(
        resource=res.ResourceDef("kubevirt.io", "v1", "VirtualMachineInstance"),
        parent=res.ResourceDef("kubevirt.io", "v1", "VirtualMachineInstance"),
        plural="virtualmachineinstances",
        verbs=["get", "patch", "put"],
        action="status",
    )


@resource_registry.register
class VirtualMachineInstance(res.NamespacedResourceG, m.VirtualMachineInstance):
    _api_info = res.ApiInfo(
        resource=res.ResourceDef("kubevirt.io", "v1", "VirtualMachineInstance"),
        plural="virtualmachineinstances",
        verbs=[
            "delete",
            "deletecollection",
            "get",
            "global_list",
            "global_watch",
            "list",
            "patch",
            "post",
            "put",
            "watch",
        ],
    )

    Status: ClassVar = VirtualMachineInstanceStatus
