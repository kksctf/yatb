from enum import StrEnum, auto
from ipaddress import IPv4Address, IPv4Network
from typing import Annotated, Literal, Self, TypeGuard
from uuid import UUID

from pydantic import BaseModel, Field, RootModel

from .... import schema
from .base import BaseETCDModel


class VPNInfoState(StrEnum):
    REQUESTED = auto()
    GENERATED = auto()


class WGInfo(BaseModel):
    private_key: str
    public_key: str


class OVPNInfo(BaseModel):
    static_key: str


class VPNGlobalState(BaseETCDModel):
    server: WGInfo

    server_addr: str
    port: int = 52812
    count: int = 0

    back_vpn: OVPNInfo | None = None
    back_port: int | None = None

    @property
    def server_addr_ip(self) -> IPv4Address:
        return IPv4Address(self.server_addr)


class UserNetInfo(BaseModel):
    client: str
    task: str
    vpn: str

    vpn_internal_port: int

    def client_ip_with_net(self, *, prefix: int) -> IPv4Network:
        return IPv4Network(f"{self.client}/{prefix}", strict=False)

    @property
    def client_ip(self) -> IPv4Address:
        return IPv4Address(self.client)

    @property
    def task_net(self) -> IPv4Network:
        return IPv4Network(self.task)

    @property
    def task_net_task(self) -> IPv4Address:
        return self.task_net.network_address + 10

    @property
    def task_net_vpn(self) -> IPv4Address:
        return self.task_net.network_address + 5

    @property
    def vpn_net(self) -> IPv4Network:
        return IPv4Network(self.vpn)

    @property
    def vpn_server_ip(self) -> IPv4Address:
        return self.vpn_net.network_address + 1

    @property
    def vpn_client_ip(self) -> IPv4Address:
        return self.vpn_net.network_address + 2


class VPNUserInfoBase(BaseETCDModel):
    state: Literal[VPNInfoState.REQUESTED] = VPNInfoState.REQUESTED

    user_id: UUID
    # user_admin: bool = False # problems

    client: WGInfo | None = None
    task: OVPNInfo | None = None
    netinfo: UserNetInfo | None = None

    @classmethod
    def build(cls, user: "schema.User") -> Self:
        return cls(
            user_id=user.user_id,
        )


class VPNUserInfoGenerated(BaseETCDModel):
    state: Literal[VPNInfoState.GENERATED] = VPNInfoState.GENERATED

    user_id: UUID
    # user_admin: bool = False # problems

    client: WGInfo
    task: OVPNInfo
    netinfo: UserNetInfo


VPNUserInfo = Annotated[
    VPNUserInfoBase | VPNUserInfoGenerated,
    Field(
        ...,
        discriminator="state",
    ),
]
VPNUserInfoModel = RootModel[VPNUserInfo]


def is_vpninfo_prepared(t: VPNUserInfo) -> TypeGuard["VPNUserInfoBase"]:
    return t.state == VPNInfoState.REQUESTED


def is_vpninfo_generated(t: VPNUserInfo) -> TypeGuard["VPNUserInfoGenerated"]:
    return t.state == VPNInfoState.GENERATED
