-- ============================================================
-- FlowSense - Device Asset & Lifecycle Management
-- Migration: 001_device_asset_management
-- ============================================================
-- IMPORTANT:
-- This migration is non-destructive.
-- It does NOT insert synthetic device/service/network data.
-- ============================================================


-- ============================================================
-- 1. EXTEND EXISTING IoT DEVICE MASTER
-- ============================================================

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(100);

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS network_type VARCHAR(30);

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS network_identifier VARCHAR(150);

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS installation_date TIMESTAMPTZ;

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS commissioned_at TIMESTAMPTZ;

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS warranty_start_date TIMESTAMPTZ;

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS warranty_end_date TIMESTAMPTZ;

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS decommissioned_at TIMESTAMPTZ;

ALTER TABLE iot_devices
    ADD COLUMN IF NOT EXISTS decommission_reason TEXT;


-- ============================================================
-- 2. DEVICE SERVICE / REPAIR HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS device_service_history (
    service_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    iot_device_id UUID NOT NULL
        REFERENCES iot_devices(iot_device_id)
        ON DELETE CASCADE,

    service_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    service_type VARCHAR(40) NOT NULL,

    description TEXT,

    technician_name VARCHAR(120),

    service_vendor VARCHAR(120),

    repair_required BOOLEAN NOT NULL DEFAULT FALSE,

    warranty_applicable BOOLEAN,

    warranty_claim_reference VARCHAR(120),

    service_cost NUMERIC(12,2),

    next_service_date TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 3. DEVICE COMPONENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS device_components (
    component_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    iot_device_id UUID NOT NULL
        REFERENCES iot_devices(iot_device_id)
        ON DELETE CASCADE,

    component_type VARCHAR(80) NOT NULL,

    component_name VARCHAR(120) NOT NULL,

    serial_number VARCHAR(100),

    installed_at TIMESTAMPTZ,

    status VARCHAR(30) NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. COMPONENT REPLACEMENT HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS device_component_replacements (
    replacement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    component_id UUID NOT NULL
        REFERENCES device_components(component_id)
        ON DELETE CASCADE,

    service_id UUID
        REFERENCES device_service_history(service_id)
        ON DELETE SET NULL,

    old_serial_number VARCHAR(100),

    new_serial_number VARCHAR(100),

    replacement_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    replacement_reason TEXT,

    warranty_covered BOOLEAN,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 5. DEVICE NETWORK EVENTS
-- ============================================================
-- This table records actual observed network state changes.
-- It must be populated by real telemetry/heartbeat events.
-- No synthetic records are created by this migration.
-- ============================================================

CREATE TABLE IF NOT EXISTS device_network_events (
    network_event_id BIGSERIAL PRIMARY KEY,

    iot_device_id UUID NOT NULL
        REFERENCES iot_devices(iot_device_id)
        ON DELETE CASCADE,

    event_type VARCHAR(20) NOT NULL,

    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    network_type VARCHAR(30),

    network_identifier VARCHAR(150),

    source VARCHAR(40),

    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_device_network_event_type
        CHECK (event_type IN ('online', 'offline'))
);


-- ============================================================
-- 6. DEVICE OFFLINE EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS device_offline_events (
    offline_event_id BIGSERIAL PRIMARY KEY,

    iot_device_id UUID NOT NULL
        REFERENCES iot_devices(iot_device_id)
        ON DELETE CASCADE,

    offline_at TIMESTAMPTZ NOT NULL,

    recovered_at TIMESTAMPTZ,

    duration_seconds BIGINT,

    detected_reason VARCHAR(60),

    evidence TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 7. INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_device_service_history_device
    ON device_service_history(iot_device_id);

CREATE INDEX IF NOT EXISTS idx_device_service_history_date
    ON device_service_history(service_date DESC);

CREATE INDEX IF NOT EXISTS idx_device_components_device
    ON device_components(iot_device_id);

CREATE INDEX IF NOT EXISTS idx_device_component_replacements_component
    ON device_component_replacements(component_id);

CREATE INDEX IF NOT EXISTS idx_device_component_replacements_date
    ON device_component_replacements(replacement_date DESC);

CREATE INDEX IF NOT EXISTS idx_device_network_events_device_time
    ON device_network_events(iot_device_id, event_time DESC);

CREATE INDEX IF NOT EXISTS idx_device_offline_events_device_time
    ON device_offline_events(iot_device_id, offline_at DESC);


-- ============================================================
-- 8. NETWORK TYPE VALIDATION
-- ============================================================

ALTER TABLE iot_devices
    DROP CONSTRAINT IF EXISTS chk_iot_devices_network_type;

ALTER TABLE iot_devices
    ADD CONSTRAINT chk_iot_devices_network_type
    CHECK (
        network_type IS NULL
        OR network_type IN (
            'Wi-Fi',
            '4G',
            'Ethernet',
            'Mesh',
            'Other'
        )
    );


-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================