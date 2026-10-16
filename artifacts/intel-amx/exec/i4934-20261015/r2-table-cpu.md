| Cell | Pair | TPS per user (sd) | TPS difference (band) | Verdict | t | TTFT s (sd) | TTFT difference ms (band) | Verdict |
|---|---|---|---|---|---|---|---|---|
| tp2, 8 users, prompt 1,024 | `fixoff` vs `headoff` | 75.00 (0.09) vs 75.84 (0.15) | -0.84 (-1.1 %, band 0.40) | beyond | -8.0 | 3.861 (0.002) vs 3.856 (0.005) | +5 (band 150) | inside |
| tp2, 8 users, prompt 1,024 | `fix` vs `new` | 86.12 (0.21) vs 85.16 (0.12) | +0.96 (+1.1 %, band 0.42) | better | +7.6 | 3.077 (0.006) vs 3.092 (0.005) | -14 (band 150) | inside |
| tp2, 8 users, prompt 8,192 | `fixoff` vs `headoff` | 15.30 (0.08) vs 15.42 (0.01) | -0.12 (-0.8 %, band 0.40) | inside | -2.7 | 117.609 (0.292) vs 117.381 (0.139) | +228 (band 584) | inside |
| tp2, 8 users, prompt 8,192 | `fix` vs `new` | 19.02 (0.02) vs 18.95 (0.04) | +0.06 (+0.3 %, band 0.40) | inside | +3.2 | 51.547 (0.057) vs 51.619 (0.094) | -72 (band 188) | inside |
| tp4, 8 users, prompt 1,024 | `fixoff` vs `headoff` | 111.64 (0.08) vs 111.18 (1.14) | +0.46 (+0.4 %, band 2.28) | inside | +0.7 | 2.404 (0.003) vs 2.396 (0.013) | +8 (band 150) | inside |
| tp4, 8 users, prompt 1,024 | `fix` vs `new` | 122.36 (0.60) vs 120.83 (0.74) | +1.53 (+1.3 %, band 1.48) | better | +2.1 | 2.119 (0.005) vs 2.133 (0.002) | -14 (band 150) | inside |
