---
name: crb-machine-access
description: CRB (Arm Phoenix Reference Server, 192.168.2.45) access, hardware identity, and sharing constraints found 2026-10-30
metadata:
  type: project
---

CRB = Arm "Phoenix Reference Server" (AGI-CPU-CRB EVT0, Quanta A1DI0 board), `ssh jhan@192.168.2.45` (key auth, hostname "ubuntu"). 128 cores, MIDR 0x410fd832 (part 0xd83 = Neoverse V3AE per Linux cputype.h), 2.8 GHz fixed (performance governor, boost off), no SMT, 1 NUMA node, 320 GiB DRAM (10 x 32 GiB DIMMs).
Caches from sysfs: L1d 64 KiB/L1i 64 KiB private, L2 2 MiB private, L3 128 MiB shared by all 128 cores (no index4). Two arm_cmn PMUs with hns_slc_* events: the L3 is likely the CMN system-level cache.
Constraints: shared box (accounts arm, positron-perf, jhan). User rule 2026-10-30: do not change anything on CRB, inspect only, until sharing policy confirmed. No passwordless sudo. perf_event_paranoid=2 (user-mode core counters only, no uncore). Logins limited to CPUs 0-119 by systemd CPUAffinity; 126-127 isolcpus. No clang, no lmbench/likwid/hwloc; gcc 14.2, perf 7.1.3, numactl present. No aarch64 cross compiler on the local x86 host, so sources must be compiled on CRB.
Full record: ~/workspace/titan/cache-perf/crb/inspection-record-2026-10-30.md

**Why:** Bill asked (2026-10-30) for per-level cache + DRAM latency/bandwidth on CRB, then Asimov. See [[asimov-cache-topology-conflict]].
**How to apply:** Re-check sharing policy before running anything on CRB. Use CPUs 0-119 unless told otherwise.

Sharing rules (from ~/workspace/titan/rampup/jeremy-tasks-plan.html, written by the user as admin "Jibin", 2026-10-22): Jeremy (account positron-perf) runs counted latency "blocks" Mon-Fri 13:00-21:00 UTC only, announced 2 h ahead in the phoenix-crb Slack channel, marked by /tmp/positron-perf.RUNNING. During a block: no logins, no processes. Never pin to CPUs 126-127. No boot-setting, package, timer, governor changes or reboots before the 2026-11-05 demo. Check the RUNNING file before any CRB work. Digest: ~/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md

Mesh topology (checked 2026-11-01): `sudo cat /sys/kernel/debug/arm-cmn/map /sys/kernel/debug/arm-cmn/map_1` prints each mesh as an X by Y grid of XPs with the device type on every port (HN-S = home node with SLC slice, RN-F_* = core requester, SN-F = memory controller) and the logical node id of device 0 and 1 on each port (two ids on one port = a CAL). CONFIG_ARM_CMN=y, CONFIG_DEBUG_FS=y, debugfs mounted, /sys/kernel/debug is root-only (0700). Kernel 7.1.3-arm-agi-20260916. The "mesh %dx%d" line is dev_dbg, not in dmesg.
