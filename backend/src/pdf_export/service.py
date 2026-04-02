from __future__ import annotations

import os
import time
from typing import Optional

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import GenerationModel

from .components import (
    add_metadata,
    add_page_numbers,
    generate_answer_key,
    generate_cover_page,
    generate_toc,
    merge_pdfs,
)
from .config import pdf_config
from .rendering import render_html_to_pdf
from .schemas import (
    CoverMetadata,
    ExportOptions,
    PDFExportResult,
    QuestionRecord,
    SectionMetadata,
)


class PDFExportService:
    """
    Orchestrates the complete PDF export pipeline for a finished generation.

    Pipeline:
    1. Generate cover page
    2. Generate table of contents (if sections_metadata present)
    3. Render content HTML → PDF via Playwright
    4. Generate answer key (if question_records present)
    5. Merge all PDFs
    6. Add page numbers (skip cover + optional TOC)
    7. Add PDF metadata
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_generation(
        self,
        generation_id: str,
        metadata: CoverMetadata,
        options: Optional[ExportOptions] = None,
    ) -> PDFExportResult:
        """
        Generate a complete print-ready PDF for a completed generation.

        Raises:
            ValueError: If the generation does not exist or is not completed.
        """
        start_time = time.time()
        options = options or ExportOptions()

        generation = await self._get_generation(generation_id)

        if generation.status != "completed":
            raise ValueError(
                f"Generation {generation_id} is not completed (status: {generation.status})"
            )

        # Derive a human-readable level from planning_spec_json if available,
        # falling back to a generic label.
        level = self._extract_level(generation.planning_spec_json)

        temp_files: list[str] = []
        os.makedirs(pdf_config.TEMP_DIR, exist_ok=True)

        try:
            # 1. Cover page
            cover_path = generate_cover_page(
                textbook_topic=generation.subject,
                textbook_level=level,
                group_name="",
                school_name=metadata.school_name,
                teacher_name=metadata.teacher_name,
                date=metadata.date,
                textbook_id=generation_id,
            )
            temp_files.append(cover_path)

            # 2. Table of contents
            toc_path: Optional[str] = None
            if options.include_toc and generation.sections_metadata:
                sections = [SectionMetadata(**s) for s in generation.sections_metadata]
                toc_path = generate_toc(sections, generation_id)
                temp_files.append(toc_path)

            # 3. Render content HTML → PDF
            content_path = await render_html_to_pdf(generation_id)
            temp_files.append(content_path)

            # 4. Answer key
            answers_path: Optional[str] = None
            if options.include_answers and generation.question_records:
                questions = [QuestionRecord(**q) for q in generation.question_records]
                answers_path = generate_answer_key(questions, generation_id)
                temp_files.append(answers_path)

            # 5. Merge
            pdf_parts = [cover_path]
            if toc_path:
                pdf_parts.append(toc_path)
            pdf_parts.append(content_path)
            if answers_path:
                pdf_parts.append(answers_path)

            merged_path = f"{pdf_config.TEMP_DIR}/merged_{generation_id}.pdf"
            merge_pdfs(pdf_parts, merged_path)

            # 6. Page numbers (skip cover; also skip TOC page if present)
            skip_pages = 1 + (1 if toc_path else 0)
            add_page_numbers(merged_path, skip_first=skip_pages)

            # 7. PDF metadata
            add_metadata(
                merged_path,
                {
                    "/Title": generation.subject,
                    "/Author": f"{metadata.teacher_name} / Lectio",
                    "/Subject": f"Personalized Textbook - {level}",
                    "/Keywords": generation.subject,
                    "/Creator": "Lectio",
                },
            )

            file_size = os.path.getsize(merged_path)
            page_count = self._count_pages(merged_path)
            generation_time_ms = int((time.time() - start_time) * 1000)

            return PDFExportResult(
                pdf_path=merged_path,
                file_size_bytes=file_size,
                page_count=page_count,
                generation_time_ms=generation_time_ms,
            )

        finally:
            # Remove component temp files; keep the merged output
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass

    async def _get_generation(self, generation_id: str) -> GenerationModel:
        result = await self.db.execute(
            select(GenerationModel).where(GenerationModel.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation is None:
            raise ValueError(f"Generation {generation_id} not found")
        return generation

    @staticmethod
    def _extract_level(planning_spec_json: Optional[str]) -> str:
        """
        Best-effort extraction of education level from the planning spec JSON string.
        Returns a generic fallback when not available.
        """
        if not planning_spec_json:
            return "General"
        try:
            import json
            spec = json.loads(planning_spec_json)
            return (
                spec.get("education_level")
                or spec.get("level")
                or spec.get("educationLevel")
                or "General"
            )
        except Exception:
            return "General"

    @staticmethod
    def _count_pages(pdf_path: str) -> int:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
