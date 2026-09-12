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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
# ALL-FACILITIES WEBSOCKET
# ============================================================

@app.websocket(
    "/ws/live/all"
)
async def live_all_websocket(
    websocket: WebSocket,
):

    channel = "all"

    await manager.connect(
        channel,
        websocket,
    )

    try:

        while True:

            try:

                message = (
                    await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30,
                    )
                )

                if (
                    message.lower()
                    == "ping"
                ):

                    await websocket.send_json(
                        {
                            "type":
                                "pong",

                            "channel":
                                "all",

                            "timestamp":
                                datetime.now(
                                    timezone.utc
                                ).isoformat(),
                        }
                    )

            except asyncio.TimeoutError:

                await websocket.send_json(
                    {
                        "type":
                            "heartbeat",

                        "channel":
                            "all",

                        "timestamp":
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                    }
                )

    except WebSocketDisconnect:

        manager.disconnect(
            channel,
            websocket,
        )

    except Exception as exc:

        manager.disconnect(
            channel,
            websocket,
        )

        print(
            f"[WebSocket] Error -> "
            f"all: {exc}"
        )


# ============================================================
# FACILITY WEBSOCKET
# ============================================================

@app.websocket(
    "/ws/live/{facility_code}"
)
async def live_websocket(
    websocket: WebSocket,
    facility_code: str,
):

    channel = facility_code

    await manager.connect(
        channel,
        websocket,
    )

    try:

        while True:

            try:

                message = (
                    await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30,
                    )
                )

                if (
                    message.lower()
                    == "ping"
                ):

                    await websocket.send_json(
                        {
                            "type":
                                "pong",

                            "facility_code":
                                facility_code,

                            "timestamp":
                                datetime.now(
                                    timezone.utc
                                ).isoformat(),
                        }
                    )

            except asyncio.TimeoutError:

                await websocket.send_json(
                    {
                        "type":
                            "heartbeat",

                        "facility_code":
                            facility_code,

                        "timestamp":
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                    }
                )

    except WebSocketDisconnect:

        manager.disconnect(
            channel,
            websocket,
        )

    except Exception as exc:

        manager.disconnect(
            channel,
            websocket,
        )

        print(
            f"[WebSocket] Error -> "
            f"{facility_code}: {exc}"
        )