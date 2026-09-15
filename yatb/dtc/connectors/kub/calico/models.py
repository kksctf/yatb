# ruff: noqa: N815, UP007
from typing import Optional

from lightkube.core.schema import DictMixin, dataclass
from lightkube.models import meta_v1

#

# #
# @dataclass
# class _(DictMixin):
#     pass


# https://docs.tigera.io/calico/latest/reference/resources/ippool#spec
@dataclass
class IPPoolSpec(DictMixin):
    cidr: str
    """ IP range to use for this pool.
    """

    blockSize: Optional[int] = None
    """ The CIDR size of allocation blocks used by this pool.
        Blocks are allocated on demand to hosts and are used to aggregate routes.
        The value can only be set when the pool is created.
    """

    ipipMode: Optional[str] = None
    """ The mode defining when IPIP will be used. Cannot be set at the same time as vxlanMode.
        Always, CrossSubnet, Never
    """

    vxlanMode: Optional[str] = None
    """ The mode defining when VXLAN will be used. Cannot be set at the same time as ipipMode.
        Always, CrossSubnet, Never
    """

    natOutgoing: Optional[bool] = None
    """ When enabled, packets sent from Calico networked containers
        in this pool to destinations outside of any Calico IP pools will be masqueraded.
    """

    disabled: Optional[bool] = None
    """ When set to true, Calico IPAM will not assign addresses from this pool.
    """

    disableBGPExport: Optional[bool] = None
    """ Disable exporting routes from this IP Pool's CIDR over BGP.
    """

    nodeSelector: Optional[str] = None
    """ Selects the nodes that Calico IPAM should assign addresses from this pool to.
    """

    allowedUses: Optional[list[str]] = None
    """ Controls whether the pool will be used for automatic assignments of certain types.
        See below.
        
        Workload, Tunnel, LoadBalancer
    """

    assignmentMode: Optional[str] = None
    """ Controls whether the pool will be used for automatic assignments or only if requested manually.
        Automatic, Manual
    """


# https://docs.tigera.io/calico/latest/reference/resources/ippool
@dataclass
class IPPool(DictMixin):
    apiVersion: Optional[str] = None
    kind: Optional[str] = None
    metadata: Optional[meta_v1.ObjectMeta] = None

    spec: Optional[IPPoolSpec] = None
