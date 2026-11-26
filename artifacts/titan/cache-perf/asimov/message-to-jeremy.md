Draft reply to Jeremy (2026-11-10). Not sent.

The cap fix is in my image, but it does not cover the memory I measured. The image is not older than the fix.

- I assume you mean Thuan's PR #4492 (the DDR timing model for the emulator's memory lanes), announced in #emulation on 2026-10-23. Please correct me if you mean a different change.
- My image is release a10280100, built from RTL commit 0d9e214 (2026-10-28). That commit is 129 commits after PR #4492, so it contains the fix.
- PR #4492 adds 61 ns read latency, 40 ns write response and a 38.4 GB/s cap per lane. It applies them only to the 32 datapath lanes, which hold the weight memory (XMS).
- The Arm cores' system DRAM (SMS) uses 4 other lanes, which the code calls AUX lanes. The PR text says: "AUX and unindexed FC instances retain native behavior". The timing doc says: "The four AUX lanes retain native zero-delay startup".
- My latency data agrees. A random read that misses every cache costs 52.7 ns for the whole path (core, mesh, memory and back). The profile alone would add at least 61 ns at the memory. So the profile is not active on the system DRAM.
- This also explains what I reported. The system DRAM model has no configured delay and no row or bank timing. A read in address order costs the same as a read in random order (52.76 ns against 52.74 ns, prefetchers off).
- The main branch today (commit 32019a3) has the same lane condition. A newer release exists (a11040933, 2026-11-05), and I have not run it. I expect the same system DRAM behavior there (inferred from the code, not measured).
- The exclusion is deliberate in the code: the PR states it, and a test fails if the AUX latency changes. The reason is not written in the PR or the doc. I will ask Thuan whether the system DRAM should get a profile.
- I have no sourced figure for what the real system DRAM should deliver. Do you know who owns that spec?

References
- PR #4492, Positron-AI-TSMC/asimov, merged 2026-10-24 06:20 UTC (2026-10-23 evening Pacific).
- emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv:641-643, 687-689 at 0d9e214: `.DATAPATH_TIMING (GC_PAIR_INDEX >= 0 && GC_PAIR_INDEX < 16)`; lines 118-119: read latency 61, write response 40, else 0.
- emu/hemi_tlm/doc/GC_DDR_TIMING.md:70-80, 86-87 at 0d9e214.
- design/xms/packages/xms_pkg.sv:84-86 at 0d9e214: 16 datapath pairs, 2 AUX pairs.
- results/membench-jibin-006 (boot B): 8 MiB flushed chain, address order 52.762 ns, random 52.739 ns.
