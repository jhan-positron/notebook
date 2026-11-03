export const meta = {
  name: 'ben-stack-predictions',
  description: 'Predict what Ben would dislike in PRs 4957/4958/4959 from his PR 5047 and his review record, refute each prediction, and critique the design brief',
  phases: [
    { title: 'Find', detail: '3 PRs x 4 lenses' },
    { title: 'Refute', detail: '3 refuters per finding, majority' },
    { title: 'Critique', detail: 'design brief critics + completeness' },
  ],
}
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad'
const K = S + '/stack'
const PRS = [
  { n: 4957, wt: '/home/jhan/workspace/ai-runs/tron-split-pr2', head: '26b86a279a', base: 'a5697f86d3', title: 'Use VNNI K layout in AMX attention' },
  { n: 4958, wt: '/home/jhan/workspace/ai-runs/tron-split-pr3', head: 'b39765ec29', base: '26b86a279a', title: 'Save K in 16-token blocks, shared with idle worker threads' },
  { n: 4959, wt: '/home/jhan/workspace/ai-runs/tron-split-pr4', head: '6b081187e1', base: 'b39765ec29', title: 'Keep short K writes row-major; enable VNNI K in the deb preset' },
]
const LENSES = [
  { key: 'structure', prompt: `Lens: PR 5047's structure (profile items P1-P5). Where does this PR put K-layout knowledge or layout branching outside the cache (self_attention.hpp, model.hpp, scheduler/full.hpp, tests), re-add public raw views, braid two control flows in one loop or function, or re-introduce compile-time layout clauses at call sites? Where would it conflict with Ben's page::score_k / try_score_k_amx / set_k_row(expr) consolidation (the simulated merge has conflicts: see design.md section 1)? For each site say what Ben's PR 5047 did to the equivalent PR 4956 code.` },
  { key: 'record', prompt: `Lens: Ben's past review comments (profile items C1-C16, full text in ben-corpus.md). Apply each item to the lines this PR adds: names a newcomer cannot decode, environment variables, functions near or over 100-200 lines, two control-flow paths in one function, hand-rolled bitmaps where mask_t/bitset exist, uint16_t for bf16, raw pointers without layout meaning, a new parallel entry point instead of extending an existing one, named bool constants, Note names, comments he could not follow, reads outside ISO C++, code without users, repeated subtle patterns, intermediates not in the per-worker state, std::array vs vector, magic constants without comments, memory orders.` },
  { key: 'abstraction', prompt: `Lens: the ben-review skill (file /home/jhan/.claude/skills/ben-review/SKILL.md; read it first). Look for missing shared domain abstractions, argument lists longer than four parameters (runtime and template lists separately), repeated low-level representation details that obscure a concept (bit masks, panel arithmetic, pointer arrays, __mmask16 in a cache API, decltype-based element-type detection), and "several values describing one concept". Name the concrete reading cost and the smallest remedy, and preserve the caller's real decisions.` },
  { key: 'interface', prompt: `Lens: the public surface the PR grows and how it will read in a year. List every new public member of page/book/batch/model and every new free function in the headers, with its callers. Which of them exist only for tests, duplicate an existing operation, expose storage representation (uint8_t block masks, __mmask16, raw bf16* row arrays, k_packed views), or encode a protocol that a type should own (the K store window's open/claim/finish/join spread over save_k_impl)? Compare with how PR 5047 shaped page's API (few verbs: score_k, try_score_k_amx, set_k_row, get_k_row).` },
]
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, pr: { type: 'integer' }, file: { type: 'string' }, line: { type: 'integer' },
      hunk: { type: 'string', description: 'at most 2 lines quoted from the PR head' },
      ben_would_say: { type: 'string', description: 'one to three sentences in his register (direct, often a question)' },
      evidence: { type: 'string', description: 'profile item ids (P1..P5, C1..C16) and comment ids / commit shas' },
      severity: { type: 'string', enum: ['block', 'should', 'nit'] },
      remedy: { type: 'string' },
      remedy_in_design: { type: 'string', enum: ['yes', 'partial', 'no'] },
    }, required: ['id', 'pr', 'file', 'line', 'hunk', 'ben_would_say', 'evidence', 'severity', 'remedy', 'remedy_in_design'] } },
    notes: { type: 'string' },
  },
  required: ['findings'],
}
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, severity: { type: 'string', enum: ['block', 'should', 'nit'] } }, required: ['refuted', 'reason', 'severity'] }
const CRITIQUE = { type: 'object', properties: {
  verdicts: { type: 'array', items: { type: 'object', properties: { section: { type: 'string' }, accept: { type: 'boolean' }, concern: { type: 'string' }, change: { type: 'string' } }, required: ['section', 'accept', 'concern', 'change'] } },
  missing: { type: 'array', items: { type: 'string' } },
  notes: { type: 'string' },
}, required: ['verdicts', 'missing'] }

const common = (pr) => `Context files (read them first, in this order): ${K}/ben-profile.md (Ben's taste with evidence ids), ${K}/design.md (the stack, Ben's structure at his head, the planned remedies), ${K}/pr${pr.n}.diff (the PR under review, base ${pr.base}..head ${pr.head}), ${K}/pr${pr.n}-body.md (its description), ${K}/ben-corpus.md (his 28 comments verbatim), ${S}/pr5047-c1.diff and ${S}/pr5047-c2.diff (Ben's two commits on PR 4956). The PR head is checked out read-only at ${pr.wt} (cite line numbers from that tree: file:line at head ${pr.head}). Ben's own tree is at /home/jhan/workspace/ai-runs/tron-pr5047 (head ade89a9d9c). Do not modify any file in any worktree. PR ${pr.n}: "${pr.title}".`

phase('Find')
const perPr = await pipeline(
  PRS.flatMap(pr => LENSES.map(l => ({ pr, l }))),
  ({ pr, l }) => agent(`You predict what Ben (the reviewer) would dislike in PR ${pr.n}, through ONE lens.
${common(pr)}
${l.prompt}
Rules: tie every finding to a line the PR adds or changes (not pre-existing code; the ben-review skill's "preserve existing code" rule applies). Each finding: the file:line at the PR head, a 1-2 line quote, what Ben would say in his own register, the evidence (profile ids + comment ids or commit shas), severity (block = he would request changes; should = he would ask and expect a follow-up; nit), the smallest remedy, and whether design.md already contains that remedy (yes/partial/no). Do not pad: an empty list is a valid answer for a lens. Aim for precision over count. Finding ids: "${l.key}-${pr.n}-<n>".`, { label: `find:${l.key}:${pr.n}`, phase: 'Find', schema: FINDINGS }),
  (found, { pr, l }) => parallel((found?.findings || []).map(f => () =>
    parallel([
      `You are Ben's advocate: refute this prediction unless the record (ben-profile.md, ben-corpus.md, PR 5047's commits) really supports that Ben objects to this kind of thing. A finding built on taste that is not in his record is refuted.`,
      `You are the PR author's advocate: refute this prediction if the quoted code is pre-existing (not added or changed by PR ${pr.n}), if the quote or line is wrong, if the remedy would break behaviour or test expectations, or if the remedy is larger than the problem.`,
      `You are a neutral checker: read the actual code at the cited line in ${pr.wt} and in Ben's tree, and confirm or refute the factual claims of the finding (what the code does, what Ben's tree does instead, the evidence ids). Also set the severity you believe Ben would give.`,
    ].map((role, i) => () => agent(`${role}
${common(pr)}
The prediction to check: ${JSON.stringify(f)}
Return refuted=true only with a concrete reason; otherwise refuted=false. Always return the severity you think is right.`, { label: `refute${i + 1}:${f.id}`, phase: 'Refute', schema: VERDICT }))
    ).then(vs => {
      const v = vs.filter(Boolean)
      const refutes = v.filter(x => x.refuted).length
      const sev = v.map(x => x.severity)
      const rank = { block: 3, should: 2, nit: 1 }
      const median = sev.sort((a, b) => rank[a] - rank[b])[Math.floor(sev.length / 2)] || f.severity
      return { ...f, kept: refutes < 2, votes: v.map(x => ({ refuted: x.refuted, reason: x.reason, severity: x.severity })), severity_final: median }
    })
  )).then(list => ({ pr: pr.n, lens: l.key, findings: list.filter(Boolean) }))
)

phase('Critique')
const critics = await parallel([
  ...PRS.map(pr => () => agent(`Critique the remedies planned for PR ${pr.n} in ${K}/design.md (section 3, the PR${pr.n === 4957 ? "2'" : pr.n === 4958 ? "3'" : "4'"} part, and section 4). ${common(pr)}
For each numbered step/sub-item: would Ben accept it (is it the smallest change that gives one layout owner, typed operations, one control flow per function)? Does it preserve behaviour (bytes, scores, memory orders, test expectations)? What would break in the merge (read the conflict hunks: run \`git -C ${pr.wt} merge-tree $(git -C ${pr.wt} merge-base origin/bgamari/vnnik-1 HEAD) origin/bgamari/vnnik-1 HEAD | grep -n '<<<<<<<' | head\` and inspect)? Name every API the plan invents (pack_amx_query, k_block_tokens, set_k_block overloads, window operations, k_staging_row, the score_k dotter helper) and say whether an existing operation already covers it or a better name/shape exists. Also list anything the plan forgot (tests that reference removed accessors, comments, README.ci.md, Notes, the hetero test, LoopyTronSpec).`, { label: `critique:${pr.n}`, phase: 'Critique', schema: CRITIQUE })),
  () => agent(`Completeness critic. Read ${K}/ben-profile.md, ${K}/design.md, the three diffs ${K}/pr4957.diff ${K}/pr4958.diff ${K}/pr4959.diff and ${K}/ben-corpus.md. Question: what kinds of objections from Ben's record are NOT covered by the lenses "structure / record / abstraction / interface" and the design brief? Examples to test: documentation of the TRON_K_VNNI option and TRON_AMX_DISABLE for users (C2), test coverage shape (CI builds both options off: issue 4865), PR size and commit topicality (he asked for topical commits and a split before), PR body claims, the deb preset decision (option on in the released package), the join watchdog (an abort after 120 s in production code), the decode-time conversion on the forward thread. Return each as a "missing" item with the evidence id, and verdicts on the brief's section 4 rules.`, { label: 'critique:completeness', phase: 'Critique', schema: CRITIQUE }),
])

const all = perPr.filter(Boolean)
const kept = all.flatMap(x => x.findings.filter(f => f.kept))
const dropped = all.flatMap(x => x.findings.filter(f => !f.kept))
log(`findings kept ${kept.length}, refuted ${dropped.length}`)
return { kept, dropped, critics: critics.filter(Boolean) }