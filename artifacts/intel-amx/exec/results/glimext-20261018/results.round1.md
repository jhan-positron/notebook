# glimext-20261018 results: PR #5015 (AMX attention kernels for kv_mul 16) with and without the change, on llama-3.1-8b, qwen3-4b, gpt-oss-120b and Muse Glimmer 30B

Words used here: base = runtron built from the PR's merge base (main 6198824246), head = runtron built from the PR head (5061623a34), both with the same recipe on delphi-3bda (plain shell, clang 19, preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON); headoff = head with the kill switch TRON_AMX_DISABLE=1; AMX share = K (key) tokens scored by the AMX kernel over all K tokens of the run's exit report (TRON_ATTN_STATS=1); attention cpu = USE_HW_ATTN=0, fpga = the model default.

## 1. Builds and tests

build g16b:
    tip 61988242460342b26f153ae5e05ec0b294174904 (2026-10-16 18:11:20 +0000 Merge pull request #4128 from positron-ai/mrc_dma_coalesce_02)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.18-61988242
build g16h:
    tip 5061623a346ba5e8d22a6de8b3ab4cc058023214 (2026-10-16 14:11:34 -0700 AMX attention: update comments that the group_heads parameter made stale)
    compiler: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75)
    version: 2026.10.18-5061623a

tests (head build):
    # test name | assertions | rc   (head 5061623a346ba5e8d22a6de8b3ab4cc058023214, binaries of /var/tmp/jhan/tron-g16h; SYSTEM_CONFIG=--instance 1,2 on cpus 72-143,216-287; args --skip-benchmarks)
    t_amx_numerics | 17424 | 0 | env=[] skips=0 | All tests passed (17424 assertions in 4 test cases)
    t_amx_dispatch_dtype | 5756 | 0 | env=[] skips=0 | All tests passed (5756 assertions in 1 test case)
    t_llama_unit | 265452 | 0 | env=[] skips=0 | All tests passed (265452 assertions in 67 test cases)
    t_amx_numerics-killswitch | 4110 | 0 | env=[TRON_AMX_DISABLE=1] skips=2 |  AMX unavailable on this host - QK precision check skipped AMX unavailable on this host - PV precision check skipped All tests passed (4110 assertions in 4 test cases)

preservation (base plain kernels vs head <4> instantiations, same compiler):
    pack_q_group_128x4: n/a (symbol <4> not found in the head; the host nm may not demangle the requires-clause template)
    qk_rowmajor_128x4: n/a (symbol <4> not found in the head; the host nm may not demangle the requires-clause template)
    weights_times_v_128x4: n/a (symbol <4> not found in the head; the host nm may not demangle the requires-clause template)

## 2. Token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)

| cell | verdict | pair | result | role |
|---|---|---|---|---|
| glm-tp2-cpu-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-cpu-p1024 | ok | head vs base | first difference at generated token 53 of 256 (2935 vs 50275); agreeing prefix 53 tokens; 200 of 256 positions differ | informational |
| glm-tp2-cpu-p1024 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-cpu-p1024 | ok | headoff vs head | first difference at generated token 53 of 256 (50275 vs 2935); agreeing prefix 53 tokens; 200 of 256 positions differ | informational |
| glm-tp2-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-fpga-p1024 | ok | head vs base | first difference at generated token 5 of 256 (806 vs 393); agreeing prefix 5 tokens; 249 of 256 positions differ | informational |
| glm-tp2-fpga-p1024 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-fpga-p1024 | ok | headoff vs head | first difference at generated token 5 of 256 (393 vs 806); agreeing prefix 5 tokens; 249 of 256 positions differ | informational |
| glm-tp2-fpga-p2048 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-fpga-p2048 | ok | head vs base | first difference at generated token 12 of 256 (4195 vs 1278); agreeing prefix 12 tokens; 243 of 256 positions differ | informational |
| glm-tp2-fpga-p2048 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp2-fpga-p2048 | ok | headoff vs head | first difference at generated token 12 of 256 (1278 vs 4195); agreeing prefix 12 tokens; 243 of 256 positions differ | informational |
| glm-tp4-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp4-fpga-p1024 | ok | head vs base | first difference at generated token 30 of 256 (2244 vs 14847); agreeing prefix 30 tokens; 224 of 256 positions differ | informational |
| glm-tp4-fpga-p1024 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| glm-tp4-fpga-p1024 | ok | headoff vs head | first difference at generated token 30 of 256 (14847 vs 2244); agreeing prefix 30 tokens; 224 of 256 positions differ | informational |
| gptoss-tp4-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| gptoss-tp4-fpga-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| gptoss-tp4-fpga-p1024 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | informational |
| gptoss-tp4-fpga-p1024 | ok | headoff vs head | identical for 256 tokens (lengths 256 / 256) | informational |
| l8b-tp2-cpu-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| l8b-tp2-cpu-p1024 | ok | headoff vs base | first difference at generated token 12 of 256 (433 vs 757); agreeing prefix 12 tokens; 239 of 256 positions differ | informational |
| l8b-tp2-cpu-p1024 | ok | headoff vs head | first difference at generated token 12 of 256 (433 vs 757); agreeing prefix 12 tokens; 239 of 256 positions differ | informational |
| q4b-tp2-fpga-p1024 | ok | head vs head2 | identical for 256 tokens (lengths 256 / 256) | must match |
| q4b-tp2-fpga-p1024 | ok | head vs base | identical for 256 tokens (lengths 256 / 256) | must match |
| q4b-tp2-fpga-p1024 | ok | headoff vs base | identical for 256 tokens (lengths 256 / 256) | informational |
| q4b-tp2-fpga-p1024 | ok | headoff vs head | identical for 256 tokens (lengths 256 / 256) | informational |

## 3. Throughput, base vs head (8 users, 256 generated tokens, --dont-stop)

| cell | attention | arm | reps | decode TPS per user (sd) | prefill s (sd) | AMX share of K tokens (mean over reps) | early-stop runs |
|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | base | 4 | 119.22 (0.11) | 3.405 (0.002) | AMX 89.8 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p1024-cpu | cpu | head | 4 | 119.35 (0.14) | 3.408 (0.002) | AMX 89.8 %, FPGA 0.0 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | base | 4 | 133.61 (0.16) | 3.056 (0.002) | AMX 0.0 %, FPGA 58.5 % | 0 |
| q4b-tp2-8u-p1024-fpga | fpga | head | 4 | 134.17 (0.15) | 3.057 (0.003) | AMX 0.0 %, FPGA 58.5 % | 0 |
| gptoss-tp4-8u-p1024-fpga | fpga | base | 4 | 96.77 (1.47) | 2.706 (0.005) | AMX 0.0 %, FPGA 29.7 % | 0 |
| gptoss-tp4-8u-p1024-fpga | fpga | head | 4 | 97.05 (0.35) | 2.701 (0.002) | AMX 0.0 %, FPGA 29.7 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | base | 4 | 25.34 (0.03) | 35.253 (0.038) | AMX 97.2 %, FPGA 0.0 % | 0 |
| l8b-tp2-8u-p8192-cpu | cpu | head | 4 | 25.25 (0.02) | 34.819 (0.057) | AMX 97.2 %, FPGA 0.0 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | base | 4 | 61.74 (0.06) | 26.396 (0.024) | AMX 3.9 %, FPGA 85.8 % | 0 |
| q4b-tp2-8u-p8192-fpga | fpga | head | 4 | 61.81 (0.07) | 26.384 (0.013) | AMX 3.9 %, FPGA 85.8 % | 0 |
| gptoss-tp4-8u-p2048-fpga | fpga | base | 4 | 95.05 (0.63) | 5.090 (0.007) | AMX 0.0 %, FPGA 38.8 % | 0 |
| gptoss-tp4-8u-p2048-fpga | fpga | head | 4 | 94.85 (1.67) | 5.093 (0.011) | AMX 0.0 %, FPGA 38.8 % | 0 |
| glm-tp2-8u-p1024-fpga | fpga | base | 4 | 38.34 (0.02) | 15.275 (0.035) | AMX 0.0 %, FPGA 13.0 % | 0 |
| glm-tp2-8u-p1024-fpga | fpga | head | 4 | 41.92 (0.05) | 14.840 (0.013) | AMX 70.8 %, FPGA 13.0 % | 0 |
| glm-tp2-8u-p2048-fpga | fpga | base | 4 | 33.01 (0.02) | 33.941 (0.032) | AMX 0.0 %, FPGA 13.2 % | 0 |
| glm-tp2-8u-p2048-fpga | fpga | head | 4 | 38.17 (0.05) | 30.922 (0.006) | AMX 75.8 %, FPGA 13.2 % | 0 |
| glm-tp4-8u-p1024-fpga | fpga | base | 4 | 60.46 (0.07) | 8.338 (0.021) | AMX 0.0 %, FPGA 13.0 % | 0 |
| glm-tp4-8u-p1024-fpga | fpga | head | 4 | 63.07 (0.09) | 8.296 (0.008) | AMX 70.8 %, FPGA 13.0 % | 0 |

Paired head minus base per cell (head vs base; band = twice the larger arm sd; verdict per the decision rule in the header):

| cell | attention | TPS delta (mean over paired reps) | TPS delta % | TPS band | t | prefill delta s | prefill delta % | prefill band s | verdict |
|---|---|---|---|---|---|---|---|---|---|
| l8b-tp2-8u-p1024-cpu | cpu | 0.13 (n 4) | 0.1 % | 0.27 | 1.4 | 0.003 | 0.1 % | 0.005 | holds |
| q4b-tp2-8u-p1024-fpga | fpga | 0.56 (n 4) | 0.4 % | 0.33 | 5.4 | 0.001 | 0.0 % | 0.006 | gain |
| gptoss-tp4-8u-p1024-fpga | fpga | 0.28 (n 4) | 0.3 % | 2.93 | 0.5 | -0.005 | -0.2 % | 0.010 | holds |
| l8b-tp2-8u-p8192-cpu | cpu | -0.09 (n 4) | -0.3 % | 0.05 | -18.1 | -0.435 | -1.2 % | 0.113 | DEGRADATION beyond the band |
| q4b-tp2-8u-p8192-fpga | fpga | 0.07 (n 4) | 0.1 % | 0.14 | 1.0 | -0.012 | -0.0 % | 0.049 | holds |
| gptoss-tp4-8u-p2048-fpga | fpga | -0.19 (n 4) | -0.2 % | 3.33 | -0.2 | 0.003 | 0.1 % | 0.023 | holds |
| glm-tp2-8u-p1024-fpga | fpga | 3.58 (n 4) | 9.3 % | 0.10 | 99.7 | -0.435 | -2.8 % | 0.070 | gain |
| glm-tp2-8u-p2048-fpga | fpga | 5.16 (n 4) | 15.6 % | 0.10 | 202.1 | -3.019 | -8.9 % | 0.064 | gain |
| glm-tp4-8u-p1024-fpga | fpga | 2.61 (n 4) | 4.3 % | 0.19 | 48.6 | -0.042 | -0.5 % | 0.041 | gain |

## 4. Near-tie margin at the first Glimmer divergence (teacher-forced logits, CPU attention)

```
run baseF rc=0 wall=847s tokens=256 logits-lines=768 full=51344169739 [21:22:56.460908835|thread 2071847|cpu 125] [info ] Version: 2026.10.18-61988242 hash: 61988242460342b26f153ae5e05ec0b294174904 [21:36:48.772581673|thread 2071934|cpu 125] [info ] [Request 1] Generating 253 response tokens with 1026 context
run headF rc=0 wall=850s tokens=256 logits-lines=768 full=51344082761 [21:37:19.242729426|thread 2072974|cpu 256] [info ] Version: 2026.10.18-5061623a hash: 5061623a346ba5e8d22a6de8b3ab4cc058023214 [21:51:15.344293745|thread 2073051|cpu 256] [info ] [Request 1] Generating 253 response tokens with 1026 context
baseF.tokens vs forced: identical for 256 tokens (lengths 256 / 256)
headF.tokens vs forced: identical for 256 tokens (lengths 256 / 256)
MARGIN steps=255/256 identical_steps=0 flips=[55, 100, 105] first_flip=55 nonflip median|delta_pair|=0.75 p95=3.112499999999997 median mean|d|=0.38827223587765053 max_tvd=0.49160218331771466 median margin_off=69.0
MARKED step=54 off_top1=3215 off_top2=97 on_top1=3215 on_top2=97 forced=50275 margin_off=75.25000 (150.5 ulps of 114.0000) margin_on_same_pair=75.25000 delta_pair=0.00000 mean|d|=0.318928 max|d|=2.00000 frac_changed=0.664 tvd=0.00000
MARGIN steps=256/256 identical_steps=0 flips=[54, 99, 104] first_flip=54 nonflip median|delta_pair|=0.75 p95=3.0999999999999943 median mean|d|=0.38933368592241974 max_tvd=0.49160218331771466 median margin_off=69.0
MARKED step=54 off_top1=50275 off_top2=2935 on_top1=2935 on_top2=50275 forced=50275 margin_off=1.31250 (21.0 ulps of 12.6250) margin_on_same_pair=-0.25000 delta_pair=-1.56250 mean|d|=0.476053 max|d|=3.25000 frac_changed=0.668 tvd=0.34001
```

At the marked step the base arm's top-1 minus top-2 margin is 1.31250 logit units (21.0 bf16 ulps of the top-1 logit 12.6250); the head arm moves that pair by -1.56250. Over all steps: 3 flips (argmax differs, at steps [54, 99, 104]), first flip at step 54, median |pair delta| on non-flip steps 0.75, max TVD 0.49160218331771466.
