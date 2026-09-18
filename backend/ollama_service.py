import json
from typing import Any, Dict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"


def _safe_number(value: Any):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
def _build_ai_evidence(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact evidence package for Ollama.

    FlowSense backend calculations remain authoritative.
    The LLM only interprets supplied metrics.
    """

    facility = report.get("facility") or {}
    snapshot = report.get("current_snapshot") or {}
    realtime = report.get("realtime") or {}
    realtime_data = realtime.get("data") or {}
    detection = realtime.get("detection") or {}

    energy = report.get("energy") or {}
    water = report.get("water") or {}

    reconciliation = report.get(
        "reconciliation",
        [],
    )

    anomalies = report.get(
        "anomalies",
        [],
    )

    alerts = report.get(
        "alerts",
        [],
    )

    devices = report.get(
        "devices",
        [],
    )

    # --------------------------------------------------------
    # Latest historical readings
    # --------------------------------------------------------

    energy_readings = energy.get(
        "readings",
        [],
    )

    water_readings = water.get(
        "readings",
        [],
    )

    latest_energy = (
        energy_readings[-1]
        if energy_readings
        else None
    )

    latest_water = (
        water_readings[-1]
        if water_readings
        else None
    )

    # --------------------------------------------------------
    # Realtime detection
    # --------------------------------------------------------

    primary_anomaly = detection.get(
        "primary_anomaly"
    )

    efficiency = detection.get(
        "efficiency",
        {},
    )

    # --------------------------------------------------------
    # Compact evidence
    # --------------------------------------------------------

    return {
        "facility": {
            "facility_code":
                facility.get("facility_code"),

            "facility_name":
                facility.get("facility_name"),

            "facility_type":
                facility.get("facility_type"),

            "city":
                facility.get("city"),

            "state":
                facility.get("state"),

            "status":
                facility.get("status"),
        },

        "report_period":
            report.get(
                "report_metadata",
                {},
            ).get(
                "period"
            ),

        "realtime": {
            "available":
                bool(realtime),

            "timestamp":
                realtime.get(
                    "timestamp"
                ),

            "energy_kwh":
                _safe_number(
                    realtime_data.get(
                        "energy_kwh"
                    )
                ),

            "expected_energy_kwh":
                _safe_number(
                    realtime_data.get(
                        "expected_energy_kwh"
                    )
                ),

            "water_kl":
                _safe_number(
                    realtime_data.get(
                        "water_kl"
                    )
                ),

            "expected_water_kl":
                _safe_number(
                    realtime_data.get(
                        "expected_water_kl"
                    )
                ),

            "power_kw":
                _safe_number(
                    realtime_data.get(
                        "power_kw"
                    )
                ),

            "water_flow_lpm":
                _safe_number(
                    realtime_data.get(
                        "water_flow_lpm"
                    )
                ),

            "pressure_bar":
                _safe_number(
                    realtime_data.get(
                        "pressure_bar"
                    )
                ),

            "temperature_c":
                _safe_number(
                    realtime_data.get(
                        "temperature_c"
                    )
                ),

            "humidity_percent":
                _safe_number(
                    realtime_data.get(
                        "humidity_percent"
                    )
                ),

            "leak_detected":
                realtime_data.get(
                    "leak_detected"
                ),
        },

        "historical_data": {
            "energy_reading_count":
                len(energy_readings),

            "water_reading_count":
                len(water_readings),

            "latest_energy":
                latest_energy,

            "latest_water":
                latest_water,
        },

        "efficiency": {
            "energy_score":
                _safe_number(
                    efficiency.get(
                        "energy_score"
                    )
                ),

            "water_score":
                _safe_number(
                    efficiency.get(
                        "water_score"
                    )
                ),
        },

        "detection": {
            "facility_status":
                detection.get(
                    "facility_status"
                ),

            "anomaly_count":
                detection.get(
                    "anomaly_count",
                    0,
                ),

            "estimated_energy_loss_kwh":
                _safe_number(
                    detection.get(
                        "estimated_energy_loss_kwh"
                    )
                ),

            "estimated_water_loss_kl":
                _safe_number(
                    detection.get(
                        "estimated_water_loss_kl"
                    )
                ),

            "primary_anomaly":
                primary_anomaly,

        },

        "persisted_data": {
            "reconciliation_count":
                len(reconciliation),

            "anomaly_count":
                len(anomalies),

            "alert_count":
                len(alerts),

            "device_count":
                len(devices),
        },
    }


def generate_report_analysis(
    report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a concise evidence-based FlowSense
    report analysis using local Ollama.
    """

    evidence = _build_ai_evidence(
        report
    )

    system_prompt = """
You are the FlowSense Energy & Water Intelligence assistant.

Analyze ONLY the FlowSense evidence supplied by the application.

IMPORTANT RULES:\n\n1. Never invent measurements, anomalies, alerts, causes, savings, or events.\n\n2. FlowSense backend calculations are authoritative.\n\n3. REALTIME DETECTION HAS PRIORITY. If realtime.available is true, use the realtime and detection sections as the primary basis of the analysis.\n\n4. If detection.anomaly_count is greater than 0 OR detection.primary_anomaly contains a detected anomaly, explicitly report the anomaly. Do NOT say no anomalies were detected.\n\n5. When a primary realtime anomaly exists, report the supplied anomaly type, severity, confidence, likely source, area, detection method, evidence, and estimated loss when those fields are available.\n\n6. If realtime data is available, do not describe the facility as healthy when the realtime detection facility_status indicates attention, warning, critical, or another non-healthy state.\n\n7. Treat realtime telemetry separately from historical data. Historical data must never override a realtime detection result.\n\n8. If historical data is unavailable or limited, state that briefly, but do not let that obscure realtime findings.\n\n9. Do not recalculate authoritative metrics.\n\n10. Recommendations must be practical and directly supported by the supplied realtime detection evidence.\n\n11. Keep the response concise and professional.\n\n12. Do not mention that you are an AI language model.

Return ONLY valid JSON with exactly these fields:

{
  "summary": "short executive summary",
  "key_findings": [
    "finding 1",
    "finding 2"
  ],
  "energy_analysis": "short energy analysis",
  "water_analysis": "short water analysis",
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "priority_actions": [
    "priority action 1"
  ]
}
"""

    user_prompt = (
        "Analyze this verified FlowSense evidence:\n\n"
        + json.dumps(
            evidence,
            default=str,
            separators=(",", ":"),
        )
    )

    payload = {
        "model": OLLAMA_MODEL,

        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        "stream": False,

        "format": "json",

        "options": {
            "temperature": 0.2,

            # Keep generation short and fast.
            "num_predict": 350,
        },
    }

    request = Request(
        OLLAMA_URL,

        data=json.dumps(
            payload
        ).encode("utf-8"),

        headers={
            "Content-Type":
                "application/json",
        },

        method="POST",
    )

    try:

        with urlopen(
            request,
            timeout=90,
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        content = (
            result.get(
                "message",
                {},
            ).get(
                "content",
                "{}",
            )
        )

        analysis = json.loads(
            content
        )

        return {
            "success":
                True,

            "model":
                OLLAMA_MODEL,

            "analysis":
                analysis,
        }

    except HTTPError as exc:

        return {
            "success":
                False,

            "error":
                f"Ollama HTTP error: {exc.code}",
        }

    except URLError as exc:

        return {
            "success":
                False,

            "error":
                f"Ollama connection failed: {exc.reason}",
        }

    except json.JSONDecodeError:

        return {
            "success":
                False,

            "error":
                "Ollama returned invalid JSON",
        }

    except Exception as exc:

        return {
            "success":
                False,

            "error":
                f"Ollama analysis failed: {exc}",
        }
