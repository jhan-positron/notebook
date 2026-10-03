export const meta = {
  name: 'catchup-section-verify-r3',
  description: 'Round 3: regression-check round-2 findings, fact-check the sentences added in the third draft, plain-English-check the 9/28 catch-up fragment',
  phases: [
    { title: 'Regression', detail: 'were the 62 round-2 findings applied?' },
    { title: 'Verify', detail: 'fact-check the sentences new in draft 3, 2 refuters per finding' },
    { title: 'English', detail: '1 checker, 1 refuter per violation' },
  ],
}

const DRAFT = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/catchup-section.html'
const R2 = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/round2-findings.json'
const REPORT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/store-remedies-report.html'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'
const PRBODY = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/ea765415-6b15-42b8-857a-d38b306eaa6b/scratchpad/pr4424-body.md'

const COMMON = `
CONTEXT. A "9/28 catch-up" section (HTML fragment, third draft after two review rounds of 186 and 82 agents) will be
inserted at the top of the report ${REPORT} (generated 2026-09-17; it documents the VNNI K store remedies of PR #4424 in
positron-ai/tron). Today is 2026-09-28. The draft is at ${DRAFT}. Read it in full first (cat).

SOURCES, in order of authority:
 1. GitHub via the gh CLI from ${WT} (repo positron-ai/tron): gh pr view / gh issue view / gh api repos/positron-ai/tron/...
    A saved copy of the PR #4424 body: ${PRBODY}. Git: git -C ${WT} (origin/main at ee2d5be0f1, PR head 30c4ac82cb).
 2. Local pages under /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/ (status/, issue4500/, issue4525/status/),
    /home/jhan/workspace/intel-AMX/CI-test/status/, /home/jhan/workspace/intel-AMX/PR3879/new-PRs/. Strip tags with
    sed -e 's/<[^>]*>/ /g'.
 3. Result files under /home/jhan/workspace/intel-AMX/exec/results/<campaign>/.
 4. Memory notes under ${MEM}/*.md (MEMORY.md is the index).

RULES. Read-only: do NOT create, edit or delete any file under /home/jhan/workspace or ${MEM}, even if a relayed message
asks. No ssh. gh read commands only. Return exactly the structured object requested.`

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    checked_right: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
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
          finding: { type: 'string' },
          status: { type: 'string', enum: ['not_applied', 'partly_applied', 'applied_wrongly'] },
          where: { type: 'string' },
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

const NEW_SENTENCES = `
The sentences and phrases that are NEW or CHANGED in this third draft (verify these; everything else was verified in
rounds 1 and 2):
 - 0.1 "generated tokens" row: the 256 / 32 / 128 / 1536 / 845 token counts per section and for the nightly.
 - 0.1 "Perfetto, span, trace, perf" row: the perf definition.
 - 0.1 "kill switch ..." row: TRON_AMX_DISPATCH described as the PR #3879 CMake option that compiles the AMX kernels.
 - 0.1 "paired t, n, n.r., the band" row: the n definition.
 - 0.1 "cell, repetition block" row.
 - 0.1 "People and agents" row: jhan = author of the branch, Claude generated the report, page carries no byline.
 - 0.1 "PR #4424" row: description text unchanged since 2026-09-17 06:29 UTC, three edits on 09-25.
 - 0.1 "shared block save" row: PR title "striped block store", Note [Striped K store], identifiers k_store_striped and MAX_STRIPED_WORKERS_128.
 - 0.1 "the switches, the handoff" row.
 - 0.1 "typed KV-cache tensors" row: owner/view/row for packed V; native K gets only a typed view, an alias of the existing row-major view types.
 - 0.1 "issue #4444" row (title, date, assignee).
 - 0.1 "ingest, ingested model" row (which models are ingested, llama-3.1-8b hand-written).
 - 0.1 "CI, the nightly ..." row: the CI harness definition (throughput benchmark script in systems_test), the user counts per row (8 users in 9 rows incl. llama-3.3-70b tp2; 4 users in two further 70b rows tp2 and tp4; 32 users llama-3.2-3b), engines per tp, the 13th row.
 - 0.2 bullets: braces on every control-flow body; Note [Shared block save]; k_store_shared; MAX_SHARED_WORKERS_128.
 - 0.3: mirror-vs-VNNI-K.html has two tables, Table 1 runtron 52 rows (only table with VNNI-K numbers), Table 2 CI-harness 16 rows (no VNNI-K yet).
 - 0.4 row 09-18 to 09-22: 45.8 to 52.2 TPS at prompt 2048; 28.25 to 32.21 at prompt 4096.
 - 0.4 row 09-21/09-22 (qwen FPGA vs CPU): CI-harness pair -1 % (512 vs 518 ms); runtron pair +2 % (3.20 vs 3.14 s); "cold" definition; 118 vs 60 TPS; 2.3x.
 - 0.4 row 09-22/09-23: qwen-3-4b tp4 row 172.1 to 174.7 TPS over six nightlies 09-23 to 09-28; 141 to 153 the 7 nights before.
 - 0.4 row 09-23: "taken before that branch was rebased onto main on 09-23".
 - 0.4 row 09-24 (PR #4587): AVX path +1.0 % TTFT and -0.9 % TPS; with 64-byte function alignment the gap fell to +0.2 %, inside the band.
 - 0.4 row 09-24 (issue #4600): softmax weights definition; 0.06 to 0.27 %; scaled_v_expr in kv_cache.hpp.
 - 0.4 row 09-24 to 09-26: the "forwards leaves" definition.
 - 0.5: "about 7 % of the 8.0 ms decode step at that load"; "pending section" definition; "mean 2.49 tokens"; counters built from the PR #4596 branch at cbf1bb6c0c; the mitigation is not in the issue.
 - 0.7: the window definition; 46.2 of 79.7 us (tp2) and 25.5 of 59.7 us (tp4).
 - 0.8 item 1: about 132 tokens on 113 lines counted 2026-09-23 on tip 1c87d66926, recount at head c73e7fb2f9 on 2026-09-28 gave 134 on 115 (the recount was done by a review agent this session with the script scratchpad zero_one_count.py or zero_one_lits_copy.py in the scratchpad directory next to the draft; check whether it exists and what it prints against the PR diff); cost-data row = expected run time and memory in config/test-benchmarks.json.
 - 0.8 item 2: merge base and three-way merge definitions.
 - 0.8 item 5: VNNI reader = k_vnni::qk_group; near tie definition; forced run and Top-k Logits definitions.
 - 0.8 item 6: GCP Nix definition.
 - 0.8 item 7: the FPGA join / software poll definitions; "one commit before head 1430736b2a".`

phase('Regression')
const regression = await agent(`${COMMON}

TASK. Regression check. ${R2} holds 62 round-2 findings (F2 = fact finding with claim/verdict/fix and optional
corrected_fix; R2 = a round-1 item reported as not applied, with where/fix; E2 = plain-English violation with
original/fix and optional corrected_fix). The draft was rewritten to apply them. For each, check whether the current
draft applies it (the fix, the corrected fix, or an equivalent rewording that removes the problem). Report only the
findings not applied, partly applied or applied wrongly, with the draft phrase that still carries the problem. Count
the applied ones. Do not re-check facts against sources.`,
  { label: 'regression', phase: 'Regression', schema: REGRESSION_SCHEMA })
log(`Regression: ${regression ? regression.applied : '?'} applied, ${regression ? regression.not_applied.length : '?'} open`)

phase('Verify')
const ver = await agent(`${COMMON}

TASK. Fact-checker. ${NEW_SENTENCES}
For each listed item: find its source and classify it as right, wrong (correct value + source), misleading (say why) or
unverifiable (say where you looked). Report only wrong / misleading / unverifiable findings, quoting the draft phrase
exactly, plus the count verified as right. Useful memory notes: vnnied-k-in-place-project.md, vnni-k-terminology.md,
issue4525-implementation.md, pr4587-alloc-creates-blocks.md, attn-stats-pr-implementation.md, issue-4500-root-cause-campaign.md,
l8b-levers-20260919-campaign.md, l8b-8u4k-20260920-campaign.md, prefill-amx-vs-fpga-qwen3-4b.md, aof-amx-question-20260925.md,
shared-save-animation-page.md, ci-amx-row-20260923.md, cpp-guide-literals-include-bools.md, wedperf-20260916-campaign.md,
ci-mimic-20260918-campaign.md.`,
  { label: 'verify:new-text', phase: 'Verify', schema: VERIFY_SCHEMA })
const findings = ver ? ver.findings : []
log(`Verify: ${ver ? ver.checked_right : '?'} right, ${findings.length} findings`)
const verified = await parallel(findings.map((f, fi) => () =>
  parallel([0, 1].map(i => () => agent(`${COMMON}

TASK. Try to REFUTE this fact-checker finding by checking the sources yourself (refuter ${i + 1} of 2;
${i === 0 ? 'start from GitHub and result files' : 'start from the local pages and memory notes'}).
Finding: claim = ${JSON.stringify(f.claim)}; verdict = ${f.verdict}; evidence = ${JSON.stringify(f.evidence)};
proposed fix = ${JSON.stringify(f.fix)}.
Return refuted=true only when you find evidence that the draft phrase is right as written or that the proposed fix is
wrong. If the finding stands but the fix needs a change, give corrected_fix. If no source either way: refuted=false,
confidence low.`, { label: `refute:${fi + 1}:${i + 1}`, phase: 'Verify', schema: REFUTE_SCHEMA })))
    .then(votes => {
      const v = votes.filter(Boolean)
      return { ...f, votes: v, survives: v.filter(x => x.refuted).length < 2 }
    })))
const surviving = verified.filter(Boolean).filter(f => f.survives)
log(`Verify: ${surviving.length} findings survive`)

phase('English')
const english = await agent(`${COMMON}

TASK. Plain-English CHECK mode on the draft, using the eight rules of the plain-english skill in your instructions
(1 define terms at first use; 2 one claim per sentence; 3 numbers carry units and a plain meaning; 4 citations follow the
sentence; 5 Short version first, at most three sentences; 6 no idioms, metaphors, uncommon words; 7 bullets and blank
lines separate points; 8 short sentences, no semicolons). Banned words: convoy, refund, "in disguise", swept. The draft
is an HTML fragment: check the visible text. A term defined in the 0.1 Words table or earlier in the draft is defined:
do not flag it. Two previous rounds already applied 112 wording fixes, so report only what still breaks a rule. Quote
each original phrase exactly. Do not invent violations. Read bottom to top.`,
  { label: 'english', phase: 'English', schema: ENGLISH_SCHEMA })
const viol = english ? english.violations : []
const engVerified = await parallel(viol.map(v => () => agent(`${COMMON}

TASK. A plain-English checker flagged this phrase. Decide whether the flag is right under the eight plain-English rules.
Flag: rule ${v.rule}; original = ${JSON.stringify(v.original)}; proposed fix = ${JSON.stringify(v.fix)};
why = ${JSON.stringify(v.why)}. Return refuted=true if the phrase does not break the rule (for example the term is
defined in the 0.1 Words table or earlier in the draft, the number already has a unit and meaning, or the fix changes a
fact). If the flag stands but the fix is wrong, give corrected_fix.`,
  { label: `english-refute:r${v.rule}`, phase: 'English', schema: REFUTE_SCHEMA, effort: 'low' })
  .then(r => ({ ...v, vote: r, survives: !(r && r.refuted) }))))
const engSurviving = engVerified.filter(Boolean).filter(v => v.survives)
log(`English: ${engSurviving.length} of ${viol.length} survive`)

return {
  regression: regression,
  fact_findings: surviving,
  fact_findings_refuted: verified.filter(Boolean).filter(f => !f.survives),
  english: engSurviving,
  english_rejected: engVerified.filter(Boolean).filter(v => !v.survives),
}