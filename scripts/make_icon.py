#!/usr/bin/env python3
"""Build Universal.iconset and Universal.icns from the crystal Ábaco mark.

On Linux this writes a PNG-based .icns that macOS accepts (10.7+).
On a Mac, scripts/make_icns.sh prefers sips + iconutil when they exist.
"""

from __future__ import annotations

import struct
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "src" / "assets" / "logo.png"
ICONSET = ROOT / "Universal.iconset"
ICNS = ROOT / "Universal.icns"

ICONSET_FILES = (
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
)

# PNG-in-icns types used by modern macOS.
ICNS_PNG = (
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
    ("ic11", 32),
    ("ic12", 64),
    ("ic13", 256),
    ("ic14", 512),
)


def _png_bytes(image: Image.Image, size: int) -> bytes:
    resized = image.resize((size, size), Image.Resampling.LANCZOS)
    buf = BytesIO()
    resized.save(buf, format="PNG")
    return buf.getvalue()


def write_iconset(image: Image.Image) -> None:
    ICONSET.mkdir(exist_ok=True)
    for size, name in ICONSET_FILES:
        path = ICONSET / name
        path.write_bytes(_png_bytes(image, size))


def write_icns(image: Image.Image) -> None:
    chunks: list[bytes] = []
    for tag, size in ICNS_PNG:
        payload = _png_bytes(image, size)
        header = tag.encode("ascii") + struct.pack(">I", 8 + len(payload))
        chunks.append(header + payload)
    body = b"".join(chunks)
    ICNS.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def main() -> int:
    if not SOURCE.is_file():
        print(f"logo missing: {SOURCE}", file=sys.stderr)
        return 2
    image = Image.open(SOURCE).convert("RGBA")
    write_iconset(image)
    write_icns(image)
    print(f"wrote {ICONSET.name}/ and {ICNS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
