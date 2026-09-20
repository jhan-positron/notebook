export const meta = {
  name: 'tron-concepts-verify',
  description: 'Verify the TRON concepts HTML page: plain-English check, adversarial fact-check of every citation, newcomer critic, brief-completeness critic, code review',
  phases: [
    { title: 'Plain English', detail: '5 checkers, one per section group' },
    { title: 'Fact check', detail: '2 lenses x 6 section groups against TRON source' },
    { title: 'Critics', detail: 'newcomer comprehension, brief completeness, code review' },
  ],
}
const HTML = '/home/jhan/workspace/random/from-claude/TRON-concepts-claude.html'
const SYN = '/tmp/claude-0/-home-jhan-workspace-random/fcd18152-9ade-458a-935d-031499cd5ec4/scratchpad/synthesis.json'
const TRON = '/home/jhan/workspace/tron'
const BRIEF = '/home/jhan/workspace/random/input-2-ai/internalize-concepts.md'

const COMMON = `The page under review is ${HTML} (a single-file HTML page with inline SVG/CSS/JS, about 145 KB). It explains how five TRON concepts fit together (attention, KV cache page, sliding window, visible range of K/V, minibatch) through one mock forward pass. READ-ONLY task: do not edit any file, do not build or run TRON. You may read the HTML with sed/grep/python (strip tags with a small python snippet if that helps), and read TRON source files under ${TRON} (git main, commit 9b11a912ba). Section ids in the HTML: #tbl concept table, #s1 mock pass, #s2 ownership tree, #s3 KV cache page, #s4 visible range, #s5 minibatch, #s6 attention kernel, #s7 sliding window, #s8 lifetime lanes, #s9 pair matrix, #s10 mock vs real constants, #s11 insufficient data, #s12 glossary, #s13 brief, #s14 sources. Figure text and captions also live in the <script> block as JS strings (PAIRS, OWN, STAGES/CAP arrays, status texts).`

const PE_SCHEMA = { type: 'object', properties: {
  sections: { type: 'string' },
  violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'integer', description: '1 define at first use, 2 one claim per sentence, 3 numbers need units and meaning, 4 citation follows a sentence, 5 short version first, 6 no idioms or uncommon words, 7 bullets or blank lines for multi-point paragraphs, 8 short sentences' }, original: { type: 'string', description: 'exact phrase as it appears in the HTML text, short enough to locate with grep' }, fix: { type: 'string', description: 'corrected phrase' }, where: { type: 'string', description: 'section id and element (p, li, td, JS string)' }, severity: { type: 'string', description: 'high: a newcomer cannot follow; medium: rule broken but readable; low: nit' } }, required: ['rule', 'original', 'fix', 'where', 'severity'] } },
  undefined_terms: { type: 'array', items: { type: 'string' }, description: 'code names, acronyms or metrics used before any definition on the page' },
  summary: { type: 'string' } }, required: ['sections', 'violations', 'undefined_terms', 'summary'] }

const PE_GROUPS = [
  { key: 'intro-table', ids: 'the title, subtitle, Short version box, and the concept table (#tbl)' },
  { key: 's1-s3', ids: 'sections #s1, #s2, #s3 (prose, figure legends, takeaways, caveats, callouts) plus the JS strings used by those figures: the tree/traversal status texts and the OWN array labels' },
  { key: 's4-s5', ids: 'sections #s4 and #s5 plus the JS strings STEPS (mask build), chunkEvenly trace texts, and page-list reason texts' },
  { key: 's6-s7', ids: 'sections #s6 and #s7 plus the JS walk() event texts and strips/dumbbell labels' },
  { key: 's8-end', ids: 'sections #s8, #s9, #s10, #s11, #s14 plus the JS CAP array (lane captions) and the PAIRS relation texts' },
]

const FACT_SCHEMA = { type: 'object', properties: {
  sections: { type: 'string' }, lens: { type: 'string' }, claims_checked: { type: 'integer' },
  findings: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, citation: { type: 'string' }, verdict: { type: 'string', description: 'confirmed | refuted | imprecise | unverifiable' }, evidence: { type: 'string', description: 'what the source line actually says, quoted, with file:line' }, severity: { type: 'string', description: 'high: wrong fact a reader would learn; medium: misleading or wrong line number; low: nit' }, suggested_fix: { type: 'string' } }, required: ['claim', 'citation', 'verdict', 'evidence', 'severity', 'suggested_fix'] } },
  summary: { type: 'string' } }, required: ['sections', 'lens', 'claims_checked', 'findings', 'summary'] }

const FACT_GROUPS = [
  { key: 'table-s1', ids: 'the concept table (#tbl) and section #s1 (mock pass, traversal)' },
  { key: 's2-s3', ids: 'section #s2 (ownership tree; verify every box label, lifetime class and parent edge in the OWN array against the code) and section #s3 (KV cache page)' },
  { key: 's4', ids: 'section #s4 (ranged mask) including the STEPS build-order texts and the probe-text reasons in the JS' },
  { key: 's5', ids: 'section #s5 (minibatch) including chunk_evenly rules in the prose and JS, page-list selection rules, dependency claims (kvs_needed = 4), and the pipelining figure' },
  { key: 's6-s7', ids: 'sections #s6 and #s7 (kernel order of tests, sliding window: parent, three application points, position vs token_id, FPGA claim, GPT-OSS 18 of 36, Gemma every sixth layer, fixture window values)' },
  { key: 's8-s11', ids: 'sections #s8 (lane spans and CAP captions), #s9 (PAIRS relation and mock texts), #s10 (constants table), #s11 (insufficient data and doc-vs-code conflicts)' },
]
const LENSES = [
  { key: 'citations', text: 'LENS: CITATION ACCURACY. For every bracketed citation [file:line] in your sections, open the file at that line (read about 15 lines around it) and decide: does the cited line support the exact claim made? Report refuted or imprecise citations with the quote of what the line really says. Also check every number (64, 128, 1024, 4096, INT_MAX, 8, 18 of 36, 127, 1600, 1187 bytes, etc.) against its source.' },
  { key: 'mechanism', text: 'LENS: MECHANISM CORRECTNESS. Ignore line numbers. For every statement about how TRON behaves (what is built when, what persists, what filters what, in which order, per what unit), find the code that implements it and try to REFUTE the statement. Pay special attention to: the claimed order of the kernel tests; whether the window is applied in the traversal (the page says it is not); whether kv_pages is trimmed for the window or HW; whether minibatching is disabled with HW attention (the page says it is not); whether visible() vs sw_required() is chosen as the page states; whether B being the first-inserted child continues S\'s book; whether the page-level window test uses count; token position vs token_id semantics; and the ascent build order (edge B before edge A). Default to reporting a finding when uncertain, with the evidence.' },
]

const CRITIC_SCHEMA = { type: 'object', properties: {
  four_questions: { type: 'array', items: { type: 'object', properties: { question: { type: 'string' }, answered: { type: 'boolean' }, where: { type: 'string' }, gaps: { type: 'string' } }, required: ['question', 'answered', 'where', 'gaps'] } },
  confusing_spots: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, why: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string' } }, required: ['where', 'why', 'fix', 'severity'] } },
  missing: { type: 'array', items: { type: 'string' } },
  strengths: { type: 'array', items: { type: 'string' } },
  overall: { type: 'string' } }, required: ['four_questions', 'confusing_spots', 'missing', 'strengths', 'overall'] }

const BRIEF_SCHEMA = { type: 'object', properties: {
  requirements: { type: 'array', items: { type: 'object', properties: { requirement: { type: 'string' }, met: { type: 'string', description: 'yes | partly | no' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['requirement', 'met', 'evidence', 'fix'] } },
  house_rules: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, met: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'met', 'evidence', 'fix'] } },
  summary: { type: 'string' } }, required: ['requirements', 'house_rules', 'summary'] }

const CODE_SCHEMA = { type: 'object', properties: {
  bugs: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, description: { type: 'string' }, severity: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'description', 'severity', 'fix'] } },
  accessibility: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'description', 'fix'] } },
  summary: { type: 'string' } }, required: ['bugs', 'accessibility', 'summary'] }

phase('Plain English')
const pe = PE_GROUPS.map(g => () => agent(`${COMMON}

You are running the plain-english skill in CHECK mode (its rules are in your CLAUDE.md context: 1 define a term at first use, 2 one claim per sentence, 3 numbers carry units and a plain meaning, 4 citations follow a sentence in brackets, 5 Short version first, 6 no idioms or uncommon words, 7 bullets or blank lines for multi-point paragraphs, 8 short sentences, no semicolons joining clauses).
Check ONLY: ${g.ids}.
Extract the visible text of those parts (python: read the file, take the HTML between the section headings, strip tags, unescape entities; for JS strings read the <script> block). Then list every violation with the exact original phrase (short, greppable), the fix, where it is, and a severity. A term counts as defined if it is defined anywhere EARLIER on the page (the concept table and the Short version come first; the "Words used here" glossary at the end does NOT count as first-use definition). Code identifiers that appear inside <code> tags still need a plain-language definition at first use unless the concept table already defines them. Do not invent violations; report zero if there are none. Keep fixes in the page's existing voice.`, { label: `pe:${g.key}`, phase: 'Plain English', schema: PE_SCHEMA }))

phase('Fact check')
const fc = []
for (const g of FACT_GROUPS) for (const l of LENSES) fc.push(() => agent(`${COMMON}

${l.text}

Check ONLY: ${g.ids}. Extract the claims from the HTML text and the relevant JS strings. Use ${TRON} as the source of truth (grep -n, sed -n). The synthesized concept map at ${SYN} (JSON) lists what the readers found with citations; it is a secondary source, the code wins. Report every refuted, imprecise, or unverifiable claim with quoted evidence. Also report claims that are confirmed only if they were the special-attention items in the lens text (say "confirmed" for those so the author knows they were checked). Give claims_checked as the number of distinct claims you examined.`, { label: `fact:${g.key}:${l.key}`, phase: 'Fact check', schema: FACT_SCHEMA }))

phase('Critics')
const critics = [
  () => agent(`${COMMON}

You are an engineer who knows attention and KV caches from the literature but has never read TRON. Read the page's text top to bottom (strip tags with python; also read the JS strings for figure captions, and understand what each figure draws from its rendering code). Judge whether the page gives you a durable, correct mental model. The brief asked four things: (1) what are the relationships between the five concepts; (2) which bigger parent and grandparent concepts own them, and how relationships go through those parents; (3) do they co-exist or only exist at certain times, and how are they related in sequencing; (4) make sliding window, visible range of K/V, and minibatch individually clear. For each, say whether it is answered, where, and what gap remains. List confusing spots (a place where you would have to guess or re-read) with a concrete fix. List anything missing. Be specific; quote phrases.`, { label: 'critic:newcomer', phase: 'Critics', schema: CRITIC_SCHEMA }),
  () => agent(`${COMMON}

You are the completeness critic. Read the brief at ${BRIEF} and the page. Check every requirement of the brief: relationships; parents and grandparents included; relationships explained at or through parents; sequencing and timing when concepts do not co-exist; individually unclear concepts (sliding window and its parents, visible range of K/V, minibatch) made clear; output file name TRON-concepts-claude.html; plain-english check applied; diagrams, animations, and mock data used; a table of concepts at the top; the prompt file content included verbatim (compare byte-for-byte with the file: the page says 1187 bytes). Also check these house rules from the user's CLAUDE.md: light background only (no dark-mode block); charts annotated with direct labels and a one-line takeaway; exact numbers available in a compact table; estimates labelled est. with units and no estimate where a measurement exists; jargon explained (a glossary exists); Insufficient data named where data is missing; every claim about test results or code grounded in a citation. Report each as yes / partly / no with evidence and a fix.`, { label: 'critic:brief', phase: 'Critics', schema: BRIEF_SCHEMA }),
  () => agent(`${COMMON}

You are reviewing the page's JavaScript and HTML for bugs, in the style of a careful code review. Read the whole <script> block and the figure containers. Look for: event handlers that can throw (null selectors, wrong data attributes), stepper state machines that get stuck or go out of range, intervals that are never cleared, DOM ids referenced but not present (or duplicated), SVG attributes with undefined values (fill="undefined"), text that would overflow its SVG viewBox at the given widths, hard-coded expectations that disagree with the computed MOCK data, the assert block (does it assert what the page claims?), reduced-motion handling, keyboard access to the clickable chips and cells (they are spans and rects with click handlers), missing aria labels on interactive controls, and colour used as the only cue anywhere. For each bug give where (function or element), what happens, severity, and a fix. Do not run a browser; reason from the code. Report only real problems.`, { label: 'critic:code', phase: 'Critics', schema: CODE_SCHEMA }),
]

log('launching 5 plain-English checkers, 12 fact checkers, 3 critics')
const all = await parallel([...pe, ...fc, ...critics])
const [peR, fcR, crR] = [all.slice(0, pe.length), all.slice(pe.length, pe.length + fc.length), all.slice(pe.length + fc.length)]
log(`done: pe ${peR.filter(Boolean).length}/5, fact ${fcR.filter(Boolean).length}/12, critics ${crR.filter(Boolean).length}/3`)
return { plainEnglish: peR, factChecks: fcR, newcomer: crR[0], brief: crR[1], code: crR[2] }