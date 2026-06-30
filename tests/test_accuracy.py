"""Regression guard: the labeled benchmark must stay accurate AND safe.

This pins the result the self-improving loop reached, so a future change that
regresses accuracy or (worse) starts skipping real changes fails CI immediately.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))

from eval import make_dataset, score  # noqa: E402

from glance import GlancePolicy  # noqa: E402


def test_default_policy_is_safe_and_accurate():
    data = make_dataset(per_kind=20)
    s = score(GlancePolicy(), data)
    # Safety is non-negotiable: a real change must never be skipped.
    assert s.missed_changes == 0, "default policy skipped a real change (blinds the agent)"
    # Accuracy target the loop converged to.
    assert s.accuracy >= 90.0, f"accuracy regressed to {s.accuracy:.1f}%"


def test_unchanged_frames_are_actually_skipped():
    data = make_dataset(per_kind=20)
    s = score(GlancePolicy(), data)
    # The whole point is savings: we should skip the clear majority of no-ops.
    assert s.skip_rate >= 90.0, f"skip rate dropped to {s.skip_rate:.0f}% (lost savings)"
