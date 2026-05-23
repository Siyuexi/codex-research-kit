---
description: Generate .pseu semantic pseudocode files for source files.
---

# /code2pseu

Generate `.pseu` files that describe source code as one unified logical flow. Process the files or directories in `$ARGUMENTS`; if none are supplied, scan the current directory for source files and skip generated, test, and config files.

Each output file must use exactly:

```text
GOAL: <one-sentence purpose of the file>;
Dependencies: <comma-separated list of .pseu files, or "none">;

STEPS:
  <unified logical flow here>
```

Rules:

- Describe the program as one continuous flow from entry to exit.
- Use simple control structures with braces: `if (...) { }`, `for (...) { }`, `while (...) { }`.
- Do not list functions as API docs. Inline helper logic where it matters.
- Write only `.pseu` files and hidden `.pseu` backups; do not modify source files.
