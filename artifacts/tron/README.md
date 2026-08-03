# tron artifacts

Preserved copies of tron-related distilled knowledge on mutable storage.
Repo copies are mirrors: edit the canonical file, not these.

## tron_threads.html

- Canonical: delphi-3bda:/home/jhan/workspace/tron/codex_tmp/tron_threads_explainer/tron_threads.html
  (a codex_tmp directory — high deletion risk, hence preserved here)
- Distilled explainer of tron's thread architecture, generated with GPT
  Codex per jhan.
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
