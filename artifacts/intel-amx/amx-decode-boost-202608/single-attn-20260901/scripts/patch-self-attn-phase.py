#!/usr/bin/env python3
"""Fence branch: add the attention phase probe (kvwait stamps 7606-7627) to
h/tron/models/self_attention.hpp by exact string replacement.
Idempotent: exits 0 with 'already patched' if namespace attn_phase exists.
Usage: patch-self-attn-phase.py [path]   (default: the fence worktree file)."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/jhan/workspace/ai-runs/tron-fence-amx/h/tron/models/self_attention.hpp"
s = open(P).read()
if "namespace attn_phase" in s:
    print("already patched"); sys.exit(0)

R = []  # (old, new) pairs; each old must occur exactly once

# S1: include the probe header (alphabetical slot after spdlog).
R.append(("""#include "spdlog/spdlog.h"
#include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free; used when TRON_AMX_DISPATCH
""", """#include "spdlog/spdlog.h"
#include <cstdlib>
#include "system/kvwait_probe.hpp"  // fence branch: attention phase probe (attn_phase)
#include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free; used when TRON_AMX_DISPATCH
"""))

# S2: counters, enable flag, TLS storage at namespace scope.
R.append(("""template <typename model>
struct self_attention {
  using plugin = model::plugin_t;
""", """// Fence-branch measurement: per-thread phase counters for the decode
// attention hot loop. Cycles are TSC ticks (hardware::system::rdtsc()).
// Worker 0 exports them once per token as kvwait stamps 7606 + index (see
// intel-AMX exec/fence-20260831/patch-gen-stamps.py); every worker resets
// them at the start of its run_attention_worker call.
namespace attn_phase {
enum idx : size_t {
  units_amx,             // 7606 apply_page_tok calls that took the AMX QK path
  units_dotter,          // 7607 dotter-path calls with relevant_k_tokens > 0
  units_empty,           // 7608 dotter-path calls with relevant_k_tokens == 0
  k_tokens_dotter,       // 7609 sum of relevant_k_tokens over dotter-path calls
  pages,                 // 7610 page-loop iterations in apply_page_range
  ranges,                // 7611 apply_page_range calls with a non-empty range
  qpacks,                // 7612 Q group packs (pack_q_*_128x4 calls)
  cyc_qk_amx,            // 7613 unit start .. QK kernel + s_pages copy done
  cyc_softmax_amx,       // 7614 scale/max/exp/sum/corr loop over the 4 heads
  cyc_pv_amx,            // 7615 weights_times_v_128x4 call
  cyc_state_amx,         // 7616 amx_o copy + v*/s*/m* update, 4 heads
  cyc_qk_dotter,         // 7617 unit start .. dotter loop done (empty units too)
  cyc_common_dotter,     // 7618 softmax pieces + v*/s*/m* update, all heads
  cyc_pv_dotter,         // 7619 page.scaled_v (PV product), all heads
  cyc_qpack,             // 7620 pack_q_*_128x4 calls
  cyc_region,            // 7621 amx_attn::begin_region + end_region
  cyc_range,             // 7622 apply_page_range wall, non-empty ranges
  cyc_sections_ready,    // 7623 run_sections(pending=false) wall
  cyc_sections_pending,  // 7624 run_sections(pending=true) wall
  cyc_upstream_wait,     // 7625 upstream_kvs_ready[slot].wait()
  cyc_joins,             // 7626 run_joins wall
  cyc_barrier,           // 7627 attn_done_barrier.arrive_and_wait
  n_counters
};
struct counters {
  uint64_t v[n_counters] = {};
};
inline thread_local counters tls;
// Read once at static initialization; every hot-loop check is one
// predictable branch on this bool. Needs BOTH the kvwait record file and
// TRON_ATTN_PHASE=1, so fence rounds that only want stamps 7600-7605 keep
// the hot loop free of the probe's rdtsc reads.
inline const bool enabled = kvwait_probe::state().enabled &&
    std::getenv("TRON_ATTN_PHASE") != nullptr &&
    std::getenv("TRON_ATTN_PHASE")[0] == '1';
}  // namespace attn_phase

template <typename model>
struct self_attention {
  using plugin = model::plugin_t;
"""))

# S3: accessors on self_attention::state (public members).
R.append(("""    enclosing_state_t& enclosing_state;
    // Scratchpads for parallel reduction in attention. One per app_pool worker.
    std::vector<attn_accum> attn;
""", """    // Fence-branch phase probe: the calling thread's counters. Generated
    // plugins call probe_reset() at the start of run_attention_worker (every
    // worker) and probe_take() from worker 0 after the last operation.
    static attn_phase::counters probe_take() noexcept {
      attn_phase::counters c = attn_phase::tls;
      attn_phase::tls = attn_phase::counters{};
      return c;
    }
    static void probe_reset() noexcept { attn_phase::tls = attn_phase::counters{}; }

    enclosing_state_t& enclosing_state;
    // Scratchpads for parallel reduction in attention. One per app_pool worker.
    std::vector<attn_accum> attn;
"""))

# S4: run_attention_job - sections / upstream wait / joins / barrier.
R.append(("""      attn_elapsed -= hardware::system::rdtsc();
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
      query_channel.finish_reading(worker_ix);
      output_channel.start_writing(worker_ix);

      run_joins<geometry>(
          outer_batch, operation, output, worker_ix, n_attn_workers, uses_hw);
      output_channel.finish_writing(worker_ix);
      outer_batch->free_scratchpads_barrier.done(worker_ix);
      post_attention();

      // Sync all the attention workers so worker 0 measures the whole operation.
      outer_batch->attn_done_barrier.arrive_and_wait(n_attn_workers);
      attn_elapsed += hardware::system::rdtsc();
      return attn_elapsed;
""", """      // Phase probe (fence branch): attn_elapsed and compute_elapsed keep
      // their exact meaning; the named timestamps only add the per-phase
      // sums for the calling thread.
      const bool probe = attn_phase::enabled;
      attn_phase::counters& pc = attn_phase::tls;
      const uint64_t t_ready0 = hardware::system::rdtsc();
      attn_elapsed -= t_ready0;
      uint64_t compute_elapsed = 0;
      compute_elapsed -= hardware::system::rdtsc();
      run_sections<geometry>(
          outer_batch, operation, queries, worker_ix, n_attn_workers, uses_hw, false);
      compute_elapsed += hardware::system::rdtsc();
      const uint64_t t_ready1 = hardware::system::rdtsc();
      attn_elapsed += t_ready1;
      if (probe) pc.v[attn_phase::cyc_sections_ready] += t_ready1 - t_ready0;

      // Wait for upstream K/V before running pending attention.
      // See Note [Minibatch Dependency Tracking].
      outer_batch->upstream_kvs_ready[binding.kv_slot].wait();

      const uint64_t t_pend0 = hardware::system::rdtsc();
      attn_elapsed -= t_pend0;
      if (probe) pc.v[attn_phase::cyc_upstream_wait] += t_pend0 - t_ready1;
      compute_elapsed -= hardware::system::rdtsc();
      run_sections<geometry>(
          outer_batch, operation, queries, worker_ix, n_attn_workers, uses_hw, true);
      compute_elapsed += hardware::system::rdtsc();
      if (probe)
        pc.v[attn_phase::cyc_sections_pending] += hardware::system::rdtsc() - t_pend0;
      tp.speedometer.observe(pool_worker_ix,
          plan_for(outer_batch, binding.operation).work_estimate[worker_ix],
          compute_elapsed);
      query_channel.finish_reading(worker_ix);
      output_channel.start_writing(worker_ix);

      const uint64_t t_join0 = probe ? hardware::system::rdtsc() : 0;
      run_joins<geometry>(
          outer_batch, operation, output, worker_ix, n_attn_workers, uses_hw);
      if (probe) pc.v[attn_phase::cyc_joins] += hardware::system::rdtsc() - t_join0;
      output_channel.finish_writing(worker_ix);
      outer_batch->free_scratchpads_barrier.done(worker_ix);
      post_attention();

      // Sync all the attention workers so worker 0 measures the whole operation.
      const uint64_t t_bar0 = probe ? hardware::system::rdtsc() : 0;
      outer_batch->attn_done_barrier.arrive_and_wait(n_attn_workers);
      const uint64_t t_end = hardware::system::rdtsc();
      if (probe) pc.v[attn_phase::cyc_barrier] += t_end - t_bar0;
      attn_elapsed += t_end;
      return attn_elapsed;
"""))

# S5a: apply_page_range - range wall start.
R.append(("""      if (page_range.empty()) return;
      int const sliding_window_size =
""", """      if (page_range.empty()) return;
      const bool probe = attn_phase::enabled;
      attn_phase::counters& pc = attn_phase::tls;
      const uint64_t t_range0 = probe ? hardware::system::rdtsc() : 0;
      int const sliding_window_size =
"""))

# S5b: begin_region + page count.
R.append(("""        amx_qpack.resize(items.size());
        amx_attn::begin_region();
      }
#endif
      for (page_id page_ix : page_range) {
""", """        amx_qpack.resize(items.size());
        const uint64_t t_reg0 = probe ? hardware::system::rdtsc() : 0;
        amx_attn::begin_region();
        if (probe) pc.v[attn_phase::cyc_region] += hardware::system::rdtsc() - t_reg0;
      }
#endif
      for (page_id page_ix : page_range) {
        if (probe) pc.v[attn_phase::pages]++;
"""))

# S5c: Q pack timing (both mirror and canonical packers sit between these anchors).
R.append(("""                static_assert(
                    amx_attn::query_scalar_ok<typename model::activation_scalar>,
                    "the AMX packers read q.data as bf16");
""", """                static_assert(
                    amx_attn::query_scalar_ok<typename model::activation_scalar>,
                    "the AMX packers read q.data as bf16");
                const uint64_t t_pack0 = probe ? hardware::system::rdtsc() : 0;
"""))
R.append(("""                amx_packed_mask[batch_job_ix >> 6] |= 1ull << (batch_job_ix & 63);
              }
""", """                amx_packed_mask[batch_job_ix >> 6] |= 1ull << (batch_job_ix & 63);
                if (probe) {
                  pc.v[attn_phase::cyc_qpack] += hardware::system::rdtsc() - t_pack0;
                  pc.v[attn_phase::qpacks]++;
                }
              }
"""))

# S5d: end_region + range wall end.
R.append(("""#ifdef TRON_AMX_DISPATCH
      if (amx_on) amx_attn::end_region();
#endif
#ifdef TRON_PAGE_SHARE_COUNTERS
      share_counters.flush();
#endif
#ifdef TRON_AMX_FALLBACK_COUNTERS
      fb_counters.flush();
      amx_fallback::tl = nullptr;
#endif
    }
""", """#ifdef TRON_AMX_DISPATCH
      if (amx_on) {
        const uint64_t t_reg1 = probe ? hardware::system::rdtsc() : 0;
        amx_attn::end_region();
        if (probe) pc.v[attn_phase::cyc_region] += hardware::system::rdtsc() - t_reg1;
      }
#endif
#ifdef TRON_PAGE_SHARE_COUNTERS
      share_counters.flush();
#endif
#ifdef TRON_AMX_FALLBACK_COUNTERS
      fb_counters.flush();
      amx_fallback::tl = nullptr;
#endif
      if (probe) {
        pc.v[attn_phase::cyc_range] += hardware::system::rdtsc() - t_range0;
        pc.v[attn_phase::ranges]++;
      }
    }
"""))

# S6a: apply_page_tok - unit start.
R.append(("""      tensor<operation_kv_mul, page::page_size> s_pages;
      int relevant_k_tokens = 0;
      bool did_amx = false;
      {
""", """      tensor<operation_kv_mul, page::page_size> s_pages;
      int relevant_k_tokens = 0;
      bool did_amx = false;
      // Phase probe (fence branch): t_u0 opens the unit; the QK phase also
      // covers the s_pages fill and dot_q construction below.
      const bool probe = attn_phase::enabled;
      attn_phase::counters& pc = attn_phase::tls;
      const uint64_t t_u0 = probe ? hardware::system::rdtsc() : 0;
      {
"""))

# S6b: end of QK (both paths), counts.
R.append(("""            for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
              s_pages[offset][i] = dot_q[offset](k);
            }
          }
        }
      }
      if (relevant_k_tokens == 0)
""", """            for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
              s_pages[offset][i] = dot_q[offset](k);
            }
          }
        }
      }
      uint64_t t_qk = 0;
      if (probe) {
        t_qk = hardware::system::rdtsc();
        if (did_amx) {
          pc.v[attn_phase::units_amx]++;
          pc.v[attn_phase::cyc_qk_amx] += t_qk - t_u0;
        } else {
          pc.v[relevant_k_tokens ? attn_phase::units_dotter : attn_phase::units_empty]++;
          pc.v[attn_phase::k_tokens_dotter] += static_cast<uint64_t>(relevant_k_tokens);
          pc.v[attn_phase::cyc_qk_dotter] += t_qk - t_u0;
        }
      }
      if (relevant_k_tokens == 0)
"""))

# S6c: AMX path - softmax end, PV end.
R.append(("""            corr_arr[offset] = was_valid ? std::exp(head_sp.m_star - m_page) : 0.f;
          }
          // See Note [Tile stores write 16 rows]: only rows 0..3 carry the
          // result.
          alignas(64) float amx_o[amx_attn::TILE_ROWS_16 * operation_head_size];
          amx_attn::weights_times_v_128x4(
              reinterpret_cast<const uint16_t*>(
                  page.template v_data<geometry.kv>(slot, kv_head)),
              &s_pages[0][0], page::page_size, amx_o);
          for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
""", """            corr_arr[offset] = was_valid ? std::exp(head_sp.m_star - m_page) : 0.f;
          }
          uint64_t t_sm = 0;
          if (probe) {
            t_sm = hardware::system::rdtsc();
            pc.v[attn_phase::cyc_softmax_amx] += t_sm - t_qk;
          }
          // See Note [Tile stores write 16 rows]: only rows 0..3 carry the
          // result.
          alignas(64) float amx_o[amx_attn::TILE_ROWS_16 * operation_head_size];
          amx_attn::weights_times_v_128x4(
              reinterpret_cast<const uint16_t*>(
                  page.template v_data<geometry.kv>(slot, kv_head)),
              &s_pages[0][0], page::page_size, amx_o);
          uint64_t t_pv = 0;
          if (probe) {
            t_pv = hardware::system::rdtsc();
            pc.v[attn_phase::cyc_pv_amx] += t_pv - t_sm;
          }
          for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
"""))

# S6d: AMX path - state end.
R.append(("""            head_sp.m_star = m_new_arr[offset];
          }
          return {relevant_k_tokens, range_hint};
""", """            head_sp.m_star = m_new_arr[offset];
          }
          if (probe) pc.v[attn_phase::cyc_state_amx] += hardware::system::rdtsc() - t_pv;
          return {relevant_k_tokens, range_hint};
"""))

# S6e: dotter path per-head loop. The only non-probe change: the eager
# scaled_v construction is named (`pv`) before the fma argument list.
R.append(("""      for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
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
      return {relevant_k_tokens, range_hint};
    }
""", """      uint64_t t_prev = t_qk;
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
        uint64_t t_sm = 0;
        if (probe) {
          t_sm = hardware::system::rdtsc();
          pc.v[attn_phase::cyc_common_dotter] += t_sm - t_prev;
        }
        // scaled_v is eager: its constructor writes the PV product into
        // `scratch` (scaled_v_expr in kv_cache.hpp). Naming it here only
        // moves that constructor ahead of the fma argument list; the inputs
        // (exp_s_minus_m, V page) and the arithmetic are unchanged.
        const auto pv =
            page.template scaled_v<geometry.kv>(slot, kv_head, exp_s_minus_m, scratch);
        if (probe) {
          t_prev = hardware::system::rdtsc();
          pc.v[attn_phase::cyc_pv_dotter] += t_prev - t_sm;
        }
        if (was_valid) {
          float exp_m_star_minus_m = std::exp(head_sp.m_star - m_page);
          auto exp_m_star_minus_m_ = constant<page::page_size>(exp_m_star_minus_m);
          head_sp.v_star.set(fma(head_sp.v_star, exp_m_star_minus_m_, pv));
          head_sp.s_star = head_sp.s_star * exp_m_star_minus_m + sum(exp_s_minus_m);
        } else {
          head_sp.v_star.set(pv);
          head_sp.s_star = sum(exp_s_minus_m);
        }
        head_sp.m_star = m_page;
      }
      if (probe) pc.v[attn_phase::cyc_common_dotter] += hardware::system::rdtsc() - t_prev;
      return {relevant_k_tokens, range_hint};
    }
"""))

for i, (old, new) in enumerate(R):
    n = s.count(old)
    assert n == 1, f"replacement {i}: anchor count {n}"
    s = s.replace(old, new)
open(P, "w").write(s)
print(f"patched {len(R)} sites in {P}")
