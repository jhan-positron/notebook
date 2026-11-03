# pr5047-20261020 results: PR 5047 (Ben's refactor of the PR 4956 K-layout code) with and without the change, on llama-3.1-8b, qwen3-4b and gpt-oss-120b

Words used here: base = runtron built from PR 5047's base (= PR 4956 head a5697f86d3), head = runtron built from the PR 5047 head (ade89a9d9c); the option = the CMake option TRON_K_VNNI (OFF in every preset); basev / headv = the same commits with the option ON; all four built with the same recipe on delphi-3bda (plain shell, clang 19, preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON); K tokens by path = the exit report of TRON_ATTN_STATS=1 (K tokens scored by the AMX kernel / the AVX software path / the FPGA); attention cpu = USE_HW_ATTN=0, fpga = the model default.

## 1. Builds and tests

build b47b:
    tag b47b worktree /var/tmp/jhan/tron-b47b option TRON_K_VNNI=OFF
    tip a5697f86d318e6a87badd4a751a005da52a9c25c (2026-10-15 21:38:29 +0000 Merge branch 'main' into jhan-vnnik-1-layout)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.21-a5697f86
    checks: cache_vnni=OFF (need OFF) define_count=0
build b47h:
    tag b47h worktree /var/tmp/jhan/tron-b47h option TRON_K_VNNI=OFF
    tip ade89a9d9c83f887270c89d6ae6c02bced3f037e (2026-10-20 17:38:46 +0000 kv_cache: hide K layout behind row and scoring operations)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.21-ade89a9d
    checks: cache_vnni=OFF (need OFF) define_count=0
build b47bv:
    tag b47bv worktree /var/tmp/jhan/tron-b47bv option TRON_K_VNNI=ON
    tip a5697f86d318e6a87badd4a751a005da52a9c25c (2026-10-15 21:38:29 +0000 Merge branch 'main' into jhan-vnnik-1-layout)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.21-a5697f86
    checks: cache_vnni=ON (need ON) define_count=240 tdpbf16ps=32 (need > 0) TRON_ATTN_STATS=4 (need > 0) amx_kernel_symbols=10 qk_group_symbols=0 (informational)
    t_heterogeneous_scheduler build rc=0 wall=145s (tag b47bv, option ON)
build b47hv:
    tag b47hv worktree /var/tmp/jhan/tron-b47hv option TRON_K_VNNI=ON
    tip ade89a9d9c83f887270c89d6ae6c02bced3f037e (2026-10-20 17:38:46 +0000 kv_cache: hide K layout behind row and scoring operations)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.21-ade89a9d
    checks: cache_vnni=ON (need ON) define_count=240 tdpbf16ps=32 (need > 0) TRON_ATTN_STATS=4 (need > 0) amx_kernel_symbols=10 qk_group_symbols=0 (informational)
    t_heterogeneous_scheduler build rc=1 wall=174s (tag b47hv, option ON)

tests (head builds):
    # tag | test name | assertions | rc   (head ade89a9d9c83f887270c89d6ae6c02bced3f037e; SYSTEM_CONFIG=--instance 1,2 on cpus 72-143,216-287; args --skip-benchmarks)
    b47h | t_amx_numerics | 4109 | 0 | env=[] skips=0 | All tests passed (4109 assertions in 4 test cases)
    b47h | t_amx_dispatch_dtype | 1612 | 0 | env=[] skips=0 | All tests passed (1612 assertions in 1 test case)
    b47h | t_llama_unit | 266356 | 0 | env=[] skips=0 | All tests passed (266356 assertions in 67 test cases)
    b47hv | t_amx_numerics | 4109 | 0 | env=[] skips=0 | All tests passed (4109 assertions in 4 test cases)
    b47hv | t_amx_dispatch_dtype | 1612 | 0 | env=[] skips=0 | All tests passed (1612 assertions in 1 test case)
    b47hv | t_llama_unit | 266356 | 0 | env=[] skips=0 | All tests passed (266356 assertions in 67 test cases)
    b47h | t_amx_numerics-killswitch | 2060 | 0 | env=[TRON_AMX_DISABLE=1] skips=2 |  AMX unavailable on this host - QK precision check skipped AMX unavailable on this host - PV precision check skipped All tests passed (2060 assertions in 4 test cases)

## 2. Token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)

| cell | verdict | pair | result | role |
|---|---|---|---|---|
| gptoss-tp4-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| gptoss-tp4-fpga-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | headv vs basev | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | headv vs head | first difference at generated token 19 of 256 (757 vs 856); agreeing prefix 19 tokens; 234 of 256 positions differ | informational |
| q4b-tp2-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| q4b-tp2-fpga-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| q4b-tp2-fpga-p1024 | ok | headv vs basev | identical for 256 tokens (lengths 256 / 256) | must match |
| q4b-tp2-fpga-p1024 | ok | headv vs head | first difference at generated token 83 of 256 (258 vs 1499); agreeing prefix 83 tokens; 163 of 256 positions differ | informational |

## 3. Throughput, head vs base (8 users, 256 generated tokens, --dont-stop)

| cell | attention | arm | reps | decode TPS per user (sd) | prefill s (sd) | K tokens by path (mean over reps) | early-stop runs |
|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | base | 4 | 119.51 (0.22) | 3.407 (0.000) | AMX 89.8 %, AVX 10.2 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | head | 4 | 119.38 (0.17) | 3.405 (0.002) | AMX 89.8 %, AVX 10.2 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | basev | 4 | 114.14 (0.76) | 3.685 (0.009) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | headv | 4 | 113.50 (0.50) | 3.690 (0.008) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | base | 4 | 133.57 (0.62) | 3.040 (0.003) | AMX 0.0 %, AVX 41.5 %, FPGA 58.5 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | head | 4 | 133.81 (0.64) | 3.050 (0.002) | AMX 0.0 %, AVX 41.5 %, FPGA 58.5 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | basev | 4 | 130.93 (0.75) | 3.231 (0.003) | AMX 0.0 %, AVX 41.5 %, FPGA 58.5 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | headv | 4 | 130.97 (0.46) | 3.247 (0.001) | AMX 0.0 %, AVX 41.5 %, FPGA 58.5 % | 0 |
| gptoss-tp4-8u-p1024-fpga | fpga | base | 4 | 98.44 (2.32) | 2.713 (0.001) | AMX 0.0 %, AVX 70.3 %, FPGA 29.7 % | 0 |
| gptoss-tp4-8u-p1024-fpga | fpga | head | 4 | 97.61 (0.60) | 2.728 (0.004) | AMX 0.0 %, AVX 70.3 %, FPGA 29.7 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | base | 4 | 25.37 (0.03) | 35.258 (0.075) | AMX 97.2 %, AVX 2.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | head | 4 | 25.30 (0.04) | 35.396 (0.012) | AMX 97.2 %, AVX 2.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | basev | 4 | 22.60 (0.07) | 75.882 (0.138) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | headv | 4 | 22.29 (0.05) | 75.979 (0.047) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | base | 4 | 61.73 (0.11) | 26.273 (0.015) | AMX 3.9 %, AVX 10.4 %, FPGA 85.8 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | head | 4 | 61.82 (0.01) | 26.319 (0.020) | AMX 3.9 %, AVX 10.4 %, FPGA 85.8 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | basev | 4 | 61.69 (0.17) | 27.346 (0.018) | AMX 0.0 %, AVX 14.2 %, FPGA 85.8 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | headv | 4 | 61.70 (0.23) | 27.431 (0.024) | AMX 0.0 %, AVX 14.2 %, FPGA 85.8 % | 0 |
| l8b-tp2-8u-p4096-cpu | cpu | base | 4 | 47.89 (0.06) | 14.182 (0.042) | AMX 95.1 %, AVX 4.9 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p4096-cpu | cpu | head | 4 | 47.81 (0.15) | 14.230 (0.014) | AMX 95.1 %, AVX 4.9 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-off | cpu | baseoff | 4 | 21.39 (0.04) | 78.793 (0.083) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-off | cpu | headoff | 4 | 21.46 (0.05) | 81.040 (0.057) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |

Paired deltas per cell (band = twice the larger arm sd, at least 0.4 TPS / 0.15 s; verdict per the decision rule in the header):

| cell | attention | pair | TPS delta (mean over paired reps) | TPS delta % | TPS band | t | prefill delta s | prefill delta % | prefill band s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | head:base | -0.13 (n 4) | -0.1 % | 0.43 | -1.3 | -0.001 | -0.0 % | 0.150 | holds |
| l8b-tp2-8u-p1024-cpu | cpu | headv:basev | -0.65 (n 4) | -0.6 % | 1.52 | -1.1 | 0.005 | 0.1 % | 0.150 | holds |
| q4b-tp2-8u-p1024-fpga | fpga | head:base | 0.24 (n 4) | 0.2 % | 1.29 | 0.5 | 0.010 | 0.3 % | 0.150 | holds |
| q4b-tp2-8u-p1024-fpga | fpga | headv:basev | 0.04 (n 4) | 0.0 % | 1.50 | 0.1 | 0.016 | 0.5 % | 0.150 | holds |
| gptoss-tp4-8u-p1024-fpga | fpga | head:base | -0.83 (n 4) | -0.8 % | 4.65 | -0.8 | 0.015 | 0.5 % | 0.150 | holds |
| l8b-tp2-8u-p8192-cpu | cpu | head:base | -0.07 (n 4) | -0.3 % | 0.40 | -2.1 | 0.138 | 0.4 % | 0.150 | holds |
| l8b-tp2-8u-p8192-cpu | cpu | headv:basev | -0.32 (n 4) | -1.4 % | 0.40 | -8.2 | 0.098 | 0.1 % | 0.275 | holds |
| q4b-tp2-8u-p8192-fpga | fpga | head:base | 0.09 (n 4) | 0.1 % | 0.40 | 1.7 | 0.046 | 0.2 % | 0.150 | holds |
| q4b-tp2-8u-p8192-fpga | fpga | headv:basev | 0.01 (n 4) | 0.0 % | 0.47 | 0.1 | 0.085 | 0.3 % | 0.150 | holds |
| l8b-tp2-8u-p4096-cpu | cpu | head:base | -0.07 (n 4) | -0.2 % | 0.40 | -1.0 | 0.048 | 0.3 % | 0.150 | holds |
| l8b-tp2-8u-p8192-off | cpu | headoff:baseoff | 0.07 (n 4) | 0.3 % | 0.40 | 2.0 | 2.247 | 2.9 % | 0.166 | DEGRADATION beyond the band |
