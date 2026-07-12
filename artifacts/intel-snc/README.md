# Intel SNC Artifact Registry

Mirrored on 2026-07-12 from:

`andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3`

This directory preserves the small, high-value files needed to resume or
understand the Intel Xeon 6 SNC/3 investigation. Raw result directories and bulk
logs remain in the remote workspace.

## Local-Only Artifact

- Local: `artifacts/intel-snc/primary-takeaway-test11-snc3-vs-snc-off.png`
  - Source: graph image attached in the Codex chat on 2026-07-12.
  - Purpose: annotated Test 11 graph used as the primary takeaway in
    `intel-snc-knowledge.html`.
  - SHA256 at import:
    `A073D84BFCF55DA2FB51C39D4EA5AD3A9C9F7FED492E326FE30CE32249D14CED`

## Mirrored Remote Artifacts

- Local: `artifacts/intel-snc/pre-work/intel-amd-comparison/`
  - Canonical:
    `andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3/pre-work/intel-amd-comparison/`
  - Contents preserved: comparison README, `pass1_outline.md`,
    `pass2_writeup.md`, test code, and architecture figure assets.
  - Purpose: pre-SNC3 Intel-vs-AMD background, including the useful text diagrams
    for Xeon 6962P, EPYC 9654, DDR5 channels, mesh/EMIB, CHAs, and CCDs.

- Local: `artifacts/intel-snc/input-2-ai/`
  - Canonical:
    `andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3/input-2-ai/`
  - Contents preserved: final hand-authored project instructions, context,
    goals, execution plan, output requirements, environment notes, and figure
    reference script.
  - Purpose: user-authored provenance and thought progression.

- Local: `artifacts/intel-snc/claude-workspace/REPORT/`
  - Canonical:
    `andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3/claude-workspace/REPORT/`
  - Contents preserved: final report, predictions, TRON SNC3 performance
    prediction, report figures, figure data, and figure generator.
  - Purpose: final evidence-backed conclusions and report visuals.

- Local: `artifacts/intel-snc/claude-workspace/code/`
  - Canonical:
    `andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3/claude-workspace/code/`
  - Contents preserved: generated benchmark C tools and Makefile.
  - Purpose: allows future review or regeneration of the latency/bandwidth test
    suite without reconstructing it from handoffs.

- Local: `artifacts/intel-snc/claude-workspace/scripts/`
  - Canonical:
    `andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3/claude-workspace/scripts/`
  - Contents preserved: final runner scripts, including Test 11 and Test 12.
  - Purpose: records the final orchestration logic and fixed gates.

## Not Mirrored

- `claude-workspace/results/`
- numbered workspace `results/` directories
- large raw logs and CSV result trees

Those remain in the canonical remote workspace. The final report lists the
specific remote result paths used for the conclusions.
