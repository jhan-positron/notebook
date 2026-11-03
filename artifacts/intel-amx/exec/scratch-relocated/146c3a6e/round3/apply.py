import pathlib, sys
WT = pathlib.Path('/home/jhan/workspace/ai-runs/tron-glimmer-amx')
def edit(rel, pairs):
    p = WT / rel
    s = p.read_text()
    for old, new, count in pairs:
        n = s.count(old)
        assert n == count, (rel, old[:60], n, count)
        s = s.replace(old, new)
    p.write_text(s)
    print('edited', rel, len(pairs), 'edits')

# 1. interface header: aliases (thread 4308443185) + use them in the declarations
edit('h/tron/kernels/amx_attn_iface.hpp', [
("""static_assert(GROUP_HEADS_16 == TILE_ROWS_16,
    "16 heads fill one tile's 16 rows (PV) and 16 columns (QK) exactly");
""",
"""static_assert(GROUP_HEADS_16 == TILE_ROWS_16,
    "16 heads fill one tile's 16 rows (PV) and 16 columns (QK) exactly");

// One page's K plane (row-major, one bf16 row per token) and V plane (VNNI
// pair-interleaved), read-only, as the kernels take them.
using const_k_row_major_plane_view =
    const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>;
using const_v_vnni_plane_view = v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>;
""", 1),
("void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page,",
 "void qk_rowmajor_128x4(const_k_row_major_plane_view k_page,", 1),
("    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page,",
 "    const_v_vnni_plane_view v_page,", 1),
])

# 2. kernel file: definitions + explicit instantiations use the aliases
edit('src/tron/kernels/amx_attn.cpp', [
("void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page,",
 "void qk_rowmajor_128x4(const_k_row_major_plane_view k_page,", 1),
("    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page,",
 "    const_v_vnni_plane_view v_page,", 1),
("    const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>,",
 "    const_k_row_major_plane_view,", 2),
("    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,",
 "    const_v_vnni_plane_view,", 2),
])

# 3. dispatch test
edit('t/t_amx_dispatch_dtype.cpp', [
# 4308443569: drop the reviewer credit
("""//   running - before the gate, the pack read these executors' bytes as bf16.
// Test shape and fakes from codex's review of PR #3879 (its
// t_amx_dispatch_dtype probe); the post-fix expectations are ours.
""",
"""//   running - before the gate, the pack read these executors' bytes as bf16.
""", 1),
# 4308387058: the fakes and the probe exist only in the dispatch build (CI warning
# "variable 'probe' is not needed" in the build without TRON_AMX_DISPATCH)
("""using namespace tron;

namespace {

struct amx_probe {""",
"""using namespace tron;

#ifdef TRON_AMX_DISPATCH

namespace {

struct amx_probe {""", 1),
("""}  // namespace tron::amx_attn_h128g4

#ifdef TRON_AMX_DISPATCH
TEST_CASE("AMX dispatch rejects non-bf16 queries and partial pages",""",
"""}  // namespace tron::amx_attn_h128g4

TEST_CASE("AMX dispatch rejects non-bf16 queries and partial pages",""", 1),
# 4308443205: the group size by its own name
("// `n_heads` is also the AMX group size: the model has one KV head.\n",
 "// `n_heads` is the model's query head count.\n", 1),
("""  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};
""",
"""  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};
  // The AMX group size, derived the way the production call sites derive it.
  constexpr size_t group_heads = geometry.kv_mul();
""", 1),
("""    REQUIRE(probe.pack_group_heads == (packs ? n_heads : 0));
    REQUIRE(probe.qk_group_heads == (dense ? n_heads : 0));
    REQUIRE(probe.pv_group_heads == (dense ? n_heads : 0));
""",
"""    REQUIRE(probe.pack_group_heads == (packs ? group_heads : 0));
    REQUIRE(probe.qk_group_heads == (dense ? group_heads : 0));
    REQUIRE(probe.pv_group_heads == (dense ? group_heads : 0));
""", 1),
# 4308443490 (named values) + 4308443061 (what the offset detects)
("""    // Per-head offsets let the fake distinguish which query head it receives.
    // Every value is exactly representable in bf16.
    constexpr float HEAD_OFFSET_STEP_0_0625 = 0.0625f;
    expected[i] = 1.0f + static_cast<float>(i / head_size) * HEAD_OFFSET_STEP_0_0625 +
                  static_cast<float>(i % 4) * 0.25f;
""",
"""    // Per-head offsets make a pack that starts at the wrong head, or steps
    // through the heads with the wrong stride, fail the value check below.
    // Every value is exactly representable in bf16.
    constexpr float QUERY_BASE_1_0 = 1.0f;
    constexpr float HEAD_OFFSET_STEP_0_0625 = 0.0625f;
    constexpr size_t VALUE_PERIOD_4 = 4;
    constexpr float VALUE_STEP_0_25 = 0.25f;
    expected[i] = QUERY_BASE_1_0 +
                  static_cast<float>(i / head_size) * HEAD_OFFSET_STEP_0_0625 +
                  static_cast<float>(i % VALUE_PERIOD_4) * VALUE_STEP_0_25;
""", 1),
# 4308443331: the 16-head section runs one round
("""  SECTION("host_bf16, 16 heads, full page: one pack, one QK, one PV, all with "
          "group_heads 16; a second call with new queries packs again") {
    exercise_page<host_bf16, amx_attn_h128g4::GROUP_HEADS_16>(
        page_size, /*repeat=*/true);
  }
""",
"""  SECTION("host_bf16, 16 heads, full page: one pack, one QK, one PV, all with "
          "group_heads 16") {
    exercise_page<host_bf16, amx_attn_h128g4::GROUP_HEADS_16>(page_size);
  }
""", 1),
])

# 4. numerics test
edit('t/t_amx_numerics.cpp', [
# 4308444165: a row above the new upper limit
("""  // llama-70b and qwen-3-32b have 64 query heads sharing 8 KV heads.
  constexpr size_t KV_MUL_8 = 8;
  STATIC_REQUIRE_FALSE(eligible<tron::bf16>(HEAD_SIZE_128, KV_MUL_8));
""",
"""  // llama-70b and qwen-3-32b have 64 query heads sharing 8 KV heads; no
  // kernel is instantiated for any group above 16.
  constexpr size_t KV_MUL_8 = 8;
  STATIC_REQUIRE_FALSE(eligible<tron::bf16>(HEAD_SIZE_128, KV_MUL_8));
  constexpr size_t KV_MUL_32 = 32;
  STATIC_REQUIRE_FALSE(eligible<tron::bf16>(HEAD_SIZE_128, KV_MUL_32));
""", 1),
# 4308443322: contract comments on the two helpers
("""template <size_t group_heads>
void check_qk() {
""",
"""// QK kernel against the AVX dotter for group_heads query rows. Rows
// group_heads..15 of s must keep the sentinel.
template <size_t group_heads>
void check_qk() {
""", 1),
("""template <size_t group_heads>
void check_pv() {
""",
"""// PV kernel against the RNE-weight reference and the truncating (AVX)
// weight reference for group_heads rows.
template <size_t group_heads>
void check_pv() {
""", 1),
# 4308387058 remedy: a skipped case is reported as skipped, not passed
("""  if (!tron::amx_attn_h128g4::available()) {
    WARN("AMX unavailable on this host - QK precision check skipped");
    return;
  }
""",
"""  if (!tron::amx_attn_h128g4::available()) {
    SKIP("AMX unavailable on this host - the QK precision check needs the kernel");
  }
""", 1),
("""  if (!tron::amx_attn_h128g4::available()) {
    WARN("AMX unavailable on this host - PV precision check skipped");
    return;
  }
""",
"""  if (!tron::amx_attn_h128g4::available()) {
    SKIP("AMX unavailable on this host - the PV precision check needs the kernel");
  }
""", 1),
])
print('ok')
