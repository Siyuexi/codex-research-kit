#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ThreadRecord:
    id: str
    rollout_path: Path
    created_at_ms: int
    updated_at_ms: int
    cwd: str
    title: str
    first_user_message: str
    model: str
    agent_role: str


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def state_db_path() -> Path:
    return Path(os.environ.get("CODEX_STATE_DB", str(codex_home() / "state_5.sqlite"))).expanduser()


def memory_dir() -> Path:
    return Path(os.environ.get("CODEX_MEMORY_DIR", str(codex_home() / "memory"))).expanduser()


def open_ro_db() -> sqlite3.Connection:
    db = state_db_path()
    if not db.exists():
        raise SystemExit(f"Codex state DB not found: {db}")
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def fetch_threads(limit: int | None = None, include_archived: bool = False) -> list[ThreadRecord]:
    where = "" if include_archived else "WHERE archived = 0"
    sql = f"""
        SELECT id, rollout_path, created_at_ms, updated_at_ms, cwd, title,
               first_user_message, COALESCE(model, ''), COALESCE(agent_role, '')
        FROM threads
        {where}
        ORDER BY updated_at_ms DESC, id DESC
    """
    if limit:
        sql += " LIMIT ?"
        params: tuple[object, ...] = (limit,)
    else:
        params = ()
    with open_ro_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        ThreadRecord(
            id=row[0],
            rollout_path=Path(row[1]).expanduser(),
            created_at_ms=int(row[2] or 0),
            updated_at_ms=int(row[3] or 0),
            cwd=row[4] or "",
            title=row[5] or "",
            first_user_message=row[6] or "",
            model=row[7] or "",
            agent_role=row[8] or "",
        )
        for row in rows
    ]


def ts(ms: int) -> str:
    if not ms:
        return ""
    return dt.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


def oneline(text: str, max_len: int = 110) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    clean = clean.replace("|", "/")
    if len(clean) > max_len:
        return clean[: max_len - 1].rstrip() + "..."
    return clean


def index_command(args: argparse.Namespace) -> int:
    records = fetch_threads(None if args.all else args.limit, include_archived=args.archived)
    lines = [
        "# Codex Session Index",
        f"Updated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Updated | Session | CWD | Title | First user message |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        title = oneline(record.title or "(untitled)", 80)
        cwd = oneline(record.cwd, 55)
        first = oneline(record.first_user_message, 120)
        lines.append(f"| {ts(record.updated_at_ms)} | `{record.id[:12]}` | {cwd} | {title} | {first} |")
    lines.append("")
    lines.append(f"Total listed: {len(records)}")
    output = "\n".join(lines) + "\n"
    if args.write:
        target = memory_dir() / "session_index.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".md.tmp")
        tmp.write_text(output, encoding="utf-8")
        tmp.replace(target)
        print(f"Wrote {target} ({len(records)} sessions)")
    else:
        print(output, end="")
    return 0


def iter_message_text(path: Path, include_tools: bool = False):
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
                role = None
                content = None
                if obj.get("type") == "response_item" and payload.get("type") == "message":
                    role = payload.get("role")
                    content = payload.get("content")
                elif obj.get("type") in {"user_message", "assistant_message"}:
                    role = "user" if obj.get("type") == "user_message" else "assistant"
                    content = obj.get("message") or obj.get("content")
                elif include_tools and obj.get("type") == "response_item" and payload.get("type") in {"function_call", "function_call_output"}:
                    role = payload.get("type")
                    content = payload.get("arguments") or payload.get("output")
                if role not in {"user", "assistant", "function_call", "function_call_output"}:
                    continue
                text = extract_text(content)
                if text:
                    yield obj.get("timestamp", ""), role, text
    except OSError:
        return


def extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            for key in ("text", "input_text", "output_text"):
                value = block.get(key)
                if isinstance(value, str):
                    parts.append(value)
                    break
        return "\n".join(parts)
    if isinstance(content, dict):
        for key in ("text", "message", "content"):
            value = content.get(key)
            if isinstance(value, str):
                return value
    return ""


def find_thread(prefix: str) -> ThreadRecord:
    matches = [record for record in fetch_threads(None, include_archived=True) if record.id.startswith(prefix)]
    if not matches:
        raise SystemExit(f"No Codex session matches prefix: {prefix}")
    if len(matches) > 1:
        shown = ", ".join(record.id[:12] for record in matches[:8])
        raise SystemExit(f"Session prefix is ambiguous: {prefix}. Matches: {shown}")
    return matches[0]


def search_command(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    if not query:
        raise SystemExit("Usage: codex_memory.py search <query>")
    needle = query.lower()
    results: list[tuple[ThreadRecord, str, str]] = []
    for record in fetch_threads(args.scan_limit, include_archived=args.archived):
        haystack = "\n".join([record.title, record.cwd, record.first_user_message]).lower()
        if needle in haystack:
            results.append((record, "metadata", snippet(record.first_user_message or record.title, needle)))
            if len(results) >= args.limit:
                break
            continue
        for _, role, text in iter_message_text(record.rollout_path):
            if needle in text.lower():
                results.append((record, role, snippet(text, needle)))
                break
        if len(results) >= args.limit:
            break
    if not results:
        print(f"No matches for: {query}")
        return 0
    for record, role, preview in results:
        print(f"### `{record.id[:12]}` {ts(record.updated_at_ms)} {oneline(record.title or record.cwd, 90)}")
        print(f"- cwd: {record.cwd}")
        print(f"- match: {role}: {preview}")
        print()
    return 0


def snippet(text: str, needle_lower: str, width: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    pos = compact.lower().find(needle_lower)
    if pos < 0:
        return oneline(compact, width)
    start = max(0, pos - width // 3)
    end = min(len(compact), start + width)
    prefix = "..." if start else ""
    suffix = "..." if end < len(compact) else ""
    return prefix + compact[start:end].replace("|", "/") + suffix


def recall_command(args: argparse.Namespace) -> int:
    record = find_thread(args.session)
    print(f"# Recall `{record.id}`")
    print(f"- updated: {ts(record.updated_at_ms)}")
    print(f"- cwd: {record.cwd}")
    print(f"- title: {record.title or '(untitled)'}")
    print()
    count = 0
    for timestamp, role, text in iter_message_text(record.rollout_path, include_tools=args.include_tools):
        if role not in {"user", "assistant"} and not args.include_tools:
            continue
        print(f"## {role} {timestamp[:16].replace('T', ' ')}")
        print(textwrap.shorten(re.sub(r"\s+", " ", text).strip(), width=args.width, placeholder="..."))
        print()
        count += 1
        if args.max_messages and count >= args.max_messages:
            break
    if count == 0:
        print("(No user/assistant messages found in rollout.)")
    return 0


def save_command(args: argparse.Namespace) -> int:
    topic = " ".join(args.topic).strip()
    if not topic:
        raise SystemExit("Usage: codex_memory.py save <topic> [--body TEXT]")
    body = args.body
    if body is None and not sys.stdin.isatty():
        body = sys.stdin.read().strip()
    if not body:
        body = topic
    notes = memory_dir() / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:80] or "note"
    target = notes / f"{dt.date.today().isoformat()}-{slug}.md"
    i = 2
    while target.exists():
        target = notes / f"{dt.date.today().isoformat()}-{slug}-{i}.md"
        i += 1
    target.write_text(f"# {topic}\n\nSaved: {dt.datetime.now().isoformat(timespec='seconds')}\n\n{body.strip()}\n", encoding="utf-8")
    print(f"Wrote {target}")
    return 0


def context_command(args: argparse.Namespace) -> int:
    query = args.query or extract_prompt_from_stdin()
    words = keywords(query)
    if not words:
        return 0
    note_hits = search_notes(words, limit=3)
    session_hits = search_session_metadata(words, limit=3)
    if not note_hits and not session_hits:
        return 0
    print("Codex memory context (deterministic, read-only):")
    for path, line in note_hits:
        print(f"- note {path.name}: {line}")
    for record in session_hits:
        print(f"- session {record.id[:12]} {ts(record.updated_at_ms)}: {oneline(record.title or record.first_user_message, 120)}")
    return 0


def extract_prompt_from_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    raw = sys.stdin.read()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:2000]
    for key in ("prompt", "message", "userPrompt", "input"):
        value = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(value, str):
            return value
    return raw[:2000]


def keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]{3,}", text.lower())
    stop = {"the", "and", "for", "with", "this", "that", "please", "codex", "agent"}
    result: list[str] = []
    for token in tokens:
        if token in stop or token in result:
            continue
        result.append(token)
    return result[:8]


def search_notes(words: list[str], limit: int) -> list[tuple[Path, str]]:
    notes = memory_dir() / "notes"
    if not notes.exists():
        return []
    hits: list[tuple[Path, str]] = []
    for path in sorted(notes.glob("*.md"), reverse=True):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lower = text.lower()
        if not any(word in lower for word in words):
            continue
        line = next((oneline(line, 140) for line in text.splitlines() if any(word in line.lower() for word in words)), oneline(text, 140))
        hits.append((path, line))
        if len(hits) >= limit:
            break
    return hits


def search_session_metadata(words: list[str], limit: int) -> list[ThreadRecord]:
    try:
        records = fetch_threads(50)
    except SystemExit:
        return []
    hits: list[ThreadRecord] = []
    for record in records:
        haystack = "\n".join([record.title, record.cwd, record.first_user_message]).lower()
        if any(word in haystack for word in words):
            hits.append(record)
        if len(hits) >= limit:
            break
    return hits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex memory utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--all", action="store_true")
    p.add_argument("--archived", action="store_true")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=index_command)

    p = sub.add_parser("search")
    p.add_argument("query", nargs="+")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--scan-limit", type=int, default=200)
    p.add_argument("--archived", action="store_true")
    p.set_defaults(func=search_command)

    p = sub.add_parser("recall")
    p.add_argument("session")
    p.add_argument("--max-messages", type=int, default=40)
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--include-tools", action="store_true")
    p.set_defaults(func=recall_command)

    p = sub.add_parser("save")
    p.add_argument("topic", nargs="+")
    p.add_argument("--body")
    p.set_defaults(func=save_command)

    p = sub.add_parser("context")
    p.add_argument("--query")
    p.set_defaults(func=context_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
