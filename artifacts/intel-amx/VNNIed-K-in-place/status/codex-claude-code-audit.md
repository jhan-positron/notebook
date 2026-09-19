Short version: the reviewed source and saved test logs support the intended key ordering, masked score calculation, and existing page-copy behavior for the tested shapes. The storage gate accepts more query-head groups than the reader can compile. Continuous integration does not build the new storage mode, and nonzero float16 scoring and the new hardware-staging adapter still lack direct correctness evidence.

Reviewed commit: `5e45ae55ae3277f025bd69a29e93741e2690e3e3`, compared with base `544ca05c7a`. This was a source and saved-log review. No production file was edited, no C++ binary was rebuilt, and no workload was launched on a test machine.

Words used here:

- K and V are cached attention keys and values. A query head reads one key head's cached tokens.
- A group size, named `kv_mul` in the code, is the number of query heads sharing one key head.
- VNNI means Vector Neural Network Instructions. Here it names the paired-value storage order used by the vector and tile dot products.
- AMX means Advanced Matrix Extensions, Intel's tile instructions. AVX-512 means its 512-bit vector instructions.
- bf16 and fp16 are different 16-bit floating-point formats. Float32 is the 32-bit format used for scores.
- CI means continuous integration. GOF is the four-token staging buffer used before transfer to the accelerator.
- A live mask marks the tokens whose scores must be computed.

**1. Confirmed compatibility limitation: valid groups above 16 query heads cannot compile with VNNI storage.**

The storage gate selects every 128-dimension head. The reader rejects groups larger than 16 query heads at compile time. The software-attention caller passes the complete geometry's group size without splitting it. [Source: `h/tron/kernels/k_vnni.hpp:54`, `h/tron/kernels/k_vnni.hpp:135`, `h/tron/models/self_attention.hpp:1618`.]

For example, 32 query heads, one key head, and 128 dimensions satisfy `attention_geometry::valid()`. They select VNNI storage and require `qk_group<32>`, which violates that assertion. The old reader constructed one dotter per head without this limit. [Source: `h/tron/models/kv_cache.hpp:165`; base commit `h/tron/models/self_attention.hpp:1557`.]

This is a proved compilation restriction. **Insufficient data:** no currently measured model was shown to be affected. The missing evidence is a generated-model geometry inventory or a build containing such a model. The design's statement that the reader handles “any kv_mul” is nevertheless false. [Frozen design text: `status/codex-review-evidence/claude-VNNIed-K.txt:331`.]

Suggested resolution: process a larger query group in bounded head batches while keeping the storage format independent of query grouping. Add a compile case above 16 query heads and nonzero score comparisons for representative supported groups. Group sizes 1, 3, 8, and 16 have no direct numerical execution evidence in the four campaign test logs reviewed here.

**2. Confirmed CI gap: the new persistent-storage behavior is compiled out of the current CI build.**

The CI configuration enables AMX dispatch but omits `TRON_K_VNNI`. That option defaults to OFF. The new test is registered, so its unconditional layout primitives can run in CI. Its page access, copy, producer, and software-attention integration paths select row-major storage there. [Source: `.github/workflows/cmake-single-platform.yml:340`, `CMakeLists.txt:49`, `t/CMakeLists.txt:603`, `h/tron/kernels/k_vnni.hpp:52`.]

No `t_k_vnni_layout` entry exists in `config/test-benchmarks.json`. CI runs `bin/slice bench --check`. The test guide requires refreshed cost data after adding or materially changing a test. [Source: `.github/workflows/cmake-single-platform.yml:345`, `t/AGENTS.md`; exact-name search of the cost file returned no match.]

Claude's design and report already disclose both omissions. They remain completion gaps, not newly discovered runtime failures. [Frozen design text: `status/codex-review-evidence/claude-VNNIed-K.txt:333`; frozen report text: `status/codex-review-evidence/Monday-morning-report.txt:747`.]

**3. Confirmed numerical coverage gap: float16 queries run, but their nonzero scores are not checked.**

The reader correctly widens float16 queries to float32 in the reviewed source. The float32 branch widens each bf16 key value without rounding the query to bf16. I found no source-level query-precision bug in these branches. [Source: `h/tron/kernels/k_vnni.hpp:136`, `h/tron/kernels/k_vnni.hpp:168`.]

The direct numerical reader test uses bf16 and float32 queries with a group size of four heads. It does not create a float16 query array. [Source: `t/t_k_vnni_layout.cpp:140`.]

The dispatch test instantiates and executes the float16 path. It fills every key and value with zero and asserts call counts. It does not assert nonzero attention results. A mistaken float16-to-bf16 query conversion would still pass this test. [Source: `t/t_amx_dispatch_dtype.cpp:98`, `t/t_amx_dispatch_dtype.cpp:125`, `t/t_amx_dispatch_dtype.cpp:155`; execution: `tests-t_amx_dispatch_dtype.out:46`.]

Suggested test: use nonzero keys and float16 query values that bf16 cannot represent, then compare against an independent float32 reference. For example, the exactly representable float16 value 1.0009765625 becomes 1.0 after bf16 rounding. Use prefix and hole masks in that case. This is a coverage gap, not evidence that the current float16 implementation is wrong.

**4. Confirmed staging coverage gap: the modified callbacks in the tests bypass the new K gather adapter.**

The scheduler's new K callback gathers one packed token into caller-owned scratch. The staging function allocates separate scratch per key head and a separate V scratch array. The reviewed ownership and head offsets are consistent. [Source: `h/tron/scheduler/full.hpp:2506`, `src/tron/gof.cpp:203`.]

The changed test callbacks accept the new scratch argument but return an existing contiguous key row. The concurrent staging test writes V scratch only. These cases therefore cannot expose an error in K gathering, K scratch reuse, or the scheduler's selected key geometry. [Source: `t/t_phase1_integration.cpp:857`, `t/t_phase1_integration.cpp:890`, `t/t_gof_dma.cpp:347`, `t/t_gof_staging_leaks.cpp:137`.]

The campaign test list contains four other executables. None of these staging tests appears in `tests.txt`. The performance campaign explicitly disables hardware attention. [Source: `exec/vnnik-20260914/campaign.sh:62`, `exec/results/vnnik-20260914/tests.txt`, `exec/vnnik-20260914/campaign.sh:248`. Paths are relative to `/home/jhan/workspace/intel-AMX`.]

**Insufficient data:** exact staged-byte comparison using the production packed-key callback, across multiple heads and token offsets, would resolve correctness coverage. A fake-device test could supply this evidence without an accelerator workload. Hardware-staging latency requires a separate measurement.

**5. Numerical and mask claims should stay within the measured contract.**

- The new AMX identity test ran on the recorded Intel host. It compares two random seeds with 256 scores per seed. The raw log records its execution and contains no AMX-unavailable warning. This is 512 bitwise score comparisons for full pages. [Source: `t/t_amx_numerics.cpp:188`; execution: `tests-t_amx_numerics.out:27`.]
- The direct AVX reader test covers all 65 prefix lengths, 24 generated hole masks, and two explicit single-token masks. Its score tolerance is `1e-4 * sum(abs(query * key)) + 1e-6` score units. Inputs are rounded samples from the interval [-1, 1]. This is useful arithmetic and mask coverage for that corpus. It does not measure model-level output quality. [Source: `t/t_k_vnni_layout.cpp:136`.]
- The dead-token poison test proves that live outputs stay within tolerance and dead output slots retain their preset value. It does not independently prove that dead key addresses are never read. An unmasked load followed by the existing masked store would leave these assertions satisfied because token lanes do not mix. The reviewed code does use masked loads. [Source: `t/t_k_vnni_layout.cpp:167`, `h/tron/kernels/k_vnni.hpp:156`, `h/tron/kernels/k_vnni.hpp:181`.]
- The smoke's repeat runs reproduce each binary's token sequence. Divergence between binaries in both AMX states is consistent with the changed vector reader. It does not isolate the partial-page reader from all other producer, layout, and software-path changes. The report acknowledges the missing per-step logit evidence but earlier states the cause as settled. Keep that attribution a hypothesis until identical-prefix logits, score differences, and the selection margin at the first differing token are captured. [Frozen report text: `status/codex-review-evidence/Monday-morning-report.txt:640`.]

**6. Coverage already present should be retained in the review.**

The saved logs contain the following successful executions at the reviewed tip:

| Test executable | Assertions | Test cases | Relevant observed scope |
|---|---:|---:|---|
| `t_k_vnni_layout` | 63,208 | 4 | Scatter/gather bits, index anchors, masked bf16/float32 scores, single-head append |
| `t_amx_numerics` | 4,621 | 5 | New full-page AMX identity case plus existing numerical checks |
| `t_amx_dispatch_dtype` | 1,559 | 1 | Query-type dispatch and full/partial-page routing |
| `t_llama_unit` | 120,079 | 29 | Existing attention, geometry, completion, append, and allocation checks |

These are assertion counts, not distinct inputs or performance samples. [Record: `/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/tests.txt`.]

The nonzero “apply and join page ranges” case ran. It uses float32 queries with two query heads per key head and compares against an attention reference. This gives integration coverage beyond the direct four-head tests. [Source: `t/t_llama_unit.cpp:1497`, `t/t_llama_unit.cpp:1528`, `t/t_llama_unit.cpp:1692`; execution: `tests-t_llama_unit.out:285`.]

The heterogeneous append case also ran. It crosses page boundaries and checks completion state. Its 128-dimension key comparison checks dimension zero only. The new uniform append case checks every dimension, including a complete-page copy and an append from five to 25 tokens. No incorrect copy was established by this review. [Source: `t/t_llama_unit.cpp:1212`, `t/t_llama_unit.cpp:1250`, `t/t_k_vnni_layout.cpp:246`; execution: `tests-t_llama_unit.out:250`, `tests-t_k_vnni_layout.out:35`.]

The producer preserves the original non-bf16 conversion path before scattering. Completion is published after the stores. The software caller constructs its live mask under the previous visibility and sliding-window conditions. These reviewed changes preserve the relevant source-level contracts. [Source: `h/tron/models/model.hpp:2757`, `h/tron/models/model.hpp:2780`, `h/tron/models/self_attention.hpp:1588`.]

**7. Minor documentation and C++ guide defects.**

- The anchor test comment says a panel contains 1,024 elements. Its dimensions multiply to 512 bf16 elements, or 1,024 bytes. The assertions use the correct 512-element offset. This is a comment error. [Source: `t/t_k_vnni_layout.cpp:57`, `t/t_k_vnni_layout.cpp:66`.]
- Newly added multi-line loop bodies omit braces. Examples include float16 widening and accumulator initialization. The required C++ guide permits omission only when the complete statement occupies one physical line. [Source: `h/tron/kernels/k_vnni.hpp:138`, `h/tron/kernels/k_vnni.hpp:149`; skill: `/home/jhan/.codex/skills/cpp-coding-guide/SKILL.md`.]
- New fixed constants `S16_ROW_BYTES` and `PANEL_ELEMS` lack the guide's value suffixes. Several new layout calculations also use fixed literals directly. These are guide-conformance issues, not observed functional failures. [Source: `src/tron/kernels/amx_attn.cpp:206`, `src/tron/kernels/amx_attn.cpp:210`, `h/tron/kernels/k_vnni.hpp:63`.]

The independent `status/codex-layout-check.py` validates Codex's proposed token-panel ordering. Claude uses a different ordering of its dimension-step and token-block panels. That Python result must not be cited as execution evidence for Claude's compiled kernels.
