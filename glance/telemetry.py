"""Session telemetry for the glance-cua server — observability across ALL tools.

Every efficiency-relevant tool call emits one JSONL record (modality, est tokens,
round-trips saved by batching, etc.). `summarize()` turns that into a report so you
can see where tokens and model round-trips actually go and decide what mix is best.

Records look like:
  {"ts":..,"tool":"computer_screenshot","modality":"image","event":"send","est_tokens":1441}
  {"ts":..,"tool":"ui_tree","modality":"text","n_elements":24,"est_tokens":180}
  {"ts":..,"tool":"computer_batch","modality":"batch","n_ran":4,"est_tokens":1441,"round_trips_saved":3}
  {"ts":..,"tool":"click_element","modality":"action","est_tokens":8,"avoided_screenshot":true}
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

DEFAULT = Path.home() / ".glance" / "session_telemetry.jsonl"


def path() -> Path:
    return Path(os.environ.get("GLANCE_TELEMETRY", str(DEFAULT)))


def emit(**fields) -> None:
    """Append one telemetry record (never raises)."""
    fields.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            f.write(json.dumps(fields) + "\n")
    except OSError:
        pass


def reset() -> None:
    """Start a fresh telemetry session (clears the file) so a run can be measured in
    isolation. Called by glance_reset."""
    p = path()
    try:
        if p.exists():
            p.unlink()
    except OSError:
        pass


def load(p: str | Path | None = None) -> list[dict]:
    fp = Path(p) if p else path()
    if not fp.exists():
        return []
    out = []
    for line in fp.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def summarize(records: list[dict]) -> str:
    if not records:
        return "no telemetry yet — use the glance-cua tools, then call session_report."

    n = len(records)                       # each tool call ~= one model round-trip
    by_tool: dict[str, int] = {}
    tokens = {"image": 0, "text": 0, "action": 0, "note": 0}
    images_sent = images_skipped = ui_trees = avoided = 0
    actions_in_batches = batches = rt_saved = 0
    img_samples = []

    for r in records:
        by_tool[r.get("tool", "?")] = by_tool.get(r.get("tool", "?"), 0) + 1
        mod = r.get("modality", "action")
        est = int(r.get("est_tokens", 0) or 0)
        if mod == "image":
            if r.get("event") == "skip":
                tokens["note"] += est
                images_skipped += 1
            else:
                tokens["image"] += est
                images_sent += 1
                img_samples.append(est)
        elif mod == "text":
            tokens["text"] += est
            ui_trees += 1
        elif mod == "batch":
            tokens["image"] += est                 # a batch costs one screenshot at the end
            if est:
                img_samples.append(est)
            batches += 1
            actions_in_batches += int(r.get("n_ran", 0) or 0)
            rt_saved += int(r.get("round_trips_saved", 0) or 0)
        else:
            tokens["action"] += est
            if r.get("avoided_screenshot"):
                avoided += 1

    total_tokens = sum(tokens.values())
    avg_img = round(sum(img_samples) / len(img_samples)) if img_samples else 1441

    # Naive 1-screenshot-1-action baseline: every action would need its own turn+shot.
    naive_rounds = n + rt_saved
    naive_tokens = naive_rounds * avg_img
    saved_pct = round(100 * (naive_tokens - total_tokens) / naive_tokens, 1) if naive_tokens else 0.0

    lines = [
        f"=== glance-cua session telemetry ({n} tool calls) ===",
        f"model round-trips        : {n}   (naive 1:1 loop would be ~{naive_rounds})",
        f"  saved by batching      : {rt_saved} round-trips  ({batches} batches, "
        f"{actions_in_batches} actions)",
        "",
        "observations:",
        f"  screenshots (image)    : {images_sent + images_skipped}  "
        f"({images_sent} sent, {images_skipped} skipped)",
        f"  ui_tree (text)         : {ui_trees}",
        f"  screenshot-free actions: {avoided}  (click_element / type_into)",
        "",
        "estimated tokens:",
        f"  image                  : {tokens['image']}",
        f"  text (ui_tree)         : {tokens['text']}",
        f"  notes + actions        : {tokens['note'] + tokens['action']}",
        f"  TOTAL                  : {total_tokens}",
        f"  vs naive screenshot loop (~{naive_tokens}): {saved_pct}% fewer  <-- headline efficiency",
        "",
        "per tool:",
    ]
    for tool, c in sorted(by_tool.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {tool:22} {c}")
    return "\n".join(lines)
