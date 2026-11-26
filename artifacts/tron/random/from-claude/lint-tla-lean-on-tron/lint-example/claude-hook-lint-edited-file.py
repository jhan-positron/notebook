#!/usr/bin/env python3
"""Claude Code PostToolUse hook: run the source rules on the file just edited.

Claude Code sends the tool call as JSON on stdin. Exit code 2 makes Claude
Code show this script's stderr to the agent, so the agent reads the rule's
Why and Fix lines right after its edit and corrects the file in the same turn.

The hook does nothing outside a repository that has
bin/ci/lint-source-rules.py, and nothing when anything unexpected happens.
A lint hook must never stop normal work.

Settings entry (in ~/.claude/settings.json, or the project's
.claude/settings.json):

  "hooks": {
    "PostToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [ { "type": "command", "timeout": 30,
                     "command": "python3 ~/.claude/hooks/lint-edited-file.py" } ] }
    ]
  }
"""

import json
import os
import subprocess
import sys


def main() -> int:
  try:
    event = json.load(sys.stdin)
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if not path or not os.path.isfile(path):
      return 0
    root = subprocess.run(
      ["git", "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
      capture_output=True,
      text=True,
      timeout=10,
    ).stdout.strip()
    linter = os.path.join(root, "bin", "ci", "lint-source-rules.py")
    if not root or not os.path.isfile(linter):
      return 0
    result = subprocess.run(
      [sys.executable, linter, os.path.relpath(path, root)],
      cwd=root,
      capture_output=True,
      text=True,
      timeout=20,
    )
  except Exception:
    return 0  # on any error, let the edit pass
  if result.returncode == 0:
    return 0
  sys.stderr.write(
    "Source rule broken by this edit. Fix the file now; do not add the hit "
    "to the baseline.\n" + result.stdout
  )
  return 2


if __name__ == "__main__":
  sys.exit(main())
