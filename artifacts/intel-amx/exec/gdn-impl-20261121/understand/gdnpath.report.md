# GDN call path from the generated plugin to the kernels, and its threading

## Short version

- The generated plugin calls `tron::run_gdn_operation` 48 times: 24 on the forward thread (worker 0) and 24 in the main-helper function. On our half of delphi-3b35 the call runs on 16 threads (1 forward thread + 15 main helpers), each pinned to one CPU. The 40 attention workers never run it.
- Activations exist only as per-token rows (`indexed_vector<token_job_id, btensor_t<N>>`, one DMA allocation per row). No contiguous [token][channel] buffer exists. A chain can hold up to 1,024 tokens in one forward, not 128.
- `run_gdn_operation` has no handle to the model state, so new counters and the AMX bracket must be reachable from its 11 arguments, from globals, or through a generator change.

Path prefixes used below:
- `WT` = `/home/jhan/workspace/ai-runs/tron-qwen35-4b` (commit 72e1191804, read only)
- `PLUGIN` = `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp` (8,642 lines)

Words: GDN = GatedDeltaNet layer. Work item = one (chain, key head) pair. Forward thread = the scheduler thread that calls the plugin's `run`. Main helper = an app-pool worker that helps the forward thread with non-attention work.

---

## 1. Call sites in the plugin

### 1.1 The call
`PLUGIN:1165` (forward thread, operation 0):
```cpp
tron::run_gdn_operation<gdn_operations[0], gdn_kernels[0]>(std::get<0>(model.prepared_gdn_operations), std::get<0>(gdn_executors), outer_state.recurrent_chains(), outer_state.recurrent_checkpoints(), linear, linear_1, linear_2, linear_3, gated_delta_net, 0, n_workers);
```
`PLUGIN:5966-5968` (main helper, operation 0):
```cpp
if (worker_ix < n_workers) {
  tron::run_gdn_operation<gdn_operations[0], gdn_kernels[0]>(..., linear, linear_1, linear_2, linear_3, gated_delta_net, worker_ix, n_workers);
}
```
- 24 calls in `run()` at PLUGIN lines 1165, 1316, 1475, 1772, 1929, 2082, 2379, 2536, 2689, 2986, 3143, 3296, 3593, 3750, 3903, 4200, 4357, 4510, 4807, 4964, 5117, 5414, 5571, 5724 (worker index literal `0`).
- 24 calls in `run_main_help()` at PLUGIN lines 5967, 6004, 6041, 6112, 6149, 6186, 6257, 6294, 6331, 6402, 6439, 6476, 6547, 6584, 6621, 6692, 6729, 6766, 6837, 6874, 6911, 6982, 7019, 7056 (worker index `worker_ix`).
- `run_attention_worker()` (PLUGIN:7115-7142) has 0 calls.
- Argument order is always (mixed_qkv, output_gate z, decay a, update b, output). Odd operations pass `linear, linear_1, linear_3, linear_2`. That is only buffer reuse: for operation 1 the generator fills `linear_3` from `in_proj_a` and `linear_2` from `in_proj_b` (PLUGIN:1275, 1289). The generator emits the activations in `GDN.SequenceInputs` order (`WT/ingest/src/TronCpp.hs:3138-3139`; `WT/ingest/src/GatedDeltaNet.hs:164-169`).

### 1.2 Signature of the callee
`WT/h/tron/models/gdn_execution.hpp:76-89`:
```cpp
template <gdn_operation_descriptor operation_descriptor, gdn_kernel_spec kernel_spec>
void run_gdn_operation(
    std::optional<prepared_gdn_operation<kernel_spec.geometry>> const& prepared_optional,
    std::vector<gdn_rolling_head_executor<kernel_spec.geometry>>& executors,
    gdn_chain_plan const& chains,
    gdn_checkpoint_table const& checkpoints,
    auto const& mixed_qkv, auto const& output_gate, auto const& decay, auto const& update,
    auto& output, size_t worker_ix, size_t n_workers)
```
It receives no model state, no layer id and no statistics object.

### 1.3 Buffer and row types
Declared in the plugin `state` struct:
- `PLUGIN:973` `indexed_vector<token_job_id, btensor_t<8192>> linear;` (mixed_qkv: 2,048 q + 2,048 k + 4,096 v channels)
- `PLUGIN:974` `indexed_vector<token_job_id, btensor_t<4096>> linear_1;` (output gate z)
- `PLUGIN:975-976` `indexed_vector<token_job_id, btensor_t<32>> linear_2; ... linear_3;` (decay a and update b, one value per value head)
- `PLUGIN:977` `indexed_vector<token_job_id, btensor_t<4096>> gated_delta_net;` (output)

Element type:
- `btensor_t` comes from the executor: `WT/h/tron/models/common.hpp:126-127`. The model is built for tp1, tp2, tp4 only (`/home/jhan/workspace/intel-AMX/exec/gdn-20261120/models.gdn.yaml`), and the runs use `ingested-qwen-3.5-4b-tp4` (`/home/jhan/workspace/intel-AMX/exec/gdn-20261120/run-one.sh:23`). `tp4 = make_llm_executor<false, hardware::tp4_min512_tensor>` keeps the default `BTensor = hardware::btensor` (`common.hpp:115-140`).
- `hardware::btensor<N> = dmatensor<bf16, N>` (`WT/h/tron/hardware/btensor.hpp:20-21`). So every row is bf16 in the real model.
- Other executors give other rows: `host` gives `tensor<N>` (float), `host_bf16` gives bf16, `host_fp16` gives fp16 (`common.hpp:144-146`). The unit tests use float rows too (`WT/t/t_gated_delta_net.cpp:1952-1953`: `using replay_buffer = indexed_vector<token_job_id, tensor<width>>;`).

Row accessors of `dmatensor<bf16, N>` (`WT/h/tron/hardware/dmatensor.hpp`):
- line 176: `hardware::unique_dma<Scalar[]> data;` Each row owns one DMA allocation.
- lines 163-165: backing size `(N + 4095) / 4096 * 4096` elements, alignment `chunk_size * sizeof(Scalar) * 2` = 64 bytes for bf16. So a 32-wide row still occupies 4,096 bf16 = 8,192 bytes. The 8,192-wide row is 16,384 bytes. The 4,096-wide rows are 8,192 bytes.
- line 337: `fp32s chunk(size_t i) const` returns 16 floats widened from 16 bf16 (aligned 256-bit load, line 439-441).
- line 342: `bf16s bf16_chunk(size_t i) const` returns the 16 raw bf16.
- line 356: `void store_chunk(size_t i, fp32s x)` narrows with `fp32s_to_bf16s` (`_mm512_cvtneps_pbh`, round to nearest even; `WT/h/tron/simd/bf16.hpp:62-64`) and does an aligned store.
- lines 380/385: `Scalar& operator[](size_t)` / `Scalar const& operator[](size_t) const` return one bf16.
- raw pointer from a const row: `operator Scalar const*() const` (line 395), `begin() const` (line 413), `data.get()`. `raw()` (line 332) is not const.
- `as_view() const` (line 227) gives `const_view<bf16, true, true, seq<N>, sseq<1>>`.

Buffer accessor: `indexed<ix, T, coll>::operator[](ix)` (`WT/h/common/indexed.hpp:87-96`). For `mixed_qkv[job]` on the `auto const&` parameter it returns `const dmatensor<bf16, 8192>&`. For `output[job]` it returns `dmatensor<bf16, 4096>&`. `token_job_id` is defined in `WT/h/tron/models/common.hpp:220-226`.

There is no `.chunk(i)` on the buffer and no multi-token view. A contiguous [token][channel] buffer was not found.

### 1.4 Input readiness and output use
- Before each call, the worker calls `start_reading(worker_ix)` and `start_reading_all()` on the 4 input channels (PLUGIN:1156-1163 and 5957-5964). `start_reading_all` waits until every item is readable (`WT/h/tron/models/common.hpp:706-713`, Note [Channel design] step 7b at 451-453). So all rows of all tokens are complete when the GDN call starts.
- The output buffer feeds an FPGA matmul (`fill_matmul_template(linear_4, gated_delta_net, ...)`, PLUGIN:1151). The worker calls `gated_delta_net_channel.finish_writing(worker_ix)` right after the call returns (PLUGIN:1166, 5969). So every output row must be fully written before `run_gdn_operation` returns.

### 1.5 Thread pool, worker count, pinning
- Pool: `app_pool()` (`WT/h/tron/threading.hpp:744-759`), size = app CPUs minus 1. Our runs log 56 app CPUs (`/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/rt-results.txt` line 5: `App CPU list: 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143`) and the attention summary says `"n_workers":55,"active_workers":40` (`.../rt/q35-tp4-1u-p1024__on__rep1.log`).
- Launch (PLUGIN:1056-1085): `n_main_helpers = outer_state.recommend_n_main_helpers()`, `n_workers = 1 + n_main_helpers`, `n_attn_workers = tp.num_workers() - n_main_helpers`. Helper `i` runs on pool worker `i` with `worker_ix = 1 + i` (`tp.enqueue_to(i, ... run_main_help(q_batches, 1 + i, n_workers))`). Attention worker `i` runs on pool worker `n_main_helpers + i`.
- `recommend_n_main_helpers` (`WT/h/tron/models/model.hpp:2533-2578`): with one minibatch it uses `fixed_main_helper_split() = (app_pool().num_workers() * 2) / 7` (2527-2529), then clamps to `[min_main_helpers, max_main_helpers]`, then caps with `plugin_state.available_main_parallelism(items)`.
  - `min_main_helpers`: env `TRON_MIN_MAIN_HELPERS`, else 1 when the pool has 16 workers or more (`model.hpp:75-81`).
  - `max_main_helpers`: env `TRON_MAX_MAIN_HELPERS`, else `num_workers() / 2` (`model.hpp:82-86`).
  - `available_main_parallelism(n_tokens) = std::max(n_tokens, tron::gdn_available_main_helpers(n_tokens, 16))` (PLUGIN:7143-7145). `gdn_available_main_helpers(chains, key_heads) = chains * key_heads - 1` (`gdn_execution.hpp:68-73`). With 1 token it is 15.
  - Result on our half of 3b35: (55 * 2) / 7 = 15 helpers, so 16 GDN threads and 40 attention workers, in decode and in prefill. The attention summary confirms `n_attn_workers_min` = `n_attn_workers_max` = 40.
- Work split (`gdn_execution.hpp:106-114`): `work_item_count = chains.size() * 16`. Worker `w` takes `work_ix = w, w + n_workers, ...`. `chain_ix = work_ix / 16`, `head_group_ix = work_ix % 16`. With 16 workers, worker `w` always owns head group `w`, for every chain, one chain after another. A worker with `worker_ix >= work_item_count` returns at line 109.
- Pinning of pool workers: `thread_pool::do_work` starts with `hardware::system::with_app_pin_thread pinned;` (`threading.hpp:710-712`). `app_pin_thread()` binds the thread to one CPU and removes it from the app set (`WT/src/system/system.cpp:652-670`). Workers start one at a time, so CPU numbers ascend (`threading.hpp:646-653`).
- Forward thread: the work-queue `std::jthread` (`WT/h/tron/scheduler/work_queue.hpp:433-451`) names itself `"%d/?-work_queue"` and calls no pin function. The process main thread is pinned with `app_pin_thread()` at `WT/src/pos/driver.cpp:418`. A new thread inherits its creator's CPU mask.
- Measured thread names in the traces (`/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/trace/t-1u-p1024.perfetto-trace.summary.json`, key `per_thread_step_us`): `96/?-work_queue` plus ` 97/1-worker` to `111/1-worker`. So the 16 GDN threads sat on CPUs 96 to 111. CPUs 108 and 109 run the GDN step in 3.8 to 4.0 us; the other 14 need 6.4 to 6.5 us (same file). The design text attributes that to a 4.00 GHz clock on those two CPUs.

---

## 2. The chain plan

### 2.1 Types
`WT/h/tron/models/gdn_chain_plan.hpp:51-61`:
```cpp
struct gdn_chain {
  token_pos_ht source_height;
  std::vector<token_job_id> order;
  token_pos_ht destination_height() const noexcept {
    return token_pos_ht(source_height.i + order.size());
  }
};
using gdn_chain_plan = indexed_vector<gdn_chain_id, gdn_chain>;
```
- A chain is a run of one sequence's consecutive tokens (Note at 22-40). `order` lists the token jobs in ascending height. Jobs of different chains may interleave, so the job ids of one chain need not be consecutive.
- `gdn_checkpoint_entry { std::span<std::byte const> source; std::span<std::byte> destination; }` (74-77). `source` is empty exactly when `source_height == 0`. `source` and `destination` can be the same bytes. Otherwise `destination` holds unspecified bytes and a non-empty `source` does not overlap it (63-73).
- `gdn_checkpoint_table::at(chain, slot)` indexes `entries_[chain.i * slot_count_ + slot.i]` (114-119).
- Every token job of a recurrent pass is in exactly one chain (`WT/h/tron/models/model.hpp:2306-2319`).

### 2.2 Where the scheduler builds chains
- `prepare_recurrent_pass()` (`WT/h/tron/scheduler/full.hpp:2574-2701`) selects chains. Per candidate (2616-2621):
```cpp
size_t const chunk_size =
    std::min({remaining_chain, model_t::max_minibatch_size, remaining_jobs});
token_pos_ht const chunk_endpoint(progress.i + chunk_size);
```
  `recurrent.chain_specs.push_back({progress, chunk_endpoint});` (2666).
- The tree walk emits the jobs: `recurrent.chain_jobs.push_back({*chain_id, output_height});` (3345).
- `plan_gdn_chains(recurrent.chain_specs, recurrent.chain_jobs)` builds the plan (2831-2836; planner at `gdn_chain_plan.hpp:128-158`).
- `prepare_recurrent_checkpoints()` (2707-2757) fills the table and asserts the three source cases: empty for height 0, `source.data() == destination.data()` for in place, distinct otherwise.
- The plan goes to the model in `state.forward(..., plan.recurrent_chains, gdn_checkpoint_table(...), ...)` (2933-2939). The model exposes it as `recurrent_chains()` / `recurrent_checkpoints()` (`model.hpp:2155-2167`) and clears it after `plugin_state.run` (2248-2250).

### 2.3 Maximum tokens in one chain in one forward
- The 128 comes from the generation layer, not from the scheduler: `get_prompt_chunk_size()` returns env `TRON_PER_USER_PROMPT_CHUNK_LIMIT`, else 128 (`WT/h/libtron.hpp:194-206`). `next_prompt_chunk_size()` uses it (`WT/src/tron/generation/context.cpp:82-96`).
- The scheduler bound is `model_t::max_minibatch_size`. Every ingested plugin has `max_minibatch_size = 1024` and `max_minibatches = 1` (PLUGIN:57-58; `WT/ingest/src/TronCpp.hs:302-303`).
- `remaining_jobs` starts at `min(live_token_limit, capacity_limit)` (full.hpp:2599-2600). Both are capped by `cfg.max_minibatches * max_minibatch_size` = 1,024 (2157-2174). So one pass holds at most 1,024 token jobs: 8 users times 128 tokens exactly fills it.
- A chain can be longer than 128 tokens, up to 1,024, in these cases:
  - `TRON_PER_USER_PROMPT_CHUNK_LIMIT` above 128.
  - The first chunk of a prompt that resumes: its size is `resume_offset - prompt_tokens_processed + min(chunk, prompt.size() - resume_offset)` (context.cpp:87-89). The chain starts at the snapshot, so it is normally one chunk long. The match is advisory ("extend_request chooses the source again", context.cpp:38-39). If the snapshot is gone, the chain covers the whole first chunk.
  - "An empty request on a published tip therefore replays from the deepest snapshot below the tip, or from SOS" (full.hpp:2022-2025).
- A chain can be shorter than its chunk: the pass cuts it to the jobs left (`remaining_jobs`), and chunks end at keep points (context.cpp:90-94). So a chain length can be any value from 1 to 1,024.
- A cut chain continues in a later pass: `selection.endpoint->advance_to(selection.destination_height)` (full.hpp:2778-2780). "later chunks read and write that storage in place" (`WT/h/tron/scheduler/recurrent_endpoint.hpp:46-49`).

### 2.4 When a chain starts at a non-zero height
- Height 0 only for the first chunk of a fresh sequence (source empty, `start_from_zero`).
- Non-zero for: every later prompt chunk (normally in place, source == destination), every decode step (1 token, in place after the storage takeover, Note [In-place recurrent continuation] `WT/src/tron/scheduler/full.cpp:142-163`), a chain that resumes from a snapshot or a shared source (source != destination, source read only; `full.hpp:256-284`, `recurrent_endpoint.hpp:37-44`), and the continuation of a chain cut by the pass capacity.
- A 1-token chain can also have source != destination: when a snapshot holds the tip state, "the next extend finds a second holder and copies forward" (full.hpp:275-276).

---

## 3. Executors: creation, size, lifetime, working set

- Declaration: `PLUGIN:1006` `std::tuple<std::vector<tron::gdn_rolling_head_executor<tron::gdn_geometry{.n_key_heads = 16, .n_value_heads = 32, .key_head_dim = 128, .value_head_dim = 128, .conv_kernel_size = 4}>>> gdn_executors;` One vector per kernel (geometry), shared by all 24 operations. Generator: `TronCpp.hs:763-778`.
- Sizing: on the forward thread, before the helpers start (PLUGIN:1067-1069):
```cpp
if (std::get<0>(gdn_executors).size() < n_workers) {
  std::get<0>(gdn_executors).resize(n_workers);
}
```
  It never shrinks (`TronCpp.hs:1582-1584, 1640-1647`). Worker `w` uses only `executors[w]` (`gdn_execution.hpp:125`; Note at 35-38).
- `gdn_rolling_head_executor<geometry> = gdn_rolling_executor<geometry, 1>` (`WT/h/tron/models/gdn_rolling_executor.hpp:475-476`): one key head per group, 16 groups.
- Default construction allocates nothing. The first `bind()` allocates the working set: `if (working_ == nullptr) working_ = std::make_unique_for_overwrite<working_set>();` (`gdn_rolling_executor.hpp:373`). The allocation happens on the worker thread that first starts a chain. Later chains and other operations reuse it.
- Lifetime: the plugin `state` is the member `plugin_state` of `model<>::state` (`model.hpp:1701`), which is the member `state` of `full_scheduler` (`full.hpp:2131, 2153`).
- `working_set` members (`gdn_rolling_executor.hpp:189-211`) for {16, 32, 128, 128}, computed from the declarations (est., not compiled):

| Member | Bytes |
|---|---|
| `recurrent_state_copy` = `tensor<2,128,128>` | 131,072 |
| `convolution_history_copy` = `array<float, 8192 * 3>` (full payload size) | 98,304 |
| `convolution_qkv` = `tensor<512>` | 2,048 |
| `recurrence_output` = `tensor<256>` | 1,024 |
| `source_chunks` = `array<size_t, 32>` | 256 |
| 5 pointers and indices | 40 |
| Total, padded to 64 | 232,768 (227.3 KiB) |

  16 executors hold 3,724,288 bytes (3.55 MiB). The history copy has the size of the whole operation's history, although one group uses only 6,144 bytes of it at payload offsets (Note at 122-125).
- `step()` also puts two `tensor<2>` on the stack (lines 326-327).
- Checkpoint payload: `gdn_fp32_checkpoint_bytes` = (32 * 128 * 128 + 8,192 * 3) * 4 = 2,195,456 bytes per operation (`WT/h/tron/models/gdn_geometry.hpp:48-52`). 24 slots = 52,690,944 bytes (50.25 MiB) per sequence (`WT/h/tron/models/recurrent_state_storage.hpp:57-61`).
- Payload layout (Note [GatedDeltaNet checkpoint payload], 91-131): FP32 state in [value head][key coordinate][value coordinate] order, then FP32 convolution history in [channel chunk][entry][lane] order. One group owns `recurrent_head_bytes * 2` = 131,072 contiguous state bytes at `first_value_head(group) * 65536`, and three history runs (`history_runs`, 401-405).

---

## 4. Geometry and operations of Qwen3.5 4B as compiled

- `PLUGIN:42`: one kernel, `gdn_kernel_id(0)`, `gdn_geometry{.n_key_heads = 16, .n_value_heads = 32, .key_head_dim = 128, .value_head_dim = 128, .conv_kernel_size = 4}`.
- Derived: key projection width 2,048, value projection width 4,096, 8,192 convolution channels, 2 value heads per key head, 32 chunks of 16 channels per group (8 q + 8 k + 16 v).
- `PLUGIN:43`: 24 `gdn_operation_descriptor`s. Operation `i` has `gdn_op_id(i)`, `recurrent_slot_id(i)`, `gdn_kernel_id(0)`, `norm_epsilon 1.0e-6f`.
- `PLUGIN:44`: 24 `recurrent_slot_spec{gdn_fp32_checkpoint_bytes(geometry), chunk_alignment}` (alignment 64 bytes).
- Operation to layer (from the weight names in `visit_named_tensors` and `finalize_weights`, PLUGIN:505-528): operation `i` is model layer `i + i / 3` (integer division): layers 0, 1, 2, 4, 5, 6, 8, 9, 10, ..., 28, 29, 30. The 8 attention operations sit on layers 3, 7, 11, 15, 19, 23, 27, 31 (PLUGIN:62).
- The descriptor carries no layer id (`WT/h/tron/models/gdn_registry.hpp:64-69`). A per-layer counter can only key by `gdn_op_id` unless a mapping is added.
- Other constants: `n_layers = 32`, `dim = 2560`, `n_heads = 16`, `n_kv_heads = 4`, `head_size = 256` (PLUGIN:33-39). Attention geometry `{16, kv_geometry{4, 256}}` (PLUGIN:60).
- Prepared constants per operation: `prepared_gdn_operation<geometry>` with `convolution_weights`, `A_exp`, `dt_bias`, `output_norm_weight`, `output_rms_norm_epsilon`, all `const` (`WT/h/tron/models/gdn_prepared_operation.hpp:51-79`). Held in `std::tuple<std::optional<...>, ...> prepared_gdn_operations` on the model (PLUGIN:496).

---

## 5. What must change to add `advance(chain rows ...)`

### 5.1 Today's loop (`gdn_execution.hpp:112-146`)
```cpp
gdn_checkpoint_access const access = chain.order.size() == 1
                                         ? gdn_checkpoint_access::in_place
                                         : gdn_checkpoint_access::working_copy;
if (starts_from_zero) {
  executor.start_from_zero(*prepared_optional, head_group_ix, destination, access);
} else {
  ...
  executor.start_from_checkpoint(*prepared_optional, head_group_ix, source, destination, access);
}
for (token_job_id job : chain.order)
  executor.step(mixed_qkv[job], output_gate[job], decay[job], update[job], output[job]);
executor.write_checkpoint();
```
So chains of 2 or more tokens already run on a working copy that `write_checkpoint` stores at the end. `advance()` replaces only the `for` loop at lines 141-143 for those chains.

### 5.2 Row concepts (`gdn_rolling_executor.hpp:25-40`)
```cpp
template <typename row> using gdn_row_reference = decltype(std::declval<row&>()[size_t{}]);
template <typename row> using gdn_row_scalar = std::remove_cvref_t<gdn_row_reference<row>>;
template <typename row, size_t width>
concept gdn_activation_row = requires { typename gdn_row_scalar<row>; } &&
                             expression<row> && expr_size<row> == width &&
                             (std::same_as<gdn_row_scalar<row>, bf16> ||
                                 std::same_as<gdn_row_scalar<row>, float>);
template <typename row, size_t width>
concept gdn_writable_activation_row =
    gdn_activation_row<row, width> &&
    requires(row& output) { output.store_chunk(size_t{}, fp32s{}); };
```
`step` (306-315) takes five row types with widths 8192, 4096, 32, 32, 4096 for this geometry. The tests assert that `hardware::btensor`, `tensor`, a float const view and a bf16 const view all satisfy the read concept (`t_gated_delta_net.cpp:1336-1349`).

### 5.3 How `step` reads rows today
- mixed_qkv: `mixed_qkv.chunk(working.source_chunks[chunk])` for 32 chunks (322-324).
- decay, update: `static_cast<float>(decay_input[value_head])` for 2 heads (328-332).
- gate: `output_gate.chunk(output_chunk)` for 16 chunks, in `postprocess` (464).
- output: `output.store_chunk(output_chunk, result)` for 16 chunks (466).
So `advance()` can stay generic by using only `.chunk(i)`, `operator[]` and `.store_chunk`. Several tokens can be read only by indexing the buffer once per job. The executor header does not include `tron/models/common.hpp`, so it does not know `token_job_id` today (includes at 15-21).

### 5.4 Places to edit
1. `WT/h/tron/models/gdn_execution.hpp`
   - lines 141-143: branch on `chain.order.size()`.
   - lines 18-53: Note [GatedDeltaNet replay] describes the two modes.
   - line 110: the trace slice (keep name and arguments, see section 8).
   - AMX bracket and counter hooks (sections 6 and the end).
2. `WT/h/tron/models/gdn_rolling_executor.hpp`
   - `working_set` (189-211): per-token buffers and the contiguous column-half buffers.
   - new public method next to `step` (306-358).
   - `postprocess` (439-469) is private and static. It rounds `values` in place and takes one gate row and one output row. Phase 3 can call it per token if phase 2 keeps each token's FP32 recurrence output (256 floats per token per group).
   - Notes at 51-89 and 91-131.
3. `WT/h/tron/kernels/gated_delta_net.hpp`
   - `gdn_recurrence` (224-300) normalizes q and k and computes decay and beta inside each call. The chain path must hoist them to phase 1 with the same expressions: `normalize_gdn` (174-194), `gdn_softplus` (168-172), `gdn_beta` (196-199), decay (259-262), `query_scale` (242-243), `scaled_query(normalized_query_values[key_coordinate] * query_scale)` (287).
   - `gdn_conv1d_silu` (117-152) shifts the history per call, so phase 1 must run in token order.
4. `WT/t/t_gated_delta_net.cpp` (2,442 lines): executor tests from 1276, replay tests from 1936. The test geometry is `{2 key heads, 4 value heads, key_head_dim 16, value_head_dim 80, conv 4}` (1277-1283). Tests instantiate both `gdn_rolling_executor<g, g.n_key_heads>` (all heads in one group) and the head executor (1295-1297). Tests call `step` on multi-token chains with `in_place` access (1995-2005, 2041-2048).
5. Only if the signature of `run_gdn_operation` changes: `WT/ingest/src/TronCpp.hs:3121-3145` (the call), `3197-3198` (forward thread), `3258-3265` (helper), the generated test plugin `WT/ingest/test/generated-gdn-scheduler/Main.hs` (used by `WT/t/t_generate_mock_plugin.cpp:50`), and the direct calls at `t_gated_delta_net.cpp:2014` and `2285`. No golden text with `run_gdn_operation` was found under `WT/ingest/test`.

---

## 6. AMX tile region

- Existing bracket: `amx_attn_h128g4::begin_region()` runs `_tile_loadconfig` for 8 tiles of 16 rows by 64 bytes; `end_region()` runs `_tile_release` (`WT/src/tron/kernels/amx_attn.cpp:115-127`). Declared without intrinsics in `WT/h/tron/kernels/amx_attn_iface.hpp:240-243`. Tile configuration is per thread (iface 87-89).
- Only one call site exists: `apply_page_range` in `WT/h/tron/models/self_attention.hpp:1553` and `1557-1559` (`tron::finally end_amx_region`), inside `#ifdef TRON_AMX_DISPATCH` (1525-1560). It runs on attention workers through `run_attention_job` (PLUGIN:7120).
- For this model the attention gate is false at compile time: `shape_ok` needs head size 128 (`amx_attn_iface.hpp:145-147`), the model has 256. The base runs show `ready_amx_visits` = 0.
- Where a GDN bracket can go: around the chain replay of one work item, at the place of `gdn_execution.hpp:141-143`, after `start_from_*` and before `write_checkpoint` (lines 131-139 and 145 are memcpy and AVX-512 NaN scans). The header is compiled in the plugin translation unit without AMX flags, so the bracket must be two out-of-line functions from the AMX translation unit, under `#ifdef TRON_AMX_DISPATCH` and a run-time gate. `TRON_AMX_DISPATCH` is defined for the plugin objects (`WT/src/tron/CMakeLists.txt:335-338`) and for users of `tron` (line 222). Only `kernels/amx_attn.cpp` gets `-mamx-tile;-mamx-bf16` today (218-223).
- Early exits: the only `return` is at line 109, before the loop. Inside the loop there is none.
- Nesting: none found.
  - `run_gdn_operation` calls only executor methods and one `TRACE_EVENT`.
  - `run_main_help` (PLUGIN:5949-7114) contains 0 calls of `save_k`, `save_v`, `prepare_attention_job`, `run_attention_job`, `help_drain_gof`.
  - The forward thread calls `prepare_attention_job`, `launch_early_hw_attention`, `save_k`, `save_v`, `prepare_late_hw_attention`, `launch_late_hw_attention` at the 8 attention layers (for example PLUGIN:1611-1622), but at other times than the GDN call, and none of them calls `begin_region` in this worktree.
  - `run_attention_worker` (PLUGIN:7115-7142) contains 0 GDN calls.
  - Within one forward a pool worker is either a helper or an attention worker (Note [Attention workers are the last pool workers], `model.hpp:2781-2811`). Across forwards the split can change on other machines; on ours it is constant at 15.
- `available()` already requests the tile permission once per process and reads `TRON_AMX_DISABLE` once (`amx_attn.cpp:86-113`).

---

## 7. NaN validation and its cost

- Where: `start_from_checkpoint` ends with `validate_checkpoint_values();` (`gdn_rolling_executor.hpp:281`). `start_from_zero` does not validate. `step` does not validate.
- What (417-437): one `mask1s` over the group's state rows (`nan_lanes` per key coordinate row) and one over the three history runs, then two `TRON_ASSERT(none(...))`. `nan_lanes` (407-415) uses aligned 64-byte loads and `cmp<_CMP_UNORD_Q>(chunk, chunk)`.
- `TRON_ASSERT` is active in release builds (`WT/h/common/assert.hpp:3-5` undefines `NDEBUG`).
- Amount per work item (computed): 2,048 loads over 131,072 state bytes plus 96 loads over 6,144 history bytes = 137,216 bytes.
- Per chain and operation: 16 groups cover the whole checkpoint, 2,195,456 bytes.
- Per decode step and user: 24 operations, 52,690,944 bytes (50.25 MiB), 823,296 loads and compares, spread over 16 threads. In decode the scan runs on the destination itself (in place) and is the first touch of the state in that step. `gdn_recurrence` then passes over the same 131,072 bytes twice (267-275 and 285-294 of `gated_delta_net.hpp`).
- For chains of 2 or more tokens the scan runs once per work item on the working copy, after the memcpy from the source.
- Time: no timer exists in the code. Measured totals from the traces (`.../trace/t-1u-p1024.perfetto-trace.summary.json`, `t-8u-p1024...`, key `cpu_us_per_group_step`): one (chain, group, token) costs 6.12 us in prefill (1 user) and 6.10 us (8 users), and 16.10 us in decode (1 user) and 13.38 us (8 users). The decode value includes start, NaN scan, step and state fetch. Insufficient data for the NaN share alone. A TSC timer around `validate_checkpoint_values` would give it.
- Other checks: learned constants are checked once at preparation (`gdn_prepared_operation.hpp:88-132`). `step` asserts `working_ != nullptr` (316). `gdn_conv1d_silu` asserts `source_chunk < n_source_chunks` per chunk (`gated_delta_net.hpp:130`), 32 times per token per group.

---

## 8. TRACE_EVENT usage

- One slice in the GDN path, `gdn_execution.hpp:110-111`:
```cpp
TRACE_EVENT("model", "GatedDeltaNet", "operation", operation_descriptor.operation.i,
    "chains", chains.size());
```
  It opens after the empty-shard return (line 109), so it is one slice per worker with work, per operation, per forward. It covers all work items of that worker.
- No `TRACE_EVENT` in `gdn_rolling_executor.hpp`, `gated_delta_net.hpp`, or the generated plugin (0 matches).
- Category `"model"` is defined in `WT/h/common/perfetto.hpp:107`. The macro is gated by `application_track_events_enabled()` (32-63).
- Our analysis script depends on this slice: `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/analyze_trace.py:73, 103-111` selects `s.name = 'GatedDeltaNet'` and the argument `operation`.
- Surrounding slices: `TRACE_EVENT("scheduler", "forward", ...)` (`model.hpp:2098`) and the helper steps of `run_forward` (`"model"`, lines 2277, 2294, 2335, 2370, 2452, 2489, 2501).

---

## 9. Scheduler notes about resume positions and chain cuts

- Note [Recurrent state snapshots] (`full.hpp:256-284`): a later request "can start its recurrent chain there instead of recomputing the state". "The chain starts from that state's exact bytes, but the request runs forward passes with other numbers of tokens than a request that recomputes from the start, so their logits can differ as Note [Paying for Determinism] describes." "A request that resumes from a snapshot holds its future as its source until its first chunk has read it".
- Note [Sparse recurrent continuation scheduling] (`full.hpp:2007-2053`): "A nonempty continuation starts from the deepest snapshot its tokens pass through strictly below its own endpoint, or else from the tip's state". A pass "cuts each chain to the token jobs left in the pass's one minibatch". "two chains that would compute the same token cannot share a pass". "After synchronous model execution, the worker advances a partial suffix within its unpublished destination."
- Note [Recurrent prompt chunks] (`context.cpp:24-52`): "the scheduler publishes recurrent state only at the end of a chunk". "To keep the state at a point, the context ends a chunk there". Keep points are arbitrary prompt offsets (`WT/h/tron/scheduler/recurrent_reuse.hpp:30-39`). `min_kept_divergence_distance = 1024` (context.cpp:58).
- Publication: the listener notification calls `completion->advance_to(completion->endpoint()); completion->publish();` (full.hpp:2989-2991).
- Meaning for the kernels: chain boundaries fall at chunk ends, keep points, capacity cuts and snapshot heights, so source heights and chain lengths are arbitrary. The recurrence uses no token position, so 32-token blocks can only be counted from the chain start, and the last block can be short. Today the state bits do not depend on where a sequence is cut, because `step` is per token. A block kernel whose FP32 sum order depends on the block partition makes the bits depend on the cuts.

---

## Files an implementer of advance() must edit

- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/gdn_rolling_executor.hpp` (new method, buffers in `working_set`, Notes)
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/gdn_execution.hpp` (dispatch at 128-145, Note at 18-53, bracket, counter hooks)
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/kernels/gated_delta_net.hpp` (column-half recurrence next to `gdn_recurrence`, hoisted per-token preparation)
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_gated_delta_net.cpp` (equal-bytes tests)
- For Part A: new `h/tron/kernels/amx_gdn_iface.hpp`, new `src/tron/kernels/amx_gdn.cpp`, `/home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/CMakeLists.txt:218-223`, `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/CMakeLists.txt` (near 684-687)
- For counters: new `h/tron/models/gdn_stats.hpp`; model on `/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/attn_stats.hpp` (owner object created at `self_attention.hpp:467-492`, forward scope at `model.hpp:2111-2115`)
- Only with a signature change: `/home/jhan/workspace/ai-runs/tron-qwen35-4b/ingest/src/TronCpp.hs:3121-3145`, `ingest/test/generated-gdn-scheduler/Main.hs`, the two direct calls in the test file

## Invariants to keep

1. Worker `w` touches only `executors[w]`; the vector is not resized during replay (`gdn_execution.hpp:35-38, 102, 125`).
2. A group reads and writes only its own state rows, its three history runs and its output columns `[value_head_base * 128, +256)`; these ranges are disjoint between groups (`gdn_rolling_executor.hpp:127-131`).
3. A non-aliased source is never written. The destination may hold garbage before the write. Source and destination may be the same bytes for a chain of any length (`gdn_chain_plan.hpp:63-73`).
4. For chains of 2 or more tokens the destination is written once, in `write_checkpoint`, not per token (reason in `gdn_execution.hpp:46-53`).
5. Every start from a checkpoint rejects NaN in the group's state and history before the first token (`gdn_rolling_executor.hpp:108-109, 281`).
6. Tokens run in `chain.order`; the convolution history after the chain holds the last three rounded inputs (`gated_delta_net.hpp:52-59`).
7. BF16 rounding points stay where they are (Note at `gated_delta_net.hpp:22-42`): inputs rounded on read, FP32 state, FP32 unrounded recurrence output, four roundings in `postprocess` (450-466).
8. Per column, the operation order of `gdn_recurrence` stays: pass 1 over key coordinates 0 to 127 with `fma(normalized_key, state * decay, remembered)`, then `delta = (value - remembered) * beta`, then pass 2 with `new_state = fma(normalized_key, delta, state * decay)` and `result = fma(scaled_query, new_state, result)` (267-294).
9. Rows may be bf16 or float; FP32 rows must give the output of the bf16 rows they round to (`gdn_rolling_executor.hpp:72-74`).
10. All output rows are written before the call returns (channel `finish_writing` follows, PLUGIN:1166).
11. `step` keeps working for multi-token chains and for `in_place` access; chains of 1 token keep `step` and the in-place path.
12. The trace slice keeps its name `GatedDeltaNet` and its `operation` argument.
13. A tile region is closed before the function returns or waits.