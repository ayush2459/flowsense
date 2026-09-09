"""
FlowSense realtime IoT simulator.

Generates realistic energy + water telemetry, stores it in PostgreSQL,
and broadcasts the same reading to the FastAPI WebSocket layer.

Usage:

    python live_feed.py --facility FS-FAC-001 --interval 5

Run forever:

    python live_feed.py --facility FS-FAC-001 --interval 5

Run a limited number:

    python live_feed.py --facility FS-FAC-001 --interval 5 --count 20

Requirements:
    DATABASE_URL must exist in .env
"""

import argparse
import os
import random
import time

import requests
import psycopg2

from dotenv import load_dotenv
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

API_URL = os.getenv(
    "FLOWSENSE_API_URL",
    "http://127.0.0.1:8000"
)


# ============================================================
# DATABASE
# ============================================================

def get_conn():

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing from .env"
        )

    return psycopg2.connect(
        DATABASE_URL
    )


# ============================================================
# BROADCAST
# ============================================================

def broadcast_reading(
    facility_code,
    payload
):
    """
    Send the generated telemetry to FastAPI.

    FastAPI then broadcasts it to all React
    WebSocket clients watching this facility.
    """

    url = (
        f"{API_URL}/api/live/broadcast/"
        f"{facility_code}"
    )

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=5
        )

        if response.ok:

            print(
                "[Realtime] Broadcast successful"
            )

        else:

            print(
                f"[Realtime] Broadcast failed: "
                f"{response.status_code}"
            )

    except requests.RequestException as exc:

        print(
            f"[Realtime] Backend unavailable: {exc}"
        )


# ============================================================
# PUSH READING
# ============================================================

def push_reading(
    conn,
    facility_code,
    inject_anomaly
):

    now = datetime.now(timezone.utc)

    energy_value = None
    water_value = None

    energy_meter_id = None
    water_meter_id = None


    # ========================================================
    # FACILITY
    # ========================================================

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT facility_id
            FROM facilities
            WHERE facility_code = %s
            """,
            (facility_code,)
        )

        row = cur.fetchone()

        if not row:

            raise ValueError(
                f"Facility {facility_code} not found"
            )

        facility_id = row[0]


        # ====================================================
        # METERS
        # ====================================================

        cur.execute(
            """
            SELECT
                meter_id,
                resource_type
            FROM meters
            WHERE facility_id = %s
            """,
            (facility_id,)
        )

        meters = cur.fetchall()


        for meter_id, resource_type in meters:

            if resource_type == "energy":

                base = random.uniform(
                    280,
                    340
                )

                if inject_anomaly:

                    base *= random.uniform(
                        2.0,
                        2.8
                    )

                energy_value = round(
                    base,
                    3
                )

                energy_meter_id = meter_id


            elif resource_type == "water":

                base = random.uniform(
                    25,
                    40
                )

                if inject_anomaly:

                    base *= random.uniform(
                        2.0,
                        3.0
                    )

                water_value = round(
                    base,
                    3
                )

                water_meter_id = meter_id


            value = (
                energy_value
                if resource_type == "energy"
                else water_value
            )


            cur.execute(
                """
                INSERT INTO meter_readings
                (
                    meter_id,
                    reading_time,
                    reading_value,
                    quality_status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'good'
                )
                ON CONFLICT
                (
                    meter_id,
                    reading_time
                )
                DO NOTHING
                """,
                (
                    meter_id,
                    now,
                    value
                )
            )


        # ====================================================
        # SENSOR READINGS
        # ====================================================

        cur.execute(
            """
            SELECT
                sensor_id,
                sensor_code,
                data_type
            FROM iot_sensors
            WHERE iot_device_id =
            (
                SELECT iot_device_id
                FROM iot_devices
                WHERE facility_id = %s
            )
            """,
            (facility_id,)
        )

        sensors = cur.fetchall()


        water_flow = None
        water_pressure = None
        temperature = None
        humidity = None
        vibration = None
        leak_detected = False


        for sensor_id, sensor_code, data_type in sensors:

            # ------------------------------------------------
            # BOOLEAN SENSOR
            # ------------------------------------------------

            if data_type == "boolean":

                boolean_value = (
                    random.random()
                    <
                    (
                        0.30
                        if inject_anomaly
                        else 0.02
                    )
                )

                if "LEAK" in sensor_code.upper():

                    leak_detected = boolean_value


                cur.execute(
                    """
                    INSERT INTO sensor_readings
                    (
                        sensor_id,
                        reading_time,
                        boolean_value,
                        quality_status
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        'good'
                    )
                    """,
                    (
                        sensor_id,
                        now,
                        boolean_value
                    )
                )

                continue


            # ------------------------------------------------
            # NUMERIC SENSOR
            # ------------------------------------------------

            code = sensor_code.upper()


            if "WATER_FLOW" in code:

                water_flow = random.uniform(
                    20,
                    50
                )

                if inject_anomaly:

                    water_flow *= 2.5


                value = water_flow


            elif "PRESSURE" in code:

                water_pressure = random.uniform(
                    2.5,
                    4.5
                )

                if inject_anomaly:

                    water_pressure *= 0.5


                value = water_pressure


            elif "TEMP" in code:

                temperature = random.uniform(
                    22,
                    32
                )

                value = temperature


            elif "HUMIDITY" in code:

                humidity = random.uniform(
                    40,
                    75
                )

                value = humidity


            elif "VIBRATION" in code:

                vibration = random.uniform(
                    0.5,
                    3.0
                )

                if inject_anomaly:

                    vibration *= 3


                value = vibration


            elif "ENERGY" in code:

                value = random.uniform(
                    280,
                    340
                )

                if inject_anomaly:

                    value *= 2.5


            else:

                value = random.uniform(
                    20,
                    60
                )


            cur.execute(
                """
                INSERT INTO sensor_readings
                (
                    sensor_id,
                    reading_time,
                    numeric_value,
                    quality_status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'good'
                )
                """,
                (
                    sensor_id,
                    now,
                    round(value, 3)
                )
            )


        # ====================================================
        # UPDATE DEVICE
        # ====================================================

        cur.execute(
            """
            UPDATE iot_devices
            SET
                last_seen_at = %s,
                status = 'online'
            WHERE facility_id = %s
            """,
            (
                now,
                facility_id
            )
        )


    conn.commit()


    # ========================================================
    # REALTIME PAYLOAD
    # ========================================================

    payload = {

        "reading_time":
            now.isoformat(),

        "energy_kwh":
            energy_value,

        "water_kl":
            water_value,

        "water_flow_lpm":
            round(water_flow, 3)
            if water_flow is not None
            else None,

        "water_pressure_bar":
            round(water_pressure, 3)
            if water_pressure is not None
            else None,

        "temperature_c":
            round(temperature, 3)
            if temperature is not None
            else None,

        "humidity_percent":
            round(humidity, 3)
            if humidity is not None
            else None,

        "vibration_mm_s":
            round(vibration, 3)
            if vibration is not None
            else None,

        "leak_detected":
            leak_detected,

        "anomaly":
            inject_anomaly,

        "status":
            "critical"
            if inject_anomaly
            else "healthy"
    }


    # ========================================================
    # BROADCAST TO FASTAPI
    # ========================================================

    broadcast_reading(
        facility_code,
        payload
    )


    return payload


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="FlowSense realtime IoT simulator"
    )

    parser.add_argument(
        "--facility",
        default="FS-FAC-001"
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=5.0
    )

    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.15
    )

    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="0 = run forever"
    )

    args = parser.parse_args()


    conn = get_conn()

    sent = 0


    print()
    print(
        "=========================================="
    )
    print(
        " FlowSense Realtime IoT Simulator"
    )
    print(
        "=========================================="
    )

    print(
        f"Facility      : {args.facility}"
    )

    print(
        f"Interval      : {args.interval}s"
    )

    print(
        f"Anomaly rate  : {args.anomaly_rate}"
    )

    print(
        f"FastAPI       : {API_URL}"
    )

    print(
        "=========================================="
    )

    print(
        "Press Ctrl+C to stop."
    )

    print()


    try:

        while (
            args.count == 0
            or sent < args.count
        ):

            inject_anomaly = (
                random.random()
                <
                args.anomaly_rate
            )


            try:

                payload = push_reading(
                    conn,
                    args.facility,
                    inject_anomaly
                )


                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Energy={payload['energy_kwh']} kWh | "
                    f"Water={payload['water_kl']} kL | "
                    f"Status={payload['status']}"
                )


                sent += 1


            except (
                psycopg2.InterfaceError,
                psycopg2.OperationalError
            ):

                print(
                    "[Database] Connection lost. "
                    "Reconnecting..."
                )

                try:
                    conn.close()
                except Exception:
                    pass

                time.sleep(2)

                conn = get_conn()


            time.sleep(
                max(args.interval, 0.5)
            )


    except KeyboardInterrupt:

        print()
        print(
            f"Stopped after {sent} readings."
        )


    finally:

        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()