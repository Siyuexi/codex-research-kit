---
description: Alias for /cowork. Run Codex-native cowork with sub-agents inside a research workflow.
---

# /research-cowork

Use the `research-cowork` skill and follow `/cowork` semantics.

Required behavior:

1. Decompose work into atomic issues with disjoint file scopes.
2. Confirm the batch plan with the user when GitHub issues/PRs will be created.
3. Spawn one Codex sub-agent per independent issue.
4. Tell every worker it is not alone in the codebase and must not revert others' edits.
5. Integrate results in the main Codex session.

Do not launch nested `codex exec` workers. The graph is `main Codex session -> multiple Codex sub-agents`.
