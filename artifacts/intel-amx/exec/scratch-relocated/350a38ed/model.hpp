#pragma once

// The common parts of all tron models, that do not vary across plugins.

#include <algorithm>  // For std::find, std::remove_if
#include <array>
#include <atomic>  // For gof_coop_outstanding_
#include <cerrno>
#include <charconv>
#include <chrono>    // For the join watchdog (Note [Shared block save])
#include <concepts>  // For std::convertible_to
#include <cstdio>    // For std::remove
#include <cstdlib>
#include <fstream>
#include <functional>   // For std::function (kv_save_observer_t)
#include <immintrin.h>  // For _mm_pause (Note [Shared block save])
#include <iomanip>
#include <limits>
#include <mutex>
#include <optional>
#include <regex>
#include <span>
#include <string_view>
#include <type_traits>
#include <unordered_set>
#include <utility>  // For std::pair (cooperative gof_rodeo queue)
#include <vector>   // For std::vector

#include <concurrentqueue.h>  // moodycamel, for the cooperative gof_rodeo queue

#include "common/indexed.hpp"
#include "common/malloc_category.hpp"
#include "common/numerics/std.hpp"
#include "common/top_k_accum.hpp"
#include "pos/device.hpp"
#include "pos/dma_tracker.hpp"
#include "spdlog/fmt/bundled/core.h"
#include "spdlog/spdlog.h"
#include "system/fuse_stats.hpp"
#include "system/fuse_tronstats.hpp"
#include "tron/expert_routing_override_kind.hpp"
#include "tron/files/safetensors.hpp"
#include "tron/generation/stats.hpp"
#include "tron/gof.hpp"
#include "tron/hardware/attention_slots.hpp"
#include "tron/hardware/placer.hpp"
#include "tron/hardware/ptensor.hpp"
#include "tron/models/common.hpp"
#include "tron/models/expert_load_profile.hpp"
#include "tron/models/expert_routing.hpp"
#include "tron/models/expert_stats.hpp"
#include "tron/models/forced_routing.hpp"
#include "tron/models/hw_attn_config.hpp"
#include "tron/models/kv_cache.hpp"
#include "tron/models/logits.hpp"
#include "tron/models/moe_router_id.hpp"
#include "tron/models/ranged_mask.hpp"
#include "tron/models/self_attention.hpp"
#include "tron/token.hpp"

namespace tron {

TRON(inline)
std::mutex& log_intermediates_mutex() {
  static std::mutex log_mutex;
  return log_mutex;
};

// Min,Max number of main helper threads to ever use in the llama_model.
// If 0, avoids main helpers, to e.g. avoid deadlock bugs.
TRON(inline)
size_t init_min_main_helpers() {
  if (const char* env = getenv("TRON_MIN_MAIN_HELPERS")) return atol(env);
  if (app_pool().num_workers() >= 16)  // typically true in TP4 but not TP2
    return 1;                          // Force at least one main helper by default.
  return 0;
}
TRON(inline)
size_t init_max_main_helpers() {
  if (const char* env = getenv("TRON_MAX_MAIN_HELPERS")) return atol(env);
  return app_pool().num_workers() / 2;  // Reserve half the workers for attention
}
TRON(inline)
size_t init_logits_chunk_size() {
  static const size_t result = [] {
    const char* env = getenv("TRON_MAX_LOGITS_CHUNK_SIZE");
    size_t upper_bound = env ? atol(env) : 99999999;
    size_t target = app_pool().num_workers();
    return std::min(upper_bound, target);
  }();
  return result;
}

// Note [Early and late hardware attention launch]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Generated attention schedules contain both legal hardware-launch positions,
// but the C++ executor selects exactly one for each batch. Batches at or above
// TRON_HWATTN_EARLY_LAUNCH_MIN_B (4 by default) use the early phase: hardware
// preparation runs while the main thread advances the attention-operation barrier,
// and launch precedes the current-token K/V saves so hardware work can overlap the
// saves and their DMA. Smaller batches skip those early actions, save K/V, and then
// prepare and launch in the late phase. This is a batch-size heuristic, not a
// prompt/decode classification, and keeping it in the executor leaves the Tron IR
// independent of runtime launch policy.
//
// Phase and eligibility are separate decisions. The phase selects when an already
// eligible operation is prepared and launched; it cannot make a software-only
// operation use hardware. See Note [Hardware attention eligibility].
TRON(inline)
size_t init_hwattn_early_launch_min_b() {
  static const size_t result = []() -> size_t {
    if (const char* env = getenv("TRON_HWATTN_EARLY_LAUNCH_MIN_B")) {
      std::string_view value(env);
      bool digits_only = !value.empty();
      for (char digit : value)
        digits_only = digits_only && digit >= '0' && digit <= '9';
      errno = 0;
      char* end = nullptr;
      unsigned long long parsed = std::strtoull(env, &end, 10);
      TRON_ASSERT(digits_only && errno != ERANGE &&
                      end == value.data() + value.size() && parsed > 0 &&
                      parsed <= std::numeric_limits<size_t>::max(),
          "invalid TRON_HWATTN_EARLY_LAUNCH_MIN_B '{}'; expected a positive integer",
          value);
      return static_cast<size_t>(parsed);
    }
    // Default to early launch for four-user batches: overlapping HW attention
    // with current-token K/V saves and DMA recovered the GPT-OSS decode gap to SW.
    return size_t{4};
  }();
  return result;
}

inline constexpr size_t max_attn_section_split = 16;

// TRON_ATTN_SECTION_SPLIT caps how many pieces one section may be split
// into; 0 or 1 disables splitting.
TRON(inline)
size_t init_attn_section_split_cap() {
  static const size_t cap = []() -> size_t {
    const char* v = getenv("TRON_ATTN_SECTION_SPLIT");
    if (v == nullptr) return size_t{8};
    std::string_view value(v);
    size_t parsed = 0;
    const auto [end, error] =
        std::from_chars(value.data(), value.data() + value.size(), parsed);
    const bool valid = error == std::errc{} && end == value.data() + value.size();
    TRON_ASSERT(valid,
        "invalid TRON_ATTN_SECTION_SPLIT '{}'; expected a nonnegative integer", value);
    return std::min(parsed, max_attn_section_split);
  }();
  return cap;
}

enum class hw_attention_launch_phase : uint8_t { late, early };

TRON(nodiscard, inline, pure)
constexpr hw_attention_launch_phase select_hw_attention_launch_phase(
    size_t batch_size, size_t early_launch_min_b) noexcept {
  return batch_size >= early_launch_min_b ? hw_attention_launch_phase::early
                                          : hw_attention_launch_phase::late;
}

// Estimator for the time to process something.  Units of time and
// work are arbitrary, but must be consistent, e.g. cycles and dot
// products, or thread-time (threads x time).
struct time_estimator {
  float curr_work;
  float prev_work;
  float prev_time;

  time_estimator() noexcept
  : curr_work(0)
  , prev_work(0)
  , prev_time(0) {}

  bool is_valid() const noexcept {
    return prev_work > 0 && prev_time > 0;
  }
  void record_time(float time) noexcept {
    prev_time = time;
  }
  void record_work(float work) noexcept {
    prev_work = curr_work;
    curr_work = work;
  }

  float predict_time() const noexcept {
    return prev_time * curr_work / prev_work;
  }
};

// This chunking heuristic aims to construct uniformly sized chunks from differently
// sized groups:
// - Large groups, corresponding to one or more prompt chunks.
//   Each large group should be split into at most 1 chunk per
//   max_minibatch_size/2 tokens.
// - Singleton groups for a single non-speculated token.
// - A handful of speculated tokens, say <= 8 == minibatch_grain_size.
//   These should never be split.
// The objective is to minimize splits, and thus preserve kv affinity.
//
// The group_ids are just a cheap proxy for kv affinity, and might be
// constructed from connected components on the token tree. Ideally we'd measure
// the number of kv entries or pages shared between every pair of tokens, but
// that's prohibitively expensive.
//
// TODO these decisions should depend on the relative amounts of work devoted to
// matmuls vs attention, but those quantities depend on the model, user queries,
// and system shape, and are not available here.
TRON(nodiscard, inline)
std::vector<std::vector<int>> chunk_evenly(size_t n_token_jobs,
    token_batching_affinity_id const* group_ids,
    auto& state) noexcept {
  if (!n_token_jobs) return {};
  constexpr size_t max_minibatch_size =
      std::decay_t<decltype(state)>::max_minibatch_size;
  static_assert(max_minibatch_size >= minibatch_grain_size);

  // Collate tokens into groups.
  size_t n_groups =
      size_t{1} + std::max_element(group_ids, group_ids + n_token_jobs)->i;
  std::vector<std::vector<int>> groups(n_groups);
  for (size_t j = 0; j < n_token_jobs; ++j)
    groups[group_ids[j].i].push_back(j);

  // Split groups in into grains that will never be further split.
  std::vector<std::vector<int>> grains;
  for (auto& group : groups)
    for (size_t i = 0; i < group.size(); i += minibatch_grain_size) {
      size_t size = std::min(minibatch_grain_size, group.size() - i);
      grains.emplace_back(group.begin() + i, group.begin() + i + size);
    }

  // Fix grains not to split even/odd token pairs.  For any given KV page,
  // we have to keep the even and odd token offsets in the same minibatch,
  // because packed V stores them in the same SIMD values (see
  // Note [VNNI Packed V layout] in h/tron/tensor/v_vnni.hpp): `page.set_v` of the
  // odd token merges into the pair its even partner wrote, and so would race
  // with itself if different threads were to try to save the two halves of
  // such a pair separately.
  adjust_grains_for_partners(grains, state, n_token_jobs);

  // Greedily consolidate grains into chunks of roughly equal size.
  size_t target_n_chunks = (n_token_jobs + max_minibatch_size - 1) / max_minibatch_size;
  // Apply max_minibatches constraint if specified
  if (state.cfg.max_minibatches > 0 &&
      target_n_chunks > static_cast<size_t>(state.cfg.max_minibatches))
    target_n_chunks = static_cast<size_t>(state.cfg.max_minibatches);
  if (target_n_chunks == 1 && (n_groups > 1 || n_token_jobs > minibatch_grain_size) &&
      (state.cfg.max_minibatches < 0 || state.cfg.max_minibatches >= 2))
    // Split a large lone chunk in half, to enable FPGA-vs-CPU latency hiding.
    // Only do this if max_minibatches allows it (is negative/unlimited or >= 2)
    target_n_chunks = 2;
  const int target_size = (n_token_jobs + target_n_chunks - 1) / target_n_chunks;
  const int max_size = max_minibatch_size;
  std::vector<std::vector<int>> chunks;
  chunks.emplace_back(std::move(grains[0]));
  for (size_t g = 1; g < grains.size(); ++g) {
    std::vector<int> grain = std::move(grains[g]);
    int old_sz = chunks.back().size();
    int new_sz = old_sz + grain.size();
    bool grain_fits = new_sz <= max_size;
    bool good_here = std::abs(new_sz - target_size) <= std::abs(old_sz - target_size);
    bool hit_chunk_limit = chunks.size() == (uint64_t)state.cfg.max_minibatches;
    if ((grain_fits && good_here) || hit_chunk_limit)
      chunks.back().insert(chunks.back().end(), grain.begin(), grain.end());
    else
      chunks.emplace_back(std::move(grain));
  }

  // Try again to split a large lone chunk, e.g. a lone prompt chunk.
  if (chunks.size() == 1 && n_token_jobs > minibatch_grain_size &&
      (state.cfg.max_minibatches < 0 || state.cfg.max_minibatches >= 2)) {
    // Only do this if max_minibatches allows it (is negative/unlimited or >= 2)
    size_t half = chunks.back().size() / 2;
    chunks.emplace_back(chunks[0].begin() + half, chunks[0].end());
    chunks[0].resize(half);
    // If the final chunk split separated an even/odd token pair, we have to fix it.
    adjust_grains_for_partners(chunks, state, n_token_jobs);
  }

#ifndef NDEBUG
  size_t total_size = 0;
  for (auto& chunk : chunks)
    total_size += chunk.size();
  TRON_ASSERT_EQ(total_size, n_token_jobs);
#endif
  return chunks;
}

void adjust_grains_for_partners(
    std::vector<std::vector<int>>& grains, auto& state, size_t n_token_jobs) {

  if (n_token_jobs == 0 || grains.empty()) return;

  // 1. Build initial job_idx_to_grain_idx_map
  std::vector<int> job_idx_to_grain_idx_map(n_token_jobs, -1);
  for (size_t c_idx = 0; c_idx < grains.size(); ++c_idx) {
    for (int job_idx_val : grains[c_idx]) {
      if (job_idx_val >= 0 && static_cast<size_t>(job_idx_val) < n_token_jobs) {
        job_idx_to_grain_idx_map[job_idx_val] = static_cast<int>(c_idx);
      }
    }
  }

  // 2. Iterate through job indices to find even partners and adjust grains
  for (int k = 0; k < static_cast<int>(n_token_jobs); ++k) {
    token_job_id tj_ix_k(k);
    token_id t_id_k = state.token_jobs[tj_ix_k];
    auto& page_k = state.page_of(t_id_k);
    int offset_k = page_k.offset_in_page(t_id_k);
    if (offset_k % 2 != 0) continue;  // Don't move tokens for odd offsets
    int partner_offset_k = offset_k + 1;
    // Don't move tokens whose partners don't exist
    if ((size_t)partner_offset_k == page_k.count()) continue;
    token_id partner_token_id = page_k.at_offset(partner_offset_k);
    token_job_id candidate_partner_job_ix =
        state.token_job_id_of_token[partner_token_id];
    // Don't try to move partner tokens that don't exist or aren't in the jobs list
    if (candidate_partner_job_ix.i >= n_token_jobs) continue;
    if (state.token_jobs[candidate_partner_job_ix] != partner_token_id) continue;

    int grain_idx_k = job_idx_to_grain_idx_map[k];
    int grain_idx_partner = job_idx_to_grain_idx_map[candidate_partner_job_ix.i];

    if (grain_idx_k != -1 && grain_idx_partner != -1 &&
        grain_idx_k != grain_idx_partner) {
      std::vector<int>& source_grain_vec = grains[grain_idx_partner];
      auto& dest_grain_vec = grains[grain_idx_k];

      auto val_it = std::find(
          source_grain_vec.begin(), source_grain_vec.end(), candidate_partner_job_ix.i);
      if (val_it != source_grain_vec.end()) {
        source_grain_vec.erase(val_it);
        dest_grain_vec.push_back(candidate_partner_job_ix.i);
        job_idx_to_grain_idx_map[candidate_partner_job_ix.i] = grain_idx_k;
      }
    }
  }

  grains.erase(std::remove_if(grains.begin(), grains.end(),
                   [](const std::vector<int>& grain_val) { return grain_val.empty(); }),
      grains.end());
}

template <typename batch>
TRON(nodiscard, inline)
std::vector<std::unique_ptr<batch>> batch_evenly(auto& state,
    size_t n_token_jobs,
    token_batching_affinity_id const* group_ids,
    latch_arena& latches) noexcept {
  constexpr size_t max_minibatch_size =
      std::decay_t<decltype(state)>::max_minibatch_size;
  std::vector<std::vector<int>> const chunks =
      chunk_evenly(n_token_jobs, group_ids, state);
  for (const auto& chunk : chunks) {
    TRON_ASSERT(chunk.size() <= max_minibatch_size,
        "Chunk size {} exceeds maximum minibatch size {}", chunk.size(),
        max_minibatch_size);
  }
  std::vector<std::unique_ptr<batch>> partitioned_vector;
  partitioned_vector.reserve(chunks.size());
  for (size_t ix = 0; ix < chunks.size(); ++ix) {
    std::vector<token_job_id> items(chunks[ix].begin(), chunks[ix].end());
    {
      TRACE_EVENT("model", "Create minibatch");
      partitioned_vector.emplace_back(new batch(state, std::move(items), latches, ix));
    }
  }
  return partitioned_vector;
}

/**
 * Note [Tron plugin API]
 * ~~~~~~~~~~~~~~~~~~~~~~
 * A Tron plugin is a type template suitable to be the first argument to the TRON_PLUGIN
 * macro (whose definitions see in llama.hpp, load.hpp, and alderaan_full.hpp).
 *
 * As such, it must template on the executor type (a member of the llm_executor
 * concept), and when instantiated, must include a nested struct named `plugin_model`,
 * which will be the argument at which the below `model` template is instantiated.
 * (See TRON_LLAMA_CONFIG in llama.hpp for an example.)
 *
 * Broadly, the plugin is responsible for:
 * - Reading the model configuration
 * - Loading the model weights from disk (using the visit_named_tensors protocol)
 * - Running the forward pass (embedding, layers, logits)
 *   (TODO: using the provided suite of attention kernels)
 * - Sundry minor responsibilities that will get smoothed out as we get a second one
 *
 * More specifically, the protocol is as follows:
 * - `plugin_model` is expected to expose several fields for type-level configuration:
 *   - `size_t dim` giving the embedding dimension (for the pre-logits buffer)
 *   - `size_t n_layers` giving the number of layers (for allocating KV books)
 *   - `size_t n_moe_routers` giving the number of MoE routing sites
 *   - `indexed_vector<moe_router_id, size_t> expert_routing_top_k_by_router`
 *     giving the number of experts selected at each MoE routing site (empty for
 *     non-MoE plugins)
 *   - `size_t n_heads` giving the number of attention heads
 *   - `size_t n_kv_head` giving the number of KV heads
 *   - `size_t head_size` giving the size of attention heads is optional and will be
 *     inferred if absent (but required for non-square WQ and WO matrices)
 *   - `size_t vocab_size` giving the size of the vocabulary, for running logits
 *   - `bool wcls_is_compensated` for whether the language head uses
 *     compensated summation
 *   - `bool attn_softcapping` for whether the attention layer should use softcapping
 *   - Attention configuration belongs to operation descriptors. Plugins provide
 *     `attention_sink_specs` plus `attention_sink(attention_sink_id)`; the returned
 *     span must satisfy Note [Attention sink span lifetime].
 *   - `bool is_eagle` for whether the model is an Eagle model
 *   In the fullness of time it may be good to let the plugin pass these as arguments
 *   to appropriate framework facilities, but they're just magic fields for now.
 * - The constructor of the plugin's `model` struct parses the model configuration,
 *   setting up any needed state.
 *   - The available arguments are as passed by the `model<plugin_type>` constructor
 *     below.
 * - Loading weights from disk follows the visit_named_tensors protocol:
 *   - The `plugin_model` must have a `cache_weights(std::string model_id)` method,
 *     which may be empty.  It is called once before weights are loaded, and once after.
 *     This gives the plugin an opportunity to reuse weights across multiple model
 *     instances loaded from the same plugin (e.g., base and Eagle variants of the
 *     same model).
 *   - The `plugin_model` must have a method
 *       `visit_named_tensors(const auto& visit, int max_layers = -1,
 *          bool tie_word_embeddings = false) noexcept`
 *     - The `visit` argument is a callable that takes a blank tensor and a
 *       `hardware::tensor_placement_request`. The request's name gives the tensor's
 *       key in the checkpoint. Every call to `visit` asks the system to load that
 *       tensor using generic machinery.
 *     - The `max_layers` argument is the maximum number of layers to load (-1 for all).
 *     - The `tie_word_embeddings` argument is a hack.  Currently, the plugin
 *       has no way to detect whether to tie the word embeddings as Llama 3B does,
 *       so we detect it on the outside and pass it in.  This argument is unreliable
 *       for non-Llama models.  TODO: Just implement Llama 3B as a separate plugin
 *       and get rid of this argument.
 *     - `visit_named_tensors` is called several times with different `visit` callbacks,
 *       to plan tensor placement across multiple devices.
 *   - The `plugin_model` must have a `finalize_weights()` method, which may be empty.
 *     It is called once after all the weights have been loaded, giving the plugin
 *     a chance to do any needed post-processing of the weights.
 * - The `plugin_model` is expected to be read-only after weight loading.
 * - The `plugin_model` must have a `wcls` field, which holds the language head matrix.
 *   - This may be a pointer (to support weight sharing) or a direct field.
 * - The `plugin_model` must have a nested `state` struct, which preallocates all the
 *   buffers and intermediates needed for the forward pass.  The `state` object
 *   persists across multiple forward passes, and is not copied; but it should not
 *   transmit information between forward passes.
 * - The `plugin_model::state` constructor is passed the `plugin_model` instance, a
 *   `model<plugin_type>::state*` pointer, and the `model_config` struct.  From this,
 *   it should initialize the persistent state.
 * - The `plugin_model::state` struct must have a `resize(size_t max_tokens)` method,
 *   which must resize any per-token buffers to accomodate the new max_tokens.
 *   Buffers are not required to shrink if `max_tokens` is smaller than the current
 *   capacity.
 * - The `plugin_model` must have a nested `plugin_batch` struct, which is available to
 *   store any per-minibatch state the plugin needs, such as channels and matmul
 *   launchers.
 *   - Every forward pass constructs one or more `plugin_batch` instances, at the
 *     whim of the minibatch scheduler.
 * - The `plugin_batch` constructor is passed the `plugin_model::state` instance,
 *   the outer minibatch instance, the latch arena, and a `size_t ix` giving the batch's
 *   index in the q_batches structure.  The latter is useful for unambiguously naming
 *   latches and channels.
 * - The `plugin_batch` struct must have methods
 *   `reset_channels(size_t n_attention_workers, size_t n_main_workers)` and
 *   `next_layer()`, which see in `common.hpp`.
 * - The `plugin_model::state` must also participate correctly in the forward pass
 *   protocol.  At the moment, the consists of
 *   - Method `make_latches(latch_arena& latches)`, which may be empty.  This gives
 *     the plugin a chance to create any state-level latches it needs (per-batch
 *     latches get a chance in the `plugin_batch` constructor).
 *   - Method `run(q_batches)`, called once per forward pass on the scheduler
 *     thread.  The plugin may run work on the `app_pool` thread pool, but must
 *     end and join those workers before `run` exits.
 *     Note [Plugin-owned worker launch].
 *   - Method `available_main_parallelism(size_t n_tokens) const`, returning
 *     the maximum useful main-helper-thread striping for a minibatch of
 *     `n_tokens` tokens.  Dense models return `n_tokens`; MoE models
 *     return `n_tokens * n_routed_experts_chosen`, reflecting that the
 *     expert loop stripes over (token, expert) slots rather than tokens.
 *     The model uses this value to cap `n_main_helpers`.
 *   - These may read the `token_job_tokens` and `token_job_positions` fields, which
 *     map token_job_id to the actual token and its position, respectively.
 *   - A plugin may provide `token_t remap_input_token(token_t) const noexcept`.
 *     The framework applies it while gathering `token_job_tokens`; sequence-tree
 *     identity and returned logits retain the original token ID.
 *   - These may call `log_intermediate` to log intermediate values.
 *   - These may call `save_k` and `save_v` with the current
 *     `attention_binding` to save the KV cache when the plugin has computed it.
 *   - These must call `prepare_for_logits()` on the enclosing state exactly once,
 *     after all the non-logit matmuls have been prepared.
 *   - After `run` exits, the outer state's `final_embedding` buffer must be filled
 *     with the final embeddings for each token.
 *   - Plugins schedule explicit attention operations with plugin-owned buffers
 *     and channels, including any RoPE or output permutation around each job.
 *   - Methods `patch_logits(auto& logits_in, auto& logits_out)` and
 *     `patch_logits_in_place(auto& logits)`.  These are used to give the plugin
 *     a chance to adjust the logits before they are returned to the user.  Currently,
 *     this facility is only used to implement the final logit softcapping of
 *     Gemma 2.  Both methods must exist, and the first must invoke
 *     `logits_out.set(logits_in)` if the plugin does not want to modify the logits.
 *   However, we intend to simplify this through further refactoring and mindful
 *   allocation of responsibilities between the plugin and the `model<plugin>`.
 * - Attention jobs consume Q and produce O through fallback-latch channels, with
 *   one reader and writer per attention worker. Plugins reset and prepare these
 *   channels and save K/V through the operation's explicit cache binding. Ready
 *   attention starts when Q is published; pending attention also waits for K/V.
 *   Workers call `finish_attention_job` after any output transformation, before
 *   advancing to the next operation. The compile-time operation overload does
 *   this immediately after the job, for schedules without such a transformation.
 */

template <typename T>
concept has_head_size = requires { T::head_size; };

template <typename T>
concept attention_plugin_config = requires(T const& plugin, attention_sink_id sink) {
  T::attention_sink_specs;
  { plugin.attention_sink(sink) } noexcept -> std::same_as<std::span<const float>>;
};

// See Note [Tron plugin API].
// This concept captures the requirements that `model<>` places on its plugin type
// parameter.  Template methods like `visit_named_tensors`, `patch_logits`, and
// `patch_logits_in_place` cannot be checked here.  Most requirements on the nested
// `state` and `plugin_batch` types (whose signatures depend on `model<>` itself) are
// likewise deferred; see the static_asserts inside `model<>`.
template <typename T>
concept plugin = requires {
  // Static model configuration.
  typename std::integral_constant<size_t, T::dim>;
  typename std::integral_constant<size_t, T::n_layers>;
  typename std::integral_constant<size_t, T::n_moe_routers>;
  T::expert_routing_top_k_by_router;
  typename std::integral_constant<size_t, T::n_heads>;
  typename std::integral_constant<size_t, T::n_kv_heads>;
  typename std::integral_constant<size_t, T::vocab_size>;
  typename std::integral_constant<bool, T::permuted>;
  typename std::integral_constant<bool, T::wcls_is_compensated>;
  typename std::integral_constant<bool, T::attn_softcapping>;
  typename std::integral_constant<int, T::max_minibatches>;
  typename std::integral_constant<size_t, T::max_minibatch_size>;
  // head_size is optional; see has_head_size.

  // Tensor type templates.
  typename T::template btensor_t<T::dim>;
  typename T::template dtensor_t<T::vocab_size, T::dim>;

  // Nested types.
  typename T::cache_t;
  typename T::state;
  typename T::plugin_batch;
  T::attention_kernels;
  T::attention_operations;
  requires sequence_cache_topology<typename T::cache_t>;
  requires sequence_cache_behavior<typename T::cache_t>;
  requires attention_plugin_config<T>;
} && requires(typename T::state const& s, size_t n) {
  { s.available_main_parallelism(n) } -> std::convertible_to<size_t>;
  { T::active_attention_operation_count(n) } -> std::same_as<size_t>;
} && requires(T& t, T const& ct, json cfg, std::string id) {
  // Construction from config JSON and max_layers.
  T(cfg, int{});

  // Weight lifecycle.
  t.cache_weights(id);
  t.finalize_weights();

  // Runtime flag for EAGLE models.
  ct.is_eagle;
};

// Note [Model-boundary input token remapping]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Some model wrappers replace reserved input IDs before entering their text
// decoder. Generated plugins carry that mapping explicitly. Apply it only to
// the gathered token-job copy: the scheduler tree, callbacks, and logits keep
// the original ID. Each plugin mapping compares against the original token, so
// replacements are simultaneous rather than cascading.
template <typename Plugin>
TRON(inline)
token_t apply_input_token_remapping(Plugin const& plugin, token_t token) noexcept {
  if constexpr (requires { plugin.remap_input_token(token); }) {
    static_assert(noexcept(plugin.remap_input_token(token)),
        "remap_input_token must be noexcept");
    static_assert(std::same_as<decltype(plugin.remap_input_token(token)), token_t>,
        "remap_input_token must return token_t");
    return plugin.remap_input_token(token);
  } else {
    return token;
  }
}

struct attention_plan_profile {
  attention_geometry geometry;
  int sliding_window_size;
  bool uses_hw;

  constexpr bool operator==(attention_plan_profile const&) const noexcept = default;
};

// Note [Attention sink span lifetime]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Each model state caches the non-owning span returned by `attention_sink()`.
// The span must refer to immutable model-owned storage that outlives every state
// referring to that model. Generated plugins return spans over their tensor fields,
// which satisfy this contract.
struct attention_runtime_config {
  int sliding_window_size;
  std::span<const float> sinks;
};

// Bind operation configuration once while model state is constructed.
template <typename Plugin>
attention_runtime_config bind_attention_runtime_config(
    Plugin const& plugin, attention_operation_descriptor const& operation) noexcept {
  attention_runtime_config result{
      operation.config.sliding_window_size.value_or(illegal_sliding_window), {}};
  if (operation.config.sink) {
    attention_sink_id const sink = *operation.config.sink;
    TRON_ASSERT_LT(sink.i, Plugin::attention_sink_specs.size());
    attention_sink_spec const& spec = Plugin::attention_sink_specs[sink.i];
    TRON_ASSERT_EQ(spec.id.i, sink.i);
    result.sinks = plugin.attention_sink(sink);
    TRON_ASSERT_EQ(result.sinks.size(), spec.n_query_heads);
  }
  return result;
}

// Whether `t`, visited with `request`, is an expert matmul weight of more than one
// tile. See Note [Expert placement without a load profile].
template <typename tensor_type>
bool is_tiled_expert_weight(
    tensor_type const&, hardware::tensor_placement_request const& request) noexcept {
  return hardware::tile_count<tensor_type>::value > 1 &&
         request.is_moe_matmul_weight_tensor();
}

// Not directly constrained as `plugin` because plugin types
// reference model<T> internally, creating a circular dependency.
template <typename plugin_type>
struct model : noncopyable<model<plugin_type>> {
  using plugin_t = plugin_type;
  static constexpr size_t dim = plugin_t::dim;
  static constexpr size_t n_layers = plugin_t::n_layers;
  static constexpr size_t n_moe_routers = plugin_t::n_moe_routers;
  static constexpr size_t n_heads = plugin_t::n_heads;
  static constexpr size_t n_kv_heads = plugin_t::n_kv_heads;
  static constexpr size_t n_attention_kernels = plugin_t::attention_kernels.size();
  static constexpr size_t n_attention_ops = plugin_t::attention_operations.size();
  static constexpr size_t vocab_size = plugin_t::vocab_size;
  static constexpr bool permuted = plugin_t::permuted;
  static constexpr int max_minibatches = plugin_t::max_minibatches;
  // Plugin-controlled upper bound on minibatch size; sizes attention and
  // batching buffers. See Note [Tron plugin API].
  static constexpr size_t max_minibatch_size = plugin_t::max_minibatch_size;

  static constexpr size_t head_size = [] {
    if constexpr (has_head_size<plugin_t>) {
      return plugin_t::head_size;
    } else {
      static_assert(dim % n_heads == 0, "dim must be divisible by n_heads");
      return dim / n_heads;
    }
  }();

  static consteval bool valid_plugin_attention_configuration() {
    return valid_attention_configuration(plugin_t::attention_kernels,
        plugin_t::attention_operations, plugin_t::cache_t::kv_slot_specs,
        plugin_t::attention_sink_specs);
  }

  static_assert(valid_plugin_attention_configuration());
  static constexpr size_t max_kernel_query_width =
      max_attention_query_width(plugin_t::attention_kernels);
  static constexpr size_t max_kernel_query_heads =
      max_attention_query_heads(plugin_t::attention_kernels);
  static constexpr size_t max_kernel_kv_heads =
      max_attention_kv_heads(plugin_t::attention_kernels);
  // Compile-time upper bound; each operation's bound span decides whether sinks run.
  static constexpr bool may_have_attention_sinks =
      !plugin_t::attention_sink_specs.empty();

  // Note [Hardware attention eligibility]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  // Hardware selection narrows in stages. An operation descriptor's `hardware`
  // field is a static candidate declaration;
  // valid_hardware_attention_operations() verifies its kernel and KV slot against
  // the model's hardware attention geometry.
  // model_shape_is_hwattn_eligible() then checks model and hardware limits, while
  // model_instance_is_hwattn_eligible() excludes EAGLE.
  // At configuration time, device availability and use_hw_attn_for_this_model()
  // apply EMEM capacity and runtime/model policy. Finally,
  // compute_operation_uses_hw() intersects that configured state with the
  // operation's binding and attention window, and its result is cached in
  // attention_operation_uses_hw.
  //
  // Generated calls read only that cache. Their explicit `uses_hw` arguments are
  // propagated snapshots, not independent decisions; disagreement is a bug. A
  // batch with an empty hardware plan can still execute an eligible operation in
  // software. See Note [Early and late hardware attention launch] for the
  // independent scheduling decision.
  static constexpr attention_geometry hardware_attention_geometry{
      n_heads, kv_geometry{n_kv_heads, head_size}};

  static consteval bool valid_hardware_attention_operations() {
    for (auto const& operation : plugin_t::attention_operations) {
      if (operation.hardware != attention_hardware_capability::kv_slot_candidate)
        continue;
      if (operation.binding.kv_slot.i >= hardware::hardware_attention_slot_capacity ||
          !is_hardware_attention_candidate(plugin_t::attention_kernels,
              plugin_t::cache_t::kv_slot_specs, operation, hardware_attention_geometry))
        return false;
    }
    return true;
  }

  static_assert(valid_hardware_attention_operations(),
      "Invalid hardware attention candidate: invalid kernel/KV slot, KV slot "
      "exceeds hardware mask capacity, missing K/V write, sliding window, "
      "or incompatible kernel/slot geometry");

  static constexpr std::optional<float> hardware_attention_scale() {
    if (!valid_uniform_hardware_attention_scale(plugin_t::attention_operations))
      return std::nullopt;
    return uniform_hardware_attention_scale(plugin_t::attention_operations);
  }

  static constexpr bool model_shape_is_hwattn_eligible() {
    bool has_candidate = false;
    for (auto const& operation : plugin_t::attention_operations)
      has_candidate |=
          operation.hardware == attention_hardware_capability::kv_slot_candidate;
    return has_candidate &&
           valid_uniform_hardware_attention_scale(plugin_t::attention_operations) &&
           (head_size == 128 || head_size == 64) &&
           n_kv_heads <= hardware::HW_MAX_KV_HEADS &&
           (n_kv_heads > 0 && (n_heads / n_kv_heads) <= hardware::HW_MAX_GQA);
  }

  static constexpr bool model_instance_is_hwattn_eligible(bool is_eagle) {
    return model_shape_is_hwattn_eligible() && !is_eagle;
  }

  static constexpr bool model_forces_hw_attn() {
    if constexpr (requires { plugin_t::force_hw_attn; }) {
      return plugin_t::force_hw_attn;
    } else {
      return false;
    }
  }

  static bool use_hw_attn_for_this_model() {
    // HW attention needs EMEM to hold at least one shard's K/V for this model's
    // query-head count. When it can't (max_shards_for_emem == 0, i.e. n_heads
    // too large for the bitfile), the hardware path cannot run and the model
    // must use SW attention throughout. Gate here so configure_hw_attention
    // never sets the hardware KV-slot mask for such a model: otherwise it marks
    // HW-offloaded ranges that construct_hw_plan then drops (empty plan),
    // leaving those tokens computed by neither path -- silently wrong output.
    // model_shape_is_hwattn_eligible() bounds n_heads only through the gqa
    // ratio, not against EMEM capacity, so this check is a distinct, necessary gate.
    if (hardware::max_shards_for_emem(n_heads, head_size, hardware::shard_tokens) == 0)
      return false;
    return fwd_hw_attn_enabled(model_forces_hw_attn());
  }

  template <size_t d, size_t... ds>
  using btensor_t = typename plugin_t::template btensor_t<d, ds...>;
  using activation_scalar = typename btensor_t<dim>::scalar;
  template <size_t width>
  using intermediate_t = indexed_vector<token_job_id, btensor_t<width>>;
  template <size_t d1, size_t d2>
  using dtensor_t = typename plugin_t::template dtensor_t<d1, d2>;
  template <size_t d1, size_t d2>
  using expert_dtensor_t = typename plugin_t::template expert_dtensor_t<d1, d2>;

  // Whether dense weights are split into tiles across devices (tp2, tp4).
  static constexpr bool model_is_tensor_parallel() {
    return hardware::is_tensor_parallel<dtensor_t<vocab_size, dim>>::value;
  }

  // Whether every expert matmul weight the plugin visits is one tile.
  // See Note [Expert placement without a load profile].
  bool expert_weights_are_single_tiles(int max_layers = -1) noexcept {
    bool single_tiles = true;
    plugin.visit_named_tensors(
        [&single_tiles](
            auto& t, hardware::tensor_placement_request const& request) noexcept {
          if (is_tiled_expert_weight(t, request)) single_tiles = false;
        },
        max_layers);
    return single_tiles;
  }

  // Persistent sequence state is plugin-owned. `book` remains as a temporary
  // compatibility name while the scheduler surface migrates to `cache_t`.
  using cache_t = typename plugin_t::cache_t;
  using book = cache_t;
  using page = cache_t::page_t;
  using batch = batch<model>;

  static constexpr bool wcls_is_compensated = plugin_t::wcls_is_compensated;
  using wcls_t = dtensor_t<vocab_size, wcls_is_compensated ? dim + dim : dim>;

  // TODO: When the plugin architecture is done, we should audit uses of this
  // field, and remove the ones that do not conform to the interface spec.
  plugin_t plugin;

  // Cumulative per-(MoE router, expert) token routing stats, exposed via
  // FUSE for live monitoring. Empty placeholder for non-MoE plugins so
  // they pay no storage cost. Updated from worker 0 in both the
  // hand-written MoE path (h/tron/models/feed_forward.hpp) and the
  // ingest-generated `state::run` blocks. See Note [MoE Expert
  // Routing Stats] in expert_stats.hpp.
  using expert_stats_t = std::conditional_t<plugin_t::moe,
      tron::expert_stats<n_moe_routers, plugin_t::n_routed_experts>,
      std::monostate>;
  // mutable: the model's weights are const after load, but the stats
  // are write-during-forward. State references this through a
  // `model const& model_ref`, so this is the cleanest way to allow
  // bumping the counter from `state::forward` without `const_cast`.
  mutable expert_stats_t expert_stats_;

  // Resolved MoE routing override for this model, built at load time from the CLI
  // intent (tensor_load_options::expert_routing) once the profile is known.
  // std::nullopt means no override (use the real gate). Consumed at each
  // hand-written or ingest-generated MoE router.
  std::optional<expert_routing_override<expert_load_profile_t>>
      expert_routing_override_ = std::nullopt;

  model(std::filesystem::path checkpoint,
      json config,
      std::string model_id = "",
      int max_layers = -1,
      size_t replicas = 0,
      tensor_load_options const& opts = {})
  : plugin(config, max_layers) {
    static_assert(tron::plugin<plugin_type>,
        "plugin_type must satisfy the plugin concept; "
        "see Note [Tron plugin API]");
    if (checkpoint.empty()) {
      spdlog::warn("Checkpoint path is empty. Skipping weight loading.");
      return;
    }

    plugin.cache_weights(model_id);  // retrieves
    load_weights(checkpoint, model_id, max_layers, replicas, opts);
    plugin.finalize_weights();
    {
      TRACE_EVENT("loading", "Cache weights");
      plugin.cache_weights(model_id);  // stores
    }
  }

private:
  void load_weights(std::filesystem::path checkpoint,
      std::string const& model_id,
      int max_layers = -1,
      size_t replicas = 0,
      tensor_load_options const& opts = {}) {
    if (max_layers == -1)
      spdlog::info("Loading all layers from {}", checkpoint);
    else
      spdlog::info("Loading {} layers from {}", max_layers, checkpoint);
    if (std::filesystem::is_directory(checkpoint)) {
      std::optional<expert_load_profile_t> expert_load;
      if constexpr (plugin_t::moe) {
        const bool needs_expert_load_profile =
            opts.load_aware_expert_placement ||
            opts.expert_routing_override == expert_routing_override_kind::load;
        if (needs_expert_load_profile) {
          const std::filesystem::path profile_path =
              opts.expert_load_profile.value_or(checkpoint / "expert_load.json");
          auto profile = expert_load_profile_t::from_file(
              profile_path, n_moe_routers, plugin_t::n_routed_experts);
          if (profile) {
            expert_load.emplace(std::move(*profile));
          } else if (profile.error().kind ==
                     expert_load_profile_t::error_kind::not_found) {
            spdlog::info("No expert-load profile at {}", profile_path);
          } else {
            spdlog::warn("Ignoring expert-load profile {}: {}", profile_path,
                profile.error().message);
          }
        }
        resolve_expert_routing_override(opts, expert_load);
        if (opts.expert_routing_override == expert_routing_override_kind::uniform) {
          spdlog::info("Using uniform expert routing for model {} ({} routed experts)",
              model_id, plugin_t::n_routed_experts);
        } else if (opts.expert_routing_override == expert_routing_override_kind::load) {
          if (expert_routing_override_)
            spdlog::info(
                "Using load-profile expert routing for model {} ({} routed experts)",
                model_id, plugin_t::n_routed_experts);
          else
            spdlog::info("Using gate expert routing for model {} ({} routed experts); "
                         "no valid load profile is available",
                model_id, plugin_t::n_routed_experts);
        }
      }

      const hardware::device_mask devices =
          hardware::current_device_mask & hardware::get_devices_v2();
      auto placement = select_placement(checkpoint, replicas, max_layers, devices);
      if constexpr (plugin_t::moe) {
        placement = maybe_wrap_experts_by_load(
            std::move(placement), devices, expert_load, opts, max_layers);
        placement =
            hardware::replicate_moe_router_tensors(std::move(placement), devices);
      }
      placement = hardware::place_attention_kv_tensors(std::move(placement), devices);
      hardware::placement_context context(std::move(placement));
      load_safetensors(checkpoint, model_id, max_layers, opts);
    } else {
      spdlog::error("Unable to load checkpoint.");
      std::abort();
    }
  }

  std::unique_ptr<hardware::PlacementStrategy> select_placement(
      std::filesystem::path checkpoint,
      size_t replicas,
      int max_layers,
      hardware::device_mask devices) noexcept {
    const size_t n_devices = devices.count();
    // Heuristically set placement strategy based on checkpoint name and dim.
    std::unique_ptr<hardware::PlacementStrategy> placement;
    const std::string filename = checkpoint.filename();
    if (replicas == 0) {  // auto-detect
      if constexpr (model_is_tensor_parallel()) {
        replicas = 1;  // tensor parallelism across 2 or 4 devices
        placement = hardware::rotated_among_devices(devices, replicas);
      } else if (std::regex_search(
                     filename, std::regex("llama-3(.1)?-70b", std::regex::icase)))
        replicas = std::max(1ul, n_devices * 7 / 8);  // Distribute across cards.
    }
    if (std::regex_search(filename, std::regex("8x22b", std::regex::icase))) {
      placement = hardware::one_expert_per_device(devices);  // assuming 8 cards
    } else if (replicas > 0 && !placement) {
      size_t total_tensors = 0;
      plugin.visit_named_tensors(
          [&total_tensors](auto&, hardware::tensor_placement_request const&) noexcept {
            ++total_tensors;  // TODO record tensor shape.
          },
          max_layers);
      placement = hardware::shuffled_among_devices(devices, replicas, total_tensors);
    }
    if (!placement) placement = hardware::all_devices(devices);
    return placement;
  }

  void resolve_expert_routing_override(tensor_load_options const& opts,
      std::optional<expert_load_profile_t> const& expert_load) noexcept {
    expert_routing_override_.reset();
    if (opts.expert_routing_override == expert_routing_override_kind::uniform)
      expert_routing_override_.emplace(route_experts_uniformly{});
    else if (opts.expert_routing_override == expert_routing_override_kind::load &&
             expert_load.has_value()) {
      auto validation = expert_load->validate(plugin_t::expert_routing_top_k_by_router);
      if (validation)
        expert_routing_override_.emplace(route_experts_by_load{expert_load.value()});
      else
        spdlog::warn(
            "Ignoring expert-load profile for routing: {}", validation.error().message);
    }
  }

  // Note [Expert placement without a load profile]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  // With load-aware placement on and no usable profile, a model plans its experts
  // with uniform loads (Note [Expert placement planning]) if expert replicas are
  // requested, or if it is tensor-parallel and every expert matmul weight its plugin
  // visits is one tile. Otherwise experts keep the base placement. The uniform
  // profile steers placement only: `--expert-routing load` needs a measured profile.
  //
  // With `replicas` 0, select_placement's base placement for a tensor-parallel model
  // rotates tiles among the devices in visit order. Generated plugins visit each
  // expert weight in its own loop over experts, so when the device count divides
  // the expert count, rotation can put all of an expert's weights on one device.
  // The plan puts tensor ID t of an expert t devices past the expert's planned
  // device instead. Separate gate and up weights (Qwen3 MoE, ingested Mixtral),
  // whose matmuls are independent, can then run in parallel; GPT-OSS's fused
  // gate_up and its down then run on different devices.
  //
  // The plan gives all tiles of an expert weight the same devices, which would put
  // a tiled weight's whole matmul on one device. Generated plugins' expert weights
  // are expert_dtensor_t, one tile under every executor (Note [Expert matmuls]).
  // Handwritten Mixtral (llm) holds w2 as dtensor_t and w1 and w3 as
  // half_result_tiles<dtensor_t>, so tp2 tiles only w2 and tp4 all three. It keeps
  // its base placement, including 8x22B's one_expert_per_device. The count relies
  // on tile_count seeing through every wrapper a plugin visits; if it misses a
  // tile, placing that tile aborts the load.
  std::unique_ptr<hardware::PlacementStrategy> maybe_wrap_experts_by_load(
      std::unique_ptr<hardware::PlacementStrategy> base,
      hardware::device_mask devices,
      std::optional<expert_load_profile_t> const& expert_load,
      tensor_load_options const& opts,
      int max_layers) noexcept {
    if (!opts.load_aware_expert_placement) {
      TRON_ASSERT(opts.num_expert_replicas == 0,
          "num_expert_replicas={} requires load-aware expert placement",
          opts.num_expert_replicas);
      return base;
    }

    const auto wrap_with_expert_placement = [&](expert_load_profile_t const& profile,
                                                bool single_tile_experts) {
      return hardware::experts_by_load(std::move(base), devices, profile,
          plugin_t::expert_routing_top_k_by_router, opts.num_expert_replicas,
          single_tile_experts);
    };

    if (expert_load.has_value()) {
      spdlog::info("Placing experts by measured load");
      return wrap_with_expert_placement(
          expert_load.value(), /*single_tile_experts=*/false);
    }
    const bool plan_uniform =
        opts.num_expert_replicas > 0 ||
        (model_is_tensor_parallel() && expert_weights_are_single_tiles(max_layers));
    if (!plan_uniform) {
      spdlog::info("Experts keep the base placement without a usable load profile");
      return base;
    }

    if (opts.num_expert_replicas == 0)
      spdlog::info("Placing experts by uniform loads");
    else
      spdlog::info("Placing experts by uniform loads with up to {} additional replicas",
          opts.num_expert_replicas);
    const expert_load_profile_t uniform_load =
        expert_load_profile_t::uniform(n_moe_routers, plugin_t::n_routed_experts);
    // Without replicas, the plan rests on every expert weight being one tile.
    return wrap_with_expert_placement(
        uniform_load, /*single_tile_experts=*/opts.num_expert_replicas == 0);
  }

  void load_safetensors(std::filesystem::path checkpoint,
      std::string const& model_id,
      int max_layers = -1,
      tensor_load_options const& opts = {}) noexcept {
    size_t total_tensors = 0;
    {
      TRACE_EVENT("loading", "Count tensors");
      plugin.visit_named_tensors(
          [&total_tensors](auto&, hardware::tensor_placement_request const&) noexcept {
            ++total_tensors;
          },
          max_layers);
    }

    std::shared_ptr<fuse::fuse_sysfs::file_handle> fuse_total, fuse_loaded;
    if (fuse::stats::is_initialized()) {
      auto prefix = "/model/loading/" + model_id;
      fuse_total = fuse::stats::make_file(prefix + "/tensors_total",
          static_cast<uint64_t>(total_tensors),
          /*read_only=*/true, /*exported=*/true);
      fuse_loaded =
          fuse::stats::make_file(prefix + "/tensors_loaded", static_cast<uint64_t>(0),
              /*read_only=*/true, /*exported=*/true);
      // Per-metric .{tensors_total,tensors_loaded}.yaml descriptors
      // for this model. Content comes from kLoadingMetrics.
      fuse::register_tronstats_loading_metrics(prefix);
    }

    // Per-model MoE expert-routing stats — one subtree per loaded model
    // at /model/<id>/experts/. Non-MoE plugins skip this branch via
    // `if constexpr`. Registered alongside loading metrics so it joins
    // the tree before stats::start() in the canonical startup order.
    // See Note [MoE Expert Routing Stats] in expert_stats.hpp.
    if constexpr (plugin_t::moe) {
      tron::register_expert_stats_fuse_files(model_id, expert_stats_);
    }

    size_t loaded_tensors = 0;
    // TODO: remove this, and just invoke visit_named_tensors directly
    if (files::mock_safetensors_file) {
      TRACE_EVENT("loading", "Mock load");
      // Only during testing.
      auto& cp = *files::mock_safetensors_file;
      plugin.visit_named_tensors(
          [&cp, &loaded_tensors, fuse_loaded](
              auto& t, hardware::tensor_placement_request request) noexcept {
            cp.load(t, std::move(request));
            ++loaded_tensors;
            if (fuse::stats::is_initialized()) {
              fuse_loaded->set_value(static_cast<uint64_t>(loaded_tensors));
            }
          },
          max_layers);
      return;
    }

    with_safetensors_file(checkpoint, opts, [&](auto& file) {
      // check for lm_head and set tie_word_embeddings, llama 3.2 3b ties these to
      // reduce size
      bool tie_word_embeddings =
          !(file.contains("lm_head.weight") || file.contains("lm_head.g_idx"));
      plugin.visit_named_tensors(
          [&file, &loaded_tensors, fuse_loaded](
              auto& t, hardware::tensor_placement_request request) noexcept {
            file.load(t, std::move(request));
            ++loaded_tensors;
            if (fuse::stats::is_initialized()) {
              fuse_loaded->set_value(static_cast<uint64_t>(loaded_tensors));
            }
          },
          max_layers, tie_word_embeddings);
    });
  }

public:
  struct state : noncopyable<state> {
    // Mirror of the enclosing model's bound, so the free `chunk_evenly` /
    // `batch_evenly` helpers (which only see the state) can reach it.
    static constexpr size_t max_minibatch_size = model::max_minibatch_size;
    model const& model_ref;
    model_config cfg;
    size_t max_tokens;
    // Must be initialized before ffn_state.
    latch_arena latches;
    indexed_span<page_id, page* const> pages;
    indexed_span<token_id, const token_t> tokens;
    indexed_span<token_id, const uint32_t> token_positions;
    indexed_span<token_id, page* const> token_pages;
    indexed_span<token_id, activation_scalar const* const> eagle_x_in;
    indexed_span<token_id, activation_scalar* const> eagle_x_out;
    // Ranged mask for HW/SW attention partitioning.
    ranged_mask const* query_mask;
    // HW reads Q at HW_BAKED_HEAD_SIZE stride per head, regardless of
    // model head_size. When the two differ we keep a parallel padded
    // buffer that launch_hw_attention refreshes from the plugin's queries before
    // each HW dispatch; SW continues to read the plugin's queries unchanged.
    static constexpr bool need_q_padding = (head_size != hardware::HW_BAKED_HEAD_SIZE);
    static_option<need_q_padding,
        intermediate_t<n_heads * hardware::HW_BAKED_HEAD_SIZE>>
        hw_qs_for_attn;
    std::mutex wo_hwattn_mutex;
    // this is mutable because all the log_intermediate functions using this
    // stream are const, but writing to this stream changes its internal state
    mutable std::ofstream log_intermediate_file;
    // See Note [Forced Expert Routing] in forced_routing.hpp
    std::optional<forced_routing> forced_routing_data;

    // TODO: When the plugin architecture is done, we should audit uses of this
    // field, and remove the ones that do not conform to the interface spec.
    plugin_t::state plugin_state;

    // Class-scope alias so member-function bodies can name
    // self_attention even when a parameter shadows the class name
    // `model`.
    using self_attn_t = self_attention<model>;
    using self_attn_state_t = typename self_attn_t::template state<state, n_layers>;
    self_attn_state_t self_attn_state;
    intermediate_t<dim> final_embedding;
    size_t n_listeners;  // total listeners
    indexed_span<token_job_id, const token_id> token_jobs;
    indexed_span<token_job_id, const uint8_t> token_jobs_do_kv;
    // Tree-unaware GOF completion callback. Set by the scheduler
    // before forward() when HW attention is enabled. Called from
    // save_k/save_v when the last outstanding save completes a GOF.
    tron::hardware::gof_rodeo_fn_t gof_rodeo_fn;
    // Per-query GOF dispatch targets from the scheduler.
    indexed_span<token_job_id, const hardware::gof_job> gof_jobs_span;
    // Cooperative gof_rodeo: save_k/save_v enqueue a completed GOF here, and
    // idle attention workers drain it in parallel via help_drain_gof().
    // gof_coop_outstanding_ counts enqueued-but-unfinished submits so
    // wait_for_coop_gof() can barrier at forward end (before the scheduler
    // rebuilds gof_jobs, which gof_rodeo_impl dereferences). The submit path is
    // cross-thread safe; see Note [GOF dispatch synchronization] / Note [GOF
    // staging eviction].
    struct gof_coop_task {
      size_t job_ix = 0;
      size_t target_ix = 0;
      kv_slot_id slot{0};
      model_layer_id layer{0};
    };
    moodycamel::ConcurrentQueue<gof_coop_task> gof_coop_queue_;
    std::atomic<int64_t> gof_coop_outstanding_{0};
    indexed_span<listener_id, const token_id> listener_index;
    indexed_span<listener_id, const std::vector<logits_buffer_t>> listener_buffers;
    indexed_span<listener_id, const std::function<void()>> listener_notifications;
    // HW attention plan entries from the traversal. Set by the
    // scheduler before forward(). Read by construct_hw_plan.
    std::span<const hw_plan_entry> hw_plan_entries;
    indexed_vector<listener_id, token_job_id> listener_job_index;
    const size_t logits_chunk_size;
    size_t n_empty_listeners;
    size_t n_logit_listeners;
    size_t n_empty_chks;
    size_t n_logit_chks;
    // Final embeddings read by hardware, indexed by listener index
    using compensated_embeddings_t = btensor_t<wcls_is_compensated ? dim + dim : dim>;
    std::vector<compensated_embeddings_t> compensated_embeddings;
    using logits_t = btensor_t<vocab_size>;
    std::vector<logits_t> logits;  // written to by hardware

    // Per-model DMA completion tracker, sized by the active KV-slot extent.
    // Constructed only when HW attention is eligible (see ctor body);
    // empty optional means "this model does not use HW attention."
    // Push/poll/await call sites should null-check via has_value() or
    // run only inside the hw_attn_eligible branch that emplaces it.
    std::optional<tron::hardware::dma_tracker> dma_tracker;

    // DMA gate: spin-wait for DMA completion at a given KV slot.
    using dma_gate_observer_t = std::function<void(kv_slot_id)>;
    std::vector<dma_gate_observer_t> on_await_dma;
    // Forward-poll: non-blocking DMA completion check in forward().
    using forward_poll_observer_t = std::function<void()>;
    std::vector<forward_poll_observer_t> on_forward_poll;

    // Active session handle_id (set by scheduler before forward pass).
    uint64_t active_handle_id = 0;
    // Whether logit streams are allocated and ready to prepare
    std::vector<latch_ref> logits_allocated;
    // Whether logit streams have been prepared
    std::vector<latch_ref> logits_prepared;
    // Knowing whether logits of a chunk are ready for the listeners
    std::vector<latch_ref> logits_done;
    // Knowing whether logits buffers are free for reuse
    std::vector<latch_ref> logits_free;
    // Knowing whether all listeners have been notified
    latch_ref listeners_notified;
    using launch_wcls_t =
        wcls_t::template launch_matmul_for<compensated_embeddings_t, logits_t>;
    launch_wcls_t launch_wcls;
    std::vector<typename launch_wcls_t::stream_result_t> wcls_streams;

    std::vector<std::unique_ptr<batch>> q_batches;

    indexed_vector<token_id, token_job_id> token_job_id_of_token;

    // Gathered data indexed by token_job_id for efficient access
    indexed_vector<token_job_id, token_t> token_job_tokens;
    indexed_vector<token_job_id, uint32_t> token_job_positions;

    size_t min_main_helpers;
    size_t max_main_helpers;
    time_estimator main_time_estimator;
    time_estimator attn_time_estimator;

    // Active operation descriptors and their bound runtime configuration. See
    // Note [Per-attention-operation plans] in common.hpp.
    std::vector<attention_operation_descriptor> active_attention_operations;
    indexed_vector<attention_op_id, attention_runtime_config> attention_runtime_configs;
    // Finalized after hardware configuration. See Note [Hardware attention
    // eligibility].
    std::array<uint8_t, n_attention_ops> attention_operation_uses_hw{};
    indexed_vector<attention_op_id, attention_plan_id> attention_plan_id_for_operation;
    indexed_vector<attention_plan_id, attention_plan_profile> attention_plan_profiles;
    indexed_vector<attention_plan_id, size_t> attention_plan_operation_count;

    // Per-pass attention work estimates, computed by
    // estimate_attention_work() and consumed by assemble_attention_plan().
    // Indexed [minibatch][plan profile]; the inner array is indexed by pending
    // (0 = ready KV, 1 = pending KV).
    // See Note [Ready versus pending attention work].
    struct attention_work_t {
      std::vector<
          indexed_vector<attention_plan_id, std::array<std::vector<page_id>, 2>>>
          page_ixs;
      std::vector<indexed_vector<attention_plan_id,
          std::array<std::vector<work_estimate_t>, 2>>>
          page_work;
      // Per page, the half-open range of batch items with software work on
      // it; parallel to page_work, {0, 0} for a page with none.
      std::vector<indexed_vector<attention_plan_id,
          std::array<std::vector<std::pair<uint32_t, uint32_t>>, 2>>>
          page_qrange;
    };
    attention_work_t attn_work;

    // array is a forwarding reference so that generated code can pass temporary
    // sub-view objects (non-owning pointer+size wrappers); writes go through
    // the pointer to the underlying buffer, so binding an rvalue view is safe.
    TRON(inline)
    void log_intermediate(std::string message, auto&& array, size_t len) const {
      if tron_unlikely (cfg.log_intermediates) {
        std::lock_guard<std::mutex> lock(log_intermediates_mutex());
        if (!log_intermediate_file.is_open()) {
          spdlog::error("Failed to open log file for appending.");
          return;
        }

        if (model_ref.plugin.is_eagle) message = "Draft " + message;
        log_intermediate_file << std::setw(50) << message << " (" << len << "): ";
        for (size_t i = 0; i < len; i++) {
#ifdef PRINT_HEX  // alternate to print as hex uint16
          uint16_t val = *reinterpret_cast<const uint16_t*>(&array[i]);

          log_intermediate_file << " " << std::setw(11) << std::setprecision(8)
                                << fmt::format("\"0x{:04x}\"", val);
#else
          log_intermediate_file << " " << std::setw(11) << std::setprecision(8)
                                << float(array[i]);
#endif
        }
        log_intermediate_file << std::endl;
        log_intermediate_file.flush();
      }
    }

    template <typename Arg, typename... Args>
    TRON(inline)
    void log_intermediate(auto&& array,
        size_t len,
        fmt::format_string<Arg, Args...> fmt,
        Arg&& arg,
        Args&&... args) const {
      if tron_unlikely (cfg.log_intermediates) {
        std::string msg =
            fmt::format(fmt, std::forward<Arg>(arg), std::forward<Args>(args)...);
        log_intermediate(msg, array, len);
      }
    }

    template <typename... Args>
    TRON(inline)
    void log_intermediate(auto&& array,
        size_t len,
        token_job_id tok,
        fmt::format_string<Args...> fmt,
        Args&&... args) const {

      if tron_unlikely (cfg.log_intermediates) {
        std::string msg = fmt::format(fmt, std::forward<Args>(args)...);
        size_t token_num = token_jobs[tok].i;
        log_intermediate(msg + " of token " + std::to_string(token_num), array, len);
      }
    }

    template <typename... Args>
    TRON(inline)
    void log_intermediate(auto&& array,
        size_t len,
        token_job_id tok,
        size_t layer,
        fmt::format_string<Args...> fmt,
        Args&&... args) const {

      if tron_unlikely (cfg.log_intermediates) {
        std::string msg = fmt::format(fmt, std::forward<Args>(args)...);
        size_t token_num = token_jobs[tok].i;
        log_intermediate(msg + " layer " + std::to_string(layer) + " of token " +
                             std::to_string(token_num),
            array, len);
      }
    }

    state(model const& model, model_config cfg)
    : model_ref(model)
    , cfg([&] {
      auto c = std::move(cfg);
      c.merge_max_minibatches(max_minibatches);
      return c;
    }())
    , max_tokens(0)
    , latches()
    , query_mask(nullptr)
    , plugin_state(model.plugin, *this, this->cfg)
    , self_attn_state(*this)
    , logits_chunk_size(init_logits_chunk_size())
    , compensated_embeddings(logits_chunk_size)
    , logits(logits_chunk_size)
    , min_main_helpers(init_min_main_helpers())
    , max_main_helpers(init_max_main_helpers()) {
      TRON_ASSERT_LE(min_main_helpers, max_main_helpers);
      build_attention_operation_table();
      resize(256);
      configure_hw_attention();
      cache_attention_operation_hardware_eligibility();
      build_attention_plan_table();

      if tron_unlikely (this->cfg.log_intermediates) {
        std::lock_guard<std::mutex> lock(log_intermediates_mutex());
        std::string log_file_name = "log_intermediate.txt";
        // override with filename supplied in the config if supplied
        if (this->cfg.intermediates_filename) {
          log_file_name = *this->cfg.intermediates_filename;
        }
        // remove existing log file first if it exists
        std::remove(log_file_name.c_str());
        log_intermediate_file.open(log_file_name, std::ios::out | std::ios::app);
        if (!log_intermediate_file.is_open()) {
          spdlog::error("Failed to open log file for appending.");
        }
      }
      if (this->cfg.forced_routing_file) {
        forced_routing_data.emplace(
            forced_routing::load(*this->cfg.forced_routing_file));
      }
      spdlog::info("Allocated state {}", ::tron::type<state>().get());
    }

    void build_attention_operation_table() {
      active_attention_operations.clear();
      attention_runtime_configs.clear();
      size_t const operation_count =
          plugin_t::active_attention_operation_count((size_t)cfg.max_layers);
      TRON_ASSERT_LE(operation_count, plugin_t::attention_operations.size());
      for (size_t operation_ix = 0; operation_ix < operation_count; ++operation_ix) {
        auto const& operation = plugin_t::attention_operations[operation_ix];
        TRON_ASSERT_LT(operation.binding.model_layer.i, (size_t)cfg.max_layers);
        TRON_ASSERT_EQ(
            operation.binding.operation.i, active_attention_operations.size());
        TRON_ASSERT_LT(operation.kernel.i, plugin_t::attention_kernels.size());
        TRON_ASSERT_LT(operation.binding.kv_slot.i, cache_t::n_slots);
        TRON_ASSERT_LT(operation.binding.kv_slot.i,
            cache_t::logical_slot_count_for_layers((size_t)cfg.max_layers));
        TRON_ASSERT(
            !model_ref.plugin.is_eagle || operation.binding.kv_slot == kv_slot_id(0),
            "EAGLE operation {} must bind KV slot zero", operation.binding.operation);
        TRON_ASSERT(cache_t::kv_slot_specs[operation.binding.kv_slot.i].geometry ==
                        kernel_for(operation).geometry.kv,
            "operation {} kernel {} geometry does not match KV slot {}",
            operation.binding.operation, operation.kernel, operation.binding.kv_slot);
        TRON_ASSERT(
            operation.hardware != attention_hardware_capability::kv_slot_candidate ||
                operation_is_hardware_candidate(operation),
            "operation {} kernel {} must explicitly select software for its cache "
            "binding and geometry",
            operation.binding.operation, operation.kernel);
        active_attention_operations.push_back(operation);
        attention_runtime_configs.push_back(
            bind_attention_runtime_config(model_ref.plugin, operation));
      }
    }

    attention_kernel_spec const& kernel_for(
        attention_operation_descriptor const& operation) const noexcept {
      return attention_kernel_at(plugin_t::attention_kernels, operation.kernel);
    }

    template <attention_geometry geometry, size_t operation_ix>
    static consteval bool valid_generated_attention_operation() noexcept {
      if constexpr (operation_ix >= plugin_t::attention_operations.size()) {
        return false;
      } else {
        constexpr auto const& operation = plugin_t::attention_operations[operation_ix];
        if (operation.binding.operation.i != operation_ix ||
            operation.kernel.i >= plugin_t::attention_kernels.size())
          return false;
        return plugin_t::attention_kernels[operation.kernel.i].geometry == geometry &&
               cache_t::template slot_matches<geometry.kv>(operation.binding.kv_slot);
      }
    }

    template <attention_geometry geometry, size_t operation_ix>
    static constexpr attention_operation_descriptor const&
    generated_attention_operation() noexcept {
      static_assert(valid_generated_attention_operation<geometry, operation_ix>());
      return plugin_t::attention_operations[operation_ix];
    }

    attention_operation_descriptor const& operation_for(
        attention_binding binding) const noexcept {
      TRON_ASSERT_LT(binding.operation.i, plugin_t::attention_operations.size());
      auto const& operation = plugin_t::attention_operations[binding.operation.i];
      TRON_ASSERT(operation.binding == binding,
          "attention binding disagrees with canonical operation {}", binding.operation);
      return operation;
    }

    template <attention_geometry... operation_geometries>
    static consteval bool valid_generated_attention_plan() noexcept {
      if constexpr (sizeof...(operation_geometries) !=
                    plugin_t::attention_operations.size()) {
        return false;
      } else {
        constexpr std::array<attention_geometry, sizeof...(operation_geometries)>
            geometries{operation_geometries...};
        for (size_t operation_ix = 0; operation_ix < geometries.size();
            ++operation_ix) {
          auto const& operation = plugin_t::attention_operations[operation_ix];
          if (operation.binding.operation.i != operation_ix ||
              operation.kernel.i >= plugin_t::attention_kernels.size() ||
              geometries[operation_ix] !=
                  plugin_t::attention_kernels[operation.kernel.i].geometry)
            return false;
        }
        return true;
      }
    }

    template <typename buffer_t>
    inline static constexpr size_t attention_buffer_width = std::remove_cvref_t<
        decltype(std::declval<buffer_t&>()[token_job_id(0)].as_view())>::size_;

    bool operation_is_hardware_candidate(
        attention_operation_descriptor const& operation) const noexcept {
      return is_hardware_attention_candidate(plugin_t::attention_kernels,
          cache_t::kv_slot_specs, operation, hardware_attention_geometry);
    }

    void cache_attention_operation_hardware_eligibility() {
      for (auto const& operation : active_attention_operations) {
        attention_op_id const op = operation.binding.operation;
        attention_operation_uses_hw[op.i] =
            static_cast<uint8_t>(self_attn_state.compute_operation_uses_hw(operation));
      }
    }

    void build_attention_plan_table() {
      attention_plan_id_for_operation.clear();
      attention_plan_profiles.clear();
      attention_plan_operation_count.clear();
      for (auto const& operation : active_attention_operations) {
        attention_op_id const op = operation.binding.operation;
        attention_plan_profile const profile{kernel_for(operation).geometry,
            attention_runtime_configs[op].sliding_window_size,
            cached_operation_uses_hw(op)};
        auto const prior = std::find(
            attention_plan_profiles.begin(), attention_plan_profiles.end(), profile);
        attention_plan_id plan_id(0);
        if (prior == attention_plan_profiles.end()) {
          plan_id = attention_plan_id(attention_plan_profiles.size());
          attention_plan_profiles.push_back(profile);
          attention_plan_operation_count.push_back(0);
        } else {
          plan_id = attention_plan_id(
              static_cast<size_t>(prior - attention_plan_profiles.begin()));
        }
        attention_plan_id_for_operation.push_back(plan_id);
        ++attention_plan_operation_count[plan_id];
      }
    }

    TRON(nodiscard, inline, pure)
    bool cached_operation_uses_hw(attention_op_id operation) const noexcept {
      return attention_operation_uses_hw[operation.i] != 0;
    }

    void configure_hw_attention() {
      if (!model_instance_is_hwattn_eligible(model_ref.plugin.is_eagle)) {
        spdlog::info(
            "HW-attention not available for this model. Will use SW-only path.");
        return;
      }
      if (!self_attn_state.hardware_scale_is_representable()) {
        spdlog::info(
            "HW-attention scale is not representable on device. Will use SW-only "
            "path.");
        return;
      }
      if constexpr (model_shape_is_hwattn_eligible()) {
        auto* devs = pos_list_devices();
        bool have_devices = devs && !devs->empty();
        bool use_hw_attn = use_hw_attn_for_this_model();
        if (have_devices && use_hw_attn) {
          auto& cfg_ref = self_attn_state.hw_attn_cfg;
          hardware::clear_hw_slots(cfg_ref);
          // Set a bit only for operations whose kernel and selected KV slot match
          // the bitfile geometry. Other operations use software.
          size_t hw_attn_kv_slot_extent = 0;
          for (auto const& operation : active_attention_operations) {
            const size_t op_ix = operation.binding.operation.i;
            if (operation_is_hardware_candidate(operation) &&
                attention_runtime_configs[attention_op_id(op_ix)].sliding_window_size ==
                    self_attn_t::illegal_sliding_window) {
              kv_slot_id const slot = operation.binding.kv_slot;
              hardware::enable_hw_slot(cfg_ref, slot);
              hw_attn_kv_slot_extent = std::max(hw_attn_kv_slot_extent, slot.i + 1);
            }
          }
          if (!hardware::has_hw_slots(cfg_ref)) {
            spdlog::info(
                "HW-attention has no eligible operations. Will use SW-only path.");
            return;
          }
          // Per-state HW attention config. Each model owns its own here so
          // target+draft (speculative decoding) cannot clobber each other
          TRON_ASSERT(cfg_ref.kv_head_size > 0, "kv_head_size is 0");
          TRON_ASSERT(cfg_ref.kv_head_size % 64 == 0,
              "kv_head_size {} must be multiple of 64", cfg_ref.kv_head_size);
          TRON_ASSERT(cfg_ref.n_kv_heads > 0 && cfg_ref.n_heads > 0,
              "n_kv_heads={} n_heads={}", cfg_ref.n_kv_heads, cfg_ref.n_heads);
          TRON_ASSERT(cfg_ref.n_kv_heads <= hardware::HW_MAX_KV_HEADS,
              "n_kv_heads {} exceeds HW_MAX_KV_HEADS {}", cfg_ref.n_kv_heads,
              hardware::HW_MAX_KV_HEADS);
          TRON_ASSERT(cfg_ref.n_heads % cfg_ref.n_kv_heads == 0,
              "n_heads {} not divisible by n_kv_heads {}", cfg_ref.n_heads,
              cfg_ref.n_kv_heads);
          TRON_ASSERT(cfg_ref.n_heads / cfg_ref.n_kv_heads <= hardware::HW_MAX_GQA,
              "gqa {} (n_heads {} / n_kv_heads {}) exceeds HW_MAX_GQA {}",
              cfg_ref.n_heads / cfg_ref.n_kv_heads, cfg_ref.n_heads, cfg_ref.n_kv_heads,
              hardware::HW_MAX_GQA);
          self_attn_state.hw_attn_kv_slot_extent = hw_attn_kv_slot_extent;
          self_attn_state.hw_attn_eligible = true;
          const char* env = std::getenv("USE_HW_ATTN");
          spdlog::info(
              "HW attention enabled for model '{}': max_layers={} engagement={} "
              "kv_slot_extent={} {}{}",
              cfg.id, cfg.max_layers, hw_attn_engagement_point(),
              hw_attn_kv_slot_extent, cfg_ref.debug_string(),
              env != nullptr           ? " (USE_HW_ATTN)"
              : model_forces_hw_attn() ? " (model default)"
                                       : "");
          for (auto* dev : *devs) {
            if (!hwattn_wlr_bitfile_ok(dev->id_dat_raw)) {
              spdlog::info("Dev {}: bitfile does not support HW attention WLR; "
                           "update to >= 01.05.08.00 (project 01) or "
                           ">= 03.05.08.00 dated 2026-05-18+ (project 03) to enable",
                  dev->addr());
            }
          }
          // Sanity... we should never reach here with invalid cfg.max_layers, but
          // make sure of it anyway
          TRON_ASSERT_GT(hw_attn_kv_slot_extent, 0);
          dma_tracker.emplace(hw_attn_kv_slot_extent, cfg.id);
          // GOF dispatch uses the gof_rodeo path (tree-unaware).
          // gof_rodeo_fn is set by the scheduler before forward().
          on_await_dma.push_back(
              [this](kv_slot_id slot) { dma_tracker->await_slot(slot); });
          on_forward_poll.push_back([this]() { dma_tracker->poll_completions(); });
        } else {
          std::string reason;
          if (!use_hw_attn) {
            // use_hw_attn_for_this_model() gates on EMEM capacity before the
            // USE_HW_ATTN env var, so an EMEM/n_heads failure must not be
            // reported as an explicit user disable.
            if (hardware::max_shards_for_emem(
                    n_heads, head_size, hardware::shard_tokens) == 0) {
              reason =
                  "EMEM cannot fit a shard for n_heads=" + std::to_string(n_heads) +
                  " (head_size=" + std::to_string(head_size) + ")";
            } else {
              reason = std::getenv("USE_HW_ATTN") != nullptr
                           ? "USE_HW_ATTN=0"
                           : "default off for this model";
            }
          }
          if (!have_devices) {
            if (!reason.empty()) reason += "; ";
            reason += "no POS devices available";
          }
          spdlog::info("HW attention disabled for model '{}': {}", cfg.id, reason);
        }
      }
    }

    void resize(size_t max_tokens) {
      TRACE_EVENT("model", "resize");
      if (this->max_tokens >= max_tokens)
        // Avoid destructor;constructor thrashing.
        // We never call std::vector::shrink_to_fit() anyway.
        return;
      // Caches and buffers used internally in the pass.
      // Currently we allocate _way_ too many btensors here.
      // Can we offer an arena-allocator for them or something?
      token_job_tokens.resize(max_tokens);
      token_job_positions.resize(max_tokens);
      plugin_state.resize(max_tokens);
      if constexpr (need_q_padding) hw_qs_for_attn.resize(max_tokens);
      final_embedding.resize(max_tokens);
      this->max_tokens = max_tokens;
    }

    /**
     * @brief The forward pass of the Llama model.
     *
     * We are working in a paged attention setting, where there is a prefix-tree of
     * tokens in flight at any given time.  The goal of the
     * `forward` function is to accept a snapshot of such a tree, and do two things:
     * - Fill in all the KV tensors that are missing from the tree
     * - Provide logits corresponding to all locations anyone wants logits for
     *
     * We accept a slice of the tree from the caller.
     *
     * The parameters are a set of parallel arrays with cross-references, kept straight
     * by the typed indexing discipline (see Note [Typed Indexing]).  This amounts to
     * an efficient representation of a fixed object graph.  The relevant index types
     * are
     * - token_id, indexing live tokens (see Note [KV Token Lifetimes]).  The live
     *   tokens are laid out as a pre-order traversal of the token tree.  Ergo, the
     *   descendants of any token---which are the tokens that may attend to it---
     *   are contiguous in the token_id order, and therefore laid out contiguously
     *   in arrays indexed by token_id.
     * - token_job_id, indexing token jobs, aka query tokens.  These are the tokens
     *   about which we need to compute something (KV entries and/or logits).
     * - page_id, indexing KV pages.
     * - listener_id, indexing listener notifications whither logits are to be supplied.
     *
     * @param in_pages The tree of KV tensors, stored as an array of pages laid out as a
     *   pre-order traversal of the tree.  Each page accounts for `page.count()` tokens
     *   (at most `page_size`).  This is an in-out parameter: `forward` will read
     *   the KV tensors for nodes that have already been computed, and write any new
     *   ones.
     * @param in_tokens For each live token, the actual token, for indexing the initial
     *   embedding table.
     * @param in_token_positions For each live token, its position in the corresponding
     *   input sequence. This is not its position in the tree, but the count of other
     *   tokens on the way from the root. We use this to tell the model where in its
     *   sequence that token is.
     * @param in_token_pages For each live token, the page it is on.
     * @param in_groups For each live token, its minibatch group ID.
     *   We accept these for all tokens, but only use the information for query tokens.
     * @param in_token_jobs For each token job, the token_id for that job
     * @param in_token_jobs_do_kv For each token job, 1 if it needs KV computation.
     * @param in_listener_index For each listener notification, the token_id of the
     *   token at which that listener wants logits. The logits are for the next token
     *   after the indexed one. Each callback only receives one set of logits
     *   corresponding to one position.
     * @param in_listener_buffers For each listener notification, an array of vectors of
     *   storage pointers.  In each vector there is a storage
     *   pointer for each listener callback associated with the notification.
     * @param in_listener_notifications For each listener notification, a function to
     *   notify listeners with the computed logits.
     */
    void forward(indexed_vector<page_id, page*> const& in_pages,
        indexed_vector<token_id, token_t> const& in_tokens,
        indexed_vector<token_id, uint32_t> const& in_token_positions,
        indexed_vector<token_id, page*> const& in_token_pages,
        indexed_vector<token_id, token_batching_affinity_id> const& in_live_groups,
        indexed_vector<token_id, activation_scalar const*> const& in_eagle_x_in,
        indexed_vector<token_id, activation_scalar*> const& in_eagle_x_out,
        indexed_vector<token_job_id, token_id> const& in_token_jobs,
        indexed_vector<token_job_id, uint8_t> const& in_token_jobs_do_kv,
        indexed_vector<listener_id, token_id> const& in_listener_index,
        indexed_vector<listener_id, std::vector<logits_buffer_t>> const&
            in_listener_buffers,
        indexed_vector<listener_id, std::function<void()>> const&
            in_listener_notifications,
        ranged_mask const& query_mask_in) noexcept {
      MODEL_DEBUG("{}", __PRETTY_FUNCTION__);
      TRACE_EVENT("scheduler", "forward", "n_token_jobs", in_token_jobs.size(),
          "n_tokens", in_tokens.size(), "n_listeners", in_listener_index.size());

      // Attention path stats (Note [Attention path stats] in attn_stats.hpp):
      // one object owns this forward's record. decode_like = every token job
      // has a listener (one generated token per user, but also a 1-token final
      // prompt chunk or a speculative verify step). prompt_or_mixed = every
      // other forward. Under continuous batching (rinzler adds users between
      // forwards) a forward that carries one user's prompt chunk next to
      // other users' generated tokens is prompt_or_mixed. The listener count
      // records how mixed it was. The object is declared before the latch
      // guard. So its destructor runs after the guard's, at the very end of
      // the forward.
      attn_stats::forward_scope attn_stats_scope(*self_attn_state.stats,
          in_listener_index.size() == in_token_jobs.size()
              ? attn_stats::forward_class::decode_like
              : attn_stats::forward_class::prompt_or_mixed,
          in_token_jobs.size(), in_listener_index.size());
      with_latch_arena latches_guard(latches);

      pages = in_pages;
      tokens = in_tokens;
      token_positions = in_token_positions;
      token_pages = in_token_pages;
      eagle_x_in = in_eagle_x_in;
      eagle_x_out = in_eagle_x_out;
      token_jobs = in_token_jobs;
      token_jobs_do_kv = in_token_jobs_do_kv;
      listener_index = in_listener_index;
      listener_buffers = in_listener_buffers;
      listener_notifications = in_listener_notifications;
      n_listeners = in_listener_index.size();
      query_mask = &query_mask_in;

      // Bump the cumulative MoE pass counter exposed under
      // /model/<id>/experts/total_passes. Non-MoE plugins compile this
      // away (the `if constexpr` and the field both go to monostate).
      // See Note [MoE Expert Routing Stats] in expert_stats.hpp.
      if constexpr (plugin_t::moe) {
        model_ref.expert_stats_.total_passes.fetch_add(1, std::memory_order_relaxed);
      }

      run_forward(in_live_groups);
    }

    TRON(nodiscard, inline)
    page& page_of(token_id tok) const noexcept {
      return *token_pages[tok];
    }

    // Called by forward() only. forward() owns the attention path stats
    // record of the forward (attn_stats::forward_scope). A second caller of
    // run_forward would file the workers' rows and fpga_queries under the
    // previous forward's class, and its path bits would be folded into the
    // next forward.
    void run_forward(
        indexed_span<token_id, const token_batching_affinity_id> live_groups) {
      // Writes: n_empty_listeners, n_logit_listeners, n_empty_chks, n_logit_chks
      partition_listeners(logits_chunk_size);
      // Writes: token_job_id_of_token, listener_job_index
      gather_token_job_ids();
      // Resizes: major intermediates
      resize(token_jobs.size());
      // Writes: q_batches
      construct_minibatches(live_groups);
      // Writes: attn_work; records work into the time estimators
      estimate_attention_work();
      // Writes: Minibatch latches and kv dependencies
      finalize_minibatches();
      // Reads: n_listeners; writes: logit latch/channel state
      setup_logits(n_listeners, logits_chunk_size, latches);
      // Writes: token_job_tokens, token_job_positions
      gather_token_data();
      // Note [Plugin-owned worker launch]
      // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      // The plugin's `run` method owns the allocation of app-pool threads
      // between main helpers and attention workers, and the launch of all
      // work on them:
      //
      // - `run` may enqueue work onto `app_pool()`.
      // - If the model has attention work, `run` must pick a number of
      //   attention workers n_attn_workers >= 1, call
      //   `assemble_attention_plan(n_attn_workers)`, reset each minibatch's
      //   channels via `q_batch->reset_channels(n_attn_workers,
      //   n_main_workers)`, and arrange for its attention-worker schedule to
      //   execute on pool worker
      //   `num_workers() - n_attn_workers + i` for every i in
      //   [0, n_attn_workers) -- see Note [Attention workers are the last
      //   pool workers].  The same n_attn_workers value must be used for
      //   all of these; run_sections asserts this against the plan.
      // - `recommend_n_main_helpers()` is the framework's split heuristic;
      //   plugins are free to use it or to choose differently.  In
      //   pay_for_determinism mode the split must be stable from pass to
      //   pass, because the attention plan depends on it (see
      //   Note [Paying for Determinism]); the recommendation handles this.
      // - Before returning, `run` must wait for all the work it spawned.
      //   This synchronization obligation is on the plugin -- including
      //   generated plugins -- because the framework cannot observe the
      //   plugin's spawned work.  Without it, this thread might read
      //   `final_embedding` in `run_logits` below before a helper finishes
      //   writing it.  (The main thread reads all of `final_embedding`
      //   because the read is indexed by listeners, whereas the write is
      //   indexed by token job ids.)  The pool is also reused for logit
      //   delivery immediately after `run` returns.
      // - Matmul completion callbacks are not work `run` spawned on the
      //   pool, and `run` need not wait for them.  Each launch site counts
      //   its callback on the minibatch's `matrix_callbacks` latch, and the
      //   minibatch destructor waits for them when `q_batches` is cleared
      //   below.  See Note [Matrix callback lifetime] in common.hpp.
      plugin_state.run(q_batches);

      // Finish any cooperative gof_rodeo before the scheduler rebuilds gof_jobs
      // (gof_rodeo_impl dereferences gof_jobs_span). No-op when the queue is empty.
      wait_for_coop_gof();

      // Launch logit delivery
      thread_pool& tp = app_pool();
      for (size_t i = 0; i < logits_chunk_size; ++i)
        tp.enqueue_to(
            i, [i, this]() { run_listener_notifications(logits_chunk_size, i); });
      run_logits(logits_chunk_size);

      // Explicitly deconstruct the q_batches before the latch arena
      // vanishes under them.  This waits for their outstanding matmul
      // callbacks; see Note [Matrix callback lifetime] in common.hpp.
      q_batches.clear();
    }  // void run_forward()

    // Helpers for run_forward, defined in invocation order.

    void partition_listeners(size_t logits_chunk_size) noexcept {
      TRACE_EVENT("model", "partition_listeners");
      // A listener requests logits iff any of its buffers is nontrivial.
      // Assume listeners are sorted with trivial buffers first.
      n_empty_listeners = 0;
      for (listener_id i : listener_buffers.indices()) {
        auto const& bs = listener_buffers[i];
        bool requests_logits = std::any_of(bs.begin(), bs.end(),
            [](auto const& b) { return !std::holds_alternative<std::monostate>(b); });
        if (requests_logits) break;
        ++n_empty_listeners;
      }
      n_logit_listeners = n_listeners - n_empty_listeners;
      n_empty_chks = (n_empty_listeners + logits_chunk_size - 1) / logits_chunk_size;
      n_logit_chks = (n_logit_listeners + logits_chunk_size - 1) / logits_chunk_size;
    }

    void gather_token_job_ids() {
      TRACE_EVENT("model", "gather_token_job_ids");
      token_job_id_of_token.clear();
      token_job_id_of_token.resize(tokens.size());
      for (token_job_id i : token_jobs.indices())
        token_job_id_of_token[token_jobs[i]] = i;

      listener_job_index.resize(n_listeners);
      for (listener_id i : listener_index.indices()) {
        token_id tok = listener_index[i];
        listener_job_index[i] = token_job_id_of_token[tok];
      }

      // Every token job must need KV, a listener, or both.
      indexed_vector<token_job_id, uint8_t> has_listener(token_jobs.size());
      for (listener_id i : listener_job_index.indices())
        has_listener[listener_job_index[i]] = 1;
      for (token_job_id j : token_jobs.indices()) {
        TRON_ASSERT(token_jobs_do_kv[j] || has_listener[j],
            "Token job {} neither needs KV nor has a listener", j.i);
      }
    }

    // Create minibatches from token jobs grouped by live_groups.
    void construct_minibatches(
        indexed_span<token_id, const token_batching_affinity_id> live_groups) {
      TRACE_EVENT("model", "construct_minibatches");
      indexed_vector<token_job_id, token_batching_affinity_id> job_groups;
      // reserve rather than size-initialize so token_batching_affinity_id doesn't need
      // a default constructor
      job_groups.reserve(token_jobs.size());
      for (token_job_id i : token_jobs.indices())
        job_groups.push_back(live_groups[token_jobs[i]]);
      q_batches = batch_evenly<batch>(
          *this, token_jobs.size(), job_groups.items.data(), latches);
      if (cfg.max_minibatches >= 0)
        TRON_ASSERT(q_batches.size() <= (uint64_t)cfg.max_minibatches);
    }

    // Classify pages as pending (have KV work) or ready (KV already cached),
    // then select and work-estimate the pages relevant to each (minibatch,
    // attention config).  Records work totals into the time estimators and
    // leaves per-page estimates in `attn_work` for assemble_attention_plan.
    void estimate_attention_work() {
      TRACE_EVENT("model", "estimate_attention_work");
      std::vector<page_id> ready_page_ixs;
      std::vector<page_id> pending_page_ixs;
      std::unordered_set<page*> pending_pages;
      for (token_job_id j : token_jobs.indices())
        if (token_jobs_do_kv[j]) pending_pages.insert(token_pages[token_jobs[j]]);
      for (page_id ix : pages.indices()) {
        if (pending_pages.count(pages[ix]))
          pending_page_ixs.push_back(ix);
        else
          ready_page_ixs.push_back(ix);
      }

      // Note [Ready versus pending attention work]
      // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      // Compute how much work every page is and partition the plan sections for the
      // `ready` and `pending`.
      //
      // Why do we even have a `ready` and a `pending`?  Because a token can attend to
      // itself. That is, a token's Q gets compared against that same token's K, and
      // therefore that token's own V may contribute (perhaps substantially) to its O.
      // Ergo, in order to compute a token's attention, we have to have that token's K-V
      // entries on hand.
      //
      // However, we can _start_ any token's attention as soon as we have its Q, thus
      // possibly overlapping some CPU attention work with the FPGAs working on K and V.
      // For this purpose, we partition the KV cache into the "ready" portion (those
      // pages that are already there, and won't get any updates in this `forward` pass)
      // and the "pending" portion (those pages that _are_ getting updated).  We can't
      // start work on the latter until we have the values, but since we plan them
      // into separate sections in assemble_attention_plan, the reduction plan
      // still remains deterministic.
      //
      // See Note [Per-attention-operation plans] in common.hpp.
      const size_t n_plans = attention_plan_profiles.size();
      attn_work.page_ixs.clear();
      attn_work.page_ixs.resize(q_batches.size());
      attn_work.page_work.clear();
      attn_work.page_work.resize(q_batches.size());
      attn_work.page_qrange.clear();
      attn_work.page_qrange.resize(q_batches.size());
      std::vector<indexed_vector<attention_plan_id, work_estimate_t>> batch_work_total(
          q_batches.size());
      int64_t weighted_total_work = 0;
      for (size_t b = 0; b < q_batches.size(); ++b) {
        batch* q_batch = q_batches[b].get();
        attn_work.page_ixs[b].resize(n_plans);
        attn_work.page_work[b].resize(n_plans);
        attn_work.page_qrange[b].resize(n_plans);
        batch_work_total[b].resize(n_plans);
        for (attention_plan_id plan_id : attention_plan_profiles.indices()) {
          attention_plan_profile const& profile = attention_plan_profiles[plan_id];
          TRACE_EVENT("model", "estimate attention work", "plan", plan_id.i, "window",
              profile.sliding_window_size, "minibatch", b);

          // Step 1. Filter to pages relevant to this minibatch, and sort pages
          // for cache locality of (q,scratchpad) data. We simply sort by the
          // first token-rank-in-minibatch that participates in each page.
          select_relevant_pages(q_batch->items, attn_work.page_ixs[b][plan_id],
              ready_page_ixs, pending_page_ixs, profile.sliding_window_size);

          // Step 2. Estimate the amount of work per page and total.
          // Work is in units of dot products.
          // Work is identical for all KV heads but differs in ready vs pending.
          estimate_work(q_batch->items, attn_work.page_ixs[b][plan_id],
              attn_work.page_work[b][plan_id], attn_work.page_qrange[b][plan_id],
              batch_work_total[b][plan_id], profile.sliding_window_size,
              profile.geometry.n_query_heads, profile.geometry.kv.n_kv_heads,
              profile.uses_hw);

          weighted_total_work += batch_work_total[b][plan_id].work() *
                                 (int64_t)attention_plan_operation_count[plan_id];
        }
      }
      main_time_estimator.record_work(token_jobs.size());
      attn_time_estimator.record_work(weighted_total_work);
    }

    // Initialize latches and inter-batch dependencies.  (Minibatch channels
    // are reset by the plugin, which owns the worker counts they need; see
    // Note [Plugin-owned worker launch].)
    void finalize_minibatches() {
      TRACE_EVENT("model", "finalize_minibatches");
      plugin_state.make_latches(latches);

      // Compute dependencies of q_batches on each other.
      // See Note [Minibatch Dependency Tracking]
      for (auto& q_batch : q_batches)
        for (auto& other_q_batch : q_batches) {
          page const* previous_page = nullptr;
          for (auto& item : q_batch->items) {
            auto const* current_page = &page_of(token_jobs[item]);
            // A failed page-wide check covers the remaining consecutive
            // producer tokens on the same physical page.
            if (current_page == previous_page) continue;
            previous_page = current_page;
            if (other_q_batch->token_ix_needed(token_jobs[item], this)) {
              other_q_batch->kvs_needed += 2;
              q_batch->downstream_minibatches.push_back(other_q_batch.get());
              break;
            }
          }
        }
      std::array<bool, cache_t::n_slots> slot_has_writer{};
      for (auto const& operation : active_attention_operations)
        slot_has_writer[operation.binding.kv_slot.i] |= operation.writes_kv;
      for (auto& q_batch : q_batches) {
        std::array<bool, cache_t::n_slots> slot_reset{};
        for (auto const& operation : active_attention_operations) {
          kv_slot_id slot = operation.binding.kv_slot;
          if (slot_reset[slot.i]) continue;
          q_batch->upstream_kvs_ready[slot].reset(
              slot_has_writer[slot.i] ? q_batch->kvs_needed : 0);
          slot_reset[slot.i] = true;
        }
      }
    }

    void gather_token_data() noexcept {
      TRACE_EVENT("model", "gather_token_data");
      for (token_job_id i : token_jobs.indices()) {
        token_id tok = token_jobs[i];
        // See Note [Model-boundary input token remapping].
        token_job_tokens[i] =
            apply_input_token_remapping(model_ref.plugin, tokens[tok]);
        token_job_positions[i] = token_positions[tok];
      }
    }

    void setup_logits(
        size_t n_listeners, size_t logits_chunk_size, latch_arena& latches) {
      TRACE_EVENT("model", "setup_logits");
      // Set up interlocks for parallel logit computation
      size_t n_logit_chks = (n_listeners + logits_chunk_size - 1) / logits_chunk_size;
      if constexpr (launch_wcls_t::can_stream_result) {
        logits_allocated.resize(n_logit_chks);
        for (latch_ref& ref : logits_allocated)
          ref = latches.make_latch(1, "logits_allocated");
        logits_prepared.resize(n_logit_chks);
        for (latch_ref& ref : logits_prepared)
          ref = latches.make_latch(1, "logits_prepared");
      }
      logits_done.resize(n_logit_chks);
      for (latch_ref& ref : logits_done)
        ref = latches.make_latch(1, "logits_done");
      logits_free.resize(n_logit_chks);
      for (latch_ref& ref : logits_free)
        ref = latches.make_latch(logits_chunk_size, "logits_free");
      listeners_notified = latches.make_latch(logits_chunk_size, "listeners_notified");
    }

    // Fixed main-helper split used when autotuning is unavailable or
    // disabled. The fraction is tuned: it seems to give the best
    // performance for gpt-oss on 2048-in 512-out, 4 users, 4 cards.
    // Changing it changes the attention plan, and with it the exact
    // logits every pay_for_determinism test produces, shifting their
    // margins against recorded goldens.
    size_t fixed_main_helper_split() const noexcept {
      return (app_pool().num_workers() * 2) / 7;
    }

    // Recommends a main | attention worker split based on time spent and
    // work estimates (as recorded by estimate_attention_work).
    size_t recommend_n_main_helpers() const noexcept {
      // Default, used before the time estimators have data.
      size_t n_main_helpers = (min_main_helpers + max_main_helpers) / 2;
      if (max_main_helpers == 0) {
        n_main_helpers = 0;
      } else if (cfg.pay_for_determinism) {
        // Determinism requires the helper count to be a function of
        // nothing measured at runtime -- not an idle helper pool --
        // so the split is pinned rather than zeroed.
        // See Note [Paying for Determinism].
        n_main_helpers = fixed_main_helper_split();
      } else if (q_batches.size() == 1) {
        // A single minibatch cannot hide attention behind main work.  We'd want
        // to assign so as to minimize the total time of attention and main work,
        // but we don't have the machinery to estimate that, because attention
        // is all CPU, but main work has significant FPGA components that helper
        // threads just don't affect.
        // TODO Instead implement an interleaved `run_attn_and_main_help()` to
        // be run in all threads; this is optimal because attention and main
        // work never temporally overlap in single-minibatch mode (except maybe
        // rope-K overlapping ready attention, but that's small).
        n_main_helpers = fixed_main_helper_split();
      } else if (main_time_estimator.is_valid() && attn_time_estimator.is_valid()) {
        // Set n_main_helpers to equalize the time taken by main+helpers and
        // attention.  The estimators predict thread-time, so apportioning
        // threads in proportion to predicted thread-time equalizes wall time.
        size_t n_workers = 1 + app_pool().num_workers();  // main + helpers + attn
        float main_thread_time = main_time_estimator.predict_time();
        float attn_thread_time = attn_time_estimator.predict_time();
        float main_portion = main_thread_time / (main_thread_time + attn_thread_time);
        size_t n_main_workers =
            std::max<size_t>(1, std::round(main_portion * n_workers));
        n_main_helpers = n_main_workers - 1;
      }
      // Technically I think input_rmsnorm could be parallelized more than this, because
      // all the batches happen at once, but I don't think that's meaningful.
      size_t available_parallelism = 0;
      for (auto const& q_batch : q_batches) {
        available_parallelism = std::max(available_parallelism,
            plugin_state.available_main_parallelism(q_batch->items.size()));
      }
      n_main_helpers = std::max(min_main_helpers, n_main_helpers);
      n_main_helpers = std::min(max_main_helpers, n_main_helpers);
      n_main_helpers = std::min(available_parallelism, n_main_helpers);
      return n_main_helpers;
    }

    // Estimates the speeds of the `n_attn_workers` pool workers that will run
    // attention.  See Note [Attention workers are the last pool workers].
    // Returns worker_cumsum, with n_attn_workers elements, whose final element is ~1.0.
    std::vector<float> estimate_worker_speeds(size_t n_attn_workers) noexcept {
      thread_pool& tp = app_pool();
      tp.speedometer.update();
      std::vector<float> worker_cumsum(n_attn_workers);
      if (cfg.pay_for_determinism) {
        // Ignore worker speed autotuning for deterministic answers.
        // See Note [Paying for Determinism].
        std::iota(worker_cumsum.begin(), worker_cumsum.end(), 1);
        for (float& value : worker_cumsum)
          value /= worker_cumsum.size();
      } else {
        const std::vector<float> worker_speeds = tp.speedometer.estimate_speeds();
        std::vector<float> normalized_speeds(
            worker_speeds.end() - n_attn_workers, worker_speeds.end());
        float total =
            std::accumulate(normalized_speeds.begin(), normalized_speeds.end(), 0.0f);
        for (float& speed : normalized_speeds)
          speed /= total;
        std::partial_sum(
            normalized_speeds.begin(), normalized_speeds.end(), worker_cumsum.begin());
      }
      return worker_cumsum;
    }

    template <attention_geometry geometry>
    void begin_attention_job(batch* q_batch,
        attention_operation_descriptor const& operation,
        size_t worker_ix,
        size_t n_attn_workers) {
      self_attn_state.template begin_attention_job<geometry>(
          q_batch, operation, worker_ix, n_attn_workers);
    }

    template <attention_geometry geometry, size_t operation_ix, typename query_buffer_t>
    void prepare_attention_job(batch* q_batch, query_buffer_t& queries) {
      static_assert(attention_buffer_width<query_buffer_t> == geometry.query_width());
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      const bool prepare_hardware =
          hw_attention_phase(q_batch) == hw_attention_launch_phase::early;
      const bool operation_uses_hardware =
          cached_operation_uses_hw(operation.binding.operation);
      self_attn_state.template prepare_attention_job<geometry>(
          q_batch, operation, queries, operation_uses_hardware, prepare_hardware);
      if (prepare_hardware && operation_uses_hardware && !q_batch->hw_plan.empty())
        TRACE_EVENT_INSTANT("hwattention-detail", "early_hw_attn_prepare", "operation",
            operation.binding.operation.i, "layer", operation.binding.model_layer.i,
            "B", q_batch->items.size(), "min_b", init_hwattn_early_launch_min_b());
    }

    void wait_attention_job(batch* q_batch, size_t worker_ix) const {
      self_attn_state.wait_attention_job(q_batch, worker_ix);
    }

    template <attention_geometry geometry,
        typename query_buffer_t,
        typename query_channel_t,
        typename output_buffer_t,
        typename output_channel_t>
    uint64_t run_attention_job(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        query_channel_t& query_channel,
        output_buffer_t& output,
        output_channel_t& output_channel,
        size_t worker_ix,
        size_t n_attn_workers) {
      static_assert(attention_buffer_width<query_buffer_t> == geometry.query_width());
      static_assert(attention_buffer_width<output_buffer_t> == geometry.query_width());
      self_attn_state.template validate_operation<geometry>(operation);
      return self_attn_state.template run_attention_job<geometry>(q_batch, operation,
          queries, query_channel, output, output_channel, worker_ix, n_attn_workers,
          cached_operation_uses_hw(operation.binding.operation));
    }

    void finish_attention_job(batch* q_batch, size_t n_attn_workers) {
      self_attn_state.finish_attention_job(q_batch, n_attn_workers);
    }

    template <attention_geometry geometry,
        size_t operation_ix,
        typename query_buffer_t,
        typename query_channel_t,
        typename output_buffer_t,
        typename output_channel_t>
    uint64_t run_attention_job(batch* q_batch,
        query_buffer_t& queries,
        query_channel_t& query_channel,
        output_buffer_t& output,
        output_channel_t& output_channel,
        size_t worker_ix,
        size_t n_attn_workers) {
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      uint64_t elapsed = run_attention_job<geometry>(q_batch, operation, queries,
          query_channel, output, output_channel, worker_ix, n_attn_workers);
      elapsed -= hardware::system::rdtsc();
      finish_attention_job(q_batch, n_attn_workers);
      return elapsed + hardware::system::rdtsc();
    }

    void record_attention_time(uint64_t elapsed) {
      attn_time_estimator.record_time(elapsed);
    }

    // Geometry-specialized dynamic entry point.
    template <attention_geometry geometry, typename query_buffer_t>
    void prepare_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries) {
      static_assert(attention_buffer_width<query_buffer_t> == geometry.query_width());
      self_attn_state.template validate_operation<geometry>(operation);
      self_attn_state.template prepare_hw_attention<geometry>(q_batch, operation,
          queries, cached_operation_uses_hw(operation.binding.operation));
    }

    template <attention_geometry geometry,
        typename query_buffer_t,
        typename query_channel_t>
    void launch_hw_attention(batch* q_batch,
        attention_operation_descriptor const& operation,
        query_buffer_t& queries,
        query_channel_t& query_channel) {
      static_assert(attention_buffer_width<query_buffer_t> == geometry.query_width());
      self_attn_state.template validate_operation<geometry>(operation);
      self_attn_state.template launch_hw_attention<geometry>(q_batch, operation,
          queries, query_channel,
          cached_operation_uses_hw(operation.binding.operation));
    }

    template <attention_geometry geometry,
        size_t operation_ix,
        typename query_buffer_t,
        typename query_channel_t>
    void launch_hw_attention(
        batch* q_batch, query_buffer_t& queries, query_channel_t& query_channel) {
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      launch_hw_attention<geometry>(q_batch, operation, queries, query_channel);
    }

    // See Note [Early and late hardware attention launch].
    hw_attention_launch_phase hw_attention_phase(batch const* q_batch) const noexcept {
      return select_hw_attention_launch_phase(
          q_batch->items.size(), init_hwattn_early_launch_min_b());
    }

    template <attention_geometry geometry,
        size_t operation_ix,
        typename query_buffer_t,
        typename query_channel_t>
    void launch_early_hw_attention(
        batch* q_batch, query_buffer_t& queries, query_channel_t& query_channel) {
      if (hw_attention_phase(q_batch) != hw_attention_launch_phase::early) return;
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      const bool dispatches_hardware =
          cached_operation_uses_hw(operation.binding.operation) &&
          !q_batch->hw_plan.empty();
      launch_hw_attention<geometry, operation_ix>(q_batch, queries, query_channel);
      if (dispatches_hardware)
        TRACE_EVENT_INSTANT("hwattention-detail", "early_hw_attn", "operation",
            operation.binding.operation.i, "layer", operation.binding.model_layer.i,
            "B", q_batch->items.size(), "min_b", init_hwattn_early_launch_min_b());
    }

    template <attention_geometry geometry, size_t operation_ix, typename query_buffer_t>
    void prepare_late_hw_attention(batch* q_batch, query_buffer_t& queries) {
      if (hw_attention_phase(q_batch) != hw_attention_launch_phase::late) return;
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      const bool dispatches_hardware =
          cached_operation_uses_hw(operation.binding.operation) &&
          !q_batch->hw_plan.empty();
      prepare_hw_attention<geometry>(q_batch, operation, queries);
      if (dispatches_hardware)
        TRACE_EVENT_INSTANT("hwattention-detail", "late_hw_attn_prepare", "operation",
            operation.binding.operation.i, "layer", operation.binding.model_layer.i,
            "B", q_batch->items.size(), "min_b", init_hwattn_early_launch_min_b());
    }

    template <attention_geometry geometry,
        size_t operation_ix,
        typename query_buffer_t,
        typename query_channel_t>
    void launch_late_hw_attention(
        batch* q_batch, query_buffer_t& queries, query_channel_t& query_channel) {
      if (hw_attention_phase(q_batch) != hw_attention_launch_phase::late) return;
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      const bool dispatches_hardware =
          cached_operation_uses_hw(operation.binding.operation) &&
          !q_batch->hw_plan.empty();
      launch_hw_attention<geometry, operation_ix>(q_batch, queries, query_channel);
      if (dispatches_hardware)
        TRACE_EVENT_INSTANT("hwattention-detail", "late_hw_attn", "operation",
            operation.binding.operation.i, "layer", operation.binding.model_layer.i,
            "B", q_batch->items.size(), "min_b", init_hwattn_early_launch_min_b());
    }

    // Note [Attention workers are the last pool workers]
    // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    // The forward pass divides the app thread pool into main helpers and
    // attention workers.  By convention, attention worker `i` of
    // `n_attn_workers` always runs on pool worker
    // `num_workers() - n_attn_workers + i`, i.e., the attention workers
    // occupy the *last* `n_attn_workers` pool workers and the main helpers
    // the first `num_workers() - n_attn_workers`.
    //
    // This convention is load-bearing in four places, which is why whoever
    // launches the workers (the plugin, since it owns the split) must honor
    // it:
    // - `estimate_worker_speeds` reads the speedometer entries of the last
    //   `n_attn_workers` pool workers when weighting the attention plan, and
    //   `run_attention_job` reports observations back under the same indices.
    //   Misplacement doesn't break correctness, but silently mistunes the
    //   plan's load balance.
    // - Per-worker attention scratchpads are keyed by attention worker
    //   index, so two threads claiming the same index would race.
    // - The attention path stats (attn_stats.hpp) key their per-worker rows
    //   by pool worker through model_stats::pool_worker, which applies this
    //   formula, and fold the last `n_attn_workers` rows at the end of the
    //   forward.
    // - Generated plugins with an aligned lane domain assume that the helpers
    //   and attention workers fill the pool.  The lane count relies on it,
    //   and each attention worker computes the helper count as
    //   `num_workers() - n_attn_workers` to find its lane and its participant
    //   id on lane channels.  If the split leaves pool workers out, these
    //   values are wrong and the pass hangs or aborts.  So each generated
    //   `reset_channels` asserts that the helpers and attention workers
    //   fill the pool.  See Note [Aligned lane domain] in
    //   ingest/src/TronCpp.hs.

    // Assemble per-worker attention plans for `n_attn_workers` attention
    // workers, from the work estimates left in `attn_work` by
    // estimate_attention_work().  The plans are speed-weighted for the
    // specific pool workers that will run attention; see
    // Note [Attention workers are the last pool workers].
    template <attention_geometry... operation_geometries>
    void assemble_attention_plan(size_t n_attn_workers) {
      static_assert(valid_generated_attention_plan<operation_geometries...>());
      assemble_attention_plan_impl(n_attn_workers);
    }

    // Compatibility entry point for handwritten uniform plugins.
    void assemble_attention_plan(size_t n_attn_workers) {
      assemble_attention_plan_impl(n_attn_workers);
    }

    void assemble_attention_plan_impl(size_t n_attn_workers) {
      // Attention-plan allocations get their own malloc counter category;
      // finish_sw_plan below re-tags its subtree as kv_plan (innermost wins).
      alloc_cat_scope _(alloc_cat::attn_plan);
      TRACE_EVENT("model", "assemble attention plan");
      TRON_ASSERT(n_attn_workers >= 1, "attention needs at least one worker");
      TRON_ASSERT_LE(n_attn_workers, app_pool().num_workers());
      // Attention path stats: the split of this forward. Rows are keyed by
      // pool worker, and the fold at the end of the forward covers the last
      // n_attn_workers rows only.
      self_attn_state.stats->note_attn_workers(n_attn_workers);
      const size_t n_plans = attention_plan_profiles.size();
      const std::vector<float> worker_cumsum = estimate_worker_speeds(n_attn_workers);

      for (size_t b = 0; b < q_batches.size(); ++b) {
        batch* q_batch = q_batches[b].get();
        q_batch->plans.resize(n_plans);
        q_batch->hw_plan.clear();

        // Step 3. Offload to the hardware all the attention compute it will take.
        construct_hw_plan(q_batch);

        for (attention_plan_id plan_id : attention_plan_profiles.indices()) {
          attention_plan_profile const& profile = attention_plan_profiles[plan_id];
          const size_t operation_kv_heads = profile.geometry.kv.n_kv_heads;
          TRACE_EVENT("model", "assemble attention plan", "plan", plan_id.i, "window",
              profile.sliding_window_size, "minibatch", b);
          auto& plan_state = q_batch->plans[plan_id];
          plan_state.n_sections = std::vector<size_t>(operation_kv_heads, 0);
          plan_state.sections_left =
              std::vector<std::atomic_size_t>(operation_kv_heads);
          plan_state.ready_kv_plan.resize(n_attn_workers);
          plan_state.pending_kv_plan.resize(n_attn_workers);
          plan_state.work_estimate.assign(n_attn_workers, 0.0f);
          plan_state.kv_heads_to_join.assign(n_attn_workers, {});
          plan_state.join_workers.resize(operation_kv_heads);
          for (auto& m : plan_state.join_workers)
            m.clear();

          // Step 4. Extend the software attention plan to cover
          // all remaining pages.  Try to distribute total work among
          // workers in proportion to their speed.
          finish_sw_plan(q_batch, plan_state, attn_work.page_ixs[b][plan_id],
              attn_work.page_work[b][plan_id], attn_work.page_qrange[b][plan_id],
              worker_cumsum, operation_kv_heads);

          // Step 5. Update work estimates and plan workers to join tasks.
          for (size_t worker = 0; worker < n_attn_workers; ++worker)
            for (int pending : {0, 1}) {
              auto& plan =
                  pending ? plan_state.pending_kv_plan : plan_state.ready_kv_plan;
              for (auto& section : plan[worker]) {
                plan_state.work_estimate[worker] += section.work_estimate.work();
                plan_state.kv_heads_to_join[worker].insert(section.kv_head);
                plan_state.join_workers[section.kv_head].insert(worker);
              }
            }

          // Step 6. If any kv_head is not planned for any join
          // workers at all, we have to put it in.  This should only
          // ever happen if _all_ the attention work is on the hardware,
          // because every kv head has the same fate.  If this happens,
          // we just add it to all the workers, lacking any better idea.
          for (size_t kv_head = 0; kv_head < operation_kv_heads; ++kv_head) {
            if (plan_state.join_workers[kv_head].empty()) {
              for (size_t worker = 0; worker < n_attn_workers; ++worker) {
                plan_state.join_workers[kv_head].insert(worker);
                plan_state.kv_heads_to_join[worker].insert(kv_head);
              }
            }
          }
        }
      }
    }

    void select_relevant_pages(const std::vector<token_job_id>& items,
        std::array<std::vector<page_id>, 2>& batch_page_ixs,
        const std::vector<page_id>& ready_page_ixs,
        const std::vector<page_id>& pending_page_ixs,
        int sliding_window_size) {
      const size_t n_pages = ready_page_ixs.size() + pending_page_ixs.size();
      indexed_vector<page_id, uint16_t> page_rank(n_pages);  // page -> min rank
      for (int pending : {0, 1}) {
        auto& page_ixs = batch_page_ixs[pending];
        const auto& all_page_ixs = pending ? pending_page_ixs : ready_page_ixs;
        page_ixs.reserve(all_page_ixs.size());
        const token_range* range_hint =
            all_page_ixs.empty()
                ? nullptr
                : &query_mask->find_range(pages[all_page_ixs.front()]->at_offset(0));
        for (page_id page_ix : all_page_ixs) {
          const auto& page = *(pages[page_ix]);
          constexpr uint16_t sentinel = -1;
          static_assert(max_minibatch_size <= sentinel);
          page_rank[page_ix] = sentinel;
          // For sliding-window layers, drop pages whose latest k-position is
          // older than `sliding_window_size` for every visible item.
          bool window_ok =
              sliding_window_size >= self_attention<model>::illegal_sliding_window;
          uint32_t k_position_last = window_ok
                                         ? 0
                                         : token_positions[page.at_offset(0)] +
                                               static_cast<uint32_t>(page.count());
          // A page can span several mask ranges (the SW/HW boundary and
          // branch points fall inside pages), so rank it by the first item
          // that sees any of its ranges.
          range_hint = query_mask->for_each_range_run(page.at_offset(0), page.count(),
              *range_hint, [&](const token_range& range, size_t, size_t) {
                const size_t limit =
                    std::min(items.size(), static_cast<size_t>(page_rank[page_ix]));
                for (size_t token_rank = 0; token_rank < limit; ++token_rank) {
                  if (!range.visible(items[token_rank])) continue;
                  if (!window_ok) {
                    uint32_t q_position =
                        token_positions[token_jobs[items[token_rank]]];
                    if ((int)q_position - (int)k_position_last >= sliding_window_size)
                      continue;
                  }
                  page_rank[page_ix] = static_cast<uint16_t>(token_rank);
                  break;
                }
                return page_rank[page_ix] == 0;  // no earlier rank is possible
              });
          if (page_rank[page_ix] != sentinel) page_ixs.push_back(page_ix);
        }
        std::stable_sort(page_ixs.begin(), page_ixs.end(),
            [&](page_id a, page_id b) { return page_rank[a] < page_rank[b]; });
      }
    }

    void estimate_work(const std::vector<token_job_id>& items,
        const std::array<std::vector<page_id>, 2>& batch_page_ixs,
        std::array<std::vector<work_estimate_t>, 2>& page_work,
        std::array<std::vector<std::pair<uint32_t, uint32_t>>, 2>& page_qrange,
        work_estimate_t& work_total,
        int sliding_window_size,
        size_t operation_query_heads,
        size_t operation_kv_heads,
        bool use_hw) {
      const bool full_causal =
          sliding_window_size >= self_attention<model>::illegal_sliding_window;
      // Visibility is constant within one mask range (the per-offset walk this
      // replaces only re-queried the mask at tok_hi boundaries), so a page's
      // offsets are segmented into runs sharing a range once, and each item's
      // dot-product count over a run is a multiplication instead of a walk.
      struct range_run {
        const token_range* range;
        size_t begin;
        size_t end;
      };
      std::vector<range_run> runs;
      // The ready and pending page partitions get independent work tallies;
      // see Note [Ready versus pending attention work].
      for (int pending : {0, 1}) {
        const auto& page_ixs = batch_page_ixs[pending];
        page_work[pending].resize(page_ixs.size());
        page_qrange[pending].assign(page_ixs.size(), {0, 0});
        const token_range* range_hint =
            page_ixs.empty()
                ? nullptr
                : &query_mask->find_range(pages[page_ixs.front()]->at_offset(0));
        // Tally per-page work for every relevant page in this partition.
        for (size_t p = 0; p < page_ixs.size(); ++p) {
          const auto& page = *(pages[page_ixs[p]]);
          uint32_t k_position_base = token_positions[page.at_offset(0)];
          runs.clear();
          const token_range* entry_range =
              &query_mask->find_range(page.at_offset(0), *range_hint);
          size_t run_begin = 0;
          // Segment the page's offsets into runs sharing one mask range,
          // closing a run whenever a KV token crosses the range's tok_hi.
          for (size_t offset = 1; offset < page.count(); offset++) {
            token_id kv_idx = page.at_offset(offset);
            if (kv_idx >= entry_range->tok_hi) {
              runs.push_back({entry_range, run_begin, offset});
              entry_range = &query_mask->find_range(kv_idx, *entry_range);
              run_begin = offset;
            }
          }
          runs.push_back({entry_range, run_begin, page.count()});
          range_hint = entry_range;
          // Accumulate each minibatch item's dot products against this page.
          size_t q_lo = SIZE_MAX, q_hi = 0;
          for (size_t ix = 0; ix < items.size(); ++ix) {
            bool has_sw_work = false;
            const int q_position =
                full_causal ? 0 : (int)token_positions[token_jobs[items[ix]]];
            // One visibility check per run covers all its offsets; the item's
            // count over a contributing run is a span-length multiplication.
            for (const range_run& run : runs) {
              size_t begin = run.begin;
              bool contributes_to_sw = use_hw ? run.range->sw_required(items[ix])
                                              : run.range->visible(items[ix]);
              if (!full_causal) {
                // Offsets at or below q_position - k_position_base -
                // sliding_window_size fall outside the window.
                const int first_in_window =
                    q_position - (int)k_position_base - sliding_window_size + 1;
                begin = std::max(begin, (size_t)std::max(first_in_window, 0));
                contributes_to_sw = run.range->visible(items[ix]);
              }
              if (!contributes_to_sw || begin >= run.end) continue;
              page_work[pending][p].k_dot_products +=
                  operation_query_heads * (run.end - begin);
              has_sw_work = true;
            }
            if (has_sw_work) {
              page_work[pending][p].scaled_vs += operation_kv_heads;
              q_lo = std::min(q_lo, ix);
              q_hi = ix + 1;
            }
          }
          if (page_work[pending][p].scaled_vs == 0) continue;
          page_qrange[pending][p] = {
              static_cast<uint32_t>(q_lo), static_cast<uint32_t>(q_hi)};
          page_work[pending][p].kv_heads += operation_kv_heads;
          work_total += page_work[pending][p];
        }
      }
    }

    void construct_hw_plan(batch* q_batch) {
      // This is a bit redundant. We *shouldn't* populate hw_plan_entries to begin
      // with if hw-attn is disabled (see guard in full::forward()), then the
      // hw_plan_entries.empty() check below would bail. This is just defensive.
      if (!self_attn_state.hw_attn_eligible || !use_hw_attn_for_this_model()) return;
      if (hw_plan_entries.empty()) return;

      TRACE_EVENT(
          "hwattention", "construct_hw_plan", "entries", hw_plan_entries.size());

      std::vector<hw_pass> passes;
      size_t n_hw_scratchpads = 0;
      const size_t physical_shards_per_pass =
          hardware::max_shards_for_emem(n_heads, head_size, hardware::shard_tokens);
      // Unreachable: use_hw_attn_for_this_model() (checked above and gating
      // configure_hw_attention's hardware KV-slot mask) already returns false when EMEM
      // cannot hold a shard, so no HW ranges would be marked. Assert rather than
      // silently returning an empty plan, which would leave HW-offloaded token
      // ranges computed by neither the HW nor the SW (sw_required-only) path.
      TRON_ASSERT(physical_shards_per_pass > 0,
          "construct_hw_plan: max_shards_for_emem returned 0 for n_heads={} "
          "head_size={} shard_tokens={} but the hardware KV-slot mask was set; "
          "use_hw_attn_for_this_model() should have forced SW attention",
          n_heads, head_size, hardware::shard_tokens);
      const bool compound_split_enabled = [&] {
        if (const char* env = std::getenv("TRON_HWATTN_COMPOUND_SPLIT"))
          return std::atol(env) != 0;
        return cfg.id.starts_with("ingested-");
      }();
      // TRON_HWATTN_COMPOUND_SPLIT is intentionally ignored: compound passes can
      // strand the final one or two result words in the current FPGA implementation.
      (void)compound_split_enabled;

      // Per-device: head tiling raises the cap to the physical command limit on cards
      // whose bitfile supports it (PosDevice::attn_tiling_enabled).
      const size_t tiled_shards_per_pass = std::max(
          physical_shards_per_pass, hardware::max_shards_for_emem_tiled(n_heads,
                                        n_heads / n_kv_heads, hardware::shard_tokens));

      struct dev_group {
        ::PosDevice* dev;
        std::vector<hardware::shard const*> shards;
      };
      struct pass_seed {
        ::PosDevice* dev;
        std::vector<hardware::shard const*> shards;
        size_t length;
        std::vector<hw_query> queries;
      };
      std::vector<pass_seed> seeds;

      auto same_shards = [](std::vector<hardware::shard const*> const& a,
                             std::vector<hardware::shard const*> const& b) {
        return a.size() == b.size() && std::equal(a.begin(), a.end(), b.begin());
      };

      auto reachable_shard_count = [](std::vector<hardware::shard const*> const& shards,
                                       size_t last_hw_token_pos) {
        size_t count = 0;
        while (count < shards.size() && last_hw_token_pos >= shards[count]->base_tok_ix)
          ++count;
        return count;
      };

      for (const auto& entry : hw_plan_entries) {
        // Use the mask boundary captured during descent. Re-querying
        // count_complete_gofs() here would race with async GOF DMA
        // completions and could push the boundary past the mask's HW/SW
        // transition, violating the no-overlap invariant.
        // entry.last_token_ix is a flattened-forward token_id; hardware shards
        // are keyed by absolute sequence position.
        size_t last_token_pos = token_positions[entry.last_token_ix];
        if (last_token_pos < hw_attn_engagement_point()) continue;

        std::vector<hw_query> queries;
        for (size_t i = 0; i < q_batch->items.size(); ++i) {
          token_job_id job_ix = q_batch->items[i];
          if (entry.query_mask.contains(job_ix.i)) {
            size_t query_pos = token_positions[token_jobs[job_ix]];
            if (query_pos < hw_attn_engagement_point()) continue;
            queries.push_back(hw_query{job_ix, std::min(query_pos, last_token_pos), i});
          }
        }
        if (queries.empty()) continue;
        // Note [HW Attention and prompt queries]
        // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        // A hw_plan_entry names one HBM-resident K/V boundary. Multiple prompt
        // queries can share that prefix; any newer per-query causal tail remains
        // SW work in later ranges. Compatible entries are coalesced below so one
        // prepare can carry several Qs whose metadata token positions are
        // identical or sequential.

        std::vector<dev_group> by_device;
        for (auto* sh : entry.shard_stack) {
          auto it = std::find_if(by_device.begin(), by_device.end(),
              [&](const dev_group& g) { return g.dev == sh->dev; });
          if (it != by_device.end())
            it->shards.push_back(sh);
          else
            by_device.push_back({sh->dev, {sh}});
        }

        for (auto& [dev, shards] : by_device) {
          const size_t max_shards_per_pass = dev->attn_tiling_enabled
                                                 ? tiled_shards_per_pass
                                                 : physical_shards_per_pass;
          for (size_t i = 0; i < shards.size(); i += max_shards_per_pass) {
            size_t end = std::min(i + max_shards_per_pass, shards.size());
            std::vector<hardware::shard const*> chunk(
                shards.begin() + i, shards.begin() + end);
            std::vector<hw_query> chunk_queries;
            for (auto const& query : queries) {
              if (query.last_hw_token_pos >= chunk.front()->base_tok_ix)
                chunk_queries.push_back(query);
            }
            if (chunk_queries.empty()) continue;

            auto seed = std::find_if(seeds.begin(), seeds.end(), [&](auto const& s) {
              return s.dev == dev && same_shards(s.shards, chunk);
            });
            if (seed == seeds.end()) {
              seeds.push_back(pass_seed{dev, std::move(chunk),
                  (end - i) * hardware::shard_tokens, std::move(chunk_queries)});
            } else {
              seed->queries.insert(
                  seed->queries.end(), chunk_queries.begin(), chunk_queries.end());
            }
          }
        }
      }

      for (auto& seed : seeds) {
        std::sort(seed.queries.begin(), seed.queries.end(),
            [](hw_query const& a, hw_query const& b) {
              if (a.job_ix.i != b.job_ix.i) return a.job_ix.i < b.job_ix.i;
              return a.last_hw_token_pos < b.last_hw_token_pos;
            });
        auto out = seed.queries.begin();
        for (auto it = seed.queries.begin(); it != seed.queries.end();) {
          hw_query query = *it++;
          while (it != seed.queries.end() && it->job_ix.i == query.job_ix.i) {
            query.last_hw_token_pos =
                std::max(query.last_hw_token_pos, it->last_hw_token_pos);
            ++it;
          }
          *out++ = query;
        }
        seed.queries.erase(out, seed.queries.end());

        std::sort(seed.queries.begin(), seed.queries.end(),
            [](hw_query const& a, hw_query const& b) {
              if (a.last_hw_token_pos != b.last_hw_token_pos)
                return a.last_hw_token_pos < b.last_hw_token_pos;
              return a.job_ix.i < b.job_ix.i;
            });

        // This is the logical Q batch cap from activation and metadata space.
        // EMEM caps the physical ACTproc inside each subcommand; the worker
        // keeps B as activ_cnt and programs activ2proc to the EMEM-safe divisor.
        size_t max_queries_per_pass =
            seed.dev ? hardware::maximum_hwattn_batch_size(
                           seed.dev, n_heads * hardware::HW_BAKED_HEAD_SIZE)
                     : hardware::MAX_B;
        max_queries_per_pass = std::max<size_t>(1, max_queries_per_pass);

        // Mirrors the worker's head-tiling engage rule: a span past the untiled
        // EMEM cap with a legal head tile becomes ONE physical command, so the
        // unpack/join side must expect a single result block per Q.
        auto physical_subpasses_for = [&](size_t covered_shards,
                                          ::PosDevice const* dev) {
          return hardware::hwattn_plan_cmd_shape(n_heads, n_heads / n_kv_heads,
              head_size, covered_shards, hardware::shard_tokens,
              covered_shards * hardware::shard_tokens,
              dev != nullptr && dev->attn_tiling_enabled)
              .subcmds;
        };

        auto query_physical_subpasses = [&](hw_query const& query) {
          TRON_ASSERT(query.last_hw_token_pos >= hw_attn_engagement_point(),
              "HW attention query {} has tok_ix {} below minimum {}", query.job_ix.i,
              query.last_hw_token_pos, hw_attn_engagement_point());
          size_t covered_shards =
              reachable_shard_count(seed.shards, query.last_hw_token_pos);
          TRON_ASSERT(covered_shards > 0,
              "HW attention query {} for token {} has no reachable shards",
              query.job_ix.i, query.last_hw_token_pos);
          return physical_subpasses_for(covered_shards, seed.dev);
        };

        for (size_t q = 0; q < seed.queries.size();) {
          size_t batch_subpasses = query_physical_subpasses(seed.queries[q]);
          size_t q_end = q + 1;
          while (q_end < seed.queries.size() && (q_end - q) < max_queries_per_pass) {
            size_t prev_pos = seed.queries[q_end - 1].last_hw_token_pos;
            size_t next_pos = seed.queries[q_end].last_hw_token_pos;
            if (next_pos != prev_pos && next_pos != prev_pos + 1) break;
            // The worker emits one metadata word per Q for every physical
            // subcommand. A shorter Q must not be carried into a subcommand
            // whose first shard starts after that Q's token extent.
            if (query_physical_subpasses(seed.queries[q_end]) != batch_subpasses) break;
            ++q_end;
          }

          hw_pass pass;
          pass.dev = seed.dev;
          pass.queries.assign(seed.queries.begin() + q, seed.queries.begin() + q_end);
          pass.last_hw_token_pos = pass.queries.back().last_hw_token_pos;
          size_t covered_shards =
              reachable_shard_count(seed.shards, pass.last_hw_token_pos);
          TRON_ASSERT(covered_shards > 0,
              "HW attention pass for token {} has no reachable shards",
              pass.last_hw_token_pos);
          pass.shards.assign(seed.shards.begin(), seed.shards.begin() + covered_shards);
          pass.length = covered_shards * hardware::shard_tokens;
          pass.scratchpad_ix = hw_scratchpad_id(n_hw_scratchpads++);
          pass.physical_subpasses =
              physical_subpasses_for(pass.shards.size(), seed.dev);
          passes.push_back(std::move(pass));
          q = q_end;
        }
      }

      if (passes.empty()) return;

      // grow our hw_attn scratchpad space as needed in each pass through construction
      while (self_attn_state.hw_attn.size() < n_hw_scratchpads)
        self_attn_state.hw_attn.emplace_back();

      q_batch->hw_plan.set_passes(std::move(passes), q_batch->items,
          [&](hw_pass const& pass, hw_query const& query) {
            self_attn_state.hw_attn_results_at(pass.scratchpad_ix)
                .prepare_raw_result(query.job_ix);
          });
      if (self_attn_state.stats->enabled) {
        // Attention path stats: the token jobs of this minibatch with at least
        // one FPGA pass, read from the same index the join uses.
        for (size_t i = 0; i < q_batch->items.size(); ++i) {
          if (!q_batch->hw_plan.by_job[i].devices.empty()) {
            self_attn_state.stats->note_fpga_query(q_batch->items[i].i);
          }
        }
      }
    }

    // Distribute work among workers according to their speed.
    // This simply uses worker_cumsum and work_cumsum to detect worker boundaries.
    // Specifically, `worker_cumsum[worker_ix]` is treated as a target
    // for the proportion of all work to be assigned to workers <=
    // `worker_ix`, and `work_cumsum` is the running total of all work
    // assigned so far.
    //
    // There are two types of section boundary: Worker and KV head. For example:
    //  | worker 0 |       worker 1      |   worker 2   |  worker 3 |  4 Workers
    //  +----------+---+--------------+--+-----------+--+-----------+  <-- worker
    //  |          /   |              |   \          |   \          |  7 Sections
    //  +---------+----+--------------+----+---------+----+---------+  <-- page_center
    //  | p0 | p1 | p2 | p0 | p1 | p2 | p0 | p1 | p2 | p0 | p1 | p2 |  3 Pages each
    //  |     ready    |   pending    |     ready    |   pending    |  Ready vs Pending
    //  |            kv 0             |             kv 1            |  2 KV heads
    void finish_sw_plan(batch* q_batch,
        typename batch::attention_plan& plan_state,
        const std::array<std::vector<page_id>, 2>& batch_page_ixs,
        const std::array<std::vector<work_estimate_t>, 2>& page_work,
        const std::array<std::vector<std::pair<uint32_t, uint32_t>>, 2>& page_qrange,
        const std::vector<float>& worker_cumsum,
        size_t operation_kv_heads) {
      // KV paging dominates attention planning; count it as its own category.
      alloc_cat_scope _(alloc_cat::kv_plan);
      size_t worker = 0;
      size_t work_cumsum = 0;
      size_t total_work = 0;
      for (int pending : {0, 1}) {
        const auto& ixs = batch_page_ixs[pending];
        for (size_t p = 0; p < ixs.size(); ++p)
          total_work += page_work[pending][p].work();
      }
      // All attention is on HW: no SW pages to distribute. Step 6
      // (in the caller) fills join_workers by broadcasting every
      // kv_head to every worker. Returning here avoids a div-by-zero
      // on page_center below.
      if (total_work == 0) return;

      TRON_ASSERT(std::abs(worker_cumsum.back() - 1.0f) < 1e-4,
          "worker_cumsum not normalized: total = {}", worker_cumsum.back());
      if (total_work == 0) return;
      // Account for work assigned to this worker previously.
      work_cumsum += plan_state.ready_kv_plan.work_estimate(0).work();
      work_cumsum += plan_state.pending_kv_plan.work_estimate(0).work();
      for (size_t kv_head = 0; kv_head < operation_kv_heads; ++kv_head) {
        for (int pending : {0, 1}) {
          const auto& page_ixs = batch_page_ixs[pending];
          auto& plan = pending ? plan_state.pending_kv_plan : plan_state.ready_kv_plan;
          for (size_t p = 0; p < page_ixs.size(); ++p) {
            work_estimate_t on_this_page = page_work[pending][p] / operation_kv_heads;
            // Decide whether to move on to the next worker by asking:
            // in which worker's interval does the page center land?
            const float page_center =
                (work_cumsum + 0.5f * on_this_page.work()) / total_work;
            if (worker_cumsum[worker] < page_center &&
                worker + 1 < worker_cumsum.size()) {
              ++worker;
              work_cumsum += plan_state.ready_kv_plan.work_estimate(worker).work();
              work_cumsum += plan_state.pending_kv_plan.work_estimate(worker).work();
            }
            if (plan.assign_page(worker, kv_head, page_ixs[p], on_this_page,
                    page_qrange[pending][p].first, page_qrange[pending][p].second)) {
              plan_state.n_sections[kv_head]++;
            }
            work_cumsum += on_this_page.work();
          }
        }
      }
      TRON_ASSERT_EQ(work_cumsum, total_work);
      split_sections_by_query(
          q_batch, plan_state, worker_cumsum, init_attn_section_split_cap());
    }

    // Parallelize single-page sections by query in both Ready and Pending phases.
    //
    // Hardware offload and sliding windows can leave too few software pages
    // to keep workers busy. Assign disjoint query ranges from a page to
    // different workers, preserving each query's full-page reduction. Split
    // only when there are at least two workers per productive (page, KV head)
    // task and enough relevant queries to amortize the extra section overhead.
    //
    // Place pieces by predicted finish time, accounting for worker load and
    // speed, relevant query count, and fixed setup/join costs per section.
    // Require a meaningful predicted gain to cover unmodeled worker arrival
    // skew, and prefer fewer pieces when their finish time is near the best.
    void split_sections_by_query(batch* q_batch,
        typename batch::attention_plan& plan_state,
        const std::vector<float>& worker_cumsum,
        size_t cap) {
      const size_t n_workers = plan_state.ready_kv_plan.size();
      const size_t n_q = q_batch->items.size();
      constexpr int64_t split_min_queries = 32;
      cap = std::min({cap, n_workers, max_attn_section_split});
      if (cap < 2 || n_q < static_cast<size_t>(split_min_queries)) return;
      TRON_ASSERT_EQ(worker_cumsum.size(), n_workers);
      TRON_ASSERT_EQ(plan_state.pending_kv_plan.size(), n_workers);
      // Charge a conservative 20 query units per section for page setup
      // and the additional bookkeeping and joins introduced by splitting.
      constexpr int64_t fixed_cost = 20;
      auto section_cost = [&](const kv_section& s) {
        return s.work_estimate.work() == 0 ? int64_t{0}
                                           : fixed_cost + s.work_estimate.work();
      };
      struct candidate {
        size_t worker;
        size_t ix;
        size_t span;
      };
      std::vector<candidate> cands;
      std::vector<int64_t> base_load(n_workers), load(n_workers);
      std::vector<double> inverse_speed(n_workers);
      for (size_t w = 0; w < n_workers; ++w) {
        const float speed = worker_cumsum[w] - (w == 0 ? 0.0f : worker_cumsum[w - 1]);
        TRON_ASSERT(std::isfinite(speed) && speed > 0,
            "invalid attention worker speed {}", speed);
        inverse_speed[w] = 1.0 / speed;
      }
      std::vector<std::pair<size_t, kv_section>> placed;
      for (int pending : {0, 1}) {
        auto& plan = pending ? plan_state.pending_kv_plan : plan_state.ready_kv_plan;
        // Ready sections run before pending ones on the same worker, so the
        // pending phase starts behind both.
        for (size_t w = 0; w < n_workers; ++w) {
          base_load[w] = 0;
          for (const kv_section& s : plan_state.ready_kv_plan[w])
            base_load[w] += section_cost(s);
          if (pending)
            for (const kv_section& s : plan_state.pending_kv_plan[w])
              base_load[w] += section_cost(s);
        }
        cands.clear();
        size_t page_tasks = 0;
        for (size_t w = 0; w < n_workers; ++w) {
          auto& worker_plan = plan.mutable_worker_plan(w);
          for (size_t i = 0; i < worker_plan.size(); ++i) {
            const kv_section& s = worker_plan[i];
            if (s.work_estimate.work() > 0) page_tasks += s.page_ixs.size();
            if (s.page_ixs.size() != 1 || s.work_estimate.scaled_vs < split_min_queries)
              continue;
            const size_t q_end = std::min(s.q_end, n_q);
            if (q_end <= s.q_begin + 1) continue;
            cands.push_back({w, i, q_end - s.q_begin});
          }
        }
        if (cands.empty() || page_tasks > n_workers / 2) continue;
        // Use the same partitioning and placement for simulation and execution.
        // Proportional boundaries make exactly k nonempty pieces even when the
        // query count is not divisible by k. Retain rounding remainders in the
        // work estimates; every piece still visits all of the original pages.
        auto place_splits = [&](size_t ways, auto&& emit) {
          load = base_load;
          for (const candidate& c : cands) {
            const kv_section& s = plan.mutable_worker_plan(c.worker)[c.ix];
            const size_t k = std::min(ways, c.span);
            if (k < 2) continue;
            const size_t q_begin = s.q_begin;
            const work_estimate_t work = s.work_estimate;
            load[c.worker] -= section_cost(s);
            for (size_t i = 0; i < k; ++i) {
              const size_t begin = c.span * i / k;
              const size_t end = c.span * (i + 1) / k;
              auto share = [&](int64_t total) {
                return total * static_cast<int64_t>(end) /
                           static_cast<int64_t>(c.span) -
                       total * static_cast<int64_t>(begin) /
                           static_cast<int64_t>(c.span);
              };
              const work_estimate_t piece_work{
                  share(work.k_dot_products), share(work.scaled_vs), work.kv_heads};
              const int64_t cost = fixed_cost + piece_work.work();
              // Keep the first piece on the original worker; moving the whole
              // section would discard the page assignment's locality choice.
              size_t target = c.worker;
              if (i > 0) {
                target = 0;
                for (size_t w = 1; w < n_workers; ++w)
                  if ((load[w] + cost) * inverse_speed[w] <
                      (load[target] + cost) * inverse_speed[target])
                    target = w;
              }
              load[target] += cost;
              emit(c, i, target, q_begin + begin, q_begin + end, piece_work);
            }
          }
          double makespan = 0;
          for (size_t w = 0; w < n_workers; ++w)
            makespan = std::max(makespan, load[w] * inverse_speed[w]);
          return makespan;
        };
        auto ignore_piece = [](const auto&...) {};
        std::array<double, max_attn_section_split> makespans;
        makespans[0] = place_splits(1, ignore_piece);
        double best_makespan = makespans[0];
        for (size_t ways = 2; ways <= cap; ++ways) {
          makespans[ways - 1] = place_splits(ways, ignore_piece);
          best_makespan = std::min(best_makespan, makespans[ways - 1]);
        }
        // Both conditions apply to the chosen split, not just the optimum:
        // save at least 10% over leaving the phase unsplit, and use the fewest
        // pieces within 3% of the best predicted finish time.
        constexpr double min_gain = 0.10;
        constexpr double near_best = 0.03;
        const double limit =
            std::min(makespans[0] * (1 - min_gain), best_makespan * (1 + near_best));
        size_t best_ways = 2;
        while (best_ways <= cap && makespans[best_ways - 1] > limit)
          ++best_ways;
        if (best_ways > cap) continue;
        // Apply what was simulated. Each original section keeps the first
        // piece; the rest are appended after the loop so the references
        // above stay valid.
        placed.clear();
        place_splits(best_ways, [&](const candidate& c, size_t i, size_t target,
                                    size_t begin, size_t end, work_estimate_t work) {
          kv_section& original = plan.mutable_worker_plan(c.worker)[c.ix];
          if (i == 0) {
            original.q_begin = begin;
            original.q_end = end;
            original.work_estimate = work;
          } else {
            kv_section piece = original;
            piece.q_begin = begin;
            piece.q_end = end;
            piece.work_estimate = work;
            placed.emplace_back(target, std::move(piece));
            plan_state.n_sections[original.kv_head]++;
          }
        });
        for (auto& [target, piece] : placed)
          plan.mutable_worker_plan(target).push_back(std::move(piece));
      }
    }

    // Note [Shared block save]
    // ~~~~~~~~~~~~~~~~~~~~~~~~
    // save_k stores the K rows of every token of the minibatch once per
    // (layer, pass). With the VNNI K layout (VNNI = Vector Neural Network
    // Instructions, Note [K VNNI storage] in kv_cache.hpp) that store is the
    // main thread's largest serial piece of work in a prefill layer. The
    // measurement of 2026-09-14 on delphi-3bda (qwen3-4b, 8 users, prompt
    // 1024, 128 tokens of each user per pass) gave 0.86 ms per layer, 105 ns
    // per (token, KV head) row. The attention workers' pending sections wait
    // behind it. Two things shorten it:
    //   1. Block save (store_block in h/tron/tensor/k_vnni.hpp, page::set_k_block):
    //      a run of the pass's tokens that fills (part of) one 16-token block of
    //      a page is transposed in registers. It is then written as whole 64-byte
    //      lines, instead of one 4-byte scatter per (token, dimension pair, line).
    //      Chosen per run in store_k_block.
    //   2. Sharing with the main helpers: in generated plugins the helpers
    //      are idle while main runs save_k. Their next kernel waits for the
    //      attention output. So the generated run_main_help calls save_k at
    //      the same statement position, with the helper's worker_ix. One
    //      function serves both sides: worker_ix 0 is main, 1 .. n_workers - 1
    //      are the helpers. Every thread then claims work units (runs of
    //      consecutive items inside one 16-token block, see the protocol
    //      below) until none is left. n_workers == 1 never shares (the
    //      handwritten plugins, and the unit tests except the shared-save case
    //      of t_llama_unit).
    // The window protocol (fields in batch::k_store_window, common.hpp):
    //   - both sides decide with k_store_shared(). A window exists only
    //     when it says yes. So a helper never waits for a window main does
    //     not open. (A pass with at most 16 items, such as a decode step, or
    //     more than 128 workers is not shared.)
    //   - main cuts the item list into work units (unit_start[]). A unit is a
    //     run of consecutive items in one 16-token block of one page with the
    //     same token_jobs_do_kv value. Items of one block that are not
    //     consecutive fall into several units. Their writers use masked
    //     stores on disjoint token lanes. So two threads may write one block
    //     without conflict. When a run fills the block, the block gets one
    //     full-line store per pair row. Main then zeroes the claim counter
    //     and `finished`. Next it increments `opened` (release). A helper's
    //     W-th call waits for `opened` >= W
    //     (acquire). So window W of a pass is the W-th shared save_k of that
    //     pass on both sides.
    //   - every thread claims units with fetch_add on `next_unit`. It stores
    //     the rows of each unit it claims. A unit index is assigned once. So
    //     a thread that leaves the claim loop has stored every unit it took.
    //   - a helper increments `finished` (release) when its claim loop ends.
    //     Main returns only when `finished` == n_workers - 1 (acquire). Four
    //     things follow once main returns. Every unit is stored. No helper is
    //     inside a window main has left. The counters are main's to reset.
    //     Every row store happens-before the downstream latch count_down
    //     below.
    //   - the per-token completion marks and GOF credits stay on main, after
    //     the join, in q_batch->items order, one token at a time.
    // The rows a helper reads (ks) are ready for two reasons. Main waited for
    // every token's K channel before calling save_k (the generated code). The
    // channel phase cannot advance while main is inside save_k. A helper can
    // reach its save_k call without main's help. Nothing blocks between its
    // K/Q rope kernel and this statement. So main's join cannot deadlock. A
    // join that does not complete within about two minutes
    // (k_join_timeout_s after the first clock read) aborts with the
    // counters in the message.

    static constexpr size_t k_store_block = k_vnni::BLOCK_TOKENS_16;
    // A run of this length is stored row by row (set_k_row), not as a block.
    static constexpr size_t k_scatter_run_len = 1;
    // The join watchdog of Note [Shared block save]: main reads the clock once
    // every k_join_clock_spins pause loops. It aborts k_join_timeout_s seconds
    // after the first clock read.
    static constexpr uint64_t k_join_clock_spins = 1048576;  // 2^20
    static_assert((k_join_clock_spins & (k_join_clock_spins - 1)) == 0,
        "the spin count is a power of two: the check below masks with it");
    static constexpr int k_join_timeout_s = 120;

    // Whether the K store of this minibatch is shared with the helpers. The
    // answer is the same on the main thread and on every helper.
    template <attention_geometry geometry>
    bool k_store_shared(batch* q_batch, size_t n_workers) const noexcept {
      if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
        return false;
      } else {
        return n_workers > 1 &&
               n_workers <= q_batch->k_store_window.helper_windows.size() &&
               q_batch->items.size() > k_store_block;
      }
    }

    // Cut the minibatch's items into the work units of Note [Shared block save].
    // Only main calls this, before it opens the window.
    void k_store_cut_units(batch* q_batch) noexcept {
      auto& w = q_batch->k_store_window;
      auto const& self = *this;
      const size_t n_items = q_batch->items.size();
      TRON_ASSERT(n_items + 1 <= w.unit_start.size(),
          "save_k: {} items exceed the K store window's unit table", n_items);
      uint32_t n_units = 0;
      const page* run_page = nullptr;
      size_t run_block = 0;
      bool run_kv = false;
      for (size_t t = 0; t < n_items; ++t) {
        const token_job_id ix = q_batch->items[t];
        const bool kv = self.token_jobs_do_kv[ix] != 0;
        const page* pg = kv ? &page_of(token_jobs[ix]) : nullptr;
        const size_t block =
            kv ? static_cast<size_t>(pg->offset_in_page(token_jobs[ix])) / k_store_block
               : 0;
        if (t == 0 || kv != run_kv || pg != run_page || block != run_block) {
          w.unit_start[n_units++] = static_cast<uint32_t>(t);
          run_kv = kv;
          run_page = pg;
          run_block = block;
        }
      }
      w.unit_start[n_units] = static_cast<uint32_t>(n_items);
      w.n_units = n_units;
    }

    // Store the K rows (every KV head) of the tokens items[task_begin,
    // task_end) of q_batch into slot `slot`. VNNI slots: consecutive items
    // that fall into the same 16-token block of the same page are stored as
    // one block (set_k_block). A run of one token is stored with set_k_row
    // (scatter). Row-major slots: one row store per token and KV head
    // (page::k(...).set). Marks and credits are not touched here. save_k_impl
    // does them after every store is done.
    template <attention_geometry geometry, typename kv_buffer_t>
    void store_k_block(batch* q_batch,
        kv_slot_id slot,
        kv_buffer_t& ks,
        size_t task_begin,
        size_t task_end) noexcept {
      auto const& self = *this;
      auto row_of = [&](token_job_id ix, size_t kv_head) {
        return slice<geometry.kv.head_size>()(
            ks[ix].as_view(), kv_head * geometry.kv.head_size);
      };
      if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
        for (size_t t = task_begin; t < task_end; ++t) {
          token_job_id ix = q_batch->items[t];
          if (!self.token_jobs_do_kv[ix]) continue;
          token_id tok_ix = token_jobs[ix];
          page& pg = page_of(tok_ix);
          int j = pg.offset_in_page(tok_ix);
          for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {
            pg.template k<geometry.kv>(slot, kv_head, j).set(row_of(ix, kv_head));
          }
        }
      } else {
        using kv_elem_t = std::remove_cv_t<
            std::remove_pointer_t<decltype(row_of(token_job_id{0}, 0).data)>>;
        constexpr bool rows_are_bf16 = std::is_same_v<kv_elem_t, bf16>;
        // A bf16 K buffer is read in place. Any other activation type is
        // converted to bf16 on the stack first, as the row-major store does
        // in place.
        alignas(64) bf16 conv[k_store_block][geometry.kv.head_size];
        size_t t = task_begin;
        while (t < task_end) {
          const token_job_id ix0 = q_batch->items[t];
          if (!self.token_jobs_do_kv[ix0]) {
            ++t;
            continue;
          }
          page& pg = page_of(token_jobs[ix0]);
          const size_t c =
              static_cast<size_t>(pg.offset_in_page(token_jobs[ix0])) / k_store_block;
          // The run: consecutive items in block c of this page (tokens
          // without KV work in between are skipped and do not end the run).
          token_job_id run_ix[k_store_block];
          uint8_t run_t[k_store_block];
          size_t n = 0;
          __mmask16 present = 0;
          for (; t < task_end && n < k_store_block; ++t) {
            const token_job_id ix = q_batch->items[t];
            if (!self.token_jobs_do_kv[ix]) continue;
            const token_id tok_ix = token_jobs[ix];
            if (&page_of(tok_ix) != &pg) break;
            const size_t j = static_cast<size_t>(pg.offset_in_page(tok_ix));
            if (j / k_store_block != c) break;
            const __mmask16 bit = __mmask16(1u << (j % k_store_block));
            if (present & bit) break;  // the same offset twice: not a run
            run_ix[n] = ix;
            run_t[n] = static_cast<uint8_t>(j % k_store_block);
            present |= bit;
            ++n;
          }
          if (n == k_scatter_run_len) {
            for (size_t i = 0; i < n; ++i) {
              const size_t j = c * k_store_block + run_t[i];
              for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {
                auto kout = row_of(run_ix[i], kv_head);
                if constexpr (rows_are_bf16) {
                  // The row view keeps the K buffer's alignment and DMA flags.
                  pg.template set_k_row<geometry.kv>(
                      slot, kv_head, j, k_source_row(kout));
                } else {
                  view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
                      seq<geometry.kv.head_size>>{conv[0]}
                      .set(kout);
                  pg.template set_k_row<geometry.kv>(
                      slot, kv_head, j, k_source_row<geometry.kv.head_size>(conv[0]));
                }
              }
            }
          } else {
            for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {
              const bf16* rows[k_store_block] = {};
              for (size_t i = 0; i < n; ++i) {
                auto kout = row_of(run_ix[i], kv_head);
                if constexpr (rows_are_bf16) {
                  rows[run_t[i]] = kout.data;
                } else {
                  view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
                      seq<geometry.kv.head_size>>{conv[i]}
                      .set(kout);
                  rows[run_t[i]] = conv[i];
                }
              }
              pg.template set_k_block<geometry.kv>(slot, kv_head, c, present, rows);
            }
          }
        }
      }
    }

    // Every worker of the store calls this (Note [Shared block save]).
    // worker_ix 0 is main: it opens the window, stores its share, joins the
    // helpers, then marks the tokens. worker_ix 1 .. n_workers - 1 is a main
    // helper: it waits for its window, stores its share and leaves.
    template <attention_geometry geometry, typename kv_buffer_t>
    void save_k_impl(batch* q_batch,
        attention_operation_descriptor const& operation,
        kv_buffer_t& ks,
        size_t worker_ix,
        size_t n_workers) noexcept {
      static_assert(geometry.valid());
      static_assert(attention_buffer_width<kv_buffer_t> == geometry.kv_width());
      TRON_ASSERT(operation.writes_kv, "attention operation {} does not write KV",
          operation.binding.operation);
      TRON_ASSERT(worker_ix < n_workers, "save_k: worker_ix {} outside 0..{}",
          worker_ix, n_workers - 1);
      const bool is_main = worker_ix == 0;
      const bool shared = k_store_shared<geometry>(q_batch, n_workers);
      // An unshared store is main's alone.
      if (!is_main && !shared) return;
      const attention_binding binding = operation.binding;
      TRACE_EVENT("model", "Save K");
      const model_layer_id layer = binding.model_layer;
      const kv_slot_id slot = binding.kv_slot;
      tron_maybe_unused const bool has_hardware_slot =
          geometry == self_attn_t::hardware_geometry &&
          operation_is_hardware_candidate(operation);
      const size_t n_items = q_batch->items.size();
      // Update the pages first. That way HW sees the latest K values.
      if (shared) {
        // See Note [Shared block save].
        auto& w = q_batch->k_store_window;
        const uint32_t n_helpers = static_cast<uint32_t>(n_workers - 1);
        if (is_main) {
          k_store_cut_units(q_batch);
          w.next_unit.store(0, std::memory_order_relaxed);
          w.finished.store(0, std::memory_order_relaxed);
          w.opened.fetch_add(1, std::memory_order_release);
        } else {
          const uint32_t my_window = ++w.helper_windows[worker_ix];
          while (w.opened.load(std::memory_order_acquire) < my_window) {
            _mm_pause();
          }
        }
        const uint32_t n_units = w.n_units;
        for (;;) {
          const uint32_t u = w.next_unit.fetch_add(1, std::memory_order_acq_rel);
          if (u >= n_units) break;
          store_k_block<geometry>(
              q_batch, slot, ks, w.unit_start[u], w.unit_start[u + 1]);
        }
        if (!is_main) {
          w.finished.fetch_add(1, std::memory_order_release);
          return;
        }
        uint64_t spins = 0;
        std::chrono::steady_clock::time_point t0{};
        while (w.finished.load(std::memory_order_acquire) < n_helpers) {
          _mm_pause();
          if ((++spins & (k_join_clock_spins - 1)) == 0) {
            const auto now = std::chrono::steady_clock::now();
            if (t0 == std::chrono::steady_clock::time_point{}) t0 = now;
            TRON_ASSERT(now - t0 < std::chrono::seconds(k_join_timeout_s),
                "save_k: the K store window did not close in {} s ({} of {} helpers "
                "finished, {} of {} units claimed); the helpers' save_k calls do not "
                "match this one",
                k_join_timeout_s, w.finished.load(), n_helpers,
                std::min<uint32_t>(w.next_unit.load(), n_units), n_units);
          }
        }
      } else {
        store_k_block<geometry>(q_batch, slot, ks, 0, n_items);
      }
      for (token_job_id ix : q_batch->items) {
        auto const& self = *this;
        if (!self.token_jobs_do_kv[ix]) continue;
        log_intermediate(ks[ix], geometry.kv_width(), ix, layer.i, "WK roped");
        token_id tok_ix = token_jobs[ix];
        page& pg = page_of(tok_ix);
        int j = pg.offset_in_page(tok_ix);
        pg.mark_k_complete(slot, static_cast<size_t>(j));
        // Drive the per-GOF dispatch counter. See Note [GOF dispatch
        // synchronization].
        if constexpr (geometry == self_attn_t::hardware_geometry) {
          if (has_hardware_slot) credit_gof_save(ix, slot, layer);
        }
      }
      // Ping downstream minibatches. See Note [Minibatch Dependency Tracking]
      for (auto batch_2 : q_batch->downstream_minibatches)
        batch_2->upstream_kvs_ready[slot].count_down();
    }

    // Store the K rows of the minibatch. Main (worker_ix 0) and the main
    // helpers (worker_ix 1 .. n_workers - 1) call this with the same
    // operation at the same point of the schedule (the generated plugins
    // pass their run() split). See Note [Shared block save]. The defaults
    // store every row on the calling thread.
    template <attention_geometry geometry, size_t operation_ix, typename kv_buffer_t>
    void save_k(batch* q_batch,
        kv_buffer_t& ks,
        size_t worker_ix = 0,
        size_t n_workers = 1) noexcept {
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      static_assert(operation.writes_kv);
      save_k_impl<geometry>(q_batch, operation, ks, worker_ix, n_workers);
    }

    template <attention_geometry geometry, typename kv_buffer_t>
    void save_k(batch* q_batch,
        attention_operation_descriptor const& operation,
        kv_buffer_t& ks,
        size_t worker_ix = 0,
        size_t n_workers = 1) noexcept {
      self_attn_state.template validate_operation<geometry>(operation);
      save_k_impl<geometry>(q_batch, operation, ks, worker_ix, n_workers);
    }

    template <attention_geometry geometry, typename kv_buffer_t>
    void save_v_impl(batch* q_batch,
        attention_operation_descriptor const& operation,
        kv_buffer_t& vs) noexcept {
      static_assert(geometry.valid());
      static_assert(attention_buffer_width<kv_buffer_t> == geometry.kv_width());
      TRON_ASSERT(operation.writes_kv, "attention operation {} does not write KV",
          operation.binding.operation);
      const attention_binding binding = operation.binding;
      TRACE_EVENT("model", "Save V");
      const model_layer_id layer = binding.model_layer;
      const kv_slot_id slot = binding.kv_slot;
      tron_maybe_unused const bool has_hardware_slot =
          geometry == self_attn_t::hardware_geometry &&
          operation_is_hardware_candidate(operation);
      // Take care: we can't just split the items across threads, because
      // packed V stores the even-offset and odd-offset tokens of any given
      // page in the same SIMD values (see Note [VNNI Packed V layout] in
      // h/tron/tensor/v_vnni.hpp): the odd token's append merges into its
      // even partner's pair, and so would race with ourselves if different
      // threads were to try to save the two halves of such a pair separately.
      // The executor's V buffer holds bf16 (btensor), fp16 (htensor) or float
      // (tensor). page::set_v takes one aligned, read-only head-sized row of
      // it, with the buffer's scalar and DMA flag.
      using v_buffer_t = std::remove_cvref_t<decltype(vs[token_job_id(0)])>;
      for (token_job_id ix : q_batch->items) {
        auto const& self = *this;
        if (!self.token_jobs_do_kv[ix]) continue;
        log_intermediate(vs[ix], geometry.kv_width(), ix, layer.i, "WV");
        token_id tok_ix = token_jobs[ix];
        page& pg = page_of(tok_ix);
        int j = pg.offset_in_page(tok_ix);

        for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {
          pg.template set_v<geometry.kv>(slot, kv_head, j,
              v_source_row<geometry.kv.head_size, v_buffer_t::dma>(
                  &vs[ix][kv_head * geometry.kv.head_size]));
        }
        pg.mark_v_complete(slot, static_cast<size_t>(j));
        // See Note [GOF dispatch synchronization].
        if constexpr (geometry == self_attn_t::hardware_geometry) {
          if (has_hardware_slot) credit_gof_save(ix, slot, layer);
        }
      }
      // Ping downstream minibatches. See Note [Minibatch Dependency Tracking]
      for (auto batch_2 : q_batch->downstream_minibatches)
        batch_2->upstream_kvs_ready[slot].count_down();
    }

    template <attention_geometry geometry, size_t operation_ix, typename kv_buffer_t>
    void save_v(batch* q_batch, kv_buffer_t& vs) noexcept {
      constexpr auto const& operation =
          generated_attention_operation<geometry, operation_ix>();
      static_assert(operation.writes_kv);
      save_v_impl<geometry>(q_batch, operation, vs);
    }

    template <attention_geometry geometry, typename kv_buffer_t>
    void save_v(batch* q_batch,
        attention_operation_descriptor const& operation,
        kv_buffer_t& vs) noexcept {
      self_attn_state.template validate_operation<geometry>(operation);
      save_v_impl<geometry>(q_batch, operation, vs);
    }

    void credit_gof_save(
        token_job_id ix, kv_slot_id slot, model_layer_id layer) noexcept {
      if (ix.i >= gof_jobs_span.size()) return;
      hardware::credit_gof_save(
          gof_jobs_span[ix], slot, [this, ix, slot, layer](size_t target_ix) {
            // GOF complete: hand it to the cooperative drain queue. The GOF is
            // fully saved, so a worker may run it immediately; the forward-end
            // barrier bounds the lifetime of the scheduler-owned target.
            gof_coop_outstanding_.fetch_add(1, std::memory_order_acq_rel);
            gof_coop_queue_.enqueue({ix.i, target_ix, slot, layer});
          });
    }

    // Cooperative-drain helper: run up to `budget` pending GOFs from the shared
    // queue. Called by attention workers at their between-layer idle point
    // so the GOF populate+DMA-submit happens on workers that would
    // otherwise be spinning. Bounded so a worker never starves its own
    // attention work draining a large (prefill) backlog.
    // fire_gof_rodeo is safe to run concurrently across workers (distinct GOFs,
    // staging_busy CAS, dma_tracker mutex); see Note [GOF dispatch synchronization].
    void help_drain_gof(size_t budget) noexcept {
      gof_coop_task task;
      for (size_t i = 0; i < budget && gof_coop_queue_.try_dequeue(task); ++i) {
        fire_gof_rodeo(task.job_ix, task.target_ix, task.slot, task.layer);
        gof_coop_outstanding_.fetch_sub(1, std::memory_order_acq_rel);
      }
    }

    // Forward-end barrier to drain any GOFs the workers did not get to, then wait
    // for in-flight submits, so every fire_gof_rodeo is done before the scheduler
    // rebuilds gof_jobs (which it dereferences). The attention workers have already
    // exited their schedule by the time this runs (plugin run() joins them), so the
    // remainder here is the tail backlog only.
    void wait_for_coop_gof() noexcept {
      TRACE_EVENT("hwattention", "wait_coop_gof");
      gof_coop_task task;
      while (gof_coop_queue_.try_dequeue(task)) {
        fire_gof_rodeo(task.job_ix, task.target_ix, task.slot, task.layer);
        gof_coop_outstanding_.fetch_sub(1, std::memory_order_acq_rel);
      }
      while (gof_coop_outstanding_.load(std::memory_order_acquire) > 0) {
      }
    }

    // Dispatch one target whose GOF save counter reached completion.
    void fire_gof_rodeo(size_t job_ix,
        size_t target_ix,
        kv_slot_id slot,
        model_layer_id layer) noexcept {
      if (!gof_rodeo_fn) return;
      // Assert all 4 tokens have K+V complete in this slot.
      if (job_ix >= gof_jobs_span.size()) return;
      auto const& job = gof_jobs_span[token_job_id(job_ix)];
      if (target_ix >= job.targets.size()) return;
      auto const& target = job.targets[target_ix];
      if (!target.gal_ptr || slot.i >= target.gal_ptr->gofs.size() ||
          !target.gal_ptr->gofs[slot.i])
        return;
      for (uint32_t p = 0; p < tron::hardware::gof_tokens; ++p) {
        TRON_ASSERT(target.gal_ptr->pages[p].kv_complete_fn,
            "GOF rodeo for job {} target {} but token at pos {} has no "
            "kv_complete_fn at slot {} (model layer {})",
            job_ix, target_ix, target.gal_ptr->pages[p].position, slot, layer);
        TRON_ASSERT(target.gal_ptr->pages[p].kv_complete_fn(slot),
            "GOF rodeo for job {} target {} but token at pos {} not kv_complete "
            "at slot {} (model layer {})",
            job_ix, target_ix, target.gal_ptr->pages[p].position, slot, layer);
      }
      gof_rodeo_fn(job_ix, target_ix, slot, layer);
    }

    // ---------------------------------------------------------------------------
    // gof_rodeo_impl — tree-unaware GOF completion handler.
    //
    // Called when all four tokens in a GOF have K and V complete for a
    // given KV slot. Populates a gof by swizzling page data into
    // hwcacheblock format, then DMAs to shards whose token range
    // covers the gal's position.
    // ---------------------------------------------------------------------------

    void gof_rodeo_impl(size_t job_ix,
        size_t target_ix,
        kv_slot_id slot,
        model_layer_id layer) noexcept {
      using namespace tron::hardware;
      // SW-only slots carry no HBM allocation; xfer_gof would dereference null bases.
      if (!hardware::slot_uses_hw(self_attn_state.hw_attn_cfg, slot)) return;
      if (job_ix >= gof_jobs_span.size()) return;
      auto const& job = gof_jobs_span[token_job_id(job_ix)];
      if (target_ix >= job.targets.size()) return;
      auto const& target = job.targets[target_ix];
      if (target.shards_getting_gofs.empty()) return;

      TRACE_EVENT("hwattention", "gof_rodeo", "layer", layer.i, "kv_slot", slot.i);
      uint32_t tok_pos = target.tok_position;

      // Populate the pre-created GOF from page_info lambdas captured
      // during tree traversal. No tree access needed.
      TRON_ASSERT(target.gal_ptr, "gof_rodeo: job {} has null gal_ptr", job_ix);
      TRON_ASSERT(slot.i < target.gal_ptr->gofs.size(),
          "gof_rodeo: slot {} >= gal gofs size {} (model layer {})", slot,
          target.gal_ptr->gofs.size(), layer);
      // shared_ptr COPY (not a reference into gal.gofs): keeps the GOF alive across
      // the whole reacquire/populate/xfer_gof/push submit window, before pending_xfer
      // takes its own host-side GOF reference. A concurrent gal teardown must not
      // dangle this or the guard's gof*.
      auto g = target.gal_ptr->gofs[slot.i];
      TRON_ASSERT(g, "gof_rodeo: null gof for job {} target {} slot {} layer {}",
          job_ix, target_ix, slot, layer);
      PosDevice* dev = target.shards_getting_gofs[0]->dev;
      // DMA this slot's GOF to each shard that still needs it.
      //
      // prepare_for_dma() makes the GOF staging buffers usable for this transfer:
      // it re-allocates K/V staging if a prior DMA completion freed them, populates
      // them from the saved page data if needed, and increments dma_inflight before
      // xfer_gof submits descriptors that read those buffers.
      //
      // After xfer_gof(), descriptors are live, so guard.commit() prevents the guard
      // destructor from undoing the dma_inflight increment. The tracker entry pushed
      // below stores `g`; when that DMA completes, poll_completions() will decrement
      // dma_inflight and may free the staging buffers.
      //
      // backfill_shard() uses the same prepare_for_dma() path, so either the rodeo
      // path here or the backfill path may be the first one to populate the GOF.
      // See Note [GOF staging eviction].
      for (auto const& sh : target.shards_getting_gofs) {
        TRON_ASSERT(sh, "null shard in gof_job");
        // A degraded shard holds no HBM; its range runs SW attention. See Note
        // [HBM exhaustion degrades to software attention].
        if (!sh->hw_usable()) continue;
        if (tok_pos < sh->base_tok_ix || tok_pos >= sh->base_tok_ix + shard_tokens) {
          continue;
        }
        size_t gof_in_shard = (tok_pos - sh->base_tok_ix) / gof_tokens;
        auto reservation =
            sh->try_reserve_gof_dma(static_cast<uint32_t>(gof_in_shard), slot);
        if (!reservation) {
          continue;
        }
        auto guard =
            g->prepare_for_dma(n_kv_heads, head_size, slot, dev, target.gal_ptr->pages);
        auto last_v = sh->xfer_gof(*g, static_cast<uint32_t>(gof_in_shard), slot);
        reservation.commit();

        // xfer_gof() has submitted descriptors that may read this GOF's staging
        // buffers, so the in-flight credit must stay in place. commit() prevents
        // the guard destructor from rolling that credit back.
        //
        // push() is noexcept: if the submitted DMA cannot be recorded, terminate
        // instead of unwinding while DMA may still read staging. After a successful
        // push, poll_completions() decrements dma_inflight on completion.
        guard.commit();
        dma_tracker->push(sh->dev->idx,
            pending_xfer{last_v, sh, static_cast<uint32_t>(gof_in_shard), slot, g});
      }
    }

    void prepare_for_logits() noexcept {
      if (n_logit_listeners > 0) prepare_logit_chk(0, logits_chunk_size);
    }

    void run_logits(size_t logits_chunk_size) {
      MODEL_DEBUG("{}", __PRETTY_FUNCTION__);
      // Note: LogitsMode::ALL in testutil.hpp relies on the logits listeners being
      // called in series, and in the order in which they were registered; otherwise, we
      // will race or save logits out of order, respectively.
      for (size_t logit_chk = 0; logit_chk < n_logit_chks; logit_chk++) {
        if (logit_chk > 0)  // The 0th one was prepared in advance by `run`
          prepare_logit_chk(logit_chk, logits_chunk_size);
        size_t chunk_start = n_empty_listeners + logit_chk * logits_chunk_size;
        size_t chunk_end = std::min(
            n_empty_listeners + (logit_chk + 1) * logits_chunk_size, n_listeners);
        for (size_t offset = 0; offset < chunk_end - chunk_start; ++offset) {
          auto j = listener_job_index[listener_id(chunk_start + offset)];
          // This version no longer assumes one listener per token j.
          auto copies = compensated_embeddings[offset].as_view();
          auto original = slice<dim>()(copies, 0);
          // This read is synchronized by the plugin's obligation to wait
          // for its workers.  See Note [Plugin-owned worker launch].
          original.set(final_embedding[j]);
          if constexpr (wcls_is_compensated)
            // TODO perform this copy in hardware
            slice<dim>()(copies, dim).set(original);
        }
        if (logit_chk > 0)
          // Wait until the listeners are done with the `logits` buffer before I
          // authorize wcls to overwrite it with the next chunk's worth.
          // TODO We could also eliminate the wait by double-buffering, i.e., having two
          // `logits` buffers.
          logits_free[logit_chk - 1].wait();
        if constexpr (launch_wcls_t::can_stream_result) {
          wcls_streams = launch_wcls.stream_results();
          logits_prepared[logit_chk].reset(chunk_end - chunk_start);
          logits_allocated[logit_chk].count_down();
          // wait for workers to prepare streams
          logits_prepared[logit_chk].wait();
        }
        launch_wcls(logits_done[logit_chk]);
        // Note: eagle_x_out is now written separately for ALL tokens after all
        // logit chunks complete (see below), not just listener tokens.
        // Can't (yet?) start preparing the next chunk before the current chunk's matmul
        // actually completes, because they are reusing the same launcher field.
        TRACE_EVENT("model", "waiting_for_logits");
        logits_done[logit_chk].wait();
      }
      // This is the main thread waiting for all of the callbacks to be done.
      listeners_notified.wait();

      // Write eagle_x_out for ALL tokens with allocated output pointers.
      // The scheduler allocates eagle_x_out for all tokens in an edge, but
      // listener_job_index only covers the subset with logit listeners.
      if (!eagle_x_out.empty()) {
        for (token_job_id j : token_jobs.indices()) {
          token_id tok = token_jobs[j];
          activation_scalar* x_out = eagle_x_out[tok];
          if (!x_out) continue;
          auto embedding = final_embedding[j].as_view();
          view<activation_scalar, true, true, seq<dim>, sseq<1>>(x_out).set(embedding);
        }
      }
    }

    void run_listener_notifications(
        size_t logits_chunk_size, size_t worker_ix) noexcept {
      // Parallelize listener notifications across the app pool.
      // We parallelize within rather than across logit chunks because they come off the
      // cards one at a time, and at low token counts there are very few of them (e.g.,
      // 1) anyway.
      for (size_t chk = 0; chk < n_empty_chks; chk++) {
        size_t chunk_start = chk * logits_chunk_size;
        size_t chunk_end = std::min((chk + 1) * logits_chunk_size, n_empty_listeners);
        for (size_t offset = worker_ix; offset < chunk_end - chunk_start;
            offset += logits_chunk_size) {
          TRACE_EVENT("model", "notify_listener", "listener", chunk_start + offset,
              "logits", false);
          listener_notifications[listener_id(chunk_start + offset)]();
        }
      }
      for (size_t logit_chk = 0; logit_chk < n_logit_chks; logit_chk++) {
        size_t chunk_start = n_empty_listeners + logit_chk * logits_chunk_size;
        size_t chunk_end = std::min(
            n_empty_listeners + (logit_chk + 1) * logits_chunk_size, n_listeners);
        if constexpr (launch_wcls_t::can_stream_result) {
          logits_allocated[logit_chk].wait();
          for (size_t offset = worker_ix; offset < chunk_end - chunk_start;
              offset += logits_chunk_size) {
            TRACE_EVENT("model", "prepare streams", "listener", chunk_start + offset);
            wcls_streams[offset].prepare();
            logits_prepared[logit_chk].count_down();
          }
        } else {
          logits_done[logit_chk].wait();
        }
        for (size_t offset = worker_ix; offset < chunk_end - chunk_start;
            offset += logits_chunk_size) {
          TRACE_EVENT("model", "notify_listener", "listener", chunk_start + offset,
              "logits", true);
          for (logits_buffer_t const& buf :
              listener_buffers[listener_id(chunk_start + offset)]) {
            if constexpr (launch_wcls_t::can_stream_result)
              if (std::holds_alternative<dense_logits_t>(buf))
                // Dense logits do not support streaming.
                logits_done[logit_chk].wait();
            if tron_unlikely (cfg.log_intermediates) {
              // logging is coded to just read the output buffer.
              logits_done[logit_chk].wait();
            }
            fill_logits_buffer(listener_id(chunk_start + offset), offset, buf);
          }
          // This is the line of code that actually calls the callback that
          // had been passed to `sequence_prompt`.
          listener_notifications[listener_id(chunk_start + offset)]();
        }
        logits_free[logit_chk].count_down();
      }
      listeners_notified.count_down();
    }

    void fill_logits_buffer(
        listener_id job_ix, size_t offset, logits_buffer_t const& buf) noexcept {
      TRACE_EVENT("model", "fill_logits_buffer");
      std::visit(
          [this, job_ix, offset](auto const& buf) -> void {
            if tron_unlikely (cfg.log_intermediates) {
              // TODO: Special-case gemma2 here, if desired.
              // TODO: This could move into the plugin in `patch_logits`,
              // but not in `patch_logits_in_place`, because the latter only
              // sees the `max_top_k` highest logits, not all of them.
              auto j = listener_job_index[job_ix];
              log_intermediate(logits[offset], vocab_size, j, "Logits");
            }
            using T = std::decay_t<decltype(buf)>;
            if constexpr (std::is_same_v<T, dense_logits_t>) {
              TRON_ASSERT_EQ(buf.nlogits, vocab_size);
              auto logits_out =
                  view<float, false, false, seq<vocab_size>, sseq<1>>(buf.logits);
              // This sets client-owned memory and may SEGFAULT if the client sends an
              // invalid buffer.
              plugin_state.patch_logits(logits[offset], logits_out);
            } else if constexpr (std::is_same_v<T, sparse_logits_t>) {
              top_k_accum_t accum(max_top_k);
              if constexpr (launch_wcls_t::can_stream_result) {
                auto& stream = wcls_streams[offset];
                stream.start();
                // This will spin poll among TP tiles.
                auto* mask = buf.constraint_mask.get();
                while (!stream.try_consume(
                    [&accum, mask](size_t off, bf16* begin, bf16* end) {
                      accum.insert(begin, end - begin, mask, off);
                    }))
                  ;
              } else {
                accum.insert(&logits[offset][0], vocab_size, buf.constraint_mask.get());
              }
              std::tie(buf.logits, buf.tokens) = accum.sort();
              size_t actual_count = buf.logits.size();
              if tron_unlikely (cfg.log_intermediates) {
                auto j = listener_job_index[job_ix];
                log_intermediate(buf.logits, actual_count, j, "Top-k Logits");
                log_intermediate(
                    buf.tokens, actual_count, j, "Top-k Token IDs for Logits");
              }
              bool needs_resize = buf.constraint_mask && actual_count != max_top_k;
              // When constraint_mask filters valid tokens, sort() may return
              // fewer than max_top_k elements. Pad so the fixed-size view
              // used by patch_logits_in_place doesn't read past the buffer.
              if (needs_resize) buf.logits.resize(max_top_k, -1.0f / 0.0f);
              auto logits =
                  view<float, false, false, seq<max_top_k>, sseq<1>>(buf.logits.data());
              plugin_state.patch_logits_in_place(logits);
              if (needs_resize) buf.logits.resize(actual_count);
            }
          },
          buf);
    }

    void prepare_logit_chk(size_t logit_chk, size_t logits_chunk_size) noexcept {
      size_t chunk_start = logit_chk * logits_chunk_size;
      size_t chunk_end = std::min((logit_chk + 1) * logits_chunk_size, n_listeners);
      std::vector<size_t> indices(chunk_end - chunk_start);
      std::iota(indices.begin(), indices.end(), 0);
      wcls_t::fill_matmul_template(logits.data(), compensated_embeddings.data(),
          indices, launch_wcls, {}, "wcls");
      if constexpr (requires { plugin_state.model.wcls.prepare_matmul(launch_wcls); }) {
        plugin_state.model.wcls.prepare_matmul(launch_wcls);
      } else {
        plugin_state.model.wcls->prepare_matmul(launch_wcls);
      }
    }
  };
};

}  // namespace tron
