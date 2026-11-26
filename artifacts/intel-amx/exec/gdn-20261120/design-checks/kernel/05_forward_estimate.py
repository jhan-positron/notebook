"""Check 5: what the kernel estimates mean for a whole forward pass (est.).

This is plain arithmetic on the numbers given in the task (M1, M2, M3, F10).
Assumptions, each one unverified until the GDN/FPGA trace exists:
  A1  the 16 GDN threads share the work evenly and each runs at the M1
      single-thread kernel speed (3.19 us per value head, 8.15 us per layer
      for the convolution of all 8192 channels)
  A2  GDN host work and attention each sit on the critical path of a pass,
      so time removed from them is removed from the pass
  A3  every attention visit can take the AMX path (upper bound; partial
      pages stay on AVX)
"""
LAYERS_GDN = 24
REC_US = 102.1          # per token per layer, all 32 value heads, 1 thread (M1)
CONV_US = 8.15          # per token per layer (M1)
THREADS = 16            # F10

cells = [               # name, tokens per prefill pass, prefill pass ms, decode ms, attn share prefill, decode
    ("1 user, prompt 1024", 128, 48.1, 3.58, 0.181, 0.129),
    ("1 user, prompt 4096", 128, 59.1, 3.90, 0.333, 0.181),
    ("8 users, prompt 1024", 1024, 361.0, 8.09, 0.148, 0.180),
    ("8 users, prompt 4096", 1024, 445.0, 12.47, 0.310, 0.412),
]
K_REC = {"low (C=32, L2 scenario, clock -23 %)": 4.8,
         "high (C=64, L1 scenario, clock -7.7 %)": 9.5}
X_ATTN = {"data from DRAM (1.26x)": 1.26, "data in cache (2.1x)": 2.1, "data in cache (2.6x)": 2.6}

per_tok_ms = LAYERS_GDN * (REC_US + CONV_US) / THREADS / 1000.0
print(f"GDN host CPU per token: {LAYERS_GDN * (REC_US + CONV_US) / 1000:.3f} ms "
      f"(recurrence {LAYERS_GDN * REC_US / 1000:.3f} + convolution {LAYERS_GDN * CONV_US / 1000:.3f})")
print(f"GDN host wall per token on {THREADS} threads (A1): {per_tok_ms:.4f} ms\n")

print("PREFILL: GDN block form")
for name, toks, pass_ms, _, s_attn, _ in cells:
    gdn = toks * per_tok_ms
    print(f"  {name}: GDN host wall {gdn:.1f} ms of {pass_ms:.1f} ms = {100 * gdn / pass_ms:.0f} % (est.)")
    for label, k in K_REC.items():
        new_gdn = toks * LAYERS_GDN * (REC_US / k + CONV_US) / THREADS / 1000.0
        new_pass = pass_ms - gdn + new_gdn
        print(f"      recurrence {k:.1f}x faster, {label}: pass {pass_ms:.1f} -> {new_pass:.1f} ms "
              f"({100 * (new_pass / pass_ms - 1):+.0f} %)")

print("\nPREFILL: 256-wide AMX attention alone (A2, A3)")
for name, _, pass_ms, _, s_attn, _ in cells:
    line = ", ".join(f"{lab}: {-100 * s_attn * (1 - 1 / x):+.0f} %" for lab, x in X_ATTN.items())
    print(f"  {name}: attention share {100 * s_attn:.1f} % -> pass time {line}")

print("\nPREFILL: both together (low GDN + 1.26x attention ... high GDN + 2.6x attention)")
for name, toks, pass_ms, _, s_attn, _ in cells:
    gdn = toks * per_tok_ms
    res = []
    for k, x in ((4.8, 1.26), (9.5, 2.6)):
        new_gdn = toks * LAYERS_GDN * (REC_US / k + CONV_US) / THREADS / 1000.0
        new_pass = pass_ms - gdn + new_gdn - pass_ms * s_attn * (1 - 1 / x)
        res.append(100 * (new_pass / pass_ms - 1))
    print(f"  {name}: pass time {res[0]:+.0f} % to {res[1]:+.0f} %")

print("\nDECODE: GDN gets no AMX gain; 256-wide AMX attention alone (A2, A3)")
for name, _, _, dec_ms, _, s_attn in cells:
    gdn_share = per_tok_ms * (8 if name.startswith("8") else 1) / dec_ms
    line = ", ".join(f"{lab}: tokens/s {100 * (1 / (1 - s_attn * (1 - 1 / x)) - 1):+.0f} %"
                     for lab, x in X_ATTN.items())
    print(f"  {name}: attention share {100 * s_attn:.1f} %, GDN host share >= "
          f"{100 * gdn_share:.0f} % (A1) -> {line}")
