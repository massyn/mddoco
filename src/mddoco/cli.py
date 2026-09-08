import logging
from pathlib import Path

import click

from mddoco.converter import convert_files
from mddoco.pdf import html_to_pdf
from mddoco.preprocessor import load_context
from mddoco.renderer import render_html
from mddoco.scanner import find_markdown_files
from mddoco.toc import combine_toc
from mddoco.writer import write_output


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    "output_path",
    default=".",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Output directory, or explicit output file path.",
)
@click.option(
    "--format",
    "-f",
    "fmt",
    default="html",
    show_default=True,
    type=click.Choice(["html", "pdf"], case_sensitive=False),
    help="Output format.",
)
@click.option("--title", "-t", default=None, help="Document title.")
@click.option(
    "--theme",
    default="default",
    show_default=True,
    help="Theme name to use for rendering.",
)
@click.option(
    "--toc/--no-toc",
    default=False,
    show_default=True,
    help="Generate a table of contents.",
)
@click.option(
    "--toc-depth",
    default=3,
    show_default=True,
    type=click.IntRange(1, 6),
    help="Maximum heading depth included in the TOC.",
)
def main(
    input_path: Path,
    output_path: Path,
    fmt: str,
    title: str | None,
    theme: str,
    toc: bool,
    toc_depth: int,
) -> None:
    """Convert markdown files in INPUT_PATH to a single document."""
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    try:
        md_files = find_markdown_files(input_path)
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Found {len(md_files)} markdown file(s).")

    try:
        context = load_context(input_path)
        raw = convert_files(md_files, toc=toc, toc_depth=toc_depth, context=context)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    sections = [(p, html) for p, html, _ in raw]
    toc_html = combine_toc([t for _, _, t in raw]) if toc else None
    has_mermaid = any('<div class="mermaid">' in html for _, html in sections)

    # Resolve output directory and filename.
    # If output_path has a suffix, treat it as an explicit file path.
    # Otherwise treat it as a directory and derive the filename from the input.
    if output_path.suffix:
        out_dir = output_path.parent
        out_filename = output_path.name
    else:
        resolved = input_path.resolve()
        stem = resolved.stem if resolved.is_file() else resolved.name
        out_dir = output_path
        out_filename = f"{stem}.{fmt}"

    try:
        content = render_html(
            sections,
            title=title,
            toc_html=toc_html or None,
            theme=theme,
            has_mermaid=has_mermaid,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if fmt == "html":
        output_file = write_output(content, out_dir, out_filename)
        click.echo(f"Written to {output_file}")

    elif fmt == "pdf":
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / out_filename
        click.echo("Rendering PDF...")
        try:
            html_to_pdf(content, dest)
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Written to {dest}")
