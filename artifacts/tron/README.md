# tron artifacts

Preserved copies of tron-related distilled knowledge on mutable storage.
Repo copies are mirrors: edit the canonical file, not these.

## tron_threads.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/tron_threads.html
- Canonical: this repo copy (regenerated 2026-08-17 with Claude Code; the
  earlier copy at delphi-3bda:/home/jhan/workspace/tron/codex_tmp/tron_threads_explainer/tron_threads.html
  was synced to match).
- Distilled explainer of tron's thread architecture: resource-map -> CPU
  sets, thread families and pinning, plus a function-to-thread distribution
  for the software-attention path (RMSNorm, RoPE, attention kernel,
  SiLU/SwiGLU, wcls, logits/sampling) and per-machine numbers for AMD
  Genoa96 and Intel Xeon 6962P. Originally generated with GPT Codex per
  jhan (2026-06-29); regenerated and extended with Claude Code.
- Related handoff: handoffs/codex_2026-06-29_document-tron-thread-pinning.md.

## kv-cache-structure.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/kv-cache-structure.html
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/tron_rampup/from-codex/kv-cache-structure.html
- What it is: interactive TRON KV-cache visualization covering token tree,
  book/page ownership, GAL/GOF grouping, head-to-slot mapping, fixed K/V staging
  capacity, D64 padding, D256 ineligibility, and the one-way book -> GOF -> FPGA
  HBM copy path.
- Related handoff: handoffs/codex_2026-07-23-2026-07-24_visualize-tron-kv-cache.md.

## pr3385-hw-attention-stage-3.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/pr3385-hw-attention-stage-3.html
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/PR3385/from-codex/2026-07-23-explanation-pr3385-hw-attention-stage-3.html
- What it is: interactive explanation of https://github.com/positron-ai/tron/pull/3385
  ("WLR Hw-Attention Stage 3"), including system background, diagrams, an EMEM
  calculator, code walkthrough, review risks, cumulative metadata capacity
  caveat, and quiz.
- Related handoff:
  handoffs/codex_2026-07-23-2026-07-27_explain-pr3385-diff.md.

## pr3385-from-pr2906-foundation.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/pr3385-from-pr2906-foundation.html
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/PR3385/from-codex/2026-07-27-explanation-pr3385-from-pr2906.html
- What it is: revised interactive PR3385 explanation after the README update,
  using PR 2906's GOF staging lifecycle as the foundation for PR 3385's
  per-layer submission ownership, batching, scheduler, EMEM, metadata, worker,
  and completion changes.
- Related handoff:
  handoffs/codex_2026-07-23-2026-07-27_explain-pr3385-diff.md.

## software-attention.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/software-attention.html
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/tron_rampup/from-codex/software-attention.html
- What it is: interactive ramp-up note for TRON software attention,
  including wall-clock lanes, K/V book/page state, C/R/U/D lifecycle tables,
  and labeled evidence gaps.
- Related handoff: handoffs/codex_2026-07-28_generate-ramp-up-html-files.md.

## attention-on-fpga.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/tron/attention-on-fpga.html
- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/tron_rampup/from-codex/attention-on-fpga.html
- What it is: interactive ramp-up note for Attention on FPGA, covering the
  derived HBM K/V copy, GAL/GOF staging, FPGA attention command path, and
  host return flow with source-confidence labels.
- Related handoff: handoffs/codex_2026-07-28_generate-ramp-up-html-files.md.

## transformer-pipeline.svg

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/tron_rampup/from-codex/transformer-pipeline.svg
- What it is: companion decoder-only transformer pipeline diagram shared by
  the software-attention and Attention-on-FPGA ramp-up notes.
- Related handoff: handoffs/codex_2026-07-28_generate-ramp-up-html-files.md.

## single-thread-assessment.html

- Rendered view:
  https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron/single-thread-assessment.html
- Canonical: claude-agentsrv:/home/jhan/workspace/tron-rampup/from-claude/single-thread-assessment.html
- What it is: source-reading assessment of the "single thread per core"
  proposal for tron (verdicts: A measure-first, B recommended, C not viable),
  with a 176-claim verification log.
- Related handoff: handoffs/claude_20260824_input-2-ai-single-thread-md-instructions.md

## single-thread.md

- Canonical: claude-agentsrv:/home/jhan/workspace/tron-rampup/input-2-ai/single-thread.md
- What it is: the user-written proposal document the assessment above answers.
- Related handoff: handoffs/claude_20260824_input-2-ai-single-thread-md-instructions.md

## 2026-09-20: TRON concepts explainer page (random project; registered by the claude-agentsrv handoff run)

Root mapping for this section: `random/` mirrors `claude-agentsrv:/home/jhan/workspace/random/` (a workspace folder on the shared NFS home, not a git repository). Canonical -> repo; edit the canonical file first.

- `memory/headless-chromium-render-check.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/headless-chromium-render-check.md` (1682 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: claude_20260919_internalize-concepts-md-directives.md)
- `memory/tron-concepts-page-2026-09-19.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/tron-concepts-page-2026-09-19.md` (2323 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: claude_20260919_internalize-concepts-md-directives.md)
- `random/from-claude/TRON-concepts-claude.html` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/TRON-concepts-claude.html` (174405 bytes). (handoff: claude_20260919_internalize-concepts-md-directives.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron/random/from-claude/TRON-concepts-claude.html
- `random/from-claude/tron-concepts-understand-design-wf_fe2751af-545.js` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/tron-concepts-understand-design-wf_fe2751af-545.js` (29955 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/fcd18152-9ade-458a-935d-031499cd5ec4/workflows/scripts/tron-concepts-understand-design-wf_fe2751af-545.js. (handoff: claude_20260919_internalize-concepts-md-directives.md)
- `random/from-claude/tron-concepts-verify-round2-wf_78f0fce1-335.js` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/tron-concepts-verify-round2-wf_78f0fce1-335.js` (11830 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/fcd18152-9ade-458a-935d-031499cd5ec4/workflows/scripts/tron-concepts-verify-round2-wf_78f0fce1-335.js. (handoff: claude_20260919_internalize-concepts-md-directives.md)
- `random/from-claude/tron-concepts-verify-wf_1c876190-471.js` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/tron-concepts-verify-wf_1c876190-471.js` (14735 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/fcd18152-9ade-458a-935d-031499cd5ec4/workflows/scripts/tron-concepts-verify-wf_1c876190-471.js. (handoff: claude_20260919_internalize-concepts-md-directives.md)
- `random/input-2-ai/internalize-concepts.md` -> `claude-agentsrv:/home/jhan/workspace/random/input-2-ai/internalize-concepts.md` (1187 bytes). (handoff: claude_20260919_internalize-concepts-md-directives.md)

## Handoff preservation — 2026-09-20

The existing `random/` mapping uses `claude-agentsrv:/home/jhan/workspace/random/`. The page uses mock teaching values, not measured benchmark results. Two validation files are copied from temporary storage into `exec/workflows/`. Their original paths remain as history.

- [`random/TRON-concepts-codex.html`](random/TRON-concepts-codex.html) — authored teaching HTML; mock data; no measurement lineage.
  - Canonical: `claude-agentsrv:/home/jhan/workspace/random/TRON-concepts-codex.html`
  - Related handoff: [codex_20260919_internalize-input-2-ai-concepts.md](../../handoffs/codex_20260919_internalize-input-2-ai-concepts.md)
  - Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron/random/TRON-concepts-codex.html

- [`random/exec/workflows/validate-tron-concepts.py`](random/exec/workflows/validate-tron-concepts.py) — document browser-validation script.
  - Canonical: `claude-agentsrv:/home/jhan/workspace/random/exec/workflows/validate-tron-concepts.py`
  - Related handoff: [codex_20260919_internalize-input-2-ai-concepts.md](../../handoffs/codex_20260919_internalize-input-2-ai-concepts.md)
  - origin: `claude-agentsrv:/tmp/validate-tron-concepts.py`. Copy retained at the original path.

- [`random/exec/workflows/tron-concepts-validation.json`](random/exec/workflows/tron-concepts-validation.json) — compact document-validation result; not inference measurements.
  - Canonical: `claude-agentsrv:/home/jhan/workspace/random/exec/workflows/tron-concepts-validation.json`
  - Related handoff: [codex_20260919_internalize-input-2-ai-concepts.md](../../handoffs/codex_20260919_internalize-input-2-ai-concepts.md)
  - origin: `claude-agentsrv:/tmp/tron-concepts-validation.json`. Copy retained at the original path.

Validation results describe the original concept-page session. The handoff records which checks preceded the final edits. No inference benchmark was run for this page.

## Batch: 2026-09-24 SCOPE:auto run (Claude, claude-agentsrv)

- `random/from-claude/tron-concepts-short-verify-wf_2f31720c-b2b.js` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/tron-concepts-short-verify-wf_2f31720c-b2b.js` (5094 bytes). origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/fcd18152-9ade-458a-935d-031499cd5ec4/workflows/scripts/tron-concepts-short-verify-wf_2f31720c-b2b.js` (relocated 2026-09-24). Workflow script: the verification run of the short edition (Workflow 4 of that session). Related: [claude_20260919-20260920_internalize-concepts-md-directives.md](../../handoffs/claude_20260919-20260920_internalize-concepts-md-directives.md).
- `memory/ci-merge-audit-0922-0923.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/ci-merge-audit-0922-0923.md` (2450 bytes). Memory note; the canonical file is edited in place by Claude Code. Related: [claude_20260923_amx-benchmark-tps-regression-between-ci-runs.md](../../handoffs/claude_20260923_amx-benchmark-tps-regression-between-ci-runs.md).
- `random/from-claude/TRON-concepts-claude-short.html` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/TRON-concepts-claude-short.html` (124612 bytes). The 3,031-word short edition of TRON-concepts-claude.html (a document, not a report page). Related: [claude_20260919-20260920_internalize-concepts-md-directives.md](../../handoffs/claude_20260919-20260920_internalize-concepts-md-directives.md).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron/random/from-claude/TRON-concepts-claude-short.html

## Batch: 2026-10-16 SCOPE:auto run (Claude, claude-agentsrv)

Registered by the 2026-10-16 `SCOPE: auto` handoff run of claude-handoff-generation-prompt.md. `claude-agentsrv` is the podman container on the dev server `agentsrv` (same home directory). Repo path -> canonical path (bytes). Canonical -> repo; edit the canonical file first.

New prefix this batch: `home-tmp/` mirrors `claude-agentsrv:/home/jhan/tmp/` (the humanized copy of TRON-concepts-codex.html of 2026-10-07; the registered `random/TRON-concepts-codex.html` canonical in `/home/jhan/workspace/random/` is unchanged).

- `home-tmp/TRON-concepts-codex.html` -> `claude-agentsrv:/home/jhan/tmp/TRON-concepts-codex.html` (59613 bytes). Document. (handoff: [claude_20261007_tron-concepts-codex-html-prose-humanization.md](../../handoffs/claude_20261007_tron-concepts-codex-html-prose-humanization.md))
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/tron/home-tmp/TRON-concepts-codex.html
- `memory/3bda-ci-amx-shape-models-2026-09-18.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/3bda-ci-amx-shape-models-2026-09-18.md` (2409 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))
- `memory/3bda-platformd-sst-dev-build-2026-10-07.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/3bda-platformd-sst-dev-build-2026-10-07.md` (3027 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261013_delphi-3bda-platform-version-0-11-0-sst-88b2d3da-upgrade.md](../../handoffs/claude_20261013_delphi-3bda-platform-version-0-11-0-sst-88b2d3da-upgrade.md))
- `memory/MEMORY.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/MEMORY.md` (4408 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md](../../handoffs/claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md))
- `memory/ci-amx-regression-20261009.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/ci-amx-regression-20261009.md` (3277 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261009_amx-benchmark-perf-regression.md](../../handoffs/claude_20261009_amx-benchmark-perf-regression.md))
- `memory/herdr-agentsrv-topology-2026-10-03.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/herdr-agentsrv-topology-2026-10-03.md` (2748 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md](../../handoffs/claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md))
- `memory/herdr-pane-shell-dash-fix-2026-10-04.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/herdr-pane-shell-dash-fix-2026-10-04.md` (2659 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261004_herdr-shell-prompt-and-tab-completion.md](../../handoffs/claude_20261004_herdr-shell-prompt-and-tab-completion.md))
- `memory/platformd-amx-sst-brief-2026-10-05.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/memory/platformd-amx-sst-brief-2026-10-05.md` (1547 bytes). Memory note; the canonical stays in the session store because Claude Code edits it in place. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))
- `random/from-claude/platformd-amx-sst-brief-2026-10-05-jhan.md` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/platformd-amx-sst-brief-2026-10-05-jhan.md` (1900 bytes). Document. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))
- `random/from-claude/platformd-amx-sst-brief-2026-10-05-long.md` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/platformd-amx-sst-brief-2026-10-05-long.md` (59980 bytes). Document. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))
- `random/from-claude/platformd-amx-sst-brief-2026-10-05.md` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/platformd-amx-sst-brief-2026-10-05.md` (36813 bytes). Document. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))
  - generator: none (hand-condensed from the workflow draft, corrected by string replacement)
  - input: /tmp/claude-0/-home-jhan-workspace-random/a8a83f74-62af-4a25-acb8-9492c69bdbd9/scratchpad/draft.md
  - input built by: workflow platformd-amx-sst-brief-wf_0dd22299-b33.js (20 agents, task wq9xj9oxa)
  - sources: /home/jhan/workspace/notebook/artifacts/intel-speed-select/README.md, /home/jhan/workspace/notebook/artifacts/intel-speed-select/reminder.md, /home/jhan/workspace/notebook/artifacts/intel-speed-select/results/sst-ab-20260917/summary.md, /home/jhan/workspace/notebook/artifacts/intel-amx/README.md, /home/jhan/workspace/notebook/handoffs/ (speed select and AMX handoffs 2026-09-16 to 2026-10-02), /home/jhan/workspace/tron/CMakeLists.txt, /home/jhan/workspace/tron/CMakePresets.json, /home/jhan/workspace/tron/GNUmakefile, /home/jhan/workspace/tron/packaging/systemd/rinzler@.service, /home/jhan/workspace/tron/src/tron/kernels/amx_attn.cpp
  - regenerate: unavailable (hand-edited after the workflow; the long draft can be rebuilt by re-running the workflow script)
  - regenerate unverified (no generator or generator unavailable)
- `random/from-claude/platformd-amx-sst-brief-wf_0dd22299-b33.js` -> `claude-agentsrv:/home/jhan/workspace/random/from-claude/platformd-amx-sst-brief-wf_0dd22299-b33.js` (23025 bytes). Workflow script. (handoff: [claude_20261005_amx-and-intel-speed-select-in-platformd.md](../../handoffs/claude_20261005_amx-and-intel-speed-select-in-platformd.md))

## story2814-scratch/ (2026-10-21 preservation batch)

Copied on 2026-10-21 from `delphi-3bda:/scratch/jhan/workspace/story2814/`
(an NFS share, also mounted on claude-agentsrv) just before that directory was
deleted to free 21 GiB. The directory held the five PR #2906 / Story 2814
perf-comparison runs of 2026-06-08 to 06-10 (per run: two tron worktrees with
builds, Perfetto captures, notes, trace queries) and the PR2906 review-note
folder. Only the notes, queries, logs and PR2906 files were kept (38 files,
884 KB). The worktrees are rebuildable from git. The 30 `.trace` captures
(4.8 GiB) were left behind by size and are gone. Paths under
`story2814-scratch/` mirror the original paths. The canonical copies no longer
exist, so these repo copies are now the only copies.
Related handoffs: handoffs/codex_2026-06-08-2026-06-10_pr-2906-perf-test.md
(the runs) and
handoffs/codex_2026-06-08-2026-06-16_story-2814-re-populate-hwcache-block-on-demand.md
(the PR2906 notes). "HW attention" below is the FPGA attention path
(`USE_HW_ATTN=1`); "TP2" is a two-device tensor-parallel model.

- `story2814-scratch/compare_perf/runs/20260608_parent_vs_tracing/notes/comparison_summary.md` — parent 576843b18 vs tracing commit 1c6d3fc8e, HW attention on, p256/g256/s64/u8, instance 0,2: -0.648 % new tok/s, plus the trace evidence (xfer_gof slice counts).
- `story2814-scratch/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes/comparison_summary.md` — f5ea3148 plus tracked dirty diff vs parent 576843b18: -0.225 % new tok/s, +1.156 % xfer_gof.
- `story2814-scratch/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes/candidate_tracked_diff.patch` — the tracked dirty diff (27,751 bytes) applied to the candidate of that run.
- `story2814-scratch/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/queries/trace_slices_candidate.csv`, `.../trace_slices_parent.csv` — Perfetto slice count and total time per trace event, the input of the summary's trace table.
- `story2814-scratch/compare_perf/runs/20260610_tp2_instance_0_4_ffc2d615_dirty_vs_parent/notes/comparison_summary.md` — corrected TP2 comparison with `--instance 0,4` forced in CLI and `SYSTEM_CONFIG` (the earlier runs inherited `--instance 0,2`): -0.144 % new tok/s, +0.147 % TTLT, -1.110 % xfer_gof.
- `story2814-scratch/compare_perf/runs/20260610_tp2_instance_0_4_ffc2d615_dirty_vs_parent/notes/candidate_tracked_diff.patch` — the dirty diff of that run (`.gitignore` only).
- `story2814-scratch/compare_perf/runs/20260610_tp2_instance_0_4_ffc2d615_dirty_vs_parent/queries/trace_slices_candidate.csv`, `.../trace_slices_parent.csv` — slice counts for that run.
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/notes/comparison_summary.md` — long-context run (prompt 8000, length 256, 4 users, instance 0,4), `--iterations 3` and `--isolated-iterations 3`: candidate +0.189 % and +0.258 % new tok/s, with the validation checks of all four captures.
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/notes/run_config.txt` — the run parameters (model, lengths, users, instance, iterations, env).
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/notes/source_status.txt`, `.../source_log_oneline.txt`, `.../base_parent_commit.txt`, `.../candidate_commit.txt`, `.../candidate_tracked_diff.patch`, `.../candidate_tracked_diff_name_status.txt` — git state of the source repo at run time: `git status`, recent log, the two commits, the tracked dirty diff and its name-status list.
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/notes/overall_log_metrics.csv`, `.../per_iteration_log_metrics.csv` — the metric tables parsed from the tronperf logs (overall and per iteration).
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/queries/` — 4 `.sql` trace-slice queries (iterations and isolated, parent and candidate) and their 4 `.csv` outputs.
- `story2814-scratch/compare_perf/runs/20260610_222324_longctx_p8000_l256_u4_ffc2d6156a_dirty_vs_576843b189/logs/runner.log`, `.../build_base_parent.log`, `.../build_candidate.log` — the unattended runner log (1.1 MB) and the two build logs of that run.
- `story2814-scratch/PR2906/before_gof_rodeo_split.patch`, `.../before_gof_rodeo_split_note.md` — snapshot of the tracked diff after backing out the experimental `gof_rodeo_impl()` prepare-once fanout split, and the note that compares it byte for byte with the perf-run diff.
- `story2814-scratch/PR2906/gof_rodeo_prepare_once_fanout_note.md` — the prepare-once fanout experiment (Mike's suggestion to split `gof_rodeo_impl()`) and why it was backed out.
- `story2814-scratch/PR2906/complete_gof_never_transferred.md` — interpretation of Mike's `backfill_shard()` review comment about complete GOFs that were never transferred.
- `story2814-scratch/PR2906/inflight_guard_struct_style_note.md`, `.../restore_inflight_guard_class_style.patch` — the `inflight_guard` class-to-struct style change (from commit 857be21be) and the patch that restores the class form.
- `story2814-scratch/PR2906/delete_model_gof_rodeo_trace_comment_note.md`, `.../restore_model_gof_rodeo_trace_comment.patch` — removal of the GOF-rodeo Perfetto comment in `h/tron/models/model.hpp` and the patch that restores it.
- Not copied: the run `20260608_hwattn_gof` had empty notes, logs and queries folders (the invalid early comparison without HW attention on the base); the `worktrees/` and `captures/` folders of every run.
