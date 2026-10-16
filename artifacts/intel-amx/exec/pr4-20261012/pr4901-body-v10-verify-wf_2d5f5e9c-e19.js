export const meta = {
  name: 'pr4901-body-v10-verify',
  description: 'Refute the two edited sentences of PR 4901 body v10 and check their English',
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
const common = `Do not edit any file outside ${SP}/v10-<your-label>/. Never run "cd" (a hook fires); use absolute paths and "git -C". Every verdict cites the command and its output. Default to "refuted" when a claim cannot be reproduced.`
phase('Refute')
const tasks = [
  { label: 'facts', prompt: `Tree-evidence refuter. ${E}/pr-body-v10.md differs from ${E}/pr-body-v9.md in two lines (run diff first). Verify against the worktree ${W} (branch jhan-vnnik-4-tail-block, head d0e6f816dd, pushed): (1) the commits after ea94e95a4e are exactly e7d06a1267, 175b1837b9, 8ad54a13b1, d0e6f816dd; (2) commit d0e6f816dd (git show) changes only t/t_amx_dispatch_dtype.cpp, turns the three default arguments of the test helper exercise_page into literals, deletes the constant RECORD_ROWS_TRUE, and moves the four remaining named bool constants (REPEAT_FALSE, AMX_AVAILABLE_TRUE, AMX_AVAILABLE_FALSE, RECORD_ROWS_FALSE) with their comment into the #ifdef TRON_AMX_DISPATCH block that holds the only test case using them; confirm every use of those four names at d0e6f816dd sits inside that block, and that nothing else changed; (3) origin/jhan-vnnik-4-tail-block is d0e6f816dd (git ls-remote); (4) the sentence "0 errors and 0 warnings" for the 38-configuration syntax-only compile: the record is ${E}/step4-q19.out, which a run in progress writes; if the file exists and contains "done", check its head line is d0e6f816dd, "MATRIX OK: 38 cells", "clang-format rc=0", "diff-check rc=0" and whether any cell line shows warnings != 0 (the lines after "cells with warnings != 0"); if the file is absent or not finished, report this claim as unverifiable and say so; (5) the counted words of v10 without the Words used here section are under 2,000: awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' ${E}/pr-body-v10.md | wc -w. ${common}` },
  { label: 'english', prompt: `Apply the plain-english skill in Check mode (rules in your CLAUDE.md context) to the two lines that differ between ${E}/pr-body-v9.md and ${E}/pr-body-v10.md (run diff; check only the changed text). The body's "Words used here" section (lines 11-19) and earlier text define the project terms; backticked names are code; the PR-description skill forbids change history and clock times. Report each violation as a finding (claim = exact phrase, verdict = refuted, evidence = rule number, fix = corrected phrase); report zero findings plainly if there are none. Do not edit the files. ${common}` },
]
const results = await parallel(tasks.map(t => () => agent(t.prompt, { label: t.label, phase: 'Refute', schema: SCHEMA }).then(r => ({ label: t.label, ...r }))))
return results.filter(Boolean)