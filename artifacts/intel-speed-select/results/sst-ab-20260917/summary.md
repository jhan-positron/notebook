# sst-ab-20260917 summary

Per cell and arm: mean over repetitions (sample sd, CV = sd/mean). TPS = decode tok/s per user; TTFT = prefill s (max over users). app MHz, dev MHz and pkg1 W are means over the turbostat 5-s samples whose app-core mean Busy% > 30; those samples cover prefill and decode together, so they show that the arm took effect and the pkg1 W delta is a whole-run delta, not the power cost of the TPS delta alone. fast cpus = app cpus (of 28) whose mean frequency is above the 2.7 GHz cap; the boot arm leaves 2 of them (126, 127, boot PCT cores) fast.

| cell | model | arm | n | TPS/user | sd | CV % | TTFT s | prefill tok/s/user | app MHz | fast cpus | dev MHz | pkg1 W | HW attn | binary version |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| l8b | llama-3.1-8b-instruct-good-tp2 | boot | 6 | 82.66 | 0.32 | 0.39 | 3.787 | 270.7 | 2798 | 2.0 | 2700 | 265.9 | disabled | 2026.09.17-31b80a18 |
| l8b | llama-3.1-8b-instruct-good-tp2 | tuned | 6 | 93.35 | 0.68 | 0.73 | 3.610 | 283.9 | 3952 | 28.0 | 2700 | 326.2 | disabled | 2026.09.17-31b80a18 |
| l8b | llama-3.1-8b-instruct-good-tp2 | tunedplus | 6 | 93.48 | 0.31 | 0.33 | 3.619 | 283.2 | 3949 | 28.0 | 4011 | 332.0 | disabled | 2026.09.17-31b80a18 |
| q3-4b | ingested-qwen-3-4b-instruct-2507-tp2 | boot | 6 | 118.68 | 1.19 | 1.00 | 3.343 | 306.3 | 2775 | 2.0 | 2698 | 225.4 | enabled | 2026.09.17-31b80a18 |
| q3-4b | ingested-qwen-3-4b-instruct-2507-tp2 | tuned | 6 | 123.46 | 0.70 | 0.56 | 3.181 | 321.9 | 3981 | 28.0 | 2700 | 273.9 | enabled | 2026.09.17-31b80a18 |
| q3-4b | ingested-qwen-3-4b-instruct-2507-tp2 | tunedplus | 6 | 122.81 | 0.71 | 0.58 | 3.178 | 322.2 | 3978 | 28.0 | 4100 | 278.2 | enabled | 2026.09.17-31b80a18 |
| mixtral | mixtral-8x7b-instruct-v0.1-tp2 | boot | 6 | 33.84 | 0.05 | 0.13 | 6.744 | 152.0 | 2804 | 2.0 | 2700 | 246.5 | disabled | 2026.09.17-31b80a18 |
| mixtral | mixtral-8x7b-instruct-v0.1-tp2 | tuned | 6 | 34.43 | 0.07 | 0.21 | 6.574 | 155.9 | 3980 | 28.0 | 2700 | 294.2 | disabled | 2026.09.17-31b80a18 |
| mixtral | mixtral-8x7b-instruct-v0.1-tp2 | tunedplus | 6 | 34.44 | 0.07 | 0.19 | 6.575 | 155.9 | 3979 | 28.0 | 4094 | 297.7 | disabled | 2026.09.17-31b80a18 |
| q25-32b | qwen-2.5-32b-it-fast-tp2 | boot | 6 | 30.34 | 0.03 | 0.09 | 18.289 | 56.0 | 2802 | 2.0 | 2700 | 262.4 | disabled | 2026.09.17-31b80a18 |
| q25-32b | qwen-2.5-32b-it-fast-tp2 | tuned | 6 | 31.12 | 0.02 | 0.06 | 18.259 | 56.1 | 3960 | 28.0 | 2700 | 314.2 | disabled | 2026.09.17-31b80a18 |
| q25-32b | qwen-2.5-32b-it-fast-tp2 | tunedplus | 6 | 31.16 | 0.03 | 0.09 | 18.256 | 56.1 | 3960 | 28.0 | 4007 | 317.8 | disabled | 2026.09.17-31b80a18 |

Paired deltas (same repetition, same cell, runs back to back): B minus A in % of A. t = mean / (sd / sqrt(n)) of the per-repetition % deltas; 95% CI = mean +/- t(0.975, n-1) x sd / sqrt(n); an interval that excludes 0 is p < 0.05 two-sided (n = 6 pairs: |t| > 2.571; n = 5: |t| > 2.776). idle = the longest wait between the two runs of a pair (second run's start minus first run's log time); FLAG marks pairs that were not back to back.

| cell | comparison (B vs A) | n pairs | TPS delta % mean +/- 95% CI | sd | t | TTFT delta % mean (negative = faster) | pkg1 W delta mean | max idle between the pair's runs (s) |
|---|---|---|---|---|---|---|---|---|
| l8b | tuned vs boot | 6 | +12.93 +/- 0.55 | 0.52 | 60.9 | -4.67 | 60.2 | 66 |
| l8b | tunedplus vs boot | 6 | +13.09 +/- 0.69 | 0.66 | 48.8 | -4.44 | 66.0 | 67 |
| l8b | tunedplus vs tuned | 6 | +0.15 +/- 1.01 | 0.96 | 0.4 | 0.24 | 5.8 | 71 |
| q3-4b | tuned vs boot | 6 | +4.03 +/- 1.09 | 1.03 | 9.5 | -4.83 | 48.5 | 62 |
| q3-4b | tunedplus vs boot | 6 | +3.48 +/- 1.17 | 1.11 | 7.7 | -4.92 | 52.8 | 62 |
| q3-4b | tunedplus vs tuned | 6 | -0.53 +/- 0.41 | 0.39 | -3.3 | -0.09 | 4.2 | 66 |
| mixtral | tuned vs boot | 6 | +1.75 +/- 0.22 | 0.21 | 20.7 | -2.51 | 47.7 | 90 |
| mixtral | tunedplus vs boot | 6 | +1.78 +/- 0.30 | 0.28 | 15.5 | -2.50 | 51.2 | 90 |
| mixtral | tunedplus vs tuned | 6 | +0.03 +/- 0.31 | 0.30 | 0.2 | 0.00 | 3.5 | 94 |
| q25-32b | tuned vs boot | 6 | +2.57 +/- 0.10 | 0.10 | 65.6 | -0.16 | 51.8 | 104 |
| q25-32b | tunedplus vs boot | 6 | +2.71 +/- 0.04 | 0.04 | 156.6 | -0.18 | 55.4 | 104 |
| q25-32b | tunedplus vs tuned | 6 | +0.13 +/- 0.11 | 0.10 | 3.2 | -0.02 | 3.6 | 111 |
