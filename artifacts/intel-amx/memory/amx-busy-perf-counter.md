---
name: amx-busy-perf-counter
description: "2026-09-17 validated on delphi-3bda: perf raw event cpu/event=0xb7,umask=0x02 = EXE.AMX_BUSY (cycles the AMX unit is busy) is direct evidence that AMX instructions executed; use per-process (-p PID) with a kill-switch control arm; perf 6.8.12 has no named AMX events for granite_rapids; perf needs sudo (perf_event_paranoid 4); TRAP: in perf -x, CSV the 4th column is run time in ns, not a count"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e961bb62-6371-4178-8c22-42772c040878
  modified: 2026-09-17T20:12:02.171Z
---

Direct evidence that a tron process executed AMX tile instructions (stronger than the
arch_prctl probe, which only shows the permission request):

    sudo -n perf stat -e cpu/event=0xb7,umask=0x02,name=exe_amx_busy/ -e cycles -x, -p <PID> -- sleep 30

Validation on delphi-3bda 2026-09-17 (pmu_name granite_rapids, perf 6.8.12, kernel 6.8.0-138),
record exec/results/ci-enable-20260917/counter-validation.txt, program exec/ci-enable-20260917/amxspin.c:
- amxspin (20,000,000 tdpbf16ps): exe_amx_busy = 320,005,520 = 16 busy cycles per tile multiply
  (the documented THROUGHPUT of TDPBF16PS; its latency is 52 cycles, Intel Table 20-2).
- amxspin scalar loop (2.9 G instructions): 0.
- production rinzler 2026.09.17-31b80a18 (no AMX code), 3 s per-process: 0 with 742 G cycles.
- packaged AMX rinzler serving qwen3-4b: 873 M busy cycles over 3 decode requests, 0 idle,
  0 with TRON_AMX_DISABLE=1 (exec/results/ci-enable-20260917/summary.tsv).

CSV TRAP (cost a wrong claim on 2026-09-17, caught by the verification pass): `perf stat -x,`
prints `count,unit,event,run_time_ns,percent,...`. A line `0,,exe_amx_busy,2042032885,100.00`
means count 0 and 2.04 s of counting, NOT 2 G busy cycles. Per-CPU (-C) and system-wide (-a)
modes counted 0 on this no-AMX system, as they should; an earlier note calling them "unusable"
was this misread.

**Why:** tron has no log line or counter for AMX use; the probe (arch_prctl 0x1023) shows only
that permission was requested once per process.
**How to apply:** per-process on the engine pid, always with a kill-switch (TRON_AMX_DISABLE=1)
control arm of the same binary and an idle window; `perf list` shows no amx events here, so use
the raw encoding; read the FIRST CSV column. See [[amd-amx-fallback-test]] (probe shim),
[[nightly-amx-check-20260916]] (binary checks), [[ci-enable-20260917-campaign]].
