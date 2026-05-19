import tempfile
from pathlib import Path


def html_to_pdf(html_content: str, dest: Path) -> None:
    """Render an HTML string to a PDF file using a headless Chromium browser.

    Navigates via a temporary file:// URL so that external resources (CDN
    scripts, Mermaid.js, etc.) load correctly before the page is printed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required for PDF output. "
            "Run: pip install playwright && playwright install chromium"
        )

    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html_content)
        tmp_path = Path(f.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp_path.as_uri(), wait_until="networkidle")
            # If Paged.js is present, wait for it to finish paginating before
            # capturing — networkidle fires before its JS layout pass completes.
            page.wait_for_function(
                "typeof window.PagedPolyfill === 'undefined'"
                " || !!document.querySelector('.pagedjs_pages')"
            )
            page.pdf(path=str(dest), format="A4", print_background=True)
            browser.close()
    finally:
        tmp_path.unlink(missing_ok=True)
