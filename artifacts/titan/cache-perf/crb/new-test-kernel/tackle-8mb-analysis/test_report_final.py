#!/usr/bin/env python3
"""test_report_final.py - checks of report_final.py.

Usage: test_report_final.py [--tmp DIR] [--json final8.json] [--no-chrome]
Prints one line per check (PASS, FAIL or SKIP). Exit status 0 only if no check failed.

What is checked, and why it matters:
  1. The generator runs on the current final8.json, on a copy without any session 2 entry, and on a copy
     in which session 2 repeats session 1. The report must exist before the last session is measured and
     must change by itself when the data arrives.
  2. Every number in the tables of sections 2 to 6 exists in final8.json with the printed rounding. A
     number that the page computes (a "calc" cell) is recomputed here from its arguments, and every
     argument must exist in final8.json. A typed or stale number would fail this check.
  3. The checker of item 2 is itself tested: a changed number must be reported.
  4. The page loads nothing from outside (no URL, no link, no script source).
  5. With a headless Chrome: at 1200 px and at 390 px the page does not scroll sideways, no chart text
     leaves its chart, crosses a plot frame or covers another text, and chart text stays readable.
     Skipped with a SKIP line if Chrome cannot run.
  6. Statements about a result follow the data. A copy of final8.json in which two failing predictions
     hold must not print the sentences about the failures. A reader would otherwise see a verdict that
     the data no longer gives.
  7. A chart whose value axis does not start at 0 says so on the chart or in the note under it.
  8. The supplementary evaluations (block 16 of final8.txt) are labelled as defined after the data was
     seen, stand after the recorded verdict, print the lines of final8.json, and their sentences follow
     the data. A reader must be able to tell a recorded verdict from a later evaluation.
"""
import argparse
import copy
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A)
import report_final as RF  # noqa: E402

FAILS, SKIPS, NCHECK = [], [], [0]
CLOCK_GHZ = 2.8
# an independent copy of the formulas of the calc cells
CALC = {
    "gain": lambda a, b: 100.0 * (a / b - 1.0),
    "diff": lambda a, b: a - b,
    "cyc": lambda rate: CLOCK_GHZ * 64.0 / rate,
    "line": lambda i, s, r: i + s * r,
    "linegap": lambda old, i, s, r: old - (i + s * r),
    "linegain": lambda old, i, s, r: 100.0 * (old / (i + s * r) - 1.0),
    "pgain": lambda s, c: 100.0 * (s / min(c, s) - 1.0),
    "share": lambda g1, gp, gm: 100.0 * (g1 - gp) / (g1 - gm),
}


def check(name, ok, detail=""):
    NCHECK[0] += 1
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:600] + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def skip(name, why):
    print("SKIP  %s  [%s]" % (name, why))
    SKIPS.append(name)


# ------------------------------------------------------------------------------------------ JSON variants
def strip_session2(J):
    """a copy of final8.json without any session 2 entry"""
    def walk(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k.endswith("/s2"):
                    continue
                if k == "s2":
                    out[k] = type(v)() if isinstance(v, (list, dict)) else "session 2 missing"
                    continue
                out[k] = walk(v)
            return out
        if isinstance(o, list):
            return [walk(x) for x in o if not (isinstance(x, dict) and x.get("session") == 2)]
        return o
    return walk(copy.deepcopy(J))


def mirror_session2(J):
    """a copy of final8.json in which every missing session 2 entry repeats session 1"""
    def as2(o):
        o = copy.deepcopy(o)

        def setses(x):
            if isinstance(x, dict):
                if x.get("session") == 1:
                    x["session"] = 2
                for v in x.values():
                    setses(v)
            elif isinstance(x, list):
                for v in x:
                    setses(v)
        setses(o)
        return o

    def walk(o):
        if isinstance(o, dict):
            for k in list(o.keys()):
                walk(o[k])
            for k in list(o.keys()):
                if k.endswith("/s1") and not o.get(k[:-1] + "2"):
                    o[k[:-1] + "2"] = as2(o[k])
                if k == "s1" and not o.get("s2"):
                    o["s2"] = as2(o[k])
        elif isinstance(o, list):
            for x in o:
                walk(x)
            rows = [x for x in o if isinstance(x, dict) and "session" in x]
            if rows:
                keyf = lambda x: json.dumps({k: v for k, v in x.items() if isinstance(v, (str, int)) and k not in (
                    "session", "folder", "processes", "n", "idx", "tag", "win_addr")}, sort_keys=True)
                dead = [x for x in rows if x["session"] == 2 and x.get("folder", 1) is None]
                for x in dead:
                    o.remove(x)
                have2 = {keyf(x) for x in o if isinstance(x, dict) and x.get("session") == 2}
                for x in [x for x in rows if x["session"] == 1]:
                    if keyf(x) not in have2:
                        o.append(as2(x))
    J = copy.deepcopy(J)
    walk(J)
    return J


# ------------------------------------------------------------------------------------------ HTML tables
class Cells(HTMLParser):
    """collects the td cells of the page with their section id"""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.sec = None
        self.cells = []        # (section, class, data-calc, data-args, text)
        self.cur = None
        self.attrs_all = []    # (tag, attrs) of every element, for the URL check

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.attrs_all.append((tag, d))
        if tag == "section":
            self.sec = d.get("id")
        if tag == "td":
            self.cur = [self.sec, d.get("class", ""), d.get("data-calc"), d.get("data-args"), ""]

    def handle_data(self, data):
        if self.cur is not None:
            self.cur[4] += data

    def handle_endtag(self, tag):
        if tag == "td" and self.cur is not None:
            self.cells.append(tuple(self.cur))
            self.cur = None


def json_numbers(J):
    out = []

    def walk(o):
        if isinstance(o, bool) or o is None:
            return
        if isinstance(o, (int, float)):
            out.append(float(o))
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(J)
    return out


NUM = re.compile(r"^-?\d+(\.\d+)?$")


def check_numbers(page, J, sections=("sec2", "sec3", "sec4", "sec5", "sec6")):
    """-> (count of V numbers, count of calc cells, [problems])"""
    nums = json_numbers(J)
    exact = set(nums)
    by_nd = {}

    def known(tok):
        nd = len(tok.split(".")[1]) if "." in tok else 0
        if nd not in by_nd:
            by_nd[nd] = {"%.*f" % (nd, v) for v in nums}
        return tok in by_nd[nd]

    p = Cells()
    p.feed(page)
    nv = nc = 0
    bad = []
    for sec, cls, kind, args, text in p.cells:
        if sec not in sections:
            continue
        c = cls.split()
        if "num" not in c:
            continue
        text = text.strip()
        if "calc" in c:
            nc += 1
            try:
                a = [float(x) for x in args.split(",")]
            except (AttributeError, ValueError):
                bad.append("%s: calc cell without arguments: %r" % (sec, text))
                continue
            miss = [x for x in a if x not in exact]
            if miss:
                bad.append("%s: calc argument not in final8.json: %r (cell %r)" % (sec, miss, text))
                continue
            tok = text.replace(" est.", "")
            nd = len(tok.split(".")[1]) if "." in tok else 0
            want = "%.*f" % (nd, CALC[kind](*a))
            if tok != want:
                bad.append("%s: calc cell %s%r prints %r, recomputed %r" % (sec, kind, a, tok, want))
            continue
        for tok in text.split():
            if not NUM.match(tok):
                bad.append("%s: not a number in a number cell: %r" % (sec, text))
                continue
            nv += 1
            if not known(tok):
                bad.append("%s: %r is not a number of final8.json at this rounding" % (sec, tok))
    return nv, nc, bad


def section_text(page, sec):
    m = re.search(r"<section id='%s'>(.*?)</section>" % sec, page, re.S)
    return m.group(1) if m else ""


# ------------------------------------------------------------------------------------------ the checks
def test_runs(J, json_path, tmp):
    out = os.path.join(tmp, "cli.html")
    r = subprocess.run([sys.executable, os.path.join(A, "report_final.py"), "--json", json_path, "-o", out],
                       capture_output=True, text=True)
    check("command line run on the current final8.json ends with status 0", r.returncode == 0, r.stderr[-400:])
    page = open(out).read() if os.path.exists(out) else ""
    check("the page has sections 1 to 10 in order",
          re.findall(r"<section id='(sec\d+)'>", page) == ["sec%d" % i for i in range(1, 11)])
    short = re.search(r"<div class='short'><h2>Short version</h2><p>(.*?)</p>", page, re.S)
    n_sent = len(re.findall(r"[.?!](?=\s+[A-Z]|\s*$)", re.sub(r"<[^>]+>", "", short.group(1)))) if short else 99
    check("the page opens with a Short version of at most three sentences", short is not None and n_sent <= 3, n_sent)
    check("the page has a 'Words used here' table", "<h2>Words used here</h2><div class='tbl'>" in page)
    check("the page declares the light colour scheme only", "prefers-color-scheme" not in page and "color-scheme:light" in page)
    miss_now = [k for k in J["folders"] if k.endswith("/s1") and k[:-1] + "2" not in J["folders"]
                and k.split("/")[0] not in RF.SESSION1_ONLY]
    if miss_now:
        check("current data: 'session 2 missing' is printed (steps without session 2: %d)" % len(miss_now),
              page.count("class='miss'") > 0 and RF.MISSING in page)
        for st in sorted(k.split("/")[0] for k in miss_now):
            check("current data: the status line names step %s" % st,
                  "<code>%s</code>" % st in (re.search(r"<p class='warn'>(.*?)</p>", page, re.S) or [""])[0])
    else:
        check("current data: both sessions exist, so no 'session 2 missing' cell in sections 2 to 8",
              all("class='miss'" not in section_text(page, "sec%d" % i) for i in range(2, 9)))
    fig = len(re.findall(r"<figure>", page))
    cap = len(re.findall(r"<figcaption><b>Takeaway:</b>", page))
    check("every figure has a takeaway line (figures: %d)" % fig, fig >= 8 and fig == cap, (fig, cap))
    check("every chart has an axis title or a panel title with a unit or a name",
          all("class='ax'" in s for s in re.findall(r"<svg class='chart'.*?</svg>", page, re.S)))
    return page


def test_without_session2(J, tmp):
    S = strip_session2(J)
    path = os.path.join(tmp, "no-s2.json")
    json.dump(S, open(path, "w"))
    try:
        page, rep = RF.build(path)
        ok = True
        err = ""
    except Exception as e:  # the check is "no crash"
        page, ok, err = "", False, repr(e)
    check("the generator runs on a copy without any session 2 entry", ok, err)
    check("without session 2: the text 'session 2 missing' appears", RF.MISSING in page)
    for i in range(2, 9):
        check("without session 2: section %d prints 'session 2 missing'" % i,
              "class='miss'" in section_text(page, "sec%d" % i))
    nv, nc, bad = check_numbers(page, S)
    check("without session 2: every table number of sections 2 to 6 exists in that copy (%d numbers, %d calc cells)" % (nv, nc),
          nv > 200 and not bad, bad[:5])
    return page


def test_with_both_sessions(J, tmp):
    M = mirror_session2(J)
    path = os.path.join(tmp, "both.json")
    json.dump(M, open(path, "w"))
    try:
        page, rep = RF.build(path)
        ok, err = True, ""
    except Exception as e:
        page, ok, err, rep = "", False, repr(e), None
    check("the generator runs on a copy in which session 2 repeats session 1", ok, err)
    check("with both sessions: the status line says that both sessions exist", "<p class='ok'>" in page and "<p class='warn'>" not in page)
    for i in range(2, 9):
        check("with both sessions: section %d has no 'session 2 missing' cell or line" % i,
              "class='miss'" not in section_text(page, "sec%d" % i),
              re.findall(r"<[a-z]+ class='miss'[^>]*>[^<]*", section_text(page, "sec%d" % i))[:3])
    if rep is not None:
        check("with both sessions: no step is reported as missing", rep.missing_steps() == [], rep.missing_steps())
    nv, nc, bad = check_numbers(page, M)
    check("with both sessions: every table number of sections 2 to 6 exists in that copy (%d numbers, %d calc cells)" % (nv, nc),
          nv > 400 and not bad, bad[:5])


def test_numbers(page, J):
    nv, nc, bad = check_numbers(page, J)
    check("every table number of sections 2 to 6 exists in final8.json at the printed rounding (%d numbers)" % nv,
          nv > 400 and not [b for b in bad if "calc" not in b], [b for b in bad if "calc" not in b][:6])
    check("every calc cell of sections 2 to 6 is recomputed from numbers of final8.json (%d cells)" % nc,
          nc > 50 and not [b for b in bad if "calc" in b], [b for b in bad if "calc" in b][:6])
    # the checker must be able to fail
    m = re.search(r"<td class='num'>(-?\d+\.\d\d)</td>", section_text(page, "sec3"))
    broken = page.replace("<section id='sec3'>", "<section id='sec3'><table><tr><td class='num'>12345.67</td></tr></table>", 1)
    check("a number that is not in final8.json is reported by the checker", m is not None and len(check_numbers(broken, J)[2]) == len(bad) + 1)
    m = re.search(r"<td class='num calc' data-calc='gain' data-args='([^']+)'>(-?\d+\.\d+)</td>", page)
    if m:
        wrong = "%.*f" % (len(m.group(2).split(".")[1]), float(m.group(2)) + 1.0)
        broken = page.replace(m.group(0), m.group(0).replace(">" + m.group(2) + "<", ">" + wrong + "<"), 1)
        check("a calc cell with a wrong value is reported by the checker", len(check_numbers(broken, J)[2]) >= len(bad) + 1)
        a0 = m.group(1).split(",")[0]
        broken = page.replace(m.group(0), m.group(0).replace(a0, repr(float(a0) + 0.123456789)), 1)
        check("a calc cell with an argument that is not in final8.json is reported", len(check_numbers(broken, J)[2]) >= len(bad) + 1)
    else:
        check("the page has a calc cell of kind 'gain' to test the checker with", False)
    # a few known values of session 1 (final8.txt, items 2 and 13)
    s3 = re.sub(r"<[^>]+>", " ", section_text(page, "sec3"))
    check("table 3 holds the 1 MiB gain of CPU 2 session 1 (27.03 %)", " 27.03 " in s3)
    for key in sorted(J.get("ZS", {}).get("rule", {})):
        c = J["ZS"]["rule"][key]
        want = "%.3f + %.3f" % (c["intercept"], c["slope"])
        check("section 2 states the fitted line of %s (%s x r) from final8.json" % (key, want), want in section_text(page, "sec2"))


def test_verdict_texts(page, J):
    plain = html.unescape(page)
    for c in J.get("claims", []):
        check("section 8 prints the overall verdict of '%s' as final8.json gives it" % c["id"], c["overall"] in plain)
    for key, c in sorted(J.get("prefetch", {}).get("rule3", {}).items()):
        check("section 6 prints the rule 3 verdict of %s literally" % key, c["verdict"] in plain)
    for key, c in sorted(J.get("YL", {}).get("verdict", {}).items()):
        check("section 7 prints the literal rule 1 verdict of %s (%s)" % (key, c["verdict"]),
              "literal verdict: <b>%s</b>" % c["verdict"] in section_text(page, "sec7"))
    check("section 6 labels the evict test 'Insufficient data'", "Insufficient data" in section_text(page, "sec6"))
    check("section 8 labels the open points 'Insufficient data'", "Insufficient data" in section_text(page, "sec8"))
    x = J.get("families", {})
    for k, v in x.get("XN", {}).get("overall", {}).items():
        check("section 4 prints the rule 6 verdict of %s" % k, v in html.unescape(section_text(page, "sec4")))
    for k, v in x.get("ZN", {}).get("overall", {}).items():
        check("section 4 prints the rule 2 verdict of %s" % k, v in html.unescape(section_text(page, "sec4")))


def test_claims_follow_data(page, J, tmp):
    """the sentences about failed predictions and about confirmation must come from the data"""
    s4 = html.unescape(section_text(page, "sec4"))
    xn = J.get("families", {}).get("XN", {}).get("rule6", {})
    zn = J.get("families", {}).get("ZN", {}).get("rule2", {})
    fail_a = sorted({k for c in xn.values() for k, d in c["kernels"].items() if d["a"] is False})
    fail_p = sorted({k for c in zn.values() for k, d in c["kernels"].items() if d["prediction_holds"] is False})
    for k in fail_a:
        check("section 4 names the kernel %s whose part (a) fails in the data" % k, "Part (a) fails for <code>%s</code>" % k in s4)
    for k in fail_p:
        check("section 4 names the kernel %s whose rule 2 prediction fails in the data" % k,
              "The prediction fails for <code>%s</code>" % k in s4)
    M = copy.deepcopy(J)
    for c in M.get("families", {}).get("XN", {}).get("rule6", {}).values():
        for d in c["kernels"].values():
            if d["a"] is False:
                d["a"] = True
    for c in M.get("families", {}).get("ZN", {}).get("rule2", {}).values():
        for d in c["kernels"].values():
            d["prediction_holds"] = True
    path = os.path.join(tmp, "holds.json")
    json.dump(M, open(path, "w"))
    p2, _ = RF.build(path)
    t4 = section_text(p2, "sec4")
    check("a copy in which every prediction of section 4 holds prints no sentence about a failed prediction",
          "Part (a) fails for" not in t4 and "The prediction fails for" not in t4)
    short = re.search(r"<div class='short'>(.*?)</div>", page, re.S).group(1)
    zs2 = bool(J.get("folders", {}).get("ZS/s2"))
    check("the Short version says 'not confirmed' for the cost rule exactly when step ZS has one session",
          ("rests on one session and is not confirmed" in short) == (not zs2))
    b2, _ = RF.build(os.path.join(tmp, "both.json"))
    check("with both sessions the Short version does not say 'one session'",
          "rests on one session" not in re.search(r"<div class='short'>(.*?)</div>", b2, re.S).group(1))
    figs = re.findall(r"<figure>(.*?)</figure>", page, re.S)
    # figure 7 is left out: its only value axis (the window number) starts at 0
    bad = [re.search(r"Figure \d+", f).group(0) for f in figs
           if not re.search(r"Figure 7\.", f)
           and not re.search(r"axis starts at|does not start at 0|\(from \d+\)", re.sub(r"<title>.*?</title>", "", f))]
    check("every figure with a value axis that does not start at 0 says so (figures checked: %d)" % (len(figs) - 1), not bad, bad)


def test_supplementary(page, J, tmp):
    """the supplementary evaluations (block 16 of final8.txt): labelled, beside the recorded verdict, from the data"""
    S = J.get("supplementary")
    if not S:
        check("final8.json has the supplementary block", False)
        return
    plain = html.unescape(page)
    s4, s6, s7 = [html.unescape(section_text(page, "sec%d" % i)) for i in (4, 6, 7)]
    lead = "Supplementary evaluation, defined after the data was seen"
    check("sections 4, 6 and 7 label each added evaluation as supplementary and defined after the data was seen",
          s4.count(lead) == 2 and s6.count(lead) == 1 and s7.count(lead) == 1, (s4.count(lead), s6.count(lead), s7.count(lead)))
    for num, sec in (("6a", s4), ("6b", s4), ("11a", s6), ("16a", s7), ("16b", s7)):
        check("the caption of table %s carries the label" % num,
              ("<caption>Table %s. Supplementary, defined after the data was seen." % num) in sec)
    cap = lambda t: t[0].upper() + t[1:]
    # section 7.3: recorded verdict first, then the supplementary lines of final8.json
    rec = "Rule 2 overall, as recorded: %s." % J["YP"]["overall"]
    check("section 7.3 keeps the recorded verdict of rule 2, and the supplementary part comes after it",
          rec in s7 and s7.index(rec) < s7.index(lead))
    Y = S["yp_round1"]
    have = sorted({c["session"] for c in Y["cells"]})
    for kind in ("up", "fall"):
        st = Y["summary_text"][kind]
        for ses in have:
            check("section 7.3 prints the %s summary of session %d as final8.json gives it" % (kind, ses),
                  cap(st["s%d" % ses]) + "." in s7)
        if have == [1, 2]:
            check("section 7.3 prints the %s summary of both sessions as final8.json gives it" % kind,
                  cap(st["overall"]) + "." in s7 and "both sessions" in st["overall"])
    m = re.search(r"<caption>Table 16a\..*?</table>.*?<caption>Table 16b\..*?</table>", section_text(page, "sec7"), re.S)
    sub = "<section id='sec7'>" + (m.group(0) if m else "") + "</section>"
    nv, nc, bad = check_numbers(sub, J, sections=("sec7",))
    check("every number of tables 16a and 16b exists in final8.json at the printed rounding (%d numbers)" % nv,
          m is not None and nv > 100 and not bad, bad[:5])
    broken = sub.replace("<td class='num'>", "<td class='num'>987654.3 ", 1)
    check("a changed number in table 16a is reported", len(check_numbers(broken, J, sections=("sec7",))[2]) == 1)
    # figure 7: the hollow marks are the round 1 windows moved by pad / 80, the same in every panel
    fig7 = next((f for f in re.findall(r"<figure>(.*?)</figure>", page, re.S) if "Figure 7." in f), "")
    pred = {x["pad"]: x["windows"] for x in Y["predicted"] if x["kind"] == "up"}
    npan = len({(p["cpu"], p["session"]) for p in J["YP"]["processes"]})
    hollow = re.findall(r"<circle cx='([0-9.]+)' cy='[0-9.]+' r='6.5' fill='%s' stroke='%s'" % (RF.C_SURF, RF.C_PRED), fig7)
    check("figure 7 draws one hollow mark per predicted window of the round 1 series (%d marks in %d panels)" % (
        len(hollow), npan), npan > 0 and len(hollow) == npan * sum(len(v) for v in pred.values()), len(hollow))
    check("figure 7 names the round 1 windows as the source of the hollow marks and says that the choice is supplementary",
          ", ".join("%d" % u for u in Y["reference"]["up"]["series"]) in html.unescape(fig7) and
          "chosen after the data was seen" in fig7 and "Verdict of rule 2 as recorded" in fig7)
    # section 6.1
    P = S["prefetch_1M"]
    rec = "Overall, as recorded:</b> %s" % J["prefetch"]["overall"]
    check("section 6.1 keeps the recorded verdict of rule 3, and the supplementary part comes after it",
          rec in s6 and s6.index(rec) < s6.index(lead))
    for size in ("1M", "8M"):
        check("section 6.1 prints the %s line of the prefetch family as final8.json gives it" % size,
              "Result: %s." % P["summary_text"][size] in s6)
    check("section 6.1 prints the 32 KiB line of the prefetch family, and reads it as a limit only if every cell is lower",
          "Result: %s." % P["summary_text"]["32K"] in s6 and
          ("can therefore come from the added instruction" in s6) == (P["at_32K"]["cells_lower"] == P["at_32K"]["cells"]))
    # section 4
    n32 = [r for r in S["old_without_adds"]["rows"] if r["size"] == "32K" and r["ratio"] is not None]
    t4 = re.sub(r"<[^>]+>", " ", section_text(page, "sec4"))
    check("table 6a holds the 32 KiB ratio of every cell (%d cells)" % len(n32),
          n32 and all((" %.3f " % r["ratio"]) in t4 for r in n32))
    G = S["gain_from_two_rates"]
    ev = [r for r in G["rows"] if r["inside"] is not None]
    check("table 6b has one 'inside' or 'outside' cell per evaluated cell (%d), and the count line follows the rows" % len(ev),
          s4.count("<td class='txt'>inside</td>") == sum(1 for r in ev if r["inside"]) and
          s4.count("<td class='txt'>outside</td>") == sum(1 for r in ev if not r["inside"]) and
          ("inside the predicted range in %d of the %d cells that exist" % (sum(1 for r in ev if r["inside"]), len(ev))) in s4)
    # statements follow the data
    M = copy.deepcopy(J)
    for x in M["supplementary"]["old_without_adds"]["summary"]:
        x["ratio_min"] = 1.0
    for x in M["supplementary"]["prefetch_1M"]["summary"]:
        x["cells_lower"] = 0
    M["supplementary"]["prefetch_1M"]["at_32K"]["cells_lower"] = 0
    flip = next((r for r in M["supplementary"]["gain_from_two_rates"]["rows"] if r["inside"]), None)
    if flip:
        flip["inside"] = False
    path = os.path.join(tmp, "sup-changed.json")
    json.dump(M, open(path, "w"))
    p2, _ = RF.build(path)
    a4, a6 = section_text(p2, "sec4"), section_text(p2, "sec6")
    check("with a ratio of 1.0 at 32 KiB section 4 does not say that the adds set the cost of old read",
          "set the cost of old read.</li>" in section_text(page, "sec4") and "So the adds, and not the loads" not in a4)
    check("with no slower prefetch cell at 1 MiB section 6 does not say that the removal of the misses does not raise "
          "the rate, and with no slower cell at 32 KiB it does not name the added instruction as a possible cause",
          "does not raise the rate" in section_text(page, "sec6") and "does not raise the rate" not in a6 and
          "can therefore come from the added instruction" not in a6)
    check("section 6.1 does not state more about H1b than its recorded verdict (no 'does not fit')",
          "does not fit hypothesis H1b" not in section_text(page, "sec6"))
    if flip:
        check("a gain row that lies outside its range is printed as 'outside' and named in the count line",
              a4.count("<td class='txt'>outside</td>") == sum(1 for r in ev if not r["inside"]) + 1 and
              "(outside: %s on CPU %d in session %d" % (flip["kernel"], flip["cpu"], flip["session"]) in a4)
    # every row of a supplementary table spans as many columns as its header, also when a session is missing
    def ragged(pg):
        bad = []
        for t in re.findall(r"<table[^>]*>(.*?)</table>", pg, re.S):
            cap = re.search(r"<caption>(Table \w+)\. Supplementary", t)
            if not cap:
                continue
            ncol = len(re.findall(r"<th scope='col'", t))
            for row in re.findall(r"<tr>(.*?)</tr>", t.split("<tbody>", 1)[1], re.S):
                n = sum(int(c or 1) for c in re.findall(r"<t[dh]\b(?:[^>]*?colspan='(\d+)')?[^>]*>", row))
                if n != ncol:
                    bad.append((cap.group(1), ncol, n))
        return bad
    M = copy.deepcopy(J)
    SM = M["supplementary"]
    SM["yp_round1"]["cells"] = [c for c in SM["yp_round1"]["cells"] if c["session"] != 2]
    SM["old_without_adds"]["rows"] = [r for r in SM["old_without_adds"]["rows"] if r["session"] != 2]
    SM["prefetch_1M"]["rows"] = [r for r in SM["prefetch_1M"]["rows"] if r["session"] != 2]
    SM["gain_from_two_rates"]["rows"] = [r for r in SM["gain_from_two_rates"]["rows"] if r["session"] != 2]
    path = os.path.join(tmp, "sup-s1.json")
    json.dump(M, open(path, "w"))
    p4, _ = RF.build(path)
    check("every row of the 5 supplementary tables has as many columns as the header, with and without session 2 rows",
          page.count(". Supplementary, defined after the data was seen.") >= 5 and not ragged(page) and not ragged(p4)
          and p4.count("session 2 missing") > page.count("session 2 missing"), (ragged(page), ragged(p4)))
    M = copy.deepcopy(J)
    del M["supplementary"]
    path = os.path.join(tmp, "no-sup.json")
    json.dump(M, open(path, "w"))
    try:
        p3, _ = RF.build(path)
        ok, err = True, ""
    except Exception as e:
        p3, ok, err = "", False, repr(e)
    check("the generator runs on a final8.json without the supplementary block, and figure 7 then predicts from pad 0",
          ok and "predicted: the pad 0 series moved earlier" in p3 and "<caption>Table 16a." not in p3, err)


def test_no_external(page):
    p = Cells()
    p.feed(page)
    check("the page names no http, https, ftp or protocol-relative URL", not re.search(r"(?:https?:|ftp:)?//[A-Za-z0-9]", page),
          re.findall(r".{30}(?:https?:|ftp:)?//[A-Za-z0-9].{20}", page)[:3])
    bad = [(t, k) for t, d in p.attrs_all for k in d if k in ("src", "href", "xlink:href", "srcset", "data", "action", "poster")]
    check("no element has a src, href or similar attribute", not bad, bad[:5])
    tags = {t for t, d in p.attrs_all}
    check("no script, link, iframe, img, object, embed or font element", not (tags & {"script", "link", "iframe", "img", "object", "embed", "image", "use", "base"}),
          sorted(tags & {"script", "link", "iframe", "img", "object", "embed", "image", "use", "base"}))
    check("the style sheet has no url() and no @import", "url(" not in page and "@import" not in page)


GEOM_JS = """<script>(function(){
var out={w:window.innerWidth,sw:document.documentElement.scrollWidth,charts:[],tbl:[]};
document.querySelectorAll('svg.chart').forEach(function(s){
 var sb=s.getBoundingClientRect(),vb=s.viewBox.baseVal;
 var c={label:s.getAttribute('aria-label'),box:[sb.left,sb.top,sb.right,sb.bottom],scale:sb.width/vb.width,frames:[],texts:[]};
 s.querySelectorAll('rect.frame').forEach(function(f){var b=f.getBoundingClientRect();c.frames.push([b.left,b.top,b.right,b.bottom]);});
 s.querySelectorAll('text').forEach(function(t){var b=t.getBoundingClientRect();
  c.texts.push([b.left,b.top,b.right,b.bottom,t.textContent,parseFloat(t.getAttribute('font-size'))]);});
 out.charts.push(c);});
document.querySelectorAll('.tbl').forEach(function(d){var b=d.getBoundingClientRect();out.tbl.push([b.left,b.right,d.scrollWidth,d.clientWidth]);});
var p=document.createElement('pre');p.id='geom';p.textContent=JSON.stringify(out);document.body.appendChild(p);
})();</script>"""


def find_chrome():
    c = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")))
    return c[-1] if c else None


def chrome_geometry(chrome, page, tmp, width):
    d = os.path.join(tmp, "chrome-%d" % width)
    for sub in ("home", "profile", "tmp", "fontconfig"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    conf = os.path.join(d, "fontconfig", "fonts.conf")
    with open(conf, "w") as f:
        f.write("<?xml version='1.0'?><!DOCTYPE fontconfig SYSTEM 'fonts.dtd'><fontconfig><dir>/usr/share/fonts</dir>"
                "<cachedir>%s</cachedir><alias><family>monospace</family><prefer><family>DejaVu Sans Mono</family></prefer></alias>"
                "</fontconfig>" % os.path.join(d, "home", ".fc"))
    src = os.path.join(d, "page.html")
    with open(src, "w") as f:
        f.write(page.replace("</body>", GEOM_JS + "</body>"))
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.join(d, "home"), "XDG_CONFIG_HOME": os.path.join(d, "home", ".config"),
           "XDG_CACHE_HOME": os.path.join(d, "home", ".cache"), "TMPDIR": os.path.join(d, "tmp"), "FONTCONFIG_FILE": conf}
    cmd = [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
           "--disable-background-networking", "--disable-component-update", "--disable-sync", "--disable-extensions",
           "--disable-crash-reporter", "--disable-breakpad", "--host-resolver-rules=MAP * ~NOTFOUND",
           "--user-data-dir=" + os.path.join(d, "profile"), "--hide-scrollbars", "--window-size=%d,2000" % width,
           "--dump-dom", "file://" + src]
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, repr(e)
    m = re.search(r"<pre id=\"geom\">(.*?)</pre>", r.stdout, re.S)
    if not m:
        return None, "no geometry in the DOM dump (status %s)" % r.returncode
    return json.loads(html.unescape(m.group(1))), ""


def geometry_problems(g):
    """-> dict of problem lists for one DOM dump"""
    out = {"outside": [], "frame": [], "overlap": [], "small": []}
    for c in g["charts"]:
        bx = c["box"]
        boxes = []
        for l, t, r, b, s, fs in c["texts"]:
            if not s.strip():
                continue
            if l < bx[0] - 0.75 or r > bx[2] + 0.75 or t < bx[1] - 0.75 or b > bx[3] + 0.75:
                out["outside"].append((c["label"], s))
            # the line box of a text is taller than its glyphs: test the middle part against the frames
            h = b - t
            core = (l + 0.5, t + 0.22 * h, r - 0.5, b - 0.22 * h)
            for f in c["frames"]:
                inside = core[0] >= f[0] and core[2] <= f[2] and core[1] >= f[1] and core[3] <= f[3]
                apart = core[2] <= f[0] or core[0] >= f[2] or core[3] <= f[1] or core[1] >= f[3]
                if not inside and not apart:
                    out["frame"].append((c["label"], s))
            if fs * c["scale"] < 8.5:
                out["small"].append((c["label"], s, round(fs * c["scale"], 1)))
            boxes.append((core, s))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b2 = boxes[i][0], boxes[j][0]
                if min(a[2], b2[2]) - max(a[0], b2[0]) > 1.0 and min(a[3], b2[3]) - max(a[1], b2[1]) > 1.0:
                    out["overlap"].append((c["label"], boxes[i][1], boxes[j][1]))
    return out


def test_geometry(page, tmp, use_chrome):
    names = ["page does not scroll sideways", "no chart text leaves its chart", "no chart text crosses a plot frame",
             "no chart text covers another chart text", "chart text is at least 8.5 px high on screen"]
    chrome = find_chrome() if use_chrome else None
    for width in (1200, 390):
        if not chrome:
            for n in names:
                skip("%d px: %s" % (width, n), "no headless Chrome" if use_chrome else "--no-chrome")
            continue
        g, err = chrome_geometry(chrome, page, tmp, width)
        if g is None or abs(g["w"] - width) > 1:
            for n in names:
                skip("%d px: %s" % (width, n), err or "Chrome used a window of %s px" % g["w"])
            continue
        pr = geometry_problems(g)
        check("%d px: %s (page %d px, charts %d, tables %d)" % (width, names[0], g["sw"], len(g["charts"]), len(g["tbl"])),
              g["sw"] <= width and all(t[1] <= width + 0.5 and t[0] >= -0.5 for t in g["tbl"]), g["sw"])
        check("%d px: %s (%d texts)" % (width, names[1], sum(len(c["texts"]) for c in g["charts"])), not pr["outside"], pr["outside"][:6])
        check("%d px: %s (%d frames)" % (width, names[2], sum(len(c["frames"]) for c in g["charts"])), not pr["frame"], pr["frame"][:6])
        check("%d px: %s" % (width, names[3]), not pr["overlap"], pr["overlap"][:6])
        check("%d px: %s" % (width, names[4]), not pr["small"], pr["small"][:6])
    # the geometry checker must be able to fail
    fake = {"charts": [{"label": "x", "box": [0, 0, 100, 100], "scale": 1.0, "frames": [[10, 10, 90, 90]],
                        "texts": [[5, 40, 30, 52, "crosses", 11], [20, 60, 60, 72, "a", 11], [30, 62, 70, 74, "b", 11],
                                  [80, 0, 120, 8, "leaves", 6]]}]}
    pr = geometry_problems(fake)
    check("the geometry checker reports a text that crosses a frame, two texts that overlap, a text that leaves the chart and a small text",
          len(pr["frame"]) >= 1 and len(pr["overlap"]) == 1 and len(pr["outside"]) == 1 and len(pr["small"]) == 1, pr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Checks of report_final.py.")
    ap.add_argument("--tmp", default=None, help="folder for temporary files (default: a new folder under $TMPDIR)")
    ap.add_argument("--json", default=os.path.join(A, "final8.json"))
    ap.add_argument("--no-chrome", action="store_true", help="skip the checks that need a headless Chrome")
    a = ap.parse_args(argv)
    tmp = tempfile.mkdtemp(prefix="test-report-final-", dir=a.tmp)
    try:
        J = json.load(open(a.json))
        page = test_runs(J, a.json, tmp)
        test_numbers(page, J)
        test_verdict_texts(page, J)
        test_without_session2(J, tmp)
        test_with_both_sessions(J, tmp)
        test_claims_follow_data(page, J, tmp)
        test_supplementary(page, J, tmp)
        test_no_external(page)
        test_geometry(page, tmp, not a.no_chrome)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d checks, %d failed, %d skipped" % (NCHECK[0], len(FAILS), len(SKIPS)))
    for f in FAILS:
        print("FAILED: " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
