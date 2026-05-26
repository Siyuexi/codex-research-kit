#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json
from pathlib import Path


def read_hook_event_name() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        raw = sys.stdin.read()
    except OSError:
        return ""
    if not raw.strip():
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if isinstance(payload, dict):
        value = payload.get("hook_event_name")
        if isinstance(value, str):
            return value
    return ""


def main() -> int:
    script = Path(__file__).resolve().parents[1] / "skills" / "codex-memory" / "scripts" / "codex_memory.py"
    if not script.exists():
        return 0
    action = sys.argv[1] if len(sys.argv) > 1 else "context"
    if action == "refresh-index":
        os.environ["CODEX_MEMORY_HOOK"] = "1"
        argv = [sys.executable, str(script), "index", "--write", "--scope", "both", "--limit", "80", "--scan-limit", "800"]
        hook_event_name = read_hook_event_name()
        if "--hook-json" in sys.argv[2:] or hook_event_name == "Stop":
            argv.append("--hook-json")
        elif "--quiet" in sys.argv[2:]:
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
