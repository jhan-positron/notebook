#!/usr/bin/env python3
"""Lead designer: counts and cost arithmetic of the merged design.

Measures nothing. Every figure is arithmetic on the task inputs:
  C1 TDPBF16PS 16.2 cycles, C2 tile load 8.4 / tile store 16.1 / tile zero 0.5,
  C3 VDPBF16PS 2.0 cycles; 2 zmm FP32 operations per cycle (est.),
  M1 102.1 us per token per layer for 32 value heads at 2.70 GHz,
  M2 pass times, M3 attention shares, C4 clock drops, C6 measured 128-wide gain.
"""
import json
import math

TDP, TLOAD, TSTORE, TZERO = 16.2, 8.4, 16.1, 0.5
VDP = 2.0
ZMM_PER_CYCLE = 2.0           # est. (C3)
GHZ = 2.70
M1_US_LAYER = 102.1           # recurrence, all 32 value heads
CONV_US_LAYER = 8.15          # convolution, all 8192 channels
N_VH = 32
M1_CYC = M1_US_LAYER / N_VH * 1e-6 * GHZ * 1e9
COMPUTE_CYC = (3072 + 2048) / ZMM_PER_CYCLE          # FMAs + multiplies per value head (F7 / 32 / 16)
LINES_TOKEN_LOOP = 2 * 1024                           # two read passes of 64 KiB into L1
LINE_CYC = (M1_CYC - COMPUTE_CYC) / LINES_TOKEN_LOOP  # M1-derived cost per 64-byte line

out = {}
print(f"M1 per value head: {M1_US_LAYER / N_VH:.4f} us = {M1_CYC:.0f} cycles at {GHZ} GHz")
print(f"operation count of the token kernel: 3072 FMA + 2048 mul = 5120 zmm ops -> {COMPUTE_CYC:.0f} cycles (est., 2 per cycle)")
print(f"M1 excess = {M1_CYC - COMPUTE_CYC:.0f} cycles over {LINES_TOKEN_LOOP} line fetches -> {LINE_CYC:.2f} cycles per line (est., M1-derived)")
print(f"check F7: 1,572,864 FMA / 16 lanes / 32 heads = {1572864 / 16 / 32:.0f}; 1,048,576 mul / 16 / 32 = {1048576 / 16 / 32:.0f}")


# ---------------------------------------------------------------- tile counts
def ceil_div(a, b):
    return -(-a // b)


def tile_counts(C):
    """Walk the loop nests of the block kernel for one chunk of C tokens.
    Registers: T0-T3 accumulators, T4-T6 the three pieces (B), T7 one A tile."""
    rb = 2 * C // 16            # row blocks of [K;Q]
    groups = ceil_div(rb, 4)    # 4 accumulators at a time
    # P1 = [K;Q] x S0 pieces, per value head
    p1 = dict(tdp=0, load=0, store=0, zero=0)
    for vb in range(8):                      # value block of 16 columns
        for g in range(groups):
            rows_in_group = min(4, rb - 4 * g)
            p1["zero"] += rows_in_group
            for kb in range(4):              # 32 key coordinates
                p1["load"] += 3              # three pieces of S0[kb, vb]
                for r in range(rows_in_group):
                    p1["load"] += 1          # A tile [row block, kb]
                    p1["tdp"] += 3
            p1["store"] += rows_in_group
    # Gram = [K;Q] x K^T, per key head (K is bf16: one piece)
    cb = ceil_div(C, 16)
    gram = dict(tdp=0, load=0, store=0, zero=0)
    for c in range(cb):
        for g in range(groups):
            rows_in_group = min(4, rb - 4 * g)
            gram["zero"] += rows_in_group
            for kb in range(4):
                gram["load"] += 1            # B tile: K^T [kb, token block c]
                for r in range(rows_in_group):
                    gram["load"] += 1
                    gram["tdp"] += 1
            gram["store"] += rows_in_group
    # update (form Y): accumulators start at zero, T = K^T x W pieces is stored to a
    # 4 KiB scratch, then AVX-512 computes S = fma(G_C, S, T). No tile load or store touches the state.
    tb = ceil_div(C, 32)
    upd = dict(tdp=0, load=0, store=0, zero=0)
    for vb in range(8):
        for g in range(2):                   # 8 key-row blocks, 4 at a time
            upd["zero"] += 4
            for t in range(tb):
                upd["load"] += 3             # W pieces [token block, vb]
                for r in range(4):
                    upd["load"] += 1         # K^T tile [key-row block, token block]
                    upd["tdp"] += 3
            upd["store"] += 4
    per_vh = {k: p1[k] + gram[k] / 2 + upd[k] for k in p1}
    return p1, gram, upd, per_vh


def tile_cyc(c):
    return c["tdp"] * TDP + c["load"] * TLOAD + c["store"] * TSTORE + c["zero"] * TZERO


print("\nTILE COUNTS PER CHUNK (P1 and update per value head, Gram per key head)")
print(f"{'C':>3} {'phase':8} {'TDPBF16PS':>10} {'loads':>6} {'stores':>7} {'zero':>5} {'cycles(L1)':>11}")
counts = {}
for C in (16, 32, 64):
    p1, gram, upd, per_vh = tile_counts(C)
    counts[C] = dict(p1=p1, gram=gram, update=upd, per_vh=per_vh)
    for name, c in (("P1", p1), ("Gram", gram), ("update", upd), ("per VH", per_vh)):
        print(f"{C:>3} {name:8} {c['tdp']:>10g} {c['load']:>6g} {c['store']:>7g} {c['zero']:>5g} {tile_cyc(c):>11.0f}")
    print(f"    per token per value head: {per_vh['tdp'] / C:.2f} TDPBF16PS, {per_vh['load'] / C:.2f} loads, {per_vh['store'] / C:.2f} stores")
out["tile_counts"] = counts


# ---------------------------------------------------------------- AMX block cost
def amx_block_cost(C):
    p1, gram, upd, per_vh = tile_counts(C)
    parts = {}
    parts["P1 tiles"] = tile_cyc(p1) / C
    parts["Gram tiles (half)"] = tile_cyc(gram) / 2 / C
    parts["update tiles"] = tile_cyc(upd) / C
    # AVX-512 parts, zmm operations per chunk per value head, at 2 per cycle (est.)
    split_s = 1024 * 8            # 4 split + 3 pack + 1 guard per zmm of state
    scale_s = 1024 * 1            # S = fma(G_C, S, T), one FMA per zmm of state
    triangle = 8 * C * (C - 1) + 40 * C
    coeff = C * (C + 1) / 2 / 16 + 3 * C * C / 16     # Gam products, CK, CQ
    w_split = 8 * C * 9           # 1 scale + 4 split + 3 pack + 1 guard per zmm of Delta
    pack = 24 * C                 # K, Q to bf16 rows, K^T tiles (per key head / 2)
    parts["split S0 (AVX)"] = split_s / ZMM_PER_CYCLE / C
    parts["S = fma(G_C,S,T) (AVX)"] = scale_s / ZMM_PER_CYCLE / C
    parts["triangle (AVX)"] = triangle / ZMM_PER_CYCLE / C
    parts["coefficients (AVX)"] = coeff / ZMM_PER_CYCLE / C
    parts["scale+split W (AVX)"] = w_split / ZMM_PER_CYCLE / C
    parts["pack K,Q,K^T (AVX)"] = pack / ZMM_PER_CYCLE / C
    l1_total = sum(parts.values())
    # memory traffic scenario: lines that come from L2, priced at the M1-derived line cost
    state_lines = 2 * 1024                              # P1 read + update read (write-back folded in, as in M1)
    kq = 2 * C * 256 // 64                              # bf16 K and Q rows
    r0q0 = 2 * (2 * C * 512 // 64)                      # written by P1, read by the triangle
    v_rows = C * 512 // 64
    coeffs = 2 * C * C * 4 // 64
    w_tiles = 2 * (3 * C * 128 * 2 // 64)               # written, then loaded
    kt = C * 128 * 2 // 64
    scratch_lines = kq + r0q0 + v_rows + coeffs + w_tiles + kt
    if C == 64:
        scratch_lines += 4096 - kq                      # lead_l1_sim.py: every A-tile line of P1 misses L1 at C = 64
    traffic = (state_lines + scratch_lines) * LINE_CYC / C
    return parts, l1_total, l1_total + traffic, state_lines, scratch_lines


print("\nAMX BLOCK KERNEL, cycles per token per value head (est.)")
amx = {}
for C in (16, 32, 64):
    parts, lo, hi, sl, scl = amx_block_cost(C)
    amx[C] = dict(parts=parts, l1=lo, l2=hi)
    print(f"C = {C}")
    for k, v in parts.items():
        print(f"   {k:24s} {v:7.1f}")
    print(f"   {'TOTAL, all loads from L1':24s} {lo:7.0f}")
    print(f"   lines from L2 per chunk: state {sl}, scratch {scl} -> +{(sl + scl) * LINE_CYC / C:.0f} cycles per token")
    print(f"   {'TOTAL, with L2 traffic':24s} {hi:7.0f}")
out["amx_block"] = amx

# ---------------------------------------------------------------- slice replay
W = 32                                               # tokens per window
slice_state_lines = 2 * 512 / W                      # two 32 KiB slices loaded once per window
slice_input_lines = 2 * (8 + 8 + 4 + 4)              # k, q, v, o rows, once per slice
slice_lo = COMPUTE_CYC
slice_hi = COMPUTE_CYC + (slice_state_lines + slice_input_lines) * LINE_CYC
print("\nSLICE REPLAY (same arithmetic as today, 64-column slices), cycles per token per value head (est.)")
print(f"   compute bound {slice_lo:.0f}; lines from L2 per token: state {slice_state_lines:.0f} (today 2048), inputs {slice_input_lines}"
      f" -> {slice_hi:.0f} with L2 traffic")
print(f"   speedup against M1: {M1_CYC / slice_hi:.2f}x to {M1_CYC / slice_lo:.2f}x")
out["slice"] = dict(lo=slice_lo, hi=slice_hi)

# ---------------------------------------------------------------- kernel speedups with the clock
print("\nKERNEL TIME per token per value head (est.), clock = 2.70 GHz x (1 - drop)")
print(f"   today (M1, measured): {M1_CYC / GHZ / 1e3:.3f} us")
print(f"   slice replay: {slice_lo / GHZ / 1e3:.3f} to {slice_hi / GHZ / 1e3:.3f} us (no clock drop: AVX-512 only)")
speed = {}
for C in (32, 64):
    for drop in (0.0, 0.077, 0.23):
        lo_us = amx[C]["l1"] / (GHZ * (1 - drop)) / 1e3
        hi_us = amx[C]["l2"] / (GHZ * (1 - drop)) / 1e3
        m1_us = M1_CYC / GHZ / 1e3
        sl_lo_us, sl_hi_us = slice_lo / GHZ / 1e3, slice_hi / GHZ / 1e3
        speed[(C, drop)] = (lo_us, hi_us)
        print(f"   AMX block C={C}, clock -{drop * 100:4.1f} %: {lo_us:.3f} to {hi_us:.3f} us"
              f" | vs M1 {m1_us / hi_us:.1f}x to {m1_us / lo_us:.1f}x"
              f" | vs slice replay {sl_lo_us / hi_us:.2f}x to {sl_hi_us / lo_us:.2f}x")
out["amx_speed"] = {f"C{C}_drop{drop}": v for (C, drop), v in speed.items()}

# ---------------------------------------------------------------- attention 256x4
print("\nFULL ATTENTION per (query token, 64-token page, KV head)")
for head in (128, 256):
    steps = head // 32
    qk = dict(tdp=steps * 4, load=steps * (1 + 4), store=4)
    groups = head // 64
    pv = dict(tdp=groups * 2 * 4, load=groups * 2 * (1 + 4), store=groups * 4)
    tot = {k: qk[k] + pv[k] for k in qk}
    cyc = tot["tdp"] * TDP + tot["load"] * TLOAD + tot["store"] * TSTORE
    avx = 64 * 4 * (head // 32) + 4 * 32 * (head // 16)
    print(f"   head {head}: QK {qk}, PV {pv}, total {tot} -> {cyc:.0f} cycles in L1 (est.);"
          f" AVX-512 {avx} VDPBF16PS x {VDP} = {avx * VDP:.0f} cycles; count ratio {avx * VDP / cyc:.2f}x")
    out[f"attn_{head}"] = dict(qk=qk, pv=pv, total=tot, amx_cycles=cyc, avx_cycles=avx * VDP)
print(f"   4 query tokens per call, head 256: {out['attn_256']['amx_cycles'] / 4:.0f} cycles of tile work per token (est.)")
print(f"   packed Q slot head 256: {8 * 16 * 16 * 2 * 2} bytes; 1024 tokens -> {8 * 16 * 16 * 2 * 2 * 1024 / 2**20:.0f} MiB per worker,"
      f" 40 workers -> {8 * 16 * 16 * 2 * 2 * 1024 * 40 / 2**20:.0f} MiB upper bound")

# ---------------------------------------------------------------- forward level
cells = [  # name, tokens per prefill pass, prefill pass ms, decode forward ms, decode tok/s, attn share decode, attn share prefill, users
    ("1 user, prompt 1024", 128, 48.1, 3.58, 276.0, 0.129, 0.181, 1),
    ("1 user, prompt 4096", 128, 59.1, 3.90, 252.0, 0.181, 0.333, 1),
    ("8 users, prompt 1024", 1024, 361.0, 8.09, 121.0, 0.180, 0.148, 8),
    ("8 users, prompt 4096", 1024, 445.0, 12.47, 77.4, 0.412, 0.310, 8),
]
GDN_US = M1_US_LAYER + CONV_US_LAYER
THREADS = 16
LAYERS = 24
print("\nFORWARD LEVEL (est.; GDN share assumes M1 speed on 16 evenly loaded threads)")
print(f"   GDN host work per token per layer today: {M1_US_LAYER} + {CONV_US_LAYER} = {GDN_US:.2f} us (M1)")
# GDN host work per token per layer (us) = 32 value heads x recurrence + convolution.
# Under AMX the whole GDN operation runs at the lower clock, so the convolution slows down too.
def gdn_us(rec_cyc, drop):
    return N_VH * rec_cyc / (GHZ * (1 - drop)) / 1e3 + CONV_US_LAYER / (1 - drop)


scen = {
    "slice replay": (gdn_us(slice_hi, 0.0), gdn_us(slice_lo, 0.0)),
    "AMX block C=32": (gdn_us(amx[32]["l2"], 0.23), gdn_us(amx[32]["l1"], 0.0)),
}
print(f"   GDN host work per token per layer (est.): slice replay {scen['slice replay'][1]:.1f} to {scen['slice replay'][0]:.1f} us;"
      f" AMX block C=32 {scen['AMX block C=32'][1]:.1f} to {scen['AMX block C=32'][0]:.1f} us (worst = L2 traffic and clock -23 %, convolution slowed too)")
fw = {}
for name, tokens, pass_ms, dec_ms, tps, a_dec, a_pre, users in cells:
    gdn_ms = tokens * LAYERS * GDN_US / THREADS / 1e3
    share = gdn_ms / pass_ms
    dense = 0.874 if "1024" in name else 0.969

    def change(us):
        return (tokens * LAYERS * us / THREADS / 1e3 - gdn_ms) / pass_ms

    sl = tuple(change(u) for u in scen["slice replay"])
    ax = tuple(change(u) for u in scen["AMX block C=32"])
    att_dec = (a_dec * (1 - 1 / 1.26), a_dec * (1 - 1 / 2.6))
    att_pre = (a_pre * (1 - 1 / 1.26), a_pre * (1 - 1 / 2.6))
    att_pre_d = (att_pre[0] * dense, att_pre[1] * dense)
    dec_gdn_ms = users * LAYERS * GDN_US / THREADS / 1e3
    fw[name] = dict(gdn_ms=gdn_ms, share=share, slice=sl, amx=ax, att_dec=att_dec, att_pre=att_pre, att_pre_dense=att_pre_d,
                    dec_gdn_ms=dec_gdn_ms, dec_gdn_share=dec_gdn_ms / dec_ms)
    print(f" {name}")
    print(f"   prefill pass {pass_ms} ms; GDN host {tokens} x {LAYERS} x {GDN_US:.2f} us / {THREADS} = {gdn_ms:.2f} ms = {share * 100:.1f} % of the pass")
    print(f"   slice replay: pass {sl[0] * 100:+.1f} % .. {sl[1] * 100:+.1f} %  ({pass_ms * (1 + sl[0]):.1f} .. {pass_ms * (1 + sl[1]):.1f} ms)")
    print(f"   AMX block C=32: pass {ax[0] * 100:+.1f} % .. {ax[1] * 100:+.1f} %  ({pass_ms * (1 + ax[0]):.1f} .. {pass_ms * (1 + ax[1]):.1f} ms)"
          f"  -> extra over slice replay {((ax[0] - sl[0]) * 100):+.1f} .. {((ax[1] - sl[1]) * 100):+.1f} points")
    print(f"   attention 256x4 (1.26x..2.6x), prefill pass: upper bound -{att_pre[0] * 100:.1f} % .. -{att_pre[1] * 100:.1f} %;"
          f" x dense share {dense}: -{att_pre_d[0] * 100:.1f} % .. -{att_pre_d[1] * 100:.1f} %")
    print(f"   attention 256x4, decode forward {dec_ms} ms upper bound: -{att_dec[0] * 100:.1f} % .. -{att_dec[1] * 100:.1f} %"
          f"; tokens/s {tps} -> {tps / (1 - att_dec[0]):.0f} .. {tps / (1 - att_dec[1]):.0f}"
          f" (+{(1 / (1 - att_dec[0]) - 1) * 100:.1f} % .. +{(1 / (1 - att_dec[1]) - 1) * 100:.1f} %)")
    print(f"   decode GDN host lower bound (M1 speed): {users} x {LAYERS} x {GDN_US:.2f} us / {THREADS} = {dec_gdn_ms:.3f} ms"
          f" = {dec_gdn_ms / dec_ms * 100:.1f} % of the decode forward")
    print(f"   prefill pass, attention 256x4 (dense-corrected) + slice replay: {(sl[0] - att_pre_d[0]) * 100:+.1f} % .. {(sl[1] - att_pre_d[1]) * 100:+.1f} %;"
          f" with the AMX block instead of slice replay: {(ax[0] - att_pre_d[0]) * 100:+.1f} % .. {(ax[1] - att_pre_d[1]) * 100:+.1f} %")
out["forward"] = fw

# dense share of prefill K tokens (pages written in the same pass are not dense)
print("\nDENSE SHARE OF SCORED K TOKENS IN PREFILL (est., 128-token chunks, 1 sequence)")
for prompt in (1024, 4096):
    chunks = prompt // 128
    old = sum(128 * j for j in range(chunks)) / chunks       # tokens in earlier chunks, average per query token
    inchunk = sum(range(1, 129)) / 128                        # visible tokens of the own chunk, average
    print(f"   prompt {prompt}: old {old:.0f} tokens (dense pages) + own chunk {inchunk:.1f} tokens -> dense share {old / (old + inchunk) * 100:.1f} %")
    out[f"dense_share_{prompt}"] = old / (old + inchunk)

# decode: why tiles lose
print("\nGDN DECODE WITH TILES (rejected)")
print(f"   [k;q] x S: 8 value blocks x 4 key blocks x 3 pieces = 96 TDPBF16PS = {96 * TDP:.0f} cycles for 2 real rows;"
      f" AVX-512: 2 x 1024 FMA / 2 per cycle = 1024 cycles (est.)")
print(f"   rank-one update with tiles: 192 TDPBF16PS + 64 loads + 64 stores = {192 * TDP + 64 * TLOAD + 64 * TSTORE:.0f} cycles; AVX-512: 1024 FMA = 512 cycles (est.)")
print(f"   split of the state every token: 1024 zmm x 8 ops / 2 = 4096 cycles (est.), 96 KiB written")
print(f"   state touched per GDN thread per decode forward: 1 user {24 * 131072 / 2**20:.0f} MiB, 8 users {8 * 24 * 131072 / 2**20:.0f} MiB (L2 = 2 MiB)")

# scratch
print("\nSCRATCH PER WORKER (bytes), window of 32 tokens, one key-head group")
k_f32 = 2 * 32 * 128 * 4
v_o = 2 * 2 * 32 * 128 * 4
kq_bf16 = 2 * 32 * 128 * 2
kt = 32 * 128 * 2
r0q0 = 2 * 32 * 128 * 4
wt = 3 * 32 * 128 * 2
split = 12 * 1024
coeffs = 2 * 2 * 32 * 32 * 4
total = k_f32 + v_o + kq_bf16 + kt + r0q0 + wt + split + coeffs + 131072
print(f"   k,q FP32 {k_f32}; v,o FP32 {v_o}; K,Q bf16 {kq_bf16}; K^T {kt}; R0/Q0 {r0q0}; W pieces {wt}; S0 split scratch {split};"
      f" coefficients {coeffs}; blocked working copy 131072 -> {total} bytes = {total / 1024:.0f} KiB (today 232,704 bytes)")

json.dump(out, open(__file__.replace(".py", ".json"), "w"), indent=1, default=str)
