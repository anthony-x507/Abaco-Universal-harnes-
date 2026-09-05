#!/usr/bin/env python3
"""Turn the white studio backdrop of the crystal Ábaco mark into real alpha.

The delivered artwork is a photo-style render on solid white. The silver
"UNIVERSAL HARNESS" / "abaco" lettering and the crystal glints are near-white
too, so a global white-to-alpha replacement would punch holes through them.

Backdrop is therefore found structurally, in two passes:

1. Near-white reachable from the canvas border is the outer backdrop.
2. An enclosed near-white region is backdrop seen through an opening in the
   mark (the counter of the "A") only when it is flat, essentially pure white.
   Lettering highlights are gradients, so they stay opaque.

The mask is then grown a couple of pixels into the mark and those band pixels
get partial alpha, which removes the white fringe a hard cut would leave.

Usage: scripts/make_logo_transparent.py [source.png] [dest.png ...]
"""

from __future__ import annotations

import sys
from collections import deque
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "web" / "src" / "assets" / "logo.png"
DEFAULT_TARGETS = (
    ROOT / "web" / "src" / "assets" / "logo.png",
    ROOT / "web" / "public" / "logo.png",
)

# A pixel can only join the backdrop if every channel is at least this bright.
BACKDROP_FLOOR = 210
# An enclosed region needs this much flat, near-pure white to count as backdrop.
PURE_WHITE = 248
PURE_FRACTION = 0.90
FLAT_STD = 4.0
MIN_ENCLOSED_AREA = 1000
# How far the backdrop grows into the mark to build the soft edge band.
FEATHER_PX = 2

NEIGHBOURS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _fill(
    light: np.ndarray, seen: np.ndarray, seeds: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """4-connected flood fill over ``light``, returning the filled pixels."""
    height, width = light.shape
    queue: deque[tuple[int, int]] = deque()
    for y, x in seeds:
        if light[y, x] and not seen[y, x]:
            seen[y, x] = True
            queue.append((y, x))
    filled: list[tuple[int, int]] = []
    while queue:
        y, x = queue.popleft()
        filled.append((y, x))
        for dy, dx in NEIGHBOURS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and light[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                queue.append((ny, nx))
    return filled


def backdrop_mask(rgb: np.ndarray) -> np.ndarray:
    height, width = rgb.shape[:2]
    darkest = rgb.min(axis=2)
    light = darkest >= BACKDROP_FLOOR
    seen = np.zeros((height, width), dtype=bool)
    mask = np.zeros((height, width), dtype=bool)

    border = [(0, x) for x in range(width)] + [(height - 1, x) for x in range(width)]
    border += [(y, 0) for y in range(height)] + [(y, width - 1) for y in range(height)]
    for y, x in _fill(light, seen, border):
        mask[y, x] = True

    for y, x in np.argwhere(light & ~seen):
        region = _fill(light, seen, [(int(y), int(x))])
        if len(region) < MIN_ENCLOSED_AREA:
            continue
        rows = np.fromiter((p[0] for p in region), dtype=np.intp, count=len(region))
        cols = np.fromiter((p[1] for p in region), dtype=np.intp, count=len(region))
        values = darkest[rows, cols]
        pure = float((values >= PURE_WHITE).mean())
        if pure >= PURE_FRACTION and float(values.std()) <= FLAT_STD:
            mask[rows, cols] = True
    return mask


def grow(mask: np.ndarray, steps: int) -> np.ndarray:
    """4-connected dilation. Builds the feather band next to the backdrop."""
    grown = mask.copy()
    for _ in range(steps):
        shifted = grown.copy()
        shifted[1:, :] |= grown[:-1, :]
        shifted[:-1, :] |= grown[1:, :]
        shifted[:, 1:] |= grown[:, :-1]
        shifted[:, :-1] |= grown[:, 1:]
        grown = shifted
    return grown


def add_alpha(image: Image.Image) -> Image.Image:
    if "A" in image.getbands() and image.getchannel("A").getextrema()[0] < 255:
        # Running on an earlier result would re-read the already un-blended
        # edge as mark and drop the feather, so refuse instead of degrading it.
        raise ValueError("source already has alpha; pass the opaque original")
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    backdrop = backdrop_mask(rgb)
    soft = grow(backdrop, FEATHER_PX)

    # A white backdrop means coverage shows up as a luminance deficit.
    coverage = (255 - rgb.min(axis=2)).astype(np.float32)
    alpha = np.full(rgb.shape[:2], 255.0, dtype=np.float32)
    alpha[soft] = coverage[soft]

    out = rgb.astype(np.float32)
    # Un-blend the white backdrop out of partly covered pixels so no light
    # fringe survives around the mark.
    partial = (alpha > 0) & (alpha < 255)
    scale = alpha[partial, None] / 255.0
    out[partial] = np.clip((out[partial] - 255.0 * (1.0 - scale)) / scale, 0, 255)

    rgba = np.dstack([out.astype(np.uint8), alpha.round().astype(np.uint8)])
    return Image.fromarray(rgba, mode="RGBA")


def main(argv: list[str]) -> int:
    source = Path(argv[1]) if len(argv) > 1 else DEFAULT_SOURCE
    targets = [Path(item) for item in argv[2:]] or list(DEFAULT_TARGETS)
    if not source.is_file():
        print(f"logo missing: {source}", file=sys.stderr)
        return 2

    try:
        with Image.open(source) as opened:
            result = add_alpha(opened)
    except ValueError as exc:
        print(f"{source}: {exc}", file=sys.stderr)
        return 2

    buffer = BytesIO()
    result.save(buffer, format="PNG", optimize=True)
    # The desktop test requires every copy to be byte-identical.
    payload = buffer.getvalue()
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"wrote {target} ({len(payload)} bytes)")

    alpha = np.asarray(result)[:, :, 3]
    total = alpha.size
    print(
        f"alpha: {(alpha == 0).mean():.1%} clear, "
        f"{(alpha == 255).mean():.1%} opaque, "
        f"{((alpha > 0) & (alpha < 255)).sum()} soft edge px of {total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
