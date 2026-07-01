"""macOS accessibility.

Reads the frontmost app's UI as structured elements (role, name, coordinates) — far
cheaper than a screenshot and precise for clicking — and anchors clicks to elements by
identity so a recorded task can re-find its targets even if the window moved or a label
reflowed. `parse_ui_output` is pure and unit-tested; `elements` runs osascript and
never raises.
"""

from __future__ import annotations

import subprocess
import sys

from . import display

ANCHOR_RADIUS = 40   # px in screenshot space: a click within this of an element's center anchors to it

UI_SCRIPT = r'''
set output to ""
tell application "System Events"
  set frontApp to first application process whose frontmost is true
  tell frontApp
    try
      set els to entire contents of front window
    on error
      set els to {}
    end try
    repeat with e in els
      try
        set p to position of e
        set s to size of e
        set output to output & (role of e) & tab & (name of e) & tab
        set output to output & (item 1 of p) & tab & (item 2 of p) & tab
        set output to output & (item 1 of s) & tab & (item 2 of s) & linefeed
      end try
    end repeat
  end tell
end tell
return output
'''


def parse_ui_output(raw: str, disp: display.Display, target_w: int) -> list[dict]:
    """Parse the tab-delimited osascript dump into elements with mapped coordinates.

    Element positions come in GLOBAL screen points; keep only named elements, drop
    whole-window containers, and map each center into the active display's served
    screenshot space. `sx/sy` stay GLOBAL (for clicking); `tx/ty` are display-relative.
    """
    els: list[dict] = []
    for line in (raw or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        role, name, xs, ys, ws, hs = parts[:6]
        name = name.strip()
        if not name:
            continue
        try:
            x, y, w, h = int(xs), int(ys), int(ws), int(hs)
        except ValueError:
            continue
        if w >= disp.w * 0.9 and h >= disp.h * 0.9:
            continue  # skip the whole-window container
        cx, cy = x + w // 2, y + h // 2                     # global center
        tx, ty = disp.global_to_target(cx, cy, target_w)
        els.append({"role": role.replace("AX", ""), "name": name,
                    "sx": cx, "sy": cy, "tx": tx, "ty": ty})
    return els


def elements(disp: display.Display, target_w: int) -> list[dict]:
    """Accessibility elements of the frontmost app (never raises; [] if unavailable)."""
    if sys.platform != "darwin":
        return []
    try:
        r = subprocess.run(["osascript", "-e", UI_SCRIPT],
                           capture_output=True, timeout=8, text=True)
    except (subprocess.TimeoutExpired, OSError):
        return []
    return parse_ui_output(r.stdout, disp, target_w)


def anchor_for_click(els: list[dict], x: int, y: int, radius: int = ANCHOR_RADIUS) -> dict | None:
    """The element a screenshot-space click landed on (role + name), or None if the
    click hit empty space — recorded so replay can re-find the target by identity."""
    if not els:
        return None
    best = min(els, key=lambda e: (e["tx"] - x) ** 2 + (e["ty"] - y) ** 2)
    if (best["tx"] - x) ** 2 + (best["ty"] - y) ** 2 <= radius ** 2:
        return {"role": best["role"], "name": best["name"]}
    return None


def resolve_anchor(els: list[dict], anchor: dict) -> tuple[int, int] | None:
    """Live GLOBAL coordinates of a recorded element: exact (role AND name) first, then
    a same-role name-substring fallback for labels that reflow (e.g. a button relabeled
    'Total: $4.82'). None if the element is gone — the caller falls back to coordinates."""
    role, name = anchor.get("role"), anchor.get("name")
    exact = next((e for e in els if e["role"] == role and e["name"] == name), None)
    if exact is not None:
        return exact["sx"], exact["sy"]
    if name:
        fuzzy = next((e for e in els if e["role"] == role and name.lower() in e["name"].lower()), None)
        if fuzzy is not None:
            return fuzzy["sx"], fuzzy["sy"]
    return None
