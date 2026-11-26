export const meta = {
  name: 'asimov-outliers-tighten',
  description: 'Split long bullets and remove semicolons in the polished outlier entries without changing any number',
  phases: [{ title: 'Tighten', detail: 'one editor per outlier' }],
}
const S = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/outliers'
const SCHEMA = { type: 'object', properties: { id: { type: 'string' }, one_line: { type: 'string' }, looked_wrong: { type: 'array', items: { type: 'string' } }, why_wrong: { type: 'array', items: { type: 'string' } }, showed: { type: 'array', items: { type: 'string' } }, open: { type: 'string' }, tests: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, run: { type: 'string' }, measures: { type: 'string' } }, required: ['name', 'run', 'measures'] } } }, required: ['id', 'one_line', 'looked_wrong', 'why_wrong', 'showed', 'open', 'tests'] }
phase('Tighten')
const out = await pipeline(args.ids, id => agent(`You are a copy editor. The file ${S}/polished.json holds an array "polished" of entries; read ONLY the entry with id "${id}" (use python3 -I to print json.dumps of that one entry, or grep; do not read the whole file into your context). Edit its text fields (one_line, looked_wrong, why_wrong, showed, open, and the name/run/measures of each test) under these rules, and return the edited fields with the same id:
1. No sentence may carry two claims. Split any bullet longer than 35 words into two or more bullets, each one sentence or two short sentences. Keep the bullets in order; a split bullet becomes consecutive bullets.
2. No semicolons anywhere in prose. Replace a semicolon between clauses with a full stop and a new sentence. Inside a square-bracket citation, replace ';' with ' and ' or split the citation across the bullets it belongs to.
3. Keep every number, unit, run/boot name, file name and citation exactly as written. Do not add, remove or round a number. Do not add any claim. Do not change a term's definition.
4. The test "run" field must stay a canonical token ("run 1", "run 2", "control run", "run 3", "boot A" ... "boot F2", "run 7 (proposed)", "not run", "other"), joined with ", " if several.
5. Keep "est." where it is. Keep the test names short (at most 12 words).
Return only the edited entry.`, { label: `tighten:${id}`, phase: 'Tighten', schema: SCHEMA, effort: 'low' }))
return { tightened: out.filter(Boolean) }