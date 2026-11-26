"""Check 4: count tile instructions by walking the loop nests of the design,
then turn the counts into cycles with the measured instruction costs.

Measured inputs (from the task statement):
  C1  TDPBF16PS            16.2 cycles
  C2  TILELOADD from L1     8.4 cycles, TILESTORED 16.1 cycles, TILEZERO 0.5
  C3  zmm FP32 FMA          2 per cycle (est., not measured by us)
  M1  existing kernel       3.19 us per value head per token = 8,613 cycles
                            at 2.70 GHz (102.1 us / 32 value heads)

Two memory scenarios bracket the unknown cache behaviour:
  L1  every tile load costs the L1 figure (lower bound)
  L2  the first load of every operand tile in a phase comes from L2 and
      pays an extra cost per 64-byte line; that cost is derived from M1:
      (8,613 measured - 2,560 compute-only) / 2,048 lines fetched = 2.96
      cycles per line (est.; it charges the whole M1 excess to line fetches)

All results are cycles per token per value head.
"""
import json
import math

TDP, TLOAD, TSTORE, TZERO = 16.2, 8.4, 16.1, 0.5
FMA_PER_CYCLE = 2.0
GHZ = 2.70
M1_US_PER_VH = 102.1 / 32
M1_CYC = M1_US_PER_VH * GHZ * 1000.0
KERNEL_COMPUTE_ONLY = (2 + 3) * 128 * 8 / FMA_PER_CYCLE          # 2 mul + 3 fma per chunk
LINE_PENALTY = (M1_CYC - KERNEL_COMPUTE_ONLY) / (2 * 1024)      # cycles per line from L2
TILE_L2_EXTRA = 16 * LINE_PENALTY


class Count:
    def __init__(self):
        self.dp = self.load = self.store = self.zero = self.first_touch = 0

    def cycles(self, l2):
        c = self.dp * TDP + self.load * TLOAD + self.store * TSTORE + self.zero * TZERO
        if l2:
            c += self.first_touch * TILE_L2_EXTRA
        return c

    def __iadd__(self, o):
        for f in ("dp", "load", "store", "zero", "first_touch"):
            setattr(self, f, getattr(self, f) + getattr(o, f))
        return self


def p1_products(C):
    """[K;Q] (2C x 128, bf16) x S0 (128 x 128, 3 bf16 pieces). Per value head.
    tiles: T0-T3 accumulators (4 row blocks), T4-T6 the 3 pieces of one S0
    block, T7 one [K;Q] block."""
    n = Count()
    row_blocks = 2 * C // 16
    seen_a, seen_b = set(), set()
    for col in range(8):                       # 16 value coordinates each
        for rg in range(0, row_blocks, 4):
            nacc = min(4, row_blocks - rg)
            n.zero += nacc
            for kb in range(4):                # 32 key coordinates each
                for piece in range(3):
                    n.load += 1
                    seen_b.add((piece, kb, col))
                for r in range(nacc):
                    n.load += 1
                    seen_a.add((rg + r, kb))
                    n.dp += 3
            n.store += nacc
    n.first_touch = len(seen_a) + len(seen_b)
    return n


def gram_products(C):
    """[K;Q] (2C x 128) x K^T (128 x C). Per KEY head (shared by 2 value heads)."""
    n = Count()
    row_blocks, col_blocks = 2 * C // 16, C // 16
    seen = set()
    for cb in range(col_blocks):
        for rg in range(0, row_blocks, 4):
            nacc = min(4, row_blocks - rg)
            n.zero += nacc
            for kb in range(4):
                n.load += 1
                seen.add(("b", cb, kb))
                for r in range(nacc):
                    n.load += 1
                    seen.add(("a", rg + r, kb))
                    n.dp += 1
            n.store += nacc
    n.first_touch = len(seen)
    return n


def update_products(C):
    """S (128 x 128 FP32, the accumulator) += K^T (128 x C) x W (C x 128, 3 pieces).
    Per value head. A chunk of 16 tokens is zero padded to one 32-token block."""
    n = Count()
    tok_blocks = math.ceil(C / 32)
    seen = set()
    for col in range(8):
        for rg in range(0, 8, 4):              # 8 blocks of 16 key coordinates
            n.load += 4                        # accumulators come from S
            for r in range(4):
                seen.add(("c", rg + r, col))
            for tb in range(tok_blocks):
                n.load += 3
                for piece in range(3):
                    seen.add(("b", piece, tb, col))
                for r in range(4):
                    n.load += 1
                    seen.add(("a", rg + r, tb))
                    n.dp += 3
            n.store += 4
    n.first_touch = len(seen)
    return n


def avx_parts(C, l2):
    """AVX-512 work of the block form, cycles per chunk per value head (est.)."""
    split_s = 1024 * 4.0                       # 1024 zmm of S0: 8 ALU ops each, 2 per cycle
    if l2:
        split_s += (1024 + 1536) * LINE_PENALTY  # read S0, write 3 piece planes
    fwd = (8 * C * C + 32 * C) / FMA_PER_CYCLE   # delta and output triangles
    if l2:
        fwd += 2 * C * 8 * LINE_PENALTY          # first touch of R0 and Q0 rows
    gam = 3 * C * C / 32 / 2.0                   # Gam, M, N as 16-lane multiplies
    split_w = 8 * C * 4.0                        # scale by Gam and split W
    pack = 16.0 * C                              # bf16 pack of K, Q, K^T (half of a key head)
    return dict(split_s=split_s, forward=fwd, gamma=gam, split_w=split_w, pack=pack)


def block_amx(C, l2):
    p1, gr, up = p1_products(C), gram_products(C), update_products(C)
    avx = avx_parts(C, l2)
    parts = dict(p1=p1.cycles(l2), gram=gr.cycles(l2) / 2.0, update=up.cycles(l2), **avx)
    return parts, (p1, gr, up)


def block_avx_only(C, l2):
    """The same block algebra with FP32 FMAs in place of tile products (est.)."""
    fma = 2 * C * 128 * 8 + C * 128 * 8 + C * C * 128 / 16 / 2.0   # P1, update, gram (per VH)
    fwd = (8 * C * C + 32 * C)
    cyc = (fma + fwd) / FMA_PER_CYCLE + 1024 / FMA_PER_CYCLE
    if l2:   # S streamed once per 4 token rows (P1: 2C rows) and once per 4 tokens (update)
        cyc += (2 * C / 4 + C / 4) * 1024 * LINE_PENALTY
    return cyc


if __name__ == "__main__":
    print(f"M1 baseline: {M1_US_PER_VH:.3f} us = {M1_CYC:.0f} cycles per token per value head")
    print(f"compute-only count of the existing kernel: {KERNEL_COMPUTE_ONLY:.0f} cycles")
    print(f"derived L2 line cost: {LINE_PENALTY:.2f} cycles per line "
          f"(+{TILE_L2_EXTRA:.1f} cycles per 1 KiB tile)\n")

    out = {"m1_cycles": M1_CYC, "rows": []}
    print("Tile instruction counts per chunk (P1 and update per value head, Gram per key head)")
    print(f"{'C':>3s} {'phase':8s} {'TDPBF16PS':>10s} {'TILELOADD':>10s} {'TILESTORED':>11s} {'TILEZERO':>9s}")
    for C in (16, 32, 64):
        _, (p1, gr, up) = block_amx(C, False)
        tot = Count()
        for name, c in (("P1", p1), ("Gram", gr), ("update", up)):
            print(f"{C:3d} {name:8s} {c.dp:10d} {c.load:10d} {c.store:11d} {c.zero:9d}")
        print(f"{C:3d} {'per VH':8s} {p1.dp + gr.dp // 2 + up.dp:10d} "
              f"{p1.load + gr.load // 2 + up.load:10d} {p1.store + gr.store // 2 + up.store:11d} "
              f"{p1.zero + gr.zero // 2 + up.zero:9d}   (Gram halved)")
        print(f"{'':3s} {'per token':8s} {(p1.dp + gr.dp / 2 + up.dp) / C:10.2f} "
              f"{(p1.load + gr.load / 2 + up.load) / C:10.2f} "
              f"{(p1.store + gr.store / 2 + up.store) / C:11.2f}")

    print("\nCycles per token per value head (est.)")
    hdr = ["p1", "gram", "update", "split_s", "forward", "gamma", "split_w", "pack"]
    print(f"{'C':>3s} {'mem':>3s} " + " ".join(f"{h:>8s}" for h in hdr) +
          f" {'TOTAL':>8s} {'vs M1':>6s} {'AVX block':>10s} {'vs M1':>6s}")
    for C in (16, 32, 64):
        for l2 in (False, True):
            parts, _ = block_amx(C, l2)
            per_tok = {k: v / C for k, v in parts.items()}
            total = sum(per_tok.values())
            avx = block_avx_only(C, l2) / C
            print(f"{C:3d} {'L2' if l2 else 'L1':>3s} " +
                  " ".join(f"{per_tok[h]:8.0f}" for h in hdr) +
                  f" {total:8.0f} {M1_CYC / total:5.1f}x {avx:10.0f} {M1_CYC / avx:5.1f}x")
            out["rows"].append(dict(C=C, mem="L2" if l2 else "L1", total=total, avx_block=avx,
                                    **per_tok))

    print("\nTime per token per value head with the clock taken into account (est.)")
    print("  clock scenarios: AMX clock = 2.70 GHz x (1 - drop); drop 7.7 % and 23 % are the")
    print("  two values measured on the sister machine (C4)")
    for C in (32, 64):
        for l2 in (False, True):
            total = sum(v / C for v in block_amx(C, l2)[0].values())
            for drop in (0.0, 0.077, 0.23):
                us = total / (GHZ * (1 - drop) * 1000.0)
                print(f"  C={C} {'L2' if l2 else 'L1'} clock drop {100 * drop:4.1f} %: "
                      f"{us:.3f} us  -> {M1_US_PER_VH / us:.1f}x faster than M1 ({M1_US_PER_VH:.2f} us)")

    # ---------------------------------------------------------------- decode
    print("\nDecode, one token (C = 1): what a tile product could do")
    dp_r = 3 * 4 * 8                    # [k;q] x S pieces: 3 pieces x 4 inner x 8 column blocks
    useful = 2 * 128 * 128              # FP32-equivalent multiply-adds wanted (k and q rows)
    print(f"  [k;q] x S with TDPBF16PS: {dp_r} tile products = {dp_r * TDP:.0f} cycles; "
          f"useful rows 2 of 16 = {100 * 2 / 16:.1f} %")
    print(f"    FP32-equivalent multiply-adds per cycle: {useful / (dp_r * TDP):.1f} "
          f"(two zmm FMA per cycle give {16 * FMA_PER_CYCLE:.0f})")
    dp_u = 3 * 64
    print(f"  rank-one update S += k delta^T with TDPBF16PS: {dp_u} tile products = "
          f"{dp_u * TDP:.0f} cycles + 64 loads + 64 stores = "
          f"{dp_u * TDP + 64 * TLOAD + 64 * TSTORE:.0f} cycles; useful products "
          f"{16 * 16} of 8192 = {100 * 256 / 8192:.1f} %; AVX-512 needs "
          f"{128 * 8 / FMA_PER_CYCLE:.0f} cycles")
    print(f"  plus a split pass over S every token (S changes every token): "
          f"{1024 * 4:.0f} cycles compute, 64 KiB read + 96 KiB written")

    # ------------------------------------------------------------- attention
    print("\nFull attention, per (query token, 64-token page, KV head)")
    for head in (128, 256):
        steps = head // 32
        qk_dp, qk_load, qk_store = steps * 4, steps * 5, 4
        groups = head // 64                 # 4 accumulator tiles = 64 output dims per group
        pv_dp, pv_load, pv_store = groups * 2 * 4, groups * 2 * 5, groups * 4
        dp, ld, st = qk_dp + pv_dp, qk_load + pv_load, qk_store + pv_store
        amx = dp * TDP + ld * TLOAD + st * TSTORE
        vdp = 64 * 4 * (head // 32) + 4 * 32 * (head // 16)   # QK + PV VDPBF16PS
        print(f"  head {head}: TDPBF16PS {dp} (QK {qk_dp} + PV {pv_dp}), loads {ld}, "
              f"stores {st} -> {amx:.0f} cycles in L1; AVX-512: {vdp} VDPBF16PS x 2.0 = "
              f"{vdp * 2.0:.0f} cycles; ratio {vdp * 2.0 / amx:.1f}x (instruction count only)")
    print("  4 query tokens per call (16 of 16 Q columns and P rows used), head 256: "
          "same 64 TDPBF16PS serve 4 tokens = 16 per token")

    json.dump(out, open(__file__.replace(".py", ".json"), "w"), indent=1)
