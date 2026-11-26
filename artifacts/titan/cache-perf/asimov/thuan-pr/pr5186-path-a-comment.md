## Proposal: measure the timed boot first, then merge with the new run window

### The problem

- The run window is 1.0G cfclks for a release SCP at version 0.51.0 or later.
- That window comes from a boot without AUX timing. Init was reached at 874M to 883M cfclks.
- With AUX timing on, each AP DRAM read takes about 58 more AXI cycles (est., from the PR text). The boot takes longer.
- Nobody has measured how much longer.
- If init falls outside the window, `run_emu.sh` exits with status 1. Every default Linux boot run would then fail.

### Why an estimate is not enough

- The repo holds one transaction count: 1,782,918 reads and 2,867,850 writes. It comes from a full-chip boot in August 2026, with SCP 0.30.0, for both hemispheres together.
- Estimates from that count put init between 926M and 1092M cfclks (est.). These assume that each hemisphere produced half of the traffic.
- So the estimates do not decide whether the boot fits 1.0G. A measurement is needed.

### Steps

1. **Build this PR branch as it is.** The AUX timing is already on. Run `emu/hemi_tlm/scripts/run_emu.sh --build-only`.
2. **Boot Linux with a large window.** Run `emu/hemi_tlm/scripts/run_emu.sh --run-cycles 1600000000 --timelimit 5400`.
3. **Find the cfclk count at which init is reached.** See "How to find the init time" below.
4. **Raise the default run window.** Use the measured count plus margin. The existing windows carry 12.8% margin (debug SCP: 1418M in 1.6G) and 14.4% margin (release SCP: 874M in 1.0G).
5. **Check the wall-clock limits.** They are 3600 s for a plain Linux boot and 5400 s over the PCIe VirtualBridge. Raise them if the longer run does not fit.
6. **Repeat steps 2 to 5 for the debug SCP.** It has its own window of 1.6G cfclks.
7. **Update the comments and docs that quote the old numbers.** See "Where the numbers live" below.
8. **Record the measurement in this PR.** State the init count, the firmware version and the asimov-os snapshot version.

### How to find the init time

The repo does not record how the 874M figure was read from a run. The console log search in `run_emu.sh` reads no time stamp.

- **If you know the method** (for example a time stamp in `uartout/uart_1.log`): use it, and add it to the comment next to the new number.
- **Otherwise, bracket the init time with the run window:**
  1. A run with verdict `BOOTED` gives an upper bound. Its `--run-cycles` value is above the init time.
  2. A run with verdict `INCOMPLETE` gives a lower bound, but only when the run is valid. A valid run reached its window (`Ran until` at N / 2 ns in `emu.log`), shows `=== PRELOAD PASS ===` in `hemi_sys_mem.log`, and its console log ends in a normal kernel boot line.
  3. Get both bounds first. If the 1.6G run boots, lower the window (for example to 1.0G) until a valid run is `INCOMPLETE`. If the 1.6G run is `INCOMPLETE`, raise the window until a run boots.
  4. Then halve the gap with `--run-only --run-cycles N` until the two bounds are closer than about 50M cfclks.
  5. Use the lowest `BOOTED` value as the measured init count.

### Where the numbers live

- **Set the new window in `emu/hemi_tlm/scripts/run_emu.sh` only**, after the helper call near line 613. The helper is shared with `cmn_tlm` and `fc_tlm`. Those two do not get AUX timing, so their windows must stay.
- **Keep the helper call line as it is.** `emu/common/tests/test_boot_firmware_selection.py` checks that the line exists in all three launchers. It also checks the helper's return values (1000000000 and 1600000000).
- **Update these texts**, which quote 1.0G, 874M or 0.44 s:
  - the usage header of `emu/hemi_tlm/scripts/run_emu.sh` (near lines 55 to 70);
  - the comment above the helper call (near lines 610 to 613);
  - the comment in `emu/hemi_tlm/scripts/run_emu.hemi_tlm.sh` (near lines 15 to 18).

### If no emulator time is available soon

There is a second option: put the AUX timing behind a build define that is off by default, merge, and turn it on in a later PR after the measurement. I have a patch for that, with unit tests. It has not been compiled or run on the emulator. It adds code that is removed again later, so I prefer the steps above.
