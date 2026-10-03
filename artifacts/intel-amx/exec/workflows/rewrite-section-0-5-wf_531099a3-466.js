export const meta = {
  name: 'rewrite-section-0-5',
  description: 'Rewrite section 0.5 of store-remedies-report.html at half length: draft x3, fact+plain-English verify, judge, final verify',
  phases: [
    { title: 'Draft', detail: 'three independent rewrites, different orderings' },
    { title: 'Verify', detail: 'fact refuter + plain-English checker + word count per draft' },
    { title: 'Judge', detail: 'pick the best draft, apply the fixes, produce the final HTML' },
    { title: 'Final check', detail: 'refute the judged text once more' },
  ],
}

const S = args.scratch
const ORIG = args.orig
const REPORT = args.report
const ROOT = args.rootcause
const MAX = args.maxWords
const MIN = args.minWords

const COMMON = `
CONTEXT
- File under revision: ${REPORT} (an HTML report). Section 0.5 is lines 107-118 (one <h3> line, then the body). A verbatim copy of the section is at ${S}/section-0.5-original.html. Read it with cat.
- Section 0.1 of the same report is the "Words used here" table (copy at ${S}/section-0.1-terms.html). Every term in that table counts as ALREADY DEFINED; the rewrite must NOT redefine them and must NOT add a words-used-here list. Terms NOT in that table but used in the section (gof::populate, qk_group, TRON_HWATTN_EARLY_LAUNCH_MIN_B, the pending section, PR #4596, the kill switch is in the table) keep a short inline definition at first use if they are kept at all.
- Primary source of truth for every fact: the original section text. Secondary sources (read only to confirm a number if in doubt): ${ROOT} (12k words; grep it rather than read it all) and the memory note /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/issue-4500-root-cause-campaign.md.
- The rewrite must contain NO fact, number, date or claim that is not in the original section. It may drop facts (that is the point of halving) but must not change any kept fact.

REQUIRED SHAPE OF THE REWRITE
1. The <h3> heading line keeps the number "0.5" and "Issue #4500" and gets shorter (at most 20 words).
2. Then three labelled parts, in this order, each opened by a bold lead-in inside a <p> (e.g. <p><b>The problem.</b> ...</p>):
   - The problem: what goes wrong, where, by how much (the essential numbers: the CI loss -5.0 % TPS in the 09-18 run at tp2, the reproduction -4.3 % TPS, the tp4 loss -13.4 % TPS, the per-layer save growth 4.6 to 20.3 us, the +0.57 ms per step in series, the 64-cache-line access, the three operations, FPGA attention is the trigger because with CPU attention the save overlaps the workers).
   - Suggested fixes: the fix idea (keep the incomplete 16-token block row-major, convert on completion, as the prefill block save of section 3.1 already does; not measured, not built), the four options the issue lists, and the run-time mitigation TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (define it once: the switch that launches the card before the K and V saves) with its numbers (+6.2 % vs the nightly package; the shipped package itself +7.7 % TPS at 2 users per engine). State that the mitigation is not in the issue, and the issue has no comment yet, and the result lives only in the local page issue4500/root-cause-debug.html.
   - Details: the remaining evidence as a <ul> of short bullets (launch-order proof +0.58 ms, paired t 19.7; the card excluded at both widths; the AMX kernel excluded at tp2 (kill switch +0.3 %, n.r.) and the layout-off build equal to main within 0.006 ms per step; at tp4 the workers' tail read adds +0.37 ms per step and an AMX-side part is open (kill switch recovers +6.8 % TPS); the 2026-09-25 PR #4596 counter measurement: with FPGA attention the AMX kernel scores no page in steady-state decode, mean 2.49 newest tokens per step never fill a 64-token page, so the layout has a decode cost and no decode gain for the ingested models, while the prefill gain is unchanged (TTFT -34 ms tp2 / -58 ms tp4, qwen-3-4b, prompt 1024, the 09-16 FPGA cells).
3. LENGTH: the whole section INCLUDING the heading, with HTML tags stripped, must be between ${MIN} and ${MAX} words (the original is 735 words; the user asked for half). Measure it: write your draft to a file and run: sed 's/<[^>]*>//g' FILE | wc -w. Iterate until inside the range. Report the measured count.
4. Plain-English rules (the plain-english skill in your instructions) apply in full, except the words-used-here list which is skipped on purpose. In particular: one claim per sentence, no semicolons, every number carries a unit and a plain meaning where needed, no idioms, short sentences, citations follow a plain sentence.
5. Output only an HTML fragment that replaces lines 107-118: the <h3> line and the body, no <html>/<body> wrappers, no CSS, pure ASCII (use "%" with a space before it as the original does, and "us" for microseconds as the original does). Match the original's markup style (<h3>, <p>, <ul><li>, <b>).
`

const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    html: { type: 'string', description: 'the HTML fragment' },
    measuredWords: { type: 'number', description: 'wc -w of the tag-stripped fragment' },
    droppedFacts: { type: 'array', items: { type: 'string' }, description: 'facts of the original left out on purpose' },
  },
  required: ['html', 'measuredWords', 'droppedFacts'],
}

const ANGLES = [
  { key: 'tight', hint: 'Angle: shortest faithful version. Prefer dropping secondary evidence over compressing sentences into dense ones. Every kept number stays exact.' },
  { key: 'reader', hint: 'Angle: a newcomer reads only "The problem" and "Suggested fixes" and must understand the issue without the details. Put the mechanism (64 cache lines instead of 4, per token) in the first two sentences of the problem.' },
  { key: 'evidence', hint: 'Angle: keep the strongest single proof in the problem part (the launch-order switch: +0.58 ms per step, paired t 19.7) and move everything else to Details. Details may be a compact <ul>.' },
]

phase('Draft')
const drafts = await parallel(ANGLES.map(a => () =>
  agent(`Write a rewrite of section 0.5 (Issue #4500) of the store-remedies report at half its length.\n${COMMON}\n${a.hint}\nWrite your draft to ${S}/draft-${a.key}.html, measure it, and return it.`,
    { label: `draft:${a.key}`, phase: 'Draft', schema: DRAFT_SCHEMA })
)).then(r => r.map((d, i) => d && ({ ...d, key: ANGLES[i].key })).filter(Boolean))
log(`${drafts.length} drafts: ` + drafts.map(d => `${d.key}=${d.measuredWords}w`).join(', '))

const FACT_SCHEMA = {
  type: 'object',
  properties: {
    wrongFacts: { type: 'array', items: { type: 'string' }, description: 'each: quoted phrase of the draft + what the original/source says instead' },
    inventedFacts: { type: 'array', items: { type: 'string' }, description: 'claims in the draft not present in the original section' },
    missingRequired: { type: 'array', items: { type: 'string' }, description: 'required facts (see the REQUIRED SHAPE list) absent from the draft' },
    structureOk: { type: 'boolean', description: 'heading + The problem + Suggested fixes + Details in that order' },
  },
  required: ['wrongFacts', 'inventedFacts', 'missingRequired', 'structureOk'],
}
const PE_SCHEMA = {
  type: 'object',
  properties: {
    violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, phrase: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'phrase', 'fix'] } },
    measuredWords: { type: 'number' },
  },
  required: ['violations', 'measuredWords'],
}

phase('Verify')
const verified = await pipeline(drafts,
  d => parallel([
    () => agent(`You are a fact refuter. A draft rewrite of section 0.5 is at ${S}/draft-${d.key}.html. Compare EVERY number, date, id, percentage, count and causal claim of the draft against the original section (${S}/section-0.5-original.html). Also try hard to find claims the draft states that the original does not (inventions), and required facts it lacks. Default to reporting a problem when uncertain. Do not judge style.\n${COMMON}`,
      { label: `facts:${d.key}`, phase: 'Verify', schema: FACT_SCHEMA }),
    () => agent(`You are the plain-english skill in Check mode. Check the draft at ${S}/draft-${d.key}.html against the plain-English rules (skip Rule 1 for terms in ${S}/section-0.1-terms.html, and skip the words-used-here list requirement). List every violation with the exact phrase and a fix. Also measure the tag-stripped word count with: sed 's/<[^>]*>//g' ${S}/draft-${d.key}.html | wc -w. Do not invent violations.`,
      { label: `plain:${d.key}`, phase: 'Verify', schema: PE_SCHEMA }),
  ]).then(([facts, pe]) => ({ ...d, facts, pe }))
)
for (const v of verified.filter(Boolean)) {
  log(`${v.key}: ${v.measuredWords}w (checker ${v.pe?.measuredWords}), wrong=${v.facts?.wrongFacts?.length ?? '?'} invented=${v.facts?.inventedFacts?.length ?? '?'} missing=${v.facts?.missingRequired?.length ?? '?'} pe=${v.pe?.violations?.length ?? '?'}`)
}

phase('Judge')
const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    chosen: { type: 'string' },
    why: { type: 'string' },
    html: { type: 'string' },
    measuredWords: { type: 'number' },
  },
  required: ['chosen', 'why', 'html', 'measuredWords'],
}
const report = verified.filter(Boolean).map(v => `=== draft ${v.key} (${S}/draft-${v.key}.html, ${v.measuredWords} words) ===\nfact report: ${JSON.stringify(v.facts)}\nplain-English report: ${JSON.stringify(v.pe)}\ndropped facts (self-reported): ${JSON.stringify(v.droppedFacts)}`).join('\n\n')
const judged = await agent(`You are the editor. Three drafts of section 0.5 were written and checked. Read all three drafts and their check reports below. Pick the best one (fewest fact problems first, then plain-English violations, then readability for a newcomer). Apply EVERY valid fix from its reports, and graft any clearly better sentence from the other drafts. Re-check each number against the original once more yourself. Then write the final fragment to ${S}/final.html, measure it (sed 's/<[^>]*>//g' ${S}/final.html | wc -w) and iterate until it is between ${MIN} and ${MAX} words. Return it.\n${COMMON}\n\nCHECK REPORTS\n${report}`,
  { label: 'judge', phase: 'Judge', schema: FINAL_SCHEMA, effort: 'max' })
log(`judge chose ${judged?.chosen}: ${judged?.measuredWords}w`)

phase('Final check')
const [facts2, pe2] = await parallel([
  () => agent(`You are a fact refuter. The FINAL rewrite of section 0.5 is at ${S}/final.html. Compare EVERY number, date, id, percentage, count and causal claim against the original section (${S}/section-0.5-original.html), and grep ${ROOT} for any number you doubt. Report inventions and wrong facts. Default to reporting a problem when uncertain. Do not judge style.\n${COMMON}`,
    { label: 'facts:final', phase: 'Final check', schema: FACT_SCHEMA, effort: 'max' }),
  () => agent(`You are the plain-english skill in Check mode. Check ${S}/final.html against the plain-English rules (skip Rule 1 for terms in ${S}/section-0.1-terms.html, skip the words-used-here list). List every violation with the exact phrase and a fix. Measure: sed 's/<[^>]*>//g' ${S}/final.html | wc -w. Do not invent violations.`,
    { label: 'plain:final', phase: 'Final check', schema: PE_SCHEMA, effort: 'max' }),
])
return { judged, facts2, pe2, drafts: verified.filter(Boolean).map(v => ({ key: v.key, words: v.measuredWords, facts: v.facts, pe: v.pe })) }