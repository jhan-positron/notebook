"""Change diagram of unit k0 of the PR 4424 page for h/tron/tensor/k_vnni.hpp:
the header comment (head lines 1-42), comment only.

The figure maps the four paragraphs of the header comment to the base diagrams
that draw them. Each row names what a paragraph introduces, with the head
lines that define that name (k_vnni.hpp unless another file is named). Every
line number comes from facts/k_vnni.json or from the head file.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, line, marker_defs, rect, text,
                         text_width)

BASE = ("Updates B1 to B5: the header comment adds no code. The figure maps its "
        "four paragraphs to the base diagrams that draw them, with the head lines "
        "of every name a paragraph introduces.")

W = 700
LX, LW = 14, 354              # the paragraph boxes (left column)
BX, BW, BH = 530, 160, 60     # the base-diagram boxes (right column)
BUS_X0, BUS_DX = 392, 24      # one vertical line per base diagram
ROW = 12                      # row pitch inside a paragraph box
CHIP_W, CHIP_H = 30, 14       # the "B2" chip at the right of a row group


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _dot(x, y, r=2.6):
    """A junction mark on a bus (a filled circle drawn with rect's rx)."""
    return rect(x - r, y - r, 2 * r, 2 * r, C["ink"], C["ink"], 0, r)


# The four paragraphs of the header comment, quoted by their first words.
# groups: (rows, base diagram the group is drawn in). A row names what the
# paragraph introduces and the head lines that define it.
PARAGRAPHS = [
    dict(title="This file defines typed access to the K plane",
         ref="k_vnni.hpp:2-11", groups=[
             (["k_vnni_tensor 201-236; k_vnni_view 153-199"], "B2"),
             (["namespace k_vnni: constants 61-117, index 134-141"], "B1"),
             (["store_row, load_row, store_block, copy_token 344-436"], "B3"),
             (["block_to_vnni, block_to_rows 494-526 and",
               "Note [Row-major tail block] 437-456"], "B4"),
             (["the AVX-512 reader: kernels/k_vnni.hpp qk_group 59-61;",
               "Note [K VNNI storage] kv_cache.hpp:651-727"], "B5"),
         ]),
    dict(title="Words used here", ref="k_vnni.hpp:13-23", groups=[
             (["AMX, AVX-512, bf16, VNNI layout (TDPBF16PS, VDPBF16PS)",
               "one 64-byte row = a dimension pair of 16 tokens 66-67;",
               "a KV page holds 64 tokens: PAGE_TOKENS_64 61; a plane",
               "is K for one KV head of one page 20-28"], "B1"),
             (["128-dimension heads only: layout_on 119-130"], "B3"),
         ]),
    dict(title="Plane layout", ref="k_vnni.hpp:24-33", groups=[
             (["plane[(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j]",
               "  == K[c * 16 + t][s * 32 + 2 * dp + j]: index 134-141",
               "one (s, c) = one 1 KiB panel = one AMX B tile 78-82",
               "token i owns column (i % 16): pair_base 290-301"], "B1"),
             (["written independently, no read-modify-write: rule R1"], "B5"),
         ]),
    dict(title="Who may compute a packed address", ref="k_vnni.hpp:34-41", groups=[
             (["detail::k_vnni_access 238-247, the one route for the",
               "typed operations here, k_vnni::qk_group (kernels/",
               "k_vnni.hpp:85), qk_vnni_128x4 (amx_attn.cpp:244) and",
               "book::fill_random (kv_cache.hpp:1405, 1835-1836)"], "B2"),
             (["page accessors (kv_cache.hpp): set_k_row 2247,",
               "get_k_row 2291, set_k_block 2277, k_packed 2120"], "B3"),
             (["used by cache code, the model, hardware staging, tests"], "B5"),
         ]),
]

# The base diagrams of the page: name, two sub-lines, the lines they draw.
BASES = [
    ("B1", "data model", ["the plane, its panels, pair", "rows and the index map"],
     "k_vnni.hpp:20-32, 61-141"),
    ("B2", "type model", ["owner, views, the one access", "route, the transfer rows"],
     "k_vnni.hpp:145-284"),
    ("B3", "function model", ["every operation, its callers", "and callees"],
     "k_vnni.hpp:57-526"),
    ("B4", "sequencing model", ["the bytes of one block", "through the operations"],
     "k_vnni.hpp:344-526"),
    ("B5", "interaction model", ["who calls which operation", "from which thread"],
     "kv_cache.hpp:651-727"),
]


def _para_box(o, boxes, p, y):
    """One paragraph box at y: the quoted title, its row groups (soft bands)
    with a chip naming the base diagram, the citation. Returns (height,
    [(chip_y, base_name), ...])."""
    inner_w = LW - 12 - 6 - CHIP_W - 6 - 6
    taps = []
    gy = y + 26
    body = []
    for rows, base in p["groups"]:
        bh = len(rows) * ROW + 4
        body.append(rect(LX + 6, gy, LW - 12, bh, C["soft"], C["soft"], 0, 3))
        for i, s in enumerate(rows):
            _w(s, 9, inner_w, True, f"k0 row {p['title']}")
            body.append(text(LX + 12, gy + 11 + i * ROW, s, 9, mono=True))
        cy = gy + bh / 2
        cx = LX + LW - 6 - 6 - CHIP_W
        body.append(rect(cx, cy - CHIP_H / 2, CHIP_W, CHIP_H, "#fff", C["ink"], 1, 3))
        body.append(text(cx + CHIP_W / 2, cy + 3.5, base, 9, "middle", True, weight=700))
        taps.append((cy, base))
        gy += bh + 4
    h = gy - 4 - y + 14
    o.append(rect(LX, y, LW, h, "#fff", C["ink"], 1.2, 5))
    title = f'"{p["title"]}"'
    _w(title, 11, LW - 16, False, "k0 title")
    o.append(text(LX + 8, y + 16, title, 11, weight=600))
    o.extend(body)
    o.append(cite(LX + LW - 4, y + h - 4, p["ref"]))
    boxes.append((p["title"], p["ref"]))
    return h, taps


def _base_box(o, boxes, b, y):
    name, short, sub, ref = b
    o.append(rect(BX, y, BW, BH, C["soft"], C["ink"], 1.2, 5))
    o.append(text(BX + 8, y + 16, name, 11, mono=True, weight=700))
    _w(short, 10.5, BW - 34, False, "k0 base name")
    o.append(text(BX + 30, y + 16, short, 10.5, weight=600))
    for i, s in enumerate(sub):
        _w(s, 9, BW - 12, False, "k0 base sub")
        o.append(text(BX + 8, y + 30 + i * 11, s, 9, fill=C["muted"]))
    o.append(cite(BX + BW - 4, y + BH - 4, ref))


def fig():
    fid = "k_vnni-d0"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    # headers
    o.append(text(LX, 16, "the four paragraphs of the header comment (k_vnni.hpp:2-41)",
                  10.5, weight=700))
    o.append(text(LX, 29, "rows: the names a paragraph introduces, with the head lines "
                  "that define them", 9, fill=C["muted"]))
    o.append(text(BX, 16, "drawn in", 10.5, weight=700))
    o.append(text(BX, 29, "the base diagrams of the page", 9, fill=C["muted"]))
    # left column: the paragraph boxes
    y = 44
    taps = []                       # (y, base name)
    for p in PARAGRAPHS:
        h, t = _para_box(o, boxes, p, y)
        taps.extend(t)
        y += h + 12
    bottom = y - 12
    # right column: the base-diagram boxes, evenly spaced, nudged so that no
    # exit line runs along a tap of another bus
    bus_x = {b[0]: BUS_X0 + i * BUS_DX for i, b in enumerate(BASES)}
    n = len(BASES)
    spacing = (bottom - 44 - BH) / (n - 1)
    exits = {}
    for i, b in enumerate(BASES):
        name = b[0]
        by = 44 + i * spacing
        ye = by + BH / 2
        others = [ty for ty, tb in taps if bus_x[tb] > bus_x[name]]
        while any(abs(ye - ty) < 7 for ty in others):
            ye += 8
            by += 8
        _base_box(o, boxes, b, by)
        exits[name] = ye
    # buses, taps, dots, exits (lines first, text was drawn inside the boxes
    # at x < LX + LW, so nothing is hidden)
    for name in bus_x:
        x = bus_x[name]
        ys = [ty for ty, tb in taps if tb == name] + [exits[name]]
        o.append(line(x, min(ys), x, max(ys), C["ink"], 1.2))
        for ty, tb in taps:
            if tb == name:
                o.append(line(LX + LW, ty, x, ty, C["ink"], 1.0))
                o.append(_dot(x, ty))
        o.append(arrow(fid, "ink", [(x, exits[name]), (BX - 3, exits[name])], C["ink"], 1.4))
        o.append(_dot(x, exits[name]))
    # legend
    o.append(text(LX, bottom + 16, "a dot joins a group of rows to the vertical line of "
                  "the diagram that draws it; lines cross without a dot", 9,
                  fill=C["muted"]))
    H = int(bottom + 24)
    cap = ("Updates B1 to B5: the header comment (head lines 2-41) adds no code, so the "
           "figure maps its four paragraphs to the base diagrams that draw them. Each "
           "row names what a paragraph introduces with the head lines that define it, "
           "and a dot joins the row's group to the vertical line of the diagram it is "
           "drawn in: the plane and its index formula in B1, the owner, views and the "
           "one access route in B2, the operations and their callers in B3, the "
           "in-place conversion in B4, who writes and reads the layout in B5. Look at "
           "the fourth paragraph: only the typed operations and the two score kernels "
           "compute a packed address, through detail::k_vnni_access (B2).")
    # the colour and font scheme of this figure (only the styles it uses)
    legend = [
        ("box", "white box, ink outline: a paragraph of the header comment (its row "
                "groups on light grey bands), and the chip B1 to B5 naming the diagram "
                "a row group is drawn in"),
        ("ctx_ink", "grey fill, ink outline: a base diagram of the page, B1 to B5, with "
                    "what it draws"),
        ("solid ink dot: a row group joins the vertical line of its base diagram, or "
         "that line turns into its exit arrow", C["ink"], C["ink"], False, False),
        ("arrow", "ink arrow: the vertical line of a base diagram enters its box"),
        ("font_mono", "monospace = the names a paragraph introduces and their head lines; "
                      "bold = a base-diagram name B1 to B5"),
        ("font_sans", "sans-serif = the quoted paragraph titles, what a base diagram "
                      "draws, the column headers and the note under the figure"),
        ("font_cite", "small grey monospace = the head lines of a paragraph, or the "
                      "lines a base diagram draws (file:line)"),
    ]
    return figure(fid, W, H, "Map from the header comment's paragraphs to the base diagrams",
                  "".join(o), cap, boxes=boxes, legend=legend)
