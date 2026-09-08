"""
FlowSense live feed simulator.

Your database already has 365 days of hourly history ending ~1 hour
before "now" (that's how it was seeded). This script keeps appending
fresh meter_readings + sensor_readings rows every interval, so a live
dashboard has something new to show while you're testing.

Usage:
    python live_feed.py --facility FS-FAC-001 --interval 10

Requires DATABASE_URL in a .env file (same one the backend uses).
"""
import argparse
import os
import random
import time
import uuid
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("Set DATABASE_URL in a .env file first.")
    return psycopg2.connect(DATABASE_URL)


def push_reading(conn, facility_code: str, inject_anomaly: bool):
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        # look up facility's meters and sensors once per call (fine for prototype rate)
        cur.execute("SELECT facility_id FROM facilities WHERE facility_code = %s", (facility_code,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Facility {facility_code} not found")
        facility_id = row[0]

        cur.execute("SELECT meter_id, resource_type FROM meters WHERE facility_id = %s", (facility_id,))
        meters = cur.fetchall()

        for meter_id, resource_type in meters:
            base = 300 if resource_type == "energy" else 30
            value = base + random.uniform(-20, 20)
            if inject_anomaly:
                value *= 2.5 if resource_type == "energy" else 3.0
            cur.execute("""
                INSERT INTO meter_readings (meter_id, reading_time, reading_value, quality_status)
                VALUES (%s, %s, %s, 'good')
                ON CONFLICT (meter_id, reading_time) DO NOTHING
            """, (meter_id, now, round(value, 3)))

        cur.execute("""
            SELECT sensor_id, sensor_code, data_type FROM iot_sensors
            WHERE iot_device_id = (SELECT iot_device_id FROM iot_devices WHERE facility_id = %s)
        """, (facility_id,))
        sensors = cur.fetchall()

        for sensor_id, sensor_code, data_type in sensors:
            if data_type == "boolean":
                cur.execute("""
                    INSERT INTO sensor_readings (sensor_id, reading_time, boolean_value, quality_status)
                    VALUES (%s, %s, %s, 'good')
                """, (sensor_id, now, random.random() < (0.3 if inject_anomaly else 0.02)))
            else:
                val = random.uniform(20, 60)
                if inject_anomaly and ("ENERGY" in sensor_code or "WATER_FLOW" in sensor_code):
                    val *= 2.5
                cur.execute("""
                    INSERT INTO sensor_readings (sensor_id, reading_time, numeric_value, quality_status)
                    VALUES (%s, %s, %s, 'good')
                """, (sensor_id, now, round(val, 3)))

        cur.execute("""
            UPDATE iot_devices SET last_seen_at = %s, status = 'online'
            WHERE facility_id = %s
        """, (now, facility_id))

    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--facility", default="FS-FAC-001")
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--anomaly-rate", type=float, default=0.15)
    parser.add_argument("--count", type=int, default=0, help="0 = run forever")
    args = parser.parse_args()

    conn = get_conn()
    sent = 0
    print(f"Feeding live data for {args.facility} every {args.interval}s. Ctrl+C to stop.")
    try:
        while args.count == 0 or sent < args.count:
            inject = random.random() < args.anomaly_rate
            push_reading(conn, args.facility, inject)
            print(f"[{datetime.now().isoformat()}] pushed reading{' (ANOMALY)' if inject else ''}")
            sent += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nStopped after {sent} readings.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
