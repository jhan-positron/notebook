---
name: crb-asct-install
description: "ASCT (Arm System Characterization Tool) on CRB - install location, what works without root, how to run its bandwidth binary directly on our CPUs with core counters (no root), and what stays blocked"
metadata:
  node_type: memory
  type: reference
  originSessionId: 368e092f-68c9-444b-98e6-22b5a4799cfe
  modified: 2026-11-16T23:55:00.000Z
---

ASCT is the Arm vendor tool for memory latency / bandwidth benchmarks and system reports. Kit source: `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/` (INSTALL.md, two vendor baseline result archives under `reports/`).

- Installed on CRB (`jhan@192.168.2.45`) on 2026-11-15 local time (CRB clock 2026-11-16 00:38 UTC) with the vendor `install.sh` (option 1, no sudo). Version 0.7.1+77461b3, the same version as the vendor baseline results.
- Activate: `source ~/asct/asct_venv/bin/activate`. Uninstall: `rm -rf ~/asct/asct_venv`.
- Layout on CRB: `~/asct/asct-0.7.1+77461b3/` (release bundle, offline manual `asct_docs/index.html`), `~/asct/golden/` (the two vendor baseline runs, extracted), `~/asct/runs/` (run outputs; asct writes its output folder and `asct.log` into the current folder).
- Works without root (all run on 2026-11-15): `asct version`, `list`, `help <cmd>`, `run ... --dry-run`, `report system-info` (DMI fields print "root required"), `view`, `diff`, `config save|check`.
- `asct --version` is not valid; the command is `asct version`.
- Source code: the kit folder holds none. The C source of the measurement loops is inside the inner tarball of the release bundle, `~/asct/asct-0.7.1+77461b3/asct-0.7.1+77461b3.tar.gz` on CRB (250 files; not extracted there). Loops: `extern/infra-microbenchmarks/loaded-latency/bandwidth.c` (read / write / mixed loops as inline `ldr`, `str`, `dc`, `stnt1w`), `memlatency.c` (pointer chase `run()`), `cntvct.h` (timer `cntvct_el0`), and `extern/core-to-core/pingpong/`. Build flags per variant are in `src/core/config/ubench.json`; the Makefiles add `-O2 -Wall`. Built binaries: `~/asct/asct_venv/bin/{loaded-latency-asct,loaded-latency-asct-sve,ping-pong-asct}.bin` (not stripped).
- No memory benchmark was run as of 2026-11-15. CRB had 0 free huge pages of every size. The manual says a non-root run uses only preallocated huge pages and skips a benchmark that cannot get them; latency-sweep needs them and every other memory benchmark depends on latency-sweep. So a memory run needs root, and root on CRB needs the user's approval per task (see [[crb-whole-chip-read-drop-2026-11-15]]).
- Before a memory run, ask the user about CPUs 126-127 (isolated under the 2026-10-22 rule in `crb/jeremy-plan-constraints-2026-10-30.md`): the manual says idle-latency and loaded-latency measure from the last core of a node (CPU 127 on CRB) and peak-bandwidth uses all cores. `loaded-latency` has `latency_cpu_id` and `bw_cpu_blocklist` settings; I did not check how the others can be kept off those CPUs.
- Vendor run time for `asct run memory`: 13 min 19 s and 13 min 39 s in the two vendor `asct.log` files (vendor machine: 136 CPUs, 2 NUMA nodes, root). CRB has 128 CPUs and 1 NUMA node, so the NUMA matrices of a CRB run will not match the vendor rows one to one.
- Method that works without root (used 2026-11-16, report `crb/new-test-kernel/ASCT-cross-check.html`, scripts and DECISIONS.md in `crb/tmp/agent-scratch/asct-2026-11-16/`): do not use `asct run`; start the installed binary directly with the command line that the front end builds: `numactl --membind 0 ~/asct/asct_venv/bin/loaded-latency-asct-sve.bin --duration D --delay-seconds 0 --bw-cpu C [--bw-cpu C ...] --bw-buflen BYTES --bw-fine-delay N --bw-write=0 --bw-cacheline-bytes 64`. `bandwidth-sweep` has no setting for its core (fixed: last CPU of node 0 = CPU 127).
- Core counters without root: build the probe variant from the inner tarball (`make EXE=... CFLAGS="-DASCT -DUSE_PROBE -DHAS_SVE -march=armv8.2-a+sve -I<extern/dietperf>"` in `extern/infra-microbenchmarks/loaded-latency`), then set `DIETPERF_PMUv3=<comma list of raw hex codes, at most 16>` and `DIETPERF_OUTDIR=<folder>`. It counts user mode, the measured phase only, one file `<cpu>_<tid>` per thread. Create the folder before the launch: two threads that create it at the same time make the binary exit with code 17. A rebuild without the probe flag gave the same sha256 as the installed binary. The probe binary is at `~/cache-perf/asct-20261116/loaded-latency-asct-probe-sve.bin` on CRB.
- ASCT's total is the sum of per-thread rates over time spans of different length. When threads finish early it is too high. Give the lower bound (all bytes / time of the slowest thread) beside it.
- Still blocked: mesh counters (`DIETPERF_CMN` opens system-wide events, so root), `asct report sysreg` (no `/sys/kernel/sysreg` on CRB, V3AE not in its list), `asct report cmn` (root and `/dev/mem`).
- On 2026-11-16 the permission system of the agent session refused a CRB command that contained `sudo -n perf stat -a` (my reading of the request as approval was not enough). Ask the user for an explicit approval of the root command before planning runs that need it, and say so early.
