Thanks for the review. Here is where each point stands, from run 3 (the numbers in the brief) and run 4
boot A (the same script again on the same platform, with prefetch counters added; results came in today).
Points 1, 2, 4, 5 and 7 are answered. Point 6 waits for the next boots. Point 4 changed after boot B came in.

1. DRAM 52 ns. The memory is a model, not DRAM. The emulator image is hemi_rtws_tlm ("tlm" means
transaction-level model). asimov-bench measured 53.3 ns on a sibling image and calls it "host-model DRAM".
The 52.7 ns is a true random miss: on boot A the 8 MiB random chain with every line flushed first read
52.74 ns per load, with 1.00 L3 refills per load and 0.00 prefetch refills per load. Of those 52.7 ns, 24.1 ns
is the trip to the home node (the SLC-hit latency), so the memory behind the home node adds only about 28 ns.
That is shorter than one LPDDR5X row cycle, so the model has no row physics. The brief now says the DRAM
rows are not silicon numbers. I will ask Jesse what delay the model is configured with. I agree not to
spend more time on DRAM.

2. "Chase". Removed as a bare term. The brief now says what the test is at first use: each load's address
is the value the previous load returned, so loads cannot overlap. Up to 384 KiB the same list is walked
repeatedly. From 512 KiB a random list is walked once, so the prefetcher cannot predict the addresses.
"Fresh" and "repeat" in the tables are replaced by "walked once" and "walked repeatedly".

4. L3 and the 42 %. Answered, and it is a firmware finding. On CPUs 2 to 9 the DSU L3 has been in
snoop-filter-only mode in every run so far: it holds no data, and every L2 miss goes to the SLC or DRAM.
Jesse found it in boot B (prefetchers off), and I confirmed it three ways: the L3 hit counter reads 0 at
every size from 64 to 512 KiB while every L3 access is a refill; the cluster power-status register reads 0x0
(one slice, snoop filter only) before and after those rows; and the SCP source sets the full-L3 operating
mode for the cluster of CPUs 0 and 1 only, with the other clusters left "as a follow-up"
(asimov-scp-firmware, mod_asimov_system.c). Our run 3 and boot A counters say the same from the refill
side: at 192 KiB, 42 % of loads hit the L2 and the other 46 % of loads that missed went straight to the mesh,
none to the L3. So "14 ns at 192 KiB" was L2 hits mixed with SLC reads, not an L3 latency, and the pages
will drop the L3 level for the measured cores. Jesse offers a boot with the SCP rebuilt to enable the L3 on
those clusters, after boots D and C; I am taking it, so the L3 latency and the 192 to 384 KiB rows get
measured with the L3 on.

5. Asimov against the CRB. Both L1s are 4 cycles. Asimov runs at 2.0 GHz on the emulator (4 KiB chain:
2.002 ns = 4 cycles), the CRB's Neoverse V3AE at 2.8 GHz.

| Level | Asimov C1-Nano | CRB V3AE |
|---|---|---|
| L1 latency | 2.0 ns (4 cycles), 32 KiB | 1.43 ns (4 cycles), 64 KiB |
| L2 latency | 6.1 ns (12 cycles), 128 KiB per 2 cores | 3.75 ns (10.5 cycles), 2 MiB private |
| L3 | 256 KiB per DSU, no clean number (point 4) | none |
| SLC latency | 24.1 ns (48 cycles), 3.75 MiB | 19 to 44 ns by slice, 29 ns average, 128 MiB |
| DRAM latency | 52.7 ns, memory model | 148 ns, DDR5-8000 |
| 1-core read from L1 | 58.1 GB/s | 133 GB/s |
| 1-core read from DRAM | 9.2 GB/s | 30 GB/s |
| 1-core write | 32.0 GB/s | 63 GB/s to DRAM, 73 GB/s to the mesh |
| Chip read from DRAM | 67.8 GB/s (8 cores) | 533 GB/s (120 cores) |
| Chip write to DRAM | 155 GB/s (8 cores) | 447 GB/s (120 cores) |

Per cycle the L1s are the same and the L2s are close. The bandwidth differences are points 6 and 7.

6. One-core DRAM read 9.2 GB/s. Not settled yet. What run 3 says:
- The same core reads 9.3 GB/s from the SLC at 2 MiB and 9.2 GB/s from DRAM at 32 MiB, so the limit
  is not the memory.
- The CME on the same DSU reads 37 GB/s from the same DRAM through the same mesh.
- Eight cores read 67.8 GB/s, about 8.5 GB/s each, so the limit is per core.
- The read loop issues 16 independent 128-bit loads per iteration. At 9.2 GB/s and 52.7 ns that is
  about 7.6 lines in flight per core (est.).
So it is either the core's miss-handling capacity or, as you suggest, the software not getting enough
loads in flight. The next boots run the same read loop with software prefetch 4, 8 and 16 lines ahead,
and a two-stream version, each with the prefetch counters. If none of them moves 9.2 GB/s, the limit is
the core. On writes I agree: 155 GB/s with 8 cores is the mesh and memory limit. It changed from 87 to
89 GB/s to 155 GB/s with a firmware update and not with the code.

7. One-core L1 read 58 GB/s. That is 91 % of the core's own limit. The C1-Nano has two 128-bit load
pipes, 32 bytes per cycle, which is 64 GB/s at 2.0 GHz. The V3AE has three 128-bit load pipes at
2.8 GHz, 134 GB/s, and measures 133 GB/s. The gap is the core design, not the measurement. Two notes:
the 2.0 GHz is the clock the emulator models, and silicon may differ. And the CME path on the same core
reads 105 GB/s at 48 KiB with 512-bit vectors, which is where this design puts its load bandwidth.
