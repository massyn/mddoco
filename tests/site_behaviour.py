"""Browser checks for the site-* themes, used by run_tests.sh.

Opens a rendered site in headless Chromium and checks that each H1 became a
nav entry and a page, that exactly one page shows at a time, that every nav
link opens its own page, and that Mermaid diagrams on pages hidden at load
are drawn at full size once shown. Exits non-zero, with a reason, on failure.

    python site_behaviour.py <file.html> <expected-page-count>
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

_STATE_JS = """() => ({
    nav: [...document.querySelectorAll(".site-nav-list > li > a")].map((a) => a.hash),
    visible: [...document.querySelectorAll(".site-page")]
        .filter((p) => p.offsetParent !== null).map((p) => p.id),
    flatDiagrams: [...document.querySelectorAll(".site-page.active .mermaid")]
        .filter((m) => {
            const svg = m.querySelector("svg");
            // A diagram drawn while hidden collapses to an empty ~16px box
            return !svg || svg.getBoundingClientRect().width < 40;
        })
        .length,
})"""


def check(html: Path, expected_pages: int) -> str | None:
    """Return a failure reason, or None when the site behaves."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(html.resolve().as_uri(), wait_until="networkidle")
        try:
            state = page.evaluate(_STATE_JS)
            if len(state["nav"]) != expected_pages:
                return f"nav has {len(state['nav'])} pages, expected {expected_pages}"
            for link in state["nav"]:
                page.evaluate("hash => { location.hash = hash; }", link)
                page.wait_for_function(
                    "slug => document.querySelector('.site-page.active')?.id === slug",
                    arg=link.removeprefix("#/"),
                )
                page.wait_for_function(
                    "() => [...document.querySelectorAll('.site-page.active .mermaid')]"
                    ".every((m) => m.querySelector('svg'))"
                )
                state = page.evaluate(_STATE_JS)
                if state["visible"] != [link.removeprefix("#/")]:
                    return f"{link}: visible pages {state['visible']}"
                if flat := state["flatDiagrams"]:
                    return f"{link}: {flat} Mermaid diagram(s) collapsed"
            if errors:
                return f"JavaScript errors: {errors}"
            return None
        finally:
            browser.close()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    failure = check(Path(sys.argv[1]), int(sys.argv[2]))
    if failure:
        print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
