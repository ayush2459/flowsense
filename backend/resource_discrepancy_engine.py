"""FlowSense Phase 2: resource discrepancy calculations and scoring."""
import math

DEFAULT_CONSUMPTION_TOLERANCE = 5.0
DEFAULT_POWER_FACTOR_MIN = 0.97
DEFAULT_POWER_FACTOR_MAX = 0.98
DEFAULT_LOAD_FACTOR_MIN = 0.65
DEFAULT_LOAD_FACTOR_MAX = 0.85

# A 20% consumption deviation reaches the maximum discrepancy score.
DEFAULT_SCORE_CAP_DEVIATION_PERCENT = 20.0
# For factor metrics, a distance of 0.10 beyond the allowed range reaches 100.
DEFAULT_FACTOR_SCORE_DISTANCE = 0.10


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _clamp_score(value):
    return round(min(100.0, max(0.0, value)), 2)


def _severity(score):
    if score is None:
        return "insufficient_data"
    if score < 25:
        return "low"
    if score < 50:
        return "moderate"
    if score < 75:
        return "high"
    return "critical"


def consumption_status(
    actual,
    expected,
    tolerance_percent=DEFAULT_CONSUMPTION_TOLERANCE,
    score_cap_deviation_percent=DEFAULT_SCORE_CAP_DEVIATION_PERCENT,
):
    a, e = _number(actual), _number(expected)
    result = {
        "actual": a,
        "expected": e,
        "deviation": None,
        "deviation_percent": None,
        "discrepancy_score": None,
        "excess_consumption_score": None,
        "severity": "insufficient_data",
        "status": "insufficient_data",
        "alert_color": "grey",
        "reason": None,
    }

    tolerance = _number(tolerance_percent)
    score_cap = _number(score_cap_deviation_percent)

    if tolerance is None or tolerance < 0:
        raise ValueError("Tolerance must be a finite non-negative number.")
    if score_cap is None or score_cap <= 0:
        raise ValueError("Score cap deviation must be greater than zero.")

    if a is None or e is None:
        result["reason"] = "Actual or expected reading is missing or invalid."
        return result
    if a < 0:
        result["reason"] = "Actual reading cannot be negative."
        return result
    if e <= 0:
        result["reason"] = "Expected baseline must be greater than zero."
        return result

    deviation = a - e
    pct = deviation / e * 100.0
    score = _clamp_score(abs(pct) / score_cap * 100.0)

    if pct > tolerance:
        status, color = "above_expected", "red"
    elif pct < -tolerance:
        status, color = "below_expected", "orange"
    else:
        status, color = "balanced", "green"

    result.update({
        "deviation": round(deviation, 4),
        "deviation_percent": round(pct, 2),
        "discrepancy_score": score,
        "excess_consumption_score": (
            round(min(max(pct, 0.0) / score_cap * 100, 100.0), 2)
            if score_cap > 0 else None
        ),
        "severity": _severity(score),
        "status": status,
        "alert_color": color,
    })
    return result


def range_status(
    value,
    minimum,
    maximum,
    score_distance=DEFAULT_FACTOR_SCORE_DISTANCE,
):
    low, high, distance = _number(minimum), _number(maximum), _number(score_distance)
    if low is None or high is None or low > high:
        raise ValueError("Range bounds must be finite and minimum cannot exceed maximum.")
    if distance is None or distance <= 0:
        raise ValueError("Score distance must be greater than zero.")

    number = _number(value)
    result = {
        "value": number,
        "minimum": low,
        "maximum": high,
        "discrepancy_score": None,
        "severity": "insufficient_data",
        "status": "insufficient_data",
        "alert_color": "grey",
        "reason": None,
    }
    if number is None:
        result["reason"] = "Measurement is missing or invalid."
        return result

    if number < low:
        status, color = "below_range", "orange"
        score = _clamp_score((low - number) / distance * 100.0)
    elif number > high:
        status, color = "above_range", "red"
        score = _clamp_score((number - high) / distance * 100.0)
    else:
        status, color, score = "balanced", "green", 0.0

    result.update({
        "status": status,
        "alert_color": color,
        "discrepancy_score": score,
        "severity": _severity(score),
    })
    return result


def _cross_resource_indicator(energy, water):
    """Describe same-sample co-deviation; this is not statistical correlation."""
    energy_status = energy["status"]
    water_status = water["status"]
    valid = {"above_expected", "below_expected", "balanced"}

    result = {
        "status": "insufficient_data",
        "energy_status": energy_status,
        "water_status": water_status,
        "correlation_confirmed": False,
        "interpretation": (
            "A single aligned sample cannot establish statistical correlation "
            "or prove the cause of a discrepancy."
        ),
    }

    if energy_status not in valid or water_status not in valid:
        return result

    if energy_status == "above_expected" and water_status == "above_expected":
        label = "both_above_expected"
    elif energy_status == "below_expected" and water_status == "below_expected":
        label = "both_below_expected"
    elif energy_status == "balanced" and water_status == "balanced":
        label = "both_balanced"
    elif energy_status != "balanced" and water_status != "balanced":
        label = "opposite_deviations"
    else:
        label = "one_resource_deviates"

    result["status"] = label
    return result


def analyze_facility(
    telemetry,
    *,
    consumption_tolerance_percent=DEFAULT_CONSUMPTION_TOLERANCE,
    power_factor_min=DEFAULT_POWER_FACTOR_MIN,
    power_factor_max=DEFAULT_POWER_FACTOR_MAX,
    load_factor_min=DEFAULT_LOAD_FACTOR_MIN,
    load_factor_max=DEFAULT_LOAD_FACTOR_MAX,
):
    if not isinstance(telemetry, dict):
        raise TypeError("Telemetry must be a dictionary.")

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
    elif all(c == "grey" for c in colors):
        status, color = "insufficient_data", "grey"
    elif "grey" in colors:
        status, color = "partial_data", "grey"
    else:
        status, color = "balanced", "green"

    consumption_metrics = (metrics["energy"], metrics["water"])
    available_scores = [
        metric["discrepancy_score"]
        for metric in consumption_metrics
        if metric["discrepancy_score"] is not None
    ]
    overall_score = (
        round(sum(available_scores) / len(available_scores), 2)
        if available_scores else None
    )

    excess_scores = [
        metric["excess_consumption_score"]
        for metric in consumption_metrics
        if metric.get("excess_consumption_score") is not None
    ]
    overall_excess_score = (
        round(sum(excess_scores) / len(excess_scores), 2)
        if excess_scores else None
    )

    return {
        "facility_code": telemetry.get("facility_code"),
        "facility_name": telemetry.get("facility_name"),
        "overall_status": status,
        "overall_alert_color": color,
        "discrepancy_score": overall_score,
        "excess_consumption_score": overall_excess_score,
        "severity": _severity(overall_score),
        "metrics": metrics,
        "cross_resource_indicator": _cross_resource_indicator(
            metrics["energy"], metrics["water"]
        ),
        "metadata": {
            "engine": "FlowSense Resource Discrepancy Engine",
            "version": "1.1",
            "live_data_connected": False,
            "scoring_method": (
                "Mean of available metric scores; consumption scores normalize "
                "absolute deviation to a configurable 20% cap. Factor scores "
                "normalize distance outside the configured range to 0.10."
            ),
        },
        "interpretation_note": (
            "Scores quantify deviations, not confirmed losses. Missing or invalid "
            "metrics are excluded from the overall score. Cross-resource indicators "
            "describe same-sample co-deviation and do not establish statistical "
            "correlation or prove a leak or fault. Load-factor limits are provisional "
            "and should be configured for each facility."
        ),
    }
