#!/usr/bin/env python3
"""Review finding R5: lengths of the runs of tile work and of AVX-512 work in the two proposed AMX kernels,
and of the two parts of each turn of the clock probe.

Words: a RUN is a stretch of tile work alone or of AVX-512 work alone. A TURN is one tile run plus the AVX-512
run beside it (the unit that the clock probe repeats).

What it computes
  A. Block kernel of Part A, one value head, one block of 32 tokens: every run in execution order, its
     instruction count, its repeats per block, its length in cycles and in us at 2.40 GHz and at 1.90 GHz.
  B. Attention kernel of Part B (256-wide heads), one page visit: the two tile runs from counts, and the
     measured parts of a page unit of the 128-wide kernel on delphi-3bda.
  C. Clock probe: the tile part and the FMA part of the short turn and of the long turn.
  D. Each run and turn of A and B against the probed turns.
  E. Part A with the working cycle count at 1.90 GHz instead of 2.40 GHz: TTFT change per cell.

Inputs (all read only, under /home/jhan/workspace/intel-AMX/exec)
  gdn-20261120/design-checks/verify-cost/recount_tiles.json   tile instructions and AVX-512 operations per block
  gdn-20261120/design_numbers.py                              instruction costs (checked by text match, not imported)
  results/gdn-20261120/bench/clock-probe.txt, clock-probe2.txt  the clock probe of 2026-11-20
  results/single-attn-20260901/summary.json                   measured parts of one page unit, delphi-3bda (Ref19)
  results/gdn-20261120/predictions.json                       measured inputs of the prediction per cell

Nothing here is a measurement of a proposed kernel. Every length in A and B is an estimate from counts (est.),
with every load from L1. Cache lines from L2 are not in the lengths, except where a line says so.
The loop nests below are those of recount_tiles.py. The totals are asserted against recount_tiles.json.
"""
import json
import re

EXEC = "/home/jhan/workspace/intel-AMX/exec"
CYC_TDP, CYC_TLD, CYC_TST = 16.17, 8.38, 16.1      # cycles per tile product, tile load, tile store
OP_LO, OP_HI = 0.50, 0.613                         # cycles per AVX-512 operation: est., and the measured FMA rate
LINE_LO, LINE_HI = 1.8, 2.96                       # cycles per cache line from L2 (est.)
CLOCKS = (2.40, 1.90)                              # GHz
BLOCK = 32

src = open(EXEC + "/gdn-20261120/design_numbers.py").read()
for text in ("CYC_TDP = 16.17", "CYC_TLD = 8.38", "CYC_TST = 16.1", "CYC_FMA = 0.613", "LINE_LO, LINE_HI = 1.8, 2.96",
             "CLK_AMX = 2.40", "CLK_MIX = 1.90", "avx_ops * 0.50, avx_ops * CYC_FMA"):
    assert text in src, text
rec = json.load(open(EXEC + "/gdn-20261120/design-checks/verify-cost/recount_tiles.json"))
g, ops = rec["gdn"]["32"], rec["avx_parts_ops"]


def us(cycles, ghz):
    return cycles / ghz / 1e3


def tile(n):
    return n["tdp"] * CYC_TDP + n["load"] * CYC_TLD + n["store"] * CYC_TST   # TILEZERO left out, as on the page


def rng(lo, hi, fmt="{:,.0f}"):
    a, b = fmt.format(lo), fmt.format(hi)
    return a if a == b else f"{a} to {b}"


def show(name, kind, what, repeats, lo, hi):
    print(f"  {name:44s} {kind:8s} {what:34s} {repeats:>22s}  {rng(lo, hi):>14s}"
          + "".join(f"  {rng(us(lo, c), us(hi, c), '{:.3f}'):>14s}" for c in CLOCKS))


# ---------------------------------------------------------------- A. block kernel
# one run of tile product 1: one value block (16 columns), 4 key blocks, 4 row tiles of [K;Q], 3 pieces
p1 = {"tdp": 4 * 4 * 3, "load": 4 * (3 + 4), "store": 4, "zero": 4}
# tile product 2: 2 token-column blocks, 4 key blocks, 4 row tiles; no AVX-512 work between them in the recount
p2 = {"tdp": 2 * 4 * 4, "load": 2 * 4 * (1 + 4), "store": 2 * 4, "zero": 2 * 4}
# one run of tile product 3: 4 result tiles (64 key rows x 16 value columns), 3 pieces of Delta
p3 = {"tdp": 4 * 3, "load": 3 + 4, "store": 4, "zero": 4}
R1, R3 = 8, 16                                     # runs per block: 8 value blocks; 8 value blocks x 2 key-row groups
for k in ("tdp", "load", "store", "zero"):
    assert R1 * p1[k] == g["p1"][k] and p2[k] == g["gram"][k] and R3 * p3[k] == g["update"][k], k
split, corr, coeff = ops["split_s0"] / R1, ops["triangle"], ops["coefficients"]
wsplit, final = ops["w_scale_split"], ops["final_fma"] / R3
pack = 2 * (ops["pack_K_Q_bf16"] + ops["pack_K_transposed"] + ops["pack_gram_B"])   # per key head
assert (split, corr, wsplit, final, pack) == (1024, 9216, 2304, 64, 1664)
d = lambda n: f"{n['tdp']} products, {n['load']} loads, {n['store']} stores"

print("A. BLOCK KERNEL (Part A), one value head, one block of 32 tokens. Estimates from counts, every load from L1.")
print(f"  {'run, in execution order':44s} {'kind':8s} {'instructions per run':34s} {'runs per block':>22s}  {'cycles per run':>14s}"
      + "".join(f"  {'us at %.2f GHz' % c:>14s}" for c in CLOCKS))
show("0  pack K, Q, K^T and the Gram operand", "AVX-512", f"{pack:,.0f} operations", "1 per key head", pack * OP_LO, pack * OP_HI)
show("1a stage 1: split 16 columns of S0", "AVX-512", f"{split:,.0f} operations", f"{R1}", split * OP_LO, split * OP_HI)
show("1b stage 1: tile product 1 on them", "tile", d(p1), f"{R1}", tile(p1), tile(p1))
show("2  stage 2: tile product 2", "tile", d(p2), "1 per key head", tile(p2), tile(p2))
show("3  stage 3: coefficients and corrections", "AVX-512", f"{coeff:,.0f} + {corr:,.0f} operations", "1", (coeff + corr) * OP_LO, (coeff + corr) * OP_HI)
show("4a stage 4: scale and split Delta", "AVX-512", f"{wsplit:,.0f} operations", "1", wsplit * OP_LO, wsplit * OP_HI)
show("4b stage 4: tile product 3, 64 rows x 16 cols", "tile", d(p3), f"{R3}", tile(p3), tile(p3))
show("4c stage 4: final write of these values", "AVX-512", f"{final:,.0f} operations", f"{R3}", final * OP_LO, final * OP_HI)
print("  Runs 3 and 4a follow each other with no tile work between. Together:")
long_ops = coeff + corr + wsplit
show("3 + 4a", "AVX-512", f"{long_ops:,.0f} operations", "1", long_ops * OP_LO, long_ops * OP_HI)
show("   stage 3 corrections alone (figure 12)", "AVX-512", f"{corr:,.0f} operations", "1", corr * OP_LO, corr * OP_HI)
print("  Turns (one tile run plus the AVX-512 run beside it):")
t1 = (split * OP_LO + tile(p1), split * OP_HI + tile(p1))
t4 = (tile(p3) + final * OP_LO, tile(p3) + final * OP_HI)
show("stage 1 turn = 1a + 1b", "turn", "", f"{R1}", *t1)
show("stage 4 turn = 4b + 4c", "turn", "", f"{R3}", *t4)
l2 = (final * OP_LO + 64 * LINE_LO, final * OP_HI + 64 * LINE_HI)
print("  Run 4c also loads its 64 state lines from L2 (lead_l1_sim.out, part C: all 1,024 state lines miss L1). With them:")
show("4c with 64 cache lines from L2", "AVX-512", f"{final:,.0f} operations + 64 lines", f"{R3}", *l2)
show("stage 4 turn with these lines", "turn", "", f"{R3}", tile(p3) + l2[0], tile(p3) + l2[1])
tile_all = R1 * tile(p1) + tile(p2) / 2 + R3 * tile(p3)
ops_all = pack / 2 + R1 * split + coeff + corr + wsplit + R3 * final
blk = (tile_all + ops_all * OP_LO, tile_all + ops_all * OP_HI)
print(f"  Check against the page: tile work {tile_all / BLOCK:.1f} cycles per token (page: 269 + 15 + 159 = 443);"
      f" AVX-512 {ops_all:,.0f} operations per block = {ops_all / BLOCK:.0f} per token (page: about 680).")
print(f"  Tile runs per value head and block: {R1} + 0.5 + {R3} = {R1 + 0.5 + R3}. Share of tile work in the instruction cycles:"
      f" {100 * tile_all / blk[1]:.0f} to {100 * tile_all / blk[0]:.0f} %.")
print(f"  Whole block of one value head, instructions only: {rng(*blk)} cycles ="
      + " or".join(f" {rng(us(blk[0], c), us(blk[1], c), '{:.1f}')} us at {c:.2f} GHz" for c in CLOCKS) + " (est.).")
print(f"  Tile cycles in stage 4: {100 * R3 * tile(p3) / tile_all:.0f} % of all tile cycles. In stage 1: {100 * R1 * tile(p1) / tile_all:.0f} %.")
assert "2048 * LINE_HI / B, 4608 * LINE_HI / B" in src
lines = (2048 * LINE_HI, 4608 * LINE_HI)           # cycles per block for cache lines from L2, low and high case of the page
print(f"  Cache lines from L2 (cost table of the page): {rng(*lines)} cycles per block more. That is {100 * lines[0] / blk[1]:.0f} to"
      f" {100 * lines[1] / blk[0]:.0f} % of the instruction cycles. The lengths above do not include them.")

# ---------------------------------------------------------------- B. attention kernel
qk = {"tdp": 8 * 4, "load": 8 * (1 + 4), "store": 4}          # 8 steps of 32 dimensions; per step 1 Q load, 4 x (K load, product)
pv = {"tdp": 4 * 2 * 4, "load": 4 * 2 * (1 + 4), "store": 4 * 4}   # 4 groups of 64 output dimensions; per group 2 x (P load, 4 x (V load, product))
tot = rec["attn_256"]["total"]
for k in ("tdp", "load", "store"):
    assert qk[k] + pv[k] == tot[k], k
print("\nB. ATTENTION KERNEL (Part B, 256-wide heads), one page visit = one page unit. Estimates from counts, every load from L1.")
show("QK tile run", "tile", d(qk), "1 per page unit", tile(qk), tile(qk))
show("PV tile run", "tile", d(pv), "1 per page unit", tile(pv), tile(pv))
kv = (512 * LINE_LO, 512 * LINE_HI)                # one page of K or of V: 64 tokens x 256 values x 2 bytes = 512 cache lines
assert 64 * 256 * 2 // 64 == 512
show("QK tile run, its 512 lines of K from L2", "tile", "the same + 512 cache lines", "1 per page unit", tile(qk) + kv[0], tile(qk) + kv[1])
show("PV tile run, its 512 lines of V from L2", "tile", "the same + 512 cache lines", "1 per page unit", tile(pv) + kv[0], tile(pv) + kv[1])
print(f"  512 cache lines from L2 at {LINE_LO} to {LINE_HI} cycles: {rng(*kv)} cycles ="
      + " or".join(f" {rng(us(kv[0], c), us(kv[1], c), '{:.2f}')} us at {c:.2f} GHz" for c in CLOCKS) + " more per run (est.).")
print("  AVX-512 runs of a page unit (self_attention.hpp lines 1760 to 1807, amx_attn.cpp lines 186 to 241 for the 128-wide kernel):")
print("    after QK : transposition of the scores, then scale, maximum, exp and sum per head, then conversion of the weights to bf16")
print("    after PV : copy of the result and update of the running sums per head")
print("  No count of these runs exists for the 256-wide kernel.")
sa = json.load(open(EXEC + "/results/single-attn-20260901/summary.json"))
print("  Measured on delphi-3bda, 128-wide AMX kernel, decode of qwen-3-4b, us per page unit (summary.json, arm canon):")
print(f"    {'prompt':>8s} {'QK part':>8s} {'softmax':>8s} {'PV part':>8s} {'update':>8s} {'whole':>8s}")
for p in (256, 2048, 8192):
    r = sa[f"canon-{p}"]
    print(f"    {p:>8,d} {r['qk']:8.3f} {r['softmax']:8.3f} {r['pv']:8.3f} {r['state']:8.3f} {r['total']:8.3f}")
print("    QK part = tile run and transposition. softmax = scale, maximum, exp and sum. PV part = conversion and tile run."
      " update = copy and running sums.")

# ---------------------------------------------------------------- C. clock probe
def probe(path, label, field):
    vals, khz = [], []
    for line in open(path):
        m = re.match(rf"{label}-\d \| freq_khz_median (\d+) .*? {field} ([\d.]+)", line)
        if m:
            khz.append(int(m.group(1)))
            vals.append(float(m.group(2)))
    assert vals, (label, field)
    return sum(vals) / len(vals), sum(khz) / len(khz) / 1e6, len(vals)


B1, B2 = EXEC + "/results/gdn-20261120/bench/clock-probe.txt", EXEC + "/results/gdn-20261120/bench/clock-probe2.txt"
fma_ns, fma_ghz, _ = probe(B2, "fma", "ns_per_fma")
tdp_ns, tdp_ghz, _ = probe(B2, "tdp", "ns_per_tdp")                 # tile products, live 512-bit values
tdpz_ns, tdpz_ghz, _ = probe(B2, "tdpz", "ns_total_per_tdp")        # tile products, upper halves cleared
mix_ns, mix_ghz, _ = probe(B1, "mix", "ns_per_round")               # 4 products + 64 FMAs, no clearing
mixz_ns, mixz_ghz, _ = probe(B2, "mixz", "ns_total_per_tdp")        # 4 products + 64 FMAs, with the clearing
mixzp_ns, mixzp_ghz, _ = probe(B2, "mixzp", "ns_total_per_tdp")     # 4,096 products + 16,384 FMAs, with the clearing
tdp1_ns, _, _ = probe(B1, "tdp", "ns_per_tdp")
cyc_fma = fma_ns * fma_ghz
print("\nC. CLOCK PROBE (measured on delphi-3b35, CPU 140; mean of the repetitions in the files)")
print(f"  FMA loop alone: {fma_ns:.4f} ns per FMA at {fma_ghz:.3f} GHz = {cyc_fma:.3f} cycles.")
print(f"  Tile products alone: {tdp_ns:.3f} ns at {tdp_ghz:.3f} GHz (live 512-bit values), {tdpz_ns:.3f} ns at {tdpz_ghz:.3f} GHz (cleared).")
short = 4 * mixz_ns
s_tile = 4 * tdp_ns
print(f"  Short turn, 4 products then 64 FMAs, with the clearing: {short:.2f} ns per turn at {mixz_ghz:.3f} GHz.")
print(f"    tile part: 4 x {tdp_ns:.3f} ns = {s_tile:.2f} ns (rate of the tile-only loop at the same clock).")
print(f"    FMA part : the turn is {short - s_tile:.2f} ns longer than its tile part. 64 FMAs alone would take {64 * cyc_fma / mixz_ghz:.1f} ns at this clock.")
print(f"    without the clearing (clock-probe.txt): {mix_ns:.2f} ns per turn at {mix_ghz:.3f} GHz, {mix_ns - 4 * tdp1_ns:.2f} ns longer than 4 x {tdp1_ns:.3f} ns.")
print("    So in the short turn the FMAs run while the tile products run. The turn has no FMA run of its own.")
long_ = 4096 * mixzp_ns / 1e3
l_tile = 4096 * tdpz_ns / 1e3
print(f"  Long turn, 4,096 products then 16,384 FMAs, with the clearing: {long_:.2f} us per turn at {mixzp_ghz:.3f} GHz.")
print(f"    tile part: 4,096 x {tdpz_ns:.3f} ns = {l_tile:.2f} us (est., rate of the tile-only loop at {tdpz_ghz:.3f} GHz), {100 * l_tile / long_:.0f} % of the turn.")
print(f"    FMA part : the rest, {long_ - l_tile:.2f} us (est.) = {1e3 * (long_ - l_tile) / 16384:.3f} ns per FMA, {100 * (long_ - l_tile) / long_:.0f} % of the turn.")
print("  FMAs per tile product: short turn 16, long turn 4. So the two probed turns differ in more than their length.")

# ---------------------------------------------------------------- D. comparison
print("\nD. THE RUNS AND TURNS OF A AND B AGAINST THE PROBED TURNS (est., lengths at 2.40 to 1.90 GHz)")
span = lambda lo, hi: (us(lo, CLOCKS[0]) * 1e3, us(hi, CLOCKS[1]) * 1e3)     # ns: shortest at 2.40, longest at 1.90
rows = [("stage 1 turn", span(*t1)), ("stage 4 turn", span(*t4)), ("stage 1 tile run (48 products)", span(tile(p1), tile(p1))),
        ("stage 4 tile run (12 products)", span(tile(p3), tile(p3))), ("stage 2 tile run (32 products)", span(tile(p2), tile(p2))),
        ("AVX-512 run 3 + 4a", span(long_ops * OP_LO, long_ops * OP_HI)), ("AVX-512 run 1a", span(split * OP_LO, split * OP_HI)),
        ("AVX-512 run 4c (64 operations)", span(final * OP_LO, final * OP_HI)),
        ("attention QK tile run (32 products)", span(tile(qk), tile(qk))), ("attention PV tile run (32 products)", span(tile(pv), tile(pv)))]
print(f"  probed: short turn {short:.1f} ns (tile part {s_tile:.1f} ns, 4 products; 64 FMAs). Long turn {long_ * 1e3:,.0f} ns"
      f" (tile part {l_tile * 1e3:,.0f} ns, 4,096 products; FMA part {(long_ - l_tile) * 1e3:,.0f} ns, 16,384 FMAs).")
for name, (a, b) in rows:
    where = "between the two probed turn lengths" if short < a and b < long_ * 1e3 else "BELOW the short probed turn" if b < short else "not between"
    print(f"  {name:38s} {a:8.0f} to {b:8.0f} ns   {a / short:6.1f} to {b / short:6.1f} x the short turn   1/{long_ * 1e3 / b:,.0f} to 1/{long_ * 1e3 / a:,.0f} of the long turn   {where}")
print(f"  Geometric middle of the two probed turn lengths: {(short * long_ * 1e3) ** 0.5:,.0f} ns.")
print(f"  Stage 4 turn against the short turn: {p3['tdp']} products against 4, and 64 AVX-512 operations against 64 FMAs.")

# ---------------------------------------------------------------- E. Part A at 1.90 GHz
OTHER_US, STEP_TODAY, CLK_AVX = 0.8, 6.4, 2.70
for text in ("OTHER_US = 0.8", "STEP_TODAY = 6.4", "CLK_AVX = 2.70", "avx_ops = 680.0", "4608 * LINE_HI / B"):
    assert text in src, text
hi_cyc = (R1 * tile(p1) + tile(p2) / 2 + R3 * tile(p3)) / BLOCK + 680.0 * OP_HI + 4608 * LINE_HI / BLOCK   # high cycle count of the page
step = lambda clk: OTHER_US * CLK_AVX / clk + 2 * hi_cyc / clk / 1e3
tax = lambda clk: round(0.21 * (CLK_AVX / clk - 1), 3)
case = {clk: (round(STEP_TODAY / step(clk), 1), tax(clk)) for clk in CLOCKS}
pred = json.load(open(EXEC + "/results/gdn-20261120/predictions.json"))
A = pred["assumptions"]
assert case[2.40] == (A["s_gdn_amx"]["mid"], A["tax_rest_amx_gdn"]["mid"]), case
assert case[1.90][1] == A["tax_rest_amx_gdn"]["lo"], case
print("\nE. PART A WITH THE WORKING CYCLE COUNT AT 1.90 GHz (est.). Formula of predict.py, measured inputs of predictions.json.")
print(f"  High cycle count of the page: {hi_cyc:,.0f} cycles per value head per token. GDN step: {step(2.40):.2f} us at 2.40 GHz, {step(1.90):.2f} us at 1.90 GHz.")
print(f"  Factor and clock cost: {case[2.40][0]} and {100 * case[2.40][1]:.1f} % at 2.40 GHz (the working values of the page);"
      f" {case[1.90][0]} and {100 * case[1.90][1]:.1f} % at 1.90 GHz.")
print(f"  {'cell':22s} {'TTFT today':>10s} {'Part 0':>8s} {'Part A 2.40':>12s} {'Part A 1.90':>12s} {'A - 0 at 2.40':>14s} {'A - 0 at 1.90':>14s}")
cols = {"p0": [], 2.40: [], 1.90: []}
for name, c in sorted(pred["cells"].items(), key=lambda kv: (kv[1]["users"], kv[1]["prompt"])):
    pf = c["prefill"]
    def change(s, t):
        new = pf["ttft_s"] - pf["passes"] * (pf["gdn_ms"] * (1 - 1 / s) - pf["rest_ms"] * t) / 1e3
        return 100 * (new / pf["ttft_s"] - 1), new
    p0 = change(A["s_gdn_reorder"]["mid"], 0.0)
    a24, a19 = change(*case[2.40]), change(*case[1.90])
    assert abs(a24[1] - c["pred"]["mid"]["amx_gdn"]["ttft_s"]) < 1e-9 and abs(p0[1] - c["pred"]["mid"]["reorder"]["ttft_s"]) < 1e-9
    cols["p0"].append(p0[0]); cols[2.40].append(a24[0]); cols[1.90].append(a19[0])
    print(f"  {c['users']} user(s), prompt {c['prompt']:<6,d} {pf['ttft_s']:9.3f}s {p0[0]:+7.1f}% {a24[0]:+11.1f}% {a19[0]:+11.1f}% {a24[0] - p0[0]:+13.1f}  {a19[0] - p0[0]:+13.1f}")
f = lambda v: f"{-max(v):.0f} to {-min(v):.0f} %"
diff = lambda k: [a - b for a, b in zip(cols[k], cols["p0"])]
print(f"  TTFT fall over the 6 cells: Part 0 {f(cols['p0'])}; Part A at 2.40 GHz {f(cols[2.40])}; Part A at 1.90 GHz {f(cols[1.90])}.")
print(f"  Part A minus Part 0, percentage points of TTFT (negative = Part A is faster): at 2.40 GHz {min(diff(2.40)):+.1f} to {max(diff(2.40)):+.1f};"
      f" at 1.90 GHz {min(diff(1.90)):+.1f} to {max(diff(1.90)):+.1f}.")
