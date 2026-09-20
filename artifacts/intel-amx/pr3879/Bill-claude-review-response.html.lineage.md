# Lineage inventory: Bill-claude-review-response.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/pr3879/Bill-claude-review-response/gen.py`
- input: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/data.json`
- input built by: `artifacts/intel-amx/pr3879/Bill-claude-review-response/build_data.py`, `artifacts/intel-amx/pr3879/Bill-claude-review-response/apply_claimcheck.py`, `artifacts/intel-amx/pr3879/Bill-claude-review-response/apply_update_0911.py`, `artifacts/intel-amx/pr3879/Bill-claude-review-response/build_f10_extra.py`
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/` (1 preserved, 3 proposed preservation); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/more-testing-r1/` (2 proposed preservation).
- regenerate: `python3 artifacts/intel-amx/pr3879/Bill-claude-review-response/gen.py artifacts/intel-amx/pr3879/Bill-claude-review-response/data.json <OUT>`; unverified; data is authored review findings and the measured soak arena sizes cite preserved rinzler logs. Pinned Git code sources are not mirrored.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/gen.py` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/gen.py`; preserved | 19040 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/build_data.py` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/build_data.py`; preserved | 143126 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/apply_claimcheck.py` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/apply_claimcheck.py`; preserved | 23833 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/apply_update_0911.py` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/apply_update_0911.py`; preserved | 19333 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/build_f10_extra.py` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/build_f10_extra.py`; preserved | 14714 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/data.json` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/data.json`; propose preservation | 186086 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/static.json` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/static.json`; propose preservation | 5629 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/replies_v2.json` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/replies_v2.json`; propose preservation | 16960 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/Bill-claude-review-response/f10_extra.html` | `artifacts/intel-amx/pr3879/Bill-claude-review-response/f10_extra.html`; preserved | 18578 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/more-testing-r1/soak/rinzler.log` | `artifacts/intel-amx/exec/results/more-testing-r1/soak/rinzler.log`; propose preservation | 1810155 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/more-testing-r1/soak__off20/rinzler.log` | `artifacts/intel-amx/exec/results/more-testing-r1/soak__off20/rinzler.log`; propose preservation | 3951672 |

Evidence:
- `artifacts/intel-amx/pr3879/Bill-claude-review-response/gen.py:2-15`
- `artifacts/intel-amx/pr3879/Bill-claude-review-response/build_data.py:1-5`
