export const meta = {
  name: 'pr4596-review-plain-english',
  description: 'Plain-English check (Check mode) of every text chunk of claude-review.html, then a verifier per chunk',
  phases: [{ title: 'Check' }, { title: 'Verify' }],
}
const S = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/scratchpad/pe'
const CHUNKS = ['intro', 'words', 'scope', 'wade', 'themes', 'findings-0', 'findings-1', 'findings-2', 'findings-3', 'findings-4', 'findings-5', 'findings-6', 'findings-7', 'findings-8', 'findings-9', 'findings-10', 'findings-11', 'findings-12', 'findings-13', 'findings-14', 'testdata', 'counters', 'conditions-0', 'conditions-1', 'tests-0', 'tests-1', 'proposed', 'correct-0', 'correct-1', 'correct-2', 'questions', 'rejected', 'method']
const RULES = `
Plain-English rules (Check mode). Apply ALL of them to the chunk:
1. Define a term at first use in the DOCUMENT. The document's "Words used here" list (file ${S}/words.txt) already defines these terms: tron, runtron, rinzler, PR 4596, head, base, TRON_ATTN_STATS, AVX, AMX, FPGA, TRON_AMX_DISABLE, token job, forward, listener, kv_only, forward class, decode_like, prompt_or_mixed, visit, ready page, pending page, KV page, layer, KV head, kv_mul, pool worker, attention worker, n_attn_workers, T1..T5, TSC cycles, tsc_hz, join, FUSE leaf, forward_scope, hook, model_stats, TRON_ASSERT, W1..W5, EAGLE, the severity words, the evidence strengths, discriminating check. Do NOT flag those. DO flag any other code name, acronym, metric or project shorthand that the chunk uses without a definition in the same chunk (examples: GQA, TTFT, TPS, A/A, ODR, TBAA, objdump, rdtsc, perfetto, Catch2, ccache, nix, ninja, spdlog, q_batch, minibatch, latch arena, hw_plan, PosDevice, MoE, tp2, sd, p95, ulp, bf16). A file path or a function name in code font needs no definition. Inside a quoted code block (lines that are C++ or JSON) do not flag anything.
2. One claim per sentence. Flag sentences that chain a test, an observation and a meaning with "because", "since", "which means", "so that" or a semicolon; give the split version.
3. Numbers carry units and a plain meaning. Flag a bare number whose unit or meaning the reader cannot judge (a count of cycles without "TSC cycles" or a time; a percentage with no base). Line numbers, commit ids, counts of items in a table, and ids need no unit.
4. Citations follow a sentence in brackets; a citation must not replace the sentence. Flag "See file:line." style sentences.
5. A "Short version" exists at the top of the document already; do not flag its absence in a chunk.
6. No idioms, metaphors, wordplay or uncommon words. Flag and give the literal verb.
7. Use bullets or blank lines to separate points; flag a paragraph that carries several separate points in one run (give the split, using " / " between the new paragraphs).
8. Short sentences; flag a sentence with more than one subordinate clause and give the split. A semicolon must become two sentences.
`
const CHECK = { type: 'object', properties: { chunk: { type: 'string' }, violations: { type: 'array', items: { type: 'object', properties: {
  rule: { type: 'number' }, original: { type: 'string', description: 'the exact phrase or sentence from the chunk, verbatim, long enough to be unique (a whole sentence is best)' },
  fix: { type: 'string', description: 'the replacement text, keeping every fact, number and citation' } }, required: ['rule', 'original', 'fix'] } },
  count_by_rule: { type: 'object', additionalProperties: { type: 'number' } } }, required: ['chunk', 'violations', 'count_by_rule'] }
phase('Check')
const checks = await parallel(CHUNKS.map(c => () => agent(`You are the plain-English checker for one chunk of a code-review page (review of tron PR 4596). Read the chunk: cat ${S}/${c}.txt ; and the document's term list: cat ${S}/words.txt.\n${RULES}\nOutput every violation as {rule, original, fix}. 'original' must be copied verbatim from the chunk (it will be replaced by exact string match, so keep punctuation, quotes and spacing exactly; do not include the ' | ' table separators or the leading 'Trigger'/'Consequence' labels). Keep every fact, number, id and citation in the fix. Do not rewrite text that already follows the rules. Do not invent violations to fill the list; report zero if there are none. Lines that are C++ or JSON code are exempt.`, { label: `check:${c}`, schema: CHECK })))
const found = checks.filter(Boolean)
log(`check: ${found.length} chunks, ${found.reduce((n, c) => n + c.violations.length, 0)} violations`)

phase('Verify')
const VER = { type: 'object', properties: { chunk: { type: 'string' }, keep: { type: 'array', items: { type: 'number' }, description: 'indices of violations to apply as given' },
  amend: { type: 'array', items: { type: 'object', properties: { index: { type: 'number' }, fix: { type: 'string' }, why: { type: 'string' } }, required: ['index', 'fix', 'why'] } },
  drop: { type: 'array', items: { type: 'object', properties: { index: { type: 'number' }, why: { type: 'string' } }, required: ['index', 'why'] } } }, required: ['chunk', 'keep', 'amend', 'drop'] }
const verified = await parallel(found.map(c => () => agent(`You verify a plain-English checker's proposed edits for one chunk of a code-review page. Read the chunk: cat ${S}/${c.chunk}.txt and the term list: cat ${S}/words.txt.\n${RULES}\nPROPOSED EDITS (index = position in this list):\n${JSON.stringify(c.violations, null, 1)}\nFor each edit decide: keep (the original appears verbatim in the chunk, the fix keeps every fact, number, id and citation, and the fix itself obeys the rules), amend (give a better fix), or drop (not a violation, or the fix changes a fact, or the original is not verbatim). Be strict about facts: a fix may not add, remove or reorder a claim. Do not drop an edit only because it is small.`, { label: `verify:${c.chunk}`, schema: VER })))
const final = []
found.forEach((c, i) => {
  const v = verified[i]
  if (!v) { c.violations.forEach(x => final.push({ chunk: c.chunk, ...x })); return }
  const amend = new Map(v.amend.map(a => [a.index, a.fix]))
  const drop = new Set(v.drop.map(d => d.index))
  c.violations.forEach((x, k) => { if (drop.has(k)) return; final.push({ chunk: c.chunk, rule: x.rule, original: x.original, fix: amend.has(k) ? amend.get(k) : x.fix }) })
})
log(`final edits: ${final.length}`)
return { edits: final, dropped: verified.filter(Boolean).flatMap(v => v.drop.map(d => ({ chunk: v.chunk, ...d }))), byRule: found.map(c => ({ chunk: c.chunk, count_by_rule: c.count_by_rule })) }
