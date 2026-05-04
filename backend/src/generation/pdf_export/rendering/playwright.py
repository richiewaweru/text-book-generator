from __future__ import annotations

from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from generation.pdf_export.config import PDFExportConfig


class PDFRenderError(RuntimeError):
    """Raised when the print route cannot be rendered to PDF."""


async def render_generation_pdf(
    *,
    output_path: Path,
    generation_id: str,
    auth_token: str,
    config: PDFExportConfig,
    render_path: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    path_part = render_path if render_path is not None else f"/textbook/{generation_id}"
    render_url = f"{config.render_base_url}{path_part}?print=true&token={auth_token}"

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(
                    render_url,
                    wait_until="networkidle",
                    timeout=config.playwright_timeout_ms,
                )
                await page.wait_for_selector(
                    '[data-generation-complete="true"]',
                    timeout=config.playwright_timeout_ms,
                )
                await page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                await browser.close()
    except PlaywrightTimeoutError as exc:
        raise PDFRenderError(f"Timed out rendering print view at {render_url}") from exc

    return output_path
