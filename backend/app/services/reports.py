"""PDF and CSV exports for an owned project."""

import csv
import io
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.constants import DISCLAIMER
from app.models import Expense, Project
from app.services.ai_analysis import analyze_project
from app.services.calculations import money
from app.services.presenters import summary_out


def csv_safe(value):
    """Keep real numbers numeric and neutralize formula-like text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def build_csv(project: Project, expenses: list[Expense]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "project_name",
            "currency",
            "expense_name",
            "category",
            "description",
            "estimated_cost",
            "actual_cost",
            "variance",
            "percentage_variance",
            "expense_date",
            "vendor",
        ]
    )
    for expense in expenses:
        from app.services.calculations import percentage_variance, variance

        difference = variance(expense.actual_cost, expense.estimated_cost)
        percent = percentage_variance(expense.actual_cost, expense.estimated_cost)
        writer.writerow(
            [
                csv_safe(project.name),
                csv_safe(project.currency),
                csv_safe(expense.expense_name),
                csv_safe(expense.category),
                csv_safe(expense.description or ""),
                float(money(expense.estimated_cost)),
                float(money(expense.actual_cost)),
                float(difference),
                "" if percent is None else float(percent),
                expense.expense_date.isoformat(),
                csv_safe(expense.vendor or ""),
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")


def build_pdf(
    project: Project,
    expenses: list[Expense],
    *,
    date_from: date | None,
    date_to: date | None,
    category: str | None,
) -> bytes:
    summary = summary_out(expenses, project.currency, [project.currency])
    analysis = analyze_project(project, expenses, allow_external=False)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="CostWise AI cost report",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#24324a"), fontSize=18, spaceAfter=6)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading2"], textColor=colors.HexColor("#3d4d88"), fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#24324a"))
    small = ParagraphStyle("ReportSmall", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#52627a"))

    story = [
        Paragraph("CostWise AI", title_style),
        Paragraph("Project cost report", heading),
        Paragraph(escape(project.name), body),
        Spacer(1, 4),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", small),
        Paragraph(
            "Filters: "
            + escape(
                f"category={category or 'all'}, date from={date_from.isoformat() if date_from else 'any'}, "
                f"date to={date_to.isoformat() if date_to else 'any'}"
            ),
            small,
        ),
        Paragraph(f"Currency: {escape(project.currency)}. Status: {escape(project.status)}.", small),
        Spacer(1, 8),
        Paragraph("Totals", heading),
    ]
    percent = "N/A" if summary["percentage_variance"] is None else f"{summary['percentage_variance']:.2f}%"
    totals = [
        ["Metric", "Value"],
        ["Total estimated", f"{summary['total_estimated']:.2f}"],
        ["Total actual", f"{summary['total_actual']:.2f}"],
        ["Total variance", f"{summary['total_variance']:.2f}"],
        ["Aggregate percentage variance", percent],
        ["Expenses", str(summary["expense_count"])],
        ["Over budget", str(summary["over_budget_count"])],
        ["Under budget", str(summary["under_budget_count"])],
    ]
    story.append(_table(totals))
    story.append(Paragraph("Expense summary", heading))
    expense_table = [["Expense", "Category", "Date", "Estimated", "Actual", "Variance"]]
    for expense in expenses[:40]:
        from app.services.calculations import variance

        difference = variance(expense.actual_cost, expense.estimated_cost)
        expense_table.append(
            [
                Paragraph(escape(expense.expense_name), small),
                Paragraph(escape(expense.category), small),
                expense.expense_date.isoformat(),
                f"{float(money(expense.estimated_cost)):.2f}",
                f"{float(money(expense.actual_cost)):.2f}",
                f"{float(difference):.2f}",
            ]
        )
    if len(expenses) > 40:
        expense_table.append(["Further rows omitted from the PDF. Use the CSV export for the full filtered list.", "", "", "", "", ""])
    story.append(_table(expense_table, wide=True))

    story.append(Paragraph("Category comparison", heading))
    category_rows = [["Category", "Estimated", "Actual", "Variance"]]
    grouped: dict[str, list[float]] = {}
    for expense in expenses:
        bucket = grouped.setdefault(expense.category, [0.0, 0.0])
        bucket[0] += float(money(expense.estimated_cost))
        bucket[1] += float(money(expense.actual_cost))
    for category_name, amounts in sorted(grouped.items()):
        category_rows.append(
            [
                category_name,
                f"{amounts[0]:.2f}",
                f"{amounts[1]:.2f}",
                f"{amounts[1] - amounts[0]:.2f}",
            ]
        )
    if len(category_rows) == 1:
        category_rows.append(["No expenses in this filter", "", "", ""])
    story.append(_table(category_rows))
    try:
        chart = _category_chart(grouped)
    except Exception:
        chart = None
    if chart is not None:
        story.append(Spacer(1, 6))
        story.append(chart)

    story.append(Paragraph("Key findings", heading))
    story.append(Paragraph(escape(analysis["mode_label"]), small))
    story.append(Paragraph(escape(analysis["summary"]), body))
    for item in analysis["recommendations"][:5]:
        story.append(Paragraph("• " + escape(item), body))
    if analysis["anomalies"]:
        story.append(Paragraph("Statistical flags for review:", body))
        for item in analysis["anomalies"][:8]:
            story.append(Paragraph(f"• {escape(item['expense_name'])} ({escape(item['category'])})", body))
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape(analysis["disclaimer"]), small))
    story.append(Paragraph(escape(DISCLAIMER), small))
    story.append(
        Paragraph(
            "Security and data-quality note: this report includes only the signed-in owner's project. "
            "Imported descriptions are treated as untrusted data and are not sent to an external model by this download. "
            "Findings in this PDF use the rule-based analysis.",
            small,
        )
    )
    document.build(story)
    return buffer.getvalue()


def _table(rows: list[list], wide: bool = False) -> Table:
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7edff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#24324a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8 if wide else 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fbff")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d5def2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _category_chart(grouped: dict[str, list[float]]):
    if not grouped:
        return None
    labels = list(sorted(grouped))[:6]
    estimated = [grouped[label][0] for label in labels]
    actual = [grouped[label][1] for label in labels]
    if max(estimated + actual + [0]) <= 0:
        return None
    drawing = Drawing(170 * mm, 55 * mm)
    chart = VerticalBarChart()
    chart.x = 20
    chart.y = 20
    chart.height = 115
    chart.width = 430
    chart.data = [estimated, actual]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 25
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#8aa4f8")
    chart.bars[1].fillColor = colors.HexColor("#7dcec0")
    chart.barSpacing = 2
    chart.groupSpacing = 8
    drawing.add(chart)
    return drawing
