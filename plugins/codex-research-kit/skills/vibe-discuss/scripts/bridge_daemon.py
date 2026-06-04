#!/usr/bin/env python3
"""Minimal bridge controller skeleton for vibe-discuss.

This v0 implementation supports dry-run/manual JSONL ingestion. It records
messages under .bridge/discussion.jsonl, deduplicates by msg_id, parses protocol
markers via vibe_discuss.py helpers, and emits routing decisions. Feishu CLI
send/receive adapters can wrap this deterministic core later.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

import vibe_discuss


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def connect_seen(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("create table if not exists seen (msg_id text primary key, seen_at text not null)")
    return conn


def seen_or_mark(conn: sqlite3.Connection, msg_id: str) -> bool:
    row = conn.execute("select 1 from seen where msg_id = ?", (msg_id,)).fetchone()
    if row:
        return True
    conn.execute("insert into seen (msg_id, seen_at) values (?, ?)", (msg_id, utc_now()))
    conn.commit()
    return False


def load_jsonl(path: str | None) -> Iterable[dict[str, Any]]:
    handle = open(path, "r", encoding="utf-8") if path else sys.stdin
    with handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSONL at line {line_no}: {exc}") from exc


def route_event(event: dict[str, Any], parsed: dict[str, Any]) -> list[str]:
    sender = str(event.get("from", "")).lower()
    mentions = set(parsed.get("mentions", []))
    targets: set[str] = set()
    if sender == "user":
        targets.update(["codex", "claude"])
    for agent in ["codex", "claude"]:
        if agent in mentions:
            targets.add(agent)
    targets.discard(sender)
    return sorted(targets)


def append_discussion(root: Path, record: dict[str, Any]) -> None:
    path = root / ".bridge" / "discussion.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def dry_run(args: argparse.Namespace) -> None:
    root = Path(args.workspace).resolve()
    config = vibe_discuss.load_config(root)
    if config and Path(config.get("workspace", root)).resolve() != root:
        raise SystemExit(f"config workspace mismatch: {config.get('workspace')} != {root}")
    conn = connect_seen(root / ".bridge" / "seen.sqlite")
    for event in load_jsonl(args.events):
        msg_id = str(event.get("msg_id") or event.get("id") or "")
        if not msg_id:
            raise SystemExit("event missing msg_id")
        if seen_or_mark(conn, msg_id):
            continue
        body = str(event.get("body", ""))
        parsed = vibe_discuss.parse_message_text(body)
        targets = route_event(event, parsed)
        record = {
            "ts": event.get("ts") or utc_now(),
            "msg_id": msg_id,
            "from": event.get("from", ""),
            "body": body,
            "mentions": parsed["mentions"],
            "refs": parsed["refs"],
            "blocks": parsed["blocks"],
            "dispatched_to": targets,
            "round_id": msg_id if str(event.get("from", "")).lower() == "user" else event.get("round_id"),
        }
        append_discussion(root, record)
        print(json.dumps({"msg_id": msg_id, "targets": targets, "blocks": list(parsed["blocks"].keys())}, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("dry-run", help="Process local JSONL events and emit routing decisions.")
    p.add_argument("workspace")
    p.add_argument("--events", help="JSONL file; stdin when omitted.")
    p.set_defaults(func=dry_run)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
