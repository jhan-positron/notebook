export const meta = {
  name: 'verify-qa-section3-round2',
  description: 'Round 2: refute the rewritten section (every claim, two lenses), plain-English check, critic',
  phases: [
    { title: 'Extract', detail: 'list checkable claims of the rewritten fragment' },
    { title: 'Refute', detail: 'two refuters per claim' },
    { title: 'Check', detail: 'plain-English pass and completeness critic' },
  ],
}
const FRAG = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/31edeaf3-fed2-4688-a6fa-1f5ec7f340d4/scratchpad/section3.html'
const RES = `
Resources (read with cat / sed -n / grep; all paths absolute):
- The rewritten fragment under review: ${FRAG} (the previous draft, for reference only: ${FRAG.replace('section3.html','section3.v1.html')})
- Findings already applied from round 1 (do not re-report what is now fixed; do check that the fixes are right): /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/31edeaf3-fed2-4688-a6fa-1f5ec7f340d4/scratchpad/findings.txt
- The page it will be inserted into: /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare-QA.html (its 'Words used here' list defines page, pending/ready page, dense page, visit, K tokens, GOF, DMA, AoF, software attention, decode step s and p, per (user, KV head, layer))
- tron source at dd0f942c75: \`git -C /home/jhan/workspace/ai-runs/tron-main-ro show dd0f942c75:<repo path>\` and \`git -C ... grep -n <pattern> dd0f942c75 -- h src\`.
- Exit reports 2026-10-02: /home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002/exit-reports.txt (cells start with '## '; +3 decode totals, +4 decode forwards, +5 decode per-layer, +6 prompt totals, +7 prompt forwards, +8 prompt per-layer; qwen multiplier 2,304; fpga_k_tokens per query, x 8 KV heads for the software scale).
- Exit reports 2026-09-25: /home/jhan/workspace/intel-AMX/exec/results/attnstats-20260925-fpga/exit-reports.txt and /home/jhan/workspace/intel-AMX/exec/results/attnstats-20260925-warm/exit-reports.txt
- Report: /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare.md ; counter.html (same folder); /home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html ; tile page Q-K-page-AMX_tile-claude.html (same folder as the report)
- Script: python3 /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/subunit.py
`
phase('Extract')
const CLAIMS = { type: 'object', properties: { claims: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, text: { type: 'string' }, kind: { type: 'string' }, where: { type: 'string' } }, required: ['id', 'text', 'kind', 'where'] } } }, required: ['claims'] }
const ex = await agent(`Read ${FRAG} fully. List every checkable factual claim: code behaviour with a cited line, every number, every measured statement, every cross-reference. Merge sentences that make one claim. Expect 60-90 claims. Ids C1.., short exact text, kind (code | data | arithmetic | cross-page), where (section + first words). ${RES}`, { label: 'extract', schema: CLAIMS })
const claims = (ex && ex.claims) ? ex.claims : []
log(`${claims.length} claims`)
phase('Refute')
const VERDICT = { type: 'object', properties: { id: { type: 'string' }, refuted: { type: 'boolean' }, confidence: { type: 'string' }, evidence: { type: 'string' }, correction: { type: 'string' } }, required: ['id', 'refuted', 'confidence', 'evidence', 'correction'] }
const lenses = [
  { name: 'code', instr: 'Lens: SOURCE CODE at dd0f942c75. Open every cited file:line and confirm line numbers and behaviour. For data claims check the counter field and the arithmetic.' },
  { name: 'data', instr: 'Lens: DATA. Recompute every number from its primary source (python3 for sums). For code claims confirm the cited line exists and says what the claim says.' },
]
const results = await pipeline(claims,
  c => parallel(lenses.map(l => () => agent(`Try to REFUTE this claim from the rewritten Q&A section. ${l.instr}
Claim ${c.id} (${c.kind}, ${c.where}): "${c.text}"
Read the surrounding paragraph for context. refuted=true only with evidence; an imprecise-but-true claim (missing condition, wrong unit, misleading rounding, wrong line number) counts as refuted with a correction. Keep the correction minimal and in the fragment's plain-English register (short sentences, no semicolons). ${RES}`, { label: `refute:${l.name}:${c.id}`, phase: 'Refute', schema: VERDICT }))),
  (votes, c) => ({ claim: c, votes: votes.filter(Boolean) }))
phase('Check')
const CHECK = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, original: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string' } }, required: ['rule', 'original', 'fix', 'severity'] } } }, required: ['findings'] }
const [english, critic] = await parallel([
  () => agent(`Plain-English CHECK mode on ${FRAG} (rules in your CLAUDE.md context). The page's 'Words used here' list already defines: page, pending page, ready page, dense page, visit, K tokens, GOF, DMA, AoF, software attention, decode step s and the position p, per (user, KV head, layer). The fragment's own words list defines card, K/V, shard, shard base, engagement point, prompt chunk, plan, arm, kill switch, cell, warm, prefix cache, tree node, TPS, TTFT, kv_mul, tile, Q panel, unit. List only real violations with exact original phrase and fix; skip HTML tags and entities (&lt; &amp;). Do not invent violations.`, { label: 'plain-english', phase: 'Check', schema: CHECK }),
  () => agent(`Completeness CRITIC for ${FRAG}, which answers jhan's question (quoted at its top). Check: is every part of the question answered? Any mechanism without a source? Any internal contradiction between sections (numbers that disagree, e.g. 66 vs 64 visits, 1.4 vs 1.5 %)? Does the 3.2 table's six cases match counter.html (sections 2.3/2.4, Tables 2 and 4) and the report? Is anything in the Short answer not supported by the body? Return findings (rule='argument', original=passage or 'missing', fix, severity). ${RES}`, { label: 'critic', phase: 'Check', schema: CHECK }),
])
return { n_claims: claims.length, results, english: english ? english.findings : null, critic: critic ? critic.findings : null }