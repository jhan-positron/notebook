---
name: asimov-cache-topology-conflict
description: Asimov C1-Nano topology as confirmed by the user on 2026-10-30 (L1 private, L2/L3 shared per 2-core DSU); earlier conflict resolved
metadata:
  type: project
---

Asimov (one hemisphere): 5 DSUs, 2 C1-Nano cores each. L1 private per core. L2 and L3 shared by the 2 cores of one DSU. OCM (on-chip SRAM) outside the DSU. SLC 5 MiB on CMN per notebook notes. User confirmed this on 2026-10-30 after an earlier description ("L1 shared, L2/L3 private") turned out to be a typo.

Run setup (Jesse Zhang, DM 2026-10-30): emulator only, no shared login. Jesse compiles and runs our plain-C sources under asimov-os (Linux on the C1-Nanos) as PID 1, on a core other than the one running the kernel. One core per DSU runs the kernel, so at most 5 cores are available for the test. Jesse wants a markdown note of the expected numbers plus the sources. Sources go in ~/workspace/titan/cache-perf/asimov/.

**Why:** The benchmark design (which cores share L2/L3, which cores are free) depends on this.
**How to apply:** Still print sysfs cache topology from the program at start as a check. Related: [[crb-machine-access]], [[crb-hierarchy-findings]].
