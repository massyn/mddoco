from pathlib import Path

import pytest

import mddoco
from mddoco.preprocessor import (
    _apply_semicolon_split,
    _parse_csv_line,
    load_context,
    load_csv_context,
)

# --- version ---


def test_version():
    assert mddoco.__version__ == "2.1.0"


# --- _parse_csv_line ---


def test_parse_csv_line_simple():
    assert _parse_csv_line("a,b,c") == [("a", False), ("b", False), ("c", False)]


def test_parse_csv_line_quoted_field():
    assert _parse_csv_line('a,"b;c",d') == [("a", False), ("b;c", True), ("d", False)]


def test_parse_csv_line_quoted_field_with_comma():
    assert _parse_csv_line('a,"b,c",d') == [("a", False), ("b,c", True), ("d", False)]


def test_parse_csv_line_escaped_quote_inside_quoted():
    assert _parse_csv_line('"say ""hello""",b') == [('say "hello"', True), ("b", False)]


def test_parse_csv_line_trailing_comma():
    assert _parse_csv_line("a,b,") == [("a", False), ("b", False), ("", False)]


def test_parse_csv_line_single_field():
    assert _parse_csv_line("hello") == [("hello", False)]


# --- _apply_semicolon_split ---


def test_split_unquoted_with_semicolon():
    assert _apply_semicolon_split("python;flask", False) == ["python", "flask"]


def test_split_trims_whitespace():
    assert _apply_semicolon_split("python ; flask ; sql", False) == [
        "python",
        "flask",
        "sql",
    ]


def test_no_split_when_quoted():
    assert _apply_semicolon_split("python;flask", True) == "python;flask"


def test_no_split_no_semicolon():
    assert _apply_semicolon_split("python", False) == "python"


def test_single_element_after_split():
    assert _apply_semicolon_split("python;", False) == ["python", ""]


# --- load_csv_context ---


def test_load_csv_basic(tmp_path: Path):
    (tmp_path / "people.csv").write_text(
        "name,role\nAlice,Engineer\nBob,Manager\n", encoding="utf-8"
    )
    ctx = load_csv_context(tmp_path)
    assert ctx == {
        "people": [
            {"name": "Alice", "role": "Engineer"},
            {"name": "Bob", "role": "Manager"},
        ]
    }


def test_load_csv_semicolon_becomes_list(tmp_path: Path):
    (tmp_path / "data.csv").write_text(
        "name,skills\nAlice,python;flask\n", encoding="utf-8"
    )
    ctx = load_csv_context(tmp_path)
    assert ctx["data"][0]["skills"] == ["python", "flask"]


def test_load_csv_quoted_semicolon_not_split(tmp_path: Path):
    (tmp_path / "data.csv").write_text('id,label\n1,"a;b;c"\n', encoding="utf-8")
    ctx = load_csv_context(tmp_path)
    assert ctx["data"][0]["label"] == "a;b;c"


def test_load_csv_multiple_files(tmp_path: Path):
    (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("y\n2\n", encoding="utf-8")
    ctx = load_csv_context(tmp_path)
    assert "a" in ctx and "b" in ctx


def test_load_csv_empty_file(tmp_path: Path):
    (tmp_path / "empty.csv").write_text("", encoding="utf-8")
    ctx = load_csv_context(tmp_path)
    assert ctx == {"empty": []}


def test_load_csv_blank_lines_skipped(tmp_path: Path):
    (tmp_path / "data.csv").write_text("name\nAlice\n\nBob\n", encoding="utf-8")
    ctx = load_csv_context(tmp_path)
    assert len(ctx["data"]) == 2


def test_load_csv_from_file_path(tmp_path: Path):
    (tmp_path / "data.csv").write_text("col\nval\n", encoding="utf-8")
    f = tmp_path / "doc.md"
    f.write_text("")
    ctx = load_csv_context(f)
    assert "data" in ctx


# --- load_context ---


def test_load_context_merges_json_and_csv(tmp_path: Path):
    (tmp_path / "config.json").write_text('{"env": "prod"}', encoding="utf-8")
    (tmp_path / "people.csv").write_text("name\nAlice\n", encoding="utf-8")
    ctx = load_context(tmp_path)
    assert "config" in ctx and "people" in ctx


def test_load_context_conflict_raises(tmp_path: Path):
    (tmp_path / "data.json").write_text('{"key": "val"}', encoding="utf-8")
    (tmp_path / "data.csv").write_text("col\nval\n", encoding="utf-8")
    with pytest.raises(ValueError, match="data"):
        load_context(tmp_path)
