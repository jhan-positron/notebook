---
name: asimov-run8-results
description: "Run 8 mesh latency map results (rehearsal 013, boots 1-3 = 014/015/016), where the report pages and generators live, key numbers and open items"
metadata:
  node_type: memory
  type: project
  originSessionId: e5424841-ab73-4e33-aa57-48b09daa261f
  modified: 2026-11-12T17:26:20.116Z
---

Run 8 (mesh latency map, `meshmap` + `run_map.sh`, commit 3b12e4f) is complete: rehearsal 013 (2026-11-11), boots 1, 2, 3 = folders 014, 015, 016 (Jesse's message 2026-11-12 09:09 PST). All copied to `results/membench-jibin-01{3,4,5,6}` and checksum-verified. Jesse ran every boot with `--kernel-cpus` and did not wait between boots.

Pages (project folder, not committed, `asimov-c1nano-perf.html` NOT updated; that needs Jibin's word):
- `run8-meshmap-boot1.html` via `gen_run8_report.py`: rehearsal + boot 1 in full.
- `run8-meshmap-3boots.html` via `gen_run8_boots.py`: the three boots side by side. Both were checked by four independent checker agents each.

Key numbers (CPUs 2-9):
- Boot 1 (L3 off, prefetch off): ocm-evict 20.61+2.00X+1.00Y ns, slc equal to it (mean diff +0.004 ns); dram-flush 50.0-57.3 ns, three-leg path via a memory point at row y=3, x<=1 (SBSX at (0,3)), rms 0.089.
- Boot 2 (L3 on, prefetch off): ocm-flush repeats boot 1 (+0.05 ns; medians fit 21.23+2.00X+1.00Y, rms 0.01); dram-flush +0.62 ns uniform (unexplained; boot 3 no-prefetch passes read boot 1's value in 4 of 5 cells). slc and ocm-evict are 13-17 ns because l3d_refill_rd is only ~0.3: mix model ns = a(1-f)+f(b+c*u+d*[pass>=4]) gives a ~10.3 ns est., c ~0.98, d ~1.3 ns, rms 0.09-0.10. So boot 2 evicted kinds are NOT a slice distance map.
- First cells of a cluster (even CPU, node 88) start with share 0.98 and fall to ~0.35 within a few passes; the second CPU of the cluster never shows it; CPU 0 shows it on all boots. The evictor (30,720 lines, 7.5x the L3) is not too small; cause unknown.
- Boot 3 (L3 on, prefetch on): flushed kinds 12-35 ns, not a distance map; evicted kinds as boot 2. Prefetches go to the chain's own lines (own-node requests ~1.05/load).
- Arm CMN S3 hash predicts every classified line on three pages (pfn 0xc004800, 0xc004c00, 0xc004000), table order 88, 216, 344, 160, 288.
- Passes 4-6 (upper 32 bytes of the line) cost +1.3 ns per mesh load on every boot; absent in dram-flush.
- CPU 0 cells are never distance numbers (its cluster keeps L3 on, prefetch on).

Open: why the cluster keeps ~70% of chain lines; 10.3 ns vs README's 6.1 ns L3 latency; +0.62 ns dram-flush; mesh base +0.5..1.0 ns in the mix; ocm-flush +0.37 ns over ocm-evict on boot 1; Y cost 0.32 vs 0.49. Suggested tests: one boot 2 cell under `--events l3`, an evictor that stores, node order reversed.

See [[asimov-run8-meshmap]] for the code and the request, [[verify-other-agents]] for how Jesse's README was treated.
