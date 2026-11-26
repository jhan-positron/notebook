#!/usr/bin/env python3
"""easy_report.py - the easy-read page of the 8 MiB investigation (tackle-8mb-report-easy-read.html).

The page is the short, top-down version of tackle-8mb-report.html: the goal, the answer in one picture, the
path of thinking and testing, the conclusion, and the test code.

Rules of this generator:
- Every measured number is read at run time from final8.json or from a result file under crb/results.
- Every code excerpt is cut at run time from the real source file, by function name or by marker text.
  A missing marker stops the generator with a message (function die).
- Rule constants that the prose repeats are checked against the source text (function need).
- One HTML file: inline CSS and inline SVG, no script, no outside reference, light background only.

Usage: python3 easy_report.py [--json final8.json] [-o tackle-8mb-report-easy-read.html] [--date YYYY-MM-DD]
Standard library only. The plot helpers come from report_final.py in the same folder (not changed).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report_final as RF  # noqa: E402  (plot, table and number helpers of the full report)

esc, fnum, med = RF.esc, RF.fnum, RF.med
C_NEW, C_OLD, C_PRED, C_INK, C_INK2, C_BAND = RF.C_NEW, RF.C_OLD, RF.C_PRED, RF.C_INK, RF.C_INK2, RF.C_BAND
N_DIR, CRB = RF.N_DIR, RF.CRB_DIR
ROOT = os.path.dirname(CRB)                                   # .../cache-perf
X8 = os.path.join(CRB, "tmp", "agent-scratch", "bwx8-2026-11-14")
X10 = os.path.join(CRB, "tmp", "agent-scratch", "bwx10-2026-11-15")
X11 = os.path.join(CRB, "tmp", "agent-scratch", "bwx11-2026-11-15")
K13 = os.path.join(CRB, "tmp", "agent-scratch", "kernels-2026-11-13")
BENCH = os.path.join(ROOT, "bench")
ORIG_FOLDER = "kernels-20261113T181222Z"                      # the first measurement (2026-11-13)
PROBE_FOLDER = "kernels-20261113T183218Z"                     # build record of bw_old and bw_new
CELLS = [(c, s) for c in RF.CPUS for s in RF.SESSIONS]
MIB = float(1 << 20)


def die(msg):
    raise SystemExit("easy_report.py: " + msg)


def rng(xs, nd=2):
    """'a to b' of a list of numbers, or one value if both ends print the same"""
    xs = [x for x in xs if x is not None]
    if not xs:
        die("empty range")
    a, b = fnum(min(xs), nd), fnum(max(xs), nd)
    return a if a == b else "%s to %s" % (a, b)


def size_name(label):
    """'1.5M' -> '1.5 MiB', '32K' -> '32 KiB'"""
    return label[:-1] + {"M": " MiB", "K": " KiB"}[label[-1]]


# ------------------------------------------------------------------------------------------- source files
class Src:
    """One source file with locators. Every locator stops the generator if it finds nothing."""
    _cache = {}

    def __init__(self, path):
        self.path = path
        try:
            with open(path) as f:
                self.L = f.read().split("\n")
        except OSError as e:
            die("cannot read %s: %s" % (path, e))
        self._incom = None

    def in_comment(self, i):
        """True if line index i (0-based) of a C file starts inside a /* ... */ block"""
        if self._incom is None:
            self._incom, state = [], False
            for line in self.L:
                self._incom.append(state)
                j = 0
                while True:
                    k = line.find("*/" if state else "/*", j)
                    if k < 0:
                        break
                    state, j = not state, k + 2
        return self._incom[i]

    @classmethod
    def get(cls, path):
        if path not in cls._cache:
            cls._cache[path] = Src(path)
        return cls._cache[path]

    def text(self, r):
        return "\n".join(self.L[r[0] - 1:r[1]])

    def find(self, marker, start=1, end=None, regex=False):
        """1-based number of the first line from 'start' that holds the marker"""
        for i in range(start - 1, min(end or len(self.L), len(self.L))):
            if (re.search(marker, self.L[i]) if regex else marker in self.L[i]):
                return i + 1
        die("marker %r not found in %s (lines %d to %s)" % (marker, self.path, start, end or "end"))

    def c_func(self, name, missing_ok=False):
        """(first, last) line of the one C function definition of that name that is not inside a comment block"""
        pat = re.compile(r"^[A-Za-z_].*(?:^|[ *])%s\(.*\)$" % re.escape(name))
        hits = []
        for i, line in enumerate(self.L[:-1]):
            if pat.match(line) and self.L[i + 1] == "{" and not self.in_comment(i):
                j = i + 1
                while j < len(self.L) and self.L[j] != "}":
                    j += 1
                if j == len(self.L):
                    die("no end of function %s in %s" % (name, self.path))
                hits.append((i + 1, j + 1))
        if not hits:
            if missing_ok:
                return None
            die("C function %s not found in %s" % (name, self.path))
        if len(hits) != 1:
            die("C function %s has %d definitions outside comments in %s" % (name, len(hits), self.path))
        return hits[0]

    def macro(self, name):
        a = self.find("#define %s(" % name)
        b = a
        while self.L[b - 1].endswith("\\"):
            b += 1
        return (a, b)

    def sh_func(self, name):
        a = self.find(r"^%s\(\) \{" % re.escape(name), regex=True)
        if self.L[a - 1].rstrip().endswith("}"):
            return (a, a)
        return (a, self.find(r"^\}", a + 1, regex=True))

    def py_def(self, name, cls=None, kind="def"):
        start = self.find(r"^class %s\b" % re.escape(cls), regex=True) if cls else 1
        a = self.find(r"^\s*%s %s\b" % (kind, re.escape(name)), start, regex=True)
        ind = len(self.L[a - 1]) - len(self.L[a - 1].lstrip())
        b = a
        for i in range(a, len(self.L)):
            line = self.L[i]
            if line.strip() and len(line) - len(line.lstrip()) <= ind:
                break
            if line.strip():
                b = i + 1
        if a > 1 and self.L[a - 2].strip().startswith("@"):
            a -= 1
        return (a, b)


def need(src, r, token):
    """the prose repeats a constant of the code: stop if the code text in range r does not hold it"""
    if token not in src.text(r):
        die("the text %r is not in %s lines %d-%d: the prose of the page would be wrong" % (token, src.path, r[0], r[1]))


def fact(path, token):
    """the prose repeats a statement of a document: stop if the document does not hold it"""
    with open(path) as f:
        if token not in f.read():
            die("the text %r is not in %s: the prose of the page would be wrong" % (token, path))


def span(a, b):
    return "%d" % a if a == b else "%d-%d" % (a, b)


def table(headers, rows, caption, note=None, cls=""):
    """a table whose caption stays outside the box that scrolls sideways on a narrow screen"""
    h = "<div class='tcap'>%s</div><div class='tbl'><table%s aria-label='%s'><thead><tr>" % (
        caption, (" class='%s'" % cls) if cls else "", esc(re.sub(r"<[^>]+>", "", caption)))
    h += "".join("<th scope='col'>%s</th>" % x for x in headers) + "</tr></thead><tbody>"
    h += "".join("<tr>%s</tr>" % "".join(r) for r in rows) + "</tbody></table></div>"
    return h + (("<p class='note'>%s</p>" % note) if note else "")


SHORT = [("X8", X8), ("X10", X10), ("X11", X11), ("K13", K13), ("BENCH", BENCH), ("A", HERE), ("N", N_DIR)]


def short(path):
    for k, p in SHORT + [("R", os.path.join(CRB, "results"))]:
        if path.startswith(p + "/"):
            return k + path[len(p):]
    return path


def listing_sections(path):
    """{section name: [normalised instruction lines]} of an objdump record ('=== name ===' headers)"""
    out, cur = {}, None
    for line in Src.get(path).L:
        m = re.match(r"^=== (.+) ===$", line)
        if m:
            cur = out.setdefault(m.group(1), [])
            continue
        m = re.match(r"^\s+[0-9a-f]+:\t(.*)$", line)
        if m and cur is not None:
            t = re.sub(r"\b[0-9a-f]+ <k_\w+?(\+0x[0-9a-f]+)?>", r"<\1>", m.group(1))
            # a target outside the kernel (stack check, data page): keep the symbol, drop the absolute address
            t = re.sub(r"\b[0-9a-f]+ <([^>+]+)(\+0x[0-9a-f]+)?>", r"<\1>", t)
            cur.append(re.sub(r"\s+", " ", t).strip())
    return out


def loop_mod64(path, binary, kernel):
    for line in Src.get(path).L:
        c = line.split("\t")
        if len(c) >= 6 and c[0] == binary and c[1] == kernel:
            return int(c[5]), c[4], c[2]
    die("no row %s %s in %s" % (binary, kernel, path))


# ------------------------------------------------------------------------------------------- the page
class Easy:
    def __init__(self, J, date):
        self.J = J
        self.date = date
        results = J.get("results_folder") or os.path.join(CRB, "results")
        self.results = results
        self.dec = os.path.join(X8, "DECISIONS-bwx8.md")
        self.rep = RF.Report(J, results, self.dec, date)        # access helpers and file readers only
        self.R = RF.Refs()
        self.n_fig = self.n_tab = self.n_exc = self.n_codetab = 0
        self.exc_lines = 0
        self._refs()
        self.v = {}
        self.load()

    # ---------------------------------------------------------------- references
    def _refs(self):
        R, J = self.R, self.J
        c = lambda p: "<code>%s</code>" % esc(p)
        R.define("final8", "%s and %s: every number and every verdict of the analysis. Written by %s." % (
            c(os.path.join(HERE, "final8.json")), c(os.path.join(HERE, "final8.txt")), c(os.path.join(HERE, "final8.py"))))
        R.define("full", "%s: the full report with every step, table and deviation." % c(os.path.join(N_DIR, "tackle-8mb-report.html")))
        R.define("results", "%s: the result handoff. Sections &quot;The answer, with its evidence&quot;, &quot;Which share is "
                            "explained, and what stays open&quot; and &quot;What ran&quot;." % c(os.path.join(N_DIR, "tackle-8mb-results.md")))
        R.define("design", "%s: the design of the investigation. Section &quot;What counts as progress, and what counts as "
                           "an answer&quot;." % c(os.path.join(N_DIR, "tackle-8mb.md")))
        R.define("handoff", "%s: the goal and its three conditions (section &quot;Short version&quot; and the lines after "
                            "&quot;The goal is reached only when all three points hold&quot;)." % c(os.path.join(N_DIR, "tackle-8mb-handoff.md")))
        R.define("decisions", "%s: every decision rule, written before the data of its step. P1 and P2: heading &quot;P1, P2, the "
                              "decomposition&quot;. Step H2: the line that starts &quot;Step `H2`&quot;. Step ZN: rule 2 of round 4. "
                              "Step ZS: heading &quot;Round 4, session 1&quot;." % c(self.dec))
        R.define("orig", "%s: the first measurement of 2026-11-13 (original program, CPUs 0 and 2)." % c(
            os.path.join(self.results, ORIG_FOLDER, "one-thread.csv")))
        for st in ("S2", "S4", "ZS", "ZN", "YF", "H2"):
            fl = [f for s in RF.SESSIONS for f in self.rep.folders(st, s)]
            if not fl:
                die("no result folder for step %s in final8.json" % st)
            R.define("step:" + st, "Step %s, result folders under %s: %s." % (st, c(self.results), ", ".join(c(f) for f in fl)))
        R.define("x8", "%s: runner source %s, run scripts %s and %s, visit scripts %s and %s, schedule %s, plan files %s, build "
                       "record %s." % (c(X8), c("bwx8.c"), c("run_bwx8.sh"), c("run_h2.sh"), c("visit8.sh"), c("visit_h2.sh"),
                                       c("schedule8.py"), c("sched/"), c("crb-build-1/")))
        R.define("x11", "%s: runner source %s, run script %s, visit script %s, schedules %s and %s, plan files %s, build record "
                        "%s." % (c(X11), c("bwx11.c"), c("run_bwx11.sh"), c("visit11.sh"), c("schedule11.py"), c("schedule_zs.py"),
                                 c("sched11/"), c("crb-build-1/")))
        R.define("x10", "%s: the build %s and its scripts (%s, %s). Step YF ran with it." % (
            c(X10), c("bwx10"), c("run_bwx10.sh"), c("visit10.sh")))
        R.define("bench", "%s: the original benchmark (source of %s). %s: its older state (source of %s). Build record: %s." % (
            c(os.path.join(BENCH, "bandwidth.c")), c("bw_new"), c(os.path.join(K13, "bandwidth.orig.c")), c("bw_old"),
            c(os.path.join(self.results, PROBE_FOLDER, "probe.txt"))))
        R.define("analysis", "%s: the analysis programs %s, %s, %s, %s, and this page's generator %s." % (
            c(HERE), c("levels9.py"), c("analyze8.py"), c("final8.py"), c("h2_analyze.py"), c("easy_report.py")))
        R.define("palette", "The dataviz skill, file %s: categorical slots 1 (blue) and 2 (orange), documented there as "
                            "validated for colour-blind readers." % c("references/palette.md"))

    def sref(self, *steps):
        return self.R(*["step:" + s for s in steps])

    # ---------------------------------------------------------------- numbers
    def zs_cells(self, kernel, size):
        out = []
        for c, s in CELLS:
            r = self.rep.one("ZS.rows", kernel=kernel, size=size, cpu=c, session=s)
            if r is None:
                die("no ZS row %s %s cpu %d session %d" % (kernel, size, c, s))
            out.append(r)
        return out

    def read_original(self):
        """repetition rates of the first measurement: {(binary, size label): [(rate, cpu)]}"""
        path = os.path.join(self.results, ORIG_FOLDER, "one-thread.csv")
        out, cur = {}, None
        for line in Src.get(path).L:
            m = re.match(r"-- binary (\S+) kernel (\S+) threads 1 cpus (\S+) bytes (\S+) round", line)
            if m:
                cur = m.groups()
            elif cur and cur[1] == "read" and line.startswith("read,"):
                q = line.split(",")
                if q[3].isdigit():
                    out.setdefault((cur[0], cur[3]), []).append((float(q[6]), cur[2]))
        for k in (("bw_old", "1M"), ("bw_new", "1M"), ("bw_old", "8M"), ("bw_new", "8M")):
            if len(out.get(k, [])) != 12:
                die("first measurement: %d repetitions for %s, 12 expected (%s)" % (len(out.get(k, [])), k, path))
        return out

    def load(self):
        v, J, rep = self.v, self.J, self.rep
        # the first measurement
        o = self.read_original()
        v["orig"] = o
        v["og"] = {}
        for size in ("1M", "8M"):
            old, new = max(r for r, _ in o[("bw_old", size)]), max(r for r, _ in o[("bw_new", size)])
            v["og"][size] = (old, new, 100.0 * (new / old - 1.0))
        if not (v["og"]["8M"][2] < 2.0 < 20.0 < v["og"]["1M"][2]):
            die("first measurement: the recomputed gains %r do not show the observation" % (v["og"],))
        v["orig_new8"] = [r for r, _ in o[("bw_new", "8M")]]
        # step S2
        v["s2"] = {}
        for size in ("1M", "8M"):
            for c, s in CELLS:
                cell = rep.r1cell(size, c, s)
                if cell is None:
                    die("no round1 cell %s cpu %d session %d" % (size, c, s))
                v["s2"][size, c, s] = cell
        v["g1"] = [v["s2"]["1M", c, s]["new_minus_old"]["gain_pct"] for c, s in CELLS]
        v["g8"] = [v["s2"]["8M", c, s]["new_minus_old"]["gain_pct"] for c, s in CELLS]
        v["g8asm"] = [v["s2"]["8M", c, s]["asm_minus_old"]["gain_pct"] for c, s in CELLS]
        v["pc"] = {(c, s): J["round1"]["per_cell"]["cpu%d/s%d" % (c, s)] for c, s in CELLS}
        v["units"] = len(v["s2"]["1M", 2, 1]["new_minus_old"]["sets"])
        # step ZS
        a1, a8 = self.zs_cells("asmread", "1M"), self.zs_cells("asmread", "8M")
        o1, o8 = self.zs_cells("oldread", "1M"), self.zs_cells("oldread", "8M")
        v["a1"], v["a8"], v["o1"], v["o8"] = a1, a8, o1, o8
        v["fit"] = {(c, s): rep.zs_fit(c, s) for c, s in CELLS}
        v["icept"] = med([f[0] for f in v["fit"].values()])
        v["slope"] = med([f[1] for f in v["fit"].values()])
        v["zsrule"] = {(c, s): J["ZS"]["rule"]["cpu%d/s%d" % (c, s)] for c, s in CELLS}
        src = Src.get(os.path.join(HERE, "final8.py"))
        ln = src.find("ZS_BASE, ZS_LO, ZS_HI, ZS_TOL =")
        v["band"] = [float(x) for x in src.L[ln - 1].split("=")[1].split(",")]
        ln = src.find("ZS_OLD_CYC, ZS_OLD_TOL, ZS_OLD_R =")
        v["oldrule"] = [float(x) for x in src.L[ln - 1].split("=")[1].split(",")]
        ln = src.find("H2_LOW_MAX, H2_HIGH_MIN, H2_ORIGINAL_GAIN =")
        v["h2rule"] = [float(x) for x in src.L[ln - 1].split("=")[1].split(",")]
        # the recorded check of old read (rule of step ZS): points with r below the limit against one cycle count
        v["old_checked"] = sum(z["oldread_checked"] for z in v["zsrule"].values())
        v["old_fails"] = [(k, q) for z in v["zsrule"].values() for k, q in z["oldread"].items() if q["holds"] is False]
        if len(v["old_fails"]) != sum(z["oldread_fails"] for z in v["zsrule"].values()):
            die("step ZS: the old-read fail count and the per-size flags differ")
        for z in v["zsrule"].values():
            for k in ("1M", "8M"):
                if z["oldread"][k]["holds"] is not True:
                    die("step ZS: old read at %s is outside its recorded check; the prose of section 2 would be wrong" % k)
        v["zs_sizes"] = sorted({r["size_bytes"] for r in rep.rows("ZS.rows", kernel="asmread")})
        # the gain that the cycle counts of step ZS give (computed here)
        v["cg1"] = [100.0 * (o["cyc"] / a["cyc"] - 1.0) for o, a in zip(o1, a1)]
        v["cg8"] = [100.0 * (o["cyc"] / a["cyc"] - 1.0) for o, a in zip(o8, a8)]
        # step ZN and the supplementary gain
        Z = J["families"]["ZN"]
        v["zn"] = {(c, s): Z["rule2"]["cpu%d/s%d" % (c, s)] for c, s in CELLS}
        v["sup"] = J["supplementary"]["gain_from_two_rates"]
        # step H2 and the levels of step S4
        v["h2"] = {(str(r["cpu"]), r["session"]): r for r in J["H2"]["rows"]}
        v["lev"] = {(c, s): rep.one("levels.rows", step="S4", kernel="asmread", cpu=c, session=s) for c, s in CELLS}
        v["levold"] = {(c, s): rep.one("levels.rows", step="S4", kernel="oldread", cpu=c, session=s) for c, s in CELLS}
        # the gain at each level (computed here): level median of asmread over the median of old read, step S4
        v["glow"], v["ghigh"] = [], []
        for c, s in CELLS:
            lv, lo = v["lev"][c, s], v["levold"][c, s]
            if lv is None or lo is None or lv["low"] is None or lv["high"] is None or not lo["one_level_rates"]:
                die("step S4: no two levels of asmread or no old read rate on CPU %d in session %d" % (c, s))
            old = med(lo["one_level_rates"])
            v["glow"].append(100.0 * (lv["low"] / old - 1.0))
            v["ghigh"].append(100.0 * (lv["high"] / old - 1.0))
        h2g = lambda cpu: [v["h2"][cpu, s]["median_gain_pct"] for s in RF.SESSIONS]
        v["gain_low"] = v["glow"] + h2g("2") + [v["og"]["8M"][2]]
        v["gain_high"] = v["ghigh"] + h2g("0")
        if max(v["gain_low"]) >= min(v["gain_high"]):
            die("the gains at the low and at the high level overlap; the prose of section 2 would be wrong")
        # run facts
        inv = J["inventory"]["rows"]
        v["procs"] = sum(r["processes"] for r in inv)
        v["bad"] = sum(r["killed"] + r["failed"] + r["incomplete"] + r["x_rows"] for r in inv)
        v["load"] = (min(r["load_min"] for r in inv), max(r["load_max"] for r in inv))
        gaps = []
        for st in ("S2", "ZS", "ZN", "H2"):
            r1 = next(r for r in inv if r["step"] == st and r["session"] == 1)
            r2 = next(r for r in inv if r["step"] == st and r["session"] == 2)
            t = lambda x: sum(int(q) * m for q, m in zip(x.split(":"), (3600, 60, 1)))
            g = (t(r2["first_launch_utc"]) - t(r1["last_launch_utc"])) / 3600.0
            if g <= 0:
                die("step %s: session 2 does not start after session 1" % st)
            gaps.append(g)
        v["gaps"] = gaps
        v["inv"] = {(r["step"], r["session"]): r for r in inv}

    # ---------------------------------------------------------------- small HTML helpers
    def fig(self, title, leg, body, takeaway, extra=""):
        self.n_fig += 1
        return RF.figure("Figure %d. %s" % (self.n_fig, title), leg, body, takeaway, extra)

    def tab(self, headers, rows, caption, note=None, cls=""):
        self.n_tab += 1
        return table(headers, rows, "Table %d. %s" % (self.n_tab, caption), note, cls)

    def svg(self, plots, aria):
        s = self.rep.draw(plots, aria)
        if self.rep.drops:
            die("chart label without room: %s" % self.rep.drops)
        return s

    @staticmethod
    def line_sw(color, dash=None):
        return ("<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'><path d='M1,7 L15,7' "
                "stroke='%s' stroke-width='2'%s/></svg>" % (color, (" stroke-dasharray='%s'" % dash) if dash else ""))

    @staticmethod
    def rect_sw(color, opacity=1.0):
        return ("<svg class='sw' viewBox='0 0 16 14' width='16' height='14' aria-hidden='true'><rect x='1' y='2' width='14' "
                "height='10' rx='2' fill='%s' opacity='%.2f'/></svg>" % (color, opacity))

    @staticmethod
    def dual(wide, narrow):
        return "<div class='wide'>%s</div><div class='narrow'>%s</div>" % (wide, narrow)

    # ================================================================== section 0
    def sec_head(self):
        v = self.v
        res = os.path.join(N_DIR, "tackle-8mb-results.md")
        fact(res, "128 cores, 2.8 GHz")
        fact(res, "64 KiB first-level cache (L1) and a 2 MiB second-level cache (L2)")
        fact(res, "128 MiB system-level cache (SLC)")
        r8 = [r["r"] for r in v["a8"]]
        # share of the 1 MiB advantage (in cycles per line) that the extra cycles at 8 MiB remove, per cell
        lost = [(a8["cyc"] - a1["cyc"]) / (o1["cyc"] - a1["cyc"]) for a1, a8, o1 in zip(v["a1"], v["a8"], v["o1"])]
        if min(lost) <= 0.5:
            die("the extra cycles at 8 MiB remove %.0f %% of the advantage in one cell: 'most' would be wrong" % (100 * min(lost)))
        h = "<h1>Why the new read loop gains so little at 8 MiB</h1>"
        h += ("<p class='meta'>Easy-read version of the full report %s. Built %s by <code>easy_report.py</code> from "
              "<code>final8.json</code> %s.</p>" % (self.R("full"), esc(self.date), self.R("final8")))
        h += "<div class='short'><h2>Short version</h2><ul>"
        h += ("<li><b>The question.</b> The new read loop is %s %% faster than the old loop at a 1 MiB buffer, and only "
              "about 1 %% faster at 8 MiB (first measurement: %s %%).</li>" % (
                  fnum(v["og"]["1M"][2], 0), fnum(v["og"]["8M"][2], 2)))
        h += ("<li><b>The cause.</b> At 8 MiB about %.0f %% of the 64-byte lines come from the shared cache (SLC), and each of "
              "them costs the new loop about %s extra processor cycles, which removes most of its advantage.</li>" % (
                  100 * med(r8), fnum(v["slope"], 2)))
        h += ("<li><b>The first measurement.</b> At 8 MiB the new loop runs at one of two rate levels, and the first "
              "measurement was at the low level.</li></ul></div>")
        words = [
            ("CRB", "The test machine: an Arm Phoenix Reference Server with 128 cores at 2.8 GHz."),
            ("L1, L2, SLC", "The three cache levels. L1 (64 KiB) and L2 (2 MiB) belong to one core. The SLC "
                            "(system-level cache, 128 MiB) is shared by all cores."),
            ("line", "One 64-byte cache line."),
            ("kernel", "Here: one small read loop of the benchmark. It is not the kernel of the operating system."),
            ("old read (<code>oldread</code>)", "The read loop of the original benchmark. It loads the data and adds it up."),
            ("new loop (<code>read</code>, <code>asmread</code>)", "The load-only read loop. <code>read</code> is written "
             "in C and <code>asmread</code> in assembly. Both only load the data."),
            ("original program (<code>bw_old</code>, <code>bw_new</code>)", "The benchmark as it was before this "
             "investigation. <code>bw_old</code> holds the old read loop and <code>bw_new</code> the new one."),
            ("runner (<code>bwx8</code>, <code>bwx10</code>, <code>bwx11</code>)", "The test program of this investigation. "
             "It runs one loop on one CPU in timed windows. The three names are three builds of it."),
            ("rate", "Bytes read per second, in GB/s (1 GB = 1e9 bytes)."),
            ("core rate (C)", "The rate of a loop at 32 KiB, where all data is in L1. It measures how fast the loop itself "
                              "is. It is not a strict upper limit: old read is slightly faster at 1 MiB."),
            ("gain", "100 x (new rate / old rate - 1), in percent."),
            ("cycles per line", "Processor cycles spent per 64-byte line (counter <code>cpu_cycles</code>)."),
            ("r", "L2 refills per line (counter <code>l2d_cache_refill</code>). It is the share of lines that enter L2 "
                  "from the SLC."),
            ("session", "One set of visits to CRB. Session 2 repeats session 1 at least 3 hours later."),
            ("cell", "One CPU in one session. There are 4 cells: CPUs 2 and 41, sessions 1 and 2 (s1, s2)."),
            ("step", "One batch of test processes with a short name, for example S2 or ZS."),
            ("window", "One timed interval of 0.3 s inside a test process."),
            ("level", "At 8 MiB the new loop runs at one of two rates. They are called the low and the high level."),
            ("nop", "A no-operation instruction. It costs time in the core and touches no data."),
            ("hypothesis (H1, H1c, H2, ...)", "A named idea under test."),
            ("as recorded", "The verdict text that the analysis wrote into <code>final8.json</code>, by a rule from the "
                            "decisions file."),
            ("supplementary", "An evaluation that was defined after the data was seen. It never replaces a recorded verdict."),
        ]
        h += "<details class='words'><summary>Words used here (%d terms, click to open)</summary><dl class='wl'>" % len(words)
        h += "".join("<dt>%s</dt><dd>%s</dd>" % w for w in words)
        h += "</dl></details>"
        return h

    # ================================================================== section 1
    def sec_goal(self):
        v = self.v
        fact(os.path.join(N_DIR, "tackle-8mb-handoff.md"), "A named mechanism explains the small gain at 8 MiB.")
        fact(os.path.join(N_DIR, "tackle-8mb-handoff.md"), "A controlled test changed that mechanism, and the gain changed as predicted.")
        fact(os.path.join(N_DIR, "tackle-8mb-handoff.md"), "which share of the gap the test explains, and what stays unexplained")
        h = "<h2 id='goal'>1. The goal</h2>"
        h += ("<p><b>The observation.</b> The benchmark got a new read loop that only loads the data. The old loop loads "
              "the data and adds it up. The first measurement compared the two %s:</p>" % self.R("orig"))
        rows = []
        for size in ("1M", "8M"):
            old, new, g = v["og"][size]
            rows.append([RF.TH(size_name(size)), RF.V(old), RF.V(new), RF.CC("gain", (new, old))])
        h += self.tab(["Buffer size", "old read, GB/s", "new read, GB/s", "gain, % (calc.)"], rows,
                      "The first measurement (2026-11-13, original program, CPUs 0 and 2).",
                      note="Each rate is the best of the 12 repetitions of 0.5 s per loop and size. Gain = 100 x (new rate / "
                           "old rate - 1), computed here.")
        h += ("<p><b>The question.</b> Why does the new loop raise the read rate by %s %% at 1 MiB, and by only %s %% at "
              "8 MiB?</p>" % (fnum(v["og"]["1M"][2], 0), fnum(v["og"]["8M"][2], 2)))
        h += ("<p><b>The machine in three lines.</b></p><ul>"
              "<li>The test machine is called CRB. Each core has two caches of its own: L1 (64 KiB) and L2 (2 MiB).</li>"
              "<li>All cores share a third cache, the SLC (system-level cache, 128 MiB).</li>"
              "<li>A 1 MiB buffer fits in L2. An 8 MiB buffer does not. At 8 MiB about %.0f %% of the 64-byte lines "
              "enter L2 from the SLC (measured, section 2) %s.</li></ul>" % (
                  100 * med([r["r"] for r in v["a8"]]), self.R("results")))
        h += ("<p><b>What counts as an answer.</b> Three things must hold %s:</p><ol>"
              "<li>A named mechanism explains the small gain at 8 MiB.</li>"
              "<li>A controlled test changes that mechanism. The gain then changes as predicted, on both CPUs and in "
              "both sessions.</li>"
              "<li>The report states which share is explained and what stays unexplained.</li></ol>" % self.R("handoff"))
        return h

    # ================================================================== section 2
    def answer_svg(self, narrow):
        v, rep = self.v, self.rep
        W, H = (350, 386) if narrow else (760, 416)
        fs = 11 if narrow else 12.5
        p = RF.Plot((0.88, 37.0), (2.0, 2.9), W=W, H=H, ml=40 if narrow else 52, mr=10 if narrow else 16, mt=68, mb=46, xlog=True)
        p.frame()
        p.raw_text(2, 14, "%s per 64-byte line (axis starts at 2.0)" % ("Cycles" if narrow else "Processor cycles"), fs=12,
                   cls="ttl", obstacle=False)
        p.yticks([2.0, 2.2, 2.4, 2.6, 2.8], "%.1f")
        ticks = [1, 2, 4, 8, 16, 32]
        p.xticks(ticks, labels=["%d" % t for t in ticks], title="buffer size, MiB (log scale)")
        ser = {}
        for k in ("oldread", "asmread"):
            by = {}
            for c, s in CELLS:
                for row in rep.zs(k, c, s):
                    by.setdefault(row["size_bytes"], []).append(row)
            ser[k] = [(b / MIB, rows) for b, rows in sorted(by.items())]
            if any(len(rows) != 4 for _, rows in ser[k]):
                die("step ZS: a size of %s does not have 4 cells" % k)
        # r of the new loop, as a row of text above the plot
        p.raw_text(p.fx0, p.fy0 - 26, "r = share of lines that come from the SLC (new loop):", fs=11, cls="ax", obstacle=False)
        for mib, rows in ser["asmread"]:
            if mib in ticks:
                p.raw_text(p.X(mib), p.fy0 - 8, "%.2f" % med([r["r"] for r in rows]), "middle", 11, "lab b", False)
        # L2 size
        x2 = p.X(2)
        p.path([(x2, p.fy0), (x2, p.fy1)], RF.C_AXIS, 1, dash="3 3")
        p.raw_text(x2 + 4, p.fy1 - 6, "L2 holds 2 MiB", fs=10, cls="ax", obstacle=False)
        name = {"oldread": "old read", "asmread": "new loop"}
        medv = {}
        for k, col in (("oldread", C_OLD), ("asmread", C_NEW)):
            up = [(p.X(m), p.Y(max(r["cyc"] for r in rows))) for m, rows in ser[k]]
            dn = [(p.X(m), p.Y(min(r["cyc"] for r in rows))) for m, rows in ser[k]]
            p.area(up + dn[::-1], col, 0.18)
            pts = []
            for m, rows in ser[k]:
                y = med([r["cyc"] for r in rows])
                medv[k, m] = y
                pts.append((p.X(m), p.Y(y)))
            p.path(pts, col, 2, layer="marks")
            for (m, rows), (x, y) in zip(ser[k], pts):
                p.dot(x, y, col, r=3.5, tip="%s, %g MiB: %s cycles per line (CPU 2 s1, CPU 2 s2, CPU 41 s1, CPU 41 s2)" % (
                    name[k], m, ", ".join("%.3f" % r["cyc"] for r in rows)))
        # the two gaps
        def bracket(x, y0, y1):
            p.marks.append("<path d='M%.1f,%.1f h4 M%.1f,%.1f V%.1f M%.1f,%.1f h4' fill='none' stroke='%s' stroke-width='1.4'/>" % (
                x - 2, y0, x, y0, y1, x - 2, y1, C_INK))
        gap1 = [o["cyc"] - a["cyc"] for o, a in zip(v["o1"], v["a1"])]
        gap8 = [o["cyc"] - a["cyc"] for o, a in zip(v["o8"], v["a8"])]
        xb = p.X(1) + 10
        bracket(xb, p.Y(medv["oldread", 1.0]) + 6, p.Y(medv["asmread", 1.0]) - 6)
        y = p.Y(2.56)
        p.raw_text(xb + 8, y, "gap %s cycles" % rng(gap1), fs=fs, cls="lab", obstacle=False)
        p.raw_text(xb + 8, y + 1.3 * fs, "= gain %s %%" % rng(v["cg1"], 0), fs=fs, cls="lab b", obstacle=False)
        xb = p.X(8) + 10
        y0, y1 = p.Y(medv["oldread", 8.0]) + 2, p.Y(medv["asmread", 8.0]) - 2
        bracket(xb, y0, y1)
        y = p.Y(2.32)
        p.path([(xb, y1 + 3), (xb, y - fs)], C_INK, 1, dash="2 2", layer="marks")
        if narrow:
            p.raw_text(p.fx1 - 6, y, "gap %s cycles" % rng(gap8), "end", fs, "lab", False)
            p.raw_text(p.fx1 - 6, y + 1.3 * fs, "= gain %s %%" % rng(v["cg8"], 1), "end", fs, "lab b", False)
        else:
            p.raw_text(xb + 8, y, "gap %s cycles" % rng(gap8), fs=fs, cls="lab", obstacle=False)
            p.raw_text(xb + 8, y + 1.3 * fs, "= gain %s %%" % rng(v["cg8"], 1), fs=fs, cls="lab b", obstacle=False)
        # series names, inside the plot
        p.raw_text(p.X(4.6), p.Y(2.715), "old read", fs=fs, cls="lab b", obstacle=False)
        p.raw_text(p.X(2.6), p.Y(2.13), "new loop (asmread)", fs=fs, cls="lab b", obstacle=False)
        return self.svg([p], "Cycles per 64-byte line against the buffer size for old read and the new loop, step ZS")

    def sec_answer(self):
        v = self.v
        h = "<h2 id='answer'>2. The answer in one picture</h2>"
        h += ("<p>The figure shows what one 64-byte line costs each loop, in processor cycles. Fewer cycles per line means "
              "a higher rate. The letter r stands for the share of lines that enter L2 from the SLC.</p>")
        leg = [(self.line_sw(C_OLD), "old read: median of the 4 cells"),
               (self.line_sw(C_NEW), "new loop (asmread): median of the 4 cells"),
               (self.rect_sw(C_INK2, 0.25), "shaded: lowest to highest of the 4 cells")]
        fact(self.dec, "2.52 (high level) to 2.67 (low level) cycles")
        h4 = self.rep.claim("H4")["overall"]
        if "cpu_cycles: confirmed: differs between the levels" not in h4:
            die("the recorded verdict on the cycle count by level is not 'confirmed'; the note of Figure 1 would be wrong")
        lv4 = self.rep.rows("levels.rows", step="XW", kernel="read", size="4M")
        if len(lv4) != 4 or not all(r["two_levels"] for r in lv4):
            die("step XW: two levels at 4 MiB are not recorded in all 4 cells; the note of Figure 1 would be wrong")
        spread = {}
        for r in self.rep.rows("ZS.rows", kernel="asmread"):
            spread.setdefault(r["size_bytes"], []).append(r["cyc"])
        wide = sorted(spread, key=lambda b: max(spread[b]) - min(spread[b]))[-4:]
        if not all(4 << 20 <= b <= 8 << 20 for b in wide):
            die("step ZS: the 4 sizes with the widest spread are not 4 to 8 MiB; the note of Figure 1 would be wrong")
        h += self.fig("What one 64-byte line costs, by buffer size (step ZS)", leg,
                      self.dual(self.answer_svg(False), self.answer_svg(True)),
                      "Old read costs about the same at every size. The new loop starts far below it and rises to it as "
                      "more lines come from the SLC. At 8 MiB the gap is almost closed.",
                      "<ul class='note'><li>A cell is one CPU in one session: CPUs 2 and 41, sessions 1 and 2.</li>"
                      "<li>The gain on the figure is computed here from the two cycle counts: old / new - 1. "
                      "A range covers the 4 cells.</li>"
                      "<li>The blue shading is wide from 4 to 8 MiB. Two rate levels of the new loop are recorded at 4 MiB "
                      "and at 8 MiB (step 5), and at 8 MiB the cycle count differs between them %s %s. Hypothesis: each "
                      "cell had a different mix of the two levels.</li>"
                      "<li>Hover over a point for the 4 cell values.</li></ul>" % (self.R("final8"), self.R("decisions")))
        h += ("<p><b>The gain at 8 MiB is not one number.</b> At 8 MiB the new loop runs at one of two rates, called the "
              "low and the high level (step 5). Runs at the low level show a gain of %s to %s %%. Runs at the high level "
              "show %s to %s %%. Each step below reports the gain of its own runs, so the values differ from step to "
              "step.</p>" % (
                  fnum(min(v["gain_low"]), 1), fnum(max(v["gain_low"]), 1), fnum(min(v["gain_high"]), 1), fnum(max(v["gain_high"]), 1)))
        h += ("<p class='note'>Low level: step H2 on CPU 2, the first measurement, and the low level of step S4. High level: "
              "step H2 on CPU 0 and the high level of step S4. The S4 gains are computed here: level median of "
              "<code>asmread</code> over the median of old read %s %s.</p>" % (self.sref("S4", "H2"), self.R("orig")))
        rows = []
        for size, a, o, cg in (("1M", v["a1"], v["o1"], v["cg1"]), ("8M", v["a8"], v["o8"], v["cg8"])):
            rows.append([RF.TH(size_name(size)), RF.TX(rng([r["r"] for r in a], 2), "num"),
                         RF.TX(rng([r["cyc"] for r in o], 2), "num"), RF.TX(rng([r["cyc"] for r in a], 2), "num"),
                         RF.TX(rng(cg, 1), "num calc")])
        h += self.tab(["Buffer size", "r of the new loop", "old read, cycles per line", "new loop, cycles per line",
                       "gain from these cycles, % (calc.)"], rows,
                      "The numbers behind the figure (step ZS). Each range covers the 4 cells.",
                      note="Loops <code>oldread</code> and <code>asmread</code>. Gain = 100 x (old cycles / new cycles - 1), "
                           "computed here.")
        fails = v["old_fails"]
        osz = sorted({k for k, _ in fails}, key=lambda t: float(t[:-1]))
        if len(osz) < 2:
            die("old read: fewer than 2 sizes outside the old-read check; the sentence of section 2 would be wrong")
        cross = None
        for b in v["zs_sizes"]:
            a = med([r["cyc"] for r in self.rep.rows("ZS.rows", kernel="asmread", size_bytes=b)])
            o = med([r["cyc"] for r in self.rep.rows("ZS.rows", kernel="oldread", size_bytes=b)])
            if a > o:
                cross = b
                break
        if cross is None:
            die("step ZS: the new loop never costs more than old read")
        before = max(b for b in v["zs_sizes"] if b < cross)
        v["cross"] = (before, cross)
        cyc0, tol, rlim = v["oldrule"]
        o18 = [r["cyc"] for r in v["o1"] + v["o8"]]
        h += "<p><b>The answer in words:</b></p><ul>"
        h += ("<li><b>Old read costs the same at 1 MiB and at 8 MiB:</b> %s cycles per line in all 4 cells. Between %s and "
              "%s MiB it costs up to %s cycles per line more in some cells. The recorded check of step ZS shows this: %d of "
              "its %d old-read points lie more than %s cycles per line away from %s. This rise is not explained. It does "
              "not occur at 1 MiB or at 8 MiB %s.</li>" % (
                  rng(o18, 2), osz[0][:-1], osz[-1][:-1], fnum(max(q["cyc"] for _, q in fails) - cyc0, 2), len(fails),
                  v["old_checked"], fnum(tol, 2), fnum(cyc0, 3), self.sref("ZS")))
        h += ("<li><b>The new loop is fast while the data comes from L2.</b> At 1 MiB r is %s and the loop costs %s cycles "
              "per line %s.</li>" % (
                  rng([r["r"] for r in v["a1"]], 2), rng([r["cyc"] for r in v["a1"]], 2), self.sref("ZS")))
        h += ("<li><b>Each line from the SLC costs the new loop about %s cycles more.</b> A straight line fitted to the "
              "points gives about %s + %s x r cycles per line (medians of the 4 cells) %s.</li>" % (
                  fnum(v["slope"], 2), fnum(v["icept"], 2), fnum(v["slope"], 2), self.R("final8")))
        h += ("<li><b>At 8 MiB most lines come from the SLC.</b> There r is %s. The new loop then costs %s cycles per line, "
              "and old read costs %s. So the gain is small %s.</li>" % (
                  rng([r["r"] for r in v["a8"]], 2), rng([r["cyc"] for r in v["a8"]], 2),
                  fnum(med([r["cyc"] for r in v["o8"]]), 2), self.sref("ZS")))
        h += ("<li><b>Nothing special happens at exactly 8 MiB.</b> The median cost of the new loop passes the cost of old read "
              "between %g and %g MiB %s.</li></ul>" % (before / MIB, cross / MIB, self.sref("ZS")))
        return h

    # ================================================================== section 3: the flow
    def flow_nodes(self):
        v, J = self.v, self.J
        zs_in = ["%d of %d" % (c["evaluated"] - c["outside"], c["evaluated"]) for c in v["zsrule"].values()]
        if len(set(zs_in)) != 1 or any(c["exceeds"] for c in v["zsrule"].values()):
            die("step ZS: the cells differ, or a cell exceeds the rule; box 3 of the flow would be wrong")
        if not all(v["zn"][c, s]["kernels"][k]["prediction_holds"] for c, s in CELLS for k in ("read_nop96", "read_nop128")):
            die("step ZN: a slowed loop does not keep its rate; box 4 of the flow would be wrong")
        if J["H2"]["verdict"]["cpu2"] != "supported":
            die("step H2: CPU 2 is not 'supported'; box 5 of the flow would be wrong")
        short_v = lambda s: s.split(" (")[0].split(":")[0]
        if not (J["YL"]["overall"].startswith("not confirmed") and J["YP"]["overall"].startswith("not confirmed")):
            die("H7: the recorded overall verdicts do not start with 'not confirmed'")
        dead1 = ["H1b: %s" % short_v(J["prefetch"]["overall"]), "H1d: %s" % short_v(J["evict"]["overall"])]
        dead2 = ["H3a: %s" % self.rep.claim("H3a")["overall"].replace("H3a ", "").replace(" in both sessions", ""),
                 "H7: %s" % short_v(J["YP"]["overall"])]
        return [
            ("start", "Observed gain", ["1 MiB: +%s %%" % fnum(v["og"]["1M"][2], 0),
                                        "8 MiB: +%s %%" % fnum(v["og"]["8M"][2], 2)], []),
            ("main", "1. Which loop changes?", ["Step S2: only the new loop falls."], []),
            ("main", "2. What limits it at 8 MiB?", ["Two ideas tested, not confirmed."], dead1),
            ("main", "3. The cost follows r", ["Step ZS: inside the band in 4 of 4 cells."], []),
            ("main", "4. A controlled test", ["Step ZN: slowed loops keep their rate."], []),
            ("main", "5. Why %s %% at first?" % fnum(v["og"]["8M"][2], 2),
             ["Step H2: two rate levels. CPU 2 was at the low one."], dead2),
            ("start", "Answer", ["Lines from the SLC cost the new loop extra cycles."], []),
        ]

    @staticmethod
    def _wrap(w, title, body, fs):
        n = max(8, int((w - 18) / (fs * 0.56)))
        tl = textwrap.wrap(title, max(8, int((w - 18) / (fs * 0.61))))
        bl = [ln for para in body for ln in textwrap.wrap(para, n)]
        lh = fs * 1.34
        return tl, bl, 10 + len(tl) * lh + (5 if bl else 0) + len(bl) * lh + 6

    @staticmethod
    def _box(x, y, w, h, tl, bl, kind, fs):
        style = {"start": "fill='#eaf2fc' stroke='%s' stroke-width='1.4'" % C_NEW,
                 "main": "fill='#ffffff' stroke='%s' stroke-width='1.2'" % C_INK2,
                 "dead": "fill='#f3f2ee' stroke='%s' stroke-width='1' stroke-dasharray='4 3'" % C_PRED}[kind]
        s = "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='6' %s/>" % (x, y, w, h, style)
        lh = fs * 1.34
        ty = y + 10 + fs * 0.85
        for t in tl:
            s += "<text x='%.1f' y='%.1f' font-size='%s' class='%s'>%s</text>" % (
                x + 9, ty, fs, "fd" if kind == "dead" else "b", esc(t))
            ty += lh
        ty += 5
        for t in bl:
            s += "<text x='%.1f' y='%.1f' font-size='%s'>%s</text>" % (x + 9, ty, fs, esc(t))
            ty += lh
        return s

    @staticmethod
    def _arrow(x0, y0, x1, y1):
        if y0 == y1:
            head = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x1, y1, x1 - 6, y1 - 4, x1 - 6, y1 + 4)
        else:
            head = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x1, y1, x1 - 4, y1 - 6, x1 + 4, y1 - 6)
        return ("<path d='M%.1f,%.1f L%.1f,%.1f' stroke='%s' stroke-width='1.5' fill='none'/><polygon points='%s' fill='%s'/>"
                % (x0, y0, x1, y1, C_INK2, head, C_INK2))

    def flow_svg(self, narrow):
        nodes = self.flow_nodes()
        fs = 13
        note = "Dashed grey boxes: ideas that were tested and not confirmed."
        s = ""
        if not narrow:
            W, gap = 1088, 14
            w = (W - gap * (len(nodes) - 1)) / float(len(nodes))
            wr = [self._wrap(w, t, b, fs) for _, t, b, _ in nodes]
            hm = max(x[2] for x in wr)
            hmax = hm
            for i, (kind, _, _, dead) in enumerate(nodes):
                x = i * (w + gap)
                s += self._box(x, 4, w, hm, wr[i][0], wr[i][1], kind, fs)
                if i:
                    s += self._arrow(x - gap + 1, 4 + hm / 2, x - 1, 4 + hm / 2)
                y = 4 + hm + 12
                for j, dt in enumerate(dead):
                    tl, bl, dh = self._wrap(w, dt, [], fs)
                    s += "<path d='M%.1f,%.1f V%.1f' stroke='%s' stroke-width='1.2' stroke-dasharray='4 3' fill='none'/>" % (
                        x + w / 2, y - (12 if j == 0 else 6), y, C_PRED)
                    s += self._box(x, y, w, dh, tl, bl, "dead", fs)
                    y += dh + 6
                    hmax = max(hmax, y - 4)
            H = hmax + 10
            s += "<text x='0' y='%.1f' font-size='12' class='fd'>%s</text>" % (H + 8, esc(note))
            H += 14
        else:
            W, w, wd = 380, 212, 150
            y, prev_bottom = 4, 0
            for i, (kind, t, b, dead) in enumerate(nodes):
                tl, bl, hm = self._wrap(w, t, b, fs)
                dd = [self._wrap(wd, dt, [], fs) for dt in dead]
                slot = max(hm, sum(d[2] for d in dd) + 6 * max(0, len(dd) - 1))
                if i:
                    s += self._arrow(2 + w / 2, prev_bottom + 1, 2 + w / 2, y - 1)
                s += self._box(2, y, w, hm, tl, bl, kind, fs)
                prev_bottom = y + hm
                yd = y
                for (dtl, dbl, dh) in dd:
                    if yd == y:
                        s += "<path d='M%.1f,%.1f H%.1f' stroke='%s' stroke-width='1.2' stroke-dasharray='4 3' fill='none'/>" % (
                            2 + w, yd + min(dh, hm) / 2, 2 + w + 14, C_PRED)
                    else:
                        s += "<path d='M%.1f,%.1f V%.1f' stroke='%s' stroke-width='1.2' stroke-dasharray='4 3' fill='none'/>" % (
                            2 + w + 14 + wd / 2, yd - 6, yd, C_PRED)
                    s += self._box(2 + w + 14, yd, wd, dh, dtl, dbl, "dead", fs)
                    yd += dh + 6
                y += slot + 22
            H = y - 14
            s += "<text x='2' y='%.1f' font-size='12' class='fd'>%s</text>" % (H + 6, esc("Dashed grey boxes: tested, not confirmed."))
            H += 12
        return ("<svg class='chart flow' viewBox='0 0 %d %d' role='img' aria-label='%s'>%s</svg>" % (
            W, H, esc("Flow of the thinking: observation, five steps with their tests, ideas that were not confirmed, answer"), s))

    def qa(self, sid, title, q, idea, test, result, so, pre="", after="", fixed="(fixed before the data)"):
        return ("<section class='step' id='%s'><h3>%s</h3>%s<dl class='qa'>"
                "<dt>Question</dt><dd>%s</dd>"
                "<dt>Idea / prediction <span>%s</span></dt><dd>%s</dd>"
                "<dt>Test</dt><dd>%s</dd>"
                "<dt class='full'>Result</dt><dd class='full'>%s</dd>"
                "<dt class='so'>So</dt><dd class='so'>%s</dd></dl>%s</section>" % (
                    sid, title, pre, q, fixed, idea, test, result, so, after))

    # ---------------------------------------------------------------- step 1: S2
    def fig_s2(self):
        v = self.v
        svgs = []
        for size in ("1M", "8M"):
            p = RF.Plot((60, 92), (0, 1), W=400, H=40 + 30 * 4 + 44, ml=74, mr=72, mt=40, mb=44)
            p.frame()
            p.title("Buffer %s" % size_name(size), "rate, GB/s (axis starts at 60)")
            p.xticks([60, 65, 70, 75, 80, 85, 90], grid=True)
            p.raw_text(p.fx1 + 6, p.fy0 - 7, "gain", "start", 11, "ax", False)
            for i, (c, s) in enumerate(CELLS):
                cell = v["s2"][size, c, s]
                y = p.fy0 + 30 * (i + 0.5)
                p.raw_text(p.fx0 - 6, y + 4, "CPU %d, s%d" % (c, s), "end", 11, "ax", False)
                xo, xn = p.X(cell["oldread"]), p.X(cell["read"])
                p.path([(xo, y), (xn, y)], C_PRED, 2, layer="marks")
                p.dot(xo, y, C_OLD, tip="old read, %s, CPU %d, session %d: %.2f GB/s" % (size_name(size), c, s, cell["oldread"]))
                p.dot(xn, y, C_NEW, tip="new loop (read), %s, CPU %d, session %d: %.2f GB/s" % (size_name(size), c, s, cell["read"]))
                p.raw_text(xo - 8, y + 4, "%.2f" % cell["oldread"], "end", 11, "lab", False)
                p.raw_text(xn + 8, y + 4, "%.2f" % cell["read"], "start", 11, "lab", False)
                p.raw_text(p.fx1 + 6, y + 4, "+%.2f %%" % cell["new_minus_old"]["gain_pct"], "start", 11, "lab b", False)
            svgs.append(self.svg([p], "Rates of old read and the new loop at %s per CPU and session, step S2" % size_name(size)))
        leg = [(RF.sw(C_OLD), "old read (oldread)"), (RF.sw(C_NEW), "new loop (read)")]
        return self.fig("Old read against the new loop at 1 MiB and at 8 MiB (step S2)", leg, RF.panels(svgs),
                        "Only the blue dot moves. Old read stays at 67 GB/s. The new loop falls from 85 GB/s to about "
                        "70 GB/s.".replace("67", fnum(med([c["oldread"] for c in v["s2"].values()]), 0)).replace(
                            "85", fnum(med([v["s2"]["1M", c, s]["read"] for c, s in CELLS]), 0)).replace(
                            "about 70", rng([v["s2"]["8M", c, s]["read"] for c, s in CELLS], 0)),
                        "<p class='note'>s1 and s2 are the two sessions. Each dot is the median of the cell.</p>")

    def step1(self):
        v, J = self.v, self.J
        a8 = Src.get(os.path.join(HERE, "analyze8.py"))
        need(a8, a8.py_def("p1_cell"), "<= P1_MARGIN")
        need(a8, (1, 80), "'fourth': ('target', 3)")
        plan = Src.get(os.path.join(X8, "sched", "s1", "S2", "0000.plan"))
        trials = [ln.split() for ln in plan.L if ln and not ln.startswith("#")]
        nwin, win_ms = int(trials[0][7]), int(trials[0][8])
        pfx_ms = int(trials[0][4].split(":")[1])
        margin = v["pc"][2, 1]["P1"]["margin"]
        r1 = J["round1"]
        rows = []
        for c, s in CELLS:
            pc = v["pc"][c, s]
            rows.append([RF.TH("CPU %d, s%d" % (c, s)), RF.V(pc["P1"]["median"], 2), RF.V(pc["P2"]["read"]["median"]),
                         RF.TX("P1: %s. P2: %s." % (pc["P1"]["outcome"], "repeatable" if pc["P2"]["read"]["repeatable"] else "not repeatable"))])
        res = self.fig_s2()
        res += self.tab(["Cell", "old read: 8 MiB minus 1 MiB, GB/s", "new loop: 8 MiB minus 1 MiB, GB/s", "as recorded"], rows,
                        "The change of each loop from 1 MiB to 8 MiB per cell (step S2, medians).",
                        note="P1 is recorded as &quot;equivalent&quot; if old read moves by at most %s GB/s, with its run-to-run "
                             "spread included. P2 is recorded as &quot;repeatable&quot; if the fall has one sign in all %d sets of "
                             "processes and is larger than the run-to-run spread." % (fnum(margin, 2), v["units"]))
        cl = self.rep.claim("H1 / P1")
        res += ("<p class='verdict'><b>Verdict as recorded:</b> &quot;%s&quot; %s.</p>" % (esc(cl["overall"]), self.R("final8")))
        q = "Is the small gain at 8 MiB real? Which of the two loops changes between 1 MiB and 8 MiB?"
        idea = ("<ul><li><b>P1:</b> old read keeps its rate from 1 MiB to 8 MiB, inside a margin of %s GB/s.</li>"
                "<li><b>P2:</b> the new loop loses rate from 1 MiB to 8 MiB.</li>"
                "<li>If both hold, the small gain comes from the new loop %s.</li></ul>" % (fnum(margin, 2), self.R("decisions")))
        test = ("<ul><li><b>Step S2</b> %s. The runner <code>bwx8</code> (the test program of this investigation) runs one "
                "loop at one size on one CPU per process.</li>"
                "<li>A process has %d trials. A trial is %d windows of preparation with the same loop, then %d timed windows "
                "of %s s. The fourth timed window gives the rate.</li>"
                "<li>%d processes per loop, size and cell.</li>"
                "<li>Code: sections <a href='#code-chain'>5.2</a> (call chain) and <a href='#code-runner'>5.5</a> (runner).</li></ul>" % (
                    self.sref("S2"), len(trials), 4, nwin, fnum(win_ms / 1000.0, 1), v["units"]))
        if pfx_ms != 1200 or len(trials) != 4 or win_ms != 300:
            die("the S2 plan is not 4 trials with a 1200 ms prefix and 300 ms windows: the prose of the page would be wrong")
        worst = max(v["pc"][c, s]["P1"]["largest_abs_plus_limit"] for c, s in CELLS)
        if worst > margin:
            die("P1: a cell is outside the margin; the prose of step 1 would be wrong")
        so = ("<ul><li>The effect is real, and the new loop is the one that changes.</li>"
              "<li>The median change of old read from 1 MiB to 8 MiB is at most %s GB/s per cell. With its run-to-run spread "
              "included, the largest change is %s GB/s. That is inside the margin of %s GB/s.</li>"
              "<li>The new loop loses %s GB/s.</li>"
              "<li>The gain at 8 MiB is %s %% here, not %s %%. Step 5 explains that difference.</li></ul>" % (
                  fnum(max(abs(v["pc"][c, s]["P1"]["median"]) for c, s in CELLS), 2), fnum(worst, 2), fnum(margin, 2),
                  rng([-v["pc"][c, s]["P2"]["read"]["median"] for c, s in CELLS]), rng(v["g8"]), fnum(v["og"]["8M"][2], 2)))
        if r1["P1"]["overall"] not in cl["overall"]:
            die("the P1 verdict of round1 and of the claim differ")
        return self.qa("step1", "Step 1. Is it real, and which loop changes? (step S2)", q, idea, test, res, so)

    # ---------------------------------------------------------------- step 2: two ideas that were not confirmed
    def step2(self):
        J = self.J
        pf, ev = J["prefetch"], J["evict"]
        head = lambda s: s.split(" (")[0]
        rej = [(k, c) for k, c in pf["rule3"].items() if c.get("rise")]
        if len(rej) != 1:
            die("H1b: expected one cell with a prefetch kernel that halves the misses, found %d" % len(rej))
        rise = list(rej[0][1]["rise"].values())[0]
        if rise >= 0:
            die("H1b: the prefetch loop is not slower; the prose of step 2 would be wrong")
        wb = [x for s in ("s1", "s2") for x in ev["rule1"][s]["wb_evict"].values()]
        if fnum(min(wb), 2) != fnum(max(wb), 2):
            die("H1d: the write-backs per line differ at 2 decimals; the prose of step 2 would be wrong")
        fact(self.dec, "written before any round 3 rate was read")
        fact(self.dec, "written before `YF` was read and before any round 4 data")
        h = ("<section class='step' id='step2'><h3>Step 2. What limits the new loop at 8 MiB? Two ideas that were tested "
             "and not confirmed</h3>"
             "<p>Each idea had a rule in the decisions file before its data %s %s.</p>"
             "<ul class='dead'>" % (self.R("decisions"), self.R("final8")))
        h += ("<li><b>H1b: the count of L1 misses is the limit.</b><ul>"
              "<li>Test: load-only loops with software prefetch, an instruction that asks for a line ahead of its load "
              "(steps YC and YF).</li>"
              "<li>As recorded: &quot;%s&quot;.</li>"
              "<li>In the one cell where a prefetch loop halved the misses, that loop was %s GB/s slower than "
              "<code>asmread</code>, not faster. The other cells gave &quot;Insufficient data&quot;.</li></ul></li>" % (
                  esc(head(pf["overall"])), fnum(-rise, 2)))
        h += ("<li><b>H1d: dirty lines cost extra.</b> At 8 MiB each line that enters L2 pushes one line back to the SLC (a "
              "write-back). The idea: a clean line would need no data in its write-back.<ul>"
              "<li>Test: an evict step that should make the buffer lines clean before the trial (steps ZC and ZD).</li>"
              "<li>As recorded: &quot;%s&quot;.</li>"
              "<li>The write-backs stayed at %s per line. So the test did not change what it should change, and H1d is "
              "not decided.</li></ul></li>" % (esc(head(ev["overall"])), fnum(med(wb), 2)))
        h += "</ul></section>"
        return h

    # ---------------------------------------------------------------- step 3: ZS
    def fig_zs(self):
        v, rep = self.v, self.rep
        base, lo, hi, tol = v["band"]
        svgs = []
        for cpu in RF.CPUS:
            p = RF.Plot((-0.05, 1.03), (2.0, 2.9), W=400, H=300, ml=44, mr=12, mt=40, mb=44)
            p.frame()
            p.title("CPU %d" % cpu, "cycles per 64-byte line (axis starts at 2.0)")
            p.yticks([2.0, 2.2, 2.4, 2.6, 2.8], "%.1f")
            p.xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], title="r = L2 refills per 64-byte line")
            p.area([(p.X(0), p.Y(base - tol)), (p.X(1), p.Y(base + lo - tol)), (p.X(1), p.Y(base + hi + tol)),
                    (p.X(0), p.Y(base + tol))], C_BAND, 1.0)
            old = med([r["cyc"] for r in v["o8"] if r["cpu"] == cpu])
            p.path([(p.fx0, p.Y(old)), (p.fx1, p.Y(old))], C_OLD, 1.5, dash="5 3")
            p.raw_text(p.fx0 + 6, p.Y(old) - 5, "old read at 8 MiB: %.2f" % old, fs=11, cls="lab", obstacle=True)
            labelled = set()
            for ses in RF.SESSIONS:
                rule = v["zsrule"][cpu, ses]["sizes"]
                for r in rep.zs("asmread", cpu, ses):
                    q = rule[r["size"]]
                    x, y = p.X(r["r"]), p.Y(r["cyc"])
                    p.dot(x, y, C_NEW, RF.SHAPE[ses], hollow=not q["counted"], r=4,
                          tip="%s, session %d: r %.3f, %.3f cycles per line, band %.3f to %.3f, %s%s" % (
                              size_name(r["size"]), ses, r["r"], r["cyc"], q["band_low"], q["band_high"],
                              "inside" if q["inside"] else "outside", "" if q["counted"] else " (not counted)"))
            for ses in RF.SESSIONS:
                rule = v["zsrule"][cpu, ses]["sizes"]
                for r in rep.zs("asmread", cpu, ses):
                    q = rule[r["size"]]
                    t = None
                    if not q["inside"]:
                        t = "%s: outside" % size_name(r["size"])
                    elif r["size"] in ("1M", "8M", "32M"):
                        t = size_name(r["size"])
                    if t and r["size"] not in labelled:
                        labelled.add(r["size"])
                        p.label(p.X(r["r"]), p.Y(r["cyc"]), t, order="BR R B AL A L AR BL", cls="lab b" if not q["inside"] else "lab")
            svgs.append(self.svg([p], "Cycles per line of asmread against r on CPU %d, with the band of the rule, step ZS" % cpu))
        leg = [(RF.sw(C_NEW, "o"), "asmread, session 1"), (RF.sw(C_NEW, "d"), "asmread, session 2"),
               (RF.sw(C_NEW, "o", True), "hollow: 1 and 8 MiB, drawn and not counted"),
               (self.rect_sw(C_BAND), "band of the rule, fixed before the data"),
               (self.line_sw(C_OLD, "5 3"), "old read at 8 MiB")]
        n_in = sum(c["evaluated"] - c["outside"] for c in v["zsrule"].values())
        n_all = sum(c["evaluated"] for c in v["zsrule"].values())
        gap8 = [o["cyc"] - a["cyc"] for o, a in zip(v["o8"], v["a8"])]
        if min(gap8) <= 0:
            die("step ZS: the new loop is not below old read at 8 MiB in every cell; the takeaway of the figure would be wrong")
        before, cross = v["cross"]
        rr = lambda b: med([r["r"] for r in rep.rows("ZS.rows", kernel="asmread", size_bytes=b)])
        fact(self.dec, "At 8 MiB there are 0.82 L2 refills and 2.52 (high level) to 2.67 (low level) cycles")
        return self.fig("The cost of the new loop against r, at %d sizes from %g to %g MiB (step ZS)" % (
            len(v["zs_sizes"]), v["zs_sizes"][0] / MIB, v["zs_sizes"][-1] / MIB), leg, RF.panels(svgs),
                        "The points follow the band from r = 0 up to r near 1. %d of the %d counted points lie inside it. "
                        "At r = %.2f (8 MiB) the cost is %s cycles per line. That is %s cycles below old read. The cost passes "
                        "old read between r = %.2f and r = %.2f (%g and %g MiB)." % (
                            n_in, n_all, med([r["r"] for r in v["a8"]]), rng([r["cyc"] for r in v["a8"]], 2), rng(gap8, 2),
                            rr(before), rr(cross), before / MIB, cross / MIB),
                        "<p class='note'>The band is wide at large r because its two edges came from the two rate levels at "
                        "8 MiB (step 5) %s.</p>" % self.R("decisions"))

    def step3(self):
        v, J = self.v, self.J
        base, lo, hi, tol = v["band"]
        f8 = Src.get(os.path.join(HERE, "final8.py"))
        need(f8, f8.py_def("rule_zs_cell"), 'res["outside"] > 2')
        fact(self.dec, "rule written before any `ZS` data")
        fact(self.dec, "each line that must come from the SLC costs a fixed number of extra cycles")
        plan = Src.get(os.path.join(X11, "sched11", "s1", "ZS", "0000.plan"))
        t = [ln.split() for ln in plan.L if ln and not ln.startswith("#")]
        if len(t) != 1:
            die("the ZS plan does not hold exactly 1 trial")
        nwin, win_ms = int(t[0][7]), int(t[0][8])
        if win_ms != 300:
            die("the ZS plan does not have 300 ms windows: the prose of the page would be wrong")
        rows = []
        for c, s in CELLS:
            z = v["zsrule"][c, s]
            outs = ["%s: %s cycles, band %s to %s" % (size_name(k), fnum(q["cyc"], 2), fnum(q["band_low"], 2), fnum(q["band_high"], 2))
                    for k, q in z["sizes"].items() if q["counted"] and not q["inside"]]
            rows.append([RF.TH("CPU %d, s%d" % (c, s)), RF.TX("%s + %s x r" % (fnum(z["intercept"], 2), fnum(z["slope"], 2)), "num"),
                         RF.TX("%d of %d" % (z["evaluated"] - z["outside"], z["evaluated"]), "num"), RF.TX(". ".join(outs) or "none")])
        res = self.fig_zs()
        res += self.tab(["Cell", "fitted line, cycles per line", "counted sizes inside the band", "the size outside"],
                        rows, "The rule of step ZS per cell (loop <code>asmread</code>).",
                        note="The fitted line is a description. The rule uses only the band.")
        res += ("<p class='verdict'><b>Verdict as recorded:</b> &quot;%s&quot; %s. &quot;Simple form&quot; means: one fixed "
                "extra cost per line from the SLC.</p>" % (esc(J["ZS"]["overall"]), self.R("final8")))
        sizes = v["zs_sizes"]
        q = "Does the cost of the new loop follow the share of lines that come from the SLC?"
        idea = ("<ul><li><b>Hypothesis H1c:</b> each line that comes from the SLC costs the new loop a fixed number of extra "
                "cycles.</li>"
                "<li><b>Prediction</b> for <code>asmread</code> at every size: the cycles per line lie between "
                "%s + %s x r - %s and %s + %s x r + %s.</li>"
                "<li><b>Rule:</b> H1c is contradicted if more than 2 of the %d counted sizes lie outside this band on both "
                "CPUs in both sessions.</li>"
                "<li>The band came from earlier numbers at 1 MiB and 8 MiB. So these two sizes are drawn and not counted "
                "%s.</li></ul>" % (fnum(base, 2), fnum(lo, 2), fnum(tol, 2), fnum(base, 2), fnum(hi, 2), fnum(tol, 2),
                                   v["zsrule"][2, 1]["evaluated"], self.R("decisions")))
        test = ("<ul><li><b>Step ZS</b>, runner <code>bwx11</code> %s. The buffer size is varied to vary r.</li>"
                "<li>Loops <code>asmread</code> and <code>oldread</code> at %d sizes from %g to %g MiB.</li>"
                "<li>One process per loop, size and CPU: %d windows of %s s.</li>"
                "<li>The counters for cycles and L2 refills are read at every window boundary.</li>"
                "<li>Code: sections <a href='#code-chain'>5.2</a>, <a href='#code-runner'>5.5</a> and "
                "<a href='#code-ana'>5.8</a> (the rule).</li></ul>" % (
                    self.sref("ZS"), len(sizes), sizes[0] / MIB, sizes[-1] / MIB, nwin, fnum(win_ms / 1000.0, 1)))
        so = ("<ul><li>The cost of the new loop rises with r as predicted, in 4 of 4 cells.</li>"
              "<li>A line from the SLC costs about %s cycles more than a line from L2 (slopes of the 4 fitted lines).</li>"
              "<li>The recorded wording is &quot;not contradicted&quot;. The rule can reject H1c, and it did not.</li></ul>"
              % rng([f[1] for f in v["fit"].values()], 2))
        return self.qa("step3", "Step 3. The idea that held: the cost follows r (step ZS)", q, idea, test, res, so)

    # ---------------------------------------------------------------- step 4: ZN
    def zn_data(self):
        """per loop: (step, [C per cell], [8 MiB median per cell]) for the two slowed loops and for asmread"""
        v, rep = self.v, self.rep
        out = []
        for k in ("read_nop128", "read_nop96"):
            ks = [v["zn"][c, s]["kernels"][k] for c, s in CELLS]
            for q in ks:
                if abs((q["C"] - q["median_8M"]) - q["loss_32K_to_8M"]) > 1e-9:
                    die("step ZN: the recorded loss of %s is not C minus the 8 MiB median" % k)
            out.append((k, "ZN", [q["C"] for q in ks], [q["median_8M"] for q in ks]))
        a32 = [rep.one("prefetch.YF", kernel="asmread", size="32K", cpu=c, session=s) for c, s in CELLS]
        a8 = [rep.one("prefetch.YF", kernel="asmread", size="8M", cpu=c, session=s) for c, s in CELLS]
        if None in a32 or None in a8:
            die("step YF: an asmread cell is missing")
        out.append(("asmread", "YF", [q["median"] for q in a32], [q["median"] for q in a8]))
        return out

    @staticmethod
    def srng(xs, nd=2):
        """'a to b' with an explicit sign on both ends"""
        a, b = "%+.*f" % (nd, min(xs)), "%+.*f" % (nd, max(xs))
        return a if a == b else "%s to %s" % (a, b)

    def fig_slow(self, data):
        rh = 52
        p = RF.Plot((30, 140), (0, 1), W=400, H=40 + rh * len(data) + 44, ml=88, mr=12, mt=40, mb=44)
        p.frame()
        p.title("Rate at 32 KiB and at 8 MiB", "rate, GB/s (axis starts at 30)")
        p.xticks([40, 60, 80, 100, 120, 140], grid=True)
        for i, (k, step, c32, c8) in enumerate(data):
            y = p.fy0 + rh * i + 24
            p.raw_text(p.fx0 - 6, y + 4, k, "end", 11, "ax", False)
            x32, x8 = p.X(med(c32)), p.X(med(c8))
            p.path([(x32, y), (x8, y)], C_PRED, 2, layer="marks")
            for (c, s), a, b in zip(CELLS, c32, c8):
                p.dot(p.X(a), y, C_NEW, hollow=True, r=6, tip="%s at 32 KiB, CPU %d, session %d: %.2f GB/s" % (k, c, s, a))
            for (c, s), a, b in zip(CELLS, c32, c8):
                p.dot(p.X(b), y, C_NEW, r=3.2, tip="%s at 8 MiB, CPU %d, session %d: %.2f GB/s (median)" % (k, c, s, b))
            ch = [b - a for a, b in zip(c32, c8)]
            moved = abs(med(ch)) > 5
            if moved:
                p.raw_text((x32 + x8) / 2, y - 12, "change %s GB/s" % self.srng(ch, 1), "middle", 11, "lab b", False)
                p.raw_text(x8, y + 19, "%s at 8 MiB" % rng(c8, 1), "middle", 11, "lab", False)
                p.raw_text(p.fx1 - 4, y + 19, "%s at 32 KiB" % fnum(med(c32), 1), "end", 11, "lab", False)
            else:
                p.raw_text(x32 - 8, y - 12, "change %s GB/s" % self.srng(ch, 2), "start", 11, "lab b", False)
                p.raw_text(x32 - 8, y + 19, "%s at 32 KiB, %s at 8 MiB" % (fnum(med(c32), 2), rng(c8, 2)), "start", 11, "lab", False)
        leg = [(RF.sw(C_NEW, "o", True), "rate at 32 KiB (core rate C), one ring per cell"),
               (RF.sw(C_NEW), "median rate at 8 MiB, one dot per cell")]
        slow = [b - a for k, _, c32, c8 in data if k != "asmread" for a, b in zip(c32, c8)]
        fast = [a - b for k, _, c32, c8 in data if k == "asmread" for a, b in zip(c32, c8)]
        return self.fig("Slowed load-only loops (step ZN) and the unslowed loop (step YF), at 32 KiB and at 8 MiB", leg,
                        "<div class='panels'><div class='panel'>%s</div></div>" % self.svg(
                            [p], "Rate at 32 KiB and at 8 MiB of read_nop128, read_nop96 and asmread"),
                        "Only the unslowed loop moves. The two slowed loops change by %s GB/s. <code>asmread</code> loses "
                        "%s GB/s." % (self.srng(slow, 2), rng(fast, 0)),
                        "<p class='note'>A ring and its dots lie on top of each other for the slowed loops. That is the result.</p>")

    def fig_zn(self):
        v = self.v
        sup = v["sup"]
        order = ["oldread", "read_nop96", "read_nop128"]
        if sorted({r["kernel"] for r in sup["rows"]}) != sorted(order):
            die("supplementary gain: other kernels than old read, read_nop96, read_nop128")
        lo = {k: min(min(r["predicted_low_pct"], r["measured_pct"]) for r in sup["rows"] if r["kernel"] == k) for k in order}
        hi = {k: max(max(r["predicted_high_pct"], r["measured_pct"]) for r in sup["rows"] if r["kernel"] == k) for k in order}
        span = max(int(hi[k]) + 1 - int(lo[k] // 1) for k in order) + 2
        span += span % 2
        svgs = []
        for k in order:
            rows = sorted([r for r in sup["rows"] if r["kernel"] == k], key=lambda r: (r["cpu"], r["session"]))
            x0 = int(lo[k] // 1) - 1
            p = RF.Plot((x0, x0 + span), (0, 1), W=340, H=40 + 28 * 4 + 44, ml=70, mr=50, mt=40, mb=44)
            p.frame()
            p.title("%s (step %s)" % ("old read" if k == "oldread" else k, rows[0]["step"]),
                    "rate at 32 KiB (C): %s GB/s" % rng([r["C"] for r in rows], 1))
            p.xticks(list(range(x0, x0 + span + 1, 2)), title="gain of asmread over this loop at 8 MiB, %", grid=True)
            p.raw_text(p.fx1 + 5, p.fy0 - 7, "meas.", "start", 11, "ax", False)
            for i, r in enumerate(rows):
                y = p.fy0 + 28 * (i + 0.5)
                p.raw_text(p.fx0 - 6, y + 4, "CPU %d, s%d" % (r["cpu"], r["session"]), "end", 11, "ax", False)
                p.bar(p.X(r["predicted_low_pct"]), y, p.X(r["predicted_high_pct"]), RF.C_AXIS, thick=12,
                      tip="predicted %.2f to %.2f %%" % (r["predicted_low_pct"], r["predicted_high_pct"]))
                p.dot(p.X(r["measured_pct"]), y, C_NEW, r=4.5, tip="measured %.2f %% (%s)" % (
                    r["measured_pct"], "inside" if r["inside"] else "outside"))
                p.raw_text(p.fx1 + 5, y + 4, "%.2f" % r["measured_pct"], "start", 11, "lab b", False)
            svgs.append(self.svg([p], "Predicted range and measured gain of asmread over %s at 8 MiB" % k))
        leg = [(self.rect_sw(RF.C_AXIS), "predicted range, from two rates"), (RF.sw(C_NEW), "measured gain")]
        # the reading of the two ends of the range, as final8.json records it
        s8 = [x for x in self.J["readings"] if "S8 is the range from the cell p5 to the cell p95 of asmread at 8 MiB" in x]
        if len(s8) != 1:
            die("final8.json does not record the reading of the range S8")
        for r in sup["rows"]:
            y = self.rep.one("prefetch.YF", kernel="asmread", size="8M", cpu=r["cpu"], session=r["session"])
            if abs(y["p5"] - r["asmread_low"]) > 1e-9 or abs(y["p95"] - r["asmread_high"]) > 1e-9:
                die("supplementary gain: the two asmread rates are not the 5th and 95th percentile of step YF")
        lowrow = min((r for r in sup["rows"] if r["kernel"] == "oldread"), key=lambda r: r["measured_pct"])
        return self.fig("Supplementary evaluation (defined after the data was seen): the gain of asmread at 8 MiB, "
                        "predicted from two rates", leg, "<div class='panels p3'>%s</div>" % "".join(
                            "<div class='panel'>%s</div>" % s for s in svgs),
                        "The measured gain lies inside the predicted range in %d of %d cells. The slower the other loop, "
                        "the larger the gain: about 1 to 7 %% over old read, 23 to 30 %% over read_nop96, 58 to 66 %% over "
                        "read_nop128.".replace("1 to 7", self._r0("oldread")).replace("23 to 30", self._r0("read_nop96")).replace(
                            "58 to 66", self._r0("read_nop128")) % (sup["cells_inside"], sup["cells"]),
                        "<ul class='note'><li>All three panels have the same scale: %d percentage points wide.</li>"
                        "<li>Predicted range = low rate of asmread / C - 1 to high rate of asmread / C - 1. C is the rate of "
                        "the other loop at 32 KiB.</li>"
                        "<li>The low and the high rate of asmread are the 5th and the 95th percentile of its window rates at "
                        "8 MiB in step YF, per cell. They are not the level medians of step 5.</li>"
                        "<li>Measured = asmread median at 8 MiB / median of the other loop at 8 MiB - 1. The asmread rates "
                        "come from step YF of the same session %s.</li>"
                        "<li>On CPU %d in session %d the median asmread rate of step YF was %s GB/s, near the low level. So "
                        "the gain over old read is %s %% there.</li></ul>" % (
                            span, self.sref("YF"), lowrow["cpu"], lowrow["session"], fnum(lowrow["asmread_median"], 2),
                            fnum(lowrow["measured_pct"], 2)))

    def _r0(self, kernel):
        return rng([r["measured_pct"] for r in self.v["sup"]["rows"] if r["kernel"] == kernel], 0)

    def step4(self):
        v, J, rep = self.v, self.J, self.rep
        Z = J["families"]["ZN"]
        f8 = Src.get(os.path.join(HERE, "final8.py"))
        r = f8.py_def("rule_zn_kernel")
        need(f8, r, "C <= 66.0")
        need(f8, r, "abs(median8 - C) <= 1.0")
        need(f8, r, "(C - median8) > 1.0")
        if {Z["asmread_source"][s]["step"] for s in ("s1", "s2")} != {"YF"}:
            die("step ZN: the asmread rate does not come from step YF")
        l11 = Src.get(os.path.join(X11, "crb-build-1", "listing.txt"))
        nops = {}
        for k in ("read_nop96", "read_nop128"):
            a = l11.find("<k_%s>:" % k)
            b = l11.find("\tret", a)
            nops[k] = sum(1 for ln in l11.L[a:b] if ln.rstrip().endswith("\tnop"))
        if nops != {"read_nop96": 96, "read_nop128": 128}:
            die("the listing does not hold 96 and 128 nop instructions: %r" % nops)
        data = self.zn_data()
        rows = []
        for k, step, c32, c8 in data:
            rows.append([RF.TH("%s (step %s)" % (k, step)), RF.TX(rng(c32), "num"), RF.TX(rng(c8), "num"),
                         RF.TX(self.srng([b - a for a, b in zip(c32, c8)], 2 if k != "asmread" else 1), "num"),
                         RF.TX(Z["overall"][k] if k in Z["overall"] else "for comparison: the rule is for slowed loops", "txt wide")])
        a1 = [rep.one("prefetch.YF", kernel="asmread", size="1M", cpu=c, session=s) for c, s in CELLS]
        if None in a1:
            die("step YF: an asmread cell at 1 MiB is missing")
        res = self.fig_slow(data)
        res += self.tab(["Loop", "rate at 32 KiB (core rate C), GB/s", "median rate at 8 MiB, GB/s",
                         "change, GB/s", "verdict as recorded"],
                        rows, "The numbers behind the figure. Each range covers the 4 cells.", cls="wrap",
                        note="<code>asmread</code> reaches %s GB/s only while the data is in L1 (32 KiB). At 1 MiB the data "
                             "comes from L2, and it runs at %s GB/s. That is the rate of Figure 2." % (
                                 fnum(med(data[2][2]), 0), fnum(med([q["median"] for q in a1]), 0)))
        res += ("<details class='sup'><summary>Supplementary evaluation (defined after the data was seen): the gain predicted "
                "from two rates, inside the range in %d of %d cells</summary>%s</details>" % (
                    v["sup"]["cells_inside"], v["sup"]["cells"], self.fig_zn()))
        # two loops that do not fit the simple picture
        n64 = [(v["zn"][c, s], v["zn"][c, s]["kernels"]["read_nop64"]) for c, s in CELLS]
        above = [q["p95_8M"] for z, q in n64 if q["p95_8M"] > z["S8_high"]]
        xn = rep.claim("H1 two limits (rule 6 of round 2, XN)")
        m16 = re.search(r"read_nop16: ([^;]+)", xn["overall"])
        if not m16 or "contradicted" not in m16.group(1) or "not contradicted" in m16.group(1):
            die("step XN: the recorded verdict for read_nop16 is not 'contradicted'; the prose of step 4 would be wrong")
        res_md = os.path.join(N_DIR, "tackle-8mb-results.md")
        fact(res_md, "So the supply rate at 8 MiB is not one number for all loops.")
        fact(res_md, "`read_nop16` never reaches the high level at 8 MiB")
        if len(above) != 3:
            die("step ZN: read_nop64 is above the high rate of asmread in %d cells, not 3" % len(above))
        res += ("<p><b>Two loops that do not fit H1 in this simple form</b> (not used as proof):</p><ul>"
                "<li><code>read_nop64</code> (step ZN) has a core rate of %s GB/s. That is above the 66 GB/s threshold, so "
                "the rule does not apply to it (as recorded: &quot;%s&quot;). At 8 MiB its fastest windows (95th percentile) "
                "reached %s GB/s in %d of 4 cells. That is faster than the high rate of <code>asmread</code> (%s GB/s).</li>"
                "<li><code>read_nop16</code> (step XN, an earlier step with 16 nops) never reaches the high level at 8 MiB. "
                "As recorded: &quot;read_nop16: %s&quot;.</li>"
                "<li>So the rate at which lines arrive at 8 MiB is not one number for all loops. This is not explained "
                "(Insufficient data) %s %s.</li></ul>" % (
                    rng([q["C"] for _, q in n64], 1), esc(Z["overall"]["read_nop64"]), rng(above, 1), len(above),
                    rng([z["S8_high"] for z, _ in n64], 1), esc(m16.group(1)), self.R("final8"), self.R("results")))
        sup = v["sup"]
        # old read at 32 KiB, 1 MiB and 8 MiB: the cell medians of step S2 that the supplementary evaluations use
        ow = {(r["size"], r["cpu"], r["session"]): r["oldread"] for r in J["supplementary"]["old_without_adds"]["rows"]}
        old32, old1, old8 = ([ow[size, c, s] for c, s in CELLS] for size in ("32K", "1M", "8M"))
        for r in sup["rows"]:
            if r["kernel"] == "oldread" and (r["step"] != "S2" or abs(r["C"] - ow["32K", r["cpu"], r["session"]]) > 1e-9
                                             or abs(r["median_8M"] - ow["8M", r["cpu"], r["session"]]) > 1e-9):
                die("supplementary gain: the old read rates do not come from step S2")
        if min(old32) <= 66.0:
            die("old read: a 32 KiB rate is at or below 66 GB/s; the prose of step 4 would be wrong")
        fact(self.dec, "the load-only loop is limited by the rate at which lines can be moved into the first-level cache")
        pre = ("<p class='bridge'><b>From step 3 to step 4.</b> Step 3 measured the extra cost on a fast loop. Hypothesis H1 "
               "(&quot;two limits&quot;) reads it this way: a loop runs at the smaller of two rates. One is its own core rate. "
               "The other is the rate at which lines arrive. H1c of step 3 names what lowers the second rate at 8 MiB: the "
               "lines come from the SLC. If H1 is right, a loop that is slow for another reason loses nothing at 8 MiB "
               "%s.</p>" % self.R("decisions"))
        q = "Does a load-only loop that is slowed inside the core keep its rate at 8 MiB?"
        idea = ("<ul><li><b>Hypothesis H1 (two limits):</b> a loop runs at the smaller of two rates: its own core rate C "
                "(its rate at 32 KiB, where all data is in L1), and the rate at which lines arrive.</li>"
                "<li><b>Prediction:</b> a loop with C at most 66 GB/s keeps C at 8 MiB, within 1.0 GB/s.</li>"
                "<li><b>Rule:</b> H1 is contradicted if such a loop loses more than 1.0 GB/s from 32 KiB to 8 MiB on both "
                "CPUs in both sessions %s.</li></ul>" % self.R("decisions"))
        test = ("<ul><li><b>Step ZN</b>, runner <code>bwx11</code> %s.</li>"
                "<li>Loops <code>read_nop96</code> and <code>read_nop128</code>: the <code>asmread</code> loop with 96 or 128 "
                "nop instructions per 256 bytes. A nop (no-operation instruction) costs time in the core and touches no data.</li>"
                "<li>Sizes %s. %d processes per loop, size and cell.</li>"
                "<li>The <code>asmread</code> rate of the same session comes from step YF (runner <code>bwx10</code>) %s.</li>"
                "<li>Code: sections <a href='#code-chain'>5.2</a>, <a href='#code-runner'>5.5</a> and "
                "<a href='#code-kern'>5.6</a>.</li></ul>" % (
                    self.sref("ZN"), ", ".join(size_name(x) for x in sorted({r["size"] for r in Z["rows"]}, key=lambda x: (
                        x[-1] == "M", float(x[:-1])))),
                    rep.one("families.ZN.rows", kernel="read_nop96", size="8M", cpu=2, session=1)["n"], self.sref("YF")))
        so = ("<ul><li>The slowed loops lose nothing at 8 MiB. This fits H1. As recorded, H1 is not contradicted by "
              "<code>read_nop96</code> and <code>read_nop128</code>.</li>"
              "<li>H1 does not hold for every loop. It is contradicted for <code>read_nop16</code> in step XN.</li>"
              "<li>Old read behaves like the slowed loops. It runs at %s GB/s at 32 KiB and at %s GB/s at 8 MiB (step S2). "
              "At 1 MiB it is %s GB/s faster than at 32 KiB.</li>"
              "<li>The recorded rule does not cover old read: its 32 KiB rate is %s GB/s above the 66 GB/s threshold. So "
              "this comparison is supplementary.</li>"
              "<li>At 8 MiB <code>asmread</code> runs at %s GB/s. That is just above old read, so the gain is small.</li></ul>" % (
                  rng(old32, 1), rng(old8, 2), rng([a - b for a, b in zip(old1, old32)], 1),
                  rng([x - 66.0 for x in old32], 1),
                  "%s to %s" % (fnum(min(r["asmread_low"] for r in sup["rows"]), 1), fnum(max(r["asmread_high"] for r in sup["rows"]), 1))))
        return self.qa("step4", "Step 4. A controlled test: change the core rate of the loop (step ZN)", q, idea, test, res, so, pre=pre)

    # ---------------------------------------------------------------- step 5: H2
    def fig_h2(self):
        v, rep, J = self.v, self.rep, self.J
        lowmax, highmin, _ = v["h2rule"]
        # panel A: one 60 s trace of step S4
        ses, cpu = 1, 2
        folder = rep.folders("S4", ses)[0]
        procs = rep.read_s4(folder)
        if not procs:
            die("cannot read %s/S4.csv" % folder)
        pa = RF.Plot((0, 60), (66, 72.5), W=400, H=294, ml=40, mr=92, mt=40, mb=44)
        pa.frame()
        pa.title("What two levels look like: CPU %d, session %d" % (cpu, ses), "rate per 0.3 s window, GB/s (axis starts at 66)")
        pa.yticks([66, 67, 68, 69, 70, 71, 72], "%d")
        pa.xticks([0, 10, 20, 30, 40, 50, 60], title="time since the start of the process, s (step S4)")
        used = []
        for kernel, col in (("oldread", C_OLD), ("asmread", C_NEW)):
            tag = "%s-cpu%d-p1" % (kernel, cpu)
            pr = next((q for q in procs if q["tag"] == tag), None)
            if not pr or not pr["w"]:
                die("step S4: no process %s in %s" % (tag, folder))
            used.append(tag)
            pts = []
            for t0, t1, by in pr["w"]:
                y = pa.Y(min(max(by / float(t1 - t0), 66.0), 72.5))
                pts += [(pa.X(t0 / 1e9), y), (pa.X(min(t1 / 1e9, 60)), y)]
            pa.path(pts, col, 1.4)
            self.s4_dur = int(round(pr["w"][-1][1] / 1e9))
        lv, lo = v["lev"][cpu, ses], v["levold"][cpu, ses]
        side = [(pa.Y(lv["high"]) + 4, "high %.1f" % lv["high"]), (pa.Y(lv["low"]) + 4, "low %.1f" % lv["low"]),
                (pa.Y(med(lo["one_level_rates"])) + 4, "old read %.1f" % med(lo["one_level_rates"]))]
        for y, t in RF.spread_labels(side, pa.fy0 + 10, pa.fy1):
            pa.raw_text(pa.fx1 + 5, y, t, "start", 11, "lab b", False)
        # panel B: the repetitions of the original program
        data = {}
        for s in RF.SESSIONS:
            for f in rep.folders("H2", s):
                pr = rep.read_h2(f)
                if pr is None:
                    die("cannot read %s/H2.csv" % f)
                for q in pr:
                    data.setdefault((q["cpu"], s, q["binary"]), []).extend(q["rates"])
        o = v["orig"]
        first = sorted({c for _, c in o[("bw_new", "8M")]}, key=lambda c: (c != "2", int(c)))
        rowsl = [("first", c) for c in first] + [(c, s) for c in ("2", "41", "0") for s in RF.SESSIONS]
        for c in first:
            data["first", c, "bw_old"] = [r for r, cc in o[("bw_old", "8M")] if cc == c]
            data["first", c, "bw_new"] = [r for r, cc in o[("bw_new", "8M")] if cc == c]
        allv = [x for vs in data.values() for x in vs]
        x0, x1 = int(min(allv)) - 0.5, int(max(allv)) + 1.5
        rh = 30
        pb = RF.Plot((x0, x1), (0, 1), W=400, H=40 + rh * len(rowsl) + 44, ml=78, mr=92, mt=40, mb=44)
        pb.frame()
        pb.title("The original program at 8 MiB: every repetition")
        pb.xticks(list(range(int(x0 + 1), int(x1) + 1)), title="rate of one repetition of 0.5 s, GB/s (axis starts at %g)" % x0, grid=True)
        for thr, txt, anc in ((lowmax, "low", "end"), (highmin, "high", "start")):
            pb.path([(pb.X(thr), pb.fy0), (pb.X(thr), pb.fy1)], C_INK2, 1, dash="4 3")
            pb.raw_text(pb.X(thr) + (-3 if anc == "end" else 3), pb.fy0 - 5, txt, anc, 11, "ax", False)
        pb.under.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%d' fill='#f3f2ee'/>" % (
            pb.fx0 + 0.5, pb.fy0 + 0.5, pb.fx1 - pb.fx0 - 1, rh * len(first)))
        for i, (c, s) in enumerate(rowsl):
            y = pb.fy0 + rh * (i + 0.5)
            if c == "first":
                pb.raw_text(pb.fx0 - 6, y, "first run,", "end", 11, "ax", False)
                pb.raw_text(pb.fx0 - 6, y + 12, "CPU %s" % s, "end", 11, "ax", False)
            else:
                pb.raw_text(pb.fx0 - 6, y + 4, "CPU %s, s%d" % (c, s), "end", 11, "ax", False)
            for j, x in enumerate(data.get((c, s, "bw_old"), [])):
                pb.dot(pb.X(x), y - 7 + ((j * 7) % 5 - 2) * 1.1, C_OLD, r=2.4, opacity=0.8)
            for j, x in enumerate(data.get((c, s, "bw_new"), [])):
                pb.dot(pb.X(x), y + 6 + ((j * 3) % 7 - 3) * 1.1, C_NEW, r=2.4, opacity=0.8)
            if c != "first":
                pb.raw_text(pb.fx1 + 5, y + 4, "%.2f %%" % v["h2"][c, s]["median_gain_pct"], "start", 11, "lab b", False)
        yb = pb.fy0 + rh * len(first) / 2.0
        pb.raw_text(pb.fx1 + 5, yb + 4, "%.2f %% (best)" % v["og"]["8M"][2], "start", 11, "lab b", False)
        pb.raw_text(pb.fx1 + 5, pb.fy0 - 5, "gain", "start", 11, "ax", False)
        leg = [(RF.sw(C_OLD), "old read (binary bw_old)"), (RF.sw(C_NEW), "new loop (asmread on the left, binary bw_new on the right)")]
        body = RF.panels([self.svg([pa], "A 60 second trace of asmread and old read at 8 MiB on CPU 2, step S4"),
                          self.svg([pb], "Repetition rates of the original program at 8 MiB per CPU and session, step H2")])
        return self.fig("Two rate levels at 8 MiB (step S4), and the level of the original program (step H2)", leg, body,
                        "The new loop has two levels at 8 MiB. Old read has one. On CPU 2 the original program stays at the "
                        "low level, as in the first run, and the gain is near zero. On CPU 0 it was low in the first run and "
                        "high in step H2.",
                        "<ul class='note'><li>Left: one process per loop of the folder <code>%s</code> (%s). The labels at the "
                        "right edge are the medians of the cell.</li>"
                        "<li>Right: one dot per repetition, spread vertically inside a row. The two shaded rows are the first "
                        "measurement of %s %s. The other rows are step H2 of %s.</li>"
                        "<li>The dashed lines are the limits of the rule: low up to %g GB/s, high from %g GB/s.</li>"
                        "<li>The gain of the first run is the best new rate over the best old rate, over both CPUs. The "
                        "other gains are medians over the 12 pairs of neighbouring processes.</li></ul>" % (
                            esc(folder), esc(", ".join(used)), self.day(ORIG_FOLDER), self.R("orig"),
                            self.day(rep.folders("H2", 1)[0]), lowmax, highmin))

    @staticmethod
    def day(folder):
        """'2026-11-13' from a result folder name that ends with a time stamp like 20261113T181222Z"""
        m = re.search(r"(\d{4})(\d{2})(\d{2})T\d{6}Z$", folder)
        if not m:
            die("no time stamp in the folder name %s" % folder)
        return "%s-%s-%s" % m.groups()

    def step5(self):
        v, J, rep = self.v, self.J, self.rep
        lowmax, highmin, g0 = v["h2rule"]
        f8 = Src.get(os.path.join(HERE, "final8.py"))
        r = f8.py_def("h2_verdict")
        need(f8, r, '>= 0.75')
        need(f8, r, '<= 1.5')
        need(f8, r, '< 0.25')
        rh = Src.get(os.path.join(X8, "run_h2.sh"))
        need(rh, (1, len(rh.L)), "--reps 3 --min-ms 500")
        need(rh, (1, len(rh.L)), "PAIRS=12")
        rows = []
        for c in ("2", "41", "0"):
            for s in RF.SESSIONS:
                r = v["h2"][c, s]
                if r["low"] + r["high"] + r["between"] != r["new_repetitions"]:
                    die("step H2: low + high + between is not the count of repetitions")
                rows.append([RF.TH("CPU %s, s%d" % (c, s)), RF.TX("%d" % r["low"], "num"), RF.TX("%d" % r["between"], "num"),
                             RF.TX("%d" % r["high"], "num"), RF.V(r["median_gain_pct"]), RF.TX(J["H2"]["verdict"]["cpu" + c])])
        nrep = v["h2"]["2", 1]["new_repetitions"]
        res = self.fig_h2()
        res += self.tab(["CPU and session", "low (at most %g GB/s)" % lowmax, "between", "high (at least %g GB/s)" % highmin,
                         "median gain over the 12 pairs, %", "H2 for this CPU, as recorded"], rows,
                        "The original program at 8 MiB (step H2): where the %d new-read repetitions lie." % nrep)
        res += ("<p class='verdict'><b>Verdict as recorded:</b> &quot;%s&quot; %s. &quot;Rejected&quot; for CPU 0 means only: "
                "CPU 0 was not at the low level in step H2.</p>" % (esc(rep.claim("H2")["overall"]), self.R("final8")))
        o8 = v["orig_new8"]
        o = v["orig"][("bw_new", "8M")]
        ocpu = sorted({c for _, c in o}, key=int)
        if ocpu != ["0", "2"]:
            die("first measurement: the CPUs are %r, not 0 and 2" % ocpu)
        o0 = [r for r, c in o if c == "0"]
        h0 = [v["h2"]["0", s] for s in RF.SESSIONS]
        if max(o8) > lowmax or any(x["low"] for x in h0) or J["H2"]["verdict"]["cpu0"] != "rejected":
            die("first measurement or step H2 on CPU 0: the prose of step 5 would be wrong")
        d0, d1 = self.day(ORIG_FOLDER), self.day(rep.folders("H2", 1)[0])
        q = ("Step 1 found a gain of %s %% at 8 MiB. Why did the first measurement say %s %%?" % (rng(v["g8"]), fnum(g0, 2)))
        idea = ("<ul><li><b>Hypothesis H2:</b> at 8 MiB the new loop runs at one of two rate levels, and the first "
                "measurement was made at the low level.</li>"
                "<li><b>Rule:</b> a new-read repetition is &quot;low&quot; at or below %g GB/s and &quot;high&quot; at or above "
                "%g GB/s.</li>"
                "<li>H2 is supported on a CPU if at least 75 %% of the repetitions are low in both sessions, and the median "
                "gain of the pairs at the low level is within 1.5 percentage points of %s %%.</li>"
                "<li>H2 is rejected on a CPU if fewer than 25 %% are low in both sessions %s.</li></ul>" % (
                    lowmax, highmin, fnum(g0, 2), self.R("decisions")))
        test = ("<ul><li><b>Step S4</b> showed the two levels: %d s runs at 8 MiB with runner <code>bwx8</code> %s.</li>"
                "<li><b>Step H2</b> ran the original program again: binaries <code>bw_old</code> and <code>bw_new</code> of "
                "2026-11-13 with the original options %s.</li>"
                "<li>CPUs 2, 0 and 41. 12 processes per binary and CPU, in pairs. 3 repetitions of 0.5 s per process.</li>"
                "<li>Code: section <a href='#code-h2'>5.7</a>.</li></ul>" % (self.s4_dur, self.sref("S4"), self.sref("H2")))
        so = ("<ul><li>On CPU 2 step H2 reproduces the first measurement. The original program stays at the low level and "
              "gains %s %%.</li>"
              "<li>At the high level it gains %s %% (CPU 0 in step H2).</li>"
              "<li>The first run used CPUs 0 and 2. All %d of its new-read repetitions were low (%s GB/s).</li>"
              "<li>So on CPU 0 step H2 does not reproduce the first run. CPU 0 was at the low level on %s (%s GB/s) and at "
              "the high level on %s (%d of %d repetitions in each session).</li>"
              "<li>Why CPU 0 changed its level between the two days is Insufficient data. It is the same open point as "
              "the cause of the level switch (section 4).</li></ul>" % (
                  rng([v["h2"]["2", s]["median_gain_pct"] for s in RF.SESSIONS]),
                  rng([v["h2"]["0", s]["median_gain_pct"] for s in RF.SESSIONS]), len(o8), rng(o8),
                  d0, rng(o0), d1, min(x["high"] for x in h0), h0[0]["new_repetitions"]))
        return self.qa("step5", "Step 5. Why the first measurement said %s %% (steps S4 and H2)" % fnum(g0, 2), q, idea, test, res, so,
                       after=self.level_ideas())

    def level_ideas(self):
        """the two ideas about the cause of the level switch, each with its recorded verdict"""
        J, rep = self.J, self.rep
        yp = J["YP"]["verdict"]
        head = lambda s: s.split(" (")[0]
        sw = J["switch_timing"]["XW_sampler"]
        if any(sw[s]["any_key_accompanies"] for s in ("s1", "s2")):
            die("H3a: the sampler record does not fit the prose of the page")
        h7 = rep.claim("H7")
        if "replaced statistic" not in h7["rule"]:
            die("H7: the claim does not name the replaced statistic")
        res_md = os.path.join(N_DIR, "tackle-8mb-results.md")
        fact(res_md, "I replaced it by the series of all switch windows and recorded this before session 2.")
        fact(self.dec, "The statistic that I fixed for rule 2 (\"first fall after window 30\") is not usable")
        h = ("<h4>What switches the level? Two ideas, neither confirmed</h4><ul class='dead'>"
             "<li><b>H3a: a timer of the operating system on the worker's CPU triggers the switch.</b><ul>"
             "<li>Test: a program that samples the host activity beside the runner (step XW).</li>"
             "<li>As recorded: &quot;%s&quot;. No sampled host activity accompanied the level switches.</li></ul></li>" % esc(
                 rep.claim("H3a")["overall"]))
        h += ("<li><b>H7: the address of the record that the runner writes after each window switches the level.</b><ul>"
              "<li>Test: move that record by extra bytes (steps YL and YP).</li>"
              "<li>As recorded for step YP: session 1 &quot;%s&quot;, session 2 &quot;%s&quot;, overall &quot;%s&quot;.</li>"
              "<li>The statistic of the YP rule was replaced after the session 1 data was read. The decisions file records "
              "this before session 2.</li>"
              "<li>So H7 stays a hypothesis %s %s %s.</li></ul></li></ul>" % (
                  esc(head(yp["s1"])), esc(head(yp["s2"])), esc(head(J["YP"]["overall"])),
                  self.R("final8"), self.R("decisions"), self.R("results")))
        return h

    def sec_path(self):
        h = "<h2 id='path'>3. How we got there</h2>"
        h += ("<p>The path had five steps. Each step asked one question. Each test had its rule in the decisions file "
              "before its data %s. Words that the steps use:</p><ul>"
              "<li>A <b>step</b> with a short name (S2, ZS, ...) is one batch of test processes.</li>"
              "<li>Each proving step ran in two <b>sessions</b> (s1, s2), at least 3 hours apart, on CPUs 2 and 41. "
              "Step H2 also used CPU 0.</li>"
              "<li><b>As recorded</b> marks a verdict text that the analysis wrote by its rule.</li></ul>" % self.R("decisions"))
        fact(self.dec, "two sessions at least 3 hours apart")
        self.n_diag = 1
        h += ("<figure class='diagram'><div class='figtitle'>Diagram 1. The thinking, from the observation to the answer</div>%s"
              "</figure>" % self.dual(self.flow_svg(False), self.flow_svg(True)))
        return h + self.step1() + self.step2() + self.step3() + self.step4() + self.step5()

    # ================================================================== section 4
    def sec_conclusion(self):
        v, J = self.v, self.J
        res = os.path.join(N_DIR, "tackle-8mb-results.md")
        fact(res, "mesh counters of the SLC (root)")
        fact(res, "physical page addresses and mesh counters (root)")
        fact(res, "Why old read needs 2.67 cycles per line")
        fact(res, "No rule fixed it before the data")
        fact(res, "a load near 1.00 is the test itself, est.")
        fact(os.path.join(N_DIR, "tackle-8mb.md"), "Do not call the 8 MiB problem solved merely because a threshold can label "
                                                    "the data or one hypothesis is not rejected.")
        sup = v["sup"]
        zn_ok = all(v["zn"][c, s]["kernels"][k]["prediction_holds"] for c, s in CELLS for k in ("read_nop96", "read_nop128"))
        if not zn_ok or sup["cells_inside"] != sup["cells"]:
            die("step ZN: a cell does not hold; the conclusion of the page would be wrong")
        share = [v["pc"][c, s]["decomposition"]["new_share_pct"] for c, s in CELLS]
        oldloss = [-v["pc"][c, s]["P1"]["median"] for c, s in CELLS]
        if min(share) <= 100.0 or min(oldloss) <= 0:
            die("step S2: the share is not above 100 %, or old read did not lose rate; the prose of section 4 would be wrong")
        h = "<h2 id='conclusion'>4. Conclusion</h2>"
        h += ("<p>The three conditions of the goal, one by one. The status words follow the recorded verdicts. No recorded "
              "rule decides the three conditions themselves, so each status is the assessment of this page. The design file "
              "says: a hypothesis that is only not rejected does not make the problem solved %s.</p><ul class='check'>" % self.R("design"))
        h += ("<li><span class='st'>supported, not proven</span> <b>1. A named mechanism.</b><ul>"
              "<li>A line that comes from the SLC costs the new loop about %s cycles more. At 8 MiB r is %s, so the cost of "
              "the new loop almost reaches the cost of old read.</li>"
              "<li>Step S2, as recorded: &quot;%s&quot;.</li>"
              "<li>Step ZS, as recorded: &quot;%s&quot;.</li>"
              "<li>Hypothesis H1 (not contradicted in step ZN, contradicted for <code>read_nop16</code> in step XN): old "
              "read is limited by its own work in the core, so the extra cost does not show in its rate %s.</li></ul></li>" % (
                  fnum(v["slope"], 2), rng([r["r"] for r in v["a8"]], 2), esc(self.rep.claim("H1 / P1")["overall"]),
                  esc(J["ZS"]["overall"].split(" (")[0]), self.R("final8")))
        h += ("<li><span class='st'>partly</span> <b>2. A controlled test that changes the mechanism.</b><ul>"
              "<li><b>Limit:</b> step ZN changed the core rate of the loop. It did not change the cost of a line from the "
              "SLC.</li>"
              "<li>Recorded: the slowed loops kept their rate at 8 MiB in 4 of 4 cells each. &quot;%s&quot;.</li>"
              "<li>Supplementary (defined after the data was seen): the gain of <code>asmread</code> over each loop was "
              "inside the predicted range in %d of %d cells.</li>"
              "<li>Not done: a test that changes the cost of an SLC line itself. The one attempt (H1d, dirty lines) gave "
              "&quot;Insufficient data&quot; %s.</li></ul></li>" % (
                  esc(J["families"]["ZN"]["overall"]["read_nop96"]), sup["cells_inside"], sup["cells"], self.R("final8")))
        h += ("<li><span class='st'>stated</span> <b>3. The share that is explained, and what is not.</b><ul>"
              "<li>The new loop carries %s %% of the advantage that is lost from 1 MiB to 8 MiB (step S2, recorded). The "
              "share is above 100 %% because old read also lost %s GB/s.</li>"
              "<li>The cycle counts of step ZS give a gain of %s %% at 1 MiB and %s %% at 8 MiB. This page computed these two "
              "values. No rule fixed them before the data.</li>"
              "<li>The full report gives the share per CPU, session and level in its table 20 %s.</li>"
              "<li>The open points are listed below.</li></ul></li></ul>" % (
                  rng(share, 1), rng(oldloss, 2), rng(v["cg1"], 1), rng(v["cg8"], 1), self.R("full")))
        h += "<h3>Not explained (Insufficient data)</h3>"
        h += ("<p>Each point names the measurement that would decide it. Root access was not allowed on CRB for this work "
              "%s.</p><ul>" % self.R("results"))
        h += ("<li><b>Why a line from the SLC costs about %s cycles more.</b> Needed: counters of the SLC and of the mesh (the "
              "network between the cores and the SLC), per line read. Needs root.</li>" % fnum(v["slope"], 2))
        h += ("<li><b>Which hardware part switches the new loop between the two levels at 8 MiB.</b> This includes why CPU 0 "
              "was low on %s and high on %s. Needed: the physical page addresses of the buffer and of the runner's record "
              "block, then mesh counters by level. Needs root. H7 (the record address) stays a hypothesis.</li>" % (
                  self.day(ORIG_FOLDER), self.day(self.rep.folders("H2", 1)[0])))
        h += ("<li><b>Why the rate at which lines arrive at 8 MiB differs between loops</b> (<code>read_nop64</code> and "
              "<code>read_nop16</code>, step 4). The sources name no deciding measurement for this point.</li>")
        h += ("<li><b>Why old read needs %s cycles per line.</b> Needed: counters that split the cycles of the old loop by "
              "pipeline stage (root). Without root: a variant of the old loop with fewer vector adds. That test was not "
              "run %s.</li>" % (fnum(med([r["cyc"] for r in v["o8"]]), 2), self.R("full")))
        h += ("<li><b>Why old read costs more between 2 and 3 MiB</b> (section 2). The sources name no deciding "
              "measurement for this point.</li></ul>")
        fact(res, "an old-loop variant with fewer vector adds at loop offset 40")
        h += "<h3>How the tests ran</h3><ul>"
        h += ("<li>Machine CRB, CPUs 2 and 41 (step H2 also CPU 0), one process at a time, no root.</li>"
              "<li>Each proving step (S2, ZS, ZN, H2) ran in 2 sessions, %s h apart.</li>"
              "<li>System load at launch: %s to %s over all result folders. This is the 1-minute load average. About 1.00 "
              "is the test itself (est.).</li>"
              "<li>%s processes ran, and %d were killed, failed or incomplete %s %s.</li></ul>" % (
                  rng(v["gaps"]), fnum(v["load"][0], 2), fnum(v["load"][1], 2), format(v["procs"], ","), v["bad"],
                  self.R("final8"), self.R("results")))
        return h

    # ================================================================== section 5: the test code
    def ex(self, path, r, what, omit=(), open_=False, note="", mask=None):
        """one excerpt: lines r of the file, with the ranges of 'omit' replaced by one inserted line each.
        mask = (regex, placeholder): the one match inside the excerpt is replaced by the placeholder, in the colour of
        the inserted lines; the generator stops if the regex does not match exactly once."""
        src = Src.get(path)
        a, b = r
        if not (1 <= a <= b <= len(src.L)):
            die("bad excerpt range %r of %s" % (r, path))
        out, n, shown, masked = [], a, 0, 0
        omit = sorted(omit)
        for o in omit:
            if not (a < o[0] <= o[1] < b):
                die("omitted range %r is not inside the excerpt %r of %s" % (o, r, path))
        while n <= b:
            o = next((o for o in omit if o[0] == n), None)
            if o:
                out.append("<span class='gap'>      [...] lines %d-%d left out%s</span>" % (
                    o[0], o[1], (" (%s)" % o[2]) if len(o) > 2 else ""))
                n = o[1] + 1
                continue
            t = esc(src.L[n - 1])
            if mask:
                t, k = re.subn(mask[0], "<span class='gap'>%s</span>" % esc(mask[1]), t)
                masked += k
            out.append("<span class='ln'>%5d</span> %s" % (n, t))
            shown += 1
            n += 1
        if mask and masked != 1:
            die("excerpt %s:%d-%d: the mask %r matched %d times, not once" % (path, a, b, mask[0], masked))
        if shown > 30:
            die("excerpt %s:%d-%d shows %d lines; the limit is 30" % (path, a, b, shown))
        self.n_exc += 1
        self.exc_lines += shown
        return ("<details class='code'%s><summary><code>%s:%s</code> %s</summary><pre>%s</pre>%s</details>" % (
            " open" if open_ else "", esc(short(path)), span(a, b), what, "\n".join(out),
            ("<p class='note'>%s</p>" % note) if note else ""))

    def raw(self, path, r, what, open_=False):
        """an excerpt of a data file (plan, result rows): whole lines; a long line scrolls sideways inside its box"""
        src = Src.get(path)
        out = []
        for n in range(r[0], r[1] + 1):
            out.append("<span class='ln'>%5d</span> %s" % (n, esc(src.L[n - 1])))
        self.n_exc += 1
        self.exc_lines += len(out)
        return ("<details class='code'%s><summary><code>%s:%s</code> %s</summary><pre>%s</pre></details>" % (
            " open" if open_ else "", esc(short(path)), span(r[0], r[1]), what, "\n".join(out)))

    def fn_rows(self):
        """rows of the function table, in call order; every line range is located at run time"""
        S = Src.get
        r8, r11, rh2 = S(os.path.join(X8, "run_bwx8.sh")), S(os.path.join(X11, "run_bwx11.sh")), S(os.path.join(X8, "run_h2.sh"))
        r10 = S(os.path.join(X10, "run_bwx10.sh"))
        b8, b11 = S(os.path.join(X8, "bwx8.c")), S(os.path.join(X11, "bwx11.c"))
        bn, bo = S(os.path.join(BENCH, "bandwidth.c")), S(os.path.join(K13, "bandwidth.orig.c"))
        s8, s11, szs = S(os.path.join(X8, "schedule8.py")), S(os.path.join(X11, "schedule11.py")), S(os.path.join(X11, "schedule_zs.py"))
        s10 = S(os.path.join(X10, "schedule10.py"))
        lv, a8, f8, h2 = (S(os.path.join(HERE, n)) for n in ("levels9.py", "analyze8.py", "final8.py", "h2_analyze.py"))
        loc = lambda src, r: "<code>%s:%s</code>" % (esc(short(src.path)), span(r[0], r[1]))
        rows = []

        def grp(t):
            rows.append(("g", t))

        def row(name, where, role):
            rows.append(("r", name, where, role))

        def sh(name, role, srcs=(r8, r10, r11, rh2)):
            row("<code>%s</code>" % name, "<br>".join(loc(s, s.sh_func(name)) for s in srcs), role)

        def c2(name, role):
            a = b11.c_func(name)
            b = b8.c_func(name, missing_ok=True)
            same = b is not None and b11.text(a) == b8.text(b)
            self.cmp[name] = "absent" if b is None else ("same" if same else "differs")
            row("<code>%s</code>" % name, "%s<br>%s" % (loc(b11, a), loc(b8, b) if b else "not in <code>bwx8.c</code>"),
                role + ("" if same else " <span class='tag'>%s</span>" % (
                    "bwx11 only" if b is None else "bwx11.c differs from bwx8.c by marked additions")))

        grp("A. Development machine: schedules (before the visit) and the login")
        row("<code>Gen.S2</code>", loc(s8, s8.py_def("S2", "Gen")), "Schedule of step S2: every loop order once per size and "
            "CPU, 4 equal trials per process. Calls <code>same_kernel_trial</code> (%s) and <code>add</code> (%s)." % (
                loc(s8, s8.py_def("same_kernel_trial", "Gen")), loc(s8, s8.py_def("add", "Gen"))))
        need(s8, s8.py_def("S4", "Gen"), 'self.sustained("closed")')
        need(s8, s8.py_def("sustained", "Gen"), '"-", "-", "-", k + "@8M", 200, count')
        need(s8, s8.py_def("sustained", "Gen"), "for i in range(3):")
        need(s10, s10.py_def("YF", "Gen"), "ks, 4, 300)] * 4")
        row("<code>Gen.S4</code>", loc(s8, s8.py_def("S4", "Gen")), "Schedule of step S4: 3 processes per loop and CPU at "
            "8 MiB, one trial of 200 windows each. Calls <code>sustained</code> (%s), which calls <code>trial</code> (%s) and "
            "<code>add</code>." % (loc(s8, s8.py_def("sustained", "Gen")), loc(s8, s8.py_def("trial", "Gen"))))
        row("<code>Gen.YF</code>", loc(s10, s10.py_def("YF", "Gen")), "Schedule of step YF (the <code>asmread</code> rates of "
            "step 4): every loop at every size and CPU, 4 equal trials per process. Calls <code>williams_square</code> (%s), "
            "<code>trial</code> (%s) and <code>add</code> (%s)." % (
                loc(s10, s10.py_def("williams_square", "Gen")), loc(s10, s10.py_def("trial", "Gen")), loc(s10, s10.py_def("add", "Gen"))))
        row("<code>Gen.ZN</code>", loc(s11, s11.py_def("ZN", "Gen")), "Schedule of step ZN. Calls <code>all_orders</code> "
            "(%s), <code>trial</code> (%s) and <code>add</code> (%s)." % (
                loc(s11, s11.py_def("all_orders", "Gen")), loc(s11, s11.py_def("trial", "Gen")), loc(s11, s11.py_def("add", "Gen"))))
        row("<code>main</code> of <code>schedule_zs.py</code>", loc(szs, szs.py_def("main")),
            "Schedule of step ZS: 2 loops x %d sizes per CPU, one trial with counters per process. Writes " % len(self.v["zs_sizes"]) +
            "<code>ZS.tsv</code>, <code>ZS.bin</code> and the plan files.")
        ssh = lambda p: "<code>%s:%d</code>" % (esc(short(p)), S(p).find("ssh -o BatchMode"))
        row("<code>visit8.sh</code>, <code>visit10.sh</code>, <code>visit11.sh</code>, <code>visit_h2.sh</code> (no functions)",
            "<br>".join(ssh(os.path.join(d, n)) for d, n in ((X8, "visit8.sh"), (X10, "visit10.sh"), (X11, "visit11.sh"),
                                                             (X8, "visit_h2.sh"))),
            "One ssh login per visit. The remote command checks the marker file first, then starts the run script.")
        grp("B. CRB, shell: the run scripts run_bwx8.sh (S2, S4), run_bwx10.sh (YF), run_bwx11.sh (ZS, ZN) and run_h2.sh (H2)")
        # the order of the two calls in the step loop of the run scripts
        for rs in (r10, r11):
            a = rs.find(r'^for STEP_NAME in "\$\{STEPS\[@\]\}"; do', rs.sh_func("load_step")[1], regex=True)
            if rs.L[a].strip() != "pick_bin" or rs.L[a + 1].strip() != "load_step":
                die("%s does not call pick_bin and then load_step at the start of its step loop" % rs.path)
        sh("pick_bin", "Chooses the runner binary of the step from <code>&lt;STEP&gt;.bin</code>. Not in "
                       "<code>run_bwx8.sh</code>, which has one binary.", (r10, r11))
        sh("load_step", "Reads <code>&lt;STEP&gt;.tsv</code>: one runner command line per process. Adds up the planned work.",
           (r8, r10, r11))
        sh("one", "One process: checks, load record, header line, start of the runner, wait.")
        sh("check_marker", "Stops if the marker file, the stop file or the stop time is there. Calls <code>why_stop</code>.")
        sh("why_stop", "The three stop conditions.")
        sh("check_deadline", "Stops if the stop time is too near.")
        sh("settle", "Waits until at most 2 tasks are runnable, 20 s at most.")
        grp("C. CRB, runner process: bwx11.c (ZS, ZN) and bwx8.c (S2, S4). Step YF ran bwx10, see section 5.1")
        self.cmp = {}
        for name, role in [
            ("main", "Reads the start time of the process. Sees <code>--trial</code> and returns <code>trial_main</code>."),
            ("now_ns", "One <code>clock_gettime(CLOCK_MONOTONIC)</code> in ns. The only clock of the window times."),
            ("restrict_cpus", "Removes CPUs above 119 from the allowed set."),
            ("trial_main", "Parses the options (<code>parse_cpus</code>, <code>parse_bytes</code>, <code>parse_long</code>). "
                           "Reads the plan. Pins the controlling thread. Starts the worker thread and waits."),
            ("parse_events", "Only with <code>--events</code> (step ZS): stores each NAME=CODE pair."),
            ("read_plan", "Reads the plan file. Calls <code>plan_pairs</code> and, per trial line, <code>plan_trial</code>."),
            ("plan_trial", "Splits the 11 fields of one trial line. Calls <code>plan_long</code>, <code>plan_part</code>, "
                           "<code>plan_size</code>, <code>trial_windows</code>, <code>window_bins</code>."),
            ("trial_worker", "The worker thread: pin, buffer, first touch, records, then the trial loop."),
            ("pin_cpu", "<code>sched_setaffinity</code> to one CPU."),
            ("alloc_buf", "Maps the buffer at a 2 MiB boundary and asks for 2 MiB pages. Uses <code>buf_len</code>."),
            ("k_write", "First touch of the buffer by the pinned worker."),
            ("alloc_records", "Allocates and first-touches the records of all trials. Calls <code>set_windows</code>."),
            ("set_windows", "Fills each window record: loop, size, duration, passes per clock read."),
            ("print_s", "Prints the S row (the plan line) before the trial."),
            ("run_trial", "Opens or closes the counters as the plan says. Calls the timed sequence between two sets of "
                          "side readings."),
            ("count_open", "Only with counters (step ZS): one <code>perf_event_open</code> per event, one group, user mode only."),
            ("page_read", "Huge-page coverage of the buffer before and after (P rows). Calls <code>read_smaps</code>, "
                          "<code>read_vmstat</code>."),
            ("switches", "Context-switch counts of the thread before and after (E row)."),
            ("tcpu", "Thread CPU time before and after (E row). Calls <code>cpu_ns</code>."),
            ("timed_sequence", "<b>The measurement.</b> Per window: clock, whole passes of the loop until the window "
                               "length, clock. Stores bytes, start and end."),
            ("tcount", "Only step ZS: one read of the counter group at each boundary of a timed window."),
            ("tclock", "<code>now_ns()</code>."),
            ("tcall", "One call of the loop through <code>call</code>."),
            ("call", "Calls the loop function with the buffer and its length in words."),
            ("THE LOOP", ""),
            ("emit_trial", "After the timed sequence: prints the P, W, C and E rows of the trial. Calls "
                           "<code>print_p8</code>, <code>print_na</code>, <code>first_multiplexed</code>."),
            ("count_close", "After the last trial, and only if a counter group is open (step ZS): closes the group."),
        ]:
            if name == "THE LOOP":
                k_old, k_asm, k_c = b11.macro("DEF_OLDREAD"), b11.macro("DEF_ASMREAD"), b11.c_func("k_read")
                row("the loop: <code>k_oldread</code>, <code>k_read</code>, <code>k_asmread</code>, <code>k_read_nop96</code>, "
                    "<code>k_read_nop128</code>",
                    "%s<br>%s<br>%s<br><code>%s:%d-%d</code>" % (
                        loc(b11, k_old), loc(b11, k_c), loc(b11, k_asm), esc(short(b11.path)),
                        b11.find("DEF_ASMREAD(read_nop96, 96)"), b11.find("DEF_ASMREAD(read_nop128, 128)")),
                    "One call is one pass over the buffer. Macro <code>DEF_OLDREAD</code>, function <code>k_read</code>, macro "
                    "<code>DEF_ASMREAD</code> with its nop count.")
                continue
            c2(name, role)
        # count_close: called after the trial loop of the worker
        wa, wb = b11.c_func("trial_worker")
        e = b11.find("emit_trial(w, i);", wa, wb)
        need(b11, (e, wb), "if (w->group_open)")
        need(b11, (e, wb), "count_close(w);")
        for sub in ("parse_cpus", "parse_bytes", "parse_long", "plan_pairs", "plan_long", "plan_part", "plan_size",
                    "trial_windows", "window_bins", "buf_len", "read_smaps", "read_vmstat", "cpu_ns", "print_p8", "print_na",
                    "first_multiplexed", "k_read"):
            a = b11.c_func(sub)
            b = b8.c_func(sub)
            self.cmp[sub] = "same" if b11.text(a) == b8.text(b) else "differs"
        for mac in ("DEF_OLDREAD", "DEF_ASMREAD"):
            self.cmp[mac] = "same" if b11.text(b11.macro(mac)) == b8.text(b8.macro(mac)) else "differs"
        grp("D. CRB, the original benchmark (step H2): bandwidth.c (bw_new) and bandwidth.orig.c (bw_old)")
        for name, role in [
            ("main", "Parses the options (<code>parse_cpus</code>, <code>parse_bytes</code>). Starts 1 worker. Per "
                     "repetition: releases the worker, waits, prints one row."),
            ("worker", "Pin, buffer, first touch. Per repetition: 1 warm-up pass, then passes until 0.5 s, between two "
                       "clock reads."),
            ("pin_cpu", "<code>sched_setaffinity</code> to one CPU."),
            ("alloc_buf", "Buffer at a 2 MiB boundary, 2 MiB pages asked for."),
            ("k_write", "First touch of the buffer."),
            ("now_s", "CLOCK_MONOTONIC in seconds."),
            ("pass", "One pass: calls <code>k_read</code>."),
            ("k_read", "The loop. New read (load-only) in <code>bandwidth.c</code>. Old read (16 sums) in "
                       "<code>bandwidth.orig.c</code>."),
        ]:
            # c_func skips the definitions inside the "History" comment blocks of bandwidth.c
            row("<code>%s</code>" % name, "%s<br>%s" % (loc(bn, bn.c_func(name)), loc(bo, bo.c_func(name))), role)
        grp("E. Development machine: the analysis, from result rows to verdicts")
        row("<code>parse_csv</code>", loc(lv, lv.py_def("parse_csv")), "Reads the rows of every process of a result file.")
        row("<code>Window.rate</code>", loc(lv, lv.py_def("rate", "Window")), "Rate of one window: bytes / (end - start), GB/s.")
        row("<code>per64</code>", loc(lv, lv.py_def("per64")), "A count per 64-byte line: count x 64 / bytes.")
        row("<code>counter_windows</code>", loc(lv, lv.py_def("counter_windows")), "The counted windows of a process, with a "
            "flag for windows where the counters did not run the whole time.")
        row("<code>counter_proc</code>", loc(f8, f8.py_def("counter_proc")), "Per process: median rate and median count per "
            "line. Gives the cycles per line and r of step ZS.")
        row("<code>proc_cell_values</code>, <code>cell_stats</code>, <code>cells_of</code>",
            "%s<br>%s<br>%s" % (loc(lv, lv.py_def("proc_cell_values")), loc(f8, f8.py_def("cell_stats")), loc(f8, f8.py_def("cells_of"))),
            "Cell values of steps ZN and YF: per process the median and the 5th and 95th percentile of all windows, then the "
            "median over the processes.")
        row("<code>scan_folder</code>", loc(f8, f8.py_def("scan_folder")), "Reads the load at launch and the process counts of a folder.")
        row("<code>Trial.check</code>, <code>Trial.usable</code>, <code>Trial.rate</code>",
            "%s<br>%s<br>%s" % (loc(a8, a8.py_def("check", "Trial")), loc(a8, a8.py_def("usable", "Trial")), loc(a8, a8.py_def("rate", "Trial"))),
            "Step S2: which trials count, and the rate of a window.")
        row("<code>cell_rate</code>, <code>s2_units</code>", "%s<br>%s" % (loc(a8, a8.py_def("cell_rate")), loc(a8, a8.py_def("s2_units"))),
            "Step S2: one value per process (median of its 4 trials), and the matched sets of processes.")
        row("<code>contrast</code>", loc(a8, a8.py_def("contrast")), "Step S2: a difference of rates over the 6 matched sets, "
            "with its median, its limit and the word &quot;repeatable&quot;.")
        row("<code>p1_cell</code>, <code>confirm</code>, <code>decomposition</code>",
            "%s<br>%s<br>%s" % (loc(a8, a8.py_def("p1_cell")), loc(a8, a8.py_def("confirm")), loc(a8, a8.py_def("decomposition"))),
            "Step S2: the P1 margin, the P2 confirmation over CPUs and sessions, the share of the new loop.")
        row("<code>stage2</code>, <code>item2</code>", "%s<br>%s" % (loc(a8, a8.py_def("stage2")), loc(f8, f8.py_def("item2"))),
            "Step S2: builds the contrasts, and takes the results into <code>final8.json</code>.")
        row("<code>zs_band</code>, <code>rule_zs_cell</code>, <code>lsq</code>, <code>rule_zs_overall</code>, <code>item13</code>",
            "<br>".join(loc(f8, f8.py_def(n)) for n in ("zs_band", "rule_zs_cell", "lsq", "rule_zs_overall", "item13")),
            "Step ZS: the band, the count of sizes outside, the fitted line, the verdict.")
        row("<code>rule_zn_kernel</code>, <code>item7</code>", "%s<br>%s" % (loc(f8, f8.py_def("rule_zn_kernel")), loc(f8, f8.py_def("item7"))),
            "Step ZN: the rule for one loop in one cell, and the verdict.")
        row("<code>sup_gain</code>", loc(f8, f8.py_def("sup_gain")), "Supplementary: the gain predicted from two rates.")
        row("<code>parse</code>, <code>complete</code>, <code>pairs_of</code>, <code>gain</code>, <code>classify</code>",
            "<br>".join(loc(h2, h2.py_def(n)) for n in ("parse", "complete", "pairs_of", "gain", "classify")),
            "Step H2: reads the rows of the original program, pairs neighbouring processes, gain and level of a repetition.")
        row("<code>h2_cpu_session</code>, <code>h2_verdict</code>, <code>item8</code>",
            "<br>".join(loc(f8, f8.py_def(n)) for n in ("h2_cpu_session", "h2_verdict", "item8")),
            "Step H2: counts and gains per CPU and session, and the verdict.")
        return rows

    def builds(self):
        """facts about the builds, computed here from the sources and the build records"""
        S = Src.get
        b8, b11 = S(os.path.join(X8, "bwx8.c")), S(os.path.join(X11, "bwx11.c"))
        kept, skip = [], False
        for line in b11.L:
            if line.strip() in ("/* bwx10+ */", "/* bwx11+ */"):
                skip = True
            elif line.strip() in ("/* bwx10- */", "/* bwx11- */"):
                skip = False
            elif not skip:
                kept.append(line)
        if len(kept) != len(b8.L) or b8.L[-1] != "":
            die("bwx11.c without its marked blocks has %d lines, bwx8.c has %d" % (len(kept), len(b8.L)))
        diff = [(x, y) for x, y in zip(kept, b8.L) if x != y]
        if not all("selftest" in x and "selftest" in y for x, y in diff):
            die("bwx11.c differs from bwx8.c outside the marked blocks and the self-test include")
        l8 = listing_sections(os.path.join(X8, "crb-build-1", "listing.txt"))
        l11 = listing_sections(os.path.join(X11, "crb-build-1", "listing.txt"))
        pr = listing_sections(os.path.join(self.results, PROBE_FOLDER, "probe.txt"))
        for k in ("read", "asmread", "oldread"):
            if l8["bwx8 " + k] != l11["bwx11 " + k] or not l8["bwx8 " + k]:
                die("the machine code of %s differs between bwx8 and bwx11" % k)
        if pr["bw_new k_read"] != l8["bwx8 read"] or pr["bw_old k_read"] != l8["bwx8 oldread"]:
            die("the machine code of the original binaries differs from the runner's loops")
        # the two sources of the original binaries: their digests must stand in the build record
        probe = S(os.path.join(self.results, PROBE_FOLDER, "probe.txt"))
        for path, name in ((os.path.join(BENCH, "bandwidth.c"), "bandwidth.c"), (os.path.join(K13, "bandwidth.orig.c"), "bandwidth.orig.c")):
            with open(path, "rb") as f:
                dig = hashlib.sha256(f.read()).hexdigest()
            if "%s  %s" % (dig, name) not in probe.text((1, len(probe.L))):
                die("%s is not the source that the build record of bw_old and bw_new names (sha256 %s)" % (path, dig))
        off = {}
        for k in ("read", "asmread", "oldread"):
            o8 = loop_mod64(os.path.join(X8, "crb-build-1", "offsets.tsv"), "bwx8", k)[0]
            o11 = loop_mod64(os.path.join(X11, "crb-build-1", "offsets.tsv"), "bwx11", k)[0]
            o10 = loop_mod64(os.path.join(X10, "crb-build-1", "offsets.tsv"), "bwx10", k)[0]
            if not (o8 == o11 == o10):
                die("the loop offset of %s differs between the builds" % k)
            off[k] = o8
        flags = {}
        for d in (X8, X11):
            b = S(os.path.join(d, "crb-build-1", "build.txt"))
            flags[d] = b.L[b.find("## CFLAGS=") - 1].split("=", 1)[1]
        if flags[X8] != flags[X11]:
            die("bwx8 and bwx11 were built with different flags")
        rk = S(os.path.join(K13, "run_kernels.sh"))
        kflags = rk.L[rk.find('CFLAGS="') - 1].split('"')[1]
        extra = [f for f in flags[X8].split() if f not in kflags.split()]
        bins = {st: S(os.path.join(X11, "sched11", "s1", st + ".bin")).L[0].strip() for st in ("ZS", "ZN")}
        bins["YF"] = S(os.path.join(X10, "sched10", "s1", "YF.bin")).L[0].strip()
        if bins != {"ZS": "bwx11", "ZN": "bwx11", "YF": "bwx10"}:
            die("unexpected binary words %r" % bins)
        r8 = S(os.path.join(X8, "run_bwx8.sh"))
        need(r8, (1, len(r8.L)), "BIN=${BWX8_BIN:-$SRC/bwx8}")
        return {"lines": len(b8.L) - 1, "diff": len(diff), "off": off, "flags": flags[X8], "extra": extra, "kflags": kflags}

    def code_facts(self):
        """constants that the text of section 5 and of the steps repeats: stop if the code says something else"""
        S = Src.get
        b11, r8, rh2 = S(os.path.join(X11, "bwx11.c")), S(os.path.join(X8, "run_bwx8.sh")), S(os.path.join(X8, "run_h2.sh"))
        bn, szs = S(os.path.join(BENCH, "bandwidth.c")), S(os.path.join(X11, "schedule_zs.py"))
        need(r8, r8.sh_func("settle"), "r <= 2 || t >= 20")
        need(b11, (1, 200), "#define MAX_USE_CPU 119")
        need(b11, (1, 200), "#define HUGE_BYTES (2UL << 20)")
        need(b11, (1, 200), "#define CHECK_BYTES (8UL << 20)")
        need(b11, b11.c_func("alloc_buf"), "MADV_HUGEPAGE")
        need(b11, b11.c_func("count_open"), "a.exclude_kernel = 1")
        need(b11, b11.macro("DEF_ASMREAD"), "add %[p], %[p], #256")
        need(b11, b11.c_func("set_windows"), "CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1")
        need(rh2, (1, len(rh2.L)), "CPUS=(2 0 41)")
        need(bn, bn.c_func("worker"), "/* warm-up */")
        need(szs, (1, len(szs.L)), 'KERNELS = ["asmread", "oldread"]')
        fact(os.path.join(self.results, ORIG_FOLDER, "one-thread.csv"), "min_ms=500")
        fact(os.path.join(N_DIR, "tackle-8mb-report.html"), "Table 20.")

    def sec_code(self):
        S = Src.get
        v = self.v
        h = "<h2 id='code'>5. The test code</h2>"
        h += ("<p>This section lists every function on the path of a measurement, from the login script down to the loop "
              "and back up to the rule. It shows short excerpts and no whole file. Each excerpt was cut from the real file "
              "when this page was built. The generator inserted two kinds of text, both <span class='gapx'>in this "
              "colour</span>: a line &quot;[...] lines a-b left out&quot;, and one placeholder for the address of CRB "
              "(section 5.4).</p>")
        h += ("<p class='note'>Path shorthands, all below <code>%s</code>: %s. R = <code>%s</code>.</p>" % (
            esc(ROOT), "; ".join("%s = <code>%s</code>" % (k, esc(os.path.relpath(p, ROOT))) for k, p in SHORT),
            esc(os.path.relpath(self.results, ROOT))))
        B = self.builds()
        rows_fn = self.fn_rows()
        self.code_facts()

        # 5.1 which program ran which step
        h += "<h3 id='code-bin'>5.1 Which program ran which step</h3>"
        t = lambda *cells: [RF.TH(cells[0])] + ["<td class='txt'>%s</td>" % c for c in cells[1:]]
        rows = [
            t("S2 (step 1)", "<code>bwx8</code>, source <code>X8/bwx8.c</code>", "<code>visit8.sh</code> &rarr; <code>run_bwx8.sh</code>",
              "<code>X8/schedule8.py</code>, method <code>Gen.S2</code>"),
            t("ZS (step 3)", "<code>bwx11</code>, source <code>X11/bwx11.c</code>", "<code>visit11.sh</code> &rarr; <code>run_bwx11.sh</code>",
              "<code>X11/schedule_zs.py</code>"),
            t("ZN (step 4)", "<code>bwx11</code>", "<code>visit11.sh</code> &rarr; <code>run_bwx11.sh</code>",
              "<code>X11/schedule11.py</code>, method <code>Gen.ZN</code>"),
            t("YF (step 4, the asmread rates)", "<code>bwx10</code>, source <code>X10/bwx10.c</code>",
              "<code>visit10.sh</code> &rarr; <code>run_bwx10.sh</code>", "<code>X10/schedule10.py</code>, method <code>Gen.YF</code>"),
            t("S4 (step 5, the trace)", "<code>bwx8</code>", "<code>visit8.sh</code> &rarr; <code>run_bwx8.sh</code>",
              "<code>X8/schedule8.py</code>, method <code>Gen.S4</code>"),
            t("H2 (step 5)", "the original benchmark: <code>bw_old</code> (source <code>K13/bandwidth.orig.c</code>) and "
                             "<code>bw_new</code> (source <code>BENCH/bandwidth.c</code>)",
              "<code>visit_h2.sh</code> &rarr; <code>run_h2.sh</code>", "none: <code>run_h2.sh</code> builds the order itself"),
        ]
        self.n_codetab += 1
        h += table(["Step", "Program", "Started by", "Schedule"], rows, "Code table 1. Program, start scripts and "
                   "schedule of each step whose data this page shows.", cls="wrap")
        same = sorted(k for k, x in self.cmp.items() if x == "same")
        differs = sorted(k for k, x in self.cmp.items() if x == "differs")
        absent = sorted(k for k, x in self.cmp.items() if x == "absent")
        if absent:
            die("functions of the path that bwx8.c does not have: %r" % absent)
        if not differs:
            die("no function differs between bwx8.c and bwx11.c: the sentence on the tags would be wrong")
        for k in ("timed_sequence", "tcall", "call", "tcount", "set_windows", "count_open", "emit_trial", "k_read",
                  "DEF_OLDREAD", "DEF_ASMREAD"):
            if self.cmp.get(k) != "same":
                die("%s is not the same text in bwx8.c and bwx11.c" % k)
        b10 = S(os.path.join(X10, "bwx10.c"))
        b11s = S(os.path.join(X11, "bwx11.c"))
        for k in ("timed_sequence", "tcall", "call", "set_windows", "k_read"):
            if b10.text(b10.c_func(k)) != b11s.text(b11s.c_func(k)):
                die("%s is not the same text in bwx10.c and bwx11.c" % k)
        if b10.text(b10.macro("DEF_ASMREAD")) != b11s.text(b11s.macro("DEF_ASMREAD")):
            die("DEF_ASMREAD is not the same text in bwx10.c and bwx11.c")
        h += ("<p><code>bwx11.c</code> is <code>bwx8.c</code> plus marked additions. The functions of the timed path and the "
              "loops have the same text in <code>bwx8.c</code>, <code>bwx10.c</code> and <code>bwx11.c</code>. So the "
              "excerpts below show <code>bwx11.c</code> only %s %s %s.</p>" % (self.R("x8"), self.R("x10"), self.R("x11")))
        h += "<details class='sup'><summary>Detail: what was compared between the builds</summary><ul>"
        h += ("<li>With the marked blocks (<code>/* bwx10+ */</code>, <code>/* bwx11+ */</code>) removed, "
              "<code>bwx11.c</code> and <code>bwx8.c</code> have %d lines each, and %d line differs: the include of the "
              "self-test file.</li>" % (B["lines"], B["diff"]))
        h += ("<li>Of the %d functions and macros compared, %d have the same text in <code>bwx8.c</code> and "
              "<code>bwx11.c</code>. %d differ, by marked additions only: %s. The added options (<code>--hot-copy</code>, "
              "<code>--rec-pad</code>, <code>--evict-mb</code>) were not used in steps S2, ZS and ZN.</li>" % (
                  len(self.cmp), len(same), len(differs), ", ".join("<code>%s</code>" % d for d in differs)))
        h += ("<li>The loops <code>k_read</code>, <code>k_asmread</code> and <code>k_oldread</code> have the same machine "
              "instructions in <code>bwx8</code> and <code>bwx11</code>. Their loops start at the same place in the code in "
              "all three builds, in bytes modulo 64: %s.</li>" % ", ".join("%s %d" % (k, o) for k, o in B["off"].items()))
        h += ("<li>The loop of <code>bw_new</code> has the same instructions as <code>k_read</code> of <code>bwx8</code>. The "
              "loop of <code>bw_old</code> has the same instructions as <code>k_oldread</code> of <code>bwx8</code> %s.</li>"
              % self.R("bench"))
        h += ("<li>Build flags of the runners <code>bwx8</code> and <code>bwx11</code>: <code>%s</code>. The original "
              "binaries were built without the last %d flags (%s).</li></ul></details>" % (
                  esc(B["flags"]), len(B["extra"]), ", ".join("<code>%s</code>" % esc(f) for f in B["extra"])))

        # 5.2 the call chain
        h += "<h3 id='code-chain'>5.2 The call chain of one measured window</h3>"
        h += ("<figure class='diagram'><div class='figtitle'>Diagram 2. From the login to the loop, and back to the rule "
              "(steps S2, S4, YF, ZS, ZN). Step H2 uses the original program in place of the runner</div><div class='chain'>"
              "<div class='lay'><div class='where'>Development machine</div><ul>"
              "<li><code>schedule8.py</code> / <code>schedule10.py</code> / <code>schedule11.py</code> / "
              "<code>schedule_zs.py</code> write the plan files</li>"
              "<li><code>visit8.sh</code> / <code>visit10.sh</code> / <code>visit11.sh</code> / <code>visit_h2.sh</code>: one "
              "ssh login, marker check first</li>"
              "</ul></div><div class='down'>&darr; ssh</div>"
              "<div class='lay'><div class='where'>CRB, shell</div><ul>"
              "<li><code>run_bwx8.sh</code> / <code>run_bwx10.sh</code> / <code>run_bwx11.sh</code> / <code>run_h2.sh</code><ul>"
              "<li><code>pick_bin</code> chooses the binary (not in <code>run_bwx8.sh</code>), then <code>load_step</code> "
              "reads <code>&lt;STEP&gt;.tsv</code></li>"
              "<li>per process <code>one</code>: <code>check_marker</code>, <code>check_deadline</code>, <code>settle</code>, "
              "load record, header line, start</li></ul></li>"
              "</ul></div><div class='down'>&darr; <code>bwx11 --trial --cpus C --bytes B --plan NNNN.plan</code></div>"
              "<div class='lay hot'><div class='where'>CRB, runner process</div><ul>"
              "<li><code>main</code> &rarr; <code>trial_main</code>: <code>read_plan</code>, pin the controlling thread</li>"
              "<li>thread <code>trial_worker</code>: <code>pin_cpu</code>, <code>alloc_buf</code>, <code>k_write</code> (first "
              "touch), <code>alloc_records</code> &rarr; <code>set_windows</code><ul>"
              "<li>per trial: <code>print_s</code>, <code>run_trial</code>, <code>emit_trial</code>. After the last trial: "
              "[<code>count_close</code>]<ul>"
              "<li><code>run_trial</code>: [<code>count_open</code>], <code>page_read</code>, <code>switches</code>, <code>tcpu</code><ul>"
              "<li><b><code>timed_sequence</code></b>, per window: [<code>tcount</code>] <code>tclock</code> &rarr; repeat "
              "{ <code>tcall</code> &rarr; <code>call</code> &rarr; <b>the loop</b> } &rarr; <code>tclock</code></li></ul></li>"
              "<li><code>emit_trial</code>: W row (bytes, start, end) and C row (counter differences)</li></ul></li></ul></li>"
              "</ul></div><div class='down'>&darr; result file <code>&lt;STEP&gt;.csv</code>, copied to R</div>"
              "<div class='lay'><div class='where'>Development machine, analysis</div><ul>"
              "<li><code>levels9.py</code>: <code>parse_csv</code>, <code>Window.rate</code> (GB/s), <code>per64</code> (count per line)</li>"
              "<li><code>final8.py</code>: <code>counter_proc</code> &rarr; <code>rule_zs_cell</code>, <code>rule_zn_kernel</code>, "
              "<code>h2_verdict</code>; <code>analyze8.py</code>: <code>contrast</code>, <code>p1_cell</code> (step S2)</li>"
              "<li><code>final8.json</code> &rarr; this page</li></ul></div></div>"
              "<p class='note'>Square brackets: only with counters (step ZS). In steps S2, S4, YF and ZN no counter is "
              "open.</p></figure>")

        # 5.3 the function table
        h += "<h3 id='code-fn'>5.3 Every function on the path</h3>"
        h += ("<p>In call order. The line ranges were located when this page was built. For the runner, the first range is "
              "<code>bwx11.c</code> and the second is <code>bwx8.c</code>. A tag marks the rows whose text differs between "
              "the two files.</p>")
        body = ""
        n = 0
        for r in rows_fn:
            if r[0] == "g":
                body += "<tr class='grp'><th colspan='4' scope='colgroup'>%s</th></tr>" % esc(r[1])
            else:
                n += 1
                body += "<tr><td class='num'>%d</td><th scope='row'>%s</th><td class='loc'>%s</td><td class='txt'>%s</td></tr>" % (
                    n, r[1], r[2], r[3])
        self.n_codetab += 1
        self.n_fnrows = n
        h += ("<div class='tcap'>Code table 2. Every function on the path of one measured window, in call order.</div>"
              "<div class='tbl'><table class='fn'><thead><tr><th scope='col'>#</th><th scope='col'>Function</th><th scope='col'>File "
              "and lines</th><th scope='col'>What it does for the measurement</th></tr></thead><tbody>%s</tbody></table></div>" % body)

        # 5.4 excerpts
        X = self.ex
        v8, v11 = os.path.join(X8, "visit8.sh"), os.path.join(X11, "visit11.sh")
        r8p, r11p, rh2p = os.path.join(X8, "run_bwx8.sh"), os.path.join(X11, "run_bwx11.sh"), os.path.join(X8, "run_h2.sh")
        r8, r11, rh2 = S(r8p), S(r11p), S(rh2p)
        b11p = os.path.join(X11, "bwx11.c")
        b11 = S(b11p)
        l11p = os.path.join(X11, "crb-build-1", "listing.txt")
        l11 = S(l11p)
        bnp, bop = os.path.join(BENCH, "bandwidth.c"), os.path.join(K13, "bandwidth.orig.c")
        bn, bo = S(bnp), S(bop)
        lvp, a8p, f8p, h2p = (os.path.join(HERE, n) for n in ("levels9.py", "analyze8.py", "final8.py", "h2_analyze.py"))
        lv, a8, f8, h2 = S(lvp), S(a8p), S(f8p), S(h2p)

        h += "<h3 id='code-top'>5.4 Excerpts: the top level (login, run script, schedule, plan)</h3>"
        a = S(v11).find("M='if [ -e /tmp/positron-perf.RUNNING")
        h += X(v11, (a, S(v11).find('echo "ssh status', a)), "the visit: marker check, then one ssh login that starts the run script",
               open_=True, mask=(r"(?<=@)\d+\.\d+\.\d+\.\d+", "<address of CRB>"),
               note="The generator replaced the network address of CRB in this excerpt. That line is not word for word.")
        h += ("<p class='note'><code>visit8.sh</code>, <code>visit10.sh</code> and <code>visit_h2.sh</code> have the same two "
              "lines with their own folder and run script.</p>")
        a, b = r8.sh_func("why_stop")[0], r8.sh_func("settle")[1]
        t0 = r8.find("trap '", a, b)
        h += X(r8p, (a, b), "the checks before every process: marker file, stop file, stop time, settle", omit=[(t0, t0, "the trap line")])
        a, b = r8.sh_func("one")
        w0 = r8.find("while kill -0", a, b)
        w1 = r8.find("done", w0, b)
        for st in ("ZS", "ZN"):
            for ses in ("s1", "s2"):
                if os.path.exists(os.path.join(X11, "sched11", ses, st + ".watch")):
                    die("a host sampler file exists for step %s: the note under the excerpt of 'one' would be wrong" % st)
        need(r11, r11.sh_func("one"), "if (( WATCH_ON )); then")
        need(r11, r11.sh_func("one"), 'setsid "$BIN" "$@" >> "$OUT/$csv"')
        h += X(r8p, (a, b), "<code>one</code>: one process. Checks, load record, header line with the load, start of the runner",
               omit=[(w0, w1, "the wait loop: checks the marker every second")], open_=True,
               note="<code>run_bwx11.sh</code> (steps ZS and ZN) has the same function with the same start line. It adds an "
                    "optional host sampler, which runs only if a file <code>&lt;STEP&gt;.watch</code> exists. No such file "
                    "exists for ZS and ZN.")
        a = r8.find('one "$STEP_NAME.csv"')
        h += X(r8p, (a - 3, a + 1), "the loop over the processes of a step")
        h += X(r11p, r11.sh_func("pick_bin"), "<code>pick_bin</code>: which runner binary a step of round 4 uses")
        s8p, szp, s11p = os.path.join(X8, "schedule8.py"), os.path.join(X11, "schedule_zs.py"), os.path.join(X11, "schedule11.py")
        h += X(s8p, S(s8p).py_def("S2", "Gen"), "schedule of step S2")
        h += X(s11p, S(s11p).py_def("ZN", "Gen"), "schedule of step ZN")
        s10p = os.path.join(X10, "schedule10.py")
        h += X(s10p, S(s10p).py_def("YF", "Gen"), "schedule of step YF (the <code>asmread</code> rates of step 4)")
        a, _ = S(s8p).py_def("sustained", "Gen")
        h += X(s8p, (a, S(s8p).py_def("S4", "Gen")[1]), "schedule of step S4 (the 60 s runs of step 5): <code>sustained</code> and <code>S4</code>")
        for st, d in (("S2", os.path.join(X8, "sched")), ("S4", os.path.join(X8, "sched")),
                      ("YF", os.path.join(X10, "sched10")), ("ZN", os.path.join(X11, "sched11"))):
            for ses in ("s1", "s2"):
                plans = [f for f in sorted(os.listdir(os.path.join(d, ses, st))) if f.endswith(".plan")]
                for f in plans:
                    if any(ln.split()[9] != "closed" for ln in S(os.path.join(d, ses, st, f)).L if ln and not ln.startswith("#")):
                        die("a plan of step %s opens the counters: the note of Diagram 2 would be wrong" % st)
        a = S(szp).find("SIZES = [")
        h += X(szp, (a, S(szp).find("rows.append(", a)), "schedule of step ZS: sizes, loops, counter events, one plan per process",
               omit=[(S(szp).find("BASE =", a), S(szp).find("rows = []", a), "seed and folders")])
        p_zs, p_s2, p_zn = (os.path.join(X11, "sched11", "s1", "ZS", "0000.plan"), os.path.join(X8, "sched", "s1", "S2", "0000.plan"),
                            os.path.join(X11, "sched11", "s1", "ZN", "0012.plan"))
        h += self.raw(p_zs, (1, 4), "a plan file of step ZS (the whole file): 1 trial, 20 windows of 300 ms, counters read", open_=True)
        h += self.raw(p_s2, (1, 4), "a plan file of step S2, first trial of 4")
        zn_plan = S(p_zn)
        need(zn_plan, (1, 4), "kernel=read_nop96 size=8388608")
        h += self.raw(p_zn, (1, 4), "a plan file of step ZN: read_nop96 at 8 MiB, first trial of 4")
        need(b11, (1, len(b11.L)), "#define PLAN_FIELDS 11")
        h += ("<p class='note'><b>Legend of a trial line</b> (11 fields): trial number; <code>cond</code> = name of the "
              "condition; <code>rep</code> = repeat number; <code>prev</code>, <code>pfx</code>, <code>pred</code> = "
              "preparation parts as LOOP@SIZE:MS or &quot;-&quot;; <code>tgt</code> = the timed loop as LOOP@SIZE; "
              "<code>nwin</code> = number of timed windows; <code>win_ms</code> = length of a window in ms; "
              "<code>count</code> = counters closed, open or read; <code>bins</code> = 1 for extra 10 ms records. "
              "The prefix runs as 4 windows of MS / 4 each.</p>")
        zs_csv = os.path.join(self.results, self.rep.folders("ZS", 1)[0], "ZS.csv")
        h += self.raw(zs_csv, (1, 1), "the header line that the run script writes before a process (step ZS, with the load)")

        h += "<h3 id='code-runner'>5.5 Excerpts: the runner (trial loop, timing, counters)</h3>"
        a, _ = b11.c_func("main")
        h += X(b11p, (a, b11.find("return trial_main(argc, argv);", a)), "<code>main</code>: start time, then <code>trial_main</code>")
        ta, tb = b11.c_func("trial_main")
        a = b11.find("/* The plan can run.", ta, tb)
        h += X(b11p, (a, tb), "<code>trial_main</code>: the controlling thread pins itself and starts the worker thread")
        h += X(b11p, b11.c_func("pin_cpu"), "<code>pin_cpu</code>")
        wa, wb = b11.c_func("trial_worker")
        a = b11.find("pin_cpu(cfg.cpus[0]);", wa, wb)
        h += X(b11p, (a, b11.find("alloc_records(w);", a, wb)), "<code>trial_worker</code>: pin, buffer, first touch, records", open_=True)
        a = b11.find("for (int i = 0; i < plan.n; i++) {", b11.find("if (!madvise_ok)", wa, wb), wb)
        h += X(b11p, (a, wb), "<code>trial_worker</code>: the trial loop", open_=True)
        ra, rb = b11.c_func("run_trial")
        o0 = b11.find("r->state =", ra, rb)
        o1 = b11.find("page_read(w, r, 0);", ra, rb) - 2
        h += X(b11p, (ra, rb), "<code>run_trial</code>: what stands before and after the timed sequence",
               omit=[(o0, o1, "counter state, and the check value for the sum of old read")])
        ta, tb = b11.c_func("timed_sequence")
        o0 = b11.find("/* A bin closes on this clock read", ta, tb)
        o1 = b11.find("} while (t1 - t0 < x->dur_ns);", ta, tb) - 1
        h += X(b11p, (ta, tb), "<b><code>timed_sequence</code></b>: the measurement of one trial, window by window",
               omit=[(o0, o1, "the optional 10 ms records")], open_=True,
               note="A window runs whole passes until its length is reached. The clock is read after every "
                    "<code>passes</code> passes.")
        sa, sb = b11.c_func("set_windows")
        a = b11.find("for (int j = 0; j < ph[i].n; j++, x++) {", sa, sb)
        h += X(b11p, (a, b11.find("x->dur_ns =", a, sb)), "<code>set_windows</code>: size and passes per clock read (8 MiB / size, at least 1)")
        need(b11, (1, 200), "#define CHECK_BYTES")
        h += X(b11p, b11.c_func("tcall"), "<code>tcall</code>: from the window loop to <code>call</code>")
        ca, cb = b11.c_func("call")
        o0 = b11.find("case T_WRITE:", ca, cb)
        h += X(b11p, (ca, cb), "<code>call</code>: calls the loop function", omit=[(o0, b11.find("break;", b11.find("case T_COPY:", ca, cb), cb),
                                                                                    "the write and copy cases")])
        h += X(b11p, b11.c_func("now_ns"), "<code>now_ns</code>: the clock")
        h += X(b11p, b11.c_func("tcount"), "<code>tcount</code>: the counter read at a window boundary (step ZS)", open_=True)
        ca, cb = b11.c_func("count_open")
        a = b11.find("for (int e = 0; e < cfg.nev; e++) {", ca, cb)
        h += X(b11p, (a, b11.find("int fd = (int)syscall(SYS_perf_event_open", a, cb)),
               "<code>count_open</code>: one group of counters, user mode only")
        ea, eb = b11.c_func("emit_trial")
        a = b11.find("for (int k = 0; k < r->nw; k++) {", ea, eb)
        h += X(b11p, (a, b11.find("(long long)(x->t_end - t_base_ns));", a, eb)), "<code>emit_trial</code>: the W row of a window")
        a = b11.find("for (int k = 0; r->cnt && k < p->nwin; k++) {", ea, eb)
        h += X(b11p, (a, b11.find('printf("\\n");', a, eb) + 1), "<code>emit_trial</code>: the C row, the counter differences of a window")
        # one window, computed end to end from real rows
        zs = S(zs_csv)
        e = zs.find("-- step", 2)
        wl, cl = zs.find(r"^W,0,target,0,", 1, e, regex=True), zs.find(r"^C,0,0,", 1, e, regex=True)
        ml = zs.find(r"^M,events,", 1, e, regex=True)
        ev = [x.split("=")[0] for x in zs.L[ml - 1].split(",", 2)[2].split(";")]
        wq, cq = zs.L[wl - 1].split(","), zs.L[cl - 1].split(",")
        nbytes, dt = int(wq[6]), int(wq[8]) - int(wq[7])
        cyc, ref = int(cq[6 + ev.index("cpu_cycles")]), int(cq[6 + ev.index("l2d_cache_refill")])
        if cq[3] != cq[4]:
            die("the example window of step ZS was multiplexed")
        h += self.raw(zs_csv, (wl, wl), "one W row of step ZS: trial, phase, window, loop, pass bytes, bytes, start ns, end ns", open_=True)
        h += self.raw(zs_csv, (cl, cl), "its C row: trial, window, enabled ns, running ns, CPU ns, then one count per event", open_=True)
        h += ("<p class='note'><b>This window, computed here:</b> %s at %g MiB. Rate = %s bytes / %s ns = %s GB/s. Cycles per "
              "line = %s x 64 / %s = %s. r = %s x 64 / %s = %s. Event order: %s.</p>" % (
                  esc(wq[4]), int(wq[5]) / MIB, format(nbytes, ","), format(dt, ","), fnum(nbytes / float(dt), 2),
                  format(cyc, ","), format(nbytes, ","), fnum(cyc * 64.0 / nbytes, 3), format(ref, ","), format(nbytes, ","),
                  fnum(ref * 64.0 / nbytes, 3), ", ".join("<code>%s</code>" % esc(x) for x in ev)))

        h += "<h3 id='code-kern'>5.6 Excerpts: the loops (kernels)</h3>"
        off11 = os.path.join(X11, "crb-build-1", "offsets.tsv")

        def loop(kernel, ldp, vadd=0):
            """lines of the built loop; stops if it does not hold 'ldp' load pairs and 'vadd' vector adds"""
            _, start, fn = loop_mod64(off11, "bwx11", kernel)
            fa = l11.find("<%s>:" % fn)
            a = l11.find(r"^\s+%s:\t" % start, fa, regex=True)
            b = l11.find("\t%s <%s+" % (start, fn), a)
            body = l11.L[a - 1:b]
            n_ldp, n_add = sum("\tldp\tq" in x for x in body), sum("\tadd\tv" in x for x in body)
            if (n_ldp, n_add) != (ldp, vadd):
                die("the built loop of %s holds %d load pairs and %d vector adds, not %d and %d" % (kernel, n_ldp, n_add, ldp, vadd))
            return fa, a, b

        h += X(b11p, b11.macro("DEF_OLDREAD"), "old read, C source (macro <code>DEF_OLDREAD</code>): 16 sums", open_=True)
        _, a, b = loop("oldread", 4, 8)
        h += X(l11p, (a, b), "old read, the built loop: 4 load pairs (128 bytes) and 8 vector adds per turn", open_=True)
        ka, kb = b11.c_func("k_read")
        h += X(b11p, (ka, kb), "new read in C (<code>k_read</code>): 16 loads of 16 bytes, no other work",
               omit=[(b11.find("vld1q_u64(p + 4)", ka, kb), b11.find("vld1q_u64(p + 28)", ka, kb), "13 more loads")])
        _, a, b = loop("read", 8)
        h += X(l11p, (a, b), "new read in C, the built loop: 8 load pairs (256 bytes) per turn")
        ma, mb = b11.macro("DEF_ASMREAD")
        need(b11, (ma, mb), '".rept " #nops')
        h += X(b11p, (ma, mb), "the load-only loop in assembly (macro <code>DEF_ASMREAD</code>), with its nop count", open_=True)
        _, a, b = loop("asmread", 8)
        h += X(l11p, (a, b), "<code>asmread</code>, the built loop: 8 load pairs (256 bytes) per turn", open_=True)
        a = b11.find("DEF_ASMREAD(read_nop64, 64)")
        h += X(b11p, (a, b11.find("DEF_ASMREAD(read_nop128, 128)", a)), "the slowed loops of step ZN")
        _, a, b = loop("read_nop96", 8)
        n0 = l11.find("\tnop", a, b)
        nn = sum(1 for ln in l11.L[a - 1:b] if ln.rstrip().endswith("\tnop"))
        last = max(i + 1 for i in range(a - 1, b) if l11.L[i].rstrip().endswith("\tnop"))
        if nn != 96 or last - n0 + 1 != 96:
            die("read_nop96: the loop holds %d nop lines, 96 expected" % nn)
        h += X(l11p, (a, b), "<code>read_nop96</code>, the built loop: the same 8 load pairs, then 96 nop",
               omit=[(n0 + 2, last - 1, "%d more nop" % (last - 1 - (n0 + 2) + 1))])

        h += "<h3 id='code-h2'>5.7 Excerpts: the original benchmark and step H2</h3>"
        a = rh2.find("# ---- the order:")
        h += X(rh2p, (a, rh2.find(r"^done", a, regex=True)), "<code>run_h2.sh</code>: the order. 12 pairs per CPU, the first binary alternates")
        oa, ob = rh2.sh_func("one")
        a = rh2.find('setsid "$DIR/$bin"', oa, ob)
        h += X(rh2p, (a - 2, a), "<code>run_h2.sh</code>, in <code>one</code>: header line with the load, and the start with the original options", open_=True)
        wa, wb = bn.c_func("worker")
        a = bn.find("for (int k = 0; k < K_COUNT; k++) {", wa, wb)
        h += X(bnp, (a, wb), "original benchmark, <code>worker</code>: a repetition is 1 warm-up pass, then passes for 0.5 s", open_=True)
        pa, pb = bn.c_func("pass")
        h += X(bnp, (pa, bn.find("return cfg.bytes;", pa, pb)), "original benchmark, <code>pass</code>: the read case")
        h += X(bop, bo.c_func("k_read"), "old read in the older source (binary <code>bw_old</code>)")
        ma_, mb_ = bn.c_func("main")
        a = bn.find("double agg = (double)total / max_el / 1e9;", ma_, mb_)
        h += X(bnp, (a, bn.find("sum / cfg.threads);", a, mb_)), "original benchmark, <code>main</code>: the rate and the output row of a repetition")
        h2csv = os.path.join(self.results, self.rep.folders("H2", 1)[0], "H2.csv")
        h += self.raw(h2csv, (1, 7), "the rows of one process of step H2: header line, legend, 3 repetitions, best")

        h += "<h3 id='code-ana'>5.8 Excerpts: the analysis (rate, cycles per line, r, the rules)</h3>"
        h += "<p class='note'>The analysis programs are in folder A %s.</p>" % self.R("analysis")
        h += X(lvp, lv.py_def("rate", "Window"), "rate of a window, GB/s (bytes per ns)", open_=True)
        h += X(lvp, lv.py_def("per64"), "a count per 64-byte line", open_=True)
        h += X(f8p, f8.py_def("counter_proc"), "per process: the medians over the counted windows. Gives cycles per line and r", open_=True)
        a = f8.find("ZS_BASE, ZS_LO, ZS_HI, ZS_TOL =")
        h += X(f8p, (a, f8.py_def("zs_band")[1]), "step ZS: the constants of the band and the band", open_=True)
        za, zb = f8.py_def("rule_zs_cell")
        a = f8.find('res = {"sizes": {}', za, zb)
        h += X(f8p, (a, f8.find('res["exceeds"]', a, zb)), "step ZS: the rule for one cell", open_=True)
        h += X(f8p, f8.py_def("rule_zn_kernel"), "step ZN: the rule for one loop in one cell")
        sa, sb = f8.py_def("sup_gain")
        a = f8.find('if C and k8 and a and a["median"] is not None:', sa, sb)
        h += X(f8p, (a, f8.find('r["inside"] =', a, sb)), "supplementary: the gain predicted from two rates")
        h += X(a8p, a8.py_def("p1_cell"), "step S2: prediction P1 in one cell")
        ca, cb = a8.py_def("contrast")
        a = a8.find("v, med = [r['value'] for r in rows], out['median']", ca, cb)
        h += X(a8p, (a, cb), "step S2: when a contrast is &quot;repeatable&quot;")
        a = h2.py_def("gain")[0]
        h += X(h2p, (a, h2.py_def("classify")[1]), "step H2: gain of a pair and level of a repetition")
        a = f8.find("H2_LOW_MAX, H2_HIGH_MIN, H2_ORIGINAL_GAIN =")
        b = f8.py_def("h2_cpu_session")[1]
        h += X(f8p, (a, b), "step H2: limits, counts and gains per CPU and session")
        ha, hb = f8.py_def("h2_verdict")
        o0 = f8.find("miss = missing_sessions(", ha, hb)
        h += X(f8p, (ha, hb), "step H2: the verdict of one CPU", omit=[(o0, f8.find('", ".join(str(s) for s in miss)', o0, hb),
                                                                          "the case of a missing session")])
        return h

    # ================================================================== page
    def page(self):
        secs = [("top", self.sec_head()), ("s1", self.sec_goal()), ("s2", self.sec_answer()), ("s3", self.sec_path()),
                ("s4", self.sec_conclusion())]
        prose = "".join(s for _, s in secs)
        secs.append(("s5", self.sec_code()))
        refs = ("<h2 id='refs'>6. References</h2>%s<p class='note'>Chart colours: slots 1 and 2 of the palette of the dataviz "
                "skill %s. The validator script of the skill was not run for this page: the machine has no <code>node</code> "
                "program. Every series also has a legend entry or a direct label, so colour is never the only cue.</p>" % ("%s", self.R("palette")))
        refs = refs % self.R.html()
        body = "".join("<section id='sec-%s'>%s</section>" % (k, s) for k, s in secs) + "<section id='sec-refs'>%s</section>" % refs
        toc = ("<nav class='toc'><a href='#goal'>1. Goal</a><a href='#answer'>2. Answer in one picture</a><a href='#path'>3. How "
               "we got there</a><a href='#conclusion'>4. Conclusion</a><a href='#code'>5. Test code</a><a href='#refs'>6. "
               "References</a></nav>")
        body = body.replace("<details class='words'", toc + "<details class='words'", 1)
        count = lambda t: len(html_text(re.sub(r"<svg.*?</svg>|<pre>.*?</pre>", " ", t, flags=re.S)).split())
        self.words = count(prose)
        self.words_by = [(k, count(t)) for k, t in secs]
        lean = re.sub(r"<table.*?</table>|<p class='note'>.*?</p>|<ul class='note'>.*?</ul>|<div class='legend'>.*?</div>|"
                      r"<details class='words'.*?</details>|<details class='sup'.*?</details>", " ", prose, flags=re.S)
        self.words_lean = count(lean)
        return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<meta name='color-scheme' content='light'>"
                "<title>Why the new read loop gains so little at 8 MiB (easy read)</title><style>%s</style></head>"
                "<body><main>%s</main></body></html>\n" % (CSS, body))


def html_text(s):
    import html as _h
    return _h.unescape(re.sub(r"<[^>]+>", " ", s))


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
html{background:#f9f9f7}
body{margin:0;background:#f9f9f7;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif}
main{max-width:1120px;margin:0 auto;padding:20px 16px 70px;min-width:0}
h1{font-size:28px;line-height:1.25;margin:8px 0 6px}
h2{font-size:22px;margin:46px 0 12px;padding-top:14px;border-top:2px solid #e1e0d9}
h3{font-size:17px;margin:26px 0 8px}
p,li{max-width:860px}
li{margin:4px 0}
ul,ol{margin:6px 0 10px;padding-left:22px}
li>ul{margin:3px 0 5px;padding-left:20px}
a{color:#1c5cab}
code{font:13px ui-monospace,"DejaVu Sans Mono",monospace;background:#efeee9;padding:0 3px;border-radius:3px;overflow-wrap:anywhere}
.meta{color:#52514e;font-size:14px;max-width:none}
.short{background:#fff;border:1px solid #e1e0d9;border-left:5px solid #2a78d6;border-radius:6px;padding:4px 18px 8px;margin:14px 0}
.short h2{border:0;margin:8px 0 4px;padding:0;font-size:18px}
.short li{font-size:17px}
.toc{display:flex;flex-wrap:wrap;gap:6px 8px;margin:14px 0}
.toc a{font-size:14px;text-decoration:none;background:#fff;border:1px solid #e1e0d9;border-radius:14px;padding:3px 11px}
details.words{background:#fff;border:1px solid #e1e0d9;border-radius:6px;padding:6px 14px;margin:12px 0}
details.words summary{font-weight:600;cursor:pointer}
dl.wl{display:grid;grid-template-columns:minmax(120px,200px) minmax(0,1fr);gap:3px 14px;margin:8px 0 4px;font-size:14px}
dl.wl dt{font-weight:600}
dl.wl dd{margin:0}
.note{color:#52514e;font-size:13.5px;margin:6px 0}
ul.note{padding-left:20px}
.verdict{background:#fff;border:1px solid #e1e0d9;border-left:4px solid #898781;border-radius:4px;padding:6px 12px;max-width:none}
figure{margin:14px 0;padding:12px;background:#fcfcfb;border:1px solid #e1e0d9;border-radius:8px;min-width:0}
.figtitle{font-weight:600;margin-bottom:6px}
figcaption{margin-top:8px;max-width:860px}
.legend{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;color:#52514e;margin:4px 0 8px}
.legend span{display:inline-flex;align-items:center;gap:4px}
.sw{flex:none}
.panels{display:flex;flex-wrap:wrap;gap:14px}
.panel{flex:1 1 400px;min-width:0;max-width:540px}
.panels.p3 .panel{flex:1 1 320px;max-width:420px}
.chart{display:block;width:100%;height:auto;font-family:system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif}
.chart text{fill:#0b0b0b}
.chart text.ax{fill:#52514e}
.chart text.ttl,.chart text.b{font-weight:600}
.chart text.fd{fill:#52514e}
.chart .frame{fill:#fcfcfb;stroke:#c3c2b7;stroke-width:1}
.chart .grid{stroke:#e1e0d9;stroke-width:1}
.chart .tick{stroke:#c3c2b7;stroke-width:1}
.wide .chart{max-width:1088px}
.narrow{display:none}
.tbl{overflow-x:auto;max-width:100%;margin:10px 0;border:1px solid #e1e0d9;border-radius:6px;background:#fff}
table{border-collapse:collapse;font-size:13.5px;width:100%}
.tcap{font-weight:600;font-size:14.5px;margin:14px 0 -4px}
th,td{padding:5px 8px;border-bottom:1px solid #efeee9;text-align:left;vertical-align:top}
thead th{background:#f3f2ee;font-weight:600;vertical-align:bottom}
tbody th{font-weight:500;white-space:nowrap}
table.wrap tbody th,table.fn tbody th{white-space:normal}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.num.list{white-space:normal}
td.calc{font-style:italic;color:#333}
td.na{text-align:right;color:#898781}
.step{background:#fff;border:1px solid #e1e0d9;border-radius:8px;padding:4px 16px 12px;margin:22px 0}
.step h3{margin-top:12px}
dl.qa{display:grid;grid-template-columns:170px minmax(0,1fr);gap:6px 16px;margin:8px 0 0}
dl.qa dt{font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#52514e;padding-top:3px}
dl.qa dt span{display:block;text-transform:none;letter-spacing:0;font-weight:400}
dl.qa dd{margin:0;min-width:0}
dl.qa dd>ul{margin-top:0}
dl.qa .full{grid-column:1/-1}
dl.qa dd.so{font-weight:500;background:#eaf2fc;border-radius:6px;padding:8px 12px}
dl.qa dt.so{padding-top:10px}
ul.dead li{color:#3a3936}
ul.check{list-style:none;padding-left:0}
ul.check>li{background:#fff;border:1px solid #e1e0d9;border-radius:6px;padding:8px 14px;margin:8px 0;max-width:none}
.st{display:inline-block;background:#f3f2ee;border:1px solid #c3c2b7;color:#0b0b0b;border-radius:10px;font-size:12px;font-weight:700;padding:0 8px;margin-right:6px}
h4{font-size:15.5px;margin:18px 0 6px}
.bridge{background:#f3f2ee;border-radius:6px;padding:8px 12px;max-width:none}
details.sup{margin:12px 0;border:1px solid #e1e0d9;border-radius:6px;background:#fff;padding:0 12px;min-width:0}
details.sup summary{cursor:pointer;padding:7px 0;font-size:14.5px;font-weight:600}
details.sup figure{border:0;padding:0;background:none}
.gapx{color:#8a4b00;font-style:italic}
details.code{margin:8px 0;border:1px solid #e1e0d9;border-radius:6px;background:#fff;min-width:0}
details.code summary{cursor:pointer;padding:6px 10px;font-size:14px}
details.code pre{margin:0;padding:8px 10px;border-top:1px solid #efeee9;overflow-x:auto;max-width:100%;font:12px/1.45 ui-monospace,"DejaVu Sans Mono",monospace;background:#fbfbf9;tab-size:4}
details.code .note{padding:0 10px 6px}
pre .ln{color:#898781;user-select:none}
pre .gap{color:#8a4b00;font-style:italic}
.chain{font-size:14px}
.chain .lay{border:1px solid #c3c2b7;border-radius:6px;background:#fff;padding:6px 12px}
.chain .lay.hot{border-color:#2a78d6;border-width:1.5px}
.chain .where{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#52514e}
.chain ul{margin:2px 0;padding-left:18px}
.chain li{max-width:none;margin:2px 0}
.chain .down{padding:2px 14px;color:#52514e;font-size:13px}
table.fn td.loc{font-size:12px;min-width:210px}
table.fn tr.grp th{background:#eaf2fc;font-weight:700}
table.fn tbody th{font-weight:500;min-width:150px}
.tag{display:inline-block;font-size:11.5px;color:#52514e;border:1px solid #d5d4cc;border-radius:8px;padding:0 6px;white-space:nowrap}
table.wrap td.txt{min-width:150px}
.refs{padding-left:18px}
.refs li{max-width:1080px;overflow-wrap:anywhere;font-size:14px}
@media (max-width:700px){
 main{padding:14px 16px 50px}
 h1{font-size:23px} h2{font-size:20px}
 .wide{display:none}.narrow{display:block}
 .step{padding:0;border:0;background:none;border-top:1px solid #e1e0d9;border-radius:0}
 figure{padding:8px 3px}
 dl.qa{grid-template-columns:minmax(0,1fr);gap:2px}
 dl.qa dt{margin-top:10px}
 dl.wl{grid-template-columns:minmax(0,1fr);gap:0}
 dl.wl dt{margin-top:6px}
 table.fn,table.fn tbody,table.fn tr,table.fn td,table.fn th{display:block;width:auto;min-width:0}
 table.fn thead{display:none}
 table.fn tr{border-bottom:1px solid #e1e0d9;padding:4px 0}
 table.fn td,table.fn th{border:0;padding:1px 8px}
 table.fn td.num{text-align:left;color:#898781;font-size:12px}
 table.fn td.loc{min-width:0}
}
"""


def build(json_path, date=None):
    with open(json_path) as f:
        J = json.load(f)
    e = Easy(J, date or datetime.date.today().isoformat())
    return e.page(), e


def main(argv=None):
    ap = argparse.ArgumentParser(description="Easy-read HTML page of the tackle-8mb investigation.")
    ap.add_argument("--json", default=os.path.join(HERE, "final8.json"), help="final8.json (default %(default)s)")
    ap.add_argument("--date", default=None, help="page date (default today)")
    ap.add_argument("-o", "--out", default=os.path.join(N_DIR, "tackle-8mb-report-easy-read.html"), help="output file (default %(default)s)")
    a = ap.parse_args(argv)
    page, e = build(a.json, a.date)
    for bad in ("http://", "https://", "<script", "src=", "@import", "url("):
        if bad in page:
            die("the page holds %r: it must have no outside reference and no script" % bad)
    m = re.search(r"(?<![\d.])\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?![\d.])", page)
    if m:
        die("the page holds %r, which looks like a network address" % m.group(0))
    with open(a.out, "w") as f:
        f.write(page)
    print("wrote %s (%d bytes)" % (a.out, len(page.encode())))
    print("figures %d, diagrams 2, data tables %d, code tables %d (function rows %d), excerpts %d (%d lines shown), "
          "words in sections 0 to 4: %d (without tables, notes, legends and the word list: %d)" % (
              e.n_fig, e.n_tab, e.n_codetab, e.n_fnrows, e.n_exc, e.exc_lines, e.words, e.words_lean))
    print("words by section: " + ", ".join("%s %d" % kv for kv in e.words_by))
    return 0


if __name__ == "__main__":
    sys.exit(main())
