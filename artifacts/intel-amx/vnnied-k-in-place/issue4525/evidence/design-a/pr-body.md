The KV cache now owns `bf16[]` arrays directly. Previously, `book` owned byte arrays, then `construct_kv_blocks()` created a second object hierarchy over those bytes. This change removes that construction pass and returns ordinary typed views of existing scalar elements.

Draft child of #4557, based on `jhan-kv-typed-tensors`. Keep this PR draft until its parent merges.

## Changes

- The fallible DMA helper calls a DMA-specific allocating `operator new[]` directly. That operation obtains the memory and provides implicit object creation under [C++23 N4950, object model paragraph 13](https://timsong-cpp.github.io/cppwp/n4950/intro.object#13). It adds no raw-address placement construction, initialization pass, or array-expression bookkeeping. Existing failure injection and allocation/release byte counts are preserved. Element-count overflow is rejected.
- Retained storage and sliding chunks own `unique_dma<bf16[]>`. Private `kv_page_view` values select adjacent K and V regions. The packed-V owner remains available for standalone storage.
- Removed the overlaid `kv_block` type, block-pointer casts, and whole-block scalar reinterpretation. Vector-load addresses are calculated within the actual scalar array in both lane-count configurations.
- Existing test cases now check physical K/V adjacency, slot stride, plane alignment, and multi-byte allocation-count overflow.

The intended byte order, packed-value arithmetic, partner initialization, retention groups, EAGLE offsets, and restore publication rules are preserved. No kernel signature changes are needed.

Words used here: KV is the saved key/value cache; bf16 is its 16-bit floating-point element; DMA is direct memory access by the device; EAGLE is the speculative model; AMX is Intel's tile matrix instruction set.

## Validation

Completed:

- Clang-format 19.1.7 on all six changed C++ files.
- `git diff --check`.
- Source-note checker: exit 0, with unreferenced-note warnings.
- Independent cache-source review and arithmetic enumeration: 1,920 packed-vector addresses, 7,680 row-major-vector addresses, and 3,300 slot/page offsets matched the old formulas. This script checks transcribed formulas; it does not compile or execute the C++.
- Verified that required host CI executes the existing `t_llama_unit` and `t_heap_v2` cases through their unchanged suites: [parent Test host job](https://github.com/positron-ai/tron/actions/runs/35942439015/job/107458951465). This is collection/execution evidence for the parent, not a pass for this change.

Pending:

- Compilation, focused cache/heap tests, AMX-on tests, the 8-lane configuration, `make build-test`, and `make test-host`.
- Required test-cost metadata refresh for the two changed test binaries.
- Generated-code comparison and performance measurements.

The build host sw-dev-01 has an unverified changed SSH host key. The test host delphi-3bda has an active CI lease. No C++ build or runtime test was launched. This draft makes no claim of compiled correctness or performance neutrality.

The two commits separate the allocation contract from the cache migration. Existing unrolled vector indices and zero-based loop bounds retain the surrounding code's literal style.

