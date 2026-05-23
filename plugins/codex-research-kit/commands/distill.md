---
description: Manually mine recent Codex sessions for disabled draft skills and revision suggestions.
---

# /distill

Invoke the `skill-distill` skill and pass through `$ARGUMENTS`.

Common forms:

- `/distill`
- `/distill --days 14`
- `/distill --dry-run`
- `/distill status`
- `/distill promote <slug>`
- `/distill revisions`
- `/distill apply <id>`

Rules:

- This command is manual only. Do not run it from hooks.
- Generated skills stay disabled until the user promotes them.
- Revision suggestions are never applied without explicit confirmation.
- Session discovery uses Codex's `~/.codex/state_5.sqlite`, not `~/.codex/projects`.
