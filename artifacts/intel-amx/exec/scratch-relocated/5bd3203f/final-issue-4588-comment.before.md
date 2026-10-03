## Short version

All three reads named in this issue are fixed by PR #4698 (commit 63df10cf90, by a maintainer), merged into the PR #4557 branch as commit 8e0cf77bed. After that commit `h/tron/models/kv_cache.hpp` holds no `reinterpret_cast` to or from `bf16`. Closing.

## What changed, per read

- Read 1, `scaled_v_expr`: the member `data` is now `const bf16*`. Every tile address is computed in `bf16` units and passed to the load intrinsic as a `bf16` pointer. A script compared the old and new load addresses for head_size 64, 128, 256 and 512 in both lane widths. All are equal.
- Read 2, `fill_storage_slot`: `k` and `v` are filled as two separate arrays. No pointer crosses from `k` into `v`.
- Read 3, the 8-lane V accessors: `v` is declared `bf16 v[page_size * head_size]` in the 8-lane branch (the same form `k` took in c73e7fb2f9). `page::v`, `page::v_ptr`, `copy_storage_slot` and `page::scaled_v` build their views without a cast.

## Evidence

- PR #4698 CI: 21 of 21 checks pass.
- The PR #4698 commit message: AVX-512 `t_llama_unit` passed all 44 cases (252720 assertions). That run is the PR author's.
- On delphi-3bda (our Intel test machine) at the PR #4557 branch head faf8ee42ca, which holds the merge, on the AMX-on tree (AMX kernels compiled in) and the AMX-off tree (compiled out): t_llama_unit 44 cases / 244522 assertions on both trees (the test case "packed V rows keep their bits through set_v, get_v and at()" alone 20755), t_amx_numerics 12301 assertions on the AMX-on tree (1 on AMX-off, the AMX cases compiled out), t_amx_dispatch_dtype 1559 (1 on AMX-off), t_heterogeneous_scheduler 1900 on both trees, and `make lint-notes` rc 0 (no dangling Note reference). The `t_llama_unit` count differs from 252720. PR #4557 commit faf8ee42ca removed test-only checks of the dropped `v_vnni_row` type.
- In `t_llama_unit` the two `scaled_v_expr<64, 128>` functions (82 and 219 instructions) are identical before and after #4698 once addresses are normalized. #4698 changed the source form of the 16-lane loads and not the generated code.

## Still open, not tracked here

- The 8-lane (AVX2) hunks are not compiled or run by any CI job. The 8-lane `t_llama_unit` build has 131 errors before this change (none in kv_cache.hpp). The 8-lane hunks in `kv_cache.hpp` were checked by reading only.
- The items this issue lists as out of scope (EAGLE `x_data` casts, intrinsic and AMX tile loads, the discarded placement new in token_tree.hpp) keep no tracker.
- The Note this issue cites is now titled Note [VNNI Packed V layout] (h/tron/tensor/v_vnni.hpp, PR #4557 commit 76502ce5b2).
