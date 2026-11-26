export const meta = {
  name: 'w120-7200-prepare',
  description: 'Review the whole-chip rerun scripts from three angles and compute baselines from the earlier runs',
  phases: [
    { title: 'Review', detail: 'three reviewers, one angle each, on the run scripts' },
    { title: 'Verify', detail: 'one skeptic per blocker or major finding' },
    { title: 'Baseline', detail: 'statistics of the earlier runs, by script' },
  ],
}

const ROOT = '/home/jhan/workspace/titan/cache-perf/crb'
const S = ROOT + '/tmp/agent-scratch/w120-7200-2026-11-17'
const CTX = `
CONTEXT (read this first).
- Project folder: ${ROOT}. Machine "CRB" = an Arm reference server at 192.168.2.45 with 128 CPUs. CPUs 0-63 sit on mesh 0, CPUs 64-127 on mesh 1. Our runs may use CPUs 0-119 only (126-127 are isolated for another user; never touch 120-127). The machine is shared: a marker file /tmp/positron-perf.RUNNING means "start nothing".
- HARD RULE: do NOT ssh to CRB or to any other machine, and run no benchmark. Work with local files only. Do not change any file except the ones this task tells you to write.
- History: on 2026-11-13 a "whole chip test" (120 threads on CPUs 0-119, 256 MiB per thread, DRAM) compared two builds of bench/bandwidth.c. bw_old (source bandwidth.orig.c) has the old read kernel: portable C, 16 running sums (each load is followed by an add). bw_new (source bandwidth.c) has the new read kernel: NEON intrinsics, loads only. The new read kernel gave about 280-305 GB/s against about 465 GB/s for the old one. Script: ${ROOT}/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh. Result: ${ROOT}/results/kernels-20261113T181222Z/ (threads120.csv, probe.txt, summarize.py).
- On 2026-11-15 the drop was investigated with a second runner, bwx12 (kernels oldread = old C read, read = new C read, asmread = hand-written load-only loop; common stop time, 6 s intervals). Facts sheet: ${ROOT}/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md. Run script rx.sh, spec files r*.spec and analysis scripts an.py, an8.py are in that folder. Result folders: ${ROOT}/results/w120-*.
- Memory modules: CRB booted with either 12 or 10 memory modules while the memory speed was 8000 MT/s. On 2026-11-17 about 19:43 UTC the speed was set to 7200 MT/s, and 6 of 6 boots then had 12 modules. Notes: /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/crb-memory-module-count-varies-per-boot.md ; report /home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md ; data ${ROOT}/results/dimm-check-20261117/ and ${ROOT}/results/dimm7200-20261117/ (boots.txt, try*.txt).
- The task of today: rerun the whole chip test at 7200 MT/s with the old read kernel and the new read kernel, then compare old against new, and compare today against the earlier 8000 MT/s results.
- New run scripts (not yet run): ${S}/ra.sh (part A: the 120-thread part of run_kernels.sh with the same binaries), ${S}/like.spec, ${S}/cfwd.spec, ${S}/crev.spec (spec files for rx.sh and bwx12), ${S}/go.sh (three sessions of A, L, C). On CRB the folder will be ~/cache-perf/w120-7200-20261117/. The CRB state seen at 21:41 UTC today: marker absent, MemTotal 395392808 kB (12 modules), boot id 3bfc57a1-e235-4fe5-8c09-a94642f9b60b (the boot for which ${ROOT}/results/dimm7200-20261117/try6.txt recorded 12 modules at 7200 MT/s), load 0.00, no other login. The kernel log is not readable without root on CRB, and root is not approved for this task.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          file: { type: 'string' },
          line: { type: 'string' },
          issue: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['id', 'severity', 'file', 'issue', 'evidence', 'fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok'],
}
const VERDICT = {
  type: 'object',
  properties: {
    real: { type: 'boolean' },
    reason: { type: 'string' },
    best_fix: { type: 'string' },
  },
  required: ['real', 'reason', 'best_fix'],
}
const BASE = {
  type: 'object',
  properties: {
    script_path: { type: 'string' },
    how_to_run: { type: 'string' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          folder: { type: 'string' },
          run_utc: { type: 'string' },
          modules: { type: 'string' },
          speed: { type: 'string' },
          state_evidence: { type: 'string' },
          layout: { type: 'string' },
          method: { type: 'string' },
          binary: { type: 'string' },
          kernel: { type: 'string' },
          n: { type: 'number' },
          min: { type: 'number' },
          median: { type: 'number' },
          max: { type: 'number' },
          values: { type: 'array', items: { type: 'number' } },
        },
        required: ['folder', 'modules', 'speed', 'state_evidence', 'method', 'kernel', 'n', 'min', 'median', 'max', 'values'],
      },
    },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['script_path', 'how_to_run', 'rows', 'notes'],
}

const LENSES = [
  {
    key: 'fidelity',
    prompt: `You review the new run scripts for FIDELITY to the earlier tests. Question: does part A (ra.sh) reproduce the 120-thread part of run_kernels.sh exactly: same binaries (sha256 values against ${ROOT}/results/kernels-20261113T181222Z/probe.txt), same process arguments, same kernel order, same round order, same pinning (taskset), same csv header lines so that summarize.py of the old result folder still parses the output? List every difference between the old procedure and the new one that could change a measured rate (for example: the old script ran about 5 minutes of one-thread work first and built the binaries first; the new one waits and sleeps before the first process). Is like.spec byte-identical to the a6456 line of ${ROOT}/tmp/agent-scratch/w120-2026-11-15/r8.spec, and do cfwd.spec and crev.spec name kernels that exist in ${ROOT}/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c with arguments that bwx12 accepts (check the argument parser: --seq, --rounds, --stop, --start, --count, --pmu-type, --events)? Does go.sh call rx.sh the way rx.sh expects (rx.sh NAME BINARY SHA256 < spec)? Is the rx.sh sha256 in go.sh the sha256 of the local rx.sh?`,
  },
  {
    key: 'safety',
    prompt: `You review the new run scripts for SHARED-MACHINE SAFETY and ROBUSTNESS. Rules for CRB are in ${ROOT}/jeremy-plan-constraints-2026-10-30.md (section "Constraints for our cache/DRAM benchmark runs"). Check: the marker file is tested before every process and nothing starts when it exists; only CPUs 0-119 are used and nothing can land on 120-127; no sudo; nothing is written outside ~/cache-perf/results; memory use fits (120 threads x 256 MiB, twice that for copy kernels, 395 GB installed); a failure in any step stops the chain with a clear message and leaves no process running (trace "set -euo pipefail" in ra.sh line by line for commands whose non-zero status would end the script by accident, for example the load-wait loop, grep, sha256sum -c with a here-document inside a subshell, "who | wc -l"); what happens to the run if the ssh session that started go.sh drops (go.sh will be started with nohup and setsid, output to a log file). Trace go.sh: exit codes of rx.sh (it ends with a "head" command), the "fail" function, the choice of the spec file. Read rx.sh fully (${ROOT}/tmp/agent-scratch/w120-2026-11-15/rx.sh). You may run "bash -n" and shellcheck-like reasoning locally, and you may dry-run fragments locally with harmless stand-in commands, but never the benchmark.`,
  },
  {
    key: 'validity',
    prompt: `You review the DESIGN of the rerun for EXPERIMENTAL VALIDITY. The two questions the data must answer: (1) at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much; (2) did the change from 8000 to 7200 MT/s move either kernel's rate, compared with the earlier runs that had 12 modules at 8000 MT/s. Read go.sh, ra.sh and the spec files, the facts sheet FINDINGS.md, and the memory note on the module count. Judge: is the number of intervals and processes per cell enough to state a range and to separate old from new (earlier ranges: old 464-470 GB/s, new 280-310 GB/s); which confounds remain (order of kernels, a rising load average from the script's own earlier processes, the state of transparent huge pages, time of day, the 0.5 s whole-pass stop rule of bandwidth.c that FINDINGS.md says distorts write totals); which earlier result folders are valid like-for-like baselines for each part and which are NOT (10-module boots; runs with firmware test settings); which machine-state facts must be recorded with the run so that each claim can cite them (go.sh records boot id, MemTotal, load, logins, marker state). Name anything that is missing and would make a conclusion unsupported. Do not ask for more scope than the two questions need.`,
  },
]

function reviewPrompt(l) {
  return `${CTX}
YOUR TASK. ${l.prompt}
Report only findings you can support with a quoted line or a concrete trace. Severity: blocker = the run would be wrong, unsafe or would fail; major = a conclusion would be unsupported or misleading without the fix; minor = worth a note. For each finding give the smallest fix. Also list what you checked and found correct ("checked_ok"). Be concrete: file, line, quoted text.`
}

phase('Review')
const reviewsP = pipeline(
  LENSES,
  l => agent(reviewPrompt(l), { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }),
  (rev, l) => {
    if (!rev) return null
    const hard = rev.findings.filter(f => f.severity !== 'minor')
    return parallel(hard.map(f => () =>
      agent(`${CTX}
YOUR TASK. A reviewer (angle: ${l.key}) reported the finding below about the new run scripts. Try to REFUTE it: read the named file and line, trace the behaviour yourself, and decide whether the problem is real and whether it matters for the two questions of today (old against new at 7200 MT/s; 7200 against 8000 MT/s). You may dry-run shell fragments locally with harmless stand-in commands; never run the benchmark and never ssh. If the finding is real, give the smallest correct fix (exact replacement text where possible).
FINDING: ${JSON.stringify(f)}`, { label: `verify:${l.key}:${f.id}`, phase: 'Verify', schema: VERDICT })
        .then(v => ({ ...f, lens: l.key, verdict: v }))
    )).then(vs => ({ lens: l.key, checked_ok: rev.checked_ok, minor: rev.findings.filter(f => f.severity === 'minor'), verified: vs.filter(Boolean) }))
  }
)

const baseA = agent(`${CTX}
YOUR TASK (baseline A: the original whole chip test). Write a small Python 3 script ${S}/stat_k120.py that takes one or more result folders (each holds a threads120.csv in the format of ${ROOT}/results/kernels-20261113T181222Z/threads120.csv) and prints, per folder and per (kernel, binary): the number of intervals n, min, median, max of aggregate_GBps, the list of values in file order with their round, and the per-thread min and max columns; plus the "load" value of each "-- binary" header line (min and max per folder). It must also be able to print the same statistics pooled over several folders given with an option --pool. Add an option --json that prints the rows as JSON. Use only the standard library. Model the parser on summarize.py in that folder but do not import it. Then run it on ${ROOT}/results/kernels-20261113T181222Z and return the rows for all six kernels and both binaries (folder, kernel, binary, n, min, median, max, values). Check your numbers against FINDINGS.md section "The question" (read: old 464.4-466.7, new C 279.7-304.1, asm 271.1-305.9, n=6 each) and report any difference in "notes".
Also establish, from the local records named in CONTEXT, how many memory modules CRB had and at which memory speed during that run (2026-11-13 18:17 UTC): cite the file and line that proves it (boot history, MemTotal or "DIMM sockets" records). If the records do not prove it, say "Insufficient data" in state_evidence and name the record that would prove it. Fill "method" with "bandwidth.c, whole-pass stop, 0.5 s, 3 intervals per process", "layout" with "120 threads, CPUs 0-119".`, { label: 'baseline:original-test', phase: 'Baseline', schema: BASE })

const baseB = agent(`${CTX}
YOUR TASK (baseline B: the bwx12 runner at 120 threads, 64 on mesh 0 + 56 on mesh 1). Write a small Python 3 script ${S}/stat_bwx.py that takes one or more result folders with bwx csv files (format: see the "#" header lines of ${ROOT}/results/w120-w120-F72d12-20261117T200231Z/a6456.csv and the parser in ${ROOT}/tmp/agent-scratch/w120-2026-11-15/an.py) and prints, per folder, per csv file and per interval (round, pos, kernel): the number of threads, the total rate in GB/s computed as the sum over threads of bytes / elapsed_s / 1e9 (the method of an.py), the same sum for the threads on CPUs 0-63 and for the threads on CPUs 64-127, the per-thread min and max in each half, and the aggregate_GBps of the matching "I" row; then per folder and kernel, for intervals with exactly 64 threads on CPUs 0-63 and 56 threads on CPUs 64-119 only: n, min, median, max of the total. Add --json for machine-readable rows and --pool to pool folders. Use only the standard library. Copy kernels count read plus written bytes; this task needs read kernels only, so just skip nothing and label nothing specially, but keep the kernel name.
Run it on these folders and return rows for the kernels oldread, asmread and read (where present), 64+56 layout only, one row per (folder, kernel): w120-R0-20261115T165608Z, w120-R0b-20261115T170342Z, w120-R1-20261115T185140Z, w120-R5-20261115T203152Z, w120-R6-20261115T203438Z, w120-R8-20261117T020549Z, w120-X1d10-20261117T034916Z, w120-X1d10b-20261117T040407Z, w120-X2d12-20261117T040922Z, w120-BASEd10-20261117T041738Z, w120-w120-F72d12-20261117T200231Z (all under ${ROOT}/results/). In "values" give the totals in file order.
For every folder establish the machine state at run time: number of memory modules (12 or 10), memory speed (8000 or 7200 MT/s), and whether a firmware test setting was active (the X1/X2 folders belong to a firmware "CPU TXREQ Throttle" test; say what the records show). Cite the proving file and line in state_evidence (boot history in ${ROOT}/results/dimm-check-20261117/ and dimm7200-20261117/boots.txt, the memory note, the DIMM report, env.txt of the folder). If the local records do not prove a state, write "Insufficient data" and name the record that would prove it. Fill "method" with "bwx12, common stop, <interval length> s" from the launch arguments in launches.txt, and "layout" with "64+56". Check your oldread and asmread ranges against FINDINGS.md table F2 (oldread 465.5-470.1 with n=22 and asmread 288.5-309.8 with n=22 over R0, R0b, R1, R5, R6) and report any difference in "notes".`, { label: 'baseline:bwx12-runs', phase: 'Baseline', schema: BASE })

const [reviews, a, b] = await Promise.all([reviewsP, baseA, baseB])
return { reviews, baselineA: a, baselineB: b }
