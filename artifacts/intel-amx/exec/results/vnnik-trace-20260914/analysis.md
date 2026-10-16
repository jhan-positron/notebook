# vnnik-trace analysis

Per trace and pass kind: mean over passes. Rows = tokens x 8 KV heads. Busy fractions: share of threads with a span overlapping the Save K window (0 = idle).

## prefill

| trace | passes | pass ms | Save K ms/pass | Save K us/layer | ns/row | Save V ms/pass | Save V us/layer | K share % | K+V share % | workers busy | helpers busy | gap after Save V us |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-tp2.perfetto-trace | 8 | 392.7 | 9.85 | 273.6 | 33.4 | 10.63 | 295.1 | 2.51 | 5.21 | 0.850 | 0.073 | 285.6 |
| base-tp4.perfetto-trace | 8 | 274.0 | 10.13 | 281.3 | 34.3 | 10.63 | 295.3 | 3.70 | 7.58 | 0.665 | 0.003 | 6.5 |
| vnni-tp2.perfetto-trace | 8 | 402.4 | 30.94 | 859.4 | 104.9 | 11.84 | 328.9 | 7.69 | 10.63 | 0.850 | 0.060 | 65.6 |
| vnni-tp4.perfetto-trace | 8 | 294.3 | 31.02 | 861.7 | 105.2 | 11.78 | 327.2 | 10.54 | 14.54 | 0.681 | 0.009 | 0.6 |

## decode

| trace | passes | pass ms | Save K ms/pass | Save K us/layer | ns/row | Save V ms/pass | Save V us/layer | K share % | K+V share % | workers busy | helpers busy | gap after Save V us |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-tp2.perfetto-trace | 8 | 13.6 | 0.17 | 4.6 | 72.2 | 0.20 | 5.6 | 1.22 | 2.69 | 0.996 | 0.003 | 109.8 |
| base-tp4.perfetto-trace | 8 | 10.9 | 0.21 | 5.8 | 90.9 | 0.26 | 7.1 | 1.92 | 4.27 | 0.992 | 0.000 | 34.0 |
| vnni-tp2.perfetto-trace | 8 | 12.7 | 1.02 | 28.4 | 444.5 | 0.18 | 4.9 | 8.05 | 9.44 | 1.000 | 0.000 | 71.8 |
| vnni-tp4.perfetto-trace | 8 | 10.8 | 1.24 | 34.5 | 539.8 | 0.22 | 6.1 | 11.55 | 13.59 | 1.000 | 0.000 | 5.0 |

## threads

- base-tp2.perfetto-trace: main 1, attention workers 20, main helpers 7, passes 16
- base-tp4.perfetto-trace: main 1, attention workers 47, main helpers 8, passes 16
- vnni-tp2.perfetto-trace: main 1, attention workers 20, main helpers 7, passes 16
- vnni-tp4.perfetto-trace: main 1, attention workers 47, main helpers 8, passes 16
