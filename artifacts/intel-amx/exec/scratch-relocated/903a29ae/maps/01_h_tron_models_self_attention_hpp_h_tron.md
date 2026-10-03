# h/tron/models/self_attention.hpp, h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp (plus the kernel fakes in t/t_amx_dispatch_dtype.cpp that these signatures force)

## textual_conflicts
- src/tron/kernels/amx_attn.cpp 14-20 (includes): Take the PARENT side (kv_cache_fwd.hpp, v_vnni.hpp, view.hpp) and add `#include "tron/tensor/k_vnni.hpp"` (the new K TENSOR header) in alphabetical order before kv_cache_fwd.hpp. Drop the CHILD's `#include "tron/kernels/k_vnni.hpp"`: the AMX TU needs only the layout constants (BLOCK_TOKENS_16, PANEL_ELEMS_512, TOKEN_BLOCKS_4, STEP_PAIRS_16, STEP_DIMS_32, PAGE_TOKENS_64, HEAD_SIZE_128) and detail::k_vnni_access, which the design moves to the tensor header; qk_group (the only thing left in the kernel header) is not used here. Design: 'Include the full K tensor header in src/tron/kernels/amx_attn.cpp' (design-child-section, header-split paragraph).
- src/tron/kernels/amx_attn.cpp 219-298 (pack_q_rows_128x4 / qk_vnni_128x4 / weights_times_v_128x4 head): Keep BOTH sides: the CHILD's pack_q_rows_128x4 and qk_vnni_128x4 bodies (HEAD) followed by the PARENT's typed weights_times_v_128x4 signature (`v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page`). The conflict exists only because the PARENT retyped the line the CHILD inserted before. Then retype qk_vnni_128x4 (see semantic changes M2) and move its tile names to file scope (S1).
- h/tron/models/self_attention.hpp 1653-1666 (comment above s_pages in apply_dense_amx_page): Merge the two comments: keep the CHILD's two-layout sentences and replace its last two sentences with the typed wording: 'In the VNNI layout the argument is this (slot, kv_head)'s packed K plane, a k_vnni_view<const bf16, 64, 128> from page::k_packed, read as the B operand of qk_vnni_128x4. In the row-major layout the argument is the whole native K plane, a const_native_k_view of 64 consecutive 128-dim rows (page::k), read as the A operand of qk_rowmajor_128x4. The view types state the layout at the call.' The PARENT's sentence 'This is the only place where the AMX path depends on K being stored as consecutive rows' stays, qualified with 'in the row-major layout'.
- h/tron/models/self_attention.hpp 1674-1687 (the QK kernel call): Keep the CHILD's `if constexpr (k_vnni::layout_on<operation_head_size>)` shape. VNNI branch: `amx_attn_h128g4::qk_vnni_128x4(pg.template k_packed<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size);`. Else branch: take the PARENT's whole-plane call `amx_attn_h128g4::qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size);` and delete the CHILD's `const auto k0 = ...; k0.data` (the PARENT removed k0 at self_attention.hpp:1653-1655 of 996f58ec82; keeping it would pass a bare bf16* and fail to compile against const_native_k_view).
- t/t_amx_dispatch_dtype.cpp 105-112 (fixture fill) and 204-222 (kernel fakes): Lines 105-112: keep the CHILD's layout-agnostic `page->set_k_row(...)` (the PARENT's `page->k(slot,0,token).data` is a row view that does not exist for VNNI slots), but pass the source as the typed row view the design prescribes for set_k_row (const_view<bf16, Aligned, Dma, seq<D>, sseq<1>>), and keep the PARENT's `v_source_row<head_size>(zero.data())` for set_v. Lines 204-222: keep the CHILD's pack_q_rows_128x4 fake and qk_vnni_128x4 fake, retype the latter's first parameter to `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>`, and take the PARENT's typed weights_times_v_128x4 fake. Add `#include "tron/tensor/k_vnni.hpp"` next to the existing `tron/tensor/v_vnni.hpp` include (line 50): a by-value parameter in a definition needs the complete type.

## semantic_changes
- [MUST] h/tron/kernels/amx_attn_iface.hpp @ line 254-257 in the worktree (declaration of qk_vnni_128x4)
  CHANGE: Change `void qk_vnni_128x4(const bf16* k_vnni_plane, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;` to `void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;`. The header stays intrinsics-free because kv_cache_fwd.hpp (already included at line 113) gains the unconstrained forward declarations `template <size_t Rows, size_t Cols> struct k_vnni_tensor; template <typename T, size_t Rows, size_t Cols> struct k_vnni_view;` parallel to the V ones at kv_cache_fwd.hpp:33-36 (PARENT).
  WHY: Design goal (b)/(c): the K VNNI plane crosses the cache/kernel boundary as a typed view, no raw bf16* K-plane pointer. Same mechanism the PARENT used for the V plane.
  EVIDENCE: PARENT diff 996f58ec82..c12df586b6 of amx_attn_iface.hpp: `+#include "tron/tensor/kv_cache_fwd.hpp"` and `-void weights_times_v_128x4(const bf16* v_page,` -> `+    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page,`. Design: 'Then amx_attn_iface.hpp can declare qk_vnni_128x4(k_vnni_view<const bf16,PAGE_TOKENS_64,HEAD_SIZE_128>, const bf16*, float*, size_t) noexcept without intrinsics.' Ben's sketch: 'qk_vnni_128x4(page.v_packed(...), ...);  // Compile error'.
- [MUST] src/tron/kernels/amx_attn.cpp @ qk_vnni_128x4 definition (worktree lines 226-290)
  CHANGE: Retype the first parameter as in the declaration. Add as the first statement `const bf16* const k_plane = detail::k_vnni_access::plane(k_page);` (if k_vnni_access lives in tron::detail, like v_vnni_access; see risk about namespaces) and replace the four `k_vnni_plane + (step * TOKEN_BLOCKS_4 + b) * PANEL_ELEMS_512` tile-load addresses with `k_plane + ...`. No other statement changes, so the loaded bytes, the tile sequence and the scores are unchanged (goal d).
  WHY: Compile necessity after M1, and the exact pattern the PARENT used in weights_times_v_128x4.
  EVIDENCE: PARENT amx_attn.cpp (worktree lines 304-307): `const bf16* const v_pairs = detail::v_vnni_access::plane(v_page);` with comment 'This kernel is one of the two layout-specific readers allowed to take the plane address'. PARENT qk_rowmajor_128x4 (worktree 156): `const bf16* const k_rows = k_page.data;`.
- [MUST] h/tron/models/self_attention.hpp @ apply_dense_amx_page, worktree lines 1675-1679 (VNNI branch of the QK call)
  CHANGE: Replace `pg.template k_vnni_plane<geometry.kv>(slot, kv_head)` with `pg.template k_packed<geometry.kv>(slot, kv_head)`. `pg` is `const page&`, so the const overload returns `k_vnni_view<const bf16, page::page_size, geometry.kv.head_size>`; inside this branch page_size == 64 (static_assert at worktree 1645-1646) and head_size == 128 (layout_on<128> plus the eligible static_assert at 1640-1643), so the type equals the kernel parameter exactly, no conversion.
  WHY: Design table 'page::k, page::k_vnni_plane': 'Replace the raw packed-plane accessor with page::k_packed<geometry>(slot, head) ... Const access returns k_vnni_view<const bf16,page_size,geometry.head_size> from the owner.' Mirrors the PARENT's `pg.template v_packed<geometry.kv>(slot, kv_head)` at worktree 1720.
  EVIDENCE: CHILD kv_cache.hpp:1689-1693: `const bf16* k_vnni_plane(...) const { return reinterpret_cast<const bf16*>(kv_block<geometry>(slot, kv_head).k); }` (the raw accessor to delete). PARENT kv_cache.hpp:1946-1954: `v_vnni_view<const bf16, page_size, geometry.head_size> v_packed(...) const { return kv_block<geometry>(slot, kv_head).v.as_view(); }`.
- [MUST] h/tron/models/self_attention.hpp @ apply_page_tok software loop, worktree lines 1876-1884 (k_vnni::qk_group call)
  CHANGE: Pass `page.template k_packed<geometry.kv>(slot, kv_head)` instead of `page.template k_vnni_plane<geometry.kv>(slot, kv_head)`. Correspondingly, qk_group in h/tron/kernels/k_vnni.hpp changes its first parameter from `const bf16* plane` to `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page` and extracts the pointer once with k_vnni_access (the fp16 recursion at CHILD k_vnni.hpp:260 forwards the view unchanged). The query pointer `q.data + kv_head * operation_kv_mul * operation_head_size` stays a raw pointer: Q is an activation, not a cache plane, and the PARENT also kept `const bf16* q_packed` raw.
  WHY: Goal (c) names the cache/kernel boundary; qk_group is the second K-plane reader. Design: 'Pass k_vnni_view<const bf16,64,128> by value to qk_vnni_128x4 and the corresponding shape to qk_group.' Ben's sketch: 'The AVX-512 fallback also takes packed_k_page.'
  EVIDENCE: CHILD k_vnni.hpp:246-252: `template <size_t kv_mul, typename q_scalar> void qk_group(const bf16* plane, const q_scalar* q, uint64_t live, float* s, size_t s_stride) noexcept`. Call at CHILD self_attention.hpp:1636-1639.
- [MUST] h/tron/models/self_attention.hpp @ include block, worktree lines 21-28
  CHANGE: Add `#include "tron/kernels/k_vnni.hpp"` (for k_vnni::qk_group and k_vnni::layout_on). Today the CHILD reaches both through kv_cache.hpp:27 (`#include "tron/kernels/k_vnni.hpp"`); the design makes kv_cache.hpp include the tensor header instead and drop the kernel header, so self_attention.hpp would stop compiling without its own include.
  WHY: Design: 'The cache drops its include of this kernel header. self_attention.hpp includes the kernel header directly for qk_group.'
  EVIDENCE: CHILD kv_cache.hpp:27 is the only route today; grep of the worktree self_attention.hpp includes (lines 16-28) shows no k_vnni include.
- [MUST] t/t_amx_dispatch_dtype.cpp @ fakes at worktree 204-222 and includes at 43-51
  CHANGE: Fake: `void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>, const bf16*, float* output, size_t stride) noexcept { ++probe.qk_calls; std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f); }`. Add `#include "tron/tensor/k_vnni.hpp"`. The fakes are defined outside `#ifdef TRON_AMX_DISPATCH` (worktree 180-224 vs TEST_CASE guard at 226), so the k_vnni_view CLASS must be defined in the 8-lane build too (only its AVX-512 operation bodies may be guarded), exactly as v_vnni.hpp:46-49 states for V.
  WHY: Compile necessity after M1; the file is a separate TU that overrides the kernels, so a signature mismatch is a silent ODR break or a link error.
  EVIDENCE: PARENT fake at worktree 197-203 `void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>, ...)` and 218-221 `void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>, ...)`. Design: 'Keep K class definitions complete in both vector widths for unconditional fake definitions. Guard packed operation bodies at 16 lanes.'
- [MUST] t/t_amx_numerics.cpp (outside AREA, forced by M1) @ CHILD lines 211-233 (struct vnni_plane, scatter_row into plane->v, qk_vnni_128x4(plane->v, ...))
  CHANGE: Replace the raw `struct alignas(64) vnni_plane { bf16 v[64*128]; }` with a `tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>` owner, fill it through the typed store_row on `owner.as_view()`, and call `qk_vnni_128x4(std::as_const(*owner).as_view(), q_rows, ...)`. This test is the bit-identity proof (goal d) and must keep passing.
  WHY: Compile necessity: the kernel no longer accepts `const bf16*`. The PARENT did the same explicit wrap for the row-major side.
  EVIDENCE: PARENT t_amx_numerics.cpp:162-166: 'The fixture's aligned row-major K block, wrapped explicitly as the whole native K plane the kernel takes.' `qk_rowmajor_128x4(tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, ...)`. CHILD test name: 'AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K'.
- [SHOULD] src/tron/kernels/amx_attn.cpp @ file-scope tile constants (worktree 43-60) and the function-local block in qk_vnni_128x4 (worktree 259-269)
  CHANGE: Adopt the PARENT's convention (file-scope constants, one comment line per kernel, name ends in the register number). Delete the CHILD's local `Q_TILE_4, K_TILE_5, K_TILE_6, S_TILE_0..3` and use `ACCUMULATOR_TILE_0..3` for the four C tiles (same registers 0-3, same role: _tile_dpbf16ps destinations) plus new file-scope `Q_ROWS_TILE_4 = 4; K_EVEN_PANEL_TILE_5 = 5; K_ODD_PANEL_TILE_6 = 6;` with the comment '// qk_vnni_128x4: the padded Q rows load into tile 4. K panels 0 and 2 load into tile 5, K panels 1 and 3 into tile 6.' Update the block comment 'Both kernels load their operands into tiles 4-6' to 'All three kernels'. Register-number check: all three kernels use 0-3 as accumulators and 4-6 as operands, and each kernel runs between its own _tile_zero and _tile_stored calls under one begin_region() config of 8 identical tiles, so there is no runtime collision; the only issue is two different identifiers named Q_TILE_* for registers 6 and 4 in one TU.
  WHY: Decision (3) in the task and consistency: the merged TU would otherwise carry two naming schemes (file-scope role names vs function-local names) and the misleading pair Q_TILE_6 (file scope) / Q_TILE_4 (local).
  EVIDENCE: PARENT worktree 47-60: `ACCUMULATOR_TILE_0..3`, `K_EVEN_BLOCK_TILE_4`, `K_ODD_BLOCK_TILE_5`, `Q_TILE_6`, `P_TILE_4`, `V_EVEN_SLICE_TILE_5`, `V_ODD_SLICE_TILE_6`. CHILD 30c4ac82cb 'VNNI K: name the tile registers in qk_vnni_128x4' adds the local `Q_TILE_4 = 4; K_TILE_5 = 5; K_TILE_6 = 6; S_TILE_0..3`.
- [SHOULD] h/tron/kernels/amx_attn_iface.hpp @ qk_vnni_128x4 comment, worktree 246-253
  CHANGE: Replace 'k_vnni_plane = the page's 16 KiB K plane (k_vnni.hpp layout). q_rows = the pack_q_rows_128x4 output.' with 'k_page = the page's packed K plane (64 tokens x 128 dims, 16 KiB) as its typed view k_vnni_view (layout: h/tron/tensor/k_vnni.hpp). A bare pointer, the native K view or a packed V view is a compile error. q_rows = the pack_q_rows_128x4 output.' Keep the reference 'Note [K VNNI storage] in kv_cache.hpp' only if that Note stays in kv_cache.hpp (see open question).
  WHY: Sentence becomes wrong after M1 (no pointer parameter; the layout header splits).
  EVIDENCE: Worktree amx_attn_iface.hpp:252-253.
- [SHOULD] h/tron/kernels/amx_attn_iface.hpp @ qk_rowmajor_128x4 comment, worktree 228-231, and Note [AMX attention dispatch] line 60
  CHANGE: 228-231: 'so that a packed V plane or a bare pointer cannot be handed in by mistake' -> 'so that a packed K or V plane or a bare pointer cannot be handed in by mistake'. Line 60: 'AMX: qk_rowmajor_128x4 per page' -> 'AMX: qk_rowmajor_128x4 (row-major K) or qk_vnni_128x4 (VNNI K) per page'. The latter was already incomplete at CHILD; the port is the moment both kernels take typed views.
  WHY: Accuracy of the contract diagram after the port.
  EVIDENCE: Worktree amx_attn_iface.hpp:60 and 228-231.
- [SHOULD] h/tron/kernels/amx_attn_iface.hpp @ Note [QK orientation] addition, worktree 216-224
  CHANGE: No wording change needed for the port: `page::set_k_row`, `page::set_k_block` and `k_vnni::qk_group` keep their names and homes under the design ('Keep the name' for set_k_block; qk_group stays in h/tron/kernels/k_vnni.hpp). Verified; leave as is. (PR 4737 rewrites this paragraph for the row-major tail block; that is its own merge.)
  WHY: Task item 4 asked for the check.
  EVIDENCE: Design table rows 'page::set_k_row, page::get_k_row' and 'page::set_k_block'; PR 4737 diff of amx_attn_iface.hpp lines 216-226.
- [SHOULD] t/t_llama_unit.cpp (outside AREA; parent precedent) @ beside amx_qk_accepts / amx_pv_accepts (PARENT 95-105) and the STATIC_REQUIRE block (PARENT 386-416)
  CHANGE: Add `amx_qk_vnni_accepts<K>` probe and assertions: accepts `k_vnni_view<const bf16,64,128>` and `k_vnni_view<bf16,64,128>` (writable converts to read-only), rejects `const bf16*`, `bf16*`, `v_plane_t`, `k_plane_t` (const_native_k_view). Also `STATIC_REQUIRE_FALSE(amx_qk_accepts<k_packed_plane_t>)` and `STATIC_REQUIRE_FALSE(amx_pv_accepts<k_packed_plane_t>)`.
  WHY: Design 'Typed function boundaries' row; the PARENT encodes the same contract for the two existing kernels.
  EVIDENCE: PARENT t_llama_unit.cpp:397-405 STATIC_REQUIRE(amx_qk_accepts<k_plane_t>) ... STATIC_REQUIRE_FALSE(amx_pv_accepts<k_plane_t>).
- [SHOULD] h/tron/models/self_attention.hpp @ keys / dot_q if-constexpr lambdas, worktree 1825-1847 and 1866-1874
  CHANGE: No code change. `keys` in the row-major branch is `decltype(page.template k<geometry.kv>(slot, kv_head)){}`; with `page` being `const page&` this is the PARENT's `const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>` (kv_block::k_view() const), default-constructed to nullptr, so `keys.valid()`/`keys = page.template k<...>(...)`/`keys[i]` compile unchanged. The CHILD's `!k_vnni::layout_on` constraints on page::k must be re-applied in the kv_cache.hpp merge (CHILD 1619-1676) so the VNNI branch never instantiates a row view; the `if constexpr` guards make this a consistency point, not a compile point. Keep the placeholder `return 0;` pattern as the CHILD wrote it.
  WHY: Confirms no port-caused change; records the dependency on the cache-side constraint.
  EVIDENCE: PARENT kv_cache.hpp:2479-2484 k_view() const; CHILD kv_cache.hpp:1618-1626 `requires(layout_t::uniform_geometry && !k_vnni::layout_on<head_size>)`.
- [COULD] h/tron/kernels/amx_attn_iface.hpp @ Note [AMX attention dispatch] worktree 24-27 and 57, and pack_q_group_128x4 comment 173-187
  CHANGE: These describe only the row-major orientation (Q packed as the B operand, 'the K operand fills its tiles'); under VNNI K Q is the A operand (pack_q_rows_128x4). Stale since the CHILD, not caused by the port. A one-sentence pointer to pack_q_rows_128x4 / Note [QK orientation] would fix it.
  WHY: Accuracy; low priority.
  EVIDENCE: Worktree amx_attn_iface.hpp:24-27, 57, 173-177.

## proposed_code
// ---- h/tron/tensor/kv_cache_fwd.hpp (other agent's file; needed by the iface) ----
// Packed K types (h/tron/tensor/k_vnni.hpp): the owner holds one bf16 array of
// [Rows tokens * Cols dimensions] in the VNNI panel order; the view refers to it.
template <size_t Rows, size_t Cols>
struct k_vnni_tensor;
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view;

// ---- h/tron/kernels/amx_attn_iface.hpp (replaces worktree 254-257) ----
// Dense QK for one page whose K is stored in the VNNI layout (Note [K VNNI
// storage]). Computes S = Q . K^T. The padded Q rows are the A operand. The
// page's 16 K panels are the B operand. There is no transpose. Writes
// s[4][s_stride_floats] fp32, all 64 token columns, UNSCALED. The 16-row tile
// stores write to a buffer inside the kernel. Only the 4 query rows are copied
// out, so `s` needs 4 rows (Note [Tile stores write 16 rows]). k_page = the
// page's packed K plane (64 tokens x 128 dims, 16 KiB) as its typed view; a
// bare pointer, the native K view or a packed V view is a compile error.
// q_rows = the pack_q_rows_128x4 output.
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_rows,
    float* s,
    size_t s_stride_floats) noexcept;

// ---- src/tron/kernels/amx_attn.cpp ----
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"
// file-scope tile constants: keep the PARENT block, change "Both kernels" to
// "All three kernels", append:
// qk_vnni_128x4: the padded Q rows load into tile 4. K panels 0 and 2 load
// into tile 5, K panels 1 and 3 into tile 6.
constexpr int Q_ROWS_TILE_4 = 4;
constexpr int K_EVEN_PANEL_TILE_5 = 5;
constexpr int K_ODD_PANEL_TILE_6 = 6;

void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_rows,
    float* s,
    size_t s_stride_floats) noexcept {
  // The plane's first element: panel (step 0, block 0), pair row 0. This
  // kernel is one of the two layout-specific readers allowed to take the
  // plane address (the other is k_vnni::qk_group).
  const bf16* const k_plane = detail::k_vnni_access::plane(k_page);
  // ... CHILD body unchanged, with these substitutions:
  //   Q_TILE_4 -> Q_ROWS_TILE_4, K_TILE_5 -> K_EVEN_PANEL_TILE_5,
  //   K_TILE_6 -> K_ODD_PANEL_TILE_6, S_TILE_b -> ACCUMULATOR_TILE_b,
  //   k_vnni_plane + ... -> k_plane + ...
  //   (delete the seven local constexpr int tile definitions)
}

// ---- h/tron/models/self_attention.hpp, apply_dense_amx_page ----
      if constexpr (k_vnni::layout_on<operation_head_size>) {
        amx_attn_h128g4::qk_vnni_128x4(pg.template k_packed<geometry.kv>(slot, kv_head),
            q_packed, &s_pages[0][0], page::page_size);
      } else {
        amx_attn_h128g4::qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head),
            q_packed, &s_pages[0][0], page::page_size);
      }

// ---- h/tron/models/self_attention.hpp, apply_page_tok software loop ----
          if (relevant_k_tokens > 0) {
            k_vnni::qk_group<operation_kv_mul>(
                page.template k_packed<geometry.kv>(slot, kv_head),
                q.data + kv_head * operation_kv_mul * operation_head_size, live,
                &s_pages[0][0], page::page_size);
          }
// plus, in the include block:
#include "tron/kernels/k_vnni.hpp"  // k_vnni::qk_group, k_vnni::layout_on

// ---- h/tron/kernels/k_vnni.hpp (kernel header, other agent's file; the call above needs it) ----
template <size_t kv_mul, typename q_scalar>
TRON(inline)
void qk_group(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const q_scalar* q,
    uint64_t live,
    float* s,
    size_t s_stride) noexcept {
  // Inside namespace tron::k_vnni an unqualified `detail::` names
  // tron::k_vnni::detail, so qualify the access helper fully.
  const bf16* const plane = tron::detail::k_vnni_access::plane(k_page);
  // fp16 branch: qk_group<kv_mul, float>(k_page, qf, live, s, s_stride);
  // ... body unchanged otherwise
}

// ---- t/t_amx_dispatch_dtype.cpp fakes ----
#include "tron/tensor/k_vnni.hpp"
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}

// ---- t/t_llama_unit.cpp probes (pattern of PARENT 95-105, 386-405) ----
template <typename K>
constexpr bool amx_qk_vnni_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0});
};
using k_packed_plane_t = k_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64,
    amx_attn_h128g4::HEAD_SIZE_128>;
using k_packed_plane_mut_t = k_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64,
    amx_attn_h128g4::HEAD_SIZE_128>;
STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_plane_t>);
STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_plane_mut_t>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<v_plane_t>);
STATIC_REQUIRE_FALSE(amx_qk_accepts<k_packed_plane_t>);
STATIC_REQUIRE_FALSE(amx_pv_accepts<k_packed_plane_t>);

## design_contradictions
- Design text asks for k_vnni_row and expression-based views ('Define k_vnni_tensor, k_vnni_view, and k_vnni_row for the proposed logical expression reads'; 'Add unconstrained k_vnni_tensor, k_vnni_view, and k_vnni_row forward declarations'). Overridden by PARENT decision (1): commit c12df586b6 dropped v_vnni_row and the expr base, and the PR body says 'Dropped by agreement ... The reviewer asked why the code exists'. So kv_cache_fwd.hpp gets only k_vnni_tensor and k_vnni_view, and the design's own fallback applies: 'If Q3 is rejected, remove the row expressions and their compatibility checks from both families.'
- Design says 'The child's AVX-512 query/key score reader in h/tron/kernels/k_vnni.hpp' keeps only qk_group, and 'detail::k_vnni_access in h/tron/tensor/k_vnni.hpp' parallel to tron::detail::v_vnni_access. The CHILD already has a namespace tron::k_vnni::detail (k_vnni.hpp:109-133 pair_base/pair_row_offsets, 148-180 transpose_16x16_epi32) that the design moves to the tensor header. If k_vnni_access is placed in tron::detail (parallel to V), an unqualified `detail::k_vnni_access` inside namespace tron::k_vnni (qk_group) resolves to tron::k_vnni::detail and fails to compile; inside tron::amx_attn_h128g4 (amx_attn.cpp) it resolves to tron::detail and works. The design does not say which `detail`. Resolution proposed above: tron::detail::k_vnni_access, fully qualified from inside tron::k_vnni.
- Design table row 'page::k, page::k_vnni_plane: Keep native overloads and their !layout_on restrictions' presumes the PARENT's page::k carries those restrictions. It does not (PARENT kv_cache.hpp:1848-1897 has only uniform_geometry / declares_geometry constraints); the CHILD's `!k_vnni::layout_on` constraints (CHILD 1619-1676) must be re-added during the kv_cache.hpp merge. The code in my area compiles either way because every use sits under `if constexpr (k_vnni::layout_on...)`.
- The CHILD's iface comment 'k_vnni_plane = the page's 16 KiB K plane (k_vnni.hpp layout)' and the CHILD's Note [K VNNI storage] ('the VNNI pair-interleaved layout of tron/kernels/k_vnni.hpp') name the kernel header as the layout home. After the design's header split the layout lives in h/tron/tensor/k_vnni.hpp. Both sentences need the new path.

## risks
- PR #4737 (origin/jhan-amx-vnniK-i4500) depends on the raw accessor: self_attention.hpp there keeps `const bf16* plane = page.template k_vnni_plane<geometry.kv>(slot, kv_head);`, calls `k_vnni::qk_group<...>(plane, ...)` and builds a `const_view<bf16, ROW_ALIGNED_TRUE, ROW_DMA_FALSE, seq<128>> k{k_vnni::row_ptr(plane, i)}` for the row-major tail block (PR 4737 diff of self_attention.hpp, hunks at 1650-1680). After this port k_vnni_plane no longer exists, so 4737 must take `k_packed` and give row_ptr / convert_block a view parameter through k_vnni_access. This is a conflict to resolve at 4737's rebase, not an impossibility; it also restores the unconditional `std::array<dotter...> dot_q`, which conflicts with the CHILD's if-constexpr lambda that this port keeps.
- The fakes in t/t_amx_dispatch_dtype.cpp are compiled in every build, including 8-lane builds with TRON_AMX_DISPATCH off (fake block at worktree 180-224 is outside the `#ifdef TRON_AMX_DISPATCH` at 226). The CHILD's k_vnni.hpp has no `#if TRON_CHUNK_SIZE == 16` guard at all (grep: only `#ifdef TRON_K_VNNI` at line 91) and uses __mmask16 and _mm512 intrinsics in always_inline functions (tron_inline = inline __attribute__((always_inline)), attributes.hpp:78). The new tensor header must define the k_vnni_view / k_vnni_tensor classes unconditionally and guard the operation bodies, as v_vnni.hpp:229-408 does. Insufficient data on whether the CHILD today compiles at 8 lanes; an 8-lane build with TRON_K_VNNI=OFF would resolve it.
- Tile-naming unification (S1) touches a numerics-sensitive kernel. The change is identifier-only (same register numbers, same instruction order), but it must be checked by the existing bit-identity test 'AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K' (t_amx_numerics.cpp) after that test is retyped (M7); without the retype that test does not compile and the proof is lost.
- A `k_vnni_view<const bf16, 64, 128>` parameter only matches `k_packed<geometry.kv>` when page_size == 64 and head_size == 128. Both are already enforced in apply_dense_amx_page (static_asserts at worktree 1640-1646) and in the software loop (layout_on<128>, static_assert at 1877); if a future head size gains layout_on, the calls stop compiling rather than silently miscomputing, which is the intended behaviour but should be stated in the k_packed comment.
- If kv_cache.hpp drops its `#include "tron/kernels/k_vnni.hpp"` before self_attention.hpp gains its own include (M5), self_attention.hpp fails to find k_vnni::qk_group while k_vnni::layout_on (moved to the tensor header) still resolves; the error is easy to misread as a namespace problem.

## open_questions
- Does Note [K VNNI storage] stay in kv_cache.hpp, or move to h/tron/tensor/k_vnni.hpp as the PARENT moved Note [VNNI Packed V layout] to v_vnni.hpp? The design keeps it in kv_cache.hpp ('Note [K VNNI storage] is a comment in the child's kv_cache.hpp'; F25 'Retain the connection'). Five references in my area (amx_attn_iface.hpp 216, 246-247; self_attention.hpp 1587, 1656, 1812) must follow the choice.
- Which namespace holds k_vnni_access: tron::detail (parallel to v_vnni_access, as the design table implies) or tron::k_vnni::detail (next to the moved pair_base helpers)? The proposed code assumes tron::detail and fully qualifies it inside tron::k_vnni.
- Should qk_group's plane parameter be the concrete `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>` (kernel serves 64x128 only; matches the design's 'corresponding shape') or a template on <Rows, Cols> with a static_assert? The concrete type is proposed because the kernel body hard-codes TOKEN_BLOCKS_4 and DIM_STEPS_4.
- t_k_vnni_layout.cpp:306-308 calls qk_group with a raw `buf->plane`; after M4 the test needs a k_vnni_tensor owner (design: 'Adapt t_k_vnni_layout to actual aligned owners'). Confirm that the t/ owner handles it together with t_amx_numerics (M7).
