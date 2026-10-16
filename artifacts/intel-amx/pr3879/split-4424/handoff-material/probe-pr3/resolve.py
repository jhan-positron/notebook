#!/usr/bin/env python3
"""resolve.py <worktree>: resolve the three conflicts of `git apply --3way ref/S-diff-4d3a..ba69.patch`
on the PR-2 head 0ee8671d35 (PR3-handoff.md step 1), by exact text. Each conflict block must be present
exactly once with exactly the expected "ours" and "theirs" sides; otherwise the script fails and changes
nothing in that file. Written 2026-10-11 from the probe apply (handoff-material/probe-pr3/conflicts.txt)."""
import pathlib
import sys

W = pathlib.Path(sys.argv[1])

# (file, ours, theirs, resolution). "ours" = the PR-2 head text, "theirs" = the patch's text (ba69cb513e).
CONFLICTS = [
    (
        "h/tron/kernels/amx_attn_iface.hpp",
        "// of the page (a panel is 16 dimension-pair rows x 16 tokens, one B tile;\n"
        "// h/tron/tensor/k_vnni.hpp) are the B operand. The tiles come out as\n"
        "// S[query][token]. No transpose is needed. The extra work moves to the K store\n"
        "// (a scatter of 64 dimension pairs per token, in save_k) and to the software\n"
        "// reader k_vnni::qk_group for partial pages.\n",
        "// of the page are the B operand. The tiles come out as S[query][token]. No\n"
        "// transpose is needed. The cost moves to two places. The K store scatters 64\n"
        "// dimension pairs per token when the token's run has one token (save_k,\n"
        "// page::set_k_row). A run of two or more consecutive tokens of one block uses\n"
        "// the block save (page::set_k_block). The software reader for partial pages\n"
        "// runs k_vnni::qk_group instead of the row-major dotter.\n",
        # PR-2's panel definition and "extra work" wording, with the patch's two store paths.
        "// of the page (a panel is 16 dimension-pair rows x 16 tokens, one B tile;\n"
        "// h/tron/tensor/k_vnni.hpp) are the B operand. The tiles come out as\n"
        "// S[query][token]. No transpose is needed. The extra work moves to two places.\n"
        "// The K store scatters 64 dimension pairs per token when the token's run has\n"
        "// one token (save_k, page::set_k_row). A run of two or more consecutive tokens\n"
        "// of one block uses the block save (page::set_k_block). The software reader for\n"
        "// partial pages runs k_vnni::qk_group instead of the row-major dotter.\n",
    ),
    (
        "h/tron/models/model.hpp",
        "\n"
        "        // Update the page first so HW sees the latest K values.\n"
        "        for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {\n"
        "          auto kout = slice<geometry.kv.head_size>()(\n"
        "              ks[ix].as_view(), kv_head * geometry.kv.head_size);\n"
        "          if constexpr (k_vnni::layout_on<geometry.kv.head_size>) {\n"
        "            // VNNI K plane (Note [K VNNI storage] in kv_cache.hpp): the row is\n"
        "            // scattered into the token's column of the plane (page::set_k_row).\n"
        "            // A bf16 K buffer is read in place. Any other activation type is\n"
        "            // converted to bf16 on the stack first, as the row-major store\n"
        "            // does in place.\n"
        "            using kv_elem_t =\n"
        "                std::remove_cv_t<std::remove_pointer_t<decltype(kout.data)>>;\n"
        "            if constexpr (std::is_same_v<kv_elem_t, bf16>) {\n"
        "              // The row view keeps the K buffer's alignment and DMA flags.\n"
        "              pg.template set_k_row<geometry.kv>(\n"
        "                  slot, kv_head, static_cast<size_t>(j), k_source_row(kout));\n"
        "            } else {\n"
        "              alignas(64) bf16 row[geometry.kv.head_size];\n"
        "              k_destination_row<geometry.kv.head_size>(row).set(kout);\n"
        "              pg.template set_k_row<geometry.kv>(slot, kv_head, static_cast<size_t>(j),\n"
        "                  k_source_row<geometry.kv.head_size>(row));\n"
        "            }\n"
        "          } else {\n"
        "            pg.template k<geometry.kv>(slot, kv_head, j).set(kout);\n"
        "          }\n"
        "        }\n"
        "\n",
        "",
        # The patch deletes the per-row loop of the mark loop (store_k_block does the stores now).
        "",
    ),
    (
        "h/tron/tensor/k_vnni.hpp",
        "// rows in and out (store_row, load_row, copy_token). The AVX-512 score reader\n"
        "// of this layout is in h/tron/kernels/k_vnni.hpp and the AMX QK kernel in\n"
        "// h/tron/kernels/amx_attn_iface.hpp. Who writes and\n",
        "// rows in and out (store_row, load_row, store_block, copy_token). The AVX-512\n"
        "// score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who writes and\n",
        "// rows in and out (store_row, load_row, store_block, copy_token). The AVX-512\n"
        "// score reader of this layout is in h/tron/kernels/k_vnni.hpp and the AMX QK\n"
        "// kernel in h/tron/kernels/amx_attn_iface.hpp. Who writes and\n",
    ),
    (
        "h/tron/tensor/k_vnni.hpp",
        "// this token's 64 pair slots are written. The row is read with unaligned loads.\n"
        "// The token index is checked here, as the packed-V operations check theirs: an\n"
        "// index at or above Rows would scatter into other tokens' slots and past the end\n"
        "// of the plane.\n",
        "// this token's 64 pair slots are written. So several threads may store\n"
        "// different tokens of one plane at the same time (Note [Shared block save] in\n"
        "// model.hpp). The row is read with unaligned loads.\n",
        "// this token's 64 pair slots are written. So several threads may store\n"
        "// different tokens of one plane at the same time (Note [Shared block save] in\n"
        "// model.hpp). The row is read with unaligned loads. The token index is checked\n"
        "// here, as the packed-V operations check theirs: an index at or above Rows\n"
        "// would scatter into other tokens' slots and past the end of the plane.\n",
    ),
]

rc = 0
for f, ours, theirs, res in CONFLICTS:
    p = W / f
    s = p.read_text()
    block = "<<<<<<< ours\n" + ours + "=======\n" + theirs + ">>>>>>> theirs\n"
    n = s.count(block)
    if n != 1:
        print(f"FAIL {f}: expected conflict block found {n} times")
        rc = 1
        continue
    s = s.replace(block, res)
    p.write_text(s)
    width = max((len(l) for l in res.splitlines()), default=0)
    print(f"ok   {f}: resolved ({len(res.splitlines())} lines, widest {width} columns)")
for f in sorted({c[0] for c in CONFLICTS}):
    left = [l for l in (W / f).read_text().splitlines() if l.startswith(("<<<<<<<", "=======", ">>>>>>>"))]
    if left:
        print(f"FAIL {f}: {len(left)} conflict marker lines left")
        rc = 1
sys.exit(rc)
