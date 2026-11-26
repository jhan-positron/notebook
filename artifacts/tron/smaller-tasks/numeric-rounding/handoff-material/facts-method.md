## Short version

Issue #5433 defines a measurement on three builds of the GDN host code, read once by a four-case rule, and nothing was measured as of 2026-11-22 [G3].
The repository holds the two kernel benchmark cases and general TVD tools, but it holds no six-out build, no replay benchmark and no script for the TVD test or the loss tests, and the Qwen3.5 4B generation test exists only on the branch of draft PR #3215 [C10][C14][X4].
Our own scripts can give a TVD per decode step between the AMX block kernel and the chain kernel from one binary with a run-time switch, and they cannot give the distance to the Transformers model [L3][L4][C19].

## Words used here

- tron: the inference program under test. runtron: its command-line tool.
- GDN: GatedDeltaNet, the recurrent layer type of the model Qwen3.5 4B.
- GDN host code: the C++ code that computes a GDN layer on the host CPU (kernels plus the executor that calls them).
- AMX, AVX-512: CPU instruction sets.
- bf16 (BF16): a 16-bit float format with 8 significant bits. FP32: the 32-bit float format.
- Rounding: one call that rounds an FP32 value to the nearest bf16 value (`round_to<bf16>`, `round_chunk_to<bf16>`).
- all-22, six-out, fourteen-out: the three builds of issue #5433 (all 22 roundings in, the six normalization roundings out, fourteen roundings out).
- Logits: the scores of all vocabulary words for the next token.
- TVD: total variation distance between two next-token distributions. It is 0 for identical distributions and 1 for distributions that share no token.
- Position: one token of a text. A decode step: one forward pass that scores one new token after the prompt.
- Forced run: a run in which every generated token is taken from a file (runtron option `--force-feed-text-token-file`). Free-running run: a run in which the sampler picks every token.
- Card run: a run that uses the FPGA cards. Host build: a build that runs on the CPU only.
- Transformers: the Hugging Face Python library that holds the reference model.
- GPTQ: a 4-bit weight quantization. The served Qwen3.5 4B checkpoint is the GPTQ form of the upstream weights.
- Golden store: the folder `/scratch/test/data`, in which each file is named by the SHA-256 of its bytes.
- Catch2: the C++ test framework of tron. `BENCHMARK_ADVANCED` is its macro for a timed case.
- Token kernel: `gdn_recurrence`, one token per call. Chain kernel: `gdn_recurrence_chain`, our AVX-512 kernel that gives the same bits. Block kernel: our AMX kernel that advances 32 tokens per call.
- Arm: one build with one set of switches. Build tags of our campaign: ctr (commit 0d69ef3ce8), pa (775bba7661), pab (882e5322f1).
- GDN switch: `TRON_AMX_GDN_DISABLE=1`, which turns only the block kernel off. Kill switch: `TRON_AMX_DISABLE=1`, which turns every AMX kernel off.
- tp4: one engine on four FPGA cards.
- est.: an estimate, not a measurement.

## 0. About this report, and corrections to the task text

- Subject: the measurement method of issue #5433 and the tools that exist to run it.
- The facts were collected on 2026-11-23 by a read-only fact reader. Nothing was built, run on a card, or changed on GitHub.
- The task names `/home/jhan/workspace/intel-AMX/GDN/exec/gdn-impl-20261121/`. That folder does not exist [X1].
  The scripts are in `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/` and `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/` [X1].
- The task names `/home/jhan/workspace/intel-AMX/GDN/exec/results/`. The results are in `/home/jhan/workspace/intel-AMX/exec/results/` [X1].
- The test `t_generate_ingest_1_qwen3_5_4b_fpga` is not a generated test. It is a hand-written source file on the branch of PR #3215 [C14].

## 1. The method of issue #5433

### 1.1 Sources and state

- The issue is open. It was created on 2026-11-18 and has two comments [G1].
- Comment 1 (2026-11-22 03:32 UTC) says that PR #5571 is the trial side and that neither side has been measured [G2].
- Comment 2 (2026-11-22 18:38 UTC) holds the thresholds. Its first line is: "The thresholds, as step 1 of the proposal asks. Nothing is measured yet." [G3]
- PR #5571 is a draft. Its body says: "Neither side has been measured; #5433 decides whether this lands once its figures are in." [G4]
- Comment 2 changes three points of the issue body [G1][G3]:
  - The body proposed two builds. The comment has three.
  - The body proposed TVD "in Python on a host CPU". The comment takes the logits from card runs.
  - The body compared against "the all-float32 model". The comment compares against "the Transformers model in BF16".

### 1.2 The procedure

1. Make three builds of the GDN host code [G3].
   - all-22: "all 22 roundings in". PR #5571 says these are the "22 calls on #3221's branch" [G4].
   - six-out: "only the six normalization roundings out". This build does not exist yet. The comment says: "#5571 removes all fourteen, so I add the six-out build and compare fourteen-out with it, to judge the eight alone." [G3]
   - fourteen-out: "all fourteen out (#5571)".
2. Build each of the three twice. The comment says: "Each is built for kernel timing and again for FPGA cards, where the issue has two host builds." [G3] Section 1.3 gives the reading of these two phrases.
3. Run the speed tests. The judged comparison is fourteen-out against six-out [G3].
   - Reading rule, quoted: "A speed test reads faster when the 95% interval of the relative gain over paired runs lies above 0, otherwise no gain when its upper end is under r, otherwise undecided."
   - The thresholds r, quoted: "r is 9% for `gdn_conv1d_silu<8192>`, 0.85% for `gdn_recurrence<16, 32, 128, 128> step`, 1.95% for a 128-token replay through the executor, and 0.35% for decode tokens a second per user on four cards (Qwen3.5-4B and 27B, each at 1, 2, 4 and 8 users, eight tests; 1,991-token prompts)."
   - That is 11 speed tests: 3 kernel cases and 8 card tests.
   - The replay case is new: "The replay is a third timed case, added because the executor has no benchmark."
   - Origin of the kernel thresholds: "The three kernel values are half the gains predicted for all fourteen, and those predictions are inferred."
   - Two more timings judge nothing: "Fourteen-out and six-out are also each timed against all-22; those figures go into #5571's description and judge nothing."

   | Speed test | r (relative gain) | Count |
   |---|---|---|
   | `gdn_conv1d_silu<8192>` (convolution benchmark case) | 9 % | 1 |
   | `gdn_recurrence<16, 32, 128, 128> step` (recurrence benchmark case) | 0.85 % | 1 |
   | 128-token replay through the executor | 1.95 % | 1 |
   | decode tokens per second per user, four cards, Qwen3.5 4B and 27B, 1, 2, 4 and 8 users, prompts of 1,991 tokens | 0.35 % | 8 |

4. Run the TVD test on the 4B model [G3].
   - Quoted: "The TVD test reads little when, on the 4B over 768 positions of one 8,192-token text, the mean TVD between fourteen-out and six-out is at most a tenth of the all-22 build's mean TVD from the Transformers model in BF16 (the issue has the all-float32 model); above that it reads not little."
   - Source of the logits, quoted: "The logits come from card runs, where the issue sketches Python, because a card run executes the kernels themselves."
   - So the test needs two mean TVD values over the same 768 positions: fourteen-out against six-out, and all-22 against the Transformers model in BF16. The limit is 0.1 times the second value.
5. Run three damage tests on the 4B model [G3].
   - Definition, quoted: "Loss is the mean negative log-probability of that text's own next token."
   - Test 1, quoted: "The first passes when the 95% interval of the rise in loss ends at or under a tenth of the all-22 build's loss gap to the Transformers model."
   - Test 2, quoted: "The second passes when the interval of that rise's growth from the text's first quarter to its last does too."
   - Test 3, quoted: "The third passes when six-out and fourteen-out each pass both cases of `t_generate_ingest_1_qwen3_5_4b_fpga`."
6. Apply the validity rule, quoted: "A test whose runs break the rules fixed for them beforehand reads undecided, whatever its figures." [G3]
7. Read the results once, "when every run above has ended". The first case that holds applies [G3]:
   1. "The TVD test reads not little: the eight stay and #5571 shrinks to the six."
   2. "Every speed test reads no gain: #5571 shrinks to the six."
   3. "The TVD test reads little, every speed test reads faster and every damage test passes: #5571 keeps the fourteen."
   4. "Anything else: I decide from the results, and #5571 does not change before that."

Fixed before any measurement: the six normalization roundings come out in every case. The issue body says: "They come out in this follow-up whatever the measurement says about the other eight." [G1]

### 1.3 What "built for kernel timing" and "built for FPGA cards" mean

The issue does not define the two phrases. The reading below is tied to code, and it is a reading, not a quote.

- "Built for kernel timing" most likely means a host build of the test program `t_gated_delta_net`.
  - The issue body sizes the work as "one Python script and two host builds of `t_gated_delta_net`" [G1].
  - `t_gated_delta_net` holds the two benchmark cases [C8][C9].
  - It links the libraries `tron pos_fake` and carries the label `fake`, so it opens no FPGA card [C10].
- "Built for FPGA cards" most likely means a build whose programs load the Qwen3.5 plugin and drive real cards.
  - The comment takes the TVD logits "from card runs" and the decode rate "on four cards" [G3].
  - The generation test of damage test 3 links `tron full_scheduler`, needs the model `ingested-qwen-3.5-4b-tp4`, and takes the resource lock `fpga` [C14].
- Not verified: which program gives the card logits and the decode rate (runtron, the generation test, or the CI benchmark tool), and which CMake preset and options each build uses. The measurement script of the GDN owner, or a question on the issue, would settle it.

### 1.4 What the issue leaves unsaid

A person who repeats the method needs these points. None is written on the issue or in PR #5571 as of 2026-11-23 [G1][G3][G4].

Text and positions:

- Which 8,192-token text is used, and which tokenizer settings give 8,192 tokens (chat template or raw text, with or without a start token).
- Which 768 of the 8,192 positions are scored (the last 768, a spread, or another choice).
- How a card run gives logits at those positions. runtron writes a "Logits" record only for the last prompt token and for each decode step [L3][X6]. So one possible layout is a prompt of 7,424 tokens followed by 768 forced decode steps. The issue does not say this.
- Whether the TVD uses the softmax of all vocabulary logits at temperature 1.

The Transformers side:

- Which Transformers version runs the model. The repository pins 5.15.1 [C5]. The issue says that 5.17 and later normalize in float32, and that PR #5124 moves the reference to 5.20.2 [G1]. PR #5124 is an open draft [G8].
- Which weights the Transformers model loads. The golden test says that its CPU references use "BF16 over the upstream HuggingFace checkpoint" and that the served checkpoint "is its 4-bit GPTQ quantization" [C15]. With upstream weights, the gap of the all-22 build to the Transformers model includes the quantization error.
- Whether the Transformers model runs the text in one forward pass or token by token with a cache. The two paths differ: the reference docstring says that a cached decoding step uses `torch_recurrent_gated_delta_rule`, that prefill uses `torch_chunk_gated_delta_rule`, "whose results differ by rounding" [C2].
- The torch version, the CPU, and the attention implementation.

Statistics:

- The number of paired runs per speed test, and how a pair is formed.
- The definition of "relative gain" (of time per call, or of rate), and the method that gives the 95 % interval.
- The unit of the 95 % interval of the loss tests (positions, or runs), and whether "the text's first quarter to its last" means quarters of the 8,192 tokens or of the 768 positions.
- "The rules fixed for them beforehand": the rules themselves (load limits, repeat counts, discard rules) are not on the issue.

Machines and builds:

- The machine and CPU pinning for the kernel timing, and the machine and the four cards for the card tests.
- The benchmark options (sample count, warm-up) for the two Catch2 cases.
- The 128-token replay case has no code. PR #5571 at 69cc70fae0 holds the same two benchmark cases as its base and no third one [C9].
- The six-out build has no branch. Five fetched branches contain 127a662083: the branch of PR #3221, three later branches of the same stack, and the branch of PR #5571. The first four hold the same count of rounding lines as 127a662083, and PR #5571 is the fourteen-out build [X4].
- The card builds need the model and the test from another line of branches. 127a662083 and 69cc70fae0 do not register Qwen3.5 4B in `config/models.yaml` [X5]. The generation test is on PR #3215's branch, and 127a662083 is not an ancestor of that branch [X3]. The issue does not say how the three variants are combined with the registration and the test.
- The slug and the weights of the 27B model, the source of the 1,991-token prompts, and the number of generated tokens of the decode tests. The number 1,991 does not occur in the benchmark configuration of the repository at 127a662083 [X7].
- Damage test 3 reads a skip as a skip, not as a pass: the test skips when fewer or more than four FPGA devices are visible, and CTest maps exit code 4 to "skipped" [C14][C15]. The issue does not say that a skip fails the damage test.

## 2. Where the pieces live in the repository

Commit ids: main = f454423b09, PR #3696 head = 72e1191804, PR #3221 head = 127a662083, PR #5571 head = 69cc70fae0, PR #3215 head = cb9a5dc070 [X2][G5][G6][G7].

### 2.1 The reference `gated_delta_net_with_state`

- File `ingest/runtime/tron_ingest_runtime/ops.py`, lines 544-692 at 127a662083 [C1].
- The file is byte-identical at f454423b09, 72e1191804, 127a662083 and 69cc70fae0 (blob e4bf672f3d) [X2]. PR #5571 lists "The reference in `ops.py`" under "Not in this PR" [G4].
- `gated_delta_net` (lines 472-541) is the wrapper that starts from zero states and calls it [C1].
- `_qwen_l2norm` (lines 695-698) is the query and key normalization [C1].

How it runs on BF16 tensors [C1]:

- The function takes the dtype of its inputs. It has no dtype argument: `hidden_dtype = mixed_qkv.dtype` (line 636).
- Convolution: the sum is float32 and is rounded once. `conv_sum = full_window.new_zeros(full_window.shape[:-1], dtype=torch.float32)` (line 650), then `conv_out = conv_sum.to(conv1d_w.dtype)` (line 653).
- SiLU: `mixed = F.silu(conv_out).to(hidden_dtype)` (line 655). So the SiLU result is a BF16 value.
- Beta: `beta = b_t.sigmoid()` (line 662). The sigmoid runs in the dtype of `b`, so it gives a BF16 value.
- Normalization: `q = _qwen_l2norm(q).float()` and `k = _qwen_l2norm(k).float()` (lines 668-669). The normalization runs in BF16 and the result is cast to float32 afterwards. This is the origin of the normalization roundings.
- Recurrent state: float32 only. Another dtype raises `ValueError` (lines 605-609).
- Output: `.to(hidden_dtype)` at lines 678, 685 and 687.
- The function has no switch that leaves a rounding out. A six-out or fourteen-out variant in Python would be new code.

How the Transformers model can use it [C3]:

- `ingest/export/qwen3_5_export.py` replaces the `forward` of the Transformers class `Qwen3_5GatedDeltaNet` with `_gated_delta_net_forward` (lines 22-72), which calls `gated_delta_net`.
- The patch is registered with `for_reference=False` (lines 155-161). So it applies to the export path only. A reference run keeps the forward of Transformers.
- The C++ kernels name this function as their reference: `h/tron/kernels/gated_delta_net.hpp` line 26 and `t/t_gated_delta_net.cpp` line 162 at 127a662083 [C4].

### 2.2 The Transformers pin

| Place (same lines at f454423b09, 72e1191804, 127a662083) | Pin |
|---|---|
| `flake.nix:42` | `github:huggingface/transformers/v5.15.1` |
| `bin/pyproject.toml:10` | `transformers>=5.15,<5.16` |
| `ingest/export/pyproject.toml:12` | `transformers>=5.15,<5.16` |
| `ingest/export/uv.lock:1134-1151` (127a662083) | 5.15.1 |
| `ingest/runtime/pyproject.toml:20` | `transformers>=5.12,<5.13` (test extra) |
| `ingest/runtime/uv.lock:1400-1417` (127a662083) | 5.12.1 |

- Evidence for the table: [C5].
- The pinned 5.15.1 is the version that normalizes in BF16, by the issue's statement [G1].
- The tables in `t/t_gated_delta_net.cpp` were made with "Transformers 5.15.1's torch_recurrent_gated_delta_rule ... under torch 2.9.1+cpu" (lines 247-248 at 127a662083) [C6].
- PR #5124 ("fix: Bump Transformers to 5.20.2 for Muse Spark") is an open draft. Its base is a feature branch, not main [G8]. So no commit named in this report pins 5.17 or 5.20.2.

### 2.3 The two benchmark cases

| Case | Lines at 127a662083 | Measured call |
|---|---|---|
| `gdn_conv1d_silu<8192>` | test case 594-621, `BENCHMARK_ADVANCED` at 596, `meter.measure` at 616-618 | `gdn_conv1d_silu(output, history, input, prepared_weights, source_chunks)` at 8,192 channels |
| `gdn_recurrence<16, 32, 128, 128> step` | test case 1233-1280, `BENCHMARK_ADVANCED` at 1235, `meter.measure` at 1274-1277 | `run_recurrence<16, 32, 128, 128>(...)`: 16 key heads, 32 value heads, head width 128 |

- Evidence for the table: [C8].
- The same two cases exist at every commit named here. Line numbers of the two `BENCHMARK_ADVANCED` lines: 570 and 1200 at f454423b09, 599 and 1229 at 72e1191804, 606 and 1313 at 69cc70fae0, 601 and 1231 at our 882e5322f1 [C9].
- They are Catch2 benchmarks. The program is built by `add_catch_test(NAME t_gated_delta_net LIBRARIES tron pos_fake PROPERTIES LABELS fake)` and links `Catch2::Catch2WithMain` [C10].
- How a case is run: call the test program with the name of the test case. Catch2 runs a benchmark unless `--skip-benchmarks` is given. Our own unit-test script passes `--skip-benchmarks`, so our records hold no timing of these cases [L8].
  - Example, not run by this reader: `./gen/t_gated_delta_net "GatedDeltaNet convolution step at 8192 channels" --benchmark-samples 100`.
  - The repository gives one written example of the form, for another test: `// Run: gen/t_mask "[bench]" --benchmark-no-analysis` [C11].
  - The two GDN cases carry the tags `[gated-delta-net][conv1d]` and `[gated-delta-net][recurrence]`, not a `[bench]` tag [C8].
- Not verified: the sample count and options that the GDN owner uses. The only earlier timing on the issue is "5204-5952 ns a convolution call at 8192 channels" with the three history roundings and "4093-4830 without" [G1].

### 2.4 The test `t_generate_ingest_1_qwen3_5_4b_fpga`

Where it exists:

| Commit | Test source and CMake entry |
|---|---|
| f454423b09 (main) | absent |
| 72e1191804 (PR #3696) | absent |
| 127a662083 (PR #3221) | absent |
| 69cc70fae0 (PR #5571) | absent |
| cb9a5dc070 (PR #3215, draft, "Add the Qwen3.5 4B FPGA golden test") | present |

- Evidence: a search of `t/` and `config/` for the test name at each commit, and a search of 201 related branches [X3][C14].
- At the three commits without it, `t/CMakeLists.txt` builds `t_generate_ingest_1_${model}` in a loop over the list `TRON_SELECTED_INGEST_TEST_MODELS` (lines 359-375 at 127a662083), and no Qwen3.5 source file is in `t/` [C13].
- At cb9a5dc070 the test is defined by hand in `t/CMakeLists.txt` lines 392-398 [C14]:
  `add_catch_test(NAME t_generate_ingest_1_qwen3_5_4b_fpga FILES t_generate_ingest_1_qwen3_5_4b_fpga.cpp ${TEST_GENERATION_SUPPORT} LIBRARIES tron full_scheduler MODEL_REQUIREMENTS ingested-qwen-3.5-4b-tp4 PROPERTIES RESOURCE_LOCK fpga LABELS fpga SKIP_RETURN_CODE 4)`, with the labels `ingest`, `skip_return_code_4` and `min_slices_4`.
- cb9a5dc070 contains 72e1191804. It does not contain 127a662083 [X3]. Its GDN kernel, executor and test files are the same blobs as at 72e1191804 [X3].

Its two cases (file `t/t_generate_ingest_1_qwen3_5_4b_fpga.cpp` at cb9a5dc070) [C15]:

1. "Qwen3.5-4B FPGA free-runs unambiguous CPU HuggingFace references" (lines 135-165).
   - It runs only the reference cases whose margins are all at least 3.0 logit units (`kReferenceStrictTop1Margin = 3.0f`, line 47).
   - It generates freely with top-k 1 and temperature 0, and requires `response == expected`.
2. "Qwen3.5-4B FPGA tracks CPU HuggingFace reference logits" (lines 167-252).
   - It force-feeds the reference tokens and takes the logits of the card run (`LogitsMode::NATIVE`).
   - It requires the reference token within the best 10 scores, or within the best 32 where the reference margin is under 0.25 (lines 39-40, 211-224).
   - It requires rank 0 where the margin is at least 3.0 (lines 225-228).
   - Between 0.25 and 3.0 it allows top-1 misses up to max(3, one quarter of those positions) (lines 242-251).
   - It computes no TVD.

The data it reads [C15][C16][X8]:

- One file: `/scratch/test/data/673c337bf8596443b10c07276f60f21aeb44248028f102bef457ab2e74c9c99f` (constant `kReferenceCasesHash`, lines 36-37; path built by `tron::test_data_path`, `t/testutil.cpp` lines 76-79).
- It is a JSON file. Each case holds `label`, `prompt` (token ids), `response` (token ids) and `margins` (top-1 minus top-2 logit of the reference, per response token) (lines 75-90).
- It reads no separate token file and no golden-logits file.
- The file exists on this host (claude-agentsrv), 14,009 bytes, dated Oct 30. Its content is in section 5.
- Not verified: that the file exists on delphi-3b35. The command `ls -la /scratch/test/data/673c337b*` on that machine would settle it.

Its skip rules (lines 52-66) [C15]: it skips when the model is not registered in the build, when the weights are missing, and when the number of visible FPGA devices is not exactly four.

### 2.5 Tools that compute TVD or compare logits

A search for "tvd" and "total variation" at 127a662083 and at f454423b09 gives the same file list in `ingest/`, `bin/`, `t/`, `src/` and `h/` [X9].

| Tool (lines at 127a662083) | What it compares | Notes |
|---|---|---|
| `tvd_from_logits`, `src/tron/generation/stats.cpp:66-77` | two logit vectors of one position | softmax of each, then half the sum of absolute differences |
| `compute_tvds`, `t/testutil.cpp:100-153` | logits of a card run against a golden-logits file, per position | reads the file with `load_logits_by_hash` (lines 81-98): per position an 8-byte length and FP32 values |
| `check_golden_logits`, `t/testutil.cpp:274-289` | the same, with a TVD cap, an outlier rule and a top-k overlap rule | used by the generation tests of other models |
| `force_generate`, `t/force_generate.cpp:360-378` | none; it produces the logits | runs a text as prompt plus forced steps with `LogitsMode::ALL`, which returns logits for every position, the prompt included (`t/force_generate.hpp:17-29`) |
| `ingest/export/reference_logits.py` (console script `tron-reference-logits`, reached through `bin/extract_logits`) | none; it produces golden logits | runs a Transformers model on a text file on the CPU and stores logits and tokens in the golden store (lines 126-179, options 202-282) |
| `ingest/runtime/tron_ingest_tools/logit_test.py:368-457` | the Transformers model against the generated Python model | computes `max_tvd` and `mean_tvd` (lines 418-423); has `--dtype bfloat16` (lines 520-526); default test texts are at most 256 tokens (lines 191-228) |
| `bin/compare_intermediates` | a runtron intermediates log against a Transformers intermediates log | relative L2 error per record, no TVD (lines 1-22) |

- Evidence for the table: [C17][C18][C19][C20][C21].
- An example of the full pattern "card logits against Transformers logits, TVD per position" is `t/t_generate_ingest_1_gemma_3_4b.cpp` lines 50-68: tokens and logits made by `bin/extract_logits ... --max-tokens 10 --save-tokens --scratch-dir /scratch/test/data`, then `force_generate`, then `check_golden_logits(logits, golden_hash, 0.05, ...)` [C22].
- No such test exists for Qwen3.5 4B at any commit named here [X3].
- Three properties of `reference_logits.py` matter for issue #5433 [C19]:
  - It runs the whole text in one forward pass: `logits = model(token_ids).logits` (lines 174-175). For Qwen3.5 that is the chunk path of Transformers, not the cached step path [C2].
  - It does not pass a dtype: "Deliberately do NOT pass `dtype`" (lines 290-294). So BF16 is not forced by an option.
  - Its defaults are 2 layers and 40 tokens (`--max-layers` default 2, `--max-tokens` default 40).
- Not verified: that `reference_logits.py` loads and runs Qwen3.5 4B. A trial run in the export environment (`make ingest-deps`) with the upstream weights would settle it. The upstream weights are not on this host: `/opt/positron/weights/huggingface/Qwen/Qwen3.5-4B` is absent on claude-agentsrv [X8].

The runtron options that record scores are below. The line numbers are those at 127a662083, and the same options exist at our 882e5322f1 [C23][C24][C25].

| Option | What it writes |
|---|---|
| `--intermediates-file FILE` | A text log of every logged vector: "file to write intermediates log to (default log_intermediate.txt); implies --log-intermediates" (`src/runtron.cpp:124-126`). Line format: the message right-aligned in 50 characters, then ` (<len>): `, then each value with width 11 and 8 significant digits (`h/tron/models/model.hpp:1733-1745`). |
| record "Logits of token N" | All `vocab_size` logits of one scored position (`model.hpp:4099-4106`). Under logging, the code waits for the full output buffer: "logging is coded to just read the output buffer" (`model.hpp:4079-4082`). |
| records "Top-k Logits of token N" and "Top-k Token IDs for Logits of token N" | The best scores, sorted, and their token ids (`model.hpp:4128-4133`). Our Qwen3.5 4B runs gave 320 values per record [X10]. |
| `--force-feed-text-token-file FILE` | Nothing. It reads: "force token selection from a whitespace-separated token-id file" (`src/runtron.cpp:114-115`). The ids are a continuation and no start token is added (`h/runtron/stream_generate.hpp:1292-1296`). |
| `--text-token-file FILE` | Nothing. It reads a prompt as token ids: "whitespace-separated decimal token ids, blank lines ignored, '#' starts an end-of-line comment" (`src/runtron.cpp:108-110`). |
| `--output-token-file FILE` | The generated token ids (`src/runtron.cpp:127`). |
| `--pay-for-determinism` | Nothing. It fixes the execution order: "pay the performance cost of deterministic execution" (`src/runtron.cpp:129-130`). |

- runtron writes "Logits" and "Top-k Logits" records for the last prompt token and for each decode step only. A trial with a prompt of 64 tokens and 2 generated tokens gave 2 "Top-k Logits" lines [X6]. The parser of our comparison script states the same rule [L3].

## 3. Our own tools and data

All scripts below run on delphi-3b35 and refuse another host, except where noted. This reader read them and did not run them.

### 3.1 `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/` and `../gdn-20261120/run-one.sh`

| Script | What it does (one sentence) | Inputs (environment) | What it writes |
|---|---|---|---|
| `build.sh` [L1] | Builds tron targets at one commit with the plugin of Qwen3.5 4B only, in the tree `/var/tmp/jhan/b35-gdn-$TAG`. | `TAG`, `SHA` (both required), `TARGETS` (default `runtron t_gated_delta_net`), `JOBS` (36), `CPUS` (96-135), `REG` (model list), `CONF_FLAGS` (default `-DTRON_AMX_DISPATCH=ON`) | `exec/logs/gdn-impl-20261121-build-$TAG.log`, `exec/results/gdn-impl-20261121/build-$TAG.txt` and `build-$TAG.done` |
| `../gdn-20261120/run-one.sh` [L2] | Runs one runtron `stream-generate-text` run on our half of the cards (`SYSTEM_CONFIG="--instance 1,2"`) after a load snapshot, and refuses the run when our cards or CPUs are busy. | `RUN` (required), `MODEL` (`ingested-qwen-3.5-4b-tp4`), `USERS` (1), `PROMPT` (1024), `LEN` (256), `ARMENV`, `EXTRA` (extra runtron arguments), `TAG` (base), `TMO` (2400 s), `NAME` | `exec/results/$NAME/rt/$RUN.log`, `load/$RUN.txt`, one block in `rt-results.txt` |
| `campaign.sh` [L4] | Runs the speed campaign: every arm in every cell, with the arm order rotated per repetition. | `CELLS`, `ARMS` (default `base p0 b ab a0 a`), `REPS` (3), `FIRST_REP` | `rt/<cell>__<arm>__rep<N>.log`, `load/`, `rt-results.txt`, a log and a marker |
| `token-check.sh` [L5] | Runs each arm once with temperature 0 and `--pay-for-determinism`, and compares the generated token ids of every arm with the arm `base`. | `PROMPTS` (default `1024 4096`), `LEN` (256), `ARMS` | `tokens/p<prompt>__<arm>.txt`, `tokens/summary.txt` |
| `logit-margin.sh` [L6] | Runs arms with `--intermediates-file` on the local disk, keeps only the "Top-k Logits" and "Top-k Token IDs for Logits" lines, and deletes the large file. | `PROMPT` (1024), `LEN` (4), `ARMS` (default `base b`), `MAX_GB` (60), `PER_TOKEN`, `TMO` (1500 s) | `tokens/logits-p<prompt>-l<len>__<arm>.txt`, `tokens/logits-summary-p<prompt>-l<len>.txt` |
| `logit_summary.py` [L7] | Prints, per arm and generated step, the best and second-best token with their scores and the margin in bf16 steps. | arguments: tokens folder, prompt, len, arms | standard output (saved by `logit-margin.sh`) |
| `unit-tests.sh` [L8] | Runs the unit-test programs of the builds ctr, pa and pab with `--skip-benchmarks`, and the pab programs again under each switch. | `TAGS`, `TESTS`, `OUT` | `unit-tests.txt`, `unit/<tag>__<test>__<env>.txt` |
| `e4b-check.sh` [L9] | Checks on Gemma 4 E4B which attention kernel each layer takes and whether AMX on and AMX off give the same tokens. | `TAG` (e4b), `MODELS`, `PROMPTS` (1024), `LEN` (128), `ARMS` | `exec/results/gdn-e4b-20261122/{rt,load,tokens}/`, `tokens/summary.txt` |

The arms, from `campaign.sh` lines 10-18 and 35-42 [L4]:

| Arm | Build tag (commit) | Extra environment | Meaning |
|---|---|---|---|
| base | ctr (0d69ef3ce8) | none | token loop for GDN, AVX-512 attention |
| p0 | pab (882e5322f1) | `TRON_AMX_DISABLE=1` | chain kernel, AVX-512 attention |
| b | pab | `TRON_AMX_GDN_DISABLE=1` | chain kernel, AMX attention |
| ab | pab | none | AMX block kernel, AMX attention |
| a0 | pa (775bba7661) | `TRON_AMX_GDN_DISABLE=1` | chain kernel, AVX-512 attention |
| a | pa | none | AMX block kernel, AVX-512 attention |

- The pair a0 and a is one binary. Only the GDN switch differs. So it isolates the block kernel [L4].
- The switch is read once per process (`src/tron/kernels/amx_gdn.cpp:150`; "Both are read once", `h/tron/kernels/amx_gdn_iface.hpp:87-90` at 882e5322f1) [C27]. So the two arms need two processes.
- The build records name the trees `/var/tmp/jhan/b35-gdn-pa` (775bba7661) and `/var/tmp/jhan/b35-gdn-pab` (882e5322f1) on delphi-3b35, built on 2026-11-22 [L10]. Not verified: that the trees still exist today. `ls /var/tmp/jhan/b35-gdn-*/gen/runtron` on delphi-3b35 would settle it.

### 3.2 `/home/jhan/workspace/intel-AMX/exec/dd/` and `/home/jhan/workspace/intel-AMX/exec/td-20261016/`

| Tool | What it computes | Record format it expects |
|---|---|---|
| `dd/dd_logits_step.py` [L3] | Per decode step, between two forced runs: top-1 of each arm, the margin in logit units and in bf16 steps, the rank of the forced token, mean and maximum absolute logit change, the fraction of changed logits, and the TVD. | Two runtron `--intermediates-file` logs (or their "Logits of token" lines), plus the forced token file. Step k is the line "Logits of token P-2+k" for prompt length P. |
| `dd/dd_first_divergence.py` [L11] | The first (token, layer, stage) record at which two intermediates logs differ, with the relative L2 error, the largest change in bf16 steps and the fraction of changed elements per record. No TVD. | Two full `--intermediates-file` logs. It keys on the first 50 characters of each line. |
| `dd/dd_intermediates.py` [L12] | The shared parser of the log lines. | The line format of `log_intermediate` (section 2.5). |
| `td-20261016/probe-td.sh` [L13] | Ran eight arms of the model qwen3-4b as forced runs with the full intermediates kept, then called `dd_logits_step.py` on ten pairs. It ran on delphi-3bda with the whole machine. | Writes `runs.txt`, `tokens.txt`, `steps-<a>-vs-<b>.{json,txt}`, `verdict.txt`. |
| `td-20261016/analyze-td.sh` [L14] | Called `dd_first_divergence.py` on the pairs, in parallel. | Writes `layers-<a>-vs-<b>.{json,txt,csv}`. |
| `td-20261016/tiestats/tie_stats.py` [L15] | Statistics of near-tie flips from the `steps-*.json` files. For the TVD it gives count, median, 10th, 5th and 95th percentile, minimum and maximum (function `dist`, lines 60-63; used at line 147). It gives no mean. | `steps-*.json` of `dd_logits_step.py`. |
| `td-20261016/ktest/` [L16] | A stand-alone C++ program that measures the attention kernels (QK and PV products) bit by bit. It is about attention, not GDN. | Its own inputs. |
| `td-20261016/replay/` [L17] | A numpy replay of tron's software attention on logged Q, K and V vectors of layers 0 and 1. It is about attention, not GDN. | Lines "WQ roped", "WK roped", "WV", "WO" taken from a full intermediates log by `extract.sh`. |

The TVD per step exists in one place [L3]:

- File `exec/dd/dd_logits_step.py`, function `main`, line 128: `"tvd": float(0.5 * np.abs(softmax(lo) - softmax(ln)).sum()),`.
- `softmax` is at lines 65-68. It runs in float64 over the whole logit vector.
- The summary holds the maximum only: `"max_tvd": float(max(r["tvd"] for r in ok)) if ok else None,` (line 155).
- The mean TVD is not printed. Every step row of the output JSON holds its `tvd`, so the mean is one more line of code.
- The script has no loss (negative log-probability) field.

The forced-run recipe exists in one place [L13]:

- `probe-td.sh` lines 85-88 give the full command: `--temperature 0 --pay-for-determinism -s 1 --output-token-file ... --intermediates-file ... --force-feed-text-token-file "$FORCED"`.
- Line 91 keeps the score lines: `grep -E 'Logits of token' "$D/$name.full" > "$D/$name.txt"`.
- The forced file was the token output of an earlier free-running run of one arm (lines 3-4 and 38).
- The script is tied to delphi-3bda: it sources campaign helpers of that machine and stops the serving units. It cannot run on delphi-3b35 as it is.

### 3.3 Existing results that need no new run

`/home/jhan/workspace/intel-AMX/exec/results/` (sizes from `du -sh`) [X11]:

| Folder | Size | Content |
|---|---|---|
| `gdn-20261120/` | 51 MB | the design campaign: `bench`, `leaves`, `load`, `plugin`, `rt`, `trace`, `rt-results.txt`, `collected.json`, `predictions.json`, `build-base.txt` |
| `gdn-impl-20261121/` | 14 MB | the implementation campaign; see below |
| `gdn-e4b-20261122/` | 719 KB | the Gemma 4 E4B check: `rt`, `load`, `tests`, `tokens`, `rt-results.txt` |

Inside `gdn-impl-20261121/` [X11]: `tokens/` (1.4 MB), `rt/` (4.3 MB), `load/` (2.2 MB), `unit/` (323 KB), `bench/` (504 KB), `trace/` (3.6 MB), `build-<tag>.txt`, `rt-results.txt`, `collected*.json`, `comparison*.json`, `unit-tests.txt`.

What `gdn-impl-20261121/tokens/` holds [X10]:

| File | Content |
|---|---|
| `p1024__<arm>.txt`, `p4096__<arm>.txt` | 256 generated token ids per arm, free-running, temperature 0 |
| `summary.txt` | the comparison of the prompt-4096 files: every arm equals the arm base at 256 of 256 positions |
| `logits-p1024-l4__{base,b,ab}.txt` | 4 decode steps: 8 lines per file, 31,192 bytes |
| `logits-p1024-l190__{base,a}.txt` | 190 decode steps (token positions 1023 to 1212): 380 lines per file, 1,481,620 bytes |
| `logits-summary-p1024-l4.txt`, `logits-summary-p1024-l190.txt` | best token, second token and margin per step and arm |

Facts about the `logits-*` files, computed today from the files [X10]:

- Each step holds two lines: "Top-k Logits of token N (320)" and "Top-k Token IDs for Logits of token N (320)". So each step holds the 320 best scores, not the whole vocabulary.
- The runs were free-running, not forced [L6].
- Arm base against arm a (prompt 1024, 190 steps): the best token is the same at 185 of 190 steps. The first step with another best token is generated step 185.
- The same pair differs in its scores from the first step on: at generated step 0, 60 of the 320 values differ.
- The token files agree with this: at prompt 1024, the arms a, a2, ab and ab2 first differ from base at generated token 185, and the arms b, b2 and bonly at generated token 1. The arms orig, p0, a0 and base2 equal base at all 256 tokens.
- These files cannot give the TVD of issue #5433. The reasons: they hold 320 of the vocabulary scores, and the two arms do not hold the same 320 tokens at a step.

`/home/jhan/workspace/intel-AMX/exec/results/td-20261016/` (201 MB), names only [X11]:

- `layers-<a>-vs-<b>.{csv,json,txt}` for the ten pairs baseoff-vs-base, baseoff-vs-newoff, baseoff-vs-pocoff, base-vs-new, base-vs-poc, clean-vs-baseoff, clean-vs-new, newoff-vs-trunc, new-vs-newoff, new-vs-trunc.
- `steps-<a>-vs-<b>.{json,txt}` for the same ten pairs.
- `runs.txt`, `tokens.txt`, `verdict.txt`, `probe.done`, `rt/`.
- These are results of the model qwen3-4b (attention work for issue #4444). Every `steps-*.json` holds a `tvd` per step, so they show the output format that a GDN run would give.

## 4. What a TVD measurement of our AMX GDN kernel would need

Goal: "mean TVD between the AMX block kernel build and the chain kernel build over N positions of one text".

### 4.1 The shortest procedure with the tools that exist

1. Binary: `gen/runtron` of build tag pa (commit 775bba7661) on delphi-3b35 [L10]. One binary serves both arms.
   - Chain kernel arm (a0): environment `TRON_AMX_GDN_DISABLE=1`.
   - Block kernel arm (a): no switch.
   - With tag pa the attention kernels are AVX-512 in both arms, so only the GDN kernel differs [L4].
2. Forced token file: run arm a0 once, free-running, through `run-one.sh` with `EXTRA="--temperature 0 --pay-for-determinism --output-token-file F"` and `LEN=N`. The file F then holds N token ids. `token-check.sh` already does this step for `LEN=256` [L5].
3. Record: run each arm once more through `run-one.sh`, with
   `EXTRA="--temperature 0 --pay-for-determinism --force-feed-text-token-file F --intermediates-file /var/tmp/jhan/<arm>.full --output-token-file /var/tmp/jhan/<arm>.tokens"`, the same `PROMPT`, and `LEN=N` [L2][L13].
4. Keep the score lines: `grep -a -E 'Logits of token' <arm>.full > <arm>.txt`, then delete the `.full` file [L13].
5. Check: the output tokens of both arms must equal F at all N positions (`probe-td.sh` lines 108-116 show the check) [L13].
6. Script: `python3 exec/dd/dd_logits_step.py --off a0.txt --on a.txt --forced F --out steps.json` [L3].
7. Mean TVD: the mean of `steps[].tvd` over the rows of `steps.json`.

### 4.2 The missing pieces

| # | Missing piece | Evidence |
|---|---|---|
| M1 | A wrapper script for steps 2 to 5 on delphi-3b35. `logit-margin.sh` is not forced and keeps the Top-k lines only. `probe-td.sh` is tied to delphi-3bda. | [L6][L13] |
| M2 | The mean TVD. `dd_logits_step.py` prints the maximum only. | [L3] |
| M3 | A control run: the same arm twice, forced, to show that two runs of one arm give a TVD of 0. Our records show that a repeat run gives the same 256 tokens (base2 = base, a2 = a, b2 = b, ab2 = ab at prompt 1024). They do not show equal logits. | [L5][X10] |
| M4 | Proof that the "Logits of token N" record is written in a Qwen3.5 4B tp4 run. The code writes it under logging. The kept files hold Top-k lines only. `grep -a -c -E '^ *Logits of token' <file>` on one new intermediates file would settle it. The plain pattern also counts the two Top-k lines (corrected 2026-11-23 after a check). | [C24][L6] |
| M5 | Disk and time limits for a long text. See the estimates below. `logit-margin.sh` stops above `MAX_GB=60` and sets `TMO=1500` s. | [L6] |
| M6 | A text. With step 2, the "text" is runtron's shipped prompt plus the chain arm's own continuation. A given text of 8,192 tokens needs a token-id file for `--text-token-file`. `run-one.sh` always passes `--prompt-length` and no prompt file, so it needs `EXTRA` or a change for that. | [L2][C23] |
| M7 | The loss of the damage tests. No script computes the negative log-probability of the forced token. The data of step 4 would hold what it needs. | [L3] |

Size of one run, from measured file sizes [X6]:

- Measured: 9,441,623,564 bytes for prompt 1024 plus 4 generated tokens, and 11,706,285,068 bytes for prompt 1024 plus 190 generated tokens.
- est. 12.18 MB per decode step: (11,706,285,068 - 9,441,623,564) / 186 = 12,175,599 bytes.
- est. 9.17 MB per prompt token: (9,441,623,564 - 4 x 12,175,599) / 1,024 = 9,172,775 bytes.
- est. 18.7 GB for prompt 1024 plus 768 forced steps.
- est. 77.4 GB for prompt 7,424 plus 768 forced steps (8,192 tokens in total).
- The free space on `/var/tmp/jhan` was 3,145 GB on 2026-11-22.
- Measured wall time: two runs of prompt 1024 plus 190 tokens took 582 s together (02:01:01 to 02:10:43 UTC).

### 4.3 What the procedure measures, and what it cannot give

- It measures the block kernel through the prompt only.
  - The block kernel advances one block of 32 consecutive tokens (`BLOCK_TOKENS_32 = 32`) [C26].
  - The executor gives it "a full window" only: "A full window takes the block kernel when the kernel serves the geometry and is available on this machine." [C28]
  - A forced token is one decode step, so it is a window of one token.
  - So the TVD at the forced positions shows how the state that the block kernel built over the prompt changes later scores.
  - Not verified by a run: the split "prompt windows take the block kernel, decode steps do not". The GDN counters (`TRON_GDN_STATS=1`) of one forced run would settle it.
- It gives no logits at positions inside the prompt. runtron writes the "Logits" record for the last prompt token and for decode steps only [X6][L3].
  - An in-process alternative exists: `tron::generate` with `LogitsMode::ALL` returns logits "including those in the prompt" [C18]. No test or script for Qwen3.5 4B uses it. That route is new C++ code.
- It cannot give the distance to the Transformers model in BF16.
  - No tool in our folders runs the Transformers model.
  - The repository tool `reference_logits.py` can store Transformers logits for a text, but it is not proven for Qwen3.5 4B, it does not force BF16, and it runs the chunk path (section 2.5) [C19].
  - No script compares a runtron "Logits" text record with a golden-logits binary file. `compute_tvds` does this inside a C++ test only [C17].
  - So the limit of the issue's TVD test ("a tenth of the all-22 build's mean TVD from the Transformers model in BF16") cannot be computed with our tools as they are.
- It cannot give the six-out against fourteen-out comparison of the issue. Those builds belong to the GDN owner, and the six-out build does not exist [X4].
- Our commits sit on another version of the GDN host code than the one the issue measures.
  - Our base 72e1191804 does not contain the commit of PR #5462 (2559c133df), which removed the three history roundings [G9]. 127a662083 contains it [X12].
  - 72e1191804 and 127a662083 are not ancestors of each other. The four GDN files differ by 982 added and 408 removed lines between them [X12].
  - So a result on our tree is not a result on the all-22 build of the issue.

## 5. The Qwen3.5 4B generation test and golden data

- The model's branch 72e1191804 holds no golden data and no generation test for this model [X3].
  - Its only change to the registry is the entry `qwen_3p5_4b` in `config/models.yaml` lines 812-824 (the commit touches this one file, 14 added lines) [C29].
  - The entry has no `trace_dir` line [C29].
- The entry says that the tokens of this model are not yet valid [C29]:
  - Line 814: `support_level: cpp_plugin`.
  - The legend at lines 2-7 of the same file: `#   cpp_plugin - full ingest pipeline; C++ plugin compiles; tokens not yet valid` and `#   working    - end-to-end: valid tokens in and out`.
- Our campaign builds copy this entry word for word, with `support_level: cpp_plugin` [L18].
- The branch of draft PR #3215 (cb9a5dc070) raises the level: `config/models.yaml` line 842 there reads `support_level: working` [C16]. PR #3215 is not merged [G7].
- The golden file of that PR exists on this host. Its content, read today [X8]:
  - 12 cases and 215 reference tokens in total.
  - Prompt lengths from 20 to 137 tokens. Eleven prompts have 20 to 30 tokens. One prompt (`paris_cite_boundary`) has 137 tokens.
  - Per case: prompt ids, response ids and margins. It holds no logits.
  - Its header: `transformers_version = 5.15.1`, `torch_version = 2.9.1+cpu`, `attention_implementation = eager`, `reference = direct CPU PyTorch/Transformers greedy generation over unquantized HF weights`.
- The generator of that file loads the Transformers model in BF16 on the CPU: `dtype=torch.bfloat16`, `device_map="cpu"`, `attn_implementation="eager"` (`ingest/export/qwen3_5_4b_reference.py` lines 188-198 at cb9a5dc070). It decodes token by token with a cache (lines 279-311) [C16].
- Consequences for any claim about "correct" tokens:
  - At 72e1191804, the repository has no oracle for the tokens of Qwen3.5 4B, and the registry says the tokens are not yet valid.
  - With PR #3215, the oracle covers 215 tokens after prompts of at most 137 tokens. It does not cover prompts of 1,024 tokens or more, where our campaign ran.
  - The oracle compares a 4-bit GPTQ model on cards with unquantized BF16 weights on the CPU. Its contract allows another best token at low margins [C15].
  - Inference, not verified by a run: eleven of the twelve golden prompts are shorter than one 32-token block, so the block kernel would not run on their prompts. The GDN counters of one run of the test would settle it.

## References

GitHub (read on 2026-11-23 with `gh ... --repo positron-ai/tron`, read only):

- [G1] Issue #5433 body. https://github.com/positron-ai/tron/issues/5433 (open, created 2026-11-18T16:25:34Z).
- [G2] Issue #5433 comment 1. https://github.com/positron-ai/tron/issues/5433#issuecomment-7073599234 (2026-11-22T03:32:04Z).
- [G3] Issue #5433 comment 2, the thresholds. https://github.com/positron-ai/tron/issues/5433#issuecomment-7083755152 (2026-11-22T18:38:17Z).
- [G4] PR #5571 body. https://github.com/positron-ai/tron/pull/5571 (draft, open, head 69cc70fae0, base = the branch of PR #3221, updated 2026-11-23T18:19:31Z).
- [G5] PR #3221. https://github.com/positron-ai/tron/pull/3221 (open, not draft, head 127a662083).
- [G6] PR #3696. https://github.com/positron-ai/tron/pull/3696 (open, head 72e1191804).
- [G7] PR #3215 "Add the Qwen3.5 4B FPGA golden test". https://github.com/positron-ai/tron/pull/3215 (draft, open, head cb9a5dc070, found with `gh pr list --head rbjarnason/qwen35-33-e2e-goldens --state all`).
- [G8] PR #5124 "fix: Bump Transformers to 5.20.2 for Muse Spark". https://github.com/positron-ai/tron/pull/5124 (draft, open, head d9df90c99d, base is a feature branch).
- [G9] PR #5462 "Stop rounding GDN convolution history entries on read". https://github.com/positron-ai/tron/pull/5462 (merged 2026-11-21T00:33:34Z).

Code in the clone `/home/jhan/workspace/tron` (read with `git -C /home/jhan/workspace/tron show <commit>:<path>` and `git grep -n`):

- [C1] `ingest/runtime/tron_ingest_runtime/ops.py` at 127a662083: `gated_delta_net` 472-541, `gated_delta_net_with_state` 544-692, `_qwen_l2norm` 695-698; quoted lines 605-609, 636, 650, 653, 655, 662, 668-669, 678, 685, 687.
- [C2] The same file at 127a662083, lines 559-562 (docstring of `gated_delta_net_with_state`) and 496-498 (docstring of `gated_delta_net`).
- [C3] `ingest/export/qwen3_5_export.py` at 127a662083, lines 22-72 and 128-162; `ingest/export/gdn_ops.py` lines 17-33.
- [C4] `h/tron/kernels/gated_delta_net.hpp:22-26` and `t/t_gated_delta_net.cpp:162` at 127a662083.
- [C5] `flake.nix:38-44`, `bin/pyproject.toml:10`, `ingest/export/pyproject.toml:12`, `ingest/runtime/pyproject.toml:20` at f454423b09, 72e1191804 and 127a662083; `ingest/export/uv.lock:1134-1151` and `ingest/runtime/uv.lock:1400-1417` at 127a662083.
- [C6] `t/t_gated_delta_net.cpp:247-256` at 127a662083.
- [C8] `t/t_gated_delta_net.cpp:594-621` and `1233-1280` at 127a662083.
- [C9] `git grep -n BENCHMARK <commit> -- t/t_gated_delta_net.cpp` at f454423b09, 72e1191804, 69cc70fae0 and 882e5322f1: two lines each (570/1200, 599/1229, 606/1313, 601/1231).
- [C10] `t/CMakeLists.txt` at 127a662083: line 266 (`add_catch_test(NAME t_gated_delta_net LIBRARIES tron pos_fake PROPERTIES LABELS fake)`), lines 181-186 (`Catch2::Catch2WithMain`), lines 206-216 (`catch_discover_tests`; `--benchmark-samples=2` for the simple test form only).
- [C11] `t/t_mask.cpp:300` at 127a662083.
- [C13] `t/CMakeLists.txt:351-375` at 127a662083; `git ls-tree -r --name-only <commit> -- t/ | grep -i qwen3_5` gives no file at 127a662083, 72e1191804, f454423b09 and 69cc70fae0.
- [C14] `t/CMakeLists.txt:392-398` and `config/test-benchmarks.json:172` at cb9a5dc070; `git diff 72e1191804 cb9a5dc070 -- t/CMakeLists.txt`.
- [C15] `t/t_generate_ingest_1_qwen3_5_4b_fpga.cpp` at cb9a5dc070: lines 1-4, 33, 36-37, 39-50, 52-66, 75-90, 116, 135-165, 167-252.
- [C16] At cb9a5dc070: `t/testutil.cpp:76-79`; `config/models.yaml:840-852`; `ingest/export/qwen3_5_4b_reference.py` lines 1-21, 37-46, 67-120, 188-198, 279-311.
- [C17] At 127a662083: `src/tron/generation/stats.cpp:66-77`; `h/tron/generation/stats.hpp:28-36`; `t/testutil.cpp:81-98`, `100-153`, `171-192`, `274-289`; `t/testutil.hpp:52,54,226,230`.
- [C18] At 127a662083: `t/force_generate.hpp:17-29`, `53-76`, `89-99`, `101-122`, `124-138`; `t/force_generate.cpp:360-378`.
- [C19] `ingest/export/reference_logits.py` at 127a662083: lines 1-8, 48-56, 126-179, 182-333. The file also exists at f454423b09 and 72e1191804.
- [C20] At 127a662083: `ingest/runtime/tron_ingest_tools/logit_test.py:38-65`, `191-228`, `368-457`, `485-559`; `ingest/runtime/scripts/logit_equivalence_test.py:1-15`; `ingest/runtime/scripts/bulk_logit_equivalence_test.py:1-37`.
- [C21] At 127a662083: `bin/compare_intermediates:1-22`; `bin/extract_logits:1-19` and `94-113`.
- [C22] `t/t_generate_ingest_1_gemma_3_4b.cpp:45-69` at 127a662083.
- [C23] `src/runtron.cpp` at 127a662083: lines 105-110, 113-115, 121-130, 764-768, 796-801, 1009-1010, 1014-1015, 1021-1024; `h/runtron/stream_generate.hpp:1292-1296`. At 882e5322f1: `src/runtron.cpp:1015`, `1022-1024`.
- [C24] `h/tron/models/model.hpp` at 127a662083: lines 1724-1747, 4079-4082, 4099-4106. At 882e5322f1: line 3999.
- [C25] `h/tron/models/model.hpp` at 127a662083: lines 4128-4133. At 882e5322f1: line 4028.
- [C26] `h/tron/kernels/amx_gdn_iface.hpp` at 882e5322f1: lines 17-25 (Note [AMX GatedDeltaNet block kernel]), 47-62, 103-104, 127-134 (read in `/home/jhan/workspace/ai-runs/tron-gdn-amx`).
- [C27] `src/tron/kernels/amx_gdn.cpp:150` and `h/tron/kernels/amx_gdn_iface.hpp:87-90` at 882e5322f1.
- [C28] `h/tron/models/gdn_rolling_executor.hpp:87-97` and `251` at 882e5322f1.
- [C29] `config/models.yaml:2-7` and `812-824` at 72e1191804; `git show --stat 72e1191804` (one file, 14 insertions).

Local files (read today, not run):

- [L1] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/build.sh`, lines 1-88.
- [L2] `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/run-one.sh`, lines 1-82 (the run command is at lines 70-71).
- [L3] `/home/jhan/workspace/intel-AMX/exec/dd/dd_logits_step.py`, lines 1-22 (docstring, with "runtron logs logits only for the last prompt token and each decode step"), 65-68, 99-134, 146-158.
- [L4] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/campaign.sh`, lines 10-48.
- [L5] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/token-check.sh`, lines 1-71.
- [L6] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/logit-margin.sh`, lines 1-67 (the kept lines are chosen at line 61; `MAX_GB` at 25; `TMO` at 38).
- [L7] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/logit_summary.py`, lines 1-52.
- [L8] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/unit-tests.sh`, lines 1-49 (`--skip-benchmarks` at line 24).
- [L9] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/e4b-check.sh`, lines 1-107.
- [L10] `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/build-pa.txt`, `build-pab.txt`, `build-ctr.txt`.
- [L11] `/home/jhan/workspace/intel-AMX/exec/dd/dd_first_divergence.py`, lines 1-163.
- [L12] `/home/jhan/workspace/intel-AMX/exec/dd/dd_intermediates.py`, lines 1-83.
- [L13] `/home/jhan/workspace/intel-AMX/exec/td-20261016/probe-td.sh`, lines 1-20, 38, 70-95, 108-121.
- [L14] `/home/jhan/workspace/intel-AMX/exec/td-20261016/analyze-td.sh`, lines 1-21.
- [L15] `/home/jhan/workspace/intel-AMX/exec/td-20261016/tiestats/tie_stats.py`, lines 1-23, 60-63, 147.
- [L16] `/home/jhan/workspace/intel-AMX/exec/td-20261016/ktest/README.md`, lines 1-30.
- [L17] `/home/jhan/workspace/intel-AMX/exec/td-20261016/replay/replay.py`, lines 1-25; `replay/extract.sh`, lines 1-14.
- [L18] `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/models.gdn.yaml`, lines 1-18.

Commands run today, with their output:

- [X1] `ls /home/jhan/workspace/intel-AMX/GDN/exec/` gives "No such file or directory". `find /home/jhan/workspace/intel-AMX -maxdepth 4 -type d -name "gdn-impl-20261121"` gives `exec/gdn-impl-20261121` and `exec/results/gdn-impl-20261121`.
- [X2] `git -C /home/jhan/workspace/tron rev-parse origin/main origin/rbjarnason/qwen35-native-4b-registry origin/rbjarnason/qwen35-37-gdn-head-parallel origin/rbjarnason/qwen35-gdn-fp32-intermediates` gives f454423b09, 72e1191804, 127a662083, 69cc70fae0. `git rev-parse <commit>:ingest/runtime/tron_ingest_runtime/ops.py` gives e4bf672f3d at all four.
- [X3] A loop of `git grep -l -i "qwen3_5_4b" <branch> -- t/ config/` over the 201 remote branches whose names hold "qwen35", "qwen3_5" or "gdn": the test source appears on the branch of PR #3215 and on later branches of that line, and not at 127a662083, 72e1191804 or f454423b09. `git merge-base --is-ancestor 72e1191804 cb9a5dc070` succeeds. `git merge-base --is-ancestor 127a662083 cb9a5dc070` fails. `git rev-parse <commit>:h/tron/kernels/gated_delta_net.hpp` gives 27789ff602 at both 72e1191804 and cb9a5dc070, and the executor and test files match in the same way. `git grep -l "673c337b\|qwen3_5_4b_reference" 72e1191804 127a662083 f454423b09` gives no file, so none of the three commits names the golden file or its generator.
- [X4] `git branch -r --contains 127a662083` gives five branches: the branch of PR #3221, three branches named qwen35-38a, 38ab and 38b, and the branch of PR #5571. `git grep -c "round_to<bf16>\|round_chunk_to<bf16>" <branch> -- h/tron/kernels/gated_delta_net.hpp h/tron/models/gdn_prepared_operation.hpp h/tron/models/gdn_rolling_executor.hpp` gives 14, 2 and 5 lines on the first four branches, and 4, 2 and 2 lines at 69cc70fae0. `gh pr list --search "5433 in:body" --state all` gives PR #5571 and PR #5462 only.
- [X5] `git grep -c -i "Qwen3\.5" <commit> -- config/models.yaml` gives no match at 127a662083, 69cc70fae0 and f454423b09. At 72e1191804 the entry is at lines 812-824.
- [X6] `/home/jhan/workspace/intel-AMX/exec/logs/gdn-impl-20261121-logit-margin.log` lines 3-8: "trial: 602826035 bytes for 66 tokens = 9133727 bytes per token", "trial: Top-k Logits lines = 2", "intermediates file bytes: 9441623564". `gdn-impl-20261121-logit-margin-l190.log` lines 1-6 and 387: "intermediates file bytes: 11706285068", start 02:01:01Z, end 02:10:43Z, "free 3145 GB". The per-step and per-token sizes are computed from these numbers.
- [X7] `git grep -n -w 1991 127a662083` gives one text hit, a file name in `datasets/wikitext/.../manifest.txt`. `bin/ci/benchmark_lib.py` at 127a662083 sets prompt lengths 2047 and 199 (lines 167 and 203).
- [X8] `ls -la /scratch/test/data/673c337b...c99f` on claude-agentsrv gives 14,009 bytes, Oct 30. A Python read of the JSON gives the header fields and the per-case lengths quoted in section 5. `ls -d /opt/positron/weights/huggingface/Qwen/Qwen3.5-4B` gives "No such file or directory".
- [X9] `git grep -l -i -E "tvd|total variation" <commit> -- ingest/ bin/ t/ scripts/ tools/ src/ h/ doc/` at 127a662083 and f454423b09: the same list (the stats files, `logit_test.py`, `testutil`, and the generation tests of other models).
- [X10] `ls -la` and `wc -lc` on `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/tokens/`; a Python read of the `logits-*` and `p1024__*` files gave: 380 records of 320 values in each l190 file; base against a: same best token at 185 of 190 steps, first other best token at step 185, 60 of 320 values differ at step 0; first token difference from base at generated token 185 (a, a2, ab, ab2), 1 (b, b2, bonly), none (orig, p0, a0, base2). A direct comparison of the repeat pairs gave equal files of 256 tokens: base and base2, a and a2, b and b2, ab and ab2.
- [X11] `du -sh /home/jhan/workspace/intel-AMX/exec/results/gdn-*` gives 51M, 719K, 14M. `du -sh .../td-20261016` gives 201M. `ls` gives the names in section 3.3.
- [X12] `git log f454423b09 --grep="(#5462)" -1` gives 2559c133df. `git merge-base --is-ancestor 2559c133df 72e1191804` fails and the same test for 127a662083 succeeds. `git merge-base --is-ancestor` fails in both directions between 72e1191804 and 127a662083. `git diff --stat 72e1191804 127a662083 -- h/tron/kernels/gated_delta_net.hpp h/tron/models/gdn_rolling_executor.hpp h/tron/models/gdn_prepared_operation.hpp t/t_gated_delta_net.cpp` gives 982 insertions and 408 deletions.
