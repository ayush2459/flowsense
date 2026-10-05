import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


API_BASE = "http://127.0.0.1:8000"

# Device sends a heartbeat every 15 seconds while it is online.
HEARTBEAT_INTERVAL_SECONDS = 15

# Backend considers a device online for 120 seconds after its
# most recent heartbeat.
BACKEND_HEARTBEAT_TIMEOUT_SECONDS = 120


# These devices intentionally have larger outage periods so that
# the backend can clearly detect real offline intervals.
TEST_OFFLINE_DEVICES = {
    11,
    22,
    33,
    44,
    55,
    66,
    77,
    88,
    99,
    100,
}


NETWORK_TYPES = {
    0: "Wi-Fi",
    1: "4G",
    2: "Ethernet",
    3: "Mesh",
}


device_state = {}
state_lock = threading.Lock()


def device_code(number):
    return f"FS-FAC-{number:03d}-IOT"


def network_for(number):
    return NETWORK_TYPES[(number - 1) % len(NETWORK_TYPES)]


def device_profile(number):
    """
    Generate a deterministic but different connectivity profile
    for every device.

    online_seconds:
        How long the device continuously sends heartbeats.

    offline_seconds:
        How long the device intentionally stops sending heartbeats.

    offset:
        Gives every device a different phase in its cycle.

    Both online and offline durations are unique enough across
    the 100 development devices to create different realtime
    uptime behaviour.
    """

    # Online period:
    # 300s -> 1797s approximately
    online_seconds = 300 + ((number * 137) % 1498)

    # Offline period:
    # Always > 120 seconds so backend can detect the outage.
    # 150s -> 599s approximately
    offline_seconds = 150 + ((number * 83) % 450)

    # Give every device a different position inside its cycle.
    cycle_length = online_seconds + offline_seconds
    offset = (number * 197) % cycle_length

    # Special devices intentionally receive more unstable
    # connectivity to demonstrate offline/online detection.
    if number in TEST_OFFLINE_DEVICES:
        online_seconds = 240 + ((number * 53) % 361)
        offline_seconds = 300 + ((number * 71) % 421)
        cycle_length = online_seconds + offline_seconds
        offset = (number * 149) % cycle_length

    return {
        "online": online_seconds,
        "offline": offline_seconds,
        "offset": offset,
    }


def send_heartbeat(number):
    code = device_code(number)
    network_type = network_for(number)

    payload = {
        "network_type": network_type,
        "network_identifier": (
            f"flowsense-"
            f"{network_type.lower().replace('-', '')}-"
            f"{number:03d}"
        ),
        "firmware_version": "1.0.0",
        "signal_strength": -45 - (number % 35),
    }

    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{API_BASE}/api/devices/{code}/heartbeat",
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:
            response.read().decode("utf-8")

        with state_lock:
            device_state[number] = {
                "last_success": datetime.now(timezone.utc),
                "status": "online",
            }

        print(
            f"[SIM] {code} -> heartbeat accepted "
            f"| {network_type} "
            f"| signal={payload['signal_strength']} dBm"
        )

    except urllib.error.HTTPError as exc:

        with state_lock:
            device_state[number] = {
                "status": "http_error"
            }

        print(
            f"[SIM] {code} -> HTTP {exc.code}"
        )

    except Exception as exc:

        with state_lock:
            device_state[number] = {
                "status": "error"
            }

        print(
            f"[SIM] {code} -> ERROR: {exc}"
        )


def should_send(number, elapsed):
    profile = device_profile(number)

    online_seconds = profile["online"]
    offline_seconds = profile["offline"]
    offset = profile["offset"]

    cycle_length = (
        online_seconds +
        offline_seconds
    )

    cycle_position = (
        elapsed + offset
    ) % cycle_length

    return cycle_position < online_seconds


def device_worker(number):

    code = device_code(number)
    profile = device_profile(number)

    print(
        f"[SIM] Started {code} "
        f"| network={network_for(number)} "
        f"| online={profile['online']}s "
        f"| offline={profile['offline']}s "
        f"| offset={profile['offset']}s"
    )

    while True:

        elapsed = time.monotonic()

        if should_send(number, elapsed):

            send_heartbeat(number)

        else:

            print(
                f"[SIM] {code} -> intentionally silent "
                f"(real simulated outage)"
            )

        time.sleep(
            HEARTBEAT_INTERVAL_SECONDS
        )


def main():

    print("=" * 80)
    print(
        "FlowSense 100-Device Realtime Heartbeat Simulator"
    )
    print("=" * 80)

    print(
        f"API: {API_BASE}"
    )

    print(
        f"Heartbeat interval: "
        f"{HEARTBEAT_INTERVAL_SECONDS}s"
    )

    print(
        f"Backend heartbeat timeout: "
        f"{BACKEND_HEARTBEAT_TIMEOUT_SECONDS}s"
    )

    print(
        "Each device has an individual connectivity profile."
    )

    print(
        "Offline periods are longer than the backend timeout."
    )

    print(
        "Special offline-test devices: "
        + ", ".join(
            device_code(number)
            for number in sorted(TEST_OFFLINE_DEVICES)
        )
    )

    print("=" * 80)

    print(
        "[SIM] Device profile summary:"
    )

    for number in range(1, 101):

        profile = device_profile(number)

        print(
            f"{device_code(number)} | "
            f"online={profile['online']}s | "
            f"offline={profile['offline']}s | "
            f"offset={profile['offset']}s"
        )

    print("=" * 80)

    threads = []

    for number in range(1, 101):

        thread = threading.Thread(
            target=device_worker,
            args=(number,),
            daemon=True,
        )

        thread.start()

        threads.append(thread)

    print(
        "[SIM] 100 device workers started."
    )

    try:

        while True:
            time.sleep(10)

    except KeyboardInterrupt:

        print(
            "\n[SIM] Simulator stopped."
        )


if __name__ == "__main__":
    main()