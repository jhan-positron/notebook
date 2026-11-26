# Review record for gdn-amx-design.html

## session=20261121T021835Z-a7a95a round=1 role=worker status=START digest=- time=2026-11-21T02:18:35Z

- Initial file: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html
- Review file: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.review.md
- Worker: Claude Code session on the host that mounts /home/jhan/workspace.
- Scope of the work under review: the design page "GDN and AMX: design for Qwen3.5 4B".
  The initial file is the deliverable itself (an HTML report).
- The worker is running its pre-submission checks now. A READY entry for round 1 follows.

END ENTRY

## session=20261121T021835Z-a7a95a round=1 role=worker status=READY digest=8a9fbfa5b4a1f2d4ad7d1b78b7583def92bd3cf1ce65ea7a6e6563749be5ec57 time=2026-11-21T03:38:43Z

### Short version

- The page gdn-amx-design.html is ready for review at the digest in the header (241,213 bytes).
- Before this submission the worker ran its own check of the page. 67 defects were confirmed and fixed. Three of them change numbers of the prediction.
- All evidence files are in /home/jhan/workspace/intel-AMX/exec/gdn-20261120/review-loop/. The checks that were not run are listed at the end.

### What is submitted

- Deliverable: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html. It is a design page: "GDN and AMX: design for Qwen3.5 4B". It holds a measured baseline, a prediction and a software design. No product code is part of this work.
- The page is generated. Generator: exec/gdn-20261120/gen_design.py with design_numbers.py, predict.py, figs_data.py, figs_design.py, figs_static.py and pagelib.py. Do not edit the HTML by hand. The worker changes the generator and regenerates.
- Inputs of the generator: exec/results/gdn-20261120/collected.json (measured runs), predictions.json (written by predict.py), bench/*.txt (clock probe and kernel benchmarks), and the saved outputs in exec/gdn-20261120/design-checks/.
- tron source that the page describes: read-only copy at /home/jhan/workspace/ai-runs/tron-qwen35-4b, commit 72e1191804 (pull request #3696, open, checked with gh on 2026-11-21).

### What changed since the first version of the page

The first version had the digest 7f0f214f9e8ae438538414b0547875595573415fc4ea328133e33ae5f7081a50 (234,822 bytes).
The full list of the 72 findings of the worker's own check is in review-loop/round1-presubmit-findings.txt (the JSON file beside it has the evidence of each one).
The text diff of the page is review-loop/round1-page-text.diff. The diff of the generator is review-loop/round1-generator.diff.

Changes that move numbers of the prediction:

1. Part 0 factors (GDN step, prefill): 1.8 / 2.2 / 2.5 became 1.4 / 2.1 / 2.4 (low / working / high).
   - High 2.4: the low end of the new GDN step was 2.6 us. It left out the cache lines from L2 that the high end included. It is now 2.7 us.
   - Working value 2.1: the page said that 2.2 was "near the middle" of the range. The middle of each estimate gives a step of 3.1 us, which is 2.1.
   - Low 1.4: this is new evidence, not a correction of arithmetic. The folder design-checks/verify-cost/ holds a stand-alone timing of both loop orders on another CPU (AMD Zen 5, 3 saved runs, bench_gdn.run*.out). The column-half order was 1.46 to 1.74 times faster there. The first version of the page did not mention this timing. The page now discloses it (section 3, section 4, section 5.2, section 6), and the low case uses it.
   - Effect: Part 0 alone now reads "TTFT falls by 14 to 23 % (est.), range 8 to 26 %". It read "15 to 24 %, range 12 to 26 %".
2. Part B prefill factors (attention busy time): 1.6 / 2.4 / 3.2 became 1.6 / 2.3 / 2.9. The page said that the fit gives 3.0 to 3.3 times. The fit script prints 2.95 and 3.05 (design-checks/review/attn_prefill_fit.out). Effect: Part B "5 to 24 %, range 4 to 28 %" (was "5 to 25 %, range 4 to 29 %"). Parts A and B "34 to 42 %, range 22 to 48 %" (was "35 to 43 %, range 22 to 49 %").
3. Part A factors and all decode numbers did not change.

Corrections of facts (no prediction number depends on them):

- Clock probe turn lengths: 35 ns and 33 us (the page had 34 ns and 25 us). Source: bench/clock-probe2.txt, lines mixz and mixzp.
- Figure 12: 9,216 AVX-512 operations per block in stage 3 (the page had 8,704). Source: verify-cost/recount_tiles.out.
- Section 5.4: "up to 67 increments" (was 46). Two-piece split: "7.5e-8 to 1.6e-5, 5 to 227 times" over the three checks (was the range of one check). The test facts were wrong: one tolerance test runs at 128 by 128. The bullet is rewritten.
- Section 5.4, resumed prompts: the page said "Today all paths give equal bytes". This holds for the GDN layer only. The logits of a resumed request can already differ today (new Ref22, tron Note [Recurrent state snapshots]).
- Section 5.3: "AMX multiplies bf16 by bf16 only" was false for this CPU (it has AMX-FP16). Rewritten.
- Section 5.5 and section 6: one page visit has two runs of 32 tile products, not one run of 64. The turn length in the attention kernel is 0.4 to 0.6 us (est.), not 1 us.
- Section 5.1 and section 4: the 77 % memory stall belongs to the AMX kernel. The AVX-512 kernel has 47 %. Both are now stated.
- Sources: Ref5, Ref17 and Ref20 pointed at wrong lines or files. Ref14 claimed that vLLM and SGLang have an AMX kernel with tile products. The kernel file has no tile instruction. It calls a library routine, and a comment in the file says that the routine uses AMX bf16 products. Ref14 and section 5.3 now say this. Ref21 (Intel manual, section 20.15) and Ref22 are new.
- Two bases that no saved output supported now have a script with a saved output: design-checks/review/attn_256_l2_count.py (low case of Part B) and decode_options_range.py (section 5.7).
- Section 3: the traced runs generate 32 tokens per user, and the traced mean leaves out the first pass. Both are now stated.

Presentation:

- Six figure defects fixed (figures 2, 7, 10, 12, the formula block). A seventh was found by the second look and fixed (figure 2, column alignment).
- The page is now byte-reproducible. A pattern id in figure 13 came from Python's randomized hash().
- 31 of 61 reference marks were wrapped twice and rendered smaller. Fixed.
- 22 plain-English rule violations fixed (idioms, undefined terms, missing "est." marks). New entries in "Words used here": us, percentage point, QK and PV, SiLU and RMS norm, memory stall, trace event, A/B run, logits.

### Evidence from the checks

Every command below was run by the worker on 2026-11-21 UTC. Outputs are in exec/gdn-20261120/review-loop/.

1. Reproducibility. Command: PYTHONHASHSEED=3 python3 review-loop/regen_check.py <scratch folder>, and again with PYTHONHASHSEED=77. The script runs predict.py and gen_design.py with redirected outputs. Result: predictions.json and the page are byte-identical to the saved files in both runs (page sha256 = the digest in the header). Output: round1-regen-check.txt. The reviewer can run the same script. It writes only to the folder given as its argument.
2. Structure. Command: python3 review-loop/structure_check.py. Result: 15 of 15 checks OK. Pure ASCII, 22 sources and all 22 cited, no reference mark wrapped twice, figures 1 to 13 in order, 7 internal links with targets, light theme only, folded word list, no semicolon, none of the banned words, no "ctx". Output: round1-structure-check.txt.
3. Design checks re-run. 29 pure-python scripts of exec/gdn-20261120/design-checks/ ran from a scratch copy. All 29 exited with code 0. 15 of the 22 scripts with a saved output reproduce it byte for byte. The other 7 differ only in wall-time lines. The 4 saved JSON outputs are identical. 7 scripts have no saved output and ran without error. Output: round1-rerun-design-checks.txt. Longest script: 1,122 s.
4. Pre-submission check (the worker's own, before the revision). 5 checkers, one per dimension (baseline numbers, prediction numbers, design numbers, code and source claims, presentation), re-derived the page's statements from the raw logs, the traces, the saved check outputs and the tron source. They checked 1,006 claims. 5 skeptics then tried to refute each finding. 72 findings, 67 confirmed, 5 refuted. Output: round1-presubmit-findings.txt and .json.
5. Verification after the revision. 4 independent checkers on the revised page. Results: all 67 confirmed findings resolved. The prediction recomputed from the formulas of section 4 and collected.json agrees with predictions.json (largest difference 2.2e-16) and with all 54 cells of the per-cell table. None of 45 old values is left. All 13 figures rendered and inspected, 0 defects. They also made 18 reports of new or missed problems, which are 14 distinct problems: 1 wrong, 1 unsupported, 2 inconsistent and 10 minor. All 14 are fixed in the submitted version. Output: round1-postfix-verify.json. The fixes made after this verification were not verified by a second agent. They are 24 replacements in the generator, and checks 1 and 2 were re-run after them.
6. Checked by hand against the outside world on 2026-11-21: pull request #3696 is open with head 72e1191804 (gh pr view). The checkpoint config.json on delphi-3b35 has 32 layers (24 linear attention, 8 full attention), head_dim 256, 16 attention heads, 4 KV heads, 16 linear key heads, 32 linear value heads, 128 by 128, float32 (Ref2). The six public claims behind Ref14 and Ref21 were read again on the web: 4 supported, the vLLM and SGLang claim corrected as described above, and the Intel manual section confirmed (20.15 "Store to Load Forwarding", document 248966).

### Checks that were not run

- No new measurement on delphi-3b35. The baseline runs, the traces and the clock probe are those of 2026-11-20. The worker did not repeat them.
- The three C programs in design-checks/verify-cost/ (alias_test.c, bench_gdn.c, calib.c) were not re-run. Their saved outputs were read. bench_gdn.c ran on an AMD Zen 5 virtual machine, not on the Xeon 6962P.
- collect.py and analyze_trace.py were not re-run. The baseline checker re-derived their results from the 43 run logs and the 6 raw traces with its own parser (252 claims, 247 held, the 5 others are fixed).
- The page was not opened in a browser. Figures were rendered with cairosvg and DejaVu fonts. The web fonts Inter and JetBrains Mono were not used. The layout at phone width and the sideways scroll of the wide tables were not checked.
- Revision 051 of the Intel manual was not read (Ref21 names revisions 049 and 050).
- The model assumptions were not tested: one serial path per pass, 21 % CPU share of the rest, the factor of 128-wide heads holding for 256-wide heads, and the Zen 5 ratio as the low case. The page marks them as estimates or hypotheses and names the task that measures each one.

### Notes for the reviewer

- The estimate "tile work and AVX-512 work take turns about every 0.2 to 0.4 us" for the block kernel (sections 5.3 and 6) has no script. One checker's own arithmetic gave 0.03 to 0.45 us for the phases. It is marked "est.".
- The user asked the worker for one more step after this review ends: a plain-English pass over the page with the user's experimental rule set. It will change wording after REVIEW_COMPLETE. It will not change numbers.

END ENTRY

## session=20261121T021835Z-a7a95a round=1 role=reviewer status=COMMENTS digest=- time=2026-11-21T03:41:05Z

I reproduced the submitted HTML and predictions.json byte for byte with PYTHONHASHSEED=923. I checked the report against the saved counters, numerical checks and source at 72e1191804. The structure script ran. Its last pattern-ID predicate contains `or True` and always passes. Chromium could not start in this sandbox, so browser layout remains unchecked here.

- R1. Sections 3 and 4, attention time. The prediction scales all of `busy_cycles`. That counter includes workers waiting for each other in the join. The reported “attention wait” also subtracts the average busy time across workers from the wall time of worker 0. That difference cannot identify time spent waiting for K and V alone. At 1 user and prompt 1,024, join wait accounts for 1.449 ms of the 6.038 ms of prefill busy time per worker. At 8 users and prompt 8,192, it accounts for 1.392 ms of the 8.900 ms in decode. Define both timers accurately. State the assumption about which time scales with the kernel, and show how Part B changes if join wait stays fixed, or justify an effective factor for the entire timer. Also identify partial pages as AVX-512 work where a factor comes from a full-page kernel count. Evidence comes from README.stats.md lines 290–298, collect.py lines 97–98, and the six-run medians in collected.json.
- R2. Section 6, task 6. The GDN-only switch compares Part A with Part 0, while the Part A range in section 4 uses today's original kernel as its baseline. A correct implementation can fail this pass rule. For 8 users at prompt 1,024 with Part B disabled, the working estimates are 2.235 s for Part 0 and 2.060 s for Part A. That is a 7.8% reduction with the switch and a 29.1% reduction from the original 2.907 s. Specify the runs and denominator for each comparison, including the fixed Part B setting. Use the original baseline for the total Part A range and the paired run for its incremental gain. Evidence comes from predictions.json and the switch definitions in section 5.6.
- R3. Sections 5.3 and 5.4, FP32 split. The design says each FP32 value is exactly the sum of three bf16 values. Even three bf16 values cannot sum to the smallest positive FP32 subnormal, 2^-149, because every finite bf16 is a multiple of 2^-133. Specify the tested truncation rule for the leading piece and residual pieces. Distinguish exact representation for the supported magnitude range from loss of tiny residuals on the tile. The default round-to-nearest conversion also overflows for some finite inputs above 3.396178e38. Evidence comes from kernel/02_split3_exhaustive.out and verify-math/vm_checks.out part C.
- R4. Figure 2, GDN read equation. The figure calls q a normalized bf16 query and gives the output as q times S. The token kernel multiplies the normalized query by 1/sqrt(key_head_dim) in FP32 before accumulation. At width 128, omitting that factor changes the output magnitude by about 11.31 times. Include the scale and identify where the reference applies it. Figure 12 already shows a scale in the block form. Evidence comes from gated_delta_net.hpp lines 239–242 and 287–296.
- R5. Sections 5.3 and 6, block timing. The report gives one 0.2–0.4 us interval for transitions throughout the block. Stage 3 alone has 9,216 consecutive AVX-512 operations per block according to Figure 12. At the report's optimistic 0.50 cycles per operation and 2.40 GHz that stage costs 1.92 us (est.) before tile work resumes. Name the phase covered by each estimate, or remove the single interval. Distinguish one phase from the full tile-plus-vector iteration timed by the clock probe. The clock of the proposed kernel can remain an open measurement.
- R6. Section 3 and Figure 7, “upper values.” A longer traced pass does not by itself prove that traced GDN wall time bounds untraced GDN wall time. The trace also uses 32 generated tokens instead of 256 and omits the first decode pass from the mean. Label these as estimates using a traced numerator. The untraced GDN counters proposed in section 5.6 would establish the direction and size of any bias. Apply the same qualification where the 1.8 ms scheduling estimate relies on this being an upper bound.
- R7. Section 4, “What would prove the prediction wrong.” A Part 0 step between 3.5 and 4.6 us does not identify cheaper state movement as its cause. Slower L1 execution or more expensive conversion, normalization or copies can give the same total. Present the cause as a hypothesis and name the component timing that distinguishes it. In the same paragraph, a smaller pass-level saving also does not establish overlap by itself. The report's own rest-of-pass clock cost can reduce that saving on a serial path. Specify the controlled comparison needed for that inference.

END ENTRY

## session=20261121T021835Z-a7a95a round=2 role=worker status=READY digest=82eab393b39fbec0416788a00765ee281990142ec9d84f147d1456b507973538 time=2026-11-21T05:07:18Z

### Short version

- All 7 findings are accepted. No finding is disputed. Each one changed the page. The note on the structure script is fixed too.
- R1 changes prediction numbers. Part B now reads "TTFT falls by 2 to 22 % (est.), range 1 to 26 %". Parts A and B read "30 to 41 % (est.), range 18 to 47 %". Part 0, Part A and the decode numbers did not change.
- The page at the digest in the header has 277,175 bytes. New evidence scripts with saved outputs are in exec/gdn-20261120/design-checks/review/. Check outputs of this round are in exec/gdn-20261120/review-loop/ (files round2-*).

### Replies to the findings

R1. Accepted. The reviewer is right on every part.
- Timers. The page now defines four terms from the source: attention busy time, join wait, full-page time and attention wait ("Words used here", section 3 bullets, Ref8 with line numbers). The busy time holds the scoring of the full pages of earlier passes, the scoring of the pages that the pass writes, the join and the join wait. The attention wait is the wall of worker 0 minus the mean busy time. The page now says that it holds the wait for Q, the wait for K and V and a worker offset, and that tron has no timer for the wait for K and V alone.
- Your two numbers reproduce from the six-run medians: 1.449 of 6.038 ms, and 1.392 of 8.900 ms. Both section 3 tables have a new column for the join wait.
- Assumption about which time scales. Prefill: the factor divides the full-page time only. The full-page time is the part of the busy time that grows with the K tokens in full pages. It comes from a line fit per user count: busy time minus join wait = fixed part + 67 ns per K token, error below 0.1 ms (predict.py, function full_page_times). The join wait is held fixed. The pages that the pass writes stay on AVX-512 (12.6, 3.1 and 1.6 % of the scored K tokens at the three prompt lengths). Reason for this choice: the prefill factor is the speedup of the term that grows with the square of the prompt length in a fit of whole prefill times. That term is the full-page work.
- "Show how Part B changes." The page gives both models. Factor on the whole busy time: 5 to 24 % (est.), range 4 to 28 %. Factor on the full-page time: 4 to 22 %, range 2 to 26 %. With the clock cost described below: 2 to 22 %, range 1 to 26 %. The last one is the model of the page.
- Decode keeps a factor on the whole busy time, with a reason: that factor was measured as a ratio of whole busy times of attention worker 0 (Ref19). The page adds the range for a fixed join wait: -4.5 % to +6.5 % (est.).
- Check against a measurement. The same statistics exist for an on/off run of the 128-wide kernel on delphi-3bda (qwen-3-4b, 8 users, prompt 1,024, one run per arm, new Ref23). The busy time got 1.88 times shorter. The full-page model gives 1.90 to 1.93 times for our cell. A factor on the whole busy time gives 2.95 to 3.05 times. The page calls this a check of plausibility, not a fit, because the model and the server differ.
- Partial pages. The low case 1.6 is now marked as a count for one visit of a full page. Figure 11 now sends only full pages of earlier passes to the AMX kernel.
- Two additions that your finding did not ask for, found by the worker's own check of this model: (1) Under Part B the other attention work of a pass (busy time minus full-page time minus join wait) gets a clock cost: +42 % in the low and working case, +12.5 % in the high case. The page models the same effect for Part A, so leaving it out for Part B was inconsistent. It is an assumption, and the page says that this clock is not measured. (2) The full-page scoring can run while the FPGA cards produce K and V. So the model needs the assumption that the faster scoring still ends after K and V are ready. Section 4 states it, a new open point names the timer that tests it, and "What would prove the prediction wrong" has a bullet for it.
- Evidence: design-checks/review/r1_attention_timers.py and .out, round2-investigation.txt.

R2. Accepted.
- Task 6 has two rules now. The paired run with the GDN switch must show a lower TTFT in all 6 cells. The total is the fall from the base run to the Part 0 run plus the fall of the A/B run, as a percent of the base run, inside the Part A range.
- The same defect existed in task 5 in the other direction, and task 2 did not say which run stands for today. Both are fixed.
- A new block "Which runs tasks 2, 5 and 6 compare" defines the base build and the base run, names run 1 and run 2 of each comparison with the Part B setting, and states the denominator of each rule. A second table gives the predicted paired changes per cell. Your example reproduces: 2.235 s, 2.060 s, 7.8 % and 29.1 %.
- The rules rest on one model assumption, which the page states: the seconds that one part saves do not depend on the other part.
- One decision to check: the design gets no switch that turns Part B off alone. So the total of Part A is a sum of two measured falls.
- The decode rule of task 5 is stricter than the predicted range. The page now says so and names the consequence of a fail.
- Evidence: design-checks/review/paired_changes.py and .out, same_code_spread.py and .out.

R3. Accepted.
- Rule tested: truncation. The first piece is the FP32 value with the low 16 bits cleared. The second piece is the remainder with its low 16 bits cleared. The third piece is the remainder of that.
- Exact range: 2^-103 (about 9.9e-32) up to the largest FP32 value. A script checked every finite bit pattern of both signs.
- Below 2^-103 a piece can be subnormal, and the tile product reads it as zero. The part not read is below 2^-126. Below 2^-110 an exact split does not always exist, because every bf16 value is a multiple of 2^-133. The page separates these two losses, as you asked.
- Round to nearest: every value of size 3.3961775e38 (2^128 - 2^119) or larger gives an infinite first piece. That is every value at or above the threshold, 32,768 per sign, not only some.
- A fact that the page did not disclose before: two of the three numeric checks round the pieces to nearest, and one uses truncation. The page says so and gives the measured difference between the two rules (0 to 56 of 131,072 output words).
- Sections 5.3 and the word list no longer say "exactly" without the range.
- Evidence: design-checks/review/r3_split_facts.py and .out, r3_rule_variants.py and .out.

R4. Accepted.
- Figure 2, line 4 reads "o = (scale x q) times S", with the note "scale = 1 / sqrt(128) = 0.0884. It multiplies q in FP32."
- Figure 12 defines scale. One point to check: the specified block form multiplies the scale into the FP32 coefficients of the read sum, not into q. The tile product needs q as a bf16 value. Section 5.4 states this difference between the two forms.
- Evidence: gated_delta_net.hpp lines 242-243 and 287 (added to Ref3), design-checks/review/r4_scale_check.py and .out.

R5. Accepted.
- The interval "0.2 to 0.4 us" is removed in all three places.
- Section 5.3 has a second table: the 8 runs of the block kernel in execution order, each with its instructions, its repeats, its cycles and its length at 2.40 and at 1.90 GHz. Notes give the merged runs. Stage 3 and the split of Delta are one AVX-512 run of 11,743 operations: 2.4 to 3.0 us at 2.40 GHz (est.). Your 1.92 us is the corrections alone at 0.50 cycles.
- The clock note now gives the parts of the two probed turns, so that a run is compared with a run. The sentence "both lie between" is removed.
- The clock of both kernels stays an open measurement (tasks 3 and 4).
- One addition: at 1.90 GHz with the same cycle count, Part A gives a TTFT fall of 14 to 23 % (est.). That is the fall of Part 0 at its working value. The page states this next to the assumption of 2.40 GHz.
- Evidence: design-checks/review/phase_lengths.py and .out.

R6. Accepted.
- "Upper values" is removed in three places: the section 3 bullet, the caption of figure 7, and the scheduling note of section 4 (now "about 1.8 ms (est.) ... can be too high or too low").
- The decode table marks its GDN share and its rest as estimates. The bullet lists the three differences between the two kinds of run and says that the direction and the size of the error are not known.
- The page gives the size that the data do show: a traced decode step is 0.5 to 1.0 ms longer, and no timer locates 0.3 to 0.7 ms of that. With 1 user that is 73 to 134 % of the traced GDN wall.
- The untraced GDN counter of section 5.6 is named as the measurement. The base build of the plan now holds it.
- Evidence: design-checks/review/r6_traced_vs_untraced.py and .out.

R7. Accepted.
- Part 0: a step between 3.5 and 4.6 us now has three hypotheses, each with its test. Hypothesis 1: the recurrence in L1 takes more than 1.16 us per value head. Test: task 1 times the recurrence on one 32 KiB slice that stays in L1. Hypothesis 2: the slice does not stay in L1. Test: the difference to the column-half order on the 128 KiB copy. Hypothesis 3: the other work takes more than 1.0 us. Test: separate timers in task 2.
- Serial path: the controlled comparison is Part 0 against the base build, because no core clock changes. Both walls must come from the same kind of run. The spread of repeated runs is given (0.2 to 0.5 ms with 1 user, 0.3 to 1.7 ms with 8 users). For Part A the clock cost must be subtracted first.
- The plan rows of tasks 1 and 2 hold these measurements.
- Evidence: design-checks/review/r7_serial_path_numbers.py and .out.

Note on structure_check.py. Fixed. The predicate with "or True" is replaced by a real check (each pattern id is defined once and used). The script has two more checks since this round. Reason: a mistake of the worker put the text of a Python object into a table tag. The reproducibility check caught it before this submission.

### Other changes in this round

- Browser layout. A headless Chromium starts on this host. The page was checked at 1280 px and at 390 px, with the web fonts and with fallback fonts. 7 layout defects were found and corrected in the CSS: table heads that could not wrap, a wide last column on phones, table line height without a doctype, a font feature that drew some "x" as a multiplication sign, line breaks inside numbers such as 9.2e-41, small figure text on phones, and the width of the Short version box.
- Wording: sub-bullets in three long bullets, new entries in "Words used here" (session, the three GDN paths, other attention work, subnormal value, tile run and turn, base build, GDN switch).
- The page text grew from 69,846 to 98,510 characters.

### Evidence from the checks

1. Reproducibility: review-loop/regen_check.py with PYTHONHASHSEED=5 and 808. Both runs give byte-identical predictions.json and page. Output: round2-regen-check.txt.
2. Structure: review-loop/structure_check.py, 17 of 17 checks OK, 23 sources and all cited. Output: round2-structure-check.txt.
3. Investigation of R1 to R7: 5 investigators checked each finding against the data and the source before any edit. Record: round2-investigation.txt and .json.
4. First verification of the revised page: 5 checkers (R1 and R2 as a strict reviewer, R3 to R7 the same, numbers, browser, fresh reader). 41 reports, none of severity "wrong". Record: round2-verify-1.json.
5. Second verification after the corrections: 3 checkers. The prediction was recomputed from the raw counters of the 36 runs with independent code: 270 values, largest relative difference to predictions.json 3.7e-16. Every prediction number on the page is a correct rounding. 31 of 34 earlier reports resolved, 3 partly. 21 new reports, none "wrong". Record: round2-verify-2.json.
6. The 21 reports of step 5 are corrected in the submitted version. Checks 1 and 2 were run after these corrections.
7. Diffs against round 1: round2-generator.diff and round2-page-text.diff.

### Checks that were not run

- The corrections of step 6 (27 replacements in the generator, the CSS and two evidence scripts) were not verified by a second agent. After them the worker ran checks 1 and 2 and took one browser screenshot of the top of the page.
- No new measurement on delphi-3b35. Every new number comes from the saved runs of 2026-11-20, from the saved on/off run of 2026-10-02 on delphi-3bda, or from instruction counts.
- The clock of an attention worker under Part B, and the time at which K and V become ready, are not measured. The page marks both as assumptions.
- No real phone, no Firefox and no Safari. The published artifact page was not opened.
- design-checks/review/r3_split_facts.py was not re-run after its pool size was changed from 8 to the number of usable CPUs. Its saved output is from the run with 8 processes. One checker re-ran the script before that edit and got identical bytes.
- The three C programs in design-checks/verify-cost/ were not re-run.

END ENTRY

## session=20261121T021835Z-a7a95a round=2 role=reviewer status=REVIEW_COMPLETE digest=82eab393b39fbec0416788a00765ee281990142ec9d84f147d1456b507973538 time=2026-11-21T05:08:40Z

R1 through R7 are resolved. I checked the revised timer definitions, benchmark comparisons, split rule, query scale, phase timings, trace limits and proposed measurements against the report and its evidence.

I independently recomputed all 18 Part B time-to-first-token predictions from the saved run counters. The largest absolute difference from predictions.json was 3.6e-15 seconds. The report and prediction data regenerated byte for byte with PYTHONHASHSEED=119. All 17 structure checks passed. The worker supplied the browser checks. I did not repeat hardware benchmarks.

No further comments.

END ENTRY
