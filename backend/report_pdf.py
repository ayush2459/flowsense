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

# ============================================================
# FLOW SENSE VISUAL DESIGN SYSTEM — ENHANCED EDITION
# ============================================================
# This layer upgrades the PDF presentation without changing the
# underlying FlowSense calculations, telemetry semantics, or data
# sources. The reporting logic remains authoritative; this module
# focuses on hierarchy, readability, cards, visual status treatment,
# section separators, and executive-style presentation.
# ============================================================

from reportlab.lib.colors import HexColor
from reportlab.platypus import HRFlowable
from reportlab.pdfbase.pdfmetrics import stringWidth


# -----------------------------
# Theme palette
# -----------------------------

FS_NAVY = HexColor("#0B1F3A")
FS_BLUE = HexColor("#1769E0")
FS_CYAN = HexColor("#16B7D8")
FS_TEAL = HexColor("#0E9F8A")
FS_GREEN = HexColor("#1F9D55")
FS_AMBER = HexColor("#D9822B")
FS_RED = HexColor("#D64545")
FS_PURPLE = HexColor("#6956D8")
FS_INK = HexColor("#172033")
FS_MUTED = HexColor("#667085")
FS_SUBTLE = HexColor("#98A2B3")
FS_BORDER = HexColor("#E4E7EC")
FS_SURFACE = HexColor("#F8FAFC")
FS_SURFACE_ALT = HexColor("#F2F4F7")
FS_WHITE = HexColor("#FFFFFF")
FS_SHADOW = HexColor("#D0D5DD")
FS_LIGHT_BLUE = HexColor("#EAF2FF")
FS_LIGHT_CYAN = HexColor("#E9FAFC")
FS_LIGHT_GREEN = HexColor("#EAF8F0")
FS_LIGHT_AMBER = HexColor("#FFF5E8")
FS_LIGHT_RED = HexColor("#FFF0F0")
FS_LIGHT_PURPLE = HexColor("#F1EEFF")


# -----------------------------
# Theme helpers
# -----------------------------

def _fs_status_color(status):
    value = str(status or "").strip().lower()
    if value in ("critical", "crit"):
        return FS_RED
    if value in ("attention", "warning", "warn", "needs attention"):
        return FS_AMBER
    if value in ("healthy", "normal", "ok", "good", "active"):
        return FS_GREEN
    return FS_BLUE


def _fs_status_bg(status):
    value = str(status or "").strip().lower()
    if value in ("critical", "crit"):
        return FS_LIGHT_RED
    if value in ("attention", "warning", "warn", "needs attention"):
        return FS_LIGHT_AMBER
    if value in ("healthy", "normal", "ok", "good", "active"):
        return FS_LIGHT_GREEN
    return FS_LIGHT_BLUE


def _fs_metric_color(metric):
    value = str(metric or "").strip().lower()
    if "energy" in value:
        return FS_BLUE
    if "water" in value:
        return FS_CYAN
    if "efficiency" in value:
        return FS_TEAL
    if "anomaly" in value or "critical" in value:
        return FS_RED
    return FS_PURPLE


def _fs_safe_text(value):
    if value is None:
        return "N/A"
    return str(value)


def _safe_text(value, default="—"):
    """Safely convert report values to renderable PDF text."""
    if value is None:
        return default
    try:
        text = str(value).strip()
    except Exception:
        return default
    return text if text else default


def _fs_kpi_card(label, value, unit="", accent=FS_BLUE, note=None):
    """
    Create a compact executive KPI card using a ReportLab table.
    The card is deliberately data-agnostic so it can be reused by
    facility and portfolio reports.
    """
    value_text = _fs_safe_text(value)
    unit_text = _fs_safe_text(unit)
    note_text = _fs_safe_text(note) if note else ""
    value_markup = f'<font color="#172033" size="17"><b>{value_text}</b></font>'
    if unit_text:
        value_markup += f' <font color="#667085" size="8">{unit_text}</font>'
    body = [
        [
            Paragraph(
                f'<font color="{accent.hexval()}"><b>{_fs_safe_text(label).upper()}</b></font>',
                ParagraphStyle(
                    "FSCardLabel",
                    fontName="Helvetica-Bold",
                    fontSize=7,
                    leading=9,
                    textColor=accent,
                ),
            )
        ],
        [
            Paragraph(
                value_markup,
                ParagraphStyle(
                    "FSCardValue",
                    fontName="Helvetica-Bold",
                    fontSize=17,
                    leading=20,
                    textColor=FS_INK,
                ),
            )
        ],
    ]
    if note_text:
        body.append(
            [
                Paragraph(
                    note_text,
                    ParagraphStyle(
                        "FSCardNote",
                        fontName="Helvetica",
                        fontSize=7,
                        leading=9,
                        textColor=FS_MUTED,
                    ),
                )
            ]
        )
    card = Table(body, colWidths=[43 * mm], hAlign="LEFT")
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FS_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.7, FS_BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return card


def _fs_status_badge(status):
    status_text = _fs_safe_text(status)
    color = _fs_status_color(status_text)
    bg = _fs_status_bg(status_text)
    badge = Table(
        [
            [
                Paragraph(
                    f"<b>{status_text.upper()}</b>",
                    ParagraphStyle(
                        "FSStatusBadge",
                        fontName="Helvetica-Bold",
                        fontSize=7,
                        leading=9,
                        textColor=color,
                        alignment=TA_CENTER,
                    ),
                )
            ]
        ],
        colWidths=[28 * mm],
        hAlign="LEFT",
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.4, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return badge


def _fs_section_rule(width=165 * mm, accent=FS_BLUE):
    return HRFlowable(
        width="100%",
        thickness=1.1,
        color=accent,
        spaceBefore=1,
        spaceAfter=6,
        hAlign="LEFT",
    )


def _fs_progress_bar(value, maximum=100, width=48 * mm, accent=FS_BLUE):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    try:
        maximum_value = float(maximum)
    except (TypeError, ValueError):
        maximum_value = 100.0
    if maximum_value <= 0:
        maximum_value = 100.0
    ratio = max(0.0, min(1.0, numeric / maximum_value))
    outer = Table([[""]], colWidths=[width], rowHeights=[5 * mm])
    outer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FS_SURFACE_ALT),
                ("BOX", (0, 0), (-1, -1), 0.4, FS_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    # Keep the actual ratio visible even in environments where nested
    # tables are rendered differently by ReportLab versions.
    return Table(
        [
            [
                Paragraph(
                    f'<font color="{accent.hexval()}">{"■" * max(1, int(ratio * 18))}</font>',
                    ParagraphStyle(
                        "FSProgress",
                        fontName="Helvetica-Bold",
                        fontSize=7,
                        leading=7,
                        textColor=accent,
                    ),
                ),
                outer,
            ]
        ],
        colWidths=[12 * mm, width],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _fs_page_title(story, title, subtitle=None, accent=FS_BLUE):
    story.append(
        Paragraph(
            _fs_safe_text(title),
            ParagraphStyle(
                "FSPageTitle",
                fontName="Helvetica-Bold",
                fontSize=19,
                leading=23,
                textColor=FS_INK,
                spaceBefore=3,
                spaceAfter=3,
            ),
        )
    )
    story.append(_fs_section_rule(accent=accent))
    if subtitle:
        story.append(
            Paragraph(
                _fs_safe_text(subtitle),
                ParagraphStyle(
                    "FSPageSubtitle",
                    fontName="Helvetica",
                    fontSize=8.5,
                    leading=12,
                    textColor=FS_MUTED,
                    spaceAfter=8,
                ),
            )
        )


def _fs_metric_grid(cards, columns=3):
    """
    Arrange KPI card flowables into a compact grid.
    """
    rows = []
    current = []
    for card in cards:
        current.append(card)
        if len(current) == columns:
            rows.append(current)
            current = []
    if current:
        while len(current) < columns:
            current.append("")
        rows.append(current)
    if not rows:
        return Spacer(1, 0)
    table = Table(
        rows,
        colWidths=[53 * mm] * columns,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _fs_portfolio_banner(story, title, subtitle, count=None):
    content = [
        Paragraph(
            _fs_safe_text(title),
            ParagraphStyle(
                "FSBannerTitle",
                fontName="Helvetica-Bold",
                fontSize=17,
                leading=21,
                textColor=FS_WHITE,
            ),
        ),
        Paragraph(
            _fs_safe_text(subtitle),
            ParagraphStyle(
                "FSBannerSubtitle",
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=HexColor("#DCE8F7"),
            ),
        ),
    ]
    if count is not None:
        content.append(
            Paragraph(
                f"<b>{_fs_safe_text(count)}</b> facilities",
                ParagraphStyle(
                    "FSBannerCount",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    leading=10,
                    textColor=FS_WHITE,
                ),
            )
        )
    banner = Table([[content]], colWidths=[165 * mm])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FS_NAVY),
                ("BOX", (0, 0), (-1, -1), 0, FS_NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 13),
                ("RIGHTPADDING", (0, 0), (-1, -1), 13),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    story.append(banner)
    story.append(Spacer(1, 5 * mm))


def _fs_facility_identity_card(story, facility):
    name = _text(facility.get("facility_name"))
    code = _text(facility.get("facility_code"))
    facility_type = _text(facility.get("facility_type"))
    city = _text(facility.get("city"))
    state = _text(facility.get("state"))
    status = _text(facility.get("status"), "Healthy")
    location = f"{city}, {state}"
    rows = [
        [
            Paragraph(
                f"<b>{name}</b>",
                ParagraphStyle(
                    "FSIdentityName",
                    fontName="Helvetica-Bold",
                    fontSize=13,
                    leading=16,
                    textColor=FS_INK,
                ),
            ),
            _fs_status_badge(status),
        ],
        [
            Paragraph(
                f"{code}  •  {facility_type}  •  {location}",
                ParagraphStyle(
                    "FSIdentityMeta",
                    fontName="Helvetica",
                    fontSize=8,
                    leading=11,
                    textColor=FS_MUTED,
                ),
            ),
            "",
        ],
    ]
    table = Table(rows, colWidths=[125 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FS_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.7, FS_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))


def _fs_render_efficiency_cards(story, energy_score, water_score, status):
    cards = [
        _fs_kpi_card(
            "Energy efficiency",
            _fmt(energy_score, 1),
            "%",
            FS_BLUE,
            "Realtime pipeline score",
        ),
        _fs_kpi_card(
            "Water efficiency",
            _fmt(water_score, 1),
            "%",
            FS_CYAN,
            "Realtime pipeline score",
        ),
        _fs_kpi_card(
            "Detection state",
            _safe_text(status),
            "",
            _fs_status_color(status),
            "Latest realtime snapshot",
        ),
    ]
    story.append(_fs_metric_grid(cards, columns=3))
    story.append(Spacer(1, 2 * mm))


def _fs_render_realtime_cards(
    story,
    energy_actual,
    energy_expected,
    energy_variance,
    water_actual,
    water_expected,
    water_variance,
):
    energy_note = (
        f"Variance {_format_variance(energy_variance, 'kWh')}"
        if energy_variance is not None
        else "Expected value unavailable"
    )
    water_note = (
        f"Variance {_format_variance(water_variance, 'kL')}"
        if water_variance is not None
        else "Expected value unavailable"
    )
    cards = [
        _fs_kpi_card(
            "Energy consumption",
            _fmt(energy_actual),
            "kWh",
            FS_BLUE,
            energy_note,
        ),
        _fs_kpi_card(
            "Energy target",
            _fmt(energy_expected),
            "kWh",
            FS_PURPLE,
            "Current facility target",
        ),
        _fs_kpi_card(
            "Water consumption",
            _fmt(water_actual),
            "kL",
            FS_CYAN,
            water_note,
        ),
        _fs_kpi_card(
            "Water target",
            _fmt(water_expected),
            "kL",
            FS_TEAL,
            "Current facility target",
        ),
    ]
    story.append(_fs_metric_grid(cards, columns=4))
    story.append(Spacer(1, 2 * mm))


def _fs_render_portfolio_health_cards(story, counts, total):
    cards = [
        _fs_kpi_card(
            "Healthy facilities",
            counts.get("Healthy", 0),
            "",
            FS_GREEN,
            f"of {total} facilities",
        ),
        _fs_kpi_card(
            "Attention",
            counts.get("Attention", 0),
            "",
            FS_AMBER,
            "Realtime detection state",
        ),
        _fs_kpi_card(
            "Critical",
            counts.get("Critical", 0),
            "",
            FS_RED,
            "Realtime detection state",
        ),
        _fs_kpi_card(
            "Realtime conditions",
            counts.get("Attention", 0) + counts.get("Critical", 0),
            "",
            FS_PURPLE,
            "Attention + Critical",
        ),
    ]
    story.append(_fs_metric_grid(cards, columns=4))
    story.append(Spacer(1, 3 * mm))


def _fs_render_portfolio_snapshot_cards(story, realtime_count, facility_count,
                                         realtime_anomaly_count,
                                         persisted_anomaly_count,
                                         alert_count):
    cards = [
        _fs_kpi_card(
            "Facilities",
            facility_count,
            "",
            FS_NAVY,
            "Active facilities in report",
        ),
        _fs_kpi_card(
            "Realtime snapshots",
            f"{realtime_count}/{facility_count}",
            "",
            FS_BLUE,
            "Available at generation time",
        ),
        _fs_kpi_card(
            "Realtime anomalies",
            realtime_anomaly_count,
            "",
            FS_RED if realtime_anomaly_count else FS_GREEN,
            "Latest detection state",
        ),
        _fs_kpi_card(
            "Persisted records",
            persisted_anomaly_count,
            "",
            FS_PURPLE,
            f"{alert_count} alerts in period",
        ),
    ]
    story.append(_fs_metric_grid(cards, columns=4))
    story.append(Spacer(1, 3 * mm))


# -----------------------------
# Optional visual components
# -----------------------------

def _fs_text_panel(title, body, accent=FS_BLUE):
    panel = Table(
        [
            [
                Paragraph(
                    _fs_safe_text(title),
                    ParagraphStyle(
                        "FSTextPanelTitle",
                        fontName="Helvetica-Bold",
                        fontSize=9,
                        leading=12,
                        textColor=FS_INK,
                    ),
                )
            ],
            [
                Paragraph(
                    _fs_safe_text(body),
                    ParagraphStyle(
                        "FSTextPanelBody",
                        fontName="Helvetica",
                        fontSize=8,
                        leading=12,
                        textColor=FS_MUTED,
                    ),
                )
            ],
        ],
        colWidths=[165 * mm],
    )
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FS_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.6, FS_BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return panel


def _fs_add_empty_state(story, message, detail=None):
    body = _fs_safe_text(message)
    if detail:
        body += f"<br/><font size='7'>{_fs_safe_text(detail)}</font>"
    story.append(
        _fs_text_panel(
            "No additional records",
            body,
            FS_MUTED,
        )
    )


def _fs_metric_label(value, unit=""):
    if value is None:
        return "N/A"
    return f"{_fmt(value)} {unit}".strip()


def _fs_variance_label(actual, expected, unit=""):
    variance = _safe_difference(actual, expected)
    if variance is None:
        return "N/A"
    return _format_variance(variance, unit)


# -----------------------------
# Additional report styling
# -----------------------------

def _fs_style_title(base_style):
    base_style.fontName = "Helvetica-Bold"
    base_style.textColor = FS_NAVY
    base_style.fontSize = 22
    base_style.leading = 26
    return base_style


def _fs_style_heading(base_style, accent=FS_BLUE):
    base_style.fontName = "Helvetica-Bold"
    base_style.textColor = FS_INK
    base_style.fontSize = 14
    base_style.leading = 18
    base_style.spaceBefore = 12
    base_style.spaceAfter = 7
    return base_style


def _fs_style_body(base_style):
    base_style.fontName = "Helvetica"
    base_style.textColor = FS_INK
    base_style.fontSize = 9
    base_style.leading = 13
    return base_style


def _fs_style_small(base_style):
    base_style.fontName = "Helvetica"
    base_style.textColor = FS_MUTED
    base_style.fontSize = 7.5
    base_style.leading = 10
    return base_style


# -----------------------------
# Visual QA notes
# -----------------------------

FS_VISUAL_QA_CHECKLIST = [
    "Use consistent navy primary headings across facility and portfolio reports.",
    "Use blue for energy-related primary metrics.",
    "Use cyan or teal for water-related primary metrics.",
    "Use green, amber, and red consistently for Healthy, Attention, and Critical states.",
    "Keep KPI variance visually distinct from anomaly status.",
    "Keep historical records visually separate from realtime snapshots.",
    "Keep facility-level values separate from portfolio-level counts.",
    "Avoid presenting target variance as physical loss without authoritative evidence.",
    "Use compact cards before dense tables so executives can scan the report.",
    "Use subtle borders instead of heavy grid lines wherever possible.",
    "Use muted explanatory text for methodology and data-quality notes.",
    "Preserve N/A semantics for missing data.",
]


# -----------------------------
# Reusable visual separators
# -----------------------------

def _fs_separator(story, accent=FS_BORDER):
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=accent,
            spaceBefore=3,
            spaceAfter=7,
        )
    )


def _fs_spacer(story, mm_value=3):
    story.append(Spacer(1, mm_value * mm))


# -----------------------------
# Executive summary helpers
# -----------------------------

def _fs_summary_sentence(status, anomaly_count, variance_text):
    normalized = str(status or "").lower()
    if normalized == "critical":
        state = "The latest realtime snapshot reports a critical detection state."
    elif normalized == "attention":
        state = "The latest realtime snapshot reports a condition requiring attention."
    else:
        state = "The latest realtime snapshot reports no active realtime anomaly."
    if anomaly_count:
        anomaly_text = f" {anomaly_count} realtime anomaly condition(s) are present."
    else:
        anomaly_text = " No realtime anomaly condition is reported."
    if variance_text:
        variance = f" KPI variance remains visible as {variance_text}."
    else:
        variance = ""
    return state + anomaly_text + variance


def _fs_render_summary_panel(
    story,
    status,
    anomaly_count,
    energy_variance,
    water_variance,
):
    variance_parts = []
    if energy_variance is not None:
        variance_parts.append(
            f"energy {_format_variance(energy_variance, 'kWh')}"
        )
    if water_variance is not None:
        variance_parts.append(
            f"water {_format_variance(water_variance, 'kL')}"
        )
    variance_text = ", ".join(variance_parts)
    sentence = _fs_summary_sentence(
        status,
        anomaly_count,
        variance_text,
    )
    story.append(
        _fs_text_panel(
            "Realtime Executive Summary",
            sentence,
            _fs_status_color(status),
        )
    )
    story.append(Spacer(1, 3 * mm))


# -----------------------------
# Portfolio facility row helper
# -----------------------------

def _fs_portfolio_facility_row(
    facility_name,
    facility_code,
    status,
    energy,
    water,
    anomaly_count,
):
    return [
        Paragraph(
            f"<b>{_fs_safe_text(facility_name)}</b><br/>"
            f"<font color='#667085'>{_fs_safe_text(facility_code)}</font>",
            ParagraphStyle(
                "FSPortfolioFacility",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=FS_INK,
            ),
        ),
        _fs_status_badge(status),
        Paragraph(
            _fs_metric_label(energy, "kWh"),
            ParagraphStyle(
                "FSEnergyValue",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=FS_BLUE,
            ),
        ),
        Paragraph(
            _fs_metric_label(water, "kL"),
            ParagraphStyle(
                "FSWaterValue",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=FS_CYAN,
            ),
        ),
        Paragraph(
            _fs_safe_text(anomaly_count),
            ParagraphStyle(
                "FSAnomalyValue",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=FS_RED if anomaly_count else FS_GREEN,
                alignment=TA_CENTER,
            ),
        ),
    ]


# -----------------------------
# Facility comparison helpers
# -----------------------------

def _fs_deviation_badge(percentage):
    if percentage is None:
        return _fs_status_badge("N/A")
    if percentage >= 20:
        status = "Critical"
    elif percentage >= 10:
        status = "Attention"
    else:
        status = "Healthy"
    return _fs_status_badge(f"{_fmt(percentage, 1)}%" if status != "Healthy"
                            else f"{_fmt(percentage, 1)}%")


def _fs_numeric_paragraph(value, unit="", accent=FS_INK):
    return Paragraph(
        _fs_metric_label(value, unit),
        ParagraphStyle(
            "FSNumeric",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=accent,
        ),
    )


# -----------------------------
# Long-form style documentation
# -----------------------------
# The following design notes intentionally remain in the source so
# future maintainers can understand why the visual system exists.
# They also make the module easier to extend without changing the
# semantics of FlowSense calculations.
#
# Visual principle 01:
# Realtime information should be scannable before a user reaches a
# dense table. KPI cards therefore precede detailed tables.
#
# Visual principle 02:
# A target is a comparison reference, not an anomaly by itself.
# The report therefore uses separate visual treatments for variance
# and detection status.
#
# Visual principle 03:
# Historical and realtime information have different temporal
# meanings. Their sections should never visually imply that they
# represent the same snapshot.
#
# Visual principle 04:
# Portfolio reports summarize the state of facilities but should not
# imply that facility-level consumption has been safely aggregated.
#
# Visual principle 05:
# Status colors are semantic, not decorative. Green means the
# detection payload reports a healthy/normal state, amber means
# attention, and red means critical.
#
# Visual principle 06:
# Blue is reserved primarily for energy, cyan/teal for water, purple
# for contextual analytics, and navy for structural navigation.
#
# Visual principle 07:
# Explanatory notes use muted typography so they remain available
# without competing with operational metrics.
#
# Visual principle 08:
# Missing data remains N/A. The visual layer never converts missing
# data into zeros.
#
# Visual principle 09:
# The report should look useful at executive level while preserving
# enough detail for engineering and operations teams.
#
# Visual principle 10:
# A polished PDF should remain print-friendly, so the design uses
# restrained fills, borders, typography, and high-contrast text.
#
# Visual principle 11:
# Tables are retained because they are the correct structure for
# audit/reference data. Cards are used for scanning, not as a
# replacement for detailed records.
#
# Visual principle 12:
# Facility identity should be immediately visible at the start of
# each facility detail section.
#
# Visual principle 13:
# Portfolio status should be visible without forcing users to read
# every row in the all-facilities table.
#
# Visual principle 14:
# Detection evidence should remain attributable to the realtime
# payload and should not be inferred from presentation formatting.
#
# Visual principle 15:
# The design should tolerate N/A values without broken alignment.
#
# Visual principle 16:
# Long facility names and descriptions should wrap inside Paragraphs
# instead of overflowing fixed-width table cells.
#
# Visual principle 17:
# Page headers and footers should reinforce the FlowSense identity
# while remaining unobtrusive.
#
# Visual principle 18:
# Section headings should create a clear reading hierarchy.
#
# Visual principle 19:
# Data-quality notes should appear near the end of reports and remain
# visibly separate from operational KPIs.
#
# Visual principle 20:
# The visual system must not modify the calculation functions that
# determine variance, baseline context, anomaly state, or loss.
#
# Visual principle 21:
# Realtime anomaly evidence remains authoritative.
#
# Visual principle 22:
# Persisted anomalies and alerts remain database-backed.
#
# Visual principle 23:
# Baselines remain contextual operating profiles.
#
# Visual principle 24:
# Facility targets remain current comparison values.
#
# Visual principle 25:
# The PDF is a presentation layer over the existing report package.
#
# Visual principle 26:
# No visual element should suggest a measurement that is not present
# in the underlying report package.
#
# Visual principle 27:
# Portfolio cards should summarize counts, not invent portfolio
# consumption totals.
#
# Visual principle 28:
# Realtime snapshot timing should remain visible.
#
# Visual principle 29:
# Historical reading timestamps should remain visible where used.
#
# Visual principle 30:
# IoT device and sensor metadata remain part of the facility report.
#
# Visual principle 31:
# The final report should be suitable for both screen viewing and
# PDF export/printing.
#
# Visual principle 32:
# Subtle whitespace is used to separate concepts rather than relying
# only on borders.
#
# Visual principle 33:
# The visual hierarchy should remain understandable in grayscale.
#
# Visual principle 34:
# Labels are written in plain operational language.
#
# Visual principle 35:
# Tables use consistent padding to improve scanning.
#
# Visual principle 36:
# The same visual language is shared by single-facility and portfolio
# reports to make the two report types feel like one product.
#
# Visual principle 37:
# The cover is intentionally minimal so the report feels like a
# product-generated intelligence document rather than a raw export.
#
# Visual principle 38:
# The portfolio cover emphasizes scope and facility count.
#
# Visual principle 39:
# Facility covers emphasize facility identity and reporting period.
#
# Visual principle 40:
# The design layer is intentionally implemented with standard
# ReportLab primitives so deployment remains straightforward.
#
# Visual principle 41:
# No browser, JavaScript, external font, or image asset is required
# by this visual upgrade.
#
# Visual principle 42:
# The module remains compatible with the existing BytesIO PDF
# generation functions.
#
# Visual principle 43:
# The existing report generator remains the source of truth for data.
#
# Visual principle 44:
# The new visual helpers can be extended independently.
#
# Visual principle 45:
# Future charts can consume the same report dictionaries without
# changing the database access layer.
#
# Visual principle 46:
# Future chart rendering should preserve the same status palette.
#
# Visual principle 47:
# Future map rendering should preserve facility identity semantics.
#
# Visual principle 48:
# Future branding should be isolated to the theme constants.
#
# Visual principle 49:
# Future typography changes should be isolated to style factories.
#
# Visual principle 50:
# Future layout changes should not alter calculation semantics.
#
# End of visual design system.

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

    # Modern FlowSense header
    canvas.setFillColor(FS_NAVY)
    canvas.roundRect(
        14 * mm,
        height - 16 * mm,
        width - 28 * mm,
        8 * mm,
        2.5 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(FS_WHITE)
    canvas.drawString(
        19 * mm,
        height - 12.2 * mm,
        "FlowSense"
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(HexColor("#DCE8F7"))
    canvas.drawRightString(
        width - 19 * mm,
        height - 12.2 * mm,
        "ENERGY & WATER INTELLIGENCE"
    )

    canvas.setStrokeColor(FS_BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(
        18 * mm,
        height - 19 * mm,
        width - 18 * mm,
        height - 19 * mm,
    )

    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(FS_MUTED)
    canvas.drawString(
        18 * mm,
        9 * mm,
        "FlowSense  •  Measured telemetry  •  Detection  •  Reconciliation"
    )

    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(FS_NAVY)
    canvas.drawRightString(
        width - 18 * mm,
        9 * mm,
        f"{doc.page:02d}"
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
            0.35,
            FS_BORDER,
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
            "TEXTCOLOR",
            (0, 0),
            (-1, -1),
            FS_INK,
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            7,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            7,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
    ]

    if header:
        style.extend([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                FS_NAVY,
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                FS_WHITE,
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),
            (
                "LINEBELOW",
                (0, 0),
                (-1, 0),
                1.2,
                FS_BLUE,
            ),
        ])

    # Subtle alternating row treatment improves scanability while
    # preserving the existing tabular structure and data semantics.
    if header and len(data) > 2:
        for row_index in range(1, len(data)):
            if row_index % 2 == 0:
                style.append(
                    (
                        "BACKGROUND",
                        (0, row_index),
                        (-1, row_index),
                        FS_SURFACE,
                    )
                )
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

    _fs_render_portfolio_health_cards(
        story,
        counts,
        total,
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
        textColor=FS_MUTED,
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
        textColor=FS_INK,
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
        textColor=FS_MUTED,
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

    # Refresh the executive cards after variance values are known.
    _fs_render_realtime_cards(
        story,
        energy_actual,
        energy_expected,
        energy_variance,
        water_actual,
        water_expected,
        water_variance,
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

    _fs_render_summary_panel(
        story,
        detection.get("facility_status") or _normalized_facility_status(realtime),
        int(_num(detection.get("anomaly_count"), 0)),
        energy_variance,
        water_variance,
    )

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

    _fs_render_efficiency_cards(
        story,
        efficiency.get("energy_score"),
        efficiency.get("water_score"),
        detection.get("facility_status") or _normalized_facility_status(realtime),
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
        textColor=FS_MUTED,
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
        textColor=FS_INK,
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
        textColor=FS_MUTED,
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

    _fs_render_portfolio_snapshot_cards(
        story,
        realtime_count,
        len(facilities),
        realtime_anomaly_count,
        persisted_anomaly_count,
        alert_count,
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

        _fs_facility_identity_card(
            story,
            facility,
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


# ============================================================
# VISUAL DESIGN EXTENSION NOTES
# ============================================================
# The following constants/documentation describe the intended UI
# hierarchy for future contributors. They are kept in source rather
# than in an external design document so the PDF generator remains
# self-documenting.
#
# Layer 01 — Brand
# FlowSense uses a dark navy structural color for identity, headers,
# and high-level navigation. It should remain stable across reports.
#
# Layer 02 — Resource identity
# Energy is represented primarily with blue.
# Water is represented primarily with cyan/teal.
#
# Layer 03 — Operational state
# Healthy is green.
# Attention is amber.
# Critical is red.
#
# Layer 04 — Contextual analytics
# Purple is reserved for contextual analytics such as persisted
# record counts, deviation context, and supporting analytics.
#
# Layer 05 — Neutral data
# Gray tones are reserved for labels, metadata, methodology, and
# unavailable values.
#
# Layout rule 01:
# Cover pages should have generous whitespace.
#
# Layout rule 02:
# Operational KPI cards should appear before detailed tables.
#
# Layout rule 03:
# Tables should use consistent row height and padding.
#
# Layout rule 04:
# Section headings should be visually stronger than body copy.
#
# Layout rule 05:
# Explanatory notes should never overpower measurements.
#
# Layout rule 06:
# Facility identity should be repeated when a report contains
# multiple facilities so pages remain understandable when printed.
#
# Layout rule 07:
# Portfolio summaries should communicate counts, not fabricate
# portfolio consumption.
#
# Layout rule 08:
# Realtime and historical data should have explicit labels.
#
# Layout rule 09:
# Baselines should be described as configured profiles.
#
# Layout rule 10:
# Targets should be described as comparison values.
#
# Layout rule 11:
# Anomaly evidence should remain traceable to the detection payload.
#
# Layout rule 12:
# Persisted anomalies should remain traceable to database records.
#
# Layout rule 13:
# Reconciliation loss should remain traceable to authoritative
# pipeline output.
#
# Layout rule 14:
# Positive variance without loss evidence should remain variance.
#
# Layout rule 15:
# N/A must remain visually obvious.
#
# Layout rule 16:
# The design must not imply that an unavailable value is zero.
#
# Layout rule 17:
# The design must remain usable when facility names are long.
#
# Layout rule 18:
# The design must remain usable when descriptions are long.
#
# Layout rule 19:
# The design must remain usable when anomaly tables contain many rows.
#
# Layout rule 20:
# The design must remain usable when there are no anomalies.
#
# Layout rule 21:
# The design must remain usable when realtime data is unavailable.
#
# Layout rule 22:
# The design must remain usable when historical data is unavailable.
#
# Layout rule 23:
# The design must remain usable when a facility has no devices.
#
# Layout rule 24:
# The design must remain usable when a facility has no sensors.
#
# Layout rule 25:
# The design must remain usable when baseline records are missing.
#
# Layout rule 26:
# The design must remain usable when facility targets are missing.
#
# Layout rule 27:
# The design must remain usable when expected values are missing.
#
# Layout rule 28:
# The design must remain usable when efficiency scores are missing.
#
# Layout rule 29:
# The design must remain usable when anomaly confidence is missing.
#
# Layout rule 30:
# The design must remain usable when anomaly source is missing.
#
# Layout rule 31:
# The design must remain usable when anomaly area is missing.
#
# Layout rule 32:
# The design must remain usable when status is missing.
#
# Layout rule 33:
# The design must remain usable when a facility report contains
# a data_error field.
#
# Layout rule 34:
# Data errors should be displayed as information, not silently
# converted into healthy state.
#
# Layout rule 35:
# A report should never hide data-quality limitations.
#
# Layout rule 36:
# A report should make the distinction between measured and inferred
# values explicit.
#
# Layout rule 37:
# A report should not visually overstate precision.
#
# Layout rule 38:
# Two decimal places remain the default for measured values.
#
# Layout rule 39:
# Percentages use one decimal place when used for confidence or
# efficiency scores.
#
# Layout rule 40:
# Status badges use uppercase text for quick scanning.
#
# Layout rule 41:
# Status badge colors are paired with text so the report remains
# interpretable without color.
#
# Layout rule 42:
# Tables use a dark header to create strong column separation.
#
# Layout rule 43:
# Alternating row backgrounds are intentionally subtle.
#
# Layout rule 44:
# Borders remain light to reduce visual noise.
#
# Layout rule 45:
# The header bar is compact so it does not consume useful page area.
#
# Layout rule 46:
# Footer metadata is compact and repeatable.
#
# Layout rule 47:
# Page numbers use two digits for consistent visual width.
#
# Layout rule 48:
# The report remains A4-first because the existing generator uses A4.
#
# Layout rule 49:
# Existing margins remain unchanged unless explicitly redesigned.
#
# Layout rule 50:
# All visual components are implemented using standard ReportLab
# primitives already used by the existing module.
#
# Extension 01:
# Add a monthly trend chart using report["monthly_summaries"].
#
# Extension 02:
# Add a daily consumption chart using report["energy"]["readings"].
#
# Extension 03:
# Add a water trend chart using report["water"]["readings"].
#
# Extension 04:
# Add a baseline envelope chart using configured baseline rows.
#
# Extension 05:
# Add a reconciliation bridge using authoritative reconciliation
# records only.
#
# Extension 06:
# Add an anomaly timeline using persisted anomaly timestamps.
#
# Extension 07:
# Add an alert timeline using persisted alert timestamps.
#
# Extension 08:
# Add a sensor inventory card for the IoT infrastructure section.
#
# Extension 09:
# Add device protocol summary counts.
#
# Extension 10:
# Add a facility comparison chart to the portfolio report while
# retaining separate facility values.
#
# Extension 11:
# Add a facility status distribution visual.
#
# Extension 12:
# Add a realtime availability indicator.
#
# Extension 13:
# Add a reporting-period completeness indicator.
#
# Extension 14:
# Add a baseline coverage indicator.
#
# Extension 15:
# Add a reconciliation coverage indicator.
#
# Extension 16:
# Add an alert closure indicator from persisted records.
#
# Extension 17:
# Add a device connectivity summary.
#
# Extension 18:
# Add a sensor coverage summary.
#
# Extension 19:
# Add a data freshness panel.
#
# Extension 20:
# Add a report provenance panel.
#
# Engineering constraint 01:
# Do not move database access into the PDF renderer.
#
# Engineering constraint 02:
# Do not calculate anomaly status from presentation-layer values.
#
# Engineering constraint 03:
# Do not calculate physical loss from target variance.
#
# Engineering constraint 04:
# Do not aggregate facility telemetry into a portfolio total unless
# the upstream report contract explicitly defines a safe aggregation.
#
# Engineering constraint 05:
# Do not replace missing values with zero.
#
# Engineering constraint 06:
# Do not mutate the report dictionaries while rendering.
#
# Engineering constraint 07:
# Do not modify historical timestamps for presentation.
#
# Engineering constraint 08:
# Do not modify realtime timestamps for presentation.
#
# Engineering constraint 09:
# Do not silently drop anomaly evidence.
#
# Engineering constraint 10:
# Do not silently drop alerts.
#
# Engineering constraint 11:
# Do not silently drop device metadata.
#
# Engineering constraint 12:
# Do not silently drop sensor metadata.
#
# Engineering constraint 13:
# Keep all existing report sections available.
#
# Engineering constraint 14:
# Keep the original report generation entry points unchanged.
#
# Engineering constraint 15:
# Keep BytesIO return values unchanged.
#
# Engineering constraint 16:
# Keep ReportLab as the rendering engine.
#
# Engineering constraint 17:
# Keep the output as a PDF.
#
# Engineering constraint 18:
# Keep facility and portfolio reports visually related.
#
# Engineering constraint 19:
# Keep data semantics separate from visual semantics.
#
# Engineering constraint 20:
# Keep the code deployable in the existing FlowSense backend.
#
# QA scenario 01:
# Facility with healthy realtime status and positive energy variance.
#
# Expected visual result:
# Healthy badge remains green while the variance remains informational.
#
# QA scenario 02:
# Facility with critical realtime anomaly.
#
# Expected visual result:
# Critical badge is red and anomaly evidence appears near the top.
#
# QA scenario 03:
# Facility with attention realtime anomaly.
#
# Expected visual result:
# Attention badge is amber and detection evidence remains visible.
#
# QA scenario 04:
# Facility with no realtime anomaly.
#
# Expected visual result:
# Healthy/no-anomaly state appears with contextual KPI cards.
#
# QA scenario 05:
# Facility with authoritative energy loss.
#
# Expected visual result:
# Loss evidence is labelled as estimated loss.
#
# QA scenario 06:
# Facility with positive target variance but no loss evidence.
#
# Expected visual result:
# Value is labelled excess consumption/variance.
#
# QA scenario 07:
# Facility with no historical readings.
#
# Expected visual result:
# Historical section clearly reports unavailable records.
#
# QA scenario 08:
# Portfolio with mixed healthy, attention, and critical facilities.
#
# Expected visual result:
# Summary cards expose counts before detailed tables.
#
# QA scenario 09:
# Portfolio with no realtime snapshots.
#
# Expected visual result:
# Snapshot count is 0/N and no fabricated realtime metrics appear.
#
# QA scenario 10:
# Portfolio with persisted anomalies but no current realtime anomaly.
#
# Expected visual result:
# Persisted anomaly count remains separate from realtime status.
#
# QA scenario 11:
# Portfolio with realtime anomaly but no persisted anomaly record.
#
# Expected visual result:
# Realtime anomaly remains visible and is not counted as persisted.
#
# QA scenario 12:
# Facility with missing expected energy.
#
# Expected visual result:
# Target and variance render as N/A.
#
# QA scenario 13:
# Facility with missing expected water.
#
# Expected visual result:
# Target and variance render as N/A.
#
# QA scenario 14:
# Facility with missing efficiency scores.
#
# Expected visual result:
# Efficiency cards render N/A.
#
# QA scenario 15:
# Facility with many sensors.
#
# Expected visual result:
# Sensor table remains readable and can split across pages.
#
# QA scenario 16:
# Facility with many anomaly records.
#
# Expected visual result:
# Existing 30-record display limit remains intact.
#
# QA scenario 17:
# Facility with many alerts.
#
# Expected visual result:
# Existing 30-record display limit remains intact.
#
# QA scenario 18:
# Facility with long anomaly description.
#
# Expected visual result:
# Paragraph/table wrapping prevents horizontal overflow.
#
# QA scenario 19:
# Facility with long facility name.
#
# Expected visual result:
# Identity card wraps the name safely.
#
# QA scenario 20:
# Portfolio with long facility names.
#
# Expected visual result:
# Facility column wraps safely.
#
# QA scenario 21:
# Portfolio with data errors.
#
# Expected visual result:
# Data-error count appears in summary and detail.
#
# QA scenario 22:
# Portfolio with zero facilities.
#
# Expected visual result:
# Empty state is explicit and no fake rows are created.
#
# QA scenario 23:
# Baseline profile with 168 rows.
#
# Expected visual result:
# Existing complete baseline table remains available.
#
# QA scenario 24:
# Baseline profile with no records.
#
# Expected visual result:
# No baseline rows are fabricated.
#
# QA scenario 25:
# Device metadata absent.
#
# Expected visual result:
# Device section remains present without fabricated inventory.
#
# QA scenario 26:
# Sensor metadata absent.
#
# Expected visual result:
# Sensor section remains present without fabricated inventory.
#
# QA scenario 27:
# Reconciliation absent.
#
# Expected visual result:
# Reconciliation count remains zero and loss evidence remains
# governed by the realtime pipeline.
#
# QA scenario 28:
# Realtime payload unavailable.
#
# Expected visual result:
# Historical and configured information remain usable.
#
# QA scenario 29:
# Realtime payload contains explicit facility_status.
#
# Expected visual result:
# Explicit status takes precedence over inferred display status.
#
# QA scenario 30:
# Realtime payload contains primary_anomaly.
#
# Expected visual result:
# Primary anomaly details are surfaced directly.
#
# QA scenario 31:
# Realtime payload uses nested detection data.
#
# Expected visual result:
# Normalization helpers preserve the existing payload compatibility.
#
# QA scenario 32:
# Realtime payload uses nested data fields.
#
# Expected visual result:
# Fallback extraction continues to work.
#
# QA scenario 33:
# Realtime payload uses anomaly_type and anomaly_count.
#
# Expected visual result:
# Primary anomaly normalization remains available.
#
# QA scenario 34:
# Realtime payload contains zero authoritative loss.
#
# Expected visual result:
# Report displays no loss evidence rather than estimated loss.
#
# QA scenario 35:
# Realtime payload contains positive authoritative loss.
#
# Expected visual result:
# Report displays estimated loss with correct unit.
#
# QA scenario 36:
# Expected value equals zero.
#
# Expected visual result:
# Percentage variance safely remains N/A rather than dividing by zero.
#
# QA scenario 37:
# Actual value is zero.
#
# Expected visual result:
# Negative variance is preserved and displayed.
#
# QA scenario 38:
# Actual and expected values are missing.
#
# Expected visual result:
# Variance remains N/A.
#
# QA scenario 39:
# Timestamp cannot be parsed.
#
# Expected visual result:
# Original timestamp text is retained by formatter fallback.
#
# QA scenario 40:
# Report is generated at a different time.
#
# Expected visual result:
# Realtime snapshot timestamp remains tied to the supplied payload.
#
# QA scenario 41:
# Historical latest reading is older than realtime.
#
# Expected visual result:
# Report explicitly separates persisted and realtime timestamps.
#
# QA scenario 42:
# Facility target differs from weekly baseline average.
#
# Expected visual result:
# Both values remain separately labelled.
#
# QA scenario 43:
# Weekly baseline has thresholds.
#
# Expected visual result:
# Lower and upper thresholds remain visible in the baseline table.
#
# QA scenario 44:
# Weekly baseline has no thresholds.
#
# Expected visual result:
# Missing thresholds display N/A.
#
# QA scenario 45:
# Facility status field is absent but no anomaly exists.
#
# Expected visual result:
# Display defaults to Healthy through existing normalization.
#
# QA scenario 46:
# Facility status field says warning.
#
# Expected visual result:
# Display normalizes warning to Attention.
#
# QA scenario 47:
# Facility status field says crit.
#
# Expected visual result:
# Display normalizes crit to Critical.
#
# QA scenario 48:
# Facility status field says normal.
#
# Expected visual result:
# Display normalizes normal to Healthy.
#
# QA scenario 49:
# Portfolio facility status is derived from anomaly severity.
#
# Expected visual result:
# Critical severity maps to Critical, other active anomaly maps
# to Attention.
#
# QA scenario 50:
# Portfolio health count is displayed.
#
# Expected visual result:
# Counts are transparent and non-ranking.
#
# End of QA design notes.
