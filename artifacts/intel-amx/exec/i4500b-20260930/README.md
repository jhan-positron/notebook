# i4500b-20260930: build and measure the issue #4500 policy "blocks completed under hardware attention stay row-major"

Short version. Commit 452b2052c9 on branch jhan-amx-vnniK-i4500 (on top of the fix f34b0fe2ec) stops the forward-end
VNNI conversion of the K blocks that decode completes for KV slots the FPGA scores. This folder builds it, tests it,
takes decode traces of it and measures it on delphi-3bda, our half, after the nightly CI of 2026-09-30. Fork of
exec/i4500fix-20260928/.

Words used here: tron = the inference program under test; runtron = its command-line tool; rinzler = the production
server; deb = the Debian package the nightly installs; VNNI K = the K cache layout of PR #4424; the fix = the row-major
16-token tail block (f34b0fe2ec); the policy = 452b2052c9; AMX = the Intel matrix instruction set; our half = socket 1
and the FPGA cards 90/93/b9/bc of delphi-3bda; the lease = /run/lock/systems-test-ci.lease, held by the nightly CI;
TPS = decode tokens per second per user; TTFT = time to first token.

## Why

Yesterday's cells (exec/results/i4500fix-20260928) left the qwen3-4b FPGA-attention cells at -2.3 % (tp2, 2 users) and
-8.8 % (tp4, 4 users) TPS against the canonical AMX build. The code reading of 2026-09-30 (fact sheet in the session
scratchpad) found that under FPGA attention the CPU scores only the tail above the DMA-complete GOFs, in the row-major
tail block, so the remaining per-step differences of the fix against canonical are main-thread bookkeeping and the
forward-end conversion of every completed block of every layer and KV head (16 KiB of traffic per block and head,
every 16th step for every user, serial on the main thread). The policy removes that conversion where the AMX kernel
can never read the block.

## Files

- chain.sh: steps A0 A B C T D E below, detached on 3bda, gated by NOT_BEFORE (default 2026-09-30T13:00:00Z), the lease
  and other people's activity (bill excluded by the half-split agreement).
- launch.sh: run on claude-box; checks the files on 3bda (NFS attribute cache) and starts chain.sh there.
- lib.sh: waits, watcher, hugepage cleanup, serving restore (as in i4500fix-20260928).
- build-deb.sh: the fixS1 .deb from commit 2fd11e32ca (the 2026-09-29 fix deb line 8198eab4cc + the policy).
- smoke.sh: runtron token rows fixS1 vs fix vs fixS1 again, CPU and FPGA attention, prompts 1024 and 1000.
- traces.sh: Perfetto decode traces (runtron, tp2 2 users, tp4 4 users) of base c7844ca2ce / fix / fixS1.
- campaign.sh: the rinzler cells; st_perf2.py: the nightly's client with --prompt-length; summarize.py: the tables.

## Steps of chain.sh

| step | what | where | result |
|---|---|---|---|
| A0 | runtron of f34b0fe2ec (incremental) -> gen/runtron.fix | /var/tmp/jhan/tron-i4500 | results/build-fix.done |
| A | build 452b2052c9 (AMX + VNNI K + ingest models), runtron + 7 tests, 5 run with the fake device | /var/tmp/jhan/tron-i4500b | results/build-fixS1.txt, tests-fixS1.txt |
| B | fixS1 deb of 2fd11e32ca | /var/tmp/jhan/tron-i4500bdeb | /var/tmp/jhan/i4500b-20260930/{fix.deb,manifest.json,root/} |
| C | smoke | our half, runtron | results/smoke/smoke.txt |
| T | traces | our half, runtron | results/traces/*.perfetto-trace, traces/rt-results.txt |
| D | cells | our half, rinzler | results/cells/, summary.md |
| E | 452b2052c9 with TRON_K_VNNI=OFF, 3 tests | /var/tmp/jhan/tron-i4500rm | results/build-fixS1rm.done |

## Cells of step D

Arms: base = canonical AMX deb (main 3faba6d0fd + AMX in the deb preset, row-major K); fix = yesterday's fix deb
(98a5accb8b); fixS1 = the policy deb; basekill / fixS1kill = the same with TRON_AMX_DISABLE=1 (tp4 only).
Cells: qwen-3-4b tp2 2 users and tp4 4 users at prompt 1024 (FPGA attention), llama-3.1-8b tp2 8 users at prompt 4096
(CPU attention; base and fixS1 only: the policy must leave it unchanged). REPS repetitions (4 by default at launch),
arms interleaved. Client: the nightly's own (systems_test testlib/tps.py: generate 1536, 10 rounds, TPS between
generated tokens 896 and 1024).

Expected if the reading is right: fixS1 within noise of base on both qwen cells (TPS), TTFT unchanged from fix
(the prefill path is untouched), llama unchanged from the fix (+8.5 % over base). The kill arms say whether the
per-section AMX tile-config bracket costs anything at tp4 in both builds.

## How to watch

    cat exec/logs/i4500b-20260930-chain.status; tail exec/logs/i4500b-20260930-chain.log
    cat exec/logs/i4500b-20260930.status; tail exec/logs/i4500b-20260930.log     # step D
    cat exec/results/i4500b-20260930/summary.md
