export const meta = {
  name: 'fix4500-revise',
  description: 'Revise fix-4500.html: apply the final-check findings, add the later-commits re-test update, shorten; then refute, English-check and render-check once more',
  phases: [
    { title: 'Revise', detail: 'one editor applies every finding and the update' },
    { title: 'Final check', detail: 'fact refuter, English check, render check' },
  ],
}
const A = args
const COMMON = `
INPUTS
- Current page (round 1): ${A.scratch}/final.html. Its generator: ${A.scratch}/gen_final.py with ${A.scratch}/final-body.html and final-fig1.svg / final-fig2.svg (edit the generator inputs and re-run it, or edit the HTML directly, but the result must be ${A.scratch}/final.html).
- Facts bundle: ${A.bundle}. Use only its facts. A NEW section at its end, "LATER COMMITS AND RE-TEST", was appended after round 1: the branch moved to f34b0fe2ec (three commits after the tested 617cb8333f), the re-test at f34b0fe2ec passes all 10 + 42 cases in both the VNNI and the row-major build, the campaign and smoke numbers were NOT re-run at f34b0fe2ec, issue #4500 has 0 comments as of 2026-09-29T18:26Z, PR #4424 head 30c4ac82cb is untouched, and the branch exists only locally. The code diff of the later commits (headers only) is at ${A.scratch}/later-commits-code.diff.
- Round-1 check reports (fact, English, render): ${A.scratch}/final-check-reports.json. Apply every item unless it contradicts the bundle; list rejected items with the reason.
- Sources for spot checks (read-only): ${A.wt} (now at f34b0fe2ec; use git show 617cb8333f:<file> for the pinned citations), ${A.res}, ${A.rootcause}, ${A.report}.
RULES: plain-English skill in full; pure ASCII; light theme; no external scripts; every number with a unit; citations in brackets after the sentence.`

const DRAFT_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, words: { type: 'number' }, applied: { type: 'string' }, rejected: { type: 'string' } }, required: ['path', 'words', 'applied', 'rejected'] }
const FACT_SCHEMA = { type: 'object', properties: { wrongFacts: { type: 'array', items: { type: 'string' } }, inventedFacts: { type: 'array', items: { type: 'string' } }, missingRequired: { type: 'array', items: { type: 'string' } } }, required: ['wrongFacts', 'inventedFacts', 'missingRequired'] }
const PE_SCHEMA = { type: 'object', properties: { violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, phrase: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'phrase', 'fix'] } }, words: { type: 'number' } }, required: ['violations', 'words'] }
const RENDER_SCHEMA = { type: 'object', properties: { problems: { type: 'array', items: { type: 'string' } }, ok: { type: 'boolean' } }, required: ['problems', 'ok'] }

phase('Revise')
const rev = await agent(`Editor, round 2. Revise ${A.scratch}/final.html in place. Do ALL of the following:
1. Apply every finding in final-check-reports.json (one wrong fact about present/model.hpp:2939; the invented "None posted" -> cite the 2026-09-29T18:26Z GitHub check from the bundle; all English violations; all render items: renumber sections 1..N consistently including the meta line's cross-reference, fix the llama-row marker overlap, reword the sd legend, draw the base sd bar last or narrower on the tp4 row, make the "N of M" test counts say passed/ran/exist).
2. Add the UPDATE from the bundle's "LATER COMMITS AND RE-TEST" section: (a) in the Short version, one sentence: the two failures were fixed by three later commits and the re-test at f34b0fe2ec passes every case in both builds, while the throughput and token results still belong to 617cb8333f; (b) in the meta line: tested commit vs current branch head; (c) in the unit-test section 7.3: a short "After the chain" paragraph with the three commits (id, date, subject in plain words), what each changed (test-side vs code-side, from the subjects and the diffstat), the re-test result with the file names, and the statement that TPS and tokens were not re-measured at the new head, so the 675df85c94 change to self_attention.hpp is unmeasured; (d) in the open items: replace the "fix the two tests" decisions with "re-measure at f34b0fe2ec (TPS cells and smoke) before pushing" and keep "push or not", "comment on issue #4500 (0 comments as of 2026-09-29)", the EAGLE+VNNI path coverage now has a passing test case (say which, from the bundle: t_k_vnni_layout "the EAGLE storage view keeps its own K layout state" passes at f34b0fe2ec), and the OOM-rescue race question.
3. Shorten to at most 3000 words by the command sed 's/<[^>]*>//g' final.html | wc -w (the CSS and SVG labels count). Cuts in this order until inside: duplicated mechanism detail between the section-5 paragraph, the figure labels and the bullets (keep one statement per fact, cite once); repeated resolved/unresolved statements between 7.1 and 8; the Words table rows for terms used only once in a sentence that already defines them inline. Never cut a number, a citation that is the only support for a claim, a required section, or a definition of a term that is used more than once.
4. Re-render both SVGs with cairosvg, view them with Read, fix overlaps, and report the measured word count.
Return the path, the word count, what you applied, and what you rejected with the reason.
${COMMON}`, { label: 'revise', phase: 'Revise', schema: DRAFT_SCHEMA, effort: 'max' })
log(`revised: ${rev?.words}w`)

phase('Final check')
const [f, p, r] = await parallel([
  () => agent(`Fact refuter, round 2. Page: ${A.scratch}/final.html. Check EVERY number, id, date, file:line, percentage, t value, test count and causal claim against the facts bundle (including its LATER COMMITS AND RE-TEST section) and the sources. Report wrong facts (quote + correction), invented facts, and anything the round-1 report asked for that is still missing (${A.scratch}/final-check-reports.json). Default to reporting when uncertain. Do not judge style.\n${COMMON}`, { label: 'facts:r2', phase: 'Final check', schema: FACT_SCHEMA, effort: 'max' }),
  () => agent(`Plain-english skill, Check mode, on ${A.scratch}/final.html (Rule 1: terms in the page's Words table count as defined; a term defined inline at first use counts too). List every remaining violation with the exact phrase and a fix. Measure the visible words with sed 's/<[^>]*>//g' | wc -w. Do not invent violations.`, { label: 'english:r2', phase: 'Final check', schema: PE_SCHEMA, effort: 'max' }),
  () => agent(`Render check, round 2, on ${A.scratch}/final.html: pure ASCII (python bytes isascii), balanced tags (html.parser), each inline SVG rendered with cairosvg and viewed with the Read tool (overlapping labels, labels crossing arrows, cut text, unreadable size, axis start stated on the page, value labels on every marker, legend in words), section numbering consistent with cross-references, every table header row with units. Return the problem list.`, { label: 'render:r2', phase: 'Final check', schema: RENDER_SCHEMA }),
])
return { rev, facts: f, english: p, render: r }