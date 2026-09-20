# Lineage inventory: 2026-08-13-02-fence-traced.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: none (hand-maintained since 2026-08-14; historical `gen_fencepf_report.py` was lost in session scratch cleanup)
- input: `workspace/trace-sync-points/data/fencepf-windows.tgz` and campaign `results.csv` (proposed); original generator input path is Insufficient data
- input built by: `alpha-scratch/perf-fluctuation/deep-dive/tools/fence_windows.py` (already preserved at the 3bda-scratch prefix); campaign harness (proposed)
- sources: Fence campaign compact per-window archive, metrics, and identity record proposed; raw traces left behind (size).
- regenerate: none (the page is hand-maintained after its historical generator was lost)

Coverage: The surviving compact data archive and named campaign sources are inventoried. The lost generator prevents a complete reconstruction of the page-authoring procedure.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| archived 17 compact per-window source CSVs | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/data/fencepf-windows.tgz` | `artifacts/tron-perf-fluctuation/workspace/trace-sync-points/data/fencepf-windows.tgz`; propose preservation | 1399670 |
| throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results.csv` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results.csv`; propose preservation | 5130 |
| small campaign record | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/identity.env` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/identity.env`; propose preservation | 669 |
| throughput input builder | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/harness.sh` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/harness.sh`; propose preservation | 29685 |
| reconstructed and validated per-window input builder | `claude-agentsrv:/scratch/jhan/perf-fluctuation/deep-dive/tools/fence_windows.py` | `artifacts/tron-perf-fluctuation/3bda-scratch/perf-fluctuation/deep-dive/tools/fence_windows.py`; duplicate (artifacts/tron-perf-fluctuation/3bda-scratch/perf-fluctuation/deep-dive/tools/fence_windows.py) | 3112 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_01/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_01/metrics.json`; propose preservation | 725 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_01/trace.pftrace` | left behind (size) | 60098008 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_02/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_02/metrics.json`; propose preservation | 732 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_02/trace.pftrace` | left behind (size) | 60120956 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_03/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_03/metrics.json`; propose preservation | 723 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_03/trace.pftrace` | left behind (size) | 59667953 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_04/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_04/metrics.json`; propose preservation | 721 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_04/trace.pftrace` | left behind (size) | 58124734 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_05/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_05/metrics.json`; propose preservation | 733 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_05/trace.pftrace` | left behind (size) | 59806169 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_06/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_06/metrics.json`; propose preservation | 723 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_06/trace.pftrace` | left behind (size) | 57021103 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_07/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_07/metrics.json`; propose preservation | 743 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_07/trace.pftrace` | left behind (size) | 58770395 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_08/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_08/metrics.json`; propose preservation | 723 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_08/trace.pftrace` | left behind (size) | 60150988 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_09/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_09/metrics.json`; propose preservation | 736 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_09/trace.pftrace` | left behind (size) | 58066317 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_10/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_10/metrics.json`; propose preservation | 723 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_10/trace.pftrace` | left behind (size) | 58611718 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_11/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_11/metrics.json`; propose preservation | 735 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_11/trace.pftrace` | left behind (size) | 60214117 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_12/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_12/metrics.json`; propose preservation | 725 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_12/trace.pftrace` | left behind (size) | 59600466 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_13/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_13/metrics.json`; propose preservation | 734 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_13/trace.pftrace` | left behind (size) | 57578088 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_14/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_14/metrics.json`; propose preservation | 734 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_14/trace.pftrace` | left behind (size) | 57063475 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_15/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_15/metrics.json`; propose preservation | 732 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_15/trace.pftrace` | left behind (size) | 60512964 |
| per-draw throughput source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_16/metrics.json` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_16/metrics.json`; propose preservation | 734 |
| raw timing source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results/draw_16/trace.pftrace` | left behind (size) | 57928061 |
| raw timing source for smoke | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/smoke/trace.pftrace` | left behind (size) | 55517840 |
| lost historical page generator; handoffs/claude_20260812-20260814_execute-runbook-and-generate-status-report.md:71 | `Insufficient data: exact former session scratchpad path for gen_fencepf_report.py` | left behind (historical generator missing; exact path unavailable) | unavailable |

Evidence:
- `handoffs/claude_20260812-20260814_execute-runbook-and-generate-status-report.md:71,75-95`
- `workspace/trace-sync-points/status_report/2026-08-13-02-fence-traced.html:1`
