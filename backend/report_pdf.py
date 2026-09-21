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
    # Estimated loss remains the authoritative value supplied
    # by the FlowSense detection/reconciliation pipeline.
    # If the pipeline does not provide a value, a positive
    # variance is used as a fallback estimate.
    # --------------------------------------------------------

    energy_pipeline_loss = realtime_data.get(
        "estimated_energy_loss_kwh"
    )

    water_pipeline_loss = realtime_data.get(
        "estimated_water_loss_kl"
    )

    energy_variance = energy_actual - energy_expected
    water_variance = water_actual - water_expected

    if energy_pipeline_loss is None:
        energy_loss = max(0.0, energy_variance)
    else:
        energy_loss = _num(energy_pipeline_loss)

    water_loss = max(0.0, water_variance)

    realtime_table = [
        [
            "Metric",
            "Actual",
            "Expected",
            "Variance",
            "Estimated Loss",
        ],
        [
            "Energy",
            f"{_fmt(energy_actual)} kWh",
            f"{_fmt(energy_expected)} kWh",
            f"{energy_variance:+,.2f} kWh",
            f"{_fmt(energy_loss)} kWh",
        ],
        [
            "Water",
            f"{_fmt(water_actual)} kL",
            f"{_fmt(water_expected)} kL",
            f"{water_variance:+,.2f} kL",
            f"{_fmt(water_loss)} kL",
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

    energy_baselines = energy.get("baselines") or []
    water_baselines = water.get("baselines") or []

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
        "Estimated losses use the values supplied by the live detection/reconciliation pipeline; if unavailable, only positive actual-versus-expected variance is used as a fallback.",
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

    # ========================================================
    # ALL-FACILITIES TABLE
    # ========================================================

    story.append(
        Paragraph(
            "2. All-Facilities Current Status",
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

        status = _text(
            detection.get("facility_status")
            if realtime
            else facility.get("status")
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
            "3. Facility Detail",
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
                _text(
                    detection.get("facility_status")
                    if realtime
                    else facility.get("status")
                ),
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

        primary = detection.get(
            "primary_anomaly"
        ) or {}

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
            "4. Data Availability & Calculation Notes",
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
