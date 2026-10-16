# Draft parts for the PR 4424 body update (sections after "Words used here"); numbers to fill after the campaign

## Words used here: rows to add (after the "shared block save" row)

| row-major tail block | A 16-token block of a VNNI K plane whose 16 rows are not all saved yet. It holds its rows row-major (one contiguous 256-byte row per token) inside the block's own 4 KiB. Every row store into such a block writes 4 whole 64-byte lines, as the row-major layout does. Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`. |
| converted block | A block whose 16 rows are saved and whose bytes were transposed in place into the VNNI layout: by the whole-block save at once, or at the end of the forward pass that saved the 16th row. The page records per storage slot which rows are saved (`k_rows_saved_`) and which blocks are converted (`k_vnni_blocks_`). Note [K VNNI storage]. |
| hardware-scored operation | An attention operation whose scores come from the FPGA. Its K blocks are never converted: the FPGA staging reads the rows in place and the CPU scores only the tail the FPGA has not processed. Note [Row-major blocks under hardware attention] in `kv_cache.hpp` (the fix of issue #4500). |
| nightly CI, perf phase | The nightly System CI run of positron-ai/systems_test on delphi-3bda: 14 perf configs (model, tensor-parallel degree, user count, prompt length), 10 rounds each, through platformd and the Caddy proxy, with the tron deb installed from apt. |
| base deb, target deb | base deb = the nightly package 2026.10.08-be0d5565 (tron `main` at be0d5565b3, the commit this branch is synced to). target deb = this branch at <HEAD>, built with the deb preset plus `TRON_K_VNNI=ON`. |

## The changes: edits

- `h/tron/tensor/k_vnni.hpp` bullet: add
  - the row-major tail block operations `row_major_row` (a token's row inside a row-major block, as a typed row view), `store_row_major`, `load_row_major`, `block_to_vnni` and `block_to_rows` (the in-place conversion of one 16-token block), and Note [Row-major tail block]
- `kv_cache.hpp` bullet: add
  - Note [Row-major blocks under hardware attention].
  - The K layout state per page and storage slot (saved-row bits, converted-block bits; one extra entry for the EAGLE storage) with `note_k_row_saved`, `note_k_block_saved`, `k_block_to_vnni` / `k_block_to_vnni_at`, `k_vnni_blocks`, `k_storage_ref` / `k_storage_of`, `k_row_if_row_major` and `k_forget_row` (a new token at a page offset drops the bits above it and converts the offset's block back to row-major).
  - `set_k_row` / `get_k_row` follow the block's recorded layout. `set_k_block` stores whole blocks. `copy_storage_slot` carries the bits and converts through row-major rows.
- `model.hpp` bullet: add
  - A run shorter than a block is stored row by row into the row-major block. `save_k` records the rows of a software-scored operation; a block completed that way is queued (`pending_k_blocks_`) and converted at the forward end (`convert_pending_k_blocks`, after the cooperative GOF staging drained). The rows of a hardware-scored operation are not recorded, so their blocks stay row-major.
- `self_attention.hpp` bullet: add
  - The dense AMX path takes a page only when its 4 blocks are converted (`k_layout_dense`). The software loop scores the tokens of a row-major tail block with the row-major dotter (`row_major_row`) and the converted blocks with `k_vnni::qk_group`.
- FPGA staging bullet: add "A row of a row-major block is read in place (`k_row_if_row_major`)."
- Tests bullet: add
  - `t_k_vnni_layout`: the tail-block conversion (bit for bit against `store_row`), the page state across the 16th row, a forgotten row and a row saved again, the EAGLE storage view, forgetting a row in several slots, and page appends that carry the state.
  - `t_amx_dispatch_dtype`: a full page with unrecorded rows takes the software loop under `TRON_K_VNNI`.
  - `t_llama_unit`: the save_k case checks the queued block and its forward-end conversion, with a hardware-scored operation (no conversion) and with another operation hardware-scored (conversion); the apply-and-join case scores a page with converted and row-major blocks.

## Measurements: new subsection to add (whole machine, nightly configs)

### Nightly CI perf configs, whole machine, <date>

Setup: the nightly's own client (systems_test at 14f0ce4, `scripts/perf.py`) against rinzler engines provisioned by platformd 0.11 in the nightly layout (4 tp2 engines or 2 tp4 engines behind the Caddy proxy), 10 rounds per config, base deb vs target deb, two passes per deb (base, target, target, base). Extra cell: qwen3-4b tp2, 8 users, prompt 8192, `USE_HW_ATTN=0` (CPU attention), same client.

<TABLE: config | base TPS | target TPS | delta % (paired t) | base TTFT | target TTFT | delta | peak RSS base/target>

Reading: <llama-8b, qwen3-4b sw attention gains; others inside band; FPGA-attention qwen cells vs issue 4500; memory>.

## Verification: replace the head/commit sentences

The delphi-3bda runs below are from 2026-10-09 at 3723bf601a (unit tests from 2026-10-08).
<unit test table from exec/results/merge4737-20261008/tests-m4737.txt and tests-m4737rm.txt>
<host suite from exec/results/merge4737-precheck/host-suite-m4737.txt>
<token identity from exec/results/merge4737-precheck/smoke/*/smoke.txt: new==new2, newoff==new; new vs head; new vs base>
<runtron perf table from exec/results/m4737-E-cpu/summary.md: base vs this branch, cpu 1024/8192>

## Open items: edits

- DELETE "Stacked PR" item (PR #4737 is merged into this branch).
- ADD "deb preset": The `deb` configure preset (the package the nightly installs) sets `TRON_AMX_DISPATCH=ON` and not `TRON_K_VNNI=ON`. With this PR as it is, the production package keeps row-major K and none of the measurements above reach production. The target deb of the measurements adds the line locally. Decision: add `"TRON_K_VNNI": "ON"` to the deb preset in this PR (as PR #4505 did for the kernels), or leave it off and ship the layout later.
- "Kill switch and token divergence" item: keep; add "The tokens of a row-major tail block are scored by the row-major dotter in both the AMX-on and the kill-switch run, so the two runs of this binary stay identical."
- "128-dimension heads with kv_mul other than 4" item: keep as is (not re-measured).
- "A main test tolerance is widened" item: keep.
- "genoa96 cost row" item: keep.
