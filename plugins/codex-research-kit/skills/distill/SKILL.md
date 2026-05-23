---
name: distill
description: "Alias for skill-distill. Use when the user says distill, asks to summarize recent interactions into possible skills, asks whether existing skills need updates, or explicitly mentions $distill."
license: MIT
---

# distill alias

This is an entry alias, not a separate protocol.

When invoked, load `~/.codex/skills/skill-distill/SKILL.md` and follow it.
Interpret any words after `$distill` as the distill action or options.

Common argument shapes:

- `$distill`: scan since the last run, write disabled draft skills, and write revision suggestions.
- `$distill --days 7`: scan a fixed recent window.
- `$distill --dry-run`: report without writing drafts or state.
- `$distill apply <id>`: apply one revision suggestion after explicit confirmation.
- `$distill status`: summarize distill state.

Never run distillation from hooks.
