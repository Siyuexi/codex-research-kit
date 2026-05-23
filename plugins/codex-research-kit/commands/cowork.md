---
description: Run a Codex-native cowork batch: main Codex session coordinates multiple Codex sub-agents.
---

# /cowork

Use the `research-cowork` skill.

Interpret `$ARGUMENTS` as either:

- a research-workflow project code TODO queue to execute, or
- an explicit list of atomic implementation tasks.

Required behavior:

1. Decompose work into atomic issues with disjoint file scopes.
2. Confirm the batch plan with the user when GitHub issues/PRs will be created.
3. Spawn one Codex sub-agent per independent issue.
4. Tell every worker it is not alone in the codebase and must not revert others' edits.
5. Integrate results in the main Codex session.

Do not launch nested `codex exec` workers. The graph is `main Codex session -> multiple Codex sub-agents`.
