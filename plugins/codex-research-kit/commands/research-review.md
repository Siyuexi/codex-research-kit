---
description: Run a checkpoint review with two blind Codex reviewer sub-agents and a diff pass.
---

# /research-review

Use the `research-review` skill.

Required behavior:

1. Fill the review brief from the current research-workflow project.
2. Spawn two mutually blind Codex reviewer sub-agents.
3. Keep reviewers read-only; each writes only its assigned report path.
4. Compare the two reports mechanically and present disagreements to the user.

Do not use Claude-vs-Codex framing and do not launch `codex exec` from reviewer sub-agents.
