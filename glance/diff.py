"""Frame-difference primitives.

The whole job of this module: given two screenshots, answer
"did the screen meaningfully change, and where?" — fast and accurately.

Design note (read this, it's the interesting part):
We do NOT hand-roll a per-pixel Python loop (that would take ~1 second per
frame). We hand the whole image array to OpenCV/NumPy, which run the comparison
as one vectorized SIMD operation in compiled C (~1-2 ms per frame).

We also deliberately use a full-resolution `absdiff` as the default gate rather
than a coarse perceptual hash (dHash). A dHash is faster (~0.2 ms) but it
downscales to 8x8 and would MISS small changes like a single typed character —
which for an agent means missing a real screen update. Since the diff is ~0.1%
of step latency (the Claude API call dominates at ~1-2 s), trading 1.8 ms for
accuracy is the correct call. dHash is provided below as an optional pre-gate
for users processing huge volumes who accept the coarseness.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


def to_array(image) -> np.ndarray:
    """Accept PNG/JPEG bytes, a NumPy array, or a PIL image -> BGR uint8 array."""
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, (bytes, bytearray)):
        buf = np.frombuffer(bytes(image), dtype=np.uint8)
        arr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if arr is None:
            raise ValueError("Could not decode image bytes")
        return arr
    # Best-effort PIL.Image support without importing Pillow as a hard dep.
    if hasattr(image, "convert"):
        return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    raise TypeError(f"Unsupported image type: {type(image)!r}")


def to_gray(image) -> np.ndarray:
    """Grayscale view of an image (cheaper to diff, change is luminance anyway)."""
    arr = to_array(image)
    if arr.ndim == 3:
        return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    return arr


@dataclass
class FrameDiff:
    """Result of comparing two frames."""

    changed_fraction: float          # fraction of pixels that changed (0.0 - 1.0)
    bbox: tuple[int, int, int, int] | None  # (x, y, w, h) of changed region, or None

    def is_changed(self, threshold: float) -> bool:
        return self.changed_fraction >= threshold


def diff_frames(prev_gray: np.ndarray, curr_gray: np.ndarray, pixel_threshold: int = 12) -> FrameDiff:
    """Compare two grayscale frames.

    pixel_threshold: a pixel counts as "changed" only if it differs by more than
    this (0-255). Filters out JPEG/compression noise and sub-pixel cursor shimmer.
    """
    if prev_gray.shape != curr_gray.shape:
        # Different resolution => treat as a full change (can't diff meaningfully).
        return FrameDiff(changed_fraction=1.0, bbox=None)

    delta = cv2.absdiff(prev_gray, curr_gray)             # |a - b| per pixel, in C
    mask = (delta > pixel_threshold).astype(np.uint8)     # 1 where it changed
    changed_fraction = float(mask.mean())                 # mean of 0/1 == fraction changed

    bbox = None
    if changed_fraction > 0:
        ys, xs = np.where(mask)                            # coords of changed pixels
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        bbox = (x0, y0, x1 - x0 + 1, y1 - y0 + 1)

    return FrameDiff(changed_fraction=changed_fraction, bbox=bbox)


# --- Optional fast pre-gate (perceptual hash). Coarse: misses small changes. ---

def dhash(image, hash_size: int = 8) -> int:
    """64-bit difference hash. Cheap fingerprint of a frame (~0.2 ms).

    Shrinks to (hash_size+1) x hash_size, then encodes whether each pixel is
    brighter than its right neighbor. Two near-identical frames -> near-identical
    hashes. Useful as a *coarse* skip gate before the accurate absdiff.
    """
    gray = to_gray(image)
    small = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]          # boolean gradient, shape (hash_size, hash_size)
    bits = np.packbits(diff.flatten())           # pack bools -> bytes
    return int.from_bytes(bits.tobytes(), "big")


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes (0 == identical)."""
    return (a ^ b).bit_count()


def fingerprint(image, hash_size: int = 8) -> int:
    """128-bit perceptual fingerprint combining horizontal AND vertical gradients.

    Plain dHash compares only left-right gradients, so it is BLIND to changes that
    are purely horizontal banding (distance 0). For the macro-replay safety guard we
    cannot have that blind spot, so we OR together a horizontal dHash and a vertical
    dHash. Compare two fingerprints with `hamming` (out of 128 bits).
    """
    gray = to_gray(image)
    small = cv2.resize(gray, (hash_size + 1, hash_size + 1), interpolation=cv2.INTER_AREA)
    h = small[:hash_size, 1:] > small[:hash_size, :hash_size]   # left-right gradient
    v = small[1:, :hash_size] > small[:hash_size, :hash_size]   # top-bottom gradient
    hbits = np.packbits(h.flatten()).tobytes()
    vbits = np.packbits(v.flatten()).tobytes()
    return int.from_bytes(hbits + vbits, "big")
