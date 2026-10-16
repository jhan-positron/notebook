import json, sys

P = "/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/05daa18d-ed3c-4a33-8e24-e3eab00ce2ea/scratchpad/spec/pr2-4887.json"
d = json.load(open(P))

def word(term):
    for w in d["words"]:
        if w["term"] == term:
            return w
    raise KeyError(term)

def set_word(term, definition):
    word(term)["definition"] = definition

def del_word(term):
    w = word(term)
    d["words"].remove(w)

def diagram(did):
    for g in d["diagrams"]:
        if g["id"] == did:
            return g
    raise KeyError(did)

def section(sid):
    for s in d["change_sections"]:
        if s["id"] == sid:
            return s
    raise KeyError(sid)

# ---- short_version ----
d["short_version"][0] = ("PR 2 (#4887) adds qk_vnni_128x4, an AMX kernel that scores one query group against one dense page "
    "by reading the VNNI-packed K plane of PR 1 in place, and it removes PR 1's temporary gate that kept such pages off "
    "the dense AMX page path.")
d["short_version"][1] = ("The page introduces two data models (the padded query rows and the typed K view the kernel takes) "
    "and one algorithm (the kernel's four-step tile loop), carried by the core diagrams K_VNNI-B2 (the type model) and "
    "KV_CACHE-B3 (the function model) and by the context diagram K_VNNI-B1 (the plane).")

# ---- what_lands ----
assert d["what_lands"][0]["concept"].startswith("Note [QK orientation]")
d["what_lands"][0]["diagrams"] = []
d["what_lands"][0]["where"] = ("h/tron/kernels/amx_attn_iface.hpp:195-229 (the VNNI paragraph at 222-229); "
    "Note [AMX attention dispatch] lines 27-29 and its flow chart line 63")

# ---- walkthrough ----
assert d["walkthrough"][4]["diagram"] == "kv_cache-b3"
d["walkthrough"][4]["say"] = ("Point at the apply_page_tok / apply_dense_amx_page caller row and the qk_vnni_128x4 cell. "
    "Open h/tron/models/self_attention.hpp:1707-1711 (the layout gate picks the packer) and 1781-1787 (it picks "
    "qk_vnni_128x4 with k_packed or qk_rowmajor_128x4 with page::k). At 1904-1910 the temporary gate clause of PR 1 is "
    "gone, and every page the kernel does not take keeps the reader qk_group (1994-1997), as Note [K VNNI storage] items "
    "2 and 3 now say (h/tron/models/kv_cache.hpp:683-694). With the kill switch available() is false (1540) and no query "
    "is packed (1634-1636). Every page of a VNNI slot then takes qk_group. The body's forced run shows that newoff (this "
    "binary with the kill switch) and head (PR 1's binary) score identically at all 256 steps.")
assert d["walkthrough"][7]["say"].startswith("Tests:")
d["walkthrough"][7]["say"] = ("Tests: the identity case in t/t_amx_numerics.cpp:219-279 stores the same K row-major and, "
    "through store_row in scrambled token order (249-252), VNNI-packed, packs the same queries both ways (256-257), runs "
    "both kernels (263-268) and compares the 4 x 64 fp32 scores bit for bit (275). Both kernels add the same four "
    "32-dimension partial products in the same order inside the tile multiply, whichever operand holds K (the case "
    "comment at 221-228). That is why the scores must match bit for bit. The mutation check, the second panel load "
    "changed from block 1 to block 2, fails at line 275. The dispatch test counts one pack, one QK and one PV call for a "
    "full page under either layout and checks that the packer of the build's layout ran (t/t_amx_dispatch_dtype.cpp:171, 196).")
assert d["walkthrough"][8]["say"].startswith("Close with")
d["walkthrough"][8]["say"] = ("Close with the numbers of the PR body: decode throughput against main rises by 5.4 % at "
    "prompt 1,024 tokens and by 9.5 % at prompt 8,192 tokens (qwen3-4b, 8 users). That recovers the loss PR 1 showed. "
    "TTFT against main is +3.2 % at prompt 1,024 tokens (inside the band) and -1.0 % at prompt 8,192 tokens (beyond the "
    "band, an improvement). The PR body does not isolate the per-row store's TTFT cost, and PR 3 (#4898) replaces the "
    "per-row store with the shared block save. The option stays off in every build preset until PR 4.")

# ---- diagrams ----
g = diagram("k_vnni-b5")
g["why"] = ("The kernel runs on the attention workers and only reads, on the same lane and through the same plane route "
    "as the reader qk_group. This PR changes no thread rule, so the diagram is context. The qk_vnni_128x4 arm of the "
    "attention-worker box is new here, and KV_CACHE-B3 carries the kernel as a core cell.")
assert g["not_yet"][1]["lands_in"] == "PR-4 (#4901)"
g["not_yet"][1]["what"] = ("note_k_row_saved -> pending_k_blocks_, convert_pending_k_blocks -> k_block_to_vnni_at -> "
    "block_to_vnni, row_major_row -> dotter, k_row_if_row_major, k_forget_row -> block_to_rows, and the thread rules R2 "
    "to R7 and the store_row_major half of R1 (R1's store_row half is PR 1 text at h/tron/tensor/k_vnni.hpp:286-288 of "
    "this PR's head, and the window that R5 describes is PR 3's)")

g = diagram("kv_cache-b5")
g["why"] = ("The lanes draw the shared save window, the join, the forward-end conversion and the tree work, none of "
    "which is in this PR. The one box this PR touches is 'attention jobs read k_vnni_blocks / k_packed after the latch'.")

g = diagram("k_vnni-b1")
g["why"] = ("This PR adds no box of the plane. The kernel is the first reader that consumes a panel as what it is, one "
    "AMX B tile. Show it first: every tile load of the kernel is one panel (s, c) of this diagram.")

g = diagram("kv_cache-b2")
g["in_this_pr"][0] = ("No box changes. At this PR no block of a VNNI slot is row-major. The kernel therefore reads the "
    "four panels of every block with no block-bit test [src/tron/kernels/amx_attn.cpp:277-295].")

g = diagram("k_vnni-b2")
g["in_this_pr"][1] = ("The kernel's K argument is k_vnni_view<const bf16, 64, 128>, the type page::k_packed returns. A "
    "native K view, a V view or a bare pointer is therefore rejected at compile time "
    "[h/tron/kernels/amx_attn_iface.hpp:265; h/tron/models/kv_cache.hpp:1997; t/t_llama_unit.cpp:103-106, 428-434].")

g = diagram("k_vnni-b3")
assert g["not_yet"][1]["lands_in"] == "PR-4 (#4901)"
g["not_yet"][1]["what"] = ("note_k_row_saved, k_layout_dense, block_bit, offset_bit, page::k_row_if_row_major, "
    "row_major_row, store_row_major, load_row_major, page::k_block_to_vnni_at, convert_pending_k_blocks, "
    "page::k_forget_row (called by clear_kv_complete_at), block_to_vnni, block_to_rows")

# ---- change_sections ----
section("K2")["note"] = ("The gate itself is PR 1. This PR adds two of its consumers in self_attention.hpp, the packer "
    "choice [1707-1711] and the kernel choice [1781-1787], and removes its clause from the dense-page gate [1904-1905]. "
    "save_k_impl's own branch on the gate is PR 1 code [h/tron/models/model.hpp:3103 at the PR-2 head]. The consumers "
    "k_store_shared and store_k_block land in PR 3, and the row-recording consumer and the k_layout_dense gate land in PR 4.")
section("M4")["note"] = ("store_k_block lands in PR 3 (#4898). At PR 3 a run of one token takes set_k_row and a run of 2 "
    "to 16 tokens takes set_k_block with a 16-bit present mask. PR 4 removes the mask from set_k_block and sends every "
    "run shorter than 16 tokens to the per-row store into the row-major tail block. At this PR save_k_impl stores every "
    "row with set_k_row inside its per-token loop [h/tron/models/model.hpp:3103-3119].")
section("K0")["note"] = ("PR 1 added the header comment. This PR changes two of its paragraphs: the file list now names "
    "the AMX QK kernel, and the rule on who may compute an address inside the VNNI-packed plane now names the two score "
    "kernels [h/tron/tensor/k_vnni.hpp:6-8, 32-35].")

# ---- words: deletions ----
for t in ["sliding window", "startOperand / K channel", "TDPBF16PS"]:
    del_word(t)

# ---- words: replacements ----
W = {
 "set_k_block / store_block / store_k_block / transpose_16x16_epi32":
  "PR 3's whole-block store, none of which exists at this PR: store_block transposes the 16 rows of a block in registers (transpose_16x16_epi32) and writes them as 64 whole lines, page::set_k_block calls it for one KV head, and store_k_block in model.hpp stores one work unit of a minibatch. At PR 3 store_block and page::set_k_block take a 16-bit present mask and store a partial block with masked line stores, and PR 4 removes the mask from page::set_k_block and passes the full mask to store_block.",
 "k_vnni_access::plane":
  "detail::k_vnni_access::plane(view), the one route from a VNNI-packed K view to its raw plane address [h/tron/tensor/k_vnni.hpp:212-219]. It is open to the typed operations of the header, the two score kernels (qk_group and, from this PR, qk_vnni_128x4) and the test-only fill.",
 "transfer row (const_k_row_view, k_row_view, k_source_row, k_destination_row)":
  "PR 1's typed view of one token's 128 bf16 values in dimension order with the caller's alignment and DMA (direct memory access) flags, not VNNI-packed storage [h/tron/tensor/k_vnni.hpp:222-231]. k_source_row builds a read-only row and k_destination_row a writable one, and the identity case builds its rows with k_source_row [237-256; t/t_amx_numerics.cpp:252].",
 "V view (v_vnni_tensor)":
  "The owner and the typed view of the VNNI-packed V plane of a kv_block, unchanged by the stack [h/tron/models/kv_cache.hpp:2541, 2546]. The kernel rejects it as its K argument.",
 "bf16 / fp32":
  "bf16 is the 16-bit brain floating-point format of the stored K and V values and of the queries the packers copy. fp32 (32-bit float) is the accumulation format of the score kernels.",
 "forced run":
  "A run that feeds every binary a fixed token sequence through --force-feed-text-token-file, so all binaries score the same context at every step. The PR body uses one to show that this binary with the kill switch and PR 1's binary score identically at all 256 steps.",
 "dense page / dense AMX page path":
  "A dense page is a full 64-token page that the query sees whole and inside its sliding window (the span of past tokens the model attends to), checked by is_dense_amx_page. The dense AMX page path applies such a page with the AMX QK and PV kernels, under the compile-time condition amx_attn_h128g4::eligible and the run-time conditions of a packed query (amx_q_packed != nullptr) and is_dense_amx_page [h/tron/models/self_attention.hpp:1904-1910].",
 "kv_saves_ / mark_k_complete / the per-token marks":
  "kv_saves_ is the page's per-offset, per-slot count of saved K and V (main-branch code) [h/tron/models/kv_cache.hpp:2212-2213]. After all KV heads' rows of a token are stored, save_k_impl marks the token with mark_k_complete and, under hardware attention, credits the GOF (credit_gof_save), and after the token loop it counts the latch down once per downstream minibatch [h/tron/models/model.hpp:3126, 3130, 3134-3135].",
 "dispatch test (t_amx_dispatch_dtype)":
  "The test that checks routing with stand-in kernels that count their calls instead of running AMX. In this PR the fakes of both packers and both QK kernels count into one probe, the VNNI packer's fake also counts into its own counter (rows_pack_calls), and the test checks that the packer of the build's layout ran [t/t_amx_dispatch_dtype.cpp:63, 171, 196, 260-274].",
 "A operand / B operand":
  "The first and the second matrix of one AMX tile multiply: the multiply accepts a row-major matrix only as A and needs the VNNI layout for B. For qk_vnni_128x4 the padded query rows are A and the 16 K panels of the page are B, and for qk_rowmajor_128x4 the native K page is A and the VNNI-packed queries are B.",
 "accumulator tiles":
  "Tile registers 0 to 3 of the AMX kernels, into which the tile multiply adds its products, so they hold the running sums. In qk_vnni_128x4 accumulator tile b holds the scores of token block b.",
 "attention workers":
  "The threads that run the attention kernels of a layer, which read a page only after every minibatch that writes it counted the latch down and never write K. The kernel of this PR runs on them.",
 "AVX-512":
  "Advanced Vector Extensions, the CPU's 512-bit vector instruction set, with 16 lanes of 32 bits per register. The reader qk_group is AVX-512 code with one token per lane.",
 "block (16-token block, token block c)":
  "16 consecutive tokens of a page, page offsets 16 c to 16 c + 15, c = 0 to 3 (k_vnni::BLOCK_TOKENS_16, TOKEN_BLOCKS_4), whose bytes are its 4 panels (one per dimension step, 4 KiB in all). In this PR every block of a VNNI slot holds the VNNI form.",
 "copy_from / copy_storage_slot / copy_token":
  "copy_from copies a token range of every slot from another page (main-branch code) [h/tron/models/kv_cache.hpp:2322], and copy_storage_slot does it for one storage slot. PR 1 made a whole-page copy one owner assignment and a smaller range a token-by-token copy_token (load_row then store_row) [h/tron/models/kv_cache.hpp:2280, 2296, 2298-2301; h/tron/tensor/k_vnni.hpp:334-341].",
 "decode / prefill":
  "Prefill is the phase that scores the prompt tokens of a request, and its wall time is the TTFT. Decode is the generation phase where every step saves one token per user, and its rate is the TPS.",
 "dimension step (s) / pair (dp)":
  "A dimension step is 32 dimensions = 16 dimension pairs (k_vnni::STEP_DIMS_32, STEP_PAIRS_16), the depth of one AMX tile multiply, so a 128-dimension head has 4 steps. A pair is two adjacent dimensions of one token stored in one 32-bit dword.",
 "dotter":
  "The per-token dot-product loop of self_attention.hpp (struct dotter in h/tron/kernels/dotter.hpp), which scores row-major K one token per call. In this PR it is compiled only for row-major slots (PR 4 lets it score the rows of a row-major tail block).",
 "EAGLE storage":
  "The extra physical slot of a book for the EAGLE speculation model (main-branch code). PR 4 gives it its own entry in the page's K-state arrays.",
 "forward end":
  "The end of one forward pass on the main thread, after run() joined the workers and wait_for_coop_gof returned [h/tron/models/model.hpp:1834, 1838]. Nothing runs there in this PR, and PR 4 converts the queued blocks there.",
 "FPGA / hardware attention":
  "The FPGA (field-programmable gate array) is the card that scores attention in hardware, and cached_operation_uses_hw says once per model whether an operation's K is scored there [h/tron/models/model.hpp:1529]. This PR has no hardware-attention policy (PR 4 keeps the blocks of such operations row-major).",
 "GOF staging gather (gof::populate, k_head_fn, help_drain_gof, wait_for_coop_gof)":
  "A GOF is a group of four tokens of K/V data that gof::populate copies into a buffer for the FPGA [src/tron/gof.cpp:188], and page_info::k_head_fn returns one token's K row for it, since PR 1 through page::get_k_row from a VNNI plane [h/tron/scheduler/full.hpp:2747-2759]. Idle attention workers run the staging through help_drain_gof and the main thread drains the rest in wait_for_coop_gof [h/tron/models/model.hpp:3239, 3252].",
 "identity case":
  "The case \"AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K\" of t_amx_numerics, which returns early with a warning without AMX hardware [t/t_amx_numerics.cpp:219-279]. It stores the same K row-major and, through store_row in scrambled token order, VNNI-packed, packs the same queries both ways, runs both kernels on real AMX and compares the 4 x 64 fp32 scores bit for bit for 2 seeds.",
 "k_vnni_tensor / k_vnni_view / k_vnni_element":
  "k_vnni_tensor<64, 128> owns one 16 KiB VNNI-packed K plane as a 64-byte-aligned bf16 array, and its as_view() is the only source of a view [h/tron/tensor/k_vnni.hpp:183-204]. k_vnni_view<T, 64, 128> (T = bf16 or const bf16, the concept k_vnni_element) is the only way to name a plane, and a writable view converts to a read-only one, never back [127, 137-172].",
 "KV head / kv_mul / query group":
  "A KV head is one key/value head of grouped-query attention, and kv_mul is the number of query heads per KV head (4 for qwen3-4b and llama-3.1-8b). A query group is the kv_mul query heads that share one KV head, and the AMX kernels take groups of 4.",
 "kv_block / KV_BLOCK_PLANES_2":
  "The struct holding the two planes K and V of one (storage slot, KV head, page), KV_BLOCK_PLANES_2 being the plane count [h/tron/models/kv_cache.hpp:2519, 717]. PR 1 made its member k the typed owner k_vnni_tensor for a VNNI slot (k_storage) [2526-2536].",
 "main thread / main helpers / run() / run_main_help / TronCpp.hs":
  "The main thread runs the generated plugin's run(), which calls save_k, and the main helpers are its helper threads, which run the generated run_main_help [ingest/src/TronCpp.hs:1364, 1420, 2918-2921]. TronCpp.hs is the Haskell generator of the plugins (PR 3 makes run_main_help call save_k with the helper's worker_ix).",
 "Note [QK orientation]":
  "The comment block in h/tron/kernels/amx_attn_iface.hpp (lines 195-229) that explains the flipped operand roles: the row-major kernel computes S^T = K x Q^T and transposes in registers, and with VNNI-packed K the kernel computes S = Q x K^T with no transpose. This PR adds its VNNI paragraph [222-229].",
 "panel":
  "The 1 KiB part of a K plane for one 32-dimension step s and one 16-token block c: 16 pair rows of 64 bytes, at index s * 4 + c, 16 per plane [h/tron/tensor/k_vnni.hpp:25-27, 75-79]. A panel is exactly one AMX B tile, which the kernel's static_asserts check [src/tron/kernels/amx_attn.cpp:257-267].",
 "PR":
  "A pull request of the tron repository: PR 1 is #4868, PR 2 (this page) is #4887, PR 3 is #4898 and PR 4 is #4901. Each is based on the previous one, and all four replace PR #4424.",
 "QK / PV":
  "QK is the score step of attention, S = Q x K^T, done for one dense page by qk_rowmajor_128x4 or qk_vnni_128x4. PV is the weights-times-values step, O = P x V, where P is the exponentiated scores, done by weights_times_v_128x4 [h/tron/kernels/amx_attn_iface.hpp:270-281].",
 "slot / kv_slot_id / storage slot (kv_storage_offset)":
  "A slot is one persistent K/V storage region of a book, selected by kv_slot_id [h/tron/attention_ids.hpp:23], and a storage slot (kv_storage_offset) is the absolute offset of such a region in the book's physical allocation [h/tron/models/common.hpp:240]. A VNNI-packed slot is one whose K uses the VNNI layout.",
 "TPS / TTFT":
  "TPS is tokens per second (the decode throughput) and TTFT is the time to first token (the prefill wall time). The PR body's decision band is twice the larger sample standard deviation over 3 repetitions, never smaller than 0.4 TPS or 0.15 s.",
 "VNNI layout / VNNI-packed":
  "VNNI (Vector Neural Network Instructions) names the B-operand layout of the AMX tile multiply, in which two consecutive dimensions of one token are adjacent in memory and one 64-byte line holds that dimension pair for 16 consecutive tokens. VNNI-packed means stored in this layout.",
 "per-row store (store_row, load_row, set_k_row, get_k_row, pair_base, pair_row_offsets)":
  "PR 1's way of writing one token's 128-dimension row into the VNNI plane: store_row issues 4 scatters of 16 dwords, one per dimension step, into the token's column of its block's 4 panels, load_row is the inverse gather, and pair_base and pair_row_offsets are their address helpers [h/tron/tensor/k_vnni.hpp:264-283, 294-306, 313-325]. page::set_k_row and page::get_k_row call them for a VNNI slot and memcpy for a row-major slot, and in this PR save_k stores every row this way [h/tron/models/kv_cache.hpp:2010-2040; h/tron/models/model.hpp:3113, 3118].",
 "packers (pack_q_group_128x4, pack_q_rows_128x4) / query pack / query-pack slot (amx_qpack_slot)":
  "The packers prepare the queries of one group: pack_q_group_128x4 (main branch) packs the 4 rows into the VNNI layout as the B operand of the row-major kernel, and pack_q_rows_128x4 (this PR) copies the 4 rows as stored into rows 0 to 3 of a 16-row A operand [src/tron/kernels/amx_attn.cpp:136, 225-229]. A query pack is one packer call for one query token, into a query-pack slot, one 4,096-byte buffer per query token that serves either packer [h/tron/models/self_attention.hpp:256-263, 1690-1713].",
 "save_k / save_k_impl / save_v":
  "save_k (two overloads) stores the K rows of one minibatch for one layer and calls save_k_impl, which at this PR stores every row on the main thread inside its per-token loop, with set_k_row for a VNNI slot and page::k(...).set for a row-major slot [h/tron/models/model.hpp:3077, 3091-3135, 3139, 3147]. save_v_impl and the two save_v overloads are the V counterpart [3155, 3204, 3212].",
 "native K view (page::k, kv_block::k_view, k_at, const_native_k_view)":
  "The row-major views of a K plane: page::k returns the kv_block's k_view, a [token][element] view, and k_at(i_page) one token's row, all constrained by PR 1 to row-major slots [h/tron/models/kv_cache.hpp:1923-1984, 2554-2572]. const_native_k_view is the argument type of qk_rowmajor_128x4.",
 "row-major tail block (row_major_row, store_row_major, load_row_major, k_row_if_row_major)":
  "PR 4's form of an incomplete 16-token block of a VNNI slot, none of which exists at this PR: token t owns 256 contiguous bytes until all 16 rows are saved, then the block is converted in place. row_major_row addresses such a row, store_row_major and load_row_major copy it, and page::k_row_if_row_major hands it to the FPGA staging.",
 "fill_storage_slot / fill_random":
  "book::fill_random is the test-only fill of every kv_block with random bf16 values, and fill_storage_slot is its body for one storage slot. PR 1 made it reach a VNNI plane through k_vnni_access::plane, the one documented exception to the typed access rule [h/tron/models/kv_cache.hpp:1290, 1715, 1721].",
 "clear_kv_complete_at / k_forget_row":
  "clear_kv_complete_at is the main-branch page function that resets a page offset when a new token takes it, and k_forget_row is PR 4's addition that drops the K bits of that offset and above [h/tron/models/kv_cache.hpp:2185]. Both run between forward passes under the tree lock.",
 "minibatch / batch / items / token_jobs_do_kv / K buffer ks":
  "A minibatch (struct batch) is one chunk of a forward pass's token jobs, its items, and token_jobs_do_kv says per job whether it needs KV work [h/tron/models/common.hpp:991, 1083; h/tron/models/model.hpp:1158]. ks is the K buffer of one layer that save_k reads [3079].",
 "scores S / s_pages / Q / K":
  "Q is the query matrix, K the key matrix and S = Q x K^T the score matrix of one query group against the tokens of one page. The AMX kernels write the raw, unscaled scores into s_pages[head][token], 4 rows of 64 fp32, the array the software loop also fills [h/tron/models/self_attention.hpp:1774-1787].",
 "t_k_vnni_layout (the layout test)":
  "PR 1's unit test of the VNNI K layout, 4 cases [t/t_k_vnni_layout.cpp]. Its copy_token call is at line 189.",
}
for t, defn in W.items():
    set_word(t, defn)

json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
open(P, "a").write("\n")
print("written", len(d["words"]), "words")
