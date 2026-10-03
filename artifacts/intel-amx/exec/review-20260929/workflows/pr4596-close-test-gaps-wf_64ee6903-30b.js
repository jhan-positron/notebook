export const meta = {
  name: 'pr4596-close-test-gaps',
  description: 'Add unit tests for the five should-fix test gaps of PR 4596, mutation-check each, review, fix, commit (no push)',
  phases: [{ title: 'Implement' }, { title: 'Review' }, { title: 'Fix' }],
}
const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const S = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/scratchpad'
const CTX = `
Context: tron PR #4596 (attention path stats behind TRON_ATTN_STATS), branch jhan-attn-path-stats, worktree ${WT}, HEAD 04da001cb5 (= the pushed PR head). A review found five should-fix unit-test gaps; their full specifications (trigger, evidence with file:line at HEAD, discriminating check, suggested fix) are in ${S}/test-gaps-5.json. Read that file first, then ${WT}/AGENTS.md (repository rules, including the test and comment policy) and the C++ guide via the Skill tool "cpp-coding-guide" (named values instead of bare literals, also 0/1/true/false).
Build rules on this host (claude-box, AMD, no AMX unit, no FPGA):
- gen/ is already configured (native preset, RelWithDebInfo, TRON_AMX_DISPATCH=ON, no model exports). Build ONLY inside the nix shell: cd ${WT} && ~/.nix-profile/bin/nix develop --command bash -c 'ninja -C gen -j 20 <targets>'. Never run cmake or ninja outside that shell (it wipes the cache).
- Run tests as: cd ${WT} && env -u SYSTEM_CONFIG ./gen/<binary> [catch2 args]. Catch2 filters: ./gen/t_llama_unit "<case name>" ; sections via -c "<section>".
- Test binaries: t_llama_unit (compiles t/t_llama_unit.cpp + t/t_attn_stats.cpp), t_heterogeneous_scheduler (t/heterogeneous_scheduler_compile.cpp), t_amx_dispatch_dtype (t/t_amx_dispatch_dtype.cpp), t_trace_passes_host (t/t_trace_passes_host.cpp; check its add_catch_test block at t/CMakeLists.txt:223 for its libraries and labels before relying on it; if it needs an exported model or hardware, say so and use another entry point that reaches model::state::forward with fakes, e.g. the fake-device fixtures of t/heterogeneous_scheduler_compile.cpp or t/t_llama_unit.cpp).
- Format changed C++ files with clang-format 19 before committing (try 'clang-format --version' inside the nix shell; else 'uvx clang-format@19'); the repo has .clang-format.
- Commit rules: git add only the files you changed; commit with --no-verify (lefthook is absent here). Subject line in the branch's style: 'Attention path stats: <what>' (see git log -5 for the style); body in plain English (define terms at first use, one claim per sentence, units on numbers, no idioms): what was missing, what the test drives, which deliberate break makes it fail (the mutation you ran), and end with the line 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'. One commit per gap. Do NOT push. Do NOT rebase. Do NOT touch production behavior except for a mutation that you revert before committing (verify with git diff that h/ is clean before each commit).
- Never modify files outside ${WT}. Never checkout another branch.
Terms: forward = one model execution over the scheduled token jobs; decode_like = every token job has a listener, prompt_or_mixed otherwise; T1..T5 the PR's timers in TSC cycles; pool worker = app thread pool index, attention workers = the last n_attn_workers pool workers; visit = one apply_page_tok call; path bits = per-token-job bits (AVX, AMX, FPGA) folded into token_jobs_by_path_set at the end of a forward.
`
const IMPL_SCHEMA = { type: 'object', properties: {
  gaps: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, status: { type: 'string', enum: ['done', 'partial', 'blocked'] },
    commit: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
    test_added: { type: 'string', description: 'case/section names and file:lines' },
    entry_point: { type: 'string', description: 'the production function the test drives' },
    run_result: { type: 'string', description: 'binary, filter, assertions passed, wall time' },
    mutation: { type: 'string', description: 'the deliberate production break applied, the failing assertion text observed, and confirmation it was reverted (git diff h/ empty)' },
    notes: { type: 'string' },
  }, required: ['id', 'status', 'commit', 'files', 'test_added', 'entry_point', 'run_result', 'mutation', 'notes'] } },
  full_runs: { type: 'string', description: 'the final full run of every touched binary with TRON_ATTN_STATS unset and =1: pass/fail, case and assertion counts' },
  git_log: { type: 'string' },
}, required: ['gaps', 'full_runs', 'git_log'] }

phase('Implement')
const impl = await agent(`${CTX}
Task: close the five gaps in this order: R1-M15 (t/t_attn_stats.cpp: reduce or delete the case that pins raw-hook misuse, keeping the durable statement), R1-M2 (path bits read back through token_jobs_by_path_set in t/t_llama_unit.cpp and t/t_amx_dispatch_dtype.cpp), R1-M8 (T2/T3/T4 hooks through run_attention_job in t/heterogeneous_scheduler_compile.cpp with an installed enabled stats object), R1-M9 (note_fpga_pass call site through prepare_uniform_hw_attention with the fake device fixture), R1-M1 (a test that drives model::state::forward with stats on and checks the forwards record: forwards, token_jobs, listener_jobs + kv_only_jobs, n_attn_workers). For each gap: (1) read the spec and the surrounding test code at HEAD; (2) write the smallest test that calls the PRODUCTION boundary named in the spec (not the hook); use named constants; the fake must keep the information that could be wrong; (3) build the target and run the new case alone, then the whole binary; (4) MUTATION CHECK: apply one deliberate semantic break in production code that the test is meant to catch (the spec's discriminating check names one), rebuild, run, confirm the NEW assertion fails and quote the failure, then git checkout -- the production file and confirm git diff h/ is empty; (5) clang-format the changed test files; (6) commit. If a gap cannot be closed as specified (fixture missing, entry point needs hardware), do the closest meaningful test and say exactly what is left, status partial. At the end run every touched binary in full with TRON_ATTN_STATS unset and =1. Report raw data only.`, { label: 'implement', schema: IMPL_SCHEMA })
log(`implement: ${impl ? impl.gaps.map(g => g.id + ':' + g.status).join(' ') : 'null'}`)

phase('Review')
const REV = { type: 'object', properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['accept', 'needs_change'] },
  calls_production_boundary: { type: 'string' }, fake_retains_information: { type: 'string' }, break_that_fails_it: { type: 'string' }, breaks_not_caught: { type: 'string' },
  guide_violations: { type: 'array', items: { type: 'string' } }, flakiness: { type: 'string' }, commit_message_issues: { type: 'array', items: { type: 'string' } },
  required_changes: { type: 'array', items: { type: 'string' } }, evidence: { type: 'string' } }, required: ['id', 'verdict', 'calls_production_boundary', 'fake_retains_information', 'break_that_fails_it', 'breaks_not_caught', 'guide_violations', 'flakiness', 'commit_message_issues', 'required_changes', 'evidence'] }
const gaps = impl ? impl.gaps : []
const reviews = (await parallel(gaps.map(g => () => agent(`${CTX}
Task: REVIEW ONE NEW TEST, read-only (do not edit, build, or commit; you may run the existing binaries with catch2 filters). Gap ${g.id}. Implementer's report: ${JSON.stringify(g)}. Read the commit (git -C ${WT} show ${g.commit}) and the spec in test-gaps-5.json. Answer the tron-code-review test questions: does it call the changed production boundary (name the call chain from the test to the production function)? Does its fake retain the information that could be wrong? What deliberate semantic break makes the assertion fail, and which related breaks would NOT be caught? Is any assertion timing-dependent or host-dependent (thread start latency, rdtsc, worker counts on a machine with fewer cores)? Does it follow the C++ guide (named values, no bare 0/1/true/false where the guide forbids them) and AGENTS.md (test comment policy: describe the contract, not a past mistake)? Is the commit message plain English and accurate (compare its claims to the diff)? List required changes precisely (file:line, exact replacement) or accept.`, { label: `review:${g.id}`, schema: REV })))).filter(Boolean)
log(`review: ${reviews.map(r => r.id + ':' + r.verdict).join(' ')}`)

phase('Fix')
const needs = reviews.filter(r => r.verdict === 'needs_change')
let fix = null
if (needs.length) {
  fix = await agent(`${CTX}
Task: apply the reviewers' required changes to the commits you (a previous agent) made on this branch, then rebuild, re-run the affected binaries, and rewrite history ONLY for the local unpushed commits made in this session (git log 04da001cb5..HEAD): amend or add fixup commits with --no-verify as appropriate (interactive rebase is not available; use 'git commit --fixup' followed by 'GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash 04da001cb5' or simply amend when the change belongs to the tip). Confirm git diff h/ is empty and every touched binary passes in full with TRON_ATTN_STATS unset and =1. Report raw data.
REVIEWS WITH REQUIRED CHANGES:
${JSON.stringify(needs, null, 1)}`, { label: 'fix', schema: IMPL_SCHEMA })
}
return { impl, reviews, fix }
