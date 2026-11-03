#!/usr/bin/env python3
"""render_md.py: the tables of results.md from results.json (replay.py) and wo_check json files."""
import json
import sys

r = json.load(open(sys.argv[1]))
CLS = [("pass0_0-127", "prompt 0-127 (pass 1)"), ("pass1_128-191", "prompt 128-191 (pass 2)"), ("decode", "decode (9 steps)"), ("all", "all 201")]


def e(x, p=2):
    return f"{x:.{p}e}" if isinstance(x, float) else str(x)


def pct(x):
    return f"{100 * x:.2f} %"


out = []
P = out.append
P(f"Parameters: layer {r['params']['layer']}, within-pair order {r['params']['within_pair_order']}, AMX model {r['params']['amx_model']}, "
  f"tokens {len(r['params']['tokens'])}, logged tokens {r['params']['n_tokens_logged']}, "
  f"values recovered by bf16 rounding {r['params']['values_not_decimal_exact']} of {r['params']['values_total']}.")
P("")
P("### M1 raw scores, path vs path (pooled over all heads and keys of the sampled tokens)")
P("")
P("| pair | token class | scores | fraction differing | median rel. diff of differing | median ulps of differing | max rel. diff | max ulps |")
P("|---|---|---:|---:|---:|---:|---:|---:|")
for k, v in r["M1"].items():
    if k == "within_pair_order_sensitivity":
        continue
    for c, cn in CLS:
        if c in v:
            d = v[c]
            P(f"| {k} | {cn} | {d['scores']} | {pct(d['frac_differ_pooled'])} | {e(d['median_over_tokens_of_median_rel_of_differing'])} | "
              f"{d['median_over_tokens_of_median_ulp_of_differing']:.0f} | {e(d['max_rel'])} | {d['max_ulp']} |")
P("")
P("Within-pair order sensitivity (scores that change versus odd_first, D and R, all sampled tokens):")
P("")
P("| order | D scores changed | R scores changed | of |")
P("|---|---:|---:|---:|")
for o, v in r["M1"]["within_pair_order_sensitivity"].items():
    P(f"| {o} | {v['D']} | {v['R']} | {v['n']} |")
P("")
P("### M2 attention output, model vs model (4096 elements per token: 32 heads x 128)")
P("")
P("| pair | token class | elements | bf16 elements differing (pooled) | median per-token fraction | max per-token fraction | median rel. diff fp32 | max rel. diff fp32 | max abs diff / rms |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|")


def m2rows(name, v):
    for c, cn in CLS:
        if c in v:
            d = v[c]
            P(f"| {name} | {cn} | {d['elements']} | {pct(d['frac_bf16_differ_pooled'])} | {pct(d['median_over_tokens_frac_bf16_differ'])} | "
              f"{pct(d['max_frac_bf16_differ'])} | {e(d['median_over_tokens_median_rel32'])} | {e(d['max_rel32'])} | {e(d['max_abs32_over_rms'])} |")


for k, v in r["M2"].items():
    if k == "amx_model_seq":
        for kk, vv in v.items():
            m2rows(kk + " (AMX model seq)", vv)
    else:
        m2rows(k, v)
P("")
P("### M3 output vs the exact fp64 reference (per token: 32 heads x 128 elements)")
P("")
P("| output | model | token class | mean mass-weighted bias | median bias | min bias | max bias | RMS rel. L2 | median rel. L2 | max elementwise rel. (big elements) | mean signed rel. (big) |")
P("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for grp in ("fp32_output", "bf16_output"):
    for m, v in r["M3"][grp].items():
        for c, cn in CLS:
            if c in v:
                d = v[c]
                P(f"| {grp} | {m} | {cn} | {d['mean_mass_bias']:+.2e} | {d['median_mass_bias']:+.2e} | {d['min_mass_bias']:+.2e} | {d['max_mass_bias']:+.2e} | "
                  f"{e(d['rms_rel_l2'])} | {e(d['median_rel_l2'])} | {e(d['max_rel_big'])} | {d['mean_signed_rel_big']:+.2e} |")
P("")
P("Weight mass kept by the bf16 rounding of P: sum(bf16(P)) / sum(P) - 1, per (token, head), over the sampled tokens:")
P("")
P("| token class | tokens | truncation: mean | truncation: min | truncation: max | RNE: mean | RNE: min | RNE: max |")
P("|---|---:|---:|---:|---:|---:|---:|---:|")
for c, cn in CLS:
    if c in r["M3"]["weight_mass"]:
        d = r["M3"]["weight_mass"][c]
        P(f"| {cn} | {d['tokens']} | {d['trunc_ratio_minus1_mean']:+.2e} | {d['trunc_ratio_minus1_min']:+.2e} | {d['trunc_ratio_minus1_max']:+.2e} | "
          f"{d['rne_ratio_minus1_mean']:+.2e} | {d['rne_ratio_minus1_min']:+.2e} | {d['rne_ratio_minus1_max']:+.2e} |")
P("")
P("Truncation bias against the number of attended tokens (mean over the 32 heads of one token):")
P("")
P("| token | attended tokens | trunc mass ratio - 1 | RNE mass ratio - 1 | clean output bias | clean_rne output bias | base output bias | new output bias |")
P("|---:|---:|---:|---:|---:|---:|---:|---:|")
for d in r["M3"]["bias_vs_attended"]:
    P(f"| {d['token']} | {d['attended']} | {d['trunc_mass_ratio_minus1']:+.2e} | {d['rne_mass_ratio_minus1']:+.2e} | {d['clean_output_mass_bias']:+.2e} | "
      f"{d['clean_rne_output_mass_bias']:+.2e} | {d['base_output_mass_bias']:+.2e} | {d['new_output_mass_bias']:+.2e} |")
P("")
P("### Per-token detail (selected tokens)")
P("")
P("| token | attended | D!=R scores | A!=R scores | bf16 out differ clean/newoff | newoff/new | base/new | clean/base | new/trunc | mass trunc-1 | bias clean | bias newoff | bias base | bias new | bias clean_rne |")
P("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for T in [0, 1, 2, 15, 63, 64, 127, 128, 129, 150, 191, 1024, 1039, 1040, 1056, 1087, 1090, 1150, 1200, 1278]:
    t = r["per_token"].get(str(T))
    if not t:
        continue
    m2 = t["M2"]; m3 = t["M3_fp32"]
    P(f"| {T} | {T + 1} | {pct(t['M1_D_vs_R']['frac_differ'])} | {pct(t['M1_A_vs_R']['frac_differ'])} | {pct(m2['clean_vs_newoff']['frac_bf16_differ'])} | "
      f"{pct(m2['newoff_vs_new']['frac_bf16_differ'])} | {pct(m2['base_vs_new']['frac_bf16_differ'])} | {pct(m2['clean_vs_base']['frac_bf16_differ'])} | {pct(m2['new_vs_trunc']['frac_bf16_differ'])} | "
      f"{t['mass']['trunc_ratio_mean'] - 1:+.2e} | {m3['clean']['mass_bias']:+.2e} | {m3['newoff']['mass_bias']:+.2e} | {m3['base']['mass_bias']:+.2e} | {m3['new']['mass_bias']:+.2e} | {m3['clean_rne']['mass_bias']:+.2e} |")
P("")
if "layers_base_vs_new" in r["M4"]:
    P("Campaign layers-base-vs-new.json: " + json.dumps(r["M4"]["layers_base_vs_new"])[:3000])
for p in sys.argv[2:]:
    w = json.load(open(p))
    P("")
    P(f"### WO check ({p}): model {w['model']}, layer {w['layer']}, dequant {w['info']}")
    P("")
    P("| token | replay bf16 -> Wo vs logged WO: rel. L2 | median elementwise rel. | fraction bf16-equal | exact fp64 -> Wo: rel. L2 | wrong head order: rel. L2 | other arm's logged WO vs this: rel. L2 |")
    P("|---:|---:|---:|---:|---:|---:|---:|")
    for T, d in w["tokens"].items():
        o = d.get("logged_WO_other_arm_vs_this", {}).get("rel_l2")
        P(f"| {T} | {e(d['replay_bf16']['rel_l2'])} | {e(d['replay_bf16']['median_rel_big'])} | {d['replay_bf16']['frac_bf16_equal']:.3f} | {e(d['exact_fp64']['rel_l2'])} | {e(d['wrong_head_order']['rel_l2'])} | {e(o) if o is not None else '-'} |")
print("\n".join(out))
