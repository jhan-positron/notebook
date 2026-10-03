# issue4500 trace analysis

Per trace, mean over decode passes (n_token_jobs <= 8): pass ms; Save K / Save V sums on main (us); wait_coop_gof (us); gof_rodeo count and sum by thread class; Attention Pending / Ready max per worker (us); hw wait max (us).

| trace | passes | burst | pass ms | SaveK us | SaveV us | SaveV end->pass end us | coop us | rodeo n (main/worker) | rodeo us (main/worker) | populate n | populate us | Pending max/worker us | Ready max/worker us | hw wait max us | launch us |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base__tp2__2u.perfetto-trace | 38 | all | 5.052 | 58 | 70 | 461 | 5 | 0/17 | 5/174 | -+- | -+- | 218 | 171 | 599 | 59 |
| base__tp2__2u.perfetto-trace | 9 | burst | 5.166 | 51 | 41 | 467 | 21 | 2/70 | 19/736 | -+- | -+- | 209 | 178 | 592 | 62 |
| base__tp2__2u.perfetto-trace | 29 | quiet | 5.017 | 60 | 79 | 459 | 1 | -/- | -/- | -+- | -+- | 220 | 169 | 601 | 58 |
| base__tp4__4u.perfetto-trace | 38 | all | 7.523 | 111 | 112 | 1219 | 86 | 1/33 | 81/446 | -+- | -+- | 433 | 358 | 220 | 1082 |
| base__tp4__4u.perfetto-trace | 9 | burst | 7.886 | 108 | 72 | 1596 | 355 | 4/139 | 342/1885 | -+- | -+- | 382 | 326 | 200 | 1048 |
| base__tp4__4u.perfetto-trace | 29 | quiet | 7.411 | 112 | 125 | 1097 | 2 | -/- | -/- | -+- | -+- | 448 | 369 | 226 | 1092 |
| fixS1__tp2__2u.perfetto-trace | 38 | all | 5.112 | 105 | 70 | 459 | 6 | 0/17 | 5/178 | -+- | -+- | 208 | 141 | 643 | 67 |
| fixS1__tp2__2u.perfetto-trace | 9 | burst | 5.171 | 96 | 44 | 477 | 22 | 2/70 | 20/753 | -+- | -+- | 162 | 134 | 629 | 61 |
| fixS1__tp2__2u.perfetto-trace | 29 | quiet | 5.094 | 107 | 78 | 453 | 1 | -/- | -/- | -+- | -+- | 222 | 143 | 647 | 69 |
| fixS1__tp4__4u.perfetto-trace | 38 | all | 7.377 | 171 | 121 | 1182 | 106 | 1/32 | 101/454 | -+- | -+- | 420 | 329 | 206 | 1019 |
| fixS1__tp4__4u.perfetto-trace | 9 | burst | 7.511 | 142 | 71 | 1410 | 442 | 4/133 | 427/1916 | -+- | -+- | 346 | 242 | 215 | 1076 |
| fixS1__tp4__4u.perfetto-trace | 29 | quiet | 7.336 | 180 | 136 | 1111 | 1 | -/- | -/- | -+- | -+- | 443 | 356 | 203 | 1002 |
| fix__tp2__2u.perfetto-trace | 38 | all | 5.164 | 107 | 70 | 491 | 6 | 0/17 | 5/169 | -+- | -+- | 213 | 172 | 638 | 64 |
| fix__tp2__2u.perfetto-trace | 9 | burst | 5.399 | 98 | 43 | 623 | 23 | 2/70 | 21/715 | -+- | -+- | 208 | 141 | 635 | 68 |
| fix__tp2__2u.perfetto-trace | 29 | quiet | 5.091 | 109 | 78 | 449 | 1 | -/- | -/- | -+- | -+- | 214 | 181 | 639 | 63 |
| fix__tp4__4u.perfetto-trace | 38 | all | 7.651 | 170 | 118 | 1458 | 132 | 1/32 | 127/444 | -+- | -+- | 328 | 278 | 202 | 1070 |
| fix__tp4__4u.perfetto-trace | 9 | burst | 8.453 | 154 | 73 | 2103 | 551 | 4/134 | 535/1875 | -+- | -+- | 299 | 259 | 222 | 1062 |
| fix__tp4__4u.perfetto-trace | 29 | quiet | 7.402 | 175 | 132 | 1251 | 2 | -/- | -/- | -+- | -+- | 336 | 284 | 195 | 1073 |
