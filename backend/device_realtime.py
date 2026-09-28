"""Realtime device heartbeat WebSocket support for FlowSense."""

from typing import Any

from fastapi import WebSocket


class DeviceConnectionManager:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        if websocket not in self.clients:
            self.clients.append(websocket)

        print(f"[DeviceWS] Connected (clients: {len(self.clients)})")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)

        print(f"[DeviceWS] Disconnected (clients: {len(self.clients)})")

    async def broadcast(self, data: dict[str, Any]):
        if not self.clients:
            print("[DeviceWS] Broadcast skipped - no connected clients")
            return

        disconnected: list[WebSocket] = []

        print(
            f"[DeviceWS] Broadcasting device heartbeat "
            f"for {data.get('device_code')} "
            f"to {len(self.clients)} client(s)"
        )

        for client in list(self.clients):
            try:
                await client.send_json(data)
            except Exception as exc:
                print(f"[DeviceWS] Send failed: {exc}")
                disconnected.append(client)

        for client in disconnected:
            await self.disconnect(client)


manager = DeviceConnectionManager()


async def broadcast_device_heartbeat(payload: dict[str, Any]):
    """
    Broadcast a realtime device heartbeat to all connected dashboards.

    The heartbeat payload must contain JSON-safe values.
    """
    print(
        f"[DeviceWS] Heartbeat received for broadcast: "
        f"{payload.get('device_code')}"
    )

    await manager.broadcast(payload)