export const meta = {
  name: 'verify-results-page-v2',
  description: 'Second check of the GDN/AMX result page: new numbers, new conclusions, and whether the first round of findings was applied',
  phases: [{ title: 'Check' }, { title: 'Refute' }],
}

const COMMON = `
You verify version 2 of a report page. Version 1 was checked before; many sentences and some tables are new. Be a skeptic.
Page (HTML): /home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html
Page as plain text: /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/results-page-text-v2.txt
Version 1 as plain text: /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/results-page-text-draft.txt
Findings of the first check (already applied, or meant to be): /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/understand/verify-page-result.json
Generator: /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/gen_report.py with report_data.py, collect.py, compare.py (same folder).
Raw data folder R = /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/
  R/rt/<cell>__<arm>__rep<N>.log   one runtron run. Cells q35-tp4-{1u,8u}-p{1024,4096,8192}. Arms base, p0, a0, a, b, ab, orig, nost.
                                    Repetitions 11-13 = session 2 (main data), 21-23 = control runs, 1-2 = session 1.
                                    A log holds per user "saw X s TTFT" and "at Y average tok/s", and at exit "[attn-stats] ..." and "[gdn-stats] ..." JSON lines
                                    (classes prompt_or_mixed = prefill passes, decode_like = decode steps; cycles / tsc_hz = seconds).
                                    Other logs the page cites: *__q-a__rep1/2 and *__f-a__rep1/2 (before and after a fix), tok-*__rep1 (token check), logit-* (score dumps).
  R/load/<run>.txt, R/rt-results.txt, R/collected*.json, R/comparison*.json
  R/bench/*.txt   stand-alone benchmarks. R/bench/task4-*.txt is a rerun of 2026-11-22; R/bench/task4-first-run/ holds the first run.
  R/tokens/p<prompt>__<arm>.txt   generated token ids; R/tokens/logits-p1024-l<len>__<arm>.txt = the 320 best scores of every generated step
                                    (lines "Top-k Logits of token N (320): ..." and "Top-k Token IDs for Logits of token N (320): ..."; generated token g = token 1023 + g);
                                    R/tokens/logits-summary-p1024-l*.txt
  R/unit-tests.txt
Prediction: /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json and predict.py in /home/jhan/workspace/intel-AMX/exec/gdn-20261120/. Design page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.
Code: git worktree /home/jhan/workspace/ai-runs/tron-gdn-amx (branch jhan-gdn-amx; base 72e1191804; branch jhan-gdn-amx-measured = the commits that session 2 ran).
Words: tron = the inference program; GDN = GatedDeltaNet layers; AMX = Intel tile instructions; TTFT = time to first token; bf16 step = distance between neighbouring bf16 values, 2^(floor(log2|x|)-7).
Arms: base = counters only; p0 = all changes with TRON_AMX_DISABLE=1; b = all changes with TRON_AMX_GDN_DISABLE=1; ab = all changes; a0 = build without Part B with TRON_AMX_GDN_DISABLE=1; a = build without Part B; orig = build of 2026-11-20; nost = counter build with the GDN counters off.
Hard rules:
- Read-only on everything above. Scratch scripts only under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/verify2-<your lens>/ .
- No ssh. Do not touch any machine named delphi-*. No network. At most 2 processes at a time.
- Recompute numbers yourself from raw files with your own code. Rounding to the printed digits is fine.
- Report only real problems: a wrong number, a sentence that claims more than the data shows, a contradiction between two places of the page, a finding of the first check that is still open. Do not report style taste.
Each finding: section, exact quote, severity, what is wrong, evidence (files and your value), corrected text. Also return "checked": what you verified and found correct, with counts.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          section: { type: 'string' },
          quote: { type: 'string' },
          severity: { type: 'string', enum: ['wrong-number', 'unsupported-claim', 'misleading', 'missing', 'wording'] },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['section', 'quote', 'severity', 'problem', 'evidence', 'fix'],
      },
    },
    checked: { type: 'string' },
  },
  required: ['findings', 'checked'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          quote: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted'] },
          reason: { type: 'string' },
          corrected_fix: { type: 'string' },
        },
        required: ['quote', 'verdict', 'reason'],
      },
    },
  },
  required: ['verdicts'],
}

const LENSES = [
  {
    key: 'campaign-numbers',
    prompt: `Lens: every number of the page that comes from the campaign logs and is new or changed against version 1. Compare the two text files to find them. They are mainly in: "The changes in one table" (row "Part B alone"), section 2 (session times, spread of the repetitions, the load text and load table with its rows for session 1, the control runs and the stand-alone benchmarks), section 3 (the bullets with working values, ranges, "below the working value in N of 6 cells", the count of single repetitions outside the range, the Part B alone bullet), section 4 (per-arm counts above and below the range, the cells above the range by more than the spread, the smallest margin to the 1.1 % limit, and all of "Where the decode gain comes from": busy time and join wait per decode step, the factors with and without the join wait), section 5 (rules table rows 1, 2, 5 and 6, the step table with its median-thread row, "Where the GDN step time goes", "From the GDN step to the pass" with the GDN wall factors and the change of the pass wall without the GDN wall, "Attention with Part B" with the join wait values, the ratio between the arms a and ab, the GDN wall change between builds), section 6 (the tron runs before and after the fix: TTFT, the count of GDN layers above 1.5 times the median layer, the largest ratio), section 7 (the sample line, the cost bullets, the cell where all runs with the counters on were slower).
Recompute each from R/rt/*.log (and R/load, R/bench/*-load.txt, the campaign log /home/jhan/workspace/intel-AMX/exec/logs/gdn-impl-20261121-campaign.log for the session times). Join wait and busy time per pass: join_wait_cycles and busy_cycles of the [attn-stats] totals / forwards / tsc_hz / number of attention workers. GDN wall per pass: sum of "wall_cycles per op" / forwards / tsc_hz.`,
  },
  {
    key: 'scores-bench-tests',
    prompt: `Lens: section 8 and section 9, and the parts of section 1 and 6 that cite stand-alone results.
(a) "Generated tokens" and "What the scores show": recompute every count from R/tokens/p*.txt and from R/tokens/logits-p1024-l4__base.txt, logits-p1024-l4__b.txt, logits-p1024-l190__base.txt, logits-p1024-l190__a.txt. Check: equal scores between two base runs; at generated token 0 how many of the common token ids differ and by how many bf16 steps (for arm b and for arm a); the scores and token ids at generated token 1 (base and b) and at generated token 185 (base and a); "In steps 0 to 79 its best score differs from the base run by at most N bf16 step" and "In the later steps it differs by up to N bf16 steps" (the best score = the score of the base run's best token id, compared in the other run, for steps before the first different token); the number of different tokens in the base output. Then judge the three conclusions of that part: "The block kernel runs in prefill only. The counters show all GDN tokens of decode on the token path, in every arm." (check the decode_like totals of the [gdn-stats] lines of session 2), "So after the prefill both runs use the same code. The difference then grows in that code.", and "This is not a tie. In this run a difference of at most 1 bf16 step at generated token 0 grew into another token within 185 steps." Is each one supported, and is anything overstated? Note that the dump keeps only the 320 best scores of a step.
(b) Numerics bullets and table against R/bench/task3-table-cpu140-run1.txt; the test-coverage bullets and the unit-test bullets against the test sources in /home/jhan/workspace/ai-runs/tron-gdn-amx/t/ and R/unit-tests.txt and R/unit/*.txt; the Part B self-check sentence against R/bench/task4-summary-cpu142.txt.
(c) Section 9 and Figure 6 text against R/bench/*.txt: per-run ratios, medians, the burst sentences and table, the stall sentence, the task 4 bullets and table (the rerun files), the 4 s loop ratio, and the claim "The 4 s loops also time the copy of the inputs into the window and the layout change of the start state. The short runs leave both out." (read /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/bench/amx_gdn_bench.cpp).
(d) Section 1 "Differences from the design": the numbers with [Ref4], [Ref5], [Ref7], and the two layout times.`,
  },
  {
    key: 'reader-and-open-findings',
    prompt: `Lens: a first-time reader, and the follow-up of the first check.
(a) Open the first-check findings file. For every finding with verdict "confirmed" or "partly", decide whether version 2 fixed it. List only those that are still open or were fixed wrongly, with the place in version 2.
(b) Read version 2 as an engineer who has never seen the project. Rules: no idioms or uncommon words; one claim per sentence; at most 25 words per sentence, 3 sentences per bullet, 8 words per parenthesis; every code name, abbreviation and metric is defined at first use or in "Words used here"; numbers have units; estimates carry "est."; every [RefN] exists and every reference is cited; the page starts with a "Short version" of at most 3 sentences that a newcomer can follow; never "ctx N"; banned words: convoy, refund, "in disguise", swept. A script already checks sentence and bullet length. Look for what a script cannot see: a term used before it is defined (name the term and the place), contradictions between two places of the page (compare numbers that appear twice, for example the same factor in the Short version, the top table, section 3 and the figures' text), a "So ..." sentence that does not follow from the sentences before it, table headers that a reader would misread, and facts a reader needs and cannot find.
(c) Check the statements about the design page (what the design assumed or asked for) against /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html and predict.py: for example "The design assumed 2.1 and 3.2 at the working values", "The design estimated 2.7 to 3.5 us for Part 0 and 1.7 to 2.5 us for Part A", "against 0.7 to 1.0 us (est.)", "The design assumed that the rest of the pass gets 2.6 % slower with Part A", "The design took 1.18 and 1.22 times from measurements of the 128-wide kernels on delphi-3bda ... clock ratio of 0.76 to 0.96", "The prediction assumed 2.3 times for the scoring of full pages only", "The design kept it fixed" (the join wait), "The chain kernel also works in windows ... The design ran each half of the state over the whole chain", "The design refused only results that are not finite", "The design asked to clear the 512-bit registers before tile work", the pass rules quoted in the rules table of section 5, and the word-list entries that give model facts (16 key heads and 32 value heads, 24 of 32 layers, 16 query heads and 4 KV heads, 40 attention threads, 16 GDN threads, 2 of them on 4.00 GHz CPUs).
Report at most 20 findings, the most important first.`,
  },
]

const results = await pipeline(
  LENSES,
  l => agent(COMMON + '\n' + l.prompt, { label: `check2:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (found, l) => {
    if (!found || !found.findings.length) return { lens: l.key, checked: found ? found.checked : 'agent failed', findings: [], verdicts: [] }
    return agent(COMMON + `\nAnother checker (lens: ${l.key}) reported the findings below about version 2 of the page. For EACH finding, try to REFUTE it: recompute the number from the raw files, or read the code, the design page or the page text yourself. Verdict "refuted" when the page is right, "partly" when there is a real but smaller problem, "confirmed" when the finding is right. Give a corrected fix when the proposed one is wrong. Copy the "quote" field of each finding into your verdict.\n\nFindings:\n${JSON.stringify(found.findings, null, 1)}`,
      { label: `refute2:${l.key}`, phase: 'Refute', schema: VERDICTS })
      .then(v => ({ lens: l.key, checked: found.checked, findings: found.findings, verdicts: v ? v.verdicts : [] }))
  }
)
return results.filter(Boolean)
