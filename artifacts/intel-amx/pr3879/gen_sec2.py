#!/usr/bin/env python3
"""Generate the section-2 SVG (baseline vs mirror lanes) with matrix shapes in every box.
Text is written with unicode symbols here and converted to numeric entities on output,
so the HTML stays pure ASCII."""
import sys

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
BASE, BASE_T = "#2a78d6", "#e4eefb"
MIR, MIR_T = "#eb6834", "#fbe7de"
HAIR, AXIS, SURF, BAND, SHARED = "#e1e0d9", "#c3c2b7", "#fcfcfb", "#f4f4f1", "#f1f0ec"
ARROW = "#52514e"

out = []
def E(s):
    # numeric entities for every non-ASCII char, plus XML escapes
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in s)
def text(x, y, s, size=None, fill=INK, anchor="middle", weight=None, extra=""):
    a = ['<text x="%g" y="%g"' % (x, y)]
    if anchor != "start": a.append('text-anchor="%s"' % anchor)
    if size: a.append('font-size="%s"' % size)
    a.append('fill="%s"' % fill)
    if weight: a.append('font-weight="%s"' % weight)
    if extra: a.append(extra)
    out.append("  " + " ".join(a) + ">" + E(s) + "</text>")

TITLE_DY, LH, PAD_BOTTOM = 18, 14, 10
def box_h(lines):
    return TITLE_DY + LH * (len(lines) - 1) + PAD_BOTTOM
def lane_box(x, y, w, lines, fill, stroke, dash=False, sw=1, title_weight=None, h=None):
    """lines: list of (kind, text); kind in title/desc/dim/cite. Returns box height."""
    h = h or box_h(lines)
    dashattr = ' stroke-dasharray="6 4"' if dash else ""
    out.append('  <rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="%s" stroke="%s" stroke-width="%g"%s/>'
               % (x, y, w, h, fill, stroke, sw, dashattr))
    cx = x + w / 2
    yy = y + TITLE_DY
    for kind, s in lines:
        if kind == "title":
            text(cx, yy, s, fill=INK, weight=title_weight)
        elif kind == "desc":
            text(cx, yy, s, size=12, fill=INK2)
        elif kind == "dim":
            text(cx, yy, s, size=12, fill=INK)
        elif kind == "cite":
            text(cx, yy, s, size=11, fill=MUTED)
        yy += LH
    return h

def shared_box(x, y, w, left, right, dims, cite, center=None, fill=SHARED, stroke=AXIS):
    h = 21 + 15 * len(dims) + 10
    out.append('  <rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="%s" stroke="%s"/>' % (x, y, w, h, fill, stroke))
    text(x + 16, y + 21, left, anchor="start")
    if center: text(x + w / 2, y + 21, center)
    if right: text(x + w - 16, y + 21, right, anchor="end")
    text(x + w + 6, y + 21, cite, size=11, fill=MUTED, anchor="start")
    yy = y + 21
    for d in dims:
        yy += 15
        text(x + 16, yy, d, size=12, fill=INK, anchor="start")
    return h

def arrow(x, y1, y2, color=ARROW, marker="arr"):
    out.append('  <line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.5" marker-end="url(#%s)"/>' % (x, y1, x, y2, color, marker))

# ---------------- geometry ----------------
LW = 440                      # lane box width
LX, RX = 30, 530              # lane box x
LC, RC = LX + LW / 2, RX + LW / 2
SW = 700; SX = 150            # shared box width / x

# --------------- content ---------------
store_left = [("title", "store K row into the page (row-major, 128 bf16)"),
              ("dim", "K row: 1 × 128 bf16 (256 B) → tok j of K_page: 64 tok × 128 dim (16 KB)"),
              ("cite", "model.hpp:2791")]
store_right = [("title", "store K row into the page (row-major, 128 bf16)"),
               ("dim", "K row: 1 × 128 bf16 (256 B) → tok j of K_page: 64 tok × 128 dim (16 KB)"),
               ("cite", "model.hpp:2791 · canonical K is kept")]
scatter = [("title", "+ scatter the same row into the K* plane (VNNI), L1-hot"),
           ("dim", "K row j: 1 × 128 bf16 → 64 dim pairs (4 B each), 64 scattered writes"),
           ("dim", "into the 4 panels of token block j/16: row = dim pair, col = j mod 16"),
           ("dim", "K*: 64 tok × 128 dim (16 KB) = 16 panels, 4 dim steps × 4 tok blocks"),
           ("cite", "set_k_mirror → scatter_k_mirror · model.hpp:2798 · kv_cache.hpp:652")]

pack_left = [("title", "pack Q (4 heads × 128) into the VNNI B layout"),
             ("dim", "Q group (this KV head's 4 heads): 4 head × 128 dim bf16 = 1 KB"),
             ("dim", "Q_packed: 4 panels (one per 32-dim step), 1 KB each = 4 KB"),
             ("dim", "panel = one B tile: 16 dim-pair rows × 16 col × 2 bf16"),
             ("dim", "col 0-3 = the 4 heads, col 4-15 zero (1 KB real data of 4 KB)"),
             ("cite", "pack_q_group_128x4 · once per token × KV head × section")]
tiles_left = [("title", "tiles:  S^T = K_page · Q_packed"),
              ("desc", "K rows are operand A, as stored · result rows = tokens"),
              ("dim", "K_page: 64 tok × 128 dim bf16 (16 KB) → 16 A tiles of 16 tok × 32 dim"),
              ("dim", "Q_packed: 4 B tiles of 16 dim-pair rows × 16 col × 2 (col 0-3 real)"),
              ("dim", "S^T: 64 tok × 16 col fp32 (4 KB) = 4 C tiles of 16 × 16; col 0-3 real"),
              ("dim", "16 tile multiplies (4 dim steps × 4 tok blocks); 20 loads, 4 stores"),
              ("cite", "amx_attn.cpp:127-146")]
transpose = [("title", "S = (S^T)^T :  tiles → stack buffer → AVX-512 transpose"),
             ("desc", "removed by the mirror · 0.37 us of QK per unit (prompt 8192)"),
             ("dim", "s_transposed: 64 tok × 16 col fp32 (4 KB), col 0-3 real"),
             ("dim", "→ s_pages: 4 head × 64 tok fp32 (1 KB), row stride 64 floats"),
             ("dim", "per C tile: 16 loads of 16 fp32 → 4 stores of 16 fp32; 4 tiles"),
             ("cite", "amx_attn.cpp:143-180")]

pack_right = [("title", "pack Q as 16 zero-padded rows (1 KB memcpy)"),
              ("dim", "Q group (this KV head's 4 heads): 4 head × 128 dim bf16 = 1 KB"),
              ("dim", "Q_rows: 16 row × 128 dim bf16 = 4 KB (1 KB real data)"),
              ("dim", "rows 0-3 = the 4 heads, rows 4-15 zero (kept zero by the caller)"),
              ("dim", "A tile = 16 row × 32 dim, one per 32-dim step (4 in all)"),
              ("cite", "pack_q_rows_128x4 · once per token × KV head × section")]
tiles_right = [("title", "tiles:  S = Q_rows · K*"),
               ("desc", "K* is operand B, read from the plane · result rows = query heads"),
               ("dim", "K*: 64 tok × 128 dim bf16 (16 KB) = 16 B tiles (panels), 1 KB each"),
               ("dim", "panel = 16 dim-pair rows × 16 tok × 2 · Q_rows A tile = 16 × 32 dim"),
               ("dim", "S: 16 row × 64 tok fp32 (4 KB) = 4 C tiles of 16 × 16; rows 0-3 real"),
               ("dim", "16 tile multiplies (4 dim steps × 4 tok blocks); 20 loads, 4 stores"),
               ("cite", "amx_attn.cpp:249-267")]
stored = [("title", "stored straight into s; the 4 real rows are copied out"),
          ("desc", "no transpose · no K* plane → AVX fallback for that page"),
          ("dim", "qk_s: 16 row × 64 tok fp32 = 4 KB (rows 4-15 zero)"),
          ("dim", "memcpy rows 0-3 → s_pages: 4 head × 64 tok fp32 = 1 KB"),
          ("cite", "self_attention.hpp:1579-1589")]

# --------------- layout ---------------
y = 40
band_top = y
out.append('  <rect x="20" y="%g" width="960" height="__BAND_H__" fill="%s" stroke="none"/>' % (band_top, BAND))
text(30, band_top + 18, "WHEN K IS GENERATED  ·  save_k, once per token × layer × KV head, on the worker that computed K",
     size=11.5, fill=MUTED, anchor="start", extra='letter-spacing="1"')
y = band_top + 32
h_sl = lane_box(LX, y, LW, store_left, SURF, AXIS)
h_sr = lane_box(RX, y, LW, store_right, SURF, AXIS)
y2 = y + h_sr
arrow(RC, y2, y2 + 10, MIR, "arrMd")
h_sc = lane_box(RX, y2 + 10, LW, scatter, MIR_T, MIR)
band_bottom = y2 + 10 + h_sc + 10
band_h = band_bottom - band_top
out[-0:] = out  # no-op
# patch the band height
for i, s in enumerate(out):
    if "__BAND_H__" in s:
        out[i] = s.replace("__BAND_H__", "%g" % band_h)

y = band_bottom + 24
text(30, y, "AT ATTENTION TIME  ·  per (query token, KV page, KV head), every decode step",
     size=11.5, fill=MUTED, anchor="start", extra='letter-spacing="1"')
y += 12
hL = lane_box(LX, y, LW, pack_left, BASE_T, BASE)
hR = lane_box(RX, y, LW, pack_right, MIR_T, MIR)
assert hL == hR, (hL, hR)
y += hL
arrow(LC, y, y + 14); arrow(RC, y, y + 14)
y += 14
hL = lane_box(LX, y, LW, tiles_left, BASE_T, BASE, title_weight=500)
hR = lane_box(RX, y, LW, tiles_right, MIR_T, MIR, title_weight=500)
assert hL == hR, (hL, hR)
y += hL
arrow(LC, y, y + 14); arrow(RC, y, y + 14)
y += 14
hh = max(box_h(transpose), box_h(stored))
hL = lane_box(LX, y, LW, transpose, SURF, BASE, dash=True, sw=1.5, title_weight=500, h=hh)
hR = lane_box(RX, y, LW, stored, SURF, AXIS, h=hh)
y += hL
lanes_end = y
# join
out.append('  <path d="M%g %g L%g %g L%g %g L%g %g" fill="none" stroke="%s" stroke-width="1.5"/>'
           % (LC, y, LC, y + 18, RC, y + 18, RC, y, ARROW))
arrow(500, y + 18, y + 36)
text(512, y + 32, "same s_pages[4][64] array of unscaled scores  ·  identical code from here on", size=11.5, fill=MUTED, anchor="start")
y += 38

h = shared_box(SX, y, SW, "s = S · scale   (or tanh softcap)", "m = max(s), then max with m*",
               ["s_pages: 4 head × 64 tok fp32 (1 KB) → same shape  ·  m: 4 values, one per head"], ":1645-1652")
y += h; arrow(500, y, y + 12); y += 12
h = shared_box(SX, y, SW, "P = exp(s − m), fp32, not divided by anything", "ΣP kept · c = exp(m*_old − m)",
               ["P: 4 head × 64 tok fp32, written in place over s_pages  ·  ΣP and c: 4 values each"], ":1653-1656")
y += h; arrow(500, y, y + 12); y += 12
h = shared_box(SX, y, SW, "tiles:  O = bf16(P) · V_page", "V read as stored (pair-interleaved), no V mirror",
               ["P → bf16 (round to nearest even): 16 row × 64 tok bf16 = 2 KB, rows 4-15 zero",
                "V_page: 64 tok × 128 dim bf16 (16 KB) = 32 token-pair rows × 256 bf16, read as stored",
                "A tile = 16 row × 32 tok; B tile = 16 token-pair rows × 16 dim × 2; 16 tile multiplies",
                "O: 16 row × 128 dim fp32 (8 KB) = 8 C tiles of 16 × 16; rows 0-3 real"], ":1661-1664")
y += h; arrow(500, y, y + 12); y += 12
h = shared_box(SX, y, SW, "v* = v*·c + O", "m* = m   → next page",
               ["v*: 4 head × 128 dim, bf16 in memory; v*·c + O is computed in fp32 and truncated to bf16 on store",
                "s*, m*: 4 fp32 values each  ·  O rows 0-3 used: 4 × 128 fp32"], ":1670-1678",
               center="s* = s*·c + ΣP")
y += h; arrow(500, y, y + 12); y += 12
h = shared_box(SX, y, SW, "after all pages + the cross-worker join:", "out = v* / s*   (the only normalization)",
               ["out: 4 head × 128 dim bf16 = this KV head's 512 values of the token's attention output row"], ":296-305, :1719",
               fill=SURF)
y += h
H = y + 16

aria = ("Two lanes, baseline and mirror. At K generation, both store the K row; mirror additionally scatters it into the K star plane. "
        "At attention time, baseline packs Q into VNNI, multiplies K page by Q to get S transposed, then transposes with AVX-512. "
        "Mirror packs Q as padded rows, multiplies Q by K star to get S directly. Both then run the same shared tail: scale, page max, exp, "
        "P times V, running state update, and one final division after the join. Every box lists the shapes of the matrices it touches.")
head = ['<svg viewBox="0 0 1000 %g" role="img" aria-label="%s" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, system-ui, sans-serif" font-size="13">' % (H, aria),
        '  <defs>',
        '    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="%s"/></marker>' % ARROW,
        '    <marker id="arrMd" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="%s"/></marker>' % MIR,
        '  </defs>',
        '  <text x="%g" y="24" text-anchor="middle" font-size="16" font-weight="600" fill="%s">Baseline AMX  (canonical-K, qk_canonical_128x4)</text>' % (LC, BASE),
        '  <text x="%g" y="24" text-anchor="middle" font-size="16" font-weight="600" fill="%s">Mirror AMX  (K*, qk_mirror_128x4)</text>' % (RC, MIR),
        '  <line x1="500" y1="36" x2="500" y2="%g" stroke="%s" stroke-dasharray="3 5"/>' % (lanes_end, HAIR),
        ]
svg = "\n".join(head + out + ["</svg>"])
assert all(ord(c) < 128 for c in svg), "non-ASCII leaked"
sys.stdout.write(svg + "\n")
