from pathlib import Path

from mddoco.converter import convert_file
from mddoco.toc import TocEntry, build_toc


def _toc_for(tmp_path: Path, *documents: str, toc_depth: int = 3) -> str:
    entries = []
    for i, text in enumerate(documents):
        path = tmp_path / f"{i:02d}.md"
        path.write_text(text, encoding="utf-8")
        _, file_entries = convert_file(path, toc=True, toc_depth=toc_depth)
        entries.extend(file_entries)
    return build_toc(entries)


def test_h1_with_subheadings_nests_under_it(tmp_path):
    toc = _toc_for(tmp_path, "# One\n\n## Two\n\n### Three\n")
    assert toc == (
        '<ul>\n<li><a href="#one">One</a><ul>\n'
        '<li><a href="#two">Two</a><ul>\n'
        '<li><a href="#three">Three</a></li>\n</ul></li>\n'
        "</ul></li>\n</ul>"
    )


def test_file_without_h1_nests_its_h2_under_previous_h1(tmp_path):
    toc = _toc_for(tmp_path, "# Intro\n", "## Detail\n")
    assert toc == (
        '<ul>\n<li><a href="#intro">Intro</a><ul>\n'
        '<li><a href="#detail">Detail</a></li>\n'
        "</ul></li>\n</ul>"
    )


def test_leading_h2_is_not_promoted_to_top_level(tmp_path):
    toc = _toc_for(tmp_path, "## Orphan\n\n# Real\n")
    assert toc == (
        '<ul>\n<li><ul>\n<li><a href="#orphan">Orphan</a></li>\n</ul></li>\n'
        '<li><a href="#real">Real</a></li>\n</ul>'
    )


def test_toc_depth_limits_entries(tmp_path):
    toc = _toc_for(tmp_path, "# One\n\n## Two\n\n### Three\n", toc_depth=2)
    assert "#two" in toc
    assert "#three" not in toc


def test_heading_text_is_escaped(tmp_path):
    toc = _toc_for(tmp_path, "# Fish & chips < 5\n")
    assert "Fish &amp; chips &lt; 5" in toc


def test_skipped_level_gets_unlabelled_parent():
    toc = build_toc([TocEntry(1, "a", "A"), TocEntry(3, "c", "C")])
    assert toc == (
        '<ul>\n<li><a href="#a">A</a><ul>\n'
        '<li><ul>\n<li><a href="#c">C</a></li>\n</ul></li>\n'
        "</ul></li>\n</ul>"
    )


def test_no_entries_gives_empty_string():
    assert build_toc([]) == ""
