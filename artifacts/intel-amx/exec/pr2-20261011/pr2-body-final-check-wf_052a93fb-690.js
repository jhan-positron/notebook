export const meta = {
  name: 'pr2-body-final-check',
  description: 'Final check of the filled PR-2 body: numbers against the result files, plain-English rules; refute each finding',
  phases: [{ title: 'Check', detail: 'numbers-vs-results, facts-vs-code, plain English' }, { title: 'Verify', detail: 'two refuters per must-fix/should-fix finding' }],
}
const BODY = '/home/jhan/workspace/intel-AMX/exec/pr2-20261011/pr-body.md'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr2'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/pr2-20261011'
const CELLS = '/home/jhan/workspace/intel-AMX/exec/results/pr2-E-cpu'
const CTX = `Context: ${BODY} is the FILLED description of PR-2 (branch jhan-vnnik-2-amx at 0ee8671d35 in ${W}; diff = git -C ${W} diff jhan-vnnik-1-layout HEAD). Read-only: modify no file. The description rules (PR2-handoff.md section 6 at /home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR2-handoff.md): present tense, no change history or review narration, no "before/after"; measurements keep provenance only (commit id + date); comparators are main at 72308ec90c, PR-1's head 82d05e94be and its kill-switch run only; a pending measurement is its own subsection; no clock times, no paths into the author's workspace, no comparison with another head's assertion counts in Verification; every term defined at first use (the Words table), one claim per sentence, numbers with units, plain English, no idioms, no semicolons, no names of people. Report findings only, each with the exact quoted phrase, severity (must-fix | should-fix | nit), the claim, the evidence (file:line or result file), and the corrected text.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { phrase: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] }, claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['phrase', 'severity', 'claim', 'evidence', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'numbers', prompt: `Check every number and every run-result statement of the body's Measurements, Verification and Open items sections against the result files: ${CELLS}/summary.md (arm and pair rows; the band = max(2 x the larger sd, 0.4 TPS / 0.15 s); inside/beyond), ${CELLS}/rt-results.txt (binaries, sha256, start date), ${RES}/tests-pr2.txt, tests-pr2nd.txt, tests-pr2rm.txt (assertion counts), ${RES}/build-pr2.log, build-pr2nd.log, build-pr2rm.log ("build rc=0 in N s"), ${RES}/mutation-run.out and mutation-result.txt, ${RES}/tests-pr2-t_amx_numerics-killswitch.out, ${RES}/smoke/*/smoke.txt (pair lines, token ids), ${RES}/host-suite-pr2.txt and .log, ${RES}/steps.txt. Also check the arithmetic of the hand-written sentences (for example "117.3 s to 52.0 s, 0.5 s below base's 52.5 s", "from 4.00 s to 3.27 s, 0.10 s above base's 3.17 s", "within 1.3 % of headoff", "0.77 TPS beyond it"). Report every mismatch. ${CTX}` },
  { key: 'facts-code', prompt: `Check the factual statements of "The changes", "Words used here" and the hypothesis paragraph of the Open item on the kill switch against the code in ${W} (src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp incl. Note [AMX attention dispatch] and Note [QK orientation], h/tron/models/self_attention.hpp, h/tron/models/kv_cache.hpp, h/tron/tensor/k_vnni.hpp, h/tron/kernels/k_vnni.hpp, t/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp, t/t_llama_unit.cpp, README.ci.md) and the diff. In particular: the claim that with the kill switch neither binary packs a query or enters the dense page path; the two documented numerics differences between the AMX path and the reader (what does Note [AMX attention dispatch] actually say, and does the reader k_vnni::qk_group use the same PV path as the dotter?); the static_assert list; the probe counters; the poison pattern; the six compile-time checks. Report every statement the code does not support. ${CTX}` },
  { key: 'plain', prompt: `Load the skill "plain-english" with the Skill tool and run its Check mode over ${BODY} (skip the tables' numeric cells). Rules: define a term at first use (the Words table counts as the definition), one claim per sentence (split "because", "since", "which means", "so that", "so", semicolons), numbers carry units and a meaning where the reader cannot judge them, citations follow a sentence in brackets, no idioms or metaphors, bullets for multi-point paragraphs, short sentences. Report the violations with the exact phrase and the corrected sentence; group identical rule violations only when the fix is the same text. ${CTX}` },
]
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (r, l) => { if (!r) { log(`lens ${l.key} returned nothing`); return [] } log(`lens ${l.key}: ${r.findings.length} findings`); return r.findings.map(f => ({ ...f, lens: l.key })) },
  async (fs, l) => {
    const out = []
    for (const f of fs) {
      if (f.severity === 'nit') { out.push({ ...f, kept: true, votes: 'unverified-nit' }); continue }
      const votes = (await parallel(['truth (is the claim true, reading the result files or the code yourself?)', 'rules (does the proposed fix obey the description rules and plain-English rules, and not add a forbidden claim?)'].map(lens => () =>
        agent(`Try to REFUTE this finding through the ${lens} lens; default to refuted=true if uncertain. Finding (lens ${l.key}): phrase "${f.phrase}", severity ${f.severity}. Claim: ${f.claim}. Evidence: ${f.evidence}. Proposed fix: ${f.fix}. ${CTX}`, { label: `verify:${l.key}:${f.phrase.slice(0, 30)}`, phase: 'Verify', schema: VERDICT })))).filter(Boolean)
      out.push({ ...f, kept: votes.length > 0 && votes.every(v => !v.refuted), votes: votes.map(v => (v.refuted ? 'R: ' : 'K: ') + v.reason) })
    }
    return out
  },
)
const all = results.flat().filter(Boolean)
log(`total ${all.length}, kept ${all.filter(f => f.kept).length}`)
return { kept: all.filter(f => f.kept), dropped: all.filter(f => !f.kept) }