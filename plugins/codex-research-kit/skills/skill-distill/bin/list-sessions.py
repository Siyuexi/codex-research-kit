#!/usr/bin/env python3
"""List Codex rollout sessions for distillation.

Codex stores the authoritative thread index in ~/.codex/state_5.sqlite. This
helper opens that DB read-only and returns rollout JSONL paths modified inside
the requested window.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path.home() / ".codex" / "distill" / "state.json"
CODEX_DB = Path.home() / ".codex" / "state_5.sqlite"


def parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def load_state_since() -> datetime | None:
    if not STATE_PATH.exists():
        return None
    try:
        last = json.loads(STATE_PATH.read_text(encoding="utf-8")).get("last_run")
    except (OSError, json.JSONDecodeError):
        return None
    return parse_iso(last) if last else None


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def compact(value: str, limit: int = 500) -> str:
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def db_rows() -> list[sqlite3.Row]:
    if not CODEX_DB.exists():
        raise SystemExit(f"Codex state DB not found: {CODEX_DB}")
    conn = sqlite3.connect(f"file:{CODEX_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """
            SELECT id, rollout_path, updated_at_ms, cwd, title, first_user_message
            FROM threads
            WHERE archived = 0
            ORDER BY updated_at_ms ASC, id ASC
            """
        ).fetchall()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--since", help="ISO 8601 timestamp; sessions updated after this are listed")
    group.add_argument("--days", type=float, help="Look back N days")
    parser.add_argument("--project", help="Only include sessions whose cwd contains this text")
    parser.add_argument("--include-current-session", metavar="SID")
    parser.add_argument("--exclude-current-session", metavar="SID")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.since:
        since = parse_iso(args.since)
    elif args.days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
    else:
        since = load_state_since() or (datetime.now(timezone.utc) - timedelta(days=1))
    since_ms = int(since.timestamp() * 1000)

    records: list[dict[str, object]] = []
    for row in db_rows():
        sid = row["id"]
        if args.exclude_current_session and sid == args.exclude_current_session:
            continue
        updated_ms = int(row["updated_at_ms"] or 0)
        if updated_ms < since_ms and not (args.include_current_session and sid == args.include_current_session):
            continue
        cwd = row["cwd"] or ""
        if args.project and args.project not in cwd:
            continue
        path = Path(row["rollout_path"]).expanduser()
        if not path.exists():
            continue
        records.append(
            {
                "mtime": datetime.fromtimestamp(updated_ms / 1000, tz=timezone.utc).isoformat(),
                "project": Path(cwd).name if cwd else "",
                "cwd": cwd,
                "path": str(path),
                "lines": count_lines(path),
                "session_id": sid,
                "title": compact(row["title"] or ""),
                "first_user_message": compact(row["first_user_message"] or ""),
            }
        )

    if args.json:
        json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for record in records:
            print(
                f"{record['mtime']}\t{record['project']}\t{record['path']}\t"
                f"{record['lines']}\t{record['session_id']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
