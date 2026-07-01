"""Tests for the self-improvement suite's pure logic (model, verifiers, scoring, loop)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bench.suite import loop, report, runner, verifiers  # noqa: E402
from bench.suite.model import TaskResult  # noqa: E402


def _result(id, ok, difficulty="easy", manual=False, tokens=1000, rt=3, naive=6, mix=None):
    return TaskResult(id=id, difficulty=difficulty, ok=ok, manual=manual, detail="",
                      tokens=tokens, round_trips=rt, naive_round_trips=naive,
                      tool_mix=mix or {})


def test_task_result_roundtrip_and_efficiency():
    r = _result("t", True, tokens=1000, naive=6)
    back = TaskResult.from_dict(r.to_dict())
    assert back == r
    assert back.pct_vs_naive == round(100 * (6 * 1616 - 1000) / (6 * 1616), 1)


def test_desktop_file_verifier(tmp_path):
    (tmp_path / "calc.txt").write_text("the answer is 576")
    assert verifiers.desktop_file("calc.txt", "576", base=tmp_path).ok
    assert not verifiers.desktop_file("calc.txt", "999", base=tmp_path).ok
    assert not verifiers.desktop_file("missing.txt", base=tmp_path).ok


def test_manual_is_flagged():
    r = verifiers.manual("needs a human")
    assert r.manual and not r.ok


def test_score_reports_success_rate_and_excludes_manual():
    results = [_result("a", True), _result("b", False), _result("c", True, manual=True)]
    out = report.score(results)
    assert "1/2" in out            # 2 auto tasks, 1 passed; the manual one excluded
    assert "manual" in out and "failures" in out


def test_compare_detects_regression():
    prev = [_result("a", True), _result("b", True)]
    curr = [_result("a", True), _result("b", False)]   # b regressed
    out = report.compare(prev, curr)
    assert "regressed" in out and "b" in out and "REGRESSION" in out


def test_findings_flags_screenshot_heavy_tasks():
    heavy = _result("h", True, mix={"computer_screenshot": 5})     # no ui_tree
    lean = _result("l", True, mix={"ui_tree": 2, "computer_screenshot": 1})
    out = loop.findings([heavy, lean])
    assert "h:" in out and "5 screenshots" in out
    assert "l:" not in out


def test_telemetry_metrics_aggregation(monkeypatch):
    recs = [
        {"tool": "computer_screenshot", "modality": "image", "event": "send", "est_tokens": 1600},
        {"tool": "computer_screenshot", "modality": "image", "event": "skip", "est_tokens": 1600},
        {"tool": "computer_batch", "modality": "batch", "est_tokens": 1600, "round_trips_saved": 3},
    ]
    monkeypatch.setattr(runner.telemetry, "load", lambda: recs)
    m = runner._telemetry_metrics()
    assert m["round_trips"] == 3
    assert m["naive_round_trips"] == 6                 # 3 calls + 3 saved
    assert m["tokens"] == 1600 + 15 + 1600             # skip counts as the ~15-token note
    assert m["tool_mix"]["computer_screenshot"] == 2
