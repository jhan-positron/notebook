export const meta = {
  name: 'easy-read-review',
  description: 'Check the easy-read page: numbers against the facts sheet, and plain-English rules',
  phases: [{ title: 'Review' }],
}
const PAGE = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html'
const GEN = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/easy_read.py'
const FACTS = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md'
const SCHEMA = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  where: { type: 'string' }, quote: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string', enum: ['wrong', 'misleading', 'style'] } },
  required: ['where', 'quote', 'problem', 'fix', 'severity'] } } }, required: ['findings'] }
const common = `Read-only review. Do not edit any file. Do not log in to any machine. The page is ${PAGE}; it is built by ${GEN} (read the generator: text and both SVG figures are there). Report only real defects, each with the exact quoted phrase and a concrete replacement. An empty list is a valid answer.`
phase('Review')
const r = await parallel([
  () => agent(`${common}\n\nTask: check EVERY number and every factual claim on the page (text, tables, both figures' data arrays and labels, the flow boxes, the open items, the load statement) against the facts sheet ${FACTS}. The facts sheet is the source of truth. Flag: a number that differs; a range attributed to the wrong loop, layout or stop rule; a claim stronger than the facts sheet supports (for example a universal statement where the sheet has exceptions, or a hypothesis stated as a fact); a percentage that does not follow from its two values (recompute); a count that is wrong (for example how many loops are fast, slow, between; how many layouts; how many variants). Also check that the P array in the generator matches the table of F2 row by row.`, { label: 'numbers', phase: 'Review', schema: SCHEMA }),
  () => agent(`${common}\n\nTask: check the prose against the plain-english skill rules (the skill text is in your instructions): Short version of at most three sentences that a newcomer can follow; one claim per sentence; short sentences; no idioms or metaphors; every number has a unit; estimates marked est.; every project term, code name and abbreviation defined at first use or in the "Words used here" list (the list is the WORDS array in the generator; check that every term used on the page that needs a definition is in it, and that no term is used before the reader can find it); every step has the four parts Question, Idea, Test, Result and the Result answers the Question; the tag "Idea held" or "Idea rejected" matches the Result text. Read as an engineer who has never seen the project. Flag at most the 15 most important defects.`, { label: 'plain-english', phase: 'Review', schema: SCHEMA }),
])
return r.filter(Boolean).flatMap(x => x.findings)
