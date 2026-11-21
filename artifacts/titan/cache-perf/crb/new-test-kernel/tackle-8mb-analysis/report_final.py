#!/usr/bin/env python3
"""report_final.py - the final HTML report of the tackle-8mb investigation.

Reads final8.json (written by final8.py) and writes one self-contained HTML page:
  report_final.py [--json final8.json] [--results DIR] [--decisions FILE] [-o tackle-8mb-report.html]

Every number of the page comes from final8.json, except two figures that need raw rows which final8.json
does not hold: the 60 s traces of step S4 (W rows of S4.csv) and the repetition rates of step H2 (H2.csv).
A step or a session that final8.json does not hold is printed as "session 2 missing". Verdict texts are
the strings of final8.json (claims, rule results). Nothing here decides a rule.

Standard library only. Charts are inline SVG. Single light theme.

Words used here
  cell      the processes of one step, kernel, size, CPU and session.
  V cell    a table cell that prints one number of final8.json with a fixed count of decimals.
  calc cell a table cell that this script computes from numbers of final8.json. It carries the formula
            name (data-calc) and the arguments (data-args), so test_report_final.py can recompute it.
"""
import argparse
import datetime
import html
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
N_DIR = os.path.dirname(HERE)
CRB_DIR = os.path.dirname(N_DIR)
X_DIR = os.path.join(CRB_DIR, "tmp", "agent-scratch", "bwx8-2026-11-14")
MISSING = "session 2 missing"
CLOCK_GHZ = 2.8          # core clock of CRB, GHz (machine description)
SESSIONS = (1, 2)
CPUS = (2, 41)
SESSION1_ONLY = ("XEV", "YA", "ZA")

# colours: slots 1 and 2 of the documented colour-blind-safe categorical palette of the dataviz skill
C_NEW = "#2a78d6"     # the new load-only loops
C_OLD = "#eb6834"     # old read
C_PRED = "#898781"    # predictions (hollow or grey)
C_INK = "#0b0b0b"
C_INK2 = "#52514e"
C_GRID = "#e1e0d9"
C_AXIS = "#c3c2b7"
C_SURF = "#fcfcfb"
C_BAND = "#e6e5df"
SHAPE = {1: "o", 2: "d"}

# formulas of the calc cells; test_report_final.py holds its own copy and recomputes every calc cell
CALC = {
    "gain": lambda a, b: 100.0 * (a / b - 1.0),                 # gain of rate a over rate b, percent
    "diff": lambda a, b: a - b,
    "cyc": lambda rate: CLOCK_GHZ * 64.0 / rate,                # cycles per 64 B line from a rate in GB/s
    "line": lambda i, s, r: i + s * r,                          # fitted line at r
    "linegap": lambda old, i, s, r: old - (i + s * r),
    "linegain": lambda old, i, s, r: 100.0 * (old / (i + s * r) - 1.0),
    "pgain": lambda s, c: 100.0 * (s / min(c, s) - 1.0),        # gain of asmread (rate s) over min(C_k, s)
    "share": lambda g1, gp, gm: 100.0 * (g1 - gp) / (g1 - gm),  # share of the fall of the gain
}


def esc(s):
    return html.escape(str(s), quote=True)


def fnum(x, nd=2):
    return "NA" if x is None else "%.*f" % (nd, x)


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


# ------------------------------------------------------------------------------------------- references
class Refs:
    def __init__(self):
        self.order = []
        self.text = {}

    def define(self, key, text):
        self.text[key] = text

    def __call__(self, *keys):
        out = []
        for k in keys:
            if k not in self.text:
                raise KeyError(k)
            if k not in self.order:
                self.order.append(k)
            out.append("[Ref%d]" % (self.order.index(k) + 1))
        return " ".join(out)

    def html(self):
        return "<ul class='refs'>" + "".join(
            "<li>[Ref%d] %s</li>" % (i + 1, self.text[k]) for i, k in enumerate(self.order)) + "</ul>"


# ------------------------------------------------------------------------------------------- table cells
def TH(s):
    return "<th scope='row'>%s</th>" % esc(s)


def V(x, nd=2):
    """one number of final8.json"""
    if x is None:
        return "<td class='na'>NA</td>"
    return "<td class='num'>%s</td>" % fnum(x, nd)


def VL(xs, nd=2):
    """a list of numbers of final8.json"""
    if not xs:
        return "<td class='na'>-</td>"
    return "<td class='num list'>%s</td>" % " ".join(fnum(x, nd) for x in xs)


def CC(kind, args, nd=2, est=False):
    """calc cell: computed here from numbers of final8.json"""
    if any(a is None for a in args):
        return "<td class='na'>NA</td>"
    val = CALC[kind](*args)
    return "<td class='num calc' data-calc='%s' data-args='%s'>%s%s</td>" % (
        kind, ",".join(repr(float(a)) for a in args), fnum(val, nd), " est." if est else "")


def TX(s, cls="txt"):
    return "<td class='%s'>%s</td>" % (cls, esc(s))


def MISS(colspan=1):
    return "<td class='miss' colspan='%d'>%s</td>" % (colspan, MISSING)


def table(headers, rows, caption=None, note=None, cls=""):
    h = "<div class='tbl'><table%s>" % ((" class='%s'" % cls) if cls else "")
    if caption:
        h += "<caption>%s</caption>" % caption
    h += "<thead><tr>" + "".join("<th scope='col'>%s</th>" % x for x in headers) + "</tr></thead><tbody>"
    for r in rows:
        h += "<tr>" + "".join(r) + "</tr>"
    h += "</tbody></table></div>"
    if note:
        h += "<p class='note'>%s</p>" % note
    return h


# ------------------------------------------------------------------------------------------- SVG plots
def text_w(t, fs):
    return 0.62 * fs * len(t)


def hit(a, b, pad=1.0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


class Plot:
    """one plot frame with its marks and labels, in the pixel units of a 400 wide SVG"""

    def __init__(self, xlim, ylim, W=400, H=280, ml=48, mr=14, mt=36, mb=44, xlog=False):
        self.W, self.H = W, H
        self.xlim, self.ylim, self.xlog = xlim, ylim, xlog
        self.fx0, self.fy0, self.fx1, self.fy1 = ml, mt, W - mr, H - mb
        self.under, self.marks, self.over = [], [], []
        self.obst = []
        self.pending = []
        self.dropped = 0
        self.dropped_texts = []

    # scales
    def X(self, v):
        a, b = self.xlim
        t = (math.log(v) - math.log(a)) / (math.log(b) - math.log(a)) if self.xlog else (v - a) / (b - a)
        return self.fx0 + t * (self.fx1 - self.fx0)

    def Y(self, v):
        a, b = self.ylim
        return self.fy1 - (v - a) / (b - a) * (self.fy1 - self.fy0)

    # chrome
    def frame(self):
        self.under.insert(0, "<rect class='frame' x='%.1f' y='%.1f' width='%.1f' height='%.1f'/>" % (
            self.fx0, self.fy0, self.fx1 - self.fx0, self.fy1 - self.fy0))

    def raw_text(self, x, y, t, anchor="start", fs=11, cls="", obstacle=True):
        w = text_w(t, fs)
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        if obstacle:
            self.obst.append((x0, y - 0.85 * fs, x0 + w, y + 0.25 * fs))
        self.over.append("<text x='%.1f' y='%.1f' text-anchor='%s' font-size='%s'%s>%s</text>" % (
            x, y, anchor, fs, (" class='%s'" % cls) if cls else "", esc(t)))

    def title(self, t, sub=None):
        self.raw_text(2, 13, t, fs=12, cls="ttl", obstacle=False)
        if sub:
            self.raw_text(2, self.fy0 - 7, sub, fs=11, cls="ax", obstacle=False)

    def xticks(self, ticks, labels=None, title=None, grid=False):
        for i, v in enumerate(ticks):
            x = self.X(v)
            if grid:
                self.under.append("<line class='grid' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>" % (
                    x, self.fy0, x, self.fy1))
            self.under.append("<line class='tick' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>" % (
                x, self.fy1, x, self.fy1 + 4))
            self.raw_text(x, self.fy1 + 16, labels[i] if labels else ("%g" % v), "middle", 11, "ax", False)
        if title:
            self.raw_text((self.fx0 + self.fx1) / 2, self.fy1 + 33, title, "middle", 11, "ax", False)

    def yticks(self, ticks, fmt="%g", grid=True):
        for v in ticks:
            y = self.Y(v)
            if grid:
                self.under.append("<line class='grid' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>" % (
                    self.fx0, y, self.fx1, y))
            self.raw_text(self.fx0 - 6, y + 4, fmt % v, "end", 11, "ax", False)

    # marks (pixel coordinates)
    def dot(self, px, py, color, shape="o", hollow=False, r=4.5, tip="", opacity=1.0):
        if hollow:
            style = "fill='%s' stroke='%s' stroke-width='1.6'" % (C_SURF, color)
        else:
            style = "fill='%s' stroke='%s' stroke-width='1.2'" % (color, C_SURF)
        if opacity < 1:
            style += " opacity='%.2f'" % opacity
        t = ("<title>%s</title>" % esc(tip)) if tip else ""
        if shape == "d":
            q = r * 1.3
            el = "<polygon points='%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f' %s>%s</polygon>" % (
                px, py - q, px + q, py, px, py + q, px - q, py, style, t)
        elif shape == "s":
            el = "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' %s>%s</rect>" % (
                px - r, py - r, 2 * r, 2 * r, style, t)
        else:
            el = "<circle cx='%.1f' cy='%.1f' r='%.1f' %s>%s</circle>" % (px, py, r, style, t)
        self.marks.append(el)
        self.obst.append((px - r - 1, py - r - 1, px + r + 1, py + r + 1))

    def path(self, pts, color, width=1.5, dash=None, opacity=1.0, layer="under"):
        if len(pts) < 2:
            return
        d = "M" + " L".join("%.1f,%.1f" % p for p in pts)
        el = "<path d='%s' fill='none' stroke='%s' stroke-width='%s'%s%s/>" % (
            d, color, width, (" stroke-dasharray='%s'" % dash) if dash else "",
            (" opacity='%.2f'" % opacity) if opacity < 1 else "")
        (self.under if layer == "under" else self.marks).append(el)

    def area(self, pts, color, opacity=1.0):
        d = "M" + " L".join("%.1f,%.1f" % p for p in pts) + " Z"
        self.under.append("<path d='%s' fill='%s' stroke='none' opacity='%.2f'/>" % (d, color, opacity))

    def bar(self, px0, py, px1, color, thick=10, tip=""):
        t = ("<title>%s</title>" % esc(tip)) if tip else ""
        w = max(px1 - px0, 1.5)
        self.marks.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%d' rx='2' fill='%s'>%s</rect>" % (
            px0, py - thick / 2.0, w, thick, color, t))
        self.obst.append((px0, py - thick / 2.0, px0 + w, py + thick / 2.0))

    # labels with a simple search for a free place
    def label(self, px, py, t, order="R A B L AR BR AL BL", fs=11, d=7, cls="lab"):
        self.pending.append((px, py, t, order.split(), fs, d, cls))

    def _place(self):
        for px, py, t, order, fs, d, cls in self.pending:
            w = text_w(t, fs)
            done = False
            for pos, d in [(q, d0) for d0 in (d, d + 5, d + 11) for q in order]:
                if pos == "R":
                    x0, yb = px + d, py + 4
                elif pos == "L":
                    x0, yb = px - d - w, py + 4
                elif pos == "A":
                    x0, yb = px - w / 2, py - d - 2
                elif pos == "B":
                    x0, yb = px - w / 2, py + d + 9
                elif pos == "AR":
                    x0, yb = px + d - 2, py - d + 1
                elif pos == "BR":
                    x0, yb = px + d - 2, py + d + 7
                elif pos == "AL":
                    x0, yb = px - d + 2 - w, py - d + 1
                else:
                    x0, yb = px - d + 2 - w, py + d + 7
                box = (x0, yb - 0.85 * fs, x0 + w, yb + 0.25 * fs)
                if box[0] < self.fx0 + 3 or box[2] > self.fx1 - 3 or box[1] < self.fy0 + 3 or box[3] > self.fy1 - 3:
                    continue
                if any(hit(box, o) for o in self.obst):
                    continue
                self.obst.append(box)
                self.over.append("<text x='%.1f' y='%.1f' font-size='%s' class='%s'>%s</text>" % (
                    x0, yb, fs, cls, esc(t)))
                done = True
                break
            if not done:
                self.dropped += 1
                self.dropped_texts.append(t)
        self.pending = []

    def body(self):
        self._place()
        return "".join(self.under) + "".join(self.marks) + "".join(self.over)


def svg(bodies, W, H, aria):
    return ("<svg class='chart' viewBox='0 0 %d %d' role='img' aria-label='%s'>%s</svg>" % (
        W, H, esc(aria), "".join(bodies)))


def panels(svgs):
    return "<div class='panels'>" + "".join("<div class='panel'>%s</div>" % s for s in svgs) + "</div>"


def sw(color, shape="o", hollow=False):
    p = Plot((0, 1), (0, 1), W=16, H=14, ml=0, mr=0, mt=0, mb=0)
    p.dot(8, 7, color, shape, hollow, r=4.5)
    return "<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'>%s</svg>" % "".join(p.marks)


def legend(items):
    return "<div class='legend'>" + "".join("<span>%s %s</span>" % (s, esc(t)) for s, t in items) + "</div>"


def session_legend():
    return [(sw(C_INK2, "o"), "session 1"), (sw(C_INK2, "d"), "session 2")]


def figure(title, leg, body, takeaway, extra=""):
    return ("<figure><div class='figtitle'>%s</div>%s%s<figcaption><b>Takeaway:</b> %s</figcaption>%s</figure>" % (
        title, legend(leg) if leg else "", body, takeaway, extra))


def spread_labels(items, lo, hi, gap=12.5):
    """items: [(y, payload)] -> [(y_adjusted, payload)], at least `gap` apart, inside lo..hi"""
    items = sorted(items, key=lambda t: t[0])
    ys = [t[0] for t in items]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < gap:
            ys[i] = ys[i - 1] + gap
    over = (ys[-1] - hi) if ys else 0
    if over > 0:
        ys = [y - over for y in ys]
        for i in range(len(ys) - 2, -1, -1):
            if ys[i + 1] - ys[i] < gap:
                ys[i] = ys[i + 1] - gap
    return [(max(y, lo), items[i][1]) for i, y in enumerate(ys)]


# ------------------------------------------------------------------------------------------- the report
class Report:
    def __init__(self, J, results, decisions_path, date):
        self.J = J
        self.results = results
        self.decisions_path = decisions_path
        self.date = date
        self.R = Refs()
        self.notes = []          # things the generator could not draw
        self.label_drops = 0
        self.drops = []
        self._refs()

    # ---- access helpers
    def folders(self, step, ses):
        return self.J.get("folders", {}).get("%s/s%d" % (step, ses)) or []

    def has(self, step, ses):
        return bool(self.folders(step, ses))

    def missing_steps(self):
        steps = sorted({k.split("/")[0] for k in self.J.get("folders", {})})
        return [st for st in steps if st not in SESSION1_ONLY and not self.has(st, 2)]

    def rows(self, path, **kw):
        cur = self.J
        for k in path.split("."):
            cur = cur.get(k, {}) if isinstance(cur, dict) else {}
        out = []
        for r in cur or []:
            if all(str(r.get(k)) == str(v) for k, v in kw.items()):
                out.append(r)
        return out

    def one(self, path, **kw):
        r = self.rows(path, **kw)
        return r[0] if r else None

    def sizecurve(self, kernel, size, cpu, ses, steps):
        for st in steps:
            r = self.one("size_curve.rows", kernel=kernel, size=size, cpu=cpu, session=ses, step=st)
            if r:
                return r
        return None

    def zs(self, kernel, cpu, ses):
        return sorted(self.rows("ZS.rows", kernel=kernel, cpu=cpu, session=ses), key=lambda r: r["size_bytes"])

    def zs_fit(self, cpu, ses):
        c = self.J.get("ZS", {}).get("rule", {}).get("cpu%d/s%d" % (cpu, ses))
        return (c["intercept"], c["slope"]) if c and c.get("intercept") is not None else (None, None)

    def slope(self):
        """median slope of the fitted lines of step ZS over the cells that exist"""
        return med([self.zs_fit(c, s)[1] for c, s in self.cells()])

    def r1cell(self, size, cpu, ses):
        return self.one("round1.cells", size=size, cpu=cpu, session=ses)

    def claim(self, prefix):
        for c in self.J.get("claims", []):
            if c["id"].startswith(prefix):
                return c
        return None

    def short(self, folder):
        m = re.match(r"^(?:bwx\d+-)?([A-Za-z0-9]+)-s(\d+)-", folder)
        return ("%s s%s" % (m.group(1).upper() if m.group(1) == "h2" else m.group(1), m.group(2))) if m else folder

    def cells(self):
        return [(c, s) for c in CPUS for s in SESSIONS]

    def draw(self, plots, aria):
        """SVG of one panel; counts the labels that found no free place"""
        bodies = [p.body() for p in plots]
        self.label_drops += sum(p.dropped for p in plots)
        for p in plots:
            for t in p.dropped_texts:
                self.drops.append("%s: label '%s'" % (aria, t))
        return svg(bodies, plots[0].W, plots[0].H, aria)

    def one_session(self, *steps):
        """a sentence for results that rest on one session"""
        m = [st for st in steps if self.has(st, 1) and not self.has(st, 2)]
        if not m:
            return ""
        return ("<p class='miss'>One session only: %s of step%s %s. The results of this part are not confirmed.</p>" % (
            MISSING, "s" if len(m) > 1 else "", ", ".join(m)))

    # ---- references
    def _refs(self):
        R = self.R
        n, a = esc(N_DIR), esc(HERE)
        R.define("handoff", "<code>%s/tackle-8mb-handoff.md</code>: the goal, the machine rules, "
                            "the section &quot;Reporting&quot;." % n)
        R.define("progress", "<code>%s/tackle-8mb-progress.md</code>: the log of the rounds." % n)
        R.define("decisions", "<code>%s</code>, section &quot;Second agent, 2026-11-15&quot;: hypotheses, steps, "
                              "decision rules, build digests, deviations." % esc(self.decisions_path))
        R.define("design", "<code>%s/tackle-8mb.md</code>: the design. Sections &quot;Shared "
                           "repeatability rule&quot; and &quot;What counts as progress, and what counts as an "
                           "answer&quot;." % n)
        R.define("final8", "<code>%s/final8.txt</code> and <code>final8.json</code> in the same folder: every "
                           "number and verdict. Written by <code>final8.py</code> in the same folder." % a)
        R.define("generator", "<code>%s/report_final.py</code>: this page's generator. "
                              "<code>test_report_final.py</code> in the same folder checks it." % a)
        R.define("palette", "The dataviz skill, file <code>references/palette.md</code>: categorical slots 1 "
                            "(blue) and 2 (orange), documented there as validated for colour-blind readers.")
        steps = sorted({k.split("/")[0] for k in self.J.get("folders", {})})
        for st in steps:
            fl = [f for s in SESSIONS for f in self.folders(st, s)]
            R.define("step:" + st, "Step <code>%s</code>, result folders under <code>%s/</code>: %s." % (
                st, esc(self.results), ", ".join("<code>%s</code>" % esc(f) for f in fl) if fl else "none"))
        R.define("listing", "<code>%s/crb-build-1/listing.txt</code> and <code>offsets.tsv</code> in the same folder: "
                            "the build record of the test program <code>bwx8</code> with the instructions of each "
                            "kernel and the place of each loop." % esc(X_DIR))
        R.define("h2env", "<code>env.txt</code> in the result folders of step H2: the digests of "
                          "<code>bw_old</code> and <code>bw_new</code>.")

    # ---- supplementary evaluations (block 16 of final8.txt)
    def sup(self, key):
        return (self.J.get("supplementary") or {}).get(key) or {}

    def sup_lead(self, what, beside="the recorded verdict above and does not replace it"):
        return ("<p><b>Supplementary evaluation, defined after the data was seen: %s.</b> It stands beside %s %s.</p>"
                % (what, beside, self.R("final8")))

    def loop_mod64(self, kernel):
        """place of the loop of a kernel in the code, in bytes modulo 64, from the build record (None if unreadable)"""
        try:
            with open(os.path.join(X_DIR, "crb-build-1", "offsets.tsv")) as f:
                for line in f:
                    c = line.rstrip("\n").split("\t")
                    if len(c) >= 6 and c[0] == "bwx8" and c[1] == kernel:
                        return int(c[5])
        except (OSError, ValueError):
            pass
        return None

    def sref(self, *steps):
        return self.R(*["step:" + s for s in steps if ("step:" + s) in self.R.text])

    # ================================================================== section 1
    def gains8(self):
        g = [c["new_minus_old"]["gain_pct"] for c in self.rows("round1.cells", size="8M")]
        g += [r["median_gain_pct"] for r in self.rows("H2.rows") if r.get("median_gain_pct") is not None]
        return g

    def cycles8(self):
        vals = []
        for r in self.rows("counters.rows", event="cpu_cycles", size="8M"):
            if r["kernel"] in ("read", "asmread"):
                vals += [r.get("low"), r.get("high"), r.get("single")]
        vals += [r["cyc"] for r in self.rows("ZS.rows", kernel="asmread", size="8M")]
        vals += [r["per64"]["cpu_cycles"] for r in self.rows("prefetch.YC", kernel="asmread", size="8M")]
        return [v for v in vals if v is not None]

    def sec1(self):
        g1 = med([c["new_minus_old"]["gain_pct"] for c in self.rows("round1.cells", size="1M")])
        g8 = self.gains8()
        c8 = self.cycles8()
        old8 = med([r["cyc"] for r in self.rows("ZS.rows", kernel="oldread", size="8M")])
        asm1 = med([r["cyc"] for r in self.rows("ZS.rows", kernel="asmread", size="1M")])
        slope = self.slope()
        miss = self.missing_steps()
        oldc = [r["cyc"] for r in self.rows("ZS.rows", kernel="oldread") if r["size_bytes"] <= 16 << 20]
        r8 = med([r["r"] for r in self.rows("ZS.rows", kernel="asmread", size="8M")])
        inv = [r for r in self.J.get("inventory", {}).get("rows", []) if r.get("folder") and r.get("load_min") is not None]
        h = "<h1>Why the new read loop gains so little at 8 MiB on CRB</h1>"
        h += "<ul class='meta'><li>Report date %s.</li>" % esc(self.date)
        h += "<li>Generated by <code>report_final.py</code> from <code>final8.json</code> %s.</li>" % (
            self.R("final8", "generator"))
        if inv:
            h += ("<li>System load of CRB (the test machine) at the launch of the test processes: %s to %s. "
                  "This is the 1 minute load average over all steps (table 23).</li>" % (
                      fnum(min(r["load_min"] for r in inv)), fnum(max(r["load_max"] for r in inv))))
        h += "</ul>"
        h += "<div class='short'><h2>Short version</h2><p>"
        h += ("On the CRB machine the new load-only read loop is %s %% faster than the old read loop at 1 MiB. "
              "At 8 MiB it is only %s to %s %% faster. " % (
                  fnum(g1, 0), fnum(min(g8), 1) if g8 else "NA", fnum(max(g8), 1) if g8 else "NA"))
        h += ("Hypothesis H1c (each line from the shared cache costs about %s extra cycles) %s.</p></div>" % (
                  fnum(slope, 2),
                  "is judged by its recorded rule in section 5" if self.has("ZS", 2) else
                  "rests on one session and is not confirmed"))
        h += "<p>Detail behind the Short version.</p><ul>"
        h += ("<li><b>Cycle counts.</b> The counted cost in processor cycles for each 64-byte line agrees with "
              "these gains.</li>")
        h += ("<li><b>Old loop.</b> It needs %s to %s cycles for each line at every size from 1 to 16 MiB.</li>" % (
                  fnum(min(oldc), 2) if oldc else "NA", fnum(max(oldc), 2) if oldc else "NA"))
        h += ("<li><b>New loop.</b> It needs %s cycles for each line at 1 MiB. It needs %s to %s cycles at 8 MiB.</li>" % (
                  fnum(asm1, 2), fnum(min(c8), 2) if c8 else "NA", fnum(max(c8), 2) if c8 else "NA"))
        h += ("<li><b>Shared cache.</b> At 8 MiB, %s %% of the lines of the new loop come from the shared cache.</li>" % (
                  fnum(100.0 * r8, 0) if r8 is not None else "NA"))
        h += "<li><b>Cost rule.</b> Hypothesis H1c is the cost rule behind these numbers.</li>"
        h += ("<li><b>Open questions.</b> Root access is needed to answer two questions."
              "<ul><li>Why does a line from the shared cache cost more?</li>"
              "<li>Which hardware part moves the new loop between two rates at 8 MiB?</li></ul></li>")
        h += "</ul>"
        if miss:
            h += ("<p class='warn'><b>Status of the data.</b> Session 2 of these steps is not in "
                  "<code>final8.json</code> yet: %s.</p>" % ", ".join("<code>%s</code>" % esc(s) for s in miss))
            h += ("<ul><li>Each result of these steps comes from one session.</li>"
                  "<li>A one-session result is not confirmed.</li>"
                  "<li>The affected tables print &quot;%s&quot;.</li>" % MISSING)
            wait = [c["id"] for c in self.J.get("claims", []) if c.get("missing")]
            full = [c["id"] for c in self.J.get("claims", []) if not c.get("missing")]
            if wait:
                h += ("<li>Hypotheses whose verdict rests on both sessions: %s.</li>"
                      "<li>Hypotheses whose verdict waits for session 2: %s.</li>"
                      "<li>Table 19 gives each verdict.</li>" % (
                          esc(", ".join(full)) or "none", esc(", ".join(wait))))
            h += "</ul>"
        else:
            h += ("<p class='ok'><b>Status of the data.</b> Both sessions of every step are in "
                  "<code>final8.json</code>.</p>")
        words = [
            ("CRB", "The test machine: an Arm Phoenix reference server. 128 cores at 2.8 GHz. Each core has a private "
                    "64 KiB first-level cache and a private 2 MiB second-level cache. All cores share one 128 MiB "
                    "system-level cache."),
            ("SLC", "The system-level cache of CRB (the shared third cache level, 128 MiB)."),
            ("L1, L2", "The first-level cache and the second-level cache of one core."),
            ("line", "One cache line: 64 bytes."),
            ("rate", "Bytes read per second, in GB/s. 1 GB is 1e9 bytes."),
            ("old read", "The read loop of the original benchmark. It loads the data and adds it up with vector "
                         "instructions. Kernel name <code>oldread</code>."),
            ("new read", "The load-only loop. The C version is the kernel <code>read</code>. The assembly version "
                         "is the kernel <code>asmread</code>."),
            ("kernel", "One measured loop of the test runner."),
            ("<code>bwx8</code>, <code>bwx10</code>, <code>bwx11</code>", "The test runner and its two later builds. "
                                                                         "Section 9 says what each build adds."),
            ("gain", "New rate divided by old rate, minus 1, in percent."),
            ("cycles per line", "Processor cycles that the loop spends for each 64-byte line. Counted with the "
                                "core's cycle counter. 2.8 cycles per line equals 64 GB/s at 2.8 GHz."),
            ("r", "The share of lines that enter the second-level cache from the SLC. Counter event "
                  "<code>l2d_cache_refill</code> per line."),
            ("first-level long miss", "A load that waits for a line that is not in the first-level cache. Counter "
                                      "event <code>l1d_cache_lmiss_rd</code>."),
            ("step", "One batch of test processes. Its name has two or three letters, for example <code>ZS</code>. "
                     "Each step has one result folder per session."),
            ("session", "One visit on CRB. Session 2 repeats session 1 at least 3 hours later with the CPU order "
                        "reversed."),
            ("cell", "The processes of one step, kernel, size, CPU and session."),
            ("set", "In step S2: one old read process, one <code>read</code> process and one <code>asmread</code> "
                    "process of the same size, CPU and session. A cell has 6 sets."),
            ("fourth window", "In step S2 a trial runs 4 windows of the same kernel and then 4 measured windows. "
                              "The fourth window is the last measured one."),
            ("P1, P2", "Two predictions of the design."
                       "<ul><li>P1: old read has the same rate at 8 MiB as at 1 MiB, inside a margin of 0.30 GB/s.</li>"
                       "<li>P2: the new loop is slower at 8 MiB than at 1 MiB.</li></ul>"),
            ("fitted line", "The straight line with the smallest sum of squared distances to the points of step "
                            "ZS (a least-squares fit). It describes those points. It is not an independent prediction."),
            ("median, p5, p95", "<ul><li>Median: the middle value.</li>"
                                "<li>p5: 5 % of the window rates of a process lie below this value.</li>"
                                "<li>p95: 95 % of the window rates of a process lie below this value.</li>"
                                "<li>A cell value is the median over the processes of the cell.</li></ul>"),
            ("window", "One timed interval of a process. 0.3 s unless a step says otherwise."),
            ("low level, high level", "The two rates between which a load-only loop moves at 8 MiB."),
            ("record", "The 80-byte entry in which the test runner stores the times of one window. The array of "
                       "records is <code>win[]</code>."),
            ("pad", "A count of bytes by which a test moves the record array (option <code>--rec-pad</code>)."),
            ("H1, H1b, H1c, H1d, H2, H3a, H4, H7", "Names of the hypotheses. Section 8 states each one."),
            ("core cost", "The cycles per line that a loop needs when all its data is in the first-level cache."),
            ("dose", "The amount of the suspected cause that a test applies. In section 5 the dose is r."),
            ("hardware prefetcher", "The part of a core that loads lines ahead of the loop by itself."),
            ("target", "The measured part of a process. Some tests run another activity for 3 s before it."),
            ("rule", "A decision rule that was written in the decisions file before the data of its step was read."),
            ("as recorded", "The text is printed as the analysis output gives it, word for word. In such a text "
                            "<code>cpu2/s1</code> means CPU 2 in session 1. &quot;True&quot; means yes."),
            ("candidate", "The explanation that the design planned to test. It has two parts."
                          "<ul><li>Old read reaches a limit of the core near 67 GB/s.</li>"
                          "<li>The rate of the new loop falls toward that value as the buffer grows.</li></ul>"
                          "&quot;Candidate supported&quot; means that P1 and P2 hold. It does not name the part of "
                          "the core or of the caches that sets either limit."),
            ("supported, rejected, contradicted, undecided", "The outcomes that a rule can give. "
                                                             "&quot;Confirmed&quot; needs the same outcome in both sessions on both CPUs."),
            ("est.", "Estimated: computed from other numbers, not measured directly."),
            ("calc.", "A table cell in italics. This page computed it from numbers of <code>final8.json</code>."),
            ("Insufficient data", "The data cannot decide the point. The text names the measurement that would."),
        ]
        h += "<h2>Words used here</h2>" + table(
            ["Term", "Meaning"], [["<th scope='row'>%s</th>" % t, "<td class='txt'>%s</td>" % m] for t, m in words], cls="words")
        return h

    # ================================================================== section 2
    def fig_cycles(self):
        svgs = []
        take = None
        for cpu in CPUS:
            p = Plot((0.85, 38), (2.0, 2.9), H=340, xlog=True)
            p.frame()
            p.title("CPU %d" % cpu, "cycles per 64 B line (axis starts at 2.0)")
            p.yticks([2.0, 2.2, 2.4, 2.6, 2.8], "%.1f")
            p.xticks([1, 2, 4, 8, 16, 32], title="buffer size, MiB (log scale)")
            drew = False
            first = None
            for ses in SESSIONS:
                asm, old = self.zs("asmread", cpu, ses), self.zs("oldread", cpu, ses)
                if not asm:
                    continue
                drew = True
                first = first or ses
                ic, sl = self.zs_fit(cpu, ses)
                mb = lambda r: r["size_bytes"] / 1048576.0
                for rows, col in ((old, C_OLD), (asm, C_NEW)):
                    p.path([(p.X(mb(r)), p.Y(r["cyc"])) for r in rows], col, 1.5, opacity=0.55 if ses == 1 else 0.3)
                if ic is not None:
                    for r in asm:
                        p.dot(p.X(mb(r)), p.Y(ic + sl * r["r"]), C_PRED, SHAPE[ses], hollow=True, r=5.5,
                              tip="fitted line: %.3f cycles at %s (%.3f + %.3f x r, r = %.3f), session %d" % (
                                  ic + sl * r["r"], r["size"], ic, sl, r["r"], ses))
                for rows, col, nm in ((old, C_OLD, "old read"), (asm, C_NEW, "asmread")):
                    for r in rows:
                        p.dot(p.X(mb(r)), p.Y(r["cyc"]), col, SHAPE[ses], r=3.6,
                              tip="%s, %s, session %d: %.3f cycles per line, %.2f GB/s" % (
                                  nm, r["size"], ses, r["cyc"], r["rate"]))
            if not drew:
                p.raw_text((p.fx0 + p.fx1) / 2, (p.fy0 + p.fy1) / 2, "step ZS: no data", "middle", 12)
                svgs.append(self.draw([p], "no data"))
                continue
            ses = first
            A = {r["size"]: r for r in self.zs("asmread", cpu, ses)}
            O = {r["size"]: r for r in self.zs("oldread", cpu, ses)}
            notes = []
            for size in ("1M", "8M"):
                if size in A and size in O:
                    a, o = A[size], O[size]
                    x = p.X(a["size_bytes"] / 1048576.0)
                    p.path([(x, p.Y(a["cyc"]) - 6), (x, p.Y(o["cyc"]) + 6)], C_INK, 1.2, layer="marks")
                    p.label(x, p.Y(a["cyc"]), "%.2f" % a["cyc"], "R BR B AR" if size == "1M" else "L BL AL")
                    p.label(x, p.Y(o["cyc"]), "%.2f" % o["cyc"], "BR R AR" if size == "1M" else "AL A AR")
                    notes.append((size, o["cyc"] - a["cyc"], 100.0 * (a["rate"] / o["rate"] - 1.0), x, a, o))
            # callouts in the two empty regions of the frame
            for size, gap, gain, x, a, o in notes:
                l1 = "%s MiB: gap %.2f cycles" % (size[:-1], gap)
                l2 = "= gain %+.1f %%" % gain
                if size == "1M":
                    tx, ty = p.fx0 + 8, p.Y(2.86)
                    p.raw_text(tx, ty, l1, fs=11, cls="lab b")
                    p.raw_text(tx, ty + 13, l2, fs=11, cls="lab b")
                    p.path([(x + 3, p.Y(o["cyc"]) - 8), (x + 3, ty + 17)], C_INK2, 0.8, dash="2 2")
                else:
                    tx, ty = p.fx1 - 6, p.Y(2.33)
                    p.raw_text(tx, ty, l1, "end", 11, "lab b")
                    p.raw_text(tx, ty + 13, l2, "end", 11, "lab b")
                    p.path([(x, p.Y(a["cyc"]) + 8), (x, ty - 11)], C_INK2, 0.8, dash="2 2")
            # inset: the 32 KiB point is far below this axis
            c32 = [r for r in self.rows("counters.rows", event="cpu_cycles", size="32K", cpu=cpu, session=ses)]
            o32 = self.sizecurve("oldread", "32K", cpu, ses, ("S2",))
            ty = p.Y(2.16)
            p.raw_text(p.fx1 - 6, ty, "32 KiB, below this axis:", "end", 11, "lab")
            if c32:
                v = c32[0]["single"] if c32[0]["single"] is not None else c32[0]["high"]
                p.raw_text(p.fx1 - 6, ty + 13, "read %.2f cycles (counted)" % v, "end", 11, "lab")
            if o32:
                p.raw_text(p.fx1 - 6, ty + 26, "old read %.2f (est. from rate)" % CALC["cyc"](o32["median"]), "end", 11, "lab")
            if take is None and len(notes) == 2:
                take = (cpu, ses, notes)
            svgs.append(self.draw([p], "Cycles per 64 byte line against buffer size on CPU %d for old read and asmread" % cpu))
        leg = [(sw(C_OLD), "old read (measured)"), (sw(C_NEW), "asmread, the new loop (measured)"),
               (sw(C_PRED, hollow=True), "fitted line of step ZS at the measured r (a fit to these points, not an "
                                         "independent prediction)")] + session_legend()
        if take:
            cpu, ses, notes = take
            t = ("From 1 MiB to 8 MiB the gap between old read and the new loop shrinks from %.2f to %.2f cycles "
                 "(CPU %d, session %d)." % (notes[0][1], notes[1][1], cpu, ses))
            extra = ("<p>What the figure shows on CPU %d in session %d.</p><ul>"
                     "<li>Old read stays near %.2f cycles per line.</li>"
                     "<li>The new loop rises from %.2f cycles per line at 1 MiB to %.2f cycles per line at 8 MiB.</li>"
                     "<li>The curve has no step at 8 MiB.</li></ul>" % (
                         cpu, ses, notes[0][5]["cyc"], notes[0][4]["cyc"], notes[1][4]["cyc"]))
        else:
            t = "Step ZS has no data yet."
            extra = ""
        extra += ("<p class='note'>How to read the figure.</p><ul class='note'>"
                  "<li>The cycle axis starts at 2.0 cycles. So the heights of the points do not show ratios.</li>"
                  "<li>Each point is one process of 6 s.</li>"
                  "<li>From 4 to 8 MiB the blue points do not lie on one curve.</li>"
                  "<li>Hypothesis, not tested for each size: the process of such a point ran at the low level or at "
                  "the high level. Section 7 describes these two levels for 8 MiB.</li></ul>")
        return figure("Figure 1. Cycles per line against buffer size (step ZS, one process per point)", leg, panels(svgs), t,
                      extra)

    def sec2(self):
        h = "<h2>2. The answer in one figure</h2>"
        fit = []
        for cpu, ses in self.cells():
            ic, sl = self.zs_fit(cpu, ses)
            if ic is not None:
                fit.append("<li>CPU %d session %d: %.3f + %.3f &times; r</li>" % (cpu, ses, ic, sl))
        h += "<ul>"
        h += ("<li><b>The test.</b> Step <code>ZS</code> counted processor cycles and second-level cache refills. "
              "It did so at 13 buffer sizes from 1 MiB to 32 MiB %s.</li>" % self.sref("ZS"))
        oldc = [r["cyc"] for r in self.rows("ZS.rows", kernel="oldread") if r["size_bytes"] <= 16 << 20]
        Zr = self.J.get("ZS", {}).get("rule", {})
        chk = sum(c.get("oldread_checked") or 0 for c in Zr.values())
        fail = sum(c.get("oldread_fails") or 0 for c in Zr.values())
        if oldc:
            h += ("<li><b>Old read.</b> It costs %s to %s cycles per line at every size from 1 to 16 MiB.</li>" % (
                      fnum(min(oldc), 3), fnum(max(oldc), 3)))
            h += ("<li><b>Check of old read.</b> The rule of the step checks the old read points with r below 0.83 "
                  "against 2.671 cycles. Of these %d points, %d lie within 0.02 cycles of that value (table 9).</li>" % (
                      chk, chk - fail))
            h += ("<li><b>Reading (hypothesis H1).</b> Old read is limited by its own instructions inside the core. "
                  "It is not limited by the caches."
                  "<ul><li>Section 4 tests this idea on load-only loops with added instructions.</li>"
                  "<li>Section 4 also compares old read with a kernel that has the loads of old read and no adds. "
                  "That comparison was defined after the data was seen.</li></ul></li>")
        h += "<li><b>New loop.</b> It costs more cycles at the sizes where more lines come from the SLC.</li>"
        if fit:
            h += ("<li><b>Fitted lines.</b> Each fitted line gives the cycles per line of the new loop in one CPU and "
                  "session.<ul>%s</ul></li>") % "".join(fit)
        else:
            h += "<li><b>Fitted lines.</b> The fitted lines are: none yet.</li>"
        h += ("<li>A fitted line describes the points of the step. It is not an independent prediction %s.</li>" %
              self.R("final8"))
        cross = []
        for cpu, ses in self.cells():
            O = {r["size"]: r for r in self.zs("oldread", cpu, ses)}
            last = None
            for a in self.zs("asmread", cpu, ses):
                if a["size"] in O and a["cyc"] < O[a["size"]]["cyc"]:
                    last = a["size"]
            nxt = next((a["size"] for a in self.zs("asmread", cpu, ses)
                        if last and a["size_bytes"] > [x for x in self.zs("asmread", cpu, ses) if x["size"] == last][0]["size_bytes"]), None)
            if last and nxt:
                cross.append("<li>CPU %d session %d: fewer cycles at %s, more cycles at %s.</li>" % (
                    cpu, ses, last.replace("M", " MiB"), nxt.replace("M", " MiB")))
        a8 = [r["cyc"] for r in self.rows("ZS.rows", kernel="asmread", size="8M")]
        o8 = [r["cyc"] for r in self.rows("ZS.rows", kernel="oldread", size="8M")]
        if a8 and o8:
            named = lambda k: "".join(
                "<li>CPU %d session %d: %s cycles per line.</li>" % (cpu, ses, fnum(r["cyc"], 3))
                for cpu, ses in self.cells() for r in self.rows("ZS.rows", kernel=k, size="8M", cpu=cpu, session=ses))
            h += ("<li><b>At 8 MiB.</b> The costs in this step are as follows."
                  "<ul><li>New loop:<ul>%s</ul></li>"
                  "<li>Old read:<ul>%s</ul></li></ul></li>" % (named("asmread"), named("oldread")))
            h += ("<li><b>Cycles and rate.</b> Cycles per line and rate are two forms of one measurement. "
                  "The formula is: rate = 2.8 GHz &times; 64 B / cycles per line.</li>")
            h += "<li>So a small gap in cycles is a small gain.</li>"
        if cross:
            h += ("<li><b>Where the cost curves cross.</b> Up to one size the new loop costs fewer cycles than old "
                  "read. At the next size of the step it costs more.<ul>%s</ul></li>" % "".join(cross))
            h += "<li>These are the largest size with the lower cost and the next size of the step.</li>"
            h += "<li>So 8 MiB is not a special size. It lies below the size where the two cost curves cross.</li>"
        h += "</ul>"
        h += self.one_session("ZS") + self.fig_cycles()
        # table
        rows = []
        for cpu, ses in self.cells():
            asm = self.zs("asmread", cpu, ses)
            if not asm:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(9)])
                continue
            O = {r["size"]: r for r in self.zs("oldread", cpu, ses)}
            ic, sl = self.zs_fit(cpu, ses)
            for a in asm:
                o = O.get(a["size"])
                rows.append([TH(a["size"]), TH(cpu), TH(ses), V(a["rate"]), V(a["cyc"], 3), V(a["r"], 3),
                             CC("line", (ic, sl, a["r"]), 3),
                             V(o["rate"]) if o else V(None), V(o["cyc"], 3) if o else V(None),
                             CC("diff", (o["cyc"], a["cyc"]), 3) if o else V(None),
                             CC("gain", (a["rate"], o["rate"]), 1) if o else V(None),
                             TX("inside" if a.get("inside") else "outside")])
        h += table(["Size", "CPU", "Session", "asmread rate, GB/s", "asmread cycles per line", "r",
                    "fitted line at r, cycles (calc.)", "old read rate, GB/s", "old read cycles per line",
                    "gap, cycles (calc.)", "gain, % (calc.)", "asmread against the band of section 5"], rows,
                   caption="Table 1. Step ZS: every point of figure 1. Medians over the 20 counted windows of one process.")
        # 32 KiB
        rows = []
        for cpu, ses in self.cells():
            c = self.one("counters.rows", event="cpu_cycles", size="32K", cpu=cpu, session=ses)
            rd = self.sizecurve("read", "32K", cpu, ses, ("S2",))
            od = self.sizecurve("oldread", "32K", cpu, ses, ("S2",))
            if not c and not rd:
                rows.append([TH(cpu), TH(ses), MISS(5)])
                continue
            if c and c["single"] is not None:
                cyc = V(c["single"], 3)
            elif c:
                cyc = VL([c["low"], c["high"]], 3)
            else:
                cyc = V(None)
            rows.append([TH(cpu), TH(ses), cyc, V(rd["median"] if rd else None),
                         CC("cyc", (rd["median"],), 3, est=True) if rd else V(None),
                         V(od["median"] if od else None), CC("cyc", (od["median"],), 3, est=True) if od else V(None)])
        h += table(["CPU", "Session", "read: counted cycles per line (step XCA)", "read rate, GB/s (step S2)",
                    "read cycles from the rate (calc.)", "old read rate, GB/s (step S2)",
                    "old read cycles from the rate (calc.)"], rows,
                   caption="Table 2. The 32 KiB point (data in the first-level cache). Two values in one cell: the "
                           "process showed two levels, low and high.")
        h += ("<ul class='note'><li>The cycle counter did not run for old read at 32 KiB.</li>"
              "<li>So its value is an estimate: 2.8 GHz &times; 64 B / rate.</li>"
              "<li>The counted value comes from step XCA. The rates come from step S2 %s.</li></ul>" % self.sref("XCA", "S2"))
        return h

    # ================================================================== section 3
    def gain_rows(self, cpu, ses):
        """[(size, bytes, old, new, gain, step)] of kernel read, steps S2 and XF"""
        out = {}
        for c in self.rows("round1.cells", cpu=cpu, session=ses):
            out[c["size"]] = [c["size"], None, c["oldread"], c["read"], c["new_minus_old"]["gain_pct"], "S2"]
        for r in self.rows("size_curve.rows", kernel="read", cpu=cpu, session=ses, step="XF"):
            o = self.one("size_curve.rows", kernel="oldread", size=r["size"], cpu=cpu, session=ses, step="XF")
            out[r["size"]] = [r["size"], r["size_bytes"], o["median"] if o else None, r["median"],
                              CALC["gain"](r["median"], o["median"]) if o else None, "XF"]
        for r in self.rows("size_curve.rows", cpu=cpu, session=ses):
            if r["size"] in out:
                out[r["size"]][1] = r["size_bytes"]
        return sorted(out.values(), key=lambda t: t[1] or 0)

    def fig_gain(self):
        svgs = []
        for cpu, ses in self.cells():
            rows = self.gain_rows(cpu, ses)
            if not rows:
                continue
            rh = 17
            p = Plot((45, 168), (0, 1), H=36 + rh * len(rows) + 46, ml=50, mr=10, mb=40)
            p.frame()
            p.title("CPU %d, session %d" % (cpu, ses), "buffer size")
            p.xticks([60, 80, 100, 120, 140, 160], title="rate, GB/s (axis starts at 45)", grid=True)
            for i, (size, _, old, new, gain, step) in enumerate(rows):
                y = p.fy0 + rh * (i + 0.5) + 2
                p.raw_text(p.fx0 - 6, y + 4, size, "end", 11, "ax", False)
                if old is not None:
                    p.path([(p.X(old), y), (p.X(new), y)], C_INK2, 1.2)
                    p.dot(p.X(old), y, C_OLD, r=4, tip="old read %.2f GB/s at %s (step %s)" % (old, size, step))
                p.dot(p.X(new), y, C_NEW, r=4, tip="read %.2f GB/s at %s (step %s)" % (new, size, step))
                right = max(new, old if old is not None else new)
                if gain is not None:
                    p.label(p.X(right), y, "%+.1f %%" % gain, "R L", cls="lab b")
                else:
                    p.label(p.X(right), y, "%.1f" % new, "R L")
            svgs.append(self.draw([p], "Old and new read rate by buffer size, CPU %d session %d" % (cpu, ses)))
        g1 = [c["new_minus_old"]["gain_pct"] for c in self.rows("round1.cells", size="1M")]
        g8 = [c["new_minus_old"]["gain_pct"] for c in self.rows("round1.cells", size="8M")]
        g16 = [c["new_minus_old"]["gain_pct"] for c in self.rows("round1.cells", size="16M")]
        t = "Only the blue dot moves with the size." if g8 else "No data."
        extra = ""
        if g8:
            extra += ("<p>The gain by size (step S2, cell medians):</p><ul>"
                      "<li>1 MiB: %.1f %%.</li>"
                      "<li>8 MiB: %.1f to %.1f %%.</li>"
                      "<li>16 MiB: %.1f to %.1f %%.</li></ul>" % (med(g1), min(g8), max(g8), min(g16), max(g16)))
        extra += ("<ul class='note'>"
                  "<li>A row with one dot and a plain number has no old read measurement at that size. The number "
                  "is the new read rate in GB/s.</li>"
                  "<li>Rows 32K, 1M, 4M, 8M and 16M are the cells of step S2 (fourth window).</li>"
                  "<li>The other rows are the cells of step XF (all windows).</li></ul>")
        leg = [(sw(C_OLD), "old read"), (sw(C_NEW), "new read (kernel read)")]
        return figure("Figure 2. Old and new read rate by size, with the gain as the label (steps S2 and XF)", leg,
                      panels(svgs), t, extra)

    def sec3(self):
        h = "<h2>3. Rates and gain by size</h2><ul>"
        c = self.claim("H1 / P1")
        h += ("<li><b>Step <code>S2</code></b> measured old read, <code>read</code> and <code>asmread</code> with 6 "
              "processes per cell. The sizes were 32 KiB, 1, 4, 8 and 16 MiB %s.</li>" % self.sref("S2"))
        h += "<li><b>Step <code>XF</code></b> added 10 sizes with 3 processes per cell %s.</li>" % self.sref("XF")
        pc = self.J.get("round1", {}).get("per_cell", {})
        d_old = [v["P1"]["median"] for v in pc.values() if v.get("P1")]
        d_new = [v["P2"]["read"]["median"] for v in pc.values() if v.get("P2")]
        if d_old and d_new:
            h += ("<li>Old read at 8 MiB minus old read at 1 MiB is %s to %s GB/s. This range covers the %d CPU and "
                  "session cells.</li>"
                  "<li>The same difference for <code>read</code> is %s to %s GB/s.</li>" % (
                      fnum(min(d_old), 3), fnum(max(d_old), 3), len(d_old), fnum(min(d_new)), fnum(max(d_new))))
        if c:
            h += ("<li>Prediction P1 says that old read keeps its rate. Prediction P2 says that the new loop loses "
                  "rate.</li>"
                  "<li>Verdict of P1 and P2, as recorded: %s %s.</li>" % (esc(c["overall"]), self.R("final8")))
        h += "</ul>" + self.fig_gain()
        rows = []
        for cpu, ses in self.cells():
            cs = sorted(self.rows("round1.cells", cpu=cpu, session=ses),
                        key=lambda c: ["32K", "1M", "4M", "8M", "16M"].index(c["size"]) if c["size"] in ["32K", "1M", "4M", "8M", "16M"] else 9)
            if not cs:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(7)])
            for c in cs:
                d = c["new_minus_old"]
                rows.append([TH(c["size"]), TH(cpu), TH(ses), V(c["oldread"]), V(c["read"]), V(c["asmread"]),
                             V(d["median"]), VL(d["sets"]), V(d["gain_pct"]),
                             TX("yes" if d.get("repeatable") else "no")])
        h += table(["Size", "CPU", "Session", "old read, GB/s", "read, GB/s", "asmread, GB/s",
                    "read minus old read, GB/s (median)", "the six set values, GB/s", "gain, %", "repeatable"], rows,
                   caption="Table 3. Step S2: cell medians of the fourth window. The column \"the six set values\" gives "
                           "read minus old read for each of the 6 matched process sets.")
        rows = []
        for cpu, ses in self.cells():
            xs = [r for r in self.gain_rows(cpu, ses) if r[5] == "XF"]
            if not xs:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(3)])
            for size, _, old, new, gain, step in xs:
                rows.append([TH(size), TH(cpu), TH(ses), V(new), V(old),
                             CC("gain", (new, old), 2) if old is not None else V(None)])
        h += table(["Size", "CPU", "Session", "read, GB/s", "old read, GB/s", "gain, % (calc.)"], rows,
                   caption="Table 4. Step XF: cell medians over all windows, 3 processes per cell. NA: old read was "
                           "not measured at that size.")
        return h

    # ================================================================== section 4
    def fam(self, kernel, size, cpu, ses):
        """(row, step) of the family table: XN, ZN, or S2 for oldread and asmread"""
        if kernel in ("oldread", "asmread"):
            r = self.sizecurve(kernel, size, cpu, ses, ("S2",))
            return (r, "S2") if r else (None, None)
        for st in ("XN", "ZN"):
            r = self.one("families.%s.rows" % st, kernel=kernel, size=size, cpu=cpu, session=ses)
            if r:
                return r, st
        return None, None

    def fam_kernels(self):
        ks = {r["kernel"] for st in ("XN", "ZN") for r in self.rows("families.%s.rows" % st)} - {"asmread"}
        return sorted(ks | {"oldread", "asmread"})

    def asm8_for(self, step, cpu, ses):
        """asmread 8 MiB median that final8 pairs with a kernel of this step"""
        if step == "XN":
            r = self.one("families.XN.rows", kernel="asmread", size="8M", cpu=cpu, session=ses)
            return r["median"] if r else None
        if step == "ZN":
            src = self.J["families"]["ZN"].get("asmread_source", {}).get("s%d" % ses, {}).get("step")
            if src == "YF":
                r = self.one("prefetch.YF", kernel="asmread", size="8M", cpu=cpu, session=ses)
                return r["median"] if r else None
            r = self.one("evict.ZD", kernel="asmread", size="8M", cpu=cpu, session=ses)
            return r["plain"]["median"] if r else None
        r = self.sizecurve("asmread", "8M", cpu, ses, ("S2",))
        return r["median"] if r else None

    def fig_family(self):
        svgs = []
        sizes = ["32K", "1M", "8M", "16M"]
        names = ["32 KiB", "1 MiB", "8 MiB", "16 MiB"]
        take = None
        for cpu, ses in self.cells():
            data = {}
            for k in self.fam_kernels():
                pts = [(i, self.fam(k, s, cpu, ses)[0]) for i, s in enumerate(sizes)]
                pts = [(i, r["median"]) for i, r in pts if r]
                if pts:
                    data[k] = pts
            if not data:
                continue
            p = Plot((0, 3), (35, 140), H=350, ml=118, mr=40, mb=30)
            p.frame()
            p.title("CPU %d, session %d" % (cpu, ses), "rate, GB/s (cell median, axis starts at 35)")
            pad = 16
            xs = [p.fx0 + pad + i * (p.fx1 - p.fx0 - 2 * pad) / 3.0 for i in range(4)]
            for v in (40, 60, 80, 100, 120, 140):
                y = p.Y(v)
                p.under.append("<line class='grid' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>" % (p.fx0, y, p.fx1, y))
                p.raw_text(p.fx1 + 5, y + 4, "%d" % v, "start", 11, "ax", False)
            for i, x in enumerate(xs):
                p.raw_text(x, p.fy1 + 16, names[i], "middle", 11, "ax", False)
            left, fast8, slowlab, mid8 = [], [], [], []
            for k, pts in sorted(data.items(), key=lambda kv: -kv[1][0][1]):
                col = C_OLD if k == "oldread" else C_NEW
                p.path([(xs[i], p.Y(v)) for i, v in pts], col, 1.5, opacity=0.8)
                for i, v in pts:
                    p.dot(xs[i], p.Y(v), col, SHAPE[ses], r=3.4, tip="%s at %s: %.2f GB/s" % (k, names[i], v))
                if pts[0][0] == 0:
                    left.append((p.Y(pts[0][1]) + 4, "%s %.1f" % ("old read" if k == "oldread" else k, pts[0][1])))
                    c32 = pts[0][1]
                    v8 = dict(pts).get(2)
                    if v8 is not None and k != "oldread":
                        if c32 >= 76:
                            fast8.append(v8)
                        elif c32 <= 66:
                            slowlab.append((k, c32, v8))
                        else:
                            mid8.append((k, c32, v8))
            for y, t in spread_labels(left, p.fy0 + 12, p.fy1 - 4):
                p.raw_text(p.fx0 - 6, y, t, "end", 11, "lab", False)
            if fast8:
                p.raw_text(p.fx1 - 6, p.Y(122), "8 MiB: the kernels above", "end", 11, "lab b")
                p.raw_text(p.fx1 - 6, p.Y(122) + 13, "76 GB/s at 32 KiB run at", "end", 11, "lab b")
                p.raw_text(p.fx1 - 6, p.Y(122) + 26, "%.1f to %.1f GB/s" % (min(fast8), max(fast8)), "end", 11, "lab b")
            for k, c32, v8 in slowlab:
                p.label((xs[0] + xs[1]) / 2.0 + 8, p.Y(c32), "%.1f at 8 MiB" % v8, "A B", d=8)
            if not self.has("ZN", ses):
                p.raw_text(p.fx1 - 6, p.fy1 - 8, "step ZN: %s" % MISSING, "end", 11, "lab")
            if take is None and fast8 and slowlab:
                take = (cpu, ses, min(fast8), max(fast8), slowlab, mid8)
            svgs.append(self.draw([p], "Rate by size for each kernel, CPU %d session %d" % (cpu, ses)))
        leg = [(sw(C_OLD), "old read"), (sw(C_NEW), "load-only kernels (name and 32 KiB rate at the left end)")] + session_legend()
        extra = ""
        if take:
            cpu, ses, lo, hi, slow, mid = take
            t = "On CPU %d in session %d the slow load-only kernels keep their rate." % (cpu, ses)
            extra += "<p>The values behind the takeaway, for CPU %d in session %d:</p><ul>" % (cpu, ses)
            extra += "<li><b>Slow load-only kernels.</b> They keep their rate:<ul>%s</ul></li>" % "".join(
                "<li><code>%s</code>: %.1f GB/s at 32 KiB and %.1f GB/s at 8 MiB.</li>" % (esc(x[0]), x[1], x[2])
                for x in slow)
            extra += ("<li><b>Kernels above 76 GB/s at 32 KiB.</b> They all run at %.1f to %.1f GB/s at 8 MiB.</li>"
                      % (lo, hi))
            if mid:
                extra += ("<li><b>The kernel between them.</b> It does not fit either group:<ul>%s</ul></li>" % "".join(
                    "<li><code>%s</code> has %.1f GB/s at 32 KiB and %.1f GB/s at 8 MiB.</li>" % (esc(x[0]), x[1], x[2])
                    for x in mid))
            extra += "</ul>"
        else:
            t = "The slow kernels of step ZN have no data in this view yet."
        extra += ("<ul class='note'>"
                  "<li>The rate axis starts at 35 GB/s.</li>"
                  "<li>Kernels of step XN have no 16 MiB point.</li>"
                  "<li>Old read and asmread are the cells of step S2.</li>"
                  "<li>The kernels are ordered by their rate at 32 KiB.</li></ul>")
        return figure("Figure 3. Rate at four sizes for kernels with different core cost (steps S2, XN, ZN)", leg, panels(svgs), t,
                      extra)

    def sec4(self):
        F = self.J.get("families", {})
        cell_name = lambda key: esc(re.sub(r"^cpu(\d+)/s(\d+)$", r"CPU \1 session \2", key))
        h = "<h2>4. Test 1: change the core cost of the loop</h2><ul>"
        h += ("<li><b>The test</b> adds no-operation instructions (instructions that do nothing) to the load-only "
              "loop. The kernels:<ul>"
              "<li><code>read_nop16</code> has 16 of them.</li>"
              "<li><code>read_nop128</code> has 128.</li>"
              "<li><code>read_sparse</code> is a further variant of the same loop.</li></ul></li>")
        h += ("<li><b>C<sub>k</sub>.</b> Each kernel has its own rate when the data is in the first-level cache. "
              "This rate is called C<sub>k</sub> %s.</li>" % self.R("decisions"))
        h += ("<li><b>Hypothesis H1</b> says: two limits exist, and the smaller one holds.</li>"
              "<li>So at 8 MiB a kernel runs at the smaller of C<sub>k</sub> and the supply rate S. S is the rate "
              "that <code>asmread</code> shows at 8 MiB.</li>")
        h += ("<li>Steps <code>XN</code> and <code>ZN</code> ran the kernels with 6 processes per cell %s.</li></ul>"
              % self.sref("XN", "ZN"))
        h += self.one_session("ZN") + self.fig_family()
        # wide table
        rows = []
        for k in self.fam_kernels():
            for cpu, ses in self.cells():
                rs = {s: self.fam(k, s, cpu, ses) for s in ("32K", "1M", "8M", "16M")}
                step = next((st for r, st in rs.values() if r), None)
                if step is None:
                    expect = "ZN" if any(self.one("families.ZN.rows", kernel=k) for _ in [0]) else "XN"
                    rows.append([TH(k), TH(cpu), TH(ses), TX(expect), MISS(6)])
                    continue
                g = lambda s, f: (rs[s][0][f] if rs[s][0] else None)
                rows.append([TH(k), TH(cpu), TH(ses), TX(step), V(g("32K", "median")), V(g("1M", "median")),
                             V(g("8M", "median")), V(g("8M", "p5")), V(g("8M", "p95")), V(g("16M", "median"))])
        h += table(["Kernel", "CPU", "Session", "Step", "32 KiB median", "1 MiB median", "8 MiB median", "8 MiB p5",
                    "8 MiB p95", "16 MiB median"], rows,
                   caption="Table 5. Cell values in GB/s (median over the processes of the cell). NA: the step has no cell at that size.")
        # predicted against measured gain
        rows = []
        for k in self.fam_kernels():
            if k == "asmread":
                continue
            for cpu, ses in self.cells():
                r32, st = self.fam(k, "32K", cpu, ses)
                r8, _ = self.fam(k, "8M", cpu, ses)
                if not r32 or not r8:
                    rows.append([TH(k), TH(cpu), TH(ses), MISS(5)])
                    continue
                S = self.asm8_for(st, cpu, ses)
                if k == "oldread":
                    c = self.r1cell("8M", cpu, ses)
                    meas = V(c["asm_minus_old"]["gain_pct"]) if c else V(None)
                    S = c["asmread"] if c else None
                    C = self.r1cell("32K", cpu, ses)["oldread"] if self.r1cell("32K", cpu, ses) else None
                else:
                    meas = V(r8.get("asmread_gain_pct"))
                    C = r32["median"]
                rows.append([TH(k), TH(cpu), TH(ses), V(C), V(S), CC("pgain", (S, C), 2), meas,
                             TX("C_k below S: keeps C_k" if (C is not None and S is not None and C < S) else "C_k above S: limited by S")])
        h += table(["Kernel k", "CPU", "Session", "C_k: rate of k at 32 KiB, GB/s", "S: asmread at 8 MiB, GB/s",
                    "predicted gain of asmread over k, % (calc.)", "measured gain of asmread over k, %", "case"], rows,
                   caption="Table 6. Gain of asmread over kernel k at 8 MiB. Predicted = S / min(C_k, S) - 1. "
                           "Measured = asmread median / median of k - 1.")
        h += ("<ul class='note'>"
              "<li>S is the 8 MiB cell median of asmread. The analysis pairs it with the step of k:<ul>"
              "<li>old read: step S2 (fourth window).</li>"
              "<li>the kernels of step XN: step XN.</li>"
              "<li>the kernels of step ZN: step YF or ZD.</li></ul></li>"
              "<li>C_k below S: the predicted gain assumes that k keeps its 32 KiB rate at 8 MiB.</li>"
              "<li>C_k above S: the predicted gain is 0 %.</li>"
              "<li>A measured gain can lie far from 0 % in that case. Then the medians of k and of asmread sat at "
              "different levels (section 7).</li></ul>")
        h += self.sec4_sup()
        # rule 6
        h += "<h3>Verdicts of rule 6 of round 2 (step XN), as recorded</h3>"
        xn = F.get("XN", {})
        rows = []
        for cpu, ses in self.cells():
            c = xn.get("rule6", {}).get("cpu%d/s%d" % (cpu, ses))
            if not c:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(6)])
                continue
            for k, d in sorted(c["kernels"].items()):
                w = lambda x: "not tested" if x is None else ("holds" if x else "fails")
                rows.append([TH(k), TH(cpu), TH(ses), V(d["C"]), V(d["median_8M"]), V(d["p95_8M"]),
                             V(d["p95_minus_asm_p95"]), TX(w(d["a"])), TX(w(d["b"]))])
        h += table(["Kernel", "CPU", "Session", "C_k, GB/s", "8 MiB median, GB/s", "8 MiB p95, GB/s",
                    "p95 minus asmread p95, GB/s", "part (a)", "part (b)"], rows,
                   caption="Table 7. Rule 6, parts (a) and (b).")
        h += ("<ul class='note'>"
              "<li>Part (a) of rule 6 is a prediction about a kernel with C_k at least 5 GB/s above the asmread high "
              "level. The prediction: the p95 of such a kernel is within 1.0 GB/s of the p95 of asmread.</li>"
              "<li>Part (b) of rule 6 is a prediction about a kernel with C_k below the asmread low level. The "
              "prediction: such a kernel keeps C_k.</li></ul>")
        if xn.get("overall"):
            h += "<p>Verdict of rule 6 for each kernel, as recorded:</p>"
        h += "<ul>"
        for k, v in sorted(xn.get("overall", {}).items()):
            h += "<li><code>%s</code>: %s.</li>" % (esc(k), esc(v))
        h += "</ul><ul>"
        pc = xn.get("part_c", {})
        if pc:
            h += ("<li><b>Part (c).</b> It says: the spread of the kernels at 8 MiB is at most 25 %% of their spread "
                  "at 32 KiB. The result for each cell:<ul>%s</ul></li>" % "".join(
                      "<li>%s: %s.</li>" % (cell_name(k), "holds" if v else "fails") for k, v in sorted(pc.items())))
        if xn.get("tested_b") is False:
            h += "<li>No kernel of step XN is slow enough to test part (b). Step ZN tests it.</li>"
        for k in sorted({k for c in xn.get("rule6", {}).values() for k, d in c["kernels"].items() if d["a"] is False}):
            ds = [c["kernels"][k] for c in xn.get("rule6", {}).values() if k in c["kernels"]]
            below = sorted(-d["p95_minus_asm_p95"] for d in ds if d["a"] is False)
            h += ("<li><b>Part (a) fails for <code>%s</code> in %d of %d cells.</b><ul>"
                  "<li>Its p95 at 8 MiB stays %s to %s GB/s below the p95 of <code>asmread</code> (table 7).</li>"
                  "<li>So this kernel does not reach the high level of <code>asmread</code> in these cells.</li>"
                  "<li>The cause is not known.</li></ul></li>" % (
                      esc(k), len(below), len(ds), fnum(below[0]), fnum(below[-1])))
        h += "</ul>"
        # rule 2 of round 4
        h += "<h3>Verdicts of rule 2 of round 4 (step ZN), as recorded</h3>"
        zn = F.get("ZN", {})
        rows = []
        for cpu, ses in self.cells():
            c = zn.get("rule2", {}).get("cpu%d/s%d" % (cpu, ses))
            if not c:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(8)])
                continue
            for k, d in sorted(c["kernels"].items()):
                rows.append([TH(k), TH(cpu), TH(ses), V(c["S8_low"]), V(c["S8_high"]), V(d["C"]), V(d["median_8M"]),
                             V(d["p95_8M"]), TX(d["class"]), TX("holds" if d["prediction_holds"] else "fails"),
                             V(d.get("loss_32K_to_8M"))])
        h += table(["Kernel", "CPU", "Session", "S8 low, GB/s", "S8 high, GB/s", "C_k, GB/s", "8 MiB median, GB/s",
                    "8 MiB p95, GB/s", "class", "prediction", "loss from 32 KiB to 8 MiB, GB/s"], rows,
                   caption="Table 8. Rule 2 of round 4. S8 = the range from the low to the high level of asmread at 8 MiB.")
        if zn.get("overall"):
            h += "<p>Verdict of rule 2 for each kernel, as recorded:</p>"
        h += "<ul>"
        for k, v in sorted(zn.get("overall", {}).items()):
            h += "<li><code>%s</code>: %s.</li>" % (esc(k), esc(v))
        h += "</ul><ul>"
        for k in sorted({k for c in zn.get("rule2", {}).values() for k, d in c["kernels"].items() if d["prediction_holds"] is False}):
            cs = [(c["kernels"][k], c, key) for key, c in zn.get("rule2", {}).items()
                  if k in c["kernels"] and c["kernels"][k]["prediction_holds"] is False]
            n_all = sum(1 for c in zn.get("rule2", {}).values() if k in c["kernels"])
            h += ("<li><b>The prediction fails for <code>%s</code> in %d of %d cells.</b> The values of these cells "
                  "(table 8):<ul>%s"
                  "<li>So one supply rate for all loops does not describe these cells.</li>"
                  "<li>The cause is not known.</li></ul></li>" % (
                      esc(k), len(cs), n_all, "".join(
                          "<li>%s: its p95 at 8 MiB is %s GB/s. The high level of <code>asmread</code> is %s GB/s.</li>" % (
                              cell_name(key), fnum(d["p95_8M"]), fnum(c["S8_high"])) for d, c, key in cs)))
        h += "</ul>"
        return h

    def sec4_sup(self):
        """the two supplementary evaluations of section 4: old read without its adds, gain from two rates"""
        O, G = self.sup("old_without_adds"), self.sup("gain_from_two_rates")
        h = "<h3>Supplementary: a test that changes the old loop (old read without its vector adds)</h3>"
        beside = "the recorded verdicts of this section (tables 7 and 8) and replaces none of them"
        h += self.sup_lead("old read of step S2 against <code>read_sparse</code> of step XN", beside)
        h += ("<ul><li><b>The loop of old read</b> has 16 instructions per 128 B:<ul>"
              "<li>4 load instructions,</li>"
              "<li>8 vector adds,</li>"
              "<li>4 instructions for the counter, the pointer and the branch.</li></ul></li>"
              "<li><b>The loop of <code>read_sparse</code></b> also has 16 instructions per 128 B:<ul>"
              "<li>the same 4 load instructions,</li>"
              "<li>9 no-operation instructions,</li>"
              "<li>3 instructions for the pointer and the branch.</li></ul></li>"
              "<li>So <code>read_sparse</code> is the old loop with its 8 vector adds and its counter add replaced by "
              "no-operation instructions %s.</li>" % self.R("listing"))
        s32 = next((x for x in O.get("summary", []) if x["size"] == "32K"), None)
        if s32:
            h += ("<li>At 32 KiB the data is in the first-level cache. The values there, in the %d cells of CPU and "
                  "session (table 6a):<ul>"
                  "<li>old read runs at %s to %s GB/s,</li>"
                  "<li><code>read_sparse</code> runs at %s to %s GB/s,</li>"
                  "<li>the ratio is %s to %s.</li></ul></li>" % (
                      s32["cells"], fnum(s32["oldread_min"]), fnum(s32["oldread_max"]), fnum(s32["read_sparse_min"]),
                      fnum(s32["read_sparse_max"]), fnum(s32["ratio_min"], 3), fnum(s32["ratio_max"], 3)))
            if s32["ratio_min"] >= 1.5:
                h += ("<li>So removing the adds raises the 32 KiB rate to about twice its value.</li>"
                      "<li>The loads are the same in both loops. So the adds, and not the loads, set the cost of old "
                      "read.</li>")
            else:
                h += ("<li>So removing the adds does not raise the 32 KiB rate by half or more in every cell.</li>"
                      "<li>This comparison does not show that the adds set the cost of old read.</li>")
        else:
            h += "<li class='miss'>Steps S2 and XN have no common cell at 32 KiB yet.</li>"
        a, b = self.loop_mod64("oldread"), self.loop_mod64("read_sparse")
        h += ("<li><b>Limit:</b> the two kernels differ also in the place of the loop in the code.<ul>%s"
              "<li>A different place can change the rate of a loop.</li>"
              "<li>This comparison cannot separate that from the adds.</li></ul></li>"
              "<li><b>Limit:</b> the two kernels ran in two steps at different times (S2 and XN) %s.</li></ul>" % (
                  ("<li>The loop of old read starts at byte %d of a 64 B block. The loop of <code>read_sparse</code> "
                   "starts at byte %d %s.</li>" % (a, b, self.R("listing"))) if a is not None and b is not None else
                  "<li>The build record with the two places could not be read.</li>", self.sref("S2", "XN")))
        rows = []
        for size, name in (("32K", "32 KiB"), ("1M", "1 MiB"), ("8M", "8 MiB")):
            for cpu, ses in self.cells():
                r = next((x for x in O.get("rows", []) if x["size"] == size and x["cpu"] == cpu and x["session"] == ses), None)
                if not r:
                    rows.append([TH(name), TH(cpu), TH(ses), MISS(3)])
                    continue
                rows.append([TH(name), TH(cpu), TH(ses), V(r["oldread"]), V(r["read_sparse"]), V(r["ratio"], 3)])
        h += table(["Size", "CPU", "Session", "old read (step S2), GB/s", "read_sparse (step XN), GB/s",
                    "ratio read_sparse / old read"], rows,
                   caption="Table 6a. Supplementary, defined after the data was seen. Cell medians of old read and of "
                           "read_sparse (6 processes per cell).")
        h += ("<ul class='note'>"
              "<li>At 1 MiB and at 8 MiB the data does not fit the first-level cache.</li>"
              "<li>There the supply of lines sets the rate of read_sparse (sections 2 and 5). So the ratio is "
              "smaller.</li></ul>")
        h += "<h3>Supplementary: the gain at 8 MiB predicted from two rates</h3>"
        h += self.sup_lead("the gain of <code>asmread</code> over a slow kernel k at 8 MiB", beside)
        h += ("<ul><li><b>Idea:</b> two assumptions.<ul>"
              "<li>A slow kernel keeps its 32 KiB rate C<sub>k</sub> at 8 MiB.</li>"
              "<li><code>asmread</code> runs at one of its two levels at 8 MiB.</li></ul></li>"
              "<li>Then the gain of <code>asmread</code> over k at 8 MiB lies between two values:<ul>"
              "<li>low level / C<sub>k</sub> - 1,</li>"
              "<li>high level / C<sub>k</sub> - 1.</li></ul></li>"
              "<li><b>The two levels</b> are cell values at 8 MiB. They are the 5th and the 95th percentile of the "
              "window rates of <code>asmread</code> %s.</li>"
              "<li><b>The measured gain</b> uses the 8 MiB cell medians. It is the median of <code>asmread</code> "
              "over the median of k, minus 1 %s.</li></ul>" % (self.sref("YF", "ZD"), self.sref("S2", "ZN", "YF", "ZD")))
        rows, n_in, n_all, outside, steps = [], 0, 0, [], {}
        for k in ("oldread", "read_nop96", "read_nop128"):
            for cpu, ses in self.cells():
                r = next((x for x in G.get("rows", []) if x["kernel"] == k and x["cpu"] == cpu and x["session"] == ses), None)
                if not r or r.get("inside") is None:
                    rows.append([TH(k), TH(cpu), TH(ses), MISS(9)])
                    continue
                steps.setdefault(r["asmread_step"], set()).add(ses)
                n_all += 1
                n_in += 1 if r["inside"] else 0
                if not r["inside"]:
                    outside.append("%s on CPU %d in session %d" % (k, cpu, ses))
                rows.append([TH(k), TH(cpu), TH(ses), V(r["C"]), V(r["asmread_low"]),
                             V(r["asmread_high"]), V(r["predicted_low_pct"]), V(r["predicted_high_pct"]),
                             V(r["measured_pct"]), TX("inside" if r["inside"] else "outside"),
                             V(r["asmread_median"]), V(r["median_8M"])])
        used = "<li>The rows shown use %s.</li>" % " and ".join(
            "step %s in session %s" % (st, " and ".join("%d" % x for x in sorted(ss)))
            for st, ss in sorted(steps.items())) if steps else ""
        h += table(["Kernel k", "CPU", "Session", "C_k, GB/s", "low, GB/s", "high, GB/s",
                    "predicted from, %", "to, %", "measured, %", "against the range",
                    "asmread median, GB/s", "k median, GB/s"], rows,
                   caption="Table 6b. Supplementary, defined after the data was seen. Gain of asmread over a slow "
                           "kernel k at 8 MiB: predicted range from two rates, and measured.")
        h += ("<ul class='note'>"
              "<li>C_k is the cell median of k at 32 KiB. Every other rate is a cell value at 8 MiB.</li>"
              "<li>Low and high are the two levels of asmread at 8 MiB.</li>"
              "<li>Predicted and measured are gains of asmread over k. The next column says whether the measured "
              "gain lies inside the predicted range.</li>"
              "<li>The asmread cell is that of step YF of the same session. If step YF is missing, it is the cell "
              "of step ZD without the evict option.</li>"
              "<li>The evict option (<code>--evict-mb</code>) writes other memory before the run (section 6).</li>%s"
              "<li>Old read is the cell of step S2.</li>"
              "<li>The comparison uses the unrounded values.</li></ul>" % used)
        if n_all:
            h += ("<ul><li><b>Result:</b> the measured gain lies inside the predicted range in %d of the %d cells "
                  "that exist%s.</li>"
                  "<li>The test can fail in one way only: the kernel k does not keep its 32 KiB rate at 8 MiB.</li>"
                  "<li>The asmread median always lies between the two asmread levels.</li></ul>" % (
                      n_in, n_all, (" (outside: %s)" % esc(", ".join(outside))) if outside else ""))
        return h

    # ================================================================== section 5
    def fig_dose(self):
        svgs = []
        for cpu in CPUS:
            p = Plot((-0.12, 1.2), (2.0, 2.96), H=350)
            p.frame()
            p.title("CPU %d" % cpu, "cycles per 64 B line (axis starts at 2.0)")
            p.yticks([2.0, 2.2, 2.4, 2.6, 2.8], "%.1f")
            p.xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], title="r: lines that enter L2 from the SLC, per line read")
            p.area([(p.X(0), p.Y(2.05)), (p.X(1), p.Y(2.10 + 0.50 - 0.05)), (p.X(1), p.Y(2.10 + 0.69 + 0.05)),
                    (p.X(0), p.Y(2.15))], C_BAND, 0.9)
            p.raw_text(p.fx1 - 6, p.Y(2.16), "grey band: the prediction,", "end", 11, "lab")
            p.raw_text(p.fx1 - 6, p.Y(2.16) + 13, "fixed before the data", "end", 11, "lab")
            drew = False
            for ses in SESSIONS:
                old = self.zs("oldread", cpu, ses)
                asm = self.zs("asmread", cpu, ses)
                if not asm:
                    continue
                drew = True
                for r in old:
                    p.dot(p.X(r["r"]), p.Y(r["cyc"]), C_OLD, SHAPE[ses], r=3.2,
                          tip="old read %s session %d: r %.3f, %.3f cycles" % (r["size"], ses, r["r"], r["cyc"]))
                for r in asm:
                    p.dot(p.X(r["r"]), p.Y(r["cyc"]), C_NEW, SHAPE[ses], r=4,
                          tip="asmread %s session %d: r %.3f, %.3f cycles, %s the band" % (
                              r["size"], ses, r["r"], r["cyc"], "inside" if r["inside"] else "outside"))
                for r in sorted(asm, key=lambda r: (r["inside"], -r["size_bytes"])):
                    t = r["size"] + ("" if r["inside"] else " outside") + (" (s2)" if ses == 2 else "")
                    p.label(p.X(r["r"]), p.Y(r["cyc"]), t, "L AL BL R BR AR A B", cls="lab" if r["inside"] else "lab b")
                if old and ses == min(s for s in SESSIONS if self.zs("oldread", cpu, s)):
                    o = old[0]
                    p.raw_text(p.X(0.02), p.Y(o["cyc"]) + 17, "old read %.2f" % o["cyc"], fs=11, cls="lab")
            if not drew:
                p.raw_text((p.fx0 + p.fx1) / 2, (p.fy0 + p.fy1) / 2, "step ZS: no data", "middle", 12)
            svgs.append(self.draw([p], "Cycles per line against r on CPU %d with the predicted band" % cpu))
        Z = self.J.get("ZS", {}).get("rule", {})
        parts = []
        chk = sum(c.get("oldread_checked") or 0 for c in Z.values())
        fail = sum(c.get("oldread_fails") or 0 for c in Z.values())
        for key in sorted(Z):
            m = re.match(r"cpu(\d+)/s(\d+)", key)
            parts.append("<li>CPU %s, session %s: %d of the %d counted sizes %s outside the band.</li>" % (
                m.group(1), m.group(2), Z[key]["outside"], Z[key]["evaluated"],
                "lies" if Z[key]["outside"] == 1 else "lie"))
        if parts:
            t = "The cost of the new loop rises with r, inside the band that was fixed before the data."
            detail = ("<p class='note'>Detail of the takeaway, per CPU and session:</p><ul class='note'>%s"
                      "<li><b>Old read:</b> it stays within 0.02 cycles of 2.671 cycles at %d of its %d points with r "
                      "below 0.83.</li></ul>" % ("".join(parts), chk - fail, chk))
        else:
            t, detail = "No data.", ""
        leg = [(sw(C_NEW), "asmread, labelled with the buffer size"), (sw(C_OLD), "old read"),
               ("<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'><rect x='1' y='3' width='14' height='8' fill='%s'/></svg>" % C_BAND,
                "predicted band: 2.10 + 0.50 r - 0.05 to 2.10 + 0.69 r + 0.05")] + session_legend()
        return figure("Figure 4. Size as the dose: cycles per line against r (step ZS)", leg, panels(svgs), t,
                      detail +
                      "<p class='note'>How to read the figure:</p><ul class='note'>"
                      "<li>The cycle axis starts at 2.0 cycles.</li>"
                      "<li>A label gives the buffer size of the blue point.</li>"
                      "<li>The buffer size was the variable that the test set.</li>"
                      "<li>r and the cycles per line were both measured.</li>"
                      "<li>So the figure shows that the two rise together with the size.</li>"
                      "<li>It does not show by itself that the lines from the SLC cause the extra cycles.</li></ul>")

    def sec5(self):
        Z = self.J.get("ZS", {})
        h = "<h2>5. Test 2: size as the dose</h2><ul>"
        h += ("<li><b>Hypothesis H1c says:</b> each line that must come from the SLC costs a fixed number of extra "
              "cycles.</li>")
        h += "<li>The buffer size sets how many lines come from the SLC. So the size is the dose.</li>"
        h += ("<li><b>The band:</b> it is the range of cycles per line that H1c predicts for each r. It was fixed "
              "before step <code>ZS</code> ran.</li>")
        h += ("<li>The band has two slopes: 0.50 and 0.69 cycles per line from the SLC. They came from the high and "
              "the low level at 8 MiB in earlier steps %s.</li>" % self.R("decisions"))
        h += ("<li><b>The rule:</b> it counts the 11 sizes other than 1 and 8 MiB. H1c in this form is contradicted "
              "if more than 2 of them lie outside the band on both CPUs in both sessions %s.</li></ul>" % self.sref("ZS"))
        h += self.one_session("ZS") + self.fig_dose()
        rows = []
        for cpu, ses in self.cells():
            c = Z.get("rule", {}).get("cpu%d/s%d" % (cpu, ses))
            if not c:
                rows.append([TH(cpu), TH(ses), MISS(7)])
                continue
            out = [s for s, d in c["sizes"].items() if d["counted"] and not d["inside"]]
            rows.append([TH(cpu), TH(ses), V(c["outside"], 0), V(c["evaluated"], 0), TX(", ".join(out) or "none"),
                         V(c["intercept"], 3), V(c["slope"], 3), V(c["oldread_fails"], 0), V(c["oldread_checked"], 0)])
        h += table(["CPU", "Session", "sizes outside the band", "sizes counted", "which", "fitted line: cycles at r = 0",
                    "fitted line: cycles per unit of r", "old read: sizes more than 0.02 from 2.671 cycles",
                    "old read: sizes checked (r below 0.83)"], rows,
                   caption="Table 9. Step ZS against its rule. The fitted line is descriptive. Table 1 holds every point.")
        h += "<ul><li><b>Verdict as recorded:</b> %s %s.</li></ul>" % (esc(Z.get("overall", "no data")), self.R("final8"))
        return h

    # ================================================================== section 6
    def fig_prefetch(self):
        svgs = []
        kernels = ["asmread", "read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "oldread"]
        allrates = []
        for r in self.rows("prefetch.YC"):
            if r["kernel"] in kernels and r["size"] in ("1M", "8M"):
                allrates.append(r["yf_median"] if r.get("yf_median") is not None else r["yc_rate"])
        if not allrates:
            return "<p class='miss'>Steps YC and YF: no data.</p>"
        lo = 5 * math.floor(min(allrates) / 5.0) - 5
        hi = 5 * math.ceil(max(allrates) / 5.0) + 5
        for size in ("1M", "8M"):
            for cpu, ses in self.cells():
                rs = {r["kernel"]: r for r in self.rows("prefetch.YC", size=size, cpu=cpu, session=ses)}
                if not rs:
                    continue
                rh = 24
                H = 36 + rh * len(kernels) + 44
                a = Plot((0, 0.6), (0, 1), H=H, ml=86, mr=400 - 214)
                b = Plot((lo, hi), (0, 1), H=H, ml=246, mr=12)
                a.frame()
                b.frame()
                a.title("%s MiB, CPU %d, session %d" % (size[:-1], cpu, ses))
                a.xticks([0, 0.2, 0.4, 0.6], title="L1 long misses per line", grid=True)
                b.xticks([t for t in range(int(lo), int(hi) + 1, 10)], title="rate, GB/s (from %d)" % lo, grid=True)
                for i, k in enumerate(kernels):
                    r = rs.get(k)
                    y = a.fy0 + rh * (i + 0.5)
                    a.raw_text(a.fx0 - 6, y + 4, "old read" if k == "oldread" else k, "end", 11, "ax", False)
                    if not r:
                        continue
                    col = C_OLD if k == "oldread" else C_NEW
                    m = r["per64"]["l1d_cache_lmiss_rd"]
                    a.bar(a.X(0), y, a.X(min(m, 0.6)), col, tip="%s: %.4f L1 long misses per line" % (k, m))
                    a.label(a.X(min(m, 0.6)), y, "%.3f" % m, "R", d=5)
                    rate = r["yf_median"] if r.get("yf_median") is not None else r["yc_rate"]
                    b.path([(b.fx0, y), (b.fx1, y)], C_GRID, 1)
                    b.dot(b.X(rate), y, col, SHAPE[ses], r=4.5, tip="%s: %.2f GB/s" % (k, rate))
                    b.label(b.X(rate), y, "%.1f" % rate, "R L", d=8)
                svgs.append(self.draw([a, b], "L1 long misses per line and rate per kernel at %s, CPU %d, session %d" % (size, cpu, ses)))
        a1 = self.one("prefetch.YC", kernel="asmread", size="1M")
        p1 = [r for r in self.rows("prefetch.YC", size="1M") if r["kernel"].startswith("read_pf")]
        if a1 and p1 and a1.get("yf_median") is not None and all(r.get("yf_median") is not None for r in p1):
            t = "At 1 MiB fewer misses did not come with a higher rate."
            detail = ("<p class='note'>Detail of the takeaway:</p><ul class='note'>"
                      "<li><b>Misses per line at 1 MiB:</b> the prefetch kernels have %.3f to %.3f. "
                      "<code>asmread</code> has %.3f.</li>"
                      "<li><b>Rate at 1 MiB:</b> the prefetch kernels run at %.1f to %.1f GB/s. <code>asmread</code> "
                      "runs at %.1f GB/s.</li>" % (
                          min(r["per64"]["l1d_cache_lmiss_rd"] for r in p1), max(r["per64"]["l1d_cache_lmiss_rd"] for r in p1),
                          a1["per64"]["l1d_cache_lmiss_rd"], min(r["yf_median"] for r in p1), max(r["yf_median"] for r in p1),
                          a1["yf_median"]))
            worse = total = 0
            for r in self.rows("prefetch.YC", size="8M"):
                if r["kernel"].startswith("read_pf") and r.get("yf_median") is not None:
                    a8 = self.one("prefetch.YC", kernel="asmread", size="8M", cpu=r["cpu"], session=r["session"])
                    if a8 and a8.get("yf_median") is not None:
                        total += 1
                        worse += r["yf_median"] < a8["yf_median"]
            if total:
                detail += ("<li><b>Rate at 8 MiB:</b> %d of %d prefetch cells are slower than <code>asmread</code> of "
                           "the same CPU and session.</li>" % (worse, total))
            detail += "</ul>"
        else:
            t, detail = "No data.", ""
        leg = [(sw(C_NEW), "load-only kernels: asmread and asmread with one software prefetch per line"),
               (sw(C_OLD), "old read")] + session_legend()
        return figure("Figure 5. First-level long misses and rate of the prefetch family (steps YC and YF)", leg, panels(svgs), t,
                      detail +
                      "<p class='note'>How to read the figure:</p><ul class='note'>"
                      "<li><b>Left frame:</b> misses from step YC (one counted process per cell).</li>"
                      "<li><b>Right frame:</b> cell median of step YF (6 processes). The rate axis does not start at 0.</li>"
                      "<li><b>Old read:</b> it is not in step YF. Its rate here is the rate of its YC process.</li>"
                      "<li><b>Kernel names:</b> <code>read_pfN</code> prefetches N bytes ahead. <code>read_1pl</code> "
                      "(one load per line) is in table 10 only.</li>"
                      "<li><b>Limit:</b> step YF has no kernel with the code layout of the prefetch kernels and no "
                      "prefetch.</li>"
                      "<li>So the lower rate of the prefetch kernels can also come from the added instruction or from "
                      "the layout.</li></ul>")

    def sec6_sup(self):
        """supplementary: the prefetch family at 1 MiB and at 8 MiB, under the recorded verdict of rule 3"""
        S = self.sup("prefetch_1M")
        h = self.sup_lead("what the prefetch kernels do at 1 MiB and at 8 MiB")
        h += ("<ul><li><b>Scope:</b> rule 3 reads the four prefetch kernels at 8 MiB only. This evaluation reads them at 1 MiB and at "
              "8 MiB (table 11a).</li>")
        for size in ("1M", "8M"):
            t = (S.get("summary_text") or {}).get(size)
            if t:
                h += "<li><b>As recorded.</b> Result: %s.</li>" % esc(t)
        s1 = next((x for x in S.get("summary", []) if x["size"] == "1M"), None)
        if s1 and s1["cells_lower"] == s1["cells"] and s1["removed_pct_min"] >= 90.0:
            h += ("<li>So at 1 MiB the removal of more than 90 % of the first-level long misses does not raise the "
                  "rate.</li>"
                  "<li>Hypothesis H1b is stated for 8 MiB. So this result is not a test of H1b by its rule.</li>")
        h += "<li>The recorded verdict of H1b stays as it is above.</li>"
        t32, s32 = (S.get("summary_text") or {}).get("32K"), S.get("at_32K") or {}
        h += ("<li><b>Limit:</b> a prefetch kernel has one more instruction per line than <code>asmread</code>. Step "
              "YF has no kernel with that added instruction and no prefetch effect.</li>")
        if t32:
            h += "<li><b>As recorded.</b> Result: %s.</li>" % esc(t32)
            if s32.get("cells") and s32.get("cells_lower") == s32["cells"]:
                h += ("<li>So the prefetch kernels are slower than <code>asmread</code> also where the data is in "
                      "the first-level cache.</li>"
                      "<li>The lower rate at 1 MiB can therefore come from the added instruction and not from the "
                      "misses. This data cannot separate the two.</li>")
        h += "</ul>"
        rows = []
        kern = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048"]
        for size, name in (("1M", "1 MiB"), ("8M", "8 MiB")):
            for ses in SESSIONS:
                rs = [x for x in S.get("rows", []) if x["size"] == size and x["session"] == ses]
                if not rs:
                    rows.append([TH("all"), TH(name), TH("2, 41"), TH(ses), MISS(5)])
                    continue
                for k in kern:
                    for cpu in CPUS:
                        r = next((x for x in rs if x["kernel"] == k and x["cpu"] == cpu), None)
                        if r:
                            rows.append([TH(k), TH(name), TH(cpu), TH(ses), V(r["share_kept"], 3), V(r["removed_pct"], 1),
                                         V(r["rate"]), V(r["asmread_rate"]), V(r["difference"])])
        h += table(["Kernel", "Size", "CPU", "Session", "share of the asmread misses that the kernel keeps",
                    "misses removed, %", "rate of the kernel, GB/s", "rate of asmread, GB/s",
                    "kernel minus asmread, GB/s"], rows,
                   caption="Table 11a. Supplementary, defined after the data was seen. Prefetch kernels against "
                           "asmread. Misses: first-level long misses of step YC, one process per cell. Rates: cell "
                           "medians of step YF, 6 processes per cell.")
        return h

    def sec6(self):
        P = self.J.get("prefetch", {})
        E = self.J.get("evict", {})
        h = "<h2>6. What does not set the limit</h2>"
        h += ("<p>This section holds the two candidate limits that the tests did not support. The verdict lines say "
              "how far each statement is established by its rule.</p>")
        h += "<h3>6.1 The count of first-level cache misses (hypothesis H1b)</h3><ul>"
        ma = [r["per64"]["l1d_cache_lmiss_rd"] for r in self.rows("prefetch.YC", kernel="asmread") if r["size"] in ("1M", "8M")]
        mo = [r["per64"]["l1d_cache_lmiss_rd"] for r in self.rows("prefetch.YC", kernel="oldread") if r["size"] in ("1M", "8M")]
        if ma and mo:
            h += ("<li><b>The observation:</b> in step YC <code>asmread</code> has %s to %s first-level long misses "
                  "per line at 1 MiB and at 8 MiB. Old read has %s to %s.</li>"
                  "<li><b>Hypothesis H1b said:</b> these misses limit the new loop.</li>" % (
                      fnum(min(ma), 3), fnum(max(ma), 3), fnum(min(mo), 3), fnum(max(mo), 3)))
        else:
            h += "<li><b>Hypothesis H1b said:</b> the first-level long misses limit the new loop.</li>"
        h += ("<li><b>The test:</b> four kernels add one software prefetch per line to the <code>asmread</code> loop. "
              "A software prefetch is an instruction that asks the core to load a line before the loop needs it %s.</li>"
              % self.R("decisions"))
        h += ("<li><b>The rule:</b> H1b is rejected if one kernel meets both conditions %s:<ul>"
              "<li>The kernel has at most half of the <code>asmread</code> misses at 8 MiB.</li>"
              "<li>Its rate is less than 1.0 GB/s above <code>asmread</code>.</li></ul></li></ul>" % self.sref("YC", "YF"))
        h += self.one_session("YC", "YF") + self.fig_prefetch()
        rows = []
        order = {"1M": 0, "8M": 1, "16M": 2}
        ycs = sorted(self.rows("prefetch.YC"), key=lambda r: (order.get(r["size"], 9), r["kernel"], r["cpu"], r["session"]))
        for ses in SESSIONS:
            rs = [r for r in ycs if r["session"] == ses]
            if not rs:
                rows.append([TH("all"), TH("all"), TH("2, 41"), TH(ses), MISS(7)])
            for r in rs:
                sh = self.one("prefetch.share", kernel=r["kernel"], size=r["size"], cpu=r["cpu"], session=ses)
                rows.append([TH(r["kernel"]), TH(r["size"]), TH(r["cpu"]), TH(ses), V(r["per64"]["cpu_cycles"], 3),
                             V(r["per64"]["l1d_cache_lmiss_rd"], 4), V(sh["share"] if sh else None, 3),
                             V(r["per64"]["l2d_cache_refill"], 3), V(r["yc_rate"]), V(r.get("yf_median")), V(r.get("yf_p95"))])
        h += table(["Kernel", "Size", "CPU", "Session", "cycles per line", "L1 long misses per line",
                    "share of the asmread misses", "L2 refills per line", "rate of the counted process, GB/s",
                    "YF cell median, GB/s", "YF cell p95, GB/s"], rows,
                   caption="Table 10. Steps YC (counters, one process per cell) and YF (rates, 6 processes per cell).")
        rows = []
        for cpu, ses in self.cells():
            c = P.get("rule3", {}).get("cpu%d/s%d" % (cpu, ses))
            if not c:
                rows.append([TH(cpu), TH(ses), MISS(3)])
                continue
            rows.append([TH(cpu), TH(ses), V(c["asmread_high"]), TX(", ".join(c["halving"]) or "none"), TX(c["verdict"])])
        h += table(["CPU", "Session", "asmread high level (YF p95 at 8 MiB), GB/s", "kernels with at most half of the misses",
                    "verdict of rule 3 of round 3, as recorded"], rows, caption="Table 11. Rule 3 of round 3 per CPU and session.")
        h += "<ul><li><b>Overall, as recorded:</b> %s %s.</li></ul>" % (esc(P.get("overall", "no data")), self.R("final8"))
        h += self.sec6_sup()
        # evict
        h += "<h3>6.2 Dirty lines in the caches (hypothesis H1d, steps ZC and ZD)</h3><ul>"
        h += ("<li><b>The observation:</b> at 8 MiB each line that enters the second-level cache pushes one line back "
              "to the SLC. The counter event is <code>l2d_cache_wb</code> (write-back).</li>")
        h += "<li><b>Hypothesis H1d said:</b> clean lines would make this cheaper.</li>"
        h += ("<li><b>Dirty and clean:</b> a dirty line holds data that is newer than the copy in memory. A clean line "
              "equals that copy.</li>")
        h += ("<li><b>The test:</b> the option <code>--evict-mb 512</code> writes 512 MiB of other memory twice "
              "before the run.</li>")
        h += ("<li>The aim was to push the buffer out of the caches. Then its lines come back clean %s.</li>" % self.R("decisions"))
        h += ("<li><b>The rule:</b> it first checks that the option changed the write-backs. With evict, the "
              "write-backs per line must fall below 0.2 %s.</li></ul>" % self.sref("ZC", "ZD"))
        h += self.one_session("ZC", "ZD")
        rows = []
        zc = sorted(self.rows("evict.ZC"), key=lambda r: (r["kernel"], order.get(r["size"], 9), r["cpu"], r["session"], r["evict_mb"]))
        for ses in SESSIONS:
            rs = [r for r in zc if r["session"] == ses]
            if not rs:
                rows.append([TH("all"), TH("all"), TH("2, 41"), TH(ses), TH("0, 512"), MISS(6)])
            for r in rs:
                rows.append([TH(r["kernel"]), TH(r["size"]), TH(r["cpu"]), TH(ses), TH(r["evict_mb"]),
                             V(r["per64"]["cpu_cycles"], 3), V(r["per64"]["l1d_cache_lmiss_rd"], 4),
                             V(r["per64"]["l2d_cache_refill"], 4), V(r["per64"]["l2d_cache_wb"], 4),
                             VL(r["l2d_cache_wb_per_process"], 3), VL(r["rates"])])
        h += table(["Kernel", "Size", "CPU", "Session", "evict, MiB", "cycles per line", "L1 long misses per line",
                    "L2 refills per line", "L2 write-backs per line", "write-backs per line of each process",
                    "rate of each process, GB/s"], rows,
                   caption="Table 12. Step ZC: counts per line, median over the 2 processes of a cell.")
        rows = []
        zd = sorted(self.rows("evict.ZD"), key=lambda r: (order.get(r["size"], -1), r["kernel"], r["cpu"], r["session"]))
        for ses in SESSIONS:
            rs = [r for r in zd if r["session"] == ses]
            if not rs:
                rows.append([TH("all"), TH("all"), TH("2, 41"), TH(ses), MISS(6)])
            for r in rs:
                rows.append([TH(r["kernel"]), TH(r["size"]), TH(r["cpu"]), TH(ses), V(r["plain"]["median"]),
                             V(r["evict"]["median"]), V(r["median_diff"]), V(r["plain"]["p95"]), V(r["evict"]["p95"]),
                             V(r["p95_diff"])])
        h += table(["Kernel", "Size", "CPU", "Session", "median without evict", "median with evict", "difference",
                    "p95 without evict", "p95 with evict", "difference"], rows,
                   caption="Table 13. Step ZD: cell values in GB/s, 6 processes per cell, without and with --evict-mb 512.")
        h += "<ul>"
        for ses in SESSIONS:
            c = E.get("rule1", {}).get("s%d" % ses)
            if c:
                h += "<li><b>Rule 1 of round 4, session %d, as recorded:</b> %s.</li>" % (ses, esc(c["verdict"]))
            else:
                h += "<li class='miss'>Rule 1 of round 4, session %d: %s.</li>" % (ses, MISSING)
        h += "<li><b>Overall, as recorded:</b> %s %s.</li></ul>" % (esc(E.get("overall", "no data")), self.R("final8"))
        if str(E.get("overall", "")).startswith("Insufficient data"):
            wb = {ev: [r["per64"]["l2d_cache_wb"] for r in self.rows("evict.ZC", kernel="asmread", size="8M") if (r["evict_mb"] > 0) == ev]
                  for ev in (False, True)}
            dp = [r["p95_diff"] for r in self.rows("evict.ZD", size="8M") if r["kernel"] in ("asmread", "read") and r.get("p95_diff") is not None]
            h += "<p><b>Insufficient data.</b></p><ul>"
            if wb[False] and wb[True]:
                h += ("<li><b>Write-backs:</b> at 8 MiB <code>asmread</code> has %s to %s write-backs per line with "
                      "evict and %s to %s without.</li>" % (
                          fnum(min(wb[True]), 3), fnum(max(wb[True]), 3), fnum(min(wb[False]), 3), fnum(max(wb[False]), 3)))
            if dp:
                h += ("<li><b>Rates:</b> the p95 rate of <code>asmread</code> and of <code>read</code> at 8 MiB changes "
                      "by %s to %s GB/s with evict.</li>" % (fnum(min(dp)), fnum(max(dp))))
            h += ("<li>Two readings fit this result. The data cannot separate them %s.<ul>"
                  "<li><b>Reading 1:</b> the evict step did not move the buffer out of the caches. Then the test did "
                  "not change the state of the lines.</li>"
                  "<li><b>Reading 2:</b> the second-level cache writes back a clean line in the same way as a dirty "
                  "line. Then H1d is wrong.</li></ul></li>"
                  "<li><b>The measurement that would decide:</b> a counter of the SLC or of the mesh that shows "
                  "whether a write-back carries data. It needs root.</li>"
                  "<li>The mesh is the network between the cores and the SLC.</li></ul>" % self.R("decisions"))
        return h

    # ================================================================== section 7
    def read_s4(self, folder):
        path = os.path.join(self.results, folder, "S4.csv")
        procs, cur = [], None
        try:
            with open(path) as f:
                for line in f:
                    if line.startswith("-- step"):
                        m = re.search(r" idx (\d+) tag (\S+)", line)
                        cur = {"idx": int(m.group(1)), "tag": m.group(2), "w": []}
                        procs.append(cur)
                    elif line.startswith("W,") and cur is not None:
                        q = line.rstrip("\n").split(",")
                        if q[2] == "target":
                            cur["w"].append((int(q[7]), int(q[8]), int(q[6])))
        except (OSError, AttributeError, ValueError, IndexError):
            return None
        return procs

    def fig_traces(self):
        ses = next((s for s in SESSIONS if self.has("S4", s)), None)
        if ses is None:
            return "<p class='miss'>Step S4: no data.</p>"
        folder = self.folders("S4", ses)[0]
        procs = self.read_s4(folder)
        if not procs:
            self.notes.append("figure 6 (traces of step S4) not drawn: %s/S4.csv could not be read" % folder)
            return "<p class='miss'>Figure 6 is not drawn: the raw file <code>%s/S4.csv</code> could not be read.</p>" % esc(folder)
        svgs, used = [], []
        for cpu in CPUS:
            p = Plot((0, 60), (66, 72.5), H=270, mr=96)
            p.frame()
            p.title("CPU %d, session %d" % (cpu, ses), "rate, GB/s, per 0.3 s window (axis starts at 66)")
            p.yticks([66, 67, 68, 69, 70, 71, 72], "%d")
            p.xticks([0, 10, 20, 30, 40, 50, 60], title="time since process start, s")
            for kernel, col in (("oldread", C_OLD), ("asmread", C_NEW)):
                pr = next((q for q in procs if q["tag"] == "%s-cpu%d-p1" % (kernel, cpu)), None)
                if not pr or not pr["w"]:
                    continue
                used.append("%s (idx %d)" % (pr["tag"], pr["idx"]))
                pts = []
                for t0, t1, by in pr["w"]:
                    rate = by / float(t1 - t0)
                    y = p.Y(min(max(rate, 66.0), 72.5))
                    pts += [(p.X(t0 / 1e9), y), (p.X(min(t1 / 1e9, 60)), y)]
                p.path(pts, col, 1.4)
            lv = self.one("levels.rows", step="S4", kernel="asmread", cpu=cpu, session=ses)
            side = []
            if lv and lv.get("high") is not None:
                side.append((p.Y(lv["high"]) + 4, "high %.1f" % lv["high"]))
                side.append((p.Y(lv["low"]) + 4, "low %.1f" % lv["low"]))
            lo = self.one("levels.rows", step="S4", kernel="oldread", cpu=cpu, session=ses)
            if lo and lo.get("one_level_rates"):
                side.append((p.Y(med(lo["one_level_rates"])) + 4, "old read %.1f" % med(lo["one_level_rates"])))
            for y, t in spread_labels(side, p.fy0 + 10, p.fy1):
                p.raw_text(p.fx1 + 5, y, t, "start", 11, "lab b", False)
            svgs.append(self.draw([p], "60 second rate traces of asmread and old read at 8 MiB on CPU %d" % cpu))
        leg = [("<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'><path d='M1,7 L15,7' stroke='%s' stroke-width='2'/></svg>" % C_OLD, "old read"),
               ("<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'><path d='M1,7 L15,7' stroke='%s' stroke-width='2'/></svg>" % C_NEW, "asmread")]
        return figure("Figure 6. Two example 60 s traces at 8 MiB per CPU (step S4)", leg, panels(svgs),
                      "In these example processes asmread changes between two rates inside one process. Old read "
                      "keeps one rate for 60 s.",
                      "<ul class='note'>"
                      "<li>The rate axis starts at 66 GB/s.</li>"
                      "<li>The labels at the right edge give the low and the high level of asmread and the rate of "
                      "old read.</li>"
                      "<li>These labels are the medians over the processes of the cell (table 14).</li>"
                      "<li>The figure shows one process per kernel and CPU of the folder <code>%s</code> %s.</li>"
                      "<li>The processes are %s.</li>"
                      "<li>The number after a name is the position of the process in the step.</li>"
                      "</ul>" % (esc(folder), self.sref("S4"), esc(", ".join(used).replace("idx ", "number "))))

    def fig_pad(self):
        Y = self.J.get("YP", {})
        svgs = []
        ref_u = ((self.sup("yp_round1").get("reference") or {}).get("up") or {}).get("series") or []
        pads = sorted({p["pad"] for p in Y.get("processes", []) if not p["hot_copy"]})
        for cpu, ses in self.cells():
            procs = [p for p in Y.get("processes", []) if p["cpu"] == cpu and p["session"] == ses]
            if not procs:
                continue
            sh = {s["pad"]: s for s in Y.get("shift", []) if s["cpu"] == cpu and s["session"] == ses}
            any_s = next(iter(sh.values()), None)
            spacing = any_s["pad0_spacing"] if any_s else None
            u0 = min(any_s["pad0_ups"]) if any_s and any_s["pad0_ups"] else None
            rowsl = [(pd, False) for pd in pads] + [(0, True)]
            from_u = {x["pad"]: x["windows"] for x in self.sup("yp_round1").get("predicted", []) if x["kind"] == "up"}
            if not ref_u:
                from_u = {}
            rh = 30
            p = Plot((0, 100), (0, 1), H=36 + 14 + rh * len(rowsl) + 44, ml=92, mr=16)
            p.frame()
            p.title("CPU %d, session %d" % (cpu, ses))
            p.xticks([0, 20, 40, 60, 80, 100], title="window in which the rate goes up (0.3 s windows)", grid=True)
            for i, (pd, hot) in enumerate(rowsl):
                y = p.fy0 + 14 + rh * (i + 0.5)
                p.raw_text(p.fx0 - 6, y, "hot-copy" if hot else "pad %d B" % pd, "end", 11, "ax", False)
                if not hot and pd:
                    p.raw_text(p.fx0 - 6, y + 12, "predicted -%g" % (pd / 80.0), "end", 11, "ax", False)
                if not hot and pd in from_u:
                    for w in from_u[pd]:
                        p.dot(p.X(w), y, C_PRED, "o", hollow=True, r=6.5, tip="predicted window %g for pad %d" % (w, pd))
                elif not hot and spacing and u0 is not None:
                    k = -10
                    while True:
                        w = u0 + k * spacing - pd / 80.0
                        k += 1
                        if w < 0:
                            continue
                        if w >= 100:
                            break
                        p.dot(p.X(w), y, C_PRED, "o", hollow=True, r=6.5, tip="predicted window %g for pad %d" % (w, pd))
                rs = [q for q in procs if q["pad"] == pd and q["hot_copy"] == hot]
                for j, q in enumerate(rs):
                    yy = y + (j - (len(rs) - 1) / 2.0) * 7
                    for u in q["ups"]:
                        p.dot(p.X(u), yy, C_NEW, SHAPE[ses], r=2.6, tip="process idx %d, pad %d: up at window %d" % (q["idx"], pd, u))
                if pd == 0 and not hot and rs and rs[0]["ups"]:
                    for u in sorted(set(rs[0]["ups"])):
                        p.raw_text(p.X(u), y - 11, "%d" % u, "middle", 11, "lab")
            svgs.append(self.draw([p], "Up-switch windows for each record pad on CPU %d session %d" % (cpu, ses)))
        if not svgs:
            return "<p class='miss'>Step YP: no data.</p>"
        leg = [(sw(C_NEW), "measured: one dot for each up-switch, one line of dots for each process"),
               (sw(C_PRED, hollow=True), "predicted: the up windows of the 60 s runs of round 1 (step S4) moved earlier "
                                         "by pad / 80 windows" if ref_u else
                "predicted: the pad 0 series moved earlier by pad / 80 windows")] + session_legend()
        v = Y.get("verdict", {})
        sh = Y.get("shift", [])
        t = ("By the recorded rule, the up-switches move with the pad as predicted in %d of %d pad and CPU cells." % (sum(1 for x in sh if x["match"]), len(sh))) if sh else "No data."
        rule = ""
        if sh:
            rule = ("<li>The recorded rule compares a cell with the pad 0 series of the same CPU and session.</li>"
                    "<li>A cell matches if its up-switches lie at these pad 0 windows moved earlier by pad / 80 "
                    "windows.</li>"
                    "<li>One record is 80 bytes.</li>")
            rule += "".join("<li>Verdict of rule 2 as recorded, session %s: %s.</li>" % (k[1:], esc(x))
                            for k, x in sorted(v.items()))
        sp = sorted({x["pad0_spacing"] for x in sh if x.get("pad0_spacing")})
        if ref_u:
            src = ("<li>The hollow marks start from the up windows of the 60 s runs of round 1: %s.</li>"
                   "<li>Each hollow mark is such a window minus pad / 80. Marks outside the windows 0 to 99 are "
                   "left out.</li>"
                   "<li>The same marks are drawn in both sessions.</li>"
                   "<li>This reference was chosen after the data was seen (supplementary evaluation below table "
                   "16).</li>"
                   "<li>The recorded rule does not use this reference. It uses the pad 0 processes of the same CPU and "
                   "session (table 16).</li>"
                   % ", ".join("%d" % u for u in ref_u))
        else:
            src = ("<li>The predicted series continues the pad 0 series with its own spacing (est. beyond window "
                   "90).</li>")
        return figure("Figure 7. Record pad against the windows of the up-switches (step YP, asmread at 8 MiB, 100 windows)", leg, panels(svgs), t,
                      "<ul class='note'>%s"
                      "<li>The pad 0 ups repeat every %s windows. This distance is the spacing.</li>"
                      "<li>So a shift is known only up to a multiple of this spacing.</li>"
                      "<li>Example: the data cannot tell a shift of 26 windows from a shift of 3 windows.</li>"
                      "%s"
                      "<li>A row without dots means that the processes showed no up-switch.</li>"
                      "<li>Row &quot;hot-copy&quot; is pad 0 with the option <code>--hot-copy</code>. With this "
                      "option the loop does not touch the record inside a window.</li>"
                      "<li>No prediction is drawn for the row &quot;hot-copy&quot;.</li>"
                      "</ul>" % (rule, " or ".join("%g" % x for x in sp) or "NA", src))

    def read_h2(self, folder):
        path = os.path.join(self.results, folder, "H2.csv")
        procs, cur = [], None
        try:
            with open(path) as f:
                for line in f:
                    m = re.match(r"-- binary (\S+) .* cpus (\S+) ", line)
                    if m:
                        cur = {"binary": m.group(1), "cpu": m.group(2), "rates": [], "ok": True}
                        procs.append(cur)
                    elif line.startswith("-- killed") or line.startswith("-- failed"):
                        if cur:
                            cur["ok"] = False
                    elif cur is not None and line.startswith("read,"):
                        q = line.split(",")
                        if q[3].isdigit():
                            cur["rates"].append(float(q[6]))
        except (OSError, ValueError, IndexError):
            return None
        return [p for p in procs if p["ok"]]

    def fig_h2(self):
        H = self.J.get("H2", {})
        rowsj = H.get("rows", [])
        if not rowsj:
            return "<p class='miss'>Step H2: no data.</p>"
        data = {}
        for ses in SESSIONS:
            for folder in self.folders("H2", ses):
                pr = self.read_h2(folder)
                if pr is None:
                    self.notes.append("figure 8 (step H2): %s/H2.csv could not be read" % folder)
                    continue
                for q in pr:
                    data.setdefault((q["cpu"], ses, q["binary"]), []).extend(q["rates"])
        if not data:
            return "<p class='miss'>Figure 8 is not drawn: the raw files <code>H2.csv</code> could not be read.</p>"
        cpus = sorted({r["cpu"] for r in rowsj}, key=int)
        rowsl = [(c, s) for c in cpus for s in SESSIONS if (c, s, "bw_new") in data]
        allv = [v for vs in data.values() for v in vs]
        lo, hi = math.floor(min(allv) * 2) / 2.0 - 0.5, math.ceil(max(allv) * 2) / 2.0 + 0.5
        rh = 36
        p = Plot((lo, hi), (0, 1), H=40 + rh * len(rowsl) + 44, ml=84, mr=100, mt=40)
        p.frame()
        p.title("CPUs 0, 2 and 41, sessions s1 and s2")
        p.xticks([t for t in range(int(math.ceil(lo)), int(hi) + 1)], title="rate of one repetition, GB/s (axis starts at %g)" % lo, grid=True)
        for thr, txt, anc in ((69.5, "low: at most 69.5", "end"), (70.5, "high: at least 70.5", "start")):
            p.path([(p.X(thr), p.fy0), (p.X(thr), p.fy1)], C_INK2, 1, dash="4 3")
            p.raw_text(p.X(thr) + (-3 if anc == "end" else 3), p.fy0 - 5, txt, anc, 11, "ax", False)
        for i, (c, s) in enumerate(rowsl):
            y = p.fy0 + rh * (i + 0.5)
            p.raw_text(p.fx0 - 6, y + 4, "CPU %s, s%d" % (c, s), "end", 11, "ax", False)
            for j, v in enumerate(data.get((c, s, "bw_old"), [])):
                p.dot(p.X(v), y - 8 + ((j * 7) % 5 - 2) * 1.2, C_OLD, r=2.4, opacity=0.75)
            for j, v in enumerate(data.get((c, s, "bw_new"), [])):
                p.dot(p.X(v), y + 7 + ((j * 3) % 7 - 3) * 1.3, C_NEW, r=2.4, opacity=0.75)
            r = next((r for r in rowsj if r["cpu"] == c and r["session"] == s), None)
            if r:
                p.raw_text(p.fx1 + 6, y - 2, "gain %.2f %%" % r["median_gain_pct"], "start", 11, "lab b", False)
                p.raw_text(p.fx1 + 6, y + 11, "%d low, %d high" % (r["low"], r["high"]), "start", 11, "lab", False)
        v = H.get("verdict", {})
        per = []
        for c in cpus:
            rs = [r for r in rowsj if r["cpu"] == c]
            rng = lambda xs, f: (f % xs[0]) if min(xs) == max(xs) else ((f + " to " + f) % (min(xs), max(xs)))
            per.append("<li><b>CPU %s:</b> %s of %s new-read repetitions are low and %s are high. The median gain "
                       "is %s %%.</li>" % (
                c, rng([r["low"] for r in rs], "%d"), rng([r["new_repetitions"] for r in rs], "%d"),
                rng([r["high"] for r in rs], "%d"), rng([r["median_gain_pct"] for r in rs], "%.2f")))
        t = ("Verdict of the H2 rule as recorded: %s." % (
            ", ".join("CPU %s %s" % (k[3:], esc(x)) for k, x in sorted(v.items(), key=lambda kv: int(kv[0][3:])))))
        leg = [(sw(C_OLD), "old read, binary bw_old: one dot for each repetition"),
               (sw(C_NEW), "new read, binary bw_new: one dot for each repetition")]
        return figure("Figure 8. The original program at 8 MiB (step H2)", leg, panels([self.draw([p], "Repetition rates of the original program per CPU and session")]), t,
                      "<ul>%s<li>A range covers the sessions.</li></ul>"
                      "<ul class='note'>"
                      "<li>The rate axis does not start at 0.</li>"
                      "<li>A repetition is &quot;low&quot; at or below 69.5 GB/s and &quot;high&quot; at or above "
                      "70.5 GB/s (the dashed lines).</li>"
                      "<li>The gain of one pair of neighbouring processes is new / old - 1. The printed gain is the "
                      "median over the 12 pairs.</li>"
                      "<li>Dots are spread vertically inside a row. This keeps equal rates visible.</li>"
                      "<li>Hypothesis H2 says: the original gain of 0.94 %% was measured at the low level.</li>"
                      "<li>&quot;Supported&quot; on a CPU means two things:<ul>"
                      "<li>At least 75 %% of its new-read repetitions are low in both sessions.</li>"
                      "<li>The gain of the low pairs is within 1.5 percentage points of 0.94 %%.</li></ul></li>"
                      "<li>&quot;Rejected&quot; means: fewer than 25 %% are low in both sessions.</li>"
                      "</ul>" % "".join(per))

    def zm_bands(self, cell):
        offs = sorted(e["offset"] for e in cell.get("events", []) if e["event"] == "up")
        bands, cur = [], []
        for o in offs:
            if cur and o - cur[-1] > 300:
                bands.append(cur)
                cur = []
            cur.append(o)
        if cur:
            bands.append(cur)
        return [(b[0], b[-1], len(b)) for b in bands if len(b) >= 3]

    def sec7_sup(self):
        """supplementary: the padded runs of step YP against the switch windows of round 1 (step S4)"""
        S = self.sup("yp_round1")
        ref = S.get("reference") or {}
        h = self.sup_lead("the padded runs against the switch windows of round 1")
        if not (ref.get("up") or {}).get("series"):
            return h + "<p class='miss'>Step S4 has no data, so there is no reference series.</p>"
        u, f = ref["up"], ref["fall"]
        h += ("<ul><li><b>Why.</b><ul>"
              "<li>Rule 2 compares a padded run with the pad 0 processes of the same CPU and session.</li>"
              "<li>So its result depends on these 2 processes per cell.</li>"
              "<li>The 60 s runs of round 1 give a reference that does not depend on them %s.</li></ul></li>"
              "<li><b>Reference.</b><ul>"
              "<li>An up window is a window at which at least %d of the %d load-only processes of step S4 go "
              "up.</li>"
              "<li>The up windows are %s.</li>"
              "<li>A fall window is a window at which at least %d of them fall.</li>"
              "<li>The fall windows are %s.</li>"
              "<li>A window is 0.3 s long.</li></ul></li>"
              "<li><b>Prediction for pad P.</b><ul>"
              "<li>A predicted window is a reference window minus P / 80.</li>"
              "<li>Only the windows 0 to 99 of a run are kept.</li>"
              "<li>An event matches a predicted window if it lies within 1 window of it.</li></ul></li>"
              "<li><b>Two counts are given.</b><ul>"
              "<li>The first count: how many of the measured ups lie at a predicted window.</li>"
              "<li>The second count: at how many predicted windows the rate goes up.</li>"
              "<li>The second count uses only the windows where the process was at the low level before. A process "
              "at the high level cannot go up.</li>"
              "<li>The falls are counted the same way, with the high level before.</li></ul></li></ul>" % (
                  self.sref("S4", "YP"), u["min_processes"], u["processes_pooled"],
                  ", ".join("%d" % x for x in u["series"]), f["min_processes"], ", ".join("%d" % x for x in f["series"])))
        for kind, many, need, num in (("up", "ups", "low", "16a"), ("fall", "falls", "high", "16b")):
            rows = []
            pads = sorted({c["pad"] for c in S.get("cells", []) if c["kind"] == kind})
            for cpu, ses in self.cells():
                cs = [c for c in S.get("cells", []) if c["kind"] == kind and c["cpu"] == cpu and c["session"] == ses]
                if not cs:
                    rows.append([TH("all"), TH(cpu), TH(ses), MISS(6)])
                    continue
                for pd in pads:
                    c = next((x for x in cs if x["pad"] == pd), None)
                    if not c:
                        continue
                    pred = next((x["windows"] for x in S.get("predicted", []) if x["kind"] == kind and x["pad"] == pd), [])
                    rows.append([TH(pd), TH(cpu), TH(ses), VL(pred, 0), V(c["processes"], 0),
                                 TX("%d of %d" % (c["n_events_match"], c["n_events"])), V(c["share_events_match_pct"], 1),
                                 TX("%d of %d" % (c["n_eligible_hit"], c["n_eligible"])), V(c["share_eligible_hit_pct"], 1)])
            h += table(["Pad, B", "CPU", "Session", "predicted %s windows" % kind, "processes",
                        "measured %s at a predicted window" % many, "share, %",
                        "predicted windows with the process at the %s level before that show %s %s" % (
                            need, "an" if kind == "up" else "a", kind), "share, %"], rows,
                       caption="Table %s. Supplementary, defined after the data was seen. Step YP: the %s of the runs "
                               "against the %s windows of round 1 moved earlier by pad / 80 windows. Pad 0 is the run "
                               "without a pad." % (num, many, kind))
            st = (S.get("summary_text") or {}).get(kind) or {}
            have = sorted({c["session"] for c in S.get("cells", []) if c["kind"] == kind})
            h += "<p>The summary lines for the %s, as recorded:</p><ul>" % many
            for ses in SESSIONS:
                t = st.get("s%d" % ses)
                if ses in have and t and t != MISSING:
                    h += "<li>%s.</li>" % esc(t[0].upper() + t[1:])
                else:
                    h += "<li class='miss'>%s, padded runs, session %d: %s.</li>" % (many.capitalize(), ses, MISSING)
            if have == list(SESSIONS) and st.get("overall"):
                h += "<li><b>%s.</b></li>" % esc(st["overall"][0].upper() + st["overall"][1:])
            h += "</ul>"
        h += ("<ul><li>The rows of every single process are in block 16.1 of <code>final8.txt</code> %s.</li>"
              "<li>This evaluation counts matches. It has no decision rule.</li>"
              "<li>So it gives no verdict.</li>"
              "<li>The verdict of rule 2 above stays as recorded.</li></ul>" % self.R("final8"))
        return h

    def sec7(self):
        J = self.J
        h = "<h2>7. The two levels at 8 MiB</h2><ul>"
        lv = [r for r in self.rows("levels.rows", step="S4") if r["kernel"] in ("read", "asmread")]
        if lv:
            h += ("<li>At 8 MiB a load-only loop runs at one of two rates. It changes between them inside one "
                  "process.</li>"
                  "<li>%d of the %d load-only processes of step S4 show two levels (table 14).</li>"
                  "<li>Old read shows one level.</li>"
                  "<li>The cost rule of section 5 does not explain this spread of the gain at 8 MiB.</li>" % (
                      sum(r["two_levels"] for r in lv), sum(r["processes"] for r in lv)))
        h += ("<li><b>Words of this section.</b><ul>"
              "<li>A switch is a change of the level inside a process.</li>"
              "<li>An up-switch (short: an up) goes to the high level.</li>"
              "<li>A fall (also: a down switch) goes to the low level.</li>"
              "<li>A kernel timer is a timer of the operating system kernel. It is not a kernel of the test "
              "runner.</li>"
              "<li>The worker is the thread of the test process that runs the measured loop.</li></ul></li>")
        c3 = self.claim("H3a")
        if c3:
            h += ("<li><b>Hypothesis H3a</b> says: a kernel timer on the worker's CPU triggers the switch. Section "
                  "7.5 gives the test.<ul><li>Verdict as recorded: %s.</li></ul></li>" % esc(c3["overall"]))
        c7 = self.claim("H7")
        if c7:
            h += ("<li><b>Hypothesis H7</b> says: the level depends on the address of the runner's own window "
                  "record, and not on time. Sections 7.3 and 7.4 give the two tests."
                  "<ul><li>Verdict as recorded: %s.</li></ul></li>" % esc(c7["overall"]))
        c2 = self.claim("H2")
        if c2:
            h += ("<li><b>Hypothesis H2</b> says: the original gain of 0.94 %% was measured at the low level. "
                  "Section 7.6 gives the test.<ul><li>Verdict as recorded: %s.</li></ul></li>" % esc(c2["overall"]))
        h += "</ul>"
        # (i)
        h += "<h3>7.1 Example traces</h3>" + self.fig_traces()
        rows = []
        for cpu, ses in self.cells():
            for k in ("asmread", "read", "oldread"):
                r = self.one("levels.rows", step="S4", kernel=k, cpu=cpu, session=ses)
                if not r:
                    rows.append([TH(k), TH(cpu), TH(ses), MISS(6)])
                    continue
                rows.append([TH(k), TH(cpu), TH(ses), V(r["processes"], 0), V(r["two_levels"], 0), V(r["low"]),
                             V(r["high"]), V(r["share_high"], 3), VL(r["one_level_rates"])])
        h += table(["Kernel", "CPU", "Session", "processes", "with two levels", "low level, GB/s", "high level, GB/s",
                    "share of windows at the high level", "rates of the processes with one level, GB/s"], rows,
                   caption="Table 14. Step S4: levels in the 60 s runs at 8 MiB.")
        # (ii)
        h += "<h3>7.2 Counters by level</h3>"
        h += ("<p>Steps <code>XCA</code>, <code>XCB</code> and <code>XCC</code> read the counters once per window. So "
              "each count belongs to one level %s.</p>" % self.sref("XCA", "XCB", "XCC"))
        rows = []
        for cpu, ses in self.cells():
            for k in ("asmread", "read", "oldread"):
                m = self.one("counters.rows", event="l1d_cache_lmiss_rd", kernel=k, size="8M", cpu=cpu, session=ses)
                c = self.one("counters.rows", event="cpu_cycles", kernel=k, size="8M", cpu=cpu, session=ses)
                if not m and not c:
                    rows.append([TH(k), TH(cpu), TH(ses), MISS(6)])
                    continue
                g = lambda r, f: r.get(f) if r else None
                rows.append([TH(k), TH(cpu), TH(ses), V(g(m, "low"), 3), V(g(m, "high"), 3), V(g(m, "single"), 3),
                             V(g(c, "low"), 3), V(g(c, "high"), 3), V(g(c, "single"), 3)])
        h += table(["Kernel", "CPU", "Session", "L1 long misses per line, low level", "L1 long misses per line, high level",
                    "L1 long misses per line, one level", "cycles per line, low level", "cycles per line, high level",
                    "cycles per line, one level"], rows,
                   caption="Table 15. Counts per line at 8 MiB by level. &quot;One level&quot;: processes that did not switch.")
        r3 = J.get("counters", {}).get("rule3", {})
        conf = sorted(k for k, v in r3.items() if v["overall"].startswith("confirmed"))
        notc = sorted(k for k, v in r3.items() if v["overall"] == "not confirmed")
        same = sorted(k for k, v in r3.items() if v["overall"].startswith("does not"))
        acc = J.get("counters", {}).get("acceptance", [])
        h += "<ul>"
        h += "<li>Events confirmed to differ between the levels (rule 3 of round 2, both CPUs, both sessions): %s.</li>" % (
            ", ".join("<code>%s</code>" % esc(k) for k in conf) or "none")
        h += "<li>Events that differ in some cells and are not confirmed: %s.</li>" % (", ".join("<code>%s</code>" % esc(k) for k in notc) or "none")
        h += "<li>Events that do not differ: %s.</li>" % (", ".join("<code>%s</code>" % esc(k) for k in same) or "none")
        if acc:
            npass = sum(1 for a in acc if a["pass"])
            h += ("<li><b>Check that counting leaves the behaviour unchanged</b> (rule 1 of round 2).<ul>"
                  "<li>The check passes in %d of %d cells. A cell here is one step, CPU and session.</li>"
                  "<li>A cell passes if its runs show the two levels of the uncounted step S4 within 0.5 GB/s "
                  "%s.</li>%s</ul></li>" % (
                      npass, len(acc), self.R("final8"),
                      "" if npass == len(acc) else "<li>The counts of a cell that fails are not used for a mechanism.</li>"))
        h += ("<li>These counts describe the two levels. They do not name the cause.</li>"
              "<li>A mechanism needs a test that changes it.</li></ul>")
        # (iii)
        h += "<h3>7.3 The record pad test (hypothesis H7, the controlled change)</h3>"
        h += ("<ul><li>The runner stores the times of window i in the record <code>win[i]</code>.</li>"
              "<li>Hypothesis H7 says: the level changes when the loop touches a record at certain addresses.</li>"
              "<li>The option <code>--rec-pad P</code> moves the record array by P bytes.</li>"
              "<li>Then window i uses the address that window i + P / 80 used before.</li>"
              "<li>So H7 predicts that each switch comes P / 80 windows earlier %s.</li></ul>" % self.sref("YP"))
        h += self.one_session("YP") + self.fig_pad()
        rows = []
        Yp = J.get("YP", {})
        for cpu, ses in self.cells():
            ss = sorted([s for s in Yp.get("shift", []) if s["cpu"] == cpu and s["session"] == ses], key=lambda s: s["pad"])
            if not ss:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(5)])
            for s in ss:
                rows.append([TH(s["pad"]), TH(cpu), TH(ses), V(s["predicted"], 0), V(s["predicted_modulo_spacing"], 0),
                             V(s["median_shift"], 1), TX("%d of %d" % (s["n_match"], s["n"])), TX("holds" if s["match"] else "fails")])
        h += table(["Pad, B", "CPU", "Session", "predicted shift pad / 80, windows", "the same modulo the spacing of the pad 0 ups",
                    "measured median shift, windows", "ups that match", "up series"], rows,
                   caption="Table 16. Step YP: shift of the up-switches against pad 0. A positive shift is earlier. "
                           "&quot;Holds&quot;: the measured median shift is within 1 window of the predicted shift "
                           "modulo the spacing.")
        hc = Yp.get("hot_copy", {})
        h += "<ul>"
        for ses in SESSIONS:
            c = hc.get("s%d" % ses)
            if c:
                h += ("<li>Option <code>--hot-copy</code>, session %d: switches per process %s. The prediction "
                      "&quot;median at most 1&quot; %s.</li>" % (ses, esc(c["switches_per_process"]), "holds" if c["prediction_holds"] else "fails"))
            else:
                h += "<li class='miss'>Option <code>--hot-copy</code>, session %d: %s.</li>" % (ses, MISSING)
        h += "<li>Rule 2 overall, as recorded: %s.</li>" % esc(Yp.get("overall", "no data"))
        h += ("<li><b>Deviation.</b><ul>"
              "<li>Rule 2 had fixed the statistic &quot;first fall after window 30&quot;. This statistic does not "
              "exist in every process.</li>"
              "<li>The series of all up-switches replaces it.</li>"
              "<li>This choice was made after the data was seen %s.</li></ul></li>"
              "<li>The test changes the address of the record and nothing else. It does not show which hardware part "
              "reacts to the address.</li></ul>" % self.R("decisions"))
        h += self.sec7_sup()
        # (iv)
        h += "<h3>7.4 The window length test (step YL)</h3>"
        h += ("<p>This test makes the window longer or shorter. It separates two cases %s.</p>"
              "<ul><li>Switches that follow the record address keep their window number.</li>"
              "<li>Switches that follow time keep their time.</li></ul>" % self.sref("YL"))
        h += self.one_session("YL")
        Yl = J.get("YL", {})
        rows = []
        for cpu, ses in self.cells():
            c = Yl.get("verdict", {}).get("cpu%d/s%d" % (cpu, ses))
            if not c:
                rows.append([TH("all"), TH(cpu), TH(ses), MISS(6)])
                continue
            for wl in sorted(c["medians"], key=int):
                m, u = c["medians"][wl], c["up_share"].get(wl, {})
                rows.append([TH(wl), TH(cpu), TH(ses), V(m["fall"], 1), V(m["n_fall"], 0), V(m["up"], 1), V(m["n_up"], 0),
                             TX("%d of %d" % (u.get("near_s4_index", 0), u.get("ups", 0))),
                             TX("%d of %d" % (u.get("near_s4_time", 0), u.get("ups", 0)))])
        h += table(["Window length, ms", "CPU", "Session", "median window of the first fall", "processes with a fall",
                    "median window of the first up", "processes with an up",
                    "ups within 1 window of an S4 up window (descriptive)", "ups within 1 window of the S4 time (descriptive)"], rows,
                   caption="Table 17. Step YL: first switches by window length, asmread and read pooled. An S4 up "
                           "window is a window number at which the runs of step S4 go up (21, 44, 67, 90). Step S4 has "
                           "0.3 s windows. The S4 time is the time of such an up in step S4 (6.3 s, 13.2 s).")
        h += "<ul>"
        for cpu, ses in self.cells():
            c = Yl.get("verdict", {}).get("cpu%d/s%d" % (cpu, ses))
            if c:
                h += ("<li>Rule 1 of round 3, CPU %d session %d, literal verdict: <b>%s</b>.<ul>"
                      "<li>Runs with one 30 s window without a switch after 0.3 s: %d of %d.</li></ul></li>" % (
                          cpu, ses, esc(c["verdict"]), c["one_window_quiet"], c["one_window_processes"]))
            else:
                h += "<li class='miss'>Rule 1 of round 3, CPU %d session %d: %s.</li>" % (cpu, ses, MISSING)
        h += "<li>Rule 1 overall, as recorded: %s.</li>" % esc(Yl.get("overall", "no data"))
        h += ("<li><b>Reading.</b><ul>"
              "<li>The rule's statistic is the first switch. The first switch differs between processes.</li>"
              "<li>Table 17 also holds a descriptive count over all up-switches.</li>"
              "<li>In this count, more ups match the window number than the time at 100 ms.</li>"
              "<li>This count was not fixed before the data. So it does not replace the verdict.</li>"
              "</ul></li></ul>")
        # (v)
        h += ("<h3>7.5 Host sampler and onset (step XW, hypothesis H3a)</h3>"
              "<ul><li>Step <code>XW</code> ran 30 s processes with a sampler.</li>"
              "<li>The sampler is a second process. It reads the activity counters of the host beside each run.</li>"
              "<li>A key is one such counter, for example the count of timer interrupts on the CPU.</li>"
              "<li>Rule 4 of round 2 asks whether a key changes at the switches more often than elsewhere.</li>"
              "<li>The onset is the time of the first up-switch of a process.</li>"
              "<li>Rule 5 asks whether the first up-switch keeps its time after the process start or after the "
              "target start.</li>"
              "<li>A condition name gives the kernel (K), the size (S) and the activity before the target "
              "(prev).</li></ul>"
              "<p>The results:</p><ul>")
        st = J.get("switch_timing", {})
        for ses in SESSIONS:
            s = st.get("XW_sampler", {}).get("s%d" % ses)
            if not s:
                h += "<li class='miss'>Sampler, session %d: %s.</li>" % (ses, MISSING)
                continue
            n = "".join("<li>CPU %s: %d up and %d down switches in %d processes.</li>" % (c, d["up_switches"], d["down_switches"], d["processes"])
                        for c, d in sorted(s["cpus"].items(), key=lambda kv: int(kv[0])))
            h += ("<li><b>Sampler, session %d.</b><ul>%s<li>%d keys were compared.</li>"
                  "<li>Rule 4 of round 2: %s.</li></ul></li>" % (
                      ses, n, len(s["keys"]), "a key accompanies the switches" if s["any_key_accompanies"] else "no key accompanies the switches"))
        for ses in SESSIONS:
            o = st.get("XW_onset", {}).get("s%d" % ses)
            if not o:
                h += "<li class='miss'>Onset, session %d: %s.</li>" % (ses, MISSING)
                continue
            for cond, d in sorted(o["conditions"].items()):
                if d.get("has_previous_activity"):
                    h += ("<li><b>Onset, session %d, condition <code>%s</code>.</b><ul>"
                          "<li>This condition has 3 s of another activity before the target.</li>"
                          "<li>The first up-switch comes %.2f s after the process start. That is %.2f s after the "
                          "target start.</li>"
                          "<li>Both times are the median of %d processes, est.</li>"
                          "<li>Rule 5, as recorded: %s.</li></ul></li>" % (
                              ses, esc(cond), d["median_since_process_start"], d["median_since_target_start"], d["n"], esc(d["verdict"])))
        c = self.claim("H3a")
        if c:
            h += "<li>Hypothesis H3a (a kernel timer on the worker's CPU triggers the switch), overall as recorded: %s %s.</li>" % (
                esc(c["overall"]), self.sref("XW"))
        h += "</ul>"
        # (vi)
        h += "<h3>7.6 The original program at 8 MiB (step H2, hypothesis H2)</h3>"
        h += ("<ul><li>Step <code>H2</code> ran the two original binaries at 8 MiB with the original options.</li>"
              "<li>It ran 12 processes per binary, CPU and session.</li>"
              "<li>The original result was a gain of 0.94 %% %s.</li></ul>" % self.sref("H2"))
        h += self.fig_h2()
        rows = []
        for r in sorted(J.get("H2", {}).get("rows", []), key=lambda r: (int(r["cpu"]), r["session"])):
            rows.append([TH(r["cpu"]), TH(r["session"]), V(r["new_repetitions"], 0), V(r["low"], 0), V(r["between"], 0),
                         V(r["high"], 0), V(r["pairs"], 0), V(r["median_gain_pct"]), V(r["low_pairs"], 0), V(r["median_gain_low_pct"])])
        h += table(["CPU", "Session", "new-read repetitions", "low", "between", "high", "pairs", "median gain, %",
                    "low pairs", "median gain of the low pairs, %"], rows, caption="Table 18. Step H2.")
        # (vii)
        h += ("<h3>7.7 Where the record is when the rate goes up (step ZM)</h3>"
              "<ul><li>The offsets come from step ZM %s. An offset counts bytes after the start of the record "
              "array.</li>"
              "<li>This page forms a band from up-switches that are at most 300 B apart.</li>"
              "<li>It keeps a band with at least 3 up-switches.</li></ul><ul>" % self.sref("ZM"))
        zm = J.get("ZM", {}).get("by_cell", {})
        for cpu, ses in self.cells():
            c = zm.get("cpu%d/s%d" % (cpu, ses))
            if not c:
                h += "<li class='miss'>Step ZM, CPU %d session %d: %s.</li>" % (cpu, ses, MISSING)
                continue
            b = self.zm_bands(c)
            h += ("<li><b>CPU %d session %d.</b> The up-switches lie in bands of record offsets.<ul>"
                  "<li>First bands, offsets in bytes: %s.</li>"
                  "<li>There are %d bands in total.</li>"
                  "<li>%d of %d processes show two levels.</li></ul></li>" % (
                      cpu, ses, ", ".join("%d to %d" % (x[0], x[1]) for x in b[:6]), len(b), c["two_levels"], c["processes"]))
        h += ("</ul>%s<p>The list is descriptive. Step ZM has no decision rule.</p>" % self.one_session("ZM"))
        return h

    # ================================================================== section 8
    def sec8(self):
        J = self.J
        h = "<h2>8. What is explained and what is not</h2>"
        rows = []
        for c in J.get("claims", []):
            fl = [self.short(f) for s in ("s1", "s2") for f in c["folders"].get(s, [])]
            ps = c.get("per_session", {})
            rows.append(["<th scope='row'>%s</th>" % esc(c["id"]), TX(c["statement"]), TX(c["rule"]),
                         TX(ps.get("s1", MISSING), "txt wide"), TX(ps.get("s2", MISSING), "txt wide"),
                         TX(c["overall"], "txt wide"), TX(", ".join(fl))])
        h += table(["Hypothesis", "Statement", "The test (rule)", "Verdict, session 1", "Verdict, session 2", "Overall",
                    "Source folders (step and session)"], rows,
                   caption="Table 19. Every hypothesis with its verdict by its recorded rule. The texts are those of final8.json.",
                   cls="claims")
        h += ("<p>The verdict texts come from the analysis output %s. The rules come from the decisions file %s.</p>"
              % (self.R("final8"), self.R("decisions")))
        # share
        h += "<h3>8.1 Which share of the gap the cycle model explains</h3><ul>"
        h += ("<li><b>The cycle model:</b><ul>"
              "<li>Cycles per line of the new loop = fitted line of step ZS at the measured r.</li>"
              "<li>Cycles per line of old read = its measured value.</li>"
              "<li>Predicted gain = old cycles / new cycles - 1.</li></ul></li>")
        h += "<li><b>The gap to explain:</b> the gain falls from its value at 1 MiB to its value at 8 MiB.</li>"
        h += ("<li><b>The share that the model explains</b> = A / B.<ul>"
              "<li>A = gain at 1 MiB - predicted gain at 8 MiB.</li>"
              "<li>B = gain at 1 MiB - measured gain at 8 MiB.</li></ul></li>")
        h += ("<li><b>Measured gain by level</b> = level rate of <code>asmread</code> in step S4 / old read rate in "
              "step S4 - 1.</li></ul>")
        h += self.one_session("ZS")
        rows = []
        for cpu, ses in self.cells():
            ic, sl = self.zs_fit(cpu, ses)
            a8 = self.one("ZS.rows", kernel="asmread", size="8M", cpu=cpu, session=ses)
            o8 = self.one("ZS.rows", kernel="oldread", size="8M", cpu=cpu, session=ses)
            lv = self.one("levels.rows", step="S4", kernel="asmread", cpu=cpu, session=ses)
            lo = self.one("levels.rows", step="S4", kernel="oldread", cpu=cpu, session=ses)
            c1 = self.r1cell("1M", cpu, ses)
            if not a8 or ic is None:
                for level in ("low", "high"):
                    rows.append([TH(cpu), TH(ses), TH(level), MISS(6)])
                continue
            pg = CALC["linegain"](o8["cyc"], ic, sl, a8["r"])
            oldrate = med(lo["one_level_rates"]) if lo and lo.get("one_level_rates") else None
            g1 = c1["asm_minus_old"]["gain_pct"] if c1 else None
            for level in ("low", "high"):
                lr = lv.get(level) if lv else None
                if lr is None or oldrate is None or g1 is None:
                    rows.append([TH(cpu), TH(ses), TH(level), V(a8["r"], 3), CC("line", (ic, sl, a8["r"]), 3),
                                 CC("linegain", (o8["cyc"], ic, sl, a8["r"]), 2), V(None), V(None), V(None)])
                    continue
                mg = CALC["gain"](lr, oldrate)
                rows.append([TH(cpu), TH(ses), TH(level), V(a8["r"], 3), CC("line", (ic, sl, a8["r"]), 3),
                             CC("linegain", (o8["cyc"], ic, sl, a8["r"]), 2), V(lr),
                             CC("gain", (lr, oldrate), 2), CC("share", (g1, pg, mg), 0)])
        h += table(["CPU", "Session", "Level", "r at 8 MiB", "predicted cycles per line (calc.)", "predicted gain, % (calc.)",
                    "measured level rate, GB/s", "measured gain at this level, % (calc.)", "share of the fall of the gain that the model gives, % (calc.)"],
                   rows, caption="Table 20. Predicted gain at 8 MiB from the cycle model against the measured gain, per CPU, session and level.")
        h += ("<ul><li>The model gives one predicted gain per CPU and session. The measured gain has two values, one "
              "per level.</li>"
              "<li>A share above 100 % means: the model predicts a smaller gain than this level shows.</li>"
              "<li>So the fitted cost line reproduces the size of the fall of the gain between 1 MiB and 8 MiB.</li>"
              "<li>The fitted cost line does not explain the difference between the two levels.</li>"
              "<li>The fitted line used the 8 MiB point too. So at 8 MiB this is a fit, and not an independent "
              "prediction.</li>"
              "<li>The independent check is in section 5. There the band was fixed before step ZS.</li>"
              "<li>This page computed the share. No rule fixed it before the data.</li></ul>")
        # open points
        h += "<h3>8.2 Not explained: Insufficient data</h3>"
        slope = self.slope()
        l2 = [r["median"] for r in self.rows("prefetch.YF", size="1M") if r["kernel"] in ("asmread", "read_1pl")]
        oldc = med([r["cyc"] for r in self.rows("ZS.rows", kernel="oldread") if r["size_bytes"] <= 16 << 20])
        prop = " This test is a proposal. It was not run."
        rows = [
            ("Why a line from the SLC costs about %s cycles more than a line from the second-level cache. This value "
             "is the slope of the fitted line of step ZS." % fnum(slope, 2),
             "Mesh and SLC counters (events of the network between the cores and the SLC) per line read, at 1 MiB and at 8 MiB.", "root"),
            ("Why the load-only loops do not pass %s GB/s when the data is in the second-level cache. Source of "
             "these rates: step YF at 1 MiB, <code>asmread</code> and <code>read_1pl</code>." % (
                 ("%s to %s" % (fnum(min(l2), 1), fnum(max(l2), 1))) if l2 else "NA"),
             "Counters of the core's buffers that hold loads and line fills, or a statement of the core's maker "
             "on the transfer rate from L2 to L1. A loop that reads two buffers in turn would test a limit per data "
             "stream without root." + prop, "root, or a new kernel"),
            ("Which hardware part reacts to the address of the window record (the two levels of section 7).",
             "The physical page addresses of the record array and of the buffer. They show whether the two compete "
             "for the same cache set. Then mesh counters by level.", "root"),
            ("Why old read needs about %s cycles per line at every size from 1 to 16 MiB." % fnum(oldc, 2),
             "Counters that split the cycles of the old loop by pipeline stage, or a simulator trace. Variants of "
             "the old loop with fewer vector adds would test it without root." + prop, "root, or new kernels"),
            ("Whether dirty lines add cost (hypothesis H1d, section 6.2).",
             "A counter that shows whether a write-back from L2 carries data, or a way to check that the buffer left the caches.", "root"),
            ("Why some kernels with added instructions miss the predictions of section 4 at 8 MiB "
             "(<code>read_nop16</code> and <code>read_nop64</code> in the data of session 1).",
             "The record pad test and the counters by level for these kernels." + prop + " Then the physical "
             "addresses named above.", "no root for the first part"),
        ]
        h += table(["Open point", "Measurement that would decide it", "Needs"],
                   [["<td class='txt wide'>%s</td>" % a, "<td class='txt wide'>%s</td>" % b, TX(c)] for a, b, c in rows],
                   caption="Table 21. Open points. Each one is &quot;Insufficient data&quot; today.")
        h += ("<ul><li>Root access is forbidden on CRB for this work %s.</li>"
              "<li>Three rows name a test that needs no root and was not run.</li>"
              "<li>So the list of tests without root is not complete.</li></ul>" % self.R("handoff"))
        return h

    # ================================================================== section 9
    def digests(self):
        out = []
        try:
            text = open(self.decisions_path).read()
        except OSError:
            return out
        for line in text.splitlines():
            for m in re.finditer(r"`?([0-9a-f]{64})`?", line):
                names = re.findall(r"`(bwx\d+)`", line[:m.start()])
                if names and (names[-1], m.group(1)) not in out:
                    out.append((names[-1], m.group(1)))
        return out

    def h2_digests(self):
        out = []
        for ses in SESSIONS:
            for folder in self.folders("H2", ses):
                try:
                    for line in open(os.path.join(self.results, folder, "env.txt")):
                        m = re.match(r"^([0-9a-f]{64})\s+\S*/(bw_old|bw_new)$", line.strip())
                        if m and (m.group(2), m.group(1)) not in out:
                            out.append((m.group(2), m.group(1)))
                except OSError:
                    pass
        return out

    def sec9(self):
        J = self.J
        h = "<h2>9. How it was measured</h2><ul>"
        h += ("<li><b>Machine.</b> CRB only. The sources of the points below are the handoff and the decisions "
              "file %s.<ul>"
              "<li>One process ran at a time.</li>"
              "<li>Each process was pinned to CPU 2 or CPU 41. Step H2 also used CPU 0.</li>"
              "<li>No root access.</li>"
              "<li>The buffer is on huge pages (memory pages of 2 MiB).</li></ul></li>" % self.R("handoff", "decisions"))
        h += ("<li><b>Runner.</b> The binaries are:<ul>"
              "<li><code>bwx8</code> is the test runner.</li>"
              "<li><code>bwx9</code> is not a binary. It is the folder prefix of the round 2 steps. Round 2 ran the "
              "<code>bwx8</code> binary %s.</li>"
              "<li><code>bwx10</code> adds the prefetch kernels. It also adds the options <code>--rec-pad</code> and "
              "<code>--hot-copy</code>.</li>"
              "<li><code>bwx11</code> adds the option <code>--evict-mb</code>. It also adds the kernels with 64, 96 and "
              "128 no-operation instructions.</li>"
              "<li><code>bw_old</code> and <code>bw_new</code> are the original benchmark binaries.</li></ul></li>"
              % self.R("decisions"))
        h += ("<li><b>Sessions.</b> Each step runs in two sessions at least 3 hours apart.<ul>"
              "<li>Session 2 uses the reversed CPU order.</li>"
              "<li>The steps <code>XEV</code>, <code>YA</code> and <code>ZA</code> are acceptance runs. They have "
              "one session.</li>"
              "<li>An acceptance run is a short run that checks a new build or a new set of counter events before "
              "its steps are used.</li></ul></li>")
        h += ("<li><b>Order of the work.</b> The progress file lists the rounds in time order with the load of each "
              "visit %s.</li></ul>" % self.R("progress"))
        dg = self.digests()
        hd = self.h2_digests()
        rows = [[TH(n), TX(d, "txt mono"), TX("decisions file")] for n, d in dg] + [[TH(n), TX(d, "txt mono"), TX("env.txt of step H2")] for n, d in hd]
        if rows:
            h += table(["Binary", "sha256 digest", "Source"], rows, caption="Table 22. Binaries.")
            h += ("<ul class='note'><li>A sha256 digest is a checksum that identifies a file.</li>"
                  "<li>The digests of the runner come from the decisions file %s.</li>%s</ul>" % (self.R("decisions"), (
                      "<li>The digests of the original binaries come from the result folders of step H2 %s.</li>"
                      % self.R("h2env")) if hd else ""))
        else:
            h += "<p class='miss'>The digests could not be read from the decisions file.</p>"
        rows = []
        for r in J.get("inventory", {}).get("rows", []):
            if r.get("folder") is None:
                rows.append([TH(r["step"]), TH(r["session"]), MISS(6)])
                continue
            rows.append([TH(r["step"]), TH(r["session"]), TX(r["folder"], "txt mono"), V(r["processes"], 0),
                         TX("%s to %s" % (r["first_launch_utc"], r["last_launch_utc"])),
                         TX("%s / %s / %s" % (fnum(r.get("load_min")), fnum(r.get("load_median")), fnum(r.get("load_max")))),
                         TX("%d / %d / %d" % (r["killed"], r["failed"], r["incomplete"])), V(r["x_rows"], 0)])
        h += table(["Step", "Session", "Result folder", "processes", "launch times, UTC on 2026-11-15",
                    "load at launch: lowest / median / highest", "killed / failed / incomplete", "error rows"], rows,
                   caption="Table 23. Every step: time and system load. Load = the 1 minute load average of CRB, read before each process.")
        h += ("<ul class='note'><li><b>Reading, not checked against a process list:</b> a load near 1.00 comes from "
              "the test itself.<ul>"
              "<li>The test processes follow each other without a pause.</li>"
              "<li>Each one keeps one CPU busy.</li></ul></li>"
              "<li>The table is the inventory of the analysis output %s.</li></ul>" % self.R("final8"))
        h += "<h3>The repeatability rule</h3>"
        h += ("<ul><li>The rule was fixed in the design before the data.</li>"
              "<li><b>Spread of a cell.</b> For each cell, trials 1 and 3 of a process are compared with trials 2 and "
              "4 of the same process. The largest such difference over the 6 processes is the spread of the cell.</li>"
              "<li><b>&quot;Repeatable&quot;.</b> A difference between two rates is &quot;repeatable&quot; on a CPU "
              "in a session only if both conditions hold.<ul>"
              "<li>Its median over the 6 units exceeds the sum of the two spreads.</li>"
              "<li>The 6 unit values of the difference all have the same sign.</li>"
              "<li>A unit is one set in step S2. In all other steps a unit is one process.</li></ul></li>"
              "<li><b>&quot;Confirmed&quot;.</b> The difference is &quot;confirmed&quot; only if this holds with the "
              "same sign in both sessions on both CPUs.</li>"
              "<li>The rule is not a confidence interval %s.</li></ul>" % self.R("design"))
        h += "<h3>Deviations, as recorded in the decisions file</h3><ul>"
        h += ("<li><b>Extra logins during runs.</b><ul>"
              "<li>2 extra logins fetched the data of steps XW, XCA, XCB and XCC while later steps of the same visit ran.</li>"
              "<li>3 extra logins did the same for steps YL, YP and YC.</li>"
              "<li>1 extra login did the same for step ZC.</li>"
              "<li>Each login ran one <code>tar</code> command.</li>"
              "<li>A login can disturb a running process.</li></ul></li>")
        h += ("<li><b>A file outside the allowed folder.</b> The build login of <code>bwx10</code> wrote one file <code>/tmp/.x</code> outside the "
              "folder <code>~/cache-perf</code> on CRB. The next login removed it 1 minute later.</li>")
        h += ("<li><b>The replaced YP statistic.</b><ul>"
              "<li>Rule 2 of round 3 named &quot;the first fall after window 30&quot;.</li>"
              "<li>That fall is absent in some processes.</li>"
              "<li>The series of all up-switches replaces it (section 7.3).</li></ul></li>")
        h += ("<li><b>Counters without the three-mode check.</b><ul>"
              "<li>The design asks for a check before counters are interpreted.</li>"
              "<li>The check runs each trial in three modes: counters closed, counters open and not read, and "
              "counters open and read at each window.</li>"
              "<li>This check was not run.</li>"
              "<li>The check used instead: the counted runs must show the two levels of the uncounted step S4 within "
              "0.5 GB/s (section 7.2).</li></ul></li>")
        h += ("<li><b>A missing control.</b> Step YF has no kernel with the code layout of the prefetch kernels and no "
              "prefetch (<code>read_nop4</code>). So a layout effect is not separated from the prefetch effect.</li></ul>")
        h += "<p>The decisions file records each of these deviations %s.</p>" % self.R("decisions")
        if self.notes:
            h += "<h3>Not drawn</h3><ul>" + "".join("<li>%s</li>" % esc(n) for n in self.notes) + "</ul>"
        h += ("<h3>How this page was made</h3><ul>"
              "<li><b>Input.</b> The generator reads <code>final8.json</code> and two raw files. The raw files are the "
              "W rows of step S4 and the repetition rows of step H2.</li>"
              "<li><b>Colours.</b> Blue for the new loops, orange for old read, grey or hollow for predictions and "
              "fitted values %s.</li>"
              "<li><b>Italics.</b> A table cell in italics is computed by this page from numbers of "
              "<code>final8.json</code> %s.</li>"
              "<li><b>Pointer texts.</b> A mark of a chart shows a short text when the pointer rests on it. No chart "
              "needs this text. The tables hold every number.</li></ul>" % (self.R("palette"), self.R("generator")))
        return h

    # ================================================================== page
    def page(self):
        secs = [self.sec1(), self.sec2(), self.sec3(), self.sec4(), self.sec5(), self.sec6(), self.sec7(), self.sec8(), self.sec9()]
        body = "".join("<section id='sec%d'>%s</section>" % (i + 1, s) for i, s in enumerate(secs))
        body += "<section id='sec10'><h2>10. References</h2>%s</section>" % self.R.html()
        return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<meta name='color-scheme' content='light'>"
                "<title>Why the new read loop gains so little at 8 MiB on CRB</title><style>%s</style></head>"
                "<body><main>%s</main></body></html>\n" % (CSS, body))


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
html{background:#f9f9f7}
body{margin:0;background:#f9f9f7;color:#0b0b0b;font:15px/1.5 system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif}
main{max-width:1200px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:26px;line-height:1.25;margin:8px 0 6px}
h2{font-size:20px;margin:36px 0 10px;padding-top:10px;border-top:1px solid #e1e0d9}
h3{font-size:16px;margin:24px 0 8px}
p,li{max-width:900px}
li{margin:3px 0}
ul{margin:6px 0 10px;padding-left:22px}
li>ul{margin:3px 0 5px;padding-left:20px}
td ul{margin:3px 0;padding-left:16px}
figure>p{margin:10px 0 2px}
figure>ul{margin-bottom:4px}
code{font:13px ui-monospace,"DejaVu Sans Mono",monospace;background:#efeee9;padding:0 3px;border-radius:3px;overflow-wrap:anywhere}
.meta{color:#52514e;font-size:13px}
.short{background:#fff;border:1px solid #e1e0d9;border-left:4px solid #2a78d6;border-radius:6px;padding:4px 16px 8px;margin:14px 0}
.short h2{border:0;margin:8px 0 4px;padding:0;font-size:17px}
.warn{background:#fff7e6;border:1px solid #f0d9a8;border-radius:6px;padding:8px 12px}
.ok{background:#eef7ee;border:1px solid #cfe5cf;border-radius:6px;padding:8px 12px}
.miss{color:#8a4b00;font-style:italic}
td.miss{background:#fff7e6;text-align:center}
.note{color:#52514e;font-size:13px;margin:6px 0}
figure{margin:18px 0;padding:12px;background:#fcfcfb;border:1px solid #e1e0d9;border-radius:8px}
.figtitle{font-weight:600;margin-bottom:6px}
figcaption{margin-top:8px;max-width:900px}
.legend{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;color:#52514e;margin:4px 0 8px}
.legend span{display:inline-flex;align-items:center;gap:4px}
.sw{flex:none}
.panels{display:flex;flex-wrap:wrap;gap:14px}
.panel{flex:1 1 400px;min-width:0;max-width:540px}
.chart{display:block;width:100%;height:auto;font-family:system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif}
.chart text{fill:#0b0b0b}
.chart text.ax{fill:#52514e}
.chart text.ttl{font-weight:600}
.chart text.b{font-weight:600}
.chart .frame{fill:#fcfcfb;stroke:#c3c2b7;stroke-width:1}
.chart .grid{stroke:#e1e0d9;stroke-width:1}
.chart .tick{stroke:#c3c2b7;stroke-width:1}
.tbl{overflow-x:auto;max-width:100%;margin:10px 0;border:1px solid #e1e0d9;border-radius:6px;background:#fff}
table{border-collapse:collapse;font-size:13px;width:max-content;min-width:100%}
caption{caption-side:top;text-align:left;padding:8px 10px;font-weight:600;max-width:900px}
th,td{padding:4px 8px;border-bottom:1px solid #efeee9;text-align:left;vertical-align:top}
thead th{background:#f3f2ee;font-weight:600;max-width:124px;white-space:normal;vertical-align:bottom}
tbody th{font-weight:500;white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.calc{font-style:italic;color:#333}
td.na{text-align:right;color:#898781}
td.txt{max-width:340px}
td.wide{min-width:240px;max-width:420px}
table.claims{width:100%;min-width:1040px;table-layout:fixed;font-size:12.5px}
table.claims th,table.claims td{max-width:none;min-width:0;white-space:normal;overflow-wrap:anywhere}
table.claims th:nth-child(1){width:10%}table.claims th:nth-child(2){width:15%}table.claims th:nth-child(3){width:10%}
table.claims th:nth-child(4){width:20%}table.claims th:nth-child(5){width:20%}table.claims th:nth-child(6){width:16%}
table.claims th:nth-child(7){width:9%}
table.words{width:100%;min-width:0}
table.words tbody th{white-space:normal;width:26%}
table.words td.txt{max-width:none}
td.mono{font:12px ui-monospace,"DejaVu Sans Mono",monospace;max-width:none;white-space:nowrap}
.refs{padding-left:18px}
@media (max-width:520px){main{padding:14px 10px 40px}figure{padding:8px 6px}h1{font-size:22px}}
.refs li{max-width:1100px;overflow-wrap:anywhere}
"""


def build(json_path, results=None, decisions=None, date=None):
    with open(json_path) as f:
        J = json.load(f)
    results = results or J.get("results_folder") or os.path.join(CRB_DIR, "results")
    decisions = decisions or os.path.join(X_DIR, "DECISIONS-bwx8.md")
    date = date or datetime.date.today().isoformat()
    rep = Report(J, results, decisions, date)
    return rep.page(), rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="Final HTML report of the tackle-8mb investigation.")
    ap.add_argument("--json", default=os.path.join(HERE, "final8.json"), help="final8.json (default %(default)s)")
    ap.add_argument("--results", default=None, help="results folder (default: the one named in final8.json)")
    ap.add_argument("--decisions", default=None, help="decisions file (default DECISIONS-bwx8.md of the runner folder)")
    ap.add_argument("--date", default=None, help="report date (default today)")
    ap.add_argument("-o", "--out", default=os.path.join(N_DIR, "tackle-8mb-report.html"), help="output file (default %(default)s)")
    a = ap.parse_args(argv)
    page, rep = build(a.json, a.results, a.decisions, a.date)
    with open(a.out, "w") as f:
        f.write(page)
    miss = rep.missing_steps()
    print("wrote %s (%d bytes)" % (a.out, len(page.encode())))
    print("session 2 missing for: %s" % (", ".join(miss) if miss else "none"))
    print("chart labels left out for lack of room: %d" % rep.label_drops)
    for n in rep.drops + rep.notes:
        print("note: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
