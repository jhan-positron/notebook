"""Change diagram of unit m1 (model.hpp page of PR 4958): the constants of the
store (head lines 3138-3148): k_store_block, k_scatter_run_len,
k_join_clock_spins (with its static_assert) and k_join_timeout_s.

The figure draws each constant as a field of B1's state group, its value, and
the arrows to the functions that read it (with the head line of each use),
plus the worked example's values on the right. Every label is an identifier
or a comment phrase of model.hpp (head line numbers of b39765ec29).
"""
from svg_helpers import (C, arrow, cite, figure, lines, marker_defs, rect, text,
                         text_width)
from base_model import MAIN_FILL, N_HELPERS_EXAMPLE, UNITS_EXAMPLE, field_row, fit

BASE = ("Updates B1 (the state group) and B3 (step 5). The four constants of B1's "
        "state group get their values and their readers: k_store_block feeds the "
        "sharing test, the unit cut and the run store; k_scatter_run_len decides "
        "between set_k_row and set_k_block; the two k_join constants are the "
        "watchdog of B3's step 5.")

FID = "model-d1"
W = 700


def use_cell(x, y, w, h, name, what, ref):
    """A reader of a constant: the function (mono), what it does with the
    value (sans), the head line of the use."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.1, 3)]
    fit(name, 9.5, w - 12, True, "m1 use name")
    o.append(text(x + 6, y + 13, name, 9.5, mono=True, weight=600))
    fit(what, 8.5, w - 12, False, "m1 use what")
    o.append(text(x + 6, y + 25, what, 8.5, fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    ink = C["ink"]
    o = [marker_defs(FID, {"ink": ink, "vnni": C["vnni"]})]
    boxes = []
    o.append(text(12, 16, "The constants of the store: B1's state group, its readers, "
                  "the worked example", 11.5, weight=700))
    o.append(cite(688, 16, "model.hpp:3138-3148"))

    # ---- the state group with the four constants --------------------------------
    SX, SW = 12, 270
    o.append(rect(SX, 28, SW, 326, C["soft"], ink, 1.2, 6))
    o.append(text(SX + 8, 44, "state (model.hpp)", 11, mono=True, weight=700))
    o.append(cite(SX + SW - 4, 44, "model.hpp:1113"))
    boxes.append(("state (model.hpp)", "model.hpp:1113 (struct state)"))
    rows = [
        ("k_store_block", ["= k_vnni::BLOCK_TOKENS_16 (16 tokens):",
                           "the size of one block save and the",
                           "longest run"], "model.hpp:3138-3139", 56),
        ("k_scatter_run_len", ["= 1: a run of this length is stored",
                               "row by row (set_k_row), not as a block"],
         "model.hpp:3140-3141", 46),
        ("k_join_clock_spins", ["= 1048576 (2^20): main reads the clock",
                                "once every this many pause loops;",
                                "static_assert: a power of two (the",
                                "check masks with it)"], "model.hpp:3142-3147", 68),
        ("k_join_timeout_s", ["= 120 (s): the join aborts this long",
                              "after the first clock read"], "model.hpp:3148", 46),
    ]
    y = 54
    mids = []
    for name, desc, ref, h in rows:
        o.append(field_row(SX + 10, y, SW - 20, h, name, desc, ref, tag="new"))
        boxes.append((name, ref))
        mids.append(y + h / 2)
        y += h + 8

    # ---- the readers --------------------------------------------------------------
    UX, UW, UH = 330, 220, 40
    uses = [
        # (which constant, name, what, ref, y offset)
        (0, "k_store_shared", "items.size() > k_store_block: 17+ items", "model.hpp:3159"),
        (0, "k_store_cut_units", "block = offset_in_page / k_store_block", "model.hpp:3180"),
        (0, "store_k_block", "conv[k_store_block], run_ix / run_t, n < 16", "model.hpp:3229, 3242-3246"),
        (1, "store_k_block", "n == k_scatter_run_len -> set_k_row", "model.hpp:3260"),
        (2, "save_k_impl (the join)", "(++spins & (k_join_clock_spins - 1)) == 0", "model.hpp:3355"),
        (3, "save_k_impl (the join)", "TRON_ASSERT(now - t0 < seconds(timeout))", "model.hpp:3358"),
    ]
    uy = 40
    for k, name, what, ref in uses:
        o.append(use_cell(UX, uy, UW, UH, name, what, ref))
        boxes.append((f"{name}: {what}", ref))
        # arrow from the constant's row to the use cell
        o.append(arrow(FID, "ink", [(SX + SW, mids[k]), (UX - 2, uy + UH / 2)], ink, 1.2))
        uy += UH + 10
    o.append(text(UX + UW / 2, 30, "readers (head line of the use)", 9.5, "middle",
                  fill=C["muted"], weight=700))
    o.append(text(UX, uy + 6, "1 constant -> every reader in the column", 8.5, fill=ink,
                  weight=600))

    # ---- worked example -------------------------------------------------------------
    EX, EW = 575, 113
    o.append(rect(EX, 28, EW, 326, "#fff", C["line"], 1, 4))
    o.append(text(EX + 6, 44, "worked example", 9.5, weight=700))
    u0, u2 = UNITS_EXAMPLE[0], UNITS_EXAMPLE[2]
    ex = [
        "41 items > 16:",
        "the store is shared",
        "",
        f"unit {u0['u']}: 16 rows =",
        "k_store_block,",
        "present 0xffff",
        f"unit {u2['u']}: 9 rows,",
        "present 0x01ff",
        "(2 .. 16: a block)",
        "",
        "a decode token:",
        "n = 1 =",
        "k_scatter_run_len",
        "-> set_k_row",
        "",
        "the join: a clock",
        "read every 2^20",
        "pause loops; abort",
        "after 120 s with",
        f"finished of {N_HELPERS_EXAMPLE}",
        "and claimed of 3",
        "in the message",
    ]
    for s in ex:
        fit(s, 8.5, EW - 10, False, "m1 example")
    o.append(lines(EX + 6, 58, ex, 8.5, 11))
    o.append(cite(EX + EW - 4, 350, "STYLE.md"))
    boxes.append(("worked example (41 items, unit 0, unit 2, a decode token, the join)",
                  "STYLE.md worked example; model.hpp:3159, 3260, 3355-3363"))

    # ---- note: what the block size ties together ---------------------------------
    NY = 366
    o.append(rect(12, NY, 676, 64, MAIN_FILL, C["line"], 1, 4))
    o.append(lines(20, NY + 15, [
        "k_store_block is the one block size of the store: the sharing threshold (more than "
        "16 items), the unit cut (a unit never",
        "crosses a 16-token block), the run (at most 16 rows, 16 row pointers for "
        "set_k_block) and the conv stack buffer (16 rows).",
        "It equals k_vnni::BLOCK_TOKENS_16 of the layout: one 64-byte pair row holds 16 "
        "tokens, so one block is one tile width.",
        "The watchdog masks spins with k_join_clock_spins - 1: that is why the constant must "
        "be a power of two (the static_assert)."], 9, 12))
    o.append(cite(684, NY + 60, "model.hpp:3138-3147; tensor/k_vnni.hpp:65"))
    boxes.append(("k_vnni::BLOCK_TOKENS_16 (one pair row holds 16 tokens)",
                  "tensor/k_vnni.hpp:65; model.hpp:3139"))
    H = NY + 76

    cap = ("Updates B1 and B3: the four constants of B1's state group, each with its "
           "value, and the arrows to every line that reads it. k_store_block (16) is read "
           "by the sharing test, the unit cut and the run store. k_scatter_run_len (1) is "
           "the one test of store_k_block that separates the per-row scatter from the "
           "block save. k_join_clock_spins (2^20) and k_join_timeout_s (120 s) are the "
           "watchdog inside B3's step 5. The worked example at the right gives the values "
           "the window of B1 sees. Nothing here is changed or removed; every constant is "
           "new.")
    legend = [
        ("ctx_ink", "grey fill, ink outline: the state (model.hpp) group of B1 that holds "
                    "the four constants"),
        ("box", "white box, ink outline: a constant (name in bold monospace, its value "
                "and meaning in sans-serif) and a reader cell (the function, what it does "
                "with the value, the head line of the use)"),
        ("ctx", "grey band, light grey outline: the note on what the block size ties "
                "together and why the spin count is a power of two"),
        ("lane", "white box, light grey outline: the worked example"),
        ("arrow", "ink arrow: a constant -> a function that reads it"),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, the note; grey "
                      "sans-serif = a secondary label"),
        "font_cite",
        ("font_tag", "bold 'new' = the constant is added by this PR"),
    ]
    return figure(FID, W, H, "The constants of the store and their readers", "".join(o),
                  cap, boxes=boxes, legend=legend)
