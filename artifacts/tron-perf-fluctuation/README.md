# TRON Performance-Fluctuation Artifacts

Preserved compact reports, reviews, and decision documents for the TRON
gpt-oss decode-performance fluctuation investigation. Repo copies are mirrors:
edit canonical files first, then refresh these copies.

## tron-serving-concepts.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron-perf-fluctuation/tron-serving-concepts.html
- Canonical:
  DESKTOP-CI2JA7M:W:/workspace/perf-fluctuation/from-claude/tron-serving-concepts.html
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
