#!/usr/bin/env python3
"""Every environment variable that the C++ code reads has a row in the doc.

Prototype for TRON. It turns this sentence of README.env-vars.md into a check:
"A PR that adds, renames or removes a variable ... also updates this file."

Scope of the prototype: getenv("NAME") calls with a string literal, in h/ and
src/. Calls whose argument is not a literal are listed, because the script
cannot see the name they read.

Usage: lint-env-vars-documented.py [--root TRON_CHECKOUT] [--doc README.env-vars.md]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

LITERAL = re.compile(r'\bgetenv\s*\(\s*"([A-Za-z0-9_]+)"')
OTHER = re.compile(r'\bgetenv\s*\(\s*[^"\s)]')


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  parser.add_argument("--root", default=".")
  parser.add_argument("--doc", default="README.env-vars.md")
  args = parser.parse_args()
  root = Path(args.root)
  doc = (root / args.doc).read_text(encoding="utf-8")
  documented = set(re.findall(r"`([A-Za-z0-9_]+)`", doc))

  read_at: dict[str, str] = {}  # name -> first place that reads it
  not_literal: list[str] = []
  for top in ("h", "src"):
    for folder, dirs, names in os.walk(root / top):
      dirs[:] = sorted(d for d in dirs if d != "_deps")
      for name in sorted(names):
        path = Path(folder) / name
        if path.suffix not in (".hpp", ".h", ".cpp", ".i"):
          continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
          where = f"{path.relative_to(root)}:{number}"
          for variable in LITERAL.findall(line):
            read_at.setdefault(variable, where)
          if OTHER.search(line):
            not_literal.append(where)

  missing = sorted(set(read_at) - documented)
  print(f"{len(read_at)} variable names read by getenv(\"...\") in h/ and src/")
  print(f"{len(missing)} of them have no row in {args.doc}")
  for variable in missing:
    print(f"{read_at[variable]}: [env-var-documented] {variable}")
  for where in not_literal:
    print(f"note: {where}: getenv() argument is not a literal; name not checked")
  if missing:
    print(
      "\nFAIL: env-var-documented\n"
      f"  Why: {args.doc} promises one row per variable the code reads.\n"
      f"  Fix: add a row for each name above to {args.doc}, in the section of\n"
      "       the code that reads it. Do not delete the getenv call to pass."
    )
  return 1 if missing else 0


if __name__ == "__main__":
  sys.exit(main())
