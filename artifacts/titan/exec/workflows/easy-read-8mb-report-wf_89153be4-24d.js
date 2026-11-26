export const meta = {
  name: 'easy-read-8mb-report',
  description: 'Build tackle-8mb-report-easy-read.html: top-down, proof data only, test code call chain',
  phases: [
    { title: 'Understand', detail: 'map the test code call chain; collect the proving numbers' },
    { title: 'Build', detail: 'write the generator and the page' },
    { title: 'Review', detail: 'newcomer read, proof of numbers, code excerpts and render' },
    { title: 'Fix', detail: 'apply findings, regenerate, re-check' },
  ],
}
const SP = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/c9b7353a-0350-43e2-b1b1-7bf2887baa7e/scratchpad/easy'
const C = '/home/jhan/workspace/titan/cache-perf/crb'
const N = C + '/new-test-kernel'
const A = N + '/tackle-8mb-analysis'
const X = C + '/tmp/agent-scratch/bwx8-2026-11-14'
const Z = C + '/tmp/agent-scratch/bwx11-2026-11-15'
const OUT = N + '/tackle-8mb-report-easy-read.html'

const CONTEXT = `
BACKGROUND. An investigation on the CRB machine (Arm Phoenix Reference Server, 128 cores, 2.8 GHz, L1 64 KiB, L2 2 MiB per core, shared SLC 128 MiB) asked: why does the new load-only read kernel raise read throughput by 27 % at a 1 MiB buffer but by only about 1 % (original measurement 0.94 %) at 8 MiB? The full report is ${N}/tackle-8mb-report.html (generator ${A}/report_final.py, all numbers in ${A}/final8.json, readable dump ${A}/final8.txt). Result handoff: ${N}/tackle-8mb-results.md. Design and goal: ${N}/tackle-8mb.md and ${N}/tackle-8mb-handoff.md. Decision rules written before the data: ${X}/DECISIONS-bwx8.md. Test runner sources: ${X} (bwx8 build, steps S2, S4, round 2), ${C}/tmp/agent-scratch/bwx10-2026-11-15 (bwx10), ${Z} (bwx11: bwx11.c, run_bwx11.sh, visit11.sh, schedule11.py, schedule_zs.py, sched11/). Original benchmark: ${C}/../bench/bandwidth.c (find it; do not change it). Analysis: ${A}/final8.py. Result folders: ${C}/results (read only).
The user said about the full report: "I am lost at all the details." They asked for a NEW page ${OUT} with these three requirements (verbatim):
 - it uses top down structure, start with end goal, illustrate the thinking and testing process which led to conclusion
 - only show the test data proving the conclusion
 - List test code, not only the kernel, also the top level test code. Do not list whole file content, but need to list all the test functions which got called
THE CONCLUSION and its proof chain (established; do not re-derive, but verify each number against final8.json):
 1. The effect is real and it comes from the new loop, not the old one (step S2): gain 27 % at 1 MiB; 3.35 to 6.75 % at 8 MiB; old read keeps 67 GB/s at both sizes (prediction P1, margin 0.30 GB/s), the new loop falls (P2).
 2. Mechanism (hypothesis H1c): in processor cycles per 64-byte line, old read costs about 2.67 at every size from 1 to 16 MiB; the new loop costs about 2.08 + 0.66 x r, where r is the share of lines that enter L2 from the SLC (counter l2d_cache_refill per line). At 8 MiB r = 0.83, so the new loop costs 2.50 to 2.67, almost the old cost. Test "size as dose" (step ZS): band fixed before the data, 10 of 11 counted sizes inside in each of the 4 CPU x session cells.
 3. Controlled change (step ZN): load-only loops slowed by no-operation instructions (read_nop96, read_nop128) keep their 32 KiB rate at 8 MiB in 4 of 4 cells; the gain of asmread over a kernel of core rate C follows the prediction from two rates (12 of 12 cells inside; this evaluation is supplementary = defined after the data was seen).
 4. Why the first measurement said 0.94 %: at 8 MiB the new loop moves between two rate levels; the original program on CPU 2 sat at the low level (step H2: median gain 0.22 % and 0.17 %; on CPU 0 5.73 % and 5.71 %).
 Dead ends that the thinking passed through (state each in one or two sentences with its verdict, at most one number each, no table): the count of L1 misses as the limit (H1b, prefetch test, recorded verdict "not confirmed"); dirty lines / write-backs (H1d, evict test, "Insufficient data"); kernel timer or host activity as cause of the level switches (H3a, not supported); address of the runner's window record (H7; recorded verdicts "supported" session 1, "undecided" session 2).
 Not explained (Insufficient data, need root): why an SLC line costs about 0.66 cycles more; which hardware part switches the two levels; why old read needs 2.67 cycles per line.
 Run facts to state once: every step ran in 2 sessions at least 3 h apart on CPUs 2 and 41; system load at launch 0.00 to 1.23 (1-minute load average; about 1.00 is the test itself, est.).
`

phase('Understand')
const [codemap, datapack] = await parallel([
  () => agent(`${CONTEXT}
YOUR TASK: map the TEST CODE that produced the proving steps S2 (round 1), ZS and ZN (round 4) and H2, from the top level down to the kernels. Write the result to ${SP}/codemap.md (create the folder). The page author will build the "Test code" section from it, so be exact.
Find out and record, each with file path and line numbers:
 a) Which script a login started, and the chain from there: visit script -> run script -> (schedule / plan generation) -> runner binary command line -> C functions -> kernel. For step H2 the chain goes to the ORIGINAL benchmark (find run_h2.sh / visit_h2.sh in ${X} and the bandwidth program they call).
 b) For the C runner: the ordered list of EVERY function that is called on the path of one measured window of a plan trial, from main() to the kernel call and to the output row (for example main, read_plan, pin_cpu, alloc_buf, alloc_records, count_open, trial_worker, run_trial, set_windows, tcall, the kernel, tclock, read of the counter group, emit_trial ... verify the real names and order by reading the code; do not trust this example). One line per function: what it does for the measurement. Mark which functions run only with certain options (counters, evict, rec-pad).
 c) The kernels that matter for the proof: oldread (the old read loop with vector adds), read / asmread (load-only), read_nop96 and read_nop128, and how the buffer size and the count of passes per window are set. For each: the source lines, and where available the built instructions from the build listing (crb-build-1/listing.txt) so the page can show the real machine loop.
 d) How a rate (GB/s) and cycles per line and r are computed from a window: which fields are timed, which counter events are opened (names and raw codes), and where the analysis (${A}/final8.py) turns rows into the numbers and applies the recorded rules for S2, ZS, ZN and H2 (function names and lines).
 e) Whether steps S2 ran the bwx8 binary and ZS/ZN the bwx11 binary, and whether the functions of (b) and the kernels of (c) are textually identical between bwx8.c and bwx11.c (run diff on the relevant functions; say exactly what differs).
 f) One real plan-file excerpt (a few lines) of step ZS and of step ZN, and the real command line of the runner from a result folder or the run script, with a legend of the row fields.
For every item propose a SHORT verbatim excerpt (5 to 25 lines) with path:first-last line, chosen so that the generator can cut it from the file by line range or by function name. Do not paste whole files. Do not edit anything outside ${SP}. Return a 15-line summary of the chain plus the path of the file.`, { label: 'map:code', phase: 'Understand' }),
  () => agent(`${CONTEXT}
YOUR TASK: collect the PROVING DATA, and only that, into ${SP}/datapack.md (create the folder). The page author will write a generator that reads ${A}/final8.json, so for every number give: the value with unit, the exact JSON path / selection in final8.json (verify by running a small Python snippet), the step name and result folder, and the metric name. Look at how ${A}/report_final.py selects the same numbers (methods rows, zs, zs_fit, gains8, cycles8, gain_rows, fam, read_h2 ...) and name the reusable selection.
Collect:
 1. Step S2: per CPU (2, 41) and session (1, 2): rate of old read, read, asmread at 1 MiB and 8 MiB (GB/s), gain in %, and the recorded verdict strings of P1 and P2.
 2. Step ZS: for old read and asmread per size (all counted sizes, 32 KiB to the largest): rate, cycles per line, r; the fitted line per cell; the band that was fixed before the data and where DECISIONS-bwx8.md records it (line numbers, quote); the count inside/outside per cell and which size lies outside; the recorded verdict string.
 3. Step ZN: read_nop96 and read_nop128 (and asmread) at 32 KiB and 8 MiB per cell; the recorded rule and verdict strings; the supplementary predicted-gain table (12 of 12) with its formula and its label.
 4. Step H2: per CPU (0, 2, 41) and session: share of repetitions at the low level, median gain, verdict string; plus the two level values (low / high GB/s per CPU) and one example trace source (which S4 folder/CSV report_final.py reads for the 60 s traces) in case the author wants one small trace chart.
 5. The original observation: where the 0.94 % and the 27 % of the first measurement come from (file, run).
 6. Dead ends: for H1b, H1d, H3a, H7 the recorded overall verdict string and at most one number each.
 7. Run facts: sessions, CPUs, load range at launch (JSON path), count of processes and folders.
Also list any number in the CONTEXT above that you could NOT confirm in final8.json, with what the JSON says instead. Do not edit anything outside ${SP}. Return a 15-line summary plus the path of the file.`, { label: 'map:data', phase: 'Understand' }),
])

phase('Build')
const build = await agent(`${CONTEXT}
Two agents prepared inputs for you: the test-code map ${SP}/codemap.md and the proving-data pack ${SP}/datapack.md. Summaries:
--- code map ---
${codemap}
--- data pack ---
${datapack}

YOUR TASK: write the generator ${A}/easy_report.py (standard library only) and run it to produce ${OUT}. Load the dataviz skill before you draw charts. You may import helpers from ${A}/report_final.py (the Plot / svg / table helpers, number formatting) or copy what you need; do not change report_final.py or any other existing file.
RULES OF THE GENERATOR
 - Every number on the page is read from ${A}/final8.json (or a result CSV) at run time; type none by hand. Verdict texts are the strings of final8.json, introduced as "as recorded".
 - Every code excerpt is cut from the real source file at run time (by function name or by start/end marker text, with a check that fails loudly if the marker is missing) and printed with its file name and line range. Excerpts are short (about 5 to 25 lines); a long function is cut with a clearly marked "[...] lines a-b left out" line that the generator inserts. Never print a whole file.
 - One self-contained HTML file: inline CSS and inline SVG, no script source, no URL, LIGHT background only (no dark theme, color-scheme light). It must not scroll sideways at 1200 px or at 390 px; code blocks scroll inside their own box.
PAGE DESIGN: the reader got lost in the full report. This page is the opposite: short, top-down, one idea per screen. Aim for a 10-minute read: about 5 charts, at most 6 small tables, no table over about 12 rows. Order:
 0. Title; "Short version" (at most 3 short sentences); one line with the load and the run facts.
 1. "The goal": the observation (27 % against 0.94 %), the question, and what counts as an answer (a named mechanism; a controlled test that changes the mechanism and moves the gain as predicted on both CPUs and both sessions; a statement of what stays unexplained).
 2. "The answer in one picture": ONE chart, cycles per 64-byte line against buffer size for old read (flat) and the new loop (rising toward it), with direct labels, the 1 MiB gap and the 8 MiB gap annotated on the figure, and a one-line takeaway. Then 3 to 4 bullets that say the answer in words.
 3. "How we got there": a left-to-right or top-down inline SVG flow diagram of the thinking: observation -> question 1 "is it real, and which loop changes?" -> idea(s) tried -> the idea that held -> the controlled test -> the remaining puzzle of 0.94 %. Dead ends are drawn as short side branches in a muted colour with their verdict. Then one subsection per step of the path, each in the same fixed pattern of four short labelled parts: "Question", "Idea / prediction (fixed before the data)", "Test" (step name, what was run, link to the code subsection), "Result" (the single chart or small table that proves it, with the recorded verdict) and one line "So". Steps: (1) S2: real, and the new loop is the one that changes; (2) dead ends in one compact list, no data tables; (3) ZS: cost per line follows r; (4) ZN: change the core cost, the gain moves as predicted; (5) H2 / two levels: why the first measurement said 0.94 %.
 4. "Conclusion": the three goal conditions from section 1 as a checklist, each with "met by" and the step; then "Not explained (Insufficient data)" with the measurement that would decide each point. Label the supplementary evaluation as supplementary (defined after the data was seen) and hypotheses as hypotheses.
 5. "The test code": first a call-chain diagram (inline SVG or an indented tree, vertical if wider than 70 columns) from the login script down to the kernel loop and back up to the analysis rule: visit script -> run script -> plan file -> runner main() -> ... -> kernel -> output row -> final8.py rule. Then a table "every function on the path of one measured window": name, file:line, one-line role, in call order, complete per the code map. Then short excerpts, top level first: the visit and run scripts (the lines that check the marker file, record the load, pin the CPU and start the runner), a plan-file excerpt with a legend, the runner's trial loop and timing/counter code, the kernels (old read, load-only, the nop variant; C source and, where the code map gives it, the built machine loop), the original benchmark's part used by step H2, and the analysis functions that compute rate, cycles per line, r and apply the rules. Say which binary (bwx8, bwx11, original benchmark) ran which step and what differs between the builds.
 6. "Words used here" (near the top, after the Short version, as a compact list: only terms this page uses) and "References" at the end ([RefN] style: files, result folders, the full report). In the body a claim sentence ends with its [RefN].
WRITING: the plain-english rules of the user's CLAUDE.md in full: short sentences (at most about 20 words), one claim per sentence, bullets, no idioms, units on every number, estimates marked "est.", every claim tied to a named step and metric, anything else labelled hypothesis. Prefer a picture or a 3-row table to a paragraph. No per-cell detail beyond what a proof needs: where 4 cells agree, show the 4 values compactly (small multiples or a 4-row table), not more.
CHECKS before you return: run the generator; confirm the page has no external reference; render it with the headless Chrome named in the memory file /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md at 1200 px and 390 px width, look at the screenshots (save under ${SP}), and fix overlaps, clipped labels and sideways scroll; read the page text once as a newcomer and cut anything that is not needed to follow the proof.
Return: the section outline as built, counts (charts, tables, excerpts, words of prose), what you left out on purpose, and any number of the CONTEXT that the data did not confirm.`, { label: 'build', phase: 'Build', effort: 'high' })

phase('Review')
const FIND = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  where: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, problem: { type: 'string' }, fix: { type: 'string' } },
  required: ['where', 'severity', 'problem', 'fix'] } } }, required: ['findings'] }
const LENSES = [
  ['newcomer', `Read ${OUT} as an engineer who has never seen the project (render it with headless Chrome per /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md, or read its text). Judge it against the user's three requirements and the complaint "I am lost at all the details". Report: places where you lose the thread; a term used before it is defined; a step of the thinking that does not follow from the one before; detail that is not needed to follow the proof (name what to cut); data shown that does not prove the conclusion; plain-english rule violations (rules in the user's CLAUDE.md: long sentences, two claims per sentence, idioms, numbers without unit, missing Short version); charts without direct labels or takeaway; anything not top-down.`],
  ['proof', `Verify ${OUT} against the data. For EVERY number and verdict on the page: find it in ${A}/final8.json or ${A}/final8.txt (write a script; compare at the printed rounding) and check it is attached to the right step, CPU, session, kernel, size and unit. Check each claim is tied to a named step and metric, that a pre-fixed rule is really recorded in ${X}/DECISIONS-bwx8.md before its data, that supplementary evaluations are labelled as defined after the data was seen and do not replace a recorded verdict, that hypotheses and "Insufficient data" points are labelled, that nothing is stated more strongly than ${N}/tackle-8mb-results.md and the full report state it, and that the charts draw the values they claim (read the SVG coordinates or the generator ${A}/easy_report.py). Also confirm the generator reads numbers from the JSON and types none.`],
  ['code', `Verify the "test code" part of ${OUT} against the sources (generator ${A}/easy_report.py; sources under ${X}, ${Z}, the bench folder; map ${SP}/codemap.md). Check: every excerpt is verbatim at the stated file and line range; the call chain and the function table are complete and in the true call order for one measured window (read main() and the worker of the runner yourself and list any called function that is missing or any listed function that is not on the path); the statement of which binary ran which step is right (check result folders / run scripts); the top-level scripts and the analysis rule functions are shown, not only kernels; no whole file is printed; no excerpt leaks a password, key or private address beyond what the full report already prints. Also render the page with headless Chrome (memory file /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md) at 1200 px and 390 px: report sideways scroll, overlapping or clipped chart text, unreadable code blocks, non-light background, any external URL or script.`],
]
const reviews = await parallel(LENSES.map(([k, p]) => () => agent(`${CONTEXT}\nREVIEW TASK (${k}). ${p}\nReport only real defects, each with a concrete fix. Do not edit any file except scratch files under ${SP}.`, { label: `review:${k}`, phase: 'Review', schema: FIND })))
const findings = reviews.filter(Boolean).flatMap(r => r.findings)
log(`${findings.length} findings`)

phase('Fix')
const fix = await agent(`${CONTEXT}
The page ${OUT} is produced by ${A}/easy_report.py. Builder's notes: ${build}
Three reviewers (newcomer read, proof of numbers, code and render) reported: ${JSON.stringify(findings)}
For each finding: verify it, then fix it in the generator (numbers stay read from final8.json, excerpts stay cut from the sources at run time) or reject it with a one-line reason. When a newcomer finding asks to cut detail, cut it: the page must stay short and top-down. Then regenerate, re-render at 1200 px and 390 px with headless Chrome (memory file /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md), look at the screenshots, and re-check that the page has no external reference and a light background. Change no existing file other than easy_report.py and its output.
Return: per finding "fixed" or "rejected: reason"; final counts (charts, tables, code excerpts, words of prose, bytes); the final section outline; anything left open.`, { label: 'fix', phase: 'Fix', effort: 'high' })
return { build, nFindings: findings.length, fix }
