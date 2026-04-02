from __future__ import annotations

import os
from io import BytesIO
from typing import List

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def merge_pdfs(pdf_paths: List[str], output_path: str) -> str:
    """
    Merge multiple PDFs into a single document.

    Returns: Path to merged PDF.
    """
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def add_page_numbers(pdf_path: str, skip_first: int = 1) -> str:
    """
    Overlay page numbers onto a PDF, skipping the first N pages (e.g. cover + TOC).

    Returns: Path to the updated PDF (overwrites original).
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_num, page in enumerate(reader.pages):
        if page_num < skip_first:
            writer.add_page(page)
        else:
            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=A4)
            c.setFont("Helvetica", 10)
            actual_page_num = page_num - skip_first + 1
            c.drawCentredString(A4[0] / 2, 15 * mm, f"Page {actual_page_num}")
            c.save()

            packet.seek(0)
            number_pdf = PdfReader(packet)
            page.merge_page(number_pdf.pages[0])
            writer.add_page(page)

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path


def add_metadata(pdf_path: str, metadata: dict) -> str:
    """
    Write PDF metadata (/Title, /Author, /Creator, etc.).

    Returns: Path to the updated PDF (overwrites original).
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(metadata)

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path
