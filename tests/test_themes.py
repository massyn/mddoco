from pathlib import Path

import pytest
from click.testing import CliRunner

from mddoco.cli import main
from mddoco.renderer import render_html, theme_supports_pdf

SITE_THEMES = ["site", "site-professional", "site-dark", "site-terminal"]


@pytest.mark.parametrize("theme", SITE_THEMES)
def test_site_themes_are_screen_only(theme):
    assert theme_supports_pdf(theme) is False


@pytest.mark.parametrize("theme", ["default", "professional", "paged-professional"])
def test_document_themes_support_pdf(theme):
    assert theme_supports_pdf(theme) is True


def test_external_theme_can_opt_out_of_pdf(tmp_path):
    theme = tmp_path / "mine.html"
    theme.write_text("{% set pdf_supported = false %}<html></html>", encoding="utf-8")
    assert theme_supports_pdf(str(theme)) is False


def test_unknown_theme_raises():
    with pytest.raises(ValueError, match="not found"):
        theme_supports_pdf("no-such-theme")


def test_cli_refuses_pdf_for_screen_only_theme(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, [str(doc), "--theme", "site", "--format", "pdf", "-o", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "screen-only" in result.output
    assert not (tmp_path / "doc.pdf").exists()


@pytest.mark.parametrize("theme", SITE_THEMES)
def test_site_theme_renders_sections_and_title(theme):
    html = render_html(
        [(Path("a.md"), "<h1>Alpha</h1><p>one</p>"), (Path("b.md"), "<h1>Beta</h1>")],
        title="My Site",
        theme=theme,
    )
    assert 'data-site-title="My Site"' in html
    assert "<h1>Alpha</h1>" in html and "<h1>Beta</h1>" in html
    assert 'class="site-nav-list"' in html
