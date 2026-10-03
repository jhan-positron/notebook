export const meta = {
  name: 'fix4500-understand',
  description: 'Understand the issue #4500 fix: mechanism from the diff, the two failing unit tests, the smoke result; each claim refuted by 2 skeptics',
  phases: [
    { title: 'Read', detail: 'mechanism, tests, smoke, chain design' },
    { title: 'Refute', detail: 'two skeptics per reader output' },
  ],
}
const A = args
const FACTS_SCHEMA = { type: 'object', properties: {
  facts: { type: 'array', items: { type: 'object', properties: {
    claim: { type: 'string' }, evidence: { type: 'string', description: 'file:line or command output that supports it' } }, required: ['claim','evidence'] } },
  unknowns: { type: 'array', items: { type: 'string' } },
}, required: ['facts','unknowns'] }
const VERDICT_SCHEMA = { type: 'object', properties: {
  verdicts: { type: 'array', items: { type: 'object', properties: {
    claim: { type: 'string' }, refuted: { type: 'boolean' }, why: { type: 'string' }, correction: { type: 'string' } }, required: ['claim','refuted','why'] } },
}, required: ['verdicts'] }

const COMMON = `
SOURCES (read-only; never modify anything):
- The fix branch worktree: ${A.wt} (branch jhan-amx-vnniK-i4500, commits 78e2da7511, 78582b7ba3, 617cb8333f on top of the PR #4424 head 30c4ac82cb). The full diff vs 30c4ac82cb is at ${A.diff} (1643 lines). Use git in ${A.wt} for history.
- The design + campaign memory note: ${A.memo} (written by the session that built the fix; treat it as a plan, verify against the code).
- The chain README: ${A.readme}. Chain results dir: ${A.res} (tests-fix.txt, tests-fix-*.out, smoke/smoke.txt, cells/*/perf.json, build-fix.txt). Chain logs: ${A.logs}/i4500fix-20260928-chain.log and i4500fix-20260928.log.
- Root-cause page of the issue: ${A.rootcause}.
Return raw facts with evidence pointers, plain English (define code names inline once), no narrative. Each claim must be checkable by file:line or a command.`

phase('Read')
const readers = [
  { key: 'mechanism', prompt: `Explain the MECHANISM of the fix from the code (the diff at ${A.diff} and the files in ${A.wt}): what a 16-token K block is, what "row-major until the 16th row" means physically (bytes, cache lines: 4 lines per row vs 64), where the state bits live (kv_cache.hpp), when a block is converted and by which thread (run_forward / convert_pending_k_blocks), what the readers do for row-major vs converted blocks (AMX dense gate, software loop dotter vs qk_group, FPGA staging get_k_row), what happens on clear/copy/restore. Also list what was REMOVED (set_k_block present parameter, K_SCATTER_RUN_LEN_1). Give file:line for every claim. Max 25 facts.` },
  { key: 'tests', prompt: `Two unit tests FAILED in step A of the chain (${A.res}/tests-fix.txt): t_k_vnni_layout.cpp:713 "the EAGLE storage view keeps its own K layout state" (SIGABRT) and t_llama_unit.cpp:1873 "apply and join page ranges" (SIGABRT, "window_excludes_all=0"). Read the .out files in ${A.res}, the test sources at those lines in ${A.wt}/t/, and the code they exercise. For each: what the test checks, whether the test case is NEW in the fix branch or pre-existing (git blame / diff), what aborted (a TRON_ASSERT? which one, file:line), and what it means: a defect in the fix, a defect in the new test, or an environment issue (the tests ran with SYSTEM_CONFIG="--instance 1,2" and the fake device on 3bda). State which is most likely and why, and what a reader cannot conclude yet. Also list the other 5 tests and their results. Max 20 facts.` },
  { key: 'smoke-chain', prompt: `Describe the chain and its results so far, from ${A.readme}, ${A.logs}/i4500fix-20260928-chain.log, ${A.logs}/i4500fix-20260928.log and ${A.res}: the five steps A-E with their UTC times and outcomes, the binaries of step D (base, vnni, fix, nightly: what each is, commit ids, ${A.res}/nightly.sha), the cells (model, tp, users per engine, prompt length, generated tokens, repetitions, the client), the smoke test (what it compares, 12 runs, the IDENTICAL result and what identical tokens do and do not prove), and how the campaign measures TPS. Note the reference numbers of the 09-19 block m6 (vnni -4.3 % tp2, -13.4 % tp4) and how the base differs (canonical AMX deb vs the no-AMX nightly). Do NOT compute the campaign result table (it is still running). Max 25 facts.` },
]
const read = await parallel(readers.map(r => () => agent(`${r.prompt}\n${COMMON}`, { label: `read:${r.key}`, phase: 'Read', schema: FACTS_SCHEMA })))
const named = read.map((r, i) => r && ({ key: readers[i].key, ...r })).filter(Boolean)
log('readers done: ' + named.map(n => `${n.key}=${n.facts.length}`).join(', '))

phase('Refute')
const refuted = await parallel(named.map(n => () =>
  parallel([0, 1].map(k => () => agent(`You are skeptic ${k + 1}. Below are ${n.facts.length} claims about the issue #4500 fix (topic: ${n.key}). For EACH claim, check it against the sources (read the cited file:line yourself; run git/grep). Mark refuted=true when the claim is wrong, unsupported by its evidence, or overstated; give the correction. ${k === 0 ? 'Lens: code correctness and exact numbers/ids.' : 'Lens: wording that a newcomer would misread, and claims that go beyond what the evidence shows.'}\n${COMMON}\n\nCLAIMS:\n${JSON.stringify(n.facts, null, 1)}`,
    { label: `refute:${n.key}:${k + 1}`, phase: 'Refute', schema: VERDICT_SCHEMA })))
  .then(vs => ({ key: n.key, facts: n.facts, unknowns: n.unknowns, verdicts: vs.filter(Boolean) }))))
const out = refuted.filter(Boolean).map(r => {
  const bad = new Map()
  for (const v of r.verdicts) for (const x of v.verdicts) if (x.refuted) bad.set(x.claim, (bad.get(x.claim) || []).concat([x.correction || x.why]))
  return { key: r.key, unknowns: r.unknowns, kept: r.facts.filter(f => !bad.has(f.claim)), corrected: [...bad.entries()].map(([claim, c]) => ({ claim, corrections: c })) }
})
log(out.map(o => `${o.key}: kept ${o.kept.length}, corrected ${o.corrected.length}`).join('; '))
return out