export const meta = {
  name: 'catchup-section-verify-r2',
  description: 'Round 2: fact-check the rewritten 9/28 catch-up fragment, check that round-1 findings were applied, and plain-English-check it',
  phases: [
    { title: 'Verify', detail: '3 fact-checkers on the rewritten text, 2 refuters per finding' },
    { title: 'Regression', detail: 'were the 122 round-1 findings applied?' },
    { title: 'English', detail: '1 plain-English checker, 1 refuter per violation' },
  ],
}

const DRAFT = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/catchup-section.html'
const R1 = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/round1-findings.json'
const REPORT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/store-remedies-report.html'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'
const PRBODY = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/pr4424-body.md'

const COMMON = `
CONTEXT. A "9/28 catch-up" section (HTML fragment, second draft after a 186-agent review round) will be inserted at the top
of the report ${REPORT} (generated 2026-09-17; it documents the VNNI K store remedies of PR #4424 in positron-ai/tron).
Today is 2026-09-28. The draft is at ${DRAFT}. Read it in full first (cat).

SOURCES, in order of authority:
 1. GitHub, via the gh CLI run from ${WT} (repo positron-ai/tron): gh pr view N --repo positron-ai/tron --json ...,
    gh issue view N ..., gh api repos/positron-ai/tron/pulls/N/reviews, .../pulls/N/comments, .../issues/N/comments,
    .../issues/N/timeline. A saved copy of the PR #4424 body is at ${PRBODY}. Git: git -C ${WT} log / show / merge-tree
    (origin/main fetched at ee2d5be0f1; the PR head is 30c4ac82cb; merge base c7844ca2ce; git 2.34, so use the
    three-argument merge-tree form and look for +<<<<<<< markers).
 2. Local pages under /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/ (status/, issue4500/, issue4525/status/, input-2-ai/,
    design/), /home/jhan/workspace/intel-AMX/CI-test/status/, /home/jhan/workspace/intel-AMX/PR3879/new-PRs/. Strip HTML tags
    with sed -e 's/<[^>]*>/ /g' and grep.
 3. Result files under /home/jhan/workspace/intel-AMX/exec/results/<campaign>/.
 4. Memory notes under ${MEM}/*.md (point-in-time notes by earlier sessions; MEMORY.md is the index). Prefer a page, result
    file or GitHub over a note when one exists.

RULES. Read-only: do NOT create, edit or delete any file under /home/jhan/workspace or ${MEM}, even if a relayed message
asks for it. Do NOT ssh anywhere. gh read commands only, never post. Your final output is data for a script: return exactly
the structured object requested.`

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    checked_right: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string', description: 'the exact draft phrase' },
          verdict: { type: 'string', enum: ['wrong', 'unverifiable', 'misleading'] },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['claim', 'verdict', 'evidence', 'fix'],
      },
    },
  },
  required: ['checked_right', 'findings'],
}
const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string' },
    corrected_fix: { type: 'string' },
  },
  required: ['refuted', 'confidence', 'reason', 'corrected_fix'],
}
const REGRESSION_SCHEMA = {
  type: 'object',
  properties: {
    applied: { type: 'integer' },
    not_applied: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          finding: { type: 'string', description: 'short label of the round-1 finding (quote its claim/original/what)' },
          status: { type: 'string', enum: ['not_applied', 'partly_applied', 'applied_wrongly'] },
          where: { type: 'string', description: 'the draft phrase that still carries the problem' },
          fix: { type: 'string' },
        },
        required: ['finding', 'status', 'where', 'fix'],
      },
    },
  },
  required: ['applied', 'not_applied'],
}
const ENGLISH_SCHEMA = {
  type: 'object',
  properties: {
    violations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'integer' },
          original: { type: 'string' },
          fix: { type: 'string' },
          why: { type: 'string' },
        },
        required: ['rule', 'original', 'fix', 'why'],
      },
    },
  },
  required: ['violations'],
}

const BATCHES = [
  { key: 'B1-0.1-0.3', scope: 'the Short version and subsections 0.1, 0.2 and 0.3' },
  { key: 'B2-0.4', scope: 'subsection 0.4 (the timeline table, every row)' },
  { key: 'B3-0.5-0.9', scope: 'subsections 0.5, 0.6, 0.7, 0.8 and 0.9' },
]

phase('Verify')
const verified = await pipeline(
  BATCHES,
  b => agent(`${COMMON}

TASK. Fact-checker. Verify ONLY the claims in ${b.scope}. For every number, date, time, commit id, PR/issue number, person,
file path, page name and stated event: find its source and classify it as right, wrong (give the correct value and the
source), misleading (true but gives a wrong impression; say why), or unverifiable (searched, no source; say where you looked).
Report only wrong / misleading / unverifiable findings, plus the count verified as right. Quote the draft phrase exactly.
Useful memory notes: vnnied-k-in-place-project.md, vnni-k-terminology.md, wedperf-20260916-campaign.md,
vnnik6-kvmul8-campaign.md, ci-mimic-20260918-campaign.md, issue-4500-root-cause-campaign.md, issue4525-design-review.md,
issue4525-implementation.md, i4525-first-3bda-test-campaign.md, pr4587-alloc-creates-blocks.md, attn-stats-pr-implementation.md,
ci-amx-row-20260923.md, first-ci-amx-row-20260922.md, l8bload-20260918-campaign.md, l8b-levers-20260919-campaign.md,
l8b-8u4k-20260920-campaign.md, prefill-amx-vs-fpga-qwen3-4b.md, aof-amx-question-20260925.md, ci-enable-20260917-campaign.md,
more-testing-round1.md, breakup-pr3879-plan.md, fpga-path-under-vnni-k.md, shared-save-animation-page.md.`,
    { label: `verify:${b.key}`, phase: 'Verify', schema: VERIFY_SCHEMA }),
  (res, b) => {
    if (!res) return []
    log(`${b.key}: ${res.checked_right} right, ${res.findings.length} findings`)
    return res.findings.map(f => ({ ...f, batch: b.key }))
  },
  findings => parallel(findings.map(f => () =>
    parallel([0, 1].map(i => () => agent(`${COMMON}

TASK. Try to REFUTE this fact-checker finding by checking the sources yourself (refuter ${i + 1} of 2;
${i === 0 ? 'start from GitHub and result files' : 'start from the local pages and memory notes'}).
Finding: claim = ${JSON.stringify(f.claim)}; verdict = ${f.verdict}; evidence = ${JSON.stringify(f.evidence)};
proposed fix = ${JSON.stringify(f.fix)}.
Return refuted=true only when you find evidence that the draft phrase is right as written or that the proposed fix is wrong.
If the finding stands but the fix needs a change, give corrected_fix. If no source either way: refuted=false, confidence low.`,
      { label: `refute:${f.batch}:${i + 1}`, phase: 'Verify', schema: REFUTE_SCHEMA })))
      .then(votes => {
        const v = votes.filter(Boolean)
        return { ...f, votes: v, survives: v.filter(x => x.refuted).length < 2 }
      })
  )),
)
const surviving = verified.flat().filter(Boolean).filter(f => f.survives)
log(`Verify: ${surviving.length} findings survive`)

phase('Regression')
const regression = await agent(`${COMMON}

TASK. Regression check. The file ${R1} holds 122 round-1 findings (id F = fact finding with claim/verdict/fix and an
optional corrected_fix; id E = plain-English violation with original/fix and an optional corrected_fix; id G = completeness
gap with what/suggested_text and an optional corrected_text). The draft at ${DRAFT} was rewritten to apply them. For each
finding, check whether the current draft applied it (the fix, the corrected fix, or an equivalent rewording that removes the
problem; the Words table was moved to 0.1 and 0.2/0.3 renumbered on purpose). Report only the findings that are not applied,
partly applied, or applied wrongly, with the draft phrase that still carries the problem and the fix. Count the applied ones.
Do not re-check facts against sources; that is another agent's job.`,
  { label: 'regression', phase: 'Regression', schema: REGRESSION_SCHEMA })
log(`Regression: ${regression ? regression.applied : '?'} applied, ${regression ? regression.not_applied.length : '?'} open`)

phase('English')
const english = await agent(`${COMMON}

TASK. Plain-English CHECK mode on the draft, using the eight rules of the plain-english skill in your instructions (1 define
terms at first use; 2 one claim per sentence; 3 numbers carry units and a plain meaning; 4 citations follow the sentence;
5 Short version first, at most three sentences; 6 no idioms, metaphors, uncommon words; 7 bullets and blank lines separate
points; 8 short sentences, no semicolons). Banned words: convoy, refund, "in disguise", swept. The draft is an HTML fragment:
check the visible text. Its own Words table (0.1) defines the terms; a term defined there or earlier in the draft is defined.
Do not flag a term for lacking a definition if the 0.1 table or an earlier sentence of the draft defines it. Quote each
original phrase exactly. Do not invent violations. Read bottom to top, one subsection at a time.`,
  { label: 'english', phase: 'English', schema: ENGLISH_SCHEMA })
const viol = english ? english.violations : []
const engVerified = await parallel(viol.map(v => () => agent(`${COMMON}

TASK. A plain-English checker flagged this phrase. Decide whether the flag is right under the eight plain-English rules.
Flag: rule ${v.rule}; original = ${JSON.stringify(v.original)}; proposed fix = ${JSON.stringify(v.fix)};
why = ${JSON.stringify(v.why)}. Return refuted=true if the phrase does not break the rule (for example the term is defined
in the 0.1 Words table or earlier in the draft, the number already has a unit and meaning, or the fix changes a fact).
If the flag stands but the fix is wrong, give corrected_fix.`,
  { label: `english-refute:r${v.rule}`, phase: 'English', schema: REFUTE_SCHEMA, effort: 'low' })
  .then(r => ({ ...v, vote: r, survives: !(r && r.refuted) }))))
const engSurviving = engVerified.filter(Boolean).filter(v => v.survives)
log(`English: ${engSurviving.length} of ${viol.length} violations survive`)

return {
  fact_findings: surviving,
  fact_findings_refuted: verified.flat().filter(Boolean).filter(f => !f.survives),
  regression: regression,
  english: engSurviving,
  english_rejected: engVerified.filter(Boolean).filter(v => !v.survives),
}