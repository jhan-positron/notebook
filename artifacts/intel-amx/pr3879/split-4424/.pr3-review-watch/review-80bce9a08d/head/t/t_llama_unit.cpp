// The first test case needs libstdc++'s precondition checks (see there). The
// define is on this target in t/CMakeLists.txt; without it that case compiles
// but can no longer fail.
#ifndef _GLIBCXX_ASSERTIONS
#error "t_llama_unit needs _GLIBCXX_ASSERTIONS (add_catch_test DEFINES)"
#endif

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <immintrin.h>
#include <initializer_list>
#include <limits>  // IWYU pragma: keep
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <signal.h>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

#include <catch2/benchmark/catch_benchmark.hpp>
#include <catch2/benchmark/catch_chronometer.hpp>
#include <catch2/catch_template_test_macros.hpp>
#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers.hpp>
#include <catch2/matchers/catch_matchers_floating_point.hpp>
#include <spdlog/spdlog.h>

#include "assertion_signal.hpp"
#include "common/attributes.hpp"
#include "common/indexed.hpp"
#include "common/json.hpp"
#include "common/mask.hpp"
#include "common/numerics.hpp"
#include "common/types.hpp"
#include "common/util.hpp"
#include "pos/lib.hpp"
#include "system/memory.hpp"
#include "testutil.hpp"
#include "tron/emulation/attention.hpp"
#include "tron/hardware/btensor.hpp"
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/kernels/expr.hpp"
#include "tron/kernels/rope.hpp"
#include "tron/models/common.hpp"
#include "tron/models/config.hpp"
#include "tron/models/heterogeneous_kv_cache.hpp"
#include "tron/models/hw_attn_config.hpp"
#include "tron/models/kv_cache.hpp"
#include "tron/models/model.hpp"
#include "tron/models/ranged_mask.hpp"
#include "tron/plugins/llama.hpp"
#include "tron/simd.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/slice.hpp"
#include "tron/tensor/tensor.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"
#include "tron/threading.hpp"

using namespace tron;
using namespace tron::hardware;

namespace {
template <typename Book>
constexpr kv_slot_id test_kv_slot(size_t layer) {
  return Book::kv_slot(model_layer_id(layer));
}

// The AMX kernels take the cache planes as typed views (issue #4525): the
// whole native K plane for QK, the packed V plane for PV. These probes ask
// whether a candidate argument type is accepted by each kernel declaration.
template <typename K>
constexpr bool amx_qk_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_rowmajor_128x4(k, q, s, size_t{0});
};

template <typename V>
constexpr bool amx_pv_accepts = requires(V v, const float* weights, float* out) {
  amx_attn_h128g4::weights_times_v_128x4(v, weights, size_t{0}, out);
};

// The VNNI K kernel takes the packed K plane (page::k_packed) the same way.
template <typename K>
constexpr bool amx_qk_vnni_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0});
};

template <typename Page, kv_geometry geometry>
constexpr bool page_k_packed_accepts_geometry =
    requires(Page const& page) { page.template k_packed<geometry>(kv_slot_id(0), 0); };

// Packed-V contract probes. Each is a template so that an invalid body makes
// the probe false instead of a hard error.
template <typename Owner>
constexpr bool owner_views_temporary = requires { Owner{}.as_view(); };

template <typename Matrix>
constexpr bool matrix_at_writes = requires(Matrix& m) { m.at(0, 0) = bf16{}; };

template <typename Page>
constexpr bool page_k_accepts_raw_index =
    requires(Page& page) { page.k(size_t{0}, 0, 0); };

template <typename Page>
constexpr bool page_completion_accepts_operation =
    requires(Page& page) { page.is_kv_complete(attention_op_id(0), 0); };

template <typename Page>
constexpr bool page_completion_accepts_layer =
    requires(Page& page) { page.is_kv_complete(model_layer_id(0), 0); };

template <typename Book>
constexpr bool book_slot_accepts_operation =
    requires { Book::kv_slot(attention_op_id(0)); };

template <typename Book>
constexpr bool book_view_accepts_logical_slot =
    requires(Book& book) { book.set_storage_view(kv_slot_id(0)); };

template <typename Page>
constexpr bool page_supports_uniform_kv_access = requires(Page& page,
    k_row_view<Page::layout_t::primary_geometry.head_size> k_output,
    view<bf16,
        VIEW_ALIGNED_TRUE,
        VIEW_DMA_FALSE,
        seq<Page::layout_t::primary_geometry.head_size>,
        sseq<1>> output) {
  page.get_k_row(
      kv_slot_id(0), 0, 0, k_output);  // both K layouts (Note [K VNNI storage])
  page.get_v(kv_slot_id(0), 0, 0, output);
};

template <typename Page, kv_geometry geometry>
constexpr bool page_k_accepts_geometry =
    requires(Page& page) { page.template k<geometry>(kv_slot_id(0), 0, 0); };

template <typename Cache>
constexpr bool cache_maps_model_layers =
    requires { Cache::kv_slot(model_layer_id(0)); };

template <typename Page, kv_geometry geometry>
constexpr bool page_scaled_v_accepts_geometry = requires(Page const& page,
    tensor<Page::page_size> const& scales,
    tensor<geometry.head_size>& scratch) {
  page.template scaled_v<geometry>(kv_slot_id(0), 0, scales, scratch);
};

template <size_t head_size>
void check_wide_scaled_v() {
  constexpr kv_geometry geometry{1, head_size};
  using cache_t = uniform_kv_cache<1, geometry, 0>;
  cache_t cache(/*n_pages=*/1);
  constexpr size_t n_tokens = 3;
  cache.increment_tokens_used(n_tokens);
  auto* page = cache.page_of(0);
  page->set_offset_bound(n_tokens);

  alignas(64) std::array<std::array<float, geometry.head_size>, n_tokens> values{};
  for (size_t i = 0; i < geometry.head_size; ++i) {
    values[0][i] = static_cast<float>(static_cast<int>(i % 17) - 8);
    values[1][i] = static_cast<float>(static_cast<int>(i % 13) - 6);
    values[2][i] = static_cast<float>(static_cast<int>(i % 11) - 5);
  }
  for (size_t token = 0; token < n_tokens; ++token)
    page->template set_v<geometry>(kv_slot_id(0), 0, token,
        v_source_row<geometry.head_size>(values[token].data()));

  tensor<cache_t::page_size> scales = constant<cache_t::page_size>(0.0f);
  scales[0] = 0.5f;
  scales[1] = -1.0f;
  scales[2] = 0.25f;
  tensor<geometry.head_size> scratch;
  tensor<geometry.head_size> actual =
      page->template scaled_v<geometry>(kv_slot_id(0), 0, scales, scratch);
  for (size_t i = 0; i < geometry.head_size; ++i) {
    float const expected =
        values[0][i] * scales[0] + values[1][i] * scales[1] + values[2][i] * scales[2];
    REQUIRE(actual[i] == expected);
  }
}

constexpr kv_geometry geometry_64{1, 64};
constexpr kv_geometry geometry_128{2, 128};
constexpr kv_geometry geometry_256{1, 256};
constexpr auto heterogeneous_slot_specs = std::array{
    kv_slot_spec{geometry_64},
    kv_slot_spec{geometry_128},
    kv_slot_spec{geometry_256},
};
constexpr auto mixed_retention_slot_specs = std::array{
    kv_slot_spec{geometry_64, kv_slot_retention::full_history()},
    kv_slot_spec{geometry_128, kv_slot_retention::sliding_window(128)},
    kv_slot_spec{geometry_256, kv_slot_retention::sliding_window(64)},
};
constexpr auto uniform_mixed_retention_slot_specs = std::array{
    kv_slot_spec{geometry_64, kv_slot_retention::full_history()},
    kv_slot_spec{geometry_64, kv_slot_retention::sliding_window(128)},
    kv_slot_spec{geometry_64, kv_slot_retention::sliding_window(64)},
};
constexpr auto heterogeneous_attention_schedule = std::array{
    attention_binding{attention_op_id(9), model_layer_id(2), kv_slot_id(0)},
    attention_binding{attention_op_id(3), model_layer_id(0), kv_slot_id(2)},
    attention_binding{attention_op_id(12), model_layer_id(5), kv_slot_id(1)},
    attention_binding{attention_op_id(4), model_layer_id(3), kv_slot_id(2)},
};
using heterogeneous_cache = heterogeneous_kv_cache<heterogeneous_slot_specs, 0>;
using mixed_retention_cache = heterogeneous_kv_cache<mixed_retention_slot_specs, 0>;
using uniform_mixed_retention_cache =
    heterogeneous_kv_cache<uniform_mixed_retention_slot_specs, 0>;

constexpr auto eagle_slot_specs = uniform_kv_slot_specs<2>(geometry_64);
using heterogeneous_eagle_cache = heterogeneous_kv_cache<eagle_slot_specs, 16>;
using mixed_retention_eagle_cache =
    heterogeneous_kv_cache<uniform_mixed_retention_slot_specs, 16>;
using full_retention_scaled_v_cache = uniform_kv_cache<3, kv_geometry{4, 128}, 0>;
constexpr std::array scaled_v_retentions{
    kv_slot_retention::sliding_window(64),
    kv_slot_retention::full_history(),
    kv_slot_retention::sliding_window(128),
};
using mixed_retention_scaled_v_cache =
    uniform_kv_cache<3, kv_geometry{4, 128}, 0, scaled_v_retentions>;
using heterogeneous_eagle_without_embeddings =
    heterogeneous_kv_cache<eagle_slot_specs, 0>;

constexpr kv_geometry gemma4_sliding_geometry{16, 256};
constexpr kv_geometry gemma4_full_geometry{4, 512};
constexpr size_t gemma4_sliding_window = 1024;
constexpr auto gemma4_31b_slot_specs = [] {
  std::array<kv_slot_spec, 60> result{};
  for (size_t layer = 0; layer < result.size(); ++layer) {
    // This fixture uses full-history attention every sixth layer and
    // sliding-window attention elsewhere, with different KV geometries.
    bool const full_history = (layer + 1) % 6 == 0;
    result[layer] = {full_history ? gemma4_full_geometry : gemma4_sliding_geometry,
        full_history ? kv_slot_retention::full_history()
                     : kv_slot_retention::sliding_window(gemma4_sliding_window)};
  }
  return result;
}();
using gemma4_31b_cache = heterogeneous_kv_cache<gemma4_31b_slot_specs, 0>;
constexpr auto gemma4_31b_all_full_slot_specs = [] {
  std::array<kv_slot_spec, 60> result{};
  for (size_t layer = 0; layer < result.size(); ++layer)
    result[layer] = {
        (layer + 1) % 6 == 0 ? gemma4_full_geometry : gemma4_sliding_geometry};
  return result;
}();
using gemma4_31b_all_full_cache =
    heterogeneous_kv_cache<gemma4_31b_all_full_slot_specs, 0>;

struct descriptor_only_cache {
  struct page_t {};
  static constexpr auto kv_slot_specs = uniform_kv_slot_specs<2>(kv_geometry{1, 128});
  static constexpr size_t n_slots = kv_slot_specs.size();

  static constexpr size_t logical_slot_count_for_layers(size_t layers) {
    return layers;
  }

  static constexpr size_t storage_slot_count_for_layers(
      size_t layers, bool support_eagle) {
    return layers + static_cast<size_t>(support_eagle);
  }
};

struct operation_attention_config_fixture {
  inline static constexpr std::array attention_sink_specs{
      attention_sink_spec{attention_sink_id(0), 2}};

  tensor<2> sink{0.75f, -0.5f};

  std::span<const float> attention_sink(attention_sink_id id) const noexcept {
    TRON_ASSERT_EQ(id.i, 0);
    return std::span<const float>(sink.data);
  }
};

struct wrong_sink_type_fixture : operation_attention_config_fixture {
  float attention_sink(attention_sink_id) const noexcept;
};

struct throwing_sink_fixture : operation_attention_config_fixture {
  std::span<const float> attention_sink(attention_sink_id) const;
};

struct remapping_plugin_like {
  token_t remap_input_token(token_t token) const noexcept {
    return token == 17 ? 3 : token;
  }
};

struct passthrough_plugin_like {};

}  // namespace

// Regression test for the memory order of the atomic load in
// tron::log_kv_footprint (h/tron/models/kv_cache.hpp). Until e2f22c7a09 the
// load used std::memory_order_release, which the C++ standard forbids on a load
// ([atomics.types.operations]). The wrong and the right order compile to the
// same instructions with clang, so no check on program output can fail. The
// detector is libstdc++'s precondition check inside std::atomic::load, enabled
// by _GLIBCXX_ASSERTIONS on this target (t/CMakeLists.txt). log_kv_footprint is
// always-inline (TRON(inline)), so this translation unit compiles its own
// checked copy, and a wrong order aborts (SIGABRT) at the first call. If
// log_kv_footprint moves out of the header into a .cpp file, this test stops
// seeing it and must move with it.
//
// Declared first on purpose: with a wrong order, the book constructions in the
// later cases call log_kv_footprint unisolated and abort the whole process;
// this fork-isolated case reports the contract by name before that happens.
TEST_CASE("log_kv_footprint uses valid atomic memory orders", "[kv_data]") {
  // Any call runs the load under test. One byte stays below the default 1 GiB
  // print granularity, so nothing is logged.
  REQUIRE(assertion_signal([] { log_kv_footprint(1, 0); }) == 0);
}

TEST_CASE("input token remapping hook is optional", "[model][input-token-remapping]") {
  remapping_plugin_like remapping;
  passthrough_plugin_like passthrough;

  REQUIRE(apply_input_token_remapping(remapping, 17) == 3);
  REQUIRE(apply_input_token_remapping(remapping, 23) == 23);
  REQUIRE(apply_input_token_remapping(passthrough, 17) == 17);
}

TEST_CASE("attention operations resolve to typed KV slots", "[kv_data]") {
  using book_t = book<2, 1, 128, 0>;
  using page_t = book_t::page_t;

  STATIC_REQUIRE(sizeof(model_layer_id) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(attention_op_id) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(attention_plan_id) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(kv_slot_id) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(kv_storage_offset) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(attention_kernel_id) == sizeof(size_t));
  STATIC_REQUIRE(sizeof(attention_binding) == 3 * sizeof(size_t));
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, model_layer_id>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, attention_op_id>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, attention_plan_id>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, attention_kernel_id>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, kv_slot_id>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<size_t, kv_storage_offset>);
  STATIC_REQUIRE_FALSE(std::is_same_v<model_layer_id, attention_op_id>);
  STATIC_REQUIRE_FALSE(std::is_same_v<attention_op_id, attention_plan_id>);
  STATIC_REQUIRE_FALSE(std::is_same_v<attention_op_id, attention_kernel_id>);
  STATIC_REQUIRE_FALSE(std::is_same_v<attention_op_id, kv_slot_id>);
  STATIC_REQUIRE_FALSE(std::is_same_v<kv_slot_id, kv_storage_offset>);
  STATIC_REQUIRE_FALSE(page_k_accepts_raw_index<page_t>);
  STATIC_REQUIRE_FALSE(page_completion_accepts_operation<page_t>);
  STATIC_REQUIRE_FALSE(page_completion_accepts_layer<page_t>);
  STATIC_REQUIRE_FALSE(book_slot_accepts_operation<book_t>);
  STATIC_REQUIRE_FALSE(book_view_accepts_logical_slot<book_t>);

  // Cache kernel arguments identify their layout (issue #4525). QK takes the
  // whole native K plane, PV the packed V plane; neither takes a bare pointer
  // or the other layout's view, so the two planes cannot be swapped by mistake.
  using k_plane_t = const_native_k_view<amx_attn_h128g4::PAGE_TOKENS_64,
      amx_attn_h128g4::HEAD_SIZE_128>;
  using v_plane_t = v_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64,
      amx_attn_h128g4::HEAD_SIZE_128>;
  using v_plane_mut_t = v_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64,
      amx_attn_h128g4::HEAD_SIZE_128>;
  using v_owner_t =
      v_vnni_tensor<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
  STATIC_REQUIRE(amx_qk_accepts<k_plane_t>);
  STATIC_REQUIRE_FALSE(amx_qk_accepts<const bf16*>);
  STATIC_REQUIRE_FALSE(amx_qk_accepts<bf16*>);
  STATIC_REQUIRE_FALSE(amx_qk_accepts<v_plane_t>);
  STATIC_REQUIRE(amx_pv_accepts<v_plane_t>);
  STATIC_REQUIRE(amx_pv_accepts<v_plane_mut_t>);  // writable converts to read-only
  STATIC_REQUIRE_FALSE(amx_pv_accepts<const bf16*>);
  STATIC_REQUIRE_FALSE(amx_pv_accepts<bf16*>);
  STATIC_REQUIRE_FALSE(amx_pv_accepts<k_plane_t>);
  // Packed views come only from an owner; a bare pointer does not say
  // which layout it points at. The native K alias is the existing row-major
  // view and keeps its pointer constructor: it names the layout at the kernel
  // signature but does not enforce it. The packed K view below is the distinct
  // type for 128-dimension heads under TRON_K_VNNI; the native alias stays for
  // the row-major geometries.
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_mut_t, bf16*>);
  STATIC_REQUIRE_FALSE(std::is_constructible_v<v_plane_t, const bf16*>);
  STATIC_REQUIRE(std::is_constructible_v<k_plane_t, const bf16*>);
  // Writable-to-read-only is the only conversion.
  STATIC_REQUIRE(std::is_convertible_v<v_plane_mut_t, v_plane_t>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<v_plane_t, v_plane_mut_t>);
  // A view must not outlive its owner: no view of a temporary owner.
  STATIC_REQUIRE_FALSE(owner_views_temporary<v_owner_t>);
  // No view writes an element. Rows enter through append_v_row and copy_token,
  // which keep the even/odd partner rule.
  STATIC_REQUIRE_FALSE(matrix_at_writes<v_plane_mut_t>);
  // The aligned vector loads and the AMX tile rows need a 64-byte-aligned
  // plane, also for an owner that lives outside a kv_block.
  STATIC_REQUIRE(alignof(v_owner_t) == 64);

  // The packed K plane (Note [K VNNI storage]) follows the same rules. The VNNI
  // QK kernel accepts the view, and no other type, as its K argument. The other
  // two kernels reject it.
  // Views come only from an owner. A writable view converts to a read-only one
  // only.
  constexpr kv_geometry one_head{1, amx_attn_h128g4::HEAD_SIZE_128};
  using k_packed_t = k_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64,
      amx_attn_h128g4::HEAD_SIZE_128>;
  using k_packed_mut_t = k_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64,
      amx_attn_h128g4::HEAD_SIZE_128>;
  using k_owner_t =
      k_vnni_tensor<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
  STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_t>);
  STATIC_REQUIRE(
      amx_qk_vnni_accepts<k_packed_mut_t>);  // writable converts to read-only
  STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>);
  STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<bf16*>);
  STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);  // the native K view
  STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<v_plane_t>);
  STATIC_REQUIRE_FALSE(amx_qk_accepts<k_packed_t>);
  STATIC_REQUIRE_FALSE(amx_pv_accepts<k_packed_t>);
  STATIC_REQUIRE_FALSE(std::is_constructible_v<k_packed_mut_t, bf16*>);
  STATIC_REQUIRE_FALSE(std::is_constructible_v<k_packed_t, const bf16*>);
  STATIC_REQUIRE(std::is_convertible_v<k_packed_mut_t, k_packed_t>);
  STATIC_REQUIRE_FALSE(std::is_convertible_v<k_packed_t, k_packed_mut_t>);
  STATIC_REQUIRE_FALSE(owner_views_temporary<k_owner_t>);
  // No view writes an element. Rows enter through store_row, store_block and
  // copy_token.
  STATIC_REQUIRE_FALSE(matrix_at_writes<k_packed_mut_t>);
  // The 64-byte pair rows and the AMX tile rows need a 64-byte-aligned plane.
  STATIC_REQUIRE(alignof(k_owner_t) == 64);
  // The page hands out the packed view only when the build option selects the
  // packed storage for the geometry.
#ifdef TRON_K_VNNI
  STATIC_REQUIRE((page_k_packed_accepts_geometry<page_t, one_head>));
  STATIC_REQUIRE(
      std::is_same_v<decltype(std::declval<page_t const&>().template k_packed<one_head>(
                         kv_slot_id(0), 0)),
          k_vnni_view<const bf16, page_t::page_size, amx_attn_h128g4::HEAD_SIZE_128>>);
#else
  STATIC_REQUIRE_FALSE((page_k_packed_accepts_geometry<page_t, one_head>));
#endif

  constexpr attention_binding distinct_binding{
      attention_op_id(7), model_layer_id(3), kv_slot_id(1)};
  STATIC_REQUIRE(distinct_binding.operation == attention_op_id(7));
  STATIC_REQUIRE(distinct_binding.model_layer == model_layer_id(3));
  STATIC_REQUIRE(distinct_binding.kv_slot == kv_slot_id(1));
  constexpr attention_binding uniform_binding =
      uniform_attention_binding(attention_op_id(1));
  STATIC_REQUIRE(uniform_binding.operation == attention_op_id(1));
  STATIC_REQUIRE(uniform_binding.model_layer == model_layer_id(1));
  STATIC_REQUIRE(uniform_binding.kv_slot == kv_slot_id(1));

  book_t cache(1);
  page_t* page = cache.page_of(0);
  const kv_slot_id slot_0 = book_t::kv_slot(model_layer_id(0));
  const kv_slot_id slot_1 = book_t::kv_slot(model_layer_id(1));
  {
    // The two slots are distinct storage. A row stored in one is not seen in
    // the other (in the form that serves both K layouts, Note [K VNNI storage]).
    constexpr size_t head_size = 128;  // the head size of book_t
    alignas(64) std::array<bf16, head_size> ones, twos, got;
    ones.fill(static_cast<bf16>(1.0f));
    twos.fill(static_cast<bf16>(2.0f));
    page->set_k_row(slot_0, 0, 0, k_source_row<head_size>(ones.data()));
    page->set_k_row(slot_1, 0, 0, k_source_row<head_size>(twos.data()));
    page->get_k_row(slot_0, 0, 0, k_destination_row<head_size>(got.data()));
    REQUIRE(got == ones);
    page->get_k_row(slot_1, 0, 0, k_destination_row<head_size>(got.data()));
    REQUIRE(got == twos);
  }
  REQUIRE_FALSE(page->is_kv_complete(slot_1, 0));
  REQUIRE_FALSE(page->mark_k_complete(slot_1, 0));
  REQUIRE(page->mark_v_complete(slot_1, 0));
  REQUIRE(page->is_kv_complete(slot_1, 0));
}

TEST_CASE("EAGLE shifts storage without shifting logical KV completion", "[kv_data]") {
  using book_t = book<1, 1, 128, 16>;
  constexpr size_t storage_slots =
      book_t::storage_slot_count_for_layers(/*max_model_layers=*/1, true);
  book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);
  auto* page = cache.page_of(0);
  const kv_slot_id slot = book_t::kv_slot(model_layer_id(0));

  STATIC_REQUIRE(book_t::kv_slot_specs.size() == 1);
  STATIC_REQUIRE(book_t::logical_slot_count_for_layers(1) == 1);
  STATIC_REQUIRE(storage_slots == 2);
  REQUIRE(cache.storage_slot_count() == 2);
  REQUIRE(cache.eagle_storage_offset() == kv_storage_offset(1));

  constexpr size_t head_size = 128;  // the head size of book_t
  alignas(64) std::array<bf16, head_size> k_row{}, got{};
  k_row[0] = static_cast<bf16>(1.0f);
  page->set_k_row(slot, 0, 0, k_source_row<head_size>(k_row.data()));
  REQUIRE_FALSE(page->mark_k_complete(slot, 0));
  REQUIRE(page->mark_v_complete(slot, 0));

  cache.set_storage_view(cache.eagle_storage_offset());
  REQUIRE(page->is_kv_complete(slot, 0));
  k_row[0] = static_cast<bf16>(2.0f);
  page->set_k_row(slot, 0, 0, k_source_row<head_size>(k_row.data()));

  cache.reset_storage_view();
  page->get_k_row(slot, 0, 0, k_destination_row<head_size>(got.data()));
  REQUIRE(float(got[0]) == 1.0f);
  REQUIRE(page->is_kv_complete(slot, 0));

  cache.set_storage_view(cache.eagle_storage_offset());
  page->get_k_row(slot, 0, 0, k_destination_row<head_size>(got.data()));
  REQUIRE(float(got[0]) == 2.0f);
  REQUIRE(page->is_kv_complete(slot, 0));
}

TEST_CASE("HW attention completion tracks operation generations", "[attention]") {
  STATIC_REQUIRE(hw_attention_completion_generation(attention_op_id(0)) == 1);
  STATIC_REQUIRE(hw_attention_completion_generation(attention_op_id(1)) == 2);

  hw_workload workload;
  workload.resize(2);
  for (auto const& completed : workload.complete)
    REQUIRE(completed.load(std::memory_order_relaxed) == 0);

  for (auto& completed : workload.complete)
    completed.store(hw_attention_completion_generation(attention_op_id(0)),
        std::memory_order_relaxed);

  for (auto const& completed : workload.complete)
    REQUIRE(completed.load(std::memory_order_relaxed) < 2);

  for (auto& completed : workload.complete)
    completed.store(hw_attention_completion_generation(attention_op_id(1)),
        std::memory_order_relaxed);

  for (auto const& completed : workload.complete)
    REQUIRE(completed.load(std::memory_order_relaxed) >= 2);
}

// See Note [Early and late hardware attention launch] in model.hpp.
TEST_CASE("HW attention launch phase switches at the batch threshold", "[attention]") {
  constexpr size_t min_early_batch = 4;

  STATIC_REQUIRE(select_hw_attention_launch_phase(min_early_batch - 1,
                     min_early_batch) == hw_attention_launch_phase::late);
  STATIC_REQUIRE(select_hw_attention_launch_phase(min_early_batch, min_early_batch) ==
                 hw_attention_launch_phase::early);
  STATIC_REQUIRE(select_hw_attention_launch_phase(min_early_batch + 1,
                     min_early_batch) == hw_attention_launch_phase::early);
}

TEST_CASE("uniform plugin cache declares value slot topology", "[kv_data]") {
  constexpr kv_geometry geometry{4, 128};
  constexpr auto slot_specs = uniform_kv_slot_specs<3>(geometry);
  constexpr std::array invalid_slot_specs{
      kv_slot_spec{kv_geometry{1, 65}},
  };
  constexpr std::array<kv_slot_spec, 0> empty_slot_specs{};
  using cache_t = uniform_kv_cache<3, geometry, 16>;
  constexpr std::array all_sliding_retentions{
      kv_slot_retention::sliding_window(64),
      kv_slot_retention::sliding_window(128),
      kv_slot_retention::sliding_window(64),
  };
  using all_sliding_cache_t = uniform_kv_cache<3, geometry, 16, all_sliding_retentions>;
  constexpr std::array prefix_retentions{
      kv_slot_retention::full_history(),
      kv_slot_retention::sliding_window(64),
      kv_slot_retention::sliding_window(128),
  };
  using prefix_retention_cache_t = uniform_kv_cache<3, geometry, 16, prefix_retentions>;

  STATIC_REQUIRE(valid_kv_slot_specs(slot_specs));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(invalid_slot_specs));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(empty_slot_specs));
  STATIC_REQUIRE(sequence_cache_topology<cache_t>);
  STATIC_REQUIRE(sequence_cache_behavior<cache_t>);
  STATIC_REQUIRE(sequence_cache<cache_t>);
  STATIC_REQUIRE(cache_maps_model_layers<cache_t>);
  STATIC_REQUIRE(cache_t::n_slots == 3);
  STATIC_REQUIRE(cache_t::layout_t::uniform_reclaimability);
  STATIC_REQUIRE(all_sliding_cache_t::layout_t::uniform_reclaimability);
  STATIC_REQUIRE(cache_t::kv_slot_specs == slot_specs);
  STATIC_REQUIRE(cache_t::logical_slot_count_for_layers(2) == 2);
  STATIC_REQUIRE(cache_t::storage_slot_count_for_layers(2, false) == 2);
  STATIC_REQUIRE(cache_t::storage_slot_count_for_layers(2, true) == 3);
  STATIC_REQUIRE(cache_t::storage_slot_count_for_layers(3, true) == 4);
  STATIC_REQUIRE(prefix_retention_cache_t::max_reclaimable_window_size(1) == 0);
  STATIC_REQUIRE(prefix_retention_cache_t::max_reclaimable_window_size(2) == 64);
  STATIC_REQUIRE(prefix_retention_cache_t::max_reclaimable_window_size(3) == 128);
  STATIC_REQUIRE(prefix_retention_cache_t::max_reclaimable_window_size() == 128);
  STATIC_REQUIRE(std::is_same_v<cache_t, book<3, 4, 128, 16>>);
  STATIC_REQUIRE(cache_maps_model_layers<cache_t>);

  STATIC_REQUIRE(sequence_cache_topology<descriptor_only_cache>);
  STATIC_REQUIRE_FALSE(sequence_cache_behavior<descriptor_only_cache>);
  STATIC_REQUIRE_FALSE(sequence_cache<descriptor_only_cache>);

  using empty_cache_t = uniform_kv_cache<0, kv_geometry{1, 64}, 0>;
  STATIC_REQUIRE(empty_cache_t::layout_t::uniform_geometry);
  STATIC_REQUIRE((empty_cache_t::layout_t::primary_geometry == kv_geometry{1, 64}));
  STATIC_REQUIRE(page_supports_uniform_kv_access<empty_cache_t::page_t>);
}

TEST_CASE("KV slot retention aggregates every operation consumer", "[kv_data]") {
  constexpr attention_geometry geometry{2, geometry_64};
  constexpr std::array kernels{attention_kernel_spec{attention_kernel_id(0), geometry}};
  constexpr std::array sliding_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(0), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, true,
          attention_operation_config{64, std::nullopt, 0.125f}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(1), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, false,
          attention_operation_config{128, std::nullopt, 0.125f}},
  };
  constexpr std::array widest_window_slot{
      kv_slot_spec{geometry_64, kv_slot_retention::sliding_window(128)}};
  constexpr std::array narrow_window_slot{
      kv_slot_spec{geometry_64, kv_slot_retention::sliding_window(64)}};
  constexpr std::array full_history_operations{
      sliding_operations[0],
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(1), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, false,
          attention_operation_config{std::nullopt, std::nullopt, 0.125f}},
  };
  constexpr std::array full_history_slot{
      kv_slot_spec{geometry_64, kv_slot_retention::full_history()}};
  constexpr std::array invalid_full_slot{kv_slot_spec{
      geometry_64, kv_slot_retention{kv_slot_retention_kind::full_history, 1}}};
  constexpr std::array invalid_window_slot{
      kv_slot_spec{geometry_64, kv_slot_retention::sliding_window(0)}};

  STATIC_REQUIRE(valid_attention_operation_descriptors(kernels, sliding_operations));
  STATIC_REQUIRE(valid_kv_slot_retentions(sliding_operations, widest_window_slot));
  STATIC_REQUIRE_FALSE(
      valid_kv_slot_retentions(sliding_operations, narrow_window_slot));
  STATIC_REQUIRE(valid_kv_slot_retentions(full_history_operations, full_history_slot));
  STATIC_REQUIRE_FALSE(
      valid_kv_slot_retentions(full_history_operations, widest_window_slot));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(invalid_full_slot));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(invalid_window_slot));
}

TEST_CASE("mixed-retention books release and restore one grouped arena",
    "[kv_data][try_create][fault_seam]") {
  struct reset_dma_test_seams final {
    ~reset_dma_test_seams() noexcept {
      test_seam::clear_dma_fault();
      test_seam::clear_dma_allocation_limit();
    }
  } reset_dma_test_seams;
  using cache_t = mixed_retention_cache;
  constexpr size_t pages = 2;
  constexpr size_t retained_bytes_per_page = 2 * cache_t::page_size * sizeof(bf16) *
                                             geometry_64.n_kv_heads *
                                             geometry_64.head_size;
  constexpr size_t reclaimable_bytes_per_page =
      2 * cache_t::page_size * sizeof(bf16) *
      (geometry_128.n_kv_heads * geometry_128.head_size +
          geometry_256.n_kv_heads * geometry_256.head_size);

  STATIC_REQUIRE_FALSE(cache_t::layout_t::uniform_geometry);
  STATIC_REQUIRE_FALSE(cache_t::layout_t::uniform_reclaimability);

  test_seam::clear_dma_fault();
  test_seam::clear_dma_allocation_limit();
  auto cache = cache_t::try_create(pages);
  REQUIRE(cache != nullptr);
  REQUIRE(cache->dma_size_bytes() ==
          static_cast<int64_t>(
              pages * (retained_bytes_per_page + reclaimable_bytes_per_page)));
  REQUIRE(cache_t::max_reclaimable_window_size() == 128);

  auto* page = cache->page_of(0);
  page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] = static_cast<bf16>(7.0f);
  // The 128-dimension slot goes through the layout-agnostic accessors: with
  // TRON_K_VNNI it has no row view (Note [K VNNI storage]).
  alignas(64) std::array<bf16, geometry_128.head_size> k_row{};
  k_row[0] = static_cast<bf16>(9.0f);
  page->template set_k_row<geometry_128>(
      kv_slot_id(1), 0, 0, k_source_row<geometry_128.head_size>(k_row.data()));
  page->template k<geometry_256>(kv_slot_id(2), 0, 0)[0] = static_cast<bf16>(10.0f);

  int64_t const released = cache->free_reclaimable_kv_storage();
  REQUIRE(released == static_cast<int64_t>(pages * reclaimable_bytes_per_page));
  REQUIRE(cache->has_reclaimed_kv_storage());
  REQUIRE(
      cache->dma_size_bytes() == static_cast<int64_t>(pages * retained_bytes_per_page));
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 7.0f);
  REQUIRE(cache->free_reclaimable_kv_storage() == 0);

  test_seam::arm_dma_fault(0);
  REQUIRE_FALSE(cache->restore_reclaimable_kv_storage(1).has_value());
  REQUIRE(cache->has_reclaimed_kv_storage());
  REQUIRE(
      cache->dma_size_bytes() == static_cast<int64_t>(pages * retained_bytes_per_page));

  test_seam::clear_dma_fault();
  REQUIRE(cache->restore_reclaimable_kv_storage(2) == released);
  REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
  REQUIRE(assertion_signal([&] {
    k_row[0] = static_cast<bf16>(11.0f);
    page->template set_k_row<geometry_128>(
        kv_slot_id(1), 0, 0, k_source_row<geometry_128.head_size>(k_row.data()));
  }) == SIGABRT);
  cache->finish_reclaimable_kv_restore(2);
  k_row[0] = static_cast<bf16>(11.0f);
  page->template set_k_row<geometry_128>(
      kv_slot_id(1), 0, 0, k_source_row<geometry_128.head_size>(k_row.data()));
  page->template k<geometry_256>(kv_slot_id(2), 0, 0)[0] = static_cast<bf16>(12.0f);
  page->template get_k_row<geometry_128>(
      kv_slot_id(1), 0, 0, k_destination_row<geometry_128.head_size>(k_row.data()));
  REQUIRE(float(k_row[0]) == 11.0f);
  REQUIRE(float(page->template k<geometry_256>(kv_slot_id(2), 0, 0)[0]) == 12.0f);

  size_t const separate_group_cap =
      pages * std::max(retained_bytes_per_page, reclaimable_bytes_per_page);
  REQUIRE(cache_t::max_pages_for_dma_allocation(separate_group_cap) == pages);
  REQUIRE(cache_t::max_pages_for_dma_allocation(reclaimable_bytes_per_page - 1) == 0);

  cache.reset();
  test_seam::set_dma_allocation_limit(separate_group_cap);
  REQUIRE(cache_t::try_create(pages) != nullptr);
  test_seam::set_dma_allocation_limit(reclaimable_bytes_per_page - 1);
  REQUIRE(cache_t::try_create(1) == nullptr);
  test_seam::clear_dma_allocation_limit();
}

TEST_CASE("Sliding KV chunks reserve and restore transactionally",
    "[kv_data][try_create][fault_seam]") {
  using cache_t = mixed_retention_cache;
  constexpr size_t pages = 7;
  constexpr size_t chunk_tokens = 2 * cache_t::page_size;
  constexpr size_t retained_bytes = pages * 2 * cache_t::page_size * sizeof(bf16) *
                                    geometry_64.n_kv_heads * geometry_64.head_size;
  constexpr size_t chunk_bytes = 2 * chunk_tokens * sizeof(bf16) *
                                 (geometry_128.n_kv_heads * geometry_128.head_size +
                                     geometry_256.n_kv_heads * geometry_256.head_size);
  finally reset_dma_test_seams([] {
    test_seam::clear_dma_fault();
    test_seam::clear_dma_allocation_limit();
  });
  test_seam::clear_dma_fault();
  // A small allocator cap exercises multiple physical chunks without allocating
  // model-sized KV. Full-history storage for this book still fits in one arena.
  test_seam::set_dma_allocation_limit(chunk_bytes);
  int64_t const baseline = pos_heap_active_allocations();
  auto cache = cache_t::try_create_lazy(pages);
  REQUIRE(cache != nullptr);
  REQUIRE(cache->dma_size_bytes() == retained_bytes);
  REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
  REQUIRE(cache->reserve_token_range(0, chunk_tokens) == chunk_bytes);
  cache->increment_tokens_used(chunk_tokens);

  // Probe both ends of each chunk, both sliding geometries, every head, and
  // both K/V planes. Neighboring chunks must retain their data across release,
  // rollback, and restoration even when their page objects were already saved.
  auto* first_page = cache->page_of(0);
  auto visit = [&]<size_t slot>(size_t first_token, size_t end_token, bool write) {
    constexpr auto geometry = cache_t::kv_slot_specs[slot].geometry;
    for (size_t token : {first_token, end_token - 1}) {
      auto* page = cache->page_of(token);
      size_t const row = token % cache_t::page_size;
      for (size_t head = 0; head < geometry.n_kv_heads; ++head) {
        float const value =
            static_cast<float>(1 + slot * 16 + head * 4 + token / chunk_tokens);
        alignas(64) std::array<bf16, geometry.head_size> values;
        values.fill(static_cast<bf16>(value));
        // set_k_row / get_k_row serve both K layouts (Note [K VNNI storage]).
        if (write) {
          page->template set_k_row<geometry>(kv_slot_id(slot), head, row,
              k_source_row<geometry.head_size>(values.data()));
          if (row % 2 != 0)
            page->template set_v<geometry>(kv_slot_id(slot), head, row - 1,
                v_source_row<geometry.head_size>(values.data()));
          page->template set_v<geometry>(kv_slot_id(slot), head, row,
              v_source_row<geometry.head_size>(values.data()));
        } else {
          alignas(64) std::array<bf16, geometry.head_size> k_row;
          page->template get_k_row<geometry>(kv_slot_id(slot), head, row,
              k_destination_row<geometry.head_size>(k_row.data()));
          for (bf16 element : k_row)
            REQUIRE(float(element) == value);
          page->template get_v<geometry>(kv_slot_id(slot), head, row,
              v_destination_row<geometry.head_size>(values.data()));
          for (bf16 element : values)
            REQUIRE(float(element) == value);
        }
      }
    }
  };
  auto visit_chunk = [&](size_t chunk, bool write) {
    size_t const begin = chunk * chunk_tokens;
    size_t const end = std::min(begin + chunk_tokens, cache->token_capacity());
    visit.template operator()<0>(begin, end, write);
    visit.template operator()<1>(begin, end, write);
    visit.template operator()<2>(begin, end, write);
  };
  visit_chunk(0, true);

  SECTION("A failed append releases new reservations and preserves the prefix") {
    int64_t const bytes_before = cache->dma_size_bytes();
    int64_t const allocations_before = pos_heap_active_allocations();
    // The first new chunk succeeds; the second must undo only this reservation.
    test_seam::arm_dma_fault(1);
    REQUIRE_FALSE(cache->reserve_token_range(chunk_tokens, 3 * chunk_tokens));
    REQUIRE(cache->dma_size_bytes() == bytes_before);
    REQUIRE(pos_heap_active_allocations() == allocations_before);
    REQUIRE(cache->size() == chunk_tokens);
    REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
    visit_chunk(0, false);

    REQUIRE(
        cache->reserve_token_range(chunk_tokens, 3 * chunk_tokens) == 2 * chunk_bytes);
    cache->increment_tokens_used(2 * chunk_tokens);
    visit_chunk(1, true);
    visit_chunk(2, true);
    for (size_t chunk = 0; chunk < 3; ++chunk)
      visit_chunk(chunk, false);
    REQUIRE(cache->page_of(0) == first_page);
  }

  SECTION("Restoring missing chunks preserves neighbors and the unallocated tail") {
    REQUIRE(
        cache->reserve_token_range(chunk_tokens, 3 * chunk_tokens) == 2 * chunk_bytes);
    cache->increment_tokens_used(2 * chunk_tokens);
    visit_chunk(1, true);
    visit_chunk(2, true);
    REQUIRE(cache->free_reclaimable_kv_chunk(0) == chunk_bytes);
    REQUIRE(cache->free_reclaimable_kv_chunk(1) == chunk_bytes);
    REQUIRE(cache->has_reclaimed_kv_storage());
    int64_t const bytes_before = cache->dma_size_bytes();
    int64_t const allocations_before = pos_heap_active_allocations();
    REQUIRE(bytes_before == retained_bytes + chunk_bytes);
    visit.template operator()<0>(0, 3 * chunk_tokens, false);
    visit_chunk(2, false);

    // Ordinary append reservation must not make historical ready tokens refer
    // to fresh, uninitialized storage; only the replay transaction may do that.
    REQUIRE_FALSE(cache->reserve_token_range(0, 1));
    REQUIRE(cache->dma_size_bytes() == bytes_before);

    test_seam::arm_dma_fault(1);
    REQUIRE_FALSE(cache->restore_reclaimable_kv_storage(1));
    REQUIRE(cache->dma_size_bytes() == bytes_before);
    REQUIRE(pos_heap_active_allocations() == allocations_before);
    REQUIRE(cache->has_reclaimed_kv_storage());
    visit_chunk(2, false);

    REQUIRE(cache->restore_reclaimable_kv_storage(2) == 2 * chunk_bytes);
    cache->abort_reclaimable_kv_restore(2);
    REQUIRE(cache->dma_size_bytes() == bytes_before);
    REQUIRE(pos_heap_active_allocations() == allocations_before);
    REQUIRE(cache->has_reclaimed_kv_storage());
    visit_chunk(2, false);

    REQUIRE(cache->restore_reclaimable_kv_storage(3) == 2 * chunk_bytes);
    cache->finish_reclaimable_kv_restore(3);
    REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
    REQUIRE(cache->dma_size_bytes() == retained_bytes + 3 * chunk_bytes);
    visit.template operator()<0>(0, 3 * chunk_tokens, false);
    visit_chunk(2, false);
    visit_chunk(0, true);
    visit_chunk(1, true);
    for (size_t chunk = 0; chunk < 3; ++chunk)
      visit_chunk(chunk, false);
    REQUIRE(cache->page_of(0) == first_page);

    // Restoration does not preallocate the untouched last chunk. It is still
    // fallible when the first novel token eventually needs that storage.
    test_seam::arm_dma_fault(0);
    REQUIRE_FALSE(cache->reserve_token_range(3 * chunk_tokens, 3 * chunk_tokens + 1));
    REQUIRE(cache->size() == 3 * chunk_tokens);
    REQUIRE(cache->dma_size_bytes() == retained_bytes + 3 * chunk_bytes);
    REQUIRE(cache->reserve_token_range(3 * chunk_tokens, 3 * chunk_tokens + 1) ==
            chunk_bytes / 2);
    visit_chunk(3, true);
    visit_chunk(3, false);
  }

  SECTION("A replay can reserve a novel suffix before publishing restored KV") {
    REQUIRE(cache->reserve_token_range(chunk_tokens, 2 * chunk_tokens) == chunk_bytes);
    cache->increment_tokens_used(chunk_tokens);
    visit_chunk(1, true);
    REQUIRE(cache->free_reclaimable_kv_chunk(0) == chunk_bytes);
    REQUIRE(cache->restore_reclaimable_kv_storage(1) == chunk_bytes);

    // A request may reuse restored history and append novel tokens in the same
    // book before replay is committed. Aborting that replay must release only
    // its restored history, preserving the existing neighbor and new reserve.
    REQUIRE(cache->reserve_token_range(0, 3 * chunk_tokens) == chunk_bytes);
    REQUIRE(cache->abort_reclaimable_kv_restore(1) == chunk_bytes);
    REQUIRE(cache->has_reclaimed_kv_storage());
    REQUIRE(cache->dma_size_bytes() == retained_bytes + 2 * chunk_bytes);
    visit_chunk(1, false);
    REQUIRE(cache->reserve_token_range(2 * chunk_tokens, 3 * chunk_tokens) == 0);
    visit_chunk(2, true);
    visit_chunk(2, false);

    REQUIRE(cache->restore_reclaimable_kv_storage(2) == chunk_bytes);
    cache->finish_reclaimable_kv_restore(2);
    visit_chunk(1, false);
    visit_chunk(2, false);
  }

  SECTION("Truncating reclaimed history permits fresh append without replay") {
    REQUIRE(
        cache->reserve_token_range(chunk_tokens, 3 * chunk_tokens) == 2 * chunk_bytes);
    cache->increment_tokens_used(2 * chunk_tokens);
    visit_chunk(1, true);
    REQUIRE(cache->free_reclaimable_kv_chunk(2) == chunk_bytes);

    // One surviving historical token still requires replay. Only after the
    // entire missing range leaves the tree may an ordinary append reuse it.
    cache->decrement_tokens_used(chunk_tokens - 1);
    REQUIRE_FALSE(cache->reserve_token_range(2 * chunk_tokens, 2 * chunk_tokens + 1));
    cache->decrement_tokens_used(1);
    REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
    REQUIRE(cache->reserve_token_range(2 * chunk_tokens, 2 * chunk_tokens + 1) ==
            chunk_bytes);
    cache->increment_tokens_used();
    visit_chunk(0, false);
    visit_chunk(1, false);
    visit_chunk(2, true);
    visit_chunk(2, false);
  }

  SECTION("Releasing an unused suffix permits fresh append without replay") {
    int64_t const allocations_before = pos_heap_active_allocations();
    REQUIRE(cache->reserve_token_range(chunk_tokens, 2 * chunk_tokens) == chunk_bytes);
    cache->increment_tokens_used(chunk_tokens);
    visit_chunk(1, true);

    // Evicting a continuation can leave its allocation resident after its
    // tokens are removed. Releasing that capacity must not create missing
    // historical KV that an ordinary novel append would have to restore.
    cache->decrement_tokens_used(chunk_tokens);
    REQUIRE(cache->free_reclaimable_kv_chunk(1) == chunk_bytes);
    REQUIRE_FALSE(cache->has_reclaimed_kv_storage());
    REQUIRE(cache->dma_size_bytes() == retained_bytes + chunk_bytes);
    REQUIRE(pos_heap_active_allocations() == allocations_before);
    visit_chunk(0, false);

    REQUIRE(cache->reserve_token_range(chunk_tokens, 2 * chunk_tokens) == chunk_bytes);
    cache->increment_tokens_used(chunk_tokens);
    REQUIRE(cache->dma_size_bytes() == retained_bytes + 2 * chunk_bytes);
    visit_chunk(1, true);
    visit_chunk(1, false);
    visit_chunk(0, false);
  }

  SECTION("Aborting replay after eviction does not restore the discarded tail") {
    REQUIRE(
        cache->reserve_token_range(chunk_tokens, 3 * chunk_tokens) == 2 * chunk_bytes);
    cache->increment_tokens_used(2 * chunk_tokens);
    visit_chunk(1, true);
    REQUIRE(cache->free_reclaimable_kv_chunk(0) == chunk_bytes);
    REQUIRE(cache->free_reclaimable_kv_chunk(2) == chunk_bytes);
    REQUIRE(cache->restore_reclaimable_kv_storage(1) == 2 * chunk_bytes);

    // A failed cache-growth retry may evict an inactive continuation while
    // keeping the matched prefix pinned. The next replay needs only history
    // that survived that eviction, even though the aborted attempt owned both.
    cache->decrement_tokens_used(chunk_tokens);
    REQUIRE(cache->abort_reclaimable_kv_restore(1) == 2 * chunk_bytes);
    REQUIRE(cache->restore_reclaimable_kv_storage(2) == chunk_bytes);
    cache->finish_reclaimable_kv_restore(2);
    REQUIRE(cache->dma_size_bytes() == retained_bytes + 2 * chunk_bytes);
    visit_chunk(1, false);
    REQUIRE(cache->reserve_token_range(2 * chunk_tokens, 2 * chunk_tokens + 1) ==
            chunk_bytes);
  }
  cache.reset();
  REQUIRE(pos_heap_active_allocations() == baseline);
}

TEST_CASE(
    "uniform-geometry mixed retention addresses both arenas", "[kv_data][try_create]") {
  using cache_t = uniform_mixed_retention_cache;
  auto cache = cache_t::try_create(/*n_pages=*/1);
  REQUIRE(cache != nullptr);
  auto* page = cache->page_of(0);

  page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] = static_cast<bf16>(1.0f);
  page->template k<geometry_64>(kv_slot_id(1), 0, 0)[0] = static_cast<bf16>(2.0f);
  page->template k<geometry_64>(kv_slot_id(2), 0, 0)[0] = static_cast<bf16>(3.0f);

  REQUIRE(cache->free_reclaimable_kv_storage() > 0);
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 1.0f);
  REQUIRE(cache->restore_reclaimable_kv_storage(1).has_value());
  cache->finish_reclaimable_kv_restore(1);

  page->template k<geometry_64>(kv_slot_id(1), 0, 0)[0] = static_cast<bf16>(4.0f);
  page->template k<geometry_64>(kv_slot_id(2), 0, 0)[0] = static_cast<bf16>(5.0f);
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(1), 0, 0)[0]) == 4.0f);
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(2), 0, 0)[0]) == 5.0f);
}

TEST_CASE("interleaved retention packs truncated slots and EAGLE independently",
    "[kv_data][try_create][eagle]") {
  constexpr kv_geometry geometry{2, 64};
  constexpr std::array retentions{
      kv_slot_retention::sliding_window(64),
      kv_slot_retention::full_history(),
      kv_slot_retention::sliding_window(128),
      kv_slot_retention::full_history(),
  };
  using cache_t = uniform_kv_cache<4, geometry, 16, retentions>;
  size_t const layers = GENERATE(size_t{1}, size_t{2}, size_t{3}, size_t{4});
  size_t const pages = GENERATE(size_t{1}, size_t{3});
  size_t const storage_slots = cache_t::storage_slot_count_for_layers(layers, true);
  size_t const slot_bytes = pages * 2 * cache_t::page_size * geometry.n_kv_heads *
                            geometry.head_size * sizeof(bf16);
  size_t const x_bytes = pages * cache_t::page_size * 16;
  size_t const sliding_slots = (layers + 1) / 2;
  size_t const retained_slots = layers / 2 + 1;
  size_t const arena_cap = slot_bytes * std::max(sliding_slots, retained_slots);
  REQUIRE(
      cache_t::max_pages_for_dma_allocation(arena_cap, storage_slots, true) == pages);

  auto cache = cache_t::try_create(pages, storage_slots, true);
  REQUIRE(cache != nullptr);
  REQUIRE(cache->logical_slot_count() == layers);
  REQUIRE(cache->dma_size_bytes() ==
          static_cast<int64_t>((layers + 1) * slot_bytes + x_bytes));
  auto visit_slot = [&](size_t slot, auto&& visit) {
    if (slot == layers) cache->set_storage_view(cache->eagle_storage_offset());
    kv_slot_id const logical_slot(slot == layers ? 0 : slot);
    for (size_t pg = 0; pg < pages; ++pg) {
      auto* page = cache->page_of(pg * cache_t::page_size);
      for (size_t head = 0; head < geometry.n_kv_heads; ++head) {
        for (size_t token : {size_t{0}, cache_t::page_size - 1}) {
          auto& k = page->template k<geometry>(logical_slot, head, token)[0];
          visit(k, static_cast<float>(32 * slot + 4 * pg + 2 * head + (token != 0)));
        }
      }
    }
    cache->reset_storage_view();
  };
  for (size_t slot = 0; slot <= layers; ++slot)
    visit_slot(slot, [](bf16& k, float expected) { k = static_cast<bf16>(expected); });
  for (size_t slot = 0; slot <= layers; ++slot)
    visit_slot(slot, [](bf16& k, float expected) { REQUIRE(float(k) == expected); });

  auto const released = static_cast<int64_t>(sliding_slots * slot_bytes);
  REQUIRE(cache->free_reclaimable_kv_storage() == released);
  REQUIRE(cache->dma_size_bytes() ==
          static_cast<int64_t>(retained_slots * slot_bytes + x_bytes));
  for (size_t slot = 0; slot <= layers; ++slot)
    if (slot == layers || !retentions[slot].reclaimable())
      visit_slot(slot, [](bf16& k, float expected) { REQUIRE(float(k) == expected); });

  REQUIRE(cache->restore_reclaimable_kv_storage(1) == released);
  cache->finish_reclaimable_kv_restore(1);
  for (size_t slot = 0; slot < layers; ++slot)
    if (retentions[slot].reclaimable())
      visit_slot(
          slot, [](bf16& k, float expected) { k = static_cast<bf16>(expected); });
  for (size_t slot = 0; slot <= layers; ++slot)
    visit_slot(slot, [](bf16& k, float expected) { REQUIRE(float(k) == expected); });
}

TEMPLATE_TEST_CASE("page K views preserve geometry and row addressing",
    "[kv_data]",
    (book<3, 1, 64, 0>),
    uniform_mixed_retention_cache,
    heterogeneous_cache,
    mixed_retention_cache) {
  using cache_t = TestType;
  cache_t cache(2);
  auto check_slot = [&]<size_t slot>() {
    constexpr auto geometry = cache_t::kv_slot_specs[slot].geometry;
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      // A VNNI slot (Note [K VNNI storage]) has no row view. Its
      // layout-agnostic accessors are covered by t_k_vnni_layout.
      STATIC_REQUIRE_FALSE(
          (page_k_accepts_geometry<typename cache_t::page_t, geometry>));
    } else {
      for (size_t pg = 0; pg < 2; ++pg) {
        auto* page = cache.page_of(pg * cache_t::page_size);
        for (size_t head = 0; head < geometry.n_kv_heads; ++head) {
          auto rows = page->template k<geometry>(kv_slot_id(slot), head);
          auto const_rows =
              std::as_const(*page).template k<geometry>(kv_slot_id(slot), head);
          STATIC_REQUIRE(std::is_same_v<typename decltype(rows)::dim,
              seq<cache_t::page_size, geometry.head_size>>);
          decltype(const_rows) lazy_rows;
          REQUIRE_FALSE(lazy_rows.valid());
          lazy_rows = const_rows;
          REQUIRE(lazy_rows.valid());
          if constexpr (cache_t::layout_t::uniform_geometry) {
            REQUIRE(page->k(kv_slot_id(slot), head).data == rows.data);
            REQUIRE(std::as_const(*page).k(kv_slot_id(slot), head).data == rows.data);
          }
          for (size_t row : {size_t{0}, cache_t::page_size - 1}) {
            REQUIRE(rows[row].data ==
                    page->template k<geometry>(kv_slot_id(slot), head, row).data);
            for (size_t element : {size_t{0}, geometry.head_size - 1}) {
              auto const value =
                  static_cast<bf16>(slot * 20 + head * 4 + pg * 2 + row + element + 1);
              rows[row][element] = value;
              REQUIRE(float(lazy_rows[row][element]) == float(value));
            }
          }
        }
      }
    }
  };
  check_slot.template operator()<0>();
  check_slot.template operator()<1>();
  check_slot.template operator()<2>();
}

TEST_CASE("all-sliding caches retain the EAGLE storage view",
    "[kv_data][try_create][eagle]") {
  constexpr std::array retentions{
      kv_slot_retention::sliding_window(64),
      kv_slot_retention::sliding_window(64),
  };
  using cache_t = uniform_kv_cache<2, geometry_64, 16, retentions>;
  constexpr size_t storage_slots =
      cache_t::storage_slot_count_for_layers(2, /*support_eagle=*/true);
  auto cache = cache_t::try_create(
      /*n_pages=*/1, storage_slots, /*support_eagle=*/true);
  REQUIRE(cache != nullptr);
  auto* page = cache->page_of(0);

  cache->set_storage_view(cache->eagle_storage_offset());
  page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] = static_cast<bf16>(6.0f);
  cache->reset_storage_view();
  REQUIRE(cache->free_reclaimable_kv_storage() > 0);
  cache->set_storage_view(cache->eagle_storage_offset());
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 6.0f);
  cache->reset_storage_view();

  REQUIRE(cache->restore_reclaimable_kv_storage(1).has_value());
  cache->finish_reclaimable_kv_restore(1);
  cache->set_storage_view(cache->eagle_storage_offset());
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 6.0f);
  cache->reset_storage_view();
}

TEST_CASE("fixed KV layout addresses each slot geometry", "[kv_data][book append]") {
  constexpr kv_geometry geometry_64{1, 64};
  constexpr kv_geometry geometry_128{2, 128};
  constexpr kv_geometry undeclared_geometry{3, 64};
  constexpr auto slot_specs =
      std::array{kv_slot_spec{geometry_64}, kv_slot_spec{geometry_128}};
  using layout_t = detail::fixed_kv_layout<slot_specs, geometry_64>;
  using cache_t = book<layout_t::n_slots, layout_t::primary_geometry.n_kv_heads,
      layout_t::primary_geometry.head_size, 0, layout_t>;
  using page_t = cache_t::page_t;

  STATIC_REQUIRE(sequence_cache<cache_t>);
  STATIC_REQUIRE_FALSE(cache_maps_model_layers<cache_t>);
  STATIC_REQUIRE(cache_t::logical_slot_count_for_layers(99) == 2);
  STATIC_REQUIRE(cache_t::storage_slot_count_for_layers(99, false) == 2);
  STATIC_REQUIRE((page_k_accepts_geometry<page_t, geometry_64>));
#ifdef TRON_K_VNNI
  // 128-dimension heads are stored as the VNNI (Vector Neural Network Instructions)
  // plane. That plane has no contiguous row view (Note [K VNNI storage]).
  // set_k_row / get_k_row serve the slot.
  STATIC_REQUIRE_FALSE((page_k_accepts_geometry<page_t, geometry_128>));
#else
  STATIC_REQUIRE((page_k_accepts_geometry<page_t, geometry_128>));
#endif
  STATIC_REQUIRE_FALSE((page_k_accepts_geometry<page_t, undeclared_geometry>));
  STATIC_REQUIRE_FALSE(page_supports_uniform_kv_access<page_t>);

  cache_t destination(/*n_pages=*/2);
  cache_t source(/*n_pages=*/2);
  std::mt19937 gen(42);
  destination.fill_random(gen);
  source.fill_random(gen);
  constexpr size_t target_token = cache_t::page_size;
  source.increment_tokens_used(target_token + 1);
  page_t* source_page = source.page_of(target_token);
  source_page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] =
      static_cast<bf16>(11.0f);
  alignas(64) std::array<bf16, geometry_128.head_size> source_k{};
  source_k[0] = static_cast<bf16>(22.0f);
  source_page->template set_k_row<geometry_128>(
      kv_slot_id(1), 1, 0, k_source_row<geometry_128.head_size>(source_k.data()));
  alignas(64) std::array<bf16, geometry_128.head_size> source_v;
  source_v.fill(static_cast<bf16>(33.0f));
  source_page->template set_v<geometry_128>(
      kv_slot_id(1), 1, 0, v_source_row<geometry_128.head_size>(source_v.data()));
  REQUIRE_FALSE(source_page->mark_k_complete(kv_slot_id(1), 0));
  REQUIRE(source_page->mark_v_complete(kv_slot_id(1), 0));

  constexpr size_t bytes_per_page =
      detail::KV_BLOCK_PLANES_2 * cache_t::page_size * sizeof(bf16) *
      (geometry_64.n_kv_heads * geometry_64.head_size +
          geometry_128.n_kv_heads * geometry_128.head_size);
  REQUIRE(destination.dma_size_bytes() == 2 * bytes_per_page);
  destination.append(source);

  page_t* destination_page = destination.page_of(target_token);
  REQUIRE(float(destination_page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) ==
          11.0f);
  alignas(64) std::array<bf16, geometry_128.head_size> destination_k{};
  destination_page->template get_k_row<geometry_128>(kv_slot_id(1), 1, 0,
      k_destination_row<geometry_128.head_size>(destination_k.data()));
  REQUIRE(float(destination_k[0]) == 22.0f);
  REQUIRE(destination_page->is_kv_complete(kv_slot_id(1), 0));
  alignas(64) std::array<bf16, geometry_128.head_size> destination_v;
  destination_page->template get_v<geometry_128>(kv_slot_id(1), 1, 0,
      v_destination_row<geometry_128.head_size>(destination_v.data()));
  for (bf16 element : destination_v)
    REQUIRE(float(element) == 33.0f);
  destination_page->set_offset_bound(1);
  tensor<cache_t::page_size> scales = constant<cache_t::page_size>(0.0f);
  scales[0] = 1.0f;
  tensor<geometry_128.head_size> scratch;
  tensor<geometry_128.head_size> scaled =
      destination_page->template scaled_v<geometry_128>(
          kv_slot_id(1), 1, scales, scratch);
  for (float element : scaled)
    REQUIRE(element == 33.0f);
}

TEST_CASE("attention registry separates operation and geometry identity", "[kv_data]") {
  constexpr attention_geometry geometry_0{8, kv_geometry{1, 64}};
  constexpr attention_geometry geometry_1{12, kv_geometry{2, 128}};
  constexpr attention_geometry geometry_2{16, kv_geometry{4, 256}};
  constexpr float scale_0 = 0.125f;
  constexpr float scale_1 = 0x1.6a09e6p-4f;
  constexpr float scale_2 = 0.0625f;
  constexpr std::array kernels{
      attention_kernel_spec{attention_kernel_id(0), geometry_0},
      attention_kernel_spec{attention_kernel_id(1), geometry_1},
      attention_kernel_spec{attention_kernel_id(2), geometry_2},
  };
  constexpr std::array operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(2), kv_slot_id(2)},
          attention_kernel_id(1), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_1}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(7), kv_slot_id(0)},
          attention_kernel_id(2), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_2}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(2), model_layer_id(11), kv_slot_id(1)},
          attention_kernel_id(0), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_0}},
  };
  constexpr std::array slots{
      kv_slot_spec{geometry_2.kv},
      kv_slot_spec{geometry_0.kv},
      kv_slot_spec{geometry_1.kv},
  };
  constexpr std::array mismatched_slots{
      kv_slot_spec{geometry_0.kv},
      kv_slot_spec{geometry_0.kv},
      kv_slot_spec{geometry_1.kv},
  };
  constexpr std::array sink_specs{
      attention_sink_spec{attention_sink_id(0), geometry_1.n_query_heads}};
  constexpr std::array mismatched_sink_specs{
      attention_sink_spec{attention_sink_id(0), geometry_0.n_query_heads}};
  constexpr std::array non_dense_sink_specs{
      attention_sink_spec{attention_sink_id(1), geometry_1.n_query_heads}};
  constexpr std::array sink_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(2), kv_slot_id(2)},
          attention_kernel_id(1), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, attention_sink_id(0), scale_1}},
      operations[1],
      operations[2],
  };
  constexpr std::array invalid_kernels{
      attention_kernel_spec{attention_kernel_id(0), geometry_0},
      attention_kernel_spec{attention_kernel_id(2), geometry_1},
  };
  constexpr std::array invalid_shared_slot{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(2), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, false,
          attention_operation_config{std::nullopt, std::nullopt, scale_0}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(7), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_0}},
  };
  constexpr std::array missing_writer{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(4), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, false,
          attention_operation_config{std::nullopt, std::nullopt, scale_0}},
  };
  constexpr std::array shared_model_layer_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(5), kv_slot_id(2)},
          attention_kernel_id(1), attention_hardware_capability::software_only, true,
          attention_operation_config{17, attention_sink_id(0), scale_1}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(5), kv_slot_id(0)},
          attention_kernel_id(2), attention_hardware_capability::software_only, true,
          attention_operation_config{31, std::nullopt, scale_2}},
  };
  constexpr std::array shared_model_layer_slots{
      kv_slot_spec{geometry_2.kv, kv_slot_retention::sliding_window(31)},
      slots[1],
      kv_slot_spec{geometry_1.kv, kv_slot_retention::sliding_window(17)},
  };
  constexpr std::array duplicate_slot_writers{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(2), kv_slot_id(0)},
          attention_kernel_id(2), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_2}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(7), kv_slot_id(0)},
          attention_kernel_id(2), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_2}},
  };
  constexpr auto uniform_operations = uniform_attention_operations<3>(scale_0);
  constexpr auto shared_layer_uniform_operations = [] {
    auto result = uniform_attention_operations<3>(0.125f);
    result[1].binding.model_layer = model_layer_id(0);
    return result;
  }();
  constexpr auto invalid_window_operations = [] {
    auto result = uniform_attention_operations<3>(0.125f);
    result[0].config.sliding_window_size = 0;
    return result;
  }();
  constexpr std::array reordered_uniform_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(1), kv_slot_id(1)},
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, scale_0}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(0), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, scale_0}},
      uniform_operations[2],
  };
  constexpr std::array truncated_uniform_operations{
      uniform_operations[0],
      uniform_operations[1],
  };
  constexpr std::array scaled_uniform_operations{
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(0)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, 0.125f}},
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(1)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, 0.125f}},
  };
  constexpr std::array mixed_scaled_uniform_operations{
      scaled_uniform_operations[0],
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(1)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, 0.25f}},
  };
  constexpr std::array invalid_scaled_uniform_operations{
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(0)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true, attention_operation_config{std::nullopt, std::nullopt, 0.0f}},
  };
  constexpr std::array infinite_scaled_uniform_operations{
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(0)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true,
          attention_operation_config{
              std::nullopt, std::nullopt, std::numeric_limits<float>::infinity()}},
  };
  constexpr std::array nan_scaled_uniform_operations{
      attention_operation_descriptor{uniform_attention_binding(attention_op_id(0)),
          attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate,
          true,
          attention_operation_config{
              std::nullopt, std::nullopt, std::numeric_limits<float>::quiet_NaN()}},
  };
  constexpr std::array remapped_uniform_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(0), kv_slot_id(1)},
          attention_kernel_id(0), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, scale_0}},
  };
  constexpr attention_operation_descriptor fixed_slot_hardware_candidate{
      attention_binding{attention_op_id(0), model_layer_id(17), kv_slot_id(1)},
      attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate, true,
      attention_operation_config{std::nullopt, std::nullopt, scale_0}};
  constexpr attention_operation_descriptor mismatched_slot_hardware_candidate{
      attention_binding{attention_op_id(0), model_layer_id(17), kv_slot_id(0)},
      fixed_slot_hardware_candidate.kernel, fixed_slot_hardware_candidate.hardware,
      fixed_slot_hardware_candidate.writes_kv, fixed_slot_hardware_candidate.config};
  constexpr attention_operation_descriptor read_only_hardware_candidate{
      fixed_slot_hardware_candidate.binding, fixed_slot_hardware_candidate.kernel,
      fixed_slot_hardware_candidate.hardware, false,
      fixed_slot_hardware_candidate.config};
  constexpr attention_operation_descriptor sliding_hardware_candidate{
      fixed_slot_hardware_candidate.binding, fixed_slot_hardware_candidate.kernel,
      fixed_slot_hardware_candidate.hardware, true,
      attention_operation_config{64, std::nullopt, scale_0}};
  using uniform_cache_t = uniform_kv_cache<3, geometry_0.kv, 0>;
  using wide_cache_t = uniform_kv_cache<1, geometry_2.kv, 16>;
  using wide_page_t = wide_cache_t::page_t;

  STATIC_REQUIRE(valid_attention_kernel_registry(kernels));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, uniform_operations, uniform_cache_t::kv_slot_specs));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, remapped_uniform_operations, uniform_cache_t::kv_slot_specs));
  STATIC_REQUIRE(valid_attention_operation_descriptors(kernels, operations));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, reordered_uniform_operations, uniform_cache_t::kv_slot_specs));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, truncated_uniform_operations, uniform_cache_t::kv_slot_specs));
  STATIC_REQUIRE(valid_attention_configuration(kernels, operations, slots));
  STATIC_REQUIRE(is_hardware_attention_candidate(
      kernels, slots, fixed_slot_hardware_candidate, geometry_0));
  STATIC_REQUIRE(
      fixed_slot_hardware_candidate.binding.model_layer == model_layer_id(17));
  STATIC_REQUIRE(fixed_slot_hardware_candidate.binding.kv_slot == kv_slot_id(1));
  STATIC_REQUIRE_FALSE(is_hardware_attention_candidate(
      kernels, slots, read_only_hardware_candidate, geometry_0));
  STATIC_REQUIRE_FALSE(is_hardware_attention_candidate(
      kernels, slots, sliding_hardware_candidate, geometry_0));
  STATIC_REQUIRE_FALSE(is_hardware_attention_candidate(
      kernels, slots, mismatched_slot_hardware_candidate, geometry_0));
  STATIC_REQUIRE_FALSE(is_hardware_attention_candidate(
      kernels, slots, fixed_slot_hardware_candidate, geometry_1));
  STATIC_REQUIRE(
      valid_attention_operation_descriptors(kernels, shared_model_layer_operations));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, shared_model_layer_operations, shared_model_layer_slots, sink_specs));
  STATIC_REQUIRE(
      valid_attention_operation_descriptors(kernels, shared_layer_uniform_operations));
  STATIC_REQUIRE(valid_attention_configuration(
      kernels, shared_layer_uniform_operations, uniform_cache_t::kv_slot_specs));
  STATIC_REQUIRE(
      valid_attention_configuration(kernels, sink_operations, slots, sink_specs));
  STATIC_REQUIRE_FALSE(valid_attention_configuration(kernels, sink_operations, slots));
  STATIC_REQUIRE_FALSE(valid_attention_configuration(
      kernels, sink_operations, slots, mismatched_sink_specs));
  STATIC_REQUIRE_FALSE(valid_attention_configuration(
      kernels, sink_operations, slots, non_dense_sink_specs));
  STATIC_REQUIRE_FALSE(
      valid_attention_configuration(kernels, operations, mismatched_slots));
  STATIC_REQUIRE_FALSE(
      valid_attention_operation_descriptors(kernels, invalid_shared_slot));
  STATIC_REQUIRE_FALSE(
      valid_attention_operation_descriptors(kernels, duplicate_slot_writers));
  STATIC_REQUIRE_FALSE(valid_attention_operation_descriptors(kernels, missing_writer));
  STATIC_REQUIRE_FALSE(valid_attention_operation_descriptors(
      kernels, invalid_scaled_uniform_operations));
  STATIC_REQUIRE_FALSE(valid_attention_operation_descriptors(
      kernels, infinite_scaled_uniform_operations));
  STATIC_REQUIRE_FALSE(
      valid_attention_operation_descriptors(kernels, nan_scaled_uniform_operations));
  STATIC_REQUIRE_FALSE(
      valid_attention_operation_descriptors(kernels, invalid_window_operations));
  STATIC_REQUIRE_FALSE(valid_attention_kernel_registry(invalid_kernels));
  STATIC_REQUIRE(valid_uniform_hardware_attention_scale(scaled_uniform_operations));
  STATIC_REQUIRE_FALSE(
      valid_uniform_hardware_attention_scale(mixed_scaled_uniform_operations));
  STATIC_REQUIRE(uniform_hardware_attention_scale(scaled_uniform_operations) ==
                 std::optional<float>{0.125f});
  STATIC_REQUIRE(hardware_attention_scale_representable(0.125f));
  STATIC_REQUIRE_FALSE(
      hardware_attention_scale_representable(std::numeric_limits<float>::min()));
  STATIC_REQUIRE_FALSE(
      hardware_attention_scale_representable(std::numeric_limits<float>::max()));
  constexpr float nominal_hardware_scale = scale_1;
  constexpr float device_hardware_scale = fp16(nominal_hardware_scale);
  constexpr float raw_hardware_maximum = 17.0f;
  STATIC_REQUIRE(device_hardware_scale != nominal_hardware_scale);
  STATIC_REQUIRE(
      decode_hardware_attention_maximum(raw_hardware_maximum, nominal_hardware_scale) ==
      raw_hardware_maximum * nominal_hardware_scale);
  STATIC_REQUIRE(
      decode_hardware_attention_maximum(raw_hardware_maximum, nominal_hardware_scale) !=
      raw_hardware_maximum * device_hardware_scale);
  STATIC_REQUIRE(
      attention_kernel_at(kernels, attention_kernel_id(1)).geometry == geometry_1);
  STATIC_REQUIRE(max_attention_query_width(kernels) == 16 * 256);
  STATIC_REQUIRE(max_attention_query_heads(kernels) == 16);
  STATIC_REQUIRE(max_attention_kv_heads(kernels) == 4);
  STATIC_REQUIRE(operations[0].binding.operation == attention_op_id(0));
  STATIC_REQUIRE(operations[0].binding.model_layer == model_layer_id(2));
  STATIC_REQUIRE(operations[0].binding.kv_slot == kv_slot_id(2));
  STATIC_REQUIRE(operations[0].kernel == attention_kernel_id(1));
  STATIC_REQUIRE(operations[0].writes_kv);
  STATIC_REQUIRE(operations[1].writes_kv);
  STATIC_REQUIRE(
      uniform_operations[2].binding == uniform_attention_binding(attention_op_id(2)));
  STATIC_REQUIRE_FALSE(std::is_default_constructible_v<attention_operation_config>);
  STATIC_REQUIRE(uniform_operations[0].config.scale == scale_0);
  STATIC_REQUIRE(uniform_operations[2].config.scale == scale_0);
  STATIC_REQUIRE(wide_cache_t::template declares_geometry<geometry_2.kv>());
  STATIC_REQUIRE((page_k_accepts_geometry<wide_page_t, geometry_2.kv>));
  STATIC_REQUIRE((page_scaled_v_accepts_geometry<wide_page_t, geometry_2.kv>));
}

TEST_CASE("attention plan profiles capture scheduling equivalence", "[attention]") {
  constexpr attention_geometry geometry{8, kv_geometry{2, 128}};
  constexpr attention_plan_profile profile{geometry, 4096, false};
  constexpr attention_plan_profile same_profile{geometry, 4096, false};
  constexpr attention_plan_profile different_geometry{
      {8, kv_geometry{1, 128}}, 4096, false};
  constexpr attention_plan_profile different_window{geometry, 2048, false};
  constexpr attention_plan_profile different_hardware_route{geometry, 4096, true};

  STATIC_REQUIRE(profile == same_profile);
  STATIC_REQUIRE_FALSE(profile == different_geometry);
  STATIC_REQUIRE_FALSE(profile == different_window);
  STATIC_REQUIRE_FALSE(profile == different_hardware_route);
}

TEST_CASE(
    "attention configuration binds operation-owned windows and sinks", "[attention]") {
  STATIC_REQUIRE(attention_plugin_config<operation_attention_config_fixture>);
  STATIC_REQUIRE_FALSE(attention_plugin_config<wrong_sink_type_fixture>);
  STATIC_REQUIRE_FALSE(attention_plugin_config<throwing_sink_fixture>);
  STATIC_REQUIRE_FALSE(attention_plugin_config<passthrough_plugin_like>);
  attention_operation_descriptor operation{
      uniform_attention_binding(attention_op_id(1)), attention_kernel_id(0),
      attention_hardware_capability::software_only, true,
      attention_operation_config{23, attention_sink_id(0), 0.125f}};
  operation_attention_config_fixture plugin;
  plugin.sink = tensor<2>{1.25f, -0.75f};
  attention_runtime_config const runtime_config =
      bind_attention_runtime_config(plugin, operation);
  REQUIRE(runtime_config.sliding_window_size == 23);
  REQUIRE(runtime_config.sinks.size() == 2);
  REQUIRE(runtime_config.sinks[0] == 1.25f);
  REQUIRE(runtime_config.sinks[1] == -0.75f);

  attention_operation_descriptor const no_sink{
      attention_binding{attention_op_id(0), model_layer_id(4), kv_slot_id(2)},
      attention_kernel_id(0), attention_hardware_capability::software_only, true,
      attention_operation_config{31, std::nullopt, 0.125f}};
  attention_operation_descriptor const with_sink{
      attention_binding{attention_op_id(1), model_layer_id(4), kv_slot_id(3)},
      attention_kernel_id(0), attention_hardware_capability::software_only, true,
      attention_operation_config{47, attention_sink_id(0), 0.125f}};
  REQUIRE(no_sink.binding.model_layer == with_sink.binding.model_layer);
  REQUIRE(no_sink.binding.kv_slot != with_sink.binding.kv_slot);
  std::array const schedules{
      std::array{with_sink, no_sink}, std::array{no_sink, with_sink}};
  operation_attention_config_fixture generated;

  struct accumulator {
    float m_star;
    float s_star;
    float value;
  };
  accumulator const initial{-0.25f, 2.0f, 3.0f};

  for (auto const& schedule : schedules) {
    for (auto const& operation : schedule) {
      attention_runtime_config const config =
          bind_attention_runtime_config(generated, operation);
      REQUIRE(
          config.sliding_window_size == operation.config.sliding_window_size.value());

      accumulator actual = initial;
      if (!config.sinks.empty()) {
        attention_sink_update const update =
            attention_sink_update_for(config.sinks[0], actual.m_star, actual.s_star);
        actual.m_star = update.m_star;
        actual.s_star = update.s_star;
        actual.value *= update.value_scale;
      }

      accumulator expected = initial;
      if (operation.config.sink) {
        float const sink = generated.sink[0];
        float const new_m = std::max(expected.m_star, sink);
        float const old_scale = std::exp(expected.m_star - new_m);
        expected.s_star = expected.s_star * old_scale + std::exp(sink - new_m);
        expected.value *= old_scale;
        expected.m_star = new_m;
      }

      REQUIRE_THAT(actual.m_star, Catch::Matchers::WithinAbs(expected.m_star, 1e-7f));
      REQUIRE_THAT(actual.s_star, Catch::Matchers::WithinAbs(expected.s_star, 1e-7f));
      REQUIRE_THAT(actual.value, Catch::Matchers::WithinAbs(expected.value, 1e-7f));
    }
  }
}

TEST_CASE("scaled_v supports wide values", "[kv_data]") {
  SECTION("256") {
    check_wide_scaled_v<256>();
  }
  SECTION("512") {
    check_wide_scaled_v<512>();
  }
}

TEST_CASE("handwritten plugins materialize exact attention scales", "[attention]") {
  STATIC_REQUIRE(named_llama_configs::llama_68m.attention_scale == 0.125f);
  STATIC_REQUIRE(named_llama_configs::llama_2_7b.attention_scale == 0x1.6a09e6p-4f);
  STATIC_REQUIRE(named_llama_configs::gemma_2_2b.attention_scale == 0.0625f);
  STATIC_REQUIRE(named_llama_configs::gemma_2_9b.attention_scale == 0.0625f);
  STATIC_REQUIRE(named_llama_configs::gemma_2_27b.attention_scale == 0x1.555556p-4f);

  using gemma_2_27b_tp1 = typename gemma_2_27b<tp1>::plugin_model;
  STATIC_REQUIRE(gemma_2_27b_tp1::attention_operations.front().config.scale ==
                 named_llama_configs::gemma_2_27b.attention_scale);
  STATIC_REQUIRE(gemma_2_27b_tp1::attention_operations.back().config.scale ==
                 named_llama_configs::gemma_2_27b.attention_scale);
}

TEST_CASE("handwritten plugins enforce checkpoint attention scales", "[attention]") {
  using llama_68m_tp1 = typename llama_68m<tp1>::plugin_model;
  using llama_2_7b_tp1 = typename llama_2_7b<tp1>::plugin_model;
  using gemma_2_27b_tp1 = typename gemma_2_27b<tp1>::plugin_model;

  llama_68m_tp1::enforce_attention_scale(json::object());
  llama_2_7b_tp1::enforce_attention_scale(json::object());
  gemma_2_27b_tp1::enforce_attention_scale(json{{"query_pre_attn_scalar", 144.0f}});
  REQUIRE(assertion_signal([] {
    gemma_2_27b_tp1::enforce_attention_scale(json::object());
  }) == SIGABRT);
  REQUIRE(assertion_signal([] {
    gemma_2_27b_tp1::enforce_attention_scale(json{{"query_pre_attn_scalar", 256.0f}});
  }) == SIGABRT);
}

TEST_CASE("dynamic attention descriptors match the active operation", "[attention]") {
  constexpr llm_configuration config{.type = model_type::llama,
      .dim = 64,
      .hidden_dim = 64,
      .n_layers = 2,
      .n_heads = 1,
      .n_kv_heads = 1,
      .vocab_size = 32,
      .head_size = 64,
      .attention_scale = 0.125f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using plugin_t = llm<config, make_llm_executor<false, tensor, tensor, tensor>>;
  using model_t = model<plugin_t>;
  constexpr attention_geometry geometry{1, kv_geometry{1, 64}};

  // Construct child-owned state without inheriting workers from earlier cases.
  shutdown_app_pool();
  auto validate = [&](attention_operation_descriptor operation, int max_layers = 2) {
    return assertion_signal([&] {
      auto model = std::make_unique<model_t>(
          std::filesystem::path{}, json(json::value_t::object));
      model_t::state state(*model, model_config{.max_layers = max_layers});
      state.self_attn_state.validate_operation<geometry>(operation);
    });
  };

  auto const canonical = plugin_t::attention_operations[0];
  REQUIRE(validate(canonical) == 0);
  auto altered = canonical;
  altered.binding.operation = attention_op_id(2);
  REQUIRE(validate(altered) == SIGABRT);
  REQUIRE(validate(plugin_t::attention_operations[1], 1) == SIGABRT);
  altered = canonical;
  altered.binding.model_layer = model_layer_id(1);
  REQUIRE(validate(altered) == SIGABRT);
  altered = canonical;
  altered.binding.kv_slot = kv_slot_id(1);
  REQUIRE(validate(altered) == SIGABRT);
  altered = canonical;
  altered.config.scale = 0.25f;
  REQUIRE(validate(altered) == SIGABRT);
}

TEST_CASE("EAGLE instances are excluded from hardware attention", "[attention]") {
  constexpr llm_configuration config{.type = model_type::llama,
      .dim = 64,
      .hidden_dim = 64,
      .n_layers = 2,
      .n_heads = 1,
      .n_kv_heads = 1,
      .vocab_size = 32,
      .head_size = 64,
      .attention_scale = 0.125f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t = model<llm<config, make_llm_executor<false, tensor, tensor, tensor>>>;

  STATIC_REQUIRE(model_t::model_shape_is_hwattn_eligible());
  STATIC_REQUIRE(model_t::model_instance_is_hwattn_eligible(false));
  STATIC_REQUIRE_FALSE(model_t::model_instance_is_hwattn_eligible(true));
}

// An MQA shape (one KV head, many query heads) fits every per-KV-head hardware limit
// but overflows the 5-bit gqa command field; it must be steered to software
// attention at the constexpr gate rather than aborting in the worker.
TEST_CASE(
    "MQA shapes past HW_MAX_GQA are not hardware-attention eligible", "[attention]") {
  constexpr llm_configuration config{.type = model_type::llama,
      .dim = 2048,
      .hidden_dim = 64,
      .n_layers = 2,
      .n_heads = 32,
      .n_kv_heads = 1,
      .vocab_size = 32,
      .head_size = 64,
      .attention_scale = 0.125f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t = model<llm<config, make_llm_executor<false, tensor, tensor, tensor>>>;

  STATIC_REQUIRE(config.n_heads / config.n_kv_heads > hardware::HW_MAX_GQA);
  STATIC_REQUIRE_FALSE(model_t::model_shape_is_hwattn_eligible());
  STATIC_REQUIRE_FALSE(model_t::model_instance_is_hwattn_eligible(false));
}

// See Note [Draft models are separate checkpoints]
TEST_CASE("draft config rebases the target's checkpoint", "[eagle]") {
  const model_config target{
      .weights_directory = "/opt/positron/weights",
      .pay_for_determinism = true,
      .id = "llama-3.1-8b-instruct-good-tp2",
      .model_path = "/opt/positron/weights/huggingface/neuralmagic/quantized",
      .resolved_weights_path = "/var/cache/positron/neuralmagic/quantized",
      .model_config_file = "/tmp/target-config.json",
      .json_config_override = json{{"num_hidden_layers", 32}},
      .max_minibatches = 4,
      .synthesize_missing_tensors = true,
      .synthesis_seed = 99,
      .expert_load_profile = "/tmp/target-expert-load.json",
  };
  const draft_model_config draft_spec{.id = "eagle-llama-3.1-8b-instruct-tp2"};

  SECTION("a draft without weights of its own resolves from the registry") {
    const model_config draft = target.for_draft(draft_spec);

    CHECK(draft.id == "eagle-llama-3.1-8b-instruct-tp2");
    CHECK_FALSE(draft.model_path.has_value());
    CHECK(draft.resolved_weights_path.empty());
    CHECK_FALSE(draft.model_config_file.has_value());
    CHECK_FALSE(draft.json_config_override.has_value());
    CHECK_FALSE(draft.expert_load_profile.has_value());
  }

  SECTION("explicit draft weights replace the target's") {
    const model_config draft = target.for_draft({.id = draft_spec.id,
        .model_path = "/opt/positron/weights/huggingface/leptonai/EAGLE"});

    CHECK(draft.model_path ==
          std::filesystem::path("/opt/positron/weights/huggingface/leptonai/EAGLE"));
  }

  SECTION("the draft runs one layer, speculates, and has no draft of its own") {
    const model_config draft = target.for_draft(draft_spec);

    CHECK(draft.max_layers == 1);
    CHECK(draft.is_speculator);
    CHECK_FALSE(draft.support_eagle);
    CHECK_FALSE(draft.draft_model.has_value());
  }

  SECTION("deployment policy applies to both models of the pair") {
    const model_config draft = target.for_draft(draft_spec);

    CHECK(draft.weights_directory == target.weights_directory);
    CHECK(draft.pay_for_determinism);
    CHECK(draft.max_minibatches == 4);
    CHECK(draft.synthesize_missing_tensors);
    CHECK(draft.synthesis_seed == 99);
  }
}

TEST_CASE("heterogeneous plugin cache uses value slot topology", "[kv_data]") {
  using cache_t = heterogeneous_cache;
  using page_t = cache_t::page_t;
  constexpr std::array invalid_specs{
      kv_slot_spec{kv_geometry{1, 65}},
  };
  constexpr std::array<kv_slot_spec, 0> empty_specs{};
  constexpr kv_geometry undeclared_geometry{3, 64};

  STATIC_REQUIRE(valid_kv_slot_specs(heterogeneous_slot_specs));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(invalid_specs));
  STATIC_REQUIRE_FALSE(valid_kv_slot_specs(empty_specs));
  STATIC_REQUIRE(sequence_cache<cache_t>);
  STATIC_REQUIRE(cache_t::n_slots == 3);
  STATIC_REQUIRE(cache_t::logical_slot_count_for_layers(6) == 3);
  STATIC_REQUIRE(cache_t::storage_slot_count_for_layers(6, false) == 3);
  STATIC_REQUIRE_FALSE(cache_t::eagle_compatible);
  STATIC_REQUIRE_FALSE(heterogeneous_eagle_without_embeddings::eagle_compatible);
  STATIC_REQUIRE(cache_t::template declares_geometry<geometry_64>());
  STATIC_REQUIRE(cache_t::template declares_geometry<geometry_128>());
  STATIC_REQUIRE(cache_t::template declares_geometry<geometry_256>());
  STATIC_REQUIRE_FALSE(cache_t::template declares_geometry<undeclared_geometry>());
  STATIC_REQUIRE((page_k_accepts_geometry<page_t, geometry_64>));
  STATIC_REQUIRE_FALSE((page_k_accepts_geometry<page_t, undeclared_geometry>));

  STATIC_REQUIRE_FALSE(cache_maps_model_layers<cache_t>);
  STATIC_REQUIRE(heterogeneous_attention_schedule[0].operation == attention_op_id(9));
  STATIC_REQUIRE(heterogeneous_attention_schedule[0].kv_slot == kv_slot_id(0));
  STATIC_REQUIRE(heterogeneous_attention_schedule[1].kv_slot == kv_slot_id(2));
  STATIC_REQUIRE(heterogeneous_attention_schedule[3].kv_slot == kv_slot_id(2));
  STATIC_REQUIRE(cache_t::template slot_matches<geometry_64>(kv_slot_id(0)));
  STATIC_REQUIRE_FALSE(cache_t::template slot_matches<geometry_128>(kv_slot_id(0)));
  STATIC_REQUIRE_FALSE(cache_t::template slot_matches<geometry_64>(kv_slot_id(3)));

  cache_t destination(/*n_pages=*/1);
  cache_t source(/*n_pages=*/1);
  destination.increment_tokens_used(2);
  source.increment_tokens_used(3);
  auto* src_page = source.page_of(0);
  for (size_t token = 0; token < source.size(); ++token) {
    src_page->template k<geometry_64>(kv_slot_id(0), 0, token)[0] =
        static_cast<bf16>(10.0f + token);
    alignas(64) std::array<bf16, geometry_128.head_size> k_row{};
    k_row[0] = static_cast<bf16>(20.0f + token);
    src_page->template set_k_row<geometry_128>(
        kv_slot_id(1), 1, token, k_source_row<geometry_128.head_size>(k_row.data()));
    src_page->template k<geometry_256>(kv_slot_id(2), 0, token)[0] =
        static_cast<bf16>(30.0f + token);
  }

  constexpr size_t bytes_per_page =
      2 * cache_t::page_size * sizeof(bf16) *
      (geometry_64.n_kv_heads * geometry_64.head_size +
          geometry_128.n_kv_heads * geometry_128.head_size +
          geometry_256.n_kv_heads * geometry_256.head_size);
  REQUIRE(destination.dma_size_bytes() == bytes_per_page);
  REQUIRE(destination.storage_slot_count() == 3);

  destination.append(source);
  REQUIRE(destination.size() == 5);
  auto* dst_page = destination.page_of(0);
  for (size_t token = 0; token < source.size(); ++token) {
    size_t const destination_token = 2 + token;
    REQUIRE(float(dst_page->template k<geometry_64>(
                kv_slot_id(0), 0, destination_token)[0]) == 10.0f + token);
    alignas(64) std::array<bf16, geometry_128.head_size> k_row{};
    dst_page->template get_k_row<geometry_128>(kv_slot_id(1), 1, destination_token,
        k_destination_row<geometry_128.head_size>(k_row.data()));
    REQUIRE(float(k_row[0]) == 20.0f + token);
    REQUIRE(float(dst_page->template k<geometry_256>(
                kv_slot_id(2), 0, destination_token)[0]) == 30.0f + token);
  }
}

TEST_CASE("heterogeneous cache isolates EAGLE as a uniform capability", "[kv_data]") {
  using cache_t = heterogeneous_eagle_cache;
  constexpr size_t storage_slots = cache_t::storage_slot_count_for_layers(2, true);

  STATIC_REQUIRE(cache_t::eagle_compatible);
  STATIC_REQUIRE(storage_slots == 3);
  STATIC_REQUIRE_FALSE(heterogeneous_cache::eagle_compatible);

  cache_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);
  auto* page = cache.page_of(0);
  REQUIRE(cache.eagle_storage_offset() == kv_storage_offset(2));
  REQUIRE(cache.storage_slot_count() == 3);
  REQUIRE(cache.dma_size_bytes() ==
          static_cast<int64_t>(3 * 2 * cache_t::page_size * geometry_64.n_kv_heads *
                                   geometry_64.head_size * sizeof(bf16) +
                               cache_t::page_size * 16));

  page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] = static_cast<bf16>(1.0f);
  cache.set_storage_view(cache.eagle_storage_offset());
  page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0] = static_cast<bf16>(2.0f);
  cache.reset_storage_view();
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 1.0f);
  cache.set_storage_view(cache.eagle_storage_offset());
  REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, 0)[0]) == 2.0f);
}

TEST_CASE(
    "heterogeneous book page count respects each DMA allocation", "[kv_data][book]") {
  constexpr size_t one_gib = size_t{1} << 30;

  // This fixture has 50 one-MiB sliding slots and ten half-MiB full-history
  // slots per page. Logical book sizing retains the 50-MiB-per-page sliding
  // bound: a one-GiB limit permits 20 pages, but not 21. Physical sliding
  // storage is chunked independently.
  REQUIRE(gemma4_31b_cache::kv_storage_bytes_for_pages(1) == 55 * (size_t{1} << 20));
  REQUIRE(gemma4_31b_cache::max_pages_for_dma_allocation(one_gib) == 20);

  // Without retention separation, the combined 55-MiB KV allocation remains
  // limited to 18 pages. Keep this as a distinct all-full layout contract.
  REQUIRE(gemma4_31b_all_full_cache::max_pages_for_dma_allocation(one_gib) == 18);
  REQUIRE(gemma4_31b_all_full_cache::kv_storage_bytes_for_pages(18) <= one_gib);
  REQUIRE(gemma4_31b_all_full_cache::kv_storage_bytes_for_pages(19) > one_gib);

  // The EAGLE KV arena and embedding buffer are distinct DMA allocations.
  // Four KV pages fit this cap even though their combined footprint does not.
  constexpr size_t storage_slots =
      heterogeneous_eagle_cache::storage_slot_count_for_layers(2, true);
  constexpr size_t kv_bytes_per_page = 3 * 2 * heterogeneous_eagle_cache::page_size *
                                       geometry_64.n_kv_heads * geometry_64.head_size *
                                       sizeof(bf16);
  constexpr size_t cap = 4 * kv_bytes_per_page;
  constexpr size_t x_bytes_per_page = heterogeneous_eagle_cache::page_size * 16;
  STATIC_REQUIRE(4 * (kv_bytes_per_page + x_bytes_per_page) > cap);
  REQUIRE(heterogeneous_eagle_cache::max_pages_for_dma_allocation(
              cap, storage_slots, /*support_eagle=*/true) == 4);
  REQUIRE(heterogeneous_eagle_cache::max_pages_for_dma_allocation(
              kv_bytes_per_page - 1, storage_slots, /*support_eagle=*/true) == 0);

  // A wide EAGLE embedding makes its separate x-storage allocation the bound.
  using wide_eagle_cache = heterogeneous_kv_cache<eagle_slot_specs, size_t{1} << 20>;
  constexpr size_t wide_x_bytes_per_page =
      wide_eagle_cache::page_size * (size_t{1} << 20);
  constexpr size_t wide_storage_slots =
      wide_eagle_cache::storage_slot_count_for_layers(2, true);
  REQUIRE(wide_eagle_cache::max_pages_for_dma_allocation(2 * wide_x_bytes_per_page,
              wide_storage_slots,
              /*support_eagle=*/true) == 2);
  REQUIRE(wide_eagle_cache::max_pages_for_dma_allocation(wide_x_bytes_per_page - 1,
              wide_storage_slots,
              /*support_eagle=*/true) == 0);
}

TEMPLATE_TEST_CASE("heterogeneous append preserves pages, V data, and completion",
    "[kv_data][book append]",
    heterogeneous_cache,
    mixed_retention_cache) {
  using cache_t = TestType;
  constexpr size_t destination_tokens = cache_t::page_size - 1;
  constexpr size_t source_tokens = cache_t::page_size + 2;
  cache_t destination(/*n_pages=*/3);
  cache_t source(/*n_pages=*/2);
  destination.increment_tokens_used(destination_tokens);
  source.increment_tokens_used(source_tokens);

  for (size_t token = 0; token < source_tokens; ++token) {
    auto* page = source.page_of(token);
    size_t const offset = token % cache_t::page_size;
    page->template k<geometry_64>(kv_slot_id(0), 0, offset)[0] =
        static_cast<bf16>(token + 1);
    alignas(64) std::array<bf16, geometry_128.head_size> k_row{};
    k_row[0] = static_cast<bf16>(token + 51);
    page->template set_k_row<geometry_128>(
        kv_slot_id(1), 1, offset, k_source_row<geometry_128.head_size>(k_row.data()));
    page->template k<geometry_256>(kv_slot_id(2), 0, offset)[0] =
        static_cast<bf16>(token + 101);
    REQUIRE_FALSE(page->mark_k_complete(kv_slot_id(0), offset));
    REQUIRE(page->mark_v_complete(kv_slot_id(0), offset));
    REQUIRE_FALSE(page->mark_k_complete(kv_slot_id(1), offset));
    alignas(64) std::array<bf16, geometry_64.head_size> value;
    value.fill(static_cast<bf16>(token + 21));
    page->template set_v<geometry_64>(
        kv_slot_id(0), 0, offset, v_source_row<geometry_64.head_size>(value.data()));
  }

  destination.append(source);
  REQUIRE(destination.size() == destination_tokens + source_tokens);
  for (size_t source_token = 0; source_token < source_tokens; ++source_token) {
    size_t const token = destination_tokens + source_token;
    auto* page = destination.page_of(token);
    size_t const offset = token % cache_t::page_size;
    REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, offset)[0]) ==
            source_token + 1);
    alignas(64) std::array<bf16, geometry_128.head_size> k_row{};
    page->template get_k_row<geometry_128>(kv_slot_id(1), 1, offset,
        k_destination_row<geometry_128.head_size>(k_row.data()));
    REQUIRE(float(k_row[0]) == source_token + 51);
    REQUIRE(float(page->template k<geometry_256>(kv_slot_id(2), 0, offset)[0]) ==
            source_token + 101);
    REQUIRE(page->is_kv_complete(kv_slot_id(0), offset));
    REQUIRE_FALSE(page->is_kv_complete(kv_slot_id(1), offset));
    REQUIRE(page->mark_v_complete(kv_slot_id(1), offset));
    alignas(64) std::array<bf16, geometry_64.head_size> value;
    page->template get_v<geometry_64>(kv_slot_id(0), 0, offset,
        v_destination_row<geometry_64.head_size>(value.data()));
    for (bf16 element : value)
      REQUIRE(float(element) == source_token + 21);
  }
}

TEMPLATE_TEST_CASE("heterogeneous EAGLE append preserves both views and embeddings",
    "[kv_data][book append]",
    heterogeneous_eagle_cache,
    mixed_retention_eagle_cache) {
  using cache_t = TestType;
  constexpr size_t storage_slots = cache_t::storage_slot_count_for_layers(2, true);
  constexpr size_t destination_tokens = cache_t::page_size - 1;
  cache_t destination(/*n_pages=*/2, storage_slots, /*support_eagle=*/true);
  cache_t source(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);
  destination.increment_tokens_used(destination_tokens);
  source.increment_tokens_used(2);

  for (size_t token = 0; token < source.size(); ++token) {
    auto* page = source.page_of(token);
    page->template k<geometry_64>(kv_slot_id(0), 0, token)[0] =
        static_cast<bf16>(token + 1);
    REQUIRE_FALSE(page->mark_k_complete(kv_slot_id(0), token));
    REQUIRE(page->mark_v_complete(kv_slot_id(0), token));
    source.set_storage_view(source.eagle_storage_offset());
    page->template k<geometry_64>(kv_slot_id(0), 0, token)[0] =
        static_cast<bf16>(token + 11);
    source.reset_storage_view();
    std::fill_n(page->template x<uint8_t>(token), 16, uint8_t(token + 21));
  }

  destination.append(source);
  for (size_t source_token = 0; source_token < source.size(); ++source_token) {
    size_t const token = destination_tokens + source_token;
    auto* page = destination.page_of(token);
    size_t const offset = token % cache_t::page_size;
    REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, offset)[0]) ==
            source_token + 1);
    REQUIRE(page->is_kv_complete(kv_slot_id(0), offset));
    destination.set_storage_view(destination.eagle_storage_offset());
    REQUIRE(float(page->template k<geometry_64>(kv_slot_id(0), 0, offset)[0]) ==
            source_token + 11);
    destination.reset_storage_view();
    for (size_t byte = 0; byte < 16; ++byte)
      REQUIRE(page->template x<uint8_t>(offset)[byte] == source_token + 21);
  }
}

TEST_CASE("heterogeneous try_create is transactional and rejects overflow",
    "[kv_data][try_create][fault_seam]") {
  int64_t const baseline = pos_heap_active_allocations();
  test_seam::clear_dma_fault();

  CHECK(heterogeneous_cache::try_create(std::numeric_limits<size_t>::max()) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  test_seam::arm_dma_fault(0);
  CHECK(heterogeneous_cache::try_create(2) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  constexpr size_t storage_slots =
      heterogeneous_eagle_cache::storage_slot_count_for_layers(2, true);
  test_seam::arm_dma_fault(1);
  CHECK(heterogeneous_eagle_cache::try_create(
            2, storage_slots, /*support_eagle=*/true) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  constexpr size_t mixed_storage_slots =
      mixed_retention_eagle_cache::storage_slot_count_for_layers(2, true);
  for (size_t failed_allocation : {size_t{0}, size_t{1}, size_t{2}}) {
    test_seam::arm_dma_fault(failed_allocation);
    CHECK(mixed_retention_eagle_cache::try_create(
              2, mixed_storage_slots, /*support_eagle=*/true) == nullptr);
    CHECK(pos_heap_active_allocations() == baseline);
  }

  test_seam::clear_dma_fault();
}

TRON(inline)
bf16 bitwise_random_bf16(std::mt19937& gen) {
  std::uniform_int_distribution<uint16_t> dis(0, 0xFFFF);
  for (size_t i = 0; i < 1000; ++i) {
    bf16 b = std::bit_cast<bf16>(dis(gen));
    if (std::isnormal(float(b))) return b;
  }
  throw std::runtime_error("Failed to generate a random bf16");
}

TEMPLATE_TEST_CASE("scaled_v",
    "[kv_data]",
    full_retention_scaled_v_cache,
    mixed_retention_scaled_v_cache) {
  static constexpr size_t head_size = 128;
  static constexpr size_t n_layers = 3;
  static constexpr size_t n_kv_heads = 4;
  using book_t = TestType;
  using page_t = book_t::page_t;
  // Use a partial page to exercise offset_bound logic
  static constexpr size_t n_tokens = 48;  // Less than page_size (64)
  const size_t n_entries = n_layers * n_kv_heads * n_tokens * head_size;
  auto flatten = [](size_t layer, size_t kv_head, size_t page_ix, size_t i) {
    size_t result = layer;
    result = result * n_kv_heads + kv_head;
    result = result * n_tokens + page_ix;
    result = result * head_size + i;
    return result;
  };
  auto unflatten = [&](size_t index) {
    size_t i = index % head_size;
    index /= head_size;
    size_t page_ix = index % n_tokens;
    index /= n_tokens;
    size_t kv_head = index % n_kv_heads;
    index /= n_kv_heads;
    size_t layer = index;
    return std::make_tuple(layer, kv_head, page_ix, i);
  };

  // Use a random bf16 pattern to minimize collisions.
  std::unordered_map<size_t, float> fwd_pattern;
  std::unordered_map<float, std::vector<size_t>> inv_pattern;
  std::mt19937 gen(20240808);
  auto pattern = [&](size_t layer, size_t kv_head, size_t page_ix, size_t i) {
    size_t key = flatten(layer, kv_head, page_ix, i);
    if (auto it = fwd_pattern.find(key); it != fwd_pattern.end()) return it->second;
    float value = bitwise_random_bf16(gen);
    fwd_pattern[key] = value;
    inv_pattern[value].push_back(key);
    return value;
  };

  // Load v data via vout.
  book_t bk(1);
  page_t* p = bk.page_of(0);
  btensor<n_kv_heads * head_size> vout[n_tokens];
  for (size_t layer = 0; layer < n_layers; ++layer) {
    // Fill vout with test data.
    for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
      for (size_t i = 0; i < head_size; ++i)
        for (size_t page_ix = 0; page_ix < n_tokens; ++page_ix) {
          if (layer == 0 && kv_head == 0 && i == 0) bk.increment_tokens_used();
          vout[page_ix][kv_head * head_size + i] = pattern(layer, kv_head, page_ix, i);
        }
    // Copy vout to v, as in v_job_done_k().
    for (size_t page_ix = 0; page_ix < n_tokens; ++page_ix)
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
        p->set_v(test_kv_slot<book_t>(layer), kv_head, page_ix,
            v_source_row<head_size>(&vout[page_ix][kv_head * head_size]));
  }
  // Set the page's live token count so scaled_v knows how many entries to read.
  p->set_offset_bound(n_tokens);
  if (inv_pattern.size() < std::min<size_t>(n_entries, 1 << 16) * 0.75)
    spdlog::warn(
        "Pattern collisions: {} / {} unique entries", inv_pattern.size(), n_entries);

  // Count errors in scaled_v.
  size_t errors_total = 0;
  std::vector<size_t> errors_by_layer(n_layers, 0);
  std::vector<size_t> errors_by_kv_head(n_kv_heads, 0);
  std::vector<size_t> errors_by_page_ix(n_tokens, 0);
  std::vector<size_t> errors_by_i(head_size, 0);
  std::stringstream errors;
  tensor<page_t::page_size> scales;
  tensor<head_size> actual;
  tensor<head_size> scratch;
  for (size_t layer = 0; layer < n_layers; ++layer)
    for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
      for (size_t page_ix = 0; page_ix < n_tokens; ++page_ix) {
        // Query v data via a one-hot probe for this page.
        scales = constant<page_t::page_size>(0.0f);
        scales[page_ix] = 1.0f;
        actual = p->scaled_v(test_kv_slot<book_t>(layer), kv_head, scales, scratch);
        // Check each entry.
        for (size_t i = 0; i < head_size; ++i) {
          if (actual[i] == pattern(layer, kv_head, page_ix, i)) continue;
          ++errors_total;
          ++errors_by_layer[layer];
          ++errors_by_kv_head[kv_head];
          ++errors_by_page_ix[page_ix];
          ++errors_by_i[i];
          errors << fmt::format("Actual {}-{}-{}-{},\t", layer, kv_head, page_ix, i);
          errors << fmt::format("Expected one of");
          for (auto entry : inv_pattern[actual[i]]) {
            auto [a, b, c, d] = unflatten(entry);
            errors << fmt::format(" {}-{}-{}-{}", a, b, c, d);
          }
          errors << '\n';
        }
      }
  if (errors_total) {
    spdlog::error("Found {} scaled_v errors / {} entries", errors_total, n_entries);
    spdlog::error("Errors by layer: {}", errors_by_layer);
    spdlog::error("Errors by kv_head: {}", errors_by_kv_head);
    spdlog::error("Errors by page_ix: {}", errors_by_page_ix);
    spdlog::error("Errors by i: {}", errors_by_i);
    spdlog::error("Individual errors:\n{}", errors.str());
  } else
    spdlog::info("No scaled_v errors");
  REQUIRE(errors_total == 0);

  BENCHMARK_ADVANCED("scaled_v")(Catch::Benchmark::Chronometer meter) {
    const size_t steps = std::max<size_t>(1, n_entries / 3000);  // ~10ms per sample
    tensor<page_t::page_size> scales = constant<page_t::page_size>(1.0f);
    tensor<head_size> actual;
    meter.measure([&] {
      for (size_t step = 0; step < steps; ++step)
        for (size_t layer = 0; layer < n_layers; ++layer)
          for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
            for (size_t page_ix = 0; page_ix < page_t::page_size; ++page_ix)
              actual = actual + p->scaled_v(test_kv_slot<book_t>(layer), kv_head,
                                    scales, scratch);
    });
  };
}

TEST_CASE(
    "pending attention waits for invisible writers on the same page", "[page_range]") {
  // Two minibatches share a page. The consumer's visible half is saved first;
  // the other half remains poisoned until its producer's Save V completes.
  // Exercise visibility starting both at and after the page's first token.
  bool const visible_prefix = GENERATE(true, false);
  CAPTURE(visible_prefix);
  constexpr size_t head_size = 128;
  constexpr attention_geometry geometry{1, kv_geometry{1, head_size}};
  constexpr llm_configuration llm_config{.type = model_type::llama,
      .dim = head_size,
      .hidden_dim = head_size,
      .n_layers = 1,
      .n_heads = 1,
      .n_kv_heads = 1,
      .vocab_size = 128,
      .head_size = head_size,
      .attention_scale = 0x1.6a09e6p-4f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t =
      model<llm<llm_config, make_llm_executor<false, tensor, tensor, tensor>>>;
  constexpr size_t n_tokens = model_t::page::page_size;
  constexpr size_t half = n_tokens / 2;
  auto model =
      std::make_unique<model_t>(std::filesystem::path{}, json(json::value_t::object));
  model_t::book book(1, 1);
  book.increment_tokens_used(n_tokens);
  auto* page = book.page_of(0);
  page->set_lo(0, 0);
  page->set_offset_bound(n_tokens);

  model_t::state state(*model, model_config{.max_layers = 1});
  state.resize(n_tokens);
  std::vector<model_t::page*> pages{page};
  std::vector<model_t::page*> token_pages(n_tokens, page);
  std::vector<uint32_t> positions(n_tokens);
  indexed_vector<token_job_id, token_id> jobs;
  indexed_vector<token_job_id, uint8_t> do_kv(n_tokens, 1);
  for (size_t i = 0; i < n_tokens; ++i) {
    positions[i] = i;
    jobs.push_back(token_id(visible_prefix ? i : (i + half) % n_tokens));
    state.plugin_state.kouts[token_job_id(i)] = constant<head_size>(0.f);
    state.plugin_state.vouts[token_job_id(i)] = constant<head_size>(2.f);
    state.plugin_state.qs_roped[token_job_id(i)] = constant<head_size>(0.f);
  }
  state.pages.items = pages;
  state.token_pages.items = token_pages;
  state.token_positions.items = positions;
  state.token_jobs = jobs;
  state.token_jobs_do_kv = do_kv;

  mask_t<ranged_mask_capacity> all_queries;
  mask_t<ranged_mask_capacity> producer_queries;
  for (size_t i = 0; i < n_tokens; ++i) {
    all_queries.insert(i);
    if (i >= half) producer_queries.insert(i);
  }
  ranged_mask mask;
  mask.add_range(
      token_id(0), token_id(half), visible_prefix ? all_queries : producer_queries, {});
  mask.add_range(token_id(half), token_id(n_tokens),
      visible_prefix ? producer_queries : all_queries, {});
  state.query_mask = &mask;

  with_latch_arena latch_guard(state.latches);
  // Batch destructors wait on their channels before the arena clears its latches.
  finally clear_batches([&] { state.q_batches.clear(); });
  for (size_t b = 0; b < 2; ++b) {
    std::vector<token_job_id> items;
    for (size_t i = b * half; i < (b + 1) * half; ++i)
      items.emplace_back(i);
    auto batch =
        std::make_unique<model_t::batch>(state, std::move(items), state.latches, b);
    batch->plans.resize(state.attention_plan_profiles.size());
    for (auto& plan : batch->plans) {
      plan.n_sections = {1};
      plan.sections_left = std::vector<std::atomic_size_t>(1);
    }
    batch->reset_channels(0, 0);
    state.q_batches.push_back(std::move(batch));
  }
  state.finalize_minibatches();
  auto* consumer = state.q_batches[0].get();
  auto* producer = state.q_batches[1].get();
  auto const& operation = state.active_attention_operations.front();
  auto const slot = operation.binding.kv_slot;

  alignas(64) std::array<float, head_size> poison;
  poison.fill(std::numeric_limits<float>::quiet_NaN());
  for (size_t i = 0; i < n_tokens; ++i) {
    page->set_v(slot, 0, i, v_source_row<head_size>(poison.data()));
  }
  state.save_k<geometry>(consumer, operation, state.plugin_state.kouts);
  state.save_v<geometry>(consumer, operation, state.plugin_state.vouts);
  REQUIRE_FALSE(consumer->upstream_kvs_ready[slot].try_wait());
  state.save_k<geometry>(producer, operation, state.plugin_state.kouts);
  REQUIRE_FALSE(consumer->upstream_kvs_ready[slot].try_wait());
  state.save_v<geometry>(producer, operation, state.plugin_state.vouts);
  REQUIRE(consumer->upstream_kvs_ready[slot].try_wait());

  state.self_attn_state.free_scratchpads<geometry>(consumer, operation);
  std::array<std::vector<page_id>, 2> relevant_pages;
  state.select_relevant_pages(consumer->items, relevant_pages, {}, {page_id(0)},
      state.attention_runtime_configs[operation.binding.operation].sliding_window_size);
  // Attention path stats forced on (h/tron/models/attn_stats.hpp): with one
  // query head per KV head the AMX path is not eligible, so every consumer
  // query visits the page once on the AVX path and scores the `half` K tokens
  // its range makes visible. Replacing the member is safe here: this binary
  // initializes the FUSE tree only inside the t_attn_stats.cpp cases, each of
  // which unmounts it again, so no leaf points at the old object.
  {
    tron::attn_stats::header_facts facts;
    facts.n_kv_heads = 1;
    facts.kv_mul = 1;
    facts.head_size = head_size;
    facts.n_layers = 1;
    facts.page_size = n_tokens;
    constexpr bool STATS_ON_TRUE = true;
    constexpr bool NOT_EAGLE_FALSE = false;
    constexpr size_t N_LAYERS_1 = 1;
    state.self_attn_state.stats =
        std::make_shared<tron::attn_stats::model_stats>(STATS_ON_TRUE, "",
            NOT_EAGLE_FALSE, facts, state.self_attn_state.attn.size(), N_LAYERS_1);
  }
  {
    // The production sequence: the forward is open (begin_forward sized the
    // per-token vectors) while the pages are visited, and folded at its end.
    constexpr size_t N_ATTN_WORKERS_1 = 1;
    tron::attn_stats::forward_scope stats_scope(*state.self_attn_state.stats,
        tron::attn_stats::forward_class::decode_like, state.token_jobs.size(),
        state.token_jobs.size());
    // assemble_attention_plan_impl records the split in production.
    state.self_attn_state.stats->note_attn_workers(N_ATTN_WORKERS_1);
    state.self_attn_state.apply_page_range<geometry>(consumer->items, operation,
        state.plugin_state.qs_roped, 0, 0, N_ATTN_WORKERS_1, relevant_pages[1], {},
        consumer->items_mask,
        /*uses_hw=*/false, /*pending=*/true);
  }
  {
    using namespace tron::attn_stats;
    const auto sums = state.self_attn_state.stats->sum_layer(
        static_cast<size_t>(forward_class::decode_like), 0);
    CHECK(load_relaxed(state.self_attn_state.stats->forwards[0].token_jobs) ==
          state.token_jobs.size());
    // The per-token path sets of the forward, written by apply_page_range (one
    // bit per visit under the visiting job's index) and folded at the end of
    // the scope: each of the consumer's `half` jobs visited the page once on
    // the AVX path, the producer's jobs had no visit, and no job saw AMX.
    forward_counters const& decode_fc =
        state.self_attn_state.stats
            ->forwards[static_cast<size_t>(forward_class::decode_like)];
    CHECK(load_relaxed(decode_fc.token_jobs_by_path_set[PATH_BIT_AVX_1]) == half);
    CHECK(load_relaxed(decode_fc.token_jobs_by_path_set[PATH_BIT_NONE_0]) ==
          n_tokens - half);
    CHECK(load_relaxed(decode_fc.token_jobs_by_path_set[PATH_BIT_AMX_2]) == 0);
    CHECK(sums.visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == half);
    CHECK(sums.k_tokens[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] ==
          half * half);
    CHECK(sums.visits_all(static_cast<size_t>(visit_path::amx)) == 0);
    CHECK(sums.visits_all(static_cast<size_t>(visit_path::empty)) == 0);
    CHECK(sums.visits[PASS_READY_0][static_cast<size_t>(visit_path::avx)] == 0);
    CHECK(sums.avx_full_page_visits[PASS_PENDING_1] == 0);
    // The row is the pool worker's, not the attention worker's. The call
    // above ran attention worker 0 of a 1-worker split, which is the last
    // pool worker (Note [Attention workers are the last pool workers] in
    // model.hpp). Keyed by the attention index, the visits would go to row 0.
    // Row 0 is a main helper whenever the pool has more than one worker.
    const size_t n_pool = state.self_attn_state.attn.size();
    const size_t last_row = n_pool - 1;
    CHECK(state.self_attn_state.stats
              ->sum_worker(static_cast<size_t>(forward_class::decode_like), last_row)
              .visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == half);
    if (n_pool > 1) {
      CHECK(state.self_attn_state.stats
                ->sum_worker(static_cast<size_t>(forward_class::decode_like), 0)
                .visits_all(static_cast<size_t>(visit_path::avx)) == 0);
    } else {
      WARN("pool has one worker: the pool-row keying check cannot discriminate");
    }
  }
  for (size_t i = 0; i < half; ++i) {
    float const sum = state.self_attn_state.attn[0].s_stars[i][0];
    REQUIRE(sum > 0.f);
    for (size_t d = 0; d < head_size; ++d) {
      REQUIRE_THAT(state.self_attn_state.attn[0].v_stars[i][d] / sum,
          Catch::Matchers::WithinAbs(2.f, 1e-6f));
    }
  }
  if (state.self_attn_state.attn.size() >= 2) {
    // Run after the numeric check above, which the first call feeds. The same
    // attention worker 0 under a 2-worker split lands one row earlier: the
    // row follows the thread, not the attention index. If keyed by the attention
    // index, this call would land in row 0 again, and added to the first call.
    using namespace tron::attn_stats;
    constexpr size_t N_ATTN_WORKERS_2 = 2;
    {
      forward_scope stats_scope(*state.self_attn_state.stats,
          forward_class::decode_like, state.token_jobs.size(), state.token_jobs.size());
      state.self_attn_state.stats->note_attn_workers(N_ATTN_WORKERS_2);
      state.self_attn_state.apply_page_range<geometry>(consumer->items, operation,
          state.plugin_state.qs_roped, 0, 0, N_ATTN_WORKERS_2, relevant_pages[1], {},
          consumer->items_mask,
          /*uses_hw=*/false, /*pending=*/true);
    }
    const size_t n_pool = state.self_attn_state.attn.size();
    const size_t cls = static_cast<size_t>(forward_class::decode_like);
    CHECK(state.self_attn_state.stats->sum_worker(cls, n_pool - 2)
              .visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == half);
    CHECK(state.self_attn_state.stats->sum_worker(cls, n_pool - 1)
              .visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == half);
    CHECK(
        state.self_attn_state.stats->sum_layer(cls, 0)
            .visits[PASS_PENDING_1][static_cast<size_t>(visit_path::avx)] == 2 * half);
    CHECK(load_relaxed(state.self_attn_state.stats->forwards[cls].n_attn_workers_min) ==
          1);
    CHECK(load_relaxed(state.self_attn_state.stats->forwards[cls].n_attn_workers_max) ==
          N_ATTN_WORKERS_2);
  } else {
    WARN("pool has one worker: the split-moves check is skipped");
  }
}

template <size_t n_q_tokens, bool split_queries, bool uses_hw = false>
static void check_page_range_reductions(int sliding_window) {
  std::mt19937 gen(18);
  std::normal_distribution<> dis(0.0, 1.0);  // mean 0.0, standard deviation 1.0

  // 1. Allocate a small `llama_model` from @llama.hpp
  constexpr size_t head_size = 128;
  constexpr size_t n_heads = 16;
  constexpr size_t dim = head_size * n_heads;
  constexpr size_t hidden_dim = 1024;
  constexpr size_t n_layers = 2;
  constexpr size_t n_kv_heads = 8;
  constexpr size_t kv_mul = n_heads / n_kv_heads;
  // Exercise a scale distinct from the conventional value so the reference
  // comparison detects whether the operation-owned value reaches the kernel.
  constexpr float operation_scale = 0.0884f;
  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};

  constexpr llm_configuration llm_config{.type = model_type::llama,
      .dim = dim,
      .hidden_dim = hidden_dim,
      .n_layers = n_layers,
      .n_heads = n_heads,
      .n_kv_heads = n_kv_heads,
      .vocab_size = 32000,
      .head_size = head_size,
      .attention_scale = 0x1.6a09e6p-4f,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t =
      model<llm<llm_config, make_llm_executor<false, tensor, tensor, tensor>>>;
  using state_t = model_t::state;
  using book_t = model_t::book;
  using page_t = model_t::page;
  using batch = model_t::batch;

  std::unique_ptr<model_t> model =
      std::make_unique<model_t>(std::filesystem::path{}, json(json::value_t::object));

  // Store random values for validation
  std::vector<std::vector<float>> random_qs;  // [n_tokens][n_heads * head_size]
  // [n_pages * page_t::page_size][n_kv_heads * head_size]
  std::vector<std::vector<float>> random_ks;
  // [n_pages * page_t::page_size][n_kv_heads * head_size]
  std::vector<std::vector<float>> random_vs;

  // 2. Initialize a few pages of KV cache with random bf16 values
  // Preserve the two-page join case with offload disabled. With offload,
  // use enough resident pages to exercise range dismissal before the SW tail.
  constexpr size_t num_pages = uses_hw ? 10 : 2;
  const size_t num_kv_tokens = num_pages * page_t::page_size;
  book_t bk(num_pages, n_layers);
  bk.fill_random(gen);

  std::vector<page_t*> pages;
  std::vector<page_id> page_ixs;
  size_t first_q_token = num_kv_tokens - n_q_tokens;
  for (size_t i = 0; i < num_pages; ++i) {
    pages.push_back(bk.page_of(i * page_t::page_size));
    page_ixs.emplace_back(page_id(i));
    // We make all the KV entries applicable to all the tokens we are going
    // to query with, except we intentionally leave the last token
    // with no applicable KV entries to test null behavior.
    pages.back()->set_lo(0, i * page_t::page_size);
    for (size_t tok = 0; tok < page_t::page_size; ++tok) {
      bk.increment_tokens_used();
    }
    pages.back()->set_offset_bound(page_t::page_size);
  }

  // Copy out layer 0 for emulation::compute_attention
  random_ks.resize(num_kv_tokens, std::vector<float>(n_kv_heads * head_size));
  random_vs.resize(num_kv_tokens, std::vector<float>(n_kv_heads * head_size));
  for (size_t kv_token = 0; kv_token < num_kv_tokens; ++kv_token) {
    page_t* page = bk.page_of(kv_token);
    int offset = page->offset_in_page(token_id(kv_token));
    for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
      alignas(64) std::array<bf16, head_size> k_row;
      page->get_k_row(test_kv_slot<book_t>(0), kv_head, offset,
          k_destination_row<head_size>(k_row.data()));
      for (size_t elt = 0; elt < head_size; ++elt) {
        random_ks[kv_token][kv_head * head_size + elt] = k_row[elt];
      }
      alignas(64) float temp[head_size];
      page->get_v(
          test_kv_slot<book_t>(0), kv_head, offset, v_destination_row<head_size>(temp));
      std::copy(
          temp, temp + head_size, random_vs[kv_token].data() + kv_head * head_size);
    }
  }

  // 3. Allocate a `state` from the model
  state_t state(*model, model_config{.max_layers = n_layers});
  REQUIRE(state.attention_plan_profiles.size() == 1);
  REQUIRE(state.attention_plan_id_for_operation[attention_op_id(0)] ==
          state.attention_plan_id_for_operation[attention_op_id(1)]);
  REQUIRE(state.attention_plan_operation_count[attention_plan_id(0)] == n_layers);
  state.resize(n_q_tokens);  // Ensure capacity for q tokens
  state.pages.items = std::span<page_t* const>(pages);
  indexed_vector<token_job_id, token_id> test_token_jobs;
  for (size_t i = 0; i < n_q_tokens; ++i)
    test_token_jobs.push_back(token_id(first_q_token + i));
  state.token_jobs = test_token_jobs;
  // Attention path stats: open the forward before the first apply_page_range,
  // as production does (begin_forward sizes the per-token vectors). With the
  // switch off the object does nothing.
  std::optional<attn_stats::forward_scope> stats_scope;
  stats_scope.emplace(*state.self_attn_state.stats,
      attn_stats::forward_class::decode_like, state.token_jobs.size(),
      state.token_jobs.size());
  // Initialize token_positions for sliding window attention
  std::vector<uint32_t> positions(num_kv_tokens);
  for (size_t i = 0; i < num_kv_tokens; ++i)
    positions[i] = i;
  state.token_positions.items = std::span<const uint32_t>(positions);

  // Build a ranged mask encoding the visibility for this test.
  // Every query except the last can see entries at
  // positions <= first_q_token+q. So as entry position rises past a query's
  // position, that query drops out.
  ranged_mask mask;
  {
    mask_t<ranged_mask_capacity> sw{};
    for (size_t q = 0; q < n_q_tokens - 1; ++q)
      sw.insert(q);
    if constexpr (split_queries) {
      // [0, first_q_token+1): all but the last query are visible.
      mask.add_range(
          token_id(0), token_id(first_q_token + 1), sw, mask_t<ranged_mask_capacity>{});
    } else {
      const size_t hw_tokens = (num_pages - 1) * page_t::page_size;
      mask.add_range(token_id(0), token_id(hw_tokens), {}, sw);
      mask.add_range(token_id(hw_tokens), token_id(first_q_token + 1), sw, {});
    }
    // Each subsequent position drops the lowest remaining query.
    for (size_t q = 0; q < n_q_tokens - 1; ++q) {
      sw.erase(q);
      mask.add_range(token_id(first_q_token + q + 1), token_id(first_q_token + q + 2),
          sw, mask_t<ranged_mask_capacity>{});
    }
  }
  state.query_mask = &mask;

  // 4. Create a batch of tokens
  latch_arena latches;
  with_latch_arena latch_guard(latches);
  std::vector<token_job_id> q_batch_items(n_q_tokens, token_job_id(0));
  for (size_t i = 0; i < n_q_tokens; ++i)
    q_batch_items[i] = token_job_id(i);
  batch q_batch(state, std::move(q_batch_items), latches, 0);
  q_batch.plans.resize(state.attention_plan_profiles.size());
  // We don't use the channels, but the batch destructor requries they be initialized.
  q_batch.reset_channels(0, 0);
  // Operation numbering is independent of the cache slot. The attention helpers
  // must use the binding fields, not operation.i.
  const attention_operation_descriptor operation{
      {attention_op_id(1), model_layer_id(0), kv_slot_id(0)}, attention_kernel_id(0),
      attention_hardware_capability::software_only, true,
      attention_operation_config{std::nullopt, std::nullopt, operation_scale}};
  attention_plan_id plan_id =
      state.attention_plan_id_for_operation[operation.binding.operation];
  state.attention_runtime_configs[operation.binding.operation].sliding_window_size =
      sliding_window;
  auto& plan = q_batch.plans[plan_id];
  plan.n_sections = std::vector<size_t>(n_kv_heads, 2);
  plan.sections_left = std::vector<std::atomic_size_t>(n_kv_heads);

  // 5. Initialize the attention accumulators correctly, like in `forward`
  state.self_attn_state.free_scratchpads<geometry>(&q_batch, operation);

  // 6. Initialize `q` with random bf16s and store for validation
  random_qs.resize(n_q_tokens, std::vector<float>(n_heads * head_size));
  for (size_t tok = 0; tok < n_q_tokens; ++tok) {
    for (size_t elt = 0; elt < n_heads * head_size; ++elt) {
      state.plugin_state.qs_roped[token_job_id(tok)][elt] = static_cast<bf16>(dis(gen));
      random_qs[tok][elt] = state.plugin_state.qs_roped[token_job_id(tok)][elt];
    }
  }

  // Excluded rows must not resolve K, even when the book has no active KV slots.
  {
    book_t empty_cache(1, 0);
    auto* empty_page = empty_cache.page_of(0);
    empty_page->set_lo(0, 0);
    for (size_t i = 0; i < page_t::page_size; ++i)
      empty_cache.increment_tokens_used();
    empty_page->set_offset_bound(page_t::page_size);
    // The first query can still see this page in larger minibatches. Select
    // the last query so a one-token window excludes every entry in the page.
    const token_job_id excluded_job(n_q_tokens - 1);
    const token_id excluded_token = state.token_jobs[excluded_job];
    REQUIRE(state.token_positions[excluded_token] >= page_t::page_size);
    auto scratch =
        state.self_attn_state.token_scratchpad_ref_at<geometry>(0, n_q_tokens - 1);
    auto const q = state.plugin_state.qs_roped[excluded_job].as_view();
    for (bool window_excludes_all : {false, true}) {
      INFO("window_excludes_all=" << window_excludes_all);
      ranged_mask excluded;
      mask_t<ranged_mask_capacity> visible{};
      visible.insert(excluded_job.i);
      excluded.add_range(token_id(0), token_id(page_t::page_size),
          window_excludes_all ? visible : mask_t<ranged_mask_capacity>{},
          window_excludes_all ? mask_t<ranged_mask_capacity>{} : visible);
      state.query_mask = &excluded;
      auto const result = state.self_attn_state.apply_page_tok<geometry>(false,
          *empty_page, operation, operation_scale, 0, q, excluded_token, scratch,
          excluded_job, &excluded.find_range(token_id(0)),
          window_excludes_all ? 1 : 1024, window_excludes_all, nullptr);
      REQUIRE(result.relevant_k_tokens == 0);
      REQUIRE(result.served == tron::attn_stats::visit_path::empty);
    }
    state.query_mask = &mask;
  }

  // 7. Manually apply `apply_page_range` to an index range referring to all the pages
  state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
      state.plugin_state.qs_roped, 0, 0, 1, std::span(page_ixs.begin(), page_ixs.end()),
      {}, q_batch.items_mask, uses_hw);
  // The state's own attention path stats object follows TRON_ATTN_STATS (unset
  // in CTest, set in the switch-on run): rows exist exactly when it is on, and
  // the production call above ran with that setting.
  CHECK(state.self_attn_state.stats->enabled == tron::attn_stats::env_enabled());
  CHECK(state.self_attn_state.stats->rows.empty() == !tron::attn_stats::env_enabled());
  CHECK(state.self_attn_state.stats->n_layers == n_layers);

  // 8. Save the results. Heap-allocated because attn_accum's parallel arrays
  // are sized by max_minibatch_size; stack-copying them overflows the stack.
  auto v_stars_saved =
      std::make_unique<decltype(state.self_attn_state.attn[0].v_stars)>(
          state.self_attn_state.attn[0].v_stars);
  auto s_stars_saved =
      std::make_unique<decltype(state.self_attn_state.attn[0].s_stars)>(
          state.self_attn_state.attn[0].s_stars);
  auto m_stars_saved =
      std::make_unique<decltype(state.self_attn_state.attn[0].m_stars)>(
          state.self_attn_state.attn[0].m_stars);

  // Compare small batches with attention emulation. Larger query splits
  // compare with the unsplit page reduction saved above.
  if constexpr (!split_queries) {
    // Create mask from ranged mask (the single source of visibility truth).
    std::vector<std::vector<bool>> vis(
        n_q_tokens, std::vector<bool>(num_kv_tokens, false));
    const token_range* hint = &state.query_mask->find_range(token_id(0));
    for (size_t kv_token = 0; kv_token < num_kv_tokens; ++kv_token) {
      hint = &state.query_mask->find_range(token_id(kv_token), *hint);
      for (size_t q_token = 0; q_token < n_q_tokens; ++q_token) {
        vis[q_token][kv_token] =
            (uses_hw ? hint->sw_required(token_job_id(q_token))
                     : hint->visible(token_job_id(q_token))) &&
            static_cast<int>(first_q_token + q_token) - static_cast<int>(kv_token) <
                sliding_window;
      }
    }

    // Run reference implementation
    for (auto algorithm :
        {emulation::sume_algorithm::ONE_PASS, emulation::sume_algorithm::TWO_PASS}) {
      auto ref_outputs = emulation::compute_attention(random_qs, random_ks, random_vs,
          vis, 2, 1, head_size, algorithm, operation_scale);

      // Compare results for kv_head 0
      for (size_t tok = 0; tok < n_q_tokens; ++tok) {
        // The given apply_page_range only did kv_head 0
        for (size_t head = 0; head < kv_mul; ++head) {
          REQUIRE_THAT((*s_stars_saved)[tok][head],
              Catch::Matchers::WithinRel(ref_outputs.sume[tok][head], 1e-5f));
          if (tok < n_q_tokens - 1) {
            REQUIRE_THAT((*m_stars_saved)[tok][head],
                Catch::Matchers::WithinRel(ref_outputs.smax[tok][head], 1e-5f));
          } else {
            // m_star ends up being 0 due to being unwritten, so we just check
            // the reference here.
            REQUIRE(ref_outputs.smax[tok][head] == -1.0 / 0.0);
          }
        }
        assert_allclose(slice<2 * head_size>()((*v_stars_saved)[tok].as_view(), 0),
            ref_outputs.v_star[tok],
            /*absolute tolerance*/ 1e-2f,
            /*relative tolerance*/ 2e-2f);
      }
    }
  }

  // 10. Reinitialize
  state.self_attn_state.free_scratchpads<geometry>(&q_batch, operation);

  // 11. Manually repeat that computation, but split the range into two, and use two
  // `apply_page_range` and then `join_page_ranges`.
  state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
      state.plugin_state.qs_roped, 0, 0, 2,
      std::span(page_ixs.begin(), page_ixs.begin() + num_pages / 2), {},
      q_batch.items_mask, uses_hw);
  state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
      state.plugin_state.qs_roped, 0, 1, 2,
      std::span(page_ixs.begin() + num_pages / 2, page_ixs.end()), {},
      q_batch.items_mask, uses_hw);
  for (size_t i = 0; i < q_batch.items.size(); ++i) {
    auto target = state.self_attn_state.token_scratchpad_ref_at<geometry>(0, i);
    auto source = state.self_attn_state.token_scratchpad_ref_at<geometry>(1, i);
    state.self_attn_state.join_page_ranges(target, source, 0);
  }

  // 12. Check that the results for kv head 0 are the same up to a floating-point
  // tolerance. The two runs reach a token's page with a different running
  // maximum m. So each softmax weight exp(s - m) is converted to bf16 for the
  // PV product (truncated on the AVX path, rounded to nearest even on the AMX
  // path; Note [AMX attention dispatch] in amx_attn_iface.hpp) at a different
  // scale. One conversion step is up to 2^-7 of the weight (truncation). With a
  // 32-token window that moves one element of the weighted V sum by up to
  // about 0.02 (measured 0.018 with row-major K and 0.022 with VNNI K, whose
  // scores differ in the last bits). s_star adds the fp32 weights and differs
  // by a few ulp only. The bounds follow the K layout. Row-major K: 0.02 on an
  // element of the weighted V sum and an absolute 2e-6 on s_star. The VNNI
  // layout (Note [K VNNI storage] in kv_cache.hpp): 0.05 and a relative 1e-6,
  // a few ulp of s_star at any magnitude.
  constexpr double v_star_tolerance = k_vnni::layout_on<head_size> ? 5e-2 : 2e-2;
  auto check_kv_head_0_against_saved = [&] {
    for (size_t tok = 0; tok < q_batch.items.size(); ++tok) {
      for (size_t head = 0; head < kv_mul; ++head) {
        if constexpr (k_vnni::layout_on<head_size>) {
          REQUIRE_THAT(state.self_attn_state.attn[0].s_stars[tok][head],
              Catch::Matchers::WithinRel((*s_stars_saved)[tok][head], 1e-6f));
        } else {
          REQUIRE_THAT(state.self_attn_state.attn[0].s_stars[tok][head],
              Catch::Matchers::WithinAbs((*s_stars_saved)[tok][head], 2e-6f));
        }
        REQUIRE_THAT(state.self_attn_state.attn[0].m_stars[tok][head],
            Catch::Matchers::WithinRel((*m_stars_saved)[tok][head], 1e-6f));
      }
      assert_allclose(slice<kv_mul * head_size>()(
                          state.self_attn_state.attn[0].v_stars[tok].as_view(), 0),
          slice<kv_mul * head_size>()((*v_stars_saved)[tok].as_view(), 0),
          v_star_tolerance);
    }
  };
  check_kv_head_0_against_saved();

  if constexpr (split_queries) {
    // Splitting the query dimension must keep every query's full page reduction
    // and section-completion accounting intact. Reverse batch order so query
    // bounds are batch positions, not token job IDs, and the no-work query makes
    // the relevant range start after position zero.
    std::reverse(q_batch.items.begin(), q_batch.items.end());
    constexpr size_t n_workers = 4;
    state.self_attn_state.attn.resize(
        std::max(state.self_attn_state.attn.size(), n_workers));
    if (state.self_attn_state.attn.size() > state.self_attn_state.stats->n_workers) {
      // The grown scratchpad vector needs rows for its new workers: close the
      // forward, rebuild the stats object for the new size, reopen the forward.
      auto const& old_stats = *state.self_attn_state.stats;
      const bool was_enabled = old_stats.enabled;
      const std::string model_id = old_stats.model_id;
      const bool is_eagle = old_stats.is_eagle;
      const attn_stats::header_facts facts = old_stats.facts;
      const size_t n_layers_kept = old_stats.n_layers;
      stats_scope.reset();
      state.self_attn_state.stats =
          std::make_shared<attn_stats::model_stats>(was_enabled, model_id, is_eagle,
              facts, state.self_attn_state.attn.size(), n_layers_kept);
      stats_scope.emplace(*state.self_attn_state.stats,
          attn_stats::forward_class::decode_like, state.token_jobs.size(),
          state.token_jobs.size());
    }
    for (bool pending : {false, true}) {
      std::array<std::vector<page_id>, 2> batch_pages;
      batch_pages[pending] = page_ixs;
      std::array<std::vector<work_estimate_t>, 2> page_work;
      std::array<std::vector<std::pair<uint32_t, uint32_t>>, 2> page_qrange;
      work_estimate_t total;
      // Only KV head 0 is computed in this fixture.
      state.estimate_work(q_batch.items, batch_pages, page_work, page_qrange, total,
          sliding_window, kv_mul, 1, false);

      auto prepare_plan = [&] {
        plan.ready_kv_plan = {};
        plan.pending_kv_plan = {};
        plan.ready_kv_plan.resize(n_workers);
        plan.pending_kv_plan.resize(n_workers);
        plan.n_sections.assign(n_kv_heads, 0);
        auto& kv_plan = pending ? plan.pending_kv_plan : plan.ready_kv_plan;
        // Hardware-covered context leaves zero-work sections in the plan for
        // join-worker accounting. It must not absorb the next productive page.
        REQUIRE(kv_plan.assign_page(0, 0, page_ixs[0], {}, 0, 0));
        ++plan.n_sections[0];
        for (size_t p = 0; p < page_ixs.size(); ++p) {
          const auto [begin, end] = page_qrange[pending][p];
          if (kv_plan.assign_page(
                  2 * p, 0, page_ixs[p], page_work[pending][p], begin, end))
            ++plan.n_sections[0];
        }
      };

      for (size_t cap : {0, 1, 3, 16}) {
        CAPTURE(pending, cap);
        prepare_plan();
        state.split_sections_by_query(&q_batch, plan, {0.25f, 0.5f, 0.75f, 1.0f}, cap);
        if (cap < 2)
          REQUIRE(plan.n_sections[0] == num_pages + 1);
        else
          REQUIRE(plan.n_sections[0] > num_pages + 1);

        // A query/page pair appears exactly once, including unequal slices and
        // caps greater than the worker count. Counting planned pairs detects
        // duplicates even when a duplicated normalized attention result agrees.
        std::array<std::array<size_t, num_pages>, n_q_tokens> visits{};
        work_estimate_t split_work;
        size_t section_count = 0;
        size_t active_workers = 0;
        auto& kv_plan = pending ? plan.pending_kv_plan : plan.ready_kv_plan;
        for (size_t worker = 0; worker < n_workers; ++worker) {
          bool has_queries = false;
          for (const auto& section : kv_plan[worker]) {
            REQUIRE(section.q_begin <= section.q_end);
            REQUIRE(section.q_end <= q_batch.items.size());
            ++section_count;
            split_work += section.work_estimate;
            has_queries |= section.q_begin < section.q_end;
            for (size_t q = section.q_begin; q < section.q_end; ++q)
              for (page_id p : section.page_ixs)
                ++visits[q][p.i];
          }
          active_workers += has_queries;
        }
        // Splitting must actually engage idle cores, not just create more
        // sections on the workers that already owned these pages.
        if (cap < 2)
          CHECK(active_workers == num_pages);
        else
          CHECK(active_workers > num_pages);
        CHECK(section_count == plan.n_sections[0]);
        CHECK(split_work.k_dot_products == total.k_dot_products);
        CHECK(split_work.scaled_vs == total.scaled_vs);
        for (size_t q = 0; q < n_q_tokens; ++q)
          for (size_t p = 0; p < num_pages; ++p)
            // Job 0 is at position 63 and cannot see the second page. The
            // reversed batch puts it last; its last job has no work anywhere.
            CHECK(visits[q][p] == (q == 0 || (p == 1 && q == n_q_tokens - 1) ||
                                              (p == 0 && sliding_window == 32 && q < 33)
                                          ? 0
                                          : 1));

        state.self_attn_state.free_scratchpads<geometry>(&q_batch, operation);
        for (size_t worker = 0; worker < n_workers; ++worker)
          state.self_attn_state.run_sections<geometry>(&q_batch, operation,
              state.plugin_state.qs_roped, worker, n_workers, false, pending);
        REQUIRE(plan.sections_left[0].load() == 0);
        for (size_t q = 0; q < n_q_tokens; ++q) {
          auto target = state.self_attn_state.token_scratchpad_ref_at<geometry>(0, q);
          for (size_t worker = 1; worker < n_workers; ++worker) {
            auto source =
                state.self_attn_state.token_scratchpad_ref_at<geometry>(worker, q);
            state.self_attn_state.join_page_ranges(target, source, 0);
          }
          REQUIRE(target.is_valid_for(0) == (q != 0));
          if (q == 0) continue;
          const size_t job = q_batch.items[q].i;
          for (size_t head = 0; head < kv_mul; ++head) {
            CHECK_THAT(state.self_attn_state.attn[0].s_stars[q][head],
                Catch::Matchers::WithinRel((*s_stars_saved)[job][head], 2e-6f));
            CHECK_THAT(state.self_attn_state.attn[0].m_stars[q][head],
                Catch::Matchers::WithinRel((*m_stars_saved)[job][head], 1e-6f));
          }
          // The bound of step 12: the bf16 truncation of the PV weights.
          assert_allclose(slice<kv_mul * head_size>()(
                              state.self_attn_state.attn[0].v_stars[q].as_view(), 0),
              slice<kv_mul * head_size>()((*v_stars_saved)[job].as_view(), 0),
              v_star_tolerance);
        }
      }

      // Idle workers are not necessarily faster: the split should be declined
      // when moving pieces to much slower workers cannot shorten this phase.
      prepare_plan();
      state.split_sections_by_query(&q_batch, plan, {0.49f, 0.5f, 0.99f, 1.0f}, 8);
      CHECK(plan.n_sections[0] == num_pages + 1);

      // Decline a small predicted saving that cannot cover worker arrival skew.
      auto prepare_single_page = [&] {
        prepare_plan();
        auto& kv_plan = pending ? plan.pending_kv_plan : plan.ready_kv_plan;
        kv_plan = {};
        kv_plan.resize(n_workers);
        const auto [begin, end] = page_qrange[pending][1];
        REQUIRE(
            kv_plan.assign_page(0, 0, page_ixs[1], page_work[pending][1], begin, end));
        plan.n_sections.assign(n_kv_heads, 0);
        plan.n_sections[0] = 1;
      };
      prepare_single_page();
      state.split_sections_by_query(&q_batch, plan, {0.42f, 0.62f, 0.81f, 1.0f}, 8);
      CHECK(plan.n_sections[0] == 1);

      // Two pieces already capture most of the benefit here. Spare workers
      // should not acquire extra sections for a nearly tied finish time.
      prepare_single_page();
      state.split_sections_by_query(&q_batch, plan, {0.25f, 0.41f, 0.59f, 1.0f}, 8);
      CHECK(plan.n_sections[0] == 2);
      auto& single_page_plan = pending ? plan.pending_kv_plan : plan.ready_kv_plan;
      CHECK(single_page_plan[0].size() == 1);
      CHECK(single_page_plan[3].size() == 1);

      // An already balanced phase should not pay additional section setup costs.
      prepare_plan();
      auto& kv_plan = pending ? plan.pending_kv_plan : plan.ready_kv_plan;
      for (size_t worker : {1, 3}) {
        const auto [begin, end] = page_qrange[pending][0];
        if (kv_plan.assign_page(
                worker, worker, page_ixs[0], page_work[pending][0], begin, end))
          ++plan.n_sections[worker];
      }
      state.split_sections_by_query(&q_batch, plan, {0.25f, 0.5f, 0.75f, 1.0f}, 8);
      CHECK(plan.n_sections[0] == num_pages + 1);
      CHECK(plan.n_sections[1] == 1);
      CHECK(plan.n_sections[3] == 1);
    }
    return;
  }

  // 13. The streaming hardware join folds a device's passes into the first
  // pass's scratchpad and adopts that accumulator into worker 0's scratchpad.
  // See Note [Streaming hardware attention join]. Stage the two page halves as
  // two "hardware pass" partials and check both fold shapes.
  auto& hw_attn = state.self_attn_state.hw_attn;
  while (hw_attn.size() < 2)
    hw_attn.emplace_back();
  state.self_attn_state.free_scratchpads<geometry>(&q_batch, operation);
  state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
      state.plugin_state.qs_roped, 0, 0, 2,
      std::span(page_ixs.begin(), page_ixs.begin() + num_pages / 2), {},
      q_batch.items_mask, uses_hw);
  state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
      state.plugin_state.qs_roped, 0, 1, 2,
      std::span(page_ixs.begin() + num_pages / 2, page_ixs.end()), {},
      q_batch.items_mask, uses_hw);
  // Copy kv head 0 of a software scratchpad into a hardware pass scratchpad.
  auto stage_as_hw_pass = [&](size_t worker, hw_scratchpad_id pass) {
    for (size_t i = 0; i < q_batch.items.size(); ++i) {
      auto source = state.self_attn_state.token_scratchpad_ref_at<geometry>(worker, i);
      auto dest = state.self_attn_state.hw_token_scratchpad_ref_at(pass, i);
      if (!source.is_valid_for(0)) continue;
      dest.mark_valid_for(0);
      for (size_t head = 0; head < kv_mul; ++head) {
        dest[head].v_star.set(source[head].v_star * 1.0f);
        dest[head].s_star = source[head].s_star;
        dest[head].m_star = source[head].m_star;
      }
    }
  };
  stage_as_hw_pass(0, hw_scratchpad_id(0));
  stage_as_hw_pass(1, hw_scratchpad_id(1));

  // Flat fold, as before streaming: adopt pass 0 into the empty worker-0
  // scratchpad, then fold pass 1.
  state.self_attn_state.attn[0].clear_validity(q_batch.items.size());
  for (size_t i = 0; i < q_batch.items.size(); ++i) {
    auto target = state.self_attn_state.token_scratchpad_ref_at<geometry>(0, i);
    auto pass0 =
        state.self_attn_state.hw_token_scratchpad_ref_at(hw_scratchpad_id(0), i);
    auto pass1 =
        state.self_attn_state.hw_token_scratchpad_ref_at(hw_scratchpad_id(1), i);
    state.self_attn_state.join_page_ranges(target, pass0, 0);
    state.self_attn_state.join_page_ranges(target, pass1, 0);
  }
  check_kv_head_0_against_saved();
  std::vector<std::vector<float>> flat_s(n_q_tokens, std::vector<float>(kv_mul));
  std::vector<std::vector<float>> flat_m(n_q_tokens, std::vector<float>(kv_mul));
  std::vector<std::vector<float>> flat_v(
      n_q_tokens, std::vector<float>(kv_mul * head_size));
  for (size_t tok = 0; tok < n_q_tokens; ++tok) {
    for (size_t head = 0; head < kv_mul; ++head) {
      flat_s[tok][head] = state.self_attn_state.attn[0].s_stars[tok][head];
      flat_m[tok][head] = state.self_attn_state.attn[0].m_stars[tok][head];
    }
    auto v = slice<kv_mul * head_size>()(
        state.self_attn_state.attn[0].v_stars[tok].as_view(), 0);
    for (size_t elt = 0; elt < kv_mul * head_size; ++elt)
      flat_v[tok][elt] = v[elt];
  }

  // Exercise the real streaming join on one and two devices, including strided
  // ownership and workers with no jobs. These folds preserve the flat result.
  auto& workload = q_batch.hw_plan;
  const uint64_t generation =
      hw_attention_completion_generation(operation.binding.operation);
  auto prepare_passes = [&](bool delayed) {
    workload.resize(delayed ? 3 : 2);
    while (hw_attn.size() < workload.passes.size())
      hw_attn.emplace_back();
    state.self_attn_state.free_scratchpads<geometry>(&q_batch, operation);
    state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
        state.plugin_state.qs_roped, 0, 0, 2,
        std::span(page_ixs.begin(), page_ixs.begin() + num_pages / 2), {},
        q_batch.items_mask, uses_hw);
    state.self_attn_state.apply_page_range<geometry>(q_batch.items, operation,
        state.plugin_state.qs_roped, 0, 1, 2,
        std::span(page_ixs.begin() + num_pages / 2, page_ixs.end()), {},
        q_batch.items_mask, uses_hw);
    stage_as_hw_pass(0, hw_scratchpad_id(0));
    stage_as_hw_pass(1, hw_scratchpad_id(1));
    state.self_attn_state.attn[0].clear_validity(q_batch.items.size());
    for (size_t pi = 0; pi < workload.passes.size(); ++pi) {
      auto& pass = workload.passes[pi];
      pass.dev = nullptr;
      pass.scratchpad_ix = hw_scratchpad_id(pi);
      pass.physical_subpasses = 1;
      pass.queries.clear();
      for (size_t b = 0; b < q_batch.items.size(); ++b) {
        // The final query has no visible KV, so an identity partial on its own
        // pass gives it a different completion dependency without changing O.
        if (delayed && ((pi == 2) != (b == n_q_tokens - 1))) continue;
        pass.queries.push_back(hw_query{q_batch.items[b], 0, b});
        hw_attn[pi].unpack_state[b].store(2, std::memory_order_release);
      }
      // Previous-operation completion must not release this operation's join.
      workload.complete[pi].store(
          delayed && pi < 2 ? generation - 1 : generation, std::memory_order_release);
    }
    workload.index_passes_by_job(std::span<const token_job_id>(q_batch.items));
    state.self_attn_state.plan_for(&q_batch, operation.binding.operation)
        .sections_left[0] = 0;
  };
  auto check_streamed_result = [&] {
    check_kv_head_0_against_saved();
    for (size_t tok = 0; tok < n_q_tokens; ++tok) {
      for (size_t head = 0; head < kv_mul; ++head) {
        CHECK(state.self_attn_state.attn[0].s_stars[tok][head] == flat_s[tok][head]);
        CHECK(state.self_attn_state.attn[0].m_stars[tok][head] == flat_m[tok][head]);
      }
      auto v = slice<kv_mul * head_size>()(
          state.self_attn_state.attn[0].v_stars[tok].as_view(), 0);
      for (size_t elt = 0; elt < kv_mul * head_size; ++elt)
        CHECK(float(v[elt]) == flat_v[tok][elt]);
    }
  };
  for (auto [n_join_workers, multiple_devices] : std::array{std::pair{size_t{1}, false},
           std::pair{size_t{3}, true}, std::pair{n_q_tokens + 1, false}}) {
    CAPTURE(n_join_workers, multiple_devices);
    prepare_passes(false);
    alignas(64) std::byte other_device[64];
    if (multiple_devices) {
      workload.passes[1].dev = reinterpret_cast<::PosDevice*>(other_device);
      workload.index_passes_by_job(std::span<const token_job_id>(q_batch.items));
    }
    std::vector<size_t> finish_count(n_q_tokens);
    auto finish_job = [&](size_t batch_job_ix) { ++finish_count[batch_job_ix]; };
    // Inside stream_hw_joins, T5 (join_wait_cycles) counts only its wait
    // loop, which a sweep that made progress never enters: every pass is
    // complete here, so no wait.
    uint64_t join_wait_cycles = 0;
    for (size_t rank = 0; rank < n_join_workers; ++rank)
      state.self_attn_state.stream_hw_joins(&q_batch, operation.binding.operation,
          /*kv_head=*/0, rank, n_join_workers, /*n_attn_workers=*/1, finish_job,
          &join_wait_cycles);
    CHECK(finish_count == std::vector<size_t>(n_q_tokens, 1));
    CHECK(join_wait_cycles == 0);
    check_streamed_result();
  }

  // A ready job must finish while an earlier job waits on hardware or on
  // another worker's decode. Finishing the ready job releases that dependency.
  // A bounded watchdog makes blocking fail instead of hanging the suite.
  for (bool pending_decode : {false, true}) {
    CAPTURE(pending_decode);
    prepare_passes(true);
    alignas(64) std::byte ready_device[64];
    workload.passes[2].dev = reinterpret_cast<::PosDevice*>(ready_device);
    workload.index_passes_by_job(std::span<const token_job_id>(q_batch.items));
    if (pending_decode) {
      for (size_t pi = 0; pi < 2; ++pi)
        workload.complete[pi].store(generation, std::memory_order_release);
      hw_attn[0].unpack_state[0].store(1, std::memory_order_release);
    }
    std::mutex release_mutex;
    std::condition_variable release_cv;
    bool released = false;
    bool timed_out = false;
    auto release_passes = [&] {
      hw_attn[0].unpack_state[0].store(2, std::memory_order_release);
      for (size_t pi = 0; pi < 2; ++pi)
        workload.complete[pi].store(generation, std::memory_order_release);
    };
    std::jthread watchdog([&] {
      std::unique_lock lock(release_mutex);
      if (!release_cv.wait_for(
              lock, std::chrono::seconds(2), [&] { return released; })) {
        timed_out = true;
        release_passes();
      }
    });
    std::vector<size_t> finished;
    auto finish_job = [&](size_t batch_job_ix) {
      finished.push_back(batch_job_ix);
      if (batch_job_ix != n_q_tokens - 1) return;
      {
        std::lock_guard lock(release_mutex);
        released = true;
        release_passes();
      }
      release_cv.notify_one();
    };
    // The ready job finishes in the first sweep and releases the rest, so the
    // join makes progress on every sweep and T5 stays 0: no blocking wait.
    uint64_t join_wait_cycles = 0;
    state.self_attn_state.stream_hw_joins(&q_batch, operation.binding.operation,
        /*kv_head=*/0, /*rank=*/0, /*n_join_workers=*/1, /*n_attn_workers=*/1,
        finish_job, &join_wait_cycles);
    watchdog.join();
    CHECK_FALSE(timed_out);
    CHECK(join_wait_cycles == 0);
    REQUIRE(finished.size() == n_q_tokens);
    CHECK(finished.front() != 0);
    if (!pending_decode) CHECK(finished.front() == n_q_tokens - 1);
    std::sort(finished.begin(), finished.end());
    for (size_t b = 0; b < n_q_tokens; ++b)
      CHECK(finished[b] == b);
    check_streamed_result();
  }
  workload.clear();
}

TEST_CASE("apply and join page ranges", "[page_range]") {
  SECTION("page splits match emulation") {
    const bool uses_hw = GENERATE(false, true);
    if (uses_hw)
      check_page_range_reductions<8, false, true>(std::numeric_limits<int>::max());
    else
      check_page_range_reductions<8, false>(std::numeric_limits<int>::max());
  }
  SECTION("query splits match unsplit page reductions") {
    const int sliding_window = GENERATE(std::numeric_limits<int>::max(), 32);
    check_page_range_reductions<65, true>(sliding_window);
  }
}

// book::try_create — the fallible KV-book factory (memory_pressure_governor
// §8). The public ctor aborts on a payload-DMA OOM; try_create returns nullptr instead.
// Driven host-side via the fault seam (see Note [DMA fault injection seam],
// system/memory.hpp), which is also the mechanism the §10.6 acceptance test
// arms under load.
TEST_CASE("book::try_create returns null on injected DMA failure",
    "[kv_data][try_create][fault_seam]") {
  static constexpr size_t head_size = 64;
  static constexpr size_t n_layers = 2;
  static constexpr size_t n_kv_heads = 4;
  using book_t = book<n_layers, n_kv_heads, head_size, 0>;

  test_seam::clear_dma_fault();  // start from a known-disarmed state
  const int64_t baseline = pos_heap_active_allocations();

  CHECK(book_t::try_create(std::numeric_limits<size_t>::max()) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  // Unarmed: a normal book allocates its payload and is non-null.
  {
    auto bk = book_t::try_create(2);
    REQUIRE(bk != nullptr);
    CHECK(pos_heap_active_allocations() > baseline);  // payload is live
  }
  CHECK(pos_heap_active_allocations() == baseline);  // freed on drop

  // Armed for the next allocation: the single kv_blocks alloc fails, so
  // try_create returns null and commits/leaks nothing.
  test_seam::arm_dma_fault(0);
  CHECK(book_t::try_create(2) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  // One-shot: the seam disarmed itself, so the next try_create succeeds.
  CHECK(book_t::try_create(2) != nullptr);
  CHECK(pos_heap_active_allocations() == baseline);

  // EAGLE book: two DMA allocations (kv_blocks, then the x buffer). Arm the
  // SECOND so kv_blocks succeeds first — try_create must free that live buffer
  // before returning null (kv_cache.hpp: "kv_blocks frees on scope exit").
  using ebook_t = book<n_layers, n_kv_heads, head_size, 16>;
  test_seam::arm_dma_fault(1);
  constexpr size_t eagle_storage_slots =
      ebook_t::storage_slot_count_for_layers(n_layers, true);
  CHECK(ebook_t::try_create(2, eagle_storage_slots, /*support_eagle=*/true) == nullptr);
  CHECK(pos_heap_active_allocations() == baseline);  // first buffer was freed

  test_seam::clear_dma_fault();  // leave the process-global seam disarmed
}

TEST_CASE("book.append()", "[book append]") {
  static constexpr size_t head_size = 128;
  static constexpr size_t n_layers = 2;
  static constexpr size_t n_kv_heads = 4;
  static constexpr size_t x_bytes = 0;  // unused
  using book_t = book<n_layers, n_kv_heads, head_size, x_bytes>;
  using page_t = book_t::page_t;

  // Create random test data
  std::mt19937 gen(42);
  std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
  auto random_bf16 = [&]() { return static_cast<bf16>(dis(gen)); };

  SECTION("append books of different sizes") {
    // Test different combinations of source and destination sizes
    // to exercise different even/odd copy cases
    auto test_sizes = GENERATE(std::make_tuple(3, 5),  // dst_tokens=3, src_tokens=5
        std::make_tuple(4, 4),                         // even to even
        std::make_tuple(3, 4),                         // odd to even
        std::make_tuple(4, 3),                         // even to odd
        std::make_tuple(5, 3)                          // odd to odd
    );
    spdlog::info("Testing append of {} + {} tokens", std::get<0>(test_sizes),
        std::get<1>(test_sizes));
    const size_t dst_tokens = std::get<0>(test_sizes);
    const size_t src_tokens = std::get<1>(test_sizes);

    // Create source, destination and expected books
    book_t dst_book(1);
    book_t src_book(1);
    book_t expected_book(1);

    // Fill destination book
    for (size_t tok = 0; tok < dst_tokens; ++tok) {
      dst_book.increment_tokens_used();
      expected_book.increment_tokens_used();
      auto& dst_page = *dst_book.page_of(tok);
      auto& expected_page = *expected_book.page_of(tok);
      for (size_t layer = 0; layer < n_layers; ++layer) {
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
          // Fill k data (set_k_row serves both K layouts, Note [K VNNI storage])
          alignas(64) std::array<bf16, head_size> k_row;
          for (size_t i = 0; i < head_size; ++i)
            k_row[i] = random_bf16();
          dst_page.set_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_source_row<head_size>(k_row.data()));
          expected_page.set_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_source_row<head_size>(k_row.data()));
          // Fill v data
          tensor<head_size> v;
          for (size_t i = 0; i < head_size; ++i)
            v[i] = random_bf16();
          dst_page.set_v(test_kv_slot<book_t>(layer), kv_head, tok % page_t::page_size,
              v_source_row<head_size>(v.data.data()));
          expected_page.set_v(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, v_source_row<head_size>(v.data.data()));
          // Check get_v()
          tensor<head_size> gotten_v;
          expected_page.get_v(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, gotten_v.as_view());
          for (size_t i = 0; i < head_size; ++i)
            REQUIRE(gotten_v[i] == v[i]);
        }
      }
    }
    REQUIRE(dst_book.size() == dst_tokens);
    REQUIRE(expected_book.size() == dst_tokens);

    // Fill source book
    for (size_t tok = 0; tok < src_tokens; ++tok) {
      src_book.increment_tokens_used();
      expected_book.increment_tokens_used();
      auto& src_page = *src_book.page_of(tok);
      auto& expected_page = *expected_book.page_of(dst_tokens + tok);
      for (size_t layer = 0; layer < n_layers; ++layer) {
        kv_slot_id const slot = test_kv_slot<book_t>(layer);
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
          // Fill k data (set_k_row serves both K layouts, Note [K VNNI storage])
          alignas(64) std::array<bf16, head_size> k_row;
          for (size_t i = 0; i < head_size; ++i)
            k_row[i] = random_bf16();
          src_page.set_k_row(slot, kv_head, tok % page_t::page_size,
              k_source_row<head_size>(k_row.data()));
          expected_page.set_k_row(slot, kv_head, (dst_tokens + tok) % page_t::page_size,
              k_source_row<head_size>(k_row.data()));
          // Fill v data
          tensor<head_size> v;
          for (size_t i = 0; i < head_size; ++i)
            v[i] = random_bf16();
          src_page.set_v(slot, kv_head, tok % page_t::page_size,
              v_source_row<head_size>(v.data.data()));
          expected_page.set_v(slot, kv_head, (dst_tokens + tok) % page_t::page_size,
              v_source_row<head_size>(v.data.data()));
        }
        REQUIRE_FALSE(src_page.mark_k_complete(slot, tok % page_t::page_size));
        if (layer == 0)
          REQUIRE(src_page.mark_v_complete(slot, tok % page_t::page_size));
      }
    }
    REQUIRE(src_book.size() == src_tokens);
    REQUIRE(expected_book.size() == dst_tokens + src_tokens);

    // Perform the append operation
    dst_book.append(src_book);

    // Set offset_bound for pages so scaled_v works correctly
    for (size_t tok = 0; tok < dst_book.size(); tok += page_t::page_size) {
      size_t bound = std::min(page_t::page_size, dst_book.size() - tok);
      dst_book.page_of(tok)->set_offset_bound(bound);
    }
    for (size_t tok = 0; tok < expected_book.size(); tok += page_t::page_size) {
      size_t bound = std::min(page_t::page_size, expected_book.size() - tok);
      expected_book.page_of(tok)->set_offset_bound(bound);
    }

    // Check metadata
    REQUIRE(dst_book.size() == expected_book.size());
    for (size_t tok = 0; tok < src_tokens; ++tok) {
      auto& page = *dst_book.page_of(dst_tokens + tok);
      size_t const offset = (dst_tokens + tok) % page_t::page_size;
      REQUIRE(page.is_kv_complete(test_kv_slot<book_t>(0), offset));
      REQUIRE_FALSE(page.is_kv_complete(test_kv_slot<book_t>(1), offset));
      REQUIRE(page.mark_v_complete(test_kv_slot<book_t>(1), offset));
    }

    // Check k data
    for (size_t layer = 0; layer < n_layers; ++layer) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        for (size_t tok = 0; tok < expected_book.size(); ++tok) {
          alignas(64) std::array<bf16, head_size> actual_k, expected_k;
          dst_book.page_of(tok)->get_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_destination_row<head_size>(actual_k.data()));
          expected_book.page_of(tok)->get_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_destination_row<head_size>(expected_k.data()));
          for (size_t i = 0; i < head_size; ++i) {
            if (actual_k[i] != expected_k[i])
              spdlog::error("Mismatch at layer={}, kv_head={}, tok={}, i={}: "
                            "actual={}, expected={}",
                  layer, kv_head, tok, i, actual_k[i], expected_k[i]);
            REQUIRE(actual_k[i] == expected_k[i]);
          }
        }
      }
    }

    // Check v data using scaled_v
    tensor<page_t::page_size> scales;
    tensor<head_size> actual_v;
    tensor<head_size> expected_v;
    tensor<head_size> scratch;
    for (size_t layer = 0; layer < n_layers; ++layer) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        for (size_t tok = 0; tok < expected_book.size(); ++tok) {
          // Query v data via a one-hot probe for this page
          scales = constant<page_t::page_size>(0.0f);
          scales[tok] = 1.0f;
          actual_v = dst_book.page_of(tok)->scaled_v(
              test_kv_slot<book_t>(layer), kv_head, scales, scratch);
          expected_v = expected_book.page_of(tok)->scaled_v(
              test_kv_slot<book_t>(layer), kv_head, scales, scratch);
          for (size_t i = 0; i < head_size; ++i) {
            if (actual_v[i] != expected_v[i])
              spdlog::error("Mismatch at layer={}, kv_head={}, tok={}, i={}: "
                            "actual={}, expected={}",
                  layer, kv_head, tok, i, actual_v[i], expected_v[i]);
            REQUIRE(actual_v[i] == expected_v[i]);
          }
        }
      }
    }
  }
}

namespace {

// FP32 bits of FP16-exact inputs (set_input checks the round trip) and their BF16
// bits. FP32 bits 12..0 are zero, so the discarded bits step by 0x2000: 0x6000 is
// just below a tie and 0xa000 just above. FP16 subnormals such as 0x33800000 are
// FP32 normals, so they are not flushed; the largest, 0x387fc000, and FP16's largest
// finite value 0x477fe000 round up into the next binade. In the quiet NaN 0x7fc02000,
// bit 13 is a payload bit that FP16 keeps and BF16 drops.
constexpr std::array<bf16_rounding_case, 32> fp16_v_cases{{
    {0x00000000, 0x0000},
    {0x80000000, 0x8000},
    {0x3f806000, 0x3f80},
    {0x3f808000, 0x3f80},
    {0x3f80a000, 0x3f81},
    {0x3f816000, 0x3f81},
    {0x3f818000, 0x3f82},
    {0x3f81a000, 0x3f82},
    {0xbf806000, 0xbf80},
    {0xbf808000, 0xbf80},
    {0xbf80a000, 0xbf81},
    {0xbf816000, 0xbf81},
    {0xbf818000, 0xbf82},
    {0xbf81a000, 0xbf82},
    {0x3f810000, 0x3f81},
    {0xbf810000, 0xbf81},
    {0x3fffe000, 0x4000},
    {0xbfffe000, 0xc000},
    {0x477fe000, 0x4780},
    {0xc77fe000, 0xc780},
    {0x38800000, 0x3880},
    {0xb8800000, 0xb880},
    {0x33800000, 0x3380},
    {0xb3800000, 0xb380},
    {0x387fc000, 0x3880},
    {0xb87fc000, 0xb880},
    {0x7f800000, 0x7f80},
    {0xff800000, 0xff80},
    {0x7fc00000, 0x7fc0},
    {0xffc00000, 0xffc0},
    {0x7fc02000, 0x7fc0},
    {0xffc02000, 0xffc0},
}};

template <typename input_type>
void check_v_stores(std::span<const bf16_rounding_case> cases) {
  constexpr size_t head_size = 128;
  constexpr kv_geometry geometry{2, head_size};
  uniform_kv_cache<1, geometry, 0> cache(/*n_pages=*/1);
  cache.increment_tokens_used(4);
  auto* page = cache.page_of(0);
  page->set_offset_bound(4);

  std::array<std::array<std::array<uint16_t, head_size>, 4>, 2> expected{};
  alignas(64) std::array<float, head_size> readback{};
  alignas(64) std::array<input_type, head_size> input{};
  auto set_input = [&](size_t lane, uint32_t bits) {
    input[lane] = std::bit_cast<float>(bits);
    if constexpr (std::is_same_v<input_type, fp16>) {
      CAPTURE(lane);
      REQUIRE(std::bit_cast<uint32_t>(float(input[lane])) == bits);
    }
  };

  for (size_t head = 0; head < 2; ++head) {
    for (size_t token = 0; token < 4; ++token) {
      for (size_t lane = 0; lane < head_size; ++lane) {
        const uint16_t bits = uint16_t(0x3e00 + head * 0x400 + token * 0x80 + lane);
        expected[head][token][lane] = bits;
        set_input(lane, uint32_t(bits) << 16);
      }
      page->template set_v<geometry>(
          kv_slot_id(0), head, token, v_source_row<head_size>(input.data()));
    }
  }

  auto check_all = [&]() {
    for (size_t head = 0; head < 2; ++head) {
      for (size_t token = 0; token < 4; ++token) {
        page->template get_v<geometry>(
            kv_slot_id(0), head, token, v_destination_row<head_size>(readback.data()));
        for (size_t lane = 0; lane < head_size; ++lane) {
          CAPTURE(head, token, lane);
          REQUIRE(std::bit_cast<uint32_t>(readback[lane]) ==
                  (uint32_t(expected[head][token][lane]) << 16));
        }
      }
    }
  };
  check_all();

  auto write = [&](size_t token, size_t rotation) {
    for (size_t lane = 0; lane < head_size; ++lane) {
      const auto& test = cases[(lane + rotation + 3 * (lane / 16)) % cases.size()];
      set_input(lane, test.input);
      expected[0][token][lane] = test.expected;
    }
    if (token % 2 == 0) expected[0][token + 1].fill(0);
    page->template set_v<geometry>(
        kv_slot_id(0), 0, token, v_source_row<head_size>(input.data()));
    check_all();
  };

  // Even writes clear the odd partner; odd writes preserve the even token.
  write(0, 0);
  write(1, 5);
  write(1, 9);
  write(2, 3);
  write(3, 11);
  write(0, 7);
}

}  // namespace

TEST_CASE("float V stores round to BF16", "[kv_data][v-store]") {
  check_v_stores<float>(bf16_rounding_cases);
}

TEST_CASE("FP16 V stores round to BF16", "[kv_data][v-store]") {
  check_v_stores<fp16>(fp16_v_cases);
}

// See Note [Zero-Initialized V Slots]
//
// Regression tests for the zero-init V slot invariant.
// "append_v zeroes the poisoned partner" poisons the padding slot and verifies
// that the zero-init invariant (make_unique_dma + append_v zeroing the odd
// partner) prevents NaN propagation through _mm512_dpbf16_ps.
// "single-token dirty-buffer reuse" isolates the allocation invariant
// from the append_v invariant.
TEST_CASE("scaled_v padding NaN", "[kv_data]") {
  static constexpr size_t head_size = 128;
  static constexpr size_t n_layers = 2;
  static constexpr size_t n_kv_heads = 4;
  static constexpr size_t x_bytes = 0;
  using book_t = book<n_layers, n_kv_heads, head_size, x_bytes>;
  using page_t = book_t::page_t;

  std::mt19937 gen(42);
  std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
  auto random_bf16 = [&]() { return static_cast<bf16>(dis(gen)); };

  SECTION("append_v zeroes the poisoned partner") {
    // With 3 destination tokens the append's last copy lands on the even token
    // 6, so the even-destination rule must zero the poisoned token 7. The four
    // copy parities are compared bit for bit in the packed-bits case below.
    const size_t dst_tokens = 3;
    const size_t src_tokens = 4;

    book_t dst_book(1);
    book_t src_book(1);

    // Fill destination book with 3 tokens.
    for (size_t tok = 0; tok < dst_tokens; ++tok) {
      dst_book.increment_tokens_used();
      auto& dst_page = *dst_book.page_of(tok);
      for (size_t layer = 0; layer < n_layers; ++layer) {
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
          alignas(64) std::array<bf16, head_size> dst_k;
          for (size_t i = 0; i < head_size; ++i)
            dst_k[i] = random_bf16();
          dst_page.set_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_source_row<head_size>(dst_k.data()));
          tensor<head_size> v;
          for (size_t i = 0; i < head_size; ++i)
            v[i] = random_bf16();
          dst_page.set_v(test_kv_slot<book_t>(layer), kv_head, tok % page_t::page_size,
              v_source_row<head_size>(v.data.data()));
        }
      }
    }

    // Poison the padding slot (token index 7 = odd partner of token 6 in pair
    // 3).  After filling dst_tokens tokens, pair 3 is untouched by set_v. The
    // append's last copy (dst=6 from src=6-dst_tokens) must zero this NaN; an
    // even-destination copy that preserved the odd slot would leak it.
    {
      auto& dst_page = *dst_book.page_of(0);
      alignas(64) float nan_buf[head_size];
      std::fill(nan_buf, nan_buf + head_size, std::numeric_limits<float>::quiet_NaN());
      for (size_t layer = 0; layer < n_layers; ++layer)
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
          // Token 7 = dst_tokens + src_tokens: the padding token right after
          // the appended tokens.
          dst_page.set_v(test_kv_slot<book_t>(layer), kv_head, 7,
              v_source_row<head_size>(nan_buf));
    }

    // Fill source book with 4 tokens.
    for (size_t tok = 0; tok < src_tokens; ++tok) {
      src_book.increment_tokens_used();
      auto& src_page = *src_book.page_of(tok);
      for (size_t layer = 0; layer < n_layers; ++layer) {
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
          alignas(64) std::array<bf16, head_size> src_k;
          for (size_t i = 0; i < head_size; ++i)
            src_k[i] = random_bf16();
          src_page.set_k_row(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, k_source_row<head_size>(src_k.data()));
          tensor<head_size> v;
          for (size_t i = 0; i < head_size; ++i)
            v[i] = random_bf16();
          src_page.set_v(test_kv_slot<book_t>(layer), kv_head, tok % page_t::page_size,
              v_source_row<head_size>(v.data.data()));
        }
      }
    }

    // Append: produces 7-token page (odd count).
    dst_book.append(src_book);

    // Set offset_bound so scaled_v sees count=7.
    for (size_t tok = 0; tok < dst_book.size(); tok += page_t::page_size) {
      size_t bound = std::min(page_t::page_size, dst_book.size() - tok);
      dst_book.page_of(tok)->set_offset_bound(bound);
    }
    REQUIRE(dst_book.size() == 7);

    // Probe every valid token via one-hot scales.  scaled_v rounds
    // count=7 to 8, reading pair (6,7).  Token 7 holds the poisoned NaN.
    tensor<page_t::page_size> scales;
    tensor<head_size> actual_v;
    tensor<head_size> scratch;

    for (size_t layer = 0; layer < n_layers; ++layer) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        for (size_t tok = 0; tok < dst_book.size(); ++tok) {
          scales = constant<page_t::page_size>(0.0f);
          scales[tok] = 1.0f;
          actual_v = dst_book.page_of(tok)->scaled_v(
              test_kv_slot<book_t>(layer), kv_head, scales, scratch);
          for (size_t i = 0; i < head_size; ++i) {
            if (std::isnan(actual_v[i])) {
              spdlog::error("NaN at layer={}, kv_head={}, tok={}, i={}: "
                            "padding slot NaN propagated through scaled_v",
                  layer, kv_head, tok, i);
            }
            REQUIRE_FALSE(std::isnan(actual_v[i]));
          }
          // Verify value correctness: one-hot scaled_v must match get_v.
          // Prevents false passes from fixes that zero all V data.
          alignas(64) float expected_v[head_size];
          dst_book.page_of(tok)->get_v(test_kv_slot<book_t>(layer), kv_head,
              tok % page_t::page_size, v_destination_row<head_size>(expected_v));
          for (size_t i = 0; i < head_size; ++i) {
            if (actual_v[i] != expected_v[i])
              spdlog::error("Value mismatch at layer={}, kv_head={}, tok={}, "
                            "i={}: scaled_v={}, get_v={}",
                  layer, kv_head, tok, i, actual_v[i], expected_v[i]);
            REQUIRE(actual_v[i] == expected_v[i]);
          }
        }
      }
    }
  }

  // Isolates the allocation invariant from the append_v invariant:
  // poison slot 1 to simulate a dirty buffer, then write slot 0 via
  // set_v (which zeros the odd partner), then verify scaled_v with
  // count=1 produces no NaN and the correct value.
  SECTION("single-token dirty-buffer reuse") {
    book_t bk(1);
    bk.increment_tokens_used();
    page_t* p = bk.page_of(0);
    p->set_offset_bound(1);

    // Poison slot 1 (odd partner of slot 0 in v[0]) to simulate a
    // dirty buffer from pool reuse.
    {
      alignas(64) float nan_buf[head_size];
      std::fill(nan_buf, nan_buf + head_size, std::numeric_limits<float>::quiet_NaN());
      for (size_t layer = 0; layer < n_layers; ++layer)
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
          p->set_v(test_kv_slot<book_t>(layer), kv_head, 1,
              v_source_row<head_size>(nan_buf));
    }

    // Write 1 valid token at slot 0.  set_v(even=0) zeros the odd
    // partner via cvtepu16_epi32, overwriting the NaN poison above.
    for (size_t layer = 0; layer < n_layers; ++layer) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        tensor<head_size> v;
        for (size_t i = 0; i < head_size; ++i)
          v[i] = random_bf16();
        p->set_v(test_kv_slot<book_t>(layer), kv_head, 0,
            v_source_row<head_size>(v.data.data()));
      }
    }

    // scaled_v with count=1 rounds up to 2, reading pair (0,1).
    // Slot 1 was poisoned but set_v(even=0) zeroed it.
    tensor<page_t::page_size> scales;
    tensor<head_size> actual_v;
    tensor<head_size> scratch;
    for (size_t layer = 0; layer < n_layers; ++layer) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        scales = constant<page_t::page_size>(0.0f);
        scales[0] = 1.0f;
        actual_v = p->scaled_v(test_kv_slot<book_t>(layer), kv_head, scales, scratch);
        for (size_t i = 0; i < head_size; ++i) {
          if (std::isnan(actual_v[i]))
            spdlog::error("NaN at layer={}, kv_head={}, i={}: "
                          "dirty buffer NaN propagated through scaled_v",
                layer, kv_head, i);
          REQUIRE_FALSE(std::isnan(actual_v[i]));
        }
        alignas(64) float expected_v[head_size];
        p->get_v(test_kv_slot<book_t>(layer), kv_head, 0,
            v_destination_row<head_size>(expected_v));
        for (size_t i = 0; i < head_size; ++i) {
          if (actual_v[i] != expected_v[i])
            spdlog::error("Value mismatch at layer={}, kv_head={}, "
                          "i={}: scaled_v={}, get_v={}",
                layer, kv_head, i, actual_v[i], expected_v[i]);
          REQUIRE(actual_v[i] == expected_v[i]);
        }
      }
    }
  }
}

// Software attention must stay available for every accepted geometry, also
// with TRON_K_VNNI. A 128-dimension K/V head shared by 32 query heads is such
// a geometry: the AMX kernel does not take it (its group is 4 heads), and the
// VNNI reader scores it in passes of 16 heads (k_vnni::qk_group). This case
// instantiates apply_page_tok for that shape in both builds and runs it on a
// page whose query mask excludes every token (query 0 is hardware-visible and
// not software-required, so the call scores nothing). It is a compile check
// first. The reader's numbers for wide groups are checked in t_k_vnni_layout.
TEST_CASE(
    "software attention compiles for 32 query heads on one 128-dimension K/V head",
    "[kv_data][k_vnni]") {
  constexpr size_t head_size = 128;
  constexpr size_t n_heads = 32;
  constexpr size_t n_kv_heads = 1;
  constexpr float attention_scale = 0x1.6a09e6p-4f;  // 1 / sqrt(128)
  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};
  static_assert(geometry.kv_mul() == n_heads, "32 query heads share the K/V head");
  constexpr llm_configuration llm_config{.type = model_type::llama,
      .dim = n_heads * head_size,
      .hidden_dim = 1024,
      .n_layers = 1,
      .n_heads = n_heads,
      .n_kv_heads = n_kv_heads,
      .vocab_size = 32000,
      .head_size = head_size,
      .attention_scale = attention_scale,
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t =
      model<llm<llm_config, make_llm_executor<false, tensor, tensor, tensor>>>;
  using state_t = model_t::state;
  using book_t = model_t::book;
  using page_t = model_t::page;

  std::unique_ptr<model_t> model =
      std::make_unique<model_t>(std::filesystem::path{}, json(json::value_t::object));
  state_t state(*model, model_config{.max_layers = 1});
  state.resize(1);  // one query token
  book_t cache(1, 1);
  page_t* page = cache.page_of(0);
  page->set_lo(0, 0);
  for (size_t i = 0; i < page_t::page_size; ++i) {
    cache.increment_tokens_used();
  }
  page->set_offset_bound(page_t::page_size);
  // The page's tokens plus the query token (position page_size), as the
  // sliding-window check reads token positions.
  std::array<page_t*, 1> pages{page};
  state.pages.items = std::span<page_t* const>(pages);
  std::vector<uint32_t> positions(page_t::page_size + 1);
  for (size_t i = 0; i < positions.size(); ++i) {
    positions[i] = static_cast<uint32_t>(i);
  }
  state.token_positions.items = std::span<const uint32_t>(positions);
  indexed_vector<token_job_id, token_id> token_jobs;
  token_jobs.push_back(token_id(page_t::page_size));
  state.token_jobs = token_jobs;
  const attention_operation_descriptor operation{
      {attention_op_id(0), model_layer_id(0), kv_slot_id(0)}, attention_kernel_id(0),
      attention_hardware_capability::software_only, true,
      attention_operation_config{std::nullopt, std::nullopt, attention_scale}};
  // Query 0 is hardware-visible and not software-required for every token of
  // the page. So the software call skips every token and returns 0 relevant
  // tokens, in both K layouts.
  ranged_mask mask;
  mask_t<ranged_mask_capacity> hw_visible{};
  hw_visible.insert(0);
  mask.add_range(token_id(0), token_id(page_t::page_size),
      mask_t<ranged_mask_capacity>{}, hw_visible);
  state.query_mask = &mask;
  auto scratch = state.self_attn_state.token_scratchpad_ref_at<geometry>(0, 0);
  auto const q = state.plugin_state.qs_roped[token_job_id(0)].as_view();
  // Arguments as in check_page_range_reductions: not was_valid, sliding
  // window 1024, not run_visible_in_software.
  auto const result = state.self_attn_state.apply_page_tok<geometry>(false, *page,
      operation, attention_scale, 0, q, token_id(page_t::page_size), scratch,
      token_job_id(0), &mask.find_range(token_id(0)), 1024, false, nullptr);
  REQUIRE(result.relevant_k_tokens == 0);
  REQUIRE(result.served == tron::attn_stats::visit_path::empty);
}

// The K store of save_k (Note [Shared block save] in model.hpp): the grouping
// of a minibatch's tokens into page blocks, and the window that shares the
// store with helper threads. The shapes a pass can present are all here: a
// run that starts in the middle of a 16-token block, a run that crosses a
// block boundary and one that crosses a page boundary, a whole block, a
// token alone in its block, and jobs without KV work inside and after a run.
// Every stored row must equal its source row bit for bit. Every other row of
// the book must be untouched. With TRON_K_VNNI off the same test runs the
// row-major store. No window opens then.
TEST_CASE("save_k stores every token's K row once, grouped by page block, alone or "
          "with helper threads",
    "[kv_data][k_vnni]") {
  constexpr size_t head_size = 128;
  constexpr size_t n_heads = 16;
  constexpr size_t n_layers = 2;
  constexpr size_t n_kv_heads = 8;
  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};
  constexpr llm_configuration llm_config{.type = model_type::llama,
      .dim = head_size * n_heads,
      .hidden_dim = 1024,
      .n_layers = n_layers,
      .n_heads = n_heads,
      .n_kv_heads = n_kv_heads,
      .vocab_size = 32000,
      .head_size = head_size,
      .attention_scale = 0x1.6a09e6p-4f,  // 1 / sqrt(128)
      .n_experts = 1,
      .n_shared_experts = 1,
      .n_routed_experts_chosen = 0,
      .rope_scaling_strategy = rope_scaling::simple};
  using model_t =
      model<llm<llm_config, make_llm_executor<false, tensor, tensor, tensor>>>;
  using state_t = model_t::state;
  using book_t = model_t::book;
  using page_t = model_t::page;
  using batch = model_t::batch;

  std::unique_ptr<model_t> model =
      std::make_unique<model_t>(std::filesystem::path{}, json(json::value_t::object));
  constexpr size_t num_pages = 3;
  constexpr size_t num_kv_tokens = num_pages * page_t::page_size;
  std::mt19937 gen(23);
  book_t bk(num_pages, n_layers);
  std::vector<page_t*> pages;
  std::vector<page_t*> token_pages(num_kv_tokens);
  for (size_t i = 0; i < num_pages; ++i) {
    pages.push_back(bk.page_of(i * page_t::page_size));
    pages.back()->set_lo(0, i * page_t::page_size);
    for (size_t tok = 0; tok < page_t::page_size; ++tok) {
      bk.increment_tokens_used();
    }
    pages.back()->set_offset_bound(page_t::page_size);
  }
  for (size_t tok = 0; tok < num_kv_tokens; ++tok) {
    token_pages[tok] = bk.page_of(tok);
  }

  // The token jobs of the pass (token ids are the positions in the book).
  std::vector<token_id> job_tokens;
  std::vector<uint8_t> do_kv;
  auto add = [&](size_t tok, bool kv) {
    job_tokens.push_back(token_id(tok));
    do_kv.push_back(kv ? 1 : 0);
  };
  // The token runs of the pass (a page holds 64 tokens, a block 16 tokens).
  constexpr size_t kv_jobs = 46;  // 48 jobs minus the two without KV work
  // Tokens 5..20: starts mid-block, crosses blocks 0/1 of page 0. The job of
  // token 8 has no KV work.
  for (size_t tok = 5; tok < 21; ++tok) {
    add(tok, tok != 8);
  }
  // Tokens 48..63: one whole block (block 3 of page 0).
  for (size_t tok = 48; tok < 64; ++tok) {
    add(tok, true);
  }
  // Tokens 64..71: page crossing 63 -> 64, partial block 0 of page 1.
  for (size_t tok = 64; tok < 72; ++tok) {
    add(tok, true);
  }
  // Token 100: alone in block 2 of page 1. This case takes the per-token
  // scatter path.
  add(100, true);
  // Tokens 130..135: page 2.
  for (size_t tok = 130; tok < 136; ++tok) {
    add(tok, true);
  }
  add(21, false);  // a trailing job without KV work
  const size_t n_items = job_tokens.size();
  REQUIRE(n_items == 48);  // more than 16. So the window can open.

  state_t state(*model, model_config{.max_layers = n_layers});
  state.resize(n_items);
  state.pages.items = std::span<page_t* const>(pages);
  state.token_pages.items = std::span<page_t* const>(token_pages);
  indexed_vector<token_job_id, token_id> jobs;
  for (token_id t : job_tokens) {
    jobs.push_back(t);
  }
  state.token_jobs = jobs;
  state.token_jobs_do_kv.items = std::span<const uint8_t>(do_kv);
  // Finite bf16 patterns per (job, element). No two rows share a pattern. A row
  // stored at the wrong token position or in the wrong slot is then detected.
  // The bits are 0x3800 + (0..0x07ff): exponent field 0x70..0x7f, never 0xff.
  // The strides 4099 and 17 spread the (job, element) pairs over that span.
  auto source_bits = [](size_t job, size_t elt) {
    const size_t mix = job * 4099 + elt * 17;
    return static_cast<uint16_t>(0x3800u + mix % 0x0800u);
  };
  for (size_t job = 0; job < n_items; ++job) {
    for (size_t elt = 0; elt < n_kv_heads * head_size; ++elt) {
      state.plugin_state.kouts[token_job_id(job)][elt] =
          bf16::from_bits(source_bits(job, elt));
    }
  }

  latch_arena latches;
  with_latch_arena latch_guard(latches);
  std::vector<token_job_id> items;
  for (size_t i = 0; i < n_items; ++i) {
    items.push_back(token_job_id(i));
  }
  batch q_batch(state, std::move(items), latches, 0);
  q_batch.reset_channels(0, 0);
  // The active operation 0 of layer 0 (validate_operation compares the
  // descriptor with it).
  const attention_operation_descriptor operation = state.active_attention_operations[0];
  REQUIRE(operation.writes_kv);
  // Not const: the three-thread section moves it to the next operation's slot.
  // snapshot and check below read it by reference.
  kv_slot_id slot = operation.binding.kv_slot;

  // Snapshot of every K row of the slot, to prove the untouched rows stay.
  auto snapshot = [&] {
    std::vector<std::array<uint16_t, head_size>> rows(num_kv_tokens * n_kv_heads);
    alignas(64) std::array<bf16, head_size> row;
    for (size_t tok = 0; tok < num_kv_tokens; ++tok) {
      page_t* page = bk.page_of(tok);
      const int offset = page->offset_in_page(token_id(tok));
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        page->get_k_row(
            slot, kv_head, offset, k_destination_row<head_size>(row.data()));
        for (size_t d = 0; d < head_size; ++d) {
          rows[tok * n_kv_heads + kv_head][d] = row[d].to_bits();
        }
      }
    }
    return rows;
  };
  auto check = [&](std::vector<std::array<uint16_t, head_size>> const& before) {
    std::vector<int> job_of_token(num_kv_tokens, -1);  // -1: no job stores it
    for (size_t job = 0; job < n_items; ++job) {
      if (do_kv[job]) job_of_token[job_tokens[job].i] = static_cast<int>(job);
    }
    const auto after = snapshot();
    size_t stored = 0, kept = 0;
    for (size_t tok = 0; tok < num_kv_tokens; ++tok) {
      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {
        auto const& got = after[tok * n_kv_heads + kv_head];
        if (job_of_token[tok] < 0) {
          REQUIRE(got == before[tok * n_kv_heads + kv_head]);
          ++kept;
          continue;
        }
        const size_t job = static_cast<size_t>(job_of_token[tok]);
        for (size_t d = 0; d < head_size; ++d) {
          const uint16_t want = source_bits(job, kv_head * head_size + d);
          if (got[d] != want) {
            FAIL("token " << tok << " kv_head " << kv_head << " dim " << d
                          << ": stored 0x" << std::hex << got[d] << " expected 0x"
                          << want);
          }
        }
        ++stored;
      }
    }
    REQUIRE(stored == kv_jobs * n_kv_heads);
    REQUIRE(kept == (num_kv_tokens - kv_jobs) * n_kv_heads);
    // The marks: save_k marks K of every job with KV work exactly once. The
    // helpers leave before the mark loop. K alone does not complete a token.
    // The second mark completes it (mark_k_complete returns true only when
    // the count was 1). A job without KV work has no mark (count 0).
    for (size_t job = 0; job < n_items; ++job) {
      page_t* page = token_pages[job_tokens[job].i];
      const size_t offset = static_cast<size_t>(page->offset_in_page(job_tokens[job]));
      REQUIRE_FALSE(page->is_kv_complete(slot, offset));
      REQUIRE(page->mark_k_complete(slot, offset) == (do_kv[job] != 0));
    }
  };

  SECTION("one thread: the grouping stores every row and touches nothing else") {
    bk.fill_random(gen);
    const auto before = snapshot();
    state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);
    check(before);
    REQUIRE(q_batch.k_store_window.opened.load() == 0);
  }

  SECTION("three threads: the helpers share the window and every row is stored once") {
    bk.fill_random(gen);
    constexpr size_t n_workers = 3;
    constexpr size_t main_worker_ix = 0;
    // Every worker calls the same save_k with its own index (Note [Shared
    // block save] in model.hpp).
    auto shared_save = [&](attention_operation_descriptor const& op) {
      std::vector<std::thread> helpers;
      for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {
        helpers.emplace_back([&, worker_ix] {
          state.template save_k<geometry>(
              &q_batch, op, state.plugin_state.kouts, worker_ix, n_workers);
        });
      }
      state.template save_k<geometry>(
          &q_batch, op, state.plugin_state.kouts, main_worker_ix, n_workers);
      for (auto& h : helpers) {
        h.join();
      }
    };
    // The job's token position, its KV flag, its page and its 16-token block.
    auto token_of = [&](size_t item) { return job_tokens[q_batch.items[item].i].i; };
    auto kv_of = [&](size_t item) { return do_kv[q_batch.items[item].i] != 0; };
    auto block_of = [&](size_t tok) {
      return (tok % page_t::page_size) / k_vnni::BLOCK_TOKENS_16;
    };
    // The window state after the n_windows-th shared save on this batch.
    [[maybe_unused]] auto check_window = [&](uint32_t n_windows) {
      auto const& w = q_batch.k_store_window;
      REQUIRE(w.opened.load() == n_windows);
      REQUIRE(w.finished.load() == n_workers - 1);
      // Each helper counts the windows it entered in its own slot. A helper's
      // W-th call waits for the W-th window (Note [Shared block save]). That
      // count pairs the call with the window.
      for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {
        CAPTURE(worker_ix);
        REQUIRE(w.helper_windows[worker_ix] == n_windows);
      }
      // Every worker claims with fetch_add until a claim returns an index at
      // or past n_units. So each of the n_workers claim loops ends with one
      // failed claim. The counter then reads n_units + n_workers. A helper
      // that skipped its claim loop leaves it lower.
      REQUIRE(w.n_units >= 1);
      REQUIRE(w.unit_start[0] == 0);
      REQUIRE(w.unit_start[w.n_units] == n_items);
      REQUIRE(w.next_unit.load() == w.n_units + n_workers);
      // The units are the maximal runs of Note [Shared block save]. A unit
      // never crosses a page, a 16-token page block or a change of
      // token_jobs_do_kv (batch::k_store_window). So two units never write
      // the same token lanes, and a unit that fills its block may use
      // whole-line stores.
      for (size_t u = 0; u < w.n_units; ++u) {
        const size_t begin = w.unit_start[u];
        const size_t end = w.unit_start[u + 1];
        CAPTURE(u, begin, end);
        REQUIRE(begin < end);
        const bool unit_kv = kv_of(begin);
        const page_t* unit_page = unit_kv ? token_pages[token_of(begin)] : nullptr;
        const size_t unit_block = unit_kv ? block_of(token_of(begin)) : 0;
        for (size_t t = begin; t < end; ++t) {
          CAPTURE(t);
          REQUIRE(kv_of(t) == unit_kv);
          if (unit_kv) {
            REQUIRE(token_pages[token_of(t)] == unit_page);
            REQUIRE(block_of(token_of(t)) == unit_block);
          }
        }
      }
      // A new unit starts only at such a change: the item before a unit's
      // first item differs from it in the KV flag, the page or the block. So
      // every run that could use the block save is one unit.
      for (size_t u = 1; u < w.n_units; ++u) {
        const size_t first = w.unit_start[u];
        const size_t prev = first - 1;
        CAPTURE(u, first);
        const bool first_kv = kv_of(first);
        const bool kv_changes = kv_of(prev) != first_kv;
        const bool place_changes =
            first_kv && (token_pages[token_of(prev)] != token_pages[token_of(first)] ||
                            block_of(token_of(prev)) != block_of(token_of(first)));
        REQUIRE((kv_changes || place_changes));
      }
    };
    const auto before = snapshot();
    shared_save(operation);
    check(before);
    if constexpr (k_vnni::layout_on<head_size>) {
      check_window(1);
    } else {
      REQUIRE(q_batch.k_store_window.opened.load() == 0);
    }
    // A second window, on the next layer's operation and KV slot. Main resets
    // the claim counter and `finished` before it opens a window. The helpers'
    // second call meets the second window.
    const attention_operation_descriptor operation_1 =
        state.active_attention_operations[1];
    REQUIRE(operation_1.writes_kv);
    REQUIRE(operation_1.binding.kv_slot.i != slot.i);
    slot = operation_1.binding.kv_slot;
    const auto before_1 = snapshot();
    shared_save(operation_1);
    check(before_1);
    if constexpr (k_vnni::layout_on<head_size>) {
      check_window(2);
    } else {
      REQUIRE(q_batch.k_store_window.opened.load() == 0);
    }
  }
}

// The typed packed-V operations (h/tron/tensor/v_vnni.hpp) carry the bodies
// that used to live in page::set_v / page::get_v, and page::v_packed exposes
// the plane as a typed view. This case pins the contracts a move can
// silently change and the value tests above (finite random data compared as
// floats) cannot see:
// - a bf16 source row is stored bit for bit, infinities and NaNs included;
// - fp16 and float source rows are stored as bf16, checked on values that
//   are exact in bf16 (how inexact values round is not a contract);
// - get_v returns the stored bits, as bf16 or as the upper half of each fp32;
// - at() on page::v_packed returns the stored bits of every token, so the
//   address formula holds for both parities.
TEST_CASE("packed V rows keep their bits through set_v, get_v and at()", "[kv_data]") {
  static constexpr size_t head_size = 64;
  static constexpr size_t x_bytes = 0;
  // Base of the distinct bit patterns: exponent field 0x78 (see pattern below).
  static constexpr uint16_t pattern_base = 0x3c00;
  // The token pairs that carry the special or converted rows in the sections.
  static constexpr size_t specials_even_token = 2;
  static constexpr size_t specials_odd_token = 3;
  static constexpr size_t float_row_even_token = 4;
  static constexpr size_t float_row_odd_token = 5;
  static constexpr size_t fp16_row_even_token = 6;
  static constexpr size_t fp16_row_odd_token = 7;
  constexpr kv_geometry geometry{1, head_size};
  using book_t = uniform_kv_cache<1, geometry, x_bytes>;
  using page_t = book_t::page_t;
  constexpr kv_slot_id slot = test_kv_slot<book_t>(0);
  book_t bk(1);
  page_t* page = bk.page_of(0);

  // Distinct finite bf16 bit patterns per (token, dim): a wrong pair or parity
  // cannot pass by coincidence. Exponent field 0x78..0x97, never 0xff.
  auto pattern = [](size_t token, size_t dim) {
    return static_cast<uint16_t>(pattern_base + token * head_size + dim);
  };
  auto as_bits = [](float x) { return std::bit_cast<uint32_t>(x); };

  // Every token written from a bf16 row, so the whole plane is defined.
  for (size_t token = 0; token < page_t::page_size; ++token) {
    alignas(chunk_alignment) std::array<bf16, head_size> row;
    for (size_t dim = 0; dim < head_size; ++dim) {
      row[dim] = bf16::from_bits(pattern(token, dim));
    }
    page->set_v(slot, 0, token, v_source_row<head_size>(row.data()));
  }

  SECTION("bf16 rows round-trip bit for bit, as bf16 and as fp32") {
    // Special values on an even and on an odd token: +inf, -inf, a quiet NaN
    // with payload, and negative zero. No denormal: the process may run with
    // denormals-are-zero set, and scalar bf16 copies in the test itself would
    // then flush it, which says nothing about the packed path.
    constexpr std::array<uint16_t, 4> specials{0x7f80u, 0xff80u, 0x7fc1u, 0x8000u};
    auto special_row = [&](size_t token, std::array<bf16, head_size>& row) {
      for (size_t dim = 0; dim < head_size; ++dim) {
        row[dim] = bf16::from_bits(
            dim < specials.size() ? specials[dim] : pattern(token, dim));
      }
    };
    alignas(chunk_alignment) std::array<bf16, head_size> row;
    special_row(specials_even_token, row);
    page->set_v(slot, 0, specials_even_token, v_source_row<head_size>(row.data()));
    // The even append must zero its odd partner (Note [Zero-Initialized V
    // Slots]): token 3 still held its pattern from the fill above. Token 2
    // carries 0xff80 and 0x8000 (sign bit set), so a sign-extending even path
    // would leave 0xffff in the partner here.
    {
      alignas(chunk_alignment) std::array<bf16, head_size> partner;
      page->get_v(
          slot, 0, specials_odd_token, v_destination_row<head_size>(partner.data()));
      for (size_t dim = 0; dim < head_size; ++dim) {
        CAPTURE(dim);
        REQUIRE(partner[dim].to_bits() == 0);
      }
    }
    special_row(specials_odd_token, row);
    page->set_v(slot, 0, specials_odd_token, v_source_row<head_size>(row.data()));
    for (size_t token = 0; token < page_t::page_size; ++token) {
      alignas(chunk_alignment) std::array<bf16, head_size> back;
      page->get_v(slot, 0, token, v_destination_row<head_size>(back.data()));
      alignas(chunk_alignment) std::array<float, head_size> back_f32;
      page->get_v(slot, 0, token, v_destination_row<head_size>(back_f32.data()));
      for (size_t dim = 0; dim < head_size; ++dim) {
        const uint16_t expected =
            (token == specials_even_token || token == specials_odd_token) &&
                    dim < specials.size()
                ? specials[dim]
                : pattern(token, dim);
        CAPTURE(token, dim);
        REQUIRE(back[dim].to_bits() == expected);
        REQUIRE(as_bits(back_f32[dim]) == static_cast<uint32_t>(expected) << 16);
      }
    }
  }

  SECTION("float rows are stored as bf16 and keep the pair rule") {
    // fp32 bit pattern -> stored bf16 bits. Every value is exact in bf16, so
    // the expected bits do not depend on the rounding rule of the store.
    constexpr std::array<std::pair<uint32_t, uint16_t>, 4> cases{{
        {0x3f800000u, 0x3f80u},  // 1.0
        {0x3f000000u, 0x3f00u},  // 0.5
        {0xc0000000u, 0xc000u},  // -2.0
        {0x7fc00000u, 0x7fc0u},  // quiet NaN, payload survives
    }};
    for (size_t token : {float_row_even_token, float_row_odd_token}) {
      alignas(chunk_alignment) std::array<float, head_size> row;
      for (size_t dim = 0; dim < head_size; ++dim) {
        row[dim] = std::bit_cast<float>(
            dim < cases.size() ? cases[dim].first
                               : static_cast<uint32_t>(pattern(token, dim)) << 16);
      }
      page->set_v(slot, 0, token, v_source_row<head_size>(row.data()));
      alignas(chunk_alignment) std::array<bf16, head_size> back;
      page->get_v(slot, 0, token, v_destination_row<head_size>(back.data()));
      for (size_t dim = 0; dim < head_size; ++dim) {
        CAPTURE(token, dim);
        REQUIRE(back[dim].to_bits() ==
                (dim < cases.size() ? cases[dim].second : pattern(token, dim)));
      }
    }
    // The odd write (token 5) must not have disturbed its even partner.
    alignas(chunk_alignment) std::array<bf16, head_size> partner;
    page->get_v(
        slot, 0, float_row_even_token, v_destination_row<head_size>(partner.data()));
    for (size_t dim = 0; dim < cases.size(); ++dim) {
      REQUIRE(partner[dim].to_bits() == cases[dim].second);
    }
  }

  SECTION("fp16 rows are stored as bf16 and keep the pair rule") {
    // fp16 value -> stored bf16 bits. Every value is exact in bf16.
    constexpr std::array<std::pair<float, uint16_t>, 3> cases{{
        {1.0f, 0x3f80u},
        {-0.00006103515625f, 0xb880u},  // -2^-14, the smallest fp16 normal
        {0.5f, 0x3f00u},
    }};
    auto fp16_row = [&](size_t token, std::array<fp16, head_size>& row) {
      for (size_t dim = 0; dim < head_size; ++dim) {
        row[dim] =
            fp16(dim < cases.size() ? cases[dim].first
                                    : float(bf16::from_bits(pattern(token, dim))));
      }
    };
    auto check_row = [&](size_t token) {
      alignas(chunk_alignment) std::array<bf16, head_size> back;
      page->get_v(slot, 0, token, v_destination_row<head_size>(back.data()));
      for (size_t dim = 0; dim < cases.size(); ++dim) {
        CAPTURE(token, dim);
        REQUIRE(back[dim].to_bits() == cases[dim].second);
      }
    };
    alignas(chunk_alignment) std::array<fp16, head_size> row;
    fp16_row(fp16_row_even_token, row);
    page->set_v(slot, 0, fp16_row_even_token, v_source_row<head_size>(row.data()));
    // The even append must zero its odd partner: token 7 still held its
    // pattern from the fill above, and token 6 carries -2^-14 (sign bit set).
    {
      alignas(chunk_alignment) std::array<bf16, head_size> partner;
      page->get_v(
          slot, 0, fp16_row_odd_token, v_destination_row<head_size>(partner.data()));
      for (size_t dim = 0; dim < head_size; ++dim) {
        CAPTURE(dim);
        REQUIRE(partner[dim].to_bits() == 0);
      }
    }
    check_row(fp16_row_even_token);
    fp16_row(fp16_row_odd_token, row);
    page->set_v(slot, 0, fp16_row_odd_token, v_source_row<head_size>(row.data()));
    check_row(fp16_row_odd_token);
    check_row(fp16_row_even_token);  // the odd append kept its even partner
  }

  SECTION("token copies keep bits in all four parity combinations") {
    // book::append copies token by token (page::append_v -> copy_token). A
    // destination that starts at an even token copies even<-even and odd<-odd;
    // one that starts at an odd token copies odd<-even and even<-odd. The
    // specials sit on source tokens 2 and 3, so a wrong half-lane merge in any
    // parity branch changes bits here, which the float comparisons of the
    // append cases above cannot see.
    constexpr std::array<uint16_t, 4> specials{0x7f80u, 0xff80u, 0x7fc1u, 0x8000u};
    auto source_bits = [&](size_t token, size_t dim) {
      return (token == specials_even_token || token == specials_odd_token) &&
                     dim < specials.size()
                 ? specials[dim]
                 : pattern(token, dim);
    };
    const size_t dst_tokens = GENERATE(2, 3);  // an even and an odd start
    const size_t src_tokens = page_t::page_size - dst_tokens;
    book_t dst_book(1);
    book_t src_book(1);
    alignas(chunk_alignment) std::array<bf16, head_size> row;
    for (size_t token = 0; token < dst_tokens; ++token) {
      dst_book.increment_tokens_used();
      for (size_t dim = 0; dim < head_size; ++dim) {
        row[dim] = bf16::from_bits(pattern(token, dim));
      }
      dst_book.page_of(0)->set_v(slot, 0, token, v_source_row<head_size>(row.data()));
    }
    for (size_t token = 0; token < src_tokens; ++token) {
      src_book.increment_tokens_used();
      for (size_t dim = 0; dim < head_size; ++dim) {
        row[dim] = bf16::from_bits(source_bits(token, dim));
      }
      src_book.page_of(0)->set_v(slot, 0, token, v_source_row<head_size>(row.data()));
    }
    dst_book.append(src_book);
    REQUIRE(dst_book.size() == page_t::page_size);
    for (size_t token = 0; token < page_t::page_size; ++token) {
      alignas(chunk_alignment) std::array<bf16, head_size> back;
      dst_book.page_of(0)->get_v(
          slot, 0, token, v_destination_row<head_size>(back.data()));
      for (size_t dim = 0; dim < head_size; ++dim) {
        const uint16_t expected = token < dst_tokens
                                      ? pattern(token, dim)
                                      : source_bits(token - dst_tokens, dim);
        CAPTURE(dst_tokens, token, dim);
        REQUIRE(back[dim].to_bits() == expected);
      }
    }
  }

  SECTION("at() reads the packed plane by (token, dim)") {
    auto const plane = page->template v_packed<geometry>(slot, 0);
    for (size_t token = 0; token < page_t::page_size; ++token) {
      for (size_t dim = 0; dim < head_size; ++dim) {
        CAPTURE(token, dim);
        REQUIRE(plane.at(token, dim).to_bits() == pattern(token, dim));
      }
    }
  }
}

// The packed layout against an independent formula that shares no code with
// the typed operations: append_v_row and at() both compute addresses through
// pair_base, so a wrong formula there would pass a read-back through at().
// This case compares the owner's bytes with
//   storage[(pair * Cols + dim) * 2 + j] = V[2 * pair + j][dim]
// written out by hand. It needs no AMX, so it runs in every build.
TEST_CASE("append_v_row matches the independent packed-V formula", "[kv_data]") {
  static constexpr size_t rows = 64;
  static constexpr size_t cols = 128;
  // Base of the distinct bit patterns: exponent field 0x78..0xb7, never 0xff.
  static constexpr uint16_t pattern_base = 0x3c00;
  auto pattern = [](size_t token, size_t dim) {
    return static_cast<uint16_t>(pattern_base + token * cols + dim);
  };
  // The owner is 16 KiB with 64-byte alignment, so it lives on the heap (the
  // aligned operator new honors alignas(64)).
  auto owner = std::make_unique<v_vnni_tensor<rows, cols>>();
  for (size_t token = 0; token < rows; ++token) {
    alignas(chunk_alignment) std::array<bf16, cols> row;
    for (size_t dim = 0; dim < cols; ++dim) {
      row[dim] = bf16::from_bits(pattern(token, dim));
    }
    append_v_row(owner->as_view(), token, v_source_row<cols>(row.data()));
  }
  std::array<uint16_t, rows * cols> stored;
  static_assert(sizeof(stored) == sizeof(*owner));
  std::memcpy(stored.data(), owner.get(), sizeof(stored));
  for (size_t pair = 0; pair < rows / 2; ++pair) {
    for (size_t dim = 0; dim < cols; ++dim) {
      for (size_t j = 0; j < 2; ++j) {
        CAPTURE(pair, dim, j);
        REQUIRE(stored[(pair * cols + dim) * 2 + j] == pattern(2 * pair + j, dim));
      }
    }
  }
}
