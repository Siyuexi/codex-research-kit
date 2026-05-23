---
name: codex-kit-sync
description: "Sync local Codex kit edits back to the codex-research-kit git repo and GitHub. Use when the user says 'sync my kit', 'push my .codex changes to the repo', 'send my new skill to the kit', '同步我的 ~/.codex/', or invokes the /sync-kit command. The scanner only enumerates drift; every write, commit, and push needs explicit user confirmation."
license: MIT
---

# codex-kit-sync — orchestrate ~/.codex/ ⇄ codex-research-kit sync

## What changed from v0.1 (the old `bin/sync-kit` + `/sync-kit` command)

The old design was a bash script that owned three decisions: what counts as
"tracked", what to do with new skills, what to do with deletes. Those
decisions were hard-coded — **new skills were silently ignored, deletions
were never propagated, renames couldn't be expressed at all**. The user
hit this directly when renaming `distill` → `skill-distill`: the script
saw "6 files deleted, 0 files added" instead of "6 files moved".

This skill replaces that script with:
- **A read-only scanner** (`bin/sync-kit-scan.py`) that emits drift as JSON,
  including rename candidates. Brand-new skill dirs are opt-in with
  `--include-new-skills` to avoid mirroring unrelated marketplace skills.
- **A conversation-driven workflow** where I (Codex) classify each piece
  of drift and propose the right git operation — `git mv` for renames,
  `git rm` for deletions, sanitized rsync for modifications.
- **Explicit per-action confirmation** — no batch `--apply` button.

There is no auto-apply script. The scanner is read-only; Codex performs any
write, commit, or push only after the user approves the specific batch.

---

## When to use

- The user says "sync my kit", "push to research-kit", "同步一下", or runs `/sync-kit`.
- The user mentions a specific local change ("I just renamed X, push that to the repo")
  and the change touches `~/.codex/`.
- After authoring a new skill / hook / command and wanting it published.

## When NOT to use

- The user wants to **pull** changes from the repo (the kit -> `~/.codex/`
  direction). That is plugin marketplace install/upgrade, not this skill. C-K5 below.
- The user is editing files inside the kit repo directly (e.g. cd'd into
  `~/Documents/codex-research-kit/`). They don't need this skill —
  they can just `git add . && git commit` directly.
- The user wants a one-line "is everything synced?" — run the scanner
  yourself and report totals; you don't need the full workflow.

---

## Section 1 — Constitution (C-K1 ~ C-K5)

### C-K1. Decisions in conversation, never in code

The scanner enumerates; I classify; the user approves. No path in this
skill batches multiple writes behind a single user "yes". The only
permitted execution model is: scanner output → my proposal → user
confirmation → one git operation.

**Why:** the old script's three deliberate guards ("never auto-delete",
"new skills not auto-tracked", "secret regex aborts") existed precisely
because the script could not safely make those decisions. Move the
decision into the conversation and the guards become unnecessary because
I can explain trade-offs and you can override.

**How to apply:** when running this skill, you (Codex) MUST hold every
git mutation behind an explicit user yes/no. If multiple files share a
single semantic change (e.g. all 7 files of a single skill), one batched
confirmation is OK — but the user has to see what's in the batch.

### C-K2. Rename detection takes priority over delete+add

When the scanner reports rename candidates (a `removed_in_home` file whose
sanitized content is byte-identical to a `new_in_home` file), propose
`git mv` rather than the naive `git rm` + `cp`. Preserves git blame and
log history.

**Why:** `distill` → `skill-distill` was a single semantic action (rename)
that the old script could only express as deletion + addition, losing
all the commit history on those 6+ files.

**How to apply:** Step 3 of the workflow always processes
`rename_candidates` before `removed_in_home` and `new_in_home`. Even when
the byte-identical heuristic misses (because file content drifted along
with the rename), I should still spot the naming pattern in conversation
and propose `git mv` followed by a content-update commit.

### C-K3. Every write needs explicit confirmation

`git mv`, `git rm`, `cp/rsync into repo`, `git commit`, `git push` —
each one needs the user to actually say yes or "go ahead" for **that
specific batch**. Implicit consent from earlier in the conversation does
not roll over.

**Why:** sync is one-way (`~/.codex/` -> repo -> GitHub). The repo and
GitHub mirror are infrastructure other machines pull from via Codex plugin
marketplace install/upgrade. A bad push hurts every future install.

**How to apply:**
- Show a diff or file list before every git operation, not after.
- Push is its own confirmation, separate from commit. ("Committed locally
  — push to origin/main now? [y/n]")
- If the user says "yes do everything", I MUST still pause before
  `git push` and confirm once more, because push crosses the local/remote
  boundary.

### C-K4. Secret scan is informational, not a hard abort

The scanner flags lines matching secret-shaped regexes (`gho_`, `ghp_`,
`sk-ant-`, `sk-…`, email addresses). The OLD script aborted on any hit.
This skill treats hits as **a list to review with the user**, not a
ground truth.

**Why:** the regex has a ~80% false-positive rate in practice. Example
emails in LaTeX templates (`name@example.com`, `proceedings-questions@aaai.org`)
match the email regex. A hard abort means the user can't sync at all
until they manually go strip every example email — which is busywork that
the abort was supposed to prevent, not cause.

**How to apply:**
- Every scan run, surface secret_hits to the user with the line + snippet.
- For each hit, classify it as: real secret (refuse to sync until fixed),
  example/template (safe), or boundary case (ask).
- Real secrets are the only thing that should block sync, and the block
  is per-file, not per-run.

### C-K5. Direction is fixed: ~/.codex/ -> repo -> GitHub

This skill never pulls from the repo into `~/.codex/`. If the user wants
that, route them to `codex plugin marketplace add <repo-or-clone>` or
`codex plugin marketplace upgrade` for an existing marketplace.
This skill also never modifies `~/.codex/` — the only files I touch on
the home side are read.

**Why:** bidirectional sync without a clear merge model causes silent
overwrites. The kit repo is the "publishing" side; `~/.codex/` is the
"authoring" side. Pull happens through Codex's plugin marketplace path.

**How to apply:** if the user asks me to do anything that would mutate
`~/.codex/` based on the repo, stop and tell them to use the plugin
marketplace install/upgrade flow.

---

## Section 2 — Project layout

```
~/.codex/skills/codex-kit-sync/
├── SKILL.md                                  ← you are here
├── bin/
│   └── sync-kit-scan.py                      ← read-only drift scanner
└── templates/                                ← (reserved for future use)

~/.codex/commands/sync-kit.md                ← thin slash command entry
~/.codex/.kit-repo-path                      ← single-line pointer to the kit repo

~/Documents/codex-research-kit/          ← the kit git repo (default location)
├── .agents/plugins/marketplace.json
└── plugins/codex-research-kit/
    ├── .codex-plugin/plugin.json
    ├── commands/
    ├── hooks/
    ├── skills/
    └── bin/
```

---

## Section 3 — Workflow

### Step 0 — Confirm the user's intent

If the user said "sync my kit" generically, ask one question to disambiguate
between **(a)** "scan and tell me drift" and **(b)** "scan, propose, then
actually push". The default if they used `/sync-kit` is (b) since the slash
command exists specifically to push.

Skip Step 0 if the user said something specific like "sync this rename" or
"push my new skill X" — they've already chosen (b).

### Step 1 — Run the scanner

```
python3 ~/.codex/skills/codex-kit-sync/bin/sync-kit-scan.py
```

If the user explicitly asks to publish a brand-new skill, add
`--include-new-skills` and filter the result before proposing anything.

Capture stdout JSON. The script never writes anywhere. If it exits non-zero,
read the stderr message and surface the error to the user (most common:
kit repo not found → tell them to set `KIT_REPO` or `~/.codex/.kit-repo-path`).

Parse the JSON. Top-level keys:
- `kit_repo`, `home_dir` — paths (verify they're what the user expects)
- `modified[]`, `new_in_home[]`, `removed_in_home[]`, `new_skill_dirs[]`,
  `rename_candidates[]`, `secret_hits[]`
- `totals` — count of each category

### Step 2 — Present a one-screen summary

Show the user the **totals** and a short preview of each category. Do not
dump 300 file paths into chat. Example format:

```
Drift between ~/.codex/ and the kit repo:
  modified:           2 files   (commands/distill.md, commands/sync-kit.md)
  rename candidates:  3 pairs   (skills/distill/* → skills/skill-distill/*)
  removed in home:    6 files   (rest of skills/distill/, post-rename)
  new in home:        4 files   inside tracked skills
  secret hits:       32 lines   (likely example emails in LaTeX templates)
```

Cap the previews at 3-5 items each; tell the user to ask for the full list
if they want it.

### Step 3 — Process rename candidates first (C-K2)

For each rename candidate or rename-shaped cluster (the scanner finds
byte-identical pairs; you should also visually spot near-matches like
`skills/distill/X → skills/skill-distill/X` even if content drifted):

1. **Detect the cluster**: if multiple `rename_candidates[]` entries share a
   common prefix (e.g. all `skills/distill/* → skills/skill-distill/*`),
   prefer a **directory-level** `git mv` over per-file ones — keeps history
   cleaner.

2. **Propose to the user**: "These N files look like a rename of `X → Y`.
   Run `git mv X Y` in the repo, commit it as a pure rename, then apply
   content updates in a second commit?"

3. **On confirm, do these in order — DO NOT skip the commit between mv and
   content edit (this is the AP-2 guardrail enforced by C-K2):**
   ```bash
   cd "$KIT_REPO"
   git mv skills/distill skills/skill-distill
   git status --short            # show user the staged R lines
   git commit -m "rename distill skill to skill-distill"
   ```
   **Why the commit between mv and content edit is non-negotiable**: if you
   stage `git mv` and then overwrite contents before committing, git's
   rename detection (default 50% similarity threshold) sees the entries as
   delete + add when content drifted significantly. The R lines downgrade
   to A + D, and `git log --follow` stops working at the rename. You can
   verify the rename was preserved by inspecting `git log --diff-filter=R
   --stat -1` after committing.

4. **Re-classify post-rename**: any `new_in_home[]` entries the scanner
   tagged `category: "new_skill_dir"` whose path now sits inside a
   directory that just got `git mv`'d **belong to the renamed skill, not
   to a brand-new skill dir**. Example: scanner reports
   `skills/skill-distill/bin/list-user-skills.py` as `new_skill_dir`
   because at scan time the repo had `skills/distill/`, not
   `skills/skill-distill/`. After Step 3 step 3's commit, that file is
   correctly inside a tracked skill — handle it in **Step 5**, not Step 6.

5. **Apply content diffs** in Step 4 (for files that exist on both sides
   but drifted) and Step 5 (for genuinely new files inside the renamed
   skill). Both as **separate commits** from the rename commit.

### Step 4 — Process modifications

For each `modified[]` entry:

1. **Show the user the file path and a diff.** Use the canonical sanitize
   transform on the home file before diffing:
   ```bash
   diff <(~/.codex/skills/codex-kit-sync/bin/sync-kit-scan.py sanitize "$home_path" /dev/stdout) "$repo_path"
   ```
   (Or just `diff <(python3 -c ...sanitize...) "$repo_path"` if you want
   the substitution inlined.)

2. **Group by semantic theme before committing.** `modified[]` can contain
   unrelated files (e.g. a command path-fix + a multi-file feature change
   in a skill). Split into one commit per coherent theme rather than one
   omnibus commit. For each theme:
   - Sanitize-copy the files (Step 4a below).
   - `git add` exactly those files.
   - `git commit` with a message describing **that theme only**.

3. **Sanitize-copy (Step 4a)**: use the scanner's `sanitize` subcommand —
   it's the single source of truth for the substitution and handles
   executable bits automatically:
   ```bash
   # One file at a time:
   ~/.codex/skills/codex-kit-sync/bin/sync-kit-scan.py sanitize \
       "$home_path" "$repo_path"

   # Or a batch via TSV (one "src<TAB>dst" per line):
   ~/.codex/skills/codex-kit-sync/bin/sync-kit-scan.py sanitize \
       --pairs /tmp/sync-batch.tsv
   ```
   This is the **only** correct way to copy files into the repo. Never
   `cp` raw — the destination MUST be sanitized so the repo stays portable
   across machines (the canonical transform is `$HOME` → `$HOME` literal,
   `/Users/<user>` → `$HOME`, `<user>` word-boundary → `yourname`).

### Step 5 — Process new files inside already-tracked skill dirs

For each `new_in_home[]` entry with `category: "inside_tracked_skill"`:
- These are unambiguously additions to existing skills the user already
  publishes. Propose as a single batch with the list, then sanitize+copy.
- No special handling — just `mkdir -p $(dirname dst) && sanitize < src > dst`.

### Step 6 — Process new skill directories (only when requested)

This section applies only when the scanner was run with `--include-new-skills`.
For each entry in `new_skill_dirs[]`:
1. Ask: "Brand-new skill `<name>` (N files). Add to the kit and publish?"
2. Three options:
   - **Yes**: copy the whole directory into `repo/skills/<name>/` (sanitized),
     then `git add` it.
   - **No, keep local**: skip — this skill stays in `~/.codex/` only.
   - **Defer**: ask later. Note in conversation but don't sync.

**Pre-filter the list before asking.** Normal Codex installs contain system,
curated, and marketplace skills. Those should NOT go into this kit unless the
user explicitly asks. Prefer candidates whose SKILL.md author/metadata clearly
marks them as user-authored.
- No `author:` field at all → ask the user.

### Step 7 — Process deletions

For each `removed_in_home[]` entry (after pairing with renames in Step 3):
1. Group by skill / directory. If 6 files in `skills/distill/` are
   removed and 6 corresponding files appeared in `skills/skill-distill/`,
   Step 3 already handled it; skip.
2. For genuine deletions ("I deleted this skill, drop it from the repo"):
   propose `git rm <files>`, confirm, execute.

### Step 8 — Triage secret hits

For each entry in `secret_hits[]`:
- If the file is one we're about to copy (in modified/new), present each
  hit with snippet.
- Classify per the rubric in C-K4: real secret / example / boundary.
- Real secrets → tell the user the file is held back from this sync until
  they edit it manually. The rest of the batch proceeds.

### Step 9 — Commit

Once Step 3-7 staged everything in the repo:
1. Run `git -C "$KIT_REPO" status --short` and show the user.
2. Propose a commit message based on the semantic change. Examples:
   - `rename distill skill to skill-distill (avoids /distill command collision)`
   - `add codex-kit-sync scanner`
   - `update commands/distill.md to point at renamed skill`
3. On confirm, commit (no `--no-verify`, no `-c commit.gpgsign=false`
   unless the user explicitly asks — match the existing repo's signing
   config). Append the Co-Authored-By trailer per the project's git rules.

### Step 10 — Push (separate confirmation, C-K3)

After commit succeeds, **separately** ask: "Push to origin/main?"

On confirm: `git -C "$KIT_REPO" push`. Report the commit hash and any
GitHub URL on success. If push fails (usually needs `git pull --rebase`),
do not auto-rebase — tell the user.

---

## Section 4 — Anti-patterns

### AP-1. Running the scanner and immediately listing 300 paths

The scanner gives you raw drift. Summarize before showing. The user can
ask for full lists, but the default view is totals + 3-5 examples per
bucket. Walls of text obscure the actual decisions to make.

### AP-2. Batching git mv + content edits into one commit

`git mv A B` and then `echo new-content > B` in the same commit hides the
rename from git log. Do the `git mv` as one commit (or staged change), then
the content edit as a second commit (or staged change). `git log --follow`
will track history through both.

### AP-3. Treating Orchestra-installed skills as user content

`~/.codex/skills/` contains user-authored, system, curated, and marketplace
skills. Do NOT propose syncing those to this kit by default — the kit is
curated, not a mirror of the local skills tree. Use `--include-new-skills`
only when the user asks to publish a new skill, then filter before asking.

### AP-4. Asking "push everything?" with no breakdown

Even after the user is on board with the sync, do not run `git push` until
you've shown them what's about to be pushed. `git push` is the only step
that crosses the local/remote boundary and is the hardest to undo (force-
push history rewrites are destructive). Always show `git log origin/main..HEAD --oneline`
or a similar preview right before pushing.

### AP-5. Falling back to the old `bin/sync-kit --apply`

If anything in this workflow is awkward, the temptation is to shell out to
the old script's `--apply` mode and let bash do it. Don't — the old script
doesn't know about renames, doesn't propagate deletes, and silently skips
new skills. Use git commands directly from the conversation instead. The
old script is kept around as a read-only fallback (and for muscle memory)
but its write path is deprecated.

---

## Section 5 — Failure modes and recovery

| Failure                                | Recovery                                                                         |
|----------------------------------------|----------------------------------------------------------------------------------|
| `sync-kit-scan.py` exits 64            | Kit repo not found. Help user set `$KIT_REPO` or `~/.codex/.kit-repo-path`.    |
| `git mv` fails: destination exists     | Stop. Investigate — probably the rename was already done partially.              |
| `rsync`/`cp` overwrites unrelated work | Should be rare since we copy file-by-file. If user reports drift, re-run scanner. |
| `git push` rejected (non-fast-forward) | Do NOT auto-rebase. Tell user to `git pull --rebase` then re-run sync.           |
| User aborts mid-workflow               | Repo may have staged but uncommitted changes. Show `git status` and ask what to do — `git reset` to undo, or keep staged for next session. |
| Scanner reports a secret in a file we want to sync | Classify per C-K4. If real, hold that file back; let the rest of the batch proceed. |
