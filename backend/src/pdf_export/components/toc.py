from __future__ import annotations

import os
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from ..config import pdf_config
from ..schemas import SectionMetadata


def generate_toc(sections: List[SectionMetadata], textbook_id: str) -> str:
    """
    Generate table of contents from section metadata.

    Returns: Path to temporary PDF file.
    """
    os.makedirs(pdf_config.TEMP_DIR, exist_ok=True)
    output_path = f"{pdf_config.TEMP_DIR}/toc_{textbook_id}.pdf"

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Table of Contents", styles["Heading1"]))
    story.append(Spacer(1, 12 * mm))

    for section in sections:
        entry = Paragraph(f"{section.section_number}. {section.title}", styles["Normal"])
        story.append(entry)
        story.append(Spacer(1, 3 * mm))

        for sub_idx, subsection in enumerate(section.subsections, start=1):
            sub_text = f"&nbsp;&nbsp;&nbsp;&nbsp;{section.section_number}.{sub_idx} {subsection}"
            story.append(Paragraph(sub_text, styles["Normal"]))
            story.append(Spacer(1, 2 * mm))

    story.append(PageBreak())
    doc.build(story)

    return output_path
