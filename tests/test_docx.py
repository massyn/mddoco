import shutil
import subprocess
import zipfile

import pytest

from mddoco import docx
from mddoco.docx import build_docx, replace_diagram_blocks, style_tables
from mddoco.renderer import check_theme_format


def _tag(language, source):
    return f"[{language}:{source.strip()}]"


def test_top_level_diagram_fences_are_replaced():
    text = "intro\n\n```d2\na -> b\n```\n\n~~~mermaid\ngraph TD\n~~~\n\nend"
    out = replace_diagram_blocks(text, _tag)
    assert out == "intro\n\n[d2:a -> b]\n\n[mermaid:graph TD]\n\nend"


def test_other_languages_are_left_alone():
    text = "```python\nprint(1)\n```"
    assert replace_diagram_blocks(text, _tag) == text


def test_nested_indented_and_unclosed_fences_are_left_alone():
    nested = "````markdown\n```d2\na -> b\n```\n````"
    indented = "  ```d2\n  a -> b\n  ```"
    unclosed = "```d2\na -> b"
    for text in (nested, indented, unclosed):
        assert replace_diagram_blocks(text, _tag) == text


def test_diagram_after_nested_example_is_still_replaced():
    text = "````markdown\n```d2\nx\n```\n````\n\n```d2\na -> b\n```"
    out = replace_diagram_blocks(text, _tag)
    assert out.endswith("[d2:a -> b]")
    assert "```d2\nx\n```" in out


_TABLE_WITH_LAYOUT = (
    '<w:tbl><w:tblPr><w:tblStyle w:val="Table" /><w:tblW w:type="pct" w:w="5000" />'
    '<w:tblLayout w:type="fixed" /><w:tblLook w:firstRow="1" w:val="0020" />'
    '</w:tblPr><w:tblGrid /><w:tr><w:trPr><w:tblHeader w:val="on" /></w:trPr>'
    "<w:tc><w:tcPr /><w:p><w:r><w:t>H</w:t></w:r></w:p></w:tc></w:tr>"
    "<w:tr><w:tc><w:tcPr /><w:p><w:r><w:t>x</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
)
_TABLE_WITHOUT_LAYOUT = _TABLE_WITH_LAYOUT.replace('<w:tblLayout w:type="fixed" />', "")


@pytest.mark.parametrize("table", [_TABLE_WITH_LAYOUT, _TABLE_WITHOUT_LAYOUT])
def test_style_tables_adds_borders_padding_and_header(table):
    out = style_tables(f"<w:body><w:p/>{table}<w:p/></w:body>")
    assert out.count("<w:tblBorders>") == 1
    assert out.count("<w:tblCellMar>") == 1
    assert out.index("<w:tblBorders>") < out.index("<w:tblLook ")
    assert out.index("<w:tblCellMar>") < out.index("<w:tblLook ")
    header, body = out.split("</w:tr>", 1)
    assert "<w:b/>" in header and "w:fill=" in header
    assert "<w:b/>" not in body and "w:fill=" not in body


def test_style_tables_styles_each_table():
    out = style_tables(_TABLE_WITH_LAYOUT + _TABLE_WITHOUT_LAYOUT)
    assert out.count("<w:tblBorders>") == 2


def test_style_tables_without_tables_is_unchanged():
    xml = "<w:body><w:p><w:r><w:t>hi</w:t></w:r></w:p></w:body>"
    assert style_tables(xml) == xml


def test_theme_other_than_default_is_rejected_for_docx():
    with pytest.raises(ValueError, match="Word"):
        check_theme_format("dark", "docx")


def test_default_theme_is_accepted_for_docx():
    check_theme_format("default", "docx")


def test_missing_pandoc_gives_install_hint(tmp_path, monkeypatch):
    md = tmp_path / "a.md"
    md.write_text("# Hi\n")
    monkeypatch.setattr(docx.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="pandoc.*installing"):
        build_docx([md], tmp_path / "out.docx")


def _fake_pandoc(monkeypatch, run):
    monkeypatch.setattr(docx.shutil, "which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(docx.subprocess, "run", run)


def test_pandoc_failure_is_reported(tmp_path, monkeypatch):
    md = tmp_path / "a.md"
    md.write_text("# Hi\n")

    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 3, "", "boom")

    _fake_pandoc(monkeypatch, run)
    with pytest.raises(RuntimeError, match="pandoc failed: boom"):
        build_docx([md], tmp_path / "out.docx")


def test_pandoc_timeout_is_reported(tmp_path, monkeypatch):
    md = tmp_path / "a.md"
    md.write_text("# Hi\n")

    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    _fake_pandoc(monkeypatch, run)
    with pytest.raises(RuntimeError, match="timed out"):
        build_docx([md], tmp_path / "out.docx")


def test_title_and_gfm_are_passed_to_pandoc(tmp_path, monkeypatch):
    md = tmp_path / "a.md"
    md.write_text("# Hi\n")
    calls = []

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        out = next(a for a in cmd if a.startswith("--output=")).split("=", 1)[1]
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("word/document.xml", "<w:body/>")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    _fake_pandoc(monkeypatch, run)
    build_docx([md], tmp_path / "sub" / "out.docx", title="My title")
    cmd, kwargs = calls[0]
    assert "--from=gfm" in cmd
    assert "--metadata=title:My title" in cmd
    assert kwargs["input"].startswith("# Hi")
    assert (tmp_path / "sub" / "out.docx").exists()


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_real_pandoc_output_has_bordered_tables(tmp_path):
    md = tmp_path / "a.md"
    md.write_text(
        "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nx = 1\n```\n"
    )
    dest = tmp_path / "out.docx"
    build_docx([md], dest)
    with zipfile.ZipFile(dest) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert xml.count("<w:tblBorders>") == 1
    assert 'w:val="Heading1"' in xml
