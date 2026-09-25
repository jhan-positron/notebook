export const meta = {
  name: 'verify-prefill-page',
  description: 'Adversarially verify the qwen3-4b prefill AMX-vs-FPGA page: numbers against source files, claims, mechanism against tron source, plain English',
  phases: [
    { title: 'Numbers', detail: 'each pair re-read from its source file' },
    { title: 'Claims', detail: 'refuters with distinct lenses' },
    { title: 'Mechanism', detail: 'section 4 statements vs tron source' },
    { title: 'Prose', detail: 'plain-English check of the page' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html'
const GEN = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/gen_page.py'
const PAIRS = '/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/pairs.json'

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string', description: 'section / figure / table / pair the finding is about' },
          claim_or_number: { type: 'string' },
          verdict: { type: 'string', description: 'confirmed | wrong | overstated | unverifiable | missing-caveat' },
          evidence: { type: 'string', description: 'file:line and the value or text found there' },
          fix: { type: 'string', description: 'the exact replacement text or number, or empty if confirmed' },
          severity: { type: 'string', description: 'high (changes the answer) | medium (changes a number or a claim) | low (wording)' },
        },
        required: ['where', 'claim_or_number', 'verdict', 'evidence', 'fix', 'severity'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const RO = `Read-only. Do not modify any file. Local files only; never ssh anywhere; use absolute paths (no cd). The page under review is ${PAGE} (strip tags with sed -e 's/<[^>]*>//g' to read the prose, or read the generator ${GEN} which holds every number and sentence). Return only the structured object. Report only what you verified; if you could not open a source, say 'unverifiable', never guess.`

phase('Numbers')
const groups = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
const numberChecks = await parallel(groups.map((g, gi) => () => agent(`${RO}
Task: verify the numbers of pairs ${g.join(', ')} (0-based indexes) in ${PAIRS}. For each pair: (1) open the cpu_ref and fpga_ref source files at the cited lines (and the surrounding rt-results.txt / summary.json / cells/ files of that campaign if the cited line does not carry the per-rep values) and check that cpu_reps and fpga_reps are the values in the source, that the arm identity (attention mode via USE_HW_ATTN or the "HW attention enabled|disabled" log lines, build commit or deb name, kill switch) matches the setup and kernel stated; (2) recompute mean, delta_ms, pct and Welch t from the reps and compare with the json (tolerance 0.05 % and 0.1 in t); (3) check that the same values appear in the page table "The record: every like-for-like pair" and in figure 1 labels (grep the page for the percent strings). Also check the specific claim in the note column for those pairs. Report one finding per pair (confirmed or not) plus any extra finding.`, { label: `numbers:${gi}`, phase: 'Numbers', schema: FINDINGS })))

phase('Claims')
const LENSES = [
  { key: 'confounds', prompt: `Lens: apples-to-apples. For every comparison the page draws (Short version, section 1 bullets, section 2, section 3 paragraph), list what differs between the two sides besides the attention mode (binary, day, client host and its load, log level, kill switch, users per engine, harness, prefix-cache warmth, n) using the campaign files under /home/jhan/workspace/intel-AMX/exec/results/ (summary.md headers, rt-results.txt run headers, caveats.html, RUNBOOK.md, meta.json in cells/). Try to REFUTE each claim: does any confound plausibly account for the stated delta? Default to "overstated" when a confound is as large as the delta and the page does not name it.` },
  { key: 'statistics', prompt: `Lens: statistical resolution. For every delta the page reports (figure 1, tables, Short version ranges), decide whether the data resolve its sign and size: n per side, sd, the Welch t the page gives, n = 1 sides, the night-to-night sd 7.2 / 10.1 ms used as a yardstick. Recompute at least four Welch t values from the per-rep values in the pairs json. Try to REFUTE the Short version sentence "in every like-for-like pair the FPGA arm is within X to Y % of the canonical-AMX arm" and the sentence about VNNI-K "slower in all five pairs": count the pairs in the table and check the ranges are exactly the min and max of the table rows. Flag any sentence that states a direction the data do not resolve without saying so.` },
  { key: 'completeness', prompt: `Lens: what the page leaves out or misclassifies. Compare the page against the full extraction /home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/rows-extracted.json (253 rows): (a) is there any qwen-3-4b CPU-attention vs FPGA-attention pair at prompt 1024 that the page could have used and did not (same campaign or same binary)? (b) is any row in the page classified with the wrong kernel or attention mode according to rows-extracted.json and its file_refs? (c) does the page anywhere present an estimate as a measurement (the 87 % share, the "about 8 forwards" statements, the "removed 182 ms" arithmetic) without labelling it? (d) does the page state the decode-TPS context correctly (20 to 60 % in favour of the FPGA) - check the TPS values in p0perf-20260913/summary.md and vnnik4-models results.txt? (e) does the "Data files" table point at files that exist with the line numbers claimed (ls and sed -n on each)?` },
]
const claimChecks = await parallel(LENSES.map(l => () => agent(`${RO}
${l.prompt}
Return each problem as a finding with the exact page sentence in claim_or_number and a concrete replacement in fix. Also return findings with verdict "confirmed" for the main claims you could not refute, so the reader sees what survived.`, { label: `claims:${l.key}`, phase: 'Claims', schema: FINDINGS })))

phase('Mechanism')
const STANCES = [
  { key: 'confirm', stance: 'Verify each statement with file:line quotes from the trees; mark confirmed / wrong / overstated.' },
  { key: 'refute', stance: 'Try to REFUTE each statement: look for code paths that contradict it (a deployment setting TRON_PER_USER_PROMPT_CHUNK_LIMIT, an ingested-model max_minibatch_size that changes the chunking, a place where the AMX dense predicate could pass inside a prompt chunk, prompt queries below the engagement point being offloaded, DMA awaited inside the forward). Default to "overstated" if the page states as fact something that depends on a runtime setting or on timing.' },
]
const mechChecks = await parallel(STANCES.map(m => () => agent(`${RO}
Section 4 of the page ("What runs where during prefill") makes these statements about tron. Source trees: PR 4424 branch /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K (30c4ac82cb) and main of 2026-09-10 /home/jhan/workspace/ai-runs/tron-main-ro (1279137d). The deployment env of delphi-3bda production engines is pasted at /home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/platformd-instance-1.env.txt and the config.env mechanism is described in /home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919/RUNBOOK.md.
Statements:
S1. A prompt is fed 128 tokens per user per forward pass by default (TRON_PER_USER_PROMPT_CHUNK_LIMIT); a 1024-token prompt is 8 forwards; with 8 runtron users each forward carries 8 x 128 = 1024 prompt tokens and all 8 users finish prefill on the same pass.
S2. With FPGA attention, the queries of forward k are scored on the FPGA against the K/V of forwards 1..k-1 already in HBM; the first forward (positions 0..127, below the engagement point 127) and every query's own 128-token chunk are always scored on the CPU; so is any K/V whose DMA had not completed when the forward was scheduled.
S3. With CPU attention, the AMX page kernel scores the queries of forward k against the full 64-token pages of forwards 1..k-1; the own-chunk causal triangle runs the AVX path in every build.
S4. The FPGA and the AMX kernel therefore replace the same part of the work, about 87 % (est.) of the causal (query, key) pairs of a 1024-token prompt; in an FPGA-attention run the AMX kernel does not touch the prompt's own attention unless DMA lags.
S5. Extra work inside TTFT in the FPGA path: gof::populate staging per 4-token group, 36 DMA descriptors per group per layer, one FPGA pass per 32 queries per layer that re-reads the resident K/V, unpack and join on the attention workers.
S6. (section 5) The CPU AMX path is quadratic in prompt length (one (query, page) pair per kernel call, page reused across the forward's queries); the FPGA path is also quadratic (32 queries per pass, K/V re-read per pass) plus a linear host cost.
S7. (section 3 hypothesis) Under FPGA attention, K/V whose DMA lags is scored on the CPU as dense pages where the AMX kernel applies.
${m.stance} Also recompute the 87 % figure: causal pairs of a 1024-token prompt = 1024*1025/2 = 524,800; within-chunk pairs for 8 chunks of 128 = 8 * 128*129/2 = 66,048; share of cross-chunk pairs = ?`, { label: `mech:${m.key}`, phase: 'Mechanism', schema: FINDINGS })))

phase('Prose')
const prose = await agent(`${RO}
Run the plain-english skill in Check mode on the page prose (strip tags; skip the SVG text and the numeric table cells). Rules: 1 define terms at first use (the page has a "Words used here" list; a term defined there needs no redefinition), 2 one claim per sentence, 3 numbers carry units and a plain meaning and estimates are labelled est., 4 citations follow a sentence in brackets and never replace it, 5 Short version of at most three sentences at the top, 6 no idioms or metaphors or uncommon words, 7 bullets or blank lines between separate points, 8 short sentences and no semicolons. Also the project rule: write "prompt 1024" never "ctx 1024", and never use the words convoy, refund, "in disguise", swept. Report each violation as a finding with the exact phrase and the corrected phrase; severity low unless the meaning changes. Cap at the 40 most important.`, { label: 'prose:plain-english', phase: 'Prose', schema: FINDINGS })

return { numberChecks, claimChecks, mechChecks, prose }