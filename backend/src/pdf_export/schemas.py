from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class CoverMetadata(BaseModel):
    """Metadata for PDF cover page."""
    school_name: str = Field(..., description="School name for cover page")
    teacher_name: str = Field(..., description="Teacher name for cover page")
    date: Optional[str] = Field(None, description="Date for cover page (defaults to today)")


class ExportOptions(BaseModel):
    """PDF export configuration options."""
    page_size: str = Field("A4", description="Page size: A4, Letter")
    include_toc: bool = Field(True, description="Include table of contents")
    include_answers: bool = Field(True, description="Include answer key at end")


class QuestionRecord(BaseModel):
    """Question tracking for answer key."""
    section_number: int
    section_title: str
    question_number: int
    question_text: str
    answer: str
    explanation: Optional[str] = None


class SectionMetadata(BaseModel):
    """Section metadata for TOC."""
    section_number: int
    title: str
    subsections: List[str] = Field(default_factory=list)


class PDFExportResult(BaseModel):
    """Result of PDF export operation."""
    pdf_path: str
    file_size_bytes: int
    page_count: int
    generation_time_ms: int
