export const meta = {
  name: 'verify-decode-section',
  description: 'Check the new decode section and the other new parts of the GDN/AMX results page against data, code and writing rules',
  phases: [
    { title: 'Check', detail: 'four independent checkers: numbers, code claims, reader, figures and scripts' },
    { title: 'Refute', detail: 'one skeptic tries to refute every finding' },
  ],
}

const COMMON = `
Context. A results page was extended. You check ONLY the new or changed parts. You must not edit any file of the project. You may write scratch files only under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/dwcheck/<your-lens>/ (create it).
Do not use ssh. Do not start more than 4 processes at once (the shell is limited to 6 CPUs).

Files:
- Page (HTML, generated): /home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html
- Page as plain text (new version): /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/results-page-text-v5.txt
- Page as plain text (previous version, before the change): /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/results-page-text-v4.txt
- Generator of the new parts: /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/decode_why.py (called from gen_report.py in the same folder)
- Data: /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/comparison.json (medians per cell and arm, key "cells" -> cell -> "terms"/"arms"/"direct"/"rules") and collected.json (key "runs": one record per run, with "cell", "arm", "derived", "gdn_derived", "attn", "gdn"; the decode class is the key "decode_like", the prefill class is "prompt_or_mixed"). collect.py and compare.py in the generator folder define every derived value.
- tron source tree at the measured branch (read-only): /home/jhan/workspace/ai-runs/tron-gdn-amx (files of interest: h/tron/models/gdn_execution.hpp, h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_stats.hpp, h/tron/models/attn_stats.hpp, h/tron/kernels/gated_delta_net.hpp, README.stats.md)

The new or changed parts of the page are:
1. Section 5 "Why decode gains little" (all of it: 4 sub-sections, Figures 5, 6, 7 and one table).
2. In section 3: the sub-section "8 users against 1 user at prompt 1,024" with Figure 3 and one table.
3. In section 2: the sub-section "Which kernel takes a token".
4. Near the top: the bullet "Part A is built on Part 0, and a build with Part A always has Part 0. ..." and the two changed "What runs" cells of the first table ("AMX block kernel for GDN, built on Part 0", "all three changes").
5. In "Words used here": the entries "attention wall", "other work", "start of a chain", "NaN", and the changed entry "Part 0, Part A, Part B".
6. Section 11: the last two bullets (decode with 1 user; the start of a chain). Section 12: [Ref20].
7. Renumbering: the old sections 5 to 11 are now 6 to 12, and the old Figures 3 to 6 are now 4, 8, 9, 10. Every "Section N" in the text must point to the right section.

Arms: base = base build; p0 = Part 0 (build with all changes, kill switch TRON_AMX_DISABLE=1); b = Parts 0 and B (GDN switch set); ab = Parts A and B = all three changes; a = Part A; a0 = Part A build with the GDN switch set. Cells: q35-tp4-{1u,8u}-p{1024,4096,8192}.

Report only real defects that you can show with evidence: a number that does not follow from the data, a statement that the code or data contradicts, a logic step that does not follow, a statement stronger than its evidence, a broken reference, a figure that misleads. Do not report matters of taste. If you find nothing, return an empty list. For each finding give the exact quoted text from the page, the evidence (numbers you computed, or file:line of code), and a concrete corrected wording.`

const FINDINGS = {
  type: 'object',
  properties: {
    checked: { type: 'string', description: 'what you checked, in 2 to 6 sentences, with counts (for example how many numbers you recomputed)' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string', description: 'section or figure and the quoted text' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'concrete corrected wording or code change' },
          severity: { type: 'string', enum: ['wrong', 'overstated', 'unclear', 'minor'] },
        },
        required: ['where', 'problem', 'evidence', 'fix', 'severity'],
      },
    },
  },
  required: ['checked', 'findings'],
}

const LENSES = [
  { key: 'numbers', prompt: `Lens: NUMBERS. Recompute, with your own Python code that reads comparison.json and collected.json directly (do not import or call decode_why.py or gen_report.py), every number in the new parts listed below, including the numbers inside the SVG figures (the text version of the page lists the SVG text after "[SVG-TEXT:"), the lane totals of Figure 6 for both states (attributes data-t0 and data-t1 in the HTML), and both new tables. Use medians over the 3 repetitions of a cell and arm, as collect.py and compare.py do. Check ranges ("67 to 76 %") by computing every cell. Check that each "est." is marked and each measured number is not. Check units. Also check the sentence "In all 6 arms and all 6 cells, 100 % of the decode head tokens took the token path" from the raw counters (gdn -> decode_like -> totals), and the statement "with Part A on, 100 % of the prompt tokens took the block kernel" (prompt_or_mixed totals of arms a and ab).` },
  { key: 'code', prompt: `Lens: CODE CLAIMS. For every statement in the new parts about how tron works, find the code that supports or contradicts it, and cite file:line. Statements to check include: a chain of 1 token takes step() and the token kernel, in place; a decode step gives a GDN layer one token per user and several users give several chains of 1 token; a full window of 32 prompt tokens takes the AMX block kernel when it is on; a shorter window takes the chain kernel; a refused block takes the chain kernel; "The chain kernel computes the read of the next token while it writes the current token"; what the "start of a chain" does (prepares/binds the state, copies it when the chain writes to another buffer, checks every state value for NaN) and whether that is all it does, for an in-place chain and for a working copy; whether the NaN check is compiled in the measured build type (the builds used the CMake preset "native": check what TRON_ASSERT does there, and say clearly if you cannot determine it); the state of one key head is 128 KiB (131,072 bytes); the definition of the "attention wall" (timer T3, wall_cycles_w0) and whether "with every wait" is right; the definition of the GDN wall; "GDN operation i is model layer i + i / 3", so that every 4th layer is an attention layer; the token step = convolution, normalization, recurrence, norm and output gate; the sentence about the design page risk (threads may finish scoring before K and V data are ready) - the design page is /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html. Also check [Ref20].` },
  { key: 'reader', prompt: `Lens: FIRST-TIME READER and LOGIC. Read the whole new text version of the page once, as an engineer who has never seen the project. Then judge the new parts. (a) Does section 5 really explain why decode gains little? Is any step of the argument missing, circular, or not supported by a number on the page? (b) Does every "So ..." follow from what precedes it? (c) Does any new statement contradict another part of the page (compare with sections 1, 4, 6, 8 and 11, for example decode numbers, busy time against attention wall, the percentages)? (d) Is any term used in the new parts before it is defined, either inline or in "Words used here"? (e) Check every "Section N" and "Figure N" reference in the whole page against the headings and captions. (f) The page follows these writing rules: at most 25 words per sentence; one claim per sentence; no clause inside a clause; a bullet has at most 3 sentences; no idioms or metaphors; every number has a unit; estimates are marked "est."; a bullet starts with its content, not with a label such as "Benefit:". A script already counts words, so look for what a script cannot see: idioms, clause-in-clause, two claims in one sentence, vague words, labels. (g) Would the reader understand from the page alone why there is no separate run "Parts 0, A and B", and why 8 users gain less than 1 user at prompt 1,024?` },
  { key: 'figures', prompt: `Lens: FIGURES and SCRIPTS. The page has two animated figures (Figure 5, id "flow-svg"; Figure 6, id "lanes-svg") driven by one inline <script> at the end of the HTML, and two new static figures (Figure 3, Figure 7). Read decode_why.py and the generated HTML. (1) Review the JavaScript for bugs: timeline logic, the counters, the pause button, the three buttons of Figure 6, the reduced-motion path, what the reader sees when JavaScript is off, leaks (timers, frames that never stop), and anything that could throw. (2) Render the figures and LOOK at them. For static renders extract each <svg> and use python3 with cairosvg (cairosvg.svg2png, output_width=1440), then read the PNG. For animated states use the headless browser /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell with --no-sandbox --disable-gpu --hide-scrollbars --window-size=W,H --screenshot=out.png file://test.html . requestAnimationFrame does not advance in that browser by itself: write a test page that first installs a fake requestAnimationFrame with a controllable clock (a queue of callbacks and a function that calls them with now += 16 until a given time), then includes the page HTML, then on load advances the clock and clicks buttons. Wrap the page in <!doctype html><html><head><meta charset="utf-8"></head><body>...</body></html>. Check several times of Figure 5 (for example 0.4 s, 1.0 s, 1.6 s, 2.4 s, 5 s, 9.5 s, and a second loop after 10.4 s) and both states of Figure 6, at desktop width (1040 px) and at phone width (400 px; figures may scroll sideways inside their own box, but the page body must not). Look for: text that overlaps other text or shapes, text cut off at an edge, a moving shape that covers a label, a block that lands outside its slot, labels that are wrong for the state shown, colors that contradict the legend or the lane labels, a caption that says something the figure does not show. (3) Check that the figure is honest: block lengths in Figure 6 must be proportional to the data inside a panel (recompute a few from the data-a attributes and the table of section 5), and the bars of Figure 3 and 7 must match their labels.` },
]

phase('Check')
const results = await parallel(LENSES.map(l => () =>
  agent(`${l.prompt}\n${COMMON}`, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS })
    .then(r => (r ? { lens: l.key, ...r } : null))))
const ok = results.filter(Boolean)
const all = ok.flatMap(r => r.findings.map((f, i) => ({ id: `${r.lens}-${i + 1}`, lens: r.lens, ...f })))
log(`${all.length} findings from ${ok.length} of ${LENSES.length} checkers`)
if (!all.length) return { checked: ok.map(r => ({ lens: r.lens, checked: r.checked })), findings: [], verdicts: [] }

phase('Refute')
const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly'] },
          reason: { type: 'string', description: 'your own evidence: numbers you recomputed or file:line' },
          fix: { type: 'string', description: 'the wording or change you recommend, empty when refuted' },
        },
        required: ['id', 'verdict', 'reason', 'fix'],
      },
    },
  },
  required: ['verdicts'],
}
const skeptic = await agent(
  `You are a skeptic. Other checkers reported the findings below about new parts of a results page. For EACH finding, try to refute it with your own evidence: recompute the number from the data, or read the code, or read the page text. A finding is "refuted" when the page is right, "confirmed" when the finding is right, and "partly" when the page should change but not as the finding says. Do not accept a finding because it sounds plausible, and do not reject one without evidence. Where two findings say the same, judge both the same way.\n\nFindings (JSON):\n${JSON.stringify(all, null, 1)}\n${COMMON}`,
  { label: 'refute:all', phase: 'Refute', schema: VERDICTS })
return { checked: ok.map(r => ({ lens: r.lens, checked: r.checked })), findings: all, verdicts: skeptic ? skeptic.verdicts : [] }
