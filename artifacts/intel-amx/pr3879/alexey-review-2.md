# Review of PR #3879 as Alexey would write it - round 2

https://github.com/positron-ai/tron/pull/3879 - AMX software attention (default-off): QK/PV tile kernels + K-mirror arena  
Head `cc8a86bb3` (round 1 reviewed `bbb55ae5f`; delta = one commit, cc8a86bb3 "Gate the K mirror arena and write-through on the AMX attention shape", 7 files, +172/-57); base `1407f48dd`; 16 files, +2565/-37. Written 2026-08-25. HTML twin: `alexey-review.html`; round 1 archived as `alexey-review-1.html`.

Lineage note: "mirror" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). "canonical-K" = K in today's original single-copy storage, read as-is.

Each comment shows the source lines it refers to (new head; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.

## 1. Verdict

**CHANGES_REQUESTED**

Progress - the shape gate is the right fix, and `shape_ok` in one place is what I asked for.  Two of the three blockers are still open, though: the EAGLE storage-view aliasing in `book::mirror()` is untouched, and `t_amx_logit_ab` is still an `fpga`-labelled test that fails without `AMX_LOGIT_OUT`.  The gate change also brought two things I'd rather not merge: a 3-argument `book`/`try_create` that defaults `amx_mirror_eligible` to true (kept, as far as I can see, for the tests and for a concept that now describes the old interface), and a doc paragraph that says "8 models" and lists six.  The PR description still says the arena is allocated "only when AMX is available at runtime" and still doesn't mention the doc, the `kv_block_planes` refactor, or the new scheduler plumbing; the split into a development chain and a `Run CI` run are still outstanding.  The rest of round 1 is carried over unchanged below; I've marked the two items you asked about.

## 2. Resolved by cc8a86bb3

| round 1 | where (new head) | what was asked | how it was addressed | his reply, if any |
|---|---|---|---|---|
| R1-01 (fixed) | `doc/intel-amx.md:42` | Two `xxx:` notes-to-self made it into the committed doc.  Please read it through once before requesting review; I'd rather not review placeholders. | delta.diff removes both placeholder lines (`-xxx: replace "reciprocal" with easier word/phrase`, `-xxx: replace "same-C accumulation chain" with easier verbose`). NEW doc/intel-amx.md:42-44 now reads `### Throughput reality` / `- A full TDP has ~16-cycle reciprocal throughput; a same-C accumulation` / `  chain sustains that rate (accumulation adds no stall).` No `xxx` remains in the file (grep). \| your triage: DONE |  |
| R1-02 (fixed) | `doc/intel-amx.md:86` | The part I'm questioning is "before AMX-using threads start", not the once-per-process caching in `available()` (that is fine).  The `arch_prctl` runs inside the first `available()` call, and the first caller is an at... | Doc side was chosen. NEW doc/intel-amx.md:86-87: `- One \`arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)\` once per process,` / `  from whichever thread first calls available()` (old: `per process / before AMX-using threads start.`). Consistent with the header Note, amx_attn_iface.hpp:29-30 `arch_prctl(ARCH_REQ_XCOMP_PERM) - a per-PROCESS grant (Linux xstate rules); result cached.` and with amx_attn.cpp:87 `static const bool ok = detect_and_request();` inside available(). \| your triage: DONE | Very good. |
| R1-09 (fixed) | `doc/intel-amx.md:185` | "no AMX code compiled into its instantiation" is true for the dispatch and false for the mirror: under `TRON_AMX_K_MIRROR` the arena is allocated and `save_k` scatters into it for every geometry, eligible or not (see ... | Doc qualified: doc/intel-amx.md:184-189 `In the canonical build no AMX code is compiled into its instantiation; in the mirror build the same shape gate (\`amx_attn::shape_ok\`, shared by the dispatch, the \`save_k\` write-through, and the mirror-arena allocation) compiles out the write-through and skips the arena, so an ineligible model on an AMX host pays nothing for the mirror either.` Code made true: model.hpp:2769-2771 `constexpr bool k_mirror_shape_ok = amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul()); const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();`, :2793-2794 `if constexpr (k_mirror_shape_ok) { if (k_mirror_on) {` around set_k_mirror; kv_cache.hpp:1039 `if (!amx_mirror_eligible \|\| !amx_attn::available()) return;` in maybe_allocate_mirror_arena; full.hpp:1454-1456 `root = std::make_shared<node_t>(..., cfg->support_eagle, amx_mirror_eligible(model_t::plugin_t::attention_kernels));`, :832-833 `book::try_create(bk_pages, storage_kv_slots, support_eagle, amx_mirror_eligible)`; t_amx_arena_leak.cpp new case checks a head-64 book with amx_mirror_eligible=false performs 0 aligned allocations. |  |

## 3. Open comments (79: 65 carried over from round 1, 14 new)

Carried-over comments keep their round-1 text; where the commit addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**. A leading `[blocker]` marks the comments the body names.

### doc/intel-amx.md

#### `doc/intel-amx.md:38` R1-05 (A3)

```markdown
   38* One `LDTILECFG`/`TILERELEASE` pair per work region (Intel guidance; ~229
   39  cycles measured between `begin_region()`/`end_region()`). 6962P also has AMX-INT8
   40  and AMX-FP16; tron's KV cache is bf16, so only `TDPBF16PS` is used.
```

It's once per `apply_page_range` call, i.e. per (worker, kv_head, page-range section) and again for the pending pass, not once per worker per layer.  Say that.  The frequency statement was removed instead of corrected, and "~229 cycles measured between `begin_region()`/`end_region()`" now reads as time elapsing inside the region; the number is the cost of the pair.  Say both.

_Verification: round 1 (R1-05), partial: The wrong frequency claim was removed rather than corrected: the doc no longer says how often the pair is paid (once per apply_page_range call = per (worker, kv_head, page-range section), and again for the pending pass). doc/intel-amx.md:49-50 still says `~229 cycles per work region` without defining a work region, and amx_attn_iface.hpp:49-51 still says `begin_region()/end_region() bracket one worker's page loop`. | your triage: DONE_

#### `doc/intel-amx.md:90` R1-06 (A3)

```markdown
   90* - One AMX thread per physical core (Intel guidance); tron already pins one
   91    attention worker per CPU from an explicit core list.
```

`with_app_pin_thread` pins to a logical CPU taken from a list; nothing keeps SMT siblings out of that list.  s/tron already pins one attention worker per CPU/this holds if the configured core list excludes SMT siblings/.

_Verification: round 1 (R1-06), not addressed | your triage: IGNORE, this is ok | persona prediction: He would accept 'the deployed core lists exclude SMT siblings' if the sentence says that; as written it still implies tron enforces it._

#### `doc/intel-amx.md:100` R1-03 (A3)

```markdown
   99  Software attention - the `apply_page_tok` QK and PV inner loops. The main
  100* target is forced software attention (`USE_HW_ATTN=0`), where attention
  101  compute is the decode wall at long context (a measurement based estimation
  102  put attention at ~64% of the decode step on the primary model at ctx 8192).
```

Archived where?  A number a reader cannot check should get a pointer or go.  This went the other way: the qualifier that it was a fit and not a trace is gone, and there is still nothing a reader can follow.  Cite where the estimate lives (result file, doc, PR) or drop the number.

_Verification: round 1 (R1-03), partial: The word "archived" is gone, but the ~64% figure is still stated with no pointer to the campaign, log, or results file, and it was not removed - neither half of "pointer or go" was done. The reword also dropped the earlier caveat ("derived from context-scaling fits, not a direct trace of that cell"), so the number is now less qualified than before. | your triage: DONE_

#### `doc/intel-amx.md:118` R1-04 (A3/A4)

```markdown
  118* Primary: `ingested-qwen-3-4b-instruct-2507-tp2`. All comparisons are
  119  same-binary kill-switch A/Bs against the true clean binary. Decode
  120  (replicated, 8 reps/cell, 95% CI): +15.3..+17.7% (canonical) /
  121  +19.7..+27.8% (mirror) at 1u/8K..8u/8K. Prefill (3-rep suite): up to +105%.
  122  Energy per token (separate power capture at 8u/8K): -14.5% / -21.6%.
  123  Generalization: llama-3.1-8b decode +15.0% (1u/8K) / +19.7% (8u/2K);
  124  mixtral-8x7b +9.4% canonical / +18.6% mirror (8u/8K); gpt-oss (ineligible
  125  geometry) -0.3..-1.6% = no regression when the gate does not fire.
```

These are 0.1-0.3 points off the table in the PR description (15.3 vs 15.2, 27.8 vs 28.1, 15.0 vs 14.9, 18.6 vs 18.5).  Presumably different campaigns; say so in both places, or use one table.

_Verification: round 1 (R1-04), not addressed | your triage: IGNORE | persona prediction: If told 'different campaigns', he would answer: then say so in one of the two places.  Not a blocker for him._

#### `doc/intel-amx.md:145` **new** (A3)

```markdown
  143  prefetch streams (LLC miss 51%->85%, AVX fallback -4..-8%, ~9% tax on the
  144  canonical path) and cost 33% KV page capacity. The arena is ordinary RAM
  145* (`kv_bytes/2`), allocated only when AMX is available at runtime, fail-soft
  146  to null; page capacity is identical with and without it. Coherence
  147  (`Note [K mirror coherence]`): the mirror is a pure derived view with
```

This sentence didn't follow the gate: the arena now also requires an eligible attention shape.  Ditto the same sentence in the PR description.

_Verification: Status agent S1 (R1-09 remaining): doc:144-146 still says 'allocated only when AMX is available at runtime'; body.md has the same wording._

#### `doc/intel-amx.md:167` R1-07 (A3/B6)

```markdown
  167* The fast path engages only for one attention shape. The whole gate is one
  168  line of compile-time arithmetic plus the runtime check
  169  (`h/tron/models/self_attention.hpp`):
  170  
  171  ```c++
  172  constexpr bool amx_shape_ok =
  173      geometry.kv.head_size == 128 && geometry.kv_mul() == 4;
  174  const bool amx_on = amx_shape_ok && amx_attn::available();
  175  ```
```

The gate is spelled three times in `self_attention.hpp` (1358, 1547, 1622), two of them with bare `4`/`128`.  See my comment there; then this sentence can become true.  The code block below (:171-175) still shows the old literal, and the prose still says "one line"; the gate is `amx_attn::shape_ok(...)` now.  Update the block.

_Verification: round 1 (R1-07), partial: The doc's code block (doc/intel-amx.md:171-175) still shows the pre-change literal `geometry.kv.head_size == 128 && geometry.kv_mul() == 4` and points at self_attention.hpp; the actual one-line gate is now `amx_attn::shape_ok` in h/tron/kernels/amx_attn_iface.hpp:81-83, and self_attention.hpp:1358-1359 calls it. The snippet and file reference need updating for the sentence to match the tree._

#### [blocker] `doc/intel-amx.md:182` **new** (A3)

```markdown
  182* The following 8 models match the gate: qwen-3-4b-2507, llama-3-8b, llama-3.1-8b,
  183  mistral-7b, ministral-8b, mixtral-8x7b. Three are measured (qwen,
  184  llama-3.1-8b, mixtral). Every other family runs the unchanged AVX path. In
```

Six names, and the sentence says 8.  Fix either the number or the list - and were phi-4 and granite-3.3-8b dropped on purpose?  The other half of my earlier question stands too: record how the list was produced, or it will go stale.

_Verification: Supersedes R1-08 (your triage: DONE); the rewrite introduced this. Count from the text itself: qwen-3-4b-2507, llama-3-8b, llama-3.1-8b, mistral-7b, ministral-8b, mixtral-8x7b = 6._

### h/tron/kernels/amx_attn_iface.hpp

#### `h/tron/kernels/amx_attn_iface.hpp:56` R1-10 (A3)

```cpp
   53  // Note [Tile stores write 16 rows]
   54  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   55  // TILESTORED always writes ALL 16 configured tile rows, no matter how many
   56* // carry real data: a width-4 result still stores 16 rows. Every output
   57  // buffer handed to a kernel below must therefore be sized for 16 rows -
   58  // a "4 x N" buffer is a silent stack overrun (rows 4..15 land past its
   59  // end). Rows 4..15 receive zeros; only rows 0..3 are the result.
```

Not true for `qk_canonical_128x4`, which writes exactly 4 rows into `s` (and `t_amx_numerics` hands it a 4-row buffer).  Scope the sentence to the kernels whose argument receives a `TILESTORED` directly.

_Verification: round 1 (R1-10), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:71` R1-11 (B2/B6)

```cpp
   66  // Tile geometry shared by every kernel below: begin_region() configures all
   67  // 8 tiles as 16 rows x 64 bytes, and TILESTORED always writes all 16 rows
   68  // (see Note [Tile stores write 16 rows]) - output buffers are sized with
   69  // tile_rows.
   70  inline constexpr size_t tile_rows = 16;
   71* inline constexpr size_t tile_row_bytes = 64;
```

Grepping suggests nobody reads `tile_row_bytes`, and `amx_attn.cpp` redefines both constants as `TILE_ROWS`/`TILE_ROW_BYTES` while including this header.  Use these there, or flush this one.

_Verification: round 1 (R1-11), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:78` **new** (A3)

```cpp
   76  // THE shape gate: the AMX kernels serve exactly one attention shape, 4 query
   77  // heads x 128 dims per KV head (the tile identity, see
   78* // Note [AMX attention dispatch]). Shared by the dispatch, the save_k mirror
   79  // write-through, and the mirror-arena allocation, so the reader and the
   80  // writers can never disagree about which models take the AMX path.
   81  constexpr bool shape_ok(size_t head_size, size_t kv_mul) noexcept {
   82    return head_size == 128 && kv_mul == 4;
   83  }
```

"so the reader and the writers can never disagree" - two of the three writers don't use this gate (the `copy_storage_slot` and `fill_random` rebuilds scatter for any geometry whose plane is non-null), and the 3-argument `book` forms pass `true`.  It holds for books the scheduler creates.  Say that, or make it true.

_Verification: N2-10, N3-6: rebuild sites kv_cache.hpp:1857-1862 and :1286-1290 have no shape_ok; legacy forms at :764 and :968-969 pass true._

#### `h/tron/kernels/amx_attn_iface.hpp:86` R1-16 (A3)

```cpp
   85  // True when the CPU, the OS, and the per-process permission all allow AMX,
   86* // and TRON_AMX_DISABLE is not set. See Note [AMX attention dispatch].
   87  bool available() noexcept;
```

s/is not set/is not `1`/ - the A/B recipe in `t_amx_logit_ab.cpp` explicitly uses `=0`.

_Verification: round 1 (R1-16), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:92` R1-12 (A3)

```cpp
   89  // Pack one query group (4 query heads x 128 dims, contiguous bf16) into the
   90  // tile B-operand (VNNI pair-interleaved) layout consumed by
   91  // qk_canonical_128x4.
   92* // `packed` must hold q_pack_elems bf16 (4 KB), 64B-aligned.
```

Who guarantees the 64B alignment?  `amx_qpack` is a `std::vector<uint16_t>`, which promises 16.  The kernels only `_tile_loadd` it, so either drop the requirement from the contract (here and at :135) or give the buffer `alignas(64)` storage.  Fix one.

_Verification: round 1 (R1-12), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:98` R1-13 (B5)

```cpp
   96  //   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
   97  //     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
   98* void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
```

`uint16_t*`?  Any reason not to take `const bf16*` (or a `const_view<bf16, ..., seq<128>>` for the Q rows and a `std::array<float, 16 * 128>&` for the 16-row outputs)?  Then the size and alignment contracts in the Note are carried by the type instead of prose, and the dozen `reinterpret_cast`s at the call sites go away.  The header would still have no intrinsics.

_Verification: round 1 (R1-13), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:128` R1-14 (A3/A4)

```cpp
  125  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  126  // (K consumed exactly as stored) and must then round-trip the score tile
  127  // through memory and transpose it - a ~300 ns/page whole-path cost at
  128* // width 4 (982 vs 686 ns, measured with the fused-page benchmark,
  129  // src/amx_fused_bench.cpp; transpose work + score traffic combined, not
  130  // isolated). NOT a store-forwarding stall: 64-byte
  131  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
  132  // a 6962P microbench measured no stall on that path; the hard restriction
  133  // is the opposite direction, any store -> TILELOADD cannot forward.
```

There is no store-forwarding microbench in the tree, and the 982/686 figures come from `amx_fused_bench.cpp` with unrecorded arguments.  Numbers we can't reproduce shouldn't be stated as facts in a Note.  Keep them in the doc with the command that produced them, and reference that from here.

_Verification: round 1 (R1-14), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:140` R1-15 (B11)

```cpp
  139  // there too). Both ship:
  140* // canonical-K is the supported default; the mirror is opt-in
  141  // (TRON_AMX_K_MIRROR) for pinned AMX deployments. Precedent: the mirror
  142  // formulation is PR #2934's k_vnni idea; this arena implementation is ours.
```

Keep the pointer to #2934 if it helps a reader find the other formulation; flush "this arena implementation is ours".  Attribution goes in the PR description.  Also, what's a "pinned AMX deployment"?  Say the concrete condition (builds that will only run on AMX hosts, since the arena RAM is wasted otherwise).

_Verification: round 1 (R1-15), not addressed_

### h/tron/kernels/page_share_counters.hpp

#### `h/tron/kernels/page_share_counters.hpp:6` R1-17 (A1/A9/A3)

```cpp
    6* // Compiled in only with -DTRON_PAGE_SHARE_COUNTERS=1. Zero hot-loop cost:
    7  // callers accumulate plain locals and flush to the global atomics once per
    8  // apply_page_range call (roughly once per (worker, kv_head, page-range) - a
    9  // few tens of thousands of flushes per second at most).
   10  //
   11  // Dump: automatic at process exit to stderr.
   12  
   13  #ifdef TRON_PAGE_SHARE_COUNTERS
```

Is this instrumentation still needed?  Its conclusion (width 4 is the guaranteed decode width) is already baked into the kernel shape, nothing in CMake defines `TRON_PAGE_SHARE_COUNTERS`, and it adds a third flag family plus an exit-time printer under `kernels/` for something that instruments `models/`.  I'd record the histogram in `doc/intel-amx.md` and drop the code; if we want a live counter, the `TRACE_EVENT` args two lines above the page loop are the existing place.  Also, the guard is `#ifdef`, so `=0` enables it too; and with the flag on there is an increment per (page, token) inside the loop, so "Zero hot-loop cost" isn't what the code does.

_Verification: round 1 (R1-17), not addressed_

### h/tron/models/kv_cache.hpp

#### `h/tron/models/kv_cache.hpp:182` **new** (A5/B1)

```cpp
  180  // (see Note [K mirror parallel arena]).
  181  template <size_t n_kernels>
  182* constexpr bool amx_mirror_eligible(
  183      std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  184    for (auto const& kernel : kernels) {
  185      if (amx_attn::shape_ok(kernel.geometry.kv.head_size, kernel.geometry.kv_mul())) {
```

Any eligible kernel makes the whole arena: for a model with one eligible and one ineligible attention kernel the ineligible slots' planes are allocated (`kv_bytes/2` covers every slot), never written by `save_k`, and rebuilt on every page move by `copy_storage_slot`.  No in-tree plugin is mixed today, so fine - but say so here ("any kernel; sized for all slots; only eligible geometries are written through"), and a two-kernel array in `t_amx_arena_leak` would record the intended answer.

_Verification: N1/N3: amx_mirror_eligible() is any-of; arena sized over all slots (kv_cache.hpp:1040-1046); copy_storage_slot/fill_storage_slot rebuilds have no shape_ok (1857, 1286); every in-tree plugin declares one kernel (llama.hpp:191, mock.hpp:113); ingest can emit several._

#### `h/tron/models/kv_cache.hpp:539` R1-25 (B7)

```cpp
  539* #if defined(TRON_AMX_K_MIRROR) && !defined(TRON_AMX_DISPATCH)
  540  #error "TRON_AMX_K_MIRROR requires TRON_AMX_DISPATCH"
  541  #endif
```

CMake already refuses this combination (`src/tron/CMakeLists.txt:178`).  If the `#error` is for non-CMake builds, say so; otherwise one check is enough.

_Verification: round 1 (R1-25), not addressed_

#### `h/tron/models/kv_cache.hpp:586` R1-24 (A9)

```cpp
  585  // if a card consumes VNNI K natively or an FPGA-free build ships.
  586* inline constexpr size_t kv_block_planes = 2;
  587  #ifdef TRON_AMX_K_MIRROR
```

Is `kv_block_planes` ever anything but 2?  If it's a leftover of the in-block third-plane design, the rename of the pre-existing `2 *` literals (here, :1138, `t_llama_unit.cpp:415`) is an unrelated refactor - its own small PR, or drop it.

_Verification: round 1 (R1-24), not addressed_

#### `h/tron/models/kv_cache.hpp:588` R1-19 (A7)

```cpp
  588* // Note [K mirror coherence]
  589  // ~~~~~~~~~~~~~~~~~~~~~~~~~
  590  // Invariant: whenever the mirror arena exists, every stored token's mirror
  591  // bytes equal scatter_k_mirror(its canonical K row). The mirror is a pure
  592  // derived view; canonical K stays the source of truth (the FPGA and the AVX
  593  // fallback keep reading it as stored). Exactly two production write sites
  594  // maintain the invariant:
  595  //   1. the save_k write-through (model.hpp) on the RX worker, right after
  596  //      the canonical store while the row is L1-hot;
  597  //   2. the copy_storage_slot rebuild - every page move (defrag, append)
```

Lock-free cross-thread hand-off, eh?  Then the Note should say what orders the RX worker's plain stores before the attention worker's tile loads.  IIUC it is not `mark_k_complete` (software attention never reads `kv_saves_`); it is (a) pages written this forward are never in the ready plan, and (b) the write precedes `upstream_kvs_ready.count_down()` in program order and the pending pass acquires on `wait()`.  Write that down, and say the write must stay before the count-down for that reason, not for L1 locality, or someone will "optimize" it later.

_Verification: round 1 (R1-19), not addressed_

#### `h/tron/models/kv_cache.hpp:602` R1-20 (A3)

```cpp
  601  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  602* // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  603  // the mirror checks in t/t_llama_unit.cpp (append + defrag).
```

There is no separate defrag operation; `append` is the defrag path and the test calls it once.  s/(append + defrag)/(`book::append`, the defrag path)/.

_Verification: round 1 (R1-20), not addressed_

#### [blocker] `h/tron/models/kv_cache.hpp:764` **new** (A12/A6)

```cpp
  759    // Legacy form: keeps today's behavior (mirror arena allocated whenever AMX
  760    // is available) for tests and callers that carry no model information.
  761    book(size_t n_pages,
  762        size_t storage_slot_count = n_slots,
  763        bool support_eagle = false) noexcept
  764*   : book(n_pages, storage_slot_count, support_eagle, /*amx_mirror_eligible=*/true) {}
```

A constructor that defaults `amx_mirror_eligible` to true allocates the arena for a book that may never read it - the thing this commit set out to stop.  Who still needs the 3-argument forms?  As far as I can see the tests, and the `sequence_cache_behavior` concept at :1328-1330, which now describes yesterday's interface.  Let's update the concept to the 4-argument forms, pass the flag explicitly in the tests (about 24 sites), and flush the delegating overloads (here and `try_create` at :965).  Also, "keeps today's behavior" describes the diff, not the code.

_Verification: Callers of the 3-arg forms in h/ src/: none in production (grep); t/ and the concept only. Persona A12 quote: 'prevent invalid data structures from ever existing'; A6: 'we probably shouldn't default the value'._

#### `h/tron/models/kv_cache.hpp:766` **new** (A3)

```cpp
  766*   // The only constructor that carries the mirror-eligibility decision: the
  767    // scheduler passes amx_mirror_eligible(plugin::attention_kernels), so a
  768    // model without an AMX-eligible attention shape allocates no mirror arena.
  769    book(size_t n_pages,
  770        size_t storage_slot_count,
  771        bool support_eagle,
  772        [[maybe_unused]] bool amx_mirror_eligible) noexcept
```

"The only constructor that carries the mirror-eligibility decision" - the adopt-constructor at :1005 carries it too, and the scheduler's path is `try_create` (`full.hpp:832`) into that one; nothing in production reaches this constructor (its sole caller is `t_amx_arena_leak.cpp:123`).  Same for the "see the 4-argument constructor" pointer at :972.  Fix the comments, or the code.

_Verification: N2-8, N3-2 (high, both): grep of the 4-arg public constructor: only the test; try_create -> make_shared<book>(adopt_t{}, ..., amx_mirror_eligible) at :992-993._

#### `h/tron/models/kv_cache.hpp:772` **new** (B4)

```cpp
  770        size_t storage_slot_count,
  771        bool support_eagle,
  772*       [[maybe_unused]] bool amx_mirror_eligible) noexcept
  773    : n_pages(n_pages)
```

`model.hpp` spells this `tron_maybe_unused` two lines from your other change; same here (and at :1005)?

_Verification: kv_cache.hpp: 0 uses of tron_maybe_unused, 2 of raw [[maybe_unused]] (both new); model.hpp save_k uses tron_maybe_unused._

#### `h/tron/models/kv_cache.hpp:1039` R1-21 (A6/A3)

```cpp
 1039*     if (!amx_mirror_eligible || !amx_attn::available()) return;
 1040      size_t const bytes =
 1041          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1042              .kv_bytes /
 1043          2;
 1044      mirror_arena_.reset(static_cast<uint8_t*>(
 1045          ::operator new[](bytes, std::align_val_t(64), std::nothrow)));
 1046      // On failure the arena stays null and consumers fall back;
 1047      // see Note [K mirror parallel arena].
 1048    }
```

If `available()` is true and this `new` fails, we run a K_MIRROR build with no AMX QK at all (the canonical kernel is `#else`'d out in `apply_page_tok`) and nothing says so - silent bad performance instead of a loud error.  At least `spdlog::warn` once; better, keep `qk_canonical_128x4` as the fallback in the mirror build.  Also, `kv_bytes/2` of host RAM per book appears in neither `log_kv_footprint` nor `dma_size_bytes()`, and main's `Note [DMA-sized KV books]` (9076993a0) now says every buffer a book owns fits one DMA allocation - that Note needs the arena as an exception when you rebase.

_Verification: round 1 (R1-21), not addressed_

#### `h/tron/models/kv_cache.hpp:1042` R1-22 (A5)

```cpp
 1040      size_t const bytes =
 1041          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1042*             .kv_bytes /
 1043          2;
```

This `/ 2`, and the two in `mirror_at_storage`, are the `kv_block_planes` you just introduced, written as a literal.  Use it, or `static_assert(kv_block_planes == 2)` next to them, so the two can't drift.

_Verification: round 1 (R1-22), not addressed_

#### `h/tron/models/kv_cache.hpp:1217` R1-23 (B4/A5)

```cpp
 1217*   bf16* mirror_at_storage(
 1218        kv_storage_offset offset, size_t kv_head, size_t pg) noexcept {
 1219      if (!mirror_arena_) return nullptr;
 1220      constexpr size_t plane_bytes = page_size * geometry.head_size * sizeof(bf16);
 1221      TRON_ASSERT_LT(pg, n_pages);
 1222      TRON_ASSERT_LT(kv_head, geometry.n_kv_heads);
 1223      size_t byte_base;
 1224      if (offset.i < logical_slot_count()) {
 1225        byte_base = n_pages * (layout_t::offsets.values[offset.i] / 2);
 1226      } else {
 1227        byte_base = n_pages * (layout_t::offsets.values[logical_slot_count()] / 2);
 1228      }
 1229      return reinterpret_cast<bf16*>(
 1230          mirror_arena_.get() + byte_base + (kv_head * n_pages + pg) * plane_bytes);
 1231    }
```

`kv_block_at_storage` asserts `slot_matches<geometry>` and the EAGLE offset; this copy of its `byte_base` branch asserts nothing, so a mismatched geometry silently computes `plane_bytes` for the wrong head size and can run off the end of the arena.  Factor one `storage_byte_base<geometry>(offset)` helper used by both, so the mirror inherits the asserts.

_Verification: round 1 (R1-23), not addressed_

#### [blocker] `h/tron/models/kv_cache.hpp:1243` R1-18 (A5)

```cpp
 1241    template <kv_geometry geometry>
 1242    TRON(nodiscard, inline, pure)
 1243*   bf16* mirror(kv_slot_id slot, size_t kv_head, size_t pg) noexcept {
 1244      return mirror_at_storage<geometry>(kv_storage_offset(slot.i), kv_head, pg);
 1245    }
 1246  
 1247    template <kv_geometry geometry>
 1248    TRON(nodiscard, inline, pure)
 1249    const bf16* mirror(kv_slot_id slot, size_t kv_head, size_t pg) const noexcept {
 1250      return mirror_at_storage<geometry>(kv_storage_offset(slot.i), kv_head, pg);
 1251    }
```

This indexes the arena by the logical slot and never looks at `kv_blocks_alias`, but `page::k` does.  So under `set_storage_view(eagle_storage_offset())` (`full.hpp:1717`) the draft's `save_k` stores canonical K in the EAGLE physical slot while `set_k_mirror` scatters it into the validator's slot-0 plane.  Concretely: (1) validator writes token j of page p: physical slot 0 gets K_v, plane M(0) gets scatter(K_v); (2) draft, under the view, writes the same (p, j): physical slot L gets K_d, but M(0) := scatter(K_d); (3) the validator's next full-page decode runs `qk_mirror_128x4` on M(0) and scores against the draft's K.  The draft runs behind the validator on the same pages, so this hits every token older than the current validator batch, for the layer on slot 0; a page move repairs it (the rebuild reads canonical slot 0) until the draft saves again.  Meanwhile M(L) is only ever written by `copy_storage_slot` and never read.  `mirror()` needs to honour the view the same way `kv_block()` does (or assert no view is active while the arena exists), and the EAGLE-view test in `t_llama_unit.cpp` should check the mirror too.  I don't see the `mirror()` / `kv_blocks_alias` fix in this commit - it is still `kv_storage_offset(slot.i)` while `kv_block()` goes through the alias, and the draft still reaches `set_k_mirror` under the view with the validator's arena.  Is it coming as a follow-up on this PR?

_Verification: round 1 (R1-18), not addressed_

#### `h/tron/models/kv_cache.hpp:1487` R1-26 (A3)

```cpp
 1487*   // Raw pair-interleaved V storage of one (slot, kv_head) for this page,
 1488    // consumed as-is by the AMX PV kernel (TRON_AMX_DISPATCH).
 1489    template <kv_geometry geometry>
 1490      requires(book_t::template declares_geometry<geometry>())
 1491    TRON(nodiscard, inline, pure)
 1492    const bf16* v_data(kv_slot_id slot, size_t kv_head) const noexcept
 1493        TRON(this_lifetimebound)
 1494    {
 1495      return kv_block<geometry>(slot, kv_head).v_base();
 1496    }
```

This accessor (and `v_base()` at :2100) exists in every build, but the layout it describes exists only under `TRON_CHUNK_SIZE == 16`; the `#else` branch is plain `[p][i/C][i%C]`.  Guard the accessors the same way, or say so in the comment.

_Verification: round 1 (R1-26), not addressed_

#### `h/tron/models/kv_cache.hpp:1854` R1-27 (A7/B1)

```cpp
 1853  #ifdef TRON_AMX_K_MIRROR
 1854*       // Rebuild the mirror for the copied tokens from the destination's
 1855        // just-copied canonical K. This is THE defrag/page-move coherence
 1856        // site. See Note [K mirror coherence].
 1857        if (bf16* plane = book.template mirror_at_storage<geometry>(
 1858                storage_offset, kv_head, pageno())) {
 1859          for (size_t i = 0; i < count; ++i) {
 1860            detail::scatter_k_mirror<page_size, geometry.head_size>(
 1861                plane, dst_begin + i, dst + i * geometry.head_size);
 1862          }
 1863        }
```

One sentence here on who runs this and why concurrent readers are safe (scheduler thread under `tree_lock`; only fresh tokens at or past `tok_ct`; the mirror's only reader needs all 64 tokens live).  The 16-tokens-per-line layout means these stores touch lines that also hold live tokens' columns, which is exactly what the next reader will worry about.

_Verification: round 1 (R1-27), not addressed_

### h/tron/models/model.hpp

#### `h/tron/models/model.hpp:2764` **new** (A3)

```cpp
 2764*       // Mirror writes exist only for the shape the AMX kernels serve
 2765        // (amx_attn::shape_ok, compile-time: ineligible geometries compile no
 2766        // scatter) and only when AMX is available and not runtime-disabled
 2767        // (TRON_AMX_DISABLE): otherwise the kernel that reads the mirror never
 2768        // runs. See Note [K mirror parallel arena].
 2769        constexpr bool k_mirror_shape_ok =
 2770            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 2771        const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();
```

"Mirror writes exist only for the shape the AMX kernels serve" is true of this write site, not of mirror writes: `copy_storage_slot` (`kv_cache.hpp:1857`) and `fill_storage_slot` (`:1286`) scatter for any geometry whose plane exists, and a head-64 book from the legacy constructor has one (your own control case).  Scope the sentence to "the `save_k` write-through is compiled out for ineligible geometries", which is what the `if constexpr` below does.

_Verification: N2-6 (high)._

#### `h/tron/models/model.hpp:2771` R1-28 (A1/A8/B7)

```cpp
 2763  #ifdef TRON_AMX_K_MIRROR
 2764        // Mirror writes exist only for the shape the AMX kernels serve
 2765        // (amx_attn::shape_ok, compile-time: ineligible geometries compile no
 2766        // scatter) and only when AMX is available and not runtime-disabled
 2767        // (TRON_AMX_DISABLE): otherwise the kernel that reads the mirror never
 2768        // runs. See Note [K mirror parallel arena].
 2769        constexpr bool k_mirror_shape_ok =
 2770            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 2771*       const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();
```

This gates the write-through on `available()` only, but the only reader is behind `head_size == 128 && kv_mul == 4`.  On an AMX host running any other geometry (or any non-matching slot of a mixed layout) the RX worker pays the scatter (and `copy_storage_slot` the rebuild) and the book the `kv_bytes/2`, for planes nobody reads.  Gate the write, the rebuild, and the arena on the same predicate as the reader.  Also, `set_k_mirror` already no-ops on a null plane, so as written `k_mirror_on` is redundant with the arena condition rather than a correctness guard; the comment should say which it is.  And `model.hpp` calls `amx_attn::available()` without including its header.  Good on the gate.  Inside the `if constexpr`, `k_mirror_on` is just `available()`, and that is still redundant with the null check in `set_k_mirror`; say it is an early-out, or drop it.  Also, for an ineligible geometry `k_mirror_on` is now an unused local in a K_MIRROR build - `has_legacy_hardware_binding` two lines down needed `tron_maybe_unused` for exactly this shape; move the bool inside the `if constexpr`.  And `model.hpp` still doesn't include `amx_attn_iface.hpp` itself.

_Verification: round 1 (R1-28), partial: (1) The rebuild is not gated on the shape: kv_cache.hpp:1857-1858 `if (bf16* plane = book.template mirror_at_storage<geometry>(\n              storage_offset, kv_head, pageno())) {` still runs the scatter for every slot whenever the arena exists. (2) Per-slot cost in a mixed layout: amx_mirror_eligible is any-kernel-matches (kv_cache.hpp:184-187), and the arena is still `kv_bytes / 2` for all slots (kv_cache.hpp:1040-1043), so non-matching slots of an eligible model still pay the arena share and the copy_storage_slot rebuild. (3) The redundancy point: the comment model.hpp:2763-2768 says the write happens `only when AMX is available and not runtime-disabled (TRON_AMX_DISABLE): otherwise the kernel that reads the mirror never runs` but still does not say that `k_mirror_on`'s available() term is redundant with set_k_mirror's null-plane no-op (kv_cache.hpp:1520). (4) model.hpp still relies on the transitive include rather than including amx_attn_iface.hpp itself._

### h/tron/models/self_attention.hpp

#### `h/tron/models/self_attention.hpp:19` R1-29 (B15/B4)

```cpp
   14  #include "common/assert.hpp"
   15  #include "common/numerics/fp16.hpp"
   16  #include "common/util.hpp"
   17  #include "libpos.hpp"
   18  #include "spdlog/spdlog.h"
   19* #include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free; used when TRON_AMX_DISPATCH
   20  #include "tron/kernels/dotter.hpp"
   21  #include "tron/kernels/expr.hpp"
   22  #include "tron/kernels/page_share_counters.hpp"  // no-op unless TRON_PAGE_SHARE_COUNTERS
```

`kv_cache.hpp` guards its include of `amx_attn_iface.hpp` under the flag; here both new headers are unconditional.  Pick one convention.  Also, `<cstdint>` is now used directly (`uint16_t`, `uint64_t`) and not included.  The include convention is now 'unconditional in both', fine.  `<cstdint>` is still not included here.

_Verification: round 1 (R1-29), partial: `<cstdint>` is still not included in self_attention.hpp (grep 'cstdint' finds nothing; `uint16_t` used at :1361, `uint64_t` at :1366). Minor: the :19 trailing comment 'used when TRON_AMX_DISPATCH' is now inconsistent with the 'all builds' use of shape_ok that kv_cache.hpp:26 documents._

#### `h/tron/models/self_attention.hpp:1358` R1-30 (B6/B12)

```cpp
 1358*       constexpr bool amx_shape_ok =
 1359            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 1360        const bool amx_on = amx_shape_ok && amx_attn::available();
```

`head_size == 128 && kv_mul() == 4` is spelled here and twice more in `apply_page_tok` (1547, 1622) with bare `4`/`128`, and `amx_attn.cpp` has its own `HEAD_SIZE`/`GROUP_HEADS`.  Let's export the two constants (or a `constexpr bool supports(head_size, kv_mul)`) from `amx_attn_iface.hpp` and evaluate the predicate once.  Good.  Now that `shape_ok` owns the 128 and the 4, `static_assert(amx_attn::shape_ok(HEAD_SIZE, GROUP_HEADS))` in `amx_attn.cpp` would tie the kernels to the gate as well.

_Verification: round 1 (R1-30), partial: amx_attn.cpp:26 `constexpr int HEAD_SIZE = 128;  // dims per head` and :45 `constexpr int GROUP_HEADS = 4;` are still independent literals with nothing tying them to shape_ok (amx_attn.cpp is byte-identical to the old head; not in delta.diff). Inside apply_page_tok the predicate is still spelled at two sites (:1547 and :1622) rather than evaluated once into a local._

#### `h/tron/models/self_attention.hpp:1361` R1-31 (A1/B7)

```cpp
 1361*       thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::q_pack_elems);
 1369          amx_attn::begin_region();
 1370        }
```

Why lazy?  Packing all `items.size()` groups once before the page loop is at most `max_minibatch_size` 512-byte copies and deletes the bitmap and the per-(page, token) test-and-set.  If a cache is really wanted, `attn_accum` is already per worker, per token and 64B-aligned; a growable `thread_local std::vector` is neither aligned (see the header contract) nor bounded the way the mask next to it is.

_Verification: round 1 (R1-31), not addressed_

#### `h/tron/models/self_attention.hpp:1362` R1-32 (A5)

```cpp
 1362*       // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
```

The comment says `items.size() <= max_minibatch_size`; who enforces it?  (`batch_evenly` does, `model.hpp:326`, but it's a long way from here - a `TRON_ASSERT_LE(items.size(), max_minibatch_size)` next to the mask costs nothing.)

_Verification: round 1 (R1-32), not addressed_

#### `h/tron/models/self_attention.hpp:1367` R1-34 (B6/A12)

```cpp
 1367*       if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::q_pack_elems);
 1369          amx_attn::begin_region();
 1370        }
```

We have `tron::finally` (`h/common/util.hpp:73`, used in `gof.hpp:221`) for exactly this bracket; `tron::finally release([&] { if (amx_on) amx_attn::end_region(); });` makes the pairing structural.  Not a bug today (the function is `noexcept` and there is no return in between), your choice.

_Verification: round 1 (R1-34), not addressed_

#### `h/tron/models/self_attention.hpp:1414` R1-33 (A13/B11)

```cpp
 1414*               // Pack lazily: select the token's mask word (batch_job_ix / 64
 1415                // via >> 6), shift its bit (batch_job_ix % 64 via & 63) down to
 1416                // bit 0, and test it. Bit clear = this token's Q group is not
 1417                // packed yet; pack it once and set the bit, so every later
 1418                // page in the range reuses the pack.
 1419                if (!((amx_packed_mask[batch_job_ix >> 6] >> (batch_job_ix & 63)) & 1)) {
```

The declaration comment already explains the word/bit split; this second explanation of `>> 6` and `& 63` is more than the two operators deserve.  Flush.

_Verification: round 1 (R1-33), not addressed_

#### `h/tron/models/self_attention.hpp:1493` R1-35 (A12/A9)

```cpp
 1493*         const uint16_t* amx_q_packed = nullptr) {
 1494        constexpr size_t operation_kv_mul = geometry.kv_mul();
 1495        constexpr size_t operation_head_size = geometry.kv.head_size;
 1496        const attention_binding binding = operation.binding;
 1497        const kv_slot_id slot = binding.kv_slot;
 1498        tensor<operation_kv_mul, page::page_size> s_pages;
 1499        int relevant_k_tokens = 0;
 1500        bool did_amx = false;
```

The default is never used (the one caller always passes `amx_qp`), and in a build without the flag the parameter is unreferenced - does the default build now warn under `-Wextra`?  CI didn't run, so I can't tell.  Drop the default, and I'd rather the OFF build's `apply_page_tok` were textually unchanged (parameter and `did_amx` under the flag).

_Verification: round 1 (R1-35), not addressed_

#### `h/tron/models/self_attention.hpp:1502` R1-36 (A8/A3)

```cpp
 1501        {
 1502*         // share the bf16 -> fp32 conversion across the page
 1503          using scalar_t = typename btensor_t<operation_head_size>::element;
 1504          for (size_t offset = 0; offset < operation_kv_mul; ++offset)
 1505            s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f);
```

On the pages AMX takes, the four `dotter` constructions here (16 zmm loads) and the `-inf` init of `s_pages` are dead work per (page, token); moving them under `if (!did_amx)` is free.  Also, "share the bf16 -> fp32 conversion" describes `dotter<float, 128>`; the `dotter<bf16, 128>` used here converts nothing.  Pre-existing, but you're touching it.

_Verification: round 1 (R1-36), not addressed_

#### `h/tron/models/self_attention.hpp:1558` R1-37 (A4/A8)

```cpp
 1558*             if (const bf16* mplane =
 1559                      page.template k_mirror_data<geometry.kv>(slot, kv_head)) {
 1560                alignas(
 1561                    64) thread_local float qk_s[amx_attn::tile_rows * page::page_size];
 1562                amx_attn::qk_mirror_128x4(
 1563                    reinterpret_cast<const uint16_t*>(mplane), amx_q_packed, qk_s);
 1564                std::memcpy(&s_pages[0][0], qk_s,
 1565                    operation_kv_mul * page::page_size * sizeof(float));
```

So the mirror path pays a 1 KB copy per page that the canonical path doesn't, and the `amxqk` bench variant behind the 686 ns figure stores straight into a 16-row `S` with no copy.  Either size `s_pages` for 16 rows in the mirror build, or note the copy's cost next to the 300 ns claim.  Also, when `mplane` is null in this build we fall all the way to the dotter although `qk_canonical_128x4` is compiled into the same binary - why not fall back to it?

_Verification: round 1 (R1-37), not addressed_

#### `h/tron/models/self_attention.hpp:1618` R1-38 (B11/B6)

```cpp
 1615        //
 1616        // The if-constexpr is runtime-redundant with did_amx (which is only
 1617        // ever set under the same condition, in the QK block above) but
 1618*       // deliberate: without it this 4-head/128-dim softmax-update block would still be
 1619        // COMPILED into every other geometry's instantiation as dead code,
 1620        // and its group-width assumptions would no longer be pinned to the
 1621        // same compile-time gate that guards the QK side.
 1622        if constexpr (amx_attn::shape_ok(operation_head_size, operation_kv_mul)) {
```

This paragraph is justifying the code to the reviewer; "`if constexpr` so other geometries don't instantiate this block" is the whole content.  Flush the rest.  Also, pass 1 is a second copy of the per-head scale/softcap/max/exp/sum math below (I diffed them; identical today) - that is how they drift.  Pull the per-head part into a helper both loops call.

_Verification: round 1 (R1-38), not addressed_

#### `h/tron/models/self_attention.hpp:1651` R1-39 (A8)

```cpp
 1649            for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
 1650              scratchpad_ref<geometry> head_sp = sp[kv_head * operation_kv_mul + offset];
 1651*             tensor<operation_head_size> scratch;
 1652              std::memcpy(&scratch[0], amx_o + offset * operation_head_size,
 1653                  operation_head_size * sizeof(float));
 1654              if (was_valid) {
 1655                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1656                head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
```

Any reason not to point a `const_view<float, true, false, seq<128>>` at `amx_o + offset * 128` instead of copying 512 B per head into `scratch`?  The AVX path feeds `fma` an expression for the same reason.

_Verification: round 1 (R1-39), not addressed_

#### `h/tron/models/self_attention.hpp:1656` R1-40 (A5)

```cpp
 1654              if (was_valid) {
 1655                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1656*               head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
 1657                head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
```

`constant<page::page_size>` (64 wide) as the multiplier in a 128-wide `fma` only works because `constant::chunk(i)` ignores `i`.  Pre-existing at :1685, but let's not copy it: `constant<operation_head_size>`.

_Verification: round 1 (R1-40), not addressed_

### h/tron/scheduler/full.hpp

#### `h/tron/scheduler/full.hpp:310` **new** (A12/B4)

```cpp
  306    bool support_eagle = false;
  307    // Whether the model has an AMX-eligible attention shape (see
  308    // amx_mirror_eligible in kv_cache.hpp); handed to every KV book this tree
  309    // creates so ineligible models allocate no K mirror arena.
  310*   bool amx_mirror_eligible = true;
  311  
```

Every constructor sets this, so the `= true` is dead, and `true` is the unsafe direction for a default (see the constructor comment in `kv_cache.hpp`).  If the file's convention is to give these members a default, make it `false`.

_Verification: Siblings logical_kv_slots/storage_kv_slots/support_eagle carry the same dead-default pattern (pre-existing); the objection is to adding a true-by-default one._

#### `h/tron/scheduler/full.hpp:1456` **new** (B3)

```cpp
 1451            cache_t::logical_slot_count_for_layers(max_layers);
 1452        const size_t storage_kv_slots =
 1453            cache_t::storage_slot_count_for_layers(max_layers, cfg->support_eagle);
 1454        root = std::make_shared<node_t>(logical_kv_slots, storage_kv_slots,
 1455            cfg->support_eagle,
 1456*           amx_mirror_eligible(model_t::plugin_t::attention_kernels));
 1457      }
```

`amx_mirror_eligible` is now the name of the predicate over kernels, a `node_base` member, and two constructor parameters.  Inside `node` methods the member shadows the function.  `has_amx_attention_shape(kernels)` for the predicate would keep them apart.

_Verification: grep: 27 occurrences across h/ src/ t/ under one name._

### src/tron/CMakeLists.txt

#### `src/tron/CMakeLists.txt:170` R1-41 (A3)

```cmake
  166  # AMX software-attention dispatch. The kernel bodies live in one
  167  # isolated translation unit that alone receives the -mamx-* flags; the rest of
  168  # the tree sees only the intrinsics-free interface header plus the
  169  # TRON_AMX_DISPATCH definition that enables the fast-path call sites.
  170* option(TRON_AMX_DISPATCH "Enable AMX software-attention dispatch (Granite Rapids)" OFF)
```

AMX-BF16 is Sapphire Rapids and later, and the code gates on CPUID bits, not the model.  s/(Granite Rapids)/(requires AMX-BF16)/.

_Verification: round 1 (R1-41), not addressed_

#### `src/tron/CMakeLists.txt:183` R1-42 (A1)

```cmake
  181  if(TRON_AMX_DISPATCH)
  182    target_sources(tron PRIVATE kernels/amx_attn.cpp)
  183*   set_source_files_properties(kernels/amx_attn.cpp PROPERTIES
  184      COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
  185    target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)
```

Only `-mamx-tile -mamx-bf16` are new for this TU; the `-mavx512*`/`-mavx2`/`-mfma` are already PUBLIC on `tron` (:234-237) unless `AVX512=OFF`, in which case this would be the only AVX-512 code in a non-AVX-512 binary.  Is that build meant to exist?  If not, trim the list; if so, say so.

_Verification: round 1 (R1-42), not addressed_

### src/tron/kernels/amx_attn.cpp

#### `src/tron/kernels/amx_attn.cpp:7` R1-43 (B15)

```cpp
    7* #include <atomic>
    8  #include <cstdlib>
    9  #include <cstring>
   10  #include <immintrin.h>
   11  #include <unistd.h>
```

Unused?

_Verification: round 1 (R1-43), not addressed_

#### `src/tron/kernels/amx_attn.cpp:26` R1-44 (B6/A5)

```cpp
   25  constexpr int PAGE = 64;        // tokens per KV page
   26* constexpr int HEAD_SIZE = 128;  // dims per head
   27  // Region tile shape: begin_region() configures all 8 tiles as 16 rows x
   28  // 64 bytes (mirrored as amx_attn::tile_rows in the interface header).
   29  constexpr int N_TILES = 8;
   30  constexpr int TILE_ROWS = 16;
   31  constexpr int TILE_ROW_BYTES = 64;
```

Ditto: `TILE_ROWS`/`TILE_ROW_BYTES` duplicate `tile_rows`/`tile_row_bytes` from the header this file includes, and `PAGE` duplicates `page::page_size` with nothing tying them together.

_Verification: round 1 (R1-44), not addressed_

#### `src/tron/kernels/amx_attn.cpp:32` R1-45 (A13)

```cpp
   32* // One stored tile's worth of fp32 scores (16 rows x 16 values).
   33  // sizeof(float) rather than a literal 4: the constant converts tile bytes
   34  // into elements of the float arrays it indexes, so the element size belongs
   35  // to that type. C++ does not formally fix sizeof(float), but every tron
   36  // target does (the AVX-512 *_ps intrinsics and the fp32 tile accumulators
   37  // require IEEE 32-bit float); the static_assert pins the assumption.
   38  // (C++23 has std::float32_t, but tron's kernel convention is plain float
   39  // for fp32 throughout.)
```

Eight lines of prose for `static_assert(sizeof(float) == 4)`.  I can smell Claude patting itself on the back a mile away.  The message string says everything the assert needs to say; flush the paragraph.

_Verification: round 1 (R1-45), not addressed_

#### `src/tron/kernels/amx_attn.cpp:43` R1-46 (B3/B12)

```cpp
   42  // TDPBF16PS consumes the head dim in 32-dim steps (16 bf16 pairs per step).
   43* constexpr int DIM_STEP = 32;
   44  // Query heads per KV head - the GQA group width, the "x4" in the kernel names.
   45  constexpr int GROUP_HEADS = 4;
```

`DIM_STEP` is documented as 32 head dims per k-step, but at :210 it means 32 tokens per PV k-step and at :211 it means 16 dims x 2 paired tokens per V tile column.  Three quantities with the same numeral shouldn't share a constant; name the other two.  Also, the `4` at :251 is `PAGE / TILE_ROWS`.

_Verification: round 1 (R1-46), not addressed_

#### `src/tron/kernels/amx_attn.cpp:62` R1-47 (B6)

```cpp
   62* bool detect_and_request() noexcept {
   63    // Runtime kill switch for same-binary A/B tests and emergency disable.
   64    const char* off = std::getenv("TRON_AMX_DISABLE");
   65    if (off && off[0] == '1') return false;
   66    unsigned a, b, c, d;
   67    // CPUID leaf 7.0 EDX: bit 22 AMX-BF16, bit 24 AMX-TILE
   68    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(7), "c"(0));
   69    if (!((d >> 22) & 1) || !((d >> 24) & 1)) return false;
```

You know we have `cpuid_bit(leaf, reg, bit)` in `h/system/mwaitx.hpp:22`, and that `is_rtm_supported` (`lazy<bool>` + `TRON_NO_RTM=1`) is the same shape as this whole function, right?  Reuse it, or say why the AMX probe can't.

_Verification: round 1 (R1-47), not addressed_

#### `src/tron/kernels/amx_attn.cpp:64` R1-48 (A6/B17)

```cpp
   63    // Runtime kill switch for same-binary A/B tests and emergency disable.
   64*   const char* off = std::getenv("TRON_AMX_DISABLE");
   65    if (off && off[0] == '1') return false;
   66    unsigned a, b, c, d;
```

This is a first-character test: `TRON_AMX_DISABLE=true` leaves AMX on, silently.  Nearest precedents are `strcmp(v, "1") == 0` (`TRON_NO_RTM`, `TRON_USE_ARENA_ALLOCATOR`) or `atoi(v) > 0` (`USE_HW_ATTN`); pick one.

_Verification: round 1 (R1-48), not addressed_

#### `src/tron/kernels/amx_attn.cpp:106` R1-49 (A8)

```cpp
  105  void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept {
  106*   std::memset(packed, 0, q_pack_elems * sizeof(uint16_t));
  107    // One panel per 32-dim step; see the layout contract at the declaration.
  108    for (int step = 0; step < HEAD_SIZE / DIM_STEP; step++) {
  109      for (int dim_pair = 0; dim_pair < DIM_STEP / 2; dim_pair++) {
```

Each pack memsets 4 KB to write 512 B; columns 4..15 never change.  The `P` buffer below zeroes its padding once per thread - same discipline here?

_Verification: round 1 (R1-49), not addressed_

#### `src/tron/kernels/amx_attn.cpp:200` R1-50 (B1)

```cpp
  196    for (int q = 0; q < GROUP_HEADS; q++) {
  197      for (int c = 0; c < PAGE; c += 32) {
  198        __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
  199        __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
  200*       _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
  201      }
```

A one-line comment that `cvtne2ps_pbh(a, b)` puts `b` in the low half would save the next reader the lookup.

_Verification: round 1 (R1-50), not addressed_

### src/amx_fused_bench.cpp

#### [blocker] `src/amx_fused_bench.cpp:3` R1-51 (B6/B8/A9)

```cpp
    1  // amx_fused_bench.cpp — fused-page software-attention benchmark.
    2  //
    3* // Self-contained (no tron includes; compiles with plain g++), but uses the
    4  // EXACT tron kv_block layouts so numbers transfer:
    5  //   K page: [64 tokens][128 dims] bf16 row-major, row stride 256 B
    6  //   V page: [32 pairs][128 dims][2] bf16 token-pair-interleaved (AMX B format)
    7  // and replicates the shipping kernels' instruction patterns for the AVX
    8  // baseline (dotter: 4x vdpbf16ps + hreduce per (token, query);
```

A 732-line `main()` in `src/` that no CMake target builds, which re-implements every shipped kernel by hand (`pack_q`, `qk_amx`, `qk_amx_rowmajor`, `pv_amx`, `pack_k_mirror`, `st_to_s`).  Any kernel fix now has to be made twice, and the numbers quoted in `Note [Mirror orientation]` were measured on the copy, not on `amx_attn.cpp`.  Either make it a `t/` benchmark target that links `libtron` and calls the real kernels, or take it out of the tree and keep the numbers in the doc with the command line that produced them.  A second copy of every kernel in `src/` is not something I want to approve.

_Verification: round 1 (R1-51), not addressed_

#### `src/amx_fused_bench.cpp:22` R1-52 (A3)

```cpp
   22* // Variants:
   23  //   avx     : dotter-pattern QK + shared softmax + scaled_v-pattern PV
   24  //   amx44   : our fused AMX path, PV output blocking 4+4
   25  //   amx62   : our fused AMX path, PV output blocking 6+2
   26  // Usage: amx_fused_bench [Nq] [iters] [variant] [pages]
```

`amxqk` and `amxpl` are missing from this list (and `amx_attn.cpp:230` cites `amxqk`).

_Verification: round 1 (R1-52), not addressed_

#### `src/amx_fused_bench.cpp:31` R1-53 (A3/A11)

```cpp
   30  // Correctness: every variant is checked against a scalar reference once
   31* // (rel tol 2e-2, matching t_amx_attention practice) before timing.
```

There is no `t_amx_attention` on main; it lives on `bill-amx`.  Also 2e-2 relative is a long way from the `1e-4 * abs_mass` `t_amx_numerics` uses in this same PR, so "practice" is doing a lot of work here.  Flush the clause.

_Verification: round 1 (R1-53), not addressed_

#### `src/amx_fused_bench.cpp:75` R1-54 (A3)

```cpp
   74  // fast exp used IDENTICALLY by all variants (so softmax cost is comparable):
   75* // exp(x) via exp2(x * log2e), 2^i * poly(f). Max rel err ~2e-7, fine at tol 2e-2.
   76  static inline __m512 vexp(__m512 x) {
```

The degree-5 Taylor terms give ~3.3e-6 at |f| = 0.5 (I checked), not 2e-7.  Fix the number or delete the sentence; the conclusion holds either way.

_Verification: round 1 (R1-54), not addressed_

#### `src/amx_fused_bench.cpp:120` R1-55 (B2)

```cpp
  119  // ---------- 16x16 fp32 transpose (validated against reference below) ----------
  120* static inline void transpose16x16(
  121      const float* src, int src_stride_f, float* dst, int dst_stride_f) {
```

Neither `transpose16x16` nor its reference is used by any variant (`st_to_s` has its own copy); they exist to validate each other.  Flush all three pieces.

_Verification: round 1 (R1-55), not addressed_

#### `src/amx_fused_bench.cpp:264` R1-56 (A3/B11)

```cpp
  261  // Q pack: Q[nq][128] bf16 -> 4 B panels, each 16 rows x 64 B:
  262  // panel s, row dp (dim pair), lane q: { Q[q][s*32+2dp], Q[q][s*32+2dp+1] },
  263  // lanes q>=nq zeroed (padding).
  264* static void pack_q(const bf16* Q, int nq, bf16* Bp /*4*16*64 bf16? bytes*/) {
  265    std::memset(Bp, 0, 4 * 16 * 64);
```

A question mark in a size comment means we don't know the size.  It's 4*16*32 bf16 = 4*16*64 bytes; write one.  Also, s/(Bill's formulation)// at :279 - same as the "ours" in the header Note.

_Verification: round 1 (R1-56), not addressed_

### t/CMakeLists.txt

#### [blocker] `t/CMakeLists.txt:190` R1-57 (A10/B8)

```cmake
  189  endif()
  190* add_catch_test(NAME t_amx_logit_ab FILES t_amx_logit_ab.cpp force_generate.cpp LIBRARIES tron full_scheduler PROPERTIES RESOURCE_LOCK fpga LABELS fpga)
  191  add_catch_test(NAME t_generate_mock FILES t_generate_mock.cpp testutil.cpp force_generate.cpp LIBRARIES tron pos_fake mock_scheduler PROPERTIES main LABELS fake)
```

This is registered under `LABELS fpga`, so `bin/slice run --filter=fpga` (the Test FPGA job), `make test`, and `ctest -L fpga` all select it, and its first line is `REQUIRE(getenv("AMX_LOGIT_OUT") != nullptr)`.  The FPGA lane fails the moment CI runs on this PR.  It's a dump tool, not a test (its one `SUCCEED` asserts nothing about AMX): make it a `runtron`/`tronutil` flag or a `bin/` script and drop the ctest entry; if it stays, `DISABLED TRUE` like `t_clearhbm`.  Also, it defaults to `ingested-llama-3.1-8b` but sits outside `if(BUILD_INGEST_MODELS)`.

_Verification: round 1 (R1-57), not addressed_

#### [blocker] `t/CMakeLists.txt:359` R1-58 (A4/A10/B14)

```cmake
  358  add_catch_test(NAME t_llama_unit LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  359* add_catch_test(NAME t_amx_mirror LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  360  add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  361  add_catch_test(NAME t_amx_arena_leak LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```

In the default build all three of these are a single `SUCCEED("...skipped")`, and even with the options on they `WARN` and return on a non-AMX host - so after merge nothing in CI compiles or runs the flagged code.  How was this validated, given `make test` has no coverage for it?  At minimum a compile-only configuration with both options ON (precedent: `heterogeneous_scheduler_compile`, :351) so the `#ifdef`'d code can't rot silently; the run log from the 6962P host in the PR would also help.

_Verification: round 1 (R1-58), not addressed_

### t/t_amx_arena_leak.cpp

#### `t/t_amx_arena_leak.cpp:48` R1-59 (A1)

```cpp
   46  // Global replacements of the aligned array forms. Allocation and
   47  // deallocation both route through aligned_alloc/free so every replaced form
   48* // stays pair-compatible with every other.
   49  void* operator new[](std::size_t n, std::align_val_t al) {
   50    void* p = counted_aligned_alloc(n, al);
   51    if (!p) throw std::bad_alloc{};
   52    return p;
   53  }
```

What failure is this guarding against?  `unique_ptr` with `mirror_delete` frees by construction, and a new[]/delete[] form mismatch is what the ASan build is for.  Replacing the global aligned `operator new[]` in a test binary is a lot of mechanism for that; if it stays, `memperf.cpp` already replaces the same forms.

_Verification: round 1 (R1-59), not addressed_

#### `t/t_amx_arena_leak.cpp:89` **new** (A3)

```cpp
   88    if (tron::amx_attn::available()) {
   89*     // The arena allocation actually ran (maybe_allocate_mirror_arena is
   90      // gated on available()), so the balance above covered it.
   91      REQUIRE(alloc_delta >= 1);
```

s/gated on available()/gated on the eligibility flag (true through the 3-argument form) and available()/.

_Verification: N3-8 (low): kv_cache.hpp:1039 now tests both._

#### `t/t_amx_arena_leak.cpp:91` R1-60 (A10)

```cpp
   88    if (tron::amx_attn::available()) {
   89      // The arena allocation actually ran (maybe_allocate_mirror_arena is
   90      // gated on available()), so the balance above covered it.
   91*     REQUIRE(alloc_delta >= 1);
   92    } else {
   93      WARN("AMX unavailable on this host - the mirror arena never allocates, so "
   94           "only the trivial balance was checked");
   95    }
```

Can we tighten this to `== 1`?  With an example this small the count is predictable.  The new case does `== 1` (:133); this one still says `>= 1`.  Ditto.

_Verification: round 1 (R1-60), not addressed_

#### `t/t_amx_arena_leak.cpp:105` **new** (A3/B6)

```cpp
  100    // The gate the scheduler evaluates per model, on the shapes that exist in
  101    // the registry: gpt-oss-20b (64 q-heads / 8 KV heads / head 64) fails both
  102    // halves, llama-3.2-1b (ratio 4, head 64) fails the head size,
  103    // llama-3.3-70b (head 128, ratio 8) fails the ratio; qwen/llama-3.1
  104    // (ratio 4, head 128) pass.
  105*   static_assert(!tron::amx_attn::shape_ok(64, 8));
  106    static_assert(!tron::amx_attn::shape_ok(64, 4));
  107    static_assert(!tron::amx_attn::shape_ok(128, 8));
  108    static_assert(tron::amx_attn::shape_ok(128, 4));
```

These four evaluate `128 == 128 && 4 == 4` in four spellings; they can only fail if someone edits `shape_ok`.  If the point is that the registry shapes classify correctly, read them from `named_llama_configs::llama_3p2_1b` / `llama_3p1_8b` / `llama_3p1_70b` so the test follows the tree - and s/llama-3.3-70b/`llama_3p1_70b`/, which is the config that has this geometry.  gpt-oss and qwen-3-4b have no C++ geometry here, so say so or drop them.

_Verification: N3-5, N3-6: llama.hpp:1538-1539 geometries verified; 'llama-3.3-70b' is a models.yaml slug of llama_3p1_70b; static_assert inside TEST_CASE has precedent (t_fp32.cpp:1328) and is not the point._

#### `t/t_amx_arena_leak.cpp:123` **new** (A10/B14)

```cpp
  118    // A head-64 book built the way the scheduler builds it for an ineligible
  119    // model: the 4-argument constructor with amx_mirror_eligible=false must
  120    // perform no arena allocation, whether or not this host has AMX.
  121    const long long before_ineligible = aligned_array_allocs.load();
  122    {
  123*     tron::book<2, 1, 64, 0> cache(/*n_pages=*/4, /*storage_slot_count=*/2,
  124          /*support_eagle=*/false, /*amx_mirror_eligible=*/false);
  125      REQUIRE(aligned_array_allocs.load() - before_ineligible == 0);
  126    }
```

"built the way the scheduler builds it" - the scheduler goes through `try_create` (`full.hpp:832`) into the adopt-constructor, which this doesn't touch; this constructor's only caller is this test.  Can both arms run through `book_t::try_create(4, 2, false, false)` / `(4, 2, false, true)`, so the pair differs only in the flag and the plumbing we ship is what gets tested?  And a `static_assert(amx_mirror_eligible(llama<...>::attention_kernels))` on a real plugin array would test what the case name says.  Also, on a non-AMX host the `== 0` at :125 holds for either flag value, so the only discriminating half is the one we `WARN` past - where does this run with AMX?

_Verification: N1-2, N2-11, N3-7, N3-4 (all high/medium): grep t/ for try_create finds only 3-arg forms; production path try_create(4-arg) -> adopt ctor -> maybe_allocate_mirror_arena is untested; on non-AMX hosts the early return fires before the flag is read._

#### `t/t_amx_arena_leak.cpp:132` **new** (A10/A12)

```cpp
  126    }
  127    // Control: the same book through the legacy constructor (eligible by
  128    // default) does allocate when AMX is available - so it is the flag, not
  129    // the geometry, that the arena decision follows.
  130    if (tron::amx_attn::available()) {
  131      const long long before_control = aligned_array_allocs.load();
  132*     tron::book<2, 1, 64, 0> control(/*n_pages=*/4);
  133      REQUIRE(aligned_array_allocs.load() - before_control == 1);
  134    } else {
```

This control case is the argument against the legacy constructor: a head-64 book gets an arena no kernel can read, and the test enshrines it.  Once the 3-argument form is gone, the control becomes `book<...>(4, 2, false, true)` and says what it means.

_Verification: Ties to the kv_cache.hpp:764 comment._

### t/t_amx_mirror.cpp

#### `t/t_amx_mirror.cpp:28` R1-61 (A11/B6/B8)

```cpp
   23  // The layout contract from detail::scatter_k_mirror:
   24  //   plane[(((s * (page_size/16) + c) * 16 + dp) * 16 + t) * 2 + j]
   25  //     == flat_k[(c*16 + t) * head_size + s*32 + 2*dp + j]
   26  template <size_t page_size, size_t head_size>
   27  void require_mirror_matches(const uint16_t* flat_k, const uint16_t* plane) {
   28*   for (size_t s = 0; s < head_size / 32; ++s) {
   29      for (size_t c = 0; c < page_size / 16; ++c) {
   30        for (size_t dp = 0; dp < 16; ++dp) {
   31          for (size_t t = 0; t < 16; ++t) {
   32            for (size_t j = 0; j < 2; ++j) {
   33              const size_t mi = (((s * (page_size / 16) + c) * 16 + dp) * 16 + t) * 2 + j;
   34              const size_t ki = (c * 16 + t) * head_size + s * 32 + 2 * dp + j;
   35              REQUIRE(plane[mi] == flat_k[ki]);
```

The reference here is the implementation's own index formula, so a layout change applied to both passes; the only test that ties the plane to its consumer (`qk_mirror_128x4`) is hardware-gated.  A scalar model of the kernel's panel addressing would pin the layout to the reader on any host.  Also, this is the fourth copy of the formula (Note, `scatter_k_mirror`, here, `t_llama_unit.cpp:440`); a `require_mirror_matches` in a `t/` header used by both tests would leave two.

_Verification: round 1 (R1-61), not addressed_

#### `t/t_amx_mirror.cpp:80` R1-62 (B18)

```cpp
   78  TEST_CASE("K mirror is byte-equivalent to canonical K", "[kv_data][amx_mirror]") {
   79    run_case<128>();  // qwen/llama head size (the AMX fast-path shape)
   80*   run_case<64>();   // smaller-head geometry
   81  }
```

Which consumer reads a head-64 plane?  Dispatch requires head 128, so this is 8192 `REQUIRE`s guarding data nobody reads - the same point as the write-through gate in `model.hpp`: don't maintain planes no kernel consumes, and this case goes away.  Still here.  Through the scheduler a head-64 book no longer has a plane at all, so this case now tests a layout only the legacy constructor can produce - one more reason to flush that constructor.

_Verification: round 1 (R1-62), partial: run_case<64>() at t_amx_mirror.cpp:80 is still present. Head-64 planes are still maintained on the other write paths: kv_cache.hpp:1857-1862 (copy_storage_slot rebuild) and :1286-1290 (fill_random rebuild) scatter for every geometry with no shape_ok gate, and the legacy 3-argument book constructor still allocates an arena for head-64 (t_amx_arena_leak.cpp:132-133 asserts "book<2, 1, 64, 0> control(4)" allocates exactly 1)._

### t/t_amx_numerics.cpp

#### `t/t_amx_numerics.cpp:1` R1-63 (A11)

```cpp
    1* // Precision regression tests for the AMX attention kernels: the AMX QK and
    2  // PV outputs must not digress from the AVX path beyond the documented
    3  // numerics contract (see Note [AMX attention dispatch]): both engines are
    4  // bf16-in/fp32-accumulate, so admissible A/B deltas are ONLY
    5  //   (a) fp32 accumulation order, and
    6  //   (b) for PV, the weight rounding mode - AVX scaled_v truncates
    7  //       fp32->bf16, AMX rounds to nearest even.
    8  // Each check pins a kernel to the AVX side (the real dotter for QK, an
```

Nice - a real reference on both sides, in double.

_Verification: round 1 (R1-63), not addressed_

#### `t/t_amx_numerics.cpp:32` R1-65 (B3/B15)

```cpp
   31  constexpr size_t PAGE = 64;
   32* constexpr size_t HD = 128;
   33  
```

We renamed this `HEAD_SIZE` in the kernel TU; same here (and in the bench)?  Also `std::make_unique` without `<memory>`.

_Verification: round 1 (R1-65), not addressed_

#### `t/t_amx_numerics.cpp:82` R1-66 (B12)

```cpp
   82*     alignas(64) uint16_t q_packed[4 * 16 * 32];
   83      tron::amx_attn::pack_q_group_128x4(in->q, q_packed);
   84      alignas(64) float s_amx[4][PAGE];
```

`q_pack_elems` exists for this.

_Verification: round 1 (R1-66), not addressed_

#### `t/t_amx_numerics.cpp:105` R1-64 (A11/A13)

```cpp
   97          // Both engines sum the same 128 exact bf16xbf16 products in fp32;
   98          // only the accumulation order differs. Envelope: a small multiple
   99          // of fp32 epsilon times the absolute-product mass.
  100          double abs_mass = 0;
  101          for (size_t d = 0; d < HD; ++d) {
  102            abs_mass += std::fabs(double(bf16_to_float(in->q[qi * HD + d])) *
  103                                  double(bf16_to_float(in->k[t * HD + d])));
  104          }
  105*         const double tol = 1e-4 * abs_mass + 1e-6;
  106          REQUIRE(std::fabs(double(s_amx[qi][t]) - double(s_avx)) <= tol);
```

The reorder bound for 128 exact products summed in fp32 is 127 ulp = 7.6e-6 of the mass, so 1e-4 is 13x looser than the math allows, and the comment calls it "a small multiple of fp32 epsilon" (it's ~1700).  Where does 1e-4 come from?  Tighten to a few times the bound, or state the measured maximum and why the margin.  Ditto :209.

_Verification: round 1 (R1-64), not addressed_

#### `t/t_amx_numerics.cpp:144` R1-67 (A3)

```cpp
  142    // Both orientations reduce the head dim in the same 4x32 step order with
  143    // the same dim pairing, so TDPBF16PS produces the identical fp32 sums -
  144*   // the system-level regression check (mirror greedy output byte-identical
  145    // to canonical-AMX) rests on this. A failure here means the orientations'
  146    // accumulation orders diverged, which invalidates that equivalence.
```

Where does that check live?  Nothing in the tree performs it (`t_amx_logit_ab` only dumps).  Name it or delete the sentence; the local assertion stands on its own.

_Verification: round 1 (R1-67), not addressed_

### t/t_llama_unit.cpp

#### `t/t_llama_unit.cpp:427` R1-68 (B14/A10)

```cpp
  427* #ifdef TRON_AMX_K_MIRROR
  428    // After fill_random and append (the defrag rebuild path), the K mirror
  429    // plane must stay byte-equivalent to canonical K for every token;
  430    // see Note [K mirror coherence].
  431    // The plane lives in the book's parallel arena, which exists only when AMX
  432    // is available at runtime - skip (with a visible note) on non-AMX hosts.
  433    if (destination_page->template k_mirror_data<geometry_128>(kv_slot_id(1), 1) ==
  434        nullptr) {
  435      WARN("mirror arena absent (AMX unavailable) - mirror coherence not checked");
  436    } else {
  437      const auto* mirror = reinterpret_cast<const uint16_t*>(
  438          destination_page->template k_mirror_data<geometry_128>(kv_slot_id(1), 1));
  439      for (size_t i = 0; i < cache_t::page_size; ++i) {
  440        const auto* row = reinterpret_cast<const uint16_t*>(
```

IIUC only token 0 of this page came through `copy_storage_slot` (append copied 64 tokens into page 0 and one into page 1, and `destination` never advanced `tok_ct`); tokens 1..63 here were rebuilt by `fill_random`.  So the defrag rebuild is checked for `i == 0, dst_begin == 0` only - a dropped `dst_begin + i` or a wrong `dst + i * head_size` stride passes.  Check page 0 too, and do one append into a destination whose `tok_ct` is not a multiple of 64.

_Verification: round 1 (R1-68), not addressed_

#### `t/t_llama_unit.cpp:1226` R1-69 (B14/A10)

```cpp
 1225    constexpr size_t head_size = 128;
 1226*   constexpr size_t n_heads = 16;
 1227    constexpr size_t dim = head_size * n_heads;
 1228    constexpr size_t hidden_dim = 1024;
 1229    constexpr size_t n_layers = 2;
 1230    constexpr size_t n_kv_heads = 8;
 1231    constexpr size_t kv_mul = n_heads / n_kv_heads;
```

I worked through the dense predicate and I believe it (token 0 is the binding window case; the `tok_hi` check on offset 63 covers the range).  But nothing in `t/` ever reaches it: this test uses `n_heads = 16`, `n_kv_heads = 8`, so `kv_mul == 2` and `amx_qp` is always null.  Can we have a `kv_mul == 4` case (n_heads 32 - the llama-3.1-8b shape) so the whole AMX QK + PV path is compared against `emulation::compute_attention`?  On non-AMX hosts it degrades to the AVX path and still passes.  Ideally with sub-cases for a mask range ending inside the page and the window edge (`sliding_window_size` 64 vs 65 for a query at position 127).

_Verification: round 1 (R1-69), not addressed_

## 4. Checked and clean in the delta

| area | what was verified | source |
|---|---|---|
| The gate itself | shape_ok(128, 4) is used by the dispatch (self_attention.hpp 1359, 1547, 1622), the save_k write-through (model.hpp 2769-2771, compile-time) and, through amx_mirror_eligible(), the arena allocation (kv_cache.hpp 1039). The three round-1 sites now evaluate one function. | delta read; N1 |
| Compile-time gating of the write-through | if constexpr (k_mirror_shape_ok) means ineligible geometries instantiate no scatter in save_k; copy_storage_slot and fill_random rebuilds are unchanged (they null-check the plane, which is absent for ineligible models built through the scheduler). | delta read |
| Scheduler plumbing | node_base carries the flag exactly the way it already carries support_eagle and the slot counts (runtime copies of per-model constants); child nodes inherit from the parent; the eagle child scheduler shares the validator's root and therefore the validator's decision, which is the right one since books are shared. | delta read; N1 |
| New test case, mechanics | Allocation counting is exact: the fake DMA path is aligned_alloc (src/pos/fake.cpp:311) and the pos heap has its own allocator, so the mirror arena's aligned operator new[] is the only counted allocation; hand-built attention_geometry{n_q, kv_geometry{n_kv, head}} argument order matches kv_cache.hpp:105-107/146-147; <array> include added; static_assert inside TEST_CASE has precedent (t_fp32.cpp:1328, t_hwattention.cpp:207). The geometries in the comments are right (llama_3p2_1b 32/8/64, llama_3p1_70b 64/8/128). | N1, N3 clean |
| Name lookup and inheritance | Inside full_scheduler (not derived from node_base) the unqualified call at full.hpp:1456 finds the free function; child nodes copy the parent's flag (:721-726); the EAGLE draft adopts the validator's root and flag, which is right since books are shared. A compile-time alternative would need a book template parameter and would split the node_t types the shared_root cast relies on - the runtime field is the consistent choice (support_eagle is carried the same way). | N3-10, N2 clean |
| arch_prctl sentence | doc:86-87 now says 'once per process, from whichever thread first calls available()', which is what amx_attn.cpp does. | delta read |

## 5. Glossary

- **canonical-K** - Project shorthand: K kept in today's original single-copy row-major storage and read as-is by the AVX dotter, the FPGA DMA and the canonical AMX kernel.
- **mirror / k_vnni** - A second, derived copy of K in the pair-interleaved (VNNI) layout the AMX B operand wants. The mirror formulation originates from Bill's PR #2934 (k_vnni); the parallel-arena implementation and all numbers in PR #3879 are ours (jhan-amx-p0).
- **parallel arena** - Ordinary (non-DMA) RAM owned by the book, sized kv_bytes/2, one mirror plane per (storage slot, kv_head, page). Not the book's DMA arena_data.
- **shape gate / amx_attn::shape_ok** - New in cc8a86bb3: head_size == 128 && kv_mul == 4 in one function, used by the dispatch, the save_k write-through and (via amx_mirror_eligible) the arena allocation.
- **amx_mirror_eligible** - New in cc8a86bb3: (a) a constexpr function over a plugin's attention_kernels (true if any kernel passes the shape gate); (b) a bool carried on every node_base and passed to book::try_create; (c) a constructor parameter of book. The 3-argument book/try_create forms default it to true.
- **storage view / kv_blocks_alias** - book::set_storage_view() repoints kv_blocks_alias so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; canonical K accessors follow it, the mirror accessors do not (still true at cc8a86bb3).
- **EAGLE** - Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots.
- **ready / pending pass** - Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after upstream_kvs_ready.wait() over pages being written this forward (pending).
- **RX worker** - Per-card driver thread running DMA completion callbacks; rope_k/save_k execute there.
- **Note [Title]** - GHC-style named long comment, checked by make lint-notes.
- **A3, B6, ... tags** - Item numbers from ~/workspace/reviewers/alexey.md section 1; shown only in the verification line, never in the comment text.

## 6. Method and limits

- Persona: ~/workspace/reviewers/alexey.md Part 1. Round-2 behaviour applied: check that fixes were actually made ("There's a promise to fix that I don't see fulfilled?"), concede fast on what was fixed, isolate the remaining blockers in the body, carry the rest inline unchanged.
- Inputs: new head cc8a86bb3 (delta from bbb55ae5f is one commit, 7 files, +172/−57), clean worktrees of head and merge base, the full PR diff, the PR description, and your triage in PR3879/alexey-review.md (DONE/IGNORE marks; used in the verification lines, never in his text).
- Agents: 4 status-checkers re-anchored all 69 round-1 comments to the new head with a source snippet range each (58 unchanged, 8 partial, 3 fixed); 3 finders (design/correctness, comment accuracy, tests) returned 32 findings on the delta, merged into 14 new comments. No adversarial round this time: the new findings are text and design questions, and the two carried-over blockers were re-verified first-hand (mirror() unchanged at kv_cache.hpp:1244/:1250; t/CMakeLists.txt not in the delta) and by finder N3.
- Not verifiable here: no tron build (nix unavailable); the commit message reports all four AMX suites passing on delphi-3bda in both configurations - taken as author-reported. CI has not run on the new head (draft, no Run CI label).
- Counts: 79 open comments (carried over + new), 3 resolved. His p90 is 11 per PR; for large core PRs he does dense passes and does not move to the next pass until the current round is addressed.
