"""
FlowSense Detection Engine
===========================

Standalone anomaly and loss-detection engine.

Purpose:
    Analyze facility telemetry against expected/baseline values and
    produce structured anomaly, severity, loss, and likely-source results.

This module is intentionally independent from FastAPI so it can be:
    1. Tested independently
    2. Called by the realtime backend
    3. Reused by batch/historical analysis
    4. Extended later for ML/AI detection

Architecture:
    Main Meter + IoT Sensors
            |
            v
    Detection Engine
            |
            +--> Baseline comparison
            +--> Energy anomaly
            +--> Water anomaly
            +--> Leak analysis
            +--> Equipment anomaly
            +--> Severity
            +--> Loss estimation
            +--> Likely source
            |
            v
        Structured result
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ============================================================
# CONFIGURATION
# ============================================================

# Minimum deviation required before a normal reading becomes
# an anomaly.
ENERGY_WARNING_DEVIATION = 0.15
ENERGY_CRITICAL_DEVIATION = 0.30

WATER_WARNING_DEVIATION = 0.15
WATER_CRITICAL_DEVIATION = 0.30

FLOW_WARNING_DEVIATION = 0.20
FLOW_CRITICAL_DEVIATION = 0.40

PRESSURE_WARNING_DROP = 0.15
PRESSURE_CRITICAL_DROP = 0.30

TEMPERATURE_WARNING = 35.0
TEMPERATURE_CRITICAL = 45.0

VIBRATION_WARNING = 4.0
VIBRATION_CRITICAL = 7.0

# Minimum water-flow level considered meaningful for leak
# analysis. This prevents tiny/no-flow values from creating
# false leak detections.
MIN_LEAK_FLOW_LPM = 5.0

# Loss calculations.
DEFAULT_ENERGY_LOSS_UNIT = "kWh"
DEFAULT_WATER_LOSS_UNIT = "kL"


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class DetectionResult:
    """
    Structured result returned by the detection engine.
    """

    detected: bool = False

    anomaly_type: Optional[str] = None

    resource_type: Optional[str] = None

    severity: str = "healthy"

    description: str = ""

    expected_value: Optional[float] = None

    actual_value: Optional[float] = None

    deviation_percent: Optional[float] = None

    estimated_loss: float = 0.0

    loss_unit: Optional[str] = None

    likely_source: Optional[str] = None

    source_type: Optional[str] = None

    area_name: Optional[str] = None

    confidence_percent: float = 0.0

    detection_method: str = "baseline"

    detected_at: str = ""

    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result into a JSON-friendly dictionary.
        """

        return asdict(self)


# ============================================================
# BASIC HELPERS
# ============================================================

def _number(value: Any) -> Optional[float]:
    """
    Safely convert a value to float.

    Returns None for missing or invalid values.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_percent(actual: float, expected: float) -> float:
    """
    Calculate percentage deviation from expected value.
    """

    if expected == 0:
        return 0.0

    return ((actual - expected) / abs(expected)) * 100.0


def _severity_from_deviation(
    deviation_percent: float,
    warning_threshold: float,
    critical_threshold: float,
) -> str:
    """
    Convert positive percentage deviation into severity.
    """

    deviation = abs(deviation_percent) / 100.0

    if deviation >= critical_threshold:
        return "critical"

    if deviation >= warning_threshold:
        return "attention"

    return "healthy"


def _now_iso() -> str:
    """
    Return current UTC timestamp.
    """

    return datetime.now(timezone.utc).isoformat()


def _result(
    *,
    anomaly_type: str,
    resource_type: str,
    severity: str,
    description: str,
    expected_value: Optional[float] = None,
    actual_value: Optional[float] = None,
    deviation_percent: Optional[float] = None,
    estimated_loss: float = 0.0,
    loss_unit: Optional[str] = None,
    likely_source: Optional[str] = None,
    source_type: Optional[str] = None,
    area_name: Optional[str] = None,
    confidence_percent: float = 0.0,
    detection_method: str = "baseline",
    evidence: Optional[Dict[str, Any]] = None,
) -> DetectionResult:

    return DetectionResult(
        detected=True,
        anomaly_type=anomaly_type,
        resource_type=resource_type,
        severity=severity,
        description=description,
        expected_value=expected_value,
        actual_value=actual_value,
        deviation_percent=deviation_percent,
        estimated_loss=max(0.0, estimated_loss),
        loss_unit=loss_unit,
        likely_source=likely_source,
        source_type=source_type,
        area_name=area_name,
        confidence_percent=max(
            0.0,
            min(100.0, confidence_percent),
        ),
        detection_method=detection_method,
        detected_at=_now_iso(),
        evidence=evidence or {},
    )


# ============================================================
# SOURCE RESOLUTION
# ============================================================

def resolve_likely_source(
    *,
    anomaly_type: Optional[str],
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Optional[str]]:
    """
    Resolve a likely equipment/source from existing FlowSense
    equipment/source mappings.

    This is intentionally conservative.

    We do not claim an exact physical location unless the
    available source mapping supports that conclusion.
    """

    candidates = source_candidates or []

    if not candidates:
        return {
            "likely_source": None,
            "source_type": None,
            "area_name": None,
        }

    preferred_types = []

    if anomaly_type == "high_energy":
        preferred_types = [
            "HVAC",
            "Cooling",
            "Lighting",
        ]

    elif anomaly_type == "water_leak":
        preferred_types = [
            "Plumbing",
            "Pump",
        ]

    elif anomaly_type == "high_water":
        preferred_types = [
            "Pump",
            "Plumbing",
        ]

    elif anomaly_type == "equipment_vibration":
        preferred_types = [
            "Pump",
        ]

    elif anomaly_type == "temperature":
        preferred_types = [
            "HVAC",
            "Cooling",
        ]

    for source in candidates:

        source_type = source.get("source_type")

        if source_type in preferred_types:

            return {
                "likely_source": source.get("source_name"),
                "source_type": source_type,
                "area_name": source.get("area_name"),
            }

    # Fall back to first mapped source.
    source = candidates[0]

    return {
        "likely_source": source.get("source_name"),
        "source_type": source.get("source_type"),
        "area_name": source.get("area_name"),
    }


# ============================================================
# ENERGY DETECTION
# ============================================================

def detect_energy_anomaly(
    actual_energy: Any,
    expected_energy: Any,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> DetectionResult:
    """
    Detect abnormal energy consumption against baseline.

    Example:

        Expected = 400 kWh
        Actual   = 520 kWh

        Deviation = +30%

    Result:

        critical high_energy anomaly
    """

    actual = _number(actual_energy)
    expected = _number(expected_energy)

    if actual is None or expected is None:
        return DetectionResult(
            description="Insufficient energy data for detection.",
            detected_at=_now_iso(),
        )

    if expected <= 0:
        return DetectionResult(
            description="Invalid energy baseline.",
            detected_at=_now_iso(),
        )

    deviation = _safe_percent(actual, expected)

    severity = _severity_from_deviation(
        deviation,
        ENERGY_WARNING_DEVIATION,
        ENERGY_CRITICAL_DEVIATION,
    )

    if severity == "healthy":

        return DetectionResult(
            detected=False,
            anomaly_type=None,
            resource_type="energy",
            severity="healthy",
            description="Energy consumption is within expected range.",
            expected_value=expected,
            actual_value=actual,
            deviation_percent=deviation,
            estimated_loss=0.0,
            loss_unit=DEFAULT_ENERGY_LOSS_UNIT,
            confidence_percent=95.0,
            detection_method="baseline",
            detected_at=_now_iso(),
        )

    source = resolve_likely_source(
        anomaly_type="high_energy",
        source_candidates=source_candidates,
    )

    excess_energy = max(
        0.0,
        actual - expected,
    )

    return _result(
        anomaly_type="high_energy",
        resource_type="energy",
        severity=severity,
        description=(
            f"Energy consumption is {abs(deviation):.1f}% "
            f"above the expected baseline."
        ),
        expected_value=expected,
        actual_value=actual,
        deviation_percent=deviation,
        estimated_loss=excess_energy,
        loss_unit=DEFAULT_ENERGY_LOSS_UNIT,
        likely_source=source["likely_source"],
        source_type=source["source_type"],
        area_name=source["area_name"],
        confidence_percent=88.0,
        detection_method="baseline",
        evidence={
            "expected_energy_kwh": expected,
            "actual_energy_kwh": actual,
            "excess_energy_kwh": excess_energy,
        },
    )


# ============================================================
# WATER CONSUMPTION DETECTION
# ============================================================

def detect_water_anomaly(
    actual_water: Any,
    expected_water: Any,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> DetectionResult:
    """
    Detect abnormal water consumption against baseline.
    """

    actual = _number(actual_water)
    expected = _number(expected_water)

    if actual is None or expected is None:
        return DetectionResult(
            description="Insufficient water data for detection.",
            detected_at=_now_iso(),
        )

    if expected <= 0:
        return DetectionResult(
            description="Invalid water baseline.",
            detected_at=_now_iso(),
        )

    deviation = _safe_percent(actual, expected)

    severity = _severity_from_deviation(
        deviation,
        WATER_WARNING_DEVIATION,
        WATER_CRITICAL_DEVIATION,
    )

    if severity == "healthy":

        return DetectionResult(
            detected=False,
            anomaly_type=None,
            resource_type="water",
            severity="healthy",
            description="Water consumption is within expected range.",
            expected_value=expected,
            actual_value=actual,
            deviation_percent=deviation,
            estimated_loss=0.0,
            loss_unit=DEFAULT_WATER_LOSS_UNIT,
            confidence_percent=95.0,
            detection_method="baseline",
            detected_at=_now_iso(),
        )

    source = resolve_likely_source(
        anomaly_type="high_water",
        source_candidates=source_candidates,
    )

    excess_water = max(
        0.0,
        actual - expected,
    )

    return _result(
        anomaly_type="high_water",
        resource_type="water",
        severity=severity,
        description=(
            f"Water consumption is {abs(deviation):.1f}% "
            f"above the expected baseline."
        ),
        expected_value=expected,
        actual_value=actual,
        deviation_percent=deviation,
        estimated_loss=excess_water,
        loss_unit=DEFAULT_WATER_LOSS_UNIT,
        likely_source=source["likely_source"],
        source_type=source["source_type"],
        area_name=source["area_name"],
        confidence_percent=87.0,
        detection_method="baseline",
        evidence={
            "expected_water_kl": expected,
            "actual_water_kl": actual,
            "excess_water_kl": excess_water,
        },
    )


# ============================================================
# WATER LEAK DETECTION
# ============================================================

def detect_water_leak(
    *,
    water_flow_lpm: Any,
    water_pressure_bar: Any = None,
    expected_flow_lpm: Any = None,
    expected_pressure_bar: Any = None,
    water_consumption_kl: Any = None,
    expected_water_kl: Any = None,
    leak_sensor: Any = None,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> DetectionResult:
    """
    Detect probable water leakage using multiple signals.

    Evidence can include:

        - Leak sensor
        - Abnormally high flow
        - Pressure drop
        - High water consumption

    The engine increases confidence when multiple signals
    agree.

    It deliberately reports "probable leak" rather than
    claiming an exact pipe/location.
    """

    flow = _number(water_flow_lpm)
    pressure = _number(water_pressure_bar)
    expected_flow = _number(expected_flow_lpm)
    expected_pressure = _number(expected_pressure_bar)

    water = _number(water_consumption_kl)
    expected_water = _number(expected_water_kl)

    leak_flag = bool(leak_sensor)

    evidence = {}

    score = 0

    # --------------------------------------------------------
    # Leak sensor
    # --------------------------------------------------------

    if leak_flag:

        score += 3

        evidence["leak_sensor"] = True

    # --------------------------------------------------------
    # High water flow
    # --------------------------------------------------------

    flow_deviation = None

    if (
        flow is not None
        and expected_flow is not None
        and expected_flow > 0
    ):

        flow_deviation = _safe_percent(
            flow,
            expected_flow,
        )

        evidence["flow_deviation_percent"] = flow_deviation

        if flow >= MIN_LEAK_FLOW_LPM:

            if flow_deviation >= FLOW_CRITICAL_DEVIATION * 100:
                score += 3

            elif flow_deviation >= FLOW_WARNING_DEVIATION * 100:
                score += 2

    # --------------------------------------------------------
    # Pressure drop
    # --------------------------------------------------------

    pressure_drop = None

    if (
        pressure is not None
        and expected_pressure is not None
        and expected_pressure > 0
    ):

        pressure_drop = (
            (expected_pressure - pressure)
            / expected_pressure
        )

        evidence["pressure_drop_percent"] = (
            pressure_drop * 100
        )

        if pressure_drop >= PRESSURE_CRITICAL_DROP:

            score += 3

        elif pressure_drop >= PRESSURE_WARNING_DROP:

            score += 2

    # --------------------------------------------------------
    # High water consumption
    # --------------------------------------------------------

    water_deviation = None

    if (
        water is not None
        and expected_water is not None
        and expected_water > 0
    ):

        water_deviation = _safe_percent(
            water,
            expected_water,
        )

        evidence["water_deviation_percent"] = (
            water_deviation
        )

        if water_deviation >= WATER_CRITICAL_DEVIATION * 100:

            score += 2

        elif water_deviation >= WATER_WARNING_DEVIATION * 100:

            score += 1

    # --------------------------------------------------------
    # Determine result
    # --------------------------------------------------------

    if score < 3:

        return DetectionResult(
            detected=False,
            anomaly_type=None,
            resource_type="water",
            severity="healthy",
            description="No strong evidence of a water leak.",
            confidence_percent=70.0,
            detection_method="multi_signal",
            detected_at=_now_iso(),
            evidence=evidence,
        )

    if score >= 7:

        severity = "critical"

    else:

        severity = "attention"

    source = resolve_likely_source(
        anomaly_type="water_leak",
        source_candidates=source_candidates,
    )

    # --------------------------------------------------------
    # Estimate loss
    #
    # This is a conservative estimate:
    # excess water consumption above baseline.
    # --------------------------------------------------------

    estimated_loss = 0.0

    if (
        water is not None
        and expected_water is not None
        and expected_water > 0
    ):

        estimated_loss = max(
            0.0,
            water - expected_water,
        )

    confidence = min(
        98.0,
        55.0 + score * 6.0,
    )

    description = (
        "Probable water leak detected using multiple "
        "flow, pressure, consumption, and sensor signals."
    )

    return _result(
        anomaly_type="water_leak",
        resource_type="water",
        severity=severity,
        description=description,
        expected_value=expected_water,
        actual_value=water,
        deviation_percent=water_deviation,
        estimated_loss=estimated_loss,
        loss_unit=DEFAULT_WATER_LOSS_UNIT,
        likely_source=source["likely_source"],
        source_type=source["source_type"],
        area_name=source["area_name"],
        confidence_percent=confidence,
        detection_method="multi_signal",
        evidence={
            **evidence,
            "evidence_score": score,
            "interpretation": (
                "Multiple independent signals support "
                "probable leakage."
            ),
        },
    )


# ============================================================
# EQUIPMENT VIBRATION DETECTION
# ============================================================

def detect_vibration_anomaly(
    vibration_mm_s: Any,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> DetectionResult:
    """
    Detect abnormal equipment vibration.
    """

    vibration = _number(vibration_mm_s)

    if vibration is None:

        return DetectionResult(
            description="No vibration reading available.",
            detected_at=_now_iso(),
        )

    if vibration >= VIBRATION_CRITICAL:

        severity = "critical"

    elif vibration >= VIBRATION_WARNING:

        severity = "attention"

    else:

        return DetectionResult(
            detected=False,
            anomaly_type=None,
            resource_type="equipment",
            severity="healthy",
            description="Equipment vibration is within normal range.",
            actual_value=vibration,
            confidence_percent=90.0,
            detection_method="threshold",
            detected_at=_now_iso(),
        )

    source = resolve_likely_source(
        anomaly_type="equipment_vibration",
        source_candidates=source_candidates,
    )

    return _result(
        anomaly_type="equipment_vibration",
        resource_type="equipment",
        severity=severity,
        description=(
            f"Equipment vibration reached "
            f"{vibration:.2f} mm/s."
        ),
        actual_value=vibration,
        likely_source=source["likely_source"],
        source_type=source["source_type"],
        area_name=source["area_name"],
        confidence_percent=91.0,
        detection_method="threshold",
        evidence={
            "vibration_mm_s": vibration,
            "warning_threshold": VIBRATION_WARNING,
            "critical_threshold": VIBRATION_CRITICAL,
        },
    )


# ============================================================
# TEMPERATURE DETECTION
# ============================================================

def detect_temperature_anomaly(
    temperature_c: Any,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> DetectionResult:
    """
    Detect abnormally high temperature.
    """

    temperature = _number(temperature_c)

    if temperature is None:

        return DetectionResult(
            description="No temperature reading available.",
            detected_at=_now_iso(),
        )

    if temperature >= TEMPERATURE_CRITICAL:

        severity = "critical"

    elif temperature >= TEMPERATURE_WARNING:

        severity = "attention"

    else:

        return DetectionResult(
            detected=False,
            anomaly_type=None,
            resource_type="environment",
            severity="healthy",
            description="Temperature is within normal range.",
            actual_value=temperature,
            confidence_percent=90.0,
            detection_method="threshold",
            detected_at=_now_iso(),
        )

    source = resolve_likely_source(
        anomaly_type="temperature",
        source_candidates=source_candidates,
    )

    return _result(
        anomaly_type="temperature",
        resource_type="environment",
        severity=severity,
        description=(
            f"Temperature reached {temperature:.1f}°C, "
            "which is above the configured operating range."
        ),
        actual_value=temperature,
        likely_source=source["likely_source"],
        source_type=source["source_type"],
        area_name=source["area_name"],
        confidence_percent=90.0,
        detection_method="threshold",
        evidence={
            "temperature_c": temperature,
            "warning_threshold": TEMPERATURE_WARNING,
            "critical_threshold": TEMPERATURE_CRITICAL,
        },
    )


# ============================================================
# FACILITY TELEMETRY ANALYSIS
# ============================================================

def analyze_telemetry(
    telemetry: Dict[str, Any],
    *,
    energy_baseline: Any = None,
    water_baseline: Any = None,
    expected_flow_lpm: Any = None,
    expected_pressure_bar: Any = None,
    source_candidates: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Analyze a complete facility telemetry payload.

    This is the main entry point that the FastAPI backend can
    eventually call.

    Input example:

        {
            "energy_kwh": 520,
            "water_kl": 42,
            "water_flow_lpm": 65,
            "water_pressure_bar": 2.1,
            "temperature_c": 29,
            "vibration_mm_s": 2.0,
            "leak_detected": False
        }

    Returns:

        {
            "facility_status": "critical",
            "anomaly_count": 2,
            "anomalies": [...],
            "primary_anomaly": {...},
            "estimated_energy_loss_kwh": ...,
            "estimated_water_loss_kl": ...
        }
    """

    anomalies: list[DetectionResult] = []

    # ========================================================
    # ENERGY
    # ========================================================

    energy_result = detect_energy_anomaly(
        actual_energy=telemetry.get("energy_kwh"),
        expected_energy=energy_baseline,
        source_candidates=source_candidates,
    )

    if energy_result.detected:

        anomalies.append(energy_result)

    # ========================================================
    # WATER CONSUMPTION
    # ========================================================

    water_result = detect_water_anomaly(
        actual_water=telemetry.get("water_kl"),
        expected_water=water_baseline,
        source_candidates=source_candidates,
    )

    if water_result.detected:

        anomalies.append(water_result)

    # ========================================================
    # WATER LEAK
    # ========================================================

    leak_result = detect_water_leak(
        water_flow_lpm=telemetry.get("water_flow_lpm"),
        water_pressure_bar=telemetry.get(
            "water_pressure_bar"
        ),
        expected_flow_lpm=expected_flow_lpm,
        expected_pressure_bar=expected_pressure_bar,
        water_consumption_kl=telemetry.get("water_kl"),
        expected_water_kl=water_baseline,
        leak_sensor=telemetry.get("leak_detected"),
        source_candidates=source_candidates,
    )

    if leak_result.detected:

        anomalies.append(leak_result)

    # ========================================================
    # VIBRATION
    # ========================================================

    vibration_result = detect_vibration_anomaly(
        telemetry.get("vibration_mm_s"),
        source_candidates=source_candidates,
    )

    if vibration_result.detected:

        anomalies.append(vibration_result)

    # ========================================================
    # TEMPERATURE
    # ========================================================

    temperature_result = detect_temperature_anomaly(
        telemetry.get("temperature_c"),
        source_candidates=source_candidates,
    )

    if temperature_result.detected:

        anomalies.append(temperature_result)

    # ========================================================
    # PRIORITY
    # ========================================================

    severity_rank = {
        "healthy": 0,
        "attention": 1,
        "critical": 2,
    }

    anomalies.sort(
        key=lambda item: severity_rank.get(
            item.severity,
            0,
        ),
        reverse=True,
    )

    primary = anomalies[0] if anomalies else None

    if primary:

        facility_status = primary.severity

    else:

        facility_status = "healthy"

    # ========================================================
    # LOSS TOTALS
    # ========================================================

    energy_loss = sum(
        item.estimated_loss
        for item in anomalies
        if item.resource_type == "energy"
        and item.loss_unit == DEFAULT_ENERGY_LOSS_UNIT
    )

    water_loss = sum(
        item.estimated_loss
        for item in anomalies
        if item.resource_type == "water"
        and item.loss_unit == DEFAULT_WATER_LOSS_UNIT
    )

    return {
        "facility_status": facility_status,

        "anomaly_count": len(anomalies),

        "estimated_energy_loss_kwh": round(
            energy_loss,
            3,
        ),

        "estimated_water_loss_kl": round(
            water_loss,
            3,
        ),

        "primary_anomaly": (
            primary.to_dict()
            if primary
            else None
        ),

        "anomalies": [
            item.to_dict()
            for item in anomalies
        ],

        "analyzed_at": _now_iso(),
    }


# ============================================================
# SIMPLE HEALTH SCORE
# ============================================================

def calculate_energy_efficiency_score(
    telemetry: Dict[str, Any],
    expected_energy: Any = None,
) -> float:
    """
    Calculate a 0-100 energy efficiency score.

    This is deliberately deterministic and explainable.
    """

    actual = _number(
        telemetry.get("energy_kwh")
    )

    expected = _number(
        expected_energy
    )

    if actual is None or expected is None or expected <= 0:

        return 81.0

    deviation = max(
        0.0,
        _safe_percent(
            actual,
            expected,
        ),
    )

    # Every 1% above baseline reduces score by 0.5.
    penalty = deviation * 0.5

    score = 95.0 - penalty

    return round(
        max(40.0, min(100.0, score)),
        1,
    )


def calculate_water_efficiency_score(
    telemetry: Dict[str, Any],
    expected_water: Any = None,
) -> float:
    """
    Calculate a 0-100 water efficiency score.
    """

    actual = _number(
        telemetry.get("water_kl")
    )

    expected = _number(
        expected_water
    )

    if actual is None or expected is None or expected <= 0:

        return 76.0

    deviation = max(
        0.0,
        _safe_percent(
            actual,
            expected,
        ),
    )

    penalty = deviation * 0.5

    score = 94.0 - penalty

    return round(
        max(35.0, min(100.0, score)),
        1,
    )


# ============================================================
# RECOMMENDATION GENERATOR
# ============================================================

def generate_recommendation(
    result: DetectionResult,
) -> Optional[Dict[str, Any]]:
    """
    Convert a detection result into a human-readable action.

    This is intentionally rule-based for Upgrade 1.
    The AI/LLM recommendation layer can be added later.
    """

    if not result.detected:

        return None

    recommendations = {
        "high_energy": {
            "action": (
                "Inspect high-load equipment and compare "
                "current operating conditions with the "
                "facility baseline."
            ),
            "priority": "high",
        },

        "high_water": {
            "action": (
                "Inspect high-consumption water systems, "
                "pumps, and plumbing usage against the "
                "normal operating pattern."
            ),
            "priority": "high",
        },

        "water_leak": {
            "action": (
                "Inspect the mapped plumbing/pump area. "
                "Check flow and pressure conditions and "
                "verify the suspected leak source."
            ),
            "priority": "critical",
        },

        "equipment_vibration": {
            "action": (
                "Inspect the associated equipment for "
                "mechanical wear, imbalance, loose components, "
                "or abnormal operation."
            ),
            "priority": "high",
        },

        "temperature": {
            "action": (
                "Inspect HVAC/cooling equipment and verify "
                "ventilation and operating conditions."
            ),
            "priority": "high",
        },
    }

    recommendation = recommendations.get(
        result.anomaly_type
    )

    if not recommendation:

        return None

    return {
        "anomaly_type": result.anomaly_type,

        "priority": recommendation["priority"],

        "action": recommendation["action"],

        "likely_source": result.likely_source,

        "area_name": result.area_name,

        "confidence_percent": result.confidence_percent,
    }


# ============================================================
# TEST / SELF CHECK
# ============================================================

def self_test() -> None:
    """
    Run a local sanity test.

    This does not connect to PostgreSQL.
    """

    source_candidates = [
        {
            "source_name": "HVAC System",
            "source_type": "HVAC",
            "area_name": "Zone 1",
        },
        {
            "source_name": "Water Pump System",
            "source_type": "Pump",
            "area_name": "Utility Area",
        },
        {
            "source_name": "Plumbing Network",
            "source_type": "Plumbing",
            "area_name": "Utility Network",
        },
    ]

    telemetry = {
        "energy_kwh": 520,
        "water_kl": 45,
        "water_flow_lpm": 70,
        "water_pressure_bar": 2.1,
        "temperature_c": 29,
        "vibration_mm_s": 2.0,
        "leak_detected": False,
    }

    result = analyze_telemetry(
        telemetry,
        energy_baseline=400,
        water_baseline=30,
        expected_flow_lpm=25,
        expected_pressure_bar=3.5,
        source_candidates=source_candidates,
    )

    print()
    print("==========================================")
    print(" FlowSense Detection Engine Self-Test")
    print("==========================================")
    print(
        f"Facility status : "
        f"{result['facility_status']}"
    )
    print(
        f"Anomaly count   : "
        f"{result['anomaly_count']}"
    )
    print(
        f"Energy loss     : "
        f"{result['estimated_energy_loss_kwh']} kWh"
    )
    print(
        f"Water loss      : "
        f"{result['estimated_water_loss_kl']} kL"
    )

    if result["primary_anomaly"]:

        primary = result["primary_anomaly"]

        print(
            f"Primary anomaly : "
            f"{primary['anomaly_type']}"
        )

        print(
            f"Severity        : "
            f"{primary['severity']}"
        )

        print(
            f"Likely source   : "
            f"{primary['likely_source']}"
        )

        recommendation = generate_recommendation(
            DetectionResult(**primary)
        )

        if recommendation:

            print(
                f"Recommendation  : "
                f"{recommendation['action']}"
            )

    print("==========================================")
    print()


# ============================================================
# MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    self_test()