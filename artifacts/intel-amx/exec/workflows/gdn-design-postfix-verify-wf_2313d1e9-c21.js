export const meta = {
  name: 'gdn-design-postfix-verify',
  description: 'Verify the revised GDN design page: every confirmed finding resolved, new numbers consistent, no new defect (read-only)',
  phases: [
    { title: 'Verify', detail: 'four independent checkers: numbers, resolution of findings (two halves), fresh-eyes consistency and figures' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'
const D = '/home/jhan/workspace/intel-AMX/exec/gdn-20261120'

const COMMON = [
  'You are checking a revised design page before it goes to an external reviewer. You do not edit anything.',
  '',
  'The page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html (241,257 bytes, sha256 db34c14f50f2dcf7a96e9762d03559958c2aeef54cc73bcf4fd1e77d2f88294b). Title: "GDN and AMX: design for Qwen3.5 4B". It reports a measured baseline of the Qwen3.5 4B model in tron (an inference program) on the server delphi-3b35, a prediction of what three proposed changes (Part 0, Part A, Part B) would do to the time to first token and to the decode speed, and a software design. Nothing is built yet.',
  'Plain-text extraction of the revised page: ' + SP + '/page-text.r1.txt (538 lines; figures appear as [SVG: ...] and [SVG-TEXT: ...] lines). Extraction of the page before the revision: ' + SP + '/page-text.r0.txt. Unified diff of the two: ' + SP + '/page-text.r0-r1.diff. Diff of the generator scripts: ' + SP + '/generator.r0-r1.diff.',
  '',
  'What the revision did. A first check found 72 defects, and a second checker confirmed 67 of them. They are in the JSON file ' + SP + '/presubmit-result.json: a list with one entry per dimension (keys baseline, prediction, design, code, presentation); each entry has "findings" and "verdicts" (same ids; a verdict with confirmed=true has a field "correction" with the checked correction when it is not empty). The author then edited the generator scripts and regenerated the page. The main changes of substance:',
  '- Part 0 factors of the prediction changed from 1.8 / 2.2 / 2.5 to 1.4 / 2.1 / 2.4 (low / working / high). The new low case comes from a stand-alone timing on another CPU (AMD Zen 5), files ' + D + '/design-checks/verify-cost/bench_gdn.run*.out. The page now discloses that timing.',
  '- Part B prefill factors changed from 1.6 / 2.4 / 3.2 to 1.6 / 2.3 / 2.9, because the fit script gives 2.95 to 3.05 (not 3.0 to 3.3).',
  '- The clock probe turn lengths were corrected (35 ns and 33 us). Stage 3 operation count 9,216. Several numerics statements, test facts and source references were corrected. Two sources were added (Ref21, Ref22). Words were added to the word list. Six figure defects were fixed.',
  '- Three small check scripts with saved outputs were added in ' + D + '/design-checks/review/ (attn_prefill_fit.out, attn_256_l2_count.py and .out, decode_options_range.py and .out).',
  '',
  'Where the evidence lives (all under /home/jhan/workspace/intel-AMX unless noted):',
  '- exec/gdn-20261120/ : gen_design.py (generates the page), design_numbers.py (numbers and text of the design sections), figs_data.py, figs_design.py, figs_static.py, pagelib.py (figures and CSS), predict.py (the prediction), collect.py, analyze_trace.py.',
  '- exec/results/gdn-20261120/ : collected.json (2.7 MB, load it with python, do not print it whole), predictions.json, rt-results.txt, rt/*.log, trace/*.summary.json, bench/*.txt, load/, plugin/qwen_3p5_4b.hpp.',
  '- exec/gdn-20261120/design-checks/ : check scripts with saved outputs (*.out, *.json).',
  '- /home/jhan/workspace/ai-runs/tron-qwen35-4b : read-only copy of the tron source at commit 72e1191804.',
  '',
  'Hard rules:',
  '- Read-only. Do not modify, create or delete any file under /home/jhan/workspace. Do not run gen_design.py, predict.py, collect.py or analyze_trace.py as programs: they overwrite the page and the result files. To regenerate the page into a scratch folder, run: PYTHONDONTWRITEBYTECODE=1 python3 ' + D + '/review-loop/regen_check.py <scratch folder> (it redirects every output to that folder and prints whether the result is byte-identical to the saved page).',
  '- Do not ssh to any machine. Do not use the network.',
  '- Scratch files go only under ' + SP + '/postfix/<your key>/ (create the folder).',
  '- Set PYTHONDONTWRITEBYTECODE=1 when you run python.',
  '',
  'Report only real problems: a statement on the revised page that the evidence contradicts or does not support, a confirmed finding that the revision did not resolve, two places of the revised page that contradict each other, or a new defect that the revision introduced. A rounding difference counts only when the page value is not a correct rounding of the source value. Wording preferences and requests for more experiments do not count. For each problem give the place, a short exact quote from the revised page, what is wrong, the evidence (file and line, or the command and the value you got), and the smallest correction. Zero problems is a valid result. Also say briefly what you checked and what you could not check.',
  '',
].join('\n')

const TASKS = [
  {
    key: 'numbers',
    prompt: 'Your key: numbers. Recompute the prediction yourself from the formulas printed in section 4 of the revised page and the measured inputs in collected.json (pass wall, GDN wall, attention busy time, number of passes, TTFT, decode speed), with the new factors, for all 6 cells, for Part 0, Part A, Part B and Parts A and B, at the low, working and high factors. Compare with predictions.json and with every prediction number on the revised page: the table under the Short version, the factor table, figures 9 and 10 (labels), the per-cell table, "How to read the prediction", "What would prove the prediction wrong", figure 13, figure 8, and the copies in sections 5.1 and 5.2. Check every arithmetic statement in the Basis bullets of the factor table, in particular the new ones: the Part 0 range 2.7 to 3.5 us and its factors, the working value (step 3.1 us, factor 2.1), the low case (ratios 1.46 to 1.74 from the three bench_gdn.run*.out files, new step 4.0 to 4.6 us, factor 1.4 to 1.6, 0.6 to 0.9 cycles per line), the Part B values (2.95 to 3.05, 2.3 = 3.0 x 0.76, 2.9 = 3.05 x 0.96, (8,192 + 3,031) / (2,031 + 3,031) = 2.2 and 1.6 at 1.90 GHz), the statement "In its low case Part A gives 3 to 5 percentage points less than Part 0 at its working value", "4 to 6 percentage points more", "about 79 %". Search the revised page for values of the old prediction that should be gone (for example "15 to 24", "12 to 26", "5 to 25", "4 to 29", "35 to 43", "22 to 49", "83 %", "3.15", "3.3", "2.6 to 3.5", "25 us", "34 ns", "8,704", "46 increments", "64 tile products", "about every 1 us") and report each one that is still there and is now wrong. Check that the comments and the ASSUMPTIONS in predict.py agree with the page.',
  },
  {
    key: 'resolved-a',
    prompt: 'Your key: resolved-a. Take every finding with confirmed=true in the dimensions baseline, prediction and design of presubmit-result.json (21 findings). For each one decide: resolved, partly resolved, or not resolved on the revised page. Then check that the replacement text itself is true: open the evidence that the finding names and compare it with the new wording. Where several findings name the same defect, check each place of the page that they list. Pay special attention to: the turn lengths in section 4 (clock note), section 5.3 and section 6; the bullet about 80 and 56 cache lines; figure 12 (9,216 operations) and whether "about 680 AVX-512 operations per value head per token" still agrees with the recount in design-checks/verify-cost/recount_tiles.out; the numerics bullets of section 5.4 (67 increments; 7.5e-8 to 1.6e-5 and 5 to 227 times over the three checks; the tests bullet); section 5.5 (two runs of 32 tile products) and the turn length "0.4 to 0.6 us" in section 6 (921 and 1,120 cycles per run at 2.40 or 1.90 GHz); the decode options of section 5.7 against design-checks/review/decode_options_range.out; figure 13 second bar.',
  },
  {
    key: 'resolved-b',
    prompt: 'Your key: resolved-b. Take every finding with confirmed=true in the dimensions code and presentation of presubmit-result.json (46 findings). For each one decide: resolved, partly resolved, or not resolved on the revised page. For the code findings, open the tron source or the local file that the finding names and check that the new wording is true (for example: section 5.4 bullet on resumed prompts against h/tron/scheduler/full.hpp lines 255-263; "AMX has no tile product for FP32 inputs ... bf16, and fp16 on this CPU" against exec/3b35-inspect-20261112/cpu-firmware-delphi-3b35-cpuid-user.txt; Ref5, Ref17, Ref20, the new Ref22). For the presentation findings 17 to 41 (plain-English rules) check each quoted sentence on the revised page. Findings presentation-7 to presentation-12 are about figures: check them from the SVG of the revised page (text positions, 0.6 em per character for monospace text, legend keys, the pre block CSS). List every finding that is not resolved or only partly resolved, with the exact text that is still on the page. Do not list resolved findings one by one: give only their count.',
  },
  {
    key: 'fresh',
    prompt: 'Your key: fresh. You are the fresh reader. Read the whole revised page text once, from top to bottom, as an engineer who has not seen it. Then: (a) Look for contradictions between sections, in particular ones that the revision may have introduced: the Part 0 low case (1.4) against every place that speaks about Part 0, Part A or their comparison (Short version table, section 3 hypothesis, section 4, section 5.1, 5.2, the plan in section 6 with its pass rules, the open points); the names "token path", "column-half path", "block path" across sections 5.4, 5.6 and 6; "memory stall" against "attention wait"; the test facts of section 5.4 against the Tests row of section 5.6. (b) Check the new and changed sentences (the lines that start with "+" in the page text diff) against the plain-English rules in /home/jhan/.claude/skills/plain-english/SKILL.md: idioms, two claims in one sentence, more than one subordinate clause, undefined terms (a term counts as defined when it is in the "Words used here" list or defined in the sentence), numbers without units, estimates without "est.". Report only violations in new or changed sentences. (c) Check that every [RefN] in the body (1 to 22) has an entry in section 7 and that what each new or changed entry says exists on disk (file paths, line ranges) where it is a local file. (d) Render all 13 figures of the revised page: extract each svg element, convert to PNG with python cairosvg at scale 2 (replace the font-family lists by "DejaVu Sans" for body text and "DejaVu Sans Mono" for monospace text first, because cairosvg uses only the first family and the named web fonts are not installed), open every PNG with the Read tool and look for text over text, text over lines or marks, text outside a box or the figure, a label that does not match its mark. Figure 2 (formula lines now in three columns) and figure 13 (longer label on the second bar) changed after the last visual check. (e) Run ' + D + '/review-loop/regen_check.py into your scratch folder twice, with PYTHONHASHSEED=1 and PYTHONHASHSEED=2, and report whether both runs say IDENTICAL.',
  },
]

const SCHEMA = {
  type: 'object',
  properties: {
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          place: { type: 'string' },
          quote: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          correction: { type: 'string' },
          severity: { type: 'string', enum: ['wrong', 'unsupported', 'inconsistent', 'unresolved', 'minor'] },
        },
        required: ['id', 'place', 'quote', 'problem', 'evidence', 'correction', 'severity'],
      },
    },
    checked: { type: 'string' },
    not_checked: { type: 'string' },
    counts: { type: 'string', description: 'for example: 21 findings, 20 resolved, 1 partly' },
  },
  required: ['problems', 'checked', 'not_checked', 'counts'],
}

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: 'verify:' + t.key, phase: 'Verify', schema: SCHEMA }).then(r => ({ key: t.key, result: r }))
))
return results.filter(Boolean)
