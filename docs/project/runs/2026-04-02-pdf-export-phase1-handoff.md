# PDF Export Phase 1 Handoff

**Date**: 2026-04-02
**Branch**: `claude/agitated-murdock`
**Status**: merged

## What Changed

- Added an isolated `backend/src/pdf_export/` module that produces print-ready PDFs from completed generations.
- PDF pipeline: cover page → table of contents → Playwright HTML→PDF render → answer key → merge → page numbers → metadata.
- Cover footer and PDF `/Creator` metadata use the **Lectio** brand (not "Kira").
- Added `question_records` (JSONB) and `sections_metadata` (JSONB) columns to the `generations` table via Alembic migration `20260402_0008`.
- New API endpoint: `POST /api/v1/generations/{generation_id}/export/pdf` — returns a `FileResponse` PDF download with page count, file size, and generation time headers.
- PDF generation is auth-gated (`get_current_user`) and validates that the generation status is `"completed"` before proceeding.
- Added `playwright>=1.42.0`, `pypdf>=4.1.0`, `reportlab>=4.1.0` to `pyproject.toml`; Chromium browser installed via `playwright install chromium`.

## Module Layout

```
backend/src/pdf_export/
  __init__.py           # exports PDFExportService, CoverMetadata, ExportOptions, PDFExportResult
  schemas.py            # CoverMetadata, ExportOptions, QuestionRecord, SectionMetadata, PDFExportResult
  config.py             # PDFConfig (pydantic-settings, env prefix PDF_EXPORT_)
  components/
    cover.py            # reportlab canvas cover page
    toc.py              # reportlab platypus table of contents
    answers.py          # reportlab platypus answer key
    assembly.py         # pypdf merge, page numbers, metadata
  rendering/
    playwright.py       # headless Chromium → PDF via ?print=true URL
  service.py            # PDFExportService.export_generation() orchestrator
  routes.py             # FastAPI router registered in app.py
```

## What Was Validated

- `uv run python -c "from pdf_export import PDFExportService, CoverMetadata, ExportOptions, PDFExportResult; print('OK')"` — imports clean.
- `uv run python -c "from playwright.sync_api import sync_playwright; from pypdf import PdfReader; from reportlab.pdfgen import canvas; print('deps OK')"` — all PDF deps import.
- Alembic migration `20260402_0008` applied successfully to the Docker Postgres instance; `question_records` and `sections_metadata` JSONB columns confirmed present on `generations`.

## What Is Left (Phase 2+)

- **Print CSS in Lectio**: The Playwright renderer navigates to `?print=true` and waits for `[data-generation-complete="true"]`. The frontend does not yet respond to `?print=true` or set that sentinel — Phase 2 adds this to SvelteKit.
- **Frontend URL config**: `FRONTEND_URL` in `PDFConfig` defaults to `http://localhost:5173`. Set `PDF_EXPORT_FRONTEND_URL` in `.env` / Docker env for production.
- **`question_records` / `sections_metadata` population**: The pipeline does not yet write these fields. Phase 2 adds pipeline nodes that extract Q&A records and section metadata during generation and persist them to the DB. Until then, TOC and answer key sections are silently skipped (fields are nullable).
- **Telemetry**: PDF generation events not yet logged to the telemetry system.
- **Temp file cleanup on error**: Merged PDF at `/tmp/pdf_export/merged_{id}.pdf` is not cleaned up on download — consider a background cleanup job or streaming directly.

## Where To Start Next Time

1. `backend/src/pdf_export/service.py` — `PDFExportService.export_generation()` is the main orchestrator.
2. `backend/src/pdf_export/rendering/playwright.py` — browser render; tweak `FRONTEND_URL`, timeout, and CSS wait selector here.
3. `backend/src/pdf_export/config.py` — all knobs exposed as `PDF_EXPORT_*` env vars.
4. `backend/src/core/database/migrations/versions/20260402_0008_add_pdf_metadata.py` — migration that added the two new columns.
5. `backend/src/pdf_export/routes.py` — the API endpoint; response headers include page count and generation time.

## Notes

- The DB was stamped at `20260401_0007` before applying `20260402_0008` because the Docker Postgres instance was bootstrapped directly from the ORM (no prior `alembic_version` table).
- Playwright's `wait_for_selector('[data-generation-complete="true"]')` will time out (30s default) until the frontend implements the print sentinel — end-to-end PDF generation will block until Phase 2.
- The `level` field on the cover page is extracted from `planning_spec_json` (keys: `education_level`, `level`, `educationLevel`); falls back to `"General"` if absent.
