---
name: plain-english-inspection-tools
description: "where the plain-english-experiment skill, the sentence/paragraph length checker, the output-measuring pipeline and the skill-wording A/B harness live (made 2026-11-20), and how to rerun them"
metadata:
  node_type: memory
  type: reference
  originSessionId: 59c0ff77-e70e-4ae6-800a-130e4fcb789d
  modified: 2026-11-20T19:31:09.066Z
---

Made on 2026-11-20 during the inspection of the plain-english skill.

Installed skill: `~/.claude/skills/plain-english-experiment/` (SKILL.md plus `scripts/check_lengths.py`). jhan asked for it as a separate skill, then asked for a Codex copy. The copy at `~/.codex/skills/plain-english-experiment/` is byte-identical (checked with `diff -rq` on 2026-11-20). Keep the two copies identical after any edit. The current `plain-english` skill and its import in `~/.claude/CLAUDE.md` are unchanged. `codex debug prompt-input "x"` prints what Codex shows its model, skill list included, without a model call.

Work folder: `~/workspace/ai-runs/plain-english-inspection-20261120/`:

- `proposed/scripts/check_lengths.py FILE [--stats] [--max-words 25] [--soft-words 20]`: flags sentences over the limit, joined or listed sentences of 21 to 25 words, paragraphs and bullets over 3 sentences, parentheses over 8 words, semicolons. Reads HTML and Markdown. It skips text inside code fences.
- `scripts/extract_chat.py OUT.jsonl` then `scripts/corpus_stats.py`: measure real chat replies (from `~/.claude/projects` transcripts) and a list of report files.
- `experiment/run_one.sh TASK ARM REP`: one test run of a skill wording in safe mode (`claude -p --safe-mode --tools "" --append-system-prompt-file ctx/ctx_ARM.md`).
- `experiment/run_real.sh PROMPT TASK ARM REP`: one run in the normal mode, where installed skills load. It unsets the HERDR_* variables so the SessionStart hook does not report the run to herdr.
- `scripts/analyze_experiment.py`, `scripts/score_boundary.py`: measure the replies. Task T4 checks that short simple sentences stay whole.
- `scripts/build_review.py`, then the skill-creator's `generate_review.py --static`: side-by-side review page at `skill-review/plain-english-experiment-review.html`.
- `proposed/SKILL.md`: the wording that the installed experiment skill carries. `SKILL.v2.md` is the first proposal that over-split.

Report: `~/workspace/random/plain-english-inspection-claude.md`. Codex's report: `plain-english-inspection-codex.md` in the same folder.

**Why:** the report recommends measuring one week of real sessions after jhan adopts a rewording. These scripts do that measurement.

**How to apply:** verify the files still exist, then rerun. Change the date constants in `corpus_stats.py` for a new period. A test run costs about 0.5 to 1.6 US dollars on Fable 5.2, so say the cost before a batch. Codex session records are under `$CODEX_HOME/sessions/YYYY/MM/DD/` (on agentsrv: `~/codex-home-claude-agentsrv`), not `~/.codex`. See [[jhan-writing-preferences]].
