export const meta = {
  name: 'wade-page-check',
  description: 'Check respond-Wade-comments.html: plain-English rules per section and file:line citations against the worktree',
  phases: [
    { title: 'Prose', detail: 'plain-English rule check per section' },
    { title: 'Cite', detail: 'verify every file:line citation of a section against the code' },
  ],
}

const RULES = `Plain-English rules (from ~/.claude/skills/plain-english/SKILL.md, Check mode):
1. Define a term at first use (code names, acronyms, metrics, build variants). A "Words used here" table at the top of the page defines: tron, PR 4596, Wade, AMX, AVX, FPGA attention, kill switch, forward, token job, listener, forward class, minibatch (q_batch), attention job, ready pass, pending pass, join, visit, app pool, attention worker, main helper, row, T1 to T5, off state, on state, hoisted, TRON_ASSERT, A/A run, band, est. Those terms count as defined for every later section. Terms NOT in that table must be defined at their first use in the page (the sections are in page order; a term defined in an earlier section counts as defined). Code identifiers that appear only inside <code> and are explained by the surrounding sentence are acceptable.
2. One claim per sentence (split on because / since / which means / so that / semicolons where a split reads better).
3. Numbers carry units and, where the reader cannot judge, a plain meaning; estimates are labelled est.
4. Citations follow a sentence in brackets; they never replace the sentence.
5. Reports start with a Short version (the page has one at the top).
6. No idioms, metaphors, wordplay, uncommon words.
7. Bullets or blank lines separate several points.
8. Short sentences; no semicolons; at most one subordinate clause.
Also flag: any word from the banned list (convoy, refund, "in disguise", swept), any em dash, any sentence that names a person by anything other than their role or first name as the page already does (Wade, jhan).`

const PROSE_SCHEMA = {
  type: 'object',
  properties: {
    section: { type: 'string' },
    violations: { type: 'array', items: { type: 'object', properties: {
      rule: { type: 'integer' }, original: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string', enum: ['must', 'should', 'nit'] } },
      required: ['rule', 'original', 'fix', 'severity'] } },
    unclear_for_newcomer: { type: 'array', items: { type: 'string' }, description: 'sentences an engineer new to the project could not follow, with a rewrite' },
  },
  required: ['section', 'violations', 'unclear_for_newcomer'],
}

const CITE_SCHEMA = {
  type: 'object',
  properties: {
    section: { type: 'string' },
    checked: { type: 'integer' },
    wrong: { type: 'array', items: { type: 'object', properties: {
      citation: { type: 'string' }, claim: { type: 'string' }, what_is_there: { type: 'string' }, correction: { type: 'string' } },
      required: ['citation', 'claim', 'what_is_there', 'correction'] } },
    factual_errors: { type: 'array', items: { type: 'object', properties: {
      sentence: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, correction: { type: 'string' } },
      required: ['sentence', 'problem', 'evidence', 'correction'] } },
  },
  required: ['section', 'checked', 'wrong', 'factual_errors'],
}

const files = args.files
const skipCite = new Set(['00-head', '01-toc', '02-words', '12-sources'])

phase('Prose')
const results = await pipeline(
  files,
  f => agent(`You are a plain-English CHECKER. Read the section file ${f} (one section of an HTML page rendered to text; "[code block]" marks code, "[figure]" a figure, " | " table cells). Apply the rules below in Check mode. Report every violation with the exact original phrase and a corrected version, ranked must / should / nit. Do not invent violations; report zero if there are none. Also list sentences an engineer who has never seen this project could not follow on first read, each with a rewrite. Return the structured result only.\n\n${RULES}`,
    { label: `prose:${f.split('/').pop()}`, phase: 'Prose', schema: PROSE_SCHEMA, effort: 'medium' }),
  (prose, f) => {
    const base = f.split('/').pop().replace('.txt', '')
    if (skipCite.has(base)) return { file: f, prose, cite: null }
    return agent(`You are a CITATION CHECKER. Read the section file ${f} (one section of a review-analysis page). The code under review is the worktree /home/jhan/workspace/ai-runs/tron-attn-stats at commit 1430736b2a (PR #4596 head). Use ABSOLUTE paths in every command and never run "cd" (the shell prints a directory listing on cd). For EVERY citation of the form <file>:<line> or <file>:<a>-<b> (files under h/, src/, t/, README.stats.md, h/tron/plugins/llama.hpp, and PR3879/new-PRs/new-counters/pr-body.md under /home/jhan/workspace/intel-AMX/, and exec/... under /home/jhan/workspace/intel-AMX/), open the cited lines with sed -n and check that the cited lines contain what the sentence claims. Line numbers may be off by a few lines: report a citation as wrong only if the claimed content is not within 3 lines of the cited range, and give the correct lines. Also check factual statements about the code that carry no citation but name a function or file (for example "run_forward is public", "note_token_path has no production caller"): verify with grep and report errors with evidence. Count how many citations you checked. Return the structured result only.`,
      { label: `cite:${base}`, phase: 'Cite', schema: CITE_SCHEMA, effort: 'high' }).then(cite => ({ file: f, prose, cite }))
  },
)
return results.filter(Boolean)
