"""
PDF Report Generator Service — generates a professional PDF executive risk report
for analyzed legal documents using ReportLab.
"""
import io
import logging
import uuid
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.analysis_summary import AnalysisSummary

from app.models.clause import Clause
from app.models.document import Document

logger = logging.getLogger(__name__)


def generate_pdf_report(
    document: Document,
    summary: Optional[AnalysisSummary],
    clauses: list[Clause],
) -> bytes:
    """
    Generates a structured PDF report containing document metadata, executive risk summary,
    risk metrics, clause-by-clause breakdown, and legal disclaimers.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
    )
    disclaimer_style = ParagraphStyle(
        "ReportDisclaimer",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica-Oblique",
    )

    story = []

    # 1. Header & Title Block
    story.append(Paragraph("LexAI Legal Simplifier — Executive Risk Report", title_style))
    story.append(Spacer(1, 4))
    now_str = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
    meta_text = (
        f"<b>Document:</b> {document.filename} &nbsp;|&nbsp; "
        f"<b>Type:</b> {document.document_type} &nbsp;|&nbsp; "
        f"<b>Report Date:</b> {now_str}"
    )
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=12))

    # 2. Risk Metrics Summary Cards
    high_cnt = summary.high_count if summary else sum(1 for c in clauses if c.risk_level == "HIGH")
    med_cnt = summary.medium_count if summary else sum(1 for c in clauses if c.risk_level == "MEDIUM")
    low_cnt = summary.low_count if summary else sum(1 for c in clauses if c.risk_level == "LOW")
    total_cnt = summary.total_clauses if summary else len(clauses)

    metric_data = [
        [
            Paragraph("<b>TOTAL CLAUSES</b>", ParagraphStyle("M1", parent=body_style, alignment=1, textColor=colors.HexColor("#475569"))),
            Paragraph("<b>HIGH RISK</b>", ParagraphStyle("M2", parent=body_style, alignment=1, textColor=colors.HexColor("#dc2626"))),
            Paragraph("<b>MEDIUM RISK</b>", ParagraphStyle("M3", parent=body_style, alignment=1, textColor=colors.HexColor("#d97706"))),
            Paragraph("<b>LOW RISK</b>", ParagraphStyle("M4", parent=body_style, alignment=1, textColor=colors.HexColor("#16a34a"))),
        ],
        [
            Paragraph(f"<font size=16><b>{total_cnt}</b></font>", ParagraphStyle("N1", parent=body_style, alignment=1)),
            Paragraph(f"<font size=16 color='#dc2626'><b>{high_cnt}</b></font>", ParagraphStyle("N2", parent=body_style, alignment=1)),
            Paragraph(f"<font size=16 color='#d97706'><b>{med_cnt}</b></font>", ParagraphStyle("N3", parent=body_style, alignment=1)),
            Paragraph(f"<font size=16 color='#16a34a'><b>{low_cnt}</b></font>", ParagraphStyle("N4", parent=body_style, alignment=1)),
        ],
    ]

    metric_table = Table(metric_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    metric_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(metric_table)
    story.append(Spacer(1, 14))

    # 3. Overall Executive Summary
    story.append(Paragraph("Executive Summary", section_heading))
    exec_summary_text = (
        summary.overall_summary
        if (summary and summary.overall_summary)
        else "This legal document was analyzed for contractual risks, ambiguous commitments, and unbalanced liabilities."
    )
    story.append(Paragraph(exec_summary_text, body_style))
    story.append(Spacer(1, 14))

    # 4. Detailed Clause Analysis Breakdown Table
    story.append(Paragraph("Detailed Clause Risk Analysis", section_heading))

    table_headers = [
        Paragraph("<b>Section / Page</b>", ParagraphStyle("TH1", parent=body_style, fontSize=9, textColor=colors.white)),
        Paragraph("<b>Risk Level</b>", ParagraphStyle("TH2", parent=body_style, fontSize=9, textColor=colors.white)),
        Paragraph("<b>Plain Explanation & Risk Reason</b>", ParagraphStyle("TH3", parent=body_style, fontSize=9, textColor=colors.white)),
    ]

    table_rows = [table_headers]

    for clause in clauses:
        sec_label = f"Section {clause.section_number}" if clause.section_number else (clause.section_title or "Provision")
        page_label = f"P. {clause.page_number}" if clause.page_number else "P. 1"
        location_cell = Paragraph(f"<b>{sec_label}</b><br/><font color='#64748b' size=8>{page_label}</font>", body_style)

        risk_upper = clause.risk_level.upper()
        if risk_upper == "HIGH":
            r_color = "#dc2626"
        elif risk_upper == "MEDIUM":
            r_color = "#d97706"
        else:
            r_color = "#16a34a"

        risk_cell = Paragraph(f"<font color='{r_color}'><b>{risk_upper}</b></font>", body_style)

        exp_cell = Paragraph(
            f"<b>Meaning:</b> {clause.explanation}<br/>"
            f"<b>Why Flagged:</b> <font color='#475569'>{clause.reason}</font>",
            body_style,
        )

        table_rows.append([location_cell, risk_cell, exp_cell])

    clause_table = Table(table_rows, colWidths=[1.5 * inch, 1.0 * inch, 4.7 * inch])
    clause_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(clause_table)
    story.append(Spacer(1, 16))

    # 5. Legal Disclaimer Box
    disclaimer_box = [
        [
            Paragraph(
                "<b>LEGAL DISCLAIMER:</b> This report is generated automatically by an AI model for informational and educational purposes only. "
                "It does not constitute formal legal advice, legal representation, or a binding attorney-client relationship. "
                "Always consult a qualified legal attorney before executing legal agreements.",
                disclaimer_style,
            )
        ]
    ]
    disc_table = Table(disclaimer_box, colWidths=[7.2 * inch])
    disc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(KeepTogether(disc_table))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
