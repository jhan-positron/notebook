"""Change diagram of unit k0 of the PR 4959 page for h/tron/tensor/k_vnni.hpp:
the header comment (head lines 2-11) now names the in-place conversion of a
block. Line numbers are head lines of PR 4959 (6b081187e1)."""
from svg_helpers import C, arrow, cite, figure, label_box, lines, marker_defs, rect, text
from base_k_vnni import _w

BASE = ("Updates B3: the header's list of what the file defines gains the fourth group "
        "of B3 (the in-place conversion block_to_vnni / block_to_rows and Note "
        "[Row-major tail block]); the other groups it names are unchanged.")

W = 700


def fig():
    fid = "k_vnni-d0"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "muted": C["muted"]})]
    o.append(text(14, 18, "the header comment (lines 2-11): what the file defines, and where "
                  "the rest lives", 12, weight=700))
    hx, hy, hw, hh = 14, 30, 672, 48
    o.append(rect(hx, hy, hw, hh, C["soft"], C["ink"], 1.2, 4))
    hl = ["\"This file defines typed access to the K plane stored in the VNNI layout "
          "(TRON_K_VNNI): ...\"",
          "the paragraph names four groups inside the file and three places outside it; "
          "the third group is new"]
    for s in hl:
        _w(s, 9.5, hw - 16, where="k0 header")
    o.append(lines(hx + 8, hy + 17, hl, 9.5, 13))
    o.append(cite(hx + hw - 4, hy + hh - 4, "k_vnni.hpp:2-11"))
    boxes.append(("the header comment (This file defines typed access ...)", "k_vnni.hpp:2-11"))
    groups = [
        ("the typed K plane", ["k_vnni_tensor: an owner that holds the bytes",
                               "k_vnni_view: a matrix view that knows the address formula",
                               "namespace k_vnni: the index map and its constants"],
         C["soft"], C["line"], "k_vnni.hpp:2-6; 59-137, 148-209", "unchanged",
         ("the typed K plane (header group)", "k_vnni.hpp:2-6 (owner 184-188, view 148-152, namespace k_vnni 59-137)")),
        ("the vector operations that move whole token rows in and out",
         ["store_row, load_row, store_block, copy_token"],
         C["soft"], C["line"], "k_vnni.hpp:5-6; 311-401", "unchanged",
         ("the vector operations (header group)", "k_vnni.hpp:5-6 (store_row 311-328, load_row 330-345, store_block 347-388, copy_token 390-401)")),
        ("the in-place conversion of one 16-token block between its row-major and its VNNI form",
         ["block_to_vnni, block_to_rows (K4), Note [Row-major tail block] below (K2)"],
         C["pend_fill"], C["pend"], "k_vnni.hpp:6-8; 403-423, 461-491", "new",
         ("the in-place conversion (header group)", "k_vnni.hpp:6-8 (block_to_vnni 461-476, block_to_rows 478-491, Note [Row-major tail block] 403-423)")),
        ("outside this file", ["the AVX-512 score reader: h/tron/kernels/k_vnni.hpp (qk_group)",
                               "the AMX QK kernel: h/tron/kernels/amx_attn_iface.hpp (qk_vnni_128x4)",
                               "who writes and reads the layout: Note [K VNNI storage] (kv_cache.hpp)"],
         C["soft"], C["line"], "k_vnni.hpp:8-11; kernels/k_vnni.hpp:38; kv_cache.hpp:685", "unchanged",
         ("outside this file (header group)", "k_vnni.hpp:8-11; kernels/k_vnni.hpp:38 (qk_group); kv_cache.hpp:685 (Note [K VNNI storage])")),
    ]
    y = hy + hh + 24
    bx, bw = 150, 536
    for title, sub, fill, stroke, ref, tag, reg in groups:
        bh = 30 + 12 * len(sub) + 10
        _w(title, 10.5, bw - 16, where="k0 title")
        for s in sub:
            _w(s, 9, bw - 16, where="k0 sub")
        o.append(rect(bx, y, bw, bh, fill, stroke, 1.4 if tag == "new" else 1, 4))
        o.append(text(bx + 8, y + 15, title, 10.5, weight=700))
        o.append(lines(bx + 8, y + 29, sub, 9, 12, fill=C["ink"]))
        col = C["new"] if tag == "new" else C["muted"]
        o.append(text(bx + 8, y + bh - 5, tag, 9, fill=col, weight=700 if tag == "new" else None))
        o.append(cite(bx + bw - 4, y + bh - 4, ref))
        boxes.append(reg)
        name = "pend" if tag == "new" else "muted"
        o.append(arrow(fid, name, [(hx + 60, hy + hh), (hx + 60, y + bh / 2), (bx - 2, y + bh / 2)],
                       C["pend"] if tag == "new" else C["muted"], 1.4))
        o.append(text(hx + 66, y + bh / 2 - 4, "names", 9, fill=C["pend"] if tag == "new" else C["muted"],
                      weight=600))
        y += bh + 12
    H = int(y) + 2
    cap = ("Updates B3: the first paragraph of the header is a table of contents of the "
           "file. It lists the typed plane, the row operations and, new in this PR, the "
           "in-place conversion of one block between its two forms with the Note that "
           "explains it. The three places outside the file (the AVX-512 reader, the AMX "
           "kernel, Note [K VNNI storage]) are unchanged.")
    legend = [
        ("ctx_ink", "grey box, ink outline: the header comment itself"),
        ("ctx", "grey box, thin grey outline: a group the header names that this PR does "
                "not change; grey 'unchanged' under it"),
        ("pend_solid", "orange box, orange-red outline: the group the header gains, the "
                       "in-place conversion of one block (K2, K4)"),
        ("orange-red arrow: the header names the new group", "arrow", C["pend"]),
        ("arrow_muted", "grey arrow: the header names an unchanged group"),
        ("font_sans", "sans-serif = the quoted header sentence, the group titles and their "
                      "members"),
        ("font_cite", "small grey monospace = the lines that define a box (file:line)"),
        ("font_tag", "bold 'new' = the group is added by this PR"),
    ]
    return figure(fid, W, H, "The header comment names the in-place conversion of a block",
                  "".join(o), cap, boxes=boxes, legend=legend)
