# issue4500 block m6: CI-layout cells (rinzler + the nightly client on our half)

| tp | users/engine | arm | n | TPS mean | TPS sd (reps) | step ms | TTFT ms | AMX-busy cycles (20 s) |
|---|---|---|---|---|---|---|---|---|
| 2 | 2 | base | 2 | 192.21 | 3.86 | 5.203 | 762 | 0/0 |
| 2 | 2 | baseminb1 | 2 | 207.01 | 2.08 | 4.831 | 760 | 0/0 |
| 2 | 2 | target | 2 | 183.88 | 1.10 | 5.438 | 700 | 1239423880/1239445732 |
| 2 | 2 | targetkill | 2 | 184.50 | 0.39 | 5.420 | 762 | 0/0 |
| 2 | 2 | targetminb1 | 2 | 204.18 | 0.19 | 4.898 | 700 | 583532564/583529068 |
| 4 | 4 | base | 2 | 156.33 | 5.18 | 6.397 | 848 | 0/0 |
| 4 | 4 | target | 2 | 135.37 | 7.30 | 7.387 | 809 | 892942088/1762677112 |
| 4 | 4 | targetkill | 2 | 144.62 | 4.17 | 6.915 | 814 | 0/0 |

## Paired (a minus b, per repetition; step ms = 1000/TPS)

| tp | users | a | b | n | delta ms/step | delta TPS % | paired t (12.71 at n=2, 4.30 at n=3) |
|---|---|---|---|---|---|---|---|
| 2 | 2 | baseminb1 | base | 2 | -0.373 (sd 0.056) | +7.70 | -9.40 |
| 2 | 2 | target | base | 2 | +0.235 (sd 0.137) | -4.33 | +2.42 |
| 2 | 2 | targetkill | base | 2 | +0.216 (sd 0.093) | -4.01 | +3.29 |
| 2 | 2 | targetminb1 | base | 2 | -0.306 (sd 0.109) | +6.23 | -3.97 |
| 2 | 2 | baseminb1 | target | 2 | -0.608 (sd 0.081) | +12.58 | -10.60 |
| 2 | 2 | targetkill | target | 2 | -0.018 (sd 0.044) | +0.34 | -0.59 |
| 2 | 2 | targetminb1 | target | 2 | -0.541 (sd 0.028) | +11.04 | -27.28 |
| 4 | 4 | target | base | 2 | +0.998 (sd 0.611) | -13.41 | +2.31 |
| 4 | 4 | targetkill | base | 2 | +0.517 (sd 0.412) | -7.49 | +1.78 |
| 4 | 4 | targetkill | target | 2 | -0.480 (sd 0.199) | +6.83 | -3.41 |
