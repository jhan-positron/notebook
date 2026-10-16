#!/usr/bin/env python3
# Rewrites the PR 4557 description for the third-review edits (commit 79478c254a and the style commit d9e7645fee).
# Usage: python3 patch-body.py <live-body.md> <results.json> > new-body.md
# results.json keys: head, date, unit (dict tree -> dict test -> text), lint_rc, ci, token_identity (text),
#   fn_diff (text), bench (dict with before/after times or null), bench_commit.
import json, re, sys

body = open(sys.argv[1]).read()
R = json.load(open(sys.argv[2]))
HEAD = R['head']


def rep(old, new, count=1):
    global body
    assert body.count(old) == count, (old[:90], body.count(old))
    body = body.replace(old, new)


# --- Short version: V_PLANE_ALIGNMENT_64 is gone since d9e7645fee ---
rep("- `v_vnni_tensor<Rows, Cols>`: the owner, one `bf16` array aligned to `V_PLANE_ALIGNMENT_64` bytes, trivially copyable, `as_view()` on lvalues only.",
    "- `v_vnni_tensor<Rows, Cols>`: the owner, one `bf16` array aligned to 64 bytes, trivially copyable, `as_view()` on lvalues only.")
rep("- `v_vnni_view<T, Rows, Cols>`: the address formula, a private pointer constructor, conversion from writable to const only, bounds-checked `at(token, dim)` for one element.",
    "- `v_vnni_view<T, Rows, Cols>`: the address formula, a private pointer constructor, conversion from writable to const only, a bounds-checked read `at(token, dim)` of one element. There is no element write: rows enter through `append_v_row` and `copy_token`, which keep the even/odd partner rule (tested with `STATIC_REQUIRE`).")
rep("- `detail::v_vnni_access`: the plane and pair-base addresses for the kernels and the bulk operations.",
    "- `detail::v_vnni_access`: the plane and pair-base addresses for the kernels and the bulk operations. `pair_base` asserts `token < Rows` (`TRON_ASSERT` is active in release builds): one compare-and-branch per row operation.\n"
    "  - `const_v_row_view<T, Cols, Dma>` / `v_row_view<T, Cols, Dma>`: aliases of the row-major `const_view` / `view` for one contiguous, aligned, unit-stride transfer row of `Cols` elements (the row `set_v` reads and `get_v` writes, not packed storage). `v_source_row<Cols, Dma>(const T*)` / `v_destination_row<Cols, Dma>(T*)` build them from a pointer and assert that the pointer is 64-byte aligned (one compare-and-branch per call). They are the one place where a raw pointer acquires the `aligned` view flag that selects the aligned vector loads and stores. The maintainer contributed the four aliases through PR #4697, merged into this branch.")
rep("- The packed operations moved here from `kv_cache.hpp` with their bodies unchanged: `append_v_row` (one token's row in, under the even/odd partner rule), `load_row` (one row out), `copy_token` (token to token).",
    "- The packed operations moved here from `kv_cache.hpp` with their bodies unchanged: `append_v_row` (one token's row in, under the even/odd partner rule), `load_row` (one row out), `copy_token` (token to token). They require only `Cols % chunk_size == 0` (the static_assert of the view and the owner). `page::set_v` and `page::get_v` keep their `head_size % 32 == 0` clauses from `main`.")
# --- kv_cache.hpp bullets: the two maintainer PRs merged into this branch ---
rep("`k_view` now builds its views from this array with no `reinterpret_cast`. The V reads do the same since the maintainer's PR #4698 (merge commit 8e0cf77bed): `scaled_v_expr` and `fill_storage_slot` read `bf16` arrays without a cast.",
    "`k_view` now builds its views from this array with no `reinterpret_cast`. `fill_storage_slot` (the fixture fill of one slot) does the same: it writes `block.k` directly and reaches the V plane through `v_vnni_access::plane`, with no cast of the block address. That change is the maintainer's, contributed as PR #4698 and merged into this branch (merge commit 8e0cf77bed), not into `main`.")
rep("(`const_v_row_view<Source, head_size, Dma>` and `v_row_view<Destination, head_size, Dma>`, the aliases from the maintainer's PR #4697, defined in `v_vnni.hpp`) instead of a pointer.",
    "(`const_v_row_view<Source, head_size, Dma>` and `v_row_view<Destination, head_size, Dma>`, defined in `v_vnni.hpp` and contributed by the maintainer through PR #4697 into this branch) instead of a pointer.")
rep("- `scaled_v_expr` (the software path's weighted sum) takes the packed view.",
    "- `scaled_v_expr` (the software path's weighted sum) takes the packed view and reads the plane through `v_vnni_access::plane`. This PR also rewrites its tile addressing (part of PR #4698). `data` is `const bf16*` instead of `const bf16s*` (one 16-lane vector). The three AVX-512 accumulate loops (head size 64, head size 128, and the 16-chunk helper that serves 256 and 512) form the tile address in `bf16` elements, `tile = data + i * head_size + 2 * chunk_size * chunk_offset`, and load `tile + 2 * chunk_size * k`. `main` formed it as a vector pointer, `tile = reinterpret_cast<const bf16x32*>(data + i * (head_size / chunk_size)) + chunk_offset`, and loaded `tile + k`, where `bf16x32` is a 32-element vector. Head sizes 64 and 128 have `chunk_offset` 0 and omit the term. The byte addresses are the same: `bf16s` holds 16 elements and `bf16x32` holds 32.")
# --- #4424 table: at() reads ---
rep("Single elements go through `at(token, dim)`. |", "Single elements are read through `at(token, dim)`. |")
rep("`v_vnni_view` is a plain struct with `at()` and the bulk operations. |", "`v_vnni_view` is a plain struct with a read-only `at()` and the bulk operations. |")
# --- Verification: instruction comparison ---
rep("- Instruction-identical: the moved bodies, that is `set_v` even/odd for bf16, float and fp16, `get_v` even/odd for float and bf16, and the `scaled_v` weighted sum.",
    "- Instruction-identical in that comparison: the moved bodies, that is `set_v` even/odd for bf16, float and fp16, `get_v` even/odd for float and bf16, and the `scaled_v` weighted sum. Since " + HEAD + " the moved bodies differ from `main` by one compare-and-branch per `pair_base` call (the bounds assert below).")
rep("- Differ by addressing only: the `page::set_v` / `page::get_v` wrappers that take the token index at run time (one scalar `add` fewer), and the `book::append` copy closure (same vector instructions, different scalar address arithmetic).",
    "- Differ by addressing only in that comparison: the `page::set_v` / `page::get_v` wrappers that take the token index at run time (one scalar `add` fewer), and the `book::append` copy closure (same vector instructions, different scalar address arithmetic). Since " + HEAD + " the wrappers also carry the alignment compare-and-branch of `v_source_row` / `v_destination_row`.")
rep("- One difference found and removed: a bounds assert in `detail::v_vnni_access::pair_base`, which `append_v_row`, `load_row` and `copy_token` call, sat on a frequently executed path. The second commit removed it (`TRON_ASSERT` is active in release builds).",
    "- Two deliberate differences from `main`, both added for the third review (" + HEAD + "): `detail::v_vnni_access::pair_base` asserts `token < Rows`, and `v_source_row` / `v_destination_row` assert the 64-byte alignment of the row pointer. Each is one compare-and-branch per row operation plus a rarely executed abort block (`TRON_ASSERT` is active in release builds). `pair_base` is called once per `set_v`, once per `get_v` and twice per token copied by `book::append`. The K save route pays a bounds check at the same granularity in `view::operator[]`.\n"
    "- Rewritten `scaled_v_expr` loops: `objdump -d` of `t_llama_unit` from two builds of this branch, one without and one with the addressing rewrite of PR #4698 (local review tree a0e8d7155e, delphi-3bda, 2026-09-30). The two `scaled_v_expr<64, 128>` functions (head size 128) have 82 and 219 instructions in both binaries and are identical after address normalisation. The head-size-64 loop and the 16-chunk helper (256, 512) have no disassembly comparison and rest on the element arithmetic described above. The token identity in the Status section (qwen3-4b, head size 128) runs the head-128 loop in the kill-switch arm against `main`.\n"
    "- Production code at " + HEAD + " against c5d44bd86f (`runtron` built from both, `objdump -d`, functions matched by name, addresses normalised): " + R['fn_diff'] + "")
# --- Status section: replace from "## Status" to "## Labels" ---
unit_rows = "\n".join(f"| {tree} | {test} | {text} |" for tree, tests in R['unit'].items() for test, text in tests.items())
bench = R.get('bench')
if bench:
    bench_txt = (f"Benchmark row (`config/test-benchmarks.json`, block `granite_rapids_6962p`, `bin/slice bench --update t_llama_unit` on delphi-3bda, {R['date']}, whole machine, serving stopped): "
                 f"t_llama_unit {bench['before']} s before, {bench['after']} s after, at 1, 2 and 4 slices (a slice is one accelerator card with its CPUs and memory). Committed as {R['bench_commit']}. {bench['attribution']}")
else:
    bench_txt = "Benchmark row: " + R.get('bench_note', 'not yet refreshed.')
status = f"""## Status ({R['date']})

The branch is {R['n_commits']} commits on top of `main` dd6e85226b: c5d44bd86f (the typed tensors), d9e7645fee (shared files keep their local constant spelling, the second reviewer's style comment), {HEAD} (the third review's edits: the two asserts, no width rule, no element write){R.get('extra_commits', '')}. The reviewed history before the squash is kept on the branch `jhan-kv-typed-tensors-pre-squash-20261006`, so every commit id named in this description stays reachable.

Unit tests at {HEAD} on delphi-3bda (an Intel machine with AMX), {R['date']}. Two trees: the AMX-on tree (`gen`, AMX kernels compiled in) and the AMX-off tree (`gen-amxoff`, compiled out). Every run has rc (return code) 0 and prints "All tests passed".

| Tree | Test | Result |
|---|---|---|
{unit_rows}

`make lint-notes` (the repo's checker of Note references) rc {R['lint_rc']} at {HEAD}. {R['ci']}

Token identity at {HEAD} against `main` dd6e85226b on delphi-3bda, {R['date']} (runtron, qwen3-4b tp2, one user, temperature 0, seed 1, `--pay-for-determinism`, prompt 1024, 256 generated tokens): {R['token_identity']}

{bench_txt}

"""
i = body.index("## Status (")
j = body.index("## Labels")
body = body[:i] + status + body[j:]
sys.stdout.write(body)
