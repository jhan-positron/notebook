export const meta = {
  name: 'verify-prefill-page-v3',
  description: 'Verify the updated qwen3-4b prefill page (measured FPGA curve): numbers vs perf.json, claims, plain English',
  phases: [
    { title: 'Numbers', detail: 'section 5 values and Short version against the perf.json files' },
    { title: 'Claims', detail: 'refute the new claims' },
    { title: 'Prose', detail: 'plain-English check of the new text' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html'
const GEN = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/gen_page.py'
const SEC = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/fpga_section.py'
const ING = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/ingest_fpga.py'
const ROWS = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/fpga-campaign-rows.json'

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string' },
          claim_or_number: { type: 'string' },
          verdict: { type: 'string', description: 'confirmed | wrong | overstated | unverifiable | missing-caveat' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
          severity: { type: 'string', description: 'high | medium | low' },
        },
        required: ['where', 'claim_or_number', 'verdict', 'evidence', 'fix', 'severity'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const RO = `Read-only. Do not modify any file. Local files only. Never ssh anywhere. Use absolute paths (no cd). The page is ${PAGE} (strip tags with sed -e 's/<[^>]*>//g'); its generator is ${GEN}, section 5 comes from ${SEC} which reads ${ROWS} written by ${ING} from the perf.json files under /home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921/<tag>/perf.json (tags fpgabase-pass1, fpgacanon-pass1, canon-pass1, fpgacanon-cold-p4096, fpgacanon-cold-p8192, fpgabase-cold-p4096, fpgabase-cold-p8192) and /home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919/<tag>/perf.json (base-pass1..3, canon-pass1..3, check-8u-p8192). In a perf.json, results[] holds per cell name, ttft_mean (harness, ms) and tps_mean; raw[] holds per cell ttfts_ms (80 values), prompt_tokens, cached_tokens, engine_requests, hwattn_ok, hwattn_unset_ok. Return only the structured object; say 'unverifiable' rather than guess.`

phase('Numbers')
const NUM = [
  { key: 'fpga-cells', prompt: `${RO}
Task: for every FPGA-attention cell (arms fpgabase and fpgacanon, passes and cold cells) recompute from the perf.json files: the harness ttft_mean per cell, the mean of raw ttfts_ms, the prefix-cache share (sum cached_tokens / sum prompt_tokens), engine_requests, hwattn_unset_ok. Compare with ${ROWS} and with the page's section 5 table ("The record: every cell") and the section 5 bullets (cold 8192: CPU 12,743 vs FPGA 6,743 / 6,878; cold 4096: 2,932 / 3,063; warm 8192: 15,764 / 6,929 / 3,681 / 6,662; the per-prompt percent lists; the 1.9x, 2.3x, 4.3x ratios). Also check the campaign facts stated: passes started 2026-09-21 22:35 UTC and ended 2026-09-22 01:17 UTC (driver.log timestamps, status-history.log in the results dir), every cell 20/20/20/20 engine spread, environment checks (hwattn_unset_ok true in FPGA arms, hwattn_ok true in canon-pass1). One finding per checked number or fact.` },
  { key: 'cpu-cells', prompt: `${RO}
Task: recompute the CPU-attention side used in section 5 and the Short version: the canonical arm warm means over the 4 passes (q4b-swattn canon-pass1..3 plus q4b-fpga canon-pass1) per prompt length, the base arm warm means over 3 passes, the cold 1024 values (first cell of every pass: base 674, canon 518), and the 2026-09-19 check cell (check-8u-p8192: 12,743 ms, cold). Compare with ${ROWS} aggregation (fpga_section.aggregate: first cell of a run = cold, others warm) and with the page's section 5 table columns for base and canon and the ratios quoted (AVX 15.8 s vs AMX 6.9 s = 2.3x at 8192 warm; canonical cold 12.7 s). Also verify the claim in the Short version and section 5 that the 2x jhan recalled holds (state the exact ratio warm and, from exec/results/vnnik-20260914/summary.md lines 9-20, the runtron cold ratio at 8192: 121,679 / 53,284 ms). One finding per number.` },
]
const numbers = await parallel(NUM.map(x => () => agent(x.prompt, { label: `numbers:${x.key}`, phase: 'Numbers', schema: FINDINGS })))

phase('Claims')
const CLM = [
  { key: 'refute', prompt: `${RO}
Lens: refute. Read the Short version, section 5 (bullets, hypothesis, reading), section 6 and the new section 7 bullet of the page. For each claim decide whether the data resolve it: "From prompt 1536 up the FPGA wins, and the gap grows with the prompt" (check the fpgacanon vs canon percent list is monotone or not; n = 1 on the FPGA side), "1.9x" (cold 8192, n = 1 each side), "the CPU build behind the FPGA changes the cold number by -2 %" (n = 1), "the two cold FPGA numbers at 8192 agree within 2 %", "prefill would take 1.2x (1024) to 2.6x (7168) longer" for the nightly switching to CPU attention without AMX (recompute from base vs fpgabase), "Decode TPS ... 121 TPS against 60 TPS at 8192" (results tps_mean of fpgacanon-pass1 and canon passes at 8192), the hypothesis paragraph is labelled as hypothesis and its test is concrete, and any sentence that states a direction the data do not resolve. Also check that the page nowhere presents a warm number as a cold one. Return confirmed findings too, so the reader sees what survived.` },
  { key: 'consistency', prompt: `${RO}
Lens: internal consistency and provenance. (a) Does the Short version agree with section 1 (prompt 1024: -1.9 % to +4.6 % for the canonical build) and with section 5 (1024 cold: fpgacanon 520 vs canon 518)? (b) Do the figure 3 end labels (15.8 s, 6.9 s, 6.7 s, 3.7 s) match the table's 8192 warm means? (c) Do section 6's statements about what was run match the results directory (ls /home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921/, status-history.log, outcome.txt) and the runbook /home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921/RUNBOOK.md (second launch = FPGA arms only)? (d) Does the data-files table row for q4b-fpga-20260921 name files that exist? (e) Are the old section 5 sentences about "Insufficient data above 1024" gone everywhere (grep the page for "Insufficient data", "no qwen3-4b run with FPGA attention", "not measured for FPGA attention")? (f) Is the memory of the platformd 0.11 change described correctly in section 6 (named engines default-0..3, ingress ports, test proxy on port 80; check exec/q4b-fpga-20260921/dut.sh and the systems_test README /home/jhan/workspace/ai-runs/systems_test/README.md lines 97-165)?` },
]
const claims = await parallel(CLM.map(x => () => agent(x.prompt, { label: `claims:${x.key}`, phase: 'Claims', schema: FINDINGS })))

phase('Prose')
const prose = await agent(`${RO}
Plain-english Check mode on the NEW text only: the Short version, section 5 (all prose, bullets, captions, hypothesis, reading), section 6, and the section 7 bullet that starts "FPGA-attention cells above prompt 1024". Rules: define terms at first use (the Words list already defines TTFT, TPS, CI, FPGA, deb, prefix cache, cold/warm, platformd, K/V, HBM, DMA, Welch t; anything else new must be defined), one claim per sentence, numbers with units and a plain meaning, estimates labelled est., citations after a sentence, no idioms or uncommon words, bullets for several points, short sentences, no semicolons outside citation brackets, "prompt 1024" never "ctx", never the words convoy / refund / "in disguise" / swept. Report each violation with the exact phrase and a corrected phrase; cap at 30.`, { label: 'prose:plain-english', phase: 'Prose', schema: FINDINGS })

return { numbers, claims, prose }