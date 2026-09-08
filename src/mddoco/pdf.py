import logging
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_INSTALL_HINT = (
    "Chromium is required for PDF output and could not be installed "
    "automatically. Run: playwright install chromium"
)


def html_to_pdf(html_content: str, dest: Path) -> None:
    """Render an HTML string to a PDF file using a headless Chromium browser.

    Navigates via a temporary file:// URL so that external resources (CDN
    scripts, Mermaid.js, etc.) load correctly before the page is printed.

    The Chromium binary that Playwright drives is not shipped with the Python
    package. The first time a PDF is rendered on a fresh machine it is
    downloaded automatically; if that download fails the user is told how to
    install it by hand.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError
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
        try:
            _render(sync_playwright, tmp_path, dest)
        except PlaywrightError as exc:
            if "Executable doesn't exist" not in str(exc):
                raise
            _install_chromium()
            _render(sync_playwright, tmp_path, dest)
    finally:
        tmp_path.unlink(missing_ok=True)


def _render(sync_playwright, source: Path, dest: Path) -> None:
    """Drive headless Chromium to print ``source`` to ``dest`` as A4 PDF."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(source.as_uri(), wait_until="networkidle")
        # If Paged.js is present, wait for it to finish paginating before
        # capturing — networkidle fires before its JS layout pass completes.
        page.wait_for_function(
            "typeof window.PagedPolyfill === 'undefined'"
            " || !!document.querySelector('.pagedjs_pages')"
        )
        page.pdf(path=str(dest), format="A4", print_background=True)
        browser.close()


def _install_chromium() -> None:
    """Download the Chromium binary Playwright needs, or explain how to."""
    log.warning("Chromium not found — downloading it now (~150 MB, one time).")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise RuntimeError(_INSTALL_HINT) from exc
