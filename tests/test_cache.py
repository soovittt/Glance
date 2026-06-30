"""Tests for the task-keyed procedure cache (record once, replay on exact repeat)."""

from __future__ import annotations

from glance import Step, TaskCache


STEPS = [
    Step(action={"action": "key", "keys": "cmd+space"}, fingerprint=111),
    Step(action={"action": "type", "text": "Calculator"}, fingerprint=222),
    Step(action={"action": "key", "keys": "enter"}, fingerprint=333),
]


def test_record_get_and_normalize(tmp_path):
    c = TaskCache(tmp_path / "t.json")
    c.put("Compute 7x8", start_fingerprint=10, steps=STEPS)
    got = c.get("compute   7x8")          # case/whitespace-normalized
    assert got is not None
    assert got.start_fingerprint == 10
    assert [s.action["action"] for s in got.steps] == ["key", "type", "key"]


def test_unknown_task_is_none(tmp_path):
    assert TaskCache(tmp_path / "t.json").get("never seen") is None


def test_persists_across_instances(tmp_path):
    path = tmp_path / "t.json"
    TaskCache(path).put("t", start_fingerprint=5, steps=STEPS)
    reloaded = TaskCache(path).get("t")
    assert reloaded is not None
    assert len(reloaded.steps) == 3
    assert reloaded.steps[1].action["text"] == "Calculator"


def test_corrupt_cache_file_does_not_crash(tmp_path):
    path = tmp_path / "t.json"
    path.write_text("{ this is not valid json ]")
    cache = TaskCache(path)          # must not raise
    assert len(cache) == 0


def test_malformed_entry_is_skipped(tmp_path):
    # outer key matches the normalized label, as save() writes it
    path = tmp_path / "t.json"
    path.write_text('{"good": {"label": "good", "start_fingerprint": 1, "steps": []}, '
                    '"bad": {"label": "bad"}}')
    cache = TaskCache(path)
    assert cache.get("good") is not None     # valid entry loads
    assert cache.get("bad") is None          # malformed entry (no start_fingerprint) skipped
    assert len(cache) == 1


def test_forget(tmp_path):
    c = TaskCache(tmp_path / "t.json")
    c.put("t", 0, STEPS)
    assert c.forget("T") is True          # normalized match
    assert c.get("t") is None
    assert c.forget("t") is False
