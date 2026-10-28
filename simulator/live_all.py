
import argparse
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_AUTH_MODE = os.getenv("DB_AUTH_MODE", "").strip().lower()
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "flowsense")
DB_USER = os.getenv("DB_USER", "flowsense_gateway")

API_URL = os.getenv(
    "FLOWSENSE_API_URL",
    "http://127.0.0.1:8001",
).rstrip("/")

# Live telemetry is not persisted by default.
# Set FLOWSENSE_PERSIST_READINGS=true only when database
# persistence has been explicitly configured and tested.
PERSIST_READINGS = (
    os.getenv("FLOWSENSE_PERSIST_READINGS", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)

CONNECT_TIMEOUT = 5
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, 15)


# ============================================================
# DATABASE / FACILITY DISCOVERY
# ============================================================

def get_conn():
    if DB_AUTH_MODE == "iam":
        if not DB_HOST or not DB_USER:
            raise RuntimeError(
                "DB_HOST and DB_USER are required for IAM authentication."
            )

        import boto3

        token = boto3.client(
            "rds",
            region_name=AWS_REGION,
        ).generate_db_auth_token(
            DBHostname=DB_HOST,
            Port=DB_PORT,
            DBUsername=DB_USER,
        )

        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=token,
            sslmode="require",
            connect_timeout=CONNECT_TIMEOUT,
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing. Check the project-root .env file."
        )

    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=CONNECT_TIMEOUT,
    )


def get_facilities():
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT facility_code
                FROM facilities
                ORDER BY facility_code
                """
            )
            facilities = [
                row[0]
                for row in cur.fetchall()
                if row[0]
            ]

        return facilities

    finally:
        conn.close()


# ============================================================
# TELEMETRY GENERATOR
# ============================================================

def generate_telemetry(facility_code, anomaly_rate):
    # Limit anomalies to avoid overwhelming the demonstration.
    effective_anomaly_rate = min(
        max(float(anomaly_rate), 0.0),
        0.01,
    )

    anomaly = random.random() < effective_anomaly_rate
    anomaly_type = None

    energy = random.uniform(280, 360)
    power_kw = random.uniform(180, 420)
    power_factor = round(random.uniform(0.90, 0.99), 3)
    load_factor = round(random.uniform(0.50, 0.95), 3)
    water = random.uniform(24, 36)
    water_flow = random.uniform(18, 32)
    water_pressure = random.uniform(2.5, 4.0)
    temperature = random.uniform(21, 30)
    humidity = random.uniform(40, 65)
    vibration = random.uniform(0.5, 2.5)

    leak_detected = False
    status = "healthy"

    if anomaly:
        anomaly_type = random.choice(
            [
                "high_energy",
                "high_water",
                "water_leak",
                "equipment_vibration",
                "temperature",
            ]
        )

        if anomaly_type == "high_energy":
            energy *= random.uniform(2.0, 3.0)
            power_kw *= random.uniform(1.8, 2.5)
            status = "critical"

        elif anomaly_type == "high_water":
            water *= random.uniform(2.0, 3.0)
            water_flow *= random.uniform(2.0, 3.0)
            status = "critical"

        elif anomaly_type == "water_leak":
            water_flow *= random.uniform(2.5, 4.0)
            leak_detected = True
            status = "critical"

        elif anomaly_type == "equipment_vibration":
            vibration *= random.uniform(3.0, 5.0)
            status = "attention"

        elif anomaly_type == "temperature":
            temperature = random.uniform(40, 55)
            status = "attention"

    elif random.random() < 0.08:
        status = "attention"

    # Expected consumption and estimated losses.
    expected_energy = 320.0
    expected_water = 30.0

    estimated_energy_loss = max(
        0.0,
        energy - expected_energy,
    )

    estimated_water_loss = max(
        0.0,
        water - expected_water,
    )

    if anomaly_type == "water_leak":
        estimated_water_loss = max(
            estimated_water_loss,
            water_flow * 0.08,
        )

    # Water treatment and reuse metrics.
    treatment_rate = random.uniform(88.0, 96.0)
    reuse_rate = random.uniform(60.0, 75.0)

    if anomaly_type == "high_water":
        treatment_rate -= random.uniform(3.0, 7.0)
        reuse_rate -= random.uniform(4.0, 8.0)

    elif anomaly_type == "water_leak":
        treatment_rate -= random.uniform(4.0, 8.0)
        reuse_rate -= random.uniform(5.0, 10.0)

    treatment_rate = max(0.0, min(100.0, treatment_rate))
    reuse_rate = max(0.0, min(100.0, reuse_rate))

    return {
        "reading_time": datetime.now(timezone.utc).isoformat(),
        "energy_kwh": round(energy, 3),
        "expected_energy_kwh": expected_energy,
        "estimated_energy_loss_kwh": round(
            estimated_energy_loss, 3
        ),
        "power_kw": round(power_kw, 3),
        "power_factor": power_factor,
        "load_factor": load_factor,
        "voltage_v": round(random.uniform(220, 240), 2),
        "current_a": round(max(0.1, power_kw * 1000 / 230), 2),
        "water_kl": round(water, 3),
        "expected_water_kl": expected_water,
        "estimated_water_loss_kl": round(
            estimated_water_loss, 3
        ),
        "treatment_rate": round(treatment_rate, 1),
        "reuse_rate": round(reuse_rate, 1),
        "water_flow_lpm": round(water_flow, 3),
        "water_pressure_bar": round(water_pressure, 3),
        "temperature_c": round(temperature, 2),
        "humidity_percent": round(humidity, 2),
        "vibration_mm_s": round(vibration, 3),
        "leak_detected": leak_detected,
        "anomaly": anomaly,
        "anomaly_type": anomaly_type,
        "status": status,
    }


# ============================================================
# HTTP BROADCAST
# ============================================================

def broadcast(facility_code, payload):
    url = f"{API_URL}/api/live/broadcast/{facility_code}"

    try:
        print(
            f"[Simulator Sending] {facility_code} | "
            f"power_factor={payload.get('power_factor')!r} | "
            f"load_factor={payload.get('load_factor')!r}",
            flush=True,
        )
        response = requests.post(
            url,
            json=payload,
            params={
                "persist": str(PERSIST_READINGS).lower(),
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return facility_code, True, None, payload

    except requests.RequestException as exc:
        response = getattr(exc, "response", None)

        if response is not None:
            error_detail = (
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        else:
            error_detail = str(exc)

        print(
            f"[Broadcast Error] {facility_code}: {error_detail}",
            flush=True,
        )

        return facility_code, False, error_detail, payload


# ============================================================
# ONE REALTIME ROUND
# ============================================================

def run_round(facilities, anomaly_rate, workers):
    started = time.perf_counter()

    counts = {
        "healthy": 0,
        "attention": 0,
        "critical": 0,
        "failed": 0,
    }

    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                broadcast,
                facility,
                generate_telemetry(facility, anomaly_rate),
            ): facility
            for facility in facilities
        }

        for future in as_completed(futures):
            facility, success, error, payload = future.result()

            results.append((facility, success, error, payload))

            if not success:
                counts["failed"] += 1
            else:
                status = payload.get("status", "healthy")

                if status in counts:
                    counts[status] += 1
                else:
                    counts["healthy"] += 1

    elapsed = time.perf_counter() - started

    return counts, elapsed, results


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="FlowSense realtime IoT telemetry simulator"
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between rounds",
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.15,
        help="Requested anomaly probability; effective rate is capped at 1%%",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Maximum concurrent HTTP requests",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of rounds; 0 runs continuously",
    )

    args = parser.parse_args()

    if args.interval < 0:
        parser.error("--interval cannot be negative")

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    if args.count < 0:
        parser.error("--count cannot be negative")

    facilities = get_facilities()

    if not facilities:
        raise RuntimeError(
            "No facilities found in the database table 'facilities'."
        )

    print()
    print("=" * 52)
    print(" FlowSense Realtime IoT Simulator")
    print("=" * 52)
    print(f"Facilities       : {len(facilities)}")
    print(f"Interval         : {args.interval}s")
    print(f"Anomaly rate cap : 1%")
    print(f"Workers          : {args.workers}")
    print(f"FastAPI          : {API_URL}")
    print(f"Persist readings : {PERSIST_READINGS}")
    print("=" * 52)
    print("Press Ctrl+C to stop.")
    print()

    round_number = 0

    try:
        while args.count == 0 or round_number < args.count:
            counts, elapsed, results = run_round(
                facilities,
                args.anomaly_rate,
                args.workers,
            )

            round_number += 1

            successful = [
                result for result in results if result[1]
            ]

            if successful:
                sample = successful[0][3]
                print(
                    f"Sample | Energy={sample['energy_kwh']} kWh | "
                    f"Water={sample['water_kl']} kL | "
                    f"Power={sample['power_kw']} kW",
                    flush=True,
                )

            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"Round={round_number} | "
                f"Facilities={len(facilities)} | "
                f"Healthy={counts['healthy']} | "
                f"Attention={counts['attention']} | "
                f"Critical={counts['critical']} | "
                f"Failed={counts['failed']} | "
                f"Time={elapsed:.3f}s",
                flush=True,
            )

            sleep_time = max(0.0, args.interval - elapsed)

            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\nStopped after {round_number} rounds.")


if __name__ == "__main__":
    main()
