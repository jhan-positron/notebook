// Dispatch-level regression test for the AMX query-scalar gate and the
// dense-page predicate, on any host: drives the production apply_page_range on
// a 4-head / 1-KV-head / 128-dim model (the AMX shape) for each CPU executor
// and records what the AMX entry points receive. This translation unit
// defines every amx_attn_h128g4 entry point as a CPU fake, so the linker never
// pulls libtron's amx_attn.cpp object and no AMX instruction is linked or
// executed; available() is the fake too, so the dispatch believes AMX is
// present. The K layout of the build selects which packer and which QK kernel
// the dispatch calls. The layout is row-major, or under TRON_K_VNNI the VNNI
// (Vector Neural Network Instructions) layout (Note [K VNNI storage] in
// kv_cache.hpp). The fakes of both packers and both QK kernels count into the
// same probe, and the fake of the VNNI packer counts a second time. So the
// expectations below hold for either layout, and the VNNI packer count checks
// that the dispatch picks the packer of the build's layout (the two packers
// share one signature; the kernel is pinned by its view type).
//   host_bf16, full page: the Q pack runs exactly once and sees the query
//   values. The dense QK and PV kernels run once each.
//   host_bf16, partial page (63 tokens): the Q pack still runs (it happens
//   once per token, after the outer visibility and window checks but before
//   the page's dense predicate) and neither kernel runs - the page is not
//   dense, so the AVX dotter serves it.
//   host_bf16, second call with changed queries: the pack runs again and sees
//   the new values (the "already packed" state is per call, not per thread).
//   host (float), host_fp16 (fp16): the gate (amx_attn_h128g4::eligible over
//   the executor's activation scalar) keeps every AMX entry point from
//   running - before the gate, the pack read these executors' bytes as bf16.
// Test shape and fakes from codex's review of PR #3879 (its
// t_amx_dispatch_dtype probe); the post-fix expectations are ours.
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <type_traits>
#include <vector>

#include <catch2/catch_test_macros.hpp>

#include "common/indexed.hpp"
#include "common/json.hpp"
#include "common/mask.hpp"
#include "common/numerics.hpp"
#include "common/types.hpp"
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/models/common.hpp"
#include "tron/models/model.hpp"
#include "tron/models/ranged_mask.hpp"
#include "tron/plugins/llama.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"

using namespace tron;

namespace {

struct amx_probe {
  size_t pack_calls = 0;
  size_t rows_pack_calls = 0;  // pack_q_rows_128x4 only: the packers share a signature
  size_t qk_calls = 0;
  size_t pv_calls = 0;
  std::array<float, amx_attn_h128g4::GROUP_HEADS_4 * amx_attn_h128g4::HEAD_SIZE_128>
      q{};
};

amx_probe probe;
// What the fake amx_attn_h128g4::available() below answers: false stands for
// the kill switch (TRON_AMX_DISABLE=1) or a CPU without AMX.
bool fake_amx_available = true;

// Runs apply_page_range over one page holding `n_tokens` tokens, with the
// query at the last token, and records the fakes' calls in `probe`. With
// `repeat` the call is made a second time with different query values.
// `amx_available` is what the fake available() answers during the call.
template <typename executor_t>
void exercise_page(size_t n_tokens, bool repeat = false, bool amx_available = true) {
  constexpr size_t head_size = 128;
  constexpr size_t n_heads = 4;
  constexpr size_t n_kv_heads = 1;
  constexpr size_t n_layers = 1;
  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};
  constexpr llm_configuration config{.type = model_type::llama,
      .dim = n_heads * head_size,
      .hidden_dim = 512,
      .n_layers = n_layers,
      .n_heads = n_heads,
      .n_kv_heads = n_kv_heads,
      .vocab_size = 32,
      .head_size = head_size,
      .attention_scale = 0x1.6a09e6p-4f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t = model<llm<config, executor_t>>;
  using state_t = model_t::state;
  using book_t = model_t::book;
  using query_scalar = typename executor_t::template btensor_t<1>::element;
  REQUIRE(n_tokens >= 1);
  REQUIRE(n_tokens <= book_t::page_size);

  auto model =
      std::make_unique<model_t>(std::filesystem::path{}, json(json::value_t::object));
  book_t cache(
      /*n_pages=*/1, /*storage_slot_count=*/n_layers, /*support_eagle=*/false);
  auto* page = cache.page_of(0);
  const kv_slot_id slot = book_t::kv_slot(model_layer_id(0));
  alignas(64) std::array<bf16, head_size> zero{};
  for (size_t token = 0; token < n_tokens; ++token) {
    page->set_k_row(slot, 0, token, k_source_row<head_size>(zero.data()));
    page->template set_v<geometry.kv>(
        slot, 0, token, v_source_row<head_size>(zero.data()));
    cache.increment_tokens_used();
  }
  page->set_lo(0, 0);
  page->set_offset_bound(n_tokens);

  state_t state(*model, model_config{.max_layers = n_layers});
  std::array<typename book_t::page_t*, 1> pages{page};
  state.pages.items = std::span<typename book_t::page_t* const>(pages);
  indexed_vector<token_job_id, token_id> token_jobs;
  token_jobs.push_back(token_id(n_tokens - 1));
  state.token_jobs = token_jobs;
  std::array<uint32_t, book_t::page_size> positions{};
  for (size_t i = 0; i < positions.size(); ++i)
    positions[i] = i;
  state.token_positions.items = std::span<const uint32_t>(positions);

  ranged_mask mask;
  mask_t<ranged_mask_capacity> visible{};
  visible.insert(0);
  mask.add_range(
      token_id(0), token_id(n_tokens), visible, mask_t<ranged_mask_capacity>{});
  state.query_mask = &mask;

  std::array<float, n_heads * head_size> expected{};
  auto& q = state.plugin_state.qs_roped[token_job_id(0)];
  for (size_t i = 0; i < expected.size(); ++i) {
    expected[i] = 1.0f + static_cast<float>(i % 4) * 0.25f;
    q[i] = static_cast<query_scalar>(expected[i]);
  }
  state.self_attn_state.attn[0].clear_validity(1);
  // Attention path stats forced on for this state: the tallies must agree with
  // the fakes' call counts (h/tron/models/attn_stats.hpp).
  {
    tron::attn_stats::header_facts facts;
    facts.n_kv_heads = n_kv_heads;
    facts.kv_mul = n_heads / n_kv_heads;
    facts.head_size = head_size;
    facts.n_layers = n_layers;
    facts.page_size = book_t::page_size;
    constexpr bool STATS_ON_TRUE = true;
    constexpr bool NOT_EAGLE_FALSE = false;
    state.self_attn_state.stats =
        std::make_shared<tron::attn_stats::model_stats>(STATS_ON_TRUE, "",
            NOT_EAGLE_FALSE, facts, state.self_attn_state.attn.size(), n_layers);
  }

  std::vector<token_job_id> jobs{token_job_id(0)};
  std::array<page_id, 1> page_ids{page_id(0)};
  const auto& operation = model_t::plugin_t::attention_operations[0];
  // The expectation is stated independently of the production gate: only a
  // bf16 query buffer may reach the packer, which copies bf16 values and
  // converts nothing. With available() false nothing is packed either.
  const bool packs = std::is_same_v<query_scalar, bf16> && amx_available;
  // The dense predicate: the kernels run only for a full page.
  const bool dense = packs && n_tokens == book_t::page_size;
  fake_amx_available = amx_available;
  for (int round = 0; round < (repeat ? 2 : 1); ++round) {
    if (round == 1) {
      // Different query values: the second call must pack again and see them.
      for (size_t i = 0; i < expected.size(); ++i) {
        expected[i] = -2.0f - static_cast<float>(i % 8) * 0.5f;
        q[i] = static_cast<query_scalar>(expected[i]);
      }
      state.self_attn_state.attn[0].clear_validity(1);
    }
    probe = {};
    {
      // The production sequence: the forward is open while the page is visited.
      attn_stats::forward_scope stats_scope(*state.self_attn_state.stats,
          attn_stats::forward_class::decode_like, token_jobs.size(), token_jobs.size());
      // batch_queries (the batch's query mask) only matters when a section is
      // large enough to dismiss workless ranges; one page and one query never is.
      state.self_attn_state.template apply_page_range<geometry>(jobs, operation,
          state.plugin_state.qs_roped, 0, 0, 1, std::span<const page_id>(page_ids), {},
          visible);
    }
    CAPTURE(round);
    REQUIRE(probe.pack_calls == (packs ? 1 : 0));
    // The packer of the build's K layout ran, never the other one.
    REQUIRE(probe.rows_pack_calls == (packs && k_vnni::layout_on<head_size> ? 1 : 0));
    REQUIRE(probe.qk_calls == (dense ? 1 : 0));
    REQUIRE(probe.pv_calls == (dense ? 1 : 0));
    // The path tallies are cumulative over the rounds: one visit per call, on
    // the AMX path exactly when the kernels ran, else on the AVX path with
    // every token of the page relevant.
    {
      using namespace tron::attn_stats;
      const size_t decode_class = static_cast<size_t>(forward_class::decode_like);
      const auto sums = state.self_attn_state.stats->sum_layer(decode_class, 0);
      const uint64_t calls = static_cast<uint64_t>(round) + 1;
      REQUIRE(
          sums.visits_all(static_cast<size_t>(visit_path::amx)) == (dense ? calls : 0));
      REQUIRE(
          sums.visits_all(static_cast<size_t>(visit_path::avx)) == (dense ? 0 : calls));
      REQUIRE(sums.visits_all(static_cast<size_t>(visit_path::empty)) == 0);
      REQUIRE(sums.k_tokens_all(static_cast<size_t>(
                  dense ? visit_path::amx : visit_path::avx)) == calls * n_tokens);
      REQUIRE(sums.avx_full_page_visits[PASS_READY_0] ==
              (!dense && n_tokens == book_t::page_size ? calls : 0));
      REQUIRE(sums.visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == 0);
      // The per-token path set of the one job, written by apply_page_range and
      // folded at the end of the scope, cumulative over the rounds: the AMX
      // set exactly when the kernels ran, else the AVX set, never both.
      forward_counters const& fc = state.self_attn_state.stats->forwards[decode_class];
      REQUIRE(load_relaxed(
                  fc.token_jobs_by_path_set[dense ? PATH_BIT_AMX_2 : PATH_BIT_AVX_1]) ==
              calls);
      REQUIRE(
          load_relaxed(
              fc.token_jobs_by_path_set[dense ? PATH_BIT_AVX_1 : PATH_BIT_AMX_2]) == 0);
    }
    if (packs) {
      for (size_t i = 0; i < expected.size(); ++i) {
        CAPTURE(i, expected[i], probe.q[i]);
        REQUIRE(probe.q[i] == expected[i]);
      }
    }
  }
}

}  // namespace

namespace tron::amx_attn_h128g4 {

bool available() noexcept {
  return fake_amx_available;
}
void begin_region() noexcept {}
void end_region() noexcept {}

void pack_q_group_128x4(const bf16* input, bf16* output) noexcept {
  ++probe.pack_calls;
  for (size_t i = 0; i < probe.q.size(); ++i)
    probe.q[i] = static_cast<float>(input[i]);
  std::fill_n(output, Q_PACK_ELEMS_2048, bf16{});
}
void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}
void pack_q_rows_128x4(const bf16* input, bf16* output) noexcept {
  ++probe.pack_calls;
  ++probe.rows_pack_calls;
  for (size_t i = 0; i < probe.q.size(); ++i) {
    probe.q[i] = static_cast<float>(input[i]);
  }
  std::fill_n(output, Q_PACK_ELEMS_2048, bf16{});
}
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}
void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const float*,
    size_t,
    float* output) noexcept {
  ++probe.pv_calls;
  std::fill_n(output, TILE_ROWS_16 * HEAD_SIZE_128, 0.0f);
}

}  // namespace tron::amx_attn_h128g4

#ifdef TRON_AMX_DISPATCH
TEST_CASE("AMX dispatch rejects non-bf16 queries and partial pages",
    "[amx_numerics][attention]") {
  constexpr size_t page_size = amx_attn_h128g4::PAGE_TOKENS_64;
  SECTION("host_bf16, full page: one pack, one QK, one PV; a second call with "
          "new queries packs again") {
    exercise_page<host_bf16>(page_size, /*repeat=*/true);
  }
  SECTION("host_bf16, partial page: one pack, no kernel call") {
    exercise_page<host_bf16>(page_size - 1);
  }
  SECTION("host_bf16, full page, available() false: no pack, no kernel call, one "
          "AVX visit that scored the whole page") {
    // The kill-switch arm of the attention path stats: the visit lands on the
    // AVX path with the page's every token, and avx_full_page_visits counts it
    // as AMX-eligible volume that did not take AMX.
    exercise_page<host_bf16>(page_size, /*repeat=*/false, /*amx_available=*/false);
  }
  SECTION("host (float): no pack, no kernel call") {
    exercise_page<host>(page_size);
  }
  SECTION("host_fp16: no pack, no kernel call") {
    exercise_page<host_fp16>(page_size);
  }
}
#else
TEST_CASE("AMX dispatch dtype test skipped (dispatch not compiled)", "[amx_numerics]") {
  SUCCEED("build without TRON_AMX_DISPATCH - nothing to test");
}
#endif
