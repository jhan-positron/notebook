export const meta = {
  name: 'perf-measurement-techniques',
  description: 'Distill cache/DRAM perf measurement techniques from bandwidth.c and run_sudo.sh, verify each against source, find gaps',
  phases: [
    { title: 'Analyze', detail: 'five lenses over the two source files' },
    { title: 'Verify', detail: 'adversarial check of every finding against the code' },
    { title: 'Critic', detail: 'what techniques are missing' },
    { title: 'Round 2', detail: 'fill the gaps and verify them' },
  ],
}

const BENCH = '/home/jhan/workspace/titan/cache-perf/bench'
const CRB = '/home/jhan/workspace/titan/cache-perf/crb'
const SOURCES = `Primary sources (read both in full, with line numbers, e.g. cat -n):
- ${BENCH}/bandwidth.c (463 lines)
- ${BENCH}/run_sudo.sh (180 lines)
Supporting context (read as needed):
- ${BENCH}/README.md (explains the plan, output format, caveats)
- ${BENCH}/Makefile (compiler flags)
- ${CRB}/results/20261030T193108Z/sysinfo.txt (CRB machine: 128 Neoverse V3AE cores at 2.8 GHz, L1d 64 KiB 4-way, L2 2 MiB 8-way private, L3 "128 MiB" = mesh cache (SLC) of 128 x 1 MiB slices, THP always, performance governor, CPUs 0-119 usable)
- ${CRB}/results/cmn-map.txt (the CMN S3 mesh map: 9x8 crosspoints, HN-S home nodes with SLC slices, RN-F core ports, SN-F memory, CCG chip-to-chip gateways)
- ${CRB}/crb-memory-hierarchy-brief.html (results brief; strip tags with sed to read: latency per level, per-core and whole-chip bandwidth, pair-port finding, slice distance, proxy for other mesh, write bypass of mesh cache, cross-mesh write collapse)
- ${CRB}/crb-memory-hierarchy.html (full report with methods, 104 KB; grep for what you need)`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          technique: { type: 'string', description: 'short name of the technique, e.g. "per-thread first-touched buffers"' },
          what: { type: 'string', description: '1-3 plain sentences: what the code does' },
          why: { type: 'string', description: '1-3 plain sentences: which measurement error or bound it addresses' },
          file: { type: 'string', description: 'bandwidth.c or run_sudo.sh (or README.md / Makefile)' },
          lines: { type: 'string', description: 'line range in that file, e.g. "288-327"' },
          snippet: { type: 'string', description: 'VERBATIM code copied from the file (trim to the essential 2-15 lines; you may elide inner lines with a line containing only "..." )' },
          pitfall: { type: 'string', description: 'what goes wrong if a reader omits this (concrete symptom)' },
          generalize: { type: 'string', description: 'how an engineer implements the same technique on another machine (x86 or other arm); 1-3 sentences' },
          bound: { type: 'string', description: 'which hardware bound this measurement isolates or hits: L1 pipes, L2, mesh slice, crosspoint port, DRAM channel, chip-to-chip link, none' },
        },
        required: ['technique', 'what', 'why', 'file', 'lines', 'snippet', 'pitfall', 'generalize', 'bound'],
      },
    },
    notes: { type: 'string', description: 'anything important that did not fit a finding' },
  },
  required: ['findings', 'notes'],
}

const ARCH_SCHEMA = {
  type: 'object',
  properties: {
    levels: {
      type: 'array',
      description: 'one entry per level of the data path from core to DRAM, in order',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          size_or_count: { type: 'string', description: 'e.g. "64 KiB per core, 4-way" or "128 slices x 1 MiB"' },
          shared_by: { type: 'string', description: 'private per core / per crosspoint port pair / whole mesh / whole chip' },
          measured_latency: { type: 'string', description: 'from the brief, with units and source' },
          measured_bw_1core: { type: 'string' },
          measured_bw_chip: { type: 'string' },
          bound_description: { type: 'string', description: 'what physically limits throughput here (load/store pipes, L2 fill bw, port width, slice count, channel count...) and which bench config exposes it' },
          bench_config: { type: 'string', description: 'exact bandwidth args / run_sudo part that targets this level' },
        },
        required: ['name', 'size_or_count', 'shared_by', 'measured_latency', 'measured_bw_1core', 'measured_bw_chip', 'bound_description', 'bench_config'],
      },
    },
    topology_facts: { type: 'array', items: { type: 'string' }, description: 'plain facts about the mesh: two meshes, CPU ranges, pair ports, home nodes, proxies, interleave, CCG, SN-F count, each with its source file' },
    data_path_story: { type: 'string', description: 'a 5-10 sentence plain-English walk of one streaming read and one streaming write from a core to DRAM, naming each hop' },
    open_or_uncertain: { type: 'array', items: { type: 'string' } },
  },
  required: ['levels', 'topology_facts', 'data_path_story', 'open_or_uncertain'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    snippet_verbatim: { type: 'boolean', description: 'true only if the snippet text matches the file exactly (modulo leading whitespace and "..." elisions) at the stated lines' },
    claim_correct: { type: 'boolean', description: 'true only if what/why/pitfall are supported by the code or the cited context files' },
    refuted: { type: 'boolean', description: 'true if either check fails or you are uncertain' },
    correction: { type: 'string', description: 'if refuted: the corrected lines, snippet, or claim; else empty' },
    corrected_lines: { type: 'string', description: 'the right line range if the stated one was wrong, else empty' },
  },
  required: ['snippet_verbatim', 'claim_correct', 'refuted', 'correction', 'corrected_lines'],
}

const LENSES = [
  { key: 'sizing', prompt: `Lens: DATA-SET SIZING and CACHE-REGIME SELECTION. Extract every technique about choosing buffer sizes and shapes so that a measurement lands in one cache level and avoids/causes hits or misses: per-thread private buffers, size per regime (32K/1M/8M/1G/256M, why 14 threads x 8 MiB), copy using two buffers, 2 MiB alignment and THP/MADV, first-touch by the owning thread, warm-up pass, the CHECK_BYTES clock cadence, --min-ms and reps/best, how run_sudo picks 8M vs 1G vs 256M for part 3/4/5 and why. Also sizes that deliberately cause misses (1G per thread) and what a core "sees" of the mesh cache (64 MiB of 128 MiB, from the brief).` },
  { key: 'kernels', prompt: `Lens: LOAD/STORE INSTRUCTION CHOICE and KERNEL DESIGN. Extract every technique about the hot loops: the C read kernel with 16 accumulators and why (latency hiding vs load-bound), noinline, -fno-tree-loop-distribute-patterns and -O3 -march=native in the Makefile, the runtime store value v and v+p (why not memset-foldable, why non-byte-repeating), the volatile sink per thread, the asm kernels (ldp/stp q registers, 256 B per iteration, loop overhead of add/cmp/b.lo, dup v0, memory and cc clobbers, callee-saved v8-v15 outside the loop, bytes multiple of 256), what each kernel's bound is (load pipes vs store pipes vs L2 fill), copy counting read+write bytes, the write-streaming-mode caveat in README and how to detect it with perf. State the per-cycle byte rates implied (e.g. 24 B/cycle for the compiler loop from README, and what 133 GB/s at 2.8 GHz means in B/cycle).` },
  { key: 'placement', prompt: `Lens: THREAD, CORE, MESH PLACEMENT and TIMING/AGGREGATION. Extract every technique about where threads run and how results are aggregated: pin_cpu via sched_setaffinity, --cpus list syntax incl. stride "0-118:2" and what stride 2 selects (one core per crosspoint port pair, cores 2k and 2k+1 share a port), i % ncpus assignment, the barrier protocol (threads+1 parties, warm-up before barrier, two barriers per rep), aggregate = sum bytes / max elapsed vs per-thread min/max/avg, --per-thread lines, taskset -c 0-119 re-exec, which CPU sets run_sudo uses (0-63 one mesh, 0-31,64-95 both meshes, 2+3 partners vs 2+4 two ports, 2,4,6,8 four ports, single core 2, core 3 for homelat) and what each placement is designed to separate (port bound, slice bound, mesh bound, DRAM bound, chip-to-chip). Include the cross-mesh write collapse numbers from the brief as the motivating observation.` },
  { key: 'counters', prompt: `Lens: HARDWARE COUNTER METHODOLOGY in run_sudo.sh. Extract every technique: why root (perf_event_paranoid), perf stat -a vs -C 2 (system-wide uncore vs one core's PMU), the short (0.2 s) / long (2 s) difference quotient and what it cancels (buffer setup, first touch, warm-up, process start), idle background control runs subtracted, distinct event ids per run to avoid multiplexing (the 50 % observation), opening each event on both meshes arm_cmn_0 and arm_cmn_1, the SETS choice (what each hns_* event measures: pocq reqs write/read, cache fill, cache miss, mc reqs local/remote, slc_sf access, sf hit, eviction, hbt; and SETS4: retry, rnf, ccgrn, throttle), per-crosspoint events with bynodeid=1,nodeid=0x98 and how the node id is computed (x<<7 | y<<3), the four counters per crosspoint and six per core limit, sysfs existence check before measuring, the raw architectural core event ids 0x41/0x43/0x51/0x53/0x61/0x67, the CSV layout (-x,) and how counts become per-line rates (bytes/64). Also the operational safety: guard() with setsid process group, marker polling, trap chown, tee log, make before run.` },
]

phase('Analyze')
log('Analyze: architecture lens + 4 technique lenses')

const archTask = agent(`You are documenting the memory hierarchy and data paths of the CRB machine so an experienced engineer can understand what each benchmark configuration measures. Produce a top-down architecture map: core -> L1 -> L2 -> crosspoint port -> mesh (home node / SLC slice, two meshes, proxies for lines homed on the other mesh) -> memory controller / DRAM channels, plus the chip-to-chip gateway (CCG). For every level give the measured numbers from the brief (with units) and the exact benchmark configuration in bandwidth.c args or run_sudo.sh part that isolates it. Describe the physical bound at each level. Every fact must come from the files; label anything inferred as "inferred" in open_or_uncertain. Use plain English, define every acronym at first use (SLC, HN-S, RN-F, SN-F, CCG, XP, CMN, THP, PMU).
${SOURCES}`, { label: 'lens:architecture', phase: 'Analyze', schema: ARCH_SCHEMA })

const lensResults = await pipeline(
  LENSES,
  l => agent(`You are extracting the measurement techniques an experienced software engineer would need to re-implement a cache/DRAM bandwidth benchmark by hand. ${l.prompt}
Rules: every finding must cite the file and exact line range and quote the code VERBATIM (copy from cat -n output, strip the line-number prefix). Keep 6 to 14 findings, each distinct. Plain English, one claim per sentence, numbers with units. Do not invent behaviour the code does not have. If the README or brief states a number (e.g. 24 B/cycle, 73 GB/s, 394 vs 173 GB/s), you may use it and say it comes from there.
${SOURCES}`, { label: `lens:${l.key}`, phase: 'Analyze', schema: FINDINGS_SCHEMA }),
  (res, l) => {
    if (!res) return null
    const fs = res.findings
    log(`verify ${fs.length} findings from lens ${l.key}`)
    return parallel(fs.map(f => () =>
      agent(`Adversarially verify ONE finding against the source. Default to refuted=true if you cannot confirm both checks.
Finding: ${JSON.stringify(f, null, 1)}
Check 1: open ${BENCH}/${f.file} with cat -n and confirm the snippet appears VERBATIM at (or near) lines ${f.lines}; whitespace differences and "..." elisions are fine, any changed token is not. If the lines are off but the snippet exists, give corrected_lines and do not refute on that alone.
Check 2: confirm "what", "why", "pitfall", "bound" and "generalize" are consistent with the code and the context files (README.md, Makefile, the brief). A claim that the code does X when it does Y is refuted. A hardware claim that contradicts the brief or sysinfo is refuted. A general engineering claim (e.g. "memset may be folded by the compiler") is fine if it is standard knowledge.
${SOURCES}`, { label: `verify:${l.key}:${f.technique.slice(0, 30)}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' })
        .then(v => ({ lens: l.key, finding: f, verdict: v }))
    )).then(vs => ({ lens: l.key, notes: res.notes, verified: vs.filter(Boolean) }))
  }
)

const arch = await archTask
const lenses = lensResults.filter(Boolean)
const kept = lenses.flatMap(l => l.verified.filter(v => v.verdict && !v.verdict.refuted).map(v => ({ ...v.finding, lens: l.lens, corrected_lines: v.verdict.corrected_lines })))
const dropped = lenses.flatMap(l => l.verified.filter(v => !v.verdict || v.verdict.refuted).map(v => ({ lens: l.lens, technique: v.finding.technique, correction: v.verdict ? v.verdict.correction : 'no verdict' })))
log(`kept ${kept.length} findings, dropped ${dropped.length}`)

phase('Critic')
const critic = await agent(`You are the completeness critic. Below is the list of measurement techniques already extracted (name + file + lines) from bandwidth.c and run_sudo.sh. Read BOTH files in full with cat -n and list every technique, guard, or design decision in the code that is NOT covered yet and that a reader implementing a cache/DRAM perf benchmark manually should know. Think about: sizing, instruction choice, cache hit/miss control, core/mesh/DRAM placement, timing and aggregation, counter methodology, operational safety on a shared host, output format choices that enable later analysis (best line, per-thread lines, CSV with -- headers). Also list any technique that is covered but whose explanation in the list is wrong or too thin. Return findings in the same schema; each must quote verbatim code with lines.
Already covered:
${kept.map(k => `- [${k.lens}] ${k.technique} (${k.file}:${k.lines})`).join('\n')}
Dropped as unverifiable (do not re-add unless you can quote the code precisely): ${dropped.map(d => d.technique).join('; ') || 'none'}
${SOURCES}`, { label: 'critic:completeness', phase: 'Critic', schema: FINDINGS_SCHEMA, effort: 'high' })

phase('Round 2')
let round2 = []
if (critic && critic.findings.length) {
  log(`critic found ${critic.findings.length} gaps; verifying`)
  const vs = await parallel(critic.findings.map(f => () =>
    agent(`Adversarially verify ONE finding against the source. Default to refuted=true if you cannot confirm both checks.
Finding: ${JSON.stringify(f, null, 1)}
Check 1: open ${BENCH}/${f.file} with cat -n and confirm the snippet appears VERBATIM at (or near) lines ${f.lines}; whitespace and "..." elisions are fine. If the lines are off but the snippet exists, give corrected_lines and do not refute on that alone.
Check 2: confirm what/why/pitfall/bound/generalize are consistent with the code and context files.
${SOURCES}`, { label: `verify2:${f.technique.slice(0, 30)}`, phase: 'Round 2', schema: VERDICT_SCHEMA, effort: 'high' })
      .then(v => ({ finding: f, verdict: v }))))
  round2 = vs.filter(Boolean)
}
const kept2 = round2.filter(v => v.verdict && !v.verdict.refuted).map(v => ({ ...v.finding, lens: 'critic', corrected_lines: v.verdict.corrected_lines }))
const dropped2 = round2.filter(v => !v.verdict || v.verdict.refuted).map(v => ({ lens: 'critic', technique: v.finding.technique, correction: v.verdict ? v.verdict.correction : 'no verdict' }))
log(`round 2 kept ${kept2.length}, dropped ${dropped2.length}`)

return {
  architecture: arch,
  findings: [...kept, ...kept2],
  dropped: [...dropped, ...dropped2],
  lens_notes: lenses.map(l => ({ lens: l.lens, notes: l.notes })),
  critic_notes: critic ? critic.notes : '',
}