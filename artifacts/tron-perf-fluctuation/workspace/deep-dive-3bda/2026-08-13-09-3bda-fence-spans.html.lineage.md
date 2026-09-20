# Lineage inventory: 2026-08-13-09-3bda-fence-spans.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: Insufficient data: handoff names the span extractor, not the script or workflow that authored the page
- input: `analysis/out/fence/d{04,05,06,10,15,16}.fspans.csv` (proposed)
- input built by: `fence_span_windows.py` (already preserved), with `window_gaps.py` (proposed)
- sources: Compact per-window archive and throughput CSV proposed; six slice dumps left behind (size); raw fence traces recorded in the fence-traced page inventory.
- regenerate: unavailable (the page authoring method is not identified by the available handoff or page)

Coverage: The named-span input files and builder are verified. The page generator is Insufficient data. This is a partial metadata proposal, not a claim that the page can be regenerated.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d04.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d04.fspans.csv`; propose preservation | 503198 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d04.slices.csv` | left behind (size) | 67231618 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d05.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d05.fspans.csv`; propose preservation | 509925 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d05.slices.csv` | left behind (size) | 69167490 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d06.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d06.fspans.csv`; propose preservation | 498359 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d06.slices.csv` | left behind (size) | 65982906 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d10.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d10.fspans.csv`; propose preservation | 504366 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d10.slices.csv` | left behind (size) | 67771906 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d15.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d15.fspans.csv`; propose preservation | 516825 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d15.slices.csv` | left behind (size) | 70015765 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d16.fspans.csv` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/out/fence/d16.fspans.csv`; propose preservation | 497888 |
| named-span measured input / raw slice source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out/fence/d16.slices.csv` | left behind (size) | 66998171 |
| input builder or compact source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/fence_span_windows.py` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/fence_span_windows.py`; duplicate (artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/fence_span_windows.py) | 4174 |
| input builder or compact source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/window_gaps.py` | `artifacts/tron-perf-fluctuation/workspace/deep-dive-3bda/analysis/window_gaps.py`; propose preservation | 6971 |
| input builder or compact source | `claude-agentsrv:/home/jhan/workspace/perf-fluctuation/trace-sync-points/data/fencepf-windows.tgz` | `artifacts/tron-perf-fluctuation/workspace/trace-sync-points/data/fencepf-windows.tgz`; propose preservation | 1399670 |
| input builder or compact source | `claude-agentsrv:/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results.csv` | `artifacts/tron-perf-fluctuation/alpha-scratch/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/results.csv`; propose preservation | 5130 |

Evidence:
- `handoffs/claude_20260811-20260813_review-runbook-and-begin-scheduled-work.md:105-112`
- `workspace/deep-dive-3bda/2026-08-13-09-3bda-fence-spans.html:Traceability`
