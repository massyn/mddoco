from pathlib import Path

import markdown

from mddoco.d2 import process_d2
from mddoco.graph import process_graph
from mddoco.mermaid import process_mermaid
from mddoco.preprocessor import render_j2
from mddoco.toc import TocEntry, flatten_tokens


def read_markdown(path: Path, context: dict | None = None) -> str:
    """Return a file's Markdown text, rendering .md.j2 templates with Jinja2."""
    if path.suffix.lower() == ".j2":
        return render_j2(path, context or {})
    return path.read_text(encoding="utf-8")


def convert_file(
    path: Path,
    toc: bool = False,
    toc_depth: int = 3,
    context: dict | None = None,
) -> tuple[str, list[TocEntry]]:
    """Convert a markdown (or .md.j2) file to an HTML fragment.

    .md.j2 files are rendered with Jinja2 first using the supplied context,
    then the resulting Markdown is converted as normal.
    Returns (html_body, toc_entries). toc_entries is empty when toc=False.
    """
    text = read_markdown(path, context)

    extensions = ["tables", "fenced_code", "attr_list"]
    extension_configs: dict = {}

    if toc:
        extensions.append("toc")
        extension_configs["toc"] = {"toc_depth": toc_depth}

    md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
    html = md.convert(text)
    html, _ = process_mermaid(html)
    html, _ = process_graph(html)
    html, _ = process_d2(html)

    toc_entries = flatten_tokens(md.toc_tokens) if toc else []
    return html, toc_entries


def convert_files(
    paths: list[Path],
    toc: bool = False,
    toc_depth: int = 3,
    context: dict | None = None,
) -> list[tuple[Path, str, list[TocEntry]]]:
    """Convert markdown files, returning (path, html_body, toc_entries) tuples."""
    results = []
    for p in paths:
        html, toc_entries = convert_file(
            p, toc=toc, toc_depth=toc_depth, context=context
        )
        results.append((p, html, toc_entries))
    return results
