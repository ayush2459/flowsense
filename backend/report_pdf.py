from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)


# ============================================================
# HELPERS
# ============================================================

def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt(value, decimals=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def _text(value, default="N/A"):
    if value is None or value == "":
        return default
    return str(value)


def _format_timestamp(value):
    if not value:
        return "N/A"

    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )

        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return str(value)


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def _header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(
        18 * mm,
        height - 12 * mm,
        "FlowSense"
    )

    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        width - 18 * mm,
        height - 12 * mm,
        "Energy & Water Intelligence Report"
    )

    canvas.setStrokeColor(colors.HexColor("#D9DEE7"))
    canvas.line(
        18 * mm,
        height - 15 * mm,
        width - 18 * mm,
        height - 15 * mm,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))

    canvas.drawString(
        18 * mm,
        10 * mm,
        "FlowSense — Generated from measured system data"
    )

    canvas.drawRightString(
        width - 18 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# TABLE
# ============================================================

def _table(data, widths=None, header=True):
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT",
    )

    style = [
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.4,
            colors.HexColor("#D9DEE7"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, -1),
            "Helvetica",
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, -1),
            8,
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
    ]

    if header:
        style.extend([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#F2F4F7"),
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),
        ])

    table.setStyle(TableStyle(style))
    return table



# ============================================================
# CORRECTED REPORT HELPERS
# ============================================================
# These helpers extend the original report engine without
# removing any of the existing FlowSense report capabilities.
# They keep realtime detection, facility targets, configured
# baselines, persisted records, and IoT metadata distinct.
# ============================================================

def _safe_difference(actual, expected):
    """
    Return actual - expected when both values are available.
    A missing value remains None so the report can render N/A
    instead of silently treating missing data as zero.
    """
    if actual is None or expected is None:
        return None

    try:
        return float(actual) - float(expected)
    except (TypeError, ValueError):
        return None


def _safe_percentage(actual, expected):
    """
    Return percentage variance relative to expected.

    This is a reporting helper only. It does not create an
    anomaly classification and does not replace the backend
    detection engine.
    """
    if actual is None or expected in (None, 0):
        return None

    try:
        return (
            (float(actual) - float(expected))
            / abs(float(expected))
        ) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _format_variance(value, unit=""):
    """
    Format a signed variance while preserving N/A for missing
    values.
    """
    if value is None:
        return "N/A"

    try:
        return f"{float(value):+,.2f} {unit}".strip()
    except (TypeError, ValueError):
        return f"{value} {unit}".strip()


def _extract_primary_anomaly(realtime):
    """
    Normalize the different realtime detection payload shapes
    used by FlowSense.

    The backend detection result remains authoritative.
    """
    realtime = realtime or {}

    detection = realtime.get("detection") or {}
    data = realtime.get("data") or {}

    primary = detection.get("primary_anomaly")

    if not primary:
        primary = data.get("primary_anomaly")

    if isinstance(primary, str):
        return {
            "anomaly_type": primary,
            "severity": (
                detection.get("severity")
                or data.get("severity")
            ),
            "confidence_percent": (
                detection.get("confidence_percent")
                or data.get("confidence_percent")
            ),
            "likely_source": (
                detection.get("likely_source")
                or data.get("likely_source")
            ),
            "area_name": (
                detection.get("area_name")
                or data.get("area_name")
            ),
            "description": (
                detection.get("description")
                or data.get("description")
            ),
        }

    if isinstance(primary, dict):
        return primary

    anomaly_count = _num(
        detection.get("anomaly_count"),
        0.0,
    )

    anomaly_type = (
        detection.get("anomaly_type")
        or data.get("anomaly_type")
    )

    if anomaly_count > 0 or anomaly_type:
        return {
            "anomaly_type": anomaly_type,
            "severity": (
                detection.get("severity")
                or data.get("severity")
            ),
            "confidence_percent": (
                detection.get("confidence_percent")
                or data.get("confidence_percent")
            ),
            "likely_source": (
                detection.get("likely_source")
                or data.get("likely_source")
            ),
            "area_name": (
                detection.get("area_name")
                or data.get("area_name")
            ),
            "description": (
                detection.get("description")
                or data.get("description")
            ),
        }

    return None


def _normalized_facility_status(realtime, facility=None):
    """
    Determine the display status from the authoritative realtime
    detection payload when available.

    This helper does not invent an anomaly from a KPI deviation.
    A facility can therefore have a KPI variance while remaining
    Healthy if the detection engine reports no anomaly.
    """
    realtime = realtime or {}
    facility = facility or {}

    detection = realtime.get("detection") or {}
    data = realtime.get("data") or {}

    explicit = (
        detection.get("facility_status")
        or data.get("facility_status")
    )

    if explicit:
        normalized = str(explicit).strip().lower()

        if normalized in ("critical", "crit"):
            return "Critical"

        if normalized in (
            "attention",
            "warning",
            "warn",
            "needs attention",
        ):
            return "Attention"

        if normalized in (
            "healthy",
            "normal",
            "ok",
            "good",
            "active",
        ):
            return "Healthy"

    primary = _extract_primary_anomaly(realtime)

    if primary:
        severity = str(
            primary.get("severity") or ""
        ).strip().lower()

        if severity == "critical":
            return "Critical"

        return "Attention"

    anomaly_count = _num(
        detection.get("anomaly_count"),
        0.0,
    )

    if anomaly_count > 0:
        severity = str(
            detection.get("severity")
            or data.get("severity")
            or ""
        ).strip().lower()

        if severity == "critical":
            return "Critical"

        return "Attention"

    return _text(
        facility.get("status"),
        "Healthy",
    ).title()


def _detection_status_text(realtime):
    """
    Produce a short human-readable detection statement.

    It deliberately does not classify positive target variance as
    an anomaly.
    """
    status = _normalized_facility_status(realtime)

    if status == "Critical":
        return (
            "Critical realtime detection is active. "
            "Review the latest anomaly evidence and source."
        )

    if status == "Attention":
        return (
            "A realtime condition requires attention. "
            "Review the latest detection evidence."
        )

    return (
        "No realtime anomaly detected in the latest "
        "FlowSense detection snapshot."
    )


def _authoritative_loss(
    realtime_data,
    actual,
    expected,
    resource,
):
    """
    Return an authoritative loss value only when supplied by the
    detection/reconciliation pipeline.

    A positive target variance is NOT relabelled as physical loss.
    """
    realtime_data = realtime_data or {}

    if resource == "energy":
        key = "estimated_energy_loss_kwh"
    else:
        key = "estimated_water_loss_kl"

    pipeline_value = realtime_data.get(key)

    if pipeline_value is None:
        return None

    return _num(
        pipeline_value,
        None,
    )


def _loss_or_variance_display(
    realtime_data,
    actual,
    expected,
    resource,
):
    """
    Return both the display value and its semantic label.

    If FlowSense supplied an authoritative loss value, the report
    can safely call it Estimated Loss. Otherwise the report calls
    the positive difference Excess Consumption / Variance.
    """
    loss = _authoritative_loss(
        realtime_data,
        actual,
        expected,
        resource,
    )

    if loss is not None:
        unit = (
            "kWh"
            if resource == "energy"
            else "kL"
        )

        # A zero authoritative loss means the detection/reconciliation
        # pipeline did not identify measurable loss. Do not present
        # that as an "Estimated Loss" value in the report.
        if loss <= 0:
            return (
                "None detected",
                "No Loss Evidence",
                True,
            )

        return (
            f"{_fmt(loss)} {unit}",
            f"Estimated Loss ({unit})",
            True,
        )

    variance = _safe_difference(
        actual,
        expected,
    )

    if variance is not None and variance > 0:
        unit = (
            "kWh"
            if resource == "energy"
            else "kL"
        )

        return (
            _fmt(variance),
            f"Excess Consumption ({unit})",
            False,
        )

    return (
        "N/A",
        "Loss Evidence",
        False,
    )


def _baseline_summary(
    baseline_rows,
    value_label,
    unit,
):
    """
    Build a compact summary from the configured weekly hourly
    baseline profile while preserving the original detailed table.
    """
    baseline_rows = baseline_rows or []

    expected = []
    lower = []
    upper = []

    for item in baseline_rows:
        expected_value = _num(
            item.get("expected_value"),
            None,
        )

        lower_value = _num(
            item.get("lower_threshold"),
            None,
        )

        upper_value = _num(
            item.get("upper_threshold"),
            None,
        )

        if expected_value is not None:
            expected.append(expected_value)

        if lower_value is not None:
            lower.append(lower_value)

        if upper_value is not None:
            upper.append(upper_value)

    average_expected = (
        sum(expected) / len(expected)
        if expected
        else None
    )

    minimum_expected = (
        min(expected)
        if expected
        else None
    )

    maximum_expected = (
        max(expected)
        if expected
        else None
    )

    minimum_lower = (
        min(lower)
        if lower
        else None
    )

    maximum_upper = (
        max(upper)
        if upper
        else None
    )

    return {
        "label": value_label,
        "unit": unit,
        "record_count": len(baseline_rows),
        "average_expected": average_expected,
        "minimum_expected": minimum_expected,
        "maximum_expected": maximum_expected,
        "minimum_lower_threshold": minimum_lower,
        "maximum_upper_threshold": maximum_upper,
    }


def _facility_kpi_deviation(
    facility_report,
):
    """
    Return energy and water percentage deviations for portfolio
    review.

    These values are ranking aids for visibility only. They do not
    create or replace anomaly classifications.
    """
    facility = (
        facility_report.get("facility")
        or {}
    )

    realtime = (
        facility_report.get("realtime")
        or {}
    )

    data = (
        realtime.get("data")
        or {}
    )

    energy_actual = _num(
        data.get("energy_kwh"),
        None,
    )

    energy_expected = _num(
        data.get("expected_energy_kwh"),
        None,
    )

    water_actual = _num(
        data.get("water_kl"),
        None,
    )

    water_expected = _num(
        data.get("expected_water_kl"),
        None,
    )

    return {
        "facility_code": _text(
            facility.get("facility_code")
        ),
        "facility_name": _text(
            facility.get("facility_name")
            or facility.get("facility_code")
        ),
        "energy_actual": energy_actual,
        "energy_expected": energy_expected,
        "energy_variance": _safe_difference(
            energy_actual,
            energy_expected,
        ),
        "energy_percent": _safe_percentage(
            energy_actual,
            energy_expected,
        ),
        "water_actual": water_actual,
        "water_expected": water_expected,
        "water_variance": _safe_difference(
            water_actual,
            water_expected,
        ),
        "water_percent": _safe_percentage(
            water_actual,
            water_expected,
        ),
        "status": _normalized_facility_status(
            realtime,
            facility,
        ),
    }


def _portfolio_health_counts(facilities):
    """
    Count facility display states from realtime detection.

    This produces a transparent portfolio health summary without
    making any evaluative recommendation.
    """
    counts = {
        "Healthy": 0,
        "Attention": 0,
        "Critical": 0,
    }

    for facility_report in facilities or []:
        facility = (
            facility_report.get("facility")
            or {}
        )

        realtime = (
            facility_report.get("realtime")
            or {}
        )

        status = _normalized_facility_status(
            realtime,
            facility,
        )

        if status not in counts:
            status = "Healthy"

        counts[status] += 1

    return counts


def _portfolio_attention_rows(facilities):
    """
    Build rows for the small portfolio attention/critical table.

    Only realtime detection evidence is included here. KPI variance
    alone does not place a facility into this table.
    """
    rows = []

    for facility_report in facilities or []:
        facility = (
            facility_report.get("facility")
            or {}
        )

        realtime = (
            facility_report.get("realtime")
            or {}
        )

        status = _normalized_facility_status(
            realtime,
            facility,
        )

        if status == "Healthy":
            continue

        primary = _extract_primary_anomaly(
            realtime
        ) or {}

        rows.append({
            "facility_code": _text(
                facility.get("facility_code")
            ),
            "facility_name": _text(
                facility.get("facility_name")
                or facility.get("facility_code")
            ),
            "status": status,
            "anomaly_type": _text(
                primary.get("anomaly_type"),
                "Realtime condition",
            ),
            "severity": _text(
                primary.get("severity"),
                status,
            ),
            "confidence": primary.get(
                "confidence_percent"
            ),
            "source": _text(
                primary.get("likely_source")
                or primary.get("source")
            ),
            "area": _text(
                primary.get("area_name")
            ),
            "description": _text(
                primary.get("description")
            ),
        })

    return rows


def _top_kpi_deviation_rows(
    facilities,
    resource,
    limit=5,
):
    """
    Return the largest positive target deviations for a resource.

    This is deliberately labelled as KPI deviation and is not an
    anomaly detector.
    """
    values = []

    for facility_report in facilities or []:
        deviation = _facility_kpi_deviation(
            facility_report
        )

        if resource == "energy":
            percentage = deviation[
                "energy_percent"
            ]
            actual = deviation[
                "energy_actual"
            ]
            expected = deviation[
                "energy_expected"
            ]
        else:
            percentage = deviation[
                "water_percent"
            ]
            actual = deviation[
                "water_actual"
            ]
            expected = deviation[
                "water_expected"
            ]

        if percentage is None:
            continue

        if percentage <= 0:
            continue

        values.append({
            "facility_code": deviation[
                "facility_code"
            ],
            "facility_name": deviation[
                "facility_name"
            ],
            "actual": actual,
            "expected": expected,
            "percentage": percentage,
            "status": deviation[
                "status"
            ],
        })

    values.sort(
        key=lambda item: item["percentage"],
        reverse=True,
    )

    return values[:limit]


def _render_status_note(
    story,
    small_style,
    realtime,
):
    """
    Add the explicit detection-status explanation to a report.
    """
    story.append(
        Paragraph(
            f"<b>Detection status:</b> "
            f"{_detection_status_text(realtime)}",
            small_style,
        )
    )


def _render_target_baseline_summary(
    story,
    heading_style,
    body_style,
    small_style,
    facility,
    energy,
    water,
    realtime_data,
):
    """
    Add a compact comparison before the original full baseline
    tables.

    Facility targets and configured hourly baselines remain visibly
    separate.
    """
    energy_target = _num(
        realtime_data.get(
            "expected_energy_kwh"
        ),
        _num(
            facility.get(
                "expected_energy_kwh"
            ),
            None,
        ),
    )

    water_target = _num(
        realtime_data.get(
            "expected_water_kl"
        ),
        _num(
            facility.get(
                "expected_water_kl"
            ),
            None,
        ),
    )

    energy_summary = _baseline_summary(
        energy.get("baselines") or [],
        "Energy",
        "kWh",
    )

    water_summary = _baseline_summary(
        water.get("baselines") or [],
        "Water",
        "kL",
    )

    story.append(
        Paragraph(
            "Target vs Configured Baseline",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "Facility targets are the current comparison values "
            "shown with realtime telemetry. Configured hourly "
            "baselines are the stored weekly operating profile "
            "used for contextual detection. They are not the same "
            "metric.",
            body_style,
        )
    )

    rows = [
        [
            "Resource",
            "Facility Target",
            "Configured Avg.",
            "Configured Range",
            "Baseline Records",
        ],
        [
            "Energy",
            (
                f"{_fmt(energy_target)} kWh"
                if energy_target is not None
                else "N/A"
            ),
            (
                f"{_fmt(energy_summary['average_expected'])} kWh"
                if energy_summary["average_expected"]
                is not None
                else "N/A"
            ),
            (
                f"{_fmt(energy_summary['minimum_expected'])}–"
                f"{_fmt(energy_summary['maximum_expected'])} kWh"
                if (
                    energy_summary["minimum_expected"]
                    is not None
                    and energy_summary["maximum_expected"]
                    is not None
                )
                else "N/A"
            ),
            str(
                energy_summary["record_count"]
            ),
        ],
        [
            "Water",
            (
                f"{_fmt(water_target)} kL"
                if water_target is not None
                else "N/A"
            ),
            (
                f"{_fmt(water_summary['average_expected'])} kL"
                if water_summary["average_expected"]
                is not None
                else "N/A"
            ),
            (
                f"{_fmt(water_summary['minimum_expected'])}–"
                f"{_fmt(water_summary['maximum_expected'])} kL"
                if (
                    water_summary["minimum_expected"]
                    is not None
                    and water_summary["maximum_expected"]
                    is not None
                )
                else "N/A"
            ),
            str(
                water_summary["record_count"]
            ),
        ],
    ]

    story.append(
        _table(
            rows,
            widths=[
                28 * mm,
                33 * mm,
                36 * mm,
                43 * mm,
                25 * mm,
            ],
        )
    )

    story.append(
        Paragraph(
            "Interpretation: a difference from the facility target "
            "is a KPI variance. It is not treated as a physical loss "
            "unless the reconciliation or detection pipeline provides "
            "authoritative loss evidence.",
            small_style,
        )
    )


def _render_portfolio_health_summary(
    story,
    heading_style,
    body_style,
    small_style,
    facilities,
):
    """
    Add the portfolio-level health view before the full current
    status table.
    """
    counts = _portfolio_health_counts(
        facilities
    )

    total = len(
        facilities or []
    )

    story.append(
        Paragraph(
            "2. Portfolio Health Summary",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "The following counts describe the latest realtime "
            "detection state of each facility. They are not a ranking "
            "of facilities and do not replace persisted database "
            "records.",
            body_style,
        )
    )

    health_rows = [
        [
            "Healthy",
            "Attention",
            "Critical",
            "Realtime Anomalies",
        ],
        [
            str(counts["Healthy"]),
            str(counts["Attention"]),
            str(counts["Critical"]),
            str(
                counts["Attention"]
                + counts["Critical"]
            ),
        ],
    ]

    story.append(
        _table(
            health_rows,
            widths=[
                38 * mm,
                38 * mm,
                38 * mm,
                46 * mm,
            ],
        )
    )

    story.append(
        Paragraph(
            f"Facilities represented: <b>{total}</b>. "
            f"Realtime snapshots are evaluated independently from "
            f"persisted anomaly and alert records.",
            small_style,
        )
    )


def _render_portfolio_attention_table(
    story,
    heading_style,
    body_style,
    small_style,
    facilities,
):
    """
    Surface all realtime Attention/Critical facilities near the
    beginning of the portfolio report.
    """
    rows = _portfolio_attention_rows(
        facilities
    )

    story.append(
        Paragraph(
            "3. Critical & Attention Facilities",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "Only facilities with an active realtime detection "
            "condition are listed here. A target variance alone does "
            "not move a facility into this table.",
            body_style,
        )
    )

    if not rows:
        story.append(
            Paragraph(
                "No realtime Attention or Critical facilities "
                "were present in this snapshot.",
                body_style,
            )
        )
        return

    table_rows = [
        [
            "Facility",
            "Status",
            "Anomaly",
            "Severity",
            "Confidence",
            "Source / Area",
        ]
    ]

    for item in rows:
        source_area = (
            f"{item['source']} / {item['area']}"
            if (
                item["source"] != "N/A"
                or item["area"] != "N/A"
            )
            else "N/A"
        )

        confidence = item[
            "confidence"
        ]

        table_rows.append([
            (
                f"<b>{item['facility_code']}</b><br/>"
                f"{item['facility_name']}"
            ),
            item["status"],
            item["anomaly_type"],
            item["severity"],
            (
                f"{_fmt(confidence, 1)} %"
                if confidence is not None
                else "N/A"
            ),
            source_area,
        ])

    story.append(
        _table(
            table_rows,
            widths=[
                38 * mm,
                25 * mm,
                31 * mm,
                24 * mm,
                25 * mm,
                37 * mm,
            ],
        )
    )

    story.append(
        Paragraph(
            "Detection details shown here come directly from the "
            "latest realtime detection payload.",
            small_style,
        )
    )


def _render_portfolio_kpi_deviations(
    story,
    heading_style,
    body_style,
    small_style,
    facilities,
):
    """
    Add a transparent KPI-deviation section. This is deliberately
    separate from anomaly classification.
    """
    story.append(
        Paragraph(
            "4. Top KPI Deviations",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "These are positive differences from the configured "
            "facility target in the latest realtime snapshot. "
            "They are informational and should not be interpreted "
            "as detected anomalies unless the detection engine "
            "reports one.",
            body_style,
        )
    )

    energy_rows = [
        [
            "Facility",
            "Actual kWh",
            "Target kWh",
            "Deviation",
            "Detection Status",
        ]
    ]

    for item in _top_kpi_deviation_rows(
        facilities,
        "energy",
        5,
    ):
        energy_rows.append([
            item["facility_code"],
            _fmt(item["actual"]),
            _fmt(item["expected"]),
            f"{_fmt(item['percentage'], 1)} %",
            item["status"],
        ])

    water_rows = [
        [
            "Facility",
            "Actual kL",
            "Target kL",
            "Deviation",
            "Detection Status",
        ]
    ]

    for item in _top_kpi_deviation_rows(
        facilities,
        "water",
        5,
    ):
        water_rows.append([
            item["facility_code"],
            _fmt(item["actual"]),
            _fmt(item["expected"]),
            f"{_fmt(item['percentage'], 1)} %",
            item["status"],
        ])

    if len(energy_rows) == 1:
        energy_rows.append([
            "No positive deviation",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ])

    if len(water_rows) == 1:
        water_rows.append([
            "No positive deviation",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ])

    story.append(
        Paragraph(
            "Energy",
            small_style,
        )
    )

    story.append(
        _table(
            energy_rows,
            widths=[
                34 * mm,
                28 * mm,
                28 * mm,
                30 * mm,
                40 * mm,
            ],
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Water",
            small_style,
        )
    )

    story.append(
        _table(
            water_rows,
            widths=[
                34 * mm,
                28 * mm,
                28 * mm,
                30 * mm,
                40 * mm,
            ],
        )
    )


def _render_facility_detection_card(
    story,
    heading_style,
    body_style,
    small_style,
    realtime,
):
    """
    Add a dedicated realtime detection section to the individual
    facility report.
    """
    status = _normalized_facility_status(
        realtime
    )

    primary = _extract_primary_anomaly(
        realtime
    )

    story.append(
        Paragraph(
            "Realtime Detection Status",
            heading_style,
        )
    )

    if not primary:
        story.append(
            Paragraph(
                "<b>Healthy / No Realtime Anomaly Detected</b>",
                body_style,
            )
        )

        story.append(
            Paragraph(
                "Current KPI differences remain visible in the "
                "performance section as informational variance. "
                "The latest FlowSense detection payload reports no "
                "realtime anomaly for this snapshot.",
                small_style,
            )
        )

        return

    rows = [
        [
            "Field",
            "Realtime Detection Evidence",
        ],
        [
            "Facility Status",
            status,
        ],
        [
            "Anomaly Type",
            _text(
                primary.get(
                    "anomaly_type"
                ),
                "Realtime condition",
            ),
        ],
        [
            "Severity",
            _text(
                primary.get(
                    "severity"
                ),
                status,
            ),
        ],
        [
            "Confidence",
            (
                f"{_fmt(primary.get('confidence_percent'), 1)} %"
                if primary.get(
                    "confidence_percent"
                ) is not None
                else "N/A"
            ),
        ],
        [
            "Likely Source",
            _text(
                primary.get("likely_source")
                or primary.get("source")
            ),
        ],
        [
            "Area",
            _text(
                primary.get(
                    "area_name"
                )
            ),
        ],
        [
            "Description",
            _text(
                primary.get(
                    "description"
                )
            ),
        ],
    ]

    story.append(
        _table(
            rows,
            widths=[
                50 * mm,
                105 * mm,
            ],
        )
    )

    story.append(
        Paragraph(
            "This status is derived from the realtime detection "
            "payload and is separate from persisted PostgreSQL "
            "anomaly records.",
            small_style,
        )
    )


# ============================================================
# PDF GENERATOR
# ============================================================

def generate_facility_pdf(report):
    """
    Generate a PDF from the report data returned by
    build_facility_report_data().
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="FlowSense Facility Report",
        author="FlowSense",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#667085"),
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor("#101828"),
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=14,
        spaceAfter=6,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#667085"),
    )

    story = []

    metadata = report.get("report_metadata", {})
    facility = report.get("facility", {})
    snapshot = report.get("current_snapshot", {})
    realtime = report.get("realtime") or {}

    realtime_data = realtime.get("data") or {}
    detection = realtime.get("detection") or {}
    efficiency = detection.get("efficiency") or {}

    energy = report.get("energy") or {}
    water = report.get("water") or {}

    anomalies = report.get("anomalies") or []
    alerts = report.get("alerts") or []
    devices = report.get("devices") or []
    sensors = report.get("sensors") or []

    # ========================================================
    # COVER
    # ========================================================

    story.append(Spacer(1, 25 * mm))

    story.append(
        Paragraph(
            "FlowSense",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Energy & Water Intelligence Report",
            ParagraphStyle(
                "MainTitle",
                parent=title_style,
                fontSize=18,
                leading=23,
            ),
        )
    )

    story.append(
        Paragraph(
            _text(facility.get("facility_name")),
            ParagraphStyle(
                "FacilityTitle",
                parent=title_style,
                fontSize=15,
                leading=20,
            ),
        )
    )

    story.append(
        Paragraph(
            f"{_text(facility.get('facility_code'))} • "
            f"{_text(facility.get('city'))}, "
            f"{_text(facility.get('state'))}",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 10 * mm))

    metadata_table = [
        ["Report Period", _text(metadata.get("period"))],
        [
            "From",
            _format_timestamp(metadata.get("start")),
        ],
        [
            "To",
            _format_timestamp(metadata.get("end")),
        ],
        [
            "Generated",
            _format_timestamp(metadata.get("generated_at")),
        ],
        [
            "Realtime Data",
            "Available"
            if metadata.get("realtime_available")
            else "Unavailable",
        ],
    ]

    story.append(
        _table(
            metadata_table,
            widths=[50 * mm, 105 * mm],
            header=False,
        )
    )

    story.append(Spacer(1, 12 * mm))

    story.append(
        Paragraph(
            "This report is generated from FlowSense measured "
            "telemetry, configured baselines, reconciliation "
            "records, anomaly records and connected IoT metadata. "
            "Values are not hardcoded.",
            body_style,
        )
    )

    story.append(PageBreak())

    # ========================================================
    # FACILITY OVERVIEW
    # ========================================================

    story.append(
        Paragraph(
            "1. Facility Overview",
            heading_style,
        )
    )

    facility_table = [
        ["Field", "Value"],
        ["Facility", _text(facility.get("facility_name"))],
        ["Code", _text(facility.get("facility_code"))],
        ["Type", _text(facility.get("facility_type"))],
        ["City", _text(facility.get("city"))],
        ["State", _text(facility.get("state"))],
        ["Country", _text(facility.get("country"))],
        [
            "Area",
            f"{_fmt(facility.get('area_sq_m'), 0)} sq m",
        ],
        ["Status", _text(facility.get("status"))],
    ]

    story.append(
        _table(
            facility_table,
            widths=[50 * mm, 105 * mm],
        )
    )

    story.append(
        Paragraph(
            "Latest Persisted System Reading",
            heading_style,
        )
    )

    latest_energy = snapshot.get("latest_energy") or {}
    latest_water = snapshot.get("latest_water") or {}

    snapshot_table = [
        ["Metric", "Latest Value", "Reading Time"],
        [
            "Energy",
            f"{_fmt(latest_energy.get('value'))} kWh",
            _format_timestamp(
                latest_energy.get("reading_time")
            ),
        ],
        [
            "Water",
            f"{_fmt(latest_water.get('value'))} kL",
            _format_timestamp(
                latest_water.get("reading_time")
            ),
        ],
        [
            "IoT Devices",
            str(len(devices)),
            _text(snapshot.get("latest_device_seen")),
        ],
    ]

    story.append(
        Paragraph(
            "This section shows the latest reading available in the historical PostgreSQL dataset; it is separate from the live telemetry shown below.",
            small_style,
        )
    )

    story.append(
        _table(
            snapshot_table,
            widths=[45 * mm, 45 * mm, 65 * mm],
        )
    )

    # ========================================================
    # REALTIME PERFORMANCE
    # ========================================================

    story.append(
        Paragraph(
            "2. Latest Realtime Performance",
            heading_style,
        )
    )

    energy_actual = _num(
        realtime_data.get("energy_kwh")
    )
    energy_expected = _num(
        realtime_data.get("expected_energy_kwh")
    )

    water_actual = _num(
        realtime_data.get("water_kl")
    )
    water_expected = _num(
        realtime_data.get("expected_water_kl")
    )

    # --------------------------------------------------------
    # Realtime variance and loss
    #
    # Variance = Actual - Expected.
    # Positive variance means consumption is above expected.
    # Negative variance means consumption is below expected.
    #
    # Authoritative loss remains the value supplied by the FlowSense
    # detection/reconciliation pipeline. A positive target variance
    # is reported as excess consumption/variance when no authoritative
    # physical-loss value is supplied.
    # --------------------------------------------------------

    energy_pipeline_loss = realtime_data.get(
        "estimated_energy_loss_kwh"
    )

    water_pipeline_loss = realtime_data.get(
        "estimated_water_loss_kl"
    )

    energy_variance = _safe_difference(
        energy_actual,
        energy_expected,
    )

    water_variance = _safe_difference(
        water_actual,
        water_expected,
    )

    energy_loss_display = (
        _loss_or_variance_display(
            realtime_data,
            energy_actual,
            energy_expected,
            "energy",
        )
    )

    water_loss_display = (
        _loss_or_variance_display(
            realtime_data,
            water_actual,
            water_expected,
            "water",
        )
    )

    realtime_table = [
        [
            "Metric",
            "Actual",
            "Expected",
            "Variance",
            "Loss / Variance Evidence",
        ],
        [
            "Energy",
            f"{_fmt(energy_actual)} kWh",
            f"{_fmt(energy_expected)} kWh",
            _format_variance(
                energy_variance,
                "kWh",
            ),
            (
                f"{energy_loss_display[0]} "
                f"({energy_loss_display[1]})"
            ),
        ],
        [
            "Water",
            f"{_fmt(water_actual)} kL",
            f"{_fmt(water_expected)} kL",
            _format_variance(
                water_variance,
                "kL",
            ),
            (
                f"{water_loss_display[0]} "
                f"({water_loss_display[1]})"
            ),
        ],
    ]

    story.append(
        Paragraph(
            "The realtime section represents the latest live telemetry snapshot and is independent of the selected historical reporting period.",
            small_style,
        )
    )

    story.append(
        _table(
            realtime_table,
            widths=[
                29 * mm,
                30 * mm,
                30 * mm,
                32 * mm,
                34 * mm,
            ],
        )
    )

    efficiency_table = [
        ["Efficiency Metric", "Score"],
        [
            "Energy Efficiency",
            _fmt(
                efficiency.get("energy_score"),
                1,
            ),
        ],
        [
            "Water Efficiency",
            _fmt(
                efficiency.get("water_score"),
                1,
            ),
        ],
        [
            "Facility Status",
            _text(
                detection.get(
                    "facility_status"
                )
            ),
        ],
    ]

    story.append(Spacer(1, 5 * mm))

    story.append(
        _table(
            efficiency_table,
            widths=[100 * mm, 55 * mm],
        )
    )

    story.append(
        Paragraph(
            f"Realtime snapshot timestamp: "
            f"{_format_timestamp(realtime.get('timestamp'))}",
            small_style,
        )
    )

    _render_facility_detection_card(
        story,
        heading_style,
        body_style,
        small_style,
        realtime,
    )

    # ========================================================
    # OPERATING CONDITIONS
    # ========================================================

    story.append(
        Paragraph(
            "3. Operating Conditions",
            heading_style,
        )
    )

    conditions_table = [
        ["Parameter", "Value"],
        [
            "Power",
            f"{_fmt(realtime_data.get('power_kw'))} kW",
        ],
        [
            "Water Flow",
            f"{_fmt(realtime_data.get('water_flow_lpm'))} L/min",
        ],
        [
            "Water Pressure",
            f"{_fmt(realtime_data.get('water_pressure_bar'))} bar",
        ],
        [
            "Temperature",
            f"{_fmt(realtime_data.get('temperature_c'))} °C",
        ],
        [
            "Humidity",
            f"{_fmt(realtime_data.get('humidity_percent'))} %",
        ],
        [
            "Vibration",
            f"{_fmt(realtime_data.get('vibration_mm_s'))} mm/s",
        ],
        [
            "Leak Detected",
            "Yes"
            if realtime_data.get("leak_detected")
            else "No",
        ],
        [
            "Treatment Rate",
            f"{_fmt(realtime_data.get('treatment_rate'), 1)} %",
        ],
        [
            "Reuse Rate",
            f"{_fmt(realtime_data.get('reuse_rate'), 1)} %",
        ],
    ]

    story.append(
        _table(
            conditions_table,
            widths=[70 * mm, 85 * mm],
        )
    )

    story.append(Spacer(1, 3 * mm))

    _render_status_note(
        story,
        small_style,
        realtime,
    )

    # ========================================================
    # ANOMALIES / ALERTS
    # ========================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "4. Persisted Anomalies & Alerts",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            f"Persisted anomalies recorded in the selected reporting period: "
            f"<b>{len(anomalies)}</b>",
            body_style,
        )
    )

    if anomalies:
        anomaly_rows = [
            [
                "Detected",
                "Type",
                "Severity",
                "Resource",
                "Loss",
            ]
        ]

        for item in anomalies[:30]:
            anomaly_rows.append([
                _format_timestamp(
                    item.get("detected_at")
                ),
                _text(
                    item.get("anomaly_type")
                ),
                _text(
                    item.get("severity")
                ),
                _text(
                    item.get("resource_type")
                ),
                (
                    f"{_fmt(item.get('estimated_loss'))} "
                    f"{_text(item.get('loss_unit'), '')}"
                ),
            ])

        story.append(
            _table(
                anomaly_rows,
                widths=[
                    31 * mm,
                    40 * mm,
                    25 * mm,
                    25 * mm,
                    34 * mm,
                ],
            )
        )
    else:
        story.append(
            Paragraph(
                "No persisted anomalies were recorded "
                "for the selected reporting period.",
                body_style,
            )
        )

    story.append(
        Paragraph(
            f"Persisted alerts recorded in the selected reporting period: "
            f"<b>{len(alerts)}</b>",
            body_style,
        )
    )

    if alerts:
        alert_rows = [
            [
                "Triggered",
                "Title",
                "Severity",
                "Status",
            ]
        ]

        for item in alerts[:30]:
            alert_rows.append([
                _format_timestamp(
                    item.get("triggered_at")
                ),
                _text(item.get("alert_title")),
                _text(item.get("severity")),
                _text(item.get("status")),
            ])

        story.append(
            _table(
                alert_rows,
                widths=[
                    35 * mm,
                    70 * mm,
                    25 * mm,
                    25 * mm,
                ],
            )
        )

    # ========================================================
    # HISTORICAL DATA AVAILABILITY
    # ========================================================

    story.append(
        Paragraph(
            "5. Historical Data Availability",
            heading_style,
        )
    )

    energy_readings = energy.get("readings") or []
    water_readings = water.get("readings") or []
    reconciliation = report.get("reconciliation") or []
    monthly_summaries = report.get("monthly_summaries") or []

    if energy_readings or water_readings:
        historical_message = (
            "Historical consumption records are available for the selected "
            "reporting period. Historical values are presented from the "
            "configured PostgreSQL data store."
        )
    else:
        historical_message = (
            "Historical energy and water consumption records were not available "
            "for the selected reporting period. Realtime telemetry and configured "
            "baseline information are shown separately. No historical consumption "
            "totals have been inferred or fabricated."
        )

    story.append(
        Paragraph(
            historical_message,
            body_style,
        )
    )

    story.append(
        Paragraph(
            f"Historical energy readings: <b>{len(energy_readings)}</b><br/>"
            f"Historical water readings: <b>{len(water_readings)}</b><br/>"
            f"Reconciliation records: <b>{len(reconciliation)}</b><br/>"
            f"Monthly summary records: <b>{len(monthly_summaries)}</b>",
            body_style,
        )
    )

    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            "Realtime detection results are reported separately and are not "
            "counted as persisted anomalies or alerts unless they are stored "
            "in the corresponding database records.",
            small_style,
        )
    )

    # ========================================================
    # BASELINES
    # ========================================================

    story.append(
        Paragraph(
            "6. Configured Consumption Baselines",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "The summary below is the operational baseline context. "
            "The complete 168-row weekly profile is retained for audit/reference and "
            "does not represent additional readings from the selected 24h period.",
            small_style,
        )
    )

    energy_baselines = energy.get("baselines") or []
    water_baselines = water.get("baselines") or []

    _render_target_baseline_summary(
        story,
        heading_style,
        body_style,
        small_style,
        facility,
        energy,
        water,
        realtime_data,
    )

    story.append(
        Paragraph(
            f"Configured energy baseline records: "
            f"<b>{len(energy_baselines)}</b>",
            body_style,
        )
    )

    if energy_baselines:
        story.append(
            Paragraph(
                "The configured baseline represents a weekly hourly profile "
                "(24 hours × 7 days). These records describe expected operating "
                "levels and thresholds and are not restricted to the selected "
                "reporting period.",
                small_style,
            )
        )

        story.append(
            Paragraph(
                "Baseline values provide operating context. They do not "
                "automatically create a physical-loss value.",
                small_style,
            )
        )

        rows = [
            [
                "Hour",
                "Day",
                "Expected kWh",
                "Lower",
                "Upper",
            ]
        ]

        for item in energy_baselines:
            rows.append([
                str(item.get("hour_of_day")),
                str(item.get("day_of_week")),
                _fmt(item.get("expected_value")),
                _fmt(item.get("lower_threshold")),
                _fmt(item.get("upper_threshold")),
            ])

        story.append(
            _table(
                rows,
                widths=[
                    22 * mm,
                    22 * mm,
                    37 * mm,
                    37 * mm,
                    37 * mm,
                ],
            )
        )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            f"Configured water baseline records: "
            f"<b>{len(water_baselines)}</b>",
            body_style,
        )
    )

    if water_baselines:
        rows = [
            [
                "Hour",
                "Day",
                "Expected kL",
                "Lower",
                "Upper",
            ]
        ]

        for item in water_baselines:
            rows.append([
                str(item.get("hour_of_day")),
                str(item.get("day_of_week")),
                _fmt(item.get("expected_value")),
                _fmt(item.get("lower_threshold")),
                _fmt(item.get("upper_threshold")),
            ])

        story.append(
            _table(
                rows,
                widths=[
                    22 * mm,
                    22 * mm,
                    37 * mm,
                    37 * mm,
                    37 * mm,
                ],
            )
        )

    # ========================================================
    # DEVICES AND SENSORS
    # ========================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "7. IoT Infrastructure",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            f"Connected devices: <b>{len(devices)}</b>",
            body_style,
        )
    )

    if devices:
        rows = [
            [
                "Device",
                "Model",
                "Protocol",
                "Status",
            ]
        ]

        for item in devices:
            rows.append([
                _text(item.get("device_name")),
                _text(item.get("device_model")),
                _text(
                    item.get(
                        "communication_protocol"
                    )
                ),
                _text(item.get("status")),
            ])

        story.append(
            _table(
                rows,
                widths=[
                    55 * mm,
                    35 * mm,
                    35 * mm,
                    30 * mm,
                ],
            )
        )

    story.append(
        Paragraph(
            f"Sensors registered: <b>{len(sensors)}</b>",
            body_style,
        )
    )

    if sensors:
        rows = [
            [
                "Sensor",
                "Measurement",
                "Type",
                "Unit",
            ]
        ]

        for item in sensors[:40]:
            rows.append([
                _text(item.get("sensor_name")),
                _text(item.get("measurement")),
                _text(item.get("sensor_type")),
                _text(item.get("unit")),
            ])

        story.append(
            _table(
                rows,
                widths=[
                    52 * mm,
                    48 * mm,
                    35 * mm,
                    20 * mm,
                ],
            )
        )

    # ========================================================
    # DATA QUALITY / ASSUMPTIONS
    # ========================================================

    story.append(
        Paragraph(
            "8. Data Quality & Calculation Notes",
            heading_style,
        )
    )

    notes = [
        "Historical readings are sourced from the configured PostgreSQL data store.",
        "The realtime section uses the latest live telemetry received by the FlowSense backend and is independent of the selected historical reporting period.",
        "The latest persisted system reading is the newest reading available in the historical PostgreSQL dataset and may have an earlier timestamp than the live telemetry.",
        "Configured consumption baselines are presented as stored in the database and represent the configured weekly hourly profile.",
        "Persisted anomaly and alert sections only report database records available for the selected period; realtime detections are reported separately.",
        "Missing historical records are not replaced with fabricated values.",
        "Efficiency values shown in the realtime section originate from the FlowSense detection pipeline.",
        "Authoritative estimated losses are shown only when supplied by the live detection/reconciliation pipeline. A zero authoritative value is shown as no loss evidence; positive actual-versus-expected differences without authoritative loss evidence are labelled variance/excess consumption rather than physical loss.",
        "Facility targets and configured weekly hourly baselines are shown separately because they serve different reporting purposes.",
        "Realtime KPI deviation is not converted into a realtime anomaly unless the FlowSense detection payload reports an anomaly.",
    ]

    for note in notes:
        story.append(
            Paragraph(
                f"• {note}",
                body_style,
            )
        )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Report generation completed successfully from the "
            "available FlowSense data package.",
            body_style,
        )
    )

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)
    return buffer


# ============================================================
# PORTFOLIO / ALL-FACILITIES PDF GENERATOR
# ============================================================

def generate_portfolio_pdf(report):
    """
    Generate an all-facilities portfolio PDF from the report data
    returned by build_portfolio_report_data().

    The generator does not create or infer telemetry values.
    Each facility row is rendered from its authoritative report
    package and, when available, its latest realtime snapshot.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="FlowSense Portfolio Report",
        author="FlowSense",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PortfolioReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "PortfolioReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#667085"),
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "PortfolioSectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor("#101828"),
    )

    body_style = ParagraphStyle(
        "PortfolioBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=14,
        spaceAfter=6,
    )

    small_style = ParagraphStyle(
        "PortfolioSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#667085"),
    )

    story = []

    metadata = report.get("report_metadata") or {}
    facilities = report.get("facilities") or []

    # ========================================================
    # PORTFOLIO COUNTS
    # ========================================================

    realtime_count = 0
    realtime_anomaly_count = 0
    persisted_anomaly_count = 0
    alert_count = 0
    data_error_count = 0

    for facility_report in facilities:
        if facility_report.get("data_error"):
            data_error_count += 1

        realtime = facility_report.get("realtime") or {}

        if realtime:
            realtime_count += 1

            detection = realtime.get("detection") or {}

            realtime_anomaly_count += int(
                _num(
                    detection.get(
                        "anomaly_count"
                    ),
                    0,
                )
            )

        persisted_anomaly_count += len(
            facility_report.get("anomalies") or []
        )

        alert_count += len(
            facility_report.get("alerts") or []
        )

    # ========================================================
    # COVER
    # ========================================================

    story.append(Spacer(1, 25 * mm))

    story.append(
        Paragraph(
            "FlowSense",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Portfolio & All-Facilities Report",
            ParagraphStyle(
                "PortfolioMainTitle",
                parent=title_style,
                fontSize=18,
                leading=23,
            ),
        )
    )

    story.append(
        Paragraph(
            "Energy & Water Intelligence",
            ParagraphStyle(
                "PortfolioSubtitleTitle",
                parent=title_style,
                fontSize=15,
                leading=20,
            ),
        )
    )

    story.append(
        Paragraph(
            f"{_text(metadata.get('scope'), 'all_facilities').replace('_', ' ').title()} "
            f"• {_text(metadata.get('facility_count'), len(facilities))} facilities",
            subtitle_style,
        )
    )

    metadata_table = [
        [
            "Report Period",
            _text(metadata.get("period")),
        ],
        [
            "From",
            _format_timestamp(
                metadata.get("start")
                or metadata.get("period_start")
            ),
        ],
        [
            "To",
            _format_timestamp(
                metadata.get("end")
                or metadata.get("period_end")
            ),
        ],
        [
            "Generated",
            _format_timestamp(
                metadata.get("generated_at")
            ),
        ],
        [
            "Facilities",
            str(len(facilities)),
        ],
        [
            "Realtime Snapshots",
            f"{realtime_count} / {len(facilities)}",
        ],
    ]

    story.append(
        _table(
            metadata_table,
            widths=[55 * mm, 100 * mm],
            header=False,
        )
    )

    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            "This portfolio report consolidates the real FlowSense "
            "report packages for all active facilities. Facility-level "
            "values are kept separate so that readings are not "
            "artificially aggregated or fabricated.",
            body_style,
        )
    )

    story.append(
        Paragraph(
            "Snapshot note: the realtime portfolio table represents "
            "the latest available snapshot captured when this PDF "
            "was generated. It is not a frozen historical dataset.",
            small_style,
        )
    )

    story.append(PageBreak())

    # ========================================================
    # PORTFOLIO SUMMARY
    # ========================================================

    story.append(
        Paragraph(
            "1. Portfolio Summary",
            heading_style,
        )
    )

    summary_table = [
        ["Metric", "Count"],
        [
            "Active facilities in report",
            str(len(facilities)),
        ],
        [
            "Facilities with realtime snapshot",
            str(realtime_count),
        ],
        [
            "Realtime anomaly count",
            str(realtime_anomaly_count),
        ],
        [
            "Persisted anomalies in period",
            str(persisted_anomaly_count),
        ],
        [
            "Persisted alerts in period",
            str(alert_count),
        ],
        [
            "Facilities with report data errors",
            str(data_error_count),
        ],
    ]

    story.append(
        _table(
            summary_table,
            widths=[115 * mm, 40 * mm],
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Realtime anomaly counts come from the latest live "
            "detection snapshot for each facility. Persisted anomaly "
            "and alert counts come from PostgreSQL records within "
            "the selected reporting period.",
            small_style,
        )
    )

    _render_portfolio_health_summary(
        story,
        heading_style,
        body_style,
        small_style,
        facilities,
    )

    _render_portfolio_attention_table(
        story,
        heading_style,
        body_style,
        small_style,
        facilities,
    )

    _render_portfolio_kpi_deviations(
        story,
        heading_style,
        body_style,
        small_style,
        facilities,
    )

    # ========================================================
    # ALL-FACILITIES TABLE
    # ========================================================

    story.append(
        Paragraph(
            "5. All-Facilities Current Status",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "The following table provides a facility-by-facility "
            "view of the latest available realtime telemetry. "
            "N/A indicates that a value was not available in the "
            "underlying report package.",
            body_style,
        )
    )

    facility_rows = [
        [
            "Facility",
            "Status",
            "Energy",
            "Water",
            "Anomalies",
        ]
    ]

    for facility_report in facilities:
        facility = facility_report.get("facility") or {}
        realtime = facility_report.get("realtime") or {}
        realtime_data = realtime.get("data") or {}
        detection = realtime.get("detection") or {}

        facility_name = _text(
            facility.get("facility_name")
            or facility.get("facility_code")
        )

        facility_code = _text(
            facility.get("facility_code")
        )

        status = _normalized_facility_status(
            realtime,
            facility,
        )

        energy_value = realtime_data.get(
            "energy_kwh"
        )
        water_value = realtime_data.get(
            "water_kl"
        )

        anomaly_count = detection.get(
            "anomaly_count"
        )

        if anomaly_count is None:
            anomaly_count = (
                1
                if _extract_primary_anomaly(
                    realtime
                )
                else 0
            )

        facility_rows.append([
            Paragraph(
                f"<b>{facility_name}</b><br/>"
                f"{facility_code}",
                small_style,
            ),
            status,
            (
                f"{_fmt(energy_value)} kWh"
                if energy_value is not None
                else "N/A"
            ),
            (
                f"{_fmt(water_value)} kL"
                if water_value is not None
                else "N/A"
            ),
            (
                str(int(_num(anomaly_count, 0)))
                if anomaly_count is not None
                else "N/A"
            ),
        ])

    if len(facility_rows) == 1:
        facility_rows.append([
            "No facilities available",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ])

    story.append(
        _table(
            facility_rows,
            widths=[
                63 * mm,
                30 * mm,
                28 * mm,
                25 * mm,
                18 * mm,
            ],
        )
    )

    # ========================================================
    # FACILITY DETAILS
    # ========================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "6. Facility Detail",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "Each facility section below retains its own realtime "
            "metrics, efficiency scores, detection state and "
            "persisted reporting-period records.",
            body_style,
        )
    )

    for index, facility_report in enumerate(
        facilities,
        start=1,
    ):
        facility = facility_report.get("facility") or {}
        realtime = facility_report.get("realtime") or {}
        realtime_data = realtime.get("data") or {}
        detection = realtime.get("detection") or {}
        efficiency = detection.get("efficiency") or {}

        normalized_status = _normalized_facility_status(
            realtime,
            facility,
        )

        facility_name = _text(
            facility.get("facility_name")
            or facility.get("facility_code")
        )
        facility_code = _text(
            facility.get("facility_code")
        )

        story.append(
            Paragraph(
                f"{index}. {facility_name}",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                f"{facility_code} • "
                f"{_text(facility.get('facility_type'))} • "
                f"{_text(facility.get('city'))}, "
                f"{_text(facility.get('state'))}",
                small_style,
            )
        )

        if facility_report.get("data_error"):
            story.append(
                Paragraph(
                    "Report data error: "
                    f"{_text(facility_report.get('data_error'))}",
                    body_style,
                )
            )
            continue

        detail_rows = [
            [
                "Metric",
                "Value",
                "Metric",
                "Value",
            ],
            [
                "Energy",
                (
                    f"{_fmt(realtime_data.get('energy_kwh'))} kWh"
                    if realtime_data.get("energy_kwh") is not None
                    else "N/A"
                ),
                "Expected Energy",
                (
                    f"{_fmt(realtime_data.get('expected_energy_kwh'))} kWh"
                    if realtime_data.get("expected_energy_kwh") is not None
                    else "N/A"
                ),
            ],
            [
                "Water",
                (
                    f"{_fmt(realtime_data.get('water_kl'))} kL"
                    if realtime_data.get("water_kl") is not None
                    else "N/A"
                ),
                "Expected Water",
                (
                    f"{_fmt(realtime_data.get('expected_water_kl'))} kL"
                    if realtime_data.get("expected_water_kl") is not None
                    else "N/A"
                ),
            ],
            [
                "Power",
                (
                    f"{_fmt(realtime_data.get('power_kw'))} kW"
                    if realtime_data.get("power_kw") is not None
                    else "N/A"
                ),
                "Water Flow",
                (
                    f"{_fmt(realtime_data.get('water_flow_lpm'))} L/min"
                    if realtime_data.get("water_flow_lpm") is not None
                    else "N/A"
                ),
            ],
            [
                "Energy Efficiency",
                _fmt(
                    efficiency.get("energy_score"),
                    1,
                ),
                "Water Efficiency",
                _fmt(
                    efficiency.get("water_score"),
                    1,
                ),
            ],
            [
                "Facility Status",
                normalized_status,
                
                "Realtime Anomalies",
                str(
                    int(
                        _num(
                            detection.get(
                                "anomaly_count"
                            ),
                            0,
                        )
                    )
                ),
            ],
        ]

        story.append(
            _table(
                detail_rows,
                widths=[
                    37 * mm,
                    40 * mm,
                    37 * mm,
                    41 * mm,
                ],
            )
        )

        primary = (
            _extract_primary_anomaly(
                realtime
            )
            or {}
        )

        if primary:
            story.append(
                Paragraph(
                    "<b>Latest Realtime Detection</b>",
                    body_style,
                )
            )

            detection_rows = [
                ["Field", "Value"],
                [
                    "Anomaly Type",
                    _text(
                        primary.get(
                            "anomaly_type"
                        )
                    ),
                ],
                [
                    "Severity",
                    _text(
                        primary.get(
                            "severity"
                        )
                    ),
                ],
                [
                    "Source",
                    _text(
                        primary.get(
                            "likely_source"
                        )
                    ),
                ],
                [
                    "Area",
                    _text(
                        primary.get(
                            "area_name"
                        )
                    ),
                ],
                [
                    "Confidence",
                    (
                        f"{_fmt(primary.get('confidence_percent'), 1)} %"
                        if primary.get("confidence_percent") is not None
                        else "N/A"
                    ),
                ],
                [
                    "Description",
                    _text(
                        primary.get(
                            "description"
                        )
                    ),
                ],
            ]

            story.append(
                _table(
                    detection_rows,
                    widths=[50 * mm, 105 * mm],
                )
            )

        anomalies = facility_report.get(
            "anomalies"
        ) or []

        alerts = facility_report.get(
            "alerts"
        ) or []

        story.append(
            Paragraph(
                f"Persisted anomalies: <b>{len(anomalies)}</b> "
                f"• Persisted alerts: <b>{len(alerts)}</b>",
                small_style,
            )
        )

        if realtime:
            story.append(
                Paragraph(
                    "Realtime snapshot: "
                    f"{_format_timestamp(realtime.get('timestamp'))}",
                    small_style,
                )
            )

        # Keep each facility section together where possible,
        # while allowing ReportLab to split large tables.
        story.append(Spacer(1, 6 * mm))

        if index < len(facilities):
            story.append(PageBreak())

    # ========================================================
    # DATA AVAILABILITY
    # ========================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "7. Data Availability & Calculation Notes",
            heading_style,
        )
    )

    notes = [
        "The portfolio is built from the active facilities returned by the FlowSense PostgreSQL database.",
        "Facility-level historical readings, baselines, anomalies, alerts, devices and sensors are sourced from the existing report engine.",
        "Latest realtime values are included only when a live snapshot is available in the FlowSense realtime report cache.",
        "Realtime energy and water values are displayed per facility and are not summed into a portfolio total because the underlying readings represent facility-level telemetry.",
        "Missing values are displayed as N/A rather than being replaced with fabricated values.",
        "Realtime anomaly counts describe the latest live detection state and are separate from persisted database anomaly records.",
        "Persisted anomaly and alert counts are limited to the selected reporting period.",
        "The report does not infer historical totals when historical database records are unavailable.",
        "Portfolio health counts are derived from the latest realtime detection state and are not a ranking of facilities.",
        "Top KPI deviation tables are informational and do not replace the backend anomaly detector.",
        "Positive actual-versus-target variance is not labelled as physical loss unless authoritative loss evidence is present.",
        "The portfolio current-status table is a point-in-time realtime snapshot; later downloads can legitimately contain different telemetry values.",
    ]

    for note in notes:
        story.append(
            Paragraph(
                f"• {note}",
                body_style,
            )
        )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Portfolio report generation completed from the "
            "available FlowSense facility report packages.",
            body_style,
        )
    )

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)
    return buffer
