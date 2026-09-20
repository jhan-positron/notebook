# Lineage inventory: VNNI-K-FPGA-ATTN.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/vnnied-k-in-place/exec/gen_fpga_page.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/` (6 proposed preservation).
- regenerate: unavailable; generator has no output-path argument and writes the canonical page. The four measurement logs and two token-comparison inputs are inventoried from vnnik4-models-20260915.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/gen_fpga_page.py` | `artifacts/intel-amx/vnnied-k-in-place/exec/gen_fpga_page.py`; preserved | 32888 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/smoke/fpga__base.log` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/smoke/fpga__base.log`; propose preservation | 16007 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/smoke/fpga__new.log` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/smoke/fpga__new.log`; propose preservation | 15909 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/rt/fpga__base.log` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/rt/fpga__base.log`; propose preservation | 16726 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/rt/fpga__new.log` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/rt/fpga__new.log`; propose preservation | 16828 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/smoke/fpga__base.tokens` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/smoke/fpga__base.tokens`; propose preservation | 558 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/smoke/fpga__new.tokens` | `artifacts/intel-amx/exec/results/vnnik4-models-20260915/smoke/fpga__new.tokens`; propose preservation | 558 |

Evidence:
- `artifacts/intel-amx/vnnied-k-in-place/exec/gen_fpga_page.py:2-5`
