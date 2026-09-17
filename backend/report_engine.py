"""
FlowSense Report Data Engine

Builds report-ready data exclusively from the existing FlowSense
PostgreSQL database.

IMPORTANT:
- No seed/demo values are created here.
- No fabricated fallback metrics are used.
- Missing data is returned as None / empty lists.
- Backend/database values remain authoritative.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _number(value: Any) -> Optional[float]:
    """Safely convert DB Numeric/other values to float."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> Optional[str]:
    """Convert datetime values to ISO strings."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Convert SQLAlchemy Row to a JSON-friendly dictionary."""
    data = dict(row._mapping)

    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, datetime):
            data[key] = value.isoformat()

    return data


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------

def get_facility(
    db: Session,
    facility_code: str,
) -> Optional[Dict[str, Any]]:
    """
    Get one facility from the authoritative facilities table.
    """

    row = db.execute(
        text(
            """
            SELECT
                facility_id,
                facility_code,
                facility_name,
                facility_type,
                city,
                state,
                country,
                area_sq_m,
                status,
                created_at
            FROM facilities
            WHERE facility_code = :facility_code
            LIMIT 1
            """
        ),
        {"facility_code": facility_code},
    ).first()

    if not row:
        return None

    return _row_to_dict(row)


def get_all_facilities(
    db: Session,
) -> List[Dict[str, Any]]:
    """
    Get all active facilities.
    """

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
                country,
                area_sq_m,
                status,
                created_at
            FROM facilities
            WHERE LOWER(COALESCE(status, 'active')) = 'active'
            ORDER BY facility_code
            """
        )
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Meters
# ---------------------------------------------------------------------------

def get_facility_meters(
    db: Session,
    facility_code: str,
) -> List[Dict[str, Any]]:
    """
    Return all meters belonging to a facility.
    """

    rows = db.execute(
        text(
            """
            SELECT
                m.meter_id,
                m.meter_code,
                m.meter_name,
                m.resource_type,
                m.unit,
                m.meter_serial_number,
                m.installation_date,
                m.status
            FROM meters m
            JOIN facilities f
                ON f.facility_id = m.facility_id
            WHERE f.facility_code = :facility_code
            ORDER BY m.resource_type, m.meter_code
            """
        ),
        {"facility_code": facility_code},
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Latest meter readings
# ---------------------------------------------------------------------------

def get_latest_meter_readings(
    db: Session,
    facility_code: str,
) -> List[Dict[str, Any]]:
    """
    Get the latest reading for every meter belonging to a facility.
    """

    rows = db.execute(
        text(
            """
            SELECT
                m.meter_code,
                m.meter_name,
                m.resource_type,
                m.unit,
                r.reading_time,
                r.reading_value,
                r.quality_status,
                r.source
            FROM meters m
            JOIN facilities f
                ON f.facility_id = m.facility_id
            LEFT JOIN LATERAL (
                SELECT
                    mr.reading_time,
                    mr.reading_value,
                    mr.quality_status,
                    mr.source
                FROM meter_readings mr
                WHERE mr.meter_id = m.meter_id
                ORDER BY mr.reading_time DESC
                LIMIT 1
            ) r ON TRUE
            WHERE f.facility_code = :facility_code
            ORDER BY m.resource_type, m.meter_code
            """
        ),
        {"facility_code": facility_code},
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Energy / Water meter history
# ---------------------------------------------------------------------------

def get_meter_history(
    db: Session,
    facility_code: str,
    resource_type: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Get real meter readings for a facility/resource and reporting period.
    """

    rows = db.execute(
        text(
            """
            SELECT
                m.meter_code,
                m.meter_name,
                m.resource_type,
                m.unit,
                mr.reading_time,
                mr.reading_value,
                mr.quality_status,
                mr.source
            FROM meter_readings mr
            JOIN meters m
                ON m.meter_id = mr.meter_id
            JOIN facilities f
                ON f.facility_id = m.facility_id
            WHERE f.facility_code = :facility_code
              AND LOWER(m.resource_type) = LOWER(:resource_type)
              AND mr.reading_time >= :start_time
              AND mr.reading_time <= :end_time
            ORDER BY mr.reading_time ASC
            """
        ),
        {
            "facility_code": facility_code,
            "resource_type": resource_type,
            "start_time": start_time,
            "end_time": end_time,
        },
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def get_baselines(
    db: Session,
    facility_code: str,
    resource_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get configured consumption baselines.

    These values come directly from consumption_baselines.
    """

    query = """
        SELECT
            cb.resource_type,
            cb.hour_of_day,
            cb.day_of_week,
            cb.expected_value,
            cb.lower_threshold,
            cb.upper_threshold,
            cb.calculation_period_days,
            cb.updated_at
        FROM consumption_baselines cb
        JOIN facilities f
            ON f.facility_id = cb.facility_id
        WHERE f.facility_code = :facility_code
    """

    params: Dict[str, Any] = {
        "facility_code": facility_code,
    }

    if resource_type:
        query += """
            AND LOWER(cb.resource_type) = LOWER(:resource_type)
        """
        params["resource_type"] = resource_type

    query += """
        ORDER BY
            cb.resource_type,
            cb.day_of_week,
            cb.hour_of_day
    """

    rows = db.execute(text(query), params).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def get_reconciliation(
    db: Session,
    facility_code: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Get real resource reconciliation records.
    """

    rows = db.execute(
        text(
            """
            SELECT
                rr.resource_type,
                rr.reconciliation_time,
                rr.main_meter_value,
                rr.observed_iot_value,
                rr.expected_value,
                rr.unaccounted_value,
                rr.unaccounted_percent,
                rr.estimated_loss,
                rr.loss_unit,
                rr.status
            FROM resource_reconciliation rr
            JOIN facilities f
                ON f.facility_id = rr.facility_id
            WHERE f.facility_code = :facility_code
              AND rr.reconciliation_time >= :start_time
              AND rr.reconciliation_time <= :end_time
            ORDER BY rr.reconciliation_time ASC
            """
        ),
        {
            "facility_code": facility_code,
            "start_time": start_time,
            "end_time": end_time,
        },
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------

def get_anomalies(
    db: Session,
    facility_code: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Get real anomalies detected/stored for the facility.
    """

    rows = db.execute(
        text(
            """
            SELECT
                a.anomaly_id,
                a.anomaly_type,
                a.resource_type,
                a.severity,
                a.detected_at,
                a.expected_value,
                a.actual_value,
                a.deviation_percent,
                a.estimated_loss,
                a.loss_unit,
                a.status,
                a.description
            FROM anomalies a
            JOIN facilities f
                ON f.facility_id = a.facility_id
            WHERE f.facility_code = :facility_code
              AND a.detected_at >= :start_time
              AND a.detected_at <= :end_time
            ORDER BY a.detected_at DESC
            """
        ),
        {
            "facility_code": facility_code,
            "start_time": start_time,
            "end_time": end_time,
        },
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def get_alerts(
    db: Session,
    facility_code: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Get real alerts for the reporting period.
    """

    rows = db.execute(
        text(
            """
            SELECT
                al.alert_id,
                al.alert_title,
                al.alert_message,
                al.severity,
                al.triggered_at,
                al.status
            FROM alerts al
            JOIN facilities f
                ON f.facility_id = al.facility_id
            WHERE f.facility_code = :facility_code
              AND al.triggered_at >= :start_time
              AND al.triggered_at <= :end_time
            ORDER BY al.triggered_at DESC
            """
        ),
        {
            "facility_code": facility_code,
            "start_time": start_time,
            "end_time": end_time,
        },
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# IoT devices
# ---------------------------------------------------------------------------

def get_devices(
    db: Session,
    facility_code: str,
) -> List[Dict[str, Any]]:
    """
    Get IoT devices associated with the facility.
    """

    rows = db.execute(
        text(
            """
            SELECT
                d.device_code,
                d.device_name,
                d.device_model,
                d.firmware_version,
                d.communication_protocol,
                d.installation_location,
                d.status,
                d.last_seen_at
            FROM iot_devices d
            JOIN facilities f
                ON f.facility_id = d.facility_id
            WHERE f.facility_code = :facility_code
            ORDER BY d.device_code
            """
        ),
        {"facility_code": facility_code},
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------

def get_sensors(
    db: Session,
    facility_code: str,
) -> List[Dict[str, Any]]:
    """
    Get configured IoT sensors belonging to the facility.
    """

    rows = db.execute(
        text(
            """
            SELECT
                d.device_code,
                s.sensor_code,
                s.sensor_name,
                s.sensor_type,
                s.measurement,
                s.unit,
                s.data_type,
                s.status
            FROM iot_sensors s
            JOIN iot_devices d
                ON d.iot_device_id = s.iot_device_id
            JOIN facilities f
                ON f.facility_id = d.facility_id
            WHERE f.facility_code = :facility_code
            ORDER BY d.device_code, s.sensor_code
            """
        ),
        {"facility_code": facility_code},
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Monthly summaries
# ---------------------------------------------------------------------------

def get_monthly_summaries(
    db: Session,
    facility_code: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Get stored monthly resource summaries overlapping the report period.
    """

    rows = db.execute(
        text(
            """
            SELECT
                mrs.month_start,
                mrs.energy_consumption_kwh,
                mrs.water_consumption_kl,
                mrs.peak_power_kw,
                mrs.anomaly_count,
                mrs.estimated_energy_loss_kwh,
                mrs.estimated_water_loss_kl
            FROM monthly_resource_summary mrs
            JOIN facilities f
                ON f.facility_id = mrs.facility_id
            WHERE f.facility_code = :facility_code
              AND mrs.month_start >= :start_time
              AND mrs.month_start <= :end_time
            ORDER BY mrs.month_start ASC
            """
        ),
        {
            "facility_code": facility_code,
            "start_time": start_time,
            "end_time": end_time,
        },
    ).fetchall()

    return [_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Current facility snapshot
# ---------------------------------------------------------------------------

def build_current_snapshot(
    db: Session,
    facility_code: str,
) -> Dict[str, Any]:
    """
    Build a current snapshot from the database.

    This is a database snapshot, not an artificial/default payload.
    """

    facility = get_facility(db, facility_code)

    if not facility:
        raise ValueError(
            f"Facility not found: {facility_code}"
        )

    meters = get_latest_meter_readings(
        db,
        facility_code,
    )

    devices = get_devices(
        db,
        facility_code,
    )

    energy = None
    water = None
    energy_time = None
    water_time = None

    for reading in meters:
        resource = str(
            reading.get("resource_type") or ""
        ).lower()

        value = _number(
            reading.get("reading_value")
        )

        if resource == "energy" and energy is None:
            energy = value
            energy_time = reading.get(
                "reading_time"
            )

        elif resource == "water" and water is None:
            water = value
            water_time = reading.get(
                "reading_time"
            )

    latest_seen = None

    for device in devices:
        seen = device.get("last_seen_at")

        if seen is not None:
            if (
                latest_seen is None
                or str(seen) > str(latest_seen)
            ):
                latest_seen = seen

    return {
        "facility": facility,
        "latest_energy": {
            "value": energy,
            "reading_time": _iso(energy_time),
        },
        "latest_water": {
            "value": water,
            "reading_time": _iso(water_time),
        },
        "devices": devices,
        "latest_device_seen": _iso(
            latest_seen
        ),
    }


# ---------------------------------------------------------------------------
# Facility report data
# ---------------------------------------------------------------------------

def build_facility_report_data(
    db: Session,
    facility_code: str,
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    """
    Build the complete evidence/data package for one facility.

    This function DOES NOT call an LLM and DOES NOT generate a PDF.

    Its output is the authoritative input for:
        1. AI narrative generation
        2. ReportLab PDF generation
    """

    facility = get_facility(
        db,
        facility_code,
    )

    if not facility:
        raise ValueError(
            f"Facility not found: {facility_code}"
        )

    energy_history = get_meter_history(
        db,
        facility_code,
        "energy",
        start_time,
        end_time,
    )

    water_history = get_meter_history(
        db,
        facility_code,
        "water",
        start_time,
        end_time,
    )

    return {
        "report_metadata": {
            "scope": "facility",
            "facility_code": facility_code,
            "period_start": _iso(start_time),
            "period_end": _iso(end_time),
            "generated_at": _iso(_utc_now()),
            "data_source": "FlowSense PostgreSQL",
        },

        "facility": facility,

        "meters": get_facility_meters(
            db,
            facility_code,
        ),

        "current_snapshot": build_current_snapshot(
            db,
            facility_code,
        ),

        "energy": {
            "readings": energy_history,
            "baselines": get_baselines(
                db,
                facility_code,
                "energy",
            ),
        },

        "water": {
            "readings": water_history,
            "baselines": get_baselines(
                db,
                facility_code,
                "water",
            ),
        },

        "reconciliation": get_reconciliation(
            db,
            facility_code,
            start_time,
            end_time,
        ),

        "anomalies": get_anomalies(
            db,
            facility_code,
            start_time,
            end_time,
        ),

        "alerts": get_alerts(
            db,
            facility_code,
            start_time,
            end_time,
        ),

        "devices": get_devices(
            db,
            facility_code,
        ),

        "sensors": get_sensors(
            db,
            facility_code,
        ),

        "monthly_summaries": get_monthly_summaries(
            db,
            facility_code,
            start_time,
            end_time,
        ),
    }


# ---------------------------------------------------------------------------
# Portfolio / All-facilities report
# ---------------------------------------------------------------------------

def build_portfolio_report_data(
    db: Session,
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    """
    Build the report evidence package for ALL active facilities.

    No artificial aggregation is performed here.
    Each facility gets its own real data package.
    """

    facilities = get_all_facilities(db)

    facility_reports: List[Dict[str, Any]] = []

    for facility in facilities:
        code = facility.get("facility_code")

        if not code:
            continue

        try:
            facility_reports.append(
                build_facility_report_data(
                    db,
                    code,
                    start_time,
                    end_time,
                )
            )
        except Exception as exc:
            # Preserve the facility in the report while making
            # the failure explicit instead of fabricating data.
            facility_reports.append(
                {
                    "report_metadata": {
                        "scope": "facility",
                        "facility_code": code,
                        "period_start": _iso(start_time),
                        "period_end": _iso(end_time),
                        "generated_at": _iso(
                            _utc_now()
                        ),
                        "data_source": "FlowSense PostgreSQL",
                    },
                    "facility": facility,
                    "data_error": str(exc),
                }
            )

    return {
        "report_metadata": {
            "scope": "all_facilities",
            "period_start": _iso(start_time),
            "period_end": _iso(end_time),
            "generated_at": _iso(_utc_now()),
            "data_source": "FlowSense PostgreSQL",
            "facility_count": len(facility_reports),
        },
        "facilities": facility_reports,
    }


# ---------------------------------------------------------------------------
# Convenience period resolver
# ---------------------------------------------------------------------------

def resolve_period(
    period: str = "24h",
    end_time: Optional[datetime] = None,
) -> tuple[datetime, datetime]:
    """
    Resolve supported report periods.

    Supported:
        1h
        6h
        24h
        7d
        30d
    """

    end = end_time or _utc_now()

    period = (
        str(period or "24h")
        .strip()
        .lower()
    )

    durations = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if period not in durations:
        raise ValueError(
            "Unsupported report period. "
            "Use one of: 1h, 6h, 24h, 7d, 30d."
        )

    return (
        end - durations[period],
        end,
    )