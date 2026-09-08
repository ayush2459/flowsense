
-- ============================================================
-- FLOWSENSE FINAL DATABASE
-- PostgreSQL 14+
--
-- Architecture:
-- Facility
--   -> 1 Main Energy Meter
--   -> 1 Main Water Meter
--   -> 1 IoT Device
--        -> multiple sensors physically integrated in the device
--             -> sensor readings
--
-- Includes:
--   * 100 facilities
--   * 2 main meters/facility
--   * 1 IoT device/facility
--   * 13 integrated sensor channels/device
--   * 365 days of hourly telemetry
--   * main-meter readings
--   * equipment/source mapping
--   * baselines
--   * reconciliation/loss calculations
--   * anomalies and alerts
--   * monthly/yearly dashboard summaries
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP VIEW IF EXISTS v_yearly_facility_summary CASCADE;
DROP VIEW IF EXISTS v_recent_anomalies CASCADE;
DROP VIEW IF EXISTS v_facility_dashboard CASCADE;
DROP VIEW IF EXISTS v_resource_reconciliation CASCADE;

DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS anomalies CASCADE;
DROP TABLE IF EXISTS resource_reconciliation CASCADE;
DROP TABLE IF EXISTS monthly_resource_summary CASCADE;
DROP TABLE IF EXISTS consumption_baselines CASCADE;
DROP TABLE IF EXISTS sensor_readings CASCADE;
DROP TABLE IF EXISTS iot_sensors CASCADE;
DROP TABLE IF EXISTS source_sensor_map CASCADE;
DROP TABLE IF EXISTS equipment_sources CASCADE;
DROP TABLE IF EXISTS iot_devices CASCADE;
DROP TABLE IF EXISTS meters CASCADE;
DROP TABLE IF EXISTS facilities CASCADE;

-- ============================================================
-- 1. FACILITIES
-- ============================================================
CREATE TABLE facilities (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_code VARCHAR(30) NOT NULL UNIQUE,
    facility_name VARCHAR(150) NOT NULL,
    facility_type VARCHAR(80) NOT NULL,
    city VARCHAR(80),
    state VARCHAR(80),
    country VARCHAR(60) DEFAULT 'India',
    area_sq_m NUMERIC(12,2),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','maintenance')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO facilities
(facility_code, facility_name, facility_type, city, state, area_sq_m)
SELECT
    'FS-FAC-' || LPAD(g::text, 3, '0'),
    CASE g % 5
        WHEN 0 THEN 'Municipal Facility '
        WHEN 1 THEN 'Commercial Facility '
        WHEN 2 THEN 'Smart School '
        WHEN 3 THEN 'Healthcare Facility '
        ELSE 'Public Service Facility '
    END || LPAD(g::text, 3, '0'),
    CASE g % 5
        WHEN 0 THEN 'Municipal'
        WHEN 1 THEN 'Commercial'
        WHEN 2 THEN 'Education'
        WHEN 3 THEN 'Healthcare'
        ELSE 'Public Service'
    END,
    CASE g % 6
        WHEN 0 THEN 'Delhi'
        WHEN 1 THEN 'Noida'
        WHEN 2 THEN 'Gurugram'
        WHEN 3 THEN 'Jaipur'
        WHEN 4 THEN 'Lucknow'
        ELSE 'Chandigarh'
    END,
    CASE g % 6
        WHEN 0 THEN 'Delhi'
        WHEN 1 THEN 'Uttar Pradesh'
        WHEN 2 THEN 'Haryana'
        WHEN 3 THEN 'Rajasthan'
        WHEN 4 THEN 'Uttar Pradesh'
        ELSE 'Chandigarh'
    END,
    4000 + (g * 173 % 30000)
FROM generate_series(1,100) g;

-- ============================================================
-- 2. MAIN METERS
-- Exactly one main energy + one main water meter per facility.
-- ============================================================
CREATE TABLE meters (
    meter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    meter_code VARCHAR(50) NOT NULL UNIQUE,
    meter_name VARCHAR(100) NOT NULL,
    resource_type VARCHAR(20) NOT NULL
        CHECK (resource_type IN ('energy','water')),
    unit VARCHAR(20) NOT NULL,
    meter_serial_number VARCHAR(80) NOT NULL UNIQUE,
    installation_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','maintenance')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_main_energy_meter
ON meters(facility_id) WHERE resource_type = 'energy';

CREATE UNIQUE INDEX uq_main_water_meter
ON meters(facility_id) WHERE resource_type = 'water';

INSERT INTO meters
(facility_id, meter_code, meter_name, resource_type, unit,
 meter_serial_number, installation_date)
SELECT
    facility_id, facility_code || '-EM', 'Main Energy Meter',
    'energy', 'kWh',
    'EM-' || LPAD(ROW_NUMBER() OVER (ORDER BY facility_code)::text,5,'0'),
    CURRENT_DATE - 400
FROM facilities;

INSERT INTO meters
(facility_id, meter_code, meter_name, resource_type, unit,
 meter_serial_number, installation_date)
SELECT
    facility_id, facility_code || '-WM', 'Main Water Meter',
    'water', 'kL',
    'WM-' || LPAD(ROW_NUMBER() OVER (ORDER BY facility_code)::text,5,'0'),
    CURRENT_DATE - 400
FROM facilities;

-- ============================================================
-- 3. ONE IOT DEVICE PER FACILITY
-- Sensors are channels/modules physically integrated into it.
-- ============================================================
CREATE TABLE iot_devices (
    iot_device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL UNIQUE REFERENCES facilities(facility_id) ON DELETE CASCADE,
    device_code VARCHAR(60) NOT NULL UNIQUE,
    device_name VARCHAR(120) NOT NULL,
    device_model VARCHAR(80) DEFAULT 'FlowSense-IoT-01',
    firmware_version VARCHAR(30) DEFAULT '1.0.0',
    communication_protocol VARCHAR(30) DEFAULT 'MQTT',
    installation_location VARCHAR(120) DEFAULT 'Main Utility Room',
    status VARCHAR(20) NOT NULL DEFAULT 'online'
        CHECK (status IN ('online','offline','maintenance')),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO iot_devices
(facility_id, device_code, device_name, last_seen_at)
SELECT
    facility_id,
    facility_code || '-IOT',
    'FlowSense IoT Device',
    NOW()
FROM facilities;

-- ============================================================
-- 4. EQUIPMENT / RESOURCE SOURCES
-- Defines where resource use can originate.
-- ============================================================
CREATE TABLE equipment_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    source_code VARCHAR(80) NOT NULL,
    source_name VARCHAR(120) NOT NULL,
    source_type VARCHAR(60) NOT NULL,
    resource_type VARCHAR(20) NOT NULL
        CHECK (resource_type IN ('energy','water','both')),
    area_name VARCHAR(120),
    criticality VARCHAR(20) DEFAULT 'medium'
        CHECK (criticality IN ('low','medium','high','critical')),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active','inactive','maintenance')),
    UNIQUE(facility_id, source_code)
);

INSERT INTO equipment_sources
(facility_id, source_code, source_name, source_type, resource_type, area_name, criticality)
SELECT facility_id, facility_code || '-HVAC', 'HVAC System', 'HVAC', 'energy', 'Zone 1', 'high'
FROM facilities;

INSERT INTO equipment_sources
(facility_id, source_code, source_name, source_type, resource_type, area_name, criticality)
SELECT facility_id, facility_code || '-PUMP', 'Water Pump System', 'Pump', 'water', 'Utility Area', 'high'
FROM facilities;

INSERT INTO equipment_sources
(facility_id, source_code, source_name, source_type, resource_type, area_name, criticality)
SELECT facility_id, facility_code || '-LIGHT', 'Lighting System', 'Lighting', 'energy', 'Common Areas', 'medium'
FROM facilities;

INSERT INTO equipment_sources
(facility_id, source_code, source_name, source_type, resource_type, area_name, criticality)
SELECT facility_id, facility_code || '-COOL', 'Cooling System', 'Cooling', 'energy', 'Zone 2', 'high'
FROM facilities;

INSERT INTO equipment_sources
(facility_id, source_code, source_name, source_type, resource_type, area_name, criticality)
SELECT facility_id, facility_code || '-PLUMB', 'Plumbing Network', 'Plumbing', 'water', 'Utility Network', 'high'
FROM facilities;

-- ============================================================
-- 5. INTEGRATED SENSOR CHANNELS
-- ============================================================
CREATE TABLE iot_sensors (
    sensor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iot_device_id UUID NOT NULL REFERENCES iot_devices(iot_device_id) ON DELETE CASCADE,
    sensor_code VARCHAR(100) NOT NULL,
    sensor_name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    measurement VARCHAR(80) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    data_type VARCHAR(20) NOT NULL
        CHECK (data_type IN ('numeric','boolean')),
    source_meter_id UUID REFERENCES meters(meter_id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active','inactive','fault')),
    UNIQUE(iot_device_id, sensor_code)
);

INSERT INTO iot_sensors
(iot_device_id, sensor_code, sensor_name, sensor_type, measurement, unit, data_type, source_meter_id)
SELECT
    d.iot_device_id,
    d.device_code || '-' || s.code,
    s.name, s.type, s.measurement, s.unit, s.data_type,
    CASE
        WHEN s.resource = 'energy' THEN em.meter_id
        WHEN s.resource = 'water' THEN wm.meter_id
        ELSE NULL
    END
FROM iot_devices d
JOIN meters em ON em.facility_id=d.facility_id AND em.resource_type='energy'
JOIN meters wm ON wm.facility_id=d.facility_id AND wm.resource_type='water'
CROSS JOIN LATERAL (
VALUES
('ENERGY','Energy Consumption Sensor','energy','Energy Consumption','kWh','numeric','energy'),
('VOLTAGE','Voltage Sensor','electrical','Voltage','V','numeric','energy'),
('CURRENT','Current Sensor','electrical','Current','A','numeric','energy'),
('POWER','Power Sensor','electrical','Power','kW','numeric','energy'),
('PF','Power Factor Sensor','electrical','Power Factor','ratio','numeric','energy'),
('WATER_FLOW','Water Flow Sensor','water','Water Flow','L/min','numeric','water'),
('WATER','Water Consumption Sensor','water','Water Consumption','kL','numeric','water'),
('PRESSURE','Water Pressure Sensor','water','Pressure','bar','numeric','water'),
('LEAK','Leak Detection Sensor','water','Leak Detected','boolean','boolean','water'),
('TEMPERATURE','Temperature Sensor','environment','Temperature','C','numeric',NULL),
('HUMIDITY','Humidity Sensor','environment','Humidity','%','numeric',NULL),
('VIBRATION','Vibration Sensor','equipment','Vibration','mm/s','numeric',NULL),
('EQUIPMENT','Equipment Status Sensor','equipment','Equipment Status','boolean','boolean',NULL)
) s(code,name,type,measurement,unit,data_type,resource);

-- ============================================================
-- 6. SENSOR -> EQUIPMENT SOURCE MAPPING
-- ============================================================
CREATE TABLE source_sensor_map (
    sensor_id UUID NOT NULL REFERENCES iot_sensors(sensor_id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES equipment_sources(source_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) DEFAULT 'monitors',
    PRIMARY KEY(sensor_id, source_id)
);

INSERT INTO source_sensor_map(sensor_id, source_id)
SELECT s.sensor_id, es.source_id
FROM iot_sensors s
JOIN iot_devices d ON d.iot_device_id=s.iot_device_id
JOIN equipment_sources es ON es.facility_id=d.facility_id
WHERE
    (s.sensor_code LIKE '%-ENERGY' AND es.source_type IN ('HVAC','Cooling'))
 OR (s.sensor_code LIKE '%-POWER' AND es.source_type IN ('HVAC','Cooling'))
 OR (s.sensor_code LIKE '%-VIBRATION' AND es.source_type='Pump')
 OR (s.sensor_code LIKE '%-WATER_FLOW' AND es.source_type IN ('Pump','Plumbing'))
 OR (s.sensor_code LIKE '%-LEAK' AND es.source_type='Plumbing')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 7. MAIN-METER READINGS
-- Main meter is the authoritative incoming resource reading.
-- ============================================================
CREATE TABLE meter_readings (
    reading_id BIGSERIAL PRIMARY KEY,
    meter_id UUID NOT NULL REFERENCES meters(meter_id) ON DELETE CASCADE,
    reading_time TIMESTAMPTZ NOT NULL,
    reading_value NUMERIC(18,6) NOT NULL,
    quality_status VARCHAR(20) DEFAULT 'good'
        CHECK (quality_status IN ('good','suspect','bad','estimated')),
    source VARCHAR(30) DEFAULT 'main_meter',
    UNIQUE(meter_id, reading_time)
);

CREATE INDEX idx_meter_readings_meter_time
ON meter_readings(meter_id, reading_time DESC);

INSERT INTO meter_readings
(meter_id, reading_time, reading_value, quality_status)
SELECT
    m.meter_id,
    ts.t,
    CASE
        WHEN m.resource_type='energy' THEN
            ROUND((
                240
                + 120 * CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 9 AND 18 THEN 1 ELSE 0.25 END
                + random()*80
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 11 AND 15
                    THEN 90 ELSE 0 END
            )::numeric,3)
        ELSE
            ROUND((
                24
                + 14 * CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 8 AND 18 THEN 1 ELSE 0.3 END
                + random()*8
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 0 AND 5
                    THEN 18 ELSE 0 END
            )::numeric,3)
    END,
    CASE WHEN random()<0.01 THEN 'suspect' ELSE 'good' END
FROM meters m
JOIN facilities f ON f.facility_id=m.facility_id
CROSS JOIN LATERAL generate_series(
    NOW()-INTERVAL '365 days',
    NOW()-INTERVAL '1 hour',
    INTERVAL '3 hours'
) ts(t);

-- ============================================================
-- 8. SENSOR READINGS
-- 13 embedded channels x 100 devices x 365 days x hourly.
-- Approx. 11.39 million rows.
-- ============================================================
CREATE TABLE sensor_readings (
    reading_id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES iot_sensors(sensor_id) ON DELETE CASCADE,
    reading_time TIMESTAMPTZ NOT NULL,
    numeric_value NUMERIC(18,6),
    boolean_value BOOLEAN,
    quality_status VARCHAR(20) DEFAULT 'good'
        CHECK (quality_status IN ('good','suspect','bad','estimated')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (
        (numeric_value IS NOT NULL AND boolean_value IS NULL)
        OR (numeric_value IS NULL AND boolean_value IS NOT NULL)
    )
);

CREATE INDEX idx_sensor_readings_sensor_time
ON sensor_readings(sensor_id, reading_time DESC);

CREATE INDEX idx_sensor_readings_time
ON sensor_readings(reading_time DESC);

INSERT INTO sensor_readings
(sensor_id, reading_time, numeric_value, boolean_value, quality_status)
SELECT
    s.sensor_id,
    ts.t,

    CASE
        WHEN s.data_type='boolean' THEN NULL

        WHEN s.sensor_code LIKE '%-ENERGY' THEN
            ROUND((
                30
                + CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 9 AND 18 THEN 25 ELSE 6 END
                + random()*10
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 11 AND 15
                    THEN 50 ELSE 0 END
            )::numeric,3)

        WHEN s.sensor_code LIKE '%-VOLTAGE' THEN
            ROUND((228+random()*8)::numeric,3)

        WHEN s.sensor_code LIKE '%-CURRENT' THEN
            ROUND((9+random()*16
                + CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 9 AND 18 THEN 10 ELSE 0 END
            )::numeric,3)

        WHEN s.sensor_code LIKE '%-POWER' THEN
            ROUND((35+random()*50
                + CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 9 AND 18 THEN 45 ELSE 0 END
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 11 AND 15
                    THEN 55 ELSE 0 END
            )::numeric,3)

        WHEN s.sensor_code LIKE '%-PF' THEN
            ROUND((0.88+random()*0.10)::numeric,3)

        WHEN s.sensor_code LIKE '%-WATER_FLOW' THEN
            ROUND((2.5+random()*4
                + CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 8 AND 18 THEN 2.5 ELSE 0 END
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 0 AND 5
                    THEN 6 ELSE 0 END
            )::numeric,3)

        WHEN s.sensor_code LIKE '%-WATER' THEN
            ROUND((2+random()*4
                + CASE WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 8 AND 18 THEN 2 ELSE 0 END
            )::numeric,3)

        WHEN s.sensor_code LIKE '%-PRESSURE' THEN
            ROUND((2.5+random()*1.2)::numeric,3)

        WHEN s.sensor_code LIKE '%-TEMPERATURE' THEN
            ROUND((22+random()*8)::numeric,3)

        WHEN s.sensor_code LIKE '%-HUMIDITY' THEN
            ROUND((45+random()*25)::numeric,3)

        WHEN s.sensor_code LIKE '%-VIBRATION' THEN
            ROUND((0.5+random()*1.8
                + CASE
                    WHEN RIGHT(f.facility_code,3)::int IN (15,45,75)
                         AND EXTRACT(HOUR FROM ts.t) BETWEEN 10 AND 16
                    THEN 3.5 ELSE 0 END
            )::numeric,3)

        ELSE NULL
    END,

    CASE
        WHEN s.data_type<>'boolean' THEN NULL
        WHEN s.sensor_code LIKE '%-LEAK' THEN
            CASE
                WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                     AND EXTRACT(HOUR FROM ts.t) BETWEEN 0 AND 5
                THEN TRUE ELSE FALSE END
        WHEN s.sensor_code LIKE '%-EQUIPMENT' THEN
            CASE
                WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 7 AND 21
                THEN TRUE ELSE FALSE END
        ELSE FALSE
    END,

    CASE WHEN random()<0.01 THEN 'suspect' ELSE 'good' END
FROM iot_sensors s
JOIN iot_devices d ON d.iot_device_id=s.iot_device_id
JOIN facilities f ON f.facility_id=d.facility_id
CROSS JOIN LATERAL generate_series(
    NOW()-INTERVAL '365 days',
    NOW()-INTERVAL '1 hour',
    INTERVAL '3 hours'
) ts(t);

-- ============================================================
-- 9. CONSUMPTION BASELINES
-- Historical expected consumption used for anomaly comparison.
-- ============================================================
CREATE TABLE consumption_baselines (
    baseline_id BIGSERIAL PRIMARY KEY,
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    resource_type VARCHAR(20) NOT NULL
        CHECK(resource_type IN ('energy','water')),
    hour_of_day SMALLINT NOT NULL CHECK(hour_of_day BETWEEN 0 AND 23),
    day_of_week SMALLINT NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    expected_value NUMERIC(18,3) NOT NULL,
    lower_threshold NUMERIC(18,3),
    upper_threshold NUMERIC(18,3),
    calculation_period_days INTEGER DEFAULT 365,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(facility_id, resource_type, hour_of_day, day_of_week)
);

INSERT INTO consumption_baselines
(facility_id, resource_type, hour_of_day, day_of_week,
 expected_value, lower_threshold, upper_threshold)
SELECT
    f.facility_id,
    r.resource_type,
    h.hour_of_day,
    dow.day_of_week,
    CASE
        WHEN r.resource_type='energy'
             AND h.hour_of_day BETWEEN 9 AND 18 THEN 380
        WHEN r.resource_type='energy' THEN 275
        WHEN r.resource_type='water'
             AND h.hour_of_day BETWEEN 8 AND 18 THEN 36
        ELSE 28
    END,
    CASE
        WHEN r.resource_type='energy'
             AND h.hour_of_day BETWEEN 9 AND 18 THEN 300
        WHEN r.resource_type='energy' THEN 200
        WHEN r.resource_type='water'
             AND h.hour_of_day BETWEEN 8 AND 18 THEN 25
        ELSE 15
    END,
    CASE
        WHEN r.resource_type='energy'
             AND h.hour_of_day BETWEEN 9 AND 18 THEN 480
        WHEN r.resource_type='energy' THEN 360
        WHEN r.resource_type='water'
             AND h.hour_of_day BETWEEN 8 AND 18 THEN 50
        ELSE 42
    END
FROM facilities f
CROSS JOIN (VALUES ('energy'),('water')) r(resource_type)
CROSS JOIN generate_series(0,23) h(hour_of_day)
CROSS JOIN generate_series(0,6) dow(day_of_week);

-- ============================================================
-- 10. RESOURCE RECONCILIATION / LOSS CALCULATION
-- Compares authoritative main meter against IoT-observed usage.
-- The observed value is a modeled aggregation of IoT source use.
-- ============================================================
CREATE TABLE resource_reconciliation (
    reconciliation_id BIGSERIAL PRIMARY KEY,
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    resource_type VARCHAR(20) NOT NULL
        CHECK(resource_type IN ('energy','water')),
    reconciliation_time TIMESTAMPTZ NOT NULL,
    main_meter_value NUMERIC(18,3) NOT NULL,
    observed_iot_value NUMERIC(18,3) NOT NULL,
    expected_value NUMERIC(18,3),
    unaccounted_value NUMERIC(18,3) NOT NULL,
    unaccounted_percent NUMERIC(8,3),
    estimated_loss NUMERIC(18,3) NOT NULL,
    loss_unit VARCHAR(20) NOT NULL,
    status VARCHAR(25) NOT NULL DEFAULT 'normal'
        CHECK(status IN ('normal','watch','loss_suspected','confirmed_loss')),
    UNIQUE(facility_id, resource_type, reconciliation_time)
);

CREATE INDEX idx_reconciliation_facility_time
ON resource_reconciliation(facility_id, reconciliation_time DESC);

-- Use the main-meter reading and a realistic modeled IoT-observed
-- share. Selected facilities intentionally have larger gaps.
INSERT INTO resource_reconciliation
(facility_id, resource_type, reconciliation_time,
 main_meter_value, observed_iot_value, expected_value,
 unaccounted_value, unaccounted_percent, estimated_loss,
 loss_unit, status)
SELECT
    f.facility_id,
    m.resource_type,
    mr.reading_time,
    mr.reading_value,
    ROUND((
        mr.reading_value *
        CASE
            WHEN m.resource_type='energy' THEN
                CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                     THEN 0.72 ELSE 0.90 + random()*0.04 END
            ELSE
                CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                     THEN 0.68 ELSE 0.88 + random()*0.05 END
        END
    )::numeric,3),
    CASE
        WHEN m.resource_type='energy' THEN
            CASE WHEN EXTRACT(HOUR FROM mr.reading_time) BETWEEN 9 AND 18
                 THEN 360 ELSE 260 END
        ELSE
            CASE WHEN EXTRACT(HOUR FROM mr.reading_time) BETWEEN 8 AND 18
                 THEN 35 ELSE 25 END
    END,
    ROUND((
        mr.reading_value -
        mr.reading_value *
        CASE
            WHEN m.resource_type='energy' THEN
                CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                     THEN 0.72 ELSE 0.90 + random()*0.04 END
            ELSE
                CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                     THEN 0.68 ELSE 0.88 + random()*0.05 END
        END
    )::numeric,3),
    ROUND((
        100 * (
        1 -
        CASE
            WHEN m.resource_type='energy' THEN
                CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                     THEN 0.72 ELSE 0.90 + random()*0.04 END
            ELSE
                CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                     THEN 0.68 ELSE 0.88 + random()*0.05 END
        END)
    )::numeric,3),
    ROUND((
        mr.reading_value -
        mr.reading_value *
        CASE
            WHEN m.resource_type='energy' THEN
                CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                     THEN 0.72 ELSE 0.90 + random()*0.04 END
            ELSE
                CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                     THEN 0.68 ELSE 0.88 + random()*0.05 END
        END
    )::numeric,3),
    CASE WHEN m.resource_type='energy' THEN 'kWh' ELSE 'kL' END,
    CASE
        WHEN (
            100 * (1 -
            CASE
                WHEN m.resource_type='energy' THEN
                    CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                         THEN 0.72 ELSE 0.90 + random()*0.04 END
                ELSE
                    CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                         THEN 0.68 ELSE 0.88 + random()*0.05 END
            END)
        ) >= 20 THEN 'confirmed_loss'
        WHEN (
            100 * (1 -
            CASE
                WHEN m.resource_type='energy' THEN
                    CASE WHEN RIGHT(f.facility_code,3)::int IN (7,23,48,71,92)
                         THEN 0.72 ELSE 0.90 + random()*0.04 END
                ELSE
                    CASE WHEN RIGHT(f.facility_code,3)::int IN (10,30,50,70,90)
                         THEN 0.68 ELSE 0.88 + random()*0.05 END
            END)
        ) >= 10 THEN 'loss_suspected'
        ELSE 'normal'
    END
FROM meter_readings mr
JOIN meters m ON m.meter_id=mr.meter_id
JOIN facilities f ON f.facility_id=m.facility_id;

-- ============================================================
-- 11. ANOMALIES
-- ============================================================
CREATE TABLE anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    iot_device_id UUID REFERENCES iot_devices(iot_device_id) ON DELETE SET NULL,
    sensor_id UUID REFERENCES iot_sensors(sensor_id) ON DELETE SET NULL,
    meter_id UUID REFERENCES meters(meter_id) ON DELETE SET NULL,
    source_id UUID REFERENCES equipment_sources(source_id) ON DELETE SET NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    resource_type VARCHAR(20),
    severity VARCHAR(20) NOT NULL
        CHECK(severity IN ('low','medium','high','critical')),
    detected_at TIMESTAMPTZ NOT NULL,
    expected_value NUMERIC(18,3),
    actual_value NUMERIC(18,3),
    deviation_percent NUMERIC(8,2),
    estimated_loss NUMERIC(18,3),
    loss_unit VARCHAR(20),
    status VARCHAR(25) NOT NULL DEFAULT 'open'
        CHECK(status IN ('open','acknowledged','investigating','resolved','false_positive')),
    description TEXT
);

-- Energy anomaly cases
INSERT INTO anomalies
(facility_id, iot_device_id, sensor_id, meter_id, source_id,
 anomaly_type, resource_type, severity, detected_at,
 expected_value, actual_value, deviation_percent,
 estimated_loss, loss_unit, status, description)
SELECT
    f.facility_id, d.iot_device_id, s.sensor_id, m.meter_id, es.source_id,
    'Abnormal Energy Consumption', 'energy',
    CASE WHEN n%5=0 THEN 'critical' WHEN n%2=0 THEN 'high' ELSE 'medium' END,
    NOW()-(n||' hours')::interval,
    100, 100+n*3.2, 35+n*0.9,
    8+n*0.4, 'kWh',
    CASE WHEN n%4=0 THEN 'resolved'
         WHEN n%3=0 THEN 'investigating' ELSE 'open' END,
    'IoT energy sensors detected usage above the historical baseline; source mapping indicates equipment requiring inspection.'
FROM generate_series(1,20) n
JOIN facilities f ON f.facility_code='FS-FAC-'||LPAD((n*5)::text,3,'0')
JOIN iot_devices d ON d.facility_id=f.facility_id
JOIN iot_sensors s ON s.iot_device_id=d.iot_device_id AND s.sensor_code LIKE '%-ENERGY'
JOIN meters m ON m.facility_id=f.facility_id AND m.resource_type='energy'
JOIN equipment_sources es ON es.facility_id=f.facility_id AND es.source_type='HVAC';

-- Water leak cases
INSERT INTO anomalies
(facility_id, iot_device_id, sensor_id, meter_id, source_id,
 anomaly_type, resource_type, severity, detected_at,
 expected_value, actual_value, deviation_percent,
 estimated_loss, loss_unit, status, description)
SELECT
    f.facility_id, d.iot_device_id, s.sensor_id, m.meter_id, es.source_id,
    'Possible Water Leakage', 'water', 'high',
    NOW()-INTERVAL '3 hours',
    3.2, 8.4, 162.5, 18.7, 'kL', 'open',
    'Leak sensor and water-flow sensor indicate unexpected flow during a low-demand period.'
FROM facilities f
JOIN iot_devices d ON d.facility_id=f.facility_id
JOIN iot_sensors s ON s.iot_device_id=d.iot_device_id AND s.sensor_code LIKE '%-LEAK'
JOIN meters m ON m.facility_id=f.facility_id AND m.resource_type='water'
JOIN equipment_sources es ON es.facility_id=f.facility_id AND es.source_type='Plumbing'
WHERE RIGHT(f.facility_code,3)::int IN (10,30,50,70,90);

-- Vibration cases
INSERT INTO anomalies
(facility_id, iot_device_id, sensor_id, source_id,
 anomaly_type, severity, detected_at,
 expected_value, actual_value, deviation_percent,
 status, description)
SELECT
    f.facility_id, d.iot_device_id, s.sensor_id, es.source_id,
    'Abnormal Equipment Vibration', 'medium', NOW()-INTERVAL '2 hours',
    2.0, 5.7, 185.0, 'acknowledged',
    'Embedded vibration sensor detected abnormal vibration associated with the water pump.'
FROM facilities f
JOIN iot_devices d ON d.facility_id=f.facility_id
JOIN iot_sensors s ON s.iot_device_id=d.iot_device_id AND s.sensor_code LIKE '%-VIBRATION'
JOIN equipment_sources es ON es.facility_id=f.facility_id AND es.source_type='Pump'
WHERE RIGHT(f.facility_code,3)::int IN (15,45,75);

-- ============================================================
-- 12. ALERTS
-- ============================================================
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id UUID NOT NULL REFERENCES anomalies(anomaly_id) ON DELETE CASCADE,
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    alert_title VARCHAR(160) NOT NULL,
    alert_message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK(status IN ('active','acknowledged','resolved','dismissed'))
);

INSERT INTO alerts
(anomaly_id, facility_id, alert_title, alert_message, severity, triggered_at, status)
SELECT
    anomaly_id, facility_id,
    CASE anomaly_type
        WHEN 'Possible Water Leakage' THEN 'Potential Water Leakage Detected'
        WHEN 'Abnormal Energy Consumption' THEN 'Abnormal Energy Consumption Detected'
        ELSE 'Equipment Condition Alert'
    END,
    description, severity, detected_at,
    CASE WHEN status='resolved' THEN 'resolved'
         WHEN status='acknowledged' THEN 'acknowledged'
         ELSE 'active' END
FROM anomalies;

-- ============================================================
-- 13. MONTHLY SUMMARY
-- ============================================================
CREATE TABLE monthly_resource_summary (
    summary_id BIGSERIAL PRIMARY KEY,
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    month_start DATE NOT NULL,
    energy_consumption_kwh NUMERIC(18,3) DEFAULT 0,
    water_consumption_kl NUMERIC(18,3) DEFAULT 0,
    peak_power_kw NUMERIC(18,3),
    anomaly_count INTEGER DEFAULT 0,
    estimated_energy_loss_kwh NUMERIC(18,3) DEFAULT 0,
    estimated_water_loss_kl NUMERIC(18,3) DEFAULT 0,
    UNIQUE(facility_id, month_start)
);

INSERT INTO monthly_resource_summary
(facility_id, month_start, energy_consumption_kwh, water_consumption_kl,
 peak_power_kw, anomaly_count, estimated_energy_loss_kwh, estimated_water_loss_kl)
SELECT
    f.facility_id,
    DATE_TRUNC('month', r.reconciliation_time)::date,
    SUM(CASE WHEN r.resource_type='energy' THEN r.main_meter_value ELSE 0 END),
    SUM(CASE WHEN r.resource_type='water' THEN r.main_meter_value ELSE 0 END),
    MAX(CASE WHEN r.resource_type='energy' THEN r.main_meter_value/4 ELSE NULL END),
    COUNT(DISTINCT a.anomaly_id),
    SUM(CASE WHEN r.resource_type='energy' THEN r.estimated_loss ELSE 0 END),
    SUM(CASE WHEN r.resource_type='water' THEN r.estimated_loss ELSE 0 END)
FROM facilities f
JOIN resource_reconciliation r ON r.facility_id=f.facility_id
LEFT JOIN anomalies a
    ON a.facility_id=f.facility_id
   AND DATE_TRUNC('month',a.detected_at)::date=DATE_TRUNC('month',r.reconciliation_time)::date
GROUP BY f.facility_id, DATE_TRUNC('month',r.reconciliation_time)::date;

-- ============================================================
-- 14. DASHBOARD VIEWS
-- ============================================================
CREATE VIEW v_resource_reconciliation AS
SELECT
    f.facility_code,
    f.facility_name,
    f.city,
    r.resource_type,
    r.reconciliation_time,
    r.main_meter_value,
    r.observed_iot_value,
    r.expected_value,
    r.unaccounted_value,
    r.unaccounted_percent,
    r.estimated_loss,
    r.loss_unit,
    r.status
FROM resource_reconciliation r
JOIN facilities f ON f.facility_id=r.facility_id;

CREATE VIEW v_facility_dashboard AS
SELECT
    f.facility_code,
    f.facility_name,
    f.city,
    d.device_code AS iot_device,
    MAX(CASE WHEN s.sensor_code LIKE '%-ENERGY' THEN sr.numeric_value END) AS energy_kwh,
    MAX(CASE WHEN s.sensor_code LIKE '%-POWER' THEN sr.numeric_value END) AS power_kw,
    MAX(CASE WHEN s.sensor_code LIKE '%-VOLTAGE' THEN sr.numeric_value END) AS voltage_v,
    MAX(CASE WHEN s.sensor_code LIKE '%-CURRENT' THEN sr.numeric_value END) AS current_a,
    MAX(CASE WHEN s.sensor_code LIKE '%-WATER' THEN sr.numeric_value END) AS water_kl,
    MAX(CASE WHEN s.sensor_code LIKE '%-WATER_FLOW' THEN sr.numeric_value END) AS water_flow_lpm,
    MAX(CASE WHEN s.sensor_code LIKE '%-PRESSURE' THEN sr.numeric_value END) AS water_pressure_bar,
    MAX(CASE WHEN s.sensor_code LIKE '%-LEAK' THEN
        CASE WHEN sr.boolean_value THEN 1 ELSE 0 END END) AS leak_detected,
    MAX(CASE WHEN s.sensor_code LIKE '%-TEMPERATURE' THEN sr.numeric_value END) AS temperature_c,
    MAX(CASE WHEN s.sensor_code LIKE '%-HUMIDITY' THEN sr.numeric_value END) AS humidity_percent,
    MAX(CASE WHEN s.sensor_code LIKE '%-VIBRATION' THEN sr.numeric_value END) AS vibration_mm_s,
    MAX(sr.reading_time) AS latest_reading_time
FROM facilities f
JOIN iot_devices d ON d.facility_id=f.facility_id
JOIN iot_sensors s ON s.iot_device_id=d.iot_device_id
JOIN sensor_readings sr ON sr.sensor_id=s.sensor_id
WHERE sr.reading_time>=NOW()-INTERVAL '2 hours'
GROUP BY f.facility_code,f.facility_name,f.city,d.device_code;

CREATE VIEW v_recent_anomalies AS
SELECT
    a.anomaly_id,
    f.facility_code,
    f.facility_name,
    d.device_code AS iot_device,
    s.sensor_name,
    es.source_name,
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
JOIN facilities f ON f.facility_id=a.facility_id
LEFT JOIN iot_devices d ON d.iot_device_id=a.iot_device_id
LEFT JOIN iot_sensors s ON s.sensor_id=a.sensor_id
LEFT JOIN equipment_sources es ON es.source_id=a.source_id;

CREATE VIEW v_yearly_facility_summary AS
SELECT
    f.facility_code,
    f.facility_name,
    f.city,
    ROUND(SUM(m.energy_consumption_kwh),2) AS annual_energy_kwh,
    ROUND(SUM(m.water_consumption_kl),2) AS annual_water_kl,
    SUM(m.anomaly_count) AS anomaly_count,
    ROUND(SUM(m.estimated_energy_loss_kwh),2) AS estimated_energy_loss_kwh,
    ROUND(SUM(m.estimated_water_loss_kl),2) AS estimated_water_loss_kl
FROM facilities f
JOIN monthly_resource_summary m ON m.facility_id=f.facility_id
GROUP BY f.facility_code,f.facility_name,f.city;

-- ============================================================
-- 15. VERIFICATION QUERIES
-- ============================================================
-- SELECT COUNT(*) FROM facilities;                         -- 100
-- SELECT resource_type, COUNT(*) FROM meters GROUP BY resource_type;
-- SELECT COUNT(*) FROM iot_devices;                       -- 100
-- SELECT COUNT(*) FROM iot_sensors;                       -- 1300
-- SELECT MIN(reading_time), MAX(reading_time), COUNT(*) FROM sensor_readings;
-- SELECT MIN(reading_time), MAX(reading_time), COUNT(*) FROM meter_readings;
-- SELECT COUNT(*) FROM consumption_baselines;              -- 33600
-- SELECT COUNT(*) FROM resource_reconciliation;
-- SELECT COUNT(*) FROM anomalies;
-- SELECT COUNT(*) FROM alerts;
-- SELECT * FROM v_facility_dashboard;
-- SELECT * FROM v_recent_anomalies ORDER BY detected_at DESC;
-- SELECT * FROM v_yearly_facility_summary ORDER BY annual_energy_kwh DESC;

-- ============================================================
-- END FLOWSENSE FINAL DATABASE
-- ============================================================
