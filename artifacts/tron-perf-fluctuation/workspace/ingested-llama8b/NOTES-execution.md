# Execution notes — RUNBOOK-llama8b-tps-screen

Executor: Claude session, started 2026-08-15 01:13 UTC on alpha (claude-box).

## State

- [x] origin/main fetched: sha `1e1c03c571ba0012f67e5358c3287b1ec4ee12c3`
      (moved from e8deb5444; merge of PR #3789)
- [x] worktree `/home/jhan/workspace/tron-llama8b` @ 1e1c03c57
- [x] `config/models.local.yaml` copied from tron-kvprobe; deleted the two
      overrides `ingested_llama_3p1_8b` and `ingested_llama_3p1_8b_permuted`
- [x] HF-401 blocker resolved via runbook option 1: trace dir copied from
      `/scratch/jhan/pr3244/base/ingest/traces/ingested-llama-3.1-8b`
      (metadata.json 5057435 B, root.fx 335310 B, torch-export.stamp present;
      embed shape 128256x4096 = Llama-3.1-8B)
- [ ] build (attempt 2 running since ~01:25 UTC)
  - Attempt 1 FAILED: ninja re-ran the torch export despite the copied
    torch-export.stamp (fresh worktree has no .ninja_log entry for the edge,
    so ninja treats it as dirty) and hit the known HTTP 401 on the gated
    `meta-llama/Llama-3.1-8B-Instruct` repo. Copied trace files survived.
  - Resolution (variant of runbook option 1): `build-model.py` resolves the
    HF id to `WEIGHTS_ROOT=/opt/positron/weights/huggingface/<id>` when that
    local path exists, and `--meta-device` export only reads config.json
    (AutoConfig + from_config; no weights). Staged config.json,
    generation_config.json, tokenizer{,_config}.json, special_tokens_map.json,
    model.safetensors.index.json from 3bda's weights store to the same path
    on alpha (container-local /opt). Export now runs genuinely offline-from-HF
    and rewrites the trace with stock latest-main code.
  - Post-build check planned: diff fresh metadata.json vs the pr3244 copy
    (shape identity).
- [x] build OK (attempt 2, BUILD_EXIT=0). Fresh export's metadata.json:
      291 params, shapes + range_constraints identical to pr3244 copy.
- [x] deployed to /scratch/jhan/perf-fluctuation/deep-dive/install-llama8b-stock
      (bin/runtron, lib/libversion.so, lib/libfuse3.so.4); ldd on 3bda:
      0 not-found.
- [x] EXPECTED_BIN_SHA = 4bc21f38d787c1014094596c04bdd4f4e0693ad459b9bcb969a7bb25dc98deb9
- [x] PREFLIGHT_ONLY=1 run on 3bda at 01:32 UTC: PREFLIGHT OK (window,
      runner idle, binary hash, tools, storage, sudo)
      root: preflight-llama8b-20260815T013203Z
- [ ] campaign A tp4 (SLICE_OF=2)
  - Attempt 1 (3bda-llama8b-tp4-20260815T113251Z): HARD SMOKE FAILURE
    ('no bitfile lines', runtron hung after hugepage-allocation line, killed
    at 120 s gate). Harness exit 1, restore verified 11:37:28.
    ROOT CAUSE (from peer session trace-sync-points-7a via cross-session
    message): collision with their lowfreq-20260815T113207Z campaign launched
    11:32:16 on the same host — both harnesses' preflights passed inside the
    ~60 s traffic-gate window, then mutual cleanup/teardown killed both
    smokes. Neither failure indicates a model/build problem.
  - Coordination agreed: this session goes first (tp4 then tp2); peer waits
    for my "3bda free" message, then runs their ~35 min lowfreq campaign.
  - Pre-launch guard adopted for campaign B: no runtron process, no campaign
    root with mtime < 3 min under deep-dive/ or pfgate-3bda/.
  - Weights presence confirmed on 3bda before relaunch:
    default_weights thesven/Meta-Llama-3.1-8B-Instruct-GPTQ staged in both
    /opt/positron/weights/huggingface/thesven/ and
    /opt/positron/weights_cache/cached/thesven/ (no first-launch download).
  - Attempt 2 launched 11:39:56 UTC: 3bda-llama8b-tp4-20260815T113956Z
- [x] campaign A tp4 attempt 2 VERIFIED: exit 0, status restored, 20/20 ok,
      token_sha256 identical across all draws
      (3831fb161958c9c213a5185622fa504abddd55172c14807c8b136702d95349ae).
      Stats (sample sd): mean 205.129 tok/s, sd 2.953, CV 1.44%,
      min 200.978, max 212.866, gap 5.80%, per-token sd 69.6 us.
      Classification: FLUCTUATES (CV >= 1.0% and gap >= 3%).
      results.csv archived to data/results-tp4-20260815T113956Z.csv.
- [x] campaign B tp2 VERIFIED: exit 0, status restored, 20/20 ok,
      token_sha256 identical across all draws
      (6ee9697e3a56075661a381b240e981e7541669c6cbbc0a54455c995de4700055).
      Stats (sample sd): mean 162.506 tok/s, sd 1.095, CV 0.67%,
      min 160.517, max 164.503, gap 2.45%, per-token sd 41.4 us.
      Classification: TIGHT (CV < 1.0% and gap < 3%).
      results.csv archived to data/results-tp2-20260815T120428Z.csv.
      Campaign: 3bda-llama8b-tp2-20260815T120428Z (launched 12:04:28 UTC).
- [x] report written: status_report/report.md
- [x] peer session (uds:/tmp/cc-socks/7102.sock) notified "3bda free" at
      ~12:25 UTC; peer confirmed taking the machine for their lowfreq
      campaign. All monitors stopped.

## Mixtral follow-up (owner-approved 2026-08-15 ~15:28 UTC)

Three campaigns, same binary install-llama8b-stock (build 1e1c03c57, sha
4bc21f38...), 20 draws each, delphi-3bda:

1. mixtral-8x7b-instruct-v0.1-tp4 (hand-authored, fp16):
   3bda-mixtral-tp4-20260815T152808Z — VERIFIED exit 0, restored, 20/20,
   sha 865824c57a84...a08924. mean 150.907, sd 3.670, CV 2.43%,
   min 143.030, max 156.664, gap 9.03%. FLUCTUATES / matrix ROLLS —
   FIRST hand-authored model to roll.
2. ingested-mixtral-8x7b-instruct-v0.1-tp4:
   3bda-ingmixtral-tp4-20260815T155824Z — VERIFIED exit 0, restored, 20/20,
   sha fd612763d695...ba3902. mean 105.490, sd 1.169, CV 1.11%,
   min 102.195, max 106.817, gap 4.38%. FLUCTUATES (screen rule); between
   TIGHT/ROLLS bands under matrix rule. ~30% slower than hand-authored.
3. ingested-mixtral-8x7b-instruct-v0.1-tp2:
   3bda-ingmixtral-tp2-20260815T163100Z — VERIFIED exit 0, restored, 20/20,
   sha bfc59d4f73f7...69fa1a. mean 94.290, sd 0.132, CV 0.14%,
   min 94.009, max 94.503, gap 0.52%. TIGHT.

Conclusion: confound broken — parallelism degree (tp4), not ingestion,
drives the fluctuation for Mixtral. Report:
status_report/report-mixtral-ab.md. Notion matrix + markdown block updated
with all three rows. Peer notified "3bda free" 2026-08-15 ~17:00 UTC; peer
recorded the finding in intra-pass/CONTEXT.md section 5c and reports
converging wcls-bypass correlations on 4-card coordination paths
([open->F1] r=-0.81, intra-pass span r=-0.86). results.csv + identity.env
for all three archived in data/.

2026-08-16 update (peer session): host DRAM bandwidth EXCLUDED
(3bda-drambw-tp4-20260816T195258Z; ceiling ~220 GB/s reads/socket, decode
mean 11.5-14.4% of ceiling, busiest-second 28-30%, corr(TPS, bw) = +0.57
i.e. bandwidth follows throughput). Exclusion ledger: wcls pipeline,
CPU freq/power, ingestion, host DRAM bandwidth. Peer report:
../intra-pass/status_report/2026-08-16-01-dram-ceiling.html.

Purpose: break the ingested/hand-authored vs ROLLS/TIGHT confound with a
same-model same-weights A/B at tp4; row 3 tests ingestion at tp2.

Peer context (trace-sync-points-7a, 2026-08-15): lowered_freq analysis
EXCLUDES frequency/power as the fluctuation cause (zero 0x64F throttle
reasons, busy clocks flat 3737-3770 MHz, slow draws burn MORE power at
higher clocks). Report: ../intra-pass/status_report/
2026-08-15-01-lowered_freq.html. Context only, different campaign family.

## Final verdict (2026-08-15, delphi-3bda, build 1e1c03c57)

- tp4 FLUCTUATES: CV 1.44%, gap 5.80% (n=20)
- tp2 TIGHT: CV 0.67%, gap 2.45% (n=20)
- Same tp2-tight/tp4-rolls pattern as qwen-3-4b: fluctuation follows the
  parallelism degree.

## Schedule

Now ~01:20 UTC; 3bda CI window 02:30-11:30 UTC (harness refuses to start
inside it). A campaign takes ~2-4 h, so starting now would overlap the window.
Plan: build+deploy now, launch campaign A after 11:30 UTC, campaign B after A
verifies (restored + 20/20 ok).

## Cross-session launch protocol (delphi-3bda), as of 2026-08-17

- Host-wide campaign lock: /var/tmp/jhan/3bda-campaign.lock (flock),
  introduced by peer session trace-sync-points-7a. Take it at launch time
  for any future campaign from this project.
- Pre-launch guard: no runtron process; no campaign root with mtime < 3 min
  under /scratch/jhan/perf-fluctuation/deep-dive/ or .../pfgate-3bda/;
  peer roots must show finished-epoch.txt + RESTORED before launching.
- Core-pinning hazard (peer finding, fpgastat-armB-20260817T114401Z):
  runtron pins TX driver threads to cores 3/4/5/6 (work_queue 24,
  worker 25, RX 147-150 on tp4 instance 0). Pinning any helper or
  instrumentation thread onto those cores HALVES TPS. CAPTURE=none runs
  are unaffected; relevant if this project ever uses CAPTURE=perf (note:
  deepdive-campaign.sh PERF_CPUS_CARD0 includes core 3 — system-wide
  perf record on those CPUs is sampling-only, but do not add pinned
  helpers there).

## Pre-campaign checks done

- CURRENT_CAMPAIGN = 3bda-wadefix-off-tp4-20260814T201252Z: finished,
  harness-exit-code 0, status restored -> no active campaign.
- ssh jhan@delphi-3bda reachable (BatchMode).
- Harness read (deepdive-campaign.sh): knobs MODEL/SLICE_OF/ROUNDS/CAPTURE/
  KVWAIT/INSTALL/EXPECTED_BIN_SHA/CAMPAIGN_ROOT confirmed; CI-window guard,
  runner-idle, traffic gate, binary-sha, bitfile-consistency, sw-attention
  banner, device-set gates all built in. tp2/SLICE_OF=4 -> NCARDS=2 ->
  EXPECTED_DEVS = 10:00.0 13:00.0 (first two BDFs), per harness logic.
