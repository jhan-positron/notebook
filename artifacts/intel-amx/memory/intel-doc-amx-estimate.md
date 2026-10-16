---
name: intel-doc-amx-estimate
description: 2026-09-02 verified facts for the "Intel documents only" prediction of the AMX attention unit (kernel tile counts, Table 20-2 rates, floors, brackets vs measured), the VDPBF16PS throughput trap (uops.info EMR 2 cycles, not 0.5), and the unresolved DRAM-traffic discrepancy; Notion page location
metadata:
  type: project
---

Notion page: Daily notes / Intel AMX / Primer: Why AMX helps decode and by how much /
"Estimate: the AMX decode boost from pre-AMX data, in plain English"
(https://app.notion.com/p/3cfd132d3cfd81fe8b79d71a428e7695). Goal (parent page): estimate
the AMX decode boost BEFORE implementation from (1) Tron decode characterization, (2) AVX
characterization using Tron, (3) AMX modeling from Intel documents; compare afterwards.

Verified 2026-09-02 (4 research + 3 modeler + 6 refuter agents, my own python checks):
- Kernel per unit (mirror path, amx_attn.cpp qk_mirror_128x4 + weights_times_v_128x4):
  32 TDPBF16PS, 40 TILELOADD (4 Q + 16 K-mirror + 4 P + 16 V, all 1 KiB tiles, Q/P have
  4 real rows of 16), 12 TILESTORED, 12 TILEZERO; LDTILECFG once per apply_page_range
  (per worker per layer). Bytes streamed per unit 32 KiB (16 KiB K mirror + 16 KiB V).
- Intel opt manual 248966-050 Table 20-2 (lines 31320-31328 of the local text in
  ~/workspace/intel-vs-amd/enable-SNC3/claude-workspace.8/refs/): TDP/* 16 cyc throughput
  / 52 latency, TILELOADD 8/45, TILESTORED 16, TILEZERO 0, LDTILECFG 204; chapter scoped
  to Sapphire/Emerald Rapids (no Granite Rapids table). Sec 2.1.1.4: Redwood Cove L2 miss
  queue 48->64. Sec 20.15: tile load after store "significant slowdown", no number. Sec
  20.2.1: AMX license clock "usually lower", no MHz. Only server cache-bandwidth table is
  Skylake Server 2-11 (L2 64/52, L3 32/15 B/cycle). ARK 6962P: 12 ch, DDR5 6400 / MRDIMM
  8800, 2.7/3.9 GHz, 432 MB cache, 2 AVX-512 FMA units, no bandwidth row, no L2 row.
- Floors per unit: compute 512 cyc (0.13-0.19 us at 3.9/2.7 GHz); loads+stores 512 cyc
  more; L3 0.26-0.81 us; DRAM socket share 12x6400x8 = 614.4 GB/s / 27 workers = 22.8 GB/s
  -> 1.44 us; Little's law 64x64 B / L = 0.8-1.6 us at L = 100-200 ns (L unpublished).
  Brackets (unit = matmul + AVX common): 256: 0.24-0.92 us -> +4.3..+5.8%; 2048:
  0.38-0.93 -> +17.0..+23.2%; 8192: 1.60-3.64 -> 0..+47.5%. Measured mirror units
  1.36 / 2.07 / 2.66 us; gains +0.5 / +6.1 / +17.3%. Intel-only = upper bound; measured
  AMX matmuls run at 13.9 GB/s per core = 61% of pin share.
- VDPBF16PS TRAP: Intel documents give NO latency/throughput for it. uops.info (Emerald
  Rapids, Alder Lake-P): 4 uops, throughput 2.00 cycles/instr, latency 8; Granite Rapids
  not listed. The rampup/distilled pages' "AMX = 8x AVX-512 BF16 MAC throughput" assumes
  2 VDPBF16PS/cycle; with the measured 2 cycles it would be 32x. Dotter issues 2048
  VDPBF16PS + 256 horizontal reductions per unit (dotter.hpp:176-222, kv_cache.hpp
  scaled_v_expr). The kernel's 4-of-16 rows make its realized compute ratio 2x (y=0.5)
  or 8x (y=2), not the peak.
- RESOLVED 2026-09-03 (mostly): perf-stat rounds 2/3 IMC numbers (54-58 GiB/s) counted only
  sub-channel 0 (legacy uncore_imc cas_count on kernel 6.8.0-124; GNR has 2 schedulers per
  channel; drambw report measured x2.01 vs membw ground truth). True reads ~115 GiB/s = 80% of
  the 145 GiB/s all-from-DRAM expectation, 20% of the 614 GB/s pin peak. Fixed event
  cas_count_read_sch0/sch1 exists on kernel 6.8.0-136+ (3bda now on -138).
- KEY CORRECTION 2026-09-03 (jhan pushed back: 'TRON is not memory bound, ~30% DDR'):
  Tron decode is NOT DRAM-bandwidth-bound (drambw 2026-08-16 tp4: 11.5-14.4% mean, 28-30%
  peak of a 220 GB/s/socket membw ceiling; peakbw 2026-08-19: 10 ms p99 28-30%, RPQ residency
  2.15x saturation = latency-class; top-down mem-bound 26-30%). The binding limit is the
  PER-CORE streaming rate: membw 15.2-16.0 GB/s per reader on 3bda; 3af6 SNC3 study
  (2026-06-05, intel-vs-amd/enable-SNC3/claude-workspace.9/REPORT/FINAL_REPORT.md):
  single-thread 15.9 GB/s (SNC off), idle DRAM latency 127-138 ns, loaded to 147 ns, socket
  saturation 595 GB/s at 64 readers. AVX dotter 9.4 GB/s/core, AMX kernel 13.9 (88% of reader).
  Memory floor = 32 KiB / 15.9 GB/s = 2.06 us -> unit 2.22 -> ceiling +28.9% (vs +47.5% with
  the pin share, measured +17.3%). Use the per-core reader rate, never the socket share.
- Sum-of-medians vs median-of-sums: page's 1%/4%/10% phase-sum gap is half a statistics
  artifact; per-token median gap is 0.5/2.0/6.5%. Untimed code between the phase timers
  = channel handshakes, speedometer.observe, free_scratchpads_barrier.done; the
  post_attention hook is an empty lambda for generated plugins (model.hpp:2159).

**How to apply:** for any "predict from Intel docs" ask, reuse the floor list above and
say plainly that Intel gives floors only; the missing inputs (loaded latency, per-core
achievable bandwidth, per-core L2/L3 bandwidth on Redwood Cove, VDPBF16PS timing) are
pre-implementation measurements: Intel MLC + a one-core kernel loop. Related:
[[single-attention-measurement]], [[amx-vs-avx-sense]], [[attn-worker-lane-facts]],
[[notion-questions-keep-verbatim]].
