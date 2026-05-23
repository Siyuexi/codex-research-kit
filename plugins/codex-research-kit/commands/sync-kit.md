---
description: Sync local Codex kit edits back to the codex-research-kit repo with explicit confirmation.
---

# /sync-kit

Invoke the `codex-kit-sync` skill to compare local `~/.codex/` changes with the `codex-research-kit` repository.

Workflow:

1. Run the read-only scanner:

```bash
python3 ~/.codex/skills/codex-kit-sync/bin/sync-kit-scan.py
```

2. Summarize drift: modified, new, removed, rename candidates, and secret-shaped hits.
3. Ask before every write, commit, or push.
4. Process rename candidates before delete/add pairs.
5. Push only after a separate confirmation.

Do not use a one-shot `--apply` sync path.
