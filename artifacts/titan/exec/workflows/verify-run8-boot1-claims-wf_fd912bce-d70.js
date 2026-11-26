export const meta = {
  name: 'verify-run8-boot1-claims',
  description: 'Independently recompute and try to refute the run 8 rehearsal and boot 1 claims from the raw files',
  phases: [{ title: 'Verify' }],
}
const ROOT = '/home/jhan/workspace/titan/cache-perf/asimov'
const COMMON = `You are an independent checker. Work read-only inside ${ROOT} (do not edit or create files there; put any script under /tmp). Write your OWN script from the raw files; do not reuse any existing analysis script. Try to REFUTE each claim. For each claim return verdict confirmed / refuted / partly, with the numbers you computed and the file and row you took them from. Report anything else in the files that looks wrong or surprising. Do not use ssh or any remote machine.

Context: results/membench-jibin-013/results/bootM0/ holds a rehearsal of the program meshmap (map-rehearsal.csv, -homes.txt, -log.txt; dmesg.txt one level up). results/membench-jibin-014/results/bootM1/ holds the full run (latency-map.csv with 23 fields per row: kind,cpu,node,lines,rep,ns_per_load,... ; map-homes.txt; four latency-ocm-region*-mapctl-cpu*.csv control files; log.txt; all.txt). Lines starting with # are comments. Kinds: ocm-flush, slc, ocm-evict, dram-flush, idle. Home nodes 88,160,216,288,344 sit at mesh (x,y) = (1,3),(2,4),(3,3),(4,4),(5,3). CPU pairs: 0-1 at (1,2), 2-3 at (2,3), 4-5 at (3,2), 6-7 at (4,3), 8-9 at (5,2). "best" = minimum ns_per_load of the 7 passes of one cell (kind,cpu,node). The method document is measure-hop-latency.md and the handoff is status/HANDOFF-run8-meshmap.md (section 3 has the ten rehearsal checks).
`
const TASKS = [
  { key: 'rehearsal', prompt: `Claims about the rehearsal (013):
R1. All ten checks of section 3 of status/HANDOFF-run8-meshmap.md pass for map-rehearsal.csv / log / homes / dmesg. Go through each of the ten rows and judge it yourself.
R2. In the first 32 "# probe" lines the winning count is 133 to 144 and the next largest count is at most 22; with the read floor "7 6 5 12 10" subtracted, a DRAM-backed line gives about 2.0 counts per flush-and-load pair (64 pairs per probe).
R3. Exactly one probe was ambiguous (line 248, d=68,60,205,70,71) and no line was left unused.
R4. The rows: ocm-flush 23.19 to 27.95 ns, slc 22.89 to 27.22 ns, ocm-evict 22.63 to 27.36 ns, dram-flush 50.67 to 56.75 ns. mc_reqs per load: slc 0.00 to 0.22, ocm-evict 0.00 to 0.02, dram-flush 1.00 to 1.11.
R5. dmesg.txt has no arm-cmn error and no warning other than the out-of-tree module taint line.
Also check results/membench-jibin-013/SHA256SUMS with sha256sum -c.` },
  { key: 'complete-controls', prompt: `Claims about boot 1 (014):
B1. sha256sum -c of results/membench-jibin-014/SHA256SUMS passes for all 11 files.
B2. latency-map.csv has 1,269 data rows, each with 23 fields: 180 cells x 7 passes = 1,260 plus 9 idle rows; the CPUs are 0 and 2 to 9; perf_cov is 1.0000 in every row; the file ends with "# meshmap: done cells=180/180".
B3. The four control files (program latency, 256 KiB OCM chain) give best 22.741 ns (CPU 2, region 0 = node 88), 26.789 ns (CPU 2, region 4 = node 344), 29.859 ns (CPU 8, region 0), 21.906 ns (CPU 8, region 4). The ocm-flush cells of the same CPU and node in latency-map.csv have best 22.561, 26.778, 29.734, 22.059 ns. The largest difference is 0.18 ns.
B4. ocm-flush cells of CPUs 2 to 9 (40 cells, best of 7): least-squares fit ns = 21.03 + 1.95 per X step + 1.05 per Y step, rms 0.22 ns. Against the older fit 20.75 + 1.99 X + 0.95 Y the 40 residuals run from -0.18 to +0.62 ns.
B5. In every row of CPUs 2 to 9, l1d_refill_hwprf and l2d_refill_hwprf are 0.0000. In the CPU 0 rows at least one of them is nonzero in 128 of 140 cell rows, and the CPU 0 ocm-flush cells read 12.7 to 15.7 ns best, far below CPUs 2 to 9 (22.0 to 29.7 ns).
B6. dram-flush cells of CPUs 2 to 9 spread at most 0.13 ns between their 7 passes; ocm and slc cells spread 1.2 to 2.1 ns typically (state the true ranges). Say what you can about why the OCM/slc passes spread more (look at per-pass values, do not guess beyond the data).` },
  { key: 'slc-counters', prompt: `Claims about boot 1 (014), CPUs 2 to 9 only (40 cells per kind):
S1. slc best minus ocm-evict best, per cell: mean +0.004 ns, range -0.25 to +0.35 ns, rms 0.13 ns. Also compute it with the median of 7 instead of best and report.
S2. Fits ns = a + b per X step + c per Y step on best values: slc a=20.64 b=2.00 c=0.99 rms 0.10; ocm-evict a=20.61 b=2.00 c=1.00 rms 0.09.
S3. ocm-flush best is on average 0.37 ns above slc best (range of slc minus ocm-flush: -0.76 to +0.37).
S4. Counters per load, median of the 7 passes per cell: mc_reqs is 0.0000 to 0.0122 for slc, 0.0000 to 0.0015 for ocm-evict, 1.0000 to 1.0005 for dram-flush. cache_miss is about 0.015 to 0.025 for slc and 1.015 for dram-flush. l3d_refill_rd is 1.00 for all kinds.
S5. req of the cell's own node minus the mean of the other four nodes, per load (median of passes): 1.20 to 1.28 for slc, ocm-evict and dram-flush. The other four read about 0.25 for slc and ocm-evict and about 0.05 for dram-flush.
S6. Only 3 of the 280 slc passes of CPUs 2 to 9 have mc_reqs above 0.05 (check: the earlier count was over all CPUs; give both), with a maximum of 0.0635. Find the ocm-evict pass with mc_reqs 0.4536: which cpu, node, rep, and its ns_per_load against the other passes of that cell.
List every pass of CPUs 2 to 9 whose ns_per_load is more than 1.0 ns above its cell's median, by kind.` },
  { key: 'hash-dram', prompt: `Claims about boot 1 (014):
H1. map-homes.txt records 10,255 probed lines of one 2 MiB page whose first frame is pfn 0xc004800 (4 KiB frames, so physical address 0xc004800000; line i is at that address + 64*i). Characters 0..4 are indexes into nodes 88,160,216,288,344; '?' is unclassified (10 of them).
Arm's non-power-of-two hash (CMN S3 manual 107858): with A = Addr[51:6],
 hash12[11:0] = {0b00, A'[51:42]} ^ A'[41:30] ^ A'[29:18] ^ A'[17:6]   (bit numbers are physical address bits)
 select = ( {h11^h0, h10^h1, h9^h2, h8^h3, h7^h4, h6^h5, h5, h4, h3, h2, h1, h0} * 5 ) >> 12
Claim: this select predicts the measured home of all 10,245 classified lines under one fixed mapping select 0,1,2,3,4 -> nodes 88,216,344,160,288, with zero exceptions. Implement the formula yourself from the text above and test it. Also test it on results/membench-jibin-013/results/bootM0/map-rehearsal-homes.txt (320 lines). Also report: what does the formula predict for the 10 '?' lines, and how many lines per node.
H2. dram-flush cells of CPUs 2 to 9 (40 cells, best of 7). Model T (triangle): ns = a + p*X + q*Y where X and Y are the mesh link crossings in x and in y summed over three legs CPU -> home node -> memory node M -> CPU (Manhattan). Model V (return through the home node): crossings of CPU -> home -> M -> home -> CPU. Search M over x,y in 0..6. Claim: model T with M at (0,3) or (1,3) (these two tie exactly) fits with rms 0.089 ns, a=46.07 (M at (0,3)), p=0.985 ns, q=0.318 ns; the best model V has rms about 1.07 ns. Recompute, and also state which other M positions come close under model T, and whether a plain fit on CPU-to-home distance alone (a + b*dx + c*dy) fits badly (claim: rms 1.73 ns).
H3. The mesh map in results/membench-jibin-011/results/bootF1/sysinfo.txt (around lines 489-551) shows a node of type SBSX at crosspoint (0,3) and the HN-S nodes at (1,3),(3,3),(5,3),(2,4),(4,4). Check the map and list every SBSX position.
H4. For slc cells, in the same per-crossing units (a round trip CPU -> home -> CPU = 2 crossings per step) the fit is a=20.64, 1.00 ns per X crossing, 0.49 ns per Y crossing. So the Y cost per crossing differs between slc (0.49) and model T for dram-flush (0.32). Check and say whether a model T with q forced to 0.49 and p forced to 1.00 still fits (give its rms with only a free).` },
]
const SCHEMA = { type: 'object', properties: {
  claims: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly'] },
    computed: { type: 'string' }, source: { type: 'string' } }, required: ['id', 'verdict', 'computed'] } },
  other_findings: { type: 'array', items: { type: 'string' } } }, required: ['claims', 'other_findings'] }
phase('Verify')
const out = await parallel(TASKS.map(t => () => agent(COMMON + '\n' + t.prompt, { label: 'verify:' + t.key, phase: 'Verify', schema: SCHEMA }).then(r => ({ key: t.key, ...r }))))
return out.filter(Boolean)