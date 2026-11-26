---
name: skill-replay-harness
description: "How to test an edit to a review skill before installing it: blind replay of the skill on a frozen PR, a held-out PR and a negative control; folders, scripts and the 2026-11-23 results for tron PR 5022; version 3 of the edits was installed on 2026-11-24"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5923dad0-d660-4ecb-a1a6-4f80f4865614
  modified: 2026-11-24T18:37:23.401Z
---

Built on 2026-11-23 to answer jhan's question why the five review skills missed Isaac's fix on tron PR 5022 (see [[declined-fix-leaves-finding-open]]).

Where things are:
- `~/workspace/ai-runs/skill-replay-20261123/`: frozen copy of the five skills from before the edits (`skills-baseline/`), the edited copies (`skills-candidate-v3/` is the installed text, `skills-candidate-v3-blind/` is the same text without the worked example of PR 5022, v1 and v2 are earlier drafts), frozen PR pages (`pr5022-snapshot-20261120.md`, `pr5572-snapshot-20261123.md`), and three detached git worktrees of the shared tron repository (`tron-ddf843ad97`, `tron-pr5572-882e5322f1`, `tron-synthetic-control`).
- `~/workspace/ai-runs/skill-miss-analysis-20261123/`: `tools/apply_candidate_v3.py` (makes the edited copy from an unedited copy; `--blind` leaves the worked example out; run it once per folder, a second run stops at its first assertion), `tools/metrics.py` (scores a workflow journal), `tools/build_report.py` with `tools/report_template.html` (builds the HTML report), and `out/` (run records, analyst reports, skeptic reviews).
- The report: `~/workspace/intel-AMX/muse-glimmer/review-skill-gap-pr5022.html`, published at https://claude.ai/artifact/ERxasCGLPhF4Mnjxxg4xk2. To see the edits: `git diff --no-index skills-baseline skills-candidate-v3` in the replay folder, or section 6 of the report.

Method that worked:
1. Freeze the PR page at a date before the outside reviewer's fix, and check the frozen file for words that give the fix away.
2. Replay prompt: one skill folder, one worktree, the frozen page, no network, no other refs. The agent returns findings in a fixed schema with a `proposed_change` field.
3. Run the unedited skill first (3 runs per skill). Then run a blind variant of the edit. A variant that names the fix of the same PR proves nothing.
4. Add a held-out PR and a negative control where the fix would be wrong.
5. Have skeptic agents review the edit text (false positives, technical correctness, form) before the final replay. On 2026-11-23 they returned 62 required changes on version 1, and a final check found 10 more defects in version 2.
6. Score with a script, then read every scored sentence. The pattern `DEFINES` must be matched in upper case: "defines its own fakes" is not the remedy.

Results of 2026-11-23 (runs that propose the per-target define): PR 5022 0 of 13 before, 28 of 28 with the edits. PR 5572 (held out) 1 of 4 before, 12 of 12 with the edits. Negative control: 0 of 9 runs told the author to add the define.

Facts met on the way:
- A workflow journal (`<session>/subagents/workflows/<run>/journal.jsonl`) holds one `{"type":"result"}` line per agent with its full return value.
- The headless browser of Playwright is at `~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`. With `--no-sandbox --disable-gpu --host-resolver-rules="MAP * ~NOTFOUND" --virtual-time-budget=4000 --screenshot=<png> file://<html>` it renders a local page for a visual check. A window of 1100 x 2600 took 0.4 s on 2026-11-24. A window of 1100 x 16000 timed out twice (120 s and 300 s), so render a long page as several small pages.
- A built-in safety check refuses `rm -rf $VAR/...` in a shell command. Use literal paths, or do not remove.
- Replay agents get the memory index `MEMORY.md` in their context. Since 2026-11-23 the index line of [[declined-fix-leaves-finding-open]] names the lesson and PR 5572. A later replay on PR 5022 or PR 5572 is therefore no longer blind, unless it runs from a project folder with another memory index. Since 2026-11-24 the installed skills also hold the worked example of PR 5022, so a later replay must use `skills-baseline/` or a blind copy, not the live skills.

Install: jhan gave the go on 2026-11-24 ("yes" to installing version 3 into `~/.claude/skills` and the Codex copy). The same day I ran the script on `~/.claude/skills` and on `~/.codex/skills`. Both are identical to `skills-candidate-v3/` (`diff -r`), and `quick_validate` passes for the three changed skills (tron-code-review, cpp-coding-guide, folks-code-review; the description of folks-code-review stays at 1,022 characters). Backup from before the install: `~/workspace/ai-runs/skills-backup-20261124/` (`claude/` and `codex/`). The notebook snapshots were not updated (see [[skill-copies-claude-codex-notebook]]). The other open points of the report (same gap in draft PR 5572, one imprecise sentence in the posted reply on PR 5022, the gate case at `t/t_amx_numerics.cpp:148`) had no decision from jhan when this note was written.
