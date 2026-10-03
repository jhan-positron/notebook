# attnstats-20261002: attention path stats of tron main, AMX kernel enabled vs disabled, three models

Short version. jhan asked (2026-10-01) for a machine test on delphi-3bda after the nightly CI of 2026-10-02:
tron main with the AMX kernel compiled in (TRON_AMX_DISPATCH=ON), run with the attention path stats on
(TRON_ATTN_STATS=1), once with the kernel enabled and once disabled by the kill switch (TRON_AMX_DISABLE=1), on
llama-3.1-8b-instruct-good tp2, gpt-oss-120b tp4 and qwen-3-4b tp2. The output is attn-stats-compare.md: how much
of the attention work ran on AMX, AVX and the FPGA in each arm, for attention on the FPGA (gpt-oss, qwen3), pure
software attention (llama) and the fitting (llama, qwen3) vs non-fitting (gpt-oss) kernel shape.

Words used here: tron = the inference program under test; runtron = its command-line tool; the lease =
/run/lock/systems-test-ci.lease (nightly CI); our half = socket 1 + FPGA cards 90/93/b9/bc of delphi-3bda;
amxon = TRON_AMX_DISABLE unset; amxoff = TRON_AMX_DISABLE=1; attn=cpu = USE_HW_ATTN=0 (software attention);
attn=fpga = USE_HW_ATTN unset (the model default: FPGA attention for generated plugins, CPU for llama);
attn=fpga1 = USE_HW_ATTN=1 (FPGA attention forced on, engagement point 127, used for the llama control).

## Files

- chain.sh: runs ON delphi-3bda, detached. NOT_BEFORE 2026-10-02T13:00:00Z, then waits for the lease (600 s grace),
  other people and blackouts. Steps F (fetch origin/main, record RES/main.sha), A (build runtron.main1002 in
  /var/tmp/jhan/tron-main1002 through exec/i4525-20260922/build2.sh; refuses a binary without AMX tile instructions),
  D (campaign.sh), R (gen_compare.py -> RES/attn-stats-compare.md, copied to PR3879/new-PRs/new-counters/).
- campaign.sh: fork of exec/attnstats-20260924/campaign.sh. One binary, arms = environments, attention mode and
  generated length per cell, a FUSE leaf poller per run (RES/leaves/<run>/). Guards, watcher, pre-CI hold, idle-serving
  takeover through platformd and the serving restore are unchanged from the parent.
- gen_compare.py: parses rt-results.txt and rt/<run>.log, writes the Markdown report (tables + templated sentences).
- launch.sh: run from claude-box; checks NFS visibility and syntax, then starts chain.sh on 3bda with setsid nohup.

## Cells (key|model|tp|users|prompt|attn|len), arms amxon / amxoff, REPS 1

jhan's final list (2026-10-02): 6 cells, 12 runs.

    l8b-8u-p1024-cpu     llama-3.1-8b-instruct-good-tp2          2 8 1024 cpu  256   (pure software attention)
    gptoss-8u-p1024-fpga ingested-gpt-oss-120b-tp4               4 8 1024 fpga 256   (attention on the FPGA, non-fitting shape)
    q3-4b-8u-p1024-fpga  ingested-qwen-3-4b-instruct-2507-tp2    2 8 1024 fpga 256   (attention on the FPGA, fitting shape)
    q3-4b-8u-p1024-cpu   ingested-qwen-3-4b-instruct-2507-tp2    2 8 1024 cpu  256   (control: fitting shape under software attention)
    l8b-8u-p8192-cpu     llama-3.1-8b-instruct-good-tp2          2 8 8192 cpu  256
    q3-4b-8u-p8192-fpga  ingested-qwen-3-4b-instruct-2507-tp2    2 8 8192 fpga 256

Dropped by jhan: gpt-oss CPU-attention cells (gpt-oss always runs AoF), gpt-oss at prompt 8192, the llama USE_HW_ATTN=1
cells (llama is not AoF), qwen CPU attention at prompt 8192.

Build: `cmake --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON` (the cross-avx512 preset was removed
from main on 2026-09-30, commit 8d64eeed81).

Kernel shape rule at main 9c88327931: the AMX kernel compiles only for head size 128 and 4 query heads per KV head
[h/tron/kernels/amx_attn_iface.hpp:148-150]; llama-3.1-8b and qwen3-4b fit, gpt-oss-120b (head 64, 8 per KV head)
does not, so gpt-oss must show 0 AMX visits in both arms. gpt-oss has 36 layers: 18 full-attention layers are FPGA
candidates (hw_slots 18), 18 sliding-window layers (window 128) always run in software.

Expected cost: about 2 min per run at prompt 1024 (model load dominates; gpt-oss-120b loads in about 80 s) and
4-6 min at prompt 8192, 12 runs, about 1 h plus the takeover wait.

## Results

exec/results/attnstats-20261002/: main.sha, build-main1002.{txt,log}, rt-results.txt, rt/<run>.log(.attemptN),
leaves/<run>/, exit-reports.txt, attn-stats-compare.md. Logs: exec/logs/attnstats-20261002-chain.log (+ .status),
exec/logs/attnstats-20261002.log (campaign, + .status, .done).

## How to run or resume

Two launches: a build-only pass on the evening of 2026-10-01 (`NOT_BEFORE=2026-10-02T01:00:00Z STEPS="F A"`,
proves the native-preset build before the pre-CI hold at 01:40 UTC), then the full chain for the morning
(`STEPS="F A D R"`, NOT_BEFORE 13:00 UTC; step F re-fetches main and step A rebuilds only when main moved).

    bash exec/attnstats-20261002/launch.sh                    # default NOT_BEFORE 2026-10-02T13:00:00Z
    NOT_BEFORE=now STEPS="D R" bash exec/attnstats-20261002/launch.sh   # resume: done steps are skipped

Resume after failed runs: the campaign marker `ok-with-N-failed-runs` makes the chain re-enter campaign.sh, which
reruns only the runs without a complete log.

Stop on 3bda: `kill -TERM $(pgrep -f 'attnstats-20261002/campaign[.]sh')` (campaign.sh restores serving on TERM),
then `kill -TERM $(pgrep -f 'attnstats-20261002/chain[.]sh')`. Never pkill -f a pattern that appears in your own
ssh command line (the ssh shell matches itself).
