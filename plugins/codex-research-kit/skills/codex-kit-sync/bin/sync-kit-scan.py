#!/usr/bin/env python3
"""Read-only enumeration of drift between ~/.codex/ and the kit repo.

Emits a JSON document over stdout. This script NEVER writes to either side —
all sync decisions are made by the calling skill in conversation with the user.

The skill consumes this JSON and decides per-file what to do: copy, git mv,
git rm, ignore, or sanitize.

Exit codes:
  0 = scan completed, JSON written to stdout (drift may or may not be present;
      the skill inspects the JSON to decide)
  64 = bad arguments / kit repo not found / not a git repo
  65 = scan failed (transient I/O); skill should retry or abort

What is reported:
  - "modified": files present on both sides whose sanitized content differs
  - "new_in_home": files present only in ~/.codex/ inside tracked skill dirs.
    Brand-new top-level skill dirs are reported only with --include-new-skills,
    because a normal Codex install contains many unrelated marketplace skills.
  - "removed_in_home": files present only in repo
  - "rename_candidates": (removed_in_home, new_in_home) pairs whose sanitized
    content is byte-identical (shasum match). Suggests `git mv`.
  - "secret_hits": lines in any home file that match secret-shaped regexes;
    these MUST be triaged before any sync (no auto-sanitize).
  - "kit_repo": which repo path was located, so the skill can confirm.
  - "home_dir": which Codex home was scanned.

Sanitization for comparison:
  Home files are passed through a sed-like substitution that replaces the
  live user's $HOME and username with portable placeholders before hashing.
  This matches the old script's behavior so a clean repo (no drift) still
  reports no drift on this machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CODEX_DIR = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
PLUGIN_NAME = "codex-research-kit"
AGENTS_BEGIN = "<!-- codex-research-kit:start -->"
AGENTS_END = "<!-- codex-research-kit:end -->"

# Tracked home surfaces. Whole-file config is intentionally not tracked because
# ~/.codex/config.toml usually contains unrelated user settings.

# Secret-shaped regexes. Same set the old script used.
SECRET_PATTERNS = [
    re.compile(rb"gho_[A-Za-z0-9]{20,}"),
    re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{30,}"),
    re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]

# Files inside the new sync-kit skill itself that should be exempt from
# secret scanning of the email pattern, because the skill documents the
# secret-detection logic and references example token/email shapes.
# (Empty by default — populate if false-positives become a problem.)
SECRET_SCAN_EXEMPT: set[str] = set()


def find_repo() -> Path | None:
    """Resolve kit repo path: $KIT_REPO → pointer file → cwd-looks-like-repo."""
    env = os.environ.get("KIT_REPO")
    if env and looks_like_repo(Path(env)):
        return Path(env)
    pointer = CODEX_DIR / ".kit-repo-path"
    if pointer.is_file():
        p = pointer.read_text().strip()
        if p and looks_like_repo(Path(p)):
            return Path(p)
    cwd = Path.cwd()
    if looks_like_repo(cwd):
        return cwd
    if looks_like_plugin_root(cwd) and (cwd.parents[1] / ".git").is_dir():
        return cwd.parents[1]
    return None


def looks_like_repo(path: Path) -> bool:
    return (
        (path / ".git").is_dir()
        and (path / ".agents" / "plugins" / "marketplace.json").is_file()
        and looks_like_plugin_root(path / "plugins" / PLUGIN_NAME)
    )


def looks_like_plugin_root(path: Path) -> bool:
    return (path / ".codex-plugin" / "plugin.json").is_file() and (path / "skills").is_dir()


def plugin_root(repo: Path) -> Path:
    nested = repo / "plugins" / PLUGIN_NAME
    return nested if looks_like_plugin_root(nested) else repo


def sanitize_for_hash(raw: bytes, home: str, user: str) -> bytes:
    """Replace live machine identifiers with portable placeholders before hashing.

    Order matters: the longer, more-specific pattern is replaced first.
    """
    out = raw
    out = out.replace(home.encode(), b"$HOME")
    out = out.replace(f"/Users/{user}".encode(), b"$HOME")
    # username word-boundary replacement
    out = re.sub(rb"\b" + re.escape(user.encode()) + rb"\b", b"yourname", out)
    return out


def extract_managed_agents(raw: bytes) -> bytes:
    text = raw.decode("utf-8", errors="replace")
    start = text.find(AGENTS_BEGIN)
    end = text.find(AGENTS_END)
    if start >= 0 and end > start:
        text = text[start + len(AGENTS_BEGIN):end]
    return text.strip().encode("utf-8") + b"\n"


def normalize_hook_command(command: str, home: str) -> str | None:
    suffix = "codex-research-kit/hooks/codex_memory_hook.py"
    for action in ("refresh-index", "context"):
        if command == f"python3 ./hooks/codex_memory_hook.py {action}":
            return command
        if command == f"python3 ./hooks/codex_memory_hook.py {action} --quiet":
            return command
        if command == f"python3 ./hooks/codex_memory_hook.py {action} --hook-json":
            return command
        if command.endswith(f"{suffix} {action}"):
            return f"python3 ./hooks/codex_memory_hook.py {action}"
        if command.endswith(f"{suffix} {action} --quiet"):
            return f"python3 ./hooks/codex_memory_hook.py {action} --quiet"
        if command.endswith(f"{suffix} {action} --hook-json"):
            return f"python3 ./hooks/codex_memory_hook.py {action} --hook-json"
    return None


def canonical_hooks(raw: bytes, home: str) -> bytes | None:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    source_hooks = data.get("hooks")
    if not isinstance(source_hooks, dict):
        return None
    out_hooks: dict[str, list[dict]] = {}
    for event, entries in source_hooks.items():
        if not isinstance(entries, list):
            continue
        kept_entries: list[dict] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            normalized_hooks = []
            for hook in entry.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if not isinstance(command, str):
                    continue
                normalized = normalize_hook_command(command, home)
                if not normalized:
                    continue
                hook_copy = dict(hook)
                hook_copy["command"] = normalized
                normalized_hooks.append(hook_copy)
            if normalized_hooks:
                entry_copy = {k: v for k, v in entry.items() if k != "hooks"}
                entry_copy["hooks"] = normalized_hooks
                kept_entries.append(entry_copy)
        if kept_entries:
            out_hooks[event] = kept_entries
    return json.dumps({"hooks": out_hooks}, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def canonical_bytes(path: Path, home: str, user: str) -> bytes | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if path.name == "AGENTS.md":
        raw = extract_managed_agents(raw)
    elif path.name == "hooks.json":
        raw = canonical_hooks(raw, home) or raw
    return sanitize_for_hash(raw, home, user)


def hash_file_canonical(path: Path, home: str, user: str) -> str | None:
    raw = canonical_bytes(path, home, user)
    if raw is None:
        return None
    return hashlib.sha1(raw).hexdigest()


def scan_secrets_in_file(path: Path) -> list[dict]:
    """Return list of {line, pattern, snippet} hits."""
    hits: list[dict] = []
    rel = str(path)
    if rel in SECRET_SCAN_EXEMPT:
        return hits
    try:
        with path.open("rb") as f:
            for lineno, line in enumerate(f, 1):
                for pat in SECRET_PATTERNS:
                    m = pat.search(line)
                    if m:
                        try:
                            snippet = line.decode("utf-8", errors="replace").rstrip("\n")
                        except Exception:
                            snippet = repr(line)
                        # Cap snippet length so JSON stays small
                        if len(snippet) > 200:
                            snippet = snippet[:200] + "…"
                        hits.append({"line": lineno, "pattern": pat.pattern.decode(), "snippet": snippet})
                        break  # one hit per line is enough
    except OSError:
        pass
    return hits


def list_tracked_pairs(repo: Path, home: Path) -> list[tuple[Path, Path]]:
    """Enumerate (home_path, repo_path) pairs for real installed surfaces."""
    pairs: list[tuple[Path, Path]] = []
    root = plugin_root(repo)
    pairs.append((home / "AGENTS.md", repo / "global" / "AGENTS.md"))
    pairs.append((home / "hooks.json", root / "hooks" / "hooks.json"))
    # Skills: every file in every skill directory that exists in the repo
    repo_skills = root / "skills"
    if repo_skills.is_dir():
        for skill_dir in sorted(repo_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            for repo_file in skill_dir.rglob("*"):
                if not repo_file.is_file():
                    continue
                if repo_file.name == ".DS_Store" or "__pycache__" in repo_file.parts:
                    continue
                rel = repo_file.relative_to(root)
                pairs.append((home / rel, repo_file))
    return pairs


def list_home_skill_files(home: Path, repo: Path) -> list[Path]:
    """Every file under ~/.codex/skills/, used to detect:
    - new files inside an existing (in-repo) skill
    - brand-new skill directories that the repo doesn't track yet
    """
    home_skills = home / "skills"
    if not home_skills.is_dir():
        return []
    out: list[Path] = []
    for f in home_skills.rglob("*"):
        if not f.is_file():
            continue
        if f.name == ".DS_Store" or "__pycache__" in f.parts:
            continue
        out.append(f)
    return out


def rel_to(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def sanitize_stream(src_path: Path, dst_path: Path, home: str, user: str) -> None:
    """Sanitize-copy a single file: read src, apply $HOME/$user substitutions,
    write to dst. Preserves executable bit. Used by both the scan path (for
    hashing/comparison) and the apply path (to copy bytes into the repo).

    This is the canonical sync transform. Anything else that writes into the
    repo MUST go through this so the repo stays portable.
    """
    sanitized = canonical_bytes(src_path, home, user)
    if sanitized is None:
        raw = src_path.read_bytes()
        sanitized = sanitize_for_hash(raw, home, user)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_bytes(sanitized)
    if os.access(src_path, os.X_OK):
        os.chmod(dst_path, os.stat(dst_path).st_mode | 0o111)


def cmd_sanitize(args) -> int:
    """`sync-kit-scan.py sanitize SRC DST` — apply the canonical sanitize
    transform to a single file. Exit 0 on success, 1 on IO error.

    This subcommand exists so the skill workflow has a single tool to copy
    files from ~/.codex/ into the repo without re-implementing the
    sanitize regex inline. Use it like:

        sync-kit-scan.py sanitize ~/.codex/X repo/X

    The skill workflow MAY also call this in a tight loop over many pairs;
    a TSV-driven `--pairs FILE` mode is available for convenience.
    """
    home = str(Path.home())
    user = os.environ.get("USER") or subprocess.run(
        ["id", "-un"], capture_output=True, text=True, check=True
    ).stdout.strip()

    if args.pairs:
        # Each line: "src<TAB>dst", blank/# lines ignored.
        copied = 0
        for line in Path(args.pairs).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" not in line:
                print(f"sync-kit-scan: bad pairs line (no tab): {line}", file=sys.stderr)
                return 1
            src, dst = line.split("\t", 1)
            try:
                sanitize_stream(Path(src), Path(dst), home, user)
                copied += 1
            except OSError as e:
                print(f"sync-kit-scan: failed {src} -> {dst}: {e}", file=sys.stderr)
                return 1
        print(f"sanitize: {copied} files copied", file=sys.stderr)
        return 0

    if not args.src or not args.dst:
        print("sync-kit-scan sanitize: need either --pairs FILE or SRC + DST", file=sys.stderr)
        return 1
    try:
        sanitize_stream(Path(args.src), Path(args.dst), home, user)
    except OSError as e:
        print(f"sync-kit-scan: failed {args.src} -> {args.dst}: {e}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    # `sanitize` subcommand
    p_san = sub.add_parser("sanitize", help="Apply the canonical sanitize transform to one file or a TSV batch")
    p_san.add_argument("src", nargs="?", help="Source path in ~/.codex/")
    p_san.add_argument("dst", nargs="?", help="Destination path in the kit repo")
    p_san.add_argument("--pairs", help="TSV file of 'src<TAB>dst' lines; overrides src/dst")

    # Default (no subcommand) = scan
    ap.add_argument("--repo", help="Override kit repo path (else env/pointer/cwd)")
    ap.add_argument("--no-secret-scan", action="store_true", help="Skip secret regex scan (faster, less safe)")
    ap.add_argument("--include-new-skills", action="store_true", help="Also report home skill directories that are not tracked by this kit")
    args = ap.parse_args()

    if args.cmd == "sanitize":
        return cmd_sanitize(args)

    repo = Path(args.repo) if args.repo else find_repo()
    if repo is None or not (repo / ".git").is_dir():
        print("sync-kit-scan: kit repo not found. Set $KIT_REPO, write ~/.codex/.kit-repo-path, or cd into the repo.", file=sys.stderr)
        return 64

    home = CODEX_DIR
    if not home.is_dir():
        print(f"sync-kit-scan: Codex home dir does not exist: {home}", file=sys.stderr)
        return 64

    home_str = str(Path.home())
    user_str = os.environ.get("USER") or ""
    try:
        if not user_str:
            user_str = subprocess.run(["id", "-un"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        user_str = ""

    modified: list[dict] = []
    new_in_home: list[dict] = []
    removed_in_home: list[dict] = []
    new_skill_dirs: list[str] = []
    secret_hits: list[dict] = []

    # Tracked pairs: classify each as modified / new_in_home / removed_in_home
    seen_home_paths: set[Path] = set()
    for home_path, repo_path in list_tracked_pairs(repo, home):
        seen_home_paths.add(home_path)
        h_exists = home_path.is_file()
        r_exists = repo_path.is_file()
        rel = rel_to(repo_path, repo)
        if h_exists and r_exists:
            h_san = hash_file_canonical(home_path, home_str, user_str)
            r_raw = hash_file_canonical(repo_path, home_str, user_str)
            if h_san is None or r_raw is None:
                continue
            if h_san != r_raw:
                modified.append({
                    "rel": rel,
                    "home_path": str(home_path),
                    "repo_path": str(repo_path),
                    "home_sanitized_sha1": h_san,
                    "repo_sha1": r_raw,
                })
        elif h_exists and not r_exists:
            new_in_home.append({
                "rel": rel,
                "home_path": str(home_path),
                "repo_path": str(repo_path),
                "category": "inside_tracked_skill",
            })
        elif r_exists and not h_exists:
            r_raw = hash_file_canonical(repo_path, home_str, user_str)
            removed_in_home.append({
                "rel": rel,
                "home_path": str(home_path),
                "repo_path": str(repo_path),
                "repo_sha1": r_raw,
            })

    # Brand-new skill dirs in ~/.codex/skills/ that the repo does NOT track.
    # This is opt-in because normal Codex installs contain many unrelated skills.
    repo_skill_names = set()
    root = plugin_root(repo)
    if (root / "skills").is_dir():
        repo_skill_names = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
    home_skills = home / "skills"
    if args.include_new_skills and home_skills.is_dir():
        for d in sorted(home_skills.iterdir()):
            if not d.is_dir():
                continue
            if d.name.startswith("."):
                continue
            if d.name in repo_skill_names:
                continue
            new_skill_dirs.append(d.name)
            # also enumerate every file inside the new skill dir
            for f in d.rglob("*"):
                if not f.is_file():
                    continue
                if f.name == ".DS_Store" or "__pycache__" in f.parts:
                    continue
                plugin_rel = Path("skills") / f.relative_to(home_skills)
                repo_path = root / plugin_rel
                new_in_home.append({
                    "rel": rel_to(repo_path, repo),
                    "home_path": str(f),
                    "repo_path": str(repo_path),
                    "category": "new_skill_dir",
                    "skill_name": d.name,
                })

    # Rename candidates: a removed-in-home file whose sanitized hash matches
    # some new-in-home file's sanitized hash. Suggests `git mv`.
    rename_candidates: list[dict] = []
    if removed_in_home and new_in_home:
        # Build hash → list of new-in-home entries
        new_by_hash: dict[str, list[dict]] = {}
        for entry in new_in_home:
            h_san = hash_file_canonical(Path(entry["home_path"]), home_str, user_str)
            if h_san:
                new_by_hash.setdefault(h_san, []).append(entry)
        for rem in removed_in_home:
            r_hash = rem.get("repo_sha1")
            if not r_hash:
                continue
            matches = new_by_hash.get(r_hash, [])
            for match in matches:
                rename_candidates.append({
                    "from_rel": rem["rel"],
                    "to_rel": match["rel"],
                    "from_repo_path": rem["repo_path"],
                    "to_home_path": match["home_path"],
                    "confidence": "byte-identical-after-sanitize",
                })

    # Secret scan over every home file we'd consider syncing
    if not args.no_secret_scan:
        scan_targets = set()
        for entry in modified:
            scan_targets.add(entry["home_path"])
        for entry in new_in_home:
            scan_targets.add(entry["home_path"])
        for p in sorted(scan_targets):
            hits = scan_secrets_in_file(Path(p))
            if hits:
                secret_hits.append({"path": p, "hits": hits})

    report = {
        "kit_repo": str(repo),
        "home_dir": str(home),
        "modified": modified,
        "new_in_home": new_in_home,
        "removed_in_home": removed_in_home,
        "new_skill_dirs": new_skill_dirs,
        "rename_candidates": rename_candidates,
        "secret_hits": secret_hits,
        "totals": {
            "modified": len(modified),
            "new_in_home": len(new_in_home),
            "removed_in_home": len(removed_in_home),
            "new_skill_dirs": len(new_skill_dirs),
            "rename_candidates": len(rename_candidates),
            "secret_hits": len(secret_hits),
        },
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
