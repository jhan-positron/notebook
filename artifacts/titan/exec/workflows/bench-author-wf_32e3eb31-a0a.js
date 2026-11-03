export const meta = {
  name: 'bench-author',
  description: 'Write, smoke-test locally, review and fix the cache/DRAM latency+bandwidth microbenchmark for CRB (aarch64)',
  phases: [
    { title: 'Write', detail: 'author source + runner, build and smoke test on local x86' },
    { title: 'Review', detail: 'three independent review lenses' },
    { title: 'Fix', detail: 'apply accepted findings, rebuild, retest' },
    { title: 'Verify', detail: 'independent rebuild + smoke run' },
  ],
}

const DIR = '/home/jhan/workspace/titan/cache-perf/bench'
const SPEC = `
PROJECT: measure best-case latency and maximum throughput (bandwidth) of L1d, L2, L3 and DRAM on "CRB", an aarch64 Linux server. Code is written and smoke-tested LOCALLY (x86_64, Ubuntu 22.04, gcc 11.4, 32 CPUs) and will later be copied to CRB and compiled there with gcc 14.2 (no clang, no cross compiler here). It must compile with plain C11 + POSIX + pthreads + GNU extensions on BOTH gcc 11 (x86) and gcc 14 (aarch64). No external libraries.

CRB facts (from sysfs): 128 cores, no SMT, 2.8 GHz fixed, L1d 64 KiB 4-way private, L2 2 MiB 8-way private, L3 128 MiB 16-way shared by all 128 cores (probably the CMN system-level cache), DRAM 320 GiB, 1 NUMA node, THP enabled=always (2 MiB pages by default for anonymous memory), 64 B lines. perf_event_paranoid=2 (per-task user-mode core counters work; events include l1d_cache_refill l2d_cache_refill l3d_cache_refill ll_cache_miss_rd ll_cache_rd dtlb_walk l2d_tlb_refill cpu_cycles inst_retired). Only CPUs 0-119 may be used; never 120-127. A marker file /tmp/positron-perf.RUNNING means another team's timed run is active: our runner must refuse to start and must stop between phases if it appears.

DELIVERABLES in ${DIR} (create the directory; nothing else outside it):
1. latency.c — single-thread dependent-load pointer chase.
   - Buffer of S bytes (S from --min to --max, doubling, plus the extra sizes given with --sizes list), 64 B elements, random cyclic permutation (Sattolo's algorithm, fixed seed, so a chase visits every line exactly once per cycle). Buffer is 2 MiB-aligned (aligned_alloc or mmap) and madvise(MADV_HUGEPAGE) by default (flag --no-thp to skip). First-touch and permutation build happen before timing.
   - Timed loop: p = *(void**)p unrolled x8 or so, with the final pointer written to a volatile sink so it cannot be optimized out. Warm-up pass over the whole cycle first. Then measure at least --min-ms milliseconds (default 300) AND at least 2 full cycles, using clock_gettime(CLOCK_MONOTONIC). Report ns per load = elapsed / loads. Repeat --reps times (default 3), report the minimum (best case) and all reps.
   - Options: --cpu N (sched_setaffinity to that CPU, default: do not pin), --min, --max, --sizes a,b,c (accepts K/M/G suffixes), --min-ms, --reps, --no-thp. Output one CSV line per size to stdout: size_bytes,rep,loads,ns_per_load  and a final 'best' line per size. Also print the hugepage status actually obtained if cheaply knowable (read /proc/self/smaps_rollup AnonHugePages after first touch; print it, do not fail on absence).
2. bandwidth.c — multi-thread streaming kernels, pthreads.
   - Options: --threads T, --cpus list (e.g. 0-119 or 0,2,4-7; threads pinned round-robin to that list; required when --threads given), --bytes B per thread (K/M/G suffixes), --kernel read|write|copy|all, --min-ms (default 500 per kernel), --reps (default 3), --no-thp.
   - Each thread: allocates its own buffers (read: one; write: one; copy: two), 2 MiB-aligned, madvise(MADV_HUGEPAGE), first-touched BY THAT THREAD (NUMA-safe and page-fault free during timing), warm-up pass. All threads wait on a pthread barrier, then each runs repeated passes over its buffer until the master's time target is reached (check elapsed every pass), counting bytes. Per-thread elapsed is measured from barrier release to its own last pass end. Aggregate GB/s = sum(bytes)/max(per-thread elapsed); also print per-thread min/avg/max GB/s. Use GB = 1e9 bytes, state so in the header.
   - read kernel: sum of 64-bit words (or doubles) with 8 independent accumulators so the loop vectorizes and is load-bound; accumulate into a volatile sink. write kernel: store a non-zero pattern (do NOT let gcc turn the loop into memset: compile with -fno-tree-loop-distribute-patterns and also write a value that depends on a runtime arg). copy kernel: dst[i]=src[i] plain loop (same flag; bytes counted = 2x buffer per pass: read + write).
   - Output CSV lines: kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps and a 'best' line per kernel (max aggregate over reps).
3. Makefile — CC?=gcc, CFLAGS = -O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 (do NOT use -mcpu; gcc 14 on CRB resolves -mcpu=native to empty). Targets: all, clean. Must build on both hosts.
4. run_crb.sh — the measurement plan for CRB, bash, executable, set -euo pipefail. Behaviour:
   - Refuses to start if /tmp/positron-perf.RUNNING exists, and re-checks before every phase and before each bandwidth configuration; on presence: print a message and exit 3 immediately.
   - Only CPUs 0-119. Latency pinned to --cpu 3. Bandwidth --cpus 0-119 (threads pinned starting at CPU 0 round-robin; for small thread counts that is CPUs 0..T-1).
   - Writes everything under $HOME/cache-perf/results/<UTC timestamp>/ : latency.csv, bandwidth.csv, sysinfo.txt (lscpu, cache sysfs dump, /proc/cmdline, governor, THP, uname, gcc --version, date, nproc), and log.txt. Prints the result directory at the end.
   - Latency sweep: sizes 4K 8K 16K 32K 48K 64K 96K 128K 256K 512K 1M 1.5M 2M 3M 4M 8M 16M 32M 64M 96M 128M 192M 256M 512M 1G 2G, reps 3, min-ms 300. Also run the same sweep once more under 'perf stat -x, -e l1d_cache_refill,l2d_cache_refill,l3d_cache_refill,ll_cache_miss_rd,dtlb_walk,cpu_cycles,inst_retired' if perf exists, capturing perf's CSV to latency-perf-<size>.csv per size, so refills per load can be computed later (this run uses --reps 1). If perf is absent or fails, log and continue.
   - Bandwidth sweep (each: kernel all, reps 3, min-ms 500):
       L1 regime:  bytes 32K  threads 1, 8, 32, 120
       L2 regime:  bytes 1M   threads 1, 8, 32, 120
       L3 regime:  bytes 4M   threads 1, 2, 4, 8, 16, 24, 28   (28 x 4 MiB = 112 MiB < 128 MiB L3; per-thread 4 MiB > 2 MiB L2 so L2 cannot hold it)
       DRAM regime: bytes 256M threads 1, 2, 4, 8, 16, 32, 64, 96, 120
     Print an estimate of total wall time in the script header comment (sum of configurations x kernels x reps x min-ms plus setup) and keep it under about 20 minutes.
   - Does not touch /sys, cpufreq, sysctl, or anything outside $HOME/cache-perf. Does not use sudo. Does not read feedback_ctrs or cpuinfo_cur_freq.
5. summarize.py — python3 (stdlib only): reads a results dir, prints (a) latency table: size, best ns/load, cycles at 2.8 GHz, and refills/load from the perf CSVs if present; (b) bandwidth table per regime: kernel x threads -> best aggregate GB/s and per-thread; (c) a 'levels' summary that picks the plateau values: L1 latency = best at 16K-32K, L2 = best at 256K-1M, L3 = best at 8M-64M, DRAM = best at 1G-2G; bandwidth per level = max aggregate in that regime (and per-core = 1-thread value). Prints as markdown tables. Takes the clock as --ghz (default 2.8).
6. README.md — short: what each file does, how to build on CRB, how to run, how to read the output, caveats (pointer-chase measures load-to-use latency of dependent loads with prefetch defeated; THP state; 'best' = minimum over reps; bandwidth GB = 1e9).

LOCAL SMOKE TEST (required, on this x86 host, keep it short, under 2 minutes total): make; ./latency --cpu 2 --sizes 16K,1M,64M --min-ms 100 --reps 2 ; ./bandwidth --threads 4 --cpus 0-7 --bytes 1M --kernel all --min-ms 100 --reps 1 ; ./bandwidth --threads 1 --cpus 2 --bytes 32K --kernel read --min-ms 100 --reps 1. Check that: compile has no warnings, latency grows with size (16K < 1M < 64M on this x86 host), read bandwidth at 32K on one thread is tens of GB/s or more (L1 regime), write/copy are not absurdly high (a memset/memcpy pattern-conversion or dead-code elimination would show as hundreds of GB/s on one thread for a large buffer: test 1 thread 256M read/write/copy and confirm all three are below ~40 GB/s on this x86 box). Also run summarize.py on a fake results dir produced by a short run of run_crb.sh? No: run_crb.sh is CRB-specific (CPU 0-119); instead add a --quick flag to run_crb.sh that uses tiny sizes/threads/ms so it can be smoke-tested locally with CPUS limited to 0-7 via an env var CPUS=0-7, and run it locally once to produce a results dir, then run summarize.py on it. Keep this flag simple.

CODE RULES: minimum code that solves the problem, no speculative features, clear comments only where the reason is not obvious (define imported terms like Sattolo). Match C style: 4-space indent, snake_case. Every number printed carries a unit in the header.
`

const WRITE_OUT = { type: 'object', properties: {
  files: { type: 'array', items: { type: 'string' } },
  build_output: { type: 'string' },
  smoke_results: { type: 'string', description: 'verbatim key output lines of the local smoke tests' },
  concerns: { type: 'array', items: { type: 'string' } },
}, required: ['files', 'build_output', 'smoke_results', 'concerns'] }

phase('Write')
const written = await agent(`${SPEC}\nWrite all deliverables now, build, and run the local smoke tests. Return the file list, the build output, the smoke-test output lines, and any concerns you have about validity on aarch64.`, { label: 'author', phase: 'Write', schema: WRITE_OUT })
log(`author wrote ${written?.files?.length ?? 0} files`)

phase('Review')
const FINDINGS = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    file: { type: 'string' }, line: { type: 'integer' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'note'] },
    claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' },
  }, required: ['file', 'line', 'severity', 'claim', 'evidence', 'fix'] } },
}, required: ['findings'] }
const LENSES = [
  { key: 'measurement', prompt: `Lens: MEASUREMENT VALIDITY. Will the numbers mean "best-case load-to-use latency" and "maximum sustained bandwidth" per level? Check: permutation is truly random and cyclic (no short cycles, no sequential runs the prefetcher could exploit; Sattolo correctness); loads are dependent; warm-up covers the whole cycle; timing window long enough vs clock_gettime overhead; per-thread first touch; barrier start; aggregate formula; per-thread buffers are distinct 2 MiB-aligned regions and do not false-share; the L3 regime (4 MiB/thread, up to 28 threads) really exceeds L2 and fits L3 on CRB; the DRAM regime exceeds L3 by a wide margin; the L1 regime 32 KiB stays within 64 KiB 4-way L1 (with 2 MiB alignment of every thread's buffer, do all buffers map to the same L1/L2 sets? private caches so no cross-thread conflict, but within one buffer 32 KiB contiguous is fine); the bandwidth 'read' kernel is load-bound rather than add-bound; cycles-at-2.8GHz conversion; whether reps/min are the right statistic for "best case".` },
  { key: 'compiler', prompt: `Lens: COMPILER AND MEMORY PITFALLS. Compile the code yourself in a scratch copy under /tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/review-compiler (cp -r, do not modify the original) with gcc -O3 -march=native -fno-tree-loop-distribute-patterns and inspect the assembly (gcc -S or objdump -d) of the hot loops: is the pointer chase a chain of dependent loads with nothing else? Did the read kernel vectorize and keep its loads (no dead-code elimination)? Did write/copy become memset/memcpy calls (search for 'call memset|memcpy' in the asm)? Check integer overflow in byte/size arithmetic (size_t everywhere, K/M/G parsing up to 2G and 256M x 120 threads = 30 GiB total), madvise/aligned_alloc error handling, buffer sizes that are not multiples of the unroll factor, thread count larger than CPU list, CPU list parsing ('0-119', '0,2,4-7'), sched_setaffinity on a CPU outside the allowed mask (CRB forbids 120-127; our list stays 0-119 but the error must be reported, not silently ignored), CLOCK_MONOTONIC usage, and portability gcc 11 x86 vs gcc 14 aarch64 (no x86-only intrinsics or headers).` },
  { key: 'ops', prompt: `Lens: OPERATIONS ON THE SHARED HOST. Review run_crb.sh, Makefile, summarize.py, README.md. Check: RUNNING-file check before start, before each phase, and before each bandwidth configuration (exit 3); only CPUs 0-119 ever appear; nothing touches /sys, cpufreq, sysctl, sudo, feedback_ctrs, cpuinfo_cur_freq; everything written goes under $HOME/cache-perf/results/<timestamp>; set -euo pipefail with correct handling of perf absence; total memory: 120 threads x 256 MiB x (copy needs 2 buffers) = 60 GiB plus others, state the peak and confirm it is far below 263 GiB free; total wall-time estimate is credible and under ~20 min (compute it from the loop structure: count configurations x kernels x reps x min-ms + per-config allocation/first-touch time for 30-60 GiB, which at a few GB/s of page zeroing is itself tens of seconds per DRAM configuration: add it); summarize.py handles missing perf CSVs; --quick mode and CPUS env var work and cannot accidentally be used on CRB with the wrong CPU list (the default must be 0-119, --quick must still refuse 120-127); README is in plain English with units. Run 'bash -n run_crb.sh' and 'shellcheck run_crb.sh' if shellcheck exists.` },
]
const reviews = await parallel(LENSES.map(l => () =>
  agent(`${SPEC}\nThe author has written the files in ${DIR}. Author's smoke results:\n${written?.smoke_results}\nAuthor's concerns:\n${(written?.concerns || []).join('\n')}\n\nYOUR JOB: review only, do not edit files in ${DIR}. ${l.prompt}\nReport findings with file:line, severity, claim, evidence (quote the code or the asm), and a concrete fix. Report nothing you did not verify in the code.`,
    { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }).then(r => ({ lens: l.key, ...r }))))
const allFindings = reviews.filter(Boolean).flatMap(r => r.findings.map(f => ({ lens: r.lens, ...f })))
const mustFix = allFindings.filter(f => f.severity !== 'note')
log(`review: ${allFindings.length} findings, ${mustFix.length} must/should-fix`)

phase('Fix')
const fixed = await agent(`${SPEC}\nYou are the author. Files are in ${DIR}. Apply these review findings (must-fix and should-fix). For each, either apply it or explain in one line why it is wrong (with evidence). Keep changes surgical. Then rebuild (no warnings) and rerun the full local smoke test list. Return the list of findings applied/rejected and the new smoke output.\n\nFINDINGS:\n${JSON.stringify(mustFix, null, 1)}\n\nNOTES (apply only if cheap and clearly right):\n${JSON.stringify(allFindings.filter(f => f.severity === 'note'), null, 1)}`,
  { label: 'fix', phase: 'Fix', schema: { type: 'object', properties: { applied: { type: 'array', items: { type: 'string' } }, rejected: { type: 'array', items: { type: 'string' } }, smoke_results: { type: 'string' } }, required: ['applied', 'rejected', 'smoke_results'] } })

phase('Verify')
const verify = await agent(`Independent verification. In ${DIR}: run 'make clean && make' and confirm zero warnings; run the local smoke tests from the spec below exactly; run 'CPUS=0-7 ./run_crb.sh --quick' locally (it must write under $HOME/cache-perf/results on THIS host; afterwards leave the directory in place and report its path) and then 'python3 summarize.py <that dir>'. Confirm on this x86 host: latency 16K < 1M < 64M; 1-thread 256M read/write/copy all below ~40 GB/s; no 'call memset' or 'call memcpy' in the hot loops of bandwidth.c assembly (gcc -O3 -march=native -fno-tree-loop-distribute-patterns -S). grep run_crb.sh for any CPU number >= 120 and for /sys, sysctl, sudo, cpupower, feedback_ctrs, cpuinfo_cur_freq: report each hit. Do not edit the files. Return verbatim outputs.\n\nSPEC:\n${SPEC}`,
  { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { build_ok: { type: 'boolean' }, smoke_output: { type: 'string' }, quick_run_dir: { type: 'string' }, summary_output: { type: 'string' }, asm_check: { type: 'string' }, grep_hits: { type: 'string' }, problems: { type: 'array', items: { type: 'string' } } }, required: ['build_ok', 'smoke_output', 'quick_run_dir', 'summary_output', 'asm_check', 'grep_hits', 'problems'] } })

return { written, findings: allFindings, fixed, verify }