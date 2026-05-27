---
name: research-review
description: "[research-workflow sub-skill] Run a checkpoint review of a research project with two mutually blind Codex reviewer sub-agents and a mechanical diff pass. Use when at least 10 new log entries have accumulated since the last review, after a major proposal pivot, or when the user asks to review a research project."
license: MIT
---

# research-review

This skill performs a checkpoint review without relying on a Claude-vs-Codex comparison. The useful property is independence, not model branding. Run memory-less reviewer sub-agents with equivalent briefs, keep them mutually blind, then compare their reports mechanically.

When a Feishu peer bridge is available through `vibe-discuss`, a checkpoint may include one Codex memory-less reviewer and one peer-requested Claude memory-less reviewer. When the bridge is unavailable, run two Codex memory-less reviewers and state that vendor diversity was unavailable.

## Dimensions

- **Soundness**: method, assumptions, metrics, baselines, and experiment interpretation.
- **Novelty**: current external state of the art, checked with live sources when available.
- **Consistency**: whether recent work still serves the current `proposal.md`.
- **Coherence**: repeated debates, stale decisions, or unresolved first-principles confusion in `log/`.

## Input Contract

Create `<project>/review/<ts>.brief.md` from `templates/review-brief.md.template`. Required fields:

- `review_ts`
- `project_root`
- `since_log_entry`
- `parent_proposal`
- `result_path`
- `survey_root_path`
- `survey_subtopic_glob`
- `log_window`
- `novelty_window_months`
- `novelty_sources`
- `output_path_reviewer_a`
- `output_path_reviewer_b`
- `output_path_diff`
- `dimensions`

If any required field is missing, stop and fix the brief. A reviewer sub-agent should not ask follow-up questions.

## Workflow

1. **Trigger check**. Use `bin/review-trigger` or inspect `review/.state` and `log/entries/`. The threshold is advisory; confirm before running a non-trivial review unless the user explicitly requested it.
2. **Write the brief**. Include only the context reviewers may see. Do not include parent session context, raw Feishu transcript, desired verdict, hidden rationale, or either reviewer output in the other reviewer's prompt. A bounded log window is allowed when the rubric needs project-history reasoning.
3. **Spawn memory-less reviewers in parallel**. Use two fresh Codex sub-agents in the same turn, or one Codex sub-agent plus a peer-requested Claude reviewer when the Feishu bridge is active. Reviewer A and Reviewer B receive equivalent prompts and write separate reports, for example `<ts>.a.md` and `<ts>.b.md`.
4. **Do not review in the main session**. The main Codex session is dispatcher and presenter. It should not form its own review opinion while the blinded reviewers are running.
5. **Generate the diff**. After both reports exist, use a third sub-agent or deterministic comparison pass with `templates/diff-generator-prompt.md.template`. The diff compares only; it does not add findings or pick a winner.
6. **Log and cascade**. Write a `review` or `review-failure` log entry, update `review/.state`, and trigger research-workflow cascade checks when findings imply proposal/result/survey changes.

## Reviewer Rules

- Read only the explicit brief and artifacts listed in that brief: normally `proposal.md`, `result.md`, root `survey.md`, subtopic surveys, and a bounded selected log window.
- Cover all requested dimensions or explicitly mark a dimension `N/A` with reason.
- Every finding needs concrete evidence: file path, log entry, survey entry, paper URL, or search trace.
- Do not mutate project artifacts. Reviewer write scope is its own report only.
- Do not read the other reviewer's report, parent session transcript, raw Feishu discussion, or any unlisted project history.

## Output

Use `templates/review-report.md.template` and set reviewer ids to `codex_a` and `codex_b`. The diff uses `templates/review-diff.md.template` and reports agreement, disagreement, consensus findings, one-sided findings, and red flags.
