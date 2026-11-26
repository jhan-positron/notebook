#!/usr/bin/env python3
"""Design content of gdn-amx-design.html: counts, cost estimates, and the text blocks of sections 4 to 7.

Sources of the numbers:
- measured on delphi-3b35 on 2026-11-20: bench/clock-probe.txt, clock-probe2.txt, clock-probe3.txt, the traces, the campaign;
- counted from the tile shapes (a tile is 16 rows x 64 bytes; one TDPBF16PS multiplies a 16 x 32 bf16 tile by a tile
  of 16 pair rows x 16 columns);
- the saved design checks in exec/gdn-20261120/design-checks/.
Every estimate is marked "est." where it is shown.
"""
import glob
import re

BLOCK = 32          # tokens per block
DK = DV = 128       # key rows and value columns of one state matrix
CLK_AVX = 2.70      # GHz, measured: AVX-512 FMA loop on 26 of the 29 probed CPUs
CLK_AMX = 2.40      # GHz, measured: tile products after the upper halves of the vector registers were cleared
CLK_MIX = 1.90      # GHz, measured: tile products with live 512-bit values, or in short turns with FMAs
CYC_TDP = 16.17     # cycles per TDPBF16PS, measured (8.53 ns at 1.895 GHz; 6.73 ns at 2.396 GHz)
CYC_TLD = 8.38      # cycles per TILELOADD from L1, measured (3.10 ns at 2.70 GHz)
CYC_TST = 16.1      # cycles per TILESTORED, measured on delphi-3bda (same CPU model)
CYC_FMA = 0.613     # cycles per AVX-512 FP32 FMA with 8 accumulators, measured (0.2269 ns at 2.70 GHz)
STEP_TODAY = 6.4    # us, GDN step on a 2.70 GHz thread in prefill (trace: 14 of 16 threads, 6.32 to 6.49)
OTHER_US = 0.8      # us per GDN step outside the recurrence loops (est., range 0.7 to 1.0): convolution 0.50 (measured),
                    # normalization of q and k, decay and beta about 0.2 (est.), norm, output gate and copies 0 to 0.3 (not measured)
OTHER_LO, OTHER_HI = 0.7, 1.0
LINE_LO, LINE_HI = 1.8, 2.96   # cycles per cache line fetched from L2 (est.: from the traced step, and from the stand-alone benchmark)
# tile instructions per block of 32 tokens: (products, loads, stores). Counted by design-checks/verify-cost/recount_tiles.py.
TILE = {"p1": (384, 224, 32), "p2": (32, 40, 8), "p3": (192, 112, 64)}   # p2 is per key head (2 value heads)
VEC_OPS = 5120      # vector operations of today's recurrence per value head per token (est. count: 5 per 16 state values)
BENCH = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/bench/clock-probe.txt"
# stand-alone timing of today's loop order and of the column-half order on another CPU (AMD Zen 5, a KVM guest)
OTHER_CPU = "/home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-cost/bench_gdn.run*.out"


def load_bench(path=BENCH):
    """Medians of the stand-alone kernel benchmarks."""
    out = {}
    try:
        txt = open(path).read()
    except OSError:
        return out
    rec = sorted(float(m) for m in re.findall(r"gdn-recurrence-\d \| .*? ms\s+([\d.]+) us", txt))
    conv = sorted(float(m) for m in re.findall(r"gdn-conv-\d \| .*? ms\s+([\d.]+) us", txt))
    if rec:
        out["rec_us"] = rec[len(rec) // 2]
        out["rec_all"] = rec
    if conv:
        out["conv_us"] = conv[len(conv) // 2]
    return out


def load_other_cpu(pattern=OTHER_CPU):
    """Saved runs of bench_gdn.c: speed ratio of the column-half order (128 KiB state) and cycles per cache line from L2."""
    ratios, lines, copies = [], [], []
    for path in sorted(glob.glob(pattern)):
        txt = open(path).read()
        m = re.search(r"token loop 128 KiB / slice replay blocked window 128 = ([\d.]+)x", txt)
        n = re.search(r"= ([\d.]+) cycles per line on this host", txt)
        loop = re.search(r"blocked  layout, window 128 tokens\s+([\d.]+)", txt)
        copy = re.search(r"layout conversion in \+ out.*?at 128 tokens\s+([\d.]+)", txt)
        if m and n and loop and copy:
            ratios.append(float(m.group(1)))
            lines.append(float(n.group(1)))
            copies.append((float(copy.group(1)), 100.0 * float(copy.group(1)) / float(loop.group(1))))
    if not ratios:
        return {}
    return {"ratio_lo": min(ratios), "ratio_hi": max(ratios), "line_lo": min(lines), "line_hi": max(lines), "runs": len(ratios),
            "copy_ns_lo": min(c[0] for c in copies), "copy_ns_hi": max(c[0] for c in copies), "copy_pct": max(c[1] for c in copies)}


def load_clock3(path):
    """clock-probe3.txt: AVX-512 clock per CPU. Returns {cpu: GHz}."""
    out = {}
    try:
        for m in re.finditer(r"^cpu (\d+) \| freq_khz_median (\d+)", open(path).read(), flags=re.M):
            out[int(m.group(1))] = int(m.group(2)) / 1e6
    except OSError:
        pass
    return out


def tile_counts(B=BLOCK):
    """Tile products per block, counted from the shapes. p2 is shared by the 2 value heads of a key head."""
    rows_kq = 2 * B // 16                 # row tiles of [K; Q]
    dim_tiles = DK // 32                  # a tile row holds 32 bf16 key dimensions
    col_tiles = DV // 16                  # a result tile holds 16 value columns
    p1 = rows_kq * dim_tiles * col_tiles * 3              # [K;Q] x S0, 3 bf16 planes of S0
    p2 = rows_kq * dim_tiles * (B // 16)                  # [K;Q] x K^T, no split
    p3 = (DK // 16) * (B // 32) * col_tiles * 3           # K^T x (w . Delta), 3 planes of Delta
    return {"p1": p1, "p2": p2, "p3": p3, "per_token": (p1 + p2 / 2 + p3) / B}


def n_corrections(B=BLOCK):
    """AVX-512 operations of stage 3 per block, 8 vectors per term: the two triangular sums over u < t (8 B (B - 1)),
    and per token the H term for u = t, the two g_t scalings, the subtraction v - r and the beta scaling (40 B).
    Same count as design-checks/verify-cost/recount_tiles.out (triangle) and verify-math/vm_checks.out."""
    return 8 * B * (B - 1) + 40 * B


def block_counts(B=BLOCK):
    t = tile_counts(B)
    return {"p1": f"tile product 1: {t['p1']} TDPBF16PS per block",
            "p2": f"tile product 2: {t['p2']} TDPBF16PS per block and key head",
            "p3": f"tile product 3: {t['p3']} TDPBF16PS per block",
            "sub": f"{n_corrections(B):,} AVX-512 operations per block (est. count)"}


def cost_model(B=BLOCK):
    """Estimated cycles per value head per prompt token of the block kernel, part by part: (name, low, high, basis).
    Counts follow design-checks/lead/lead_costs.py as corrected by design-checks/verify-cost/verify_numbers.py."""
    def tiles(key, share=1.0):
        n, ld, st = TILE[key]
        return share * (n * CYC_TDP + ld * CYC_TLD + st * CYC_TST) / B, share * n / B, share * ld / B, share * st / B
    c1, c2, c3 = tiles("p1"), tiles("p2", 0.5), tiles("p3")
    d = lambda c: f"{c[1]:g} tile products, {c[2]:g} tile loads and {c[3]:g} tile store{'s' if c[3] != 1 else ''} per token"
    avx_ops = 680.0                       # vector operations per token (est.): split of S0 256, corrections 288, scaling and split of Delta 72,
                                          # final write 32, coefficients and packing 33 (recount_tiles.out: 21,791 per block = 681 per token)
    parts = [
        ("Tile product 1 (stage 1: read the state)", c1[0], c1[0], d(c1)),
        ("Tile product 2 (stage 2: token against token)", c2[0], c2[0], d(c2) + ". Shared by the 2 value heads of a key head"),
        ("Tile product 3 (stage 4: write the state)", c3[0], c3[0], d(c3)),
        ("AVX-512 work: split of S0, packing, corrections, split of Delta, final write", avx_ops * 0.50, avx_ops * CYC_FMA,
         f"about {avx_ops:.0f} vector operations per token at 0.50 to 0.61 cycles per operation"),
        ("Moving data between L2 and L1", 2048 * LINE_HI / B, 4608 * LINE_HI / B,
         "Low: the 2,048 cache lines of the state per block, at about 3 cycles per line. High: 4,608 lines per block, with the kernel's own buffers"),
    ]
    return parts, sum(x[1] for x in parts), sum(x[2] for x in parts)


def kernel_runs(B=BLOCK):
    """Tile runs and AVX-512 runs of the block kernel for one value head and one block, in execution order.
    Estimates from the instruction counts, every load from L1: (name, kind, instructions, runs per block, share per value
    head, cycles low, cycles high). Same rows as design-checks/review/phase_lengths.out, part A."""
    t = lambda n, ld, st: (n * CYC_TDP + ld * CYC_TLD + st * CYC_TST,) * 2
    v = lambda ops: (ops * 0.50, ops * CYC_FMA)
    tile = lambda n, ld, st: f"{n} tile products, {ld} tile loads, {st} tile stores"
    nc = n_corrections(B)
    return [
        ("Packing of K, Q and K^T", "AVX-512", "1,664 operations", "1 per key head", 0.5, *v(1664)),
        ("Stage 1: split of 16 value columns of S0", "AVX-512", "1,024 operations", "8", 8, *v(1024)),
        ("Stage 1: tile product 1 on these columns", "Tile", tile(48, 28, 4), "8", 8, *t(48, 28, 4)),
        ("Stage 2: tile product 2", "Tile", tile(32, 40, 8), "1 per key head", 0.5, *t(32, 40, 8)),
        ("Stage 3: corrections and their coefficients", "AVX-512", f"{nc + 223:,} operations ({nc:,} and 223)", "1", 1, *v(nc + 223)),
        ("Stage 4: scaling and split of Delta", "AVX-512", "2,304 operations", "1", 1, *v(2304)),
        ("Stage 4: one part of tile product 3", "Tile", tile(12, 7, 4), "16", 16, *t(12, 7, 4)),
        ("Stage 4: final write of one part", "AVX-512", "64 operations", "16", 16, *v(64)),
    ]


def kernel_runs_summary(B=BLOCK):
    """Numbers of the run table that the text quotes. Times in us at 2.40 GHz unless the key says 190."""
    rows = kernel_runs(B)
    us = lambda cyc, clk=CLK_AMX: cyc / clk / 1e3
    tiles = [r for r in rows if r[1] == "Tile"]
    avx = [r for r in rows if r[1] == "AVX-512"]
    run3 = (rows[4][5] + rows[5][5], rows[4][6] + rows[5][6])           # stage 3 and the split of Delta: one AVX-512 run
    turn1 = (rows[1][5] + rows[2][5], rows[1][6] + rows[2][6])          # split of 16 columns + its tile run
    turn4 = (rows[6][5] + rows[7][5], rows[6][6] + rows[7][6])          # one part of tile product 3 + its final write
    block = (sum(r[4] * r[5] for r in rows), sum(r[4] * r[6] for r in rows))
    lines_lo, lines_hi = 2048 * LINE_HI, 4608 * LINE_HI                 # cache lines from L2 per block (cost table)
    qk, pv = 32 * CYC_TDP + 40 * CYC_TLD + 4 * CYC_TST, 32 * CYC_TDP + 40 * CYC_TLD + 16 * CYC_TST
    tile12 = rows[2][5] + rows[3][5]                                   # last tile run of stage 1 + tile run of stage 2 (once per key head)
    avx01 = (rows[0][5] + rows[1][5], rows[0][6] + rows[1][6])         # packing + first split of stage 1 (once per key head)
    return {"tile_lo": us(min(r[5] for r in tiles)), "tile_hi": us(tile12), "avx_lo": us(min(r[5] for r in avx)), "avx_hi": us(run3[1]),
            "tile12_cyc": tile12, "tile12": us(tile12), "tile12_190": us(tile12, CLK_MIX), "avx01": (us(avx01[0]), us(avx01[1])),
            # first turn (packing + split + tile run) and last turn (split + tile run of stage 1 and of stage 2) of that value head
            "turn1_long": (us(min(avx01[0] + rows[2][5], rows[1][5] + tile12)), us(max(avx01[1] + rows[2][6], rows[1][6] + tile12))),
            "run3": (us(run3[0]), us(run3[1])), "run3_190": (us(run3[0], CLK_MIX), us(run3[1], CLK_MIX)), "run3_ops": n_corrections(B) + 223 + 2304,
            "turn1": (us(turn1[0]), us(turn1[1])), "turn1_190": (us(turn1[0], CLK_MIX), us(turn1[1], CLK_MIX)),
            "turn4": (us(turn4[0]), us(turn4[1])), "turn4_190": (us(turn4[0], CLK_MIX), us(turn4[1], CLK_MIX)),
            "l2_pct": (100 * lines_lo / block[1], 100 * lines_hi / block[0]),
            "qk": us(qk), "pv": us(pv), "qk_190": us(qk, CLK_MIX), "pv_190": us(pv, CLK_MIX), "qk_cyc": qk, "pv_cyc": pv}


RUNS_LEAD = ("Runs of the block kernel for one value head and one block of 32 tokens, in execution order. "
             "The lengths are estimates from the instruction counts, with every load from L1 [Ref18].")


def runs_table(table):
    rng = lambda a, b, f: f(a) if abs(a - b) < 1e-9 else f"{f(a)} to {f(b)}"
    cyc = lambda x: f"{x:,.0f}"
    us = lambda x: f"{x:.2f}" if x >= 0.1 else f"{x:.3f}"
    rows = [[name, kind, ins, runs, rng(lo, hi, cyc), rng(lo / CLK_AMX / 1e3, hi / CLK_AMX / 1e3, us), rng(lo / CLK_MIX / 1e3, hi / CLK_MIX / 1e3, us)]
            for name, kind, ins, runs, _, lo, hi in kernel_runs()]
    return table(["Run", "Kind", "Instructions per run (est. count)", "Runs per block", "Cycles per run (est.)", "us at 2.40 GHz (est.)", "us at 1.90 GHz (est.)"],
                 rows, num_cols=(3, 4, 5, 6))


def runs_notes():
    k = kernel_runs_summary()
    return [
        "Two rows of the same kind that follow each other are one run.",
        "For the first value head of a key head, two pairs of rows are one run each.<ul>"
        f"<li>The packing and the first split of stage 1 are one AVX-512 run. Its 2,688 operations take {k['avx01'][0]:.2f} to {k['avx01'][1]:.2f} us at 2.40 GHz (est.).</li>"
        f"<li>The last tile run of stage 1 and the tile run of stage 2 are one tile run. Its {k['tile12_cyc']:,.0f} cycles take {k['tile12']:.2f} us at 2.40 GHz, or {k['tile12_190']:.2f} us at 1.90 GHz (est.).</li></ul>",
        f"Stage 3 and the scaling and split of Delta follow each other with no tile work between. Together they are one AVX-512 run. Its {k['run3_ops']:,} operations take "
        f"{k['run3'][0]:.1f} to {k['run3'][1]:.1f} us at 2.40 GHz, or {k['run3_190'][0]:.1f} to {k['run3_190'][1]:.1f} us at 1.90 GHz (est.).",
        "The turns have these lengths:<ul>"
        f"<li>Stage 1 has 8 turns. Each takes {k['turn1'][0]:.2f} to {k['turn1'][1]:.2f} us at 2.40 GHz, or {k['turn1_190'][0]:.2f} to {k['turn1_190'][1]:.2f} us at 1.90 GHz (est.).</li>"
        f"<li>For the first value head of a key head, the first and the last of these turns are longer. They take {k['turn1_long'][0]:.1f} to {k['turn1_long'][1]:.1f} us at 2.40 GHz (est.).</li>"
        f"<li>Stage 4 has 16 turns of {k['turn4'][0]:.2f} us at 2.40 GHz, or {k['turn4_190'][0]:.2f} to {k['turn4_190'][1]:.2f} us at 1.90 GHz (est.).</li></ul>",
        "The table uses these costs:<ul>"
        f"<li>{CYC_TDP} cycles per tile product</li><li>{CYC_TLD} cycles per tile load</li><li>{CYC_TST} cycles per tile store</li>"
        "<li>0.50 to 0.61 cycles per AVX-512 operation</li></ul>",
        f"The lengths leave out the cache lines from L2 of the table above. Those add {k['l2_pct'][0]:.0f} to {k['l2_pct'][1]:.0f} % to the cycles of a block (est.).",
        "The final write of stage 4 has 64 FMAs per run. The short turn of the clock probe has the same count.",
        "The clock of the AVX-512 runs is not measured either. The table uses the two clocks that the probe read under tile work.",
    ]


def step_estimates():
    """GDN step time per variant on a 2.70 GHz thread, in us: {name: (low, high)}. All est."""
    _, lo, hi = cost_model()
    rec0 = (VEC_OPS * 0.50 / CLK_AVX / 1e3, VEC_OPS * CYC_FMA / CLK_AVX / 1e3)
    lines0 = (80 * LINE_LO / CLK_AVX / 1e3, 80 * LINE_HI / CLK_AVX / 1e3)
    part0 = (OTHER_LO + 2 * (rec0[0] + lines0[0]), OTHER_HI + 2 * (rec0[1] + lines0[1]))
    part0_mid = OTHER_US + 2 * (sum(rec0) / 2 + sum(lines0) / 2)
    # low case of Part 0: the speed ratio timed on another CPU, applied to the recurrence share of today's step
    zen = load_other_cpu()
    rec_today = (STEP_TODAY - OTHER_US) / 2.0
    part0_other = tuple(OTHER_US + 2 * rec_today / zen[k] for k in ("ratio_hi", "ratio_lo")) if zen else (float("nan"), float("nan"))
    at = lambda clk, cyc, other=OTHER_US: other * CLK_AVX / clk + 2 * cyc / clk / 1e3
    return {"rec0": rec0, "lines0": lines0, "part0": part0, "part0_mid": part0_mid, "part0_other": part0_other, "zen": zen,
            "parta": (at(CLK_AMX, lo), at(CLK_AMX, hi)), "parta_mix": (at(CLK_MIX, lo), at(CLK_MIX, hi)),
            "parta_low_case": at(CLK_MIX, 1.5 * hi), "other_amx": OTHER_US * CLK_AVX / CLK_AMX}


def kernel_rows():
    """Bars of the recurrence figure: time per value head per prompt token, in microseconds."""
    _, lo, hi = cost_model()
    today = load_bench().get("rec_us", float("nan")) / 32.0
    se = step_estimates()
    r_lo, r_hi = se["rec0"][0] + se["lines0"][0], se["rec0"][1] + se["lines0"][1]
    a_lo, a_hi = lo / CLK_AMX / 1e3, hi / CLK_AMX / 1e3
    return [
        {"label": "Today: stand-alone benchmark, 2 MiB state", "value": today, "color": "#434b59", "note": "measured, recurrence only"},
        {"label": "Part 0: same arithmetic, state kept in L1", "value": (r_lo + r_hi) / 2, "color": "#2a78d6", "hatch": True,
         "note": f"est. ({r_lo:.2f} to {r_hi:.2f}, with cache lines from L2)"},
        {"label": f"Part A: AMX block kernel, {BLOCK} tokens", "value": (a_lo + a_hi) / 2, "color": "#1baf7a", "hatch": True,
         "note": f"est. ({a_lo:.2f} to {a_hi:.2f} at {CLK_AMX:.2f} GHz)"},
    ]


def block_table(table):
    parts, lo, hi = cost_model()
    f = lambda a, b: f"{a:,.0f}" if abs(a - b) < 0.5 else f"{a:,.0f} to {b:,.0f}"
    rows = [[n, f(a, b), why] for n, a, b, why in parts]
    today = load_bench().get("rec_us", float("nan")) / 32.0
    rows.append(["<b>Total</b>", f"<b>{f(lo, hi)}</b>",
                 f"<b>{lo / CLK_AMX / 1e3:.2f} to {hi / CLK_AMX / 1e3:.2f} us at {CLK_AMX:.2f} GHz, or {lo / CLK_MIX / 1e3:.2f} to {hi / CLK_MIX / 1e3:.2f} us at {CLK_MIX:.2f} GHz (est.). Today: {today:.2f} us (measured, stand-alone benchmark). "
                 "The cycle counts are estimates, not timings.</b>"])
    return table(["Part of the block kernel", "Cycles per value head per token (est.)", "Basis"], rows, num_cols=(1,))


def factor_basis():
    """Bulleted basis text of each factor row of section 4. Returns a dict of HTML lists."""
    se = step_estimates()
    _, lo, hi = cost_model()
    ul = lambda items: "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    p0, pa, pm = se["part0"], se["parta"], se["parta_mix"]
    po, zen = se["part0_other"], se["zen"]
    return {
        "part0": ul([
            f"GDN step today on a 2.70 GHz thread: {STEP_TODAY} us (trace).",
            f"Recurrence with the state in L1: {se['rec0'][0]:.2f} to {se['rec0'][1]:.2f} us per value head (est.). The count of {VEC_OPS:,} vector operations (est. count) stays the same. "
            "Each costs 0.50 cycles (est.) to 0.61 cycles (the measured FMA rate) [Ref11].",
            f"At most about 80 cache lines per token still come from L2: {se['lines0'][0]:.2f} to {se['lines0'][1]:.2f} us per value head (est.). "
            "80 cache lines per token is the count for a chain of 32 tokens (est.). A chain of 128 tokens has 56 cache lines per token (est.) [Ref18].",
            f"Other work of the GDN step: {OTHER_LO} to {OTHER_HI} us (est.)." + ul([
                "Convolution: 0.50 us (measured, stand-alone benchmark [Ref11]).",
                "Normalization of q and k, decay and beta: about 0.2 us (est.).",
                "Norm, output gate and copies: 0 to 0.3 us (not measured).",
            ]),
            f"New GDN step: {p0[0]:.1f} to {p0[1]:.1f} us (est.). Factor {STEP_TODAY / p0[1]:.1f} to {STEP_TODAY / p0[0]:.1f}.",
            f"Working value {STEP_TODAY / se['part0_mid']:.1f}: a new GDN step of {se['part0_mid']:.1f} us (est.), from the middle of each estimate above. "
            f"High case {STEP_TODAY / p0[0]:.1f}: the low end of the range.",
            f"Low case {STEP_TODAY / po[1]:.1f}: from the only timing of this loop order. It ran on another CPU (AMD Zen 5), not on delphi-3b35." + ul([
                f"A stand-alone copy of both loop orders ran there {zen['runs']} times on a 128 KiB state. "
                f"The column-half order was {zen['ratio_lo']:.2f} to {zen['ratio_hi']:.2f} times faster than today's order [Ref18].",
                f"The ratio leaves out the copy into the contiguous buffer and back. That copy cost {zen['copy_ns_lo']:.0f} to {zen['copy_ns_hi']:.0f} ns per token and value head on that CPU, "
                f"about {zen['copy_pct']:.0f} % of the loop time.",
                f"With that ratio on the recurrence of today's step, the new GDN step is {po[0]:.1f} to {po[1]:.1f} us (est.). Factor {STEP_TODAY / po[1]:.1f} to {STEP_TODAY / po[0]:.1f}.",
                f"On that CPU a cache line from L2 cost {zen['line_lo']:.1f} to {zen['line_hi']:.1f} cycles. The estimates above use {LINE_LO} to {LINE_HI} cycles for delphi-3b35 (est.). "
                "Task 1 of the plan measures the ratio on delphi-3b35.",
            ]),
        ]),
        "parta": ul([
            f"Recurrence in the block kernel: {lo:,.0f} to {hi:,.0f} cycles per value head per token (est., table in section 5.3).",
            f"Other work of the GDN step: {OTHER_US} us at 2.70 GHz (est.). It runs at the lower clock too.",
            f"At 2.40 GHz the new GDN step is {pa[0]:.1f} to {pa[1]:.1f} us (est.). Factor {STEP_TODAY / pa[1]:.1f} to {STEP_TODAY / pa[0]:.1f}.",
            f"At 1.90 GHz the new GDN step is {pm[0]:.1f} to {pm[1]:.1f} us (est.). Factor {STEP_TODAY / pm[1]:.1f} to {STEP_TODAY / pm[0]:.1f}.",
            "The clock at this kernel's own mix of tile work and AVX-512 work is not measured (see the clock note).",
            f"Working value {STEP_TODAY / pa[1]:.1f}: the high cycle count at 2.40 GHz.",
            f"Low case {STEP_TODAY / se['parta_low_case']:.1f}: 1.5 times the high cycle count at 1.90 GHz (GDN step {se['parta_low_case']:.1f} us, est.). It includes a margin for costs that the model does not count.",
            f"High case {STEP_TODAY / pa[0]:.1f}: the low cycle count at 2.40 GHz.",
        ]),
        "decode_gdn": ul([
            "A decode chain has one token. It has no block form.",
            "A tile would use 1 or 2 of its 16 rows. The state is FP32 and differs per sequence [Ref14].",
        ]),
        "attn_pf": ul([
            "On delphi-3bda the 128-wide AMX kernel cut the prefill time of qwen-3-4b [Ref13]:" + ul([
                "by 20 % at prompt 1,024",
                "by 35 % at prompt 2,048",
                "by 47 % at prompt 4,096",
                "by 57 % at prompt 8,192",
            ]),
            "A fit of these times gives 2.95 to 3.05 times (est., script in [Ref18])." + ul([
                "The fit writes the prefill time of a prompt of p tokens in two forms. Without AMX: a x p + b x p x p. With AMX: a x p + b x p x p / s.",
                "So s is the speedup of the part that grows with the square of the prompt length. That part is the scoring of the full pages of earlier passes.",
                "The pages that a pass writes and every cost that is fixed per pass grow with p. They stay in the term a x p.",
                "The lower bound is 2.3 times: the ratio of the whole prefill times at prompt 8,192.",
            ]),
            "On delphi-3bda the core ran AMX work at 92 % of its AVX-512 clock [Ref12]. On delphi-3b35 it runs at 70 % (1.90 of 2.70 GHz) to 89 % (2.40 of 2.70 GHz). "
            "So the factor is multiplied by 0.76 to 0.96 (est.).",
            "Working value 2.3 = 3.0 x 0.76. High case 2.9 = 3.05 x 0.96.",
            "Both values assume that the factor of 128-wide heads holds for 256-wide heads.",
            "Low case 1.6: the case in which this assumption does not hold." + ul([
                "One page of a 256-wide head holds 64 KiB of K and V. It does not fit the 48 KiB L1 cache. So every visit loads the 1,024 cache lines of the page from L2, at about 3 cycles per line (est.).",
                "A count of instruction cycles and cache lines then gives (8,192 + 3,031) / (2,027 + 3,031) = 2.2 times at equal clocks (est.). At 1.90 GHz it gives 1.6 times (est.). A script computes both values [Ref18].",
                "The count is for one visit of a full page. It does not cover the pages that a pass writes.",
            ]),
        ]),
        "attn_dec": ul([
            "On delphi-3bda the attention time per token got shorter with the 128-wide kernel [Ref19]:" + ul([
                "1.02 times shorter at prompt 256",
                "1.18 times shorter at prompt 2,048",
                "1.22 times shorter at prompt 8,192",
            ]),
            "That time is the busy time of attention worker 0, summed over the layers. So the factor already contains the join, the join wait and the pages of the pass in progress.",
            "In decode a large part of that time is a memory stall. The core waits while K and V rows are loaded from main memory." + ul([
                "On delphi-3bda the stall was 47 % of a page unit with the AVX-512 kernel and 77 % with the AMX kernel, at prompt 8,192 [Ref12].",
                "This stall is inside the busy time. It is not the attention wait of section 3. A lower clock does not change it.",
            ]),
            "Working value 1.0: the gain and the lower clock cancel (est.). Low case 0.9 = 1.18 x 0.76. High case 1.17 = 1.22 x 0.96.",
        ]),
        "tax": ul([
            "The 16 GDN threads also do other work of the pass. Under AMX their clock is 2.40 GHz instead of 2.70 GHz, or 1.90 GHz in the low case.",
            "About 21 % of the rest is CPU work on these threads (est.). The value is the share of the work that prepares and starts the FPGA matrix multiplies, in a decode trace of qwen-3-4b on delphi-3bda [Ref12]. "
            "Its share in a prefill pass of this model is not measured.",
            "Working value 0.21 x (2.70 / 2.40 - 1) = 2.6 %. Low case 0.21 x (2.70 / 1.90 - 1) = 8.8 %.",
            "High case: no cost. It assumes that none of the rest is CPU work on these threads. That share is not measured for this model.",
        ]),
    }


NUMERICS_HTML = """
<li><b>Part 0 changes no bit of the result.</b><ul>
<li>Each value column of S is its own recurrence. Part 0 runs the columns in two halves, with all tokens of the chain per half. Each column still sees the same operations in the same order.</li>
<li>Two independent scripts confirm equal bits for outputs and state. A stand-alone copy in AVX-512 code on another CPU confirms it too [Ref18].</li>
</ul></li>
<li><b>Part A changes the order of the FP32 sums.</b> It also applies the scale of the read step (figure 2, line 4) in FP32 after the tile products.<ul>
<li>Part A applies the scale to the coefficients of the read sum. The token kernel applies it to q before the sum. The tile product needs q as a bf16 value, and scale x q is not a bf16 value.</li>
<li>The result is close to today's result, and it is not equal. Three numeric checks on synthetic inputs compared the block form with today's kernel. 0.005 to 0.10 % of the bf16 output words differ [Ref18].</li>
</ul></li>
<li><b>The differences in the output words are small.</b> An output above 1 % of the typical output size differs by one bf16 increment. Outputs nearer to zero differ by up to 67 increments [Ref18].</li>
<li><b>The error is of the same size as today's.</b> The checks compare both kernels with a float64 computation.<ul>
<li>The block form's output error is 0.3 to 1.1 times the error of today's kernel.</li>
<li>The block form's state error is 0.3 to 3.2 times today's [Ref18].</li>
</ul></li>
<li><b>Long chains with a decay near 1 were checked too.</b> After 1,024 tokens the two kernels differ by up to 33 FP32 increments in the state. Today's kernel is then 27 increments away from float64, and the block form 9 [Ref18].</li>
<li><b>The split rule makes the three pieces in four steps.</b><ol>
<li>The first piece is the FP32 value with the low 16 bits of its bit pattern cleared. This is truncation, which rounds toward zero.</li>
<li>The remainder is the value minus the first piece.</li>
<li>The second piece is the remainder with its low 16 bits cleared.</li>
<li>The third piece is the remainder minus the second piece.</li>
</ol>
Both subtractions are FP32 subtractions. tron's bf16 conversion rounds to nearest, and the split does not use it [Ref18].</li>
<li><b>The split is exact from 2^-103 upward.</b><ul>
<li>Take an FP32 value of size 2^-103 (about 9.9e-32) or larger. Its three pieces are bf16 values, and their sum is the value. None of the three is a subnormal value.</li>
<li>This holds up to the largest FP32 value, 3.4028235e38. A script checked every finite FP32 bit pattern of both signs [Ref18].</li>
</ul></li>
<li><b>Below 2^-103 the tile product reads some pieces as zero.</b><ul>
<li>The second or the third piece can then be a subnormal value.</li>
<li>TDPBF16PS reads a subnormal input as zero. It also replaces a subnormal result by zero. So a piece can exist as a number and still be absent from the product.</li>
<li>A subnormal FP32 value is absent as a whole.</li>
<li>In every case the unread part of one value is below 2^-126 (about 1.2e-38) [Ref18].</li>
</ul></li>
<li><b>Below 2^-110 an exact split does not always exist.</b><ul>
<li>Every finite bf16 value is a multiple of 2^-133 (about 9.2e-41). An FP32 value below 2^-110 (about 7.7e-34) can have bits below 2^-133. No sum of bf16 values holds such bits.</li>
<li>The smallest positive FP32 value, 2^-149, is an example. The third piece then keeps its upper 16 bits, and the part dropped is below 2^-133.</li>
<li>From 2^-110 to 2^-103 the three pieces still add up to the value [Ref18].</li>
</ul></li>
<li><b>Under the truncation rule every finite FP32 value gives three finite pieces.</b> At the top of the range, round to nearest does not.<ul>
<li>The largest finite bf16 value is 3.3895314e38. Round to nearest turns every value of size 3.3961775e38 (2^128 - 2^119) or larger into an infinite first piece. These are the 32,768 largest FP32 values of each sign.</li>
<li>The checks covered both rules up to the largest FP32 value [Ref18].</li>
</ul></li>
<li><b>One of the three numeric checks above uses the truncation rule.</b> The other two round every piece to nearest.<ul>
<li>The first one also ran the round-to-nearest rule on the same inputs in 3 of its test cases.</li>
<li>Between the two rules, 0 to 56 of 131,072 bf16 output words differ.</li>
<li>The error against float64 with round to nearest is 0.99 to 1.13 times the error with truncation [Ref18].</li>
</ul></li>
<li><b>Two pieces are not enough for the split.</b> In the three checks their state error against float64 is 7.5e-8 to 1.6e-5. That is 5 to 227 times the error of today's kernel [Ref18].</li>
<li><b>Decay factors are built by multiplication only.</b> Dividing two running products gives wrong results when the product becomes very small inside a block [Ref18].</li>
<li><b>The fallback of the block path is the column-half path of Part 0.</b> A block takes it when its start state or an intermediate result is not finite. The state is still untouched at that point.<ul>
<li>The column-half path has the bits of the token path.</li>
<li>One check found a case where the block form overflows and today's kernel does not [Ref18].</li>
<li>The split adds no fallback case. Under the truncation rule every finite value gives three finite pieces [Ref18].</li>
<li>Values below 2^-103 take no fallback. Their loss is part of the error band of the contract.</li>
</ul></li>
<li><b>The existing tests require three things today.</b><ul>
<li>The recurrence is checked with an absolute tolerance of 1e-7.</li>
<li>Other tests require equal bytes between the prefill path and the decode path.</li>
<li>One test fixes 320 output words to values from PyTorch (a machine-learning library) [Ref16].</li>
</ul></li>
<li><b>No existing test runs the block path.</b><ul>
<li>The equal-bytes tests and the test with 320 fixed output words use a small head. It has 16 key rows and 80 value columns.</li>
<li>The tolerance tests call the token kernel directly, one of them at 128 by 128 for 2 tokens.</li>
<li>So these tests never run a block path that is limited to chains on a 128 by 128 head. They stay unchanged.</li>
<li>The equal-bytes tests run chains of 2 or more tokens on the small head. So they will run the chain path of Part 0 at 16 by 80.</li>
<li>New tests of both paths at 128 by 128 are needed.</li>
</ul></li>
<li><b>We propose this contract for Part A.</b><ul>
<li>The block path stays within a stated error band of the token path.</li>
<li>The block path runs only for the 128 by 128 shape.</li>
<li>The block path runs only for full blocks of 32 tokens on a fixed grid of token positions.</li>
<li>The block path runs only when AMX is on.</li>
<li>The token path stays the reference.</li>
</ul></li>
<li><b>The contract has two consequences to accept.</b><ul>
<li>With Part A, prefill and decode of the same text can differ in rare output bits. Hugging Face Transformers has the same property. It uses the block form for prompts and the token form for single tokens [Ref14].</li>
<li>tron can resume a prompt from a stored state at any token position. If such a position cuts a block, the block runs on the column-half path of Part 0. So the GDN output of a resumed run and of a run from the start can differ in rare bits.<ul>
<li>Today all GDN paths give equal bytes for equal inputs [Ref16].</li>
<li>The logits of a resumed request can already differ today. Its passes hold other numbers of tokens than the passes of a request from the start [Ref22].</li>
</ul></li>
</ul></li>
"""

ATTN_HTML = """
<li><b>Part B uses the same method as the existing kernels.</b> K and V are bf16 already. No split is needed.</li>
<li><b>QK has 8 groups of 32 dimensions instead of 4, and they go into the same 4 result tiles.</b> That is 32 tile products per query token, page and KV head. Today's 128-wide kernel has 16 [Ref6].</li>
<li><b>PV has 4 groups of output dimensions instead of 2.</b> That is 32 tile products per query token, page and KV head. Today's kernel has 16.</li>
<li><b>The buffer of the packed queries of one token grows from 4 KiB to 8 KiB.</b> The buffer of the PV output grows from 8 KiB to 16 KiB.</li>
<li><b>The eligibility check <code>shape_ok</code> accepts head width 256 with 4 query heads per KV head.</b> The dispatch, the kill switch and the attention statistics work as today.</li>
<li><b>The numerics have the same two known differences from AVX-512 as today's kernel.</b> The weights are rounded to nearest, and the sums are added in another order. The existing error-band tests extend to the new shape.</li>
<li><b>Each kernel call serves one query token.</b> So 4 of 16 tile rows carry data, in prefill and in decode. Today's kernel has the same property.</li>
<li><b>The clock of this kernel is a hypothesis.</b><ul>
<li>Section 4 assumes 1.90 GHz at the working value and 2.40 GHz in the high case. No probed turn has the mix of this kernel. Task 4 measures the clock.</li>
<li>The probe read 1.90 GHz for turns of 4 tile products and 64 FMAs. It read 2.40 GHz for turns of 4,096 tile products and 16,384 FMAs [Ref11].</li>
<li>One page unit has two tile runs. Their lengths are estimates from counts, with every load from L1.<ul>
<li>The QK run has 32 tile products, 40 tile loads and 4 tile stores. That is 917 cycles: 0.38 us at 2.40 GHz or 0.48 us at 1.90 GHz (est.).</li>
<li>The PV run has 32 tile products, 40 tile loads and 16 tile stores. That is 1,110 cycles: 0.46 us at 2.40 GHz or 0.58 us at 1.90 GHz (est.).</li>
</ul></li>
<li>When the 512 cache lines of K or of V come from L2, a run is 0.4 to 0.6 us longer at 2.40 GHz (est.).</li>
<li>AVX-512 work follows each tile run. After QK it turns the scores into softmax weights. After PV it adds the result to the running sums of the token.</li>
<li>No count of this AVX-512 work exists for the 256-wide kernel. With the 128-wide kernel on delphi-3bda, the softmax step took 0.08 to 0.11 us per page unit in decode (measured). There the update after PV took 0.07 to 0.17 us per page unit in decode (measured) [Ref19].</li>
</ul></li>
<li><b>One risk is that the page does not fit L1.</b> One page of a 256-wide head holds 64 KiB of K and V.<ul>
<li>At 128-wide a page holds 32 KiB. That fits the 48 KiB L1 cache. So the page stays in L1 while the tokens of one prefill pass visit it.</li>
<li>The low case of section 4 covers this risk.</li>
</ul></li>
<li><b>An optional later step for prefill is to serve 4 query tokens per kernel call.</b><ul>
<li>Then all 16 tile rows carry data, and a page is loaded once per 4 tokens.</li>
<li>The bits equal those of the single-token AMX kernel.</li>
<li>This step is not part of the prediction.</li>
</ul></li>
"""

CODE_ROWS = [
    ["Chain path (Part 0)", "<code>h/tron/models/gdn_rolling_executor.hpp</code>, <code>gdn_execution.hpp</code>",
     "New <code>advance(chain)</code>. It replaces the token loop for chains of 2 or more tokens. It has three phases.<ul>"
     "<li>Phase 1, per token, writes convolution, normalization, decay and beta into a buffer of about 2 KiB per token.</li>"
     "<li>Phase 2 is the recurrence over the chain.</li>"
     "<li>Phase 3, per token, does the norm and the output gate.</li></ul>"
     "Chains of 1 token keep <code>step()</code>. The check for invalid values still covers the state and the convolution history."],
    ["Column-half recurrence (Part 0)", "<code>h/tron/kernels/gated_delta_net.hpp</code>",
     "Same loop body as today on a slice of columns.<ul>"
     "<li>The slice lives in its own buffer of contiguous 32 KiB halves. The buffer is filled from the working copy and written back at the end of the chain.</li>"
     "<li>The slice width follows the head size. The equal-bytes tests and the test with 320 fixed output words (section 5.4) use a head of 16 key rows and 80 value columns.</li></ul>"],
    ["AMX block kernel (Part A)", "new <code>src/tron/kernels/amx_gdn.cpp</code>, <code>h/tron/kernels/amx_gdn_iface.hpp</code>",
     "Out-of-line kernel (a separate function, not inlined) for one value head and one block of 32 tokens.<ul>"
     "<li>It is built with the AMX compiler flags, like <code>amx_attn.cpp</code>. The interface header has no AMX intrinsics (compiler functions for AMX instructions). "
     "The call site is inside <code>#ifdef TRON_AMX_DISPATCH</code>.</li>"
     "<li>The buffers of one GDN thread grow from 227 KiB to at most 559 KiB (est.). They still fit the 2 MiB L2 cache.</li></ul>"],
    ["Attention 256 x 4 (Part B)", "<code>amx_attn_iface.hpp</code>, <code>amx_attn.cpp</code>, <code>self_attention.hpp</code>",
     "Second shape next to 128 x 4: query packer, QK kernel, PV kernel, eligibility check, buffer sizes. The per-shape counters keep their meaning."],
    ["Switches", "build option <code>TRON_AMX_DISPATCH</code>, kill switch <code>TRON_AMX_DISABLE=1</code>",
     "Both exist. They cover the new kernels too.<ul>"
     "<li>With the kill switch set, GDN prefill runs Part 0, which has today's bits. Attention then runs AVX-512.</li>"
     "<li>One more run-time switch, the GDN switch, turns the GDN block path off alone. With the GDN switch set, GDN prefill runs Part 0. Attention keeps its kernel.</li>"
     "<li>The GDN switch allows A/B runs that differ only in this switch.</li>"
     "<li>No switch selects today's token loop for prefill. No switch turns the attention kernel of Part B off alone.</li>"
     "<li>Each switch is read once at start.</li></ul>"],
    ["Tile setup", "<code>begin_region</code> / <code>end_region</code> of the AMX code",
     "Opened once per work item on the GDN threads. The upper halves of the vector registers are cleared before each run of tile work.<ul>"
     "<li>For tile products alone the probe read 2.40 GHz with the clearing and 1.90 GHz without it.</li>"
     "<li>Short turns of tile work and AVX-512 work read 1.90 GHz even with the clearing (clock note in section 4).</li></ul>"],
    ["Counters", "new <code>h/tron/models/gdn_stats.hpp</code>",
     "Per layer: the tokens taken by each of the three paths, and the GDN wall time. The paths are the token path, the column-half path and the AMX block path. "
     "Today only a trace can time GDN."],
    ["Tests", "<code>t/t_gated_delta_net.cpp</code>, new <code>t/t_amx_gdn_numerics.cpp</code>, <code>t/t_amx_numerics.cpp</code>, <code>t/t_amx_dispatch_dtype.cpp</code>, <code>t/t_llama_unit.cpp</code>",
     "<ul><li>The tests of Part 0 check equal bytes against the token path. They use chains of 2, 3, 127 and 128 tokens. They run at 128 by 128 and at the small test heads.</li>"
     "<li>The tests of Part A cover:<ul>"
     "<li>the error band against the token path, on chains of 128 tokens or fewer</li>"
     "<li>the split rule: exact sum from 2^-103 up to the largest FP32 value, the stated loss below 2^-103</li>"
     "<li>the fallback cases</li>"
     "<li>chains that do not start on a block boundary</li></ul></li>"
     "<li>The tests of Part B are:<ul>"
     "<li>the existing QK and PV band tests for 256-wide heads</li>"
     "<li>the tests that name the 128-wide kernel shape</li></ul></li>"
     "<li>The AMX kernel tests run only on a CPU with AMX. They need a CI runner (a machine of the automated test system) with such a CPU.</li></ul>"],
]

OUTSIDE_HTML = """
<li><b>AMX is not used for GDN decode.</b> One token fills 1 or 2 of the 16 tile rows. Users cannot share a tile, because each sequence has its own state.</li>
<li><b>Decode has options that do not need AMX.</b><ul>
<li>The check for invalid values reads the state before every token. The state part of this check could be done inside the first loop of the recurrence. This keeps the bits.</li>
<li>The gain is 1.1 to 1.2 times on the decode recurrence (est.). This gain holds for a cost of 1.8 to 2.96 cycles per cache line from L2 [Ref18].</li>
</ul></li>
<li><b>A state stored in column halves could help decode more.</b><ul>
<li>Together with the merged check, the gain is 1.2 to 1.55 times on the decode recurrence (est.). This gain holds for the same range of line costs [Ref18].</li>
<li>This option needs a new layout of the stored state. It is not part of this design.</li>
</ul></li>
<li><b>16 of 56 threads run GDN while 40 attention workers wait.</b> Using all threads would cut the GDN wall of a prefill pass with 8 users to about 3/8 (est.). It changes the scheduler and the code generator, not a kernel.</li>
<li><b>A state stored in 16 bits is rejected.</b><ul>
<li>A state in fp16 or in bf16 could be loaded into tiles without a split.</li>
<li>In a numeric check with synthetic inputs, 7 to 36 % of the bf16 output words change with an fp16 state. With a bf16 state, 32 to 81 % change [Ref18].</li>
</ul></li>
"""

PLAN_ROWS = [
    ["1", "Stand-alone benchmark of the recurrence at the working-copy size (128 KiB): today's kernel and the column-half order. Also the recurrence alone on one 32 KiB slice that stays in L1.",
     "us per value head per token, on 1 thread and on 16 threads.",
     "<ul><li>2 times faster or more: the estimate from the counts holds.</li>"
     "<li>From 1.46 to 2 times: Part 0 continues at its low case.</li>"
     "<li>Below 1.46 times: the prediction for Part 0 is wrong.</li></ul>"],
    ["2", "Part 0 in tron: chain path with the column-half order.",
     "<ul><li>Byte compare of outputs and state against the base build.</li>"
     "<li>TTFT of the base run and of the Part 0 run in the 6 cells.</li>"
     "<li>GDN step on a 2.70 GHz thread. Separate timers cover the recurrence, the copy into the contiguous buffer and back, the normalization and the other per-token work.</li>"
     "<li>Pass wall and GDN wall for both builds, for prefill and for decode. They come from the counters of section 5.6, in untraced runs.</li></ul>",
     "<ul><li>Equal bytes.</li>"
     "<li>The TTFT fall from the base run to the Part 0 run is taken as a percent of the base run. This percent is inside the Part 0 range of the table in section 4.</li></ul>"],
    ["3", "Stand-alone AMX block kernel with the 3-piece split.", "us per value head per token, and the core clock while it runs.",
     "2 times faster than the column-half kernel of task 1 at the measured clock. If not, Part A stops here."],
    ["4", "Stand-alone 256 x 4 attention kernel against the AVX-512 path.", "us per page unit with the data in cache and from main memory, and the core clock.",
     "1.5 times faster than the AVX-512 path or more, with the data in cache."],
    ["5", "Part B in tron.",
     "<ul><li>A/B run with the kill switch: decode tok/s and TTFT in the 6 cells.</li>"
     "<li>A base run in the same session.</li>"
     "<li>Pass wall and attention busy time per prefill pass in every run.</li>"
     "<li>AMX K tokens above 0 in the attention statistics.</li></ul>",
     "<ul><li>The TTFT fall of the A/B run is taken as a percent of the base run. This percent is inside the Part B range of the table in section 4.</li>"
     "<li>Decode with Part B is at most 1.1 % below decode with the kill switch set. 1.1 % is the largest difference between two sets of runs of the same code in section 2.</li>"
     "<li>This decode rule is stricter than the prediction on purpose. The low case of section 4 (down to -5.3 %, est.) fails it. "
     "After a fail the design needs a rule that keeps the 256-wide kernel off in decode steps.</li></ul>"],
    ["6", "Part A in tron, after the owners of the GDN code accept the numerics contract.",
     "<ul><li>A/B run with the GDN switch: TTFT in the 6 cells.</li>"
     "<li>A base run and a Part 0 run in the same session.</li>"
     "<li>Error-band test.</li></ul>",
     "<ul><li>The run with Part A has a lower TTFT than the run with the GDN switch set, in all 6 cells.</li>"
     "<li>The fall from the base run to the Part 0 run and the fall of the A/B run are added. The sum is taken as a percent of the base run. "
     "This percent is inside the Part A range of the table in section 4.</li></ul>"],
]

COMPARE_HTML = """
<li>The base build is tron without Parts 0, A and B, at the commit where the Part 0 change starts.</li>
<li>A base run is a run of the base build. Its GDN prefill runs today's token loop. Its attention runs AVX-512.</li>
<li>The base build holds the counters of section 5.6. They change no output bit. Their time cost is not measured.</li>
<li>The base build is needed as a second build. No switch selects today's token loop in a build with Part 0 (section 5.6). So today's kernel is measured with the base build.</li>
<li>All runs of one task are made in one session on delphi-3b35, with a load snapshot before every run. Every session has its own base run. The values of section 2 are not used as a denominator.</li>
<li>TTFT and decode speed are medians per cell, as in section 2. A TTFT fall is the TTFT of run 1 minus the TTFT of run 2, in seconds.</li>
<li>Every range of section 4 is a percent of today's TTFT. So a pass rule with a range divides a TTFT fall by the TTFT of the base run. The bounds of a range are the unrounded low and high values of the prediction [Ref9].</li>
<li>An A/B run alone gives a percent of its run 1. Run 1 already runs Part 0. So this percent is not comparable with a range of section 4.</li>
<li>The second table below gives the predicted percent of run 1 for both A/B runs.</li>
<li>A fall in seconds is comparable. In the model of section 4 one part saves the same seconds with or without the other parts (est.). So Part B saves the same seconds on a build with Part 0 as on the base build (est.).</li>
<li>The fall from the base run to Part A is the sum of two falls:<ul>
<li>the fall from the base run to Part 0</li>
<li>the fall from Part 0 to Part A</li>
</ul></li>
"""

COMPARE_ROWS = [
    ["Base to Part 0", "2. Repeated in the sessions of tasks 5 and 6.", "Base run: base build. GDN prefill: today's token loop. Attention: AVX-512.",
     "Part 0 run: build of the task, kill switch set. GDN prefill: Part 0. Attention: AVX-512.",
     "The build. In task 2 the kill switch changes nothing. That build has no AMX kernel for this model."],
    ["A/B run of Part B", "5", "Build with Parts 0 and B, kill switch set. GDN prefill: Part 0. Attention: AVX-512.",
     "Same build, kill switch not set. GDN prefill: Part 0. Attention: Part B.",
     "The kill switch. If the build holds Part A, the GDN switch is set in both runs."],
    ["A/B run of Part A", "6", "Build with Parts 0 and A, GDN switch set. GDN prefill: Part 0.",
     "Same build, GDN switch not set. GDN prefill: Part A.",
     "The GDN switch. The kill switch is not set. Attention runs the same kernel in both runs: Part B if the build holds Part B, AVX-512 if not."],
]

OPEN_HTML = """
<li>No timing of the column-half order exists for delphi-3b35.<ul>
<li>On another CPU (AMD Zen 5) it was 1.46 to 1.74 times faster than today's order [Ref18]. That is below the 2 times that the counts predict.</li>
<li>Insufficient data for the size of the Part 0 gain on this CPU. Task 1 measures it.</li>
</ul></li>
<li>The probe measured the core clock under AMX in stand-alone loops only, not in tron.<ul>
<li>The probe covered two turns. The first has 4 tile products with 64 FMAs (35 ns per turn, 1.90 GHz). The second has 4,096 tile products followed by 16,384 FMAs (33 us per turn, 2.40 GHz).</li>
<li>Neither kernel has one turn length. The runs of the block kernel are in the second table of section 5.3. The tile runs of the attention kernel are in section 5.5.</li>
<li>The AVX-512 work of the attention kernel is not counted.</li>
<li>Insufficient data for the clock of either kernel. Tasks 3 and 4 measure it.</li>
<li>The clock of the other attention work under Part B is not measured either. A reading of the core clock of one attention worker during a prefill pass of task 5 would give it.</li>
</ul></li>
<li>Insufficient data for the wait for K and V under Part B. tron has no timer for this wait alone.<ul>
<li>A worker scores the full pages while K and V of the pass are produced. The AMX kernel of Part B may end this scoring before K and V are ready. Then the worker waits for them, and that part of the saving is lost.</li>
<li>The tron function <code>run_attention_job</code> runs one attention job on one worker. A timer around the wait for K and V in this function would give the missing value [Ref8].</li>
<li>The risk is largest at prompt 1,024, where the full-page time is 0.38 ms per layer with 1 user (est.).</li>
</ul></li>
<li>The block kernel's cost model does not count two costs. Task 3 measures both. The low case of section 4 includes a margin for them.<ul>
<li>A tile load right after an AVX-512 store of the same data waits until the data is written to memory [Ref21].</li>
<li>Small decay values put subnormal values into the AVX-512 parts. The CPU handles such values much more slowly.</li>
</ul></li>
<li>On this server 3 of the 29 probed CPUs run at 4.00 GHz and 26 run at 2.70 GHz [Ref11]. All factors in section 4 are for 2.70 GHz threads. A server with another clock setup needs its own baseline.</li>
<li>Insufficient data for the CPU share of the rest of a prefill pass on the 16 GDN threads. This share decides how much a lower clock costs outside the kernel. A trace of the main thread with the matrix-multiply events turned on would give it.</li>
<li>The numeric checks used synthetic inputs, not the real value ranges of state, decay and beta in this model. A capture of the GDN inputs of one real prompt would give the size of the error band.</li>
<li>After a resume from a stored state, a chain does not always start on a block boundary. In that case a chain of 128 tokens holds only 3 full blocks.<ul>
<li>Then 96 of its 128 tokens run in the block kernel. The other 32 run on the column-half path of Part 0.</li>
<li>The 6 cells of this page do not show this case.</li>
</ul></li>
<li>The hypothesis in section 3 on the cause of the slow decode step is not confirmed. Either of two measurements would confirm or reject it:<ul>
<li>a stand-alone benchmark of one decode step on a 128 KiB state that is outside the caches of the core</li>
<li>cache-miss counters on one GDN thread</li>
</ul></li>
<li>The owners of the GDN code must decide two things for the numerics contract. Part 0 does not need these decisions. Part A does.<ul>
<li>May prefill differ from decode in rare output bits?</li>
<li>May the GDN output of a resumed run differ from that of a run from the start? The logits of such runs can already differ today [Ref22].</li>
</ul></li>
<li>The model's registry entry says that its tokens are not yet valid. The design should be checked again after the merge of the pull requests that add the model.</li>
<li>We did not read the design document of that series of pull requests. We could not open it.</li>
"""

REFS = [
    ("tron pull request #3696 \"Register Qwen3.5 4B\", head commit 72e1191804."
     "<ul>"
     "<li>Registry entry <code>qwen_3p5_4b</code> in <code>config/models.yaml</code>.</li>"
     "<li>Meaning of the support levels: the comment at the top of <code>config/models.yaml</code>, and <code>README.models.md</code> line 35.</li>"
     "<li>Read-only copy of the code: <code>~/workspace/ai-runs/tron-qwen35-4b</code>.</li>"
     "</ul>"),
    "Configuration file of the checkpoint (the saved model weights): <code>/opt/positron/weights/huggingface/Qwen/Qwen3.5-4B/config.json</code> on delphi-3b35. Fields <code>layer_types</code>, <code>head_dim 256</code>, <code>linear_num_key_heads 16</code>, <code>linear_num_value_heads 32</code>, <code>mamba_ssm_dtype float32</code>.",
    ("<code>h/tron/kernels/gated_delta_net.hpp</code>."
     "<ul>"
     "<li>Note [GatedDeltaNet BF16 rounding points]: lines 22-42.</li>"
     "<li>Note [GatedDeltaNet recurrence].</li>"
     "<li>The two state loops: lines 266-294.</li>"
     "<li>Scale of the query: lines 242-243 and 287.</li>"
     "</ul>"),
    ("<code>h/tron/models/gdn_rolling_executor.hpp</code>."
     "<ul>"
     "<li><code>step</code>: lines 311-358.</li>"
     "<li>Layout of the stored state: lines 91-131.</li>"
     "<li>Check for invalid values: lines 281 and 419-437.</li>"
     "<li>State size: <code>gdn_geometry.hpp</code> lines 27-52.</li>"
     "</ul>"),
    ("<code>h/tron/models/gdn_execution.hpp</code>."
     "<ul>"
     "<li>Note [GatedDeltaNet replay]: lines 18-53. Replay is the code's name for the work of <code>run_gdn_operation</code>.</li>"
     "<li><code>run_gdn_operation</code>: lines 76-147.</li>"
     "<li>Thread split: <code>model.hpp</code> lines 2527-2577.</li>"
     "</ul>"),
    "<code>h/tron/kernels/amx_attn_iface.hpp</code> lines 149-151 hold <code>shape_ok</code>: head width 128, 4 query heads per KV head. Kernels: <code>src/tron/kernels/amx_attn.cpp</code>. Dispatch: <code>h/tron/models/self_attention.hpp</code> lines 1533-1536.",
    "<code>h/tron/models/model.hpp</code> lines 835-845 (<code>model_shape_is_hwattn_eligible</code>: head width 128 or 64). Run log line \"HW-attention not available for this model\". HW-attention is tron's name for FPGA attention.",
    ("<code>h/tron/models/attn_stats.hpp</code>, Note [Attention path stats]."
     "<ul>"
     "<li>The timers: lines 30-43.</li>"
     "<li>Full-page visits that stay on the AVX-512 path: lines 200-204.</li>"
     "<li>Also <code>README.stats.md</code> lines 290-298.</li>"
     "<li>The timed code is <code>run_attention_job</code> in <code>h/tron/models/self_attention.hpp</code>, lines 771-851."
     "<ul>"
     "<li>Start of the wall timer: line 794.</li>"
     "<li>Wait for Q: lines 800-802.</li>"
     "<li>Wait for K and V: line 819.</li>"
     "</ul></li>"
     "<li>The join wait is timed in <code>run_joins</code>, lines 1262-1274 of <code>h/tron/models/self_attention.hpp</code>.</li>"
     "<li>Ready and pending pages: <code>h/tron/models/model.hpp</code> lines 2383-2401, Note [Ready versus pending attention work]. A ready page gets no update in the pass in progress. A pending page is one that this pass writes.</li>"
     "<li>The GDN files do not call the statistics code.</li>"
     "</ul>"),
    "Campaign results: <code>exec/results/gdn-20261120/rt-results.txt</code>, <code>rt/*.log</code>, <code>collected.json</code>, <code>predictions.json</code>. Scripts: <code>exec/gdn-20261120/</code>.",
    "Traces: <code>exec/results/gdn-20261120/trace/*.perfetto-trace</code> and <code>*.summary.json</code>, written by <code>analyze_trace.py</code>. Definition of the trace event: <code>gdn_execution.hpp</code> line 110.",
    "Kernel benchmarks and clock probes of 2026-11-20: <code>exec/results/gdn-20261120/bench/clock-probe.txt</code>, <code>clock-probe2.txt</code>, <code>clock-probe3.txt</code>. Benchmark source: <code>t/t_gated_delta_net.cpp</code> lines 597 and 1227.",
    "Earlier AMX measurements on delphi-3bda: <code>perf-model/index.html</code>. It holds instruction costs, core clocks, the time of a page unit and the share of the memory stall. Differences between the two servers: <code>exec/3b35-inspect-20261112/delphi-3b35-vs-3bda.html</code>.",
    "Prefill of qwen-3-4b with and without the AMX attention kernel, 2026-09-22: <code>CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html</code> lines 857-891.",
    ("Published work, read by two independent readers. The files below were read again on 2026-11-20."
     "<ul>"
     "<li>The GatedDeltaNet paper (arXiv 2412.06464) and the DeltaNet paper (arXiv 2406.06484) give the block form.</li>"
     "<li>Hugging Face Transformers <code>modeling_qwen3_5.py</code> uses block size 64 for calls with several tokens. It uses the token form for one token with a stored state.</li>"
     "<li>vLLM and SGLang include a CPU kernel for this layer (in vLLM: <code>csrc/cpu/sgl-kernels/fla.cpp</code>)."
     "<ul>"
     "<li>Its prefill uses blocks of 64 tokens.</li>"
     "<li>Its matrix products call a library routine. A comment in the file says that this routine uses AMX bf16 products.</li>"
     "<li>Its decode runs per token in FP32 vector code.</li>"
     "</ul></li>"
     "<li>One CUDA kernel of llama.cpp (<code>ggml/src/ggml-cuda/gated-delta-net-mma.cu</code>) splits FP32 operands into bf16 pieces. CUDA is the programming interface of Nvidia graphics processors.</li>"
     "</ul>"),
    "Load snapshots before every run: <code>exec/results/gdn-20261120/load/</code>. Script: <code>exec/3b35-inspect-20261112/load-snapshot.sh</code>.",
    ("<code>t/t_gated_delta_net.cpp</code>."
     "<ul>"
     "<li>Tolerance 1e-7: lines 702, 776, 780.</li>"
     "<li>Output words fixed bit for bit: lines 1414-1460 (table) and 1666-1672 (check).</li>"
     "<li>Equal-bytes replay checks: lines 2034, 2167, 2202.</li>"
     "<li>Test head sizes: lines 1278-1284.</li>"
     "</ul>"),
    ("Generated plugin <code>exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp</code>."
     "<ul>"
     "<li>GDN shape: line 42.</li>"
     "<li>Attention shape: line 60.</li>"
     "<li>One GDN layer, from the wait for the 4 input projections to the launch of the output projection: lines 1151-1182.</li>"
     "</ul>"),
    ("Design checks of 2026-11-20, scripts and saved outputs in <code>exec/gdn-20261120/design-checks/</code>."
     "<ul>"
     "<li>Block form against token form: <code>proto/gdn_block_proto.py</code>, <code>skeptic/numerics_check.py</code> and <code>verify-math/vm_checks.py</code>.</li>"
     "<li>Long chains: <code>verify-math/vm_longmem.py</code>.</li>"
     "<li>Exhaustive checks of the split: <code>kernel/02_split3_exhaustive.py</code>, <code>verify-math/vm_checks.py</code> (part C) and <code>review/r3_split_facts.py</code>.</li>"
     "<li>Truncation rule against round to nearest in the block form: <code>verify-math/vm_checks.py</code> (part E) and <code>review/r3_rule_variants.py</code>.</li>"
     "<li>Tile layouts: <code>kernel/07_tile_layout_check.py</code>.</li>"
     "<li>L1 cache models: <code>skeptic/l1_sim.py</code> and <code>verify-cost/l1_check.py</code>.</li>"
     "<li>Equal bits of the column-half order: <code>skeptic/numerics_check.py</code> and <code>verify-math/vm_checks.py</code> (check F1).</li>"
     "<li>A state stored in 16 bits: <code>skeptic/numerics_check.py</code>.</li>"
     "<li>Cost models and their check: <code>kernel/04_cost_model.py</code>, <code>skeptic/cost_model.py</code>, <code>integration/cost_arith.py</code>, <code>lead/lead_costs.py</code>, <code>verify-cost/verify_numbers.py</code>.</li>"
     "<li>Count of tile instructions: <code>verify-cost/recount_tiles.py</code>.</li>"
     "<li>Lengths of the tile runs and AVX-512 runs of both kernels, and the parts of the two probed turns: <code>review/phase_lengths.py</code>.</li>"
     "<li>Timing of both loop orders on another CPU (AMD Zen 5, a virtual machine): <code>verify-cost/bench_gdn.c</code> with 3 saved runs.</li>"
     "<li>Fit of the prefill attention speedup: <code>review/attn_prefill_fit.py</code>.</li>"
     "<li>Count for a 256-wide page that is loaded from L2: <code>review/attn_256_l2_count.py</code>.</li>"
     "<li>Range of the two decode options: <code>review/decode_options_range.py</code>.</li>"
     "<li>Parts of the attention busy time, and Part B under four assumptions: <code>review/r1_attention_timers.py</code>.</li>"
     "<li>Paired changes of the A/B runs: <code>review/paired_changes.py</code>.</li>"
     "<li>Traced runs against untraced runs: <code>review/r6_traced_vs_untraced.py</code>.</li>"
     "<li>Scale of the read step: <code>review/r4_scale_check.py</code>.</li>"
     "<li>Components of the Part 0 step and the serial-path numbers: <code>review/r7_serial_path_numbers.py</code>.</li>"
     "</ul>"),
    ("Time per page unit and attention time per token of qwen-3-4b on delphi-3bda, AVX-512 against the merged AMX kernel, 2026-09-01."
     "<ul>"
     "<li>Results: <code>exec/results/single-attn-20260901/summary.json</code>.</li>"
     "<li>Report: <code>PR3879/make-sense-amx-vs-avx.html</code>.</li>"
     "<li>The attention time per token is the busy time of attention worker 0, summed over the 36 layers. Source: <code>exec/single-attn-20260901/instr-design-report.md</code> lines 8 and 22.</li>"
     "</ul>"),
    "Shape of llama-3.1-8b: <code>h/tron/plugins/llama.hpp</code> line 1680 (<code>TRON_LLAMA_CONFIG</code> for <code>llama_3p1_8b</code>). The shape is 32 layers, 32 heads of 128 values and 8 KV heads.",
    "Intel 64 and IA-32 Architectures Optimization Reference Manual, volume 1 (document 248966, revisions 049 and 050). Chapter 20 (Intel AMX), section 20.15 \"Store to Load Forwarding\".",
    "<code>h/tron/scheduler/full.hpp</code> lines 255-263, Note [Recurrent state snapshots]. It points to Note [Paying for Determinism] in <code>h/runtron/stream_generate.hpp</code> line 140.",
    "Attention statistics of qwen-3-4b and llama-3.1-8b on delphi-3bda with the AMX attention kernel on and off, 2026-10-02: <code>exec/results/attnstats-20261002/exit-reports.txt</code>. The runs used tron's main branch at commit dd0f942c75, with 8 users and software attention, one run per arm. Report: <code>attn-stats-compare.md</code> in the same folder.",
]
