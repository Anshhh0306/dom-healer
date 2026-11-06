from __future__ import annotations

import io
import json
import runpy
import sys

import pytest

from dom_healer import __version__, cli


@pytest.fixture
def pages(tmp_path, old_html, new_html):
    old = tmp_path / "old.html"
    new = tmp_path / "new.html"
    old.write_text(old_html, encoding="utf-8")
    new.write_text(new_html, encoding="utf-8")
    return old, new


def _run(argv, stdin: bytes | None = None, monkeypatch=None):
    out, err = io.StringIO(), io.StringIO()
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = cli.run(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_repair_text_output(pages):
    old, new = pages
    code, out, err = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector", "#nl-email",
                           "--ranker", "heuristic"])
    assert code == 0, err
    assert "status:     healed" in out
    assert 'css:        [name="email"]' in out
    assert "candidates:" in out and "timings:" in out
    code, out, _ = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector",
                         "button[data-testid='add-SK-200']"])
    assert code == 0 and "inside shadow DOM" in out


def test_repair_json_output(pages):
    old, new = pages
    code, out, _ = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector",
                         "button[data-testid='add-SK-200']", "--json", "--top-k", "2"])
    data = json.loads(out)
    assert code == 0 and data["ok"] is True
    assert data["selector"] == '[data-sku="SK-200"] button'
    assert len(data["candidates"]) == 2


def test_repair_low_confidence_exit_code(pages):
    old, new = pages
    code, out, _ = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector", "#nl-email",
                         "--min-confidence", "0.999", "--ranker", "heuristic", "--max-candidates", "5"])
    assert code == 1 and "low_confidence" in out


def test_input_errors(pages, tmp_path):
    old, new = pages
    code, _, err = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector", "#missing"])
    assert code == 2 and "matched no element" in err
    code, _, err = _run(["repair", "--old-html", str(tmp_path / "nope.html"), "--new-html", str(new),
                         "--selector", "#x"])
    assert code == 2 and "error" in err
    code, _, err = _run(["repair", "--old-html", str(old), "--new-html", str(new), "--selector", "div["])
    assert code == 2 and "invalid CSS selector" in err
    code, _, err = _run(["locate", "--fingerprint", str(old), "--html", str(new)])
    assert code == 2


def test_fingerprint_and_locate(pages, tmp_path, monkeypatch):
    old, new = pages
    code, out, _ = _run(["fingerprint", "--html", str(old), "--selector", "#weekly"])
    assert code == 0 and json.loads(out)["tag"] == "input"
    fp_path = tmp_path / "fp.json"
    code, out, _ = _run(["fingerprint", "--html", str(old), "--selector", "#weekly", "-o", str(fp_path)])
    assert code == 0 and out == "" and json.loads(fp_path.read_text())["attrs"]["name"] == "weekly"
    code, out, _ = _run(["locate", "--fingerprint", str(fp_path), "--html", str(new), "--json"])
    assert code == 0 and json.loads(out)["selector"] == '[name="weekly"]'
    code, out, _ = _run(["locate", "--fingerprint", "-", "--html", str(new), "--ranker", "heuristic"],
                        stdin=fp_path.read_bytes(), monkeypatch=monkeypatch)
    assert code == 0 and "healed" in out


def test_mcp_command(monkeypatch):
    calls = []
    import dom_healer.mcp_server as server

    monkeypatch.setattr(server, "main", lambda: calls.append(True))
    assert _run(["mcp"])[0] == 0 and calls == [True]

    def boom():
        raise ImportError("mcp missing")

    monkeypatch.setattr(server, "main", boom)
    code, _, err = _run(["mcp"])
    assert code == 2 and "mcp missing" in err


def test_version_and_usage(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.run(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.run([])


def test_python_dash_m(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dom-healer", "--version"])
    with pytest.raises(SystemExit):
        runpy.run_module("dom_healer", run_name="__main__")
    assert __version__ in capsys.readouterr().out
