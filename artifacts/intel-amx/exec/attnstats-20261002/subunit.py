# Closed forms per (user, KV head, layer) for qwen decode: S=255 steps, p = P + s - 1.
# What a kernel with a smaller unit U (tokens) could take from the AVX loop,
# under software (CPU) attention and under AoF (card boundary = last complete GOF of 4).
def run(P, S=255):
    out = {}
    tot = sum(p + 1 for p in range(P, P + S))           # all keys scored (any path)
    cpu_amx = sum(64 * (p // 64) + (64 if p % 64 == 63 else 0) for p in range(P, P + S))
    cpu_avx = tot - cpu_amx                             # pending-page partial keys
    aof_cpu = sum((p % 4) + 1 for p in range(P, P + S)) # CPU tail under AoF
    aof_card = tot - aof_cpu
    out['total'] = tot; out['cpu_amx'] = cpu_amx; out['cpu_avx'] = cpu_avx
    out['aof_cpu_tail'] = aof_cpu; out['aof_card'] = aof_card
    for U in (16, 8, 4):
        # CPU attention: pending page holds k=(p mod 64)+1 keys (when < 64); unit U takes floor(k/U)*U of them
        gain_cpu = sum((lambda k: (k // U) * U if k < 64 else 0)((p % 64) + 1) for p in range(P, P + S))
        # AoF: CPU tail t=(p mod 4)+1 keys; unit U takes floor(t/U)*U
        gain_aof = sum((lambda t: (t // U) * U)((p % 4) + 1) for p in range(P, P + S))
        out[f'U{U}_cpu_gain_keys'] = gain_cpu
        out[f'U{U}_aof_gain_keys'] = gain_aof
    return out
for P in (1024, 8192):
    r = run(P)
    print(f'P={P} S=255 per (user, KV head, layer)')
    for k, v in r.items():
        print(f'  {k:22s} {v:>12,}')
    print(f"  cpu AVX share of all keys  {100*r['cpu_avx']/r['total']:.3f} %")
    print(f"  aof CPU tail share         {100*r['aof_cpu_tail']/r['total']:.3f} %")
    for U in (16, 8, 4):
        print(f"  U={U}: CPU-attention keys movable AVX->kernel {r[f'U{U}_cpu_gain_keys']:,} = {100*r[f'U{U}_cpu_gain_keys']/r['total']:.3f} % of all keys, {100*r[f'U{U}_cpu_gain_keys']/r['cpu_avx']:.1f} % of the AVX keys")
        print(f"       AoF keys movable AVX->kernel {r[f'U{U}_aof_gain_keys']:,} = {100*r[f'U{U}_aof_gain_keys']/r['total']:.4f} % of all keys")
    print()
# cross-check against the measured totals (x 2304)
r = run(1024)
assert r['cpu_amx'] * 2304 == 658243584, r['cpu_amx']*2304
assert r['cpu_avx'] * 2304 == 18579456
assert r['aof_cpu_tail'] * 2304 == 1465344
print('asserts vs exit report OK')
# AoF tail: max 4 keys. A 16-row tile holds 16 keys -> fill fraction
print('AoF tail per step: keys 1..4; one AMX tile row block = 16 tokens; fill <= 25 %')
