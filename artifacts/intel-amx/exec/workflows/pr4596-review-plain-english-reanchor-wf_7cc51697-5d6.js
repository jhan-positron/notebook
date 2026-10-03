export const meta = {
  name: 'pr4596-review-plain-english-reanchor',
  description: 'Re-anchor the plain-English edits that no longer matched: rewrite the current data string so it carries the intended fix',
  phases: [{ title: 'Reanchor' }],
}
const S = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/scratchpad/pe3'
const N = args.batches
const OUT = { type: 'object', properties: { results: { type: 'array', items: { type: 'object', properties: {
  index: { type: 'number' }, action: { type: 'string', enum: ['rewrite', 'already_fixed', 'skip'] },
  new_current: { type: 'string', description: 'the full replacement for the current string (only for rewrite); keep every fact, number, id, citation, newline and "lens: " prefix' },
  why: { type: 'string' } }, required: ['index', 'action', 'new_current', 'why'] } } }, required: ['results'] }
phase('Reanchor')
const res = await parallel(Array.from({ length: N }, (_, i) => () => agent(`You finish a plain-English pass over a code-review page. Read ${S}/batch-${i}.json: a list of items, each with 'rule' (1 define terms at first use, 2 one claim per sentence, 3 units on numbers, 6 no idioms, 7 bullets or blank lines for several points, 8 short sentences and no semicolons), 'original' (the sentence a checker flagged, from an older version of the text), 'fix' (the checker's replacement), and 'current' (the string as it is now in the page's data; an earlier edit may already have changed it). Also read ${S}/words.txt (terms already defined for the whole document; never re-define them).
For each item: if 'current' already satisfies the rule at that place, answer already_fixed. Otherwise produce new_current = the whole 'current' string with the intended fix applied at the right place, keeping everything else byte-for-byte (newlines, "reach: " / "evidence: " / "intent: " prefixes, code names, numbers, citations in brackets). Never add, remove or reorder a claim. Answer skip only when the fix would change a fact. Output raw data only.`, { label: `reanchor:${i}`, schema: OUT })))
return { batches: res }
