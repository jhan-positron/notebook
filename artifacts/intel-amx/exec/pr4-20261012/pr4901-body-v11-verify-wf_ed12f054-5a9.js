export const meta = {
  name: 'pr4901-body-v11-verify',
  description: 'Refute the edited sentence of PR 4901 body v11 and check its English',
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
const common = `Do not edit any file outside ${SP}/v11-<your-label>/. Never run "cd" (a hook fires); use absolute paths and "git -C". Every verdict cites the command and its output. Default to "refuted" when a claim cannot be reproduced.`
phase('Refute')
const tasks = [
  { label: 'facts', prompt: `Tree-evidence refuter. ${E}/pr-body-v11.md differs from ${E}/pr-body-v10.md in one line (run diff first). Verify against the worktree ${W} (branch jhan-vnnik-4-tail-block, head 4d64013dff, pushed): (1) the commits after ea94e95a4e are exactly e7d06a1267, 175b1837b9, 8ad54a13b1, d0e6f816dd, 4d64013dff; (2) commit 4d64013dff (git show) changes only t/heterogeneous_scheduler_compile.cpp, adds the two constants HAS_HARDWARE_GEOMETRY_TRUE and FORCE_HW_ATTENTION_FALSE and uses them as the template arguments of software_scored_heterogeneous_scheduler_tp1 in place of bare true and false, and changes nothing else; that t/CMakeLists.txt builds this file as the t_heterogeneous_scheduler binary; that the fixture's comment calls it software-scored; (3) origin/jhan-vnnik-4-tail-block is 4d64013dff (git ls-remote); (4) the body's sentence "a syntax-only compile in 38 configurations with 0 errors and 0 warnings" at this head: the record ${E}/step4-q20.out is being written by a run in progress (about 3 minutes); if it exists and contains a line starting with "done", check its head line is 4d64013dff, "MATRIX OK: 38 cells", "clang-format rc=0", "diff-check rc=0", and that ${E}/pr4check-out-q20/summary.txt has 38 lines all with warnings=0; if it is not finished after you have waited up to 4 minutes (use "timeout 240 tail -f --pid=<pid of 'bash step4.sh q20'> <file>" or an until-loop with Monitor), report the claim as unverifiable and say so; (5) the counted words of v11 without the Words used here section are under 2,000: awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' ${E}/pr-body-v11.md | wc -w. ${common}` },
  { label: 'english', prompt: `Apply the plain-english skill in Check mode (rules in your CLAUDE.md context) to the one line that differs between ${E}/pr-body-v10.md and ${E}/pr-body-v11.md (run diff; check only the changed text). The body's "Words used here" section (lines 11-19) and earlier text define the project terms; backticked names are code; the PR-description skill forbids change history and clock times. Report each violation as a finding (claim = exact phrase, verdict = refuted, evidence = rule number, fix = corrected phrase); report zero findings plainly if there are none. Do not edit the files. ${common}` },
]
const results = await parallel(tasks.map(t => () => agent(t.prompt, { label: t.label, phase: 'Refute', schema: SCHEMA }).then(r => ({ label: t.label, ...r }))))
return results.filter(Boolean)