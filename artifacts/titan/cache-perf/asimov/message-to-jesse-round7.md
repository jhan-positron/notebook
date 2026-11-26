# Draft to Jesse (round seven: run 8, the mesh latency map)

Not sent. The code is pushed: commit 3b12e4f on main of jhan-positron/asimov.

The next run measures a latency map of the mesh: one load from each of CPUs 2 to 9 to each of the
five home nodes (88, 160, 216, 288, 344), for OCM lines and for DRAM-backed lines held in that node's
cache slice. The files so far give the OCM cells from CPUs 2, 4, 6 and 8 only. Their 2 MiB chain is a
mean over the five slices (23.9 ns on boot B), since a DRAM line's home node is a hash of its address.

The new program `meshmap` finds each line's node with the mesh counters: it flushes and loads one
line 64 times and sees which node's `hns_pocq_reqs_recvd_all` rose. Then it times each node's lines
alone. It is on cache-mem-perf at commit `3b12e4f`, built by `make`. The script is `run_map.sh`.

Two asks, in this order.

**1. A rehearsal, with its files back before the full run is queued.** One command on CPU 2, about
0.06 s est. of chip time, on boot B's firmware (SCP 0.48.0-nopcie.1, TF-A 0.35.0-pfoff.1) if that is
convenient. Any firmware works: the home node of a line does not depend on the L3 or the prefetchers.

    ./meshmap --cpus 2 --lines 64 --reps 1 --out map-rehearsal.csv --homes map-rehearsal-homes.txt > map-rehearsal-log.txt 2>&1

Not under cmncount: `meshmap` opens the mesh counters itself and uses all eight. Files to return:
the three above and dmesg.

The reason: the counter code has run only against a stand-in. Three things in it are new on this image.

- Five per-node events opened as one perf group. cmncount opens each event alone.
- The group read while it counts, from CPU 2, with the PMU on CPU 0. cmncount stops the events first.
- The count per flush-and-load pair on a DRAM-backed line. It is known for OCM lines only.

What the files answer:

- `# mesh counters: level=`: 1 is one group with three sums, 2 the five per-node events as a group,
  3 the five opened alone. The program steps down by itself.
- `# probe line= ns= d=`: the five raw counts of the first 32 probes, and the time of one probe.
  The time sets the classification time of the full run.
- `# read_floor:`: the counts that one empty read adds.
- `# pagemap:` and `# one_2mib_page:`: whether the buffer's frame number is readable and whether the
  buffer is one 2 MiB page. With both I can check Arm's hash formula against the measured homes.
- 20 rows of 64 loads. I expect 22 to 27 ns for the OCM and `slc` rows and about 53 ns for
  `dram-flush`. They check the path. They are not numbers to quote.

**2. The full run:** `sh run_map.sh`, one `--out` directory per boot, about 0.92 s est. of chip time
(5 commands; 160 cells of 7 passes of 2,048 loads). A classification that runs to its time stop
makes it about 2.8 s est. Boots, in this order:

1. **L3 off, prefetchers off**: boot B's firmware. The clean reference. It repeats the 20 known OCM cells.
2. **L3 on, prefetchers off**: boot F2's firmware (SCP 0.48.0-nopcie-l3.1, TF-A 0.35.0-pfoff.1). No
   core row exists in this state.
3. **Optional, L3 on, prefetchers on**: boot F1's firmware. It shows the prefetchers' effect. It is
   not a distance map.

With boot B's readbacks in the README (IMP_CPUECTLR_EL1 bit 48, IMP_CMECFG_EL1 bit 28,
IMP_CLUSTERPWRSTAT_EL1). I would like boot 1's files before boot 2 is queued, so one defect cannot
repeat on every boot.

What cannot cost the boot: a counter or classification failure prints a `#` line, skips the rows
that depend on it, and the rest runs. The OCM cells run first and need no counter. Every row is
flushed to the file when it is written. The program stops its classification at 2 chip seconds.

What `run_map.sh` does: it brings CPU 3 online (CPUs 2 to 9 all stay online), writes
`sysinfo-map.txt`, runs four `latency` control rows, then one `meshmap` command that writes
`latency-map.csv` and `map-homes.txt`. It exits 1 when a requested cell is missing or a write failed.

One question. The script has an option `--kernel-cpus`, off by default, that also measures from
CPU 0 in a last block (about 0.09 s est. more). CPU 0's cluster sits at crosspoint (1,2), a fifth
position on the mesh, and adds two cells at five steps. Your boot E note says a hang on CPU 0 or 1
could take the boot down, so I leave it off unless you say it is safe.

Tested: x86 host and the CRB (aarch64, default flags, no warnings; self-test 47 of 47). Not tested:
the mesh counter path on real counters, and `/dev/ocm` through `meshmap` (it ran against a file).

No hurry on the queue; nothing here launches or changes the platform on my side.
