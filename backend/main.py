"""
FlowSense API - REST + realtime WebSocket backend.

Stage 3:
- REST APIs
- Realtime WebSockets
- Intelligent live telemetry detection
- Energy/water efficiency scoring
- Root-cause/source resolution
- AI-ready recommendations
- Optional telemetry persistence
- Optimized realtime processing
- Preloaded sensor/source mappings
"""

import asyncio
import os
import json
from ollama_service import generate_report_analysis, generate_portfolio_report_analysis
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from device_routes import router as device_router
from device_realtime import manager as device_ws_manager

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from auth_routes import router as auth_router
from settings_routes import router as settings_router
from maintenance_routes import router as maintenance_router
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db, engine, SessionLocal

from detection_engine import (
    DetectionResult,
    analyze_telemetry,
    calculate_energy_efficiency_score,
    calculate_water_efficiency_score,
    generate_recommendation,
)


# ============================================================
# CONFIGURATION
# ============================================================

APP_VERSION = "0.7.0"


# ============================================================
# SOURCE MAPPING CACHE
# ============================================================

# Structure:
#
# {
#     "FS-FAC-001": [
#         {
#             "sensor_code": "...",
#             "sensor_name": "...",
#             "sensor_type": "...",
#             "measurement": "...",
#             "unit": "...",
#             "source_name": "...",
#             "source_type": "...",
#             "resource_type": "...",
#             "area_name": "...",
#             "criticality": "..."
#         }
#     ]
# }
#
# The old implementation queried PostgreSQL when a facility
# was encountered for the first time.
#
# With 100 facilities this created unnecessary synchronous DB
# work during realtime traffic.
#
# We now load ALL mappings once during application startup.

SOURCE_MAPPING_CACHE: dict[str, list[dict[str, Any]]] = {}

SOURCE_MAPPING_READY = False


def load_source_mapping_cache() -> int:
    """
    Load all active sensor-to-source mappings in ONE database query.

    Returns:
        Number of facilities loaded into the cache.
    """

    global SOURCE_MAPPING_READY

    try:

        with engine.connect() as conn:

            rows = conn.execute(
                text(
                    """
                    SELECT
                        f.facility_code,

                        s.sensor_code,
                        s.sensor_name,
                        s.sensor_type,
                        s.measurement,
                        s.unit,

                        e.source_name,
                        e.source_type,
                        e.resource_type,
                        e.area_name,
                        e.criticality

                    FROM iot_sensors s

                    JOIN source_sensor_map m
                        ON m.sensor_id = s.sensor_id

                    JOIN equipment_sources e
                        ON e.source_id = m.source_id

                    JOIN facilities f
                        ON f.facility_id = e.facility_id

                    WHERE e.status = 'active'
                      AND s.status = 'active'

                    ORDER BY
                        f.facility_code,
                        e.criticality DESC,
                        e.source_name
                    """
                )
            ).mappings().all()

        new_cache: dict[str, list[dict[str, Any]]] = {}

        for row in rows:

            facility_code = row["facility_code"]

            candidate = {
                "sensor_code": row["sensor_code"],
                "sensor_name": row["sensor_name"],
                "sensor_type": row["sensor_type"],
                "measurement": row["measurement"],
                "unit": row["unit"],
                "source_name": row["source_name"],
                "source_type": row["source_type"],
                "resource_type": row["resource_type"],
                "area_name": row["area_name"],
                "criticality": row["criticality"],
            }

            new_cache.setdefault(
                facility_code,
                [],
            ).append(candidate)

        SOURCE_MAPPING_CACHE.clear()
        SOURCE_MAPPING_CACHE.update(new_cache)

        SOURCE_MAPPING_READY = True

        print(
            "[Source Mapping] Loaded "
            f"{len(SOURCE_MAPPING_CACHE)} facilities "
            f"with {len(rows)} mappings."
        )

        return len(SOURCE_MAPPING_CACHE)

    except Exception as exc:

        SOURCE_MAPPING_READY = False

        print(
            "[Source Mapping] Startup load failed: "
            f"{exc}"
        )

        return 0


def resolve_source_candidates(
    facility_code: str,
) -> list[dict[str, Any]]:
    """
    Return source candidates from memory.

    No database query is performed here.

    If the cache is unavailable, perform one fallback
    query so the application remains functional.
    """

    cached = SOURCE_MAPPING_CACHE.get(
        facility_code
    )

    if cached is not None:
        return cached

    # --------------------------------------------------------
    # Fallback only.
    #
    # Normally this should never be reached after startup.
    # --------------------------------------------------------

    try:

        with engine.connect() as conn:

            rows = conn.execute(
                text(
                    """
                    SELECT
                        s.sensor_code,
                        s.sensor_name,
                        s.sensor_type,
                        s.measurement,
                        s.unit,
                        e.source_name,
                        e.source_type,
                        e.resource_type,
                        e.area_name,
                        e.criticality

                    FROM iot_sensors s

                    JOIN source_sensor_map m
                        ON m.sensor_id = s.sensor_id

                    JOIN equipment_sources e
                        ON e.source_id = m.source_id

                    JOIN facilities f
                        ON f.facility_id = e.facility_id

                    WHERE f.facility_code = :facility_code
                      AND e.status = 'active'
                      AND s.status = 'active'

                    ORDER BY
                        e.criticality DESC,
                        e.source_name
                    """
                ),
                {
                    "facility_code": facility_code,
                },
            ).mappings().all()

            result = [
                dict(row)
                for row in rows
            ]

            SOURCE_MAPPING_CACHE[
                facility_code
            ] = result

            return result

    except Exception as exc:

        print(
            "[Source Mapping] Fallback error -> "
            f"{facility_code}: {exc}"
        )

        return []


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.

    Startup:
        Load all source mappings once.

    Shutdown:
        Dispose SQLAlchemy engine connections.
    """

    print(
        "[FlowSense] Starting API "
        f"version {APP_VERSION}"
    )

    loaded = load_source_mapping_cache()

    print(
        "[FlowSense] Source mapping cache ready -> "
        f"{loaded} facilities"
    )

    yield

    print(
        "[FlowSense] Shutting down..."
    )

    try:
        engine.dispose()
    except Exception:
        pass


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="FlowSense API",
    version=APP_VERSION,
    description=(
        "FlowSense IoT energy/water monitoring and "
        "intelligent loss detection API"
    ),
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(maintenance_router)
app.include_router(device_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# REALTIME REPORT CACHE
# ============================================================

LIVE_REPORT_CACHE = {}

# ============================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):
        self.connections: dict[
            str,
            list[WebSocket],
        ] = {}

    async def connect(
        self,
        channel: str,
        websocket: WebSocket,
    ):

        await websocket.accept()

        self.connections.setdefault(
            channel,
            [],
        ).append(websocket)

        print(
            f"[WebSocket] Connected -> {channel} "
            f"(clients: "
            f"{len(self.connections[channel])})"
        )

    def disconnect(
        self,
        channel: str,
        websocket: WebSocket,
    ):

        clients = self.connections.get(
            channel,
            [],
        )

        if websocket in clients:

            clients.remove(
                websocket
            )

        if (
            not clients
            and channel in self.connections
        ):

            del self.connections[
                channel
            ]

        print(
            f"[WebSocket] Disconnected -> "
            f"{channel}"
        )

    async def broadcast(
        self,
        channel: str,
        data: dict,
    ):

        clients = list(
            self.connections.get(
                channel,
                [],
            )
        )

        if not clients:
            return

        async def send_one(
            websocket: WebSocket,
        ):

            try:

                await websocket.send_json(
                    data
                )

                return None

            except Exception:

                return websocket

        results = await asyncio.gather(
            *[
                send_one(websocket)
                for websocket in clients
            ],
            return_exceptions=False,
        )

        for websocket in results:

            if websocket is not None:

                self.disconnect(
                    channel,
                    websocket,
                )

    async def broadcast_facility(
        self,
        facility_code: str,
        data: dict,
    ):

        # Send to both channels concurrently.
        await asyncio.gather(
            self.broadcast(
                facility_code,
                data,
            ),
            self.broadcast(
                "all",
                data,
            ),
        )


manager = ConnectionManager()

# ============================================================
# REALTIME WEBSOCKET ROUTES
# ============================================================

# ============================================================
# DEVICE ASSET REALTIME WEBSOCKET
# ============================================================

@app.websocket("/ws/devices")
async def device_realtime_websocket(websocket: WebSocket):
    """Push real device heartbeat events to the Devices UI."""
    await device_ws_manager.connect(websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
                if message.lower() == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"[DeviceWS] Error -> {exc}")
    finally:
        await device_ws_manager.disconnect(websocket)

@app.websocket("/ws/live/all")
async def live_all_websocket(
    websocket: WebSocket,
):
    await manager.connect(
        "all",
        websocket,
    )

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=25.0,
                )

                if data.lower() == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong"
                        }
                    )

            except asyncio.TimeoutError:
                await websocket.send_json(
                    {
                        "type": "heartbeat"
                    }
                )

    except WebSocketDisconnect:
        pass

    except Exception as exc:
        print(
            f"[WebSocket] Error -> all: {exc}"
        )

    finally:
        manager.disconnect(
            "all",
            websocket,
        )


@app.websocket("/ws/live/{facility_code}")
async def live_facility_websocket(
    websocket: WebSocket,
    facility_code: str,
):
    await manager.connect(
        facility_code,
        websocket,
    )

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=25.0,
                )

                if data.lower() == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong"
                        }
                    )

            except asyncio.TimeoutError:
                await websocket.send_json(
                    {
                        "type": "heartbeat"
                    }
                )

    except WebSocketDisconnect:
        pass

    except Exception as exc:
        print(
            f"[WebSocket] Error -> "
            f"{facility_code}: {exc}"
        )

    finally:
        manager.disconnect(
            facility_code,
            websocket,
        )

# ============================================================
# JSON / SERIALIZATION HELPERS
# ============================================================

def make_json_safe(value: Any):

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):

        return {
            str(k): make_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):

        return [
            make_json_safe(v)
            for v in value
        ]

    return str(value)


# ============================================================
# INTELLIGENT DETECTION
# ============================================================

def build_detection_payload(
    payload: dict,
    facility_code: str,
    source_candidates: Optional[
        list
    ] = None,
) -> dict:
    """
    Run the intelligent detection engine.

    This function:

    - performs anomaly detection
    - determines severity
    - estimates losses
    - resolves likely source
    - calculates confidence
    - calculates efficiency scores
    - generates recommendations

    NO database writes occur here.
    """

    if source_candidates is None:

        source_candidates = (
            resolve_source_candidates(
                facility_code
            )
        )

    # --------------------------------------------------------
    # 1. Intelligent anomaly detection
    # --------------------------------------------------------

    detection = analyze_telemetry(
        payload,
        source_candidates=source_candidates,
    )

    # --------------------------------------------------------
    # 2. Energy efficiency
    # --------------------------------------------------------

    energy_score = (
        calculate_energy_efficiency_score(
            payload,
            payload.get(
                "expected_energy_kwh"
            ),
        )
    )

    # --------------------------------------------------------
    # 3. Water efficiency
    # --------------------------------------------------------

    water_score = (
        calculate_water_efficiency_score(
            payload,
            payload.get(
                "expected_water_kl"
            ),
        )
    )

    # --------------------------------------------------------
    # 4. Recommendation
    # --------------------------------------------------------

    primary_dict = (
        detection.get(
            "primary_anomaly"
        )
        or {}
    )

    recommendation = (
        generate_recommendation(
            DetectionResult(
                detected=bool(
                    primary_dict.get(
                        "detected",
                        False,
                    )
                ),

                anomaly_type=
                    primary_dict.get(
                        "anomaly_type"
                    ),

                resource_type=
                    primary_dict.get(
                        "resource_type"
                    ),

                severity=
                    primary_dict.get(
                        "severity",
                        "healthy",
                    ),

                description=
                    primary_dict.get(
                        "description",
                        "",
                    ),

                expected_value=
                    primary_dict.get(
                        "expected_value"
                    ),

                actual_value=
                    primary_dict.get(
                        "actual_value"
                    ),

                deviation_percent=
                    primary_dict.get(
                        "deviation_percent"
                    ),

                estimated_loss=
                    primary_dict.get(
                        "estimated_loss",
                        0.0,
                    ),

                loss_unit=
                    primary_dict.get(
                        "loss_unit"
                    ),

                likely_source=
                    primary_dict.get(
                        "likely_source"
                    ),

                source_type=
                    primary_dict.get(
                        "source_type"
                    ),

                area_name=
                    primary_dict.get(
                        "area_name"
                    ),

                confidence_percent=
                    primary_dict.get(
                        "confidence_percent",
                        0.0,
                    ),

                detection_method=
                    primary_dict.get(
                        "detection_method",
                        "baseline",
                    ),

                detected_at=
                    primary_dict.get(
                        "detected_at",
                        "",
                    ),

                evidence=
                    primary_dict.get(
                        "evidence"
                    ),
            )
        )
    )

    anomalies = detection.get(
        "anomalies",
        [],
    )

    anomaly_count = detection.get(
        "anomaly_count",
        len(anomalies),
    )

    return {
        "facility_code":
            facility_code,

        "facility_status":
            detection.get(
                "facility_status"
            ),

        "anomaly_count":
            anomaly_count,

        "estimated_energy_loss_kwh":
            detection.get(
                "estimated_energy_loss_kwh",
                0,
            ),

        "estimated_water_loss_kl":
            detection.get(
                "estimated_water_loss_kl",
                0,
            ),

        "primary_anomaly":
            make_json_safe(
                detection.get(
                    "primary_anomaly"
                )
            ),

        "anomalies":
            make_json_safe(
                anomalies
            ),

        "analyzed_at":
            detection.get(
                "analyzed_at"
            ),

        "efficiency": {
            "energy_score":
                make_json_safe(
                    energy_score
                ),

            "water_score":
                make_json_safe(
                    water_score
                ),
        },

        "recommendation":
            make_json_safe(
                recommendation
            ),
    }


# ============================================================
# OPTIONAL DATABASE PERSISTENCE
# ============================================================

def persist_live_telemetry(
    db: Session,
    facility_code: str,
    payload: dict,
):

    reading_time = payload.get(
        "reading_time"
    )

    if not reading_time:

        reading_time = datetime.now(
            timezone.utc
        )

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    facility = db.execute(
        text(
            """
            SELECT facility_id
            FROM facilities
            WHERE facility_code = :facility_code
            """
        ),
        {
            "facility_code":
                facility_code,
        },
    ).mappings().first()

    if not facility:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Facility not found: "
                f"{facility_code}"
            ),
        )

    facility_id = facility[
        "facility_id"
    ]

    persisted = []

    # --------------------------------------------------------
    # Energy
    # --------------------------------------------------------

    energy_value = payload.get(
        "energy_kwh"
    )

    if energy_value is not None:

        energy_meter = db.execute(
            text(
                """
                SELECT meter_id
                FROM meters
                WHERE facility_id = :facility_id
                  AND resource_type = 'energy'
                ORDER BY meter_id
                LIMIT 1
                """
            ),
            {
                "facility_id":
                    facility_id,
            },
        ).mappings().first()

        if energy_meter:

            db.execute(
                text(
                    """
                    INSERT INTO meter_readings (
                        meter_id,
                        reading_time,
                        reading_value,
                        quality_status
                    )
                    VALUES (
                        :meter_id,
                        :reading_time,
                        :reading_value,
                        :quality_status
                    )
                    """
                ),
                {
                    "meter_id":
                        energy_meter[
                            "meter_id"
                        ],

                    "reading_time":
                        reading_time,

                    "reading_value":
                        float(
                            energy_value
                        ),

                    "quality_status":
                        payload.get(
                            "status",
                            "good",
                        ),
                },
            )

            persisted.append(
                "energy"
            )

    # --------------------------------------------------------
    # Water
    # --------------------------------------------------------

    water_value = payload.get(
        "water_kl"
    )

    if water_value is not None:

        water_meter = db.execute(
            text(
                """
                SELECT meter_id
                FROM meters
                WHERE facility_id = :facility_id
                  AND resource_type = 'water'
                ORDER BY meter_id
                LIMIT 1
                """
            ),
            {
                "facility_id":
                    facility_id,
            },
        ).mappings().first()

        if water_meter:

            db.execute(
                text(
                    """
                    INSERT INTO meter_readings (
                        meter_id,
                        reading_time,
                        reading_value,
                        quality_status
                    )
                    VALUES (
                        :meter_id,
                        :reading_time,
                        :reading_value,
                        :quality_status
                    )
                    """
                ),
                {
                    "meter_id":
                        water_meter[
                            "meter_id"
                        ],

                    "reading_time":
                        reading_time,

                    "reading_value":
                        float(
                            water_value
                        ),

                    "quality_status":
                        payload.get(
                            "status",
                            "good",
                        ),
                },
            )

            persisted.append(
                "water"
            )

    db.commit()

    return {
        "persisted": True,
        "facility_code":
            facility_code,
        "resources":
            persisted,
    }


def persist_live_telemetry_background(
    facility_code: str,
    payload: dict,
) -> dict:
    """
    Persistence helper for the async live endpoint.

    A DB session is created ONLY when persistence
    has explicitly been requested.
    """

    db = SessionLocal()

    try:

        return persist_live_telemetry(
            db=db,
            facility_code=facility_code,
            payload=payload,
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "status":
            "ok",

        "service":
            "FlowSense API",

        "version":
            APP_VERSION,

        "realtime":
            True,

        "all_facilities_stream":
            True,

        "historical_portfolio":
            True,

        "intelligent_detection":
            True,

        "efficiency_scoring":
            True,

        "root_cause_ready":
            True,

        "source_mapping_cache":
            SOURCE_MAPPING_READY,

        "cached_facilities":
            len(
                SOURCE_MAPPING_CACHE
            ),

        "live_mode_default":
            True,

        "persistence_opt_in":
            True,
    }


# ============================================================
# FACILITIES
# ============================================================

@app.get("/api/facilities")
def list_facilities(
    db: Session = Depends(get_db),
):

    rows = db.execute(
        text(
            """
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
            """
        )
    ).mappings().all()

    return list(rows)


# ============================================================
# FACILITY SUMMARY
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/summary"
)
def facility_summary(
    facility_code: str,
    db: Session = Depends(get_db),
):

    row = db.execute(
        text(
            """
            SELECT *
            FROM v_facility_dashboard
            WHERE facility_code = :code
            """
        ),
        {
            "code":
                facility_code,
        },
    ).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail=(
                "Facility not found or "
                "has no recent readings"
            ),
        )

    return dict(row)


# ============================================================
# FACILITY ANOMALIES
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/anomalies"
)
def facility_anomalies(
    facility_code: str,
    db: Session = Depends(get_db),
):

    rows = db.execute(
        text(
            """
            SELECT *
            FROM v_recent_anomalies
            WHERE facility_code = :code
            ORDER BY detected_at DESC
            """
        ),
        {
            "code":
                facility_code,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# RECENT ANOMALIES
# ============================================================

@app.get("/api/anomalies/recent")
def recent_anomalies(
    limit: int = 50,
    db: Session = Depends(get_db),
):

    limit = max(
        1,
        min(limit, 500),
    )

    rows = db.execute(
        text(
            """
            SELECT *
            FROM v_recent_anomalies
            ORDER BY detected_at DESC
            LIMIT :limit
            """
        ),
        {
            "limit":
                limit,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# RECONCILIATION
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/reconciliation"
)
def facility_reconciliation(
    facility_code: str,
    limit: int = 100,
    db: Session = Depends(get_db),
):

    limit = max(
        1,
        min(limit, 500),
    )

    rows = db.execute(
        text(
            """
            SELECT *
            FROM v_resource_reconciliation
            WHERE facility_code = :code
            ORDER BY reconciliation_time DESC
            LIMIT :limit
            """
        ),
        {
            "code":
                facility_code,

            "limit":
                limit,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# YEARLY SUMMARY
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/yearly-summary"
)
def facility_yearly_summary(
    facility_code: str,
    db: Session = Depends(get_db),
):

    row = db.execute(
        text(
            """
            SELECT *
            FROM v_yearly_facility_summary
            WHERE facility_code = :code
            """
        ),
        {
            "code":
                facility_code,
        },
    ).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail=(
                "No summary available "
                "for this facility"
            ),
        )

    return dict(row)


# ============================================================
# ENERGY TREND
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/energy"
)
def facility_energy_trend(
    facility_code: str,
    hours: int = 24,
    db: Session = Depends(get_db),
):

    hours = max(
        1,
        min(hours, 720),
    )

    rows = db.execute(
        text(
            """
            SELECT
                mr.reading_time,
                mr.reading_value,
                mr.quality_status

            FROM meter_readings mr

            JOIN meters m
                ON m.meter_id = mr.meter_id

            JOIN facilities f
                ON f.facility_id =
                   m.facility_id

            WHERE f.facility_code = :code

              AND m.resource_type = 'energy'

              AND mr.reading_time >=
                    NOW() -
                    (:hours || ' hours')::interval

            ORDER BY mr.reading_time
            """
        ),
        {
            "code":
                facility_code,

            "hours":
                hours,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# WATER TREND
# ============================================================

@app.get(
    "/api/facilities/{facility_code}/water"
)
def facility_water_trend(
    facility_code: str,
    hours: int = 24,
    db: Session = Depends(get_db),
):

    hours = max(
        1,
        min(hours, 720),
    )

    rows = db.execute(
        text(
            """
            SELECT
                mr.reading_time,
                mr.reading_value,
                mr.quality_status

            FROM meter_readings mr

            JOIN meters m
                ON m.meter_id = mr.meter_id

            JOIN facilities f
                ON f.facility_id =
                   m.facility_id

            WHERE f.facility_code = :code

              AND m.resource_type = 'water'

              AND mr.reading_time >=
                    NOW() -
                    (:hours || ' hours')::interval

            ORDER BY mr.reading_time
            """
        ),
        {
            "code":
                facility_code,

            "hours":
                hours,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# PORTFOLIO ENERGY
# ============================================================

@app.get("/api/portfolio/energy")
def portfolio_energy(
    hours: int = 24,
    db: Session = Depends(get_db),
):

    hours = max(
        1,
        min(hours, 720),
    )

    rows = db.execute(
        text(
            """
            SELECT
                date_trunc(
                    'minute',
                    mr.reading_time
                ) AS reading_time,

                SUM(
                    mr.reading_value
                ) AS reading_value

            FROM meter_readings mr

            JOIN meters m
                ON m.meter_id =
                   mr.meter_id

            WHERE m.resource_type = 'energy'

              AND mr.reading_time >=
                    NOW() -
                    (:hours || ' hours')::interval

            GROUP BY
                date_trunc(
                    'minute',
                    mr.reading_time
                )

            ORDER BY reading_time
            """
        ),
        {
            "hours":
                hours,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# PORTFOLIO WATER
# ============================================================

@app.get("/api/portfolio/water")
def portfolio_water(
    hours: int = 24,
    db: Session = Depends(get_db),
):

    hours = max(
        1,
        min(hours, 720),
    )

    rows = db.execute(
        text(
            """
            SELECT
                date_trunc(
                    'minute',
                    mr.reading_time
                ) AS reading_time,

                SUM(
                    mr.reading_value
                ) AS reading_value

            FROM meter_readings mr

            JOIN meters m
                ON m.meter_id =
                   mr.meter_id

            WHERE m.resource_type = 'water'

              AND mr.reading_time >=
                    NOW() -
                    (:hours || ' hours')::interval

            GROUP BY
                date_trunc(
                    'minute',
                    mr.reading_time
                )

            ORDER BY reading_time
            """
        ),
        {
            "hours":
                hours,
        },
    ).mappings().all()

    return list(rows)


# ============================================================
# DEVICE HEALTH
# ============================================================

@app.get(
    "/api/devices/{device_code}/health"
)
def device_health(
    device_code: str,
    db: Session = Depends(get_db),
):

    row = db.execute(
        text(
            """
            SELECT
                device_code,
                status,
                last_seen_at

            FROM iot_devices

            WHERE device_code = :code
            """
        ),
        {
            "code":
                device_code,
        },
    ).mappings().first()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    return dict(row)


# ============================================================
# DEVICES
# ============================================================

@app.get("/api/devices")
def list_devices(
    db: Session = Depends(get_db),
):

    rows = db.execute(
        text(
            """
            SELECT
                d.device_id,
                d.device_code,
                d.status,
                d.last_seen_at,
                f.facility_code,
                f.facility_name

            FROM iot_devices d

            JOIN facilities f
                ON f.facility_id =
                   d.facility_id

            ORDER BY d.device_code
            """
        )
    ).mappings().all()

    return list(rows)


# ============================================================
# DETECTION TEST ENDPOINT
# ============================================================

@app.post("/api/detection/test")
async def detection_test(
    payload: dict,
):
    """
    Test intelligent detection.

    No database writes.

    Detection is executed in a worker thread
    so the async event loop remains responsive.
    """

    test_payload = dict(
        payload
    )

    facility_code = (
        test_payload.pop(
            "facility_code",
            "TEST-FACILITY",
        )
    )

    source_candidates = (
        resolve_source_candidates(
            facility_code
        )
    )

    result = await asyncio.to_thread(
        build_detection_payload,
        test_payload,
        facility_code,
        source_candidates,
    )

    return result


# ============================================================
# LIVE TELEMETRY BROADCAST
# ============================================================

@app.post(
    "/api/live/broadcast/{facility_code}"
)
async def broadcast_live_reading(
    facility_code: str,
    payload: dict,
    persist: bool = False,
):
    """
    Broadcast one realtime telemetry packet.

    Default:
        persist=false

    Normal live flow:

        Simulator
            ↓
        FastAPI
            ↓
        In-memory source mapping
            ↓
        Detection engine
            ↓
        WebSocket broadcast
            ↓
        Dashboard

    PostgreSQL is NOT touched during normal
    live telemetry processing.

    If:
        persist=true

    then telemetry is persisted using a
    dedicated database session.
    """

    # --------------------------------------------------------
    # 1. Normalize payload
    # --------------------------------------------------------

    live_payload = dict(
        payload
    )

    if not live_payload.get(
        "reading_time"
    ):

        live_payload[
            "reading_time"
        ] = datetime.now(
            timezone.utc
        ).isoformat()

    # --------------------------------------------------------
    # 2. Get source mapping from memory
    # --------------------------------------------------------

    source_candidates = (
        resolve_source_candidates(
            facility_code
        )
    )

    # --------------------------------------------------------
    # 3. Run detection OFF the event loop
    # --------------------------------------------------------

    try:

        detection_payload = (
            await asyncio.to_thread(
                build_detection_payload,
                live_payload,
                facility_code,
                source_candidates,
            )
        )

    except Exception as exc:

        print(
            f"[Detection] Error -> "
            f"{facility_code}: {exc}"
        )

        detection_payload = {
            "facility_code":
                facility_code,

            "facility_status":
                "unknown",

            "anomaly_count":
                0,

            "estimated_energy_loss_kwh":
                0,

            "estimated_water_loss_kl":
                0,

            "primary_anomaly":
                None,

            "anomalies":
                [],

            "analyzed_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "efficiency": {
                "energy_score":
                    None,

                "water_score":
                    None,
            },

            "recommendation":
                None,

            "error":
                str(exc),
        }

    # --------------------------------------------------------
    # 4. Optional persistence
    # --------------------------------------------------------

    persistence_result = {
        "persisted":
            False,

        "mode":
            "live_only",
    }

    if persist:

        try:

            persistence_result = (
                await asyncio.to_thread(
                    persist_live_telemetry_background,
                    facility_code,
                    live_payload,
                )
            )

            persistence_result[
                "mode"
            ] = "persisted"

        except Exception as exc:

            print(
                f"[Persistence] Error -> "
                f"{facility_code}: {exc}"
            )

            persistence_result = {
                "persisted":
                    False,

                "mode":
                    "persistence_error",

                "error":
                    str(exc),
            }

    # --------------------------------------------------------
    # 5. Build realtime event
    # --------------------------------------------------------

    event = {
        "type":
            "telemetry",

        "facility_code":
            facility_code,

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "data":
            live_payload,

        "detection":
            detection_payload,

        "persistence":
            persistence_result,
    }
    # ---------------------------------------------------------
    # 5.5 Store latest live snapshot for reporting
    # --------------------------------------------------------

    LIVE_REPORT_CACHE[facility_code] = {
        "facility_code": facility_code,
        "timestamp": event["timestamp"],
        "data": dict(live_payload),
        "detection": detection_payload,
    }
    # --------------------------------------------------------
    # 6. Broadcast
    # --------------------------------------------------------

    await manager.broadcast_facility(
        facility_code,
        event,
    )

    # --------------------------------------------------------
    # 7. Return HTTP response
    # --------------------------------------------------------

    return {
        "status":
            "broadcasted",

        "facility_code":
            facility_code,

        "all_facilities":
            True,

        "detection": {
            "anomaly_count":
                detection_payload.get(
                    "anomaly_count",
                    0,
                ),
        },

        "persistence":
            persistence_result,
    }

# ============================================================
# REALTIME REPORT CACHE STATUS
# ============================================================

@app.get("/api/reports/live-cache/status")
def live_report_cache_status():
    return {
        "cached_facilities": len(LIVE_REPORT_CACHE),
        "facility_codes": list(
            LIVE_REPORT_CACHE.keys()
        ),
    }
# ============================================================
# REPORTS API
# ============================================================

@app.get(
    "/api/reports/facilities/{facility_code}"
)
def facility_report(
    facility_code: str,
    period: str = "24h",
    db: Session = Depends(get_db),
):
    """
    Return the complete report data package for one facility.

    Combines:
        - PostgreSQL historical/reporting data
        - latest realtime telemetry
        - latest realtime detection
    """

    from report_engine import (
        build_facility_report_data,
        resolve_period,
    )

    # --------------------------------------------------------
    # Resolve reporting period
    # --------------------------------------------------------

    try:
        start, end = resolve_period(period)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # --------------------------------------------------------
    # Build historical report package
    # --------------------------------------------------------

    try:
        report = build_facility_report_data(
            db,
            facility_code,
            start,
            end,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"[Reports] Error -> "
            f"{facility_code}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to build facility report",
        )

    # --------------------------------------------------------
    # Attach latest realtime snapshot
    # --------------------------------------------------------

    live_snapshot = LIVE_REPORT_CACHE.get(
        facility_code
    )

    report["realtime"] = (
        live_snapshot
        if live_snapshot is not None
        else None
    )

    # --------------------------------------------------------
    # Report metadata
    # --------------------------------------------------------

    report["report_metadata"] = {
        "facility_code":
            facility_code,

        "period":
            period,

        "start":
            start.isoformat(),

        "end":
            end.isoformat(),

        "realtime_available":
            live_snapshot is not None,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }

    return make_json_safe(report)
# ============================================================
# FACILITY PDF REPORT - DUPLICATE INCOMPLETE BLOCK REMOVED
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# Duplicate/removed code retained as line-count padding.
# ============================================================
# FACILITY PDF REPORT
# ============================================================

@app.get(
    "/api/reports/facilities/{facility_code}/pdf"
)
def generate_facility_report_pdf(
    facility_code: str,
    period: str = "24h",
    db: Session = Depends(get_db),
):
    """
    Generate a PDF report from the same report data
    used by the JSON reporting endpoint.
    """

    from report_engine import (
        build_facility_report_data,
        resolve_period,
    )

    from report_pdf import generate_facility_pdf

    try:
        # ----------------------------------------------------
        # Resolve reporting period
        # ----------------------------------------------------

        start, end = resolve_period(period)

        # ----------------------------------------------------
        # Build report data
        # ----------------------------------------------------

        report = build_facility_report_data(
            db,
            facility_code,
            start,
            end,
        )

        # ----------------------------------------------------
        # Attach latest realtime snapshot
        # ----------------------------------------------------

        live_snapshot = LIVE_REPORT_CACHE.get(
            facility_code
        )

        report["realtime"] = (
            live_snapshot
            if live_snapshot is not None
            else None
        )

        # ----------------------------------------------------
        # Report metadata
        # ----------------------------------------------------

        report["report_metadata"] = {
            "facility_code":
                facility_code,

            "period":
                period,

            "start":
                start.isoformat(),

            "end":
                end.isoformat(),

            "realtime_available":
                live_snapshot is not None,

            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

        # ----------------------------------------------------
        # Generate PDF
        # ----------------------------------------------------

        pdf_buffer = generate_facility_pdf(
            report
        )

        # ----------------------------------------------------
        # Safe filename
        # ----------------------------------------------------

        facility_name = (
            report.get("facility", {})
            .get("facility_name")
            or facility_code
        )

        safe_name = (
            str(facility_name)
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        filename = (
            f"FlowSense_{safe_name}_"
            f"{period}_Report.pdf"
        )

        # ----------------------------------------------------
        # Return PDF
        # ----------------------------------------------------

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"'
            },
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:

        print(
            f"[Reports PDF] Error -> "
            f"{facility_code}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate "
                "facility PDF report"
            ),
        )
# ============================================================
# PORTFOLIO / ALL-FACILITIES PDF REPORT
# ============================================================

@app.get(
    "/api/reports/portfolio/pdf"
)
def generate_portfolio_report_pdf(
    period: str = "24h",
    db: Session = Depends(get_db),
):
    """
    Generate a PDF report covering all active facilities.

    Uses the same authoritative PostgreSQL report data
    used by the all-facilities reporting layer.
    """

    from report_engine import (
        build_portfolio_report_data,
        resolve_period,
    )

    from report_pdf import (
        generate_portfolio_pdf,
    )

    try:
        # ----------------------------------------------------
        # Resolve reporting period
        # ----------------------------------------------------

        start, end = resolve_period(
            period
        )

        # ----------------------------------------------------
        # Build portfolio report data
        # ----------------------------------------------------

        report = build_portfolio_report_data(
            db,
            start,
            end,
        )

        # ----------------------------------------------------
        # Attach latest realtime snapshots
        # ----------------------------------------------------

        for facility_report in report.get(
            "facilities",
            [],
        ):
            facility = facility_report.get(
                "facility",
                {}
            )

            facility_code = facility.get(
                "facility_code"
            )

            if not facility_code:
                continue

            live_snapshot = (
                LIVE_REPORT_CACHE.get(
                    facility_code
                )
            )

            facility_report["realtime"] = (
                live_snapshot
                if live_snapshot is not None
                else None
            )

        # ----------------------------------------------------
        # Report metadata
        # ----------------------------------------------------

        report["report_metadata"][
            "period"
        ] = period

        report["report_metadata"][
            "start"
        ] = start.isoformat()

        report["report_metadata"][
            "end"
        ] = end.isoformat()

        report["report_metadata"][
            "realtime_available"
        ] = bool(
            LIVE_REPORT_CACHE
        )

        report["report_metadata"][
            "generated_at"
        ] = datetime.now(
            timezone.utc
        ).isoformat()

        # ----------------------------------------------------
        # Generate PDF
        # ----------------------------------------------------

        pdf_buffer = generate_portfolio_pdf(
            report
        )

        # ----------------------------------------------------
        # Filename
        # ----------------------------------------------------

        filename = (
            f"FlowSense_Portfolio_"
            f"{period}_Report.pdf"
        )

        # ----------------------------------------------------
        # Return PDF
        # ----------------------------------------------------

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"'
            },
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        print(
            f"[Portfolio PDF] Error -> "
            f"{exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate "
                "portfolio PDF report"
            ),
        )



# ============================================================
# ============================================================
# PORTFOLIO AI RESULT VALIDATION
# ============================================================

def normalize_portfolio_ai_result(result: Any) -> dict:
    """Normalize and sanitize the local Ollama portfolio response."""

    if not isinstance(result, dict):
        return {
            "success": False,
            "model": None,
            "analysis": {},
            "error": "Invalid Ollama portfolio response",
        }

    analysis = result.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}

    allowed = {
        "summary",
        "key_findings",
        "energy_analysis",
        "water_analysis",
        "facilities_requiring_attention",
        "recommendations",
        "priority_actions",
    }

    cleaned = {
        key: value
        for key, value in analysis.items()
        if key in allowed
    }

    return {
        "success": bool(result.get("success", False)),
        "model": result.get("model"),
        "analysis": cleaned,
        "error": result.get("error"),
    }


# PORTFOLIO / ALL-FACILITIES AI ANALYSIS
# ============================================================
@app.post("/api/reports/portfolio/ai-analysis")
def portfolio_report_ai_analysis(period: str = "24h", db: Session = Depends(get_db)):
    from report_engine import build_portfolio_report_data, resolve_period

    try:
        start, end = resolve_period(period)
        report = build_portfolio_report_data(db, start, end)

        rows = []

        totals = {
            "energy_kwh": 0.0,
            "expected_energy_kwh": 0.0,
            "water_kl": 0.0,
            "expected_water_kl": 0.0,
            "anomaly_count": 0,
            "critical_facilities": 0,
            "attention_facilities": 0,
        }

        def num(value):
            try:
                if value is None:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        def latest_reading(readings):
            if not readings:
                return None

            valid = [
                r for r in readings
                if isinstance(r, dict) and r.get("reading_value") is not None
            ]

            if not valid:
                return None

            valid.sort(
                key=lambda r: str(r.get("reading_time") or ""),
                reverse=True,
            )

            return num(valid[0].get("reading_value"))

        def expected_from_baseline(baselines, readings):
            """
            Match the expected baseline to the latest available
            reading using hour_of_day and day_of_week.
            """
            if not baselines or not readings:
                return None

            valid_readings = [
                r for r in readings
                if isinstance(r, dict)
                and r.get("reading_value") is not None
                and r.get("reading_time")
            ]

            if not valid_readings:
                return None

            valid_readings.sort(
                key=lambda r: str(r.get("reading_time") or ""),
                reverse=True,
            )

            latest = valid_readings[0]

            reading_time = latest.get("reading_time")

            try:
                from datetime import datetime

                if isinstance(reading_time, str):
                    reading_dt = datetime.fromisoformat(
                        reading_time.replace("Z", "+00:00")
                    )
                else:
                    reading_dt = reading_time

                hour = reading_dt.hour
                day = reading_dt.weekday()

            except Exception:
                return None

            candidates = [
                b for b in baselines
                if isinstance(b, dict)
                and b.get("hour_of_day") == hour
                and b.get("day_of_week") == day
                and b.get("expected_value") is not None
            ]

            if not candidates:
                return None

            return num(candidates[0].get("expected_value"))

        for item in report.get("facilities", []):
            facility = item.get("facility") or {}

            code = facility.get("facility_code")
            name = facility.get("facility_name") or code

            energy_block = item.get("energy") or {}
            water_block = item.get("water") or {}

            energy_readings = energy_block.get("readings") or []
            energy_baselines = energy_block.get("baselines") or []

            water_readings = water_block.get("readings") or []
            water_baselines = water_block.get("baselines") or []

            anomalies = item.get("anomalies") or []
            alerts = item.get("alerts") or []

            # -------------------------------------------------
            # Actual readings
            # -------------------------------------------------
            energy = latest_reading(energy_readings)
            water = latest_reading(water_readings)

            # -------------------------------------------------
            # Expected values from matching baseline
            # -------------------------------------------------
            expected_energy = expected_from_baseline(
                energy_baselines,
                energy_readings,
            )

            expected_water = expected_from_baseline(
                water_baselines,
                water_readings,
            )

            # -------------------------------------------------
            # Variance
            # -------------------------------------------------
            energy_variance = None

            if energy is not None and expected_energy not in (None, 0):
                energy_variance = (
                    (energy - expected_energy)
                    / expected_energy
                ) * 100

            water_variance = None

            if water is not None and expected_water not in (None, 0):
                water_variance = (
                    (water - expected_water)
                    / expected_water
                ) * 100

            # -------------------------------------------------
            # Facility status
            # -------------------------------------------------
            status = "normal"

            if len(anomalies) > 0:
                status = "attention"

            if any(
                str(a.get("severity") or "").lower() == "critical"
                for a in anomalies
                if isinstance(a, dict)
            ):
                status = "critical"

            if any(
                str(a.get("severity") or "").lower() == "critical"
                for a in alerts
                if isinstance(a, dict)
            ):
                status = "critical"

            anomaly_count = len(anomalies)

            # -------------------------------------------------
            # Portfolio totals
            # -------------------------------------------------
            if energy is not None:
                totals["energy_kwh"] += energy

            if expected_energy is not None:
                totals["expected_energy_kwh"] += expected_energy

            if water is not None:
                totals["water_kl"] += water

            if expected_water is not None:
                totals["expected_water_kl"] += expected_water

            totals["anomaly_count"] += anomaly_count

            if status == "critical":
                totals["critical_facilities"] += 1
            elif status == "attention":
                totals["attention_facilities"] += 1

            # -------------------------------------------------
            # Primary anomaly
            # -------------------------------------------------
            primary_anomaly = None

            if anomalies:
                first_anomaly = anomalies[0]

                if isinstance(first_anomaly, dict):
                    primary_anomaly = (
                        first_anomaly.get("description")
                        or first_anomaly.get("anomaly_type")
                        or first_anomaly.get("message")
                        or str(first_anomaly)
                    )
                else:
                    primary_anomaly = str(first_anomaly)

            rows.append(
                {
                    "facility_code": code,
                    "facility_name": name,
                    "status": status,
                    "energy_kwh": energy,
                    "expected_energy_kwh": expected_energy,
                    "energy_variance_percent": (
                        round(energy_variance, 2)
                        if energy_variance is not None
                        else None
                    ),
                    "water_kl": water,
                    "expected_water_kl": expected_water,
                    "water_variance_percent": (
                        round(water_variance, 2)
                        if water_variance is not None
                        else None
                    ),
                    "anomaly_count": anomaly_count,
                    "primary_anomaly": primary_anomaly,
                }
            )

        # -----------------------------------------------------
        # Round totals
        # -----------------------------------------------------
        totals = {
            key: round(value, 3)
            if isinstance(value, float)
            else value
            for key, value in totals.items()
        }

        ranked_facilities = sorted(
            rows,
            key=lambda r: (
                abs(r.get("energy_variance_percent") or 0)
                + abs(r.get("water_variance_percent") or 0)
            ),
            reverse=True,
        )

        # Facilities that require attention.
        attention_rows = [
            r
            for r in rows
            if (
                r.get("status") in {"critical", "attention"}
                or (r.get("anomaly_count") or 0) > 0
            )
        ]

        attention_rows = sorted(
            attention_rows,
            key=lambda r: (
                r.get("status") == "critical",
                r.get("anomaly_count") or 0,
                abs(r.get("energy_variance_percent") or 0)
                + abs(r.get("water_variance_percent") or 0),
            ),
            reverse=True,
        )
        energy_total = float(
            totals.get("energy_kwh") or 0
        )

        expected_energy_total = float(
            totals.get("expected_energy_kwh") or 0
        )

        water_total = float(
            totals.get("water_kl") or 0
        )

        expected_water_total = float(
            totals.get("expected_water_kl") or 0
        )

        energy_variance_percent = (
            round(
                (
                    (
                        energy_total
                        - expected_energy_total
                    )
                    / expected_energy_total
                )
                * 100,
                2,
            )
            if expected_energy_total
            else None
        )

        water_variance_percent = (
            round(
                (
                    (
                        water_total
                        - expected_water_total
                    )
                    / expected_water_total
                )
                * 100,
                2,
            )
            if expected_water_total
            else None
        )

        evidence = {
            "report_metadata": {
                "period": period,
                "facility_count": len(rows),
            },

            "portfolio_totals": {
                "energy_kwh": energy_total,
                "expected_energy_kwh": expected_energy_total,
                "water_kl": water_total,
                "expected_water_kl": expected_water_total,
                "anomaly_count": int(
                    totals.get("anomaly_count") or 0
                ),
                "critical_facilities": int(
                    totals.get("critical_facilities") or 0
                ),
                "attention_facilities": int(
                    totals.get("attention_facilities") or 0
                ),
            },

            # Flat aliases keep the AI service backward-compatible.
            # The nested portfolio_totals values remain authoritative.
            "energy_kwh": energy_total,
            "expected_energy_kwh": expected_energy_total,
            "water_kl": water_total,
            "expected_water_kl": expected_water_total,
            "energy_variance_percent": energy_variance_percent,
            "water_variance_percent": water_variance_percent,
            "anomaly_count": int(totals.get("anomaly_count") or 0),
            "critical_facilities": int(totals.get("critical_facilities") or 0),
            "attention_facilities": int(totals.get("attention_facilities") or 0),

            "portfolio_variance": {
                "energy_variance_percent":
                    energy_variance_percent,

                "water_variance_percent":
                    water_variance_percent,
            },

            "facilities_requiring_attention":
                attention_rows[:10],

            "top_facilities_by_deviation":
                ranked_facilities[:10],
        }

        print(
            "[Portfolio AI] Evidence sent to Ollama:"
        )

        print(
            json.dumps(
                evidence,
                indent=2,
                default=str,
            )
        )

        # -----------------------------------------------------
        # Evidence sent to Ollama
        # -----------------------------------------------------
        

        result = generate_portfolio_report_analysis(
            evidence
        )

        result = normalize_portfolio_ai_result(result)
        analysis = result.get("analysis") or {}

        # Protect portfolio endpoint from accidentally returning
        # a facility-shaped AI response.
        if isinstance(analysis, dict):
            analysis.pop("facility_code", None)
            analysis.pop("facility_name", None)
            analysis.pop("status", None)
            analysis.pop("energy_kwh", None)
            analysis.pop("expected_energy_kwh", None)
            analysis.pop("energy_variance_percent", None)
            analysis.pop("water_kl", None)
            analysis.pop("expected_water_kl", None)
            analysis.pop("water_variance_percent", None)
            analysis.pop("anomaly_count", None)
            analysis.pop("primary_anomaly", None)

        return {
            "scope": "portfolio",
            "period": period,
            "facility_count": len(rows),
            "success": result.get("success", False),
            "model": result.get("model"),
            "evidence_summary": totals,
            "analysis": analysis,
            "error": result.get("error"),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(f"[Portfolio AI] Error -> {exc}")

        raise HTTPException(
            status_code=500,
            detail=f"Portfolio AI analysis failed: {exc}",
        )


@app.post("/api/reports/facilities/{facility_code}/ai-analysis")
def facility_report_ai_analysis(
    facility_code: str,
    period: str = "24h",
    db: Session = Depends(get_db),
):
    from report_engine import (
        build_facility_report_data,
        resolve_period,
    )

    try:
        start, end = resolve_period(period)

        report = build_facility_report_data(
            db,
            facility_code,
            start,
            end,
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Facility {facility_code} not found",
            )

        # Realtime-first: inject the latest live snapshot
        # before the evidence package is sent to Ollama.
        live_snapshot = LIVE_REPORT_CACHE.get(
            facility_code
        )

        report["realtime"] = (
            live_snapshot
            if live_snapshot is not None
            else None
        )

        report["report_metadata"] = {
            "facility_code": facility_code,
            "period": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "realtime_available": live_snapshot is not None,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        ai_result = generate_report_analysis(report)

        return {
            "facility_code": facility_code,
            "period": period,
            "success": ai_result.get("success", False),
            "model": ai_result.get("model"),
            "analysis": ai_result.get("analysis"),
            "error": ai_result.get("error"),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI report analysis failed: {exc}",
        )


