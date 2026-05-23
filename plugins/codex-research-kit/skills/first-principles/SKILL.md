---
name: first-principles
description: "Apply the kit's first-principles mode. Use when the user asks for first-principles reasoning, a constitution check, or the old /first-principles behavior."
license: MIT
---

# first-principles

Apply the global first-principles rules from `~/.codex/AGENTS.md`:

1. Start from the raw requirement and actual goal.
2. Surface vague goals, hidden assumptions, and costly detours before executing.
3. Verify changing or repo-specific claims from code, docs, or search.
4. When correcting an error, state what was missed and what check prevents it.

Do not create files just because this skill was invoked. Use it as a reasoning
checkpoint unless the user asks for edits.
