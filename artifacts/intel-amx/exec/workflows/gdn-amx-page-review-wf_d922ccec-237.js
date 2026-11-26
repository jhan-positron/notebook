export const meta = {
  name: 'gdn-amx-page-review',
  description: 'Fact-check and plain-English review of gdn-amx-design.html: 4 lenses find problems, a skeptic per lens refutes weak findings',
  phases: [
    { title: 'Find', detail: '4 reviewers: numbers, code facts, prediction logic, plain English' },
    { title: 'Refute', detail: 'one skeptic per lens keeps only findings that hold' },
  ],
}

const DRAFT = '/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/gdn-amx-design.draft1.html'
const GEN = '/home/jhan/workspace/intel-AMX/exec/gdn-20261120'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120'
const WT = '/home/jhan/workspace/ai-runs/tron-qwen35-4b'

const CONTEXT = `
CONTEXT
- The page under review: ${DRAFT} (HTML, about 210 KB, most of it inline SVG figures). It is a design document: what GDN (GatedDeltaNet) is, a measured baseline of the model Qwen3.5 4B on the server delphi-3b35, a prediction of what three proposed changes would gain, and the software design. Read it as text: strip the <svg> bodies for the prose, but DO check the text labels inside the SVG figures (they carry numbers).
- The page is generated. Generator: ${GEN}/gen_design.py, with ${GEN}/design_numbers.py (design text and cost model), figs_data.py, figs_design.py, figs_static.py, pagelib.py, predict.py (the prediction model and its estimated factors), collect.py, analyze_trace.py.
- Data: ${RES}/collected.json (every run), ${RES}/predictions.json, ${RES}/rt-results.txt and ${RES}/rt/*.log (raw run logs, with [attn-stats] lines), ${RES}/trace/*.summary.json (GDN wall from traces), ${RES}/bench/clock-probe.txt and clock-probe2.txt (kernel benchmarks and the core clock probe), ${RES}/load/*.txt (load snapshots), ${RES}/plugin/qwen_3p5_4b.hpp (the generated model plugin).
- tron code at the commit the page describes: ${WT} (read only: no edits, no builds, no state-changing git commands).
- Design checks cited by the page: ${GEN}/design-checks/ (scripts and their saved outputs).
- Earlier reports cited: /home/jhan/workspace/intel-AMX/perf-model/index.html, /home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html, /home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/delphi-3b35-vs-3bda.html.
- You must not edit any file. You report findings only. You may write small scripts under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/be74f0ef-9ecd-4d0b-b01e-43155cd9bc79/scratchpad/review/<your-lens>/ to recompute numbers. No ssh.
RULES
- A finding needs: the exact text on the page (quote it), what is wrong, the evidence (file and line or a recomputed number), and the corrected text.
- Do not report style preferences. Report only what is wrong, unsupported, inconsistent, or breaks a stated rule.
- Severity: 'wrong' (the statement is false or the number is off), 'unsupported' (no source supports it as written), 'inconsistent' (two places of the page disagree), 'rule' (breaks a writing rule), 'minor'.
`

const FINDINGS = {
  type: 'object',
  properties: {
    checked: { type: 'string', description: 'What you checked and how many items, in 3 sentences at most' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          where: { type: 'string', description: 'section and a short quote of the page text' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'the corrected text or number' },
          severity: { type: 'string', enum: ['wrong', 'unsupported', 'inconsistent', 'rule', 'minor'] },
        },
        required: ['id', 'where', 'problem', 'evidence', 'fix', 'severity'],
      },
    },
    confirmed_ok: { type: 'array', items: { type: 'string' }, description: 'Load-bearing statements you checked and found correct (short)' },
  },
  required: ['checked', 'findings', 'confirmed_ok'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          holds: { type: 'boolean' },
          reason: { type: 'string' },
          better_fix: { type: 'string', description: 'empty if the proposed fix is right' },
        },
        required: ['id', 'holds', 'reason', 'better_fix'],
      },
    },
    missed: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'evidence', 'fix'] } },
  },
  required: ['verdicts', 'missed'],
}

const LENSES = [
  { key: 'numbers', brief: `LENS: every measured number. For sections 2, 3 and 4, the Short version, the figure labels and the tables: recompute each number from collected.json, predictions.json, the trace summaries, the bench files and the load files, and compare with the page. Check medians, ranges, run counts, shares, units, the benchmark numbers (97.9 us, 3.06 us, 6.1 us), the clock numbers (2.70, 2.40, 1.90 GHz) and the instruction costs used in design_numbers.py against clock-probe.txt and clock-probe2.txt. Check that the two arms of each cell really show 0 AMX K tokens in the raw logs. Check that every figure label equals the table value it draws. Recompute at least two cells of the prediction table by hand from the formula in predict.py.` },
  { key: 'code', brief: `LENS: every statement about the tron code and the model. Check each against ${WT} and the generated plugin: layer counts and geometry, what runs on FPGA and what on the host CPU, the state size and layout, the two passes over the state per token, the NaN check in decode, the thread split (16 GDN threads, 40 attention workers), chains and work items, the AMX gate (head 128 with 4 query heads per KV head), the FPGA attention gate (64 or 128), what the attention statistics see, the tile counts of the existing 128-wide kernels (16 QK + 16 PV), the tests named in section 5.4 (tolerance 1e-7, bit-pinned words, equal-bytes checks), and every file name, function name and line range in the Sources list (section 7) and in the code structure table (section 5.6). Also check the design claims in section 5.2 (each value column is its own recurrence; a 64-column half is 32 KiB) against the kernel source and against the scripts in design-checks/skeptic/.` },
  { key: 'logic', brief: `LENS: the prediction and the design reasoning. Check: (1) the prediction formula on the page equals what predict.py computes; (2) each estimated factor in the table of section 4 follows from the basis text next to it (redo the arithmetic: step times, cycles, clocks); (3) the claim that a time saved in GDN or in attention shortens the pass by the same amount: look for evidence in the code or data for or against it (are GDN and FPGA work serial inside a layer? is attention on the critical path?); (4) the cost model of the block kernel in design_numbers.py (tile counts per block from the tile shapes, loads, stores, the split cost) and whether figure 12's counts match it; compare with the three independent cost models in design-checks/ (kernel/04_cost_model.out, skeptic/cost_model.out, integration/cost_arith.py) and report disagreements above 30 %; (5) whether the numerics statements of section 5.4 match the saved outputs in design-checks/proto/gdn_block_proto.out and design-checks/skeptic/numerics_check.out; (6) internal consistency: the same quantity must have the same value everywhere on the page (Short version, figure captions, tables, lists); (7) claims that go beyond the evidence, such as a prediction stated without 'est.'.` },
  { key: 'english', brief: `LENS: the writing rules the author must follow. Rules: (R1) no idioms, metaphors, wordplay or uncommon words; (R2) one claim per sentence; (R3) short sentences, no semicolons; (R4) bullets or blank lines to separate points; (R5) references as [RefN] after the sentence, never replacing it; (R6) every number has a unit and, where needed, a plain meaning; estimates are marked 'est.'; (R7) the page starts with a 'Short version' of at most three sentences that a newcomer can follow; (R8) every term (code name, acronym, metric, machine name) is defined at first use or in the 'Words used here' list. Also banned words: convoy, refund, 'in disguise', swept/sweep. Also the project rule: write 'prompt 1,024' or 'prompt length', never 'ctx'. Report each violation with the exact phrase and a corrected version. Check the text inside figures too. Check that the Words list covers every term used (for example: tile row, working copy, slice, clock, flat-frequency service, TSX, FMA, zmm or 512-bit, cache names, 'work item', 'head', 'K token', 'page unit'). Do not report sentences that are fine.` },
]

const out = await pipeline(
  LENSES,
  l => agent(`${CONTEXT}\n${l.brief}`, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (found, l) => {
    if (!found || !found.findings.length) return { lens: l.key, found, verdicts: null }
    return agent(`${CONTEXT}\nYOU ARE THE SKEPTIC for the lens below. Another reviewer listed findings against the page. For each finding decide whether it HOLDS: open the page, find the quoted text, open the evidence, recompute. A finding that misquotes the page, misreads the data, or asks for a style change does not hold. If the finding holds but its fix is wrong, give the better fix. Then list problems the reviewer missed (same lens).\n\nLENS:\n${l.brief}\n\nFINDINGS (JSON):\n${JSON.stringify(found.findings)}`, { label: `refute:${l.key}`, phase: 'Refute', schema: VERDICTS })
      .then(v => ({ lens: l.key, found, verdicts: v }))
  }
)
return out.filter(Boolean)
