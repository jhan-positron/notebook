"""Change diagram of unit c0 (kv_cache.hpp page of PR 4956): Note [K VNNI storage].

Head lines 685-746, comment only. The figure maps the Note's paragraphs and its
six numbered consumer items onto the base diagrams that draw them. Every box
cites the Note's lines; the right column names the code each item describes.
"""
from svg_helpers import C, arrow, cite, figure, lines, marker_defs, rect, text
from base_kv_cache import fit

BASE = ("Updates B3 and B4: the six consumer items of Note [K VNNI storage] are the six "
        "call paths of the function model and the writer and readers of the sequencing "
        "model; the figure is the index from each paragraph of the Note to the base "
        "diagram that draws it and to the code the paragraph describes.")

W = 700


def fig():
    fid = "kv_cache-d0"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    boxes = []
    o.append(text(20, 18, "Note [K VNNI storage] (kv_cache.hpp:685-746): what each paragraph "
                  "says, and where the page draws it", 11.5, weight=700))
    rows = [
        ("the gate", ["with TRON_K_VNNI the K plane of every 128-dimension head holds the",
                      "VNNI layout; same bytes, same page capacity; the gate is",
                      "k_vnni::layout_on<head_size>, so every reader and writer of a slot",
                      "sees the same layout; V is unchanged"],
         "687-695", "B1, B2", ["k_vnni::layout_on", "(tensor/k_vnni.hpp:86-95)"], C["vnni"]),
        ("the typed plane", ["kv_block::k is a k_vnni_tensor for a VNNI slot, a bf16 array",
                             "otherwise; reached only through k_vnni_view and store_row /",
                             "load_row / copy_token; detail::k_vnni_access is the one route",
                             "to the address: for those, qk_group and the test-only fill_random"],
         "697-704", "B1, B2, C1, C6", ["k_storage (2562-2575);", "k_vnni_access (tensor/k_vnni.hpp:188-194)"],
         C["vnni"]),
        ("why", ["the VNNI plane is the B operand of the AMX tile multiply; an AMX QK",
                 "kernel can read it directly; that kernel is not part of this change"],
         "706-710", "(none: lands in a later PR)", ["Note [QK orientation]", "(amx_attn_iface.hpp:191)"],
         C["muted"]),
        ("1. save_k", ["stores every token's row with page::set_k_row -> store_row:",
                       "4 AVX-512 scatters, 4 bytes into each of 64 pair rows (was 4",
                       "64-byte stores); TRON_AMX_DISABLE leaves the store untouched"],
         "713-717", "B3 row 1, B4 row 1, C4", ["set_k_row (2053-2068);", "model.hpp:3100-3112"],
         C["ink"]),
        ("2. the dense AMX page path", ["is not compiled for a VNNI slot: its kernel reads",
                                        "row-major K; every page of a VNNI slot takes the",
                                        "software path (temporary until the VNNI AMX kernel lands)"],
         "718-720", "C2 (page::k does not exist)", ["self_attention.hpp:1882-1886"], C["ink"]),
        ("3. the software path", ["uses k_vnni::qk_group with page::k_packed, the read-only",
                                  "view: AVX-512, one token per lane, no per-token gather, no",
                                  "horizontal reduction; the row-major dotter loop is compiled",
                                  "only for row-major slots"],
         "721-727", "B3 row 2, B4 row 2, C3", ["k_packed (2041-2051);", "self_attention.hpp:1953-1971"],
         C["ink"]),
        ("4. the FPGA staging path", ["needs one row per token: page_info::k_head_fn",
                                      "materializes it with page::get_k_row into caller-owned",
                                      "scratch (v_head_fn already does so for V); the staging",
                                      "bytes and the HBM layout are unchanged"],
         "728-732", "B3 row 3, B4 row 2, C4", ["get_k_row (2070-2085);", "full.hpp:2747-2760"],
         C["ink"]),
        ("5. page copies", ["copy_storage_slot (append and defrag): a whole page is one",
                            "owner assignment dst_block.k = src_block.k; a token's position",
                            "decides its column, so every other range moves token by token"],
         "733-736", "B3 row 4, B4 row 2, C5", ["copy_storage_slot (2324-2361)"], C["ink"]),
        ("6. page::k", ["does not exist for VNNI slots: a token's values are not",
                        "contiguous; the layout-agnostic set_k_row / get_k_row exist for",
                        "every slot"],
         "737-739", "B2, B3 row 7, C2, C4", ["page::k requires clauses (1974-2039)"], C["ink"]),
        ("the kill switch", ["keeps the layout: with TRON_AMX_DISABLE=1 a TRON_K_VNNI binary",
                             "runs the AVX-512 VNNI reader, not the row-major dotter; until the",
                             "VNNI AMX kernel is merged it changes no score and no visit path;",
                             "no AMX visit can occur for a VNNI slot"],
         "740-746", "B5 (note)", ["Note [AMX attention dispatch]", "(self_attention.hpp:1881)"],
         C["muted"]),
    ]
    y = 30
    for title, body, ref, where, code, col in rows:
        h = 14 + 11 * len(body) + 14
        o.append(rect(20, y, 400, h, "#fff", col, 1.2, 4))
        o.append(text(28, y + 13, title, 10, mono=True, weight=700))
        for s in body:
            fit(s, 8.5, 384, False, "d0 body")
        o.append(lines(28, y + 26, body, 8.5, 11))
        o.append(cite(416, y + h - 4, f"kv_cache.hpp:{ref}"))
        boxes.append((f"Note [K VNNI storage]: {title}", f"kv_cache.hpp:{ref}"))
        o.append(arrow(fid, "ink", [(422, y + h / 2), (438, y + h / 2)], C["ink"], 1.2))
        o.append(rect(440, y, 240, h, C["soft"], C["line"], 1, 4))
        o.append(text(448, y + 13, "drawn in: " + where, 9, weight=600))
        for c_ in code:
            fit(c_, 8.5, 226, False, "d0 code")
        o.append(lines(448, y + 27, ["the code it describes:"] + code, 8.5, 11, mono=False))
        y += h + 6
    H = y + 6
    cap = ("Updates B3 and B4: Note [K VNNI storage] is the design record that the code of "
           "this file follows. Each row quotes one paragraph of the Note in plain words "
           "(left) and names the base diagram or unit that draws it and the code it "
           "describes (right). The six numbered items are the six consumers of a VNNI "
           "slot: save_k, the AMX page path, the software path, the FPGA staging, page "
           "copies and the row view page::k. The 'why' paragraph and the kill-switch "
           "paragraph describe work outside this PR, so no diagram draws them as present.")
    legend = [
        ("box", "white box, ink outline: a paragraph of the Note that describes code of this "
                "PR (the six consumer items); title in bold monospace, the paragraph in "
                "sans-serif"),
        ("white box, blue outline: a paragraph about the layout itself (the gate, the typed "
         "plane)", "#fff", C["vnni"], False, False),
        ("white box, grey outline: a paragraph about work outside this PR (why; the kill "
         "switch)", "#fff", C["muted"], False, False),
        ("ctx", "grey box, thin grey outline: where the page draws the paragraph, and the "
                "code it describes"),
        ("arrow", "ink arrow: paragraph -> where it is drawn"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Note [K VNNI storage]: each paragraph and where the page draws it",
                  "".join(o), cap, boxes=boxes, legend=legend)
