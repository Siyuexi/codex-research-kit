---
description: Index, search, recall, or save Codex memory using deterministic local session utilities.
---

# /codex-memory

Use the `codex-memory` skill.

Parse `$ARGUMENTS` as a subcommand:

- `index [--limit N] [--write]`
- `search <query>`
- `recall <session-id-prefix> [--max-messages N]`
- `save <topic> [--body TEXT]`
- `context [--query TEXT]`

Run:

```bash
python3 ~/.codex/skills/codex-memory/scripts/codex_memory.py $ARGUMENTS
```

Rules:

- Do not call a model, `codex exec`, or a sub-agent for memory indexing.
- Do not auto-summarize the current session.
- For `save`, write only factual user-approved notes.
- For `recall`, show minimal relevant excerpts unless the user asks for more.
