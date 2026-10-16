# Handoff: issue #4934 fix (kill-switch parity for PR #4901), state at 2026-10-15 21:30 UTC

## Update 2026-10-16 01:4x UTC: round 2 is DONE at the rebased head; the goal is not met at one cell; nothing is pushed

- Head: `b87d20dd81d5d7b562e5b9eea6656de7a6c6df84`, 7 commits on PR #4901's head `6b081187e1` (rebased 2026-10-15 23:0x UTC; backup branch `jhan-vnnik-5-i4934-pre-rebase` = `9b30b2074d`). Not pushed, no PR opened: jhan's rule was to push only when every line of the decision rule holds.
- Verdict (results in `exec/results/i4934-E2-cpu/summary.md` and `i4934-E2-fpga/summary.md`, 3 repetitions, rotated arm order): line 1 fails at tp2 prompt 1024 (fixoff vs headoff -0.84 TPS, -1.1 %, t -8.0, beyond the 0.40 TPS floor) and holds at tp2 prompt 8192 (-0.12 TPS), at tp4 (+0.46 TPS) and in TTFT everywhere; line 2 holds (AMX on: +1.1 % better, +0.3 % inside, +1.3 % better); line 3 holds (FPGA: -0.3 % and +0.0 %, inside). The remaining 1.1 % is the dotter path over the row-major tail rows (the ablation's 1.2 %, confirmed). A 16-row tail-block kernel would recover it.
- Also done at this head: six unit tests plus the kill-switch repeat, option-off and dispatch-off builds and tests (`exec/results/i4934-r2/tests-*.txt`), four traces analysed (`i4934-r2/compare-p*.txt`), token identity ok in three cells (`i4934-identity2`), mutations m1 and m3 caught (`i4934-mutate2`), m2 re-run after an anchor fix (`i4934-mutate2b`, see status.md).
- Deliverables ready: PR body `exec/i4934-20261015/pr-body-v5.md` (complete, 1,993 words outside Words used here, plain-English checked), chart page `VNNIed-K-in-place/issue4934/results-round2.html` (gen_report.py, render-checked), status log `status.md` (every step with numbers).
- 2026-10-16 13:22 UTC: the micro-benchmark of the tail-row score paths is DONE (exec/i4934-20261015/bench/, results exec/results/i4934-tailbench/, bench.done = ok, tables.md, chart page VNNIed-K-in-place/issue4934/tail-bench.html). Result: the fix's dotter path is cheaper than PR #4898's reader at the tail block in every cache scenario (-97 ns per visit hot, -333 ns in the one-decode-step scenario, -1,004 ns flushed; -5.6 to -57.8 us per decode step) against a measured gap of +156 us per step, so the tail-row scoring is NOT the cause of the remaining 1.1 % and option (b), a 16-row tail-block kernel, has nothing to recover (best candidate rowbat = dotter within 2 to 41 ns). The cause stays open: round-1 traces put it inside the workers' attention spans spread over all page visits (lower IPC, more DRAM misses at prompt 1024); next measurement = perf stat L2/LLC misses per attention worker, fixoff vs headoff vs newoff (status.md, section of 13:16 UTC). Comparison with main (2026-10-13 data chained with round 2): fixoff vs main est. +2.8 / +5.2 / +0.1 % TPS, est. -2.0 / -4.2 / -2.7 % TTFT; AMX on vs main: insufficient data (a base/baseoff arm in the next whole-machine round, about 1 h). First launch failed to link (libgcc_s); bench-run.sh has -lgcc_s now.
- 2026-10-16 (jhan): option (a), opening the PR as is, is declined for now. Option (b) stays open and starts only on jhan's word. The line below is kept for the record.
- Next, jhan's decision: (a) open the PR as is with the -1.1 % as an open item (`gh pr create --base jhan-vnnik-4-tail-block --body-file exec/i4934-20261015/pr-body-v5.md` after `git push -u origin jhan-vnnik-5-i4934`), or (b) add a 16-row tail-block kernel first and measure again (the chain scripts take a new COMMIT as they are; delete the i4934-E2-*, identity2, mutate2* result directories or fork new names first).
- The sections below are the state at 21:30 UTC on 2026-10-15 and are kept for the record. "How to resume" is superseded by this block.

## Short version

The fix branch `jhan-vnnik-5-i4934` (7 commits on PR #4901, head `9b30b2074d`, not pushed) builds and passes its unit tests, and its round-1 measurements show the prefill-time loss of issue #4934 gone and its decode-speed loss halved. Round 2, the measurement of the final head, was stopped at 21:06 UTC on jhan's order to free delphi-3bda, so the decision (push and open the PR, or not) is still open. To resume: rebase the branch onto PR #4901's current head, relaunch the round-2 chain with the one command in "How to resume", then fill the three deliverables from its records as described in "After the chain finishes".

## Words used here

| Term | Meaning |
|---|---|
| issue #4934 | The loss this branch addresses. With the AMX kill switch, PR 4 decodes qwen-3-4b (8 users, tp2) 2.7 to 3.7 % slower than PR 3, and its 8,192-token prefill takes 453 to 587 ms longer. |
| 3bda | delphi-3bda, the Granite Rapids test machine (Intel Xeon 6962P, 8 FPGA cards). Our half = socket 1, `--instance 1,2`. Whole-machine steps need jhan's order each time. |
| claude-box | The container this Claude session runs in. It shares the workspace with 3bda over NFS. nix (the build-environment tool) is no longer installed on it, so it cannot build or test tron. |
| tron, runtron, rinzler, serving | tron is the inference program under test. runtron is its command-line tool, which runs every cell. rinzler is the production server. "serving" means the four `rinzler@N` units on 3bda, managed by platformd. |
| Bill's marker | The file `/bill-has-instance-0,2` on 3bda. While it exists, Bill's agent may use the first half of the machine. A whole-machine step removes it (`exec/bill-share.sh take`) and the driver's exit handler recreates it. |
| AMX, the kill switch, `<x>off` | AMX (Advanced Matrix Extensions) is the Intel CPU matrix instruction set the attention kernels use. `TRON_AMX_DISABLE=1` (the kill switch) turns those kernels off at run time in the same binary. An arm `headoff`, `newoff`, `fixoff` runs the `head` (PR 3), `new` (PR 4) or `fix` binary with the kill switch. `fix2` is a second run of the `fix` binary (the A/A control). |
| PR 3, PR 4, the fix | PR 3 = PR #4898 (`dfafd13dce`, branch `jhan-vnnik-3-shared-save`). PR 4 = PR #4901 (branch `jhan-vnnik-4-tail-block`), the row-major tail block: a user's incomplete 16-token K (key) block is kept row by row in its own bytes and converted in place at the forward end (the end of one pass of the model). The fix = branch `jhan-vnnik-5-i4934` on PR 4. |
| KV page, block mask, the mask read, the dotter path | A KV page is a 64-token block of the key/value cache. The block mask is one byte per page and K store (`page::k_vnni_blocks_`), one bit per 16-token block, set once the block holds the packed VNNI layout. The mask read is the software attention's read of that byte once per page visit (a cold cache line before commit 7). The dotter path scores the up to 15 row-major tail rows of a page one row at a time (a dotter is the per-row dot product). |
| cell | One attention path (CPU or FPGA), tensor-parallel degree (tp2 or tp4), 8 users, and a prompt length (1024 or 8192 tokens). Every run generates 256 tokens per user. |
| TPS, TTFT, the band, t | TPS = decode tokens per second per user. TTFT = prefill time of the whole prompt. The band = twice the larger sample standard deviation of the two arms, never under 0.40 TPS or 0.15 s. Beyond the band = a change. t = the paired t statistic (the mean of the per-repetition differences over its standard error). |
| the chain | chain-r2.sh on 3bda: probe-r2.sh (build and tests on our half, then whole machine: traces, the CPU and FPGA campaigns, the fixrm and fixnd builds), identity-r2.sh (token identity), mutate-r2.sh (mutation checks). |
| fixrm, fixnd | The option-off build (`TRON_K_VNNI=OFF`, row-major K) and the dispatch-off build (`TRON_AMX_DISPATCH=OFF`, no AMX kernels compiled in), each with its tests. |
| Perfetto trace | The trace format tron writes (`.pftrace`), read with the perfetto Python package through `uvx --from perfetto python -I <tool.py>`. |
| the 22-cell syntax matrix | A local syntax-only compile in 22 build configurations (AMX dispatch on or off, the layout option on or off, five test files and the AMX kernel file). Command: `W=/home/jhan/workspace/ai-runs/tron-i4934 P=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material/probe bash /home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material/probe/matrix.sh <label> > /home/jhan/workspace/intel-AMX/exec/i4934-20261015/matrix-<label>.log`. It prints `MATRIX OK: 22 cells` on success. |

## Where everything is

- Worktree `/home/jhan/workspace/ai-runs/tron-i4934` (shared repo `/home/jhan/workspace/tron`), branch `jhan-vnnik-5-i4934`, head `9b30b2074dfb71a7ce5f94160b7659c3ca78bf38`, 7 commits on `175b1837b9`. Nothing pushed. Commits, oldest first: tensor block_token_mask; attention live-mask loop and split; attention per-page mask read; kv_cache completion reported once; model pool conversion; tests; kv_cache block mask in the page's first cache line. Commits in the worktree need `git commit --no-verify` (the lefthook git-hook runner needs nix).
- Status log (every step with times and numbers): `VNNIed-K-in-place/issue4934/status.md`. Read it before anything else.
- Scripts: `exec/i4934-20261015/` (all relative paths in this file are under `/home/jhan/workspace/intel-AMX/`). Records: `exec/results/i4934-*/`. Logs: `exec/logs/i4934-*.log`.
- 3bda build trees: `/var/tmp/jhan/tron-i4934` (the fix; `gen/runtron.fix` = sha256 `7025af651a333821...` at `9b30b2074d`, built 20:54 UTC), `/var/tmp/jhan/tron-pr4/gen/runtron.pr4` (PR 4, `ea94e95a4e`), `/var/tmp/jhan/tron-pr3/gen/runtron.pr3` (PR 3), `/var/tmp/jhan/tron-i4934abl` (ablation probes, a dirty tree, not needed again), `/var/tmp/jhan/tron-i4934mut` (mutation tree).
- Deliverable drafts: PR body `exec/i4934-20261015/pr-body-v3.md` (head `9b30b2074d`; places marked «R2...» and `<!-- R2 TABLE ... -->` take the round-2 numbers). Chart page config `exec/i4934-20261015/report-config-r2.json` for `gen_report.py` (it points at the round-2 summaries; "short" and "notes" are placeholders). A draft page from round 1: `VNNIed-K-in-place/issue4934/results-draft.html`.
- Memory: `~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/issue-4934-fix.md`.

## The rebase that must come first

PR 4's branch on origin is at `4d64013dff`, three commits past the fix's base `175b1837b9` (all three by jhan on 2026-10-15, 04:07 to 04:50 UTC): `8ad54a13b1` (comment review of kv_cache.hpp, model.hpp, self_attention.hpp, t_k_vnni_layout.cpp), `d0e6f816dd` (t_amx_dispatch_dtype.cpp: literal default arguments, named bools only next to their calls), `4d64013dff` (heterogeneous_scheduler_compile.cpp fixture). The PR needs the fix rebased onto `4d64013dff`, and round 2 must measure the rebased head. The rebase was not done in this session (the permission classifier refused `git rebase` as an irreversible local change). The pre-rebase head is `9b30b2074d`.

A read-only three-way merge preview (`git merge-tree 175b1837b9 4d64013dff 9b30b2074d`) shows one conflict hunk in each of three files. kv_cache.hpp and t_k_vnni_layout.cpp merge without conflict.
- `h/tron/models/model.hpp`, the comment above the `convert_pending_k_blocks` call: jhan's review keeps only the placement reason (after `run()` and `wait_for_coop_gof`). The fix's comment adds the pool conversion and the join before the logit delivery. Resolution: jhan's short form plus one sentence on the pool join.
- `h/tron/models/self_attention.hpp`, the dotter construction in the page loop: jhan's review removes `[[maybe_unused]]` from `live`, `vnni_blocks` and `plane`. The fix replaces that region with `make_dot_q` and a `[[maybe_unused]] auto dot_q` built after the loop. Resolution: the fix's region without the `[[maybe_unused]]` attribute (a name read inside a discarded `if constexpr` branch counts as used, per jhan's commit message).
- `t/t_amx_dispatch_dtype.cpp`, the `exercise_page` arguments: jhan's review writes the default arguments as literals and keeps named bools only at call sites. The fix adds its constants block (REPEAT_FALSE, AMX_AVAILABLE_*, RECORDED_ROWS_*, DOMINANT_TOKEN_*, the bf16 value helpers). Resolution: keep the fix's constants that are used at call sites, drop the ones that only fed default arguments, and follow `d0e6f816dd` for the rest.
After the rebase: clang-format (`uvx --from clang-format==19.1.7 clang-format --dry-run -Werror <files>`), the 22-cell syntax matrix, then the chain (it rebuilds and retests before any measurement).

## What is verified at the pre-rebase head 9b30b2074d (round 2's our-half part, records exec/results/i4934-r2/)

- Build with the native preset, RelWithDebInfo, `TRON_AMX_DISPATCH=ON`, `TRON_K_VNNI=ON`: ok, 603 s.
- Six unit tests, fake device, `--skip-benchmarks`: t_k_vnni_layout 1,041,278 assertions in 10 cases, t_amx_dispatch_dtype 2,778 in 2, t_amx_numerics 6,669 in 5, t_llama_unit 277,962 in 66, t_heterogeneous_scheduler 2,855 in 4, t_phase1_integration 6,220 in 64. All pass (`tests-fix.txt`).
- Kill-switch repeat: t_llama_unit 277,962 in 66 and t_heterogeneous_scheduler 2,855 in 4 pass. t_amx_numerics passes 4,108 assertions with its three AMX checks skipped as "AMX unavailable" (`tests-fixks.txt`).
- Four Perfetto traces of the head: `trace-{newoff,fixoff}-p{1024,8192}.pftrace` (not analysed. The trace tools are listed under "After the chain finishes").
- clang-format clean and the 22-cell syntax matrix OK at the head (status.md, "commit 7").

## What round 1 established (head c30a86f252 = commits 1 to 6, the same code without commit 7)

- E-cpu (`exec/results/i4934-E-cpu/summary.md`): kill-switch TTFT at parity with PR 3 in every cell. Decode: fixoff vs headoff -1.7 % at tp2 prompt 1024 (beyond the band), -1.5 % at tp2 prompt 8192 (inside through the 0.40 TPS floor), -0.4 % at tp4 prompt 1024 (inside). fixoff vs newoff +1.5 % at both tp2 cells, so the fix recovers half of PR 4's loss. With AMX on, fix vs new +0.6 / -0.1 / +1.3 % at tp2 prompt 1024 / tp2 prompt 8192 / tp4 prompt 1024 (no cost).
- E-fpga (`exec/results/i4934-E-fpga/summary.md`): tp2 fix vs new +0.0 %. tp4 fix vs new -1.2 % (beyond the band, t -17). A later interleaved run of 2,045 generated tokens (`exec/results/i4934-perf-fpga`, 2 runs per arm, read from the run logs because its summary.md is empty) found parity: fix -0.1 % TPS vs new (159.69 vs 159.87 tokens per second per user). So the tp4 gap is unexplained. Round 2 rotates the arm order per repetition to test an order effect.
- Token identity (`exec/results/i4934-identity`): fix == fix2 == new in all three cells (256 of 256 generated tokens identical). fixoff differs from fix at generated token 247 at prompt 1024 (the known kill-switch token divergence of issue #4444, not caused by this branch) and is identical at prompt 8192.
- Mutations (`exec/results/i4934-mutate`): the three deliberate breaks each fail their guarding test.
- Ablations (`exec/results/i4934-abl-cpu/summary.md`, four arms): builds with one mechanism removed each, timing probes only (their generated tokens are wrong by design). The kill-switch decode loss splits into the dotter path (-1.2 % at prompt 1024, 0.0 % at 8192), the mask read (-0.6 % and -1.0 %) and everything else (0.0 % and -0.6 %). Commit 7 targets the mask read. The dotter attribution is uncertain, for two reasons. The ablation builds show prefill differences up to 1.8 % where nothing they probe runs. The round-1 profile shows no dotter instructions with a large share of the samples. Round 2 at prompt 1024 settles it: about -0.6 % means the dotter part was an artefact, about -1.2 % means it is real.
- Comparison traces (`exec/results/i4934-trace2`, PR 3 vs the fix): the fix's main thread spends 0.8 to 1.1 ms less per decode step in Save K (the trace span of the key write) than PR 3. That time runs in parallel with the workers' attention and does not add to the step. The step grows by what the slowest worker's attention span grows: +215 us at prompt 1024, +1,264 us at 8192. So the whole residual is inside the software attention of the workers.

## What round 2 still has to produce

- `exec/results/i4934-E2-cpu/`: CPU attention, cells tp2 prompt 1024, tp2 prompt 8192, tp4 prompt 1024, arms head headoff new newoff fix fixoff, 3 repetitions with the arm order rotated per repetition (campaign-rot.sh), 54 runs, 75 min in round 1. Five complete records of repetition 1 at tp2 prompt 1024 exist from the stopped run (head, headoff, new, newoff, fix). The sixth (fixoff) had not started. Delete the directory before the relaunch, then the repetition runs as one block.
- `exec/results/i4934-E2-fpga/`: FPGA attention, tp2 and tp4 at prompt 1024, arms head new fix, 18 runs, 17 min.
- The fixrm and fixnd builds and their tests at the head (8 min). The round-1 values are in pr-body-v3.md at the «R2» marks..
- `exec/results/i4934-identity2/` (token identity, about 10 min in round 1) and `exec/results/i4934-mutate2/` (mutations, 7 min).

## How to resume

1. Rebase first (see "The rebase that must come first"). The new head's full sha is the COMMIT below.
2. Get jhan's order for the whole-machine steps (Bill's marker removed, serving down). Get a machine window too: the chain needs about 2.5 h. The window must avoid the nightly CI (its lease is held about 03:37 to 13:15 UTC) and the pre-CI hold (02:10 to 03:45 UTC, in which the drivers wait by themselves). Check nobody else runs: `ssh delphi-3bda "pgrep -af runtron | grep -v pgrep; ls -la /bill-has-instance-0,2; cat /run/lock/systems-test-ci.lease"`.
3. Remove the partial campaign records: `ssh delphi-3bda "rm -rf /home/jhan/workspace/intel-AMX/exec/results/i4934-E2-cpu /home/jhan/workspace/intel-AMX/exec/logs/i4934-E2-cpu.*"`. Keep `exec/results/i4934-r2/`: probe-r2.sh rebuilds and retests in 11 min, which is wanted after the rebase. (`SKIP_OURHALF=1` in the ssh line of a copy of launch-chain2.sh would skip that part, and it also skips the fixrm and fixnd builds at the end of probe-r2.sh, lines 154 to 159. Keep it at 0.)
4. Launch from claude-box (the script checks that the commit and the scripts are visible on 3bda first):
   ```
   COMMIT=<full sha of the rebased head> PROBE_END_BY=<ISO UTC> IDENTITY_END_BY=<ISO UTC> MUTATE_END_BY=<ISO UTC> bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/launch-chain2.sh
   ```
   The three END_BY values are the latest start times of each driver (round 2 used 01:30Z, 02:00Z and 02:05Z for an 18:38Z launch). Logs: `exec/logs/i4934-chain2.log`, `i4934-r2-probe.log`, `i4934-E2-cpu.log`, `i4934-E2-fpga.log`. Done files: `exec/results/i4934-r2/probe.done`, `i4934-identity2/identity.done`, `i4934-mutate2/mutate.done`.
5. Watch from claude-box with a loop over ssh (no faster than every 5 min). To stop the chain: `ssh delphi-3bda "kill -- -<pgid>"` with the pgid (process group id) from the chain log's first line. The running driver's exit handler brings serving up and recreates Bill's marker (it takes about 5 min).

## After the chain finishes

1. Decision rule, every line must hold:
   - fixoff vs headoff inside the band in TPS and TTFT in every CPU cell.
   - fix vs new inside the band or better in TPS with AMX on.
   - fix vs new inside the band under FPGA attention.
   jhan's instruction (2026-10-15): push the branch and open the PR only once the measurements show the goal is met. Otherwise report the numbers and stop. The PR is standalone (not part of the 4-PR stack), base `jhan-vnnik-4-tail-block`, opened with `gh pr create --body-file`, body ending with the Claude Code line.
2. Performance tables for the PR body: `python3 -I exec/i4934-20261015/pr_tables.py exec/results/i4934-E2-cpu/summary.json --arms headoff,fixoff,new,fix --pairs fixoff:headoff,fix:new --combined`, and the same on `exec/results/i4934-E2-fpga/summary.json` with `--arms new,fix --pairs fix:new`. Then:
   - Paste the tables into pr-body-v3.md at the two `<!-- R2 TABLE -->` marks.
   - Fill every «R2» mark from `exec/results/i4934-r2/tests-*.txt`, `exec/results/i4934-identity2/` and the fixrm and fixnd build records.
   - Write «R2-SAY»: the mechanism (the traces, the ablation split, the FPGA tp4 remark).
   - Write «R2-OPEN»: the dotter path at short prompts, if round 2 confirms it. A 16-row tail-block kernel would recover it. Reviewers decide, or an issue tracks it.
   - Run the plain-english check. Then `awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' pr-body-v3.md | wc -w` must be under 2,000 words (it is 1,947 words before the tables: cut Background and the Builds bullets first).
3. Chart page: fill "short" and "notes" in report-config-r2.json, then `python3 -I exec/i4934-20261015/gen_report.py exec/i4934-20261015/report-config-r2.json VNNIed-K-in-place/issue4934/results-round2.html` (light theme, Okabe-Ito colours, the ablation group is already in the config). Render-check the SVGs with cairosvg before delivering.
4. Trace analysis of `exec/results/i4934-r2/trace-*.pftrace` (optional, the round-1 comparison exists): save each `uvx --from perfetto python -I exec/i4934-20261015/trace_spans.py exec/results/i4934-r2/trace-<arm>-p<prompt>.pftrace --forwards` output as `exec/results/i4934-r2/spans-<arm>-p<prompt>.txt`, run `attn_forward.py` on each trace the same way, then `python3 -I exec/i4934-20261015/spans_compare.py exec/results/i4934-r2 1024 newoff fixoff` (and 8192).
5. Update status.md and the memory file with the outcome.

## Open questions the data does not settle

- Is the dotter path's 1.2 % at prompt 1024 real? Round 2 at tp2 prompt 1024 answers it (see "What round 1 established").
- The FPGA tp4 -1.2 % of round 1: an order effect or real? Round 2's rotated order answers it.
- The 0.6 % at prompt 8192 outside the mask read and the dotter path: it is inside the workers' attention (traces), and its source is not found yet.

## Traps (all verified this session)

- Builds and tests run only on 3bda. Local checks are the 22-cell syntax matrix and clang-format through `uvx --from clang-format==19.1.7 clang-format`.
- Never edit a script a 3bda process is running (NFS stale handle): copy to a new name. After editing a script on claude-box, verify it is visible on 3bda before launching (launch-chain2.sh does this).
- The permission classifier of this session refused `kill` of 3bda processes once ("dangerous") and allowed it later on jhan's explicit order, and it refused `git rebase`. If refused, give jhan the exact command.
- `summarize.py` lists only the arms in `WEDPERF_ARMS` (default `base head baseoff headoff`). For other arm names, regenerate with `WEDPERF_ARMS` and `WEDPERF_PAIRS` set (the ablation summary needed this).
- `rinzler@0` on 3bda was active at 01:37 and 01:54 UTC on 2026-10-15 (after our run-1 serving-up) and shows `failed` on every machine line from 04:39 UTC on. The cause was not investigated, and it is not ours to fix.
