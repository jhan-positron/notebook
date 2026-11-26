#!/usr/bin/env python3
"""Verifier (cost lens): independent recount of every tile kernel in the specification.

Method: each kernel is written as a straight-line TILE PROGRAM (zero / load / tdp / store) for a
machine with 8 tile registers. The checker executes the program symbolically and verifies
  - no register number above 7, no use of a register that was never loaded or zeroed,
  - every result tile receives exactly the set of (A operand, B operand) products that the
    matrix product needs (coverage), nothing twice, nothing missing,
  - the counts of TDPBF16PS, TILELOADD, TILESTORED, TILEZERO.
Cycles use C1/C2 of the task (16.2 / 8.4 / 16.1 / 0.5).
Nothing here is a measurement.
"""
from collections import Counter, defaultdict
import json

TDP, TLOAD, TSTORE, TZERO = 16.2, 8.4, 16.1, 0.5


class TileMachine:
    def __init__(self, name):
        self.name = name
        self.reg = [None] * 8            # content tag: ("op", tag) or ("acc", frozenset-builder list)
        self.n = Counter()
        self.results = {}                # result tag -> list of (a_tag, b_tag)
        self.max_live = 0
        self.same_dst_runs = Counter()   # length of runs of consecutive tdp on one destination
        self._last_dst, self._run = None, 0
        self.loaded_tags = Counter()

    def _chk(self, r):
        assert 0 <= r <= 7, f"{self.name}: tile register {r} does not exist"

    def zero(self, r):
        self._chk(r)
        self.reg[r] = ("acc", [])
        self.n["zero"] += 1
        self._live()

    def load(self, r, tag):
        self._chk(r)
        self.reg[r] = ("op", tag)
        self.n["load"] += 1
        self.loaded_tags[tag] += 1
        self._live()

    def tdp(self, dst, a, b):
        for r in (dst, a, b):
            self._chk(r)
        assert self.reg[dst] and self.reg[dst][0] == "acc", f"{self.name}: T{dst} is not an accumulator"
        assert self.reg[a] and self.reg[a][0] == "op", f"{self.name}: A operand T{a} not loaded"
        assert self.reg[b] and self.reg[b][0] == "op", f"{self.name}: B operand T{b} not loaded"
        self.reg[dst][1].append((self.reg[a][1], self.reg[b][1]))
        self.n["tdp"] += 1
        if dst == self._last_dst:
            self._run += 1
        else:
            if self._last_dst is not None:
                self.same_dst_runs[self._run] += 1
            self._last_dst, self._run = dst, 1

    def store(self, r, result_tag):
        self._chk(r)
        assert self.reg[r] and self.reg[r][0] == "acc"
        assert result_tag not in self.results, f"{self.name}: result {result_tag} stored twice"
        self.results[result_tag] = list(self.reg[r][1])
        self.reg[r] = None
        self.n["store"] += 1

    def _live(self):
        self.max_live = max(self.max_live, sum(x is not None for x in self.reg))

    def finish(self, expected):
        if self._last_dst is not None:
            self.same_dst_runs[self._run] += 1
        assert set(self.results) == set(expected), f"{self.name}: result tiles differ from the expected set"
        for tag, prods in expected.items():
            got = Counter(self.results[tag])
            want = Counter(prods)
            assert got == want, f"{self.name}: result {tag} has wrong products"
        return self

    def cycles(self):
        return self.n["tdp"] * TDP + self.n["load"] * TLOAD + self.n["store"] * TSTORE + self.n["zero"] * TZERO


# ------------------------------------------------------------------ attention (A1), per (query token, page, KV head)
def attn_qk(width):
    """amx_attn.cpp:158-181 with dim steps = width / 32."""
    m = TileMachine(f"QK {width}")
    steps = width // 32
    for r in range(4):
        m.zero(r)
    for step in range(steps):
        m.load(6, ("Q", step))
        for blk in range(4):
            reg = 4 + blk % 2
            m.load(reg, ("K", blk, step))
            m.tdp(blk, reg, 6)
    for blk in range(4):
        m.store(blk, ("S", blk))
    exp = {("S", blk): [(("K", blk, s), ("Q", s)) for s in range(steps)] for blk in range(4)}
    return m.finish(exp)


def attn_pv(width):
    """amx_attn.cpp:243-275 with groups = width / 64."""
    m = TileMachine(f"PV {width}")
    groups = width // 64
    for g in range(groups):
        for r in range(4):
            m.zero(r)
        for s in range(2):
            m.load(4, ("P", s))
            for j in range(4):
                reg = 5 + j % 2
                m.load(reg, ("V", s, g * 4 + j))
                m.tdp(j, 4, reg)
        for j in range(4):
            m.store(j, ("O", g * 4 + j))
    exp = {("O", d): [(("P", s), ("V", s, d)) for s in range(2)] for d in range(width // 16)}
    return m.finish(exp)


# ------------------------------------------------------------------ GDN block kernel (G2)
def gdn_p1(C):
    """R0 = K S0, U0 = Q S0 for one value head. Loop: value block > row group > key block: load 3 B; per row block: load A, 3 TDP."""
    m = TileMachine(f"P1 C={C}")
    rb = 2 * C // 16
    for vb in range(8):
        for g0 in range(0, rb, 4):
            rows = list(range(g0, min(g0 + 4, rb)))
            for i, r in enumerate(rows):
                m.zero(i)
            for kb in range(4):
                for p in range(3):
                    m.load(4 + p, ("S0", kb, vb, p))
                for i, r in enumerate(rows):
                    m.load(7, ("KQ", r, kb))
                    for p in range(3):
                        m.tdp(i, 7, 4 + p)
            for i, r in enumerate(rows):
                m.store(i, ("R0U0", r, vb))
    exp = {("R0U0", r, vb): [(("KQ", r, kb), ("S0", kb, vb, p)) for kb in range(4) for p in range(3)]
           for r in range(rb) for vb in range(8)}
    return m.finish(exp)


def gdn_gram(C):
    """KK = K K^T, QK = Q K^T for one key head."""
    m = TileMachine(f"Gram C={C}")
    rb = 2 * C // 16
    cb = -(-C // 16)
    for c in range(cb):
        for g0 in range(0, rb, 4):
            rows = list(range(g0, min(g0 + 4, rb)))
            for i, r in enumerate(rows):
                m.zero(i)
            for kb in range(4):
                m.load(4, ("Kpair", kb, c))
                for i, r in enumerate(rows):
                    m.load(7, ("KQ", r, kb))
                    m.tdp(i, 7, 4)
            for i, r in enumerate(rows):
                m.store(i, ("G", r, c))
    exp = {("G", r, c): [(("KQ", r, kb), ("Kpair", kb, c)) for kb in range(4)] for r in range(rb) for c in range(cb)}
    return m.finish(exp)


def gdn_update(C, reload_w_per_group=True):
    """T = K^T W for one value head (accumulators start at zero, stored to a scratch)."""
    m = TileMachine(f"update C={C}")
    tb = -(-C // 32)
    for vb in range(8):
        for g in range(2):
            for i in range(4):
                m.zero(i)
            for t in range(tb):
                if reload_w_per_group or g == 0 or tb > 1:
                    for p in range(3):
                        m.load(4 + p, ("W", t, vb, p))
                for i in range(4):
                    kr = g * 4 + i
                    m.load(7, ("KT", kr, t))
                    for p in range(3):
                        m.tdp(i, 7, 4 + p)
            for i in range(4):
                m.store(i, ("T", g * 4 + i, vb))
    exp = {("T", kr, vb): [(("KT", kr, t), ("W", t, vb, p)) for t in range(tb) for p in range(3)]
           for kr in range(8) for vb in range(8)}
    return m.finish(exp)


def show(m, per=1.0, note=""):
    n = m.n
    runs = ", ".join(f"{k} in a row x{v}" for k, v in sorted(m.same_dst_runs.items()))
    print(f"  {m.name:14s} TDPBF16PS {n['tdp']:5d}  loads {n['load']:5d}  stores {n['store']:4d}  zeros {n['zero']:4d}"
          f"  | registers live at once {m.max_live} of 8 | cycles (C1, C2) {m.cycles():8.1f} {note}")
    print(f"  {'':14s} products on the same destination tile: {runs}")


out = {}
print("ATTENTION, per (query token, 64-token page, KV head)")
for w in (128, 256):
    qk, pv = attn_qk(w), attn_pv(w)
    show(qk)
    show(pv)
    tot = {k: qk.n[k] + pv.n[k] for k in ("tdp", "load", "store", "zero")}
    cyc_spec = tot["tdp"] * TDP + tot["load"] * TLOAD + tot["store"] * TSTORE
    cyc_all = cyc_spec + tot["zero"] * TZERO
    avx = 64 * 4 * (w // 32) + 4 * 32 * (w // 16)
    print(f"  width {w}: total {tot['tdp']} / {tot['load']} / {tot['store']} (+{tot['zero']} TILEZERO)"
          f" -> {cyc_spec:.1f} cycles without zeros, {cyc_all:.1f} with zeros; AVX-512 {avx} VDPBF16PS x 2.0 = {avx * 2.0:.0f} cycles;"
          f" count ratio {avx * 2.0 / cyc_spec:.2f}x")
    # the P tile is loaded once per (group, token half) although only 2 distinct P tiles exist
    print(f"  width {w}: distinct P tiles 2, P loads {sum(v for t, v in pv.loaded_tags.items() if t[0] == 'P')};"
          f" bytes of K and V streamed per visit: {64 * w * 2 * 2 // 1024} KiB (L1 = 48 KiB)")
    out[f"attn_{w}"] = dict(total=tot, cycles=cyc_spec, avx_cycles=avx * 2.0)
print(f"  A2 (4 query tokens per call), width 256: {out['attn_256']['cycles'] / 4:.0f} cycles of tile work per token")

print("\nGDN BLOCK KERNEL (G2)")
res = {}
for C in (16, 32, 64):
    p1, gram, upd = gdn_p1(C), gdn_gram(C), gdn_update(C)
    print(f" C = {C}")
    show(p1, note="per value head")
    show(gram, note="per key head")
    show(upd, note="per value head")
    per_vh = {k: p1.n[k] + gram.n[k] / 2 + upd.n[k] for k in ("tdp", "load", "store", "zero")}
    cyc = p1.cycles() + gram.cycles() / 2 + upd.cycles()
    print(f"  per value head (Gram halved): {per_vh['tdp']:g} / {per_vh['load']:g} / {per_vh['store']:g}"
          f" -> {cyc:.1f} cycles = {cyc / C:.1f} per token; per token: {per_vh['tdp'] / C:.2f} TDPBF16PS,"
          f" {per_vh['load'] / C:.2f} loads, {per_vh['store'] / C:.2f} stores")
    res[C] = dict(p1=dict(p1.n), gram=dict(gram.n), update=dict(upd.n), per_vh=per_vh, tile_cycles=cyc,
                  p1_cyc=p1.cycles() / C, gram_cyc=gram.cycles() / 2 / C, upd_cyc=upd.cycles() / C)
out["gdn"] = res

# spec figures to compare with
spec = {16: (388, 278, 81), 32: (592, 356, 100), 64: (1216, 752, 144)}
print("\nCOMPARISON WITH THE SPECIFICATION (TDPBF16PS / loads / stores per value head)")
for C, (t, l, s) in spec.items():
    pv = res[C]["per_vh"]
    ok = (pv["tdp"], pv["load"], pv["store"]) == (t, l, s)
    print(f"  C = {C}: spec {t} / {l} / {s}; recount {pv['tdp']:g} / {pv['load']:g} / {pv['store']:g} -> {'MATCH' if ok else 'DIFFERENT'}")
print("  attention 256: spec 64 / 80 / 20; recount "
      f"{out['attn_256']['total']['tdp']} / {out['attn_256']['total']['load']} / {out['attn_256']['total']['store']}")
print("  attention 128: spec 32 / 40 / 12; recount "
      f"{out['attn_128']['total']['tdp']} / {out['attn_128']['total']['load']} / {out['attn_128']['total']['store']}")

# variants
u2 = gdn_update(32, reload_w_per_group=False)
print("\nVARIANT: update at C = 32 with the 3 W tiles kept across the 2 key-row groups of a value block:"
      f" loads {u2.n['load']} instead of 112 (saves {(112 - u2.n['load']) * TLOAD / 32:.1f} cycles per token per value head)")

# AVX-512 work around the tiles, zmm operations per block per value head (recount from the step list)
print("\nAVX-512 PARTS OF G2, zmm operations per 32-token block per value head (recount)")
C = 32
split_s0 = 1024 * (4 + 3 + 1)                 # 4 split, 3 pack (shift+or per row pair = 1 per zmm per piece), 1 guard
triangle = 8 * (C * (C - 1) // 2) + 8 * (C * (C + 1) // 2) + 32 * C   # r pairs, o pairs, per token 8 mul + 8 sub + 8 mul + 8 mul
w_part = 8 * C * (1 + 4 + 3 + 1)
final = 1024
coeff = (C * (C - 1) // 2 + 3 * C * C) / 16   # G products; CK, CQ (2 multiplies), per 16 values
pack_kq = 2 * 8 * C / 2                       # K and Q to bf16 rows: 8 zmm each per token, per key head -> half per value head
pack_kt = (5 * 32) * 4 / 2                    # transpose 32 x 128 16-bit K: 4 blocks of 32x32, 5 unpack stages x 32 zmm, per key head
pack_gramB = (4 * 16) * 8 / 2                 # Gram B operand: 8 blocks of 16x16 pair transposes, 4 stages x 16 zmm, per key head
parts = dict(split_s0=split_s0, triangle=triangle, w_scale_split=w_part, final_fma=final, coefficients=coeff,
             pack_K_Q_bf16=pack_kq, pack_K_transposed=pack_kt, pack_gram_B=pack_gramB)
tot_ops = 0
for k, v in parts.items():
    print(f"  {k:20s} {v:8.0f} operations = {v / 2 / C:6.1f} cycles per token at 2 per cycle")
    tot_ops += v
print(f"  total {tot_ops:.0f} operations = {tot_ops / 2 / C:.1f} cycles per token per value head at 2 per cycle"
      f" (spec: 340; the Gram B packing {pack_gramB / 2 / C:.1f} is not in the spec's list)")
out["avx_parts_ops"] = parts
out["avx_parts_cycles_per_token"] = tot_ops / 2 / C
tile = res[32]["tile_cycles"] / 32
print(f"\nG2 at C = 32, every load from L1: tiles {tile:.1f} + AVX-512 {tot_ops / 2 / C:.1f} = {tile + tot_ops / 2 / C:.0f} cycles"
      " per token per value head (spec: 785)")
out["g2_l1_recount"] = tile + tot_ops / 2 / C

# GDN decode with tiles (G4)
dec = 96 * TDP + (192 * TDP + 64 * TLOAD + 64 * TSTORE) + 1024 * 8 / 2
print(f"\nG4 decode with tiles: 96 x {TDP} + (192 x {TDP} + 64 x {TLOAD} + 64 x {TSTORE}) + 4096 = {dec:.0f} cycles (spec: 10,329)."
      f" Not counted by the spec: 96 + 4 tile loads and 8 stores of the [k;q] x S product = {(100 * TLOAD + 8 * TSTORE):.0f} cycles more.")
out["g4_decode_tiles"] = dec

json.dump(out, open(__file__.replace(".py", ".json"), "w"), indent=1, default=str)
