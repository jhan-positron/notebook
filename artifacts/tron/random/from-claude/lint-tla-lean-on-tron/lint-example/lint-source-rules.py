#!/usr/bin/env python3
"""Source rules that came from corrections. One table row per rule.

Prototype for TRON, meant to live at bin/ci/lint-source-rules.py. It follows
the repository's Python style (2 spaces, 88 columns).

A rule is a regular expression plus the text an agent needs to act on a hit:
why the pattern is wrong and what to write instead. Each row also carries one
bad and one good sample line. --self-test proves that the rule fires on the
bad line and does not report the good one.

Known old hits live in a baseline file. A file may not have more hits than
its baseline count, and a full run fails when a count can be lowered. So the
old hits can only go down.

Usage:
  lint-source-rules.py                  # whole tree under --root
  lint-source-rules.py FILE...          # only these files (pre-commit, hooks)
  lint-source-rules.py --self-test
  lint-source-rules.py --print-baseline
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CPP_ROOTS = ("h", "src", "t")
CPP_SUFFIXES = (".hpp", ".h", ".cpp", ".i")


@dataclass(frozen=True)
class Rule:
  id: str
  pattern: str
  why: str
  fix: str
  bad: str  # a line the rule must report
  good: str  # a line the rule must accept
  roots: tuple[str, ...] = CPP_ROOTS
  suffixes: tuple[str, ...] = CPP_SUFFIXES


RULES = [
  # Already enforced by a grep in lefthook.yml, flake.nix and the GNUmakefile.
  # Shown here to demonstrate that an existing rule fits one row.
  Rule(
    id="no-cassert",
    pattern=r"^\s*#\s*include\s*<cassert>",
    why="<cassert> asserts vanish under NDEBUG. Tron asserts must stay active.",
    fix='Include "common/assert.hpp" and use TRON_ASSERT.',
    bad="#include <cassert>",
    good='#include "common/assert.hpp"',
  ),
  # The correction: "delete the #if 0 block you left in the diff".
  Rule(
    id="no-if-0",
    pattern=r"^\s*#\s*if\s+0\b",
    why="No build compiles a block under #if 0, so it goes stale unnoticed.",
    fix="Delete the block. Git keeps the old text. Keep live switches under a "
    "named macro or a runtime option.",
    bad="#if 0  // old path",
    good="#if TRON_HAS_AMX",
  ),
]


def applies(rule: Rule, path: str) -> bool:
  parts = Path(path).parts
  return (
    bool(parts)
    and parts[0] in rule.roots
    and path.endswith(rule.suffixes)
    and "_deps" not in parts
  )


def tree_files(root: Path) -> list[str]:
  found = []
  for top in sorted({r for rule in RULES for r in rule.roots}):
    for folder, dirs, names in os.walk(root / top):
      dirs[:] = sorted(d for d in dirs if d != "_deps")
      for name in sorted(names):
        found.append(str((Path(folder) / name).relative_to(root)))
  return found


def scan(root: Path, files: list[str]) -> dict[tuple[str, str], list[tuple[int, str]]]:
  """Returns {(rule id, path): [(line number, line text), ...]}."""
  hits: dict[tuple[str, str], list[tuple[int, str]]] = {}
  compiled = [(rule, re.compile(rule.pattern)) for rule in RULES]
  for path in files:
    rules = [(rule, rx) for rule, rx in compiled if applies(rule, path)]
    if not rules:
      continue
    try:
      text = (root / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
      continue  # a staged deletion
    for number, line in enumerate(text.splitlines(), 1):
      for rule, rx in rules:
        if rx.search(line):
          hits.setdefault((rule.id, path), []).append((number, line.strip()))
  return hits


def read_baseline(path: Path) -> dict[tuple[str, str], int]:
  baseline: dict[tuple[str, str], int] = {}
  if not path.exists():
    return baseline
  for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
      continue
    rule_id, file_path, count = line.split()
    baseline[(rule_id, file_path)] = int(count)
  return baseline


def self_test() -> int:
  failed = 0
  for rule in RULES:
    rx = re.compile(rule.pattern)
    if not rx.search(rule.bad):
      print(f"{rule.id}: the rule does not report its bad sample: {rule.bad!r}")
      failed += 1
    if rx.search(rule.good):
      print(f"{rule.id}: the rule reports its good sample: {rule.good!r}")
      failed += 1
  print(f"self-test: {len(RULES)} rules, {failed} failures")
  return 1 if failed else 0


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  parser.add_argument("files", nargs="*")
  parser.add_argument("--root", default=".")
  parser.add_argument("--baseline", default=None)
  parser.add_argument("--self-test", action="store_true")
  parser.add_argument("--print-baseline", action="store_true")
  args = parser.parse_args()
  if args.self_test:
    return self_test()

  root = Path(args.root)
  baseline_path = (
    Path(args.baseline)
    if args.baseline
    else Path(__file__).with_name("lint-source-rules.baseline")
  )
  full_run = not args.files
  hits = scan(root, tree_files(root) if full_run else args.files)
  if args.print_baseline:
    for (rule_id, path), found in sorted(hits.items()):
      print(f"{rule_id} {path} {len(found)}")
    return 0

  baseline = read_baseline(baseline_path)
  by_id = {rule.id: rule for rule in RULES}
  failed_rules: list[str] = []
  for (rule_id, path), found in sorted(hits.items()):
    allowed = baseline.get((rule_id, path), 0)
    if len(found) <= allowed:
      continue
    if rule_id not in failed_rules:
      failed_rules.append(rule_id)
    for number, text in found:
      print(f"{path}:{number}: [{rule_id}] {text}")
    if allowed:
      print(f"  ({len(found)} hits in this file; the baseline allows {allowed})")
  for rule_id in failed_rules:
    rule = by_id[rule_id]
    print(f"\nFAIL: {rule_id}\n  Why: {rule.why}\n  Fix: {rule.fix}")

  stale = []
  if full_run:  # only a full run sees every file, so only it can tighten
    for (rule_id, path), allowed in sorted(baseline.items()):
      now = len(hits.get((rule_id, path), []))
      if now < allowed:
        stale.append(f"{rule_id} {path}: baseline says {allowed}, the tree has {now}")
  if stale:
    print("\nFAIL: the baseline can be lowered")
    for line in stale:
      print(f"  {line}")
    print(f"  Fix: lower or delete these lines in {baseline_path.name}")
  return 1 if failed_rules or stale else 0


if __name__ == "__main__":
  sys.exit(main())
