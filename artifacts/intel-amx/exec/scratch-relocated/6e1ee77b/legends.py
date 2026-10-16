import re
L58 = '''LEGEND = f"""
<p class="meta">ink = the near-black of the body text ({C['ink']}), used for box outlines, arrows and the
step badges; grey-blue = {C['unit']} (work units of the shared window). The palette is Okabe-Ito (colour-blind safe);
fills are light tints of the outline colours.</p>
<div class="chips">
<span>{chip(C['vnni_fill'], C['vnni'])}VNNI layout: the packed K plane (k_vnni_tensor / k_vnni_view), a VNNI slot (k_vnni::layout_on true), a block or panel written by store_block</span>
<span>{chip(C['vnni'], C['vnni'])}solid blue: a VNNI pair row (one 64-byte line of a panel) or a token's column, as bytes</span>
<span>{chip(C['rm_fill'], C['rm'])}row-major rows: one token's native K row in dimension order (the K buffer ks, the rows[t] pointers of store_block, a transfer row), or a row-major slot (page::k)</span>
<span>{chip(C['rm'], C['rm'])}solid orange: a row-major token row, as bytes (one 64-byte load of store_block)</span>
<span>{chip(C['empty_fill'], C['empty'], True)}grey dashed: no row saved, or an absent token lane (its bit in `present` is clear: bytes never written)</span>
<span>{chip(C['rows_fill'], C['rows'])}present: a token lane whose bit is set in the `present` mask of store_block / set_k_block (its row is stored)</span>
<span>{chip(C['unit_fill'], C['unit'])}work unit of the shared K store window (unit_start[u] .. unit_start[u + 1]), the claim counter next_unit, the window counters opened / finished / helper_windows</span>
<span>{chip(C['q_fill'], C['q'])}the attention side that waits for the store: the attention workers' pending sections, the downstream latch upstream_kvs_ready</span>
<span>{chip(C['hw_fill'], C['hw'])}hardware attention: has_hardware_slot, the per-GOF dispatch credits (context only)</span>
<span>{chip(C['hi_fill'], C['ink'])}the worked example's cell (page 7, storage slot 5, KV head 0; token 37, dimension 70; work unit 2)</span>
<span><span class="chip" style="background:#fff;border-color:{C['ink']};border-style:dashed"></span>ink dashed: waiting or idle in a wall-clock-lanes figure (a helper that spins on `opened`, main that spins on `finished`)</span>
<span><span class="chip" style="background:#fff;border-color:{C['crit']};border-width:3px"></span>thick solid red frame: the critical path (main's serial part) in a wall-clock-lanes figure</span>
<span><span class="chip" style="background:#fff;border-color:{C['muted']};border-style:dashed"></span>with the word "deleted" or "does not exist": a function or route the code does not provide</span>
<span><span class="chip" style="background:#fff;border-color:{C['gone']};border-style:dashed"></span>red dashed: before / removed (the base code: the per-token store inside the marks loop)</span>
<span><span class="chip" style="background:{C['soft']};border-color:{C['line']}"></span>grey fill, thin grey outline: context (a caller in another file, a generated plugin, a test, a note)</span>
<span><span class="chip" style="background:#e6ffec;border-color:#9fd3ad"></span>added line (head)</span>
<span><span class="chip" style="background:#ffebe9;border-color:#e0a6a0"></span>removed line (base)</span>
</div>
<p class="meta">Identifiers are set in monospace in prose, code and diagrams. The same concept has
the same colour on all three pages. A dashed outline means "waiting", "not written" or "no bytes saved". Threads
are lanes or bracketed names ([main], [helper 1]), never colours. The words "new" and "changed" are markers in bold
ink, not a colour. Every box cites the line or Note that defines it
(small grey text in the box, and the "Boxes and their sources" list under each figure). Every
arrow between data-model boxes says how many.</p>"""'''
L59 = '''LEGEND = f"""
<p class="meta">ink = the near-black of the body text ({C['ink']}), used for box outlines, arrows and the
step badges; orange-red = {C['pend']} (a complete block that waits for its conversion, and the conversion itself), green =
{C['rows']} (k_rows_saved_ bits), pink = {C['blk']} (k_vnni_blocks_ bits). The palette is Okabe-Ito (colour-blind safe);
fills are light tints of the outline colours.</p>
<div class="chips">
<span>{chip(C['vnni_fill'], C['vnni'])}VNNI layout: a converted block (its k_vnni_blocks_ bit set), a whole-block save, the packed plane k_vnni_tensor / k_vnni_view</span>
<span>{chip(C['vnni'], C['vnni'])}solid blue: a VNNI pair row (one 64-byte line of a panel) or a token's column, as bytes</span>
<span>{chip(C['rm_fill'], C['rm'])}row-major rows: the row-major tail block of a VNNI slot (row_major_row, store_row_major, load_row_major), a row-major slot, or one token's row in dimension order</span>
<span>{chip(C['rm'], C['rm'])}solid orange: a row-major token row, as bytes (4 whole 64-byte lines)</span>
<span>{chip(C['pend_fill'], C['pend'], True)}complete, may wait: a block whose 16 row bits are set and whose block bit is clear; the deferred conversion list pending_k_blocks_</span>
<span>{chip(C['pend_fill'], C['pend'])}drawn solid: the conversion of such a block (block_to_vnni, k_block_to_vnni_at, convert_pending_k_blocks) and the way back (block_to_rows)</span>
<span>{chip(C['rows_fill'], C['rows'])}k_rows_saved_: a saved-row bit that is set (one square per page offset)</span>
<span>{chip(C['blk_fill'], C['blk'])}k_vnni_blocks_: a converted-block bit that is set (one square per 16-token block)</span>
<span>{chip(C['empty_fill'], C['empty'], True)}grey dashed: no row saved (bytes undefined), a bit that is clear</span>
<span>{chip(C['hw_fill'], C['hw'])}hardware attention: an operation the FPGA scores (cached_operation_uses_hw: no row bit, no conversion, the block stays row-major) and the FPGA staging path (gof::populate, page_info::k_head_fn, k_row_if_row_major)</span>
<span>{chip(C['eagle_fill'], C['eagle'])}EAGLE storage: the extra physical slot and its state entry layout_t::n_slots (k_state_ix, eagle_view_active)</span>
<span>{chip(C['q_fill'], C['q'])}query side: Q rows, the dotters dot_q, the live mask of k_vnni::qk_group, the scores s_pages, the AMX gate k_layout_dense</span>
<span>{chip(C['unit_fill'], C['unit'])}work unit of the shared K store window of PR 4958 (context only)</span>
<span>{chip(C['hi_fill'], C['ink'])}the worked example's cell (page 7, storage slot 5, KV head 0; token 37, dimension 70; block 2)</span>
<span><span class="chip" style="background:#fff;border-color:{C['muted']};border-style:dashed"></span>with the word "deleted" or "does not exist": a function or route the code does not provide (page::k for a VNNI slot, a partial set_k_block)</span>
<span><span class="chip" style="background:#fff;border-color:{C['gone']};border-style:dashed"></span>red dashed: before / removed (the base code: the partial block save with a present mask, the scatter of a single-token run)</span>
<span><span class="chip" style="background:{C['soft']};border-color:{C['line']}"></span>grey fill, thin grey outline: context (a caller in another file, a test, a note)</span>
<span><span class="chip" style="background:#e6ffec;border-color:#9fd3ad"></span>added line (head)</span>
<span><span class="chip" style="background:#ffebe9;border-color:#e0a6a0"></span>removed line (base)</span>
</div>
<p class="meta">Identifiers are set in monospace in prose, code and diagrams. The same concept has
the same colour on all three pages. A dashed outline means "waiting", "not read" or "no bytes saved". Threads
are lanes or bracketed names, never colours. The words "new" and "changed" are markers in bold
ink, not a colour. Every box cites the line or Note that defines it
(small grey text in the box, and the "Boxes and their sources" list under each figure). Every
arrow between data-model boxes says how many.</p>"""'''
for pr, L in (("4958", L58), ("4959", L59)):
    p = f"/home/jhan/workspace/intel-AMX/exec/pr{pr}-diagrams-20261016/page_common.py"
    s = open(p).read()
    s2, n = re.subn(r'LEGEND = f""".*?arrow between data-model boxes says how many\.</p>"""', L, s, count=1, flags=re.S)
    assert n == 1, pr
    open(p, "w").write(s2)
    # the catalogue: add 'present' (PR 4958) and keep the rest
    sp = f"/home/jhan/workspace/intel-AMX/exec/pr{pr}-diagrams-20261016/svg_helpers.py"
    t = open(sp).read()
    if pr == "4958":
        t = t.replace('    "eagle": (C["eagle_fill"]',
            '    # PR 4958: the present mask of store_block / set_k_block (one bit per token lane of a block)\n'
            '    "present": (C["rows_fill"], C["rows"], False, False,\n'
            '                "present: a token lane whose bit is set in the present mask (its row is stored); one square per lane"),\n'
            '    "eagle": (C["eagle_fill"]', 1)
        assert '"present"' in t
    open(sp, "w").write(t)
    print(pr, "legend replaced")
