# Lineage inventory: CI-AMX-test-shapes.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py`
- input: `artifacts/intel-amx/exec/results/l8b-levers-20260919/summary.json`, `artifacts/intel-amx/exec/results/l8b-levers-20260919/check-32u-p8192/perf.json`
- input built by: `artifacts/intel-amx/exec/l8b-levers-20260919/analyze.py`
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/more-testing/round-1/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/data-p/` (3 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/canon-ci-20260918/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ctxfill-20260901/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ctxfill2-20260901/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/fence3-20260901/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/` (13 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8bload-20260918/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/single-attn-20260901/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-attr-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-gen1536-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/tmp/amx-raw-data/` (3 preserved).
- regenerate: unavailable; the generator imports h_registry.py through an absolute canonical directory; h_registry.py hard-codes its result directory. The command cannot redirect these reads to preserved copies.

- Campaign source sets for the cited summaries are shared with the named report inventories in this batch and the existing mirror-vs-VNNI-K inventory.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/canon-ci-20260918/gen_ci_shapes.py` | `artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py`; preserved | 153460 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/analyze.py` | `artifacts/intel-amx/exec/l8b-levers-20260919/analyze.py`; preserved | 14874 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/summary.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/summary.json`; preserved | 46444 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/check-32u-p8192/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/check-32u-p8192/perf.json`; preserved | 809113 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8bload-20260918/summary.json` | `artifacts/intel-amx/exec/results/l8bload-20260918/summary.json`; preserved | 3351 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8bload-20260918/summary.md` | `artifacts/intel-amx/exec/results/l8bload-20260918/summary.md`; preserved | 6512 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/canon-ci-20260918/canon/perf.json` | `artifacts/intel-amx/exec/results/canon-ci-20260918/canon/perf.json`; preserved | 3889505 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/base-pass1/perf.json` | `artifacts/intel-amx/exec/results/ci-mimic-20260918/base-pass1/perf.json`; preserved | 3889486 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/reference/nightly_stats.json` | `artifacts/intel-amx/exec/results/ci-mimic-20260918/reference/nightly_stats.json`; preserved | 30169 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-20260916/summary.md` | `artifacts/intel-amx/exec/results/wedperf-20260916/summary.md`; preserved | 6528 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-gen1536-20260916/summary.md` | `artifacts/intel-amx/exec/results/wedperf-gen1536-20260916/summary.md`; preserved | 5085 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-attr-20260916/summary.md` | `artifacts/intel-amx/exec/results/wedperf-attr-20260916/summary.md`; preserved | 5663 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/more-testing/round-1/status.md` | `artifacts/intel-amx/pr3879/more-testing/round-1/status.md`; preserved | 42248 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/more-testing/round-1/results.html` | `artifacts/intel-amx/pr3879/more-testing/round-1/results.html`; preserved | 71616 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/summary.md` | `artifacts/intel-amx/exec/results/p0perf-20260913/summary.md`; preserved | 12522 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/tmp/amx-raw-data/t4-suite.txt` | `artifacts/intel-amx/tmp/amx-raw-data/t4-suite.txt`; preserved | 52580 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/perf-round.txt` | `artifacts/intel-amx/exec/results/perf-round-20260825/perf-round.txt`; preserved | 82837 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/perf-round.txt` | `artifacts/intel-amx/exec/results/perf-round-20260830/perf-round.txt`; preserved | 134951 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/pr-summary.md` | `artifacts/intel-amx/exec/results/perf-round-20260830/pr-summary.md`; preserved | 1174 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/data-p/prune_probe.py` | `artifacts/intel-amx/pr3879/PR1/data-p/prune_probe.py`; preserved | 1267 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/data-p/sharegpt_tok_lens.json` | `artifacts/intel-amx/pr3879/PR1/data-p/sharegpt_tok_lens.json`; preserved | 6004 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/tmp/amx-raw-data/chart-check.csv` | `artifacts/intel-amx/tmp/amx-raw-data/chart-check.csv`; preserved | 2144 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/tmp/amx-raw-data/amx-summary.csv` | `artifacts/intel-amx/tmp/amx-raw-data/amx-summary.csv`; preserved | 5261 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ctxfill-20260901/curve.json` | `artifacts/intel-amx/amx-decode-boost-202608/ctxfill-20260901/curve.json`; preserved | 372 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ctxfill2-20260901/curve2.json` | `artifacts/intel-amx/amx-decode-boost-202608/ctxfill2-20260901/curve2.json`; preserved | 209 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/fence3-20260901/medians.json` | `artifacts/intel-amx/amx-decode-boost-202608/fence3-20260901/medians.json`; preserved | 1024 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/fence3-20260901/medians-7605.json` | `artifacts/intel-amx/exec/results/fence3-20260901/medians-7605.json`; preserved | 5328 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/single-attn-20260901/summary.json` | `artifacts/intel-amx/amx-decode-boost-202608/single-attn-20260901/summary.json`; preserved | 4766 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-shapes.txt` | `artifacts/intel-amx/exec/results/t4/t4-shapes.txt`; preserved | 23355 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/data-p/prune_probe_2048.py` | `artifacts/intel-amx/pr3879/PR1/data-p/prune_probe_2048.py`; preserved | 973 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass2/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass2/perf.json`; preserved | 2849788 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass3/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass3/perf.json`; preserved | 2848955 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass1/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass1/perf.json`; preserved | 2848736 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass2/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass2/perf.json`; preserved | 2848611 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass3/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass3/perf.json`; preserved | 2848618 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass1/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass1/perf.json`; preserved | 2848602 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/check-mode/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/check-mode/perf.json`; preserved | 13349 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/prompt-check/run1.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/prompt-check/run1.json`; preserved | 141193 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/outcome.txt` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/outcome.txt`; preserved | 92 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/status-history.log` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/status-history.log`; preserved | 13176 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/configs-used.txt` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/configs-used.txt`; preserved | 76 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/h_registry.py` | `artifacts/intel-amx/exec/l8b-levers-20260919/h_registry.py`; preserved | 7772 |

Evidence:
- `handoffs/claude_20260919_status-saturday-plan-md-post-ci-actions.md:109-114`
- `artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py:442`
- `artifacts/intel-amx/exec/l8b-levers-20260919/h_registry.py:17`
