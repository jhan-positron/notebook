---
name: aarch64-disassembly-source
description: Where to get aarch64 machine code of the cache-perf bench binaries; a downloaded cross-compiler cannot be run here
metadata:
  node_type: memory
  type: reference
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-11T21:43:05.532Z
---

`bench/bandwidth` and `bench/latency` on the dev machine are x86-64 builds. The aarch64 builds live only on CRB under `~/cache-perf/bench/` (source there had the same sha256 as the local source on 2026-11-11).

- To read the machine code, run `objdump -d --no-show-raw-insn --disassemble=<function> bandwidth` on CRB in one read-only ssh login (`jhan@192.168.2.45`, key already set up). Check `/tmp/positron-perf.RUNNING` first and follow `crb/jeremy-plan-constraints-2026-10-30.md` (announced blocks are in Slack #phoenix-crb).
- Do not plan on a local cross-build: on 2026-11-11 the session's permission system declined to execute a downloaded Arm GNU toolchain ("Code from External"). Ask the user first if a cross-compiler is really needed.
- The output of the 2026-11-11 login is kept at `crb/results/probe-20261111T210017Z.txt` (disassembly of k_read, k_write, k_copy, k_asmread, gcc version, `-march=native` string, firmware and kernel version, mesh event names).
