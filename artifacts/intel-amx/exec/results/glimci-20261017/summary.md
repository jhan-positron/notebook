# glimci-20261017 summary

Nightly reference (run 38999609242, 2026-10-17): TPS per user 78.69 (sd 0.48 over 80 samples), TTFT 3697 ms (sd 188), prefill proxy 277.0 tok/s

| pass | status | TPS per user mean (sd) | TTFT ms mean (sd) | prefill proxy tok/s | prompt tokens (server usage) mean [min-max] | journal prompt tokens mean (n) | journal prefill s mean (n) | AMX busy cycles (20 s probe) | requests per engine | binary ok | HW attn unset ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| amxoff-pass1 | ok | 78.42 (0.62) | 3772 (191) | 271.5 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| amxoff-pass2 | ok | 78.88 (0.47) | 3784 (191) | 270.6 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| amxoff-pass3 | ok | 78.49 (0.52) | 3787 (194) | 270.4 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| amxon-pass1 | ok | 82.59 (0.43) | 3644 (202) | 281.0 | 992 [925-1023] | - (0) | - (0) | 5,556,008,472 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| amxon-pass2 | ok | 82.08 (1.08) | 3662 (184) | 279.6 | 992 [925-1023] | - (0) | - (0) | 5,516,600,600 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| amxon-pass3 | ok | 82.13 (0.59) | 3648 (196) | 280.7 | 992 [925-1023] | - (0) | - (0) | 5,543,678,624 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| base-pass1 | ok | 78.80 (0.56) | 3796 (195) | 269.8 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| base-pass2 | ok | 78.55 (1.97) | 3777 (186) | 271.1 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |
| base-pass3 | ok | 78.71 (0.51) | 3768 (186) | 271.8 | 992 [925-1023] | - (0) | - (0) | 0 | {'0': 40, '1': 40, '2': None, '3': None} | True | True |

## Arms (mean over passes)

| arm | passes | TPS per user | sd over passes | TTFT ms | prefill proxy tok/s | vs nightly TPS | vs nightly TTFT |
|---|---|---|---|---|---|---|---|
| base | 3 | 78.69 | 0.13 | 3780 | 270.9 | +0.0 % | +2.3 % |
| amxoff | 3 | 78.60 | 0.25 | 3781 | 270.8 | -0.1 % | +2.3 % |
| amxon | 3 | 82.27 | 0.28 | 3651 | 280.5 | +4.6 % | -1.2 % |

## Differences

- base -> amxoff: TPS 78.69 -> 78.60 (-0.1 %), TTFT 3780 -> 3781 ms (+0.0 %), paired t over 3 passes = -0.4
- amxoff -> amxon: TPS 78.60 -> 82.27 (+4.7 %), TTFT 3781 -> 3651 ms (-3.4 %), paired t over 3 passes = 13.1
- base -> amxon: TPS 78.69 -> 82.27 (+4.6 %), TTFT 3780 -> 3651 ms (-3.4 %), paired t over 3 passes = 33.1
