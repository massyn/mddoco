from pathlib import Path

import markdown

from mddoco.graph import process_graph
from mddoco.mermaid import process_mermaid
from mddoco.preprocessor import render_j2


def convert_file(
    path: Path,
    toc: bool = False,
    toc_depth: int = 3,
    context: dict | None = None,
) -> tuple[str, str]:
    """Convert a markdown (or .md.j2) file to an HTML fragment.

    .md.j2 files are rendered with Jinja2 first using the supplied context,
    then the resulting Markdown is converted as normal.
    Returns (html_body, toc_html). toc_html is empty when toc=False.
    """
    if path.suffix.lower() == ".j2":
        text = render_j2(path, context or {})
    else:
        text = path.read_text(encoding="utf-8")

    extensions = ["tables", "fenced_code", "attr_list"]
    extension_configs: dict = {}

    if toc:
        extensions.append("toc")
        extension_configs["toc"] = {"toc_depth": toc_depth}

    md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
    html = md.convert(text)
    html, _ = process_mermaid(html)
    html, _ = process_graph(html)

    toc_html: str = md.toc if toc else ""
    return html, toc_html


def convert_files(
    paths: list[Path],
    toc: bool = False,
    toc_depth: int = 3,
    context: dict | None = None,
) -> list[tuple[Path, str, str]]:
    """Convert markdown files, returning (path, html_body, toc_html) tuples."""
    results = []
    for p in paths:
        html, toc_html = convert_file(p, toc=toc, toc_depth=toc_depth, context=context)
        results.append((p, html, toc_html))
    return results
