"""Display-free tests for the MCP server's control logic (coords, dispatch, launch).

These pin the bugs that bit the live runs: distorted coordinates (a click that
missed and typed into the wrong app) and unreliable app launching.
"""

from __future__ import annotations

import pytest

import glance.mcp_server as m


@pytest.fixture
def screen_1512x982(monkeypatch):
    """Pretend the active display is a single 1512x982 logical screen (14" MBP)."""
    monkeypatch.setattr(m, "_pg", object())     # mark pyautogui as 'loaded'
    monkeypatch.setattr(m, "_screen", (1512, 982))
    monkeypatch.setattr(m, "_active", m.display.Display(0, 0, 1512, 982))
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
    monkeypatch.setattr(m, "_active", m.display.Display(0, 0, sw, sh))
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


def test_parse_ui_output_maps_and_filters():
    disp = m.display.Display(0, 0, 1512, 982)
    raw = ("AXButton\t7\t100\t200\t50\t50\n"        # kept
           "AXStaticText\t\t0\t0\t10\t10\n"          # dropped: no name
           "AXWindow\twin\t0\t0\t1512\t982\n")       # dropped: whole-window
    els = m._parse_ui_output(raw, disp, 1366)
    assert len(els) == 1
    e = els[0]
    assert e["role"] == "Button" and e["name"] == "7"
    assert (e["sx"], e["sy"]) == (125, 225)                       # GLOBAL center (for clicking)
    assert (e["tx"], e["ty"]) == disp.global_to_target(125, 225, 1366)  # display-relative


def test_parse_ui_output_maps_second_display():
    """An app on a second display maps relative to THAT display, not the primary."""
    disp = m.display.Display(1512, 0, 1920, 1080)                 # to the right of primary
    raw = "AXButton\tOK\t1612\t100\t80\t40\n"                     # global coords on display 2
    els = m._parse_ui_output(raw, disp, 1366)
    assert len(els) == 1
    e = els[0]
    assert (e["sx"], e["sy"]) == (1652, 120)                      # global center kept for click
    assert e["tx"] == round((1652 - 1512) * 1366 / 1920)          # relative to display origin
    assert 0 <= e["tx"] <= 1366


def test_computer_batch_runs_all_actions_in_one_call(monkeypatch):
    import asyncio

    import cv2
    import numpy as np
    png = cv2.imencode(".png", np.zeros((10, 10, 3), np.uint8))[1].tobytes()
    calls = []
    monkeypatch.setattr(m, "_do", lambda a: calls.append(a["action"]))
    monkeypatch.setattr(m, "_grab_png", lambda: png)
    monkeypatch.setattr(m, "_recording_label", None)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)

    acts = [{"action": "click", "x": 1, "y": 2}, {"action": "type", "text": "hi"},
            {"action": "key", "keys": "enter"}]
    # stop_on_stall off: this mock never changes the frame, so we test the run-all path
    res = asyncio.run(m.mcp.call_tool("computer_batch", {"actions": acts, "stop_on_stall": False}))
    content = res[0] if isinstance(res, tuple) else res
    assert calls == ["click", "type", "key"]                      # all ran, one call
    kinds = [type(c).__name__ for c in content]
    assert "TextContent" in kinds and "ImageContent" in kinds     # summary + final screen


def test_computer_batch_stops_on_stall(monkeypatch):
    import asyncio

    import cv2
    import numpy as np
    png = cv2.imencode(".png", np.zeros((10, 10, 3), np.uint8))[1].tobytes()  # frame never changes
    calls = []
    monkeypatch.setattr(m, "_do", lambda a: calls.append(a["action"]))
    monkeypatch.setattr(m, "_grab_png", lambda: png)
    monkeypatch.setattr(m, "_recording_label", None)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)

    acts = [{"action": "click", "x": 1, "y": 2}, {"action": "type", "text": "hi"}]
    res = asyncio.run(m.mcp.call_tool("computer_batch", {"actions": acts}))   # stall on by default
    content = res[0] if isinstance(res, tuple) else res
    text = next(c.text for c in content if type(c).__name__ == "TextContent")
    assert calls == ["click"]                    # stopped after the no-op click
    assert "no visible effect" in text


def test_record_then_replay_roundtrip(monkeypatch, tmp_path):
    """Full procedure-cache path: record a task, then task_begin replays it."""
    import cv2
    import numpy as np
    png = cv2.imencode(".png", np.zeros((10, 10, 3), np.uint8))[1].tobytes()

    monkeypatch.setattr(m, "_do", lambda a: None)            # don't touch a real screen
    monkeypatch.setattr(m, "_grab_png", lambda: png)
    # fingerprints in call order: record-start, record-step, replay-start, replay-verify
    fps = iter([100, 200, 100, 200])
    monkeypatch.setattr(m, "_try_grab_fp", lambda: next(fps))
    monkeypatch.setattr(m, "_cache", m.TaskCache(tmp_path / "t.json"))
    monkeypatch.setattr(m, "_recording_label", None)
    monkeypatch.setattr(m, "_recorded", [])

    assert "ecording" in m.task_begin("demo")                # new task -> records
    m.computer_key("enter")                                  # one recorded step
    assert "saved" in m.task_end()

    res = m.task_begin("demo")                               # start matches -> replays
    text = res[0] if isinstance(res, list) else res
    assert "replayed" in text and "1 actions" in text


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


# --- accessibility-anchored replay (Fix #2) ---------------------------------

_ELS = [
    {"role": "Button", "name": "=", "tx": 100, "ty": 200, "sx": 111, "sy": 222},
    {"role": "Button", "name": "7", "tx": 300, "ty": 400, "sx": 333, "sy": 444},
]


def test_anchor_for_click_picks_nearest_within_radius():
    assert m._anchor_for_click(110, 205, _ELS) == {"role": "Button", "name": "="}


def test_anchor_for_click_none_when_click_hits_empty_space():
    assert m._anchor_for_click(900, 900, _ELS) is None      # beyond ANCHOR_RADIUS


def test_resolve_anchor_exact_match(monkeypatch):
    monkeypatch.setattr(m, "_ui_elements",
                        lambda: [{"role": "Button", "name": "7", "sx": 9, "sy": 8, "tx": 1, "ty": 1}])
    assert m._resolve_anchor({"role": "Button", "name": "7"}) == (9, 8)


def test_resolve_anchor_fuzzy_fallback(monkeypatch):
    # Recorded name '=' now reads '= equals' — exact fails, same-role substring matches.
    monkeypatch.setattr(m, "_ui_elements",
                        lambda: [{"role": "Button", "name": "= equals", "sx": 50, "sy": 60,
                                  "tx": 5, "ty": 6}])
    assert m._resolve_anchor({"role": "Button", "name": "="}) == (50, 60)


def test_resolve_anchor_none_when_gone(monkeypatch):
    monkeypatch.setattr(m, "_ui_elements", lambda: [])
    assert m._resolve_anchor({"role": "Button", "name": "7"}) is None


def test_do_step_anchored_click_uses_live_position(monkeypatch):
    """The point of the fix: an anchored click goes to where the element IS now."""
    clicked = {}
    fake = type("pg", (), {"click": staticmethod(lambda x, y, **k: clicked.update(x=x, y=y))})()
    monkeypatch.setattr(m, "_pyautogui", lambda: fake)
    # Element recorded at coord (100,200) now lives at screen (999,888).
    monkeypatch.setattr(m, "_ui_elements",
                        lambda: [{"role": "Button", "name": "=", "sx": 999, "sy": 888,
                                  "tx": 10, "ty": 20}])
    step = m.Step(action={"action": "click", "x": 100, "y": 200}, fingerprint=0,
                  anchor={"role": "Button", "name": "="})
    assert m._do_step(step) == "anchor"
    assert (clicked["x"], clicked["y"]) == (999, 888)       # live position, not stale coord


def test_do_step_falls_back_to_coord_when_anchor_unresolved(monkeypatch):
    done = []
    monkeypatch.setattr(m, "_ui_elements", lambda: [])       # element gone
    monkeypatch.setattr(m, "_do", lambda a: done.append(a))
    step = m.Step(action={"action": "click", "x": 7, "y": 8}, fingerprint=0,
                  anchor={"role": "Button", "name": "gone"})
    assert m._do_step(step) == "coord"
    assert done == [{"action": "click", "x": 7, "y": 8}]     # recorded coord, via _do


def test_do_step_non_click_ignores_anchor(monkeypatch):
    done = []
    monkeypatch.setattr(m, "_do", lambda a: done.append(a))
    step = m.Step(action={"action": "key", "keys": "enter"}, fingerprint=0)
    assert m._do_step(step) == "coord"
    assert done == [{"action": "key", "keys": "enter"}]


def test_anchor_survives_cache_roundtrip(tmp_path):
    from glance import Step, TaskCache
    steps = [Step(action={"action": "click", "x": 1, "y": 2}, fingerprint=3,
                  anchor={"role": "Button", "name": "="})]
    TaskCache(tmp_path / "t.json").put("calc", 0, steps)
    got = TaskCache(tmp_path / "t.json").get("calc")
    assert got.steps[0].anchor == {"role": "Button", "name": "="}


def test_legacy_step_without_anchor_loads(tmp_path):
    """A .glance_tasks.json written before Fix #2 has no 'anchor' key — must still load."""
    import json
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"calc": {"label": "calc", "start_fingerprint": 0, "steps": [
        {"action": {"action": "click", "x": 1, "y": 2}, "fingerprint": 5}]}}))
    from glance import TaskCache
    got = TaskCache(p).get("calc")
    assert got.steps[0].anchor is None                       # defaulted, no crash


def test_record_click_then_replay_follows_moved_element(monkeypatch, tmp_path, screen_1512x982):
    """End-to-end: record an anchored click, then replay after the element moved."""
    import cv2
    import numpy as np
    png = cv2.imencode(".png", np.zeros((10, 10, 3), np.uint8))[1].tobytes()
    monkeypatch.setattr(m, "_grab_png", lambda: png)
    fps = iter([100, 200, 100, 200])   # rec-start, rec-step, replay-start, replay-verify
    monkeypatch.setattr(m, "_try_grab_fp", lambda: next(fps))
    monkeypatch.setattr(m, "_cache", m.TaskCache(tmp_path / "t.json"))
    monkeypatch.setattr(m, "_recording_label", None)
    monkeypatch.setattr(m, "_recorded", [])
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    clicks = []
    fake = type("pg", (), {"click": staticmethod(lambda x, y, **k: clicks.append((x, y)))})()
    monkeypatch.setattr(m, "_pyautogui", lambda: fake)

    monkeypatch.setattr(m, "_ui_elements",
                        lambda: [{"role": "Button", "name": "=", "tx": 100, "ty": 200,
                                  "sx": 100, "sy": 200}])
    m.task_begin("calc")                 # records, start fp 100
    m.computer_click(100, 200)           # anchored to '='
    m.task_end()

    # Same task, but '=' now lives at screen (900,800).
    monkeypatch.setattr(m, "_ui_elements",
                        lambda: [{"role": "Button", "name": "=", "tx": 10, "ty": 20,
                                  "sx": 900, "sy": 800}])
    m.task_begin("calc")                 # start matches -> replay
    assert clicks[-1] == (900, 800)      # replay clicked the MOVED element
