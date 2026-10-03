# i4500fix-20260928: build and measure the issue #4500 fix (row-major tail block for the VNNI K layout)

Short version. The fix for issue #4500 (commit f34b0fe2ec (head; 5 commits) on branch jhan-amx-vnniK-i4500, on top of the PR #4424
head 30c4ac82cb) keeps a 16-token K block row-major until its 16th row is saved and converts it in place. This
folder builds it, tests it and measures it on delphi-3bda, our half, after the nightly CI of 2026-09-29 (jhan
2026-09-28: "Rhys needs to use 3bda, please hold launching test, please schedule to use the machine tomorrow
morning after CI").

Words used here: tron = the inference program under test; runtron = its command-line tool; rinzler = the
production server; deb = the Debian package the nightly installs; VNNI K = the K cache layout of PR #4424;
AMX = the Intel matrix instruction set; our half = socket 1 and the FPGA cards 90/93/b9/bc of delphi-3bda;
the lease = /run/lock/systems-test-ci.lease, held by the nightly CI; TPS = decode tokens per second per user.

## Files

- chain.sh: the steps A to E below, detached on 3bda, gated by NOT_BEFORE (default 2026-09-29T13:00:00Z), the lease
  and other people's activity (lib-guard other_user_active; bill is excluded by the half-split agreement, anyone else
  makes the chain wait).
- launch.sh: run on claude-box; checks the files on 3bda (NFS attribute cache) and starts chain.sh there.
- lib.sh: waits, watcher, hugepage cleanup shared by smoke.sh and campaign.sh.
- build-deb.sh: the fix .deb from commit 8198eab4cc (= the 2026-09-18 ci-mimic target 29a8a54740, main 3faba6d0fd +
  PR #4424, plus the fix), extracted to /var/tmp/jhan/i4500fix-20260928/root; extracts the canon deb root too.
- smoke.sh: runtron token rows, fix vs the PR head vs fix again (A/A), CPU and FPGA attention, prompts 1024 and 1000.
- campaign.sh: the cells; st_perf2.py: the nightly's client with a --prompt-length override; summarize.py: the table.

## Steps of chain.sh

| step | what | where | result |
|---|---|---|---|
| A | build f34b0fe2ec (AMX + VNNI K + ingest models) and run 7 tests with the fake device | /var/tmp/jhan/tron-i4500 | results/build-fix.txt, tests-fix.txt, build-fix.done |
| B | build the fix deb | /var/tmp/jhan/tron-i4500deb | /var/tmp/jhan/i4500fix-20260928/{fix.deb,manifest.json,root/} |
| C | smoke | our half, runtron | results/smoke/smoke.txt |
| D | cells | our half, rinzler | results/cells/, summary.md |
| E | build the same commit with TRON_K_VNNI=OFF and run 3 tests | /var/tmp/jhan/tron-i4500rm | results/build-fixrm.done |

## Cells of step D

Binaries: base = canonical AMX (main 3faba6d0fd + AMX in the deb preset, row-major K), vnni = PR #4424 on the same
main (the package that showed the loss on 2026-09-18), fix = vnni + the fix, nightly = the installed nightly package
(today's main, for reference). Cells: qwen-3-4b tp2 with 2 users per engine and tp4 with 4 users per engine at prompt
1024 (the cells of block m6 on 2026-09-19, FPGA attention), llama-3.1-8b tp2 with 8 users per engine at prompt 4096
(CPU attention, the model's nightly mode). 3 repetitions, binaries interleaved. The client is the nightly's own
(systems_test testlib/tps.py: generate 1536 tokens, 10 rounds, TPS captured between generated tokens 896 and 1024).

Reference numbers to beat (block m6, 2026-09-19, n = 2): qwen tp2 2 users: vnni 183.9 vs base 192.2 TPS (-4.3 %);
qwen tp4 4 users: 135.4 vs 156.3 TPS (-13.4 %). The base there was the nightly deb without AMX; here the base is the
canonical AMX deb (+0.1 % / -2.6 % vs that nightly in the canon-ci run).

## How to watch

    cat exec/logs/i4500fix-20260928-chain.status; tail exec/logs/i4500fix-20260928-chain.log
    cat exec/logs/i4500fix-20260928.status; tail exec/logs/i4500fix-20260928.log     # step D
    cat exec/results/i4500fix-20260928/summary.md
