from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


def render_html(
    sections: list[tuple[Path, str]],
    title: str | None = None,
    toc_html: str | None = None,
    theme: str = "default",
    has_mermaid: bool = False,
) -> str:
    """Render a full HTML document from (path, html_fragment) pairs."""
    theme_path = Path(theme)
    if theme_path.is_file():
        loader_dir = str(theme_path.parent.resolve())
        template_name = theme_path.name
    else:
        loader_dir = str(files("mddoco").joinpath("themes"))
        template_name = f"{theme}.html"

    env = Environment(loader=FileSystemLoader(loader_dir), autoescape=True)
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise ValueError(f"Theme '{theme}' not found.")
    return template.render(
        title=title,
        toc_html=toc_html,
        sections=sections,
        has_mermaid=has_mermaid,
    )
