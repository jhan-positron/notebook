# Means from summary.md (TPS per user) and context lengths.
tps = {1024: dict(base=81.07, new=76.01, newoff=75.58, baseoff=72.40),
       8192: dict(base=17.29, new=15.39, newoff=15.44, baseoff=14.65)}
ctx = {1024: 1025, 8192: 8193}
pages = {1024: 17, 8192: 129}
L = {}
for p, a in tps.items():
    ms = {k: 1000.0 / v for k, v in a.items()}
    d_new_newoff = a['new'] - a['newoff']
    d_newoff_baseoff = a['newoff'] - a['baseoff']
    d_baseoff_base = a['baseoff'] - a['base']
    print(f"prompt {p}: new-base = {a['new']-a['base']:+.2f} TPS = "
          f"(new-newoff {d_new_newoff:+.2f}) + (newoff-baseoff {d_newoff_baseoff:+.2f}) + (baseoff-base {d_baseoff_base:+.2f}) "
          f"= {d_new_newoff + d_newoff_baseoff + d_baseoff_base:+.2f}")
    print(f"  ms/step: base {ms['base']:.3f} new {ms['new']:.3f} newoff {ms['newoff']:.3f} baseoff {ms['baseoff']:.3f}")
    print(f"  loss new-base {ms['new']-ms['base']:+.3f} ms/step; AMX gain on main (baseoff-base) {ms['baseoff']-ms['base']:+.3f} ms; "
          f"layout gain AMX-off (baseoff-newoff) {ms['baseoff']-ms['newoff']:+.3f} ms; AMX-on-unused (new-newoff) {ms['new']-ms['newoff']:+.3f} ms")
    L[p] = ms['new'] - ms['base']
    print(f"  loss per context token {1000*L[p]/ctx[p]:.3f} us; per page {L[p]/pages[p]:.4f} ms")
k = (L[8192] - L[1024]) / (ctx[8192] - ctx[1024]); c = L[1024] - k * ctx[1024]
print(f"two-cell fit loss = c + k*ctx: c = {c:+.3f} ms/step (constant per step), k = {1000*k:.3f} us per context token")
print(f"pure-proportional prediction at 8193 from p1024: {L[1024]/ctx[1024]*ctx[8193 if False else 8192]:.3f} ms vs actual {L[8192]:.3f} ms; residual {L[8192]-L[1024]/ctx[1024]*ctx[8192]:+.3f} ms ({100*(L[8192]-L[1024]/ctx[1024]*ctx[8192])/L[8192]:.0f}%)")
# Noise: sd of TPS -> sd of ms/step
for p, sd in {1024: dict(base=0.20, new=0.44), 8192: dict(base=0.02, new=0.01)}.items():
    for arm, s in sd.items():
        v = tps[p][arm]; print(f"prompt {p} {arm}: TPS sd {s} -> ms/step sd ~{1000*s/v**2:.3f}")
# Per-step constant work counts (qwen3-4b: 36 layers, 8 KV heads, tp2 -> 4 KV heads per shard; 8 users)
layers, kv_heads_per_shard, users = 36, 4, 8
rows = layers * kv_heads_per_shard * users
print(f"K rows stored per decode step per shard: {rows}; scatters: {4*rows}; cache lines touched by scatters: {64*rows} ({64*rows*64/1e6:.1f} MB); Q packs per step per shard: {rows} ({rows*4096/1e6:.1f} MB written)")
# est. scatter cost upper bound: 60 extra cycles per row at 2.7 GHz, serialized
print(f"est. extra scatter cycles if serialized on one core: {60*rows} cycles = {60*rows/2.7e3:.0f} us = {100*60*rows/2.7e3/1000/ (1000/76.01):.2f}% of a p1024 step")
