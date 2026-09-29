"""Realtime device heartbeat WebSocket support for FlowSense."""

from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class DeviceConnectionManager:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        if websocket not in self.clients:
            self.clients.append(websocket)

        print(
            f"[DeviceWS] Connected "
            f"(clients: {len(self.clients)})"
        )

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)

        print(
            f"[DeviceWS] Disconnected "
            f"(clients: {len(self.clients)})"
        )

    async def broadcast(self, data: dict[str, Any]):
        if not self.clients:
            print(
                "[DeviceWS] Broadcast skipped - "
                "no connected clients"
            )
            return

        safe_data = jsonable_encoder(data)

        print(
            "[DeviceWS] Broadcasting device heartbeat "
            f"for {safe_data.get('device_code')} "
            f"to {len(self.clients)} client(s)"
        )

        disconnected = []

        for client in list(self.clients):
            try:
                await client.send_json(safe_data)

            except Exception as exc:
                print(
                    f"[DeviceWS] Send failed: {exc}"
                )

                disconnected.append(client)

        for client in disconnected:
            await self.disconnect(client)


manager = DeviceConnectionManager()


async def broadcast_device_heartbeat(
    payload: dict[str, Any]
):
    print(
        "[DeviceWS] Heartbeat received for broadcast: "
        f"{payload.get('device_code')}"
    )

    await manager.broadcast(payload)