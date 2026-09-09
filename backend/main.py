"""
FlowSense API - REST + realtime WebSocket backend.

Provides:
- Facility list
- Facility dashboard summary
- Energy trends
- Water trends
- Anomalies
- Reconciliation/loss analysis
- Yearly summaries
- IoT device health
- Realtime WebSocket telemetry streaming
- All-facility realtime streaming

Run:
    uvicorn main:app --reload
"""

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

import asyncio
from datetime import datetime, timezone


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="FlowSense API",
    version="0.4.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REALTIME WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    """
    Maintains active WebSocket connections.

    Special channel:
        all -> receives telemetry from every facility

    Facility channels:
        FS-FAC-001 -> only receives FS-FAC-001
        FS-FAC-002 -> only receives FS-FAC-002
        etc.
    """

    def __init__(self):
        self.connections = {}


    async def connect(
        self,
        channel: str,
        websocket: WebSocket
    ):
        await websocket.accept()

        if channel not in self.connections:
            self.connections[channel] = []

        self.connections[channel].append(websocket)

        print(
            f"[WebSocket] Connected -> {channel} "
            f"(clients: {len(self.connections[channel])})"
        )


    def disconnect(
        self,
        channel: str,
        websocket: WebSocket
    ):
        clients = self.connections.get(channel, [])

        if websocket in clients:
            clients.remove(websocket)

        if not clients and channel in self.connections:
            del self.connections[channel]

        print(
            f"[WebSocket] Disconnected -> {channel}"
        )


    async def broadcast(
        self,
        channel: str,
        data: dict
    ):
        """
        Send data to every browser connected
        to the specified channel.
        """

        clients = list(
            self.connections.get(channel, [])
        )

        if not clients:
            return

        disconnected = []

        for websocket in clients:

            try:

                await websocket.send_json(data)

            except Exception:

                disconnected.append(websocket)

        for websocket in disconnected:

            self.disconnect(
                channel,
                websocket
            )


    async def broadcast_facility(
        self,
        facility_code: str,
        data: dict
    ):
        """
        Broadcast telemetry to:

        1. Clients watching this facility
        2. Clients watching ALL facilities
        """

        await self.broadcast(
            facility_code,
            data
        )

        await self.broadcast(
            "all",
            data
        )


manager = ConnectionManager()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "FlowSense API",
        "version": "0.4.0",
        "realtime": True,
        "all_facilities_stream": True,
    }


# ============================================================
# FACILITIES
# ============================================================

@app.get("/api/facilities")
def list_facilities(
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT
            facility_id,
            facility_code,
            facility_name,
            facility_type,
            city,
            state,
            status
        FROM facilities
        ORDER BY facility_code
    """)).mappings().all()

    return list(rows)


# ============================================================
# FACILITY SUMMARY
# ============================================================

@app.get("/api/facilities/{facility_code}/summary")
def facility_summary(
    facility_code: str,
    db: Session = Depends(get_db)
):

    row = db.execute(text("""
        SELECT *
        FROM v_facility_dashboard
        WHERE facility_code = :code
    """), {
        "code": facility_code
    }).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Facility not found or has no recent readings"
        )

    return dict(row)


# ============================================================
# FACILITY ANOMALIES
# ============================================================

@app.get("/api/facilities/{facility_code}/anomalies")
def facility_anomalies(
    facility_code: str,
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT *
        FROM v_recent_anomalies
        WHERE facility_code = :code
        ORDER BY detected_at DESC
    """), {
        "code": facility_code
    }).mappings().all()

    return list(rows)


# ============================================================
# RECENT ANOMALIES
# ============================================================

@app.get("/api/anomalies/recent")
def recent_anomalies(
    limit: int = 50,
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT *
        FROM v_recent_anomalies
        ORDER BY detected_at DESC
        LIMIT :limit
    """), {
        "limit": limit
    }).mappings().all()

    return list(rows)


# ============================================================
# RESOURCE RECONCILIATION
# ============================================================

@app.get("/api/facilities/{facility_code}/reconciliation")
def facility_reconciliation(
    facility_code: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT *
        FROM v_resource_reconciliation
        WHERE facility_code = :code
        ORDER BY reconciliation_time DESC
        LIMIT :limit
    """), {
        "code": facility_code,
        "limit": limit
    }).mappings().all()

    return list(rows)


# ============================================================
# YEARLY SUMMARY
# ============================================================

@app.get("/api/facilities/{facility_code}/yearly-summary")
def facility_yearly_summary(
    facility_code: str,
    db: Session = Depends(get_db)
):

    row = db.execute(text("""
        SELECT *
        FROM v_yearly_facility_summary
        WHERE facility_code = :code
    """), {
        "code": facility_code
    }).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="No summary available for this facility"
        )

    return dict(row)


# ============================================================
# ENERGY TREND
# ============================================================

@app.get("/api/facilities/{facility_code}/energy")
def facility_energy_trend(
    facility_code: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT
            mr.reading_time,
            mr.reading_value,
            mr.quality_status
        FROM meter_readings mr
        JOIN meters m
            ON m.meter_id = mr.meter_id
        JOIN facilities f
            ON f.facility_id = m.facility_id
        WHERE
            f.facility_code = :code
            AND m.resource_type = 'energy'
            AND mr.reading_time >=
                NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {
        "code": facility_code,
        "hours": hours
    }).mappings().all()

    return list(rows)


# ============================================================
# WATER TREND
# ============================================================

@app.get("/api/facilities/{facility_code}/water")
def facility_water_trend(
    facility_code: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):

    rows = db.execute(text("""
        SELECT
            mr.reading_time,
            mr.reading_value,
            mr.quality_status
        FROM meter_readings mr
        JOIN meters m
            ON m.meter_id = mr.meter_id
        JOIN facilities f
            ON f.facility_id = m.facility_id
        WHERE
            f.facility_code = :code
            AND m.resource_type = 'water'
            AND mr.reading_time >=
                NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {
        "code": facility_code,
        "hours": hours
    }).mappings().all()

    return list(rows)


# ============================================================
# DEVICE HEALTH
# ============================================================

@app.get("/api/devices/{device_code}/health")
def device_health(
    device_code: str,
    db: Session = Depends(get_db)
):

    row = db.execute(text("""
        SELECT
            device_code,
            status,
            last_seen_at
        FROM iot_devices
        WHERE device_code = :code
    """), {
        "code": device_code
    }).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return dict(row)


# ============================================================
# REALTIME WEBSOCKET - ALL FACILITIES
# ============================================================

@app.websocket("/ws/live/all")
async def live_all_websocket(
    websocket: WebSocket
):
    """
    One realtime WebSocket connection for all facilities.

    React connects to:

        ws://127.0.0.1:8000/ws/live/all

    Every telemetry event from every facility is delivered
    through this single connection.
    """

    channel = "all"

    await manager.connect(
        channel,
        websocket
    )

    try:

        while True:

            try:

                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30
                )

                if message.lower() == "ping":

                    await websocket.send_json({
                        "type": "pong",
                        "channel": "all",
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    })

            except asyncio.TimeoutError:

                await websocket.send_json({
                    "type": "heartbeat",
                    "channel": "all",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

    except WebSocketDisconnect:

        manager.disconnect(
            channel,
            websocket
        )

    except Exception as exc:

        manager.disconnect(
            channel,
            websocket
        )

        print(
            f"[WebSocket] Error -> all: {exc}"
        )


# ============================================================
# REALTIME WEBSOCKET - INDIVIDUAL FACILITY
# ============================================================

@app.websocket("/ws/live/{facility_code}")
async def live_websocket(
    websocket: WebSocket,
    facility_code: str
):
    """
    Realtime telemetry channel for one facility.

    React can connect to:

        ws://127.0.0.1:8000/ws/live/FS-FAC-001
    """

    channel = facility_code

    await manager.connect(
        channel,
        websocket
    )

    try:

        while True:

            try:

                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30
                )

                if message.lower() == "ping":

                    await websocket.send_json({
                        "type": "pong",
                        "facility_code": facility_code,
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    })

            except asyncio.TimeoutError:

                await websocket.send_json({
                    "type": "heartbeat",
                    "facility_code": facility_code,
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

    except WebSocketDisconnect:

        manager.disconnect(
            channel,
            websocket
        )

    except Exception as exc:

        manager.disconnect(
            channel,
            websocket
        )

        print(
            f"[WebSocket] Error -> "
            f"{facility_code}: {exc}"
        )


# ============================================================
# REALTIME BROADCAST API
# ============================================================

@app.post("/api/live/broadcast/{facility_code}")
async def broadcast_live_reading(
    facility_code: str,
    payload: dict
):
    """
    Receives telemetry from the simulator.

    The event is broadcast to:

        1. The specific facility channel
        2. The ALL facilities channel
    """

    event = {
        "type": "telemetry",
        "facility_code": facility_code,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "data": payload,
    }

    await manager.broadcast_facility(
        facility_code,
        event
    )

    return {
        "status": "broadcasted",
        "facility_code": facility_code,
        "all_facilities": True,
    }