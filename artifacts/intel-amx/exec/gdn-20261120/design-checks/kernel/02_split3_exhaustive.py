"""Check 2: an FP32 value splits EXACTLY into 3 bf16 values.

Why it matters: TDPBF16PS multiplies bf16 by bf16. The GDN state S is FP32.
If S = S_hi + S_mid + S_lo with every piece a bf16 value, then
k*S = k*S_hi + k*S_mid + k*S_lo and every product is exact in FP32
(8-bit x 8-bit significands).

Two split rules are tested on EVERY non-negative finite FP32 bit pattern
(2,139,095,040 patterns; both rules are sign-symmetric, so negative values
behave the same):

  truncation split:  hi = x with low 16 bits cleared; r = x - hi;
                     mid = r with low 16 bits cleared; lo = r - mid
  nearest split:     same, with round-to-nearest-even in place of clearing bits

A split is counted "exact for the tile product" when
  (a) every piece has its low 16 bits zero (is a bf16 value),
  (b) hi + mid + lo == x exactly, and
  (c) no piece is a nonzero subnormal. TDPBF16PS treats subnormal inputs as
      zero (Intel SDM pseudo-code: "DAZ=FTZ=1"), so such a piece would be lost.
"""
import numpy as np
from multiprocessing import Pool

F32, F64 = np.float32, np.float64


def rne(x):
    bits = x.view(np.uint32).astype(np.uint64)
    r = ((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16) & 0xFFFF
    return (r << 16).astype(np.uint32).view(F32)


def trunc(x):
    return (x.view(np.uint32) & np.uint32(0xFFFF0000)).view(F32)


def subnormal_nonzero(p):
    b = p.view(np.uint32)
    return ((b & np.uint32(0x7F800000)) == 0) & ((b & np.uint32(0x007FFFFF)) != 0)


def check_block(top12):
    """All patterns whose top 12 bits (sign 0, 8 exponent bits, 3 fraction
    bits) equal top12: 2^20 patterns per call, to keep memory small."""
    lo_bits = np.arange(1 << 20, dtype=np.uint32)
    x = ((np.uint32(top12) << np.uint32(20)) | lo_bits).view(F32)
    finite = np.isfinite(x)
    res = {}
    with np.errstate(over="ignore", invalid="ignore"):
        for name, rnd in (("trunc", trunc), ("nearest", rne)):
            hi = rnd(x)
            r1 = (x - hi).astype(F32)
            mid = rnd(r1)
            lo = (r1 - mid).astype(F32)
            pieces_bf16 = ((hi.view(np.uint32) | mid.view(np.uint32) | lo.view(np.uint32))
                           & np.uint32(0xFFFF)) == 0
            x64 = x.astype(F64)
            s2 = hi.astype(F64) + mid.astype(F64)
            exact_sum = (s2 + lo.astype(F64)) == x64
            daz_loss = subnormal_nonzero(hi) | subnormal_nonzero(mid) | subnormal_nonzero(lo)
            bad = finite & ~(pieces_bf16 & exact_sum & ~daz_loss)
            res[name] = (int(finite.sum()), int(bad.sum()),
                         float(x[bad & (x < 1)].max()) if (bad & (x < 1)).any() else 0.0,
                         float(x[bad & (x > 1)].min()) if (bad & (x > 1)).any() else 0.0,
                         int((finite & (s2 == x64)).sum()))
    return top12, res


if __name__ == "__main__":
    tops = list(range(0, 1 << 11))  # sign bit 0
    with Pool(8) as pool:
        out = pool.map(check_block, tops, chunksize=16)
    for name in ("trunc", "nearest"):
        n_fin = sum(r[name][0] for _, r in out)
        n_bad = sum(r[name][1] for _, r in out)
        small_max = max((r[name][2] for t, r in out), default=0.0)
        big_min = min((r[name][3] for t, r in out if r[name][3] > 0), default=0.0)
        n_two = sum(r[name][4] for _, r in out)
        print(f"[{name} split] finite patterns tested: {n_fin:,}")
        print(f"   not exact for the tile product: {n_bad:,} "
              f"({100.0 * n_bad / n_fin:.4f} %)")
        print(f"   largest failing value below 1: {small_max:.6e}")
        print(f"   smallest failing value above 1: {big_min:.6e}"
              if big_min else "   no failing value above 1")
        print(f"   patterns where 2 pieces already suffice: {n_two:,} "
              f"({100.0 * n_two / n_fin:.3f} %)")
    print("2^-110 =", 2.0 ** -110, " 2^-103 =", 2.0 ** -103,
          " FLT_MAX =", float(np.finfo(F32).max))
