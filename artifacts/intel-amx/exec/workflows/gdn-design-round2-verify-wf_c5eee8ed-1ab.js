export const meta = {
  name: 'gdn-design-round2-verify',
  description: 'Verify the round-2 revision of the GDN design page against the 7 reviewer findings, the data and a real browser (read-only)',
  phases: [
    { title: 'Verify', detail: 'five independent checkers: R1-R2, R3-R7, numbers, browser layout, fresh reader' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'
const D = '/home/jhan/workspace/intel-AMX/exec/gdn-20261120'

const COMMON = [
  'You are checking a revised design page before the author hands it back to an external reviewer. You do not edit anything.',
  '',
  'The page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html (269,347 bytes, sha256 cfbf9a37364270bdc0b076942b202d18003887bf60573d71d0ad44e7d61aa0b5). Title: "GDN and AMX: design for Qwen3.5 4B". It reports a measured baseline of the Qwen3.5 4B model in tron (an inference program) on the server delphi-3b35, a prediction of what three proposed changes (Part 0: a new loop order for the GDN layers without AMX; Part A: an AMX block kernel for GDN; Part B: an AMX attention kernel for 256-wide heads) would do to the time to first token (TTFT) and to the decode speed, and a software design. Nothing is built yet.',
  'Plain-text extraction of this version: ' + SP + '/page-text.r2.txt (622 lines; figures appear as [SVG: ...] and [SVG-TEXT: ...] lines). Extraction of the version that the reviewer saw (round 1): ' + SP + '/page-text.r1c.txt. Diff of the generator scripts between the two: make it yourself with diff -u ' + SP + '/before-round2/<file> ' + D + '/<file> for predict.py, design_numbers.py, gen_design.py, figs_static.py, figs_design.py.',
  '',
  'The review record: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.review.md. Read the entry with role=reviewer status=COMMENTS: it holds 7 findings, R1 to R7, and one note about the structure check script. The author accepted all 7 and revised the page. The main changes:',
  '- R1: the prefill factor of Part B now divides only the "full-page time" (the part of the attention busy time that grows with the K tokens in full pages, from a line fit in predict.py), not the whole busy time. Part B now reads "TTFT falls by 4 to 22 % (est.), range 2 to 26 %" and Parts A and B "32 to 41 %, range 20 to 47 %". The timers are redefined (attention busy time, join wait, full-page time, attention wait), two table columns were added in section 3, and section 4 has new method bullets with a check against a measured A/B run on delphi-3bda.',
  '- R2: section 6 has new pass rules for tasks 2, 5 and 6, a block "Which runs tasks 2, 5 and 6 compare" with two tables, and the terms base build, base run and GDN switch.',
  '- R3: section 5.4 states the split rule (truncation), the range where the 3-piece split is exact (2^-103 and larger), what is lost below it, and the overflow of round to nearest at the top of the range.',
  '- R4: figure 2 line 4 reads "o = (scale x q) times S" with a note, and figure 12 defines scale.',
  '- R5: the single interval "0.2 to 0.4 us" is gone. Section 5.3 has a second table with the runs of the block kernel, and the clock texts name the run or turn that each number belongs to.',
  '- R6: the decode GDN shares are labeled as estimates with a traced numerator, not as upper values.',
  '- R7: "What would prove the prediction wrong" presents three hypotheses for a Part 0 step between 3.5 and 4.6 us and names the timings that separate them, and states the controlled comparison for the serial-path assumption.',
  'The investigation behind each change (facts, evidence, proposed text) is in ' + SP + '/round1-investigation.json (a list: one entry per investigator with result.answers[], each with id, verdict, facts, changes, numbers, open_points). New evidence scripts with saved outputs are in ' + D + '/design-checks/review/ (r1_attention_timers, paired_changes, same_code_spread, r3_split_facts, r3_rule_variants, r4_scale_check, phase_lengths, r6_traced_vs_untraced, r7_serial_path_numbers).',
  '',
  'Where the evidence lives (all under /home/jhan/workspace/intel-AMX unless noted):',
  '- exec/gdn-20261120/ : gen_design.py, design_numbers.py, predict.py, figs_*.py, pagelib.py, collect.py, analyze_trace.py, clock_probe.cpp.',
  '- exec/results/gdn-20261120/ : collected.json (2.7 MB: load it with python, never print it whole), predictions.json, rt-results.txt, rt/*.log, trace/*.summary.json, bench/*.txt.',
  '- exec/gdn-20261120/design-checks/ : check scripts with saved outputs.',
  '- exec/results/attnstats-20261002/ : attention statistics of an A/B run on delphi-3bda (exit-reports.txt, attn-stats-compare.md).',
  '- /home/jhan/workspace/ai-runs/tron-qwen35-4b : read-only copy of the tron source at commit 72e1191804.',
  '',
  'Hard rules:',
  '- Read-only. Do not modify, create or delete any file under /home/jhan/workspace. Do not run gen_design.py, predict.py, collect.py or analyze_trace.py as programs (they overwrite outputs). To regenerate the page into a scratch folder, run: PYTHONDONTWRITEBYTECODE=1 python3 ' + D + '/review-loop/regen_check.py <scratch folder>.',
  '- Do not ssh to any machine. Do not use the network.',
  '- Scratch files go only under ' + SP + '/round2-verify/<your key>/ (create the folder).',
  '- Set PYTHONDONTWRITEBYTECODE=1 when you run python.',
  '',
  'Report only real problems: a statement on the revised page that the evidence contradicts or does not support, a reviewer finding that the revision did not fully answer (say exactly which part of the reviewer\'s request is still open), two places of the page that contradict each other, or a new defect. A rounding difference counts only when the page value is not a correct rounding of the source value. Wording preferences and requests for more experiments do not count. For each problem give the place, a short exact quote from the revised page, what is wrong, the evidence, and the smallest correction. Zero problems is a valid result. Also say briefly what you checked and what you could not check.',
  '',
].join('\n')

const TASKS = [
  {
    key: 'r1r2',
    prompt: 'Your key: r1r2. Act as the external reviewer who wrote findings R1 and R2, and be strict. For R1: read every part of the request ("Define both timers accurately. State the assumption about which time scales with the kernel, and show how Part B changes if join wait stays fixed, or justify an effective factor for the entire timer. Also identify partial pages as AVX-512 work where a factor comes from a full-page kernel count.") and decide for each part whether the revised page answers it. Check the new definitions against README.stats.md lines 280-300, h/tron/models/attn_stats.hpp and run_attention_job in h/tron/models/self_attention.hpp of the tron copy. Check the predict.py change (the function full_page_times and the formula line): does the code do what the page says, is the line fit sound with 3 points per user count, and are the new fields attn_full_ms and attn_join_ms right? Recompute the join wait and full-page columns of the two section 3 tables from collected.json. Check every number of the new method bullets in section 4 against design-checks/review/r1_attention_timers.out and against exec/results/attnstats-20261002/ (1.88 times, 4.1 to 12.0 ms, 99.7 ms, 106.5 ms, 1.90 to 1.93, 1.18 to 1.19, 12.6 / 3.1 / 1.6 %, 67 ns, 9 times, 1.1 to 1.6 times, 51 %, 72 %, 88 to 96 %, the sensitivity ranges, the decode range -4.5 % to +6.5 %). Note that the page chose a model that the reviewer did not list literally (factor on the full-page time; join wait and the pages of the pass in progress stay fixed): judge whether this answers "show how Part B changes if join wait stays fixed". For R2: check the new pass rules of tasks 2, 5 and 6, the block "Which runs tasks 2, 5 and 6 compare", its two tables and notes against the reviewer\'s request ("Specify the runs and denominator for each comparison, including the fixed Part B setting. Use the original baseline for the total Part A range and the paired run for its incremental gain."). Recompute the table "Predicted TTFT fall of the two A/B runs" from predictions.json and compare with design-checks/review/paired_changes.out. Check that the rules cannot be failed by a correct implementation at the working values, and that section 5.6 (row Switches) and the "Words used here" entries agree with the plan.',
  },
  {
    key: 'r3to7',
    prompt: 'Your key: r3to7. Act as the external reviewer who wrote findings R3, R4, R5, R6 and R7, and be strict. For each finding, read every part of the request and decide whether the revised page answers it, and whether the new text is true. R3: check the split bullets of section 5.4, the section 5.3 bullet "The FP32 state", the word list entries "piece, plane" and "subnormal value", and the Tests row of section 5.6 against design-checks/review/r3_split_facts.out, r3_rule_variants.out, kernel/02_split3_exhaustive.out and verify-math/vm_checks.out (parts C and E): the rule, 2^-103, 2^-110, 2^-126, 2^-133, 2^-149, 3.3895314e38, 3.3961775e38, 32,768 values per sign, 0 to 56 of 131,072 words, 0.99 to 1.13 times. R4: check figure 2 ("o = (scale x q) times S", the note with 0.0884) and figure 12 (the new note line) against h/tron/kernels/gated_delta_net.hpp lines 239-243 and 284-297 of the tron copy, and the new sentence in section 5.4 ("It also applies the scale of the read step ... to the FP32 sum"). R5: check that no single turn interval for the whole block kernel is left anywhere (search for "0.2 to 0.4"), and check every number of the second table of section 5.3 and its notes, of the section 5.3 bullet "Clock", of the clock note of section 4, of the section 5.5 bullet "Clock (hypothesis)" and of the open point "Core clock under AMX in tron" against design-checks/review/phase_lengths.out and against your own arithmetic from the costs (16.17 cycles per tile product, 8.38 per tile load, 16.1 per tile store, 0.50 to 0.613 per AVX-512 operation). Check the statement about Part A at 1.90 GHz (factor 2.6, clock cost 8.8 %, TTFT fall 14 to 23 %). R6: search the page for "upper value", "upper values", "up to" and "at most" and decide for each hit whether it still claims a bound that rests on a traced run; check the numbers of the new sentences (0.5 to 1.0 ms, 0.1 to 0.3 ms, 0.3 to 0.7 ms, 73 to 134 %, 11 to 22 %, at most 4 %) against design-checks/review/r6_traced_vs_untraced.out. R7: check the two rewritten bullets under "What would prove the prediction wrong" and the plan rows of tasks 1 and 2: does the text present the cause as hypotheses, name the component timings, and state the controlled comparison for the serial-path inference, as the reviewer asked?',
  },
  {
    key: 'numbers',
    prompt: 'Your key: numbers. Recompute the prediction yourself, from collected.json and the formulas printed in section 4 of the revised page (the formula block and the method bullets), with the factors of the factor table, for all 6 cells, for Part 0, Part A, Part B and Parts A and B, at the low, working and high factors, and for decode. For the full-page time, implement the line fit as the page describes it (per user count, a least-squares line of busy time minus join wait against the K tokens that the ready pass scores per pass; the full-page time is the slope times those K tokens) with your own code. Compare with predictions.json and with every prediction number on the revised page: the table under the Short version, the factor table, figures 9 and 10 (labels in the SVG text), the per-cell table, "How to read the prediction", figure 8, figure 13, the copies in sections 5.1 and 5.2, the table "Predicted TTFT fall of the two A/B runs" and its example note in section 6. Then search the revised page for numbers of the earlier versions that should be gone or should appear only in the sensitivity bullet: "5 to 24", "4 to 28", "34 to 42", "22 to 48", "15 to 24", "12 to 26", "35 to 43", "0.2 to 0.4 us", "about every", "upper value", "at most 1.8", "64 tile products", "25 us", "34 ns" (34 ns may remain only as the tile part of the short turn). Report each one that is still there and is now wrong. Check that the page is internally consistent after the change of the Part B model: every place that speaks about the attention time that Part B speeds up (Short version table, section 3, section 4, section 5.1 row "Full attention, prefill", section 5.5, section 6, the word list) must agree with "the factor divides the full-page time only" in prefill and "the whole busy time" in decode. Check the comments and docstring of predict.py against the page.',
  },
  {
    key: 'browser',
    prompt: 'Your key: browser. Check the layout of the revised page in a real browser. A headless Chromium is at /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell. This command line is known to work here (it wrote a correct screenshot): <binary> --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer --hide-scrollbars --window-size=1280,2400 --timeout=20000 --screenshot=<png in your scratch folder> "file:///home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html". Run it from your scratch folder, with a timeout of 100 s per call, and ignore the dbus and GPU warnings. A screenshot shows only the window, so cover the whole page by loading the page with a fragment for each anchor (#s1 to #s7 for the sections, #fig1 to #fig13 for the figures, #ref1 for the sources) and a window height of about 3000 px, and add more positions where a long section is not covered (you can also load a copy of the page from your scratch folder with extra anchors added, as long as the copy stays in your scratch folder). The page loads its fonts from Google Fonts. The network is probably blocked, so the browser falls back to local fonts: say which case you saw. Do two passes: desktop width (window 1280 px wide) and phone width (window 390 px wide; if the browser does not honour 390, use the smallest width it honours and say so). Open every screenshot with the Read tool and look for: text or a table that runs out of its column or over other content, a wide table that does not scroll inside its own box and instead widens the page (at phone width: content cut off at the right edge, or the whole page wider than the window), figures that are cut off or unreadably small at phone width, the formula block in section 4 (a light box with five lines: does each line fit, and does the block scroll sideways inside its box at phone width), the folded "Words used here" block, the new wide tables (the two tables of section 3 now have 12 columns, the second table of section 5.3, the two tables of the block "Which runs tasks 2, 5 and 6 compare" in section 6), overlapping text inside the SVG figures, and missing content. To test for a sideways scroll of the whole page you may write a small wrapper HTML file in your scratch folder that loads the page in an iframe of the tested width and prints document.documentElement.scrollWidth of the inner page (the browser flag --allow-file-access-from-files makes file URLs readable for such a script, and --dump-dom prints the result). Report each layout defect with the screenshot path, the position, and the smallest correction (CSS or structure). Also report plainly what you could not check.',
  },
  {
    key: 'fresh',
    prompt: 'Your key: fresh. You are the fresh reader. Read the whole revised page text once, from top to bottom, as an engineer who has not seen it. Then: (a) Look for contradictions between sections that the round-2 revision may have introduced: the Part B model (full-page time) against every place that speaks about attention time; the terms base build, base run, today\'s build, today\'s kernel; token path, column-half path, block path; attention wait, join wait, memory stall; tile run, AVX-512 run, turn; the pass rules of section 6 against section 4 ("What would prove the prediction wrong") and section 5.6 (Switches, Counters, Tests). (b) Check the new and changed sentences (compare page-text.r1c.txt with page-text.r2.txt) against the plain-English rules in /home/jhan/.claude/skills/plain-english/SKILL.md and the project term list in /home/jhan/workspace/intel-AMX/CLAUDE.md: idioms, two claims in one sentence, more than one subordinate clause, undefined terms (a term counts as defined when it is in the "Words used here" list or defined in the sentence), numbers without units, estimates without "est.". Report only violations in new or changed sentences, at most the 20 clearest. (c) Check that every [RefN] in the body (1 to 23) has an entry in section 7, and that the files and line ranges named by the new or changed entries (Ref3, Ref8, Ref18, Ref19, Ref23) exist on disk and hold what the entry says. (d) Render all 13 figures of the revised page: extract each svg element, convert to PNG with python cairosvg at scale 2 (replace the font-family lists by "DejaVu Sans" for body text and "DejaVu Sans Mono" for monospace text first), open every PNG with the Read tool and look for text over text, text over lines or marks, text outside a box or the figure, a label that does not match its mark. Figure 2 (a second note line under the four formula lines) and figure 12 (a sixth note line under the stage 3 box, the figure is 16 px taller) changed in this round. (e) Run ' + D + '/review-loop/regen_check.py into your scratch folder twice, with PYTHONHASHSEED=1 and PYTHONHASHSEED=2, and report whether both runs say IDENTICAL. (f) Say whether the page is still readable at its new length: name any passage where the new detail hides the main point, and propose the smallest restructuring (for example a sentence moved into a table note), without removing content that a reviewer finding asked for.',
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
    counts: { type: 'string' },
  },
  required: ['problems', 'checked', 'not_checked', 'counts'],
}

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: 'verify:' + t.key, phase: 'Verify', schema: SCHEMA }).then(r => ({ key: t.key, result: r }))
))
return results.filter(Boolean)
