## Short version

The AMX software-attention kernels accept Muse Glimmer 30B's shape, 16 query heads per KV head, through one template parameter, and the kv_mul-4 kernels emit the same instructions as on main. Glimmer's 39 sliding-window layers then run on AMX instead of the AVX loop. On delphi-3bda with 8 users, Glimmer's decode rate per user rises by 4.4 to 15.2 % and its prefill time shortens by 0.6 to 8.7 % with the production attention mode (FPGA on the 13 full layers, CPU on the 39 sliding-window layers).

## Background

Muse Glimmer 30B has 32 query heads over 2 KV heads at head size 128. Its kv_mul is therefore 16.

On main the AMX kernels serve head size 128 with kv_mul 4 only, and the gate `shape_ok` refuses every other shape. 39 of Glimmer's 52 layers are sliding-window layers (attention over the most recent tokens only), which tron (the inference program under test) always scores on the CPU. The other 13 layers go to the FPGA by default. So on main, Glimmer's CPU attention runs on the AVX loop.

One AMX tile holds 16 rows, and the 4-head kernels use 4 of them. With 16 heads the QK (query times key, the score step) result tile and the PV (probability times value, the weighting step) weight tile are full. No padding is needed.

Note [AMX attention dispatch] in `amx_attn_iface.hpp` describes the gate and the kernel contract. Note [QK orientation] describes why the QK result is transposed when it is stored. Note [Tile stores write 16 rows] describes the 16-row stores the PV kernel makes.

## Words used here

| Term | Meaning |
|---|---|
| runtron | tron's command-line tool. It runs one model with N users and prints per-user rates |
| AMX, AVX | two Intel CPU instruction sets. AMX multiplies 16-row tiles, and AVX is the vector loop the non-AMX attention path uses |
| kv_mul | query heads per KV head (grouped-query attention). 4 for llama-3.1-8b, 16 for Muse Glimmer 30B |
| Muse Glimmer 30B | the production ingested model `ingested-meta-models--Muse-Glimmer-30B` (tp2 and tp4 variants). 52 layers, 2 KV heads, head size 128 |
| tp2, tp4 | the model split over 2 or 4 FPGA cards (tensor parallel degree) |
| kill switch | `TRON_AMX_DISABLE=1`. The same binary then scores every page with the AVX loop |
| FPGA attention | the default attention mode of Glimmer (the layer split is in [Background]) |
| CPU attention | `USE_HW_ATTN=0`: all 52 layers scored on the CPU |
| attention path stats | `TRON_ATTN_STATS=1`. tron prints, at exit, how many K tokens each path (AMX, AVX, FPGA) scored per layer |
| delphi-3bda | the Intel Xeon 6 test machine with 8 FPGA cards. "Our half" is socket 1 with cards 90, 93, b9, bc |

## How to review this PR

**Does the 16-head transposing store put every QK score in the right row and column?**

- `src/tron/kernels/amx_attn.cpp`, `store_transposed_rows<lane>` and its four call sites in `qk_rowmajor_128x4`: stages 1 and 2 unpack. After them, 128-bit lane `l` of `u[row_group][k]` holds result column `4*l + k`. In stage 3, row `4*l + k` of `s` uses the `vshufps` selector `0x88` when bit 0 of `l` is 0 and `0xdd` when it is 1. Stage 4 does the same with bit 1 of `l`.
- Lane 0 is the sequence the 4-head kernel runs on main, at the same addresses. Lanes 1 to 3 exist only in the 16-head instantiation (`if constexpr`).
- Verification: `t_amx_numerics` case "AMX QK does not digress from the AVX dotter" (the dotter is the AVX dot-product routine the non-AMX path uses), sections "16 heads: all 16 rows match the dotter" and "4 heads: rows 0..3 match the dotter, rows 4..15 untouched" (a sentinel value checks that rows 4..15 stay untouched). The object compare in [Verification] shows the 4-head QK kernel instruction-identical to main.

**Do the gate, the call sites and the instantiations agree on the set of group sizes?**

- `h/tron/kernels/amx_attn_iface.hpp`: `group_heads_ok` lists 4 and 16, `shape_ok` uses it, and every kernel declaration carries `requires(group_heads_ok(group_heads))` (`group_heads` is the kernels' template parameter, equal to the model's kv_mul).
- `src/tron/kernels/amx_attn.cpp`, the explicit instantiations at the end of the file: the same two sizes. A caller with any other size fails to link. A model with any other kv_mul is refused by the gate.
- `h/tron/models/self_attention.hpp`: the pack call passes `geometry.kv_mul()`, the QK and PV calls pass `operation_kv_mul`. Both are the model's kv_mul.
- Verification: `t_amx_numerics` static checks (`eligible` is true for kv_mul 16 and false for kv_mul 8). The `t_amx_dispatch_dtype` fakes (test doubles for the kernels) record the group size of every pack, QK and PV call and require it to equal the model's. The attention path stats in [Verification] show AMX on the 39 sliding-window layers and the FPGA on the 13 full layers, and no AMX under the kill switch.

**Is the kv_mul-4 path unchanged?**

- `src/tron/kernels/amx_attn.cpp`: every head loop bound is `group_heads` (4 in the kv_mul-4 instantiation). The `thread_local` P scratch is one per instantiation.
- Verification: the object compare in [Verification] (pack and QK identical, PV differs only in the thread-local access model) and the llama-3.1-8b cell (kv_mul 4) in [Verification].

## Verification

Every result below comes from head 5061623a34 (branch `jhan-amx-kvmul16`, base main 6198824246) on delphi-3bda, our half, on 2026-10-16 and 2026-10-17, built inside `nix develop` with clang 19.1.7, preset `native`, RelWithDebInfo, `-DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`. One binary, two arms: AMX-on (the kill switch unset) and AMX-off (the kill switch set). The runtron cells run 8 users, 256 generated tokens (runtron reports 253), 2 repetitions, with FPGA attention (the model default) and with CPU attention. The object compare uses the zig-bundled clang 19.1.7 on the client host at -O3 on `amx_attn.cpp` from main and from the branch, outside the build system. Raw results: rt-results.txt, attn-stats-compare.md, tests.txt and local-obj-compare/ (result set glimmer-20261016).

### Builds and tests

| Configuration | Built | Tests (assertions / cases) |
|---|---|---|
| AMX on | runtron, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | t_amx_numerics 17,424 / 4 pass, t_amx_dispatch_dtype 5,756 / 1 pass, t_llama_unit 265,452 / 67 pass |
| AMX off (kill switch) | same binaries | t_amx_numerics 4,110 / 4 pass, 2 sections skipped with "AMX unavailable on this host" (the precision checks need the kernel) |

The clang-format check was not run locally (no nix shell on the client host). CI runs it. No mutation check was run.

Object compare (lines of each disassembly listing, one of which is the label line):

| Kernel | main | branch, 4 heads | branch, 16 heads | main vs branch 4 heads |
|---|---|---|---|---|
| pack_q_group_128x4 | 510 | 510 | 1,286 | identical |
| qk_rowmajor_128x4 | 205 | 205 | 208 | identical (16 `tdpbf16ps` tile multiplies in each, and 40 `vshuf` shuffles in the 16-head kernel only) |
| weights_times_v_128x4 | 122 | 122 | 207 | differs only in how the thread-local scratch is addressed (main local-dynamic, branch general-dynamic, the register and offset differences follow from it). The linker rewrites both to the same code |

### Token identity

Not measured. The runtron cells ran 8 free-running users, which is not a token-identity setup. The kernel-level checks are the numerics cases above (QK and PV against the AVX dotter, both group sizes). The pending measurement is in [Open items].

### Performance

Decision rule: a difference counts when it exceeds a band of twice the larger of the two arms' sample standard deviations over the 2 repetitions. With 2 repetitions no t statistic is given. The band is the whole rule. Decode TPS (tokens per second) per user is the mean over the 8 users' "average tok/s" lines, then over repetitions. Prefill time is the slowest user's "Parsing the prompt took" value. Differences come from the unrounded means.

| Cell (Glimmer 30B unless noted) | AMX off TPS/user | AMX on TPS/user | Difference | Band |
|---|---|---|---|---|
| tp2, prompt 1024, FPGA attention | 38.42 | 41.89 | +3.47 (+9.0 %) | 0.01 |
| tp2, prompt 2048, FPGA attention | 33.11 | 38.15 | +5.04 (+15.2 %) | 0.09 |
| tp4, prompt 1024, FPGA attention | 60.44 | 63.08 | +2.64 (+4.4 %) | 0.38 |
| tp4, prompt 2048, FPGA attention | 54.21 | 59.74 | +5.53 (+10.2 %) | 0.21 |
| tp2, prompt 1024, CPU attention | 37.15 | 42.14 | +4.99 (+13.4 %) | 0.10 |
| tp2, prompt 2048, CPU attention | 31.17 | 37.78 | +6.61 (+21.2 %) | 0.06 |
| tp4, prompt 1024, CPU attention | 58.96 | 62.54 | +3.58 (+6.1 %) | 0.04 |
| tp4, prompt 2048, CPU attention | 51.63 | 58.71 | +7.08 (+13.7 %) | 0.43 |
| llama-3.1-8b tp2, prompt 1024, CPU attention | 113.20 | 119.08 | +5.88 (+5.2 %) | 0.58 |

Prefill time shortens in every cell: by 0.6 to 8.7 % with FPGA attention, by 1.3 to 14.8 % with CPU attention and by 6.3 % on llama-3.1-8b (the rows are in rt-results.txt). Every difference, in the table and in that file, is beyond its band. What the tables say:

- The attention path stats (attn-stats-compare.md) show that with FPGA attention the AMX kernel scores 72.1 % of the K (key) tokens of a decode step at prompt 1024 (the 39 sliding-window layers), the FPGA 24.9 % and the AVX loop 2.9 % (the KV pages the AMX gate refuses because they are not full).
- The busy time per attention worker thread per forward falls from 5.3 ms to 3.1 ms at tp2, prompt 1024 (27.1 s and 16.0 s summed over 20 workers and 256 forwards). The forward wall time falls from 25.9 ms to 23.7 ms. Attention is about one fifth of the AMX-off step.
- The gain grows with the prompt length, and it grows with CPU attention. A longer prompt adds K tokens to every step. CPU attention adds the 13 full layers to the AMX share.
- The llama-3.1-8b cell (kv_mul 4, the unchanged path) gains +5.2 % decode TPS per user, beyond its band.

### Performance at the CI configuration

The nightly CI perf phase runs Glimmer tp4 with 8 users per machine on 2 engines of 4 cards, prompt 1024, 1,536 generated tokens. summary.md records the harness settings (prompt set, rounds, capture window).

The CI-configuration cells run that shape with the nightly's own harness on the whole of delphi-3bda (2026-10-17): three arms, three passes each, interleaved. Every arm runs FPGA attention on the 13 full layers, as the nightly does. One pass = 80 requests.

- `base`: the nightly deb (the Debian package the nightly builds) of 2026-10-17 (main 3751511dcc, the main the nightly built that day, whose gate refuses Glimmer).
- `AMX off`: the deb of this head with the kill switch in /opt/positron/user/config.env.
- `AMX on`: the deb of this head.

TTFT is the harness's time to first token, which holds the prompt parse of 4 users on one engine.

Raw results: perf.json per pass (every request) and summary.md (result set glimci-20261017).

| Arm | Passes | TPS per user (mean over passes) | sd (sample standard deviation) over passes | TTFT ms | prefill proxy tok/s (1024 / TTFT) |
|---|---|---|---|---|---|
| nightly GitHub Actions run 38999609242 (2026-10-17) | 1 | 78.69 | - | 3697 | 277.0 |
| base (nightly deb) | 3 | 78.69 | 0.13 | 3780 | 270.9 |
| AMX off (this head, kill switch) | 3 | 78.60 | 0.25 | 3781 | 270.8 |
| AMX on (this head) | 3 | 82.27 | 0.28 | 3651 | 280.5 |

Decision rule: paired t over the 3 passes, with the sd over passes as the band. What the table says: the base arm reproduces the nightly's row (78.69 against 78.69 tokens/s per user). The kill switch on this head equals the base arm (-0.1 %, t -0.4, inside the band). AMX on gains +4.6 % decode TPS per user over the base arm (t 33.1, far beyond the band) and shortens TTFT by 3.4 %. The AMX-busy probe (20 s of EXE.AMX_BUSY, the CPU counter of cycles in which the AMX unit is busy, on both engine processes during 4 probe requests) counted 5.52 to 5.56 billion busy cycles in the AMX-on passes (the AMX unit is in use) and 0 in every other pass (it is not).

## Open items

**Kill switch against a build without the AMX code.** Every AMX-off result in [Verification] is the kill switch on the AMX build. Whether it equals a `TRON_AMX_DISPATCH=OFF` build on Glimmer is not measured. The measurement is the same runtron cells with such a build as a third arm.

**Token identity between the arms.** Not measured. The measurement is runtron with pay-for-determinism, temperature 0, CPU attention and one prompt, AMX-on against AMX-off, on Glimmer tp2 at prompt 1024. The kill-switch tokens must match. A difference against main is informational.

The author decides before merging whether either measurement is needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

