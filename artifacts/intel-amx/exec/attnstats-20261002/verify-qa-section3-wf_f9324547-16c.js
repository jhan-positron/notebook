export const meta = {
  name: 'verify-qa-section3',
  description: 'Extract claims from the new QA section, refute each with code and data lenses, plain-English check, completeness critic',
  phases: [
    { title: 'Extract', detail: 'one agent lists every checkable claim' },
    { title: 'Refute', detail: 'two refuters per claim: code lens and data lens' },
    { title: 'Check', detail: 'plain-English pass and completeness critic' },
  ],
}

const FRAG = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/31edeaf3-fed2-4688-a6fa-1f5ec7f340d4/scratchpad/section3.html'
const RES = `
Resources (read with cat / sed -n / grep; all paths absolute):
- The draft fragment under review: ${FRAG}
- The page it will be inserted into (sections 1-2 define terms and closed forms): /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare-QA.html
- tron source at the campaign's main commit dd0f942c75: run \`git -C /home/jhan/workspace/ai-runs/tron-main-ro show dd0f942c75:<repo path>\` (e.g. h/tron/models/self_attention.hpp, h/tron/scheduler/full.hpp, h/tron/shard.hpp, h/tron/gof.hpp, h/pos/config.hpp, h/libtron.hpp, h/tron/kernels/amx_attn_iface.hpp). Also \`git -C ... grep -n <pattern> dd0f942c75 -- h src\`. Extracted copies of five files: /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/31edeaf3-fed2-4688-a6fa-1f5ec7f340d4/scratchpad/src/
- Exit reports of the 2026-10-02 campaign: /home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002/exit-reports.txt. Cells begin with a '## <cell>__<attn>__<arm>__rep1' line: gptoss fpga amxoff line 1, amxon 11; l8b p1024 cpu amxoff 21 / amxon 31; l8b p8192 cpu 41 / 51; q3-4b p1024 cpu amxoff 61 / amxon 71; q3-4b p1024 fpga amxoff 81 / amxon 91; q3-4b p8192 fpga amxoff 101 / amxon 111. Within a cell: +3 = decode totals, +4 = decode forwards, +5 = decode per-layer, +6 = prompt totals, +7 = prompt forwards, +8 = prompt per-layer. qwen multiplier 2,304 = 8 users x 8 KV heads x 36 layers; fpga_k_tokens is per query (x 8 KV heads for the software scale).
- The campaign report: /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare.md
- 2026-09-25 page (states, Tables 2-4, section 2.4): /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/counter.html (grep for 'Table 4', '8.5', 'state 5', 'warm')
- 2026-09-22 prefill page (section 6, HBM exhaustion): /home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html
- Tile page (kernel per-page work): /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/Q-K-page-AMX_tile-claude.html
- Arithmetic script (run with python3): /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/subunit.py
Terminology: 'unit' = per (user, KV head, layer); p = P + s - 1 for decode step s = 1..255; GOF = 4 tokens; page = 64 tokens.
`

phase('Extract')
const CLAIMS = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, text: { type: 'string' }, kind: { type: 'string', description: 'code | data | arithmetic | cross-page' },
      where: { type: 'string', description: 'section number and the sentence start' } }, required: ['id', 'text', 'kind', 'where'] } }
  }, required: ['claims']
}
const ex = await agent(`Read the HTML fragment ${FRAG} fully. List every checkable factual claim in it: code behaviour with a cited line, every number (counts, percentages, line references), every statement about what was measured, and every cross-reference to another page or table. Merge sentences that make one claim; keep separate claims separate. Expect 40-70 claims. Give each an id C1.., the exact claim text (short), its kind (code | data | arithmetic | cross-page) and where it sits (section number + first words of the sentence). ${RES}`, { label: 'extract-claims', schema: CLAIMS })
const claims = (ex && ex.claims) ? ex.claims : []
log(`${claims.length} claims extracted`)

phase('Refute')
const VERDICT = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    refuted: { type: 'boolean', description: 'true only when you have evidence that the claim is wrong or imprecise' },
    confidence: { type: 'string', description: 'high | medium | low' },
    evidence: { type: 'string', description: 'what you checked: file:line, exit-report line and field, or the computation' },
    correction: { type: 'string', description: 'if refuted or imprecise: the corrected sentence(s) to use in the fragment; else empty' },
  }, required: ['id', 'refuted', 'confidence', 'evidence', 'correction']
}
const lenses = [
  { name: 'code', instr: 'Your lens is the SOURCE CODE at dd0f942c75: open every cited file:line with git show and confirm the line numbers and the behaviour. For data claims, check at least that the cited counter field exists and that the arithmetic from it is right.' },
  { name: 'data', instr: 'Your lens is the DATA: the exit reports, the campaign report, counter.html, the prefill page and the arithmetic script. Recompute every number from its primary source (run python3 for sums). For code claims, confirm the cited line exists and says what the claim says.' },
]
const results = await pipeline(claims,
  c => parallel(lenses.map(l => () => agent(`Try to REFUTE this claim from a draft Q&A section. ${l.instr}
Claim ${c.id} (${c.kind}, ${c.where}): "${c.text}"
Read the surrounding paragraph in the fragment for context. Report refuted=true only with evidence (a line that says otherwise, a number that recomputes differently, a cited line number that is off, a source that does not contain the fact). A claim that is right but imprecise (wrong unit, missing condition, rounding that misleads) counts as refuted with a correction. If the sources confirm the claim, refuted=false and say what you checked. ${RES}`, { label: `refute:${l.name}:${c.id}`, phase: 'Refute', schema: VERDICT }))),
  (votes, c) => ({ claim: c, votes: votes.filter(Boolean) })
)

phase('Check')
const CHECK = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  rule: { type: 'string' }, original: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string', description: 'high | medium | low' } }, required: ['rule', 'original', 'fix', 'severity'] } } }, required: ['findings'] }
const [english, critic] = await parallel([
  () => agent(`Plain-English CHECK mode on the HTML fragment ${FRAG} (read the plain-english rules in your CLAUDE.md context; the fragment is one section of a page whose 'Words used here' list already defines: page, pending page, ready page, dense page, visit, K tokens, GOF, DMA, AoF, software attention, decode step s, per (user, KV head, layer); the fragment adds shard, engagement point, prompt chunk, unit). List every violation: undefined term at first use, two claims in one sentence, number without unit or meaning, bare citation, idiom or metaphor, paragraph with several points and no bullets, sentence with more than one subordinate clause, semicolons. Give the exact original phrase and a fix. Skip HTML tags. Do not invent violations.`, { label: 'plain-english', phase: 'Check', schema: CHECK }),
  () => agent(`Completeness CRITIC for the HTML fragment ${FRAG}, which answers this question from jhan: "When FPGA attention is enabled, neither prefill nor decode can leverage AMX, right? My understanding of the reason is, the unit of AoF is 4 token while AMX is 64 tokens. So when AoF is on, the pending/tail page can never accumulate to 64 tokens before the first attention. In other words, it is a fruitless thought to lower AMX token numbers from 64 because it is not realistic to lower to 4. Correct?"
Ask: what is missing or wrong at the level of the ARGUMENT? Is any part of the question left unanswered? Is any mechanism asserted without a source? Is there a case under FPGA attention where the CPU does hold a whole page in decode that the fragment misses (check counter.html Table 2 states and section 2.4, and the report's section 2.1)? Does the 'opposite lever' paragraph hold (what happens to the pending page if the card unit were 64)? Is the 'visibility lever' paragraph in 3.3 right about the own-chunk page visits (66 full-page AVX visits per chunk per unit: 64 page-A visits by page-B queries + 2 last-token visits)? Verify with the sources. Return findings with rule = 'argument', original = the passage or 'missing', fix = what to add or change, severity.
${RES}`, { label: 'critic', phase: 'Check', schema: CHECK }),
])
return { n_claims: claims.length, results, english: english ? english.findings : null, critic: critic ? critic.findings : null }