"""Token/efficiency accounting so every claim Glance makes is measured, not vibes."""

from __future__ import annotations

from dataclasses import dataclass, field


def estimate_image_tokens(width: int, height: int) -> int:
    """Anthropic's documented rule of thumb: image tokens ~= (w * h) / 750.

    A 1280x720 screenshot ~= 1229 tokens; a 1024x768 one ~= 1049 tokens.
    """
    return round((width * height) / 750)


# Tokens for the short "nothing changed" text note we send instead of an image.
SKIP_NOTE_TOKENS = 15


@dataclass
class GlanceStats:
    """Running totals across a session, for before/after reporting."""

    frames_total: int = 0
    frames_skipped: int = 0
    tokens_sent: int = 0          # what Glance actually sent
    tokens_baseline: int = 0      # what a full-image-every-step loop would have sent
    per_frame: list[dict] = field(default_factory=list)

    def record(self, *, skipped: bool, image_tokens: int) -> None:
        self.frames_total += 1
        self.tokens_baseline += image_tokens
        if skipped:
            self.frames_skipped += 1
            self.tokens_sent += SKIP_NOTE_TOKENS
        else:
            self.tokens_sent += image_tokens
        self.per_frame.append({"skipped": skipped, "image_tokens": image_tokens})

    @property
    def tokens_saved(self) -> int:
        return self.tokens_baseline - self.tokens_sent

    @property
    def pct_saved(self) -> float:
        if self.tokens_baseline == 0:
            return 0.0
        return 100.0 * self.tokens_saved / self.tokens_baseline

    @property
    def skip_rate(self) -> float:
        if self.frames_total == 0:
            return 0.0
        return 100.0 * self.frames_skipped / self.frames_total

    def summary(self) -> str:
        return (
            f"frames={self.frames_total} "
            f"skipped={self.frames_skipped} ({self.skip_rate:.0f}%) "
            f"tokens={self.tokens_sent} vs baseline={self.tokens_baseline} "
            f"saved={self.tokens_saved} ({self.pct_saved:.0f}%)"
        )
