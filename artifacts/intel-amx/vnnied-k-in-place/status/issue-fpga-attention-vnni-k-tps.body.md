## Short version

With FPGA attention (the nightly's default for ingested models), a build that carries PR #4424 (the VNNI K layout, `TRON_K_VNNI=ON`) decodes qwen-3-4b 2 to 11 % slower than the same code without the layout. The loss grows with the load per engine and is largest at tp4. In the nightly's own layout it moves qwen-3-4b tp4 from PASS to FAIL against the CI threshold. This issue tracks the measurement of the cause and the decision on a fix before the layout is enabled in a shipped package.

## Words used here

| Term | Meaning |
|---|---|
| FPGA attention, hardware attention | Attention scored on the FPGA cards from query position 127 on (`USE_HW_ATTN` unset; the default for ingested models). Positions 0 to 126 and the newest tokens not yet copied to the card stay on CPU attention. |
| VNNI K layout | PR #4424: the K cache of 128-dimension heads stored in the AMX pair-interleaved layout. A CMake option (`TRON_K_VNNI`), not a run-time switch. |
| AMX kernel | PR #3879's tile kernel for CPU attention (`TRON_AMX_DISPATCH=ON`); kill switch `TRON_AMX_DISABLE=1`. |
| gof::populate | The routine that copies a token's K and V rows from the host cache into the buffer the FPGA reads (`h/tron/gof.hpp`, `src/tron/gof.cpp`, `h/tron/scheduler/full.hpp`). It is the only reader of host K on the FPGA path. |
| TPS | Decode tokens per second per user. TTFT = time to first token. |
| CI harness | systems_test `testlib/tps.py`: prompt 1024 (sharegpt), generate 1536, 10 rounds, TPS captured over generated tokens 896 to 1024. |
| nightly layout | 8 users through the Caddy proxy over 4 tp2 engines (2 users per engine) or 2 tp4 engines (4 users per engine). |
| paired t | The mean of the per-round (or per-repetition) differences divided by its standard error. With 10 rounds the 95 % threshold is 2.26, with 6 repetitions 2.57. |

## Measurements

All on delphi-3bda (Xeon 6962P, 8 FPGA cards), `USE_HW_ATTN` unset, prompt 1024. Base and head differ only by PR #4424 unless stated.

| date | driver, layout | config | without PR #4424 | with PR #4424 | change | evidence |
|---|---|---|---|---|---|---|
| 2026-09-15 | runtron, 1 engine, 8 users, 256 tokens, n = 1 | tp2 | 125.39 TPS | 123.62 | -1.4 % | PR #4424 description, measurements table |
| 2026-09-16 | runtron, 1 engine, 8 users, 256 tokens, n = 6 | tp2 | 125.41 | 122.61 | -2.2 % (paired t -6.5) | exec/results/wedperf-attr-20260916, block D (main c7844ca2ce vs head ff680c8020) |
| 2026-09-16 | same | tp4 | 129.65 | 117.12 | -9.7 % (t -2.9) | same |
| 2026-09-18 | CI harness, nightly layout, whole machine, 10 rounds, 1 run per arm | tp2 @8u | 186.13 | 176.75 | -5.0 % (t -7.5 over rounds) | exec/results/ci-mimic-20260918 (nightly deb 2026.09.18-3faba6d0 vs the same main 3faba6d0 + PR #4424 30c4ac82cb as a deb, 2026.09.18-29a8a547) |
| 2026-09-18 | same | tp4 @8u | 149.94 | 133.44 | -11.0 % (t -10.2) | same; CI threshold 135 TPS: the nightly passed, the PR package fails |

### Latest data in detail (2026-09-18, the nightly's own configuration)

The client was the nightly's perf phase (systems_test scripts/perf.py test_performance) with platformd provisioning and the Caddy proxy, run by hand right after the nightly, on the whole machine, with the nightly's exact configuration. The base arm reproduced the same-day nightly within 1.6 % on 11 of 12 configs.

| config | arm | TPS mean over 80 samples | sd | slowest sample | TTFT ms | per-round means (10 rounds of 8 users) |
|---|---|---|---|---|---|---|
| tp2 @8u | base (nightly deb) | 186.13 | 8.92 | 173.9 | 556 | 183.9, 189.3, 186.8, 187.7, 185.4, 189.0, 183.7, 180.1, 190.5, 185.0 |
| tp2 @8u | with PR #4424 | 176.75 | 7.35 | 163.2 | 504 | 176.0, 177.8, 179.8, 175.4, 176.6, 179.3, 175.9, 178.6, 174.0, 174.0 |
| tp4 @8u | base (nightly deb) | 149.94 | 7.34 | 135.2 | 650 | 150.0, 149.1, 153.8, 150.9, 149.0, 151.1, 153.4, 146.1, 150.7, 145.3 |
| tp4 @8u | with PR #4424 | 133.44 | 4.16 | 128.2 | 629 | 133.2, 135.4, 134.7, 130.5, 129.3, 132.2, 130.4, 139.5, 133.4, 135.6 |

Every one of the 10 rounds is slower with the PR in both configs. The 13 earlier nightlies had tp4 at 146.6 to 153.4 TPS, so 133.44 is far outside the night-to-night band. The TTFT differences (-52 ms at tp2, -21 ms at tp4) are not attributable: the client host was CPU-saturated by other containers during the base arm and lightly loaded during the target arm, which inflates the base TTFT.

Token output with FPGA attention was identical between the two binaries in the one smoke run that compared it (128 of 128 tokens, 2026-09-15, exec/results/vnnik4-models-20260915). So this is a speed problem, not a correctness problem.

The 2026-09-18 package also had the AMX kernel compiled and enabled. The AMX probe (EXE.AMX_BUSY counter, 20 s on the four tp2 engines while 4 streaming requests ran) recorded 13.7 billion busy cycles, so the kernel ran on the CPU-scored share. The 2026-09-16 attribution separates the two: the step from main (with the AMX kernel, no layout) to main + PR #4424 is the loss; the AMX kernel step alone was +0.5 % (tp2) and -2.0 % (tp4), neither resolved.

## What is not affected

- Models that run CPU attention (llama, mixtral, qwen-2.5, gemma-2): no FPGA staging happens there. Measured 2026-09-18 in the same run: llama-3.1-8b +0.8 %, llama-3.3-70b tp2 @4u +1.1 %, the others within +/-0.5 %.
- 64-dimension heads (gpt-oss-120b): the layout gate is `head_size == 128`, those heads stay row-major. Measured -0.3 %, not resolved.
- Correctness of the FPGA path: tokens identical in the one comparison above.

## Hypothesis for the cause (not measured)

The FPGA reads host K only through `gof::populate`. PR #4424 rewired its K source (`page_info::k_head_fn`) to gather one token's K row out of the VNNI layout (`k_vnni::gather_row`) into a scratch buffer. A row gathered from the VNNI layout touches 64 cache lines per (token, KV head) instead of 4 for a row-major row. Every generated token's K must be staged to the card, so the gather lands in every decode step. The design estimate in the PR was about 1 us per GOF per layer; it was never measured. The loss growing with tp (tp4 has a shorter FPGA step, so a fixed CPU cost is a larger share) and with users per engine fits this picture.

Measurement that would confirm or reject it: perfetto spans `gof_populate` and `wait_coop_gof` on the same qwen-3-4b cell, base against head. If the gather is the cost, the span grows by the observed per-step loss (about 0.3 ms per step at tp4 from the numbers above, est.).

## Options (the PR owner decides, with the FPGA-attention owners)

1. Keep a row-major staging copy of K for the FPGA path, written at save time next to the VNNI plane (memory cost: one more K plane per page for 128-dimension heads).
2. Stage directly from the VNNI layout with a gather tuned for it (measure first).
3. Gate the layout off for models that run FPGA attention (`layout_on` currently depends only on head size); the AMX kernel would then not apply to their CPU-scored share either.
4. Accept the loss: not an option while it flips a CI threshold.

## Related

- PR #4424 (the layout), PR #3879 (the AMX kernel), issue #4444 (token divergence and the kill-switch contract), issue #4347 (enable AMX in CI).
- Local reports (intel-AMX workspace): VNNIed-K-in-place/status/Wednesday-perf-test.html (2026-09-16 cells and attribution), VNNIed-K-in-place/status/Friday-morning-CI-run-report.html (2026-09-18 nightly-layout run).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
