# Lineage inventory: block-store-animation.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/gen_page.py`
- input: `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/token21.json`, `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/block.json`
- input built by: `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/build-gt.sh`, `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/gt.cpp`
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/` (2 left behind (regenerable from preserved program and pinned Git source)); `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/shim/common/numerics/` (2 preserved).
- regenerate: unavailable; the two generated layout inputs are deliberately omitted as regenerable. Rebuilding them needs k_vnni.hpp from the external Git worktree pinned at 04ffeedccb. No generator check was run.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/gen_page.py` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/gen_page.py`; preserved | 71853 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/build-gt.sh` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/build-gt.sh`; preserved | 395 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/gt.cpp` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/gt.cpp`; preserved | 3559 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/token21.json` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/token21.json`; left behind (regenerable from preserved program and pinned Git source) | 13448 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/block.json` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/block.json`; left behind (regenerable from preserved program and pinned Git source) | 33246 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/shim/common/numerics/bf16.hpp` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/shim/common/numerics/bf16.hpp`; preserved | 786 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/exec/block-store-animation/shim/common/numerics/fp16.hpp` | `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/shim/common/numerics/fp16.hpp`; preserved | 136 |

Evidence:
- `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/gen_page.py:16-25`
- `artifacts/intel-amx/vnnied-k-in-place/exec/block-store-animation/build-gt.sh:6-8`
