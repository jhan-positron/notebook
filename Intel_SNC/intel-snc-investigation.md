# Intel SNC Investigation

Last updated: 2026-07-12

This is the top-level resume map for the Intel Xeon 6 SNC/3 investigation.
The original working tree is:

`andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3`

A curated, non-bulk subset is preserved in this notebook under:

`../artifacts/intel-snc/`

## Primary Takeaway

SNC/3 is not a free BIOS switch for TRON-like workloads.

SNC/3 splits each Xeon 6962P socket into three NUMA domains, one per compute
die. That improves local latency, but it also partitions memory bandwidth: one
SNC node has about four DDR5 channels and saturates near 204 GB/s. SNC-OFF
exposes the whole socket as one NUMA node, so a simple socket-local workload can
scale across all twelve DDR5 channels and reach about 600 GB/s.

The concise mental model:

```text
SNC3 local die:
  lower local latency, but one-node DRAM BW ceiling ~= 204 GB/s

SNC-OFF socket node:
  higher local latency, but one-node DRAM BW ceiling ~= 596-600 GB/s

SNC3 only recovers full socket bandwidth when work and memory are explicitly
spread local-per-die, for example first-touch local allocation across all three
socket-local SNC nodes.
```

The seed knowledge-base page is [intel-snc-knowledge.html](intel-snc-knowledge.html).
It preserves the annotated Test 11 graph and a distilled version of the Slack
message that explains why SNC/3 did not automatically improve performance.

## Start Here

- [../artifacts/intel-snc/input-2-ai/README.md](../artifacts/intel-snc/input-2-ai/README.md):
  the hand-authored project control folder. These files capture the goal,
  context, execution plan, environment constraints, expected output structure,
  and the evolution of the investigation. Treat these as user-authored
  provenance, not generated output.
- [../artifacts/intel-snc/claude-workspace/REPORT/FINAL_REPORT.md](../artifacts/intel-snc/claude-workspace/REPORT/FINAL_REPORT.md):
  final same-machine SNC3 report for `delphi-3af6`. It records the clean run,
  result CSV paths, figure paths, prediction scorecard, and caveats.
- [../artifacts/intel-snc/claude-workspace/REPORT/TRON_SNC3_PERFORMANCE_PREDICTION.md](../artifacts/intel-snc/claude-workspace/REPORT/TRON_SNC3_PERFORMANCE_PREDICTION.md):
  TRON-specific interpretation. It explains why compact Llama decode might
  benefit only with correct placement, while Qwen/model-load/wide phases can
  regress unless sharded across SNC nodes.
- [../artifacts/intel-snc/pre-work/intel-amd-comparison/pass1_outline.md](../artifacts/intel-snc/pre-work/intel-amd-comparison/pass1_outline.md):
  structured Intel-vs-AMD background study with tables, diagrams, and citations.
- [../artifacts/intel-snc/pre-work/intel-amd-comparison/pass2_writeup.md](../artifacts/intel-snc/pre-work/intel-amd-comparison/pass2_writeup.md):
  prose version of the same background study. This is the file with the useful
  text diagrams for Intel Xeon 6962P, AMD EPYC 9654, DDR5 channels, mesh/EMIB,
  CHAs, CCDs, and system topology.

## Handoffs

Use these handoffs to recover the conversation trail:

- [../handoffs/codex_2026-06-03-2026-06-11_intel-snc3.md](../handoffs/codex_2026-06-03-2026-06-11_intel-snc3.md):
  broad Codex SNC3 investigation thread, including script review, topology
  reasoning, figure fixes, Test12 follow-up, and artifact paths.
- [../handoffs/codex_2026-06-05-2026-06-07_delphi-3af6-enable-snc3-runner.md](../handoffs/codex_2026-06-05-2026-06-07_delphi-3af6-enable-snc3-runner.md):
  clean-run summary for the full `delphi-3af6` SNC3 characterization and TRON
  prediction work.
- [../handoffs/codex_2026-06-01-2026-06-11_fix-code-connection-error.md](../handoffs/codex_2026-06-01-2026-06-11_fix-code-connection-error.md):
  related thread that touched the figure generator and `input-2-ai` fixes.
- [../handoffs/codex_2026-06-05_can-you-connect-to-the-codex-which-is-currently-running-tasks-at.md](../handoffs/codex_2026-06-05_can-you-connect-to-the-codex-which-is-currently-running-tasks-at.md):
  remote-session coordination notes around the running SNC3 work.
- [../handoffs/codex_2026-06-05_how-to-print-all-the-bios-config-of-this-machine.md](../handoffs/codex_2026-06-05_how-to-print-all-the-bios-config-of-this-machine.md):
  useful side note for finding BIOS/SNC-related settings.

To rediscover anything broader later:

```bash
rg -n "SNC3|SNC/3|SNC-OFF|Sub-NUMA|enable-SNC3" ../handoffs ../artifacts
```

## Remote Workspace Map

Remote root:

`andoria-15:/home/jhan/workspace/intel-vs-amd/enable-SNC3`

Key directories:

- `pre-work/`
  - Purpose: static Intel-vs-AMD background study made before the focused SNC3
    run.
  - Important child: `pre-work/intel-amd-comparison/`
  - Why it exists: it explains the starting problem: Intel Xeon 6962P in
    SNC-OFF looked weak versus AMD EPYC 9654 in several CPU/memory subsystem
    measurements. The later SNC3 project used this as background and AMD
    cross-vendor context, not as the live same-machine SNC-OFF baseline.
- `input-2-ai/`
  - Purpose: final hand-crafted instruction set for the project.
  - Important files: `goal.md`, `context.md`, `planning.md`, `environment.md`,
    `execute.md`, `output.md`, and `util/make_figures_csv_reference.py`.
  - Why it matters: these are the user's thoughts and requirements. They record
    how the investigation evolved, what had to be measured, what comparisons
    mattered, and how the report should be shaped.
- `input-2-ai.7/`, `input-2-ai.8/`, `input-2-ai.9/`
  - Purpose: snapshots of earlier instruction iterations.
  - `input-2-ai.9/` is very close to the final `input-2-ai/` copy.
- `claude-workspace/`
  - Purpose: final active workspace with the clean run artifacts.
  - Start from `REPORT/FINAL_REPORT.md`, `REPORT/TRON_SNC3_PERFORMANCE_PREDICTION.md`,
    `REPORT/figures/`, `code/`, and `scripts/`.
- `claude-workspace.10/`
  - Purpose: late/final snapshot parallel to the unnumbered `claude-workspace/`.
    The unnumbered directory should be treated as the current final copy.
- `claude-workspace.9/`
  - Purpose: earlier clean SNC3 pass/report generation snapshot.
- `claude-workspace.5/`, `claude-workspace.6.mode-common.1/`,
  `claude-workspace.7/`, `claude-workspace.8/`
  - Purpose: historical workspace snapshots from script/report iterations.
    These are useful if a later result needs to be compared against an older
    script version.
- `from-codex-20260604_063349-inspect-latency/`
  - Purpose: Codex review/fix area for inspect and latency scripts, including
    `analysis/` notes and candidate script changes.
- `test_3b70/`
  - Purpose: adaptation and small runs against the `delphi-3b70` SNC3 topology.

## Preserved Artifact Set

Preserved in [../artifacts/intel-snc/](../artifacts/intel-snc/):

- `primary-takeaway-test11-snc3-vs-snc-off.png`
  - Source: the graph attached on 2026-07-12.
  - Role: annotated human-readable takeaway for Test 11.
- `pre-work/intel-amd-comparison/`
  - Preserves the comparison README, `pass1_outline.md`, `pass2_writeup.md`,
    test code, and architecture figure generator/assets.
- `input-2-ai/`
  - Preserves the final hand-authored project inputs and figure-reference script.
- `claude-workspace/REPORT/`
  - Preserves final reports, report figures, figure data, and report figure
    generator.
- `claude-workspace/code/`
  - Preserves generated benchmark tools: `inspect_pages`, `ptr_chase`,
    `bw_avx512`, `bw_multi`, and `c2c_lat` source plus `Makefile`.
- `claude-workspace/scripts/`
  - Preserves the final runner scripts, including Test 11 socket saturation and
    Test 12 latency-vs-socket-bandwidth.

Not preserved here:

- Raw `results/` trees and benchmark logs. They are bulk evidence and remain in
  the remote workspace. The final report records the exact remote result paths.

## Key Measurements

From the final report:

- SNC3 exposes six NUMA nodes, three per socket.
- Local-die L3 latency improved from 60.535 ns in the same-machine SNC-OFF prior
  to 35.892 ns in SNC3.
- Local DRAM latency improved from 137.696 ns to 112.751 ns.
- One SNC3 memory node peaked around 204.238 GB/s, essentially the expected
  four-channel die limit.
- Whole-socket `--local` read saturation recovered full socket bandwidth:
  608.882 GB/s at 72 threads, about 99% of the 12-channel DDR5-6400 theoretical
  ceiling.
- The key performance risk is binding a wide workload to one SNC node. That can
  turn a 596-600 GB/s socket into a 204 GB/s bottleneck.

## Resume Checklist

1. Open [intel-snc-knowledge.html](intel-snc-knowledge.html) for the mental
   model.
2. Read [../artifacts/intel-snc/input-2-ai/context.md](../artifacts/intel-snc/input-2-ai/context.md)
   and [../artifacts/intel-snc/input-2-ai/goal.md](../artifacts/intel-snc/input-2-ai/goal.md).
3. Read the final report and TRON prediction report under
   `../artifacts/intel-snc/claude-workspace/REPORT/`.
4. If rerunning measurements, start from the preserved `code/` and `scripts/`
   but verify the live remote tree first.
5. Always runtime-detect SNC mode:

```bash
cat /sys/devices/system/node/online
```

Interpretation:

```text
0-5 = SNC/3, three NUMA nodes per socket
0-1 = SNC-OFF, one NUMA node per socket
```

## Caveats

- Test 12 had rows marked `background_finished_during_probe`; they were retained
  in raw CSV evidence but excluded from the figure where appropriate.
- There was no same-machine SNC-OFF Test12 CSV in the final report, so
  cross-mode Test12 conclusions are caveated.
- Do not treat SNC3 as beneficial unless CPU placement, memory allocation,
  DMA/descriptor/KV buffers, queues, and device locality are all considered
  together.
