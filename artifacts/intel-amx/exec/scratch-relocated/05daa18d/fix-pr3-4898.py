import json, sys

P = "/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/05daa18d-ed3c-4a33-8e24-e3eab00ce2ea/scratchpad/spec/pr3-4898.json"
d = json.load(open(P))

# ---------- short version ----------
d["short_version"][1] = (
    "The page introduces the two data models (the K store window batch::k_store_window_t and the work unit), "
    "the three algorithms (the register transpose of store_block, the run cut k_store_cut_units and the per-run store store_k_block), "
    "the two policies (the sharing decision k_store_shared and the partial-block path) and the two protocols "
    "(the open / claim / join window of save_k_impl with its watchdog, and the save_k entry points with their generated call sites) "
    "that the PR adds, carried by K_VNNI-B3, KV_CACHE-B2 and MODEL-B1 to MODEL-B5."
)
d["short_version"][2] = (
    "For each diagram the page says which boxes land in this PR, which were there already (from main, PR #4868 or PR #4887), "
    "and which land only in PR #4901 (the saved-row bits, the row-major tail block and the forward-end conversion)."
)

# ---------- words ----------
W = {w["term"]: w for w in d["words"]}

def setdef(term, definition):
    assert term in W, term
    W[term]["definition"] = definition

def rename(old, new, definition):
    assert old in W, old
    W[old]["term"] = new
    W[old]["definition"] = definition

setdef("acquire / release / acq_rel / relaxed (memory orders)",
    "C++ std::memory_order values. A release write publishes every earlier write of its thread to a thread whose acquire read sees the stored value, acq_rel does both, and relaxed orders nothing beyond the atomic itself.")
setdef("AMX",
    "Intel Advanced Matrix Extensions, the tile instruction set of the CPU. The AMX kernel qk_vnni_128x4 reads a page's VNNI-packed K plane as its B operand (the second matrix of the tile multiply), and this PR adds no AMX instruction.")
setdef("apply_page_tok / apply_dense_amx_page",
    "The attention workers' per-page scoring routines of self_attention.hpp. apply_dense_amx_page runs the AMX kernel on a full page [1749, 1782], and apply_page_tok runs the software readers (qk_group for a VNNI slot [1856, 1994]) and calls apply_dense_amx_page at 1909.")
setdef("attention workers",
    "The threads that run the attention kernels of a layer. Their pending sections (the attention work that waits for a page's latch) wait behind save_k, and they read a page only after every minibatch that writes it counted the latch down [model.hpp:3088].")
setdef("AVX-512",
    "The CPU's 512-bit vector instruction set, with 16 lanes of 32 bits per register. The loads, the transpose and the stores of store_block, and the reader qk_group, are AVX-512 code.")
setdef("base diagram",
    "One of the 16 drawings of the three PR 4424 source pages (data, type, function, sequencing, interaction and decision models), copied unchanged with line numbers that cite PR 4424 head 9d5c7a389b, not this PR's head. This page says what of each lands in this PR.")
setdef("block (16-token block), k_store_block",
    "16 consecutive page offsets of one page (offsets 16 c to 16 c + 15 for block c): one AMX tile width and the unit of the block save. k_store_block is model.hpp's name for the constant [model.hpp:3142].")
setdef("block save (store_block, page::set_k_block)",
    "The store of the K rows of up to 16 tokens of one block as whole 64-byte lines after a register transpose. page::set_k_block is the page entry point and store_block the operation [kv_cache.hpp:2042-2049; tensor/k_vnni.hpp:381-406], and its result is bit-identical to the per-row store per present token.")
setdef("critical path",
    "Main's serial part of a layer, the time that no other thread shortens (the thick red frame of MODEL-B4). The Note calls the per-row store the main thread's largest serial piece of work in a prefill layer [model.hpp:3083-3084].")
setdef("decode / prefill",
    "Prefill processes the prompt (many tokens per user per pass), and decode generates one token per user per step (one item per user per pass). The PR body's decode cells run 8 users, 8 items per decode pass, below the sharing threshold of 16 items [model.hpp:3160-3162].")
setdef("dimension step (s)",
    "32 dimensions = 16 dimension pairs, 4 steps per 128-dimension head. store_block runs its transpose once per step.")
setdef("EAGLE",
    "A speculation model whose KV storage has its own extra physical slot in the book. The names book::eagle_view_active and EAGLE_STORAGE_SLOTS_1 in the later-PR lists are PR #4901's, and this PR changes nothing of EAGLE.")
setdef("FPGA / hardware attention",
    "FPGA = field-programmable gate array, the accelerator card, and hardware attention is attention scored on it. The policy for blocks under hardware attention is PR #4901's.")
setdef("generated plugin / handwritten plugin",
    "A generated plugin is the model code that the code generator ingest/src/TronCpp.hs emits, with a main thread that runs run() and helpers that run run_main_help. Handwritten plugins (h/tron/plugins/llama.hpp:1038-1039) and the unit tests call save_k with the default worker arguments (0 and 1) and never share [model.hpp:3102-3104], except the three-thread section of the save_k case (t/t_llama_unit.cpp:3988-4108), which passes worker_ix and n_workers = 3.")
setdef("join / join watchdog",
    "The join is main's wait until every helper has incremented finished. The watchdog reads the clock once every k_join_clock_spins = 1,048,576 _mm_pause loops (_mm_pause is a CPU hint instruction that slows a polling loop and saves power) and aborts k_join_timeout_s = 120 s after the first clock read, with the finished-helper and claimed-unit counts in the message [model.hpp:3145-3151, 3354-3368].")
setdef("K / K row / K buffer (ks)",
    "K is the key matrix of attention, and a K row is one token's 128 bf16 values for one KV head in dimension order. ks is the K buffer of the minibatch that save_k reads (its tron record label is 'WK roped').")
setdef("KV page / page / page offset",
    "A page holds 64 contiguous tokens of K and V per storage slot and KV head, and a page offset is a token's position inside its page (0 to 63). Block c of a page is offsets 16 c to 16 c + 15.")
setdef("load_row / copy_token / page::k_packed",
    "load_row is the inverse of store_row (4 gathers that read one token's row out of a plane [tensor/k_vnni.hpp:351]), and copy_token copies one token between planes through load_row and store_row [415]. page::k_packed is the read-only view of a plane that the two score kernels take [kv_cache.hpp:2005-2009].")
setdef("main thread / main helpers / worker_ix / n_workers / run_main_help",
    "The main thread runs the schedule of a generated plugin, and the main helpers run its per-token kernels through run_main_help. worker_ix is 0 for main and 1 to n_workers - 1 for the helpers, and n_workers = 1 + the number of main helpers [TronCpp.hs:1392, 1363-1365].")
setdef("minibatch / batch / items / token job / token_jobs_do_kv",
    "A minibatch (struct batch) is one chunk of the pass's token jobs that run together, listed in order in q_batch->items. token_jobs_do_kv says whether a job writes KV.")
rename("Note [name]", "Note [Shared block save] / Note [K VNNI storage] (a Note)",
    "A Note is a named comment block in the tron source. Note [Shared block save] (model.hpp:3078-3139) is this PR's design record, and Note [K VNNI storage] (kv_cache.hpp:651) says who writes and reads the VNNI-packed layout.")
setdef("option, the (TRON_K_VNNI)",
    "The CMake option, default OFF, which when on selects VNNI-packed K storage for every 128-dimension head. It stays off in every preset until PR #4901.")
setdef("page copies, clears and the staging callback (book::append, copy_from, copy_storage_slot, clear_kv_complete_at, fill_storage_slot, k_head_fn)",
    "book::append copies a page's slots between books through page::copy_from and copy_storage_slot [kv_cache.hpp:1254, 1282, 2350, 2308], clear_kv_complete_at clears a page offset's completion state when a new token takes the offset [2213], and book::fill_storage_slot fills a storage slot with values from a random distribution [1722-1723]. page_info::k_head_fn is the staging gather's callback that reads one K row through get_k_row [full.hpp:2747, 2759].")
setdef("panel",
    "One 1 KiB tile of a plane for one dimension step s and one token block c (16 pair rows of 64 bytes), which is one AMX B tile. store_block fills one panel per (step, block) with 16 line stores.")
setdef("present mask / FULL_BLOCK_0XFFFF / masked store / k_scatter_run_len",
    "The present mask is the 16-bit lane mask of the block's tokens that the run holds (FULL_BLOCK_0XFFFF is the all-present value), a partial block uses line stores masked to the present lanes, and k_scatter_run_len = 1 is the run length that takes the per-row store instead [tensor/k_vnni.hpp:80-81, 396-406; model.hpp:3144, 3263]. PR #4901 removes the mask parameter from set_k_block and the constant k_scatter_run_len, and keeps FULL_BLOCK_0XFFFF as the value set_k_block passes to store_block.")
setdef("rope / K channel / startOperand",
    "rope is the rotary position embedding applied to the Q and K rows before the store, and nothing blocks between a helper's rope kernel and its save_k call [model.hpp:3135-3136]. The K channel is the buffer whose readiness main waits for before save_k (startOperand in the generated run(), TronCpp.hs:2937; main renamed it startReadingAll in commit d3e4297df6, after the stack's base 72308ec90c).")
setdef("row-major / row-major tail block",
    "Row-major is the layout with one contiguous 256-byte row per token. The row-major tail block of PR #4901 keeps a block row-major until its 16th row is saved, and at this PR's head no block is row-major in a VNNI slot.")
setdef("run (of tokens)",
    "Consecutive items of the minibatch that fall in the same 16-token block of the same page, with no page offset repeated. store_k_block collects one run at a time [model.hpp:3240-3262].")
setdef("save_k / save_k_impl / store_k_block / k_store_shared / k_store_cut_units",
    "save_k (two overloads) is the entry point that stores the K rows of one minibatch, and save_k_impl runs the window protocol. k_store_shared decides the sharing, k_store_cut_units cuts the items into work units, and store_k_block stores the runs of one unit [model.hpp:3398-3416, 3304, 3156, 3168, 3204].")
rename("saved-row bits and the forward-end conversion (PR #4901 names)", "saved-row bits / forward-end conversion (PR #4901 names)",
    "note_k_row_saved and note_k_block_saved publish the page bits k_rows_saved_ (one per page offset) and k_vnni_blocks_ (one per block), and convert_pending_k_blocks converts the blocks listed in pending_k_blocks_ at the forward end through k_block_to_vnni_at and block_to_vnni. None of these names, nor the row-major readers and clears block_to_rows, row_major_row, k_row_if_row_major and k_forget_row, exists at this PR's head.")
setdef("spin / spin-wait",
    "A loop that re-reads a variable until it changes, instead of sleeping. The helper's wait for opened and main's join on finished are spins [model.hpp:3339-3341, 3356-3368].")
setdef("VNNI / VNNI-packed",
    "VNNI = Vector Neural Network Instructions, and VNNI-packed means stored in the VNNI layout. That layout is the right-operand format of the AMX tile multiply: two consecutive dimensions of one token are adjacent in memory, and one 64-byte line holds that dimension pair for 16 consecutive tokens.")
setdef("window (k_store_window_t) / work unit / the counters",
    "The window is the per-minibatch record of one shared K store [common.hpp:1170-1193], with the unit table unit_start (unit u = items[unit_start[u], unit_start[u + 1])) and n_units, the claim counter next_unit, opened (windows opened in this pass), finished (helpers done with the open window), and helper_windows (the windows each helper has entered, by worker_ix). A work unit is a run of consecutive items in one 16-token block of one page with the same token_jobs_do_kv value.")

def insert_after(term_before, entry):
    idx = [i for i, w in enumerate(d["words"]) if w["term"] == term_before]
    assert len(idx) == 1, term_before
    d["words"].insert(idx[0] + 1, entry)

insert_after("spin / spin-wait", {
    "term": "split plan / U2.1",
    "definition": "split-plan-3.1.md, the plan that assigned the changes of PR 4424 to the four PRs. Its item U2.1 keeps the masked partial-block path in this PR and lets PR #4901 delete it."})
insert_after("Granite Rapids test machine", {
    "term": "hits.txt / files-4901.txt (evidence files)",
    "definition": "Working files of the page's verification. hits.txt counts, for each identifier of a diagram box, its occurrences in main's tree and in the added lines of each of the four PR diffs, and files-4901.txt lists the files PR #4901 touches."})

# ---------- what_lands ----------
wl = d["what_lands"]
assert wl[0]["concept"].startswith("The block save")
wl[0]["where"] = "h/tron/tensor/k_vnni.hpp:80-83, 91, 95-96 (FULL_BLOCK_0XFFFF, LANES_16 and their static_asserts), 294-320 (the transpose), 365-406 (store_block); h/tron/models/kv_cache.hpp:2031-2049 (set_k_block), 666-667 and 678-690 (Note [K VNNI storage] item 1)"
wl[0]["diagrams"] = ["k_vnni-b3", "kv_cache-b2", "k_vnni-b1a"]
assert wl[6]["concept"].startswith("The window protocol")
assert "3299-3389" in wl[6]["where"]

# ---------- diagrams ----------
D = {x["id"]: x for x in d["diagrams"]}

D["k_vnni-b3"]["in_this_pr"][0] = "store_block (the whole-block group): h/tron/tensor/k_vnni.hpp:365-406 (comment 365-378, function 379-406)"

a = D["kv_cache-b2"]["already_there"][0]["what"]
assert "65-78" in a
D["kv_cache-b2"]["already_there"][0]["what"] = a.replace("65-78", "65-79")

a = D["k_vnni-b1"]["already_there"][2]["what"]
assert "21-30, 56-78" in a
D["k_vnni-b1"]["already_there"][2]["what"] = a.replace("21-30, 56-78", "22-30, 58-79")

a = D["k_vnni-b1"]["not_yet"][0]["what"]
assert "kv_cache.hpp:2509 of PR 4424" in a
D["k_vnni-b1"]["not_yet"][0]["what"] = a.replace("kv_cache.hpp:2509 of PR 4424", "kv_cache.hpp:2508 of PR 4424")

a = D["model-b3"]["in_this_pr"][9]
assert a.startswith("the counters column"), a
D["model-b3"]["in_this_pr"][9] = "the counters column: unit_start, n_units (common.hpp:1189, 1180), opened (1178), next_unit (1176), finished (1179)"

a = D["model-b4"]["already_there"][1]["what"]
assert a.startswith("startOperand"), a
D["model-b4"]["already_there"][1]["what"] = "startOperand (the K channel wait before save_k, TronCpp.hs:2937; named startReadingAll on main since d3e4297df6, after the stack's base 72308ec90c), save_v (TronCpp.hs:2945-2949), the K/Q rope kernel"

D["kv_cache-b4"]["why"] = "The five states of a block are defined by the page's saved-row and converted-block bits. Those bits do not exist at this PR's head. Every row a VNNI slot stores is VNNI-packed at once. So a block has no layout state. The arc over the top is this PR's: set_k_block per KV head, called from any thread of the shared window. note_k_block_saved and the states the arc connects are PR #4901's."

# evidence ids in uppercase
for did, old, new in [
    ("k_vnni-b1", "hits.txt k_vnni-b1:", "hits.txt K_VNNI-B1:"),
    ("k_vnni-b1a", "hits.txt k_vnni-b1a:", "hits.txt K_VNNI-B1A:"),
    ("k_vnni-b5", "hits.txt k_vnni-b5:", "hits.txt K_VNNI-B5:"),
    ("kv_cache-b5", "hits.txt kv_cache-b5:", "hits.txt KV_CACHE-B5:"),
    ("kv_cache-b4", "kv_cache-b4 arc label:", "KV_CACHE-B4 arc label:"),
]:
    ev = D[did]["evidence"]
    hits = [i for i, e in enumerate(ev) if old in e]
    assert len(hits) == 1, (did, old)
    ev[hits[0]] = ev[hits[0]].replace(old, new)

# order: kv_cache-b3, kv_cache-b4, kv_cache-b5
ids = [x["id"] for x in d["diagrams"]]
i5, i4 = ids.index("kv_cache-b5"), ids.index("kv_cache-b4")
assert i5 < i4 and i4 == i5 + 1
d["diagrams"][i5], d["diagrams"][i4] = d["diagrams"][i4], d["diagrams"][i5]

# ---------- change sections ----------
C = {c["id"]: c for c in d["change_sections"]}
notes = {
    "C0": "This PR rewrites consumer item 1 of Note [K VNNI storage] for the two store paths and the sharing (kv_cache.hpp:678-690) and adds store_block to the typed-operations list (666-667). The Note itself came with PR-1. Note [Row-major blocks under hardware attention] and the row-major-tail text land in PR-4.",
    "C1": "kv_block::k as the typed owner k_vnni_tensor landed in PR-1 (kv_cache.hpp:2554-2564 at this head). This PR does not touch it.",
    "C4": "The row-major constraint on page::k and k_packed landed in PR-1 (kv_cache.hpp:1928-1957, 2005-2009). k_vnni_blocks lands in PR-4.",
    "C5": "note_k_row_saved and note_k_block_saved land in PR-4. At this head set_k_block sets no bit (kv_cache.hpp:2042-2049).",
    "C7": "set_k_row and get_k_row landed in PR-1 without the block-bit branch (kv_cache.hpp:2018-2029, 2056-2067). The branch and k_row_if_row_major land in PR-4.",
    "C8": "page::set_k_block lands here (kv_cache.hpp:2031-2049) with a __mmask16 present parameter and the bit-identity contract. PR-4 removes the mask parameter (diff-4901 line 504) and makes store_k_block pass only full blocks.",
    "C10": "The VNNI branch of copy_storage_slot (one owner assignment per KV head) landed in PR-1 (kv_cache.hpp:2314-2330, inside copy_storage_slot 2308-2347). The k_storage_ref parameter and the bit carry land in PR-4.",
    "K0": "This PR adds store_block to the header comment's operation lists (tensor/k_vnni.hpp:6, 37). The rest of the header is PR-1's, and the Note [Row-major tail block] paragraph is PR-4's.",
    "K1": "FULL_BLOCK_0XFFFF and LANES_16 with their static_asserts land here (tensor/k_vnni.hpp:80-83, 91, 95-96). The other constants and index landed in PR-1, and block_bit, offset_bit, BLOCKS_PER_PAGE_MASK_0XF and PANEL_ROWS_4 land in PR-4.",
    "K2": "The gate layout_on landed in PR-1 (tensor/k_vnni.hpp:105-108). This PR adds two of the consumers the section lists, k_store_shared and store_k_block (model.hpp:3157, 3214), without touching the gate.",
    "K3": "The owner, the views and the access route landed in PR-1. This PR changes only the two view comments that name store_block as a writer (tensor/k_vnni.hpp:137, 159).",
    "K4": "The transfer rows and their builders landed in PR-1 (tensor/k_vnni.hpp:234-262). The store_k_block consumer the section lists is this PR's code (model.hpp:3268-3277, 3283-3289), moved from PR-1's save_k_impl.",
    "K5": "transpose_16x16_epi32 lands here (tensor/k_vnni.hpp:290-320). pair_base and pair_row_offsets landed in PR-1 (270-283).",
    "K6": "store_row, load_row and copy_token landed in PR-1. This PR adds the thread rule to store_row's comment (tensor/k_vnni.hpp:323-329: several threads may store different tokens of one plane at the same time).",
    "K7": "store_block lands here in full (tensor/k_vnni.hpp:365-406), including the masked branch for a partial block. PR-4 does not edit the function (its k_vnni.hpp hunks are the header, the constants and the code appended after copy_token).",
    "M0": "Note [Shared block save] lands here (model.hpp:3078-3139: the measurement, the two remedies, the window protocol, the deadlock argument, the watchdog). PR-4 rewrites remedy 1's paragraph to the whole-block-only form with the row-major tail block (diff-4901 model.hpp @@ -3088,10 +3095,17 @@).",
    "M1": "k_store_block lands here (model.hpp:3141-3142). pending_k_block, pending_k_blocks_, convert_pending_k_blocks and the run_forward call land in PR-4.",
    "M4": "store_k_block lands here (model.hpp:3196-3296) with the test n == k_scatter_run_len (a one-token run takes set_k_row, 2 to 16 tokens take set_k_block with the present mask). PR-4 changes the test to n < k_store_block, adds the FULL_BLOCK_0XFFFF assert and note_k_block_saved after the last KV head (diff-4901 lines 916-941).",
    "M5": "save_k_impl's worker arguments, the early return, the open / claim / join protocol and the watchdog with its constants land here (model.hpp:3145-3151, 3298-3371). PR-4 adds only the recording loop after them (M6).",
    "M6": "The row-recording loop (note_k_row_saved, cached_operation_uses_hw, pending_k_blocks_.push_back) lands in PR-4 (diff-4901 model.hpp @@ -3369,6 +3416,26 @@). At this head the join is followed by the marks loop directly (model.hpp:3372-3388).",
}
for k, v in notes.items():
    assert ";" in C[k]["note"], k
    C[k]["note"] = v

# ---------- walkthrough ----------
wt = d["walkthrough"]
assert wt[1]["diagram"] == "k_vnni-b1"
wt[1]["say"] = "Point at the plane, its 16 panels (s, c), and the pair rows of one panel: one 64-byte line holds one dimension pair for 16 tokens. All of this is the layout PR's. The constants are at tensor/k_vnni.hpp:58-79 and the index map at 113. Say that store_block writes one panel at a time, the four panels (s, c) of one block c. The two state words in the page column and the orange frame (a block that is still row-major) belong to PR #4901."
assert wt[6]["diagram"] == "model-b2"
wt[6]["say"] = "Follow the arrows from the three caller boxes: the generated run() passes 0 and n_workers [TronCpp.hs:2936-2944], run_main_help passes worker_ix and n_workers [2875-2882], and tests and handwritten plugins use the defaults [model.hpp:3400-3401]. save_k_impl [3304] calls k_store_shared [3156], k_store_cut_units [3168] and store_k_block [3204]. store_k_block calls set_k_block [kv_cache.hpp:2042] or set_k_row. The cells note_k_block_saved, note_k_row_saved, k_storage_of, convert_pending_k_blocks and k_block_to_vnni_at, and the use of cached_operation_uses_hw inside save_k_impl, are PR #4901."
assert wt[8]["diagram"] == "model-b4"
wt[8]["say"] = "The red dashed lane is the kernel PR's state: the per-row store inside the marks loop, the 28 lines this PR removes [diff hunk @@ -3095,34; model.hpp:3098-3125 at the PR-2 head 0ee8671d35]. Below it main opens, claims and joins. Helper 1 and helper 2 reach save_k with nothing blocking after their rope kernel, claim beside main, and are idle again until the attention output [Note, model.hpp:3095-3100, 3132-3139]. The deadlock argument is the Note's. Both sides decide with k_store_shared from the same inputs: a VNNI slot, 2 to 128 workers and more than 16 items [3153-3164]. So a helper never waits for a window main does not open. The convert_pending_k_blocks slice at the forward end is PR #4901."
assert wt[9]["diagram"] == "model-b5"
wt[9]["say"] = "Say that the decision differs here from the drawing. At this PR's head the test is n == k_scatter_run_len [model.hpp:3263]: a one-token run takes set_k_row [3264-3278], a run of 2 to 16 tokens takes set_k_block with the present mask [3279-3293], and store_block masks the line stores to the present lanes [tensor/k_vnni.hpp:400-404]. PR #4901 turns the test into 'a run of 16?' and stores a shorter run row by row into the row-major tail block (split plan U2.1; diff of #4901 lines 916-929). The whole right half (note_k_row_saved, the hardware-attention branch, the pending list, the forward-end conversion) is PR #4901."

# ---------- gaps ----------
assert d["gaps"][0].startswith("The partial-block path")
d["gaps"][0] = "The partial-block path of section 1 (k_scatter_run_len = 1, the present mask through page::set_k_block, store_block's masked branch at tensor/k_vnni.hpp:400-404): no base diagram draws it. MODEL-B5 draws the PR #4901 form, in which only a run of 16 takes the block save."
assert d["gaps"][1].startswith("The tests")
d["gaps"][1] = "The tests of section 1 (the block-save case, the one-thread and three-thread sections of the save_k case, the two LoopyTronSpec specs): no base diagram draws them. K_VNNI-B3 draws one test call site, the layout PR's copy_token call at t_k_vnni_layout.cpp:197 of PR 4424."

# ---------- global line-range fixes ----------
GLOBAL = [
    ("381-407", "381-406"),
    ("365-407", "365-406"),
    ("323-330", "323-329"),
    ("3299-3389", "3298-3389"),
    ("3299-3371", "3298-3371"),
    ("2863-2882", "2864-2882"),
    ("2018-2027", "2018-2029"),
    ("2056-2066", "2056-2067"),
    ("3238-3262", "3240-3262"),
]
counts = {o: 0 for o, _ in GLOBAL}

def walk(x):
    if isinstance(x, str):
        for o, n in GLOBAL:
            if o in x:
                counts[o] += x.count(o)
                x = x.replace(o, n)
        return x
    if isinstance(x, list):
        return [walk(v) for v in x]
    if isinstance(x, dict):
        return {k: walk(v) for k, v in x.items()}
    return x

d = walk(d)
print("global replacements:", counts)

# ---------- checks ----------
s = json.dumps(d)
for bad in ["381-407", "365-407", "323-330", "3299-", "2863-2882", "2018-2027", "2056-2066", "3238-3262",
            "402-406", "234-261", "56-78", "65-78", "3354-3367", "3354-3358", "k_vnni.hpp:2509",
            "hits.txt k_vnni", "hits.txt kv_cache", "kv_cache-b4 arc", "inside save_k,"]:
    assert bad not in s, bad
assert len(d["diagrams"]) == 16 and len(d["change_sections"]) == 29 and 2 <= len(d["short_version"]) <= 3
roles = [x["role"] for x in d["diagrams"]]
order = {"core": 0, "context": 1, "not involved": 2}
assert [order[r] for r in roles] == sorted(order[r] for r in roles), roles
assert all(w["kind"] in {"data model", "algorithm", "protocol", "policy", "build and test"} for w in d["what_lands"])
assert all(c["status"] in {"full", "partial", "none"} for c in d["change_sections"])
dids = {x["id"] for x in d["diagrams"]}
assert all(w["diagram"] == "none" or w["diagram"] in dids for w in d["walkthrough"])
assert all(di in dids for w in d["what_lands"] for di in w["diagrams"])
terms = [w["term"] for w in d["words"]]
assert len(terms) == len(set(terms))
# at most two sentences in the shortened definitions is a goal, not asserted; report sentence counts > 2
import re
long_defs = [w["term"] for w in d["words"] if len(re.findall(r"[.!?](?:\s|$)", w["definition"])) > 2]
print("definitions with more than 2 sentences:", long_defs)

json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
open(P, "a").write("\n")
print("written")
