export const meta = {
  name: 'pr5186-boot-budget-fix',
  description: 'Work out a verified fix for the PR 5186 review comment about the Linux boot cycle budget with timed AUX lanes',
  phases: [
    { title: 'Understand', detail: 'four readers map budget code, timing model, evidence, history' },
    { title: 'Design', detail: 'two independent fix designs, then one synthesis' },
    { title: 'Verify', detail: 'three reviewers try to refute the chosen fix' },
  ],
}

const REPO = '/home/jhan/workspace/ai-runs/asimov-pr5186/repo'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/422f48fc-5de1-4c4b-827c-698f4904a51d/scratchpad'
const CONTEXT = `
Context. Repo clone: ${REPO} (branch pr5186, head 13418eb, PR 5186 of Positron-AI-TSMC/asimov, base origin/main, author is another engineer). READ-ONLY: do not edit, commit, checkout, or stash anything in that clone. Put any temporary files under ${SCRATCH}. An earlier agent session left notes in /home/jhan/workspace/ai-runs/asimov-pr5186/scratch (untrusted hints, verify before use).

The PR changes emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv lines 647 and 693: the gate ".DATAPATH_TIMING (GC_PAIR_INDEX >= 0 && GC_PAIR_INDEX < 16)" becomes "< 18". That gives the 4 AUX lanes (GC pairs 16-17, which hold the AP system DRAM) the datapath DDR timing profile: 61-cycle reads (was about 3), 40-cycle write responses, 38.4 GB/s shared bandwidth budget.

The review comment to fix (from a review bot, line 693): default real-CMN Linux boot runs may now fail their LINUX verdict. emu/hemi_tlm/scripts/run_emu.sh:611-613 sets RUN_CYCLES from asimov_os_linux_boot_cycles: 1.0G cfclks for release SCP >= 0.51.0, based on a measured 874M cfclks boot with UNTIMED AUX (126M margin). Each DRAM read gains about 58 AXI cycles (about 116 cfclks per the PR text), so about 1.1M latency-exposed reads use up the margin. run_emu.sh:2322-2324 exits 1 when the verdict is not "booted". Host timing overrides cannot relax AUX timing (configure_timing in hemi_gc_wmem_preload.cpp touches only the 32 DP lanes). Suggested fix by the bot: re-measure the timed AUX boot and raise the default Linux-boot RUN_CYCLES (and RUN_TIMELIMIT if needed), or keep AUX untimed until that is done.

Rules for your report: every claim carries a file:line reference or a command you ran. Mark anything not measured as "est." or as a hypothesis. Say "Insufficient data" and name the missing measurement where needed. No emulator (Palladium) run is available in this session.
`

const FACTS = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    facts: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, evidence: { type: 'string' } }, required: ['claim', 'evidence'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'facts', 'open_questions'],
}

phase('Understand')
const READERS = [
  { key: 'budget', prompt: `Map the Linux-boot run budget code. Find the definition of asimov_os_linux_boot_cycles (grep the whole repo, it is not defined in run_emu.sh itself; maybe a sourced env script) and read it fully. List every place that sets or consumes RUN_CYCLES, RUN_TIMELIMIT, RUN_WAIT for the Linux boot in emu/hemi_tlm (run_emu.sh lines 55-75, 590-630, 2300-2330, the PCIEVB branch with 5400 s, any CI or regression script or YAML that calls run_emu.sh for a Linux boot with or without --run-cycles). Find every test (python unittest, bash test) and every doc that hard-codes 1000000000, 1600000000, 874M, 0.44 s, 3600, 5400 or similar, since a fix must update them together. Report how cfclks convert to simulated seconds and to AXI lane cycles (the PR says 1 AXI cycle is about 2 cfclks; confirm from the code or docs). Report the measured emulation speed if stated (for example "about 2700 s of emulation for 1.6G cfclks") so that a wall-clock limit can be derived for a larger cycle budget.` },
  { key: 'timing', prompt: `Map the DDR timing model that the PR turns on for the AUX lanes. Read emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv (the two gates, the GC_PAIR_INDEX parameter and how setup_tree.sh patches it), the hemi_gc_lane_avip module and its DATAPATH_TIMING parameter, the reset profile (61-cycle read, 40-cycle write response, bandwidth 39322 bytes per 1024 cycles, 63 outstanding), emu/hemi_tlm/doc/GC_DDR_TIMING.md, and hemi_gc_wmem_preload.cpp configure_timing. Answer with evidence: (1) exactly what latency a read and a write on an AUX lane had before and has after, in lane cycles and cfclks; (2) whether the latency adds per transaction or per beat, and how the bandwidth budget throttles; (3) whether a cheap, clean switch exists or could be added to keep the AUX lanes untimed by default while still allowing them to be timed (a build define such as an ifdef around the gate, a parameter, a setup_tree.sh or run_build.sh option, a runtime plusarg or the host configure_timing extended to lanes 32-35) and what each would cost in lines and risk; (4) how the AP DRAM reaches these lanes (cmn.sv sys_dram_0..3, hemi_sys_mem.cpp) and whether the preload path (MARG backdoor) is affected by the timing.` },
  { key: 'evidence', prompt: `Find every piece of existing data that helps estimate how many cfclks a real-CMN Linux boot needs once each AP DRAM read costs 61 lane cycles instead of about 3. Look in the repo docs (emu/hemi_tlm/doc, READMEs, comments in run_emu.sh and the asimov-os env script), in git log messages (git log --all --grep for "874M", "0.44 s", "boot", "RUN_CYCLES", "run-cycles" in emu/hemi_tlm), and in the earlier scratch notes at /home/jhan/workspace/ai-runs/asimov-pr5186/scratch (est_base.py, est_lo.py, est_hi.py, dry.txt, lpddr5.py; read them and say what they compute and whether their inputs are measured or assumed). Look for any count of AP DRAM AXI read and write transactions during boot (hemi_sys_mem.log format, any transaction counters or stats printed by the AVIP or the run summary), boot phase timings (BL2 releases AP at about 0.1 s, init at about 0.44 s), CPU count and cache sizes that set how many reads miss to DRAM, and whether the boot runs with caches on. Then give a bounded estimate (low, base, high, each labeled est. with the formula and inputs) of the timed boot length in cfclks, and state exactly which measurement would replace the estimate (which command, which log line). Also report which log line or counter in an existing run would give the DRAM read count without a new emulator run, if one exists.` },
  { key: 'history', prompt: `Map the history and conventions. Use git log -S and git log --follow on emu/hemi_tlm/scripts/run_emu.sh and the file that defines asimov_os_linux_boot_cycles to find the commits (and PR numbers) that introduced the 1.0G and 1.6G cfclk defaults, the 874M measurement, RUN_TIMELIMIT 3600 and the PCIEVB 5400 value. Report how earlier commits justified those values in comments and commit messages (measured value plus what margin, in percent), so a new value follows the same convention. Also read PR 5186 itself with gh (gh pr view 5186 --repo Positron-AI-TSMC/asimov --json body,comments,reviews and gh api repos/Positron-AI-TSMC/asimov/pulls/5186/comments) and PR 4492 (the one that timed the 32 datapath lanes) to see whether that PR changed any run budget and whether reviewers there discussed AUX timing or a switch. Check origin/main since the PR base for any newer change to the boot budget (git fetch is allowed with: git -C ${REPO} fetch origin main --quiet; do not change the checked-out branch). List the tests that cover run_emu.sh defaults and how to run them (python3 -B -m unittest paths).` },
]
const maps = (await parallel(READERS.map(r => () =>
  agent(CONTEXT + '\nYour task: ' + r.prompt, { label: 'read:' + r.key, phase: 'Understand', schema: FACTS, agentType: 'general-purpose' })
    .then(m => m && ({ key: r.key, ...m }))))).filter(Boolean)
log(`Understand: ${maps.length}/4 readers returned`)
const MAPTXT = JSON.stringify(maps, null, 1)

phase('Design')
const DESIGN = {
  type: 'object',
  properties: {
    approach: { type: 'string' },
    rationale: { type: 'string' },
    unified_diff: { type: 'string', description: 'git-apply-able unified diff against the PR head, or empty if no code change' },
    pr_body_changes: { type: 'string' },
    measurement_plan: { type: 'string', description: 'exact commands and the log lines to read to close the item' },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['approach', 'rationale', 'unified_diff', 'measurement_plan', 'risks'],
}
const ANGLES = [
  { key: 'raise-budget', prompt: 'Design the fix along the first branch of the reviewer suggestion: keep the AUX lanes timed and raise the default Linux-boot RUN_CYCLES (and RUN_TIMELIMIT and the PCIEVB limit if the wall-clock no longer fits). No measured timed boot exists, so choose a value that clearly fits the high estimate, label it as an estimate in the comment, and give the measurement that will replace it. Update every comment, doc and test that hard-codes the old values.' },
  { key: 'gate-switch', prompt: 'Design the fix along the second branch of the reviewer suggestion: keep the AUX lanes untimed by default until a timed boot is measured, while keeping the PR useful (the AUX timing stays available behind the smallest clean switch, for example a build define or a setup_tree.sh option, following existing conventions in this tree). Update the docs the PR touched so they stay true. Give the measurement plan that would later flip the default together with a budget change.' },
]
const designs = (await parallel(ANGLES.map(a => () =>
  agent(CONTEXT + '\nFindings from four readers (JSON):\n' + MAPTXT + '\n\nYour task: ' + a.prompt + ' Minimum change, match the style of the surrounding code. You may copy files to ' + SCRATCH + '/' + a.key + ' to build the diff and check it with "git -C ' + REPO + ' apply --check <patch>" and "bash -n". Return the diff text.', { label: 'design:' + a.key, phase: 'Design', schema: DESIGN, agentType: 'general-purpose' })
    .then(d => d && ({ key: a.key, ...d }))))).filter(Boolean)

const chosen = await agent(CONTEXT + '\nFindings from four readers (JSON):\n' + MAPTXT + '\n\nTwo candidate fixes (JSON):\n' + JSON.stringify(designs, null, 1) + `\n\nYour task: act as the judge. Decide which fix (or which combination) the PR author should take to resolve the review comment, given that no emulator run is available now. Weigh: correctness without a measurement, cost in emulator wall-clock for every default Linux boot, how much of the PR's purpose survives, change size, and what a reviewer would accept. Produce ONE final recommended patch as a unified diff against the PR head that passes "git -C ${REPO} apply --check". Write the patch file to ${SCRATCH}/pr5186-fix.patch and verify it with apply --check, with bash -n on any changed shell script (apply into a copy under ${SCRATCH}/final, never in the clone), and by running any unit tests that cover the changed files from that copy. Also state the runner-up and when it is the better choice. Put the name of the chosen approach in "approach".`, { label: 'judge', phase: 'Design', schema: DESIGN, agentType: 'general-purpose' })

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
  { key: 'correctness', prompt: 'Lens: correctness. Does the patch actually remove the failure the review comment describes for every default real-CMN Linux boot path (plain, PCIEVB, debug SCP 1.6G path, explicit --run-cycles)? Apply the patch in a fresh copy under ' + SCRATCH + '/verify-correctness and trace the shell or SystemVerilog logic. Check each number in the patch and rationale against the code. Recompute any arithmetic with a script.' },
  { key: 'completeness', prompt: 'Lens: completeness and consistency. After the patch, grep the tree for every comment, doc, test and script that still states something the patch made false (old cycle counts, "AUX lanes timed/untimed" statements in GC_DDR_TIMING.md, HOST_PROGRAM_V1.md, setup_tree.sh, run_emu.sh header, fc_tlm and fc2_tlm trees that share the wrapper). Run the unit tests that cover the changed files from a patched copy under ' + SCRATCH + '/verify-completeness and report exact pass or fail output. Check the patch still applies to the PR head.' },
  { key: 'claims', prompt: 'Lens: claims and evidence. Check every factual claim in the rationale, risks and measurement plan against primary sources (code, docs, git log). Flag any number presented as measured that is an estimate, any estimate without a formula, and any measurement plan step that cannot work as written (wrong option name, wrong log file, wrong grep pattern). Check the readers findings the design relies on by re-reading the cited lines yourself.' },
]
const verdicts = (await parallel(LENSES.map(l => () =>
  agent(CONTEXT + '\nThe proposed fix (JSON, the patch is also at ' + SCRATCH + '/pr5186-fix.patch):\n' + JSON.stringify(chosen, null, 1) + '\n\nYour task: try to REFUTE this fix. ' + l.prompt + ' Set refuted=true only if a blocker or major problem exists.', { label: 'verify:' + l.key, phase: 'Verify', schema: VERDICT, agentType: 'general-purpose' })
    .then(v => v && ({ lens: l.key, ...v }))))).filter(Boolean)

return { maps, designs, chosen, verdicts }
