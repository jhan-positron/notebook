# attnstats-20260924 summary (attention path stats: base/base2 = main binary 66c7bb8db1 with the switch unset (same-binary control pair), head = branch binary with TRON_ATTN_STATS unset (off-state cost), headon = branch binary with TRON_ATTN_STATS=1 (on-state cost), headkill = headon + TRON_AMX_DISABLE=1 (kill-switch cross-check); attn = cpu)

Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).

| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q3-4b-tp2-1u-p1000-it1 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headon2 | 1 | 227.19 | 0.00 | 0.402 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1000-it3 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headon2 | 0 | - | - | 0.400 | 0.000 | 1 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1000-it3 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headkill2 | 0 | - | - | 0.397 | 0.000 | 1 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p1000-it1 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 1 | 125.50 | 0.00 | 3.154 | 0.000 | 0 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-8u-p1000-it3 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 8 | headon2 | 0 | - | - | 3.144 | 0.000 | 1 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1024-it3 | fpga | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headon2 | 0 | - | - | 0.403 | 0.000 | 1 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1000-it3 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headon2 | 0 | - | - | 0.413 | 0.000 | 1 | 0.0 | cbf1bb6c0c |
| q3-4b-tp2-1u-p1000-it3 | cpu | ingested-qwen-3-4b-instruct-2507-tp2 | 2 | 1 | headkill2 | 0 | - | - | 0.517 | 0.000 | 1 | 0.0 | cbf1bb6c0c |

| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |
|---|---|---|---|---|---|---|---|

Excluded rt attempts (failed or stopped): 0

Failed or stopped smoke attempts: 0

Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): 6
- ### runtron kind=rt cell=q3-4b-tp2-1u-p1000-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=1 attn=fpga prompt=1000 len=256 arm=headon2 armenv=[TRON_ATTN_STATS=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T13:44:29Z load=52.22 97.70 98.76 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253] tokens over 3 completion lines
- ### runtron kind=rt cell=q3-4b-tp2-8u-p1000-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=8 attn=fpga prompt=1000 len=256 arm=headon2 armenv=[TRON_ATTN_STATS=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T13:45:52Z load=16.13 74.62 90.51 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253] tokens over 24 completion lines
- ### runtron kind=rt cell=q3-4b-tp2-1u-p1024-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=1 attn=fpga prompt=1024 len=256 arm=headon2 armenv=[TRON_ATTN_STATS=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T13:46:40Z load=13.80 65.75 86.75 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253] tokens over 3 completion lines
- ### runtron kind=rt cell=q3-4b-tp2-1u-p1000-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=1 attn=fpga prompt=1000 len=256 arm=headkill2 armenv=[TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T14:00:02Z load=94.35 111.92 102.02 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253] tokens over 3 completion lines
- ### runtron kind=rt cell=q3-4b-tp2-1u-p1000-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=1 attn=cpu prompt=1000 len=256 arm=headkill2 armenv=[TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T14:00:43Z load=46.89 96.87 97.39 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253] tokens over 3 completion lines
- ### runtron kind=rt cell=q3-4b-tp2-1u-p1000-it3 model=ingested-qwen-3-4b-instruct-2507-tp2 tp=2 users=1 attn=cpu prompt=1000 len=256 arm=headon2 armenv=[TRON_ATTN_STATS=1] rep=1 attempt=1 bin=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2 tip=cbf1bb6c0c 2026-09-25T14:01:24Z load=26.73 85.38 93.50 hugepages_free=512 bill_procs=0 bill_cpu_pct=0 marker=present -> generated [253, 253, 253] tokens over 3 completion lines

Duplicate complete records of one repetition (second and later ignored): 0

