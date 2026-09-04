"""PyInstaller / desktop entry. Starts the same factory as ``universal serve``."""

from __future__ import annotations

import sys

from universal.desktop import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
