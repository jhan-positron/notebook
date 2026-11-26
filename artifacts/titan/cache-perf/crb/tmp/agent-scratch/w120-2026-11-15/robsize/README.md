# robsize

## Short version

`robsize` measures how many instructions of one kind fit in the out-of-order
window of one AArch64 core. It times a loop with two independent cache
misses and N filler instructions after each miss. The N where the time per
iteration steps from about one miss time to about two miss times is the
capacity for that filler kind.

Status: built with gcc 14.2.0 and run on the CRB (the Arm server, Neoverse
V3AE core) on 2026-11-15. The result files are in `results/`.

## Words used here

- Out-of-order window: the instructions a core holds between fetch and
  retirement. Its size is limited by the reorder buffer (ROB), by the free
  physical registers, and by the load queue.
- Filler: an instruction placed between the two cache-missing loads. It
  does not depend on those loads.
- Chain: a buffer of pointers that form one random cycle. Reading
  `p = *p` gives one cache miss per step.
- Template: an instruction assembled at build time, whose 4-byte word the
  program copies into the generated loop.

## Method

Henry Wong, "Measuring Reorder Buffer Capacity" (2013).

```
loop:
    ldr  x0, [x0]        ; load A, cache miss, chain A
    <N filler units>
    ldr  x1, [x1]        ; load B, cache miss, chain B
    <N filler units>
    sub  x2, x2, #1
    cbnz x2, loop
```

- N small: both misses are in the window together. One iteration costs
  about one miss time.
- N larger than the capacity: load B enters the window only after load A
  retires. One iteration costs about two miss times.

The loop is generated at run time, so N can be any value. No instruction
is encoded by hand. The assembler encodes every instruction in the
`__asm__` template block of `robsize.c`, and the program copies the words.
The only run-time change is the offset field of the `cbnz` loop branch.
The program checks that patch against an assembler-encoded `cbnz` at start
and stops if the two words differ.

## Filler kinds and default N lists

| kind      | one unit of N                              | limit it measures                        | default N         |
|-----------|--------------------------------------------|------------------------------------------|-------------------|
| `nop`     | `nop`                                      | reorder-buffer entries                   | 0..1200 step 10   |
| `vadd`    | `add vA.2d, vA.2d, v0.2d`, A = 16..31      | free vector physical registers           | 0..600 step 5     |
| `iadd`    | `add xA, xA, x3`, A = 4..17                | free integer physical registers          | 0..1200 step 10   |
| `ldrq`    | `ldr q16, [x3]`                            | load-queue entries or vector registers   | 0..600 step 5     |
| `ldpq`    | `ldp q16, q17, [x3]`                       | same, 2 vector register writes each      | 0..300 step 2     |
| `iter256` | 8 x `ldp q(2k), q(2k+1), [x3, #32k]`       | benchmark iterations (256 B = 4 lines)   | 0..60 step 1      |
| `vadd_nd` | `add vA.2d, v0.2d, v1.2d`, A = 16..31      | control for `vadd`, no dependency chain  | 0..600 step 5     |
| `iadd_nd` | `add xA, x3, x3`, A = 4..17                | control for `iadd`, no dependency chain  | 0..1200 step 10   |

`x3` points to a 256 B scratch buffer that stays in the L1 cache.

### Kernel-body kinds (added 2026-11-15, run k1 to k3)

One unit of N is one loop body of a benchmark kernel of `bwx12.c`, in the
instruction order of that kernel. Default N list: 0 to a maximum per kind,
step 1.

| kind                 | one unit of N                                              | bytes per unit |
|----------------------|------------------------------------------------------------|----------------|
| `k_nopN`             | 8 x `ldp q`, N `nop`, loop end. N = 32 to 256 (13 values)  | 256            |
| `k_dadd2/4/8/16`     | 8 x `ldp q`, 2/4/8/16 adds of loaded registers, loop end   | 256            |
| `k_iadd16`           | 8 x `ldp q`, 16 adds of v24-v31 (no loaded register)       | 256            |
| `k_old`              | `ldp`, `add x6`, 3 x `ldp`, pointer add, 8 adds, cmp, b.lo | 128            |
| `k_spN`              | 4 x `ldp q`, N `nop`, loop end. N = 9, 24, 32, 40, 48, 56  | 128            |
| `k_1pl`              | 4 x `ldr q` (one per 64 B line), loop end                  | 256            |
| `k_1pl_nop96`        | `k_1pl` with 96 `nop` before the loop end                  | 256            |
| `k_pf2048`           | 8 x `ldp q`, 4 x `prfm pldl1keep`, loop end                | 256            |

Differences from the benchmark kernels:

- "Loop end" is `add x4, x4, #bytes; cmp x4, x5; b.lo next`. The branch goes
  to the next instruction. It is never taken, because the prologue sets
  x4 = x5 = 0. In the benchmark the branch is taken.
- All loads and prefetches read the hot scratch buffer `[x3]`. They hit L1
  and do not depend on the pointer add.
- The accumulators v16 to v31 are not initialized.

`--kind` accepts a list of names with commas. `go.sh TAG` runs the calls of
`TAG.spec`. `go.sh build` only builds.

`vadd_nd` and `iadd_nd` were not in the request. They are added as controls.
In `vadd`, each accumulator receives N/8 adds per iteration. If one NEON add
takes 2 cycles (est., not measured on this core), that is N/4 cycles per
iteration. At N = 1200 this is 300 cycles (est.), which can exceed one miss
time. The `_nd` kinds write the same registers but read only registers that
are never written, so they have no such chain.

## Run

```
./run_rob.sh                                  # all kinds, CPU 2
./run_rob.sh --kind nop --nmin 300 --nmax 420 --nstep 1   # refine one step
```

`run_rob.sh` builds with `gcc -O2`, records the load average, and writes
`rob-<UTC time>.csv` in this folder.

Options of `robsize`: `--cpu C` (required, CPUs above 119 are refused),
`--kind NAME|all`, `--nmin`, `--nmax`, `--nstep`, `--reps` (default 5,
minimum 5), `--iters` (default 200000, minimum 200000), `--mb` (MiB per
chain, default 1024), `--stride` (bytes between pointers, default 64).

Memory use: 2 chains of 1 GiB each. The program is single-threaded.

## Output

CSV on stdout. Lines that start with `#` are comments.

```
kind,N,filler_instrs_per_block,median_ns,min_ns,hot_ns
```

- `median_ns`, `min_ns`: nanoseconds per iteration over the repetitions,
  with the two cache-missing loads.
- `hot_ns`: the same generated code with both loads reading a cell that
  stays in L1 (minimum of 3 repetitions). It is the cost of the fillers
  alone.

After each kind, two `# step` lines give the step position:

- `N_at_midpoint`: the N where the series first crosses the midpoint
  between the low plateau (mean of the first 3 points) and the high
  plateau (mean of the last 3 points), with linear interpolation.
- `largest_rise`: the pair of neighbouring N values with the largest
  increase. This estimate does not depend on the plateaus.
- The first line uses `median_ns`. The second line uses
  `median_ns - hot_ns`, which removes most of the slope that the filler
  cost adds at large N.

## Limits of the method

- The window between load B and the next load A also holds `sub` and
  `cbnz`. The capacity is about the step N plus 2 to 3 instructions.
- With the default step of 10, the step position is known to within 10.
  Refine with `--nstep 1`.
- A core may store several nops in one ROB entry. The `nop` result is then
  "nops that fit", which can be larger than the number of ROB entries.
- If the `# AnonHugePages` line shows a warning, the chains are not on
  2 MiB pages. Page-table walks then add to every miss.
- At large N the filler cost itself (`hot_ns`) can approach one miss time.
  Read the step from the CSV, not only from the summary lines.
- The step line prints a warning when the high plateau is below 1.4 times
  the low plateau. The step is then outside the N range.

## Check the encodings

On the target: `objdump -d robsize`, then search for `t_prologue`,
`t_nop`, `t_vadd`, `t_iadd`, `t_ldrq`, `t_ldpq`, `t_iter256`. The
disassembly shows each template word next to its assembly text.
