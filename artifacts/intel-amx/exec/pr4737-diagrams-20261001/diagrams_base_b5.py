"""B5, the interaction model (threads over one forward pass)."""
from svg_helpers import C, figure, label_box, line, lines, marker_defs, rect, text


def b5():
    fid = "b5"
    W, H = 1000, 590
    o = [marker_defs(fid, {"ink": C["ink"], "gone": C["gone"], "new": C["new"]})]
    LH = 80
    lanes = [(["main forward thread"], 60), (["main helpers", "(shared block save)"], 150),
             (["attention workers"], 240), (["cooperative", "GOF staging"], 330),
             (["scheduler thread", "(tree lock)"], 420)]
    y0, y1, y2, y3, y4 = [y for _, y in lanes]
    # header
    o.append(text(170, 22, "time, left to right; one layer of forward pass N; order "
                  "schematic, durations NOT to scale", 11, fill=C["muted"]))
    o.append(line(180, 34, 838, 34, C["ink"], 1.2))
    o.append(text(509, 48, "forward pass N", 10.5, "middle", weight=600))
    o.append(line(848, 34, 976, 34, C["ink"], 1.2))
    o.append(text(912, 48, "between passes", 10.5, "middle", weight=600))
    for labs, y in lanes:
        o.append(rect(170, y, 810, LH, "#fff", C["line"], 1, 0))
        ly = y + LH / 2 + 4 - (len(labs) - 1) * 7
        o.append(lines(160, ly, labs, 11, 14, "end", weight=600))

    def blk(x, y, w, h, title, sub=(), fill="#fff", stroke=C["ink"], dash=None,
            size=10):
        return label_box(x, y, w, h, title, sub, fill, stroke, size, False, 3, dash)

    dashed = dict(fill="#fff", stroke=C["muted"], dash="4 3")
    # waiting / idle boxes first, so that nothing drawn later is hidden
    o.append(blk(182, y2 + 6, 300, 68, "wait for the latch of every writer minibatch",
                 ["(a pending page is read only after that)"], **dashed))
    o.append(blk(338, y1 + 6, 450, 68, "idle until the attention output", [], **dashed))
    o.append(blk(182, y3 + 6, 150, 68, "idle", [], **dashed))
    o.append(blk(604, y3 + 6, 184, 68, "drained by wait_for_coop_gof", [], **dashed))
    o.append(blk(670, y2 + 6, 118, 68, "done", [], **dashed))
    o.append(blk(182, y4 + 6, 606, 68, "idle: the token tree is locked only between passes",
                 [], **dashed))
    o.append(blk(850, y0 + 6, 126, 68, "no forward in flight", [], **dashed))
    for y in (y1, y2, y3):
        o.append(blk(850, y + 6, 126, 68, "", [], **dashed))
    # work boxes
    o.append(blk(182, y0 + 6, 150, 68, "save_k, minibatch 1",
                 ["set_k_row (short runs)", "set_k_block (16-token runs)"],
                 C["rm_fill"], C["rm"]))
    o.append(blk(182, y1 + 6, 150, 68, "shared window",
                 ["set_k_block +", "note_k_block_saved", "(prefill only)"],
                 C["vnni_fill"], C["vnni"]))
    o.append(blk(338, y0 + 6, 150, 68, "join; row-recording loop",
                 ["note_k_row_saved -> pending", "(not for hardware ops);",
                  "marks, credits, latch"], C["rows_fill"], C["rows"]))
    o.append(blk(494, y2 + 6, 170, 68, "attention, pending sections",
                 ["k_vnni_blocks, k_vnni_plane,", "row_ptr rows; k_layout_dense gate"],
                 C["soft"], C["ink"]))
    o.append(blk(338, y3 + 6, 260, 68, "GOF staging gather of minibatch 1",
                 ["k_head_fn -> k_row_if_row_major (in place)", "or get_k_row (gather)"],
                 C["soft"], C["ink"]))
    o.append(blk(494, y0 + 6, 150, 68, "save_k, minibatch 2",
                 ["the same block's last rows", "(grains of 8 tokens)"],
                 C["rm_fill"], C["rm"]))
    o.append(blk(650, y0 + 6, 138, 68, "run() returned",
                 ["wait_for_coop_gof;", "convert_pending_k_blocks", "-> k_block_to_vnni_at"],
                 C["pend_fill"], C["pend"]))
    # the reader/writer overlap: lanes 1..4, x 494..598
    o.append(rect(494, y0 + 2, 104, (y3 + LH - 2) - (y0 + 2), "none", C["gone"], 1.6, 4,
                  "6 3"))
    # the conversion instant
    o.append(line(800, y0 + 6, 800, y4 - 4, C["new"], 1.8, "4 3"))
    # scheduler, between passes
    o.append(blk(850, y4 + 4, 126, 36, "clear_kv_complete_at", ["-> k_forget_row"],
                 C["rm_fill"], C["rm"], size=9.5))
    o.append(blk(850, y4 + 44, 126, 32, "copy_from ->", ["copy_storage_slot"], C["soft"],
                 C["ink"], size=9.5))
    o.append(lines(170, 528, [
        "solid box = work on the K layout state or bytes; dashed box = waiting or no K work; "
        "colours as in B1.",
        "red dashed frame = the same block is read row-major by the staging gather of "
        "minibatch 1 while minibatch 2 saves its last rows.",
        "green dashed line = the first instant with no reader of this pass left: the queued "
        "blocks convert there (main thread)."], 10.5, 15, fill=C["muted"]))
    cap = ("B5, interaction model: who touches the K layout when, within one layer of "
           "one forward pass and between passes. The staging gather of an earlier "
           "minibatch can read a block's rows while a later minibatch of the same pass "
           "saves the block's last rows; the forward end, after wait_for_coop_gof, is the "
           "first point with no reader left, so the conversion runs there.")
    return figure(fid, W, H, "Interaction model: threads and the K layout state over one pass",
                  "".join(o), cap)
