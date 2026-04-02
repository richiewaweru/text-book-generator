from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.middleware import get_current_user
from core.dependencies import get_async_session
from core.entities.user import User

from .schemas import CoverMetadata, ExportOptions
from .service import PDFExportService

router = APIRouter(prefix="/api/v1", tags=["pdf"])


@router.post("/generations/{generation_id}/export/pdf")
async def export_generation_pdf(
    generation_id: str,
    metadata: CoverMetadata,
    options: ExportOptions = ExportOptions(),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and download a print-ready PDF for a completed generation.

    The PDF contains:
    - Cover page (school, teacher, date, student name field)
    - Table of contents (if sections_metadata present, default: included)
    - All content sections rendered via Playwright
    - Answer key (if question_records present, default: included)
    - Page numbers (cover page excluded)

    Example request body:
    ```json
    {
        "school_name": "Lincoln High School",
        "teacher_name": "Ms. Johnson",
        "date": "April 2, 2026"
    }
    ```
    """
    try:
        service = PDFExportService(db)
        result = await service.export_generation(generation_id, metadata, options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    safe_topic = (
        result.pdf_path.rsplit("/", 1)[-1]
        .replace("merged_", "")
        .replace(".pdf", "")
    )
    filename = f"textbook_{safe_topic}.pdf"

    return FileResponse(
        result.pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Page-Count": str(result.page_count),
            "X-File-Size": str(result.file_size_bytes),
            "X-Generation-Time-Ms": str(result.generation_time_ms),
        },
    )
