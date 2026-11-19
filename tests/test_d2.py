import shutil
import subprocess

import pytest

from mddoco import d2
from mddoco.d2 import process_d2


def _block(source: str) -> str:
    return f'<pre><code class="language-d2">{source}</code></pre>'


def _fake_run(stdout="", stderr="", returncode=0, calls=None):
    def run(cmd, **kwargs):
        if calls is not None:
            calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    return run


@pytest.fixture
def fake_d2(monkeypatch):
    monkeypatch.setattr(d2.shutil, "which", lambda name: "/usr/bin/d2")


def test_no_d2_blocks_leaves_html_untouched_and_needs_no_binary(monkeypatch):
    monkeypatch.setattr(d2.shutil, "which", lambda name: None)
    html = "<p>hello</p><pre><code>plain</code></pre>"
    assert process_d2(html) == (html, False)


def test_block_replaced_with_inline_svg(fake_d2, monkeypatch):
    svg = '<?xml version="1.0"?><svg viewBox="0 0 1 1"></svg>'
    monkeypatch.setattr(d2.subprocess, "run", _fake_run(stdout=svg))
    html, found = process_d2(f"<p>a</p>{_block('x -> y')}<p>b</p>")
    assert found
    assert html == (
        '<p>a</p><div class="d2">'
        '<svg viewBox="0 0 1 1" width="1" height="1"></svg></div><p>b</p>'
    )


def test_outer_svg_gets_its_natural_size(fake_d2, monkeypatch):
    svg = '<svg xmlns="x" viewBox="0 0 255.4 455"><svg width="1"></svg></svg>'
    monkeypatch.setattr(d2.subprocess, "run", _fake_run(stdout=svg))
    html, _ = process_d2(_block("x"))
    assert '<svg xmlns="x" viewBox="0 0 255.4 455" width="255" height="455">' in html


def test_source_is_unescaped_and_sent_on_stdin(fake_d2, monkeypatch):
    calls = []
    monkeypatch.setattr(
        d2.subprocess, "run", _fake_run(stdout="<svg></svg>", calls=calls)
    )
    process_d2(_block("x -&gt; y: &quot;hi&quot; &amp; bye"))
    cmd, kwargs = calls[0]
    assert cmd == ["/usr/bin/d2", "-", "-"]
    assert kwargs["input"] == 'x -> y: "hi" & bye'


def test_multiple_blocks_each_rendered(fake_d2, monkeypatch):
    calls = []
    monkeypatch.setattr(
        d2.subprocess, "run", _fake_run(stdout="<svg></svg>", calls=calls)
    )
    html, _ = process_d2(_block("a -> b") + _block("c -> d"))
    assert html.count('<div class="d2">') == 2
    assert len(calls) == 2


def test_compile_failure_raises_with_d2_message(fake_d2, monkeypatch):
    monkeypatch.setattr(
        d2.subprocess,
        "run",
        _fake_run(stderr="err: maps must be terminated", returncode=1),
    )
    with pytest.raises(RuntimeError, match="maps must be terminated"):
        process_d2(_block("a -> {"))


def test_timeout_raises(fake_d2, monkeypatch):
    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(d2.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="timed out"):
        process_d2(_block("a -> b"))


def test_missing_binary_gives_install_hint(monkeypatch):
    monkeypatch.setattr(d2.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="d2lang.com/tour/install"):
        process_d2(_block("a -> b"))


@pytest.mark.skipif(shutil.which("d2") is None, reason="d2 CLI not installed")
def test_real_d2_renders_svg():
    html, found = process_d2(_block("a -&gt; b: hello"))
    assert found
    assert html.startswith('<div class="d2"><svg')
    assert "<?xml" not in html


@pytest.mark.skipif(shutil.which("d2") is None, reason="d2 CLI not installed")
def test_real_d2_rejects_invalid_source():
    with pytest.raises(RuntimeError, match="d2 failed"):
        process_d2(_block("a -&gt; {"))
