"""
ORM models for FlowSense.

These models map to the existing PostgreSQL database schema.
The database schema must be created/migrated separately.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    BigInteger,
    Boolean,
    SmallInteger,
    Text,
    JSON,
)

from sqlalchemy.dialects.postgresql import UUID

from database import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id = Column(UUID(as_uuid=True), primary_key=True)
    facility_code = Column(String(30), unique=True, nullable=False)
    facility_name = Column(String(150), nullable=False)
    facility_type = Column(String(80), nullable=False)
    city = Column(String(80))
    state = Column(String(80))
    country = Column(String(60))
    area_sq_m = Column(Numeric(12, 2))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True))


class Meter(Base):
    __tablename__ = "meters"

    meter_id = Column(UUID(as_uuid=True), primary_key=True)
    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )
    meter_code = Column(String(50), unique=True)
    meter_name = Column(String(100))
    resource_type = Column(String(20))
    unit = Column(String(20))
    meter_serial_number = Column(String(80))
    installation_date = Column(DateTime)
    status = Column(String(20), default="active")


class IotDevice(Base):
    __tablename__ = "iot_devices"

    iot_device_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
        unique=True,
    )

    device_code = Column(String(60), unique=True)
    device_name = Column(String(120))
    device_model = Column(String(80))
    firmware_version = Column(String(30))
    communication_protocol = Column(String(30))
    installation_location = Column(String(120))

    status = Column(
        String(20),
        default="online",
    )

    last_seen_at = Column(
        DateTime(timezone=True)
    )

    # --------------------------------------------------------
    # Asset / Lifecycle Management
    # --------------------------------------------------------

    serial_number = Column(
        String(100)
    )

    network_type = Column(
        String(30)
    )

    network_identifier = Column(
        String(150)
    )

    installation_date = Column(
        DateTime(timezone=True)
    )

    commissioned_at = Column(
        DateTime(timezone=True)
    )

    warranty_start_date = Column(
        DateTime(timezone=True)
    )

    warranty_end_date = Column(
        DateTime(timezone=True)
    )

    decommissioned_at = Column(
        DateTime(timezone=True)
    )

    decommission_reason = Column(
        Text
    )


class IotSensor(Base):
    __tablename__ = "iot_sensors"

    sensor_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.iot_device_id"),
    )

    sensor_code = Column(String(100))
    sensor_name = Column(String(100))
    sensor_type = Column(String(50))
    measurement = Column(String(80))
    unit = Column(String(20))
    data_type = Column(String(20))
    source_meter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meters.meter_id"),
    )
    status = Column(
        String(20),
        default="active",
    )


class EquipmentSource(Base):
    __tablename__ = "equipment_sources"

    source_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    source_code = Column(String(80))
    source_name = Column(String(120))
    source_type = Column(String(60))
    resource_type = Column(String(20))
    area_name = Column(String(120))
    criticality = Column(String(20))
    status = Column(String(20))


class MeterReading(Base):
    __tablename__ = "meter_readings"

    reading_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    meter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meters.meter_id"),
    )

    reading_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    reading_value = Column(
        Numeric(18, 6),
        nullable=False,
    )

    quality_status = Column(
        String(20),
        default="good",
    )

    source = Column(
        String(30),
        default="main_meter",
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    reading_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iot_sensors.sensor_id"),
    )

    reading_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    numeric_value = Column(
        Numeric(18, 6)
    )

    boolean_value = Column(
        Boolean
    )

    quality_status = Column(
        String(20),
        default="good",
    )

    created_at = Column(
        DateTime(timezone=True)
    )


class ConsumptionBaseline(Base):
    __tablename__ = "consumption_baselines"

    baseline_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    resource_type = Column(String(20))
    hour_of_day = Column(SmallInteger)
    day_of_week = Column(SmallInteger)

    expected_value = Column(
        Numeric(18, 3)
    )

    lower_threshold = Column(
        Numeric(18, 3)
    )

    upper_threshold = Column(
        Numeric(18, 3)
    )

    calculation_period_days = Column(
        SmallInteger
    )

    updated_at = Column(
        DateTime(timezone=True)
    )


class ResourceReconciliation(Base):
    __tablename__ = "resource_reconciliation"

    reconciliation_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    resource_type = Column(String(20))

    reconciliation_time = Column(
        DateTime(timezone=True)
    )

    main_meter_value = Column(
        Numeric(18, 3)
    )

    observed_iot_value = Column(
        Numeric(18, 3)
    )

    expected_value = Column(
        Numeric(18, 3)
    )

    unaccounted_value = Column(
        Numeric(18, 3)
    )

    unaccounted_percent = Column(
        Numeric(8, 3)
    )

    estimated_loss = Column(
        Numeric(18, 3)
    )

    loss_unit = Column(
        String(20)
    )

    status = Column(
        String(25)
    )


class Anomaly(Base):
    __tablename__ = "anomalies"

    anomaly_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.iot_device_id"),
    )

    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iot_sensors.sensor_id"),
    )

    meter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meters.meter_id"),
    )

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("equipment_sources.source_id"),
    )

    anomaly_type = Column(String(100))
    resource_type = Column(String(20))
    severity = Column(String(20))

    detected_at = Column(
        DateTime(timezone=True)
    )

    expected_value = Column(
        Numeric(18, 3)
    )

    actual_value = Column(
        Numeric(18, 3)
    )

    deviation_percent = Column(
        Numeric(8, 2)
    )

    estimated_loss = Column(
        Numeric(18, 3)
    )

    loss_unit = Column(
        String(20)
    )

    status = Column(
        String(25),
        default="open",
    )

    description = Column(
        Text
    )


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    anomaly_id = Column(
        UUID(as_uuid=True),
        ForeignKey("anomalies.anomaly_id"),
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    alert_title = Column(
        String(160)
    )

    alert_message = Column(
        Text
    )

    severity = Column(
        String(20)
    )

    triggered_at = Column(
        DateTime(timezone=True)
    )

    status = Column(
        String(20),
        default="active",
    )


class MonthlyResourceSummary(Base):
    __tablename__ = "monthly_resource_summary"

    summary_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facilities.facility_id"),
    )

    month_start = Column(
        DateTime
    )

    energy_consumption_kwh = Column(
        Numeric(18, 3)
    )

    water_consumption_kl = Column(
        Numeric(18, 3)
    )

    peak_power_kw = Column(
        Numeric(18, 3)
    )

    anomaly_count = Column(
        BigInteger
    )

    estimated_energy_loss_kwh = Column(
        Numeric(18, 3)
    )

    estimated_water_loss_kl = Column(
        Numeric(18, 3)
    )


# ============================================================
# DEVICE ASSET / LIFECYCLE MANAGEMENT
# ============================================================


class DeviceServiceHistory(Base):
    __tablename__ = "device_service_history"

    service_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "iot_devices.iot_device_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    service_date = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    service_type = Column(
        String(40),
        nullable=False,
    )

    description = Column(
        Text
    )

    technician_name = Column(
        String(120)
    )

    service_vendor = Column(
        String(120)
    )

    repair_required = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    warranty_applicable = Column(
        Boolean
    )

    warranty_claim_reference = Column(
        String(120)
    )

    service_cost = Column(
        Numeric(12, 2)
    )

    next_service_date = Column(
        DateTime(timezone=True)
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class DeviceComponent(Base):
    __tablename__ = "device_components"

    component_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "iot_devices.iot_device_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    component_type = Column(
        String(80),
        nullable=False,
    )

    component_name = Column(
        String(120),
        nullable=False,
    )

    serial_number = Column(
        String(100)
    )

    installed_at = Column(
        DateTime(timezone=True)
    )

    status = Column(
        String(30),
        nullable=False,
        default="active",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class DeviceComponentReplacement(Base):
    __tablename__ = "device_component_replacements"

    replacement_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    component_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "device_components.component_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "device_service_history.service_id",
            ondelete="SET NULL",
        ),
    )

    old_serial_number = Column(
        String(100)
    )

    new_serial_number = Column(
        String(100)
    )

    replacement_date = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    replacement_reason = Column(
        Text
    )

    warranty_covered = Column(
        Boolean
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class DeviceNetworkEvent(Base):
    __tablename__ = "device_network_events"

    network_event_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "iot_devices.iot_device_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    event_type = Column(
        String(20),
        nullable=False,
    )

    event_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    network_type = Column(
        String(30)
    )

    network_identifier = Column(
        String(150)
    )

    source = Column(
        String(40)
    )

    metadata_json = Column(
        "metadata",
        JSON,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class DeviceOfflineEvent(Base):
    __tablename__ = "device_offline_events"

    offline_event_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    iot_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "iot_devices.iot_device_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    offline_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    recovered_at = Column(
        DateTime(timezone=True)
    )

    duration_seconds = Column(
        BigInteger
    )

    detected_reason = Column(
        String(60)
    )

    evidence = Column(
        Text
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )