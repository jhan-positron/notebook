export const meta = {
  name: 'decode-regression-page-final',
  description: 'Final check of the explainer page after the second round of fixes: plain English, citations, diagrams; refute each finding',
  phases: [{ title: 'Check', detail: 'three lenses' }, { title: 'Verify', detail: 'two refuters per must-fix/should-fix finding' }],
}
const PAGE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/track-decode-regression-by-logits-token-ties-explained.html'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr2'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/p247-20261011'
const CTX = `Context: ${PAGE} is the third version of an explainer page for jhan about the token-247 probe of PR #4887 (tree ${W} at 0ee8671d35; results in ${RES}). Two earlier checks found and fixed 173 items; report only what is still wrong, and do not repeat an item whose fix is already in the page. Read-only: modify nothing. Report findings only: each with the exact quoted phrase, severity (must-fix | should-fix | nit), the claim, the evidence (file:line or result file) and the corrected text. Plain-English rules: define terms at first use or in the Words list, one claim per sentence, numbers with units and a meaning, citations after a sentence in brackets, no idioms or metaphors, bullets for multi-point paragraphs, short sentences, no semicolons.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { phrase: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] }, claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['phrase', 'severity', 'claim', 'evidence', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'plain', prompt: `Load the skill "plain-english" with the Skill tool and run its Check mode over the prose of ${PAGE} (strip the HTML tags; include the text inside the SVG diagrams and the tables). Report each remaining violation with the exact phrase and the corrected sentence. ${CTX}` },
  { key: 'facts', prompt: `Verify every citation of the page against ${W} (file:line ranges as written, including h/tron/plugins/llama.hpp:514 and :1308-1309, h/tron/kernels/k_vnni.hpp:53-54, src/tron/generation/context.cpp:50 and :136-139, src/tron/generation/stats.cpp:133-135, h/tron/models/model.hpp:3508, :3517, :3519-3533, :3537-3539, :3546-3548, h/tron/kernels/amx_attn_iface.hpp:49-53, :77-85, :82-84, h/tron/models/common.hpp:79 and :95, h/tron/hardware/btensor.hpp:21, h/common/top_k_accum.hpp:84-88, h/tron/generation/stats.hpp:16) and every number against ${RES} (steps-new-vs-newoff.json, verdict.txt, tokens.txt, runs.txt), /home/jhan/workspace/intel-AMX/exec/results/pr2-20261011/smoke/cpu-p1024/*.tokens, tests-pr2.txt, mutation-result.txt, and /home/jhan/workspace/intel-AMX/definitive-decode/token30-results.html. Report every mismatch. ${CTX}` },
  { key: 'diagrams', prompt: `Read the three SVG diagrams and the chart in ${PAGE} as a reader would and check: text wider than its box or the viewBox (estimate 6.5 px per character at font-size 12, 7 px at 13), overlapping labels, arrows crossing boxes, legends that do not match what is drawn, undefined labels, and agreement with the prose and ${RES}/runs.txt and verdict.txt. Report findings with the exact label text and the correction. ${CTX}` },
]
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (r, l) => { if (!r) { log(`lens ${l.key} returned nothing`); return [] } log(`lens ${l.key}: ${r.findings.length} findings`); return r.findings.map(f => ({ ...f, lens: l.key })) },
  async (fs, l) => {
    const out = []
    for (const f of fs) {
      if (f.severity === 'nit') { out.push({ ...f, kept: true, votes: 'unverified-nit' }); continue }
      const votes = (await parallel(['truth (is the claim true, reading the code, the result files or the page yourself?)', 'rules (does the proposed fix obey the plain-English rules and keep the page accurate?)'].map(lens => () =>
        agent(`Try to REFUTE this finding through the ${lens} lens; default to refuted=true if uncertain. Finding (lens ${l.key}): phrase "${f.phrase}", severity ${f.severity}. Claim: ${f.claim}. Evidence: ${f.evidence}. Proposed fix: ${f.fix}. ${CTX}`, { label: `verify:${l.key}:${f.phrase.slice(0, 30)}`, phase: 'Verify', schema: VERDICT })))).filter(Boolean)
      out.push({ ...f, kept: votes.length > 0 && votes.every(v => !v.refuted), votes: votes.map(v => (v.refuted ? 'R: ' : 'K: ') + v.reason) })
    }
    return out
  },
)
const all = results.flat().filter(Boolean)
log(`total ${all.length}, kept ${all.filter(f => f.kept).length}`)
return { kept: all.filter(f => f.kept), dropped: all.filter(f => !f.kept) }