---
name: sync-kit
description: "Alias for codex-kit-sync. Use when the user says sync my kit, push local Codex kit edits to GitHub, publish a new skill, or explicitly mentions $sync-kit."
license: MIT
---

# sync-kit alias

This is an entry alias, not a separate protocol.

When invoked, load `~/.codex/skills/codex-kit-sync/SKILL.md` and follow it.
Interpret any words after `$sync-kit` as the sync intent.

The scanner is read-only. Every repo write, commit, and push still needs the
user's explicit approval unless the user has already granted that exact action
in the current exchange.
