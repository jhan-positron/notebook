A. Per-layer records (results/td-20261016/layers-<pair>.json + .csv; units: counts, rel_l2 = relative L2 ratio, frac = fraction, ulps = bf16 ulps)

| pair | keys | over | first_over key | rel_l2 | frac | max_ulps | WO n_over/n | WO first (tok,layer) | Logits n_over/n | WQ first (tok,layer) | WK first | WV first |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-vs-poc | 416443 | 60123 | Logits of token 1087 | 0.00439 | 0.556 | 1.81e+04 | 6723/46044 | (1087,0) | 192/256 | (1087,1) | (1087,1) | (1087,1) |
| base-vs-new | 416443 | 399212 | WO layer 16 of token 1 | 0.000257 | 0.0363 | 17 | 45011/46044 | (1,16) | 256/256 | (1,17) | (1,17) | (1,17) |
| new-vs-newoff | 416443 | 367937 | WO layer 0 of token 128 | 0.00194 | 0.362 | 704 | 41436/46044 | (128,0) | 256/256 | (128,1) | (128,1) | (128,1) |
| newoff-vs-trunc | 416443 | 361549 | WO layer 2 of token 128 | 0.000231 | 0.0121 | 7 | 40768/46044 | (128,2) | 256/256 | (128,3) | (128,3) | (128,3) |
| new-vs-trunc | 416443 | 367937 | WO layer 0 of token 128 | 0.00194 | 0.362 | 704 | 41436/46044 | (128,0) | 256/256 | (128,1) | (128,1) | (128,1) |
| baseoff-vs-base | 416443 | 367937 | WO layer 0 of token 128 | 0.00194 | 0.362 | 272 | 41436/46044 | (128,0) | 256/256 | (128,1) | (128,1) | (128,1) |
| baseoff-vs-newoff | 416443 | 402077 | WO layer 16 of token 1 | 0.000257 | 0.0363 | 17 | 45348/46044 | (1,16) | 256/256 | (1,17) | (1,17) | (1,17) |
| baseoff-vs-pocoff | 416443 | 0 | none | - | - | - | 0/46044 | (None,None) | 0/256 | (None,None) | (None,None) | (None,None) |
| clean-vs-baseoff | pending |
| clean-vs-new | pending |

WO at layer 0 from the CSV (tokens where rel_l2 > 0; median / max of rel_l2 over those tokens; page-end = rel_l2 at tokens 1087 / 1151 / 1215; token 1279 is absent from every log):

| pair | all 0..1278 differing | first 5 | med rel_l2 | max rel_l2 | med frac | prompt 0..1023 | decode 1024..1278 | pass2 128..191 (first 5) | page-end 1087 / 1151 / 1215 |
|---|---|---|---|---|---|---|---|---|---|
| base-vs-poc | 3 of 1279 | [1087, 1151, 1215] | 0.00172 | 0.00263 | 0.393 | 0 | 3 | 0 [] | 0.00119 / 0.00263 / 0.00172 |
| base-vs-new | 352 of 1279 | [26, 27, 31, 32, 33] | 0.000106 | 0.00263 | 0.0148 | 338 | 14 | 16 [136, 140, 142, 153, 156] | 0.00119 / 0.00263 / 0.00172 |
| new-vs-newoff | 1151 of 1279 | [128, 129, 130, 131, 132] | 0.00217 | 0.00498 | 0.318 | 896 | 255 | 64 [128, 129, 130, 131, 132] | 0.00316 / 0.00247 / 0.00258 |
| newoff-vs-trunc | 484 of 1279 | [129, 130, 132, 138, 139] | 7.26e-05 | 0.00124 | 0.00937 | 360 | 124 | 18 [129, 130, 132, 138, 139] | 4e-06 / 0.000132 / 0 |
| new-vs-trunc | 1151 of 1279 | [128, 129, 130, 131, 132] | 0.00217 | 0.00498 | 0.318 | 896 | 255 | 64 [128, 129, 130, 131, 132] | 0.00316 / 0.00247 / 0.00258 |
| baseoff-vs-base | 1151 of 1279 | [128, 129, 130, 131, 132] | 0.00217 | 0.005 | 0.318 | 896 | 255 | 64 [128, 129, 130, 131, 132] | 0.00334 / 0.00355 / 0.00304 |
| baseoff-vs-newoff | 689 of 1279 | [26, 27, 31, 32, 33] | 9.2e-05 | 0.00183 | 0.0137 | 550 | 139 | 24 [132, 133, 134, 138, 139] | 8.3e-05 / 0.000132 / 0 |
| baseoff-vs-pocoff | 0 of 1279 | [] | None | None | None | 0 | 0 | 0 [] | 0 / 0 / 0 |

base-vs-new, any layer: first token where any WO differs = 1 (lowest layer 16; layers differing at that token: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]); WO cells differing among tokens 0..127 = 4411 of 4608 (token, layer) cells; tokens 0..127 with any WO difference = 127.

B. Per-step logits (steps-<pair>.json summary; logit = logit units; delta_pair = ON minus OFF movement of the top pair; marked step = --mark step)

| campaign | pair | steps w/ logits | identical steps | flips | nonflip med \|delta_pair\| | p95 | med mean\|d\| | p95 | med frac_changed | max TVD | max \|d\| | med margin_off | marked step | margin_off (ulps) | delta_pair | on_top1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| td-20261016 | base-vs-poc | 256/256 | 64 | [84] | 0 | 0.5 | 0.0302 | 0.249 | 0.741 | 0.0305 | 10.4 | 3.91 | 84 | 0 (0) | -0.0625 | 1499 (off 258) |
| td-20261016 | baseoff-vs-pocoff | 256/256 | 256 | [] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 248 | 0 (0) | 0 | 13 (off 13) |
| td-20261016 | clean-vs-baseoff | 256/256 | 256 | [] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 84 | 0.125 (2) | 0 | 1499 (off 1499) |
| td-20261016 | base-vs-new | 256/256 | 0 | [84] | 0.0625 | 0.375 | 0.0364 | 0.272 | 0.801 | 0.0559 | 11.6 | 3.91 | 84 | 0 (0) | -0.125 | 1499 (off 258) |
| td-20261016 | new-vs-newoff | 256/256 | 0 | [248] | 0.0625 | 0.5 | 0.0382 | 0.236 | 0.791 | 0.0548 | 10 | 3.88 | 248 | 0.125 (1) | -0.25 | 624 (off 13) |
| td-20261016 | newoff-vs-trunc | pending |
| td-20261016 | new-vs-trunc | pending |
| td-20261016 | baseoff-vs-base | pending |
| td-20261016 | baseoff-vs-newoff | pending |
| td-20261016 | clean-vs-new | pending |
| p83-20261013 | fnew-vs-fbase | 256/256 | 0 | [] | 0.0625 | 0.375 | 0.0363 | 0.198 | 0.801 | 0.0432 | 7.42 | 3.88 | 84 | 0.0625 (1) | 0 | 1499 (off 1499) |
| p83-20261013 | fnew-vs-fhead | 256/256 | 1 | [84] | 0.0625 | 0.412 | 0.0346 | 0.209 | 0.784 | 0.0338 | 5.83 | 3.88 | 84 | 0.0625 (1) | -0.0625 | 258 (off 1499) |
| p83-20261013 | new-vs-base | 256/256 | 0 | [84] | 0.0625 | 0.375 | 0.0364 | 0.272 | 0.801 | 0.0559 | 11.6 | 3.88 | 84 | 0.125 (2) | -0.125 | 258 (off 1499) |
| p83-20261013 | new-vs-head | 256/256 | 1 | [] | 0.0625 | 0.375 | 0.0363 | 0.245 | 0.804 | 0.0349 | 5.34 | 3.88 | 84 | 0.125 (2) | 0 | 1499 (off 1499) |
| p83-20261013 | new-vs-newforced | 256/256 | 256 | [] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3.88 | 84 | 0.125 (2) | 0 | 1499 (off 1499) |
| p83-20261013 | new-vs-newoff | 256/256 | 0 | [248] | 0.0625 | 0.5 | 0.0382 | 0.236 | 0.791 | 0.0548 | 10 | 3.88 | 248 | 0.125 (1) | -0.25 | 624 (off 13) |

C. Near-tie statistics (td-20261016/tiestats/tie_stats.json; margin in logit units and bf16 ulps of the top-1 logit)

| pair | flips | margin med logit / ulps | p10 ulps | p05 | min | =0 / <=1 / <=2 / <=4 ulps | \|delta_pair\| med / p95 / max ulps | med / p95 / max logit | E[flips] own ulps | P(>=1) | E pooled_all ulps | P(>=1) | at-risk steps (p95 ulps) | flip ranks (ulps) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new-vs-base | [84] | 3.88 / 39 | 6.5 | 3 | 1 | 0 / 8 / 10 / 21 | 0.5 / 2.62 / 48 | 0.0625 / 0.375 / 6 | 0.758 | 0.548 | 1.04 | 0.662 | 11 | step 84: m=2 d=-2 rank 9 |
| new-vs-head | [] | 3.88 / 39 | 6.5 | 3 | 1 | 0 / 8 / 10 / 21 | 0.5 / 3 / 22 | 0.0625 / 0.375 / 2.75 | 1.54 | 0.802 | 1.04 | 0.662 | 19 | - |
| new-vs-newforced | [] | 3.88 / 39 | 6.5 | 3 | 1 | 0 / 8 / 10 / 21 | 0 / 0 / 0 | 0 / 0 / 0 | 0 | 0 | 1.04 | 0.662 | 0 | - |
| fnew-vs-fhead | [84] | 3.88 / 39.2 | 6 | 3 | 0 | 1 / 7 / 12 / 22 | 0.5 / 2 / 6 | 0.0625 / 0.406 / 1.12 | 1.01 | 0.659 | 1.36 | 0.771 | 12 | step 84: m=1 d=-1 rank 2 |
| fnew-vs-fbase | [] | 3.88 / 39.2 | 6 | 3 | 0 | 1 / 7 / 12 / 22 | 0.5 / 3 / 7 | 0.0625 / 0.375 / 1.5 | 1 | 0.653 | 1.36 | 0.771 | 17 | - |
| new-vs-newoff | [248] | 3.88 / 39 | 6.5 | 3 | 1 | 0 / 8 / 10 / 21 | 1 / 3 / 41 | 0.0625 / 0.5 / 5.12 | 1.25 | 0.737 | 1.04 | 0.662 | 19 | step 248: m=1 d=-2 rank 1 |
| r3x-vs-r4x-20260830 | [22, 37, 145] | 7.25 / 48.8 | 7 | 3 | 0 | 2 / 4 / 7 / 18 | 1 / 4 / 48.5 | 0.125 / 0.75 / 6.06 | 1.36 | 0.777 | 1.23 | 0.742 | 18 | step 22: m=0 d=-1 rank 1, step 37: m=0 d=-1 rank 1, step 145: m=3 d=-6 rank 8 |

Totals over [new-vs-base, new-vs-head, fnew-vs-fhead, fnew-vs-fbase, new-vs-newoff, r3x-vs-r4x-20260830]: observed 6 flips in 1536 steps; expected own-logit 14.8, own-ulps 6.92, pooled_all-logit 14.8, pooled_all-ulps 7.07. Model reproduces every observed flip: True.

D. Kernel tests (td-20261016/ktest/results.txt; n = scores or elements compared)

| test | identical | n | diff | diff % | max_bf16ulps | line |
|---|---|---|---|---|---|---|
| T1_amx_qk_vs_vnni_reader | no | 512000 | 253188 | 49.5 | 2 | line 7 |
| T1b_rowmajor_amx_vs_vnni_amx | yes | 512000 | 0 | 0 | - | line 8 |
| T2_avx_dotter_vs_amx_qk | no | 512000 | 256294 | 50.1 | 0.75 | line 9 |
| T5_residual_best_simple_candidate_vs_hardware | no | 512000 | 105925 | 20.7 | 2 | line 39 |
| T5m_amx_qk_vs_even_odd_chain_model_identical | yes | 512000 | 0 | 0 | - | line 349 |
| T6a_amx_pv_vs_avx_pv_bf16_exact_P | no | 1024000 | 745618 | 72.8 | 36 | line 352 |
| T6b_amx_pv_rne_vs_avx_pv_truncated_P | no | 1024000 | 1023910 | 100 | 2.08e+06 | line 358 |
| T6c_amx_pv_vs_avx_pv_fed_rne_P | no | 1024000 | 745817 | 72.8 | 19.2 | line 359 |
| T6d_amx_pv_vs_even_odd_chain_model_identical | yes | 102400 | 0 | 0 | - | line 355 |
| T9a_avx512_amx_order_qk_vs_amx_qk | yes | 512000 | 0 | 0 | - | line 384 |
| T9b_avx512_amx_order_pv_vs_amx_pv | yes | 1024000 | 0 | 0 | - | line 385 |
- T0 (MXCSR_FTZ_DAZoff): n=2000000; s1 (acc+pe)+po 92.8 %, s2 (acc+po)+pe 100 %, s3 acc+(pe+po) 92.4 %, sg round1 92.5 %.
- T0 (MXCSR_FTZ_DAZon): n=2000000; s1 (acc+pe)+po 92.8 %, s2 (acc+po)+pe 100 %, s3 acc+(pe+po) 92.4 %, sg round1 92.5 %.
- T3_dotter_bit_identical_model: lane=s2:(acc+po)+pe reduce=halving(j+8,j+4,j+2,0+1) match 512000 (100 %).
- T4_vnni_reader_bit_identical_model: s2:(acc+po)+pe match 512000 (100 %).
- T5 best simple candidate: step_exact_then_add; T5m identical combine = acc+fl(E+O); T6d identical combine = acc+fl(E+O).

| test | tokens | instances | trunc bias (mean signed rel) | trunc mass-weighted bias | trunc rms_rel | rne bias | rne mass-weighted bias | rne rms_rel | rms ratio trunc/rne | mass ratio-1 trunc | mass ratio-1 rne |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T7a | 64 | 2000 | -0.000733 | -0.000834 | 0.00292 | -5.76e-06 | -3.96e-06 | 0.00162 | 1.79 | -0.00144 | -4.1e-06 |
| T7b | 64 | 2000 | -0.000757 | -0.000857 | 0.00293 | -1.17e-06 | 6.39e-07 | 0.00163 | 1.8 | -0.00145 | -3.32e-08 |
| T8a | 16 | 500 | -0.000552 | -0.000623 | 0.00291 | 1.57e-06 | 1.73e-06 | 0.00154 | 1.88 | -0.00108 | -4.94e-06 |
| T8b | 1 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

T9c timings (ns per query group of 4 heads x 64-token page, single thread, data in cache): k_vnni::qk_group<4,bf16> (current VNNI reader) = 824 ns; qk_group_amxorder<4> (AMX order) = 1074 ns, 1.3x vs current; qk_vnni_128x4 (AMX kernel, with pack_q_rows) = 166 ns (kernel only 143 ns); avx_scaled_v x4 heads (current AVX loop) = 896 ns; scaled_v_amxorder x4 heads (AMX order) = 952 ns, 1.06x vs current; weights_times_v_128x4 (AMX kernel, 4 heads) = 178 ns.

E. Offline replay (td-20261016/replay/results.json, arms_wo-L0.json, wo_check-*-L0.json; layer 0, 201 sampled tokens)

Params: layer 0, AMX model step_exact, 201 sampled tokens (decode steps [1024, 1039, 1040, 1056, 1087, 1090, 1150, 1200, 1278]), 1279 logged tokens, 126553 of 11132416 values not decimal-exact, wall 63.1 s. Q/K/V of layer 0 vs base: new Q/K/V differ 0/0/0; newoff Q/K/V differ 0/0/0; poc Q/K/V differ 0/0/0.

M1 raw scores (fraction of scores differing, pooled; median rel of differing; max rel):

| pair | all | pass0 0..127 | pass1 128..191 | decode | median rel (all) | median fp32 ulp (all) | max rel (all) |
|---|---|---|---|---|---|---|---|
| D_vs_R | 0.641 | 0.618 | 0.615 | 0.688 | 1.05e-07 | 1 | 0.0212 |
| A_vs_R_model_step_exact | 0.606 | 0.586 | 0.576 | 0.652 | 1.03e-07 | 1 | 0.0159 |
| A_vs_D_model_step_exact | 0.488 | 0.447 | 0.456 | 0.556 | 9.29e-08 | 1 | 0.00826 |
| A_vs_R_model_seq | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Within-pair order sensitivity (scores changed of 912032): odd_first: D 0, R 0; even_first: D 14086, R 208447; pair_sum_first: D 13079, R 171484.

M2 attention output (fraction of bf16 elements differing, pooled per token class; tokens with any difference of 201):

| pair | pass0 0..127 | pass1 128..191 | decode | all | tokens any diff | exactly one element | first token | token 1087 |
|---|---|---|---|---|---|---|---|---|
| clean_vs_newoff | 0.000591 | 0.000309 | 0.000326 | 0.000489 | 88 | 49 | 26 | 0.000244 |
| newoff_vs_new | 0 | 0.195 | 0.284 | 0.0747 | 73 | 0 | 128 | 0.3 |
| base_vs_new | 0.000591 | 0.00013 | 0.025 | 0.00154 | 72 | 40 | 26 | 0.225 |
| clean_vs_base | 0 | 0.195 | 0.299 | 0.0754 | 73 | 0 | 128 | 0.434 |
| new_vs_trunc | 0 | 0.195 | 0.284 | 0.0747 | 73 | 0 | 128 | 0.3 |
| clean_vs_clean_rne | 0.343 | 0.361 | 0.403 | 0.351 | 200 | 0 | 1 | 0.434 |
| newoff_vs_trunc | 0 | 0.000217 | 0.000163 | 7.65e-05 | 23 | 14 | 128 | 0 |
| clean_vs_new | 0.000591 | 0.195 | 0.284 | 0.0751 | 123 | 26 | 26 | 0.3 |
| amx_model_seq / newoff_vs_new | 0 | 0.195 | 0.284 | 0.0747 | - | - | - | - |
| amx_model_seq / base_vs_new | 0.000591 | 0.000137 | 0.025 | 0.00154 | - | - | - | - |

M3 vs exact fp64 (all 201 tokens; bias = mass-weighted bias ratio; rel L2 ratio):

| model | fp32 mean bias | min | max | fp32 rms rel L2 | median | bf16 mean bias | bf16 rms rel L2 |
|---|---|---|---|---|---|---|---|
| clean | -0.000784 | -0.00176 | 0 | 0.002 | 0.00195 | -0.000692 | 0.00257 |
| newoff | -0.000784 | -0.00176 | 0 | 0.002 | 0.00195 | -0.000691 | 0.00257 |
| base | -0.000628 | -0.00163 | 6.94e-05 | 0.00191 | 0.00187 | -0.000535 | 0.0025 |
| new | -0.00063 | -0.00163 | 0 | 0.00191 | 0.00187 | -0.000537 | 0.0025 |
| trunc | -0.000784 | -0.00176 | 0 | 0.002 | 0.00195 | -0.000691 | 0.00257 |
| clean_rne | -1.61e-05 | -0.000357 | 0.000174 | 0.0016 | 0.00157 | 7.56e-05 | 0.00228 |

| token class | trunc mass ratio-1 mean / min / max | RNE mean / min / max |
|---|---|---|
| all | -0.00162 / -0.00344 / 0 | 1.05e-06 / -0.00149 / 0.00134 |
| pass0_0-127 | -0.00155 / -0.00344 / 0 | 1.66e-06 / -0.00149 / 0.00134 |
| pass1_128-191 | -0.0017 / -0.00331 / -5.77e-08 | -8.02e-07 / -0.000957 / 0.00116 |
| decode | -0.00203 / -0.00305 / -1.32e-06 | 5.57e-06 / -0.000658 / 0.00117 |

| token | attended | trunc mass ratio-1 | RNE | clean bias | clean_rne bias | base bias | new bias |
|---|---|---|---|---|---|---|---|
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 15 | 16 | -0.0015 | 2.99e-05 | -0.000676 | -1.46e-05 | -0.000676 | -0.000676 |
| 63 | 64 | -0.0018 | -5.1e-06 | -0.000975 | -2.37e-06 | -0.000975 | -0.000975 |
| 127 | 128 | -0.00186 | -8.61e-06 | -0.000848 | 3.46e-05 | -0.000848 | -0.000848 |
| 1087 | 1088 | -0.00222 | 3.39e-05 | -0.00149 | 6.96e-05 | 6.94e-05 | -0.000537 |

M4 token 0: all models identical = yes; output equals V0 in bf16 = yes.

M4 logged WO (layer 0, 1279 tokens, arms_wo-L0.json):

| pair | class | tokens | with WO difference | first | median frac elements | median rel L2 | max rel L2 |
|---|---|---|---|---|---|---|---|
| base_vs_poc | prompt_0-127 | 128 | 0 | None | 0 | 0 | 0 |
| base_vs_poc | prompt_128-1023 | 896 | 0 | None | 0 | 0 | 0 |
| base_vs_poc | decode | 255 | 3 | 1087 | 0.393 | 0.00172 | 0.00263 |
| base_vs_poc | all | 1279 | 3 | 1087 | 0.393 | 0.00172 | 0.00263 |
| base_vs_new | prompt_0-127 | 128 | 37 | 26 | 0.0164 | 0.000116 | 0.00162 |
| base_vs_new | prompt_128-1023 | 896 | 301 | 136 | 0.0148 | 0.000104 | 0.000938 |
| base_vs_new | decode | 255 | 14 | 1046 | 0.018 | 0.00011 | 0.00263 |
| base_vs_new | all | 1279 | 352 | 26 | 0.0148 | 0.000106 | 0.00263 |
| newoff_vs_new | prompt_0-127 | 128 | 0 | None | 0 | 0 | 0 |
| newoff_vs_new | prompt_128-1023 | 896 | 896 | 128 | 0.3 | 0.0021 | 0.00498 |
| newoff_vs_new | decode | 255 | 255 | 1024 | 0.373 | 0.00239 | 0.00498 |
| newoff_vs_new | all | 1279 | 1151 | 128 | 0.318 | 0.00217 | 0.00498 |

Replay vs logged set overlap (201 sampled tokens): newoff_vs_new: logged 73, predicted 73, both 73, logged-not-predicted 0, predicted-not-logged 0, first logged 128 / predicted 128; base_vs_new: logged 55, predicted 72, both 43, logged-not-predicted 12, predicted-not-logged 29, first logged 26 / predicted 26.

wo_check (replay bf16 output through o_proj vs logged WO, relative L2; exact fp64 through o_proj; wrong head order control):

| token | base replay / exact / wrong-order | newoff replay / exact / wrong-order | trunc replay / exact / wrong-order |
|---|---|---|---|
| 0 | 0.00161 / 0.00161 / 0.00161 | - | - |
| 1 | 0.00241 / 0.00289 / 0.53 | 0.00241 / 0.00289 / 0.53 | 0.00241 / 0.00289 / 0.53 |
| 2 | 0.00162 / 0.00219 / 0.598 | - | - |
| 5 | 0.00186 / 0.00244 / 0.603 | - | - |
| 17 | 0.00173 / 0.00223 / 0.845 | - | - |
| 64 | 0.0016 / 0.00284 / 0.798 | - | - |
| 100 | 0.0017 / 0.00272 / 0.589 | 0.0017 / 0.00272 / 0.589 | - |
| 127 | 0.00195 / 0.00298 / 0.712 | 0.00195 / 0.00298 / 0.712 | - |
| 128 | 0.00221 / 0.00227 / 0.691 | 0.00192 / 0.00232 / 0.691 | 0.00192 / 0.00232 / 0.691 |
| 129 | - | 0.00198 / 0.00331 / 0.606 | 0.00198 / 0.00331 / 0.606 |
| 150 | 0.00236 / 0.00249 / 0.656 | - | - |
| 191 | 0.00137 / 0.00165 / 0.614 | 0.00212 / 0.00218 / 0.614 | 0.00212 / 0.00218 / 0.614 |
| 1024 | 0.00222 / 0.00224 / 0.541 | 0.00171 / 0.00297 / 0.542 | 0.00171 / 0.00297 / 0.542 |
| 1090 | 0.00213 / 0.0027 / 0.718 | - | - |
| 1278 | 0.00197 / 0.00227 / 0.56 | 0.00177 / 0.00291 / 0.561 | 0.00177 / 0.00291 / 0.561 |

F. Campaign record

| round | arm | binary | env | rc | wall s | tokens | full bytes | version | hash |
|---|---|---|---|---|---|---|---|---|---|
| td-20261016 | new | runtron.pr4 | - | 0 | 310 | 256 | 20636614998 | 2026.10.13-ea94e95a | ea94e95a4e30 |
| td-20261016 | base | runtron.main1010 | - | 0 | 310 | 256 | 20636625693 | 2026.10.10-72308ec9 | 72308ec90c80 |
| td-20261016 | poc | runtron.poc | - | 0 | 311 | 256 | 20636627555 | 2026.10.16-017181c0 | 017181c02d6f |
| td-20261016 | newoff | runtron.pr4 | TRON_AMX_DISABLE=1 | 0 | 311 | 256 | 20636627867 | 2026.10.13-ea94e95a | ea94e95a4e30 |
| td-20261016 | trunc | runtron.trunc | - | 0 | 306 | 256 | 20636605807 | 2026.10.16-3d1426f5 | 3d1426f5491d |
| td-20261016 | baseoff | runtron.main1010 | TRON_AMX_DISABLE=1 | 0 | 310 | 256 | 20636613682 | 2026.10.10-72308ec9 | 72308ec90c80 |
| td-20261016 | pocoff | runtron.poc | TRON_AMX_DISABLE=1 | 0 | 308 | 256 | 20636613682 | 2026.10.16-017181c0 | 017181c02d6f |
| td-20261016 | clean | runtron.clean | - | 0 | 313 | 256 | 20636613682 | 2026.10.16-72308ec9 | 72308ec90c80 |
| td2-20261016 | pending (/home/jhan/workspace/intel-AMX/exec/results/td2-20261016/runs.txt) |
| td3-20261016 | pending (/home/jhan/workspace/intel-AMX/exec/results/td3-20261016/runs.txt) |
- td-20261016 tokens.txt: new.tokens: identical for 256 tokens (lengths 256 / 256); base.tokens: identical for 256 tokens (lengths 256 / 256); poc.tokens: identical for 256 tokens (lengths 256 / 256); newoff.tokens: identical for 256 tokens (lengths 256 / 256); trunc.tokens: identical for 256 tokens (lengths 256 / 256); baseoff.tokens: identical for 256 tokens (lengths 256 / 256); pocoff.tokens: identical for 256 tokens (lengths 256 / 256); clean.tokens: identical for 256 tokens (lengths 256 / 256)
- td-20261016 probe.done: pending
- td2-20261016 tokens.txt: pending
- td2-20261016: verdict pending; steps base-vs-new: pending, new-vs-newoff: pending, base-vs-poc: pending
- td3-20261016: verdict pending; stats base63: pending, base64: pending, new63: pending, new64: pending, poc64: pending; deltas 64-63: base: pending, new: pending

G. Builds and commits

| build | commit | subject | configure | cache options | build wall s | sha256 of the binary |
|---|---|---|---|---|---|---|
| clean | 72308ec90c | Merge pull request #4491 from positron-ai/mitchell2-26-09-18-owned-buffer-resize | --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS= | TRON_AMX_DISPATCH:BOOL=OFF (matching CMakeCache lines: 1) | 905 | 31dded7b8fb746298e1cf25507736ebe8399776d8cfbc449c9fa8d3decb1b8f1 |
| poc | 017181c02d6f46dd50e33c3d2efe78ebbcccccb4 | PoC (issue #4444 measurement): score VNNI blocks through unpack + the row-major dotter | --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= | TRON_AMX_DISPATCH:BOOL=ON TRON_K_VNNI:BOOL=ON | 924 | e2662a4a810f7ffd17a69415f267da874fba7cd67cebefb105b52a9008afbf27 |
| trunc | 3d1426f5491d676900f625edd8e933d04acf7dc5 | PoC (issue #4444 measurement): AMX PV weights truncated to bf16 like the AVX path | --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= | TRON_AMX_DISPATCH:BOOL=ON TRON_K_VNNI:BOOL=ON | 971 | a3428884fac60454268b78b13305eea716e61141f472d87ba0e92aa5d833b527 |

Worktree commits: poc: 017181c02d6f46dd50e33c3d2efe78ebbcccccb4 (PoC (issue #4444 measurement): score VNNI blocks through unpack + the row-major dotter); trunc: 3d1426f5491d676900f625edd8e933d04acf7dc5 (PoC (issue #4444 measurement): AMX PV weights truncated to bf16 like the AVX path).

predictions.md (/home/jhan/workspace/intel-AMX/token-divergence-4444/predictions.md) is stored verbatim in facts.json at G_builds.predictions_md.value (3223 characters).
