import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f))
    for kind in ('prefill', 'decode'):
        w = d[kind]
        sp = w['spans']
        mains = sorted([s for s in sp if s['cls']=='main'], key=lambda s: s['start_us'])
        helpers = [s for s in sp if s['cls']=='helper']
        attn = [s for s in sp if s['cls']=='attention']
        nh = d['threads']['helpers']; na = d['threads']['attention']
        print(f"\n== {f} {kind}: pass_ms {w['pass_ms']:.1f} n_token_jobs {w['n_token_jobs']} layer {w['layer']} window {w['window_us']}")
        print(f"{'main span':40s} {'start_us':>9s} {'dur_us':>8s} {'helpers busy':>12s} {'attn busy':>9s}")
        def busy(group, s0, s1):
            tot = 0.0
            for g in group:
                a = max(s0, g['start_us']); b = min(s1, g['start_us']+g['dur_us'])
                if b > a: tot += (b-a)
            return tot/(s1-s0) if s1>s0 else 0
        for s in mains:
            s0 = s['start_us']; s1 = s0+s['dur_us']
            print(f"{s['name'][:40]:40s} {s0:9.1f} {s['dur_us']:8.1f} {busy(helpers,s0,s1):12.2f} {busy(attn,s0,s1):9.2f}")
        # gaps between main spans
        names = sorted(set(s['name'] for s in sp))
        print('span names:', names)
