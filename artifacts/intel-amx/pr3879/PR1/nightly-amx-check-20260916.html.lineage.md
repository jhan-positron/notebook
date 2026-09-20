# Lineage inventory: nightly-amx-check-20260916.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/nightly-amx-check-20260916/gen_page.py`
- input: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/evidence.json`
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/` (1 preserved, 1 proposed preservation); `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/scratchpad/` (4 left behind (size)).
- regenerate: unavailable; generator has no output-path argument. evidence.json was authored from four GitHub Actions run logs, each above 5 MiB and listed as left behind (size). Binary and build identity records are provenance, not measured rate/time sources.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/gen_page.py` | `artifacts/intel-amx/exec/nightly-amx-check-20260916/gen_page.py`; preserved | 38502 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/evidence.json` | `artifacts/intel-amx/exec/nightly-amx-check-20260916/evidence.json`; propose preservation | 4413 |
| source | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/scratchpad/run-34925789174.log` | left behind (size) | 6264705 |
| source | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/scratchpad/run-35052594106.log` | left behind (size) | 6094372 |
| source | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/scratchpad/run-34923936332.log` | left behind (size) | 6183725 |
| source | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/scratchpad/run-35050734153.log` | left behind (size) | 6152205 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/slack-reports.tsv` | `artifacts/intel-amx/exec/nightly-amx-check-20260916/slack-reports.tsv`; preserved | 4141 |

Evidence:
- `artifacts/intel-amx/exec/nightly-amx-check-20260916/gen_page.py:2-7`
- `handoffs/claude_20260916-20260917_tron-amx-dispatch-in-ci-builds-after-pr3879.md:47-55,75-78`
