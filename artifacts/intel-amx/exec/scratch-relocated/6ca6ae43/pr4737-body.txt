Short version: This change addresses the decode slowdown tracked in #4500. Short writes to K (cached attention keys) use row-major storage, where each token's values are contiguous. Completed blocks convert to the VNNI layout (the pair-interleaved layout used by Intel AMX matrix instructions) only when software attention can use that conversion.

This draft is stacked on #4424. Its base is `jhan-amx-vnniK` at `30c4ac82cbb6959f7e4f66b29efb36f5e0749b48`; its head is `jhan-amx-vnniK-i4500` at `bb32a807743487c3d37d7e680f3cb369eb99e138`.

**Behavior**

- A write covering fewer than 16 tokens stores contiguous rows inside the block's existing storage. A full 16-token write still stores the VNNI layout directly.
- For software attention, completed row-major blocks convert in place after the model execution joins its workers and drains cooperative staging work.
- For operations configured to use FPGA attention (attention computed on programmable accelerator cards), short writes leave the blocks row-major. This avoids conversions and later gathers that the hardware path does not need.
- Each cache page records saved rows and converted blocks. Readers select the matching layout. Page copies and token reuse preserve that state.
- Hardware staging reads a row-major key directly. Converted keys still use the existing gather into temporary storage.
- Tests cover mixed layouts, conversion, copying, token reuse, attention dispatch, model saves, and the separate storage view used by EAGLE speculative decoding.

**Validation**

Checks run for this review:

- `git diff --check` passed.
- `clang-format-19 --dry-run -Werror` passed for all nine changed C++ files in the repository's Nix lint environment.

Results for commit 452b2052c9, recorded on September 30, 2026:

- With `TRON_K_VNNI=ON` (the layout build option): `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_llama_unit`, and `t_phase1_integration` all passed.
- With `TRON_K_VNNI=OFF`: `t_k_vnni_layout`, `t_amx_dispatch_dtype`, and `t_llama_unit` all passed.
- Source records: `intel-AMX/exec/results/i4500b-20260930/build-fixS1.txt`, `build-fixS1rm.txt`, `tests-fixS1.txt`, and `tests-fixS1rm.txt` in the development workspace.

Results for commit 9e813a8ce5 (the head bb32a80774 differs from it by one comment, one constant name, and two named literals returned to `1` and `true`), recorded on October 1, 2026, on delphi-3bda (our Intel test machine; fake device; socket 1):

- With `TRON_K_VNNI=ON`: `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_llama_unit`, and `t_phase1_integration` all passed, with the same assertion counts as at 452b2052c9.
- With `TRON_K_VNNI=OFF`: `t_k_vnni_layout`, `t_amx_dispatch_dtype`, and `t_llama_unit` all passed.
- Source records: `intel-AMX/exec/results/pr4737-review-20261001/tests-r1.txt` and `tests-r1rm.txt` in the development workspace.

Hardware measurements (TPS, TTFT, generated tokens) are from 452b2052c9. The three commits after it change a parameter type, comment passages, and literal spellings with the same values; they were not re-measured. The full host suite was not run.

Related: #4500, #4424.







