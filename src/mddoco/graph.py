import ast
import io
import json
import logging
import re
from html import unescape

import matplotlib

matplotlib.use("Agg")  # non-interactive backend — must be set before importing pyplot
import matplotlib.pyplot as plt

log = logging.getLogger(__name__)

_JSON_TO_PY = re.compile(r"\b(true|false|null)\b")
_JSON_TO_PY_MAP = {"true": "True", "false": "False", "null": "None"}

_DEFAULT_COLOURS = [
    "#2d6cbe",
    "#e74c3c",
    "#27ae60",
    "#e67e22",
    "#8e44ad",
    "#16a085",
    "#2c3e50",
    "#d35400",
]


def graph_it(data, output=None):
    dpi = 100
    width_px = data.get("width_px", 640)
    height_px = data.get("height_px", 480)
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)

    orientation = data.get("orientation", "vertical").lower()
    if orientation not in ("horizontal", "vertical"):
        raise ValueError(
            f"Invalid orientation '{orientation}' — must be 'horizontal' or 'vertical'"
        )
    horizontal = orientation == "horizontal"

    x = data["data"]["x"]

    # Auto-generate series from data keys (everything except 'x') if not provided
    series_list = data.get("series") or [{"label": k} for k in data["data"] if k != "x"]

    for i, series in enumerate(series_list):
        label = series["label"]
        values = data["data"][label]
        series_type = series.get("type", "line")
        colour = series.get("colour", _DEFAULT_COLOURS[i % len(_DEFAULT_COLOURS)])

        if series_type == "bar":
            colour_val = colour if isinstance(colour, list) else [colour] * len(values)
            if horizontal:
                ax.barh(x, values, color=colour_val, label=label)
            else:
                ax.bar(x, values, color=colour_val, label=label)
        elif series_type in ("line", "line2"):
            marker = "o" if series.get("marker", False) else "None"
            linestyle = ":" if series_type == "line2" else "-"
            if horizontal:
                ax.plot(
                    values,
                    x,
                    color=colour,
                    marker=marker,
                    linewidth=2,
                    linestyle=linestyle,
                    label=label,
                )
            else:
                ax.plot(
                    x,
                    values,
                    color=colour,
                    marker=marker,
                    linewidth=2,
                    linestyle=linestyle,
                    label=label,
                )

    if "min" in data or "max" in data:
        lo = data.get("min", None)
        hi = data.get("max", None)
        if horizontal:
            ax.set_xlim(lo, hi)
        else:
            ax.set_ylim(lo, hi)

    title = data.get("title", "")
    if title:
        ax.set_title(title)

    if data.get("show_legend", True):
        ax.legend(loc="upper left")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if output:
        plt.savefig(output, format="svg", bbox_inches="tight")
        plt.close(fig)
    else:
        buf = io.StringIO()
        plt.savefig(buf, format="svg", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()


_GRAPH_BLOCK = re.compile(
    r'<pre><code class="language-graph">(.*?)</code></pre>',
    re.DOTALL,
)

_SVG_HEADER = re.compile(r"^.*?(?=<svg)", re.DOTALL)


def _parse_source(source: str) -> dict:
    """Parse graph source, accepting strict JSON or Python-style literals.

    Handles single quotes, and True/False/None or true/false/null interchangeably.
    """
    text = unescape(source).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        normalised = _JSON_TO_PY.sub(lambda m: _JSON_TO_PY_MAP[m.group()], text)
        return ast.literal_eval(normalised)


def _render_graph(source: str) -> str:
    """Parse source, render via graph_it, and return an inline SVG element."""
    data = _parse_source(source)
    svg = graph_it(data)
    svg = _SVG_HEADER.sub("", svg)  # strip XML declaration and DOCTYPE
    return f'<div class="graph">{svg}</div>'


def process_graph(html: str) -> tuple[str, bool]:
    """Replace fenced graph blocks with rendered SVG charts.

    Raises on any parse or render failure — errors are logged before raising
    so the caller sees the problem on the console.
    Returns (processed_html, found).
    """
    found = bool(_GRAPH_BLOCK.search(html))
    errors: list[Exception] = []

    def replace(m: re.Match) -> str:
        try:
            return _render_graph(m.group(1))
        except Exception as exc:
            log.error("Graph error: %s", exc)
            errors.append(exc)
            return ""

    processed = _GRAPH_BLOCK.sub(replace, html)

    if errors:
        raise errors[0]

    return processed, found
