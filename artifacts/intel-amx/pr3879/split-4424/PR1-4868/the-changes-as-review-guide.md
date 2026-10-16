## How to review this PR

Three threads carry the risk of this change. Each names the question to answer, the files to read, and the test that pins the answer.

**Thread 1: the type boundary and the layout gate.** Question: can a raw pointer or a row-major view reach a VNNI-packed plane, and do every reader and writer of a slot select the same layout?

- Read `h/tron/tensor/k_vnni.hpp`: `k_vnni_tensor` owns the plane, `k_vnni_view` reads it through `at(token, dim)`, and `detail::k_vnni_access` is the only route from a view to a plane address. `store_row` and `load_row` assert the token index before they compute a scatter or gather address.
- Read `h/tron/models/kv_cache.hpp`: `kv_block::k` is a `k_vnni_tensor` for a 128-dimension head when the option is on. The row accessors `page::k()`, `kv_block::k_view` and `k_at` exist only for row-major slots (`requires` clauses). `page::k_packed` is the read-only view the reader takes.
- The gate `k_vnni::layout_on<head_size>` depends only on storage geometry, so query type and AMX availability cannot split readers from writers.
- Pinned by: the compile checks in `t_llama_unit` (a raw pointer cannot construct a view, a temporary owner cannot produce one, `at()` cannot write, `page::k_packed` exists exactly when the option selects the layout) and cases 1 and 2 of `t_k_vnni_layout` (index map, store and load in scrambled order).

**Thread 2: what runs with the option on, and what the kill switch changes.** Question: on an AMX host with the option on, which pages take which scoring path, and why does decode TPS fall at this head?

- Read `h/tron/models/self_attention.hpp`: `if constexpr` on the layout gate selects the reader for VNNI-packed K and the per-token dotters for row-major K. The dense AMX predicate carries `&& !k_vnni::layout_on<operation_head_size>`, the temporary gate, until the AMX kernel PR. Every VNNI-packed page therefore uses the software loop on every host.
- Read `save_k` in `h/tron/models/model.hpp`: one `page::set_k_row` per token, a 4-scatter store that touches 64 cache lines per token where the row-major store touches 4. That is the prefill cost until the block-save PR.
- With the option on, the kill switch (`TRON_AMX_DISABLE=1`) keeps the layout and the reader. It changes no scoring path for 128-dimension heads in this PR. [Open items, issue #4444]
- Pinned by: the `t_amx_dispatch_dtype` expectation under the option (Q is prepared, no dense kernel call), the four-binary decomposition under Measurements, and the token-identity table (`newoff` equals `new` in every cell).

**Thread 3: the one pointer that crosses into the FPGA path.** Question: does each head keep its own scratch row until `gof::populate` has copied it?

- Read `src/tron/gof.cpp` (`populate` allocates K scratch beside V scratch and collects every head's pointer before it copies) and the scheduler callback in `h/tron/scheduler/full.hpp` (`page::get_k_row` gathers a VNNI-packed row into the caller's 64-byte-aligned scratch; row-major K returns the existing row pointer).
- Pinned by: the populate case of `t_phase1_integration`, which compares every staged value through the K swizzle, and its mutation check under Verification (the per-head stride removed, the case fails).
