---
name: crb-memory-module-count-varies-per-boot
description: "CRB sometimes boots with 10 of 12 memory modules (329 GB instead of 395 GB); whole-chip read rates differ a lot between the two states, so check the module count before comparing runs"
metadata:
  node_type: memory
  type: project
  originSessionId: 4a6b911c-1987-43f1-be61-e96fcfc7261d
  modified: 2026-11-17T04:21:22.155Z
---

CRB (firmware 0.7.2) does not always bring up all 12 memory modules (32 GB each, DDR5 at 8000 MT/s). A boot shows either 12 modules (MemTotal about 395 GB) or 10 modules (about 329 GB, one module missing per half). Check with `grep MemTotal /proc/meminfo` or `sudo dmesg | grep "DIMM sockets"`.

Boot history from the journal and from 2026-11-17: 2026-10-20 = 12; 2026-10-22 to 2026-11-07 = 10; 2026-11-09 to 2026-11-17 03:44 UTC = 12; then four warm reboots on 2026-11-17 gave 10, 10, 12, 10. The count did not follow the firmware setting under test. Cause not known.

Effect on the read benchmark (bwx12, 64+56 threads, runs of 2026-11-17): old read loop 467-468 GB/s with 12 modules, 360-362 GB/s with 10; load-only loop 299-300 against 260-287; read_nop256 548 against 506-514. One half alone (64+0 or 0+56) and one thread are the same in both states.

**Why:** any comparison of a run from 2026-10-22..11-07 with a run from 2026-11-09..11-17 mixes the two states. The state after 2026-11-17 04:17 UTC was 10 modules.

**How to apply:** record the module count with every CRB performance run. A reboot can change it, so a reboot on this shared machine has a side effect for all users. On 2026-11-17 an automated "reboot until 12 modules" loop was denied by the permission system; more reboots need the user's explicit approval.

Related: [[crb-whole-chip-read-drop-2026-11-15]], [[arm-welcome-kit-crb-resources]]. The firmware "CPU TXREQ Throttle" test of 2026-11-17 (TXREQ Min 1/4, then TXREQ Max 1/4 and Min 1/4) changed no read rate by more than about 3 %, also not for one thread; settings were set back and the full list verified equal to the original. Results: `crb/results/w120-X1d10*`, `w120-X2d12*`, `w120-BASEd10*`, `fwtest-20261117/`.

Added 2026-11-17 06:40 UTC (read-only checks, folder `crb/results/dimm-check-20261117/`): journal now shows 12 boots since 2026-09-29, 5 with 10 modules, 7 with 12, none with 11. The missing modules are always slot DIMM_CP0_5 (serial ...568a26d4) and DIMM_CP1_5 (serial ...568a449a), both at once. Linux only reports what firmware hands over (SMBIOS and EFI memory map are 64 GB smaller; no offline memory blocks; same kernel and command line). The kernel log holds firmware error records (GHES, vendor section type bf32d4d5-b427-4025-8495-8a9e5d4030e4, names like DDS2_CP0 / DDS6_CP1, severity "corrected"): 301 in the 10-module boot of 2026-10-22, 321 in the 12-module boot of 2026-11-09, first ones at the times of the all-core memory tests. Linux EDAC counters stay 0 because the section type is unknown to the kernel. No /dev/ipmi* on the host (ipmi_ssif finds no working interface), so BMC logs are not readable from Linux.

Added 2026-11-17 20:10 UTC: the user approved setting firmware "DIMM Frequency" from 8000 to 7200 MT/s (Arm's changelog recommends 7200 for firmware 0.7.2). 6 of 6 warm reboots then gave 12 modules, gaps 170-182 s (203-260 s at 8000). bwx12 read rates at 7200 with 12 modules equal the 8000 values within +2.4 % (old read loop 468.5/467.4 GB/s at 120 threads); 0 error records in a 3.6-minute 120-thread run. The setting was LEFT at 7200 MT/s (not reverted); check `sudo dmidecode -t 17 | grep "Configured Memory Speed"` before comparing with older 8000 MT/s runs. Arm's "DCS delay training" known issue names no speed, so 7200 is supported by this test, not proven. Full report: `~/workspace/machines/arm-crb/DIMM-flaky-report.md`; data `crb/results/dimm7200-20261117/`.
