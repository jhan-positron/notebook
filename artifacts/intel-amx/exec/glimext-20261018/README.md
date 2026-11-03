# glimext-20261018: extended test of PR #5015 (AMX attention kernels for kv_mul 16) with and without the change

Short version. PR #5015 generalises the AMX attention kernels from kv_mul 4 to kv_mul 4 and 16 (Muse Glimmer 30B).
The scripts here build the PR's merge base and the PR head with one recipe on delphi-3bda, then compare the two
binaries on our half of the machine: token identity (one user, greedy) and throughput (8 users) on llama-3.1-8b,
qwen3-4b, gpt-oss-120b and Glimmer, plus a near-tie logits probe for the expected Glimmer divergence (issue #4444).

## Words used here

- tron = the inference program under test. runtron = its command-line tool.
- AMX = Intel tile-matrix instructions. The AMX kernel scores dense 64-token KV pages. The AVX software loop scores every other page.
- kv_mul = query heads per KV head. llama-3.1-8b has 4, Muse Glimmer 30B has 16, qwen3-4b has 4, gpt-oss-120b has 8 at head size 64 (never AMX).
- base = runtron built from main 6198824246, the PR's merge base ("without PR #5015"). head = runtron built from the PR head
  5061623a34 ("with PR #5015"). headoff = head with the kill switch TRON_AMX_DISABLE=1. head2 = head run a second time.
- hw attn / FPGA attention = USE_HW_ATTN unset, the model default: qwen and gpt-oss score attention on the FPGA cards;
  Glimmer sends its 13 full layers to the FPGA and runs its 39 sliding-window layers on the CPU. CPU attention = USE_HW_ATTN=0.
- attention path stats = TRON_ATTN_STATS=1: runtron prints an exit report with AVX / AMX / FPGA K-token counts per layer.
- our half of 3bda = socket 1, cpus 72-143 and 216-287, FPGA cards 90/93/b9/bc (--instance 2,4 for tp2, --instance 1,2 for tp4).
- the lease = /run/lock/systems-test-ci.lease, held by the nightly CI. The pre-CI hold = 01:40-03:45 UTC, when no run of ours starts.
- the worktrees = /var/tmp/jhan/tron-g16b (base) and /var/tmp/jhan/tron-g16h (head), 3bda-local checkouts of the shared repo.

## Files

- build.sh: ON 3bda. One commit -> worktree /var/tmp/jhan/tron-$TAG, plain-shell build (host clang 19 + ccache, the nix dev
  shell no longer builds on 3bda), targets runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit, three checks
  (tdpbf16ps present, TRON_ATTN_STATS literal, kernel symbols: base 4 lines, head 8 lines). Per-tag lock. Marker build-$TAG.done.
- tests.sh: ON 3bda, chain step T. The head's three test binaries + t_amx_numerics under the kill switch, on our half with
  the fake device (SYSTEM_CONFIG="--instance 1,2"); then the preservation check base plain kernels vs head <4> instantiations
  (same compiler this time). Marker tests.done.
- campaign.sh: ON 3bda, chain step D. Two binaries, arms base / head (env TRON_ATTN_STATS=1 in both), 9 cells, REPS 4,
  arm order alternating per repetition, per-run timeout 2400 s; guards, watcher, idle-serving takeover through platformd,
  leaf poller and exit-report collection as in exec/glimmer-20261016/campaign.sh. SKIP_SERVING_UP=1 (the chain restores).
- smoke.sh: ON 3bda, chain step I, once per identity cell: 1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens,
  arms base head head2 headoff; pairs head:head2, head:base, headoff:base, headoff:head; MUST_MATCH names the pairs that
  make the verdict. Outputs smoke/<key>/.
- margin.sh: ON 3bda, chain step E (only when head and base differ in the Glimmer CPU identity cell): two teacher-forced
  runs with --intermediates-file (tens of GB each, filtered to the 'Logits of token' lines and deleted), then
  exec/dd/dd_logits_step.py -> margin/steps-base-vs-head.json: the base arm's top-1 minus top-2 margin at the step where the
  free-running tokens first differed, in logit units and bf16 ulps, and the head arm's change of that pair.
- chain.sh: ON 3bda, detached. Steps B (both builds in parallel), T, I, D, E, R (gen_report.py -> results.md/results.json;
  exec/sync4424-20261002/summarize.py -> summary.md). Deadline 01:30 UTC; a missed deadline sleeps until NOT_BEFORE
  (default 2026-10-19T13:30:00Z) and resumes with done runs skipped. Production serving is brought back before a long
  sleep and at exit. Marker chain.done.
- gen_report.py: the report. Perf decision rule: paired head - base per repetition; band = twice the larger arm sd;
  "holds" = TPS delta >= -band and prefill delta <= +band; "gain" = TPS delta > +band; else "DEGRADATION beyond the band".
- launch.sh: from claude-box: `bash launch.sh check` (file + syntax checks against the 3bda view) and `bash launch.sh chain` (CHAIN=chain2.sh selects the resume chain; E_NOT_AFTER, E_MIN_HOURS, BASE_SHA, HEAD_SHA, MAX_CAMPAIGN_PASSES are forwarded).
- chain2.sh, smoke2.sh: the review-fixed copies (see Resume below).

## How to launch (by hand on 3bda, one line)

    setsid nohup bash /home/jhan/workspace/intel-AMX/exec/glimext-20261018/chain.sh >/dev/null 2>&1 </dev/null &

Optional variables: NOT_BEFORE=2026-10-19T13:30:00Z, STEPS="B T I D E R", REPS=4, CELLS="<keys>", E_NOT_AFTER=2026-10-19T00:00:00Z,
BASE_SHA / HEAD_SHA (defaults = the merge base and the PR head).

## Cells

Perf (key|model|tp|users|prompt|attn|len), run order:

    l8b-tp2-8u-p1024-cpu      llama-3.1-8b-instruct-good-tp2             2 8 1024 cpu  256   (kv_mul 4: AMX in both arms, same kernel)
    q4b-tp2-8u-p1024-fpga     ingested-qwen-3-4b-instruct-2507-tp2       2 8 1024 fpga 256   (FPGA attention: the PR does not touch this path)
    gptoss-tp4-8u-p1024-fpga  ingested-gpt-oss-120b-tp4                  4 8 1024 fpga 256   (head size 64: never AMX)
    l8b-tp2-8u-p8192-cpu      llama-3.1-8b-instruct-good-tp2             2 8 8192 cpu  256
    q4b-tp2-8u-p8192-fpga     ingested-qwen-3-4b-instruct-2507-tp2       2 8 8192 fpga 256
    gptoss-tp4-8u-p2048-fpga  ingested-gpt-oss-120b-tp4                  4 8 2048 fpga 256
    glm-tp2-8u-p1024-fpga     ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 1024 fpga 256   (base: AVX on 39 layers; head: AMX)
    glm-tp2-8u-p2048-fpga     ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 2048 fpga 256
    glm-tp4-8u-p1024-fpga     ingested-meta-models--Muse-Glimmer-30B-tp4 4 8 1024 fpga 256

Identity (key|model|tp|attn|prompt|must-match): l8b-tp2-cpu-p1024 (head:head2 head:base), q4b-tp2-fpga-p1024 (head:head2 head:base),
gptoss-tp4-fpga-p1024 (head:head2 head:base), glm-tp2-fpga-p1024, glm-tp2-cpu-p1024, glm-tp2-fpga-p2048, glm-tp4-fpga-p1024
(head:head2 headoff:base; head:base is informational, expected to differ per issue #4444).

## Where results land

- exec/results/glimext-20261018/: build-g16{b,h}.{done,txt}, build-symbols-*.txt, tests.{done,txt}, tests/, preservation.txt,
  smoke/<key>/, identity.{txt,done}, rt-results.txt, rt/<run>.log, leaves/, exit-reports.txt, margin/, margin.done,
  results.{md,json}, summary.md, chain.done.
- exec/logs/: glimext-20261018-build-g16{b,h}.log, -tests.log, -chain.log (+ .status), glimext-20261018.log (campaign, + .status, .done).

## Stop

On 3bda, by step: during D `kill -TERM $(pgrep -f 'glimext-20261018/campaign[.]sh')` (campaign.sh restores its own state on
TERM); during I or E first `kill -TERM $(pgrep -f 'glimext-20261018/(smoke2?|margin)[.]sh')` and then the runtron they
started, `pkill -TERM -u jhan -f '^/var/tmp/jhan/tron-g16[bh]/gen/runtron\.g16[bh] '` (these scripts have no TERM trap of
their own; the chain's trap waits for the child). Then `kill -TERM $(pgrep -f 'glimext-20261018/chain2?[.]sh')` (the chain's
exit handler brings production serving back). Never pkill -f a pattern that appears in your own ssh command line (the ssh
shell matches itself).

## Resume with chain2.sh

chain2.sh = chain.sh plus the fixes of the 2026-10-18 script review (step I loops over passes and detects a deadline
inside a cell, the failed-line count looks at the current pass only, step D checks the deadline first, step E has a
relative bound E_MIN_HOURS=3 before the deadline, step B re-checks the binaries, smoke2.sh = smoke.sh with --dont-stop).
The first chain ran from chain.sh and smoke.sh (never edited while running). To resume after a stop: `CHAIN=chain2.sh
STEPS='I D E R' bash launch.sh chain` from claude-box, or on 3bda
`STEPS='I D E R' setsid nohup bash /home/jhan/workspace/intel-AMX/exec/glimext-20261018/chain2.sh >/dev/null 2>&1 </dev/null &`.
Done steps and runs are skipped (markers, smoke.done, the TPS lines of rt/<run>.log).

## Traps

- Never edit a script while a copy of it runs on 3bda (NFS: bash reads the file incrementally; a replacement kills the
  running process with a stale file handle). Fixes go into a NEW file name.
- NFS attribute cache: a file edited on claude-box can be stale on 3bda for up to a minute; launch.sh compares md5 sums.
- `local a=$1 b="$a"` expands before assigning; the scripts here were grepped for the pattern and dry-run in a stub sandbox
  (chain with stubbed runtron/build/guard/dut; see the session notes of 2026-10-18).
- platformd 0.11 restarts rinzler@N units stopped with systemctl; takeover and restore go through lib-guard.sh
  rinzler_takeover_if_idle and dut.sh serving-up (platformd API).
- The margin step writes tens of GB to /var/tmp/jhan/glimext-margin/ (deleted after the filter); E_NOT_AFTER bounds its start.
