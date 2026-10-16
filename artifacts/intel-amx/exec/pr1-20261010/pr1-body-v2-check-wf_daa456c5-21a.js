export const meta = {
  name: 'pr1-body-v2-check',
  description: 'Check the revised PR #4868 description: facts vs results and code, plain-English rules, description rules',
  phases: [{ title: 'Check' }],
}
const SCHEMA = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit', 'ok'] }, where: { type: 'string' }, claim: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } },
      required: ['severity', 'where', 'claim', 'fix', 'evidence'] } },
    notes: { type: 'string' },
  },
  required: ['findings', 'notes'],
}
const COMMON = `Read-only task: do not modify any file, do not run builds, do not ssh. The text under review is the revised description of PR #4868 (positron-ai/tron, branch jhan-vnnik-1-layout, head 82d05e94be = main 72308ec90c + the PR): /home/jhan/workspace/intel-AMX/exec/pr1-20261010/pr-body-v2.md. It will replace the current description on GitHub. Plain English in your output, no idioms. Cite line numbers of pr-body-v2.md in "where". Mark checks that passed as "ok" findings so the record shows what was checked.`
phase('Check')
const results = await parallel([
  () => agent(`${COMMON}
Lens: FACTS. Check every number, commit id, file name, test name, count and claim in the description against the sources:
- the measured cells: /home/jhan/workspace/intel-AMX/exec/results/pr1b-E-cpu/summary.md (its header line is stale text from an older campaign; the table rows are authoritative) and rt-results.txt in the same directory;
- the unit tests, kill-switch runs, mutation check, build times and format checks: /home/jhan/workspace/intel-AMX/exec/results/pr1b-20261010/ (tests-pr1.txt, tests-pr1nd.txt, tests-pr1rm.txt, mutation-result.txt, build-pr1.txt, build-pr1nd.txt, build-pr1rm.txt, format-pr1.txt, steps.txt) — note build-pr1.log etc. give "build rc=0 in N s";
- the smokes: /home/jhan/workspace/intel-AMX/exec/results/pr1b-20261010/smoke/{cpu-p1024,cpu-p8192,fpga-p1024}/smoke.txt;
- the host suite: /home/jhan/workspace/intel-AMX/exec/results/pr1b-20261010/host-suite-pr1.txt;
- the syntax matrix: /home/jhan/workspace/intel-AMX/exec/pr1-20261010/matrix-pr1b.log (22 cells at 82d05e94be) and /home/jhan/workspace/intel-AMX/exec/pr1-20261010/pr1check-38b.log (38 cells, may still be running: if its last line is not "MATRIX OK" say so);
- the code: worktree /home/jhan/workspace/ai-runs/tron-split-pr1 (git -C <worktree> diff 72308ec90c HEAD for the whole PR diff; the four newest commits answer review comments).
Also recompute the decision bands (the larger of 2 x the largest sd of the two binaries and 0.4 TPS / 0.15 s) and the inside/beyond labels of the pair table, the TTFT percentages, and the decomposition sentence (sum of baseoff-base and newoff-baseoff vs new-base, residual = new-newoff). Check the Open items' older numbers against the PR #4424 description text saved at /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/8fea3a6f-7ad9-451b-8c8e-0abdf5692000/scratchpad/pr4424-body-live.md. Report every mismatch as must-fix with the correct value.`, { label: 'check:facts', phase: 'Check', schema: SCHEMA }),
  () => agent(`${COMMON}
Lens: PLAIN ENGLISH. Load the skill "plain-english" (Skill tool) and run it in Check mode over the whole description: every code name, acronym and metric defined at first use or in the Words table; one claim per sentence; numbers with units and a meaning clause where needed; citations after sentences in brackets; a Short version of at most three sentences first; no idioms or uncommon words; bullets or blank lines between separate points; no sentence with more than one subordinate clause; no semicolons joining clauses. Also check the project rule: the prompt length is written "prompt length N tokens" or "prompt N", never "ctx N". Report each violation with the exact phrase and a corrected phrase (severity nit for style, should-fix for an undefined term or a sentence a newcomer cannot follow). Do not rewrite the whole text; list findings.`, { label: 'check:english', phase: 'Check', schema: SCHEMA }),
  () => agent(`${COMMON}
Lens: DESCRIPTION RULES. Check the description against these rules and report violations:
(1) Present tense, written as of today; no change history, no review-round narration ("round", "previously", "earlier version", "was", "now ... instead of"), no "before/after"; measurements keep provenance only (commit id + date); only the final head against the latest main; no previous-head comparator.
(2) No clock times, no paths into an author's workspace (anything under /home/, /var/tmp/, exec/results), no names of people (roles and links only), no comparison with another head's assertion counts.
(3) Every pending or unmeasured item is its own subsection or bullet with the question and the measurement that would settle it; no claim wider than the code (for example "the next PR removes the loss" must be stated as intended, not measured).
(4) Required sections in order: Short version (three sentences), Background, Words used here, The changes, Measurements, Verification (with a "CI coverage" subsection citing issue #4865), Open items, The stack, the attribution line "🤖 Generated with [Claude Code](https://claude.com/claude-code)" last.
(5) Load the skill "Wade-code-review" (Skill tool) and apply its claim checks to the description: guarantees wider than the code, CI lanes described correctly (required CI gcp-nix.yml builds with both options off; the legacy lane cmake-single-platform.yml sets both on; see .github/workflows in the worktree /home/jhan/workspace/ai-runs/tron-split-pr1 and nix/cmake-tron-test-build.nix), stale result rows, PR-body passages that contradict the code (the gate predicate in h/tron/models/self_attention.hpp, the asserts in h/tron/tensor/k_vnni.hpp, the tolerance selection in t/t_llama_unit.cpp, the staging test in t/t_phase1_integration.cpp).
Report each violation with the exact phrase and a fix.`, { label: 'check:rules', phase: 'Check', schema: SCHEMA }),
])
return results.filter(Boolean)