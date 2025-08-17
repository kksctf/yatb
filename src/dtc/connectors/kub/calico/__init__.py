from typing import ClassVar

from lightkube.codecs import resource_registry
from lightkube.core import resource as res

from . import models as m


@resource_registry.register
class IPPool(res.GlobalResource, m.IPPool):
    _api_info = res.ApiInfo(
        resource=res.ResourceDef("projectcalico.org", "v3", "IPPool"),
        plural="ippools",
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
