"""Display geometry + capture (macOS / Quartz).

Isolates every multi-display concern in one place: which display an app is on, its
global bounds, capturing just that display, and mapping between the served-screenshot
space and global screen coordinates.

The `Display` geometry is pure and dependency-free (unit-tested); the native capture
is Quartz and degrades gracefully to None so callers can fall back.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Display:
    """One display in global screen POINTS: origin (x, y) and size (w, h)."""

    x: int
    y: int
    w: int
    h: int

    def target_size(self, target_w: int) -> tuple[int, int]:
        """(w, h) to serve this display at — preserves aspect ratio (no distortion)."""
        return target_w, max(1, round(target_w * self.h / self.w))

    def to_global(self, tx: int, ty: int, target_w: int) -> tuple[int, int]:
        """Map a point in served-screenshot space back to global screen points."""
        tw, th = self.target_size(target_w)
        return round(self.x + tx * self.w / tw), round(self.y + ty * self.h / th)

    def global_to_target(self, gx: float, gy: float, target_w: int) -> tuple[int, int]:
        """Map a global screen point into this display's served-screenshot space."""
        tw, th = self.target_size(target_w)
        return round((gx - self.x) * tw / self.w), round((gy - self.y) * th / self.h)

    def contains(self, gx: float, gy: float) -> bool:
        return self.x <= gx < self.x + self.w and self.y <= gy < self.y + self.h


def _quartz():
    import Quartz
    return Quartz


def displays() -> list[Display]:
    """All active displays in global point coords ([] if Quartz is unavailable)."""
    try:
        q = _quartz()
        err, ids, n = q.CGGetActiveDisplayList(16, None, None)
        if err:
            return []
        out = []
        for did in list(ids)[:n]:
            b = q.CGDisplayBounds(did)
            out.append(Display(int(b.origin.x), int(b.origin.y),
                               int(b.size.width), int(b.size.height)))
        return out
    except Exception:  # noqa: BLE001 - any pyobjc/import issue -> no displays, caller falls back
        return []


def containing(ds: list[Display], gx: float, gy: float) -> Display | None:
    """The display whose bounds contain global point (gx, gy)."""
    return next((d for d in ds if d.contains(gx, gy)), None)


def main_display(ds: list[Display]) -> Display | None:
    """The primary display (origin 0,0), or the first one if none is at the origin."""
    if not ds:
        return None
    return next((d for d in ds if d.x == 0 and d.y == 0), ds[0])


def capture(d: Display) -> bytes | None:
    """PNG bytes of one display's region via Quartz (None if capture fails)."""
    try:
        q = _quartz()
        rect = q.CGRectMake(d.x, d.y, d.w, d.h)
        img = q.CGWindowListCreateImage(rect, q.kCGWindowListOptionOnScreenOnly,
                                        q.kCGNullWindowID, q.kCGWindowImageDefault)
        if img is None:
            return None
        from Foundation import NSMutableData
        data = NSMutableData.alloc().init()
        dest = q.CGImageDestinationCreateWithData(data, "public.png", 1, None)
        if dest is None:
            return None
        q.CGImageDestinationAddImage(dest, img, None)
        if not q.CGImageDestinationFinalize(dest):
            return None
        return bytes(data)
    except Exception:  # noqa: BLE001 - degrade to None so the caller can fall back
        return None
