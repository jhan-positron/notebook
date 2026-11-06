# Draft to Bill (replaces the two earlier drafts; all five boots are in)

Bill, the follow-up boots are back, so here are answers to your points with data.

Words used here: "chase" is a dependent-load chain (each load's address comes from the previous
load, so no prefetcher can run ahead). "L3 on" means boot E, where Jesse rebuilt the SCP firmware so
the L3 of each cluster is a working cache; "L3 off" means every run before it.

1. The L3 and the 42 % L2 hit rate. The L3 of the cores we measure (CPUs 2-9) was not a cache in any
   earlier run. The SCP firmware puts the whole L3 in snoop-filter-only mode for every cluster except
   the one with CPUs 0-1 (asimov-scp-firmware, mod_asimov_system.c, "tracked as a follow-up"), and the
   cluster power-status register read 0x0 on those runs. So the 192-384 KiB rows were L2 hits mixed
   with reads from the SLC, with no L3 level between. A 192 KiB footprint in a 128 KiB L2 keeps about
   half its lines in the L2: measured 0.51-0.54 L2 hits per load, the rest came from outside the
   cluster. Jesse then rebuilt the SCP (boot E): the register reads 0x70 (all slices, full RAM), the
   L3 hits per load read 0.47, 0.75 and 0.92 at 192, 256 and 384 KiB, and the chase at those sizes
   fell from 14.1, 19.7 and 22.7 ns to 7.8, 9.5 and 10.9 ns. From the 384 KiB row (92 % L3 hits) the
   L3 hit costs about 11 ns est., about 22 core cycles est. Nothing below 128 KiB moved (within 1.4 %).

2. One-core DRAM read at 9.2 GB/s. That rate was with the L3 off. With the L3 on, the same program
   on the same core reads 24.9 GB/s at 2 MiB and 24.5 GB/s at 32 MiB (2.7 times). The cause is not in
   the counters yet: the refill counts per line are about the same on both boots, so the L3 does not
   serve the lines; it changes how far ahead the fills run. The hardware prefetcher is the mechanism
   either way: with the prefetchers off the plain read falls to 5.0 GB/s at 2 MiB and 2.4 GB/s at
   32 MiB, and software prefetch 4 lines ahead brings it back to 12.1 and 6.3 GB/s. With the hardware
   prefetchers on and the L3 on, the software prefetch lowers the rate (20.2-20.4 GB/s), so it does not
   add to the hardware prefetcher. So "a software mechanism" was half right: the rate is set by how
   many lines are in flight, and on this chip that is the hardware prefetcher plus the L3 behind it.
   Which part of the DSU makes the L3 case faster: Insufficient data; the measurement that would
   settle it is a read row with the L3 hit set counted (the program rejects that combination today).

3. The 52 ns DRAM latency. It is a model, and the number is two legs. The home-node hop is 24 ns
   (the 2 MiB SLC row, which the L3 did not move: 24.18 vs 24.05 ns). The memory leg is about 29 ns:
   with the prefetchers off, a chain walked in address order through 8 MiB takes 52.76 ns per load,
   the same as a random chain (52.74). Real LPDDR5X would give a row-buffer hit on the address-order
   walk and a miss on the random one, so a fixed delay behind the home node is the only reading that
   fits. With the L3 on the 8 MiB chase and the flushed 8 MiB row did not move (45.08 vs 45.13,
   52.66 vs 52.66 ns). So 52 ns is what the emulator's memory model is set to, not a DRAM
   measurement, and I keep those rows labelled "emulator memory model" and do not compare them with
   the CRB.

4. One-core L1 read at 58 GB/s against a 64 GB/s path. The gap is a fixed time per pass of the
   test program, not the L1's rate. Words: a pass is one read of the whole buffer. A rep is a timed
   group of passes. TRM is Arm's Technical Reference Manual for the core. CRB is the Arm reference
   server we compare against, and V3AE is its Neoverse V3AE core.
   I added rows at 4, 8, 16 and 24 KiB in two forms. The looped form makes one kernel call per pass.
   The single-call form keeps all passes of a rep inside one assembly call. The single-call form reads 59.8
   to 60.6 GB/s at 16 and 24 KiB (boots C and E). The 16 KiB pass takes about 130 ns longer than the
   8 KiB pass (single-call form, boot E). That difference is the time of the added 8 KiB alone. Those
   bytes move at 62.8 to 64.8 GB/s (derived from the difference, every form and boot), which is the
   64 GB/s dual 128-bit read path within 1.2 %. So each row falls short of 64 GB/s by a fixed time per
   pass. The write rows fit the line time per pass = fixed cost + bytes / rate. The rate is 31.9 to
   32.1 GB/s, the 128-bit write path exactly. The fixed cost is 24 to 26 ns per pass in the looped form
   and 9 to 14 ns in the single-call form. I accept such a fit only when every row is within 2 % of the
   line. The read rows miss that (2.1 to 5.4 %), so I quote no single per-pass cost for reads.
   Instead, the time above the 64 GB/s ideal is 13 to 16 ns per pass in the single-call form and 25 to
   37 ns in the looped form, at 4 to 16 KiB on both boots. The C1-Nano is an in-order core. Its TRM
   (r0p2, section 1.1) lists an "in-order pipeline with direct and indirect branch prediction". In an
   in-order core the work at a pass boundary (loop exit, return, register save and restore, the next
   call) must finish before the next pass's first load can issue. For comparison, the CRB's V3AE is
   out of order. On the same program it adds 4.2 ns per pass in the looped form and reads the same rate
   in both forms, so it overlaps most of that work with the loads.

The pages with the figures follow once the boot E rows are in them.
