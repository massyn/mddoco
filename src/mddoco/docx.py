import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from mddoco.converter import read_markdown
from mddoco.d2 import _render_d2
from mddoco.graph import _SVG_HEADER, _parse_source, graph_it
from mddoco.pdf import _install_chromium

log = logging.getLogger(__name__)

_PANDOC_HINT = (
    "Word output requires the 'pandoc' command-line tool, which was not found "
    "on PATH. Install it from https://pandoc.org/installing.html"
)

_PANDOC_TIMEOUT_SECONDS = 120

_MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js"
_MERMAID_SRI = "sha384-EOXBFmc3gx5mb+vn0vPvvGqACToJD24hhacX5Yx+8NUUQrHIle/Qi5Bg9o3zKwW2"
_MERMAID_SCRIPT = (
    f'<script src="{_MERMAID_URL}" integrity="{_MERMAID_SRI}" '
    'crossorigin="anonymous"></script>'
)
_MERMAID_PAGE = f'<body style="margin:0;background:#fff">{_MERMAID_SCRIPT}</body>'
_SVG_PAGE = '<body style="margin:0;background:#fff;display:inline-block">{}</body>'
_MERMAID_RENDER_JS = """async (source) => {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'neutral',
        htmlLabels: false,
        flowchart: { htmlLabels: false },
    });
    const { svg } = await mermaid.render('mddoco-diagram', source);
    document.body.innerHTML = svg;
}"""

DIAGRAM_LANGUAGES = ("graph", "d2", "mermaid")

_FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*([^\s`]*)[^`]*$")

_BORDER = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>'
_TABLE_BORDERS = (
    "<w:tblBorders>"
    + "".join(
        _BORDER.format(side)
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    + "</w:tblBorders>"
)
_TABLE_CELL_MARGINS = (
    '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
    '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar>'
)
_HEADER_CELL_SHADING = (
    '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="E7ECF3"/></w:tcPr>'
)


def replace_diagram_blocks(text: str, replace: Callable[[str, str], str]) -> str:
    """Swap fenced graph, d2 and mermaid blocks for the text ``replace`` returns.

    Only top-level fences are considered, so an example of a diagram block
    shown inside a longer fence (or an indented one) is left alone, as is any
    block that is never closed.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        match = _FENCE_OPEN.match(lines[i])
        if not match:
            out.append(lines[i])
            i += 1
            continue

        indent, fence, language = match.groups()
        closing = re.compile(rf"^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$")
        end = i + 1
        while end < len(lines) and not closing.match(lines[end]):
            end += 1

        closed = end < len(lines)
        if language in DIAGRAM_LANGUAGES and closed and not indent:
            out.append(replace(language, "\n".join(lines[i + 1 : end])))
        else:
            out.extend(lines[i : end + 1])
        i = end + 1

    return "\n".join(out)


def style_tables(document_xml: str) -> str:
    """Give every table grid borders, cell padding and a shaded, bold header row.

    Borders are written onto each table, not into a Word style, because Google
    Docs keeps them reliably when they are applied directly.
    """

    def style_header(match: re.Match) -> str:
        row = match.group(0).replace("<w:tcPr />", _HEADER_CELL_SHADING)
        return re.sub(r"<w:r>(<w:t[ >])", r"<w:r><w:rPr><w:b/></w:rPr>\1", row)

    def style_table(match: re.Match) -> str:
        table = match.group(0)
        # Order inside tblPr: tblW, tblBorders, tblLayout, tblCellMar, tblLook
        table = re.sub(
            r"(<w:tblLayout [^>]*/>|<w:tblLook )",
            lambda m: _TABLE_BORDERS + m.group(1),
            table,
            count=1,
        )
        table = re.sub(
            r"(<w:tblLook )",
            lambda m: _TABLE_CELL_MARGINS + m.group(1),
            table,
            count=1,
        )
        return re.sub(
            r"<w:tr><w:trPr><w:tblHeader[^>]*/></w:trPr>.*?</w:tr>",
            style_header,
            table,
            count=1,
            flags=re.DOTALL,
        )

    return re.sub(r"<w:tbl>.*?</w:tbl>", style_table, document_xml, flags=re.DOTALL)


def _style_docx_tables(source: Path, dest: Path) -> None:
    """Copy a .docx, applying style_tables to its document body."""
    with (
        zipfile.ZipFile(source) as zin,
        zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = style_tables(data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)


def _diagram_svg(language: str, source: str) -> str | None:
    """Return inline SVG for a graph or d2 block; None for Mermaid (browser-drawn)."""
    if language == "graph":
        svg = graph_it(_parse_source(source))
        return _SVG_HEADER.sub("", svg, count=1)
    if language == "d2":
        return _render_d2(source)
    return None


def _screenshot_diagrams(
    sync_playwright, jobs: list[tuple[str, str, str]], dest_dir: Path
) -> None:
    """Render each (file name, language, svg-or-source) job to a PNG."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name, language, content in jobs:
                page = browser.new_page(
                    viewport={"width": 1000, "height": 800}, device_scale_factor=2
                )
                try:
                    if language == "mermaid":
                        page.set_content(_MERMAID_PAGE)
                        if page.evaluate("typeof window.mermaid") != "object":
                            raise RuntimeError(
                                "Mermaid.js could not be loaded; Mermaid diagrams "
                                "need network access"
                            )
                        page.evaluate(_MERMAID_RENDER_JS, content)
                    else:
                        page.set_content(_SVG_PAGE.format(content))
                    page.locator("svg").first.screenshot(path=str(dest_dir / name))
                except RuntimeError:
                    raise
                except Exception as exc:
                    raise RuntimeError(
                        f"Could not render {language} diagram: {exc}"
                    ) from exc
                finally:
                    page.close()
        finally:
            browser.close()


def _render_diagram_images(jobs: list[tuple[str, str, str]], dest_dir: Path) -> None:
    """Turn collected diagram jobs into PNG files in ``dest_dir``."""
    if not jobs:
        return
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required to draw diagrams in Word output. "
            "Run: pip install playwright && playwright install chromium"
        )

    try:
        _screenshot_diagrams(sync_playwright, jobs, dest_dir)
    except PlaywrightError as exc:
        if "Executable doesn't exist" not in str(exc):
            raise RuntimeError(f"Could not render diagrams: {exc}") from exc
        _install_chromium()
        _screenshot_diagrams(sync_playwright, jobs, dest_dir)


def build_markdown(
    paths: list[Path], context: dict | None
) -> tuple[str, list[tuple[str, str, str]]]:
    """Join the files' Markdown, replacing diagram blocks with image links.

    Returns (markdown, jobs). Each job is (png file name, language, svg or
    source) and is drawn to a PNG by the caller.
    """
    jobs: list[tuple[str, str, str]] = []

    def replace(language: str, source: str) -> str:
        name = f"diagram-{len(jobs) + 1}.png"
        try:
            content = _diagram_svg(language, source)
        except Exception as exc:
            log.error("%s error: %s", language.capitalize(), exc)
            raise
        jobs.append((name, language, content if content is not None else source))
        return f"![{language} diagram {len(jobs)}]({name})"

    sections = [
        replace_diagram_blocks(read_markdown(path, context), replace) for path in paths
    ]
    return "\n\n".join(sections), jobs


def build_docx(
    paths: list[Path],
    dest: Path,
    context: dict | None = None,
    title: str | None = None,
) -> None:
    """Write the Markdown files to ``dest`` as a Word document using Pandoc.

    Diagrams (graph, d2, mermaid) are drawn to PNG images first, and every
    table gets borders and a shaded header row.
    """
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError(_PANDOC_HINT)

    with tempfile.TemporaryDirectory(prefix="mddoco-docx-") as tmp:
        work = Path(tmp)
        markdown, jobs = build_markdown(paths, context)
        _render_diagram_images(jobs, work)

        # Relative image links in the Markdown resolve against each source folder.
        search_path = [str(work)] + [str(p.parent.resolve()) for p in paths]
        raw = work / "pandoc-output.docx"
        cmd = [
            pandoc,
            "--from=gfm",
            "--to=docx",
            f"--output={raw}",
            f"--resource-path={os.pathsep.join(dict.fromkeys(search_path))}",
        ]
        if title:
            cmd.append(f"--metadata=title:{title}")

        try:
            result = subprocess.run(
                cmd,
                input=markdown,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=_PANDOC_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"pandoc timed out after {_PANDOC_TIMEOUT_SECONDS}s"
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"pandoc failed: {detail}")
        if result.stderr.strip():
            log.warning("pandoc: %s", result.stderr.strip())

        dest.parent.mkdir(parents=True, exist_ok=True)
        _style_docx_tables(raw, dest)
