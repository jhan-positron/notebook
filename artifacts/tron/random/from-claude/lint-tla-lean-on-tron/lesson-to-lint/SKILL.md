---
name: lesson-to-lint
description: Turn the correction the user just gave into a deterministic check (a type, a compiler setting, a lint rule or a test) instead of a new sentence in AGENTS.md. Use right after the user corrects agent output and says "make this a rule", "lesson to lint" or "this must not happen again".
argument-hint: "[the lesson in one sentence; default: the last correction in this conversation]"
---

# Lesson to lint

The user corrected something. Make the tools reject that mistake from now on.

Lesson: $ARGUMENTS

When the line above is empty, use the most recent correction in this conversation.

## Steps

1. State the rule in one sentence: "PATTERN is not allowed in SCOPE. Write REPLACEMENT instead." Quote the bad line and the corrected line from this conversation. If the correction was a decision for this one case and not a general rule, say so and stop.
2. Choose where the rule lives. Try the places in this order and take the first that can decide the rule from the source alone:
   1. The code makes the mistake impossible: a type, `= delete`, `[[nodiscard]]`, `static_assert`, a narrower interface.
   2. A setting of a tool the repository already runs: a `-Werror=` flag, a Ruff rule, clang-format.
   3. A row in `bin/ci/lint-source-rules.py`, when one line of text decides it.
   4. A script that compares files, when the rule spans files. The model is `bin/ci/lint-ci-pins.sh`.
   5. A test, when the rule is about behavior and not about text.
   6. One sentence in the nearest AGENTS.md, only when no check can decide the rule. Say why no check can.
3. Write the check. Its message names the file and the line, gives the reason in one sentence, and says what to write instead. The reader of the message is an agent that has not seen this conversation.
4. Prove the check. Show the output of both runs:
   - it fails on the bad line from step 1,
   - it passes on the corrected line.
5. Run the check on the whole tree. Report the count of old hits. Do not fix them in this change. Record them in the baseline, so that the count can only go down.
6. Wire the check as README.ci.md "Adding Lint Checks" says: `lefthook.yml`, the `lint-toolchain` check in `flake.nix`, and the `lint` target of the GNUmakefile. Keep the three commands the same.
7. Report: the rule sentence, the place chosen, why the stronger places did not fit, the two proof outputs, the count of old hits, and the files changed. List what the check cannot see.

## Limits

- Do not weaken or delete an existing check to make the new one pass.
- Do not add the hit that caused the correction to the baseline.
- One lesson gives one rule in one change. Leave old hits alone.
