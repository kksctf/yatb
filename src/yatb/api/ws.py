import datetime
from collections import defaultdict, deque
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel

from yatb import schema

from ..shared.dtc.models.vpn import is_vpninfo_generated
from .api_dynamic_tasks import _get_client


class AlertData(BaseModel):
    src_ip: str
    dst_ip: str
    alert: str
    ts: datetime.datetime


class FrontAlert(BaseModel):
    time: datetime.datetime
    message: str


class ConnectionManager:
    active_connections: list[WebSocket]
    user_to_ws: dict[UUID, list[WebSocket]]
    ip_to_user: dict[str, UUID]
    history: dict[UUID, deque[FrontAlert]]

    def __init__(self) -> None:
        self.active_connections = []
        self.user_to_ws = defaultdict(list)
        self.ip_to_user = {}
        self.history = defaultdict(lambda: deque(maxlen=16))

    async def connect(self, user: schema.User, websocket: WebSocket) -> None:
        await websocket.accept()

        self.active_connections.append(websocket)
        self.user_to_ws[user.user_id].append(websocket)

        client = await _get_client()
        info = await client.get_vpn_info(user.user_id)
        if not info or not is_vpninfo_generated(info):
            return

        self.ip_to_user[info.netinfo.client_ip.compressed] = user.user_id

        for entry in self.history[user.user_id]:
            await websocket.send_json(data=entry.model_dump_json())

    def disconnect(self, user: schema.User, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)
        del self.user_to_ws[user.user_id]

    async def send_alert(self, alert: AlertData) -> None:
        src_ip = IPv4Address(alert.src_ip)
        dst_ip = IPv4Address(alert.dst_ip)

        if not (uid := self.ip_to_user.get(src_ip.compressed)) and not (uid := self.ip_to_user.get(dst_ip.compressed)):
            return

        wss = self.user_to_ws[uid]

        fa = FrontAlert(time=alert.ts, message=alert.alert)

        self.history[uid].append(fa)

        for connection in wss:
            await connection.send_json(data=fa.model_dump_json())

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_json(self, data: Any, mode: str = "text") -> None:
        for connection in self.active_connections:
            await connection.send_json(data=data, mode=mode)


ws_manager = ConnectionManager()
