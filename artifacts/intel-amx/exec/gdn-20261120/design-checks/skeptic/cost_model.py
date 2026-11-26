#!/usr/bin/env python3
"""Cost model for GDN (GatedDeltaNet) and full attention on Qwen3.5 4B.

Inputs marked MEASURED come from the task sheet (M1-M3, C1-C6).
Everything this script derives is an ESTIMATE unless it says "count".
"""
import math

HZ = 2.70e9                      # MEASURED busy-core clock on delphi-3b35
US = HZ / 1e6                    # cycles per microsecond
KIB, MIB, GB = 1024, 1024 ** 2, 1e9

# ---- MEASURED inputs ------------------------------------------------------
M1_US_PER_LAYER = 102.1          # gdn_recurrence<16,32,128,128>, 1 thread
CONV_US_PER_LAYER = 8.15         # gdn_conv1d_silu<8192>
TDP, TLOAD, TSTORE = 16.2, 8.4, 16.1      # cycles (C1, C2)
TILECFG = 229                    # LDTILECFG + TILERELEASE pair, cycles
VDPBF16 = 2.0                    # cycles per zmm VDPBF16PS (C3)
FMA_PER_CYCLE = 2.0              # assumed (C3, est.)
CLOCK_DROPS = (0.0, 0.077, 0.23)           # C4: none / sparse AMX / pure tile loop
DRAM_GBS = (13.0, 20.0)          # per-core DRAM read rate (task sheet)
M2 = {  # cell: (decode forward ms, prefill pass ms, tokens per pass)
    "1 user, prompt 1024": (3.58, 48.1, 128),
    "1 user, prompt 4096": (3.90, 59.1, 128),
    "8 users, prompt 1024": (8.09, 361.0, 1024),
    "8 users, prompt 4096": (12.47, 445.0, 1024),
}
M3 = {  # attention share of the forward wall: (decode, prefill)
    "1 user, prompt 1024": (0.129, 0.181),
    "1 user, prompt 4096": (0.181, 0.333),
    "8 users, prompt 1024": (0.180, 0.148),
    "8 users, prompt 4096": (0.412, 0.310),
}
USERS = {k: int(k.split()[0]) for k in M2}
PROMPT = {k: int(k.split()[-1]) for k in M2}

# ---- geometry (counts) ----------------------------------------------------
KD = VD = 128
CH = VD // 16                    # 8 zmm chunks per state row
GDN_LAYERS, ATT_LAYERS = 24, 8
GROUPS, HEADS_PER_GROUP = 16, 2
GDN_THREADS, POOL_THREADS = 16, 55
HEAD_BYTES = KD * VD * 4         # 64 KiB
L1, L2, L3 = 48 * KIB, 2 * MIB, 432 * MIB


def hdr(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


# ---------------------------------------------------------------------------
hdr("A. Today's kernel: arithmetic against the measured time (per token, per value head)")
fma_today = KD * CH * 3          # loop 1: 1 fma; loop 2: 2 fma, per (row, chunk)
mul_today = KD * CH * 2          # the decay multiply, done in both loops
ops_today = fma_today + mul_today
compute_bound = ops_today / FMA_PER_CYCLE
m1_head_us = M1_US_PER_LAYER / 32
m1_head_cyc = m1_head_us * US
print(f"count: {fma_today} FMA + {mul_today} multiplies = {ops_today} zmm operations")
print(f"est. compute-only bound at {FMA_PER_CYCLE:.0f} operations per cycle: {compute_bound:.0f} cycles = {compute_bound/US:.2f} us")
print(f"MEASURED (M1): {m1_head_us:.2f} us = {m1_head_cyc:.0f} cycles  ->  {m1_head_cyc/compute_bound:.1f} x the compute-only bound")
lines = HEAD_BYTES // 64
print(f"count: one value head = {HEAD_BYTES//KIB} KiB = {lines} cache lines; L1d holds {L1//KIB} KiB")
print(f"count (l1_sim.py): today {2*lines} state line fetches into L1 per token per value head")
pass_lo = (m1_head_cyc - compute_bound) / 3      # traffic and compute do not overlap
pass_hi = m1_head_cyc / 3                        # traffic alone sets the time
print(f"est. cost of moving one 64 KiB pass between L2 and L1 (2 reads + 1 write-back = 3 passes): "
      f"{pass_lo:.0f}..{pass_hi:.0f} cycles = {pass_lo/lines:.1f}..{pass_hi/lines:.1f} cycles per line")

# ---------------------------------------------------------------------------
hdr("B. Prefill: cycles per token per value head for four kernel forms")


def fp32_block(B):
    fmas = 3 * KD * CH + 8 * B + 8 * B       # 3 big products + Gram + triangular solves
    traffic = (2 * pass_lo / B, 2 * pass_hi / B)          # 2 passes over the state per block
    return fmas, (fmas / FMA_PER_CYCLE + traffic[0], fmas / FMA_PER_CYCLE + traffic[1])


def amx_block(B, split_per_chunk=(5.0, 8.0)):
    tok16, tok32 = B // 16, B // 32
    # K.S0 and Q.S0: 8 column blocks x 4 key slices x 3 bf16 pieces, two operand phases (K, Q)
    phases = 2 * math.ceil((2 * tok16 + 1) / 8)           # C + A tiles per phase must fit 8 registers
    tdp_prod = 8 * 4 * 3 * 2 * tok16
    bload_prod = 8 * 4 * 3 * phases
    aload_prod = 8 * 4 * 2 * tok16
    cstore_prod = 8 * 2 * tok16
    prod = tdp_prod * TDP + (bload_prod + aload_prod) * TLOAD + cstore_prod * TSTORE
    # update S = g*S0 + K^T . W : 64 result tiles, 3 pieces, 32 tokens deep
    tdp_upd = 64 * 3 * tok32
    load_upd = 8 * 3 * tok32 + 64 * tok32 + 64
    upd = tdp_upd * TDP + load_upd * TLOAD + 64 * TSTORE
    # two Gram matrices per key head by tile products, shared by 2 value heads
    gram = (2 * (tok16 ** 2 * 4 * TDP + (tok16 * 4 * 2) * TLOAD + tok16 ** 2 * TSTORE)) / 2
    tri = (8 * B) * B / FMA_PER_CYCLE                     # triangular solves stay FP32
    split_state = (1024 * split_per_chunk[0], 1024 * split_per_chunk[1])
    split_w = (CH * B * split_per_chunk[0], CH * B * split_per_chunk[1])
    misc = 36 * B                                         # pack K^T, delta arithmetic
    # state traffic per block: 1 read for split + products (bf16 planes of one
    # 16-column block stay in an L1 scratch), 1 read + 1 write-back for the update
    traffic = (3 * pass_lo, 3 * pass_hi)
    lo = (prod + upd + gram + tri + split_state[0] + split_w[0] + misc + traffic[0]) / B
    hi = (prod + upd + gram + tri + split_state[1] + split_w[1] + misc + traffic[1]) / B
    detail = dict(tdp_per_token=(tdp_prod + tdp_upd) / B, prod=prod / B, upd=upd / B, gram=gram / B, tri=tri / B,
                  split=(split_state[0] / B, split_state[1] / B), traffic=(traffic[0] / B, traffic[1] / B))
    return (lo, hi), detail


interchange = (compute_bound, compute_bound * 1.17)       # upper bound: 17 % port and loop overhead
print(f"{'form':46s} {'cycles/token/head':>20s} {'kernel speedup':>16s}  bit-identical to today")
print(f"{'today, token form (MEASURED M1)':46s} {m1_head_cyc:20.0f} {'1.0x':>16s}  -")
print(f"{'loop interchange, FP32 token form (est.)':46s} {interchange[0]:9.0f}..{interchange[1]:<9.0f} "
      f"{m1_head_cyc/interchange[1]:6.1f}..{m1_head_cyc/interchange[0]:.1f}x     yes (numerics_check.py [1])")
best = {}
for B in (16, 32, 64):
    f, c = fp32_block(B)
    best[("fp32", B)] = c
    print(f"{f'block form FP32 only, B={B} (est.)':46s} {c[0]:9.0f}..{c[1]:<9.0f} "
          f"{m1_head_cyc/c[1]:6.1f}..{m1_head_cyc/c[0]:.1f}x     no")
for B in (32, 64):
    c, d = amx_block(B)
    best[("amx", B)] = c
    print(f"{f'block form AMX 3 bf16 pieces, B={B} (est.)':46s} {c[0]:9.0f}..{c[1]:<9.0f} "
          f"{m1_head_cyc/c[1]:6.1f}..{m1_head_cyc/c[0]:.1f}x     no   "
          f"[{d['tdp_per_token']:.0f} tile products/token; products {d['prod']:.0f}, update {d['upd']:.0f}, "
          f"Gram {d['gram']:.0f}, solves {d['tri']:.0f}, state split {d['split'][0]:.0f}..{d['split'][1]:.0f}, state traffic {d['traffic'][0]:.0f}..{d['traffic'][1]:.0f}]")
amx = best[("amx", 64)]
fp32b = best[("fp32", 32)]
print(f"\nWhat the block form itself gives over today (FP32, B=32): {m1_head_cyc - fp32b[1]:.0f}..{m1_head_cyc - fp32b[0]:.0f} cycles saved")
print(f"What the loop interchange gives over today (bit-identical): {m1_head_cyc - interchange[1]:.0f}..{m1_head_cyc - interchange[0]:.0f} cycles saved")
print(f"(AMX rows below use B=64, the cheaper of the two)")
print(f"What AMX adds on top of the FP32 block form: {fp32b[0] - amx[1]:.0f}..{fp32b[1] - amx[0]:.0f} cycles saved (before the clock drop)")
print(f"What AMX adds on top of the loop interchange: {interchange[0] - amx[1]:.0f}..{interchange[1] - amx[0]:.0f} cycles saved (before the clock drop)")

# ---------------------------------------------------------------------------
hdr("C. Prefill: step time per key-head group, and the predicted pass time")
conv_group_us = CONV_US_PER_LAYER / GROUPS
other_us = 0.35                  # est.: normalise q,k + postprocess (2 heads) + gather; not measured
rest_us = conv_group_us + other_us
step_today = 2 * m1_head_us + rest_us
print(f"step today per group per token = 2 x {m1_head_us:.2f} us (M1) + conv {conv_group_us:.2f} us (M1) + other {other_us:.2f} us (est.) = {step_today:.2f} us")


def step(cyc, drop=0.0):
    return (2 * cyc / US + rest_us) / (1 - drop)


forms = {"loop interchange": [(step(interchange[1]), step(interchange[0]))],
         "FP32 block B=32": [(step(fp32b[1]), step(fp32b[0]))]}
for dr in CLOCK_DROPS:
    forms[f"AMX block B=64, clock -{dr*100:.1f} %"] = [(step(amx[1], dr), step(amx[0], dr))]
for name, [(hi, lo)] in forms.items():
    print(f"  {name:32s} step {lo:.2f}..{hi:.2f} us  -> {step_today/hi:.2f}..{step_today/lo:.2f}x per step")
be = 1 - step(amx[1]) / step(interchange[1]), 1 - step(amx[0]) / step(interchange[0])
print(f"  clock drop at which AMX block only equals the loop interchange: {min(be)*100:.0f}..{max(be)*100:.0f} %")

print("\nGDN share of one prefill pass (est. = 24 layers x items per thread x 128 tokens x step):")
print(f"{'cell':22s} {'pass ms':>8s} {'attn ms':>8s} {'GDN est. ms':>12s} {'GDN share':>10s} {'rest ms':>8s} | pass change: interchange | FP32 block B=32 | AMX block B=64 (clock -7.7 %) | interchange + GDN on all 55 pool threads")
for cell, (_, pass_ms, toks) in M2.items():
    u = USERS[cell]
    items_per_thread = math.ceil(u * GROUPS / GDN_THREADS)
    gdn = GDN_LAYERS * items_per_thread * 128 * step_today / 1000
    attn = M3[cell][1] * pass_ms
    rest = pass_ms - attn - gdn
    out = []
    for name in ("loop interchange", "FP32 block B=32", "AMX block B=64, clock -7.7 %"):
        hi, lo = forms[name][0]
        out.append(f"{(gdn*hi/step_today - gdn)/pass_ms*100:+.0f}..{(gdn*lo/step_today - gdn)/pass_ms*100:+.0f} %")
    hi, lo = forms["loop interchange"][0]
    rounds = math.ceil(u * GROUPS / POOL_THREADS) / items_per_thread
    out.append(f"{(gdn*hi/step_today*rounds - gdn)/pass_ms*100:+.0f}..{(gdn*lo/step_today*rounds - gdn)/pass_ms*100:+.0f} %")
    print(f"{cell:22s} {pass_ms:8.1f} {attn:8.1f} {gdn:12.1f} {gdn/pass_ms*100:9.0f}% {rest:8.1f} | " + " | ".join(out))
print("check: 'rest' (FPGA + small kernels) per 128 tokens per user should not depend on the prompt length:")
for cell, (_, pass_ms, toks) in M2.items():
    u = USERS[cell]
    gdn = GDN_LAYERS * math.ceil(u * GROUPS / GDN_THREADS) * 128 * step_today / 1000
    print(f"  {cell:22s} non-attention {pass_ms*(1-M3[cell][1]):6.1f} ms; minus GDN est. = {pass_ms*(1-M3[cell][1]) - gdn:6.1f} ms = {(pass_ms*(1-M3[cell][1]) - gdn)/u:5.1f} ms per user")

# ---------------------------------------------------------------------------
hdr("D. Decode: where the state lives, and the traffic bound")
state_layer = 32 * HEAD_BYTES
state_seq = GDN_LAYERS * state_layer
print(f"count: state per layer per sequence {state_layer//MIB} MiB; per sequence {state_seq/MIB:.1f} MiB (convolution history not counted)")
for u in (1, 2, 4, 8):
    per_thread = u * GDN_LAYERS * HEADS_PER_GROUP * HEAD_BYTES
    kv = {p: u * ATT_LAYERS * 4 * (p // 64) * 64 * KIB for p in (1024, 4096)}
    hot = {p: u * state_seq + kv[p] for p in kv}
    caches = L3 + 56 * L2
    print(f"  {u} user(s): one GDN thread touches {per_thread/MIB:5.1f} MiB of state per decode forward (L2 = {L2//MIB} MiB) | "
          f"socket: state {u*state_seq/MIB:5.0f} MiB + KV pages {kv[1024]/MIB:5.0f} (prompt 1024) or {kv[4096]/MIB:5.0f} MiB (prompt 4096) "
          f"-> {hot[1024]/MIB:5.0f} / {hot[4096]/MIB:5.0f} MiB against L3 + 56 L2 = {caches/MIB:.0f} MiB")
print("\nest. GDN wall per decode forward on one GDN thread, 8 users:")
u = 8
per_thread = u * GDN_LAYERS * HEADS_PER_GROUP * HEAD_BYTES
fetch_ms = [per_thread / (r * GB) * 1000 for r in DRAM_GBS[::-1]]
compute_ms = u * GDN_LAYERS * step_today / 1000
print(f"  fetch {per_thread/MIB:.0f} MiB from DRAM at {DRAM_GBS[0]:.0f}..{DRAM_GBS[1]:.0f} GB/s: {fetch_ms[0]:.2f}..{fetch_ms[1]:.2f} ms (the write-back of the same {per_thread/MIB:.0f} MiB is extra)")
print(f"  kernel work with the state already in L2 (M1 rate): 8 x 24 x {step_today:.2f} us = {compute_ms:.2f} ms")
gdn8 = (fetch_ms[0] + compute_ms, fetch_ms[1] + compute_ms)
print(f"  sum (no overlap assumed): {gdn8[0]:.2f}..{gdn8[1]:.2f} ms")
gdn1 = GDN_LAYERS * step_today / 1000
print(f"  1 user: 24 x {step_today:.2f} us = {gdn1:.2f} ms plus an L3 fetch of 3 MiB (rate not measured)")
for cell, (dec_ms, _, _) in M2.items():
    att = M3[cell][0] * dec_ms
    if USERS[cell] == 8:
        print(f"  {cell}: decode forward {dec_ms:.2f} ms; attention {att:.2f} ms; GDN est. {gdn8[0]:.2f}..{gdn8[1]:.2f} ms = {gdn8[0]/dec_ms*100:.0f}..{gdn8[1]/dec_ms*100:.0f} %")
    else:
        print(f"  {cell}: decode forward {dec_ms:.2f} ms; attention {att:.2f} ms; GDN est. >= {gdn1:.2f} ms = {gdn1/dec_ms*100:.0f} %")
na = {c: M2[c][0] * (1 - M3[c][0]) for c in M2}
print(f"check: non-attention part of the decode forward grows from {na['1 user, prompt 1024']:.2f}/{na['1 user, prompt 4096']:.2f} ms (1 user) to "
      f"{na['8 users, prompt 1024']:.2f}/{na['8 users, prompt 4096']:.2f} ms (8 users): +{na['8 users, prompt 1024']-na['1 user, prompt 1024']:.2f}/+{na['8 users, prompt 4096']-na['1 user, prompt 4096']:.2f} ms; "
      f"GDN est. grows by {gdn8[0]-gdn1:.2f}..{gdn8[1]-gdn1:.2f} ms")
tot = 2 * 8 * state_seq
print(f"floor: 8 users move {tot/MIB:.0f} MiB per decode forward (read once + write once). At 16 threads x {DRAM_GBS[0]:.0f}..{DRAM_GBS[1]:.0f} GB/s = "
      f"{16*DRAM_GBS[0]:.0f}..{16*DRAM_GBS[1]:.0f} GB/s this takes {tot/(16*DRAM_GBS[1]*GB)*1000:.1f}..{tot/(16*DRAM_GBS[0]*GB)*1000:.1f} ms")

print("\nest. effect of the non-AMX decode changes (per value head, cycles):")
fetch_cyc = [HEAD_BYTES / (r * GB) * HZ for r in DRAM_GBS[::-1]]
print(f"  DRAM fetch of one 64 KiB head at {DRAM_GBS[0]:.0f}..{DRAM_GBS[1]:.0f} GB/s: {fetch_cyc[0]:.0f}..{fetch_cyc[1]:.0f} cycles")
today_dram = (fetch_cyc[0] + m1_head_cyc, fetch_cyc[1] + m1_head_cyc)
loop2 = KD * CH * 3 / FMA_PER_CYCLE            # loop 2 runs from L1 after loop 1 fetched the half
single = (fetch_cyc[0] + loop2, fetch_cyc[1] + loop2)
print(f"  today, DRAM-fed (NaN scan fetches, then 2 more L2->L1 passes): {today_dram[0]:.0f}..{today_dram[1]:.0f}")
print(f"  NaN check folded + one pass per 32 KiB half, DRAM-fed (fetch + loop 2 from L1 = {loop2:.0f} cycles): {single[0]:.0f}..{single[1]:.0f} -> {today_dram[1]/single[1]:.2f}..{today_dram[0]/single[0]:.2f}x")
dec_gain = (today_dram[1] / single[1], today_dram[0] / single[0])
for cell, (dec_ms, _, _) in M2.items():
    if USERS[cell] == 8:
        save = (gdn8[0] * (1 - 1 / dec_gain[0]), gdn8[1] * (1 - 1 / dec_gain[1]))
        print(f"    {cell}: GDN est. {gdn8[0]:.2f}..{gdn8[1]:.2f} ms -> saves {min(save):.2f}..{max(save):.2f} ms = {-max(save)/dec_ms*100:.0f}..{-min(save)/dec_ms*100:.0f} % of the decode forward")
today_l2 = (m1_head_cyc + pass_lo, m1_head_cyc + pass_hi)
print(f"  today, cache-fed (1 to 4 users): {today_l2[0]:.0f}..{today_l2[1]:.0f}; after: {interchange[0]:.0f}..{interchange[0]+pass_hi:.0f} "
      f"-> {today_l2[0]/(interchange[0]+pass_hi):.1f}..{today_l2[1]/interchange[0]:.1f}x")
print(f"  more threads at 8 users: 128 work items on 16 threads = 8 per thread; on 55 threads = {math.ceil(128/55)} per thread -> up to {8/math.ceil(128/55):.2f}x, "
      f"if DRAM can supply 55 x {DRAM_GBS[0]:.0f}..{DRAM_GBS[1]:.0f} = {55*DRAM_GBS[0]:.0f}..{55*DRAM_GBS[1]:.0f} GB/s (it cannot; 12 channels of DDR5-6400 carry at most 614 GB/s)")
print(f"  AMX in decode: 1 token per tile product uses 1 of 16 tile rows; state must be split into 3 bf16 planes per token "
      f"({3*HEAD_BYTES//2//KIB} KiB written per head per token on top of the {HEAD_BYTES//KIB} KiB) -> more traffic, no gain")
print(f"  tile configuration per work item: {TILECFG} cycles = {TILECFG/(2*128*amx[0])*100:.2f} % of a 128-token prefill item (2 heads x 128 tokens x {amx[0]:.0f} cycles)")

# ---------------------------------------------------------------------------
hdr("E. Full attention with 256-wide heads: AVX-512 today against an AMX 256x4 kernel")
avx_qk = 64 * 4 * (256 // 32) * VDPBF16
avx_pv = 4 * 32 * 16 * VDPBF16
amx_tdp = 32 + 32
amx_loads = (8 + 32) + (8 + 32)
amx_stores = 4 + 16
amx_cyc = amx_tdp * TDP + amx_loads * TLOAD + amx_stores * TSTORE
print(f"count per (query token, page, KV head): AVX QK {64*4*8} + PV {4*32*16} VDPBF16PS; AMX {amx_tdp} tile products, {amx_loads} loads, {amx_stores} stores")
print(f"est. cycles: AVX {avx_qk + avx_pv:.0f}; AMX {amx_cyc:.0f} -> {(avx_qk+avx_pv)/amx_cyc:.1f}x on arithmetic alone")
avx128 = 64 * 4 * 4 * VDPBF16 + 4 * 32 * 8 * VDPBF16
amx128 = 32 * TDP + 40 * TLOAD + 12 * TSTORE
print(f"same arithmetic for the existing 128x4 kernel: AVX {avx128:.0f}; AMX {amx128:.0f} -> {avx128/amx128:.1f}x; MEASURED there: 2.1..2.6x in cache, 1.26x from DRAM (C6)")
print("so the forward-wall change below uses the MEASURED 128x4 range, 1.26x (DRAM-fed) to 2.6x (in cache):")
print(f"{'cell':22s} {'decode attn share':>18s} {'decode forward':>18s} {'tokens/s':>14s} | {'prefill attn share':>18s} {'prefill pass':>16s}")
for cell in M2:
    ds, ps = M3[cell]
    d = [-ds * (1 - 1 / x) * 100 for x in (1.26, 2.6)]
    p = [-ps * (1 - 1 / x) * 100 for x in (1.26, 2.6)]
    tps = [(1 / (1 + v / 100) - 1) * 100 for v in d]
    print(f"{cell:22s} {ds*100:17.1f}% {d[0]:8.1f}..{d[1]:.1f} % {tps[0]:+6.1f}..{tps[1]:+.1f} % | {ps*100:17.1f}% {p[0]:7.1f}..{p[1]:.1f} %")
for cell in M2:
    kv = USERS[cell] * ATT_LAYERS * 4 * (PROMPT[cell] // 64) * 64 * KIB
    print(f"  {cell}: KV bytes read per decode forward {kv/MIB:.0f} MiB (L3 = {L3//MIB} MiB) -> {'DRAM-fed, expect the low end' if kv > L3 else 'fits L3'}")

# ---------------------------------------------------------------------------
hdr("F. Summary matrix (all est.; change of wall time per cell)")
print(f"{'cell':22s} | {'decode: AMX attention 256x4':>28s} | {'decode: AMX on GDN':>18s} | {'prefill: loop interchange':>26s} | {'prefill: AMX GDN block, extra':>30s} | {'prefill: AMX attention 256x4':>29s}")
for cell, (dec_ms, pass_ms, _) in M2.items():
    u = USERS[cell]
    ds, ps = M3[cell]
    gdn = GDN_LAYERS * math.ceil(u * GROUPS / GDN_THREADS) * 128 * step_today / 1000
    ih, il = forms["loop interchange"][0]
    ah, al = forms["AMX block B=64, clock -7.7 %"][0]
    inter = ((gdn * ih / step_today - gdn) / pass_ms * 100, (gdn * il / step_today - gdn) / pass_ms * 100)
    extra = ((gdn * ah / step_today - gdn * ih / step_today) / pass_ms * 100, (gdn * al / step_today - gdn * il / step_today) / pass_ms * 100)
    print(f"{cell:22s} | {-ds*(1-1/1.26)*100:11.1f}..{-ds*(1-1/2.6)*100:.1f} % | {'0 %':>18s} | {inter[0]:12.0f}..{inter[1]:.0f} % | {min(extra):15.0f}..{max(extra):.0f} points | {-ps*(1-1/1.26)*100:13.1f}..{-ps*(1-1/2.6)*100:.1f} %")
