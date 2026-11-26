export const meta = {
  name: 'bwx8-review-fix-report',
  description: 'Review each part against the design, fix confirmed defects, then build the report and test the whole chain locally',
  phases: [{ title: 'Review' }, { title: 'Fix' }, { title: 'Report' }],
}
const C = '/home/jhan/workspace/titan/cache-perf'
const X = C + '/crb/tmp/agent-scratch/bwx8-2026-11-14'
const A = C + '/crb/new-test-kernel/tackle-8mb-analysis'
const BASE = `
Context: an experiment design was implemented in four parts by four agents that could not talk to each other.
- Design (the authority; "design line N" is line N): ${C}/crb/new-test-kernel/tackle-8mb.md
- Contract between the parts (formats and one fixed reading per ambiguous rule): ${X}/DECISIONS-bwx8.md
- Four notes for the implementer: ${C}/crb/new-test-kernel/tackle-8mb.md.review.md, line 344 to the end.
- Runner and schedules: ${X}/ (bwx8.c, bwx8_selftest.c, build8.sh, check_listing8.py, test_runner8.py, schedule8.py, run_bwx8.sh, visit8.sh, test_schedule8.py, sched/)
- Analysis: ${A}/ (analyze8.py, test_analyze8.py, stage0.py, stage0.html, stage0.json, test_stage0.py)
- The earlier benchmark that bwx8 copies: ${C}/crb/tmp/agent-scratch/bwx-2026-11-13/ (read-only). Saved results: ${C}/crb/results/ (read-only).
Hard rules: development machine only. No ssh, no scp, no login to CRB or any other host. No sudo. Python standard library only. Use TMPDIR or your scratchpad for temporary files. The shell profile prints a directory listing on every cd: prefer absolute paths.`
const FIND = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      file: { type: 'string' }, where: { type: 'string', description: 'function or line' },
      defect: { type: 'string', description: 'what is wrong, with the design line or contract section it breaks' },
      evidence: { type: 'string', description: 'the command you ran or the input you built, and what came out' },
      fix: { type: 'string' } }, required: ['id', 'severity', 'file', 'defect', 'evidence'] } },
    checked_and_correct: { type: 'array', items: { type: 'string' } },
    not_checked: { type: 'array', items: { type: 'string' } },
  }, required: ['findings', 'checked_and_correct', 'not_checked'],
}
const FIXED = {
  type: 'object',
  properties: {
    fixed: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, change: { type: 'string' } }, required: ['id', 'change'] } },
    rejected: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, reason: { type: 'string' } }, required: ['id', 'reason'] } },
    tests_run: { type: 'array', items: { type: 'object', properties: { command: { type: 'string' }, result: { type: 'string' } }, required: ['command', 'result'] } },
    interface_changes: { type: 'array', items: { type: 'string' }, description: 'any change to rows, file formats or function results that another part must know' },
    still_open: { type: 'array', items: { type: 'string' } },
  }, required: ['fixed', 'rejected', 'tests_run', 'interface_changes', 'still_open'],
}
const REVIEW_RULES = `
You are a reviewer. Your job is to find real defects, not to praise. Compare the code with the design line by line for the sections named below. A finding needs evidence: run the code on an input that shows the wrong behaviour, or quote the code lines beside the design line they break. Do not report style, naming, or wishes beyond the design. Do not report a thing as a defect only because the existing tests do not cover it: show the wrong behaviour, or list it under not_checked. Do NOT edit any file of the implementation (write only in your scratchpad). Also judge the tests: a test that cannot fail when the rule changes is a finding (show it by a mutation of a scratch copy).`
const PARTS = [
  { key: 'runner', files: 'bwx8.c, bwx8_selftest.c, build8.sh, check_listing8.py, test_runner8.py', focus: `
Part: the runner. Design sections: "Runner design" lines 131 to 169; Stage 1 items 1 and 4 (lines 175 to 178); Stage 4 counter modes (lines 295 to 305). Look hard at:
- The timed sequence in bwx8.c: is there ANY call, store to shared memory, branch on trace, allocation, output, page read, or syscall other than clock_gettime between the end of the predecessor (or prefix) and the last target window, in closed and open counter states? Is the kernel still called through the unchanged call()? Diff the kernel functions, PLACE macros, call() and alloc_buf() against bwx.c (they must be textually identical) and check that new code cannot move kernel offsets modulo 64 (file order, -fno-toplevel-reorder).
- Byte accounting: whole passes only, clock checked after max(1, 8 MiB / SIZE) passes, a window ends at the first clock read at or after its duration, bytes counted only for completed passes, no apportioning. Window start/end times, gaps measured with two clock reads, gap_ns definition.
- Record storage: sized from the plan, first-touched before trial 0, never grows; overflow impossible (bins, trace, counts) or handled without writing past the end.
- Bins: no extra clock read; B rows sum to the W row.
- Counter states: open/close before the prefix with checked results; reads only at target window boundaries in state read; failure rows; multiplexing check; what happens when a trial with count open follows a trial with count closed and the open fails.
- Plan parser: every defect found before pinning/allocation; integer overflow in durations and sizes; nwin bound; a prefix of "-" with a predecessor; trials with prev but no prefix.
- Thread placement: controlling thread pinned and idle, worker pinned before allocation and first touch (design line 137); restrict_cpus still applies.
- The old --seq mode is unchanged in behaviour (step B6W needs "the unchanged interval wrapper").
- build8.sh: marker check first and before each run of the binary, CPUs 0-119, flags equal to the accepted build (crb-build-2/build.txt), writes only in its own folder. check_listing8.py: can a changed loop body, a changed loop offset, a missing kernel, or a changed prologue pass? Judge the "got_offset_differs" exemption: is it limited to exactly the stack-guard load, or could it hide another change?
Build the stand-in binary in your scratchpad and run it (short plans; CPUs that exist here).` },
  { key: 'schedule', files: 'schedule8.py, run_bwx8.sh, visit8.sh, test_schedule8.py, and the generated sched/', focus: `
Part: schedules and run script. Design sections: lines 137 (CPU order reversed in session 2), 199, 201 to 209 (S2), 224 to 228 (P3), 179 (P3G, S3G), 234 to 245 (S3, especially the construction of line 242), 285 to 289 (S4), 299 to 307 (CS, CM, C4), 176 (B6W), 340 to 358 (budget), 360 to 366 (host rules); and handoff.md of ${C}/crb/new-test-kernel/ sections "The machine, and the rules for using it" and "Stop controls". Look hard at:
- Recompute independently, from the generated plan files in ${X}/sched/, with your own short script: process counts, trial counts and nominal seconds per step; S2: per size/CPU/session the six kernel orders once each, size order randomized per replicate block, CPU order per session; S3 and CM: every ordered pair of distinct conditions inside rows exactly twice and every condition in every position exactly twice per CPU/session, 6 processes x 4 cycles; P3: all six permutations four times over the 24 cycles; P3G: 9 conditions x 4 repeats, durations 2400/1200/4x300; S3G; S4: 200 windows; rep numbering (rep n is the n-th occurrence of cond in the process, in time order) since the A/A split depends on it.
- The 12 Stage 3 conditions and their phases (prefix oldread@8M 1200, predecessor 300 at the right size, target at 8M).
- Randomness: seeded, saved, deterministic; no use of time or of Python hash order.
- run_bwx8.sh against run_bwx.sh: is the stop-control block the same in behaviour (diff it)? Marker checked before the wait, in every turn, directly before each launch and every second during a run? STOP_AT margin from the longest process? Can any path start a process after a stop condition? Does it stay in CPUs 0-119 and still allow the control CPU 0? Does it write only under ~/cache-perf? Session-2 rule (3 hours after SESSION1_END) and its edge cases (bad date, missing value, session 1 not ended). --from. Quoting of args from the TSV (injection or word splitting). The record of system load before each process (user rule: load is measured before every performance test and reported). Does it print conditions, process count and nominal work before execution?
- visit8.sh: marker check first; no scp; nothing that logs in without the check.
Run the scripts with a dummy binary in your scratchpad; never against a real host.` },
  { key: 'analysis', files: 'analyze8.py, test_analyze8.py', focus: `
Part: the analysis rules. Design sections: lines 78 to 88 (P1, P2, P3), 181 to 197 (gates and margins), 211 to 222 (Stage 2), 226 to 228, 247 to 255 (Stage 3), 257 to 279 (shared rule, quality checks), 285 to 307 (sustained, counters), 176 (B6W), 373 (required synthetic tests); the contract section "Fixed readings of the design"; the four notes. Method: for each rule, build a tiny synthetic input by hand (use the builder in test_analyze8.py or your own rows in the contract format), work the expected answer out on paper from the design text, and compare with the code's answer. Look hard at:
- A/A split {rep 1, rep 3} against {rep 2, rep 4}; spread = max over the 6 units of one CPU and session (for Stage 2: over the 6 processes of that kernel/size/CPU/session); limit = sum of spreads of the constituent rates (2, 4, 8).
- Repeatable: |median of 6| above the limit AND one sign; exactly 0 fails; exactly at the limit fails. Confirmed needs both sessions with the same sign.
- P1 exactly as line 80 and the contract (every set: |d| + L <= 0.30; boundary value 0.30 passes); P1 contradicted needs repeatable and above 0.30. P2. Decomposition formula and sign of both terms (line 216: original example 17.55 and 0.05 give 17.50). Percentage gain formula 100 x (new/old - 1).
- P3 in the contract's order; tie rule; endpoint by the kernel's own min and max; control limit = 2 x max |old A/A|; boundary values 0.30 and 2.0; "Insufficient data" versus "undecided" (note 4).
- Gate: three conditions of line 193; margin formula and clip bounds per quantity type (table lines 183 to 187); roundup at exact multiples of 0.05 (floating point: 2 x 0.075 must give 0.15, not 0.20); L0 >= margin; L0 per selected use (note 3); the gate refuses a margins file whose source is the gated batch; margins never computed from the gated data; all 18 / 6 contrasts on both CPUs and sessions must pass.
- Stage 3 contrasts with the right signs and windows; four-rate interaction; the assembly-predecessor replication is not substituted for a failed primary contrast.
- Quality marks: thresholds (0.99, any involuntary switch, 100 microseconds), NA handling of gap_ns for trials without a window before the target, filtered against unfiltered, completeness per contrast, units below 6.
- Mixing of processes: can two processes with one key, or a continued run (--from), produce a silently merged unit? Is a trial counted twice?
- Rates from actual bytes and times; bins aggregated by sums.
- Parser against the REAL runner: build ${X}/bwx8.c locally (stand-in), run plans from ${X}/sched/ made with a test divisor (python3 ${X}/schedule8.py has --test-divisor and an output-folder option; write only to your scratchpad), wrap the output in the result-folder layout, and check that every row type parses, including NA values and the X codes count_read and count_close.
- test=1 data gives no decision word anywhere.` },
  { key: 'stage0', files: 'stage0.py, stage0.html, stage0.json, test_stage0.py', focus: `
Part: Stage 0 (design lines 114 to 129) on the saved files. This page will be read by the user as a result, so every number must be right. Method: write your OWN short independent scripts (do not import stage0.py) that recompute from the raw csv files, and compare with stage0.json and with the numbers printed in stage0.html. At least: the original size table and gains (line 43 to 50); the four 8 MiB process-median gains; the B6 pair count per session and the claim "first slower in all 192"; pooled medians of positions 8 and 11 and the position-5 range (line 53); the size-difference ranges of line 54; B1 reference medians (lines 61 and 90); the two-spread limits 0.1546 and 0.1178 GB/s of B6 position 5 on CPU 2; the B4 and C1 block values and the pooled two-spread range for assembly read (review note: 0.335 to 2.840 GB/s) and how the page reports the per-source reading; the P1 emulation (-0.139 to -0.054, 0.162 to 0.222); the margin and forecast per use against the margin rule of design lines 183 to 191 and notes 1 to 3; the loop-offset and instruction comparison (item 5) against the listing files; item 4 line numbers against bwx.c and run_bwx.sh. Then read the whole page text (strip the tags) as a reader who has never seen the project and check: it starts with a Short version of at most three sentences; every term is defined; every number has a unit; estimates are marked est.; no sentence claims a cause (the stage establishes no causal history effect); no claim lacks a source reference; "Insufficient data" names the missing measurement; the stop decision of line 129 follows from the computed facts; all eight items are present; nothing of the data was dropped silently (CPU 94, no-huge-page processes, transitions). Render check: the page was rendered by its author; render it again yourself with the headless Chrome (command in /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md, scratch folder in your scratchpad, own --user-data-dir) and look at EVERY piece with the Read tool for clipped or overlapping text, unreadable charts, tables wider than the page, and a dark or coloured page background (it must be light).` },
]
const reviewed = await pipeline(
  PARTS,
  p => agent(`${BASE}\n${REVIEW_RULES}\nFiles under review: ${p.files}.\n${p.focus}`, { label: 'review:' + p.key, phase: 'Review', schema: FIND }),
  (rev, p) => {
    const f = (rev && rev.findings) || []
    if (!f.length) return { part: p.key, review: rev, fix: null }
    return agent(`${BASE}
You own this part now: ${p.files}. A reviewer reported the findings below. For EACH finding: first reproduce it yourself (run the evidence or read the code beside the design line). If it is real, fix it with the smallest change and add or correct a test that fails without the fix. If it is not real, reject it and give the reason with your own evidence. Do not make changes that no finding asks for. Keep the contract formats; if a fix must change a row, a file format or a function result that another part reads, keep the old reading working where you can and list the change under interface_changes. Do not edit files of other parts, with one exception: none. After the fixes run ALL test scripts of the part (test_runner8.py, test_schedule8.py, test_analyze8.py, test_stage0.py as applicable; for stage0 also run stage0.py again so that stage0.html and stage0.json are current, and render the changed sections and look at them) and report the real result. If you regenerate ${X}/sched/, use the default base seed.
Findings (JSON):
${JSON.stringify(f, null, 1)}
Reviewer could not check: ${JSON.stringify(rev.not_checked || [])}`, { label: 'fix:' + p.key, phase: 'Fix', schema: FIXED }).then(fix => ({ part: p.key, review: rev, fix }))
  })
const ifc = reviewed.filter(Boolean).flatMap(r => (r.fix && r.fix.interface_changes) || [])
phase('Report')
const report = await agent(`${BASE}
YOUR PART: the HTML report of new runs and the local test of the whole chain. Files you write: ${A}/report8.py, ${A}/test_chain8.py, and scratch only under ${A}/chain-test/ (generated; safe to delete and rebuild). You may NOT edit the other parts. If you find a defect in another part, do not patch it: report it under defects_in_other_parts with evidence.
Interface changes made by the fix round just before you: ${JSON.stringify(ifc)}

Load the "dataviz" skill before chart code and the "plain-english" skill before page text.
report8.py: "report8.py FOLDER... [--margins FILE] -o report.html". It imports analyze8 (call analyze8.load and analyze8.summary; read the code for the result structure) and decides nothing by itself: every decision word and every number comes from analyze8. Self-contained page, inline SVG drawn in Python, no script, no external file, LIGHT background only. As a model for style read ${A}/stage0.py (reuse its CSS and chart helpers by import if that is clean) so that both pages look alike.
Content, from design lines 375 to 383 (deliverable 4) and 222:
- Short version (at most three sentences, built from computed values), then Words used here.
- Banner for test=1 data ("TEST DATA: stand-in kernels or shortened durations; no decision").
- System load before each process (from the launch header lines) summarized per step and session: the user requires the load in every performance report.
- Stage 2: paired old/new dots by buffer size (dumbbell per size: old read and new read, the gap labelled with the gain in %), per CPU and session panel, with rates, gains, all six set values and ranges in an exact table beside the chart; assembly read shown too; fourth window primary and first window beside it; P1, P2 outcomes with their numbers (all six |d| + L values against 0.30); the decomposition terms in GB/s (new-read term and old-read term) and shares only where resolved; the 8 MiB rate range of each kernel; approach or crossing between 8 and 16 MiB; the result sentence of line 222 filled only from measurements.
- Stage 4: the complete 60 s traces per kernel, CPU and session (small multiples, one line per process, no level labels; 69 and 70.5 GB/s only as annotation lines), transitions listed.
- If present: P3 (old against new and assembly fourth-window rates per process on one allocation, individual trial rates and time order beside the medians, instability marks, the two endpoint checks), Stage 3 (target-rate traces after each predecessor on actual elapsed time, primary contrasts with limits, persistence), shared-allocation first/fourth-window dots per allocation, gates (each contrast: median, limit, margin, largest passing median, outcome), B6W, counters (raw event names, counts per 64 B read, instructions per byte, cycles per byte; no cache mechanism assigned; "Insufficient data: authoritative event definitions").
- Separate CPU and session panels everywhere; filtered and unfiltered estimates side by side with counts; the explicit exclusion table; interrupted or killed processes and the scheduled work that remains.
- A closing section "What explains what" in the terms of design lines 326 to 338: only the rows of that table whose evidence is present, else the words "Insufficient data" with the next measurement named. No causal sentence that the analysis did not return.
- References at the end; [RefN] after sentences.
test_chain8.py (the local test of the whole chain; it must exit 0 only if every check passed): build ${X}/bwx8.c with gcc in ${A}/chain-test/ (stand-in), generate a schedule with python3 ${X}/schedule8.py and a --test-divisor into ${A}/chain-test/ (find its options; BIN and CS need --select), run ${X}/run_bwx8.sh for session 1 and session 2 with the BWX8_* test overrides (dummy marker path, results under chain-test, SESSION1_END set more than 3 hours in the past) for the steps B6W, S2, S4, P3G, P3, S3G, S3 (and BIN if cheap; counter steps only if software events can stand in, else say so) on CPUs that exist here, then analyze8 summary, a forecast into margins.json where the commands allow it, then report8.py. Checks: every scheduled process has its output; counts of processes and trials equal the schedule; the report contains each required section and the TEST DATA banner and no decision word for test data; the page has no dark background. Keep the test run short (divisor so that the whole chain takes a few minutes; note the run_bwx8.sh wait of up to 20 s per launch on a loaded machine and whether an override shortens it).
Because real decisions cannot appear with test data, ALSO render the report from synthetic non-test data: use the builder in ${A}/test_analyze8.py to make result folders with realistic rates (old read 67 GB/s flat; new read 85 at 1 MiB falling to 67.7 at 8 MiB; a predecessor effect in Stage 3; one process with a disturbed trial; one killed process) and check that the decision words and the charts appear. Render both pages with the headless Chrome (command in /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md; fonts in ${C}/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts/), look at every screenshot piece with the Read tool, and fix clipped or overlapping labels. Leave the synthetic example page at ${A}/chain-test/report-synthetic-example.html with a banner that says the data are synthetic.`, {
  label: 'report+chain', phase: 'Report', schema: {
    type: 'object', properties: {
      files: { type: 'array', items: { type: 'string' } },
      tests_run: { type: 'array', items: { type: 'object', properties: { command: { type: 'string' }, result: { type: 'string' } }, required: ['command', 'result'] } },
      defects_in_other_parts: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, defect: { type: 'string' }, evidence: { type: 'string' } }, required: ['file', 'defect', 'evidence'] } },
      not_done: { type: 'array', items: { type: 'string' } },
      open_choices: { type: 'array', items: { type: 'string' } },
    }, required: ['files', 'tests_run', 'defects_in_other_parts', 'not_done'] } })
return { reviewed, report }
