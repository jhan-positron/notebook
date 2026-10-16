"""Change diagram of unit m0 (model.hpp page): Note [Shared block save].

Comment-only unit (head lines 3085-3152, every line added by the diff). The
figure maps each paragraph and bullet of the Note to the base diagrams B1-B5
of the page that draw it, with the head lines the paragraph covers. A row's
title is the paragraph's opening words; its description lines paraphrase the
rest of the paragraph (memory orders and thread names as the Note states
them); the worked example (40 items, units {0, 16, 32, 40}) is the one of
base_model.py. Every line number comes from the head file.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, line, marker_defs, rect, text,
                         text_width)
from base_model import MAIN_FILL, N_UNITS_EXAMPLE, UNIT_START_EXAMPLE

BASE = ("Index into B1 to B5 (comment-only unit: the figure maps each paragraph of "
        "the Note to the base diagram that draws it; no base shape changes). The "
        "problem and the two remedies land on B2, B4 and B5, the window protocol "
        "bullets on B1, B3 and B4.")

FID = "model-d0"
W = 700
# the paragraph column and the chip band of the five base diagrams
PX, PW = 12, 448
CHIP_X0, CHIP_PITCH, CHIP_W, CHIP_H = 502, 38, 30, 18
BAND_X = 498                      # where a row's arrow ends, the band starts
TITLE_SIZE, DESC_SIZE, LH = 9.5, 9, 11
BOLD = 0.62                       # bold DejaVu Sans: about 0.62 em per char

B_NAMES = [("B1", "data model"), ("B2", "function model"),
           ("B3", "sequencing model"), ("B4", "interaction model"),
           ("B5", "store decision")]

UNITS_TXT = "{" + ", ".join(str(v) for v in UNIT_START_EXAMPLE) + "}"

# Sections of the Note, in order: (section title, head lines, tag, rows).
# A row: (opening words of the paragraph, description lines, (first, last)
# head line, base diagrams that draw it).
SECTIONS = [
    ("Note [Shared block save]", (3085, 3152), "new comment text: 68 lines added", [
        ("save_k stores the K rows of every token of the minibatch",
         ["once per (layer, pass); with the VNNI K layout: the main thread's largest serial",
          "piece of work in a prefill layer; measured 2026-09-14 (delphi-3bda, qwen3-4b,",
          "8 users, prompt 1024, 128 tokens of each user per pass): 0.86 ms per layer,",
          "105 ns per (token, KV head) row; the attention workers' pending sections",
          "wait behind it"],
         (3087, 3094), "B2 B4"),
    ]),
    ("Two things shorten it:", (3094, 3116), None, [
        ("1. Block save (store_block, page::set_k_block)",
         ["a run that fills one whole 16-token block: transposed in registers, written as",
          "whole 64-byte lines (chosen per run in store_k_block); a shorter run: row by row",
          "into the block's row-major form, queued after the join and converted at the",
          "forward end (convert_pending_k_blocks), unless the hardware attention scores",
          "the operation's K (the block stays row-major)"],
         (3095, 3106), "B1 B2 B4 B5"),
        ("2. Sharing with the main helpers",
         ["in generated plugins the helpers are idle while main runs save_k (their next",
          "kernel waits for the attention output): run_main_help calls save_k at the same",
          "statement position with the helper's worker_ix; worker_ix 0 is [main], 1 ..",
          "n_workers - 1 are the [helpers]; every thread claims work units until none is",
          "left; n_workers == 1 never shares (handwritten plugins, unit tests except the",
          "shared-save case of t_llama_unit)"],
         (3107, 3116), "B1 B2 B4"),
    ]),
    ("The window protocol (fields in batch::k_store_window, common.hpp)", (3117, 3143),
     None, [
        ("- both sides decide with k_store_shared()",
         ["a window exists only when it says yes, so a [helper] never waits for a window",
          "[main] does not open; a pass with at most 16 items (a decode step) or more",
          "than 128 workers is not shared"],
         (3118, 3121), "B2 B3"),
        ("- main cuts the item list into work units (unit_start[])",
         ["a unit: consecutive items in one 16-token block of one page with the same",
          "token_jobs_do_kv value; two threads may write one block without conflict",
          "(masked stores on disjoint token lanes: the Note's phrase; at the head a short",
          "run writes its token's own bytes through set_k_row, see M4); [main] zeroes",
          "next_unit and finished, then increments opened (release); a [helper]'s W-th",
          "call waits for opened >= W (acquire): window W = the W-th shared save_k of",
          "the pass on both sides",
          f"worked example: unit_start {UNITS_TXT}, n_units {N_UNITS_EXAMPLE}"],
         (3122, 3132), "B1 B3"),
        ("- every thread claims units with fetch_add on next_unit",
         ["(acq_rel at model.hpp:3393); it stores the rows of each unit it claims; a unit",
          "index is assigned once, so a thread that leaves the claim loop has stored",
          "every unit it took"],
         (3133, 3135), "B3 B4"),
        ("- a helper increments finished (release) when its claim loop ends",
         ["[main] returns only when finished == n_workers - 1 (acquire); four things then",
          "hold: every unit is stored; no helper is inside a window main has left; the",
          "counters are main's to reset; every row store happens-before the downstream",
          "latch count_down (upstream_kvs_ready)"],
         (3136, 3141), "B3 B4"),
        ("- the per-token completion marks and GOF credits stay on main",
         ["[main] after the join, in q_batch->items order, one token at a time",
          "(mark_k_complete, credit_gof_save)"],
         (3142, 3143), "B2 B3 B4"),
    ]),
    ("Closing paragraph (\"main's join cannot deadlock\")", (3144, 3151), None, [
        ("The rows a helper reads (ks) are ready for two reasons",
         ["[main] waited for every token's K channel before calling save_k, and the",
          "channel phase cannot advance while main is inside save_k; a [helper] reaches",
          "its save_k call without main's help (nothing blocks between its K/Q rope kernel",
          "and this statement), so main's join cannot deadlock; a join not complete within",
          "about two minutes (k_join_timeout_s, 120 s after the first clock read) aborts",
          "with the counters in the message"],
         (3144, 3151), "B1 B3 B4"),
    ]),
]


def _w(s, size, mono=False, bold=False):
    tw = text_width(s, size, mono)
    return tw * (BOLD / 0.55) if bold and not mono else tw


def _fit(s, size, w, mono=False, bold=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = _w(s, size, mono, bold)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w:.0f}", file=sys.stderr)


def _ref(rng):
    a, b = rng
    return f"model.hpp:{a}" if a == b else f"model.hpp:{a}-{b}"


def chip_x(k):
    """Left x of the chip of base diagram B<k+1>."""
    return CHIP_X0 + k * CHIP_PITCH


def chip(x, y, name):
    return (rect(x, y, CHIP_W, CHIP_H, "#fff", C["ink"], 1.1, 3) +
            text(x + CHIP_W / 2, y + 13, name, 9.5, "middle", True, weight=700))


def para_row(y, title, desc, rng, drawn_in):
    """One paragraph: its box (opening words, description lines, head lines),
    an arrow into the chip band, and one chip per base diagram that draws it.
    The citation sits on the title line when the title leaves room for it,
    else in the lower-right corner (then the last line must stay short).
    Returns (svg, height, ref)."""
    ref = _ref(rng)
    cite_w = text_width(ref, 8.5, True)
    h = 21 + LH * len(desc)
    o = [rect(PX, y, PW, h, MAIN_FILL, C["line"], 1, 4)]
    title_w = _w(title, TITLE_SIZE, bold=True)
    cite_on_title = title_w + cite_w + 24 <= PW - 16
    o.append(text(PX + 8, y + 12, title, TITLE_SIZE, weight=600))
    if cite_on_title:
        o.append(cite(PX + PW - 4, y + 12, ref))
        last_w = PW - 16
    else:
        _fit(title, TITLE_SIZE, PW - 16, bold=True, where="m0 title")
        o.append(cite(PX + PW - 4, y + h - 4, ref))
        last_w = PW - 16 - cite_w - 10
    for i, s in enumerate(desc):
        avail = last_w if i == len(desc) - 1 else PW - 16
        _fit(s, DESC_SIZE, avail, where=f"m0 desc line {i} of '{title[:30]}'")
        o.append(text(PX + 8, y + 24 + i * LH, s, DESC_SIZE, fill=C["muted"]))
    ym = y + h / 2
    ks = [int(n[1]) - 1 for n in drawn_in.split()]
    # one grey line from the box to the last chip's right edge, drawn under
    # every chip of the row (no arrowhead: an arrowhead at the band edge
    # pointed at the first chip only)
    o.append(line(PX + PW + 3, ym, chip_x(max(ks)) + CHIP_W, ym, C["line"], 1.2))
    for k in ks:
        o.append(chip(chip_x(k), ym - CHIP_H / 2, B_NAMES[k][0]))
    return "".join(o), h, ref


def section(y, title, rng, tag=None):
    """A section title (the Note's own words), its head lines at the right end
    of the chip band, and an optional tag under the title's line."""
    o = [text(PX, y, title, 11.5, weight=700)]
    _fit(title, 11.5, BAND_X - PX - 8, bold=True, where="m0 section")
    o.append(cite(chip_x(4) + CHIP_W, y, _ref(rng)))
    if tag:
        o.append(text(chip_x(4) + CHIP_W, y + 13, tag, 9.5, "end", fill=C["new"],
                      weight=700))
    return "".join(o)


def fig():
    o = [marker_defs(FID, {"ink": C["ink"]})]
    boxes = []
    # header: column titles and the B1..B5 column labels over the chip band
    o.append(text(PX, 14, "paragraph or bullet of the Note (head lines)", 11,
                  weight=700))
    band_mid = (chip_x(0) + chip_x(4) + CHIP_W) / 2
    o.append(text(band_mid, 14, "drawn in base diagram", 10, "middle", weight=700))
    for k, (nm, _) in enumerate(B_NAMES):
        o.append(text(chip_x(k) + CHIP_W / 2, 32, nm, 10, "middle", True,
                      fill=C["muted"], weight=700))
    y = 52
    for stitle, srng, tag, rows in SECTIONS:
        o.append(section(y, stitle, srng, tag))
        y += 19 if tag else 6
        for title, desc, rng, drawn in rows:
            s, h, ref = para_row(y, title, desc, rng, drawn)
            o.append(s)
            boxes.append((title, f"{ref} (Note [Shared block save])"))
            y += h + 4
        y += 14
    # key: the five base diagrams with their figure ids
    o.append(line(PX, y, chip_x(4) + CHIP_W, y, C["line"]))
    y += 15
    key1 = "   |   ".join(f"{nm} {desc}" for nm, desc in B_NAMES[:3])
    key2 = "   |   ".join(f"{nm} {desc}" for nm, desc in B_NAMES[3:])
    o.append(text(PX, y, key1, 9.5))
    o.append(text(PX, y + 13, key2 + "   (figures model-b1 to model-b5 in section 1)",
                  9.5))
    o.append(text(PX, y + 27, "a chip = that base diagram draws the paragraph; the row's "
                  "line runs under its chips; [...] = the thread the Note names", 9,
                  fill=C["muted"]))
    H = y + 36
    cap = ("Index into B1 to B5 (comment-only unit; no base shape changes). The Note is "
           "the design record of the shared K store window that the five base diagrams "
           "draw. Each row is one paragraph or bullet of the Note with its head lines. "
           "Its line runs under the base diagrams that draw it (the chips B1 to B5). The "
           "unit-cut row flags the Note's phrase 'masked stores on disjoint token lanes' "
           "(model.hpp:3125-3126): at the head a short run writes its token's own bytes "
           "through set_k_row (kv_cache.hpp:2252-2258). The problem and the two "
           "remedies land on B2 (the functions), B4 (the lanes, the base diagram that "
           "quotes the 0.86 ms per layer measurement) and B5 (the store decision). The "
           "five protocol bullets land on B1 (the window fields), B3 (the steps with "
           "their memory orders) and B4. The unit-cut bullet quotes the worked example's "
           "unit table. Look at the closing paragraph: its two reasons are B4's K channel "
           "wait and rope kernel, and its watchdog is B3's step 5.")
    legend = [
        ("ctx", "grey fill, light grey outline: one paragraph or bullet of the Note (its "
                "opening words in bold, its description in grey, its head lines at the "
                "right)"),
        ("box", "white box, ink outline: a chip B1 to B5 = the base diagram that draws "
                "the paragraph of its row; the name in bold monospace"),
        ("thin light grey line: joins a paragraph row to the chips of the base diagrams "
         "that draw it", "line", C["line"]),
        ("font_mono", "bold monospace = the chip names and the column labels B1 to B5 "
                      "over the chip band"),
        ("font_sans", "sans-serif = the Note's section titles, a paragraph's opening "
                      "words (bold) and its description lines (grey) in the grey "
                      "paragraph rows, the key under the rule"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the head lines of a section or a paragraph "
                      "(model.hpp:first-last)"),
        ("font_tag", "bold 'new comment text: 68 lines added' = the whole Note is added "
                     "by this PR; no row is marked changed or removed"),
    ]
    return figure(FID, W, H, "Map from the paragraphs of Note [Shared block save] to the "
                  "base diagrams that draw them", "".join(o), cap, boxes=boxes,
                  legend=legend)
