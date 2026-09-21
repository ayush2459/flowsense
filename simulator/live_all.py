import argparse
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import requests
from dotenv import load_dotenv


# ============================================================
# CONFIG
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
        DATABASE_URL,
        connect_timeout=5
    )


def get_facilities():
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    facility_code
                FROM facilities
                ORDER BY facility_code
            """)

            return [
                row[0]
                for row in cur.fetchall()
            ]

    finally:
        conn.close()


# ============================================================
# TELEMETRY GENERATOR
# ============================================================

def generate_telemetry(
    facility_code,
    anomaly_rate
):
    anomaly = random.random() < anomaly_rate

    # --------------------------------------------------------
    # Normal values
    # --------------------------------------------------------

    energy = random.uniform(
        280,
        360
    )

    power_kw = random.uniform(
        180,
        420
    )

    water = random.uniform(
        24,
        36
    )

    water_flow = random.uniform(
        18,
        32
    )

    water_pressure = random.uniform(
        2.5,
        4.0
    )

    temperature = random.uniform(
        21,
        30
    )

    humidity = random.uniform(
        40,
        65
    )

    vibration = random.uniform(
        0.5,
        2.5
    )

    leak_detected = False

    status = "healthy"

    # --------------------------------------------------------
    # Anomaly simulation
    # --------------------------------------------------------

    if anomaly:

        anomaly_type = random.choice([
            "high_energy",
            "high_water",
            "water_leak",
            "equipment_vibration",
            "temperature"
        ])

        if anomaly_type == "high_energy":

            energy *= random.uniform(
                2.0,
                3.0
            )

            power_kw *= random.uniform(
                1.8,
                2.5
            )

            status = "critical"

        elif anomaly_type == "high_water":

            water *= random.uniform(
                2.0,
                3.0
            )

            water_flow *= random.uniform(
                2.0,
                3.0
            )

            status = "critical"

        elif anomaly_type == "water_leak":

            water_flow *= random.uniform(
                2.5,
                4.0
            )

            leak_detected = True

            status = "critical"

        elif anomaly_type == "equipment_vibration":

            vibration *= random.uniform(
                3.0,
                5.0
            )

            status = "attention"

        elif anomaly_type == "temperature":

            temperature = random.uniform(
                40,
                55
            )

            status = "attention"

    else:

        anomaly_type = None

        # Small chance of attention state
        if random.random() < 0.08:
            status = "attention"

    # --------------------------------------------------------
    # Expected values and derived losses
    # --------------------------------------------------------

    expected_energy = 320.0
    expected_water = 30.0

    estimated_energy_loss = max(
        0.0,
        energy - expected_energy
    )

    estimated_water_loss = max(
        0.0,
        water - expected_water
    )

    # A leak can create additional unaccounted water usage
    if anomaly_type == "water_leak":
        estimated_water_loss = max(
            estimated_water_loss,
            water_flow * 0.08
        )

    # --------------------------------------------------------
    # Water treatment / reuse
    # --------------------------------------------------------

    treatment_rate = random.uniform(
        88.0,
        96.0
    )

    reuse_rate = random.uniform(
        60.0,
        75.0
    )

    if anomaly_type == "high_water":

        treatment_rate -= random.uniform(
            3.0,
            7.0
        )

        reuse_rate -= random.uniform(
            4.0,
            8.0
        )

    elif anomaly_type == "water_leak":

        treatment_rate -= random.uniform(
            4.0,
            8.0
        )

        reuse_rate -= random.uniform(
            5.0,
            10.0
        )

    treatment_rate = max(
        0.0,
        min(100.0, treatment_rate)
    )

    reuse_rate = max(
        0.0,
        min(100.0, reuse_rate)
    )

    # --------------------------------------------------------
    # TELEMETRY PAYLOAD
    # --------------------------------------------------------

    return {

        "reading_time": time.time(),

        "energy_kwh": round(
            energy,
            3
        ),

        "expected_energy_kwh": expected_energy,

        "estimated_energy_loss_kwh": round(
            estimated_energy_loss,
            3
        ),

        "power_kw": round(
            power_kw,
            3
        ),

        "voltage_v": round(
            random.uniform(220, 240),
            2
        ),

        "current_a": round(
            max(0.1, power_kw * 1000 / 230),
            2
        ),
        "water_kl": round(
            water,
            3
        ),

        "expected_water_kl": expected_water,

        "estimated_water_loss_kl": round(
            estimated_water_loss,
            3
        ),

        "treatment_rate": round(
            treatment_rate,
            1
        ),

        "reuse_rate": round(
            reuse_rate,
            1
        ),

        "water_flow_lpm": round(
            water_flow,
            3
        ),

        "water_pressure_bar": round(
            water_pressure,
            3
        ),

        "temperature_c": round(
            temperature,
            2
        ),

        "humidity_percent": round(
            humidity,
            2
        ),

        "vibration_mm_s": round(
            vibration,
            3
        ),

        "leak_detected": leak_detected,

        "anomaly": anomaly,

        "anomaly_type": anomaly_type,

        "status": status
    }


# ============================================================
# BROADCAST
# ============================================================

def broadcast(
    facility_code,
    payload
):
    url = (
        f"{API_URL}/api/live/broadcast/"
        f"{facility_code}"
    )

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=2
        )

        response.raise_for_status()

        return (
            facility_code,
            True,
            None,
            payload
        )

    except Exception as exc:

        return (
            facility_code,
            False,
            str(exc),
            payload
        )


# ============================================================
# ONE REALTIME ROUND
# ============================================================

def run_round(
    facilities,
    anomaly_rate,
    workers
):
    start = time.perf_counter()

    healthy = 0
    attention = 0
    critical = 0
    failed = 0

    results = []

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = []

        for facility in facilities:

            payload = generate_telemetry(
                facility,
                anomaly_rate
            )

            futures.append(
                executor.submit(
                    broadcast,
                    facility,
                    payload
                )
            )

        for future in as_completed(
            futures
        ):

            facility, success, error, payload = (
                future.result()
            )

            results.append(
                (
                    facility,
                    success,
                    error,
                    payload
                )
            )

            if not success:

                failed += 1

            elif payload["status"] == "critical":

                critical += 1

            elif payload["status"] == "attention":

                attention += 1

            else:

                healthy += 1

    elapsed = (
        time.perf_counter()
        - start
    )

    return (
        healthy,
        attention,
        critical,
        failed,
        elapsed,
        results
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0
    )

    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.15
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=100
    )

    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="0 = run forever"
    )

    args = parser.parse_args()

    facilities = get_facilities()

    if not facilities:

        raise RuntimeError(
            "No facilities found in database"
        )

    print()
    print("==========================================")
    print(" FlowSense Realtime IoT Simulator")
    print("==========================================")
    print(
        f"Facilities    : {len(facilities)}"
    )
    print(
        f"Interval      : {args.interval}s"
    )
    print(
        f"Anomaly rate  : {args.anomaly_rate}"
    )
    print(
        f"Workers       : {args.workers}"
    )
    print(
        f"FastAPI       : {API_URL}"
    )
    print("Mode          : REALTIME")
    print("==========================================")
    print("Press Ctrl+C to stop.")
    print()

    round_number = 0

    try:

        while (
            args.count == 0
            or round_number < args.count
        ):

            (
                healthy,
                attention,
                critical,
                failed,
                elapsed,
                results
            ) = run_round(
                facilities,
                args.anomaly_rate,
                args.workers
            )

            round_number += 1

            # Show one sample so we can verify
            # the new realtime fields directly.
            sample = (
                results[0][3]
                if results
                else None
            )

            if sample:
                print(
                    f"  Sample | "
                    f"Energy={sample['energy_kwh']} kWh | "
                    f"Water={sample['water_kl']} kL | "
                    f"WaterLoss={sample['estimated_water_loss_kl']} kL | "
                    f"Power={sample['power_kw']} kW"
                )

            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"Round {round_number} | "
                f"Facilities={len(facilities)} | "
                f"Healthy={healthy} | "
                f"Attention={attention} | "
                f"Critical={critical} | "
                f"Failed={failed} | "
                f"Time={elapsed:.3f}s"
            )

            sleep_time = max(
                0,
                args.interval - elapsed
            )

            if sleep_time > 0:

                time.sleep(
                    sleep_time
                )

    except KeyboardInterrupt:

        print()
        print(
            f"Stopped after "
            f"{round_number} rounds."
        )


if __name__ == "__main__":
    main()