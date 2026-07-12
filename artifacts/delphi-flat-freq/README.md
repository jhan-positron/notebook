# delphi-flat-freq artifacts

Preserved copies of workspace tools that are hard to recreate. The live
(canonical) copies are on mutable NFS storage — these repo copies exist to
survive accidental workspace deletion. Update the repo copy whenever the
canonical one changes.

## flat_freq_utils.sh (v3, 2026-07-06)

- Canonical location:
  delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
  (NFS-shared; same path on delphi-3af6)
- What it is: SST-CP/SST-TF frequency-shape utilities for the delphi Xeon
  6962P hosts. `flat_freq_apply` (no args) = all 288 CPUs -> CLOS0, TF on
  (universal flat, 4100-class for <=20 busy cores/domain);
  `flat_freq_apply <cpulist>` = select mode, listed cores + HT siblings ->
  CLOS0 (4100-class), rest -> CLOS3 <= 2700;
  `flat_freq_apply_tiers <fast> <mid>` (v3 addition, 2026-07-06) = 3-tier
  mode, fast -> CLOS0 ~4100 / mid -> CLOS1 <=3900 / rest -> CLOS3 <=2700;
  `flat_freq_revert` = boot default; `flat_freq_status` = read-only state.
  Auto-detects the NOPASSWD isst binary per host (3bda: /opt copy, 3af6:
  workspace build). Header documents the measured grant constraints (4400
  only when all others <=2700; no 4200 rung).
- Verified: universal flat + select mode measured on both 3bda and 3af6
  (2026-07-02/03 experiment series); used for the 24h flat sweep, the
  TRON-80 run (3af6), the TRON-88 and 3-tier rounds (3bda), and the
  PR-3070 A/B/C ladder (3af6, 2026-07-09).
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md
  (created v2), handoffs/claude_20260702-20260709_debug-3bda-flat-freq-run-ci-tests.md
  (benchmark usage). Central results doc:
  delphi-3bda:/scratch/jhan/flat_freq_tests/README.md
- NOTE: frequency state applied by this tool does NOT survive a reboot.

## ../positron_perf_metrics.html (repo location: artifacts/positron_perf_metrics.html)

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/positron_perf_metrics.html
- Moved 2026-07-12 from docs/ to the artifacts/ root at user request (it is a
  cross-cutting tron/checkerboard/CI metrics doc, not delphi-flat-freq-specific).
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/positron_perf_metrics.html
  (authored 2026-07-12)
- What it is: the one-stop explainer of Positron performance metrics —
  per-request semantics (harmonic means, one-burst load model), request
  lifecycle SVGs (parse==prefill, generate=decode window, exact metric
  windows with file:line cites), CPU-vs-FPGA phase map (prefill attention
  is always CPU), checkerboard-vs-rinzler path contrast, per-request vs
  aggregate throughput (users x HM labeled as proxy only), and the
  industry-metric mapping (Artificial Analysis / Cerebras / Groq / MLPerf /
  Positron Atlas public benchmark) with URLs. Every claim labeled
  VERIFIED / PROXY / INFERRED. Consensus-reviewed by Claude + gpt-5.6-sol
  (3 PAL rounds, 2026-07-12); code facts from two source-verification
  passes over the tron/checkerboard checkouts.

## gen_tron_flatfreq.py

- Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/gen_tron_flatfreq.py
- Parses tron/config/resource-map.yaml (granite_rapids_6962p) and emits the
  exact isst command sequence for the boost-TRON-cores shape
  (--also-boost dev,rinzler,platform; --revert for boot restore). Also
  emits a physical-cores-only boost set (HT siblings folded, with sibling
  clock note) — used 2026-07-08/09 to independently validate the
  hand-derived flat_freq_apply argument for the
  https://github.com/positron-ai/tron/pull/3070 core map.
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md,
  handoffs/claude_20260702-20260709_debug-3bda-flat-freq-run-ci-tests.md.

## test-scripts/

- run_gpt_oss_single.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_gpt_oss_single.sh
  - What it is: instrumented single-config gpt-oss benchmark
  (env scrub, turbostat capture, self-contained run folder).
- run_24h_sweep.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_24h_sweep.sh
  - What it is: the full 11-model sweep (took ~50 h; llama-3.1-70b
  substituted for Hannah's llama-3.3-70b which is absent from tron main).
- run_tron80_subset_3af6.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_tron80_subset_3af6.sh
  - What it is: gpt-oss + 3B matrices under strict TRON-80
  shape on delphi-3af6 (~6.5 h).
- run_tron88_baseline_round_3bda.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_tron88_baseline_round_3bda.sh
  - What it is: baseline-matched round (gpt-oss +
  8B tp4/tp2, lengths 256-2048, users 2-32) under TRON-80+drivers (~2 h).
- run_tier3_baseline_round_3bda.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_tier3_baseline_round_3bda.sh
  - What it is: the same baseline-matched grid under the 3-tier shape
  (flat_freq_apply_tiers fast/mid/low, ~1 h) with a 3-probe tier-drift
  watch (2026-07-06 round).
- run_pr3070_baseline_round_3bda.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_pr3070_baseline_round_3bda.sh
  - What it is: baseline-matched grid under the PR-3070 (tron112) select
  shape on 3bda, RUNTRON_BIN pointed at the PR build. Staged 2026-07-08
  but never run — superseded by the A/B/C ladder on 3af6.
- run_pr3070_ladder_3af6.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_pr3070_ladder_3af6.sh
  - What it is: the A->B->C decomposition ladder for
  https://github.com/positron-ai/tron/pull/3070 (A main+flat, B PR+flat,
  C PR+matched select), re-asserting the shape between phases, per-phase
  turbostat/shape-watch/CSV export (~3 h).
- run_pr3070_ladder_BC_3af6.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_pr3070_ladder_BC_3af6.sh
  - What it is: the B+C rerun after the RPATH/libversion.so failure —
  bakes in the LD_LIBRARY_PATH fix for running the /scratch copy of the
  PR build on a non-build host (the 2026-07-09 results came from this).
- ci_workload_profile.sh (+ ci_profile_trace.cfg)
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/ci_workload_profile.sh
    and delphi-3bda:/scratch/jhan/tools/ci_profile_trace.cfg
  - What it is: plan-item-6b capture kit — profiles workload shape during a
  FULL CI/nightly run (observational only; refuses to run unless engine
  processes are already up, never starts/stops tron). Captures a perfetto
  system trace (sched_switch/waking + cpu_frequency/idle via
  /scratch/jhan/tools/tracebox), perf record -a -g + per-engine perf stat
  (run as root, which bypasses perf_event_paranoid=4 without a sysctl
  change), and before/after provenance (engine cmdlines, per-thread
  psr/wchan/ctxt-switch snapshots, turbostat, isst shape probes). Gates on
  the gpt-oss phase by default (--model/--any to change); --check = safe
  preflight. Analysis via /scratch/jhan/tools/trace_processor (SQL, on-host)
  or ui.perfetto.dev. Staged 2026-07-10; preflight verified against live
  engines on 3bda; not yet run for real (needs an approved CI window +
  cached sudo).
- run_window_round_3bda.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/run_window_round_3bda.sh
  - What it is: daytime-window checkerboard round (gpt-oss + 8B, baseline-
  matched grid) under the DEPLOYED tron80 shape — verify-only on shape,
  writes RUNNER_PGID for the yield monitor, cleans its own hugepage files.
  Staged 2026-07-11, not yet run (3bda's daytime GitHub-runner role was
  discovered first — needs a ci-runner.sh handover window).
- yield_monitor_3bda.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/yield_monitor_3bda.sh
  - What it is: auto-yield guard for window tests on the CI machine — kills
  the runner's process group and cleans hugepages on non-jhan login,
  rinzler/talos/foreign-runtron appearance, or deadline. TODO: add a
  Runner.Worker (GitHub job) trigger.
- apply_tron84_rinzler_AB.sh
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/scripts/apply_tron84_rinzler_AB.sh
  (drafted 2026-07-11; installation pending user go)
  - What it is: delayed applier for the rinzler-boost nightly A/B — waits
  for 02:55 UTC (post runner-stop), preflights (no Runner.Worker, strict
  tron80 present), applies tron84 (workers + rinzler 24,48,72,96 + sibs
  -> CLOS0), double readback for provenance. Baseline = Jul 10/11 tron80
  nightly pair.
- All benchmark runners scrub the SYSTEM_CONFIG/TRON_LOG_LEVEL/SPDLOG_LEVEL env landmines and
  set CHECKERBOARD_MEMLOCK_KB=197971044 (host limit < checkerboard's 200 GB
  default). The marked THE BENCHMARK COMMAND block in each is the exact
  manual invocation.
- Related handoffs: handoffs/claude_20260702-20260709_debug-3bda-flat-freq-run-ci-tests.md.

## docs/

- flat_freq_tests-README.md
  - Canonical: delphi-3bda:/scratch/jhan/flat_freq_tests/README.md
  - What it is: central results narrative, renamed to avoid clashing with this
  provenance file —
  run log, host-fault diagnosis + fix recipe, flat-vs-clamped and
  TRON-80-vs-flat comparison tables, manual how-to.
- ALLCORE_CEILING_HETERO_CLAUDE_20260702.md
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md
  - What it is: the measurement report behind the v2 recipes (RAPL-bound
  all-core ceiling, TF-on+assoc 4100x80, heterogeneous shapes, CLOS
  mechanism findings).
- PLAN_E5_TRON_TOKPS_20260702.md
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/PLAN_E5_TRON_TOKPS_20260702.md
  - What it is: the tokens/s A/B plan whose variants (V1 flat / V2 strict TRON /
  V3 +drivers) map to the runs executed 2026-07-03..05.
- distilled_knowledge_visual.html
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/distilled_knowledge_visual.html
  - What it is: distilled speed-select knowledge as a visual HTML page.
- core_power.html
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/core_power.html
  - What it is: distilled core-power (SST-CP) knowledge page.
- core_power_help_source_distill.md
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/core_power_help_source_distill.md
  - What it is: source distillation for the core-power knowledge page.
- system_perf_research_workflow_template.html
  - Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/tmp/system_perf_research_workflow_template.html
  - What it is: system-performance research workflow template. The canonical
    lives in a tmp dir, so this mirror is especially important.
- speed_select_intuition.html
  - Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/speed_select_intuition.html
    (authored 2026-07-06 in the "run CI tests" session, local Windows machine)
  - What it is: intuition explainer for the whole technology stack —
    turbo-freq/core-power as managers of the persistent CLOS table, the
    min-of-caps frequency model, silent table-rewriting switches, and the
    discrete grant rungs (4400/4100/2700, no 4200). All numbers are
    measured turbostat values from the 2026-07 benchmark rounds.
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md,
  handoffs/claude_20260702-20260709_debug-3bda-flat-freq-run-ci-tests.md,
  handoffs/codex_2026-06-22-2026-06-30_configure-xeon-6-core-speeds.md,
  handoffs/codex_2026-06-29-2026-06-30_explore-core-power-feature.md.
