from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_cover_pdf(
    *,
    output_path: Path,
    subject: str,
    context: str,
    school_name: str,
    teacher_name: str,
    date_label: str | None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setTitle(subject)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 55 * mm, subject)

    pdf.setFont("Helvetica", 13)
    text = pdf.beginText(25 * mm, height - 78 * mm)
    text.setLeading(18)
    for line in _wrap_text(context, 88):
        text.textLine(line)
    pdf.drawText(text)

    card_left = 25 * mm
    card_width = width - 50 * mm
    card_top = height - 115 * mm
    card_height = 52 * mm
    pdf.roundRect(card_left, card_top - card_height, card_width, card_height, 8, stroke=1, fill=0)

    details = [
        ("School", school_name),
        ("Teacher", teacher_name),
        ("Date", date_label or datetime.utcnow().strftime("%B %d, %Y")),
    ]
    y = card_top - 12 * mm
    for label, value in details:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(card_left + 8 * mm, y, f"{label}:")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(card_left + 34 * mm, y, value)
        y -= 12 * mm

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(25 * mm, 38 * mm, "Student Name:")
    pdf.line(58 * mm, 37 * mm, width - 25 * mm, 37 * mm)

    pdf.showPage()
    pdf.save()
    return output_path


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines
