# Lineage inventory: token30-results.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/dd/dd_report.py`
- input: `artifacts/intel-amx/exec/results/dd/build-record.txt`, `artifacts/intel-amx/exec/results/dd/campaign.txt`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-r2.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-r1b.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-archived-off1.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1c-vs-r1a.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r3a-prefix.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/flip-match.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r5.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4x.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r4.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r5.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-aa.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r3c.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r6-vs-r4.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r6-vs-r3a.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r5-vs-r4.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r3c-vs-r3a-tokens.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r6-footprint.txt`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-canon.txt`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-mirror.txt`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-trunc.txt`, `artifacts/intel-amx/exec/results/dd/verdict.html`, `artifacts/intel-amx/exec/results/dd/codex-response.html`
- input built by: `artifacts/intel-amx/exec/dd/dd-campaign-v3.sh`, `artifacts/intel-amx/exec/dd/dd_tokens.py`, `artifacts/intel-amx/exec/dd/dd_intermediates.py`, `artifacts/intel-amx/exec/dd/dd_logits_step.py`
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/` (7 left behind (size), 1 not produced (optional experiment not run), 4 preserved, 13 proposed preservation); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/slot1/` (1 proposed preservation); `delphi-3bda:/var/tmp/jhan/dd/` (8 left behind (size), 3 not produced (optional experiment not run), 23 proposed preservation).
- regenerate: `python3 artifacts/intel-amx/exec/dd/dd_report.py --res artifacts/intel-amx/exec/results/dd --out <OUT>`; Scratch preview exited 0 but failed comparison: seven direct layers JSON inputs exceed 5 MiB and are omitted. The rebuilt page loses those measured sections. Original remote intermediate captures were statted; eight exceed 5 MiB. Small token/log originals are proposed. Regenerate unverified; scratch output did not match. regenerate unverified (seven required layer JSON inputs exceed 5 MiB each and were omitted from the proposed input set)

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd_report.py` | `artifacts/intel-amx/exec/dd/dd_report.py`; preserved | 32903 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd-campaign-v3.sh` | `artifacts/intel-amx/exec/dd/dd-campaign-v3.sh`; preserved | 16220 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd_tokens.py` | `artifacts/intel-amx/exec/dd/dd_tokens.py`; preserved | 2220 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd_intermediates.py` | `artifacts/intel-amx/exec/dd/dd_intermediates.py`; preserved | 2601 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd_logits_step.py` | `artifacts/intel-amx/exec/dd/dd_logits_step.py`; preserved | 7292 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/build-record.txt` | `artifacts/intel-amx/exec/results/dd/build-record.txt`; preserved | 702 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/campaign.txt` | `artifacts/intel-amx/exec/results/dd/campaign.txt`; preserved | 20230 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-r2.json` | `artifacts/intel-amx/exec/results/dd/r1a-vs-r2.json`; propose preservation | 881 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-r1b.json` | `artifacts/intel-amx/exec/results/dd/r1a-vs-r1b.json`; propose preservation | 212 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1a-vs-archived-off1.json` | `artifacts/intel-amx/exec/results/dd/r1a-vs-archived-off1.json`; propose preservation | 1115 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r1c-vs-r1a.json` | `artifacts/intel-amx/exec/results/dd/r1c-vs-r1a.json`; left behind (not produced; optional r1c experiment was not run) | unavailable |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r3a-prefix.json` | `artifacts/intel-amx/exec/results/dd/r3a-prefix.json`; propose preservation | 41 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/flip-match.json` | `artifacts/intel-amx/exec/results/dd/flip-match.json`; propose preservation | 58 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4.json` | `artifacts/intel-amx/exec/results/dd/steps-r4.json`; propose preservation | 44340 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r5.json` | `artifacts/intel-amx/exec/results/dd/steps-r5.json`; propose preservation | 44355 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4x.json` | `artifacts/intel-amx/exec/results/dd/steps-r4x.json`; propose preservation | 173138 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r4.json` | `artifacts/intel-amx/exec/results/dd/layers-r4.json`; left behind (size) | 8145946 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r5.json` | `artifacts/intel-amx/exec/results/dd/layers-r5.json`; left behind (size) | 8109963 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-aa.json` | `artifacts/intel-amx/exec/results/dd/layers-aa.json`; left behind (size) | 5930148 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r3c.json` | `artifacts/intel-amx/exec/results/dd/layers-r3c.json`; left behind (size) | 8139672 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r6-vs-r4.json` | `artifacts/intel-amx/exec/results/dd/layers-r6-vs-r4.json`; left behind (size) | 5832208 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r6-vs-r3a.json` | `artifacts/intel-amx/exec/results/dd/layers-r6-vs-r3a.json`; left behind (size) | 8150102 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/layers-r5-vs-r4.json` | `artifacts/intel-amx/exec/results/dd/layers-r5-vs-r4.json`; left behind (size) | 8146334 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r3c-vs-r3a-tokens.json` | `artifacts/intel-amx/exec/results/dd/r3c-vs-r3a-tokens.json`; propose preservation | 878 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r6-footprint.txt` | `artifacts/intel-amx/exec/results/dd/r6-footprint.txt`; propose preservation | 0 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-canon.txt` | `artifacts/intel-amx/exec/results/dd/r7-canon.txt`; propose preservation | 51 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-mirror.txt` | `artifacts/intel-amx/exec/results/dd/r7-mirror.txt`; propose preservation | 51 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/r7-trunc.txt` | `artifacts/intel-amx/exec/results/dd/r7-trunc.txt`; propose preservation | 51 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/verdict.html` | `artifacts/intel-amx/exec/results/dd/verdict.html`; preserved | 23306 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/dd/codex-response.html` | `artifacts/intel-amx/exec/results/dd/codex-response.html`; preserved | 14173 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/dd/dd_first_divergence.py` | `artifacts/intel-amx/exec/dd/dd_first_divergence.py`; preserved | 7911 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/slot1/t1-quick/off1-2048.log` | `artifacts/intel-amx/exec/results/slot1/t1-quick/off1-2048.log`; propose preservation | 22929 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1a.tok` | `artifacts/intel-amx/exec/results/dd/original/r1a.tok`; propose preservation | 1080 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1a.log` | `artifacts/intel-amx/exec/results/dd/original/r1a.log`; propose preservation | 23284 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1b.tok` | `artifacts/intel-amx/exec/results/dd/original/r1b.tok`; propose preservation | 1080 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1b.log` | `artifacts/intel-amx/exec/results/dd/original/r1b.log`; propose preservation | 23054 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r2.tok` | `artifacts/intel-amx/exec/results/dd/original/r2.tok`; propose preservation | 1082 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r2.log` | `artifacts/intel-amx/exec/results/dd/original/r2.log`; propose preservation | 23058 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3a.tok` | `artifacts/intel-amx/exec/results/dd/original/r3a.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3a.txt` | left behind (size) | 12038105886 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3a.log` | `artifacts/intel-amx/exec/results/dd/original/r3a.log`; propose preservation | 17987 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3b.tok` | `artifacts/intel-amx/exec/results/dd/original/r3b.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3b.txt` | left behind (size) | 12038153973 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3b.log` | `artifacts/intel-amx/exec/results/dd/original/r3b.log`; propose preservation | 18097 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3c.tok` | `artifacts/intel-amx/exec/results/dd/original/r3c.tok`; propose preservation | 273 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3c.txt` | left behind (size) | 12038327919 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3c.log` | `artifacts/intel-amx/exec/results/dd/original/r3c.log`; propose preservation | 18058 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3x.tok` | `artifacts/intel-amx/exec/results/dd/original/r3x.tok`; propose preservation | 1080 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3x.txt` | left behind (size) | 468919001 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r3x.log` | `artifacts/intel-amx/exec/results/dd/original/r3x.log`; propose preservation | 23156 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4.tok` | `artifacts/intel-amx/exec/results/dd/original/r4.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4.txt` | left behind (size) | 12038042684 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4.log` | `artifacts/intel-amx/exec/results/dd/original/r4.log`; propose preservation | 17991 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4x.tok` | `artifacts/intel-amx/exec/results/dd/original/r4x.tok`; propose preservation | 1080 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4x.txt` | left behind (size) | 468918801 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r4x.log` | `artifacts/intel-amx/exec/results/dd/original/r4x.log`; propose preservation | 23175 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r5.tok` | `artifacts/intel-amx/exec/results/dd/original/r5.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r5.txt` | left behind (size) | 12038158134 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r5.log` | `artifacts/intel-amx/exec/results/dd/original/r5.log`; propose preservation | 17992 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r6.tok` | `artifacts/intel-amx/exec/results/dd/original/r6.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r6.txt` | left behind (size) | 12038452470 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r6.log` | `artifacts/intel-amx/exec/results/dd/original/r6.log`; propose preservation | 17995 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/forced.tok` | `artifacts/intel-amx/exec/results/dd/original/forced.tok`; propose preservation | 268 |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1c.tok` | left behind (not produced; optional r1c experiment was not run) | unavailable |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1c.txt` | left behind (not produced; optional r1c experiment was not run) | unavailable |
| original measurement source | `delphi-3bda:/var/tmp/jhan/dd/r1c.log` | left behind (not produced; optional r1c experiment was not run) | unavailable |

Evidence:
- `artifacts/intel-amx/exec/dd/dd_report.py:311-321,365-367`
