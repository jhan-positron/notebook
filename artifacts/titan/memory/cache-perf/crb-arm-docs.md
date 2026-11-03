---
name: crb-arm-docs
description: "Arm documents that match CRB's hardware (Neoverse V3AE r0p2 core, CMN S3 mesh), where the PDFs are kept, and the facts taken from them"
metadata:
  node_type: memory
  type: reference
  originSessionId: ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e
  modified: 2026-11-01T19:20:23.272Z
---

CRB cores are Neoverse V3AE r0p2 (MIDR 0x410fd832). The mesh is Arm CMN S3 (arm_cmn identifier 43e05, part 0x43e = PART_CMN_S3 in drivers/perf/arm-cmn.c; events are `hns_*`, Super Home Node).

PDFs kept in ~/workspace/titan/cache-perf/crb/refs/ (downloaded 2026-11-01 from documentation-service.arm.com; the developer.arm.com HTML pages are script-rendered and cannot be fetched):
- arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf (issue 3.0). Table 2-1 p13: pipes Load/Store 0, Load 1, Load 2, Store 1, Store data 0/1, FP/ASIMD 0/1. Table 3-13 p23: LDR q 3/cycle, LDP q 1.5/cycle. Table 3-14 p25: STR q 2/cycle, STP q 1/cycle. So L1 = 48 B/cycle load, 32 B/cycle store = 134.4 / 89.6 GB/s at 2.8 GHz (measured 132.7 / 89.5).
- arm-cmn-s3-r2p3-trm-107858.pdf. 1.4 p17 mesh of crosspoints, up to 4 device ports per XP. Home Nodes p19: one home per address, each HN-S has SF + SLC. 2.1.1.3 p54 SLC definition. 2.1.1.15 p63 CAL2 = two identical devices (RN-F allowed) on one XP device port. Table 1-9 p31: SLC per node 0 to 4 MiB, 12 or 16 ways.
- arm-cmn-700-trm-102308-issue08.pdf (same CAL wording, section 3.1.1.13).

Not obtainable: Neoverse V3AE core TRM 101595 (HTML only). L1 4-way / L2 8-way / SLC 16-way come from CRB sysfs cache index0/2/3. Linux topology gives each CPU its own cluster, so the core-pair port is measured only; CAL2 is the documented mechanism, not confirmed for CRB. Mesh node count: read 2026-11-01, 64 HN-S per mesh, see [[crb-hierarchy-findings]]. Related: [[crb-hierarchy-findings]], [[crb-machine-access]].
