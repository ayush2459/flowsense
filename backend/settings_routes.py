import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import get_current_user, get_db
from auth_models import User


router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _require_admin(user: User) -> None:
    role = getattr(user, "role", None) or "admin"
    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Administrator access required")


def _json(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _ensure_settings(db: Session, user: User) -> None:
    db.execute(
        text(
            """
            INSERT INTO flowsense_settings (id, updated_by)
            VALUES (1, :user_id)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"user_id": user.user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO user_settings (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO NOTHING
            """
        ),
        {"user_id": user.user_id},
    )
    db.commit()


def _read_settings(db: Session, user: User) -> dict:
    _ensure_settings(db, user)

    org = db.execute(
        text(
            """
            SELECT
                organization_name, organization_code,
                timezone, locale, currency, date_format, theme,
                contact_email, contact_phone,
                monitoring, notifications, integrations,
                system, security, updated_at
            FROM flowsense_settings
            WHERE id = 1
            """
        )
    ).mappings().one()

    profile = db.execute(
        text(
            """
            SELECT
                user_id, name, email, auth_provider, profile_image,
                is_active, COALESCE(role, 'admin') AS role,
                phone, job_title, department, created_at
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user.user_id},
    ).mappings().one()

    prefs = db.execute(
        text(
            """
            SELECT theme, timezone, locale, preferences, notifications
            FROM user_settings
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user.user_id},
    ).mappings().one()

    return {
        "organization": {
            "name": org["organization_name"],
            "code": org["organization_code"],
            "contact_email": org["contact_email"] or "",
            "contact_phone": org["contact_phone"] or "",
        },
        "preferences": {
            "timezone": prefs["timezone"] or org["timezone"],
            "locale": prefs["locale"] or org["locale"],
            "currency": org["currency"],
            "date_format": org["date_format"],
            "theme": prefs["theme"] or org["theme"],
        },
        "monitoring": _json(org["monitoring"]),
        "notifications": {
            **_json(org["notifications"]),
            **_json(prefs["notifications"]),
        },
        "integrations": _json(org["integrations"]),
        "system": _json(org["system"]),
        "security": _json(org["security"]),
        "profile": {
            "user_id": str(profile["user_id"]),
            "name": profile["name"],
            "email": profile["email"],
            "auth_provider": profile["auth_provider"],
            "profile_image": profile["profile_image"],
            "is_active": profile["is_active"],
            "role": profile["role"],
            "phone": profile["phone"],
            "job_title": profile["job_title"],
            "department": profile["department"],
            "created_at": profile["created_at"],
        },
        "updated_at": org["updated_at"],
    }


class SettingsUpdate(BaseModel):
    organization: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    monitoring: dict[str, Any] | None = None
    notifications: dict[str, Any] | None = None
    integrations: dict[str, Any] | None = None
    system: dict[str, Any] | None = None
    security: dict[str, Any] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    profile_image: str | None = Field(default=None, max_length=500)


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    department: str | None = Field(default=None, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)


@router.get("")
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _read_settings(db, current_user)


@router.put("")
def update_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_settings(db, current_user)
    data = payload.model_dump(exclude_none=True)

    org = data.get("organization")
    if org:
        mapping = {
            "name": "organization_name",
            "code": "organization_code",
            "contact_email": "contact_email",
            "contact_phone": "contact_phone",
        }
        values = {
            column: org[key]
            for key, column in mapping.items()
            if key in org
        }
        if values:
            sets = ", ".join(f"{key} = :{key}" for key in values)
            db.execute(
                text(
                    f"""
                    UPDATE flowsense_settings
                    SET {sets}, updated_at = NOW(), updated_by = :updated_by
                    WHERE id = 1
                    """
                ),
                {**values, "updated_by": current_user.user_id},
            )

    prefs = data.get("preferences")
    if prefs:
        db.execute(
            text(
                """
                UPDATE flowsense_settings
                SET
                    timezone = COALESCE(:timezone, timezone),
                    locale = COALESCE(:locale, locale),
                    currency = COALESCE(:currency, currency),
                    date_format = COALESCE(:date_format, date_format),
                    theme = COALESCE(:theme, theme),
                    updated_at = NOW(),
                    updated_by = :updated_by
                WHERE id = 1
                """
            ),
            {
                "timezone": prefs.get("timezone"),
                "locale": prefs.get("locale"),
                "currency": prefs.get("currency"),
                "date_format": prefs.get("date_format"),
                "theme": prefs.get("theme"),
                "updated_by": current_user.user_id,
            },
        )
        db.execute(
            text(
                """
                UPDATE user_settings
                SET
                    theme = COALESCE(:theme, theme),
                    timezone = COALESCE(:timezone, timezone),
                    locale = COALESCE(:locale, locale),
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            {
                "theme": prefs.get("theme"),
                "timezone": prefs.get("timezone"),
                "locale": prefs.get("locale"),
                "user_id": current_user.user_id,
            },
        )

    for column in (
        "monitoring",
        "notifications",
        "integrations",
        "system",
        "security",
    ):
        value = data.get(column)
        if value is not None:
            db.execute(
                text(
                    f"""
                    UPDATE flowsense_settings
                    SET {column} = CAST(:value AS jsonb),
                        updated_at = NOW(),
                        updated_by = :updated_by
                    WHERE id = 1
                    """
                ),
                {
                    "value": json.dumps(value),
                    "updated_by": current_user.user_id,
                },
            )

    if data.get("notifications") is not None:
        db.execute(
            text(
                """
                UPDATE user_settings
                SET notifications = CAST(:value AS jsonb),
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            {
                "value": json.dumps(data["notifications"]),
                "user_id": current_user.user_id,
            },
        )

    db.commit()
    return _read_settings(db, current_user)


@router.put("/profile")
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(exclude_unset=True)
    if values:
        sets = ", ".join(f"{key} = :{key}" for key in values)
        db.execute(
            text(
                f"""
                UPDATE users
                SET {sets}
                WHERE user_id = :user_id
                """
            ),
            {**values, "user_id": current_user.user_id},
        )
        db.commit()
        db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "user": {
            "user_id": str(current_user.user_id),
            "name": current_user.name,
            "email": current_user.email,
            "auth_provider": current_user.auth_provider,
            "profile_image": current_user.profile_image,
        },
    }


@router.put("/password")
def update_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    from auth import hash_password, verify_password

    if not current_user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="This account does not have a local password. Use Google authentication.",
        )

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)

    rows = db.execute(
        text(
            """
            SELECT
                user_id, name, email, auth_provider, profile_image,
                is_active, COALESCE(role, 'admin') AS role,
                phone, job_title, department, created_at
            FROM users
            ORDER BY created_at ASC
            """
        )
    ).mappings().all()

    return {
        "count": len(rows),
        "users": [
            {**dict(row), "user_id": str(row["user_id"])}
            for row in rows
        ],
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)

    values = payload.model_dump(exclude_unset=True)
    if values.get("role") not in {None, "admin", "manager", "viewer", "technician"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    if not values:
        return {"message": "No changes requested"}

    sets = ", ".join(f"{key} = :{key}" for key in values)
    result = db.execute(
        text(
            f"""
            UPDATE users
            SET {sets}
            WHERE user_id = :user_id
            """
        ),
        {**values, "user_id": user_id},
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")

    db.commit()
    return {"message": "User updated successfully"}


@router.get("/system-status")
def system_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    checks = {"database": "offline"}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "online"
    except Exception:
        pass

    try:
        device_count = db.execute(text("SELECT COUNT(*) FROM iot_devices")).scalar() or 0
        facility_count = db.execute(text("SELECT COUNT(*) FROM facilities")).scalar() or 0
    except Exception:
        device_count = 0
        facility_count = 0

    return {
        "api": "online",
        "database": checks["database"],
        "device_count": int(device_count),
        "facility_count": int(facility_count),
        "server_time": datetime.now(timezone.utc),
    }
