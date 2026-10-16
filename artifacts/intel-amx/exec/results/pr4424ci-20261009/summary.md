## pr4424ci-20261009 summary: base (nightly deb 2026.10.08-be0d5565) against target (PR 4424 deb)

Runs found: base-pass1 (14 cells, 109.6 min, tron None), target-pass1 (14 cells, 106.25 min, tron None), base-sw8k-pass1 (1 cells, 7.85 min, tron None), target-sw8k-pass1 (1 cells, 7.53 min, tron None), base-pass2 (14 cells, 109.04 min, tron None), target-pass2 (14 cells, 108.91 min, tron None), base-sw8k-pass2 (1 cells, 7.76 min, tron None), target-sw8k-pass2 (1 cells, 7.7 min, tron None)

Resolution rule: resolved = |paired t| >= 2.26 AND |delta| >= 1 % (TTFT also |delta| >= 1 ms). The paired t pools the paired-by-round differences (target - base, round means) of every complete pass pair (pass1 with pass1, pass2 with pass2; n = 10 rounds per pair). Memory = mean over passes of the sum over engine pids of VmHWM (peak resident set) and VmRSS read right after the benchmark (MiB; 1 GiB hugepages are NOT in these sums, they are in HugetlbPages). n/t = not testable (no complete pass pair).

### Full passes (the harness's 14 configs, FPGA attention as shipped)

| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama-3.2-3b-instruct-fast-tp2@32u-p200 | 198.26 (0.40) n=2 | 195.56 (0.44) n=2 | -1.4 % | -16.56 (20) | YES | 74 | 58 | -15 ms (-20.8 %) t=-1.47 | no | 8,714 | 8,719 | +6 MiB (+0.1 %) | 692 | 696 | +4 MiB |
| llama-3.1-8b-instruct-good-tp2@8u-p1024 | 143.03 (0.55) n=2 | 142.58 (0.57) n=2 | -0.3 % | -1.35 (20) | no | 586 | 585 | -0 ms (-0.1 %) t=-0.05 | no | 21,926 | 21,930 | +5 MiB (+0.0 %) | 758 | 759 | +1 MiB |
| llama-3.1-8b-instruct-good-tp2@32u-p4096 | 32.62 (0.02) n=2 | 34.20 (0.03) n=2 | +4.8 % | +39.40 (20) | YES | 11,821 | 11,833 | +12 ms (+0.1 %) t=+0.66 | no | 21,926 | 21,930 | +5 MiB (+0.0 %) | 987 | 1,001 | +14 MiB |
| llama-3.3-70b-instruct-good-tp2@8u-p1024 | 17.01 (0.01) n=2 | 17.00 (0.01) n=2 | -0.0 % | -2.11 (20) | no | 9,382 | 9,393 | +11 ms (+0.1 %) t=+0.98 | no | 151,916 | 151,918 | +2 MiB (+0.0 %) | 754 | 760 | +6 MiB |
| llama-3.3-70b-instruct-good-tp2@4u-p1024 | 28.46 (0.00) n=2 | 28.68 (0.04) n=2 | +0.8 % | +13.14 (20) | no | 4,086 | 4,457 | +371 ms (+9.1 %) t=+1.05 | no | 151,916 | 151,918 | +2 MiB (+0.0 %) | 764 | 772 | +7 MiB |
| llama-3.3-70b-instruct-good-tp4@4u-p1024 | 31.71 (0.00) n=2 | 31.67 (0.09) n=2 | -0.1 % | -0.77 (20) | no | 4,875 | 4,874 | -1 ms (-0.0 %) t=-0.16 | no | 75,903 | 75,903 | -0 MiB (-0.0 %) | 404 | 408 | +4 MiB |
| mixtral-8x7b-instruct-v0.1-tp2@8u-p1024 | 80.68 (0.31) n=2 | 80.62 (0.23) n=2 | -0.1 % | -0.16 (20) | no | 1,259 | 1,264 | +5 ms (+0.4 %) t=+2.24 | no | 356,379 | 356,363 | -16 MiB (-0.0 %) | 433 | 438 | +6 MiB |
| qwen-2.5-32b-it-fast-tp2@8u-p1024 | 36.06 (0.04) n=2 | 36.02 (0.01) n=2 | -0.1 % | -2.60 (20) | no | 3,946 | 3,939 | -7 ms (-0.2 %) t=-1.11 | no | 73,832 | 73,838 | +6 MiB (+0.0 %) | 727 | 730 | +3 MiB |
| ingested-qwen-3-4b-instruct-2507-tp2@8u-p1024 | 189.13 (1.04) n=2 | 187.38 (0.68) n=2 | -0.9 % | -2.19 (20) | no | 502 | 494 | -8 ms (-1.6 %) t=-1.01 | no | 16,457 | 16,457 | +0 MiB (+0.0 %) | 7,176 | 7,173 | -3 MiB |
| ingested-qwen-3-4b-instruct-2507-tp4@8u-p1024 | 181.01 (0.44) n=2 | 180.30 (0.55) n=2 | -0.4 % | -0.42 (20) | no | 557 | 545 | -12 ms (-2.1 %) t=-0.76 | no | 8,140 | 8,132 | -8 MiB (-0.1 %) | 3,947 | 3,971 | +25 MiB |
| gemma-2-9b-it-fast-tp2@8u-p1024 | 104.03 (0.12) n=2 | 104.84 (1.06) n=2 | +0.8 % | +0.97 (20) | no | 856 | 852 | -5 ms (-0.5 %) t=-1.73 | no | 23,678 | 23,597 | -81 MiB (-0.3 %) | 1,023 | 1,023 | -0 MiB |
| ingested-gpt-oss-120b-tp4@8u-p1024 | 122.38 (0.05) n=2 | 121.83 (1.34) n=2 | -0.5 % | -1.28 (20) | no | 966 | 944 | -22 ms (-2.3 %) t=-1.93 | no | 128,490 | 128,492 | +2 MiB (+0.0 %) | 5,496 | 5,492 | -4 MiB |
| ingested-gemma-4-31b-it-tp2@8u-p1024 | 38.21 (0.02) n=2 | 38.23 (0.04) n=2 | +0.1 % | +0.70 (20) | no | 5,456 | 5,448 | -8 ms (-0.1 %) t=-1.57 | no | 92,586 | 92,603 | +17 MiB (+0.0 %) | 22,651 | 22,653 | +1 MiB |
| ingested-meta-models--Muse-Glimmer-30B-tp4@8u-p1024 | 74.72 (0.02) n=2 | 76.53 (0.15) n=2 | +2.4 % | +24.35 (20) | YES | 3,720 | 3,602 | -118 ms (-3.2 %) t=-25.90 | YES | 46,420 | 46,428 | +8 MiB (+0.0 %) | 10,955 | 10,957 | +2 MiB |

### Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)

| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ingested-qwen-3-4b-instruct-2507-tp2@8u-p8192 | 59.84 (0.20) n=2 | 64.41 (0.26) n=2 | +7.6 % | +39.27 (20) | YES | 12,957 | 12,807 | -150 ms (-1.2 %) t=-8.97 | YES | 16,451 | 16,475 | +24 MiB (+0.1 %) | 6,854 | 6,895 | +41 MiB |

Per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state): all ok

