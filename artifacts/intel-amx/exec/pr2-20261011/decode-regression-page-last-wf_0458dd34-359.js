export const meta = {
  name: 'decode-regression-page-last',
  description: 'Last light check of the explainer page after the third round of fixes: plain English and the facts of the new sentences',
  phases: [{ title: 'Check', detail: 'two lenses' }, { title: 'Verify', detail: 'two refuters per must-fix/should-fix finding' }],
}
const PAGE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/track-decode-regression-by-logits-token-ties-explained.html'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr2'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/p247-20261011'
const CTX = `Context: ${PAGE} is the fourth version of an explainer page for jhan about the token-247 probe of PR #4887 (tree ${W} at 0ee8671d35; results in ${RES}; the September study at /home/jhan/workspace/intel-AMX/definitive-decode/token30-results.html). Three earlier checks found and fixed 206 items; report only what is still wrong, and only must-fix or should-fix items (skip nits). Read-only: modify nothing. Report findings only: each with the exact quoted phrase, severity, the claim, the evidence (file:line or result file) and the corrected text. Plain-English rules: define terms at first use or in the Words list, one claim per sentence, numbers with units and a meaning, citations after a sentence in brackets, no idioms or metaphors, no semicolons.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { phrase: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] }, claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['phrase', 'severity', 'claim', 'evidence', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'plain', prompt: `Load the skill "plain-english" with the Skill tool and run its Check mode over the prose of ${PAGE} (strip the HTML tags; include the text inside the SVG diagrams and the tables). Report only must-fix and should-fix violations with the exact phrase and the corrected sentence. ${CTX}` },
  { key: 'facts', prompt: `Verify the sentences that were added or changed in this version against the sources: (1) the statistics of step 248 in sections 3 and 2 (mean change 0.040 vs median 0.038; largest change 0.171 vs median about 0.19, at token 105663; fraction changed 96 % at about the 93rd percentile; TVD 0.030 the second highest of 256 steps, median about 0.0012) against ${RES}/steps-new-vs-newoff.json; (2) the September study claims (the Attn out record excluded as unreliable because it differed between two identical AMX-off runs; at WO of layer 0 the rounding term about 30 times the add-order term; equal end to end; its AVX path the row-major dotter; flips at steps 22 and 37 in 64 compared steps) against /home/jhan/workspace/intel-AMX/definitive-decode/token30-results.html; (3) the mutation description (the kernel reads token block 2's panels where it should read block 1) against /home/jhan/workspace/intel-AMX/exec/pr2-20261011/chain.sh and ${W}/src/tron/kernels/amx_attn.cpp; (4) the record-label sentence (every line "<label> of token N"; the filter keeps 768 lines) against ${W}/h/tron/models/model.hpp:1319-1330 and ${RES}/runs.txt; (5) the dotter-as-reference sentence (QK only; PV against an exactly rounded weight reference) against ${W}/t/t_amx_numerics.cpp. Report every mismatch. ${CTX}` },
]
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (r, l) => { if (!r) { log(`lens ${l.key} returned nothing`); return [] } log(`lens ${l.key}: ${r.findings.length} findings`); return r.findings.filter(f => f.severity !== 'nit').map(f => ({ ...f, lens: l.key })) },
  async (fs, l) => {
    const out = []
    for (const f of fs) {
      const votes = (await parallel(['truth (is the claim true, reading the sources yourself?)', 'rules (does the proposed fix obey the plain-English rules and keep the page accurate?)'].map(lens => () =>
        agent(`Try to REFUTE this finding through the ${lens} lens; default to refuted=true if uncertain. Finding (lens ${l.key}): phrase "${f.phrase}", severity ${f.severity}. Claim: ${f.claim}. Evidence: ${f.evidence}. Proposed fix: ${f.fix}. ${CTX}`, { label: `verify:${l.key}:${f.phrase.slice(0, 30)}`, phase: 'Verify', schema: VERDICT })))).filter(Boolean)
      out.push({ ...f, kept: votes.length > 0 && votes.every(v => !v.refuted), votes: votes.map(v => (v.refuted ? 'R: ' : 'K: ') + v.reason) })
    }
    return out
  },
)
const all = results.flat().filter(Boolean)
log(`total ${all.length}, kept ${all.filter(f => f.kept).length}`)
return { kept: all.filter(f => f.kept), dropped: all.filter(f => !f.kept) }