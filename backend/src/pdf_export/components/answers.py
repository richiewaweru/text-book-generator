from __future__ import annotations

import os
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from ..config import pdf_config
from ..schemas import QuestionRecord


def generate_answer_key(questions: List[QuestionRecord], textbook_id: str) -> str:
    """
    Generate answer key section.

    Returns: Path to temporary PDF file.
    """
    os.makedirs(pdf_config.TEMP_DIR, exist_ok=True)
    output_path = f"{pdf_config.TEMP_DIR}/answers_{textbook_id}.pdf"

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Answer Key", styles["Heading1"]))
    story.append(Spacer(1, 10 * mm))

    # Group by section
    sections_dict: dict[int, list[QuestionRecord]] = {}
    for record in questions:
        sections_dict.setdefault(record.section_number, []).append(record)

    for section_num in sorted(sections_dict.keys()):
        section_records = sections_dict[section_num]
        section_title = section_records[0].section_title
        story.append(
            Paragraph(
                f"<b>Section {section_num}: {section_title}</b>",
                styles["Heading2"],
            )
        )
        story.append(Spacer(1, 5 * mm))

        for record in section_records:
            story.append(
                Paragraph(
                    f"<b>Q{record.question_number}:</b> {record.answer}",
                    styles["Normal"],
                )
            )
            if record.explanation:
                story.append(
                    Paragraph(
                        f"<i>Explanation:</i> {record.explanation}",
                        styles["Normal"],
                    )
                )
            story.append(Spacer(1, 3 * mm))

        story.append(Spacer(1, 8 * mm))

    doc.build(story)
    return output_path
