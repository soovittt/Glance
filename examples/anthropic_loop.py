"""Illustrative computer-use loop showing exactly where Glance plugs in.

This is the same shape as Anthropic's reference `loop.py`, trimmed to the essential
control flow. The ONE Glance-specific line is marked with `# <-- GLANCE`.

It is illustrative: to actually run it you need the `anthropic` SDK, an API key,
and a real screen/VM behind `take_screenshot()` and `perform_action()`. The point
is to see the integration seam, not to ship a desktop environment.

    pip install anthropic
    export ANTHROPIC_API_KEY=...
"""

from __future__ import annotations

from typing import Any

# from anthropic import Anthropic
from glance import Observer

MODEL = "claude-opus-4-8"  # any computer-use-capable Claude model
DISPLAY_W, DISPLAY_H = 1280, 720


def take_screenshot() -> bytes:
    """Your code: grab the screen as PNG bytes (mss, pyautogui, a VM API, etc.)."""
    raise NotImplementedError("wire this to your screen capture")


def perform_action(action: dict[str, Any]) -> None:
    """Your code: execute a click/type/scroll on the real machine."""
    raise NotImplementedError("wire this to your input automation")


def run(task: str) -> None:
    # client = Anthropic()
    observer = Observer()  # <-- GLANCE: one stateful gate for the whole session

    tools = [{"type": "computer_20250124", "name": "computer",
              "display_width_px": DISPLAY_W, "display_height_px": DISPLAY_H}]
    messages: list[dict[str, Any]] = [{"role": "user", "content": task}]

    while True:
        # response = client.beta.messages.create(
        #     model=MODEL, max_tokens=1024, tools=tools, messages=messages,
        #     betas=["computer-use-2025-01-24"],
        # )
        response = _fake_response()  # placeholder so the file imports cleanly

        messages.append({"role": "assistant", "content": response["content"]})

        tool_uses = [b for b in response["content"] if b["type"] == "tool_use"]
        if not tool_uses:
            break  # Claude is done

        tool_results = []
        for tu in tool_uses:
            perform_action(tu["input"])                 # do the click/type
            screenshot = take_screenshot()              # grab the new screen

            obs = observer.observe(screenshot)          # <-- GLANCE decides skip vs full
            # obs.blocks is a full image if the screen changed, else a ~15-token note.
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": obs.blocks,
            })

        messages.append({"role": "user", "content": tool_results})

    print(observer.stats.summary())  # e.g. "frames=42 skipped=14 (33%) saved=15330 (34%)"


def _fake_response() -> dict[str, Any]:
    return {"content": [{"type": "text", "text": "(wire up the real Anthropic client)"}]}


if __name__ == "__main__":
    run("Open the text editor and type hello world")
