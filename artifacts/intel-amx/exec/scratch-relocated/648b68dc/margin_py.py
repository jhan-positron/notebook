import json, sys
r = json.load(open(sys.argv[1])); s = r['summary']; m = s.get('marked_step', {})
print(f"MARGIN steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
      f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} max_tvd={s['max_tvd']} median margin_off={s['median_margin_off']}")
if m: print(f"MARKED step={sys.argv[2]} off_top1={m['off_top1']} off_top2={m['off_top2']} on_top1={m['on_top1']} on_top2={m['on_top2']} forced={m['forced_id']} margin_off={m['margin_off']:.5f} ({m['margin_off_ulps']} ulps of {m['off_top1_logit']:.4f}) margin_on_same_pair={m['margin_on_same_pair']:.5f} delta_pair={m['delta_pair']:.5f} mean|d|={m['mean_abs_delta']:.6f} max|d|={m['max_abs_delta']:.5f} frac_changed={m['frac_changed']:.3f} tvd={m['tvd']:.5f}")
else: print(f"MARKED step={sys.argv[2]}: not in the compared steps")
