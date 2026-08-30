# TRON Performance-Fluctuation Artifacts

Preserved compact reports, reviews, and decision documents for the TRON
gpt-oss decode-performance fluctuation investigation. Repo copies are mirrors:
edit canonical files first, then refresh these copies.

## tron-serving-concepts.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/tron-serving-concepts.html
- Canonical:
  claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/tron-serving-concepts.html
  (re-pointed 2026-08-30: the former Windows path
  DESKTOP-CI2JA7M:W:/workspace/perf-fluctuation/from-claude/... was a mount of
  the same workspace file; content verified identical to this Linux path)
- What it is: Claude-generated conceptual explainer for TRON serving terms:
  session, batch, forward pass, token tree, shared prefix safety, and the
  off-by-one relationship between generated tokens and forward passes.
- Related handoff:
  direct artifact publish request on 2026-08-09.

## resolve_tron_gpt-oss_random.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/resolve_tron_gpt-oss_random.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/resolve_tron_gpt-oss_random.html
- What it is: standalone context and resolution plan for gpt-oss decode
  variability, including latest TP2/TP4 results, corrected trace-loss limits,
  source map, ranked hypotheses, and experiment ladder.
- Related handoff:
  handoffs/codex_2026-07-30-2026-07-31_inspect-tron-moe-randomness.md

## tron-MoE-random.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/tron-MoE-random.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/tron-MoE-random.html
- What it is: source audit of gpt-oss/MoE decode variance, later updated with
  Mixtral falsification, reciprocal Claude review context, WCLS tie-path
  analysis, and corrected experiment priorities.
- Related handoff:
  handoffs/codex_2026-07-30-2026-07-31_inspect-tron-moe-randomness.md

## group-f-pmu-interpretation.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/group-f-pmu-interpretation.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/group-f-pmu-interpretation.html
- What it is: interpretation of Claude's Group F PMU evidence, with PMU delta
  chart, supported versus unresolved claims, prioritized experiments, and
  evidence grading.
- Related handoff:
  handoffs/codex_2026-07-30_interpret-pmu-instruction-scoping.md

## review reports

- `ab58-report-review-v2.md`
  - Canonical:
    DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/ab58-report-review-v2.md
  - Related handoff:
    handoffs/codex_2026-07-29-2026-07-30_review-claude-test-report.md
- `simlot-S1-report-review.md`
  - Canonical:
    DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/simlot-S1-report-review.md
  - Related handoff:
    handoffs/codex_2026-07-29-2026-07-30_review-claude-test-report.md

## perf-fluctuation-suspicion-history.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/perf-fluctuation-suspicion-history.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/from-codex/perf-fluctuation-suspicion-history.html
- What it is: self-contained HTML suspicion ledger with current-investigation
  rows, handoff-derived historical additions, corrections, evidence bounds,
  sources, and filters.
- Related handoff:
  handoffs/codex_2026-07-29-2026-07-30_review-claude-test-report.md

## consensus and runbook review docs

- `FINAL_CONSENSUS.md`
  - Canonical:
    DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/review/tron-perf-fluctuation/FINAL_CONSENSUS.md
  - Related handoff:
    handoffs/codex_2026-08-01_review-tron-performance-analyses.md
- `RUNBOOK_from_codex.md`
  - Canonical:
    DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/review/tron-perf-fluctuation/RUNBOOK_from_codex.md
  - Related handoff:
    handoffs/codex_2026-08-01_review-tron-performance-analyses.md
- `CODEX_AUTONOMY_ANALYSIS_AND_RECOMMENDATION.md`
  - Canonical:
    DESKTOP-CI2JA7M:C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/review/tron-perf-fluctuation/CODEX_AUTONOMY_ANALYSIS_AND_RECOMMENDATION.md
  - Related handoff:
    handoffs/codex_2026-08-02_scope-runbook-permissions.md

## 2026-08-19 preservation batch (claude-alpha handoff run)

Registered by the 2026-08-19 SCOPE:auto handoff run on claude-alpha. Compact
registry format: one bullet per file — repo path, canonical location, what it
is, related handoff. Mirrors follow the canonical->repo rule: edit the
canonical file, refresh here on the next run.
- `workspace/from-claude/runbook-runtron-20-draw-perfetto.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/runbook-runtron-20-draw-perfetto.md` — runbook for the 20-draw runtron Perfetto+turbostat campaign. (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `alpha-scratch/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-campaign-v3.sh` — canonical `claude-agentsrv:/scratch/jhan/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-campaign-v3.sh` — v3 campaign harness (turbostat, template-generated config, ROUNDS/PERFETTO_TPL_SRC knobs). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `alpha-scratch/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-report-v3.py` — canonical `claude-agentsrv:/scratch/jhan/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-report-v3.py` — v3 report generator (throughput + power section). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `workspace/common/perfetto.cfg-template` — canonical `claude-agentsrv:/home/jhan/workspace/common/perfetto.cfg-template` — canonical Perfetto capture config (scheduler,model,driver,sys; write_into_file; RING_BUFFER). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `workspace/common/perfetto.cfg-template-driver-detail` — canonical `claude-agentsrv:/home/jhan/workspace/common/perfetto.cfg-template-driver-detail` — driver-detail variant of the capture config. (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `workspace/from-claude/perfetto-gap-analysis-draw18-slowest.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/perfetto-gap-analysis-draw18-slowest.html` — gap/O1a analysis report, slowest 20b draw (SQL embedded). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/from-claude/perfetto-gap-analysis-draw18-slowest.html
- `workspace/from-claude/perfetto-gap-analysis-draw19-fastest.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/perfetto-gap-analysis-draw19-fastest.html` — gap/O1a analysis report, fastest 20b draw + fast-vs-slow comparison. (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/from-claude/perfetto-gap-analysis-draw19-fastest.html
- `workspace/alpha-build/tron-build-fail-alpha.md` — canonical `claude-agentsrv:/home/jhan/workspace/tron-build-fail-alpha.md` — alpha container build-failure writeup (seccomp/overlayfs evidence + remediation). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `workspace/alpha-build/resume-build.sh` — canonical `claude-agentsrv:/home/jhan/workspace/alpha-build-scaffold/resume-build.sh` — one-command tron build resume script (probes fchmodat2 first). (handoff: claude_20260806-20260809_generate-runbook-for-runtron-test.md)
- `3bda-scratch/pdjn/tools-shape/perfetto-5cat-campaign-v4.sh` — canonical `delphi-3bda:/scratch/jhan/pdjn/tools-shape/perfetto-5cat-campaign-v4.sh` — parameterized campaign harness (users/gen-len/slice/model) with traffic gate v3, bitfile gate, USE_HW_ATTN gate. (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)
- `3bda-scratch/pdjn/mine1/mine.py` — canonical `delphi-3bda:/scratch/jhan/pdjn/mine1/mine.py` — Perfetto trace-mining tool (per-draw span-duration extraction via trace_processor) used by mine1–mine6 analyses. (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)
- `workspace/project-PDJN/HANDOFF-2026-08-11-suspended.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/project-PDJN/HANDOFF-2026-08-11-suspended.md` — suspended-track index: exclusions, resume traps, artifact map, resume plan. (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)
- `workspace/project-PDJN/NEW-TRACK-launch-lottery-3c51.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/project-PDJN/NEW-TRACK-launch-lottery-3c51.md` — new-track design + 3c51 machine-difference ledger. (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)
- `workspace/from-claude/mem-alloc-analysis.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/mem-alloc-analysis.html` — malloc analysis report answering Ben's suspicion (verdict, numbers, SQL method). (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/from-claude/mem-alloc-analysis.html
- `workspace/deep-dive/harness/deepdive-campaign.sh` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/harness/deepdive-campaign.sh` — main campaign harness (determinism gates, CI guard, CAPTURE/KVWAIT/SAMPLER modes, platformd dual-format restore). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `workspace/deep-dive/harness/msrsamp.c` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/harness/msrsamp.c` — 150 us APERF/MPERF+thermal MSR sampler (Ben's method, settled H6). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `workspace/deep-dive/status_report/2026-08-12-06-3c51-step5.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/2026-08-12-06-3c51-step5.html` — master current-state report (elimination ladder, code appendix for both span edges). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/deep-dive/status_report/2026-08-12-06-3c51-step5.html
- `workspace/deep-dive/status_report/2026-08-12-07-stall-map.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/2026-08-12-07-stall-map.html` — stall anatomy + fence-chain/definitive-sync-point documentation with verbatim source snippets. (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/deep-dive/status_report/2026-08-12-07-stall-map.html
- `workspace/deep-dive-3bda/RUNBOOK-perfetto-gated-inter-fwd-pass.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/RUNBOOK-perfetto-gated-inter-fwd-pass.md` — recipe for gated perfetto instrumentation + campaign on 3bda. (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `workspace/trace-sync-points/RUNBOOK-measure-fence3-and-span-endpoint.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/RUNBOOK-measure-fence3-and-span-endpoint.md` — recipe for fence-stamp builds (tags 7600/7601) and fence campaigns. (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/ab_verdict.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/ab_verdict.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/block_timing.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/block_timing.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/boundary_split.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/boundary_split.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/boundary_v5.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/boundary_v5.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/boundary_v6.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/boundary_v6.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/boundary_v7.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/boundary_v7.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deadbylayer.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deadbylayer.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deadseg.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deadseg.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deadtime.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deadtime.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deepdive-campaign-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deepdive-campaign-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deepdive-campaign-3c51-wclsbypass.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deepdive-campaign-3c51-wclsbypass.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deepdive-campaign-drambw.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deepdive-campaign-drambw.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deepdive-campaign.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deepdive-campaign.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/deepdive-campaign-wadefix.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/deepdive-campaign-wadefix.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence3_dump.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence3_dump.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence3_split.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence3_split.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence_cov.sql` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence_cov.sql` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence_cross.sql` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence_cross.sql` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence_win_create.sql` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence_win_create.sql` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fence_windows.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence_windows.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/fill_vs_rx.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/fill_vs_rx.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/gap_percard.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/gap_percard.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/gap_stations_decode.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/gap_stations_decode.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/gap_stations.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/gap_stations.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/gate_count.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/gate_count.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/hbm_audit.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/hbm_audit.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/kv_timeseries.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/kv_timeseries.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/make_folded.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/make_folded.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/membw.c` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/membw.c` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/msrsamp.c` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/msrsamp.c` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/msrsamp_join.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/msrsamp_join.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/pagemap_dump.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/pagemap_dump.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/parent_total.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/parent_total.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/percard_arrival.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/percard_arrival.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/perjob.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/perjob.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/perstep_corr.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/perstep_corr.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/phase_overlap.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/phase_overlap.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-antag-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-antag-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-dmalat-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-dmalat-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-f1pair-3bda.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-f1pair-3bda.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-irqquarantine-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-irqquarantine-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-minfreq-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-minfreq-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-noplatformd-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-noplatformd-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-selfintf-3bda.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-selfintf-3bda.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/run-uncorepin-3c51.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/run-uncorepin-3c51.sh` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/stall_10s.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/stall_10s.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/stall_forensics.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/stall_forensics.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/stall_inwindow.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/stall_inwindow.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/step_accounting.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/step_accounting.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/tps_summary.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/tps_summary.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `3bda-scratch/perf-fluctuation/deep-dive/tools/wcls7700.py` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/tools/wcls7700.py` — DUT-side analyzer/campaign tool (deep-dive tools set). (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `workspace/deep-dive-3bda/2026-08-12-07-3bda-pfgate-step0.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/2026-08-12-07-3bda-pfgate-step0.html` — gated-campaign attribution report (lanes, two-level attribution, next targets). (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/2026-08-12-07-3bda-pfgate-step0.html
- `workspace/deep-dive-3bda/2026-08-12-08-3bda-ungated-run.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/2026-08-12-08-3bda-ungated-run.html` — ungated r3 report (cmdline, env vars, fastest/slowest, campaign history). (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/2026-08-12-08-3bda-ungated-run.html
- `workspace/deep-dive-3bda/2026-08-13-09-3bda-fence-spans.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/2026-08-13-09-3bda-fence-spans.html` — fence-window population analysis + sharpened next target. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/2026-08-13-09-3bda-fence-spans.html
- `workspace/deep-dive-3bda/analysis/pfgate_windows.py` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/pfgate_windows.py` — gated-trace window recovery + leak detector. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `workspace/deep-dive-3bda/analysis/fence_span_windows.py` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/fence_span_windows.py` — joins slice dumps to fence-window boundaries (occupancy analysis). (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `workspace/deep-dive-3bda/pfgate-gate-patch.diff` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/pfgate-gate-patch.diff` — the 34-line perfetto window-gate patch on trunk 12804a812. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `workspace/deep-dive-3bda/LAUNCH-NOTES-pfgate.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/LAUNCH-NOTES-pfgate.md` — precondition checks + exact campaign launch command. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `3bda-scratch/pdjn/tools-pfgate/perfetto-5cat-campaign-v4.sh` — canonical `delphi-3bda:/scratch/jhan/pdjn/tools-pfgate/perfetto-5cat-campaign-v4.sh` — campaign harness copy with runbook edits + early-SIGUSR1 fix. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `claude-memory/fpga-monitoring-reference.md` — canonical `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-perf-fluctuation-deep-dive-3bda/memory/fpga-monitoring-reference.md` — FPGA monitoring mechanisms + Notion/Drive links. (handoff: claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md)
- `workspace/trace-sync-points/status_report/2026-08-13-01-fence3-split.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/status_report/2026-08-13-01-fence3-split.html` — TSC fence-decomposition report (campaigns 1-3, drift, SQL how-to, glossary). (handoff: claude_20260812-20260814_execute-runbook-and-generate-status-report.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/trace-sync-points/status_report/2026-08-13-01-fence3-split.html
- `workspace/trace-sync-points/status_report/2026-08-13-02-fence-traced.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/status_report/2026-08-13-02-fence-traced.html` — Traced 3bda fence campaign report (corr -0.85 verdict, data-ready stats). (handoff: claude_20260812-20260814_execute-runbook-and-generate-status-report.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/trace-sync-points/status_report/2026-08-13-02-fence-traced.html
- `workspace/trace-sync-points/tools/fpgastat_fence_dump.py` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/tools/fpgastat_fence_dump.py` — fence-flip tag-8xxx analyzer with full hygiene spec. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/tools/fpgause_poller_dump.py` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/tools/fpgause_poller_dump.py` — 1s FPGA-use poller record analyzer. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/tools/peakbw_analyze.py` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/tools/peakbw_analyze.py` — peakbw H1-H3 analyzer. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `3bda-scratch/perf-fluctuation/pfgate-3bda/tools/fpgastat-campaign.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/pfgate-3bda/tools/fpgastat-campaign.sh` — campaign harness with smoke barrier, host lock, control draws. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `3bda-scratch/perf-fluctuation/pfgate-3bda/tools/peakbw-campaign.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/pfgate-3bda/tools/peakbw-campaign.sh` — peakbw harness with CI-lease guard and RPQ calibration. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `3bda-scratch/perf-fluctuation/pfgate-3bda/tools/lowfreq-campaign.sh` — canonical `delphi-3bda:/scratch/jhan/perf-fluctuation/pfgate-3bda/tools/lowfreq-campaign.sh` — lowered_freq harness with dd-based MSR throttle capture. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/RUNBOOK-peakbw.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/RUNBOOK-peakbw.md` — executed runbook with pre-registered hypotheses and verdicts. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/RUNBOOK-fpgastat-armB.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/RUNBOOK-fpgastat-armB.md` — executed arm B runbook (post-review gates, decision tree). (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/rtl-register-audit.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/rtl-register-audit.md` — FPGA register inventory from llm_fpga RTL with poll tiers. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/intra-pass/CONTEXT.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/intra-pass/CONTEXT.md` — canonical project context + exclusion ledger. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/data/fpgause-probe-patch-4ceaca1a.diff` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/data/fpgause-probe-patch-4ceaca1a.diff` — frozen probe patch (poller + fence-flip + fine-window). (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
- `workspace/trace-sync-points/status_report/2026-08-17-02-window-waits.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/status_report/2026-08-17-02-window-waits.html` — report 05, the current-lead analysis. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/trace-sync-points/status_report/2026-08-17-02-window-waits.html
- `workspace/trace-sync-points/status_report/2026-08-13-03-wcls-bypass.html` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/status_report/2026-08-13-03-wcls-bypass.html` — report 03, bypass scoping + verdict. (handoff: claude_20260813-20260819_bypass-fpga-to-isolate-logits-jitter.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/workspace/trace-sync-points/status_report/2026-08-13-03-wcls-bypass.html
- `workspace/ingested-llama8b/NOTES-execution.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/NOTES-execution.md` — execution log: build-blocker fix recipe, collision guard protocol, peer findings. (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/status_report/report.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/status_report/report.md` — llama-8b tp4/tp2 screen report with per-draw numbers and gates. (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/status_report/report-mixtral-ab.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/status_report/report-mixtral-ab.md` — Mixtral hand-vs-ingested A/B report (confound-breaking result). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/RUNBOOK-llama8b-tps-screen.md` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/RUNBOOK-llama8b-tps-screen.md` — the runbook this session executed (repeatable screen recipe). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/identity-ingmixtral-tp2-20260815T163100Z.env` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/identity-ingmixtral-tp2-20260815T163100Z.env` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/identity-ingmixtral-tp4-20260815T155824Z.env` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/identity-ingmixtral-tp4-20260815T155824Z.env` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/identity-mixtral-tp4-20260815T152808Z.env` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/identity-mixtral-tp4-20260815T152808Z.env` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/identity-tp2-20260815T120428Z.env` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/identity-tp2-20260815T120428Z.env` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/identity-tp4-20260815T113956Z.env` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/identity-tp4-20260815T113956Z.env` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/results-ingmixtral-tp2-20260815T163100Z.csv` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/results-ingmixtral-tp2-20260815T163100Z.csv` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/results-ingmixtral-tp4-20260815T155824Z.csv` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/results-ingmixtral-tp4-20260815T155824Z.csv` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/results-mixtral-tp4-20260815T152808Z.csv` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/results-mixtral-tp4-20260815T152808Z.csv` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/results-tp2-20260815T120428Z.csv` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/results-tp2-20260815T120428Z.csv` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)
- `workspace/ingested-llama8b/data/results-tp4-20260815T113956Z.csv` — canonical `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/ingested-llama8b/data/results-tp4-20260815T113956Z.csv` — archived campaign measurement record (results.csv / identity.env). (handoff: claude_20260814-20260819_execute-runbook-ingested-llama8b.md)

### worktree-snapshots/ (uncommitted instrumentation, saved as diffs)

- `worktree-snapshots/tron-kvprobe-tracked-12804a812.diff` — canonical `claude-agentsrv:/home/jhan/workspace/tron-kvprobe` (git diff vs trunk 12804a812) — TSC-probe patch series, tags P1-P6/7000-7900. (handoff: claude_20260810-20260813_runtron-decode-perf-deep-dive.md)
- `worktree-snapshots/tron-kvprobe-untracked-kvwait_probe.hpp` — canonical `claude-agentsrv:/home/jhan/workspace/tron-kvprobe/h/system/kvwait_probe.hpp` (untracked) — probe header. (same handoff)
- `worktree-snapshots/tron-kvprobe-untracked-trace_gate.hpp` — canonical `claude-agentsrv:/home/jhan/workspace/tron-kvprobe/h/common/trace_gate.hpp` (untracked) — perfetto window gate header. (same handoff)
- `worktree-snapshots/pdjn-wt-tracked-12804a812.diff` — canonical `claude-agentsrv:/scratch/jhan/pdjn-wt` (git diff vs trunk 12804a812) — txlat probes, seq marker, data-ready instant, DMA alloc logger, model overlay. (handoff: claude_20260809-20260811_fix-runtron-decode-perf-fluctuation.md)

Deviation note: the worktrees themselves are directories; per the 2026-08-19
approval they are preserved as diff snapshots plus untracked source files,
not directory copies. Untracked build logs excluded.

## Linux Codex source-audit and runbook reviews (2026-08-11 to 2026-08-16)

- `handoff-review.md` — canonical
  `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/from-codex/handoff-review.md`
  — review explaining why shrinking leaf deltas should trigger a pivot from
  decomposition to causal intervention.
- `decode-sync-source-review.md` — canonical
  `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/from-codex/decode-sync-source-review.md`
  — decode-only source audit from final attention through the next forward pass.
- `decode-sync-lanes.html` — canonical
  `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive/from-codex/decode-sync-lanes.html`
  — all-thread lane diagram and S1-S16 source excerpts.
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron-perf-fluctuation/decode-sync-lanes.html
- `RUNBOOK-fpgastat-armB-review.md` — canonical
  `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/from-codex/RUNBOOK-fpgastat-armB-review.md`
  — unattended-run readiness review for the fpgastat Arm B experiment.
- Related handoffs:
  `handoffs/codex_20260811-20260813_review-decode-sync-investigation.md` and
  `handoffs/codex_20260816_review-fpgastat-runbook.md`.

## 2026-08-30 preservation batch (claude-agentsrv handoff run)

- `workspace/from-claude/qwen-3-30b-a3b-failure.md` — canonical
  `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/from-claude/qwen-3-30b-a3b-failure.md`
  — failure report for the qwen-3-30b-a3b campaign: NaN logit abort at tp4
  and tp2, making the model unusable for the fluctuation study.
  (handoff: claude_20260809_resume-tron-build-and-campaigns.md)
- `workspace/alpha-build/models.local.yaml` — canonical
  `claude-agentsrv:/home/jhan/workspace/alpha-build-scaffold/models.local.yaml`
  — gated-model overlay used by the container tron build.
  (handoff: claude_20260809_resume-tron-build-and-campaigns.md)
