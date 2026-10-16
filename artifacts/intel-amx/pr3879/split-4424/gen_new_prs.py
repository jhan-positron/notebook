#!/usr/bin/env python3
"""Generate new-PRs.html: what the four proposed PRs are and how they relate to PR 4424.

All diagrams are inline SVG built here with computed coordinates, so cairosvg can render them for a visual check.
Run: python3 -I gen_new_prs.py   (writes new-PRs.html next to this script and svg/*.svg for inspection)
"""
import os, html

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "new-PRs.html")
SVGDIR = os.path.join(HERE, "svg")
os.makedirs(SVGDIR, exist_ok=True)

# ---- palette (dataviz reference instance, light mode) ----
C = {
    "text": "#1b1b1b", "muted": "#52514e", "surface": "#fcfcfb", "panel": "#f4f3ef", "rule": "#d9d7cf",
    "pr1": "#2a78d6", "pr2": "#eb6834", "pr3": "#1baf7a", "pr4": "#eda100", "pr4text": "#8a5d00",
    "gray": "#8b8a84", "grayfill": "#c9c8c0", "base": "#6b6a64",
}
PRC = [C["pr1"], C["pr2"], C["pr3"], C["pr4"]]
PRN = ["PR-1", "PR-2", "PR-3", "PR-4"]

FONT = "font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"


def esc(s):
    return html.escape(s, quote=True)


def text(x, y, s, size=12, fill=None, anchor="start", weight=None, mono=False, extra=""):
    fill = fill or C["text"]
    fam = "font-family:ui-monospace,SFMono-Regular,Menlo,monospace" if mono else FONT
    w = f"font-weight:{weight};" if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="{fam};font-size:{size}px;{w}" '
            f'fill="{fill}" {extra}>{esc(s)}</text>')


# ------------------------------------------------------------------------------------------------
# Figure 1: what PR 4424 contains, and which PR each part goes to (proportional blocks)
# Concern sizes = added lines at the head 0a5334ccb6 vs the merge base (hunk classification, non-blank lines).
# ------------------------------------------------------------------------------------------------
CONCERNS = [
    # key, label, added lines, PR index
    ("L", "L  K VNNI layout, storage, views, per-row store", 1026, 0),
    ("R", "R  AVX-512 reader", 427, 0),
    ("G", "G  FPGA staging", 37, 0),
    ("B", "B  build, CI flag, README, cost rows", 30, 0),
    ("A", "A  AMX kernel on the plane", 247, 1),
    ("S", "S  shared block save", 813, 2),
    ("T", "T  row-major tail block + hardware-attention policy", 1338, 3),
]


def fig_decomposition():
    W = 940
    left, right = 24, 24
    top = 56
    total = sum(c[2] for c in CONCERNS)
    barw = W - left - right
    y = top
    h = 54
    parts = []
    parts.append(text(left, 24, "PR 4424 at its head 0a5334ccb6: 3,918 non-blank added lines, labeled by concern", 14, weight=600))
    parts.append(text(left, 42, "block width = added lines; color = the PR of the new stack that carries the block", 12, C["muted"]))
    x = left
    gap = 2
    for key, label, n, pr in CONCERNS:
        w = barw * n / total
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w-gap,1):.1f}" height="{h}" fill="{PRC[pr]}" rx="3" ry="3"/>')
        # label inside when wide enough, else below with a tick
        if w > 46:
            parts.append(text(x + (w - gap) / 2, y + 23, key, 15, "#ffffff" if pr != 3 else C["text"], "middle", 700))
            parts.append(text(x + (w - gap) / 2, y + 41, f"{n:,}", 12, "#ffffff" if pr != 3 else C["text"], "middle"))
        x += w
    # second row: the PR boxes spanning their blocks
    y2 = y + h + 14
    x = left
    spans = {}
    for key, label, n, pr in CONCERNS:
        w = barw * n / total
        spans.setdefault(pr, [x, x])
        spans[pr][1] = x + w
        x += w
    sizes = {0: "PR-1  1,846 added lines", 1: "PR-2  277", 2: "PR-3  678", 3: "PR-4  1,466"}
    for pr in range(4):
        x0, x1 = spans[pr]
        parts.append(f'<path d="M{x0+1:.1f},{y2} v8 H{x1-3:.1f} v-8" fill="none" stroke="{PRC[pr]}" stroke-width="2"/>')
        lab = sizes[pr]
        anchor = "middle"
        cx = (x0 + x1) / 2
        if x1 - x0 < 90:
            anchor = "start" if pr == 1 else "middle"
        parts.append(text(cx, y2 + 24, lab, 12, C["text"] if pr != 3 else C["pr4text"], anchor, 600))
    # small-block legend (G and B are too narrow to label inside)
    y3 = y2 + 46
    parts.append(text(left, y3, "G (37 lines) and B (30 lines) are the two thin blocks inside PR-1. The PR sizes under the brackets are the real patch sizes", 11.5, C["muted"]))
    parts.append(text(left, y3 + 16, "(added lines by git numstat); they exceed the block sums by the temporary code and the comment rewrites the split adds.", 11.5, C["muted"]))
    H = y3 + 30
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="PR 4424 decomposed into seven concern blocks grouped into four PRs">' + "".join(parts) + "</svg>"
    return svg


# ------------------------------------------------------------------------------------------------
# Figure 2: lineage. PR 4424's history line and the four new PRs mapped onto it.
# ------------------------------------------------------------------------------------------------
def fig_lineage():
    W, H = 940, 456
    p = []
    p.append(text(24, 24, "How the four PRs relate to PR 4424's history", 14, weight=600))
    # top lane: history of jhan-amx-vnniK (first-parent line), left to right
    ly = 112
    nodes = [
        (120, "6b939d25d2", "layout + reader + staging\n+ AMX kernel + shared save\n(2694+/189-)"),
        (360, "ba69cb513e", "+ save_k worker fold\n(PR 4774, 91+/91-)"),
        (600, "9d5c7a389b", "+ tail block + policy\n(PR 4737, 1459+/113-)"),
        (840, "0a5334ccb6", "+ deb preset line\n(7+/2-) = head today"),
    ]
    p.append(text(24, ly - 62, "jhan-amx-vnniK (PR 4424), tested states on its first-parent line", 12, C["muted"]))
    p.append(f'<line x1="40" y1="{ly}" x2="900" y2="{ly}" stroke="{C["rule"]}" stroke-width="2"/>')
    for x, sha, lab in nodes:
        p.append(f'<circle cx="{x}" cy="{ly}" r="7" fill="{C["base"]}"/>')
        p.append(text(x, ly - 14, sha, 11.5, C["text"], "middle", mono=True))
        for i, line in enumerate(lab.split("\n")):
            p.append(text(x, ly + 22 + i * 14, line, 11, C["muted"], "middle"))
    # merged-in PRs as short branches
    for x, lab in [(240, "PR 4774 merged in 2026-10-08"), (480, "PR 4737 merged in 2026-10-08")]:
        p.append(f'<path d="M{x-40},{ly-30} Q{x+10},{ly-30} {x+120},{ly}" fill="none" stroke="{C["gray"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        p.append(text(x - 42, ly - 36, lab, 10.5, C["gray"]))
    # arrow from history to the stack
    sy = 276
    p.append(text(24, sy - 16, "The same content, cut into four stacked PRs", 12, C["muted"]))
    boxes = [
        (24, 212, "PR-1", "layout + AVX-512 reader\n+ FPGA staging + build\n1,846 added lines", "new tree 76a0160b72\n= ba69cb513e minus A, minus S"),
        (258, 212, "PR-2", "AMX kernel on the plane\n277 added lines", "new tree 4d3a042225\n= PR-1 plus the AMX diff"),
        (492, 212, "PR-3", "shared block save\n(with the worker fold)\n678 added lines", "= ba69cb513e: what PR 4774\nand the striping commits added"),
        (726, 212, "PR-4", "tail block + policy\n+ deb preset\n1,466 added lines", "= the PR 4737 merge diff\n+ the preset commit"),
    ]
    bh = 108
    for i, (x, w, name, lab, src) in enumerate(boxes):
        p.append(f'<rect x="{x}" y="{sy}" width="{w}" height="{bh}" fill="{C["panel"]}" stroke="{PRC[i]}" stroke-width="2.5" rx="6" ry="6"/>')
        tcol = C["pr4text"] if i == 3 else PRC[i]
        p.append(text(x + 12, sy + 22, name, 14, tcol, weight=700))
        for j, line in enumerate(lab.split("\n")):
            p.append(text(x + 12, sy + 42 + j * 15, line, 11.5))
        for j, line in enumerate(src.split("\n")):
            p.append(text(x + 12, sy + bh + 16 + j * 13, line, 10.5, C["muted"], mono=False))
        if i < 3:
            nx = boxes[i + 1][0]
            p.append(f'<path d="M{x+w+2},{sy+bh/2} L{nx-2},{sy+bh/2}" stroke="{C["text"]}" stroke-width="1.5" marker-end="url(#arr)"/>')
    # mapping arrows from history nodes down to the stack
    for x_hist, x_box, col in [(360, 492 + 106, C["pr3"]), (600, 726 + 106, C["pr4"])]:
        p.append(f'<path d="M{x_hist},{ly+62} C{x_hist},{ly+130} {x_box},{sy-70} {x_box},{sy-4}" fill="none" stroke="{col}" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#arrg)"/>')
    defs = (f'<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{C["text"]}"/></marker>'
            f'<marker id="arrg" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{C["gray"]}"/></marker></defs>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="PR 4424 history and the four stacked PRs">' + defs + "".join(p) + "</svg>"
    return svg


# ------------------------------------------------------------------------------------------------
# Figure 3: dependency graph of the concerns (what needs what)
# ------------------------------------------------------------------------------------------------
def fig_deps():
    W, H = 940, 262
    p = []
    p.append(text(24, 24, "What needs what (an arrow points from a part to the part it needs)", 14, weight=600))
    pos = {"L": (110, 130), "R": (300, 130), "G": (470, 130), "A": (300, 60), "S": (300, 200), "T": (700, 130)}
    pr_of = {"L": 0, "R": 0, "G": 0, "A": 1, "S": 2, "T": 3}
    names = {"L": "L layout", "R": "R AVX-512 reader", "G": "G FPGA staging", "A": "A AMX kernel", "S": "S shared save", "T": "T tail block + policy"}
    edges = [("R", "L"), ("G", "L"), ("A", "L"), ("S", "L"), ("T", "A"), ("T", "S"), ("T", "R"), ("T", "G")]
    # PR-1 envelope
    p.append(f'<rect x="40" y="100" width="520" height="60" rx="8" ry="8" fill="none" stroke="{C["pr1"]}" stroke-width="2" stroke-dasharray="6 4"/>')
    p.append(text(48, 94, "PR-1", 11.5, C["pr1"], weight=700))
    rw, rh = 150, 32
    for k, (x, y) in pos.items():
        pass
    # edges first (behind boxes)
    for a, b in edges:
        xa, ya = pos[a]; xb, yb = pos[b]
        # shrink to box edges along the line
        dx, dy = xb - xa, yb - ya
        import math
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        # exit point: rectangle boundary approx
        def edge(x, y, ux, uy, sign):
            tx = (rw / 2) / abs(ux) if ux else 1e9
            ty = (rh / 2) / abs(uy) if uy else 1e9
            t = min(tx, ty) + 4
            return x + sign * ux * t, y + sign * uy * t
        x1, y1 = edge(xa, ya, ux, uy, 1)
        x2, y2 = edge(xb, yb, ux, uy, -1)
        col = PRC[pr_of[a]]
        p.append(f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{col}" stroke-width="1.6" marker-end="url(#arrd)" fill="none"/>')
    for k, (x, y) in pos.items():
        col = PRC[pr_of[k]]
        p.append(f'<rect x="{x-rw/2}" y="{y-rh/2}" width="{rw}" height="{rh}" rx="5" ry="5" fill="{C["surface"]}" stroke="{col}" stroke-width="2"/>')
        p.append(text(x, y + 4.5, names[k], 12, C["pr4text"] if k == "T" else col, "middle", 600))
    p.append(text(24, 232, "L ships with R and G in PR-1: without the reader a build with the option on does not compile.", 11.5, C["muted"]))
    p.append(text(24, 248, "A and S each need only L, so PR-2 and PR-3 could land in either order. T needs A, S, R and G, so PR-4 is last.", 11.5, C["muted"]))
    defs = (f'<defs><marker id="arrd" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{C["gray"]}"/></marker></defs>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="dependency graph of the concerns">' + defs + "".join(p) + "</svg>"


# ------------------------------------------------------------------------------------------------
# Figure 4: sizes per PR (stacked code / tests), added lines by git numstat
# ------------------------------------------------------------------------------------------------
SIZES = [("PR-1", 881, 965), ("PR-2", 179, 98), ("PR-3", 500, 178), ("PR-4", 791, 675)]


def fig_sizes():
    W, H = 940, 256
    p = []
    p.append(text(24, 24, "Size of each PR (added lines, git numstat)", 14, weight=600))
    p.append(text(24, 42, "solid = code, light = tests; the number at the end is the total", 12, C["muted"]))
    x0, x1 = 90, 820
    maxv = 2000
    def sx(v):
        return x0 + (x1 - x0) * v / maxv
    y = 62
    bh = 26
    for i, (name, code, tests) in enumerate(SIZES):
        yy = y + i * (bh + 12)
        p.append(text(x0 - 10, yy + bh / 2 + 4, name, 12, C["pr4text"] if i == 3 else PRC[i], "end", 700))
        wc = sx(code) - sx(0)
        wt = sx(tests) - sx(0)
        p.append(f'<rect x="{x0}" y="{yy}" width="{wc:.1f}" height="{bh}" fill="{PRC[i]}" rx="3" ry="3"/>')
        p.append(f'<rect x="{x0+wc+2:.1f}" y="{yy}" width="{max(wt-2,1):.1f}" height="{bh}" fill="{PRC[i]}" fill-opacity="0.35" rx="3" ry="3"/>')
        p.append(text(x0 + wc + wt + 8, yy + bh / 2 + 4, f"{code+tests:,}  (code {code:,}, tests {tests:,})", 11.5, C["text"]))
    # axis
    ay = y + 4 * (bh + 12) + 4
    p.append(f'<line x1="{x0}" y1="{ay}" x2="{x1}" y2="{ay}" stroke="{C["rule"]}"/>')
    for v in (0, 500, 1000, 1500, 2000):
        p.append(f'<line x1="{sx(v):.1f}" y1="{ay}" x2="{sx(v):.1f}" y2="{ay+4}" stroke="{C["rule"]}"/>')
        p.append(text(sx(v), ay + 16, f"{v:,}", 10.5, C["muted"], "middle"))
    p.append(text((x0 + x1) / 2, ay + 34, "added lines", 10.5, C["muted"], "middle"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="size of each PR">' + "".join(p) + "</svg>"


# ------------------------------------------------------------------------------------------------
# Figure 5: what each step buys. Three small dumbbell charts: before (gray) -> after (PR color).
# ------------------------------------------------------------------------------------------------
PANELS = [
    {
        "title": "Decode throughput vs main's AMX kernel",
        "sub": "qwen3-4b, tp2, 8 users, CPU attention, runtron; 2026-09-14, old base 544ca05c7a",
        "before_label": "after PR-1 (option on; kill-switch run as proxy)",
        "after_label": "after PR-2 (AMX kernel on the plane)",
        "pr": 1,
        "unit": "% TPS vs main's AMX",
        "rows": [("prompt 1024", -7.1, 6.1), ("prompt 2048", -10.3, 7.1), ("prompt 8192", -11.1, 10.4)],
        "lo": -14, "hi": 14,
        "take": "PR-1 alone loses on an AMX host; PR-2 turns it into the gain. PR-3 and PR-4 leave decode throughput within 0.4 %.",
    },
    {
        "title": "Time to first token at prompt 1024 vs main's AMX base",
        "sub": "qwen3-4b, 8 users, runtron; 2026-09-15 arms vnni0 and ab, old base",
        "before_label": "after PR-2 (per-row scatter store)",
        "after_label": "after PR-3 (shared block save)",
        "pr": 2,
        "unit": "% TTFT vs main's AMX base (+ = slower)",
        "rows": [("tp2 (3.226 -> 3.098 s)", 2.6, -1.4), ("tp4 (2.362 -> 2.108 s)", 7.5, -4.1)],
        "lo": -6, "hi": 9,
        "take": "The per-row store costs prefill time at short prompts; the shared block save removes it and ends below main.",
    },
    {
        "title": "FPGA-attention decode throughput vs canonical AMX base",
        "sub": "qwen3-4b, rinzler, our half of delphi-3bda, n=4; 2026-09-30 (exec/results/i4500b-20260930)",
        "before_label": "before PR-4 (VNNI layout, no tail block)",
        "after_label": "after PR-4 (row-major tail block + policy)",
        "pr": 3,
        "unit": "% TPS vs canonical AMX base",
        "rows": [("tp2, 2 users", -3.8, 0.4), ("tp4, 4 users", -11.8, 2.8)],
        "lo": -14, "hi": 6,
        "take": "Issue #4500: the per-token column access hurt FPGA-attention decode; PR-4 brings it back to the base (the after values are not resolved from zero).",
    },
]


def fig_panel(panel, idx):
    W = 940
    rows = panel["rows"]
    top = 92
    rowh = 34
    H = top + len(rows) * rowh + 70
    p = []
    p.append(text(24, 24, panel["title"], 14, weight=600))
    p.append(text(24, 42, panel["sub"], 11, C["muted"]))
    x0, x1 = 230, 860
    lo, hi = panel["lo"], panel["hi"]
    def sx(v):
        return x0 + (x1 - x0) * (v - lo) / (hi - lo)
    col = PRC[panel["pr"]]
    # zero line and ticks
    ay = top + len(rows) * rowh
    p.append(f'<line x1="{sx(0):.1f}" y1="{top-6}" x2="{sx(0):.1f}" y2="{ay}" stroke="{C["muted"]}" stroke-width="1" stroke-dasharray="3 3"/>')
    p.append(text(sx(0), top - 10, "0 = same as the base", 10.5, C["muted"], "middle"))
    step = 2 if hi - lo <= 16 else 4
    v = lo
    while v <= hi + 1e-9:
        p.append(f'<line x1="{sx(v):.1f}" y1="{ay}" x2="{sx(v):.1f}" y2="{ay+4}" stroke="{C["rule"]}"/>')
        p.append(text(sx(v), ay + 16, f"{v:+d} %" if v else "0", 10, C["muted"], "middle"))
        v += step
    p.append(f'<line x1="{x0}" y1="{ay}" x2="{x1}" y2="{ay}" stroke="{C["rule"]}"/>')
    p.append(text((x0 + x1) / 2, ay + 32, panel["unit"], 10.5, C["muted"], "middle"))
    for i, (lab, b, a) in enumerate(rows):
        yy = top + i * rowh + rowh / 2
        p.append(text(x0 - 12, yy + 4, lab, 11.5, C["text"], "end"))
        xb, xa = sx(b), sx(a)
        p.append(f'<line x1="{xb:.1f}" y1="{yy}" x2="{xa:.1f}" y2="{yy}" stroke="{C["grayfill"]}" stroke-width="3"/>')
        p.append(f'<circle cx="{xb:.1f}" cy="{yy}" r="6" fill="{C["gray"]}" stroke="{C["surface"]}" stroke-width="2"/>')
        p.append(f'<circle cx="{xa:.1f}" cy="{yy}" r="6" fill="{col}" stroke="{C["surface"]}" stroke-width="2"/>')
        # direct labels, placed on the outer side of each dot
        lb = f"{b:+.1f} %"
        la = f"{a:+.1f} %"
        if xb < xa:
            p.append(text(xb - 10, yy + 4, lb, 11, C["muted"], "end"))
            p.append(text(xa + 10, yy + 4, la, 11, C["text"], "start", 600))
        else:
            p.append(text(xb + 10, yy + 4, lb, 11, C["muted"], "start"))
            p.append(text(xa - 10, yy + 4, la, 11, C["text"], "end", 600))
    # legend
    ly = 60
    p.append(f'<circle cx="{x0+6}" cy="{ly}" r="5" fill="{C["gray"]}"/>')
    p.append(text(x0 + 16, ly + 4, panel["before_label"], 10.5, C["muted"]))
    lx2 = x0 + 330
    p.append(f'<circle cx="{lx2+6}" cy="{ly}" r="5" fill="{col}"/>')
    p.append(text(lx2 + 16, ly + 4, panel["after_label"], 10.5, C["muted"]))
    p.append(text(24, H - 12, panel["take"], 11.5, C["text"]))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{esc(panel["title"])}">' + "".join(p) + "</svg>"


# ------------------------------------------------------------------------------------------------
# page
# ------------------------------------------------------------------------------------------------
CARDS = [
    {
        "name": "PR-1", "title": "VNNI K: the layout, its AVX-512 reader and the FPGA staging path",
        "base": "main", "opens": "ready for review", "size": "+1,846 / -160 lines (965 added lines are tests)",
        "what": [
            "Stores the K cache of 128-dimension heads in the VNNI layout instead of row-major rows. A new typed owner (k_vnni_tensor) and read-only or writable views replace raw pointers, which is what Ben asked for on 2026-09-21.",
            "Writes every token's K row into that layout one row at a time (4 scatters per row).",
            "Scores the stored K with a new AVX-512 reader (k_vnni::qk_group) wherever the software path runs: partial pages, hosts without AMX, the kill switch. Until PR-2, every page of a VNNI slot takes this reader, even on an AMX host. The reader is permanent: after PR-2 the AMX kernel takes full pages and the reader keeps the partial ones; after PR-4 the rows of a row-major tail block go to the row-major dotter, and the reader keeps the converted blocks of partial pages.",
            "Teaches the FPGA staging gather to read K rows out of the layout.",
            "Adds the CMake option TRON_K_VNNI (off in every preset) and turns it on in the manual CMake CI lane. The packed V layout has no such option (it is unconditional on main); the K option exists so that a row-major K build stays available as the rollback and comparison binary (issue #4444) and so that main's default build does not change until PR-4.",
        ],
        "why": "Everything else in the stack builds on the layout and on the typed views. Keeping the AMX kernel out of this PR lets reviewers without AMX background review the storage design on its own: the PR has no AMX instruction.",
        "after": "With the option off (every preset): no change. With the option on and no AMX: about +4 to +5 % decode throughput over the row-major reader. With the option on and AMX: about 7 to 11 % below main's AMX kernel until PR-2 (figure 5, first panel).",
        "temp": "One clause that keeps the dense AMX path off for VNNI slots, and five comment sentences. PR-2 removes them.",
        "from": "Built as a real tree (76a0160b72 = the tested ba69cb513e minus the AMX kernel minus the shared save). It passes a 22-cell syntax check; it has not been built or run on delphi-3bda yet.",
        "inherits": "The open items of PR 4424 that belong to the layout and the reader. Addressed later in the stack: issue #4444 only in part (PR-4 makes the tokens identical to main in the measured CPU-attention cells; the FPGA-attention difference and the kill-switch rollback contract stay open). Not addressed by any of the four: the kv_mul 3/8 reader slowdown (the AMX kernel is eligible for kv_mul 4 only, so those models stay on the reader), the widened test tolerance, the genoa96 cost row, the benchmark-binary mismatch of the legacy lane.",
    },
    {
        "name": "PR-2", "title": "VNNI K: the AMX QK kernel reads the plane as its B operand",
        "base": "PR-1", "opens": "draft", "size": "+277 / -61 lines",
        "what": [
            "Adds the kernel qk_vnni_128x4 and its query packer pack_q_rows_128x4. The kernel takes the 4 query rows as the A operand and the page's 16 K panels as the B operand, so the scores come out as S = Q K^T with no register transpose.",
            "Dispatches to it for full pages of VNNI slots and removes PR-1's temporary gate.",
            "Tests: bit identity against the row-major kernel on real AMX (t_amx_numerics), the dispatch fakes (t_amx_dispatch_dtype), a typed-boundary probe.",
        ],
        "why": "This is the reason the layout exists: the transpose that the row-major kernel pays on every page is gone.",
        "after": "About +6 to +10 % decode throughput over main's AMX kernel at prompt 1024 to 8192 (figure 5). Prefill at short prompts is a little slower at tp4 (the per-row store) until PR-3.",
        "temp": "None of its own.",
        "from": "Built as a real tree (4d3a042225 = the PR-1 tree plus the AMX diff, two comment repairs). 22-cell syntax check passes; not built on delphi-3bda yet.",
        "inherits": "The reviewers of the AMX code (Ben, Bill) review this PR; it is the smallest of the four.",
    },
    {
        "name": "PR-3", "title": "VNNI K: shared block save",
        "base": "PR-2", "opens": "draft", "size": "+678 / -75 lines",
        "what": [
            "When a pass saves 16 consecutive tokens of one page block, the 16 rows are transposed in registers and written as whole 64-byte lines (store_block, page::set_k_block) instead of 64 scatters per row.",
            "The main thread shares that store with its idle helper threads: save_k takes a worker index, the code generator (TronCpp.hs) emits the helper-side call, and a window protocol hands out work units. This is the form Ben asked for in the only open review thread (the save_k_helper fold, PR 4774).",
            "Tests: the block save bit for bit against the per-row store, and a three-thread save_k case.",
        ],
        "why": "The per-row store of PR-1 costs 105 ns per (token, KV head) row in prefill, 0.86 ms per layer at 8 users. That shows up as a slower first token at short prompts.",
        "after": "Time to first token at prompt 1024 drops below main's AMX base: about -45 ms at tp2 and -88 ms at tp4 (figure 5, second panel). Decode throughput is unchanged within 0.4 %.",
        "temp": "About 15 lines of masked partial-block store logic that PR-4 replaces with the row-major tail block (decision D10 keeps the tested form).",
        "from": "Its tree equals ba69cb513e, built and tested on delphi-3bda on 2026-10-08, apart from comment wording.",
        "inherits": "Main changed the code generator by 442 lines since the merge base, so this PR's two Haskell hunks are the likeliest merge conflict of the stack.",
    },
    {
        "name": "PR-4", "title": "VNNI K: keep short K-cache writes row-major, convert at the forward end; deb preset turns the layout on",
        "base": "PR-3", "opens": "draft", "size": "+1,466 / -115 lines",
        "what": [
            "A 16-token block whose rows arrive one at a time (every decode step) is kept in plain row order inside its own bytes until its 16th row is saved; the main thread converts it to the VNNI layout at the end of that forward pass. Two bit sets per page record which rows are saved and which blocks are converted; the converted-block bit selects the layout for every reader and writer.",
            "Under hardware (FPGA) attention the blocks are never converted: the FPGA reads rows, so the layout would only cost.",
            "The dense AMX path takes a page only when all 4 blocks are converted; the software loop scores tail rows with the row-major dotter.",
            "Turns the layout on in the deb preset (the released package), so this PR is the one that changes production.",
        ],
        "why": "Issue #4500: with the per-token column access of the VNNI layout, FPGA-attention decode on qwen3-4b lost 4 to 12 %. The tail block removes the 64-line access for decode rows and makes CPU-attention tokens identical to main again in the measured cells.",
        "after": "FPGA-attention decode back to the base within noise (figure 5, third panel). Whole machine, 14 nightly configs, 2026-10-09: llama-8b 32 users at 4096 +4.8 % TPS, qwen 8k software attention +7.6 %, llama-3.2-3b -1.4 % (the kv_mul 3 item), memory within 0.3 %.",
        "temp": "None.",
        "from": "Its content is the PR 4737 merge diff (byte-identical) plus the preset commit: the tree of 9d5c7a389b, built, tested and measured on the whole machine on 2026-10-09.",
        "inherits": "The cost rows refresh, and the whole-machine campaign that backs the production claim.",
    },
]


def card_html(c, i):
    col = PRC[i]
    tcol = C["pr4text"] if i == 3 else col
    lis = "".join(f"<li>{esc(w)}</li>" for w in c["what"])
    return f'''
<article class="card" style="--c:{col};--t:{tcol}">
  <header><span class="tag">{c["name"]}</span><h3>{esc(c["title"])}</h3>
  <p class="meta">base: <b>{esc(c["base"])}</b> · opens as: <b>{esc(c["opens"])}</b> · size: <b>{esc(c["size"])}</b></p></header>
  <h4>What it changes</h4><ul>{lis}</ul>
  <h4>Why it exists</h4><p>{esc(c["why"])}</p>
  <h4>What you get after it merges</h4><p>{esc(c["after"])}</p>
  <h4>Temporary code</h4><p>{esc(c["temp"])}</p>
  <h4>Where its tree comes from</h4><p>{esc(c["from"])}</p>
  <h4>Also carries</h4><p>{esc(c["inherits"])}</p>
</article>'''


def page():
    f1 = fig_decomposition(); f2 = fig_lineage(); f3 = fig_deps(); f4 = fig_sizes()
    panels = [fig_panel(pn, i) for i, pn in enumerate(PANELS)]
    for name, s in [("fig1-decomposition", f1), ("fig2-lineage", f2), ("fig3-deps", f3), ("fig4-sizes", f4)] + [(f"fig5-{i}", s) for i, s in enumerate(panels)]:
        open(os.path.join(SVGDIR, name + ".svg"), "w").write(s)
    cards = "".join(card_html(c, i) for i, c in enumerate(CARDS))
    css = f'''
<style>
/* layout: one reading column, figures full width of the column, light theme only (project rule) */
:root {{ --bg:{C["surface"]}; --fg:{C["text"]}; --muted:{C["muted"]}; --panel:{C["panel"]}; --rule:{C["rule"]};
        --pr1:{C["pr1"]}; --pr2:{C["pr2"]}; --pr3:{C["pr3"]}; --pr4:{C["pr4"]}; color-scheme: light; }}
body {{ background:var(--bg); color:var(--fg); margin:0; {FONT}; font-size:15px; line-height:1.5; }}
.wrap {{ max-width: 980px; margin: 0 auto; padding-block: 28px 56px; padding-inline: 16px; }}
h1 {{ font-size: 28px; line-height:1.2; margin: 0 0 6px; text-wrap: balance; }}
h2 {{ font-size: 20px; margin: 40px 0 10px; text-wrap: balance; border-top: 1px solid var(--rule); padding-top: 18px; }}
h3 {{ font-size: 16px; margin: 4px 0 2px; }}
h4 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 12px 0 2px; }}
p {{ margin: 6px 0; max-width: 72ch; }}
ul {{ margin: 4px 0 4px 18px; padding: 0; max-width: 72ch; }} li {{ margin: 3px 0; }}
.lede {{ color: var(--muted); margin-bottom: 14px; }}
.short {{ background: var(--panel); border-left: 4px solid var(--pr1); padding: 10px 14px; margin: 14px 0 20px; }}
.short p {{ margin: 4px 0; }}
figure {{ margin: 14px 0 6px; padding: 10px 8px; border: 1px solid var(--rule); border-radius: 6px; background: #fff; overflow-x: auto; }}
figure svg {{ display:block; min-width: 640px; }}
figcaption {{ font-size: 12.5px; color: var(--muted); padding: 6px 4px 0; }}
.cards {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 12px; }}
.card {{ border: 1px solid var(--rule); border-top: 4px solid var(--c); border-radius: 6px; padding: 12px 16px 14px; background: #fff; min-width: 0; }}
.card header h3 {{ color: var(--t); }}
.tag {{ display:inline-block; font-weight: 700; color: var(--t); font-size: 13px; letter-spacing: .04em; }}
.meta {{ color: var(--muted); font-size: 13px; }}
table {{ border-collapse: collapse; font-size: 13.5px; margin: 8px 0; font-variant-numeric: tabular-nums; }}
th, td {{ border-bottom: 1px solid var(--rule); padding: 6px 10px; text-align: left; vertical-align: top; }}
th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }}
.tablewrap {{ overflow-x: auto; }}
dl {{ max-width: 76ch; }} dt {{ font-weight: 600; margin-top: 8px; }} dd {{ margin: 0 0 0 0; color: var(--fg); }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; background: var(--panel); padding: 1px 4px; border-radius: 3px; }}
.small {{ font-size: 13px; color: var(--muted); }}
@media (max-width: 480px) {{ h1 {{ font-size: 23px; }} }}
</style>'''
    body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Four PRs from PR 4424</title>
{css}
</head><body>
<div class="wrap">
<h1>The four PRs proposed from PR 4424</h1>
<p class="lede">What each proposed PR is, and how the four relate to PR 4424. Written 2026-10-10 from split-plan.md and split-handoff.md; no execution steps here.</p>

<div class="short">
<p><b>Short version.</b> PR 4424 is four features in one: the VNNI K layout with its readers, the AMX kernel that reads it, the shared block save, and the row-major tail block with the hardware-attention policy.</p>
<p>The proposal cuts it into four stacked PRs in that order, each building on the one before: PR-1 the layout and its readers, PR-2 the AMX kernel, PR-3 the shared block save, PR-4 the tail block, the policy and the deb preset.</p>
<p>Together the four reproduce today's PR 4424 head; PR-3 and PR-4 are the content of the former PRs 4774 and 4737, and PR-1 and PR-2 are the rest, split along the AMX seam.</p>
</div>

<h2>Words used here</h2>
<dl>
<dt>PR 4424</dt><dd>positron-ai/tron pull request "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save". Draft, branch jhan-amx-vnniK, base main, head 0a5334ccb6, 29 files, +4,054 / -198 lines.</dd>
<dt>K cache, KV page, plane</dt><dd>The K cache holds the key vectors of past tokens. A KV page is a 64-token block of the K and V caches. The plane is the packed K storage of one page and one KV head (16 KiB).</dd>
<dt>VNNI layout</dt><dd>The pair-interleaved operand layout that the AMX tile multiply reads as its right operand (B operand). Storing K that way lets the kernel compute S = Q K^T without a register transpose.</dd>
<dt>AMX, AVX-512</dt><dd>AMX: Intel Advanced Matrix Extensions, the tile instruction set. AVX-512: the 512-bit vector instruction set, present on every host tron runs on.</dd>
<dt>The option, the kill switch</dt><dd>The option is the CMake switch TRON_K_VNNI (off in every preset until PR-4 puts it into the deb preset, the preset that builds the released package). The kill switch is TRON_AMX_DISABLE=1, which turns the AMX kernels off at run time.</dd>
<dt>Dotter, reader</dt><dd>The dotter is the row-major dot-product loop that scores K on the CPU today. The reader is PR-1's AVX-512 loop that scores K stored in the VNNI layout.</dd>
<dt>save_k, shared block save</dt><dd>save_k stores one pass's K rows into the cache. The shared block save writes one whole 16-token block at a time and shares the work with the idle helper threads of the main loop.</dd>
<dt>Row-major tail block</dt><dd>The last, partly filled 16-token block of a page, kept in plain row order until its 16th row is saved, then converted to the VNNI layout at the end of that forward pass.</dd>
<dt>Hardware attention, FPGA</dt><dd>Attention scores computed on the FPGA (the accelerator card) instead of the CPU. Production runs qwen3-4b that way.</dd>
<dt>Stack</dt><dd>A chain of PRs, each based on the previous one. Repo rule: only the PR based on main is ready for review; the others stay drafts until their parent merges.</dd>
<dt>Concern letters L, R, G, A, S, T, B</dt><dd>The seven parts of PR 4424 used in the plan: L layout and storage, R AVX-512 reader, G FPGA staging, A AMX kernel, S shared block save, T tail block + policy, B build and CI files.</dd>
<dt>TPS, TTFT, tp2 / tp4</dt><dd>TPS: decode tokens per second per user. TTFT: time to first token. tp2 / tp4: tensor parallelism over 2 or 4 engines.</dd>
<dt>Issues #4444 and #4500</dt><dd>#4444: the VNNI reader adds scores in a different order than the dotter, so a token can flip at a near tie against the row-major binary. #4500: the FPGA-attention decode loss caused by the per-token 64-line column access of the VNNI layout.</dd>
</dl>

<h2>1. What PR 4424 contains</h2>
<p>Every hunk of the PR was labeled by concern. Four of the seven concerns go to PR-1 (the layout cannot ship without its software reader: a build with the option on does not compile otherwise). The other three become one PR each.</p>
<figure>{f1}<figcaption>Figure 1. The seven concern blocks of PR 4424, width proportional to their non-blank added lines (hunk classification at the head), colored by the PR that carries them.</figcaption></figure>

<h2>2. The four PRs</h2>
<div class="cards">{cards}</div>

<h2>3. How they relate to PR 4424</h2>
<p>PR 4424's own history already holds three of the four trees. PR 4774 (the save_k worker fold) and PR 4737 (the tail block) were separate stacked PRs until 2026-10-08, when they were merged into 4424. PR-3 and PR-4 give them back their own PRs; PR-1 and PR-2 are the remaining content, cut along the AMX seam, which the history never had as separate states. The sum of the four, merged with the same main, equals today's head except for the CMake line that required AMX dispatch (dropped in PR-1, decision D2) and comment wording that the earlier PRs carry and the later ones restore.</p>
<figure>{f2}<figcaption>Figure 2. Top: the tested states on PR 4424's branch. Bottom: the four stacked PRs. Dashed arrows: which history state each of PR-3 and PR-4 reproduces.</figcaption></figure>
<figure>{f3}<figcaption>Figure 3. The dependencies between the seven parts decide the order of the stack.</figcaption></figure>

<h2>4. How big each PR is</h2>
<figure>{f4}<figcaption>Figure 4. Added lines by git numstat on the real trees (PR-1 = 76a0160b72, PR-2 = 4d3a042225, PR-3 = ba69cb513e against PR-2, PR-4 = the 4737 merge diff plus the preset). PR 4424 itself: 4,054 added lines.</figcaption></figure>
<p>PR-1 is still at the repository's 95th percentile of merged-PR size. Half of it is tests. Cutting it further would mean adding the tensor type without its store and reader, which the reviewer declined on PR 4557.</p>

<h2>5. What each step buys</h2>
<p>Three measured effects, each attributed to the PR that causes it. Gray dot = before that PR, colored dot = after it. All three are measurements from the development of PR 4424 at older bases; the PR bodies will carry fresh runs of each final head against the latest main.</p>
<figure>{panels[0]}<figcaption>Figure 5a. Decode throughput against main's AMX kernel. The "after PR-1" values come from the kill-switch run of the VNNI binary on an AMX host (AMX off, reader on), which is what PR-1 alone does on such a host with the option on.</figcaption></figure>
<figure>{panels[1]}<figcaption>Figure 5b. Time to first token at prompt 1024. Positive is slower than main's AMX base.</figcaption></figure>
<figure>{panels[2]}<figcaption>Figure 5c. Decode throughput under FPGA attention (production's mode for qwen3-4b). The after values are within noise of the base (paired t not resolved).</figcaption></figure>

<h2>6. The stages at a glance</h2>
<div class="tablewrap"><table>
<tr><th>After</th><th>Decode TPS, CPU attention, vs main's AMX</th><th>TTFT at prompt 1024</th><th>FPGA-attention decode (qwen3-4b)</th><th>Tokens vs main (CPU attention, qwen3-4b, 1 user)</th><th>Option in the deb preset</th></tr>
<tr><td>PR-1 (option on)</td><td>-7 to -11 % (kill-switch run as proxy)</td><td>about equal</td><td>-4 / -12 % (issue #4500)</td><td>differ at generated token 52 at prompt 1024 (#4444)</td><td>off</td></tr>
<tr><td>PR-2</td><td>+6 to +10 %</td><td>+2.6 % tp2, +7.5 % tp4</td><td>-4 / -12 %</td><td>differ at token 52</td><td>off</td></tr>
<tr><td>PR-3</td><td>+6 to +10 %</td><td>-1.4 % tp2, -4.1 % tp4</td><td>-4 / -12 %</td><td>differ at token 52</td><td>off</td></tr>
<tr><td>PR-4</td><td>+5 to +10 %</td><td>-1.4 % tp2, -4.1 % tp4</td><td>within noise</td><td>identical at prompt 1024 and 8192 (256 tokens)</td><td>on</td></tr>
</table></div>
<p class="small">Sources: figure 5 for the first three columns; exec/results/merge4737-precheck/smoke (2026-10-09) for the token column; the stack keeps the option off in every preset until PR-4, so no intermediate row reaches production.</p>

<h2>7. What stays open about this picture</h2>
<ul>
<li>Every number above is from an older base (2026-09-14, 2026-09-15, 2026-09-30) or from the whole head (2026-10-09). The four new heads have not been measured against the latest main yet; the handoff schedules those runs.</li>
<li>PR-1 and PR-2 exist as real trees that pass a syntax check only; PR-3 and PR-4 reuse trees that were built and tested on delphi-3bda. Full builds and tests of the reduced trees are part of the handoff.</li>
<li>Whether a four-PR stack or a three-PR variant (AMX kernel folded into PR-1) suits the reviewers is decision D1 in split-handoff.md; the other open decisions (CI coverage, build host, protected sections) are listed there.</li>
</ul>
</div>
</body></html>'''
    open(OUT, "w").write(body)
    print("wrote", OUT, len(body), "bytes;", "svgs in", SVGDIR)


if __name__ == "__main__":
    page()
