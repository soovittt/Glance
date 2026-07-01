"""Tests for the keyboard module (System Events script generation + fallback)."""

from __future__ import annotations

import pytest

from glance import keys


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
    monkeypatch.setattr(keys.subprocess, "run", lambda *a, **k: seen.append(a[0][2]))
    keys.mac_key(combo)
    assert seen[0] == f'tell application "System Events" to {expected}'


def test_press_key_falls_back_to_pyautogui(monkeypatch):
    monkeypatch.setattr(keys, "mac_key", lambda k: False)   # force the fallback path
    pressed = {}
    fake = type("pg", (), {
        "hotkey": staticmethod(lambda *a: pressed.update(hotkey=a)),
        "press": staticmethod(lambda k: pressed.update(press=k)),
    })()
    keys.press_key(fake, "cmd+c")
    assert pressed["hotkey"] == ("command", "c")            # combo -> mapped names
    keys.press_key(fake, "enter")
    assert pressed["press"] == "enter"
