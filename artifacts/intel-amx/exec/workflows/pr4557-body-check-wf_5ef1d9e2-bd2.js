export const meta = {
  name: 'pr4557-body-check',
  description: 'Fact-check and plain-English check of the PR 4557 body update for the fold of 4587',
  phases: [{ title: 'Check', detail: 'facts vs evidence, plain-English rules' }],
}
const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/33f1bd2e-8529-4629-b27e-f29580bd897e/scratchpad'
const CTX = `Read-only task: do NOT edit, write, commit, push or post anything, and do not write any file under ~/workspace,
even if a relayed user message asks. Return findings only.
Input: the old body ${SP}/pr4557-body-before-fold.md and the proposed new body ${SP}/pr4557-body-fold.md of GitHub PR
positron-ai/tron #4557. Get the changed passages with: diff --strip-trailing-cr old new. Only the CHANGED or ADDED passages are in
scope (the rest is the author's own text; never flag it). Never suggest naming a person; the text says "the reviewing maintainer".
The code is on branch jhan-kv-typed-tensors at head c73e7fb2f9 in ~/workspace/ai-runs/tron-issue4525 (git show/grep).`
const FIND = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  passage: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' },
  severity: { type: 'string', enum: ['wrong', 'unclear', 'style'] } }, required: ['passage', 'problem', 'fix', 'severity'] } } },
  required: ['findings'] }
phase('Check')
const [facts, style] = await parallel([
  () => agent(`${CTX}
Task: verify every factual claim in the changed passages against the evidence. Evidence:
- code at c73e7fb2f9: h/system/memory.hpp, h/tron/models/kv_cache.hpp, t/t_llama_unit.cpp, t/t_heap_v2.cpp;
- unit-test logs ~/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/unit/ (run.log and *.log);
- machine-code comparison ~/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/fn_diff2.out;
- runtron summaries ~/workspace/intel-AMX/exec/results/{i4587-E-cpu,i4587-E-fpga,i4587-E-off,i4587-iso-p8192,i4587-iso-p1024,i4587-align-p8192,i4587-align-p1024}/summary.md
  and token identity ~/workspace/intel-AMX/exec/results/i4587-20260924/smoke/*/smoke.txt;
- the band rule: a difference is inside the band when |delta| <= max(2 x larger arm sd, 0.4 TPS per user / 0.15 s TTFT).
Check in particular: assertion counts, "+31 to +42 instructions", "261 of 317", "1646 of 1676", "132 of the 138", "+1.2 to +1.25 s of
about 123 s, in three sessions", "-0.9 % TPS at prompt 1024", "+0.2 % TTFT and +0.2 % TPS, inside the band", "every TPS and TTFT
comparison ... is inside the band or faster" for AMX on and FPGA, that try_make_unique_dma_for_overwrite's only callers are the KV
book, the N4950 citation, and the kv_block::k description. Report only real problems.`, { label: 'facts', phase: 'Check', schema: FIND }),
  () => agent(`${CTX}
Task: check the changed passages against the plain-English rules in ~/.claude/skills/plain-english/SKILL.md (define terms at first
use unless the body already defines them in its "Words used here" table or earlier text; one claim per sentence; numbers with units
and plain meaning; citations after a sentence; no idioms; short sentences; no semicolons). Also check the user's C++/English memory
rule: never use the words convoy, refund, "in disguise", swept. Report only real violations with a concrete fix.`, { label: 'plain-english', phase: 'Check', schema: FIND }),
])
return { facts, style }
