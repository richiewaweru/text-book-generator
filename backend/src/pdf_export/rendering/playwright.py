from __future__ import annotations

import os

from playwright.async_api import async_playwright

from ..config import pdf_config


async def render_html_to_pdf(generation_id: str) -> str:
    """
    Render the textbook HTML view to PDF using a headless Chromium browser.

    Navigates to ``{frontend_url}/textbook/{generation_id}?print=true``,
    waits for the ``[data-generation-complete="true"]`` sentinel, then
    exports the page as a PDF.

    Returns: Path to generated PDF file.
    """
    os.makedirs(pdf_config.TEMP_DIR, exist_ok=True)
    output_path = f"{pdf_config.TEMP_DIR}/content_{generation_id}.pdf"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        url = f"{pdf_config.FRONTEND_URL}/textbook/{generation_id}?print=true"
        await page.goto(
            url,
            wait_until="networkidle",
            timeout=pdf_config.PLAYWRIGHT_TIMEOUT_MS,
        )

        await page.wait_for_selector(
            '[data-generation-complete="true"]',
            timeout=pdf_config.PLAYWRIGHT_TIMEOUT_MS,
        )

        await page.wait_for_timeout(pdf_config.PLAYWRIGHT_WAIT_AFTER_LOAD_MS)

        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={
                "top": f"{pdf_config.MARGIN_TOP_MM}mm",
                "right": f"{pdf_config.MARGIN_RIGHT_MM}mm",
                "bottom": f"{pdf_config.MARGIN_BOTTOM_MM}mm",
                "left": f"{pdf_config.MARGIN_LEFT_MM}mm",
            },
            prefer_css_page_size=True,
        )

        await browser.close()

    return output_path
