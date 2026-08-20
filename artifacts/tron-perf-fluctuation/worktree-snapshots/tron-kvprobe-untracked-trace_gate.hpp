#pragma once

#include <atomic>

namespace tron {

// Window gate for the perfetto-gated inter-fwd-pass capture (deep-dive
// runbook, 2026-08-12). ANDed into the emission macro overrides in
// common/perfetto.hpp on top of application_track_events_enabled(), so
// track events are emitted only between the last layer's post-attention
// OPEN and the next step's layer-0 entry CLOSE, decode batches only.
// Redundant stores from concurrent attention workers are intentional.
inline std::atomic<bool> g_trace_gate{false};

inline bool trace_gate_open() noexcept {
  return g_trace_gate.load(std::memory_order_relaxed);
}

inline void trace_gate_set(bool open) noexcept {
  g_trace_gate.store(open, std::memory_order_relaxed);
}

}  // namespace tron
