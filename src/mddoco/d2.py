import logging
import re
import shutil
import subprocess
from html import unescape

log = logging.getLogger(__name__)

_D2_BLOCK = re.compile(
    r'<pre><code class="language-d2">(.*?)</code></pre>',
    re.DOTALL,
)

_OUTER_SVG = re.compile(r'(?P<tag><svg\b[^>]*)\sviewBox="(?P<dims>[^"]+)"')

_INSTALL_HINT = (
    "D2 diagrams require the 'd2' command-line tool, which was not found on "
    "PATH. Install it from https://d2lang.com/tour/install"
)

_TIMEOUT_SECONDS = 30


def _render_d2(source: str) -> str:
    """Compile D2 source with the d2 CLI and return an inline SVG element."""
    d2 = shutil.which("d2")
    if d2 is None:
        raise RuntimeError(_INSTALL_HINT)

    try:
        result = subprocess.run(
            [d2, "-", "-"],
            input=unescape(source),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"d2 timed out after {_TIMEOUT_SECONDS}s") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"d2 failed: {detail}")

    start = result.stdout.find("<svg")  # skip the XML declaration
    svg = result.stdout[max(start, 0) :]
    svg = _OUTER_SVG.sub(_with_natural_size, svg, count=1)
    return f'<div class="d2">{svg}</div>'


def _with_natural_size(m: re.Match) -> str:
    """Give the outer <svg> its viewBox size so it is not stretched to fit."""
    dims = m.group("dims")
    width, height = (round(float(v)) for v in dims.split()[2:])
    return f'{m.group("tag")} viewBox="{dims}" width="{width}" height="{height}"'


def process_d2(html: str) -> tuple[str, bool]:
    """Replace fenced d2 blocks with SVG diagrams rendered by the d2 CLI.

    Raises on any render failure — errors are logged before raising so the
    caller sees the problem on the console.
    Returns (processed_html, found).
    """
    found = bool(_D2_BLOCK.search(html))
    errors: list[Exception] = []

    def replace(m: re.Match) -> str:
        try:
            return _render_d2(m.group(1))
        except Exception as exc:
            errors.append(exc)
            return ""

    processed = _D2_BLOCK.sub(replace, html)

    for exc in errors:
        log.error("D2 error: %s", exc)
    if errors:
        raise errors[0]

    return processed, found
