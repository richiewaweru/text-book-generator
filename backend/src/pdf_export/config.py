from __future__ import annotations

from pydantic_settings import BaseSettings


class PDFConfig(BaseSettings):
    """PDF export configuration."""

    # Fonts
    TITLE_FONT: str = "Helvetica-Bold"
    TITLE_SIZE: int = 32
    HEADING_FONT: str = "Helvetica-Bold"
    HEADING_SIZE: int = 16
    BODY_FONT: str = "Helvetica"
    BODY_SIZE: int = 11

    # Margins (in mm)
    MARGIN_TOP_MM: int = 20
    MARGIN_RIGHT_MM: int = 15
    MARGIN_BOTTOM_MM: int = 20
    MARGIN_LEFT_MM: int = 15

    # Playwright settings
    PLAYWRIGHT_TIMEOUT_MS: int = 30000
    PLAYWRIGHT_WAIT_AFTER_LOAD_MS: int = 500
    FRONTEND_URL: str = "http://localhost:5173"

    # Temp directory for intermediate PDF files
    TEMP_DIR: str = "/tmp/pdf_export"

    class Config:
        env_prefix = "PDF_EXPORT_"


pdf_config = PDFConfig()
