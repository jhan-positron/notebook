export const meta = {
  name: 'pr5186-codex-round1',
  description: 'Check codex review round 1 on the PR 5186 fix, implement the launcher guard and the timing-selection test, verify with mutations',
  phases: [
    { title: 'Implement', detail: 'guard + test, wrapper selection test, fact checks for doc items' },
    { title: 'Integrate', detail: 'one combined patch against the PR head' },
    { title: 'Verify', detail: 'two reviewers with mutation tests' },
  ],
}
const REPO = '/home/jhan/workspace/ai-runs/asimov-pr5186/repo'
const S = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/422f48fc-5de1-4c4b-827c-698f4904a51d/scratchpad'
const DIR = '/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr'
const CTX = `
Context. PR 5186 of Positron-AI-TSMC/asimov, head 13418eb. Local clone: ${REPO} (sparse and partial clone; READ-ONLY: never edit, checkout, stash or commit there; "git show HEAD:<path>" and "git archive" are fine; avoid tree-wide "git grep" on HEAD because it fetches many blobs). A proposed fix exists: ${DIR}/pr5186-fix.patch (applies to the PR head) with its description ${DIR}/pr5186-fix.md. It puts the AUX lane DDR timing behind a build define HEMI_GC_AUX_TIMING (off by default) through "localparam int GC_TIMED_PAIRS" in emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv. A second reviewer (codex) reviewed it: read ${DIR}/codex-review-pr5186-fix.md in full first. Do not edit any file in ${DIR}. Treat the codex text as claims to verify against the code, not as fact.

Working copy recipe (each agent uses its OWN directory under ${S}): mkdir the dir; "git -C ${REPO} archive HEAD emu/hemi_tlm emu/common | tar -x -C <dir>"; cd <dir>; git init -q; git add -A; git commit -qm base; "git apply ${DIR}/pr5186-fix.patch"; git commit -qam fixv1. Your change is then "git diff" in that copy. Files outside emu/hemi_tlm and emu/common that a test needs can be added with "git -C ${REPO} show HEAD:<path>".

Rules: minimum change, match the style of the surrounding code and of the existing tests, comments in plain literal English with one claim per sentence, no review-round narration in comments. Every claim in your report carries a file:line or the command you ran with its output. Say plainly what you did not run. No emulator and likely no SystemVerilog simulator are available; check with "command -v xrun verilator iverilog slang" before deciding the test form.
`
const IMPL = {
  type: 'object',
  properties: {
    agree_with_codex: { type: 'string', description: 'which codex claims you confirmed or rejected, with evidence' },
    summary: { type: 'string' },
    diff_path: { type: 'string', description: 'absolute path of the diff file you wrote (relative to the fixv1 commit), or empty' },
    tests_run: { type: 'string', description: 'exact commands and pass/fail output, including mutation results' },
    not_done: { type: 'array', items: { type: 'string' } },
  },
  required: ['agree_with_codex', 'summary', 'diff_path', 'tests_run', 'not_done'],
}

phase('Implement')
const TASKS = [
  { key: 'guard', prompt: `Codex item 1 (image reuse). First confirm or reject codex's claims: the image directory is the same with and without the define (run_build.sh:386-401, run_emu.sh:736-753), and the launcher picks the Linux boot window (run_emu.sh:605-615) before it reads the compiled defines (run_emu.sh:961-1054, look for compiled_defines and the MANIFEST "defines:" line). If confirmed, implement the smaller change codex asks for in emu/hemi_tlm/scripts/run_emu.sh: before the emulator is launched for a Linux boot, read the defines of the image that will actually run (the existing MANIFEST / compiled_defines mechanism), and when they contain HEMI_GC_AUX_TIMING and the caller gave no explicit --run-cycles, stop with a clear error message that asks for an explicit --run-cycles (use the existing red ERROR printf style). It must cover a fresh --build, a reused image and --run-only. Mind the ssh/remote re-dispatch near run_emu.sh:880, which always forwards --run-cycles: the remote side must still know whether the caller set it (find how RUN_CYCLES_SET or similar state crosses that boundary today and reuse it; add the smallest signal if none exists). Also mind that a --build with --define HEMI_GC_AUX_TIMING and no --run-cycles should fail early, before a long build, if the script can know that from its arguments. Then add a regression test in the style of the existing launcher tests (look at emu/common/tests/test_boot_firmware_selection.py, test_hemi_notel.py and any test that executes run_emu.sh blocks or uses a dry-run mode) that establishes: untimed image + default window accepted; timed image + default window rejected before emulator execution; timed image + explicit window accepted. Run the new test and the existing suites (python3 -B -m unittest for emu/common/tests and emu/hemi_tlm/tests files that can run in the copy; report any that cannot run and why). Mutation check: remove your guard and show the new test fails. bash -n the script. Write your diff to ${S}/r1-guard/guard.diff. Your working copy dir: ${S}/r1-guard/tree.` },
  { key: 'seltest', prompt: `Codex item 2 (test the wrapper timing selection in both build modes). First reproduce codex's claim: in a patched copy change the default GC_TIMED_PAIRS from 16 to 18 and run "python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_gc_*.py'"; report whether everything still passes. Then add a test that exercises BOTH outer-wrapper lane instances (lane_bfm0 and lane_bfm1 in emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv, module goldcrestEW_ip_fullconn_wrapper) with the define absent and present, for pair indices -1, 0, 15, 16, 17, 18. Expected: negative and out-of-range indices untimed in both builds; pairs 0..15 timed in both; pairs 16..17 untimed by default and timed only with HEMI_GC_AUX_TIMING. The test must fail when either lane receives a wrong timing parameter expression. Prefer a real elaboration if a simulator exists and the existing tests already use one (see emu/hemi_tlm/tests/run_gc_avip_timing.sh and gc_avip_timing_tb.sv for how Xcelium scenarios are qualified; if Xcelium is the only way and it is not installed here, you may add a scenario there only if it stays small, and say it was not run). In any case add a Python unittest that runs everywhere in CI without a simulator, in the style of emu/hemi_tlm/tests/test_gc_port_order.py and test_real_gc_wrapper.py: extract from the wrapper source the ifdef block that defines GC_TIMED_PAIRS and the DATAPATH_TIMING expression of each of the two hemi_gc_lane_avip instances, evaluate them for both define states and all six indices, and compare with the expected table. Keep the parser strict so that an unexpected expression form fails the test instead of passing silently. Mutation checks to run and report: default 16 changed to 18; define branch 18 changed to 16; lane_bfm1 gate changed back to a literal "< 18"; lane_bfm0 gate changed to "< 16" literal; ifdef inverted to ifndef; the ">= 0" clause dropped. Each mutation must make the new test fail; the unmutated tree must pass. Also update the "aux" scenario wording in docs only if your change makes it false. Write your diff to ${S}/r1-seltest/seltest.diff. Your working copy dir: ${S}/r1-seltest/tree.` },
  { key: 'facts', prompt: `Codex items 3 and 4 (document corrections). No code change; you produce verified facts and proposed replacement text for ${DIR}/pr5186-fix.md (do not edit it; write your proposed replacement sections to ${S}/r1-facts/doc-changes.md and return that path in diff_path). Item 3: verify whether the count "1,782,918 reads and 2,867,850 writes" in emu/fc_tlm/doc/NIGHT_TASK_PLAN.md:218-225 (git show HEAD:emu/fc_tlm/doc/NIGHT_TASK_PLAN.md) is a combined full-chip total for both hemispheres. Check the historical code codex cites: commit 2aeb9d4f4, emu/fc_tlm/scripts/run_emu.sh lines 480-487 and emu/fc_tlm/sim/fc_sys_mem.cpp lines 221-224 (use "git -C ${REPO} show 2aeb9d4f4:<path>"; if the commit is not in the clone use "gh api repos/Positron-AI-TSMC/asimov/contents/<path>?ref=2aeb9d4f4a96f5ddabebe881972b556a7db04acf" with -H "Accept: application/vnd.github.raw"). State whether the log is shared by both hemispheres and whether the count filters by hemisphere. Then rewrite the estimate table of the fix description so that: the count is called a full-chip logged total over the whole 1.0G cfclk run with SCP 0.30.0; any case that charges the entire total to one hemisphere is labeled an artificial conservative assumption (or removed); halving is labeled an equal-traffic assumption; and an "Insufficient data" line names the missing measurement (per-hemisphere counts up to Linux init). Recompute every number with a script and show the formula (reads x 58 AXI cycles x 2 cfclks; writes x 40 AXI cycles x 2 cfclks where used). Item 4: verify whether anything in the tree gives an absolute cfclk or simulated-time stamp for the console line "Run /sbin/... as init process" (hemi_uart_tty_xtor.sv, uart log format, run_emu.sh:1999-2029, emu/common/scripts/emu_run_status.sh, any doc that explains how 874M was obtained, the commit message of the commit that introduced the 874M comment: find it with "git -C ${REPO} log -S'874M' --format='%h %s' -- emu/hemi_tlm/scripts/run_emu.sh emu/common/scripts/asimov_os_env.sh" and read its message). If a real method exists, give the exact command. If none exists, write the measurement step as a bracket procedure: runs at chosen --run-cycles values, verdict booted or incomplete, how to exclude unrelated failures, record the passing upper bound and the exact firmware and OS snapshot. Also give the corrected wording for the short version and the behavior table per codex item 4: a fresh default build restores the base branch's AUX timing selection; boot completion with the current snapshot (v0.0.22) has not been verified.` },
]
const impl = (await parallel(TASKS.map(t => () =>
  agent(CTX + '\nYour task: ' + t.prompt, { label: 'impl:' + t.key, phase: 'Implement', schema: IMPL, agentType: 'general-purpose' })
    .then(r => r && ({ key: t.key, ...r }))))).filter(Boolean)
log(`Implement: ${impl.length}/3 returned`)

phase('Integrate')
const INTEG = {
  type: 'object',
  properties: {
    patch_path: { type: 'string' },
    stat: { type: 'string' },
    tests_run: { type: 'string' },
    notes: { type: 'string' },
    conflicts_or_gaps: { type: 'array', items: { type: 'string' } },
  },
  required: ['patch_path', 'stat', 'tests_run', 'notes', 'conflicts_or_gaps'],
}
const integ = await agent(CTX + '\nThree agents worked on the codex items. Their reports (JSON):\n' + JSON.stringify(impl, null, 1) + `\n\nYour task: integrate. Make a fresh working copy at ${S}/r1-integ/tree with the recipe, apply the guard diff and the selection-test diff on top of fixv1, resolve any overlap, and review both changes yourself for minimal size, correct shell quoting, and consistency with each other and with the docs the patch already changes (emu/hemi_tlm/doc/GC_DDR_TIMING.md paragraph on the define must now say the launcher rejects a timed image without an explicit --run-cycles, instead of only advising it; update that paragraph). Then produce ONE patch against the PR head (diff of base commit to your final state: "git diff <base> -- ." ) at ${S}/pr5186-fix-v2.patch. Check: "git -C ${REPO} apply --check ${S}/pr5186-fix-v2.patch" passes; bash -n on changed scripts; run every unit test file that can run in the copy and report the exact totals; "git apply --stat". Do not touch ${DIR}.`, { label: 'integrate', phase: 'Integrate', schema: INTEG, agentType: 'general-purpose' })

phase('Verify')
const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    problems: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, problem: { type: 'string' }, evidence: { type: 'string' }, suggested_change: { type: 'string' } }, required: ['severity', 'problem', 'evidence'] } },
    confirmed: { type: 'array', items: { type: 'string' } },
  },
  required: ['refuted', 'problems', 'confirmed'],
}
const LENSES = [
  { key: 'guard', prompt: `Lens: the launcher guard. Apply ${S}/pr5186-fix-v2.patch in a fresh copy (${S}/r1-verify-guard/tree, from the base commit, not on top of fixv1). Trace every path by reading and by executing what can be executed: fresh --build with the define and no --run-cycles; reused image built with the define, plain invocation; --run-only; explicit --run-cycles; the ssh/remote re-dispatch (does the remote side wrongly see --run-cycles as explicit and skip the guard, or wrongly reject an explicit one?); HEMI_LINUX_BOOT=0 (non-Linux runs must not be rejected); --nocmn and --test modes; an untimed image must behave exactly as before. Does the guard fire BEFORE emulator execution? Does the new test really cover the three outcomes codex listed, and does it fail when the guard is removed (run that mutation yourself)? Run the full set of runnable unit tests and report totals.` },
  { key: 'seltest', prompt: `Lens: the timing-selection test and the SystemVerilog. Apply ${S}/pr5186-fix-v2.patch in a fresh copy (${S}/r1-verify-seltest/tree, from the base commit). Run the new selection test. Then run mutations yourself, each from a clean state: default 16 -> 18; define branch 18 -> 16; one lane gate replaced by literal "< 18"; one lane gate replaced by "< 16"; ifdef -> ifndef; ">= 0" dropped; "&&" changed to "||"; the two instances given different expressions; GC_TIMED_PAIRS renamed in only one place. Report which mutations the test catches. Look for ways the test can pass while the real elaboration differs (for example a second definition of GC_TIMED_PAIRS elsewhere in the module, a define spelled differently in run_build.sh --define handling, the localparam declared inside a generate or ifdef region that hides it from one instance, the HEMI_GC_EMBEDDED_MEM ifdef region). Read the SystemVerilog for legality: localparam declaration position between module items, use before declaration. Also check that the docs in the patch agree with the final behavior.` },
]
const verdicts = (await parallel(LENSES.map(l => () =>
  agent(CTX + '\nIntegration report (JSON):\n' + JSON.stringify(integ, null, 1) + '\n\nYour task: try to REFUTE the integrated patch. ' + l.prompt + ' Set refuted=true only for a blocker or major problem.', { label: 'verify:' + l.key, phase: 'Verify', schema: VERDICT, agentType: 'general-purpose' })
    .then(v => v && ({ lens: l.key, ...v }))))).filter(Boolean)
return { impl, integ, verdicts }
