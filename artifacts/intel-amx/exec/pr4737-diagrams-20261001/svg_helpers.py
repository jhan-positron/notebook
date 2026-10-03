"""SVG primitives and the one colour scheme of the PR 4737 kv_cache.hpp page.

Every diagram of the page uses these tokens, so the same concept has the
same colour everywhere (the user's requirement). Palette: Okabe-Ito
(colour-blind safe). Fills are light tints of the stroke colours so that
black text stays readable on them.
"""
import html

# ---- concept colours -------------------------------------------------------
C = {
    # a K row / block held row-major (contiguous 256-byte token rows)
    "rm": "#E69F00", "rm_fill": "#FBE9C4",
    # a converted block: the VNNI layout (AMX B-operand layout)
    "vnni": "#0072B2", "vnni_fill": "#CFE2F3",
    # a complete block that waits for its conversion (16 row bits, block bit
    # clear); also the pending list and the conversion event
    "pend": "#D55E00", "pend_fill": "#FBE9C4",
    # k_rows_saved_ bits (one per page offset)
    "rows": "#009E73", "rows_fill": "#BFE8DA",
    # k_vnni_blocks_ bits (one per 16-token block)
    "blk": "#CC79A7", "blk_fill": "#F0D4E3",
    # hardware (FPGA) attention, the operation flag cached_operation_uses_hw
    "hw": "#B8A200", "hw_fill": "#F7F0B0",
    # EAGLE storage (the extra physical slot) and its view
    "eagle": "#56B4E9", "eagle_fill": "#D9EEF9",
    # empty: no row saved (bytes undefined)
    "empty": "#9CA3AF", "empty_fill": "#FFFFFF",
    # neutral structure
    "ink": "#1F2937", "muted": "#6B7280", "line": "#C9CDD3", "soft": "#F3F5F8",
    # new code (this PR) marker in function maps
    "new": "#009E73",
    # removed code / dropped state
    "gone": "#B91C1C",
}

MONO = "ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, 'DejaVu Sans', sans-serif"


def esc(s):
    return html.escape(str(s), quote=False)


def rect(x, y, w, h, fill="#fff", stroke=C["ink"], sw=1.2, rx=4, dash=None,
         extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{extra}/>')


def text(x, y, s, size=12, anchor="start", mono=False, fill=None, weight=None,
         italic=False, extra=""):
    fam = MONO if mono else SANS
    st = f"font-family:{fam};font-size:{size}px"
    if fill:
        st += f";fill:{fill}"
    if weight:
        st += f";font-weight:{weight}"
    if italic:
        st += ";font-style:italic"
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{st}"{extra}>'
            f'{esc(s)}</text>')


def lines(x, y, items, size=12, lh=15, anchor="start", mono=False, fill=None,
          weight=None):
    """Several text lines starting at (x, y), one per item."""
    out = []
    for i, s in enumerate(items):
        out.append(text(x, y + i * lh, s, size, anchor, mono, fill, weight))
    return "".join(out)


def marker_defs(fig_id, colors):
    """One arrowhead marker per colour, ids unique per figure (cairosvg trap)."""
    out = ["<defs>"]
    for name, col in colors.items():
        out.append(
            f'<marker id="{fig_id}-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    out.append("</defs>")
    return "".join(out)


def arrow(fig_id, name, pts, color, sw=1.4, dash=None):
    """Polyline arrow through pts [(x,y),...] with the figure's marker `name`."""
    d = " ".join(f"{x},{y}" for x, y in pts)
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}"{dd} marker-end="url(#{fig_id}-{name})"/>')


def line(x1, y1, x2, y2, color=C["line"], sw=1, dash=None):
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}"{dd}/>')


def label_box(x, y, w, h, title, sub=(), fill="#fff", stroke=C["ink"],
              size=12, mono_title=True, rx=5, dash=None, sw=1.2):
    """Box with a title line and optional smaller lines under it."""
    out = [rect(x, y, w, h, fill, stroke, sw, rx, dash)]
    ty = y + 16
    out.append(text(x + w / 2, ty, title, size, "middle", mono_title,
                    weight=600))
    for s in sub:
        ty += 14
        out.append(text(x + w / 2, ty, s, size - 1, "middle", False,
                        fill=C["muted"]))
    return "".join(out)


def bit_row(x, y, bits, cell=9, gap=1, on_fill=None, on_stroke=None,
            off_fill=C["empty_fill"], off_stroke=C["empty"], group=16,
            group_gap=6):
    """A row of small squares, one per bit; bits is a str of '0'/'1'."""
    out = []
    cx = x
    for i, b in enumerate(bits):
        if i > 0 and group and i % group == 0:
            cx += group_gap
        f = on_fill if b == "1" else off_fill
        s = on_stroke if b == "1" else off_stroke
        out.append(rect(cx, y, cell, cell, f, s, 0.8, 1))
        cx += cell + gap
    return "".join(out), cx


def svg_open(fig_id, w, h, aria):
    return (f'<svg id="{fig_id}" viewBox="0 0 {w} {h}" width="100%" '
            f'role="img" aria-label="{esc(aria)}" '
            f'xmlns="http://www.w3.org/2000/svg">')


def figure(fig_id, w, h, aria, body, caption, max_width=None):
    mw = f' style="max-width:{max_width}px"' if max_width else ""
    return (f'<figure{mw}>{svg_open(fig_id, w, h, aria)}{body}</svg>'
            f'<figcaption>{caption}</figcaption></figure>')


def block_cell(x, y, w, h, state, label=None, size=11):
    """One 16-token block drawn by its layout state.

    state: 'empty' | 'rm' (row-major rows, some saved) | 'pend' (complete,
    not converted) | 'vnni' (converted) | 'hw' (row-major, no bits, hardware
    attention)
    """
    if state == "empty":
        r = rect(x, y, w, h, C["empty_fill"], C["empty"], 1, 3, "3 2")
    elif state == "rm":
        r = rect(x, y, w, h, C["rm_fill"], C["rm"], 1.4, 3)
    elif state == "pend":
        r = rect(x, y, w, h, C["pend_fill"], C["pend"], 2, 3, "5 3")
    elif state == "vnni":
        r = rect(x, y, w, h, C["vnni_fill"], C["vnni"], 1.4, 3)
    elif state == "hw":
        r = rect(x, y, w, h, C["hw_fill"], C["hw"], 1.4, 3)
    else:
        raise ValueError(state)
    out = [r]
    if label:
        out.append(text(x + w / 2, y + h / 2 + 4, label, size, "middle",
                        mono=True))
    return "".join(out)


def legend_chip(x, y, state, label, w=26, h=14):
    return block_cell(x, y, w, h, state) + text(x + w + 6, y + 11, label, 11)
