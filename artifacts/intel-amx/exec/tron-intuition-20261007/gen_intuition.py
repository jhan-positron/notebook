#!/usr/bin/env python3
"""Generate PR3879/new-PRs/new-counters/tron-intuition-claude.html.

A mental map of tron for timing estimates by hand (jhan, 2026-10-07).
Every number is copied from a measured source named in the page; the few
estimates are labeled est. Pure ASCII output, light theme only.
"""
import os, sys, html

OUT = "/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/tron-intuition-claude.html"

# ---------------------------------------------------------------- palette (dataviz reference instance, light mode)
BLUE = "#2a78d6"     # slot 1: AMX on / after
ORANGE = "#eb6834"   # slot 2: AVX / kill switch / before
AQUA = "#1baf7a"     # slot 3: the FPGA card
RED = "#d03b3b"      # status critical: the slice a kernel can shorten (always with a label)
INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"; GRID = "#e1e0d9"; AXIS = "#c3c2b7"
SURF = "#fcfcfb"; PLANE = "#f9f9f7"
LIGHTBLUE = "#9ec5f4"; LIGHTORANGE = "#f7b9a0"; GREY = "#d9d8d2"

# ---------------------------------------------------------------- SVG helpers
def esc(s):
    return html.escape(str(s), quote=True)

def txt(x, y, s, size=12, fill=INK, anchor="start", weight="normal", extra=""):
    return ('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="%s" font-weight="%s" %s>%s</text>\n'
            % (x, y, size, fill, anchor, weight, extra, esc(s)))

def rect(x, y, w, h, fill="none", stroke="none", sw=1, dash=None, rx=0, title=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    t = "<title>%s</title>" % esc(title) if title else ""
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" stroke-width="%s" rx="%s"%s>%s</rect>\n'
            % (x, y, w, h, fill, stroke, sw, rx, d, t))

def line(x1, y1, x2, y2, stroke=AXIS, sw=1, dash=None, marker=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    m = ' marker-end="url(#%s)"' % marker if marker else ""
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s%s/>\n' % (x1, y1, x2, y2, stroke, sw, d, m)

def circle(cx, cy, r, fill, stroke="none", sw=1, title=None):
    t = "<title>%s</title>" % esc(title) if title else ""
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s">%s</circle>\n' % (cx, cy, r, fill, stroke, sw, t)

def svg_open(w, h, aria):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s" '
            'font-family="system-ui, -apple-system, Segoe UI, sans-serif" style="max-width:100%%;height:auto;display:block">\n'
            '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse">'
            '<path d="M0,0 L8,4 L0,8 z" fill="%s"/></marker>'
            '<marker id="arrred" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse">'
            '<path d="M0,0 L8,4 L0,8 z" fill="%s"/></marker></defs>\n'
            '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>\n' % (w, h, w, h, esc(aria), INK2, RED, w, h, SURF))

def svg_close():
    return "</svg>\n"

def wrap_lines(s, width):
    words = s.split(); out = []; cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur: out.append(cur)
    return out


def wtxt(x, y, s, size=12, fill=INK2, width=150, lh=None, weight="normal", anchor="start"):
    """Several text lines, wrapped at about `width` characters. Returns (svg, y after the last line)."""
    lh = lh or size + 4
    out = ""
    for ln in wrap_lines(s, width):
        out += txt(x, y, ln, size=size, fill=fill, weight=weight, anchor=anchor)
        y += lh
    return out, y

def box(x, y, w, h, title, lines, fill="#ffffff", stroke=AXIS, title_fill=INK, size=12, rx=6):
    s = rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.2, rx=rx)
    s += txt(x + 10, y + 20, title, size=13, fill=title_fill, weight="bold")
    yy = y + 38
    for ln in lines:
        s += txt(x + 10, yy, ln, size=size, fill=INK2)
        yy += size + 4
    return s

# ---------------------------------------------------------------- Figure 1: the map in one picture
def fig_map():
    W, H = 1180, 400
    s = svg_open(W, H, "The map: engine, decode step, layer, attention operation, page visit")
    bx = 18; bw = 215; gap = 20; by = 60; bh = 200
    cols = [
        ("Engine (one tron process)", [
            "tp2: 2 cards, 28 app cores",
            "  = main thread + 27 workers",
            "tp4: 4 cards, 56 app cores",
            "  = main + 55 workers",
            "Serves U users at once.",
            "Nightly: tp2 = 4 engines,",
            "tp4 = 2 engines per machine.",
            "",
            "Count that matters: U,",
            "the users PER ENGINE."]),
        ("Decode step = one forward", [
            "One new token for each of",
            "the U users (one token job",
            "per user), over all L layers.",
            "Timer T1 = its wall time.",
            "TPS per user = 1 / T1.",
            "",
            "llama (hand-written plugin):",
            "  8 users -> 2 minibatches of 4",
            "qwen, gpt-oss (ingested):",
            "  one minibatch"]),
        ("Layer (period T4)", [
            "Cards: WQ, WK, WV, WO,",
            "  WFF1, WFF3, WFF2 (matmuls).",
            "CPU: rope Q, norms, and",
            "  the attention operation.",
            "The RX workers save K and V",
            "  into KV pages (host DRAM).",
            "",
            "'Other work' = everything",
            "but attention: about flat",
            "in context."]),
        ("Attention operation", [
            "Split over the attention",
            "workers as (KV head, page",
            "range) sections: one JOB per",
            "worker per layer (T2 busy,",
            "T3 wall on worker 0).",
            "ready pass: old pages.",
            "pending pass: this layer's",
            "  newest page (waits for K/V).",
            "join: fold partial results",
            "  (T5 = join wait)."]),
        ("Page visit = one unit", [
            "1 query token (its kv_mul",
            "query heads) x 1 KV head x",
            "1 KV page (64 tokens):",
            "reads 32 KiB (K 16 + V 16).",
            "",
            "Path per visit:",
            "  AMX kernel: full page,",
            "    fitting shape, AMX on",
            "  AVX loop: everything else",
            "  card: under AoF"]),
    ]
    fills = ["#ffffff", "#ffffff", "#ffffff", "#ffffff", "#eef4fc"]
    x = bx
    for i, (t, lines) in enumerate(cols):
        s += box(x, by, bw, bh, t, lines, fill=fills[i], size=11.5)
        if i < len(cols) - 1:
            s += line(x + bw + 2, by + bh / 2, x + bw + gap - 2, by + bh / 2, stroke=INK2, sw=1.5, marker="arr")
        x += bw + gap
    # count line under the boxes
    s += txt(bx, 30, "Figure 1. The map: what contains what, and which count sets its size.", size=14, fill=INK, weight="bold")
    yy = by + bh + 34
    s += txt(bx, yy, "Counts per decode step:  visits on the CPU  =  U users  x  L layers on the CPU  x  KV heads  x  pages per user (context / 64, rounded up)", size=12.5, fill=INK)
    s += txt(bx, yy + 20, "Shared by the attention workers (27 at tp2 at most, 55 at tp4). The split heuristic hands 13 to 26 of the 27 to attention at 8 users. Time per worker = its visits x unit cost + waits.", size=12, fill=INK2)
    s += txt(bx, yy + 40, "Under AoF the card scores every whole group of 4 tokens (GOF) and the CPU keeps a 1-to-4-key tail per (user, KV head, layer): the kernel's unit (64 keys) never fills.", size=12, fill=INK2)
    s += txt(bx, yy + 60, "Sources: tron-amx-distilled.html (Decode architecture); counter.html sections 2 and 3; attention-stats-claude.html (timers); self_attention.hpp:1710-1721 (the full-page predicate).", size=11, fill=MUTED)
    return s + svg_close()

# ---------------------------------------------------------------- Figure 2: one decode layer as worker 0 sees it (lanes)
# durations in us from exec/results/attnstats-20261002/leaves/<run>/decode_like_layer_* (in-flight snapshots)
PANELS = [
    dict(key="a", title="(a) llama-3.1-8b, tp2, CPU attention, prompt 1024, kernel on vs kill switch: two minibatches, 2 jobs per layer",
         rows=[
             ("worker 0, kernel on", [("job A 87", 87, "busy"), ("job B 87", 87, "busy"), ("not in attention", 73, "idle")], 247),
             ("worker 0, kill switch", [("job A 89", 89, "busy2"), ("job B 89", 89, "busy2"), ("not in attention", 70, "idle")], 248),
         ],
         main="while the workers score minibatch A, the cards run minibatch B's weight multiplies, and the other way round",
         bracket=(0, 174),
         red="the kernel shortens the jobs (busy per job 98 -> 89 us, mean over workers) but not the period.",
         note="period 247 vs 248 us: unchanged. The card lane of the other minibatch sets the period here, so the attention saving does not reach T1 at this prompt length (T1 8.92 -> 8.66 ms = one third of the saving)."),
    dict(key="b", title="(b) qwen3-4b, tp2, CPU attention, prompt 1024, kernel on vs kill switch: one minibatch, 1 job per layer",
         rows=[
             ("worker 0, kernel on", [("not in attention", 83, "idle"), ("waits", 57, "wait"), ("busy: ready pages on AMX, newest page on AVX", 180, "busy"), ("join", 4, "join")], 329),
             ("worker 0, kill switch", [("not in attention", 84, "idle"), ("waits", 60, "wait"), ("busy: every page on the AVX loop", 213, "busy2"), ("join", 5, "join")], 366),
         ],
         main="WQ, WK, WV before the attention, then WO and the feed-forward block after it, and main waits for the workers' output in between",
         bracket=(140, 320),
         red="the kernel shortens this block, 213 -> 180 us (-33 us per layer).",
         note="period 329 vs 366 us. The 33 us of busy per layer (1.2 ms over 36 layers) passed to the forward in full: T4 fell 1.41 ms and T1 1.45 ms per forward."),
    dict(key="c", title="(c) qwen3-4b, tp2, attention on the FPGA (AoF), prompt 1024: the card scores all whole GOFs",
         rows=[
             ("worker 0, either arm", [("not in attention", 101, "idle"), ("waits", 58, "wait"), ("tail", 18, "busy"), ("card", 24, "card")], 201),
         ],
         main="the weight multiplies AND the attention passes over the card-resident K/V. The counters do not split the two",
         bracket=(159, 177),
         red="18 us of scoring 1 to 4 keys per (KV head, layer): no full page on the CPU, the kernel never runs. Then 24 us waiting for the card's partial result.",
         note="both arms measure the same within 1 %. The period still grows with context inside the card: T1 7.75 ms at prompt 1024 and 15.96 ms at 8192, with the join wait at 58 % and 88 % of the workers' busy time."),
    dict(key="d", title="(d) gpt-oss-120b, tp4, AoF, prompt 1024: a sliding-window layer (even layers) and a card layer (odd layers)",
         rows=[
             ("worker 0, sliding-window layer", [("not in attention", 181, "idle"), ("waits", 55, "wait"), ("window 29", 29, "busy"), ("join", 7, "join")], 272),
             ("worker 0, card layer", [("not in attention", 154, "idle"), ("waits", 63, "wait"), ("tail", 24, "busy"), ("join", 4, "join")], 245),
         ],
         main="the weight multiplies of all 36 layers, and attention passes on the card in the 18 card layers only",
         bracket=(236, 265),
         red="the 29 us of scoring the 128-key window on the AVX loop is the only block a 64x8 kernel could touch, and only half of its keys sit in a full page.",
         note="0.04 to 0.05 ms per 10.26 ms forward (est.) = under 1 %. The ceiling with free scoring is 18 x 29 us = 0.53 ms = 5.2 %."),
]

def fig_lanes():
    SCALE = 1.9   # px per us
    GUT = 200     # label gutter
    W = 1180
    rowh = 26; gap = 12; band = 18
    # measure the height first
    def panel_height(p):
        n_read = len(wrap_lines("Reading: " + p["note"], 150))
        return 22 + 18 + 28 + band + len(p["rows"]) * (rowh + gap) + 18 + n_read * 14 + 14
    H = 76 + sum(panel_height(p) for p in PANELS) + 84
    s = svg_open(W, H, "One decode layer as attention worker 0 sees it, four cases, durations to scale")
    s += txt(18, 24, "Figure 2. One decode layer on attention worker 0, four cases. Durations to scale: 1 us = %.1f px." % SCALE, size=14, weight="bold")
    s += txt(18, 42, "8 users, runtron on our half of delphi-3bda, 2026-10-02. Solid = the worker computes. Dashed = the worker waits (for main's next layer, for Q, for this layer's K/V, or for the card).", size=11.5, fill=INK2)
    s += txt(18, 58, "Red bracket = the only slice a kernel changes. The ORDER of the blocks inside a period is schematic: the counters give durations, not start times.", size=11.5, fill=INK2)
    y = 76
    x0 = GUT
    for p in PANELS:
        s += txt(18, y + 14, p["title"], size=12.5, weight="bold")
        y += 22
        s += txt(18, y + 12, "main + cards (schematic): " + p["main"], size=10.5, fill=INK2)
        y += 18
        maxper = max(r[2] for r in p["rows"])
        s += rect(x0, y + 2, maxper * SCALE, 18, fill="#e6f6ef", stroke=AQUA, sw=1)
        s += txt(x0 + 6, y + 15, "main thread + FPGA cards: the weight multiplies and launches of this layer (not timed per phase)", size=10.5, fill=INK2)
        s += txt(18, y + 15, "main + cards", size=11, fill=MUTED)
        y += 28
        # bracket band
        bx1, bx2 = p["bracket"]
        bx1 = x0 + bx1 * SCALE; bx2 = x0 + bx2 * SCALE
        s += line(bx1, y + 5, bx2, y + 5, stroke=RED, sw=2)
        s += line(bx1, y + 5, bx1, y + 10, stroke=RED, sw=2); s += line(bx2, y + 5, bx2, y + 10, stroke=RED, sw=2)
        y += band
        for (lab, segs, per) in p["rows"]:
            s += txt(18, y + 17, lab, size=11.5, fill=INK)
            x = x0
            for (name, dur, kind) in segs:
                w = dur * SCALE
                title = "%s: %d us" % (name, dur)
                if kind == "idle":
                    s += rect(x, y + 3, w, rowh - 6, fill="none", stroke=MUTED, sw=1, dash="4 3", title=title)
                elif kind == "wait":
                    s += rect(x, y + 3, w, rowh - 6, fill="#f2f1ee", stroke=MUTED, sw=1, dash="4 3", title=title)
                elif kind == "busy":
                    s += rect(x, y + 3, w, rowh - 6, fill=BLUE, stroke="none", title=title)
                elif kind == "busy2":
                    s += rect(x, y + 3, w, rowh - 6, fill=ORANGE, stroke="none", title=title)
                elif kind == "join":
                    s += rect(x, y + 3, w, rowh - 6, fill=INK2, stroke="none", title=title)
                elif kind == "card":
                    s += rect(x, y + 3, w, rowh - 6, fill="#e6f6ef", stroke=AQUA, sw=1, dash="4 3", title=title)
                label = name if name.endswith(str(dur)) else "%s %d" % (name, dur)
                if w > len(label) * 6.0 + 8:
                    s += txt(x + 4, y + 18, label, size=10.5, fill=("#ffffff" if kind in ("busy", "busy2", "join") else INK2))
                elif w > 12:
                    s += txt(x + w / 2, y - 3, "%d" % dur, size=10, fill=INK2, anchor="middle")
                x += w
            s += txt(x + 8, y + 18, "period %d us" % per, size=11, fill=INK, weight="bold")
            y += rowh + gap
        s += txt(x0, y + 8, "Red bracket: " + p["red"], size=11, fill=RED)
        y += 18
        t, y = wtxt(x0, y + 8, "Reading: " + p["note"], size=11, fill=INK2, width=150, lh=14)
        s += t
        y += 14
    # scale bar + legend
    s += line(x0, y + 6, x0 + 100 * SCALE, y + 6, stroke=INK, sw=1.5)
    s += line(x0, y + 2, x0, y + 10, stroke=INK, sw=1.5); s += line(x0 + 100 * SCALE, y + 2, x0 + 100 * SCALE, y + 10, stroke=INK, sw=1.5)
    s += txt(x0 + 100 * SCALE + 8, y + 10, "100 us", size=11, fill=INK)
    lx = x0 + 300
    s += rect(lx, y, 14, 12, fill=BLUE); s += txt(lx + 18, y + 10, "busy, kernel on", size=10.5)
    s += rect(lx + 120, y, 14, 12, fill=ORANGE); s += txt(lx + 138, y + 10, "busy, kill switch", size=10.5)
    s += rect(lx + 250, y, 14, 12, fill=INK2); s += txt(lx + 268, y + 10, "join", size=10.5)
    s += rect(lx + 310, y, 14, 12, fill="#f2f1ee", stroke=MUTED, dash="3 2"); s += txt(lx + 328, y + 10, "wait (Q, K/V)", size=10.5)
    s += rect(lx + 430, y, 14, 12, fill="none", stroke=MUTED, dash="3 2"); s += txt(lx + 448, y + 10, "not in attention", size=10.5)
    s += rect(lx + 560, y, 14, 12, fill="#e6f6ef", stroke=AQUA, dash="3 2"); s += txt(lx + 578, y + 10, "waiting for the card", size=10.5)
    t, _ = wtxt(18, y + 30, "Source: decode_like_layer_* leaves of exec/results/attnstats-20261002/leaves/<run>/, read by exec/tron-intuition-20261007/leaves.py: means over the layers of the class (gpt-oss: even and odd layers separately), in-flight snapshots of 98 to 198 forwards. Whole-run totals are in Table 1.", size=10, fill=MUTED, width=190, lh=13)
    s += t
    return s + svg_close()

# ---------------------------------------------------------------- Figure 3: decision tree per page visit
def fig_tree():
    W, H = 1180, 500
    s = svg_open(W, H, "Which path serves one page visit")
    s += txt(18, 26, "Figure 3. Which path serves one page visit (one query, one KV head, one 64-token page). Read left to right.", size=14, weight="bold")
    def q(x, y, w, h, title, lines, fill="#ffffff"):
        return box(x, y, w, h, title, lines, fill=fill, size=11.5)
    y0 = 60
    s += q(18, y0, 200, 96, "1. Attention on the FPGA?", ["(AoF: USE_HW_ATTN unset for", "ingested models such as qwen3", "and gpt-oss, and =0 forces CPU)"])
    s += line(220, y0 + 48, 258, y0 + 48, stroke=INK2, sw=1.5, marker="arr")
    s += txt(224, y0 + 42, "yes", size=10.5, fill=INK2)
    s += q(260, y0 - 4, 250, 104, "Card layer under AoF", ["card: every whole GOF (4 tokens)", "CPU, AVX loop: the 1-to-4-key tail", "kernel: 0 (no full page on the CPU)", "exceptions: prompt < 128, copy lag,", "prefix-cache branch, card store full"], fill="#e6f6ef")
    s += line(118, y0 + 98, 118, y0 + 134, stroke=INK2, sw=1.5, marker="arr")
    s += txt(124, y0 + 122, "no, or a sliding-window layer (never on the card)", size=10.5, fill=INK2)
    y1 = y0 + 138
    s += q(18, y1, 200, 112, "2. Shape fits the kernel?", ["head size 128 AND kv_mul 4", "[amx_attn_iface.hpp:148-150]", "llama-3.1-8b, qwen3-4b: yes", "qwen-2.5-32b (5), llama-70b (8),", "gpt-oss (64 wide, 8): no"])
    s += line(220, y1 + 48, 258, y1 + 48, stroke=INK2, sw=1.5, marker="arr")
    s += txt(224, y1 + 42, "no", size=10.5, fill=INK2)
    s += q(260, y1 + 10, 250, 76, "AVX loop (the dotter)", ["every page, full or partial", "3.6 us per unit at prompt 8192", "(1.7 us hot in L2)"], fill="#fdece5")
    s += line(118, y1 + 114, 118, y1 + 150, stroke=INK2, sw=1.5, marker="arr")
    s += txt(124, y1 + 138, "yes", size=10.5, fill=INK2)
    # third question to the right, lower row
    y2 = y1 + 154
    s += q(18, y2, 200, 76, "3. Full page, visible, AMX on?", ["64 tokens stored, one visible", "range, inside the window, and", "TRON_AMX_DISABLE not set"])
    s += line(220, y2 + 38, 258, y2 + 38, stroke=INK2, sw=1.5, marker="arr")
    s += txt(224, y2 + 32, "yes", size=10.5, fill=INK2)
    s += q(260, y2, 250, 76, "AMX kernel", ["2.9 us per unit at prompt 8192", "(canonical; 0.6 us hot in L2)", "ready pages: all but the newest"], fill="#eef4fc")
    s += line(512, y2 + 38, 550, y2 + 38, stroke=INK2, sw=1.5, marker="arr")
    s += txt(516, y2 + 32, "no", size=10.5, fill=INK2)
    s += q(552, y2, 250, 76, "AVX loop", ["the newest (pending) page in 63", "of every 64 steps, prefill's own", "chunk pages, kill-switch runs"], fill="#fdece5")
    # right column: counts
    s += q(830, y0 - 4, 330, 330, "Per (user, KV head, layer) and step s", [
        "p = prompt + s - 1 = the query's position",
        "",
        "CPU attention, kernel on:",
        "  AMX visits = floor(p / 64)  (+1 when p mod 64 = 63)",
        "  AVX visits = 1 with (p mod 64) + 1 keys",
        "  kill switch: same visits, all AVX",
        "",
        "AoF, steady state:",
        "  AMX visits = 0",
        "  AVX visits = 1 with (p mod 4) + 1 keys",
        "  card: 4 x floor(p / 4) keys",
        "",
        "gpt-oss sliding-window layer (128 keys):",
        "  1 full page + 2 partial pages, all AVX",
        "",
        "Checked against the counters exactly",
        "[attn-stats-compare-QA.html 1.3-1.4]"], fill=PLANE)
    s += txt(18, H - 10, "Sources: self_attention.hpp:1710-1721 (predicate), full.hpp:2850-2889 (card boundary), counter.html 2.2-2.3 (AoF exceptions), tron-amx-distilled.html 4.1 (shape table).", size=10.5, fill=MUTED)
    return s + svg_close()

# ---------------------------------------------------------------- Figure 4: unit cost dumbbells
UNITS = [  # (label, AVX, canonical AMX, mirror/VNNI-K AMX)  us, Tron worker-0 medians 2026-09-01 (single-attn-20260901/summary.json)
    ("prompt 8192 (pages from DRAM)", 3.64, 2.89, 2.66),
    ("prompt 2048", 2.80, 2.14, 2.07),
    ("prompt 256 (pages in cache)", 2.88, 2.38, 1.36),
    ("hot in L2, benchmark (no data wait)", 1.68, None, 0.62),
]

def fig_units():
    W, H = 1180, 365
    s = svg_open(W, H, "Cost of one unit on each code path")
    s += txt(18, 26, "Figure 4. Cost of one unit (one query x one page x one KV head, 32 KiB read) on each code path, in us.", size=14, weight="bold")
    s += txt(18, 44, "Rows 1 to 3 measured inside tron (worker 0 medians over 510 tokens, 1 user, 2026-09-01). Row 4 from the unit benchmark outside tron (2026-09-03, clock-scaled).", size=11.5, fill=INK2)
    x0 = 330; xw = 700; vmax = 4.0
    def X(v): return x0 + v / vmax * xw
    ytop = 84; rowh = 44
    # grid
    for v in range(0, 5):
        s += line(X(v), ytop - 10, X(v), ytop + rowh * len(UNITS) - 6, stroke=GRID, sw=1)
        s += txt(X(v), ytop + rowh * len(UNITS) + 10, "%d us" % v, size=11, fill=MUTED, anchor="middle")
    # memory floor
    s += line(X(2.49), ytop - 14, X(2.49), ytop + rowh * len(UNITS) - 6, stroke=INK2, sw=1.2, dash="5 3")
    s += txt(X(2.49) + 5, ytop - 16, "memory time 2.49 us = 32 KiB at 13.1 GB/s per core (27 cores reading)", size=10.5, fill=INK2)
    for i, (lab, avx, canon, mirror) in enumerate(UNITS):
        y = ytop + i * rowh + 14
        s += txt(x0 - 12, y + 4, lab, size=12, fill=INK, anchor="end")
        lo = min(v for v in (avx, canon, mirror) if v is not None)
        s += line(X(lo), y, X(avx), y, stroke=GREY, sw=3)
        s += circle(X(avx), y, 6.5, ORANGE, title="AVX %.2f us" % avx)
        s += txt(X(avx) + 11, y + 4, "AVX %.2f" % avx, size=11, fill=INK)
        if canon is not None:
            s += circle(X(canon), y, 6.5, BLUE, title="canonical AMX %.2f us" % canon)
            s += txt(X(canon), y - 11, "canon %.2f" % canon, size=10.5, fill=INK, anchor="middle")
        s += circle(X(mirror), y, 6.5, "#ffffff", stroke=BLUE, sw=2.2, title="mirror / VNNI-K AMX %.2f us" % mirror)
        s += txt(X(mirror), y + 20, ("AMX %.2f" if canon is None else "mirror %.2f") % mirror, size=10.5, fill=INK, anchor="middle")
    # legend
    ly = ytop + rowh * len(UNITS) + 34
    s += circle(x0, ly, 6, ORANGE); s += txt(x0 + 12, ly + 4, "AVX loop (dotter)", size=11.5)
    s += circle(x0 + 150, ly, 6, BLUE); s += txt(x0 + 162, ly + 4, "AMX, canonical kernel (in main since 2026-09-15)", size=11.5)
    s += circle(x0 + 470, ly, 6, "#ffffff", stroke=BLUE, sw=2.2); s += txt(x0 + 482, ly + 4, "AMX reading a VNNI K copy (mirror; PR 4424, open)", size=11.5)
    t, _ = wtxt(18, ly + 28, "Takeaway: once the pages come from DRAM the unit sits near the memory time whatever the arithmetic does. AMX saves 0.5 to 1.0 us of 3.6 us (1.26x with the canonical kernel), not the 1.1 us it saves when the page is hot. Sources: rows 1-3 PR3879/make-sense-amx-vs-avx.html 7.2.1, and row 4 perf-model/index.html section 5.", size=11, fill=INK2, width=170, lh=14)
    s += t
    return s + svg_close()

# ---------------------------------------------------------------- Figure 5: llama-8b gains, CI harness
LEVERS_PROMPT = {"2 users per engine": [(1024, 0.21), (2048, 1.55), (3000, 7.30), (4096, 8.19)],
                 "8 users per engine": [(1024, 10.79), (2048, 13.99), (4096, 14.01)]}
LEVERS_USERS = [(2, 0.21), (4, 4.75), (8, 10.79)]

def fig_levers():
    W, H = 1180, 345
    s = svg_open(W, H, "llama-3.1-8b decode gain of the canonical AMX package over the nightly package, CI harness")
    s += txt(18, 26, "Figure 5. llama-3.1-8b decode gain, canonical-AMX package vs the nightly package, CI harness, nightly layout, whole machine.", size=14, weight="bold")
    # left chart: gain vs prompt
    lx0, ly0, lw, lh = 80, 70, 470, 190
    def LX(p): return lx0 + (p - 1024) / (4096 - 1024) * lw
    def LY(g): return ly0 + lh - g / 16.0 * lh
    for g in (0, 4, 8, 12, 16):
        s += line(lx0, LY(g), lx0 + lw, LY(g), stroke=GRID, sw=1)
        s += txt(lx0 - 8, LY(g) + 4, "+%d %%" % g, size=11, fill=MUTED, anchor="end")
    for p in (1024, 2048, 3000, 4096):
        s += txt(LX(p), ly0 + lh + 18, str(p), size=11, fill=MUTED, anchor="middle")
    s += txt(lx0 + lw / 2, ly0 + lh + 36, "prompt length, tokens", size=11.5, fill=INK2, anchor="middle")
    s += txt(lx0, ly0 - 16, "gain vs prompt length", size=12.5, fill=INK, weight="bold")
    for name, pts, col in (("2 users per engine", LEVERS_PROMPT["2 users per engine"], MUTED), ("8 users per engine", LEVERS_PROMPT["8 users per engine"], BLUE)):
        for (p1, g1), (p2, g2) in zip(pts, pts[1:]):
            s += line(LX(p1), LY(g1), LX(p2), LY(g2), stroke=col, sw=2)
        for p, g in pts:
            s += circle(LX(p), LY(g), 5, col, title="%s, prompt %d: +%.2f %%" % (name, p, g))
            s += txt(LX(p) + (8 if p != 4096 else -8), LY(g) - 8, "+%.1f" % g, size=10.5, fill=INK, anchor=("start" if p != 4096 else "end"))
        s += txt(LX(pts[-1][0]) - 8, LY(pts[-1][1]) + 16, name, size=11, fill=col, anchor="end", weight="bold")
    # right chart: gain vs users per engine at prompt 1024
    rx0, ry0, rw, rh = 680, 70, 420, 190
    def RX(u): return rx0 + (u - 2) / 6 * rw
    def RY(g): return ry0 + rh - g / 16.0 * rh
    for g in (0, 4, 8, 12, 16):
        s += line(rx0, RY(g), rx0 + rw, RY(g), stroke=GRID, sw=1)
        s += txt(rx0 - 8, RY(g) + 4, "+%d %%" % g, size=11, fill=MUTED, anchor="end")
    for u in (2, 4, 8):
        s += txt(RX(u), ry0 + rh + 18, str(u), size=11, fill=MUTED, anchor="middle")
    s += txt(rx0 + rw / 2, ry0 + rh + 36, "users per engine (prompt 1024)", size=11.5, fill=INK2, anchor="middle")
    s += txt(rx0, ry0 - 16, "gain vs users per engine", size=12.5, fill=INK, weight="bold")
    pts = LEVERS_USERS
    for (u1, g1), (u2, g2) in zip(pts, pts[1:]):
        s += line(RX(u1), RY(g1), RX(u2), RY(g2), stroke=BLUE, sw=2)
    for u, g in pts:
        s += circle(RX(u), RY(g), 5, BLUE, title="%d users per engine, prompt 1024: +%.2f %%" % (u, g))
        s += txt(RX(u) + 8, RY(g) - 8, "+%.1f" % g, size=10.5, fill=INK)
    t, _ = wtxt(18, H - 26, "Both levers raise the attention share of the step. The 2-user cells are the nightly layout (8 users over 4 engines). Source: CI-test/status/llama-3.1-8b.html (campaigns l8b-levers-20260919 and l8b-8u4k-20260920; nightly deb 3faba6d0 vs canonical deb 0594dc54; 3 interleaved passes).", size=11, fill=INK2, width=170, lh=14)
    s += t
    return s + svg_close()

# ====================================================================== prose
def P(s): return "<p>%s</p>\n" % s
def H2(i, s): return '<h2 id="s%s">%s</h2>\n' % (i, s)
def H3(i, s): return '<h3 id="s%s">%s</h3>\n' % (i, s)
def UL(items): return "<ul>\n" + "".join("<li>%s</li>\n" % i for i in items) + "</ul>\n"
def OL(items): return "<ol>\n" + "".join("<li>%s</li>\n" % i for i in items) + "</ol>\n"
def CODE(s): return "<pre><code>%s</code></pre>\n" % esc(s)
def TABLE(head, rows, cls="", caption=None):
    s = '<table class="%s">\n' % cls
    if caption: s += "<caption>%s</caption>\n" % caption
    s += "<thead><tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>\n<tbody>\n"
    for r in rows:
        s += "<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>\n"
    return s + "</tbody></table>\n"
def FIG(svg, cap): return '<figure>%s<figcaption>%s</figcaption></figure>\n' % (svg, cap)
def DL(items): return "<dl>\n" + "".join("<dt>%s</dt><dd>%s</dd>\n" % (k, v) for k, v in items) + "</dl>\n"
def NOTE(s): return '<div class="note">%s</div>\n' % s

SHORT = """
<div class="short"><b>Short version.</b> A decode step of tron is one forward over all layers for all users of one engine, and its time is other work (the weight multiplies on the FPGA cards, about flat in context) plus attention (which re-reads the whole context every step, so it grows with prompt length and with users per engine). AMX changes only the attention page visits that run on the CPU, on a full 64-token page, for a model whose attention shape fits the kernel. So the estimate by hand is: count those visits, price them with the per-unit costs, and pass the saving to the forward through the layer's waits and overlaps.
<ul>
<li><b>llama-3.1-8b</b> gains: +3 % at 8 users and prompt 1024 in lockstep decode, +16 % at prompt 8192, +11 to +14 % in the CI harness at 8 users per engine.</li>
<li><b>qwen-2.5-32b</b> gains nothing today. It fails the kernel's shape gate (5 query heads per KV head), so every page visit stays on the AVX loop.</li>
<li><b>gpt-oss</b> runs attention on the FPGA and keeps only 1-to-4-key tails and 128-key sliding windows on the CPU. A kernel for its shape could gain under 1 % of decode throughput (est.).</li>
</ul></div>
"""

WORDS = [
    ("tron, runtron, rinzler", "tron is Positron's inference program. runtron is its command-line tool: one process, a fixed number of users, all users decode in lockstep. rinzler is the production server: continuous batching behind a proxy, started by platformd."),
    ("engine, tp2, tp4", "An engine is one tron process bound to FPGA cards and CPU cores. tp2 splits every weight multiply over 2 cards, tp4 over 4. On delphi-3bda (the test server, two Intel Xeon 6962P sockets) a tp2 engine has 28 application cores (one main thread plus 27 workers) and a tp4 engine 56 (main plus 55)."),
    ("nightly, CI harness, users per engine", "The nightly is the systems_test performance run on delphi-3bda. Its harness spreads 8 users over 4 engines at tp2 (2 users per engine) or 2 engines at tp4 (4 per engine). The 32-user llama-3.1-8b row runs 8 users per engine. U in the formulas below is always users per engine."),
    ("AMX, AVX, dotter, kernel", "AMX is Intel's tile matrix instruction set (bf16 tiles of 16 rows by 64 bytes, multiplied by one instruction). AVX is the 512-bit vector set. tron's AVX attention loop is called the dotter. \"The kernel\" below means tron's AMX attention kernel (canonical form, in main since 2026-09-15)."),
    ("AoF, CPU attention", "AoF = attention on the FPGA: the card scores the stored keys and values, and the CPU keeps a short tail. It is the default for ingested models (qwen3-4b, gpt-oss) when USE_HW_ATTN is unset. USE_HW_ATTN=0 forces CPU attention. Hand-written plugins (llama, qwen-2.5) default to CPU attention."),
    ("kill switch", "TRON_AMX_DISABLE=1: the AMX binary with the kernel switched off. Every page visit then runs on the AVX loop. Same visits, same key counts, different speed."),
    ("bf16, KV cache, KV page", "bf16 is the 16-bit floating-point format of the keys, values and queries. The KV cache stores every past token's keys and values per layer per KV head, in pages of 64 tokens: 16 KiB of keys plus 16 KiB of values = 32 KiB per page."),
    ("KV head, kv_mul, head size", "Models store fewer key/value heads than query heads. kv_mul = query heads per KV head (also called the GQA ratio). Head size = numbers per head. The kernel serves exactly head size 128 and kv_mul 4 [amx_attn_iface.hpp:148-150]."),
    ("unit, page visit", "One query token (its kv_mul query heads) scored against one KV page of one KV head: the QK multiply, the softmax pieces, the PV multiply and the running-state update. It reads the page's 32 KiB. \"Visit\" and \"unit\" are the same thing: the counters say visit, the timing pages say unit."),
    ("forward, decode step, token job, TPS", "A forward is one pass over all layers. In decode it produces one new token for each user: one token job per user. TPS = tokens per second per user. In lockstep decode (runtron) TPS = 1 / forward time."),
    ("prefill, chunk, TTFT", "The prompt is scored in chunks of 128 tokens per user per forward (TRON_PER_USER_PROMPT_CHUNK_LIMIT, default 128 [libtron.hpp:194-205]). TTFT = time to first token, which the harness divides into the prompt length to print a prefill rate."),
    ("minibatch", "The users of one forward can be split into groups whose card work and CPU attention overlap. The hand-written llama plugin allows this (max_minibatches = -1 [llama.hpp:183]) and runs 8 users as two minibatches of 4. Ingested plugins run one minibatch."),
    ("attention worker, main thread, job, ready pass, pending pass, join", "The main thread runs the plugin schedule and launches the card jobs. Attention workers run the attention jobs: each layer's attention operation is split over the workers as (KV head, page range) sections, one job per worker. A job has a ready pass (pages that were complete before this layer), a pending pass (the newest page, after this layer's K/V landed) and a join (the fold of partial results across workers)."),
    ("T1 to T5", "The five timers of the attention stats (PR 4596): T1 = wall time of a forward. T2 = busy time of one attention job (both passes plus the join, without the K/V wait). T3 = wall time of a job as worker 0 sees it, waits included. T4 = layer period on worker 0 (from the start of one layer's job to the start of the next). T5 = join wait, inside T2."),
    ("GOF, shard, engagement", "GOF = group of four tokens, the card's copy and scoring unit. A shard is 1024 tokens of K/V on the card. Engagement 127 = the card scores positions from 127 on. Earlier positions stay on the CPU."),
    ("sliding window", "A layer whose attention sees only the last N keys. gpt-oss uses N = 128 on its even layers. Such layers never run on the card [model.hpp:1554-1556 per attn-stats-compare-QA.html 3.5]."),
    ("prompt N", "A prompt of N tokens. Every run quoted here then generates 256 tokens per user, so the context a decode step reads is N plus the tokens generated so far."),
    ("lever", "A setting of the cell that moves the gain: users per engine, prompt length, attention mode."),
    ("est., Insufficient data", "est. marks an estimate. Insufficient data marks a quantity nobody measured, with the measurement named."),
]

RULES = [
    ("A decode step is other work plus attention, and only attention grows.",
     "The weight multiplies run on the cards and take about the same time whatever the context. Attention re-reads every stored page each step, so its time grows with context and with users per engine. Measured attention share of a worker's forward: 16 / 31 / 62 % at prompt 256 / 2048 / 8192 for one qwen3-4b user on the AVX path [make-sense-amx-vs-avx.html section 7]. At 8 users and prompt 1024 it is 56 % for qwen3-4b and 67 % for llama-3.1-8b. At prompt 8192 llama reaches 93 % (Table 1)."),
    ("Attention is a loop over page visits, and the count is arithmetic.",
     "Visits per decode step = U users x L layers on the CPU x KV heads x pages per user (context / 64, rounded up). The attention workers share them. Example: qwen3-4b, 8 users, context 1152 (prompt 1024 plus 128 generated tokens): 8 x 36 x 8 x 18 = 41,472 visits, 2,074 per worker with 20 workers."),
    ("A unit costs about 3 us, and AMX removes 0.5 to 1.0 us of it.",
     "One unit (32 KiB read) takes 3.64 us on the AVX path and 2.89 us with the canonical kernel at prompt 8192, where the pages come from DRAM. At prompt 2048 the pair is 2.80 vs 2.14 us, and at prompt 256 (pages in cache) 2.88 vs 2.38 us [make-sense-amx-vs-avx.html 7.2.1]. Hot in the L2 cache the two paths take 1.68 and 0.62 us [perf-model/index.html section 5]. The memory time of a unit is 2.49 us (32 KiB at 13.1 GB/s per core while 27 cores read). So the arithmetic can be 33x faster and the unit still shortens by only 1.26x, because the bytes set the lower bound."),
    ("Pass the attention saving to the forward through the layer's overlap.",
     "With one minibatch (ingested plugins: qwen3-4b, gpt-oss) a shorter attention job shortens the layer period 1:1. When the kernel was enabled, qwen3-4b's attention busy fell 33 us per layer (1.2 ms over 36 layers), T4 fell 1.41 ms and T1 fell 1.45 ms per forward. With two minibatches (llama at 8 users) the cards' work for the other minibatch overlaps the attention, and at prompt 1024 the period did not move at all (247 vs 248 us) although busy per job fell 9 %. At prompt 8192 attention is 93 % of the forward and the saving passed 1:1 again (period 1405 -> 1207 us). Working rule for llama: one third at short prompts, 1:1 at long prompts (section 3)."),
    ("The path is chosen per page visit, not per model and not per token.",
     "Figure 3 is the decision. Under AoF the card scores every whole GOF and the CPU keeps a 1-to-4-key tail, so the kernel's 64-key unit never fills: 0 AMX visits in the steady state. A sliding-window layer never goes to the card. The shape gate (head size 128 and kv_mul 4) is compile-time. llama-3.1-8b and qwen3-4b pass it. qwen-2.5-32b (kv_mul 5), llama-3.1/3.3-70b (kv_mul 8) and gpt-oss (head size 64, kv_mul 8) do not. A partial page always takes the AVX loop, so even under CPU attention the newest page is AVX in 63 of every 64 steps."),
    ("Keys are not time.",
     "The counters count keys scored per path. Convert keys to visits, and visits to time with the unit costs. Keep the waits fixed: the join wait (T5) and the K/V wait do not shrink when a kernel is faster. gpt-oss scores 10.2 % of its decode keys on the CPU, which is 6.3 % of a worker's forward time, of which a kernel could remove under 1 % (section 6, example C)."),
    ("Under AoF the step still grows with context, inside the card.",
     "qwen3-4b at 8 users: T1 = 7.75 ms per forward at prompt 1024 and 15.96 ms at prompt 8192. The join wait (the workers waiting for the card's partial results) rises from 58 % to 88 % of the workers' busy time [attn-stats-compare.md section 7]. The CPU build matters little there: AMX on vs off differ by under 1 % in both cells. AoF beats CPU attention with AMX by 1.6x at prompt 1024 (126.6 vs 79.5 TPS) and 3.6x at prompt 8192 (61.5 vs 17.1 TPS, runtron 8 users) [attn-stats-compare.md section 1, and q4b-rt8u-20260922]."),
    ("Users per engine is the lever in CI, not users in total.",
     "The nightly's 8 users are 2 per engine at tp2 and 4 per engine at tp4. llama-3.1-8b gains +0.2 / +4.8 / +10.8 % at 2 / 4 / 8 users per engine (prompt 1024) and +14.0 % at 8 users per engine with prompt 2048 or 4096 (Figure 5). The same model at 2 users per engine and prompt 1024 shows nothing, which is what the nightly's 8-user llama row measures."),
    ("Prefill is the other place where the kernel counts.",
     "The prompt is scored 128 tokens per user per forward. The kernel takes the full pages of earlier chunks, so under CPU attention prefill forwards run 1.7x to 2.5x faster per attention job [attn-stats-compare.md section 7]: llama-3.1-8b, 8 users, prompt 8192: TTFT 34.6 s with the kernel vs 78.8 s without. Under AoF the card does that work and the kernel sees only copy-lag pages (0.6 % of the prefill keys at prompt 8192). The nightly reports prefill as prompt length divided by TTFT. Nothing on the server times prefill."),
    ("Name the denominator, and check that AMX actually ran.",
     "Three pairs are easy to mix: kill switch vs a clean AVX build (the switch costs 0 to 5 points by itself, build-dependent), runtron lockstep vs the CI harness (section 9, edge 1), and users in total vs per engine. A TPS step on the night AMX arrived is not proof: on 2026-09-23 qwen-3-4b tp4 rose +18.3 % and gpt-oss-120b +12.8 %, both AoF rows with 0 AMX visits, in a package with two other merges [Was-AMX-boosting-all-models.html section 1]. Proof is the stats (ready_amx_visits > 0) or the AMX busy-cycle counter (section 8, card 4)."),
]

# anchors table: runtron 8 users, our half, tron main dd0f942c75, 2026-10-02 (attn-stats-compare.md sections 1 and 7)
ANCHORS = [
    # cell, attention, TPS on, TPS off, gain, T1 on, T1 off, busy/job on, busy/job off, jobs per worker per forward, share
    ("llama-3.1-8b tp2, prompt 1024", "CPU", 113.87, 110.66, 8.66, 8.92, 91, 103, 64, "67 %"),
    ("llama-3.1-8b tp2, prompt 8192", "CPU", 24.84, 21.42, 39.64, 46.05, 574, 679, 64, "93 %"),
    ("qwen3-4b tp2, prompt 1024", "CPU (USE_HW_ATTN=0)", 79.48, 71.20, 12.48, 13.93, 193, 229, 36, "56 %"),
    ("qwen3-4b tp2, prompt 1024", "AoF", 126.59, 127.69, 7.75, 7.68, 43, 43, 36, "20 % (58 % of it join wait)"),
    ("qwen3-4b tp2, prompt 8192", "AoF", 60.53, 60.86, 15.96, 15.87, 242, 243, 36, "55 % (88 % of it join wait)"),
    ("gpt-oss-120b tp4, prompt 1024", "AoF", 96.07, 96.22, 10.26, 10.24, 32, 31, 36, "11 %"),
]

def anchors_table():
    rows = []
    for (cell, attn, on, off, t1on, t1off, bon, boff, jobs, share) in ANCHORS:
        gain = (on / off - 1) * 100
        rows.append((cell, attn, "%.1f" % on, "%.1f" % off, "%+.1f %%" % gain, "%.2f / %.2f" % (t1on, t1off), "%d / %d" % (bon, boff), str(jobs), share))
    return TABLE(["cell (8 users, runtron, our half)", "attention", "TPS per user, AMX on", "kill switch", "gain", "T1 ms per forward, on / off", "T2 busy us per job, on / off", "jobs per worker per forward", "attention busy share of T1 (AMX on)"], rows, cls="num",
                 caption="Table 1. The six cells of 2026-10-02 (tron main dd0f942c75, 256 generated tokens per user). Share = busy per job x jobs per worker per forward / T1. Source: attn-stats-compare.md sections 1 and 7.")

GEOM = [
    ("llama-3.1-8b", "32", "32", "8", "128", "4", "CPU (hand-written plugin)", "pass", "the measured AMX case: +3 to +16 % runtron, +11 to +14 % CI at 8 users per engine", "llama.hpp:1583"),
    ("llama-3.1 / 3.3-70b", "80", "64", "8", "128", "8", "CPU", "fail (kv_mul 8)", "0 today; a width-8 kernel would be new code", "llama.hpp:1584"),
    ("qwen-2.5-32b", "64", "40", "8", "128", "5", "CPU", "fail (kv_mul 5)", "0 today; a kv_mul-5 kernel would be new code (section 6, example D)", "llama.hpp:1594"),
    ("qwen3-4b", "36", "32", "8", "128", "4", "AoF (ingested, force_hw_attn)", "pass", "0 under AoF in decode; +12 to +18 % under CPU attention", "qwen_3_4b_instruct_2507.hpp:28-41"),
    ("gpt-oss-120b", "36 = 18 sliding (128) + 18 full", "64", "8", "64", "8", "AoF (ingested)", "fail (64 wide, kv_mul 8)", "0 today; a 64x8 kernel: under 1 % of decode (est.)", "ingested_gpt_oss_120b.hpp:28-52"),
    ("gpt-oss-20b", "24 = 12 sliding + 12 full", "64", "8", "64", "8", "AoF (ingested)", "fail", "same as the 120b", "rampup/gptoss-estimate.html section 1"),
]

def geometry_table():
    return TABLE(["model", "layers", "query heads", "KV heads", "head size", "kv_mul", "default attention", "kernel shape gate", "what the map says", "source"], GEOM, cls="",
                 caption="Table 2. Attention geometry of the models in question, read from the tron sources (tron-amx checkout, 85fc8ff4de). The gate is compile-time: a failing model never compiles the AMX branch [self_attention.hpp, amx_shape_ok].")

def section_recipe():
    s = H2(6, "6. The recipe: six steps, then four worked examples")
    s += P("The steps turn the map into a number. Each example then runs the steps on one of your models and compares with a measurement when one exists.")
    s += OL([
        "<b>Fix the cell.</b> Model, tp, users per engine U, prompt length, attention mode (AoF or CPU), and the two arms (kill switch vs kernel, or AVX build vs AMX build). Take the context at mid-run: prompt plus 128 generated tokens.",
        "<b>Decide what is on the CPU.</b> Figure 3: under AoF only the 1-to-4-key tails and the sliding-window layers are on the CPU, and no page is full. Under CPU attention every page is on the CPU.",
        "<b>Count the kernel-eligible visits per forward per worker.</b> U x (layers on the CPU) x KV heads x full pages per user, divided by the attention workers (Table 1 gives the worker counts the split heuristic chose). Only models that pass the shape gate have any.",
        "<b>Price them.</b> Saving per worker per forward = visits x (AVX unit - AMX unit) at that context: 0.50 us at prompt 256, 0.66 us at 2048, 0.75 us at 8192 (Figure 4). This is the drop in T2 summed over a worker's jobs.",
        "<b>Pass the saving to the forward.</b> One minibatch, or attention over 90 % of the forward: 1:1. llama at 8 users and a short prompt: about one third. New T1 = T1 - pass x saving. Gain = T1 / new T1 - 1.",
        "<b>Check against an anchor.</b> Table 1, Figure 5 or the nightly rows. When no anchor exists, name the cell to run (TRON_ATTN_STATS=1, both arms) instead of trusting the number.",
    ])
    # Example A
    s += H3("6a", "Example A: llama-3.1-8b, tp2, 8 users, CPU attention, kill switch vs kernel")
    s += P("Prompt 1024. Context at mid-run 1152 tokens = 18 pages per user, 17 of them full. Visits = 8 users x 32 layers x 8 KV heads x 17 full pages = 34,816 per forward. The run used 23 to 24 attention workers [Table 1 source], so about 1,450 visits per worker. At this context the pages are between the cache and the DRAM regime, so the unit saving is 0.50 to 0.66 us: 0.73 to 0.96 ms per worker per forward (est.). Measured: busy per job fell from 103 to 91 us over 64 jobs per worker per forward = 0.77 ms. The two minibatches overlap most of it with the cards' work for the other minibatch: the pass is about one third, so T1 drops 0.24 to 0.32 ms of 8.92 ms = +2.8 to +3.7 % (est.). Measured: T1 8.92 -> 8.66 ms, TPS 110.7 -> 113.9 per user = +2.9 %.")
    s += P("Prompt 8192. Context 8320 tokens = 130 pages, 129 full. Visits = 8 x 32 x 8 x 129 = 264,192 per forward, 26 workers, 10,161 per worker. Saving = 10,161 x 0.75 us = 7.6 ms per worker per forward (est.). Measured drop of T2 over the 64 jobs: (679 - 574) us x 64 = 6.7 ms. Attention is 93 % of the forward, so the pass is 1:1: T1 46.05 -> 38.4 to 39.3 ms = +17 to +20 % (est.). Measured: 39.64 ms, TPS 21.4 -> 24.8 = +16.0 %.")
    s += P("The same model in the CI harness at 8 users per engine and prompt 1024 gains +10.8 % (nightly package vs canonical package, 3 passes) and +12.9 % (same binary, kill switch, rinzler) [CI-test/status/llama-3.1-8b.html, and VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html]. The map's decode-only arithmetic gives +3 % for that cell. The gap is the first edge of the map (section 9).")
    # Example B
    s += H3("6b", "Example B: qwen3-4b, tp2, 8 users, AoF (the deployed mode)")
    s += P("Step 2 ends the estimate. The card scores every whole GOF of every user from position 127 on. The CPU keeps (p mod 4) + 1 keys per (user, KV head, layer) per step, 1 to 4 keys, mean 2.49. No page is ever full on the CPU, so the kernel-eligible visits are 0 and the predicted gain is 0. Measured: TPS -0.9 % at prompt 1024 and -0.5 % at prompt 8192 with the kernel on, busy per job equal within 1 %, 0 AMX visits in both cells (Table 1, and attn-stats-compare.md section 2.1).")
    s += P("The useful question for qwen3-4b is therefore AoF vs CPU attention, not AMX vs AVX: at prompt 1024 and 8 users AoF gives 126.6 TPS per user against 79.5 with CPU attention and the kernel (1.6x). At prompt 8192 the ratio is 3.6x (61.5 vs 17.1 TPS, runtron 8 users, 2026-09-22) [CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html section 7]. The kernel matters for this model only where the card is absent, full (HBM exhaustion), or bypassed (prefix-cache branches, prompts under 128 tokens) [counter.html section 2.3].")
    # Example C
    s += H3("6c", "Example C: gpt-oss-120b, tp4, 8 users, AoF, prompt 1024 (the Scratch page question)")
    s += P("The question on the Scratch page was whether the 10 % of decode keys that gpt-oss scores on the CPU means a kernel for its shape would pay. The map answers in four lines.")
    s += OL([
        "<b>What is on the CPU.</b> The 18 card layers keep a 1-to-4-key tail (40,960 AVX keys per layer per run, no full page). The 18 sliding-window layers score 128 keys per query on the CPU: 1 full page plus 2 partial pages in 252 of the 256 steps. That is 2,097,152 AVX keys per layer per run (8 users x 8 KV heads x 128 keys x 256 steps) [attn-stats-compare.md section 6, and the exit report's per-layer line].",
        "<b>Kernel-eligible visits.</b> One full page per (user, KV head, sliding layer) per step: 8 x 8 x 18 = 1,152 per forward, holding half of those layers' keys. Today the shape gate (64 wide, kv_mul 8) sends them to the AVX loop.",
        "<b>Time.</b> Busy per job in a sliding-window layer is 36.0 us (29.4 us scoring plus 6.6 us join wait), 18 jobs per worker per forward = 0.65 ms = 6.3 % of the 10.26 ms forward (Figure 2d). The join wait does not change with a kernel, so the ceiling for any kernel is the 0.53 ms of scoring = 5.2 % of T1.",
        "<b>Price.</b> On the fitting models the kernel cut decode busy per job by 12 to 16 % while taking 96 to 99 % of the keys (Table 1: llama 103 -> 91 us, qwen 229 -> 193 us). Half the keys at that rate is 6 to 8 % of 0.65 ms = 0.04 to 0.05 ms per forward = 0.4 to 0.5 % of T1 (est.). Pass 1:1 (one minibatch). So the answer is: under 1 % of decode TPS, with 5.2 % as the ceiling.",
    ])
    s += P("Two cautions that the map makes visible. The 128-key window of one KV head is 32 KiB and stays in cache across steps. So the per-key cost there is the cache-regime one, not the 3.6 us DRAM unit (Insufficient data for the exact value: only a built kernel measures it). Prefill has more room than decode. The sliding layers' attention busy is 8.7 % of a 335 ms prompt forward, and the kernel's prefill cut on the fitting models is 1.7x to 2.5x per job. So 3 to 4 % of TTFT is reachable (est.) [Notion Scratch page 2026-10-07, and the leaves prompt_or_mixed_layer_*].")
    # Example D
    s += H3("6d", "Example D: qwen-2.5-32b, tp2, nightly (2 users per engine), CPU attention")
    s += P("qwen-2.5-32b is a hand-written plugin configuration (model_type::llama), so it defaults to CPU attention like llama [llama.hpp:1594, and hw_attn_config.hpp:12-15]. Its attention has 40 query heads over 8 KV heads: kv_mul 5 with head size 128. The gate fails, the AMX branch is not compiled for it, and every page visit runs on the AVX loop [tron-amx-distilled.html 4.1.1]. Predicted AMX gain today: 0. The nightly row moved +1.2 to +1.6 % between the pre and post windows, the same small step as nine other rows without the kernel, which arrived six nights after the AMX package [Was-AMX-boosting-all-models.html sections 1 and 2].")
    s += P("If a kv_mul-5 kernel existed, the map gives the shape of the gain but not its size. Visits per forward at 2 users per engine and prompt 1024 = 2 x 64 layers x 8 KV heads x 17 full pages = 17,408, about 645 per worker over 27 workers. At 0.5 to 0.66 us saved per visit that is 0.3 to 0.4 ms per forward (est.). The forward time of that row is at most 28 ms (1 / 35.3 TPS per user) [nightly table], so the gain at that cell is at least +1 % and probably a few percent (est.). The missing input is the attention share of this model's forward, which also decides the 8-users-per-engine case. Insufficient data: one TRON_ATTN_STATS=1 runtron cell of qwen-2.5-32b-it-fast tp2 at 2 and 8 users, prompt 1024 and 8192, gives T2 x 64 jobs / T1 directly, with no kernel needed.")
    return s

def section_internalize():
    s = H2(2, "2. What to internalize: ten rules with their numbers")
    s += P("These are the facts to keep in memory. Each has one measured number attached so that a guess can be checked against it.")
    for i, (title, body) in enumerate(RULES, 1):
        s += '<div class="rule"><div class="rule-t">%d. %s</div><div class="rule-b">%s</div></div>\n' % (i, title, body)
    return s

def section_lanes():
    s = H2(3, "3. One decode layer, four ways")
    s += P("Figure 2 draws the same thing for four cells: one layer's period on attention worker 0, split into the part outside attention, the waits, the busy part and the join. The red bracket marks the only block a kernel changes. The numbers are means over the layers of the class from the in-flight FUSE snapshots of the 2026-10-02 runs. Table 1 carries the whole-run totals.")
    s += FIG(fig_lanes(), "Figure 2. One decode layer on attention worker 0 in four cells, durations to scale. Panels (a) and (b) show the kernel's effect under CPU attention: the busy block shrinks in both, but only the single-minibatch model (b) shortens its period. Panels (c) and (d) show AoF: the CPU's blocks are tails and windows, and the card's time hides in the waits.")
    s += anchors_table()
    s += P("How to read Table 1 for an estimate: the share column is the most a kernel can touch. The gain column is what it did touch. The difference between them is rule 3 (the bytes set the lower bound) and rule 4 (the overlap).")
    return s

def section_cards():
    s = H2(8, "8. What to keep handy")
    s += P("Six cards. Cards 1 to 3 are the inputs of the recipe. Cards 4 to 6 are how to measure and where to read more.")
    s += H3("8a", "Card 1: model geometry")
    s += geometry_table()
    s += H3("8b", "Card 2: machine and engine numbers (delphi-3bda)")
    s += UL([
        "Engine cores: tp2 = 28 application cores (main thread + 27 workers), tp4 = 56 (main + 55). The card drivers use separate dev cores. Our half of the machine = socket 1 with cards 90/93/b9/bc [exec/results/attnstats-20261002/rt-results.txt placement lines].",
        "Attention workers the split heuristic actually used at 8 users: qwen3-4b 20 of 27, llama-3.1-8b 23-24 (prompt 1024) and 26 (prompt 8192), gpt-oss-120b 40 of 55 at tp4 [exit report model lines, active_workers, and attn-stats-compare.md section 7].",
        "Per-core streaming rate from DRAM: 19.8 GB/s for one core alone, 13.1 GB/s per core with 27 cores reading. Memory time of one 32 KiB unit: 2.49 us. DRAM latency 127 to 147 ns [perf-model/index.html sections 5 and 10].",
        "Caches: L2 2 MiB per core, L3 432 MiB per socket. One qwen3-4b user at prompt 8192 reads 36 layers x 8 KV heads x 130 pages x 32 KiB = 1,170 MiB per decode step, 2.7x the L3, so the pages come from DRAM [perf-model/index.html, Words used here].",
        "Clocks while busy: 3.74 GHz on the AVX path, 3.60 GHz with AMX tiles in use on 27 cores (the AMX license clock) [perf-model/index.html section 5]. The stats count TSC cycles at 2.70 GHz: divide by tsc_hz from the exit report's model line.",
        "Fixed costs per attention operation: joins plus barrier 9 to 13 us per layer at 1 user (320 to 480 us per token), join wait T5 3 to 6 us per job at 8 users under CPU attention [make-sense-amx-vs-avx.html 7.2.1, and the Table 1 source].",
    ])
    s += H3("8c", "Card 3: unit costs and visit counts")
    s += UL([
        "Unit (one visit, 32 KiB), AVX / canonical AMX / mirror AMX: 3.64 / 2.89 / 2.66 us at prompt 8192. 2.80 / 2.14 / 2.07 us at prompt 2048. 2.88 / 2.38 / 1.36 us at prompt 256. Hot in L2: 1.68 us (AVX) and 0.62 us (AMX) [Figure 4 sources].",
        "Visits per decode step on the CPU: U x L(CPU) x KV heads x ceil(context / 64). Kernel-eligible = the full pages: floor(context / 64) per (user, KV head, layer), plus the pending page in 1 of 64 steps.",
        "AoF steady state: 0 kernel visits, one AVX visit of (p mod 4) + 1 keys per (user, KV head, layer) per step, and the card scores 4 x floor(p / 4) keys per query. Exceptions that put pages on the CPU: a prompt under 128 tokens, a whole-page copy lag, a prefix-cache branch inside a shard, a full card store [counter.html 2.3, and attn-stats-compare-QA.html 1.3].",
        "Prefill: 128-token chunks per user per forward. The chunk's own pages are always AVX (one range per token), and earlier chunks' full pages are kernel-eligible. One 8-user prompt-1024 run has 7,168 ready kernel visits per (user, KV head, layer) [attention-stats-claude.html].",
        "Kill-switch identity: the same visits with the same key counts, every former AMX visit becomes one avx_full_page visit of 64 keys. Use it to check a counter reading before trusting a timing.",
    ])
    s += H3("8d", "Card 4: switches, commands, and where the counters appear")
    s += CODE("""TRON_ATTN_STATS=1              # exit report on stderr ([attn-stats] lines) + live FUSE leaves
TRON_AMX_DISABLE=1             # kill switch: same visits, all on the AVX loop; exit report says "amx_available":false
USE_HW_ATTN=0 | USE_HW_ATTN=1  # force CPU attention | force FPGA attention; unset = the model default
TRON_PER_USER_PROMPT_CHUNK_LIMIT=128   # prefill chunk per user per forward (default 128)

# runtron, 8 users in lockstep, 256 tokens each, our half of delphi-3bda (tp2 placement)
env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_ATTN_STATS=1 \\
  gen/runtron <model-name> --prompt-length 1024 -l 256 -u 8 --dont-stop \\
  --instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 \\
  --dev-cores 75,76 --numa 1 --nr_hugepages 128
# tp4: --instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores <28 more> --dev-cores 75,76,77,78 --nr_hugepages 256

# hardware proof that the kernel ran (0 under the kill switch): EXE.AMX_BUSY on the engine pid
sudo perf stat -e cpu/event=0xb7,umask=0x02/ -p <engine pid> -- sleep 20

# live leaves while a run is on: runtron mounts <worktree>/stats/instance-N/; rinzler mounts /var/run/rinzler/N/rinzler/stats/
#   .../attention/decode_like_forwards   T1 (wall_cycles / forwards), token_jobs_by_path_set, n_attn_workers
#   .../attention/decode_like_totals     T2 (busy_cycles / attn_jobs), T5 (join_wait_cycles), T4 (period_cycles_w0 / period_count_w0)
#   .../attention/decode_like_layer_<L>  the same per layer (the sliding-window vs card split of gpt-oss)
#   .../attention/prompt_or_mixed_*      the prefill class""")
    s += P("Reading the exit report: the model line gives n_layers, kv_mul, head_size, n_workers, active_workers and tsc_hz. The totals lines give the visit and key counts per path and the cycle sums of T2, T3, T4, T5. The forwards line gives the forward count, T1 and the path sets of the token jobs. The per-layer line gives K tokens per layer as amx/avx/fpga. A multi-leaf snapshot is not one consistent read: take ratios inside one leaf [attention-stats-claude.html, Traps].")
    s += H3("8e", "Card 5: measured anchors beyond Table 1")
    s += TABLE(["cell", "harness, layout", "result", "source"], [
        ("qwen3-4b tp2, 1 user, prompt 256 / 2048 / 8192, canonical kernel vs kill switch", "runtron, our half", "+0.2 / +3.9 / +10.8 % TPS; attention share 16 / 31 / 62 %", "make-sense-amx-vs-avx.html section 7 (fence3, 2026-09-01)"),
        ("qwen3-4b tp2, 1 user, prompt 256 to 32768, mirror kernel vs clean AVX build", "runtron, our half, 8 reps", "+0.6 / +1.9 / +1.7 / +5.0 / +14.9 / +18.0 / +26.0 / +27.6 % at 256 / 512 / 1024 / 2048 / 4096 / 8192 / 16384 / 32768", "make-sense-amx-vs-avx.html 2.1 (ctxfill, 2026-09-01)"),
        ("qwen3-4b tp2, 8 users, prompt 8192, decode TPS per user: AVX-CPU / AMX-CPU / AoF+AVX / AoF+AMX", "runtron, our half, 3 reps", "14.5 / 17.1 / 61.5 / 61.5; batched prefill of the 8 prompts 123.1 / 53.5 / 29.7 / 29.1 s", "CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html section 7 (2026-09-22)"),
        ("qwen3-4b tp2, cold prefill at prompt 8192: CPU AMX vs FPGA", "CI harness, whole machine", "12,743 ms vs 6,743 ms TTFT (1.9x for the card); CPU AMX vs CPU AVX 2.3x", "same page, section 5"),
        ("llama-3.1-8b tp2, 2 / 4 / 8 users per engine, prompt 1024, kill switch vs on", "rinzler + CI harness, our half", "+0.2 / +3.9 / +12.9 %; AMX busy 40 / 68 / 92 G cycles per 20 s", "VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html (2026-09-18)"),
        ("llama-3.1-8b tp2, 8 users per engine, prompt 4096, nightly package vs canonical package", "CI harness, nightly layout, whole machine, 3 passes", "28.24 -> 32.20 TPS = +14.0 %; TTFT 19.0 -> 11.5 s", "CI-test/status/llama-3.1-8b-8u-4k.html (2026-09-20)"),
        ("nightly rows, medians of 12 nights after 2026-09-23 vs 8 nights before", "nightly, Intel machine", "llama-3.1-8b 32 users +15.4 % (28.25 -> 32.61, the AMX row); llama-3.1-8b 8 users, qwen-2.5-32b, qwen-3-4b tp2: +1.2 to +1.6 % (no kernel); gpt-oss-120b tp4 +12.8 % and qwen-3-4b tp4 +18.3 % (AoF rows, not the kernel)", "Was-AMX-boosting-all-models.html sections 1, 2 and 8"),
        ("mixtral-8x7b tp2, 8 users, prompt 2048 / 8192, canonical kernel vs kill switch", "runtron", "+2.3 / +9.4 % decode; +56 % prefill at 8192", "tron-amx-distilled.html 4.1 (results/ci-models/mixtral-ab.txt, 2026-08-21)"),
    ], cls="", caption="Table 3. Anchors to check an estimate against. Each row names its harness and layout: never compare across harnesses.")
    s += H3("8f", "Card 6: where the detail lives")
    s += UL([
        "<b>tron-amx-distilled.html</b> (intel-AMX root): what AMX is, the decode architecture with the attention-worker lane figure, the shape table of every model, the kv_mul 3 / 5 / 8 explanation.",
        "<b>PR3879/make-sense-amx-vs-avx.html</b>: the boost-vs-prompt curves, the attention share, the per-unit measurement 7.2.1, the counters of the fence rounds.",
        "<b>perf-model/index.html</b>: the data-wait model of a unit (compute, memory time, overlap), the chain from a unit to the token, the benchmark outside tron.",
        "<b>PR3879/new-PRs/new-counters/counter.html</b>: which path serves a page visit in prefill and decode, the AoF exceptions, the counter design.",
        "<b>PR3879/new-PRs/new-counters/attention-stats-claude.html</b>: the five timers line by line, the closed-form visit counts, the check script attention-stats-claude-check.py.",
        "<b>PR3879/new-PRs/new-counters/attn-stats-compare.md</b> and <b>attn-stats-compare-QA.html</b>: the 2026-10-02 three-model comparison and the AoF questions (unit of 64, GOF of 4, equations).",
        "<b>rampup/gptoss-estimate.html</b>: what a gpt-oss kernel needs (new 64x8 kernels, two gate sites).",
        "<b>CI-test/status/llama-3.1-8b.html</b> and <b>qwen3-4b-prefill-amx-vs-fpga.html</b>: the CI-harness campaigns behind Figure 5 and the AoF-vs-CPU comparison.",
        "<b>Was-AMX-boosting-all-models.html</b> (new-counters): the nightly rows night by night, and why most September gains were not the kernel.",
    ])
    return s

def section_edges():
    s = H2(9, "9. Edges of the map: what it does not predict")
    s += OL([
        "<b>The CI harness at 8 users per engine, prompt 1024.</b> The map gives +3 % for llama-3.1-8b (lockstep decode, measured +2.9 %) while the CI harness measures +10.8 to +12.9 % in that cell. Hypothesis: in continuous batching a user's decode steps share forwards with other users' prefill chunks, and the kernel speeds those jobs 1.7x to 2.5x, so the per-user token interval drops more than the pure decode step. Measurement that decides it: the TRON_ATTN_STATS exit report of one rinzler engine under the CI harness, both arms, reading the T1 sums of the decode_like and prompt_or_mixed classes.",
        "<b>The card's own time under AoF.</b> The counters see it only as waits and join wait on the CPU side (Figure 2c). A card-side timer or a trace would split the matmuls from the attention passes.",
        "<b>qwen-2.5-32b's attention share.</b> No stats cell exists. One runtron cell with TRON_ATTN_STATS=1 (no kernel needed) closes it (example D).",
        "<b>The llama pass fraction at short prompts.</b> The one-third pass comes from one cell (8 users, prompt 1024). Cells at 2 and 4 users per engine, and at prompt 2048 and 4096, would show the shape of the rule.",
        "<b>Per-unit costs for shapes without a kernel.</b> kv_mul 5 (qwen-2.5-32b), kv_mul 8 (llama-70b) and 64x8 (gpt-oss) have no measured unit. The memory time (2.49 us per 32 KiB, or 1.25 us per 16 KiB page of a 64-wide head) is the only number the map can give.",
        "<b>The AMX clock license in serving.</b> Busy clocks fall from 3.74 to 3.60 GHz when the tiles are in use. The effect on the other work of the same cores is not separated in any run.",
    ])
    return s

def section_sources():
    return H2(10, "10. Sources") + UL([
        "exec/results/attnstats-20261002/{exit-reports.txt, rt-results.txt, leaves/&lt;run&gt;/decode_like_*}: the six 2026-10-02 cells (tron main dd0f942c75), and PR3879/new-PRs/new-counters/attn-stats-compare.md (sections 1, 2, 6, 7) built from them.",
        "exec/tron-intuition-20261007/leaves.py reads the per-layer leaves for Figure 2 (means over the layers of each class: gpt-oss even and odd layers, the other cells all layers).",
        "PR3879/make-sense-amx-vs-avx.html sections 2.1, 3, 7, 7.2.1 (unit costs, attention share, boost curves, 2026-08-31 to 2026-09-01).",
        "perf-model/index.html sections 2, 5, 6, 10 (compute, memory time, overlap, per-core rate, clocks; 2026-09-03).",
        "PR3879/new-PRs/new-counters/{counter.html, attention-stats-claude.html, attn-stats-compare-QA.html, Was-AMX-boosting-all-models.html}.",
        "CI-test/status/{llama-3.1-8b.html, llama-3.1-8b-8u-4k.html, qwen3-4b-prefill-amx-vs-fpga.html}, and VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html.",
        "tron sources (tron-amx checkout, 85fc8ff4de): h/tron/plugins/llama.hpp:183 and 1583-1594, gen-amd/src/tron/h/tron/plugins/{ingested_gpt_oss_120b.hpp, qwen_3_4b_instruct_2507.hpp}:28-52, h/tron/kernels/amx_attn_iface.hpp:148-150, h/tron/models/self_attention.hpp:1710-1721, h/libtron.hpp:194-205, h/tron/models/model.hpp:1937-1970 (the worker split).",
        "Notion Scratch page (2026-10-07): the gpt-oss time-budget answer that example C re-derives.",
    ])

def section_map():
    s = H2(1, "1. The map in one picture")
    s += P("Figure 1 is the containment chain. Every estimate reads it from right to left. A visit has a cost. A job is a worker's visits plus its waits. A layer is a job plus the card work around it. A forward is the layers, and TPS is one over the forward.")
    s += FIG(fig_map(), "Figure 1. What contains what in one engine, and the count that sets each level's size. The blue box is the unit the kernel changes.")
    return s

def section_tree():
    s = H2(4, "4. Which path serves a page visit")
    s += P("The path is a property of one visit, decided at the moment the worker reaches the page. Three questions decide it. The right-hand panel has the closed forms that the counters reproduce exactly.")
    s += FIG(fig_tree(), "Figure 3. The decision per page visit, and the visit counts per (user, KV head, layer) and step that follow from it.")
    return s

def section_units():
    s = H2(5, "5. What a unit costs, and why the kernel's gain is 1.3x and not 8x")
    s += P("A unit is the smallest thing the kernel changes. Its cost has two parts: the instructions, and the wait for its 32 KiB. Hot in the L2 cache the AMX path is 2.7x faster than the AVX path (0.62 vs 1.68 us). Under decode load the pages come from DRAM at 13.1 GB/s per core, so the 32 KiB need 2.49 us however fast the instructions run, and the two paths end 0.75 us apart (2.89 vs 3.64 us at prompt 8192).")
    s += FIG(fig_units(), "Figure 4. One unit on each code path at three prompt lengths (measured inside tron, worker 0 medians, 2026-09-01) and hot in L2 (unit benchmark, 2026-09-03). The dashed line is the memory time with 27 cores reading.")
    s += P("Two consequences for estimates. First, use the row that matches the context: 0.50 us saved per unit at prompt 256, 0.66 at 2048, 0.75 at 8192 (canonical kernel). Second, the AMX tile does useful work on 4 of its 16 rows in private decode (one query token per user, 4 query heads per KV head), so the 8x instruction-level figure never applies to decode. It applies to prefill, where many query tokens share a page [make-sense-amx-vs-avx.html section 4].")
    return s

def section_levers():
    s = H2(7, "7. The levers in CI: users per engine and prompt length")
    s += P("Figure 5 is the measured shape of rule 8 for llama-3.1-8b. Both levers work through the same quantity, the attention share of the forward. The nightly's llama-3.1-8b 8-user row sits at the bottom left of the left panel (2 users per engine, prompt 1024, +0.2 %). The 32-user row sits at the top (8 users per engine).")
    s += FIG(fig_levers(), "Figure 5. llama-3.1-8b decode gain of the canonical-AMX package over the nightly package in the CI harness. Left: against prompt length at 2 and 8 users per engine. Right: against users per engine at prompt 1024. Values are the mean over 3 interleaved passes. Every point except 2 users x 1024 is resolved (paired t above 4.3).")
    return s

CSS = """
:root { color-scheme: light; }
body { margin: 0; background: #f9f9f7; color: #0b0b0b; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 15px; line-height: 1.5; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 60px; }
h1 { font-size: 26px; margin: 0 0 6px; }
h2 { font-size: 20px; margin: 36px 0 10px; border-bottom: 1px solid #e1e0d9; padding-bottom: 4px; }
h3 { font-size: 16px; margin: 22px 0 8px; }
p { margin: 8px 0 10px; }
.sub { color: #52514e; font-size: 13.5px; margin-bottom: 14px; }
.short { background: #ffffff; border: 1px solid #e1e0d9; border-left: 4px solid #2a78d6; padding: 12px 16px; margin: 14px 0 18px; }
.note { background: #fff8ef; border: 1px solid #f1d9bb; padding: 10px 14px; margin: 10px 0; }
figure { margin: 14px 0 18px; background: #fcfcfb; border: 1px solid #e1e0d9; padding: 8px; overflow-x: auto; }
figcaption { color: #52514e; font-size: 13px; margin-top: 6px; }
table { border-collapse: collapse; margin: 10px 0 14px; font-size: 13px; background: #ffffff; }
caption { caption-side: top; text-align: left; color: #52514e; font-size: 12.5px; padding: 4px 0; }
th, td { border: 1px solid #e1e0d9; padding: 5px 8px; vertical-align: top; text-align: left; }
th { background: #f2f1ee; font-weight: 600; }
table.num td:nth-child(n+3) { font-variant-numeric: tabular-nums; }
pre { background: #f2f1ee; border: 1px solid #e1e0d9; padding: 10px 12px; overflow-x: auto; font-size: 12.5px; line-height: 1.45; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
dl { margin: 8px 0; }
dt { font-weight: 600; margin-top: 8px; }
dd { margin: 2px 0 0 18px; color: #1f1f1d; }
.rule { background: #ffffff; border: 1px solid #e1e0d9; padding: 8px 12px; margin: 8px 0; }
.rule-t { font-weight: 600; }
.rule-b { color: #1f1f1d; margin-top: 4px; font-size: 14px; }
ul, ol { margin: 6px 0 12px; }
li { margin: 4px 0; }
nav.toc { font-size: 13.5px; background: #ffffff; border: 1px solid #e1e0d9; padding: 8px 14px; margin: 12px 0 18px; }
nav.toc a { margin-right: 14px; color: #1c5cab; text-decoration: none; }
a { color: #1c5cab; }
"""

def build():
    toc = ['<a href="#s1">1 Map</a>', '<a href="#s2">2 Internalize</a>', '<a href="#s3">3 One layer, four ways</a>', '<a href="#s4">4 Path per visit</a>',
           '<a href="#s5">5 Unit cost</a>', '<a href="#s6">6 Recipe + examples</a>', '<a href="#s7">7 CI levers</a>', '<a href="#s8">8 Keep handy</a>',
           '<a href="#s9">9 Edges</a>', '<a href="#s10">10 Sources</a>']
    body = ""
    body += "<h1>A mental map of tron for timing estimates by hand</h1>\n"
    body += '<div class="sub">AMX / AVX / attention on the FPGA, for llama-3.1, qwen-2.5 and gpt-oss. Written by Claude for jhan, 2026-10-07, from the measurements of 2026-08-31 to 2026-10-04 on delphi-3bda. Every number is measured and cited unless marked est. Generator: exec/tron-intuition-20261007/gen_intuition.py.</div>\n'
    body += SHORT
    body += '<nav class="toc">' + "".join(toc) + "</nav>\n"
    body += '<h2 id="words">Words used here</h2>\n' + DL(WORDS)
    body += section_map()
    body += section_internalize()
    body += section_lanes()
    body += section_tree()
    body += section_units()
    body += section_recipe()
    body += section_levers()
    body += section_cards()
    body += section_edges()
    body += section_sources()
    page = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>tron mental map for timing estimates</title>\n<style>%s</style>\n</head>\n<body>\n<main>\n%s</main>\n</body>\n</html>\n' % (CSS, body))
    # ASCII guard: the page must be pure ASCII (artifact mojibake trap)
    bad = [c for c in page if ord(c) > 126]
    if bad:
        raise SystemExit("non-ASCII characters in the page: %r" % sorted(set(bad))[:20])
    with open(OUT, "w") as f:
        f.write(page)
    print("wrote", OUT, len(page), "bytes")

if __name__ == "__main__":
    build()
