from device_realtime import broadcast_device_heartbeat
from datetime import datetime, timedelta, timezone
from fastapi import (
    BackgroundTasks,
    Depends,
    HTTPException,
    APIRouter,
)
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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        broadcast_device_heartbeat,
        {
            "type": "device_heartbeat",
            "device_code": device.device_code,
            "device_status": "online",
            "status": "online",
            "database_status": device.status,
            "last_seen_at": device.last_seen_at,
            "heartbeat_at": now,
            "network_type": device.network_type,
            "network_identifier": device.network_identifier,
            "firmware_version": device.firmware_version,
            "signal_strength": payload.get("signal_strength"),
        },
    )

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
    Calculate uptime using only real device heartbeat evidence.

    Important:
    - No synthetic uptime is generated.
    - A heartbeat proves the device was online at that point.
    - The device remains online for HEARTBEAT_TIMEOUT_SECONDS
      after the heartbeat.
    - If another heartbeat arrives before the timeout, the
      interval remains online.
    - If the gap exceeds the timeout, the remaining gap is
      classified as offline.
    - Time before the first available heartbeat is UNKNOWN.
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

    heartbeat_timeout_seconds = HEARTBEAT_TIMEOUT_SECONDS

    now = utc_now()

    period_start = now - timedelta(hours=hours)

    period_end = now

    # ---------------------------------------------------------
    # Get REAL heartbeat events from PostgreSQL
    # ---------------------------------------------------------

    events = (
        db.query(DeviceNetworkEvent)
        .filter(
            DeviceNetworkEvent.iot_device_id == device.iot_device_id,
            DeviceNetworkEvent.event_type == "online",
            DeviceNetworkEvent.source == "device_heartbeat",
            DeviceNetworkEvent.event_time <= period_end,
            DeviceNetworkEvent.event_time >= (
                period_start
                - timedelta(seconds=heartbeat_timeout_seconds)
            ),
        )
        .order_by(
            DeviceNetworkEvent.event_time.asc()
        )
        .all()
    )

    heartbeat_times = []

    for event in events:

        event_time = event.event_time

        if event_time is None:
            continue

        if event_time.tzinfo is None:
            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        heartbeat_times.append(event_time)

    # last_seen_at is also real heartbeat evidence.
    if device.last_seen_at:

        last_seen = device.last_seen_at

        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(
                tzinfo=timezone.utc
            )

        if (
            period_start
            - timedelta(seconds=heartbeat_timeout_seconds)
            <= last_seen
            <= period_end
        ):
            heartbeat_times.append(last_seen)

    # Remove duplicates and sort.
    heartbeat_times = sorted(
        set(heartbeat_times)
    )

    total_seconds = float(
        (
            period_end
            - period_start
        ).total_seconds()
    )

    online_seconds = 0.0
    offline_seconds = 0.0

    # ---------------------------------------------------------
    # Calculate REAL observed uptime
    # ---------------------------------------------------------

    if heartbeat_times:

        for index, heartbeat_time in enumerate(
            heartbeat_times
        ):

            if heartbeat_time > period_end:
                continue

            # The interval ends at:
            # - next heartbeat
            # - current time
            # whichever comes first.
            if index + 1 < len(heartbeat_times):

                next_heartbeat = heartbeat_times[
                    index + 1
                ]

                interval_end = min(
                    next_heartbeat,
                    period_end,
                )

            else:

                interval_end = period_end

            # Ignore intervals completely before the
            # requested reporting period.
            if interval_end <= period_start:
                continue

            # -------------------------------------------------
            # ONLINE portion
            # -------------------------------------------------

            online_start = max(
                heartbeat_time,
                period_start,
            )

            online_end = min(
                heartbeat_time
                + timedelta(
                    seconds=heartbeat_timeout_seconds
                ),
                interval_end,
                period_end,
            )

            if online_end > online_start:

                online_seconds += (
                    online_end
                    - online_start
                ).total_seconds()

            # -------------------------------------------------
            # OFFLINE portion
            #
            # Once the heartbeat timeout has passed,
            # the device is considered offline until the
            # next real heartbeat.
            # -------------------------------------------------

            offline_start = max(
                heartbeat_time
                + timedelta(
                    seconds=heartbeat_timeout_seconds
                ),
                period_start,
            )

            offline_end = min(
                interval_end,
                period_end,
            )

            if offline_end > offline_start:

                offline_seconds += (
                    offline_end
                    - offline_start
                ).total_seconds()

    # ---------------------------------------------------------
    # Observed evidence
    # ---------------------------------------------------------

    observed_seconds = (
        online_seconds
        + offline_seconds
    )

    observed_seconds = min(
        max(observed_seconds, 0.0),
        total_seconds,
    )

    unknown_seconds = max(
        total_seconds
        - observed_seconds,
        0.0,
    )

    # ---------------------------------------------------------
    # Percentages
    # ---------------------------------------------------------

    coverage_percent = (
        (
            observed_seconds
            / total_seconds
        )
        * 100
        if total_seconds > 0
        else 0.0
    )

    observed_uptime_percent = (
        (
            online_seconds
            / observed_seconds
        )
        * 100
        if observed_seconds > 0
        else None
    )

    # A true 24h uptime value is only available when the
    # complete requested period has real evidence.
    data_complete = (
        coverage_percent >= 99.999
    )

    # Only expose uptime_percent as a valid "requested
    # period uptime" when the requested period is completely
    # covered by real evidence.
    #
    # Otherwise the frontend should display "--" and show
    # observed uptime + coverage separately.
    uptime_percent = (
        round(
            observed_uptime_percent,
            2,
        )
        if (
            data_complete
            and observed_uptime_percent is not None
        )
        else None
    )

    return {
        "device_id": str(
            device.iot_device_id
        ),

        "device_code": device.device_code,

        "period_hours": hours,

        # Real online time supported by heartbeat evidence.
        "online_seconds": round(
            online_seconds,
            2,
        ),

        # Real offline time after heartbeat timeout.
        "offline_seconds": round(
            offline_seconds,
            2,
        ),

        # Time for which we have actual heartbeat evidence.
        "observed_seconds": round(
            observed_seconds,
            2,
        ),

        # Time for which there is no heartbeat evidence.
        "unknown_seconds": round(
            unknown_seconds,
            2,
        ),

        "total_seconds": round(
            total_seconds,
            2,
        ),

        # Only populated when the complete requested period
        # has real evidence.
        "uptime_percent": uptime_percent,

        # Uptime calculated only over the period for which
        # real evidence exists.
        "observed_uptime_percent": (
            round(
                observed_uptime_percent,
                2,
            )
            if observed_uptime_percent is not None
            else None
        ),

        # How much of the requested period has actual
        # heartbeat evidence.
        "coverage_percent": round(
            coverage_percent,
            2,
        ),

        "data_complete": data_complete,

        "heartbeat_timeout_seconds":
            heartbeat_timeout_seconds,

        "heartbeat_count":
            len(heartbeat_times),

        "calculation":
            "Uptime is calculated only from real device "
            "heartbeat evidence. A heartbeat keeps the "
            "device online for the configured heartbeat "
            "timeout. Gaps beyond the timeout are counted "
            "as offline. Time before the first available "
            "heartbeat is unknown and is not treated as "
            "online or offline. No synthetic uptime data "
            "is generated.",
    }