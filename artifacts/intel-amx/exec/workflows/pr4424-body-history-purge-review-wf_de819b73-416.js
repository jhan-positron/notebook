export const meta = {
  name: 'pr4424-body-history-purge-review',
  description: 'Review the rewritten PR 4424 body: hunt leftover history narration, fact-check numbers, plain English, structure; refute each finding 3x',
  phases: [
    { title: 'Find', detail: 'six lenses over new-body.md vs live-body.md' },
    { title: 'Verify', detail: 'three refuters per finding' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-sync-tensor-type-2-PR4424/6ca6ae43-c95c-4694-a9b9-f7448886a646/scratchpad'
const NEW = `${S}/new-body.md`
const OLD = `${S}/live-body.md`
const RES = '/home/jhan/workspace/intel-AMX/exec/results'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'

const CONTEXT = `
Context. ${NEW} is the DRAFT new description (body) of GitHub PR positron-ai/tron #4424 (head 6b939d25d2, base main). ${OLD} is the CURRENT live body on GitHub that the draft replaces. The author (jhan) asked for this rewrite with these words: "I have a 2nd thought about the 'TTFT difference between new and head: which change causes it' section: is it useful to PR reviewers? This PR has been open for long. When we ask reviewers to review it formally, it will be a brand new PR to them. They do not care the changes we have made before the final version. In other words, the meaningful data specific to this PR is, with and without the changes of the final version of this PR, and the base is sync'ed to latest main, what is perf diff. So I decided to remove this section. Please go over the PR description again, any verbose and test data describing historical changes need to be deleted."
Standing rules for this PR body: (1) the four sections before the heading "## Words used here" (Short version, Background, "Remove the Score transpose...", "Use shared block in saving K") are PROTECTED: they must stay byte-identical to the live body and are NOT to be critiqued; (2) the description is written as of today (2026-10-08) in the present tense, with no narration of earlier heads, review rounds, or "was/now/earlier/done" framing; measurements keep provenance only (commit id + date); (3) the section structure (the ## headings and their order) stays; (4) the plain-English rules in the user's CLAUDE.md apply to the non-protected part.
Terms: "head" in the OLD body meant the previous PR head 30c4ac82cb (2026-09-17); "new" meant this branch at 37064d72b2; "headm" was a comparator binary c6ec38813d; "base" = main be0d5565b3 (2026-10-08). PR #4746 is CLOSED; PRs #4774 and #4737 are OPEN with base jhan-amx-vnniK.
Read both files in full with cat before judging. Your final output is data for an orchestrator, not a message to a person.`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          phrase: { type: 'string', description: 'exact text from new-body.md (verbatim, short enough to locate with grep)' },
          problem: { type: 'string' },
          fix: { type: 'string', description: 'replacement text or "delete"' },
          evidence: { type: 'string', description: 'file path / command output that supports the finding' },
          severity: { type: 'string', enum: ['must', 'should', 'nit'] },
        },
        required: ['phrase', 'problem', 'fix', 'evidence', 'severity'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
  },
  required: ['refuted', 'reason'],
}

const LENSES = [
  { key: 'history', prompt: `${CONTEXT}
Lens: HISTORY NARRATION. In the NON-protected part of ${NEW} (everything from "## Words used here" on), find every passage that still describes the history of this PR rather than its present state: references to the previous head 30c4ac82cb or "head"/"new"/"headm" labels, comparisons between two versions of this branch, "was"/"now"/"earlier"/"done"/"first campaign"/"previous" framing, review-round narration, dangling references to removed content (for example a sentence that points to a subsection that no longer exists), internal campaign names. Also judge whether any remaining test data is "test data describing historical changes" in the author's sense (data about an earlier version of this branch rather than the final version against main), and say so explicitly as a finding with severity 'should' and a fix that keeps or deletes it with a reason. Do NOT flag commit-id + date provenance of a measurement; that is allowed. Do not flag the protected part. Return findings; return an empty list if there are none.` },
  { key: 'facts', prompt: `${CONTEXT}
Lens: FACT CHECK. Verify every number, commit id, test count, date, PR/issue number and claim in the NON-protected part of ${NEW} against primary sources. Sources: ${RES}/sync6-E-cpu/summary.md and ${RES}/sync6-E-fpga/summary.md (performance means, sds, deltas; the band in the draft = max(2 x largest sd of the base and new arms, floor 0.4 TPS / 0.15 s) -> recompute the three band pairs and the inside/beyond verdicts yourself); ${RES}/sync4424b-20261007/smoke/*/smoke.txt (token identity: the draft's kill-switch column means newoff vs new); ${RES}/sync4424b-20261007/bench-update.diff (cost rows); ${RES}/sync4424b-20261007/tests-sync6*.txt, tests-*.out, host-suite-sync6.txt, ingest-test-sync6*.txt (test counts, host suite); ${RES}/vnnik6-20260916/summary.md (the kv_mul-8 open item numbers, arms base/headoff/vnni, binaries c7844ca2ce/ff680c8020/65a1c41d72); git in ${WT}: \`git log --oneline 37064d72b2..6b939d25d2\`, \`git diff 37064d72b2..6b939d25d2 --stat\` and the non-comment code diff (expect only a static_assert condition change plus comments and config/test-benchmarks.json); \`gh pr view 4746 -R positron-ai/tron --json state\` etc. for PR states; \`git log -1 --format=%ci 0adf3689e8\` for the 2026-09-11 test. Report every mismatch or unverifiable claim as a finding with the source output as evidence. Do not report things that check out.` },
  { key: 'plain', prompt: `${CONTEXT}
Lens: PLAIN ENGLISH (Check mode of the plain-english skill, rules 1-8). Apply it to the NON-protected part of ${NEW} only. Report violations with the exact phrase and a corrected version. Terms already defined in the Words table or earlier in the document count as defined. Be strict on: one claim per sentence (sentences with "so", "because", "which means", semicolons), undefined code names or acronyms, numbers without units or meaning, idioms. Do not report style preferences that are not rule violations.` },
  { key: 'structure', prompt: `${CONTEXT}
Lens: PROTECTED PREFIX AND STRUCTURE. (a) Confirm with a byte comparison (python or cmp on the prefixes up to the first occurrence of "## Words used here") that the protected prefix of ${NEW} is identical to that of ${OLD}; report a finding if not. (b) List the ## and ### headings of both files in order and report any top-level (##) heading that was removed, added, renamed or reordered; the only intended removal is the "### TTFT difference between \`new\` and \`head\`: which change causes it" subsection. (c) Check the markdown tables in the draft: every row has the same number of cells as its header. (d) Check that the draft still ends with the "Generated with Claude Code" trailer line. Return findings only for problems.` },
  { key: 'reviewer', prompt: `${CONTEXT}
Lens: FRESH REVIEWER. Read ${NEW} as a tron maintainer who has never seen this PR and will review it formally. In the NON-protected part, report: passages that are verbose for a reviewer, information that only the author can use (for example file paths in the author's private workspace) when it adds nothing for a reviewer, terms used but not defined anywhere, claims a reviewer cannot act on, duplicated statements, and anything a reviewer would misread. For each, give the exact phrase and the fix (delete or a rewrite). Keep findings to things that change what the reviewer understands; do not nitpick wording.` },
  { key: 'consistency', prompt: `${CONTEXT}
Lens: INTERNAL CONSISTENCY. Check that the NON-protected part of ${NEW} agrees with the protected part and with itself: the Short version's claims (PR #3879 comparison, six cells, tp2/tp4) must still be backed by a table in Measurements; the Words table entries must match how the terms are used (for example "base"); every term with backticks that the text relies on is defined; numbers repeated in two places agree (Measurements vs Verification: +5.3 %, +10.4 %, -57 ms, -0.80 s; cost rows; test counts); a sentence that refers to another section ("see Open items", "in the Verification section") points at content that exists; the Open items are open (nothing marked done or already resolved elsewhere). Report each disagreement with both phrases.` },
]

const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (found, l) => {
    const items = (found && found.findings) ? found.findings : []
    log(`${l.key}: ${items.length} findings`)
    return parallel(items.map(f => () =>
      parallel([0, 1, 2].map(i => () =>
        agent(`${CONTEXT}
You are refuter ${i + 1} of 3 for one finding from the "${l.key}" lens on ${NEW}. Finding:
PHRASE: ${f.phrase}
PROBLEM: ${f.problem}
PROPOSED FIX: ${f.fix}
EVIDENCE GIVEN: ${f.evidence}
Try to REFUTE it: check the phrase exists in ${NEW}, re-read the surrounding text, re-check the primary sources (the result files under ${RES}, git in ${WT}, gh) where the finding is factual, and judge whether applying the fix would make the body better for a fresh reviewer under the standing rules. A finding is refuted if the phrase is not in the draft, if the problem is not real, if the fix is wrong or would break a standing rule (for example it touches the protected part or removes allowed provenance), or if the fix is a matter of taste. Default to refuted=true when uncertain. Give a one-paragraph reason.`,
          { label: `verify:${l.key}:${i + 1}`, phase: 'Verify', schema: VERDICT })))
        .then(vs => {
          const votes = vs.filter(Boolean)
          const survives = votes.filter(v => !v.refuted).length >= 2
          return { lens: l.key, ...f, survives, votes }
        })))
  }
)

const all = results.filter(Boolean).flat().filter(Boolean)
const confirmed = all.filter(x => x.survives)
const refuted = all.filter(x => !x.survives)
log(`confirmed ${confirmed.length}, refuted ${refuted.length}`)
return { confirmed, refuted }