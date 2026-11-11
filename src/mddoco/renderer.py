from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


def load_theme(theme: str) -> Template:
    """Load a theme by built-in name or by path to an HTML template file."""
    theme_path = Path(theme)
    if theme_path.is_file():
        loader_dir = str(theme_path.parent.resolve())
        template_name = theme_path.name
    else:
        loader_dir = str(files("mddoco").joinpath("themes"))
        template_name = f"{theme}.html"

    env = Environment(loader=FileSystemLoader(loader_dir), autoescape=True)
    try:
        return env.get_template(template_name)
    except TemplateNotFound:
        raise ValueError(f"Theme '{theme}' not found.")


def theme_supports_pdf(theme: str) -> bool:
    """Return False when the theme opts out of PDF output.

    A screen-only theme declares ``{% set pdf_supported = false %}`` at the
    top level of its template; themes that say nothing support PDF.
    """
    return getattr(load_theme(theme).module, "pdf_supported", True) is not False


def check_theme_format(theme: str, fmt: str) -> None:
    """Raise ValueError when the theme is missing or cannot produce ``fmt``."""
    if fmt == "pdf" and not theme_supports_pdf(theme):
        raise ValueError(
            f"Theme '{theme}' is screen-only and cannot produce PDF output. "
            "Use --format html, or choose another theme for PDF."
        )


def render_html(
    sections: list[tuple[Path, str]],
    title: str | None = None,
    toc_html: str | None = None,
    theme: str = "default",
    has_mermaid: bool = False,
    has_code: bool = False,
) -> str:
    """Render a full HTML document from (path, html_fragment) pairs."""
    return load_theme(theme).render(
        title=title,
        toc_html=toc_html,
        sections=sections,
        has_mermaid=has_mermaid,
        has_code=has_code,
    )
