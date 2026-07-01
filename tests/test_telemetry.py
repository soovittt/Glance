"""Tests for session telemetry summarization (cross-tool observability)."""

from __future__ import annotations

from glance.telemetry import emit, load, summarize

RECORDS = [
    {"tool": "computer_screenshot", "modality": "image", "event": "send", "est_tokens": 1441},
    {"tool": "computer_screenshot", "modality": "image", "event": "skip", "est_tokens": 15},
    {"tool": "ui_tree", "modality": "text", "n_elements": 10, "est_tokens": 120},
    {"tool": "computer_batch", "modality": "batch", "n_ran": 4, "round_trips_saved": 3,
     "est_tokens": 1441},
    {"tool": "click_element", "modality": "action", "matched": True, "est_tokens": 8,
     "avoided_screenshot": True},
]


def test_summarize_reports_key_efficiency_metrics():
    out = summarize(RECORDS)
    assert "5 tool calls" in out
    assert "saved by batching      : 3" in out          # batching collapsed round-trips
    assert "1 sent, 1 skipped" in out                   # screenshot breakdown
    assert "screenshot-free actions: 1" in out          # semantic action
    assert "headline efficiency" in out                 # the % vs naive loop


def test_summarize_empty():
    assert "no telemetry" in summarize([])


def test_emit_and_load_roundtrip(tmp_path, monkeypatch):
    fp = tmp_path / "t.jsonl"
    monkeypatch.setenv("GLANCE_TELEMETRY", str(fp))
    emit(tool="ui_tree", modality="text", est_tokens=42)
    rows = load()
    assert len(rows) == 1 and rows[0]["tool"] == "ui_tree" and "ts" in rows[0]
