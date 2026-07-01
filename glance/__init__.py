"""Glance — make Claude *glance*, not stare.

A drop-in efficiency layer for computer-use agents: skip screenshots that didn't
change (Layer 1, Observer) and replay action sequences you've already done
(Layer 2, MacroCache). Fewer tokens, less latency, same behavior.
"""

from .cache import Procedure, Step, TaskCache
from .decide import Decision, explain, is_meaningful_change
from .diff import FrameDiff, dhash, diff_frames, fingerprint, hamming
from .metrics import GlanceStats, estimate_image_tokens
from .observer import Observation, Observer
from .policy import GlancePolicy

__version__ = "0.1.0"

__all__ = [
    "Observer",
    "Observation",
    "GlancePolicy",
    "GlanceStats",
    "TaskCache",
    "Procedure",
    "Step",
    "Decision",
    "explain",
    "is_meaningful_change",
    "FrameDiff",
    "diff_frames",
    "dhash",
    "fingerprint",
    "hamming",
    "estimate_image_tokens",
    "__version__",
]
