"""Jinja2 templates must render the same content in every output format.

tests/jinja_fixtures holds one .md.j2 template that exercises variables,
filters, conditionals, loops over CSV rows, a macro import, comments, a raw
block and a graph block fed through ``tojson``, next to a plain .md file.
Each test runs against HTML, PDF and Word output.
"""

import html
import re
import shutil
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from mddoco.cli import main

TESTS = Path(__file__).parent
FIXTURES = TESTS / "jinja_fixtures"
BROKEN = TESTS / "jinja_broken"

FORMATS = ["html", "pdf", "docx"]


def _require_tools(fmt: str) -> None:
    if fmt in ("pdf", "docx"):
        pytest.importorskip("playwright")
    if fmt == "pdf":
        pytest.importorskip("pypdf")
    if fmt == "docx" and shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _extract_text(fmt: str, path: Path) -> str:
    if fmt == "html":
        body = re.sub(
            r"<(script|style)\b.*?</\1>", " ", path.read_text("utf-8"), flags=re.S
        )
        return _normalise(re.sub(r"<[^>]+>", " ", body))
    if fmt == "pdf":
        from pypdf import PdfReader

        return _normalise(
            " ".join(page.extract_text() for page in PdfReader(path).pages)
        )
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return _normalise(
        " ".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, flags=re.S))
    )


@pytest.fixture(scope="module", params=FORMATS)
def rendered(request, tmp_path_factory):
    fmt = request.param
    _require_tools(fmt)
    out = tmp_path_factory.mktemp(f"jinja-{fmt}")
    result = CliRunner().invoke(main, [str(FIXTURES), "--format", fmt, "-o", str(out)])
    assert result.exit_code == 0, result.output
    path = out / f"{FIXTURES.name}.{fmt}"
    assert path.stat().st_size > 0
    return fmt, path, _extract_text(fmt, path)


def test_variables_filters_and_macros_are_rendered(rendered):
    _, _, text = rendered
    assert "Template Check" in text
    assert "Project: Atlas" in text  # macro imported from _macros.j2
    assert "Shouting: ATLAS" in text  # upper filter
    assert "Owners: Ada Lovelace and Grace Hopper" in text  # join filter


def test_special_characters_survive(rendered):
    _, _, text = rendered
    assert 'Motto: Café & "quoted"' in text


def test_conditionals_pick_the_right_branch(rendered):
    _, _, text = rendered
    assert "STATUS_RELEASED_BRANCH" in text
    assert "STATUS_WRONG_BRANCH" not in text
    assert "ARCHIVED_WRONG_BRANCH" not in text


def test_csv_rows_are_looped_in_order(rendered):
    _, _, text = rendered
    cells = [
        "Zed Zebra Engineer python, go",
        "Amy Ant Lead, Platform rust",
        "Bob Bee Analyst sql, excel, python",
    ]
    positions = [text.find(cell) for cell in cells]
    assert all(pos >= 0 for pos in positions), positions
    assert positions == sorted(positions)
    assert "Headcount: 3" in text


def test_raw_block_is_kept_literally(rendered):
    _, _, text = rendered
    assert "Write {{ literal_variable }} to print a value." in text


def test_no_jinja_syntax_leaks(rendered):
    _, _, text = rendered
    for leaked in ("{% ", "{#", "SENTINEL_TEMPLATE_COMMENT", "m.badge", "project.name"):
        assert leaked not in text


def test_template_and_plain_files_are_combined_in_order(rendered):
    _, _, text = rendered
    assert text.index("Template Check") < text.index("PLAIN_FILE_MARKER")
    assert "_macros" not in text


def test_table_and_chart_exist_in_the_output_format(rendered):
    fmt, path, _ = rendered
    if fmt == "html":
        content = path.read_text("utf-8")
        assert content.count("<table>") == 1
        assert "<svg" in content
    elif fmt == "docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
            media = [n for n in z.namelist() if n.startswith("word/media/")]
        assert xml.count("<w:tbl>") == 1
        assert len(media) == 1
    else:
        from pypdf import PdfReader

        assert len(PdfReader(path).pages) >= 1


@pytest.mark.parametrize("fmt", FORMATS)
def test_template_syntax_error_fails_the_build(fmt, tmp_path):
    _require_tools(fmt)
    result = CliRunner().invoke(
        main, [str(BROKEN), "--format", fmt, "-o", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert not list(tmp_path.iterdir())
