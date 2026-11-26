export const meta = {
  name: 'implement-meshmap',
  description: 'Implement meshmap.c and run_map.sh per the spec, build and test on host and CRB, review adversarially, fix',
  phases: [{ title: 'Implement' }, { title: 'Harness' }, { title: 'Review' }, { title: 'Fix' }, { title: 'Verify' }],
}
const S = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/cb96bba4-a5c1-4b47-b0fa-d3c0c4267082/scratchpad'
const R = '/home/jhan/workspace/ai-runs/asimov-repo/cache-mem-perf'
const COMMON = `
Specification: ${S}/SPEC.md (read it fully first; it is binding). Background: ${S}/critique/c1.txt, c2.txt, c3.txt (why the spec is as it is) and ${S}/understand/r3.txt (survey of the existing code), r5.txt (topology, PMU).
Repository: ${R}. Do NOT run any git command that changes state (no add, commit, stash, checkout, reset). Do NOT edit files outside ${R} except your own scratch files under ${S}/impl/. Do not ssh anywhere unless your task says so. Follow the user's coding rules already in your context (minimum code, surgical changes, match the existing style of latency.c/common.h/cmncount.c/run_l3.sh, fail loud). Never write the word "hop" in any new text. Comments in plain English, short sentences.
`
phase('Implement')
const impl = await agent(COMMON + `
Your task: write ${R}/meshmap.c (and the one new perf-set open function in common.h only if needed) implementing SPEC.md sections 1 to 5 and 8 completely. Add the Makefile target (meshmap in all and clean, built like latency). Read latency.c, common.h and cmncount.c first and reuse their helpers and style; copy cmncount's sysfs config builder into meshmap.c with a comment saying it is a copy (cmncount.c stays byte-identical). latency.c must stay byte-identical.
Then build on this x86 host with the Makefile (look at how the Makefile handles a non-aarch64 compiler; the existing binaries here are x86 builds made with an override of CFLAGS such as CFLAGS=-O2: find what works, do not change the default flags) and make these pass:
  ./meshmap --selftest            (exit 0, prints each check)
  ./meshmap --no-perf --no-ocm --cpus 0 --lines 256 --reps 3 --out ${S}/impl/t1.csv --homes ${S}/impl/t1.homes
  ./meshmap --no-perf --no-ocm --cpus 0,1 --last-cpus 2 --lines 64 --reps 7     (rows to stdout)
  a run with a CPU that does not exist in --cpus (must drop it with a # line and still finish; exit code 1 because cells are missing)
  a run WITHOUT --no-perf on this host (no arm_cmn PMU here): must print the "no mesh counters" line, skip the DRAM kinds, and finish without crashing.
Compile with -Wall -Wextra clean. Check the CSV by eye and with a small python check: header column count equals every row's field count; rows per cell = reps; kinds named slc-fake / dram-flush-fake under --no-perf.
The code paths that only run with the real PMU (group open, level fallbacks, read floor, classification, probes) cannot run here: desk-check them line by line against SPEC section 3 C and D and against the kernel ABI (struct perf_event_attr fields, read_format layout for GROUP|TOTAL_TIME_ENABLED|TOTAL_TIME_RUNNING: nr, time_enabled, time_running, values[nr]; for a non-group event: value, time_enabled, time_running). Guard aarch64-only instructions (DC CIVAC, DSB) the way common.h does for x86 builds.
Return: the list of files changed, the exact build command that works on x86, the test commands and their outcomes, every place where you deviated from SPEC.md and why, and anything you could not verify.`, { label: 'implement:meshmap.c', phase: 'Implement', effort: 'high' })

phase('Harness')
const harness = await agent(COMMON + `
meshmap.c already exists in the repository (another engineer wrote it; its report is below). Your task: SPEC.md section 6: write ${R}/run_map.sh, extend ${R}/est_chip_time.py for the meshmap command, and update ${R}/README.md (Files table, phase table, Words used here, Output format, reading rules of SPEC section 7, chip-time paragraph). Read run_l3.sh, lib_run.sh, run_all.sh, est_chip_time.py and README.md first and match them. Check meshmap's real options with ./meshmap (usage text) and its real output format by running it, so README and the script match the program, not the spec, where they differ (and report each difference).
Then verify on this host (build with the same command the implementer reports):
  sh -n run_map.sh
  sh run_map.sh --dry-run            and   sh run_map.sh --dry-run --kernel-cpus   (the second must add --last-cpus 0 and must not exit 2)
  sh run_map.sh --dry-run | python3 est_chip_time.py     (print the estimate; it must count the meshmap command)
  sh run_l3.sh --dry-run | python3 est_chip_time.py  and  sh run_asimov.sh --dry-run | python3 est_chip_time.py : outputs must be identical before and after your est_chip_time.py change (keep a copy of the original in ${S}/impl/ to compare). If the clone lacks binaries that the dry run requires, build them with make first.
  sh run_map.sh --quick --out ${S}/impl/quick-out    (0 failures; look at every output file)
Then the CRB check: the Arm board is reachable as ssh jhan@192.168.2.45 (aarch64, shared machine, NO sudo, be light: one core, seconds of work). Copy the source files (not binaries) to a NEW directory /tmp/jhan-meshmap-build/<date-time> there with scp, run make with the Makefile's default flags (-mcpu=cortex-a520 -static; if the default fails, report the exact error, and try the flags earlier CRB build checks used), then run ./meshmap --selftest and ./meshmap --no-perf --no-ocm --cpus 3 --lines 256 --reps 3 and one run without --no-perf (as a normal user the PMU open is refused: the program must say so and finish). Report compiler warnings verbatim. Do nothing else on that machine and leave the directory in place.
Return: files changed, every command with its outcome, the est_chip_time numbers, CRB results, and all mismatches found between SPEC.md and meshmap.c.

Implementer's report:
` + impl, { label: 'harness:run_map.sh', phase: 'Harness', effort: 'high' })

phase('Review')
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, severity: { type: 'string', enum: ['boot-losing', 'wrong-data', 'minor'] }, file: { type: 'string' }, line: { type: 'integer' },
  problem: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'severity', 'file', 'problem', 'evidence', 'fix'] } },
  sound: { type: 'string' } }, required: ['findings', 'sound'] }
const LENSES = [
  { key: 'pmu-abi', p: 'the mesh PMU code in meshmap.c that has never executed: sysfs config builder, perf_event_open arguments for the arm-cmn driver (pid -1, cpu = cpumask CPU, no exclude bits, group leader/member fds, pinned), the three fallback levels, read() buffer layouts for group and single events, enabled/running checks, signed deltas, the read floor, closing fds. Compare with cmncount.c (proven on the emulator) and the driver copy /tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/kernel/arm-cmn.c. A mistake here loses the DRAM kinds of a boot.' },
  { key: 'classify', p: 'classification in meshmap.c: the probe sequence (neighbours, flush-and-load pairs, one read per line), the decision rule and floor correction, retries, the restart with doubled P, the projection and the step-down of lines, pool end handling, the homes file, and that NO path exits or loops forever (a hang meets the 12 chip-second kill and loses buffered data; an infinite retry loop is the worst case). Simulate by hand: every line ambiguous; counters that never move; counters that move on all nodes equally; one node never appearing.' },
  { key: 'recipe', p: 'the measurement recipe in meshmap.c against SPEC sections 1, 4, 5 and critique c2.txt: chain build per cell on the measuring CPU, slots 0-6 vs slot 7, the store-preload, the evictor list (excludes exactly node k DRAM chain lines; order re-indexing visits each once; (a,s) coprime), warm-up counts, bracket order (mesh read, core start, clock, chase, clock, core stop, mesh read), dram-flush storing slot 7 after its last pass, the flush kinds, per-load normalisation, idle rows, seeds differing per (kind,node,cpu,rep), the compiler not optimising the loads away, pointer chase correctness (returns to start after lines loads), OCM mapping and the region-to-node order. Also check that x86 guards do not change aarch64 behaviour.' },
  { key: 'robustness', p: 'failure handling and output in meshmap.c and run_map.sh: every row and # line flushed at once to --out (append mode), nothing lost on SIGKILL; no exit() reachable after preflight except at the end (grep for exit, die, abort, assert and the common.h helpers that exit: pin_cpu, map_dev, alloc paths); dropped CPUs; OCM absent; exit code rule; stdout summary lines at most 120 characters; run_map.sh option stripping before lib_run.sh, CPU 3 online, never under cmn, quick and dry-run paths, the sysinfo-map.txt step, shell portability (the image has busybox sh only: no bashisms, no arrays, check zcat/grep usage). Run sh -n and the dry runs yourself.' },
  { key: 'docs-est', p: 'README.md changes, est_chip_time.py changes and the script header against the program as it really behaves (run ./meshmap on this x86 host after building: the harness report gives the build command): option names, column names and order, file names, the reading rules, the chip-time arithmetic (redo it by hand with the numbers in the file). Check wording rules: the word "hop" must not appear in any NEW text (git diff shows what is new; git diff is read-only and allowed), plain English, every new term defined, estimates marked est. Check that est_chip_time.py output for the existing scripts is unchanged (run them).' },
]
const reviews = await parallel(LENSES.map(l => () => agent(COMMON + `
You are an adversarial reviewer. READ-ONLY on the repository (you may build and run on this x86 host in a copy under ${S}/impl/review-${l.key}/; do not modify ${R}). The code will run once per emulator boot with no chance to debug. Find real defects only, each with file, line and concrete evidence (a traced execution, a compile or run result, or the driver/ABI text). Do not report style. Your lens: ${l.p}

Implementer's report:
${impl}

Harness report:
${harness}`, { label: 'review:' + l.key, phase: 'Review', schema: FINDINGS, effort: 'high' }).then(r => r && ({ lens: l.key, ...r }))))
const all = reviews.filter(Boolean).flatMap(r => r.findings.map(f => ({ lens: r.lens, ...f })))
log(all.length + ' findings from ' + reviews.filter(Boolean).length + ' reviewers')

phase('Fix')
const fix = await agent(COMMON + `
You are the fixer. Reviewers produced the findings below (JSON). For each finding: check it against the code yourself; if it is real, fix it in ${R} with the smallest change; if it is wrong, say why. Then rebuild with -Wall -Wextra clean and rerun every host test from the implementer's and harness reports (selftest, the --no-perf runs, the run without --no-perf, sh -n, both dry runs, the estimator on all three scripts, sh run_map.sh --quick), and add a selftest case for any logic bug you fixed where a case can catch it. If any C source changed, redo the CRB check exactly as the harness report describes (new directory under /tmp/jhan-meshmap-build/, no sudo, light). Keep latency.c and cmncount.c byte-identical to git HEAD (verify with git diff --stat, read-only).
Return: per finding id: fixed / rejected with the reason; the final test outcomes; the final list of changed files (git status --short, read-only) and anything still unverified.

Findings:
${JSON.stringify(all, null, 1)}

Implementer's report:
${impl}

Harness report:
${harness}`, { label: 'fix', phase: 'Fix', effort: 'high' })

phase('Verify')
const verify = await agent(COMMON + `
You are the final independent verifier. READ-ONLY on ${R}. Reviewers' findings and the fixer's report are below. (1) For every finding the fixer marked fixed, read the current code and confirm the fix is present and correct; for every rejected one, judge the reason. (2) Read meshmap.c top to bottom once more against SPEC.md and list every remaining deviation. (3) Build in a copy under ${S}/impl/verify/ and run: selftest, a --no-perf run, a run without --no-perf, and count rows per cell. (4) git diff --stat and git status --short (read-only): confirm latency.c, cmncount.c, run_asimov.sh, run_l3.sh, run_cme.sh, lib_run.sh are unchanged, and list what changed in common.h, Makefile, est_chip_time.py, README.md.
Return a plain report: confirmed fixes, open defects (with file:line and severity), deviations from the spec, test outcomes, and the changed-file list with line counts.

Findings:
${JSON.stringify(all, null, 1)}

Fixer's report:
${fix}`, { label: 'verify', phase: 'Verify', effort: 'high' })
return { impl, harness, findings: all, fix, verify }
