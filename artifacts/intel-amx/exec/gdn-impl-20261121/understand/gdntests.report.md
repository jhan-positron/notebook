# Tests and build wiring for the GDN code and the AMX code (tron commit 72e1191804)

## Short version

- The GDN test file has 33 test cases. Only 3 of them send chains of 2 or more tokens through `run_gdn_operation`. All 3 demand equal bytes against a token-by-token replay through `step()`. A fourth such test sits in `t_generate_mock_plugin.cpp`.
- A new source file needs 2 CMake lines in `src/tron/CMakeLists.txt`. A new test target needs 1 line in `t/CMakeLists.txt` and 1 row in `config/test-benchmarks.json`. A missing row does not fail at configure time. It fails the CI step `bin/slice bench --check`.
- The repository has no C++ style document. The rules come from `AGENTS.md`, `t/AGENTS.md`, the lint checks, and the conventions of the surrounding files.

## Words used here

- tron: the LLM inference program under study. R: the read-only worktree `/home/jhan/workspace/ai-runs/tron-qwen35-4b`.
- GDN: GatedDeltaNet, the recurrent layer type of Qwen3.5 4B. AMX: Intel tile-matrix instructions. bf16: the 2-byte bfloat16 number format.
- Chain: a run of consecutive tokens of one sequence that a GDN layer must take in order.
- Catch2: the C++ test framework (version v3.7.1). ctest: the CMake test runner. Slice: the repository's own test scheduler (`bin/slice`).
- Cost data: the per-test time and memory rows in `config/test-benchmarks.json` that Slice schedules with.
- CI: the automated test system. TU: translation unit (one compiled .cpp file).
- chunk: 16 FP32 values, one AVX-512 register (`TRON_CHUNK_SIZE 16`, `/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/simd/auto.hpp:18`).

## 1. /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_gated_delta_net.cpp (2,442 lines)

### 1.1 Helpers and reference implementations

First anonymous namespace, lines 34-401:
- `n_channels = 2 * chunk_size` (32) and `history_width = 3` are the convolution test sizes [lines 36-37].
- `history_index(channel, entry)` maps a channel to the kernel's packed history layout [lines 50-53].
- `recurrence_test_value(index, salt, scale)` is the deterministic input generator: `((index*29 + salt*17) % 47 - 23) * scale` [lines 55-58].
- `reference_bf16(value)` rounds through `bf16` [lines 60-62].
- `identity_conv1d_chunks<width>()` builds the identity chunk map [lines 65-71].
- `reference_conv1d_silu` is the scalar oracle of the convolution [lines 73-95]. `check_convolution(bool alias)` runs 7 steps against it with bit equality [lines 97-146].
- PyTorch golden tables (torch 2.9.1+cpu, Transformers 5.15.1) [lines 148-278]: convolution, normalization, beta, and recurrence outputs and states.
- `reference_recurrence<n_key_heads, n_value_heads, key_head_dim, value_head_dim>` is a double-precision scalar oracle of the recurrence [lines 285-374].
- `float_view(tensor)` and `run_recurrence(...)` wrap the view-based kernel `gdn_recurrence` [lines 376-399].

Second anonymous namespace, lines 947-986:
- `gdn_operation_parameters<geometry>` holds test weights for one operation. `prepare()` returns `prepared_gdn_operation<geometry>` [lines 952-984].

Third anonymous namespace, lines 1276-1623 (the executor fixtures):
- `executor_geometry` = 2 key heads, 4 value heads, key head width 16, value head width 80, 4 taps [lines 1278-1284]. Key width 32, value width 320, 384 convolution channels. One checkpoint is 25,088 bytes (computed: 4*16*80*4 + 384*3*4).
- `executor_type = gdn_rolling_executor<executor_geometry, 2>` has 1 head group. `replay_executor_type = gdn_rolling_head_executor<executor_geometry>` has 2 head groups [lines 1295-1297, 1356, 1359].
- `executor_checkpoint` is an `alignas(chunk_alignment)` byte array [lines 1307-1308].
- A block of `static_assert`s fixes type properties [lines 1327-1368]. Examples: `std::is_nothrow_default_constructible_v<executor_type>`, not copyable, nothrow movable, `start_from_zero` rejects an rvalue operation, `checkpoint_size_bytes() == gdn_fp32_checkpoint_bytes(executor_geometry)`.
- `basic_executor_token<row>` builds the 4 input rows of token N. `executor_token` uses bf16 rows. `float_executor_token` uses FP32 rows [lines 1370-1406].
- `torch_executor_output_bits` holds 320 PyTorch output words for the 4th token of a chain from zero [lines 1424-1461].
- `executor_reference::step` composes `gdn_conv1d_silu` + `gdn_recurrence` by hand [lines 1463-1510].
- `reference_executor_postprocess` rebuilds the norm and output gate with switchable rounding points [lines 1512-1557].
- `check_executor_step` steps the executor and the reference on one token and compares bits [lines 1587-1600].
- `restore_gdn_checkpoint_with_nan`, `reject_uninitialized_gdn_checkpoint_write` feed the abort tests [lines 1605-1621].

Fourth anonymous namespace, lines 1909-2096 (the replay fixtures):
- `replay_kernel` / `replay_operation` are the descriptors passed as template arguments to `run_gdn_operation` [lines 1911-1924].
- `replay_checkpoint_storage` owns a `gdn_checkpoint_table` [lines 1926-1950].
- `replay_rows` holds the activation rows as `indexed_vector<token_job_id, tensor<width>>`. These are FP32 rows, not bf16 rows [lines 1952-1976].
- `run_direct_replay` is the expected side: one `executor_type`, access `in_place`, `step()` per job of `chain.order`, then `write_checkpoint()` [lines 1984-2006].
- `run_one_replay_worker` / `run_all_replay_workers` call `run_gdn_operation<replay_operation, replay_kernel>(...)` [lines 2008-2026].
- `check_replay_outputs` compares rows with `==` [lines 2028-2035]. `make_replay_checkpoint` builds a source checkpoint with `step()` [lines 2037-2050].
- `replay_checkpoint_group(byte)` and `check_only_replay_group_written` prove that one worker wrote only its head group's bytes [lines 2052-2094].

Fifth anonymous namespace, lines 2292-2355: `run_invalid_replay` and 4 `reject_gdn_replay_*` functions (1-token chains), and `chain_plan_signal`.

Abort tests use `assertion_signal(fn)` from `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/assertion_signal.hpp:16-29`. It forks, runs `fn`, and returns the signal number. The tests expect `SIGABRT`.

### 1.2 All 33 TEST_CASEs

"Chain" column: RGO = runs chains through `run_gdn_operation`. STEP = calls `executor.step()` directly. K = calls a kernel directly. - = neither.

| Line | Name (shortened) | Checks | Geometry | Chain |
|---|---|---|---|---|
| 403 | normalization matches PyTorch BF16 boundaries | `normalize_gdn<16>` bits equal 16 torch words | head 16 | K |
| 432 | normalization rounds the epsilon operand | `normalize_gdn<128>` bits | head 128 | K |
| 460 | normalization at the Qwen head width | `normalize_gdn<128>`, 47-periodic torch words | head 128 | K |
| 488 | beta matches PyTorch BF16 sigmoid | `gdn_beta` on 8 words | scalar | K |
| 501 | softplus boundary values | `gdn_softplus` at inf, NaN, threshold | scalar | K |
| 519 | convolution matches PyTorch BF16 boundaries | weights, output, history bits | 32 channels | K |
| 570 | convolution propagates NaN | NaN reaches output and history | 32 channels | K |
| 597 | convolution step at 8192 channels | `BENCHMARK_ADVANCED` only | 8,192 channels | K |
| 625 | convolution matches a scalar oracle | 7 steps, bit equality | 32 channels | K |
| 630 | convolution with output aliasing input | same, aliased | 32 channels | K |
| 636 | recurrence matches a rectangular multi-step oracle | 3 steps of `gdn_recurrence`, abs tolerance 1e-7, aliased output equal | 2 key / 6 value heads, 32 x 48 | K |
| 720 | recurrence matches PyTorch at the Qwen head width | 2 steps, 8 outputs + 6 state values within 1e-7 | 1 / 2 heads, 128 x 128 | K |
| 785 | recurrence matches PyTorch for rectangular heads | 2 steps, 16 + 16 values within 1e-7 | 2 / 4 heads, 48 x 128 | K |
| 865 | recurrence accepts unaligned views | aligned and +1-float-offset inputs give equal results | 2 / 6 heads, 32 x 32 | K |
| 988 | operation constants are prepared once | prepared values, 4 SECTIONs with SIGABRT cases | 2 / 6 heads, 16 x 32 | - |
| 1144 | recurrence keeps tiny inputs finite | 1 step vs oracle | 1 / 1, 16 x 16 | K |
| 1191 | zero query and key head give zero | output 0, state 0.25 | 1 / 1, 16 x 16 | K |
| 1227 | recurrence step at the Qwen head geometry | `BENCHMARK_ADVANCED("gdn_recurrence<16, 32, 128, 128> step")` | 16 / 32, 128 x 128 | K |
| 1625 | helper capacity counts | `gdn_available_main_helpers(0,2)==0`, `(3,2)==5` | - | - |
| 1633 | Rolling execution matches exact BF16 composition | 4 tokens, bit equality vs reference, token 3 vs 320 torch words | 2 / 4, 16 x 80 | STEP (4 tokens, in_place) |
| 1682 | Rolling preserves BF16 semantics for float rows | FP32 rows give the bits of bf16 rows | 16 x 80 | STEP (6 tokens) |
| 1725 | Rolling checkpoints preserve the dependency chain | `GENERATE(in_place, working_copy)`, checkpoint bytes, restore, move | 16 x 80 | STEP (3 + 1 tokens) |
| 1804 | Rolling checkpoints reject invalid state | NaN at 4 offsets x 2 access modes x 2 source modes gives SIGABRT | 16 x 80 | - |
| 1823 | Resetting discards state and rebinds | restart equals a fresh executor | 16 x 80 | STEP (3 + 3 tokens) |
| 1862 | Moving transfers its chain | move construct and move assign | 16 x 80 | STEP |
| 1898 | rejects a step before any chain starts | SIGABRT | 16 x 80 | - |
| 2098 | replay shards one chain across head groups | `GENERATE(10, 1)` tokens, 4 executors, worker 0 first, then 3 `std::jthread` workers | 16 x 80 | RGO (10 tokens and 1 token) |
| 2172 | replay restores and continues in place | chains of 3, 2 and 1 tokens, source == destination in the 2nd and 3rd | 16 x 80 | RGO |
| 2237 | sibling chains share only their source | 2 chains of 2 tokens from one source, then again with `n_workers=1` and 4 executors | 16 x 80 | RGO |
| 2357 | chain planning accepts interleaved chains | `plan_gdn_chains` order | - | - |
| 2388 | chain planning accepts no work | empty plan | - | - |
| 2395 | replay rejects malformed checkpoint views | 4 SIGABRT cases | 16 x 80 | RGO (1-token chains) |
| 2403 | chain planning rejects invalid topology | 11 SIGABRT cases | - | - |

Facts about the 3 multi-token RGO cases that the chain path must respect:
- The expected side is `run_direct_replay`, which uses `step()` with access `in_place`. Outputs are compared with `==` and checkpoints byte by byte [lines 2028-2035, 2167, 2202, 2220, 2276-2277].
- The chain lists job ids out of ascending order: `{9, 0, 7, 2, 11, 4, 1, 10, 3, 8}` [line 2107]. Replay must step rows in the order `chain.order` gives.
- After worker 0 alone, every checkpoint byte outside head group 0 must still hold the fill byte 0x31, and every output column outside group 0 must still hold -1024.0f [lines 2140-2157].
- The continuation chain passes the same bytes as source and destination [lines 2208-2210].
- No test in this file runs an executor at 128 x 128. The two 128-wide tests call `gdn_recurrence` directly [lines 720, 1227].

## 2. Other tests that touch GDN

`grep -rli gdn /home/jhan/workspace/ai-runs/tron-qwen35-4b/t` returns 6 files.
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_generate_mock_plugin.cpp`: the case "TronCpp-generated GDN executes through the full scheduler" [line 726] exists only under `#if defined(TRON_GENERATED_GDN_SCHEDULER_ENABLED)` [lines 509, 765]. Its plugin geometry is 2 key heads, 4 value heads, key head width 16, value head width 16 (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/ingest/test/generated-gdn-scheduler/Main.hs:212-223`). The prompt has `2 * page_size + 2` = 130 tokens and `TRON_LIVE_TOKEN_LIMIT` is 128 [lines 677, 740]. The expected checkpoints come from `replay_generated_gdn`, which uses `step()` in place [lines 600-631]. The test demands equal checkpoint bytes, and equal logits between 0 and 1 helper threads [lines 754-762]. The generated plugin calls `tron::run_gdn_operation` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/ingest/src/TronCpp.hs:3125`).
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_llama_unit.cpp`: only compile-time checks of `gdn_geometry` and the GDN registry [lines 1245, 1275, 1312, 1357]. No kernel runs.
- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/heterogeneous_scheduler_compile.cpp`: uses `gdn_chain_plan` and `gdn_checkpoint_table` types with a 1-word mock state [lines 249-254, 1020-1053, 1770]. It does not call `run_gdn_operation`.
- `t/CMakeLists.txt` and `t/README.testing.md` mention the generated GDN plugin only.
- A test that loads Qwen3.5 4B: not found. `TRON_INGEST_TEST_MODEL_REQUIREMENTS` has no entry for it (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/model_test_selection.cmake:19-37`), and no `t_generate_ingest_1_qwen*` file exists.

## 3. /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/CMakeLists.txt (1,116 lines)

### 3.1 add_catch_test

- Definition: lines 110-221. Keywords: options `SIMPLE;HARNESS`, single values `NAME;SHARDS`, lists `FILES;PROPERTIES;LIBRARIES;DEFINES;MODEL_REQUIREMENTS;OPTIONAL_MODEL_REQUIREMENTS;MODEL_REFERENCES` [lines 111-113].
- `FILES` defaults to `${NAME}.cpp` only when it is empty [lines 119-121]. A call that passes `FILES` must list the main file too.
- The word `fake` inside `PROPERTIES` adds `fake.cpp`, whose listener calls `pos_startup()` before the tests [lines 152-154; `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/fake.cpp:14-19`]. The word `main` adds `main.cpp` and is then removed [lines 156-160].
- Every non-sharded test gets the label `slice_filter_catch2` appended to its `LABELS` [lines 165-179].
- `spdlog::spdlog TBB::tbb perfetto` and `Catch2::Catch2WithMain` are linked automatically [lines 185-188].
- Registration: `add_test(NAME ... COMMAND "${CMAKE_BINARY_DIR}/${TEST_NAME}" --benchmark-samples=2 WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}")` [lines 212-216]. One binary is one ctest test. The `catch_discover_tests` branch at line 206-210 needs `NOT DEFINED TEST_SIMPLE`, and `cmake_parse_arguments` always defines an option variable, so that branch is not taken (my reading of CMake, not executed). The comment at lines 796-797 says the same: "add_catch_test registers the whole binary as ONE ctest test".

### 3.2 The four lines asked for

- Line 266: `add_catch_test(NAME t_gated_delta_net LIBRARIES tron pos_fake PROPERTIES LABELS fake)`
- Lines 676-683: `add_catch_test(NAME t_llama_unit FILES t_llama_unit.cpp t_attn_stats.cpp LIBRARIES tron pos_fake DEFINES _GLIBCXX_ASSERTIONS MODEL_REFERENCES llama-3.1-8b-instruct-good-tp2 eagle-llama-3.1-8b-instruct-tp2 PROPERTIES LABELS fake)`. The comment above it says: "t_attn_stats.cpp ... is part of this binary so it needs no cost-data row of its own" [lines 673-675]. So `t_attn_stats` is not a target.
- Line 684: `add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake PROPERTIES LABELS fake)`
- Lines 685-687: comment "Defines CPU fakes for every amx_attn_h128g4 entry point in its own TU (see the file header), so it must not be merged with another AMX test." then `add_catch_test(NAME t_amx_dispatch_dtype LIBRARIES tron pos_fake PROPERTIES LABELS fake)`.
- `TEST_INSTALL_TARGETS` lists `t_gated_delta_net` and `t_llama_unit` but neither AMX test [lines 1022-1034].
- Core profile: `/home/jhan/workspace/ai-runs/tron-qwen35-4b/config/tests.core.txt` lists `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_llama_unit`. It does not list `t_gated_delta_net`. In a core build every test outside the list gets `DISABLED TRUE` [CMakeLists.txt lines 1054-1072].

### 3.3 Model requirement audit

- `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/model_requirement_audit.cmake` records each test's sources and declared slugs [lines 12-50] and runs `config/check_test_model_requirements.py` at configure time [lines 52-99]. A finding is `message(FATAL_ERROR "Test model requirement audit failed...")` [lines 90-96].
- The audit is called once at `t/CMakeLists.txt:1015-1020`.
- It scans the `.c/.cc/.cpp/.cxx` files of `FILES` (or `<NAME>.cpp`) for string literals equal to a known runtime model slug. It does not scan headers or generator expressions (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/README.testing.md:128-140`).
- Consequence: a real slug such as the Qwen3.5 one, written as a string literal in a new test file without a `MODEL_REQUIREMENTS`, `OPTIONAL_MODEL_REQUIREMENTS` or `MODEL_REFERENCES` declaration, fails configure. `t_attn_stats.cpp:628-629` notes the same trap.
- A test with `MODEL_REQUIREMENTS` is omitted when a slug is not selected, and that is a configure error under `TRON_REQUIRE_ALL_MODEL_TESTS=ON` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/model_test_selection.cmake:55-71`).

### 3.4 Cost data for a NEW test target

- Nothing checks `config/test-benchmarks.json` at configure time. No CMake file references it (grep for `test-benchmarks` matched no `.cmake` or `CMakeLists.txt`).
- CI runs `bin/slice bench --check` after the build (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/.github/workflows/cmake-single-platform.yml:358-361` and `gcp-nix.yml:503-505`).
- A test with no row on any platform prints `error: bench entries missing from every platform: <names>` and exits 1 (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/bin/slice:2114-2125`). A row missing only on the current platform is a warning [bin/slice:2127-2132].
- At run time a test without a row runs in the "unbenched phase" at 2 slices (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/doc/slice.md:147-152`).
- Rows are written by `bin/slice bench --update <test>` or `bin/slice bench --new` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/AGENTS.md:23-26`).
- Current rows: `t_gated_delta_net` exists only under `genoa96`. `t_amx_numerics` and `t_amx_dispatch_dtype` exist under `genoa96` and `granite_rapids_6962p` (computed from the JSON). Row format: `{"name":"t_gated_delta_net","filter":"","labels":["fake"],"times":{"1":0.339,"2":0.335,"4":0.342},"max_rss_mb":{"1":8,"2":7,"4":8}}` [config/test-benchmarks.json:171].

## 4. /home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/CMakeLists.txt

- `tron` is a STATIC library [lines 187-205].
- AMX block, lines 218-223:
```cmake
if(TRON_AMX_DISPATCH)
  target_sources(tron PRIVATE kernels/amx_attn.cpp)
  set_source_files_properties(kernels/amx_attn.cpp PROPERTIES
    COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
  target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)
endif()
```
- The comment at lines 207-217 says the kernel bodies live in "one isolated translation unit that alone receives the -mamx-* flags".
- Lines 335-338 pass `TRON_AMX_DISPATCH` to `tron_model_compile_config` (INTERFACE). The generated model objects therefore see the define. This matters for a GDN call site inside `#ifdef TRON_AMX_DISPATCH`, because `run_gdn_operation` is instantiated in the generated plugin.
- `tron` has PUBLIC options `-mavx512f;-mavx512dq;-mavx512bw;-mavx512vl;-mavx512vbmi2;-mavx512vpopcntdq;-mavx512vp2intersect;-mavx512bf16` [line 271] and `-O3;-DTRON_IGNORE_NAN;-DTRON_IGNORE_FTZ` outside Debug [lines 291-294]. Test TUs get these, and never the AMX flags.
- `lto(tron)` adds `-flto=thin` unless COVERAGE is set [line 262; `/home/jhan/workspace/ai-runs/tron-qwen35-4b/CMakeLists.txt:128-138`].
- The option is declared OFF by default (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/CMakeLists.txt:46`). The `native` preset does not set it. Only the `deb` preset sets `"TRON_AMX_DISPATCH": "ON"` (`CMakePresets.json:68`). The CMake CI lane passes `-DTRON_AMX_DISPATCH=ON` (`cmake-single-platform.yml:353-355`). A setting in `flake.nix` or `nix/`: not found.

## 5. The two AMX tests

### 5.1 /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_amx_numerics.cpp (288 lines)

- Whole body is inside `#ifdef TRON_AMX_DISPATCH` [line 22]. The `#else` arm is one case that calls `SUCCEED("build without TRON_AMX_DISPATCH - nothing to test")` [lines 282-286].
- It imports the shape constants by name: `GROUP_HEADS_4`, `HEAD_SIZE_128`, `PAGE_TOKENS_64`, `TILE_ROWS_16` [lines 37-40].
- Helpers: `bf16_rne`, `bf16_trunc`, `bf16_to_float` on bit patterns [lines 46-64], `qk_inputs` and `fill_qk` with `std::mt19937` [lines 69-83].
- Case 1 [line 87]: `STATIC_REQUIRE`s on `query_scalar_ok` and `eligible`. It runs on every host. It includes `STATIC_REQUIRE_FALSE(eligible<tron::bf16>(HEAD_SIZE_128, 2))` and `STATIC_REQUIRE_FALSE(eligible<tron::bf16>(64, GROUP_HEADS_4))` [lines 112-113].
- Case 2 [line 116]: layout of `pack_q_group_128x4`. "a scalar copy, no AMX instruction runs, so this runs on every host" [lines 118-121].
- Case 3 [line 148] QK and case 4 [line 194] PV: each starts with
```cpp
if (!tron::amx_attn_h128g4::available()) {
  WARN("AMX unavailable on this host - QK precision check skipped");
  return;
}
```
  So on a CPU without AMX the case passes with a warning. It is not a Catch2 `SKIP`.
- Error band: `tol = 1e-4 * abs_mass + 1e-6` for QK [line 187]. PV checks an exact round-to-nearest reference within `acc_slack`, and the AVX reference within `envelope + acc_slack` [lines 267-274], and requires `total_rounding_gap > 0.0` [line 279].
- Kernel calls are bracketed by `begin_region()` / `end_region()` [lines 161-167, 247-250]. The PV output buffer has `TILE_ROWS_16 * HEAD_SIZE_128` floats [lines 245-246].

### 5.2 /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_amx_dispatch_dtype.cpp (288 lines)

- It drives the production `apply_page_range` on a model with 4 heads, 1 KV head, head size 128, for the executors `host_bf16`, `host`, `host_fp16` [lines 70-90, 260-283].
- It defines CPU fakes for all 6 entry points of `namespace tron::amx_attn_h128g4` [lines 228-257]: `available()` (returns `fake_amx_available`), `begin_region()`, `end_region()`, `pack_q_group_128x4`, `qk_rowmajor_128x4`, `weights_times_v_128x4`. The fakes count calls in `probe` [lines 53-61].
- The file header states the mechanism: "This translation unit defines every amx_attn_h128g4 entry point as a CPU fake, so the linker never pulls libtron's amx_attn.cpp object" [lines 4-8]. This works because `tron` is a static archive.
- The fakes are defined outside the `#ifdef`. The test case is inside `#ifdef TRON_AMX_DISPATCH` [line 259], with a `SUCCEED` case in the `#else` arm [lines 284-287]. It needs no AMX CPU.
- It also checks the attention statistics against the fake call counts [lines 138-152, 191-216].

### 5.3 What a new entry point or namespace requires there

- Rule: if the link of `t_amx_dispatch_dtype` needs any symbol that only `amx_attn.o` defines, the linker loads `amx_attn.o`. That object also defines the 6 faked functions. The link then fails with duplicate definitions.
- `self_attention.hpp:479` calls `amx_attn_h128g4::available()` without any shape test. Every model state references it.
- A new function in `amx_attn_h128g4` that the 128 x 4 path calls needs a fake with the exact signature in this file.
- A new namespace `amx_attn_h256g4` defined inside `amx_attn.cpp` needs fakes only if the 128 x 4 llama instantiation references one of its symbols. Call sites kept behind `if constexpr (amx_attn_h256g4::eligible<...>(...))`, as the 128 path does at `self_attention.hpp:1877`, leave no reference. An unconditional call such as a second `available()` in the stats header facts would need a fake.
- If the dispatch is changed to call a new shared probe instead of `amx_attn_h128g4::available()`, `fake_amx_available` no longer steers the test. The test then fails on a host without AMX.
- `amx_gdn`: the llama plugin of this test has no GDN layer, so no fake is needed. This holds only while `amx_gdn.cpp` is its own object. If `amx_gdn.cpp` calls `amx_attn_h128g4::available()`, binaries that use it load `amx_attn.o` too, which is harmless outside this test.
- `t_llama_unit.cpp:99-107` names `qk_rowmajor_128x4` and `weights_times_v_128x4` in `requires` probes, and lines 512-519 use `PAGE_TOKENS_64` and `HEAD_SIZE_128`. A rename of these breaks that file.
- A test that drives `apply_page_range` on a 256-wide head with 4 query heads per KV head: not found. The only such geometry, `attention_geometry geometry_2{16, kv_geometry{4, 256}}` at `t_llama_unit.cpp:1544`, feeds compile-time registry checks.

## 6. How tests are run

- Preferred environment: `nix develop --accept-flake-config` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/AGENTS.md:60-64`). The non-Nix path is supported and deprecated.
- One test: `make t_foo`. It runs `cmake --build gen --target t_foo -j $(NPROC_BUILD)` and then `gen/t_foo` from the repository root (`GNUmakefile:1028-1037`). `NPROC_BUILD` is `min(nproc, 16)` [GNUmakefile:92-94].
- The build directory is `gen/` and the test binary is `gen/t_<name>` (`CMakePresets.json` preset `native`; `t/CMakeLists.txt:214`). Every test's working directory is the repository root [t/CMakeLists.txt:215].
- Suites: `make test-host` = `bin/slice run --filter=host --exclude-tag=slow`. `make test-host-old` = `ctest -LE fpga --test-dir gen --output-on-failure -j` (`GNUmakefile:1056-1057, 1073-1074`). CI runs `bin/slice run --filter=host` (`cmake-single-platform.yml:465-473`).
- Required check order for a C++ change: build and run `t_<name>`, then `make build-test` and `make test-host` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/.agents/skills/run-tron-tests/SKILL.md`, section "Choose checks by change"). Run `bin/slice route` before substantial tests (`AGENTS.md:85-93`).
- `SYSTEM_CONFIG=--instance i,n` is set by Slice, not by ctest (`t/CMakeLists.txt:934-938`; `t/AGENTS.md:17`). The runtime reads it in `src/system/system.cpp:949`.
- The campaign's own recipe on delphi-3b35 (the test server): `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/build-3b35.sh:29` configures with `--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DDEV_MODEL_CONFIG=$WT/models.gdn.yaml` and builds `runtron t_gated_delta_net` [line 30]. `clock-probe.sh:50-56` ran the test as `cd /var/tmp/jhan/b35-gdn-base && SYSTEM_CONFIG="--instance 1,2" taskset -c "$CPU" gen/t_gated_delta_net "<case name>" --benchmark-samples 300`.
- With that one-model registry, `t_generate_mock_plugin` is omitted, because its `MODEL_REQUIREMENTS mock-host` is not selected (`t/CMakeLists.txt:401-405, 129-133`). So the generated-GDN scheduler case is not built by the 3b35 recipe.

## 7. Lint and format checks

- Authoritative: the Nix check `checks.x86_64-linux.lint-toolchain` in `/home/jhan/workspace/ai-runs/tron-qwen35-4b/flake.nix` [lines 2272-2460]. `/home/jhan/workspace/ai-runs/tron-qwen35-4b/lefthook.yml` mirrors it for pre-commit (`AGENTS.md:72-76`).
- clang-format: `clang-format-19 --dry-run -Werror` over `h/**/*.{hpp,h,i}`, `src/**/*.cpp`, `t/**/*.cpp`, `t/**/*.hpp` (`flake.nix:2333-2343`; `lefthook.yml:44-62`; `GNUmakefile:835-838`). Fix with `make format` [GNUmakefile:961-965]. Config: `/home/jhan/workspace/ai-runs/tron-qwen35-4b/.clang-format`: `ColumnLimit: 88`, `IndentWidth: 2`, `ContinuationIndentWidth: 4`, `AlignAfterOpenBracket: DontAlign`, `BinPackParameters: false`, `AlwaysBreakTemplateDeclarations: Yes`, `BreakConstructorInitializers: BeforeComma`, `IncludeBlocks: Regroup` (bare system headers, then headers with a slash, then quoted headers), `AllowShortIfStatementsOnASingleLine: WithoutElse`, `InsertBraces: false`.
- `clang-format-19` on this agent machine: not found (`which` returned nothing). On delphi-3b35: not checked.
- Whitespace: `git diff --check origin/main HEAD -- ':!lib/**'` [GNUmakefile:826-828; lefthook.yml:15-28].
- No `<cassert>`: grep over `h src t` [GNUmakefile:829-834; flake.nix:2317-2330].
- Note references: `make lint-notes` runs `/home/jhan/workspace/ai-runs/tron-qwen35-4b/bin/lint-notes` over headers, `t/*.hpp`, all `.cpp` under `t` and `src`, `doc/*.md`, the ingest `.hs` files and a fixed CI list [GNUmakefile:807-817, 30-82]. A Note definition is `Note [Name]` followed by a `~~~` rule. The `]` must be on the same line and the name needs 5 or more characters [bin/lint-notes:20-26, 115-116]. A reference to an undefined Note fails [lines 279-287]. An unreferenced Note is a warning only [lines 288-291]. `bin/lint-notes` with no file arguments exits 1 [lines 261-264].
- A script that checks comment style: not found.
- `bin/ci/lint-ci-pins.sh` runs when any `CMakeLists.txt` changes [lefthook.yml:246-250].
- Include-what-you-use (`make iwyu-check`) exists [GNUmakefile:1150-1151]. A CI workflow step that runs it: not found.
- `.editorconfig`: 2 spaces, LF, final newline, no trailing whitespace.

## 8. Coding rules for new C++ code, with the source of each

Repository documents (`docs/` does not exist. The folder is `doc/`. `CONTRIBUTING`: not found. `/home/jhan/workspace/ai-runs/tron-qwen35-4b/CLAUDE.md` is the single line `@AGENTS.md`.)

From `/home/jhan/workspace/ai-runs/tron-qwen35-4b/AGENTS.md`:
- C++23, limited to the standard library of libstdc++ 12, in `src/`, `h/` and `t/`. Traps named there: `<format>`, `<print>`, `ranges::contains`, `ranges::fold_*`, `ranges::to`, C++23 range adaptors, `std::expected` monadic operations [lines 65-71].
- "Use `h/common/assert.hpp`, never `<cassert>`. Treat NaN as corruption and check the exact IEEE 754 condition intended; infinities may be valid identities." [lines 80-82].
- Follow `.editorconfig`. Run the format target of every changed language [lines 72-76].
- Pin every dependency to an exact version [line 77].
- The public API is `h/libtron.hpp` plus what it exports. Preserve it [lines 78-79].
- Test policy [lines 20-56]: every committed test must run in CI. Name the incorrect behaviour a new test would catch. Do not derive expected results from the logic under test. A regression test must fail without the fix. Prefer extending the closest existing test. "do not create a dedicated CI job when an existing suite can carry them".
- Pull request policy [lines 10-18]: add the label `Skip benchmarks`. Do not add `Run CI` unless told.
- "Keep changes request-scoped, preserve behavior and APIs, and match local patterns." [lines 125-127].

From `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/AGENTS.md`:
- Test files start with `t_`. Use `add_catch_test()`. Choose `pos_fake` unless real FPGA behaviour is needed [lines 5-12].
- Deterministic seeds. Use `h/common/assert.hpp` [line 13].
- "Do not delete, skip, or weaken existing assertions." [line 21].
- Refresh `config/test-benchmarks.json` after adding or materially changing a test [lines 23-26].

From the code itself (convention, no document):
- Assertions: `TRON_ASSERT(cond, fmt, args...)`, `TRON_ASSERT_EQ/NE/LT/LE/GT/GE(a, b)`, `TRON_ABORT(...)` (`/home/jhan/workspace/ai-runs/tron-qwen35-4b/h/common/assert.hpp:66-86`). The header undefines `NDEBUG`, so they are always on [lines 3-5].
- Attributes go through the macro `TRON(...)`, for example `TRON(nodiscard, inline, const)` and `TRON(noinline)` (`h/common/attributes.hpp:24`; `h/tron/kernels/gated_delta_net.hpp:118, 168`).
- Kernels and executor methods are `noexcept` (`gated_delta_net.hpp:123, 239`; `gdn_rolling_executor.hpp:315`; every AMX entry point in `amx_attn_iface.hpp:171-243`).
- GDN files use lower_snake `inline constexpr` names without a value suffix (`gdn_conv1d_kernel_size`, `gdn_qk_norm_epsilon`, `gated_delta_net.hpp:19-20, 154`), east const (`size_t const`), and scratch tensors declared `{uninitialized}` (`gdn_rolling_executor.hpp:197-198, 326-327`).
- AMX files use upper-case names with the value as suffix: `HEAD_SIZE_128`, `PAGE_TOKENS_64`, `GROUP_HEADS_4`, `TILE_ROWS_16`, `Q_PACK_ELEMS_2048`, with `static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value")` (`amx_attn_iface.hpp:130-144`). The same style appears in `t_attn_stats.cpp:36-64` and `attn_stats.hpp:116-157`.
- Long explanations are `Note [Name]` blocks referenced by "See Note [Name]".
- The AMX interface header holds no intrinsics, and the kernels sit in a TU of their own (`amx_attn_iface.hpp:2-5`).
- Environment switches are read once and exactly `"1"` turns them on: `TRON_AMX_DISABLE` (`src/tron/kernels/amx_attn.cpp:85-89, 103-113`), `TRON_ATTN_STATS` (`attn_stats.hpp:8-17, 159-167`).

From the user's own guide (not in the repository): `/home/jhan/.claude/skills/cpp-coding-guide/SKILL.md`:
- Fixed values are named `constexpr` variables in upper case with the value appended (`MAX_RETRIES_3`). Literal 0 and `alignas(64)` are allowed. A bool passed as a call or template argument gets a name such as `ROW_ALIGNED_TRUE` [lines 10-21].
- Control-flow bodies need braces unless the whole statement is on one line [lines 40-44].
- Hot paths: no zero-filled scratch when the next writer sets every element, pass views instead of copies, test the condition before preparing a branch's inputs [lines 55-61].
- The user's memory notes limit the value-suffix names to AMX kernel files and keep the local idiom in shared files (`/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/value-suffix-names-shared-files.md`), and forbid issue or pull-request numbers in code comments (`.../memory/no-issue-numbers-in-source.md`).

## 9. Exact CMake lines

(a) `/home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/CMakeLists.txt`, inside `if(TRON_AMX_DISPATCH)`, after line 221:
```cmake
  target_sources(tron PRIVATE kernels/amx_gdn.cpp)
  set_source_files_properties(kernels/amx_gdn.cpp PROPERTIES
    COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
```
Three comments then state something false and need an edit: `src/tron/CMakeLists.txt:210-211` ("one isolated translation unit that alone receives the -mamx-* flags"), `src/tron/kernels/amx_attn.cpp:2-3` ("The ONLY translation unit compiled with -mamx-tile/-mamx-bf16"), `h/tron/kernels/amx_attn_iface.hpp:4-5`.

(b) `/home/jhan/workspace/ai-runs/tron-qwen35-4b/t/CMakeLists.txt`, after line 684:
```cmake
add_catch_test(NAME t_amx_gdn_numerics LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```
Plus one row for `t_amx_gdn_numerics` in `config/test-benchmarks.json` on at least one platform, or CI fails at `bin/slice bench --check`. Optional: a line in `config/tests.core.txt` if the test must run in the core profile.
Variant without a new cost-data row (the `t_attn_stats.cpp` precedent):
```cmake
add_catch_test(NAME t_amx_numerics FILES t_amx_numerics.cpp t_amx_gdn_numerics.cpp
  LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```
Do not add the file to `t_amx_dispatch_dtype` [t/CMakeLists.txt:685-686].

(c) A new file for the GDN statistics, here called `t_gdn_stats.cpp`. Variant without a new cost-data row, replacing line 266:
```cmake
add_catch_test(NAME t_gated_delta_net FILES t_gated_delta_net.cpp t_gdn_stats.cpp
  LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```
Variant as its own target (needs a cost-data row):
```cmake
add_catch_test(NAME t_gdn_stats LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```
`t_attn_stats.cpp` includes `system/fuse_stats.hpp` and `system/fuse_sysfs.hpp` and links only `tron pos_fake`. Its fixture `stats_environment` initializes the statistics tree in a temporary folder and never mounts it [t_attn_stats.cpp:91-113].

## 10. Existing tests whose behaviour is expected to change when chains of 2+ tokens take a new code path

Code path changes, result must stay equal (these become the equal-bytes proof of Part 0 against the token path):
- `t_gated_delta_net.cpp:2098` "replay shards one chain across head groups", the 10-token arm. Value heads are 80 columns wide, which is 5 chunks.
- `t_gated_delta_net.cpp:2172` "replay restores and continues in place", the 3-token and the 2-token chain.
- `t_gated_delta_net.cpp:2237` "sibling chains share only their source", both 2-token chains, in both passes.
- `t_generate_mock_plugin.cpp:726` "TronCpp-generated GDN executes through the full scheduler", only in builds that define `TRON_GENERATED_GDN_SCHEDULER_ENABLED`. Value heads are 16 columns wide, which is 1 chunk.

Not affected, if `step()` and the kernel `gdn_recurrence` keep their behaviour:
- Lines 1633-1898 call `step()` directly, including with access `working_copy` [line 1730].
- Lines 403-1227 call kernels directly.
- Lines 2395 and 2292-2343 use 1-token chains. Their aborts fire in the checks of `run_gdn_operation` before any executor call (`h/tron/models/gdn_execution.hpp:103, 121-123, 134`).
- The 1-token arms of lines 2098 and 2172 keep `step()` in place.

Part A (AMX block path, 128 x 128 only): no existing test has an executor at 128 x 128, so none changes. Part B (256 x 4): no existing test drives that shape through `apply_page_range` (not found), so none changes at run time. The files that name the 128 shape must still compile.