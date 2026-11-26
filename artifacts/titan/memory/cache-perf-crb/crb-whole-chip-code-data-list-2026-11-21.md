---
name: crb-whole-chip-code-data-list-2026-11-21
description: "Where the code-and-data list of the 7200 MT/s whole-chip rerun and its companion explanation files live, and how to rebuild them (generators, not hand edits)"
metadata:
  node_type: memory
  type: reference
  originSessionId: cf95f96f-fe0e-4464-9ebe-3b1a78f78771
  modified: 2026-11-25T00:28:44.230Z
---

Deliverable of 2026-11-21 (user request: review the test code of the rerun described in [[crb-whole-chip-rerun-7200-2026-11-17]]):

- List: `crb/new-test-kernel/whole-chip-test-code-data-list.md` (calling order, old and new read kernel, data, analysis code, result table).
- Companions: `<file name>.md` beside each listed file (for example `go.sh.md`, `bandwidth.c.md`, `threads120.csv.md`). Code companions show the source at the left and the explanation at the right in an HTML table.
- Tool folder: `crb/tmp/agent-scratch/code-data-list-2026-11-21/` (T).

77 of the 81 companions and the list are generated. Do not edit a generated file by hand: edit the input and rebuild. The other 4 companions are edited in place.

- Code and listing companions (33): input `T/ann/<key>.overview.json` and `T/ann/<key>.cNN.json` (keys in `T/manifest.json`). Build: `python3 T/companion_tool.py build-all` (it verifies that the left column equals the source line by line). A passing build proves the left column only. After an edit of a source file, first change the annotation text of the edited lines. Then search the other companions for sentences that the edit makes false. Also check the sentences of the list that hold a count. On 2026-11-24 a new reference made the words "two session records" false. Case of 2026-11-24: one changed line of `go.sh` needed changes in 12 annotation files and 3 hand-written companions.
- Exception since 2026-11-24: `go.sh.md` is no longer the output of `companion_tool.py`. The user asked for a short line-by-line page (`/explain-bash ... generate to go.sh.md`). Its generator is `crb/tmp/agent-scratch/explain-bash-2026-11-24/make_go_sh_md.py`. The page is plain Markdown without any HTML tag (see [[md-output-plain-markdown-no-html]]): one pipe table `| Line | Source | Explanation |` with one row per source line, each `|` of the source written `\|`. The script tests the facts from other files, reads the table back itself and through pandoc (reader `gfm`), and needs pandoc. The earlier page is kept there as `go.sh.md.before-explain-bash`, and my first version with an HTML table as `go.sh.md.html-table-version`. `companion_tool.py verify go` and `verify-all` now stop with `ValueError: substring not found` at the key `go`, because the tool searches for `<table style=`. `companion_tool.py build go` or `build-all` writes the earlier HTML page again from `T/ann/go.*.json` (inputs unchanged): after a `build-all`, rerun `make_go_sh_md.py`. The tool and `manifest.json` were not changed (conflict reported to the user on 2026-11-24, no decision yet). The other 32 pages of the manifest still hold the HTML table. The new page keeps the section "Behavior a reader must know" (the list points to it in two sentences). It has no "Call sequence" and no "Functions" section, so the sentence of the list about these sections "of each companion" is not exact for `go.sh` (reported to the user, not changed). After an edit of `go.sh`, the text pieces in `rows()` and the facts in `check_facts()` of that script must be updated.
- Data companions (44): input `T/types/<type>.md` plus the data file. Build: `python3 T/data_companions.py`.
- Four companions were written directly (no generator): `FACTS.md.md`, `facts.json.md`, `baselines-and-rules.txt.md` in the rerun scratch folder, and `whole-chip-rerun-7200.html.md` in `new-test-kernel`.
- List: `python3 T/make_list.py` (reads the overviews, checks links, intro length under 15 words, and cross-checks the result table against the raw csv files).
- `T/BRIEF.md` is the briefing that the writer and reviewer agents used. Its section 7 holds facts that the run folder does not record.

Facts found during this work that are not in the run folder:

- The commands that started `go.sh` and `go2.sh` on CRB exist only in the Claude Code session record of 2026-11-17 (`~/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`, lines 309, 313, 339, 353, 365, 377).
- The local `bandwidth.c` (sha256 `f1985072...`) differs from the text of the timed build of 2026-11-13 18:12 UTC (`c1406e02...`) in comment lines only: local lines 178 to 182, above `k_read`. Proof: the edit is in the session record `~/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000 (18:32:07 UTC). Reversing it gives the sha256 `c1406e02...`. `T/make_list.py` (function `check_two_texts`) repeats this check at every build. The binary `bw_new` has the same sha256 in all three build records.
- The local `go.sh` (sha256 `d68cf6c0...`) differs from the text that ran on 2026-11-17 (`75bc50b0...`, line 1 of `local.sha`) in the message of line 20 only. The line was changed on 2026-11-24 on the user's instruction. `T/make_list.py` (function `check_two_texts_go`) repeats the proof at every build. The tests of that edit are kept in `crb/tmp/agent-scratch/go-edit-2026-11-24/`. State and the open task: [[crb-go-sh-remove-boot-id-todo]].
- The binaries `bw_old`, `bw_new` and `bwx12` are in no local folder. They were on CRB on 2026-11-17.
- `T/work/notes-not-added.txt` holds 120 notes of the checkers about facts that the companions leave out (candidates, not verified).

Render check of a companion: see [[headless-chrome-offline-render]] (pandoc `-f gfm`, then a screenshot).
