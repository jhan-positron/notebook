"""Change diagram of unit c2 (kv_cache.hpp page of PR 4956): the row view page::k
exists only for row-major slots.

Head lines 1974-2039: the comment and the eight overloads of page::k, each with
the new constraint !k_vnni::layout_on.
"""
from svg_helpers import C, arrow, cite, figure, lines, marker_defs, rect, text
from base_kv_cache import fit, nx_box, tag

BASE = ("Updates B2 and B3: the row-major accessor column of B2 and the last row of the "
        "function model, opened into the eight overloads of page::k with their new "
        "constraint, the row-major outcome (kv_block::k_view, as before) and the VNNI "
        "outcome (the function does not exist; each caller's if constexpr takes the "
        "typed accessor instead).")

W = 700


def fig():
    fid = "kv_cache-d2"
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "muted": C["muted"]})]
    boxes = []
    o.append(text(20, 18, "page::k: eight overloads, each now requires "
                  "!k_vnni::layout_on<head_size>", 12.5, weight=700))
    o.append(text(20, 32, "comment 1974-1975: \"K data indexed by [token][head element]. For "
                  "a VNNI slot use", 9, fill=C["muted"]))
    o.append(text(20, 43, "set_k_row / get_k_row below (Note [K VNNI storage]).\"", 9,
                  fill=C["muted"]))
    o.append(cite(W - 20, 43, "kv_cache.hpp:1974-1975"))
    boxes.append(("K data indexed by [token][head element] (the page::k comment)", "kv_cache.hpp:1974-1975"))
    cols = [("k(slot, kv_head): the plane view", 20),
            ("k(slot, kv_head, i_page): one token's row", 360)]
    for h, x in cols:
        o.append(text(x + 160, 60, h, 10.5, "middle", weight=700))
    cells = [
        # (col, row, overload lines, old requires, new part, cite)
        (0, 0, ["auto k(slot, kv_head)", "non-const, uniform layout"],
         "requires(layout_t::uniform_geometry &&", "1976-1980"),
        (0, 1, ["auto k(slot, kv_head) const", "uniform layout"],
         "requires(layout_t::uniform_geometry &&", "1982-1986"),
        (0, 2, ["template <geometry> k(slot, kv_head)", "non-const"],
         "requires(book_t::declares_geometry<geometry>() &&", "1988-1995"),
        (0, 3, ["template <geometry> k(slot, kv_head) const", ""],
         "requires(book_t::declares_geometry<geometry>() &&", "1997-2004"),
        (1, 0, ["auto k(slot, kv_head, i_page)", "non-const, uniform layout"],
         "requires(layout_t::uniform_geometry &&", "2007-2012"),
        (1, 1, ["auto k(slot, kv_head, i_page) const", "uniform layout"],
         "requires(layout_t::uniform_geometry &&", "2014-2019"),
        (1, 2, ["template <geometry> k(slot, kv_head, i_page)", "non-const"],
         "requires(book_t::declares_geometry<geometry>() &&", "2021-2029"),
        (1, 3, ["template <geometry> k(slot, kv_head, i_page) const", ""],
         "requires(book_t::declares_geometry<geometry>() &&", "2031-2039"),
    ]
    CH = 66
    for col, row, sig, old, ref in cells:
        x = cols[col][1]
        y = 68 + row * (CH + 6)
        o.append(rect(x, y, 320, CH, "#fff", C["ink"], 1.1, 4))
        fit(sig[0], 9.5, 300, True, "d2 sig")
        o.append(text(x + 8, y + 14, sig[0], 9.5, mono=True, weight=700))
        if sig[1]:
            o.append(text(x + 8, y + 26, sig[1], 8.5, fill=C["muted"]))
        fit(old, 8.5, 300, True, "d2 old")
        o.append(text(x + 8, y + 40, old, 8.5, mono=True))
        o.append(text(x + 8, y + 52, "!k_vnni::layout_on<...>)", 8.5, mono=True, weight=700))
        o.append(tag(x + 312, y + 52, "new clause", C["new"], size=8.5))
        o.append(cite(x + 316, y + CH - 4, f"kv_cache.hpp:{ref}"))
        boxes.append((f"page::k overload ({'row' if col else 'plane'} view, "
                      f"{sig[0]})", f"kv_cache.hpp:{ref}"))
    y0 = 68 + 4 * (CH + 6) + 8
    o.append(text(20, y0 + 12, "the row overloads call the plane overloads: k(slot, kv_head)"
                  "[i_page] (2011, 2018, 2028, 2038);", 9))
    o.append(text(20, y0 + 24, "the plane overloads return kv_block::k_view() (1979, 1985, 1994, "
                  "2003); the uniform overloads test the page's head_size,", 9))
    o.append(text(20, y0 + 36, "the geometry overloads test geometry.head_size (the slot's own "
                  "head size)", 9))
    # outcomes
    oy = y0 + 52
    o.append(rect(20, oy, 320, 118, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(28, oy + 16, "row-major slot: unchanged behaviour", 10.5, weight=700))
    rl = ["k() returns kv_block::k_view(): the plane as a",
          "[token][element] view; k(..., i_page) is one 256-byte row",
          "callers at the head (all under a row-major branch):",
          "model.hpp:3114  pg.k<geometry.kv>(slot, kv_head, j).set(kout)",
          "self_attention.hpp:1956  page.k<geometry.kv>(slot, kv_head)",
          "full.hpp:2758  pg_ptr->k<hw_kv>(slot, kv_head, off).data"]
    for s in rl:
        fit(s, 8.5, 304, False, "d2 rm")
    o.append(lines(28, oy + 32, rl, 8.5, 11))
    o.append(cite(336, oy + 114, "kv_cache.hpp:1979, 2011; kv_block::k_view 2590-2602"))
    boxes.append(("row-major slot: k() returns kv_block::k_view()", "kv_cache.hpp:1979, 2011, 2590-2602"))
    boxes.append(("callers of page::k", "model.hpp:3114; self_attention.hpp:1956; full.hpp:2758"))
    o.append(nx_box(360, oy, 320, 118, "VNNI slot: page::k does not exist",
                    ["a call does not compile; a token's values are not",
                     "contiguous in the plane (Note [K VNNI storage] item 6).",
                     "each caller's if constexpr takes the typed accessor:",
                     "save_k: set_k_row (model.hpp:3100-3112)",
                     "apply_page_tok: live mask + k_packed (s_a.hpp:1953-1970)",
                     "k_head_fn: get_k_row into dest (full.hpp:2751-2756)"],
                    "kv_cache.hpp:737-739"))
    boxes.append(("VNNI slot: page::k does not exist", "kv_cache.hpp:737-739 (Note [K VNNI storage] item 6); requires clauses 1978, 1984, 1990, 1999, 2010, 2017, 2023, 2033"))
    o.append(arrow(fid, "rm", [(180, y0 + 30), (180, oy - 2)], C["rm"], 1.4))
    o.append(arrow(fid, "muted", [(520, y0 + 30), (520, oy - 2)], C["muted"], 1.4, "4 3"))
    ty = oy + 130
    o.append(text(20, ty + 12, "the test: page_k_accepts_geometry is STATIC_REQUIRE_FALSE for a "
                  "VNNI geometry, and the k() checks run for row-major geometries only", 9))
    o.append(cite(20, ty + 24, "t_llama_unit.cpp:1096-1102", "start"))
    boxes.append(("page_k_accepts_geometry (test)", "t_llama_unit.cpp:1096-1102"))
    H = ty + 34
    cap = ("Updates B2 and B3: the eight overloads of page::k, four for the plane view and "
           "four for one token's row, each gain the clause !k_vnni::layout_on on its head "
           "size. For a row-major slot nothing changes: k() returns kv_block::k_view(), "
           "and the three production callers keep using it on their row-major branch. For "
           "a VNNI slot the function does not exist, so a call would not compile; every "
           "caller's if constexpr takes the typed accessor instead (set_k_row, the live "
           "mask with k_packed, get_k_row).")
    legend = [
        ("box", "white box, ink outline: one overload of page::k: its signature in bold "
                "monospace, its requires clause, the new clause in bold"),
        ("rm", "orange: the row-major outcome, kv_block::k_view() as before"),
        ("deleted", "grey dashed box: the VNNI outcome: page::k does not exist for the slot"),
        ("orange arrow: a row-major slot takes the overloads as before", "arrow", C["rm"]),
        ("grey dashed arrow: a VNNI slot finds no overload", "arrow", C["muted"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new clause' = the constraint this PR adds to each overload"),
    ]
    return figure(fid, W, H, "page::k: eight overloads constrained to row-major slots",
                  "".join(o), cap, boxes=boxes, legend=legend)
