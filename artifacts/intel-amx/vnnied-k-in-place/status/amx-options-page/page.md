**Short version.** Two build options and one environment variable control the AMX attention code of tron: `TRON_AMX_DISPATCH` (PR 3879) compiles the AMX kernels, `TRON_K_VNNI` (PR 4424) stores the K cache of 128-dimension heads in the AMX operand layout, and `TRON_AMX_DISABLE=1` switches the kernels off at run time. The kernels run only for a (query, page) pair that software attention scores, in a process with AMX, for a model with 128-value heads, 4 query heads per KV head and bf16 activations, and only when the page is a full 64-token page that the query sees whole, in one visible range and inside its sliding window. No nix build and no CMake preset sets either option, and today only the legacy CMake CI lane compiles this code.

## Words used here

| Term | Meaning |
|---|---|
| tron, runtron | The inference program under test and its command-line tool. |
| PR | A GitHub pull request, one reviewed change. PR 3879 (merged 2026-09-15) and PR 4424 (open as a draft) are the two changes this page describes. The PR head is the PR's latest commit. |
| CMake, nix | The two build systems of tron. CMake is the build configuration tool of the repository. Nix is the package manager that builds tron for the default CI. |
| CI, lane | Continuous integration, the automatic build-and-test runs that GitHub starts for each change. A lane is one CI workflow. The legacy CMake CI lane is `.github/workflows/cmake-single-platform.yml`. It is kept for manual runs and for the Debian package gate. The GCP (Google Cloud Platform) Nix workflow has been the default CI since September 2026. |
| AMX, AVX-512 | Intel Advanced Matrix Extensions, the tile-multiply instruction set of Sapphire Rapids and later Xeons. AVX-512 is the 512-bit vector instruction set that every other path uses. |
| FPGA | Field-programmable gate array, the accelerator cards of the tron hosts. |
| software attention, hardware attention | Attention computed on the CPU (software) or on the FPGA cards (hardware). The AMX code lives inside software attention. |
| ingested model, generated plugin, hand-written plugin | An ingested model has a plugin (the model-specific C++ code) that the code generator produced from the model files (qwen, llama, gpt-oss). Generated plugins declare `force_hw_attn = true`, so hardware attention is their default. The hand-written plugins (`h/tron/plugins/llama.hpp` and the test-only `h/tron/plugins/mock.hpp`) default to software attention. |
| executor | The tron code variant that runs a model's layers. The `tp*`, `perm_tp*` and `host_bf16` executors keep activations in bf16. `host` keeps 32-bit float, `host_fp16` keeps fp16. |
| KV page, dense page, sliding window | 64 tokens of keys (K) and values (V). A dense page has all 64 tokens in use, is visible to the query in one range, and lies inside the query's sliding window (the span of recent tokens that a model with a limited attention range lets a query see). |
| head size 128, kv_mul 4, "128 x 4" | Each attention head has 128 values, and 4 query heads share one KV head (grouped-query attention). The AMX kernels serve only this shape (namespace `amx_attn_h128g4`). |
| bf16, fp16, fp32 | 16-bit brain floating point (the storage format of K, V and of the activations the kernels read), 16-bit IEEE half-precision float, and 32-bit float (the accumulator format). |
| Q, QK, PV, softmax | Q is the query vector of a step. QK is the query-times-key product, one score per token. Softmax turns the scores into weights that sum to 1. PV multiplies those weights by V. A packed Q is Q copied into the AMX tile layout. |
| row-major K, VNNI layout, VNNI plane | Row-major: one row of 128 values per token, the layout of `main` (the main git branch of tron). VNNI (Vector Neural Network Instructions): the pair-interleaved layout of the right-hand operand of the AMX tile multiply. One 64-byte row holds one dimension pair for 16 tokens. The VNNI plane is the K storage of one page in that layout, which the AMX kernel reads directly. |
| dotter, VNNI reader | The dotter is the existing AVX-512 per-token dot product over row-major K. The VNNI reader (`k_vnni::qk_group`) is PR 4424's AVX-512 routine that scores tokens from the VNNI layout. |
| kill switch | The environment variable `TRON_AMX_DISABLE=1`. |
| engagement point | The first token position that hardware attention handles. Software attention handles every query below it. The default is position 127. |
| Note [name] | A named comment block in a tron header, for example Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp`. |
| token divergence | The first generated token at which two binaries, run on the same prompt with greedy decoding, produce different tokens. |

## AMX and VNNI options

### Build time

**CMake based**

- `TRON_AMX_DISPATCH` (PR 3879, default OFF). ON compiles the AMX kernels and the dispatch code in software attention. Only one file, `src/tron/kernels/amx_attn.cpp`, gets the AMX compiler flags. A default build contains no AMX code.
- `TRON_K_VNNI` (PR 4424, default OFF). ON stores the K cache of 128-dimension heads in the VNNI layout at the moment it is written. The AMX kernel then reads K without a transpose. It requires `TRON_AMX_DISPATCH=ON`. Configure stops otherwise. Both options require the AVX-512 build (`TRON_CHUNK_SIZE == 16`).
- Where they are ON: only in the legacy CMake CI lane, which passes both. No preset in `CMakePresets.json` sets them. So a plain `make` build, the Debian package (`deb` preset) and the weekly `coverage` build are row-major and contain no AMX code.

**nix based**

- None. The nix build of tron (`nix/cmake-tron-test-build.nix`) passes neither option, and no nix file mentions AMX. The default CI (GCP Nix) therefore never compiles the AMX or the VNNI code.

### Run time

**Environment variables**

- `TRON_AMX_DISABLE=1` (PR 3879), the kill switch. Exactly the string `1` counts. It is read once, at the first attention dispatch, and holds for the whole process. With it, the AMX kernels never run and software attention uses its AVX-512 path on every page. On a `TRON_K_VNNI` binary the K layout stays VNNI and the VNNI reader runs. The output is therefore not that of a row-major build (tracked in tron issue #4444).
- `USE_HW_ATTN` is older than both PRs. It decides which (query, page) pairs software attention scores, and only those pairs can reach the AMX code. Unset: hardware attention for ingested models when the process sees FPGA cards, software attention for the other models and for every model without cards. `0`, or any value that is not a positive number: software attention for every model. A number N greater than 0: hardware attention for every eligible model from the engagement point on, which is N rounded up to the end of a 128-position hardware page (position k x 128 - 1) and never below 127.
- PR 4424 adds no environment variable. Its two measurement switches (`TRON_K_VNNI_BLOCK`, `TRON_K_VNNI_STRIPE`) were added in one development commit (0b54de7a10) and removed two commits later (ab94854999). Neither name appears in the PR head.

**Execution logic**

- First attention dispatch: `available()` is true when the kill switch is not set, CPUID (the x86 instruction that reports CPU features) reports the AMX-BF16 and AMX-TILE feature bits, the OS has enabled the tile state (bits 17 and 18 of XCR0, the register that lists the enabled CPU state components), and Linux grants tile data to the process (`arch_prctl(ARCH_REQ_XCOMP_PERM)`). The probe runs once, at the first call, and its result holds for the whole process. AMD hosts fail the CPUID test and run the AVX-512 path.
- Model shape is 128 x 4: `eligible` is true when the head size is 128, `kv_mul` is 4 and the executor keeps activations in bf16. This is decided at compile time per model geometry. qwen3-4b and llama-3.1-8b qualify. qwen-3-30b-a3b (kv_mul 8) and gpt-oss-120b (head size 64) do not.
- Which pairs software attention scores: every pair when hardware attention is off (see `USE_HW_ATTN`). Under hardware attention, software attention still scores every query below the engagement point, the causal tail of a request past the K and V that already sit in FPGA memory, and every query of a layer with a sliding window. The AMX gate does not test whether hardware attention is on. So a dense page in one of those software-scored pairs takes the AMX path even in a hardware-attention run. This follows from the code. No counter measurement of it exists yet.
- Per software-scored (query, page) pair: if the page is dense, the AMX QK kernel scores all 64 tokens in one call, and the AMX PV kernel multiplies the softmax weights by V. Otherwise that pair runs the AVX-512 path. A query with a partial tail page therefore uses both paths in one step.
- K layout (PR 4424): `k_vnni::layout_on<head_size>` is true when `TRON_K_VNNI` is defined and the head size is 128. It is a property of the storage, decided at compile time per model, not a run-time choice. The K store (`save_k`), the AMX kernel (`qk_vnni_128x4`), the AVX-512 reader (`k_vnni::qk_group`) and the FPGA staging (`page::get_k_row`, which rebuilds one row per token for the FPGA) all follow it. A 128 x 8 model gets the layout but not the kernel. In software attention it scores every page with the VNNI reader.

## Details

### 1. The decision chain

```
build          environment      process       model      page       what scores it
-------------  ---------------  ------------  ---------  ---------  ------------------
TRON_AMX_      TRON_AMX_        available():  eligible:  dense?     AMX QK + PV
DISPATCH=ON    DISABLE not 1    CPUID, XCR0,  128 x 4,   64 tokens  (row-major K or
TRON_K_VNNI    pair scored in   arch_prctl    bf16       visible,   VNNI plane)
=ON/OFF        software attn                             in window  else AVX-512 path
```

Every stage must pass for the AMX kernels to run. A failed stage sends the pair to the AVX-512 path: the dotter on a row-major build, the VNNI reader on a `TRON_K_VNNI` build with 128-dimension heads. Hardware attention (`USE_HW_ATTN` unset on an ingested model with FPGA cards) moves only the queries at or above the engagement point to the FPGA. The queries below it, the causal tail, and every query of a sliding-window layer still run the software path, so their pairs go through the chain.

### 2. What runs in each combination

Rows 1 to 9 describe software-scored pairs: every pair with `USE_HW_ATTN=0`, on a hand-written plugin, or on a host without FPGA cards, and the software-scored pairs of a hardware-attention run. Row 10 is the hardware-scored part of a hardware-attention run.

| Build | Environment and host | Model | Page | What scores the page | K layout |
|---|---|---|---|---|---|
| 1. default (both OFF) | software-scored pair | any | any | AVX-512 dotter | row-major |
| 2. `TRON_AMX_DISPATCH=ON` | AMX available, software-scored pair | 128 x 4, bf16 | dense | AMX QK and PV kernels | row-major |
| 3. `TRON_AMX_DISPATCH=ON` | same | 128 x 4, bf16 | partial | AVX-512 dotter | row-major |
| 4. `TRON_AMX_DISPATCH=ON` | `TRON_AMX_DISABLE=1`, or a host without AMX | any | any | AVX-512 dotter (same numbers as the default build) | row-major |
| 5. both ON | AMX available, software-scored pair | 128 x 4, bf16 | dense | AMX QK from the VNNI plane (bit-identical to row 2) and PV | VNNI |
| 6. both ON | same | 128 x 4, bf16 | partial | AVX-512 VNNI reader | VNNI |
| 7. both ON | `TRON_AMX_DISABLE=1`, or a host without AMX | 128-dimension heads | any | AVX-512 VNNI reader (not the numbers of the default build) | VNNI |
| 8. both ON | software-scored pair | 128 x 8 (qwen-3-30b-a3b) | any | AVX-512 VNNI reader | VNNI |
| 9. both ON | software-scored pair | head size 64 (gpt-oss-120b) | any | AVX-512 dotter | row-major |
| 10. any | FPGA cards present, and `USE_HW_ATTN` unset on an ingested model or `USE_HW_ATTN=N` with N greater than 0 | a model the FPGA bitfile can serve | the K and V already copied to FPGA memory, for queries at or above the engagement point | FPGA hardware attention (the K bytes handed to the FPGA are unchanged) | as built |

### 3. Build time, with sources

- The two options are declared in the top-level `CMakeLists.txt` with default OFF [CMakeLists.txt:48-49]. `TRON_AMX_DISPATCH` adds `kernels/amx_attn.cpp` to the tron library. It gives that one file the flags `-mamx-tile -mamx-bf16` plus `-mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 -mavx2 -mfma`. It defines `TRON_AMX_DISPATCH` for every target that links the library [src/tron/CMakeLists.txt:193-198].
- `TRON_K_VNNI` stops configure with "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON" when the first option is off. It defines `TRON_K_VNNI` the same public way. Every translation unit (one compiled source file) that touches a KV page must agree on the layout [src/tron/CMakeLists.txt:209-214].
- Both options need `TRON_CHUNK_SIZE == 16`. Each option has its own `#error` guard that stops compilation otherwise: `TRON_AMX_DISPATCH` in `self_attention.hpp`, `TRON_K_VNNI` in `kv_cache.hpp` [h/tron/models/self_attention.hpp:30-35; h/tron/models/kv_cache.hpp:35-39].
- The legacy CMake CI lane configures with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON` [.github/workflows/cmake-single-platform.yml:331-334]. That workflow runs only by manual dispatch and from `publish-deb.yml` [.github/workflows/cmake-single-platform.yml:3-16].
- No preset sets either option (`grep AMX CMakePresets.json` is empty), and the nix build passes a fixed flag list without them [nix/cmake-tron-test-build.nix:79-103]. The Debian package uses the `deb` preset. Shipped packages therefore contain no AMX code (tron issue #4347 records this gap).

### 4. Run time, with sources

- The kill switch and the probe. `detect_and_request()` returns false in four cases [src/tron/kernels/amx_attn.cpp:60-74]:
  - `TRON_AMX_DISABLE` is exactly `1`.
  - CPUID leaf 7.0 EDX (the feature-flag word that CPUID returns for sub-function 7) has bit 22 (AMX-BF16) or bit 24 (AMX-TILE) clear.
  - XCR0 bits 17 and 18 are not both set.
  - `arch_prctl(ARCH_REQ_XCOMP_PERM, XTILEDATA)` fails.
- `available()` runs the probe once and caches the result for the process. Its only production caller is the attention dispatch [src/tron/kernels/amx_attn.cpp:78-88; h/tron/models/self_attention.hpp:1239].
- The shape gate. `shape_ok` is head size 128 and kv_mul 4. `query_scalar_ok` is "the executor's activation scalar is bf16". `eligible` is both [h/tron/kernels/amx_attn_iface.hpp:148-165].
- The dispatch. Inside `#ifdef TRON_AMX_DISPATCH`, `apply_dense_amx_page` runs the pair and returns when three checks pass: the model is eligible, a packed Q exists, and `is_dense_amx_page` holds. Every other pair falls to the AVX-512 loop below [h/tron/models/self_attention.hpp:1537-1560]. The dense predicate is: begin 0 and end 64 (all 64 tokens of the page are in use), visible, last token below the visible range's end, first token inside the sliding window [h/tron/models/self_attention.hpp:1383-1394].
- Hardware attention and the gate. Under hardware attention a pair counts as visible for the software path when the scheduler marked it software-required [h/tron/models/self_attention.hpp:1220-1221, 1535-1536]. The AMX gate uses that flag and has no hardware-attention term [h/tron/models/self_attention.hpp:1236-1239, 1546-1551]. The scheduler marks every query below the engagement point and the causal tail past the hardware K and V boundary as software-required [h/tron/scheduler/full.hpp:1936-1965]. The engagement point defaults to position 127 [h/libpos.hpp:90].
- The layout gate. `k_vnni::layout_on<head_size>` is `head_size == 128` under `TRON_K_VNNI` and false otherwise [h/tron/kernels/k_vnni.hpp:91-97]. Note [K VNNI storage] lists the six consumers that follow it: the store, the dense AMX path, the software path, the FPGA staging, page copies, and the per-token row view, which no longer exists for K in the VNNI layout [h/tron/models/kv_cache.hpp:653-710]. The Q pack and the QK kernel are chosen by the same gate [h/tron/models/self_attention.hpp:1348-1370; 1426-1445].
- `USE_HW_ATTN` is read once. Unset means hardware attention for ingested models with FPGA cards present and software attention otherwise. A value that is not a positive number disables hardware attention for all models. N greater than 0 enables it for every eligible model from the engagement point, which is N rounded up to the end of a 128-position hardware page (k x 128 - 1) and never below 127 [h/tron/models/hw_attn_config.hpp:9-23; src/tron/models/hw_attn_config.cpp:19-33; h/tron/models/model.hpp:711-732, 1443-1447].

### 5. Numerics and the kill switch

- Note [AMX attention dispatch] states that the AVX-512 and AMX paths multiply bf16 inputs and add the products in fp32. It states that, for inputs that are finite and not subnormal, their outputs differ for exactly two reasons. The first is the bf16 rounding of the softmax weights (AVX truncates, AMX rounds to nearest even). The second is the order of the fp32 adds [h/tron/kernels/amx_attn_iface.hpp:74-85]. `t_amx_numerics` (the AMX kernel numerics test) checks that the kernels stay within those two allowed differences.
- PR 4424: the AMX kernel reading the VNNI plane is bit-identical to the AMX kernel reading row-major K (a test case in `t_amx_numerics`). The VNNI reader differs from the dotter only in add order. The test case in `t_k_vnni_layout` checks it to a tolerance of 1e-4 (0.01%) times the sum of the absolute values of the 128 products, plus an absolute floor of 1e-6.
- Consequence for the kill switch. PR 3879 promised that `TRON_AMX_DISABLE=1` gives "same layout, same AVX dotter, clean-binary numerics" [h/tron/kernels/amx_attn_iface.hpp:47-51]. On a `TRON_K_VNNI` binary the second and third parts no longer hold for 128-dimension heads. The layout is a build-time property of the head size, and the VNNI reader replaces the dotter for those heads [h/tron/kernels/k_vnni.hpp:91-97; h/tron/models/kv_cache.hpp:706-710]. Heads of other sizes keep the row-major plane and the dotter. Rolling back to row-major K means a rebuild with the option off. Tron issue #4444 tracks that decision and one measurement: a forced run of both binaries on the same prompt, comparing the top candidate scores at the first divergent step. It would confirm whether the add-order difference explains the token divergence seen against the row-major binary. Today that cause is inferred from the numerics contract, not measured.

### 6. CI coverage and open issues

- Only the legacy CMake lane compiles and tests the AMX and VNNI code (both options ON). Its kernel tests execute AMX only when the job runs on a Granite Rapids runner (a CI machine with an Intel Xeon 6 CPU, which has AMX). Elsewhere they skip with a warning. Tron issue #3997: no required CI check proves a real AMX execution.
- Tron issue #4347: the nightly system tests install the Debian package and run hardware attention (`USE_HW_ATTN` unset). The package's preset leaves AMX off. Enabling and verifying AMX there is open.
- Tron issue #4444: token divergence against the row-major binary and the kill-switch contract (section 5).

### 7. Sources

- PR 3879, "AMX software attention, canonical path: kernel + dispatch, default-off", merged into `main` on 2026-09-15: https://github.com/positron-ai/tron/pull/3879
- PR 4424, "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save", open as a draft, base `main`: https://github.com/positron-ai/tron/pull/4424
- Notebook page with the former `doc/amx_software_attention.md` and the PR 4424 addendum: https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/amx_software_attention.md
- File and line references above are at commit `ff680c8020` of tron (the PR 4424 head, which contains the merged PR 3879), for example https://github.com/positron-ai/tron/blob/ff680c8020/h/tron/kernels/amx_attn_iface.hpp
- Fact-check: every sentence of this page was checked against that tree and the two PR descriptions on 2026-09-16 by a read-only review (6 checkers, 2 refuters per finding). 20 factual corrections were applied before publication.
