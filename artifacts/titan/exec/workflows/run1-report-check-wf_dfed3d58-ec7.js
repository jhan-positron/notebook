export const meta = {
  name: 'run1-report-check',
  description: 'Adversarially verify every number and claim in run1-report.html against the run 1 CSVs and the sources',
  phases: [
    { title: 'Check', detail: 'four readers, one per section group' },
    { title: 'Refute', detail: 'two skeptics per reported defect' },
  ],
}
const CTX = `
Files (read-only; do not edit anything, do not post anywhere, do not touch remote machines):
- The report under test: /home/jhan/workspace/titan/cache-perf/asimov/run1-report.html (HTML with inline SVG; read the text and the SVG title/text elements).
- The data: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/results/19700101T000000Z/*.csv, log.txt, sysinfo.txt; Jesse Zhang's notes: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-001/README.md.
- The sources that produced the data: /home/jhan/workspace/titan/cache-perf/asimov/{latency.c,bandwidth.c,common.h,run_asimov.sh,README.md}.
- CRB comparison data: /home/jhan/workspace/titan/cache-perf/asimov/crb-validation/20261031T073509Z/.
- Use python3 for every recomputation. Cite file:line for each finding. Return raw data through the schema.
`
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string', description: 'the report sentence or number, quoted' },
      verdict: { type: 'string', enum: ['correct', 'wrong', 'unsupported', 'misleading'] },
      evidence: { type: 'string' },
      fix: { type: 'string', description: 'the corrected sentence or number; empty if correct' },
    }, required: ['claim', 'verdict', 'evidence', 'fix'] } },
    checked_count: { type: 'number', description: 'how many distinct numbers or claims you checked in total' },
  },
  required: ['findings', 'checked_count'],
}
const AREAS = [
  { key: 'latency', prompt: 'Sections "The run", "1. Latency by level" and "8. Open items": recompute every ns, cycle, refill and CSV line reference from the CSVs (best rows, ranges, the 192 KiB L3 arithmetic 0.57/0.46/0.11, the 32 KiB 4 % L1 refills, the SLC run-out past 3 MiB, the flushed-equals-DRAM claim). Check the chart text labels in the first SVG (L1 2.00, L2 6.07, SLC 24.0, DRAM 52.3, flushed 52.7) and the guide lines (32 KiB, 128 KiB, 384 KiB, 3.75 MiB). Check the "The run" bullets against log.txt, sysinfo.txt, SHA256SUMS and Jesse\'s README (1.237 s, 34 commands, 57 min, 2,779 wall s per chip s, arm_cmn_0 present, hugetlb).' },
  { key: 'ocm', prompt: 'Section "2. OCM latency by region" and the second SVG: recompute every best value, the repeat ranges, the L3 refill ranges, the group means and their difference (the report says 3.4 ns est.), the "within 1.5 ns of an SLC hit" claim, the "3.4 times the core caches" arithmetic, and the one-hop/three-hop assignment against Jesse\'s README. Also check the OCM bandwidth table in section 4 (per-region GB/s, all-five rows and their line numbers 7 and 14, write 7.18, copy 11.96, 4-core 66.49 and 29.18).' },
  { key: 'bandwidth', prompt: 'Sections "3. One-core bandwidth" and "4. Bandwidth with more cores" and the third and fourth SVGs: recompute every GB/s, bytes per cycle (28.8 and 16), the per-thread values (8.3 to 9.3, 22.2, 11.0), the pair numbers (115.6, 33.8, 16.9, 17.5, 23.5, 31.9), the "one 64-byte line per 14 cycles" arithmetic, the "2.2 times" latency ratio, and every CSV line reference in the two tables. Check that the fourth SVG uses the 32 MiB row as the 1-thread point of the DRAM panel and says so.' },
  { key: 'method', prompt: 'Sections "5. Problems in run 1", "6. Run 2", "7. Questions for Jesse": verify against bandwidth.c, latency.c, run_asimov.sh and the CSVs. In particular: (a) the OCM write arithmetic: 37.0 us per rep (bandwidth-ocm-write.csv elapsed_s), 8.2 us store time derived from the 32 GB/s DRAM write rate, the remaining 28.8 us as the flush of 4,096 lines = 7.0 ns per line; is the claim that the warm-up pass leaves the region in L2 and L3 supported by bandwidth.c (warm-up pass, flush_after inside the timed region)? (b) the claim that latency.c supports --fresh K together with --flush (timed_walk flushes before each fresh chain) and that run_asimov.sh never combined them; (c) the claim that the 256 KiB flushed rows walk chain 0 which the warm-up walked twice (latency.c run_size); (d) the claim that the CRB flushed 256K rows show 0.15 to 0.38 L1 refills per load (crb-validation latency-dram-flushed.csv); (e) the run 2 list: do the line numbers 110 to 113, 128, 126, 147, 88, 151 match run_asimov.sh; is "about 4 ms of chip time each (est.)" for a 256 KiB --fresh 3 --flush row consistent with latency.c (3 chain builds of 4 touches per line, 2 warm-up walks, 2 timed walks, 2 flushes at the measured 19 to 25 ns per OCM load); is the claim "no C change is needed" true for every listed change; (f) the three questions: does sysinfo.txt already answer any of them (for example CONFIG_DEBUG_FS is not in the grep list, arm_cmn_0 exists); is the TRM statement about OCM-mode CleanInvalid and locked lines quoted correctly (../crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf pages 289 to 292; pypdf may be needed: pip3 install --target into the scratchpad is allowed).' },
]
phase('Check')
const checks = await parallel(AREAS.map(a => () => agent(`${CTX}\nYour area: ${a.key}. ${a.prompt}\nBe exhaustive: every number in your sections gets checked. Report only non-correct items in detail, but count everything in checked_count. Mark "misleading" when a number is right but the sentence around it draws a conclusion the data does not support.`, { label: `check:${a.key}`, phase: 'Check', schema: FINDINGS })))
const areas = checks.map((c, i) => ({ key: AREAS[i].key, result: c })).filter(x => x.result)
const bad = areas.flatMap(a => a.result.findings.filter(f => f.verdict !== 'correct').map(f => ({ ...f, area: a.key })))
log(`checked ${areas.reduce((s, a) => s + a.result.checked_count, 0)} items, ${bad.length} non-correct`)
phase('Refute')
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const judged = await pipeline(bad,
  f => parallel([0, 1].map(k => () => agent(`${CTX}\nA checker says this report claim is ${f.verdict}: "${f.claim}". Evidence: ${f.evidence}. Proposed fix: ${f.fix}.\nTry to REFUTE the checker (lens ${k === 0 ? 'recompute from the CSV yourself' : 'check whether the checker misread the report sentence or the code'}). Default refuted=true if the checker's evidence does not clearly hold.`, { label: `refute:${f.area}:${k}`, phase: 'Refute', schema: VERDICT }))),
  (votes, f) => ({ ...f, survives: votes.filter(Boolean).filter(v => v.refuted).length < 2, votes: votes.filter(Boolean) }))
return { areas: areas.map(a => ({ key: a.key, checked: a.result.checked_count })), defects: judged.filter(Boolean) }