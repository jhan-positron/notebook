---
name: crb-go-sh-remove-boot-id-todo
description: "Boot-id check of go.sh and go2.sh: removed on 2026-11-24 in the code repo ai-proj (not committed, in review), still present in the scratch tree. Also the state of go.sh after the message edit of 2026-11-24, the rules that follow from it, and what a change of go.sh must update"
metadata:
  node_type: memory
  type: project
  originSessionId: cf95f96f-fe0e-4464-9ebe-3b1a78f78771
  modified: 2026-11-25T00:08:44.402Z
---

State of 2026-11-24. Folders: `crb/tmp/agent-scratch/w120-7200-2026-11-17/` (S, run folder), `crb/tmp/agent-scratch/code-data-list-2026-11-21/` (T, tools of the list), `crb/tmp/agent-scratch/go-edit-2026-11-24/` (E, tests of the edit of 2026-11-24).

Words: launch = the start of the rerun on CRB on 2026-11-17. Marker file = `/tmp/positron-perf.RUNNING` on CRB. Jeremy = another user of CRB, who runs measurements in reserved time windows. Decision (h) = one item of section 2 of FACTS.md.

**Update of 2026-11-24, later the same day:** the user said "your memory has a record to remove checking boot-id, let's do it" and named the code repo `~/workspace/ai-proj/arm-crb/code` as the place for changes. Done there, not committed, waiting for a review by another agent: the fixed boot id and its check are removed from `go.sh` and from `go2.sh` (first my reading that the request covers `go2.sh`; the user confirmed it on 2026-11-24: "yes, remove boot-id check, it is not needed"), and `manual-run/run.sh` is unchanged (its `sed` now deletes no line). Details: [[crb-hw-record-2026-11-24]]. The scratch files in S are NOT changed: everything below still describes the scratch tree, where the check still stands. Do not copy the scratch `go.sh` over the repo file.

**Task as it was before that update:** remove the fixed boot-id check from `go.sh`. Not started in the scratch tree. User on 2026-11-22 (local date): "we will need to update go.sh to remove boot-id at some point, not now". The user named `go.sh` only. `go2.sh` holds the same check (lines 12 and 21). Ask the user before `go2.sh` is changed.

**Why:** the fixed boot id stops `go.sh` in every boot except the one of 2026-11-17. The user's view: reading `12 Configured Memory Speed: 7200 MT/s` and MemTotal of at least 395000000 kB at each start is enough. Background in [[crb-whole-chip-rerun-7200-2026-11-17]].

**How to apply:** change `go.sh` or `go2.sh` only when the user asks. When a session changes these scripts, remind the user that the boot-id task is open. Until it is done, a run starts through the user's saved command `crb/new-test-kernel/manual-run/run.sh`. That command writes and starts the copy `go-direct.sh`.

**Open point of mine (the user did not ask for it):** this work did not copy the edit of 2026-11-24 to CRB. A copy to CRB needs a login, and a login needs the user's authorization.

Done on 2026-11-24, on the user's instruction: line 20 of the local `go.sh` reads `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"`. Before: `... && fail "RUNNING file present"`. No other line changed (48 lines).

Facts after that edit:

- Two texts. The local file has the sha256 `d68cf6c0...`. The text that ran on 2026-11-17 has `75bc50b0...`. That value is the `go.sh` entry of `S/local.sha`. It is also the sha256 of the text in line 295 of the session record `405492c8-...jsonl`. With the old line 20 put back, the local file has `75bc50b0...` again. `E/go.sh.as-run-2026-11-17` is a byte copy of the older text.
- `S/local.sha` and `S/go2.sha` were not changed. Do not write either of them again. They are the records of the two launches. Check 20 of `build_facts.py` reads both. Decision (h) of FACTS.md prints the file time of `local.sha`. The copy command of 2026-11-17 (record line 309) starts with `sha256sum ... > local.sha` in S. Do not reuse that command unchanged.
- `sha256sum -c local.sha` in S now prints `go.sh: FAILED`. This is expected.
- `build_facts.py` cannot rebuild FACTS.md in S while `go.sh` does not have the sha256 that `local.sha` lists for it. Check 20 (`sha-local`) fails. Then `facts_text4.py` line 1461 stops the build before a file is written.
- The list build needs the opposite state. `T/make_list.py` and `companion_tool.py verify` pass only with the new line 20. So a rebuild of FACTS.md works only in a copy of S with the old line 20.
- `E/check_facts_build.py` tests both states in a copy of S (8 checks pass). With the edited text the build ends with status 1 and changes nothing. With the old line 20 all 27 checks of the build pass. The two written files then equal the stored ones after the folder path of the copy is replaced.
- My suggestion for the boot-id task, not agreed: keep a copy of each script as it ran, and make check 20 read these copies.
- Guard: `T/make_list.py`, function `check_two_texts_go`, tests these points at every build of the list: the text of line 20, both sha256 values, the sha256 of `local.sha` itself, `go2.sh` against `go2.sha`, lines of the two session records, the place of check 20, and the stored outputs of `check_line20.py` and `check_facts_build.py` in E. It does not run the tests. It does not read `check_start_command.out`. It stops when `go.sh` changes again.
- After a further edit of `go.sh`, rewrite this function so that it reverses every edit since 2026-11-17. New constants alone are not enough. The function holds the sha256 starts `75bc50b0` and `d68cf6c0` as literals. Also update the open point "Two texts of go.sh" in `make_list.py`, the annotation of the edited lines (`T/ann/go.c01.json`, `T/ann/go.overview.json`), point 8 of `T/BRIEF.md`, and the tests in E. Then rebuild (see [[crb-whole-chip-code-data-list-2026-11-21]]).
- Copy on CRB: this work ran no command on CRB. By the last record (2026-11-17, `go.sh: OK` against `local.sha`) the copy there has the old line 20. `run.sh` makes `go-direct.sh` from the `go.sh` on CRB. So a run started today has the line 20 of that copy.
- If only `go.sh` is copied to CRB, `run.sh` stops at its line 4 with status 4 (`NOT STARTED: a script differs from local.sha`). A copy needs a checksum list on CRB that fits the copied files. On CRB that list must have the name `local.sha`. Write it under another name on the agent server. `E/check_start_command.py` tests the three states (12 checks pass: 11 cases and one comparison of the two texts).
- When the message appears. `run.sh` tests the marker file itself in its line 2 and prints `RUNNING file present: stop` (status 3). So line 20 of `go.sh` prints its message only when the file appears between that test and line 20. When the file appears during a run, `ra.sh` (line 12) or `rx.sh` (lines 7, 13, 19) stops with its own message and status 3. `go.sh` then prints `FAILED: ra.sh session N rc 3` or `FAILED: rx.sh NAME rc 3`.
- `go2.sh` was not edited, because the user named `go.sh` only. It keeps the old message in lines 16 and 25.
- `E/check_line20.py` (9 checks pass) holds the proof of the two texts and the test of the new message.

What the boot-id task must change:

- `go.sh`: line 15 (comment), line 16 (`BOOT=...`), line 26 (the check). Keep line 17: the `state` function prints the boot id as a record only. Keep line 27 (MemTotal).
- `go2.sh` (only when the user asks): line 12 (`BOOT=...`), line 21 (the check). After an edit of `go2.sh`, check 20 fails for `go2.sh` as well.
- My suggestion, not agreed with the user: replace the check by a direct reading inside the script (`sudo -n dmidecode -t 17`, 12 lines at 7200 MT/s). The script then needs root once per start.
- The copies on CRB under `~/cache-perf/w120-7200-20261117/`.
- The companions `go.sh.md` and `go2.sh.md` are generated, and `companion_tool.py` compares their left column with the source. Since 2026-11-24 `go.sh.md` has its own generator, `crb/tmp/agent-scratch/explain-bash-2026-11-24/make_go_sh_md.py` (see [[crb-whole-chip-code-data-list-2026-11-21]]). It stops when a line of `go.sh` no longer holds the text that its explanation names. The list is generated too. `make_list.py` tests typed line numbers of both scripts and the text of `go.sh` line 20. Change the annotation inputs first, then rebuild.
