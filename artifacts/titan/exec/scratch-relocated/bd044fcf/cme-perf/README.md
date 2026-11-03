# isa: CME cycles per instruction class

`cme_perf isa` times the instruction classes of the GDN il block (`../gdn/kernel/gdn_cme_il.c`) on the
CME, one CPU at a time. It tells where the il block's cycles go: issue cost per class, latency exposed
between dependent instructions, and whether the CME takes more than one instruction per cycle.

## Method

- `gen_isa.py` writes `isa_tests.inc`: one streaming function per test (`__arm_locally_streaming
  __arm_new("za")`), whose loop holds 32 instructions (30 for `feed3`) in exactly the il block's forms.
  The prologue sets the predicates and slice registers, zeroes ZA and loads z0-z31 from the buffer (two
  4 KiB pages of FP16 1.0; `st1h_x2b` also sets x17 to the second page).
- The bench runs each test at `--n1` (4) and `--n2` (132) loop iterations, `--reps` (9) times each after
  a warmup, and reads the CME PMU group of `decode` around each call. With the median CME cycles c1, c2:
  cycles per iteration = (c2 - c1) / (n2 - n1); per instruction = that / 32; per group = per instruction
  × group size; IPC = 32 / cycles per iteration. The call, the prologue and SMSTART/SMSTOP cancel. The
  loop's `subs` and `b.ne` are inside the difference: two scalar instructions per 32.
- Each `CME,isa` record also gives the time of each pass from `cntvct_el0`: `t0_us` (the test's start,
  from the row's first test), `us_n1` and `us_n2` (warmup, reps and PMU reads), and `CME,r` the ticks of
  each timed rep at n2 (`tk_n2`). `CME,isaend` gives `us_row`. So a row's time outside the timed calls
  shows per test. The UART (480000 baud, about 48 kB/s) sets the pace of a row, so the records leave out
  what the header, the rep lists or `gen_isa.py` give (n1, n2, reps, ops, min, max, cycles per iteration).
- An `--ev` row (`isa-ev-*`, after all the timed rows) runs instead, per test, a pass at n2 that counts,
  with a second PMU group, where the CME cycles go: front-end stall because
  the core sent nothing (`CME_STALL_FRONTEND_CPU` 0x324B), the core's stall while the CME waits for it
  (`STALL_BACKEND_BUSY_CME_CPUBOUND` 0x3203), the DP0/DP1/load issue-queue dispatch stalls
  (0x325D-0x325F) and the ALU, MAC, permute, store, MMDP and MMMV issue counts (0x3260-0x3265). Only an
  `--ev` row opens this group (a timed row has only the `decode` group, as the decode rows have); it is
  enabled for each test's pass only. `full=1` says it counted for the whole pass; `us_ev` is the pass's
  time. GA13 run 4001 had the group open in the timed rows and took about 0.12 s of chip time per test
  against about 1 ms of timed calls; the split keeps the timed rows apart from it.
- Values are FP16 1.0 reinterpreted by the forms that read FP32; the timing of these forms is not
  expected to depend on the values.

## Tests

`gen_isa.py --list`. Throughput tests rotate destinations, ZA offsets (`fdot` 0-7, `fmlal` 0:1-6:7) or
tiles (`fmopa` za0-za3), so no instruction waits for another. Latency chains reuse one destination or ZA
group. Pairs: the consumer reads the producer's result (`_dep`) or an unrelated register (`_ind`);
`_dep - _ind` per pair is the exposed producer latency. Feed tests mix independent classes in groups of
2, 3 or 4. `st1h_x2b` is `st1h_x2` with the stores alternating between two pages: it shows whether
`st1h_x2`'s cost (and its reps' spread) comes from storing to the same lines again.

## Checks

`make O=<dir> test`: `isa_tests.inc` is what `gen_isa.py` writes, and `count_isa.py` finds exactly the
generated instructions, in order, in every compiled loop (and SMSTART/SMSTOP in every function).
`../bench` `make test` checks the arithmetic (`isa_calc.h`).
