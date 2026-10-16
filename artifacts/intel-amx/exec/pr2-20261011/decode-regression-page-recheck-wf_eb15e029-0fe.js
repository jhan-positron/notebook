export const meta = {
  name: 'decode-regression-page-recheck',
  description: 'Re-check the regenerated explainer page: plain English, citations vs code, numbers vs results, diagram consistency; refute each finding',
  phases: [{ title: 'Check', detail: 'four lenses' }, { title: 'Verify', detail: 'two refuters per must-fix/should-fix finding' }],
}
const PAGE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/track-decode-regression-by-logits-token-ties-explained.html'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr2'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/p247-20261011'
const CTX = `Context: ${PAGE} is the second version of an explainer page for jhan (an engineer) about the token-247 probe of PR #4887 (PR-2 of the PR 4424 split, tree ${W} at 0ee8671d35). A first check already found and fixed 112 items; report only what is still wrong. Read-only: modify nothing. Report findings only: each with the exact quoted phrase, severity (must-fix | should-fix | nit), the claim, the evidence (file:line or result file) and the corrected text. Plain-English rules: define terms at first use or in the Words list, one claim per sentence, numbers with units and a meaning, citations after a sentence in brackets, no idioms or metaphors, bullets for multi-point paragraphs, short sentences, no semicolons, a Short version of at most three sentences at the top.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { phrase: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] }, claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['phrase', 'severity', 'claim', 'evidence', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'plain', prompt: `Load the skill "plain-english" with the Skill tool and run its Check mode over the prose of ${PAGE} (strip the HTML tags; check paragraphs, lists, tables, figure captions and the text inside the SVG diagrams). Report each remaining violation with the exact phrase and the corrected sentence. ${CTX}` },
  { key: 'facts-code', prompt: `Verify every source citation and code claim of the page against ${W}: cited lines (h/tron/models/model.hpp:1155, :1195, :1224-1227, :3398, :3416, :3508, :3517, :3520-3534, :3537-3539, :3546-3548; h/tron/generation/stats.hpp:16; h/common/top_k_accum.hpp:84-88; src/tron/generation/stats.cpp:133-135; src/tron/generation/context.cpp:136-139; h/tron/kernels/amx_attn_iface.hpp:77-85 and :82-84), the claims about bf16 logits for the tp2 executor, the 320-entry accumulator and its tie rule, the sampler at temperature 0, forced ids replacing the pick, the Logits record written before the dense/sparse branch and before any patch, patch_logits_in_place after the sort, final_embedding declared and read in model.hpp and written by the plugin, the two documented numerics differences, the identity case and the reader (h/tron/kernels/k_vnni.hpp qk_group, VDPBF16PS). Report every statement the code does not support. ${CTX}` },
  { key: 'facts-results', prompt: `Verify every number of the page against the result files: ${RES}/verdict.txt, ${RES}/steps-new-vs-newoff.json (summary; the step-248 row; counts of steps with margin_off_ulps <= 2 and margin_off == 0; min/median/max of frac_changed; median of margin_off_ulps), ${RES}/steps-new-vs-newforced.json, ${RES}/steps-newoff-vs-head.json, ${RES}/tokens.txt, ${RES}/runs.txt, /home/jhan/workspace/intel-AMX/exec/results/pr2-20261011/smoke/cpu-p1024/new.tokens and newoff.tokens (positions 240 to 255, 0-based), /home/jhan/workspace/intel-AMX/exec/results/pr2-20261011/tests-pr2.txt and mutation-result.txt (6,669 assertions in 5 cases; the mutant fails at seed 21, qi 0, t 16), and the September study /home/jhan/workspace/intel-AMX/definitive-decode/token30-results.html (its flip at step 22, the truncation build 0.89 times, the R3c core-count control). Report every mismatch. ${CTX}` },
  { key: 'diagrams', prompt: `Read the three SVG diagrams and the chart in ${PAGE} as a reader would, and check them for: text wider than its box or the viewBox (estimate 6.5 px per character at font-size 12, 7 px at 13), overlapping labels, arrows crossing boxes, legends that do not match what is drawn (count the red bars in the chart SVG and compare with the legend), undefined labels, and agreement with the prose and the result files (${RES}/runs.txt, verdict.txt; the smoke token files for diagram C). Report findings with the exact label text and the correction. ${CTX}` },
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