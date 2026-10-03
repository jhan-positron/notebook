# Port PR #4557 (typed KV tensors) into PR #4424 (VNNI K): ordered implementation plan

## Short version

The merge of the PARENT into the CHILD is already resolved and staged in the worktree, and the four K test binaries compile with TRON_K_VNNI ON and OFF on claude-box. The remaining work is one CMake fix, then a header split that gives the K plane a typed owner and view (mirroring the parent's V types), then typed row arguments and compile-time contracts, then PR hygiene. Three items need the user: the push target, whether the worker-index merge is in scope, and authorization for the whole-machine benchmark refresh.

## Words used here

- PARENT: `origin/jhan-kv-typed-tensors` = c12df586b6 = PR #4557 ("Typed KV-cache tensors for packed V and native K").
- CHILD: `origin/jhan-amx-vnniK` = 30c4ac82cb = PR #4424 ("VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout").
- worktree: `/home/jhan/workspace/ai-runs/tron-vnnik-typed`, branch `jhan-amx-vnniK-typed`, HEAD = CHILD, MERGE_HEAD = PARENT. Every path is staged. `git grep '^<<<<<<< '` finds nothing (checked 2026-10-02).
- VNNI: Vector Neural Network Instructions. The term names the pair-interleaved operand layout of the bf16 dot-product instructions. AMX: Intel Advanced Matrix Extensions (tile instructions).
- K plane: the K values of one KV head in one 64-token page, 16384 bytes.
- owner / view: `k_vnni_tensor` holds a plane's bytes. `k_vnni_view` refers to a plane and knows its address map. These mirror the PARENT's `v_vnni_tensor` / `v_vnni_view` (h/tron/tensor/v_vnni.hpp:103-185 at PARENT).
- 16-lane build: `TRON_CHUNK_SIZE == 16` (AVX-512). The packed operations exist only there.
- goals (a)-(d): (a) compiles and passes tests with TRON_K_VNNI ON and OFF; (b) typed K owner and view; (c) no raw K-plane pointer crosses the cache/kernel boundary; (d) stored bytes and scores unchanged.
- Line numbers below are worktree (merged tree) line numbers unless marked "at CHILD" or "at PARENT".

## Verified starting state

- `git -C <worktree> status --short`: all formerly conflicted files (`config/test-benchmarks.json`, `h/tron/models/common.hpp`, `h/tron/models/kv_cache.hpp`, `h/tron/models/self_attention.hpp`, `src/tron/kernels/amx_attn.cpp`, `t/t_amx_dispatch_dtype.cpp`, `t/t_llama_unit.cpp`) are `M ` (staged). MERGE_HEAD exists, so the merge is not yet committed.
- `gen/` (clang++-19 from nix, RelWithDebInfo, TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON, AVX512=ON, BUILD_INGEST/TEST/PRODUCTION_MODELS=OFF) holds `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_k_vnni_layout`, `t_llama_unit` built 2026-10-02 10:23-10:25. `gen-rm/` (TRON_K_VNNI=OFF) holds `t_k_vnni_layout` and `t_llama_unit` built 10:28-10:29. So the merged tree compiles for these targets in both configurations. No test run has been recorded.
- nix works on claude-box again (`~/.nix-profile/bin/nix`, `/nix/store` present). claude-box is AMD (no AMX): `t_amx_numerics` warns and skips its AMX cases there.

## Decisions taken (resolve the disagreements between the seven maps)

- D1 Row views. `const_k_row_view<Cols, Aligned, Dma>` = `const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>` and `k_row_view<Cols, Aligned, Dma>` = `view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>`. Helpers `k_source_row<Cols, Aligned = VIEW_ALIGNED_TRUE, Dma = VIEW_DMA_FALSE>(const bf16*)` and `k_destination_row<Cols, Aligned = VIEW_ALIGNED_TRUE, Dma = VIEW_DMA_FALSE>(bf16*)`. The element type is fixed to bf16: every K row in the CHILD is bf16 (`scatter_row(bf16*, size_t, const bf16*)` at CHILD k_vnni.hpp:139; model.hpp converts other types into `conv` first, worktree 2899-2940). Parameter order Aligned, Dma follows `view`'s own order and the design table. The PARENT's V aliases are not reused because they fix `VIEW_ALIGNED_TRUE` (v_vnni.hpp:209-213 at PARENT) and the design says K keeps the caller's flag. Call sites use the helpers, as the PARENT does with `v_source_row` (model.hpp:3135, full.hpp:2773).
- D2 Worker-index merge (design "Worker-index request", [S18]/[S21]). Deferred to an optional Stage 4 behind question Q2. It is not needed for goals (a)-(d), it changes the generator (`ingest/src/TronCpp.hs`) and 7 spec assertions, it has no reviewer source (neither review 5270587330 nor sketch 5765866077 mentions it), and it overlaps PR #4737's model.hpp changes (+88 lines). The CHILD at 30c4ac82cb still has two separate pairs (`save_k(..., size_t n_workers = 1)` at worktree 3081/3089; `save_k_helper(..., worker_ix, n_workers)` at 2969-2990), so the item is real, not already done.
- D3 Shape pin. Both K classes carry `static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128)` in their bodies, not a `requires` clause and not the sketch's `%16 / %32` form. Reason: `k_vnni::index` hard-codes `TOKEN_BLOCKS_4`, `STEP_PAIRS_16`, `BLOCK_TOKENS_16`, `PAIR_2` (CHILD k_vnni.hpp:101-107), so no other shape is addressable. `std::conditional_t` only names the unselected `k_vnni_tensor<64, 64>` (gpt-oss heads), which does not instantiate it, so the assert never fires for native geometries.
- D4 K `copy_token`. Added, with one consumer (the partial-range branch of `copy_storage_slot`). Its body is the CHILD's loop (gather into a 64-byte-aligned local row, then scatter; worktree kv_cache.hpp:2353-2360). The design asks for "typed K token copies" and forbids only a plane-copy helper.
- D5 16-lane guards. The operation bodies (`store_row`, `load_row`, `store_block`, `copy_token`, the `k_vnni::detail` helpers) and `qk_group` go under `#if TRON_CHUNK_SIZE == 16`. The classes, constants, `layout_on`, `index`, the row aliases and helpers stay outside the guard. The tensor header includes `tron/simd/auto.hpp`, which is the only place that defines `TRON_CHUNK_SIZE` (auto.hpp:17-21 at PARENT); without it `#if TRON_CHUNK_SIZE == 16` is `#if 0 == 16` and the operations vanish silently. No other new guards anywhere. The `#error` block stays (worktree kv_cache.hpp:36-41). origin/main has removed 8 lanes (commits 8d64eeed81, bbc702251e), so these two guard pairs become one trivial deletion hunk at the later main merge; the base 996f58ec82 still has 8 lanes, so the guard is correct for this branch.
- D6 `at(token, dim)` on `k_vnni_view`: included, bounds-checked, mirroring `v_vnni_view::at` (v_vnni.hpp:119-134 at PARENT). Consumers: the `matrix_at_writes` probes in t_llama_unit (Stage 2.3).
- D7 `detail::k_vnni_access` lives in `tron::detail` (parallel to `tron::detail::v_vnni_access`). Inside `namespace tron::k_vnni` the name `detail` means `tron::k_vnni::detail` (CHILD k_vnni.hpp:109-133), so qk_group writes `tron::detail::k_vnni_access`.
- D8 Note [K VNNI storage] stays in kv_cache.hpp (worktree 657-712). Its eight cross-references (model.hpp:2752, full.hpp:2753, gof.hpp:71, amx_attn_iface.hpp, self_attention.hpp, amx_attn.cpp) stay valid.
- D9 Tile-name unification in `qk_vnni_128x4` (file-scope `ACCUMULATOR_TILE_*` vs the CHILD's local `Q_TILE_4`, `K_TILE_5`, `K_TILE_6`, `S_TILE_0..3`, worktree amx_attn.cpp:259-265): COULD, default skip. The two naming schemes exist after the plain merge, so the port does not cause them, and the kernel is numerics-sensitive.
- D10 Operation names and namespaces. `store_row`, `load_row`, `store_block`, `copy_token` are free functions in `namespace tron`, overloading the V functions on the view type (the PARENT puts `append_v_row`, `load_row`, `copy_token` in `tron`). Constants, `layout_on`, `index` and `qk_group` stay in `tron::k_vnni` (the test anchors spell `tron::k_vnni::index`, t_k_vnni_layout.cpp:81-90).
- D11 Git strategy. Merge-based, on the existing branch `jhan-amx-vnniK-typed`: merge commit, then adaptation commits. No history rewrite of `jhan-amx-vnniK`, so PR #4737 keeps its merge base 30c4ac82cb. Tag the old head locally (`jhan-amx-vnniK-pre-typed`). The push target is question Q1.
- D12 Start now, do not wait. The PARENT is CHANGES_REQUESTED and CONFLICTING with main, so its head will move. With a merge-based branch, taking a new PARENT head is `git merge origin/jhan-kv-typed-tensors`; the K port touches the PARENT's files only in kv_cache.hpp, self_attention.hpp and t_llama_unit.cpp, so re-merge conflicts stay local to those files.
- D13 The design's `using native_k_storage = bf16s[page_size][head_size / chunk_size];` is superseded by the PARENT's `bf16 k[page_size * head_size]` (worktree kv_cache.hpp:2638; PR 4557 body: "kv_block::k is a plain bf16 array"). The native branch is `bf16[page_size * head_size]`.
- D14 Stage 1 keeps the CHILD's raw plane access (`reinterpret_cast` on the bf16 array compiles unchanged against the PARENT's array). The one semantic fix in Stage 1 is the CMake define for the generated model objects (below).

---

## Stage 1 - Merge commit (compile-level port)

### 1.1 Verify the present resolution, block by block

The worktree already holds a resolution. Check each block against this specification before committing. Fix any deviation; otherwise leave the file alone.

| File | Block | Required content | Present? |
|---|---|---|---|
| `h/tron/models/common.hpp` | lines 3-8 | `<algorithm>` (main's), `<array>`, `<atomic>` (CHILD's, used by `k_store_window_t`), then `<compare>`, `<cstdint>`, `<span>` | yes (3-8) |
| `h/tron/models/kv_cache.hpp` | former markers 1981-2122 | CHILD K accessors (`k_vnni_plane` 1981-1992, `set_k_row` 1994-2010, `set_k_block` 2019-2031, `get_k_row` 2035-2048, uniform forms 2051-2065) followed by the PARENT's `// The actual V data for a token in this page.` block (2066) with typed `set_v`/`get_v` declarations and `v_packed` (2118-2126). The five stale `v_data` comment lines ("Pointer to this page's V values ...", CHILD 1767-1771) must be absent | yes (grep for "Pointer to this page's V" is empty) |
| `h/tron/models/self_attention.hpp` | 1655-1675 | CHILD's `if constexpr (k_vnni::layout_on<operation_head_size>)` calling `qk_vnni_128x4(pg.template k_vnni_plane<...>, ...)`; else branch = PARENT's `qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head), ...)`; no `k0` / `k0.data` left; merged comment names both layouts | yes (grep `k0` empty) |
| `src/tron/kernels/amx_attn.cpp` | 13-18, 226-300 | all four includes (`kernels/k_vnni.hpp`, `tensor/kv_cache_fwd.hpp`, `tensor/v_vnni.hpp`, `tensor/view.hpp`); CHILD's `pack_q_rows_128x4` + `qk_vnni_128x4` definitions followed by the PARENT's typed `weights_times_v_128x4` | yes |
| `t/t_amx_dispatch_dtype.cpp` | 105-107, 199-212 | fill loop: CHILD `page->set_k_row(slot, 0, token, zero.data())` + PARENT `set_v(..., v_source_row<head_size>(zero.data()))`; fakes: PARENT typed `qk_rowmajor_128x4`, CHILD `pack_q_rows_128x4`, CHILD raw `qk_vnni_128x4(const bf16*, const bf16*, float*, size_t)`, PARENT typed `weights_times_v_128x4` | yes |
| `t/t_llama_unit.cpp` | 141-152 | one probe with two parameters: `bf16* k_output` for `get_k_row` and the PARENT's typed `view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<head_size>, sseq<1>> output` for `get_v` | yes |
| `t/t_llama_unit.cpp` | 3264-3516 and 3518-end | both appended cases: CHILD "save_k stores every token's K row once ..." and PARENT "packed V rows keep their bits ..." under `#if TRON_CHUNK_SIZE == 16` | yes |
| `t/t_llama_unit.cpp` | main-drift tests (added by main between the two bases, commit 1ca3a70e21) | "Sliding KV chunks reserve and restore transactionally" writes/reads K through `set_k_row`/`get_k_row` (767-778); "page K views preserve geometry and row addressing" guards slot 1 (geometry_128) with `if constexpr (k_vnni::layout_on<...>)` + `STATIC_REQUIRE_FALSE(page_k_accepts_geometry<...>)` (1070-1074). Without these, TRON_K_VNNI=ON does not compile, because every `page::k` overload is constrained with `!k_vnni::layout_on` (1914-1979) | yes |
| `t/t_amx_numerics.cpp` | 233-236 (auto-merged) | `qk_rowmajor_128x4(tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, ...)` (the PARENT's typed declaration); `qk_vnni_128x4(plane->v, ...)` stays raw in Stage 1 | yes |
| `config/test-benchmarks.json` | granite_rapids_6962p block | PARENT (= main) rows throughout, including `t_llama_unit` 5.187/5.256/4.936 s, 331 MB (line 424) and `t_amx_numerics` 0.903/0.698/0.58 s (476); plus the CHILD's `t_k_vnni_layout` row 0.709/0.697/0.696 s, 9/8/8 MB once (478, after `t_amx_dispatch_dtype`). `python3 -m json.tool` parses it; no duplicate names. Row position is immaterial: `bin/slice` matches rows by name | yes |

Files that merged without conflict and were reviewed semantically (no Stage 1 change): `h/tron/models/model.hpp` (exact textual union; K writes at 2889, 2936, 2940, 2957; V writes at 3134-3140), `h/tron/scheduler/full.hpp` (k_head_fn 2747-2762 is the CHILD's 3-parameter form), `h/tron/gof.hpp`, `src/tron/gof.cpp`, `ingest/src/TronCpp.hs`, `ingest/test/LoopyTronSpec.hs` (generated `save_k`/`save_k_helper` calls match the merged signatures: 3 and 4 arguments), `t/t_gof_dma.cpp`, `t/t_gof_staging_leaks.cpp`, `t/t_phase1_integration.cpp`, `t/heterogeneous_scheduler_compile.cpp` (256-dim head, native in both builds), `t/t_heap_v2.cpp`, `t/CMakeLists.txt`, `.github/workflows/cmake-single-platform.yml` (356 `-DTRON_K_VNNI=ON`), `README.ci.md` (550, 573-583).

### 1.2 MUST: define TRON_K_VNNI for the generated model objects

- File: `src/tron/CMakeLists.txt`. Main commit 0128331632 (between the two bases) compiles `gen/src/tron/model_<arch>.cpp` as OBJECT libraries that link only `tron_model_compile_config`, an INTERFACE library that does not link `tron` (worktree 316-324, 359-364). Its defines are listed by hand: `TRON_AVX512_ENABLED`, `TRON_DISTRIBUTED`, `TRON_AMX_DISPATCH`, `TRON_PAGE_SHARE_COUNTERS` (335-352). The CHILD's `TRON_K_VNNI` is PUBLIC on `tron` only (226-240). Result without the fix: every model object compiles kv_cache.hpp / model.hpp / self_attention.hpp with `k_vnni::layout_on == false` while libtron and the schedulers use the VNNI layout. That is an ODR violation and wrong K bytes at run time, with no compile error. The CHILD's base c7844ca2ce predates this restructuring, which is why the CHILD's CI passed.
- Edit: insert after the `if(TRON_AMX_DISPATCH) ... endif()` block at 345-348, before the `TRON_PAGE_SHARE_COUNTERS` block:

```cmake
if(TRON_K_VNNI)
  # The generated model objects compile kv_cache.hpp and model.hpp too. They
  # must see the same K layout as the tron library (TRON_K_VNNI block above).
  target_compile_definitions(tron_model_compile_config INTERFACE
    TRON_K_VNNI)
endif()
```

- Check: in a configuration that builds at least one model (BUILD_TEST_MODELS=ON or the 3bda build), `ninja -C gen -t commands tron_model_<arch>_objects | grep -c -- -DTRON_K_VNNI` is greater than 0 (`<arch>` from `TRON_MODEL_ARCHITECTURES`, src/tron/CMakeLists.txt:105-112). The claude-box gen/ has all model options OFF, so this check needs the 3bda build.

### 1.3 Build and test gate (Stage 1)

- claude-box, inside the nix shell: `~/.nix-profile/bin/nix develop --accept-flake-config --command bash -c 'ninja -C gen -j 20'` (everything, TRON_K_VNNI=ON) and the same for `gen-rm` (OFF). Run from the repo root: `env -u SYSTEM_CONFIG ./gen/t_llama_unit --skip-benchmarks`, `./gen/t_k_vnni_layout`, `./gen/t_amx_dispatch_dtype`, `./gen/t_amx_numerics` (expect the "AMX unavailable" WARN on AMD), `./gen/t_heterogeneous_scheduler`, `./gen/t_gof_dma`, `./gen/t_gof_staging_leaks`, `./gen/t_phase1_integration`; the same binaries from `gen-rm`. `bin/slice bench --check`.
- delphi-3bda (real AMX): isolated worktree on local disk under `/var/tmp/jhan` (NFS attr-cache trap: never edit on claude-box and build on 3bda in the same minute without checking the file content on 3bda first). Run `exec/lib-guard.sh` checks and `exec/bill-share.sh status` first; pin to socket 1 (`taskset -c 72-143,216-287`); run fake tests with `SYSTEM_CONFIG="--instance 1,2"`; never run a real-driver tron binary without `--instance`. Build with TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON plus BUILD_INGEST_MODELS=ON (for the 1.2 check and runtron), then run `t_amx_numerics` (the VNNI identity case must run, no WARN), `t_amx_dispatch_dtype`, `t_k_vnni_layout`, `t_llama_unit`; repeat the K cases with `TRON_AMX_DISABLE=1`.
- Commits: (1) `git commit` of the merge: `Merge branch 'jhan-kv-typed-tensors' into jhan-amx-vnniK-typed` (body lists the 7 resolved files and the adapted main-drift tests). (2) `cmake: define TRON_K_VNNI for the generated model objects`. Every commit body ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

## Stage 2 - Typed K owner and views

Three commits. Each one compiles with TRON_K_VNNI ON and OFF.

### 2.1 Commit "VNNI K: typed owner and view for the K plane (h/tron/tensor/k_vnni.hpp)"

Scope: the header split, the two class templates, the typed plane operations, the owner inside `kv_block`, `page::k_packed`, the typed kernel boundary, the direct test users of the moved functions. `page::set_k_row` / `get_k_row` keep their raw row parameters in this commit (their bodies go typed), so the ~40 call sites stay untouched until 2.2.

#### 2.1.1 New `h/tron/tensor/k_vnni.hpp`

Move from CHILD `h/tron/kernels/k_vnni.hpp` verbatim: constants and the three static_asserts (CHILD 44-84, minus `MAX_KV_MUL_16`, which moves with qk_group), `layout_on` (86-97), `index` (99-107), `detail::pair_base` both overloads and `pair_row_offsets` (109-133), `transpose_16x16_epi32` (148-180); the bodies of `scatter_row` (140-145), `gather_row` (222-227) and `store_block` (198-215) become the bodies of `store_row`, `load_row`, `store_block` after one line that obtains the plane pointer. Keeping the bodies verbatim is what guarantees goal (d).

```cpp
#pragma once
// Typed access to the K plane of a 128-dimension head stored in the VNNI layout
// (TRON_K_VNNI): the owner k_vnni_tensor, the view k_vnni_view, the index map,
// and the vector operations that move token rows and 16-token blocks in and out
// (store_row, load_row, store_block, copy_token). Layout: Note [K VNNI storage]
// in h/tron/models/kv_cache.hpp. The AVX-512 score reader k_vnni::qk_group
// lives in h/tron/kernels/k_vnni.hpp.
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <immintrin.h>
#include <type_traits>

#include "common/assert.hpp"
#include "common/attributes.hpp"
#include "common/numerics/bf16.hpp"
#include "tron/simd/auto.hpp"  // defines TRON_CHUNK_SIZE; the 16-lane guard below needs it
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/view.hpp"

namespace tron {

namespace k_vnni {
// CHILD h/tron/kernels/k_vnni.hpp:44-84 verbatim, without MAX_KV_MUL_16.
// CHILD :86-97 verbatim (layout_on, under #ifdef TRON_K_VNNI).
// CHILD :99-107 verbatim (constexpr size_t index(size_t token, size_t dim) noexcept).
}  // namespace k_vnni

namespace detail {
// The one route from a packed K view to its plane address: the typed
// operations below, the AMX kernel qk_vnni_128x4 and the AVX-512 reader
// k_vnni::qk_group.
struct k_vnni_access;
}  // namespace detail

// Byte alignment of one K VNNI plane. Every pair row is one 64-byte line, and
// the AMX QK kernel reads the plane in 64-byte tile rows.
inline constexpr size_t K_PLANE_ALIGNMENT_64 = 64;
// One plane: 64 tokens x 128 dimensions of bf16.
inline constexpr size_t K_PLANE_BYTES_16384 =
    k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16);
static_assert(K_PLANE_BYTES_16384 == 16384, "the constant's name states its value");

template <typename T>
concept k_vnni_element = std::same_as<T, bf16> || std::same_as<T, const bf16>;

// A K plane in the VNNI layout, [Rows tokens * Cols dimensions]. One element is
// reached through at(token, dim). Whole token rows move through store_row,
// load_row, store_block and copy_token. Views come only from an owner
// (k_vnni_tensor::as_view). A writable view (bf16) converts to a read-only one
// (const bf16), never the reverse. There is no public pointer constructor, no
// data() accessor, no operator[] and no pointer conversion: a bare pointer does
// not say which layout it points at.
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view final {
  static_assert(k_vnni_element<T>, "a packed K plane holds bf16 or const bf16");
  // k_vnni::index is written for 4 token blocks of 16 and 4 dimension steps of
  // 32, so the packed K layout exists for one shape.
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "the K VNNI layout exists for 64-token pages of 128-dimension heads only");

  template <typename U>
    requires(std::is_const_v<T> && std::same_as<U, std::remove_const_t<T>>)
  TRON(inline)
  k_vnni_view(k_vnni_view<U, Rows, Cols> other) noexcept
  : data_(other.data_) {}

  TRON(nodiscard, inline, pure)
  T& at(size_t token, size_t dim) noexcept {
    TRON_ASSERT_LT(token, Rows);
    TRON_ASSERT_LT(dim, Cols);
    return data_[k_vnni::index(token, dim)];
  }

  TRON(nodiscard, inline, pure)
  const bf16& at(size_t token, size_t dim) const noexcept {
    TRON_ASSERT_LT(token, Rows);
    TRON_ASSERT_LT(dim, Cols);
    return data_[k_vnni::index(token, dim)];
  }

private:
  friend struct k_vnni_tensor<Rows, Cols>;
  friend struct detail::k_vnni_access;
  template <typename U, size_t R, size_t C>
  friend struct k_vnni_view;

  TRON(inline)
  explicit k_vnni_view(T* data) noexcept
  : data_(data) {}

  T* data_;
};

// Owns one K VNNI plane: exactly one 64-byte-aligned bf16 array, no separate
// allocation and no initialization (the cache's DMA allocation creates the
// kv_blocks that hold it; see Note [KV block lifetime] in kv_cache.hpp).
// Trivial to construct, copy and destroy; copying an owner copies the plane
// (copy_storage_slot's whole-page copy is `dst_block.k = src_block.k`).
// as_view() on a temporary is deleted: a view must not outlive its owner.
template <size_t Rows, size_t Cols>
struct alignas(K_PLANE_ALIGNMENT_64) k_vnni_tensor final {
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "the K VNNI layout exists for 64-token pages of 128-dimension heads only");

  TRON(nodiscard, inline)
  k_vnni_view<bf16, Rows, Cols> as_view() & noexcept TRON(this_lifetimebound)
  {
    return k_vnni_view<bf16, Rows, Cols>(data_);
  }

  TRON(nodiscard, inline)
  k_vnni_view<const bf16, Rows, Cols> as_view() const& noexcept TRON(this_lifetimebound)
  {
    return k_vnni_view<const bf16, Rows, Cols>(data_);
  }

  k_vnni_view<bf16, Rows, Cols> as_view() && = delete;
  k_vnni_view<const bf16, Rows, Cols> as_view() const&& = delete;

private:
  alignas(K_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols];
};
static_assert(sizeof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_BYTES_16384 &&
              alignof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_ALIGNMENT_64,
    "one packed K owner is the plane: 16384 bytes, aligned to 64 bytes");

namespace detail {
struct k_vnni_access final {
  // The plane's first element: panel (step 0, block 0), pair row 0, token 0.
  template <typename T, size_t Rows, size_t Cols>
  TRON(nodiscard, inline, pure)
  static T* plane(k_vnni_view<T, Rows, Cols> k) noexcept {
    return k.data_;
  }
};
}  // namespace detail

// Contiguous transfer rows for page::set_k_row / get_k_row, not packed storage.
// Unlike the V rows, the caller's alignment and DMA flags are kept: the K store
// and load use unaligned vector loads and stores (_mm512_loadu_si512,
// _mm512_storeu_si512). The flags are a statement about the caller's buffer.
template <size_t Cols, bool Aligned, bool Dma>
using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;
template <size_t Cols, bool Aligned, bool Dma>
using k_row_view = view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;

// These helpers neither check alignment nor copy data.
template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
TRON(nodiscard, inline)
const_k_row_view<Cols, Aligned, Dma> k_source_row(const bf16* row) noexcept {
  return const_k_row_view<Cols, Aligned, Dma>{row};
}
template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
TRON(nodiscard, inline)
k_row_view<Cols, Aligned, Dma> k_destination_row(bf16* row) noexcept {
  return k_row_view<Cols, Aligned, Dma>{row};
}

#if TRON_CHUNK_SIZE == 16

namespace k_vnni::detail {
// CHILD :112-123 (pair_base, both overloads), :125-132 (pair_row_offsets),
// :152-179 (transpose_16x16_epi32): verbatim.
}  // namespace k_vnni::detail

// Store one token's 128-dimension K row into the plane: 4 scatters of 16 dwords
// (one dimension pair each), one per dimension step. Only this token's 64 pair
// slots are written. (The CHILD's scatter_row.)
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void store_row(k_vnni_view<bf16, Rows, Cols> dst,
    size_t token,
    const_k_row_view<Cols, Aligned, Dma> src) noexcept {
  bf16* const plane = detail::k_vnni_access::plane(dst);
  const bf16* const row = src.data;
  // CHILD :140-145 verbatim (pair_row_offsets, loadu, i32scatter per step).
}

// Load one token's 128-dimension K row out of the plane: 4 gathers of 16
// dwords, the inverse of store_row. (The CHILD's gather_row.)
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void load_row(k_vnni_view<const bf16, Rows, Cols> src,
    size_t token,
    k_row_view<Cols, Aligned, Dma> dst) noexcept {
  const bf16* const plane = detail::k_vnni_access::plane(src);
  bf16* const row = dst.data;
  // CHILD :222-227 verbatim (pair_row_offsets, i32gather, storeu per step).
}

// Store the K rows of up to 16 tokens of token block c with whole-line stores
// (CHILD comment :182-192 and body :198-215 verbatim). rows[t] points at the
// 128 bf16 of token c * 16 + t, or is null when bit t of `present` is clear.
// The row pointers are plain native source rows; they do not expose packed storage.
template <size_t Rows, size_t Cols>
TRON(inline)
void store_block(k_vnni_view<bf16, Rows, Cols> dst,
    size_t c,
    __mmask16 present,
    const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
  bf16* const plane = detail::k_vnni_access::plane(dst);
  // CHILD :198-215 verbatim.
}

// Copy one token between packed K planes (or inside one plane): gather its row
// into a 64-byte-aligned local row (4 gathers), then scatter it (4 scatters).
// The same instructions as the CHILD's copy loop (kv_cache.hpp:2353-2360 at the
// merge). Consumer: copy_storage_slot for ranges smaller than a page.
template <size_t Rows, size_t Cols>
TRON(inline)
void copy_token(k_vnni_view<bf16, Rows, Cols> dst,
    size_t dst_token,
    k_vnni_view<const bf16, Rows, Cols> src,
    size_t src_token) noexcept {
  alignas(K_PLANE_ALIGNMENT_64) bf16 row[Cols];
  load_row(src, src_token, k_destination_row<Cols>(row));
  store_row(dst, dst_token, k_source_row<Cols>(row));
}

#endif  // TRON_CHUNK_SIZE == 16

}  // namespace tron
```

#### 2.1.2 `h/tron/kernels/k_vnni.hpp` keeps only `qk_group`

```cpp
#pragma once
// AVX-512 QK reader of the K VNNI layout (h/tron/tensor/k_vnni.hpp) for
// partial pages, hosts without AMX and the kill switch TRON_AMX_DISABLE=1.
// No AMX instruction here, so any translation unit may include it.
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <type_traits>

#include "common/attributes.hpp"
#include "common/numerics/bf16.hpp"
#include "common/numerics/fp16.hpp"
#include "tron/tensor/k_vnni.hpp"

namespace tron::k_vnni {

// One accumulator register per query head of the group.
inline constexpr size_t MAX_KV_MUL_16 = 16;

#if TRON_CHUNK_SIZE == 16
// CHILD :230-245 comment, with "plane" replaced by "k_page, the page's packed K plane as its typed view".
template <size_t kv_mul, typename q_scalar>
TRON(inline)
void qk_group(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const q_scalar* q,
    uint64_t live,
    float* s,
    size_t s_stride) noexcept {
  static_assert(kv_mul >= 1 && kv_mul <= MAX_KV_MUL_16, "one accumulator register per head");
  if constexpr (std::is_same_v<q_scalar, fp16>) {
    alignas(64) float qf[kv_mul * HEAD_SIZE_128];
    for (size_t i = 0; i < kv_mul * HEAD_SIZE_128; ++i) {
      qf[i] = float(q[i]);
    }
    qk_group<kv_mul, float>(k_page, qf, live, s, s_stride);
    return;
  } else {
    // Inside tron::k_vnni the name `detail` is tron::k_vnni::detail, so qualify.
    const bf16* const plane = tron::detail::k_vnni_access::plane(k_page);
    // CHILD :263-306 verbatim (the body already reads through `plane`).
  }
}
#endif  // TRON_CHUNK_SIZE == 16

}  // namespace tron::k_vnni
```

#### 2.1.3 `h/tron/tensor/kv_cache_fwd.hpp`: forward declarations

Add after the V declarations (lines 27-36 at PARENT). No `k_vnni_row` (the PARENT dropped `v_vnni_row` in c12df586b6; design Q3 rejected).

```cpp
// Packed K types (TRON_K_VNNI, Note [K VNNI storage] in kv_cache.hpp):
// - k_vnni_tensor holds one bf16 array of [Rows tokens * Cols dimensions] in
//   the K VNNI layout of h/tron/tensor/k_vnni.hpp, at an address that is a
//   multiple of 64 bytes.
// - k_vnni_view refers to that array and computes where each (token, dim) is.
// T = bf16 allows writes, and T = const bf16 is read-only.
template <size_t Rows, size_t Cols>
struct k_vnni_tensor;
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view;
```

#### 2.1.4 `h/tron/models/kv_cache.hpp`

- Line 27: `#include "tron/kernels/k_vnni.hpp"` becomes `#include "tron/tensor/k_vnni.hpp"`. Keep the `#error` block (36-41). `<type_traits>` is already in use.
- `kv_block` (2635-2683). Replace line 2638 and constrain `k_view()` / `k_at()` (2658-2681):

```cpp
  // Native K: one row of head_size bf16 values per token, indexed as
  // [p * head_size + i]. Packed K (TRON_K_VNNI, 128-dimension heads): the typed
  // owner of Note [K VNNI storage]. Both hold page_size * head_size bf16 values.
  using native_k_storage = bf16[page_size * head_size];
  using k_storage = std::conditional_t<k_vnni::layout_on<head_size>,
      k_vnni_tensor<page_size, head_size>,
      native_k_storage>;
  static_assert(std::is_trivially_default_constructible_v<k_storage> &&
                    std::is_trivially_copyable_v<k_storage> &&
                    std::is_trivially_destructible_v<k_storage>,
      "the DMA allocation creates kv_blocks; see Note [KV block lifetime]");
  static_assert(sizeof(k_storage) == page_size * head_size * sizeof(bf16),
      "packed K holds the same bytes as native K");
  alignas(kv_block_alignment) k_storage k;
  // ... v unchanged (2639-2654) ...
  static_assert(sizeof(k) == sizeof(v));  // 2656, unchanged

  TRON(nodiscard, inline, pure)
  auto k_view() noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>)
  { return view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k}; }
  // k_view() const, k_at(), k_at() const: the same trailing requires-clause; bodies unchanged.
```

  `kv_block_alignment` is `std::max<size_t>(64, chunk_alignment)` (2630), so `alignas(kv_block_alignment)` on the 64-byte-aligned owner is valid, as it already is for `v_storage`. The book-level asserts (1616-1623, 1656-1666: `sizeof(kv_block_t) == expected_block_bytes`, `alignof == storage_alignment`, trivial traits) keep holding and now cover the K owner.

- `fill_storage_slot` (1713-1728). The range-for at 1718-1719 does not compile over an owner. Replace it with:

```cpp
        if constexpr (k_vnni::layout_on<geometry.head_size>) {
          bf16* k = detail::k_vnni_access::plane(block.k.as_view());
          for (size_t i = 0; i < page_size * geometry.head_size; ++i) {
            k[i] = static_cast<bf16>(distribution(gen));
          }
        } else {
          for (auto& value : block.k) {
            value = static_cast<bf16>(distribution(gen));
          }
        }
```
  Extend the `fill_random` comment (1287-1289) so the "one documented exception to the typed packed access rule" names K as well as V.

- Delete `page::k_vnni_plane` (1981-1992). Add next to `v_packed` (after 2126):

```cpp
  // This page's packed K plane for one KV head of one slot, read-only: the
  // argument type of qk_vnni_128x4 and k_vnni::qk_group (Note [K VNNI storage]).
  // Internal cache writes take writable views from the block owner instead.
  // The view's shape is the page's shape; the kernels accept 64 x 128 only, so
  // a head size that gains layout_on later fails to compile at the call.
  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(
      kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
  {
    return kv_block<geometry>(slot, kv_head).k.as_view();
  }
```

- `set_k_row` (1994-2010), `set_k_block` (2019-2031), `get_k_row` (2035-2048): parameters unchanged in this commit; bodies become typed:

```cpp
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page,
          k_source_row<geometry.head_size>(row));
    } else { /* memcpy through k_at(i_page).data, unchanged */ }
    // set_k_block:
    store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, present, rows);
    // get_k_row (const member, so .k.as_view() is the read-only view):
      load_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page,
          k_destination_row<geometry.head_size>(row));
```

- `copy_storage_slot` packed branch (2345-2361):

```cpp
        auto const& src_block =
            src_page->template kv_block_at_storage<geometry>(storage_offset, kv_head);
        auto& dst_block = kv_block_at_storage<geometry>(storage_offset, kv_head);
        if (src_begin == 0 && dst_begin == 0 && count == page_size) {
          // Defaulted owner assignment copies the whole 16 KiB plane.
          dst_block.k = src_block.k;
        } else {
          for (size_t i = 0; i < count; ++i) {
            copy_token(dst_block.k.as_view(), dst_begin + i, src_block.k.as_view(),
                src_begin + i);
          }
        }
```
  `src_block` is `const&` (const `src_page`), so its `as_view()` is the read-only view that `copy_token`'s `src` deduces. Native branch (2362-2371) unchanged. Comment: "a whole-page copy assigns the owner; every other range moves token by token with copy_token".

- Note [K VNNI storage] (657-712): first paragraph names `h/tron/tensor/k_vnni.hpp` (was `tron/kernels/k_vnni.hpp`); item 1 names `store_block` and `store_row` (was `k_vnni::store_block`, `k_vnni::scatter_row`); item 2: "passes page::k_packed (a k_vnni_view<const bf16, 64, 128>) to qk_vnni_128x4"; item 3: qk_group takes the same view; item 5: "a whole-page copy assigns the owner (dst_block.k = src_block.k). Every other range moves token by token (copy_token in h/tron/tensor/k_vnni.hpp)."; item 6 adds: "The K plane is reached only through the owner k_vnni_tensor and its views. No raw plane pointer leaves the cache. detail::k_vnni_access is the one route, for the typed operations and the two score kernels." Keep the Note title (`make lint-notes` checks references).
- Note [KV block lifetime] last paragraph (1526-1528): "K and V are separate members: a bf16 array or a trivially copyable owner (k_vnni_tensor for packed K, v_vnni_tensor for packed V). Fill each member separately. SIMD load addresses inside a packed plane come from the plane's access helper (detail::k_vnni_access, detail::v_vnni_access)."
- Overview comment (581-582): add "and packed-K storage (h/tron/tensor/k_vnni.hpp, Note [K VNNI storage])".

#### 2.1.5 Kernel boundary

- `h/tron/kernels/amx_attn_iface.hpp` (254-257): `void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;`. The header already includes `tron/tensor/kv_cache_fwd.hpp` (113) and stays free of intrinsics. Comment (252-253): "k_page = the page's packed K plane (64 tokens x 128 dims, 16 KiB) as its typed view (layout: h/tron/tensor/k_vnni.hpp). A bare pointer, the native K view or a packed V view is a compile error. q_rows = the pack_q_rows_128x4 output." Also 229-231: "so that a packed K or V plane or a bare pointer cannot be handed in by mistake".
- `src/tron/kernels/amx_attn.cpp`: line 14 `#include "tron/kernels/k_vnni.hpp"` becomes `#include "tron/tensor/k_vnni.hpp"` (the TU uses only the constants and the access struct, never qk_group). Definition (228-231) takes the typed view; first statement of the body:

```cpp
  // One of the two layout-specific readers allowed to take the plane address
  // (the other is k_vnni::qk_group).
  const bf16* const k_vnni_plane = detail::k_vnni_access::plane(k_page);
```
  The local name `k_vnni_plane` keeps lines 268-277 (the tile loads) textually unchanged, so the loaded bytes, tile order and scores are unchanged (goal d). Comment at 224 ("Note [K VNNI storage] in kv_cache.hpp") stays.
- `h/tron/models/self_attention.hpp`: add `#include "tron/kernels/k_vnni.hpp"  // k_vnni::qk_group` to the include block (16-28). Without it, qk_group disappears once kv_cache.hpp stops including the kernel header, while `k_vnni::layout_on` (now in the tensor header) still resolves; the error is easy to misread. Replace the two calls: 1670-1672 `pg.template k_packed<geometry.kv>(slot, kv_head)`; 1869-1870 `page.template k_packed<geometry.kv>(slot, kv_head)`. `pg` is `const page&`, so `k_packed` returns `k_vnni_view<const bf16, 64, 128>` exactly (page_size 64 and head_size 128 are static_asserted at 1645-1646 and by `layout_on`). Comment 1655-1666: "In the VNNI layout the argument is this (slot, kv_head)'s packed K plane, a k_vnni_view<const bf16, 64, 128> from page::k_packed, read as the B operand of qk_vnni_128x4."
- `t/t_amx_dispatch_dtype.cpp`: add `#include "tron/tensor/k_vnni.hpp"` next to line 50 (a by-value class parameter in a definition needs the complete type; the fakes sit outside `#ifdef TRON_AMX_DISPATCH`, so the class must be complete in every build). Fake (205-208):

```cpp
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}
```
  The fake signatures and the declarations must change in the same commit; otherwise the linker pulls libtron's amx_attn.cpp into the test and defeats its purpose (file header lines 1-8).

#### 2.1.6 Tests that call the moved functions directly

- `t/t_amx_numerics.cpp`: line 28 include becomes `tron/tensor/k_vnni.hpp` (the TU never calls qk_group). Lines 217-227 and 237-238:

```cpp
  auto in = std::make_unique<qk_inputs>();
  auto k_owner = std::make_unique<tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();
  ...
      tron::store_row(k_owner->as_view(), tok,
          tron::k_source_row<HEAD_SIZE_128>(in->k + tok * HEAD_SIZE_128));
  ...
    tron::amx_attn_h128g4::qk_vnni_128x4(
        k_owner->as_view(), q_rows, &s_vnni[0][0], PAGE_TOKENS_64);
```
  (`qk_vnni_128x4` is not a template, so the writable view converts to the read-only parameter.) Comment at 202: "the K store (store_row)". This case is the bit-identity proof of goal (d); it must keep passing on 3bda.
- `t/t_k_vnni_layout.cpp`: includes (24-26): add `#include "tron/tensor/k_vnni.hpp"`; keep `tron/kernels/k_vnni.hpp` (qk_group at 306-309). Fixture (67-70): `tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128> plane;` with `rows` unchanged; add `static_assert(sizeof(tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>) == PAGE_TOKENS_64 * HEAD_SIZE_128 * sizeof(tron::bf16))` (it guards the memcmp below). Mapping: `scatter_row(buf->plane, tok, src)` at 113, 139-140, 199, 214, 226, 291 -> `tron::store_row(buf->plane.as_view(), tok, tron::k_source_row<HEAD_SIZE_128>(src))`; `gather_row(buf->plane, tok, row)` at 129, 232 -> `tron::load_row(std::as_const(buf->plane).as_view(), tok, tron::k_destination_row<HEAD_SIZE_128>(row))` (`load_row` is a template: a writable view does not deduce the `const bf16` parameter, so `as_const` is required); `store_block(blk->plane, c, __mmask16(m), rows)` at 201, 228 -> `tron::store_block(blk->plane.as_view(), c, __mmask16(m), rows)`; element reads `buf->plane[index(tok, d)]` at 120-122, 143 -> copy the owner's bytes first (`alignas(64) std::array<tron::bf16, PAGE_TOKENS_64 * HEAD_SIZE_128> bytes; std::memcpy(bytes.data(), &buf->plane, sizeof(buf->plane));`) and index `bytes[tron::k_vnni::index(tok, d)]` (design: "Copy the trivially copyable owner's bytes to a test buffer"); poison fills at 107-109, 190-192, 286-288 -> one poison row `alignas(64) tron::bf16 poison_row[HEAD_SIZE_128]` and 64 `store_row` calls (design: "Fill poison with 64 typed row saves"); `std::memcpy(blk->plane, ref->plane, sizeof)` at 193, 216 -> `blk->plane = ref->plane;`; `std::memcmp(blk->plane, ref->plane, sizeof(ref->plane))` at 202, 229 -> `std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane))`; `qk_group<KV_MUL_4>(buf->plane, ...)` at 306-309 -> `std::as_const(buf->plane).as_view()`. The index anchors (81-90) and `using tron::k_vnni::index` stay verbatim. Do not call `detail::k_vnni_access`, `pair_base` or `pair_row_offsets` from the test. The `#if TRON_CHUNK_SIZE == 16` (31, 466) and `#ifdef TRON_K_VNNI` (388-392) guards stay. The book-level cases (401-459) keep their raw `row.data()` arguments in this commit.

### 2.2 Commit "VNNI K: typed row views for page::set_k_row and page::get_k_row"

- `h/tron/models/kv_cache.hpp` (1994-2010, 2035-2048, 2051-2065):

```cpp
  template <kv_geometry geometry, bool Aligned, bool Dma>
    requires(book_t::template declares_geometry<geometry>())
  TRON(inline)
  void set_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
      const_k_row_view<geometry.head_size, Aligned, Dma> row) noexcept {
    TRON_ASSERT_LT(i_page, page_size);
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
    } else {
      std::memcpy(kv_block<geometry>(slot, kv_head).k_at(i_page).data, row.data,
          geometry.head_size * sizeof(bf16));
    }
  }

  template <kv_geometry geometry, bool Aligned, bool Dma>
    requires(book_t::template declares_geometry<geometry>())
  TRON(inline)
  void get_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
      k_row_view<geometry.head_size, Aligned, Dma> row) const noexcept {
    TRON_ASSERT_LT(i_page, page_size);
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      load_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
    } else {
      std::memcpy(row.data, kv_block<geometry>(slot, kv_head).k_at(i_page).data,
          geometry.head_size * sizeof(bf16));
    }
  }

  // Uniform-geometry forms.
  template <bool Aligned, bool Dma>
  TRON(inline)
  void set_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
      const_k_row_view<head_size, Aligned, Dma> row) noexcept
    requires(layout_t::uniform_geometry)
  { set_k_row<layout_t::primary_geometry>(slot, kv_head, i_page, row); }
  // get_k_row likewise with k_row_view<head_size, Aligned, Dma>.
```
  Aligned and Dma are deduced through the alias (alias templates are transparent for deduction). Template deduction does not apply the pointer-to-view conversion, so every caller wraps its pointer (design: "Construct read-only source views explicitly").
- `h/tron/models/model.hpp`, `store_k_block` (2878-2941): add `using k_buffer_t = std::remove_cvref_t<decltype(ks[token_job_id(0)])>;` in the VNNI branch next to `rows_are_bf16` (mirrors `v_buffer_t`, 3122). Line 2936: `pg.template set_k_row<geometry.kv>(slot, kv_head, j, k_source_row<geometry.kv.head_size, VIEW_ALIGNED_TRUE, k_buffer_t::dma>(kout.data));`. Line 2940: `pg.template set_k_row<geometry.kv>(slot, kv_head, j, k_source_row<geometry.kv.head_size>(conv[0]));` (`conv` is `alignas(64)`, 2899). `VIEW_ALIGNED_TRUE` for `kout.data` holds because `kout` is a `slice` at offset `kv_head * 128 * 2` bytes (a multiple of 256) of a 64-byte-aligned executor buffer, the same buffer family the PARENT states aligned for V. The block path (2946-2957, `const bf16* rows[K_STORE_BLOCK_16]` + `set_k_block`) stays raw by design.
- `h/tron/scheduler/full.hpp` (2758): `pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off, k_destination_row<hw_kv.head_size>(dest));`. `dest` comes from gof.cpp's `alignas(64) std::array<bf16, HW_MAX_KV_HEADS * HW_BAKED_HEAD_SIZE> k_scratch` at 256 bytes per head, so aligned is a true statement. The else branch (`return pg_ptr->template k<hw_kv>(slot, kv_head, off).data;`) stays: page_info is the bf16* hardware boundary the PARENT kept.
- `t/t_llama_unit.cpp`: probe (141-152) becomes one typed `output` for both calls:

```cpp
template <typename Page>
constexpr bool page_supports_uniform_kv_access = requires(Page& page,
    view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
        seq<Page::layout_t::primary_geometry.head_size>, sseq<1>> output) {
  page.get_k_row(kv_slot_id(0), 0, 0, output);  // both K layouts (Note [K VNNI storage])
  page.get_v(kv_slot_id(0), 0, 0, output);
};
```
  Wrap every raw call: `set_k_row(..., X.data())` at 465, 466, 495, 502, 682, 704, 708, 769-770, 1179, 1820, 1940, 2926-2929, 2963-2965, 3097-3098, 3131-3132 -> `k_source_row<HEAD_SIZE_128>(X.data())` (or `<geometry.head_size>` / `<geometry_128.head_size>` where the geometry form is used); `get_k_row(..., X.data())` at 467, 469, 505, 510, 710, 778, 1203-1204, 1841-1842, 1963, 2432, 3011-3014, 3416 -> `k_destination_row<...>(X.data())`. All these arrays are `alignas(64) std::array<bf16, 128>`, so the default aligned flag is true. Add `#include "tron/tensor/k_vnni.hpp"` to the include block (58-77).
- `t/t_k_vnni_layout.cpp` 401, 424, 428, 453 (`set_k_row`) and 405, 434, 441, 459 (`get_k_row`): same wraps.
- `t/t_amx_dispatch_dtype.cpp` 105: `page->set_k_row(slot, 0, token, k_source_row<head_size>(zero.data()));`.

### 2.3 Commit "VNNI K: compile-time contracts for the typed K plane"

`t/t_llama_unit.cpp`, beside the PARENT's probes (merged ~95-166) and inside the case "attention operations resolve to typed KV slots" (merged ~392-445):

```cpp
template <typename K>
constexpr bool amx_qk_vnni_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0});
};
template <typename Page, kv_geometry geometry>
constexpr bool page_k_packed_accepts_geometry =
    requires(Page const& page) { page.template k_packed<geometry>(kv_slot_id(0), 0); };

// in the case:
using k_vnni_plane_t = k_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
using k_vnni_plane_mut_t = k_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
using k_vnni_owner_t = k_vnni_tensor<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_t>);
STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_mut_t>);  // writable converts to read-only
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);  // the native K view
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<v_plane_t>);
STATIC_REQUIRE_FALSE(amx_qk_accepts<k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(amx_pv_accepts<k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(std::is_constructible_v<k_vnni_plane_mut_t, bf16*>);
STATIC_REQUIRE_FALSE(std::is_constructible_v<k_vnni_plane_t, const bf16*>);
STATIC_REQUIRE_FALSE(std::is_default_constructible_v<k_vnni_plane_t>);
STATIC_REQUIRE(std::is_convertible_v<k_vnni_plane_mut_t, k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(std::is_convertible_v<k_vnni_plane_t, k_vnni_plane_mut_t>);
STATIC_REQUIRE_FALSE(owner_views_temporary<k_vnni_owner_t>);
STATIC_REQUIRE(matrix_at_writes<k_vnni_plane_mut_t>);
STATIC_REQUIRE_FALSE(matrix_at_writes<k_vnni_plane_mut_t const>);
STATIC_REQUIRE_FALSE(matrix_at_writes<k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_plane_mut_t>);
STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_plane_t>);
STATIC_REQUIRE(std::is_trivially_default_constructible_v<k_vnni_owner_t>);
STATIC_REQUIRE(std::is_trivially_destructible_v<k_vnni_owner_t>);
STATIC_REQUIRE(std::is_trivially_copyable_v<k_vnni_owner_t>);
STATIC_REQUIRE(sizeof(k_vnni_owner_t) == K_PLANE_BYTES_16384);
STATIC_REQUIRE(alignof(k_vnni_owner_t) == K_PLANE_ALIGNMENT_64);
#ifdef TRON_K_VNNI
STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k), k_vnni_owner_t>);
STATIC_REQUIRE((page_k_packed_accepts_geometry<page_t, geometry_128>));
#else
STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k), bf16[amx_attn_h128g4::PAGE_TOKENS_64 * amx_attn_h128g4::HEAD_SIZE_128]>);
STATIC_REQUIRE_FALSE((page_k_packed_accepts_geometry<page_t, geometry_128>));
#endif
STATIC_REQUIRE_FALSE((page_k_packed_accepts_geometry<page_t, geometry_64>));
// existing, still true: STATIC_REQUIRE(sizeof(kv_block_t) == detail::KV_BLOCK_PLANES_2 * sizeof(v_owner_t));
```
These compile in both builds because the K classes are defined unconditionally and `qk_vnni_128x4` is declared unconditionally. Reword the comments at 1073-1074 and 1159-1161 ("set_k_row / get_k_row serve the slot") to add "and k_packed exposes the plane as a read-only typed view".

### 2.4 COULD (default: skip): unify the tile names in `qk_vnni_128x4`

Replace the local `Q_TILE_4`, `K_TILE_5`, `K_TILE_6`, `S_TILE_0..3` (amx_attn.cpp:259-265) with file-scope `Q_ROWS_TILE_4`, `K_EVEN_PANEL_TILE_5`, `K_ODD_PANEL_TILE_6` and the existing `ACCUMULATOR_TILE_0..3`; change "Both kernels" to "All three kernels" (41-42). Same registers, same instruction order. If done, it needs the t_amx_numerics identity case on 3bda as its check.

### 2.5 Build and test gate (Stage 2)

- After each commit: the Stage 1 claude-box gate (gen ON and gen-rm OFF; all tests listed there). `bin/slice bench --check`.
- delphi-3bda, after 2.3: the Stage 1 3bda gate, plus `TRON_AMX_DISABLE=1` runs of `t_k_vnni_layout`, `t_llama_unit`, `t_amx_dispatch_dtype`. Keep `logs-<host>/run-NNNN/t_amx_numerics.log` showing the VNNI identity case ran without "AMX unavailable on this host", and a separate TRON_AMX_DISABLE=1 log showing the warning (design acceptance rule).
- Goal (d) evidence, bit-identity against the CHILD: (1) `t_k_vnni_layout` (index anchors, store/load/block exactness, owner-byte comparisons) passes; (2) the `t_amx_numerics` identity case passes with real AMX; (3) one A/A runtron pair on 3bda, same model with 128-dim heads (llama-8b), CHILD binary at 30c4ac82cb vs the port binary, both TRON_K_VNNI=ON, `--pay-for-determinism --temperature 0`, `USE_HW_ATTN=0`, one prompt, identical `--app-cores/--dev-cores/--devices` and `--instance 1,2`: `--output-token-file` rows and the "Top-k Logits" log lines must be identical. The kernels and the vector bodies are the same instructions, so any difference is a port defect. (4) Optional, PARENT precedent: objdump of `noinline` wrappers of `store_row` / `load_row` / `store_block` / `copy_token` vs the CHILD's `scatter_row` / `gather_row` / `store_block` / copy loop, to cite in the PR body.

---

## Stage 3 - Cost rows, CI, docs, PR hygiene

- `config/test-benchmarks.json`: keep the Stage 1 resolution. The kept `t_llama_unit` row (5.187 s, 331 MB) measures main's binary without the CHILD's cases; the CHILD measured 13.4 s / 643 MB for its own version, so the merged binary is understated by about 2.6x (est., ratio of the two recorded measurements). `bench --check` does not fail on wrong times (bin/slice checks duplicates and coverage), so this is a packing-balance issue, not a correctness issue. Refresh = `bin/slice route` first, then `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` on the whole 3bda (it launches tests under every `--instance i,n`, both sockets, so it needs the Bill marker taken by jhan; question Q3). Until then the PR body records: rows deferred; CHILD's historical values 13.436/13.388/13.618 s and 0.804/0.745/0.728 s; genoa96, genoa32, granite_rapids_6960p unrefreshed.
- CI and docs: no change needed. Verify `grep -n TRON_K_VNNI .github/workflows/cmake-single-platform.yml README.ci.md` shows 356 and 550/573/583. Read `.github/AGENTS.md` and `README.ci.md` before any further edit there.
- Lint: inside the nix shell `make lint-notes` (Note references: the K Note title is unchanged) and `clang-format --dry-run --Werror` on every touched C++ file (clang-format 19.1.7 is in the shell).
- Tag the old CHILD head locally: `git -C <worktree> tag jhan-amx-vnniK-pre-typed 30c4ac82cb` (design: preserve the old head before changing history; here history is not rewritten, so the tag is a convenience).
- PR body (present tense, head description only, measurements with commit id and date): the four review points of #4424 now covered for K (encapsulated plane -> k_packed and the typed kernels; owner type -> k_vnni_tensor; row-wise load/store -> store_row/load_row/store_block/copy_token; no bare bf16* -> STATIC_REQUIRE contracts); the `expr` point stays dropped; the CMake define for the model objects; the test-benchmarks deferral; the note that PR #4737 (row-major tail block) needs a re-port of its raw-pointer helpers (`k_vnni_plane`, `row_ptr`, `block_to_vnni`, `block_to_rows`, `k_storage_ref`) onto the typed views before it can merge on top.
- Push per Q1. Keep the PR draft; keep "Skip benchmarks"; add no "Run CI" label without the user's direction. After #4557 merges: verify the base is main, merge updated main (the memory rule for approved PRs: merge main, do not rebase), re-run the gates.
- When the PARENT head moves: `git merge origin/jhan-kv-typed-tensors` into `jhan-amx-vnniK-typed`, resolve, re-run the Stage 2 gate.

Commit subjects (Stage 3): `bench: carry the t_k_vnni_layout cost row; t_llama_unit refresh deferred` (only if the JSON changes again), otherwise no code commit.

---

## Stage 4 (deferred; only on a yes to Q2) - Worker-index merge

- `h/tron/models/model.hpp`: merge `save_k(batch*, kv_buffer_t&, size_t n_workers = 1)` (3081) and the descriptor form (3089) with `save_k_helper` (2969-2990) into `save_k(..., size_t worker_ix = 0, size_t n_workers = 1)` for both pairs; `TRON_ASSERT(n_workers >= 1)`, `TRON_ASSERT_LT(worker_ix, n_workers)`; worker 0 keeps window setup, claims, join, completion marks, GOF credits, countdowns; the `layout_on` and `k_store_shared(q_batch, n_workers)` checks come first; both trailing parameters stay defaulted because main's tests call `save_k<geometry>(consumer, operation, kouts)` with three arguments (worktree t_llama_unit.cpp:3459 and two more).
- `ingest/src/TronCpp.hs` (read `ingest/AGENTS.md` first): run() passes `0, n_workers`; run_main_help calls `save_k` with `worker_ix, n_workers`. `ingest/test/LoopyTronSpec.hs`: both `save_k<` counts become 2; the two `save_k_helper<` counts go; main tails `,k,0,n_workers);`; helper tails unchanged.
- `t/t_llama_unit.cpp` 3471-3472 -> `save_k<geometry>(&q_batch, operation, kouts, worker_ix, N_WORKERS_3)`; the main call below -> `save_k<geometry>(&q_batch, operation, kouts, 0, N_WORKERS_3)`; `h/tron/plugins/llama.hpp:1024` stays valid through the defaults (verify).
- Gate: nix develop: `make format-haskell`, `bin/ingest-cabal build`, `bin/ingest-cabal test`; `nix build .#checks.x86_64-linux."tron-ingest:test:ingest-tests"`; then the Stage 2 gate.
- Commit subject: `VNNI K: one save_k entry point with a worker index`.

---

## Risks carried into implementation

- PR #4737 (origin/jhan-amx-vnniK-i4500) depends on `k_vnni_plane` and adds raw-pointer helpers in `h/tron/kernels/k_vnni.hpp` (+105 lines) and `kv_cache.hpp` (+539 lines). After this port its merge is a re-port onto the typed views, not a mechanical merge. Keeping the constants block verbatim in the tensor header keeps its constants hunk re-applicable.
- `load_row` and `copy_token` overload the V functions on the view's class template. A mistyped argument yields "no matching function" naming both families; that is the intended compile error.
- A raw-pointer caller of `set_k_row`/`get_k_row` missed in 2.2 is a compile error, not a silent change; the native branch is instantiated only with TRON_K_VNNI=OFF (or for non-128 heads), so both builds must be compiled.
- The PARENT is not final (CHANGES_REQUESTED, CONFLICTING with main: 13 hunks in 6 files). Names in this plan follow c12df586b6; a rename there ripples into the K mirror.
- `std::memcmp(&owner_a, &owner_b, sizeof)` in t_k_vnni_layout is valid only while the owner is a single 16384-byte array with no padding; the static_assert on `sizeof` guards it.
- No CI lane that builds at `TRON_CHUNK_SIZE == 8` was identified (Insufficient data; a `-DAVX512=OFF -DTRON_AMX_DISPATCH=OFF` configure and build of `tron` and `t_amx_dispatch_dtype` would resolve it). The class definitions stay complete at 8 lanes by construction; the design accepts "packed K at 8 lanes: not applicable".

## Gate summary

| Stage | claude-box (AMD, nix shell) | delphi-3bda (AMX, our half, guard first) |
|---|---|---|
| 1 | `ninja -C gen` (ON) and `ninja -C gen-rm` (OFF); run t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype, t_amx_numerics (WARN expected), t_heterogeneous_scheduler, t_gof_dma, t_gof_staging_leaks, t_phase1_integration with `env -u SYSTEM_CONFIG`; `bin/slice bench --check` | isolated worktree under /var/tmp/jhan, BUILD_INGEST_MODELS=ON; the 1.2 `-DTRON_K_VNNI` check on a model object; the four K tests with and without TRON_AMX_DISABLE=1 |
| 2 | same, after each of 2.1, 2.2, 2.3 | same plus the identity logs and the A/A runtron token comparison vs the CHILD binary |
| 3 | `make lint-notes`, clang-format dry run | `bin/slice bench --update` only with authorization (Q3) |

Commit subjects in order: `Merge branch 'jhan-kv-typed-tensors' into jhan-amx-vnniK-typed`; `cmake: define TRON_K_VNNI for the generated model objects`; `VNNI K: typed owner and view for the K plane (h/tron/tensor/k_vnni.hpp)`; `VNNI K: typed row views for page::set_k_row and page::get_k_row`; `VNNI K: compile-time contracts for the typed K plane`; optional `VNNI K: one save_k entry point with a worker index`.