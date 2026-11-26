#!/usr/bin/env python3
"""Corrected numbers for the code-fit verifier (all est., from the spec's own kernel figures)."""
today = 3.19                      # us per token per value head (M1)
g1 = (0.95, 1.04)                 # spec, slice replay
g2 = {"2.70 GHz": (0.29, 0.45), "-7.7 %": (0.32, 0.49), "-23 %": (0.38, 0.58)}   # spec, AMX block
cov = 96 / 128                    # tokens of an off-grid 128-token chain that sit in full blocks
print("[A] chain that starts off the 32-token grid: 96 of 128 tokens in blocks (75.0 %)")
for clock, (lo, hi) in g2.items():
    b_lo = cov * lo + (1 - cov) * g1[0]
    b_hi = cov * hi + (1 - cov) * g1[1]
    print(f"    {clock:9s}: blended {b_lo:.3f} to {b_hi:.3f} us per token per value head;"
          f" vs today {today/b_hi:.1f}x to {today/b_lo:.1f}x; vs G1 {g1[1]/b_hi:.2f}x to {g1[0]/b_lo:.2f}x")
print("    spec, all tokens in blocks: vs today 5.5x to 11.0x; vs G1 1.6x to 3.6x")
lo, hi = 3.9, 9.0
print(f"    extra prefill-pass points over G1: spec {lo} to {hi}; x 0.75 = {lo*cov:.1f} to {hi*cov:.1f}")

print("[B] bytes one dense attention visit touches (count), L1D = 49,152 bytes")
for w in (128, 256):
    k = 64 * w * 2; v = 64 * w * 2; q = 16 * w * 2; o = 16 * w * 4; st = 64 * 16 * 4; p = 16 * 64 * 2
    print(f"    width {w}: K {k} + packed Q {q} + s_transposed {st} = {k+q+st} (QK);"
          f" V {v} + PV store target {o} + P {p} = {v+o+p} (PV); K + V = {k+v}")
print("    packed Q of one 128-token chunk: width 128 =", 128 * 4096, "bytes; width 256 =", 128 * 8192, "bytes")

print("[C] counts")
print("    I2 rows: 16 GDN workers x 24 operations x 64 bytes =", 16 * 24 * 64)
print("    working_set after G1 + G2: 232,704 +", 229376, "+", 110592, "=", 232704 + 229376 + 110592, "bytes per GDN worker")
print("    16 GDN workers:", 16 * (232704 + 229376 + 110592), "bytes")
print("    coefficient scratch if G, KK, QK, CK, CQ are all kept (5 x 32 x 32 x 4):", 5 * 32 * 32 * 4)
