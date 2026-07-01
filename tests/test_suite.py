"""Tests for the self-improvement suite's pure logic (model, verifiers, scoring, loop)."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bench.suite import analyze, loop, report, runner, verifiers  # noqa: E402
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


def test_analyze_shows_failures_with_trajectory(tmp_path):
    d = tmp_path / "run1"
    d.mkdir()
    (d / "_meta.json").write_text(json.dumps({"tasks": 2, "passed": 1}))
    (d / "t1.json").write_text(json.dumps({
        "id": "t1", "difficulty": "easy", "prompt": "p",
        "result": {"id": "t1", "ok": False, "error": "timeout", "detail": "missing",
                   "duration_s": 9.0, "round_trips": 3, "tokens": 100},
        "telemetry": [{"tool": "computer_screenshot"}], "stdout_tail": "got stuck on dialog"}))
    (d / "t2.json").write_text(json.dumps({
        "id": "t2", "difficulty": "easy", "prompt": "p",
        "result": {"id": "t2", "ok": True, "error": "", "detail": "ok",
                   "duration_s": 5.0, "round_trips": 2, "tokens": 50},
        "telemetry": [], "stdout_tail": "done"}))
    out = analyze.analyze(d, failures_only=True)
    assert "t1" in out and "timeout" in out and "got stuck on dialog" in out
    assert "t2" not in out                              # passing task hidden by default
    assert "t2" in analyze.analyze(d, failures_only=False)


def test_simulate_result_is_deterministic_and_shaped():
    t = runner.TASKS[0]
    a, b = runner.simulate_result(t, 0), runner.simulate_result(t, 0)
    assert a == b                                          # deterministic per task id
    assert a.id == t.id and not a.manual
    assert a.round_trips > 0 and a.naive_round_trips >= a.round_trips
    assert a.tokens > 0 and a.duration_s > 0


def test_metrics_aggregation():
    recs = [
        {"tool": "computer_screenshot", "modality": "image", "event": "send", "est_tokens": 1600},
        {"tool": "computer_screenshot", "modality": "image", "event": "skip", "est_tokens": 1600},
        {"tool": "computer_batch", "modality": "batch", "est_tokens": 1600, "round_trips_saved": 3},
        {"tool": "computer_click", "modality": "action"},        # now counted as a round-trip
    ]
    m = runner._metrics(recs)
    assert m["round_trips"] == 4
    assert m["naive_round_trips"] == 7                 # 4 calls + 3 saved
    assert m["tokens"] == 1600 + 15 + 1600             # skip counts as the ~15-token note
    assert m["tool_mix"]["computer_screenshot"] == 2
