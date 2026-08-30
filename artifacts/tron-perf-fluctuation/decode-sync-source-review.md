# Decode Critical-Cut Source Review

**Scope:** steady-state, nonterminal decode for `ingested-qwen-3-4b-instruct-2507-tp4`,
`USE_HW_ATTN=0`, `--speculation 0`, `-u 1`  
**Source checkout:** `/home/jhan/workspace/tron-kvprobe`, commit `12804a812166`; line anchors refer
to the current worktree, which already contains the handoff's probe instrumentation  
**Method:** local static source analysis only. No Delphi machine, remote execution, or runtime
experiment was used.

Companion lane diagram: [decode-sync-lanes.html](/home/jhan/workspace/perf-fluctuation/deep-dive/from-codex/decode-sync-lanes.html)

## Bottom line

The synchronization-cut approach produces clearer targets than further timing decomposition.
I did **not** find a source-proven missing unlock, permanent missed wakeup, or circular wait in
the requested interval. I did find:

1. A **source-proven, pool-wide over-constraint**: with one logits listener, the implementation
   wakes and joins the entire application pool. In the recorded topology this means 70 listener
   tasks for one useful item; 69 do no listener work, but every one must acknowledge before the
   next forward pass can begin.
2. A **source-proven synchronous callback gate**: token selection, next-request enqueue, the
   runtron token callback, token decoding/printing, and (for the `n == 1` runtron case) a
   per-token `fflush(stdout)` all execute inside the useful listener task. The scheduler waits
   for that task before it can service the next request.
3. A **hard scheduler serialization boundary**: the next decode request is enqueued while the
   one global work-queue thread is still blocked inside the current `forward()`. A condition-
   variable notification cannot make that thread drain the request until full WCLS completion
   and all listener acknowledgements have completed.
4. A **language-level under-constraint** in the app-pool wakeup path: its doorbell is shared as
   a raw `volatile uint64_t`, read and modified concurrently. `volatile` is not C++ inter-thread
   synchronization. The 10 microsecond retry bounds a lost notification in practice, but the
   access is still a data race/undefined behavior and can turn a queue wake into latency jitter.
5. An **external-writer publication gap**: the WCLS consumer spin-polls a plain 16-bit word written
   by DMA, without a visible compiler/external-read primitive or acquire/DMA-read barrier before
   consuming the payload. Several POS ring handoff counters have the same `volatile`, non-atomic
   cross-thread problem.
6. An **intentional measurement barrier** makes every attention worker rendezvous after every
   layer solely so worker 0 can time the whole operation. At layer 35 it duplicates the subsequent
   plugin-wide worker join.
7. Two more latency gates worth separating: inline global token-tree cleanup under `tree_lock`,
   and the scheduler's wait for the WCLS full-completion callback even though the useful listener
   consumes streamed blocks independently.

The strongest immediate suspect is therefore not an increasingly small compute leaf. It is the
**one-token continuation being coupled to a pool-wide fanout, synchronous output callback, full
hardware-completion fence, and one globally serialized scheduler**.

## Exact boundary and exclusions

The phrase “end of attention” has two distinct source boundaries, both shown in the diagram:

- **Data boundary:** each last-layer attention worker publishes its joined output with
  `output_channel.finish_writing(worker_ix)`. Once the fallback channel reaches zero, the already-
  launched W_O job can consume `sdpa`. See
  [self_attention.hpp:830](/home/jhan/workspace/tron-kvprobe/h/tron/models/self_attention.hpp:830)
  and, specifically, lines 893–900.
- **Worker-retirement boundary:** those workers then rendezvous at
  `attn_done_barrier.arrive_and_wait(n_attn_workers)` at lines 902–910. This barrier does not
  publish W_O data and the W_O path can overlap it.

The endpoint is the first layer-0 Q of the **next** forward pass becoming readable by an attention
worker: return from `query_channel.start_reading_at(0)` at
[self_attention.hpp:850](/home/jhan/workspace/tron-kvprobe/h/tron/models/self_attention.hpp:850).
The generated next-pass producer path begins at
[qwen generated plugin:1723](/home/jhan/workspace/tron-kvprobe/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp:1723),
launches layer-0 WQ at lines 1755–1774, publishes normalized/RoPE Q at lines 1795–1803, and the
layer-0 attention worker consumes it at generated lines 7712–7714.

Explicitly excluded:

- The `!prompt_processed` branch at
  [context.cpp:38](/home/jhan/workspace/tron-kvprobe/src/tron/generation/context.cpp:38), so prompt
  chunking and prefill are outside this review.
- `speculation_context` / EAGLE. With `--speculation 0`, continuation uses
  `stream_generation_context::loop()` at
  [context.cpp:22](/home/jhan/workspace/tron-kvprobe/src/tron/generation/context.cpp:22).
- Hardware attention. Q/K/V, W_O, MLP, and WCLS accelerator matmuls remain in scope because they
  are on the software-attention decode dependency path; only attention math itself is CPU-side.
- Terminal-token and cancellation branches. The traced continuation is the ordinary
  `should_stop == false` branch at context.cpp lines 227–248.

## Threads in the interval

Let `P = app_pool().num_workers()`, `H = n_main_helpers`, and `A = P - H`.
The prior source/configuration map records `P = 70`. For this one-live-token,
`--pay-for-determinism` workload, the generated plugin's main parallelism is capped at one, so
`H = 1` and `A = 69` absent an environment override. The split and cap are at
[model.hpp:2012](/home/jhan/workspace/tron-kvprobe/h/tron/models/model.hpp:2012) and
[generated plugin:7824](/home/jhan/workspace/tron-kvprobe/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp:7824).

| Lane | OS threads | Role in this interval |
|---|---:|---|
| Global scheduler / work queue | 1 | Runs model main/orchestration synchronously, waits for plugin workers and logits, then mutates the token tree and starts the next pass. There is one global worker for all executors. |
| App-pool attention role | 69 of the same 70 workers in this workload | Finishes layer 35, publishes `sdpa`, passes the attention barrier, then counts down `workers_done`. |
| App-pool main-helper role | worker 0 in this workload | Completes W_O residual/RMS, gate/up join, SwiGLU, down projection residual, and final norm. |
| App-pool useful listener role | normally worker 0 for `u1` | Prepares the one WCLS stream, spin-consumes blocks, selects a token, enqueues the continuation, runs the output callback, and performs listener-pin cleanup. |
| App-pool empty listener role | workers `1..P-1` for `u1` | Waits on `logits_allocated`, finds no assigned listener, then acknowledges `logits_free` and `listeners_notified`. No work stealing exists. |
| POS TX | 4, one per TP card | Dequeues each matmul, may take `wcmd_post_mutex`, waits `act_ready` and device capacity, then submits activation DMA. |
| POS RX | 4, one per TP card | Polls result descriptors, exposes streamed result blocks in memory, performs completion cleanup, and invokes the shared completion callback. |
| FPGA + DMA | 4 device paths, not CPU threads | Executes W_O/MLP/WCLS/current pass and WQ/K/V/next pass; DMA overwrites the prepared NaN sentinels consumed by the listener. |

The app-pool “attention,” “helper,” and “listener” rows are time-multiplexed roles of the same `P`
OS threads. The plugin joins all helper/attention roles before those threads are reused for logits
delivery. Source: generated plugin lines 1728–1754 and 6690–6692, plus
[model.hpp:1753](/home/jhan/workspace/tron-kvprobe/h/tron/models/model.hpp:1753).

## Synchronization inventory

The labels match the companion diagram.

| ID | Synchronization / owner | Waiters or consumers | Necessary dependency and audit result |
|---|---|---|---|
| S1 | Last-layer `sdpa_channel.finish_writing()` by all attention workers | W_O launcher's activation wait | Necessary data-ready edge. It is distinct from the following attention barrier. |
| S2 | `attn_done_barrier` across `A` attention workers | Attention workers only | Barrier is used to retire/measure the attention operation. It does not release W_O. No mismatch found. |
| S3 | W_O, gate/up, and down result channels, completed from RX shared callbacks | Scheduler-main plus `H` helpers | Necessary result-readiness edges. The generated channel choreography is balanced in the inspected path. |
| S4 | `workers_done`, initialized to `H + A = P` | Scheduler thread in generated `run()` | Required today because `final_embedding` and the pool itself are reused immediately. It is a full plugin fence. |
| S5 | Per-worker app-pool queue doorbell | Exact targeted pool worker | **Under-constrained:** raw volatile shared state, not an atomic. No work stealing; a delayed exact worker cannot be rescued. |
| S6 | `logits_allocated`, count 1 | All `P` listener tasks | Publication of stream objects is necessary, but waking all `P` workers for one listener is not. |
| S7 | `logits_prepared`, reset to useful items in the chunk | Scheduler | Necessary: WCLS must not overwrite sentinel words before the consumer prepares them. For `u1`, only worker 0 contributes. |
| S8 | TX `wcmd_post_mutex`, `act_ready`, slot/in-flight/FIFO capacity gates | Each card's TX thread | Real host synchronization inside the old P5→P6 interval. No missing release found; the old report incorrectly treated the whole interval as card execution. |
| S9 | Per-block NaN sentinel overwrite by DMA; listener spin-polls `try_consume()` | Useful listener worker | Streaming data-ready protocol. It is a polling dependency, not the RX completion callback. |
| S10 | Shared final RX callback counts down `logits_done` | Scheduler | Full-job/lifetime fence. Scheduler always waits it even when the stream consumer has obtained the usable sparse logits. Potential over-constraint, but relaxing it requires launcher/result lifetime redesign. |
| S11 | `sequence_prompt()` enqueues under `model_mutex`, then `model_cv.notify_one()` | Global scheduler worker | Correct predicate-based CV use. Notification occurs while the only consumer is still inside current `forward()`, so it cannot advance the next request yet. |
| S12 | runtron `on_tokens` callback; for `n == 1`, token decode/print and `fflush(stdout)` | Runs inline on useful listener worker | **Over-constrained:** output delivery is inside the model continuation fence. The next request was enqueued first, but cannot run until this callback returns. |
| S13 | Global `tree_lock` in `ensure_listener` to unpin/coalesce | Useful listener worker | Lock is deliberately not held by scheduler across `state.forward()`, so no cycle was found. Cleanup nevertheless gates the listener acknowledgement. |
| S14 | `logits_free` and `listeners_notified`, both initialized to `P` | Scheduler waits `listeners_notified`; later chunks would wait `logits_free` | **Strongest over-constraint:** for `u1`, `P-1` empty tasks still contend and are mandatory. `logits_free` is not consumed with a single chunk, but still receives all `P` countdowns. |
| S15 | Work-queue drain plus global `tree_lock` in `extend_request` / `compute_forward_args` | Single scheduler worker | Serializes next-token tree mutation and next-pass construction. A queued node release can add unpin/coalesce/evict work before the continuation. |
| S16 | Next-pass WQ result channel, CPU Q normalization/RoPE channel | Layer-0 attention workers | Necessary data-ready edge; return from Q channel wait is the requested endpoint. |

The core latch primitive uses atomic acquire/release countdowns, and the work-queue CV waits with a
predicate. Those pieces do not show a lost-wakeup pattern:
[threading.hpp:124](/home/jhan/workspace/tron-kvprobe/h/tron/threading.hpp:124) and
[work_queue.hpp:316](/home/jhan/workspace/tron-kvprobe/h/tron/scheduler/work_queue.hpp:316).

## Findings, ranked

### F1 — One useful listener creates a `P`-worker thundering herd and `P`-way join

**Classification:** source-proven over-constraint; highest-priority target.

`init_logits_chunk_size()` defaults to the full app-pool width at
[model.hpp:76](/home/jhan/workspace/tron-kvprobe/h/tron/models/model.hpp:76). After plugin completion,
`run_forward()` enqueues exactly that many targeted tasks at model.hpp lines 1790–1795. The latches
`logits_free` and `listeners_notified` are also initialized to that full width at lines 1978–1997.

Every task waits `logits_allocated` at lines 3115–3127. Work assignment then starts at
`offset = worker_ix`; with one listener, only worker 0 enters the prepare/fill/callback loops at
lines 3128–3176. Nevertheless, every worker decrements both latches at lines 3178–3180, and the
scheduler cannot return until `listeners_notified.wait()` at lines 3082–3083.

Consequences for the recorded `P = 70` topology:

- 70 exact-worker queue wakeups per token for one useful listener;
- 69 tasks wake, wait, and retire without processing a listener;
- 70 writers contend on the same two latch cache lines;
- the slowest of all 70 exact worker queues can gate the next token;
- because the pool explicitly has no work stealing, another idle worker cannot complete a delayed
  acknowledgement.

The intended worker count should be bounded by useful listener parallelism. A minimal code design is
to introduce `n_delivery_workers = min(logits_chunk_size, n_listeners)` (with the zero-listener case
handled explicitly), enqueue only those workers, and size `listeners_notified` / `logits_free` to
that count. For this exact workload the existing `TRON_MAX_LOGITS_CHUNK_SIZE=1` setting already
selects the one-worker topology and is a clean future causal check; no machine test was run here.

### F2 — Per-token output I/O is inside the scheduler's continuation fence

**Classification:** source-proven over-constraint; high-priority target for this runtron workload.

The useful listener invokes the generation callback inline at model.hpp lines 3167–3176. Ordinary
decode samples at
[context.cpp:122](/home/jhan/workspace/tron-kvprobe/src/tron/generation/context.cpp:122), enqueues
the next `sequence_prompt()` at lines 227–238, and then synchronously calls `on_tokens_callback()`
at lines 241–248.

For runtron, `n == 1` sets `report_progress = true` at
[stream_generate.hpp:723](/home/jhan/workspace/tron-kvprobe/h/runtron/stream_generate.hpp:723).
The callback calls `report_token_batch()` at lines 770–817. With a tokenizer, `report_token()`
decodes and prints the token and calls `fflush(stdout)` at
[stream_generate.hpp:267](/home/jhan/workspace/tron-kvprobe/h/runtron/stream_generate.hpp:267),
lines 274–303.

Although the next request is enqueued before the print/flush, the work-queue thread is still blocked
in current `forward()` and waits for this listener. Thus stdout latency, tokenization, vector growth,
the API callback, and listener cleanup all sit directly between tokens. Benchmark progress output
should be buffered/disabled, or output delivery should be copied and decoupled from model progress.

This is more than a performance surprise: the public API says callbacks “can block if desired
without stalling the generation process” at
[libtron.hpp:293](/home/jhan/workspace/tron-kvprobe/h/libtron.hpp:293), lines 293–310. The actual
decode path violates that documented contract because `listeners_notified` cannot release while the
callback is blocked.

### F3 — The next request wakes a scheduler that cannot service it

**Classification:** source-proven serialization; architectural over-constraint.

The work queue intentionally has one global consumer and guarantees that no executor runs
concurrently with another at
[work_queue.hpp:33](/home/jhan/workspace/tron-kvprobe/h/tron/scheduler/work_queue.hpp:33).
`sequence_prompt()` enqueues the next `extend_request` at
[full.cpp:423](/home/jhan/workspace/tron-kvprobe/src/tron/scheduler/full.cpp:423). The mutex/CV
implementation is conventional, but the worker that must receive the notification is synchronously
inside `state.forward()` at
[full.hpp:1494](/home/jhan/workspace/tron-kvprobe/h/tron/scheduler/full.hpp:1494), lines 1614–1618.

That call cannot return until the scheduler observes full WCLS completion and every listener task.
Only then can `do_work()` swap the newly queued request, mutate the tree, build forward arguments,
and launch the next pass. This precludes useful overlap between current-pass cleanup/output and
next-pass request preparation.

A larger redesign would split “logits are usable and continuation is enqueued” from “all hardware
and callback-owned storage is safe to reuse,” allowing the global scheduler to prepare or dispatch
the continuation without violating object lifetimes.

### F4 — App-pool queue wakeup uses a non-atomic doorbell

**Classification:** source-proven C++ data race / under-constrained synchronization; causal weight
unknown from source alone.

At [threading.hpp:723](/home/jhan/workspace/tron-kvprobe/h/tron/threading.hpp:723), each exact-worker
queue stores `volatile uint64_t doorbell`; the producer performs `doorbell += 1`, while the worker
reads it and passes its address to the wait primitive. A volatile object does not establish a C++
happens-before edge, and the read/write pair is a data race. The concurrent queue safely publishes
the task itself, but it does not make the separate doorbell race valid.

The worker retries after `timeout_ns = 10000`, so an ineffective notification is not expected to
deadlock permanently. It can, however, add a bounded scheduling tail—especially when F1 creates
dozens of exact-worker wakes per token. Replace the doorbell with an atomic counter and make the
wait primitive consume an atomic readiness source with release increment / acquire observation.

### F5 — WCLS readiness is polled through ordinary memory written by DMA

**Classification:** source-level external-agent ordering defect; plausible streamed-logits risk.

`stream_result_t::prepare()` stores a `0xffff` sentinel through a plain `uint16_t*`, and
`try_consume()` repeatedly reads the same plain object while DMA changes it at
[libpos.hpp:202](/home/jhan/workspace/tron-kvprobe/h/libpos.hpp:202), lines 210–237. The caller is an
empty spin loop at model.hpp lines 3206–3215. No volatile/external-read primitive, compiler barrier,
atomic acquire, or platform DMA-read barrier is visible before it consumes the preceding payload.

An accelerator DMA write is outside the normal C++ thread model, so the platform may provide cache
coherence, but the compiler and payload-ordering contract still needs to be expressed. The current
optimized TP4 binary reportedly reloads the word each poll, so this review does **not** claim a
current infinite loop. It does establish fragile/under-specified synchronization exactly inside the
streamed-logits segment. Use a supported DMA readiness accessor plus the platform's payload read
barrier and validate the generated load.

### F6 — The attention timing barrier creates a convoy and duplicates the final join

**Classification:** source-proven intentional over-constraint.

After publishing attention output and releasing scratchpad use, every attention worker executes
`attn_done_barrier.arrive_and_wait(n_attn_workers)` at self_attention.hpp lines 893–910. The source
comment says this exists so worker 0 measures the whole operation. The generated plugin separately
joins every attention/helper task via `workers_done` before returning at generated lines 1742–1754
and 6690–6692.

At layer 35, the barrier therefore supplies neither output readiness nor final lifetime safety; it
duplicates the imminent plugin-wide join and can convoy 69 workers. Across earlier layers, removal
needs a channel/scratchpad phase audit, but per-worker completion stamps followed by an offline max
would preserve measurement without holding fast workers.

### F7 — Token-tree maintenance is synchronous with useful-listener completion

**Classification:** source-proven critical-path work; contention/causal magnitude unknown.

After the generation callback returns, `ensure_listener` takes the global `tree_lock`, drops the
listener pin, and may coalesce the node at
[full.hpp:1651](/home/jhan/workspace/tron-kvprobe/h/tron/scheduler/full.hpp:1651), lines 1658–1685.
This is correctly placed outside any scheduler-held `tree_lock`, so the audited path has no lock
cycle. It is still before the listener's `listeners_notified.count_down()`.

When an old sequence-tip reference expires, a worker-thread `node_release_request` may additionally
unpin, coalesce, hold/evict under the same global lock before the next continuation is extended:
[full.cpp:190](/home/jhan/workspace/tron-kvprobe/src/tron/scheduler/full.cpp:190) and
[token_cache.cpp:472](/home/jhan/workspace/tron-kvprobe/src/tron/scheduler/token_cache.cpp:472).
Pin correctness must be preserved, but coalescing/eviction policy work is a candidate for deferred or
batched maintenance rather than a per-token latency fence.

### F8 — Stream usability and full WCLS completion are joined

**Classification:** source-proven wait; potential over-constraint that is correctness-required by
current object reuse.

The useful listener prepares NaN sentinels and then independently spin-consumes streamed output at
model.hpp lines 3128–3165 and 3204–3219. The scheduler nevertheless always waits
`logits_done[logit_chk]` at lines 3074–3080. That latch is released by the last shared RX completion
callback, after RX descriptor handling and cleanup, not by each block becoming consumable.

The current comment says the launcher field is reused, so simply deleting the wait would be unsafe.
The design opportunity is double buffering or job-owned launcher/result lifetime, not an unchecked
wait removal.

### F9 — POS cross-thread/device publication also relies on `volatile` ordinary memory

**Classification:** source-proven C++ races / external-agent ordering gaps; lower-confidence direct
fluctuation hypothesis.

The per-device `prepare_tail`, `launch_tail`, and `rx_head` fields are declared `volatile`, not atomic,
at [device.hpp:370](/home/jhan/workspace/tron-kvprobe/h/pos/device.hpp:370). TX increments
`launch_tail` after the DMA kick while RX tests it and consumes the corresponding `rx_entry` at
[worker.cpp:322](/home/jhan/workspace/tron-kvprobe/src/pos/worker.cpp:322). There is no C++
release/acquire handoff for that publication. RX also repeatedly reads the FPGA-updated completion
head as ordinary memory before using results.

Aligned volatile access on the present x86 system may mask this in the current binary, but it is not
a valid language-level synchronization contract. Functional host-to-host tails should be atomics
with release publication/acquire observation; MMIO/device-owned state should use the project's
explicit DMA/MMIO accessors and required barriers. No cross-card global mutex was found: the
inspected `wcmd_post_mutex` and preparation mutexes are per device.

## Correction to the existing handoff interpretation

The prior timing artifacts are useful localization evidence, but several lane labels are not faithful
to the current source:

- `fill_logits_buffer`, sampling, and token callbacks execute on an app-pool listener worker, not
  on the global work-queue thread. Combining those lanes hides the key rendezvous.
- Probe P5 is stamped at `tx_launch` **entry**, before `wcmd_post_mutex`, command-capacity waits,
  `act_ready`, slot/in-flight waits, and actual DMA submission. Probe P6 is stamped only after RX
  completion handling and callback invocation. Therefore P5→P6 is not pure “card execute + DMA”
  and cannot exonerate host synchronization.
- Probe 7100 is a host `logits_allocated` latch released before WCLS launch, not a card allocation
  response.
- P1/P2/P3 observe attention worker 0 only, so they cannot characterize waits of all attention
  workers.
- The probe record has no thread, request, forward-pass, or prefill/decode identity. The old
  decode-only filter is positional. This review avoids that ambiguity by following only the static
  steady-state decode branch.

The relevant probe placements are in
[self_attention.hpp:850](/home/jhan/workspace/tron-kvprobe/h/tron/models/self_attention.hpp:850),
[worker.cpp:2127](/home/jhan/workspace/tron-kvprobe/src/pos/worker.cpp:2127),
[worker.cpp:610](/home/jhan/workspace/tron-kvprobe/src/pos/worker.cpp:610), and model.hpp lines
3119–3176.

## Recommended source-first sequence

1. Treat F1 as the first target. Make logits-delivery worker/latch cardinality equal useful
   parallelism, with a one-listener fast path.
2. Remove runtron per-token `fflush` from measured generation and separate output delivery from the
   model listener fence where API lifetimes permit.
3. Make the app-pool doorbell and host-to-host POS tail publications atomic; express DMA sentinel
   and completion-head observation through the platform's supported external-read/barrier contract.
4. Add source instrumentation only at synchronization ownership boundaries—not smaller compute
   leaves—with decode/pass ID and thread ID: enqueue→worker-start for each listener task, last empty
   acknowledgement, useful callback subphases, `logits_done`, scheduler forward-return, tree-lock
   acquire/hold, next extend begin/end, and next Q-ready.
5. Replace the timing-only attention barrier with non-blocking per-worker completion measurement,
   starting with the redundant final-layer barrier.
6. If a remaining gap exists, redesign WCLS completion lifetime and defer/batch token-tree policy
   maintenance. These are larger changes and should follow the low-risk cardinality/I/O fixes.

This sequence directly tests whether broad synchronization scope, rather than one slow leaf task,
creates the fluctuation. It also preserves the parent critical path as the target, avoiding the
shrinking-contribution problem raised in the original concern.
