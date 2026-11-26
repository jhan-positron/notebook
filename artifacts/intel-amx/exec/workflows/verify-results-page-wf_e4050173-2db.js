export const meta = {
  name: 'verify-results-page',
  description: 'Check every claim of the GDN/AMX result page against raw data and code, then try to refute each finding',
  phases: [{ title: 'Check' }, { title: 'Refute' }],
}

const COMMON = `
You verify a draft report page. Be a skeptic: the goal is to find statements that the data or the code do not support.
Page (HTML): /home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html
Page as plain text (same content, easier to read): /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/results-page-text-draft.txt
Generator of the page: /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/gen_report.py (with report_data.py, collect.py, compare.py in the same folder).
Raw data folder R = /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/
  R/rt/<cell>__<arm>__rep<N>.log   one runtron run. Cells q35-tp4-{1u,8u}-p{1024,4096,8192}. Arms base, p0, a0, a, b, ab, orig, nost.
                                    Repetitions 11-13 = session 2 (the main data). Repetitions 21-23 = control runs. Repetitions 1-2 = session 1.
                                    A log holds, per user: "saw X s TTFT", "at Y average tok/s", and at exit the lines "[attn-stats] ..." and "[gdn-stats] ..." (JSON).
  R/load/<run>.txt                  load snapshot taken before the run
  R/rt-results.txt                  one header line per run with the commit of the binary (tip=)
  R/collected.json, R/comparison.json            session 2, made by collect.py and compare.py
  R/collected-session1.json, R/comparison-session1.json, R/collected-controls.json, R/comparison-controls.json
  R/bench/*.txt                     stand-alone benchmarks (task1, slice-variants, task3, task4, stall)
  R/tokens/*.txt                    generated token ids per arm, and summary.txt
  R/unit-tests.txt                  unit-test table
Prediction: /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json (made by /home/jhan/workspace/intel-AMX/exec/gdn-20261120/predict.py). Design page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.
Code: git worktree /home/jhan/workspace/ai-runs/tron-gdn-amx (branch jhan-gdn-amx; base commit 72e1191804).
Words: tron = the inference program; runtron = its command-line tool; GDN = GatedDeltaNet layers; AMX = Intel tile instructions; TTFT = time to first token; arm = one build with one set of switches (base = counters only; p0 = all changes with TRON_AMX_DISABLE=1; b = all changes with TRON_AMX_GDN_DISABLE=1; ab = all changes; a0 = build without Part B with TRON_AMX_GDN_DISABLE=1; a = build without Part B; orig = build of 2026-11-20; nost = counter build with the GDN counters off).
Hard rules:
- Read-only on everything above. Write your own scratch scripts only under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/verify-<your lens>/ .
- Do not use ssh. Do not touch any machine named delphi-*. No network. At most 2 processes at a time.
- Recompute numbers yourself from the raw files with your own code. Do not trust collected.json or the generator; use them only to locate a disagreement.
- Known pending parts, do not report them: commit ids in section 1 and in the unit-test table (a rebuild at the branch head is running), and the "Hypothesis" bullet about token scores in section 8.
- A value on the page is a median over the repetitions of one cell and arm unless the page says otherwise. Rounding to the printed digits is fine. Report a number only when it differs after rounding, or when a sentence claims more than the data shows.
Return findings. Each finding: the section, the exact quote from the page, what is wrong, your evidence (file names and your computed value), and the corrected text or value. Also return "checked": what you verified and found correct (3 to 6 sentences with counts, for example "48 of 48 TTFT cells match").
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
    key: 'ttft-decode',
    prompt: `Lens: time to first token and decode speed. Sections: "Short version", "The changes in one table", "2. How it was measured" (run counts, session times, load table), "3. Time to first token" (table, session comparison), "4. Decode speed" (table and the bullets, including "Why decode gained more than predicted").
Recompute from R/rt/*.log: per run the TTFT (the largest "saw X s TTFT" over the users of the run) and the decode rate (mean of the per-user "average tok/s"); per cell and arm the median over repetitions 11-13. Then the fall in percent of the base run of the same cell, and the decode change in percent. Compare every table cell and every range in a sentence.
Recompute the predicted low / working / high values from predictions.json the way compare.py does, and check that method against the design page section 4 and predict.py (is "fall in percent of the base TTFT" computed against the right base?). Check each "inside / below / above the range" verdict and each "N of 6 cells" count.
For the decode explanation, recompute the attention busy time per decode step from the [attn-stats] decode_like lines (busy_cycles / forwards / tsc_hz / number of attention workers) for arms p0 and b, and check the factors and the example numbers.
Check the load table against R/load/*.txt of the session 2 runs, and the session 1 comparison table against repetitions 1-2.`,
  },
  {
    key: 'counters',
    prompt: `Lens: numbers derived from the counters. Sections: "5. Measurement against the prediction" (the rules table rows for tasks 2, 5 and 6; "Where the GDN step time goes" with its table and figure text; "From the GDN step to the pass"; "Attention with Part B"; the table "All measured parts of a prefill pass"), "7. The new GDN counters" (the sample line, and "What the counters cost" with its table), and the "GDN step" sentences anywhere.
Recompute from the [gdn-stats] and [attn-stats] exit lines of R/rt/*.log (classes prompt_or_mixed = prefill passes, decode_like = decode steps): prefill pass wall, GDN wall per pass (sum of "wall_cycles per op" / forwards), GDN step in microseconds per head token (busy_cycles / all head tokens) and its parts (pre, recurrence, post, start + write), share of head tokens on the AMX path, attention busy time per pass, join wait. Medians over repetitions 11-13. Note: these binaries print the chain path with keys named half_* (half_head_tokens, half_recurrence_cycles).
Check every number in the tables and sentences, the "factor" values (base / arm), the percent-of-fall ratios, and the claims about the design's estimates (compare with the design page text: are the quoted "design (est.)" values really in the design page or in predict.py?).
For the control runs (repetitions 21-23, arms base / nost / orig) recompute the table and the sentences, including "Repetitions of one arm differ by up to X %".
Also judge each sentence that starts with "So": does the data shown on the page really support the conclusion?`,
  },
  {
    key: 'bench-tests-tokens',
    prompt: `Lens: stand-alone measurements, numerics, unit tests and tokens. Sections: "6. A problem found on the way" (and its table), "8. Numerics and tests" (numerics table, token bullets and token table, unit-test bullets, but not commit ids), "9. Stand-alone measurements" (kernel table, burst table, task 4 table and their bullets), and rows 1, 3 and 4 of the rules table in section 5, and the last figure's text.
Read R/bench/*.txt directly (task1-*, slice-variants-*, task3-table-*, task3-clock-*, task3-burst-*, task3-decay-*, task3-zeroupper-*, stall-test.txt, task4-*) and recompute every number, range and ratio on the page. The benchmark sources are in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/bench/ if you need to know what a column means.
For tokens: compare the files R/tokens/p<prompt>__<arm>.txt pairwise yourself and check every count and every "first difference" on the page, and the sentences about repeat runs and about the stand-alone Part B build.
For unit tests: check counts of assertions and test cases against R/unit-tests.txt and the claims about what the new tests cover against the test sources in /home/jhan/workspace/ai-runs/tron-gdn-amx/t/ (t_gated_delta_net.cpp, t_amx_gdn_numerics.cpp, t_gdn_stats.cpp, t_amx_numerics.cpp): for example the listed chain lengths, start positions and head widths, and "Tests cover an infinity, a NaN and a value of 3e38".
Check the claim "AMX bursts on 16 CPUs did not stall a seventeenth CPU. No gap above 0.1 ms was seen" against stall-test.txt.`,
  },
  {
    key: 'code-claims',
    prompt: `Lens: statements about the code and the design. Sections: "1. What was built" (bullets, the table, "Differences from the design"), "7. The new GDN counters" (the descriptive bullets), "8. Numerics and tests" (statements about what the kernels do), "Review of the code", "10. Limits and open points", "Words used here", and "11. Sources" (do the named files exist at the named places?).
Check each statement against the code at the branch head in /home/jhan/workspace/ai-runs/tron-gdn-amx (h/tron/kernels/gated_delta_net.hpp, h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_execution.hpp, h/tron/models/gdn_stats.hpp, h/tron/kernels/amx_gdn_iface.hpp, src/tron/kernels/amx_gdn.cpp, src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/models/self_attention.hpp, h/tron/models/model.hpp, README.stats.md, ingest/src/TronCpp.hs) and against the design page /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.
Examples of what to verify: "Chains of 1 token keep step(), so decode runs today's code"; "The three existing 128-wide kernels are unchanged, byte for byte" (compare the kernel bodies in amx_attn.cpp with git show 72e1191804:src/tron/kernels/amx_attn.cpp); "The kernel now sets both bits for its own work and restores the caller's setting on return"; "With the switch off, a GDN call tests one flag and reads no clock"; "The counters are kept per GDN operation, not per model layer"; the FUSE path; the three switches and when they are read; "16 of 56 threads run GDN"; "24 of the 32 layers are GDN layers"; "a GDN layer has 16 key heads and 32 value heads"; what the design page really asked for in each "difference from the design"; the review counts against /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/understand/review-result.json and review2-result.json; each item of the "not fixed" list (is it really not fixed at the head? is anything missing from the list that the review confirmed and the head still has?).`,
  },
  {
    key: 'reader',
    prompt: `Lens: a first-time reader and the writing rules. Read the whole page as an engineer who has never seen the project.
Rules (the user's "plain English" rules): no idioms, metaphors or uncommon words; one claim per sentence; a sentence has at most 25 words; a bullet or paragraph has at most 3 sentences; a parenthesis has at most 8 words; every code name, abbreviation and metric is defined at first use or in "Words used here"; every number has a unit and, where needed, a meaning; estimates carry "est."; a measured value is never replaced by an estimate; citations sit at the end of a sentence as [RefN] and every reference is cited; the page starts with a "Short version" of at most 3 sentences that a newcomer can follow; never write "ctx N" for a prompt length (write "prompt N"); banned words: convoy, refund, "in disguise", swept.
A script already checks sentence length and bullet length, so focus on what a script cannot see: terms used before they are defined (list each with the place), numbers without unit or meaning, claims with no data behind them on the page, a "So ..." conclusion that does not follow, text that contradicts another part of the page (compare numbers that appear twice), unclear table headers, figure captions that do not say what the reader should see.
Also check completeness against the request that the page answers: (1) what was implemented, (2) the test on the server delphi-3b35 with the load of the shared machine before the runs, (3) the comparison of measured performance with the prediction, (4) the new GDN/AMX counters. Name anything a reader would need and cannot find, for example: which result is the main one, what was not done, what could be wrong with the measurement.
Report at most 25 findings, the most important first.`,
  },
]

const results = await pipeline(
  LENSES,
  l => agent(COMMON + '\n' + l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (found, l) => {
    if (!found || !found.findings.length) return { lens: l.key, checked: found ? found.checked : 'agent failed', findings: [], verdicts: [] }
    return agent(COMMON + `\nAnother checker (lens: ${l.key}) reported the findings below about the page. For EACH finding, try to REFUTE it: recompute the number from the raw files or read the code or the page text yourself. Verdict "refuted" when the page is right, "partly" when there is a real but smaller problem, "confirmed" when the finding is right. Give a corrected fix when the proposed one is wrong. Use the same "quote" field as the finding so the verdicts can be matched.\n\nFindings:\n${JSON.stringify(found.findings, null, 1)}`,
      { label: `refute:${l.key}`, phase: 'Refute', schema: VERDICTS })
      .then(v => ({ lens: l.key, checked: found.checked, findings: found.findings, verdicts: v ? v.verdicts : [] }))
  }
)
return results.filter(Boolean)
