# Codex Research Kit

Codex-native research workflow kit migrated from `claude-code-research-kit`.

## Install

Clone the repo and run the installer:

```bash
git clone https://github.com/Siyuexi/codex-research-kit.git
python3 codex-research-kit/bin/install.py
```

The installer writes the user-facing Codex surfaces directly into `~/.codex/`:

- skills to `~/.codex/skills/`
- the local plugin copy to `~/.codex/local-plugins/plugins/codex-research-kit/`
- global first-principles and long-horizon rules to `~/.codex/AGENTS.md`
- deterministic memory hooks to `~/.codex/hooks.json`
- hook feature and local marketplace config to `~/.codex/config.toml`

Restart Codex after installation so newly installed skills are loaded.

Codex CLI custom workflows are skills, not user-defined slash commands. The CLI slash menu is currently a built-in control surface. Use `/skills`, `$skill-name` mentions, or natural language:

- `$research` or "research ..." -> research workflow router
- `$distill` or "distill my recent sessions" -> self-distillation
- `$sync-kit` or "sync my kit" -> local kit sync
- `$research-survey`, `$research-review`, `$research-cowork` -> research sub-skills

You can also add the repository as a marketplace source:

```bash
codex plugin marketplace add ./codex-research-kit
```

## Included Skills

- `research-workflow`: first-principles project constitution, artifact layout, log discipline, and routing.
- `research-survey`: sub-topic literature sweeps for research-workflow projects.
- `research-cowork`: Codex-native cowork: main Codex session coordinates multiple Codex sub-agents.
- `research-review`: two mutually blind Codex reviewer sub-agents plus a diff pass.
- `codex-memory`: deterministic session index/search/recall and explicit durable notes.
- `skill-distill`: manual self-distillation from past sessions into disabled draft skills and revision suggestions.
- `codex-kit-sync`: conversation-led sync from local Codex edits back to this kit.
- Entry aliases: `research`, `distill`, `sync-kit`, `cowork`, `memory-manager`, `first-principles`, `code2pseu`, and the `vibe-*` compatibility aliases.

## Memory Safety

The memory subsystem deliberately does not summarize sessions from hooks. Hooks only perform deterministic index refresh and read-only context lookup; they never call a model, run `codex exec`, spawn sub-agents, or write AI summaries.

Indexes are written globally to `~/.codex/memory/session_index.md` and per current project/workdir to `~/.codex/memory/by-cwd/<project-key>/session_index.md`.

Use `$codex-memory index --write --scope both` for manual refreshes, and use `$distill` manually when you want skill distillation.
