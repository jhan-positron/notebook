import json
F = json.load(open('/home/jhan/workspace/intel-AMX/exec/td-20261016/report/facts.json'))
def P(d): return isinstance(d, dict) and d.get('status') == 'pending'
def v(d, *ks):
    for k in ks:
        if P(d) or d is None: return 'pending'
        d = d.get(k)
    if d is None: return 'None'
    if P(d): return 'pending'
    return d['value'] if isinstance(d, dict) and 'value' in d else d
def f(x):
    if x == 'pending' or x is None or x == 'None': return str(x)
    if isinstance(x, bool): return 'yes' if x else 'no'
    if isinstance(x, int): return str(x)
    if isinstance(x, float):
        if x == 0: return '0'
        if x.is_integer() and abs(x) < 1e6: return str(int(x))
        return f'{x:.3g}'
    if isinstance(x, list): return '[' + ', '.join(f(y) for y in x) + ']'
    return str(x)
out = []
A = F['A_layer_records']
out.append('A. Per-layer records (results/td-20261016/layers-<pair>.json + .csv; units: counts, rel_l2 = relative L2 ratio, frac = fraction, ulps = bf16 ulps)')
out.append('')
out.append('| pair | keys | over | first_over key | rel_l2 | frac | max_ulps | WO n_over/n | WO first (tok,layer) | Logits n_over/n | WQ first (tok,layer) | WK first | WV first |')
out.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for p, d in A.items():
    if P(d): out.append(f'| {p} | pending |'); continue
    s = d['summary']; bl = d['by_label']
    fo = s.get('first_over')
    fk = v(fo, 'key') if isinstance(fo, dict) and 'key' in fo else 'none'
    out.append(f"| {p} | {f(v(s,'n_keys_compared'))} | {f(v(s,'n_over_threshold'))} | {fk} | {f(v(fo,'rel_l2')) if fk!='none' else '-'} | {f(v(fo,'frac_changed')) if fk!='none' else '-'} | {f(v(fo,'max_ulps')) if fk!='none' else '-'} | {f(v(bl,'WO','n_over'))}/{f(v(bl,'WO','n'))} | ({f(v(bl,'WO','first_token_over'))},{f(v(bl,'WO','first_layer_over'))}) | {f(v(bl,'Logits','n_over'))}/{f(v(bl,'Logits','n'))} | ({f(v(bl,'WQ','first_token_over'))},{f(v(bl,'WQ','first_layer_over'))}) | ({f(v(bl,'WK','first_token_over'))},{f(v(bl,'WK','first_layer_over'))}) | ({f(v(bl,'WV','first_token_over'))},{f(v(bl,'WV','first_layer_over'))}) |")
out.append('')
out.append('WO at layer 0 from the CSV (tokens where rel_l2 > 0; median / max of rel_l2 over those tokens; page-end = rel_l2 at tokens 1087 / 1151 / 1215; token 1279 is absent from every log):')
out.append('')
out.append('| pair | all 0..1278 differing | first 5 | med rel_l2 | max rel_l2 | med frac | prompt 0..1023 | decode 1024..1278 | pass2 128..191 (first 5) | page-end 1087 / 1151 / 1215 |')
out.append('|---|---|---|---|---|---|---|---|---|---|')
for p, d in A.items():
    if P(d): continue
    w = d['wo_layer0']
    if P(w): out.append(f'| {p} | csv pending |'); continue
    a = w['all_tokens_0_1278']; pr = w['prompt_tokens_0_1023']; de = w['decode_tokens_1024_1278']; p2 = w['prefill_pass2_tokens_128_191']; pe = w['page_end_decode_tokens']
    pes = ' / '.join(f(v(pe, f'token_{t}', 'rel_l2')) if 'rel_l2' in pe[f'token_{t}'] else 'absent' for t in (1087, 1151, 1215))
    out.append(f"| {p} | {f(v(a,'tokens_differing'))} of {f(v(a,'tokens_present'))} | {f(v(a,'first_5_differing_tokens'))} | {f(v(a,'median_rel_l2_of_differing'))} | {f(v(a,'max_rel_l2_of_differing'))} | {f(v(a,'median_frac_changed_of_differing'))} | {f(v(pr,'tokens_differing'))} | {f(v(de,'tokens_differing'))} | {f(v(p2,'tokens_differing'))} {f(v(p2,'first_5_differing_tokens'))} | {pes} |")
out.append('')
bn = A.get('base-vs-new', {}).get('wo_any_layer', {})
if bn:
    out.append(f"base-vs-new, any layer: first token where any WO differs = {f(v(bn,'first_token_any_layer_wo_differs'))} (lowest layer {f(v(bn,'layer_at_first_token'))}; layers differing at that token: {f(v(bn,'layers_differing_at_first_token'))}); WO cells differing among tokens 0..127 = {f(v(bn,'wo_cells_differing_tokens_0_127'))} of {f(v(bn,'wo_cells_total_tokens_0_127'))} (token, layer) cells; tokens 0..127 with any WO difference = {f(v(bn,'tokens_0_127_with_any_wo_difference'))}.")
out.append('')
B = F['B_step_logits']
out.append('B. Per-step logits (steps-<pair>.json summary; logit = logit units; delta_pair = ON minus OFF movement of the top pair; marked step = --mark step)')
out.append('')
out.append('| campaign | pair | steps w/ logits | identical steps | flips | nonflip med \\|delta_pair\\| | p95 | med mean\\|d\\| | p95 | med frac_changed | max TVD | max \\|d\\| | med margin_off | marked step | margin_off (ulps) | delta_pair | on_top1 |')
out.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for camp, d in B.items():
    for p, r in d.items():
        if p == 'verdict_txt': continue
        if P(r): out.append(f'| {camp} | {p} | pending |'); continue
        s = r['summary']; m = r['marked_step']
        mk = '-' if P(m) or 'step' not in m else f"{f(v(m,'step'))} | {f(v(m,'margin_off'))} ({f(v(m,'margin_off_ulps'))}) | {f(v(m,'delta_pair'))} | {f(v(m,'on_top1'))} (off {f(v(m,'off_top1'))})"
        out.append(f"| {camp} | {p} | {f(v(s,'n_with_logits'))}/{f(v(s,'n_steps'))} | {f(v(s,'n_identical_steps'))} | {f(v(s,'flip_steps'))} | {f(v(s,'nonflip_median_abs_delta_pair'))} | {f(v(s,'nonflip_p95_abs_delta_pair'))} | {f(v(s,'nonflip_median_mean_abs_delta'))} | {f(v(s,'nonflip_p95_mean_abs_delta'))} | {f(v(s,'nonflip_median_frac_changed'))} | {f(v(s,'max_tvd'))} | {f(v(s,'max_max_abs_delta'))} | {f(v(s,'median_margin_off'))} | {mk} |")
out.append('')
C = F['C_tie_stats']
out.append('C. Near-tie statistics (td-20261016/tiestats/tie_stats.json; margin in logit units and bf16 ulps of the top-1 logit)')
out.append('')
out.append('| pair | flips | margin med logit / ulps | p10 ulps | p05 | min | =0 / <=1 / <=2 / <=4 ulps | \\|delta_pair\\| med / p95 / max ulps | med / p95 / max logit | E[flips] own ulps | P(>=1) | E pooled_all ulps | P(>=1) | at-risk steps (p95 ulps) | flip ranks (ulps) |')
out.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for p, r in C['pairs'].items():
    pr = C['prediction'][p]
    fl = r['flip_steps']
    ranks = ', '.join(f"step {k.split('_')[1]}: m={f(v(x,'margin_ulps'))} d={f(v(x,'delta_pair_ulps'))} rank {f(v(x,'rank_by_margin_ulps'))}" for k, x in fl.items()) or '-'
    out.append(f"| {p} | {f(v(r,'observed_flips'))} | {f(v(r,'margin_logit','median'))} / {f(v(r,'margin_ulps','median'))} | {f(v(r,'margin_ulps','p10'))} | {f(v(r,'margin_ulps','p05'))} | {f(v(r,'margin_ulps','min'))} | {f(v(r,'margin_counts','eq_0'))} / {f(v(r,'margin_counts','le_1ulp'))} / {f(v(r,'margin_counts','le_2ulp'))} / {f(v(r,'margin_counts','le_4ulp'))} | {f(v(r,'abs_delta_pair_ulps','median'))} / {f(v(r,'abs_delta_pair_ulps','p95'))} / {f(v(r,'abs_delta_pair_ulps','max'))} | {f(v(r,'abs_delta_pair_logit','median'))} / {f(v(r,'abs_delta_pair_logit','p95'))} / {f(v(r,'abs_delta_pair_logit','max'))} | {f(v(pr,'own_ulps','expected_flips'))} | {f(v(pr,'own_ulps','p_at_least_one'))} | {f(v(pr,'pooled_all_ulps','expected_flips'))} | {f(v(pr,'pooled_all_ulps','p_at_least_one'))} | {f(v(r,'at_risk','steps_margin_le_p95_ulps'))} | {ranks} |")
t = C['totals']
out.append('')
out.append(f"Totals over {f(v(t,'pairs'))}: observed {f(v(t,'observed_flips_total'))} flips in {f(v(t,'steps_total'))} steps; expected own-logit {f(v(t,'expected_flips_total_own_logit'))}, own-ulps {f(v(t,'expected_flips_total_own_ulps'))}, pooled_all-logit {f(v(t,'expected_flips_total_pooled_all_logit'))}, pooled_all-ulps {f(v(t,'expected_flips_total_pooled_all_ulps'))}. Model reproduces every observed flip: {all(v(r,'model_reproduces_observed') for r in C['pairs'].values())}.")
out.append('')
D = F['D_kernel_tests']
out.append('D. Kernel tests (td-20261016/ktest/results.txt; n = scores or elements compared)')
out.append('')
out.append('| test | identical | n | diff | diff % | max_bf16ulps | line |')
out.append('|---|---|---|---|---|---|---|')
for k in ('T1_amx_qk_vs_vnni_reader','T1b_rowmajor_amx_vs_vnni_amx','T2_avx_dotter_vs_amx_qk','T5_residual_best_simple_candidate_vs_hardware','T5m_amx_qk_vs_even_odd_chain_model_identical','T6a_amx_pv_vs_avx_pv_bf16_exact_P','T6b_amx_pv_rne_vs_avx_pv_truncated_P','T6c_amx_pv_vs_avx_pv_fed_rne_P','T6d_amx_pv_vs_even_odd_chain_model_identical','T9a_avx512_amx_order_qk_vs_amx_qk','T9b_avx512_amx_order_pv_vs_amx_pv'):
    r = D.get(k)
    if r is None or P(r): out.append(f'| {k} | pending |'); continue
    out.append(f"| {k} | {f(v(r,'identical'))} | {f(v(r,'n'))} | {f(v(r,'diff_count'))} | {f(v(r,'diff_percent'))} | {f(v(r,'max_bf16ulps')) if 'max_bf16ulps' in r else '-'} | {r['n']['source'].split('::')[1].strip()} |")
t0 = D['T0_lane_semantics']
for k, r in t0.items():
    out.append(f"- T0 ({k}): n={f(v(r,'n'))}; s1 (acc+pe)+po {f(v(r,'s1_percent'))} %, s2 (acc+po)+pe {f(v(r,'s2_percent'))} %, s3 acc+(pe+po) {f(v(r,'s3_percent'))} %, sg round1 {f(v(r,'sg_percent'))} %.")
for k in ('T3_dotter_bit_identical_model','T4_vnni_reader_bit_identical_model'):
    r = D[k]; out.append(f"- {k}: {f(v(r,'model'))} match {f(v(r,'match'))} ({f(v(r,'match_percent'))} %).")
out.append(f"- T5 best simple candidate: {f(v(D,'T5_best_simple_candidate'))}; T5m identical combine = {f(v(D['T5m_amx_qk_vs_even_odd_chain_model_identical'],'combine'))}; T6d identical combine = {f(v(D['T6d_amx_pv_vs_even_odd_chain_model_identical'],'combine'))}.")
out.append('')
out.append('| test | tokens | instances | trunc bias (mean signed rel) | trunc mass-weighted bias | trunc rms_rel | rne bias | rne mass-weighted bias | rne rms_rel | rms ratio trunc/rne | mass ratio-1 trunc | mass ratio-1 rne |')
out.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
for k in ('T7a','T7b','T8a','T8b'):
    r = D[k]; a = r['o_trunc_avx_path_vs_fp64']; b = r['o_rne_amx_kernel_vs_fp64']
    out.append(f"| {k} | {f(v(r,'tokens'))} | {f(v(r,'instances'))} | {f(v(a,'mean_signed_rel_bias'))} | {f(v(a,'mass_weighted_bias'))} | {f(v(a,'rms_rel'))} | {f(v(b,'mean_signed_rel_bias'))} | {f(v(b,'mass_weighted_bias'))} | {f(v(b,'rms_rel'))} | {f(v(r,'rms_ratio_trunc_over_rne'))} | {f(v(r,'weight_mass_ratio_minus1_trunc'))} | {f(v(r,'weight_mass_ratio_minus1_rne'))} |")
out.append('')
t9 = D['T9c_timings']
out.append('T9c timings (ns per query group of 4 heads x 64-token page, single thread, data in cache): ' + '; '.join(f"{f(v(r,'description'))} = {f(v(r,'ns_per_call'))} ns" + (f" (kernel only {f(v(r,'kernel_only_ns'))} ns)" if 'kernel_only_ns' in r else '') + (f", {f(v(r,'ratio_vs_current'))}x vs current" if 'ratio_vs_current' in r else '') for k, r in t9.items() if k != 'conditions') + '.')
out.append('')
E = F['E_replay']
out.append('E. Offline replay (td-20261016/replay/results.json, arms_wo-L0.json, wo_check-*-L0.json; layer 0, 201 sampled tokens)')
out.append('')
pa = E['params']
out.append(f"Params: layer {f(v(pa,'layer'))}, AMX model {f(v(pa,'amx_model'))}, {f(v(pa,'n_sampled_tokens'))} sampled tokens (decode steps {f(v(pa,'decode_tokens_sampled'))}), {f(v(pa,'n_tokens_logged'))} logged tokens, {f(v(pa,'values_not_decimal_exact'))} of {f(v(pa,'values_total'))} values not decimal-exact, wall {f(v(pa,'wall_s'))} s. Q/K/V of layer 0 vs base: " + '; '.join(f"{arm} Q/K/V differ {f(v(d,'Q'))}/{f(v(d,'K'))}/{f(v(d,'V'))}" for arm, d in E['qkv_identity_vs_base'].items()) + '.')
out.append('')
out.append('M1 raw scores (fraction of scores differing, pooled; median rel of differing; max rel):')
out.append('')
out.append('| pair | all | pass0 0..127 | pass1 128..191 | decode | median rel (all) | median fp32 ulp (all) | max rel (all) |')
out.append('|---|---|---|---|---|---|---|---|')
for p, r in E['M1_scores'].items():
    if p == 'within_pair_order_sensitivity': continue
    out.append(f"| {p} | {f(v(r,'all','frac_differ_pooled'))} | {f(v(r,'pass0_0-127','frac_differ_pooled'))} | {f(v(r,'pass1_128-191','frac_differ_pooled'))} | {f(v(r,'decode','frac_differ_pooled'))} | {f(v(r,'all','median_rel_of_differing'))} | {f(v(r,'all','median_ulp_of_differing'))} | {f(v(r,'all','max_rel'))} |")
w = E['M1_scores']['within_pair_order_sensitivity']
out.append('')
out.append('Within-pair order sensitivity (scores changed of 912032): ' + '; '.join(f"{o}: D {f(v(d,'D'))}, R {f(v(d,'R'))}" for o, d in w.items()) + '.')
out.append('')
out.append('M2 attention output (fraction of bf16 elements differing, pooled per token class; tokens with any difference of 201):')
out.append('')
out.append('| pair | pass0 0..127 | pass1 128..191 | decode | all | tokens any diff | exactly one element | first token | token 1087 |')
out.append('|---|---|---|---|---|---|---|---|---|')
for p, r in E['M2_attention_output'].items():
    if p == 'amx_model_seq':
        for p2, rr in r.items(): out.append(f"| amx_model_seq / {p2} | {f(v(rr,'pass0_0-127'))} | {f(v(rr,'pass1_128-191'))} | {f(v(rr,'decode'))} | {f(v(rr,'all'))} | - | - | - | - |")
        continue
    out.append(f"| {p} | {f(v(r,'pass0_0-127','frac_bf16_differ_pooled'))} | {f(v(r,'pass1_128-191','frac_bf16_differ_pooled'))} | {f(v(r,'decode','frac_bf16_differ_pooled'))} | {f(v(r,'all','frac_bf16_differ_pooled'))} | {f(v(r,'tokens_with_any_bf16_difference'))} | {f(v(r,'tokens_with_exactly_one_element'))} | {f(v(r,'first_token_with_difference'))} | {f(v(r,'token_1087_frac_bf16_differ'))} |")
out.append('')
out.append('M3 vs exact fp64 (all 201 tokens; bias = mass-weighted bias ratio; rel L2 ratio):')
out.append('')
out.append('| model | fp32 mean bias | min | max | fp32 rms rel L2 | median | bf16 mean bias | bf16 rms rel L2 |')
out.append('|---|---|---|---|---|---|---|---|')
m3 = E['M3_vs_exact']
for mdl, r in m3['fp32_output'].items():
    b = m3['bf16_output'][mdl]
    out.append(f"| {mdl} | {f(v(r,'all','mean_mass_bias'))} | {f(v(r,'all','min_mass_bias'))} | {f(v(r,'all','max_mass_bias'))} | {f(v(r,'all','rms_rel_l2'))} | {f(v(r,'all','median_rel_l2'))} | {f(v(b,'all','mean_mass_bias'))} | {f(v(b,'all','rms_rel_l2'))} |")
out.append('')
out.append('| token class | trunc mass ratio-1 mean / min / max | RNE mean / min / max |')
out.append('|---|---|---|')
for cls, r in m3['weight_mass'].items():
    out.append(f"| {cls} | {f(v(r,'trunc_ratio_minus1_mean'))} / {f(v(r,'trunc_ratio_minus1_min'))} / {f(v(r,'trunc_ratio_minus1_max'))} | {f(v(r,'rne_ratio_minus1_mean'))} / {f(v(r,'rne_ratio_minus1_min'))} / {f(v(r,'rne_ratio_minus1_max'))} |")
out.append('')
out.append('| token | attended | trunc mass ratio-1 | RNE | clean bias | clean_rne bias | base bias | new bias |')
out.append('|---|---|---|---|---|---|---|---|')
for k, r in m3['bias_vs_attended'].items():
    out.append(f"| {k.split('_')[1]} | {f(v(r,'attended'))} | {f(v(r,'trunc_mass_ratio_minus1'))} | {f(v(r,'rne_mass_ratio_minus1'))} | {f(v(r,'clean_output_mass_bias'))} | {f(v(r,'clean_rne_output_mass_bias'))} | {f(v(r,'base_output_mass_bias'))} | {f(v(r,'new_output_mass_bias'))} |")
out.append('')
out.append(f"M4 token 0: all models identical = {f(v(E['M4_token0'],'token0_all_models_identical'))}; output equals V0 in bf16 = {f(v(E['M4_token0'],'token0_output_equals_V0_bf16'))}.")
out.append('')
out.append('M4 logged WO (layer 0, 1279 tokens, arms_wo-L0.json):')
out.append('')
out.append('| pair | class | tokens | with WO difference | first | median frac elements | median rel L2 | max rel L2 |')
out.append('|---|---|---|---|---|---|---|---|')
for p, r in E['M4_logged_wo']['pairs'].items():
    for cls, c in r.items():
        out.append(f"| {p} | {cls} | {f(v(c,'tokens'))} | {f(v(c,'tokens_with_any_WO_difference'))} | {f(v(c,'first_differing_token'))} | {f(v(c,'median_frac_elements_differing_when_differing'))} | {f(v(c,'median_rel_l2_when_differing'))} | {f(v(c,'max_rel_l2'))} |")
so = E['M4_logged_wo']['set_overlap']
out.append('')
out.append('Replay vs logged set overlap (201 sampled tokens): ' + '; '.join(f"{p}: logged {f(v(r,'n_logged'))}, predicted {f(v(r,'n_predicted'))}, both {f(v(r,'n_both'))}, logged-not-predicted {f(v(r,'n_logged_not_predicted'))}, predicted-not-logged {f(v(r,'n_predicted_not_logged'))}, first logged {f(v(r,'first_logged'))} / predicted {f(v(r,'first_predicted'))}" for p, r in so.items()) + '.')
out.append('')
out.append('wo_check (replay bf16 output through o_proj vs logged WO, relative L2; exact fp64 through o_proj; wrong head order control):')
out.append('')
hdr = '| token | ' + ' | '.join(f'{m} replay / exact / wrong-order' for m in E['M4_wo_check']) + ' |'
out.append(hdr); out.append('|---|' + '---|' * len(E['M4_wo_check']))
toks = []
for m, r in E['M4_wo_check'].items():
    for k in r['tokens']:
        if k not in toks: toks.append(k)
for k in sorted(toks, key=lambda s: int(s.split('_')[1])):
    cells = []
    for m, r in E['M4_wo_check'].items():
        t = r['tokens'].get(k)
        cells.append('-' if t is None else f"{f(v(t,'replay_bf16_rel_l2'))} / {f(v(t,'exact_fp64_rel_l2'))} / {f(v(t,'wrong_head_order_rel_l2'))}")
    out.append(f"| {k.split('_')[1]} | " + ' | '.join(cells) + ' |')
out.append('')
Fc = F['F_campaign']
out.append('F. Campaign record')
out.append('')
out.append('| round | arm | binary | env | rc | wall s | tokens | full bytes | version | hash |')
out.append('|---|---|---|---|---|---|---|---|---|---|')
for camp, d in Fc.items():
    runs = d['runs']
    if P(runs): out.append(f'| {camp} | pending ({runs["source"]}) |'); continue
    for arm, r in runs.items():
        if arm.startswith('_'): continue
        out.append(f"| {camp} | {arm} | {f(v(r,'binary')).split('/')[-1]} | {f(v(r,'env'))} | {f(v(r,'rc')) if 'rc' in r else 'reused'} | {f(v(r,'wall'))} | {f(v(r,'tokens'))} | {f(v(r,'full_bytes'))} | {f(v(r,'version'))} | {f(v(r,'hash'))[:12]} |")
for camp, d in Fc.items():
    tk = d.get('tokens')
    if tk is None: continue
    if P(tk): out.append(f"- {camp} tokens.txt: pending"); continue
    out.append(f"- {camp} tokens.txt: " + '; '.join(f"{a}: {f(v(x))}" for a, x in tk.items() if not a.startswith('_')))
    pdn = d.get('probe_done'); out.append(f"- {camp} probe.done: {'pending' if P(pdn) else f(v(pdn))}")
for camp in ('td2-20261016', 'td3-20261016'):
    d = Fc[camp]
    out.append(f"- {camp}: verdict {'pending' if P(d['verdict']) else f(v(d['verdict']))}; " + ('steps ' + ', '.join(f"{p}: {'pending' if P(r) else 'present'}" for p, r in d['steps'].items()) if 'steps' in d else 'stats ' + ', '.join(f"{a}: {'pending' if P(r) else 'present'}" for a, r in d['stats'].items()) + '; deltas 64-63: ' + ', '.join(f"{a}: {'pending' if P(r) else f(v(r,'distinct_values'))}" for a, r in d['deltas_64_minus_63'].items())))
out.append('')
G = F['G_builds']
out.append('G. Builds and commits')
out.append('')
out.append('| build | commit | subject | configure | cache options | build wall s | sha256 of the binary |')
out.append('|---|---|---|---|---|---|---|')
for b, r in G['builds'].items():
    if P(r): out.append(f'| {b} | pending |'); continue
    out.append(f"| {b} | {f(v(r,'sha_requested')) if 'sha_requested' in r else f(v(r,'head_short'))} | {f(v(r,'head_subject'))} | {f(v(r,'configure_args'))} | {f(v(r,'tron_options'))} | {f(v(r,'build_wall'))} | {f(v(r,'sha256'))} |")
out.append('')
out.append('Worktree commits: ' + '; '.join(f"{n}: {f(v(r,'hash'))} ({f(v(r,'subject'))})" for n, r in G['commits'].items()) + '.')
out.append('')
out.append(f"predictions.md ({G['predictions_md']['source']}) is stored verbatim in facts.json at G_builds.predictions_md.value ({len(G['predictions_md']['value'])} characters).")
print('\n'.join(out))
