#pragma once

#include <algorithm>
// #include <atomic>
#include <bitset>
#include <cmath>
#include <cstring>
#include <deque>
#include <limits>
#include <memory>  // IWYU pragma: keep
#include <optional>
#include <span>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "common/assert.hpp"
#include "common/numerics/fp16.hpp"
#include "common/util.hpp"
#include "libpos.hpp"
#include "spdlog/spdlog.h"
#include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free
#include "tron/kernels/dotter.hpp"
#include "tron/kernels/expr.hpp"
#include "tron/kernels/page_share_counters.hpp"  // TRON_PAGE_SHARE_COUNTERS only
#include "tron/models/attn_stats.hpp"
#include "tron/models/common.hpp"
#include "tron/models/hw_attn_config.hpp"  // IWYU pragma: keep
#include "tron/models/kv_cache.hpp"
#include "tron/models/ranged_mask.hpp"

// #define DEBUG_HWATTN
#ifdef DEBUG_HWATTN
#define dbg_hwattn_log(...) spdlog::debug(__VA_ARGS__)
#else
#define dbg_hwattn_log(...)
#endif

namespace tron {

constexpr bool hardware_attention_scale_representable(float scale) noexcept {
  const float device_scale = fp16(scale);
  return device_scale > 0.0f && device_scale < std::numeric_limits<float>::infinity();
}

constexpr float decode_hardware_attention_maximum(
    float raw_maximum, float nominal_scale) noexcept {
  return raw_maximum * nominal_scale;
}

// Note [Host scale for hardware attention joins]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Hardware stores the attention scale in fp16, but returns an unscaled raw QK
// maximum M with partial softmax statistics computed about M using device scale
// a_h = fp16(a). The host decodes M and computes software fragments using the
// nominal model scale a. A hardware score x therefore joins as if its logit were
//
//   a M + a_h (x - M).
//
// This anchors each hardware-partial maximum, each software score, and
// comparisons between partial maxima at the nominal scale. Nonmax hardware
// scores retain device-scale gaps. This approximation is partition-dependent:
// changing which scores share a hardware partial changes which maximum anchors
// each gap. It preserves nominal scale at partial boundaries instead of applying
// the device scale uniformly.

struct attention_sink_update {
  float m_star;
  float s_star;
  float value_scale;
};

// Compute the exact deferred-softmax update for one query-head sink.
inline attention_sink_update attention_sink_update_for(
    float sink, float m_star, float s_star) noexcept {
  float const new_m = std::max(m_star, sink);
  float const value_scale = std::exp(m_star - new_m);
  return attention_sink_update{
      new_m, s_star * value_scale + std::exp(sink - new_m), value_scale};
}

// Note [Self-attention in Tron]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Tron implements a range of attention variants in the parallel
// `self_attention` CPU kernel. The `self_attention` struct identifies an
// instantiation of the self-attention kernel (giving, e.g. number of layers,
// heads, and the attention variant). Static geometry lives in the parent
// `model`; operation values are bound once in the enclosing model state.
//
// The runtime state needed by the kernel is captured by
// `self_attention::state`, of which each model typically carries an instance.
// This structure captures:
//
//  * a reference to the parent model state (`enclosing_state`)
//  * the model-wide hardware-attention scale
//  * a number of intermediate accumulator buffers, one per parallel
//    worker (`attn_accum`)
//
// As with the rest of Tron, `self_attention` is designed to exploit
// parallelism. Plugins schedule `run_attention_job` with explicit operation
// descriptors and plugin-owned Q/O buffers and channels. Plugins own any RoPE
// or output permutation around the attention operation. Attention is evaluated
// according to Note [Computing self-attention]; see
// Note [Ready versus pending attention work] for overlap with FPGA matmuls.
//
// Note that this kernel implements multi-head attention with minibatching;
// consequently all intermediates are of shape
// [minibatch_sz, n_attn_heads, ...].
//
// In general we try to hold the API surface here to a minimum. The goal is to
// able to support MHLA or other attention variants by swapping to a different
// self_attention struct (and corresponding dependent types).
//
// This kernel was originally separated out of llama.hpp with a vague concept of
// modularization, so, e.g., we could write another one of these for MHLA and
// have llama.hpp pick which attention module to use.  That hasn't happened, and
// instead the current modularity goes the other way: Ingest may generate
// replacements for llama.hpp, but the attention module is (currently) forever.
//
//
// Note [Computing self-attention]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Our self-attention implementation builds upon Rabe & Staats 2021 [1], which
// presents a strategy for numerically-stable computation of self-attention
// requiring only O(num_q_tokens * head_size) memory compared to the O(num_q_tokens *
// num_k_tokens) of a naive approach materialising the Q K^T product). See
// section 3 of [1] for a description of our variant of this algorithm.
//
// Recall that attention is defined as
//
//      Attention(q, {k_0..k_n}, {v_0..v_n}; a) = dot(softmax(s), v)
//        where
//          s_i = a * dot(q, k_i)  for all sequence elements i
//          a                         is the operation's attention scale
//          softmax(x)_i
//              = e^{x_i} / sum_i(e^{x_i})
//          q   \in R^d
//          k_i \in R^d            for all sequence elements i
//          v_i \in R^d            for all sequence elements i
//
// In self-attention, this will be evaluated over a query for each sequence
// element, q_i. This is problematic as evaluating attention at a particular
// sequence element q_i will require a reduction across the entire sequence of
// {s_0..s_n} due to the use of softmax. Naively one might evaluate this by
// materialising the full S \in R^{seq_len x n_query_tokens}. Rabe observes
// that portions of S can instead be computed incrementally by exploiting the
// monoidal structure of softmax, represented by a triple of three values:
//
//   - m^*, giving the maximum score seen thus far
//   - s^*, giving a running sum of exp(score - m)
//   - v^*, giving a running weighted sum of scores seen thus far
//
// This representation, coupled with the update rules given in [1] Section 3,
// allows us to examine subsets of the sequence at a time, evaluating attention
// on each individually, and joining these results at the end into a final
// attention value:
//
//   for each query q:
//     bvector<head_size> v_star = zeros
//     float s_star = 0
//     float m_star = -inf
//     for each relevant token position i:
//       # N.B. Rabe & Staats omit the attention scale
//       float s_i = operation_scale * dot(q, k[i])
//       float m_i = max(m_star, s_i)
//       v_star = v_star * exp(m_star - m_i) + v[i] * exp(s_i - m_i)
//       s_star = s_star * exp(m_star - m_i) + exp(s_i - m_i)
//       m_star = m_i
//     scores_for_q = v_star / s_star
//
// Additionally, this incrementality allows us to parallelize these evaluations
// over the sequence, combining them at the end. We take advantage
// of this by computing pages over a set of "KV workers". Each worker is
// responsible for computing a set of `kv_section`s, over a minibatch. Each
// section identifies a set of pages and a particular KV head. This is
// especially helpful when we have more cores than KV heads.
//
// Concretely, the evaluation of a given set of pages is carried out
// in `apply_page_range`. Here we compute v^*, m^*, and s^* for each
// position of each page in the set and update the corresponding
// intermediate buffers of the worker's local `attn_accum`.  Once all
// KV ranges have been evaluated, we perform a parallel reduction via
// `join_page_ranges`.
//
// See Note [Attention Sequence Parallelism] for further detail on this
// parallelism dance, and Note [Attention join parallelism scheme] for how
// we parallelize the join at the end.
//
// [1]: https://arxiv.org/abs/2112.05682

inline constexpr int illegal_sliding_window = std::numeric_limits<int>::max();

template <typename model>
struct self_attention {
  using plugin = model::plugin_t;
  static constexpr size_t dim = plugin::dim;
  static constexpr size_t n_layers = plugin::n_layers;
  static constexpr size_t n_heads = plugin::n_heads;
  static constexpr size_t n_kv_heads = model::n_kv_heads;
  static constexpr size_t head_size = model::head_size;
  inline static const size_t kv_mul = n_heads / n_kv_heads;
  static constexpr bool softcapping = plugin::attn_softcapping;
  static constexpr bool sinks = model::may_have_attention_sinks;
  static constexpr size_t max_minibatch_size = model::max_minibatch_size;
  inline static const constant<head_size> unity_weights = constant<head_size>(1.0f);
  static constexpr size_t hw_contraction_size = n_heads * head_size;
  inline static constexpr attention_geometry hardware_geometry{
      n_heads, kv_geometry{n_kv_heads, head_size}};
  static constexpr size_t scratch_query_width =
      std::max(hw_contraction_size, model::max_kernel_query_width);
  static constexpr size_t scratch_query_heads =
      std::max(n_heads, model::max_kernel_query_heads);
  static constexpr size_t scratch_kv_heads =
      std::max(n_kv_heads, model::max_kernel_kv_heads);
  static constexpr size_t hw_result_size =
      n_heads * (hardware::HW_BAKED_HEAD_SIZE + hardware::HW_RMEM_WIDTH_ELEMS);
  static constexpr size_t max_hw_subpasses_per_pass =
      hardware::MAX_HW_SUBPASSES_PER_PASS;
  static constexpr size_t hw_result_landing_size =
      hw_result_size * max_hw_subpasses_per_pass;

  template <size_t M, size_t N>
  using dtensor_t = typename plugin::template dtensor_t<M, N>;
  template <size_t d, size_t... ds>
  using btensor_t = typename plugin::template btensor_t<d, ds...>;
  using cache_t = typename model::cache_t;
  using book = cache_t;
  using page = cache_t::page_t;
  using batch = batch<model>;

  static constexpr int illegal_sliding_window = tron::illegal_sliding_window;

  // There is one attention state for the whole forward pass.
  template <typename enclosing_state_t, size_t n_layers>
  struct state : noncopyable<state<enclosing_state_t, n_layers>> {
    // Raw HW DMA landing buffers live on the per-scratchpad `hw_attn_results`
    // struct below (state-resident, keyed by token_job_id, lazily allocated).
    std::array<bool, max_minibatch_size> hw_results_ready{};
    std::array<bool, max_minibatch_size> hw_job_in_flight{};
    std::array<std::mutex, max_minibatch_size> hw_results_mutex;
    std::array<std::condition_variable, max_minibatch_size> hw_results_cv;
    const hardware::device_mask attn_mask = hardware::get_devices();
    // pre_attn_scalar and the hardware KV-slot mask are wired in later
    hardware::hw_attn_params hw_attn_cfg{head_size, n_kv_heads, n_heads, kv_mul,
        /*pre_attn_scalar=*/0.0f, /*hw_slots=*/{}};
    // Per-state hardware-attention bookkeeping keeps target and draft models
    // independent during speculative decoding.
    bool hw_attn_eligible = false;
    // Highest hardware-enabled KV slot plus one. This is an extent, not the
    // number of enabled slots; software-only holes remain addressable.
    size_t hw_attn_kv_slot_extent = 0;

#ifdef TRON_AMX_DISPATCH
    // One packed query group for the AMX attention path (the output of
    // pack_q_group_128x4): 4096 bytes. alignas(64) meets the packer's 64-byte
    // alignment contract; std::vector routes over-aligned elements through
    // the aligned operator new.
    struct alignas(64) amx_qpack_slot {
      bf16 v[amx_attn_h128g4::Q_PACK_ELEMS_2048];
    };
#endif

    // The actual backing memory for worker scratchpads for software attention.
    // We mostly access it through the `scratchpad_ref` struct below, but
    // we lay it out like this in memory for the sake of cache locality.
    struct attn_accum {
      // These `std::array` are parallel, and indexed by the token's index in its
      // `q_batch`.
      std::array<btensor_t<scratch_query_width>, max_minibatch_size> v_stars;
      std::array<std::array<float, scratch_query_heads>, max_minibatch_size> s_stars;
      // largest scalar seen so far
      std::array<std::array<float, scratch_query_heads>, max_minibatch_size> m_stars;
      // Per-token, per-kv_head validity.
      std::array<std::array<bool, scratch_kv_heads>, max_minibatch_size> valid;
#ifdef TRON_AMX_DISPATCH
      // The packed queries for the AMX attention path.
      //
      // The AMX QK kernel cannot read a token's 4 query heads as they are
      // stored; it needs them copied to its tile layout (a "pack"). Element
      // batch_job_ix of this vector is the pack of the token at position
      // batch_job_ix of the minibatch, so the vector is indexed like the
      // arrays above.
      std::vector<amx_qpack_slot> amx_qpack;
#endif

      void clear_validity(size_t n_items) {
        TRON_ASSERT_LE(n_items, max_minibatch_size);
        for (size_t item_ix = 0; item_ix < n_items; ++item_ix)
          std::fill(valid[item_ix].begin(), valid[item_ix].end(), false);
      }

      template <attention_geometry geometry>
      void finish(auto& vo, token_job_id tok, size_t kv_head, size_t token_job_id) {
        constexpr size_t operation_kv_mul = geometry.kv_mul();
        for (size_t head = kv_head * operation_kv_mul;
            head < (kv_head + 1) * operation_kv_mul; ++head) {
          slice<geometry.kv.head_size>()(
              vo[tok].as_view(), head * geometry.kv.head_size)
              .set(slice<geometry.kv.head_size>()(
                       v_stars[token_job_id].as_view(), head * geometry.kv.head_size) /
                   s_stars[token_job_id][head]);
        }
      }

      std::string debug_string() const {
        std::string result = "attn_accum addresses:\n";
        for (size_t i = 0; i < max_minibatch_size; ++i) {
          result += fmt::format("  [{}] v_stars: {:p}, s_stars: {:p}, m_stars: {:p}\n",
              i, static_cast<const void*>(&v_stars[i].data[0]),
              static_cast<const void*>(s_stars[i].data()),
              static_cast<const void*>(m_stars[i].data()));
        }
        for (size_t i = 0; i < scratch_kv_heads; ++i) {
          result += fmt::format(
              "  valid[{}]: {:p}\n", i, static_cast<const void*>(&valid[i]));
        }
        return result;
      }
    };

    // Reference bundles for the softmax monoid state (v*, s*, m*).
    // See Note [Attention join parallelism scheme].
    //
    // `scratchpad_ref` holds the state for a specific (worker, token, head) triplet.
    // `token_scratchpad_ref` holds the state for a specific (worker, token) pair
    // across all heads, referencing into the SoA `attn_accum` storage.

    template <attention_geometry geometry>
    using v_star_view_t = decltype(slice<geometry.kv.head_size>()(
        std::declval<btensor_t<scratch_query_width>&>().as_view(), size_t{0}));
    using v_stars_view_t =
        decltype(std::declval<btensor_t<scratch_query_width>&>().as_view());

    // The soft-max accumulation state for a specific (worker, token, head) triplet.
    template <attention_geometry geometry>
    struct scratchpad_ref {
      v_star_view_t<geometry> v_star;
      float& s_star;
      float& m_star;
    };

    // The soft-max accumulation state for a specific (worker, token) pair across
    // all heads.  Also carries validity information for the deferred softmax
    // monoid, allowing `join_page_ranges` to operate on two `token_scratchpad`
    // instances directly.
    template <attention_geometry geometry>
    struct token_scratchpad_ref {
      v_stars_view_t v_stars;
      std::array<float, scratch_query_heads>& s_stars;
      std::array<float, scratch_query_heads>& m_stars;
      std::array<bool, scratch_kv_heads>& valid;
      size_t worker_ix;     // For error reporting
      size_t batch_job_ix;  // For error reporting

      scratchpad_ref<geometry> operator[](size_t head) {
        return {slice<geometry.kv.head_size>()(v_stars, head * geometry.kv.head_size),
            s_stars[head], m_stars[head]};
      }

      bool is_valid_for(size_t kv_head) const {
        return valid[kv_head];
      }

      // Returns whether it was already valid before this call.
      bool mark_valid_for(size_t kv_head) {
        bool was = valid[kv_head];
        valid[kv_head] = true;
        return was;
      }

      // Returns whether it was already valid before this call.
      bool mark_invalid_for(size_t kv_head) {
        bool was = valid[kv_head];
        valid[kv_head] = false;
        return was;
      }
    };

    template <attention_geometry geometry>
    token_scratchpad_ref<geometry> token_scratchpad_ref_at(
        size_t worker_ix, size_t batch_job_ix) {
      return {attn[worker_ix].v_stars[batch_job_ix].as_view(),
          attn[worker_ix].s_stars[batch_job_ix], attn[worker_ix].m_stars[batch_job_ix],
          attn[worker_ix].valid[batch_job_ix], worker_ix, batch_job_ix};
    }

    struct hw_attn_results {
      attn_accum data;
      std::array<std::atomic<int>, max_minibatch_size> unpack_state;
      // Raw HW DMA landing buffers for this scratchpad, one per token job.
      // Plan assembly allocates them before attention workers launch.
      indexed_vector<token_job_id,
          std::unique_ptr<hardware::btensor<hw_result_landing_size>>>
          raw_results;
      attn_accum unpack_tmp;

      hw_attn_results() = default;
      hw_attn_results(hw_attn_results&&) = delete;
      hw_attn_results& operator=(hw_attn_results&&) = delete;

      void reset(size_t n_items) {
        data.clear_validity(n_items);
        unpack_tmp.clear_validity(n_items);
        for (size_t item_ix = 0; item_ix < n_items; ++item_ix)
          unpack_state[item_ix].store(0, std::memory_order_relaxed);
      }

      token_scratchpad_ref<hardware_geometry> get_token_scratchpad_ref(
          size_t batch_job_ix) {
        return {data.v_stars[batch_job_ix].as_view(), data.s_stars[batch_job_ix],
            data.m_stars[batch_job_ix], data.valid[batch_job_ix], SIZE_MAX,
            batch_job_ix};
      }

      token_scratchpad_ref<hardware_geometry> get_tmp_token_scratchpad_ref(
          size_t batch_job_ix) {
        return {unpack_tmp.v_stars[batch_job_ix].as_view(),
            unpack_tmp.s_stars[batch_job_ix], unpack_tmp.m_stars[batch_job_ix],
            unpack_tmp.valid[batch_job_ix], SIZE_MAX, batch_job_ix};
      }

      void prepare_raw_result(token_job_id job) {
        if (raw_results.size() <= job.i) raw_results.resize(job.i + 1);
        auto& slot = raw_results[job];
        if (!slot) slot = std::make_unique<hardware::btensor<hw_result_landing_size>>();
      }

      hardware::btensor<hw_result_landing_size>& raw_result(token_job_id job) {
        TRON_ASSERT(job.i < raw_results.size());
        auto& slot = raw_results[job];
        TRON_ASSERT(slot);
        return *slot;
      }
    };

    hw_attn_results& hw_attn_results_at(hw_scratchpad_id scratchpad_ix) {
      return hw_attn[scratchpad_ix.i];
    }

    token_scratchpad_ref<hardware_geometry> hw_token_scratchpad_ref_at(
        hw_scratchpad_id scratchpad_ix, size_t batch_job_ix) {
      return hw_attn_results_at(scratchpad_ix).get_token_scratchpad_ref(batch_job_ix);
    }

    scratchpad_ref<hardware_geometry> hw_scratchpad(
        hw_scratchpad_id scratchpad_ix, size_t batch_job_ix, size_t head) {
      return hw_token_scratchpad_ref_at(scratchpad_ix, batch_job_ix)[head];
    }

    enclosing_state_t& enclosing_state;
    // Scratchpads for parallel reduction in attention. One per app_pool worker.
    std::vector<attn_accum> attn;
    // Scratchpads for hardware attention passes.  One per hw_pass in the
    // hw_workload.  Empties allowed.  A deque so growth constructs only the
    // new elements: existing scratchpads and their lazily-allocated raw DMA
    // landing buffers must survive (each element is ~1MB, and rebuilding the
    // whole set every time the pass count grows costs ~0.8ms per element).
    std::deque<hw_attn_results> hw_attn;
    // See Note [Host scale for hardware attention joins].
    std::optional<float> hardware_attention_scale;
    // Attention path statistics of this state (Note [Attention path stats] in
    // attn_stats.hpp). Always present. `stats->enabled` says whether the hooks
    // count. A shared_ptr because the FUSE leaves hold a weak_ptr to it, so
    // the member must keep the object the constructor registered (unit tests
    // that never initialize the FUSE tree may replace it).
    std::shared_ptr<attn_stats::model_stats> stats;

    state(enclosing_state_t& enclosing_state)
    : enclosing_state(enclosing_state) {
      // Preallocate scratchpad slots for the parallel reduction in attention
      attn.resize(app_pool().num_workers());
      hw_results_ready.fill(false);
      hw_job_in_flight.fill(false);
      {
        attn_stats::header_facts facts;
#ifdef TRON_AMX_DISPATCH
        facts.amx_compiled = attn_stats::AMX_COMPILED_TRUE;
        facts.amx_available = amx_attn_h128g4::available();
#endif
        facts.n_kv_heads = n_kv_heads;
        facts.kv_mul = kv_mul;
        facts.head_size = head_size;
        facts.n_layers = n_layers;
        facts.page_size = page::page_size;
        // cfg is declared before self_attn_state in model::state, so its id is
        // initialized here.
        stats = std::make_shared<attn_stats::model_stats>(attn_stats::env_enabled(),
            enclosing_state.cfg.id, enclosing_state.model_ref.plugin.is_eagle, facts,
            attn.size(), n_layers);
        attn_stats::register_fuse_files(stats);
      }

      constexpr std::optional<float> configured_hardware_scale =
          model::hardware_attention_scale();
      if constexpr (configured_hardware_scale.has_value()) {
        hardware_attention_scale = *configured_hardware_scale;
        // The POS worker performs the fp16 conversion for the device operand.
        // See Note [Host scale for hardware attention joins].
        hw_attn_cfg.pre_attn_scalar = *configured_hardware_scale;
      }
      spdlog::info("Hw-Attn model params: {}, {} layers",
          hw_attn_cfg.debug_string().c_str(), n_layers);
    }

    bool compute_operation_uses_hw(
        attention_operation_descriptor const& operation) const {
      return !enclosing_state.model_ref.plugin.is_eagle && hw_attn_eligible &&
             enclosing_state.operation_is_hardware_candidate(operation) &&
             hardware_attention_scale &&
             operation.config.scale == *hardware_attention_scale &&
             enclosing_state.attention_runtime_configs[operation.binding.operation]
                     .sliding_window_size == illegal_sliding_window;
    }

    bool hardware_scale_is_representable() const noexcept {
      return hardware_attention_scale &&
             hardware_attention_scale_representable(*hardware_attention_scale);
    }

    template <attention_geometry geometry>
    void validate_operation(
        attention_operation_descriptor const& operation) const noexcept {
      static_assert(geometry.valid());
      static_assert(cache_t::template declares_geometry<geometry.kv>());
      const attention_op_id id = operation.binding.operation;
      TRON_ASSERT_LT(id.i, enclosing_state.active_attention_operations.size());
      TRON_ASSERT(operation == enclosing_state.active_attention_operations[id.i],
          "attention descriptor disagrees with active operation {}", id);
      auto const& kernel = enclosing_state.kernel_for(operation);
      TRON_ASSERT(kernel.geometry == geometry,
          "operation {} kernel {} geometry disagrees with specialization",
          operation.binding.operation, operation.kernel);
      TRON_ASSERT(
          cache_t::template slot_matches<geometry.kv>(operation.binding.kv_slot),
          "operation {} kernel {} does not match KV slot {}",
          operation.binding.operation, operation.kernel, operation.binding.kv_slot);
    }

    // See Note [Per-attention-operation plans] in common.hpp.
    typename batch::attention_plan& plan_for(
        batch* q_batch, attention_op_id operation) {
      return q_batch->plans[enclosing_state.attention_plan_id_for_operation[operation]];
    }
    typename batch::attention_plan const& plan_for(
        batch const* q_batch, attention_op_id operation) const {
      return q_batch->plans[enclosing_state.attention_plan_id_for_operation[operation]];
    }

    template <typename query_buffer_t>
    void prepare_uniform_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        bool uses_hw) {
      const attention_binding binding = operation.binding;
      const model_layer_id layer = binding.model_layer;
      const kv_slot_id slot = binding.kv_slot;
      TRACE_EVENT("hwattention", "prep_hw_attn", "layer", layer.i, "kv_slot", slot.i);
      if (q_batch->hw_plan.empty() || !uses_hw) {
        return;
      }
      auto& workload = q_batch->hw_plan;
      auto& attn_launchers = q_batch->attn_launchers;
      if (attn_launchers.size() < workload.passes.size())
        attn_launchers.resize(workload.passes.size());

      for (size_t pi = 0; pi < workload.passes.size(); ++pi) {
        const auto& pass = workload.passes[pi];
        size_t B = pass.queries.size();

        bf16* result_ptrs[hardware::MAX_B] = {};
        bf16 const* activation_ptrs[hardware::MAX_B] = {};
        size_t tok_ix_arr[hardware::MAX_B] = {};

        // Compute tok_ix as the inclusive last valid position concatenated
        // across all shards in this pass. Shards may be non-contiguous in
        // absolute token space (round-robin device allocation), so we cannot
        // subtract the base of the first shard from last_hw_token_pos -- that
        // would inflate rel_tok_ix by the gaps between shards. Instead: each
        // complete prefix shard contributes exactly shard_tokens; the last
        // (possibly partial) shard contributes last_hw_token_pos -
        // last_shard->base_tok_ix. If the global boundary is beyond every shard
        // in this device-local pass, all local tokens are valid; rel_tok_ix is
        // then a count, so convert it back to an inclusive index.
        auto relative_hw_tok_ix = [&](size_t last_hw_token_pos) -> size_t {
          size_t rel_tok_ix = 0;
          for (auto const* sh : pass.shards) {
            const size_t shard_begin = sh->base_tok_ix;
            const size_t shard_end = shard_begin + hardware::shard_tokens;
            if (last_hw_token_pos < shard_begin) {
              break;
            }
            if (last_hw_token_pos < shard_end) {
              rel_tok_ix += last_hw_token_pos - shard_begin;
              return rel_tok_ix;
            }
            rel_tok_ix += hardware::shard_tokens;
          }
          TRON_ASSERT(rel_tok_ix > 0,
              "HW attention pass has no local K/V at or before global token {}",
              last_hw_token_pos);
          return rel_tok_ix - 1;
        };

        for (size_t qi = 0; qi < B; ++qi) {
          token_job_id job_ix = pass.queries[qi].job_ix;
          result_ptrs[qi] =
              hw_attn_results_at(pass.scratchpad_ix).raw_result(job_ix).data.get();
          // HW reads at HW_BAKED_HEAD_SIZE per-head stride; if the model
          // is narrower, point at the parallel padded buffer that
          // launch_hw_attention will refresh.
          if constexpr (head_size != hardware::HW_BAKED_HEAD_SIZE) {
            activation_ptrs[qi] = reinterpret_cast<const bf16*>(
                enclosing_state.hw_qs_for_attn[job_ix].as_view().begin());
          } else {
            activation_ptrs[qi] =
                reinterpret_cast<const bf16*>(queries[job_ix].as_view().begin());
          }
          tok_ix_arr[qi] = relative_hw_tok_ix(pass.queries[qi].last_hw_token_pos);
        }
        if (stats->enabled) {
          // Attention path stats: K tokens the FPGA card scores in this pass (the
          // inclusive last index + 1 per query) and the pass's query count.
          uint64_t fpga_k_tokens = 0;
          for (size_t qi = 0; qi < B; ++qi) {
            fpga_k_tokens += tok_ix_arr[qi] + 1;
          }
          stats->note_fpga_pass(layer.i, fpga_k_tokens, B);
        }

        std::vector<hardware::shard_kv_slot_t> shard_slots;
        for (auto* sh : pass.shards) {
          TRON_ASSERT_LT(slot.i, sh->kv_shard_slots.size());
          TRON_ASSERT_GT(sh->kv_shard_slots[slot.i].allocation_bytes, 0);
          shard_slots.push_back(sh->kv_shard_slots[slot.i]);
        }

        // HW Q stride is HW_BAKED_HEAD_SIZE per head; hw_contraction_size
        // (n_heads*head_size) is the model-side geometry and would
        // mis-stride HW reads when head_size < HW_BAKED_HEAD_SIZE.
        hardware::fill_attn_job_template(n_heads * hardware::HW_BAKED_HEAD_SIZE, B,
            result_ptrs, activation_ptrs, tok_ix_arr, shard_slots, attn_launchers[pi],
            "hwattn", layer.i, hw_attn_cfg, pass.dev);
        hardware::prepare_hardware_attn_job(attn_launchers[pi], pass.dev);
      }
    }

    template <attention_geometry geometry, typename query_buffer_t>
    void prepare_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        bool uses_hw) {
      if constexpr (geometry == hardware_geometry) {
        prepare_uniform_hw_attention(q_batch, operation, queries, uses_hw);
      } else {
        TRON_ASSERT(!uses_hw, "heterogeneous geometry cannot use HW attention");
        TRON_ASSERT(operation.hardware == attention_hardware_capability::software_only,
            "kernel {} geometry has no heterogeneous HW cache path", operation.kernel);
      }
    }

    template <typename query_buffer_t, typename query_channel_t>
    void launch_uniform_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        query_channel_t& query_channel,
        bool uses_hw) {
      const attention_binding binding = operation.binding;
      const model_layer_id layer = binding.model_layer;
      TRACE_EVENT("hwattention", "launch_hw_attn", "layer", layer.i);
      if (q_batch->hw_plan.empty() || !uses_hw) return;

      // Wait for Q to be fully written (RoPE complete) before HW
      // reads it. The fallback latch is signalled by every Q producer.
      query_channel.waitable().wait();

      // Refresh padded Q buffer for HW when head_size < HW_BAKED_HEAD_SIZE.
      // Per-head: copy head_size bf16 from queries into the wider
      // HW_BAKED_HEAD_SIZE slot, zero-fill the remaining cells.
      if constexpr (head_size != hardware::HW_BAKED_HEAD_SIZE) {
        for (auto job_ix : q_batch->items) {
          const bf16* src =
              reinterpret_cast<const bf16*>(queries[job_ix].as_view().begin());
          bf16* dst = reinterpret_cast<bf16*>(
              enclosing_state.hw_qs_for_attn[job_ix].as_view().begin());
          for (size_t head = 0; head < n_heads; ++head) {
            std::copy(src + head * head_size, src + (head + 1) * head_size,
                dst + head * hardware::HW_BAKED_HEAD_SIZE);
            std::fill(dst + head * hardware::HW_BAKED_HEAD_SIZE + head_size,
                dst + (head + 1) * hardware::HW_BAKED_HEAD_SIZE, bf16{0});
          }
        }
      }

      // No explicit await on KV DMA here: shards admitted to the HW plan
      // already have count_complete_prefix_gofs() >= threshold (gated on gs.dma_done,
      // advanced by on_forward_poll), and last_hw_token_pos comes from the same
      // snapshot — HW cannot read past a pending xfer. The prefix, not the
      // count, is what makes that true; see Note [GOF residency is a prefix,
      // not a count].

      auto& workload = q_batch->hw_plan;
      auto& attn_launchers = q_batch->attn_launchers;
      // See Note [HW attention operation completion].
      const uint64_t gen = hw_attention_completion_generation(binding.operation);
      for (size_t pi = 0; pi < workload.passes.size(); ++pi) {
        attn_launchers[pi]([&workload, pi, gen]() {
          TRACE_EVENT("hwattention", "attn_launcher_cb", "pass", pi);
          workload.complete[pi].store(gen, std::memory_order_release);
        });
      }
    }

    template <attention_geometry geometry,
        typename query_buffer_t,
        typename query_channel_t>
    void launch_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        query_channel_t& query_channel,
        bool uses_hw) {
      if constexpr (geometry == hardware_geometry) {
        launch_uniform_hw_attention(
            q_batch, operation, queries, query_channel, uses_hw);
      } else {
        TRON_ASSERT(!uses_hw, "heterogeneous geometry cannot use HW attention");
        TRON_ASSERT(operation.hardware == attention_hardware_capability::software_only,
            "kernel {} geometry has no heterogeneous HW cache path", operation.kernel);
      }
    }

    // See Note [Generated attention operation phases] in TronCpp.hs.
    template <attention_geometry geometry, typename query_buffer_t>
    void prepare_attention_job(batch* outer_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        bool uses_hw,
        bool prepare_hardware) {
      outer_batch->free_scratchpads_barrier.next_phase([&] {
        free_scratchpads<geometry>(outer_batch, operation);
        if (prepare_hardware)
          prepare_hw_attention<geometry>(outer_batch, operation, queries, uses_hw);
      });
    }

    void wait_attention_job(batch* outer_batch, size_t worker_ix) const {
      outer_batch->free_scratchpads_barrier.wait(worker_ix);
    }

    // Reset operation-owned scratchpads before handwritten-plugin workers
    // consume them.
    template <attention_geometry geometry>
    void begin_attention_job(batch* outer_batch,
        attention_operation_descriptor const& operation,
        size_t worker_ix,
        size_t n_attn_workers) {
      validate_operation<geometry>(operation);
      TRON_ASSERT_GT(n_attn_workers, 0);
      enclosing_state.help_drain_gof(/*budget=*/4);
      if (worker_ix == n_attn_workers - 1) {
        outer_batch->free_scratchpads_barrier.next_phase(
            [&] { free_scratchpads<geometry>(outer_batch, operation); });
      }
      outer_batch->free_scratchpads_barrier.wait(worker_ix);
    }

    // Run one operation selected by the plugin schedule. Q and O are normal
    // plugin buffers whose channels carry their asynchronous lifetime.
    template <attention_geometry geometry,
        typename query_buffer_t,
        typename query_channel_t,
        typename output_buffer_t,
        typename output_channel_t>
    uint64_t run_attention_job(batch* outer_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        query_channel_t& query_channel,
        output_buffer_t& output,
        output_channel_t& output_channel,
        size_t worker_ix,
        size_t n_attn_workers,
        bool uses_hw) {
      const attention_binding binding = operation.binding;
      static_assert(query_channel_t::scope == readiness_scope::whole_phase,
          "attention query channels must use whole-phase readiness");
      static_assert(output_channel_t::scope == readiness_scope::whole_phase,
          "attention output channels must use whole-phase readiness");
      thread_pool& tp = app_pool();
      const size_t pool_worker_ix = tp.num_workers() - n_attn_workers + worker_ix;
      const model_layer_id layer = binding.model_layer;
      uint64_t attn_elapsed = 0;
      // Attention path stats timers (Note [Attention path stats] in
      // attn_stats.hpp). T3, the wall of this job on worker 0, and T4, the
      // layer period, start here. T2 is attn_elapsed below.
      attn_stats::model_stats& stats_ref = *stats;
      const bool stats_enabled = stats_ref.enabled;
      const uint64_t t_entry =
          stats_enabled ? hardware::system::rdtsc() : attn_stats::UNSET_CYCLES_0;
      if (stats_enabled && worker_ix == attn_stats::WORKER_0) {
        stats_ref.note_attn_job_entry_w0(binding.operation.i, layer.i, t_entry);
      }

      // Query channels are fallback channels, so this waits for every query.
      query_channel.start_reading(worker_ix);
      for (size_t task_ix = worker_ix; task_ix < outer_batch->items.size();
          task_ix += n_attn_workers) {
        token_job_id ix = outer_batch->items[task_ix];
        enclosing_state.log_intermediate(
            queries[ix], geometry.query_width(), ix, layer.i, "WQ roped");
      }
      attn_elapsed -= hardware::system::rdtsc();
      uint64_t compute_elapsed = 0;
      compute_elapsed -= hardware::system::rdtsc();
      run_sections<geometry>(
          outer_batch, operation, queries, worker_ix, n_attn_workers, uses_hw, false);
      compute_elapsed += hardware::system::rdtsc();
      attn_elapsed += hardware::system::rdtsc();

      // Wait for upstream K/V before running pending attention.
      // See Note [Minibatch Dependency Tracking].
      outer_batch->upstream_kvs_ready[binding.kv_slot].wait();

      attn_elapsed -= hardware::system::rdtsc();
      compute_elapsed -= hardware::system::rdtsc();
      run_sections<geometry>(
          outer_batch, operation, queries, worker_ix, n_attn_workers, uses_hw, true);
      compute_elapsed += hardware::system::rdtsc();
      tp.speedometer.observe(pool_worker_ix,
          plan_for(outer_batch, binding.operation).work_estimate[worker_ix],
          compute_elapsed);
      output_channel.start_writing(worker_ix);

      run_joins<geometry>(outer_batch, operation, output, worker_ix, n_attn_workers,
          uses_hw, stats_enabled);
      // Note [Attention query lifetime]
      // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      // Hardware launch queues pointers; it does not consume Q synchronously.
      // Keep the channel readers until joins observe hardware completion, so
      // the next producer cannot reuse Q while device DMA still reads it.
      query_channel.finish_reading(worker_ix);
      output_channel.finish_writing(worker_ix);
      outer_batch->free_scratchpads_barrier.done(worker_ix);
      const uint64_t t_end = hardware::system::rdtsc();
      attn_elapsed += t_end;
      if (stats_enabled) {
        stats_ref.note_attn_job(
            stats_ref.pool_worker(worker_ix, n_attn_workers), layer.i, attn_elapsed);
        if (worker_ix == attn_stats::WORKER_0) {
          stats_ref.note_attn_job_wall_w0(layer.i, t_end - t_entry);
        }
      }
      return attn_elapsed;
    }

    // Plugins finish after any worker-side output transformation, so worker 0
    // measures the whole operation and no worker starts the next one early.
    void finish_attention_job(batch* outer_batch, size_t n_attn_workers) {
      outer_batch->attn_done_barrier.arrive_and_wait(n_attn_workers);
    }

    // Remaining methods are private except for unit tests

    template <attention_geometry geometry>
    void free_scratchpads(
        batch* q_batch, attention_operation_descriptor const& operation) {
      const attention_binding binding = operation.binding;
      MODEL_DEBUG("{} layer {} qbatch [{}]", __PRETTY_FUNCTION__, binding.model_layer,
          fmt::join(q_batch->items, ","));
      TRACE_EVENT("model", "Free scratchpads");
      for (auto& a : attn)
        a.clear_validity(q_batch->items.size());
      // `q_batch->layer()` is racy from the attn side (main/main-helper
      // threads advance it asynchronously in pipelined mode), so the caller
      // passes the binding's model-layer ID, the ground truth for which plan's
      // `n_sections` is about to be consumed.
      auto& plan_state = plan_for(q_batch, binding.operation);
      for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head)
        plan_state.sections_left[kv_head] = plan_state.n_sections[kv_head];
      // Reset operation scratchpads. Completion generations are not reset:
      // resetting from this worker would race the HW completion callback.
      for (auto& r : hw_attn)
        r.reset(q_batch->items.size());
    }

    // Decode one pass's raw DMA results for one batch job into the pass
    // scratchpad. Exactly one worker performs the deinterleave, published via
    // unpack_state 0 (fresh) -> 1 (claimed) -> 2 (decoded). Non-blocking:
    // returns true once the scratchpad is decoded (by this call or an earlier
    // one) and false while another worker holds the claim, in which case the
    // caller comes back later instead of spinning. See
    // Note [Streaming hardware attention join].
    bool try_unpack_hw_pass(batch* q_batch, size_t pass_ix, size_t batch_job_ix) {
      auto& pass = q_batch->hw_plan.passes[pass_ix];
      auto& scratchpad = hw_attn_results_at(pass.scratchpad_ix);
      auto& unpack_state = scratchpad.unpack_state[batch_job_ix];
      // Decoded once, read on every later sweep and by every kv head: check
      // with a load before the read-modify-write.
      const int state = unpack_state.load(std::memory_order_acquire);
      if (state != 0) return state == 2;
      int expected = 0;
      // On failure `expected` holds the observed state; 2 was published with
      // release, and the failed exchange acquires it.
      if (!unpack_state.compare_exchange_strong(expected, 1, std::memory_order_acq_rel))
        return expected == 2;
      auto* raw = scratchpad.raw_result(q_batch->items[batch_job_ix]).data.get();
      auto decode_into = [&](const bf16* hw_results, attn_accum& dest) {
        // HW emits HW_BAKED_HEAD_SIZE + rmem(32) bf16 per head; aux floats
        // sit at offset HW_BAKED_HEAD_SIZE. The model only consumes the
        // first head_size cells per head; the rest is zero pad.
        for (size_t head = 0; head < n_heads; ++head) {
          const bf16* hw_head = hw_results + head * (hardware::HW_BAKED_HEAD_SIZE +
                                                        hardware::HW_RMEM_WIDTH_ELEMS);
          const float* hw_aux =
              reinterpret_cast<const float*>(hw_head + hardware::HW_BAKED_HEAD_SIZE);
          auto dest_head = slice<head_size>()(
              dest.v_stars[batch_job_ix].as_view(), head * head_size);
          for (size_t i = 0; i < head_size; ++i)
            dest_head[i] = hw_head[i];
          // See Note [Host scale for hardware attention joins].
          TRON_ASSERT(hardware_attention_scale);
          dest.m_stars[batch_job_ix][head] =
              decode_hardware_attention_maximum(hw_aux[0], *hardware_attention_scale);
          dest.s_stars[batch_job_ix][head] = hw_aux[1];
        }
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
          dest.valid[batch_job_ix][kv_head] = true;
      };

      TRON_ASSERT(pass.physical_subpasses > 0 &&
                      pass.physical_subpasses <= max_hw_subpasses_per_pass,
          "HW attention pass has invalid physical_subpasses {}",
          pass.physical_subpasses);
      decode_into(raw, scratchpad.data);
      for (size_t subpass = 1; subpass < pass.physical_subpasses; ++subpass) {
        scratchpad.unpack_tmp.valid[batch_job_ix].fill(false);
        decode_into(raw + subpass * hw_result_size, scratchpad.unpack_tmp);
        token_scratchpad_ref target = scratchpad.get_token_scratchpad_ref(batch_job_ix);
        token_scratchpad_ref source =
            scratchpad.get_tmp_token_scratchpad_ref(batch_job_ix);
        for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head)
          join_page_ranges(target, source, kv_head);
      }
      unpack_state.store(2, std::memory_order_release);
      return true;
    }

    // Note [Streaming hardware attention join]
    // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    // At long context a hardware layer spreads one job's attention over many
    // passes (one per device per EMEM window of K/V shards), and each device
    // retires its passes in launch order.
    //
    // The join streams. For each of this worker's batch jobs and each device
    // group in `hw_plan.by_job` (built by construct_hw_plan; O(1) per job), a
    // cursor holds the next unfolded pass. A sweep over the open jobs folds
    // each completed pass at a cursor into its group's first-pass scratchpad,
    // the per-device accumulator, and advances. Once all groups of a job are
    // folded, their accumulators fold into the first group's scratchpad.
    // Independently, once the kv head's software sections finish, its software
    // scratchpads fold into worker 0's. Neither reduction waits for the other.
    // When both are ready, one final join combines the two accumulators, then
    // `finish_job` applies sinks and normalizes. Only when a whole sweep makes
    // no progress does the worker spin, watching both software and hardware
    // readiness. The `attention: join wait` span excludes merge work.
    //
    // Raw DMA results are decoded once per (pass, job) by whichever worker
    // claims them (`try_unpack_hw_pass`). The kv-head workers of a job
    // converge on a freshly completed pass, so a worker that finds another's
    // claim in progress skips the pass and returns to it on a later sweep
    // instead of spinning behind the decode.
    //
    // Reduction order. `join_page_ranges` is the softmax monoid join,
    // associative and commutative in exact arithmetic; floating-point results
    // depend on association. Each device's passes fold left in launch order
    // into that device's accumulator. Device accumulators fold left in order
    // of each device's first pass; software scratchpads fold left in worker
    // order. The final join combines those two results:
    //   (sw0 (+) sw1 (+) ... (+) sw(n-1))
    //       (+) ((d0p0 (+) d0p1 (+) ...) (+) (d1p0 (+) ...) (+) ...),
    // with sw_w the software scratchpad of attention worker w and dIpK the
    // k'th pass of device i serving the job. Every pass and every software
    // scratchpad folds exactly once, so each query's (v*, s*, m*) covers the
    // whole K/V set and the result is a complete partial. The order is fixed
    // by the plan, not by completion timing: within a device the cursor never
    // folds pass k+1 before pass k, and devices fold in `by_job` group order.
    //
    // Folding into a pass scratchpad is safe: after `try_unpack_hw_pass`
    // publishes state 2, the only writer of that scratchpad's heads for a kv
    // head is the single join worker owning (kv head, job), and different kv
    // heads occupy disjoint head slices and `valid` entries.

    // Per-job cursor state for stream_hw_joins. Job j of a worker's stride is
    // batch job `rank + j * n_join_workers`, so the position is not stored.
    struct hw_join_cursor {
      // Per device group of `hw_plan.by_job[batch_job_ix]`: passes [0, next)
      // are folded into the group's first pass scratchpad.
      std::array<uint32_t, hardware::MAX_DEVICES> next;
      bool software_joined;
      bool hardware_joined;
      bool done;
    };

    template <attention_geometry geometry>
    void join_software(size_t kv_head, size_t batch_job_ix, size_t n_attn_workers) {
      auto target = token_scratchpad_ref_at<geometry>(0, batch_job_ix);
      for (size_t w = 1; w < n_attn_workers; ++w) {
        auto source = token_scratchpad_ref_at<geometry>(w, batch_job_ix);
        join_page_ranges(target, source, kv_head);
      }
    }

    // Reduce software and hardware independently for this worker's batch jobs
    // (rank, rank + n_join_workers, ...) and `finish_job` after their final join.
    // See Note [Streaming hardware attention join].
    template <typename finish_job_t>
    void stream_hw_joins(batch* q_batch,
        attention_op_id operation,
        size_t kv_head,
        size_t rank,
        size_t n_join_workers,
        size_t n_attn_workers,
        finish_job_t& finish_job,
        uint64_t* join_wait_cycles) {  // T5 accumulator, nullptr when stats are off
      auto& workload = q_batch->hw_plan;
      auto const& sections_left = plan_for(q_batch, operation).sections_left[kv_head];
      const size_t n_batch_jobs = q_batch->items.size();
      // See Note [HW attention operation completion].
      const uint64_t expected = hw_attention_completion_generation(operation);

      // One entry per batch job of this worker's stride, kept across calls:
      // this runs once per kv head per layer on a pool thread.
      static thread_local std::vector<hw_join_cursor> cursors;
      cursors.clear();
      for (size_t batch_job_ix = rank; batch_job_ix < n_batch_jobs;
          batch_job_ix += n_join_workers) {
        TRON_ASSERT_LE(
            workload.by_job[batch_job_ix].devices.size(), hardware::MAX_DEVICES);
        cursors.push_back(hw_join_cursor{});
      }
      const size_t n_jobs = cursors.size();
      auto job_of = [&](size_t j) { return rank + j * n_join_workers; };

      auto slot = [&](size_t pass_ix, size_t batch_job_ix) {
        return hw_token_scratchpad_ref_at(
            workload.passes[pass_ix].scratchpad_ix, batch_job_ix);
      };
      auto completed = [&](size_t pass_ix) {
        return workload.complete[pass_ix].load(std::memory_order_acquire) >= expected;
      };
      // Completed, and not mid-decode by another worker.
      auto ready = [&](size_t pass_ix, size_t batch_job_ix) {
        if (!completed(pass_ix)) return false;
        auto& scratchpad = hw_attn_results_at(workload.passes[pass_ix].scratchpad_ix);
        return scratchpad.unpack_state[batch_job_ix].load(std::memory_order_acquire) !=
               1;
      };

      size_t n_open = n_jobs;
      bool software_ready = false;
      while (n_open > 0) {
        bool progressed = false;
        // Acquires every software producer's scratchpad writes through the
        // sections_left RMW release sequence. Never touch SW scratchpads early.
        software_ready =
            software_ready || sections_left.load(std::memory_order_acquire) == 0;
        for (size_t j = 0; j < n_jobs; ++j) {
          hw_join_cursor& cursor = cursors[j];
          if (cursor.done) continue;
          const size_t batch_job_ix = job_of(j);
          auto const& groups = workload.by_job[batch_job_ix].devices;
          if (software_ready && !cursor.software_joined) {
            join_software<hardware_geometry>(kv_head, batch_job_ix, n_attn_workers);
            cursor.software_joined = true;
            progressed = true;
          }
          bool all_folded = true;
          for (size_t d = 0; !cursor.hardware_joined && d < groups.size(); ++d) {
            auto const& pass_ixs = groups[d].pass_ixs;
            uint32_t& next = cursor.next[d];
            while (next < pass_ixs.size()) {
              const size_t pass_ix = pass_ixs[next];
              if (!completed(pass_ix)) break;
              if (!try_unpack_hw_pass(q_batch, pass_ix, batch_job_ix)) break;
              if (next > 0) {
                token_scratchpad_ref<hardware_geometry> accumulator =
                    slot(pass_ixs.front(), batch_job_ix);
                token_scratchpad_ref<hardware_geometry> source =
                    slot(pass_ix, batch_job_ix);
                join_page_ranges(accumulator, source, kv_head);
              }
              ++next;
              progressed = true;
            }
            if (next != pass_ixs.size()) all_folded = false;
          }
          if (!all_folded) continue;
          if (!cursor.hardware_joined) {
            if (!groups.empty()) {
              auto target = slot(groups.front().pass_ixs.front(), batch_job_ix);
              for (size_t d = 1; d < groups.size(); ++d) {
                auto source = slot(groups[d].pass_ixs.front(), batch_job_ix);
                join_page_ranges(target, source, kv_head);
              }
            }
            cursor.hardware_joined = true;
            progressed = true;
          }
          if (!cursor.software_joined) continue;
          token_scratchpad_ref<hardware_geometry> target =
              token_scratchpad_ref_at<hardware_geometry>(0, batch_job_ix);
          if (!groups.empty()) {
            token_scratchpad_ref<hardware_geometry> accumulator =
                slot(groups.front().pass_ixs.front(), batch_job_ix);
            join_page_ranges(target, accumulator, kv_head);
          }
          finish_job(batch_job_ix);
          cursor.done = true;
          --n_open;
          progressed = true;
        }
        if (progressed) continue;
        // Watch both producers: SW can finish while HW is pending, and any
        // device or job can become ready while software is still computing.
        TRACE_EVENT("hwattention", "attention: join wait", "open jobs", n_open);
        // T5: this loop is the only pure waiting in the hardware join. It ends
        // when a hardware pass or the software partials become ready. The
        // software-only join times its poll in run_joins instead.
        const uint64_t t_wait =
            join_wait_cycles ? hardware::system::rdtsc() : attn_stats::UNSET_CYCLES_0;
        bool any_ready = false;
        while (!any_ready) {
          if (!software_ready && sections_left.load(std::memory_order_acquire) == 0)
            break;
          for (size_t j = 0; j < n_jobs && !any_ready; ++j) {
            hw_join_cursor const& cursor = cursors[j];
            if (cursor.done) continue;
            const size_t batch_job_ix = job_of(j);
            auto const& groups = workload.by_job[batch_job_ix].devices;
            for (size_t d = 0; d < groups.size() && !any_ready; ++d)
              if (cursor.next[d] < groups[d].pass_ixs.size())
                any_ready = ready(groups[d].pass_ixs[cursor.next[d]], batch_job_ix);
          }
        }
        if (join_wait_cycles) *join_wait_cycles += hardware::system::rdtsc() - t_wait;
      }
    }

    // See Note [Computing self-attention]
    template <attention_geometry geometry, typename query_buffer_t>
    void run_sections(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        const size_t worker_ix,
        size_t n_attn_workers,
        bool uses_hw,
        bool pending) {
      const attention_binding binding = operation.binding;
      // See Note [Ready versus pending attention work]
      auto& plan_state = plan_for(q_batch, binding.operation);
      // The plan must have been assembled for the same worker count the
      // workers were launched with.
      TRON_ASSERT_EQ(plan_state.ready_kv_plan.size(), n_attn_workers);
      auto const& plan = pending ? plan_state.pending_kv_plan[worker_ix]
                                 : plan_state.ready_kv_plan[worker_ix];
      MODEL_DEBUG("{} layer {} qbatch [{}]", __PRETTY_FUNCTION__, binding.model_layer,
          fmt::join(q_batch->items, ","));
      for (const kv_section& section : plan) {
        apply_page_range<geometry>(q_batch->items, operation, queries, section.kv_head,
            worker_ix, n_attn_workers, section.page_ixs, section.work_estimate,
            q_batch->items_mask, uses_hw, pending, section.q_begin, section.q_end);
        plan_state.sections_left[section.kv_head]--;
      }
    }

    template <attention_geometry geometry, typename output_buffer_t>
    void run_joins(batch* q_batch,
        attention_operation_descriptor const& operation,
        output_buffer_t& output,
        size_t worker_ix,
        size_t n_attn_workers,
        bool uses_hw,
        bool stats_enabled) {
      const attention_binding binding = operation.binding;
      const model_layer_id layer = binding.model_layer;
      uint64_t join_wait_cycles =
          attn_stats::UNSET_CYCLES_0;  // T5 of this job, over its kv heads
      // This is the join part; see Note [Computing self-attention].
      //
      // Note [Attention join parallelism scheme]
      // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      //
      // After all the `run_sections` calls are done, we will have some
      // partially-computed attention values (elements of the softmax
      // monoid over v_star), and we need to finish the reduction.  To
      // wit, for a given q_batch,
      // - For every token in q_batch->items
      // - For every query head
      // - For every run_sections worker
      // - The softmax monoid state is accessible via
      //   `token_scratchpad_at(worker_ix, token_ix)[head]`, which returns a
      //   `scratchpad_ref` containing references to v_star, s_star, and m_star.
      // - This data is valid if the bit for this _kv_head_ is set in
      //   `attn[worker_ix].valid`, because validity changes with
      //   kv-head granularity, rather than query head granularity.
      // - Also, for every hardware attention pass in the hw_workload
      //   - Results for that token, head, and pass are available in
      //     `hw_token_scratchpad_ref_at(scratchpad_ix, token_ix)[head]`,
      //     which is also a `scratchpad_ref`.
      // - If it is not valid, we should treat it as the monoid identity, i.e.
      //   zeros, zero, -inf, respectively.
      // - A given scratchpad may be invalid if that worker did not process any
      //   KV data pertaining to that q_batch token.
      // - Hardware pass results are folded in as the passes complete, per
      //   device; see Note [Streaming hardware attention join].
      //
      // After all the `run_joins` calls are done, we want to have reduced
      // all of this.  Namely,
      // - For each token in q_batch->items
      // - For every query head
      // - We want the 0th scratchpad to contain the join of all the data in
      //   all valid scratchpads for that token and that query head, and then
      //   we want to call `attn[0].finish` on that data to write it into
      //   the location where the answer ultimately goes.
      //
      // But, being persnickety about performance as we are, we want
      // to parallelize the join work too.  Thus, the same worker
      // threads that computed the sections are reused for running
      // joins, parallelizing across tokens.
      //
      // But, being very persnickety about performance, we assign each
      // worker to do only those kv heads that this same thread has
      // worked on before, in hopes of hitting the core's L2 cache as
      // best we can.
      //
      // The assignment is in the q_batch:
      // - kv_heads_to_join is a mask of kv heads to work on indexed by worker
      // - join_workers is a mask of which workers are assigned to that kv head,
      //   so they can partition the tokens among themselves deterministically.
      //
      // Also, since worker A may finish their `run_sections` and
      // start their `run_joins` before another worker B touching some
      // of the same kv heads did, we poll
      // `plan_state.sections_left[kv_head]` among our assigned kv heads
      // to see which ones are actually all done.
      const size_t n_batch_jobs = q_batch->items.size();
      auto& plan_state = plan_for(q_batch, binding.operation);
      // SW-only layers never dispatched HW, so complete[] would never flip.
      const bool join_hw = uses_hw && !q_batch->hw_plan.empty();
      TRON_ASSERT(!join_hw || q_batch->hw_plan.by_job.size() == n_batch_jobs,
          "HW plan indexes {} jobs for a batch of {}", q_batch->hw_plan.by_job.size(),
          n_batch_jobs);
      mask_t<64> kv_heads_to_join = plan_state.kv_heads_to_join[worker_ix];
      // T5 on a software-only join: one stretch of waiting = consecutive failed
      // polls with no join progress in between, over all of this worker's kv
      // heads. Folding head B while head A is still pending is work, not
      // waiting, so stretches never overlap and their sum stays below the
      // job's wall time. With join_hw the poll is skipped and stream_hw_joins
      // times its own wait loop into the same accumulator, so nothing is
      // counted twice. Off state: no rdtsc. One test of stats_enabled per
      // failed poll, and one test of poll_waiting per kv head joined (also in
      // the hardware join, where the poll is skipped).
      bool poll_waiting = false;
      uint64_t t_poll = attn_stats::UNSET_CYCLES_0;
      while (!kv_heads_to_join.empty())
        for (size_t kv_head : kv_heads_to_join) {
          if (!join_hw && plan_state.sections_left[kv_head]) {  // poll
            if (stats_enabled && !poll_waiting) {
              poll_waiting = true;
              t_poll = hardware::system::rdtsc();
            }
            continue;
          }
          if (poll_waiting) {  // a successful poll closes the stretch
            join_wait_cycles += hardware::system::rdtsc() - t_poll;
            poll_waiting = false;
          }
          TRACE_EVENT("model", "attention: join", "worker_ix", worker_ix, "layer",
              layer.i, "kv_head", kv_head);
          const size_t n_join_workers = plan_state.join_workers[kv_head].count();
          const size_t rank = plan_state.join_workers[kv_head].index(worker_ix);
          // All partials have been folded into worker 0's scratchpad.
          // Apply sinks and write the normalized result.
          auto finish_job = [&](size_t batch_job_ix) {
            // Note [Garbage attention scores corner case]
            // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            //
            // If `run_sections` did not mark any scratchpads valid for this
            // kv_head, then `join_page_ranges` won't either, and `finish` will
            // write garbage.  That normally can't happen, because even the first
            // token of a sequence attends to itself, so there's always a page
            // that affects every q token.
            //
            // However, Eagle models skip the first k token.  Moreover,
            // there's a further exception,
            // see Note [EAGLE first token exception], which causes them
            // to compute the first k token afterall on sequences of length 1.
            //
            // Ergo, either that works out to always give us at least one
            // valid scratchpad, or it's so rare that we haven't found any
            // crashes in testing so it doesn't matter.
            if constexpr (sinks) {
              auto const& runtime_config =
                  enclosing_state.attention_runtime_configs[binding.operation];
              if (!runtime_config.sinks.empty())
                apply_attn_sinks<geometry>(batch_job_ix, runtime_config.sinks, kv_head);
            }
            attn[0].template finish<geometry>(
                output, q_batch->items[batch_job_ix], kv_head, batch_job_ix);
          };
          auto finish_all_jobs = [&] {
            for (size_t batch_job_ix = rank; batch_job_ix < n_batch_jobs;
                batch_job_ix += n_join_workers) {
              join_software<geometry>(kv_head, batch_job_ix, n_attn_workers);
              finish_job(batch_job_ix);
            }
          };
          if constexpr (geometry == hardware_geometry) {
            if (join_hw) {
              // Keep normalization out of the streaming loop's register set.
              auto finish_hw_job = [&](size_t batch_job_ix)
                                       TRON(noinline) { finish_job(batch_job_ix); };
              stream_hw_joins(q_batch, binding.operation, kv_head, rank, n_join_workers,
                  n_attn_workers, finish_hw_job,
                  stats_enabled ? &join_wait_cycles : nullptr);
            } else
              finish_all_jobs();
          } else {
            TRON_ASSERT(!join_hw, "heterogeneous geometry cannot use HW attention");
            finish_all_jobs();
          }
          kv_heads_to_join.erase(kv_head);
        }
      if (stats_enabled) {
        stats->note_join_wait(
            stats->pool_worker(worker_ix, n_attn_workers), layer.i, join_wait_cycles);
      }
      /**
       * Note [TODO: Improving parallelism in self-attention reduction]
       * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
       * We could eke out a little more parallelism from the reduction section by
       * setting up a deterministic balanced binary tree (per KV head) of the
       * pattern in which the sections will be joined up.  Each section (except section
       * 0) will be the argument to another's `join` operation exactly once.  One
       * pattern we could choose is that for each i > 0, section i will be joined into
       * section j, where j is i with its least significant one bit set to zero.  We do
       * this in order from least to most significant bits.
       *
       * For example, for 6 sections, we would get this pattern, where each row can
       * happen in parallel:
       *   0.join(1), 2.join(3), 4.join(5)
       *   0.join(2)
       *   0.join(4)
       * If we had 8 sections, it would be
       *   0.join(1), 2.join(3), 4.join(5), 6.join(7)
       *   0.join(2), 4.join(6)
       *   0.join(4)
       *
       * Implementation:
       * - Index the necessary joins by the second argument, since that's unique.
       * - For each join, we would track one of 4 states: 0-2 inputs ready, and join
       *   complete (which we code as 3).
       * - When a worker finishes any item of work, it searches through the joins whose
       *   data dependency it just finished to see if one is ready, and if so does it.
       */
    }

    /**
     * Note [Attention Sequence Parallelism]
     * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     *
     * We modify the attention definition described in
     * Note [Computing self-attention], iterating by KV-cache pages rather
     * than query positions, and processing all the relevant query positions
     * for each KV-cache page. In pseudo-code this is:
     *
     *   int page_size = 64
     *   bvector<num_heads * head_size> v_stars[num_tokens] = zeros
     *   for each head in attention heads:  // Parallel across KV heads
     *     float s_stars[num_tokens] = zeros
     *     float m_stars[num_tokens] = [each -inf]
     *
     *     for each page in KV pages:
     *       for each query location j in locations affected by p:
     *         float q = queries[j][{slice for head}]
     *         float& v_star = v_stars[j][{read-write slice for head}]
     *         float& s_star = s_stars[j]  // Read-write alias
     *         float& m_star = m_stars[j]  // Read-write alias
     *
     *         // N.B. -inf is the identity of max in case the page isn't full
     *         float& s_temp[page_size] = [each -inf]
     *         for each kv entry i in page:
     *           if kv entry affects query location j:
     *             float k = page.k[layer][i][{slice for kv head}]
     *             s_temp[i] = operation_scale * dot(q, k)
     *
     *         // m accounting for this page
     *         float m_page = max(max(s_temp), m_star)
     *         float exp_s_minus_m[page_size] = exp(s_temp - m_page)
     *         float exp_m_star_minus_m = exp(m_star - m_page)
     *         v_star = v_star * exp_m_star_minus_m
     *         for each kv entry i in page:
     *           v_star += page.v[layer][i][{slice for kv head}] * exp_s_minus_m[i]
     *         s_star = s_star * exp_m_star_minus_m + sum(exp_s_minus_m)
     *         m_star = m_page
     *
     *     // N.B. this is implemented in page::scaled_v as a page_size-way
     *     // SIMD computation.
     *     for each token position i:
     *       results[i][{write slice for head}] =
     *         v_stars[i][{read slice for head}] / s_stars[i]
     *
     * This is implemented in apply_page_range and join_page_ranges, which form a
     * parallel-reduction pair along the KV-page dimension of the KV cache.  (We of
     * course also parallelize among KV heads, but that's embarassingly easy.)
     *
     * The correctness invariant is that, for appropriate section numbers A and B any
     * range R of KV cache pages, the following are equivalent up to floating-point:
     * - Calling `apply_page_range(A, R)` once
     * - Splitting R into R1 and R2, calling `apply_page_range(A, R1)`, calling
     *   `apply_page_range(B, R2)`, then calling `join_page_range(A, B)`. The two
     *   `apply_page_range` calls can be parallel.
     *
     * The only observable difference between these is the use of the scratchpad memory
     * in section B, but the results in the scratchpad memory in section A must be the
     * same (again, up to floating-point).
     *
     * The memory management scheme is as follows.  Recall that the state of the
     * deferred softmax reduction carried across KV pages is
     * - v*, the running result for every attention head corresponding to this KV head
     *   (head size 128 * GQA factor 4 * bf16 size 2 = 1024 bytes per KV head
     *   in Mixtral);
     * - s*, the running normalization term
     *   (currently coded as one fp32s per attention head, making it
     *   GQA factor 4 * float size 4 * SIMD width 8 = 64 bytes per KV head); and
     * - m*, the running maximum score as a float (GQA factor 4 * float size 4 = 16
     *   bytes per KV head).
     *
     * We need one block of this memory per section of pages.
     *
     * Just allocating these in each task is too slow, so we preallocate all of them
     * in `state`, as the `attn` vector of `attn_accum` instances.  `attn` is indexed by
     * worker.  We take care not to read the content of a freshly appropriated
     * scratchpad, so as to avoid having to zero them.
     *
     * Finally, `attn_accum` instances index their slots by _token index in the
     * minibatch_, not the global token index.  This is safe because they are only
     * used to do one minibatch at a time, and saves memory and allocation cost.
     *
     * Note that Group-Query Attention means any given KV head serves several
     * query heads.  We parallelize over KV heads, since that's the memory
     * bottleneck, and serially loop over corresponding query heads.
     *
     */
    template <attention_geometry geometry, typename query_buffer_t>
    void apply_page_range(std::vector<token_job_id> const& items,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        size_t kv_head,
        size_t scratchpad,
        size_t n_attn_workers,
        const auto& page_range,  // vector<page_id> or span<page_id>
        work_estimate_t work_estimate,
        const mask_t<ranged_mask_capacity>& batch_queries,
        bool uses_hw = false,
        bool pending = false,
        size_t q_begin = 0,
        size_t q_end = SIZE_MAX) noexcept {
      const attention_binding binding = operation.binding;
      // Attention path stats (Note [Attention path stats] in attn_stats.hpp).
      // This bool, copied once per call, gates every per-visit hook below. The
      // row key (the pool worker of this attention worker) and the path-bit
      // span of that row are hoisted here too; the off state computes neither.
      attn_stats::model_stats& stats_ref = *stats;
      const bool stats_enabled = stats_ref.enabled;
      attn_stats::visit_tally stats_tally;
      const size_t stats_worker =
          stats_enabled ? stats_ref.pool_worker(scratchpad, n_attn_workers)
                        : attn_stats::model_stats::NO_WORKER;
      uint8_t* path_bits = stats_enabled ? stats_ref.token_path_span(stats_worker,
                                               enclosing_state.token_jobs.size())
                                         : nullptr;
      // MODEL_DEBUG("{} layer {} kv_head {} scratchpad {} qbatch [{}]",
      // __PRETTY_FUNCTION__, layer, kv_head, scratchpad,
      // fmt::join(q_batch->items,","));
      TRACE_EVENT("model",
          perfetto::StaticString(pending ? "Attention Pending" : "Attention Ready"),
          "layer", binding.model_layer.i, "kv head", kv_head,
          // The scratchpad is the attention worker index; see
          // Note [Attention workers are the last pool workers] in model.hpp.
          "app thread id", app_pool().num_workers() - n_attn_workers + scratchpad,
          "relevant q tokens", work_estimate.scaled_vs, "dot products",
          work_estimate.k_dot_products, "pages",
          work_estimate.kv_heads,  // KV heads are counted in pages here
          // Bounds also exclude queries with no software work on these pages.
          "q begin", q_begin, "q end", std::min(q_end, items.size()));
      const ranged_mask* query_mask = enclosing_state.query_mask;
      TRON_ASSERT(query_mask && !query_mask->empty(),
          "query_mask must be populated before attention");
      q_end = std::min(q_end, items.size());
      if (page_range.empty() || q_begin >= q_end) return;
      int const sliding_window_size =
          enclosing_state.attention_runtime_configs[binding.operation]
              .sliding_window_size;
      bool const run_visible_in_software =
          sliding_window_size < illegal_sliding_window || !uses_hw;
      const float operation_scale = operation.config.scale;
      // One intersection of the batch's query mask with a mask range says
      // whether the range holds any work for this batch, so the pages of a
      // range without work are dismissed without visiting their entries: in a
      // hardware layer the resident context is one such range and covers most
      // pages. The decision reads the same masks apply_page_tok consults.
      // Skipped for small sections, where the walk costs less than the
      // intersection.
      const bool dismiss_workless_ranges = page_range.size() * items.size() >= 64;
      auto range_has_work = [&](const token_range& range) {
        return run_visible_in_software ? range.any_visible(batch_queries)
                                       : range.any_sw_required(batch_queries);
      };
      const token_range* page_end_hint = &query_mask->find_range(
          enclosing_state.pages[page_range.front()]->at_offset(0));
      const token_range* flagged_range = page_end_hint;
      bool flagged_has_work =
          dismiss_workless_ranges ? range_has_work(*flagged_range) : true;
#ifdef TRON_PAGE_SHARE_COUNTERS
      page_share::page_visit_counts visit_counts;
#endif
#ifdef TRON_AMX_DISPATCH
      // AMX fast path for dense pages of the head-128 / kv_mul-4 shape on a
      // bf16 Q buffer; see Note [AMX attention dispatch]. Each token's Q
      // group is packed once per call, at its first page that passes the
      // outer checks below (visible, inside the window) and before that
      // page's dense predicate; later pages reuse it (packed_amx_query). The
      // tile configuration is held for the whole call (one uninterrupted
      // region).
      constexpr bool amx_eligible =
          amx_attn_h128g4::eligible<typename model::activation_scalar>(
              geometry.kv.head_size, geometry.kv_mul());
      const bool amx_on = amx_eligible && amx_attn_h128g4::available();
      // Packed-Q storage: this worker's scratchpad slots (attn_accum::amx_qpack),
      // one 4096-byte slot per token of the minibatch, indexed by
      // batch_job_ix like v_stars. Only this worker touches attn[scratchpad]
      // during this call (Note [Attention workers are the last pool workers]).
      auto& amx_qpack = attn[scratchpad].amx_qpack;
      // Which tokens of this call already have their Q group packed. A
      // std::bitset rather than mask_t because mask_t<N> exists for N <= 128,
      // 512 and 4096 only, while max_minibatch_size is set per plugin: 128 in
      // llama.hpp, 1024 for the mock plugin and every ingested plugin.
      std::bitset<max_minibatch_size> amx_packed;
      if (amx_on) {
        TRON_ASSERT_LE(items.size(), max_minibatch_size);
        // resize() zero-fills new slots and the packer writes only the 4
        // live columns of each slot, so the padding it relies on stays zero
        // (see the pack contract in amx_attn_iface.hpp).
        amx_qpack.resize(items.size());
        amx_attn_h128g4::begin_region();
      }
      // Release the tile configuration on every exit from this function,
      // including an early return added later.
      tron::finally end_amx_region([&] {
        if (amx_on) amx_attn_h128g4::end_region();
      });
#endif
      for (page_id page_ix : page_range) {
        page& page = *(enclosing_state.pages[page_ix]);
        const size_t n_entries = page.count();
        // Find the range covering this page's first entry once per page.
        // Consecutive pages are typically in the same or adjacent range,
        // so the hint avoids a binary search in the common case.
        const token_range* page_begin_hint =
            &query_mask->find_range(page.at_offset(0), *page_end_hint);
#ifdef TRON_PAGE_SHARE_COUNTERS
        uint64_t n_relevant_query_tokens = 0;
#endif
        if (dismiss_workless_ranges && page_begin_hint != flagged_range) {
          flagged_range = page_begin_hint;
          flagged_has_work = range_has_work(*flagged_range);
        }
        // A range boundary may fall inside the page: the first token's range
        // speaks for the whole page only when the last entry is in it too.
        const bool page_in_one_range =
            n_entries == 0 || page.at_offset(n_entries - 1) < page_begin_hint->tok_hi;
        if (n_entries == 0 || (page_in_one_range && !flagged_has_work)) {
          page_end_hint = page_begin_hint;
          continue;
        }
        // Page-level visibility gate. The first token's range is exact when
        // visibility only narrows along the page, the common case. A fresh
        // page has one range per token, so the union over its ranges costs an
        // OR per range: compute it only when a query fails the first-token
        // test, and then once per page. apply_page_tok resolves SW vs HW per
        // range.
        bool have_page_visible = false;
        mask_t<ranged_mask_capacity> page_visible;
        for (size_t batch_job_ix = q_begin; batch_job_ix < q_end; batch_job_ix++) {
          token_job_id tok_ix = items[batch_job_ix];
          token_id q_tok = enclosing_state.token_jobs[tok_ix];
          bool sees_page = page_begin_hint->visible(tok_ix);
          if (!sees_page && !page_in_one_range) {
            if (!have_page_visible) {
              query_mask->for_each_range_run(page.at_offset(0), n_entries,
                  *page_begin_hint, [&](const token_range& range, size_t, size_t) {
                    page_visible = page_visible | range.sw_mask() | range.hw_mask();
                    return false;
                  });
              have_page_visible = true;
            }
            sees_page = page_visible.contains(tok_ix.i);
          }
          if (!sees_page) continue;
          uint32_t q_position = enclosing_state.token_positions[q_tok];
          uint32_t k_position = enclosing_state.token_positions[page.at_offset(0)];
          if ((int)q_position - (int)(k_position + page.count()) >= sliding_window_size)
            // The entire page is definitely outside the sliding window
            continue;
          if (enclosing_state.model_ref.plugin.is_eagle) {
            // EAGLE models skip the first k token of the sequence.
            // See Note [EAGLE first token exception].  If that would cause this
            // page to have no valid k tokens, that qualifies as "page does not affect
            // the q token", so skip it.  Failing to do this causes NANs in the corner
            // case where my sequence shares a 1-token common prompt with another
            // sequence.
            if (k_position == 0 && q_position != 0 && page.count() == 1) continue;
          }
          const auto& q = queries[tok_ix].as_view();
          token_scratchpad_ref<geometry> sp =
              token_scratchpad_ref_at<geometry>(scratchpad, batch_job_ix);
          bool was_valid = sp.is_valid_for(kv_head);
          const bf16* amx_qp = nullptr;
#ifdef TRON_AMX_DISPATCH
          if constexpr (amx_eligible) {
            if (amx_on) {
              amx_qp = packed_amx_query<geometry>(
                  amx_qpack[batch_job_ix].v, amx_packed, batch_job_ix, kv_head, q);
            }
          }
#endif
          const page_tok_result visit = apply_page_tok<geometry>(was_valid, page,
              operation, operation_scale, kv_head, q, q_tok, sp, tok_ix,
              page_begin_hint, sliding_window_size, run_visible_in_software, amx_qp);
          const int relevant_k_tokens = visit.relevant_k_tokens;
          page_end_hint = visit.hint;
          if (stats_enabled) {
            stats_tally.record(visit.served, relevant_k_tokens, page::page_size);
            path_bits[tok_ix.i] |= attn_stats::path_bit(visit.served);
          }
#ifdef TRON_PAGE_SHARE_COUNTERS
          if (relevant_k_tokens > 0) n_relevant_query_tokens++;
#endif
          if (relevant_k_tokens > 0 && !was_valid) {
            // Mark valid only once a real score has landed: m_star must have
            // advanced past the -inf identity for at least one head in the
            // group.  Without this, a scratchpad can be marked valid while
            // m_star is still -inf, tripping the -inf assert when
            // join_page_ranges reduces the workers into worker 0 (seen with
            // multi-token q_batches under multiple resident users).
            // TODO: root-cause how a valid scratchpad reaches join with -inf
            // m_star; this gates the symptom, not the cause.
            bool has_data = false;
            for (size_t h = kv_head * geometry.kv_mul();
                h < (kv_head + 1) * geometry.kv_mul(); ++h)
              has_data |= (sp[h].m_star != -std::numeric_limits<float>::infinity());
            if (has_data) sp.mark_valid_for(kv_head);
          }
        }
#ifdef TRON_PAGE_SHARE_COUNTERS
        visit_counts.record_page_visit(n_relevant_query_tokens, pending);
#endif
      }
#ifdef TRON_PAGE_SHARE_COUNTERS
      visit_counts.flush();
#endif
      if (stats_enabled) {
        // stats_worker is the pool worker of this attention worker (one to one
        // inside a forward), so the row is written by its owner only.
        stats_ref.add_visits(stats_worker, binding.model_layer.i, stats_tally,
            pending ? attn_stats::PASS_PENDING_1 : attn_stats::PASS_READY_0);
      }
    }

#ifdef TRON_AMX_DISPATCH
    // Returns this token's packed Q group for kv_head, packing it on the first
    // request of the call (`packed` records which tokens are done). `slot` is
    // the token's 4096-byte buffer in the worker's attn_accum::amx_qpack; the
    // packer reads q as bf16 (see query_scalar_ok).
    template <attention_geometry geometry>
    TRON(inline)
    const bf16* packed_amx_query(bf16* slot,
        std::bitset<max_minibatch_size>& packed,
        size_t batch_job_ix,
        size_t kv_head,
        const auto& q) noexcept {
      static_assert(amx_attn_h128g4::query_scalar_ok<typename model::activation_scalar>,
          "the AMX query packer reads q.data as bf16");
      if (!packed.test(batch_job_ix)) {
        amx_attn_h128g4::pack_q_group_128x4(
            q.data + kv_head * geometry.kv_mul() * geometry.kv.head_size, slot);
        packed.set(batch_job_ix);
      }
      return slot;
    }

    // The dense-page predicate of Note [AMX attention dispatch]: the whole
    // 64-token page is active (begin == 0, end == page_size), the query sees
    // all of it through one visible range, and the whole page is inside the
    // query's sliding window.
    // Only such pages take the AMX path; everything else runs the dotter loop.
    // Shape, activation type and runtime availability are checked separately
    // (eligible, available), before this predicate is reached.
    TRON(inline)
    static bool is_dense_amx_page(const page& pg,
        size_t begin,
        size_t end,
        bool query_visible,
        const token_range& range,
        uint32_t q_position,
        uint32_t k_position,
        int sliding_window_size) noexcept {
      return begin == 0 && end == page::page_size && query_visible &&
             pg.at_offset(page::page_size - 1) < range.tok_hi &&
             (int)q_position - (int)k_position < sliding_window_size;
    }

    // The whole AMX path for one (query, page) pair: the QK kernel, the same
    // scale / max / exp step as the dotter, the PV kernel, and the update of the
    // running-softmax state. The caller has already checked that a packed Q
    // exists and that the page is dense (is_dense_amx_page), so this function
    // always applies the page.
    // was_valid: whether the scratchpad already holds a running-softmax state
    // (v*, s*, m*) for this query token and kv_head from earlier pages. When
    // true, this page is folded into that state; when false, this page starts
    // it. apply_page_range computes it as sp.is_valid_for(kv_head).
    template <attention_geometry geometry>
    TRON(inline)
    void apply_dense_amx_page(bool was_valid,
        const page& pg,
        kv_slot_id slot,
        float operation_scale,
        size_t kv_head,
        token_scratchpad_ref<geometry>& scratchpad,
        const bf16* q_packed) noexcept {
      constexpr size_t operation_kv_mul = geometry.kv_mul();
      constexpr size_t operation_head_size = geometry.kv.head_size;
      static_assert(amx_attn_h128g4::eligible<typename model::activation_scalar>(
                        operation_head_size, operation_kv_mul),
          "the dense AMX page path exists only for the AMX shape on bf16 Q");
      static_assert(amx_attn_h128g4::PAGE_TOKENS_64 == page::page_size,
          "the AMX kernels assume the KV page size");
      // QK for the whole page in one kernel call. The kernel writes the raw
      // scores, not yet multiplied by the attention scale, into
      // s_pages[head][token], the same array and layout the dotter loop fills.
      // It reads K straight from storage: the argument is this (slot, kv_head)'s
      // whole K plane, a const_native_k_view of 64 consecutive 128-dim rows.
      // This is the only place where the AMX path depends on K being stored as
      // consecutive rows, and the view type states that layout at the call.
      tensor<operation_kv_mul, page::page_size> s_pages;
      // Both kernels take &s_pages[0][0] with row stride page_size, so the 4
      // rows of 64 floats must be consecutive with no padding. The size check
      // forces both: 4 x 64 x 4 bytes leaves no room for a gap.
      static_assert(
          sizeof(s_pages) == operation_kv_mul * page::page_size * sizeof(float),
          "the AMX kernels read s_pages as one block: rows must be consecutive");
      amx_attn_h128g4::qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head),
          q_packed, &s_pages[0][0], page::page_size);
      // Scale (or softcap), page max, exp and sum per head: the same math as
      // the dotter epilogue in apply_page_tok, on the AMX scores.
      float corr_arr[operation_kv_mul], m_new_arr[operation_kv_mul],
          sum_arr[operation_kv_mul];
      for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
        tensor<page::page_size>& s_page = s_pages[offset];
        scratchpad_ref<geometry> head_sp =
            scratchpad[kv_head * operation_kv_mul + offset];
        if constexpr (softcapping) {
          auto softcap = enclosing_state.plugin_state.model.attn_logit_softcapping;
          s_page = tanh(s_page * (operation_scale / softcap)) * softcap;
        } else {
          s_page = s_page * operation_scale;
        }
        float m_page = max(s_page);
        if (was_valid) m_page = std::max(head_sp.m_star, m_page);
        s_page = exp(s_page - m_page);
        m_new_arr[offset] = m_page;
        sum_arr[offset] = sum(s_page);
        corr_arr[offset] = was_valid ? std::exp(head_sp.m_star - m_page) : 0.f;
      }
      // PV for the 4 heads in one tile call, reading the page's packed V plane
      // in place (v_packed). See Note [Tile stores write 16 rows]: only rows
      // 0..3 of amx_o carry the result.
      alignas(64) float amx_o[amx_attn_h128g4::TILE_ROWS_16 * operation_head_size];
      amx_attn_h128g4::weights_times_v_128x4(
          pg.template v_packed<geometry.kv>(slot, kv_head), &s_pages[0][0],
          page::page_size, amx_o);
      // The v*/s*/m* update, from the AMX PV output instead of scaled_v.
      for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
        scratchpad_ref<geometry> head_sp =
            scratchpad[kv_head * operation_kv_mul + offset];
        tensor<operation_head_size> scratch;
        std::memcpy(&scratch[0], amx_o + offset * operation_head_size,
            operation_head_size * sizeof(float));
        if (was_valid) {
          auto corr_ = constant<page::page_size>(corr_arr[offset]);
          head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
          head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
        } else {
          head_sp.v_star.set(scratch);
          head_sp.s_star = sum_arr[offset];
        }
        head_sp.m_star = m_new_arr[offset];
      }
    }
#endif

    // What one apply_page_tok call did: how many K tokens were relevant, the
    // range hint to continue from, and which path served the visit (the AMX
    // kernel, the AVX dotter loop, or none: an empty visit).
    struct page_tok_result {
      const token_range* hint;
      int relevant_k_tokens;
      attn_stats::visit_path served;
    };
    static_assert(
        sizeof(page_tok_result) == sizeof(std::pair<int, const token_range*>) &&
            std::is_trivially_copyable_v<page_tok_result>,
        "page_tok_result must stay as small as the pair it replaced");

    // Minimum iota of work for paged attention: apply one KV head of one page to
    // the attention-score accumulator of one token.  This incorporates
    // the deferred-softmax trick, whose extra state is carried by the scratchpad.
    // Returns {number of relevant k tokens, final range hint, path}.
    template <attention_geometry geometry>
    TRON(inline)
    page_tok_result apply_page_tok(bool was_valid,
        const page& page,
        attention_operation_descriptor const& operation,
        float operation_scale,
        size_t kv_head,
        const auto& q,
        token_id q_tok,
        token_scratchpad_ref<geometry>& sp,
        token_job_id job_ix,
        const token_range* range_hint,
        int sliding_window_size,
        bool run_visible_in_software,
        tron_maybe_unused const bf16* amx_q_packed) {
      constexpr size_t operation_kv_mul = geometry.kv_mul();
      constexpr size_t operation_head_size = geometry.kv.head_size;
      const attention_binding binding = operation.binding;
      const kv_slot_id slot = binding.kv_slot;
      size_t begin = 0;
      // TODO: This position collection is now violating the framework-plugin
      // abstraction.  Should we extend the API, or can we find a way to
      // move this into the plugin?
      uint32_t q_position = enclosing_state.token_positions[q_tok];
      uint32_t k_position = enclosing_state.token_positions[page.at_offset(0)];
      if (enclosing_state.model_ref.plugin.is_eagle) {
        // Note [EAGLE first token exception]
        // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        //
        // EAGLE models skip the first k token, but doing so for the
        // first q token would cause NANs, so we perform and discard
        // the k=q=0 case.
        if (k_position == 0 && q_position != 0) begin = 1;
      }
      // page.count() tracks active entries during traversal, skipping stale
      // entries from other branches.
      size_t end = page.count();

      // Start from the range hint; advance through entries.
      bool query_visible = run_visible_in_software ? range_hint->visible(job_ix)
                                                   : range_hint->sw_required(job_ix);
#ifdef TRON_AMX_DISPATCH
      // Two gates decide here whether this (query, page) pair takes the AMX
      // path: a packed Q must exist (it is null when AMX is unavailable or
      // disabled) and the page must be dense (is_dense_amx_page). When both
      // hold, apply_dense_amx_page does the whole page (QK, softmax step, PV,
      // accumulator update) and we return; every other pair falls through to
      // the dotter loop below. The `if constexpr` keeps the AMX code out of
      // every other geometry's and activation type's instantiation. See
      // Note [AMX attention dispatch].
      if constexpr (amx_attn_h128g4::eligible<typename model::activation_scalar>(
                        operation_head_size, operation_kv_mul)) {
        if (amx_q_packed != nullptr &&
            is_dense_amx_page(page, begin, end, query_visible, *range_hint, q_position,
                k_position, sliding_window_size)) {
          apply_dense_amx_page<geometry>(
              was_valid, page, slot, operation_scale, kv_head, sp, amx_q_packed);
          // The hint is returned unchanged: is_dense_amx_page proved that the
          // page's last token is below range_hint->tok_hi, so the dotter's
          // advance (kv_idx >= tok_hi below) could not have fired for this
          // page either.
          return {range_hint, int(page::page_size), attn_stats::visit_path::amx};
        }
      }
#endif
      tensor<operation_kv_mul, page::page_size> s_pages;
      int relevant_k_tokens = 0;
      {
        decltype(page.template k<geometry.kv>(slot, kv_head)) keys;
        // share the bf16 -> fp32 conversion across the page
        using scalar_t = typename btensor_t<operation_head_size>::element;
        for (size_t offset = 0; offset < operation_kv_mul; ++offset)
          s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f);
        // `dotter` binds to a view at construction and has no default
        // constructor, so we can't declare a std::array<dotter,...> and fill
        // it in a loop. Pack-expand `kv_mul` constructor calls inside the
        // array initializer instead. Worth the syntax because `kv_mul` is a
        // compile-time constant and this is the per-page hot path, so we
        // avoid the heap allocation a std::vector<dotter> would incur.
        std::array<dotter<scalar_t, operation_head_size>, operation_kv_mul> dot_q =
            [&]<size_t... I>(std::index_sequence<I...>) {
              return std::array{
                  dotter<scalar_t, operation_head_size>(slice<operation_head_size>()(
                      q, (kv_head * operation_kv_mul + I) * operation_head_size))...};
            }(std::make_index_sequence<operation_kv_mul>{});
        for (size_t i = begin; i < end; ++i) {
          // Advance range_hint when we move past the current range.
          token_id kv_idx = page.at_offset(i);
          if (kv_idx >= range_hint->tok_hi) {
            range_hint = &enclosing_state.query_mask->find_range(kv_idx, *range_hint);
            query_visible = run_visible_in_software ? range_hint->visible(job_ix)
                                                    : range_hint->sw_required(job_ix);
          }
          if (!query_visible) {
            // Skip to next range or end of page (-1 for ++i).
            i = page.offset_for(range_hint->tok_hi) - 1;
            continue;
          }
          if ((int)q_position - (int)(k_position + i) >= sliding_window_size) {
            // The k token is outside the sliding window
            continue;
          }
          relevant_k_tokens++;
          if (!keys.valid()) keys = page.template k<geometry.kv>(slot, kv_head);
          const auto k = keys[i];
          for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
            s_pages[offset][i] = dot_q[offset](k);
          }
        }
      }
      if (relevant_k_tokens == 0)
        // Skip the V portion if there's nothing for it to do.  It
        // would NaN anyway.
        return {range_hint, 0, attn_stats::visit_path::empty};
      for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
        size_t head = kv_head * operation_kv_mul + offset;
        tensor<page::page_size>& s_page = s_pages[offset];
        scratchpad_ref<geometry> head_sp = sp[head];
        // The lanes in these tensors correspond to tokens in this page
        if constexpr (softcapping) {
          // TRACE_EVENT("model", "attention softcapping");
          auto softcap = enclosing_state.plugin_state.model.attn_logit_softcapping;
          s_page = tanh(s_page * (operation_scale / softcap)) * softcap;
        } else {
          s_page = s_page * operation_scale;
        }
        float m_page = max(s_page);
        if (was_valid) m_page = std::max(head_sp.m_star, m_page);
        auto& exp_s_minus_m = s_page;  // Reuse s_page.
        exp_s_minus_m = exp(s_page - m_page);
        tensor<operation_head_size> scratch;
        if (was_valid) {
          float exp_m_star_minus_m = std::exp(head_sp.m_star - m_page);
          auto exp_m_star_minus_m_ = constant<page::page_size>(exp_m_star_minus_m);
          head_sp.v_star.set(fma(head_sp.v_star, exp_m_star_minus_m_,
              page.template scaled_v<geometry.kv>(
                  slot, kv_head, exp_s_minus_m, scratch)));
          head_sp.s_star = head_sp.s_star * exp_m_star_minus_m + sum(exp_s_minus_m);
        } else {
          head_sp.v_star.set(page.template scaled_v<geometry.kv>(
              slot, kv_head, exp_s_minus_m, scratch));
          head_sp.s_star = sum(exp_s_minus_m);
        }
        head_sp.m_star = m_page;
      }
      return {range_hint, relevant_k_tokens, attn_stats::visit_path::avx};
    }

    template <attention_geometry geometry>
    TRON(inline)
    static bool v_star_has_nan(const v_star_view_t<geometry>& v_star) noexcept {
      // A NaN is the only IEEE-754 value unequal to itself. 'values' below is an
      // 8- or 16-lane FP32 SIMD vector. fp32s::operator!= returns true when any
      // SIMD lane fails that ordered self-equality comparison.
      for (size_t i = 0; i < geometry.kv.head_size / chunk_size; ++i) {
        auto values = v_star.chunk(i);
        if (values != values) return true;
      }
      if constexpr (geometry.kv.head_size % chunk_size != 0) {
        auto values = v_star.last();
        if (values != values) return true;
      }
      return false;
    }

    template <attention_geometry geometry>
    void join_page_ranges(token_scratchpad_ref<geometry>& target,
        token_scratchpad_ref<geometry>& source,
        size_t kv_head) {
      constexpr size_t operation_kv_mul = geometry.kv_mul();
      MODEL_DEBUG("{} kv_head {} to worker {}, from worker {}, batch_job_ix {}",
          __PRETTY_FUNCTION__, kv_head, target.worker_ix, source.worker_ix,
          source.batch_job_ix);
      TRON_ASSERT(source.worker_ix != 0, "Unexpected join from a base scratchpad.");
      // `source` didn't allocate a scratchpad for this token and therefore has nothing
      // to contribute.  Skip.
      if (!source.is_valid_for(kv_head)) return;
      bool was_valid = target.mark_valid_for(kv_head);
      for (size_t head = kv_head * operation_kv_mul;
          head < (kv_head + 1) * operation_kv_mul; ++head) {
        scratchpad_ref<geometry> sp = target[head];
        scratchpad_ref<geometry> other_sp = source[head];
        TRON_ASSERT(!std::isnan(other_sp.m_star),
            "Encountered NaN m_star, probably a bug in software or firmware. "
            "This is often due to reading from uninitialized memory somewhere in the "
            "system. "
            "KV_head {}, to worker {}, from worker {}, batch_job_ix {}",
            kv_head, target.worker_ix, source.worker_ix, source.batch_job_ix);
        TRON_ASSERT(other_sp.m_star != -std::numeric_limits<float>::infinity(),
            "Encountered -inf m_star in a valid scratchpad. "
            "KV_head {}, to worker {}, from worker {}, batch_job_ix {}",
            kv_head, target.worker_ix, source.worker_ix, source.batch_job_ix);
        float new_m =
            was_valid ? std::max(sp.m_star, other_sp.m_star) : other_sp.m_star;
        if (was_valid) {
          float my_exp_m_star_minus_m = std::exp(sp.m_star - new_m);
          float other_exp_m_star_minus_m = std::exp(other_sp.m_star - new_m);
          sp.v_star.set(sp.v_star * my_exp_m_star_minus_m +
                        other_sp.v_star * other_exp_m_star_minus_m);
          sp.s_star = sp.s_star * my_exp_m_star_minus_m +
                      other_sp.s_star * other_exp_m_star_minus_m;
        } else {
          float other_exp_m_star_minus_m = 1;  // Because new_m == other_sp.m_star
          sp.v_star.set(other_sp.v_star * other_exp_m_star_minus_m);
          sp.s_star = other_sp.s_star * other_exp_m_star_minus_m;
        }
        TRON_ASSERT(!std::isnan(sp.s_star),
            "Encountered NaN s_star while joining attention ranges. "
            "KV_head {}, to worker {}, from worker {}, batch_job_ix {}",
            kv_head, target.worker_ix, source.worker_ix, source.batch_job_ix);
        TRON_ASSERT(!v_star_has_nan<geometry>(sp.v_star),
            "Encountered NaN v_star while joining attention ranges. "
            "KV_head {}, to worker {}, from worker {}, batch_job_ix {}",
            kv_head, target.worker_ix, source.worker_ix, source.batch_job_ix);
        sp.m_star = new_m;
      }
    }

    // Note [Attention Sinks a la GPT-OSS]
    // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    //
    // To wit, the sink value for each head is just included in the softmax,
    // with a hard-zero V vector.
    //
    // The `apply_attn_sinks` method is just a specialization of
    // `join_page_ranges`:
    // - scratchpad is 0 because we always apply_attn_sinks to the final result
    // - we don't check was_valid for the same reason
    // - other_m_star is the attention sink value for the query head
    // - other_v_star is all zeros
    // - other_s_star is 1, because that's exp(<sink value> - other_m_star)
    //
    // Reference: Here is how attention sinks are implemented in
    // https://github.com/openai/gpt-oss/blob/48db88d8e29f48493fe75f084a8c9bd900a2b92f/gpt_oss/torch/model.py#L153
    //
    // In scope:
    // - n_tokens is the batch size
    // - n_heads is the number of KV heads
    // - q_mult is the GQA factor, i.e., the num_attention_heads / n_heads
    // - d_head is the head size
    // - n_k_tokens is the context length
    //
    // # S is the sinks, and comes in with shape [num_attention_heads]
    // # (which is n_heads * q_mult).
    // S = S.reshape(n_heads, q_mult, 1, 1).expand(-1, -1, n_tokens, -1)
    // # QK is the Q*K^T result, of shape [n_heads, q_mult, n_tokens, n_k_tokens]
    // QK = torch.cat([QK, S], dim=-1)
    // W = torch.softmax(QK, dim=-1)
    // W = W[..., :-1]
    // # W, now of shape [n_heads, q_mult, n_tokens, n_k_tokens], is used as the
    // # input to the E*V matmul.
    template <attention_geometry geometry>
    void apply_attn_sinks(
        size_t batch_job_ix, std::span<const float> operation_sinks, size_t kv_head) {
      constexpr size_t operation_kv_mul = geometry.kv_mul();
      token_scratchpad_ref<geometry> ts =
          token_scratchpad_ref_at<geometry>(0, batch_job_ix);
      for (size_t head = kv_head * operation_kv_mul;
          head < (kv_head + 1) * operation_kv_mul; ++head) {
        // Not checking the validity of the scratchpad because it's always
        // valid.  Note [Garbage attention scores corner case].
        scratchpad_ref<geometry> sp = ts[head];
        attention_sink_update const update =
            attention_sink_update_for(operation_sinks[head], sp.m_star, sp.s_star);
        sp.v_star.set(sp.v_star * update.value_scale);
        sp.s_star = update.s_star;
        sp.m_star = update.m_star;
      }
    }
  };
};

}  // namespace tron
