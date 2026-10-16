## pr4424ci-20261009 summary: base (nightly deb 2026.10.08-be0d5565) against target (PR 4424 deb)

Runs found: base-pass1 (14 cells, 109.6 min, tron None), target-pass1 (14 cells, 106.25 min, tron None), base-sw8k-pass1 (1 cells, 7.85 min, tron None), target-sw8k-pass1 (1 cells, 7.53 min, tron None), base-pass2 (2 cells, None min, tron None), target-pass2 (14 cells, 108.91 min, tron None), target-sw8k-pass2 (1 cells, 7.7 min, tron None)

Resolution rule: resolved = |paired t| >= 2.26 AND |delta| >= 1 % (TTFT also |delta| >= 1 ms). The paired t pools the paired-by-round differences (target - base, round means) of every complete pass pair (pass1 with pass1, pass2 with pass2; n = 10 rounds per pair). Memory = mean over passes of the sum over engine pids of VmHWM (peak resident set) and VmRSS read right after the benchmark (MiB; 1 GiB hugepages are NOT in these sums, they are in HugetlbPages). n/t = not testable (no complete pass pair).

### Full passes (the harness's 14 configs, FPGA attention as shipped)

| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama-3.2-3b-instruct-fast-tp2@32u-p200 | 198.26 (0.40) n=2 | 195.56 (0.44) n=2 | -1.4 % | -16.56 (20) | YES | 74 | 58 | -15 ms (-20.8 %) t=-1.47 | no | 8,714 | 8,719 | +6 MiB (+0.1 %) | 692 | 696 | +4 MiB |
| llama-3.1-8b-instruct-good-tp2@8u-p1024 | 143.03 (0.55) n=2 | 142.58 (0.57) n=2 | -0.3 % | -1.35 (20) | no | 586 | 585 | -0 ms (-0.1 %) t=-0.05 | no | 21,926 | 21,930 | +5 MiB (+0.0 %) | 758 | 759 | +1 MiB |
| llama-3.1-8b-instruct-good-tp2@32u-p4096 | 32.60 (0.00) n=1 | 34.20 (0.03) n=2 | +4.9 % | +53.44 (10) | YES | 11,815 | 11,833 | +18 ms (+0.2 %) t=-0.84 | no | 21,931 | 21,930 | -1 MiB (-0.0 %) | 995 | 1,001 | +6 MiB |
| llama-3.3-70b-instruct-good-tp2@8u-p1024 | 17.00 (0.00) n=1 | 17.00 (0.01) n=2 | -0.0 % | -1.67 (10) | no | 9,396 | 9,393 | -2 ms (-0.0 %) t=-0.09 | no | 151,921 | 151,918 | -2 MiB (-0.0 %) | 754 | 760 | +7 MiB |
| llama-3.3-70b-instruct-good-tp2@4u-p1024 | 28.45 (0.00) n=1 | 28.68 (0.04) n=2 | +0.8 % | +13.95 (10) | no | 4,397 | 4,457 | +59 ms (+1.3 %) t=-0.29 | no | 151,921 | 151,918 | -2 MiB (-0.0 %) | 763 | 772 | +8 MiB |
| llama-3.3-70b-instruct-good-tp4@4u-p1024 | 31.71 (0.00) n=1 | 31.67 (0.09) n=2 | -0.1 % | -2.87 (10) | no | 4,871 | 4,874 | +3 ms (+0.1 %) t=+0.87 | no | 75,902 | 75,903 | +1 MiB (+0.0 %) | 404 | 408 | +3 MiB |
| mixtral-8x7b-instruct-v0.1-tp2@8u-p1024 | 80.46 (0.00) n=1 | 80.62 (0.23) n=2 | +0.2 % | +0.69 (10) | no | 1,255 | 1,264 | +9 ms (+0.7 %) t=+1.38 | no | 356,378 | 356,363 | -15 MiB (-0.0 %) | 432 | 438 | +6 MiB |
| qwen-2.5-32b-it-fast-tp2@8u-p1024 | 36.04 (0.00) n=1 | 36.02 (0.01) n=2 | -0.1 % | -1.59 (10) | no | 3,948 | 3,939 | -8 ms (-0.2 %) t=-0.61 | no | 73,837 | 73,838 | +1 MiB (+0.0 %) | 727 | 730 | +2 MiB |
| ingested-qwen-3-4b-instruct-2507-tp2@8u-p1024 | 189.87 (0.00) n=1 | 187.38 (0.68) n=2 | -1.3 % | -1.51 (10) | no | 492 | 494 | +2 ms (+0.3 %) t=+0.37 | no | 16,475 | 16,457 | -18 MiB (-0.1 %) | 7,171 | 7,173 | +2 MiB |
| ingested-qwen-3-4b-instruct-2507-tp4@8u-p1024 | 181.32 (0.00) n=1 | 180.30 (0.55) n=2 | -0.6 % | -0.50 (10) | no | 559 | 545 | -14 ms (-2.5 %) t=-3.26 | YES | 8,139 | 8,132 | -7 MiB (-0.1 %) | 3,949 | 3,971 | +23 MiB |
| gemma-2-9b-it-fast-tp2@8u-p1024 | 104.11 (0.00) n=1 | 104.84 (1.06) n=2 | +0.7 % | -0.07 (10) | no | 856 | 852 | -4 ms (-0.5 %) t=-0.81 | no | 23,680 | 23,597 | -82 MiB (-0.3 %) | 1,024 | 1,023 | -1 MiB |
| ingested-gpt-oss-120b-tp4@8u-p1024 | 122.42 (0.00) n=1 | 121.83 (1.34) n=2 | -0.5 % | -3.17 (10) | no | 977 | 944 | -33 ms (-3.4 %) t=-1.75 | no | 128,487 | 128,492 | +5 MiB (+0.0 %) | 5,500 | 5,492 | -8 MiB |
| ingested-gemma-4-31b-it-tp2@8u-p1024 | 38.22 (0.00) n=1 | 38.23 (0.04) n=2 | +0.0 % | -0.35 (10) | no | 5,455 | 5,448 | -7 ms (-0.1 %) t=-0.67 | no | 92,584 | 92,603 | +19 MiB (+0.0 %) | 22,651 | 22,653 | +2 MiB |
| ingested-meta-models--Muse-Glimmer-30B-tp4@8u-p1024 | 74.73 (0.00) n=1 | 76.53 (0.15) n=2 | +2.4 % | +19.84 (10) | YES | 3,719 | 3,602 | -117 ms (-3.2 %) t=-18.99 | YES | 46,420 | 46,428 | +8 MiB (+0.0 %) | 10,958 | 10,957 | -1 MiB |

### Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)

| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ingested-qwen-3-4b-instruct-2507-tp2@8u-p8192 | 59.70 (0.00) n=1 | 64.41 (0.26) n=2 | +7.9 % | +28.80 (10) | YES | 12,970 | 12,807 | -163 ms (-1.3 %) t=-20.54 | YES | 16,426 | 16,475 | +50 MiB (+0.3 %) | 6,851 | 6,895 | +44 MiB |

Per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state): all ok

