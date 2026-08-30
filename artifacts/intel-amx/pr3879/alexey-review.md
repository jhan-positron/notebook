REVIEW: CHANGES_REQUESTED

Oof, that's a lot of PR.  I got through all of it, but I don't think we should merge it in this shape.  Three things I'd call blockers: (i) `book::mirror()` indexes the arena by logical slot and never looks at the storage view, so with EAGLE the draft's `save_k` overwrites the validator's slot-0 mirror plane (worked through inline in `kv_cache.hpp`); (ii) `t_amx_logit_ab` is registered under the `fpga` label and `REQUIRE`s an env var nobody sets, so the FPGA lane fails the moment CI runs on this; (iii) `doc/intel-amx.md` still has two `xxx:` notes-to-self in it.  Then the process asks.  Per #2000 this is at least four PRs (dispatch + canonical kernels, the mirror arena, the counters, the bench and doc), and the description doesn't mention the doc, the `kv_block_planes` refactor, `v_data`/`v_base`, the `CHUNK_SIZE` `#error`, or the `fill_random` rebuild.  And I'd like a CI run (label `Run CI`) on the default-off build before merge: `apply_page_tok` changed for everyone, and after merge nothing in CI compiles the flagged code at all.  Everything else is inline; most of it is comment accuracy.


doc/intel-amx.md:44 - DONE
Two `xxx:` notes-to-self made it into the committed doc.  Please read it through once before requesting review; I'd rather not review placeholders.


doc/intel-amx.md:89 - DONE
The code doesn't do this.  In a DISPATCH-only build the first `available()` call is on an attention worker (`self_attention.hpp:1360`), i.e. after the pool started; in a K_MIRROR build it's the book constructor on the scheduler thread.  Either this states a real kernel requirement we violate, or (my reading of xstate.rst: the grant is per-process and covers existing threads) the sentence is false.  Fix one or the other.


doc/intel-amx.md:103 - DONE
Archived where?  A number a reader cannot check should get a pointer or go.


doc/intel-amx.md:121 - IGNORE
These are 0.1-0.3 points off the table in the PR description (15.3 vs 15.2, 27.8 vs 28.1, 15.0 vs 14.9, 18.6 vs 18.5).  Presumably different campaigns; say so in both places, or use one table.


doc/intel-amx.md:38 - DONE
It's once per `apply_page_range` call, i.e. per (worker, kv_head, page-range section) and again for the pending pass, not once per worker per layer.  Say that.


doc/intel-amx.md:93 - IGNORE, this is ok
`with_app_pin_thread` pins to a logical CPU taken from a list; nothing keeps SMT siblings out of that list.  s/tron already pins one attention worker per CPU/this holds if the configured core list excludes SMT siblings/.


doc/intel-amx.md:170
The gate is spelled three times in `self_attention.hpp` (1358, 1547, 1622), two of them with bare `4`/`128`.  See my comment there; then this sentence can become true.


doc/intel-amx.md:185 - DONE
`config/models.yaml` has 40 families, 36 at `cpp_plugin` or better.  Which count is this?  Also, geometry for the ingested families isn't in the tree, so record how the list was produced or it will go stale.


doc/intel-amx.md:189
"no AMX code compiled into its instantiation" is true for the dispatch and false for the mirror: under `TRON_AMX_K_MIRROR` the arena is allocated and `save_k` scatters into it for every geometry, eligible or not (see `model.hpp`).  Qualify it, or fix the code so it becomes true.


h/tron/kernels/amx_attn_iface.hpp:54
Not true for `qk_canonical_128x4`, which writes exactly 4 rows into `s` (and `t_amx_numerics` hands it a 4-row buffer).  Scope the sentence to the kernels whose argument receives a `TILESTORED` directly.


h/tron/kernels/amx_attn_iface.hpp:69
Grepping suggests nobody reads `tile_row_bytes`, and `amx_attn.cpp` redefines both constants as `TILE_ROWS`/`TILE_ROW_BYTES` while including this header.  Use these there, or flush this one.


h/tron/kernels/amx_attn_iface.hpp:81
Who guarantees the 64B alignment?  `amx_qpack` is a `std::vector<uint16_t>`, which promises 16.  The kernels only `_tile_loadd` it, so either drop the requirement from the contract (here and at :135) or give the buffer `alignas(64)` storage.  Fix one.


h/tron/kernels/amx_attn_iface.hpp:87
`uint16_t*`?  Any reason not to take `const bf16*` (or a `const_view<bf16, ..., seq<128>>` for the Q rows and a `std::array<float, 16 * 128>&` for the 16-row outputs)?  Then the size and alignment contracts in the Note are carried by the type instead of prose, and the dozen `reinterpret_cast`s at the call sites go away.  The header would still have no intrinsics.


h/tron/kernels/amx_attn_iface.hpp:117
There is no store-forwarding microbench in the tree, and the 982/686 figures come from `amx_fused_bench.cpp` with unrecorded arguments.  Numbers we can't reproduce shouldn't be stated as facts in a Note.  Keep them in the doc with the command that produced them, and reference that from here.


h/tron/kernels/amx_attn_iface.hpp:129
Keep the pointer to #2934 if it helps a reader find the other formulation; flush "this arena implementation is ours".  Attribution goes in the PR description.  Also, what's a "pinned AMX deployment"?  Say the concrete condition (builds that will only run on AMX hosts, since the arena RAM is wasted otherwise).


h/tron/kernels/amx_attn_iface.hpp:75
s/is not set/is not `1`/ - the A/B recipe in `t_amx_logit_ab.cpp` explicitly uses `=0`.


h/tron/kernels/page_share_counters.hpp:6
Is this instrumentation still needed?  Its conclusion (width 4 is the guaranteed decode width) is already baked into the kernel shape, nothing in CMake defines `TRON_PAGE_SHARE_COUNTERS`, and it adds a third flag family plus an exit-time printer under `kernels/` for something that instruments `models/`.  I'd record the histogram in `doc/intel-amx.md` and drop the code; if we want a live counter, the `TRACE_EVENT` args two lines above the page loop are the existing place.  Also, the guard is `#ifdef`, so `=0` enables it too; and with the flag on there is an increment per (page, token) inside the loop, so "Zero hot-loop cost" isn't what the code does.


h/tron/models/kv_cache.hpp:1199
This indexes the arena by the logical slot and never looks at `kv_blocks_alias`, but `page::k` does.  So under `set_storage_view(eagle_storage_offset())` (`full.hpp:1717`) the draft's `save_k` stores canonical K in the EAGLE physical slot while `set_k_mirror` scatters it into the validator's slot-0 plane.  Concretely: (1) validator writes token j of page p: physical slot 0 gets K_v, plane M(0) gets scatter(K_v); (2) draft, under the view, writes the same (p, j): physical slot L gets K_d, but M(0) := scatter(K_d); (3) the validator's next full-page decode runs `qk_mirror_128x4` on M(0) and scores against the draft's K.  The draft runs behind the validator on the same pages, so this hits every token older than the current validator batch, for the layer on slot 0; a page move repairs it (the rebuild reads canonical slot 0) until the draft saves again.  Meanwhile M(L) is only ever written by `copy_storage_slot` and never read.  `mirror()` needs to honour the view the same way `kv_block()` does (or assert no view is active while the arena exists), and the EAGLE-view test in `t_llama_unit.cpp` should check the mirror too.


h/tron/models/kv_cache.hpp:571
Lock-free cross-thread hand-off, eh?  Then the Note should say what orders the RX worker's plain stores before the attention worker's tile loads.  IIUC it is not `mark_k_complete` (software attention never reads `kv_saves_`); it is (a) pages written this forward are never in the ready plan, and (b) the write precedes `upstream_kvs_ready.count_down()` in program order and the pending pass acquires on `wait()`.  Write that down, and say the write must stay before the count-down for that reason, not for L1 locality, or someone will "optimize" it later.


h/tron/models/kv_cache.hpp:585
There is no separate defrag operation; `append` is the defrag path and the test calls it once.  s/(append + defrag)/(`book::append`, the defrag path)/.


h/tron/models/kv_cache.hpp:996
If `available()` is true and this `new` fails, we run a K_MIRROR build with no AMX QK at all (the canonical kernel is `#else`'d out in `apply_page_tok`) and nothing says so - silent bad performance instead of a loud error.  At least `spdlog::warn` once; better, keep `qk_canonical_128x4` as the fallback in the mirror build.  Also, `kv_bytes/2` of host RAM per book appears in neither `log_kv_footprint` nor `dma_size_bytes()`, and main's `Note [DMA-sized KV books]` (9076993a0) now says every buffer a book owns fits one DMA allocation - that Note needs the arena as an exception when you rebase.


h/tron/models/kv_cache.hpp:999
This `/ 2`, and the two in `mirror_at_storage`, are the `kv_block_planes` you just introduced, written as a literal.  Use it, or `static_assert(kv_block_planes == 2)` next to them, so the two can't drift.


h/tron/models/kv_cache.hpp:1174
`kv_block_at_storage` asserts `slot_matches<geometry>` and the EAGLE offset; this copy of its `byte_base` branch asserts nothing, so a mismatched geometry silently computes `plane_bytes` for the wrong head size and can run off the end of the arena.  Factor one `storage_byte_base<geometry>(offset)` helper used by both, so the mirror inherits the asserts.


h/tron/models/kv_cache.hpp:569
Is `kv_block_planes` ever anything but 2?  If it's a leftover of the in-block third-plane design, the rename of the pre-existing `2 *` literals (here, :1138, `t_llama_unit.cpp:415`) is an unrelated refactor - its own small PR, or drop it.


h/tron/models/kv_cache.hpp:525
CMake already refuses this combination (`src/tron/CMakeLists.txt:178`).  If the `#error` is for non-CMake builds, say so; otherwise one check is enough.


h/tron/models/kv_cache.hpp:1444
This accessor (and `v_base()` at :2100) exists in every build, but the layout it describes exists only under `TRON_CHUNK_SIZE == 16`; the `#else` branch is plain `[p][i/C][i%C]`.  Guard the accessors the same way, or say so in the comment.


h/tron/models/kv_cache.hpp:1811
One sentence here on who runs this and why concurrent readers are safe (scheduler thread under `tree_lock`; only fresh tokens at or past `tok_ct`; the mirror's only reader needs all 64 tokens live).  The 16-tokens-per-line layout means these stores touch lines that also hold live tokens' columns, which is exactly what the next reader will worry about.


h/tron/models/model.hpp:2767
This gates the write-through on `available()` only, but the only reader is behind `head_size == 128 && kv_mul == 4`.  On an AMX host running any other geometry (or any non-matching slot of a mixed layout) the RX worker pays the scatter (and `copy_storage_slot` the rebuild) and the book the `kv_bytes/2`, for planes nobody reads.  Gate the write, the rebuild, and the arena on the same predicate as the reader.  Also, `set_k_mirror` already no-ops on a null plane, so as written `k_mirror_on` is redundant with the arena condition rather than a correctness guard; the comment should say which it is.  And `model.hpp` calls `amx_attn::available()` without including its header.


h/tron/models/self_attention.hpp:19
`kv_cache.hpp` guards its include of `amx_attn_iface.hpp` under the flag; here both new headers are unconditional.  Pick one convention.  Also, `<cstdint>` is now used directly (`uint16_t`, `uint64_t`) and not included.


h/tron/models/self_attention.hpp:1358
`head_size == 128 && kv_mul() == 4` is spelled here and twice more in `apply_page_tok` (1547, 1622) with bare `4`/`128`, and `amx_attn.cpp` has its own `HEAD_SIZE`/`GROUP_HEADS`.  Let's export the two constants (or a `constexpr bool supports(head_size, kv_mul)`) from `amx_attn_iface.hpp` and evaluate the predicate once.


h/tron/models/self_attention.hpp:1361
Why lazy?  Packing all `items.size()` groups once before the page loop is at most `max_minibatch_size` 512-byte copies and deletes the bitmap and the per-(page, token) test-and-set.  If a cache is really wanted, `attn_accum` is already per worker, per token and 64B-aligned; a growable `thread_local std::vector` is neither aligned (see the header contract) nor bounded the way the mask next to it is.


h/tron/models/self_attention.hpp:1362
The comment says `items.size() <= max_minibatch_size`; who enforces it?  (`batch_evenly` does, `model.hpp:326`, but it's a long way from here - a `TRON_ASSERT_LE(items.size(), max_minibatch_size)` next to the mask costs nothing.)


h/tron/models/self_attention.hpp:1414
The declaration comment already explains the word/bit split; this second explanation of `>> 6` and `& 63` is more than the two operators deserve.  Flush.


h/tron/models/self_attention.hpp:1367
We have `tron::finally` (`h/common/util.hpp:73`, used in `gof.hpp:221`) for exactly this bracket; `tron::finally release([&] { if (amx_on) amx_attn::end_region(); });` makes the pairing structural.  Not a bug today (the function is `noexcept` and there is no return in between), your choice.


h/tron/models/self_attention.hpp:1493
The default is never used (the one caller always passes `amx_qp`), and in a build without the flag the parameter is unreferenced - does the default build now warn under `-Wextra`?  CI didn't run, so I can't tell.  Drop the default, and I'd rather the OFF build's `apply_page_tok` were textually unchanged (parameter and `did_amx` under the flag).


h/tron/models/self_attention.hpp:1502
On the pages AMX takes, the four `dotter` constructions here (16 zmm loads) and the `-inf` init of `s_pages` are dead work per (page, token); moving them under `if (!did_amx)` is free.  Also, "share the bf16 -> fp32 conversion" describes `dotter<float, 128>`; the `dotter<bf16, 128>` used here converts nothing.  Pre-existing, but you're touching it.


h/tron/models/self_attention.hpp:1558
So the mirror path pays a 1 KB copy per page that the canonical path doesn't, and the `amxqk` bench variant behind the 686 ns figure stores straight into a 16-row `S` with no copy.  Either size `s_pages` for 16 rows in the mirror build, or note the copy's cost next to the 300 ns claim.  Also, when `mplane` is null in this build we fall all the way to the dotter although `qk_canonical_128x4` is compiled into the same binary - why not fall back to it?


h/tron/models/self_attention.hpp:1618
This paragraph is justifying the code to the reviewer; "`if constexpr` so other geometries don't instantiate this block" is the whole content.  Flush the rest.  Also, pass 1 is a second copy of the per-head scale/softcap/max/exp/sum math below (I diffed them; identical today) - that is how they drift.  Pull the per-head part into a helper both loops call.


h/tron/models/self_attention.hpp:1651
Any reason not to point a `const_view<float, true, false, seq<128>>` at `amx_o + offset * 128` instead of copying 512 B per head into `scratch`?  The AVX path feeds `fma` an expression for the same reason.


h/tron/models/self_attention.hpp:1656
`constant<page::page_size>` (64 wide) as the multiplier in a 128-wide `fma` only works because `constant::chunk(i)` ignores `i`.  Pre-existing at :1685, but let's not copy it: `constant<operation_head_size>`.


src/tron/CMakeLists.txt:170
AMX-BF16 is Sapphire Rapids and later, and the code gates on CPUID bits, not the model.  s/(Granite Rapids)/(requires AMX-BF16)/.


src/tron/CMakeLists.txt:183
Only `-mamx-tile -mamx-bf16` are new for this TU; the `-mavx512*`/`-mavx2`/`-mfma` are already PUBLIC on `tron` (:234-237) unless `AVX512=OFF`, in which case this would be the only AVX-512 code in a non-AVX-512 binary.  Is that build meant to exist?  If not, trim the list; if so, say so.


src/tron/kernels/amx_attn.cpp:7
Unused?


src/tron/kernels/amx_attn.cpp:26
Ditto: `TILE_ROWS`/`TILE_ROW_BYTES` duplicate `tile_rows`/`tile_row_bytes` from the header this file includes, and `PAGE` duplicates `page::page_size` with nothing tying them together.


src/tron/kernels/amx_attn.cpp:32
Eight lines of prose for `static_assert(sizeof(float) == 4)`.  I can smell Claude patting itself on the back a mile away.  The message string says everything the assert needs to say; flush the paragraph.


src/tron/kernels/amx_attn.cpp:43
`DIM_STEP` is documented as 32 head dims per k-step, but at :210 it means 32 tokens per PV k-step and at :211 it means 16 dims x 2 paired tokens per V tile column.  Three quantities with the same numeral shouldn't share a constant; name the other two.  Also, the `4` at :251 is `PAGE / TILE_ROWS`.


src/tron/kernels/amx_attn.cpp:62
You know we have `cpuid_bit(leaf, reg, bit)` in `h/system/mwaitx.hpp:22`, and that `is_rtm_supported` (`lazy<bool>` + `TRON_NO_RTM=1`) is the same shape as this whole function, right?  Reuse it, or say why the AMX probe can't.


src/tron/kernels/amx_attn.cpp:64
This is a first-character test: `TRON_AMX_DISABLE=true` leaves AMX on, silently.  Nearest precedents are `strcmp(v, "1") == 0` (`TRON_NO_RTM`, `TRON_USE_ARENA_ALLOCATOR`) or `atoi(v) > 0` (`USE_HW_ATTN`); pick one.


src/tron/kernels/amx_attn.cpp:106
Each pack memsets 4 KB to write 512 B; columns 4..15 never change.  The `P` buffer below zeroes its padding once per thread - same discipline here?


src/tron/kernels/amx_attn.cpp:200
A one-line comment that `cvtne2ps_pbh(a, b)` puts `b` in the low half would save the next reader the lookup.


src/amx_fused_bench.cpp:3
A 732-line `main()` in `src/` that no CMake target builds, which re-implements every shipped kernel by hand (`pack_q`, `qk_amx`, `qk_amx_rowmajor`, `pv_amx`, `pack_k_mirror`, `st_to_s`).  Any kernel fix now has to be made twice, and the numbers quoted in `Note [Mirror orientation]` were measured on the copy, not on `amx_attn.cpp`.  Either make it a `t/` benchmark target that links `libtron` and calls the real kernels, or take it out of the tree and keep the numbers in the doc with the command line that produced them.  A second copy of every kernel in `src/` is not something I want to approve.


src/amx_fused_bench.cpp:22
`amxqk` and `amxpl` are missing from this list (and `amx_attn.cpp:230` cites `amxqk`).


src/amx_fused_bench.cpp:31
There is no `t_amx_attention` on main; it lives on `bill-amx`.  Also 2e-2 relative is a long way from the `1e-4 * abs_mass` `t_amx_numerics` uses in this same PR, so "practice" is doing a lot of work here.  Flush the clause.


src/amx_fused_bench.cpp:75
The degree-5 Taylor terms give ~3.3e-6 at |f| = 0.5 (I checked), not 2e-7.  Fix the number or delete the sentence; the conclusion holds either way.


src/amx_fused_bench.cpp:119
Neither `transpose16x16` nor its reference is used by any variant (`st_to_s` has its own copy); they exist to validate each other.  Flush all three pieces.


src/amx_fused_bench.cpp:264
A question mark in a size comment means we don't know the size.  It's 4*16*32 bf16 = 4*16*64 bytes; write one.  Also, s/(Bill's formulation)// at :279 - same as the "ours" in the header Note.


t/CMakeLists.txt:190
This is registered under `LABELS fpga`, so `bin/slice run --filter=fpga` (the Test FPGA job), `make test`, and `ctest -L fpga` all select it, and its first line is `REQUIRE(getenv("AMX_LOGIT_OUT") != nullptr)`.  The FPGA lane fails the moment CI runs on this PR.  It's a dump tool, not a test (its one `SUCCEED` asserts nothing about AMX): make it a `runtron`/`tronutil` flag or a `bin/` script and drop the ctest entry; if it stays, `DISABLED TRUE` like `t_clearhbm`.  Also, it defaults to `ingested-llama-3.1-8b` but sits outside `if(BUILD_INGEST_MODELS)`.


t/CMakeLists.txt:357
In the default build all three of these are a single `SUCCEED("...skipped")`, and even with the options on they `WARN` and return on a non-AMX host - so after merge nothing in CI compiles or runs the flagged code.  How was this validated, given `make test` has no coverage for it?  At minimum a compile-only configuration with both options ON (precedent: `heterogeneous_scheduler_compile`, :351) so the `#ifdef`'d code can't rot silently; the run log from the 6962P host in the PR would also help.


t/t_amx_arena_leak.cpp:47
What failure is this guarding against?  `unique_ptr` with `mirror_delete` frees by construction, and a new[]/delete[] form mismatch is what the ASan build is for.  Replacing the global aligned `operator new[]` in a test binary is a lot of mechanism for that; if it stays, `memperf.cpp` already replaces the same forms.


t/t_amx_arena_leak.cpp:90
Can we tighten this to `== 1`?  With an example this small the count is predictable.


t/t_amx_mirror.cpp:28
The reference here is the implementation's own index formula, so a layout change applied to both passes; the only test that ties the plane to its consumer (`qk_mirror_128x4`) is hardware-gated.  A scalar model of the kernel's panel addressing would pin the layout to the reader on any host.  Also, this is the fourth copy of the formula (Note, `scatter_k_mirror`, here, `t_llama_unit.cpp:440`); a `require_mirror_matches` in a `t/` header used by both tests would leave two.


t/t_amx_mirror.cpp:80
Which consumer reads a head-64 plane?  Dispatch requires head 128, so this is 8192 `REQUIRE`s guarding data nobody reads - the same point as the write-through gate in `model.hpp`: don't maintain planes no kernel consumes, and this case goes away.


t/t_amx_numerics.cpp:1
Nice - a real reference on both sides, in double.


t/t_amx_numerics.cpp:105
The reorder bound for 128 exact products summed in fp32 is 127 ulp = 7.6e-6 of the mass, so 1e-4 is 13x looser than the math allows, and the comment calls it "a small multiple of fp32 epsilon" (it's ~1700).  Where does 1e-4 come from?  Tighten to a few times the bound, or state the measured maximum and why the margin.  Ditto :209.


t/t_amx_numerics.cpp:32
We renamed this `HEAD_SIZE` in the kernel TU; same here (and in the bench)?  Also `std::make_unique` without `<memory>`.


t/t_amx_numerics.cpp:77
`q_pack_elems` exists for this.


t/t_amx_numerics.cpp:143
Where does that check live?  Nothing in the tree performs it (`t_amx_logit_ab` only dumps).  Name it or delete the sentence; the local assertion stands on its own.


t/t_llama_unit.cpp:427
IIUC only token 0 of this page came through `copy_storage_slot` (append copied 64 tokens into page 0 and one into page 1, and `destination` never advanced `tok_ct`); tokens 1..63 here were rebuilt by `fill_random`.  So the defrag rebuild is checked for `i == 0, dst_begin == 0` only - a dropped `dst_begin + i` or a wrong `dst + i * head_size` stride passes.  Check page 0 too, and do one append into a destination whose `tok_ct` is not a multiple of 64.


t/t_llama_unit.cpp:1220
I worked through the dense predicate and I believe it (token 0 is the binding window case; the `tok_hi` check on offset 63 covers the range).  But nothing in `t/` ever reaches it: this test uses `n_heads = 16`, `n_kv_heads = 8`, so `kv_mul == 2` and `amx_qp` is always null.  Can we have a `kv_mul == 4` case (n_heads 32 - the llama-3.1-8b shape) so the whole AMX QK + PV path is compared against `emulation::compute_attention`?  On non-AMX hosts it degrades to the AVX path and still passes.  Ideally with sub-cases for a mask range ending inside the page and the window edge (`sliding_window_size` 64 vs 65 for a query at position 127).

