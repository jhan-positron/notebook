#!/usr/bin/env python3
"""Fill the report template with numbers computed from the result files.

usage: fill_report.py DATA_DIR TEMPLATE_HTML REPORT_HTML
The template is report-template.html in the data folder.
"""
import html
import json
import os
import sys

D, T, H = sys.argv[1], sys.argv[2], sys.argv[3]


def load(name):
    return json.load(open(os.path.join(D, name)))


ab = {r["phase"]: r for r in load("ab.json")}
w = {n: load("width-n%d.json" % n)[0] for n in (4, 5, 6, 7)}
fg = {r["phase"]: r for r in load("final-guard.json")}
ad = {r["phase"]: r for r in load("after-detach.json")}

# Probe speed at rest: all phases with no test load and no other batch.
rest = [ab["idle-before"], ab["idle-between"], ab["idle-after"],
        ad["idle"], ad["idle-end"]]
rest_rate = sum(r["probe_rounds"] for r in rest) / sum(r["wall_s"] for r in rest)


def speed(r):
    return 100 * r["probe_rounds"] / r["wall_s"] / rest_rate


def agg(rs):
    """Totals over runs: stall time over test time, rounds over test time."""
    wall = sum(r["wall_s"] for r in rs)
    return {
        "stall": sum(r["full_stall_pct"] * r["wall_s"] for r in rs) / wall,
        "speed": 100 * sum(r["probe_rounds"] for r in rs) / wall / rest_rate,
        "wall": wall,
    }


g1 = [ab["A-unpinned"]]
g2 = [ab["B-pinned"], ab["C-pinned-long"], w[6], fg["final-pinned"]]
g3 = [ad["pinned-36x30s"], ad["pinned-36x30s-b"]]
a1, a2, a3 = agg(g1), agg(g2), agg(g3)
print("stall %.2f %.2f %.2f | speed %.1f %.1f %.1f | seconds %.1f %.1f %.1f" % (
    a1["stall"], a2["stall"], a3["stall"], a1["speed"], a2["speed"],
    a3["speed"], a1["wall"], a2["wall"], a3["wall"]))
print("factors %.1f %.1f" % (a1["stall"] / a2["stall"], a2["stall"] / a3["stall"]))


def detail(rs, fmt):
    return ["%s, %.0f s: %s" % (r["started"], r["wall_s"], fmt(r)) for r in rs]


def st(r):
    return "%.2f%% stalled" % r["full_stall_pct"]


def spd(r):
    return "%.1f%% of the speed at rest" % speed(r)


conds = [
    {"name": "No pin", "runs": "1 run of 4 s",
     "stall": a1["stall"], "stallLabel": "%.1f%%" % a1["stall"],
     "stallRange": "", "stallNote": "",
     "speed": a1["speed"], "speedLabel": "%.0f%%" % a1["speed"],
     "speedRange": "",
     "stallDetail": detail(g1, st), "speedDetail": detail(g1, spd)},
    {"name": "Pinned to 6 CPUs", "runs": "4 runs, %.0f s in total" % a2["wall"],
     "stall": a2["stall"], "stallLabel": "%.1f%%" % a2["stall"],
     "stallRange": "(%.1f to %.1f)" % (min(r["full_stall_pct"] for r in g2),
                                       max(r["full_stall_pct"] for r in g2)),
     "stallNote": "the pin: %.0f times less stall" % (a1["stall"] / a2["stall"]),
     "speed": a2["speed"], "speedLabel": "%.0f%%" % a2["speed"],
     "speedRange": "(%.0f to %.0f)" % (min(speed(r) for r in g2),
                                       max(speed(r) for r in g2)),
     "stallDetail": detail(g2, st), "speedDetail": detail(g2, spd)},
    {"name": "Pinned, tmux clients detached", "runs": "2 runs of 30 s",
     "stall": a3["stall"], "stallLabel": "%.2f%%" % a3["stall"],
     "stallRange": "(%.2f, %.2f)" % tuple(sorted(r["full_stall_pct"] for r in g3)),
     "stallNote": "tmux cleanup: %.0f times less again" % (a2["stall"] / a3["stall"]),
     "speed": a3["speed"], "speedLabel": "%.0f%%" % a3["speed"],
     "speedRange": "(%.1f, %.1f)" % tuple(sorted(speed(r) for r in g3)),
     "stallDetail": detail(g3, st), "speedDetail": detail(g3, spd)},
]


def strip(name, limit_s):
    """[seconds since start, CPUs in use] per 0.1 s window."""
    t, out = 0, []
    for wall, used, _ in load(name)["intervals"]:
        t += wall
        if t / 1000 > limit_s + 1e-9:
            break
        out.append([round(t / 1000, 2), round(used / wall, 2)])
    return out


def rest_stats(name):
    iv = load(name)["intervals"]
    wall = sum(i[0] for i in iv)
    cpus = [i[1] / i[0] for i in iv]
    return {"wall": wall / 1000, "mean": sum(i[1] for i in iv) / wall,
            "over": sum(1 for c in cpus if c > 8), "n": len(iv),
            "max": max(cpus), "stall": 100 * sum(i[2] for i in iv) / wall}


ib = rest_stats("bursts-idle.json")
ia = rest_stats("bursts-idle-after-detach.json")
print("before", ib)
print("after", ia)

data = {"conds": conds, "idleRate": "%.0f" % rest_rate,
        "stripBefore": strip("bursts-idle.json", 60),
        "stripAfter": strip("bursts-idle-after-detach.json", 60),
        "afterMax": "%.1f" % ia["max"]}


def row(label, r):
    return ("  <tr><td>%s</td><td>%s</td><td class=\"num\">%.0f s</td>"
            "<td class=\"num\">%.2f</td><td class=\"num\">%.2f%%</td>"
            "<td class=\"num\">%.1f%%</td><td class=\"num\">%.2f ms</td>"
            "<td class=\"num\">%.1f ms</td><td class=\"num\">%d of %s</td></tr>") % (
        html.escape(label), r["started"], r["wall_s"], r["cpus_used"],
        r["full_stall_pct"], speed(r), r["probe_p99_ms"], r["probe_max_ms"],
        r["probe_rounds_over_20ms"], format(r["probe_rounds"], ","))


def grp(title):
    return "  <tr class=\"grp\"><td colspan=\"9\">%s</td></tr>" % html.escape(title)


run_rows = [
    grp("No test load"),
    row("at rest", ab["idle-before"]),
    row("at rest", ab["idle-between"]),
    row("at rest", ad["idle"]),
    grp("36 busy processes, no pin"),
    row("run 1", ab["A-unpinned"]),
    grp("36 busy processes, pinned to 6 CPUs, tmux clients attached"),
    row("run 1", ab["B-pinned"]),
    row("run 2", ab["C-pinned-long"]),
    row("run 3", w[6]),
    row("run 4, with the real batch of the other session", fg["final-pinned"]),
    grp("Real batch of the other session only, pinned, tmux clients attached"),
    row("8 workers of r3_split_facts.py", fg["idle"]),
    grp("36 busy processes, pinned to 6 CPUs, tmux clients detached"),
    row("run 1", ad["pinned-36x30s"]),
    row("run 2", ad["pinned-36x30s-b"]),
]
width_rows = [
    "  <tr><td class=\"num\">%d</td><td class=\"num\">%.1f%%</td>"
    "<td class=\"num\">%.2f</td><td class=\"num\">%.2f%%</td></tr>" % (
        n, 100 * n / 8, w[n]["cpus_used"], w[n]["full_stall_pct"])
    for n in (4, 5, 6, 7)]
rest_rows = [
    "  <tr><td>%s</td><td class=\"num\">%.2f</td>"
    "<td class=\"num\">%d of %d (%.1f%%)</td><td class=\"num\">%.1f CPUs</td>"
    "<td class=\"num\">%.2f%%</td></tr>" % (
        label, s["mean"], s["over"], s["n"], 100 * s["over"] / s["n"],
        s["max"], s["stall"])
    for label, s in (
        ("Before the detach, from 20:18:59, %.0f s" % ib["wall"], ib),
        ("After the detach, from 20:44:48, %.0f s" % ia["wall"], ia))]

page = open(T).read()
for key, value in (("__DATA_JSON__", json.dumps(data)),
                   ("__RUN_ROWS__", "\n".join(run_rows)),
                   ("__WIDTH_ROWS__", "\n".join(width_rows)),
                   ("__IDLE_ROWS__", "\n".join(rest_rows)),
                   ("__IDLE_RATE__", "%.0f" % rest_rate),
                   ("__AFTER_MAX__", "%.1f" % ia["max"]),
                   ("__BEFORE_OVER__", "%d" % sum(
                       1 for p in data["stripBefore"] if p[1] > 8))):
    assert key in page, key
    page = page.replace(key, value)
open(H, "w").write(page)
print("written", len(page), "bytes")
