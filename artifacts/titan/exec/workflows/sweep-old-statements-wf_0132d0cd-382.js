export const meta = {
  name: 'sweep-old-statements',
  description: 'Find every place in the CRB report and brief that repeats or depends on the statements that P1 to P3 and the new Spec box replace',
  phases: [{ title: 'Sweep', detail: 'four readers, three by line range and one by search pattern' }],
}

const REPORT = '/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html'
const RECORD = '/home/jhan/tmp/update-crb-memory-hierarchy.md'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/apply_p/agents'

const COMMON = `
You are a read-only checker. Do NOT edit any file under /home/jhan/workspace or /home/jhan/tmp. Do not log in to any other machine and do not use the network. If you need scratch files, write them only under ${SCRATCH}/<your label>/ (create it).

Context. The report ${REPORT} (HTML, 978 physical lines, many lines are several thousand characters long) describes memory-hierarchy measurements on a server called CRB. The author decided today to replace three older statements and one figure label. Your job is to find every OTHER place that still states, repeats or relies on the old statements, so that the report does not contradict itself after the change.

How to read the report: the Read tool may cut long lines. Print full lines with:
python3 -B -c "import sys;L=open('${REPORT}',encoding='utf-8').read().split('\\n');a,b=int(sys.argv[1]),int(sys.argv[2]);[print('L%d: %s'%(n,L[n-1])) for n in range(a,b+1)]" 200 216

The decided changes (the new texts P1, P2, P3 are in ${RECORD}, section 10.6, lines 624 to 650 — read them first, in full):
- C1 (old, withdrawn): "For DRAM traffic / DRAM streams the pair port is not the limit, because DRAM latency limits each core first (2 threads at 1 GiB get 53 GB/s paired or not)". New (P1): at 1 GiB a second partner reader adds 86 to 87 %, a second partner asm writer adds 0.3 % (63.0 -> 63.2 GB/s), four writers on two pairs write 113 GB/s; what the shared limit is was not measured.
- C2 (old): "The pair port is a 78 GB/s (or about 80 GB/s) limit per two cores" stated as a fact about the port. New (P2): two partner threads read 77.5 to 78.5 GB/s together at 8 MiB; the rate counts bytes at the loops, including lines from the cores' own L2; what limits the pair was not measured; that the full port is the limit is hypothesis 2; hypothesis 1 says the port passes at most 64 GB/s in each direction.
- C3 (old): "The single-writer limit (71 to 73 GB/s) is inside the core", and "the same port/path carries 82 GB/s with the partner and 229 GB/s with four writers". New (P3): what limits one writer at 8 MiB was not measured; four writers ran on four ports.
- C4 (old): "two cores of different pairs read 134 GB/s (two times the single-core value)". New: 125 to 134 GB/s (125 to 132 GB/s on one mesh, 134 GB/s only for two cores on different meshes).
- C5 (old): the Spec box of the pair port in the first figure says "unknown" (report lines 92, 97, 118, 416; aria-label line 77 says "for core and DRAM only"). New: the box will say "estimated 64 GB/s" (32 B per data flit x 2.0 GHz mesh clock, one data flit per mesh cycle in each direction, hypothesis 1).
- C6 (old): "about 28 B per core cycle (est. from 78 GB/s at 2.8 GHz)". Dropped.
- C7: "1.8 x 10^9 flits per second" (line 278) against 1.85 x 10^9 in the new text.
- C8: the caption of the pair chart (line 379) says "asm read"; the data are from the read loop compiled from C.
The author will rewrite report lines 92, 97, 110, 118, 213, 214, 278, 289, 343, 377, 379, 380, 416, 437 and the brief. You look for everything ELSE, and you also report other defects inside those listed lines that the planned change (as described above and in section 10.6 and rows F2, F3, F15, F31, F32, F33 of section 6 of the record) would leave in place.

For every place return: the line number, the exact quoted sentence or label (copy it from the file, do not paraphrase), which of C1..C8 it conflicts with or depends on, how serious it is ("contradiction" = the sentence states the old claim as fact; "dependent" = it relies on the old claim as a premise or repeats an old number; "wording" = harmless but would read oddly next to the new text; "none-but-checked" is NOT to be returned), and a proposed minimal replacement text in plain English (short sentences, one claim per sentence, numbers with units, estimates marked "est.", no semicolons). A replacement must not introduce a number that you did not verify in the raw result files under /home/jhan/workspace/titan/cache-perf/crb/results/ (name the file and line when you add a number). Do not report places that are correct. Do not invent findings. If a range holds nothing, return an empty list.
`

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          quote: { type: 'string' },
          conflicts_with: { type: 'string' },
          severity: { type: 'string', enum: ['contradiction', 'dependent', 'wording'] },
          why: { type: 'string' },
          proposed_text: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['file', 'line', 'quote', 'conflicts_with', 'severity', 'why', 'proposed_text'],
      },
    },
    lines_read: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['findings', 'lines_read'],
}

const TASKS = [
  { label: 'range-047-216', prompt: `Your range: report lines 47 to 216 (header, short version, contents, first figure with its caption and source table, the pipeline section, cache ways, and the section "The SLC (L3) and the pair port"). Read every line of the range in full, including SVG text labels and the aria-label.` },
  { label: 'range-217-381', prompt: `Your range: report lines 217 to 381 (latency sections, "Bandwidth per core" with the part-5 table, "Bandwidth of the whole chip", "Who reads, who provides", "DRAM bandwidth against thread count", "The pair finding"). Read every line of the range in full, including figure captions.` },
  { label: 'range-382-978', prompt: `Your range: report lines 382 to 978 ("Record" tables, "Method and caveats", "Open items", "Words used here", "When the runs happened", and the two script blocks that draw the figures: read every text string that the scripts draw, for example chart labels, panel titles and the 'lines' arrays of the data-path panels). Read every line of the range in full.` },
  { label: 'pattern-and-brief', prompt: `Your job is a search by pattern, not by range. (1) In the whole report, search for these patterns and judge every hit in its sentence: "78", "~80", "80 GB/s", "134", "53 GB/s", "paired or not", "not the limit", "inside the core", "outside the core", "limit" within 120 characters of "pair" or "port", "share one", "shares one", "the same port", "the same path", "229", "82 GB/s", "28 B", "unknown", "Spec row", "no number", "per 2 cores", "per pair", "one path to the mesh", "ceiling", "caps", "bottleneck". (2) Read the whole brief /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy-brief.html (504 lines; the text is in lines 1 to 60, the rest is figure markup: still read every text label) and its generator /home/jhan/workspace/titan/cache-perf/crb/make-brief.py (228 lines). The brief is generated: a change must be made in the generator's template. The brief prints on exactly 2 A4 pages and must stay at 2 pages, so a replacement for the brief must be about as long as the text it replaces. The record's section 10.6 proposes texts for generator lines 180 and 181: judge them too (correct numbers, undefined terms such as "flit" or "credit-stall" in a brief without a word list, length), and propose a shorter version of each that keeps the measured facts and names the hypothesis as not tested. (3) List, without proposed text, the other files in /home/jhan/workspace/titan/cache-perf/crb/ (not under results/, refs/ or tmp/) and in /home/jhan/workspace/titan/cache-perf/bench/ that repeat C1, C2, C3 or C4: file, line, quote. Use severity "dependent" for these and put "other file, list only" in proposed_text.` },
]

phase('Sweep')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + '\n' + t.prompt + `\nYour label: ${t.label}.`, { label: `sweep:${t.label}`, phase: 'Sweep', schema: SCHEMA })
    .then(r => ({ label: t.label, result: r }))
))
return results.filter(Boolean)
