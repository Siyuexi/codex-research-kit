#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().parents[1] / "skills" / "codex-memory" / "scripts" / "codex_memory.py"
    if not script.exists():
        return 0
    os.execv(sys.executable, [sys.executable, str(script), "context"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
