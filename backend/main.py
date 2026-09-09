"""
FlowSense API - REST + realtime WebSocket backend.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

app = FastAPI(title="FlowSense API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, channel, websocket):
        await websocket.accept()
        self.connections.setdefault(channel, []).append(websocket)
        print(f"[WebSocket] Connected -> {channel} (clients: {len(self.connections[channel])})")

    def disconnect(self, channel, websocket):
        clients = self.connections.get(channel, [])
        if websocket in clients:
            clients.remove(websocket)
        if not clients and channel in self.connections:
            del self.connections[channel]
        print(f"[WebSocket] Disconnected -> {channel}")

    async def broadcast(self, channel, data):
        clients = list(self.connections.get(channel, []))
        disconnected = []
        for websocket in clients:
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(channel, websocket)

    async def broadcast_facility(self, facility_code, data):
        await self.broadcast(facility_code, data)
        await self.broadcast("all", data)


manager = ConnectionManager()


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "FlowSense API",
        "version": "0.5.0",
        "realtime": True,
        "all_facilities_stream": True,
        "historical_portfolio": True,
    }


@app.get("/api/facilities")
def list_facilities(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT facility_id, facility_code, facility_name, facility_type,
               city, state, status
        FROM facilities
        ORDER BY facility_code
    """)).mappings().all()
    return list(rows)


@app.get("/api/facilities/{facility_code}/summary")
def facility_summary(facility_code: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT * FROM v_facility_dashboard
        WHERE facility_code = :code
    """), {"code": facility_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Facility not found or has no recent readings")
    return dict(row)


@app.get("/api/facilities/{facility_code}/anomalies")
def facility_anomalies(facility_code: str, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM v_recent_anomalies
        WHERE facility_code = :code
        ORDER BY detected_at DESC
    """), {"code": facility_code}).mappings().all()
    return list(rows)


@app.get("/api/anomalies/recent")
def recent_anomalies(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM v_recent_anomalies
        ORDER BY detected_at DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return list(rows)


@app.get("/api/facilities/{facility_code}/reconciliation")
def facility_reconciliation(facility_code: str, limit: int = 100, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM v_resource_reconciliation
        WHERE facility_code = :code
        ORDER BY reconciliation_time DESC
        LIMIT :limit
    """), {"code": facility_code, "limit": limit}).mappings().all()
    return list(rows)


@app.get("/api/facilities/{facility_code}/yearly-summary")
def facility_yearly_summary(facility_code: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT * FROM v_yearly_facility_summary
        WHERE facility_code = :code
    """), {"code": facility_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No summary available for this facility")
    return dict(row)


@app.get("/api/facilities/{facility_code}/energy")
def facility_energy_trend(facility_code: str, hours: int = 24, db: Session = Depends(get_db)):
    hours = max(1, min(hours, 720))
    rows = db.execute(text("""
        SELECT mr.reading_time, mr.reading_value, mr.quality_status
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        JOIN facilities f ON f.facility_id = m.facility_id
        WHERE f.facility_code = :code
          AND m.resource_type = 'energy'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {"code": facility_code, "hours": hours}).mappings().all()
    return list(rows)


@app.get("/api/facilities/{facility_code}/water")
def facility_water_trend(facility_code: str, hours: int = 24, db: Session = Depends(get_db)):
    hours = max(1, min(hours, 720))
    rows = db.execute(text("""
        SELECT mr.reading_time, mr.reading_value, mr.quality_status
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        JOIN facilities f ON f.facility_id = m.facility_id
        WHERE f.facility_code = :code
          AND m.resource_type = 'water'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {"code": facility_code, "hours": hours}).mappings().all()
    return list(rows)


# Historical portfolio endpoints. These aggregate all facility meters on the
# server so the browser does not need to make 100 separate requests.
@app.get("/api/portfolio/energy")
def portfolio_energy(hours: int = 24, db: Session = Depends(get_db)):
    hours = max(1, min(hours, 720))
    rows = db.execute(text("""
        SELECT date_trunc('minute', mr.reading_time) AS reading_time,
               SUM(mr.reading_value) AS reading_value
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        WHERE m.resource_type = 'energy'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        GROUP BY date_trunc('minute', mr.reading_time)
        ORDER BY reading_time
    """), {"hours": hours}).mappings().all()
    return list(rows)


@app.get("/api/portfolio/water")
def portfolio_water(hours: int = 24, db: Session = Depends(get_db)):
    hours = max(1, min(hours, 720))
    rows = db.execute(text("""
        SELECT date_trunc('minute', mr.reading_time) AS reading_time,
               SUM(mr.reading_value) AS reading_value
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        WHERE m.resource_type = 'water'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        GROUP BY date_trunc('minute', mr.reading_time)
        ORDER BY reading_time
    """), {"hours": hours}).mappings().all()
    return list(rows)


@app.get("/api/devices/{device_code}/health")
def device_health(device_code: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT device_code, status, last_seen_at
        FROM iot_devices
        WHERE device_code = :code
    """), {"code": device_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return dict(row)


@app.websocket("/ws/live/all")
async def live_all_websocket(websocket: WebSocket):
    channel = "all"
    await manager.connect(channel, websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if message.lower() == "ping":
                    await websocket.send_json({
                        "type": "pong", "channel": "all",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat", "channel": "all",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
    except Exception as exc:
        manager.disconnect(channel, websocket)
        print(f"[WebSocket] Error -> all: {exc}")


@app.websocket("/ws/live/{facility_code}")
async def live_websocket(websocket: WebSocket, facility_code: str):
    channel = facility_code
    await manager.connect(channel, websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if message.lower() == "ping":
                    await websocket.send_json({
                        "type": "pong", "facility_code": facility_code,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat", "facility_code": facility_code,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
    except Exception as exc:
        manager.disconnect(channel, websocket)
        print(f"[WebSocket] Error -> {facility_code}: {exc}")


@app.post("/api/live/broadcast/{facility_code}")
async def broadcast_live_reading(facility_code: str, payload: dict):
    event = {
        "type": "telemetry",
        "facility_code": facility_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    await manager.broadcast_facility(facility_code, event)
    return {"status": "broadcasted", "facility_code": facility_code, "all_facilities": True}
