# issue4500 trace analysis

Per trace, mean over decode passes (n_token_jobs <= 8): pass ms; Save K / Save V sums on main (us); wait_coop_gof (us); gof_rodeo count and sum by thread class; Attention Pending / Ready max per worker (us); hw wait max (us).

| trace | passes | burst | pass ms | SaveK us | SaveV us | SaveV end->pass end us | coop us | rodeo n (main/worker) | rodeo us (main/worker) | populate n | populate us | Pending max/worker us | Ready max/worker us | hw wait max us | launch us |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| m3__base__tp2__8u__catA.perfetto-trace | 38 | all | 8.404 | 173 | 190 | 624 | 17 | 2/66 | 14/1600 | -+- | -+- | 308 | 352 | 985 | 1362 |
| m3__base__tp2__8u__catA.perfetto-trace | 9 | burst | 8.716 | 170 | 113 | 670 | 65 | 8/280 | 60/6757 | -+- | -+- | 291 | 220 | 1132 | 1434 |
| m3__base__tp2__8u__catA.perfetto-trace | 29 | quiet | 8.307 | 174 | 214 | 610 | 2 | -/- | -/- | -+- | -+- | 313 | 393 | 940 | 1340 |
| m3__base__tp2__8u__catB.perfetto-trace | 38 | all | 8.626 | 178 | 189 | 627 | 22 | 1/67 | 21/3069 | 1+67 | 10+1246 | 337 | 249 | 958 | 1291 |
| m3__base__tp2__8u__catB.perfetto-trace | 9 | burst | 10.246 | 188 | 125 | 711 | 91 | 5/283 | 87/12956 | 5+283 | 42+5262 | 400 | 311 | 1075 | 1373 |
| m3__base__tp2__8u__catB.perfetto-trace | 29 | quiet | 8.123 | 175 | 209 | 600 | 1 | -/- | -/- | -+- | -+- | 317 | 230 | 921 | 1265 |
| m3__base__tp4__8u__catA.perfetto-trace | 38 | all | 8.775 | 198 | 181 | 1281 | 88 | 2/66 | 80/1495 | -+- | -+- | 535 | 277 | 384 | 1397 |
| m3__base__tp4__8u__catA.perfetto-trace | 9 | burst | 9.038 | 216 | 122 | 1443 | 357 | 8/280 | 339/6313 | -+- | -+- | 411 | 298 | 362 | 1420 |
| m3__base__tp4__8u__catA.perfetto-trace | 29 | quiet | 8.693 | 193 | 199 | 1229 | 5 | -/- | -/- | -+- | -+- | 574 | 270 | 391 | 1389 |
| m3__base__tp4__8u__catB.perfetto-trace | 38 | all | 9.117 | 189 | 180 | 1199 | 51 | 1/67 | 42/2884 | 1+67 | 18+1114 | 609 | 285 | 349 | 1336 |
| m3__base__tp4__8u__catB.perfetto-trace | 9 | burst | 10.194 | 208 | 120 | 1148 | 190 | 5/283 | 178/12176 | 5+283 | 74+4704 | 473 | 313 | 411 | 1352 |
| m3__base__tp4__8u__catB.perfetto-trace | 29 | quiet | 8.783 | 183 | 198 | 1215 | 8 | -/- | -/- | -+- | -+- | 652 | 277 | 329 | 1330 |
| m3__headoff__tp2__2u__catA.perfetto-trace | 38 | all | 5.061 | 59 | 71 | 473 | 5 | 0/17 | 5/168 | -+- | -+- | 201 | 177 | 626 | 56 |
| m3__headoff__tp2__2u__catA.perfetto-trace | 9 | burst | 5.213 | 57 | 45 | 501 | 21 | 2/70 | 19/710 | -+- | -+- | 204 | 186 | 626 | 67 |
| m3__headoff__tp2__2u__catA.perfetto-trace | 29 | quiet | 5.013 | 60 | 79 | 464 | 1 | -/- | -/- | -+- | -+- | 200 | 174 | 625 | 53 |
| m3__headoff__tp2__8u__catA.perfetto-trace | 38 | all | 8.428 | 164 | 187 | 615 | 14 | 2/67 | 12/1614 | -+- | -+- | 337 | 230 | 1015 | 1461 |
| m3__headoff__tp2__8u__catA.perfetto-trace | 9 | burst | 8.645 | 153 | 110 | 643 | 55 | 7/281 | 52/6816 | -+- | -+- | 318 | 228 | 1144 | 1460 |
| m3__headoff__tp2__8u__catA.perfetto-trace | 29 | quiet | 8.361 | 167 | 212 | 607 | 1 | -/- | -/- | -+- | -+- | 343 | 230 | 975 | 1461 |
| m3__headoff__tp2__8u__catB.perfetto-trace | 38 | all | 8.721 | 172 | 187 | 664 | 17 | 1/67 | 16/3261 | 1+67 | 8+1350 | 419 | 255 | 905 | 1333 |
| m3__headoff__tp2__8u__catB.perfetto-trace | 9 | burst | 10.285 | 197 | 115 | 765 | 69 | 4/284 | 67/13769 | 4+284 | 32+5700 | 409 | 347 | 1032 | 1400 |
| m3__headoff__tp2__8u__catB.perfetto-trace | 29 | quiet | 8.236 | 164 | 209 | 631 | 1 | -/- | -/- | -+- | -+- | 422 | 227 | 866 | 1313 |
| m3__headoff__tp4__8u__catA.perfetto-trace | 38 | all | 8.734 | 193 | 183 | 1125 | 139 | 2/66 | 130/1478 | -+- | -+- | 540 | 281 | 351 | 1496 |
| m3__headoff__tp4__8u__catA.perfetto-trace | 9 | burst | 8.971 | 193 | 122 | 1391 | 566 | 8/280 | 548/6239 | -+- | -+- | 422 | 277 | 369 | 1476 |
| m3__headoff__tp4__8u__catA.perfetto-trace | 29 | quiet | 8.660 | 193 | 201 | 1042 | 6 | -/- | -/- | -+- | -+- | 577 | 282 | 346 | 1502 |
| m3__headoff__tp4__8u__catB.perfetto-trace | 38 | all | 8.882 | 174 | 179 | 1028 | 43 | 1/67 | 39/2650 | 1+67 | 21+1091 | 511 | 287 | 323 | 1428 |
| m3__headoff__tp4__8u__catB.perfetto-trace | 9 | burst | 10.040 | 169 | 127 | 992 | 169 | 6/282 | 164/11189 | 6+282 | 87+4605 | 480 | 354 | 410 | 1240 |
| m3__headoff__tp4__8u__catB.perfetto-trace | 29 | quiet | 8.523 | 175 | 195 | 1039 | 4 | -/- | -/- | -+- | -+- | 520 | 266 | 296 | 1486 |
| m3__vnni__tp2__2u__catA.perfetto-trace | 38 | all | 5.262 | 210 | 68 | 477 | 6 | 0/17 | 5/210 | -+- | -+- | 313 | 143 | 609 | 62 |
| m3__vnni__tp2__2u__catA.perfetto-trace | 9 | burst | 5.290 | 178 | 52 | 492 | 24 | 2/70 | 22/885 | -+- | -+- | 307 | 149 | 601 | 64 |
| m3__vnni__tp2__2u__catA.perfetto-trace | 29 | quiet | 5.253 | 219 | 72 | 473 | 1 | -/- | -/- | -+- | -+- | 315 | 141 | 611 | 62 |
| m3__vnni__tp2__8u__catA.perfetto-trace | 38 | all | 9.064 | 730 | 167 | 630 | 22 | 2/66 | 20/1850 | -+- | -+- | 742 | 365 | 392 | 1397 |
| m3__vnni__tp2__8u__catA.perfetto-trace | 9 | burst | 8.965 | 616 | 117 | 669 | 91 | 8/280 | 85/7811 | -+- | -+- | 736 | 241 | 455 | 1530 |
| m3__vnni__tp2__8u__catA.perfetto-trace | 29 | quiet | 9.095 | 765 | 183 | 617 | 1 | -/- | -/- | -+- | -+- | 744 | 403 | 373 | 1356 |
| m3__vnni__tp2__8u__catB.perfetto-trace | 38 | all | 9.030 | 717 | 164 | 649 | 30 | 2/67 | 28/3003 | 2+67 | 15+1246 | 741 | 269 | 442 | 1443 |
| m3__vnni__tp2__8u__catB.perfetto-trace | 9 | burst | 10.122 | 645 | 129 | 745 | 126 | 6/282 | 118/12680 | 6+282 | 63+5261 | 767 | 355 | 541 | 1477 |
| m3__vnni__tp2__8u__catB.perfetto-trace | 29 | quiet | 8.691 | 739 | 175 | 618 | 1 | -/- | -/- | -+- | -+- | 733 | 242 | 412 | 1432 |
| m3__vnni__tp4__8u__catA.perfetto-trace | 38 | all | 9.771 | 755 | 172 | 1445 | 53 | 2/66 | 47/1651 | -+- | -+- | 914 | 257 | 264 | 1335 |
| m3__vnni__tp4__8u__catA.perfetto-trace | 9 | burst | 9.807 | 640 | 118 | 1459 | 210 | 8/280 | 198/6973 | -+- | -+- | 770 | 251 | 236 | 1384 |
| m3__vnni__tp4__8u__catA.perfetto-trace | 29 | quiet | 9.760 | 791 | 189 | 1440 | 5 | -/- | -/- | -+- | -+- | 958 | 258 | 272 | 1320 |
| m3__vnni__tp4__8u__catB.perfetto-trace | 38 | all | 9.676 | 749 | 168 | 1218 | 95 | 1/67 | 85/3004 | 1+67 | 40+1357 | 871 | 362 | 304 | 1313 |
| m3__vnni__tp4__8u__catB.perfetto-trace | 9 | burst | 10.948 | 655 | 122 | 1477 | 381 | 5/283 | 360/12684 | 5+283 | 167+5731 | 824 | 324 | 348 | 1407 |
| m3__vnni__tp4__8u__catB.perfetto-trace | 29 | quiet | 9.281 | 779 | 183 | 1135 | 6 | -/- | -/- | -+- | -+- | 885 | 373 | 290 | 1284 |
| prefill-only__m3__base__tp2__8u__catA.perfetto-trace | 0 | all | - | - | - | - | - | -/- | -/- | -+- | -+- | - | - | - | - |
| prefill-only__m3__base__tp2__8u__catA.perfetto-trace | 0 | burst | - | - | - | - | - | -/- | -/- | -+- | -+- | - | - | - | - |
| prefill-only__m3__base__tp2__8u__catA.perfetto-trace | 0 | quiet | - | - | - | - | - | -/- | -/- | -+- | -+- | - | - | - | - |
