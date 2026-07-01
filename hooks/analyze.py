#!/usr/bin/env python3
"""Analyze Glance hook telemetry — visibility to tune accuracy and prove savings.

Reads ~/.glance/telemetry.jsonl (one record per screenshot) and reports:
  - skip rate + token savings
  - decision-reason breakdown
  - changed_fraction distribution for SENDs vs SKIPs (is the threshold well placed?)
  - accuracy watch: borderline skips and near-zero sends worth a human look
  - per-step decide latency

Run:  python hooks/analyze.py            (default ~/.glance/telemetry.jsonl)
      python hooks/analyze.py FILE.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT = Path.home() / ".glance" / "telemetry.jsonl"


def _load(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"no telemetry at {path} — run some computer use with the hook first")
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _quantiles(xs: list[float]) -> str:
    if not xs:
        return "(none)"
    xs = sorted(xs)
    def q(p):  # noqa: E306
        return xs[min(len(xs) - 1, int(p * len(xs)))]
    return f"min={xs[0]:.5f} p50={q(0.5):.5f} p90={q(0.9):.5f} max={xs[-1]:.5f}"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    recs = _load(path)
    if not recs:
        raise SystemExit(f"{path} is empty")

    n = len(recs)
    skips = [r for r in recs if r.get("event") == "skip"]
    sends = [r for r in recs if r.get("event") == "send"]
    saved = recs[-1].get("cum_tokens_saved", 0)
    baseline = sum(r.get("est_tokens", 0) for r in recs)

    print(f"\n=== Glance telemetry: {path} ===")
    print(f"screenshots     : {n}")
    print(f"  sent          : {len(sends)} ({_pct(len(sends), n)}%)")
    print(f"  skipped       : {len(skips)} ({_pct(len(skips), n)}%)")
    print(f"tokens saved    : {saved} of ~{baseline} baseline ({_pct(saved, baseline)}%)")

    print("\nreasons:")
    reasons: dict[str, int] = {}
    for r in recs:
        reasons[r.get("reason", "?")] = reasons.get(r.get("reason", "?"), 0) + 1
    for reason, c in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {reason:16} {c:>5}  ({_pct(c, n)}%)")

    def fracs(rows):
        return [r["changed_fraction"] for r in rows if r.get("changed_fraction") is not None]

    print("\nchanged_fraction distribution (the signal to tune skip_threshold):")
    print(f"  SKIP frames : {_quantiles(fracs(skips))}")
    print(f"  SEND frames : {_quantiles(fracs(sends))}")

    # Accuracy watch: skips whose change was close to the send band, and near-zero sends.
    borderline = [r for r in skips if (r.get("changed_fraction") or 0) >= 0.001]
    tiny_sends = [r for r in sends
                  if r.get("reason") == "changed" and (r.get("changed_fraction") or 1) < 0.0002]
    print("\naccuracy watch:")
    print(f"  borderline skips (fraction >=0.001)   : {len(borderline)}  <- review if any real change was hidden")
    print(f"  near-zero 'changed' sends (<0.0002)   : {len(tiny_sends)}  <- candidates to also skip (more savings)")

    lat = [r.get("decide_ms", 0) for r in recs if r.get("decide_ms")]
    if lat:
        print(f"\ndecide latency  : {_quantiles([float(x) for x in lat])} ms  (vs ~1000ms model call)")
    print()


if __name__ == "__main__":
    main()
