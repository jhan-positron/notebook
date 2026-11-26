#!/usr/bin/env python3
"""Review finding R3: facts about the split of one FP32 value into 3 bf16 pieces.

Reads no input file. Needs python3 and numpy. Deterministic.

Part A (exact rational arithmetic, no numpy): every finite bf16 bit pattern.
    The common unit of all finite bf16 values, the smallest and largest ones.
Part B (bit arithmetic): the finite FP32 values that are NOT a multiple of that
    unit. No sum of bf16 values, of any length, can equal such a value.
Part C (every finite FP32 bit pattern of both signs, 4,278,190,080 patterns):
    two split rules, both with FP32 arithmetic for the residuals.
      truncation: hi  = x with the low 16 bits of its pattern cleared
                  r   = x - hi          (FP32 subtract)
                  mid = r with the low 16 bits cleared
                  lo  = r - mid         (FP32 subtract, kept as it is)
      nearest:    the same, with tron's FP32 to bf16 conversion in place of
                  clearing bits (h/common/numerics/bf16.hpp:91-97: round to
                  nearest even, zero and subnormal -> signed zero, a value
                  that rounds past the largest finite bf16 -> infinity).
    Per magnitude band of x it counts:
      nonfinite   a piece is infinity or NaN
      sum_bad     hi + mid + lo != x as numbers (float64 sum of the 3 pieces)
      lo_not_bf16 lo has one of its low 16 bits set (it is not a bf16 value)
      sub_piece   a piece is a nonzero subnormal (TDPBF16PS reads it as zero)
      plane_loss  largest |x - (sum of the top 16 bits of each piece)|, as
                  numbers: the part that three bf16 values cannot hold.
      tile_loss   largest |x - (what the tile product reads)|. The tile reads
                  the top 16 bits of each piece and reads a subnormal as zero.
Part D: the top of the FP32 range under both rules.
"""
import os
import sys
from fractions import Fraction
from multiprocessing import Pool

import numpy as np

f32, f64, u32 = np.float32, np.float64, np.uint32
BANDS = ((0, 0, "|x| < 2^-126 (FP32 subnormal or zero)"),
         (1, 16, "2^-126 <= |x| < 2^-110"),
         (17, 23, "2^-110 <= |x| < 2^-103"),
         (24, 253, "2^-103 <= |x| < 2^127"),
         (254, 254, "2^127 <= |x| <= largest FP32"))
KEYS = ("n", "not_mult", "nonfinite", "sum_bad", "lo_not_bf16", "sub_piece", "lo_vs_mult")


# ---------------------------------------------------------------- part A
def bf16_value(word):
    """Exact value of a finite bf16 bit pattern (1 sign, 8 exponent, 7 fraction bits)."""
    sign = -1 if word & 0x8000 else 1
    e, frac = (word >> 7) & 0xFF, word & 0x7F
    if e == 0:
        return sign * Fraction(frac) * Fraction(2) ** -133
    return sign * Fraction(128 + frac) * Fraction(2) ** (e - 127 - 7)


def part_a():
    unit = Fraction(2) ** -133
    n = bad = 0
    smallest_pos = smallest_normal = largest = None
    for w in range(1 << 16):
        if (w >> 7) & 0xFF == 0xFF:
            continue  # infinity or NaN
        v = bf16_value(w)
        n += 1
        if (v / unit).denominator != 1:
            bad += 1
        if v > 0:
            smallest_pos = v if smallest_pos is None else min(smallest_pos, v)
            if (w >> 7) & 0xFF:
                smallest_normal = v if smallest_normal is None else min(smallest_normal, v)
            largest = v if largest is None else max(largest, v)
    print("PART A  every finite bf16 bit pattern, exact rational arithmetic")
    print(f"  finite bf16 patterns: {n}; not an integer multiple of 2^-133: {bad}")
    print(f"  smallest positive bf16 (a subnormal): 2^-133 = {float(smallest_pos):.6e}; equal to 2^-133: {smallest_pos == unit}")
    print(f"  smallest positive normal bf16: 2^-126 = {float(smallest_normal):.6e}; equal to 2^-126: "
          f"{smallest_normal == Fraction(2) ** -126}")
    print(f"  largest finite bf16: {float(largest):.7e}; equal to 2^128 - 2^120: {largest == 2 ** 128 - 2 ** 120}")
    q = (Fraction(2) ** -149) / unit
    print(f"  smallest positive FP32, 2^-149 = {2.0 ** -149:.6e}, divided by 2^-133: {q} (not an integer, so no sum of "
          f"bf16 values equals it)")


# ---------------------------------------------------------------- part B
def not_multiple(b):
    """True where the finite FP32 pattern b is not an integer multiple of 2^-133."""
    e = (b >> u32(23)) & u32(0xFF)
    low_bits = np.clip(17 - np.maximum(e.astype(np.int64), 1), 0, 16)  # fraction bits below 2^-133
    mask = ((np.int64(1) << low_bits) - 1).astype(u32)
    return (b & mask) != 0


def part_b():
    per_sign = (2 ** 23 - 2 ** 7) + sum(2 ** 23 - 2 ** (6 + e) for e in range(1, 17))
    print("\nPART B  finite FP32 values that are not a multiple of 2^-133 (count by formula; part C counts them again)")
    print(f"  per sign: {per_sign} = 2^27: {per_sign == 2 ** 27}; both signs: {2 * per_sign}")
    largest = np.array([0x087FFFFF], u32).view(f32)[0]
    print(f"  largest one: bit pattern 0x087fffff = {float(largest):.6e} = 2^-110 - 2^-134: "
          f"{Fraction(float(largest)) == Fraction(2) ** -110 - Fraction(2) ** -134}")
    print(f"  every FP32 value of magnitude 2^-110 = {2.0 ** -110:.6e} or larger is a multiple of 2^-133")


# ---------------------------------------------------------------- part C
def trunc16(x):
    return (x.view(u32) & u32(0xFFFF0000)).view(f32)


def tron_bf16(x):
    """bf16.hpp:91-97 on FP32 bits, result held in FP32."""
    b = x.view(u32)
    nan = (b & u32(0x7FFFFFFF)) > u32(0x7F800000)
    tiny = (b & u32(0x7F800000)) == 0
    r = (b + u32(0x7FFF) + ((b >> u32(16)) & u32(1))) >> u32(16)
    r = np.where(tiny, (b >> u32(16)) & u32(0x8000), r)
    r = np.where(nan, (b >> u32(16)) | u32(0x0040), r)
    return ((r & u32(0xFFFF)) << u32(16)).astype(u32).view(f32)


def subnormal(p):
    b = p.view(u32)
    return ((b & u32(0x7F800000)) == 0) & ((b & u32(0x007FFFFF)) != 0)


def tile_reads(p):
    """What TDPBF16PS reads from a piece: its top 16 bits, a subnormal as zero."""
    t = trunc16(p)
    return np.where(subnormal(t), f32(0.0), t).astype(f64)


def worker(idx):
    b = (np.arange(1 << 20, dtype=np.uint64) + (np.uint64(idx) << np.uint64(20))).astype(u32)
    e = (b >> u32(23)) & u32(0xFF)
    keep = e != 255
    b, e = np.ascontiguousarray(b[keep]), e[keep]
    out = {}
    if b.size == 0:
        return out
    x = b.view(f32)
    x64 = x.astype(f64)
    nm = not_multiple(b)
    with np.errstate(all="ignore"):
        for rule, rnd in (("truncation", trunc16), ("nearest", tron_bf16)):
            hi = rnd(x)
            r = x - hi
            mid = rnd(r)
            lo = r - mid
            fin = np.isfinite(hi) & np.isfinite(mid) & np.isfinite(lo)
            total = hi.astype(f64) + mid.astype(f64) + lo.astype(f64)
            sum_bad = ~(total == x64)
            lo_nb = fin & ((lo.view(u32) & u32(0xFFFF)) != 0)
            sub = fin & (subnormal(hi) | subnormal(mid) | subnormal(lo))
            loss = np.where(fin, np.abs(x64 - (tile_reads(hi) + tile_reads(mid) + tile_reads(lo))), 0.0)
            planes = trunc16(hi).astype(f64) + trunc16(mid).astype(f64) + trunc16(lo).astype(f64)
            ploss = np.where(fin, np.abs(x64 - planes), 0.0)
            for lo_e, hi_e, _ in BANDS:
                m = (e >= lo_e) & (e <= hi_e)
                if not m.any():
                    continue
                out[(rule, lo_e)] = dict(
                    n=int(m.sum()), not_mult=int((m & nm).sum()), nonfinite=int((m & ~fin).sum()),
                    sum_bad=int((m & sum_bad).sum()), lo_not_bf16=int((m & lo_nb).sum()),
                    sub_piece=int((m & sub).sum()), lo_vs_mult=int((m & (lo_nb != nm) & fin).sum()),
                    tile_loss=float(loss[m].max()), plane_loss=float(ploss[m].max()))
    return out


def part_c():
    with Pool(len(os.sched_getaffinity(0))) as pool:   # as many processes as this shell may use
        res = pool.map(worker, range(4096), chunksize=32)
    print("\nPART C  every finite FP32 bit pattern of both signs")
    for rule in ("truncation", "nearest"):
        print(f"  [{rule} split]")
        tot = {k: 0 for k in KEYS}
        for lo_e, hi_e, label in BANDS:
            rows = [r[(rule, lo_e)] for r in res if (rule, lo_e) in r]
            s = {k: sum(r[k] for r in rows) for k in KEYS}
            loss = max(r["tile_loss"] for r in rows)
            ploss = max(r["plane_loss"] for r in rows)
            for k in KEYS:
                tot[k] += s[k]
            print(f"    {label}: patterns {s['n']}; not a multiple of 2^-133: {s['not_mult']}; a piece not finite: "
                  f"{s['nonfinite']}; hi+mid+lo != x: {s['sum_bad']}; lo not a bf16 value: {s['lo_not_bf16']}; "
                  f"a subnormal piece: {s['sub_piece']}; largest part that 3 bf16 values do not hold: {ploss:.6e}; "
                  f"largest part the tile does not read: {loss:.6e}")
        print(f"    all bands: patterns {tot['n']}; a piece not finite: {tot['nonfinite']}; hi+mid+lo != x: {tot['sum_bad']}; "
              f"lo not a bf16 value: {tot['lo_not_bf16']}; a subnormal piece: {tot['sub_piece']} "
              f"({100.0 * tot['sub_piece'] / tot['n']:.4f} %); not a multiple of 2^-133: {tot['not_mult']} "
              f"({100.0 * tot['not_mult'] / tot['n']:.4f} %)")
        print(f"    patterns where 'lo not a bf16 value' and 'x not a multiple of 2^-133' disagree (all pieces finite): "
              f"{tot['lo_vs_mult']}")
    print(f"  reference values: 2^-103 = {2.0 ** -103:.6e}; 2^-110 = {2.0 ** -110:.6e}; 2^-126 = {2.0 ** -126:.6e}; "
          f"2^-126 - 2^-149 = {2.0 ** -126 - 2.0 ** -149:.6e}; 2^-133 = {2.0 ** -133:.6e}; "
          f"2^-133 - 2^-149 = {2.0 ** -133 - 2.0 ** -149:.6e}")


# ---------------------------------------------------------------- part D
def part_d():
    print("\nPART D  top of the FP32 range")
    b = np.arange(0x7F000000, 0x7F800000, dtype=u32)  # exponent field 254, positive
    x = b.view(f32)
    with np.errstate(all="ignore"):
        hi_n = tron_bf16(x)
        hi_t = trunc16(x)
    inf = ~np.isfinite(hi_n)
    first, last = int(b[inf][0]), int(b[inf][-1])
    v_first = float(b[inf][:1].view(f32)[0])
    print(f"  nearest: leading piece is infinity for {int(inf.sum())} positive patterns, 0x{first:08x} to 0x{last:08x}; "
          f"the same count for negative values")
    print(f"  smallest such value: {v_first:.9e} = 2^128 - 2^119: {Fraction(v_first) == 2 ** 128 - 2 ** 119}; "
          f"largest FP32: {float(np.finfo(f32).max):.9e}")
    print(f"  value just below it: 0x{first - 1:08x} = {float(np.array([first - 1], u32).view(f32)[0]):.9e}, "
          f"nearest leading piece {float(hi_n[first - 1 - 0x7F000000]):.7e} (finite)")
    print(f"  truncation: leading piece infinite for {int((~np.isfinite(hi_t)).sum())} patterns; "
          f"largest leading piece {float(hi_t.max()):.7e}")
    with np.errstate(all="ignore"):
        for rule, rnd in (("truncation", trunc16), ("nearest", tron_bf16)):
            v = np.array([3.4028235e38, -3.4028235e38, 3.3961775e38, np.inf, np.nan], f32)
            hi = rnd(v)
            r = v - hi
            mid = rnd(r)
            lo = r - mid
            print(f"  {rule} split of [largest FP32, -largest FP32, 2^128 - 2^119, inf, nan]:")
            print(f"     hi {hi}\n     mid {mid}\n     lo {lo}")


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
    part_d()
    sys.stdout.flush()
