# i5097-20261021 results: the dense-page live-mask fast path (fix) against PR 5047's head and base, with and without the AMX kill switch, on llama-3.1-8b

Words used here: base = runtron built from PR 5047's base (= PR 4956 head a5697f86d3), head = runtron built from the PR 5047 head (ade89a9d9c), fix = PR 5098 head plus the dense-page live-mask fast path (b79dfb9fed), c1 = PR 5047 commit 1 alone (e17a12ff09); every binary has the CMake option TRON_K_VNNI OFF and the same recipe on delphi-3bda (plain shell, clang 19, preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON); <arm>off = the same binary under the kill switch TRON_AMX_DISABLE=1 (every K token on the software scoring path); K tokens by path = the exit report of TRON_ATTN_STATS=1; attention cpu = USE_HW_ATTN=0.

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
build b47f:
    tag b47f worktree /var/tmp/jhan/tron-b47f option TRON_K_VNNI=OFF
    tip b79dfb9fed9a780282b277812ba9f378ee056f47 (2026-10-21 13:53:02 -0700 tests: the dense-page fast path selects the same tokens as the token loop)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.22-b79dfb9f
    checks: cache_vnni=OFF (need OFF) define_count=0 tdpbf16ps=32 (need > 0) TRON_ATTN_STATS=4 (need > 0) amx_kernel_symbols=10 qk_group_symbols=0 (informational)
    t_heterogeneous_scheduler build rc=0 wall=192s (tag b47f, option OFF)
build b47c1:
    tag b47c1 worktree /var/tmp/jhan/tron-b47c1 option TRON_K_VNNI=OFF
    tip e17a12ff09ea284ebd2616d1bf0531d7502e118d (2026-10-20 15:03:36 +0000 self_attention: Make token selection logic a bit more obvious)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.22-e17a12ff
    checks: cache_vnni=OFF (need OFF) define_count=0 tdpbf16ps=32 (need > 0) TRON_ATTN_STATS=4 (need > 0) amx_kernel_symbols=10 qk_group_symbols=0 (informational)
    t_heterogeneous_scheduler build rc=0 wall=197s (tag b47c1, option OFF)

tests (head builds):
    # tag | test name | assertions | rc   (head b79dfb9fed9a780282b277812ba9f378ee056f47; SYSTEM_CONFIG=--instance 1,2 on cpus 72-143,216-287; args --skip-benchmarks)
    b47f | t_amx_numerics | 4109 | 0 | env=[] skips=0 | All tests passed (4109 assertions in 4 test cases)
    b47f | t_amx_dispatch_dtype | 1612 | 0 | env=[] skips=0 | All tests passed (1612 assertions in 1 test case)
    b47f | t_llama_unit | 267937 | 0 | env=[] skips=0 | All tests passed (267937 assertions in 68 test cases)
    b47f | t_amx_numerics-killswitch | 2060 | 0 | env=[TRON_AMX_DISABLE=1] skips=2 |  AMX unavailable on this host - QK precision check skipped AMX unavailable on this host - PV precision check skipped All tests passed (2060 assertions in 4 test cases)
    b47f | t_llama_unit-killswitch | 267937 | 0 | env=[TRON_AMX_DISABLE=1] skips=0 | All tests passed (267937 assertions in 68 test cases)

## 2. Token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)

| cell | verdict | pair | result | role |
|---|---|---|---|---|
| l8b-tp2-cpu-p1024 | ok | fix vs fix2 | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | fix vs head | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024-off | ok | fixoff vs headoff | identical for 256 tokens (lengths 256 / 256) | must match |

## 3. Throughput, head vs base (8 users, 256 generated tokens, --dont-stop)

| cell | attention | arm | reps | decode TPS per user (sd) | prefill s (sd) | K tokens by path (mean over reps) | early-stop runs |
|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p8192-off | cpu | baseoff | 4 | 21.37 (0.01) | 78.825 (0.067) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-off | cpu | headoff | 4 | 21.45 (0.03) | 80.977 (0.050) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-off | cpu | fixoff | 4 | 21.63 (0.02) | 77.842 (0.140) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-off | cpu | c1off | 4 | 21.42 (0.06) | 81.338 (0.028) | AMX 0.0 %, AVX 100.0 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | base | 4 | 25.37 (0.04) | 35.359 (0.053) | AMX 97.2 %, AVX 2.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | head | 4 | 25.34 (0.02) | 35.453 (0.056) | AMX 97.2 %, AVX 2.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | fix | 4 | 25.32 (0.02) | 35.281 (0.073) | AMX 97.2 %, AVX 2.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | head | 4 | 117.82 (0.24) | 3.423 (0.001) | AMX 89.8 %, AVX 10.2 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | fix | 4 | 117.81 (0.10) | 3.425 (0.001) | AMX 89.8 %, AVX 10.2 %, FPGA 0.0 % | 0 |

Paired deltas per cell (band = twice the larger arm sd, at least 0.4 TPS / 0.15 s; verdict per the decision rule in the header):

| cell | attention | pair | TPS delta (mean over paired reps) | TPS delta % | TPS band | t | prefill delta s | prefill delta % | prefill band s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p8192-off | cpu | headoff:baseoff | 0.08 (n 4) | 0.4 % | 0.40 | 5.4 | 2.152 | 2.7 % | 0.150 | DEGRADATION beyond the band |
| l8b-tp2-8u-p8192-off | cpu | fixoff:headoff | 0.17 (n 4) | 0.8 % | 0.40 | 11.7 | -3.135 | -3.9 % | 0.280 | holds |
| l8b-tp2-8u-p8192-off | cpu | fixoff:baseoff | 0.25 (n 4) | 1.2 % | 0.40 | 42.1 | -0.982 | -1.2 % | 0.280 | holds |
| l8b-tp2-8u-p8192-off | cpu | c1off:baseoff | 0.05 (n 4) | 0.2 % | 0.40 | 1.3 | 2.513 | 3.2 % | 0.150 | DEGRADATION beyond the band |
| l8b-tp2-8u-p8192-cpu | cpu | head:base | -0.03 (n 4) | -0.1 % | 0.40 | -1.7 | 0.094 | 0.3 % | 0.150 | holds |
| l8b-tp2-8u-p8192-cpu | cpu | fix:head | -0.01 (n 4) | -0.1 % | 0.40 | -0.7 | -0.172 | -0.5 % | 0.150 | holds |
| l8b-tp2-8u-p8192-cpu | cpu | fix:base | -0.05 (n 4) | -0.2 % | 0.40 | -2.4 | -0.078 | -0.2 % | 0.150 | holds |
| l8b-tp2-8u-p1024-cpu | cpu | fix:head | -0.02 (n 4) | -0.0 % | 0.49 | -0.1 | 0.002 | 0.1 % | 0.150 | holds |
