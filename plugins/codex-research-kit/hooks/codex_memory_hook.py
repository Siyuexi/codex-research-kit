#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().parents[1] / "skills" / "codex-memory" / "scripts" / "codex_memory.py"
    if not script.exists():
        return 0
    action = sys.argv[1] if len(sys.argv) > 1 else "context"
    if action == "refresh-index":
        os.environ["CODEX_MEMORY_HOOK"] = "1"
        argv = [sys.executable, str(script), "index", "--write", "--scope", "both", "--limit", "80", "--scan-limit", "800"]
        if "--quiet" in sys.argv[2:]:
            argv.append("--quiet")
    elif action == "context":
        os.environ["CODEX_MEMORY_HOOK"] = "1"
        argv = [sys.executable, str(script), "context"]
    else:
        return 0
    os.execv(sys.executable, argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
