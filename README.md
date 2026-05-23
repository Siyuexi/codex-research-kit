# Codex Research Kit

Codex-native research workflow kit migrated from `claude-code-research-kit`.

## Install

Clone the repo and add it as a Codex plugin marketplace:

```bash
git clone https://github.com/Siyuexi/codex-research-kit.git
codex plugin marketplace add ./codex-research-kit
```

The plugin lives at `plugins/codex-research-kit/` and bundles skills, slash commands, and a read-only optional memory hook.

## Included Skills

- `research-workflow`: first-principles project constitution, artifact layout, log discipline, and routing.
- `research-survey`: sub-topic literature sweeps for research-workflow projects.
- `research-cowork`: Codex-native cowork: main Codex session coordinates multiple Codex sub-agents.
- `research-review`: two mutually blind Codex reviewer sub-agents plus a diff pass.
- `codex-memory`: deterministic session index/search/recall and explicit durable notes.
- `skill-distill`: manual self-distillation from past sessions into disabled draft skills and revision suggestions.
- `codex-kit-sync`: conversation-led sync from local Codex edits back to this kit.

## Memory Safety

The memory subsystem deliberately does not summarize sessions from hooks. The optional hook only performs deterministic read-only lookup; it never calls a model, never runs `codex exec`, never spawns sub-agents, and never writes session summaries.

Use `/codex-memory index --write` or `/distill` manually when you want persistent artifacts.
