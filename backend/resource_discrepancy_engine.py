"""FlowSense Phase 2: standalone resource discrepancy calculations."""
import math

DEFAULT_CONSUMPTION_TOLERANCE = 5.0
DEFAULT_POWER_FACTOR_MIN = 0.97
DEFAULT_POWER_FACTOR_MAX = 0.98
DEFAULT_LOAD_FACTOR_MIN = 0.65
DEFAULT_LOAD_FACTOR_MAX = 0.85


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def consumption_status(actual, expected, tolerance_percent=5.0):
    a, e = _number(actual), _number(expected)
    result = {
        "actual": a, "expected": e, "deviation": None,
        "deviation_percent": None, "status": "insufficient_data",
        "alert_color": "grey", "reason": None
    }
    if a is None or e is None:
        result["reason"] = "Actual or expected reading is missing or invalid."
        return result
    if a < 0:
        result["reason"] = "Actual reading cannot be negative."
        return result
    if e <= 0:
        result["reason"] = "Expected baseline must be greater than zero."
        return result
    if tolerance_percent < 0:
        raise ValueError("Tolerance cannot be negative.")

    deviation = a - e
    pct = deviation / e * 100
    if pct > tolerance_percent:
        status, color = "above_expected", "red"
    elif pct < -tolerance_percent:
        status, color = "below_expected", "orange"
    else:
        status, color = "balanced", "green"
    result.update({
        "deviation": round(deviation, 4),
        "deviation_percent": round(pct, 2),
        "status": status, "alert_color": color
    })
    return result


def range_status(value, minimum, maximum):
    if minimum > maximum:
        raise ValueError("Minimum cannot exceed maximum.")
    number = _number(value)
    result = {
        "value": number, "minimum": minimum, "maximum": maximum,
        "status": "insufficient_data", "alert_color": "grey",
        "reason": None
    }
    if number is None:
        result["reason"] = "Measurement is missing or invalid."
        return result
    if number < minimum:
        status, color = "below_range", "orange"
    elif number > maximum:
        status, color = "above_range", "red"
    else:
        status, color = "balanced", "green"
    result.update({"status": status, "alert_color": color})
    return result


def analyze_facility(
    telemetry,
    *,
    consumption_tolerance_percent=5.0,
    power_factor_min=0.97,
    power_factor_max=0.98,
    load_factor_min=0.65,
    load_factor_max=0.85,
):
    metrics = {
        "energy": consumption_status(
            telemetry.get("energy_kwh"),
            telemetry.get("expected_energy_kwh"),
            consumption_tolerance_percent,
        ),
        "water": consumption_status(
            telemetry.get("water_kl"),
            telemetry.get("expected_water_kl"),
            consumption_tolerance_percent,
        ),
        "power_factor": range_status(
            telemetry.get("power_factor"), power_factor_min, power_factor_max
        ),
        "load_factor": range_status(
            telemetry.get("load_factor"), load_factor_min, load_factor_max
        ),
    }
    colors = [metric["alert_color"] for metric in metrics.values()]
    if "red" in colors:
        status, color = "alert", "red"
    elif "orange" in colors:
        status, color = "warning", "orange"
    elif "grey" in colors:
        status, color = "insufficient_data", "grey"
    else:
        status, color = "balanced", "green"

    return {
        "facility_code": telemetry.get("facility_code"),
        "facility_name": telemetry.get("facility_name"),
        "overall_status": status,
        "overall_alert_color": color,
        "metrics": metrics,
        "metadata": {
            "engine": "FlowSense Resource Discrepancy Engine",
            "version": "1.0",
            "live_data_connected": False,
        },
        "interpretation_note": (
            "Standalone calculations only; not connected to live telemetry. "
            "Load-factor limits are provisional and require facility-specific "
            "configuration. Alerts do not prove a fault or its cause."
        ),
    }
