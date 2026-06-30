"""Display-free tests for the MCP server's control logic (coords, dispatch, launch).

These pin the bugs that bit the live runs: distorted coordinates (a click that
missed and typed into the wrong app) and unreliable app launching.
"""

from __future__ import annotations

import pytest

import glance.mcp_server as m


@pytest.fixture
def screen_1512x982(monkeypatch):
    """Pretend pyautogui is loaded with a 1512x982 logical screen (14" MBP)."""
    monkeypatch.setattr(m, "_pg", object())     # mark pyautogui as 'loaded'
    monkeypatch.setattr(m, "_screen", (1512, 982))
    return 1512, 982


def test_target_preserves_aspect(screen_1512x982):
    sw, sh = screen_1512x982
    tw, th = m._target_hw()
    assert tw == m.TARGET_W
    assert abs(th / tw - sh / sw) < 0.01      # no distortion


def test_coordinate_corners_map_exactly(screen_1512x982):
    sw, sh = screen_1512x982
    tw, th = m._target_hw()
    assert m._to_screen(0, 0) == (0, 0)
    assert m._to_screen(tw, th) == (sw, sh)   # bottom-right maps to the real corner


def test_coordinate_center_is_screen_center(screen_1512x982):
    sw, sh = screen_1512x982
    tw, th = m._target_hw()
    cx, cy = m._to_screen(tw // 2, th // 2)
    assert abs(cx - sw / 2) <= 2 and abs(cy - sh / 2) <= 2


def test_screenshot_failure_returns_message(monkeypatch):
    import asyncio

    def boom():
        raise RuntimeError("no display")
    monkeypatch.setattr(m, "_grab_png", boom)
    res = asyncio.run(m.mcp.call_tool("computer_screenshot", {}))
    content = res[0] if isinstance(res, tuple) else res
    text = content[0].text
    assert "screenshot failed" in text and "no display" in text   # no crash


def test_recording_survives_capture_failure(monkeypatch):
    monkeypatch.setattr(m, "_recording_label", "t")
    monkeypatch.setattr(m, "_recorded", [])
    monkeypatch.setattr(m, "_do", lambda a: None)

    def boom():
        raise RuntimeError("no display")
    monkeypatch.setattr(m, "_grab_png", boom)
    m._act({"action": "key", "keys": "enter"})       # must not raise mid-recording
    assert len(m._recorded) == 1
    assert m._recorded[0].fingerprint == 0           # safe sentinel -> replay diverges here


def test_task_begin_handles_capture_failure(monkeypatch):
    import asyncio

    def boom():
        raise RuntimeError("no display")
    monkeypatch.setattr(m, "_grab_png", boom)
    res = asyncio.run(m.mcp.call_tool("task_begin", {"label": "demo"}))
    content = res[0] if isinstance(res, tuple) else res
    assert "could not capture" in content[0].text     # no crash, clear message


def test_do_open_app_runs_open_dash_a(monkeypatch):
    calls = []
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    m._do({"action": "open_app", "name": "Calculator"})
    assert calls == [["open", "-a", "Calculator"]]


def test_do_click_scales_to_screen(monkeypatch, screen_1512x982):
    clicked = {}
    fake = type("pg", (), {"click": staticmethod(lambda x, y, **k: clicked.update(x=x, y=y))})()
    monkeypatch.setattr(m, "_pyautogui", lambda: fake)
    tw, th = m._target_hw()
    m._do({"action": "click", "x": tw, "y": th})
    assert (clicked["x"], clicked["y"]) == (1512, 982)


# --- harder cases -----------------------------------------------------------

@pytest.mark.parametrize("sw,sh", [(3440, 1440), (2560, 1600), (1920, 1080), (1280, 800)])
def test_coordinate_corners_across_aspect_ratios(monkeypatch, sw, sh):
    monkeypatch.setattr(m, "_pg", object())
    monkeypatch.setattr(m, "_screen", (sw, sh))
    tw, th = m._target_hw()
    assert m._to_screen(0, 0) == (0, 0)
    assert m._to_screen(tw, th) == (sw, sh)            # exact corner on any monitor
    assert abs(th / tw - sh / sw) < 0.01               # never distorted


@pytest.mark.parametrize("combo,expected", [
    ("cmd+space", "key code 49 using {command down}"),
    ("cmd+shift+4", 'keystroke "4" using {command down, shift down}'),
    ("cmd+option+esc", "key code 53 using {command down, option down}"),
    ("enter", "key code 36"),
    ("f5", "key code 96"),                                   # function key, not text
    ("cmd+f3", "key code 99 using {command down}"),
])
def test_mac_key_script(monkeypatch, combo, expected):
    seen = []
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: seen.append(a[0][2]))
    m._mac_key(combo)
    assert seen[0] == f"tell application \"System Events\" to {expected}"


@pytest.mark.parametrize("raw,expected", [
    (2, 2.0), (20, 10.0), (-5, 0.0), (0, 0.0), ("3", 3.0), (None, 1.0), ("x", 1.0),
])
def test_clamp_wait(raw, expected):
    assert m._clamp_wait(raw) == expected


def test_safe_act_returns_error_instead_of_raising(monkeypatch):
    def boom(_):
        raise RuntimeError("boom")
    monkeypatch.setattr(m, "_do", boom)
    out = m._safe_act({"action": "click", "x": 1, "y": 1}, "ok")
    assert "failed" in out and "boom" in out      # no exception escapes the boundary


def test_safe_act_returns_ok_on_success(monkeypatch):
    monkeypatch.setattr(m, "_do", lambda a: None)
    monkeypatch.setattr(m, "_recording_label", None)
    assert m._safe_act({"action": "move", "x": 1, "y": 1}, "moved") == "moved"


def test_do_wait_sleeps_clamped(monkeypatch):
    slept = []
    monkeypatch.setattr(m.time, "sleep", lambda s: slept.append(s))
    m._do({"action": "wait", "seconds": 99})
    assert slept == [10.0]      # clamped to the 10s ceiling


def test_do_drag_scales_both_endpoints(monkeypatch, screen_1512x982):
    moves, drags = [], []
    fake = type("pg", (), {
        "moveTo": staticmethod(lambda x, y: moves.append((x, y))),
        "dragTo": staticmethod(lambda x, y, **k: drags.append((x, y))),
    })()
    monkeypatch.setattr(m, "_pyautogui", lambda: fake)
    tw, th = m._target_hw()
    m._do({"action": "drag", "x1": 0, "y1": 0, "x2": tw, "y2": th})
    assert moves == [(0, 0)] and drags == [(1512, 982)]


def test_frontmost_app_parses_name(monkeypatch):
    monkeypatch.setattr(m.sys, "platform", "darwin")
    monkeypatch.setattr(m.subprocess, "run",
                        lambda *a, **k: type("r", (), {"stdout": "Calculator\n"})())
    assert m._frontmost_app() == "Calculator"


def test_frontmost_app_handles_error(monkeypatch):
    monkeypatch.setattr(m.sys, "platform", "darwin")
    def boom(*a, **k):
        raise OSError("nope")
    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m._frontmost_app().startswith("unknown")


def test_frontmost_app_non_darwin(monkeypatch):
    monkeypatch.setattr(m.sys, "platform", "linux")
    assert "not macOS" in m._frontmost_app()


def test_open_app_action_survives_cache_roundtrip(tmp_path):
    from glance import Step, TaskCache
    steps = [Step(action={"action": "open_app", "name": "Calculator"}, fingerprint=7)]
    TaskCache(tmp_path / "t.json").put("calc", 0, steps)
    got = TaskCache(tmp_path / "t.json").get("calc")
    assert got.steps[0].action == {"action": "open_app", "name": "Calculator"}
