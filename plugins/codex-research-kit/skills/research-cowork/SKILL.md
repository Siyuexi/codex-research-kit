---
name: research-cowork
description: "[research-workflow sub-skill] Execute concrete code-writing TODOs in a research project by decomposing them into atomic issues and dispatching parallel Codex sub-agents. Use when one or more `src-update` log entries are ready for implementation, especially when the work can be split by file scope. Do not use for paper reading, survey sweeps, exploratory debugging, or non-research coding."
license: MIT
---

# research-cowork

This is Codex-native cowork: the main Codex session coordinates multiple Codex sub-agents. Keep the cowork vocabulary, but remove the old extra layer where each sub-agent launched a separate external Codex agent. The only default execution graph is:

```text
main Codex session -> multiple Codex sub-agents
```

Do not nest `codex exec` inside this workflow. If the user explicitly asks for a detached CLI run, treat that as a separate manual workflow, not as research-cowork.

When `vibe-discuss` is active, Claude is a peer reached through the Feishu bridge, not a backend that Codex silently dispatches. Cross-agent review requests go through the bridge and must use memory-less reviewer sub-agents on both sides.

## Non-Negotiables

- **Atomicity**: one sub-agent owns one issue with a clear acceptance check and file scope.
- **Disjoint write sets**: parallel workers must not be assigned overlapping files unless dependency ordering is explicit.
- **No worker self-merge**: workers may edit, test, commit, and open a PR when asked, but the main Codex session owns final merge decisions.
- **Full-auto v0 limit**: inside a `vibe-discuss` full-auto worktree, workers may open feature branches/PRs only if authorized by `allow-src-branch-push`; they must not merge PRs or push Overleaf before final user acceptance.
- **Low/high review split**: worker or reviewer sub-agent checks file scope, tests, and local correctness. Main Codex checks research alignment against `proposal.md`, `result.md`, and the project log.
- **No hidden execution-mode switch**: if GitHub, tests, or a required tool is unavailable, surface it. Do not fall back to nested CLI agents.
- **No polling loops in the main session**: after spawning sub-agents, continue useful non-overlapping work. Wait only when their output is needed for the next step.
- **Research cascade**: after code lands, update source log entries and run the research-workflow cascade check for `proposal.md`, `result.md`, `survey.md`, and `doc/`.

## Workflow

1. **Select TODOs**. Read `log/entries/` for `src-update` or equivalent code-task entries with `status: todo`. Exclude vague research questions and unresolved design debates.
2. **Decompose**. Convert each selected TODO into one or more atomic issues. For each issue define: title, motivation, file scope, forbidden paths, acceptance checks, test command, dependency order, and expected research artifact impact.
3. **Prepare batch state**. Create `<project>/cache/cowork/<batch-id>/brief.md` from `templates/cowork-brief.md.template`. Use `cache/cowork/` for scratch artifacts only.
4. **Dispatch sub-agents in parallel**. Spawn one Codex sub-agent per independent issue in the same turn. Give each worker ownership of its files and explicitly state that other workers may be editing elsewhere. Do not assign the immediate blocker to a sub-agent if the main session needs it before any other progress is possible.
5. **Worker contract**. Each worker must read the project `AGENTS.md`, obey the issue file scope, run the requested checks, and return a final report with changed files, tests run, residual risks, and PR/branch info if applicable.
6. **Integrate**. Review worker reports. For passing branches/PRs, perform high-level research alignment before merging. Resolve conflicts in the main session because conflicts are cross-issue coordination.
7. **Close out**. Mark source TODO log entries as done or blocked, write a `cowork-batch` or `cowork-batch-failure` log entry, and run research-workflow cascade checks.

If running inside full-auto, remember that dependent code tasks cannot rely on an internal PR merge boundary. Bundle dependent work into one branch/PR, or split it across multiple full-auto runs with a user-gated merge between runs.

## Worker Prompt Shape

Use this shape when spawning a worker:

```text
You are a Codex worker for one atomic research-cowork issue.
You are not alone in the codebase; other workers may be editing disjoint files.
Do not revert changes you did not make. Stay inside this file scope:
<file_scope>

Issue:
<title and body>

Acceptance:
<checks>

Forbidden paths:
<paths>

Return:
- changed files
- tests run and exact outcomes
- implementation summary
- risks or blockers
- PR/branch URL if created
```

## Templates

- `templates/cowork-brief.md.template`: batch planning record.
- `templates/pr-review-checklist.md.template`: low-level and high-level review split.
- `templates/log-entry-cowork.md.template`: successful batch log entry.
- `templates/cowork-failure.md.template`: failure log entry.

Templates that used to launch external `codex exec` workers were intentionally removed. This skill is only about main-session orchestration of Codex sub-agents.
