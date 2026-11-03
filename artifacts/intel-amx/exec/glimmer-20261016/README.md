# glimmer-20261016: Muse Glimmer kv_mul-16 AMX kernels, build / tests / measurement on delphi-3bda

Short version. Branch jhan-amx-kvmul16 makes the AMX attention kernels serve kv_mul 16, the shape of Muse Glimmer 30B.
The scripts here build that branch on delphi-3bda, run its three AMX test binaries, and then measure Glimmer and one
llama cell with the AMX kernel enabled and disabled, on our half of the machine. Every launch takes SHA=<full commit
sha> from the environment, and the machine steps wait for the other session's probe to finish.

## Words used here

- tron = the inference program under test. runtron = its command-line tool.
- AMX = Intel tile-matrix instructions. The AMX kernel scores dense KV pages. The AVX software loop scores every other page.
- kv_mul = query heads per KV head. llama-3.1-8b has kv_mul 4. Glimmer has 32 query heads, 2 KV heads, head size 128,
  so kv_mul 16.
- Muse Glimmer 30B = ingested-meta-models--Muse-Glimmer-30B (runtron names -tp2 and -tp4), the production ingested
  plugin, GPTQ weights in the 3bda cache. 52 layers: 39 sliding-window layers (window 2048 tokens) that always run on
  the CPU, 13 full layers that go to the FPGA when USE_HW_ATTN is unset (hw_slots 13).
- the kill switch = TRON_AMX_DISABLE=1 (same binary, every page through the AVX loop). amxon = the switch unset.
  amxoff = the switch set.
- attention path stats = TRON_ATTN_STATS=1. runtron prints an exit report with AVX / AMX / FPGA visit counts per layer.
- AoF = attention on the FPGA. attn=fpga = USE_HW_ATTN unset (the model default). attn=cpu = USE_HW_ATTN=0.
- our half of 3bda = socket 1, cpus 72-143 and 216-287, FPGA cards 90/93/b9/bc (--instance 2,4 for tp2, --instance 1,2
  for tp4). The other half may be Bill's.
- the lease = /run/lock/systems-test-ci.lease, held by the nightly CI. The pre-CI hold = 01:40-03:45 UTC, when no run
  of ours starts.
- the probe markers = exec/results/td-20261016/probe.done, td2-20261016/probe.done and td3-20261016/probe.done.
  Another session's whole-machine probe writes one per round when that round is finished. Its probe removes the
  hugepage slice files between its runs, and our tests and runs use those files, so nothing of ours overlaps with it.
  tests.sh waits for the first marker only. chain.sh step G waits for all of them (WAIT_MARKERS, see below).
- the go file = exec/glimmer-20261016/go.marker. jhan creates it by hand after the other session says it is done.
- the worktree = /var/tmp/jhan/tron-g16, a 3bda-local checkout of the shared repo /home/jhan/workspace/tron at SHA.
- g16 = the tag of this build. The binary is /var/tmp/jhan/tron-g16/gen/runtron.g16.
- main1010 = /var/tmp/jhan/tron-main1010/gen/runtron.main1010, tron main 72308ec90c, the reference for the
  preservation check.

## Files

- build.sh: runs ON 3bda, detached. Worktree at SHA, copy of the ingest traces, configure
  `cmake --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON` inside nix develop, build runtron
  t_amx_numerics t_amx_dispatch_dtype t_llama_unit with `nice -n10 taskset -c 72-143,216-287` and -j20, copy
  gen/runtron to gen/runtron.g16, then three checks: tdpbf16ps in the disassembly (count > 0), the TRON_ATTN_STATS
  literal in the binary, and 6 kernel template symbols (pack_q_group_128x4, qk_rowmajor_128x4, weights_times_v_128x4,
  each as <4> and <16>). Marker exec/results/glimmer-20261016/build.done = "ok" or "failed: <why>".
- tests.sh: runs ON 3bda, called by chain.sh step T. Waits for the first probe marker, no jhan runtron, no pre-CI hold, a
  clear lease, no other person. Then runs the three test binaries pinned to our half with SYSTEM_CONFIG="--instance 1,2"
  (the fake device), plus t_amx_numerics again with TRON_AMX_DISABLE=1. The kill-switch run passes only when rc is 0 and
  the log has at least one "AMX unavailable" skip line. Writes tests.txt ("name | assertions | rc | ..."),
  tests/<name>.log and preservation.txt (best effort, not gating). Marker tests.done = "ok" or "failed-<n>".
- chain.sh: runs ON 3bda, detached. Steps B (wait for build.done ok), T (tests.sh), G (wait for every probe marker in
  WAIT_MARKERS and the go file), D (campaign.sh), R (gen_compare.py). Marker exec/results/glimmer-20261016/chain.done.
- campaign.sh: fork of exec/attnstats-20261002/campaign.sh. One binary, arms as environments, 9 cells, REPS 2, per-run
  timeout 2400 s. Guards, watcher, pre-CI hold, idle-serving takeover through platformd, leaf poller, exit-report
  collection and the serving restore are unchanged from the parent.
- gen_compare.py: rt-results.txt and rt/<run>.log to attn-stats-compare.md (stdout) and results.json (in the results
  dir). fits() accepts kv_mul 4 and 16 at head 128. Section 5 checks the per-layer pattern against the Glimmer
  expectation. Section 6 is the performance table over every repetition.
- launch.sh: optional launcher from claude-box (checks the NFS copies and the syntax, then starts build.sh or chain.sh
  on 3bda with setsid nohup). jhan may use the by-hand commands below instead.

## How to launch (by hand on 3bda, one line each)

Build, as soon as the commit exists (the chain's step B waits for it):

    SHA=<full sha> setsid nohup bash /home/jhan/workspace/intel-AMX/exec/glimmer-20261016/build.sh >/dev/null 2>&1 </dev/null &

Chain (build-wait, tests, go-wait, campaign, report):

    SHA=<full sha> setsid nohup bash /home/jhan/workspace/intel-AMX/exec/glimmer-20261016/chain.sh >/dev/null 2>&1 </dev/null &

Go file, after the other session says it is finished:

    touch /home/jhan/workspace/intel-AMX/exec/glimmer-20261016/go.marker

Both scripts append to their own logs, so the shell redirections above are only for the detach. Optional variables:
NOT_BEFORE=2026-10-17T13:00:00Z (default), STEPS="B T G D R" (default), REPS=2 (default), CELLS="<keys>" (a subset of
the table), JOBS=20 (build.sh), KSYM_RE / KSYM_N (build.sh symbol check), TESTS_WAIT_MARKERS (tests.sh, default the
first probe marker), WAIT_MARKERS (chain.sh step G, default the three probe markers; a fourth round is added at launch:
`WAIT_MARKERS="/home/jhan/workspace/intel-AMX/exec/results/td-20261016/probe.done ... /home/jhan/workspace/intel-AMX/exec/results/td4-20261016/probe.done"`,
never by editing the running script).

From claude-box instead: `SHA=<sha> bash exec/glimmer-20261016/launch.sh build` and `... launch.sh chain`.

## Order and conditions

    build.sh (by hand)                 chain.sh (by hand)
    worktree at SHA ----------------> B: wait build.done = ok
    configure + build 4 targets       T: tests.sh (waits: first probe marker, no jhan runtron, no pre-CI hold, lease clear)
    3 checks -> build.done            G: wait all probe markers (td, td2, td3) + go.marker; deadline 01:30 UTC
                                         missed -> sleep until NOT_BEFORE (default 2026-10-17T13:00:00Z), wait lease
                                      D: campaign.sh (9 cells x amxon/amxoff x REPS 2 = 36 runs)
                                         campaign stops at 01:30 UTC -> chain sleeps until NOT_BEFORE, resumes (done runs skipped)
                                      R: gen_compare.py -> attn-stats-compare.md + results.json

Cells (key|model|tp|users|prompt|attn|len), in run order:

    l8b-tp2-8u-p1024-cpu   llama-3.1-8b-instruct-good-tp2            2 8 1024 cpu  256   (kv_mul 4, the unchanged path)
    glm-tp2-8u-p1024-fpga  ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 1024 fpga 256
    glm-tp2-8u-p2048-fpga  ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 2048 fpga 256
    glm-tp2-8u-p1024-cpu   ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 1024 cpu  256
    glm-tp2-8u-p2048-cpu   ingested-meta-models--Muse-Glimmer-30B-tp2 2 8 2048 cpu  256
    glm-tp4-8u-p1024-fpga  ingested-meta-models--Muse-Glimmer-30B-tp4 4 8 1024 fpga 256
    glm-tp4-8u-p2048-fpga  ingested-meta-models--Muse-Glimmer-30B-tp4 4 8 2048 fpga 256
    glm-tp4-8u-p1024-cpu   ingested-meta-models--Muse-Glimmer-30B-tp4 4 8 1024 cpu  256
    glm-tp4-8u-p2048-cpu   ingested-meta-models--Muse-Glimmer-30B-tp4 4 8 2048 cpu  256

Arms: amxon = TRON_ATTN_STATS=1; amxoff = TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1. The two arms of one cell run back to
back inside every repetition. A run whose log already has the TPS lines is skipped, so a relaunch resumes.

Expected per-layer pattern (section 5 of the report checks it): amxon with attn=fpga shows AMX visits on the 39 sliding
layers only, and FPGA K tokens plus a small AVX tail on the 13 full layers. amxon with attn=cpu shows AMX on all 52
layers. amxoff shows AMX on no layer. llama shows AMX on all 32 layers under amxon.

## Where results land

- exec/results/glimmer-20261016/: build.done, build.txt, build-symbols.txt, tests.done, tests.txt, tests/<name>.log,
  preservation.txt, rt-results.txt (one "### runtron" header per run, then the grep of its log), rt/<run>.log
  (.attemptN = raw attempts), leaves/<run>/ (FUSE leaf snapshots), exit-reports.txt, attn-stats-compare.md, results.json,
  chain.done.
- exec/logs/: glimmer-20261016-build.log, glimmer-20261016-tests.log, glimmer-20261016-chain.log (+ .status),
  glimmer-20261016.log (campaign, + .status, .done).

## Stop

On 3bda: `kill -TERM $(pgrep -f 'glimmer-20261016/campaign[.]sh')` (campaign.sh restores serving on TERM), then
`kill -TERM $(pgrep -f 'glimmer-20261016/chain[.]sh')`. Never pkill -f a pattern that appears in your own ssh command
line (the ssh shell matches itself).

## Traps

- Never edit a script while a copy of it runs on 3bda. bash reads the file incrementally over NFS, and any replacement
  (editor save, sed -i, mv) kills the running process with a stale file handle. Fixes go into a NEW file name
  (build2.sh, chain2.sh, ...) and the new name is launched. Python files are read whole at start and may be edited
  between runs.
- NFS attribute cache: a file edited on claude-box can be stale on 3bda for up to a minute. launch.sh compares md5 sums
  on both hosts before starting anything. build.sh waits up to 5 min for the commit to appear in the shared object store.
- `local a=$1 b="$a"` expands every word before any assignment (under set -u it aborts). One local per dependent
  assignment; the scripts here were grepped for the pattern and dry-run in a stub sandbox.
- platformd 0.11 restarts rinzler@N units stopped with systemctl within a minute. The takeover in campaign.sh goes
  through lib-guard.sh rinzler_takeover_if_idle (platformd API), and the restore through dut.sh serving-up.
- The nightly CI never stops its rinzler@N units. campaign.sh waits for the lease, then takes idle serving down through
  platformd and brings it back in finish().
- Never `git worktree prune` the shared repo from claude-box: the 3bda worktrees under /var/tmp/jhan are invisible
  there and would be pruned. If /var/tmp/jhan/tron-g16 exists at another commit, build.sh fails and says so; remove the
  worktree by hand on 3bda.
- build.sh symbol check: if the branch names the kernel templates differently, build.sh fails with the count; relaunch
  it with KSYM_RE=<regex> KSYM_N=<count> (the worktree and the build are reused).
- The dry run used a bash script as the fake runtron, so its command line starts with "bash" and the watcher, the
  leaf poller and kill_ours never matched it (their pattern anchors on the binary path). On 3bda runtron is an ELF
  binary and the pattern matches, as in every earlier campaign of this template.
