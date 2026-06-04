# Vibe Discuss Protocol v0

Status: consensus approved by user, Claude, and Codex on 2026-05-27.

## 1. Architecture

- Feishu group: discussion and routing bus.
- Local research-workflow workspace: durable project state.
- New agent sessions: execution boundary for survey, code, paper, experiment, and long-running work.
- Bridge daemon: deterministic transport/router and run controller; no reasoning authority.

One topic maps to one workspace and one Feishu group. Prefer separate bot/app identities for Claude and Codex.

## 2. Message Surface

Normative markers:

- `@codex` / `@claude`: route to peer agent. Parse with `(?:^|\s)@(claude|codex)\b`, case-insensitive.
- `@bridge <command>`: bridge command. Parse the command line with `(?:^|\s)@bridge\s+(.+)`, case-insensitive, single-line.
- `<consensus>...</consensus>`: candidate closure.
- `<debate>...</debate>`: unresolved disagreement.
- `<handoff>...</handoff>`: session rotation request.
- `<full-auto-done>...</full-auto-done>`: full-auto completion proposal.

`[FMRP]` headers are optional debug/verbose context, never required.

Agents should include informal `refs: [...]` in message bodies when relying on concrete artifacts. The bridge does not parse refs for authority.

## 3. Consensus

Consensus match succeeds only when both agents emit blocks since the latest user message and either:

- normalized `decision` fields are byte-equal, or
- one block contains `echoes: <prior-message-id-or-run-id>`.

Any other shape becomes a `debate` entry. The bridge never infers semantic equivalence.

Consensus produces a log entry only. It does not authorize downstream execution. Survey/code/paper work starts in a new session under the appropriate research-workflow skill.

Pending consensus reverts to discussing on new user message or after one hour without agent activity.

Block parsing is case-insensitive, multi-line, non-greedy. Fields are `key: value` lines; continuation lines append to the previous field. Decision normalization is lowercase, trim, and collapse internal whitespace. Any non-empty `echoes:` value counts as endorsement. `next-step` matching strips surrounding whitespace and then uses exact string equality.

## 4. Storage

- `.bridge/config.json`: chat/workspace/agent config.
- `.bridge/discussion.jsonl`: raw Feishu audit stream; gitignored by default.
- `.bridge/full-auto/*.json`: full-auto run state; gitignored by default.
- `log/entries/*.md`: curated research-workflow timeline; tracked.
- `log/index.md`: derived table regenerated from entries.

Payloads over 8KB are stored in gitignored cache by hash reference instead of inline raw duplication.

Bad log entries are not deleted. Add a correction/supersession entry, encoded in v0 as `type: decision`, `slug: correction-...`, `supersedes: [...]` until the research-workflow schema has a native `correction` type.

The v0 bridge config schema is `references/bridge-config-v0.schema.json`. Runtime-compatible configs use `topic_slug`, `feishu_chat_id`, `controller_user_ids`, and `bots.{claude,codex}`. `session_id` defaults to `null`; do not store placeholder strings as session ids. Codex resume command shape is `codex exec resume <session_id> <prompt>`, while first dispatch is `codex exec <prompt>`.

## 5. Shared Workspace Discipline

Both agents share one working tree by default.

- `.bridge/*`: bridge-only.
- `log/entries/*.md`: append-only; timestamp collision gets an agent suffix.
- mutable root artifacts: single writer by routing or owned decision entry.
- root commits: never silent. Edit first, ask the user, then stage/commit only after approval.
- `log/index.md`: regenerate from entries; do not merge by hand.
- `src/`: GitHub-backed submodule. Non-trivial work uses issue/branch/PR. Root pointer bump is a separate user-gated commit.
- `doc/`: Overleaf-backed submodule. One owner at a time. Root pointer bump is a separate user-gated commit.
- if unsure, remain read-only and emit `<debate>` if there is a collision.

## 6. Review Independence

Independent reviews must be done by memory-less sub-agents. Parent session orchestrates only.

Reviewers receive only the explicit brief and artifacts listed there. The brief may include a bounded, task-relevant log window. It must not include parent session context, raw Feishu transcript, desired verdict, or hidden rationale.

Preserve raw review reports. Diff/synthesis is a separate artifact.

## 7. Full-Auto Extension

Default mode remains interactive. Full-auto is opt-in and worktree-based.

Start requires user message plus explicit confirmation. Required fields: topic/workspace, one-line goal, `budget_turns`, `budget_wall_clock`, external policy, notes/constraints.

Preflight must verify:

- root is a git repo
- root working tree and index are clean
- `src/` and `doc/` submodules are clean if present
- `.bridge/` is gitignored
- no other full-auto run is active for this workspace
- root `base_ref`/`base_sha` and submodule SHAs are recorded

Allowed in v0 full-auto:

- local commits in the full-auto worktree
- local branches in `src`/`doc`
- pushing `src` feature branches and opening PRs only with explicit `allow-src-branch-push`

Not allowed in v0 full-auto:

- PR merges before final user acceptance
- Overleaf pushes before final user acceptance
- Class D high-risk actions
- bridge semantic conflict resolution

Exit conditions: matching `<full-auto-done>` blocks, budget, user kill, or hard error. Matching uses byte-equal-or-echoes `decision` plus matching `next-step`.

Final report does not count against turn budget. It records goal, exit condition, turns, wall time, file changes, decisions, debates, PRs, doc edits, reviews, and residual risks.

Final user choices:

- accept: fast-forward merge only, with clean main workspace and reachable submodule pointers
- reject: archive run report/SHA/diff/logs to `cache/full-auto/<run_id>/`, remove worktree/branch
- partial accept: commit-level cherry-pick only in v0

Non-fast-forward or conflict stops the bridge. Resolution is manual or an interactive follow-up session under shared-workspace rules.

Because PRs are not merged during full-auto, dependent code chains must be bundled into one PR or split across multiple full-auto runs with a user-gated merge between them.
