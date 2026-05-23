---
name: codex-memory
description: "Codex-native cross-session memory utilities. Use when the user asks to index/search/recall previous Codex sessions, save durable notes, or inspect recent conversation history. Reads Codex sessions from ~/.codex/state_5.sqlite and rollout JSONL files; never runs automatic AI summarization from hooks."
license: MIT
---

# codex-memory

This skill provides a conservative two-layer memory system for Codex:

1. **Durable notes** under `~/.codex/memory/notes/`, written only when the user explicitly asks to save something.
2. **Low-level session retrieval** from Codex's local `~/.codex/state_5.sqlite` thread index and rollout JSONL files.

It intentionally does **not** summarize sessions automatically in hooks. A hook that calls an agent or `codex exec` can create a new session, whose ending can trigger another summary, and so on. This skill forbids that pattern.

## Non-Negotiables

- Do not call `codex exec`, a model API, or any sub-agent from a hook.
- Do not write summaries at `SessionStart`, `Stop`, or `UserPromptSubmit`.
- Hooks, if enabled, may only run deterministic read-only retrieval and print short context.
- Manual commands may write `~/.codex/memory/session_index.md` or note files only after the user invokes `/codex-memory`.
- Treat rollout transcripts as sensitive. Show minimal snippets unless the user asks to recall a session.

## CLI

Use the bundled script:

```bash
python3 ~/.codex/skills/codex-memory/scripts/codex_memory.py <subcommand>
```

Subcommands:

- `index [--limit N] [--write]`: list recent sessions; with `--write`, refresh `~/.codex/memory/session_index.md`.
- `search <query> [--limit N]`: search thread metadata and recent rollout text.
- `recall <session-id-prefix> [--max-messages N]`: print user/assistant messages from a specific session.
- `save <topic> [--body TEXT]`: create a durable note under `~/.codex/memory/notes/`.
- `context [--query TEXT]`: read-only short context for optional hooks.

## Workflow

1. For "what did we decide" questions, run `search` first, then `recall` only for the relevant session prefix.
2. For user-approved durable memory, run `save`. Keep notes factual and short.
3. For cross-session mining into new skills, use `skill-distill`; do not overload memory with skill drafting.
4. If a command cannot locate `state_5.sqlite`, report that Codex session metadata is unavailable instead of guessing paths.

## Hook Safety

The optional hook wrapper in this plugin only invokes `codex_memory.py context`. That command opens the SQLite DB in read-only mode and scans existing note files. It does not write files, call models, spawn agents, or create sessions.
