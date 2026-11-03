---
name: explain-bash
description: Use when the user asks what a bash/shell script or command does, or asks to explain one in plain English. Produces a brief plain-English explanation.
---

# Explain BASH in plain English

Explain the given bash script or command in plain English. Assume the reader does not know shell syntax.

## How to translate

- Turn each command into a plain sentence, not shell jargon.
  Example: `find . -name "foo"` → "find all the files and directories under the current folder tree whose names are `foo`".
- Fold flag meanings into the sentence.
  Example: `sort -u` → "sort the lines and drop duplicates".
- Be brief: one sentence per significant command or pipeline stage. Skip lines that need no explanation (comments, progress `echo`s, simple variable assignments).

## Structure

For a single command or one-liner: one short paragraph, no headers.

For a script:

1. **Purpose** — one or two sentences on what the whole script accomplishes.
2. **Main flow** — walk the top-level execution path in order: argument/environment handling, then each major step or primary function in the order it runs.

Do not give helper functions dedicated sections. Explain what a helper does in one clause at the point where a primary function calls it; if a helper is called from several places, explain it at its first use and refer back after that.

Mention a detail outside the main flow only when it changes behavior the reader must know, e.g. `set -e` (the script stops at the first failed command) or a destructive step like `rm -rf "$DIR"`.
