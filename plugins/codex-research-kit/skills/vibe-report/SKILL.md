---
name: vibe-report
description: VRC report support and deployment skill. Use when the controller asks for a visual web report, deployed report, Feishu-readable report page, report template, or Bridge /report workflow. Codex defaults to data/backend validation and deployment; Claude defaults to HTML/front-end authoring.
license: MIT
tags: [VRC, Report, Deploy, HTML, Feishu]
---

# vibe-report

Use this skill to support and deploy VRC user-facing reports. In Bridge mode, the default role split is:

- **Claude**: author the visual HTML report and Markdown shadow.
- **Codex**: prepare data/backend checks, validate report artifacts, and deploy with `vrc report serve`.

## Codex Deploy Contract

When assigned deployment:

1. Verify the HTML path exists and is under the topic workspace unless the controller explicitly granted a different path.
2. Check that the report is a real user-facing artifact, not an empty placeholder.
3. Run `vrc report serve <workspace|.> <report.html>`.
4. Confirm the public URL and service metadata from command output.
5. Ensure credentials are sent by controller DM or by the `vrc report serve` helper; do not post passwords in the group.

If the requested path is missing, report the exact missing path and stop. Do not invent a report.

## Codex Data/Backend Contract

When assigned data support before authoring:

- Produce normalized data files under `report/assets/<slug>/` or another project-local cache path.
- Include a short data dictionary and caveats for Claude.
- Prefer deterministic scripts/parsers over ad hoc string edits when transforming structured data.
- Keep source links and file paths traceable.

## Template

Use `references/report-template.html` as the default component library when authoring is needed or when validating Claude's HTML. It distills the 03-TraceAnalyzer and 04-SmashSE report style: dark workbench theme, sticky nav, KPI/stat cards, evidence tables, finding boxes, progress bars, and responsive chart panels.

## Quality Bar

- HTML primary, Markdown shadow.
- Self-contained by default: inline CSS and JS; no React/Vue/build step.
- Use Chart.js only when it is already acceptable for the report context; otherwise use HTML tables, inline SVG, or CSS bars.
- Findings and evidence must be adjacent in the HTML.
- Do not deploy stale or unreviewed artifacts when a newer report file exists.
