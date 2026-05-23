---
name: cowork
description: "Alias for research-cowork. Use when the user says cowork, asks for a Codex-native cowork batch, wants multiple Codex sub-agents on implementation tasks, or explicitly mentions $cowork."
license: MIT
---

# cowork alias

This is an entry alias, not a separate protocol.

When invoked, load `~/.codex/skills/research-cowork/SKILL.md` and follow it.
The execution graph is `main Codex session -> multiple Codex sub-agents`.
Do not launch nested `codex exec` workers.
