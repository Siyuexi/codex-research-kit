#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "codex-research-kit"
PLUGIN_SRC = REPO_ROOT / "plugins" / PLUGIN_NAME
GLOBAL_AGENTS_SRC = REPO_ROOT / "global" / "AGENTS.md"


def read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_skills(codex_home: Path) -> list[Path]:
    installed: list[Path] = []
    for src in sorted((PLUGIN_SRC / "skills").iterdir()):
        if not src.is_dir():
            continue
        dst = codex_home / "skills" / src.name
        copy_tree(src, dst)
        installed.append(dst)
    return installed


def remove_legacy_command_stubs(codex_home: Path) -> list[Path]:
    commands_dir = codex_home / "commands"
    if not commands_dir.is_dir():
        return []
    removed: list[Path] = []
    for src in sorted((PLUGIN_SRC / "commands").glob("*.md")):
        dst = commands_dir / src.name
        if not dst.is_file():
            continue
        try:
            if dst.read_bytes() != src.read_bytes():
                continue
            dst.unlink()
        except OSError:
            continue
        removed.append(dst)
    return removed


def install_plugin_copy(codex_home: Path) -> Path:
    dst = codex_home / "local-plugins" / "plugins" / PLUGIN_NAME
    copy_tree(PLUGIN_SRC, dst)
    return dst


def merge_local_marketplace(codex_home: Path) -> Path:
    target = codex_home / "local-plugins" / ".agents" / "plugins" / "marketplace.json"
    data = read_json(
        target,
        {
            "name": "codex-local",
            "interface": {"displayName": "Local Codex plugins"},
            "plugins": [],
        },
    )
    data.setdefault("name", "codex-local")
    data.setdefault("interface", {"displayName": "Local Codex plugins"})
    plugins = data.setdefault("plugins", [])
    entry = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "INSTALLED_BY_DEFAULT", "authentication": "ON_USE"},
        "category": "Coding",
    }
    plugins[:] = [plugin for plugin in plugins if plugin.get("name") != PLUGIN_NAME]
    plugins.append(entry)
    write_json(target, data)
    return target


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def upsert_toml_table(text: str, table: str, entries: dict[str, object]) -> str:
    body = "\n".join(f"{key} = {toml_value(value)}" for key, value in entries.items()) + "\n"
    block = f"[{table}]\n{body}"
    pattern = re.compile(rf"(?ms)^\[{re.escape(table)}\]\n.*?(?=^\[|\Z)")
    if pattern.search(text):
        return pattern.sub(block, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def upsert_toml_keys(text: str, table: str, entries: dict[str, object]) -> str:
    pattern = re.compile(rf"(?ms)^\[{re.escape(table)}\]\n.*?(?=^\[|\Z)")
    match = pattern.search(text)
    if not match:
        return upsert_toml_table(text, table, entries)
    block = match.group(0)
    for key, value in entries.items():
        line = f"{key} = {toml_value(value)}"
        key_pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=.*$")
        if key_pattern.search(block):
            block = key_pattern.sub(line, block)
        else:
            block = block.rstrip() + "\n" + line + "\n"
    return text[: match.start()] + block + text[match.end():]


def remove_toml_keys(text: str, table: str, keys: list[str]) -> str:
    pattern = re.compile(rf"(?ms)^\[{re.escape(table)}\]\n.*?(?=^\[|\Z)")
    match = pattern.search(text)
    if not match:
        return text
    block = match.group(0)
    for key in keys:
        block = re.sub(rf"(?m)^{re.escape(key)}\s*=.*\n?", "", block)
    return text[: match.start()] + block + text[match.end():]


def merge_config(codex_home: Path) -> Path:
    target = codex_home / "config.toml"
    text = target.read_text(encoding="utf-8") if target.exists() else ""
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = upsert_toml_table(
        text,
        "marketplaces.codex-research-kit-local",
        {
            "last_updated": now,
            "source_type": "local",
            "source": str(codex_home / "local-plugins"),
        },
    )
    text = upsert_toml_keys(text, "features", {"hooks": True})
    text = remove_toml_keys(text, "features", ["codex_hooks"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def merge_agents(codex_home: Path) -> Path:
    target = codex_home / "AGENTS.md"
    block = GLOBAL_AGENTS_SRC.read_text(encoding="utf-8").strip() + "\n"
    begin = "<!-- codex-research-kit:start -->"
    end = "<!-- codex-research-kit:end -->"
    managed = f"{begin}\n{block}{end}\n"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(managed, encoding="utf-8")
        return target
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?ms){re.escape(begin)}.*?{re.escape(end)}\n?")
    if pattern.search(text):
        text = pattern.sub(managed, text)
    elif text.strip() == block.strip():
        text = managed
    elif block.strip() not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + managed
    target.write_text(text, encoding="utf-8")
    return target


def hook_entry(command: str, status: str, timeout: int) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": timeout,
                "statusMessage": status,
            }
        ]
    }


def merge_hooks(codex_home: Path, plugin_dst: Path) -> Path:
    target = codex_home / "hooks.json"
    data = read_json(target, {"hooks": {}})
    hooks = data.setdefault("hooks", {})
    hook_script = plugin_dst / "hooks" / "codex_memory_hook.py"
    refresh = f"python3 {shlex.quote(str(hook_script))} refresh-index"
    refresh_quiet = f"python3 {shlex.quote(str(hook_script))} refresh-index --quiet"
    context = f"python3 {shlex.quote(str(hook_script))} context"
    desired = {
        "SessionStart": {
            "matcher": "startup|resume",
            **hook_entry(refresh, "Refreshing Codex memory index", 10),
        },
        "UserPromptSubmit": hook_entry(context, "Loading Codex memory context", 2),
        "Stop": hook_entry(refresh_quiet, "Refreshing Codex memory index", 10),
    }
    desired_commands = {refresh, refresh_quiet, context}
    for event, entry in desired.items():
        event_entries = hooks.setdefault(event, [])
        filtered = []
        for existing in event_entries:
            commands = [
                hook.get("command")
                for hook in existing.get("hooks", [])
                if isinstance(hook, dict)
            ]
            if any(command in desired_commands for command in commands):
                continue
            filtered.append(existing)
        filtered.append(entry)
        hooks[event] = filtered
    write_json(target, data)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Codex Research Kit into CODEX_HOME.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    parser.add_argument("--no-hooks", action="store_true")
    parser.add_argument("--no-agents", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codex_home = Path(args.codex_home).expanduser()
    codex_home.mkdir(parents=True, exist_ok=True)

    plugin_dst = install_plugin_copy(codex_home)
    skills = copy_skills(codex_home)
    legacy_commands = remove_legacy_command_stubs(codex_home)
    marketplace = merge_local_marketplace(codex_home)
    config = merge_config(codex_home)
    agents = None if args.no_agents else merge_agents(codex_home)
    hooks = None if args.no_hooks else merge_hooks(codex_home, plugin_dst)

    print(f"Installed plugin: {plugin_dst}")
    print(f"Installed skills: {len(skills)}")
    if legacy_commands:
        print(f"Removed unsupported legacy command stubs: {len(legacy_commands)}")
    print(f"Updated marketplace: {marketplace}")
    print(f"Updated config: {config}")
    if agents:
        print(f"Updated global instructions: {agents}")
    if hooks:
        print(f"Updated hooks: {hooks}")
    print("Restart Codex to load newly installed skills. Custom workflows are invoked through /skills, $skill-name mentions, or natural language.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
