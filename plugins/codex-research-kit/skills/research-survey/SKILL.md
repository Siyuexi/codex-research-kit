---
name: research-survey
description: "[research-workflow sub-skill] Scoped to research-workflow projects only — do not invoke as a standalone tool. Defines how to survey a sub-topic for a research project. Use when the task is 'investigate this sub-area' rather than 'record this one paper' — e.g., the main agent receives a sub-topic brief, or research-workflow Workflow E discovers it is facing a sub-area sweep, not a single-paper intake. Defines the input contract (so sub-agents can work without follow-up questions), the six survey constitution rules (recency, venue, version, code, content fields, objectivity), the sweep workflow, and the output format. Pairs with research-workflow Workflow E' (sub-topic surveying)."
license: MIT
---

# research-survey — Surveying a Sub-Topic for a research-workflow Project

This skill is a **sub-skill of `research-workflow`**. It does not redefine the research constitution — it inherits from research-workflow SKILL.md — and it does not handle single-paper intake (that is research-workflow Workflow E). It handles the case where the task is **"go investigate sub-area X and bring back a structured survey"**.

The skill is designed to be runnable by **isolated sub-agents** (no ability to ask the user back). It therefore enforces an explicit **input contract**: the dispatcher must provide every field the worker needs up-front. If the brief is incomplete, the worker returns a failure receipt rather than guessing.

---

## When to Use

- The main agent or user says: "调研一下 X 这个子方向 / sweep the literature on X / survey related work on X"
- research-workflow Workflow E's step 1 reveals the request is not a single paper but a sub-area
- A `survey/<slug>.brief.md` file is handed to a worker (sub-agent or remote routine)
- Inside an **auto research-workflow** run, the controller dispatches sub-topic sweeps in parallel

## When NOT to Use

- A specific paper is already named and needs recording → research-workflow **Workflow E** (single-paper intake)
- Early brainstorming with no target sub-topic yet → `brainstorming-research-ideas`
- The project lives in `~/Documents/project/00-QuickReview/` (no project constitution applies; do whatever is convenient)
- Citation / BibTeX verification during paper writing → `20-ml-paper-writing`

---

## Section 1 — Input Contract (the brief)

A sub-agent cannot call `ask the user`. To avoid mid-task guessing, every sweep starts from a **brief** that the dispatcher fills out. The brief is a markdown file under `<project>/survey/<slug>.brief.md`, generated from `templates/subtopic-brief.md.template`.

### Required fields

| Field | Meaning | Example |
|---|---|---|
| `subtopic` | One-line description of the sub-area | "Advantage normalization techniques in GRPO-style RL fine-tuning" |
| `slug` | kebab-case identifier, used in filenames | `grpo-adv-norm` |
| `parent_proposal_ref` | Relative path (or `proposal.md#section`) the worker reads to learn the main topic | `../proposal.md#section-3-method` |
| `axes_of_interest` | Comma list of dimensions the worker should compare against the parent topic | `task, method, dataset, metric` |
| `time_window_start` | ISO date, defaults to the project's creation date (NOT today). Fixed across the project's life. | `2026-05-14` (means: papers published on/after this date, looking back 5 years → `2021-05-14`) |
| `venue_whitelist_extra` | Project-specific extras beyond CCF-A (read from project AGENTS.md `accepted_venues`) | `ICLR, COLM, TMLR` |
| `target_count` | Soft cap on number of papers in the final survey (recommend 8–15; if a sub-topic needs >20, the dispatcher should split it) | `12` |
| `output_path` | Where to write the survey | `survey/grpo-adv-norm.md` |

### Optional fields

| Field | Meaning |
|---|---|
| `seed_papers` | Known-relevant papers the dispatcher already has, used as anchors for cite-chain search |
| `exclude_papers` | DBLP keys / arXiv ids to skip (already in main survey.md, or known irrelevant) |
| `recency_override` | If set, expands time window beyond 5 years (with reason, e.g., "include foundational 2017 paper X") |
| `notes_for_worker` | Free-form extra context (subtle distinctions, terminology the worker should not confuse) |

### Time window semantics (per the project decision)

- `time_window_start` is the **project's creation date**, recorded once and reused.
- The accepted publication window is `[time_window_start - 5 years, today]`.
- Rationale: a survey done in month 1 and a survey done in month 10 of the same project should agree on what "近五年" means. Rolling windows break this.
- If the worker needs to break the 5-year wall, the dispatcher must set `recency_override` in the brief. The worker does NOT decide this on its own.

### If the brief is incomplete

The worker does **not** guess. It writes a failure receipt (see `templates/failure-receipt.md.template`) listing the missing fields and stops. The dispatcher fixes the brief and re-dispatches.

---

## Section 2 — The Survey Constitution (C-S1 ~ C-S6)

These rules govern every sweep. They sit **below** the research-workflow constitution (C1–C8) and inherit from it; where this skill is silent, research-workflow applies.

### C-S1. Recency: ≥ (project-creation-date − 5 years)

Default: only papers published in the 5-year window described in Section 1.

- **Why**: surveys for active research projects need current state of the art, not historical foundations.
- **How to apply**: filter candidates by publication year against `time_window_start − 5y`. Older papers go to a `dropped_for_recency` list at the bottom of the candidates file, not into the survey.
- **Override**: only when `recency_override` is set in the brief.

### C-S2. Venue: CCF-A by default, plus project-declared extras

- **Default whitelist**: CCF-A conferences and journals across the relevant area (AI/ML: NeurIPS, ICML, AAAI, IJCAI, ACL, EMNLP, NAACL, CVPR, ICCV, ECCV, TPAMI, IJCV, JMLR, TOG, SIGGRAPH; SE: ICSE, FSE, ASE, ISSTA, OOPSLA, TSE, TOSEM; Sys: SOSP, OSDI, ASPLOS, ISCA, MICRO, HPCA, SIGCOMM, NSDI, MobiCom, FAST, EuroSys; DB: SIGMOD, VLDB, ICDE; Sec: CCS, S&P, USENIX Security, NDSS; Theory: STOC, FOCS, SODA, LICS, CAV; HCI: CHI, UIST, CSCW). When in doubt about a venue's tier, **do not silently include it** — the worker writes the candidate to the candidates file with `venue_justification: needs-review` and surfaces it in the final receipt for the dispatcher to decide.
- **Project extras**: the project's `AGENTS.md` may declare an `accepted_venues:` field naming additional venues the project considers acceptable (ICLR, COLM, TMLR are common examples). The worker reads this and merges it with the CCF-A default. The brief's `venue_whitelist_extra` overrides per-sweep.
- **Workshop papers, arXiv-only papers, technical reports**: not acceptable as primary entries. They may appear as `discovered_via` references for context but do not get rows in the survey.
- **Why**: keeps the sweep anchored to peer-reviewed venues the project lead trusts, while allowing per-project flexibility.

### C-S3. Version: publication > arXiv

- **Preferred**: the venue's published version (PDF from the publisher's site, the conference proceedings page, or the journal page).
- **Acceptable fallback**: if the publication version is paywalled and not retrievable, use the arXiv version. Record `version: arxiv-fallback` and `fallback_reason: paywalled` on the entry.
- **Not acceptable**: using arXiv when the publication version is freely available. The worker must attempt the publication URL first and record the attempt.
- **Why**: the publication version is the one of record; reviewers will compare to it.

### C-S4. Code: open-source repository required (or proof of absence)

Every survey entry must carry either:

- `code: <github-url>` — verified to exist and to correspond to the paper, OR
- `code: not-found` plus a `search_trace` showing the three search steps were performed:
  1. Paper-side: searched the paper PDF (abstract, footnotes, intro, "Code available at", appendix) for any URL
  2. Author-side: checked the first/last author's GitHub profile for a repo matching the paper title or method name
  3. Topic-side: searched GitHub for `<method-name>` and `<paper-keywords>` to find third-party reimplementations (if even a third-party repo exists, log it but mark `code: third-party-only`)

`code: not-found` without a `search_trace` is treated as missing data — the entry is rejected from the survey.

### C-S5. Content fields (per entry)

Every entry must contain these fields, factually stated:

- `what`: what the paper does (1–3 sentences, descriptive only)
- `goal`: the stated purpose / problem it tries to solve (in the paper's own framing)
- `relation_to_parent`: how this work connects to the parent project's topic, across the `axes_of_interest`
- `differences`: in what dimensions this work diverges from the parent topic (task / method / setting / data / metric — be specific)
- `salience_axes`: which of the brief's `axes_of_interest` this paper **actually touches** (this is factual labeling, not a judgment). Example: `[task, dataset]` if the paper shares the task and dataset but not the method.

### C-S6. Objectivity: no value judgments

The worker **describes facts**. The worker does **not**:

- Rank papers by importance, relevance, novelty, or "collision risk" with the parent topic
- Use evaluative language: "the most likely to overlap", "the most worth learning from", "SOTA", "seminal", "groundbreaking", "weak", "strong"
- Recommend which paper the user should read first

The downstream analyst (human or another agent) decides what is salient. The worker's job is to produce a clean, complete, factual record so that downstream judgment is well-supported.

Stating that a paper "shares dataset X with our proposal" is factual. Stating that it "is likely to be a direct competitor" is not. Keep to the first kind.

---

## Section 3 — Workflow (a sweep, end to end)

This is the worker's procedure. Each step is concrete enough that a sub-agent with no prior context can execute it given only the brief and access to `research-workflow` SKILL.md.

### Step 0 — Read brief and verify completeness

1. Read `<project>/survey/<slug>.brief.md`
2. Verify all required fields (Section 1) are present and non-empty
3. Read project `AGENTS.md` to fetch `accepted_venues`
4. If any required field missing → write failure receipt → stop

### Step 1 — Read the parent proposal

Read the `parent_proposal_ref` target. Extract:

- The parent topic in one sentence
- The specific dimensions named in `axes_of_interest` (e.g., what task, what method family, what dataset)
- Vocabulary the parent uses (to align terminology in `relation_to_parent` / `differences` later)

### Step 2 — Discovery (cast a wide net)

Goal: collect 30–50 candidates with metadata only (no PDF download yet).

Sources, in order of trust:

1. **Venue ToCs**: for each venue in the whitelist, scan the relevant year's accepted papers list for keyword matches
2. **DBLP**: author / keyword queries scoped to the venue whitelist and time window
3. **Google Scholar**: keyword search with `venue:` and year filters; useful for finding the publication version of a paper you only know from arXiv
4. **Cite-chain from seed_papers**: forward and backward citations of any `seed_papers` in the brief
5. **arXiv**: only for finding the publication-version URL of a recent paper; never as the primary source

For each candidate, record metadata in `<project>/survey/<slug>.candidates.md` (template provided):

- Title, authors, venue, year
- Stable ID (DBLP key preferred, else arXiv id, else DOI)
- `discovered_via`: which source surfaced it
- Abstract (copied verbatim)
- Provisional `venue_status`: in-whitelist / project-extra / needs-review / out-of-scope

### Step 3 — Filter candidates

Apply, in order:

1. **Venue filter** (C-S2): drop `out-of-scope`; flag `needs-review` for the dispatcher
2. **Time filter** (C-S1): drop anything outside the window
3. **Relevance filter** (abstract-level): drop anything whose abstract clearly does not touch the parent topic. Be permissive at this stage; better to read one extra PDF than to miss a relevant paper
4. **Deduplication**: a paper that appears in both arXiv form and conference form is one entry, keyed by the conference DBLP key; merge `discovered_via` lists
5. **Exclude list**: drop anything in the brief's `exclude_papers`

Aim to come out of this step with ~15–25 papers that warrant a PDF read.

### Step 4 — Fetch publication PDFs

For each surviving candidate:

1. Try the publication URL first (conference proceedings page, journal page, publisher PDF)
2. If paywalled / 403 / unavailable after a reasonable attempt → fall back to arXiv version, record `version: arxiv-fallback` and the reason
3. Save the PDF to `<project>/cache/papers/<stable-id>.pdf`
4. If both publication and arXiv fail → drop from this sweep, log in candidates file as `dropped_for_unavailable`

`cache/papers/` is the same cache that research-workflow C4 uses. PDFs landed here become available for subsequent single-paper Workflow E intake.

### Step 5 — Code repository hunt

For each paper whose PDF landed:

1. **Paper-side search**: open the PDF, search for `github.com`, `gitlab.com`, "Code available", "Implementation", footnotes on page 1, the abstract page, and the appendix. Capture the URL.
2. **Author-side search**: if not found, look up the first author and last author on GitHub (try `github.com/<lastname>`, then a GitHub user search). Scan their repos for one matching the paper title or method name.
3. **Topic-side search**: if still not found, search GitHub for `<method-name>` and 2–3 distinctive keywords from the paper. If only third-party reimplementations exist, record one and mark `code: third-party-only`.
4. **Verification**: open the candidate repo's README. Confirm it cites this paper or implements its method (don't just match on name). Record the verification.

Outcomes:

- `code: <url>` (verified official) — record `code_status: official-verified`
- `code: <url>` (third-party only) — record `code_status: third-party-only`
- `code: not-found` — record the full `search_trace` (what was tried, what was found)

### Step 6 — Read and extract

For each paper, read at minimum: abstract, intro (especially the contributions list), method overview, experiments setup, conclusion. Extract the C-S5 content fields. Stick to descriptive language (C-S6).

Cross-reference with the parent proposal vocabulary (from Step 1) so `relation_to_parent` and `differences` are anchored in the project's own terms, not the paper's.

### Step 7 — Write the survey file

Write to `<project>/survey/<slug>.md` using `templates/subtopic-survey.md.template`.

Structure:

1. **YAML frontmatter** with sweep metadata (slug, time window, venue whitelist used, brief path, worker session id if available, total papers in survey, count of `code: not-found`)
2. **Summary table** listing all papers with the essential columns (title, venue/year, code link or `not-found`, salience_axes, verified_by)
3. **Per-paper sections** with the full C-S5 fields
4. **Coverage notes** (optional): brief paragraph on which sub-axes are well covered and which are sparse. Factual, not evaluative.
5. **Dropped candidates appendix**: short list of `needs-review` venue cases and `dropped_for_unavailable` papers, so the dispatcher can decide next steps

### Step 8 — Log the sweep

Write a log entry to `<project>/log/entries/<ts>_survey-sweep_<slug>.md` using `templates/log-entry-survey-sweep.md.template`. Type is `survey-sweep` (new log type, must be added to research-workflow SKILL.md's log type vocabulary — see research-workflow Section 5).

Summary should state: N papers in survey, M with `code: not-found`, K flagged `needs-review` for venue.

### Step 9 — Final message to dispatcher

The worker's final message to the dispatcher (the main agent or routine controller) is short and structured:

- Path to `survey/<slug>.md`
- Path to `survey/<slug>.candidates.md`
- Path to the log entry
- Counts: total papers, code not-found, venue needs-review
- Any papers requiring `verified_by` validation before being merged into the project-root `survey.md` via Workflow E

The dispatcher (not the worker) decides when and how to merge sub-topic surveys into the project-root `survey.md`.

---

## Section 4 — Output Format

The detailed format lives in `templates/subtopic-survey.md.template`. Highlights:

- **YAML frontmatter** carries machine-readable sweep metadata so a downstream merge script can verify counts and constraints
- **Each paper has both a row in the summary table and a section below** with full fields — the table is for scanning, the sections are for analysis
- **Every entry has `verified_by: cache/papers/<stable-id>.pdf`** — same convention as research-workflow C4, so Workflow E can promote entries to the root `survey.md` without re-verification
- **No subjective fields anywhere** in the schema — there is no "importance score", "collision likelihood", or "recommended reading order" column

---

## Section 5 — Dispatch Mode

The same brief and worker behavior are designed for in-session Codex sub-agents.

The main agent, during a research-workflow session, hands off a sub-topic sweep:

1. Main agent drafts `<project>/survey/<slug>.brief.md` (using the template; main agent has full context to fill it well)
2. Main agent spawns a Codex sub-agent with this prompt:
   > "You are a research-survey worker. Read `~/.codex/skills/research-survey/SKILL.md` for the protocol. Your brief is at `<absolute-path>/survey/<slug>.brief.md`. Execute Section 3 end-to-end and return the Section 3 Step 9 final message."
3. Multiple sweeps in parallel → one message with multiple Codex sub-agent tool calls
4. Worker returns the structured final message; main agent reads `survey/<slug>.md` and decides on Workflow E promotions

### Sub-agent vs main agent capability differences (operational facts the dispatcher must know)

- **Sub-agent cannot call `ask the user`**. The brief must be complete; if it's not, the worker returns a failure receipt.
- **Sub-agent cannot launch its own sub-agents**. It does PDF fetch and code search serially. Don't make sweeps too large.
- **Sub-agent has fresh context**. It does not see the conversation, MEMORY.md, or any prior decisions. Everything it needs must be in the brief or reachable from disk via the brief.
- **Parallel sweeps don't share state**. Two workers on adjacent sub-topics will likely re-discover the same paper. Dedup at the dispatcher level using stable IDs after both return.

---

## Section 6 — Anti-patterns

| Anti-pattern | Symptom | Correction |
|---|---|---|
| **Abstract-only entries** | Entry exists in `survey/<slug>.md` but PDF was never fetched | Reject. PDF must be in `cache/papers/` with `verified_by` set. Apply C-S3 + research-workflow C4. |
| **Silent venue inclusion** | A workshop / non-CCF-A paper appears in the survey without justification | Reject. Apply C-S2 — either it matches `accepted_venues` or it goes to `needs-review`, not into the survey. |
| **`code: not-found` without trace** | Code field marked missing but no `search_trace` recorded | Reject. Apply C-S4 — three-step search is mandatory; the trace proves the search happened. |
| **arXiv-by-default** | Worker grabs arXiv URL without trying the publication version | Apply C-S3 — try publication first, record the attempt; arXiv is a fallback, not a default. |
| **Value judgments leaking in** | Entries use "SOTA", "seminal", "likely competitor", "weak baseline" | Strip. Apply C-S6 — describe, don't evaluate. The analyst evaluates. |
| **Rolling time window** | Sweep done in month 10 uses a different "5 years" than sweep done in month 1 of the same project | Apply Section 1 — `time_window_start` is the project's creation date, fixed for the project's life. |
| **Sub-agent guessing missing brief fields** | Worker assumed defaults instead of returning a failure receipt | Reject. Apply Section 1 — if the brief is incomplete, fail loudly, don't paper over. |
| **Mega-sweep** | A single sub-topic has 40+ papers in the survey | Split the sub-topic into 2–3 narrower briefs. Workers don't read 40 PDFs well. |
| **Re-discovering papers across parallel sweeps without dedup** | The same paper appears in two sub-topic surveys with different `what` writeups | Dedup at the dispatcher using stable IDs (DBLP > arXiv > DOI). Don't change the worker; fix the merge. |
| **Drift between modes** | A brief works in Mode A but not Mode B (or vice versa) because someone added a side-channel assumption | Keep the brief format identical. If a mode needs extra context, add it as an optional brief field, not as out-of-band knowledge. |

---

## Section 7 — Integration with research-workflow

This skill depends on changes to research-workflow SKILL.md. Those changes are:

1. **New log type**: `survey-sweep` added to Section 5's type vocabulary
2. **New workflow**: Workflow E' (Surveying a sub-topic) added to Section 3, with the entry condition "the request is a sub-area sweep, not a single-paper intake"
3. **Routing table**: Section 6 gains a row "Surveying a sub-topic → research-survey"
4. **Directory layout**: Section 2 gains the `survey/` subdirectory under each project (sibling of `cache/`, `log/`, `doc/`, `src/`). `survey/` is in git; `cache/papers/` already isn't.
5. **Workflow E reference**: Workflow E gains a one-line note: "If the user mentions a *sub-area* rather than a specific paper, route to research-survey first; Workflow E then promotes individual entries from `survey/<slug>.md` into the project-root `survey.md`."

Promotion path: when the project lead decides a sub-topic survey is ready to fold into the master related-work list, each row of `survey/<slug>.md` becomes a Workflow E call. The `verified_by` field is already there (same convention), so promotion is a copy, not a re-verification.

---

## Notes for the agent

- This skill is meant to be readable and executable by an isolated worker. Keep procedures concrete; assume no prior conversation.
- The constitution rules (C-S1 ~ C-S6) are non-negotiable for survey entries. The workflow steps (Section 3) are the default procedure; minor adaptations are fine (e.g., a different discovery order for an unusual sub-area) but the constitution must hold.
- When in doubt about a venue, mark `needs-review` and surface in the receipt. Do not silently include or exclude.
- When in doubt about objectivity, ask: "would this sentence still be true if a hostile reviewer read it?" If the sentence is a judgment that depends on the reader's priors, rephrase as a fact.
- The dispatcher (main agent or controller), not the worker, decides when sub-topic surveys are promoted into the project-root `survey.md`. The worker's job ends at Step 9.
