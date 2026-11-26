export const meta = {
  name: 'pr5022-pre-post-check',
  description: 'Independent read-only check of the final PR 5022 reply and description against the CI evidence, before they are saved on GitHub',
  phases: [{ title: 'Verify', detail: 'three independent read-only checkers try to refute the final texts' }],
}

const E = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/after-go'
const R = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123'
const W = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'

const COMMON = `
Context. Pull request 5022 of the GitHub repository positron-ai/tron (branch jhan-amx-kvmul16) was fast-forwarded
today, 2026-11-24 18:36 UTC, from ddf843ad97 to 90a9110be5. The two new commits (c6cba6b0f8, 90a9110be5) are the
reviewer Isaac's own fix from his draft PR 5606: the test t_amx_dispatch_dtype now passes the define
TRON_AMX_DISPATCH itself, so its real test case runs in the required CI lane (GCP Nix, option OFF).
Two texts are about to be saved on GitHub. The owner approved their wording. Names in capitals were then replaced
by CI results. Your job is an independent check BEFORE they are saved. Try to REFUTE, not to confirm.

Files (all local, read them):
- ${E}/reply.final.md : the reply that will be posted as one conversation comment on PR 5022.
- ${E}/pr5022-body.final.md : the PR description that will replace the live one.
- ${E}/pr5022-body-live-before-edit.md : the live PR description before the edit.
- ${E}/values.json : the CI values that were filled in.
- ${E}/nix-run-45461355215.json and ${E}/nix-test-host.log : the required lane (GCP Nix) run of the new head and the log of its Test host job.
- ${E}/cmake-run-45461357302-attempt1-jobs.json, ${E}/cmake-run-45461357302-attempt2-jobs.json, ${E}/cmake-test-host-attempt1.log, ${E}/cmake-test-host-attempt2.rest.log, ${E}/cmake-build-attempt1.log : the CMake workflow run started by hand, both attempts.
- ${E}/checks-head-90a9110be5.tsv and ${E}/workflow-runs-head-90a9110be5.tsv : every check run and workflow run of the head.
- ${R}/results.txt and the other files of ${R} : test records of 2026-11-23/24 on the host delphi-3b35 (20 test runs, fault runs, memory and time values). ${R}/registry-check.txt covers config/test-benchmarks.json.
- ${W} : a git worktree of the repository at 90a9110be5 (read-only for you). Useful files: t/CMakeLists.txt, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, config/test-benchmarks.json, bin/slice, .github/workflows/gcp-nix.yml, .github/workflows/cmake-single-platform.yml, .github/workflows/bench-refresh.yml, README.ci.md.

Hard rules for you:
- READ-ONLY. Do not push, commit, edit, post, comment, rerun or start anything. No "git push", no "git commit", no "gh pr edit", no "gh pr comment", no "gh pr review", no "gh run rerun", no "gh workflow run", no "gh api" with -X/-f/-F/--input. Do not ssh to any machine. Do not change any file in ${W}, ${E} or ${R}.
- Read-only GitHub reads (gh run view, gh api GET) are allowed when a local file does not answer a question.
- This machine allows 6 busy CPUs. Run no builds and no tests.
- Every finding needs a quoted sentence from the text and the evidence (file and line, or command and its output) that contradicts it. If you cannot name evidence, do not report it as a finding. Write "Insufficient data" where a claim can be neither confirmed nor refuted, and name what would resolve it.
- Do not report style preferences. The wording is approved. Report only: a statement that is false, a statement the evidence does not support, a stale statement, a broken link or number, or a markup problem that changes what GitHub shows.
`

const SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['ok', 'not_ok'] },
    checked: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, result: { type: 'string', enum: ['supported', 'refuted', 'insufficient_data'] }, evidence: { type: 'string' } },
      required: ['claim', 'result', 'evidence'] } },
    findings: { type: 'array', items: { type: 'object', properties: {
      text: { type: 'string', enum: ['reply', 'description', 'both'] },
      quote: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' },
      severity: { type: 'string', enum: ['blocker', 'should_fix', 'note'] } },
      required: ['text', 'quote', 'problem', 'evidence', 'severity'] } },
  },
  required: ['verdict', 'checked', 'findings'],
}

const TASKS = [
  { key: 'reply-facts', prompt: COMMON + `
Your part: the reply (${E}/reply.final.md). Split it into single claims (about 20). For each claim find the evidence
and decide supported / refuted / insufficient_data. Check in particular:
- both run ids, that each link target equals its link text, and which workflow each run belongs to;
- "the jobs Build Tron and Test host pass" and "The Test host log lists t_amx_dispatch_dtype as passed" for run 45461355215;
- "test-host passes 106 of 106 tests on delphi-3bd6-0, a Granite Rapids runner" (which attempt, which CPU model, do the AMX flags appear in that log) and "That workflow builds with TRON_AMX_DISPATCH ON" (build log);
- "passes 30,747 assertions in 1 test case" with the option OFF on delphi-3b35, and "When the registration loses the define, 5 of its 9 sections fail" (records in ${R});
- "still record the placeholder case, 8 MB" (config/test-benchmarks.json at the head, both rows of t_amx_dispatch_dtype) and "peaks at 96.75 to 99.0 MiB" (records in ${R});
- "The current values of both rows come from the weekly refresh (bench-refresh.yml). It measures main on both machine classes." (git log/blame of the rows in ${W}, and the workflow file);
- "Slice plans the schedule and the memory budget from these rows, and it sets no limit from them." (bin/slice in ${W});
- "the description lists the rows under Open items" and "The Verification section of the description now describes the new head" (against ${E}/pr5022-body.final.md).
` },
  { key: 'description-facts', prompt: COMMON + `
Your part: the description (${E}/pr5022-body.final.md).
1. Diff it against ${E}/pr5022-body-live-before-edit.md. List every changed place. There must be exactly seven replacements in five changed lines and nothing else (no lost character, no changed table cell elsewhere).
2. For each changed sentence decide supported / refuted / insufficient_data against the evidence. In particular: the head 90a9110be5, the host, the date 2026-11-24 and the record name pr5606-check-20261123; "Both jobs pass. t_amx_dispatch_dtype and the transpose case run. Four t_amx_numerics cases are compiled out." for the option-OFF build (count the TEST_CASE blocks of t/t_amx_numerics.cpp inside and outside the #ifdef, and check the nix Test host log); the CMake row (run id, runner delphi-3bd6-0, Xeon 6962P, attempt 2, "The build and both test jobs pass", 106 of 106); "The dispatch test uses fake kernels and passes TRON_AMX_DISPATCH itself. It and the transpose case need no AMX CPU."; the Open items sentence.
3. Then read the WHOLE final description once more and look for any OTHER sentence, table cell or number that the two new commits or the new CI runs made stale or false at the head 90a9110be5 and that the seven replacements did not touch. Examples of what to look for: another mention of ddf843ad97 or of an old run id, a sentence that says the dispatch test is compiled out or runs only with the option ON, a count of tests or cases, a statement about README.ci.md or t/CMakeLists.txt that the commits changed (see "git -C ${W} diff ddf843ad97 90a9110be5"). Report each with the quote and the contradicting evidence.
4. Count the words of the final description with the rule "split at white space". It must be under 2,000.
` },
  { key: 'render-and-rules', prompt: COMMON + `
Your part: what a reader on GitHub will see, and the owner's rules.
1. Markdown. For both final texts, look for anything GitHub would render differently from the plain intent: an unbalanced backtick, a bare underscore or asterisk outside code that starts emphasis, a pipe inside a table cell that splits the cell, a "#number" or "@name" outside code that links or notifies someone other than intended (the reply's "#5606" is intended and must link to pull request 5606), a line break inside a paragraph, a list that does not start after a blank line. You may render a text with GitHub's markdown service, which publishes nothing: gh api markdown --input - with a JSON body {"text": ..., "mode": "gfm", "context": "positron-ai/tron"} on stdin (this single POST is allowed, it only renders). Compare the table of the Verification section in the rendered description before and after: the same number of rows and cells.
2. Owner's rules for a reply to a reviewer: no promise of later work, no mention of issue 3997, no word that grades the work down ("only", "merely", "I accept"), no claim that a measurement is impossible, simplest and shortest explanation, every number with a unit. Report a violation only with the quoted words.
3. Consistency between the two texts and with the page that the owner approved: /home/jhan/workspace/intel-AMX/muse-glimmer/round2-respond-2-issac.html, section 7 (id="reply"). The final reply must equal the draft of that section word for word, except for the filled names RUN_ID_NIX, RUN_ID_CMAKE, N_PASS, N_TOTAL and RUNNER_NAME. The seven description edits must equal the table "Edits to the PR description" of that section, with CPU_MODEL and ATTEMPT_N filled as well. Report any other difference.
4. Check that every statement the reply makes about the description is true for ${E}/pr5022-body.final.md.
` },
]

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(t.prompt, { label: `verify:${t.key}`, phase: 'Verify', schema: SCHEMA, effort: 'high' })
    .then(r => ({ key: t.key, ...r }))))
const ok = results.filter(Boolean)
log(`${ok.length} of ${TASKS.length} checkers returned`)
return {
  missing: TASKS.map(t => t.key).filter(k => !ok.some(r => r.key === k)),
  verdicts: ok.map(r => ({ key: r.key, verdict: r.verdict, n_checked: r.checked.length,
    refuted: r.checked.filter(c => c.result === 'refuted'), insufficient: r.checked.filter(c => c.result === 'insufficient_data'),
    findings: r.findings })),
}
