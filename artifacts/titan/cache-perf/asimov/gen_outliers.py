#!/usr/bin/env python3
"""Build outliners.html: every measurement outlier of the Asimov study, what looked wrong, why, and the tests added.

Data layer (written by the research and polish workflows of 2026-11-08, verified against the results folders):
  DATA/entries/<id>.json   one verified record per outlier (the long form; shown under "Full record")
  DATA/polished.json       the plain-English bullets, chart spec and terms per outlier
  DATA/facts.json          the architecture and prefetcher fact sheets
The architecture, prefetcher and rounds sections are typed in here from those fact sheets (cited where used).
"""
import json, os, re, html, glob, datetime

A = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("OUTLIERS_DATA", "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/outliers")
OUT = A + "/outliners.html"

IDS = json.load(open(DATA + "/entry-ids.json"))["ids"]
REQUEST = open(DATA + "/request.txt", encoding="utf-8").read()  # Jibin's prompt, verbatim, never edited
ENTRIES = {i: json.load(open(f"{DATA}/entries/{i}.json")) for i in IDS}
try:
    POL = {p["id"]: p for p in json.load(open(DATA + "/polished.json"))["polished"]}
except FileNotFoundError:
    POL = {}

HOP_RULES = [(re.compile(r"mesh hops"), "mesh steps"), (re.compile(r"hop count"), "step count"),
             (re.compile(r"DUP/LASTB hops"), "DUP/LASTB round trips"), (re.compile(r"\bone-hop\b"), "one-load"),
             (re.compile(r"\bhops per rep\b"), "round trips per rep"), (re.compile(r"\bhops\b"), "loads"), (re.compile(r"\bhop\b"), "load")]

def esc(s):
    """HTML-escape, and apply Jibin's page wording: no 'hop' (a chain has loads, the mesh has steps)."""
    s = str(s)
    for rx, rep in HOP_RULES: s = rx.sub(rep, s)
    return html.escape(s, quote=False)

# ---------------------------------------------------------------- the architecture diagram
# Block ids used by the outlier records (the "blocks" field) map onto drawn blocks here.
ALIAS = {"L1-DTLB": "core", "SCP": "firmware", "memory-controller": "memory-model", "DSU-L3": "L3", "TLB": "core",
         "CME-L1": "CME", "CME-prefetcher": "CME-prefetcher", "home-node": "home-node", "timer": "harness"}

DASH = ' stroke-dasharray="5 4"'
BOLD = ' font-weight="600"'

def arch_svg(hl=(), compact=False, idp="a"):
    """The hierarchy as boxes, left to right: cluster, mesh and home nodes, memory. Highlighted ids get class hl."""
    hl = {ALIAS.get(b, b) for b in hl}
    W, H = 1000, 380
    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Asimov memory hierarchy diagram">']
    def box(bid, x, y, w, h, lines, dash=False, fs=12, sub=False, title=False):
        cls = "blk hl" if bid in hl else ("blk sub" if sub else "blk")
        o.append(f'<g class="{cls}" id="{idp}-{bid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5"{DASH if dash else ""}/>')
        if title:
            o.append(f'<text x="{x + 10}" y="{y + 16}" font-size="{fs}"{BOLD}>{esc(lines[0])}</text>')
        else:
            n = len(lines); lh = 13.5
            ty = y + h / 2 - (n - 1) * lh / 2 + 4.5
            for i, ln in enumerate(lines):
                o.append(f'<text x="{x + w / 2:.0f}" y="{ty + i * lh:.1f}" text-anchor="middle" font-size="{fs if i == 0 else fs - 1.5}"{BOLD if i == 0 else ""}>{esc(ln)}</text>')
        o.append('</g>')
    def arrow(x1, y1, x2, y2, label=None):
        o.append(f'<line class="lnk" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
        if label: o.append(f'<text x="{(x1 + x2) / 2:.0f}" y="{y1 - 6:.0f}" text-anchor="middle" font-size="10" class="lbl">{esc(label)}</text>')
    # cluster
    box("DSU", 8, 8, 384, 300, ["DSU cluster (one of five)"], dash=True, fs=12, title=True)
    box("core", 18, 34, 180, 68, ["C1-Nano core 0", "in-order, 2 x 128-bit loads per cycle", "L1 DTLB 16 entries"], fs=12)
    box("core2", 206, 34, 176, 68, ["C1-Nano core 1", "(CPU 3, 5, 7 or 9)", "same as core 0"], fs=12, sub=True)
    box("L1", 18, 110, 118, 38, ["L1 data 32 KiB", "4 cycles, 2.0 ns"], fs=11)
    box("L1-prefetcher", 142, 110, 56, 38, ["L1 pre-", "fetcher"], fs=10)
    box("L1b", 206, 110, 118, 38, ["L1 data 32 KiB", "(core 1)"], fs=11, sub=True)
    box("L1pfb", 330, 110, 52, 38, ["L1 pre-", "fetcher"], fs=10, sub=True)
    box("L2", 18, 158, 244, 40, ["L2 128 KiB, shared by both cores", "12 cycles, 6.0 ns"], fs=11)
    box("L2-prefetcher", 268, 158, 114, 40, ["L2-side prefetcher", "fills the L2"], fs=10)
    box("CME", 18, 208, 244, 40, ["CME (C1-SME2 unit): L1D 64 KiB", "streaming-mode loads and stores"], fs=11)
    box("CME-prefetcher", 268, 208, 114, 40, ["CME prefetcher", "128 streams"], fs=10)
    box("L3", 18, 258, 244, 40, ["L3 256 KiB per cluster", "held no data until boot E"], fs=11)
    box("snoop-filter", 268, 258, 114, 40, ["snoop filter", "tracks the cores' lines"], fs=10)
    # mesh
    box("mesh", 412, 8, 280, 300, ["CMN S3 mesh: 6 x 6 crosspoints"], dash=True, fs=12, title=True)
    box("home-node", 422, 34, 260, 134, ["home node HN-S (one of five)", "owns 1/5 of all addresses by hash"], fs=12)
    box("SLC", 430, 80, 120, 82, ["SLC 768 KiB", "12 of 16 ways", "caches DRAM lines", "5 x 768 KiB = 3.75 MiB"], fs=11)
    box("OCM", 556, 80, 120, 82, ["OCM 256 KiB", "4 locked ways", "addressable SRAM", "5 x 256 KiB = 1.25 MiB"], fs=11)
    box("meshxp", 422, 178, 260, 56, ["crosspoints and links", "1 to 5 steps from a cluster to a node", "about 1 ns per step est."], fs=11, sub=True)
    box("sbsx", 422, 244, 260, 54, ["SBSX bridges (10)", "requests to memory leave the mesh here"], fs=11, sub=True)
    # memory
    box("memory-model", 712, 34, 280, 68, ["4 Cadence AXI memory models", "every delay control 0", "3 ns native response, no refresh"], fs=11)
    box("DRAM", 712, 112, 280, 56, ["DRAM 2 GiB (emulator memory)", "52.7 ns per random load from the core"], fs=11)
    box("memnote", 712, 178, 280, 120, ["Load cost from a core (boot E)", "L1 2.0 ns, L2 6.0 ns", "L3 hit 10.8 ns est.", "SLC 24.2 ns, OCM 26.1 ns", "DRAM 52.7 ns", "(2.003 GHz: 1 ns = 2 cycles)"], fs=11, sub=True)
    # off-chip helpers
    box("firmware", 8, 322, 236, 48, ["Firmware: SCP and TF-A", "SCP stages the L3 mode; TF-A", "turns the prefetchers off (B, D, F2)"], fs=10)
    box("kernel-os", 254, 322, 236, 48, ["Kernel and OS", "page placement, /dev/ocm,", "isolated CPUs 2 to 9, huge pages"], fs=10)
    box("harness", 500, 322, 236, 48, ["Test harness", "chase and bandwidth programs,", "timer stamps, PMU and mesh counters"], fs=10)
    box("memory-ref", 746, 322, 246, 48, ["Reference numbers", "asimov-bench (older RTL), CRB server,", "Arm documents"], fs=10, sub=True)
    arrow(392, 290, 412, 290, "port")
    arrow(692, 140, 712, 140, "SN")
    o.append('</svg>')
    return "\n".join(o)

ARCH_CSS = """pre.req { white-space: pre-wrap; overflow-wrap: anywhere; background: #f6f3ee; border: 1px solid #ddd6cc; border-radius: 6px; padding: 12px 16px; font-size: 0.92em; line-height: 1.45; margin: 0 0 1.4em }
""" + """
.blk rect { fill:#f3f2ed; stroke:#b9b8ae; stroke-width:1.2; }
.blk text { fill:#0b0b0b; } .blk.sub rect { fill:#f9f9f7; stroke:#d5d4cb; } .blk.sub text { fill:#52514e; }
.blk.hl rect { fill:#ffe1cc; stroke:#eb6834; stroke-width:2.4; } .blk.hl text { fill:#0b0b0b; font-weight:600; }
.dim .blk:not(.hl) rect { fill:#f7f7f4; stroke:#dcdbd3; } .dim .blk:not(.hl) text { fill:#9a9890; }
.lnk { stroke:#898781; stroke-width:1.4; } .lbl { fill:#898781; }
.ocard { display:grid; grid-template-columns:minmax(0,1fr) 320px; gap:14px 22px; align-items:start; }
.ocard .mini { position:sticky; top:8px; }
.ocard .mini svg { width:100%; height:auto; border:1px solid var(--grid); border-radius:6px; background:var(--surface); padding:4px; }
.ocard .mini .cap { font-size:12px; color:var(--ink2); margin-top:4px; }
@media (max-width:760px) { .ocard { grid-template-columns:1fr; } .ocard .mini { position:static; } }
details { margin:8px 0 4px; } summary { cursor:pointer; color:var(--s1); font-weight:600; }
details .rec p { font-size:13.5px; color:var(--ink2); max-width:none; }
.status { display:inline-block; font-size:12px; padding:1px 8px; border-radius:10px; margin-left:8px; vertical-align:middle; }
.st-explained { background:#e3f3e3; color:#1d5a1d; } .st-partly { background:#fff1d6; color:#7a4b00; } .st-open { background:#fbe9e2; color:#8a3a1c; }
.oneline { font-size:16px; font-weight:600; margin:4px 0 10px; max-width:none; }
.chips span { display:inline-block; font-size:11px; background:#efeee9; color:#52514e; border-radius:9px; padding:1px 7px; margin:0 4px 4px 0; }
h4 { font-size:14px; margin:12px 0 4px; color:var(--ink2); text-transform:uppercase; letter-spacing:.04em; }
ul.b { margin:4px 0 8px; padding-left:20px; } ul.b li { margin:3px 0; }
.lanes rect.work { fill:#2a78d6; } .lanes rect.wait { fill:none; stroke:#898781; stroke-dasharray:4 3; } .lanes rect.crit { fill:#eb6834; }
.glos dt { font-weight:600; } .glos { grid-template-columns:max-content 1fr; }
.round-table td:nth-child(n+2) { text-align:left; }
figure svg.chart { max-width:620px; margin:0 auto; }
.ocard table { width:100%; min-width:0; table-layout:fixed; } .ocard td, .ocard th { text-align:left !important; white-space:normal; word-wrap:break-word; }
.ocard col.c1 { width:38%; } .ocard col.c2 { width:20%; } .ocard col.c3 { width:42%; }
.rec table { table-layout:auto; width:auto; min-width:0; }
"""

# ---------------------------------------------------------------- charts
def dumbbell(rows, unit, before_label, after_label, title, w=560):
    """Paired before/after dots per row, direct value labels, the gap annotated."""
    vals = [v for r in rows for v in (r.get("before"), r.get("after")) if isinstance(v, (int, float))]
    if not vals: return ""
    lo, hi = 0, max(vals) * 1.18 or 1
    L, R, top, rh = 190, w - 70, 34, 26
    H = top + rh * len(rows) + 30
    o = [f'<svg class="chart" viewBox="0 0 {w} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(title)}">']
    X = lambda v: L + (v - lo) / (hi - lo) * (R - L)
    # grid
    step = nice_step(hi)
    v = 0
    while v <= hi:
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 10}" x2="{X(v):.1f}" y2="{H - 26}" stroke="#e1e0d9"/>')
        o.append(f'<text x="{X(v):.1f}" y="{H - 12}" text-anchor="middle" font-size="10" fill="#898781">{fmtn(v)}</text>')
        v += step
    o.append(f'<text x="{w - 70}" y="{H - 12}" text-anchor="end" font-size="10" fill="#898781"> {esc(unit)}</text>')
    # legend
    o.append(f'<circle cx="{L}" cy="14" r="5" fill="#2a78d6"/><text x="{L + 10}" y="18" font-size="11" fill="#52514e">{esc(before_label)}</text>')
    lx = L + 14 + 6.5 * len(before_label) + 18
    o.append(f'<circle cx="{lx:.0f}" cy="14" r="5" fill="#eb6834"/><text x="{lx + 10:.0f}" y="18" font-size="11" fill="#52514e">{esc(after_label)}</text>')
    for i, r in enumerate(rows):
        y = top + i * rh + 12
        b, a = r.get("before"), r.get("after")
        o.append(f'<text x="{L - 8}" y="{y + 4}" text-anchor="end" font-size="11" fill="#0b0b0b">{esc(r["label"])}</text>')
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            o.append(f'<line x1="{X(b):.1f}" y1="{y}" x2="{X(a):.1f}" y2="{y}" stroke="#c3c2b7" stroke-width="2"/>')
            ratio = (a / b) if b else None
            if ratio and abs(ratio - 1) >= 0.03:
                mx = (X(a) + X(b)) / 2
                o.append(f'<text x="{mx:.1f}" y="{y - 7}" text-anchor="middle" font-size="10" fill="#52514e">{ratio:.2f}x</text>')
        for v, c, anchor, dx in ((b, "#2a78d6", "end", -8), (a, "#eb6834", "start", 8)):
            if isinstance(v, (int, float)):
                if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a < b: anchor, dx = ("start", 8) if c == "#2a78d6" else ("end", -8)
                o.append(f'<circle cx="{X(v):.1f}" cy="{y}" r="5" fill="{c}" stroke="#fcfcfb" stroke-width="1.5"/>')
                o.append(f'<text x="{X(v) + dx:.1f}" y="{y + 4}" text-anchor="{anchor}" font-size="10.5" fill="#0b0b0b">{fmtn(v)}</text>')
    o.append('</svg>')
    return "\n".join(o)

def bars(rows, unit, title, w=560):
    vals = [r.get("value") for r in rows if isinstance(r.get("value"), (int, float))]
    if not vals: return ""
    hi = max(vals) * 1.18 or 1
    L, R, top, rh = 190, w - 70, 14, 24
    H = top + rh * len(rows) + 30
    X = lambda v: L + v / hi * (R - L)
    o = [f'<svg class="chart" viewBox="0 0 {w} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(title)}">']
    step = nice_step(hi); v = 0
    while v <= hi:
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 6}" x2="{X(v):.1f}" y2="{H - 26}" stroke="#e1e0d9"/>')
        o.append(f'<text x="{X(v):.1f}" y="{H - 12}" text-anchor="middle" font-size="10" fill="#898781">{fmtn(v)}</text>')
        v += step
    o.append(f'<text x="{w - 70}" y="{H - 12}" text-anchor="end" font-size="10" fill="#898781"> {esc(unit)}</text>')
    for i, r in enumerate(rows):
        y = top + i * rh
        val = r.get("value")
        o.append(f'<text x="{L - 8}" y="{y + 15}" text-anchor="end" font-size="11" fill="#0b0b0b">{esc(r["label"])}</text>')
        if isinstance(val, (int, float)):
            o.append(f'<rect x="{L}" y="{y + 4}" width="{max(X(val) - L, 1):.1f}" height="14" rx="3" fill="#2a78d6"/>')
            o.append(f'<text x="{X(val) + 6:.1f}" y="{y + 15}" font-size="10.5" fill="#0b0b0b">{fmtn(val)}</text>')
    o.append('</svg>')
    return "\n".join(o)

def nice_step(hi):
    raw = hi / 5
    for s in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000):
        if s >= raw: return s
    return raw

def fmtn(v):
    if isinstance(v, int) or float(v).is_integer(): return f"{int(v):,}"
    return f"{v:,.3g}" if abs(v) < 100 else f"{v:,.0f}"

# ---------------------------------------------------------------- the rounds timeline
ROUNDS = [("run 1", "run 1"), ("run 2", "run 2"), ("control run", "control"), ("run 3", "run 3"), ("boot A", "A"), ("boot B", "B"), ("boot C", "C"), ("boot D", "D"), ("boot E", "E"), ("boot F1", "F1"), ("boot F2", "F2"), ("run 7 (proposed)", "run 7")]
RX = [(re.compile(p), i) for p, i in (
    (r"run 7|proposed|not yet run|not run|planned|next run", 11),
    (r"boot f2|\b012\b", 10), (r"boot f1|\b011\b|run 6", 9), (r"boot e|\b010\b", 8), (r"boot d|\b008\b", 7), (r"boot c|\b007\b", 6), (r"boot b|\b006\b", 5), (r"boot a|\b005\b|run 4|run 5", 4),
    (r"run 3|\b004\b", 3), (r"control|\b003\b", 2), (r"run 2|\b002\b", 1), (r"run 1|\b001\b", 0))]
def round_cols(s):
    s = s.lower(); cols = set()
    for rx, i in RX:
        if rx.search(s): cols.add(i)
    return cols

def timeline_svg(items):
    """One row per outlier: a filled dot where it was first seen, open squares where tests were added, the status at the right."""
    cw, L, top, rh = 54, 300, 46, 15
    W = L + cw * len(ROUNDS) + 90
    H = top + rh * len(items) + 16
    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Rounds timeline">']
    for i, (_, short) in enumerate(ROUNDS):
        x = L + cw * i + cw / 2
        o.append(f'<text x="{x:.0f}" y="18" text-anchor="middle" font-size="10.5" fill="#52514e">{esc(short)}</text>')
        o.append(f'<line x1="{x:.0f}" y1="26" x2="{x:.0f}" y2="{H - 8}" stroke="#e1e0d9"/>')
    o.append(f'<text x="{L + cw * 4 + cw / 2:.0f}" y="34" text-anchor="middle" font-size="9.5" fill="#898781">run 4 boots</text>')
    o.append(f'<text x="{L + cw * 9 + cw:.0f}" y="34" text-anchor="middle" font-size="9.5" fill="#898781">run 6</text>')
    for j, it in enumerate(items):
        y = top + j * rh + 6
        o.append(f'<a href="#{it["id"]}"><text x="{L - 8}" y="{y + 4}" text-anchor="end" font-size="10" fill="#2a78d6">{esc(it["num"] + " " + shorten(it["title"], 44))}</text></a>')
        o.append(f'<line x1="{L}" y1="{y}" x2="{L + cw * len(ROUNDS)}" y2="{y}" stroke="#f0efe9"/>')
        for c in it["test_cols"]:
            x = L + cw * c + cw / 2
            o.append(f'<rect x="{x - 4:.0f}" y="{y - 4}" width="8" height="8" fill="#fcfcfb" stroke="#eb6834" stroke-width="1.5"/>')
        for c in it["seen_cols"]:
            x = L + cw * c + cw / 2
            o.append(f'<circle cx="{x:.0f}" cy="{y}" r="4.5" fill="#2a78d6"/>')
        col = {"explained": "#1baf7a", "partly explained": "#eda100", "open": "#eb6834"}[it["status"]]
        o.append(f'<circle cx="{L + cw * len(ROUNDS) + 14}" cy="{y}" r="4" fill="{col}"/>')
        o.append(f'<text x="{L + cw * len(ROUNDS) + 22}" y="{y + 3.5}" font-size="9.5" fill="#52514e">{esc(it["status"])}</text>')
    o.append('</svg>')
    return "\n".join(o)

def shorten(s, n): return s if len(s) <= n else s[:n - 1].rstrip() + "..."

# ---------------------------------------------------------------- page pieces
def ul(items): return "<ul class=\"b\">" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"

def status_chip(st):
    cls = {"explained": "st-explained", "partly explained": "st-partly", "open": "st-open"}[st]
    return f'<span class="status {cls}">{esc(st)}</span>'

def sentences_to_bullets(text, n=6):
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[])", text) if p.strip()]
    return parts[:n] + (["(continued in the full record below)"] if len(parts) > n else [])

def outlier_section(k, i):
    e = ENTRIES[i]["outlier"]; p = POL.get(i)
    num = f"4.{k}"
    blocks = [ALIAS.get(b, b) for b in e["blocks"]]
    seen = set(); blocks = [b for b in blocks if not (b in seen or seen.add(b))]
    o = [f'<h3 id="{i}">{num} {esc(e["title"])}{status_chip(e["status"])}</h3>']
    o.append('<div class="ocard"><div class="main">')
    if p:
        o.append(f'<p class="oneline">{esc(p["one_line"])}</p>')
        o.append('<h4>What looked wrong</h4>' + ul(p["looked_wrong"]))
        o.append('<h4>Why it looked wrong</h4>' + ul(p["why_wrong"]))
        tests = p["tests"]
    else:
        o.append('<h4>What looked wrong</h4>' + ul(sentences_to_bullets(e["what_looked_wrong"])))
        o.append('<h4>Why it looked wrong</h4>' + ul(sentences_to_bullets(e["why_wrong"])))
        tests = e["tests_added"]
    o.append('<h4>Tests added to clarify it</h4>')
    if tests:
        o.append('<div class="tbl"><table><colgroup><col class="c1"><col class="c2"><col class="c3"></colgroup><tr><th>Test</th><th>Run or boot</th><th>What it measures</th></tr>')
        for t in tests: o.append(f'<tr><td>{esc(t["name"])}</td><td>{esc(t["run"])}</td><td>{esc(t["measures"])}</td></tr>')
        o.append('</table></div>')
    else:
        o.append('<p class="note">No test was added for this item.</p>')
    if p:
        o.append('<h4>What the tests showed</h4>' + ul(p["showed"]))
        if p.get("open"): o.append(f'<h4>Still open</h4><p>{esc(p["open"])}</p>')
        ch = p.get("chart") or {}
        rows = ch.get("rows") or []
        if ch.get("kind") == "dumbbell" and rows:
            svg = dumbbell(rows, ch.get("unit", ""), ch.get("before_label") or "before", ch.get("after_label") or "after", ch.get("title", ""))
            if svg: o.append(f'<figure>{svg}<figcaption><span class="take">{esc(ch.get("takeaway", ""))}</span> {esc(ch.get("title", ""))} [{esc("; ".join(sorted({r.get("source", "") for r in rows if r.get("source")})))}]</figcaption></figure>')
        elif ch.get("kind") == "bars" and rows:
            svg = bars(rows, ch.get("unit", ""), ch.get("title", ""))
            if svg: o.append(f'<figure>{svg}<figcaption><span class="take">{esc(ch.get("takeaway", ""))}</span> {esc(ch.get("title", ""))} [{esc("; ".join(sorted({r.get("source", "") for r in rows if r.get("source")})))}]</figcaption></figure>')
    else:
        o.append('<h4>What the tests showed</h4>' + ul(sentences_to_bullets(e["what_tests_showed"])))
    # the full record
    o.append('<details><summary>Full verified record (long form, with every number and source)</summary><div class="rec">')
    o.append(f'<p><b>First seen.</b> {esc(e["first_seen"])}</p><p><b>What looked wrong.</b> {esc(e["what_looked_wrong"])}</p><p><b>Why it looked wrong.</b> {esc(e["why_wrong"])}</p>')
    o.append('<p><b>Tests added.</b></p><ul>' + "".join(f'<li>{esc(t["name"])} [{esc(t["run"])}]: {esc(t["measures"])}</li>' for t in e["tests_added"]) + '</ul>')
    o.append(f'<p><b>What the tests showed.</b> {esc(e["what_tests_showed"])}</p>')
    if e["numbers"]:
        o.append('<div class="tbl"><table><tr><th>Number</th><th>Value</th><th>Unit</th><th>Source</th></tr>' + "".join(f'<tr><td>{esc(n["label"])}</td><td>{esc(n["value"])}</td><td>{esc(n["unit"])}</td><td>{esc(n["source"])}</td></tr>' for n in e["numbers"]) + '</table></div>')
    o.append(f'<p class="note">Sources: {esc("; ".join(e["sources"]))}. Verification: {esc(ENTRIES[i]["confidence"])}; {len(ENTRIES[i]["corrections"])} corrections applied by the verifier.</p>')
    o.append('</div></details>')
    o.append('</div><div class="mini">')
    o.append(f'<div class="dim">{arch_svg(blocks, idp="o" + str(k))}</div>')
    o.append(f'<div class="cap">Highlighted: {esc(", ".join(blocks))}.</div>')
    o.append('</div></div>')
    return "\n".join(o)

def glossary():
    seen = {}
    for i in IDS:
        for t in (POL.get(i) or {}).get("terms", []):
            k = re.sub(r"\s+", " ", t["term"].strip()).strip(".")
            if not k or len(k) > 40: continue
            e = seen.setdefault(k.lower(), {"term": k, "defs": [], "n": 0})
            e["n"] += 1; e["defs"].append(t["definition"])
    terms = {e["term"]: min(e["defs"], key=len) for e in seen.values() if e["n"] >= 2}
    base = {
        "DSU": "DynamIQ Shared Unit: the two-core cluster with its shared L2, L3, CME and one mesh port.",
        "CME": "Compute Matrix Engine, the Arm C1-SME2 unit: one per cluster, runs streaming-mode (SME) loads, stores and matrix instructions with its own 64 KiB L1 data cache.",
        "CMN S3": "Arm's coherent mesh network: a 6 by 6 grid of crosspoints that connects clusters, home nodes and memory bridges.",
        "home node (HN-S)": "The mesh node that owns an address: it keeps the snoop filter and the SLC slice for that address. Asimov has five.",
        "SLC": "System Level Cache: the cache inside each home node, 1 MiB in 16 ways; 12 ways (768 KiB) cache DRAM lines after the OCM lock.",
        "OCM": "On-Chip Memory: 4 of the 16 SLC ways of each home node locked as 256 KiB of addressable memory (five regions, 1.25 MiB).",
        "chase (chain walk)": "A chain of dependent loads: each load's result is the next address, so one load must finish before the next starts. It measures latency.",
        "repeated chain / fresh chain / flushed chain": "Repeated: the same random chain walked many times (later walks hit whatever cache holds it). Fresh: walked once. Flushed: every line cleaned and invalidated (DC CIVAC) first.",
        "sparse (one line per page) / dense (every line)": "Sparse OCM chains use one line per 4 KiB page, so a prefetcher cannot fetch a neighbour that the chain will use. Dense chains use every line of the region.",
        "refills per load": "PMU counts of cache line fills per load: 0x03 L1 refills, 0x17 L2 refills, 0xA2 L3 read refills (a line the L3 fetched from the mesh).",
        "prefetcher": "Hardware that fetches lines before a load asks for them, after it detects a pattern (a stream or a stride) in the addresses.",
        "in flight": "Issued and not yet returned: the number of reads a core, a prefetcher or a cluster keeps open at once.",
        "snoop-filter-only mode": "The L3 state on runs 1 to 3 and boots A to D: the L3 RAM keeps only the snoop filter, so no line is stored there and every L2 miss goes to the mesh.",
        "SCP / TF-A": "SCP: the system control processor firmware, which stages each cluster's L3 mode. TF-A: Trusted Firmware-A, the EL3 firmware; a rebuilt TF-A turned the prefetchers off on boots B, D and F2.",
        "bracket / span": "Bracket: the time between two timer reads around a whole call. Span: run 6's second pair of stamps inside the call, around the data loop only.",
        "est.": "An estimate: a number derived from other measurements, not read from a counter or a timer.",
        "asimov-bench": "An earlier benchmark run by another team on an older RTL; its numbers are the reference the first runs were compared with.",
        "CRB": "The Arm Neoverse V3AE reference server used to test the benchmark programs before the emulator runs.",
    }
    for k, v in base.items():
        terms.setdefault(k, v)
    return "<dl class=\"glos\">" + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in sorted(terms.items(), key=lambda kv: kv[0].lower())) + "</dl>"

# ---------------------------------------------------------------- authored sections (typed in from the verified fact sheets)
LADDER = [("L1 data (4 to 24 KiB chain)", 2.002, "4.0 cycles", "boot E, run 3, F1: latency-dram-small.csv"),
          ("L2 (128 KiB chain)", 6.023, "12.1 cycles", "boot E latency-dram-small.csv"),
          ("L3 hit (derived)", 10.8, "22 cycles est.", "boot E 256 and 384 KiB rows, hit set"),
          ("SLC (2 MiB fresh chain)", 24.177, "48 cycles", "boot E latency-dram-large.csv"),
          ("OCM (all five regions, every line)", 26.082, "52 cycles", "boot E latency-ocm-all5-dense-cpu2.csv"),
          ("DRAM (8 MiB chain, every line flushed)", 52.659, "105 cycles", "boot E latency-dram-flushed.csv"),
          ("CME round trip, no memory access", 21.005, "42 CME cycles", "boot E cme-latency rows")]

def ladder_svg(w=720):
    hi = 60; L, R, top, rh = 250, w - 150, 10, 26
    H = top + rh * len(LADDER) + 28
    X = lambda v: L + v / hi * (R - L)
    o = [f'<svg viewBox="0 0 {w} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Measured latency ladder">']
    for v in range(0, 61, 10):
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 4}" x2="{X(v):.1f}" y2="{H - 22}" stroke="#e1e0d9"/><text x="{X(v):.1f}" y="{H - 8}" text-anchor="middle" font-size="10" fill="#898781">{v}</text>')
    o.append(f'<text x="{R + 18}" y="{H - 8}" font-size="10" fill="#898781">ns per load</text>')
    for i, (lab, v, cyc, src) in enumerate(LADDER):
        y = top + i * rh
        c = "#6250d6" if "CME" in lab else ("#eda100" if "est." in cyc else "#2a78d6")
        o.append(f'<text x="{L - 8}" y="{y + 15}" text-anchor="end" font-size="11">{esc(lab)}</text>')
        o.append(f'<rect x="{L}" y="{y + 4}" width="{X(v) - L:.1f}" height="14" rx="3" fill="{c}"/>')
        o.append(f'<text x="{X(v) + 6:.1f}" y="{y + 15}" font-size="10.5">{v:.1f} ns = {esc(cyc)}</text>')
    o.append('</svg>')
    return "\n".join(o)

def lanes_svg(w=900):
    """Wall-clock lanes: how a prefetcher overlaps DRAM reads. Durations to scale (1 ns = 5 px); interleaving schematic."""
    px = 4.4; L = 340; T = 52.7
    o = [f'<svg viewBox="0 0 {w} 300" xmlns="http://www.w3.org/2000/svg" class="lanes" role="img" aria-label="Wall-clock lanes of three read patterns">']
    for t in range(0, 121, 20):
        x = L + t * px
        o.append(f'<line x1="{x:.0f}" y1="22" x2="{x:.0f}" y2="270" stroke="#e1e0d9"/><text x="{x:.0f}" y="286" text-anchor="middle" font-size="10" fill="#898781">{t} ns</text>')
    def lane(y, title, sub):
        o.append(f'<text x="8" y="{y + 4}" font-size="11.5" font-weight="600">{esc(title)}</text><text x="8" y="{y + 18}" font-size="10" fill="#52514e">{esc(sub)}</text>')
    # lane 1: dependent chain
    lane(44, "Dependent chain, any boot", "one load open at a time: 52.7 ns each")
    for k in range(2):
        x = L + k * T * px
        o.append(f'<rect class="crit" x="{x:.0f}" y="36" width="{T * px:.0f}" height="12" rx="2"/>')
        o.append(f'<text x="{x + 4:.0f}" y="46" font-size="9.5" fill="#fff">load {k + 1}: 52.7 ns, waits for DRAM</text>')
    # lane 2: plain loop, prefetchers off
    lane(104, "Independent reads, prefetchers off (boot B)", "about 2 lines in flight: 2.38 GB/s = one line per 26.9 ns")
    for k in range(3):
        x = L + k * 26.9 * px
        o.append(f'<rect class="wait" x="{x:.0f}" y="{88 + (k % 2) * 14}" width="{T * px:.0f}" height="11" rx="2"/>')
        o.append(f'<rect class="work" x="{x:.0f}" y="{88 + (k % 2) * 14}" width="3" height="11"/>')
    # lane 3: prefetcher on, L3 on
    lane(190, "Independent reads, prefetchers on, L3 on (boot E)", "about 21 reads in flight est.: one line per 2.49 ns")
    for k in range(22):
        x = L + k * 2.49 * px
        yy = 150 + (k % 8) * 9
        o.append(f'<rect class="wait" x="{x:.0f}" y="{yy}" width="{T * px:.0f}" height="7" rx="1"/>')
        o.append(f'<rect class="work" x="{x:.0f}" y="{yy}" width="2.5" height="7"/>')
    o.append(f'<text x="{L}" y="244" font-size="10" fill="#52514e">Dashed box: one 64-byte line waiting 52.7 ns for DRAM. Solid tick: the request is issued.</text>')
    o.append(f'<text x="{L}" y="258" font-size="10" fill="#52514e">In row 3 the loads do not wait: the line is in the L1 when the loop reaches it (0.9997 L1 prefetch refills per load).</text>')
    o.append('</svg>')
    return "\n".join(o)

def l3_dumbbell():
    rows = [{"label": "48 KiB (L2)", "before": 17.483, "after": 27.299}, {"label": "96 KiB (L2)", "before": 12.057, "after": 26.877},
            {"label": "256 KiB (L2 and L3)", "before": 10.164, "after": 26.297}, {"label": "2 MiB (SLC)", "before": 9.311, "after": 25.044},
            {"label": "32 MiB (DRAM)", "before": 9.172, "after": 24.575}]
    return dumbbell(rows, "GB/s, one core reading", "run 3: L3 off (snoop filter only)", "boot F1: L3 on", "One-core read rate, run 3 against boot F1")

def pf_dumbbell():
    rows = [{"label": "2 MiB, plain loop", "before": 5.031, "after": 9.294}, {"label": "32 MiB, plain loop", "before": 2.377, "after": 9.196},
            {"label": "2 MiB, PRFM 4 lines ahead", "before": 12.146, "after": 9.651}, {"label": "32 MiB, PRFM 4 lines ahead", "before": 6.334, "after": 9.339}]
    return dumbbell(rows, "GB/s, one core reading, L3 off", "boot B: prefetchers off", "boot C: prefetchers on", "One-core read rate with the hardware prefetchers off and on")

def chain_dumbbell():
    rows = [{"label": "192 KiB", "before": 14.045, "after": 7.825}, {"label": "256 KiB", "before": 19.333, "after": 9.509}, {"label": "384 KiB", "before": 22.729, "after": 10.986},
            {"label": "128 KiB (L2, control)", "before": 6.090, "after": 6.014}, {"label": "2 MiB (SLC, control)", "before": 24.096, "after": 23.714}]
    return dumbbell(rows, "ns per load, repeated chain", "run 3: L3 off", "boot F1: L3 on", "Repeated chains at the L3 sizes, run 3 against boot F1")

def rounds_table():
    rows = [("run 1", "001", "2026-10-31", "first full sweep: chains, flushed rows, OCM, bandwidth", "flushed rows read DRAM; OCM survives a flush; OCM write row timed the flush; per-region OCM rows hold prefetched lines; OCM 18.5 ns against asimov-bench 14.4; DRAM 52 ns against 31.65; L3 rows look like SLC; one core reads 9 GB/s"),
            ("run 2", "002", "2026-11-02", "fresh chains, one flushed 8 MiB row, mesh counters around commands, OCM per region and CPU", "mesh requests per line; CPU 6 and CPU 8 port placement; OCM cell spread follows mesh distance; node 344 extra requests"),
            ("control run", "003", "2026-11-02", "run 2 repeated on the run 1 firmware", "the hemisphere write limit moved with the firmware"),
            ("run 3", "004", "2026-11-03", "sparse OCM chains, CME rows, PMU prefetch events, 8-core rows", "CME chain 21 ns against the round trip; CME flushed below fresh; CME per-call cost; L1 read 58 of 64 GB/s; sparse against dense gap"),
            ("run 4 boots A to D", "005 to 008", "2026-11-04 to 05", "A: hypothesis rows; B: prefetchers off; C: sequential chains and PRFM; D: prefetchers off plus 64 KiB OCM hint", "L3 held no data (register 0x0); sequential chain 2.5 ns; walks per load; software prefetch slower with hardware prefetchers on"),
            ("boot E", "010", "2026-11-05", "rebuilt SCP: L3 in full mode", "read streams 2.7 times faster; L3 hit about 10.8 ns est.; CME slower at small sizes with the L3 on; large chains slower"),
            ("run 6 boots F1, F2", "011, 012", "2026-11-06", "run 3's rows with the L3 on (F1); CME rows with prefetchers off (F2); in-span stamps", "CME writes fall with the L3 on; F1 against run 3 moved rows; stamp cost in the per-call number; F2 sweep time outside the walks"),
            ("run 7 (proposed)", "", "", "home-node queue occupancy, stamp-free per-call row, prefetchers-off core sweep with the L3 on", "the open items below")]
    return '<div class="tbl"><table class="round-table"><tr><th>Round</th><th>Folder</th><th>Date</th><th>What it added</th><th>Outliers it raised or answered</th></tr>' + "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td><td>{esc(e)}</td></tr>" for a, b, c, d, e in rows) + "</table></div>"

# ---------------------------------------------------------------- assemble
def build():
    items = []
    for k, i in enumerate(IDS, 1):
        e = ENTRIES[i]["outlier"]; p = POL.get(i)
        tests = p["tests"] if p else e["tests_added"]
        tcols = set()
        for t in tests: tcols |= round_cols(t["run"])
        scols = round_cols(e["first_seen"]) or {0}
        scols = {min(scols)}
        items.append({"id": i, "num": f"4.{k}", "title": e["title"], "status": e["status"], "seen_cols": scols, "test_cols": tcols - scols, "blocks": e["blocks"]})
    n_expl = sum(1 for x in items if x["status"] == "explained"); n_part = sum(1 for x in items if x["status"] == "partly explained"); n_open = len(items) - n_expl - n_part
    toc_out = "".join(f'<li><a href="#{x["id"]}">{x["num"]} {esc(x["title"])}</a></li>' for x in items)
    sections = "\n".join(outlier_section(k, i) for k, i in enumerate(IDS, 1))
    today = datetime.date.today().isoformat()
    H = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asimov Outliers</title><style>
{CSS}{ARCH_CSS}
</style></head><body><main>
<h1>Asimov memory tests: the outliers, why they looked wrong, and the tests we added</h1>
<p class="meta">Written {today} from the histories of the two analysis sessions (asimov-04 and asimov-be), Jesse's README files for results 001 to 012, the run plans and the four report pages. Every number was checked against the result files by the verification pass; numbers marked est. are derived, not measured. Generated by gen_outliers.py.</p>
<div class="short"><p><b>Short version.</b> Across six rounds of emulator runs, {len(items)} measured results did not make sense at first sight. Each one led to a question, a hypothesis and a new test in the next round. {n_expl} are now explained, {n_part} are narrowed to a named cause with a test still to run, and {n_open} are open.</p></div>
<nav class="toc"><b>Contents</b><ol>
<li><a href="#request">0. The request, as written</a></li>
<li><a href="#arch">1. Architecture overview</a><ol><li><a href="#arch-blocks">1.1 The blocks</a></li><li><a href="#arch-lat">1.2 Measured latency per level</a></li><li><a href="#arch-gen">1.3 General ranges for a memory hierarchy</a></li><li><a href="#arch-bw">1.4 Measured bandwidth</a></li></ol></li>
<li><a href="#pf">2. Prefetchers</a><ol><li><a href="#pf-levels">2.1 Which levels have one</a></li><li><a href="#pf-timing">2.2 How a prefetch relates in time to the load</a></li><li><a href="#pf-inflight">2.3 How many can be in flight</a></li><li><a href="#pf-off">2.4 How the prefetchers were turned off</a></li></ol></li>
<li><a href="#rounds">3. The rounds: how each test led to the next</a></li>
<li><a href="#outliers">4. The outliers</a><ol>{toc_out}</ol></li>
<li><a href="#words">5. Words used here</a></li>
<li><a href="#sources">6. Sources and method</a></li>
</ol></nav>

<h2 id="request">0. The request, as written</h2>
<p>This is the prompt that asked for this page, copied without edits. It states what the page must contain.</p>
<pre class="req">{html.escape(REQUEST, quote=False)}</pre>

<h2 id="arch">1. Architecture overview</h2>
<h3 id="arch-blocks">1.1 The blocks</h3>
<p>Asimov is an Arm SoC under test on a Palladium emulator (a hardware emulator that runs the chip's RTL cycle by cycle). One hemisphere holds five clusters. Each cluster is a DSU (DynamIQ Shared Unit) with two Arm C1-Nano cores. The diagram below is the map used for every outlier in section 4: the blocks involved in an outlier are highlighted in orange.</p>
<figure>{arch_svg(idp="main")}<figcaption><span class="take">One cluster, one home node and the memory path, with the load cost at each level.</span> The same drawing is repeated beside each outlier with its blocks highlighted. Sizes and modes are from Jesse's README files (membench-jibin-004 and 011, Platform facts) and sysinfo.txt; the latencies are boot E's best rows.</figcaption></figure>
<ul class="b">
<li><b>Cores.</b> Ten C1-Nano cores, CPUs 0 to 9. CPUs 0 and 1 run the kernel. CPUs 2 to 9 are isolated for the tests. A C1-Nano is an in-order core that issues two 128-bit loads per cycle [C1-Nano Software Optimization Guide, section 2.33; README 011].</li>
<li><b>L1.</b> Each core has a 32 KiB data cache and a 32 KiB instruction cache with 64-byte lines, and a 16-entry L1 data TLB (the table that translates addresses) [sysinfo.txt of bootF1 lines 101 to 102]. The way count is not in any source on disk (sysfs prints 0).</li>
<li><b>L2.</b> One 128 KiB L2 per cluster, shared by its two cores [sysinfo.txt line 103]. So the L2 is a cluster cache here, not a per-core cache.</li>
<li><b>L3.</b> One 256 KiB L3 per cluster, one slice [sysinfo.txt line 104]. It has two modes. In snoop-filter-only mode the L3 RAM keeps only the snoop filter (the list of lines held by the cores) and stores no data. In full mode it stores data. The stock firmware put only cluster 0 in full mode, so on runs 1 to 3 and boots A to D the L3 of the measured cores held no data. Boot E's rebuilt SCP firmware put all clusters in full mode [README 006 and 010].</li>
<li><b>CME.</b> Each cluster has one CME (the Arm C1-SME2 unit) shared by its two cores. It runs the streaming-mode (SME) instructions. It has its own 64 KiB, 4-way L1 data cache with two 512-bit read paths, a 24-entry TLB and its own prefetcher. Its path to memory is CME L1D, then the cluster's L3, then the mesh. The core's L1 and L2 are not on that path [C1-SME2 TRM as cited on the CME page; cme_test output].</li>
<li><b>Mesh.</b> The clusters, home nodes and memory bridges sit on a CMN S3 mesh, a 6 by 6 grid of crosspoints. Each cluster has one mesh port (RN-F). A request travels 1 to 5 crosspoint steps to a home node [README 004, mesh map].</li>
<li><b>Home nodes, SLC and OCM.</b> Five home nodes (HN-S) own all addresses; a DRAM address belongs to one of them by a hash, so a buffer spreads over all five. Each home node has 1 MiB of SLC (System Level Cache) in 16 ways. The firmware locks 4 ways of each node as a 256 KiB OCM region (On-Chip Memory, addressable SRAM at 0xE0000000 plus n MiB). The other 12 ways, 768 KiB per node and 3.75 MiB in all, cache DRAM lines [README 004 Platform facts].</li>
<li><b>DRAM.</b> About 2 GiB of memory behind the mesh's SBSX bridges. On the emulator it is four Cadence AXI memory models, not real LPDDR. Every delay control on the four models is zero and the native response is 3 ns. Of the 52.7 ns a random load costs from the core, 23.7 to 24.2 ns is the home-node round trip and about 29 ns the leg beyond the home node, of which about 20 ns is RTL pipeline by Jesse's stage count (est.) [README 011, memory model answer].</li>
<li><b>Clock.</b> The cores run at 2.0 GHz nominal (2.003 GHz from the 4 KiB row: 4.01 cycles per 2.002 ns load). The timer runs at 1 GHz, so one tick is 1 ns and 2 cycles. The emulator is cycle-exact with no frequency scaling [README 004 and 011].</li>
</ul>

<h3 id="arch-lat">1.2 Measured latency per level</h3>
<p>A chain of dependent loads (a chase) gives the load-to-use time of a level. The figure shows the best row per level on boot E, where the L3 held data. The L3 value is derived from rows that mix L2 and L3 hits, so it is an estimate.</p>
<figure>{ladder_svg()}<figcaption><span class="take">Each level costs about twice the one before it, except the step from the SLC to DRAM, which costs 28.5 ns more.</span> L1 2.0 ns (4 cycles), L2 6.0 ns (12 cycles), L3 hit 10.8 ns est. (22 cycles est.), SLC 24.2 ns (48 cycles), OCM all five regions 26.1 ns (52 cycles), DRAM 52.7 ns (105 cycles) [latency-dram-small.csv, latency-dram-large.csv, latency-ocm-all5-dense-cpu2.csv, latency-dram-flushed.csv of 010]. A CME instruction that touches no memory costs 21.0 ns (42 cycles) round trip, so every CME load sits on top of that.</figcaption></figure>
<div class="tbl"><table><tr><th>Level</th><th>Footprint of the row</th><th>ns per load</th><th>Cycles at 2.003 GHz</th><th>Boot and file</th></tr>
<tr><td>L1 data</td><td>4 to 24 KiB repeated chain</td><td>2.002</td><td>4.0</td><td>the same on every boot; latency-dram-small.csv</td></tr>
<tr><td>L2</td><td>96 KiB / 128 KiB repeated chain</td><td>5.82 / 6.02</td><td>11.7 / 12.1</td><td>boot E latency-dram-small.csv</td></tr>
<tr><td>L3 (data held)</td><td>192 / 256 / 384 KiB repeated chain, 47 / 75 / 92 % L3 hits</td><td>7.82 / 9.53 / 11.00</td><td>15.7 / 19.1 / 22.0</td><td>boot E latency-dram-small-l3.csv; L3 hit about 10.8 ns est.</td></tr>
<tr><td>L3 (no data)</td><td>the same rows on run 3</td><td>14.05 / 19.33 / 22.73</td><td>28.1 / 38.7 / 45.5</td><td>run 3 latency-dram-small.csv: L2 hits mixed with SLC reads</td></tr>
<tr><td>SLC</td><td>2 MiB fresh chain from CPU 2</td><td>24.18</td><td>48.4</td><td>boot E latency-dram-large.csv (F1 23.71)</td></tr>
<tr><td>OCM</td><td>all five regions, every line, from CPU 2</td><td>26.08</td><td>52.2</td><td>boot E latency-ocm-all5-dense-cpu2.csv</td></tr>
<tr><td>OCM, one region</td><td>one line per page, from CPU 2</td><td>21.4 to 25.8</td><td>43 to 52</td><td>boot E latency-ocm-region*-cpu2.csv (order follows mesh distance)</td></tr>
<tr><td>DRAM</td><td>8 MiB chain, every line flushed</td><td>52.66</td><td>105.5</td><td>boot E latency-dram-flushed.csv (run 3 52.74, F1 52.66)</td></tr>
<tr><td>CME round trip</td><td>no memory access</td><td>21.005</td><td>42.0</td><td>every boot; cme-latency rows</td></tr>
<tr><td>CME chain load</td><td>4 KiB / 64 KiB / 32 MiB</td><td>21.37 / 45.64 / 70.47</td><td>42.8 / 91.4 / 141.1</td><td>boot E cme-latency-dram-small.csv and -large.csv (prefetcher on)</td></tr>
</table></div>

<h3 id="arch-gen">1.3 General ranges for a memory hierarchy</h3>
<p>These ranges are what an engineer expects before measuring. They are the yardstick the outliers were judged against.</p>
<div class="tbl"><table><tr><th>Level</th><th>General range (modern cores)</th><th>Arm's own number for the C1-Nano</th><th>Asimov measured</th></tr>
<tr><td>L1 hit</td><td>1 to 5 cycles, about 1 ns</td><td>2 to 4 cycles (2 best case, 4 normal case)</td><td>4.0 cycles, 2.0 ns</td></tr>
<tr><td>L2 hit</td><td>10 to 20 cycles, 3 to 5 ns</td><td>10 to 12 cycles</td><td>12 cycles, 6.0 ns</td></tr>
<tr><td>L3 or last-level cache hit</td><td>30 to 75 cycles, 10 to 17 ns</td><td>not stated in the sources on disk</td><td>22 cycles est., 10.8 ns est. (cluster L3); 48 cycles, 24.2 ns (SLC in the mesh)</td></tr>
<tr><td>DRAM</td><td>150 to 300 cycles, 50 to 100 ns</td><td>not applicable (emulator memory model)</td><td>105 cycles, 52.7 ns, with every model delay at zero</td></tr>
</table></div>
<p class="note">General ranges: UVM CS2210 memory-hierarchy notes (L1 about 3 cycles, L2 10 to 15, L3 30 to 45, memory 150 to 300 at 3 GHz) and Chips and Cheese on the Cortex-A510 (L1 4 to 5 cycles, L2 9 to 13), both read 2026-11-08. Arm's numbers: C1-Nano Software Optimization Guide 109590, table 3-2. The DRAM number on Asimov says nothing about silicon: the memory model answers in a fixed time.</p>

<h3 id="arch-bw">1.4 Measured bandwidth</h3>
<p>Bandwidth rows stream independent reads, writes or copies over a buffer. Unlike a chain, a stream can keep many lines in flight, so its rate depends on the prefetchers and on the L3 mode as much as on the level.</p>
<figure>{l3_dumbbell()}<figcaption><span class="take">Turning the cluster L3 on made every one-core read stream 1.6 to 2.7 times faster, with the same lines fetched and the same mesh requests.</span> The chains beyond the L3, the writes and the controls did not move [bandwidth-dram-1core.csv of 004 and 011]. Why the L3 makes a stream faster is outlier 4.33.</figcaption></figure>
<div class="tbl"><table><tr><th>Row</th><th>Run 3 (L3 off)</th><th>Boot F1 (L3 on)</th><th>File</th></tr>
<tr><td>One core, L1 (16 KiB) read / write / copy</td><td>58.1 / 30.1 / 39.7 GB/s</td><td>56.1 / 30.6 / 39.4</td><td>bandwidth-dram-1core.csv</td></tr>
<tr><td>One core, DRAM (32 MiB) read / write</td><td>9.2 / 32.0 GB/s</td><td>24.6 / 32.0</td><td>bandwidth-dram-1core.csv</td></tr>
<tr><td>One core, prefetchers off, DRAM read</td><td>2.38 GB/s (boot B)</td><td>not run</td><td>bandwidth-read-prefetch.csv of 006</td></tr>
<tr><td>Four cores on four clusters, 16 MiB each, read / write</td><td>34.0 / 128.0 GB/s</td><td>98.1 / 128.0</td><td>bandwidth-perdsu.csv</td></tr>
<tr><td>All eight cores, 16 MiB each, read / write</td><td>66.7 / 152.2 GB/s</td><td>107.6 / 153.0</td><td>bandwidth-all8.csv</td></tr>
<tr><td>One core, one OCM region read</td><td>14.8 to 16.6 GB/s</td><td>19.9 to 20.1</td><td>bandwidth-ocm-region*.csv</td></tr>
<tr><td>CME, one core, 48 KiB read (in span) / DRAM read / write</td><td>104.9 (bracket) / 36.6 / 64 GB/s</td><td>104.6 / 36.6 / 52</td><td>cme-bandwidth-*.csv</td></tr>
</table></div>

<h2 id="pf">2. Prefetchers</h2>
<p>A prefetcher is hardware that fetches cache lines before a load asks for them. It watches the addresses of recent loads or misses, detects a pattern (a stream of consecutive lines, or a fixed stride), and issues its own reads ahead of the program. The prefetchers shaped more outliers than any other block, because they change what a row measures without changing the row.</p>
<h3 id="pf-levels">2.1 Which levels have one</h3>
<ul class="b">
<li><b>Core, L1 side.</b> A prefetcher fills the core's L1 data cache. Its fills are counted by event 0x81BC (L1 refills a hardware prefetcher asked for) and 0x0111 (L2 refills made for the L1 prefetcher's requests). On the 8 MiB sequential chain with every line flushed, both read 1.00 per load: every line entered the L1 at the prefetcher's request [boot A latency-dram-seq rows, 005].</li>
<li><b>Core, L2 side.</b> A second prefetcher fills the L2. Its fills are counted by 0x81BD. On the one-line-per-page OCM chains it fetched up to 2.98 extra lines per load while 0x81BC read 0 [boot A latency-ocm-region4-vary-cpu8.csv]. The Arm PMU lists five named data prefetchers for this core family: correlating, spatial, offset, stride and TLB descriptor (events 0x00D9 to 0x00DB, 0x010F, 0x0110). Which one fills which level is not stated in the sources on disk.</li>
<li><b>Cluster L3.</b> The predecessor core's manual (Cortex-A520 TRM) names L3 stride and offset prefetchers, and the C1-Nano PMU has event 0x0123 (L3 refills by L2-side prefetches). That event was never counted in these runs, so an L3-side prefetcher is neither shown nor excluded. Insufficient data: counting 0x0123 beside the refill set would show it.</li>
<li><b>CME.</b> The CME has its own prefetcher with 128 streams, indexed by instruction address. It fills the CME's L1D and the cluster L3, works in virtual addresses and keeps its own TLB [C1-SME2 TRM, as cited on the CME page]. Its fills are counted by CME event 0x32B2.</li>
<li><b>SLC, OCM, DRAM.</b> No prefetcher is documented at the home nodes or the memory models in the sources on disk.</li>
</ul>
<figure>{arch_svg(["L1-prefetcher", "L2-prefetcher", "CME-prefetcher"], idp="pf")}<figcaption><span class="take">Three prefetchers were measured: the core's L1-side and L2-side prefetchers and the CME's own.</span> An L3-side one may exist (event 0x0123 was never counted).</figcaption></figure>

<h3 id="pf-timing">2.2 How a prefetch relates in time to the load</h3>
<p>The prefetcher does not run at the same time as the load it helps. It runs ahead of it. It trains on the first loads or misses of a pattern, then issues reads for lines the program has not reached yet, independently of the demand loads. The demand load then finds the line in the cache, or finds it on its way in. The measurements below show the three cases.</p>
<figure>{lanes_svg()}<figcaption><span class="take">The prefetcher's gain is overlap: with it on and the L3 on, about 21 reads wait for DRAM at once (est.), so the loop sees one line every 2.49 ns instead of every 52.7 ns.</span> Durations to scale (1 ns = 4.4 px); the interleaving is schematic. Row 1: a dependent chain cannot overlap, on any boot. Row 2: the plain read loop with the prefetchers off keeps about 2 lines in flight (2.377 GB/s = one 64-byte line per 26.9 ns against a 52.2 ns DRAM load, boot B). Row 3: the sequential chain with the prefetchers on and the L3 on reads 2.492 ns per load, 0.9997 L1 prefetch refills per load (boot E, latency-dram-seq rows of 010); 52.7 / 2.49 = 21 reads in flight est.</figcaption></figure>
<ul class="b">
<li><b>Before the load (a stream or stride).</b> On the sequential chain every line still comes from DRAM once (1.00 L2 refills per load), but the load costs 2.49 ns instead of 52.7 ns. The lines arrive in the L1 before the chain reaches them [boot E, 010; boot C with the L3 off: 6.92 ns per load]. On the one-line-per-page OCM chains the L2-side prefetcher reacts to the page stride, not to the line offset inside the page: it fetched 1.8 to 2.2 extra lines per load with a fixed offset and 1.2 to 1.7 with a varying one [boot A, 005].</li>
<li><b>Never (a random dependent chain).</b> The next address is inside the line being read, so there is no pattern. Boot B (prefetchers off) is within -5.6 to +5.3 % of boot A on all 24 random chase rows from 4 KiB to 32 MiB. The chain latencies in section 1.2 are therefore the levels' own [latency-dram-small.csv and -large.csv of 005 and 006].</li>
<li><b>Partly before (a random chain over a small region).</b> On the per-region OCM chains of runs 1 and 2 (256 KiB, dense) the prefetcher fetched neighbours of the missed line that the chain used later: 0.74 to 0.96 L3 read refills per load instead of 1.00, so a quarter of the loads hit a line already brought in. That is why run 3 moved to one line per page [outliers 4.4 and 4.19].</li>
<li><b>Against the load (the CME).</b> Through the CME a random chain that fits the CME's 64 KiB L1 gets slower from 8 KiB on with the prefetcher on: 21.4 ns at 4 KiB, 24.9 at 8 KiB, 45.6 at 64 KiB, with 14 prefetched lines per load at 32 to 64 KiB. The prefetcher's fills evict the chain. With it off (boots B and F2) the chain reads 21.0 to 21.2 ns up to 64 KiB [cme-latency-dram-small.csv of 010 and 012; outlier 4.27].</li>
<li><b>Software hints.</b> A PRFM hint 4 lines ahead raises the plain loop from 2.38 to 6.33 GB/s with the hardware prefetchers off, adds 1.5 to 3.8 % with them on and the L3 off, and slows the loop with the L3 on (24.9 to 20.2 GB/s) [bandwidth-read-prefetch.csv of 006, 007, 010; outlier 4.41].</li>
</ul>
<figure>{pf_dumbbell()}<figcaption><span class="take">With the hardware prefetchers off a software hint more than doubles the plain loop; with them on it adds almost nothing.</span> Boot B against boot C, both with the L3 off, one core reading [bandwidth-read-prefetch.csv of 006 and 007].</figcaption></figure>

<h3 id="pf-inflight">2.3 How many can be in flight</h3>
<p>No counter in these runs reads the number of reads in flight. The numbers below are estimates by Little's law: rate times latency over 64 bytes per line.</p>
<div class="tbl"><table><tr><th>Case</th><th>Rate or time per line</th><th>Latency per line</th><th>Lines in flight (est.)</th><th>Source</th></tr>
<tr><td>Dependent random chain</td><td>one load at a time</td><td>52.7 ns</td><td>1</td><td>by construction</td></tr>
<tr><td>Plain read loop, prefetchers off, L3 off (boot B)</td><td>2.377 GB/s = 26.9 ns per line</td><td>52.2 ns</td><td>about 2</td><td>bandwidth-read-prefetch.csv of 006</td></tr>
<tr><td>Plain read loop, prefetchers on, L3 off (run 3, boot C)</td><td>9.2 GB/s = 7.0 ns per line</td><td>52.2 ns</td><td>about 7.5</td><td>bandwidth-dram-1core.csv of 004</td></tr>
<tr><td>Plain read loop, prefetchers on, L3 on (boot E, F1)</td><td>24.6 GB/s = 2.6 ns per line</td><td>52.7 ns</td><td>about 20</td><td>bandwidth-dram-1core.csv of 011</td></tr>
<tr><td>Sequential chain, prefetchers on, L3 on (boot E)</td><td>2.49 ns per load</td><td>52.7 ns</td><td>about 21</td><td>latency-dram-seq rows of 010</td></tr>
<tr><td>CME read stream from DRAM, prefetcher on (F1)</td><td>36.6 GB/s = 1.75 ns per line</td><td>62.1 ns (CME flushed 8 MiB chain, boot E)</td><td>about 35</td><td>cme-bandwidth-dram-1core.csv of 011</td></tr>
</table></div>
<ul class="b">
<li><b>Arm's documented limit for the predecessor core.</b> The Cortex-A520 TRM gives the core's L2 interface 31 outstanding read transactions (single-slice L2). The C1-Nano and C1-DSU manuals are not on disk, so Asimov's own limits per core, per cluster and for the CME are Insufficient data. The measurement that would give them: the home nodes' read-queue occupancy event (PMU_HNF_POCQ_OCCUPANCY) around the same one-core read on an L3-on and an L3-off boot, proposed for run 7 [follow-up-run-plan.md section 14].</li>
<li><b>What the L3 changes.</b> With the L3 on the same stream keeps about 20 lines in flight instead of 7.5, with the same refills per line and 0.975 times the mesh requests. So the L3's full mode lets more read requests stay open, by a mechanism not yet measured [outlier 4.33].</li>
</ul>

<h3 id="pf-off">2.4 How the prefetchers were turned off</h3>
<ul class="b">
<li>Boots B, D and F2 ran a rebuilt TF-A (0.35.0-pfoff.1). At the end of every power-on of CPUs 2 to 9 it sets IMP_CPUECTLR_EL1 bit 48 (ALLPFDIS: disable all data-side prefetchers) and IMP_CMECFG_EL1 bit 28 (PF_DISABLE for the CME prefetcher), reads both back and prints one line on the console [README 006, which quotes uart_1.log lines 104 to 111].</li>
<li>The check that it worked: boot B's sequential chain reads 52.76 ns per load against boot A's 6.92 ns, and the prefetch refill columns read 0.0000 in 558 of 559 latency rows [006 latency-dram-flushed.csv and the latency files].</li>
<li>Linux cannot make these writes itself: the registers are EL3-only, so the change needed firmware.</li>
</ul>

<h2 id="rounds">3. The rounds: how each test led to the next</h2>
<p>Each round answered some questions and raised new ones. The table lists what each round added and which outliers it touched. The figure below it places every outlier on the rounds: a blue dot where it was first seen, an orange square where a test for it ran, and its status at the right.</p>
{rounds_table()}
<figure>{timeline_svg(items)}<figcaption><span class="take">Most outliers were raised by runs 1 and 3 and answered by the run 4 boots and boot E; run 6 raised a new set around the CME and the L3.</span> Blue dot: first seen. Orange square: a test for it ran in that round (or is proposed for run 7). Right: status. Click a label to jump to the outlier.</figcaption></figure>

<h2 id="outliers">4. The outliers</h2>
<p>In order of first appearance. Each item has four parts: what looked wrong, why it looked wrong (the expectation it contradicted), the tests added, and what they showed. The small diagram marks the blocks involved. The full verified record with every number and source folds out under each item.</p>
{sections}

<h2 id="words">5. Words used here</h2>
{glossary()}

<h2 id="sources">6. Sources and method</h2>
<ul class="b">
<li>The two session histories (asimov-04 and asimov-be, 2026-10-30 to 2026-11-08), distilled to their user and assistant turns.</li>
<li>Jesse's README.md in results/membench-jibin-001 to 012, and the result CSV files, log.txt, sysinfo.txt and uart logs in those folders.</li>
<li>The run plans and reviews: RUN2-PLAN.md, follow-up-run-plan.md, CME-plan.md, the codex review files, HANDOFF-2026-11-02.md, jibin-comments-perf-modeling.md.</li>
<li>The report pages: asimov-c1nano-perf.html, asimov-cme-perf.html, asimov-c1nano-run4.html, asimov-cme-run4.html, run1-report.html, ocm-interpretation.html, cme-survey.html.</li>
<li>Arm documents: C1-Nano Software Optimization Guide 109590 (on disk); C1-Nano TRM, C1-SME2 TRM 107831, C1-DSU TRM 107804 and CMN S3 TRM 107858 as cited by the pages (not on disk); Cortex-A520 TRM (predecessor core, public).</li>
<li>Method: 17 extraction passes (one per source slice) produced raw outlier lists; a merge pass joined duplicates into {len(items)} entries; one verification pass per entry recomputed every number from the CSV files; one rewrite and one check pass per entry produced the bullets. Numbers the sources disagree on are kept with both sources in the full record.</li>
</ul>
</main></body></html>"""
    open(OUT, "w", encoding="utf-8").write(H)
    print(f"wrote {OUT}: {len(H):,} bytes, {len(items)} outliers, {n_expl} explained, {n_part} partly, {n_open} open")

CSS = open(A + "/asimov-c1nano-perf.html", encoding="utf-8").read().split("<style>")[1].split("</style>")[0]

if __name__ == "__main__":
    build()
