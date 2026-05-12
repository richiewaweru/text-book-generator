from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from generation.pdf_export.config import PDFExportConfig

logger = logging.getLogger(__name__)


class PDFRenderError(RuntimeError):
    """Raised when the print route cannot be rendered to PDF."""

    def __init__(self, message: str, *, debug: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.debug = debug or {}


def _on_console(msg) -> None:
    text = msg.text
    if len(text) > 1000:
        text = f"{text[:1000]}..."
    logger.warning("PDF print console", extra={"type": msg.type, "text": text})


def _on_request_failed(request) -> None:
    failure = request.failure
    failure_s = str(failure) if failure is not None else None
    logger.warning(
        "PDF print request failed",
        extra={"url": request.url, "method": request.method, "failure": failure_s},
    )


_PRINT_ROOT_SNAPSHOT_JS = """
() => {
  const root = document.querySelector('[data-generation-complete="true"]');
  if (!root) {
    return { found: false };
  }
  return {
    found: true,
    renderer: root.getAttribute('data-renderer'),
    section_count: root.getAttribute('data-section-count'),
    template_id: root.getAttribute('data-template-id'),
    image_count: root.getAttribute('data-image-count'),
    images_loaded: root.getAttribute('data-images-loaded'),
    images_failed: root.getAttribute('data-images-failed'),
    images_timed_out: root.getAttribute('data-images-timed-out'),
    failed_image_sources: root.getAttribute('data-failed-image-sources')
  };
}
"""


async def render_generation_pdf(
    *,
    output_path: Path,
    generation_id: str,
    auth_token: str,
    config: PDFExportConfig,
    render_path: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    path_part = render_path if render_path is not None else f"/textbook/{generation_id}"
    render_url = f"{config.render_base_url}{path_part}?print=true&token={auth_token}"

    print_snapshot: dict[str, Any] = {}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.on("console", _on_console)
            page.on("requestfailed", _on_request_failed)
            try:
                response = await page.goto(
                    render_url,
                    wait_until="domcontentloaded",
                    timeout=config.playwright_timeout_ms,
                )
                logger.info(
                    "PDF print route opened",
                    extra={
                        "render_url": render_url,
                        "status": response.status if response else None,
                        "page_url": page.url,
                        "title": await page.title(),
                    },
                )
                await page.wait_for_selector(
                    '[data-generation-complete="true"]',
                    timeout=config.playwright_timeout_ms,
                )
                logger.info(
                    "PDF print ready selector found",
                    extra={"render_url": render_url, "page_url": page.url},
                )
                try:
                    evaluated = await page.evaluate(_PRINT_ROOT_SNAPSHOT_JS)
                    if isinstance(evaluated, dict):
                        print_snapshot = evaluated
                except Exception:
                    logger.exception("PDF print page evaluate failed")
                await page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
            except PlaywrightTimeoutError as exc:
                debug: dict[str, Any] = {
                    "render_url": render_url,
                    "page_url": page.url,
                    "title": None,
                    "html_sample": None,
                }
                try:
                    html = await page.content()
                    debug["title"] = await page.title()
                    debug["html_sample"] = html[:4000]
                    logger.error(
                        "PDF print timed out (navigation or ready selector)",
                        extra={
                            "render_url": render_url,
                            "page_url": page.url,
                            "title": debug["title"],
                            "html_sample": debug["html_sample"],
                        },
                    )
                except Exception as capture_exc:
                    debug["capture_error"] = str(capture_exc)[:500]
                    logger.exception("Could not capture failed print page HTML")
                raise PDFRenderError(
                    f"Timed out rendering print view at {render_url}",
                    debug=debug,
                ) from exc
        finally:
            await browser.close()

    return output_path, print_snapshot
