---
description: Start or operate a first-principles research-workflow project.
---

# /research

Use the `research-workflow` skill.

Interpret `$ARGUMENTS` as the research task or project operation. If the user is starting a new project, initialize the research-workflow structure. If the user is inside an existing project, route to the correct workflow and sub-skill:

- sub-topic sweep -> `research-survey`
- queued implementation work -> `research-cowork`
- checkpoint review -> `research-review`

Preserve first-principles behavior: if the goal is vague, stop and discuss; if the proposed path is costly or misdirected, surface the better alternative before executing.
