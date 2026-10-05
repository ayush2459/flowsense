import json
import requests
from typing import Any, Dict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"


# ============================================================
# HELPERS
# ============================================================

def _safe_number(value: Any):
    try:
        if value is None:
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


# ============================================================
# FACILITY AI EVIDENCE
# ============================================================

def _build_ai_evidence(
    report: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Build a compact evidence package for facility-level Ollama analysis.

    FlowSense backend calculations remain authoritative.
    Ollama only interprets supplied evidence.
    """

    facility = report.get("facility") or {}

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
    # Historical readings
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
    # Detection
    # --------------------------------------------------------

    primary_anomaly = detection.get(
        "primary_anomaly"
    )

    efficiency = detection.get(
        "efficiency",
        {},
    )

    # --------------------------------------------------------
    # Compact facility evidence
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
                None
                if realtime
                else latest_energy,

            "latest_water":
                None
                if realtime
                else latest_water,
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


# ============================================================
# FACILITY-LEVEL AI ANALYSIS
# ============================================================

def generate_report_analysis(
    report: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Generate facility-level FlowSense AI analysis.

    Backend calculations remain authoritative.
    """

    evidence = _build_ai_evidence(
        report
    )

    system_prompt = """
You are the FlowSense Energy & Water Intelligence assistant.

Analyze ONLY the evidence supplied by FlowSense.

Rules:

1. Never invent measurements, anomalies, alerts, causes,
   savings, or events.

2. FlowSense backend calculations are authoritative.

3. If realtime.available is true, realtime data is authoritative
   for current values.

4. Historical data must not override realtime data.

5. If an anomaly is supplied, explicitly report it.

6. If actual usage is above expected usage, explicitly state
   that it is above expected.

7. Do not recalculate authoritative metrics.

8. Recommendations must be supported by supplied evidence.

9. Keep the response concise and professional.

10. Do not mention that you are an AI model.

Return ONLY valid JSON:

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
            "num_predict": 300,
            "num_ctx": 4096,
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
            timeout=180,
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

        if not content:
            raise ValueError(
                "Ollama returned empty content"
            )

        analysis = json.loads(
            content
        )

        return {
            "success": True,

            "model":
                OLLAMA_MODEL,

            "analysis":
                analysis,

            "error":
                None,
        }

    except HTTPError as exc:

        return {
            "success": False,

            "model":
                OLLAMA_MODEL,

            "analysis":
                {},

            "error":
                f"Ollama HTTP error: {exc.code}",
        }

    except URLError as exc:

        return {
            "success": False,

            "model":
                OLLAMA_MODEL,

            "analysis":
                {},

            "error":
                f"Ollama connection failed: {exc.reason}",
        }

    except json.JSONDecodeError:

        return {
            "success": False,

            "model":
                OLLAMA_MODEL,

            "analysis":
                {},

            "error":
                "Ollama returned invalid JSON",
        }

    except Exception as exc:

        return {
            "success": False,

            "model":
                OLLAMA_MODEL,

            "analysis":
                {},

            "error":
                f"Ollama analysis failed: {exc}",
        }


# ============================================================
# PORTFOLIO / ALL-FACILITIES AI ANALYSIS
# ============================================================
# ============================================================
# PORTFOLIO / ALL-FACILITIES AI ANALYSIS
# ============================================================

def generate_portfolio_report_analysis(
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate portfolio-level FlowSense AI interpretation.

    IMPORTANT:
    - Portfolio metrics are calculated by the FlowSense backend.
    - Ollama is used only for concise qualitative interpretation
      and recommendations.
    - Exact numeric statements returned to the frontend are built
      from backend-authoritative values, preventing the model from
      hallucinating values such as 0 kWh or 0 kL.
    """

    portfolio_totals = (
        evidence.get("portfolio_totals") or {}
    )

    portfolio_variance = (
        evidence.get("portfolio_variance") or {}
    )

    energy_kwh = float(
        portfolio_totals.get("energy_kwh") or 0
    )

    expected_energy_kwh = float(
        portfolio_totals.get("expected_energy_kwh") or 0
    )

    water_kl = float(
        portfolio_totals.get("water_kl") or 0
    )

    expected_water_kl = float(
        portfolio_totals.get("expected_water_kl") or 0
    )

    anomaly_count = int(
        portfolio_totals.get("anomaly_count") or 0
    )

    critical_facilities = int(
        portfolio_totals.get("critical_facilities") or 0
    )

    attention_facilities = int(
        portfolio_totals.get("attention_facilities") or 0
    )

    energy_variance_percent = (
        portfolio_variance.get("energy_variance_percent")
    )

    water_variance_percent = (
        portfolio_variance.get("water_variance_percent")
    )

    # --------------------------------------------------------
    # Backend-authoritative status calculations
    # --------------------------------------------------------

    if energy_kwh > expected_energy_kwh:
        energy_status = "above"
    elif energy_kwh < expected_energy_kwh:
        energy_status = "below"
    else:
        energy_status = "at"

    if water_kl > expected_water_kl:
        water_status = "above"
    elif water_kl < expected_water_kl:
        water_status = "below"
    else:
        water_status = "at"

    # --------------------------------------------------------
    # Exact backend-derived statements.
    # These are NOT generated by Ollama.
    # --------------------------------------------------------

    if energy_status == "above":
        energy_analysis = (
            f"Energy consumption is above the expected portfolio "
            f"level: {energy_kwh:.3f} kWh actual versus "
            f"{expected_energy_kwh:.3f} kWh expected "
            f"({energy_variance_percent}% variance)."
        )
    elif energy_status == "below":
        energy_analysis = (
            f"Energy consumption is below the expected portfolio "
            f"level: {energy_kwh:.3f} kWh actual versus "
            f"{expected_energy_kwh:.3f} kWh expected "
            f"({energy_variance_percent}% variance)."
        )
    else:
        energy_analysis = (
            f"Energy consumption is at the expected portfolio "
            f"level: {energy_kwh:.3f} kWh."
        )

    if water_status == "above":
        water_analysis = (
            f"Water consumption is above the expected portfolio "
            f"level: {water_kl:.3f} kL actual versus "
            f"{expected_water_kl:.3f} kL expected "
            f"({water_variance_percent}% variance)."
        )
    elif water_status == "below":
        water_analysis = (
            f"Water consumption is below the expected portfolio "
            f"level: {water_kl:.3f} kL actual versus "
            f"{expected_water_kl:.3f} kL expected "
            f"({water_variance_percent}% variance)."
        )
    else:
        water_analysis = (
            f"Water consumption is at the expected portfolio "
            f"level: {water_kl:.3f} kL."
        )

    # --------------------------------------------------------
    # Compact CPU-friendly Ollama prompt.
    #
    # IMPORTANT:
    # Do NOT ask Ollama to reproduce numeric metrics.
    # This avoids CPU-model hallucinations such as 0 kWh.
    # --------------------------------------------------------

    prompt = f"""
You are the FlowSense portfolio monitoring assistant.

The FlowSense backend has already calculated the authoritative
portfolio metrics.

Energy status: {energy_status}
Water status: {water_status}

Detected anomalies: {anomaly_count}
Critical facilities: {critical_facilities}
Facilities requiring attention: {attention_facilities}

Energy variance: {energy_variance_percent}%
Water variance: {water_variance_percent}%

Generate ONLY qualitative interpretation and practical
evidence-based recommendations.

Do NOT output any numbers.
Do NOT mention kWh.
Do NOT mention kL.
Do NOT invent facilities.
Do NOT invent anomalies.
Do NOT recalculate metrics.

Return ONLY valid JSON:

{{
  "summary": "two short factual sentences",
  "key_findings": [
    "one short factual finding",
    "one short factual finding"
  ],
  "recommendations": [
    "one practical evidence-based recommendation",
    "one practical evidence-based recommendation"
  ],
  "priority_actions": [
    "one concise priority action"
  ]
}}
"""

    payload = {
        "model": OLLAMA_MODEL,

        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "stream": False,

        "format": "json",

        "options": {
            "temperature": 0.1,
            "num_predict": 100,
            "num_ctx": 2048,
        },
    }

    ai_analysis = {}

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        content = (
            data.get(
                "message",
                {},
            ).get(
                "content",
                "",
            )
        )

        if not content:
            raise ValueError(
                "Ollama returned empty portfolio content"
            )

        print(
            "[Portfolio AI] Raw Ollama response:"
        )
        print(content)

        parsed = json.loads(content)

        if isinstance(parsed, dict):
            ai_analysis = parsed

    except requests.Timeout:
        print(
            "[Portfolio AI] Ollama timed out; "
            "using backend-authoritative fallback."
        )

    except requests.RequestException as exc:
        print(
            f"[Portfolio AI] Ollama request failed: {exc}; "
            "using backend-authoritative fallback."
        )

    except json.JSONDecodeError:
        print(
            "[Portfolio AI] Ollama returned invalid JSON; "
            "using backend-authoritative fallback."
        )

    except Exception as exc:
        print(
            f"[Portfolio AI] Unexpected Ollama error: {exc}; "
            "using backend-authoritative fallback."
        )

    # --------------------------------------------------------
    # Normalize AI qualitative fields.
    # --------------------------------------------------------

    key_findings = (
        ai_analysis.get("key_findings")
        if isinstance(
            ai_analysis.get("key_findings"),
            list,
        )
        else []
    )

    recommendations = (
        ai_analysis.get("recommendations")
        if isinstance(
            ai_analysis.get("recommendations"),
            list,
        )
        else []
    )

    priority_actions = (
        ai_analysis.get("priority_actions")
        if isinstance(
            ai_analysis.get("priority_actions"),
            list,
        )
        else []
    )

    # --------------------------------------------------------
    # Deterministic findings ensure the dashboard never loses
    # important backend evidence even if Ollama is weak/slow.
    # --------------------------------------------------------

    deterministic_findings = []

    if energy_status == "above":
        deterministic_findings.append(
            "Portfolio energy consumption is above the configured expected level."
        )
    elif energy_status == "below":
        deterministic_findings.append(
            "Portfolio energy consumption is below the configured expected level."
        )
    else:
        deterministic_findings.append(
            "Portfolio energy consumption is at the configured expected level."
        )

    if water_status == "above":
        deterministic_findings.append(
            "Portfolio water consumption is above the configured expected level."
        )
    elif water_status == "below":
        deterministic_findings.append(
            "Portfolio water consumption is below the configured expected level."
        )
    else:
        deterministic_findings.append(
            "Portfolio water consumption is at the configured expected level."
        )

    if anomaly_count > 0:
        deterministic_findings.append(
            f"{anomaly_count} anomalies are present in the backend evidence."
        )

    # Keep AI findings only when they are non-empty.
    final_findings = deterministic_findings[:2]

    for finding in key_findings:
        if isinstance(finding, str) and finding.strip():
            if finding not in final_findings:
                final_findings.append(finding.strip())

    final_findings = final_findings[:3]

    # --------------------------------------------------------
    # Deterministic executive summary.
    # --------------------------------------------------------

    if energy_status == "above" and water_status == "above":
        summary = (
            "Portfolio energy and water consumption are both above "
            "their configured expected levels. "
        )
    elif energy_status == "above":
        summary = (
            "Portfolio energy consumption is above its configured "
            "expected level. "
        )
    elif water_status == "above":
        summary = (
            "Portfolio water consumption is above its configured "
            "expected level. "
        )
    else:
        summary = (
            "Portfolio consumption is not above both configured "
            "expected levels. "
        )

    summary += (
        f"The backend reports {anomaly_count} anomalies, "
        f"{critical_facilities} critical facilities, and "
        f"{attention_facilities} facilities requiring attention."
    )

    # --------------------------------------------------------
    # Safe fallback recommendations if Ollama returns none.
    # --------------------------------------------------------

    if not recommendations:
        recommendations = [
            "Review facilities contributing the largest deviations from expected usage.",
            "Investigate critical and anomaly-affected facilities using the available device and sensor evidence.",
        ]

    if not priority_actions:
        if critical_facilities > 0:
            priority_actions = [
                "Review the critical facilities and associated anomalies first."
            ]
        elif anomaly_count > 0:
            priority_actions = [
                "Review the detected anomalies and their affected facilities."
            ]
        else:
            priority_actions = [
                "Continue monitoring portfolio energy and water performance."
            ]

    # --------------------------------------------------------
    # Final normalized response.
    #
    # Numeric energy/water analysis comes ONLY from backend.
    # Ollama supplies qualitative findings/recommendations.
    # --------------------------------------------------------

    normalized = {
        "summary": summary,

        "key_findings": final_findings,

        "energy_analysis": energy_analysis,

        "water_analysis": water_analysis,

        "facilities_requiring_attention": [],

        "recommendations": [
            str(x)
            for x in recommendations[:3]
            if isinstance(x, str) and x.strip()
        ],

        "priority_actions": [
            str(x)
            for x in priority_actions[:3]
            if isinstance(x, str) and x.strip()
        ],
    }

    return {
        "success": True,
        "model": OLLAMA_MODEL,
        "analysis": normalized,
        "error": None,
    }
