from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import IotDevice, DeviceServiceHistory


router = APIRouter(
    prefix="/api/maintenance",
    tags=["Maintenance"],
)


def utc_now():
    return datetime.now(timezone.utc)


def service_to_dict(service, device):
    return {
        "service_id": str(service.service_id),
        "device_id": str(device.iot_device_id),
        "device_code": device.device_code,
        "device_name": device.device_name,
        "facility_id": (
            str(device.facility_id)
            if device.facility_id
            else None
        ),
        "service_date": service.service_date,
        "service_type": service.service_type,
        "description": service.description,
        "technician_name": service.technician_name,
        "service_vendor": service.service_vendor,
        "repair_required": service.repair_required,
        "warranty_applicable": service.warranty_applicable,
        "warranty_claim_reference": (
            service.warranty_claim_reference
        ),
        "service_cost": (
            float(service.service_cost)
            if service.service_cost is not None
            else None
        ),
        "next_service_date": service.next_service_date,
    }


# ============================================================
# MAINTENANCE SUMMARY
# ============================================================

@router.get("/summary")
def maintenance_summary(
    db: Session = Depends(get_db),
):
    now = utc_now()

    total_services = (
        db.query(
            func.count(DeviceServiceHistory.service_id)
        )
        .scalar()
        or 0
    )

    upcoming = (
        db.query(
            func.count(DeviceServiceHistory.service_id)
        )
        .filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date >= now,
        )
        .scalar()
        or 0
    )

    overdue = (
        db.query(
            func.count(DeviceServiceHistory.service_id)
        )
        .filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date < now,
        )
        .scalar()
        or 0
    )

    repairs = (
        db.query(
            func.count(DeviceServiceHistory.service_id)
        )
        .filter(
            DeviceServiceHistory.repair_required.is_(True)
        )
        .scalar()
        or 0
    )

    warranty = (
        db.query(
            func.count(DeviceServiceHistory.service_id)
        )
        .filter(
            DeviceServiceHistory.warranty_applicable.is_(True)
        )
        .scalar()
        or 0
    )

    total_cost = (
        db.query(
            func.coalesce(
                func.sum(DeviceServiceHistory.service_cost),
                0,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_services": total_services,
        "upcoming": upcoming,
        "overdue": overdue,
        "repairs_required": repairs,
        "warranty_services": warranty,
        "total_service_cost": float(total_cost),
        "checked_at": now,
    }


# ============================================================
# MAINTENANCE RECORDS
# ============================================================

@router.get("/records")
def maintenance_records(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    service_type: str | None = Query(default=None),
):
    now = utc_now()

    query = (
        db.query(
            DeviceServiceHistory,
            IotDevice,
        )
        .join(
            IotDevice,
            IotDevice.iot_device_id
            == DeviceServiceHistory.iot_device_id,
        )
    )

    # Search by device, technician, vendor, or description
    if search:
        pattern = f"%{search}%"

        query = query.filter(
            or_(
                IotDevice.device_code.ilike(pattern),
                IotDevice.device_name.ilike(pattern),
                DeviceServiceHistory.technician_name.ilike(
                    pattern
                ),
                DeviceServiceHistory.service_vendor.ilike(
                    pattern
                ),
                DeviceServiceHistory.description.ilike(
                    pattern
                ),
            )
        )

    # Filter by service type
    if service_type:
        query = query.filter(
            DeviceServiceHistory.service_type == service_type
        )

    # Filter by maintenance status
    if status == "upcoming":
        query = query.filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date >= now,
        )

    elif status == "overdue":
        query = query.filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date < now,
        )

    elif status == "repair":
        query = query.filter(
            DeviceServiceHistory.repair_required.is_(True)
        )

    rows = (
        query
        .order_by(
            DeviceServiceHistory.service_date.desc()
        )
        .all()
    )

    return {
        "count": len(rows),
        "records": [
            service_to_dict(service, device)
            for service, device in rows
        ],
    }


# ============================================================
# UPCOMING MAINTENANCE
# ============================================================

@router.get("/upcoming")
def upcoming_maintenance(
    db: Session = Depends(get_db),
):
    now = utc_now()

    rows = (
        db.query(
            DeviceServiceHistory,
            IotDevice,
        )
        .join(
            IotDevice,
            IotDevice.iot_device_id
            == DeviceServiceHistory.iot_device_id,
        )
        .filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date >= now,
        )
        .order_by(
            DeviceServiceHistory.next_service_date.asc()
        )
        .all()
    )

    return {
        "count": len(rows),
        "records": [
            service_to_dict(service, device)
            for service, device in rows
        ],
    }


# ============================================================
# OVERDUE MAINTENANCE
# ============================================================

@router.get("/overdue")
def overdue_maintenance(
    db: Session = Depends(get_db),
):
    now = utc_now()

    rows = (
        db.query(
            DeviceServiceHistory,
            IotDevice,
        )
        .join(
            IotDevice,
            IotDevice.iot_device_id
            == DeviceServiceHistory.iot_device_id,
        )
        .filter(
            DeviceServiceHistory.next_service_date.isnot(None),
            DeviceServiceHistory.next_service_date < now,
        )
        .order_by(
            DeviceServiceHistory.next_service_date.asc()
        )
        .all()
    )

    return {
        "count": len(rows),
        "records": [
            service_to_dict(service, device)
            for service, device in rows
        ],
    }


# ============================================================
# CREATE MAINTENANCE RECORD
# ============================================================

@router.post("/records")
def create_maintenance_record(
    payload: dict,
    db: Session = Depends(get_db),
):
    device_id = payload.get("device_id")

    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="device_id is required",
        )

    device = (
        db.query(IotDevice)
        .filter(
            IotDevice.iot_device_id == device_id
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    service = DeviceServiceHistory(
        iot_device_id=device.iot_device_id,

        service_date=(
            payload.get("service_date")
            or utc_now()
        ),

        service_type=payload.get(
            "service_type",
            "maintenance",
        ),

        description=payload.get(
            "description"
        ),

        technician_name=payload.get(
            "technician_name"
        ),

        service_vendor=payload.get(
            "service_vendor"
        ),

        repair_required=bool(
            payload.get(
                "repair_required",
                False,
            )
        ),

        warranty_applicable=payload.get(
            "warranty_applicable"
        ),

        warranty_claim_reference=payload.get(
            "warranty_claim_reference"
        ),

        service_cost=payload.get(
            "service_cost"
        ),

        next_service_date=payload.get(
            "next_service_date"
        ),
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return {
        "status": "created",
        "record": service_to_dict(
            service,
            device,
        ),
    }