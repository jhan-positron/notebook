export const meta = {
  name: 'verify-qa-section3-round3',
  description: 'Round 3: refute only the sentences changed between v2 and v3 of the section, plus a final plain-English check',
  phases: [
    { title: 'Diff', detail: 'list changed or new claims' },
    { title: 'Refute', detail: 'one refuter per changed claim' },
    { title: 'Check', detail: 'plain-English pass' },
  ],
}
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/31edeaf3-fed2-4688-a6fa-1f5ec7f340d4/scratchpad/'
const RES = `
Resources (absolute paths):
- v3 (under review): ${S}section3.html ; v2 (previous): ${S}section3.v2.html ; round-2 findings that drove the changes: ${S}findings2.txt
- tron source at dd0f942c75: \`git -C /home/jhan/workspace/ai-runs/tron-main-ro show dd0f942c75:<repo path>\` and \`git -C ... grep -n <pattern> dd0f942c75 -- h src\`
- Exit reports 2026-10-02: /home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002/exit-reports.txt (cells start '## '; +3 decode totals, +4 decode forwards, +5 decode per-layer, +6 prompt totals, +7 prompt forwards; qwen multiplier 2,304; fpga_k_tokens per query)
- Exit reports 2026-09-25: /home/jhan/workspace/intel-AMX/exec/results/attnstats-20260925-fpga/exit-reports.txt and .../attnstats-20260925-warm/exit-reports.txt
- Report /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare.md ; counter.html (same folder) ; /home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html ; tile page Q-K-page-AMX_tile-claude.html
- Script: python3 /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/subunit.py
`
phase('Diff')
const CLAIMS = { type: 'object', properties: { claims: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, text: { type: 'string' }, where: { type: 'string' } }, required: ['id', 'text', 'where'] } } }, required: ['claims'] }
const ex = await agent(`Compare ${S}section3.v2.html with ${S}section3.html (run: diff <(sed 's/>/>\\n/g' v2) <(sed 's/>/>\\n/g' v3)). List every claim that is NEW or CHANGED in v3: each number, line reference, mechanism statement or cross-reference that differs from v2. Ids D1.., short exact text, where (section + first words). Expect 30-50. ${RES}`, { label: 'diff-claims', schema: CLAIMS })
const claims = (ex && ex.claims) ? ex.claims : []
log(`${claims.length} changed claims`)
phase('Refute')
const VERDICT = { type: 'object', properties: { id: { type: 'string' }, refuted: { type: 'boolean' }, confidence: { type: 'string' }, evidence: { type: 'string' }, correction: { type: 'string' } }, required: ['id', 'refuted', 'confidence', 'evidence', 'correction'] }
const results = await pipeline(claims,
  c => agent(`Try to REFUTE this changed claim in v3 of the Q&A section, with BOTH lenses: open the cited source lines at dd0f942c75 and recompute the numbers from the primary data (python3). Claim ${c.id} (${c.where}): "${c.text}". Read its paragraph in ${S}section3.html for context. refuted=true only with evidence; imprecise-but-true (missing condition, wrong unit, wrong line span) counts as refuted with a minimal correction in plain English (short sentences, no semicolons). ${RES}`, { label: `refute:${c.id}`, phase: 'Refute', schema: VERDICT }),
  (v, c) => ({ claim: c, vote: v }))
phase('Check')
const CHECK = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, original: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string' } }, required: ['rule', 'original', 'fix', 'severity'] } } }, required: ['findings'] }
const english = await agent(`Plain-English CHECK mode on ${S}section3.html (rules in your CLAUDE.md context). Already defined on the page: page, pending/ready page, dense page, visit, K tokens, GOF, DMA, AoF, software attention, decode step s and p, per (user, KV head, layer). Defined in the fragment's own words list: card, K/V, shard, shard base, engagement point, prompt chunk, plan, range builder, arm, kill switch, cell, warm, prefix cache, tree node, edge, TPS, TTFT, kv_mul, rinzler, join wait, tile, Q panel, unit. Semicolons inside bracketed citation lists are the page's convention and are not violations. Report only real violations with exact phrase and fix. Do not invent violations.`, { label: 'plain-english', phase: 'Check', schema: CHECK })
return { n: claims.length, results, english: english ? english.findings : null }