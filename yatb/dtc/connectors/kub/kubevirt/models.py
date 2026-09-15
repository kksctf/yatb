# ruff: noqa: N815, UP007
from typing import Optional

from lightkube.core.schema import DictMixin, dataclass
from lightkube.models import meta_v1

# https://lightkube.readthedocs.io/en/latest/custom-resources/

# #
# @dataclass
# class _(DictMixin):
#     pass


# https://kubevirt.io/api-reference/main/definitions.html#_v1_cpu
@dataclass
class CPU(DictMixin):
    cores: Optional[int] = None
    dedicatedCpuPlacement: Optional[bool] = None
    # features
    isolateEmulatorThread: Optional[bool] = None
    maxSockets: Optional[int] = None
    model: Optional[str] = None
    # numa
    # realtime
    sockets: Optional[int] = None
    threads: Optional[int] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_cdromtarget
@dataclass
class CDRomTarget(DictMixin):
    bus: Optional[str] = None
    """ Bus indicates the type of disk device to emulate. supported values: virtio, sata, scsi.
    """

    readonly: Optional[bool] = None
    """ ReadOnly. Defaults to false.
    """

    tray: Optional[str] | None = None
    """ Tray indicates if the tray of the device is open or closed.
        Allowed values are "open" and "closed". Defaults to closed.
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_disktarget
@dataclass
class DiskTarget(DictMixin):
    bus: Optional[str] = None
    """ Bus indicates the type of disk device to emulate. supported values: virtio, sata, scsi.
    """

    pciAddress: Optional[str] = None
    """ If specified, the virtual disk will be placed on the guests
        pci address with the specified PCI address. For example: 0000:81:01.10
    """

    readonly: Optional[bool] = None
    """ ReadOnly. Defaults to false.
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_disk
@dataclass
class Disk(DictMixin):
    name: str = ""

    # blockSize
    bootOrder: Optional[int] = None
    cache: Optional[str] = None
    cdrom: Optional[CDRomTarget] = None
    dedicatedIOThread: Optional[bool] = None
    disk: Optional[DiskTarget] = None
    errorPolicy: Optional[str] = None
    io: Optional[str] = None
    # lun
    serial: Optional[str] = None
    shareable: Optional[bool] = None
    tag: Optional[str] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_port
@dataclass
class Port(DictMixin):
    port: int
    """ Number of port to expose for the virtual machine. This must be a valid port number, 0 < x < 65536.
        Default : 0
    """

    name: Optional[str] = None
    """ If specified, this must be an IANA_SVC_NAME and unique within the pod.
        Each named port in a pod must have a unique name. Name for the port that can be referred to by services.
    """

    protocol: Optional[str] = None
    """ Protocol for port. Must be UDP or TCP. Defaults to "TCP".
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_interface
@dataclass
class Interface(DictMixin):
    name: str = ""
    """ Logical name of the interface as well as a reference to the associated networks. 
        Must match the Name of a Network.
    """

    # acpiIndex
    # binding
    # bootOrder
    # bridge
    # dhcpOptions
    # macAddress
    # macvtap

    masquerade: Optional[dict] = None
    """ ???
        https://kubevirt.io/api-reference/main/definitions.html#_v1_interfacemasquerade
    """

    model: Optional[str] = None
    """ Interface model. One of: e1000, e1000e, igb, ne2k_pci, pcnet, rtl8139, virtio. Defaults to virtio.
    """

    # passt
    # pciAddress

    ports: Optional[list[Port]] = None
    """ List of ports to be forwarded to the virtual machine.
    """

    # slirp
    # sriov
    # state
    # tag


# https://kubevirt.io/api-reference/main/definitions.html#_v1_devices
@dataclass
class Devices(DictMixin):
    # autoattachGraphicsDevice
    # autoattachInputDevice
    # autoattachMemBalloon
    # autoattachPodInterface
    # autoattachSerialConsole
    # autoattachVSOCK
    # blockMultiQueue
    # clientPassthrough
    # disableHotplug
    disks: Optional[list[Disk]] = None
    # downwardMetrics
    # filesystems
    # gpus
    # hostDevices
    # inputs

    interfaces: Optional[list[Interface]] = None

    # logSerialConsole
    # networkInterfaceMultiqueue
    # rng
    # sound
    # tpm
    # useVirtioTransitional
    # watchdog


# https://kubevirt.io/api-reference/main/definitions.html#_v1_memory
@dataclass
class Memory(DictMixin):
    guest: Optional[str] = None  # Quantity
    # hugepages
    # maxGuest


# https://kubevirt.io/api-reference/main/definitions.html#_v1_resourcerequirements
@dataclass
class ResourceRequirements(DictMixin):
    limits: Optional[dict[str, str]] = None
    """ Limits describes the maximum amount of compute resources allowed.
        Valid resource keys are "memory" and "cpu".
    """

    overcommitGuestOverhead: Optional[bool] = None
    """ Don't ask the scheduler to take the guest-management overhead into account.
        Instead put the overhead only into the container's memory limit. 
        This can lead to crashes if all memory is in use on a node. Defaults to false.
    """

    requests: Optional[dict[str, str]] = None
    """ Requests is a description of the initial vmi resources.
        Valid resource keys are "memory" and "cpu".
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_containerdisksource
@dataclass
class ContainerDiskSource(DictMixin):
    image: str

    # imagePullPolicy
    # imagePullSecret
    path: Optional[str] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_hostdisk
@dataclass
class HostDisk(DictMixin):
    path: str
    """ The path to HostDisk image located on the cluster
    """

    type: str
    """ Contains information if disk.img exists or should be created;
        allowed options are 'Disk' and 'DiskOrCreate'
    """

    capacity: Optional[str] = None
    """ Capacity of the sparse disk
    """

    shared: Optional[bool] = None
    """ Shared indicate whether the path is shared between nodes
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_cloudinitnocloudsource
@dataclass
class CloudInitNoCloudSource(DictMixin):
    networkData: Optional[str] = None
    """ NetworkData contains NoCloud inline cloud-init networkdata.
    """

    networkDataBase64: Optional[str] = None
    """ NetworkDataBase64 contains NoCloud cloud-init networkdata as a base64 encoded string.
    """

    # networkDataSecretRef
    # secretRef

    userData: Optional[str] = None
    """ UserData contains NoCloud inline cloud-init userdata.
    """

    userDataBase64: Optional[str] = None
    """ UserDataBase64 contains NoCloud cloud-init userdata as a base64 encoded string.
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_volume
@dataclass
class Volume(DictMixin):
    name: str
    """ Volume's name.
        Must be a DNS_LABEL and unique within the vmi.
        More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    """

    # cloudInitConfigDrive

    cloudInitNoCloud: Optional[CloudInitNoCloudSource] = None
    """ CloudInitNoCloud represents a cloud-init NoCloud user-data source.
        The NoCloud data will be added as a disk to the vmi.
        A proper cloud-init installation is required inside the guest.
        More info: http://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html
    """

    # configMap
    containerDisk: Optional[ContainerDiskSource] = None
    """ ContainerDisk references a docker image,
        embedding a qcow or raw disk.
        More info: https://kubevirt.gitbooks.io/user-guide/registry-disk.html
    """

    # dataVolume
    # downwardAPI
    # downwardMetrics
    # emptyDisk
    # ephemeral
    hostDisk: Optional[HostDisk] = None
    """ HostDisk represents a disk created on the cluster level
    """

    # memoryDump
    # persistentVolumeClaim
    # secret
    # serviceAccount
    # sysprep


# https://kubevirt.io/api-reference/main/definitions.html#_v1_domainspec
@dataclass
class DomainSpec(DictMixin):
    cpu: Optional[CPU] = None
    devices: Optional[Devices] = None
    # features: Optional[ Features] = None
    # firmware: Optional[ Firmware] = None
    # ioThreads: Optional[ DiskIOThreads] = None
    # ioThreadsPolicy: Optional[ str] = None
    # launchSecurity: Optional[ LaunchSecurity] = None
    # machine: Optional[ Machine] = None
    memory: Optional[Memory] = None
    resources: Optional[ResourceRequirements] = None


# # https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachinespec
# @dataclass
# class VirtualMachineSpec(DictMixin):
#     pass


# # https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachinestatus
# @dataclass
# class VirtualMachineStatus(DictMixin):
#     pass


# # https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachine
# @dataclass
# class VirtualMachine(DictMixin):
#     apiVersion: Optional[ str] = None  # noqa: N815
#     kind: Optional[ str] = None
#     metadata: Optional[ meta_v1.ObjectMeta] = None
#     spec: Optional[ VirtualMachineSpec] = None
#     status: Optional[ VirtualMachineStatus] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_podnetwork
@dataclass
class PodNetwork(DictMixin):
    vmIPv6NetworkCIDR: Optional[str] = None
    """ IPv6 CIDR for the vm network. Defaults to fd10:0:2::/120 if not specified.
    """

    vmNetworkCIDR: Optional[str] = None
    """ CIDR for vm network. Default 10.0.2.0/24 if not specified.
    """


# https://kubevirt.io/api-reference/main/definitions.html#_v1_network
@dataclass
class Network(DictMixin):
    name: str = ""

    # multus

    pod: Optional[PodNetwork] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachineinstancespec
@dataclass
class VirtualMachineInstanceSpec(DictMixin):
    domain: DomainSpec

    architecture: Optional[str] = None
    evictionStrategy: Optional[str] = None
    hostname: Optional[str] = None
    # livenessProbe

    networks: Optional[list[Network]] = None

    # nodeSelector
    priorityClassName: Optional[str] = None
    # readinessProbe
    schedulerName: Optional[str] = None
    startStrategy: Optional[str] = None
    subdomain: Optional[str] = None
    terminationGracePeriodSeconds: Optional[int] = None
    # tolerations
    # topologySpreadConstraints
    volumes: Optional[list[Volume]] = None


# https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachineinstancestatus
@dataclass
class VirtualMachineInstanceStatus(DictMixin):
    VSOCKCID: Optional[int] = None
    activePods: Optional[dict[str, str]] = None
    # conditions
    # currentCPUTopology
    evacuationNodeName: Optional[str] = None
    fsFreezeStatus: Optional[str] = None
    # guestOSInfo
    # interfaces
    # kernelBootStatus
    launcherContainerImageVersion: Optional[str] = None
    # machine
    # memory
    # migratedVolumes
    migrationMethod: Optional[str] = None
    # migrationState
    migrationTransport: Optional[str] = None
    nodeName: Optional[str] = None
    phase: Optional[str] = None
    # phaseTransitionTimestamps
    # qosClass
    reason: Optional[str] = None
    runtimeUser: Optional[int] = None
    selinuxContext: Optional[str] = None
    # topologyHints
    virtualMachineRevisionName: Optional[str] = None
    # volumeStatus


# https://kubevirt.io/api-reference/main/definitions.html#_v1_virtualmachineinstance
@dataclass
class VirtualMachineInstance(DictMixin):
    apiVersion: Optional[str] = None
    kind: Optional[str] = None
    metadata: Optional[meta_v1.ObjectMeta] = None
    spec: Optional[VirtualMachineInstanceSpec] = None
    status: Optional[VirtualMachineInstanceStatus] = None
