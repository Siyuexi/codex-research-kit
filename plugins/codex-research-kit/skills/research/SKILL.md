---
name: research
description: "Alias for research-workflow. Use when the user says research, starts or operates a research project, asks for the old /research behavior, or explicitly mentions $research."
license: MIT
---

# research alias

This is an entry alias, not a separate protocol.

When invoked, load `~/.codex/skills/research-workflow/SKILL.md` and follow it.
Interpret any words after `$research` as the requested research-workflow
operation.

Common argument shapes:

- `$research init <slug>`: initialize a project.
- `$research log <type> <slug> [--status todo|done]`: create a log entry.
- `$research filter [args]`: run the log filter.
- `$research check`: run the cascade check.
- `$research status`: summarize current project state.

If the request is a sub-topic sweep, route to `research-survey`. If it is queued
implementation work, route to `research-cowork`. If it is a checkpoint review,
route to `research-review`.
