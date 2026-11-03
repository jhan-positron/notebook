#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <future>
#include <latch>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <thread>
#include <vector>

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

#include "common/util.hpp"
#include "kv_cache_helpers.hpp"
#include "pos/device.hpp"
#include "pos/hwattention.hpp"
#include "system/memory.hpp"
#include "tron/hardware/attention_slots.hpp"
#include "tron/models/attn_stats.hpp"
#include "tron/models/heterogeneous_kv_cache.hpp"
#include "tron/models/model.hpp"
#include "tron/models/moe_router_id.hpp"
#include "tron/scheduler/full.hpp"
#include "tron/scheduler/token_cache.hpp"
#include "tron/scheduler/token_cache_control.hpp"
#include "tron/shard.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/view.hpp"

namespace tron {

// Compile the full scheduler against a cache that deliberately provides no
// layer-to-slot compatibility API.
template <llm_executor executor, bool has_hardware_geometry = true>
struct heterogeneous_scheduler_plugin
: noncopyable<heterogeneous_scheduler_plugin<executor, has_hardware_geometry>> {
  static constexpr size_t dim = 256;
  static constexpr size_t n_layers = 3;
  static constexpr size_t n_moe_routers = 0;
  static constexpr size_t n_heads = 1;
  static constexpr size_t n_kv_heads = 1;
  static constexpr size_t head_size = 128;
  static constexpr size_t vocab_size = 128;
  static constexpr bool permuted = executor::permuted;
  static constexpr bool wcls_is_compensated = true;
  static constexpr bool attn_softcapping = false;
  static constexpr int max_minibatches = -1;
  static constexpr size_t max_minibatch_size = 128;
  inline static constexpr bool force_hw_attn = true;
  static constexpr bool moe = false;
  static constexpr size_t n_experts = 1;
  static constexpr size_t n_shared_experts = 1;
  static constexpr size_t n_routed_experts = 0;
  // Attention workers the fixture's run assembles the plan for.
  static constexpr size_t RUN_N_ATTN_WORKERS_1 = 1;
  inline static const indexed_vector<moe_router_id, size_t>
      expert_routing_top_k_by_router{};

  template <size_t M, size_t N>
  using dtensor_t = typename executor::template dtensor_t<M, N>;
  template <size_t M, size_t N>
  using expert_dtensor_t = typename executor::template expert_dtensor_t<M, N>;
  template <size_t d, size_t... ds>
  using btensor_t = typename executor::template btensor_t<d, ds...>;

  inline static constexpr attention_geometry geometry_64{1, kv_geometry{1, 64}};
  inline static constexpr attention_geometry geometry_128{1, kv_geometry{1, 128}};
  inline static constexpr attention_geometry geometry_256{1, kv_geometry{1, 256}};
  inline static constexpr attention_geometry middle_geometry =
      has_hardware_geometry ? geometry_128 : geometry_64;
  inline static constexpr size_t middle_width = middle_geometry.query_width();
  inline static constexpr std::array slot_specs{
      kv_slot_spec{geometry_64.kv},
      kv_slot_spec{middle_geometry.kv},
      kv_slot_spec{geometry_256.kv},
  };
  using cache_t =
      heterogeneous_kv_cache<slot_specs, dim * sizeof(typename btensor_t<dim>::scalar)>;
  inline static constexpr std::array attention_kernels = {
      attention_kernel_spec{attention_kernel_id(0), geometry_64},
      attention_kernel_spec{attention_kernel_id(1), middle_geometry},
      attention_kernel_spec{attention_kernel_id(2), geometry_256},
  };
  inline static constexpr std::array attention_operations{
      attention_operation_descriptor{
          attention_binding{attention_op_id(0), model_layer_id(0), kv_slot_id(0)},
          attention_kernel_id(0), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, 0.125f}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(1), model_layer_id(2), kv_slot_id(1)},
          attention_kernel_id(1),
          has_hardware_geometry ? attention_hardware_capability::kv_slot_candidate
                                : attention_hardware_capability::software_only,
          true, attention_operation_config{std::nullopt, std::nullopt, 0x1.6a09e6p-4f}},
      attention_operation_descriptor{
          attention_binding{attention_op_id(2), model_layer_id(1), kv_slot_id(2)},
          attention_kernel_id(2), attention_hardware_capability::software_only, true,
          attention_operation_config{std::nullopt, std::nullopt, 0.0625f}},
  };
  static constexpr size_t active_attention_operation_count(size_t) noexcept {
    return attention_operations.size();
  }
  static_assert(valid_attention_configuration(
      attention_kernels, attention_operations, cache_t::kv_slot_specs));
  using wcls_t = dtensor_t<vocab_size, dim + dim>;

  struct state;
  struct plugin_batch;

  inline static constexpr std::array<attention_sink_spec, 0> attention_sink_specs{};

  std::span<const float> attention_sink(attention_sink_id) const noexcept {
    TRON_ASSERT(false, "heterogeneous scheduler fixture has no attention sinks");
    return {};
  }
  std::shared_ptr<wcls_t> wcls;
  const bool is_eagle = false;

  heterogeneous_scheduler_plugin(json, int) noexcept
  : wcls(std::make_shared<wcls_t>()) {}

  void cache_weights(std::string const&) noexcept {}
  void finalize_weights() noexcept {}

  template <typename Visit>
  void visit_named_tensors(Visit&&, int = -1, bool = false) noexcept {}

  struct state : noncopyable<state> {
    using outer_model_t = ::tron::model<heterogeneous_scheduler_plugin>;
    using outer_batch_t = batch<outer_model_t>;
    template <size_t width>
    using intermediate_t = indexed_vector<token_job_id, btensor_t<width>>;
    template <size_t width>
    using compile_channel_t =
        channel<token_job_id, btensor_t<width>, tensor_latch<fallback_producer_t>>;

    heterogeneous_scheduler_plugin const& model;
    outer_model_t::state& outer_state;

    state(heterogeneous_scheduler_plugin const& model,
        ::tron::model<heterogeneous_scheduler_plugin>::state& outer_state,
        model_config const&) noexcept
    : model(model)
    , outer_state(outer_state) {}

    size_t available_main_parallelism(size_t) const noexcept {
      return 1;
    }

    void resize(size_t) noexcept {}
    void make_latches(latch_arena&) noexcept {}

    template <typename In, typename Out>
    void patch_logits(In& logits_in, Out& logits_out) noexcept {
      logits_out.set(logits_in);
    }

    template <typename Logits>
    void patch_logits_in_place(Logits&) noexcept {}

    void compile_generated_attention_calls(outer_batch_t* q_batch,
        intermediate_t<64>& q64,
        compile_channel_t<64>& q64_channel,
        intermediate_t<64>& k64,
        intermediate_t<64>& v64,
        intermediate_t<64>& o64,
        compile_channel_t<64>& o64_channel,
        intermediate_t<middle_width>& q_middle,
        compile_channel_t<middle_width>& q_middle_channel,
        intermediate_t<middle_width>& k_middle,
        intermediate_t<middle_width>& v_middle,
        intermediate_t<middle_width>& o_middle,
        compile_channel_t<middle_width>& o_middle_channel,
        intermediate_t<256>& q256,
        compile_channel_t<256>& q256_channel,
        intermediate_t<256>& k256,
        intermediate_t<256>& v256,
        intermediate_t<256>& o256,
        compile_channel_t<256>& o256_channel) {
      outer_state
          .template assemble_attention_plan<geometry_64, middle_geometry, geometry_256>(
              1);

      outer_state.template prepare_attention_job<geometry_64, 0>(q_batch, q64);
      outer_state.template save_k<geometry_64, 0>(q_batch, k64);
      outer_state.template save_v<geometry_64, 0>(q_batch, v64);
      (void)outer_state.template run_attention_job<geometry_64, 0>(
          q_batch, q64, q64_channel, o64, o64_channel, 0, 1);
      outer_state.template launch_hw_attention<geometry_64, 0>(
          q_batch, q64, q64_channel);

      outer_state.template prepare_attention_job<middle_geometry, 1>(q_batch, q_middle);
      outer_state.template save_k<middle_geometry, 1>(q_batch, k_middle);
      outer_state.template save_v<middle_geometry, 1>(q_batch, v_middle);
      (void)outer_state.template run_attention_job<middle_geometry, 1>(
          q_batch, q_middle, q_middle_channel, o_middle, o_middle_channel, 0, 1);
      outer_state.template launch_hw_attention<middle_geometry, 1>(
          q_batch, q_middle, q_middle_channel);

      outer_state.template prepare_attention_job<geometry_256, 2>(q_batch, q256);
      outer_state.template save_k<geometry_256, 2>(q_batch, k256);
      outer_state.template save_v<geometry_256, 2>(q_batch, v256);
      (void)outer_state.template run_attention_job<geometry_256, 2>(
          q_batch, q256, q256_channel, o256, o256_channel, 0, 1);
      outer_state.template launch_hw_attention<geometry_256, 2>(
          q_batch, q256, q256_channel);
    }

    void run(std::vector<
        std::unique_ptr<batch<::tron::model<heterogeneous_scheduler_plugin>>>>&) {
      // As a generated plugin does (compile_generated_attention_calls above):
      // the forward's attention plan for one attention worker. No attention
      // job runs; the forward then goes straight to the logits.
      outer_state
          .template assemble_attention_plan<geometry_64, middle_geometry, geometry_256>(
              RUN_N_ATTN_WORKERS_1);
      outer_state.prepare_for_logits();
    }
  };

  struct plugin_batch {
    std::vector<token_job_id> items;

    plugin_batch(state&,
        batch<::tron::model<heterogeneous_scheduler_plugin>>&,
        latch_arena&,
        size_t) noexcept {}

    void reset_channels(size_t, size_t) noexcept {}
    void next_layer() noexcept {}
  };
};

using heterogeneous_scheduler_tp1 = heterogeneous_scheduler_plugin<tp1>;
using software_only_heterogeneous_scheduler_tp1 =
    heterogeneous_scheduler_plugin<tp1, false>;
using heterogeneous_scheduler_state = heterogeneous_scheduler_tp1::state;
using heterogeneous_model = model<heterogeneous_scheduler_tp1>;
using heterogeneous_outer_state = heterogeneous_model::state;
using software_only_heterogeneous_model =
    model<software_only_heterogeneous_scheduler_tp1>;

[[maybe_unused]] auto const compile_generated_attention_calls =
    &heterogeneous_scheduler_state::compile_generated_attention_calls;

static_assert(plugin<heterogeneous_scheduler_tp1>);
static_assert(sequence_cache<heterogeneous_scheduler_tp1::cache_t>);
template <typename Cache>
constexpr bool cache_accepts_model_layer =
    requires { Cache::kv_slot(model_layer_id(0)); };
static_assert(!cache_accepts_model_layer<heterogeneous_scheduler_tp1::cache_t>);
static_assert(model<heterogeneous_scheduler_tp1>::model_shape_is_hwattn_eligible());
static_assert(!software_only_heterogeneous_model::model_shape_is_hwattn_eligible());
static_assert(heterogeneous_outer_state::template valid_generated_attention_operation<
    heterogeneous_scheduler_tp1::geometry_64,
    0>());
static_assert(heterogeneous_outer_state::template valid_generated_attention_operation<
    heterogeneous_scheduler_tp1::geometry_128,
    1>());
static_assert(heterogeneous_outer_state::template valid_generated_attention_operation<
    heterogeneous_scheduler_tp1::geometry_256,
    2>());
static_assert(!heterogeneous_outer_state::template valid_generated_attention_operation<
    heterogeneous_scheduler_tp1::geometry_128,
    0>());
static_assert(!heterogeneous_outer_state::template valid_generated_attention_operation<
    heterogeneous_scheduler_tp1::geometry_64,
    3>());
static_assert(heterogeneous_outer_state::template valid_generated_attention_plan<
    heterogeneous_scheduler_tp1::geometry_64,
    heterogeneous_scheduler_tp1::geometry_128,
    heterogeneous_scheduler_tp1::geometry_256>());
static_assert(!heterogeneous_outer_state::template valid_generated_attention_plan<
    heterogeneous_scheduler_tp1::geometry_128,
    heterogeneous_scheduler_tp1::geometry_64,
    heterogeneous_scheduler_tp1::geometry_256>());
static_assert(!heterogeneous_outer_state::template valid_generated_attention_plan<
    heterogeneous_scheduler_tp1::geometry_64,
    heterogeneous_scheduler_tp1::geometry_128>());

template <typename Channel>
struct observed_output_channel {
  static constexpr readiness_scope scope = Channel::scope;
  Channel& output;
  std::latch& started;

  void start_writing(size_t worker) {
    output.start_writing(worker);
    started.count_down();
  }

  void finish_writing(size_t worker) {
    output.finish_writing(worker);
  }
};

// An enabled attention path stats object (h/tron/models/attn_stats.hpp) in
// place of the state's own, which follows TRON_ATTN_STATS. Replacing the member
// is safe here because this binary never mounts the FUSE tree, so no leaf
// callback holds the old object. The caller opens the forward.
static std::shared_ptr<attn_stats::model_stats> make_enabled_stats(
    heterogeneous_outer_state& state) {
  attn_stats::header_facts facts;
  facts.n_kv_heads = 1;
  facts.kv_mul = 1;
  facts.head_size = heterogeneous_scheduler_tp1::geometry_128.kv.head_size;
  facts.n_layers = heterogeneous_model::n_layers;
  constexpr bool STATS_ON_TRUE = true;
  constexpr bool NOT_EAGLE_FALSE = false;
  auto stats = std::make_shared<attn_stats::model_stats>(STATS_ON_TRUE,
      "heterogeneous-hw-config-test", NOT_EAGLE_FALSE, facts,
      state.self_attn_state.attn.size(), heterogeneous_model::n_layers);
  state.self_attn_state.stats = stats;
  return stats;
}

// make_enabled_stats plus an open decode_like forward of n_token_jobs jobs.
static std::shared_ptr<attn_stats::model_stats> install_enabled_stats(
    heterogeneous_outer_state& state, size_t n_token_jobs) {
  auto stats = make_enabled_stats(state);
  stats->begin_forward(attn_stats::forward_class::decode_like, n_token_jobs,
      /*n_listeners=*/n_token_jobs);
  return stats;
}

TEST_CASE("hardware attention configuration uses KV-slot identity", "[attention]") {
  REQUIRE(devices.empty());
  PosDevice device(hardware::process_device_id{0}, uint8_t{0}, uint8_t{0}, uint8_t{0},
      0, uint16_t{0x0100});
  device.num_fetchers = 32;
  device.id_dat_raw = 0;
  devices.push_back(&device);
  tron::finally pop_device([] { devices.pop_back(); });

  auto model = std::make_unique<heterogeneous_model>(
      std::filesystem::path{}, json(json::value_t::object));
  model_config cfg;
  cfg.max_layers = heterogeneous_model::n_layers;
  cfg.id = "heterogeneous-hw-config-test";
  auto state = std::make_unique<heterogeneous_outer_state>(*model, cfg);

  auto const& attention = state->self_attn_state;
  REQUIRE(attention.hw_attn_eligible);
  CHECK(attention.hw_attn_cfg.hw_kv_slots.count() == 1);
  CHECK(hardware::slot_uses_hw(attention.hw_attn_cfg, kv_slot_id(1)));
  CHECK_FALSE(hardware::slot_uses_hw(attention.hw_attn_cfg, kv_slot_id(0)));
  CHECK_FALSE(hardware::slot_uses_hw(attention.hw_attn_cfg, kv_slot_id(2)));
  CHECK(attention.hw_attn_kv_slot_extent == 2);
  CHECK(state->cached_operation_uses_hw(attention_op_id(1)));
  REQUIRE(state->dma_tracker);
  CHECK(state->dma_tracker->last_v_xfer.size() == 2);

  SECTION("mixed attention retains both contributions regardless of readiness order") {
    constexpr auto geometry = heterogeneous_scheduler_tp1::geometry_128;
    constexpr auto operation = heterogeneous_scheduler_tp1::attention_operations[1];
    heterogeneous_scheduler_state::intermediate_t<128> output;
    output.resize(2);
    state->resize(2);
    state->self_attn_state.hw_attn.resize(2);
    latch_arena latches;
    with_latch_arena latch_guard(latches);
    heterogeneous_model::batch q_batch(
        *state, {token_job_id(1), token_job_id(0)}, latches, 0);
    q_batch.reset_channels(0, 0);
    q_batch.plans.resize(state->attention_plan_profiles.size());
    auto& plan = state->self_attn_state.plan_for(&q_batch, operation.binding.operation);
    plan.n_sections = {0};
    plan.sections_left = std::vector<std::atomic_size_t>(1);
    plan.kv_heads_to_join.resize(1);
    plan.kv_heads_to_join[0].insert(0);
    plan.join_workers.resize(1);
    plan.join_workers[0].insert(0);
    q_batch.hw_plan.resize(2);
    for (size_t pi = 0; pi < 2; ++pi) {
      auto& pass = q_batch.hw_plan.passes[pi];
      pass.dev = pi == 0 ? &device : nullptr;
      pass.scratchpad_ix = hw_scratchpad_id(pi);
      pass.physical_subpasses = 1;
      for (size_t b = 0; b < q_batch.items.size(); ++b)
        pass.queries.push_back({q_batch.items[b], 0, b});
    }
    q_batch.hw_plan.index_passes_by_job(q_batch.items);

    // Both an empty worker-0 accumulator and a populated one must retain
    // every software contribution when hardware is folded into the result.
    // Equal maxima and these partials keep the sums and both expected means
    // exactly representable in the BF16 scratchpads.
    constexpr std::array<float, 4> values{0, 2, 4, 12};
    const bool worker_zero_valid = GENERATE(false, true);
    const bool hardware_first = GENERATE(false, true);
    CAPTURE(worker_zero_valid, hardware_first);
    state->self_attn_state.free_scratchpads<geometry>(&q_batch, operation);
    auto produce_software = [&] {
      for (size_t b = 0; b < q_batch.items.size(); ++b) {
        auto fill = [&](size_t worker) {
          auto partial =
              state->self_attn_state.token_scratchpad_ref_at<geometry>(worker, b);
          partial.mark_valid_for(0);
          partial[0].m_star = 0;
          partial[0].s_star = 1;
          partial[0].v_star.set(constant<128>(values[worker] + b));
        };
        if (worker_zero_valid) fill(0);
        fill(1);
      }
      plan.sections_left[0].store(0, std::memory_order_release);
    };
    for (size_t pi = 0; pi < 2; ++pi) {
      auto& scratchpad = state->self_attn_state.hw_attn[pi];
      for (size_t b = 0; b < q_batch.items.size(); ++b) {
        scratchpad.prepare_raw_result(q_batch.items[b]);
        auto* raw = scratchpad.raw_result(q_batch.items[b]).data.get();
        for (size_t i = 0; i < hardware::HW_BAKED_HEAD_SIZE; ++i)
          raw[i] = bf16(values[pi + 2] + b);
        const std::array<float, 2> auxiliary{0.0f, 1.0f};
        std::memcpy(
            raw + hardware::HW_BAKED_HEAD_SIZE, auxiliary.data(), sizeof(auxiliary));
      }
      q_batch.hw_plan.complete[pi].store(0);
    }
    auto produce_hardware = [&] {
      for (auto& complete : q_batch.hw_plan.complete)
        complete.store(hw_attention_completion_generation(operation.binding.operation),
            std::memory_order_release);
    };
    plan.sections_left[0] = 1;
    if (hardware_first)
      produce_hardware();
    else
      produce_software();
    // T5 of the hardware join: the worker below blocks in stream_hw_joins'
    // wait loop until the second producer runs, so its row must show a wait
    // that is bounded by the wall time of the whole join.
    auto stats = install_enabled_stats(*state, q_batch.items.size());
    constexpr bool STATS_ENABLED_TRUE = true;
    const uint64_t t_join_start = hardware::system::rdtsc();
    // The latch starts the 20 ms window at worker entry, not at std::async,
    // so a slow thread start cannot let the second producer run before the
    // worker's first pass. It narrows the window to a preemption between
    // lambda entry and that pass; it does not close it.
    std::latch joining(1);
    auto worker = std::async(std::launch::async, [&] {
      joining.count_down();
      state->self_attn_state.run_joins<geometry>(
          &q_batch, operation, output, 0, 2, true, STATS_ENABLED_TRUE);
    });
    joining.wait();
    bool hardware_progressed = false;
    if (hardware_first) {
      // Decoding must progress before SW readiness. Bound the wait and
      // always release the producer so a failure cannot hang the suite.
      auto const deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
      while (!(hardware_progressed =
                     state->self_attn_state.hw_attn[1].unpack_state[1].load(
                         std::memory_order_acquire) == 2) &&
             std::chrono::steady_clock::now() < deadline)
        std::this_thread::yield();
    }
    const auto waiting_for_other = worker.wait_for(std::chrono::milliseconds(20));
    if (hardware_first)
      produce_software();
    else
      produce_hardware();
    worker.get();
    const uint64_t join_wall = hardware::system::rdtsc() - t_join_start;
    if (hardware_first) CHECK(hardware_progressed);
    CHECK(waiting_for_other == std::future_status::timeout);
    {
      const auto sums =
          stats->sum_layer(static_cast<size_t>(attn_stats::forward_class::decode_like),
              operation.binding.model_layer.i);
      CHECK(sums.join_wait_cycles > 0);
      CHECK(sums.join_wait_cycles <= join_wall);
    }
    for (size_t b = 0; b < q_batch.items.size(); ++b) {
      const float expected = (worker_zero_valid ? 4.5f : 6.0f) + b;
      for (size_t i = 0; i < geometry.query_width(); ++i)
        CHECK(float(output[q_batch.items[b]].as_view()[i]) == expected);
    }
  }

  SECTION("software-only join times its wait for the peer sections (T5)") {
    // With no hardware plan, run_joins polls sections_left of its kv heads
    // until the peer workers' sections are done. T5 (join_wait_cycles) must
    // cover that poll: positive and bounded by the join's wall time when the
    // producer is late, zero when the sections are already done, and zero
    // when the stats flag of the call is off.
    constexpr auto geometry = heterogeneous_scheduler_tp1::geometry_128;
    constexpr auto operation = heterogeneous_scheduler_tp1::attention_operations[1];
    heterogeneous_scheduler_state::intermediate_t<128> output;
    output.resize(2);
    state->resize(2);
    latch_arena latches;
    with_latch_arena latch_guard(latches);
    heterogeneous_model::batch q_batch(
        *state, {token_job_id(1), token_job_id(0)}, latches, 0);
    q_batch.reset_channels(0, 0);
    q_batch.plans.resize(state->attention_plan_profiles.size());
    REQUIRE(q_batch.hw_plan.empty());  // no hardware plan: join_hw is false
    auto& plan = state->self_attn_state.plan_for(&q_batch, operation.binding.operation);
    plan.n_sections = {0};
    plan.sections_left = std::vector<std::atomic_size_t>(1);
    plan.kv_heads_to_join.resize(1);
    plan.kv_heads_to_join[0].insert(0);
    plan.join_workers.resize(1);
    plan.join_workers[0].insert(0);
    // Two software partials with equal maxima: the join is their mean.
    constexpr std::array<float, 2> values{0, 2};
    auto produce_software = [&] {
      for (size_t b = 0; b < q_batch.items.size(); ++b)
        for (size_t worker = 0; worker < 2; ++worker) {
          auto partial =
              state->self_attn_state.token_scratchpad_ref_at<geometry>(worker, b);
          partial.mark_valid_for(0);
          partial[0].m_star = 0;
          partial[0].s_star = 1;
          partial[0].v_star.set(constant<128>(values[worker] + b));
        }
      plan.sections_left[0].store(0, std::memory_order_release);
    };
    enum class arm {
      late_producer_stats_on,
      sections_done_stats_on,
      late_producer_stats_off
    };
    const arm which = GENERATE(arm::late_producer_stats_on, arm::sections_done_stats_on,
        arm::late_producer_stats_off);
    CAPTURE(static_cast<int>(which));
    const bool late = which != arm::sections_done_stats_on;
    const bool stats_enabled = which != arm::late_producer_stats_off;
    state->self_attn_state.free_scratchpads<geometry>(&q_batch, operation);
    auto stats = install_enabled_stats(*state, q_batch.items.size());
    plan.sections_left[0] = 1;
    if (!late) produce_software();
    const uint64_t t_join_start = hardware::system::rdtsc();
    // The latch starts the 20 ms window at worker entry (see the mixed
    // section above).
    std::latch joining(1);
    auto worker = std::async(std::launch::async, [&] {
      joining.count_down();
      state->self_attn_state.run_joins<geometry>(
          &q_batch, operation, output, 0, 2, /*uses_hw=*/false, stats_enabled);
    });
    joining.wait();
    if (late) {
      // The worker must still be polling after 20 ms; then release it.
      CHECK(worker.wait_for(std::chrono::milliseconds(20)) ==
            std::future_status::timeout);
      produce_software();
    }
    worker.get();
    const uint64_t join_wall = hardware::system::rdtsc() - t_join_start;
    const auto sums =
        stats->sum_layer(static_cast<size_t>(attn_stats::forward_class::decode_like),
            operation.binding.model_layer.i);
    if (late && stats_enabled) {
      CHECK(sums.join_wait_cycles > 0);
      CHECK(sums.join_wait_cycles <= join_wall);
    } else {
      CHECK(sums.join_wait_cycles == 0);
    }
    for (size_t b = 0; b < q_batch.items.size(); ++b) {
      const float expected = 1.0f + b;
      for (size_t i = 0; i < geometry.query_width(); ++i)
        CHECK(float(output[q_batch.items[b]].as_view()[i]) == expected);
    }
  }

  SECTION("prepare_hw_attention files the FPGA K tokens of a pass (note_fpga_pass)") {
    // Attention path stats: for every hardware pass, prepare_uniform_hw_attention
    // (self_attention.hpp) files under the operation's layer the K tokens the
    // FPGA card scores, summed over the pass's queries as the query's last
    // hardware token relative to the pass's shards, inclusive, plus one; and
    // the pass's query count. The three queries below take the three return
    // paths of that relative index: inside the first shard, inside the second
    // shard (not adjacent to the first, as round-robin device allocation
    // produces), and beyond every shard of the pass.
    constexpr auto geometry = heterogeneous_scheduler_tp1::geometry_128;
    constexpr auto operation = heterogeneous_scheduler_tp1::attention_operations[1];
    constexpr size_t DECODE_CLASS_0 =
        static_cast<size_t>(attn_stats::forward_class::decode_like);
    constexpr size_t N_JOBS_3 = 3;
    heterogeneous_scheduler_state::intermediate_t<128> queries;
    queries.resize(N_JOBS_3);
    state->resize(N_JOBS_3);
    state->self_attn_state.hw_attn.resize(1);
    latch_arena latches;
    with_latch_arena latch_guard(latches);
    heterogeneous_model::batch q_batch(
        *state, {token_job_id(0), token_job_id(1), token_job_id(2)}, latches, 0);
    q_batch.plans.resize(state->attention_plan_profiles.size());
    // Two shards of shard_tokens (1024) tokens each, at token 0 and at token
    // 2048, over the model's KV-slot extent. Their constructor allocates the
    // HBM regions of the hardware-enabled slots, which the pass reads for the
    // operation's KV slot.
    static_assert(hardware::shard_tokens == 1024);
    constexpr uint32_t SHARD_A_BASE_0 = 0;
    constexpr uint32_t SHARD_B_BASE_2048 = 2048;
    const uint32_t slot_extent = state->self_attn_state.hw_attn_kv_slot_extent;
    hardware::hw_attn_params const* hw_params = &state->self_attn_state.hw_attn_cfg;
    hardware::shard shard_a(&device, SHARD_A_BASE_0, slot_extent, hw_params);
    hardware::shard shard_b(&device, SHARD_B_BASE_2048, slot_extent, hw_params);
    for (hardware::shard const* sh : {&shard_a, &shard_b}) {
      REQUIRE_FALSE(sh->sw_fallback);
      REQUIRE(sh->kv_shard_slots()[operation.binding.kv_slot.i].allocation_bytes > 0);
    }
    // Last hardware token of each query and the K tokens it yields: token 5
    // lies in shard A (index 5, so 6 tokens); token 2050 lies in shard B
    // (1024 of A plus index 2, so 1027 tokens); token 5000 lies beyond both
    // (all 2048 local tokens). The sum is 3081.
    constexpr size_t LAST_POS_IN_A_5 = 5;
    constexpr size_t LAST_POS_IN_B_2050 = 2050;
    constexpr size_t LAST_POS_BEYOND_5000 = 5000;
    constexpr uint64_t K_TOKENS_SUM_3081 = 6 + 1027 + 2048;
    std::vector<hw_pass> passes(1);
    passes[0].dev = &device;
    passes[0].shards = {&shard_a, &shard_b};
    passes[0].scratchpad_ix = hw_scratchpad_id(0);
    passes[0].queries = {{token_job_id(0), LAST_POS_IN_A_5, 0},
        {token_job_id(1), LAST_POS_IN_B_2050, 1},
        {token_job_id(2), LAST_POS_BEYOND_5000, 2}};
    passes[0].last_hw_token_pos = LAST_POS_BEYOND_5000;
    q_batch.hw_plan.set_passes(std::move(passes), q_batch.items,
        [&](hw_pass const& pass, hw_query const& query) {
          state->self_attn_state.hw_attn_results_at(pass.scratchpad_ix)
              .prepare_raw_result(query.job_ix);
        });
    auto stats = install_enabled_stats(*state, N_JOBS_3);
    const auto& fpga = stats->fpga_at(DECODE_CLASS_0, operation.binding.model_layer.i);
    // An operation that does not use the hardware files nothing, plan or not.
    constexpr bool USES_HW_FALSE = false;
    state->self_attn_state.prepare_hw_attention<geometry>(
        &q_batch, operation, queries, USES_HW_FALSE);
    CHECK(attn_stats::load_relaxed(fpga.k_tokens) == 0);
    CHECK(attn_stats::load_relaxed(fpga.query_passes) == 0);
    // The pass, prepared twice: the counters add up per pass, under the
    // operation's layer only.
    constexpr bool USES_HW_TRUE = true;
    constexpr uint64_t PASSES_PREPARED_2 = 2;
    for (uint64_t prepared = 1; prepared <= PASSES_PREPARED_2; ++prepared) {
      state->self_attn_state.prepare_hw_attention<geometry>(
          &q_batch, operation, queries, USES_HW_TRUE);
      CHECK(attn_stats::load_relaxed(fpga.k_tokens) == prepared * K_TOKENS_SUM_3081);
      CHECK(attn_stats::load_relaxed(fpga.query_passes) == prepared * N_JOBS_3);
    }
    for (size_t layer = 0; layer < heterogeneous_model::n_layers; ++layer) {
      if (layer == operation.binding.model_layer.i) continue;
      CHECK(attn_stats::load_relaxed(stats->fpga_at(DECODE_CLASS_0, layer).k_tokens) ==
            0);
      CHECK(attn_stats::load_relaxed(
                stats->fpga_at(DECODE_CLASS_0, layer).query_passes) == 0);
    }
  }

  SECTION("Q reuse waits for software work and hardware completion per minibatch") {
    constexpr auto geometry = heterogeneous_scheduler_tp1::geometry_128;
    constexpr auto operation = heterogeneous_scheduler_tp1::attention_operations[1];
    using buffer_t = heterogeneous_scheduler_state::intermediate_t<128>;
    using channel_t = heterogeneous_scheduler_state::compile_channel_t<128>;
    buffer_t queries;
    buffer_t output;
    queries.resize(2);
    output.resize(2);
    state->resize(2);
    state->self_attn_state.hw_attn.resize(1);
    constexpr auto software_geometry = heterogeneous_scheduler_tp1::geometry_256;
    constexpr auto software_operation =
        heterogeneous_scheduler_tp1::attention_operations[2];
    heterogeneous_model::book book(1);
    book.increment_tokens_used();
    auto* page = book.page_of(0);
    page->set_lo(0, 0);
    page->set_offset_bound(1);
    // page::set_v takes one aligned, read-only source row.
    alignas(chunk_alignment) std::array<float, software_geometry.kv.head_size> values;
    values.fill(3.0f);
    page->set_v<software_geometry.kv>(software_operation.binding.kv_slot, 0, 0,
        v_source_row<software_geometry.kv.head_size>(values.data()));
    for (size_t i = 0; i < 256; ++i)
      page->k<software_geometry.kv>(software_operation.binding.kv_slot, 0, 0)[i] =
          bf16(0.0f);
    std::array<heterogeneous_model::page*, 1> pages{page};
    state->pages.items = std::span<heterogeneous_model::page* const>(pages);
    indexed_vector<token_job_id, token_id> tokens;
    tokens.push_back(token_id(0));
    tokens.push_back(token_id(0));
    state->token_jobs = tokens;
    // Attention path stats on, with the forward open for the whole section as
    // in production: the T2/T3/T4 hooks of run_attention_job run under an
    // enabled object and are read back below.
    auto stats = make_enabled_stats(*state);
    attn_stats::forward_scope stats_scope(
        *stats, attn_stats::forward_class::decode_like, tokens.size(), tokens.size());
    constexpr size_t DECODE_CLASS_0 =
        static_cast<size_t>(attn_stats::forward_class::decode_like);
    // Every batch runs two attention jobs on the one attention worker: the
    // hardware-assisted operation, then the software one.
    constexpr uint64_t JOBS_PER_BATCH_2 = 2;
    // The job of this batch, on top of the earlier batches.
    constexpr uint64_t ONE_JOB_1 = 1;
    // The last pool row is n_pool - 1.
    constexpr size_t LAST_ROW_BACK_1 = 1;
    // Row 0 and the last row must differ for the keying check.
    constexpr size_t MIN_ROWS_TO_DISCRIMINATE_2 = 2;
    const size_t n_pool = state->self_attn_state.attn.size();
    std::array<uint32_t, 1> positions{0};
    state->token_positions.items = positions;
    ranged_mask mask;
    mask_t<ranged_mask_capacity> visible;
    visible.insert(0);
    visible.insert(1);
    mask.add_range(token_id(0), token_id(1), visible, {});
    state->query_mask = &mask;
    heterogeneous_scheduler_state::intermediate_t<256> software_queries;
    heterogeneous_scheduler_state::intermediate_t<256> software_output;
    software_queries.resize(2);
    software_output.resize(2);
    for (size_t job = 0; job < 2; ++job)
      for (size_t i = 0; i < 256; ++i)
        software_queries[token_job_id(job)].as_view()[i] = bf16(0.0f);
    latch_arena latches;
    with_latch_arena latch_guard(latches);

    for (size_t batch_ix = 0; batch_ix < 2; ++batch_ix) {
      CAPTURE(batch_ix);
      const uint64_t hw_jobs_so_far = batch_ix + ONE_JOB_1;
      const token_job_id job(batch_ix);
      heterogeneous_model::batch q_batch(*state, {job}, latches, batch_ix);
      q_batch.reset_channels(1, 0);
      q_batch.plans.resize(state->attention_plan_profiles.size());
      auto& plan =
          state->self_attn_state.plan_for(&q_batch, operation.binding.operation);
      plan.ready_kv_plan.resize(1);
      plan.pending_kv_plan.resize(1);
      plan.work_estimate = {0.0f};
      plan.n_sections = {0};
      plan.sections_left = std::vector<std::atomic_size_t>(1);
      plan.kv_heads_to_join.resize(1);
      plan.kv_heads_to_join[0].insert(0);
      plan.join_workers.resize(1);
      plan.join_workers[0].insert(0);

      std::vector<hw_pass> passes(1);
      passes[0].queries = {{job, 0, 0}};
      passes[0].scratchpad_ix = hw_scratchpad_id(0);
      q_batch.hw_plan.set_passes(std::move(passes), q_batch.items,
          [&](hw_pass const& pass, hw_query const& query) {
            state->self_attn_state.hw_attn_results_at(pass.scratchpad_ix)
                .prepare_raw_result(query.job_ix);
          });
      auto& scratchpad = state->self_attn_state.hw_attn[0];
      auto* raw = scratchpad.raw_result(job).data.get();
      const float expected = static_cast<float>(batch_ix + 1);
      for (size_t i = 0; i < hardware::HW_BAKED_HEAD_SIZE; ++i)
        raw[i] = bf16(expected);
      const std::array<float, 2> auxiliary{0.0f, 1.0f};
      std::memcpy(
          raw + hardware::HW_BAKED_HEAD_SIZE, auxiliary.data(), sizeof(auxiliary));
      state->begin_attention_job<geometry>(&q_batch, operation, 0, 1);

      channel_t query_channel(queries, q_batch.items, latches, "queries", batch_ix);
      channel_t output_channel(output, q_batch.items, latches, "output", batch_ix);
      query_channel.reset(1, 1);
      output_channel.reset(1, 1);
      query_channel.prepare();
      output_channel.prepare();
      query_channel.start_writing(0);
      query_channel.finish_writing(0);
      q_batch.upstream_kvs_ready[operation.binding.kv_slot].reset(1);

      std::latch joins_started(1);
      observed_output_channel observed{output_channel, joins_started};
      auto worker = std::async(std::launch::async, [&] {
        state->run_attention_job<geometry>(
            &q_batch, operation, queries, query_channel, output, observed, 0, 1);
        state->finish_attention_job(&q_batch, 1);
      });
      auto reuse = std::async(std::launch::async, [&] { query_channel.prepare(); });
      const auto software_pending = reuse.wait_for(std::chrono::milliseconds(20));
      q_batch.upstream_kvs_ready[operation.binding.kv_slot].count_down();
      joins_started.wait();
      const auto hardware_pending = reuse.wait_for(std::chrono::milliseconds(20));

      // This is the existing POS completion boundary, held until Q reuse is probed.
      q_batch.hw_plan.complete[0].store(
          hw_attention_completion_generation(operation.binding.operation),
          std::memory_order_release);
      worker.get();
      reuse.get();
      output_channel.start_reading(0);
      output_channel.start_reading_all();
      for (size_t i = 0; i < geometry.query_width(); ++i)
        CHECK(float(output[job].as_view()[i]) == expected);
      output_channel.finish_reading(0);
      CHECK(software_pending == std::future_status::timeout);
      CHECK(hardware_pending == std::future_status::timeout);
      // T2 and T3 through run_attention_job (self_attention.hpp), cumulative
      // over the batches: the job is filed once under the pool worker that
      // ran it (attention worker 0 of a 1-worker split is the last pool
      // worker, Note [Attention workers are the last pool workers] in
      // model.hpp), never under row 0. T2 (busy) leaves out the upstream
      // K/V wait, which the 20 ms probe above makes real, while T3 (the
      // job's wall on worker 0) includes it, so T3 exceeds T2.
      {
        const auto layer =
            stats->sum_layer(DECODE_CLASS_0, operation.binding.model_layer.i);
        CHECK(layer.attn_jobs == hw_jobs_so_far);
        CHECK(layer.busy_cycles > 0);
        CHECK(layer.wall_cycles > layer.busy_cycles);
        CHECK(layer.wall_max_cycles <= layer.wall_cycles);
        // The max of two positive walls is below their sum.
        if (batch_ix > 0) CHECK(layer.wall_max_cycles < layer.wall_cycles);
        const uint64_t row_jobs_so_far = JOBS_PER_BATCH_2 * batch_ix + ONE_JOB_1;
        CHECK(stats->sum_worker(DECODE_CLASS_0, n_pool - LAST_ROW_BACK_1).attn_jobs ==
              row_jobs_so_far);
        if (n_pool >= MIN_ROWS_TO_DISCRIMINATE_2) {
          CHECK(stats->sum_worker(DECODE_CLASS_0, 0).attn_jobs == 0);
        } else {
          WARN("pool has one worker: the pool-row keying check cannot discriminate");
        }
      }

      // Dense operation order does not require ascending model-layer order.
      auto& software_plan = state->self_attn_state.plan_for(
          &q_batch, software_operation.binding.operation);
      software_plan.ready_kv_plan.resize(1);
      software_plan.pending_kv_plan.resize(1);
      software_plan.ready_kv_plan.assign_page(0, 0, page_id(0), {.scaled_vs = 1});
      software_plan.work_estimate = {1.0f};
      software_plan.n_sections = {1};
      software_plan.sections_left = std::vector<std::atomic_size_t>(1);
      software_plan.kv_heads_to_join.resize(1);
      software_plan.kv_heads_to_join[0].insert(0);
      software_plan.join_workers.resize(1);
      software_plan.join_workers[0].insert(0);
      state->begin_attention_job<software_geometry>(&q_batch, software_operation, 0, 1);
      heterogeneous_scheduler_state::compile_channel_t<256> software_q_channel(
          software_queries, q_batch.items, latches, "software queries", batch_ix);
      heterogeneous_scheduler_state::compile_channel_t<256> software_o_channel(
          software_output, q_batch.items, latches, "software output", batch_ix);
      software_q_channel.reset(1, 1);
      software_o_channel.reset(1, 1);
      software_q_channel.prepare();
      software_o_channel.prepare();
      software_q_channel.start_writing(0);
      software_q_channel.finish_writing(0);
      state->run_attention_job<software_geometry, 2>(&q_batch, software_queries,
          software_q_channel, software_output, software_o_channel, 0, 1);
      software_o_channel.start_reading(0);
      software_o_channel.start_reading_all();
      for (size_t i = 0; i < 256; ++i)
        CHECK(float(software_output[job].as_view()[i]) == 3.0f);
      software_o_channel.finish_reading(0);
      // T4 through run_attention_job: a layer's period closes at worker 0's
      // entry into the next operation's job. The hardware-assisted
      // operation's layer closes at the software operation's entry, once per
      // batch. The software operation's layer closes at the next batch's
      // entry into the hardware-assisted operation, so it is one behind.
      {
        const auto hw_layer =
            stats->sum_layer(DECODE_CLASS_0, operation.binding.model_layer.i);
        const auto sw_layer =
            stats->sum_layer(DECODE_CLASS_0, software_operation.binding.model_layer.i);
        CHECK(hw_layer.period_count == hw_jobs_so_far);
        CHECK(hw_layer.period_cycles > 0);
        CHECK(sw_layer.period_count == batch_ix);
        CHECK(sw_layer.attn_jobs == hw_jobs_so_far);
        CHECK(sw_layer.wall_cycles >= sw_layer.busy_cycles);
      }
    }
  }
}

TEST_CASE("model::state::forward files one whole attention path stats record per "
          "forward",
    "[attention]") {
  // The forward of model::state (model.hpp) owns the record of one forward
  // (attn_stats::forward_scope): the class, decided by whether every token
  // job has a listener; the token job, listener job and KV-only job counts;
  // the wall (T1); and the split noted by assemble_attention_plan. Every
  // stats-on test elsewhere opens the scope by hand, so this is the one
  // test that reads a record the production forward wrote. Same fixture as
  // the KV-slot case above: a fake device, no weights, the plugin's run
  // assembles the plan and prepares the logits. The live token count is
  // kept different from the token job count in both forwards, so a forward
  // that counted tokens instead of token jobs would file the wrong number.
  REQUIRE(devices.empty());
  PosDevice device(hardware::process_device_id{0}, uint8_t{0}, uint8_t{0}, uint8_t{0},
      0, uint16_t{0x0100});
  device.num_fetchers = 32;
  device.id_dat_raw = 0;
  devices.push_back(&device);
  tron::finally pop_device([] { devices.pop_back(); });

  auto model = std::make_unique<heterogeneous_model>(
      std::filesystem::path{}, json(json::value_t::object));
  model_config cfg;
  cfg.max_layers = heterogeneous_model::n_layers;
  cfg.id = "heterogeneous-forward-stats-test";
  auto state = std::make_unique<heterogeneous_outer_state>(*model, cfg);
  auto stats = make_enabled_stats(*state);
  constexpr size_t DECODE_CLASS_0 =
      static_cast<size_t>(attn_stats::forward_class::decode_like);
  constexpr size_t PROMPT_CLASS_1 =
      static_cast<size_t>(attn_stats::forward_class::prompt_or_mixed);
  attn_stats::forward_counters const& decode = stats->forwards[DECODE_CLASS_0];
  attn_stats::forward_counters const& prompt = stats->forwards[PROMPT_CLASS_1];

  // Four live tokens on one page. Every token job stores its K and V.
  constexpr size_t N_TOKENS_4 = 4;
  constexpr uint8_t DO_KV_1 = 1;
  constexpr uint8_t LIVE_GROUP_0 = 0;
  constexpr size_t ONE_NOTIFICATION_1 = 1;
  heterogeneous_model::book book(1);
  book.increment_tokens_used(N_TOKENS_4);
  auto* page = book.page_of(0);
  page->set_lo(0, 0);
  page->set_offset_bound(N_TOKENS_4);
  indexed_vector<page_id, heterogeneous_model::page*> pages;
  pages.push_back(page);
  indexed_vector<token_id, token_t> tokens;
  indexed_vector<token_id, uint32_t> positions;
  indexed_vector<token_id, heterogeneous_model::page*> token_pages;
  indexed_vector<token_id, token_batching_affinity_id> live_groups;
  for (size_t i = 0; i < N_TOKENS_4; ++i) {
    tokens.push_back(static_cast<token_t>(i));
    positions.push_back(static_cast<uint32_t>(i));
    token_pages.push_back(page);
    live_groups.push_back(token_batching_affinity_id(LIVE_GROUP_0));
  }
  indexed_vector<token_id, heterogeneous_model::activation_scalar const*> no_eagle_in;
  indexed_vector<token_id, heterogeneous_model::activation_scalar*> no_eagle_out;
  // The decode forward notifies its two listeners from two pool workers at
  // once (run_listener_notifications, one task per pool worker index).
  std::atomic<size_t> notified{0};
  // One forward: the given token jobs, with a listener (no logits buffer)
  // on each token of `listener_tokens`. Returns the forward's wall in TSC
  // cycles as the caller sees it.
  auto run_forward = [&](std::vector<token_id> const& job_tokens,
                         std::vector<token_id> const& listener_tokens) {
    indexed_vector<token_job_id, token_id> token_jobs;
    indexed_vector<token_job_id, uint8_t> token_jobs_do_kv;
    mask_t<ranged_mask_capacity> every_job;
    for (token_id tok : job_tokens) {
      every_job.insert(token_jobs.size());
      token_jobs.push_back(tok);
      token_jobs_do_kv.push_back(DO_KV_1);
    }
    ranged_mask mask;
    mask.add_range(token_id(0), token_id(N_TOKENS_4), every_job, {});
    indexed_vector<listener_id, token_id> listener_index;
    indexed_vector<listener_id, std::vector<logits_buffer_t>> listener_buffers;
    indexed_vector<listener_id, std::function<void()>> listener_notifications;
    for (token_id tok : listener_tokens) {
      listener_index.push_back(tok);
      listener_buffers.push_back({});
      listener_notifications.push_back([&notified] {
        notified.fetch_add(ONE_NOTIFICATION_1, std::memory_order_relaxed);
      });
    }
    const uint64_t t_start = hardware::system::rdtsc();
    state->forward(pages, tokens, positions, token_pages, live_groups, no_eagle_in,
        no_eagle_out, token_jobs, token_jobs_do_kv, listener_index, listener_buffers,
        listener_notifications, mask);
    return hardware::system::rdtsc() - t_start;
  };

  // decode_like: two token jobs, both with a listener. Two of the four live
  // tokens (0 and 3) are not jobs of this forward.
  constexpr uint64_t DECODE_JOBS_2 = 2;
  constexpr uint64_t N_ATTN_WORKERS_1 =
      heterogeneous_scheduler_tp1::RUN_N_ATTN_WORKERS_1;
  const uint64_t decode_wall =
      run_forward({token_id(1), token_id(2)}, {token_id(1), token_id(2)});
  CHECK(notified.load() == DECODE_JOBS_2);
  CHECK(attn_stats::load_relaxed(decode.forwards) == 1);
  CHECK(attn_stats::load_relaxed(decode.token_jobs) == DECODE_JOBS_2);
  CHECK(attn_stats::load_relaxed(decode.listener_jobs) == DECODE_JOBS_2);
  CHECK(attn_stats::load_relaxed(decode.kv_only_jobs) == 0);
  CHECK(attn_stats::load_relaxed(decode.wall_cycles) > 0);
  CHECK(attn_stats::load_relaxed(decode.wall_cycles) <= decode_wall);
  CHECK(attn_stats::load_relaxed(decode.n_attn_workers_min) == N_ATTN_WORKERS_1);
  CHECK(attn_stats::load_relaxed(decode.n_attn_workers_max) == N_ATTN_WORKERS_1);
  CHECK(
      attn_stats::load_relaxed(
          decode.token_jobs_by_path_set[attn_stats::PATH_BIT_NONE_0]) == DECODE_JOBS_2);
  CHECK(attn_stats::load_relaxed(prompt.forwards) == 0);
  CHECK(attn_stats::load_relaxed(prompt.token_jobs) == 0);

  // prompt_or_mixed: three token jobs, a listener on the last one only.
  constexpr uint64_t PROMPT_JOBS_3 = 3;
  constexpr uint64_t PROMPT_LISTENERS_1 = 1;
  const uint64_t prompt_wall =
      run_forward({token_id(1), token_id(2), token_id(3)}, {token_id(3)});
  CHECK(notified.load() == DECODE_JOBS_2 + PROMPT_LISTENERS_1);
  CHECK(attn_stats::load_relaxed(prompt.forwards) == 1);
  CHECK(attn_stats::load_relaxed(prompt.token_jobs) == PROMPT_JOBS_3);
  CHECK(attn_stats::load_relaxed(prompt.listener_jobs) == PROMPT_LISTENERS_1);
  CHECK(attn_stats::load_relaxed(prompt.kv_only_jobs) ==
        PROMPT_JOBS_3 - PROMPT_LISTENERS_1);
  CHECK(attn_stats::load_relaxed(prompt.wall_cycles) > 0);
  CHECK(attn_stats::load_relaxed(prompt.wall_cycles) <= prompt_wall);
  CHECK(attn_stats::load_relaxed(prompt.n_attn_workers_min) == N_ATTN_WORKERS_1);
  CHECK(attn_stats::load_relaxed(prompt.n_attn_workers_max) == N_ATTN_WORKERS_1);
  CHECK(
      attn_stats::load_relaxed(
          prompt.token_jobs_by_path_set[attn_stats::PATH_BIT_NONE_0]) == PROMPT_JOBS_3);
  CHECK(attn_stats::load_relaxed(decode.forwards) == 1);
  CHECK(attn_stats::load_relaxed(decode.token_jobs) == DECODE_JOBS_2);
}

TEST_CASE("Growing sliding storage preserves token-cache accounting",
    "[kv_data][fault_seam]") {
  // A wide sliding slot crosses the production chunk boundary in a short
  // logical book. pos_fake allocates this address space without initializing
  // the payload; the test touches only the saved prefix's K values.
  constexpr kv_geometry sliding_geometry{64, 1024};
  constexpr kv_geometry retained_geometry{1, 64};
  constexpr std::array slot_specs{
      kv_slot_spec{sliding_geometry, kv_slot_retention::sliding_window(128)},
      kv_slot_spec{retained_geometry, kv_slot_retention::full_history()},
  };
  using book_t = heterogeneous_kv_cache<slot_specs, 0>;
  using node_t = node<book_t>;
  token_cache_temporary_target_size target(std::numeric_limits<int64_t>::max());
  auto& cache = token_cache();
  int64_t const bytes_before = cache.size_bytes();
  int64_t const pinned_before = cache.cache_pinned_bytes();
  int64_t const opportunistic_before = cache.cache_opportunistic_bytes();
  int64_t const allocations_before = pos_heap_active_allocations();
  scheduler_metrics_t metrics;
  auto root = std::make_shared<node_t>(book_t::n_slots, book_t::n_slots, false);
  std::shared_ptr<node_base> prefix;
  std::shared_ptr<node_base> result;
  std::shared_ptr<node_base> retry_prefix;
  bool pinned = false;
  bool result_pinned = false;
  bool retry_prefix_pinned = false;
  std::optional<int64_t> all_book_bytes;
  token_pos_ht const saved_position(1);
  auto cleanup = [&] {
    hardware::test_seam::clear_dma_fault();
    if (result_pinned) {
      tree_lock lock;
      cache.release_node_locked(result);
      result_pinned = false;
    }
    result.reset();
    if (retry_prefix_pinned) {
      tree_lock lock;
      cache.release_node_locked(retry_prefix);
      retry_prefix_pinned = false;
    }
    retry_prefix.reset();
    if (pinned) {
      tree_lock lock;
      prefix->follow_tombstones()->_forget_pin_position_locked(saved_position);
      cache.release_node_locked(prefix);
      pinned = false;
    }
    prefix.reset();
    root.reset();
    cache.clear();
  };
  finally cleanup_guard(cleanup);
  hardware::test_seam::clear_dma_fault();
  prefix = cache.add_tokens(root, {42}, metrics);
  REQUIRE(prefix != nullptr);
  {
    tree_lock lock;
    prefix->_pin_at_locked(saved_position);
    pinned = true;
  }
  auto* book = static_cast<node_t*>(prefix.get())->parent_edge.kv_book.get();
  size_t const first_chunk_end = book->reclaimable_chunk_token_end(0);
  REQUIRE(book->token_capacity() > first_chunk_end);
  auto* page = book->page_of(0);
  test::set_k_tag<sliding_geometry>(*page, kv_slot_id(0), 0, 0, bf16(7.0f));
  test::set_k_tag<retained_geometry>(*page, kv_slot_id(1), 0, 0, bf16(9.0f));
  int64_t const initial_book_bytes = book->dma_size_bytes();

  SECTION("A successful append accounts for storage added to its pinned book") {
    result =
        cache.add_tokens(prefix, std::vector<token_t>(first_chunk_end, 7), metrics);
    REQUIRE(result != nullptr);
  }

  SECTION("Failed ephemeral growth still accounts for surviving persistent storage") {
    // Fill the existing logical book, then fail the next book's first DMA
    // allocation. The saved prefix keeps the expanded original book alive.
    auto const new_chunks = static_cast<int64_t>(book->reclaimable_chunk_count() - 1);
    hardware::test_seam::arm_dma_fault(new_chunks);
    result = cache.add_tokens(prefix, std::vector<token_t>(book->token_capacity(), 7),
        metrics, /*num_ephemeral=*/1);
    REQUIRE(result == nullptr);
  }

  SECTION("Allocation retry preserves an append when sibling eviction can compact") {
    // This continuation cannot fit in the parent's remaining capacity, so it
    // owns an evictable book. Its sibling will have a separate book too.
    auto sibling = cache.add_tokens(
        prefix, std::vector<token_t>(book->token_capacity(), 8), metrics);
    REQUIRE(sibling != nullptr);
    std::weak_ptr<node_base> evictable_sibling = sibling;
    {
      tree_lock lock;
      sibling->_pin_locked();
      cache.release_node_locked(sibling);
    }
    retry_prefix = cache.add_tokens(prefix, {9}, metrics);
    REQUIRE(retry_prefix != nullptr);
    {
      tree_lock lock;
      retry_prefix->_pin_locked();
      retry_prefix_pinned = true;
    }
    auto* retry_book =
        static_cast<node_t*>(retry_prefix.get())->parent_edge.kv_book.get();
    size_t const append_count = retry_book->token_capacity() - retry_book->size();
    size_t const initial_height = retry_prefix->abs_ht.i;
    test::set_k_tag<sliding_geometry>(
        *retry_book->page_of(0), kv_slot_id(0), 0, 0, bf16(11.0f));
    test::set_k_tag<retained_geometry>(
        *retry_book->page_of(0), kv_slot_id(1), 0, 0, bf16(13.0f));

    // Evicting the other child permits compaction into the parent's book.
    // Filling this book to capacity exposes any stale offset after relocation.
    hardware::test_seam::arm_dma_fault(0);
    result =
        cache.add_tokens(retry_prefix, std::vector<token_t>(append_count, 10), metrics);
    REQUIRE(result != nullptr);
    REQUIRE(result->abs_ht.i == initial_height + append_count);
    REQUIRE(evictable_sibling.expired());
    {
      tree_lock lock;
      result->_pin_locked();
      result_pinned = true;
      auto saved = follow_tombstones<book_t>(retry_prefix);
      size_t const index = saved->parent_edge.kv_first_entry_nr + initial_height - 1 -
                           saved->parent_edge.parent->abs_ht.i;
      auto* saved_page = saved->parent_edge.kv_book->page_of(index);
      size_t const row = index % book_t::page_size;
      REQUIRE(
          test::k_tag<sliding_geometry>(*saved_page, kv_slot_id(0), 0, row) == 11.0f);
      REQUIRE(
          test::k_tag<retained_geometry>(*saved_page, kv_slot_id(1), 0, row) == 13.0f);

      // Sum distinct resident books independently of the cache's byte ledger.
      // Compaction may validly change which book owns the retained prefix.
      all_book_bytes = 0;
      std::vector<book_t const*> counted;
      for (auto node = follow_tombstones<book_t>(result); !node->parent_edge.is_empty();
          node = node->parent_edge.parent) {
        auto* resident_book = node->parent_edge.kv_book.get();
        if (std::find(counted.begin(), counted.end(), resident_book) == counted.end()) {
          *all_book_bytes += resident_book->dma_size_bytes();
          counted.push_back(resident_book);
        }
      }
    }
  }

  int64_t const expected_book_bytes = all_book_bytes.value_or(book->dma_size_bytes());
  REQUIRE(expected_book_bytes > initial_book_bytes);
  REQUIRE(cache.size_bytes() - bytes_before == expected_book_bytes);
  REQUIRE(cache.cache_pinned_bytes() - pinned_before == expected_book_bytes);
  REQUIRE(cache.cache_opportunistic_bytes() == opportunistic_before);
  REQUIRE(test::k_tag<sliding_geometry>(*page, kv_slot_id(0), 0, 0) == 7.0f);
  REQUIRE(test::k_tag<retained_geometry>(*page, kv_slot_id(1), 0, 0) == 9.0f);
  {
    tree_lock lock;
    std::string error;
    REQUIRE(verify_tree(root, &error));
  }
  cleanup();
  REQUIRE(cache.size_bytes() == bytes_before);
  REQUIRE(cache.cache_pinned_bytes() == pinned_before);
  REQUIRE(cache.cache_opportunistic_bytes() == opportunistic_before);
  REQUIRE(pos_heap_active_allocations() == allocations_before);
}

template struct full_scheduler<model<heterogeneous_scheduler_tp1>>;
template struct full_scheduler<software_only_heterogeneous_model>;

}  // namespace tron

