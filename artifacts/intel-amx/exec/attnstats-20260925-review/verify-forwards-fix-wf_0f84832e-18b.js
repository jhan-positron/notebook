export const meta = {
  name: 'verify-forwards-fix',
  description: 'Adversarially verify the render_forwards off-state fix for PR 4596 (three lenses, then a critic)',
  phases: [
    { title: 'Verify', detail: 'three lenses: correctness, contract/docs + siblings, tests + C++ guide' },
    { title: 'Critic', detail: 'merge the lens reports into must-fix / should-fix' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const CTX = `Context. Worktree: ${WT} (branch jhan-attn-path-stats, PR positron-ai/tron #4596). The PR head on GitHub is d85edc0e28; the local HEAD 0a6c0a8582 holds the change under review. Show it with: git -C ${WT} diff d85edc0e28 -- h/tron/models/attn_stats.hpp t/t_attn_stats.cpp
Background: the cursor bot (PR discussion r4109173415) reported that render_forwards in h/tron/models/attn_stats.hpp never checks the member 'enabled' and emits a zero-filled JSON object, while render_totals returns "{}" when the switch is off and README.stats.md (around lines 236-244) promises "{}" for both the <class>_totals and the <class>_forwards leaves. The fix makes render_forwards return "{}" while the switch is off and adds off-state CHECKs to two existing test cases in t/t_attn_stats.cpp (plus a renamed TEST_CASE title).
Rules: do NOT edit any file. Cite file:line for every claim (read the files, do not guess). Default to NO finding when uncertain; if you still want to mention it, mark it severity "info". Return only the structured result.`

const FINDINGS = {
  type: 'object',
  properties: {
    ok: { type: 'boolean', description: 'true when nothing must-fix or should-fix was found' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit', 'info'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'what you read, with file:line' },
        },
        required: ['severity', 'claim', 'evidence'],
      },
    },
    checked: { type: 'array', items: { type: 'string' }, description: 'one line per check you performed, with its outcome' },
  },
  required: ['ok', 'findings', 'checked'],
}

const LENSES = [
  {
    key: 'correctness',
    prompt: `${CTX}

Lens: CORRECTNESS of the renderer change. Try to REFUTE the fix.
1. Compare the OLD render_forwards (git -C ${WT} show d85edc0e28:h/tron/models/attn_stats.hpp, find 'render_forwards') with the NEW one. Prove byte-for-byte that the ON-state output is unchanged: the old code opened with "{{" (fmt escape = one brace) and closed with out += "}}" (two literal braces: the path-set object and the outer object); the new code opens with "{" as a plain string, and closes the path-set object with out += "}" inside the if and the outer object with out += "}" after it. Write out the exact resulting string for a small example in both versions.
2. Prove the OFF-state output is exactly "{}" and valid JSON, and that render_totals, render_layer, render_worker follow the same shape (read them).
3. Check every caller of render_forwards: print_report (returns early when !enabled?), the FUSE leaf lambda in register_fuse_files, and the tests (grep render_forwards and _forwards in t/). Does any caller depend on the old zero-filled object while off?
4. Check that forwards[cls] indexing stays in range for every caller (cls < N_CLASSES_2), and that reading fc only inside 'if (enabled)' changes no atomics or memory ordering (load_relaxed unchanged).
5. fmt::format_to with the new format string: count the {} placeholders vs the arguments (5 and 5?) and the escaped {{ at the end; any mismatch is a compile-time error with fmt's consteval format strings, so state clearly whether it compiles (the local syntax check with clang 19 passed; confirm by reading).`,
  },
  {
    key: 'contract',
    prompt: `${CTX}

Lens: DOCUMENTED CONTRACT and SIBLING defects.
1. Find every text that describes the off-state or dead-state behaviour of the attention leaves and check it agrees with the FIXED code: README.stats.md (the casual-stats example paragraph, around lines 236-262), the Note [Attention path stats] at the top of h/tron/models/attn_stats.hpp, the comment block above register_fuse_files (around line 718-733), the PR body draft /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/pr-body.md, and the test README if any. Quote each sentence and say agree/disagree.
2. Hunt for SIBLING defects of the same kind: any renderer or leaf (render_summary, render_totals, render_layer, render_worker, render_forwards, print_report, the weak_ptr leaf callbacks) whose off-state, dead-state (weak_ptr expired) or takeover output disagrees with the documented contract. Read the code for each; do not assume.
3. Downstream parsers: /home/jhan/workspace/intel-AMX/exec/attnstats-20260924/decide.py, /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/gen_counter.py, /home/jhan/workspace/intel-AMX/exec/attnstats-20260924/chain.sh (the fuse poll loop) and any other reader of the _forwards leaf under /home/jhan/workspace/intel-AMX/exec (grep -rl _forwards). Would "{}" from the off-state _forwards leaf break any of them (KeyError etc.)? Note that the 2026-09-24 switch-unset run already produced "{}" for _totals, so parsers that survived that are likely fine for _forwards; verify rather than assume.
4. Does the PR body (pr-body.md, and the live GitHub body: gh pr view 4596 -R positron-ai/tron --json body -q .body) claim anything about the off-state forwards leaf that is now wrong or that should mention the fix? Report as info only; the body is jhan's to edit.`,
  },
  {
    key: 'tests',
    prompt: `${CTX}

Lens: TESTS and the C++ CODING GUIDE.
1. Do the new CHECKs compile with this file's conventions? Verify that CLASS_PROMPT_1, CLASS_DECODE_0, STATS_OFF_FALSE, leaf_string, stats_environment and make_stats exist in t/t_attn_stats.cpp with the used signatures (cite lines).
2. Would the new CHECKs FAIL on the PRE-fix code? Read git -C ${WT} show d85edc0e28:h/tron/models/attn_stats.hpp render_forwards and state what the old off-state string was; confirm each new CHECK (renderer and FUSE leaf, both classes) turns red on the old code and green on the new one. A test that cannot fail is a defect (project rule 9).
3. Do the new test comments say WHY (the README contract) and not merely WHAT? Quote them.
4. The renamed TEST_CASE title: is it unique in the binary (grep across t/), and truthful: with the switch off, register_fuse_files registers exactly summary + 2 totals + 2 forwards = 5 leaves and no layer/worker leaves (read register_fuse_files and count).
5. Load the C++ coding guide with the Skill tool (skill name: cpp-coding-guide) and check the changed lines of both files against it: named values instead of bare literals, brace rules, comment register (one claim per sentence, plain words), anything else the guide says. Report violations with the guide's rule name.
6. Any OTHER existing test (t/t_attn_stats.cpp, t/t_llama_unit.cpp, t/t_amx_dispatch_dtype.cpp, t/t_heterogeneous_scheduler.cpp) that asserts the OLD off-state forwards output and would now break: grep for token_jobs_by_path_set, render_forwards, _forwards, "forwards\\":0.
7. Is any test missing that the fix deserves (e.g. the on-state forwards output still carries every key: check that an existing case already asserts the on-state keys, cite it)?`,
  },
]

phase('Verify')
const reports = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `lens:${l.key}`, phase: 'Verify', schema: FINDINGS })
    .then(r => ({ lens: l.key, report: r }))))
const got = reports.filter(Boolean)
log(`lens reports: ${got.length}/3 (${got.map(r => `${r.lens}: ${r.report.findings.length} findings, ok=${r.report.ok}`).join('; ')})`)

phase('Critic')
const CRITIC = {
  type: 'object',
  properties: {
    must_fix: { type: 'array', items: { type: 'string' } },
    should_fix: { type: 'array', items: { type: 'string' } },
    dropped: { type: 'array', items: { type: 'string' }, description: 'lens findings you could not confirm, with why' },
    notes: { type: 'array', items: { type: 'string' } },
    complete_and_minimal: { type: 'boolean' },
    verdict: { type: 'string' },
  },
  required: ['must_fix', 'should_fix', 'dropped', 'notes', 'complete_and_minimal', 'verdict'],
}
const critic = await agent(`${CTX}

You are the CRITIC. Three lens reports about this change are below (JSON). Read the diff yourself. For every lens finding of severity must-fix or should-fix, confirm it from the code with file:line or drop it (list dropped ones with the reason). Then answer: (a) is the change complete with respect to what the bot asked (both _forwards leaves read "{}" while off, README contract now met), (b) is it minimal (touches only what it must, matches the sibling render_totals shape), (c) is anything must-fix before a push to the PR, (d) is anything cheap and worth doing before the push (should-fix). Keep must_fix empty unless you can name the exact line and the failure.

Lens reports:
${JSON.stringify(got, null, 1)}`, { label: 'critic', phase: 'Critic', schema: CRITIC, effort: 'high' })

return { lenses: got, critic }