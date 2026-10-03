export const meta = {
  name: 'pr4596-round3-diff-review',
  description: 'Review commit fac3d21d10 of PR 4596 (review round 3): correctness finders, literal completeness, comment plain-English, then refuters',
  phases: [
    { title: 'Find', detail: '4 finders with different lenses over the diff' },
    { title: 'Verify', detail: '2 refuters per finding' },
  ],
}
const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const SHA = 'fac3d21d10'
const CTX = `Repository worktree: ${WT} (tron, branch jhan-attn-path-stats). The commit under review is ${SHA} (HEAD).
Get the diff with: git -C ${WT} show ${SHA} | cat   and read files with: git -C ${WT} show ${SHA}:<path> | cat -n
Its parent 04dab92a77 is the PR #4596 head on GitHub. Do not edit any file. Cite file:line of ${SHA}. Return raw findings.
Context of the commit (the PR author's review, applied): model_stats::on -> enabled and stats_on -> stats_enabled; add_relaxed -> inc_relaxed;
switch_value_turns_on folded into env_enabled and its unit test case deleted; named values COUNT_ONE_1, BIT_SET_1, BIT_CLEAR_0,
INCLUSIVE_INDEX_TO_COUNT_1, FIRST_INDEX_0 removed and literals 0/1 used at their sites (the author's explicit decision, an exception
to the project's C++ guide rule "literal values include 0 and 1"); TIMED_WORKER_0 -> WORKER_0; fpga_bits stores PATH_BIT_FPGA_4 directly;
comments rewritten (path enum, N_PASSES_2, T3, T4 block).`
const FINDINGS = {
  type: 'object',
  properties: { findings: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
    severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
    claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
    required: ['title', 'file', 'line', 'severity', 'claim', 'evidence', 'fix'] } } },
  required: ['findings'],
}
const LENSES = [
  { key: 'correctness', prompt: 'Behavior: does the commit change any counted value, JSON leaf, exit-report line, or off-state cost? Check especially end_forward with fpga_bits holding PATH_BIT_FPGA_4 (begin_forward assigns 0; note_fpga_query writes the bit), env_enabled\'s static lambda (noexcept, warn path, "1" rule), and that every caller of the renamed members compiles: grep the WHOLE tree (h, src, t, ingest) for ->on, .on, stats_on, add_relaxed, switch_value_turns_on, TIMED_WORKER_0, COUNT_ONE_1, BIT_SET_1, BIT_CLEAR_0, INCLUSIVE_INDEX_TO_COUNT_1, FIRST_INDEX_0 at the new commit.' },
  { key: 'names', prompt: 'Name lookup and ABI: t/t_attn_stats.cpp dropped its own WORKER_0 and relies on tron::attn_stats::WORKER_0 through a using-directive; check every test TU that has "using namespace tron::attn_stats" (t_attn_stats.cpp, t_llama_unit.cpp, t_amx_dispatch_dtype.cpp) for any other constant that now collides with a header name (WORKER_0, UNSET_CYCLES_0, LEAF_READ_ONLY_TRUE, AMX_COMPILED_TRUE, N_*). Also check the ctor parameter rename (stats_enabled) against every construction site.' },
  { key: 'literals', prompt: 'Mechanical completeness pass on the + lines of the diff: list EVERY literal token (numeric, bool, char, string, nullptr). For each say whether it is (a) a literal the author explicitly exempted (0/1 as increment, cleared bit, first index, inclusive-to-count), (b) a pre-existing pattern kept, or (c) a NEW bare literal the guide would name. Report class (c) as findings, and report the exempted classes with counts in one finding titled "exemption register" (severity nit).' },
  { key: 'comments', prompt: 'Comments changed by the diff, checked against the project plain-English rules: one claim per sentence, no semicolons, terms defined at first use within the header (Note at the top counts), no idioms, and FACTUAL accuracy against the code: (1) "run_attention_job calls run_sections twice: first over the ready pages, then, after the upstream K/V wait, over the pending pages" (self_attention.hpp run_attention_job), (2) "The FPGA is not a visit path. Its share is counted per hardware pass (note_fpga_pass) and per token job (note_fpga_query)", (3) the T3 comment "elapsed cycles ... in TSC cycles", (4) the T4 block now above NO_OPERATION, (5) the enabled field comment "Nothing is allocated when false" (check the ctor), (6) the fpga_bits trailing comment. Also check README.stats.md and the Note [Attention path stats] text for statements the rename made stale (e.g. "stats->on").' },
]
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, evidence: { type: 'string' } }, required: ['refuted', 'reason', 'evidence'] }

const results = await pipeline(
  LENSES,
  l => agent(`${CTX}\n\nLens: ${l.key}. ${l.prompt}`, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  async (r, l) => {
    if (!r) return null
    const out = []
    for (const f of r.findings) {
      const votes = (await parallel([1, 2].map(k => () =>
        agent(`${CTX}\n\nYou are refuter ${k}. Try to REFUTE this review finding by reading the code at ${SHA}. refuted=true only with concrete contrary evidence (file:line).\nFinding: ${f.title}\nClaim: ${f.claim}\nEvidence: ${f.evidence}\nProposed fix: ${f.fix}`,
          { label: `refute${k}:${l.key}`, phase: 'Verify', schema: VERDICT })))).filter(Boolean)
      out.push({ ...f, lens: l.key, votes, survives: votes.filter(v => v.refuted).length < 2 })
    }
    return out
  },
)
const all = results.filter(Boolean).flat()
log(`${all.length} findings, ${all.filter(f => f.survives).length} survive`)
return { findings: all }