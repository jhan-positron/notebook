export const meta = {
  name: 'verify-renumbered-pr-bodies',
  description: 'Read each new PR body for text that the PR renumbering made wrong, then refute each finding',
  phases: [{ title: 'Review' }, { title: 'Refute' }],
}
const DIR = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/exec/newprs-20261015'
const PRS = [
  { old: 4868, now: 4956, pos: 1 },
  { old: 4887, now: 4957, pos: 2 },
  { old: 4898, now: 4958, pos: 3 },
  { old: 4901, now: 4959, pos: 4 },
]
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  line: { type: 'integer' }, quote: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['line', 'quote', 'problem', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const ctx = `Context: four stacked PRs in positron-ai/tron were closed and re-opened on the SAME branches at the SAME commits so reviewers get a fresh conversation. Mapping old->new PR number: 4868->4956 (PR 1, base main, ready for review), 4887->4957 (PR 2, base jhan-vnnik-1-layout, draft), 4898->4958 (PR 3, base jhan-vnnik-2-amx, draft), 4901->4959 (PR 4, base jhan-vnnik-3-shared-save, draft). The new bodies are the old bodies with only the '#NNNN' PR numbers replaced. Old PRs are CLOSED with a 'Superseded by #new' comment. Issues #4444, #4934, #4955, #4500 are unchanged and keep their numbers.`
const results = await pipeline(PRS,
  p => agent(`${ctx}
Task: read ${DIR}/new/${p.now}.md (the live body of the new PR #${p.now}, position ${p.pos} of 4) and, for comparison, ${DIR}/live/${p.old}.md (the old body). Use Bash (cat -n) to read them.
Find every sentence or table cell in the NEW body that is wrong, misleading or stale BECAUSE of the renumbering or the close/re-open. Examples of what counts: a leftover old PR number or URL (pull/4868 etc.); a reference to a review thread, review comment or review round that lived on the old PR; a stack-table row whose 'this PR' marker, branch, base or status no longer matches position ${p.pos}; a sentence like 'draft until PR #X merges' pointing at the wrong PR; a head commit hash that does not match the branch head (heads: 4956=7ce378934f, 4957=65a9d655ec, 4958=dfafd13dce, 4959=4d64013dff).
Do NOT report wording, style, or content issues that were equally true of the old body and are unaffected by the renumbering. Do not edit any file. Return findings with the line number in the NEW file, the exact quote, the problem, and the fix. Return an empty list if nothing is wrong.`,
    { label: `review:#${p.now}`, phase: 'Review', schema: FINDINGS }),
  (r, p) => r ? parallel(r.findings.map(f => () =>
    agent(`${ctx}
A reviewer claims this sentence in ${DIR}/new/${p.now}.md (new PR #${p.now}, position ${p.pos} of 4) is wrong because of the renumbering:
line ${f.line}: "${f.quote}"
claimed problem: ${f.problem}
proposed fix: ${f.fix}
Try to REFUTE the claim. Read the file with Bash (cat -n, sed -n) and, if useful, 'gh pr view ${p.now} -R positron-ai/tron --json headRefOid,baseRefName,isDraft' or 'gh api repos/positron-ai/tron/pulls/${p.now}/commits --jq ".[].sha"'. refuted=true if the text is still correct as written, or if the problem existed identically in the old body and is unrelated to the renumbering. refuted=false only if the renumbering or re-open really made it wrong. Default to refuted=true if uncertain.`,
      { label: `refute:#${p.now}:L${f.line}`, phase: 'Refute', schema: VERDICT })
      .then(v => ({ ...f, pr: p.now, verdict: v })))) : [])
log('review done')
const all = results.flat().filter(Boolean)
return { confirmed: all.filter(f => f.verdict && !f.verdict.refuted), refuted: all.filter(f => !f.verdict || f.verdict.refuted) }