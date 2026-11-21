# pr5022-final-20261119: tests of the final head of tron PR 5022 on delphi-3b35

Short version: the final tree of PR 5022 (review round 2) builds on delphi-3b35 with the build option
TRON_AMX_DISPATCH (it compiles the AMX kernels) ON, and all 14 unit-test runs end with the wanted exit code
(2026-11-20). The AMX kernel file compiles to the same instructions at the reviewed head and at the final tree.
No benchmark ran, and the registry tool `bin/slice bench` was not run, because it measures on both halves of
the machine.

State on 2026-11-20 10:28 PST: the tree is pushed as commit ddf843ad97, the CI runs on it passed, all replies
are posted, and the review is re-requested (section "After the go").

Words used here:
- tron: the inference program. runtron: its command-line tool. rinzler: its server.
- AMX: Intel's tile-matrix instruction set. Kill switch: the environment variable TRON_AMX_DISABLE=1.
- Fake device: a software stand-in for the FPGA cards, linked into the unit tests.
- Final tree: PR head 4c4b7b8864 merged with main 3bea58b788, plus the review edits. Prepared, not committed, in
  /home/jhan/workspace/ai-runs/pr5022-final/tron. Its git tree hash is in results/pr5022-final-20261119/tree.txt.
- Registry: config/test-benchmarks.json. Per machine class it holds the run time and memory of every test, and
  the exit code a test may return when all its cases skip. `bin/slice` (the test scheduler) reads it.
- QK kernel: scores queries against keys. PV kernel: multiplies the attention weights with the values.

## Rules for the shared machine

- delphi-3b35 is shared. Brian Hamon and John Pruitt use the first half of the FPGA cards (cards 0-3).
- Every command here is pinned to our CPUs 96-143 with `nice -n10`, and uses SYSTEM_CONFIG="--instance 1,2".
- The test binaries link the fake device. They open no FPGA card and take no huge page.
- Take the load snapshot first: `bash exec/3b35-inspect-20261112/load-snapshot.sh`.
- Never run `git worktree prune` on that machine. Build trees are /var/tmp/jhan/b35-pr5022-<tag>.
- Do not run `bin/slice bench` there. It measures each test on slot 0 (first half) and on the first slot of the
  second half, and the test binaries pin their threads by slot (see "Registry" below).

## Files

| File | Runs on | What it does |
|---|---|---|
| build-3b35.sh | delphi-3b35 | `TAG=final`: worktree of main plus the prepared files, tree-hash check, build of runtron and the three tests. `TAG=main`: the same build of plain main (not used in the end). |
| tests-3b35.sh | delphi-3b35 | The test runs listed in its header. Results in results/pr5022-final-20261119/tests.txt and tests/*.log. |
| objcmp-3b35.sh, objcmp-compare.py | delphi-3b35 | Object compare of src/tron/kernels/amx_attn.cpp between three source trees, with the compile command of the final build. Results in results/pr5022-final-20261119/objcmp/. |
| registry-check-3b35.sh | delphi-3b35 | Read-only checks of the registry file in the build tree. Results in results/pr5022-final-20261119/registry-check-<label>.txt. |
| mutation-exit-code-3b35.sh | delphi-3b35 | Breaks one line of the transpose header, rebuilds and runs t_amx_numerics, records the exit codes, restores the line. Results in results/pr5022-final-20261119/mutation-exit-code.txt. |
| ci-watch.sh | the agent's own machine | Polls the CI runs of the pushed head on GitHub (read-only) until they end. Log in results/pr5022-final-20261119/ci-watch.txt. |

## How to run

```
ssh delphi-3b35 'TAG=final bash ~/workspace/intel-AMX/exec/pr5022-final-20261119/build-3b35.sh'
ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/pr5022-final-20261119/tests-3b35.sh'
ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/pr5022-final-20261119/objcmp-3b35.sh'
ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/pr5022-final-20261119/registry-check-3b35.sh after'
```

Logs: exec/logs/pr5022-final-20261119-*.log. Markers: results/pr5022-final-20261119/{build-final,tests,objcmp}.done.

## Results (2026-11-20, 13:37 to 13:50 UTC, which is 05:37 to 05:50 PST)

Machine state. The load snapshot before the runs (13:35 UTC) shows our CPUs 0.1 % busy and FPGA cards 4-7 not
open. The other half runs two rinzler servers of user `disagg` with 31 busy threads each (load average 64).
The snapshot after the runs (13:50 UTC, results/.../load-snapshot-after.txt) shows the same two servers with
the same process ids, and cards 4-7 still not open.

Two passes ran. The first pass used tree 5821ee8641 (11 files differ from main). The second pass used the final
tree c114b85944 (12 files: the registry file is added). The four binaries have the same sha256 in both passes,
so the registry edit changes no binary. The first-pass records are kept in results/.../first-pass-tree-5821ee86/.

Build (results/.../build-final.txt). clang 19.1.7, preset native, RelWithDebInfo, TRON_AMX_DISPATCH=ON,
BUILD_INGEST_MODELS=OFF. 0 compiler warnings. runtron holds 64 `tdpbf16ps` instructions (the AMX bf16 dot
product). First pass 304 s, second pass 19 s.

Tests at tree c114b85944 (results/.../tests.txt). Every run ended with the wanted exit code.

| Run | Exit code (wanted) | Result |
|---|---|---|
| t_amx_numerics, AMX on | 0 (0) | 21,521 assertions in 5 test cases pass |
| QK section, 4 heads / 16 heads | 0 (0) | 4,096 / 4,096 assertions pass |
| PV section, 4 heads / 16 heads | 0 (0) | 2,561 / 4,097 assertions pass |
| transpose section, 4 heads / 16 heads | 0 (0) | 1,280 / 1,280 assertions pass |
| t_amx_numerics, kill switch | 0 (0) | 6,671 assertions pass; 3 cases pass, 2 cases skip ("AMX unavailable") |
| t_amx_numerics "[kv_data]", kill switch | 4 (4) | 2 cases, both skip, so Catch2 returns 4 |
| t_amx_dispatch_dtype, AMX on / kill switch | 0 (0) | 30,747 assertions in 1 test case pass, both runs |
| t_llama_unit, AMX on / kill switch | 0 (0) | 265,564 assertions in 75 test cases pass, both runs |
| CTest registration of t_amx_numerics | - | SKIP_RETURN_CODE=4, labels fake, skip_return_code_4, slice_filter_catch2 |

Object compare (results/.../objcmp/objcmp.txt). Each tree is compiled with the command the final build
recorded for the kernel file. The file has 11 functions.

| Pair | Identical functions | The difference |
|---|---|---|
| reviewed head 4c4b7b8864 vs final tree | 11 of 11 | none |
| measured commit 5061623a34 vs final tree | 10 of 11 | 16-head QK kernel: the same 207 instructions, two adjacent `addq` (loop counter steps) swapped |
| final tree, recompiled vs the object of the build | 11 of 11 | none |
| object of the build vs the code inside gen/runtron | 9 of 11 | both PV kernels: the linker replaces the 2 instructions that fetch the per-thread buffer address (`__tls_get_addr` call) with 2 that read it from `%fs` |

The last row masks addresses, because the linker fills them in.

Registry (results/.../registry-check-before.txt and -after.txt, wall-times.txt).
- `bin/slice route` on delphi-3b35 answers `local-legacy` (8 cards, no shared scheduler).
- `bin/slice bench --update` was not run. It runs one of the two tests with SYSTEM_CONFIG `--instance 0,N`,
  which is the first half of the machine [bin/slice:2354-2365, :2419-2440]. The test binaries pin their threads by
  that value (the test logs show "INIT: Pinning application cores to ..."). That would put test threads on the
  CPUs the two rinzler servers use.
- Edited by hand instead: both `t_amx_numerics` rows (machine classes genoa96 and granite_rapids_6962p) gain
  `"skip_return_codes":[4]`. The file still equals the output of the tool's own formatter.
- Before the edit, the scheduler's drift warning reads "t_amx_numerics: skip_return_codes=[] -> [4]". After
  the edit there is no warning. `bin/slice bench --check` and `--check-platform` exit 0 before and after.
- The `times` and `max_rss_mb` values of the rows are not changed. Measured directly on our half, 5 runs each,
  with the registered command: t_amx_numerics 0.66 to 0.69 s and 7 to 9 MiB; t_amx_dispatch_dtype 0.77 to 0.79 s
  and 97 to 99 MiB. The granite_rapids_6962p rows say 0.66 to 0.91 s and 0.60 to 0.85 s, and 8 MB for both.

Lint (results/.../lint-notes.txt): `make lint-notes` (the check of "Note [...]" references in comments) exits 0
at tree c114b85944 on delphi-3b35, run with the GHC and Cabal of ~/.ghcup. No changed file includes `<cassert>`.
`git diff --check` against main is clean. The changelog line has 79 characters (limit 80).

Not covered here: throughput, token identity, and any run with a real FPGA card.

## After the go (jhan's "go" of 2026-11-20 08:50 PST)

Done on 2026-11-20. Times are PST.

1. Commits (git plumbing, results/pr5022-final-20261119/commits.txt): merge commit 1bda322822 (tree 3afff9bb86bf,
   parents 4c4b7b8864 and 3bea58b788) and review commit ddf843ad97 (tree c114b85944, the tested tree). Pushed to
   `jhan-amx-kvmul16` at 08:52 as a fast-forward, without force. The worktree ai-runs/tron-glimmer-amx is
   fast-forwarded to it.
2. CI at ddf843ad97, all passed (watch log: results/.../ci-watch.txt; watcher: ci-watch.sh):
   - GCP Nix, the default workflow, run 44777709823. Test host on delphi-3bd6-0: 106 tests pass.
   - Slice tests, run 44777709810.
   - CMake and CTest, the legacy workflow with TRON_AMX_DISPATCH=ON, run 44777748892, started by hand at 08:52.
     Build on andoria-ee10-0 (28 minutes). test-host attempt 1 on andoria-ee10-0 (AMD EPYC 9654): 106 tests pass,
     and the QK and PV kernel cases skip on that CPU. Only that job was rerun
     (`gh run rerun 44777748892 --job 136449930359`). Attempt 2 landed on delphi-3bd6-0 (Xeon 6962P, AMX in the
     CPU flags): 106 tests pass. A passing log has one line per test executable, not per case.
3. Follow-up issue filed: positron-ai/tron #5511 (text: muse-glimmer/pr5022-followup-issue.md).
4. PR description edited at 09:43 (muse-glimmer/pr5022-body-round2.final.md, 1,996 words; the old one is
   results/.../pr-body-before-round2.md). Comment on issue 5021 posted at 09:43.
5. The 26 thread replies and the combined reply were posted at 09:50 as ONE review, number 5997064669
   (results/.../posted-review.json). The review is created "pending", the replies are added and read back, and
   the last step submits it. The tools and the posted texts are in muse-glimmer/pr5022-post/ (README there).

After the automated review (2026-11-20):

- An automated review (`claude[bot]`, review 5996505130) commented on ddf843ad97 at 09:08 with two findings. Its
  red finding says that 4 failed assertions exit with code 4 and are reported as a skip. That is refuted:
  Catch2 v3.7.1 exits with 42 for any failed assertion (see "Mutation check" below).
- jhan found the phrase "legacy workflow only" in the draft reply B2 unnecessarily harsh. B2 was reworded, and
  jhan gave the go at about 10:26.
- Both replies (cards B1 and B2 of muse-glimmer/respond-2-Isaac.html) were posted at 10:27 as one review, number
  5997527928 (results/.../posted-bot-replies.json). All 28 review threads of the PR hold a reply.
- The review was re-requested from the reviewer at 10:27.
- The push made GitHub request reviews from the teams tron-ci, tron-ingest and tron-core (.github/CODEOWNERS).

Nothing is open on our side as of 10:28. The review decision on GitHub stays "changes requested" until the
reviewer reviews again.

## Mutation check of the test exit code (2026-11-20, 17:48 UTC)

Script: mutation-exit-code-3b35.sh. Result: results/pr5022-final-20261119/mutation-exit-code.txt.
One line of h/tron/kernels/amx_attn_transpose.hpp is broken (stage 1 reads the high halves), gen/t_amx_numerics
is rebuilt and run, and the line is restored.

| Run of the broken build | Failed assertions | Exit code |
|---|---|---|
| t_amx_numerics, AMX on | 4 (the transpose and QK cases fail) | 42 |
| t_amx_numerics, kill switch | 2 (2 cases skip) | 42 |
| ctest -R t_amx_numerics (applies SKIP_RETURN_CODE 4) | - | 8, the test is reported as Failed |

After the restore the tree hash equals c114b85944 and gen/t_amx_numerics has the same sha256 as before
(f187851345e3...). The load snapshot before the run (17:47 UTC) shows our CPUs 0.1 % busy and the same two
rinzler servers on the other half.
