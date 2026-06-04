#!/usr/bin/env python3
"""Deterministic helpers for the vibe-discuss v0 protocol."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


AGENT_MENTION_RE = re.compile(r"(?:^|\s)@(claude|codex)\b", re.IGNORECASE)
BRIDGE_COMMAND_RE = re.compile(r"(?:^|\s)@bridge\s+(.+)", re.IGNORECASE)
REFS_RE = re.compile(r"refs:\s*\[(.*?)\]", re.IGNORECASE | re.DOTALL)


def die(message: str, code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=check)


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd, check=check)


def slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return (slug or "run")[:max_len].strip("-") or "run"


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M")


def normalize_decision(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_key_values(body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            current_key = match.group(1).strip().lower()
            values[current_key] = match.group(2).strip()
        elif current_key and line.strip():
            values[current_key] += "\n" + line.strip()
    return values


def extract_blocks(text: str, tag: str) -> list[dict[str, Any]]:
    pattern = re.compile(rf"<{re.escape(tag)}\b[^>]*>(.*?)</{re.escape(tag)}>", re.IGNORECASE | re.DOTALL)
    blocks = []
    for match in pattern.finditer(text):
        body = match.group(1).strip()
        blocks.append({"tag": tag, "body": body, "fields": parse_key_values(body)})
    return blocks


def parse_message_text(text: str) -> dict[str, Any]:
    refs: list[str] = []
    for match in REFS_RE.finditer(text):
        refs.extend([item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()])
    blocks: dict[str, list[dict[str, Any]]] = {}
    for tag in ["consensus", "debate", "handoff", "full-auto-done", "full-auto-abort"]:
        found = extract_blocks(text, tag)
        if found:
            blocks[tag] = found
    bridge_command = None
    bridge_match = BRIDGE_COMMAND_RE.search(text)
    if bridge_match:
        bridge_command = bridge_match.group(1).strip()
    return {
        "mentions": sorted({m.group(1).lower() for m in AGENT_MENTION_RE.finditer(text)}),
        "bridge_command": bridge_command,
        "refs": refs,
        "blocks": blocks,
    }


def first_block(path: Path, tag: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    blocks = extract_blocks(text, tag)
    if not blocks:
        die(f"{path} does not contain <{tag}> block")
    return blocks[0]


def blocks_match(a: dict[str, Any], b: dict[str, Any]) -> tuple[bool, str]:
    a_fields = a["fields"]
    b_fields = b["fields"]
    a_decision = a_fields.get("decision")
    b_decision = b_fields.get("decision")
    if not a_decision or not b_decision:
        return False, "missing decision field"
    if normalize_decision(a_decision) == normalize_decision(b_decision):
        return True, "normalized decision fields match"
    if b_fields.get("echoes") or a_fields.get("echoes"):
        return True, "explicit echoes sentinel present"
    return False, "decision fields differ and no echoes sentinel is present"


def require_git_repo(root: Path) -> None:
    try:
        git(root, "rev-parse", "--show-toplevel")
    except subprocess.CalledProcessError:
        die(f"{root} is not a git repository")


def git_status_porcelain(root: Path) -> str:
    return git(root, "status", "--porcelain").stdout


def git_is_clean(root: Path) -> bool:
    return git_status_porcelain(root).strip() == ""


def current_ref(root: Path) -> str:
    proc = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if proc.returncode == 0:
        return proc.stdout.strip()
    return "DETACHED"


def current_sha(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").stdout.strip()


def submodule_paths(root: Path) -> list[str]:
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        return []
    proc = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"path$", check=False)
    paths: list[str] = []
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                paths.append(parts[1].strip())
    return paths


def active_full_auto_runs(root: Path) -> list[dict[str, Any]]:
    state_dir = root / ".bridge" / "full-auto"
    runs: list[dict[str, Any]] = []
    if not state_dir.exists():
        return runs
    for path in sorted(state_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            runs.append({"path": str(path), "state": "unreadable"})
            continue
        if data.get("state") in {"running", "assembling-report"}:
            data["path"] = str(path)
            runs.append(data)
    return runs


def bridge_is_ignored(root: Path) -> bool:
    proc = git(root, "check-ignore", "-q", ".bridge/config.json", check=False)
    return proc.returncode == 0


def preflight(root: Path) -> dict[str, Any]:
    root = root.resolve()
    result: dict[str, Any] = {"workspace": str(root), "ok": True, "errors": [], "submodules": []}
    try:
        require_git_repo(root)
        result["base_ref"] = current_ref(root)
        result["base_sha"] = current_sha(root)
    except SystemExit:
        result["ok"] = False
        result["errors"].append("root is not a git repository")
        return result

    status = git_status_porcelain(root)
    result["root_clean"] = status.strip() == ""
    if status.strip():
        result["ok"] = False
        result["errors"].append("root working tree or index is dirty")
        result["root_status"] = status.splitlines()

    result["bridge_ignored"] = bridge_is_ignored(root)
    if not result["bridge_ignored"]:
        result["ok"] = False
        result["errors"].append(".bridge/ is not gitignored; run vibe_discuss.py init and commit the .gitignore change first")

    active = active_full_auto_runs(root)
    result["active_full_auto_runs"] = active
    if active:
        result["ok"] = False
        result["errors"].append("an active full-auto run already exists for this workspace")

    for rel in submodule_paths(root):
        path = root / rel
        entry: dict[str, Any] = {"path": rel, "exists": path.exists()}
        if not path.exists():
            entry["clean"] = False
            entry["error"] = "missing submodule path"
            result["ok"] = False
            result["errors"].append(f"submodule missing: {rel}")
        else:
            try:
                entry["sha"] = current_sha(path)
                status = git_status_porcelain(path)
                entry["clean"] = status.strip() == ""
                if status.strip():
                    entry["status"] = status.splitlines()
                    result["ok"] = False
                    result["errors"].append(f"submodule dirty: {rel}")
            except subprocess.CalledProcessError as exc:
                entry["clean"] = False
                entry["error"] = exc.stderr.strip()
                result["ok"] = False
                result["errors"].append(f"submodule git error: {rel}")
        result["submodules"].append(entry)
    return result


def load_config(root: Path) -> dict[str, Any]:
    path = root / ".bridge" / "config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_gitignore(root: Path, line: str) -> None:
    path = root / ".gitignore"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    if line not in existing:
        existing.append(line)
        path.write_text("\n".join(existing).rstrip() + "\n", encoding="utf-8")


def command_init(args: argparse.Namespace) -> None:
    root = Path(args.workspace).resolve()
    if not root.exists():
        die(f"workspace does not exist: {root}")
    bridge = root / ".bridge"
    bridge.mkdir(exist_ok=True)
    (bridge / "full-auto").mkdir(exist_ok=True)
    if args.gitignore:
        ensure_gitignore(root, ".bridge/")
    config = load_config(root)
    topic_slug = args.topic_slug or args.project or root.name
    config.update(
        {
            "version": "v0",
            "workspace": str(root),
            "topic_slug": topic_slug,
            "feishu_chat_id": args.chat_id,
            "controller_user_ids": args.controller_user_id or [],
            "mode": "interactive",
            "active_full_auto_run_id": None,
            "bots": {
                "claude": {
                    "agent_name": "claude",
                    "mention": "@claude",
                    "feishu_app_id": args.claude_app_id,
                    "feishu_app_secret_path": args.claude_secret_path,
                    "feishu_bot_user_id": args.claude_bot_user_id,
                    "cli_binary": "claude",
                    "cli_subcommand": None,
                    "cli_resume_flag": "--resume",
                    "cli_start_argv": ["claude", "-p", "--output-format", "json", "{prompt}"],
                    "cli_resume_argv": ["claude", "-p", "--output-format", "json", "--resume", "{session_id}", "{prompt}"],
                    "session_id": None,
                    "context_limit_tokens": 1000000,
                    "rotation_threshold_pct": 0.9,
                },
                "codex": {
                    "agent_name": "codex",
                    "mention": "@codex",
                    "feishu_app_id": args.codex_app_id,
                    "feishu_app_secret_path": args.codex_secret_path,
                    "feishu_bot_user_id": args.codex_bot_user_id,
                    "cli_binary": "codex",
                    "cli_subcommand": "exec",
                    "cli_resume_flag": None,
                    "cli_start_argv": ["codex", "exec", "{prompt}"],
                    "cli_resume_argv": ["codex", "exec", "resume", "{session_id}", "{prompt}"],
                    "session_id": None,
                    "context_limit_tokens": 400000,
                    "rotation_threshold_pct": 0.9,
                },
            },
            "discussion_log_path": ".bridge/discussion.jsonl",
            "discussion_body_inline_max_bytes": 8192,
            "discussion_cache_dir": "cache/discussion-bodies/",
            "ping_pong": {
                "between_agents_requires_mention": True,
                "user_message_dispatches_to": ["claude", "codex"],
            },
            "consensus": {
                "pending_timeout_minutes": 60,
                "normalize_decision": ["lowercase", "trim", "collapse-whitespace"],
            },
            "full_auto": {
                "allowed_external_push_policies": ["default", "allow-src-branch-push"],
                "global_default_cap": 1,
            },
            "feishu_cli": {
                "binary": args.feishu_cli_binary,
                "event_subscription_command": ["event", "consume", "im.message.receive_v1", "--chat-id", "{{feishu_chat_id}}"],
                "send_message_command": ["msg", "send", "--chat-id", "{{feishu_chat_id}}"],
                "fallback_poll_seconds": 30,
            },
            "logging": {
                "bridge_log_path": ".bridge/bridge.log",
                "level": "info",
            },
        }
    )
    write_json(bridge / "config.json", config)
    print(json.dumps({"ok": True, "config": str(bridge / "config.json")}, indent=2))


def command_parse_message(args: argparse.Namespace) -> None:
    if args.text is not None:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    print(json.dumps(parse_message_text(text), indent=2, sort_keys=True))


def command_match(args: argparse.Namespace) -> None:
    a = first_block(Path(args.a), args.tag)
    b = first_block(Path(args.b), args.tag)
    matched, reason = blocks_match(a, b)
    if args.tag == "full-auto-done":
        a_next = (a["fields"].get("next-step") or "").strip()
        b_next = (b["fields"].get("next-step") or "").strip()
        if matched and a_next != b_next:
            matched = False
            reason = "next-step fields differ"
    print(json.dumps({"matched": matched, "reason": reason}, indent=2, sort_keys=True))
    raise SystemExit(0 if matched else 1)


def command_preflight(args: argparse.Namespace) -> None:
    result = preflight(Path(args.workspace))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


def command_full_auto_start(args: argparse.Namespace) -> None:
    root = Path(args.workspace).resolve()
    pf = preflight(root)
    if not pf["ok"]:
        print(json.dumps(pf, indent=2, sort_keys=True))
        raise SystemExit(1)
    run_id = args.run_id or f"{now_stamp()}_{slugify(args.goal)}"
    branch = f"full-auto/{run_id}"
    worktree = Path(args.worktree).resolve() if args.worktree else root.with_name(f"{root.name}.fa-{run_id}")
    state = {
        "run_id": run_id,
        "state": "planned" if not args.confirm else "running",
        "workspace": str(root),
        "worktree": str(worktree),
        "branch": branch,
        "goal": args.goal,
        "budget_turns": args.budget_turns,
        "budget_wall_clock": args.budget_wall_clock,
        "external_push_policy": args.external_push_policy,
        "base_ref": pf.get("base_ref"),
        "base_sha": pf.get("base_sha"),
        "submodules": pf.get("submodules", []),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat() if args.confirm else None,
        "turn_counter": 0,
    }
    if not args.confirm:
        print(json.dumps({"ok": True, "confirm_required": True, "state": state}, indent=2, sort_keys=True))
        return
    if worktree.exists():
        die(f"worktree already exists: {worktree}")
    git(root, "worktree", "add", str(worktree), "-b", branch, pf["base_sha"])
    if (worktree / ".gitmodules").exists():
        git(worktree, "submodule", "update", "--init", "--recursive")
    write_json(root / ".bridge" / "full-auto" / f"{run_id}.json", state)
    print(json.dumps({"ok": True, "run_id": run_id, "worktree": str(worktree), "branch": branch}, indent=2, sort_keys=True))


def command_hash_payload(args: argparse.Namespace) -> None:
    data = Path(args.file).read_bytes() if args.file else sys.stdin.buffer.read()
    digest = hashlib.sha256(data).hexdigest()
    out = Path(args.cache_dir) / f"{digest[:16]}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(json.dumps({"ref": str(out), "bytes": len(data), "sha256": digest}, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create .bridge config for a workspace.")
    p.add_argument("workspace")
    p.add_argument("--chat-id", required=True)
    p.add_argument("--project")
    p.add_argument("--topic-slug")
    p.add_argument("--controller-user-id", action="append", help="Feishu user/open id allowed to run @bridge commands; repeatable.")
    p.add_argument("--claude-app-id")
    p.add_argument("--claude-secret-path")
    p.add_argument("--claude-bot-user-id")
    p.add_argument("--codex-app-id")
    p.add_argument("--codex-secret-path")
    p.add_argument("--codex-bot-user-id")
    p.add_argument("--feishu-cli-binary", default="feishu-cli")
    p.add_argument("--gitignore", action="store_true", default=True)
    p.set_defaults(func=command_init)

    p = sub.add_parser("parse-message", help="Parse mentions and protocol blocks from a message.")
    p.add_argument("--text")
    p.add_argument("--file")
    p.set_defaults(func=command_parse_message)

    p = sub.add_parser("match", help="Match consensus/full-auto-done blocks.")
    p.add_argument("--tag", choices=["consensus", "full-auto-done"], default="consensus")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.set_defaults(func=command_match)

    p = sub.add_parser("preflight", help="Check whether full-auto can start.")
    p.add_argument("workspace")
    p.set_defaults(func=command_preflight)

    p = sub.add_parser("full-auto-start", help="Plan or start a full-auto worktree run.")
    p.add_argument("workspace")
    p.add_argument("--goal", required=True)
    p.add_argument("--budget-turns", required=True, type=int)
    p.add_argument("--budget-wall-clock", required=True, type=float)
    p.add_argument("--external-push-policy", choices=["default", "allow-src-branch-push"], required=True)
    p.add_argument("--run-id")
    p.add_argument("--worktree")
    p.add_argument("--confirm", action="store_true")
    p.set_defaults(func=command_full_auto_start)

    p = sub.add_parser("hash-payload", help="Store a large payload by hash reference.")
    p.add_argument("--file")
    p.add_argument("--cache-dir", required=True)
    p.set_defaults(func=command_hash_payload)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
