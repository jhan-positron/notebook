# Attention statistics infrastructure, as the model for GDN statistics

Roots used below:
- `W` = `/home/jhan/workspace/ai-runs/tron-qwen35-4b` (tron worktree, commit 72e1191804, read only)
- `P` = `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp` (generated plugin, 8,642 lines)
- `E` = `/home/jhan/workspace/intel-AMX/exec/gdn-20261120` (3b35 recipe, read only)

Nothing was built or modified. No GDN counter exists today: a grep for `TRON_GDN`, `gdn_stats`, and rdtsc or counter code near gdn in `W/h`, `W/src`, `W/t`, `W/ingest/src` found nothing.

## 1. Env switch, the "enabled" flag, cost when off

- Switch read: `W/h/tron/models/attn_stats.hpp:161-172`, `inline bool env_enabled() noexcept` with `static const bool enabled = [] { const char* value = std::getenv("TRON_ATTN_STATS"); ... }()`. Exactly `"1"` turns it on. Unset is off. Any other value is off with one `spdlog::warn` (lines 166-168). Read once per process.
- It is an environment variable, not a CMake option. Every hook is compiled into every build (header note, lines 8-17).
- The flag lives in the object: `const bool enabled;` is the first member of `attn_stats::model_stats` (line 324). The production constructor call passes `attn_stats::env_enabled()` (`W/h/tron/models/self_attention.hpp:488`). Tests pass a bool.
- The object exists in every state, also when off (lines 319-323). When off, `rows`, `fpga`, `timers`, `path_bits` stay empty (constructor, lines 376-385).
- Off-state contract (header lines 13-17): "a per-visit hook may test one bool that was copied once per apply_page_range call and nothing else, no memory write and no atomic. Per call the cost is one byte load and one stack tally. Per job and per forward it is one branch."
- How the hot code does it: `const bool stats_enabled = stats_ref.enabled;` hoisted once per `apply_page_range` call (`self_attention.hpp:1471-1479`) and once per `run_attention_job` (`self_attention.hpp:792-795`). Timestamps are taken as `stats_enabled ? hardware::system::rdtsc() : attn_stats::UNSET_CYCLES_0`.
- Every `note_*` method starts with `if (!enabled) return;` (for example lines 451, 468, 483, 507, 516, 525, 533, 541, 554, 590).
- Info line when on (lines 381-384): `attention path stats on (TRON_ATTN_STATS=1) for model '{}'{}: rows for {} app-pool workers x {} layers`.
- A test pins the off state of a real model state: `W/t/t_llama_unit.cpp:3279-3280` (`stats->enabled == env_enabled()`, `rows.empty() == !env_enabled()`).

## 2. Data structures

All in `W/h/tron/models/attn_stats.hpp`, namespace `tron::attn_stats`.

- `enum class visit_path : uint8_t { empty = 0, avx = 1, amx = 2 }` (line 115), `N_PATHS_3`, `PATH_NAMES = {"empty","avx","amx"}` (116-117).
- Two software passes: `N_PASSES_2`, `PASS_READY_0`, `PASS_PENDING_1` (124-126).
- `enum class forward_class : uint8_t { decode_like = 0, prompt_or_mixed = 1 }` (131), `CLASS_NAMES` (leaf name segment) and `CLASS_LABELS` (stderr label with the rule) (133-136).
- Path-set bits per token job: `PATH_BIT_AVX_1`, `PATH_BIT_AMX_2`, `PATH_BIT_FPGA_4`, `N_PATH_SETS_8`, `PATH_SET_NAMES` (140-146).
- Relaxed helpers (176-192): `inc_relaxed` (load + add + store, single writer), `max_relaxed`, `min_relaxed`, `load_relaxed`.
- `struct visit_tally` (197-217): plain integers on the stack, filled per visit by `record(visit_path, int relevant_k_tokens, size_t page_size)`, added to the row once per `apply_page_range` call.
- `struct alignas(64) worker_layer_row` (225-246): `visits[2][3]`, `k_tokens[2][3]`, `avx_full_page_visits[2]`, `attn_jobs`, `busy_cycles`, `join_wait_cycles`, all `std::atomic<uint64_t>`. 17 atomics = 136 bytes, 192 bytes after alignment. One row per (forward class, pool worker, layer).
- `struct alignas(64) layer_timers` (252-263): `wall_cycles`, `wall_max_cycles`, `period_cycles`, `period_count`, `period_max_cycles`. One per (class, layer), written by attention worker 0 only.
- `struct layer_fpga_counters` (271-274), one per (class, layer), main thread, `fetch_add` relaxed.
- `struct forward_counters` (278-303), one per class: `forwards`, `wall_cycles`, `wall_max_cycles`, `fpga_queries`, `token_jobs`, `listener_jobs`, `kv_only_jobs`, `n_attn_workers_min` (init `UINT64_MAX`), `n_attn_workers_max`, `token_jobs_by_path_set[8]`.
- `struct header_facts` (306-314): `amx_compiled`, `amx_available`, `n_kv_heads`, `kv_mul`, `head_size`, `n_layers`, `page_size`.
- `struct model_stats` (318-850). Index: `rows[(cls * n_workers + worker) * n_layers + layer]` (392-397), `fpga[cls * n_layers + layer]`, `timers[cls * n_layers + layer]`. Every accessor asserts its bounds with `TRON_ASSERT_LT`.
- Row key is the pool worker, not the attention worker index: `pool_worker(attn_ix, n_attn_workers) = n_workers - n_attn_workers + attn_ix` (431-435). `n_workers` is `attn.size()` = `app_pool().num_workers()` (`self_attention.hpp:472, 490`).
- Writers and readers (header lines 45-49, 59-67):
  - Only the owning worker writes its rows (plain load-add-store on relaxed atomics).
  - FUSE read callbacks and the exit report read with relaxed loads.
  - FPGA counters and per-forward counters are written on the main thread with relaxed `fetch_add`.
  - Per-forward scratch (`path_bits[pool worker][token job]`, `fpga_bits`, the T4 fields `t4_last_operation`, `t4_last_layer`, `t4_layer_start_cycles`) is plain data. Reason given: forwards of one model state are serialized, the main thread writes before the workers start and reads after they finish.
- Memory when on (header 83-84): 2 classes x pool workers x layers x 192 bytes. For this model on 3b35 that is 55 x 32 x 2 x 192 = 675,840 bytes.

## 3. Timers

- All timers are raw TSC cycles. Differences are always taken on one thread.
- `hardware::system::rdtsc()`: `W/h/system/system.hpp:317-321`, `inline uint64_t rdtsc(void) noexcept`, namespace `tron::hardware::system` (line 21).
- TSC frequency: `uint64_t get_cpu_freq() noexcept;` declared `system.hpp:338`, defined `W/src/system/system.cpp:2337-2339` (returns `detail::cpu_frequency_hz`, 0 until the calibration thread publishes). The summary leaf carries it as `tsc_hz` (`attn_stats.hpp:724-733`).
- Other helpers in `system.hpp`: `cycles_to_ns` (269), `ns_to_cycles` (280), `get_corrected_ns(tsc, cpu)` (290), `tsc_in_ns()` (324), `tsc_core_in_ns()` (328), `get_system_ns()` (335). `cycles_to_ns` and `get_corrected_ns` assert that calibration ran (`TRON_ASSERT(detail::cpu_frequency_hz != 0)`, `TRON_ASSERT(physical_cores > 0)`), so they abort in a unit test that never started the calibration thread. attn_stats uses none of them.
- Timer definitions (header 30-43): T1 forward wall (`forward_scope`), T2 busy per attention job per worker (`run_attention_job`'s `attn_elapsed`), T3 job wall on worker 0, T4 layer period on worker 0, T5 join wait.
- Hook sites: T2/T3/T4 at `self_attention.hpp:789-798` and `841-849`; T5 at `self_attention.hpp:1123-1127` (hardware join) and `1250-1272` (software poll); T1 in `forward_scope` (`attn_stats.hpp:866-883`).
- `UNSET_CYCLES_0` (line 154) is the "timestamp not taken" value.
- `system.cpp:2178-2182` says "TSC values differ by a constant offset between cores". Measured on 3b35: 43 baseline logs under `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/rt` and `.../trace` print `TSC core calibration: min core,offset:..  max core,offset:..` (`system.cpp:2332-2333`). Offsets are between -35 and +43 cycles. The largest spread inside one run is 46 cycles (17 ns at 2.70 GHz).

## 4. FUSE leaves

- API: `tron::fuse::stats` in `W/h/system/fuse_stats.hpp`. `static auto make_file(const std::string& path, const fuse_sysfs::value_type& value, bool read_only = false, bool exported = false) noexcept` (101-120). `get_file_handle(path)` (122-131). `is_initialized()` (57-59).
- `fuse_sysfs::value_type` = `std::variant<bool, int, double, int64_t, uint32_t, uint64_t, std::string>` (`W/h/system/fuse_sysfs.hpp:28-29`). `file_handle::set_read_callback(read_callback)` (355). `MAX_STRING_LENGTH = 2048` (343).
- Registration: `inline void register_fuse_files(std::shared_ptr<model_stats> const& stats)` (`attn_stats.hpp:914-950`).
  - No-op when `!fuse::stats::is_initialized()` or `!is_safe_model_id(stats->model_id)` (916-917). `is_safe_model_id` (888-898): non-empty, no leading dot, characters `[A-Za-z0-9-_.:]` only.
  - Prefix: `/model/<model id>/attention`, or `/model/<model id>/attention_eagle` for an EAGLE draft state (918-919).
  - Leaf: `make_file(path, std::string{"{}"}, LEAF_READ_ONLY_TRUE)` then `set_read_callback([weak, render](...) { if (auto s = weak.lock()) return value_type(render(*s)); return value_type(std::string{"{}"}); })` (926-933).
  - Flat layout: `summary`, `<class>_totals`, `<class>_forwards`, and only when on `<class>_layer_<L>`, `<class>_worker_<W>` (934-949).
  - A later state of the same id takes the leaves over (make_file returns the existing handle, the callback is replaced), with one info line (920-924).
- Leaf content: one JSON object per leaf, rendered by `render_summary` (722-735), `render_totals` (739-756), `render_forwards` (760-787), `render_layer` (789-800), `render_worker` (802-811). Off state: totals and forwards render `{}`, layer and worker render `{"layer":L}` / `{"worker":W}`.
- Convention test: the attention leaves are "casual" leaves. They live outside `/exported/`, pass `exported=false`, have no `.skip` marker and no manifest entry (`attn_stats.hpp:900-903`, `W/README.stats.md:232-240`). `W/t/t_tronstats_convention.cpp` covers only the manifest entries, markers, and the `/exported/` mirror (test cases at lines 327, 438, 639, 706, 831). `W/src/system/fuse_tronstats_manifest.cpp` has no attention entry. So a new casual group needs no change in the manifest, the lint, or that test, as long as it does not pass `exported=true`.
- README obligations, from what the attention group did in `W/README.stats.md`: the prose paragraph at 242-298, the path-table row `/model/<model_id>/attention/` at 352, and the registration-site sentence at 355-360. No test reads README.stats.md against the code (grep found only prose references).
- Leaf size: `W/t/t_attn_stats.cpp:483-558` checks every rendered leaf is below `MAX_STRING_LENGTH` for 96 workers x 128 layers. The limit is enforced for stored values, and `W/t/t_fuse_sysfs.cpp:922` says a read callback may serve longer strings. The attention code keeps below the limit anyway.

## 5. Exit report on stderr

- Printed by the destructor: `~model_stats() { if (enabled) print_report(stderr); }` (`attn_stats.hpp:388-390`).
- `print_report(std::FILE*)` (815-849) prints only when the switch is on and at least one forward or one visit was counted.
- Format (7 lines per state, the first with a leading blank line):
  - `\n[attn-stats] model <id>: <summary JSON>`
  - per class: `[attn-stats] <CLASS_LABEL> totals: <JSON>`, `[attn-stats] <CLASS_LABEL> forwards: <JSON>`, `[attn-stats] <CLASS_LABEL> k_tokens per layer (amx/avx/fpga): 0=a/b/c 1=...`
- Class labels: `decode_like/all_jobs_with_listener`, `prompt_or_mixed/some_jobs_without_listener`.
- When: when the last owner of the `shared_ptr` goes away, normally with the model state. runtron builds one state per prompt batch and each prints (header 71-74). The 3b35 baseline logs hold exactly one report of 7 lines per run.
- Consumers in the recipe: `E/run-one.sh` counts `^\[attn-stats\]` lines. `E/collect.py:38-43` parses `\[attn-stats\] model \S+: (\{.*\})` and `\[attn-stats\] (decode_like|prompt_or_mixed)\S* (totals|forwards): (\{.*\})`. Per-layer and per-worker values exist only in the leaves, which `E/poll-leaves2.sh` copies once per second from `$WT/stats/.../attention`.

## 6. Ownership, and how GDN code can reach a sibling object

Attention side:
- Owner: `std::shared_ptr<attn_stats::model_stats> stats;` in `self_attention<model>::state` (`self_attention.hpp:462-467`). Built and registered in that constructor (`self_attention.hpp:475-492`): `std::make_shared<attn_stats::model_stats>(attn_stats::env_enabled(), enclosing_state.cfg.id, enclosing_state.model_ref.plugin.is_eagle, facts, attn.size(), n_layers); attn_stats::register_fuse_files(stats);`
- The comment at 486-487 states the order rule: "cfg is declared before self_attn_state in model::state, so its id is initialized here."
- `model::state` member order (`W/h/tron/models/model.hpp`): `model_ref` (1322), `layers` (1325), `cfg` (1327), ..., `plugin_state` (1356), `self_attn_state` (1363), ..., `recurrent_chain_plan` (1368), `recurrent_checkpoint_table` (1369), ..., `min_main_helpers`/`max_main_helpers` (1576-1577). Init list at 1689-1707: `plugin_state(model.plugin, *this, this->cfg)` runs before `self_attn_state(*this)`.
- Reached from attention code as `stats` (same object), and from model.hpp as `self_attn_state.stats` (2111, 2840, 3284-3289).

GDN side:
- `run_gdn_operation` signature (`W/h/tron/models/gdn_execution.hpp:76-89`):
  `template <gdn_operation_descriptor operation_descriptor, gdn_kernel_spec kernel_spec> void run_gdn_operation(std::optional<prepared_gdn_operation<kernel_spec.geometry>> const& prepared_optional, std::vector<gdn_rolling_head_executor<kernel_spec.geometry>>& executors, gdn_chain_plan const& chains, gdn_checkpoint_table const& checkpoints, auto const& mixed_qkv, auto const& output_gate, auto const& decay, auto const& update, auto& output, size_t worker_ix, size_t n_workers)`
- It gets no state object. None of its arguments can carry a stats pointer today.
- Generated call sites in `P`: main thread at 1165 (op 0), 1316, 1475, ... with `worker_ix` literal 0; helpers in `run_main_help` (5949) at 5966-5968, 6004, ... inside `if (worker_ix < n_workers)`.
- Objects in scope at the call site (`P:968-970, 1006, 1051-1069`): `model` (the plugin impl, const), `outer_state` (`tron::model<qwen_3p5_4b_impl>::state&`), `gdn_executors`, the activation buffers, `q_batch`, `worker_ix`, `n_workers`, and the static `gdn_operations` / `gdn_kernels`.
- So a sibling object is reachable as a member of `outer_state`. Precedent in the generator: `W/ingest/src/TronCpp.hs:3493-3499` emits `outer_state.model_ref.expert_stats_.record_router(...)` with `MethodCall (FieldRef (FieldRef (Var "outer_state") "model_ref") "expert_stats_") "record_router" [...]`.
- The emitter is one function, `gdnExecutionCall` (`TronCpp.hs:3121-3144`). Both the main statement (3197-3198) and the helper statement (3258-3265) call it. One added argument there covers all 48 call sites.
- The 3b35 build regenerates the plugin: `E/build-3b35.sh` configures with `-DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`. The file `P` is a copy of one generated output and will be stale after a generator change.
- Other callers of `run_gdn_operation`: `W/t/t_gated_delta_net.cpp:2014` and `:2285` only. `t_generate_mock_plugin` includes `generated_gdn_scheduler.hpp`, rendered at build time by the generator, or by a prebuilt generator executable (`W/t/CMakeLists.txt:417-454`).
- No Haskell spec under `W/ingest/test` pins the text of the `run_gdn_operation` call (grep for `run_gdn_operation`, `gdn_executors`, `recurrent_chains` in `W/ingest/**/*.hs` hits only `TronCpp.hs`).
- Worker identity (`P:1065-1079`): `n_workers = 1 + n_main_helpers`. Worker 0 is the thread that called `run` (the scheduler thread, not a pool worker). Worker `1 + i` runs on pool worker `i` (`tp.enqueue_to(i, ...)`). The baseline had 55 pool workers, 40 attention workers, so 16 GDN workers.
- Layer identity: `gdn_operation_descriptor` has `operation`, `recurrent_slot`, `kernel`, `norm_epsilon` and no model layer (`W/h/tron/models/gdn_registry.hpp:64-69`). The Haskell record has `gdnModelLayer` (`W/ingest/src/Tron.hs:1095-1103`), but `gdnOperationDescriptorExpr` (`TronCpp.hs:682-694`) does not emit it. The sidecar `qwen_3p5_4b.trace.json` gives op 0..23 -> layers 0,1,2,4,5,6,...,28,29,30 (layer = op + op/3 with integer division).

## 7. forward_scope and the forward class

- `struct forward_scope : noncopyable<forward_scope>` (`attn_stats.hpp:866-883`). Constructor: `forward_scope(model_stats& s, forward_class cls, size_t n_jobs, size_t n_listeners)`. It copies `s.enabled` to `on`, takes the T1 start stamp, calls `begin_forward`. Destructor: `note_forward_wall` then `end_forward`.
- One site: `W/h/tron/models/model.hpp:2111-2115`, in `model::state::forward`, declared before `with_latch_arena latches_guard(latches);` so it is destroyed last. Class rule: `in_listener_index.size() == in_token_jobs.size() ? decode_like : prompt_or_mixed`.
- `run_forward` has only this caller (comment at `model.hpp:2174-2178`).
- Workers read the class with `current_class_ix()` (404-406), a relaxed load of `std::atomic<uint8_t> current_class`.
- Can GDN reuse the class in progress? Not from the attention object. `forward_scope` calls `begin_forward` only `if (on)`, and `begin_forward` returns before the store when `!enabled` (450-453). With TRON_ATTN_STATS unset, `current_class` stays 0 (`decode_like`) for every forward.
- The class value itself is reusable. A second scope object at the same site can take the same expression. `attn_stats::forward_class`, `CLASS_NAMES`, `CLASS_LABELS`, `N_CLASSES_2` are plain header definitions.
- Test precedent for a conditional scope: `std::optional<attn_stats::forward_scope> stats_scope; stats_scope.emplace(...)` (`W/t/t_llama_unit.cpp:3164-3167`).
- Recurrent models run one minibatch per forward: `static_assert(!recurrent_execution || max_minibatches == 1, ...)` (`model.hpp:755-756`) and `validate_recurrent_minibatch` (2348-2363). So each GDN operation runs once per forward per worker.

## 8. AMX counters that exist today

- Path counters with the `amx` path: JSON keys `ready_amx_visits`, `ready_amx_k_tokens`, `pending_amx_visits`, `pending_amx_k_tokens` (built in `put_counts`, 672-695). In totals, layer and worker leaves.
- `ready_avx_full_page_visits`, `pending_avx_full_page_visits`: AVX visits that scored a whole page, the AMX-eligible volume that did not take AMX. The note at 200-204 gives the A/B identity: the kill-switch run's value equals the AMX-on run's amx visits plus its own `avx_full_page_visits`.
- `token_jobs_by_path_set` with names `none, avx, amx, avx+amx, fpga, fpga+avx, fpga+amx, fpga+avx+amx` (forwards leaf).
- Summary facts: `amx_compiled` (set when `TRON_AMX_DISPATCH` is defined, `self_attention.hpp:477-478`), `amx_available` (`amx_attn_h128g4::available()`, `self_attention.hpp:479`; false under `TRON_AMX_DISABLE=1`, `W/src/tron/kernels/amx_attn.cpp:84-113`), plus `n_kv_heads`, `kv_mul`, `head_size`, `n_layers`, `page_size`, `n_workers`, `active_workers`, `tsc_hz`, `switch`.
- stderr line `k_tokens per layer (amx/avx/fpga)`.
- Where a visit becomes `amx`: `apply_page_tok` returns `{range_hint, int(page::page_size), attn_stats::visit_path::amx}` (`self_attention.hpp:1877-1890`), behind `if constexpr (amx_attn_h128g4::eligible<...>(operation_head_size, operation_kv_mul))`. The result type is `struct page_tok_result { const token_range* hint; int relevant_k_tokens; attn_stats::visit_path served; }` (1813-1817).
- Baseline for this model: summary `"head_size":256,"kv_mul":4`, all amx counters 0, `amx_compiled:true` (log `q35-tp4-1u-p1024__off__rep1.log`, line 187-193).
- For Part B: `facts.amx_available` is tied to the namespace `amx_attn_h128g4`. A second shape needs this fact to come from the probe that applies to the model's shape.

## 9. Test file and CMake registration

- `W/t/CMakeLists.txt:672-683`: `add_catch_test(NAME t_llama_unit FILES t_llama_unit.cpp t_attn_stats.cpp LIBRARIES tron pos_fake DEFINES _GLIBCXX_ASSERTIONS MODEL_REFERENCES llama-3.1-8b-instruct-good-tp2 eagle-llama-3.1-8b-instruct-tp2 PROPERTIES LABELS fake)`. So `t_attn_stats.cpp` is the second FILES entry of `t_llama_unit`. The comment (673-675) gives the reason: "is part of this binary so it needs no cost-data row of its own". Cost data is `W/config/test-benchmarks.json`. `W/t/AGENTS.md:23-26` asks for a refresh with `bin/slice bench --new` after a new test target.
- `t_gated_delta_net` is registered at `W/t/CMakeLists.txt:266` (`add_catch_test(NAME t_gated_delta_net LIBRARIES tron pos_fake PROPERTIES LABELS fake)`), has a cost row, and is one of the two targets `E/build-3b35.sh` builds (`TARGETS='runtron t_gated_delta_net'`).
- Structure of `W/t/t_attn_stats.cpp` (890 lines, 17 test cases, tag `[attn_stats]`):
  - Header comment says what the test protects (1-10).
  - Anonymous namespace with value-suffixed constants (`N_WORKERS_3`, `STATS_ON_TRUE`, `CYCLES_100`), `test_facts()`, `make_stats(bool, id)`, `leaf_string(path)`, and `struct stats_environment` (93-113) that calls `fuse::stats::initialize(tmpdir)` without mounting and `unmount()` on exit.
  - Cases: tally (117), rows and sums (135), path sets and forwards, `forward_scope` (304), job counts (369), out-of-range indexes die with SIGABRT via `tron::assertion_signal` from `assertion_signal.hpp` (406-452), switch off allocates nothing (456), JSON keys and size (483), FUSE registration and takeover and weak_ptr (560), off-state leaves (611), rows keyed by pool worker (640), fold (725), exit report text via `std::tmpfile` (800-852), off-state layer/worker JSON (854), EAGLE prefix (861).
  - Made-up model ids only: "a real model slug in a test source trips the CMake model-requirement audit" (628-629).
- Hook tests on real code replace the member with an enabled object: `W/t/t_llama_unit.cpp:2940-2972`, `W/t/heterogeneous_scheduler_compile.cpp:355-381`, `W/t/t_amx_dispatch_dtype.cpp:139-195`.

## 10. Proposal: the smallest gdn_stats.hpp that matches these conventions

### Files
- New `W/h/tron/models/gdn_stats.hpp`, namespace `tron::gdn_stats`, with a `Note [GDN path stats]` at the top in the style of `Note [Attention path stats]`.
- New `W/t/t_gdn_stats.cpp`, added as a second FILES entry of `t_gated_delta_net` (no new cost row, and the 3b35 recipe already builds that target).
- Edits: `gdn_execution.hpp`, `gdn_rolling_executor.hpp` (Part 0's `advance`), `model.hpp`, `ingest/src/TronCpp.hs`, `README.stats.md`, `t/CMakeLists.txt`.

### Switch
- `TRON_GDN_STATS`, exactly `"1"`, read once: copy `env_enabled()` (`attn_stats.hpp:161-172`) with the new name and warning text.
- Separate from `TRON_ATTN_STATS`, so the attention numbers of the baseline stay comparable. Campaign runs set both.

### Reused from attn_stats.hpp (include it; model.hpp already does)
`inc_relaxed`, `max_relaxed`, `min_relaxed`, `load_relaxed`, `forward_class`, `N_CLASSES_2`, `CLASS_NAMES`, `CLASS_LABELS`, `UNSET_CYCLES_0`, `LEAF_READ_ONLY_TRUE`, `is_safe_model_id`.

### Types
```cpp
enum class gdn_path : uint8_t { token = 0, column_half = 1, amx_block = 2 };
inline constexpr size_t N_PATHS_3 = 3;
inline constexpr const char* PATH_NAMES[N_PATHS_3] = {"token", "half", "amx"};

// Stack tally of one run_gdn_operation call (one worker, one operation).
struct work_tally {
  uint64_t items = 0;                       // (chain, key head) work items
  uint64_t head_tokens[N_PATHS_3] = {};     // tokens per path, once per key head
  uint64_t amx_blocks = 0;                  // blocks of 32 tokens the AMX kernel finished
  uint64_t amx_fallback_blocks = 0;         // full on-grid blocks that left AMX (non-finite) and ran column-half
  uint64_t half_full_block_tokens = 0;      // column-half tokens inside full on-grid blocks
  uint64_t start_cycles = 0;                // bind + zero or copy from source + NaN check
  uint64_t pre_cycles = 0;                  // phase 1, per token (chain path)
  uint64_t copy_cycles = 0;                 // state into the contiguous halves and back (chain path)
  uint64_t recurrence_cycles[N_PATHS_3] = {}; // token: the whole step() loop; half; amx
  uint64_t post_cycles = 0;                 // phase 3, per token (chain path)
  uint64_t write_cycles = 0;                // write_checkpoint
};
struct alignas(64) worker_op_row { /* the same fields as atomics, plus gdn_jobs, busy_cycles */ };
struct alignas(64) op_timers { std::atomic<uint64_t> wall_cycles{0}, wall_max_cycles{0}, wall_count{0}; };
struct forward_counters { forwards, wall_cycles, wall_max_cycles, token_jobs, chains,
                          n_gdn_workers_min{UINT64_MAX}, n_gdn_workers_max; };
struct header_facts { bool amx_compiled, amx_available, amx_gdn_enabled;
                      size_t block_tokens, n_key_heads, n_value_heads, key_head_dim, value_head_dim, n_operations; };
struct model_stats { const bool enabled; const std::string model_id; const bool is_eagle;
                     const header_facts facts; const size_t n_workers; const size_t n_operations; ... };
struct forward_scope;   // same shape as attn_stats::forward_scope
void register_fuse_files(std::shared_ptr<model_stats> const&);
```
- Rows: `rows[(cls * n_workers + worker) * n_operations + op]`. `n_workers` = `1 + app_pool().num_workers()`. Row index = the `worker_ix` passed to `run_gdn_operation` (0 = scheduler thread, w = pool worker w-1). No remap is needed.
- Row key is the GDN operation id, not the model layer (the C++ descriptor has no layer). Leaf name `<class>_op_<I>`.
- Unit of `head_tokens`: one token of one (chain, key head) work item. Tokens of a layer = `head_tokens / n_key_heads`. This mirrors "K tokens are counted once per kv head".
- `half_full_block_tokens` gives the A/B identity of section 8: in a run with the kill switch or the GDN switch set, it equals the AMX run's `head_tokens[amx]` plus that run's own `half_full_block_tokens`.
- Size when on, for this model on 3b35: about 19 atomics = 152 bytes, 192 bytes per row; 2 x 56 x 24 x 192 = 516,096 bytes.
- GDN wall of one operation (the design defines it as first thread's start to last thread's end): per-forward plain scratch `span[worker][op] = {t_entry, t_exit}` (raw TSC), each worker writes its own slots, the main thread zeroes it in `begin_forward` and folds it in `end_forward`: `wall = max(t_exit) - min(t_entry)` over workers with a nonzero entry, added to `op_timers`. This compares raw TSC across threads. On 3b35 the per-core offsets are at most 46 cycles apart (section 3). Keep each worker's block of slots on its own cache lines.
- Per-forward record: `forwards`, `wall_cycles` (pass wall, same stamps as T1), `token_jobs`, `chains`, smallest and largest `n_workers` seen.

### Leaves and report
- Prefix `/model/<id>/gdn` (and `gdn_eagle` for an EAGLE state, same rule). Casual, read only, not exported, no marker.
- Leaves: `summary`, `<class>_totals`, `<class>_forwards`, and when on `<class>_op_<I>`, `<class>_worker_<W>`. Off state: `summary` with `"on":false`, totals and forwards read `{}`.
- Summary keys: `on, model_id, eagle, amx_compiled, amx_available, amx_gdn_enabled, block_tokens, n_key_heads, n_value_heads, key_head_dim, value_head_dim, n_operations, n_workers, active_workers, tsc_hz, "switch":"TRON_GDN_STATS=1"`.
- stderr at destruction, same rule (on, and something counted):
  - `\n[gdn-stats] model <id>: <summary>`
  - per class: `[gdn-stats] <CLASS_LABEL> totals: {...}`, `[gdn-stats] <CLASS_LABEL> forwards: {...}`, `[gdn-stats] <CLASS_LABEL> head_tokens per op (token/half/amx): 0=a/b/c ...`, `[gdn-stats] <CLASS_LABEL> wall_cycles per op: 0=x ...`
  - The per-op wall line puts the GDN wall into the exit report, so a batch run needs no leaf poller for it.

### Exact hook points
1. `W/h/tron/models/gdn_execution.hpp:89`: add a last parameter `gdn_stats::model_stats* stats = nullptr`. A default keeps `t_gated_delta_net.cpp:2014, 2285` and a header rendered by a prebuilt generator compiling.
2. `gdn_execution.hpp:109-111`: after `if (worker_ix >= work_item_count) return;` and at the `TRACE_EVENT("model", "GatedDeltaNet", ...)`, add `const bool stats_enabled = stats != nullptr && stats->enabled;`, the entry stamp, and a stack `work_tally`. Taking the stamp where the trace slice opens keeps the counter wall equal to the traced GDN wall.
3. `gdn_execution.hpp:112-146`, per work item: stamp before `start_from_zero` / `start_from_checkpoint` (131-139), after it, after the token loop (141-143), after `write_checkpoint()` (145). Chains of 1 token and, in the base build, every chain: add `chain.order.size()` to `head_tokens[token]` and the loop time to `recurrence_cycles[token]`. With Part 0: `executor.advance(...)` takes `work_tally*` (null when off) and fills `pre_cycles`, `copy_cycles`, `recurrence_cycles[half|amx]`, `post_cycles`, `head_tokens[half|amx]`, `amx_blocks`, `amx_fallback_blocks`, `half_full_block_tokens`.
4. `gdn_execution.hpp:146` (after the loop): `if (stats_enabled) stats->note_gdn_job(worker_ix, operation_descriptor.operation.i, tally, t_entry, t_exit);` It adds the tally to the worker's row with `inc_relaxed`, adds `busy_cycles = t_exit - t_entry`, and writes the per-forward span slot.
5. `W/h/tron/models/model.hpp`: member `std::shared_ptr<gdn_stats::model_stats> gdn_path_stats;` in `struct state` (next to `self_attn_state`, line 1363). Build and register it in the constructor body (after line 1707) under `if constexpr (!gdn_operations.empty())`, with `gdn_stats::env_enabled()`, `this->cfg.id`, `model_ref.plugin.is_eagle`, facts from `gdn_kernels[0].geometry`, `1 + app_pool().num_workers()`, `gdn_operations.size()`.
6. `model.hpp:2111-2116`: compute the class once, pass it to `attn_stats_scope`, and open a `gdn_stats::forward_scope` under the same `if constexpr` (for example through `std::optional`), declared before `latches_guard`. Pass `in_token_jobs.size()` and `in_recurrent_chains.size()`.
7. `W/ingest/src/TronCpp.hs:3140`: append `MethodCall (FieldRef (Var "outer_state") "gdn_path_stats") "get" []` after `Var "n_workers"`.
8. `W/README.stats.md`: a paragraph after line 298, a row after line 352 (`/model/<model_id>/gdn/`), and the registration site in the sentence at 355-360.
9. `W/t/CMakeLists.txt:266`: `add_catch_test(NAME t_gated_delta_net FILES t_gated_delta_net.cpp t_gdn_stats.cpp LIBRARIES tron pos_fake PROPERTIES LABELS fake)`. Add a hook test in `t_gated_delta_net.cpp` that passes an enabled object to `run_gdn_operation` and checks items, tokens per path and one job per worker.
10. Recipe: add `TRON_GDN_STATS=1` to `ARMENV` in `E/run-one.sh`, a `[gdn-stats]` regex in `E/collect.py`, and a `TRON_GDN_STATS` literal check next to the `TRON_ATTN_STATS` one in `E/build-3b35.sh`. Those files are read only for this task, so the campaign needs its own copies.

### Order of commits
The design's base build is "tron without Parts 0, A and B" that still "holds the counters". So the counters (hooks 1-9, token path only) must be a commit of their own before Part 0. Part 0 and Part A then only fill more tally fields.