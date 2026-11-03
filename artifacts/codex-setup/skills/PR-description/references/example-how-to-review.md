# Worked example: How to review this PR

The section 4 of PR #4868 (positron-ai/tron, the VNNI K layout PR), as its author edited it on 2026-10-14. Three bold questions, bullets per file and per claim, a Verification bullet each. Pointers in brackets name sections of the same body.

## How to review this PR

**Can a raw pointer or a row-major view reach a VNNI-packed plane?**
- Read `h/tron/tensor/k_vnni.hpp`: `k_vnni_tensor` owns the plane, `k_vnni_view` reads it through `at(token, dim)`, and `detail::k_vnni_access` is the only route from a view to a plane address.
- Read `h/tron/models/kv_cache.hpp`: the row accessors `page::k()`, `kv_block::k_view` and `k_at` exist only for row-major slots, and `page::k_packed` is the read-only view the reader takes.
- The layout gate `k_vnni::layout_on<head_size>` depends only on storage geometry (head counts and dimensions). Every reader and writer of a slot therefore selects the same layout.
- Verification: the compile checks in `t_llama_unit` (a raw pointer cannot construct a view, a temporary owner cannot produce one, `at()` cannot write) and cases 1 and 2 of `t_k_vnni_layout` (the index map, and stores and loads in scrambled token order).

**Which pages take which scoring path with the option on, and what does the kill switch change?**
- Read `h/tron/models/self_attention.hpp`: `if constexpr` on the layout gate selects the reader for VNNI-packed K and the per-token dotters for row-major K. The dense-page AMX predicate carries `&& !k_vnni::layout_on<operation_head_size>`, the temporary gate, until the AMX kernel PR. Every VNNI-packed page therefore takes CPU software attention, through the reader, on every host.
- Read `save_k` in `h/tron/models/model.hpp`: one `page::set_k_row` per token, a 4-scatter store that touches 64 cache lines per token where the row-major store touches 4.
- With the option on, the kill switch keeps the layout and the reader.
- Verification: the `t_amx_dispatch_dtype` expectation under the option (Q is prepared, no dense kernel call), the four-binary decomposition and the token-identity table [Verification].

**Does each head keep its own scratch row until `gof::populate` has copied it?**
- Read `populate` in `src/tron/gof.cpp`: it allocates K scratch beside V scratch and collects every head's pointer before it copies the rows.
- Read the scheduler callback in `h/tron/scheduler/full.hpp`: it gathers a VNNI-packed row through `page::get_k_row` into the caller's 64-byte-aligned scratch, and returns the existing row pointer for row-major K.
- Verification: the populate case of `t_phase1_integration`, which compares every staged value through the K swizzle (the element transposition the FPGA expects), and its mutation check (a deliberate code change that the test must catch) [Builds and tests].
