export const meta = {
  name: 'gdn-design-round2-final-verify',
  description: 'Final check of the round-2 page: numbers with the new clock-cost term, the 30 residues of the last pass, and the browser layout (read-only)',
  phases: [
    { title: 'Verify', detail: 'three independent checkers: numbers, residues, browser' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'
const D = '/home/jhan/workspace/intel-AMX/exec/gdn-20261120'

const COMMON = [
  'You are checking a revised design page before the author hands it back to an external reviewer. You do not edit anything.',
  '',
  'The page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html (275,341 bytes, sha256 385fe4fcce762b4622f0f8d17ccd9ebe104d977b33674af244ab8f955a28b632). Title: "GDN and AMX: design for Qwen3.5 4B". It reports a measured baseline of the Qwen3.5 4B model in tron (an inference program) on the server delphi-3b35, a prediction of what three proposed changes (Part 0: a new loop order for the GDN layers without AMX; Part A: an AMX block kernel for GDN; Part B: an AMX attention kernel for 256-wide heads) would do to the time to first token (TTFT) and to the decode speed, and a software design. Nothing is built yet.',
  'Plain-text extraction of this version: ' + SP + '/page-text.r2c.txt (645 lines; figures appear as [SVG: ...] and [SVG-TEXT: ...] lines). Extraction of the version one step earlier, which five checkers examined: ' + SP + '/page-text.r2.txt. Their 41 reports are in ' + SP + '/round2-verify-result.json (a list of {key, result:{problems[], checked, not_checked, counts}}; keys r1r2, r3to7, numbers, browser, fresh). The author then applied corrections for them. The largest one: predict.py has a new term. Under Part B the "other attention work" of a prefill pass (attention busy time minus full-page time minus join wait) is made slower by a clock cost (assumption tax_attn_other: +42 % in the low and working case, +12.5 % in the high case), because the attention workers run it at the clock of the AMX kernel. Part B now reads "TTFT falls by 2 to 22 % (est.), range 1 to 26 %" and Parts A and B "30 to 41 %, range 18 to 47 %". The factor table has a new last row for this cost, and the formula block of section 4 has a new term.',
  'The review record with the 7 reviewer findings (R1 to R7) that this revision answers: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.review.md.',
  '',
  'Where the evidence lives (all under /home/jhan/workspace/intel-AMX unless noted):',
  '- exec/gdn-20261120/ : gen_design.py, design_numbers.py, predict.py, figs_*.py, pagelib.py (CSS), collect.py.',
  '- exec/results/gdn-20261120/ : collected.json (2.7 MB: load it with python, never print it whole), predictions.json, bench/*.txt.',
  '- exec/gdn-20261120/design-checks/review/ : evidence scripts with saved outputs (r1_attention_timers, paired_changes, same_code_spread, r3_split_facts, r3_rule_variants, r4_scale_check, phase_lengths, r6_traced_vs_untraced, r7_serial_path_numbers, attn_256_l2_count, attn_prefill_fit, decode_options_range).',
  '- /home/jhan/workspace/ai-runs/tron-qwen35-4b : read-only copy of the tron source at commit 72e1191804.',
  '',
  'Hard rules:',
  '- Read-only. Do not modify, create or delete any file under /home/jhan/workspace. Do not run gen_design.py, predict.py, collect.py or analyze_trace.py as programs (they overwrite outputs). To regenerate the page into a scratch folder, run: PYTHONDONTWRITEBYTECODE=1 python3 ' + D + '/review-loop/regen_check.py <scratch folder>.',
  '- Do not ssh to any machine. Do not use the network.',
  '- This shell may use 6 CPUs. Size any worker pool from nproc. Do not start more than 6 processes at once.',
  '- Scratch files go only under ' + SP + '/round2-final/<your key>/ (create the folder).',
  '- Set PYTHONDONTWRITEBYTECODE=1 when you run python.',
  '',
  'Report only real problems: a statement on the page that the evidence contradicts or does not support, a correction that was not applied or was applied wrongly, two places of the page that contradict each other, or a new defect. A rounding difference counts only when the page value is not a correct rounding of the source value. Wording preferences and requests for more experiments do not count. For each problem give the place, a short exact quote from the page, what is wrong, the evidence, and the smallest correction. Zero problems is a valid result. Also say briefly what you checked and what you could not check.',
  '',
].join('\n')

const TASKS = [
  {
    key: 'numbers',
    prompt: 'Your key: numbers. Recompute the prediction yourself from collected.json with your own code, following the formula block and the method bullets of section 4 of the page: the full-page time from the line fit (per user count, a least-squares line of busy time minus join wait against the K tokens that the ready pass scores per pass; full-page time = slope x those K tokens), the other attention work (busy time minus full-page time minus join wait), the factors and the two clock-cost rows of the factor table, for all 6 cells, for Part 0, Part A, Part B, Part 0 with Part B, and Parts A and B, at the low, working and high values, and decode. Compare with predictions.json and with every prediction number on the page: the table under the Short version, the factor table (all rows, including the new last row and its basis bullets: 1.5 to 1.6 ms, 6.4 to 6.5 ms, 42 %, 12.5 %), figures 9 and 10 (labels in the SVG text), the per-cell table, "How to read the prediction", the sensitivity bullet (it must be the pure variant: the whole busy time divided by the factor and no clock cost on other attention work), the decode range with a fixed join wait, the clock note (Part A at 1.90 GHz), figure 8, figure 13, sections 5.1 and 5.2, and in section 6 the table "Predicted TTFT fall of the two A/B runs" with its notes and example. Check that the page describes the new term consistently in every place that speaks about what Part B changes in a prefill pass (word list entries, section 3, section 4 method bullets and formula block, factor table, section 5.1, section 5.5, section 6), and that predict.py (docstring, comments, ASSUMPTIONS, formula) agrees with the page. Check the saved outputs of design-checks/review/paired_changes.out and r1_attention_timers.out against predictions.json (both scripts print a cross-check line). Search the page for stale numbers of earlier versions: "4 to 22", "2 to 26", "32 to 41", "20 to 47" must be gone; "5 to 24", "4 to 28", "34 to 42", "22 to 48" may appear only in the sensitivity bullet; "2,031" must be gone.',
  },
  {
    key: 'residues',
    prompt: 'Your key: residues. Take the reports of the five earlier checkers in round2-verify-result.json (keys r1r2: P1 to P5; r3to7: R5-a, R6-a, R4-a, R3-a; numbers: N1 to N5; fresh: F1 to F5 and the plain-English items P1 to P15; the browser items B1 to B7 belong to another checker, skip them). For each report decide whether the present page resolves it: resolved, partly, or not. Where the author chose another correction than the one proposed, judge the result, not the method. Check the truth of every replacement text against the evidence that the report names. Pay special attention to: (1) the method bullets of section 4 about the serial order in GDN layers and in attention layers, against the open point "Wait for K and V under Part B" and the new bullet "Part B" under "What would prove the prediction wrong"; (2) the new last row of the factor table (clock cost on the other attention work) and the reason added to the high case of the Part A clock-cost row; (3) figure 11 labels ("page of this pass, or no AMX", "full page of an earlier pass", "No AMX, or the kill switch or the GDN switch is set:") against section 5.6 and h/tron/models/attn_stats.hpp lines 200-204; (4) the notes under the second table of section 5.3 (merged runs: 2,688 operations, 2,057 cycles, 0.86 us, 1.08 us); (5) figure 12 note "scale = 1 / sqrt(128), in the FP32 coefficients." and the section 5.4 sentence about the scale, against design-checks/verify-math/vm_engine.py (block_spec); (6) the task 5 pass rule (the decision rule sentence and "-5.3 %") and the bullets "Base build, base run" and "Denominator of a range rule"; (7) the restructured bullets "Limit of the decode numbers" and "Part 0" under "What would prove the prediction wrong" (sub-bullets): no content that reviewer findings R6 and R7 asked for may be lost. Then read all sentences that are new against page-text.r2.txt and report any that is false, unsupported, or breaks a plain-English rule in /home/jhan/.claude/skills/plain-english/SKILL.md (idiom, two claims in one sentence, more than one subordinate clause, undefined term, number without unit, estimate without "est."). Finally act as the external reviewer once more for R1 to R7 and say, per finding, whether you would close it on this page, with the reason if not.',
  },
  {
    key: 'browser',
    prompt: 'Your key: browser. Check the layout of the page in a real browser after seven CSS and markup corrections. An earlier checker found 7 layout defects (B1 to B7 in round2-verify-result.json, key browser: read its problems, its "checked" text and its scratch folder ' + SP + '/round2-verify/browser/, which holds its helper scripts such as shot.sh, dump.sh and cols.js and its wrapper pages: reuse them, copied into your own scratch folder). The corrections: th.n may wrap (B2); table { line-height: inherit } (B3); font-feature-settings "calt" 0 for body and table (B4); a span class "nw" (white-space: nowrap) around exponent-form numbers, powers of two and "AVX-512" in text (B5); figure svg { min-width: 880px } at widths up to 640 px (B6); .short { box-sizing: border-box } (B7); table.prose th:last-child { min-width: 400px } for the factor table, the code structure table, the plan table and the comparison table (B1). The headless Chromium is at /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell, with the flags --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer --hide-scrollbars --window-size=W,H --timeout=20000 --screenshot=<png> <url>. Note: a file URL with a #fragment gave a blank screenshot in the author\'s own test, and a screenshot without a fragment worked. The earlier checker covered the page with tiles through its own wrapper pages. For each of B1 to B7 decide: resolved, partly, or not, at desktop width (1280 px) and at phone width (390 px), with the web fonts and with the fallback fonts where the defect depended on them. Then look at the whole page again at both widths for new defects: a table or the page wider than the window, columns that cannot be reached, text that runs over other content, the formula block of section 4 (it now has eight lines), the new last row of the factor table, the tables of section 6, figures 2, 11 and 12 (their labels changed), and broken markup (the page must contain no visible raw tag text). Report each remaining or new layout defect with the screenshot path, the position, and the smallest correction.',
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
