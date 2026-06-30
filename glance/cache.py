"""Task-keyed procedure cache — the moat: learn a whole task once, replay it instantly.

Why keyed on the TASK and not on pixels: a whole-screen fingerprint can't tell a
calculator showing "7" from one showing "7x8" (the difference is below its
resolution), so a pixel-state key collides and goes ambiguous. A task LABEL doesn't
collide. So we store the entire ordered action sequence under a normalized task
label, and use the per-step fingerprint only to VERIFY a replay is on track (abort
to the model on drift) — never as the key.

Reliable for "do that exact task again": record open->click->click->= once, then a
single `task_begin(label)` replays all of it locally with zero model round-trips.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Step:
    action: dict[str, Any]   # normalized action, e.g. {"action":"click","x":10,"y":20}
    fingerprint: int         # 128-bit perceptual hash of the screen AFTER the action


@dataclass
class Procedure:
    label: str
    start_fingerprint: int       # screen the recording started from (replay sanity check)
    steps: list[Step] = field(default_factory=list)


def normalize(label: str) -> str:
    """So 'Compute 7x8' and 'compute   7x8' map to the same procedure."""
    return " ".join(label.lower().split())


class TaskCache:
    """Persistent store of task label -> ordered action procedure."""

    def __init__(self, path: str | Path = ".glance_tasks.json"):
        self.path = Path(path)
        self._procs: dict[str, Procedure] = {}
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError, ValueError):
            return  # corrupt/unreadable cache -> start empty rather than crash the server
        if not isinstance(raw, dict):
            return
        for key, p in raw.items():
            try:
                self._procs[key] = Procedure(
                    label=p["label"],
                    start_fingerprint=p["start_fingerprint"],
                    steps=[Step(**s) for s in p["steps"]],
                )
            except (KeyError, TypeError):
                continue  # skip a single malformed entry, keep the rest

    def save(self) -> None:
        raw = {k: asdict(p) for k, p in self._procs.items()}
        self.path.write_text(json.dumps(raw, indent=2))

    def put(self, label: str, start_fingerprint: int, steps: list[Step]) -> None:
        key = normalize(label)
        self._procs[key] = Procedure(label=label, start_fingerprint=start_fingerprint,
                                     steps=list(steps))
        self.save()

    def get(self, label: str) -> Procedure | None:
        return self._procs.get(normalize(label))

    def forget(self, label: str) -> bool:
        key = normalize(label)
        if key in self._procs:
            del self._procs[key]
            self.save()
            return True
        return False

    def labels(self) -> list[str]:
        return [p.label for p in self._procs.values()]

    def clear(self) -> None:
        self._procs = {}
        if self.path.exists():
            self.path.unlink()

    def __len__(self) -> int:
        return len(self._procs)
