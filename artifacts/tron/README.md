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
