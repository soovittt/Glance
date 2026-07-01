"""Data model for the self-improvement suite.

A `Task` pairs a natural-language prompt with a programmatic `verify()` that checks the
end state — this is what turns "did it work?" into a signal the loop can optimize
against. A `TaskResult` records correctness *and* efficiency for one run.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field


@dataclass
class VerifyResult:
    ok: bool
    detail: str = ""
    manual: bool = False        # True => couldn't auto-check; excluded from the success rate


@dataclass
class Task:
    id: str
    difficulty: str             # "easy" | "medium" | "hard"
    prompt: str                 # what a real user would type
    verify: Callable[[], VerifyResult]
    setup: Callable[[], None] | None = None     # clean slate before the run (idempotent)


@dataclass
class TaskResult:
    id: str
    difficulty: str
    ok: bool
    manual: bool
    detail: str
    tokens: int = 0
    round_trips: int = 0
    naive_round_trips: int = 0
    tool_mix: dict[str, int] = field(default_factory=dict)
    duration_s: float = 0.0
    error: str = ""             # "" | "timeout" | "exit <n>" | "launch: ..." — agent-level failure

    @property
    def pct_vs_naive(self) -> float:
        naive_tokens = self.naive_round_trips * 1616  # ~one screenshot per naive round-trip
        return round(100 * (naive_tokens - self.tokens) / naive_tokens, 1) if naive_tokens else 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> TaskResult:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
