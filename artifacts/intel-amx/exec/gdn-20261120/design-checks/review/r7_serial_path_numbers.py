#!/usr/bin/env python3
"""R7: numbers behind the two bullets "Part 0" and "The method" of "What would prove the prediction wrong".

Part 1. The Part 0 estimate of the GDN step, component by component, as design_numbers.py builds it:
    new step = other work + 2 x (arithmetic with the state in L1 + cache lines from L2)
  The script prints which value of ONE component, alone, moves the step to 3.5 us and to 4.6 us.
  It shows that three different components can each give a step between 3.5 and 4.6 us.

Part 2. The serial-path test. On one serial path the model of section 4 gives, per prefill pass:
    Part 0: fall of the pass wall = fall of the GDN wall                      (no core clock changes)
    Part A: fall of the pass wall = fall of the GDN wall - rest x clock_cost  (the lower clock slows the rest)
  The script prints both falls per cell, the clock cost in ms, and the spread of the pass wall over the 6 untraced
  runs of the cell (the size of a difference that repeated runs alone can produce).

Inputs (read-only):
  /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json  (per-cell walls and the factors)
  /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/collected.json    (pass wall of every untraced run)
  Constants copied from /home/jhan/workspace/intel-AMX/exec/gdn-20261120/design_numbers.py (lines 16 to 30).
Output: text on stdout (saved beside this script as r7_serial_path_numbers.out). Pure python, deterministic.
"""
import json

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
pred = json.load(open(RES + "/predictions.json"))
col = json.load(open(RES + "/collected.json"))
A = pred["assumptions"]

# ---- Part 1: constants of design_numbers.py (all est. except CLK_AVX and CYC_FMA, which are measured)
CLK_AVX = 2.70                 # GHz
CYC_FMA = 0.613                # cycles per AVX-512 FMA, measured
STEP_TODAY, OTHER_US = 6.4, 0.8
OTHER_LO, OTHER_HI = 0.7, 1.0  # us, other work of the GDN step
LINE_LO, LINE_HI = 1.8, 2.96   # cycles per cache line from L2
VEC_OPS = 5120                 # vector operations per value head per token
rec = (VEC_OPS * 0.50 / CLK_AVX / 1e3, VEC_OPS * CYC_FMA / CLK_AVX / 1e3)   # arithmetic with the state in L1
lines = (80 * LINE_LO / CLK_AVX / 1e3, 80 * LINE_HI / CLK_AVX / 1e3)        # 80 cache lines per token from L2
step = (OTHER_LO + 2 * (rec[0] + lines[0]), OTHER_HI + 2 * (rec[1] + lines[1]))
mid = dict(other=OTHER_US, rec=sum(rec) / 2, lines=sum(lines) / 2)
step_mid = mid["other"] + 2 * (mid["rec"] + mid["lines"])
print("==== Part 1: the Part 0 estimate of the GDN step (us, 2.70 GHz thread) ====")
print(f"arithmetic with the state in L1: {rec[0]:.2f} to {rec[1]:.2f} us per value head (est.)")
print(f"cache lines from L2            : {lines[0]:.2f} to {lines[1]:.2f} us per value head (est.), {lines[0] * CLK_AVX * 1e3 / LINE_LO:.0f} lines per token")
print(f"other work of the step         : {OTHER_LO} to {OTHER_HI} us (est.)")
print(f"new GDN step                   : {step[0]:.2f} to {step[1]:.2f} us (est.), middle {step_mid:.2f} us")
print(f"recurrence in today's step     : ({STEP_TODAY} - {OTHER_US}) / 2 = {(STEP_TODAY - OTHER_US) / 2:.2f} us per value head (est.)")
print()
print("One component alone, the two others at the middle of their estimate. Value that gives a step of 3.5 us and of 4.6 us:")
for target in (3.5, 4.6):
    need_rec = (target - mid["other"]) / 2 - mid["lines"]
    need_lines = (target - mid["other"]) / 2 - mid["rec"]
    need_other = target - 2 * (mid["rec"] + mid["lines"])
    print(f"  step {target} us: arithmetic in L1 = {need_rec:.2f} us per value head ({need_rec / mid['rec']:.2f} x its middle), "
          f"or cache lines from L2 = {need_lines:.2f} us per value head ({need_lines * CLK_AVX * 1e3 / ((LINE_LO + LINE_HI) / 2):.0f} lines per token at {(LINE_LO + LINE_HI) / 2:.2f} cycles), "
          f"or other work = {need_other:.2f} us")
print()

# ---- Part 2: serial-path test per cell
print("==== Part 2: fall of the GDN wall and of the pass wall of one prefill pass, on ONE serial path (ms, est.) ====")
print("spread = largest minus smallest pass wall over the 6 untraced runs of the cell (measured).")
print(f"{'users':>5} {'prompt':>6} | {'pass':>7} {'GDN':>7} {'rest':>7} {'spread':>6} | {'P0 GDN fall':>11} {'P0 pass fall':>12} | "
      f"{'PA GDN fall':>11} {'clock cost':>10} {'PA pass fall':>12} | {'PA low: GDN fall':>16} {'clock cost':>10} {'pass fall':>9}")
order = sorted(pred["cells"], key=lambda c: (pred["cells"][c]["users"], pred["cells"][c]["prompt"]))
out = {1: [], 8: []}
for c in order:
    r = pred["cells"][c]
    p = r["prefill"]
    walls = []
    for arm in ("on", "off"):
        if arm in col["cells"][c]:
            walls += col["cells"][c][arm]["prompt_or_mixed"]["forward_wall_ms"]["values"]
    g, rest = p["gdn_ms"], p["rest_ms"]
    p0 = g * (1 - 1 / A["s_gdn_reorder"]["mid"])
    pa = g * (1 - 1 / A["s_gdn_amx"]["mid"])
    tax = rest * A["tax_rest_amx_gdn"]["mid"]
    pa_lo = g * (1 - 1 / A["s_gdn_amx"]["lo"])
    tax_lo = rest * A["tax_rest_amx_gdn"]["lo"]
    # the model's own pass wall must agree with these falls
    assert abs((p["t1_ms"] - r["pred"]["mid"]["reorder"]["t1_prefill_ms"]) - p0) < 1e-9
    assert abs((p["t1_ms"] - r["pred"]["mid"]["amx_gdn"]["t1_prefill_ms"]) - (pa - tax)) < 1e-9
    assert abs((p["t1_ms"] - r["pred"]["lo"]["amx_gdn"]["t1_prefill_ms"]) - (pa_lo - tax_lo)) < 1e-9
    spread = max(walls) - min(walls)
    out[r["users"]].append((tax, tax_lo, spread, p0))
    print(f"{r['users']:5d} {r['prompt']:6d} | {p['t1_ms']:7.2f} {g:7.2f} {rest:7.2f} {spread:6.2f} | {p0:11.2f} {p0:12.2f} | "
          f"{pa:11.2f} {tax:10.2f} {pa - tax:12.2f} | {pa_lo:16.2f} {tax_lo:10.2f} {pa_lo - tax_lo:9.2f}")
print()
print("==== ranges for the text ====")
for u in (1, 8):
    t = [x[0] for x in out[u]]; tl = [x[1] for x in out[u]]; s = [x[2] for x in out[u]]; f = [x[3] for x in out[u]]
    name = "1 user" if u == 1 else "8 users"
    print(f"{name}: with Part A the pass wall falls by {min(t):.1f} to {max(t):.1f} ms less than the GDN wall at the working value, "
          f"and by {min(tl):.1f} to {max(tl):.1f} ms less in the low case (est., one serial path).")
    print(f"{name}: with Part 0 the two falls are equal: {min(f):.1f} to {max(f):.1f} ms at the working value (est.). "
          f"Spread of the pass wall over 6 runs today: {min(s):.1f} to {max(s):.1f} ms (measured).")
