from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

_WRAP_WIDTH = 95


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _wrap_lines(text: str) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.extend(textwrap.wrap(paragraph, width=_WRAP_WIDTH, break_long_words=True) or [""])
        else:
            lines.append("")
    return lines or [""]


def generate_v3_answer_key_pdf(
    *,
    output_path: Path,
    answer_key: dict[str, Any] | None,
) -> Path | None:
    """Render V3 `GeneratedAnswerKeyBlock` entries (from `document_json.answer_key`) to a PDF."""
    if not answer_key or not isinstance(answer_key, dict):
        return None
    entries = answer_key.get("entries")
    if not isinstance(entries, list) or not entries:
        return None

    rows: list[tuple[str, str, str]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        qid = _safe_str(raw.get("question_id")) or "question"
        answer = _safe_str(raw.get("student_answer")) or _safe_str(raw.get("answer"))
        if not answer:
            continue
        working = _safe_str(raw.get("working"))
        notes = _safe_str(raw.get("notes"))
        explanation = _safe_str(raw.get("explanation"))
        extra_parts = [p for p in (working, notes, explanation) if p]
        detail = " — ".join(extra_parts) if extra_parts else ""
        rows.append((qid, answer, detail))

    if not rows:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    y = height - 28 * mm

    pdf.setTitle("Answer Key")
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(20 * mm, y, "Answer Key (V3)")
    y -= 12 * mm

    line_height = 4.2 * mm
    margin_x = 20 * mm

    pdf.setFont("Helvetica-Bold", 10)
    for qid, answer, detail in rows:
        if y < 25 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica-Bold", 10)

        pdf.drawString(margin_x, y, qid)
        y -= line_height
        pdf.setFont("Helvetica", 10)
        for line in _wrap_lines(answer):
            if y < 20 * mm:
                pdf.showPage()
                y = height - 20 * mm
                pdf.setFont("Helvetica", 10)
            pdf.drawString(margin_x + 2 * mm, y, line)
            y -= line_height * 0.85
        if detail:
            pdf.setFont("Helvetica-Oblique", 9)
            for line in _wrap_lines(detail):
                if y < 20 * mm:
                    pdf.showPage()
                    y = height - 20 * mm
                    pdf.setFont("Helvetica-Oblique", 9)
                pdf.drawString(margin_x + 4 * mm, y, line)
                y -= line_height * 0.8
        pdf.setFont("Helvetica-Bold", 10)
        y -= line_height * 0.5

    pdf.save()
    return output_path
