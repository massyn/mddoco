import csv
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def load_json_context(input_path: Path) -> dict:
    """Load all *.json files from the input directory into a template context dict."""
    directory = input_path if input_path.is_dir() else input_path.parent
    context: dict = {}
    for json_file in sorted(directory.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {json_file.name}: {exc}") from exc
        context[json_file.stem] = data
    return context


def _parse_csv_line(line: str) -> list[tuple[str, bool]]:
    """Parse a single CSV line into (value, was_quoted) pairs.

    Handles quoted fields (including commas and escaped quotes inside them).
    """
    fields: list[tuple[str, bool]] = []
    i = 0
    n = len(line)

    while True:
        if i >= n:
            break

        if line[i] == '"':
            i += 1
            parts: list[str] = []
            while i < n:
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        parts.append('"')
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    parts.append(line[i])
                    i += 1
            value = ''.join(parts)
            while i < n and line[i] != ',':
                i += 1
            fields.append((value, True))
        else:
            start = i
            while i < n and line[i] != ',':
                i += 1
            fields.append((line[start:i], False))

        if i < n and line[i] == ',':
            i += 1
            if i >= n:
                fields.append(('', False))

    return fields


def _apply_semicolon_split(value: str, was_quoted: bool) -> str | list[str]:
    """Return value split on ';' unless the field was originally quoted."""
    if was_quoted or ';' not in value:
        return value
    return [part.strip() for part in value.split(';')]


def load_csv_context(input_path: Path) -> dict:
    """Load all *.csv files from the input directory into a template context dict.

    Each file's stem becomes the variable name (people.csv → ``people``).
    The value is a list of row dicts. Cell values containing ';' become lists;
    quoted fields are never split.
    """
    directory = input_path if input_path.is_dir() else input_path.parent
    context: dict = {}

    for csv_file in sorted(directory.glob("*.csv")):
        lines = csv_file.read_text(encoding="utf-8").splitlines()
        rows: list[dict] = []

        if not lines:
            context[csv_file.stem] = rows
            continue

        header = next(csv.reader([lines[0]]))

        for raw_line in lines[1:]:
            if not raw_line.strip():
                continue
            fields = _parse_csv_line(raw_line)
            row: dict = {}
            for idx, key in enumerate(header):
                if idx < len(fields):
                    value, was_quoted = fields[idx]
                else:
                    value, was_quoted = '', False
                row[key] = _apply_semicolon_split(value, was_quoted)
            rows.append(row)

        context[csv_file.stem] = rows

    return context


def load_context(input_path: Path) -> dict:
    """Load JSON and CSV context files, raising ValueError on stem conflicts."""
    json_ctx = load_json_context(input_path)
    csv_ctx = load_csv_context(input_path)
    conflicts = set(json_ctx) & set(csv_ctx)
    if conflicts:
        names = ', '.join(sorted(conflicts))
        raise ValueError(
            f"Context name conflict — both a .json and .csv exist for: {names}"
        )
    return {**json_ctx, **csv_ctx}


def render_j2(path: Path, context: dict) -> str:
    """Render a .md.j2 Jinja2 template and return the resulting Markdown text."""
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(path.name)
    return template.render(**context)
