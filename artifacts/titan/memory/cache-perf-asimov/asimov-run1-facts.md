---
name: asimov-run1-facts
description: "Asimov emulator run 1 (membench-jibin-001, 2026-10-31) platform facts from Jesse's README and the first-look numbers; where the data lives"
metadata:
  node_type: memory
  type: project
  originSessionId: ca8b250c-52a6-45d3-bbc5-a704f24ca1dd
  modified: 2026-11-02T04:38:43.065Z
---

Run 1 of cache-mem-perf commit 9c6b8e7 ran 2026-10-31 on the GA13 Palladium (hemi_rtws_tlm, RTL 0d9e214, SCP 0.34.0, Linux 6.18.36). Data copied to ~/workspace/titan/cache-perf/asimov/results/membench-jibin-001/ from /home/jzhang/dev/emuMemBenchBox/results/jibin/membench-jibin-001/ (lab /home, reachable from delphi-3bda, not from claude-agentsrv). Report: ~/workspace/titan/cache-perf/asimov/run1-report.html.

Platform facts (Jesse's README in that folder):
- 1.237 s chip time, 2,779 wall s per chip s (57 min), 34 commands all exit 0. Jesse: "runs for you are cheap and decently fast".
- CPU 2's DSU port is 1 hop from the home nodes of OCM 0, 1, 2 and 3 hops from OCM 3, 4 (confirms the (x,y) reading of crosspoints 12,23,32,43,52 / 13,24,33,44,53).
- 0xA2 counts; arm_cmn_0 PMU probed (sysinfo perf events); CONFIG_DEBUG_FS unknown; /dev/ocm is Jesse's own module membench_ocm.ko, 4 KiB pages; OCM never written reads zero (write-before-read not required).
- No real-time clock: results folder is 19700101T000000Z. SPM driver absent on this image (phase C skipped).
- The HRA leg 0x8000_0000-0xBFFF_FFFF (PCIe, SMS/XMS/scratchpad control registers) is tied off on this image.
- Firmware newer than SCP 0.34.0 has mesh QoS setup; Jesse will look at matching firmware to the image (2026-11-01 20:25 PST).

First-look numbers (CPU 2, best rows): L1 2.00 ns, L2 6.07 ns, SLC 23.1-24.0 ns (fresh 512K-2M), DRAM 52.3 ns; OCM per region flushed 18.8-20.1 ns (1 hop) and 22.4-23.2 ns (3 hops); all-five OCM 25.2-25.5 ns. One-core read beyond L2 is 9.2-10 GB/s at every footprint; write 32 GB/s flat; hemisphere write limit about 88 GB/s; 8-core read 67 GB/s; OCM read 16.6 GB/s per core, scales to 66.5 with 4 cores.

Defects found in run 1 (to fix in run 2): DC CIVAC removes DRAM-backed lines from the SLC too (flushed rows = DRAM); OCM write rows with --flush-after measure DC CIVAC throughput (7 ns per line est.), not OCM writes; 256 KiB flushed rows carry 9-23 % prefetched lines (learned chain 0), fix with --fresh 3 --flush.

Verified 2026-11-01 (Jesse's agent reply 21:37 PST, checked against sources):
- OCM is CMN OCM mode: SCP program_ocm (positron-ai/asimov-scp-firmware product/asimov/scp_ramfw/asimov_physical_sam.c:458-490) writes HN_LOCK_WAYS = 0x100 | W, four HN_LOCK_BASE registers, then HN_CFG_CTL |= HN_OCM_EN with ALLWAYS cleared. Address map (positron-ai/asimov-address-map profiles/sam_map.yaml:208-212): ocm0..4 route to one home node each (HNS_CTRL, HNS_X2..X5), "No HN subordinate" (no memory behind). TRM p292: in OCM mode the HN-F sends no requests to the SN-F and CleanInvalid/CleanShared terminate in the SLC without invalidation. So DC CIVAC on OCM is a no-op for the data; run 1 agrees.
- Home-node ids of OCM0..4: 88, 160, 216, 288, 344. Decoded with the 9-bit CMN node-id layout (X[8:6] Y[5:3] port dev): crosspoints 13, 24, 33, 44, 53, which match the RTL list.
- arm_cmn_0: 280 events (Jesse's env.txt on the lab home, evidence/runs/membench-boot-002/window/env.txt). Formats: bynodeid config:31, nodeid config:32-47, type config:0-15, eventid config:16-26, occupid config:27-30. Events of interest: hns_cache_miss_all (type 0x200 eventid 0x1), hns_slc_sf_cache_access_all (0x2), hns_cache_fill_all (0x3), hns_pocq_reqs_recvd_{all,hbt,lbt} (0x5, occupid 0/1/2), hns_sf_hit_all (0x6), hns_slc_eviction_all (0xa), hns_mc_reqs_local_all (0xd).
- Driver rules (arm-cmn.c): PERF_PMU_CAP_NO_EXCLUDE (exclude_kernel/hv must be 0), task-attached events rejected (use pid -1 with a cpu), event->cpu forced to the PMU's cpu, a mesh event cannot share a group with a core event. No perf tool in the image (busybox only); use perf_event_open.
- CONFIG_DEBUG_FS off in the current kernel: stated by Jesse's agent, not verifiable from env.txt (only 10 CONFIG_ lines there); Jesse offers to enable it for the next run.

**Why:** These facts shape run 2 and every later interpretation.
**How to apply:** Do not re-ask Jesse for the hop layout, the PMU, or chip-time cost. Related: [[asimov-run-status-2026-10-31]], [[asimov-emulator-run-facts]].
