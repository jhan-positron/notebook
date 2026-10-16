---
name: tron-tsc-timing-infra
description: "2026-09-25 verified (wf_a54ec608-f3a, 24 agents, 6/6 claims survived with wording fixes): how tron reads the TSC and saves timing records, which macros exist (perfetto TRACE_EVENT family + tron-owned TRON_CHECKPOINT), the decode-side idiom, and why PR 4596 keeps raw cycles + its own rows; recommendation: nothing required, optional init_cpu_freq_ref_value() in the model_stats ctor"
metadata:
  node_type: memory
  type: project
  originSessionId: 54307022-5593-4f51-b645-9a5329a5e08b
  modified: 2026-09-25T06:02:14.167Z
---

Answer to jhan's question (2026-09-25) "how does tron read the rtc and save records, I remember a simple
MACRO; should PR 4596 leverage that infra?" Verified against ~/workspace/ai-runs/tron-attn-stats @
cbf1bb6c0c; result JSON PR3879/new-PRs/new-counters/rtc-infra-wf_a54ec608.json.

The primitive (no macro):
- tron::hardware::system::rdtsc() = inline function, asm "rdtsc", unserialized (no rdtscp/lfence anywhere)
  [h/system/system.hpp:315-319]. cycles_to_ns / ns_to_cycles = one 64x64->128 multiply by a Q3.61 reciprocal
  (~5 cycles), TRON_ASSERT(cpu_frequency_hz != 0) [:267-285]; reciprocals refreshed by the tsc-calibration
  thread every 50 ms [src/system/system.cpp:1799-1818, 2016-2019]. tsc_in_ns() = get_corrected_ns(rdtsc(),
  get_cpu()) = TSC -> monotonic ns with per-core offsets [:288-330]. get_cpu_freq() returns 0 before
  calibration, no assert [system.cpp:1895-1899]. init_cpu_freq_ref_value() = idempotent system_init() that
  blocks until the frequency is published; the pos/heap metrics ctors call it [h/pos/metrics.hpp:36].
- struct cycle_stat {elapsed,min,max,count} plain uint64, only user t/t_mwaitx.cpp [system.hpp:190-208].

The macros:
- perfetto TRACE_EVENT family (TRACE_EVENT 139 uses = scoped span; BEGIN/END, INSTANT, TRACE_COUNTER 25).
  tron overrides two SDK-internal macros to AND in application_track_events_enabled() [h/common/perfetto.hpp:
  31-96]; gate = SDK category check in a live session, then tron's gate (default true, closed outside
  --trace-passes windows). Records go to a trace session, read from the file afterwards (rinzler: 10 s
  SIGUSR1 window, src/pos/perf.cpp:207-231). No span wraps run_attention_job (no T2/T3 span).
- TRON_CHECKPOINT = the one tron-owned macro that reads the TSC and saves a record: expands to
  monitor->record_checkpoint(handle, "file:line: text"), timestamp = tsc_in_ns(), into
  harvester<TokenStreamEvent> (per-CPU lock-free), drained by a monitor thread into FUSE TPS/TTFT
  [h/tron/generation/token_stream_monitor.hpp:43-48, :130, :528; src/rinzler/fuse-stats-monitor.cpp:264-297;
  caller src/tron/generation.cpp:62]. Keyed by generation handle, no layer/worker axis.
- Dormant #ifdef blocks around hand-written tsc_in_ns(): LOG_TOKEN_TIMES (runtron per-token ms line,
  h/runtron/stream_generate.hpp:51, :292-300) and EXECUTION_TIMERS (src/pos/worker.cpp:90, :359-370; dead if
  re-enabled: nothing writes timers[..][0]).

Decode side (model forward): locals with x -= rdtsc(); work; x += rdtsc(): main_elapsed -> main_time_estimator
.record_time [h/tron/plugins/llama.hpp:660, 694, 707]; attn_elapsed -> record_attention_time ->
attn_time_estimator [llama.hpp:761-775; model.hpp:2138-2147]; compute_elapsed -> speedometer.observe
[self_attention.hpp:820-839]. Consumers store floats (time_estimator = one prev_time; speedometer = Kalman
log-speed per worker). scheduler_metrics_t keeps a snapshot timestamp and converts with cycles_to_ns at
report time [full.hpp:216-225]. No per-layer or per-worker value survives on main.

PR 4596: every timestamp is rdtsc(); T2 reuses attn_elapsed; tsc_hz = get_cpu_freq() in the summary leaf;
net diff touches nothing under h/system (27c1a3a9d9 added an accessor, cbf1bb6c0c removed it). Extra reads
when on: +1 rdtsc in run_attention_job (8 -> 9), 2 per forward, and 2 per join-wait entry in stream_hw_joins
(T5, FPGA path, not covered by the CPU-attention A/A). Only T1 and T4 have cycle_stat's sum/count/max shape.

Recommendation (critic): nothing required. Optional: init_cpu_freq_ref_value() in the model_stats ctor so
tsc_hz is never 0 (today "0 until calibrated", untested); one Note sentence why cycles not ns (defensible
reasons = decode-path convention + no calibration dependency in the hooks; NOT "unit tests would trip the
assert": the PR's test binaries carry LABELS fake -> system_init runs). Do not adopt cycle_stat (non-atomic,
shape mismatch), TRON_CHECKPOINT (no layer/worker axis) or TRACE_EVENT (needs a session, no T2/T3 span).

**Why:** reviewers of PR 4596 may ask "why not the existing timer macro"; the true answer names two macros.
**How to apply:** say TRACE_EVENT for spans, TRON_CHECKPOINT for token-stream records; cite
llama.hpp:660/694 for the idiom. Related: [[attn-stats-pr-implementation]], [[attn-stats-why-not-fuse]],
[[attn-path-counters-design]].
