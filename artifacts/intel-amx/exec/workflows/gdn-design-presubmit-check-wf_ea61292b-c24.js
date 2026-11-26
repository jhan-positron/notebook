export const meta = {
  name: 'gdn-design-presubmit-check',
  description: 'Check the GDN x AMX design page against its data, scripts and code before it goes to the reviewer (read-only)',
  phases: [
    { title: 'Check', detail: 'one checker per dimension: baseline numbers, prediction numbers, design numbers, code and source claims, presentation' },
    { title: 'Verify', detail: 'one skeptic per dimension tries to refute each finding' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'

const COMMON = [
  'You are checking a design page before it is handed to an external reviewer. Your job is to find statements on the page that its own evidence contradicts or does not support. You do not edit anything.',
  '',
  'The page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html (HTML, 234,822 bytes, 13 inline SVG figures, 11 tables). Title: "GDN and AMX: design for Qwen3.5 4B". It reports a measured baseline of the Qwen3.5 4B model in tron (an inference program) on the server delphi-3b35, a prediction of what three proposed changes (Part 0, Part A, Part B) would do to the time to first token and to the decode speed, and a software design. Nothing is built yet.',
  'A plain-text extraction of the page is at ' + SP + '/page-text.txt (521 lines; each figure appears as [SVG: ...] and [SVG-TEXT: ...] lines that hold the text labels of the figure). Read all of it first. Use the HTML when you need exact markup or figure geometry.',
  '',
  'Where the evidence lives (all under /home/jhan/workspace/intel-AMX unless noted):',
  '- exec/gdn-20261120/ : scripts. gen_design.py (generates the page), design_numbers.py (numbers and text blocks of the design sections), figs_data.py, figs_design.py, figs_static.py, pagelib.py (figures), predict.py (the prediction; writes predictions.json), collect.py (parses the run logs; writes collected.json), analyze_trace.py (trace summaries), campaign.sh, run-one.sh, trace.sh.',
  '- exec/results/gdn-20261120/ : results. rt-results.txt, rt/*.log (run logs), collected.json (2.7 MB: do not print it whole; load it with python and index into it), predictions.json, trace/*.summary.json, bench/*.txt (kernel benchmarks and clock probes), load/ (load snapshots), attn-busy-vs-t3.json, plugin/qwen_3p5_4b.hpp.',
  '- exec/gdn-20261120/design-checks/ : check scripts with saved outputs (*.out, *.json) in the folders kernel, proto, skeptic, integration, lead, verify-math, verify-cost, verify-fit, review.',
  '- /home/jhan/workspace/ai-runs/tron-qwen35-4b : read-only copy of the tron source at commit 72e1191804 (the commit that the page names).',
  '- Section 7 "Sources" of the page lists 20 references. In the page body they appear as [Ref1] to [Ref20], numbered in list order.',
  '',
  'Hard rules:',
  '- Read-only. Do not modify, create or delete any file under /home/jhan/workspace. Do not run gen_design.py, predict.py, collect.py or analyze_trace.py as programs, because they overwrite result files. To reuse their logic, copy the script into your scratch folder and change its output path there, or import single functions.',
  '- Do not ssh to any machine. Do not use the network. Everything you need is on the local disk.',
  '- Scratch files go only under ' + SP + '/presubmit/<your dimension key>/ (create the folder).',
  '- Set PYTHONDONTWRITEBYTECODE=1 when you run python.',
  '',
  'What counts as a finding:',
  '- A number, name, line reference or statement on the page that the evidence contradicts.',
  '- A statement that the page presents as measured or as read from code, for which you find no supporting evidence in the places above (say where you looked).',
  '- Two places of the page that contradict each other.',
  '- A rounding difference is a finding only when the page value is not a correct rounding of the source value to the digits shown.',
  'What does not count: wording preferences, requests for more experiments, design opinions.',
  '',
  'For each finding give: the place on the page (section, table row or figure number), a short exact quote, what is wrong, the evidence (file path and line, or the command you ran and the value you got), and the smallest correction. Severity: "wrong" (the page states something false), "unsupported" (no evidence found), "inconsistent" (the page contradicts itself), "minor" (cosmetic, a typo, a line reference that is off by a few lines).',
  'Also report what you checked: the number of distinct claims you checked, the number that held, a short description of the coverage, and the areas you could not check and why. Do not pad. Zero findings is a valid result.',
  '',
].join('\n')

const DIMENSIONS = [
  {
    key: 'baseline',
    prompt: 'Your dimension: BASELINE NUMBERS (key: baseline). Scope: page sections 2 and 3, figures 4 to 8 with their tables, and the bullets under "What the numbers say". Re-derive the values from the raw data, not from the page generator: TTFT and decode medians and ranges per cell (rt-results.txt, rt/*.log, collected.json), the prefill rates, the "Runs" counts, the comparison of the two AMX arms (-0.6 to +1.1 %), the claim "AMX scored 0 K tokens in all 36 runs", the load snapshot values (at most 0.2 % busy, 43.1 to 43.2 % busy), the split of a prefill pass (pass wall, GDN wall, attention busy time, rest, attention wait), the split of a decode step, the traced-against-untraced percentages (3 to 28 %, 0.2 to 3.1 %), the GDN step times per thread (6.3 to 6.5 us, 3.8 to 4.0 us, mean 6.1 us, 13 to 16 us in decode), 0.85 ms per layer and 6.6 us per token, the ratios 7.5 to 7.6, 7.9, and 5.2 to 6.8, the decode falls of 16 % and 54 %, the clock probe values (2.70, 2.40, 1.90, 4.00 GHz; 26 of 29 CPUs; CPUs 108, 109, 126; the turn lengths 34 ns and 25 us), the benchmark values 3.06 us and 0.50 us, and every value in figure 8. Check that the labels of each figure agree with its table. Read how collect.py and analyze_trace.py define each quantity, and check that the page describes that definition correctly (for example: what "GDN wall" is, what the attention busy time is divided by, which runs are traced, which user the TTFT belongs to).',
  },
  {
    key: 'prediction',
    prompt: 'Your dimension: PREDICTION NUMBERS (key: prediction). Scope: the table in the "Short version", all of section 4 (the method formulas, the factor table with its "Basis" bullets, the clock note, figures 9 and 10, the per-cell table, "How to read the prediction", "What would prove the prediction wrong", the block "Seen in the same data"), and the copies of these numbers in sections 5.1, 5.2 and 5.7. Recompute the prediction yourself from the formulas printed on the page and the measured inputs in collected.json (pass wall, GDN wall, attention busy time, number of passes, TTFT, decode speed), for all 6 cells, for Part 0, Part A, Part B and Parts A and B, at the low, working and high factors. Compare with predictions.json and with every number on the page (seconds, percentages, ranges). Check every arithmetic statement in the Basis bullets (for example 3.15 x 0.76, 3.3 x 0.96, 1.18 x 0.76, 1.22 x 0.96, 0.21 x (2.70 / 2.40 - 1), the GDN step times and factors at 2.40 and 1.90 GHz that follow from the cycle counts, "Part 0 gives about 83 % of the fall", "3 to 5 points more", "1.0 to 1.6 points worse", "about 3/8", "about 100 ms of the 362 ms", "at most 1.8 ms of the 8.1 ms"). Check that predict.py implements the formulas that the page prints, including how the low and the high case combine the factors and where the clock cost is applied. Check that the summary ranges in the Short version table, in the "How to read" bullets and in the per-cell table agree with each other and with figures 9 and 10.',
  },
  {
    key: 'design',
    prompt: 'Your dimension: DESIGN NUMBERS (key: design). Scope: sections 5.2, 5.3, 5.4, 5.5 and 5.7, the cost table of section 5.3, figures 12 and 13, the "Basis" bullets for Part 0 and Part A in the factor table of section 4, the estimates under "What the numbers say" (0.95 to 1.16 us, about 2.8 us), and the buffer sizes in section 5.6. For every number in scope, find the saved output or script in exec/gdn-20261120/design-checks/ (or in exec/results/gdn-20261120/bench/) that supports it, and compare. Examples: 18.5 tile products and about 680 AVX-512 operations per value head per token; about 5,120 operations today; the cycle rows 269, 15, 159, 340 to 417, 189 to 426 and the total 972 to 1,286; 0.41 to 0.54 us and 0.51 to 0.68 us; 384, 32 and 192 TDPBF16PS per block; 8,704 operations per block; 87 % against 40 % of cache lines in L1; the 12 KiB buffer; 96 KiB; 0.005 to 0.10 % of output words; up to 46 increments; 0.3 to 1.1 and 0.3 to 3.2 times; 33, 27 and 9 FP32 increments after 1,024 tokens; 9.9e-32 and 1.2e-38; 7.5e-8 to 1.7e-6 and 18 to 61 times; 7 to 36 % and 32 to 81 %; 1.1 to 1.2 and 1.2 to 1.55 times; 227 KiB to at most 559 KiB; 32 tile products for QK and for PV against 16 today; 4 KiB to 8 KiB and 8 KiB to 16 KiB; 64 KiB against 32 KiB per page; 1.6 to 2.2 times; the fit 3.0 to 3.3 with the lower bound 2.3. You may re-run a design-check script when it is pure python and finishes in under 5 minutes: run a copy from your scratch folder so that no saved output is overwritten. Also check the block-form formulas printed in figure 12 against the prototype script (proto/gdn_block_proto.py): the indices, which decay products appear, and the stage that each tile product belongs to. Where the saved outputs of two check folders disagree on a number that the page uses, report it.',
  },
  {
    key: 'code',
    prompt: 'Your dimension: CODE AND SOURCE CLAIMS (key: code). Scope: every statement on the page that describes the tron source, the model shape, or an earlier measurement, and every entry of section 7 "Sources". Check against the tron copy at /home/jhan/workspace/ai-runs/tron-qwen35-4b (confirm with git that it is at commit 72e1191804) and against the other local files that the Sources name. Examples: the file paths and line ranges in Ref1 to Ref8, Ref10, Ref11, Ref16, Ref17 and Ref20 (does each line range hold what the page says it holds?); the model shape (32 layers, the pattern of GDN and attention layers, 16 key heads, 32 value heads, a 128 x 128 FP32 state, 16 query heads of 256 values, 4 KV heads; llama-3.1-8b with 32 heads of 128 values and 8 KV heads); the memory sizes (2 MiB per layer, 48 MiB, 2.25 MiB of convolution history, 50.25 MiB; 131,072 bytes per context token for llama); the arithmetic counts (262,144 and 65,536 multiply-adds per context token, 37.7 million per token, the crossover at 576 tokens in figure 3); shape_ok accepting only 128 x 4; FPGA attention accepting only 64 and 128; the thread split (the main thread and 15 main helpers run GDN, 40 attention workers, 56 application CPUs); work item = (chain, key head); prefill chains of 128 tokens on a working copy of 128 KiB; the check for invalid values; what the trace slice GatedDeltaNet covers; the test facts of section 5.4 (tolerance 1e-7, the equal-bytes tests, 320 output words fixed to PyTorch values, a test head of 16 key rows and 80 value columns); the file names in section 5.6 (do the existing files exist at those paths, and are the files marked "new" really absent?); the support level cpp_plugin and its meaning. For the earlier measurements, check the quoted values in the local pages: Ref12 (perf-model/index.html and exec/3b35-inspect-20261112/delphi-3b35-vs-3bda.html: AMX at 92 % of the AVX-512 clock, a 77 % wait share at prompt 8,192, the 21 % launch work share, the three CPU settings that differ), Ref13 (CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html lines 857-891: 20, 35, 47 and 57 %), Ref19 (exec/results/single-attn-20260901/summary.json and PR3879/make-sense-amx-vs-avx.html: 1.02, 1.18, 1.22). Ref14 cites published work on the internet: do not fetch it, and list it as not checked. Also confirm that every [RefN] used in the body has an entry and that every entry is cited at least once.',
  },
  {
    key: 'presentation',
    prompt: 'Your dimension: PRESENTATION (key: presentation). Scope: the whole page as a reader sees it. (a) Render every inline SVG figure and look at it: extract each svg element to a file in your scratch folder, convert it to PNG with python cairosvg (if cairosvg is missing, try rsvg-convert or inkscape; if none works, say so and check the geometry from the SVG coordinates), open each PNG with the Read tool, and look for text that overlaps other text or marks, text cut off by the figure edge, labels inside arrowheads, bars or dots that do not match their labels, a missing legend entry, and text too small to read. (b) Check the page against the plain-English rules in the file /home/jhan/.claude/skills/plain-english/SKILL.md and the project rule "prompt N, never ctx N": idioms or metaphors, sentences with two claims or with more than one subordinate clause, semicolons, code names or abbreviations that are used before they are defined and are missing from "Words used here", numbers without units, estimates not marked "est.", a citation that stands alone, a missing "Short version", and the banned words convoy, refund, "in disguise", swept. Report at most the 25 clearest rule violations, each with the exact sentence and a corrected sentence, and say how many more you saw. (c) Check the structure: the figure numbers run 1 to 13 without gaps and each caption matches its figure; every internal link target exists; the table of contents matches the section headings; tables have a header row and units in the headers; the page has a light background and does not switch to dark colors under prefers-color-scheme; the page is pure ASCII; the "Words used here" list is a folded details element. (d) Look for statements in different sections that contradict each other in words (another checker covers the numbers).',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'short stable id, dimension key plus a number, for example baseline-1' },
          place: { type: 'string' },
          quote: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          correction: { type: 'string' },
          severity: { type: 'string', enum: ['wrong', 'unsupported', 'inconsistent', 'minor'] },
        },
        required: ['id', 'place', 'quote', 'problem', 'evidence', 'correction', 'severity'],
      },
    },
    claims_checked: { type: 'integer' },
    claims_ok: { type: 'integer' },
    checked: { type: 'string' },
    not_checked: { type: 'string' },
  },
  required: ['findings', 'claims_checked', 'claims_ok', 'checked', 'not_checked'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          confirmed: { type: 'boolean' },
          reason: { type: 'string' },
          evidence: { type: 'string' },
          correction: { type: 'string', description: 'the right correction when confirmed; empty when not confirmed' },
        },
        required: ['id', 'confirmed', 'reason', 'evidence', 'correction'],
      },
    },
  },
  required: ['verdicts'],
}

function verifyPrompt(d, findings) {
  return COMMON + [
    'Your role now: SKEPTIC for the dimension "' + d.key + '" (scratch folder key: verify-' + d.key + ').',
    'A checker reported the findings below about the page. For each finding, try to refute it. Open the page and the evidence yourself and recompute. Mark a finding confirmed only when you reproduced the problem on your own. Mark it not confirmed when the checker misread the page, misread the data, compared against the wrong source, the page value is a correct rounding of the source, or you cannot reproduce it. When the problem is real and the proposed correction is wrong or larger than needed, give the right smallest correction. Return one verdict per finding, with the same id.',
    '',
    'Findings (JSON):',
    JSON.stringify(findings, null, 1),
  ].join('\n')
}

const results = await pipeline(
  DIMENSIONS,
  d => agent(COMMON + d.prompt, { label: 'check:' + d.key, phase: 'Check', schema: FINDINGS_SCHEMA }),
  (res, d) => {
    if (!res) return { key: d.key, failed: true, findings: [], verdicts: [] }
    if (!res.findings.length) return { key: d.key, summary: res, findings: [], verdicts: [] }
    return agent(verifyPrompt(d, res.findings), { label: 'verify:' + d.key, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({ key: d.key, summary: { claims_checked: res.claims_checked, claims_ok: res.claims_ok, checked: res.checked, not_checked: res.not_checked }, findings: res.findings, verdicts: v ? v.verdicts : null }))
  }
)
return results
