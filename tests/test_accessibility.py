"""Tests for accessibility parsing + click anchoring (pure logic)."""

from __future__ import annotations

from glance import accessibility as a
from glance.display import Display


def test_parse_ui_output_maps_and_filters():
    disp = Display(0, 0, 1512, 982)
    raw = ("AXButton\t7\t100\t200\t50\t50\n"        # kept
           "AXStaticText\t\t0\t0\t10\t10\n"          # dropped: no name
           "AXWindow\twin\t0\t0\t1512\t982\n")       # dropped: whole-window
    els = a.parse_ui_output(raw, disp, 1366)
    assert len(els) == 1
    e = els[0]
    assert e["role"] == "Button" and e["name"] == "7"
    assert (e["sx"], e["sy"]) == (125, 225)                       # GLOBAL center (for clicking)
    assert (e["tx"], e["ty"]) == disp.global_to_target(125, 225, 1366)


def test_parse_ui_output_maps_second_display():
    """An app on a second display maps relative to THAT display, not the primary."""
    disp = Display(1512, 0, 1920, 1080)
    raw = "AXButton\tOK\t1612\t100\t80\t40\n"                     # global coords on display 2
    els = a.parse_ui_output(raw, disp, 1366)
    assert len(els) == 1
    e = els[0]
    assert (e["sx"], e["sy"]) == (1652, 120)                      # global center kept for click
    assert e["tx"] == round((1652 - 1512) * 1366 / 1920)          # relative to display origin
    assert 0 <= e["tx"] <= 1366


def test_anchor_for_click_matches_nearest_within_radius():
    els = [{"role": "Button", "name": "=", "tx": 100, "ty": 100, "sx": 0, "sy": 0},
           {"role": "Button", "name": "7", "tx": 300, "ty": 300, "sx": 0, "sy": 0}]
    assert a.anchor_for_click(els, 105, 98) == {"role": "Button", "name": "="}
    assert a.anchor_for_click(els, 900, 900) is None             # far from any element
    assert a.anchor_for_click([], 1, 1) is None


def test_resolve_anchor_exact_then_fuzzy():
    els = [{"role": "Button", "name": "Total: $4.82", "sx": 500, "sy": 600, "tx": 0, "ty": 0}]
    assert a.resolve_anchor(els, {"role": "Button", "name": "Total: $4.82"}) == (500, 600)
    assert a.resolve_anchor(els, {"role": "Button", "name": "Total"}) == (500, 600)  # substring
    assert a.resolve_anchor(els, {"role": "Button", "name": "Nope"}) is None
