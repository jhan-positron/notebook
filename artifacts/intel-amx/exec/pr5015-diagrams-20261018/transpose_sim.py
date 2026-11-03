"""Simulate the 16 x 16 transpose of qk_rowmajor_128x4 (PR 5015 head 5061623a34,
src/tron/kernels/amx_attn.cpp:231-261 and store_transposed_rows at 169-183).

Why: the diagrams of the transposing store claim which tile column each
128-bit lane holds after the two unpack stages, and which output rows each
store_transposed_rows<lane> writes. This script executes the same intrinsic
semantics (Intel SDM: VUNPCKLPS/VUNPCKHPS, VUNPCKLPD/VUNPCKHPD, VSHUFF32X4) on
a labelled tile and prints the mapping, so the figures quote a computed fact.

Run: python3 transpose_sim.py
"""
import itertools

LANES_EVEN_0X88 = 0x88
LANES_ODD_0XDD = 0xdd
ROWS_PER_LANE_4 = 4


def lanes(v):
    return [v[4 * L:4 * L + 4] for L in range(4)]


def unpacklo_ps(a, b):
    out = []
    for la, lb in zip(lanes(a), lanes(b)):
        out += [la[0], lb[0], la[1], lb[1]]
    return out


def unpackhi_ps(a, b):
    out = []
    for la, lb in zip(lanes(a), lanes(b)):
        out += [la[2], lb[2], la[3], lb[3]]
    return out


def unpacklo_pd(a, b):
    # 64-bit elements = pairs of fp32: low pair of each lane from a, then b
    out = []
    for la, lb in zip(lanes(a), lanes(b)):
        out += [la[0], la[1], lb[0], lb[1]]
    return out


def unpackhi_pd(a, b):
    out = []
    for la, lb in zip(lanes(a), lanes(b)):
        out += [la[2], la[3], lb[2], lb[3]]
    return out


def shuffle_f32x4(a, b, imm):
    la, lb = lanes(a), lanes(b)
    sel = [(imm >> (2 * i)) & 3 for i in range(4)]
    return la[sel[0]] + la[sel[1]] + lb[sel[2]] + lb[sel[3]]


def transpose_tile(tile, group_heads):
    """tile[token][col] (16 x 16) -> rows {row: [16 tokens]} for the rows the
    kernel writes (0..group_heads-1)."""
    u = [[None] * 4 for _ in range(4)]
    for row_group in range(4):
        r0, r1, r2, r3 = (tile[4 * row_group + i] for i in range(4))
        t0, t1 = unpacklo_ps(r0, r1), unpackhi_ps(r0, r1)
        t2, t3 = unpacklo_ps(r2, r3), unpackhi_ps(r2, r3)
        u[row_group][0] = unpacklo_pd(t0, t2)
        u[row_group][1] = unpackhi_pd(t0, t2)
        u[row_group][2] = unpacklo_pd(t1, t3)
        u[row_group][3] = unpackhi_pd(t1, t3)
    rows = {}

    def store_transposed_rows(lane):
        pair_sel = LANES_ODD_0XDD if lane & 1 else LANES_EVEN_0X88
        quad_sel = LANES_ODD_0XDD if lane & 2 else LANES_EVEN_0X88
        for k in range(ROWS_PER_LANE_4):
            p = shuffle_f32x4(u[0][k], u[1][k], pair_sel)
            q2 = shuffle_f32x4(u[2][k], u[3][k], pair_sel)
            rows[lane * ROWS_PER_LANE_4 + k] = shuffle_f32x4(p, q2, quad_sel)
        return pair_sel, quad_sel

    sels = {0: store_transposed_rows(0)}
    if group_heads == 16:
        for lane in (1, 2, 3):
            sels[lane] = store_transposed_rows(lane)
    return u, rows, sels


def main():
    # label (token, col) as token * 100 + col; tokens are the tile rows
    tile = [[tok * 100 + col for col in range(16)] for tok in range(16)]
    u, rows, sels = transpose_tile(tile, 16)
    print("after stage 1+2: lane L of u[row_group][k] holds column 4L+k of tokens "
          "4*row_group..4*row_group+3")
    ok = True
    for rg, k, L in itertools.product(range(4), range(4), range(4)):
        lane_vals = lanes(u[rg][k])[L]
        want = [(4 * rg + t) * 100 + 4 * L + k for t in range(4)]
        ok &= lane_vals == want
    print("  verified for all row_group, k, lane:", ok)
    print("selectors per lane (pair_sel, quad_sel):",
          {L: (hex(a), hex(b)) for L, (a, b) in sels.items()})
    allok = True
    for row in range(16):
        want = [tok * 100 + row for tok in range(16)]
        allok &= rows[row] == want
    print("  output row r = column r of the 16 tokens, for all 16 rows:", allok)
    # the 4-head kernel emits lane 0 only
    _, rows4, sels4 = transpose_tile(tile, 4)
    print("group_heads 4: rows written =", sorted(rows4), "selectors", sels4)
    # worked example: Muse Glimmer (16 heads), head 9, token 37 of the page
    head, token = 9, 37
    r, tok_in_tile = divmod(token, 16)
    row_group, pos = divmod(tok_in_tile, 4)
    lane, k = divmod(head, 4)
    print(f"worked example head {head}, token {token}: tile r={r}, token row "
          f"{tok_in_tile} -> row_group {row_group}, position {pos}; column {head} -> "
          f"lane {lane}, k {k}; store_transposed_rows<{lane}> row k={k} writes "
          f"s row {lane * 4 + k} at s_block + {lane}*4*stride + {k}*stride, element {tok_in_tile} "
          f"-> s[{lane * 4 + k}][{r * 16 + tok_in_tile}]")
    assert lanes(u[row_group][k])[lane][pos] == tok_in_tile * 100 + head
    assert rows[head][tok_in_tile] == tok_in_tile * 100 + head
    print("  checked in the simulation: s_transposed[37][9] -> u[1][1] lane 2 "
          "position 1 -> s[9][37]")
    return 0 if ok and allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
