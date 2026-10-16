"""SVG primitives and the ONE colour scheme of the PR 4424 diagram pages.

Every diagram of the three pages (k_vnni.hpp, kv_cache.hpp, model.hpp) uses
these tokens, so the same concept has the same colour and font everywhere.
Palette: Okabe-Ito (colour-blind safe). Fills are light tints of the stroke
colours so that black text stays readable on them.

Rules every diagram follows (the user's requirements):
  * no invented shorthand: box labels are identifiers or comment phrases from
    the code; every box cites the line or Note that defines it (cite()).
  * every function cell carries a one-line description (fn_cell()).
  * every arrow between data-model boxes is labelled with how many
    (card_arrow(): "1 page -> n_slots + 1 entries").
  * threads are lanes or bracketed names, never colours: colours are reserved
    for data concepts.
"""
import html

# ---- concept colours -------------------------------------------------------
C = {
    # a K row / block held row-major (contiguous 256-byte token rows)
    "rm": "#E69F00", "rm_fill": "#FBE9C4",
    # the VNNI layout (AMX B-operand layout): a converted block, the packed
    # plane, k_vnni_tensor / k_vnni_view
    "vnni": "#0072B2", "vnni_fill": "#CFE2F3",
    # a complete block that is not converted yet (16 row bits, block bit
    # clear; dashed outline); also the deferred conversion list
    # (pending_k_blocks_) and, drawn solid, the conversion of such a block
    "pend": "#D55E00", "pend_fill": "#FBE9C4",
    # k_rows_saved_ bits (one per page offset); saved-row events
    "rows": "#009E73", "rows_fill": "#BFE8DA",
    # k_vnni_blocks_ bits (one per 16-token block)
    "blk": "#CC79A7", "blk_fill": "#F0D4E3",
    # hardware (FPGA) attention, the operation flag cached_operation_uses_hw
    "hw": "#B8A200", "hw_fill": "#F7F0B0",
    # EAGLE storage (the extra physical slot) and its state entry
    "eagle": "#56B4E9", "eagle_fill": "#D9EEF9",
    # the query side: Q rows, packed Q, scores s_pages (model.hpp / self_attention)
    "q": "#7B61FF", "q_fill": "#E4DEFF",
    # a work unit of the shared block save (batch::k_store_window_t.unit_start):
    # grey-blue, the one hue no data concept above uses
    "unit": "#4C6A8F", "unit_fill": "#E4EAF2",
    # the worked example's cell (page 7, slot 5) in data-model grids
    "hi_fill": "#FFF4D6",
    # the critical path of a wall-clock-lanes figure: thick SOLID red frame
    # (removed code is the same red, DASHED)
    "crit": "#B91C1C",
    # empty: no row saved (bytes undefined)
    "empty": "#9CA3AF", "empty_fill": "#FFFFFF",
    # neutral structure
    "ink": "#1F2937", "muted": "#6B7280", "line": "#C9CDD3", "soft": "#F3F5F8",
    # the "new" / "changed" marker (a word in bold ink, not a data concept);
    # removed code / dropped state
    "new": "#1F2937", "gone": "#B91C1C",
    # citation text (file:line) inside boxes
    "cite": "#8A8F98",
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


def text_width(s, size=12, mono=False):
    """Rough advance width in px (DejaVu metrics), for layout checks."""
    per = 0.60 if mono else 0.55
    return len(s) * size * per


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


def cite(x, y, ref, anchor="end", size=8.5):
    """A source citation (file:line or Note name) in small grey text.
    Place it in a box corner: cite(x + w - 4, y + h - 4, 'kv_cache.hpp:2391')."""
    return text(x, y, ref, size, anchor, mono=True, fill=C["cite"])


def label_box(x, y, w, h, title, sub=(), fill="#fff", stroke=C["ink"],
              size=12, mono_title=True, rx=5, dash=None, sw=1.2, ref=None):
    """Box with a title line, optional smaller lines under it, and an optional
    citation `ref` in the lower-right corner."""
    out = [rect(x, y, w, h, fill, stroke, sw, rx, dash)]
    ty = y + 16
    out.append(text(x + w / 2, ty, title, size, "middle", mono_title,
                    weight=600))
    for s in sub:
        ty += 14
        out.append(text(x + w / 2, ty, s, size - 1, "middle", False,
                        fill=C["muted"]))
    if ref:
        out.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(out)


def fn_cell(x, y, w, h, name, desc, ref, tag=None, fill="#fff",
            stroke=C["ink"], size=11.5):
    """A function cell: name (mono, bold), ONE-line description (what the
    function does), citation of its definition, optional tag ('new',
    'changed', 'unchanged'). desc may be a list of up to 2 short lines."""
    out = [rect(x, y, w, h, fill, stroke, 1.2, 4)]
    out.append(text(x + 8, y + 16, name, size, mono=True, weight=600))
    ds = desc if isinstance(desc, (list, tuple)) else [desc]
    out.append(lines(x + 8, y + 31, ds, size - 2, 12))
    if tag:
        col = C["new"] if tag.startswith("new") else (
            C["gone"] if tag.startswith("removed") else C["muted"])
        out.append(text(x + 8, y + h - 5, tag, 9, fill=col,
                        weight=700 if tag.startswith("new") else None))
    out.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(out)


def card_arrow(fig_id, name, pts, color, label, label_dx=0, label_dy=-5,
               sw=1.4, dash=None, size=9.5, anchor="middle"):
    """An arrow whose label says HOW MANY ('1 page -> n_slots + 1 entries').
    The label sits at the midpoint of the first segment, offset by
    (label_dx, label_dy); pass an offset so that it never lies on the line."""
    (x1, y1), (x2, y2) = pts[0], pts[1]
    mx, my = (x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy
    return arrow(fig_id, name, pts, color, sw, dash) + \
        text(mx, my, label, size, anchor, fill=color, weight=600)


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


# ---- the per-figure "Colour and font scheme" --------------------------------
# Every figure declares the styles it uses: figure(..., legend=[...]). The page
# prints them under the SVG, so a reader never needs the global scheme. Items:
#   "key"                  an entry of the LEGEND catalogue below
#   ("key", "label")       a catalogue entry with a label specific to the figure
#                          (say WHAT the style marks in this figure)
#   ("label", fill, stroke, dashed, thick)   a figure-specific box style
#   ("label", fill, stroke, dashed, thick, opacity)   the same, for a tinted band:
#                          the chip shows the fill at that opacity; the
#                          data-style stays the fill's (what the SVG rect says)
#   ("label", "arrow", stroke)               a figure-specific arrow colour
#   ("label", "text", colour)                coloured text with no box or arrow
#                                            of that colour in the figure
#   ("label", "line", colour[, True])        a thin line without an arrowhead
#                                            (True = dashed); optional in the check
#   ("label", "multi", [part, ...])          ONE entry for the several styles of one
#                                            concept (a box and its arrow): a part is
#                                            a catalogue key, ("arrow", colour),
#                                            ("text", colour), ("line", colour[, True])
#                                            or (fill, stroke, dashed, thick)
# check_legend.py compares the declaration with the styles the SVG uses.
_W = "#fff"
LEGEND = {
    # concept boxes (fill, stroke, dashed, thick)
    "vnni": (C["vnni_fill"], C["vnni"], False, False,
             "VNNI layout: a converted block, the packed plane, k_vnni_tensor / k_vnni_view"),
    "vnni_solid": (C["vnni"], C["vnni"], False, False,
                   "solid blue: a VNNI pair row or a token's column, as bytes"),
    "pend": (C["pend_fill"], C["pend"], True, False,
             "complete, may wait: 16 row bits set, block bit clear; the deferred conversion list pending_k_blocks_"),
    "pend_solid": (C["pend_fill"], C["pend"], False, False,
                   "the conversion of a complete block (block_to_vnni, k_block_to_vnni_at, convert_pending_k_blocks)"),
    "rm": (C["rm_fill"], C["rm"], False, False,
           "row-major rows: a row-major slot, or the row-major form of a block"),
    "rm_solid": (C["rm"], C["rm"], False, False, "solid orange: a row-major token row, as bytes"),
    "empty": (_W, C["empty"], True, False, "no row bit / no row saved (bytes undefined): grey dashed"),
    "bit_clear": (_W, C["empty"], False, False, "a bit that is clear (white square)"),
    "hw": (C["hw_fill"], C["hw"], False, False,
           "hardware attention: a hardware-scored operation (row-major, no bits) or the FPGA staging path"),
    "rows": (C["rows_fill"], C["rows"], False, False,
             "k_rows_saved_: a saved-row bit that is set (one square per page offset)"),
    "blk": (C["blk_fill"], C["blk"], False, False,
            "k_vnni_blocks_: a converted-block bit that is set (one square per 16-token block)"),
    "eagle": (C["eagle_fill"], C["eagle"], False, False, "EAGLE storage: the extra physical slot and its state entry n_slots"),
    "q": (C["q_fill"], C["q"], False, False, "the query side: Q rows, packed Q, the scores s_pages, attention jobs"),
    "unit": (C["unit_fill"], C["unit"], False, False,
             "a work unit of the shared block save (unit_start), or the claim counter next_unit"),
    "hi": (C["hi_fill"], C["ink"], False, False, "the worked example's cell (page 7, slot 5)"),
    "gone": (_W, C["gone"], True, False, "before / removed: base code or an old state (red dashed)"),
    "crit": ("none", C["crit"], False, True, "the critical path, main's serial part (thick solid red frame)"),
    "deleted": (_W, C["muted"], True, False, "a function or route the code does not provide (deleted / does not exist)"),
    "idle": (_W, C["ink"], True, False, "waiting or idle (dashed outline), even a spin-wait"),
    "box": (_W, C["ink"], False, False,
            "a box with a name from the code: the name in bold monospace, its description in sans-serif under it"),
    "ctx": (C["soft"], C["line"], False, False, "context: a caller in another file, or a note (grey fill, thin grey outline)"),
    "ctx_ink": (C["soft"], C["ink"], False, False, "a work block or a grouped band (grey fill, ink outline)"),
    "lane": (_W, C["line"], False, False, "a lane, a frame or a grid (thin grey outline)"),
    "thick_ink": ("none", C["ink"], False, True, "thick ink outline: the highlighted instance of the worked example"),
    # arrows (stroke)
    "arrow": ("arrow", C["ink"], "an arrow = a call, a containment or a step; its label says how many"),
    "arrow_muted": ("arrow", C["muted"], "a grey arrow = a reference or a route that is only context"),
    # fonts
    "font_mono": ("font", "mono", "monospace = an identifier or a value from the code"),
    "font_sans": ("font", "sans", "sans-serif = prose: descriptions, labels, captions"),
    "font_cite": ("font", "cite", "small grey monospace = the line or Note that defines the box (file:line)"),
    "font_tag": ("font", "tag", "bold 'new' = added by this PR; 'changed' = changed by it; red 'removed' = removed"),
    # the same tag font, shown with the grey 'changed' word (a figure that tags nothing 'new')
    "font_tag_changed": ("font", "tag_changed",
                         "grey 'changed' = changed by this PR; red 'removed' = removed"),
}


def _norm(c):
    c = (c or "").strip().lower()
    return "#fff" if c in ("#ffffff", "white") else c


def style_key(fill, stroke, dashed, thick):
    return f"box:{_norm(fill)}:{_norm(stroke)}:{'d' if dashed else 's'}:{'t' if thick else 'n'}"


def _part(p):
    """A part of a ("label", "multi", [...]) entry as a legend item with no label."""
    if isinstance(p, str):
        return p
    if len(p) == 2 and p[0] in ("arrow", "text"):
        return ("", p[0], p[1])
    if len(p) in (2, 3) and p[0] == "line":
        return ("", "line", p[1], len(p) == 3 and bool(p[2]))
    if len(p) == 4:
        return ("", p[0], p[1], p[2], p[3])
    raise ValueError(f"bad legend part {p!r}")


def legend_entries(items):
    """Expand figure(legend=...) items into (label, data_style, chip_html)."""
    out = []
    for it in items or ():
        label_override = None
        opacity = None
        if isinstance(it, str):
            key, spec = it, LEGEND[it]
        elif isinstance(it, (list, tuple)) and len(it) == 2 and it[0] in LEGEND:
            key, spec = it[0], LEGEND[it[0]]
            label_override = it[1]
        elif isinstance(it, (list, tuple)) and len(it) == 3 and it[1] == "arrow":
            key, spec = None, ("arrow", it[2], it[0])
        elif isinstance(it, (list, tuple)) and len(it) == 3 and it[1] == "text":
            key, spec = None, ("text", it[2], it[0])
        elif isinstance(it, (list, tuple)) and len(it) in (3, 4) and it[1] == "line":
            key, spec = None, ("line", it[2], len(it) == 4 and bool(it[3]), it[0])
        elif isinstance(it, (list, tuple)) and len(it) == 3 and it[1] == "multi":
            parts = legend_entries([_part(p) for p in it[2]])
            out.append((it[0], " ".join(ds for _, ds, _ in parts),
                        "".join(chip for _, _, chip in parts)))
            continue
        elif isinstance(it, (list, tuple)) and len(it) == 5:
            key, spec = None, (it[1], it[2], bool(it[3]), bool(it[4]), it[0])
        elif isinstance(it, (list, tuple)) and len(it) == 6:
            key, spec = None, (it[1], it[2], bool(it[3]), bool(it[4]), it[0])
            opacity = float(it[5])
        else:
            raise ValueError(f"bad legend item {it!r}")
        if spec[0] == "line":
            _, stroke, dashed, label = spec
            ds = f"line:{_norm(stroke)}:{'d' if dashed else 's'}"
            dd = ' stroke-dasharray="4 3"' if dashed else ""
            chip = (f'<span class="lchip"><svg width="34" height="12" viewBox="0 0 34 12">'
                    f'<line x1="1" y1="6" x2="33" y2="6" stroke="{stroke}" stroke-width="1.4"{dd}/>'
                    f'</svg></span>')
        elif spec[0] == "arrow":
            _, stroke, label = spec
            label = label_override or label
            ds = f"arrow:{_norm(stroke)}"
            chip = (f'<span class="lchip"><svg width="34" height="12" viewBox="0 0 34 12">'
                    f'<line x1="1" y1="6" x2="27" y2="6" stroke="{stroke}" stroke-width="1.6"/>'
                    f'<path d="M26 1 L33 6 L26 11 z" fill="{stroke}"/></svg></span>')
        elif spec[0] == "text":
            _, colour, label = spec
            label = label_override or label
            ds = f"text:{_norm(colour)}"
            chip = (f'<span class="lchip"><span class="lf" style="color:{colour};font-weight:700">'
                    f'text</span></span>')
        elif spec[0] == "font":
            _, kind, label = spec
            label = label_override or label
            ds = "font:tag" if kind.startswith("tag") else f"font:{kind}"
            sample = {"mono": '<code class="lf">name_of_it</code>',
                      "sans": '<span class="lf">prose</span>',
                      "cite": f'<code class="lf" style="color:{C["cite"]};font-size:11px">file.hpp:123</code>',
                      "tag": '<b class="lf">new</b>',
                      "tag_changed": f'<span class="lf" style="color:{C["muted"]}">changed</span>'}[kind]
            chip = f'<span class="lchip">{sample}</span>'
        else:
            fill, stroke, dashed, thick, label = spec
            label = label_override or label
            ds = style_key(fill, stroke, dashed, thick)
            bw = "3px" if thick else "1.5px"
            bs = "dashed" if dashed else "solid"
            bg = "transparent" if fill == "none" else fill
            if opacity is not None:
                r, g, b = (int(fill[i:i + 2], 16) for i in (1, 3, 5))
                bg = f"rgba({r},{g},{b},{opacity})"
            chip = (f'<span class="chip" style="background:{bg};border:{bw} {bs} {stroke}"></span>')
        out.append((label, ds, chip))
    return out


def legend_html(items):
    ents = legend_entries(items)
    if not ents:
        return ""
    spans = "".join(f'<span data-style="{ds}">{chip}{esc(label)}</span>' for label, ds, chip in ents)
    return (f'<div class="figlegend"><span class="lt">Colour and font scheme used in this '
            f'figure:</span>{spans}</div>')


def figure(fig_id, w, h, aria, body, caption, boxes=(), max_width=None, legend=None):
    """A <figure> with the inline SVG, its colour and font scheme (legend=[...],
    see LEGEND), a caption, and the box register: boxes = [(label, source),
    ...] where source is the line or Note that defines the box."""
    mw = f' style="max-width:{max_width}px"' if max_width else ""
    reg = ""
    if boxes:
        items = "".join(f"<li><code>{esc(l)}</code>: {esc(s)}</li>" for l, s in boxes)
        reg = f'<details class="boxes"><summary>Boxes and their sources ({len(boxes)})</summary><ul>{items}</ul></details>'
    return (f'<figure{mw}>{svg_open(fig_id, w, h, aria)}{body}</svg>'
            f'{legend_html(legend)}'
            f'<figcaption>{esc(caption)}</figcaption>{reg}</figure>')


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


def lane(x, y, w, h, label, sub=None):
    """A wall-clock lane (one thread/actor): a light band with a 2-line label
    in a 140 px gutter at the left. Returns the svg and the x where time
    starts."""
    out = [rect(x, y, w, h, "#fff", C["line"], 1, 3),
           text(x + 8, y + h / 2 + (0 if sub else 4), label, 11, weight=600)]
    if sub:
        out.append(text(x + 8, y + h / 2 + 13, sub, 9.5, fill=C["muted"]))
    return "".join(out), x + 140


def work_block(x, y, w, h, label, fill, stroke, idle=False, size=9.5):
    """Real work = solid block; waiting/idle = dashed outline, white fill.
    Draw idle blocks BEFORE any text that may overlap them."""
    if idle:
        r = rect(x, y, w, h, "#fff", stroke, 1, 2, "4 3")
    else:
        r = rect(x, y, w, h, fill, stroke, 1.2, 2)
    out = [r]
    if label:
        out.append(text(x + w / 2, y + h / 2 + 3.5, label, size, "middle"))
    return "".join(out)
