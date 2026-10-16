export const meta = {
  name: 'pr4901-body-v9-verify',
  description: 'Refute the two edited paragraphs of PR 4901 body v9 and check their English',
  phases: [{ title: 'Refute' }],
}
const E = '/home/jhan/workspace/intel-AMX/exec/pr4-20261012'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr4'
const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/e6f04fce-1790-4fc0-8220-267a113c6ec1/scratchpad'
const SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'unverifiable'] },
    evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['claim', 'verdict', 'evidence'] } },
  summary: { type: 'string' } }, required: ['findings', 'summary'] }
const common = `Do not edit any file outside ${SP}/v9-<your-label>/. Never run "cd" (a hook fires); use absolute paths and "git -C". Every verdict cites the command and its output. Default to "refuted" when a claim cannot be reproduced.`
phase('Refute')
const tasks = [
  { label: 'facts', prompt: `Tree-evidence refuter. The PR body draft ${E}/pr-body-v9.md differs from ${E}/pr-body-v8.md in two places (run "diff" on them first). Verify every fact of the two new sentences against the git worktree ${W} (branch jhan-vnnik-4-tail-block, head 8ad54a13b1, pushed; base jhan-vnnik-3-shared-save = dfafd13dce): (1) the commits after the implementation commit ea94e95a4e are exactly e7d06a1267 (four benchmark-record rows in config/test-benchmarks.json), 175b1837b9 (the forward-path test case, in t/t_heterogeneous_scheduler*.cpp) and 8ad54a13b1; (2) commit 8ad54a13b1 (git show) cuts comments, replaces exactly three named bool constants (BLOCK_COMPLETED_FALSE, CONVERTED_FALSE, CONVERTED_TRUE) by literals, removes exactly eight [[maybe_unused]] attributes and one "(void)slot;" cast, and respells one all-ones mask from ~uint64_t{} to ~uint64_t{0}; count every added and removed line and classify it, and report any change the sentence does not name; (3) t_heterogeneous_scheduler has 3 cases before 175b1837b9 and 4 from it (count TEST_CASE in the test file at dfafd13dce, 175b1837b9^ and 175b1837b9); (4) "Clean at the head: clang-format on the 11 changed C++ files, git diff --check, and a syntax-only compile in 38 configurations with 0 errors (two no-dispatch configurations warn about unused constants)" holds at 8ad54a13b1 per ${E}/step4-q18.out (read it; check its head line, the clang-format, diff-check, "C++ files" and the warning-cell lines); (5) the counted word total of v9 without the "Words used here" section is under 2,000: run awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' ${E}/pr-body-v9.md | wc -w. ${common}` },
  { label: 'english', prompt: `Apply the plain-english skill in Check mode (rules in your CLAUDE.md context) to the two sentences that differ between ${E}/pr-body-v8.md and ${E}/pr-body-v9.md (run diff; check only the changed lines 41 and 47 of v9). Context: the body's "Words used here" section (lines 11-19 of v9) defines the project terms, and a term defined there or earlier in the body needs no new definition; backticked code names are code, not prose; the PR-description skill forbids change history and clock times. Report each violation as a finding (claim = exact phrase, verdict = refuted, evidence = rule number, fix = corrected phrase). Report zero findings plainly if there are none. Do not edit the files. ${common}` },
]
const results = await parallel(tasks.map(t => () => agent(t.prompt, { label: t.label, phase: 'Refute', schema: SCHEMA }).then(r => ({ label: t.label, ...r }))))
return results.filter(Boolean)