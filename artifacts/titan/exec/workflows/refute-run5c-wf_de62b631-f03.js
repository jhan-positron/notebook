export const meta = {
  name: 'refute-run5c',
  description: 'Three independent refuters check the run 5c change (asm, script, plan arithmetic)',
  phases: [{ title: 'Refute' }],
}
const DIFF = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/run5c.diff'
const SEC = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/run5c-section12.md'
const SRC = '/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c'
const SH = '/home/jhan/workspace/titan/cache-perf/asimov/run_followup.sh'
const SAMPLE = '/home/jhan/workspace/ai-runs/run5c-crb-sample'
const SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, severity: { type: 'string', enum: ['blocker','should-fix','nit','refuted'] },
    evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['title','severity','evidence','fix'] } },
  summary: { type: 'string' } }, required: ['findings','summary'] }
const common = `You are a skeptical reviewer. Read-only: do not edit any file. Try to REFUTE the change; report only findings you can back with a quoted line or a computed number. For each finding give severity blocker / should-fix / nit, the evidence, and the smallest fix. If you looked for a problem and found none, say so in the summary. Files: the commit diff ${DIFF}; the full current bandwidth.c ${SRC}; run_followup.sh ${SH}; the plan section ${SEC}; CRB sample output files in ${SAMPLE} (bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv; the CRB is a Neoverse V3AE at 2.8 GHz with three 128-bit load pipes, not the target C1-Nano).`
phase('Refute')
const lenses = [
  { key: 'asm', prompt: `${common}\nLens: the AArch64 inline assembly of k_read_n and k_write_n and their call path (pass_asm, worker, option validation). Check operand constraints (early-clobber, read-write, inputs that must not share a register with outputs), the loop labels (1:/2: with b.lo 2b and b.ne 1b inside one asm statement), the clobber lists, the pointer reset per pass, the passes count down with subs, behaviour when passes is 1, bytes a multiple of 256, the nseg != 1 exit, the host stand-ins, and whether the default form or any other kernel changed behaviour. Compare with the existing k_read, k_read_2s and k_write in the same file, including the early-clobber comment on k_read_2s.` },
  { key: 'script', prompt: `${common}\nLens: the G8 rows in run_followup.sh and their output. Check the command lines against the plan section (sizes, passes, reps, --perf, --asm-passes, file names), the --quick behaviour, where the section sits relative to cpu_set_online and the dry-run exit, the use of $BW (the current binary) rather than $BW2/$BW3, and whether the sample CSV files in ${SAMPLE} match the layout the plan section and the header describe (count the rows, check the header field asm_passes, check that the best rows print '-' in the counter columns). Also compute from the sample files: per size, elapsed_s / passes for the per-pass form and the asm form, and a least-squares line of time per pass against bytes for the best rep of each size in the per-pass file; report the intercept in ns and the slope as GB/s, and say whether the plan's reading rules (residual under 2 % of the smallest pass time; l1d_refill_per_line below 0.01) hold on the CRB sample.` },
  { key: 'plan', prompt: `${common}\nLens: the arithmetic and claims of the plan section. Recompute: 16 KiB at 58.127 GB/s -> ns per pass and cycles at 2.0 GHz; 512 cycles ideal at 32 B/cycle; the V3AE 32 KiB pass at 132.67 GB/s and 48 B/cycle at 2.8 GHz; the 0.24 s est. for 16 launches at 14 ms; '138 commands'. Check that every number has a unit and that estimates are labelled est. Check the plain-English rules: terms defined at first use, one claim per sentence, no idioms. Check that the success criterion is falsifiable and that the 'what stays open' paragraph does not overclaim. Flag any claim about the C1-Nano that the section states as fact without a source.` },
]
const results = await parallel(lenses.map(l => () => agent(l.prompt, { label: `refute:${l.key}`, schema: SCHEMA })))
return results.map((r, i) => ({ lens: lenses[i].key, ...(r || { findings: [], summary: 'agent returned null' }) }))