# ruff: noqa: E501
from __future__ import annotations

import io
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from xml.sax.saxutils import escape

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from incrementality_api.application.data_products.reports import ReportModel


INK = colors.HexColor("#171522")
MUTED = colors.HexColor("#6F6A7D")
PURPLE = colors.HexColor("#5B3FD9")
PURPLE_SOFT = colors.HexColor("#F1EDFF")
PURPLE_LINE = colors.HexColor("#D8CFFF")
GREEN = colors.HexColor("#168A56")
GREEN_SOFT = colors.HexColor("#EAF7F0")
GREEN_LINE = colors.HexColor("#BFE8D1")
LINE = colors.HexColor("#E7E3EC")
SUBTLE = colors.HexColor("#FAF9FC")
W, H = letter
MARGIN = 42
CONTENT = W - MARGIN * 2
PAGE_NAMES = {
    1: "EXECUTIVE SUMMARY",
    2: "KEY FINDINGS & DIAGNOSTICS",
    3: "GEOGRAPHY & INTERPRETATION",
    4: "REPRODUCIBILITY APPENDIX",
}


def mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def sequence(value: object) -> Sequence[object]:
    return (
        value
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
        else ()
    )


def deep(value: object, names: set[str]) -> object | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in names:
                return cast(object, item)
        for item in value.values():
            found = deep(item, names)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            found = deep(item, names)
            if found is not None:
                return found
    return None


def number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def deep_number(value: object, *names: str) -> float | None:
    return number(deep(value, set(names)))


def text(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered or fallback


def human(value: object) -> str:
    raw = text(value, "")
    known = {
        "fednow_transactions_per_1000_business_accounts": "FedNow transactions per 1,000 business accounts",
        "geo_holdout": "Geo holdout",
        "difference_in_differences": "Difference in differences",
        "synthetic_control": "Synthetic control",
        "marketing_mix_model": "Marketing mix model",
        "off_policy_evaluation": "Off-policy evaluation",
    }
    return known.get(raw, raw.replace("_", " ").strip().capitalize() or "Not available")


def fmt(value: object, digits: int = 1) -> str:
    parsed = number(value)
    if parsed is None:
        return "Not available"
    if abs(parsed - round(parsed)) < 10 ** (-(digits + 1)):
        return f"{round(parsed):,}"
    return f"{parsed:,.{digits}f}"


def signed(value: object, digits: int = 1) -> str:
    parsed = number(value)
    if parsed is None:
        return "Not available"
    return f"{'+' if parsed > 0 else ''}{parsed:,.{digits}f}"


def percent(value: object) -> str:
    parsed = number(value)
    if parsed is None:
        return "Not available"
    parsed = parsed * 100 if abs(parsed) <= 2 else parsed
    return f"{'+' if parsed > 0 else ''}{parsed:.1f}%"


def date(value: object) -> str:
    raw = text(value, "")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw or "Not available"
    return parsed.strftime("%b %-d, %Y")


def short(value: object, limit: int = 28) -> str:
    raw = text(value)
    if len(raw) <= limit:
        return raw
    keep = max(6, (limit - 3) // 2)
    return f"{raw[:keep]}...{raw[-keep:]}"


def safe(value: object) -> str:
    return escape(text(value))


STYLES = {
    "title": ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=INK
    ),
    "subtitle": ParagraphStyle(
        "subtitle", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=PURPLE
    ),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.2, leading=11, textColor=MUTED),
    "dark": ParagraphStyle("dark", fontName="Helvetica", fontSize=8.2, leading=11, textColor=INK),
    "eyebrow": ParagraphStyle(
        "eyebrow", fontName="Helvetica-Bold", fontSize=6.6, leading=8, textColor=PURPLE
    ),
    "headline": ParagraphStyle(
        "headline", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK
    ),
    "label": ParagraphStyle(
        "label", fontName="Helvetica", fontSize=6.6, leading=8, textColor=MUTED
    ),
    "value": ParagraphStyle(
        "value", fontName="Helvetica-Bold", fontSize=19, leading=21, textColor=PURPLE
    ),
    "green": ParagraphStyle(
        "green", fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=GREEN
    ),
    "small": ParagraphStyle(
        "small", fontName="Helvetica", fontSize=6.3, leading=8, textColor=MUTED
    ),
    "row_label": ParagraphStyle(
        "row_label", fontName="Helvetica", fontSize=7.1, leading=9, textColor=MUTED
    ),
    "row_value": ParagraphStyle(
        "row_value", fontName="Helvetica-Bold", fontSize=7.1, leading=9, textColor=INK
    ),
    "chip_t": ParagraphStyle(
        "chip_t",
        fontName="Helvetica-Bold",
        fontSize=7.1,
        leading=9,
        textColor=PURPLE,
        alignment=TA_CENTER,
    ),
    "chip_h": ParagraphStyle(
        "chip_h",
        fontName="Helvetica-Bold",
        fontSize=7.1,
        leading=9,
        textColor=GREEN,
        alignment=TA_CENTER,
    ),
}


def para(value: object, style: str) -> Paragraph:
    return Paragraph(safe(value), STYLES[style])


def title_block(title: str, subtitle: str, description: str) -> list[Flowable]:
    return [
        para(title, "title"),
        para(subtitle, "subtitle"),
        para(description, "body"),
        Spacer(1, 10),
    ]


def card(
    label: str, value: str, note: str, *, green: bool = False, width: float = CONTENT / 4 - 7
) -> Table:
    content = [
        para(label, "label"),
        Spacer(1, 5),
        para(value, "green" if green else "value"),
        Spacer(1, 3),
        para(note, "small"),
    ]
    table = Table([[content]], colWidths=[width], rowHeights=[78])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("ROUNDEDCORNERS", [8]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def callout(label: str, headline: str, body: str, *, green: bool = False) -> Table:
    color = GREEN if green else PURPLE
    icon_style = ParagraphStyle(
        "icon",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=22,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    icon = Table(
        [[Paragraph("&#10003;" if green else "&#9733;", icon_style)]],
        colWidths=[42],
        rowHeights=[42],
    )
    icon.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("ROUNDEDCORNERS", [21]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    body_flow = [
        para(label.upper(), "eyebrow"),
        para(headline, "headline"),
        Spacer(1, 2),
        para(body, "body"),
    ]
    table = Table([[icon, body_flow]], colWidths=[52, CONTENT - 78], rowHeights=[76])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT if green else PURPLE_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.8, GREEN_LINE if green else PURPLE_LINE),
                ("ROUNDEDCORNERS", [10]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def properties(rows: Sequence[tuple[str, object]], width: float) -> Table:
    data = [[para(label, "row_label"), para(value, "row_value")] for label, value in rows]
    table = Table(data, colWidths=[width * 0.43, width * 0.57])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
            ]
        )
    )
    return table


class GeoMap(Flowable):  # type: ignore[misc]
    OUTLINE = (
        (-124.7, 48.6),
        (-123.1, 46),
        (-124, 42),
        (-122.4, 38),
        (-119, 34.8),
        (-117.2, 32.6),
        (-111, 31.3),
        (-106.5, 31.8),
        (-103, 29.8),
        (-97, 25.9),
        (-90, 29),
        (-85, 29.7),
        (-81, 25.4),
        (-80, 31),
        (-80.5, 35),
        (-75, 38.8),
        (-73.8, 40.7),
        (-69, 44.8),
        (-71, 47),
        (-82.5, 45),
        (-89, 47.7),
        (-96, 49),
        (-105, 49),
        (-114, 49),
        (-124.7, 48.6),
    )

    def __init__(self, assignments: Sequence[Mapping[str, object]], width: float, height: float):
        super().__init__()
        self.assignments = assignments
        self.width = width
        self.height = height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)

        coordinates = [
            (lat, lon)
            for item in self.assignments
            if (lat := number(item.get("latitude"))) is not None
            and (lon := number(item.get("longitude"))) is not None
        ]
        treated_count = sum(item.get("assignment") == "treatment" for item in self.assignments)
        holdout_count = len(self.assignments) - treated_count

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(12, self.height - 17, "Assignment geography")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.2)
        c.drawRightString(
            self.width - 12,
            self.height - 17,
            f"{treated_count} treated  /  {holdout_count} holdout",
        )

        x0, y0, mw, mh = 12, 29, self.width - 24, self.height - 58
        c.setFillColor(SUBTLE)
        c.setStrokeColor(colors.HexColor("#EFEAF8"))
        c.roundRect(x0, y0, mw, mh, 7, fill=1, stroke=1)

        if coordinates:
            latitudes = [lat for lat, _ in coordinates]
            longitudes = [lon for _, lon in coordinates]
            lat_center = (min(latitudes) + max(latitudes)) / 2
            lon_center = (min(longitudes) + max(longitudes)) / 2
            lat_span = max(max(latitudes) - min(latitudes), 1.5) * 1.28
            lon_span = max(max(longitudes) - min(longitudes), 1.5) * 1.28
            lat_min, lon_min = lat_center - lat_span / 2, lon_center - lon_span / 2
        else:
            lat_span, lon_span = 26.5, 60
            lat_min, lon_min = 24, -126

        def project(lon: float, lat: float) -> tuple[float, float]:
            return (
                x0 + (lon - lon_min) / lon_span * mw,
                y0 + (lat - lat_min) / lat_span * mh,
            )

        c.setStrokeColor(colors.HexColor("#EAE6F2"))
        c.setLineWidth(0.35)
        c.setDash(1, 3)
        for i in range(1, 6):
            c.line(x0 + mw * i / 6, y0, x0 + mw * i / 6, y0 + mh)
        for i in range(1, 4):
            c.line(x0, y0 + mh * i / 4, x0 + mw, y0 + mh * i / 4)
        c.setDash()

        if not coordinates:
            points = [project(lon, lat) for lon, lat in self.OUTLINE]
            path = c.beginPath()
            path.moveTo(*points[0])
            for point in points[1:]:
                path.lineTo(*point)
            path.close()
            c.setFillColor(colors.HexColor("#F0F1F4"))
            c.setStrokeColor(colors.HexColor("#D6D8DE"))
            c.drawPath(path, fill=1, stroke=1)

        for item in self.assignments:
            lat, lon = number(item.get("latitude")), number(item.get("longitude"))
            if lat is None or lon is None:
                continue
            x, y = project(lon, lat)
            treatment = item.get("assignment") == "treatment"
            c.setFillColor(PURPLE_SOFT if treatment else GREEN_SOFT)
            c.setStrokeColor(PURPLE_LINE if treatment else GREEN_LINE)
            c.setLineWidth(0.5)
            c.circle(x, y, 6.1, fill=1, stroke=1)

            c.setFillColor(PURPLE if treatment else colors.white)
            c.setStrokeColor(colors.white if treatment else GREEN)
            c.setLineWidth(1.35)
            c.circle(x, y, 3.8, fill=1, stroke=1)
            if not treatment:
                c.setFillColor(GREEN)
                c.circle(x, y, 1.25, fill=1, stroke=0)

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 5.8)
        c.drawString(x0 + 7, y0 + mh - 11, "LOCAL ASSIGNMENT VIEW")

        c.setFont("Helvetica", 6.4)
        c.setFillColor(MUTED)
        c.drawString(16, 11, "Treated geographies")
        c.setFillColor(PURPLE)
        c.setStrokeColor(colors.white)
        c.setLineWidth(1)
        c.circle(9, 13, 3.2, fill=1, stroke=1)

        c.setFillColor(MUTED)
        c.drawString(122, 11, "Holdout geographies")
        c.setFillColor(colors.white)
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.2)
        c.circle(115, 13, 3.2, fill=1, stroke=1)
        c.setFillColor(GREEN)
        c.circle(115, 13, 1, fill=1, stroke=0)
        c.restoreState()


class Gauge(Flowable):  # type: ignore[misc]
    def __init__(self, value: float | None, width: float, height: float):
        super().__init__()
        self.value = value
        self.width = width
        self.height = height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(SUBTLE)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(14, self.height - 20, "Balance diagnostics")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.7)
        c.drawString(14, self.height - 32, "Pre-period standardized mean difference")
        cx, cy, radius = self.width / 2, 58, min(self.width * 0.33, 62)
        c.setLineWidth(9)
        c.setStrokeColor(PURPLE_LINE)
        c.arc(cx - radius, cy - radius, cx + radius, cy + radius, 0, 180)
        c.setStrokeColor(GREEN_LINE)
        c.arc(cx - radius, cy - radius, cx + radius, cy + radius, 0, 90)
        bounded = 0 if self.value is None else max(-1, min(1, self.value))
        angle = math.radians(90 - bounded * 78)
        nx, ny = cx + math.cos(angle) * (radius - 8), cy + math.sin(angle) * (radius - 8)
        c.setStrokeColor(INK)
        c.setLineWidth(2)
        c.line(cx, cy, nx, ny)
        c.setFillColor(INK)
        c.circle(cx, cy, 4, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(cx - radius - 4, cy - 12, "-1")
        c.drawCentredString(cx, cy + radius + 3, "0")
        c.drawString(cx + radius - 3, cy - 12, "1")
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(cx, 24, fmt(self.value, 2))
        c.setFillColor(GREEN if self.value is not None and abs(self.value) <= 0.1 else MUTED)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(
            cx,
            12,
            "Well balanced"
            if self.value is not None and abs(self.value) <= 0.1
            else "Review balance",
        )
        c.restoreState()


class ComparisonChart(Flowable):  # type: ignore[misc]
    def __init__(
        self,
        series: Sequence[Mapping[str, object]],
        *,
        width: float,
        height: float,
        title: str = "Observed versus expected outcome",
    ):
        super().__init__()
        self.series = series
        self.width = width
        self.height = height
        self.title = title

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(14, self.height - 20, self.title)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(MUTED)
        c.drawString(14, self.height - 31, "Saved estimator diagnostic series")

        points = [
            (
                index,
                number(item.get("observed")),
                number(item.get("counterfactual")),
                number(item.get("period")),
            )
            for index, item in enumerate(self.series)
        ]
        valid = [item for item in points if item[1] is not None and item[2] is not None]
        if len(valid) < 2:
            self._empty(c)
            c.restoreState()
            return

        left, bottom = 38, 34
        chart_width = self.width - left - 16
        chart_height = self.height - bottom - 50
        values = [value for item in valid for value in item[1:3] if value is not None]
        minimum, maximum = min(values), max(values)
        padding = max((maximum - minimum) * 0.12, 1)
        minimum -= padding
        maximum += padding

        def x(index: int) -> float:
            return left + index / max(1, len(points) - 1) * chart_width

        def y(value: float) -> float:
            return bottom + (value - minimum) / max(maximum - minimum, 1e-9) * chart_height

        c.setStrokeColor(colors.HexColor("#ECE9F2"))
        c.setLineWidth(0.45)
        for line_index in range(4):
            line_y = bottom + line_index / 3 * chart_height
            c.line(left, line_y, left + chart_width, line_y)
            label = minimum + line_index / 3 * (maximum - minimum)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 5.8)
            c.drawRightString(left - 5, line_y - 2, fmt(label, 0))

        intervention_index = next(
            (
                index
                for index, _, _, period in points
                if period is not None and period >= 0
            ),
            None,
        )
        if intervention_index is not None:
            intervention_x = x(intervention_index)
            c.setStrokeColor(colors.HexColor("#B9B3C8"))
            c.setDash(2, 2)
            c.line(intervention_x, bottom, intervention_x, bottom + chart_height)
            c.setDash()
            c.setFillColor(MUTED)
            c.setFont("Helvetica-Bold", 5.6)
            c.drawCentredString(intervention_x, bottom + chart_height + 5, "INTERVENTION")

        self._line(c, valid, x=x, y=y, value_index=1, color=PURPLE, dashed=False)
        self._line(
            c,
            valid,
            x=x,
            y=y,
            value_index=2,
            color=colors.HexColor("#8FCDB2"),
            dashed=True,
        )
        self._legend(c)
        c.restoreState()

    def _line(
        self,
        canvas: Canvas,
        points: Sequence[tuple[int, float | None, float | None, float | None]],
        *,
        x: object,
        y: object,
        value_index: int,
        color: object,
        dashed: bool,
    ) -> None:
        project_x = x
        project_y = y
        path = canvas.beginPath()
        started = False
        canvas.setStrokeColor(color)
        canvas.setFillColor(color)
        canvas.setLineWidth(1.6)
        if dashed:
            canvas.setDash(4, 2)
        for point in points:
            value = point[value_index]
            if value is None:
                continue
            point_x = project_x(point[0])  # type: ignore[operator]
            point_y = project_y(value)  # type: ignore[operator]
            if started:
                path.lineTo(point_x, point_y)
            else:
                path.moveTo(point_x, point_y)
                started = True
            canvas.circle(point_x, point_y, 2.1, fill=1, stroke=0)
        canvas.drawPath(path, fill=0, stroke=1)
        canvas.setDash()

    def _legend(self, canvas: Canvas) -> None:
        canvas.setFont("Helvetica", 6.2)
        canvas.setFillColor(PURPLE)
        canvas.circle(14, 14, 2.5, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.drawString(20, 12, "Observed")
        canvas.setFillColor(colors.HexColor("#8FCDB2"))
        canvas.circle(72, 14, 2.5, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.drawString(78, 12, "Expected without treatment")

    def _empty(self, canvas: Canvas) -> None:
        canvas.setFillColor(SUBTLE)
        canvas.roundRect(14, 28, self.width - 28, self.height - 72, 7, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(
            self.width / 2,
            self.height / 2 - 4,
            "Time-series diagnostic data was not captured for this run.",
        )


class EffectChart(Flowable):  # type: ignore[misc]
    def __init__(
        self,
        series: Sequence[Mapping[str, object]],
        *,
        width: float,
        height: float,
        title: str = "Effect over time",
    ):
        super().__init__()
        self.series = series
        self.width = width
        self.height = height
        self.title = title

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(14, self.height - 20, self.title)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(MUTED)
        c.drawString(14, self.height - 31, "Estimated effect with available uncertainty")

        points: list[tuple[float, float, float, float]] = []
        for index, item in enumerate(self.series):
            effect = number(item.get("coefficient") if "coefficient" in item else item.get("effect"))
            if effect is None:
                continue
            low = number(item.get("confidence_interval_low"))
            high = number(item.get("confidence_interval_high"))
            period = number(item.get("period"))
            points.append(
                (
                    float(index) if period is None else period,
                    effect,
                    effect if low is None else low,
                    effect if high is None else high,
                )
            )
        if not points:
            c.setFillColor(SUBTLE)
            c.roundRect(14, 28, self.width - 28, self.height - 72, 7, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7)
            c.drawCentredString(
                self.width / 2,
                self.height / 2 - 4,
                "Effect-over-time diagnostics were not captured for this run.",
            )
            c.restoreState()
            return

        left, bottom = 38, 34
        chart_width = self.width - left - 16
        chart_height = self.height - bottom - 50
        minimum = min(0.0, *(point[2] for point in points))
        maximum = max(0.0, *(point[3] for point in points))
        padding = max((maximum - minimum) * 0.12, 1)
        minimum -= padding
        maximum += padding

        def x(index: int) -> float:
            return left + index / max(1, len(points) - 1) * chart_width

        def y(value: float) -> float:
            return bottom + (value - minimum) / max(maximum - minimum, 1e-9) * chart_height

        c.setStrokeColor(colors.HexColor("#ECE9F2"))
        c.setLineWidth(0.45)
        for line_index in range(4):
            line_y = bottom + line_index / 3 * chart_height
            c.line(left, line_y, left + chart_width, line_y)
        c.setStrokeColor(colors.HexColor("#9A94A8"))
        c.setDash(2, 2)
        c.line(left, y(0), left + chart_width, y(0))
        c.setDash()

        for index, (period, effect, low, high) in enumerate(points):
            point_x = x(index)
            c.setStrokeColor(colors.HexColor("#9A86F2"))
            c.setLineWidth(1)
            c.line(point_x, y(low), point_x, y(high))
            c.setFillColor(PURPLE)
            c.circle(point_x, y(effect), 2.8, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 5.6)
            c.drawCentredString(point_x, 20, fmt(period, 0))
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6)
        c.drawString(14, 12, "Event time")
        c.restoreState()


def chips(items: Sequence[Mapping[str, object]], *, treatment: bool) -> Table:
    values = [text(item.get("geo"), "Unknown") for item in items[:16]]
    if len(items) > 16:
        values[-1] = f"+{len(items) - 15} more"
    rows = []
    for start in range(0, max(1, len(values)), 4):
        row = values[start : start + 4]
        row.extend([""] * (4 - len(row)))
        rows.append([para(value, "chip_t" if treatment else "chip_h") for value in row])
    table = Table(rows, colWidths=[54] * 4, rowHeights=[27] * len(rows))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PURPLE_SOFT if treatment else GREEN_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, PURPLE_LINE if treatment else GREEN_LINE),
                ("INNERGRID", (0, 0), (-1, -1), 4, colors.white),
                ("ROUNDEDCORNERS", [7]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


class PdfReportRenderer:
    media_type = "application/pdf"
    extension = "pdf"

    def render(self, model: ReportModel) -> bytes:
        out = io.BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=letter,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=66,
            bottomMargin=42,
            title=model.title,
            author="Incrementality",
            subject="Measurement evidence report",
            pageCompression=1,
            invariant=1,
        )
        config, diagnostics, impact, quality, lineage = map(
            dict,
            (
                model.configuration,
                model.diagnostics,
                model.business_impact,
                model.quality_summary,
                model.lineage,
            ),
        )
        semantic = mapping(deep(lineage, {"semantic_mapping_snapshot"}))
        selection = mapping(deep(lineage, {"analysis_selection_snapshot"}))
        geography_column = (
            selection.get("geography_column")
            or deep(config, {"geography_column", "unit_column"})
            or semantic.get("unit_column")
        )
        assignments = [
            dict(item)
            for item in sequence(diagnostics.get("geographic_assignments"))
            if isinstance(item, Mapping)
        ]
        treated = [item for item in assignments if item.get("assignment") == "treatment"]
        holdout = [item for item in assignments if item.get("assignment") == "holdout"]
        is_geo = model.estimator == "geo_holdout"
        is_ope = model.estimator == "off_policy_evaluation"
        relative_lift = deep_number(impact, "relative_lift")
        incremental = deep_number(
            impact,
            "incremental_outcome",
            "incremental_revenue",
            "incremental_conversions",
            "incremental_impact",
        )
        sample_size = deep_number(
            {"d": diagnostics, "q": quality, "c": config},
            "sample_size",
            "observation_count",
            "observations",
        )
        standard_error = number(model.standard_error)
        p_value = number(model.p_value)
        balance = deep_number(
            mapping(diagnostics.get("balance_diagnostics")), "standardized_mean_difference"
        )
        treated_units = deep_number(diagnostics, "treated_units")
        control_units = deep_number(diagnostics, "control_units")
        if is_geo:
            treated_units = treated_units if treated_units is not None else float(len(treated))
            control_units = control_units if control_units is not None else float(len(holdout))
        parallel = mapping(diagnostics.get("parallel_trends"))
        parallel_passed = parallel.get("passed") is True
        pre_rmspe = deep_number(diagnostics, "pre_treatment_rmspe")
        effective_sample_size = deep_number(diagnostics, "effective_sample_size")
        max_r_hat = deep_number(diagnostics, "max_r_hat")
        if model.estimator == "difference_in_differences":
            comparability_label = "Parallel trends"
            comparability_value = "Passed" if parallel_passed else "Review"
            comparability_note = "Pre-period diagnostic"
        elif model.estimator == "synthetic_control":
            comparability_label = "Pre-treatment RMSPE"
            comparability_value = fmt(pre_rmspe, 2)
            comparability_note = "Counterfactual fit"
        elif model.estimator == "marketing_mix_model":
            comparability_label = "Maximum R-hat"
            comparability_value = fmt(max_r_hat, 2)
            comparability_note = "Posterior convergence"
        elif model.estimator == "off_policy_evaluation":
            comparability_label = "Effective sample size"
            comparability_value = fmt(effective_sample_size, 0)
            comparability_note = "Weighted policy evidence"
        else:
            comparability_label = "Pre-period comparability"
            comparability_value = fmt(balance, 2)
            comparability_note = "Standardized mean difference"
        design = human(
            diagnostics.get("design_assessment") or quality.get("design_assessment") or "valid"
        )
        causal = diagnostics.get("causal_claim_allowed") is True
        outcome = human(deep({"c": config, "l": lineage}, {"target_outcome", "outcome_column"}))
        is_ope_probability = is_ope and outcome.lower() == "conversion"
        policy_ready = diagnostics.get("recommendations_allowed") is True or (
            diagnostics.get("recommendations_allowed") is None
            and str(diagnostics.get("reliability") or "").lower() == "strong"
        )
        reliability = human(diagnostics.get("reliability"))
        primary_method = human(
            diagnostics.get("primary_method") or deep(config, {"primary_method"})
        )
        policy_value = (
            f"{fmt(model.estimate * 100, 1)}%"
            if is_ope_probability
            else fmt(model.estimate, 3)
        )
        policy_interval = (
            f"{fmt(model.confidence_low * 100, 1)}% to {fmt(model.confidence_high * 100, 1)}%"
            if is_ope_probability
            else f"{fmt(model.confidence_low, 3)} to {fmt(model.confidence_high, 3)}"
        )
        analysis_start, analysis_end, intervention = (
            deep(config, {"analysis_start_date"}),
            deep(config, {"analysis_end_date"}),
            deep(config, {"intervention_date"}),
        )
        p_text = (
            "p < 0.001"
            if p_value is not None and p_value < 0.001
            else (f"p = {p_value:.3f}" if p_value is not None else "p unavailable")
        )
        inference_summary = (
            f"95% confidence interval {policy_interval}."
            if is_ope
            else (
                f"95% normal-approximation interval {fmt(model.confidence_low, 1)} to "
                f"{fmt(model.confidence_high, 1)} (using the placebo-effect standard error). "
                f"In-space placebo inference: {p_text}."
                if model.estimator == "synthetic_control"
                else f"95% confidence interval {fmt(model.confidence_low, 1)} to "
                f"{fmt(model.confidence_high, 1)}. {p_text}"
            )
        )
        story: list[Flowable] = []

        story += title_block(
            model.title,
            "Executive summary",
            (
                f"This report summarizes the estimated target-policy value for {outcome.lower()} using off-policy evaluation."
                if is_ope
                else f"This report summarizes the incremental effect on {outcome.lower()} using a {human(model.estimator).lower()} design."
            ),
        )
        story += [
            callout(
                "Analysis conclusion",
                (
                    "The saved overlap and weight diagnostics support this policy-value estimate for decision support."
                    if policy_ready
                    else "The policy-value estimate requires cautious interpretation because the saved overlap diagnostics need review."
                )
                if is_ope
                else (
                    "The saved diagnostics support a credible incremental effect."
                    if causal
                    else "The estimate is directional and requires cautious interpretation."
                ),
                (
                    "This run estimates target-policy value, not improvement versus the behavior policy."
                    if is_ope
                    else (
                        "The estimate is supported by the saved diagnostic evidence."
                        if causal
                        else "Review the diagnostics before using this result for a decision."
                    )
                ),
            ),
            Spacer(1, 10),
        ]
        summary_cards = (
            [
                card(
                    "Estimated policy value",
                    policy_value,
                    "Expected outcome under the target policy",
                ),
                card(
                    "Policy improvement vs behavior policy",
                    "Not estimated",
                    "This run estimates target-policy value only.",
                ),
                card(
                    "Overlap quality",
                    reliability,
                    "Historical policy support is sufficient for estimation."
                    if policy_ready
                    else "Review propensity overlap before acting.",
                    green=policy_ready,
                ),
                card(
                    "Effective sample size",
                    fmt(effective_sample_size, 0),
                    "Weighted policy evidence",
                ),
            ]
            if is_ope
            else [
                card(
                    "Estimated lift", percent(relative_lift), "Relative to expected outcome"
                ),
                card(
                    "Incremental outcome",
                    fmt(incremental, 0),
                    "Across treated observations",
                ),
                card(
                    "Design quality",
                    design,
                    "Meets current diagnostic policy"
                    if design.lower() == "valid"
                    else "Does not meet current diagnostic policy",
                    green=design.lower() == "valid",
                ),
                card(
                    comparability_label,
                    comparability_value,
                    comparability_note,
                ),
            ]
        )
        story += [
            Table([summary_cards], colWidths=[CONTENT / 4] * 4),
            Spacer(1, 10),
        ]
        story += [
            callout(
                "Business recommendation",
                (
                    "Use this target-policy value with the documented assumptions and overlap evidence."
                    if is_ope
                    else "Use this result with the documented assumptions and diagnostic evidence."
                ),
                (
                    "The saved policy diagnostics allow this estimate to support a decision."
                    if policy_ready
                    else "The current policy diagnostics support exploration rather than deployment."
                )
                if is_ope
                else (
                    "The diagnostic policy allows this estimate to support a decision."
                    if causal
                    else "The current evidence supports exploration, not a definitive causal decision."
                ),
                green=policy_ready if is_ope else causal,
            ),
            Spacer(1, 10),
            para("STUDY OVERVIEW", "eyebrow"),
        ]
        story += [
            properties(
                (
                    (
                        ("Method", human(model.estimator)),
                        ("Analysis period", f"{date(analysis_start)} to {date(analysis_end)}"),
                        ("Outcome", outcome),
                        ("Primary method", primary_method),
                        ("Observations", fmt(sample_size, 0)),
                        ("Effective sample size", fmt(effective_sample_size, 0)),
                    )
                    if is_ope
                    else (
                        ("Method", human(model.estimator)),
                        ("Analysis period", f"{date(analysis_start)} to {date(analysis_end)}"),
                        ("Intervention date", date(intervention)),
                        ("Outcome", outcome),
                        (
                            "Treated / control geographies" if is_geo else "Treated / control units",
                            f"{fmt(treated_units, 0)} / {fmt(control_units, 0)}",
                        ),
                        ("Observations", fmt(sample_size, 0)),
                    )
                ),
                CONTENT,
            ),
            Spacer(1, 9),
        ]
        ci = Table(
            [
                [
                    para(
                        inference_summary,
                        "dark",
                    )
                ]
            ],
            colWidths=[CONTENT],
            rowHeights=[30],
        )
        ci.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PURPLE_SOFT),
                    ("BOX", (0, 0), (-1, -1), 0.8, PURPLE_LINE),
                    ("ROUNDEDCORNERS", [7]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story += [ci, PageBreak()]

        story += title_block(
            model.title,
            "Key findings and diagnostics",
            "Detailed results from the saved estimator output and supporting diagnostic evidence.",
        )
        page_two_cards = (
            [
                card(
                    "Estimated policy value",
                    policy_value,
                    "Expected outcome under the target policy",
                    width=CONTENT / 3 - 7,
                ),
                card(
                    "Policy improvement vs behavior policy",
                    "Not estimated",
                    "Target-policy value only",
                    width=CONTENT / 3 - 7,
                ),
                card(
                    "Primary method",
                    primary_method,
                    "Estimator used for the reported policy value",
                    width=CONTENT / 3 - 7,
                ),
            ]
            if is_ope
            else [
                card(
                    "Estimated lift",
                    percent(relative_lift),
                    "Relative to expected outcome",
                    width=CONTENT / 3 - 7,
                ),
                card(
                    "Incremental outcome",
                    fmt(incremental, 0),
                    "Across treated observations",
                    width=CONTENT / 3 - 7,
                ),
                card(
                    "Effect per treated observation",
                    signed(model.estimate),
                    "Average estimated change",
                    width=CONTENT / 3 - 7,
                ),
            ]
        )
        story += [
            Table([page_two_cards], colWidths=[CONTENT / 3] * 3),
            Spacer(1, 10),
        ]
        if is_geo:
            evidence_visuals: list[Flowable] = [
                Table(
                    [
                        [
                            GeoMap(assignments, CONTENT * 0.62 - 6, 220),
                            Gauge(balance, CONTENT * 0.38 - 6, 220),
                        ]
                    ],
                    colWidths=[CONTENT * 0.62, CONTENT * 0.38],
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ]
                    ),
                ),
                Spacer(1, 10),
            ]
        elif model.estimator in {"difference_in_differences", "synthetic_control"}:
            observed_series = [
                dict(item)
                for item in sequence(diagnostics.get("observed_vs_counterfactual"))
                if isinstance(item, Mapping)
            ]
            effect_key = (
                "event_study"
                if model.estimator == "difference_in_differences"
                else "treatment_effects_over_time"
            )
            effect_series = [
                dict(item)
                for item in sequence(diagnostics.get(effect_key))
                if isinstance(item, Mapping)
            ]
            evidence_visuals = [
                Table(
                    [
                        [
                            ComparisonChart(
                                observed_series,
                                width=CONTENT * 0.5 - 6,
                                height=220,
                            ),
                            EffectChart(
                                effect_series,
                                width=CONTENT * 0.5 - 6,
                                height=220,
                            ),
                        ]
                    ],
                    colWidths=[CONTENT * 0.5] * 2,
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ]
                    ),
                ),
                Spacer(1, 10),
            ]
        elif is_ope:
            overlap = mapping(diagnostics.get("propensity_overlap"))
            evidence_visuals = [
                Table(
                    [
                        [
                            properties(
                                (
                                    ("Evidence type", "Historical policy evaluation"),
                                    ("Primary method", primary_method),
                                    ("Effective sample size", fmt(effective_sample_size, 0)),
                                    ("Reliability", reliability),
                                ),
                                CONTENT * 0.48,
                            ),
                            properties(
                                (
                                    (
                                        "Maximum importance weight",
                                        fmt(overlap.get("maximum_importance_weight"), 2),
                                    ),
                                    (
                                        "Extreme weights",
                                        fmt(diagnostics.get("extreme_weight_count"), 0),
                                    ),
                                    ("Policy improvement", "Not estimated"),
                                ),
                                CONTENT * 0.48,
                            ),
                        ]
                    ],
                    colWidths=[CONTENT * 0.5] * 2,
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ]
                    ),
                ),
                Spacer(1, 10),
            ]
        else:
            convergence = mapping(diagnostics.get("convergence"))
            overlap = mapping(diagnostics.get("propensity_overlap"))
            evidence_visuals = [
                Table(
                    [
                        [
                            properties(
                                (
                                    (
                                        "Evidence type",
                                        "Posterior channel contribution"
                                        if model.estimator == "marketing_mix_model"
                                        else "Historical policy comparison",
                                    ),
                                    (
                                        "Channels",
                                        len(mapping(diagnostics.get("channel_contributions"))),
                                    ),
                                    (
                                        "Effective sample size",
                                        fmt(effective_sample_size, 0),
                                    ),
                                    (
                                        "Reliability",
                                        human(diagnostics.get("reliability")),
                                    ),
                                ),
                                CONTENT * 0.48,
                            ),
                            properties(
                                (
                                    (
                                        "Maximum R-hat",
                                        fmt(convergence.get("max_r_hat"), 2),
                                    ),
                                    (
                                        "Divergences",
                                        fmt(convergence.get("divergences"), 0),
                                    ),
                                    (
                                        "Maximum importance weight",
                                        fmt(overlap.get("maximum_importance_weight"), 2),
                                    ),
                                    (
                                        "Extreme weights",
                                        fmt(diagnostics.get("extreme_weight_count"), 0),
                                    ),
                                ),
                                CONTENT * 0.48,
                            ),
                        ]
                    ],
                    colWidths=[CONTENT * 0.5] * 2,
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ]
                    ),
                ),
                Spacer(1, 10),
            ]
        story += evidence_visuals
        story += [
            Table(
                [
                    [
                        properties(
                            (
                                (
                                    ("Overlap quality", reliability),
                                    (
                                        "Blocking warnings",
                                        "None" if not model.warnings else len(model.warnings),
                                    ),
                                    (
                                        "Policy evidence",
                                        "Decision support" if policy_ready else "Needs review",
                                    ),
                                    ("Effective sample size", fmt(effective_sample_size, 0)),
                                )
                                if is_ope
                                else (
                                    ("Design quality", design),
                                    (
                                        "Blocking warnings",
                                        "None" if not model.warnings else len(model.warnings),
                                    ),
                                    ("Causal evidence", "Supported" if causal else "Not supported"),
                                    (comparability_label, comparability_value),
                                )
                            ),
                            CONTENT * 0.48,
                        ),
                        properties(
                            (
                                (
                                    ("Method", human(model.estimator)),
                                    ("Primary method", primary_method),
                                    ("Observations", fmt(sample_size, 0)),
                                    ("Standard error", fmt(standard_error, 3)),
                                    ("Confidence interval", policy_interval),
                                )
                                if is_ope
                                else (
                                    ("Method", human(model.estimator)),
                                    (
                                        "Treated / control geographies"
                                        if is_geo
                                        else "Treated / control units",
                                        f"{fmt(treated_units, 0)} / {fmt(control_units, 0)}",
                                    ),
                                    ("Observations", fmt(sample_size, 0)),
                                    ("Standard error", fmt(standard_error, 3)),
                                    (
                                        "Confidence interval",
                                        f"{fmt(model.confidence_low, 1)} to {fmt(model.confidence_high, 1)}",
                                    ),
                                )
                            ),
                            CONTENT * 0.48,
                        ),
                    ]
                ],
                colWidths=[CONTENT * 0.5] * 2,
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 10),
        ]
        story += [
            callout(
                "Decision takeaway",
                (
                    "The target-policy value is supported by the saved overlap and weight diagnostics."
                    if policy_ready
                    else "The target-policy value should be interpreted cautiously until overlap diagnostics improve."
                )
                if is_ope
                else (
                    "The result is directionally strong and supported by the documented diagnostics."
                    if causal
                    else "The result is directional and should be interpreted cautiously."
                ),
                (
                    "Use the estimate only within the saved population, period, and policy-assignment assumptions; it is not an estimate of policy improvement."
                    if is_ope
                    else "Use the estimate only within the saved population, period, and assignment assumptions."
                ),
            ),
            PageBreak(),
        ]

        detail_title = (
            "Geography detail and business interpretation"
            if is_geo
            else "Design diagnostics and interpretation"
        )
        detail_description = (
            "Detailed view of the experimental design across geographies and how to interpret the result."
            if is_geo
            else "Method-specific evidence, limitations, and practical guidance for interpreting the estimate."
        )
        story += title_block(model.title, detail_title, detail_description)
        filters = deep(config, {"row_filters", "eligibility_filters"})
        excluded = deep(config, {"excluded_geographies"})
        if is_geo:
            assignment = Table(
                [
                    [
                        [
                            para("TREATED GEOGRAPHIES", "eyebrow"),
                            Spacer(1, 5),
                            chips(treated, treatment=True),
                        ],
                        [
                            para("CONTROL GEOGRAPHIES (HOLDOUT)", "eyebrow"),
                            Spacer(1, 5),
                            chips(holdout, treatment=False),
                        ],
                    ]
                ],
                colWidths=[CONTENT / 2] * 2,
                rowHeights=[118],
            )
            assignment.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, PURPLE_LINE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                        ("ROUNDEDCORNERS", [10]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ]
                )
            )
            story += [assignment, Spacer(1, 10)]

        if is_ope:
            interpretation = f"The estimated target-policy value is {policy_value}."
            interpretation_evidence = (
                "Overlap and weight diagnostics support policy evaluation for the saved target policy."
                if policy_ready
                else "Overlap and weight diagnostics require review before relying on the saved target policy."
            )
            interpretation_scope = (
                "This run does not estimate improvement versus the behavior policy."
            )
        else:
            interpretation = (
                "The intervention is associated with an increase in the mapped outcome."
                if model.estimate > 0
                else "The intervention is associated with a reduction in the mapped outcome."
            )
            interpretation_evidence = (
                "The saved diagnostics support causal interpretation."
                if causal
                else "The saved diagnostics do not support a definitive causal interpretation."
            )
            interpretation_scope = (
                "Apply the estimate only to the documented population, period, and assignment."
            )
        interpretation_box = Table(
            [
                [
                    [
                        para("BUSINESS INTERPRETATION", "eyebrow"),
                        Spacer(1, 6),
                        Paragraph(
                            f"- {escape(interpretation)}<br/>"
                            f"- {escape(interpretation_evidence)}<br/>"
                            f"- {escape(interpretation_scope)}",
                            STYLES["dark"],
                        ),
                    ]
                ]
            ],
            colWidths=[CONTENT * 0.47],
            rowHeights=[146],
        )
        interpretation_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                    ("ROUNDEDCORNERS", [8]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        if is_geo:
            design_rows: Sequence[tuple[str, object]] = (
                ("Row filters", "None" if not filters else short(filters, 60)),
                ("Included geographies", len(treated) + len(holdout)),
                (
                    "Excluded geographies",
                    "None" if not excluded else short(excluded, 60),
                ),
                ("Geography column", text(geography_column)),
                ("Outcome", outcome),
            )
        elif is_ope:
            design_rows = (
                ("Method", human(model.estimator)),
                ("Primary method", primary_method),
                ("Overlap quality", reliability),
                ("Effective sample size", fmt(effective_sample_size, 0)),
                ("Outcome", outcome),
            )
        else:
            design_rows = (
                ("Method", human(model.estimator)),
                ("Design quality", design),
                (comparability_label, comparability_value),
                ("Treated / control units", f"{fmt(treated_units, 0)} / {fmt(control_units, 0)}"),
                ("Outcome", outcome),
            )
        story += [
            Table(
                [[properties(design_rows, CONTENT * 0.47), interpretation_box]],
                colWidths=[CONTENT * 0.5] * 2,
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 10),
        ]
        default_assumptions = {
            "difference_in_differences": (
                "Parallel trends should hold before the intervention.",
                "Treatment timing and group membership are correctly mapped.",
                "No unmodeled event differentially affects one group at intervention.",
            ),
            "synthetic_control": (
                "The donor pool can reproduce the treated unit before intervention.",
                "No donor is materially affected by the intervention.",
                "The pre-treatment fit remains informative after intervention.",
            ),
            "geo_holdout": (
                "Holdout geographies remain comparable absent the intervention.",
                "Spillovers between treated and holdout geographies are limited.",
                "External shocks do not differentially affect the groups.",
            ),
            "marketing_mix_model": (
                "Media inputs and outcomes are consistently measured over time.",
                "The model specification captures material seasonality and response shape.",
                "Posterior convergence is sufficient for business interpretation.",
            ),
            "off_policy_evaluation": (
                "Logged behavior propensities are valid and strictly positive.",
                "The target policy has adequate overlap with historical decisions.",
                "For doubly robust estimation, consistency can hold when either the behavior-propensity specification or the reward model is correct, provided the policy-evaluation identifying assumptions hold.",
            ),
        }
        assumptions = list(model.limitations) or list(
            default_assumptions.get(
                model.estimator,
                ("Interpret the estimate within the documented analysis design.",),
            )
        )
        assumption_box = Table(
            [
                [
                    [
                        para("ASSUMPTIONS AND LIMITATIONS", "eyebrow"),
                        Spacer(1, 5),
                        Paragraph(
                            "<br/>".join(f"- {escape(item)}" for item in assumptions[:5]),
                            STYLES["dark"],
                        ),
                    ]
                ]
            ],
            colWidths=[CONTENT],
            rowHeights=[105],
        )
        assumption_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.7, PURPLE_LINE),
                    ("ROUNDEDCORNERS", [8]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story += [
            assumption_box,
            Spacer(1, 10),
            callout(
                "Decision takeaway",
                (
                    "The analysis can inform whether to deploy, refine, or reject the target policy."
                    if policy_ready
                    else "The analysis can guide further validation and refinement of the target policy."
                )
                if is_ope
                else (
                    "The analysis can inform whether to scale, continue, or refine the intervention."
                    if causal
                    else "The analysis can guide further validation and refinement of the intervention."
                ),
                (
                    "Apply the result only to the documented population, time window, and saved policy assumptions."
                    if is_ope
                    else "Apply the result only to the documented population and time window."
                ),
                green=policy_ready if is_ope else causal,
            ),
            PageBreak(),
        ]

        libraries = deep(lineage, {"statistical_library_versions", "libraries"})
        source_revision = deep(lineage, {"source_revision"}) or "Not available"
        random_seed = deep(lineage, {"random_seed"}) or deep(config, {"random_seed"})
        fingerprint = deep(lineage, {"input_fingerprint_sha256", "input_fingerprint"})
        story += title_block(
            model.title,
            "Reproducibility appendix",
            "Technical appendix documenting the immutable inputs, configuration, and execution lineage for this analysis.",
        )
        story += [
            callout(
                "Reproducibility status",
                "Verified - all available lineage captured",
                "This read-only receipt preserves the analysis inputs and execution identity used for the result.",
                green=True,
            ),
            Spacer(1, 10),
        ]
        treatment_snapshot = mapping(
            deep(
                lineage,
                {"treatment_control_snapshot"},
            )
        )

        treated_names = [text(item.get("geo"), "") for item in treated if text(item.get("geo"), "")]

        if not treated_names:
            treated_names = [
                text(item)
                for item in sequence(
                    treatment_snapshot.get("treated_units")
                    or treatment_snapshot.get("treatment_units")
                    or treatment_snapshot.get("treated_geographies")
                )
            ]

        control_names = [text(item.get("geo"), "") for item in holdout if text(item.get("geo"), "")]

        if not control_names:
            control_names = [
                text(item)
                for item in sequence(
                    treatment_snapshot.get("control_units")
                    or treatment_snapshot.get("holdout_units")
                    or treatment_snapshot.get("control_geographies")
                )
            ]

        selected_names = [text(item) for item in sequence(selection.get("selected_geographies"))]

        if not selected_names:
            selected_names = [
                *treated_names,
                *control_names,
            ]

        excluded_names = [text(item) for item in sequence(selection.get("excluded_geographies"))]

        covariate_names = [human(item) for item in sequence(semantic.get("covariate_columns"))]

        filter_names = [text(item) for item in sequence(selection.get("row_filters"))]

        library_mapping = mapping(libraries)

        if library_mapping:
            library_summary = " · ".join(
                f"{human(name)} {text(version)}" for name, version in library_mapping.items()
            )
        else:
            library_values = [text(item) for item in sequence(libraries)]

            library_summary = (
                " · ".join(library_values)
                if library_values
                else text(
                    libraries,
                    "Not available",
                )
            )

        application_version = (
            deep(
                lineage,
                {"application_version"},
            )
            or "Not available"
        )

        story += [
            para(
                "EXECUTION IDENTITY",
                "eyebrow",
            ),
            Spacer(1, 4),
        ]

        identity_table = Table(
            [
                [
                    properties(
                        (
                            (
                                "Analysis run ID",
                                short(
                                    model.analysis_run_id,
                                    18,
                                ),
                            ),
                            (
                                "Input fingerprint",
                                short(
                                    fingerprint,
                                    18,
                                ),
                            ),
                        ),
                        CONTENT * 0.48,
                    ),
                    properties(
                        (
                            (
                                "Dataset checksum",
                                short(
                                    model.dataset_checksum,
                                    18,
                                ),
                            ),
                            (
                                "Source revision",
                                short(
                                    source_revision,
                                    18,
                                ),
                            ),
                        ),
                        CONTENT * 0.48,
                    ),
                ]
            ],
            colWidths=[
                CONTENT * 0.5,
                CONTENT * 0.5,
            ],
            style=TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            ),
        )

        story += [
            identity_table,
            Spacer(1, 8),
            para(
                "DATASET AND METHOD",
                "eyebrow",
            ),
            Spacer(1, 4),
        ]

        dataset_method_table = Table(
            [
                [
                    properties(
                        (
                            (
                                "Dataset ID",
                                short(
                                    model.dataset_id,
                                    28,
                                ),
                            ),
                            (
                                "Mapping version",
                                f"v{model.mapping_version}",
                            ),
                            (
                                "Generated on",
                                model.generated_at.astimezone(UTC).strftime(
                                    "%b %-d, %Y %I:%M %p UTC"
                                ),
                            ),
                        ),
                        CONTENT * 0.48,
                    ),
                    properties(
                        (
                            (
                                "Estimator",
                                human(model.estimator),
                            ),
                            (
                                "Estimator version",
                                model.estimator_version,
                            ),
                            (
                                "Random seed",
                                text(
                                    random_seed,
                                    "Not available",
                                ),
                            ),
                            (
                                "Application version",
                                text(application_version),
                            ),
                            (
                                "Libraries",
                                short(
                                    library_summary,
                                    54,
                                ),
                            ),
                        ),
                        CONTENT * 0.48,
                    ),
                ]
            ],
            colWidths=[
                CONTENT * 0.5,
                CONTENT * 0.5,
            ],
            style=TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            ),
        )

        story += [
            dataset_method_table,
            Spacer(1, 8),
            para(
                "MAPPING AND SELECTION",
                "eyebrow",
            ),
            Spacer(1, 4),
        ]

        selected_summary = short(
            ", ".join(selected_names) if selected_names else "None",
            88,
        )

        excluded_summary = short(
            ", ".join(excluded_names) if excluded_names else "None",
            68,
        )

        covariate_summary = short(
            ", ".join(covariate_names) if covariate_names else "None",
            82,
        )

        filter_summary = short(
            " · ".join(filter_names) if filter_names else "None",
            68,
        )

        mapping_selection_table = Table(
            [
                [
                    properties(
                        (
                            (
                                "Time column",
                                text(
                                    semantic.get("time_column")
                                    or deep(
                                        config,
                                        {"time_column"},
                                    ),
                                    "Not available",
                                ),
                            ),
                            (
                                "Unit column",
                                text(
                                    semantic.get("unit_column")
                                    or deep(
                                        config,
                                        {"unit_column"},
                                    ),
                                    "Not available",
                                ),
                            ),
                            (
                                "Treatment column",
                                text(
                                    semantic.get("treatment_column")
                                    or deep(
                                        config,
                                        {"treatment_column"},
                                    ),
                                    "Not available",
                                ),
                            ),
                            (
                                "Outcome column",
                                outcome,
                            ),
                            (
                                "Spend column",
                                text(
                                    semantic.get("spend_column"),
                                    "None",
                                ),
                            ),
                            (
                                "Covariates",
                                covariate_summary,
                            ),
                        ),
                        CONTENT * 0.48,
                    ),
                    properties(
                        (
                            (
                                (
                                    "Row filters",
                                    filter_summary,
                                ),
                                (
                                    "Behavior propensity column",
                                    text(
                                        deep(config, {"behavior_propensity_column"}),
                                        "Not available",
                                    ),
                                ),
                                (
                                    "Target propensity column",
                                    text(
                                        deep(config, {"target_propensity_column"}),
                                        "Not available",
                                    ),
                                ),
                                (
                                    "Reward column",
                                    text(
                                        deep(config, {"reward_column"}),
                                        "Not available",
                                    ),
                                ),
                                (
                                    "Observed-action expected reward",
                                    text(
                                        deep(
                                            config,
                                            {"observed_action_expected_reward_column"},
                                        ),
                                        "Not available",
                                    ),
                                ),
                                (
                                    "Target-policy expected reward",
                                    text(
                                        deep(
                                            config,
                                            {"target_policy_expected_reward_column"},
                                        ),
                                        "Not available",
                                    ),
                                ),
                                ("Primary method", primary_method),
                            )
                            if is_ope
                            else (
                                ("Row filters", filter_summary),
                                (
                                    "Geography column",
                                    text(geography_column, "Not available"),
                                ),
                                ("Selected geographies", selected_summary),
                                ("Excluded geographies", excluded_summary),
                                (
                                    "Treated / control",
                                    (
                                        f"{len(treated_names) if treated_names else int(treated_units or 0)} / "
                                        f"{len(control_names) if control_names else int(control_units or 0)}"
                                    ),
                                ),
                            )
                        ),
                        CONTENT * 0.48,
                    ),
                ]
            ],
            colWidths=[
                CONTENT * 0.5,
                CONTENT * 0.5,
            ],
            style=TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            ),
        )

        story += [
            mapping_selection_table,
            Spacer(1, 8),
        ]

        boundary = Table(
            [
                [
                    [
                        para("REPRODUCIBILITY BOUNDARY", "eyebrow"),
                        Spacer(1, 4),
                        para(
                            "Persisted lineage captures the immutable inputs, configuration, random seed, application source revision, and available library versions used for this analysis. It does not guarantee bit-for-bit identical results across different hardware, operating systems, or numerical backends.",
                            "dark",
                        ),
                    ]
                ]
            ],
            colWidths=[CONTENT],
            rowHeights=[74],
        )
        boundary.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PURPLE_SOFT),
                    ("BOX", (0, 0), (-1, -1), 0.8, PURPLE_LINE),
                    ("ROUNDEDCORNERS", [8]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story += [boundary]

        page_names = dict(PAGE_NAMES)
        if not is_geo:
            page_names[3] = "DESIGN & INTERPRETATION"

        def header_footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
            del document
            canvas.saveState()
            for index, height in enumerate((16, 22, 28)):
                canvas.setFillColor(PURPLE)
                canvas.roundRect(42 + index * 7, H - 44, 4, height, 1.5, fill=1, stroke=0)
            canvas.setFillColor(INK)
            canvas.setFont("Helvetica-Bold", 12)
            canvas.drawString(70, H - 35, "Incrementality")
            canvas.setFillColor(PURPLE)
            canvas.setFont("Helvetica-Bold", 6.5)
            canvas.drawRightString(W - 42, H - 34, "MEASUREMENT EVIDENCE REPORT")
            canvas.setStrokeColor(LINE)
            canvas.line(42, H - 52, W - 42, H - 52)
            page = canvas.getPageNumber()
            canvas.setStrokeColor(PURPLE_LINE)
            canvas.line(42, 28, W - 42, 28)
            canvas.setFillColor(PURPLE)
            canvas.setFont("Helvetica-Bold", 6.5)
            page_label = page_names.get(page, "REPORT")
            canvas.drawString(42, 15, page_label)
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 6.3)
            label_width = canvas.stringWidth(page_label, "Helvetica-Bold", 6.5)
            canvas.drawString(42 + label_width + 16, 15, short(model.title, 38))
            canvas.setFillColor(PURPLE)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawRightString(W - 42, 15, f"{page} of 4")
            canvas.restoreState()

        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        return out.getvalue()
