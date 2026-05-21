import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def load_json_context(input_path: Path) -> dict:
    """Load all *.json files from the input directory into a template context dict.

    The stem of each JSON file becomes the variable name in the context.
    E.g. report.json → available as ``report`` inside .md.j2 templates.
    """
    directory = input_path if input_path.is_dir() else input_path.parent
    context: dict = {}
    for json_file in sorted(directory.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {json_file.name}: {exc}") from exc
        context[json_file.stem] = data
    return context


def render_j2(path: Path, context: dict) -> str:
    """Render a .md.j2 Jinja2 template and return the resulting Markdown text."""
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(path.name)
    return template.render(**context)
