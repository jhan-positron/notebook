export const meta = {
  name: 'pr4424-diagram-pages',
  description: 'Draw the base and per-change diagrams of the three PR 4424 pages, assemble, check, review and fix them',
  phases: [
    { title: 'Base', detail: 'five base diagrams per file' },
    { title: 'Change', detail: 'one diagram per logical unit' },
    { title: 'Build', detail: 'assemble the page, static checks, render' },
    { title: 'Review', detail: 'visual, requirements, facts+English lenses' },
    { title: 'Fix', detail: 'apply findings, rebuild, recheck' },
  ],
}

const G = '/home/jhan/workspace/intel-AMX/exec/pr4424-diagrams-20261009'
const OUT = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424'
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-merge-4737-2-4424/daed4d8b-e695-45e4-a9c9-1635c10014f7/scratchpad/diffs'
const WT = '/home/jhan/workspace/ai-runs/tron-vnnik-i4500m'
const REF = '/home/jhan/workspace/intel-AMX/exec/pr4737-diagrams-20261001'

const FILES = [
  { key: 'kv_cache', file: 'h/tron/models/kv_cache.hpp', head: `${S}/kv_cache.hpp.head`, diff: `${S}/kv_cache.hpp.diff`, out: `${OUT}/diagramming-code-changes-kv_cache.hpp.html`,
    related: [`${S}/tensor_k_vnni.hpp.head`, `${S}/model.hpp.diff`, `${S}/self_attention.hpp.diff`, `${S}/full.hpp.diff`, `${S}/gof.hpp.diff`] },
  { key: 'k_vnni', file: 'h/tron/tensor/k_vnni.hpp', head: `${S}/tensor_k_vnni.hpp.head`, diff: `${S}/tensor_k_vnni.hpp.diff`, out: `${OUT}/diagramming-code-changes-k_vnni.hpp.html`,
    related: [`${S}/kernels_k_vnni.hpp.head`, `${S}/kv_cache.hpp.diff`, `${S}/model.hpp.diff`, `${S}/self_attention.hpp.diff`, `${S}/amx_attn.cpp.diff`] },
  { key: 'model', file: 'h/tron/models/model.hpp', head: `${S}/model.hpp.head`, diff: `${S}/model.hpp.diff`, out: `${OUT}/diagramming-code-changes-model.hpp.html`,
    related: [`${S}/common.hpp.diff`, `${S}/kv_cache.hpp.diff`, `${S}/tensor_k_vnni.hpp.head`, `${S}/TronCpp.hs.diff`, `${S}/self_attention.hpp.diff`] },
]
const UNITS = {
  kv_cache: ['c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10'],
  k_vnni: ['k0', 'k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7', 'k8', 'k9'],
  model: ['m0', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7'],
}

const CTX = (f) => `CONTEXT. You are drawing diagrams for a page that explains what tron PR 4424 (branch jhan-amx-vnniK, head 9d5c7a389b, base main be0d5565b3) changes in ${f.file}. Three such pages exist (keys kv_cache, k_vnni, model); yours is key "${f.key}".
Read FIRST, in this order: ${G}/STYLE.md (the drawing rules; binding), ${G}/svg_helpers.py (the only primitives you may use; do NOT edit it), ${G}/units_${f.key}.json (the page's units: titles, head line ranges, verified lead bullets; and the base diagram list: ids, titles, intros), ${G}/facts/${f.key}.json (VERIFIED facts: data_box, cardinality, function, sequence_step, thread_rule claims with citations; every label, count, one-line description and citation in your diagrams must come from here or from the code itself).
Code: the file at the head with head line numbers: ${f.head}; its diff vs main: ${f.diff}; related files of the PR: ${f.related.join(', ')}; the full worktree (read-only, grep/sed only): ${WT}.
Idiom reference (style only, a different PR and a different base): ${REF}/diagrams_base.py and ${REF}/diagrams_changes.py. Do not copy their facts.
Hard rules: names from the code only; every box cites its defining line or Note (cite() in the box AND in figure(boxes=[...])); every function cell has a one-line description; every data-model arrow is labelled with how many; colours per STYLE.md; threads as lanes or [bracketed names]; ASCII only; nothing overlaps. Write only the file(s) named below. Never edit another agent's module, units_*.json, facts/*.json, page_common.py or svg_helpers.py (if you need a new primitive, define it inside your own module).
Checking: run \`cd ${G} && python3 render_one.py figs/<your module>.py\`, then open EVERY png it printed with the Read tool and look at it. Fix clipped text, text on lines, overlapping boxes, labels narrower than their text (use text_width), unreadable sizes; re-render; repeat until clean. Your final answer is the structured output only.`

const BASE_SCHEMA = { type: 'object', properties: {
  module: { type: 'string' },
  figures: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, width: { type: 'number' }, height: { type: 'number' }, boxes: { type: 'number' }, arrows_with_counts: { type: 'number' }, fn_cells: { type: 'number' } }, required: ['id', 'title'] } },
  exports_for_change_diagrams: { type: 'array', items: { type: 'string' } },
  render_rounds: { type: 'number' },
  issues_fixed: { type: 'array', items: { type: 'string' } },
  open_problems: { type: 'array', items: { type: 'string' } },
}, required: ['module', 'figures', 'exports_for_change_diagrams'] }

const basePrompt = (f) => `${CTX(f)}
TASK: write ${G}/figs/base_${f.key}.py with the FIVE base diagrams of this page: functions b1(), b2(), b3(), b4(), b5(), one per entry of "base" in units_${f.key}.json, in that order, each returning figure(fid, W, H, aria, body, caption, boxes=[...]) with fid = the entry's id ("${f.key}-b1" ...). Each diagram's content is what the entry's title and intro say (data model with cardinalities; the geometry/type model; the function model with one-line descriptions per cell and callers in other files; the sequencing model; the interaction model with thread lanes or a decision model). Base diagrams are 1000 wide. Use the page's WORKED EXAMPLE from STYLE.md and export its constants and any building-block functions (block rows, bit rows, the plane/panel grid, lane helpers, the window table ...) at module level so the change-diagram agents can \`from base_${f.key} import ...\` them; list those names in exports_for_change_diagrams. Tag what the PR adds ("new") or changes ("changed") versus pre-existing context in the function model and the data model. Cite with head line numbers of ${f.file} (e.g. "kv_cache.hpp:2608-2622") or "<other file>:<line>" for other files, or "Note [name] (<file>:<a>-<b>)". Captions: 1-3 plain-English sentences each (define any term at first use, one claim per sentence, no idioms).
Mind the size: five rich figures. Spend your effort on correctness and legibility, not decoration. Render and inspect every figure before answering.`

const CHANGE_SCHEMA = { type: 'object', properties: {
  module: { type: 'string' }, figure_ids: { type: 'array', items: { type: 'string' } }, base_sentence: { type: 'string' },
  what_the_diagram_shows: { type: 'string' }, boxes: { type: 'number' }, render_rounds: { type: 'number' },
  issues_fixed: { type: 'array', items: { type: 'string' } }, open_problems: { type: 'array', items: { type: 'string' } },
}, required: ['module', 'figure_ids', 'base_sentence', 'what_the_diagram_shows'] }

const changePrompt = (f, uid, baseInfo) => `${CTX(f)}
The base diagrams of this page already exist in ${G}/figs/base_${f.key}.py (read it; it exports these building blocks and worked-example constants: ${JSON.stringify(baseInfo.exports_for_change_diagrams || [])}; its figures: ${JSON.stringify((baseInfo.figures || []).map(x => x.id + ' ' + x.title))}). Reuse them so your diagram looks like a piece of the base diagram it updates.
TASK: draw the diagram of ONE logical change: unit "${uid}" of units_${f.key}.json (read its title, kind, ranges and lead bullets there; read the code of its head line ranges in ${f.head} with the comments, and the diff). Write ${G}/figs/d_${f.key}_${uid}.py exposing fig() -> the HTML of one figure with fid "${f.key}-d${uid.replace(/^[a-z]+/, '')}" (or figs() -> a list of two figures with fids "...a" and "...b" when one figure cannot carry the change legibly), and a module-level string BASE = "Updates B<n>: <how this change alters that base diagram, one sentence>". The figure sits BESIDE the code in a half-width column: viewBox width 640-720, height as needed (<= 900). It must illustrate what these lines change: the data model they add or alter, the check they make between two models, the path they add, the before -> after when behaviour changes (old state in C['gone'] dashed, marked "before"/"removed"; new in C['new']). Draw the worked example where a concrete instance helps. Every box: a name from the code + cite; every function cell: a one-line description; every data-model arrow: how many. Memory orders, return values and thread names that the lead bullets state belong on the figure as labels ([main thread], acq_rel ...). Caption: 2-3 plain-English sentences starting with the BASE sentence's "Updates B<n>" idea and saying what to look at. For a comment-only unit (${uid} ends with 0), the figure maps the Note's paragraphs/items to the base diagrams they describe (a paragraph list with arrows to B-diagram names and the lines each paragraph covers).
Render (python3 render_one.py figs/d_${f.key}_${uid}.py), Read the png(s), fix, repeat until clean.`

const BUILD_SCHEMA = { type: 'object', properties: {
  built: { type: 'boolean' }, page: { type: 'string' }, bytes: { type: 'number' }, svgs: { type: 'number' },
  check_problems: { type: 'array', items: { type: 'string' } }, fixes_applied: { type: 'array', items: { type: 'string' } },
  png_dir: { type: 'string' }, notes: { type: 'string' },
}, required: ['built', 'page', 'check_problems'] }

const buildPrompt = (f, round) => `You assemble and check the diagram page for ${f.file} (key "${f.key}", round ${round}). Working dir: ${G}. Read ${G}/STYLE.md first.
Steps (run them, fix, rerun until the build passes):
1. cd ${G} && python3 spec_builder.py ${f.key}   -> writes ${f.out}. If a figure module (figs/base_${f.key}.py, figs/d_${f.key}_<unit>.py) fails to import or raises, fix THAT module minimally (a missing BASE string, a wrong function name, a syntax error, a missing export); do not redesign figures. If the build asserts "uncovered added lines", report it (do not edit units_${f.key}.json ranges yourself unless the fix is an obvious one-line range typo; say what you did).
2. python3 check_page.py ${f.out}   -> fix every class-1/2/3/4/6 problem in the responsible module (ASCII, duplicate ids, markers, missing diagram, missing caption or box register, dangling anchors). Class-5 problems ("box not found at its source") are real citation errors: fix the cite in the module to the line that defines the box (verify in ${f.head} or the related file in ${WT}); class-7 (width estimate) must be checked visually: open the png and fix only if the text really exceeds the box or viewBox.
3. python3 render_check.py ${f.out} ${G}/png/page_${f.key}   -> renders every svg of the page; this is the png set the reviewers read.
Report the remaining check_page problems verbatim (empty list if none), what you fixed, the page size and svg count.`

const REVIEW_SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, where: { type: 'string' }, severity: { type: 'string', enum: ['must', 'should', 'nit'] },
    problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } }, required: ['id', 'where', 'severity', 'problem', 'fix'] } },
  summary: { type: 'string' },
}, required: ['findings', 'summary'] }

const reviewPrompts = (f, round) => ({
  visual: `VISUAL REVIEW, round ${round}, of the diagram page ${f.out} (key "${f.key}"). The rendered figures are the PNG files ${G}/png/page_${f.key}/*.png (one per svg id; run ls to list them, then open EVERY one with the Read tool and look at it carefully). For each figure report every legibility defect: text clipped at an edge, text running over a line or arrow, two texts overlapping, a box over another box, a label wider than its box, an arrowhead missing or pointing at nothing, a label that does not sit next to the thing it names, text smaller than ~8.5 px at the figure's natural width, a figure whose height makes it unreadable beside code (change diagrams are shown at about half the page width), a figure that does not show what its caption says. Also judge each figure as a reader: can an engineer new to tron follow it? Say what is missing or confusing. Rules binding the figures: ${G}/STYLE.md. where = the figure id (e.g. "${f.key}-d3") and the module (figs/d_${f.key}_c3.py). fix = the concrete change (move label X right by 12 px; widen box to 180; split into two figures; ...). severity: must = unreadable or wrong, should = clearly worse than it should be, nit = polish.`,
  requirements: `REQUIREMENTS REVIEW, round ${round}, of the diagram page ${f.out} (key "${f.key}"), its figure modules ${G}/figs/base_${f.key}.py and ${G}/figs/d_${f.key}_*.py, and ${G}/units_${f.key}.json. Read ${G}/STYLE.md. Check every requirement of the user's request (quoted verbatim at the top of the page, section "The request") and of STYLE.md, one by one, and report every violation with evidence:
(a) the prompt is included literally at the top; a table of contents is at the top; (b) EVERY logical unit in section 2 has at least one diagram, and the diagram shows THAT change (not a generic picture): read the unit's code excerpt and lead bullets and judge; (c) trivial changes are listed (section 3) with their code; (d) code comments stay with the code in the excerpts; (e) code and diagram are side by side (CSS .side) for every unit; (f) consistent colours: the same concept has the same colour in every figure of the page (grep the modules for C[...] uses: e.g. a VNNI block drawn in a non-vnni colour, a work unit not in unit colour, a thread drawn as a colour); (g) base diagrams exist for data model, function model, sequencing model, interaction model, and each change diagram says which base diagram it updates (BASE string / caption "Updates B<n>") and visibly reuses its shapes; (h) NO INVENTED SHORTHAND: every box label is an identifier or a comment phrase from the code: for every box label in every figure(boxes=[...]) register, grep it (the identifier part) in ${f.head} or the related files under ${WT}; report labels that do not exist; (i) every box cites the comment or line that defines it (the cite points at the DEFINITION, not at a use); (j) every function cell carries a one-line description; (k) every arrow between data-model boxes is labelled with how many, and the count expression exists in the code (n_slots + 1, n_kv_heads, 16, 4 ...); (l) all three target pages share one scheme: compare with ${G}/svg_helpers.py C tokens. Also run \`python3 ${G}/check_page.py ${f.out}\` and include its problems. where = figure id + module, or the page section. fix = concrete.`,
  facts: `FACTS AND PLAIN-ENGLISH REVIEW, round ${round}, of the diagram page ${f.out} (key "${f.key}"). Sources of truth: the code at the head ${f.head} (head line numbers), the diff ${f.diff}, related files ${f.related.join(', ')}, the worktree ${WT} (read-only), and the verified facts ${G}/facts/${f.key}.json. Check every sentence of: the Short version, the base-diagram intros, every figure caption (the <figcaption> text in the page), every box register entry, every unit's lead bullets, the glossary, section 3 and section 5. Two lenses: (1) FACTS: is the sentence true of the code? are the numbers, names, line numbers, memory orders, thread names and counts right? does a diagram label contradict the code (read the SVG text content in the page or the module)? (2) PLAIN ENGLISH (the rules are in the global CLAUDE.md you were given: define every code name, acronym and metric at first use or in Words used here; one claim per sentence; numbers carry units and a meaning; citations follow a sentence in brackets; no idioms or metaphors; short sentences, no semicolons; bullets for several points). The lead bullets came from reviewers and some pack several claims into one sentence: propose split versions. For each finding give the exact original text and the exact replacement text (fix). where = "caption <figure id>" / "unit <id> lead bullet <n>" / "glossary <term>" / "intro <B-id>" / "short version" / "box register <figure id> <label>". severity: must = false statement or wrong number/name/line; should = plain-English rule broken or an undefined term; nit = wording.`,
})

const FIX_SCHEMA = { type: 'object', properties: {
  applied: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
  rebuilt: { type: 'boolean' }, check_problems: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' },
}, required: ['applied', 'skipped', 'rebuilt', 'check_problems'] }

const fixPrompt = (f, round, findings) => `FIX ROUND ${round} for the diagram page of ${f.file} (key "${f.key}"). Working dir ${G}; read ${G}/STYLE.md. Apply EVERY finding below in order of severity (must, then should, then nit) by editing the responsible file: a figure module (${G}/figs/base_${f.key}.py or ${G}/figs/d_${f.key}_<unit>.py), or ${G}/units_${f.key}.json (lead bullets, glossary, short, intros, trivial entries, method). Never edit files of another key, svg_helpers.py, page_common.py, facts/*.json, spec_builder.py or check_page.py. Verify each factual fix against the code (${f.head}, head line numbers; ${WT} read-only) before applying: if a finding is itself wrong, skip it and say why (with the line that shows it). Keep every text ASCII. When several findings touch one figure, redraw that part once.
Then: cd ${G} && python3 spec_builder.py ${f.key} && python3 check_page.py ${f.out} && python3 render_check.py ${f.out} ${G}/png/page_${f.key}; open the pngs of every figure you changed with the Read tool and confirm they are clean (fix and repeat if not). Report what you applied (finding ids), what you skipped and why, and the remaining check_page problems verbatim.
FINDINGS (JSON):
${JSON.stringify(findings)}`

const criticPrompt = (f) => `COMPLETENESS CRITIC for the finished diagram page ${f.out} (key "${f.key}"), modules ${G}/figs/base_${f.key}.py and ${G}/figs/d_${f.key}_*.py, pngs ${G}/png/page_${f.key}/*.png (read them all), units ${G}/units_${f.key}.json, verified facts ${G}/facts/${f.key}.json, code ${f.head} and diff ${f.diff}. Ask: what is still missing or wrong for the user's request (quoted at the top of the page)? Specifically: a unit whose diagram does not explain the change in its lines (generic, or shows a neighbouring concept); a base diagram no change diagram updates; a change diagram that says "Updates B<n>" but shares nothing visible with B<n>; an arrow between data boxes without a count; a box without a cite, or a cite that points at a use rather than the definition; a function cell without a one-line description; a data-model entity of the facts (data_box claims) that no base diagram shows; a sequence_step or thread_rule of the facts that no diagram shows and that a reader needs; a glossary term used on the page but not defined; a lead bullet or caption that a newcomer could not follow. Report findings in the same shape as a review (id, where, severity, problem, fix, evidence), musts first. Be concrete and exhaustive; do not pad with praise.`

const bykey = {}
const result = await pipeline(
  FILES,
  async (f) => {
    const b = await agent(basePrompt(f), { label: `base:${f.key}`, phase: 'Base', schema: BASE_SCHEMA })
    if (!b) throw new Error(`base ${f.key} failed`)
    log(`${f.key}: base diagrams ${(b.figures || []).map(x => x.id).join(' ')}`)
    return b
  },
  async (b, f) => {
    const outs = await parallel(UNITS[f.key].map(uid => () =>
      agent(changePrompt(f, uid, b), { label: `change:${f.key}:${uid}`, phase: 'Change', schema: CHANGE_SCHEMA })))
    const missing = UNITS[f.key].filter((u, i) => !outs[i])
    if (missing.length) log(`${f.key}: change diagrams missing for ${missing.join(', ')}`)
    return { base: b, changes: outs.filter(Boolean), missing }
  },
  async (st, f) => {
    const build1 = await agent(buildPrompt(f, 1), { label: `build1:${f.key}`, phase: 'Build', schema: BUILD_SCHEMA })
    log(`${f.key}: build 1 built=${build1 && build1.built} problems=${build1 ? build1.check_problems.length : '?'}`)
    const rp = reviewPrompts(f, 1)
    const reviews = await parallel(['visual', 'requirements', 'facts'].map(l => () =>
      agent(rp[l], { label: `review1:${f.key}:${l}`, phase: 'Review', schema: REVIEW_SCHEMA })))
    let findings = reviews.filter(Boolean).flatMap((r, i) => r.findings.map(x => ({ ...x, id: `${['V', 'R', 'F'][i]}1-${x.id}` })))
    log(`${f.key}: review 1 -> ${findings.length} findings (${findings.filter(x => x.severity === 'must').length} must)`)
    const fix1 = findings.length ? await agent(fixPrompt(f, 1, findings), { label: `fix1:${f.key}`, phase: 'Fix', schema: FIX_SCHEMA }) : null
    // round 2: visual + requirements again (the fixer changed figures), plus the completeness critic
    const rp2 = reviewPrompts(f, 2)
    const reviews2 = await parallel([
      () => agent(rp2.visual, { label: `review2:${f.key}:visual`, phase: 'Review', schema: REVIEW_SCHEMA }),
      () => agent(rp2.requirements, { label: `review2:${f.key}:requirements`, phase: 'Review', schema: REVIEW_SCHEMA }),
      () => agent(criticPrompt(f), { label: `critic:${f.key}`, phase: 'Review', schema: REVIEW_SCHEMA }),
    ])
    let findings2 = reviews2.filter(Boolean).flatMap((r, i) => r.findings.map(x => ({ ...x, id: `${['V', 'R', 'C'][i]}2-${x.id}` })))
    log(`${f.key}: review 2 -> ${findings2.length} findings (${findings2.filter(x => x.severity === 'must').length} must)`)
    const fix2 = findings2.length ? await agent(fixPrompt(f, 2, findings2), { label: `fix2:${f.key}`, phase: 'Fix', schema: FIX_SCHEMA }) : null
    const build3 = await agent(buildPrompt(f, 3), { label: `build-final:${f.key}`, phase: 'Build', schema: BUILD_SCHEMA })
    bykey[f.key] = { missing: st.missing, build1, findings1: findings.length, fix1, findings2: findings2.length, fix2, buildFinal: build3,
      leftover: findings2.filter(x => x.severity === 'must').map(x => ({ id: x.id, where: x.where, problem: x.problem })) }
    return bykey[f.key]
  }
)
return { perKey: bykey, pipeline_nulls: result.filter(x => !x).length }
