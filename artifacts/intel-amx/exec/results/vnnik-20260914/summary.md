# vnnik-20260914 summary

Per cell: mean over repetitions (sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (8 prompts).

## tp2

| prompt | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs |
|---|---|---|---|---|---|---|---|
| 1024 | off | 3 | 70.28 | 0.05 | 3.938 | 0.007 | 0 |
| 1024 | base | 3 | 79.59 | 0.43 | 3.151 | 0.008 | 0 |
| 1024 | vnni | 3 | 84.44 | 0.19 | 3.221 | 0.007 | 0 |
| 1024 | vnnioff | 3 | 73.93 | 0.07 | 3.935 | 0.005 | 0 |
| 2048 | off | 3 | 45.62 | 0.07 | 11.077 | 0.004 | 0 |
| 2048 | base | 3 | 52.76 | 0.06 | 7.272 | 0.027 | 0 |
| 2048 | vnni | 3 | 56.53 | 0.03 | 7.271 | 0.015 | 0 |
| 2048 | vnnioff | 3 | 47.31 | 0.13 | 10.926 | 0.017 | 0 |
| 8192 | off | 3 | 14.75 | 0.02 | 121.679 | 0.066 | 0 |
| 8192 | base | 3 | 17.29 | 0.01 | 53.284 | 0.080 | 0 |
| 8192 | vnni | 3 | 19.09 | 0.01 | 52.344 | 0.149 | 0 |
| 8192 | vnnioff | 3 | 15.37 | 0.03 | 118.812 | 0.176 | 0 |

| prompt | comparison | TPS delta % | TTFT delta % (time; negative = faster) |
|---|---|---|---|
| 1024 | vnni vs base | +6.1 | +2.2 |
| 1024 | base vs off | +13.2 | -20.0 |
| 1024 | vnnioff vs off | +5.2 | -0.1 |
| 1024 | vnni vs off | +20.2 | -18.2 |
| 1024 | vnni vs vnnioff | +14.2 | -18.1 |
| 2048 | vnni vs base | +7.1 | -0.0 |
| 2048 | base vs off | +15.6 | -34.4 |
| 2048 | vnnioff vs off | +3.7 | -1.4 |
| 2048 | vnni vs off | +23.9 | -34.4 |
| 2048 | vnni vs vnnioff | +19.5 | -33.5 |
| 8192 | vnni vs base | +10.4 | -1.8 |
| 8192 | base vs off | +17.2 | -56.2 |
| 8192 | vnnioff vs off | +4.2 | -2.4 |
| 8192 | vnni vs off | +29.4 | -57.0 |
| 8192 | vnni vs vnnioff | +24.2 | -55.9 |

## tp4

| prompt | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs |
|---|---|---|---|---|---|---|---|
| 1024 | off | 2 | 96.45 | 2.41 | 2.457 | 0.027 | 0 |
| 1024 | base | 2 | 106.41 | 1.90 | 2.187 | 0.005 | 0 |
| 1024 | vnni | 2 | 105.47 | 1.06 | 2.358 | 0.000 | 0 |
| 1024 | vnnioff | 2 | 94.91 | 2.13 | 2.533 | 0.011 | 0 |
| 2048 | off | 2 | 71.90 | 2.36 | 6.505 | 0.001 | 0 |
| 2048 | base | 2 | 78.05 | 1.48 | 4.706 | 0.003 | 0 |
| 2048 | vnni | 2 | 81.00 | 1.12 | 4.935 | 0.001 | 0 |
| 2048 | vnnioff | 2 | 77.02 | 0.04 | 6.483 | 0.009 | 0 |
| 8192 | off | 2 | 26.49 | 0.15 | 64.651 | 0.070 | 0 |
| 8192 | base | 2 | 30.99 | 0.06 | 30.516 | 0.078 | 0 |
| 8192 | vnni | 2 | 33.06 | 0.61 | 30.180 | 0.003 | 0 |
| 8192 | vnnioff | 2 | 27.65 | 0.41 | 63.170 | 0.072 | 0 |

| prompt | comparison | TPS delta % | TTFT delta % (time; negative = faster) |
|---|---|---|---|
| 1024 | vnni vs base | -0.9 | +7.8 |
| 1024 | base vs off | +10.3 | -11.0 |
| 1024 | vnnioff vs off | -1.6 | +3.1 |
| 1024 | vnni vs off | +9.3 | -4.0 |
| 1024 | vnni vs vnnioff | +11.1 | -6.9 |
| 2048 | vnni vs base | +3.8 | +4.9 |
| 2048 | base vs off | +8.6 | -27.7 |
| 2048 | vnnioff vs off | +7.1 | -0.3 |
| 2048 | vnni vs off | +12.7 | -24.1 |
| 2048 | vnni vs vnnioff | +5.2 | -23.9 |
| 8192 | vnni vs base | +6.7 | -1.1 |
| 8192 | base vs off | +17.0 | -52.8 |
| 8192 | vnnioff vs off | +4.4 | -2.3 |
| 8192 | vnni vs off | +24.8 | -53.3 |
| 8192 | vnni vs vnnioff | +19.5 | -52.2 |

