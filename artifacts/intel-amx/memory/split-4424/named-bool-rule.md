---
name: named-bool-rule
description: "jhan's named constexpr bool rule (2026-10-15 wording in ~/.claude/skills/cpp-coding-guide/SKILL.md): named bool only as a function, constructor or template argument; default arguments and initializers take the bare literal (precedent PR #4901 commit d0e6f816dd)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 529be9bf-943d-4be8-8266-aff7c422c30e
  modified: 2026-10-15T04:45:48.280Z
---

Rule text (jhan, 2026-10-15, now line 21 of ~/.claude/skills/cpp-coding-guide/SKILL.md): "Use a named `constexpr bool`
only where a bool is passed as an argument in a function call or constructor call or template argument. The reason is,
at call site a bare `true` or `false` does not say what it means." An earlier wording (2026-10-14) said "or is a default
argument" and did not name template arguments; jhan replaced it mid-task on 2026-10-14/15.

**Why:** a bare literal at a call site hides the parameter it binds to; next to a parameter name (a default argument,
an initializer) the literal already says what it means. PR #4901 commit d0e6f816dd applied this: the three default
arguments of exercise_page became bare literals and RECORD_ROWS_TRUE, which had no call-site use, was deleted.

**How to apply:** when checking a diff, flag (1) bare true/false as a function, constructor or template argument
(a `/*name=*/true` comment does not satisfy the rule as written; main has 454 such sites, so say so once), and
(2) a named literal bool used in a return, an initializer, an assignment, a default function or template argument, or
never used as an argument (delete it). Do not flag bare literals in returns, initializers, assignments, comparisons,
designated initializers, default arguments, Catch2 macros, or computed constexpr bools. Propose names in the PR
series' form ALL_CAPS parameter name + _TRUE/_FALSE. Related: [[pr4-split-execution]], [[no-minor-refactors]].
