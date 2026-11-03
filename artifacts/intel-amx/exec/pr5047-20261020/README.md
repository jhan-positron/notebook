# pr5047-20261020: does PR 5047 (Ben's refactor of the PR 4956 K-layout code) change throughput?

Short version. PR 5047 (branch bgamari/vnnik-1, two commits, head ade89a9d9c) is based on jhan's PR 4956 branch
(jhan-vnnik-1-layout, head a5697f86d3). The scripts here build four runtron binaries with one recipe on delphi-3bda, two
commits x two values of the CMake option TRON_K_VNNI, then compare them on our half of the machine: token identity (one
user, greedy) and throughput (8 users) on llama-3.1-8b (CPU attention), qwen3-4b and gpt-oss-120b (FPGA attention).

## Words used here

- tron = the inference program under test. runtron = its command-line tool. AMX = Intel tile-matrix instructions.
- the option = TRON_K_VNNI, the CMake option PR 4956 adds (K cache of 128-dim heads in the VNNI pair-interleaved layout). OFF in every preset.
- base = runtron built from PR 5047's base commit a5697f86d3 (= PR 4956 head), option OFF. head = the PR 5047 head ade89a9d9c, option OFF.
  basev / headv = the same two commits with the option ON. <arm>off = the same binary with the kill switch TRON_AMX_DISABLE=1 (not used by default).
- hw attn / FPGA attention = USE_HW_ATTN unset (qwen and gpt-oss score attention on the FPGA cards). CPU attention = USE_HW_ATTN=0 (llama).
- attention path stats = TRON_ATTN_STATS=1: runtron prints an exit report with AVX / AMX / FPGA K-token counts per layer.
- our half of 3bda = socket 1, cpus 72-143 and 216-287, FPGA cards 90/93/b9/bc (--instance 2,4 for tp2, --instance 1,2 for tp4).
- the lease = /run/lock/systems-test-ci.lease, held by the nightly CI. The pre-CI hold = 01:40-03:45 UTC, when no run of ours starts.
- the worktrees = /var/tmp/jhan/tron-b47b, tron-b47h, tron-b47bv, tron-b47hv (3bda-local checkouts of the shared repo).

## Files

- build.sh (first run; its define-count check had a bug, fixed in build2.sh which the chain now calls): ON 3bda. One commit + one option value -> worktree /var/tmp/jhan/tron-$TAG, plain-shell build (host clang 19 + ccache),
  targets runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit; checks (option value in the cache and compile_commands.json,
  tdpbf16ps present, TRON_ATTN_STATS literal); a best-effort compile of t_heterogeneous_scheduler (the test that broke PR 5047's
  GitHub "Build Tron" check: t/heterogeneous_scheduler_compile.cpp:688 still calls the removed page::k), recorded in hetero-$TAG.txt.
- smoke.sh: ON 3bda, chain step I, once per identity cell: 1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, --dont-stop;
  arms base head head2 basev headv; MUST_MATCH = head:head2 head:base headv:basev (expected identical: PR 5047 is a refactor);
  INFO_PAIRS = headv:head (the two readers add in a different order, a difference is expected).
- campaign.sh: ON 3bda, chain step D. Four binaries, per-cell arms (field 8 of the cell table), REPS 4, arm order alternating per
  repetition, TRON_ATTN_STATS=1 in every arm, per-run timeout 2400 s; guards, watcher, idle-serving takeover through platformd, leaf
  poller and exit-report collection as in exec/glimext-20261018/campaign.sh. SKIP_SERVING_UP=1 (the chain restores).
- tests.sh: ON 3bda, chain step T (after D). The head builds' three test binaries (b47h and b47hv) + t_amx_numerics of b47h under the kill switch.
- chain.sh: ON 3bda, detached. Steps B (four builds in parallel; an option-on build failure drops the arms basev/headv), I, D, T, R
  (gen_report.py -> results.md/results.json). Deadline 01:30 UTC; a missed deadline sleeps until NOT_BEFORE (default
  2026-10-21T13:30:00Z) and resumes with done runs skipped. Production serving is brought back before a long sleep and at exit.
- gen_report.py: the report. Perf decision rule: paired head - base per repetition; band = twice the larger arm sd, at least 0.4 TPS /
  0.15 s; "holds" = TPS delta >= -band and prefill delta <= +band; "gain" = TPS delta > +band; else "DEGRADATION beyond the band".
- launch.sh: from claude-box: `bash launch.sh check` (file + syntax checks against the 3bda view) and `bash launch.sh chain`.

## How to launch (by hand on 3bda, one line)

    setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr5047-20261020/chain.sh >/dev/null 2>&1 </dev/null &

Optional variables: NOT_BEFORE=2026-10-21T13:30:00Z, STEPS="B I D T R", REPS=4, CELLS="<keys>", ARM_FILTER="basev headv".

## Cells

Perf (key|model|tp|users|prompt|attn|len|arms), run order:

    l8b-tp2-8u-p1024-cpu     llama-3.1-8b-instruct-good-tp2        2 8 1024 cpu  256  base head basev headv
    q4b-tp2-8u-p1024-fpga    ingested-qwen-3-4b-instruct-2507-tp2  2 8 1024 fpga 256  base head basev headv
    gptoss-tp4-8u-p1024-fpga ingested-gpt-oss-120b-tp4             4 8 1024 fpga 256  base head   (64-dim heads: the option never applies)
    l8b-tp2-8u-p8192-cpu     llama-3.1-8b-instruct-good-tp2        2 8 8192 cpu  256  base head basev headv
    q4b-tp2-8u-p8192-fpga    ingested-qwen-3-4b-instruct-2507-tp2  2 8 8192 fpga 256  base head basev headv
    l8b-tp2-8u-p4096-cpu     llama-3.1-8b-instruct-good-tp2        2 8 4096 cpu  256  base head

Identity (key|model|tp|attn|prompt|arms|must-match|info): l8b-tp2-cpu-p1024 and q4b-tp2-fpga-p1024 (base head head2 basev headv;
head:head2 head:base headv:basev; info headv:head), gptoss-tp4-fpga-p1024 (base head head2; head:head2 head:base).

## Where results land

- exec/results/pr5047-20261020/: build-b47*.{done,txt}, build-symbols-*.txt, hetero-*.{txt,log}, smoke/<key>/, identity.{txt,done},
  rt-results.txt, rt/<run>.log, leaves/, exit-reports.txt, tests.{done,txt}, tests/, results.{md,json}, chain.done.
- exec/logs/: pr5047-20261020-build-b47*.log, -tests.log, -chain.log (+ .status), pr5047-20261020.log (campaign, + .status, .done).

## Stop

On 3bda: during D `kill -TERM $(pgrep -f 'pr5047-20261020/campaign[.]sh')` (campaign.sh restores its own state on TERM); during I
first `kill -TERM $(pgrep -f 'pr5047-20261020/smoke[.]sh')` and then the runtron it started,
`pkill -TERM -u jhan -f '^/var/tmp/jhan/tron-b47[bh]v?/gen/runtron\.b47[bh]v? '`. Then `kill -TERM $(pgrep -f 'pr5047-20261020/chain[.]sh')`
(the chain's exit handler brings production serving back). Never pkill -f a pattern that appears in your own ssh command line.

## Traps

- Never edit a script while a copy of it runs on 3bda (NFS: bash reads the file incrementally). Fixes go into a NEW file name.
- NFS attribute cache: a file edited on claude-box can be stale on 3bda for up to a minute; launch.sh compares md5 sums.
- platformd 0.11 restarts rinzler@N units stopped with systemctl; takeover and restore go through lib-guard.sh
  rinzler_takeover_if_idle and dut.sh serving-up (platformd API).
- Dry run of 2026-10-21 00:07 UTC (stub sandbox, one forced build failure): every step and marker appeared; ARM_FILTER dropped basev/headv.
