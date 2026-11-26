#!/usr/bin/env python3
"""R6: what the saved data can and cannot say about the GDN share of a decode step.

The page divides a GDN wall that was measured in a TRACED run by a step wall that was measured in the
UNTRACED runs. This script puts the two kinds of run side by side, per cell, for the decode steps and for
the prefill passes.

It computes, from saved files only (no new measurement):
  1. the three differences between the two kinds of run: number of passes that each mean covers, and the
     wall of a pass with and without the trace;
  2. the attention busy time per pass in both kinds of run. It is the only part of a pass that has a timer in
     both. It shows what the trace does to a part that both runs time;
  3. the GDN share that the page prints (traced GDN wall / untraced pass wall), and the share inside the traced run;
  4. the only limit on the untraced GDN wall that the untraced runs give alone: pass wall minus attention busy time;
  4b. the extra wall time of a traced pass that is not attention busy time. No saved data say how much of it sits in
     GDN and how much in the rest;
  5. a CONDITIONAL range of the untraced GDN wall. It holds only if the trace lengthens every part of a pass or
     leaves it unchanged, and if the mean GDN wall does not depend on which passes the mean covers.
     Neither condition is tested by any saved data. Then:
        GDN_traced - (pass_traced - pass_untraced) + (attention_traced - attention_untraced) <= GDN_untraced <= GDN_traced
  6. the scheduling estimate of section 4 (5/8 of the GDN wall, 8 users, prompt 1,024) with the same conditional range.

Inputs (read-only):
  /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/collected.json   (attention statistics per run, trace summaries)
  /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json (the per-cell values that the page prints)
Output: text on stdout (saved beside this script as r6_traced_vs_untraced.out). Pure python, deterministic.
"""
import json

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
col = json.load(open(RES + "/collected.json"))
pred = json.load(open(RES + "/predictions.json"))

CLS = {"decode": "decode_like", "prefill": "prompt_or_mixed"}


def median(v):
    v = sorted(v)
    n = len(v)
    return (v[(n - 1) // 2] + v[n // 2]) / 2.0


def untraced(cell, cls, key):
    """All untraced runs of the cell (both arms): the list of per-run values."""
    vals = []
    for arm in ("on", "off"):
        if arm in col["cells"][cell]:
            vals.extend(col["cells"][cell][arm][cls][key]["values"])
    return vals


order = sorted(pred["cells"], key=lambda c: (pred["cells"][c]["users"], pred["cells"][c]["prompt"]))
rows = {}
for kind in ("decode", "prefill"):
    cls = CLS[kind]
    print(f"==== {kind}: one {'decode step' if kind == 'decode' else 'prefill pass'} ====")
    print("U = untraced runs (median of 6 runs, attention statistics). S = the traced run, attention statistics "
          "(every pass). T = the traced run, trace events (first pass left out).")
    print(f"{'users':>5} {'prompt':>6} | {'U passes':>8} {'U wall ms':>9} {'U attn ms':>9} | {'S passes':>8} {'S wall ms':>9} {'S attn ms':>9} | "
          f"{'T passes':>8} {'T wall ms':>9} {'T GDN ms':>8} | {'wall T/U':>8} {'attn S/U':>8}")
    for c in order:
        p = pred["cells"][c]
        k = p[kind]
        tname = "t-" + c.split("tp4-")[1]
        tr = col["traces"][tname]["kinds"][kind]
        srun = col["runs"]["trace-" + tname]["derived"][cls]
        u_fw = sorted(set(int(x) for x in untraced(c, cls, "forwards")))
        u_wall = median(untraced(c, cls, "forward_wall_ms"))
        n_w = median(untraced(c, cls, "attn_workers"))
        u_attn = median(untraced(c, cls, "attn_busy_cpu_ms_per_forward")) / n_w
        s_attn = srun["attn_busy_cpu_ms_per_forward"] / srun["attn_workers"]
        t_wall, t_gdn = tr["mean_pass_ms"], tr["gdn"]["wall_span_ms_per_pass"]
        # the page's own values must be the ones recomputed here
        assert abs(u_wall - k["t1_ms"]) < 1e-9 and abs(u_attn - k["attn_ms"]) < 1e-9 and abs(t_gdn - k["gdn_ms"]) < 1e-12, c
        assert abs(t_wall - k["trace_pass_ms"]) < 1e-12, c
        rows[(kind, c)] = dict(users=p["users"], prompt=p["prompt"], u_wall=u_wall, u_attn=u_attn, s_wall=srun["forward_wall_ms"], s_attn=s_attn,
                               t_wall=t_wall, t_gdn=t_gdn, t_share=tr["gdn"]["wall_span_pct_of_pass"])
        print(f"{p['users']:5d} {p['prompt']:6d} | {'/'.join(str(x) for x in u_fw):>8} {u_wall:9.3f} {u_attn:9.3f} | {srun['forwards']:8d} {srun['forward_wall_ms']:9.3f} {s_attn:9.3f} | "
              f"{tr['passes_used']:8d} {t_wall:9.3f} {t_gdn:8.3f} | {100 * (t_wall / u_wall - 1):+7.1f}% {100 * (s_attn / u_attn - 1):+7.1f}%")
    print()
    print("GDN share of the pass, and what the untraced runs alone allow.")
    print("page share = T GDN / U wall. traced share = T GDN / T wall. U limit = U wall - U attn (the untraced runs have no GDN timer).")
    print("conditional range: only if the trace lengthens every part of a pass or leaves it unchanged (NOT tested).")
    print(f"{'users':>5} {'prompt':>6} | {'page share':>10} {'traced share':>12} | {'U limit ms':>10} {'U limit %':>9} | "
          f"{'cond. low ms':>12} {'cond. high ms':>13} {'cond. low %':>11} {'cond. high %':>12}")
    for c in order:
        r = rows[(kind, c)]
        low = max(0.0, r["t_gdn"] - (r["t_wall"] - r["u_wall"]) + (r["s_attn"] - r["u_attn"]))
        r["cond_low"] = low
        r["extra"] = (r["t_wall"] - r["u_wall"]) - (r["s_attn"] - r["u_attn"])
        lim = r["u_wall"] - r["u_attn"]
        print(f"{r['users']:5d} {r['prompt']:6d} | {100 * r['t_gdn'] / r['u_wall']:9.1f}% {r['t_share']:11.1f}% | {lim:10.3f} {100 * lim / r['u_wall']:8.1f}% | "
              f"{low:12.3f} {r['t_gdn']:13.3f} {100 * low / r['u_wall']:10.1f}% {100 * r['t_gdn'] / r['u_wall']:11.1f}%")
    print()
    print("Extra time of a traced pass, and where it can sit.")
    print("extra wall = T wall - U wall. extra attn = S attn - U attn. not located = extra wall - extra attn: it sits in GDN or in the rest.")
    print(f"{'users':>5} {'prompt':>6} | {'extra wall ms':>13} {'extra attn ms':>13} {'not located ms':>14} | {'T GDN ms':>8} {'not located / T GDN':>19}")
    for c in order:
        r = rows[(kind, c)]
        print(f"{r['users']:5d} {r['prompt']:6d} | {r['t_wall'] - r['u_wall']:13.3f} {r['s_attn'] - r['u_attn']:13.3f} {r['extra']:14.3f} | "
              f"{r['t_gdn']:8.3f} {100 * r['extra'] / r['t_gdn']:18.0f}%")
    print()

print("==== ranges for the text ====")
for kind in ("decode", "prefill"):
    longer = [100 * (rows[(kind, c)]["t_wall"] / rows[(kind, c)]["u_wall"] - 1) for c in order]
    attn = [100 * (rows[(kind, c)]["s_attn"] / rows[(kind, c)]["u_attn"] - 1) for c in order]
    print(f"{kind}: a traced pass is {min(longer):.1f} to {max(longer):.1f} % longer than an untraced one (trace events against attention statistics).")
    print(f"{kind}: the attention busy time per pass is {min(attn):.0f} to {max(attn):.0f} % longer in the traced run (same counter in both kinds of run).")
for label, pick in (("1 user", 1), ("8 users", 8)):
    sh = [100 * rows[("decode", c)]["t_gdn"] / rows[("decode", c)]["u_wall"] for c in order if rows[("decode", c)]["users"] == pick]
    tsh = [rows[("decode", c)]["t_share"] for c in order if rows[("decode", c)]["users"] == pick]
    print(f"decode, {label}: page share {min(sh):.0f} to {max(sh):.0f} % (traced GDN wall / untraced step). Inside the traced run: {min(tsh):.0f} to {max(tsh):.0f} %.")
alltr = [rows[("decode", c)]["t_share"] for c in order]
print(f"decode, all cells: share inside the traced run {min(alltr):.0f} to {max(alltr):.0f} %.")

c8 = [c for c in order if rows[("decode", c)]["users"] == 8 and rows[("decode", c)]["prompt"] == 1024][0]
r = rows[("decode", c8)]
print()
print("==== scheduling estimate of section 4 (8 users, prompt 1,024, decode): 5/8 of the GDN wall ====")
print(f"page value: 5/8 x {r['t_gdn']:.3f} ms = {r['t_gdn'] * 5 / 8:.2f} ms of the {r['u_wall']:.2f} ms step (traced GDN wall, untraced step).")
print(f"conditional range of the same value (assumption above, NOT tested): {r['cond_low'] * 5 / 8:.2f} to {r['t_gdn'] * 5 / 8:.2f} ms.")
print("Without that assumption the saved data give no limit below 5/8 x (U wall - U attn) = "
      f"{(r['u_wall'] - r['u_attn']) * 5 / 8:.2f} ms.")
