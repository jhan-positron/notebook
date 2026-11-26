#!/usr/bin/env python3
"""Generate /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.

Inputs : exec/results/gdn-20261120/collected.json (collect.py), predictions.json (predict.py), bench/clock-probe*.txt,
         design_numbers.py (the block kernel's counts, cost estimates and the text blocks of sections 4 to 7).
Output : GDN/gdn-amx-design.html. Pure ASCII (numeric character references), light theme only.
Every measured number in the page is read from the result files. Code facts are typed in and carry a reference.
"""
import json
import re

import design_numbers as DN
import figs_data as FD
import figs_design as FG
import figs_static as FS
from pagelib import CSS, assert_ascii, figure

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
OUT = "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html"

col = json.load(open(RES + "/collected.json"))
pred = json.load(open(RES + "/predictions.json"))
cells = pred["cells"]
order = FD.order(pred)
ASM = pred["assumptions"]
NAN = float("nan")


def ref(*ns):
    return '<span class="ref">[' + ", ".join(f"Ref{n}" for n in ns) + "]</span>"


def pct(new, old):
    return 100.0 * (new - old) / old


def rng(vals, digits=0, unit=" %"):
    lo, hi = min(vals), max(vals)
    if f"{lo:.{digits}f}" == f"{hi:.{digits}f}":
        return f"{lo:.{digits}f}{unit}"
    return f"{lo:.{digits}f} to {hi:.{digits}f}{unit}"


def fall(vals, digits=0):
    """Negative changes written as a fall: [-45, -37] -> '37 to 45 %'."""
    return rng([abs(v) for v in vals], digits)


def signed(v, digits=1):
    v = 0.0 if abs(v) < 0.5 * 10 ** (-digits) else v
    return f"{v:+.{digits}f}"


def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def table(head, rows, num_cols=(), kind=""):
    num_cols = set(num_cols)
    cls = lambda i: ' class="n"' if i in num_cols else ""
    h = "".join(f"<th{cls(i)}>{c}</th>" for i, c in enumerate(head))
    b = "".join("<tr>" + "".join(f"<td{cls(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    c = f' class="{kind}"' if kind else ""
    return f'<div class="tablewrap"><table{c}><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ---------------------------------------------------------------- derived numbers used in the prose
def share(kind, part, pick=lambda r: True):
    return [100.0 * cells[c][kind][part] / cells[c][kind]["t1_ms"] for c in order if pick(cells[c])]


def vals(kind, key, pick=lambda r: True):
    return [cells[c][kind][key] for c in order if pick(cells[c])]


short_p = lambda r: r["prompt"] == 1024
long_p = lambda r: r["prompt"] == 8192
one_u = lambda r: r["users"] == 1
eight_u = lambda r: r["users"] == 8
gdn_pf_short, gdn_pf_long = share("prefill", "gdn_ms", short_p), share("prefill", "gdn_ms", long_p)
attn_pf_short, attn_pf_long = share("prefill", "attn_ms", short_p), share("prefill", "attn_ms", long_p)
gdn_dec_1u, gdn_dec_8u = share("decode", "gdn_ms", one_u), share("decode", "gdn_ms", eight_u)
gdn_dec_tr_1u, gdn_dec_tr_8u = vals("decode", "gdn_trace_share_pct", one_u), vals("decode", "gdn_trace_share_pct", eight_u)
attn_dec_all = share("decode", "attn_ms")
trace_longer = [pct(cells[c]["decode"]["trace_pass_ms"], cells[c]["decode"]["t1_ms"]) for c in order]
trace_longer_pf = [pct(cells[c]["prefill"]["trace_pass_ms"], cells[c]["prefill"]["t1_ms"]) for c in order]


def ttft_change(scen, level="mid"):
    return [pct(cells[c]["pred"][level][scen]["ttft_s"], cells[c]["prefill"]["ttft_s"]) for c in order]


def ttft_all(scen):
    return ttft_change(scen, "lo") + ttft_change(scen, "mid") + ttft_change(scen, "hi")


def tps_change(level):
    return [pct(cells[c]["pred"][level]["amx_attn"]["tps"], cells[c]["decode"]["tps"]) for c in order]


extra_mid = [a - b for a, b in zip(ttft_change("amx_gdn"), ttft_change("reorder"))]
a_low_less = [a - b for a, b in zip(ttft_change("amx_gdn", "lo"), ttft_change("reorder"))]   # Part A low case against Part 0 working value
assert min(a_low_less) > 0, a_low_less
part0_of_a = [100.0 * b / a for a, b in zip(ttft_change("amx_gdn"), ttft_change("reorder"))]
part0_low_of_a = [100.0 * b / a for a, b in zip(ttft_change("amx_gdn"), ttft_change("reorder", "lo"))]   # Part 0 low case against Part A working value
n_samples = sorted({cells[c]["samples"] for c in order})

# GDN step per thread (trace): the threads on the 4.00 GHz cores are faster
thr_pf = [v for c in order for v in cells[c]["prefill"]["gdn_per_thread_us"].values()]
thr_fast = [v for v in thr_pf if v < 5.0]
thr_slow = [v for v in thr_pf if v >= 5.0]
n_fast = len(thr_fast) // len(order)
fast_cpus = sorted({k.split("/")[0].strip() for c in order for k, v in cells[c]["prefill"]["gdn_per_thread_us"].items() if v < 5.0}, key=int)
step_mean_pf = vals("prefill", "gdn_step_us")
step_mean_dec = vals("decode", "gdn_step_us")
wait_pf_1u, wait_pf_8u = vals("prefill", "attn_wait_ms", one_u), vals("prefill", "attn_wait_ms", eight_u)
wait_dec = vals("decode", "attn_wait_ms")
gdn_pf_1u, gdn_pf_8u = vals("prefill", "gdn_ms", one_u), vals("prefill", "gdn_ms", eight_u)
x8_pf = [b / a for a, b in zip(gdn_pf_1u, gdn_pf_8u)]
x8_dec = [b / a for a, b in zip(vals("decode", "gdn_ms", one_u), vals("decode", "gdn_ms", eight_u))]
ttft_x8 = [b / a for a, b in zip(vals("prefill", "ttft_s", one_u), vals("prefill", "ttft_s", eight_u))]
tps_1u, tps_8u = vals("decode", "tps", one_u), vals("decode", "tps", eight_u)

# load before the runs: our half and the other socket
loads = [r["load"] for r in col["runs"].values() if r.get("load") and not r["traced"] and r["arm"]]
our_busy = max(l.get("our-app-cores", 0.0) for l in loads) if loads else NAN
s0 = [l.get("socket0", 0.0) for l in loads]
n_runs = len([1 for r in col["runs"].values() if r.get("arm") and r["tps"]])
arm_delta = []
for c in col["cells"]:
    a = col["cells"][c]
    if "on" in a and "off" in a:
        arm_delta.append(pct(a["on"]["decode_tps_per_user"]["median"], a["off"]["decode_tps_per_user"]["median"]))

bench = DN.load_bench()
rec_us = bench.get("rec_us", NAN) / 32.0
conv_us = bench.get("conv_us", NAN) / 16.0
clock3 = DN.load_clock3(RES + "/bench/clock-probe3.txt")
cpu_fast = sorted(c for c, g in clock3.items() if g > 3.5)
cpu_base = [c for c, g in clock3.items() if g <= 3.5]
se = DN.step_estimates()
parts_cost, cost_lo, cost_hi = DN.cost_model()
tc = DN.tile_counts()
in_tron_rec = (DN.STEP_TODAY - DN.OTHER_US) / 2.0
zen = se["zen"]
zen_ratio = f"{zen['ratio_lo']:.2f} to {zen['ratio_hi']:.2f}"
# the typed factors of predict.py must equal the values that design_numbers.py derives, and typed copies must match
assert f"{ASM['s_gdn_reorder']['mid']:.1f}" == f"{DN.STEP_TODAY / se['part0_mid']:.1f}", se["part0_mid"]
assert f"{ASM['s_gdn_reorder']['hi']:.1f}" == f"{DN.STEP_TODAY / se['part0'][0]:.1f}", se["part0"]
assert f"{ASM['s_gdn_reorder']['lo']:.1f}" == f"{DN.STEP_TODAY / se['part0_other'][1]:.1f}", se["part0_other"]
assert f"On another CPU (AMD Zen 5) it was {zen_ratio} times faster" in DN.OPEN_HTML, zen_ratio
assert f"From {zen['ratio_lo']:.2f} to 2 times" in DN.PLAN_ROWS[0][3] and f"Below {zen['ratio_lo']:.2f} times" in DN.PLAN_ROWS[0][3], zen_ratio

c1u = cells[[c for c in order if cells[c]["users"] == 1 and cells[c]["prompt"] == 1024][0]]
c8u = cells[[c for c in order if cells[c]["users"] == 8 and cells[c]["prompt"] == 1024][0]]
c8u_long = cells[[c for c in order if cells[c]["users"] == 8 and cells[c]["prompt"] == 8192][0]]

# attention: join wait (inside the busy time) and full-page time of a prefill pass (est., both from predict.py)
join_pf_1u, join_pf_8u = vals("prefill", "attn_join_ms", one_u), vals("prefill", "attn_join_ms", eight_u)
join_dec = vals("decode", "attn_join_ms")
join_share_pf = lambda r: 100.0 * r["prefill"]["attn_join_ms"] / r["prefill"]["attn_ms"]
join_share_dec = [100.0 * cells[c]["decode"]["attn_join_ms"] / cells[c]["decode"]["attn_ms"] for c in order]
join_growth = [join_pf_1u[-1] / join_pf_1u[0], join_pf_8u[-1] / join_pf_8u[0]]   # prompt 1,024 -> 8,192
full_share = lambda pick: [100.0 * cells[c]["prefill"]["attn_full_ms"] / cells[c]["prefill"]["attn_ms"] for c in order if pick(cells[c])]
attn_fixed = lambda pick: [cells[c]["prefill"]["attn_ms"] - cells[c]["prefill"]["attn_full_ms"] for c in order if pick(cells[c])]


def whole_busy(scen):
    """Sensitivity: TTFT change per level if the prefill factor divided the whole attention busy time."""
    out = {}
    for level in ("lo", "mid", "hi"):
        s = ASM["s_attn_prefill"][level]
        # the whole busy time is divided by the factor, and no other attention work is left to run at the AMX clock
        out[level] = [pct(cells[c]["pred"][level][scen]["ttft_s"]
                          - cells[c]["prefill"]["passes"] * ((cells[c]["prefill"]["attn_ms"] - cells[c]["prefill"]["attn_full_ms"]) * (1 - 1 / s)
                                                             + cells[c]["prefill"]["attn_other_ms"] * ASM["tax_attn_other"][level]) / 1e3,
                          cells[c]["prefill"]["ttft_s"]) for c in order]
    return out


def tps_join_fixed(level):
    """Sensitivity: decode speed change if the join wait of a decode step did not shrink with the kernel."""
    s = ASM["s_attn_decode"][level]
    return [pct(1e3 / (1e3 / cells[c]["decode"]["tps"] - (cells[c]["decode"]["attn_ms"] - cells[c]["decode"]["attn_join_ms"]) * (1 - 1 / s)), cells[c]["decode"]["tps"])
            for c in order]


wb_b, wb_ab = whole_busy("amx_attn"), whole_busy("amx_both")
attn_other = lambda pick: [cells[c]["prefill"]["attn_other_ms"] for c in order if pick(cells[c])]
full_of_pass = [100.0 * cells[c]["prefill"]["attn_full_ms"] / cells[c]["prefill"]["t1_ms"] for c in order]
tax_attn = ASM["tax_attn_other"]
assert f"{tax_attn['mid']:.3f}" == f"{DN.CLK_AVX / DN.CLK_MIX - 1:.3f}" and f"{tax_attn['hi']:.3f}" == f"{DN.CLK_AVX / DN.CLK_AMX - 1:.3f}", tax_attn
wb_all = lambda w: w["lo"] + w["mid"] + w["hi"]
KR = DN.kernel_runs_summary()
gdn_layer_ms = c1u["prefill"]["gdn_ms"] / 24.0
rest_layer_ms = c1u["prefill"]["rest_ms"] / 32.0
slow_step_us = gdn_layer_ms * 1e3 / 128.0
clock_layer_ms = c1u["prefill"]["rest_ms"] * ASM["tax_rest_amx_gdn"]["mid"] / 24.0


# ---------------------------------------------------------------- tables
def glance_table():
    nw = lambda s: re.sub(r"(\S+ %)", r'<span class="nw">\1</span>', s)   # a number and its percent sign stay on one line
    f = lambda scen: nw(f"falls by {fall(ttft_change(scen))}")
    g = lambda scen: nw(f"{fall(ttft_all(scen))}")
    dec = nw(f"{signed(min(tps_change('lo')))} to {signed(max(tps_change('hi')))} %, working value 0 %")
    return table(["Change", "What it is", "Uses AMX", "Bits of the result", "Time to first token, working values (est.)", "Range of the fall (est.)", "Decode speed (est.)"], [
        ["<b>Part 0</b>", "A new loop order for GDN in prompt processing. The state stays in the L1 cache.", "No", "Same as today", f("reorder"), g("reorder"), "No change"],
        ["<b>Part A</b>", "An AMX kernel for GDN in prompt processing. It takes 32 tokens at once. It replaces the inner loop of Part 0.", "Yes", "Rare output bits differ",
         f("amx_gdn"), g("amx_gdn"), "No change"],
        ["<b>Part B</b>", "An AMX kernel for the 8 attention layers, whose heads are 256 values wide.", "Yes", "Same error band as today's AMX attention kernel",
         f("amx_attn"), g("amx_attn"), dec],
        ["<b>Parts A and B</b>", "Both AMX kernels.", "Yes", "As Part A", f("amx_both"), g("amx_both"), "As Part B"],
    ])


def baseline_table():
    rows = []
    for c in order:
        r = cells[c]
        p, d = r["prefill"], r["decode"]
        rows.append([f"{r['users']}", f"{r['prompt']:,}", f"{p['ttft_s']:.3f}", f"{p['ttft_min_s']:.3f} to {p['ttft_max_s']:.3f}",
                     f"{r['prompt'] * r['users'] / p['ttft_s']:,.0f}", f"{d['tps']:.1f}", f"{d['tps_min']:.1f} to {d['tps_max']:.1f}",
                     f"{d['tps'] * r['users']:,.0f}", f"{r['samples']}"])
    return table(["Users", "Prompt (tokens)", "TTFT, median (s)", "TTFT, range (s)", "Prefill rate, all users (tokens/s)",
                  "Decode, median (tok/s per user)", "Decode, range (tok/s per user)", "Decode, all users (tok/s)", "Runs"], rows, num_cols=range(9))


def split_table(kind):
    rows = []
    for c in order:
        r = cells[c]
        k = r[kind]
        t = k["t1_ms"]
        row = [f"{r['users']}", f"{r['prompt']:,}", f"{t:.2f}", f"{k['gdn_ms']:.2f}", f"{100 * k['gdn_ms'] / t:.0f}",
               f"{k['attn_ms']:.2f}", f"{100 * k['attn_ms'] / t:.0f}"]
        if kind == "prefill":
            row.append(f"{k['attn_full_ms']:.2f}")
        row += [f"{k['attn_join_ms']:.2f}", f"{k['rest_ms']:.2f}", f"{100 * k['rest_ms'] / t:.0f}", f"{k['attn_wait_ms']:.2f}"]
        if kind == "decode":
            row.append(f"{k['gdn_trace_share_pct']:.0f}")
        rows.append(row)
    what = "one prefill pass" if kind == "prefill" else "one decode step"
    est = "" if kind == "prefill" else ", est."   # decode: a traced GDN wall over an untraced step wall
    head = ["Users", "Prompt (tokens)", f"Wall of {what} (ms)", "GDN wall (ms)", f"GDN share (%{est})", "Attention busy time (ms)", "Attention share (%)"]
    if kind == "prefill":
        head.append("Full-page time, inside the busy time (ms, est.)")
    head += ["Join wait, inside the busy time (ms)", f"Rest (ms{est})", f"Rest share (%{est})", "Attention wait, inside the rest (ms)"]
    if kind == "decode":
        head.append("GDN share inside the traced run (%)")
    return table(head, rows, num_cols=range(len(head)))


def pred_table():
    rows = []
    for c in order:
        r = cells[c]
        p = r["pred"]
        t0 = r["prefill"]["ttft_s"]
        d0 = r["decode"]["tps"]

        def f(scen):
            m, lo, hi = (pct(p[l][scen]["ttft_s"], t0) for l in ("mid", "lo", "hi"))
            return f"{p['mid'][scen]['ttft_s']:.2f} ({m:+.0f} %)<br><small>{lo:+.0f} to {hi:+.0f} %</small>"

        rows.append([f"{r['users']}", f"{r['prompt']:,}", f"{t0:.2f}", f("reorder"), f("amx_gdn"), f("amx_attn"), f("amx_both"), f"{d0:.1f}",
                     f"{p['mid']['amx_attn']['tps']:.1f} (no change)<br>"
                     f"<small>{signed(pct(p['lo']['amx_attn']['tps'], d0))} to {signed(pct(p['hi']['amx_attn']['tps'], d0))} %</small>"])
    return table(["Users", "Prompt (tokens)", "TTFT today (s)", "Part 0 (s, est.)", "Part A (s, est.)", "Part B (s, est.)", "Parts A and B (s, est.)",
                  "Decode today (tok/s per user)", "Decode with Part B (tok/s per user, est.)"], rows, num_cols=range(9))


FB = DN.factor_basis()
num = lambda x: f"{x:.1f}" if abs(x - round(x, 1)) < 1e-9 else f"{x:g}"
A = lambda k: (num(ASM[k]["lo"]), num(ASM[k]["mid"]), num(ASM[k]["hi"]))
tax = ASM["tax_rest_amx_gdn"]
# Part A if its clock is 1.90 GHz: the high cycle count at that clock, and the low-case clock cost on the rest of the pass
f190 = round(DN.STEP_TODAY / se["parta_mix"][1], 1)
parta_190 = [pct(p["ttft_s"] - p["passes"] * (p["gdn_ms"] * (1 - 1 / f190) - p["rest_ms"] * tax["lo"]) / 1e3, p["ttft_s"]) for p in (cells[c]["prefill"] for c in order)]
# typed copies in design_numbers.py text must match the data
assert f"{max(abs(x) for x in arm_delta):.1f} % below decode with the kill switch set" in DN.PLAN_ROWS[4][3], arm_delta
assert f"(down to {signed(min(tps_change('lo')))} %, est.)" in DN.PLAN_ROWS[4][3], tps_change('lo')
assert f"where the full-page time is {c1u['prefill']['attn_full_ms'] / 8:.2f} ms per layer" in DN.OPEN_HTML, c1u["prefill"]["attn_full_ms"]


def ab_table():
    """Section 6: predicted TTFT fall of the two A/B runs, working values in both runs."""
    rows = []
    for c in order:
        r = cells[c]
        m, t0 = r["pred"]["mid"], r["prefill"]["ttft_s"]
        run1, run1_b = m["reorder"]["ttft_s"], m["reorder_attn"]["ttft_s"]
        fall_b, fall_a = run1 - run1_b, run1 - m["amx_gdn"]["ttft_s"]
        assert abs(fall_a - (run1_b - m["amx_both"]["ttft_s"])) < 1e-9, c
        rows.append([f"{r['users']}", f"{r['prompt']:,}", f"{fall_b:.3f}", f"{100 * fall_b / t0:.1f}", f"{100 * fall_b / run1:.1f}",
                     f"{fall_a:.3f}", f"{100 * fall_a / t0:.1f}", f"{100 * fall_a / run1:.1f}", f"{100 * fall_a / run1_b:.1f}"])
    return table(["Users", "Prompt (tokens)", "Part B, A/B run: TTFT fall (s, est.)", "Part B: percent of the base run (est.)", "Part B: percent of run 1 (est.)",
                  "Part A, A/B run: TTFT fall (s, est.)", "Part A: percent of the base run (est.)", "Part A: percent of run 1, Part B off (est.)",
                  "Part A: percent of run 1, Part B on (est.)"], rows, num_cols=range(9))


_m8, _t8 = c8u["pred"]["mid"], c8u["prefill"]["ttft_s"]
ab_notes = ul([
    "The percent of the base run in the Part B columns equals the Part B column of section 4.",
    "The percent of the base run in the Part A columns is the Part A column of section 4 minus the Part 0 column.",
    "The A/B run of Part A has no predicted range." + ul([
        "The factors of Part 0 and of Part A are separate estimates. Section 4 defines no case that mixes a low factor with a high factor.",
        "So the pass rule for this run asks only that the TTFT falls.",
    ]),
    "The example is the cell with 8 users and prompt 1,024, with Part B off." + ul([
        f"The base run takes {_t8:.3f} s. Part 0 takes {_m8['reorder']['ttft_s']:.3f} s (est.). Part A takes {_m8['amx_gdn']['ttft_s']:.3f} s (est.).",
        f"The A/B run shows a fall of {100 * (_m8['reorder']['ttft_s'] - _m8['amx_gdn']['ttft_s']) / _m8['reorder']['ttft_s']:.1f} % (est.).",
        f"The fall from the base run is {abs(pct(_m8['amx_gdn']['ttft_s'], _t8)):.1f} % (est.). "
        f"The Part A range of this cell is {abs(pct(c8u['pred']['lo']['amx_gdn']['ttft_s'], _t8)):.0f} to {abs(pct(c8u['pred']['hi']['amx_gdn']['ttft_s'], _t8)):.0f} %.",
    ]),
])
factor_rows = [
    ["<b>GDN step, prefill, Part 0</b>", *A("s_gdn_reorder"), FB["part0"]],
    ["<b>GDN step, prefill, Part A</b>", *A("s_gdn_amx"), FB["parta"]],
    ["<b>GDN step, decode</b>", "1.0", "1.0", "1.0", FB["decode_gdn"]],
    ["<b>Full-page time of the attention, prefill, Part B</b>", *A("s_attn_prefill"), FB["attn_pf"]],
    ["<b>Attention busy time, decode, Part B</b>", *A("s_attn_decode"), FB["attn_dec"]],
    ["<b>Clock cost on the rest of a prefill pass, Part A</b> (a slowdown, not a speedup)", f"+{100 * tax['lo']:.1f} %", f"+{100 * tax['mid']:.1f} %", f"+{100 * tax['hi']:.0f} %", FB["tax"]],
    ["<b>Clock cost on the other attention work of a prefill pass, Part B</b> (a slowdown, not a speedup)", f"+{100 * tax_attn['lo']:.0f} %", f"+{100 * tax_attn['mid']:.0f} %", f"+{100 * tax_attn['hi']:.1f} %", ul([
        "Under Part B an attention worker runs tile work and AVX-512 work in the same job. The model assumes that its other attention work then runs at the core clock of the kernel. This clock is not measured.",
        "The other attention work is the busy time without the full-page time and without the join wait. It consists of the AVX-512 scoring of the pages that the pass writes, and the join. "
        f"It is {rng(attn_other(one_u), 1, ' ms')} per prefill pass with 1 user and {rng(attn_other(eight_u), 1, ' ms')} with 8 users (est.).",
        "Working value and low case: 1.90 GHz, so 2.70 / 1.90 - 1 = 42 %. High case: 2.40 GHz, so 2.70 / 2.40 - 1 = 12.5 %.",
        "The join wait is not CPU work of this kind. The model holds it fixed.",
        "Decode needs no such row. Its factor is a ratio of whole busy times. So the other attention work and the lower clock are already inside the factor.",
    ])],
]

differences_table = table(["", "Attention layer (llama-3.1-8b)", "GDN layer (Qwen3.5 4B)"], [
    ["What it remembers", "The K and V rows of every earlier token (the KV cache).", "One matrix S per value head. Each token rewrites it."],
    ["Memory per sequence", "Grows. 131,072 bytes per context token over 32 layers.",
     "Fixed at any context length. 50.25 MiB over 24 layers: 48 MiB of state and 2.25 MiB of convolution history " + ref(4) + "."],
    ["CPU work per new token", f"Grows with the context. {FD.macs_per_context_token(32, 32, 128):,} bf16 multiply-adds per context token.",
     f"Constant. {FD.gdn_fmas_per_token() / 1e6:.1f} million FP32 multiply-adds " + ref(3) + "."],
    ["Number formats", "bf16 times bf16.", "bf16 inputs times an FP32 state " + ref(3) + "."],
    ["Order of tokens", "The tokens of one prefill pass can be scored in parallel.", "Token t needs the state that token t-1 left. One serial chain per key head " + ref(5) + "."],
    ["Threads in tron (this setup, 56 threads)", "The 40 attention workers.", "The main thread and 15 main helpers. The 40 attention workers wait " + ref(5) + "."],
    ["Other ways to run it", "FPGA attention (attention computed on the FPGA cards), for heads of 64 or 128 values.", "None. Host CPU only."],
    ["AMX today", "Yes, for 128-wide heads with 4 query heads per KV head.", "No."],
])

can_table = table(["Work", "Share of the time today", "Can AMX help?", "Why"], [
    ["GDN, prefill", f"{rng(gdn_pf_long + gdn_pf_short)} of a pass", "<b>Yes</b>, with Part A. Part 0 comes first and needs no AMX.",
     "A chain of 128 tokens can be written as matrix products. Then all 16 rows of a tile carry data."],
    ["GDN, decode", f"{rng(gdn_dec_tr_1u + gdn_dec_tr_8u)} of a step (inside the traced runs)", "<b>No</b>.",
     "One token per sequence. The state is FP32 and differs per sequence. A tile would use 1 or 2 of its 16 rows."],
    ["Full attention, prefill", f"{rng(attn_pf_short + attn_pf_long)} of a pass", "<b>Yes</b>, with Part B.", f"Same method as today's 128-wide kernels. Part B makes only the full-page time faster. That is {rng(full_of_pass)} of a pass (est.)."],
    ["Full attention, decode", f"{rng(attn_dec_all)} of a step", "<b>Not on this server</b> (est.). Part B applies, and its working value is no gain.",
     f"<ul><li>About half of this time is a memory stall (47 % of a page unit on delphi-3bda {ref(12)}). A new kernel does not shorten the stall.</li>"
     "<li>The lower core clock under AMX cancels the remaining gain (est.).</li></ul>"],
    ["Convolution, norms, output gate", f"inside the GDN step, about {DN.OTHER_US} us of {DN.STEP_TODAY} us (est.)", "No.", "Small. Every operation is followed by a bf16 rounding."],
])

# ---------------------------------------------------------------- figures
la_mac = FD.macs_per_context_token(32, 32, 128)
qa_mac = FD.macs_per_context_token(8, 16, 256)
gdn_fma = FD.gdn_fmas_per_token()
fig_stack = figure(FS.layer_stack(), "<b>Figure 1.</b> The 32 layers of each model. "
                   '<span class="take">Qwen3.5 4B keeps full attention in every fourth layer only.</span>', "fig1")
fig_flow = figure(FS.token_flow(), "<b>Figure 2.</b> What one new token does in one layer. "
                  '<span class="take">Attention looks at a list that grows. GDN rewrites a matrix of fixed size.</span>'
                  "<ul><li>Gray boxes run on the FPGA cards.</li>"
                  "<li>Colored boxes run on the host CPU.</li></ul>", "fig2")
fig_work = figure(FD.fig_work_vs_context(), "<b>Figure 3.</b> CPU arithmetic per generated token: a count computed from the model shape, not a timing. "
                  '<span class="take">By this count GDN looks small at long context. Section 3 shows that its time is not small.</span>'
                  f"<ul><li>Attention costs {la_mac:,} multiply-adds per context token in llama-3.1-8b and {qa_mac:,} in Qwen3.5 4B.</li>"
                  f"<li>GDN costs {gdn_fma / 1e6:.1f} million multiply-adds per token at every context length.</li></ul>", "fig3")
fig_ttft = figure(FD.fig_baseline_ttft(pred), "<b>Figure 4.</b> Measured time to first token (TTFT) of the slowest user. Median of "
                  f"{n_samples[0]} runs per cell. "
                  f'<span class="take">With 8 users the same prompt length takes {rng(ttft_x8, 1, "")} times longer than with 1 user.</span>', "fig4")
fig_tps = figure(FD.fig_baseline_tps(pred), "<b>Figure 5.</b> Measured decode speed per user. Median of "
                 f"{n_samples[0]} runs per cell. "
                 f'<span class="take">From prompt 1,024 to prompt 8,192 the speed falls by {abs(pct(tps_1u[-1], tps_1u[0])):.0f} % with 1 user '
                 f"and by {abs(pct(tps_8u[-1], tps_8u[0])):.0f} % with 8 users.</span>", "fig5")
fig_split_pf = figure(FD.fig_split(pred, "prefill"), "<b>Figure 6.</b> Wall time of one prefill pass, split into three parts. "
                      f'<span class="take">GDN takes {rng(gdn_pf_short)} of a pass at prompt 1,024 and {rng(gdn_pf_long)} at prompt 8,192. '
                      "Its time per pass does not change with the prompt length, and the attention time grows.</span>"
                      "<ul><li>The attention busy time comes from the attention statistics.</li>"
                      "<li>The GDN wall comes from the trace.</li>"
                      "<li>The rest is the remainder.</li></ul>", "fig6")
fig_split_dec = figure(FD.fig_split(pred, "decode"), "<b>Figure 7.</b> Wall time of one decode step, split the same way. "
                       f'<span class="take">GDN takes {rng(gdn_dec_1u)} of a step with 1 user and {rng(gdn_dec_8u)} with 8 users (est.).</span>'
                       "<ul><li>The GDN wall comes from the traced runs.</li>"
                       "<li>The step wall and the attention busy time come from the untraced runs.</li>"
                       "<li>So the GDN shares and the rest are estimates (est.). They can be too high or too low (see the limit of the decode numbers above).</li></ul>", "fig7")
fig_lanes = figure(FG.lanes(gdn_layer_ms, rest_layer_ms, 128, slow_step_us, ASM["s_gdn_amx"]["mid"], clock_layer_ms),
                   "<b>Figure 8.</b> Who does what, and when, in one GDN layer of a prefill pass (1 user, prompt 1,024). "
                   '<span class="take">The red path is serial: token t cannot start before token t-1 of the same key head. '
                   "More threads cannot shorten it, but a faster GDN step can.</span>"
                   "<ul><li>The red path has 128 GDN steps, one after another.</li>"
                   "<li>Durations are to scale.</li>"
                   "<li>Solid blocks are work. Dashed outlines are waiting.</li>"
                   "<li>The gray block is the mean per layer of the FPGA matrix multiplies and the small host kernels. Its position inside the layer is schematic.</li></ul>", "fig8")
fig_pred = figure(FD.fig_pred_ttft(pred), "<b>Figure 9.</b> Time to first token, relative to today's measured value (100 %). "
                  f'<span class="take">With both AMX kernels, TTFT falls by {fall(ttft_change("amx_both"))} (est.). Part 0 alone gives {fall(ttft_change("reorder"))} (est.).</span>'
                  "<ul><li>The ring is Part 0 alone (no AMX).</li><li>The green dot is both AMX kernels at the working values.</li>"
                  "<li>The shaded bar is the range between the low and the high factors.</li><li>Labels give seconds.</li></ul>", "fig9")
fig_pred_tps = figure(FD.fig_pred_tps(pred), "<b>Figure 10.</b> Decode speed per user with Part B, relative to today's measured value (100 %). "
                      f'<span class="take">The working value is no change (est.). The range is {signed(min(tps_change("lo")))} % to {signed(max(tps_change("hi")))} % (est.).</span>'
                      "<ul><li>No GDN change applies to decode.</li><li>The shaded bar is the range between the low and the high factors.</li></ul>", "fig10")
fig_path = figure(FG.call_path(), "<b>Figure 11.</b> Where the new code sits. "
                  '<span class="take">Prefill chains take advance() on every machine. Decode chains keep today\'s code path.</span>'
                  "<ul><li>Green boxes are new AMX code.</li>"
                  "<li>The blue box named advance() is new code without AMX.</li></ul>", "fig11")
fig_block = figure(FG.block_kernel(DN.BLOCK, DN.block_counts()), "<b>Figure 12.</b> The four stages of the AMX block kernel for one value head. "
                   '<span class="take">The three large products become matrix times matrix. So all 16 rows of a tile carry data.</span>'
                   "<ul><li>Dashed green frames are AMX tile products.</li></ul>", "fig12")
fig_kernel = figure(FD.fig_kernel_cycles(DN.kernel_rows()), "<b>Figure 13.</b> Time of the recurrence per value head per prompt token. "
                    '<span class="take">Most of the estimated gain comes from keeping the state in the L1 cache (Part 0). The AMX kernel adds a second, smaller gain (Part A).</span>'
                    "<ul><li>The first bar is measured.</li>"
                    "<li>The hatched bars are estimates from operation counts and measured instruction costs.</li></ul>", "fig13")

# ---------------------------------------------------------------- words
WORDS = [
    ("tron, runtron", "tron is the inference program under test. runtron is its command-line tool."),
    ("Qwen3.5 4B", "the model under study. Its tron name is <code>ingested-qwen-3.5-4b</code>."),
    ("llama-3.1-8b, qwen-3-4b", "two models that tron already runs. Every layer of both is an attention layer. Our earlier AMX numbers come from qwen-3-4b."),
    ("GDN (GatedDeltaNet)", "a recurrent layer type. It does the job of attention with a matrix of fixed size, the state."),
    ("state S", "the memory of a GDN layer. One matrix of 128 key rows by 128 value columns per value head, in FP32."),
    ("key head, value head", "a GDN layer has 16 key heads and 32 value heads. Each key head serves 2 value heads."),
    ("decay, beta", "two numbers that the model computes per token and value head. Decay shrinks the old state. Beta scales the correction."),
    ("convolution, norm, output gate", "the small operations around the recurrence of a GDN layer. The convolution is a filter over the last 4 tokens. The norm is a normalization, and the output gate is a multiplication by a gate value."),
    ("recurrence", "the four lines that read and rewrite the state for one token (figure 2)."),
    ("SiLU, RMS norm", "SiLU is the function x / (1 + exp(-x)). The RMS norm divides the values by their root mean square."),
    ("full attention", "ordinary attention: the new token is scored against every earlier token."),
    ("software attention", "full attention computed on the host CPU, not on the FPGA cards."),
    ("head, query head, KV head", "attention splits a token's vector into heads. Qwen3.5 4B has 16 query heads and 4 KV heads per attention layer. A KV head holds the stored K and V rows that 4 query heads share."),
    ("128-wide, 256-wide, 256 x 4", "the number of values per head. 256 x 4 means heads of 256 values with 4 query heads per KV head."),
    ("KV cache, KV page", "the stored K and V rows of earlier tokens. tron keeps them in pages of 64 tokens."),
    ("K token", "one stored K row that a query is scored against. The attention statistics count K tokens per kernel."),
    ("page unit", "the attention work of one query token on one KV page of one KV head."),
    ("QK, PV", "the two products of the attention kernel. QK is queries times stored keys, and it gives the scores. PV is softmax weights times stored values."),
    ("AMX", "Intel Advanced Matrix Extensions: tile registers, and instructions that multiply two tiles."),
    ("tile, tile row", "an AMX register of 16 rows by 64 bytes. A tile product is efficient only when most of the 16 rows carry data."),
    ("tile product (TDPBF16PS)", "one AMX instruction. It computes 8,192 bf16 multiply-adds and adds them into a 16 by 16 FP32 tile."),
    ("AVX-512, FMA", "512-bit vector instructions. FMA is the fused multiply-add on 16 FP32 values at once."),
    ("bf16, fp16, FP32, float64", "number formats.<ul><li>bf16 has 16 bits and 8 significant bits.</li><li>fp16 has 16 bits and 11 significant bits.</li><li>FP32 has 32 bits and 24 significant bits.</li>"
     "<li>float64 has 64 bits. The checks use it as the exact reference.</li></ul>"),
    ("piece, plane", "Part A splits one FP32 value into 3 bf16 values, the pieces.<ul><li>The sum of the pieces is the FP32 value when its size is 2^-103 (about 9.9e-32) or larger. Section 5.4 gives the rule.</li>"
     "<li>A plane is the matrix of one piece of every state value.</li></ul>"),
    ("subnormal value", "a nonzero value that is smaller than the smallest normal value of its number format. For bf16 and for FP32 the smallest normal value is 2^-126, about 1.2e-38."),
    ("L1, L2 cache, cache line", "the two private caches of a CPU core. They hold 48 KiB and 2 MiB on this CPU, and data in L1 is the fastest to reach. A cache line is 64 bytes."),
    ("core clock", "the frequency at which a CPU core runs. The CPU lowers it while AVX-512 or AMX instructions run."),
    ("clock probe", "our small test program. It runs one instruction mix on one CPU and reads the core clock."),
    ("tile run, AVX-512 run, turn", "a tile run is a stretch of tile instructions with no AVX-512 work between them. An AVX-512 run is a stretch of AVX-512 work with no tile instruction. A turn is one tile run plus the AVX-512 run next to it."),
    ("FPGA cards", "the accelerator cards that do tron's large matrix multiplies (projections, feed-forward layers)."),
    ("host", "the server's own CPUs, as opposed to the FPGA cards."),
    ("engine, tp4", "an engine is one running copy of the model. tp4 is the executor that spreads one engine over four FPGA cards."),
    ("plugin", "the C++ code that tron generates for one model."),
    ("kernel", "a small, performance-critical routine, for example the GDN recurrence or the attention dot products."),
    ("dispatch", "the code that picks a kernel at run time."),
    ("prefill, TTFT", "prefill is the processing of the prompt. TTFT is the time to first token: from the request to the first generated token."),
    ("decode, tok/s", "decode is the generation of tokens after the prompt. Its speed is given in tokens per second per user."),
    ("pass, decode step", "a pass is one forward computation through all 32 layers. A prefill pass holds 128 prompt tokens per user. A decode step is a pass with one token per user."),
    ("wall", "wall-clock time: the elapsed time from the start of a piece of work to its end, waits included."),
    ("us", "the microsecond, one millionth of a second."),
    ("percentage point", "the unit of a difference between two percentages."),
    ("chain", "the consecutive tokens of one sequence in one pass. A GDN layer must take them in order."),
    ("GDN step", "the work of one token for one key head. It contains the convolution, the recurrence on 2 value heads, the norm and the output gate."),
    ("work item", "one chain of one key head. The GDN threads divide the work items among themselves."),
    ("working copy", "in prefill each GDN thread copies the state of one key head (128 KiB) to a private buffer. The thread works on this copy and then copies it back."),
    ("token form, block form", "two ways to compute the same recurrence. The token form updates the state token by token, as tron does today. The block form takes a block of tokens at once with matrix products."),
    ("block, block kernel", "a block is 32 consecutive tokens of a chain. The block kernel is the AMX routine of Part A for one block."),
    ("column-half order, slice", "the loop order of Part 0. A slice is a group of value columns of the state, here one half (64 columns)."),
    ("main thread, main helpers, attention workers", "tron's CPU threads. The main thread and 15 main helpers run GDN. The 40 attention workers run software attention only."),
    ("application CPUs", "the CPUs that tron's threads may use: 56 per engine in this setup."),
    ("attention statistics", "counters and timers that tron reports when the environment variable <code>TRON_ATTN_STATS=1</code> is set."),
    ("attention busy time", "the time of the attention jobs on one attention worker. It leaves out the worker's waits for the queries (Q) and for K and V. The page gives the mean over the 40 workers."
     "<ul><li>The busy time has four parts. The first is the scoring of the full pages of earlier passes.</li><li>The second is the scoring of the pages that the pass in progress writes.</li>"
     "<li>The third is the join.</li><li>The fourth is the join wait.</li></ul>"),
    ("join, join wait", "the join is the last step of an attention job.<ul><li>The join adds the partial results of the workers into one result per token.</li>"
     "<li>The join wait is a worker's waiting time in the join. It ends when the other workers have finished their scoring. It is part of the busy time.</li></ul>"),
    ("other attention work", "the attention busy time of a prefill pass without the full-page time and without the join wait. It is the AVX-512 scoring of the pages that the pass writes, and the join (est.)."),
    ("full-page time", "one part of the attention busy time of a prefill pass. It is the time spent on the full pages of earlier passes (est.). In a prefill pass Part B makes only this part faster."),
    ("attention wait", "the wall time of the attention jobs on attention worker 0, minus the mean busy time.<ul><li>It contains the worker's wait for Q at the start of a job.</li>"
     "<li>It also contains the worker's wait for K and V in the middle of a job.</li><li>tron has no timer for either wait alone.</li></ul>"),
    ("memory stall", "the time a core waits while data is loaded from main memory. It is part of the busy time."),
    ("trace, trace event", "a trace is a recording of timed events made by runtron, in the Perfetto format. Its trace event named GatedDeltaNet is tron's only timer for GDN."),
    ("kill switch", "the environment variable <code>TRON_AMX_DISABLE=1</code>. It turns the AMX kernels off at run time."),
    ("arm", "one of the two settings of a comparison. Here: AMX allowed, or the kill switch set."),
    ("A/B run", "two runs that differ in one switch only."),
    ("base build, base run", "the base build is tron without Parts 0, A and B. A base run is a run of the base build. It is made in the same session as the runs that are compared with it."),
    ("GDN switch", "a new run-time switch of this design. It turns the GDN block path of Part A off alone."),
    ("token path, column-half path, block path", "the three code paths of the GDN recurrence.<ul><li>The token path runs <code>step()</code> per token. It is today's code.</li>"
     "<li>The column-half path runs <code>advance()</code> with the loop order of Part 0.</li><li>The block path runs <code>advance()</code> with the block kernel of Part A.</li></ul>"),
    ("chain path", "<code>advance()</code>, the new code path for chains of 2 or more tokens. The column-half path and the block path both run <code>advance()</code>."),
    ("session", "one series of runs on delphi-3b35 with no reboot between them. The server's own settings (CPU settings, SYSTEM_CONFIG) also stay unchanged between them."),
    ("cell", "one combination of user count and prompt length."),
    ("prompt N", "a prompt of N tokens. Every baseline run then generates 256 tokens per user. A traced run generates 32 tokens per user."),
    ("Part 0, Part A, Part B", "the three proposed changes.<ul><li>Part 0 is a new loop order for GDN prompt processing, without AMX.</li><li>Part A is the AMX block kernel for GDN.</li>"
     "<li>Part B is the AMX attention kernel for 256-wide heads.</li></ul>"),
    ("factor, working value", "a factor is old time divided by new time. Each factor has a low value, a working value and a high value. The working value is the one we expect."),
    ("error band", "a stated limit on how far a result may differ from the reference result."),
    ("increment", "the step between two neighboring values of a number format, here bf16 or FP32."),
    ("logits", "per-word scores. The model gives one score to every word of its vocabulary for the next token."),
    ("numerics contract", "a written rule. It says which results must be equal bit for bit and which may differ inside an error band."),
    ("pull request", "a proposed code change on GitHub that is not merged yet."),
    ("delphi-3b35, our half", "the test server. We use its second CPU socket and FPGA cards 4 to 7."),
    ("delphi-3bda", "a second server with the same CPU model. Our earlier AMX numbers were measured there."),
    ("TSX, flat-frequency service, deep idle states", "three CPU settings that differ between the two servers. The flat-frequency service holds the core clock at a fixed value."),
    ("Hugging Face Transformers, vLLM, SGLang, llama.cpp", "open-source programs that also run this model."),
    ("est.", "an estimate. Every number without it is measured or read from the code."),
    ("Insufficient data", "a value that we could not measure. The text names the measurement that would give it."),
]
words_html = "<details><summary>Words used here</summary><ul>" + "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in WORDS) + "</ul></details>"
refs_html = '<ol class="refs">' + "".join(f'<li id="ref{i + 1}">{r}</li>' for i, r in enumerate(DN.REFS)) + "</ol>"

s1_intro = ul([
    f"llama-3.1-8b has 32 layers. Every layer is a full-attention layer {ref(20)}.",
    f"Qwen3.5 4B has 32 layers too. 24 are GDN layers and 8 are full-attention layers {ref(1, 2)}.",
    "A GDN layer does the job of attention. It brings information from earlier tokens into the current token. It uses a different mechanism.",
])
s1_attn = ul([
    f"The 8 full-attention layers of Qwen3.5 4B differ from llama's too. They have 16 query heads of 256 values and 4 KV heads {ref(17)}. llama-3.1-8b has 32 heads of 128 values and 8 KV heads {ref(20)}.",
    f"tron's AMX attention kernels accept only 128-wide heads {ref(6)}.",
    f"tron's FPGA attention accepts only 64-wide and 128-wide heads {ref(7)}.",
    "So every attention layer of this model runs the AVX-512 path, at every prompt length.",
    f"The attention statistics confirm it. AMX scored 0 K tokens in all {n_runs} runs {ref(9)}.",
])
s2_setup = ul([
    "The server is delphi-3b35, with two Xeon 6962P CPUs.",
    "We used our half: socket 1 with 56 application CPUs, and FPGA cards 4 to 7. The cards have the PCI addresses 90, 93, b9 and bc. "
    'The setting is <code class="nw">SYSTEM_CONFIG="--instance 1,2"</code>.',
    f"The build is tron pull request #3696 at commit 72e1191804. It was built with clang 19.1.7, with the AMX kernels compiled in. The model is not on tron's main branch yet {ref(1)}.",
    "The model is <code>ingested-qwen-3.5-4b-tp4</code>: one engine on four FPGA cards.",
    f"The runs used runtron at prompt 1,024, 4,096 or 8,192, with 1 or 8 users. Each run generated 256 tokens per user. Each cell has {n_samples[0]} runs.",
    f"A load snapshot of 10 s was taken before every run. Our application CPUs were at most {our_busy:.1f} % busy. "
    f"The other socket ran two servers of another team and was {rng(s0, 1)} busy {ref(15)}.",
    f"The core clock under AVX-512 work is 2.70 GHz on {len(cpu_base)} of the {len(clock3)} CPUs that we probed. On CPUs {', '.join(str(c) for c in cpu_fast[:-1])} and {cpu_fast[-1]} it is 4.00 GHz {ref(11)}.",
])
s2_notes = ul([
    "The runs used two arms: AMX allowed, and the kill switch set.",
    f"On this model both arms run the same code. Their decode medians differ by {min(arm_delta):+.1f} to {max(arm_delta):+.1f} %. So all runs of a cell count as baseline samples.",
    f"These numbers are not comparable with our earlier numbers from delphi-3bda. Three CPU settings differ: TSX is off, no flat-frequency service runs, and deep idle states are on {ref(12)}.",
    f"The model's registry entry has the support level <code>cpp_plugin</code>. This level means that the plugin compiles and that its tokens are not yet valid {ref(1)}. The timings do not depend on that.",
])
s3_how = (ul([
    f"The attention statistics were turned on in every run, with <code>TRON_ATTN_STATS=1</code> {ref(8)}.",
    "The statistics give the wall time of every pass. The page calls it the pass wall. For a decode step the page calls it the step wall.",
]) + "<h4>Attention busy time</h4>" + ul([
    f"The statistics give the attention busy time per worker. It is the time of the attention jobs without the worker's waits for Q and for K and V {ref(8)}. "
    "The page divides the sum over all workers by the 40 workers.",
    "The busy time is not kernel time only. It contains four parts:" + ul([
        "the scoring of the full pages of earlier passes",
        "the scoring of the pages that the pass in progress writes",
        "the join",
        "the join wait",
    ]),
]) + "<h4>Join wait</h4>" + ul([
    "A worker finishes its scoring. Then it waits in the join until the other workers have finished theirs. This wait is the join wait.",
    f"The statistics time the join wait. It is inside the busy time {ref(8)}.",
    f"Per prefill pass the join wait is {rng(join_pf_1u, 1, ' ms')} with 1 user and {rng(join_pf_8u, 1, ' ms')} with 8 users. "
    f"With 1 user at prompt 1,024, that is {join_share_pf(c1u):.0f} % of the busy time. With 8 users at prompt 8,192 it is {join_share_pf(c8u_long):.1f} %.",
    f"Per decode step the join wait is {min(join_dec):.2f} to {max(join_dec):.2f} ms, or {rng(join_share_dec)} of the busy time.",
]) + "<h4>Attention wait</h4>" + ul([
    "The statistics also give the wall time of the attention jobs on attention worker 0, waits included. This wall time is longer than the mean busy time:" + ul([
        f"by {rng(wait_pf_1u, 1, ' ms')} per prefill pass with 1 user",
        f"by {rng(wait_pf_8u, 0, ' ms')} per prefill pass with 8 users",
        f"by {rng(wait_dec, 1, ' ms')} per decode step",
    ]),
    "The page calls this difference the attention wait. It contains two waits of worker 0:" + ul([
        "The first is the wait for Q at the start of each job.",
        f"The second is the wait for K and V. It comes before the scoring of the pages that the pass writes {ref(8)}.",
    ]),
    "The attention wait also contains the difference between the busy time of worker 0 and the mean. So it does not give the wait for K and V alone. tron has no timer for that wait.",
    "The attention wait stays in the rest.",
]) + "<h4>GDN wall and the rest</h4>" + ul([
    f"The statistics do not cover GDN. The GDN code does not call the statistics code {ref(8)}.",
    "GDN was timed with tron's trace, in one traced run per cell. A traced run generates 32 tokens per user.",
    f"The trace event named GatedDeltaNet covers the GDN host work of one layer on one thread {ref(10)}. "
    "The GDN wall of a layer runs from the first thread's start to the last thread's end.",
    "The rest is the pass wall minus the GDN wall minus the attention busy time. It is FPGA matrix multiplies, small host kernels and the attention wait.",
]) + "<h4>Limit of the decode numbers</h4>" + ul([
    "The decode table divides the GDN wall of a traced run by the step wall of the untraced runs. So its GDN shares are estimates (est.).",
    "The rest of a decode step is computed with the same GDN wall. It is an estimate too. The last column gives the GDN share inside the traced run.",
    "The two kinds of run differ in three ways:" + ul([
        f"The trace is on. A traced decode step is {rng(trace_longer)} longer than an untraced one. A traced prefill pass is {rng(trace_longer_pf, 1)} longer.",
        "A traced run generates 32 tokens per user, and an untraced run generates 256.",
        "The traced mean leaves out the first pass of each kind, and the untraced mean covers every pass.",
    ]),
    "The untraced runs have no timer for GDN. So we do not know whether the GDN shares are too high or too low, or by how much. Insufficient data.",
    "The GDN wall counter proposed in section 5.6 (row Counters) runs without the trace. It would give the direction and the size of the error.",
    "A decode step of the traced run is 0.5 to 1.0 ms longer than a step of the untraced runs." + ul([
        "0.1 to 0.3 ms of that is attention busy time.",
        f"No timer locates the other 0.3 to 0.7 ms. With 1 user that is 73 to 134 % of the traced GDN wall. With 8 users it is 11 to 22 % {ref(18)}.",
    ]),
    f"The prefill table is built the same way. There the time that no timer locates is at most 4 % of the GDN wall {ref(18)}.",
]))
s3_say = ul([
    f"<b>The GDN time of a prefill pass does not depend on the prompt length.</b> It is {rng(gdn_pf_1u, 1, ' ms')} with 1 user and {rng(gdn_pf_8u, 0, ' ms')} with 8 users.",
    f"<b>One GDN step takes {min(thr_slow):.1f} to {max(thr_slow):.1f} us on {16 - n_fast} of the 16 GDN threads in prefill.</b>" + ul([
        f"The {n_fast} threads on CPUs {' and '.join(fast_cpus)} take {min(thr_fast):.1f} to {max(thr_fast):.1f} us. Their cores run at 4.00 GHz {ref(11)}.",
        f"The mean over the 16 threads is {rng(step_mean_pf, 1, ' us')}.",
    ]),
    f"<b>The slowest thread sets the GDN wall of a layer.</b> One GDN layer takes {gdn_layer_ms:.2f} ms for 128 tokens with 1 user. That is {slow_step_us:.1f} us per token.",
    f"<b>A stand-alone benchmark of the recurrence alone takes {rec_us:.2f} us per value head</b> (1 thread, 2 MiB state) {ref(11)}. The convolution takes {conv_us:.2f} us per key head." + ul([
        "The benchmark is not the same quantity as the traced GDN step.",
        f"In tron the recurrence takes about {in_tron_rec:.1f} us per value head (est.). This estimate is {DN.STEP_TODAY} us minus {DN.OTHER_US} us of other work, for 2 value heads.",
    ]),
    "<b>Our hypothesis is that the GDN step is limited by moving the state, not by arithmetic.</b>" + ul([
        "A value head's matrix is 64 KiB. The L1 cache is 48 KiB. Each token passes over the matrix twice.",
        f"The arithmetic alone needs 0.95 to 1.16 us per value head (est.), against about {in_tron_rec:.1f} us (est.) in tron.",
        "Task 1 of the plan confirms or rejects this hypothesis. A timing on another CPU gives the moving of the state a smaller share (section 4, low case of Part 0).",
    ]),
    f"<b>The same GDN step takes {rng(step_mean_dec, 0, ' us')} in decode</b> (mean over the threads, traced runs)." + ul([
        "Our hypothesis has two parts. In decode the state comes from outside the core's own caches for every token. "
        f"The check for invalid values reads the state once more {ref(4)}.",
        "The open points name the measurement that confirms or rejects this hypothesis.",
    ]),
    "<b>Only 16 of the 56 threads run GDN.</b> With 8 users each of the 16 threads has 8 chains to run, one after another. "
    "Compared with the wall with 1 user, the GDN wall with 8 users is:" + ul([
        f"{rng(x8_pf, 1, '')} times as long in prefill",
        f"{rng(x8_dec, 1, '')} times as long in decode",
    ]),
])
s4_method = ul([
    "The layers of a pass run one after another.",
    "In a GDN layer the FPGA projections, the host work and the next projection run one after another. So a time saved in GDN shortens the pass by the same amount.",
    f"In an attention layer the scoring of the full pages starts when Q is ready. It can run while the FPGA cards produce K and V of the pass {ref(8)}. "
    "Assumption of the model: with Part B on, this scoring still ends after K and V are ready." + ul([
        "Under this assumption a time saved in attention shortens the pass by the same amount.",
        "The open point on the wait for K and V names the measurement that tests it.",
    ]),
])
s4_inputs = (
    "<h4>Symbols of the formulas</h4>" + ul([
        "s_gdn and s_attn are the factors of the table below for the GDN step and for the attention.",
        "attention_scaled is the part of the attention busy time that s_attn divides.",
        "clock_cost and clock_cost_attention are the last two rows of the table below.",
        "attention_other is the other attention work: the AVX-512 scoring of the pages that the pass writes, and the join.",
        "step is the wall of one decode step. step_new is computed like pass_new.",
    ])
    + "<h4>Prefill: what the factor divides</h4>" + ul([
        "<b>In a prefill pass the factor divides the full-page time only.</b> The AMX kernel replaces the scoring of the full pages of earlier passes.",
        f"The pages that the pass in progress writes stay on the AVX-512 path {ref(8)}. They contain these shares of the scored K tokens of a pass {ref(9)}:" + ul([
            "12.6 % at prompt 1,024",
            "3.1 % at prompt 4,096",
            "1.6 % at prompt 8,192",
        ]),
        "The join and the join wait are not kernel work.",
    ])
    + "<h4>Size of the full-page time</h4>" + ul([
        "The busy time without the join wait fits a straight line. The line is a fixed part per pass, plus 67 ns of CPU time per K token in full pages. "
        f"The error of the line is below 0.1 ms at each of the three prompt lengths {ref(18)}.",
        "The full-page time is the part that grows with the K tokens (est.). It is this share of the busy time (est.):" + ul([
            f"{full_share(lambda r: r is c1u)[0]:.0f} % with 1 user at prompt 1,024",
            f"{full_share(lambda r: r is c8u)[0]:.0f} % with 8 users at prompt 1,024",
            f"{rng(full_share(long_p))} at prompt 8,192",
        ]),
        "The part that s_attn does not divide holds the join wait and the other attention work. Its size per pass is (est.):" + ul([
            f"{rng(attn_fixed(one_u), 1, ' ms')} with 1 user",
            f"{rng(attn_fixed(eight_u), 1, ' ms')} with 8 users",
        ]),
        "The model holds the join wait fixed. The other attention work gets slower under Part B (last row of the factor table).",
    ])
    + "<h4>Join wait of a prefill pass</h4>" + ul([
        "<b>The join wait of a prefill pass grows far less than the kernel work.</b>",
        f"From prompt 1,024 to prompt 8,192 the K tokens in full pages become 9 times as many. The join wait gets {min(join_growth):.1f} to {max(join_growth):.1f} times longer.",
        "The model holds it fixed.",
    ])
    + "<h4>Check against a measurement</h4>" + ul([
        f"On delphi-3bda the same statistics were recorded for qwen-3-4b with the 128-wide kernel on and off {ref(23)}. Each arm was one run with 8 users and prompt 1,024.",
        "The kernel scored every K token of the full pages. It scored no K token of the pages that the pass wrote.",
        "The busy time per pass got 1.88 times shorter. The join wait rose from 4.1 to 12.0 ms. This rise is already inside the measured ratio of 1.88 times.",
        "The pass wall fell by 99.7 ms, and the busy time fell by 106.5 ms. So 94 % of the fall of the busy time appeared in the pass wall.",
        "The kernel factor of that server is 2.95 to 3.05 (est.). With that factor, this model gives 1.90 to 1.93 times for our cell with 8 users and prompt 1,024 (est.). "
        f"A factor on the whole busy time gives 2.95 to 3.05 times {ref(18)}.",
        "The measurement is of qwen-3-4b on delphi-3bda. The model value uses the parts of the busy time of Qwen3.5 4B on delphi-3b35. It also has no clock cost for the other attention work.",
        "So this is a check of plausibility, not a fit.",
    ])
    + "<h4>Decode: what the factor divides</h4>" + ul([
        f"<b>In a decode step the factor divides the whole busy time.</b> The decode factor is a ratio of whole busy times of attention worker 0 {ref(19)}. "
        "So the join, the join wait and the pages of the pass in progress are already in it.",
        f"With 8 users the mean busy time per decode step got 1.18 to 1.19 times shorter in three A/B runs on delphi-3bda {ref(23)}.",
        f"If the decode join wait did not shrink with the kernel, the decode range would be {signed(min(tps_join_fixed('lo')))} % to {signed(max(tps_join_fixed('hi')))} % (est.).",
    ])
    + "<h4>Sensitivity of the prefill model</h4>" + ul([
        f"If the factor divided the whole busy time, Part B would give a TTFT fall of {fall(wb_b['mid'])} (est.). Its range would be {fall(wb_all(wb_b))}.",
        f"Parts A and B together would then give {fall(wb_ab['mid'])} (est.). Their range would be {fall(wb_all(wb_ab))}.",
    ])
    + "<h4>Measured inputs</h4>" + ul([
        "runtron gives the TTFT and the decode speed (section 2).",
        "The attention statistics give the pass wall, the attention busy time and the join wait (section 3). They also give the K tokens and the number of passes.",
        "The trace gives the GDN wall (section 3).",
        f"Two inputs were measured today for this prediction {ref(11)}:" + ul([
            "the core clock under AMX on delphi-3b35",
            "the cost of the tile and FMA instructions",
        ]),
    ])
    + "<h4>Estimated inputs and ranges</h4>" + ul([
        "The estimated inputs are the factors in the table below. Each one comes from:" + ul([
            "operation counts,",
            "measured instruction costs,",
            "an earlier measurement on delphi-3bda,",
            "or a stand-alone timing on another CPU (the low case of Part 0).",
        ]),
        "The low case uses every low factor together. The high case uses every high factor together.",
    ])
)
clock_note = ('<div class="warn"><b>The clock probe measured the core clock under AMX on one of our CPUs today ' + ref(11) + ".</b>" + ul([
    "AVX-512 FMA loop: 2.70 GHz.",
    "Tile products only, after the upper halves of the vector registers were cleared: 2.40 GHz.",
    "Tile products only, with 512-bit values still in the registers: 1.90 GHz.",
    "Short turns of 4 tile products and 64 FMAs (35 ns per turn), with the clearing: 1.90 GHz." + ul([
        "The 4 tile products alone take 34.1 ns at this clock (est.). The estimate uses the rate of the loop with tile products only.",
        "So the FMAs run while the tile products run. This turn has no AVX-512 run of its own.",
    ]),
    "Long turns of 4,096 tile products and 16,384 FMAs (33 us per turn), with the clearing: 2.40 GHz. "
    "The tile run takes 27.6 us of the turn and the FMA run 5.4 us (est.). The estimate uses the rate of the loop with tile products only.",
    "No other turn was probed." + ul([
        "The two probed turns differ in length and in mix. The short turn has 16 FMAs per tile product. The long turn has 4.",
        "Neither proposed kernel has a single turn length. Their runs are listed in the second table of section 5.3 (block kernel) and in section 5.5 (attention kernel).",
        "Every tile run of both kernels is longer than the tile part of the short turn (34 ns) (est.). "
        "Every tile run is also shorter than the tile run of the long turn (27.6 us) (est.).",
        "The probe does not show which clock these mixes get. Insufficient data. Tasks 3 and 4 of the plan measure it.",
    ]),
    "The working values assume 2.40 GHz for the block kernel and 1.90 GHz for the attention kernel. The high case assumes 2.40 GHz for both. The low case assumes 1.90 GHz for both.",
    "The probe does not show which clock the block kernel gets. So 2.40 GHz is an assumption." + ul([
        f"At 1.90 GHz with the same cycle count, the factor of Part A is {f190:.1f} (est.). The clock cost is then {100 * tax['lo']:.1f} % (est.).",
        f"The TTFT fall of Part A is then {fall(parta_190)} (est.). The fall of Part 0 at its working value is {fall(ttft_change('reorder'))} (est.).",
    ]),
    "On delphi-3bda the core ran AMX work at 92 % of its AVX-512 clock " + ref(12) + ". On delphi-3b35 this value is 70 to 89 %.",
]) + "</div>")
s4_read = ul([
    f"With Part 0 alone, TTFT falls by {fall(ttft_change('reorder'))} (est.). The range is {fall(ttft_all('reorder'))}.",
    f"With Part A, TTFT falls by {fall(ttft_change('amx_gdn'))} (est.). The range is {fall(ttft_all('amx_gdn'))}.",
    f"At the working values Part A gives {abs(max(extra_mid)):.0f} to {abs(min(extra_mid)):.0f} percentage points more than Part 0 (est.). "
    "This difference is what AMX itself adds for GDN." + ul([
        f"Part 0 then gives about {rng(part0_of_a)} of the fall that Part A gives (est.).",
        "These values depend on the assumed clock of 2.40 GHz for the block kernel (clock note above).",
        f"In its low case Part A gives {min(a_low_less):.0f} to {max(a_low_less):.0f} percentage points less than Part 0 at its working value (est.). "
        "In that case the block kernel is no faster than the loop of Part 0. The lower core clock then also slows the rest of the pass.",
    ]),
    f"With Part B, TTFT falls by {fall(ttft_change('amx_attn'))} (est.). The range is {fall(ttft_all('amx_attn'))}. The gain grows with the prompt length.",
    f"With Parts A and B together, TTFT falls by {fall(ttft_change('amx_both'))} (est.). The range is {fall(ttft_all('amx_both'))}.",
    f"The decode speed does not change at the working values (est.). The range is {signed(min(tps_change('lo')))} % to {signed(max(tps_change('hi')))} %. All of it comes from Part B.",
    "The decode values are the weakest part of the prediction. They are based on measurements from delphi-3bda and on a clock ratio.",
])
s4_wrong = ("<h4>Part 0</h4>" + ul([
    f"The prediction is wrong if the measured GDN step on a 2.70 GHz thread is above {se['part0_other'][1]:.1f} us, the low case. The estimate from the counts is {se['part0'][0]:.1f} to {se['part0'][1]:.1f} us.",
    f"A step between {se['part0'][1]:.1f} and {se['part0_other'][1]:.1f} us has three possible causes." + ul([
        f"Hypothesis 1 is that the recurrence with the state in L1 takes more than {se['rec0'][1]:.2f} us per value head, the high end of the estimate. Then moving the state costs less today than the estimate assumes. "
        "Test: task 1 times the recurrence on one 32 KiB slice that stays in L1.",
        "Hypothesis 2 is that the slice does not stay in L1. Test: task 1 also times the column-half order on the 128 KiB working copy. The difference between the two timings tests this hypothesis.",
        f"Hypothesis 3 is that the other work of the step takes more than {DN.OTHER_HI} us, the high end of the estimate. "
        "This work is the convolution, the normalization, the rounding to bf16, the copies, the norm and the output gate. "
        "Test: task 2 separately times the copy into the contiguous buffer and back, the normalization and the other per-token work.",
    ]),
]) + "<h4>Part A</h4>" + ul([
    "The prediction is wrong if the measured GDN step of the block kernel is not below the measured GDN step of Part 0. Then Part A adds nothing. "
    f"The estimate is {se['parta'][0]:.1f} to {se['parta_mix'][1]:.1f} us against {se['part0'][0]:.1f} to {se['part0'][1]:.1f} us.",
]) + "<h4>The method</h4>" + ul([
    "The test of the method is Part 0 against the base build. Part 0 uses no AMX. So no core clock changes.",
    "On one serial path the pass wall then falls by the same time as the GDN wall, within the spread of repeated runs. If the pass wall falls by less, the layers do not form one serial path.",
    f"The spread is the largest minus the smallest pass wall of a cell. The 6 runs of section 2 give 0.2 to 0.5 ms with 1 user and 0.3 to 1.7 ms with 8 users {ref(18)}.",
    "Both walls must come from the same kind of run. Either both come from counters of untraced runs, or both come from traced runs.",
    "Part A alone cannot show whether the layers form one serial path. Its lower core clock also slows the rest of the pass (factor table, clock cost row of Part A). "
    "That clock cost must be subtracted from the fall of the GDN wall first.",
]) + "<h4>Part B</h4>" + ul([
    "The test is the A/B run of task 5. It gives the fall of the pass wall and the fall of the attention busy time. "
    "The prediction is wrong if the first fall is smaller than the second by more than the spread of repeated runs.",
    "The hypothesis for this case is that the workers wait for K and V after the faster scoring. A longer join wait gives the same pattern. "
    "The timer of the open point on the wait for K and V separates the two.",
]))
threads_note = ('<div class="note"><b>The same data also show a finding that is not an AMX matter.</b>' + ul([
    "With 8 users the 16 GDN threads each run 8 chains, one after another, while 40 attention workers wait.",
    "Spreading the 128 work items over all 56 threads would cut the GDN wall to about 3/8 of today's value (est.). This estimate comes from the work-item count.",
    f"In prefill with 8 users at prompt 1,024, the saving is about {c8u['prefill']['gdn_ms'] * 5 / 8:.0f} ms of the {c8u['prefill']['t1_ms']:.0f} ms pass (est.).",
    f"In decode for the same cell, the saving is about {c8u['decode']['gdn_ms'] * 5 / 8:.1f} ms of the {c8u['decode']['t1_ms']:.1f} ms step (est.). "
    "The GDN wall behind this value comes from a traced run. So the value can be too high or too low (section 3, limit of the decode numbers).",
    "Spreading the work items needs a scheduling change, not a new kernel. It does not help 1 user.",
]) + "</div>")
s52 = ul([
    f"Today the kernel passes over a 64 KiB matrix twice for each token {ref(3)}. The matrix does not fit the 48 KiB L1 cache. So each of the two passes moves it between L2 and L1.",
    "The new loop order uses one fact: each value column of S is its own recurrence. Column c depends only on the keys, the decay, the beta and column c of the values.",
    "The new order splits each value head into two halves of 64 columns (32 KiB). It runs all tokens of the chain on one half, then on the other half. The half stays in L1 for the whole chain.",
    "Each chain runs in three phases." + ul([
        "Phase 1 runs per token: convolution, normalization, decay and beta. It saves the results in a small buffer.",
        "Phase 2 runs the recurrence over the chain, half by half.",
        "Phase 3 runs per token: norm and output gate.",
    ]),
    f"Each half is stored as one contiguous block of 32 KiB in a buffer of its own. In the layout of today's working copy, too many rows of a half need the same L1 positions (cache sets). The half would then not stay in L1 {ref(18)}.",
    "The bits are unchanged. Every column sees the same operations in the same order.",
    "No timing of this order on delphi-3b35 exists so far.",
    f"On another CPU (AMD Zen 5) a stand-alone copy of this order gave equal bits. It ran {zen_ratio} times faster than today's order {ref(18)}. The low case of Part 0 in section 4 uses this ratio.",
    "Part 0 is in an AMX design for two reasons." + ul([
        f"At the working values it gives about {rng(part0_of_a)} of the fall that Part A is predicted to give (est.). In its low case it gives about {rng(part0_low_of_a)} (est.).",
        "It also builds the chain entry point and the per-token buffers that Part A needs.",
    ]),
])
s53 = ("<h4>The block form and why AMX fits it</h4>" + ul([
    f"The idea is to process a block of {DN.BLOCK} tokens at once. The state is then read twice and written once per block. Today it is read twice and written once per token.",
    "AMX fits the block form. The three large products become matrix times matrix. A tile product then uses all 16 rows.",
    f"The block kernel needs {tc['per_token']:.1f} tile products and about 680 AVX-512 operations per value head per token (est. count). Today's kernel needs about {DN.VEC_OPS:,} AVX-512 operations (est. count).",
    "Three other programs that run this model use the same algebra." + ul([
        "Hugging Face Transformers uses this block form (block size 64) for every call with several tokens.",
        f"vLLM and SGLang include a CPU kernel that is built on the block form. Its matrix products call a library routine. A comment in that kernel says that the routine uses AMX bf16 products {ref(14)}.",
    ]),
    f"The block size is 32 tokens. In the L1 cache model, the tile loads find 87 % of their cache lines in L1 with blocks of 32 tokens (est.). With blocks of 64 tokens the value is 40 % (est.) {ref(18)}.",
]) + "<h4>The FP32 state</h4>" + ul([
    "AMX has no tile product for FP32 inputs. Its floating-point tile products take 16-bit inputs: bf16, and fp16 on this CPU.",
    f"Each FP32 value is split into 3 bf16 pieces. The product is computed once per piece, and the 3 results are added {ref(18)}.",
    "The sum of the pieces is exactly the FP32 value when its size is 2^-103 (about 9.9e-32) or larger. Section 5.4 gives the split rule and what is lost for smaller values.",
]) + "<h4>Two stages in detail</h4>" + ul([
    "Stage 1 takes 16 value columns of S0 (the state at the start of the block) at a time. AVX-512 code splits them into 3 pieces in a 12 KiB buffer that stays in L1. Then 48 tile products run on that buffer.",
    "Stage 4 starts with AVX-512 code. It scales Delta (the 32 correction rows of the block) and splits it into 3 pieces.",
    "Tile product 3 then builds the update in 16 parts. One part has 12 tile products and covers 64 key rows by 16 value columns. "
    "After each part, AVX-512 code writes the decayed start state plus the update for these values (64 FMAs).",
]) + "<h4>The core clock of the block kernel</h4>" + ul([
    "Tile work and AVX-512 work alternate in runs of many lengths. The second table below lists the runs of one value head and one block. The lengths are estimates from the instruction counts, not timings.",
    "At 2.40 GHz the kernel has these turns and runs:" + ul([
        f"Stage 1 has 8 turns of {KR['turn1'][0]:.2f} to {KR['turn1'][1]:.2f} us (est.). The first and the last of these turns are longer for the first value head of a key head. They take {KR['turn1_long'][0]:.1f} to {KR['turn1_long'][1]:.1f} us (est.).",
        f"Stage 3 and the split of Delta are one AVX-512 run of {KR['run3'][0]:.1f} to {KR['run3'][1]:.1f} us with no tile work (est.).",
        f"Stage 4 has 16 turns of {KR['turn4'][0]:.2f} us (est.).",
    ]),
    f"The clock probe covered two turns. The first had 4 tile products with 64 FMAs (35 ns per turn, 1.90 GHz). The second had 4,096 tile products followed by 16,384 FMAs (33 us per turn, 2.40 GHz) {ref(11)}.",
    "Neither probed turn has the mix of this kernel. Insufficient data for the clock of the block kernel. Task 3 of the plan measures it.",
    "If the turns of stage 1 give 1.90 GHz, the alternative first splits the whole state. All tile products of stage 1 then run in one long run. The pieces of one value head are then 96 KiB, which do not fit L1.",
    "If the turns of stage 4 give 1.90 GHz, the alternative first stores all 64 result tiles of tile product 3. The final write is then one run of 1,024 FMAs. The result tiles are then 64 KiB, which do not fit L1.",
]))

page = f"""<title>GDN AMX Design</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&amp;family=Space+Grotesk:wght@500;600&amp;family=JetBrains+Mono:wght@400&amp;display=swap">
<style>{CSS}</style>
<div class="sheet">
<h1>GDN and AMX: design for Qwen3.5 4B</h1>
<p class="meta">2026-11-20. Measured on delphi-3b35 (our test server), on our half of it. The code is tron (the inference program under test) at commit 72e1191804 (open pull request #3696).<br>
Status: baseline, prediction and design. Nothing is built yet.</p>

<div class="short col">
<h2>Short version</h2>
<ul>
<li>In Qwen3.5 4B, 24 of the 32 layers are GDN layers (layers with a fixed-size memory matrix).</li>
<li>Today tron runs no AMX code (Intel's matrix instructions) for this model, we propose three changes, and none is built.</li>
<li>The table below gives each change's estimated effect (est.) on the time to first token, from the baseline measured on delphi-3b35.</li>
</ul>
</div>
<h3>The three changes in one table</h3>
{glance_table()}

<div class="col">
{words_html}
<ul class="toc">
<li><a href="#s1">1. What GDN is</a></li>
<li><a href="#s2">2. Baseline on delphi-3b35</a></li>
<li><a href="#s3">3. Where the time goes</a></li>
<li><a href="#s4">4. Prediction</a></li>
<li><a href="#s5">5. Software design</a></li>
<li><a href="#s6">6. Plan and open points</a></li>
<li><a href="#s7">7. Sources</a></li>
</ul>
</div>

<h2 id="s1">1. What GDN is, compared with llama-3.1-8b</h2>
<div class="col">
{s1_intro}
</div>
{fig_stack}
{fig_flow}
<div class="col">
<h3>The differences that matter for the CPU</h3>
</div>
{differences_table}
<div class="col">
{s1_attn}
</div>
{fig_work}

<h2 id="s2">2. Baseline on delphi-3b35</h2>
<div class="col">
{s2_setup}
</div>
{fig_ttft}
{fig_tps}
{baseline_table()}
<div class="col">
{s2_notes}
</div>

<h2 id="s3">3. Attention metrics: where the time goes</h2>
<div class="col">
{s3_how}
</div>
{fig_split_pf}
{split_table("prefill")}
{fig_split_dec}
{split_table("decode")}
<div class="col">
<h3>What the numbers say</h3>
{s3_say}
</div>
{fig_lanes}

<h2 id="s4">4. Prediction, made before any test of the solution on delphi-3b35</h2>
<div class="col">
<h3>Method</h3>
{s4_method}
<pre><code>pass_new = pass - GDN_wall x (1 - 1/s_gdn)
                - attention_scaled x (1 - 1/s_attn)
                + rest x clock_cost
                + attention_other x clock_cost_attention
attention_scaled = full-page time        (prefill pass)
attention_scaled = attention busy time   (decode step)
attention_other  = attention busy time - full-page time - join wait
                   (prefill pass, Part B only)
TTFT_new = TTFT - passes x (pass - pass_new)
ms_per_token_new = ms_per_token - (step - step_new)</code></pre>
{s4_inputs}
</div>
{table(["Factor (old time / new time)", "Low (est.)", "Working value (est.)", "High (est.)", "Basis"], factor_rows, num_cols=(1, 2, 3), kind="prose")}
<div class="col">
{clock_note}
</div>
{fig_pred}
{fig_pred_tps}
<div class="col">
<p>Each table cell gives the working value, its change against today, and the range between the low and high cases.</p>
</div>
{pred_table()}
<div class="col">
<h3>How to read the prediction</h3>
{s4_read}
<h3>What would prove the prediction wrong</h3>
{s4_wrong}
{threads_note}
</div>

<h2 id="s5">5. Software design</h2>
<div class="col">
<h3>5.1 What AMX can and cannot do here</h3>
</div>
{can_table}
{fig_path}
<div class="col">
<h3>5.2 Part 0: a chain path that keeps the state in L1 (no AMX, same bits)</h3>
{s52}
<h3>5.3 Part A: the AMX block kernel</h3>
{s53}
</div>
{fig_block}
{DN.block_table(table)}
<div class="col">
<p>{DN.RUNS_LEAD}</p>
</div>
{DN.runs_table(table)}
<div class="col">
{ul(DN.runs_notes())}
</div>
{fig_kernel}
<div class="col">
<h3>5.4 Numerics: what changes and what the contract should say</h3>
<ul>
{DN.NUMERICS_HTML}
</ul>
<h3>5.5 Part B: attention kernels for 256-wide heads</h3>
<ul>
{DN.ATTN_HTML}
</ul>
<h3>5.6 Code structure</h3>
</div>
{table(["Piece", "Where", "What"], DN.CODE_ROWS, kind="prose")}
<div class="col">
<h3>5.7 What stays outside this design</h3>
<ul>
{DN.OUTSIDE_HTML}
</ul>
</div>

<h2 id="s6">6. Plan and open points</h2>
{table(["Task", "Work", "Measurement that closes it", "Pass rule"], DN.PLAN_ROWS, kind="prose")}
<div class="col">
<h3>Which runs tasks 2, 5 and 6 compare</h3>
<ul>
{DN.COMPARE_HTML}
</ul>
</div>
{table(["Comparison", "Task", "Run 1", "Run 2", "The two runs differ in"], DN.COMPARE_ROWS, kind="prose")}
<div class="col">
<p>Predicted TTFT fall of the two A/B runs, with the working values of section 4 in both runs (est.).</p>
</div>
{ab_table()}
<div class="col">
{ab_notes}
</div>
<div class="col">
<h3>Open points</h3>
<ul>
{DN.OPEN_HTML}
</ul>
</div>

<h2 id="s7">7. Sources</h2>
<div class="col">
{refs_html}
</div>
</div>
"""

# sentence-end references written as [RefN] inside design_numbers text blocks
page = re.sub(r'(?<!<span class="ref">)\[Ref(\d+)\]', lambda m: f'<span class="ref">[Ref{m.group(1)}]</span>', page)


def nowrap(html_text):
    """A browser may break a line after the hyphen of 9.2e-41, 2^-103 or AVX-512. Wrap these tokens in a no-wrap span.
    Only text nodes outside svg, style, pre, code and title elements are touched."""
    token = re.compile(r"\b\d+(?:\.\d+)?e-\d+\b|\b2\^-?\d+(?: - 2\^\d+)?|\bAVX-512\b")
    out, skip = [], 0
    for part in re.split(r"(<svg\b.*?</svg>|<style\b.*?</style>|<pre\b.*?</pre>|<code\b.*?</code>|<title\b.*?</title>|<[^>]+>)", html_text, flags=re.S):
        out.append(part if part.startswith("<") else token.sub(lambda m: f'<span class="nw">{m.group(0)}</span>', part))
    return "".join(out)


page = nowrap(page)
page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
assert_ascii(page)
open(OUT, "w").write(page)
print("wrote", OUT, len(page), "bytes")
