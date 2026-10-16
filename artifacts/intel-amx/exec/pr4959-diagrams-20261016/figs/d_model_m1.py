"""Change diagram of unit m1 (model.hpp page of PR 4959): the deferred
conversion list and the forward-end conversion. Head lines 1837-1843 and
3148-3177.
"""
from svg_helpers import C, arrow, cite, figure, lines, marker_defs, rect, text, work_block
from base_model import CRIT_SW, crit_frame, fit, note_box, stmt_row

BASE = ("Updates B1 and B4: the pending_k_block record and the pending_k_blocks_ list of B1 "
        "get their writer (save_k_impl on main, one entry per true note_k_row_saved) and "
        "their reader (convert_pending_k_blocks, one k_block_to_vnni_at per entry). The "
        "strip at the bottom is B4's forward-end lane: the call sits after "
        "wait_for_coop_gof and before the logits, and the removed constant "
        "k_scatter_run_len is shown red dashed.")

W = 700


def member_row(x, y, w, h, decl, desc, ref):
    o = [rect(x, y, w, h, C["pend_fill"], C["pend"], 1, 3)]
    fit(decl, 10, w - 12, True, decl)
    o.append(text(x + 6, y + 13, decl, 10, mono=True, weight=600))
    fit(desc, 9, w - 12, False, decl)
    o.append(text(x + 6, y + 25, desc, 9, fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    fid = "model-d1"
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "gone": C["gone"]})]
    boxes = []
    # the struct
    o.append(text(20, 18, "struct pending_k_block (one entry) and the list pending_k_blocks_", 12,
                  weight=700))
    o.append(text(20 + 448, 18, "new", 9, fill=C["new"], weight=700))
    o.append(rect(20, 26, 320, 130, C["pend_fill"], C["pend"], 1.4, 6, "5 3"))
    o.append(text(28, 42, "pending_k_block", 11, mono=True, weight=700))
    o.append(cite(336, 42, "model.hpp:3161-3165"))
    boxes.append(("pending_k_block", "model.hpp:3161-3165"))
    o.append(member_row(28, 50, 304, 32, "page* pg", "the page that holds the block", "model.hpp:3162"))
    o.append(member_row(28, 86, 304, 32, "typename page::k_storage_ref storage",
                        "{offset, state_ix}: resolved at the save", "model.hpp:3163"))
    o.append(member_row(28, 122, 304, 32, "uint32_t block", "the block index c = offset / 16",
                        "model.hpp:3164"))
    boxes.append(("pg / storage / block", "model.hpp:3162-3164"))
    o.append(rect(360, 26, 320, 74, C["pend_fill"], C["pend"], 1.4, 6, "5 3"))
    o.append(text(368, 42, "std::vector<pending_k_block> pending_k_blocks_;", 9.5, mono=True,
                  weight=700))
    o.append(lines(368, 56, ["one entry per block this pass completed through runs",
                             "shorter than a block, when the hardware attention does",
                             "not score the operation (main thread, after the join)"], 8.5, 10))
    o.append(cite(676, 96, "model.hpp:3152-3166"))
    boxes.append(("pending_k_blocks_", "model.hpp:3166; comment 3152-3160"))
    o.append(note_box(360, 110, 320, 64, "why the storage reference is taken at the save",
                      ["\"so that a storage view change between the save and",
                       "the forward end cannot redirect the conversion\"",
                       "(the EAGLE view maps slot 0 to another storage)"],
                      "model.hpp:3159-3160; kv_cache.hpp:2186-2192", size=8.5))
    boxes.append(("why the storage reference is taken at the save",
                  "model.hpp:3159-3160; kv_cache.hpp:2186-2192"))
    # the function
    fy = 196
    o.append(text(20, fy - 6, "convert_pending_k_blocks(): the four statements", 12, weight=700))
    o.append(text(20 + 372, fy - 6, "new", 9, fill=C["new"], weight=700))
    o.append(stmt_row(20, fy, 320, 38, "if (pending_k_blocks_.empty()) return;",
                      "the 15 of 16 decode steps that queued nothing cost one test", "model.hpp:3171"))
    o.append(stmt_row(20, fy + 42, 320, 38,
                      ["TRACE_EVENT(\"model\", \"convert_k_blocks\",", "    \"blocks\", pending_k_blocks_.size());"],
                      "", "model.hpp:3172"))
    o.append(stmt_row(20, fy + 84, 320, 50,
                      ["for (pending_k_block const& b : pending_k_blocks_)",
                       "  b.pg->k_block_to_vnni_at(b.storage, b.block);"],
                      "one conversion per entry; a block converts once", "model.hpp:3173-3175"))
    o.append(stmt_row(20, fy + 138, 320, 38, "pending_k_blocks_.clear();",
                      "the list is empty for the next pass", "model.hpp:3176"))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3168-3177"))
    # what k_block_to_vnni_at does (kv_cache.hpp)
    o.append(rect(360, fy, 320, 176, C["pend_fill"], C["pend"], 1.4, 6))
    o.append(text(368, fy + 16, "page::k_block_to_vnni_at(storage, c)", 10, mono=True, weight=700))
    kl = ["returns false unless the 16 row bits of block c are set",
          "and its block bit is clear (k_rows_saved_, k_vnni_blocks_",
          "of state_ix, acquire loads);",
          "else for every KV head of the storage slot's geometry:",
          "  block_to_vnni(kv_block_at_storage(offset, kv_head)",
          "                .k.as_view(), c)",
          "  (16 load_row_major onto the stack, then store_block",
          "   with FULL_BLOCK_0XFFFF: 4 KiB read, 4 KiB written);",
          "then k_vnni_blocks_[state_ix] |= block_bit(c) (release)",
          "worked example: {slot 5, 5}, c = 2 -> bits 0b0011 -> 0b0111"]
    for s in kl:
        fit(s, 8.5, 304, False, "d1 kbtv")
    o.append(lines(368, fy + 31, kl, 8.5, 11))
    o.append(cite(676, fy + 172, "kv_cache.hpp:2261-2283; k_vnni.hpp:466-477"))
    boxes.append(("page::k_block_to_vnni_at", "kv_cache.hpp:2249-2283"))
    boxes.append(("block_to_vnni", "k_vnni.hpp:462-477"))
    o.append(arrow(fid, "pend", [(340, fy + 109), (358, fy + 109)], C["pend"]))
    # the forward end strip
    sy = fy + 200
    o.append(text(20, sy - 6, "where the call sits: the forward end of run_forward (main thread)", 12,
                  weight=700))
    o.append(rect(20, sy, 660, 70, "#fff", C["line"], 1, 3))
    o.append(text(28, sy + 14, "[main]", 10, weight=700))
    bx = 90
    o.append(work_block(bx, sy + 20, 120, 34, "plugin_state.run", C["soft"], C["ink"]))
    boxes.append(("plugin_state.run", "model.hpp:1834"))
    o.append(work_block(bx + 124, sy + 20, 120, 34, "", "#fff", C["ink"], idle=True))
    o.append(text(bx + 184, sy + 41, "wait_for_coop_gof", 9, "middle"))
    boxes.append(("wait_for_coop_gof", "model.hpp:1838; defined at 3577"))
    o.append(work_block(bx + 248, sy + 20, 150, 34, "", C["pend_fill"], C["pend"]))
    o.append(crit_frame(bx + 248, sy + 20, 150, 34))
    o.append(text(bx + 323, sy + 37, "convert_pending_", 9, "middle", True, weight=600))
    o.append(text(bx + 323, sy + 48, "k_blocks()", 9, "middle", True, weight=600))
    o.append(work_block(bx + 402, sy + 20, 100, 34, "logits", C["soft"], C["ink"]))
    boxes.append(("logits (run_logits)", "model.hpp:1845-1849"))
    o.append(cite(676, sy + 66, "model.hpp:1834-1849"))
    o.append(text(20, sy + 86, "the comment at 1840-1841: \"run() joined its workers and wait_for_coop_gof "
                  "drained the staging: no reader of a", 8.5, fill=C["muted"]))
    o.append(text(20, sy + 97, "completed K block is left\". Measured cost (PR #4959 body, trace "
                  "pr4trace-20261015): 3.7 to 4.2 us per block, once every 16 decode steps.", 8.5,
                  fill=C["muted"]))
    boxes.append(("the measured cost (PR #4959 body, trace pr4trace-20261015)",
                  "PR #4959 body, Performance; model.hpp:3172"))
    # removed constant
    ry = sy + 112
    o.append(rect(20, ry, 660, 44, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(28, ry + 15, "static constexpr size_t k_scatter_run_len = 1;", 9.5, mono=True,
                  weight=600, fill=C["gone"]))
    o.append(text(28, ry + 29, "\"A run of this length is stored row by row (set_k_row), not as a "
                  "block.\" The scatter branch of store_k_block is gone (M2).", 8.5))
    o.append(text(28, ry + 40, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(676, ry + 40, "base model.hpp:3140-3141"))
    boxes.append(("k_scatter_run_len (removed)", "base model.hpp:3140-3141 (removed at head 3151)"))
    H = ry + 56
    cap = ("Updates B1 and B4: the entry type and the list (top), the four statements of "
           "convert_pending_k_blocks and what the page does for each entry (middle), and "
           "the position of the call in the forward end (bottom, main's lane of B4). The "
           "list is filled by the row-recording loop of M3; it converts every entry once "
           "per pass, after the staging drained. The constant k_scatter_run_len of the base "
           "is removed.")
    legend = [
        ("pend", "orange-red dashed: the entry type and the list (complete blocks that wait)"),
        ("pend_solid", "orange-red solid: the conversion (k_block_to_vnni_at, convert_pending_k_blocks in the lane)"),
        ("box", "white box, ink outline: one statement of convert_pending_k_blocks"),
        ("ctx_ink", "grey block, ink outline: unchanged work of the forward end (the plugin's run, the logits)"),
        ("idle", "ink dashed: wait_for_coop_gof (main waits for the staging)"),
        ("crit", "thick solid red frame: the serial main-thread work this PR adds"),
        ("gone", "red dashed: the removed constant k_scatter_run_len"),
        ("ctx", "grey note: why the storage reference is taken at the save"),
        ("lane", "thin grey frame: main's lane"),
        ("arrow", "ink arrow: a call (none here)") if False else ("orange-red arrow: the loop body calls k_block_to_vnni_at", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR; red 'removed' = removed"),
    ]
    return figure(fid, W, H, "The deferred conversion list, its reader and the forward end",
                  "".join(o), cap, boxes=boxes, legend=legend)
