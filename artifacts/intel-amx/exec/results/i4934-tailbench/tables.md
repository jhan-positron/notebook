# tail_bench results

# tail_bench reader_cpu=72 writer_cpu=90 tsc_ghz=2.7000 iters_hot=20000 iters_cold=3000
# tail_bench reader_cpu=72 writer_cpu=90 tsc_ghz=2.7000 iters_hot=20000 iters_cold=3000

Correctness (max relative error of every arm against a double-precision reference, all n):

| arm | kv_mul | run | max rel err |
|---|---|---|---|
| dotter | 4 | tail_bench-run1.csv | 1.073e-06 |
| dotter | 4 | tail_bench-run2.csv | 1.073e-06 |
| dotter | 8 | tail_bench-run1.csv | 1.132e-06 |
| dotter | 8 | tail_bench-run2.csv | 1.132e-06 |
| reader | 4 | tail_bench-run1.csv | 6.855e-07 |
| reader | 4 | tail_bench-run2.csv | 6.855e-07 |
| reader | 8 | tail_bench-run1.csv | 8.537e-07 |
| reader | 8 | tail_bench-run2.csv | 8.537e-07 |
| rowbat | 4 | tail_bench-run1.csv | 1.073e-06 |
| rowbat | 4 | tail_bench-run2.csv | 1.073e-06 |
| rowbat | 8 | tail_bench-run1.csv | 1.132e-06 |
| rowbat | 8 | tail_bench-run2.csv | 1.132e-06 |
| tmpblk | 4 | tail_bench-run1.csv | 6.855e-07 |
| tmpblk | 4 | tail_bench-run2.csv | 6.855e-07 |
| tmpblk | 8 | tail_bench-run1.csv | 8.537e-07 |
| tmpblk | 8 | tail_bench-run2.csv | 8.537e-07 |
| xpose | 4 | tail_bench-run1.csv | 6.855e-07 |
| xpose | 4 | tail_bench-run2.csv | 6.855e-07 |
| xpose | 8 | tail_bench-run1.csv | 8.537e-07 |
| xpose | 8 | tail_bench-run2.csv | 8.537e-07 |

## scenario hot, kv_mul 4: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 53 | 293 | 52 | 330 | 390 | -240 | 1 % |
| 2 | 75 | 293 | 75 | 330 | 390 | -218 | 1 % |
| 3 | 95 | 293 | 94 | 330 | 390 | -198 | 1 % |
| 4 | 115 | 293 | 114 | 330 | 390 | -178 | 1 % |
| 5 | 135 | 293 | 134 | 330 | 391 | -158 | 1 % |
| 6 | 155 | 293 | 154 | 330 | 391 | -137 | 2 % |
| 7 | 176 | 293 | 173 | 330 | 390 | -117 | 2 % |
| 8 | 196 | 293 | 193 | 330 | 390 | -97 | 1 % |
| 9 | 216 | 293 | 213 | 330 | 391 | -77 | 1 % |
| 10 | 236 | 293 | 233 | 330 | 390 | -57 | 1 % |
| 11 | 256 | 293 | 253 | 331 | 389 | -36 | 2 % |
| 12 | 276 | 293 | 273 | 330 | 391 | -16 | 2 % |
| 13 | 296 | 293 | 293 | 331 | 390 | +4 | 2 % |
| 14 | 317 | 293 | 312 | 331 | 390 | +24 | 2 % |
| 15 | 336 | 293 | 332 | 330 | 391 | +43 | 1 % |

Per-step conversion (kv_mul 4): mean over n of dotter 195 ns, reader 293 ns, difference -97 ns per visit. x 57.6 tail visits per worker per step = -5.6 us per step, against the measured gap of 156 us (1.1 % of 14195 us).

Fastest row-major arm in this scenario: rowbat (193 ns mean over n, -100 ns vs reader, -2 ns vs dotter).

## scenario hot, kv_mul 8: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 77 | 429 | 78 | 518 | 522 | -352 | 0 % |
| 2 | 115 | 429 | 117 | 519 | 522 | -313 | 1 % |
| 3 | 156 | 429 | 156 | 518 | 522 | -272 | 1 % |
| 4 | 194 | 429 | 195 | 519 | 522 | -234 | 1 % |
| 5 | 236 | 429 | 235 | 520 | 523 | -193 | 1 % |
| 6 | 274 | 429 | 273 | 519 | 522 | -154 | 1 % |
| 7 | 315 | 429 | 313 | 519 | 522 | -113 | 1 % |
| 8 | 354 | 429 | 352 | 520 | 523 | -75 | 1 % |
| 9 | 394 | 429 | 392 | 519 | 525 | -34 | 1 % |
| 10 | 433 | 429 | 430 | 521 | 525 | +4 | 1 % |
| 11 | 474 | 429 | 470 | 520 | 524 | +46 | 1 % |
| 12 | 513 | 429 | 509 | 522 | 525 | +85 | 1 % |
| 13 | 553 | 429 | 548 | 520 | 525 | +125 | 1 % |
| 14 | 592 | 429 | 587 | 522 | 524 | +164 | 1 % |
| 15 | 633 | 429 | 626 | 520 | 525 | +204 | 1 % |

## scenario step, kv_mul 4: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 262 | 997 | 260 | 839 | 1046 | -735 | 30 % |
| 2 | 269 | 997 | 267 | 828 | 1022 | -728 | 36 % |
| 3 | 357 | 997 | 357 | 827 | 1022 | -641 | 36 % |
| 4 | 444 | 997 | 444 | 826 | 1022 | -552 | 36 % |
| 5 | 581 | 994 | 580 | 842 | 1054 | -413 | 29 % |
| 6 | 598 | 996 | 599 | 834 | 1026 | -398 | 35 % |
| 7 | 617 | 996 | 617 | 843 | 1031 | -380 | 34 % |
| 8 | 636 | 997 | 637 | 854 | 1036 | -361 | 33 % |
| 9 | 764 | 1001 | 759 | 863 | 1064 | -237 | 29 % |
| 10 | 839 | 1000 | 834 | 883 | 1088 | -162 | 26 % |
| 11 | 844 | 1000 | 838 | 892 | 1100 | -156 | 24 % |
| 12 | 873 | 997 | 870 | 912 | 1122 | -123 | 20 % |
| 13 | 959 | 1001 | 951 | 922 | 1120 | -42 | 21 % |
| 14 | 963 | 1000 | 954 | 919 | 1157 | -38 | 14 % |
| 15 | 973 | 1000 | 964 | 934 | 1171 | -27 | 12 % |

Per-step conversion (kv_mul 4): mean over n of dotter 665 ns, reader 998 ns, difference -333 ns per visit. x 57.6 tail visits per worker per step = -19.2 us per step, against the measured gap of 156 us (1.1 % of 14195 us).

Fastest row-major arm in this scenario: rowbat (662 ns mean over n, -336 ns vs reader, -3 ns vs dotter).

## scenario step, kv_mul 8: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 343 | 1549 | 350 | 1025 | 1232 | -1206 | 27 % |
| 2 | 447 | 1547 | 459 | 1017 | 1211 | -1100 | 30 % |
| 3 | 600 | 1550 | 604 | 1016 | 1207 | -950 | 31 % |
| 4 | 640 | 1547 | 643 | 1014 | 1211 | -907 | 30 % |
| 5 | 819 | 1549 | 816 | 1041 | 1242 | -730 | 25 % |
| 6 | 780 | 1549 | 778 | 1036 | 1212 | -769 | 30 % |
| 7 | 814 | 1548 | 812 | 1038 | 1215 | -734 | 30 % |
| 8 | 854 | 1552 | 853 | 1044 | 1219 | -697 | 29 % |
| 9 | 991 | 1549 | 993 | 1056 | 1236 | -558 | 28 % |
| 10 | 1069 | 1547 | 1071 | 1100 | 1260 | -478 | 24 % |
| 11 | 1075 | 1537 | 1076 | 1267 | 1270 | -462 | 29 % |
| 12 | 1112 | 1529 | 1107 | 1283 | 1296 | -416 | 27 % |
| 13 | 1254 | 1532 | 1246 | 1282 | 1300 | -277 | 27 % |
| 14 | 1268 | 1553 | 1260 | 1302 | 1339 | -285 | 24 % |
| 15 | 1293 | 1531 | 1284 | 1327 | 1427 | -238 | 21 % |

## scenario alldirty, kv_mul 4: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 206 | 1568 | 206 | 492 | 544 | -1362 | 4 % |
| 2 | 295 | 1568 | 303 | 492 | 524 | -1273 | 4 % |
| 3 | 317 | 1568 | 319 | 499 | 531 | -1251 | 4 % |
| 4 | 368 | 1568 | 354 | 523 | 573 | -1200 | 4 % |
| 5 | 569 | 1568 | 544 | 700 | 637 | -999 | 43 % |
| 6 | 537 | 1568 | 537 | 723 | 661 | -1032 | 40 % |
| 7 | 563 | 1568 | 550 | 752 | 671 | -1006 | 38 % |
| 8 | 669 | 1568 | 644 | 789 | 695 | -899 | 38 % |
| 9 | 791 | 1568 | 750 | 863 | 703 | -777 | 21 % |
| 10 | 789 | 1568 | 794 | 976 | 766 | -780 | 11 % |
| 11 | 893 | 1568 | 858 | 1027 | 805 | -675 | 12 % |
| 12 | 955 | 1568 | 928 | 1129 | 865 | -613 | 4 % |
| 13 | 1172 | 1568 | 1105 | 1146 | 890 | -397 | 16 % |
| 14 | 1150 | 1568 | 1101 | 1209 | 924 | -418 | 7 % |
| 15 | 1201 | 1568 | 1174 | 1280 | 977 | -367 | 10 % |

Per-step conversion (kv_mul 4): mean over n of dotter 698 ns, reader 1568 ns, difference -870 ns per visit. x 57.6 tail visits per worker per step = -50.1 us per step, against the measured gap of 156 us (1.1 % of 14195 us).

Fastest row-major arm in this scenario: rowbat (678 ns mean over n, -890 ns vs reader, -21 ns vs dotter).

## scenario alldirty, kv_mul 8: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 228 | 2042 | 224 | 641 | 671 | -1814 | 15 % |
| 2 | 367 | 2038 | 353 | 641 | 639 | -1670 | 4 % |
| 3 | 387 | 2039 | 364 | 646 | 672 | -1653 | 4 % |
| 4 | 428 | 2039 | 411 | 667 | 711 | -1611 | 4 % |
| 5 | 765 | 2040 | 725 | 810 | 807 | -1274 | 30 % |
| 6 | 669 | 2039 | 696 | 883 | 823 | -1370 | 37 % |
| 7 | 775 | 2039 | 728 | 909 | 848 | -1264 | 36 % |
| 8 | 818 | 2039 | 773 | 947 | 850 | -1221 | 35 % |
| 9 | 1106 | 2039 | 1041 | 1037 | 867 | -933 | 18 % |
| 10 | 1040 | 2039 | 1040 | 1146 | 926 | -999 | 9 % |
| 11 | 1179 | 2039 | 1106 | 1191 | 956 | -860 | 5 % |
| 12 | 1290 | 2039 | 1217 | 1316 | 1016 | -749 | 5 % |
| 13 | 1633 | 2039 | 1541 | 1351 | 1043 | -406 | 11 % |
| 14 | 1559 | 2039 | 1472 | 1408 | 1079 | -480 | 7 % |
| 15 | 1684 | 2039 | 1579 | 1460 | 1149 | -354 | 8 % |

## scenario flush, kv_mul 4: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 319 | 1867 | 300 | 684 | 643 | -1548 | 15 % |
| 2 | 398 | 1864 | 401 | 710 | 670 | -1466 | 5 % |
| 3 | 440 | 1877 | 372 | 727 | 714 | -1437 | 24 % |
| 4 | 497 | 1864 | 487 | 745 | 733 | -1367 | 15 % |
| 5 | 623 | 1871 | 613 | 1023 | 822 | -1248 | 16 % |
| 6 | 649 | 1873 | 651 | 1037 | 861 | -1223 | 18 % |
| 7 | 745 | 1866 | 720 | 1050 | 889 | -1121 | 17 % |
| 8 | 822 | 1864 | 808 | 1110 | 920 | -1043 | 26 % |
| 9 | 926 | 1874 | 901 | 1259 | 928 | -948 | 8 % |
| 10 | 957 | 1873 | 936 | 1347 | 1073 | -916 | 10 % |
| 11 | 1095 | 1870 | 1043 | 1449 | 1130 | -776 | 10 % |
| 12 | 1253 | 1876 | 1111 | 1603 | 1215 | -623 | 12 % |
| 13 | 1370 | 1873 | 1316 | 1789 | 1257 | -503 | 14 % |
| 14 | 1403 | 1877 | 1317 | 1861 | 1297 | -474 | 7 % |
| 15 | 1503 | 1870 | 1412 | 1914 | 1368 | -367 | 5 % |

Per-step conversion (kv_mul 4): mean over n of dotter 867 ns, reader 1871 ns, difference -1004 ns per visit. x 57.6 tail visits per worker per step = -57.8 us per step, against the measured gap of 156 us (1.1 % of 14195 us).

Fastest row-major arm in this scenario: rowbat (826 ns mean over n, -1045 ns vs reader, -41 ns vs dotter).

## scenario flush, kv_mul 8: median ns per visit (median over 2 runs)

| n | dotter | reader | rowbat | xpose | tmpblk | dotter - reader | run spread (max over arms) |
|---|---|---|---|---|---|---|---|
| 1 | 323 | 2322 | 330 | 873 | 857 | -1999 | 16 % |
| 2 | 468 | 2331 | 443 | 932 | 850 | -1863 | 6 % |
| 3 | 592 | 2321 | 533 | 922 | 930 | -1729 | 9 % |
| 4 | 636 | 2320 | 608 | 927 | 926 | -1684 | 5 % |
| 5 | 907 | 2321 | 838 | 1191 | 980 | -1414 | 18 % |
| 6 | 937 | 2319 | 889 | 1276 | 1001 | -1382 | 24 % |
| 7 | 1059 | 2320 | 958 | 1290 | 1027 | -1260 | 22 % |
| 8 | 1127 | 2320 | 1004 | 1298 | 1077 | -1193 | 23 % |
| 9 | 1312 | 2321 | 1273 | 1471 | 1118 | -1009 | 6 % |
| 10 | 1365 | 2322 | 1329 | 1542 | 1220 | -957 | 8 % |
| 11 | 1526 | 2319 | 1409 | 1664 | 1298 | -793 | 9 % |
| 12 | 1591 | 2322 | 1524 | 1862 | 1383 | -731 | 6 % |
| 13 | 1916 | 2321 | 1915 | 1896 | 1426 | -406 | 6 % |
| 14 | 1916 | 2323 | 1897 | 1916 | 1475 | -407 | 6 % |
| 15 | 1928 | 2327 | 1915 | 1917 | 1519 | -400 | 6 % |

