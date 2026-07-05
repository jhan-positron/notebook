# delphi-flat-freq artifacts

Preserved copies of workspace tools that are hard to recreate. The live
(canonical) copies are on mutable NFS storage — these repo copies exist to
survive accidental workspace deletion. Update the repo copy whenever the
canonical one changes.

## flat_freq_utils.sh (v2, 2026-07-03)

- Canonical location:
  delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
  (NFS-shared; same path on delphi-3af6)
- What it is: SST-CP/SST-TF frequency-shape utilities for the delphi Xeon
  6962P hosts. `flat_freq_apply` (no args) = all 288 CPUs -> CLOS0, TF on
  (universal flat, 4100-class for <=20 busy cores/domain);
  `flat_freq_apply <cpulist>` = select mode, listed cores + HT siblings ->
  CLOS0 (4100-class), rest -> CLOS3 <= 2700; `flat_freq_revert` = boot
  default; `flat_freq_status` = read-only state. Auto-detects the
  NOPASSWD isst binary per host (3bda: /opt copy, 3af6: workspace build).
- Verified: universal flat + select mode measured on both 3bda and 3af6
  (2026-07-02/03 experiment series); used for the 24h flat sweep, the
  TRON-80 run (3af6), and the TRON-88 baseline round (3bda).
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md
  (created v2), handoffs/claude_20260702-20260704_debug-3bda-flat-freq-run-ci-tests.md
  (benchmark usage). Central results doc:
  delphi-3bda:/scratch/jhan/flat_freq_tests/README.md
- NOTE: frequency state applied by this tool does NOT survive a reboot.

## gen_tron_flatfreq.py

- Canonical: delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/gen_tron_flatfreq.py
- Parses tron/config/resource-map.yaml (granite_rapids_6962p) and emits the
  exact isst command sequence for the boost-TRON-cores shape
  (--also-boost dev,rinzler,platform; --revert for boot restore).
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md,
  handoffs/claude_20260702-20260704_debug-3bda-flat-freq-run-ci-tests.md.

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
- All scrub the SYSTEM_CONFIG/TRON_LOG_LEVEL/SPDLOG_LEVEL env landmines and
  set CHECKERBOARD_MEMLOCK_KB=197971044 (host limit < checkerboard's 200 GB
  default). The marked THE BENCHMARK COMMAND block in each is the exact
  manual invocation.
- Related handoffs: handoffs/claude_20260702-20260704_debug-3bda-flat-freq-run-ci-tests.md.

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
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md,
  handoffs/claude_20260702-20260704_debug-3bda-flat-freq-run-ci-tests.md,
  handoffs/codex_2026-06-22-2026-06-30_configure-xeon-6-core-speeds.md,
  handoffs/codex_2026-06-29-2026-06-30_explore-core-power-feature.md.
