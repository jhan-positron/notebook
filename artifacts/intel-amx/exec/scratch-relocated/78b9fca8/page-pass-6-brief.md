# Page pass 6: delphi-3b35 results are in; replies move to their posting form

Target: `/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html` only. Same method as passes 2 to 5:
one idempotent script `apply_patch6.py` in the scratchpad, exact-text asserts, write only when every assert passes,
then the structure check, then `html2text.py <page> <scratchpad>/respond-cur7.txt`. Do not touch any other file.
Nothing is committed, pushed or posted. The user's rules stay: plain English (one claim per sentence, numbers
with units, terms defined, no idioms), light page, no "#3997" in any reply block, "prompt N" never "ctx N".

## A. Facts (all measured; cite the files as new references R47 and up)

Time line.
- delphi-3b35 rebooted on 2026-11-19 at 21:19 PST (the machine prints 2026-11-20 05:19:05 UTC).
- John Pruitt wrote in the group thread on 2026-11-19 at 23:48 PST: "Reboots are done. I'm doing some more work on
  the machines but doesn't appear like I'll need to reboot them again. Still keeping to FPGAs 0-3 on delphi-3b35".
- My watcher compared the machine's UTC boot time with the local Pacific clock. So it reported the reboot 8 hours
  late, at 05:35 PST on 2026-11-20. That is my error. The runs took place from 05:37 to 05:50 PST on 2026-11-20
  (13:37 to 13:50 UTC).

Machine state (load snapshot at 13:35 UTC before and 13:50 UTC after; files
`exec/results/pr5022-final-20261119/load-snapshot-after.txt`, README of the run).
- Before: our CPUs 0.1 % busy. FPGA cards 4-7 not open. The other half runs two rinzler servers of user `disagg`
  (the deployments dev1 and dev2 under /var/lib/disagg) with 31 busy threads each, which gives the load average 64.
  Do not name an owner for them beyond "the other half, used by Brian Hamon and John Pruitt".
- After: the same two servers with the same process ids (148594, 150359). Cards 4-7 still not open.
- Every run was pinned to CPUs 96-143 at `nice -n10` with SYSTEM_CONFIG="--instance 1,2". No FPGA card and no
  huge page was used.

Tree.
- First pass: tree hash `5821ee86418d3ac07944112c529d7d311e91f3bd`, 11 files differ from main 3bea58b788.
- Final tree: `c114b85944795538cb5b2431493f3dc196e9822f`, 12 files (the 12th is `config/test-benchmarks.json`).
- The four binaries (runtron and the three tests) have the same sha256 in both passes. So the registry edit
  changes no binary. Record: `exec/results/pr5022-final-20261119/{tree.txt,prep.txt,build-final.txt}` and
  `first-pass-tree-5821ee86/`.
- Main moved by 1 commit after the merge: 0af590c21e (PR 5304) on 2026-11-19 21:17 PST. It changes line 409 of the
  registry file and none of the other 11 files. A trial merge of the final tree with 0af590c21e gives 0 conflict
  markers. The merge in the final tree stays at 3bea58b788.

Build (`build-final.txt`). `cmake --preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON` with
clang 19.1.7 and ccache, RelWithDebInfo. Note OFF: the old plan line in Part C says `BUILD_INGEST_MODELS=ON`; that
line is wrong now, correct it. Targets runtron, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit. 0 compiler
warnings. runtron holds 64 `tdpbf16ps` instructions. 304 s in the first pass, 19 s in the second.

Tests at the final tree c114b85944 (`tests.txt`, `tests/*.log`, `tests/t_amx_numerics.junit.xml`). All 14 runs
ended with the wanted exit code. Same counts in both passes.

| Run | Exit code (wanted) | Result |
|---|---|---|
| t_amx_numerics, AMX on | 0 (0) | 21,521 assertions in 5 test cases pass (before this round: 17,425 in 4) |
| QK section, 4 heads / 16 heads | 0 (0) | 4,096 / 4,096 assertions |
| PV section, 4 heads / 16 heads | 0 (0) | 2,561 / 4,097 assertions |
| transpose section, 4 heads / 16 heads | 0 (0) | 1,280 / 1,280 assertions |
| t_amx_numerics, kill switch | 0 (0) | 6,671 assertions pass; 3 cases pass, 2 cases skip ("AMX unavailable") |
| t_amx_numerics "[kv_data]", kill switch | 4 (4) | 2 cases, both skip, Catch2 returns 4 |
| t_amx_dispatch_dtype, AMX on and kill switch | 0 (0) | 30,747 assertions in 1 test case, both runs (before this round: 3,694) |
| t_llama_unit, AMX on and kill switch | 0 (0) | 265,564 assertions in 75 test cases, both runs (before: 265,452 in 67; the 8 new cases come from main: t/t_llama_unit.cpp has 44 TEST_CASE macros at 4c4b7b8864 and 52 on main 3bea58b788) |
| CTest registration of t_amx_numerics | - | SKIP_RETURN_CODE=4; labels fake, skip_return_code_4, slice_filter_catch2 |

Durations (Catch2): the whole of t_amx_numerics takes 0.013 s of test time. The 9 sections of
t_amx_dispatch_dtype take 0.134 s together; the three new sections take 0.011 s, 0.008 s and 0.011 s.

Object compare of `src/tron/kernels/amx_attn.cpp` (`objcmp/objcmp.txt`, `objcmp/main-vs-final-4head.txt`).
Method: each tree is compiled on delphi-3b35 with the command the final build recorded for this file
(clang 19.1.7, the same compiler build as the measured binaries). The file has 11 functions.

| Pair | Identical functions | The difference |
|---|---|---|
| reviewed commit 4c4b7b8864 vs final tree | 11 of 11 | none |
| measured commit 5061623a34 vs final tree | 10 of 11 | `qk_rowmajor_128x4<16>`: the same 207 instructions; the two adjacent loop-counter additions `addq $0x40, %rdx` and `addq $0x400, %rsi` are swapped |
| final tree recompiled vs the object of the build itself | 11 of 11 | none |
| object of the build vs the code inside the linked `gen/runtron` (addresses masked) | 9 of 11 | both PV kernels: the linker replaces the 2 instructions that fetch the address of the per-thread buffer (a call of `__tls_get_addr`) by 2 instructions that read it from `%fs` |
| main 3bea58b788 vs final tree, 4-head kernels | pack 509 = 509, QK 204 = 204 instructions, identical | PV: 121 = 121 instructions with the same instruction names in the same order; registers, offsets and the access to the per-thread buffer differ |

So the T10 bullet (10 of 11 identical between 5061623a34 and the final head, `<16>` QK with two neighbouring
counter increments swapped) is confirmed as written. The Short version claim of the PR body (the 4-head pack and
QK kernels emit the same instructions as on main) is confirmed at the final tree.

Registry (I25, I26) (`registry-check-before.txt`, `registry-check-after.txt`, `wall-times.txt`).
- `bin/slice route` on delphi-3b35: `route: local-legacy`, cards 8, "Local cards are present; shared Dice is not
  configured."
- `bin/slice bench --update` was NOT run. Reason, from the tool's code and the test logs: it measures on the first
  slot of each NUMA node, so one of the two tests always runs with SYSTEM_CONFIG `--instance 0,N`, the first half
  of the machine [bin/slice:2354-2365, :2419-2440]. The test programs pin their threads by that value (their logs
  print "INIT: Pinning application cores to ..."; t_amx_dispatch_dtype starts 55 pool workers). That would put test
  threads on the CPUs of the two rinzler servers. This is the case the page announced in Part C ("It is skipped if
  it needs FPGA cards or the whole machine").
- Done by hand instead: both `t_amx_numerics` rows gain `"skip_return_codes":[4]`
  [config/test-benchmarks.json:151 (genoa96), :494 (granite_rapids_6962p)]. Older page text names lines 152 and 492;
  the right lines are 151 and 494. The file equals the output of the tool's own formatter (`format_bench_json`),
  byte for byte.
- Before the edit the scheduler's drift warning reads "t_amx_numerics: skip_return_codes=[] -> [4]". After the
  edit: none. `bin/slice bench --check` and `bin/slice bench --check-platform` exit 0 before and after.
- `times` and `max_rss_mb` are not changed. Direct measurement on our half, 5 runs each, registered command
  (`gen/<test> --benchmark-samples=2`), load on our CPUs 0.0 %: t_amx_numerics 0.66 to 0.69 s and 7 to 9 MiB;
  t_amx_dispatch_dtype 0.77 to 0.79 s and 97 to 99 MiB. The granite_rapids_6962p rows say 0.66 to 0.91 s and
  0.60 to 0.85 s, and 8 MB for both. The 8 MB of t_amx_dispatch_dtype is the default build with the option OFF,
  where the file holds only its placeholder case.
- The scheduled refresh (`bench-refresh.yml`, weekly) succeeded on 2026-11-01, 11-08 and 11-15. The page's older
  remark that it failed on 2026-10-18 and 10-25 is true but stale; do not present it as the current state.

PR body draft (`pr5022-body-round2.draft.md`): values filled in. 1,979 words. Placeholders left: ⟦HEAD⟧, ⟦NIXRUN⟧,
⟦CMAKERUN⟧, ⟦RUNNER⟧, ⟦CMAKERESULT⟧ (all need the push). Two rows left the merge-base table (qwen3-4b / tp2 / 8192
and gpt-oss-120b / tp4 / 2048, both inside their bands) with the sentence "Two further rows, both inside their
bands, are in the result file." The object-compare sentence reads: "Compiled with the build's own command, 10 of
the kernel file's 11 functions match the measured commit exactly. The 16-head QK kernel has the same 207
instructions, with two adjacent loop-counter additions swapped."

## B. Reply drafts: posting form

The replies are posted after the push and after both CI runs, in one go. So every reply must read as a report
of what the final head contains.

1. In every reply block: "Will do: X" becomes "Done: X", and "I will ..." becomes a statement of what the head
   has, in present or past tense. Keep the technical content. Do not add new claims. 16 lines carry "Will do" and
   28 carry "I will" in the current text.
2. Things that exist only after the push get a visible placeholder in the reply text: ⟦HEAD⟧ (head commit),
   ⟦NIXRUN⟧ (default CI run), ⟦CMAKERUN⟧ and ⟦RUNNER⟧ (legacy CMake run and its test runner), ⟦ISSUE⟧ (number of the
   follow-up issue, filed just before the replies). A reply that promised an addition to the Verification table
   now says the table has it.
3. I25, new reply (replace the whole reply; Action row becomes "accept in part: registry metadata by hand, timing
   rows not re-measured"):

   Partly done. Both `t_amx_numerics` rows now carry `"skip_return_codes":[4]`, so the registry agrees with the
   registration [config/test-benchmarks.json:151, :494]. `bin/slice bench --check` and `--check-platform` pass,
   and the scheduler's drift warning for `t_amx_numerics` is gone.

   Not done: I did not run `bin/slice bench --update`, so `times` and `max_rss_mb` are unchanged. `bin/slice route`
   answers `local-legacy` on the Granite Rapids host I can use. But the tool measures on slots of both NUMA nodes,
   and the tests pin their threads by slot. That host is shared, and I may use one half of it.

   Measured directly on that half with the option-ON build, 5 runs each with the registered command:
   `t_amx_numerics` takes 0.66 to 0.69 s and `t_amx_dispatch_dtype` 0.77 to 0.79 s. The rows say 0.66 to 0.91 s
   and 0.60 to 0.85 s, so the scheduling estimates still hold. One number is off: `t_amx_dispatch_dtype` peaks at
   99 MiB in the option-ON build, and the row says 8 MB, which is the default build where the file holds only its
   placeholder case.

4. I26: "The registry refresh follows." becomes "Both registry rows of `t_amx_numerics` carry
   `"skip_return_codes":[4]` (your comment at line 311)." Drop the later sentence "Then the registry refresh from
   your comment at line 311, which adds ...". The Verification paragraph becomes measured: on delphi-3b35 with the
   kill switch, `TRON_AMX_DISABLE=1 gen/t_amx_numerics "[kv_data]"` exits 4 (2 cases, both skipped);
   `ctest --show-only=json-v1` lists `SKIP_RETURN_CODE 4` and the label `skip_return_code_4`; the unfiltered
   kill-switch run exits 0 with 3 cases passed and 2 skipped; the unfiltered AMX run exits 0. Say plainly that the
   kill switch stands in for a host without AMX.
5. T10: first bullet, replace "with the compiler build and the flags of the measured binaries" by "with the
   compiler build of the measured binaries and the compile command of the final build". The "Before posting" row
   becomes: confirmed on delphi-3b35 on 2026-11-20 (table above); nothing to correct.
6. I10: the bullet "Object compare of the kernel file (one object file, clang 19.1.7, 2026-11-19) ... is pending."
   becomes the measured result: reviewed commit vs final tree 11 of 11 functions identical on a Granite Rapids
   host with the build's own compile command; `qk_rowmajor_128x4<4>` has 204 instructions and `<16>` has 207; the
   4-head pack and QK kernels are identical to main's (509 and 204 instructions). The new case ran there: 1,280
   assertions per section, and it also ran under the kill switch.
7. I19: "I will rerun `t_amx_dispatch_dtype` ..." becomes: at the final head it passes 30,747 assertions in 1
   test case (3,694 before this round), with AMX on and with the kill switch. The "Still open" row becomes
   "Closed 2026-11-20": the check ran on delphi-3b35 and passed, including `v_star == 0` on the AVX path.
8. I5, I6, I17, I21, I24 and every other reply that promised a rerun at the final head: state the result from the
   table above where the reply speaks of it. Do not add numbers a reply does not need.
9. T5 / I16 (CI coverage): keep the two CI rows as placeholders (⟦NIXRUN⟧, ⟦CMAKERUN⟧, ⟦RUNNER⟧), in posting form.

## C. Status parts of the page

1. New box at the top, above the earlier answer boxes, id `open4`, title "Status 2026-11-20 05:55 PST: the tests
   at the final head are in". Content, short: (a) all 14 test runs at the wanted exit code, table of 5 rows at
   most; (b) object compare in two sentences; (c) the registry tool was not run and why, what was done instead;
   (d) John Pruitt's and Brian Hamon's half was not touched (snapshot facts); (e) my watcher error, 8 hours;
   (f) "One thing is needed from you: the go to commit, push and post." with the ordered list of what the go
   starts: 1. two commits on `jhan-amx-kvmul16` (the merge of main 3bea58b788, then the review edits; the head
   tree must equal c114b85944) and the push; 2. the default CI runs by itself, and I start the legacy CMake
   workflow by hand; 3. I file the approved follow-up issue; 4. when both CI runs are in, I fill the run ids into
   the PR description and the replies, edit the PR description, post the 26 inline replies and the combined
   reply, and add the comment on #5021. Also say: if a CI run fails I stop and report before posting anything.
2. The page's own Short version and any "pending" wording: bring up to date.
3. Part C: the status paragraph (tree hash, 12 files, date), the bullet "Pending on delphi-3b35" (now done), the
   `config/test-benchmarks.json` line (hand edit, tool not run), "PR body edits" (values filled, placeholders
   left, two rows dropped), the block "Runs on delphi-3b35: pending" (becomes "done on 2026-11-20", with the
   results and with the corrected build line), "CI and issues" (unchanged, still after the go).
4. References: add R47 and up for: the run README `exec/pr5022-final-20261119/README.md`; `tests.txt`;
   `objcmp/objcmp.txt` and `objcmp/main-vs-final-4head.txt`; `registry-check-before.txt` / `-after.txt` and
   `wall-times.txt`; `load-snapshot-after.txt`; John Pruitt's message of 2026-11-19 23:48 PST (group thread
   C0CKKMX08LC); bin/slice lines 2354-2365 and 2419-2440; `bench-refresh.yml` run list (2026-11-01, 11-08, 11-15
   success). All under `/home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/` unless said.

## D. Checks before you report

- Structure check passes.
- `grep -c "Will do"` in reply blocks: 0. No "I will" left in a reply block, except for actions that truly come
  after posting (none expected).
- "3997" in reply blocks: 0.
- Every quoted code block still matches the working tree `/home/jhan/workspace/ai-runs/pr5022-final/tron`.
- No reply states a number that differs from section A.
- Report: byte size, line count, the list of reply ids you changed, every placeholder ⟦...⟧ now in the page with
  its count, and anything in section A that you could not place.
