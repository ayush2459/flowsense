"""
FlowSense API - serves the real database (flowsense_final_database_completed.sql).

This DB is already seeded with 100 facilities and 365 days of hourly
data, so these endpoints are read-focused: list facilities, dashboard
summary (via v_facility_dashboard), anomalies (via v_recent_anomalies),
reconciliation/loss, and yearly summaries.

Run schema.sql against your Postgres instance first, then:
    uvicorn main:app --reload
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

app = FastAPI(title="FlowSense API", version="0.2.0")

# Local dev only - open CORS so the frontend on a different localhost port can call this.
# Tighten this to specific origins before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "FlowSense API"}


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
    """Live-ish dashboard summary from the pre-built view."""
    row = db.execute(text("""
        SELECT * FROM v_facility_dashboard WHERE facility_code = :code
    """), {"code": facility_code}).mappings().first()
    if not row:
        raise HTTPException(404, "Facility not found or has no recent readings")
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
    """Main-meter vs IoT-observed loss/unaccounted analysis (SRS Section 13)."""
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
        SELECT * FROM v_yearly_facility_summary WHERE facility_code = :code
    """), {"code": facility_code}).mappings().first()
    if not row:
        raise HTTPException(404, "No summary available for this facility")
    return dict(row)


@app.get("/api/facilities/{facility_code}/energy")
def facility_energy_trend(facility_code: str, hours: int = 24, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT mr.reading_time, mr.reading_value, mr.quality_status
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        JOIN facilities f ON f.facility_id = m.facility_id
        WHERE f.facility_code = :code AND m.resource_type = 'energy'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {"code": facility_code, "hours": hours}).mappings().all()
    return list(rows)


@app.get("/api/facilities/{facility_code}/water")
def facility_water_trend(facility_code: str, hours: int = 24, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT mr.reading_time, mr.reading_value, mr.quality_status
        FROM meter_readings mr
        JOIN meters m ON m.meter_id = mr.meter_id
        JOIN facilities f ON f.facility_id = m.facility_id
        WHERE f.facility_code = :code AND m.resource_type = 'water'
          AND mr.reading_time >= NOW() - (:hours || ' hours')::interval
        ORDER BY mr.reading_time
    """), {"code": facility_code, "hours": hours}).mappings().all()
    return list(rows)


@app.get("/api/devices/{device_code}/health")
def device_health(device_code: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT device_code, status, last_seen_at
        FROM iot_devices WHERE device_code = :code
    """), {"code": device_code}).mappings().first()
    if not row:
        raise HTTPException(404, "Device not found")
    return dict(row)
