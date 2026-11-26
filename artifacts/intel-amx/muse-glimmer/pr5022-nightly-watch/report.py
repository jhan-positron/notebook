"""Builds report.html for the PR 5022 nightly watch. Called by watch.py."""
import datetime as dt
import html
import json
import math

E = html.escape
UTC = dt.timezone.utc
GL = "ingested_meta_models__muse_glimmer_30b_tp4_tps @ 8"
GL_MMLU = "ingested-meta-models--Muse-Glimmer-30B-tp4"
INTEL, AMD = "delphi-3bda", "andoria-b1a3"
MACHINE = {INTEL: ("Intel machine", "Intel Xeon 6, Granite Rapids", "intel"),
           AMD: ("AMD machine", "AMD EPYC, Genoa", "amd")}
METRIC = {"tps": ("Decode rate per user", "TPS", "higher is faster", "decode"),
          "ttft": ("Time to first token", "ms", "lower is faster", "prefill")}
TALOS_UI = "http://talos:5174/sessions/"
PR_URL = "https://github.com/positron-ai/tron/pull/5022"
MINUS = "−"


def day(ts, fmt="%b %-d"):
    return dt.datetime.fromtimestamp(ts, UTC).strftime(fmt)


def num(metric, v):
    return "%.2f" % v if metric == "tps" else "%d" % round(v)


def val(metric, v):
    return "%s %s" % (num(metric, v), METRIC[metric][1])


def pct(x, digits=1):
    s = "%+.*f" % (digits, 100 * x)
    return s.replace("-", MINUS) + " %"


def chip(check):
    kind, icon = {
        "as expected": ("good", "✓"),
        "waiting": ("wait", "○"),
        "faster, not expected": ("note", "▲"),
        "SLOWER": ("bad", "▼"),
        "NO GAIN": ("bad", "✕"),
        "TEST FAILED": ("bad", "✕"),
    }.get(check, ("wait", "○"))
    label = {"SLOWER": "slower", "NO GAIN": "no gain", "TEST FAILED": "test failed"}.get(check, check)
    return '<span class="chip %s"><span class="ic">%s</span>%s</span>' % (kind, icon, E(label))


def nice_ticks(lo, hi, n=5):
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if raw <= m * mag)
    v, out = math.ceil(lo / step) * step, []
    while v <= hi + 1e-9:
        out.append(round(v, 10))
        v += step
    dec = 0 if step >= 1 and step == int(step) else (1 if step * 10 == int(step * 10) else 2)
    return out, dec


def after_text(row):
    v = row["verdict"]
    if v["state"] == "waiting":
        return "no night yet"
    return "%s (%s, %d night%s)" % (val(row["metric"], v["median"]), pct(v["delta"]),
                                    v["n"], "" if v["n"] == 1 else "s")


# ---------------------------------------------------------- time-series panel

def ts_panel(dut, row, nights, pr, t0, t1, pid):
    metric, base = row["metric"], row["base"]
    W, H, L, R, T, B = 1000, 262, 56, 150, 28, 30
    pw, ph = W - L - R, H - T - B
    pts = [n for n in nights if n["dut"] == dut and GL in n["series"]]
    c, h = base["median"], base["half"]
    est = c * (1 + row["pr_measured"]) if row["pr_measured"] else None
    ys = [n["series"][GL][metric] for n in pts] + [c - h, c + h] + ([est] if est else [])
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.09
    lo, hi = lo - pad, hi + pad
    X = lambda t: L + (t - t0) / (t1 - t0) * pw
    Y = lambda v: T + (hi - v) / (hi - lo) * ph
    o = ['<svg class="ts" viewBox="0 0 %d %d" data-src="%s" data-w="%d" tabindex="0" role="img" '
         'aria-label="%s of Muse Glimmer on %s per night. Use the left and right arrow keys to read each night.">'
         % (W, H, pid, W, E(METRIC[metric][0]), E(dut))]
    ticks, dec = nice_ticks(lo, hi)
    for v in ticks:
        o.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (L, L + pw, Y(v), Y(v)))
        o.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%.*f</text>' % (L - 8, Y(v) + 4, dec, v))
    d = dt.datetime.fromtimestamp(t0, UTC).date()
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    while True:
        ts = dt.datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp()
        if ts > t1:
            break
        o.append('<line class="grid" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (X(ts), X(ts), T + ph, T + ph + 4))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (X(ts), T + ph + 18, d.strftime("%b %-d")))
        d += dt.timedelta(days=7)
    o.append('<line class="axis" x1="%d" x2="%d" y1="%d" y2="%d"/>' % (L, L + pw, T + ph, T + ph))
    # normal band and median, from the first baseline night to the right edge
    bx = X(base["first"]) - 7
    o.append('<rect class="band" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (bx, Y(c + h), L + pw - bx, Y(c - h) - Y(c + h)))
    o.append('<line class="median" x1="%.1f" x2="%d" y1="%.1f" y2="%.1f"/>' % (bx, L + pw, Y(c), Y(c)))
    o.append('<text class="lab strong" x="%d" y="%.1f">normal %s</text>' % (L + pw + 10, Y(c) + 1, val(metric, c)))
    o.append('<text class="lab" x="%d" y="%.1f">band ±%s (%.2f %%)</text>' % (L + pw + 10, Y(c) + 15, num(metric, h) if metric == "ttft" else "%.2f" % h, 100 * h / c))
    if est:
        ex = X(base["last"])
        o.append('<line class="est" x1="%.1f" x2="%d" y1="%.1f" y2="%.1f"/>' % (ex, L + pw, Y(est), Y(est)))
        o.append('<text class="lab strong" x="%d" y="%.1f">PR test: %s</text>' % (L + pw + 10, Y(est) + 1, val(metric, est)))
        o.append('<text class="lab" x="%d" y="%.1f">est., %s</text>' % (L + pw + 10, Y(est) + 15, pct(row["pr_measured"])))
    if pr.get("merged_ts"):
        mx = X(pr["merged_ts"])
        o.append('<line class="merge" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (mx, mx, T, T + ph))
        o.append('<text class="lab strong" x="%.1f" y="%d" text-anchor="end">PR 5022 merged</text>' % (mx + 4, T - 12))
        o.append('<line class="merge" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (mx, mx, T - 8, T))
    path = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", X(n["started"]), Y(n["series"][GL][metric])) for i, n in enumerate(pts))
    o.append('<path class="line %s" d="%s"/>' % (MACHINE[dut][2], path))
    inbase, data, last_post = set(base["uuids"]), [], None
    for n in pts:
        v = n["series"][GL][metric]
        x, y = X(n["started"]), Y(v)
        if n["has_pr"]:
            kind, cls, r = "night with PR 5022", "post", 5.5
            last_post = (x, y, v)
        elif n["uuid"] in inbase:
            kind, cls, r = "baseline night", "base", 4
        else:
            kind, cls, r = "older night, not in the baseline", "old", 3
        o.append('<circle class="dot %s %s" cx="%.1f" cy="%.1f" r="%s"/>' % (cls, MACHINE[dut][2], x, y, r))
        data.append({"x": round(x, 1), "y": round(y, 1), "t": day(n["started"], "%a %b %-d, %Y"),
                     "v": val(metric, v), "k": kind, "d": pct(v / c - 1, 2), "b": n["tron_version"]})
    if last_post:
        o.append('<text class="lab strong halo" x="%.1f" y="%.1f" text-anchor="end">%s</text>' % (last_post[0] - 9, last_post[1] - 9, num(metric, last_post[2])))
    o.append('<line class="xh" y1="%d" y2="%d" style="display:none"/><circle class="hl" r="8" style="display:none"/>' % (T, T + ph))
    o.append("</svg>")
    return ('<figure class="panel"><figcaption><b>%s</b> <span>%s, %s. The axis does not start at zero.</span></figcaption>'
            '<div class="scroll">%s</div><script type="application/json" id="%s">%s</script></figure>'
            % (E(METRIC[metric][0]), METRIC[metric][1], METRIC[metric][2], "".join(o), pid, json.dumps(data)))


# ------------------------------------------------------------- strip chart

def speed(metric, v, c):
    """Difference from normal as a speed change. Positive is faster for both metrics."""
    return v / c - 1 if metric == "tps" else c / v - 1


def strip(dut, rows):
    W, L, R, T, lane, nameh, gap = 520, 64, 128, 30, 17, 18, 8
    pw = W - L - R
    mags = [6.0]
    for r in rows:
        c, h = r["base"]["median"], r["base"]["half"]
        if h / c > 0.06:    # a series with a band wider than the axis does not set the axis
            continue
        mags.append(100 * abs(speed(r["metric"], r["pre_latest"], c)) + 1)
        if r["verdict"]["state"] != "waiting":
            mags.append(100 * abs(speed(r["metric"], r["verdict"]["median"], c)) + 1)
    A = min(30.0, 2.0 * math.ceil(max(mags) / 2))
    X = lambda p: L + (max(-A, min(A, 100 * p)) + A) / (2 * A) * pw
    keys = []
    for r in rows:
        if r["key"] not in keys:
            keys.append(r["key"])
    H = T + len(keys) * (nameh + 2 * lane + gap) + 30
    cls = MACHINE[dut][2]
    o = ['<svg class="strip" viewBox="0 0 %d %d" role="img" aria-label="Difference from normal of every model on %s">' % (W, H, E(dut))]
    for p in (-A, -A / 2, 0, A / 2, A):
        x = L + (p + A) / (2 * A) * pw
        o.append('<line class="%s" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % ("axis" if p == 0 else "grid", x, x, T - 6, H - 28))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x, H - 12, "0" if p == 0 else pct(p / 100, 0)))
    o.append('<text class="tick" x="%d" y="%d">slower</text><text class="tick" x="%d" y="%d" text-anchor="end">faster</text>' % (L, T - 12, L + pw, T - 12))
    y = T
    for key in keys:
        pair = [r for r in rows if r["key"] == key]
        o.append('<text class="name%s" x="4" y="%d">%s</text>' % (" strong" if pair[0]["glimmer"] else "", y + 13, E(pair[0]["name"])))
        y += nameh
        for r in pair:
            m, b = r["metric"], r["base"]
            c, h = b["median"], b["half"]
            cy = y + lane / 2
            lo, hi = sorted((speed(m, c - h, c), speed(m, c + h, c)))
            o.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 8, cy + 4, METRIC[m][3]))
            o.append('<rect class="band" x="%.1f" y="%.1f" width="%.1f" height="9" rx="4.5"/>' % (X(lo), cy - 4.5, X(hi) - X(lo)))
            pre = speed(m, r["pre_latest"], c)
            o.append('<circle class="ring %s" cx="%.1f" cy="%.1f" r="4"/>' % (cls, X(pre), cy))
            tip = [["normal", val(m, c)], ["band", "\u00b1%.2f %%" % (100 * h / c)],
                   ["newest night before the PR", "%s (%s)" % (val(m, r["pre_latest"]), pct(r["pre_latest"] / c - 1, 2))]]
            v = r["verdict"]
            note = ""
            if v["state"] != "waiting":
                sp = speed(m, v["median"], c)
                o.append('<circle class="dot post %s" cx="%.1f" cy="%.1f" r="5"/>' % (cls, X(sp), cy))
                tip.append(["with PR 5022, median of %d night%s" % (v["n"], "" if v["n"] == 1 else "s"),
                            "%s (%s)" % (val(m, v["median"]), pct(v["delta"], 2))])
                if v["state"] != "normal":
                    up = v["state"] == "faster"
                    note = '<tspan class="%s">%s</tspan> %s %s' % ("tgood" if up else "tbad", "\u25b2" if up else "\u25bc", pct(sp), v["state"])
            if r["check"] == "TEST FAILED":
                note = '<tspan class="tbad">\u2715</tspan> test failed'
                tip.append(["with PR 5022", "the test failed on at least one night"])
            if note:
                o.append('<text class="lab strong" x="%d" y="%.1f">%s</text>' % (L + pw + 8, cy + 4, note))
            o.append('<rect class="hit" x="0" y="%.1f" width="%d" height="%d" tabindex="0" data-tip="%s"/>' % (
                y, W, lane, E(json.dumps({"t": "%s: %s" % (r["name"], METRIC[m][3]), "rows": tip}), quote=True)))
            y += lane
        y += gap
    o.append("</svg>")
    return '<div class="scroll">%s</div>' % "".join(o)


# ------------------------------------------------------------------ tables

def series_table(rows):
    o = ['<div class="scroll"><table><thead><tr><th>Model and users</th><th>Metric</th><th class="n">Normal</th>'
         '<th class="n">Lowest to highest</th><th class="n">Band</th><th>Baseline nights</th>'
         '<th class="n">With PR 5022 (nights)</th><th class="n">Change</th><th>Result</th></tr></thead><tbody>']
    for r in rows:
        m, b, v = r["metric"], r["base"], r["verdict"]
        o.append("<tr%s><td>%s</td><td>%s, %s</td><td class=\"n\">%s</td><td class=\"n\">%s to %s</td><td class=\"n\">±%.2f %%</td>"
                 "<td>%d, %s to %s%s</td><td class=\"n\">%s</td><td class=\"n\">%s</td><td>%s</td></tr>" % (
                     ' class="gl"' if r["glimmer"] else "", E(r["name"]), METRIC[m][3], METRIC[m][1], num(m, b["median"]),
                     num(m, b["lo"]), num(m, b["hi"]), 100 * b["half"] / b["median"], b["n"], day(b["first"]), day(b["last"]),
                     " (short)" if b["short"] else "",
                     "%s (%d)" % (num(m, v["median"]), v["n"]) if v["state"] != "waiting" else "–",
                     pct(v["delta"], 2) if v["state"] != "waiting" else "–", chip(r["check"])))
    o.append("</tbody></table></div>")
    return "".join(o)


def glimmer_table(status):
    first = min(r["base"]["first"] for a in status["machines"].values() for r in a["rows"] if r["glimmer"])
    inb = {}
    for dut, a in status["machines"].items():
        for r in a["rows"]:
            if r["glimmer"]:
                for u in r["base"]["uuids"]:
                    inb.setdefault(u, []).append(METRIC[r["metric"]][3])
    o = ['<div class="scroll"><table><thead><tr><th>Night (UTC)</th><th>Machine</th><th>tron build</th><th>PR 5022 in the build</th>'
         '<th class="n">Decode, TPS</th><th class="n">TTFT, ms</th><th class="n">Prefill, tokens/s</th><th class="n">MMLU Pro, %</th>'
         '<th>Baseline night for</th><th>Session</th></tr></thead><tbody>']
    for n in reversed(status["nights"]):
        if n["started"] < first or GL not in n["series"]:
            continue
        s = n["series"][GL]
        o.append('<tr%s><td>%s</td><td>%s</td><td class="mono">%s</td><td>%s</td><td class="n">%.2f</td><td class="n">%d</td>'
                 '<td class="n">%d</td><td class="n">%s</td><td>%s</td><td><a href="%s%s">Talos</a></td></tr>' % (
                     ' class="gl"' if n["has_pr"] else "", day(n["started"], "%Y-%m-%d"), E(n["dut"]), E(str(n["tron_version"])),
                     {True: "yes", False: "no", None: "not decided"}[n["has_pr"]], s["tps"], s["ttft"], s["prefill"],
                     "%.2f" % n["mmlu"][GL_MMLU] if GL_MMLU in n["mmlu"] else ("running" if n.get("running") else "–"),
                     " and ".join(inb.get(n["uuid"], [])) or "–", TALOS_UI, E(n["uuid"])))
    o.append("</tbody></table></div>")
    return "".join(o)


def band_text(half, median):
    """Band in percent with two decimals and no trailing zero: 0.75 and 1.0."""
    t = "%.2f" % (100 * half / median)
    return "\u00b1%s %%" % (t[:-1] if t.endswith("0") else t)


def glimmer_snapshot(status):
    """The Glimmer summary table as data. One row per machine. After the fixed columns come
    two columns (decode, TTFT) for every night whose tron build contains the PR.
    "date" is the newest night in the table. It names the section of the page."""
    g = {(d, r["metric"]): r for d, a in status["machines"].items() for r in a["rows"] if r["glimmer"]}
    dates = sorted({day(x["started"], "%Y-%m-%d") for r in g.values() for x in r["after"]})
    head = ["Machine", "Decode normal", "Decode band", "TTFT normal", "TTFT band", "Baseline nights", "Expected with the PR"]
    for i, d in enumerate(dates, 1):
        label = dt.datetime.strptime(d, "%Y-%m-%d").strftime("%b %-d")
        head += ["Day %d decode (%s)" % (i, label), "Day %d TTFT (%s)" % (i, label)]
    rows, duts = [], []
    for dut in (INTEL, AMD):
        if (dut, "tps") not in g or (dut, "ttft") not in g:
            continue
        t, f = g[dut, "tps"], g[dut, "ttft"]
        bt, bf = t["base"], f["base"]
        if (bt["n"], bt["first"], bt["last"]) == (bf["n"], bf["first"], bf["last"]):
            nights = "%d (%s to %s)" % (bt["n"], day(bt["first"]), day(bt["last"]))
        else:
            nights = "%d for decode, %d for TTFT" % (bt["n"], bf["n"])
        exp = "no change"
        if t["pr_measured"] and f["pr_measured"]:
            exp = "faster: %s decode, %s TTFT (est. from the PR's own test [Ref2])" % (pct(t["pr_measured"]), pct(f["pr_measured"]))
        row = ["%s (%s)" % (dut, "Intel" if dut == INTEL else "AMD"),
               val("tps", bt["median"]) + " per user", band_text(bt["half"], bt["median"]),
               val("ttft", bf["median"]), band_text(bf["half"], bf["median"]), nights, exp]
        for d in dates:
            for r in (t, f):
                x = [a for a in r["after"] if day(a["started"], "%Y-%m-%d") == d]
                if not x:
                    row.append("\u2013")            # no result of this machine for that night
                elif "value" not in x[-1]:
                    row.append(x[-1]["state"])      # the test failed
                elif "delta" in x[-1]:
                    row.append("%s (%s)" % (val(r["metric"], x[-1]["value"]), pct(x[-1]["delta"])))
                else:
                    row.append("%s (%s)" % (val(r["metric"], x[-1]["value"]), x[-1]["state"]))
        rows.append(row)
        duts.append(dut)
    newest = dates[-1] if dates else day(max(r["base"]["last"] for r in g.values()), "%Y-%m-%d")
    title = ("%s: Day %d with PR 5022" % (newest, len(dates))) if dates else ("%s: baseline, before PR 5022" % newest)
    return {"date": newest, "title": title, "days": len(dates), "head": head, "rows": rows, "duts": duts}


def snapshot_html(snap):
    num_col = lambda i: i in (1, 2, 3, 4) or i >= 7
    o = ['<div class="scroll"><table class="days"><thead><tr>']
    o += ['<th%s>%s</th>' % (' class="n"' if num_col(i) else "", E(h)) for i, h in enumerate(snap["head"])]
    o.append("</tr></thead><tbody>")
    for dut, row in zip(snap["duts"], snap["rows"]):
        o.append("<tr>")
        for i, c in enumerate(row):
            if i == 0:
                o.append('<td><span class="sw %s"></span>%s</td>' % (MACHINE[dut][2], E(c)))
            else:
                o.append('<td%s>%s</td>' % (' class="n"' if num_col(i) else (' class="w"' if i == 6 else ' class="w2"'), E(c)))
        o.append("</tr>")
    o.append("</tbody></table></div>")
    return "".join(o)


def snapshot_markdown(snap):
    """The same table as Markdown text, for the chat report."""
    head = snap["head"]
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(r) + " |" for r in snap["rows"]])


# -------------------------------------------------------------------- page

CSS = """
/* Layout: one reading column. Status first, then one card per machine, then the records. */
:root{--bg:#f4f6f9;--surface:#ffffff;--ink:#17212b;--ink2:#4b5967;--ink3:#74818e;--rule:#d9e0e8;--grid:#e7ecf1;
--band:rgba(23,33,43,.075);--intel:#257de0;--amd:#f47230;--good:#0aac23;--goodbg:#e4f5e7;--goodink:#075e14;
--bad:#dc3c3d;--badbg:#fbe6e6;--badink:#8f1d1e;--notebg:#fdf1d3;--noteink:#6b4b00;--waitbg:#e9edf2;
--body:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;--head:"Space Grotesk","Inter",system-ui,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
body{background:var(--bg);color:var(--ink);font:15px/1.55 var(--body);margin:0}
.wrap{max-width:1120px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:26px}
h1{font:600 30px/1.15 var(--head);margin:0;letter-spacing:-.01em;text-wrap:balance}
h2{font:600 20px/1.25 var(--head);margin:0 0 10px;text-wrap:balance}
h3{font:600 16px/1.3 var(--head);margin:0}
p{margin:0 0 8px;max-width:72ch}
ul{margin:0;padding-left:20px;max-width:76ch}
li{margin:3px 0}
a{color:#1757ac}
.meta{color:var(--ink2);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 18px;margin-top:8px}
.short{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:16px 18px}
.short p{font-size:16px;margin:0;max-width:80ch}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:16px 18px;display:flex;flex-direction:column;gap:12px;min-width:0}
.mh{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
.sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}
.sw.intel{background:var(--intel)}.sw.amd{background:var(--amd)}
.sub{color:var(--ink2);font-size:13px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px 24px;font-size:14px}
.facts div{min-width:0}
.panel{margin:0;min-width:0}
figcaption{font-size:13px;color:var(--ink2);margin-bottom:2px}
figcaption b{color:var(--ink);font-weight:600}
.scroll{overflow-x:auto;min-width:0}
svg{display:block;width:100%;height:auto}
svg.ts{min-width:760px}svg.strip{min-width:440px;max-width:620px}
svg:focus-visible{outline:2px solid #1757ac;outline-offset:2px}
svg text{font-family:var(--body);font-size:12px;fill:var(--ink3);font-variant-numeric:tabular-nums}
svg text.strong{fill:var(--ink);font-weight:600}
svg text.name{fill:var(--ink2);font-size:12.5px}
svg text.name.strong{fill:var(--ink)}
svg text.halo{paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}
.grid{stroke:var(--grid);stroke-width:1}.axis{stroke:#b9c3ce;stroke-width:1}
.band{fill:var(--band)}.median{stroke:var(--ink2);stroke-width:1}
.est{stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:5 4}
.merge{stroke:var(--ink);stroke-width:1}
.line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round;opacity:.3}
.line.intel{stroke:var(--intel)}.line.amd{stroke:var(--amd)}
.dot{stroke:var(--surface);stroke-width:2}
.dot.intel{fill:var(--intel)}.dot.amd{fill:var(--amd)}
.dot.old{opacity:.4;stroke-width:1}
.ring{fill:var(--surface);stroke-width:2}.ring.intel{stroke:var(--intel)}.ring.amd{stroke:var(--amd)}
.xh{stroke:var(--ink3);stroke-width:1}.hl{fill:none;stroke:var(--ink);stroke-width:1.5}
.hit{fill:transparent;outline:none}.hit.on,.hit:focus-visible{fill:rgba(23,33,43,.05)}
.tgood{fill:var(--good)}.tbad{fill:var(--bad)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink2);align-items:center}
.legend span{display:inline-flex;align-items:center;gap:6px}
.k{display:inline-block;flex:none}
.k.dot3{width:7px;height:7px;border-radius:50%;background:var(--ink3);opacity:.5}
.k.dot4{width:9px;height:9px;border-radius:50%;background:var(--ink2)}
.k.dot5{width:12px;height:12px;border-radius:50%;background:var(--ink)}
.k.ringk{width:8px;height:8px;border-radius:50%;border:2px solid var(--ink2);background:var(--surface)}
.k.bandk{width:22px;height:10px;border-radius:3px;background:var(--band)}
.k.estk{width:22px;height:0;border-top:2px dashed var(--ink2)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,500px),1fr));gap:18px}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid);white-space:nowrap;vertical-align:top}
th{font-weight:600;color:var(--ink2);border-bottom:1px solid var(--rule);font-size:12px}
td.n,th.n{text-align:right}
tr.gl td{background:#f3f7fd}
table.wrapt td{white-space:normal}table.wrapt td.n{white-space:nowrap}
table.days th{white-space:normal;vertical-align:bottom}
table.days td.w{white-space:normal;min-width:176px}table.days td.w2{white-space:normal;min-width:92px}
table.days th:first-child,table.days td:first-child{position:sticky;left:0;background:var(--surface)}
.mono{font-family:var(--mono);font-size:12px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:1px 9px 1px 7px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.chip .ic{font-size:11px}
.chip.good{background:var(--goodbg);color:var(--goodink)}.chip.good .ic{color:var(--good)}
.chip.bad{background:var(--badbg);color:var(--badink)}.chip.bad .ic{color:var(--bad)}
.chip.note{background:var(--notebg);color:var(--noteink)}
.chip.wait{background:var(--waitbg);color:var(--ink2)}
.toc{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:14px 18px}
.toc h2{font-size:16px;margin-bottom:6px}
.toc ul{list-style:none;padding:0;margin:0;columns:2 300px;column-gap:32px;max-width:none}
.toc li{margin:2px 0;break-inside:avoid}
.older{display:flex;flex-direction:column;gap:8px}
.older h3{font-size:14px;color:var(--ink2)}
section[id],details[id]{scroll-margin-top:12px}
details{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:10px 16px}
summary{cursor:pointer;font:600 15px var(--head)}
details ul,details ol{margin-top:8px}
.refs{font-size:13px;color:var(--ink2);padding-left:0;list-style:none;max-width:none}
.refs li{margin:5px 0;overflow-wrap:anywhere}
.err{background:var(--badbg);color:var(--badink);border-radius:8px;padding:10px 14px;font-weight:600}
#tip{position:fixed;z-index:20;background:var(--surface);border:1px solid var(--rule);border-radius:8px;box-shadow:0 6px 20px rgba(23,33,43,.14);padding:8px 11px;font-size:12px;max-width:300px;pointer-events:none}
#tip .tt{font-weight:600;margin-bottom:4px}
#tip .tr{display:flex;gap:8px;align-items:baseline}
#tip .tv{font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
#tip .tk{color:var(--ink3)}
"""

JS = """
(function(){
var tip=document.getElementById('tip');
function place(cx,cy){tip.hidden=false;var w=tip.offsetWidth,h=tip.offsetHeight,x=cx+14,y=cy+14;
if(x+w>window.innerWidth-8)x=cx-w-14;if(x<8)x=8;if(y+h>window.innerHeight-8)y=cy-h-14;if(y<8)y=8;
tip.style.left=x+'px';tip.style.top=y+'px';}
function fill(title,rows){tip.textContent='';var t=document.createElement('div');t.className='tt';t.textContent=title;tip.appendChild(t);
rows.forEach(function(r){var d=document.createElement('div');d.className='tr';var a=document.createElement('span');a.className='tv';a.textContent=r[1];
var b=document.createElement('span');b.className='tk';b.textContent=r[0];d.appendChild(a);d.appendChild(b);tip.appendChild(d);});}
function hide(){tip.hidden=true;}
document.querySelectorAll('svg.ts').forEach(function(svg){
var pts=JSON.parse(document.getElementById(svg.dataset.src).textContent),W=+svg.dataset.w,xh=svg.querySelector('.xh'),hl=svg.querySelector('.hl'),cur=-1;
function sel(i,cx,cy){cur=i;var p=pts[i];xh.setAttribute('x1',p.x);xh.setAttribute('x2',p.x);hl.setAttribute('cx',p.x);hl.setAttribute('cy',p.y);
xh.style.display='';hl.style.display='';fill(p.t,[[p.k,p.v],['against normal',p.d],['tron build',p.b]]);
var r=svg.getBoundingClientRect(),s=r.width/W;place(cx==null?r.left+p.x*s:cx,cy==null?r.top+p.y*s:cy);}
function off(){xh.style.display='none';hl.style.display='none';hide();}
svg.addEventListener('pointermove',function(e){var r=svg.getBoundingClientRect(),x=(e.clientX-r.left)*W/r.width,b=0,bd=1e9;
pts.forEach(function(p,i){var d=Math.abs(p.x-x);if(d<bd){bd=d;b=i;}});sel(b,e.clientX,e.clientY);});
svg.addEventListener('pointerleave',off);
svg.addEventListener('focus',function(){sel(cur<0?pts.length-1:cur);});
svg.addEventListener('blur',off);
svg.addEventListener('keydown',function(e){if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();
var i=(cur<0?pts.length-1:cur)+(e.key==='ArrowLeft'?-1:1);sel(Math.max(0,Math.min(pts.length-1,i)));}});
});
document.querySelectorAll('.toc a').forEach(function(a){a.addEventListener('click',function(e){
var t=document.getElementById(a.getAttribute('href').slice(1));if(!t)return;if(t.tagName==='DETAILS')t.open=true;
e.preventDefault();t.scrollIntoView({block:'start'});});});
document.querySelectorAll('.hit').forEach(function(el){
var d=JSON.parse(el.dataset.tip);
function on(cx,cy){fill(d.t,d.rows);el.classList.add('on');place(cx,cy);}
function off(){el.classList.remove('on');hide();}
el.addEventListener('pointermove',function(e){on(e.clientX,e.clientY);});
el.addEventListener('pointerleave',off);
el.addEventListener('focus',function(){var r=el.getBoundingClientRect();on(r.left+r.width*0.55,r.bottom);});
el.addEventListener('blur',off);
});
})();
"""


def short_version(status):
    pr, M = status["pr"], status["machines"]
    g = {(d, r["metric"]): r for d, a in M.items() for r in a["rows"] if r["glimmer"]}
    n_post = max(a["n_post"] for a in M.values())
    if n_post == 0:
        state = ("PR 5022 was merged on %s UTC, and no nightly run has used a build with it yet"
                 % pr["mergedAt"][:16].replace("T", " ")) if pr.get("state") == "MERGED" else \
                "PR 5022 is not merged yet, so no nightly run contains it"
        return ("%s. The normal values are ready: Muse Glimmer on the Intel machine decodes at %s per user with a time to "
                "first token of %s, and on the AMD machine at %s with %s. The expectation is a faster Glimmer on the Intel "
                "machine and no change anywhere else."
                % (state, val("tps", g[INTEL, "tps"]["base"]["median"]), val("ttft", g[INTEL, "ttft"]["base"]["median"]),
                   val("tps", g[AMD, "tps"]["base"]["median"]), val("ttft", g[AMD, "ttft"]["base"]["median"])))
    it, ip, at, ap = g[INTEL, "tps"], g[INTEL, "ttft"], g[AMD, "tps"], g[AMD, "ttft"]

    def one(r):
        v = r["verdict"]
        return "no result yet" if v["state"] == "waiting" else "%s (%s)" % (val(r["metric"], v["median"]), pct(v["delta"]))
    others = [r for a in M.values() for r in a["rows"] if not r["glimmer"] and r["verdict"]["state"] != "waiting"]
    slower = [r for r in others if r["check"] in ("SLOWER", "TEST FAILED")]
    s1 = "%d nightly run%s on the Intel machine and %d on the AMD machine used a tron build with PR 5022." % (
        M[INTEL]["n_post"], "" if M[INTEL]["n_post"] == 1 else "s", M[AMD]["n_post"])
    s2 = "Muse Glimmer on the Intel machine: decode %s, time to first token %s; on the AMD machine: decode %s, time to first token %s." % (
        one(it), one(ip), one(at), one(ap))
    s3 = ("Other models: none of the %d compared series is slower than its normal band." % len(others)) if not slower else (
        "Other models: %d of the %d compared series are slower than normal or failed: %s." % (
            len(slower), len(others), "; ".join(sorted({r["name"] for r in slower}))))
    return " ".join((s1, s2, s3))


def render(status):
    pr, M, nights = status["pr"], status["machines"], status["nights"]
    t0 = min(n["started"] for n in nights) - 86400
    t1 = max(n["started"] for n in nights) + 6 * 86400
    o = ['<meta name="claude:viewport-fit-sides" content="cover"><title>PR 5022 Nightly Watch</title>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@600&display=swap">',
         "<style>%s</style>" % CSS, '<div class="wrap">']
    merged = pr.get("state") == "MERGED"
    o.append('<header><h1>PR 5022 Nightly Watch</h1><div class="meta"><span>Updated %s</span><span>PR 5022: %s</span>'
             '<span>Nights with the PR: Intel %d, AMD %d</span></div></header>' % (
                 E(status["generated"]),
                 "merged %s UTC, commit %s" % (pr["mergedAt"][:16].replace("T", " "), E(pr["oid"][:10])) if merged else "not merged yet (state %s)" % E(str(pr.get("state"))).lower(),
                 M[INTEL]["n_post"], M[AMD]["n_post"]))
    if status.get("error"):
        o.append('<div class="err">%s. The page shows the last saved data.</div>' % E(status["error"]))
    o.append('<section class="short"><h2>Short version</h2><p>%s</p></section>' % E(short_version(status)))

    # One section per date, newest first. Each holds the Glimmer table as it stood for that nightly.
    log = status.get("table_log") or [glimmer_snapshot(status)]
    arr = status.get("arrived") or {}
    toc = [("night-" + x["date"], x["title"]) for x in log] + [
        ("expectation-check", "Expectation check"),
        ("glimmer-history", "Muse Glimmer, every night since October 1"),
        ("all-models", "All models against their normal"),
        ("series-intel", "Every series on the Intel machine"),
        ("series-amd", "Every series on the AMD machine"),
        ("glimmer-record", "Muse Glimmer nightly record")] + (
        [("arrived", "What else arrived in the first build with PR 5022")] if arr else []) + [
        ("method", "How the normal is calculated"), ("words", "Words used here"), ("references", "References")]
    o.append('<nav class="toc" aria-label="Table of contents"><h2>Table of contents</h2><ul>%s</ul></nav>' % "".join(
        '<li><a href="#%s">%s</a></li>' % (i, E(t)) for i, t in toc))
    for k, x in enumerate(log):
        if k == 0:
            o.append('<section id="night-%s"><h2>%s</h2><div class="card">%s</div><p class="sub" style="margin-top:8px">'
                     'The section name is the date of the nightly report, the same date as in the title of the Slack report. %s '
                     'Normal is the median of the baseline nights. The band is the range around the normal that still counts as no change. '
                     'TPS is tokens per second. TTFT is the time to first token, the measure of prefill. '
                     'The percentage in a day column is the change from the normal. For the decode rate a positive change is faster. '
                     'For the TTFT a negative change is faster.</p></section>' % (
                         x["date"], E(x["title"]), snapshot_html(x),
                         "Day 1 is the first nightly whose tron build contains PR 5022." if x["days"] else
                         "No nightly contains PR 5022 yet. From the first such nightly on, each night adds two columns: the decode rate and the TTFT."))
        else:
            if k == 1:
                o.append('<section class="older"><h3>Earlier dates</h3>')
            o.append('<details id="night-%s"><summary>%s</summary>%s</details>' % (x["date"], E(x["title"]), snapshot_html(x)))
    if len(log) > 1:
        o.append("</section>")

    # expectation table
    o.append('<section id="expectation-check"><h2>Expectation check</h2><div class="card"><div class="scroll"><table class="wrapt"><thead><tr><th>Machine</th><th>What</th>'
             '<th>Expected with PR 5022</th><th class="n">Normal</th><th class="n">With PR 5022</th><th>Result</th></tr></thead><tbody>')
    for dut in (INTEL, AMD):
        a = M[dut]
        for r in a["rows"]:
            if not r["glimmer"]:
                continue
            exp = "no change"
            if r["pr_measured"]:
                exp = "faster (the PR's own test: %s, est.)" % pct(r["pr_measured"])
            o.append('<tr><td><span class="sw %s"></span>%s</td><td>Muse Glimmer %s</td><td>%s</td><td class="n">%s</td><td class="n">%s</td><td>%s</td></tr>' % (
                MACHINE[dut][2], MACHINE[dut][0], METRIC[r["metric"]][3], exp, val(r["metric"], r["base"]["median"]), after_text(r), chip(r["check"])))
        rest = [r for r in a["rows"] if not r["glimmer"]]
        done = [r for r in rest if r["verdict"]["state"] != "waiting" or r["check"] == "TEST FAILED"]
        bad = [r for r in done if r["check"] in ("SLOWER", "TEST FAILED")]
        fast = [r for r in done if r["verdict"]["state"] == "faster"]
        res = chip("waiting") if not done else (chip("SLOWER") if bad else chip("as expected"))
        txt = "no night yet" if not done else "%d slower or failed, %d faster, %d inside the band" % (len(bad), len(fast), len(done) - len(bad) - len(fast))
        o.append('<tr><td><span class="sw %s"></span>%s</td><td>Other models, %d series</td><td>no change, no series slower</td><td class="n">per series</td><td class="n">%s</td><td>%s</td></tr>' % (
            MACHINE[dut][2], MACHINE[dut][0], len(rest), txt, res))
    o.append("</tbody></table></div></div>")
    o.append('<p class="sub" style="margin-top:8px">The verdict of a series uses the median of all nights with the PR. A verdict from one night is preliminary. '
             'The expected gain comes from the PR description [Ref2].</p></section>')

    # Glimmer charts
    o.append('<section id="glimmer-history"><h2>Muse Glimmer, every night since October 1</h2>'
             '<div class="legend"><span><i class="k dot3"></i>older night, not in the baseline</span><span><i class="k dot4"></i>baseline night</span>'
             '<span><i class="k dot5"></i>night with PR 5022</span><span><i class="k bandk"></i>normal band</span>'
             '<span><i class="k estk"></i>result of the PR\'s own test (est.)</span></div></section>')
    pid = 0
    for dut in (INTEL, AMD):
        a = M[dut]
        o.append('<section class="card"><div class="mh"><h3><span class="sw %s"></span>%s</h3><span class="sub">%s, %s</span></div><div class="facts">' % (
            MACHINE[dut][2], MACHINE[dut][0], E(dut), MACHINE[dut][1]))
        for r in a["rows"]:
            if r["glimmer"]:
                b = r["base"]
                o.append("<div><b>%s.</b> Normal %s from %d nights (%s to %s). With PR 5022: %s. %s</div>" % (
                    METRIC[r["metric"]][0], val(r["metric"], b["median"]), b["n"], day(b["first"]), day(b["last"]), after_text(r), chip(r["check"])))
        o.append("</div>")
        for r in a["rows"]:
            if r["glimmer"]:
                pid += 1
                o.append(ts_panel(dut, r, nights, pr, t0, t1, "ts%d" % pid))
        o.append("</section>")
    o.append('<p class="sub">Each dot is one nightly run. The grey band is the normal value plus or minus the band width. '
             'Older nights ran with other platform software or sit before a level shift, so they are not part of the baseline. '
             'Point at a chart, or focus it and press the arrow keys, to read one night.</p>')

    # all models
    o.append('<section id="all-models"><h2>All models against their normal</h2><div class="legend"><span><i class="k ringk"></i>newest night before the PR</span>'
             '<span><i class="k dot5"></i>median of the nights with PR 5022</span><span><i class="k bandk"></i>normal band of that series</span></div>'
             '<div class="two" style="margin-top:12px">')
    for dut in (INTEL, AMD):
        o.append('<div class="card"><div class="mh"><h3><span class="sw %s"></span>%s</h3><span class="sub">%s</span></div>%s</div>' % (
            MACHINE[dut][2], MACHINE[dut][0], E(dut), strip(dut, M[dut]["rows"])))
    o.append('</div><p class="sub" style="margin-top:8px">The axis shows the speed difference from normal in percent. Right is faster for both rows of a model: '
             'a higher decode rate, or a shorter time to first token. A band or a dot at the edge of the plot lies beyond the axis. Point at a row to read its numbers.</p></section>')
    for dut in (INTEL, AMD):
        o.append('<section id="series-%s"><h3 style="margin-bottom:8px"><span class="sw %s"></span>%s (%s): every series</h3><div class="card">%s</div></section>' % (
            MACHINE[dut][2], MACHINE[dut][2], MACHINE[dut][0], E(dut), series_table(M[dut]["rows"])))

    o.append('<section id="glimmer-record"><h2>Muse Glimmer nightly record</h2><div class="card">%s</div>'
             '<p class="sub" style="margin-top:8px">MMLU Pro (an accuracy test on a 10 %% sample of the questions) is listed for reference. This page does not judge it.</p></section>' % glimmer_table(status))

    if arr:
        o.append("<section id=\"arrived\"><h2>What else arrived in the first build with PR 5022</h2><p>A nightly build contains every change merged that day. "
                 "A change of a number on the first night with the PR can come from any commit in this list [Ref4].</p>")
        seen = set()
        for dut, x in arr.items():
            k = (x["old"], x["new"])
            if k in seen:
                continue
            seen.add(k)
            c = x.get("commits")
            o.append("<details><summary>Commits from build %s to build %s: %s</summary><ol>%s</ol></details>" % (
                E(x["old"]), E(x["new"]), "%d" % len(c) if c is not None else "list not available",
                "".join("<li>%s</li>" % E(t) for t in (c or []))))
        o.append("</section>")

    fa = status.get("false_alarms") or {}
    o.append("<section id=\"method\"><h2>How the normal is calculated</h2><ul>"
             "<li>Source: every scheduled nightly session of the two machines since October 1, 2026, read from Talos [Ref1]. Reruns started by hand are left out.</li>"
             "<li>A night counts as a night with PR 5022 when the merge commit of the PR is an ancestor of the commit of its tron build [Ref4].</li>"
             "<li>Baseline nights: start at the newest night before the PR. Keep the nights with the same platformd version, the same FPGA image and the same test settings. "
             "Then walk back night by night. Two nights in a row that sit more than 3 spreads from the median are a level shift, and the baseline stops there.</li>"
             "<li>Normal: the median of the baseline nights.</li>"
             "<li>Spread: 1.4826 times the median distance of the baseline nights from their median. For bell-shaped data this equals the standard deviation. One odd night does not change it.</li>"
             "<li>Band: the normal plus or minus the largest of three values: 4 spreads; 0.75 % of the normal for the decode rate or 1 % for the time to first token; 3 ms for the time to first token.</li>"
             "<li>A night outside the band counts as faster or slower. Inside the band it counts as normal.</li>"
             + ("<li>False alarms: each baseline night was tested against a band built from the other baseline nights of its series. %d of %d nights fell outside (%.1f %%).</li>" % (
                 fa["flagged"], fa["total"], 100.0 * fa["flagged"] / fa["total"]) if fa.get("total") else "")
             + "<li>Not covered: the rate of the slowest user, which the Slack report prints [Ref3]. The numbers here are the mean over all users.</li>"
             "<li>The nightly package build turns AMX on [Ref5]. Without it PR 5022 could not change the nightly numbers.</li></ul></section>")

    o.append("<details id=\"words\"><summary>Words used here</summary><ul>"
             "<li><b>tron</b>: the inference program under test. <b>rinzler</b>: the production server built from it, which the nightly runs.</li>"
             "<li><b>PR 5022</b>: the tron pull request that lets the AMX attention code serve Muse Glimmer [Ref2].</li>"
             "<li><b>AMX</b>, <b>AVX</b>: CPU instruction sets for matrix and vector math. Only the Intel machine has AMX. Before the PR, Glimmer used AVX on both machines.</li>"
             "<li><b>Muse Glimmer 30B</b>: a 30-billion-parameter language model. It has 16 query heads per KV head (kv_mul 16), a shape the AMX code did not accept before the PR.</li>"
             "<li><b>Nightly</b>: the System CI run of the systems_test repository. Each night it runs functional, performance, accuracy and soak tests on a whole machine.</li>"
             "<li><b>delphi-3bda</b>: the Intel machine of the nightly. <b>andoria-b1a3</b>: the AMD machine of the nightly.</li>"
             "<li><b>Talos</b>: the internal test-results service that stores every nightly session.</li>"
             "<li><b>Decode</b>: producing output tokens one by one. <b>TPS</b>: tokens per second for one user during decode, as a mean over all users.</li>"
             "<li><b>Prefill</b>: reading the prompt before the first output token. <b>TTFT</b> (time to first token): how long that takes, in milliseconds. The nightly prompt has 1024 tokens.</li>"
             "<li><b>tp2, tp4</b>: the model is split over 2 or 4 FPGA cards. <b>8 users</b>: 8 requests run at the same time on the machine.</li>"
             "<li><b>Series</b>: one model at one user count on one machine, for one metric.</li>"
             "<li><b>Median</b>: the middle value of a sorted list. <b>Level shift</b>: a lasting step of a series to a new level.</li>"
             "<li><b>platformd</b>: the control service on the machine that starts the servers. <b>FPGA image</b>: the bitfile loaded on the accelerator cards.</li>"
             "<li><b>tron build</b> name, for example v2026.11.25-73ab1891: the build date and the first 8 digits of the commit.</li>"
             "<li><b>est.</b>: an estimate, not a measurement of the nightly.</li></ul></details>")

    o.append('<section id="references"><h2>References</h2><ul class="refs">'
             "<li>[Ref1] Talos session list, <span class=\"mono\">http://talos:5000/sessions</span> (company network). Fields named <span class=\"mono\">&lt;model&gt;_tps @ &lt;users&gt;</span> hold the decode rate, its standard deviation, the TTFT and the prompt settings.</li>"
             '<li>[Ref2] <a href="%s">tron PR 5022</a>, description, section &ldquo;Nightly configuration&rdquo;: on delphi-3bda at commit 5061623a34 the decode rate rose by 4.6 %% and the TTFT fell by 3.4 %% against the nightly package of 2026-10-17.</li>'
             '<li>[Ref3] Slack channel <a href="https://positronai.slack.com/archives/C06S8PNDBQA">#ci-cd-notifications</a>: the nightly reports of the talos bot. They print the same decode rate and TTFT as Talos.</li>'
             "<li>[Ref4] GitHub compare API, <span class=\"mono\">repos/positron-ai/tron/compare/&lt;merge commit&gt;...&lt;build commit&gt;</span>. A result with behind_by 0 means the build contains the PR.</li>"
             "<li>[Ref5] tron <span class=\"mono\">CMakePresets.json</span>, preset <span class=\"mono\">deb</span>, line 68: <span class=\"mono\">TRON_AMX_DISPATCH ON</span> (read on 2026-11-25).</li>"
             "<li>[Ref6] The script <span class=\"mono\">muse-glimmer/pr5022-nightly-watch/watch.py</span> holds the band rule and writes this page.</li>"
             "</ul></section>" % PR_URL)
    o.append('</div><div id="tip" role="status" hidden></div><script>%s</script>' % JS)
    return "".join(o).encode("ascii", "xmlcharrefreplace").decode("ascii")
