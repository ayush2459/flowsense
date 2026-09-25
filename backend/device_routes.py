from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    IotDevice,
    DeviceServiceHistory,
    DeviceComponent,
    DeviceComponentReplacement,
    DeviceNetworkEvent,
    DeviceOfflineEvent,
)

router = APIRouter(
    prefix="/api/devices",
    tags=["Device Management"],
)

HEARTBEAT_TIMEOUT_SECONDS = 120


def utc_now():
    return datetime.now(timezone.utc)


def normalize_datetime(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def device_to_dict(device):
    now = utc_now()

    warranty_status = "unknown"

    if device.warranty_start_date or device.warranty_end_date:
        start = normalize_datetime(device.warranty_start_date)
        end = normalize_datetime(device.warranty_end_date)

        if start and now < start:
            warranty_status = "not_started"
        elif end and now > end:
            warranty_status = "expired"
        else:
            warranty_status = "active"

    last_seen = normalize_datetime(device.last_seen_at)

    realtime_status = "unknown"

    if device.decommissioned_at:
        realtime_status = "decommissioned"
    elif last_seen:
        age_seconds = (now - last_seen).total_seconds()

        if age_seconds <= HEARTBEAT_TIMEOUT_SECONDS:
            realtime_status = "online"
        else:
            realtime_status = "offline"

    return {
        "iot_device_id": str(device.iot_device_id),
        "facility_id": str(device.facility_id),
        "device_code": device.device_code,
        "device_name": device.device_name,
        "device_model": device.device_model,
        "firmware_version": device.firmware_version,
        "communication_protocol": device.communication_protocol,
        "installation_location": device.installation_location,

        "status": device.status,
        "realtime_status": realtime_status,
        "last_seen_at": device.last_seen_at,

        "serial_number": device.serial_number,
        "network_type": device.network_type,
        "network_identifier": device.network_identifier,

        "installation_date": device.installation_date,
        "commissioned_at": device.commissioned_at,

        "warranty_start_date": device.warranty_start_date,
        "warranty_end_date": device.warranty_end_date,
        "warranty_status": warranty_status,

        "decommissioned_at": device.decommissioned_at,
        "decommission_reason": device.decommission_reason,
    }


def get_device_or_404(device_id, db):
    device = (
        db.query(IotDevice)
        .filter(IotDevice.iot_device_id == device_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    return device


# ============================================================
# DEVICE LIST / DETAIL
# ============================================================

@router.get("")
def get_devices(
    db: Session = Depends(get_db),
):
    devices = (
        db.query(IotDevice)
        .order_by(IotDevice.device_code.asc())
        .all()
    )

    return {
        "count": len(devices),
        "devices": [
            device_to_dict(device)
            for device in devices
        ],
    }


@router.get("/{device_id}")
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    return device_to_dict(device)


# ============================================================
# REAL DEVICE HEARTBEAT
# ============================================================

@router.post("/{device_code}/heartbeat")
def device_heartbeat(
    device_code: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Real IoT device heartbeat.

    The device must call this endpoint periodically.

    Expected payload:

    {
        "network_type": "Wi-Fi",
        "network_identifier": "device-network-id",
        "firmware_version": "1.0.1",
        "signal_strength": -61
    }

    No synthetic timestamp is accepted as the heartbeat time.
    The backend records the time at which the request was received.
    """

    device = (
        db.query(IotDevice)
        .filter(IotDevice.device_code == device_code)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    if device.decommissioned_at:
        raise HTTPException(
            status_code=409,
            detail="Device has been decommissioned",
        )

    now = utc_now()

    previous_status = device.status

    network_type = payload.get("network_type")
    network_identifier = payload.get("network_identifier")
    firmware_version = payload.get("firmware_version")

    if network_type is not None:
        allowed_network_types = {
            "Wi-Fi",
            "4G",
            "Ethernet",
            "Mesh",
            "Other",
        }

        if network_type not in allowed_network_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid network_type. "
                    "Allowed values: Wi-Fi, 4G, Ethernet, Mesh, Other"
                ),
            )

        device.network_type = network_type

    if network_identifier is not None:
        device.network_identifier = str(network_identifier)

    if firmware_version is not None:
        device.firmware_version = str(firmware_version)

    device.last_seen_at = now
    device.status = "online"

    event_metadata = dict(payload)

    db.add(
        DeviceNetworkEvent(
            iot_device_id=device.iot_device_id,
            event_type="online",
            event_time=now,
            network_type=device.network_type,
            network_identifier=device.network_identifier,
            source="device_heartbeat",
            metadata_json=event_metadata,
        )
    )

    db.commit()
    db.refresh(device)

    return {
        "status": "accepted",
        "device_code": device.device_code,
        "device_status": "online",
        "previous_status": previous_status,
        "heartbeat_at": now,
        "last_seen_at": device.last_seen_at,
        "network_type": device.network_type,
        "network_identifier": device.network_identifier,
    }


# ============================================================
# DEVICE HEALTH
# ============================================================

@router.get("/{device_code}/realtime-health")
def device_realtime_health(
    device_code: str,
    db: Session = Depends(get_db),
):
    device = (
        db.query(IotDevice)
        .filter(IotDevice.device_code == device_code)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    now = utc_now()
    last_seen = normalize_datetime(device.last_seen_at)

    if device.decommissioned_at:
        realtime_status = "decommissioned"
        seconds_since_seen = None

    elif last_seen is None:
        realtime_status = "unknown"
        seconds_since_seen = None

    else:
        seconds_since_seen = max(
            0,
            int((now - last_seen).total_seconds()),
        )

        realtime_status = (
            "online"
            if seconds_since_seen <= HEARTBEAT_TIMEOUT_SECONDS
            else "offline"
        )

    reason = None
    evidence = None

    if realtime_status == "offline":
        reason = "heartbeat_timeout"
        evidence = (
            f"No heartbeat received for "
            f"{seconds_since_seen} seconds. "
            f"Threshold: {HEARTBEAT_TIMEOUT_SECONDS} seconds."
        )

    return {
        "device_code": device.device_code,
        "status": realtime_status,
        "database_status": device.status,
        "last_seen_at": device.last_seen_at,
        "checked_at": now,
        "seconds_since_last_seen": seconds_since_seen,
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "offline_reason": reason,
        "evidence": evidence,
        "network_type": device.network_type,
        "network_identifier": device.network_identifier,
    }


# ============================================================
# LIFECYCLE
# ============================================================

@router.get("/{device_id}/lifecycle")
def get_device_lifecycle(
    device_id: str,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    services = (
        db.query(DeviceServiceHistory)
        .filter(DeviceServiceHistory.iot_device_id == device_id)
        .order_by(DeviceServiceHistory.service_date.desc())
        .all()
    )

    components = (
        db.query(DeviceComponent)
        .filter(DeviceComponent.iot_device_id == device_id)
        .order_by(DeviceComponent.created_at.desc())
        .all()
    )

    return {
        "device": device_to_dict(device),

        "services": [
            {
                "service_id": str(service.service_id),
                "service_date": service.service_date,
                "service_type": service.service_type,
                "description": service.description,
                "technician_name": service.technician_name,
                "service_vendor": service.service_vendor,
                "repair_required": service.repair_required,
                "warranty_applicable": service.warranty_applicable,
                "warranty_claim_reference": service.warranty_claim_reference,
                "service_cost": service.service_cost,
                "next_service_date": service.next_service_date,
            }
            for service in services
        ],

        "components": [
            {
                "component_id": str(component.component_id),
                "component_type": component.component_type,
                "component_name": component.component_name,
                "serial_number": component.serial_number,
                "installed_at": component.installed_at,
                "status": component.status,
            }
            for component in components
        ],
    }


# ============================================================
# SERVICE HISTORY
# ============================================================

@router.get("/{device_id}/services")
def get_device_services(
    device_id: str,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    services = (
        db.query(DeviceServiceHistory)
        .filter(DeviceServiceHistory.iot_device_id == device_id)
        .order_by(DeviceServiceHistory.service_date.desc())
        .all()
    )

    return {
        "device_id": str(device.iot_device_id),
        "count": len(services),
        "services": [
            {
                "service_id": str(service.service_id),
                "service_date": service.service_date,
                "service_type": service.service_type,
                "description": service.description,
                "technician_name": service.technician_name,
                "service_vendor": service.service_vendor,
                "repair_required": service.repair_required,
                "warranty_applicable": service.warranty_applicable,
                "warranty_claim_reference": service.warranty_claim_reference,
                "service_cost": service.service_cost,
                "next_service_date": service.next_service_date,
            }
            for service in services
        ],
    }


@router.post("/{device_id}/services")
def create_device_service(
    device_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    service = DeviceServiceHistory(
        iot_device_id=device.iot_device_id,
        service_date=payload.get("service_date") or utc_now(),
        service_type=payload.get(
            "service_type",
            "maintenance",
        ),
        description=payload.get("description"),
        technician_name=payload.get("technician_name"),
        service_vendor=payload.get("service_vendor"),
        repair_required=bool(
            payload.get("repair_required", False)
        ),
        warranty_applicable=payload.get(
            "warranty_applicable"
        ),
        warranty_claim_reference=payload.get(
            "warranty_claim_reference"
        ),
        service_cost=payload.get("service_cost"),
        next_service_date=payload.get(
            "next_service_date"
        ),
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return {
        "status": "created",
        "service_id": str(service.service_id),
        "device_id": str(device.iot_device_id),
    }


# ============================================================
# COMPONENTS
# ============================================================

@router.get("/{device_id}/components")
def get_device_components(
    device_id: str,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    components = (
        db.query(DeviceComponent)
        .filter(DeviceComponent.iot_device_id == device_id)
        .order_by(DeviceComponent.created_at.desc())
        .all()
    )

    return {
        "device_id": str(device.iot_device_id),
        "count": len(components),
        "components": [
            {
                "component_id": str(component.component_id),
                "component_type": component.component_type,
                "component_name": component.component_name,
                "serial_number": component.serial_number,
                "installed_at": component.installed_at,
                "status": component.status,
            }
            for component in components
        ],
    }


@router.post("/{device_id}/components")
def create_device_component(
    device_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    if not payload.get("component_type"):
        raise HTTPException(
            status_code=400,
            detail="component_type is required",
        )

    if not payload.get("component_name"):
        raise HTTPException(
            status_code=400,
            detail="component_name is required",
        )

    component = DeviceComponent(
        iot_device_id=device.iot_device_id,
        component_type=payload["component_type"],
        component_name=payload["component_name"],
        serial_number=payload.get("serial_number"),
        installed_at=payload.get("installed_at") or utc_now(),
        status=payload.get("status", "active"),
    )

    db.add(component)
    db.commit()
    db.refresh(component)

    return {
        "status": "created",
        "component_id": str(component.component_id),
        "device_id": str(device.iot_device_id),
    }


# ============================================================
# COMPONENT REPLACEMENT
# ============================================================

@router.post("/{device_id}/components/replacements")
def replace_device_component(
    device_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    device = get_device_or_404(device_id, db)

    component_id = payload.get("component_id")

    if not component_id:
        raise HTTPException(
            status_code=400,
            detail="component_id is required",
        )

    component = (
        db.query(DeviceComponent)
        .filter(
            DeviceComponent.component_id == component_id,
            DeviceComponent.iot_device_id == device.iot_device_id,
        )
        .first()
    )

    if not component:
        raise HTTPException(
            status_code=404,
            detail="Component not found for this device",
        )

    old_serial = component.serial_number
    new_serial = payload.get("new_serial_number")

    replacement = DeviceComponentReplacement(
        component_id=component.component_id,
        service_id=payload.get("service_id"),
        old_serial_number=old_serial,
        new_serial_number=new_serial,
        replacement_date=payload.get(
            "replacement_date"
        ) or utc_now(),
        replacement_reason=payload.get(
            "replacement_reason"
        ),
        warranty_covered=payload.get(
            "warranty_covered"
        ),
    )

    if new_serial:
        component.serial_number = new_serial

    db.add(replacement)
    db.commit()
    db.refresh(replacement)

    return {
        "status": "created",
        "replacement_id": str(
            replacement.replacement_id
        ),
        "component_id": str(
            component.component_id
        ),
        "old_serial_number": old_serial,
        "new_serial_number": new_serial,
    }


# ============================================================
# NETWORK EVENTS
# ============================================================
@router.get("/{device_code}/network")
def get_device_network(
    device_code: str,
    db: Session = Depends(get_db),
):
    device = (
        db.query(IotDevice)
        .filter(IotDevice.device_code == device_code)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    events = (
        db.query(DeviceNetworkEvent)
        .filter(
            DeviceNetworkEvent.iot_device_id
            == device.iot_device_id
        )
        .order_by(DeviceNetworkEvent.event_time.desc())
        .limit(100)
        .all()
    )

    return {
        "device_id": str(device.iot_device_id),
        "device_code": device.device_code,
        "status": device_to_dict(device)["realtime_status"],
        "network_type": device.network_type,
        "network_identifier": device.network_identifier,
        "last_seen_at": device.last_seen_at,
        "events": [
            {
                "network_event_id": event.network_event_id,
                "event_type": event.event_type,
                "event_time": event.event_time,
                "network_type": event.network_type,
                "network_identifier": event.network_identifier,
                "source": event.source,
                "metadata": event.metadata_json,
            }
            for event in events
        ],
    }

# ============================================================
# OFFLINE EVENTS
# ============================================================

@router.get("/{device_code}/offline-events")
def get_device_offline_events(
    device_code: str,
    db: Session = Depends(get_db),
):
    device = (
        db.query(IotDevice)
        .filter(IotDevice.device_code == device_code)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    events = (
        db.query(DeviceOfflineEvent)
        .filter(
            DeviceOfflineEvent.iot_device_id
            == device.iot_device_id
        )
        .order_by(DeviceOfflineEvent.offline_at.desc())
        .limit(100)
        .all()
    )

    return {
        "device_id": str(device.iot_device_id),
        "device_code": device.device_code,
        "count": len(events),
        "offline_events": [
            {
                "offline_event_id": event.offline_event_id,
                "offline_at": event.offline_at,
                "recovered_at": event.recovered_at,
                "duration_seconds": event.duration_seconds,
                "detected_reason": event.detected_reason,
                "evidence": event.evidence,
            }
            for event in events
        ],
    }


# ============================================================
# UPTIME
# ============================================================

@router.get("/{device_code}/network/uptime")
def get_device_uptime(
    device_code: str,
    hours: int = 24,
    db: Session = Depends(get_db),
):
    """
    Calculate device uptime from real heartbeat evidence.

    A heartbeat proves the device was reachable at the
    heartbeat timestamp. The device remains considered
    online for the heartbeat timeout window unless another
    heartbeat arrives earlier.

    No synthetic uptime data is generated.
    """

    device = (
        db.query(IotDevice)
        .filter(IotDevice.device_code == device_code)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    hours = max(1, min(hours, 8760))

    heartbeat_timeout_seconds = 120

    row = db.execute(
        text(
            """
            WITH boundaries AS (
                SELECT
                    NOW() - (:hours || ' hours')::interval
                        AS start_time,
                    NOW() AS end_time
            ),

            heartbeat_events AS (
                SELECT
                    event_time
                FROM device_network_events
                WHERE iot_device_id = :device_id
                  AND event_type = 'online'
                  AND source = 'device_heartbeat'
                  AND event_time <= NOW()
                  AND event_time >=
                      NOW()
                      - (:hours || ' hours')::interval
                      - (:heartbeat_timeout || ' seconds')::interval
                ORDER BY event_time
            ),

            heartbeat_intervals AS (
                SELECT
                    event_time,
                    LEAD(event_time) OVER (
                        ORDER BY event_time
                    ) AS next_heartbeat
                FROM heartbeat_events
            ),

            uptime_intervals AS (
                SELECT
                    GREATEST(
                        event_time,
                        NOW()
                        - (:hours || ' hours')::interval
                    ) AS interval_start,

                    LEAST(
                        COALESCE(
                            next_heartbeat,
                            NOW()
                        ),
                        event_time
                        + (:heartbeat_timeout || ' seconds')::interval,
                        NOW()
                    ) AS interval_end

                FROM heartbeat_intervals
            )

            SELECT
                COALESCE(
                    SUM(
                        GREATEST(
                            0,
                            EXTRACT(
                                EPOCH FROM (
                                    interval_end
                                    - interval_start
                                )
                            )
                        )
                    ),
                    0
                ) AS online_seconds,

                EXTRACT(
                    EPOCH FROM (
                        NOW()
                        -
                        (
                            NOW()
                            - (:hours || ' hours')::interval
                        )
                    )
                ) AS total_seconds

            FROM uptime_intervals
            """
        ),
        {
            "device_id": device.iot_device_id,
            "hours": hours,
            "heartbeat_timeout": heartbeat_timeout_seconds,
        },
    ).mappings().first()

    online_seconds = float(
        row["online_seconds"] or 0
    )

    total_seconds = float(
        row["total_seconds"] or 0
    )

    uptime_percent = (
        (online_seconds / total_seconds) * 100
        if total_seconds > 0
        else 0
    )

    return {
        "device_id": str(device.iot_device_id),
        "device_code": device.device_code,
        "period_hours": hours,
        "online_seconds": round(
            online_seconds,
            2,
        ),
        "total_seconds": round(
            total_seconds,
            2,
        ),
        "uptime_percent": round(
            uptime_percent,
            2,
        ),
        "heartbeat_timeout_seconds":
            heartbeat_timeout_seconds,
        "calculation":
            "Based on real device heartbeat evidence",
    }