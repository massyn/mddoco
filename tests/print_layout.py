"""Print-layout checks for rendered mddoco output, used by run_tests.sh.

Blank PDF pages come from two faults: space left below the content in print
(it spills onto an extra, empty sheet) and, for Paged.js themes, a PDF that
does not match the pages Paged.js laid out. Each subcommand checks one of
these in headless Chromium and exits non-zero, with a reason, on failure.

    python print_layout.py trailing-space <file.html> [--max-px N]
    python print_layout.py paged-pages <file.html> <file.pdf>
"""

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from mddoco.pdf import _PAGED_RENDERED_HOOK

# Distance from the bottom of the last visible element (including its bottom
# margin) to the end of the document. SVG internals are skipped: their boxes
# do not reflect where the chart sits on the page.
_TRAILING_SPACE_JS = """() => {
    let last = 0;
    for (const el of document.querySelectorAll("body *")) {
        const tag = el.tagName.toLowerCase();
        if (el.closest("svg") && tag !== "svg") continue;
        if (el.children.length && tag !== "svg") continue;
        const box = el.getBoundingClientRect();
        if (!box.height) continue;
        const marginBottom = parseFloat(getComputedStyle(el).marginBottom) || 0;
        last = Math.max(last, box.bottom + window.scrollY + marginBottom);
    }
    return document.documentElement.scrollHeight - last;
}"""


def trailing_space(html: Path, max_px: float) -> str | None:
    """Fail when print layout leaves more than ``max_px`` below the content."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html.resolve().as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        gap = page.evaluate(_TRAILING_SPACE_JS)
        browser.close()
    if gap > max_px:
        return f"{gap:.0f}px of print space below the last content (max {max_px:g}px)"
    return None


def paged_pages(html: Path, pdf: Path) -> str | None:
    """Fail when the PDF page count differs from the Paged.js page count."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.add_init_script(_PAGED_RENDERED_HOOK)
        page.goto(html.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_function("window.__mddocoPagedRendered === true")
        expected = page.evaluate("document.querySelectorAll('.pagedjs_page').length")
        browser.close()
    actual = len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf.read_bytes()))
    if actual != expected:
        return f"PDF has {actual} pages, Paged.js laid out {expected}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="check", required=True)
    trailing = sub.add_parser("trailing-space")
    trailing.add_argument("html", type=Path)
    trailing.add_argument("--max-px", type=float, default=4.0)
    paged = sub.add_parser("paged-pages")
    paged.add_argument("html", type=Path)
    paged.add_argument("pdf", type=Path)
    args = parser.parse_args()

    if args.check == "trailing-space":
        failure = trailing_space(args.html, args.max_px)
    else:
        failure = paged_pages(args.html, args.pdf)
    if failure:
        print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
