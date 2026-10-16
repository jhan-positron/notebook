"""Change diagram of unit m0 (model.hpp page of PR 4959): Note [Shared block
save] item 1 rewritten (comment only). Head lines 3089-3102.
"""
from svg_helpers import C, arrow, block_cell, cite, figure, lines, marker_defs, rect, text
from base_model import block_state_box, fit, note_box

BASE = ("Updates B5: the item-1 sentences are the rule B5 draws. The figure puts the base's "
        "wording (a run that fills part of a block is transposed and written as whole lines) "
        "beside the head's (only a whole block is; a shorter run goes row by row into the "
        "row-major form, and the completed block converts at the forward end unless the "
        "hardware attention scores the operation), and points each sentence at the block "
        "state it produces.")

W = 700


def fig():
    fid = "model-d0"
    o = [marker_defs(fid, {"ink": C["ink"], "gone": C["gone"], "pend": C["pend"]})]
    boxes = []
    o.append(text(20, 18, "Note [Shared block save], item 1 (block save): before and after",
                  12.5, weight=700))
    # before
    o.append(rect(20, 30, 660, 74, "#fff", C["gone"], 1.2, 5, "5 3"))
    o.append(text(28, 46, "before (the base, PR 4958)", 10.5, weight=700, fill=C["gone"]))
    bl = ["\"a run of the pass's tokens that fills (part of) one 16-token block of a page is",
          "transposed in registers. It is then written as whole 64-byte lines ... Chosen per",
          "run in store_k_block.\" (a run of 2..16 tokens; a run of one token took the scatter)"]
    for s in bl:
        fit(s, 9, 640, False, "d0 before")
    o.append(lines(28, 61, bl, 9, 11))
    o.append(text(28, 99, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(676, 100, "base model.hpp:3087-3091"))
    boxes.append(("before: '(part of) one 16-token block' (removed wording)",
                  "base model.hpp:3087-3091 (removed at head 3092, 3095)"))
    # after
    ay = 118
    o.append(rect(20, ay, 660, 118, "#fff", C["ink"], 1.2, 5))
    o.append(text(28, ay + 16, "after (the head): three sentences, three block states", 10.5,
                  weight=700))
    o.append(text(28 + 340, ay + 16, "new", 9, fill=C["new"], weight=700))
    al = ["1. \"a run of the pass's tokens that fills one whole 16-token block of a page is",
          "    transposed in registers. It is then written as whole 64-byte lines\" (3092-3094)",
          "2. \"A shorter run is stored row by row into the block's row-major form (Note",
          "    [Row-major tail block] in h/tron/tensor/k_vnni.hpp), also whole lines.\" (3095-3097)",
          "3. \"A block completed that way is queued after the join below and converted to the",
          "    VNNI layout at the forward end (convert_pending_k_blocks, Note [K VNNI storage]",
          "    in kv_cache.hpp), unless the hardware attention scores the operation's K\" (3097-3102)"]
    for s in al:
        fit(s, 9, 640, False, "d0 after")
    o.append(lines(28, ay + 31, al, 9, 11))
    o.append(cite(676, ay + 114, "model.hpp:3091-3102"))
    boxes.append(("after: item 1 of Note [Shared block save] (head)", "model.hpp:3091-3102"))
    # the states each sentence produces
    sy = 262
    o.append(block_state_box(20, sy, 200, 58, "vnni", "converted: VNNI layout",
                             ["sentence 1: a run of 16 ->", "store_block + note_k_block_saved"],
                             "model.hpp:3316-3333"))
    boxes.append(("converted: VNNI layout (a run of 16)", "model.hpp:3316-3333"))
    o.append(block_state_box(250, sy, 200, 58, "rm", "row-major rows",
                             ["sentence 2: a run of 1..15 ->", "set_k_row -> store_row_major"],
                             "model.hpp:3297-3315"))
    boxes.append(("row-major rows (a run of 1..15)", "model.hpp:3297-3315; k_vnni.hpp:445"))
    o.append(block_state_box(480, sy, 200, 58, "pend", "complete, may wait",
                             ["sentence 3: 16 rows saved by short", "runs -> queued, converted later"],
                             "model.hpp:3426-3428"))
    boxes.append(("complete, may wait (queued after the join)", "model.hpp:3152-3166; 3426-3428"))
    o.append(arrow(fid, "ink", [(120, ay + 118), (120, sy - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(350, ay + 118), (350, sy - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(580, ay + 118), (580, sy - 2)], C["ink"]))
    hy = sy + 76
    o.append(arrow(fid, "pend", [(580, sy + 58), (580, hy - 2)], C["pend"]))
    o.append(text(588, hy - 10, "forward end, unless ...", 8.5, fill=C["pend"], weight=600))
    o.append(block_state_box(250, hy, 200, 58, "vnni", "converted: VNNI layout",
                             ["convert_pending_k_blocks ->", "k_block_to_vnni_at -> block_to_vnni"],
                             "model.hpp:3170-3177"))
    boxes.append(("converted at the forward end (convert_pending_k_blocks)", "model.hpp:3168-3177"))
    o.append(arrow(fid, "pend", [(580, hy + 29), (452, hy + 29)], C["pend"]))
    o.append(block_state_box(480, hy, 200, 58, "hw", "row-major, no bits (hardware attention)",
                             ["the unless: cached_operation_uses_hw", "-> no bit, no entry, stays row-major"],
                             "model.hpp:3419; kv_cache.hpp:763", size=8.5))
    boxes.append(("row-major, no bits (hardware attention)",
                  "model.hpp:3414-3419; kv_cache.hpp:763-799 (Note [Row-major blocks under hardware attention])"))
    o.append(note_box(20, hy, 222, 58, "where the words are defined",
                      ["Note [Row-major tail block]: k_vnni.hpp:403", "Note [K VNNI storage]: kv_cache.hpp:685",
                       "Note [Row-major blocks ...]: kv_cache.hpp:763"], None, size=8.5))
    boxes.append(("Note [Row-major tail block], Note [K VNNI storage], Note [Row-major blocks under hardware attention]",
                  "k_vnni.hpp:403; kv_cache.hpp:685; kv_cache.hpp:763"))
    H = hy + 72
    cap = ("Updates B5: the rewritten item 1 of Note [Shared block save] is the rule the code "
           "of M2 and M3 follows. The base's sentence let a run that fills part of a block "
           "take the block save; the head's three sentences say that only a whole block does, "
           "that a shorter run goes row by row into the row-major form, and that the "
           "completed block converts at the forward end unless the hardware attention scores "
           "the operation. Each sentence is pointed at the block state it produces, named as "
           "in B5.")
    legend = [
        ("gone", "red dashed: the base's wording, removed"),
        ("box", "white box, ink outline: the head's wording"),
        ("vnni", "blue: converted: VNNI layout (a whole-block save; the result of the conversion)"),
        ("rm", "orange: row-major rows (a run of 1..15 tokens)"),
        ("pend", "orange-red dashed: complete, may wait (queued after the join)"),
        ("hw", "yellow: row-major, no bits (the hardware attention scores the operation)"),
        ("ctx", "grey note: where the three Notes are defined"),
        ("arrow", "ink arrow: a sentence -> the block state it produces"),
        ("orange-red arrow: a queued block converts at the forward end, or stays row-major", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the head's sentences; red 'removed' = the base's"),
    ]
    return figure(fid, W, H, "Note [Shared block save] item 1: before and after", "".join(o),
                  cap, boxes=boxes, legend=legend)
