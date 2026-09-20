# Lineage inventory: CI-AMX-test-shapes.v1-20260919.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py.v1-20260919`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/more-testing/round-1/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/data-p/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/canon-ci-20260918/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8bload-20260918/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-attr-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/wedperf-gen1536-20260916/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/tmp/amx-raw-data/` (1 preserved).
- regenerate: `python3 artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py.v1-20260919 --out <OUT>`; verified 2026-09-20; identical after removing renderer comment and replacing generated timestamp Scratch preparation preview verified 2026-09-20; normalizations: renderer comment, Generated timestamp.

- Campaign source sets for the cited summaries are shared with the named report inventories in this batch and the existing mirror-vs-VNNI-K inventory.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/canon-ci-20260918/gen_ci_shapes.py.v1-20260919` | `artifacts/intel-amx/exec/canon-ci-20260918/gen_ci_shapes.py.v1-20260919`; preserved | 78488 |
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

Evidence:
- `handoffs/claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md:111-116`
