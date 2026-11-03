# Near-tie flip statistics (issue #4444), 2026-10-16

Section 1 (Q1 to Q8) covers the 2026-10-13 p83 pairs and the 2026-08-30 record. Section 2 (at the end) covers the ten pairs of the 2026-10-16 campaign.

Short version. The arm change moves the top-1-minus-top-2 logit gap by a median of 0.5 to 1 bf16 notches per step, while the gap itself is a median of 39 to 49 notches, so a flip needs a step whose gap is already within a few notches of zero. Every observed flip sits at such a step: the six flip steps rank 9, 2, 1, 1, 1, 8 of 256 by gap in notches (1 = smallest). The flip model (gap plus a pair movement drawn independently from the measured movements) reproduces every observed flip by construction and, in its predictive form, expects 0.76 to 1.54 flips per 256 steps per pair against 0 to 3 observed, so the observed flip counts are what near-ties plus notch-level numerics produce.

Words used here.

- forced run: a run whose generated token ids are replaced by a fixed list (teacher forcing), so both arms see the same input at every step and their logits can be compared step by step.
- OFF arm / ON arm: the two logs of one pair, as passed to dd_logits_step.py as --off and --on. OFF is the first-named arm (new, fnew, r3x); its top pair defines the margin.
- margin (field margin_off): OFF-arm top-1 logit minus top-2 logit, in logit units; margin_off_ulps is the same in bf16 notches of the top-1 logit.
- ulp (one notch, field ulp_top1_off): the spacing of bf16 numbers at the top-1 logit, 0.0625 for logits in [8,16), 0.125 in [16,32), 0.25 in [32,64); all three occur (field ulp_top1_off, counts in tie_stats.json ulp_top1_values). Pair quantities in ulps use the top-1 notch, so they are half-integers when the top-2 logit lies in the next-lower binade.
- delta_pair (field delta_pair): (ON minus OFF) of the top-1 logit minus (ON minus OFF) of the top-2 logit, i.e. how far the arm change moves the margin; negative = toward a flip.
- flip (field same_top1 == false): the ON arm's top-1 id differs from the OFF arm's top-1 id at that step. Ties go to the lower id (np.argmax, std::max_element).
- TVD (field tvd): total variation distance between the two arms' softmax distributions at the step, 0 = identical, 1 = disjoint.
- frac_changed: fraction of vocabulary logits that differ between the arms at the step; mean_abs_delta: mean |ON - OFF| over the vocabulary.
- pooled_p83: delta_pair values of the five non-control prompt-1024 pairs together (new-vs-newforced excluded, all zero); pooled_all adds the 2026-08-30 prompt-2048 pair.

Pairs (file, arms):

- new-vs-base: new (PR4 ea94e95a, CPU attention) vs base (main 72308ec9, CPU), prompt 1024, 256 steps, observed flips [84] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-new-vs-base.json]
- new-vs-head: new vs head (PR3 dfafd13d, CPU), prompt 1024, 256 steps, observed flips [] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-new-vs-head.json]
- new-vs-newforced: new vs new replayed (A/A control), prompt 1024, control, 256 steps, observed flips [] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-new-vs-newforced.json]
- fnew-vs-fhead: fnew (PR4, FPGA attention) vs fhead (PR3, FPGA), prompt 1024, 256 steps, observed flips [84] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-fnew-vs-fhead.json]
- fnew-vs-fbase: fnew vs fbase (main, FPGA), prompt 1024, 256 steps, observed flips [] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-fnew-vs-fbase.json]
- new-vs-newoff: new vs newoff (PR4, TRON_AMX_DISABLE=1), prompt 1024, 256 steps, observed flips [248] [/home/jhan/workspace/intel-AMX/exec/results/p83-20261013/steps-new-vs-newoff.json]
- r3x-vs-r4x-20260830: r3x (runtron.canon, AMX off) vs r4x (runtron.canon, AMX on), prompt 2048, 2026-08-30, 256 steps, observed flips [22, 37, 145] [/home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4x.json]

## Q1. OFF-arm margin per step (margin_off, margin_off_ulps)

| pair | median (logit) | p10 | p05 | min | median (ulps) | p10 | p05 | min | =0 | <=1 ulp | <=2 | <=4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new-vs-base | 3.875 | 0.5 | 0.1875 | 0.0625 | 39 | 6.5 | 3 | 1 | 0 | 8 | 10 | 21 |
| new-vs-head | 3.875 | 0.5 | 0.1875 | 0.0625 | 39 | 6.5 | 3 | 1 | 0 | 8 | 10 | 21 |
| new-vs-newforced | 3.875 | 0.5 | 0.1875 | 0.0625 | 39 | 6.5 | 3 | 1 | 0 | 8 | 10 | 21 |
| fnew-vs-fhead | 3.875 | 0.5625 | 0.25 | 0 | 39.2 | 6 | 3 | 0 | 1 | 7 | 12 | 22 |
| fnew-vs-fbase | 3.875 | 0.5625 | 0.25 | 0 | 39.2 | 6 | 3 | 0 | 1 | 7 | 12 | 22 |
| new-vs-newoff | 3.875 | 0.5 | 0.1875 | 0.0625 | 39 | 6.5 | 3 | 1 | 0 | 8 | 10 | 21 |
| r3x-vs-r4x-20260830 | 7.25 | 0.75 | 0.3125 | 0 | 48.8 | 7 | 3 | 0 | 2 | 4 | 7 | 18 |

The five prompt-1024 pairs share the OFF arm (new or fnew), so their margin rows repeat by construction. Counts are steps out of n_steps.

## Q2. Pair movement (delta_pair) and vocabulary-wide change per step

| pair | median abs delta_pair (logit) | p95 | max | median (ulps) | p95 | max | neg/zero/pos | mean_abs_delta median / p95 / max | frac_changed median / p95 / max | tvd median / p95 / max |
|---|---|---|---|---|---|---|---|---|---|---|
| new-vs-base | 0.0625 | 0.375 | 6 | 0.5 | 2.62 | 48 | 65/97/94 | 0.0361 / 0.2697 / 1.4129 | 0.801 / 0.984 / 0.997 | 0.0017 / 0.0222 / 0.0559 |
| new-vs-head | 0.0625 | 0.375 | 2.75 | 0.5 | 3 | 22 | 74/113/69 | 0.0363 / 0.2451 / 1.0012 | 0.804 / 0.982 / 0.996 | 0.0012 / 0.0178 / 0.0349 |
| new-vs-newforced | 0 | 0 | 0 | 0 | 0 | 0 | 0/256/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| fnew-vs-fhead | 0.0625 | 0.4062 | 1.125 | 0.5 | 2 | 6 | 57/114/85 | 0.0346 / 0.2087 / 1.4977 | 0.783 / 0.98 / 0.998 | 0.0012 / 0.0167 / 0.0338 |
| fnew-vs-fbase | 0.0625 | 0.375 | 1.5 | 0.5 | 3 | 7 | 51/110/95 | 0.0363 / 0.198 / 1.069 | 0.801 / 0.977 / 0.996 | 0.0015 / 0.0181 / 0.0432 |
| new-vs-newoff | 0.0625 | 0.5 | 5.125 | 1 | 3 | 41 | 90/92/74 | 0.0381 / 0.2359 / 1.3402 | 0.792 / 0.984 / 0.998 | 0.0013 / 0.0226 / 0.0548 |
| r3x-vs-r4x-20260830 | 0.125 | 0.75 | 6.0625 | 1 | 4 | 48.5 | 72/77/107 | 0.0527 / 0.3624 / 1.1311 | 0.86 / 0.982 / 0.998 | 0.0001 / 0.0172 / 0.3583 |

Statistics are over all steps of the pair (flip steps included). The summary block of each json excludes the flip steps from the delta_pair and frac_changed statistics; the cross-check below shows both.

| pair | p95 abs delta_pair: all steps / summary nonflip_p95_abs_delta_pair | median frac_changed: all / summary nonflip_median_frac_changed | max tvd: all / summary max_tvd | identical steps: all / summary n_identical_steps |
|---|---|---|---|---|
| new-vs-base | 0.375 / 0.375 | 0.8012 / 0.8005 | 0.05588 / 0.05588 | 0 / 0 |
| new-vs-head | 0.375 / 0.375 | 0.8039 / 0.8039 | 0.03495 / 0.03495 | 1 / 1 |
| new-vs-newforced | 0 / 0 | 0 / 0 | 0 / 0 | 256 / 256 |
| fnew-vs-fhead | 0.4062 / 0.4125 | 0.7834 / 0.7836 | 0.03378 / 0.03378 | 1 / 1 |
| fnew-vs-fbase | 0.375 / 0.375 | 0.8006 / 0.8006 | 0.04316 / 0.04316 | 0 / 0 |
| new-vs-newoff | 0.5 / 0.5 | 0.7922 / 0.7913 | 0.0548 / 0.0548 | 0 / 0 |
| r3x-vs-r4x-20260830 | 0.75 / 0.75 | 0.8598 / 0.8605 | 0.35826 / 0.35826 | 0 / 0 |

Pooled delta_pair sets:

| pool | n | median abs (logit) | p95 | max | median abs (ulps) | p95 | max | neg/zero/pos |
|---|---|---|---|---|---|---|---|---|
| pooled_p83 | 1280 | 0.0625 | 0.375 | 6 | 0.5 | 3 | 48 | 337/526/417 |
| pooled_all | 1536 | 0.0625 | 0.5 | 6.0625 | 0.5 | 3 | 48.5 | 409/603/524 |

## Q3. Flip model

Deterministic form: flip at step k iff m_k + d_k < 0, or m_k + d_k == 0 and the OFF top-2 id is lower than the OFF top-1 id (lowest id wins an exact tie). Check of the rule at the known flips: step 84 of new-vs-base has m + d = 0 with off_top1 1499 > off_top2 258, so the lower id 258 wins in the ON arm (on_top1 = 258); step 248 of new-vs-newoff has m + d = -0.125 < 0. The model is evaluated on every step and compared with same_top1; it also checks that the ON top-1 is always one of the OFF top pair (no third token overtakes).

| pair | observed flips | model flips | model == observed | ON top-1 always in OFF top pair |
|---|---|---|---|---|
| new-vs-base | [84] | [84] | True | True |
| new-vs-head | [] | [] | True | True |
| new-vs-newforced | [] | [] | True | True |
| fnew-vs-fhead | [84] | [84] | True | True |
| fnew-vs-fbase | [] | [] | True | True |
| new-vs-newoff | [248] | [248] | True | True |
| r3x-vs-r4x-20260830 | [22, 37, 145] | [22, 37, 145] | True | True |

Predictive form: d is drawn independently of m_k from an empirical delta_pair set (the pair's own 256 values, pooled_p83, or pooled_all), in logit units or in ulps (d/ulp vs m/ulp). Expected flips = sum over steps of P(flip_k); P(at least one) and P(count >= observed) come from the exact Poisson-binomial distribution of the flip count over the steps (independence across steps assumed).

| pair | observed | own (logit): expected / P(>=1) / P(>=obs) | own (ulps) | pooled_p83 (logit) | pooled_p83 (ulps) | pooled_all (logit) | pooled_all (ulps) |
|---|---|---|---|---|---|---|---|
| new-vs-base | 1 | 2.15 / 0.9 / 0.9 | 0.76 / 0.55 / 0.55 | 2.4 / 0.92 / 0.92 | 1 / 0.65 / 0.65 | 2.46 / 0.93 / 0.93 | 1.04 / 0.66 / 0.66 |
| new-vs-head | 0 | 3.37 / 0.97 / 1 | 1.54 / 0.8 / 1 | 2.4 / 0.92 / 1 | 1 / 0.65 / 1 | 2.46 / 0.93 / 1 | 1.04 / 0.66 / 1 |
| new-vs-newforced | 0 | 0 / 0 / 1 | 0 / 0 / 1 | 2.4 / 0.92 / 1 | 1 / 0.65 / 1 | 2.46 / 0.93 / 1 | 1.04 / 0.66 / 1 |
| fnew-vs-fhead | 1 | 1.87 / 0.86 / 0.86 | 1.01 / 0.66 / 0.66 | 2.63 / 0.94 / 0.94 | 1.33 / 0.76 / 0.76 | 2.69 / 0.95 / 0.95 | 1.36 / 0.77 / 0.77 |
| fnew-vs-fbase | 0 | 1.91 / 0.87 / 1 | 1 / 0.65 / 1 | 2.63 / 0.94 / 1 | 1.33 / 0.76 / 1 | 2.69 / 0.95 / 1 | 1.36 / 0.77 / 1 |
| new-vs-newoff | 1 | 3.15 / 0.97 / 0.97 | 1.25 / 0.74 / 0.74 | 2.4 / 0.92 / 0.92 | 1 / 0.65 / 0.65 | 2.46 / 0.93 / 0.93 | 1.04 / 0.66 / 0.66 |
| r3x-vs-r4x-20260830 | 3 | 2.31 / 0.92 / 0.41 | 1.36 / 0.78 / 0.14 | 1.98 / 0.88 / 0.31 | 1.21 / 0.73 / 0.1 | 2.03 / 0.89 / 0.33 | 1.23 / 0.74 / 0.11 |

Totals over the six non-control pairs (1536 steps): observed 6 flips; expected 14.76 (own, logit), 6.92 (own, ulps), 14.81 (pooled_all, logit), 7.07 (pooled_all, ulps). For the control pair the own set is all zeros, so its expected count is 0 by construction; its pooled rows show what the model predicts for the same margins under a real arm change. The ulp form is the physically right one: the pair movement is quantized at the notch of the step's own logit (0.0625 to 0.25), and the logit-unit form applies the large movements of 0.25-notch steps to the small-margin steps, which have the 0.0625 notch, so it over-predicts by about 2x (14.8 vs 6.9 expected for 6 observed).

Steps that carry the predicted flip probability (pooled_all, ulps), top 3 per pair:

- new-vs-base: step 20 (margin 1 ulps, p 0.217), step 10 (margin 1 ulps, p 0.062), step 22 (margin 1 ulps, p 0.062); steps with p > 0: 39
- new-vs-head: step 20 (margin 1 ulps, p 0.217), step 10 (margin 1 ulps, p 0.062), step 22 (margin 1 ulps, p 0.062); steps with p > 0: 39
- new-vs-newforced: step 20 (margin 1 ulps, p 0.217), step 10 (margin 1 ulps, p 0.062), step 22 (margin 1 ulps, p 0.062); steps with p > 0: 39
- fnew-vs-fhead: step 248 (margin 0 ulps, p 0.266), step 20 (margin 1 ulps, p 0.217), step 84 (margin 1 ulps, p 0.217); steps with p > 0: 39
- fnew-vs-fbase: step 248 (margin 0 ulps, p 0.266), step 20 (margin 1 ulps, p 0.217), step 84 (margin 1 ulps, p 0.217); steps with p > 0: 39
- new-vs-newoff: step 20 (margin 1 ulps, p 0.217), step 10 (margin 1 ulps, p 0.062), step 22 (margin 1 ulps, p 0.062); steps with p > 0: 39
- r3x-vs-r4x-20260830: step 22 (margin 0 ulps, p 0.266), step 37 (margin 0 ulps, p 0.266), step 7 (margin 1 ulps, p 0.217); steps with p > 0: 40

## Q4. Are the flip-step margins special?

| pair | step | margin (logit) | margin (ulps) | delta_pair (logit / ulps) | rank by margin, 1 = smallest (logit) | steps with margin <= this | rank (ulps) | steps with margin <= this (ulps) |
|---|---|---|---|---|---|---|---|---|
| new-vs-base | 84 | 0.125 | 2 | -0.125 / -2 | 4 | 10 | 9 | 10 |
| fnew-vs-fhead | 84 | 0.0625 | 1 | -0.0625 / -1 | 2 | 5 | 2 | 7 |
| new-vs-newoff | 248 | 0.125 | 1 | -0.25 / -2 | 4 | 10 | 1 | 8 |
| r3x-vs-r4x-20260830 | 22 | 0 | 0 | -0.125 / -1 | 1 | 2 | 1 | 2 |
| r3x-vs-r4x-20260830 | 37 | 0 | 0 | -0.0625 / -1 | 1 | 2 | 1 | 2 |
| r3x-vs-r4x-20260830 | 145 | 0.75 | 3 | -1.5 / -6 | 26 | 29 | 8 | 14 |

Every flip happened at a step whose OFF margin is among the 9 smallest of its 256 margins in notches. The three exact ties (0 ulps) all flipped when the pair moved by -1 ulp. Step 145 of 2026-08-30 is the one flip that needed a movement beyond the p95: margin 3 ulps, movement -6 ulps (the p95 of that pair is 4 ulps). The other flips needed movements of 1 to 2 ulps, inside the median-to-p95 range of the pair movement.

Near-tie steps (OFF margin <= 2 ulps) and what the pair movement did there (delta_pair in ulps; flip marked with *):

- new-vs-base: step 10 m=1 d=-1, step 16 m=2 d=0, step 20 m=1 d=0, step 22 m=1 d=1, step 32 m=1 d=0, step 52 m=1 d=1, step 53 m=1 d=3, step 84 m=2 d=-2*, step 129 m=1 d=0, step 248 m=1 d=-1
- new-vs-head: step 10 m=1 d=-1, step 16 m=2 d=0, step 20 m=1 d=0, step 22 m=1 d=0, step 32 m=1 d=1, step 52 m=1 d=1, step 53 m=1 d=1, step 84 m=2 d=0, step 129 m=1 d=1, step 248 m=1 d=-1
- fnew-vs-fhead: step 10 m=1 d=0, step 15 m=2 d=1, step 16 m=2 d=0, step 20 m=1 d=0, step 21 m=2 d=1, step 22 m=1 d=0, step 32 m=1 d=1, step 53 m=1 d=0, step 69 m=2 d=0, step 84 m=1 d=-1*, step 129 m=2 d=0, step 248 m=0 d=0
- fnew-vs-fbase: step 10 m=1 d=0, step 15 m=2 d=1, step 16 m=2 d=0, step 20 m=1 d=0, step 21 m=2 d=0, step 22 m=1 d=0, step 32 m=1 d=1, step 53 m=1 d=2, step 69 m=2 d=0, step 84 m=1 d=0, step 129 m=2 d=0, step 248 m=0 d=1
- new-vs-newoff: step 10 m=1 d=1, step 16 m=2 d=1, step 20 m=1 d=0, step 22 m=1 d=1, step 32 m=1 d=0, step 52 m=1 d=2, step 53 m=1 d=1, step 84 m=2 d=0, step 129 m=1 d=1, step 248 m=1 d=-2*
- r3x-vs-r4x-20260830: step 7 m=1 d=0, step 17 m=1 d=0, step 22 m=0 d=-1*, step 24 m=2 d=1, step 37 m=0 d=-1*, step 50 m=2 d=0, step 83 m=2 d=0

A near-tie step survives when the movement is 0 or positive, or when the post-movement exact tie keeps the lower id. Steps that reached an exact tie in the ON arm and survived because the OFF top-1 had the lower id: new-vs-base step 10 (ids 548 vs 16359), new-vs-base step 248 (ids 13 vs 624), new-vs-head step 10 (ids 548 vs 16359), new-vs-head step 248 (ids 13 vs 624), fnew-vs-fhead step 248 (ids 13 vs 624). Step 248 of the FPGA arm fnew is an exact tie (ids 13 vs 624, 13 wins) and stayed one in fnew-vs-fhead (movement 0) and widened in fnew-vs-fbase (movement +1 ulp), so it did not flip there.

## Q5. Steps at risk per run

At risk = OFF margin <= the p95 of |delta_pair| of the same pair (a movement that the arm change produces in 1 of 20 steps would close the gap).

| pair | p95 abs delta_pair (logit) | at-risk steps (logit) | p95 (ulps) | at-risk steps (ulps) | max abs delta_pair (logit) | steps with margin <= max |
|---|---|---|---|---|---|---|
| new-vs-base | 0.375 | 22 | 2.62 | 11 | 6 | 156 |
| new-vs-head | 0.375 | 22 | 3 | 19 | 2.75 | 99 |
| new-vs-newforced | 0 | 0 | 0 | 0 | 0 | 0 |
| fnew-vs-fhead | 0.4062 | 23 | 2 | 12 | 1.125 | 44 |
| fnew-vs-fbase | 0.375 | 23 | 3 | 17 | 1.5 | 61 |
| new-vs-newoff | 0.5 | 27 | 3 | 19 | 5.125 | 142 |
| r3x-vs-r4x-20260830 | 0.75 | 29 | 4 | 18 | 6.0625 | 114 |

## Q6. The 2026-08-30 record (prompt 2048, AMX on vs off, runtron.canon)

File /home/jhan/workspace/intel-AMX/exec/results/dd/steps-r4x.json (OFF = r3x forced with r1a.tok, ON = r4x, 256 steps). Flips [22, 37, 145]; margins at the flips: step 22 = 0 ulps (0 logit), pair moved -1 ulps, step 37 = 0 ulps (0 logit), pair moved -1 ulps, step 145 = 3 ulps (0.75 logit), pair moved -6 ulps. Margin median 7.25 logit (48.8 ulps); exact ties 2, <= 1 ulp 4, <= 4 ulps 18. Pair movement median 1 ulp, p95 4 ulps (handoff: 1 and 4). Model reproduces the flips: True; expected flips own/ulps 1.36, pooled_all/ulps 1.23, observed 3. Same pattern as the prompt-1024 pairs: flips sit at the 0-, 0- and 3-ulp margins (ranks 1, 1, 3 of 256), and the arm change moves every other step's logits too (frac_changed median 0.86).

## Q7. Cross-checks

| pair | steps where top-1 differs | steps where top-1 same | steps with all logits identical (frac_changed = 0) | steps with frac_changed >= 0.5 | frac_changed median / min |
|---|---|---|---|---|---|
| new-vs-base | 1 | 255 | 0 | 245 | 0.801 / 0.379 |
| new-vs-head | 0 | 256 | 1 | 233 | 0.804 / 0 |
| new-vs-newforced | 0 | 256 | 256 | 0 | 0 / 0 |
| fnew-vs-fhead | 1 | 255 | 1 | 239 | 0.783 / 0 |
| fnew-vs-fbase | 0 | 256 | 0 | 247 | 0.801 / 0.384 |
| new-vs-newoff | 1 | 255 | 0 | 239 | 0.792 / 0.368 |
| r3x-vs-r4x-20260830 | 3 | 253 | 0 | 240 | 0.86 / 0.37 |

The top token differs only at the listed flip steps; at every other step the two arms pick the same id (steps_top1_same = 256 minus flips). The logits are not bit-identical: the median step has about 80 % of the vocabulary changed by at least one notch in the prompt-1024 pairs. new-vs-head and fnew-vs-fhead each have exactly one step with all logits identical (field n_identical_steps = 1), so 'never identical' holds at 255 of 256 steps for those two pairs and at 256 of 256 for the others. The control pair new-vs-newforced is identical at all 256 steps.

## Q8. Scale

| pair | median abs delta_pair / median margin (logit) | same ratio in ulps |
|---|---|---|
| new-vs-base | 0.0161 | 0.0128 |
| new-vs-head | 0.0161 | 0.0128 |
| new-vs-newforced | 0 | 0 |
| fnew-vs-fhead | 0.0161 | 0.0127 |
| fnew-vs-fbase | 0.0161 | 0.0127 |
| new-vs-newoff | 0.0161 | 0.0256 |
| r3x-vs-r4x-20260830 | 0.0172 | 0.0205 |

For new-vs-base: median |delta_pair| 0.0625 logit vs median margin 3.875 logit, ratio 0.0161; in notches 0.5 vs 39 ulps. The typical pair movement is about 1/60 of the typical gap, so only the few steps whose gap is itself a few notches can flip.

## Reproduce

```
python3 /home/jhan/workspace/intel-AMX/exec/td-20261016/tiestats/tie_stats.py
```
Outputs tie_stats.json (every number above plus per-step prediction details) and tie_stats.md next to the script. Inputs are read only.

# Section 2. The 2026-10-16 campaign (10 new pairs, same cell: qwen3-4b tp2, prompt 1024, 256 forced steps)

Short version. Ten new pairwise comparisons from /home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-<off>-vs-<on>.json, all arms fed the same 256 token ids. Two pairs are bit-identical controls (baseoff-vs-pocoff, clean-vs-baseoff); the other eight show 9 flips in 2048 steps, all at steps 20, 84 or 248, where the OFF margin is 0 to 2 notches. The flip model reproduces every flip; its predictive form expects 12.38 flips over the eight pairs (own movements, ulps) or 12.41 (pooled), against 9 observed; P(count <= 9) = 0.18 under the pooled model, so the observed count is on the low side of the model and inside it.

Arms: base (main 72308ec9, AMX on); baseoff (main, TRON_AMX_DISABLE=1); new (PR4 ea94e95a, AMX on); newoff (PR4, TRON_AMX_DISABLE=1); poc (runtron.poc, AMX on); pocoff (runtron.poc, TRON_AMX_DISABLE=1); trunc (runtron.trunc, AMX on); clean (runtron.clean, AMX on). The OFF arm of a pair is the first-named one. new-vs-newoff is a re-run of the section 1 pair with tonight's logs.

## S2.1 Pairs, margins (margin_off / margin_off_ulps of the OFF arm) and flips

| pair | observed flips | model == observed | median margin (logit) | p05 | min | median (ulps) | p05 | min | =0 | <=1 ulp | <=2 | <=4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-vs-poc | [84] | True | 3.9062 | 0.25 | 0 | 39 | 3 | 0 | 4 | 6 | 10 | 22 |
| baseoff-vs-pocoff | [] | True | 4 | 0.25 | 0 | 39.2 | 3 | 0 | 3 | 7 | 11 | 20 |
| clean-vs-baseoff | [] | True | 4 | 0.25 | 0 | 39.2 | 3 | 0 | 3 | 7 | 11 | 20 |
| base-vs-new | [84] | True | 3.9062 | 0.25 | 0 | 39 | 3 | 0 | 4 | 6 | 10 | 22 |
| new-vs-newoff | [248] | True | 3.875 | 0.1875 | 0.0625 | 39 | 3 | 1 | 0 | 8 | 10 | 21 |
| newoff-vs-trunc | [248] | True | 3.9375 | 0.25 | 0 | 39 | 3 | 0 | 1 | 3 | 11 | 23 |
| new-vs-trunc | [] | True | 3.875 | 0.1875 | 0.0625 | 39 | 3 | 1 | 0 | 8 | 10 | 21 |
| baseoff-vs-base | [20, 84] | True | 4 | 0.25 | 0 | 39.2 | 3 | 0 | 3 | 7 | 11 | 20 |
| baseoff-vs-newoff | [20, 248] | True | 4 | 0.25 | 0 | 39.2 | 3 | 0 | 3 | 7 | 11 | 20 |
| clean-vs-new | [20] | True | 4 | 0.25 | 0 | 39.2 | 3 | 0 | 3 | 7 | 11 | 20 |

The ON top-1 is one of the OFF top pair at every step of every pair (field on_top1_always_in_off_top_pair = true in tie_stats.json).

## S2.2 Pair movement (delta_pair) and vocabulary-wide change

| pair | median abs delta_pair (logit) | p95 | max | median (ulps) | p95 | max | neg/zero/pos | identical steps | frac_changed median | tvd median / max |
|---|---|---|---|---|---|---|---|---|---|---|
| base-vs-poc | 0 | 0.5 | 1.75 | 0 | 2.5 | 10 | 64/144/48 | 64 | 0.739 | 0 / 0.0305 |
| baseoff-vs-pocoff | 0 | 0 | 0 | 0 | 0 | 0 | 0/256/0 | 256 | 0 | 0 / 0 |
| clean-vs-baseoff | 0 | 0 | 0 | 0 | 0 | 0 | 0/256/0 | 256 | 0 | 0 / 0 |
| base-vs-new | 0.0625 | 0.375 | 2.75 | 0.75 | 2.12 | 11 | 89/94/73 | 0 | 0.801 | 0.0017 / 0.0559 |
| new-vs-newoff | 0.0625 | 0.5 | 5.125 | 1 | 3 | 41 | 90/92/74 | 0 | 0.792 | 0.0013 / 0.0548 |
| newoff-vs-trunc | 0.0625 | 0.2812 | 0.875 | 0.5 | 2 | 5 | 70/111/75 | 0 | 0.78 | 0.0011 / 0.0486 |
| new-vs-trunc | 0.0625 | 0.625 | 5.25 | 1 | 3 | 42 | 88/85/83 | 0 | 0.816 | 0.0015 / 0.0571 |
| baseoff-vs-base | 0.0625 | 0.5 | 2.625 | 0.5 | 2 | 10.5 | 70/100/86 | 0 | 0.811 | 0.0013 / 0.0316 |
| baseoff-vs-newoff | 0.0625 | 0.375 | 2.625 | 0.5 | 2.12 | 12 | 85/113/58 | 0 | 0.796 | 0.0012 / 0.0368 |
| clean-vs-new | 0.0625 | 0.375 | 2.875 | 1 | 3 | 23 | 80/101/75 | 0 | 0.814 | 0.0017 / 0.0352 |

Pooled movement set pooled_td (the eight non-identical pairs, n = 2048): median |delta_pair| 0.0625 logit / 0.5 ulps, p95 0.5 / 3, max 5.25 / 42; signed neg/zero/pos 636/840/572. base-vs-poc has 64 identical steps (the first 64, frac_changed = 0), so its own movement set is 25 % zeros.

## S2.3 Flip model: expected vs observed

| pair | observed | own (ulps): expected / P(>=1) / P(>=obs) | own (logit) | pooled_td (ulps) | pooled_td (logit) | at-risk steps (margin <= p95 abs delta_pair, ulps) |
|---|---|---|---|---|---|---|
| base-vs-poc | 1 | 1.6 / 0.83 / 0.83 | 2.84 / 0.95 / 0.95 | 1.92 / 0.89 / 0.89 | 2.93 / 0.96 / 0.96 | 10 |
| baseoff-vs-pocoff | 0 | 0 / 0 / 1 | 0 / 0 / 1 | 1.72 / 0.86 / 1 | 3.03 / 0.97 / 1 | 3 |
| clean-vs-baseoff | 0 | 0 / 0 / 1 | 0 / 0 / 1 | 1.72 / 0.86 / 1 | 3.03 / 0.97 / 1 | 3 |
| base-vs-new | 1 | 2.11 / 0.92 / 0.92 | 2.98 / 0.97 / 0.97 | 1.92 / 0.89 / 0.89 | 2.93 / 0.96 / 0.96 | 10 |
| new-vs-newoff | 1 | 1.25 / 0.74 / 0.74 | 3.15 / 0.97 / 0.97 | 1.05 / 0.67 / 0.67 | 2.58 / 0.94 / 0.94 | 19 |
| newoff-vs-trunc | 1 | 0.94 / 0.65 / 0.65 | 1.43 / 0.78 / 0.78 | 1.31 / 0.77 / 0.77 | 2.34 / 0.92 / 0.92 | 11 |
| new-vs-trunc | 0 | 1.4 / 0.77 / 1 | 3.17 / 0.97 / 1 | 1.05 / 0.67 / 1 | 2.58 / 0.94 / 1 | 19 |
| baseoff-vs-base | 2 | 1.55 / 0.82 / 0.48 | 2.59 / 0.94 / 0.76 | 1.72 / 0.86 / 0.54 | 3.03 / 0.97 / 0.84 | 11 |
| baseoff-vs-newoff | 2 | 1.83 / 0.88 / 0.58 | 3.23 / 0.97 / 0.87 | 1.72 / 0.86 / 0.54 | 3.03 / 0.97 / 0.84 | 11 |
| clean-vs-new | 1 | 1.7 / 0.86 / 0.86 | 3.04 / 0.97 / 0.97 | 1.72 / 0.86 / 0.86 | 3.03 / 0.97 / 0.97 | 17 |

Sum over the eight non-identical pairs (2048 steps): observed 9; expected 12.38 (own, ulps), 12.41 (pooled_td, ulps), 22.44 (own, logit), 22.44 (pooled_td, logit). Exact distribution of the summed count under pooled_td/ulps: P(>= 9) = 0.897, P(<= 9) = 0.179. Without the repeated new-vs-newoff (seven pairs, 1792 steps): observed 8, expected 11.13 (own, ulps) / 11.36 (pooled_td, ulps), P(>= 8) = 0.906. The observed count is below the expectation and inside the model's range (P(<= observed) about 0.2); the ulp form of the model is the right one (section 1, Q3), and the logit form over-predicts by about 2x for the same reason as before.

## S2.4 Steps 20, 84 and 248 across every pair of the cell

Margin of the OFF arm in ulps (m) and movement in ulps (d) at the three steps where flips occur; flip marked with *. The p83 pairs of section 1 (same cell, 2026-10-13 logs) are listed below the new ones for comparison.

| pair | step 20: m / d / OFF ids | step 84: m / d / OFF ids | step 248: m / d / OFF ids |
|---|---|---|---|
| td/base-vs-poc | 1 / 0 / 2566 vs 327 | 0 / -1* / 258 vs 1499 | 0 / 0 / 13 vs 624 |
| td/baseoff-vs-pocoff | 0 / 0 / 327 vs 2566 | 2 / 0 / 1499 vs 258 | 0 / 0 / 13 vs 624 |
| td/clean-vs-baseoff | 0 / 0 / 327 vs 2566 | 2 / 0 / 1499 vs 258 | 0 / 0 / 13 vs 624 |
| td/base-vs-new | 1 / 0 / 2566 vs 327 | 0 / -2* / 258 vs 1499 | 0 / 1 / 13 vs 624 |
| td/new-vs-newoff | 1 / 0 / 2566 vs 327 | 2 / 0 / 1499 vs 258 | 1 / -2* / 13 vs 624 |
| td/newoff-vs-trunc | 1 / 0 / 2566 vs 327 | 2 / -1 / 1499 vs 258 | 1 / -2* / 624 vs 13 |
| td/new-vs-trunc | 1 / 0 / 2566 vs 327 | 2 / -1 / 1499 vs 258 | 1 / 0 / 13 vs 624 |
| td/baseoff-vs-base | 0 / -1* / 327 vs 2566 | 2 / -2* / 1499 vs 258 | 0 / 0 / 13 vs 624 |
| td/baseoff-vs-newoff | 0 / -1* / 327 vs 2566 | 2 / 0 / 1499 vs 258 | 0 / -1* / 13 vs 624 |
| td/clean-vs-new | 0 / -1* / 327 vs 2566 | 2 / 0 / 1499 vs 258 | 0 / 1 / 13 vs 624 |
| p83/new-vs-base | 1 / 0 / 2566 vs 327 | 2 / -2* / 1499 vs 258 | 1 / -1 / 13 vs 624 |
| p83/new-vs-head | 1 / 0 / 2566 vs 327 | 2 / 0 / 1499 vs 258 | 1 / -1 / 13 vs 624 |
| p83/fnew-vs-fhead | 1 / 0 / 2566 vs 327 | 1 / -1* / 1499 vs 258 | 0 / 0 / 13 vs 624 |
| p83/fnew-vs-fbase | 1 / 0 / 2566 vs 327 | 1 / 0 / 1499 vs 258 | 0 / 1 / 13 vs 624 |
| p83/new-vs-newoff | 1 / 0 / 2566 vs 327 | 2 / 0 / 1499 vs 258 | 1 / -2* / 13 vs 624 |

Reading the table. Each of the three steps is a near-tie between the same two ids in every arm of the cell: step 20: ids 327 and 2566; step 84: ids 258 and 1499; step 248: ids 13 and 624 (one id pair per step, 3 pairs in all). The OFF margins at the flips are 0, 1, 2 notches and the movements at the flips are -2, -1 notches, the median-to-p95 range of the pair movement; no flip required a movement outside that range. Which arm is called OFF decides the sign: an arm that holds the pair at margin 0 with the lower id first survives a 0 movement and flips on -1 notch (step 20 in baseoff, clean; step 248 in baseoff), and an arm that holds it at 1 or 2 notches flips only when the movement is at least that large (step 84 in new, baseoff; step 248 in new, newoff).

