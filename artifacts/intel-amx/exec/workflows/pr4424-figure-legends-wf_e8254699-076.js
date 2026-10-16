export const meta = {
  name: 'pr4424-figure-legends',
  description: 'Add a per-figure Colour and font scheme (legend) to every diagram of the three PR 4424 pages, check it against the SVG, review and fix',
  phases: [
    { title: 'Declare', detail: 'one agent per figure module adds legend=[...] to each figure()' },
    { title: 'Build', detail: 'build each page, check_page + check_legend' },
    { title: 'Review', detail: 'legend text vs the rendered figure' },
    { title: 'Fix', detail: 'apply findings, rebuild, recheck' },
  ],
}

const G = '/home/jhan/workspace/intel-AMX/exec/pr4424-diagrams-20261009'
const OUT = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424'
const FILES = [
  { key: 'kv_cache', units: ['c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10'], out: `${OUT}/diagramming-code-changes-kv_cache.hpp.html` },
  { key: 'k_vnni', units: ['k0', 'k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7', 'k8', 'k9'], out: `${OUT}/diagramming-code-changes-k_vnni.hpp.html` },
  { key: 'model', units: ['m0', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7'], out: `${OUT}/diagramming-code-changes-model.hpp.html` },
]

const DECL_SCHEMA = { type: 'object', properties: {
  module: { type: 'string' }, figures: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, n_entries: { type: 'number' }, custom_entries: { type: 'array', items: { type: 'string' } } }, required: ['id', 'n_entries'] } },
  check_problems: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' },
}, required: ['module', 'figures', 'check_problems'] }

const declPrompt = (f, mod) => `TASK: give every figure of the module ${G}/figs/${mod}.py its own "Colour and font scheme" (the user's new rule: at each section or diagram, repeat the scheme but only with the colours and fonts that diagram uses; a style the global scheme does not list, such as the plain white box of a data-model entity, must appear in the figure's own scheme with what it marks there).
Read first: the section "The per-figure Colour and font scheme" at the end of ${G}/STYLE.md, and the LEGEND catalogue + legend item forms in ${G}/svg_helpers.py (search for "LEGEND = {" and "def legend_entries").
Steps:
1. cd ${G} && python3 check_legend.py --show figs/${mod}.py   -> for each figure, the box styles (box:fill:stroke:d|s:t|n), arrow colours and fonts it uses, and the coloured text colours.
2. Look at each figure's PNG (${G}/png/page_${f.key}/<figure id>.png; if it is missing or stale, run python3 render_one.py figs/${mod}.py and open ${G}/png/<figure id>.png) and read the module's drawing code, so you know what each style MARKS in that figure.
3. In the module, add legend=[...] to every figure(...) call (also the figures returned by figs()). Use catalogue keys where the catalogue label is exact for this figure; use ("key", "label") when the label must say what the style marks here (for example ("box", "white box, ink outline: the data-model entities plane, token block c, token i, dimension step s; name in bold monospace, description in grey sans-serif"), or ("rm", "orange: the row-major form of block 2 (panels (s, 2))")); use ("label", fill, stroke, dashed, thick) for a style that is not in the catalogue (a thick orange frame, a solid blue column, a grey band ...), and ("label", "arrow", stroke) for an arrow colour. Declare the fonts the figure uses (font_mono, font_sans, font_cite, font_tag). Labels: plain English, names from the code, say what the style marks in THIS figure, one short clause each.
4. Rerun check_legend.py on the module until it prints 0 legend problems (no MISSING, no UNUSED). A MISSING "coloured text #rrggbb" means a label is drawn in a concept colour: declare an entry whose stroke is that colour (a catalogue key of that concept, or a custom entry such as ("blue labels: the VNNI form", "none", C["vnni"], False, False) if no box of that colour exists).
Do not change any drawing (no coordinates, no colours, no text); only add the legend declarations. Do not edit other modules or shared files. Return the structured output.`

const BUILD_SCHEMA = { type: 'object', properties: { built: { type: 'boolean' }, check_page: { type: 'array', items: { type: 'string' } }, check_legend: { type: 'array', items: { type: 'string' } }, fixes: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['built', 'check_page', 'check_legend'] }
const buildPrompt = (f, round) => `Build and check the ${f.key} page (round ${round}). cd ${G}; run: python3 spec_builder.py ${f.key}; python3 check_page.py ${f.out}; python3 check_legend.py ${f.out}. If a figure module fails to import (a syntax error from a legend edit) fix that minimally. If check_legend reports MISSING or UNUSED entries for a figure, fix that figure's legend declaration in its module (figs/base_${f.key}.py or figs/d_${f.key}_<unit>.py) following ${G}/STYLE.md ("The per-figure Colour and font scheme") and rebuild, until both checkers print 0 problems. Do not change drawings. Report the remaining problems verbatim (empty lists when none).`

const REVIEW_SCHEMA = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, figure: { type: 'string' }, severity: { type: 'string', enum: ['must', 'should', 'nit'] }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'figure', 'severity', 'problem', 'fix'] } }, summary: { type: 'string' } }, required: ['findings', 'summary'] }
const reviewPrompt = (f) => `REVIEW the per-figure "Colour and font scheme" legends of the ${f.key} page ${f.out}. For every figure (grep '<div class="figlegend">' in the page; the figure id is the <svg id> just before it; the rendered figure is ${G}/png/page_${f.key}/<id>.png, open it): compare the legend's entries with what is visible. Report: (a) an entry whose label does not say what the style marks in THIS figure (a generic catalogue phrase where the figure uses the style for something specific, e.g. "a box with a name from the code" when the white boxes are the plane entities, or "VNNI layout" when the blue is the pair rows of panel (2,2)); (b) a visible style with no entry (a thick frame, a dashed box, a coloured label, a solid column, a tinted band); (c) an entry that nothing in the figure uses; (d) a label that breaks plain English (undefined shorthand, two claims in one clause, an idiom); (e) the legend of a figure that is much longer than needed (merge entries that mark the same concept). Also confirm the request line "At each section or its diagrams, repeat Colour and font scheme but only include the color/font used in the section/diagrams" is satisfied for the base-diagram section and every unit. fix = the exact replacement entry/label. Be exhaustive; one finding per defect.`

const FIX_SCHEMA = { type: 'object', properties: { applied: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } }, check_page: { type: 'array', items: { type: 'string' } }, check_legend: { type: 'array', items: { type: 'string' } } }, required: ['applied', 'skipped', 'check_page', 'check_legend'] }
const fixPrompt = (f, findings) => `Apply the legend findings below to the ${f.key} page's figure modules (${G}/figs/base_${f.key}.py, ${G}/figs/d_${f.key}_<unit>.py): edit only the legend=[...] declarations (and their labels), following ${G}/STYLE.md ("The per-figure Colour and font scheme") and the catalogue in ${G}/svg_helpers.py. Never change a drawing. Skip a finding only when it is wrong (say why, citing the figure or the checker output). Then cd ${G} && python3 spec_builder.py ${f.key} && python3 check_page.py ${f.out} && python3 check_legend.py ${f.out}; both must print 0 problems (fix until they do). Report what you applied and skipped and the checkers' remaining output verbatim.
FINDINGS: ${JSON.stringify(findings)}`

const result = await pipeline(
  FILES,
  async (f) => {
    const mods = [`base_${f.key}`].concat(f.units.map(u => `d_${f.key}_${u}`))
    const outs = await parallel(mods.map(m => () => agent(declPrompt(f, m), { label: `declare:${m}`, phase: 'Declare', schema: DECL_SCHEMA })))
    const bad = outs.map((o, i) => (!o || (o.check_problems || []).length) ? mods[i] : null).filter(Boolean)
    log(`${f.key}: legends declared in ${mods.length} modules; modules with leftover problems: ${bad.join(', ') || 'none'}`)
    return { mods, bad }
  },
  async (st, f) => {
    const b1 = await agent(buildPrompt(f, 1), { label: `build1:${f.key}`, phase: 'Build', schema: BUILD_SCHEMA })
    log(`${f.key}: build 1 page=${b1 && b1.check_page.length} legend=${b1 && b1.check_legend.length}`)
    const rv = await agent(reviewPrompt(f), { label: `review:${f.key}`, phase: 'Review', schema: REVIEW_SCHEMA })
    const findings = rv ? rv.findings : []
    log(`${f.key}: review -> ${findings.length} findings (${findings.filter(x => x.severity === 'must').length} must)`)
    const fx = findings.length ? await agent(fixPrompt(f, findings), { label: `fix:${f.key}`, phase: 'Fix', schema: FIX_SCHEMA }) : null
    const b2 = await agent(buildPrompt(f, 2), { label: `build-final:${f.key}`, phase: 'Build', schema: BUILD_SCHEMA })
    return { key: f.key, declared: st, build1: b1, findings: findings.length, fix: fx, buildFinal: b2 }
  }
)
return result
