export const meta = {
  name: 'fix4500-write',
  description: 'Write issue4500/fix-4500.html in plain English from the verified facts bundle: 2 drafts, fact+English+render checks, judge, final check',
  phases: [
    { title: 'Write', detail: 'two independent drafts of the page' },
    { title: 'Check', detail: 'fact refuter, plain-English check, render check per draft' },
    { title: 'Judge', detail: 'merge the best draft, apply all valid fixes' },
    { title: 'Final check', detail: 'refute and English-check the merged page' },
  ],
}
const A = args
const COMMON = `
INPUTS (read them all first)
- The facts bundle: ${A.bundle}. It holds every verified claim (mechanism, tests, chain, campaign numbers, smoke, unit tests). Use ONLY facts from it. Where the bundle marks a claim REFUTED, use the CORRECTION. Where it lists an unknown, the page may name it as open, never resolve it.
- Sources for spot checks (read-only): fix worktree ${A.wt} (branch jhan-amx-vnniK-i4500), results ${A.res}, chain README ${A.readme}, root-cause page ${A.rootcause}, the 9/28 catch-up section 0.5 of ${A.report} (lines 134-152) for the problem statement.
- Page head to reuse verbatim (doctype, meta, style): ${A.stylehead}. Change only the <title>. Light theme only.

THE PAGE: ${A.out} (write it there; pure ASCII, no non-ASCII bytes; HTML5; no external scripts or stylesheets; inline SVG allowed).
Audience: an engineer who has never seen this project. Plain-English rules from the plain-english skill apply in full (Short version first, Words used here list, one claim per sentence, units and meaning on numbers, no idioms, citations after sentences in brackets, short sentences, bullets for multi-point paragraphs).
Required order of sections:
1. Title "Issue #4500: the fix, built and measured (2026-09-29)" and a meta line (generated date UTC, machine, chain folder, branch and commits).
2. Short version (3 sentences at most). It must say: the fix idea was built on a side branch (not pushed, PR #4424 untouched); on the FPGA-attention cells it removes about a third of the loss and the change fix-vs-vnni is NOT resolved at n = 3 (paired t 1.6 tp2, 1.8 tp4 against the 4.30 threshold); tokens are identical to the PR head under FPGA attention; two unit tests fail (one a defect in the new test, one most likely a defect in the fix code); so it is not ready to push.
3. Words used here (table). Define: tron, runtron, rinzler, deb, K, KV cache, page, 16-token block, VNNI layout, row-major, AMX, FPGA attention vs CPU attention, tp2/tp4, users per engine, TPS, TTFT, paired t and its thresholds (12.71 at n=2, 4.30 at n=3), base / vnni / fix / nightly binaries (with commit ids), delphi-3bda and our half, the chain, smoke, the fake device, EAGLE (only as much as the bundle supports: a speculative-decoding storage view).
4. What the problem was (3-5 sentences from the root cause: per-token K row in 64 cache lines instead of 4, three operations, in series with the card; reference numbers of 09-19: -4.3 % tp2, -13.4 % tp4).
5. What the fix does: mechanism in plain words, then a diagram. Draw ONE inline SVG "before / after" picture: one token row as 4 whole cache lines (row-major) versus 4 bytes in each of 64 lines (VNNI), and the block life: rows saved row-major -> 16th row -> converted at the forward end by the main thread -> AMX-ready. Keep the SVG simple (boxes, arrows, labels), width 100 % with a viewBox, labels never overlapping arrows, gutter >= 140 px around text. Then bullets: where the state bits live, who converts and when and why not inside save_k, what readers do for each block kind, what happens on clear/copy/restore, what was removed. Every bullet cites file:line from the bundle.
6. How it was tested: the chain steps A-E as a table (step, what, when UTC, outcome), the binaries, the cells, the client.
7. Results, three parts:
   7.1 Throughput: a dumbbell chart (inline SVG) with one row per cell (3 cells) and one dot per binary (base, vnni, fix, nightly), direct value labels on every dot, the fix-vs-vnni gap annotated with its % and its paired t, a one-line takeaway under it, honest axis (state where the axis starts), colorblind-safe colors (blue #2a78d6 base, orange #eb6834 vnni, green #1f9d55 fix, grey #8a8a8a nightly), legend with words not only colors. Then the exact table (cell, binary, n, mean TPS, sd, step ms, TTFT ms) and the paired table (a vs b, delta ms/step, delta %, paired t, resolved yes/no against the threshold). Say plainly which differences are resolved and which are not. Note the tp4 sd of 14-17 TPS for vnni and fix (run-to-run bimodal behaviour seen before) and the nightly tp4 +12.9 % vs base (a rise seen since 09-23 on packages without the layout, cause open).
   7.2 Tokens (smoke): the 4 configurations, identical under FPGA attention, A/A identical, CPU-attention differs (first difference token 52 of 128 at prompt 1024, token 6 at prompt 1000) and why a difference there is admissible per the bundle (row-major dotter vs qk_group add order on the tail block) but not yet proven to be only that: name the measurement that would prove it (forced run with Top-k Logits at the first divergent step).
   7.3 Unit tests: the two failures with test name, file:line, what aborted, new-or-pre-existing, classification, consequence (which later cases never ran), the remedy the bundle implies, and the step E row-major result (t_llama_unit 42/42 passed, so failure 2 is specific to the VNNI build; the EAGLE test fails in both builds, consistent with a test defect). Also AMX-busy cycles are in the summary: mention only that they were recorded, no interpretation beyond the bundle.
8. Reading: what the numbers say and do not say. Label every explanation of the remaining loss as a hypothesis with the measurement that would confirm or reject it (the bundle does not explain the remaining two thirds). Do not invent.
9. Open items and decisions for jhan (fix the two tests: test defect vs code defect; the unverified test cases; push or not; comment on issue #4500; the EAGLE + VNNI path has no passing test; the OOM-rescue race question).
10. Where the data is (paths: results dir, logs, scripts, worktrees, summary.md, this page's facts bundle path).
Length target: 1800 to 2600 words of visible text (measure with: sed 's/<[^>]*>//g' FILE | wc -w). Every number carries a unit. Do not write "Insufficient data" for things the bundle answers.
`
const DRAFT_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, words: { type: 'number' }, notes: { type: 'string' } }, required: ['path', 'words', 'notes'] }
const FACT_SCHEMA = { type: 'object', properties: {
  wrongFacts: { type: 'array', items: { type: 'string' } }, inventedFacts: { type: 'array', items: { type: 'string' } },
  missingRequired: { type: 'array', items: { type: 'string' } }, structureOk: { type: 'boolean' } }, required: ['wrongFacts', 'inventedFacts', 'missingRequired', 'structureOk'] }
const PE_SCHEMA = { type: 'object', properties: { violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, phrase: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'phrase', 'fix'] } }, words: { type: 'number' } }, required: ['violations', 'words'] }
const RENDER_SCHEMA = { type: 'object', properties: { problems: { type: 'array', items: { type: 'string' } }, ok: { type: 'boolean' } }, required: ['problems', 'ok'] }

const ANGLES = [
  { key: 'a', hint: 'Angle A: decision-first. The reader is jhan deciding whether to push. Keep the mechanism section tight and the results and open items complete.' },
  { key: 'b', hint: 'Angle B: newcomer-first. The reader has never seen the project. Spend more words on the mechanism picture and the words table; results still complete.' },
]
phase('Write')
const drafts = (await parallel(ANGLES.map(x => () =>
  agent(`Write the page described below as ${A.scratch}/draft-${x.key}.html. ${x.hint} Load the dataviz skill (Skill tool, name "dataviz") before drawing the chart if it is available; otherwise follow the chart rules in the spec. Before returning, render both SVGs to PNG (python3 -c "import cairosvg" if available, else skip and say so) and look at them; fix overlaps. Measure the visible word count and return it.\n${COMMON}`,
    { label: `write:${x.key}`, phase: 'Write', schema: DRAFT_SCHEMA, effort: 'max' })))).map((d, i) => d && ({ ...d, key: ANGLES[i].key })).filter(Boolean)
log('drafts: ' + drafts.map(d => `${d.key}=${d.words}w`).join(', '))

phase('Check')
const checked = await pipeline(drafts, d => parallel([
  () => agent(`Fact refuter. Draft page: ${A.scratch}/draft-${d.key}.html. Check EVERY number, id, date, file:line, percentage, t value, test name and causal claim against the facts bundle and, where the bundle cites a file:line, against the source. Report wrong facts (quote + correction), invented facts (not in the bundle), and required content that is missing (compare with the numbered section list in the spec). Default to reporting a problem when uncertain. Do not judge style.\n${COMMON}`, { label: `facts:${d.key}`, phase: 'Check', schema: FACT_SCHEMA }),
  () => agent(`Plain-english skill, Check mode. Check ${A.scratch}/draft-${d.key}.html against every rule (Rule 1: a term defined in the page's own Words table counts as defined). List every violation with the exact phrase and a fix. Measure the visible words. Do not invent violations.`, { label: `english:${d.key}`, phase: 'Check', schema: PE_SCHEMA }),
  () => agent(`Render check. Open ${A.scratch}/draft-${d.key}.html. (1) Confirm it is pure ASCII (python3: open(...,'rb').read().isascii()). (2) Parse it with python html.parser and report unbalanced tags. (3) Extract each inline <svg>, render to PNG with cairosvg if available (pip show cairosvg; if missing try python3 -m pip install --user cairosvg, else report), view the PNGs with the Read tool, and report overlapping labels, labels crossing arrows, text cut at the edges, unreadable sizes, a chart axis that does not start where the page says, missing value labels, and missing legend words. (4) Check that the tables have a header row and every numeric cell has a unit in the header. Return the problem list.`, { label: `render:${d.key}`, phase: 'Check', schema: RENDER_SCHEMA }),
]).then(([facts, pe, render]) => ({ ...d, facts, pe, render })))
for (const c of checked.filter(Boolean)) log(`${c.key}: wrong=${c.facts?.wrongFacts?.length} invented=${c.facts?.inventedFacts?.length} missing=${c.facts?.missingRequired?.length} english=${c.pe?.violations?.length} render=${c.render?.problems?.length}`)

phase('Judge')
const reports = checked.filter(Boolean).map(c => `=== draft ${c.key}: ${A.scratch}/draft-${c.key}.html (${c.words} words) ===\nFACTS: ${JSON.stringify(c.facts)}\nENGLISH: ${JSON.stringify(c.pe)}\nRENDER: ${JSON.stringify(c.render)}`).join('\n\n')
const judged = await agent(`Editor. Two drafts of the page were written and checked. Read both and their reports below. Choose the better base (fewest fact problems, then completeness, then readability), apply EVERY valid fix from all reports, graft better sections from the other draft, re-check each number against the bundle yourself, re-render the SVGs and look at them, and write the result to ${A.scratch}/final.html. Keep it pure ASCII. Return the path, the word count, and a list of the fixes you applied and any report item you rejected with the reason.\n${COMMON}\n\nREPORTS\n${reports}`, { label: 'judge', phase: 'Judge', schema: DRAFT_SCHEMA, effort: 'max' })
log(`judge: ${judged?.words}w`)

phase('Final check')
const [f2, p2, r2] = await parallel([
  () => agent(`Fact refuter, final pass. Page: ${A.scratch}/final.html. Check EVERY number, id, date, file:line, percentage, t value and causal claim against the facts bundle and the sources. Report wrong and invented facts with corrections, and required content still missing. Default to reporting when uncertain.\n${COMMON}`, { label: 'facts:final', phase: 'Final check', schema: FACT_SCHEMA, effort: 'max' }),
  () => agent(`Plain-english skill, Check mode, final pass on ${A.scratch}/final.html (Rule 1: terms in the page's Words table count as defined). List every violation with the exact phrase and a fix. Measure the visible words.`, { label: 'english:final', phase: 'Final check', schema: PE_SCHEMA, effort: 'max' }),
  () => agent(`Render check, final pass on ${A.scratch}/final.html: ASCII, balanced tags, each SVG rendered with cairosvg and viewed with Read, overlaps, cut text, axis honesty, value labels, legend words, table headers with units. Return the problem list.`, { label: 'render:final', phase: 'Final check', schema: RENDER_SCHEMA }),
])
return { judged, facts: f2, english: p2, render: r2 }