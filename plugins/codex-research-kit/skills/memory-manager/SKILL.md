---
name: memory-manager
description: "Alias for codex-memory. Use when the user says memory-manager, asks to search or recall Codex memory, asks for the old /memory-manager behavior, or explicitly mentions $memory-manager."
license: MIT
---

# memory-manager alias

This is an entry alias, not a separate protocol.

When invoked, load `~/.codex/skills/codex-memory/SKILL.md` and follow it.
Interpret any words after `$memory-manager` as `codex-memory` arguments.

Hooks may refresh deterministic indexes, but this alias must not summarize
sessions automatically.
