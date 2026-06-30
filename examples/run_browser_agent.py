"""End-to-end test: a REAL Claude computer-use agent driving a REAL browser,
with Glance hooked into the screenshot step, reporting REAL token savings.

This is the honest proof that Glance works with Claude computer use:
  - Claude controls a headless Chromium via the `computer` tool (screenshot/click/type).
  - After every action we take a screenshot and pass it through Glance's Observer.
  - When the screen didn't change, Glance sends a ~15-token note instead of the
    ~1,500-token image — so Claude keeps going without re-looking.
  - At the end we print BOTH the real API token usage AND Glance's exact
    counterfactual ("we sent X, would have sent Y on this same run -> saved Z%").

Why browser instead of a desktop VM: it's the lightest real environment that runs
on a laptop. The `computer` tool doesn't care — it sees an image and emits clicks;
we map those clicks onto the browser viewport.

Setup:
    pip install -e ".[examples]"
    playwright install chromium
    export ANTHROPIC_API_KEY=...

Run (Glance on, the default):
    python examples/run_browser_agent.py --task "Go to example.com and click the 'More information' link"

Compare against Glance off:
    python examples/run_browser_agent.py --task "...same task..." --no-glance
"""

from __future__ import annotations

import argparse
import os

from anthropic import Anthropic
from playwright.sync_api import sync_playwright

from glance import GlancePolicy, Observer

# A computer-use-capable Claude model.
MODEL = "claude-sonnet-4-6"
WIDTH, HEIGHT = 1280, 800

# Map Claude's key names onto Playwright's.
KEY_MAP = {
    "Return": "Enter", "KP_Enter": "Enter", "Escape": "Escape", "BackSpace": "Backspace",
    "Tab": "Tab", "space": " ", "Page_Down": "PageDown", "Page_Up": "PageUp",
    "Down": "ArrowDown", "Up": "ArrowUp", "Left": "ArrowLeft", "Right": "ArrowRight",
}


def perform(page, action: dict) -> None:
    """Execute one `computer` tool action against the browser."""
    kind = action.get("action")
    coord = action.get("coordinate")

    if kind in ("screenshot", "wait", "cursor_position"):
        return  # no-op here; the screenshot is taken by the caller after every action
    if kind == "mouse_move" and coord:
        page.mouse.move(coord[0], coord[1])
    elif kind in ("left_click", "right_click", "middle_click", "double_click") and coord:
        button = {"right_click": "right", "middle_click": "middle"}.get(kind, "left")
        clicks = 2 if kind == "double_click" else 1
        page.mouse.click(coord[0], coord[1], button=button, click_count=clicks)
    elif kind == "type":
        page.keyboard.type(action.get("text", ""))
    elif kind == "key":
        for part in action.get("text", "").split("+"):
            page.keyboard.press(KEY_MAP.get(part, part))
    elif kind == "scroll" and coord:
        dy = int(action.get("scroll_amount", 3)) * 100
        if action.get("scroll_direction") == "up":
            dy = -dy
        page.mouse.move(coord[0], coord[1])
        page.mouse.wheel(0, dy)
    # other/unsupported actions are intentionally ignored for this minimal demo


def run(task: str, use_glance: bool, model: str, max_steps: int, headful: bool) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    client = Anthropic()
    observer = Observer(GlancePolicy(enabled=use_glance))
    tools = [{
        "type": "computer_20250124", "name": "computer",
        "display_width_px": WIDTH, "display_height_px": HEIGHT,
    }]
    messages: list[dict] = [{"role": "user", "content": task}]
    total_in = total_out = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headful)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto("https://www.google.com")

        for step in range(max_steps):
            resp = client.beta.messages.create(
                model=model, max_tokens=1024, tools=tools, messages=messages,
                betas=["computer-use-2025-01-24"],
            )
            total_in += resp.usage.input_tokens
            total_out += resp.usage.output_tokens

            messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                print(f"\n[done in {step + 1} model turns] Claude finished.")
                break

            results = []
            for tu in tool_uses:
                perform(page, tu.input)
                page.wait_for_timeout(400)            # let the page settle
                screenshot = page.screenshot()
                obs = observer.observe(screenshot)    # <-- GLANCE hooks in here
                results.append({
                    "type": "tool_result", "tool_use_id": tu.id, "content": obs.blocks,
                })
            messages.append({"role": "user", "content": results})

        browser.close()

    print("\n" + "=" * 60)
    print(f"  Glance: {'ON' if use_glance else 'OFF (baseline)'}")
    print(f"  {observer.stats.summary()}")
    print(f"  real API tokens this run: input={total_in}  output={total_out}")
    if use_glance and observer.stats.tokens_saved:
        print(f"  >>> Glance skipped {observer.stats.frames_skipped} redundant "
              f"screenshots, ~{observer.stats.tokens_saved} image tokens "
              f"({observer.stats.pct_saved:.0f}%) on THIS run.")
    print("=" * 60)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="natural-language task for Claude")
    ap.add_argument("--no-glance", action="store_true", help="disable Glance (baseline)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--headful", action="store_true", help="show the browser window")
    args = ap.parse_args()
    run(args.task, not args.no_glance, args.model, args.max_steps, args.headful)


if __name__ == "__main__":
    main()
