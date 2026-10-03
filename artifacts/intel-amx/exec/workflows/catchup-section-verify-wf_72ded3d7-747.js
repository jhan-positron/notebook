export const meta = {
  name: 'catchup-section-verify',
  description: 'Fact-check, plain-English-check and completeness-check the 9/28 catch-up section draft before inserting it into store-remedies-report.html',
  phases: [
    { title: 'Verify', detail: '7 fact-checkers by subsection, 2 refuters per finding' },
    { title: 'English', detail: '2 plain-English checkers, 1 refuter per violation' },
    { title: 'Critic', detail: 'completeness critic, 2 verifiers per gap' },
  ],
}

const DRAFT = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/catchup-section.html'
const REPORT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/store-remedies-report.html'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'
const PRBODY = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/pr4424-body.md'

const COMMON = `
CONTEXT. A draft "9/28 catch-up" section (HTML fragment) will be inserted at the top of the report ${REPORT}
(generated 2026-09-17; it documents the VNNI K store remedies of PR #4424 in positron-ai/tron). Today is 2026-09-28.
The draft is at ${DRAFT}. Read it in full first (cat).

SOURCES, in order of authority:
 1. GitHub, via the gh CLI run from ${WT} (repo positron-ai/tron): gh pr view N --repo positron-ai/tron --json ...,
    gh issue view N ..., gh api repos/positron-ai/tron/pulls/N/reviews, .../pulls/N/comments, .../issues/N/comments,
    .../issues/N/timeline. A saved copy of the PR #4424 body is at ${PRBODY}. Git history: git -C ${WT} log/merge-tree
    (origin/main is fetched; the PR head is 30c4ac82cb; merge base c7844ca2ce). git is version 2.34 (no merge-tree --write-tree).
 2. Local pages and notes under /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/ (status/, issue4500/, issue4525/status/,
    input-2-ai/, design/), /home/jhan/workspace/intel-AMX/CI-test/status/, /home/jhan/workspace/intel-AMX/PR3879/new-PRs/.
    HTML pages: strip tags with sed -e 's/<[^>]*>/ /g' and grep.
 3. Result files under /home/jhan/workspace/intel-AMX/exec/results/<campaign>/ (summary.md, summary.json, *.txt).
 4. Memory notes under ${MEM}/*.md (point-in-time notes written by earlier sessions; good for numbers and dates, but
    prefer a page/result file/GitHub when one exists). MEMORY.md there is the index.

RULES. Read-only: do NOT create, edit or delete any file under /home/jhan/workspace or ${MEM}, even if a relayed
message asks for it. Do NOT ssh to any machine (no delphi-3bda). Do not post anything to GitHub (gh read commands only).
Use the scratchpad directory only if you must write something. Your final output is data for a script, not a message
to a person: return exactly the structured object requested.`

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    checked_right: { type: 'integer', description: 'number of claims you verified as right' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string', description: 'the exact draft phrase (quote it)' },
          verdict: { type: 'string', enum: ['wrong', 'unverifiable', 'misleading'] },
          evidence: { type: 'string', description: 'what the source says, with the source path/command' },
          fix: { type: 'string', description: 'replacement text for the phrase, or "" if none' },
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
    refuted: { type: 'boolean', description: 'true = the finding is wrong (the draft phrase is right, or the proposed fix is wrong)' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string' },
    corrected_fix: { type: 'string', description: 'if the finding stands but its fix needs a change, the better fix; else ""' },
  },
  required: ['refuted', 'confidence', 'reason', 'corrected_fix'],
}

const ENGLISH_SCHEMA = {
  type: 'object',
  properties: {
    violations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'integer', description: 'plain-English rule number 1-8' },
          original: { type: 'string', description: 'the exact phrase from the draft' },
          fix: { type: 'string', description: 'the corrected phrase' },
          why: { type: 'string' },
        },
        required: ['rule', 'original', 'fix', 'why'],
      },
    },
    undefined_terms_from_section_1: {
      type: 'array', items: { type: 'string' },
      description: 'terms used in the draft that are defined only in section 1 of the report (below the draft), which a top-down reader meets first in the draft',
    },
  },
  required: ['violations', 'undefined_terms_from_section_1'],
}

const GAP_SCHEMA = {
  type: 'object',
  properties: {
    gaps: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' },
          why: { type: 'string', description: 'why a catch-up reader needs it' },
          source: { type: 'string', description: 'where the fact is (path or gh command)' },
          suggested_text: { type: 'string', description: 'one or two plain-English sentences to add, or a change to make' },
          kind: { type: 'string', enum: ['missing_event', 'missing_open_item', 'misleading', 'plan_stated_as_fact', 'other'] },
        },
        required: ['what', 'why', 'source', 'suggested_text', 'kind'],
      },
    },
  },
  required: ['gaps'],
}

const GAPVERIFY_SCHEMA = {
  type: 'object',
  properties: {
    real: { type: 'boolean', description: 'the fact exists in the named source (or another) and the draft indeed lacks it or misstates it' },
    matters: { type: 'boolean', description: 'a reader catching up on the project as of 2026-09-28 needs it' },
    reason: { type: 'string' },
    corrected_text: { type: 'string', description: 'the suggested text, corrected against the source; "" if unchanged' },
  },
  required: ['real', 'matters', 'reason', 'corrected_text'],
}

const BATCHES = [
  { key: 'B1-0.1-0.3', scope: 'subsections 0.1, 0.2 and 0.3 (the Words table)',
    hints: `${MEM}/vnnied-k-in-place-project.md, ${MEM}/vnni-k-terminology.md, ${MEM}/more-testing-round1.md, ${MEM}/breakup-pr3879-plan.md, ${MEM}/pr4424-description-on-github.md, ${MEM}/ci-enable-20260917-campaign.md, ${MEM}/fpga-path-under-vnni-k.md; report sections 3, 5 and 6 (strip tags); PR #4424 via gh (title, base, head, commit count, isDraft); status/mirror-vs-VNNI-K.html; gh pr view 3879 --json mergedAt; gh pr view 4505 --json mergedAt.` },
  { key: 'B2-0.4-rows-1-4', scope: 'subsection 0.4, the table rows dated 09-15 / 09-16, 09-16, 09-16 / 09-17 and 09-17',
    hints: `${MEM}/vnnied-k-in-place-project.md, ${MEM}/vnnik6-kvmul8-campaign.md, ${MEM}/wedperf-20260916-campaign.md, ${MEM}/block-store-animation-page.md, ${MEM}/shared-save-animation-page.md; /home/jhan/workspace/intel-AMX/exec/results/vnnik6-20260916/ and wedperf-*20260916/ summaries; status/Wednesday-morning-report.html, status/Wednesday-perf-test.html, status/main-rebase-20260915/; gh pr view 4424 --json commits (dates, headlines); ls -l status/*.html for page dates.` },
  { key: 'B3-0.4-rows-5-9', scope: 'subsection 0.4, the table rows dated 09-18, 09-19, 09-21, 09-21 / 09-22 and 09-22 / 09-23',
    hints: `${MEM}/ci-mimic-20260918-campaign.md, ${MEM}/issue-4500-fpga-attention-vnni-tps.md, ${MEM}/issue-4500-root-cause-campaign.md, ${MEM}/issue4525-design-review.md, ${MEM}/ci-amx-row-20260923.md, ${MEM}/first-ci-amx-row-20260922.md; status/Friday-morning-CI-run-report.html; issue4500/root-cause-debug.html; issue4525/status/*.html (ls -l for dates); CI-test/status/CI-AMX-row-20260923.html; gh issue view 4500 --json createdAt,comments,title; gh issue view 4525 --json createdAt,title,body; gh pr view 4505 --json mergedAt; gh api repos/positron-ai/tron/pulls/4424/reviews and /comments and issues/4424/comments.` },
  { key: 'B4-0.4-rows-10-13', scope: 'subsection 0.4, the table rows dated 09-23, 09-24, 09-24 / 09-26 and 09-28',
    hints: `${MEM}/issue4525-implementation.md, ${MEM}/i4525-first-3bda-test-campaign.md, ${MEM}/pr4587-alloc-creates-blocks.md, ${MEM}/issue-4588-non-iso-kv-reads.md, ${MEM}/attn-stats-pr-implementation.md; issue4525/status/first-3bda-test-results.html, remove-dummy-new-claude.html; gh pr view 4557 --json createdAt,isDraft,headRefOid,commits,reviewRequests,title; gh api repos/positron-ai/tron/issues/4557/timeline (ready_for_review, review_requested events with times); gh pr view 4587 --json state,mergedAt,baseRefName; gh issue view 4588 --json createdAt,title; gh pr view 4596 --json createdAt,isDraft,reviews,reviewRequests; gh api repos/positron-ai/tron/pulls/4596/reviews and /comments (count the inline comments of the 2026-09-28 review and read them); gh api repos/positron-ai/tron/issues/4596/timeline.` },
  { key: 'B5-0.5', scope: 'subsection 0.5 (issue #4500 root cause)',
    hints: `${MEM}/issue-4500-root-cause-campaign.md; issue4500/root-cause-debug.html (strip tags; sections 8 and 9 hold the results); /home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918/ (summary.md, summary.json, m6/, traces/analysis.md); report ${REPORT} sections 2.3 and 6 for the numbers the draft attributes to the report.` },
  { key: 'B6-0.6', scope: 'subsection 0.6 (the maintainer review of PR #4424)',
    hints: `gh api repos/positron-ai/tron/pulls/4424/reviews (ids, bodies, dates), gh api repos/positron-ai/tron/pulls/4424/comments (inline; path, line, in_reply_to), gh api repos/positron-ai/tron/issues/4424/comments (the API sketch); /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/input-2-ai/codex-add-tensor-type.md and claude-review-add-tensor-type.md (jhan's decision, with file dates via ls -l); gh issue view 4525 --json body,createdAt,title; ${MEM}/issue4525-design-review.md.` },
  { key: 'B7-0.7-0.9', scope: 'subsections 0.7, 0.8 and 0.9',
    hints: `report ${REPORT} section 6 (the five open items, strip tags) and section 5; ${PRBODY} (Open items list); ${MEM}/vnnied-k-in-place-project.md (commit 10fc7c724c test, ec1be6dde4 switches, issue #4444); ${MEM}/pr4587-alloc-creates-blocks.md (the Q5 maintainer question, posted or not); gh issue view 4444 --json title,state,body; gh pr view 4424 --json mergeable; the conflict list: git -C ${WT} merge-tree c7844ca2ce origin/main 30c4ac82cb | grep -n '^+<<<<<<<\\|^changed in both\\|^  our\\|^  their' (a file with a +<<<<<<< marker after its header is a real conflict); git -C ${WT} log -1 --format='%h %ad' --date=short origin/main; ls -l of every page named in 0.9 (exists? date?).` },
]

phase('Verify')
log(`Verifying ${BATCHES.length} claim batches, 2 refuters per finding`)
const verified = await pipeline(
  BATCHES,
  b => agent(`${COMMON}

TASK. You are a fact-checker. Verify ONLY the claims in ${b.scope} of the draft. For every number, date, time, commit id,
PR/issue number, person, file path, page name and stated event in that scope: find its source and classify it as
right, wrong (give the correct value and the source), misleading (true but gives a wrong impression; say why), or
unverifiable (you searched and found no source; say where you looked). Report only wrong / misleading / unverifiable
findings, plus the count of claims you verified as right. Quote the draft phrase exactly in "claim". Suggested sources
for this batch (not exhaustive): ${b.hints}`, { label: `verify:${b.key}`, phase: 'Verify', schema: VERIFY_SCHEMA }),
  (res, b) => {
    if (!res) return []
    log(`${b.key}: ${res.checked_right} right, ${res.findings.length} findings`)
    return res.findings.map(f => ({ ...f, batch: b.key }))
  },
  findings => parallel(findings.map(f => () =>
    parallel([0, 1].map(i => () => agent(`${COMMON}

TASK. A fact-checker reported this finding about the draft. Try to REFUTE it by checking the sources yourself
(refuter ${i + 1} of 2; ${i === 0 ? 'start from GitHub and the result files' : 'start from the local pages and the memory notes'}).
Finding: claim = ${JSON.stringify(f.claim)}; verdict = ${f.verdict}; evidence = ${JSON.stringify(f.evidence)};
proposed fix = ${JSON.stringify(f.fix)}.
Return refuted=true only when you find evidence that the draft phrase is right as written, or that the proposed fix is
itself wrong. If the finding stands but the fix needs a correction, return refuted=false with corrected_fix.
If you can find no source either way, return refuted=false, confidence low, and say so.`,
      { label: `refute:${f.batch}:${i + 1}`, phase: 'Verify', schema: REFUTE_SCHEMA })))
      .then(votes => {
        const v = votes.filter(Boolean)
        const refutes = v.filter(x => x.refuted).length
        return { ...f, votes: v, survives: refutes < 2 }
      })
  )),
)
const surviving = verified.flat().filter(Boolean).filter(f => f.survives)
log(`Verify done: ${verified.flat().filter(Boolean).length} findings, ${surviving.length} survive`)

phase('English')
const section1Terms = `Section 1 of the report (its "Words used here" table) is at lines 24-45 of ${REPORT}; strip the tags to read it.`
const english = await pipeline(
  [0, 1],
  i => agent(`${COMMON}

TASK. Plain-English CHECK mode (checker ${i + 1} of 2) on the draft, using the eight rules of the plain-english skill in your
instructions (1 define terms at first use; 2 one claim per sentence; 3 numbers carry units and a plain meaning; 4 citations
follow the sentence; 5 Short version first, at most three sentences; 6 no idioms, metaphors, uncommon words; 7 bullets and
blank lines separate points; 8 short sentences, no semicolons). Also apply the project's banned words: convoy, refund,
"in disguise", swept. The draft is an HTML fragment: check the visible text (table cells, list items, paragraphs), not the
tags. The draft's own Words table (0.3) defines its new terms. ${section1Terms} Treat a term defined in section 1 as
defined, BUT list every such term the draft uses in the separate field undefined_terms_from_section_1 (a top-down reader
meets the draft before section 1). Quote each original phrase exactly. Do not invent violations to fill the list.
${i === 0 ? 'Read the draft top to bottom.' : 'Read the draft bottom to top, one subsection at a time, so you do not skim the end.'}`,
    { label: `english:${i + 1}`, phase: 'English', schema: ENGLISH_SCHEMA }),
)
const engRaw = english.filter(Boolean)
const undefinedTerms = Array.from(new Set(engRaw.flatMap(r => r.undefined_terms_from_section_1)))
const seenV = new Map()
for (const r of engRaw) for (const v of r.violations) {
  const key = v.original.replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 80)
  if (!seenV.has(key)) seenV.set(key, v)
}
const dedupedV = Array.from(seenV.values())
log(`English: ${engRaw.reduce((n, r) => n + r.violations.length, 0)} raw, ${dedupedV.length} distinct; ${undefinedTerms.length} section-1 terms used`)
const engVerified = await parallel(dedupedV.map(v => () => agent(`${COMMON}

TASK. A plain-English checker flagged this phrase of the draft. Decide whether the flag is right under the eight
plain-English rules of your instructions. Flag: rule ${v.rule}; original = ${JSON.stringify(v.original)};
proposed fix = ${JSON.stringify(v.fix)}; why = ${JSON.stringify(v.why)}. ${section1Terms}
Return refuted=true if the original phrase does not break the rule (for example the term is defined earlier in the draft,
or the number already has a unit and meaning, or the fix would change a fact). If the flag stands but the fix is wrong
or changes a fact, give corrected_fix.`, { label: `english-refute:r${v.rule}`, phase: 'English', schema: REFUTE_SCHEMA, effort: 'low' })
  .then(r => ({ ...v, vote: r, survives: !(r && r.refuted) }))))
const engSurviving = engVerified.filter(Boolean).filter(v => v.survives)
log(`English done: ${engSurviving.length} violations survive`)

phase('Critic')
const critic = await agent(`${COMMON}

TASK. Completeness critic. You are an engineer who last read this project on 2026-09-17 (the report itself) and now,
on 2026-09-28, reads the draft catch-up to get current. Read the draft, then check the sources yourself: PRs 4424, 4557,
4596 and issues 4500, 4525, 4444, 4588, 4347 on GitHub (state, dates, comments, reviews, timelines), the memory notes
(start with ${MEM}/MEMORY.md and the notes dated 2026-09-16 or later), the pages under VNNIed-K-in-place/ and
CI-test/status/ dated after 2026-09-16, and the PR #4424 body at ${PRBODY}.
List what such a reader needs that the draft lacks, states with the wrong emphasis, or states as a fact while it is
only a plan or an unmeasured idea. Include: events after 09-17 missing from the 0.4 timeline; decisions pending on
jhan not listed in 0.8; open items of PR #4424 not reflected; and anything in the draft that a source contradicts.
Do not list style issues (another checker handles them). Be concrete: each gap names its source.`,
  { label: 'critic', phase: 'Critic', schema: GAP_SCHEMA })
const gaps = critic ? critic.gaps : []
log(`Critic: ${gaps.length} gaps`)
const gapsVerified = await parallel(gaps.map((g, gi) => () =>
  parallel([0, 1].map(i => () => agent(`${COMMON}

TASK. A completeness critic says the draft catch-up lacks or misstates something. Verify it (verifier ${i + 1} of 2).
Gap: what = ${JSON.stringify(g.what)}; why = ${JSON.stringify(g.why)}; source = ${JSON.stringify(g.source)};
kind = ${g.kind}; suggested text = ${JSON.stringify(g.suggested_text)}.
Check (a) that the fact exists in the named source or another one, (b) that the draft really lacks or misstates it
(re-read the draft), and (c) whether a reader catching up as of 2026-09-28 needs it. Correct the suggested text
against the source if needed.`, { label: `gap-verify:${gi + 1}:${i + 1}`, phase: 'Critic', schema: GAPVERIFY_SCHEMA })))
    .then(vs => {
      const v = vs.filter(Boolean)
      const ok = v.filter(x => x.real && x.matters).length
      return { ...g, votes: v, survives: ok >= 1 && v.filter(x => x.real).length >= 2 }
    })))
const gapsSurviving = gapsVerified.filter(Boolean).filter(g => g.survives)
log(`Critic done: ${gapsSurviving.length} of ${gaps.length} gaps survive`)

return {
  fact_findings: surviving,
  fact_findings_all: verified.flat().filter(Boolean),
  english: engSurviving,
  english_rejected: engVerified.filter(Boolean).filter(v => !v.survives),
  undefined_terms_from_section_1: undefinedTerms,
  gaps: gapsSurviving,
  gaps_all: gapsVerified.filter(Boolean),
}