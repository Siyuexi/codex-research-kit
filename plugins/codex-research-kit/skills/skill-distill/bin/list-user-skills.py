#!/usr/bin/env python3
"""List user-authored skills, optionally annotated with usage counts.

Usage:
  list-user-skills.py [--with-usage SESSIONS_JSON] [--top N] [--json]

A "user-authored skill" is any `~/.codex/skills/*/SKILL.md` whose frontmatter
includes `author: lee.vasquez` (the convention used by this user for skills
they wrote themselves; vs `Orchestra Research`, `Anthropic`, etc. for vendor
skills).

With `--with-usage <sessions.json>` (the JSON output of `list-sessions.py`),
counts how many sessions reference each skill by name. This is a
cheap proxy for "how often is this skill actually exercised" — used to
prioritize which skills to audit in the revision workflow.

Output records (TSV by default, one per line):
  <kind>\t<name>\t<path>\t<usage_count>

kind is "skill". usage_count is "-" if --with-usage was not provided.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / ".codex" / "skills"

USER_AUTHOR_MARKERS = {"lee.vasquez"}  # extend if the user adopts more handles


def parse_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def list_user_skills() -> list[dict]:
    out = []
    if not SKILLS_DIR.exists():
        return out
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        sm = skill_dir / "SKILL.md"
        if not sm.is_file():
            continue
        fm = parse_frontmatter(sm)
        if not fm:
            continue
        author = fm.get("author", "")
        if author not in USER_AUTHOR_MARKERS:
            continue
        out.append(
            {
                "kind": "skill",
                "name": fm.get("name", skill_dir.name),
                "path": str(sm),
                "description": fm.get("description", "").strip('"'),
            }
        )
    return out


def count_usage(records: list[dict], sessions: list[dict]) -> None:
    """Annotate each record with usage_count: how many session jsonls
    mention the skill name. Cheap substring match — false positives
    on common words are possible, but for slug-style names ("research-workflow",
    "distill", "code2pseu") collisions are rare in practice.
    """
    for r in records:
        r["usage_count"] = 0
    if not sessions:
        return
    # Build name list once
    names = [(r, r["name"]) for r in records]
    for s in sessions:
        try:
            text = Path(s["path"]).read_text(errors="ignore")
        except OSError:
            continue
        for r, name in names:
            if name in text:
                r["usage_count"] += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--with-usage",
        metavar="SESSIONS_JSON",
        help="Path to JSON output from list-sessions.py; annotate records with usage_count",
    )
    ap.add_argument("--top", type=int, help="Only emit top N by usage_count (requires --with-usage)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    records = list_user_skills()

    if args.with_usage:
        try:
            with open(args.with_usage) as f:
                sessions = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"failed to read sessions JSON: {e}", file=sys.stderr)
            return 1
        count_usage(records, sessions)
        records.sort(key=lambda r: (-r.get("usage_count", 0), r["name"]))
        if args.top:
            records = records[: args.top]
    else:
        for r in records:
            r["usage_count"] = None

    if args.json:
        json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for r in records:
            uc = r.get("usage_count")
            uc_str = "-" if uc is None else str(uc)
            print(f"{r['kind']}\t{r['name']}\t{r['path']}\t{uc_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
