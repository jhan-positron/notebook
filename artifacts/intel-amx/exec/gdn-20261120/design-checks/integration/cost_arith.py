#!/usr/bin/env python3
"""Arithmetic behind the integration design. Every printed number is an estimate (est.)
unless the line says "count" (an exact count from the geometry) or "measured" (copied
from the task's M1-M3 / C1-C6 tables).  No timing is measured here.
"""
import math

# ---- measured inputs (task text) ------------------------------------------------
TDP = 16.2      # cycles, one TDPBF16PS (C1)
TLOAD = 8.4     # cycles, TILELOADD from L1 (C2)
TSTORE = 16.1   # cycles, TILESTORED (C2)
VDP = 2.0       # cycles, one VDPBF16PS = 32 multiply-adds (C3)
FMA_PER_CYCLE = 2.0   # est. (C3)
M1_REC_US = 102.1     # us per token per layer, all 32 value heads, 1 thread (M1)
M1_CONV_US = 8.15     # us per token per layer (M1)
M1_CYC_PER_VH = 8600  # cycles per value head per token (M1)
GDN_LAYERS = 24
GDN_THREADS = 16      # 1 + 15 helpers (F10)
POOL_THREADS = 56     # 55 pool workers + main (F10)

print("== A. Tile counts per (query token, page, KV head): count ==")
def attn_counts(head):
    steps = head // 32            # 32 dims per tile product
    tok_blocks = 64 // 16         # 16 K tokens per A tile
    qk_prod = steps * tok_blocks
    qk_loads = qk_prod + steps    # K tiles + packed-Q panels
    qk_stores = tok_blocks
    n_blocks = head // 16         # 16 output dims per result tile
    tok_steps = 64 // 32          # 32 tokens (16 pairs) per tile product
    pv_prod = n_blocks * tok_steps
    pv_loads = pv_prod + (n_blocks // 4) * tok_steps   # V tiles + P reloaded per 4-tile pass
    pv_stores = n_blocks
    return qk_prod + pv_prod, qk_loads + pv_loads, qk_stores + pv_stores
for head in (128, 256):
    p, l, s = attn_counts(head)
    amx = p * TDP + l * TLOAD + s * TSTORE
    macs = 2 * 4 * 64 * head                  # QK + PV, 4 query heads, 64 tokens
    avx = macs / 32 * VDP
    print(f"head {head}: {p} tile products, {l} tile loads, {s} tile stores; "
          f"tile cycles est. {amx:.0f}; AVX-512 compute-only est. {avx:.0f} cycles "
          f"({macs} multiply-adds); ratio est. {avx/amx:.2f}x (data in L1, no softmax step)")
print("check against F4 for head 128: 32 products, 40 loads, 12 stores")

print("\n== B. Packed-query scratch for a 256x4 kernel: count ==")
for head in (128, 256):
    slot = 16 * head * 2          # 16 tile rows x head dims... = (head/32) panels x 1 KiB
    print(f"head {head}: slot {slot} bytes per token; x 1024 tokens = {slot*1024/2**20:.0f} MiB per "
          f"attention worker; x 40 workers = {slot*1024*40/2**20:.0f} MiB upper bound")

print("\n== C. Attention gain from the measured attention share (M3) ==")
print("forward saving est. = share x (1 - 1/s); s = per-unit speedup of the 128x4 kernel (C6):")
print("1.26x (data from DRAM), 2.1x (data in cache). Upper bound: assumes the whole attention")
print("wall is kernel time and no clock drop.")
cells = [("1 user, prompt 1024", 0.129, 0.181), ("1 user, prompt 4096", 0.181, 0.333),
         ("8 users, prompt 1024", 0.180, 0.148), ("8 users, prompt 4096", 0.412, 0.310)]
for name, dec, pre in cells:
    row = []
    for share in (dec, pre):
        lo = share * (1 - 1 / 1.26)
        hi = share * (1 - 1 / 2.1)
        row.append((lo, hi))
    (dl, dh), (pl, ph) = row
    print(f"  {name}: decode forward -{100*dl:.1f} % to -{100*dh:.1f} % "
          f"(tokens/s +{100*(1/(1-dl)-1):.1f} % to +{100*(1/(1-dh)-1):.1f} %); "
          f"prefill pass -{100*pl:.1f} % to -{100*ph:.1f} %")

print("\n== D. GDN host work as a share of a pass: est. from M1 (stand-alone) x M2 ==")
gdn_us = M1_REC_US + M1_CONV_US
passes = [("1 user, prompt 1024, prefill", 128, 48.1), ("1 user, prompt 4096, prefill", 128, 59.1),
          ("8 users, prompt 1024, prefill", 1024, 361.0), ("8 users, prompt 4096, prefill", 1024, 445.0),
          ("1 user, prompt 1024, decode", 1, 3.58), ("1 user, prompt 4096, decode", 1, 3.90),
          ("8 users, prompt 1024, decode", 8, 8.09), ("8 users, prompt 4096, decode", 8, 12.47)]
gdn_ms = {}
for name, tokens, pass_ms in passes:
    thread_ms = GDN_LAYERS * tokens * gdn_us / 1000.0
    wall_ms = thread_ms / GDN_THREADS
    gdn_ms[name] = (wall_ms, pass_ms)
    print(f"  {name}: {GDN_LAYERS} layers x {tokens} tokens x {gdn_us:.2f} us = {thread_ms:.1f} ms "
          f"thread time / {GDN_THREADS} threads = {wall_ms:.2f} ms = {100*wall_ms/pass_ms:.1f} % of "
          f"the {pass_ms} ms pass")
print("  caveat: M1 ran one thread over a 2 MiB state; in tron a prefill worker holds a 128 KiB")
print("  working copy, and decode reads cold state. The in-tron share is not measured.")

print("\n== E. Block kernel cycles per token per value head: est. ==")
def avx_block(C):
    u = 2 * 128 * 128 / 16 / FMA_PER_CYCLE            # S0^T k_t and S0^T q_t
    upd = (128 * 128 / 16 + 128 * 128 / 16 / C) / FMA_PER_CYCLE
    gram = (C * 128 / 16) / FMA_PER_CYCLE             # half of K K^T and half of Q K^T
    fwd = (C * 8) / FMA_PER_CYCLE                     # triangular loops, 8 chunks of 16
    return u + upd + gram + fwd
def amx_block(C):
    tb = C // 16
    u = (192 * tb * TDP + (96 + 64 * tb) * TLOAD + 16 * tb * TSTORE) / C
    split = 16384 / 16 * 4.0 / C                      # 4 cycles per 16 floats: a guess
    kk = math.ceil(C / 32)
    upd = (64 * (3 * kk * TDP + 3 * kk * TLOAD + TSTORE + 20.0) + 8 * kk * TLOAD) / C
    gram = (8 * tb * tb * TDP + 12 * tb * TLOAD + 2 * tb * tb * TSTORE) / C
    fwd = (C * 8) / FMA_PER_CYCLE
    return u + split + upd + gram + fwd
traffic_now = M1_CYC_PER_VH - 2560                     # cycles not explained by arithmetic (M1)
print(f"  today: {M1_CYC_PER_VH} cycles measured (M1); arithmetic alone est. 2560; rest {traffic_now}")
res = {}
for C in (16, 32, 64):
    t = traffic_now / C                                # same state passes, once per block
    a = avx_block(C) + t
    x = amx_block(C) + t
    res[C] = (a, x)
    print(f"  C = {C}: AVX-512 block {avx_block(C):.0f} + state traffic {t:.0f} = {a:.0f} cycles "
          f"({M1_CYC_PER_VH/a:.1f}x); AMX block {amx_block(C):.0f} + {t:.0f} = {x:.0f} cycles "
          f"({M1_CYC_PER_VH/x:.1f}x; {M1_CYC_PER_VH/(x/0.923):.1f}x at -7.7 % clock, "
          f"{M1_CYC_PER_VH/(x/0.77):.1f}x at -23 % clock)")

print("\n== F. GDN operation and prefill pass with a block path, C = 32: est. ==")
a, x = res[32]
variants = [("AVX-512 block", M1_CYC_PER_VH / a), ("AMX block, -7.7 % clock", M1_CYC_PER_VH / (x / 0.923)),
            ("AMX block, -23 % clock", M1_CYC_PER_VH / (x / 0.77))]
for label, sp in variants:
    op = M1_REC_US / sp + M1_CONV_US
    line = f"  {label}: recurrence {M1_REC_US/sp:.1f} us + convolution {M1_CONV_US} us = {op:.1f} us " \
           f"per token per layer ({gdn_us/op:.1f}x on the GDN operation)"
    print(line)
    for name in ("1 user, prompt 1024, prefill", "1 user, prompt 4096, prefill",
                 "8 users, prompt 1024, prefill", "8 users, prompt 4096, prefill"):
        wall, pass_ms = gdn_ms[name]
        new = pass_ms - wall + wall * op / gdn_us
        print(f"      {name}: pass {pass_ms} -> {new:.1f} ms ({100*(new/pass_ms-1):+.0f} %)")

print("\n== G. Scratch memory per GDN worker for a block path: count ==")
today = 131072 + 8192 * 3 * 4 + 512 * 4 + 256 * 4 + 32 * 8
print(f"  today's working_set: state copy 131072 + history copy {8192*3*4} + conv row 2048 + "
      f"output row 1024 + chunk map 256 = {today} bytes ({today/1024:.1f} KiB)")
for C in (16, 32, 64):
    conv_rows = C * 512 * 4            # q, k, v of every token after the convolution, FP32
    kq_bf16 = 2 * C * 128 * 2          # normalized k and q rows as bf16 (tile A operand)
    k_t = 128 * max(C, 32) * 2         # k transposed, bf16 (A operand of the update)
    u = 2 * C * 128 * 4                # S0^T k and S0^T q, one value head at a time
    delta = C * 128 * 4
    delta_p = 3 * C * 128 * 2          # 3 bf16 pieces of the weighted deltas
    s_p = 3 * 32 * 128 * 2             # 3 bf16 pieces of one 32-row strip of S
    small = 2 * C * C * 4 + (C + 1) * (C + 1) * 4 + 4 * C * 4
    out = C * 256 * 4
    total = conv_rows + kq_bf16 + k_t + u + delta + delta_p + s_p + small + out
    print(f"  C = {C}: {total} bytes ({total/1024:.0f} KiB) extra per worker; "
          f"x {GDN_THREADS} workers = {total*GDN_THREADS/2**20:.2f} MiB")

print("\n== H. Work items per thread: count ==")
for users in (1, 8):
    items = users * 16
    for threads in (GDN_THREADS, POOL_THREADS):
        used = min(items, threads)
        print(f"  {users} user(s): {items} work items over {threads} threads -> {used} threads busy, "
              f"at most {math.ceil(items/threads)} items on one thread")
