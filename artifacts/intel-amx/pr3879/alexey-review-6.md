# Review of PR #3879 as Alexey would write it - round 6

https://github.com/positron-ai/tron/pull/3879 - AMX software attention (default-off): QK/PV tile kernels + K-mirror arena  
Head `3fa11d911` (round 5 reviewed `234c02bde`; delta = b2010bee9 (3-argument book/try_create default amx_mirror_eligible to false), b85fd2789 (kernel TU header), 298dbad0f (TODO at the AMX options -> #3997), 275fa89a0 (comment trims), 35b3f3cae (Q-pack padding zeroed once by the buffer owner), 3fa11d911 (TRON_AMX_DISABLE exact "1"): 9 files, +70/-66); base `1407f48dd`; 14 files, +1827/-43. Written 2026-08-25. HTML twin: `alexey-review.html`; rounds 1-5 archived as `alexey-review-1.html` ... `-4.html`.

Lineage note: "mirror" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). "canonical-K" = K in today's original single-copy storage, read as-is.

Each comment shows the source lines it refers to (head `3fa11d911`; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.

## 1. Verdict

**CHANGES_REQUESTED**

Eleven threads closed this round - the `strcmp` rule (R1-16, R1-48), the pack padding zeroed once and the `cvtne2ps_pbh` note (R1-49, R1-50), the comment trims (R1-33, R1-43, R1-45, R1-67, R5-02), the `node_base` default (R2-09), the control case that now says what it means (R2-14) - good.

R2-03: the default flip does the half that mattered.  The two delegating overloads and the 3-argument clauses of `sequence_cache_behavior` can follow; one constructor with defaulted trailing parameters would do it without touching a test.

Two sentences the delta introduced are wrong, one of them mine: R1-15, "anywhere else the arena RAM is wasted" - nothing is allocated on a host without AMX, `maybe_allocate_mirror_arena` returns first; and R6-01, "so callers can reuse the same buffer", which stopped being true when the packers stopped zeroing the padding.

R1-47 and R1-58: so be it, replies inline.

What still blocks from my side is the stack of comment sentences that do not match the code - none of them big, all of them wrong as written:
- R1-10 - Note [Tile stores write 16 rows] says every output buffer receives 16 rows; `qk_canonical_128x4` writes 4.
- R3-02 - "every shape literal in the AMX code derives from these three"; `DIM_STEP`, `PANEL_ELEMS`, the pack-index 16s and the store offsets are still literals.
- R2-06 - "the reader and the writers can never disagree"; the two rebuild writers key on a non-null plane, not on `shape_ok`.
- R1-12 - the 64B-aligned contract on the Q pack buffer, which `std::vector<uint16_t>` does not meet (Codex's point too).
- R1-14 - the date on the 1250/686 pair is not the date of the sweep that produced it, and the Note names no record a reader can follow.
- R1-15, R6-01 - the two sentences above.
- Smaller ones of the same kind: R3-04, R1-20, R2-07, R1-21, R1-26, R2-08, R1-41, R2-11, R2-12, R3-05, R4-01.

The description still says nothing about `kv_block_planes`, `v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the `amx_mirror_eligible` plumbing through `node_base`, and no build or test job has run on any commit of this PR.

**Round 6 in one line:** 11 comments fixed by the six commits (section 2); 2 declined or deferred by you with his predicted reply (section 2a); 60 carried over (nine with a follow-up, one of them his correction of his own round-1 wording); 1 new (the pack-buffer reuse sentence that the padding change made false). Blockers 2 -> 0: R2-03's allocating default is gone (remainder is non-blocking, with a compiled single-constructor fix attached) and R1-58 is deferred by decision.

## 1a. What EAGLE is, and how likely it is to run together with the mirror

_Added on request in round 3 (2026-08-25) and carried unchanged; background for the EAGLE items, written from the tree at `96b5a6c72` (the fix landed in that commit)._

**What EAGLE is.** EAGLE is a speculative-decoding method: a small _draft_ model proposes several next tokens from the base model's hidden state, and the base model (the _validator_) checks them in one forward pass, so accepted tokens cost less than one full decode step each. In tron the draft is a one-layer model that shares the validator's KV books:

- **Enablement.** `src/tron/scheduler/full.cpp:307-308`: if `cfg.support_eagle` or the process-wide `prefer_eagle` is set, `find_eagle_model("eagle-<model>")` looks the draft up in the registry; if found, `support_eagle` is forced on. `prefer_eagle` reads `TRON_USE_SPECULATION` and is `false` by default (`full.cpp:40-43`, "Disabled by default"); `runtron --draft eagle` sets `support_eagle` per run (`h/runtron/stream_generate.hpp:1421`). Nothing under `.github/`, `bin/ci` or `config/test-benchmarks.json` turns speculation on.
- **Same model type.** The draft is created with the validator's own `model_t` and a copied config with `max_layers = 1`, `is_speculator = true` (`full.cpp:317-324`). Its attention geometry - and therefore its `shape_ok` - is the validator's.
- **Shared books, extra slot.** The draft scheduler adopts the validator's token-tree root (`full.hpp:1446-1448`). Books are created with `support_eagle`, which adds one physical storage slot after the validator's logical slots plus per-token embedding storage (`x_bytes`). Around each draft forward the scheduler calls `set_storage_view(eagle_storage_offset())` on every touched book and `reset_storage_view()` after (`full.hpp:1732`, `:1740`), so the draft's logical slot 0 resolves to that extra slot while canonical accessors go through `kv_blocks_alias`.
- **Registry.** Two production families have a draft: `eagle-llama-3.1-8b-instruct` (`config/models.yaml:254`; base shape 32/8/128 - AMX-eligible) and `eagle-llama-3.3-70b-instruct` (`:298`; base 64/8/128 - ratio 8, ineligible).

```
one KV book, one page, token j          canonical K (DMA)              mirror planes (arena)
                                        [slot 0][slot 1..L-1][slot L]  [M(0)][M(1..L-1)][M(L)]
validator forward (no view)
  save_k(slot 0) = K_v            --->   slot 0                  --->   M(0)
draft forward (view = slot L)
  save_k(slot 0) = K_d, same j    --->   slot L (follows view)
      before 96b5a6c72: mirror ignored the view          -X->   M(0)  (validator's plane overwritten)
      after:            mirror_view_offset_             --->   M(L)
```

**The two ways out of the round-1 bug.** Option A: make `mirror()` follow the view (what `96b5a6c72` does, via `mirror_view_offset_`). Option B: assert that no view is active while a mirror arena exists - i.e. forbid EAGLE and the mirror in the same process.

**How likely EAGLE and the mirror would be active together (the cost of option B).**

| fact | evidence | direction |
|---|---|---|
| Speculation is off unless an operator asks for it | `prefer_eagle` defaults false; `runtron --draft eagle` is per run; no CI/benchmark config enables it | lowers overlap today |
| Exactly one eligible production model has a draft | llama-3.1-8b (32/8/128) is in the gate and measured in this PR (+15%/+20% decode); llama-3.3-70b is ratio 8, outside the gate | overlap is one model, not zero |
| The draft inherits the validator's geometry | same `model_t`, `full.cpp:321-324` | whenever the validator is eligible, the draft's write-through is too - the bug was reachable, and option B would have to refuse the draft |
| Both features target decode latency on the same hosts | the mirror is opt-in "for pinned AMX deployments"; EAGLE cuts decode steps | the deployment that wants one is the deployment that wants the other |
| How often `--draft eagle` is used in production | not in the tree | Insufficient data |

Reading: not a frequent configuration as the tree stands (speculation is opt-in and absent from CI), but not a corner case either - llama-3.1-8b is the one eligible production model with a draft, and option B would have made tron's two decode accelerators mutually exclusive on exactly that model. The PR chose option A, which removes the question; what remains for review is the shape of that fix (two copies of the view state, section 3).

## 2. Resolved since round 5

Open comments the three commits addressed (11 fixed), made moot by deleting the file they were about (0 obsolete), or whose remaining half now lives in another thread (0 merged; the 'how it was addressed' column names the threads).

| comment | where (3fa11d911) | what was asked | how it was addressed | his reply, if any |
|---|---|---|---|---|
| R1-16 (fixed) | `h/tron/kernels/amx_attn_iface.hpp:96` | s/is not set/is not `1`/ - the A/B recipe in `t_amx_logit_ab.cpp` explicitly uses `=0`. | h/tron/kernels/amx_attn_iface.hpp:96; src/tron/kernels/amx_attn.cpp:57; src/tron/kernels/amx_attn.cpp:58 \| triage check: claim holds: 3fa11d911 changed :96 from 'is not set' to 'is not `1`' and amx_attn.cpp:58 now compares with strcmp(off, "1") == 0, so the `=0` recipe in t_amx_logit_ab.cpp:7 matches the contract \| your triage: done (3fa11d911) - available() contract says 'is not `1`' instead of 'is not set' |  |
| R1-33 (fixed) | `h/tron/models/self_attention.hpp:1417` | The declaration comment already explains the word/bit split; this second explanation of `>> 6` and `& 63` is more than the two operators deserve.  Flush. | h/tron/models/self_attention.hpp:1417; h/tron/models/self_attention.hpp:1418; h/tron/models/self_attention.hpp:1419 \| triage check: claim holds: delta.diff hunk @@ -1411,11 +1414,8 @@ removes the five-line 'Pack lazily: select the token's mask word (batch_job_ix / 64 via >> 6) ...' comment and replaces it with the two-line 'Pack this token's Q group once; later pages in the range reuse it.' (HEAD 1417-1418); the declaration comment at 1362-1365 remains the single explanation of the word/bit split. Commit 275fa89a0 as stated. \| your triage: done (275fa89a0) - second explanation of >> 6 / & 63 flushed |  |
| R2-09 (fixed) | `h/tron/scheduler/full.hpp:311` | Every constructor sets this, so the `= true` is dead, and `true` is the unsafe direction for a default (see the constructor comment in `kv_cache.hpp`).  If the file's convention is to give these members a default, mak... | h/tron/scheduler/full.hpp:306; h/tron/scheduler/full.hpp:309; h/tron/scheduler/full.hpp:310 \| triage check: no triage entry; commit b2010bee9 ('node_base's member default follows (every constructor sets it)') changed `= true` to `= false` and the comment records that every constructor sets it - the comment's either/or (delete the default, or make it false to match `support_eagle = false`) is met by the second branch | Good. |
| R5-02 (fixed) | `src/tron/kernels/amx_attn.cpp:1` | This describes a benchmark that is no longer in the tree, and the PR description already says so.  The Note this points at already names `t_amx_numerics` as what pins the kernels; flush the sentence. | src/tron/kernels/amx_attn.cpp:1; src/tron/kernels/amx_attn.cpp:3; src/tron/kernels/amx_attn.cpp:4 \| triage check: No triage entry. Commit b85fd2789 ('amx_attn.cpp: drop the history sentence from the file header') removed R5 lines 3-6 ('Kernel design and constants were validated with a stand-alone whole-path benchmark ... (git history up to d176c88b3).'); HEAD header is exactly the three lines proposed in the round-5 fix text. git grep d176c88b3 in HEAD src/tron/kernels: no hits. |  |
| R1-43 (fixed) | `src/tron/kernels/amx_attn.cpp:5` | Unused? | src/tron/kernels/amx_attn.cpp:5; src/tron/kernels/amx_attn.cpp:6; src/tron/kernels/amx_attn.cpp:7 \| triage check: claim holds: delta.diff removes '#include <atomic>' (R5 line 8) in 275fa89a0; grep -n atomic on HEAD amx_attn.cpp returns nothing, so no std::atomic use remains that depended on it. The include block now starts at HEAD line 5. \| your triage: done (275fa89a0) - unused <atomic> include removed |  |
| R1-45 (fixed) | `src/tron/kernels/amx_attn.cpp:32` | Eight lines of prose for `static_assert(sizeof(float) == 4)`.  I can smell Claude patting itself on the back a mile away.  The message string says everything the assert needs to say; flush the paragraph. | src/tron/kernels/amx_attn.cpp:31; src/tron/kernels/amx_attn.cpp:32; src/tron/kernels/amx_attn.cpp:33 \| triage check: claim holds: 275fa89a0 removed the seven comment lines R5:36-42 ('sizeof(float) rather than a literal 4: ...' through '... plain float for fp32 throughout.)'). Only the one-line purpose comment (HEAD:31) and the static_assert with its message string remain. \| your triage: done (275fa89a0) - prose around static_assert(sizeof(float) == 4) flushed |  |
| R1-48 (fixed) | `src/tron/kernels/amx_attn.cpp:58` | This is a first-character test: `TRON_AMX_DISABLE=true` leaves AMX on, silently.  Nearest precedents are `strcmp(v, "1") == 0` (`TRON_NO_RTM`, `TRON_USE_ARENA_ALLOCATOR`) or `atoi(v) > 0` (`USE_HW_ATTN`); pick one. | src/tron/kernels/amx_attn.cpp:56; src/tron/kernels/amx_attn.cpp:58; src/system/mwaitx.cpp:38 \| triage check: claim holds: 3fa11d911 replaced R5:68 'if (off && off[0] == '1') return false;' with the exact strcmp form, identical to the TRON_NO_RTM precedent at mwaitx.cpp:38; <cstring> was already included (HEAD:6). The header contract (amx_attn_iface.hpp:96) changed from 'is not set' to 'is not `1`', consistent with the Note at :32 'TRON_AMX_DISABLE=1 forces available() false'. The author's '=10 runs AMX' claim follows from strcmp("10","1") != 0 (unverified by execution here). The comment asked to pick one of the two house conventions; strcmp was picked. The 'optional INIT log line' in the triage note was not part of the comment. \| your triage: done (3fa11d911) - TRON_AMX_DISABLE now disables only on exact "1" (the TRON_NO_RTM rule); verified: unset and =10 run AMX, =1 skips. No new parser for true/yes (neither house convention accepts them). Optional INIT log line not done. |  |
| R1-49 (fixed) | `src/tron/kernels/amx_attn.cpp:98` | Each pack memsets 4 KB to write 512 B; columns 4..15 never change.  The `P` buffer below zeroes its padding once per thread - same discipline here? | src/tron/kernels/amx_attn.cpp:99; src/tron/kernels/amx_attn.cpp:100; src/tron/kernels/amx_attn.cpp:228 \| triage check: claim holds: 35b3f3cae removed 'std::memset(packed, 0, Q_PACK_ELEMS_2048 * sizeof(uint16_t));' (R5:109) and the rows-4..15 memset (R5:236-237); both header contracts now require zero padding on entry (amx_attn_iface.hpp:102-104, :156-159). Owner side verified: amx_qpack is thread_local (self_attention.hpp:1361), resize() value-initializes new slots, and the only writers are the two packers (:1424, :1429). The canonical and mirror layouts have different padding positions (columns 4..15 of each 32-element panel row vs rows 4..15), but the choice is a compile-time #ifdef TRON_AMX_K_MIRROR (:1420), so one slot never alternates layouts within a binary; the invariant holds. Test buffers are zero-initialized with = {} (t_amx_numerics.cpp:85, :125, :138). \| your triage: done (35b3f3cae) - packers write only the live columns/rows; padding zeroed once by the buffer owner (thread_local vector resize; test buffers = {}); both contracts updated | Good. |
| R1-50 (fixed) | `src/tron/kernels/amx_attn.cpp:194` | A one-line comment that `cvtne2ps_pbh(a, b)` puts `b` in the low half would save the next reader the lookup. | src/tron/kernels/amx_attn.cpp:194; src/tron/kernels/amx_attn.cpp:195; src/tron/kernels/amx_attn.cpp:196 \| triage check: claim holds: 35b3f3cae added the two comment lines at HEAD:194-195 directly above the call. Content is correct per the Intel intrinsics definition of _mm512_cvtne2ps_pbh(a, b): dst[255:0] is converted from b, dst[511:256] from a, so passing (hi, lo) keeps tokens c..c+15 in the low lanes. \| your triage: done (35b3f3cae) - one-line comment on cvtne2ps_pbh argument order |  |
| R2-14 (fixed) | `t/t_amx_arena_leak.cpp:134` | This control case is the argument against the legacy constructor: a head-64 book gets an arena no kernel can read, and the test enshrines it.  Once the 3-argument form is gone, the control becomes `book<...>(4, 2, fal... | t/t_amx_arena_leak.cpp:129; t/t_amx_arena_leak.cpp:134; t/t_amx_arena_leak.cpp:135 \| triage check: no triage entry; b2010bee9 made the control exactly `book<2, 1, 64, 0>(4, 2, false, true)` with a rewritten comment that names the flag. The 3-argument constructor was not removed (kv_cache.hpp:767-770) but now delegates with amx_mirror_eligible=false, so the case the comment argued against - a head-64 book getting an arena by default - no longer exists; the control says what it means. Anchor moved 132 -> 134. |  |
| R1-67 (fixed) | `t/t_amx_numerics.cpp:146` | Where does that check live?  Nothing in the tree performs it (`t_amx_logit_ab` only dumps).  Name it or delete the sentence; the local assertion stands on its own. | t/t_amx_numerics.cpp:145; t/t_amx_numerics.cpp:146; t/t_amx_numerics.cpp:147 \| triage check: claim holds: commit 275fa89a0 ("t_amx_numerics.cpp: removed the reference to a system-level byte-identical-output check that nothing in the tree performs") replaced the four-line comment with the two lines at :146-147; `grep -n 'system-level\\|byte-identical' t/t_amx_numerics.cpp` returns nothing at HEAD. The local REQUIRE at :150 stands alone as asked. \| your triage: done (275fa89a0) - sentence naming a check nothing performs removed |  |

## 2a. Declined or deferred by the author

Comments the author triaged `ignore` or `defer` (PR3879/triage.json). They are not re-raised below; the last column is how he would answer the stated reason, in his voice (predicted, checked against the tree by the status agents).

| comment | where (3fa11d911) | what was asked | author's decision and reason | his predicted reply |
|---|---|---|---|---|
| R1-47 | `src/tron/kernels/amx_attn.cpp:54` | You know we have `cpuid_bit(leaf, reg, bit)` in `h/system/mwaitx.hpp:22`, and that `is_rtm_supported` (`lazy<bool>` + `TRON_NO_RTM=1`) is the same shape as this whole function, right?  Reuse it, or say why the AMX probe can't. | ignore: Refactor, not a bug fix. Reusing cpuid_bit would cover only the two CPUID bits; the XGETBV and arch_prctl steps have no helper, so the probe stays hand-written. Decided 2026-08-25. | Fair enough; `mwaitx.hpp` has no home for the `xgetbv` and `arch_prctl` steps, so the probe stays here.  I would still have written the two bit tests as `cpuid_bit(7, cpuid_register_edx, 22)` and `... 24)` so the numerals read as leaf/register/bit, but your choice. |
| | | | _background block for R1-47 carried in the HTML version_ | |
| R1-58 | `t/CMakeLists.txt:365` | In the default build all three of these are a single `SUCCEED("...skipped")`, and even with the options on they `WARN` and return on a non-AMX host - so after merge nothing in CI compiles or runs the flagged code.  How was this validated, given `make test` ... | defer (298dbad0f): Accepted for now: CMakeLists.txt records that no CI configuration builds the AMX options; tracked in #3997 with the interim verify-on-an-AMX-host process. | OK, so be it.  The `TODO(jhan)` at the options and #3997 record what CI does not cover and why that is acceptable for a default-off feature; the compile-only target can come with the CI configuration. |

## 3. Open comments (61: 60 carried over from rounds 1-5, 1 new in round 6)

Carried-over comments keep their earlier text; where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**; replies he would post in the two Codex threads are marked **reply** and quote the bot comment they answer. A leading `[blocker]` marks the comments the body names.

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

**Suggested fix** (added at your request)

Replace lines 55-59 with:

```suggestion
// TILESTORED always writes ALL 16 configured tile rows, no matter how many
// carry real data: a width-4 result still stores 16 rows. The two kernels
// that store a tile straight into the caller's buffer - weights_times_v_128x4
// (`o`) and qk_mirror_128x4 (`s`) - therefore need 16-row buffers; a
// "4 x N" buffer is a silent overrun (rows 4..15 land past its end).
// Rows 4..15 of those buffers receive zeros (the A-operand rows 4..15 are
// zero padding); only rows 0..3 are the result. qk_canonical_128x4 stores
// its tiles into a kernel-local buffer, transposes, and writes exactly 4 rows
// x 64 columns into `s`, so `s` needs only 4 rows (s[4][s_stride_floats]).
```

_Fix note: Fact-checked against 3fa11d911 (CONFIRMED with two wording corrections, applied): the only _tile_stored targets in a caller's buffer are weights_times_v_128x4's `o` (amx_attn.cpp:220-223) and qk_mirror_128x4's `s` (:255-258); qk_canonical_128x4 stores into its local s_transposed (:142-145) and its transpose writes rows k = 0..3 (:173-177) - the header's own contract at :114 says 'writes s[4][s_stride_floats]'; t_amx_numerics hands it s_amx[NQ][PAGE] with NQ = 4 (:87). Rows 4..15 of `o` / mirror `s` are zero because the A-operand rows 4..15 (P rows :187-190, Qpad rows) are zero padding. 'stack overrun' -> 'overrun': the production mirror scratch qk_s is thread_local (self_attention.hpp:1567-1568), not stack. Five lines become nine; line 60 follows unchanged. Residual the checker noted, outside this range: :66-69 still says 'output buffers are sized with TILE_ROWS_16' for every kernel - add 'the two kernels that store into a caller buffer' there too if you take this fix._

**Explanation** (added at your request) - the Note, sentence by sentence

##### The picture

AMX works on **tiles**: fixed-size registers configured here as **16 rows x 64 bytes**. Three kernels produce result tiles; the question is where each one *stores* them and therefore how big the caller's output buffer has to be.

```
kernel                  where TILESTORED writes                caller must provide
----------------------  -------------------------------------  ---------------------------
weights_times_v_128x4   straight into the caller's `o`          16 rows x 128 fp32  (8 KB)
qk_mirror_128x4         straight into the caller's `s`          16 rows x  64 fp32  (4 KB)
qk_canonical_128x4      into its OWN local buffer, then         `s` with only 4 rows
                        transposes and copies rows 0..3 to `s`  (row stride: caller's choice)
```

What one stored tile looks like at width 4 (4 query heads = 4 useful rows):

```
16-row buffer (correct)            4-row buffer (the bug the Note warns about)
row  0 #### result                 row 0 #### result
row  1 #### result                 row 1 #### result
row  2 #### result                 row 2 #### result
row  3 #### result                 row 3 #### result
row  4 ---- zeros                  rows 4..15 are written PAST THE END of the
 ...   ---- zeros                  buffer: memory after it is overwritten,
row 15 ---- zeros                  and nothing reports an error ("silent overrun")
```

##### Sentence by sentence

| the comment says | in plain words |
|---|---|
| "TILESTORED always writes ALL 16 configured tile rows, no matter how many carry real data: a width-4 result still stores 16 rows." | The tile-store instruction has no "store only 4 rows" mode. If the tile is configured as 16 rows, 16 rows land in memory, even when only 4 of them mean anything. |
| "The two kernels that store a tile straight into the caller's buffer - `weights_times_v_128x4` (`o`) and `qk_mirror_128x4` (`s`) - therefore need 16-row buffers" | Two of the three kernels point the store instruction directly at the memory the caller passed in. For those two, the caller's buffer must have room for 16 rows. |
| "a "4 x N" buffer is a silent overrun (rows 4..15 land past its end)." | If a caller sizes the buffer for the 4 real rows only, rows 4..15 are written beyond it. No crash, no error - just corrupted memory somewhere else. |
| "Rows 4..15 of those buffers receive zeros (the A-operand rows 4..15 are zero padding)" | Why those extra rows are zeros and not garbage: the tile multiply computes C = A.B row by row, so output row i comes from row i of the left-hand input (the "A operand"). Rows 4..15 of A are padding that is kept at zero (the P rows in `weights_times_v_128x4`, the packed Q rows in the mirror kernel), so rows 4..15 of the output are zero. This is also why 35b3f3cae made "padding must already be zero" a precondition of the pack functions. |
| "only rows 0..3 are the result." | The caller reads rows 0..3 and ignores the rest. |
| "`qk_canonical_128x4` stores its tiles into a kernel-local buffer, transposes, and writes exactly 4 rows x 64 columns into `s`" | The third kernel is different: it computes the *transposed* scores (64 token rows x 16 columns) into a scratch buffer that lives inside the kernel (`s_transposed`), then flips them and copies only the 4 real rows into the caller's `s`. The 16-row store happens on the kernel's own memory, not the caller's. |
| "so `s` needs only 4 rows (s[4][s_stride_floats])." | For this kernel a 4-row `s` is correct - which is exactly what `t_amx_numerics` passes it (`s_amx[NQ][PAGE]`, NQ = 4). `s_stride_floats` is the distance between consecutive rows of `s`, chosen by the caller (both current callers use 64). |

##### Why the sentence was changed

The old Note said "**every** output buffer handed to a kernel below must be sized for 16 rows." That was false for `qk_canonical_128x4`, and it made the test's correct 4-row buffer look like a bug (R1-10). The new text names the two kernels the rule applies to and states the exception.

##### Glossary

- **TILESTORED** - the AMX instruction that copies a tile register to memory (`_tile_stored` in the code).
- **tile** - one of 8 AMX registers; configured here as 16 rows x 64 bytes (16 fp32 or 32 bf16 per row).
- **A operand / B operand** - the two inputs of the tile multiply `C += A.B`; output rows follow A's rows, output columns follow B's columns.
- **width-4** - one KV head shared by 4 query heads (GQA), so a decode step has 4 useful query rows.
- **padding** - rows or columns present only to fill the tile; must be zero so they do not disturb the result.
- **row stride** - the number of elements between the start of one row and the next in a buffer.


_Verification: round 1 (R1-10), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:56; h/tron/kernels/amx_attn_iface.hpp:57; src/tron/kernels/amx_attn.cpp:122_

#### `h/tron/kernels/amx_attn_iface.hpp:75` R3-02 (A3)

```cpp
   72  // The one attention shape these kernels serve - the tile identity of
   73  // Note [AMX attention dispatch]: a 64-token KV page, 128-dim heads, and 4
   74  // query heads per KV head (4 x 128 bf16 = one full tile operand). Every
   75* // shape literal in the AMX code derives from these three.
   76  inline constexpr size_t PAGE_TOKENS_64 = 64;
   77  inline constexpr size_t HEAD_SIZE_128 = 128;
   78  inline constexpr size_t GROUP_HEADS_4 = 4;
```

"Every shape literal in the AMX code derives from these three" - `DIM_STEP = 32`, `PANEL_ELEMS = 16 * 16 * 2`, the `4` in `step * 4`, the `16`s in the pack index and the `64/16/32/48` in the output stores are still literals in `amx_attn.cpp`, `scatter_k_mirror` has its own 16 and 32, and `Q_PACK_ELEMS_2048` on the next line derives from `TILE_ROWS_16`, a fourth.  s/Every shape literal in the AMX code derives from these three/`shape_ok` and the kernel buffer sizes are written in terms of these/ - or make it true.

**Suggested fix** (added at your request)

Replace lines 72-75 with:

```suggestion
// The one attention shape these kernels serve - the tile identity of
// Note [AMX attention dispatch]: a 64-token KV page, 128-dim heads, and 4
// query heads per KV head (4 x 128 bf16 = one full tile operand). shape_ok
// and the kernel buffer sizes are written in terms of these three.
```

_Fix note: Exactly the s/// he offered in R3-02. My first draft added a clause calling the remaining amx_attn.cpp literals 'AMX tile geometry, not model shape'; the fact-checker refuted it: `step * 4` (:246-252) is PAGE/16 token blocks per dim step, `r < 4` (:150) is PAGE/TILE_ROWS, `k < 4` (:173) is GROUP_HEADS, `half < 2` (:200) is HEAD_SIZE/64, `s < 2` (:205) is PAGE/DIM_STEP, `half * 64` (:220-223) is HEAD_SIZE/2 - all model-derived; DIM_STEP, PANEL_ELEMS, the pack-index 16s and the 16-float store offsets are tile geometry; the transpose/convert 4s, 32s and 0x88 are AVX-512 widths. So the honest sentence stops after 'these three'. Checked: shape_ok (:91-92) uses HEAD_SIZE_128 / GROUP_HEADS_4; Q_PACK_ELEMS_2048 (:83), s_transposed[PAGE * TILE_ROWS] (amx_attn.cpp:122), P[TILE_ROWS][PAGE] (:189) and the 1 KB memcpy (:229) use the named constants._

_Verification: round 3 (R3-02), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:74; h/tron/kernels/amx_attn_iface.hpp:75; h/tron/kernels/amx_attn_iface.hpp:83_

#### `h/tron/kernels/amx_attn_iface.hpp:77` R3-01 (B3)

```cpp
   76  inline constexpr size_t PAGE_TOKENS_64 = 64;
   77* inline constexpr size_t HEAD_SIZE_128 = 128;
   78  inline constexpr size_t GROUP_HEADS_4 = 4;
   79  // One packed Q group (the pack_q_group_128x4 / pack_q_rows_128x4 output
   80  // buffer): 16 tile rows x 128 bf16 = 2048 bf16 = 4 KB. The VNNI pack
   81  // (4 panels x 16 dim-pair rows x 32 bf16) and the zero-padded A-operand rows
   82  // (16 x 128) are the same size, so callers reuse one buffer.
   83  inline constexpr size_t Q_PACK_ELEMS_2048 = TILE_ROWS_16 * HEAD_SIZE_128;
   84  static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value");
```

A constant whose name carries its value is a literal with a longer name: the day `HEAD_SIZE_128` is not 128 the name lies, and `static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value")` guards a problem we created.  `tile_rows`/`q_pack_elems` were fine; `head_size`, `group_heads`, `page_tokens` say what they are, and every constant in `h/tron/models`, `kernels` and `scheduler` is lower snake_case (`page_size`, `kv_block_planes`, `illegal_sliding_window`).  Flush the `static_assert` with the rename.

_Verification: round 3 (R3-01), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:76; h/tron/kernels/amx_attn_iface.hpp:77; h/tron/kernels/amx_attn_iface.hpp:78_

#### `h/tron/kernels/amx_attn_iface.hpp:89` R2-06 (A3)

```cpp
   86  // THE shape gate: the AMX kernels serve exactly one attention shape, 4 query
   87  // heads x 128 dims per KV head (the tile identity, see
   88  // Note [AMX attention dispatch]). Shared by the dispatch, the save_k mirror
   89* // write-through, and the mirror-arena allocation, so the reader and the
   90  // writers can never disagree about which models take the AMX path.
   91  constexpr bool shape_ok(size_t model_head_size, size_t model_kv_mul) noexcept {
   92    return model_head_size == HEAD_SIZE_128 && model_kv_mul == GROUP_HEADS_4;
   93  }
```

"so the reader and the writers can never disagree" - two of the three writers don't use this gate (the `copy_storage_slot` and `fill_random` rebuilds scatter for any geometry whose plane is non-null), and the 3-argument `book` forms pass `true`.  It holds for books the scheduler creates.  Say that, or make it true.  Since b2010bee9 the 3-argument forms pass false, so the un-gated writers are now the eight test sites that pass true; "it holds for books the scheduler creates" is still the true sentence, and the Note still does not say it.

**Suggested fix** (added at your request)

Replace lines 88-90 with:

```suggestion
// Note [AMX attention dispatch]). Evaluated by the dispatch, the save_k
// write-through and, through amx_mirror_eligible, the scheduler's
// mirror-arena decision; the page-move and fill_random rebuilds do not test
// it - they rebuild whatever plane exists. So for a book the scheduler
// creates, the reader and the writers agree on which models take the AMX
// path; a book built by hand with amx_mirror_eligible=true gets planes for
// every slot on an AMX host, whether or not its geometry passes this gate.
```

_Fix note: Fact-checked (CONFIRMED with three calibration corrections, applied): shape_ok is evaluated by the dispatch (self_attention.hpp:1358-1359, :1499-1500), the save_k write-through (model.hpp:2769-2770) and amx_mirror_eligible() at the scheduler's call site (full.hpp:1457; kv_cache.hpp:184-186) - the book's allocator itself (kv_cache.hpp:1052-1057) only consumes the bool, hence 'through amx_mirror_eligible'; copy_storage_slot (:1885-1886) and fill_storage_slot (:1314) null-check mirror_at_storage only; the arena also needs amx_attn::available() (:1057), hence 'on an AMX host'; a hand-built head-64 book with the flag true gets one arena sized kv_bytes/2 covering every storage slot (t_amx_arena_leak.cpp:134-136; kv_cache.hpp:1058-1061). Line 87 ends with '(the tile identity, see', so the first line reads on; :91 `constexpr bool shape_ok(` follows. Three lines become seven, max 76 columns._

_Verification: round 2 (R2-06), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:89; h/tron/kernels/amx_attn_iface.hpp:90; h/tron/models/kv_cache.hpp:770_

#### `h/tron/kernels/amx_attn_iface.hpp:102` R1-12 (A3)

```cpp
   99  // Pack one query group (4 query heads x 128 dims, contiguous bf16) into the
  100  // tile B-operand (VNNI pair-interleaved) layout consumed by
  101  // qk_canonical_128x4.
  102* // `packed` must hold Q_PACK_ELEMS_2048 bf16 (4 KB), 64B-aligned, with
  103  // columns 4..15 of every panel already zero: this call writes columns 0..3
  104  // only, so a buffer zeroed once at allocation stays valid for every pack.
  105  // `packed` layout: 4 panels, one per 32-dim step of the head; each panel is
  106  // 16 dim-pair rows x 16 query columns (columns 0..3 = the 4 heads, columns
  107  // 4..15 zero padding) x 2 paired values:
  108  //   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
  109  //     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
  110  void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
```

Who guarantees the 64B alignment?  `amx_qpack` is a `std::vector<uint16_t>`, which promises 16.  The kernels only `_tile_loadd` it, so either drop the requirement from the contract (here and at :135) or give the buffer `alignas(64)` storage.  Fix one.

**Suggested fix** (added at your request)

1. Take the zero-cost arm of his 'Fix one': drop the alignment claim from the two Q-pack contracts (:102 here; :160 goes with the R6-01 replacement below), since nothing in the tree provides 64-byte storage and TILELOADD does not require it. Codex's point that a 16 mod 64 base makes every 64-byte tile row straddle two cache lines stays a performance question, not a correctness one.
2. If that cost is to be settled rather than accepted: time one dense page with the pack at 0 vs 16 mod 64 (his R5-03 sentence). If it matters, the storage his R1-31 points at - `attn_accum`, per attention worker, per token, already 64B-aligned, allocated in `state` for the loaded model only - is the place; that change is not drafted here.
3. NOT suggested: a fixed `alignas(64) thread_local` array sized by `max_minibatch_size` (my first draft, syntax-checked clean). The fact-checker measured why: a function-local thread_local in apply_page_range is one static-TLS block per model instantiation, and glibc allocates and zero-fills the whole static TLS image for every thread at creation; ingest-generated plugins hard-code max_minibatch_size = 1024 (ingest/src/TronCpp.hs:264), so each eligible ingested model costs 4 MB per thread and llama.hpp's 128 costs 512 KB - est. ~52 MB per thread for a production build, on every thread, for models never loaded. The rejected diff is kept at exec/review-pipeline/r6/fix/self_attention.REJECTED-thread_local-tls.diff.

`h/tron/kernels/amx_attn_iface.hpp`:102-102 - the canonical pack contract; :103-104 read on

```suggestion
// `packed` must hold Q_PACK_ELEMS_2048 bf16 (4 KB; no alignment requirement), with
```

_Fix note: The :160 line ('(= Q_PACK_ELEMS_2048, 4 KB, 64B-aligned) - same size as the canonical pack,') is rewritten by the R6-01 fix, which drops '64B-aligned' as well, so the two contracts stay consistent. Verified: the only Q-pack storage is `thread_local std::vector<uint16_t> amx_qpack` (self_attention.hpp:1361), whose data() is 16 mod 64 in nearly every allocation on glibc (measured in round 5); the other two 64B contracts (`o` :123-125, `s` :166-168) are honored by alignas(64) storage at self_attention.hpp:1567-1568 and :1646 and stay as they are. Line 102 is the only edit here; it stays under 88 columns._

_Verification: round 1 (R1-12), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:102; h/tron/kernels/amx_attn_iface.hpp:160; h/tron/models/self_attention.hpp:1361_

#### `h/tron/kernels/amx_attn_iface.hpp:110` R1-13 (B5)

```cpp
  108  //   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
  109  //     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
  110* void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
  111  
  112  // Dense QK for one page, canonical-K orientation: computes S^T = K_page . Q^T
  113  // in tiles and transposes on the way out (see Note [Mirror orientation]);
  114  // writes s[4][s_stride_floats] fp32, all 64 token columns, UNSCALED.
  115  // k_page = 64 x 128 bf16 row-major (the kv_block K layout).
  116  void qk_canonical_128x4(const uint16_t* k_page,
  117      const uint16_t* q_packed,
  118      float* s,
  119      size_t s_stride_floats) noexcept;
```

`uint16_t*`?  Any reason not to take `const bf16*` (or a `const_view<bf16, ..., seq<128>>` for the Q rows and a `std::array<float, 16 * 128>&` for the 16-row outputs)?  Then the size and alignment contracts in the Note are carried by the type instead of prose, and the dozen `reinterpret_cast`s at the call sites go away.  The header would still have no intrinsics.

_Verification: round 1 (R1-13), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:110; h/tron/kernels/amx_attn_iface.hpp:116; h/tron/kernels/amx_attn_iface.hpp:127_

#### `h/tron/kernels/amx_attn_iface.hpp:140` R1-14 (A3/A4)

```cpp
  137  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  138  // (K consumed exactly as stored) and must then round-trip the score tile
  139  // through memory and transpose it - a ~560 ns/page whole-path cost at
  140* // width 4 (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19;
  141  // transpose work + score traffic combined, not isolated). NOT a
  142  // store-forwarding stall: 64-byte
  143  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
  144  // a 6962P microbench measured no stall on that path; the hard restriction
  145  // is the opposite direction, any store -> TILELOADD cannot forward.
```

There is no store-forwarding microbench in the tree, and the 982/686 figures come from `amx_fused_bench.cpp` with unrecorded arguments.  Numbers we can't reproduce shouldn't be stated as facts in a Note.  Record the command that produced them where a reader can find it, and reference that from here.  The figures now agree with a recorded sweep (`exec/results/slot1/fused-sweep-v2.txt`: 1249.9 / 686.0, same ring) - good.  But that file is stamped `2026-08-18T18:34:53Z`, still the 18th in PDT, so where does 08-19 come from?  If there was no second run, s/2026-08-19/2026-08-18/.  And the command line that ff7269a9f recorded went out again in 901f30d8e, so a reader still has nowhere to go to reproduce 1250: this Note is now the only place the pair lives, so let's name the record and the command here, or drop the numbers.  The forwarding-stall "6962P microbench" at :142 still has no record at all.  This is marked done, but :140 still says 2026-08-19 and the Note still names neither the record nor the command - the sweep we agree on is stamped `2026-08-18T18:34:53Z`.

**Suggested fix** (added at your request)

Replace lines 139-141 with:

```suggestion
// through memory and transpose it - a ~560 ns/page whole-path cost at
// width 4 (1250 vs 686 ns per L2-resident page: exec/results/slot1/
// fused-sweep-v2.txt in the campaign workspace, 2026-08-18, 6962P core 96,
// `taskset -c 96 ./amx_fused_bench 4 200000 amx44 1` / `amxqk` on the
// stand-alone benchmark at d176c88b3; ~500 ns once that benchmark's per-page
// scalar Q pack is amortized, 512-page ring 1972 vs 1470 - the pack, the
// transpose and the score round trip were not isolated). NOT a
```

_Fix note: Same replacement as round 5, re-anchored (+2 lines): names the record, the host, the corrected date (file header 2026-08-18T18:34:53Z; exec/logs/p0-fused-sweep.log lists both sweeps on 08-18), the command ff7269a9f recorded and 901f30d8e removed, and the pack artifact R5-01 asks about (pages=512 row: 1971.6 vs 1470.2). Line 142 ('store-forwarding stall: 64-byte') reads on. The '6962P microbench' sentence at :142-144 is unchanged: no record exists to cite._

_Verification: round 1 (R1-14), partial: Met: the unrecorded 982 is gone and 1250/686 match fused-sweep-v2.txt:14/:30. Not met, and unchanged since R5 (the delta did not touch :137-145): (1) the Note still says 2026-08-19 at :140 while the only record is stamped 2026-08-18T18:34:53Z (file mtime 2026-08-18 11:38:07 -0700; exec/logs/p0-fused-sweep.log lists both sweeps on 08-18, 18:12 and 18:34 UTC) - no 08-19 run exists; (2) the Note names no record and no command; the pr_body.md:7 sentence points to an out-of-tree notebook URL and says the benchmark 'is not in the tree (git history up to d176c88b3)', so a reader of the header still has nowhere to reproduce 1250; (3) the '6962P microbench measured no stall' sentence at :144 still has no record anywhere ('6962P' is not in the sweep header either; 'cpu 96' is a core index). | evidence: h/tron/kernels/amx_attn_iface.hpp:139; h/tron/kernels/amx_attn_iface.hpp:140; h/tron/kernels/amx_attn_iface.hpp:144 | your triage: done (ff7269a9f, 901f30d8e) - Note [Mirror orientation] now states the recorded measurement (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19) instead of the unrecorded 982._

#### `h/tron/kernels/amx_attn_iface.hpp:141` R5-01 (A3/A4)

```cpp
  137  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  138  // (K consumed exactly as stored) and must then round-trip the score tile
  139  // through memory and transpose it - a ~560 ns/page whole-path cost at
  140  // width 4 (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19;
  141* // transpose work + score traffic combined, not isolated). NOT a
  142  // store-forwarding stall: 64-byte
  143  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
  144  // a 6962P microbench measured no stall on that path; the hard restriction
  145  // is the opposite direction, any store -> TILELOADD cannot forward.
```

IIUC the `amx44` variant re-ran the scalar `pack_q` inside `run_pages` (so once per page at `pages=1`) while `amxqk` built `Qpad` once before the timer, and production packs Q once per (token, kv_head) per section - so isn't part of the 560 a bench artifact rather than transpose or score traffic?  The 512/16384-page rows, where the pack is amortized, show ~500.  Either name it in the 'combined' list or quote the amortized gap and drop 'L2-resident'.

_Verification: round 5 (R5-01), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:140; h/tron/kernels/amx_attn_iface.hpp:141; exec/results/slot1/fused-sweep-v2.txt:14_

#### `h/tron/kernels/amx_attn_iface.hpp:153` R1-15 (B11)

```cpp
  151  // there too). Both ship:
  152  // canonical-K is the supported default; the mirror is opt-in
  153* // (TRON_AMX_K_MIRROR) for builds that will only run on AMX hosts - anywhere
  154  // else the arena RAM is wasted. The mirror formulation is PR #2934's k_vnni.
```

Keep the pointer to #2934 if it helps a reader find the other formulation; flush "this arena implementation is ours".  Attribution goes in the PR description.  Also, what's a "pinned AMX deployment"?  Say the concrete condition (builds that will only run on AMX hosts, since the arena RAM is wasted otherwise).  Is the arena RAM wasted anywhere?  On a non-AMX host `available()` is false and `maybe_allocate_mirror_arena` returns before allocating (`kv_cache.hpp:1057`; Note [K mirror parallel arena] and the PR description both say non-AMX hosts pay nothing), so the mirror's cost is the kv_bytes/2 plus the save_k write-through on the AMX hosts that do run it.  Let's say that instead - my round-1 phrasing was wrong.

**Suggested fix** (added at your request)

Replace lines 152-154 with:

```suggestion
// canonical-K is the supported default; the mirror is opt-in
// (TRON_AMX_K_MIRROR): on an AMX host it costs kv_bytes/2 of ordinary RAM per
// book plus the save_k write-through; on any other host nothing is allocated
// and the AVX path runs. The mirror formulation is PR #2934's k_vnni.
```

_Fix note: Replaces the consequence clause with the condition the code implements (kv_cache.hpp:1057 gate; model.hpp:2771 write-through gate). Keeps the #2934 pointer he asked to keep._

_Verification: round 1 (R1-15), partial: 275fa89a0 applied the round-1 suggestion near-verbatim; its consequence clause 'anywhere else the arena RAM is wasted' (:153-154) is false: maybe_allocate_mirror_arena returns at kv_cache.hpp:1057 when available() is false, so a non-AMX host allocates no arena (Note [K mirror parallel arena] :558-561, t_amx_arena_leak.cpp:95 and the PR body all say so). Finder 'text' #1, refuter PARTIAL (wording), would-he-raise=yes - his own phrasing, corrected in his voice. | evidence: h/tron/kernels/amx_attn_iface.hpp:152-154; h/tron/models/kv_cache.hpp:1057; t/t_amx_arena_leak.cpp:95 | your triage: done (275fa89a0) - attribution sentence dropped, #2934 pointer kept, 'pinned AMX deployments' replaced by the concrete condition_

#### `h/tron/kernels/amx_attn_iface.hpp:161` **new** (A3)

```cpp
  156  // Pack one query group (4 heads x 128 dims, contiguous bf16) as a zero-padded
  157  // A operand: rows 0..3 = the 4 heads' rows; rows 4..15 are padding this call
  158  // leaves untouched, so they must already be zero (a buffer zeroed once at
  159  // allocation stays valid for every pack). `padded` must hold 16 * 128 bf16
  160  // (= Q_PACK_ELEMS_2048, 4 KB, 64B-aligned) - same size as the canonical pack,
  161* // so callers can reuse the same buffer.
  162  void pack_q_rows_128x4(const uint16_t* q_group, uint16_t* padded) noexcept;
```

"so callers can reuse the same buffer" - not now that the padding is a precondition: a canonical pack writes elements 512..2023 (this layout's rows 4..15) and a rows pack fills panel 0's columns 4..15, so a buffer that has seen one packer fails the other's "must already be zero" without a memset in between.  Rows 0..3 of S still come out right - the dirt only reaches the discarded rows/columns - so this is the contract contradicting itself (and "Rows 4..15 receive zeros" at :59), not a wrong number.  s/so callers can reuse the same buffer/so one buffer size serves either orientation/.

**Suggested fix** (added at your request)

Replace lines 160-161 with:

```suggestion
// (= Q_PACK_ELEMS_2048, 4 KB; no alignment requirement) - the same size as
// the canonical pack, so one buffer size serves either orientation (never
// both in turn: each pack's live data lands in the other's padding).
```

_Fix note: Two lines become three; line 162 (`void pack_q_rows_128x4(...)`) follows unchanged. Also drops '64B-aligned' here, the R1-12 arm taken above. The call-site comment at self_attention.hpp:1422 '(same 4 KB buffer either way)' already means one allocation per build, which this wording keeps._

_Verification: new in round 6 (R6-01); finder 'design' #2, refuter PARTIAL -> confirmed with the consequence corrected (no wrong S rows: the canonical transpose emits k = 0..3 only, amx_attn.cpp:147/:173; the mirror path copies rows 0..3 only, self_attention.hpp:1571-1572; t_amx_numerics compares qi < 4). Verified index math: pack_q_group_128x4 writes offsets 0..7 of every 32-element panel row (amx_attn.cpp:105), 384 of its 512 elements land in rows 4..15 of the row layout; pack_q_rows_128x4 memcpys elements 0..511, 384 of which are panel 0's columns 4..15. Not exercised in-tree: one packer per build under #ifdef TRON_AMX_K_MIRROR (self_attention.hpp:1420-1433); t_amx_numerics uses separate buffers (:125, :138). The R5 contract said 'rows 4..15 zeroed by this call', which made the reuse sentence true; 35b3f3cae changed the precondition and kept the sentence._

### h/tron/kernels/page_share_counters.hpp

#### `h/tron/kernels/page_share_counters.hpp:6` R1-17 (A1/A9/A3)

```cpp
    2  // Page-sharing instrumentation: measures how many query tokens of the
    3  // current minibatch legally attend the SAME physical KV page in one visit -
    4  // the achievable batching width for the AMX kernels.
    5  //
    6* // Compiled in only with -DTRON_PAGE_SHARE_COUNTERS=1. Zero hot-loop cost:
    7  // callers accumulate plain locals and flush to the global atomics once per
    8  // apply_page_range call (roughly once per (worker, kv_head, page-range) - a
    9  // few tens of thousands of flushes per second at most).
   10  //
   11  // Dump: automatic at process exit to stderr.
   12  
   13  #ifdef TRON_PAGE_SHARE_COUNTERS
```

Is this instrumentation still needed?  Its conclusion (width 4 is the guaranteed decode width) is already baked into the kernel shape, nothing in CMake defines `TRON_PAGE_SHARE_COUNTERS`, and it adds a third flag family plus an exit-time printer under `kernels/` for something that instruments `models/`.  I'd record the histogram in the PR description and drop the code; if we want a live counter, the `TRACE_EVENT` args two lines above the page loop are the existing place.  Also, the guard is `#ifdef`, so `=0` enables it too; and with the flag on there is an increment per (page, token) inside the loop, so "Zero hot-loop cost" isn't what the code does.  With the histogram's home gone from the PR, the PR description is where its conclusion belongs; the question whether the code stays is unchanged.

_Verification: round 1 (R1-17), not addressed | evidence: file unchanged since 234c02bde_

### h/tron/models/kv_cache.hpp

#### `h/tron/models/kv_cache.hpp:182` R2-05 (A5/B1)

```cpp
  176  // True when at least one of a model's attention kernels has the shape the AMX
  177  // kernels serve (amx_attn::shape_ok). The scheduler passes this as
  178  // amx_mirror_eligible when it creates KV books, so a model that can never
  179  // take the AMX path allocates no mirror arena and writes no mirror rows
  180  // (see Note [K mirror parallel arena]).
  181  template <size_t n_kernels>
  182* constexpr bool amx_mirror_eligible(
  183      std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  184    for (auto const& kernel : kernels) {
  185      if (amx_attn::shape_ok(kernel.geometry.kv.head_size, kernel.geometry.kv_mul())) {
  186        return true;
  187      }
  188    }
  189    return false;
  190  }
```

Any eligible kernel makes the whole arena: for a model with one eligible and one ineligible attention kernel the ineligible slots' planes are allocated (`kv_bytes/2` covers every slot), never written by `save_k`, and rebuilt on every page move by `copy_storage_slot`.  No in-tree plugin is mixed today, so fine - but say so here ("any kernel; sized for all slots; only eligible geometries are written through"), and a two-kernel array in `t_amx_arena_leak` would record the intended answer.

_Verification: round 2 (R2-05), not addressed | evidence: h/tron/models/kv_cache.hpp:176; h/tron/models/kv_cache.hpp:178; h/tron/models/kv_cache.hpp:554 | your triage: question - explained in PR3879/kv_cache-hpp-1199.html 4.1; recommended Option 1 (comment consequences + Note sentence + two-kernel static_assert); not applied yet_

#### `h/tron/models/kv_cache.hpp:539` R1-25 (B7)

```cpp
  539* #if defined(TRON_AMX_K_MIRROR) && !defined(TRON_AMX_DISPATCH)
  540  #error "TRON_AMX_K_MIRROR requires TRON_AMX_DISPATCH"
  541  #endif
```

CMake already refuses this combination (`src/tron/CMakeLists.txt:178`).  If the `#error` is for non-CMake builds, say so; otherwise one check is enough.

_Verification: round 1 (R1-25), not addressed | evidence: h/tron/models/kv_cache.hpp:539; h/tron/models/kv_cache.hpp:540; src/tron/CMakeLists.txt:182_

#### `h/tron/models/kv_cache.hpp:586` R1-24 (A9)

```cpp
  584  // pair-interleaved layout natively, so V needs no second copy. Reopen only
  585  // if a card consumes VNNI K natively or an FPGA-free build ships.
  586* inline constexpr size_t kv_block_planes = 2;
  587  #ifdef TRON_AMX_K_MIRROR
  588  // Note [K mirror coherence]
```

Is `kv_block_planes` ever anything but 2?  If it's a leftover of the in-block third-plane design, the rename of the pre-existing `2 *` literals (here, :1138, `t_llama_unit.cpp:415`) is an unrelated refactor - its own small PR, or drop it.

_Verification: round 1 (R1-24), not addressed | evidence: h/tron/models/kv_cache.hpp:586; h/tron/models/kv_cache.hpp:647; h/tron/models/kv_cache.hpp:1199_

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
  598  //      goes through copy_storage_slot, which regenerates the mirror from
  599  //      the DESTINATION's just-copied canonical K, so it is coherent no
  600  //      matter the source book's mirror state.
  601  // Both sites address the plane of the PHYSICAL slot the canonical row lives
```

Lock-free cross-thread hand-off, eh?  Then the Note should say what orders the RX worker's plain stores before the attention worker's tile loads.  IIUC it is not `mark_k_complete` (software attention never reads `kv_saves_`); it is (a) pages written this forward are never in the ready plan, and (b) the write precedes `upstream_kvs_ready.count_down()` in program order and the pending pass acquires on `wait()`.  Write that down, and say the write must stay before the count-down for that reason, not for L1 locality, or someone will "optimize" it later.

_Verification: round 1 (R1-19), not addressed | evidence: h/tron/models/kv_cache.hpp:595; h/tron/models/kv_cache.hpp:596; h/tron/models/model.hpp:2791_

#### `h/tron/models/kv_cache.hpp:602` R3-04 (A3)

```cpp
  598  //      goes through copy_storage_slot, which regenerates the mirror from
  599  //      the DESTINATION's just-copied canonical K, so it is coherent no
  600  //      matter the source book's mirror state.
  601  // Both sites address the plane of the PHYSICAL slot the canonical row lives
  602* // in: under the EAGLE storage view (set_storage_view) mirror() remaps logical
  603  // slot 0 to the extra physical slot exactly as kv_block() does, so the
  604  // draft's write-through can never land in the validator's slot-0 plane.
  605  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  606  // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  607  // the mirror checks in t/t_llama_unit.cpp (append + defrag, and the EAGLE
```

Only the `save_k` write-through goes through `mirror()`; `copy_storage_slot` (:1883) addresses the arena by physical `storage_offset` and never sees the view.  "Both sites ... mirror() remaps" sends a reader looking for view handling in the rebuild.  Scope the sentence to site 1.

_Verification: round 3 (R3-04), not addressed | evidence: h/tron/models/kv_cache.hpp:602; h/tron/models/kv_cache.hpp:603; h/tron/models/kv_cache.hpp:1885_

#### `h/tron/models/kv_cache.hpp:607` R1-20 (A3)

```cpp
  605  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  606  // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  607* // the mirror checks in t/t_llama_unit.cpp (append + defrag, and the EAGLE
  608  // storage-view cases).
```

There is no separate defrag operation; `append` is the defrag path and the test calls it once.  s/(append + defrag)/(`book::append`, the defrag path)/.  This sentence was edited in 96b5a6c72 and kept "(append + defrag)".

_Verification: round 1 (R1-20), not addressed | evidence: h/tron/models/kv_cache.hpp:607; h/tron/models/kv_cache.hpp:597_

#### `h/tron/models/kv_cache.hpp:770` R2-03 (A12/A6)

```cpp
  764    // Legacy form for callers that carry no model information (tests): no
  765    // mirror arena. The default is the direction that allocates nothing; a test
  766    // that exercises the mirror says so through the 4-argument constructor.
  767    book(size_t n_pages,
  768        size_t storage_slot_count = n_slots,
  769        bool support_eagle = false) noexcept
  770*   : book(n_pages, storage_slot_count, support_eagle, /*amx_mirror_eligible=*/false) {}
  771  
  772    // The constructor that carries the mirror-eligibility decision: the
  773    // scheduler passes amx_mirror_eligible(plugin::attention_kernels), so a
  774    // model without an AMX-eligible attention shape allocates no mirror arena.
  775    book(size_t n_pages,
```

A constructor that defaults `amx_mirror_eligible` to true allocates the arena for a book that may never read it - the thing this commit set out to stop.  Who still needs the 3-argument forms?  As far as I can see the tests, and the `sequence_cache_behavior` concept at :1328-1330, which now describes yesterday's interface.  Let's update the concept to the 4-argument forms, pass the flag explicitly in the tests (about 24 sites), and flush the delegating overloads (here and `try_create` at :965).  Also, "keeps today's behavior" describes the diff, not the code.  The new EAGLE coherence test (`t_llama_unit.cpp:338`) relies on the arena and therefore on this implicit `true` - a third user of the 3-argument form (with `:272`).  Pass the flag explicitly there either way.  The allocating default is gone, which was the part that mattered.  What still keeps the 3-argument forms alive is the tests and `sequence_cache_behavior` at :1356-1358, which now requires an interface production never calls (`full.hpp:834` passes four) - shall we move the concept to the 4-argument forms and drop the two overloads, or is there a caller I am not seeing?  Can be a follow-up PR if desired.

**Suggested fix** (added at your request)

1. Keep the 3-argument spelling (every test and the `sequence_cache_behavior` concept use it) but as defaulted trailing parameters of ONE constructor and ONE `try_create`, instead of two delegating overloads: the same calls compile, the default is still the direction that allocates nothing, and there is one signature to read.
2. The concept (:1356-1358) then needs no change (a 3-argument call still satisfies `constructible_from<T, size_t, size_t, bool>`); moving it to four arguments becomes optional. R2-07's misattributed 'the scheduler passes' sentence disappears with the second comment.

`h/tron/models/kv_cache.hpp`:764-778 - one constructor; replaces both comments and both signatures (line 779 `: n_pages(n_pages)` follows unchanged)

```suggestion
  // `amx_mirror_eligible` is amx_mirror_eligible(plugin::attention_kernels)
  // for the model this book serves (the scheduler computes it; tests pass it
  // explicitly): a model without an AMX-eligible attention shape allocates no
  // mirror arena. The default is the direction that allocates nothing.
  book(size_t n_pages,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false,
      [[maybe_unused]] bool amx_mirror_eligible = false) noexcept
```

`h/tron/models/kv_cache.hpp`:976-991 - one try_create; replaces the delegating overload, its body and the second comment (the STORY-127 comment above stays; line 992 `auto const sizes =` follows unchanged)

```suggestion
  // `amx_mirror_eligible` as for the constructor; the scheduler's production
  // path passes all four arguments (full.hpp).
  TRON(nodiscard)
  static std::shared_ptr<book> try_create(size_t n_pages,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false,
      bool amx_mirror_eligible = false) noexcept {
```

_Fix note: Applied to a scratch copy of the tree at 3fa11d911 and syntax-checked with the build's own compile commands (clang++-19 -fsyntax-only, both AMX options ON): t/t_amx_arena_leak.cpp, t/t_llama_unit.cpp (all 3- and 4-argument sites) and a TU instantiating `full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>` (covers full.hpp:833) - 0 errors each. Not built or run. Diff and logs: exec/review-pipeline/r6/fix/kv_cache.diff, arena.log, llama.log, tu.log. His stated preference in R2-03 was no default at all; this variant answers 'two overloads for one purpose' while keeping your decision to leave the 3-argument calls in place._

_Verification: round 2 (R2-03), partial: Met: the allocating default is gone (book :770 and try_create :980-981 delegate with false; node_base default false at full.hpp:311; 'keeps today's behavior' sentence removed); every test that reads the mirror passes true explicitly (t_llama_unit.cpp 272-273, 339-340, 478-481, 1080-1083; t_amx_arena_leak.cpp 79-80, 133-134; mirror-reading code grep: k_mirror_data only at 306-382, 522-536, 1121-1145, all inside those tests). Not met: the two delegating 3-argument overloads still exist (:767-770, :977-982) and the sequence_cache_behavior concept (:1356-1358) still requires the 3-argument constructor and try_create, an interface production never calls (full.hpp:833-834 passes four arguments); 19 non-mirror test sites still use the 3-argument forms (t_llama_unit.cpp 111, 257, 964-965, 1008, 1031-1032, 1158, 1162, 1168, 1227, 1397, 1620, 1625, 1634, 1638, 1648, 1682-1684, 1846-1847, 1952). | evidence: h/tron/models/kv_cache.hpp:770; h/tron/models/kv_cache.hpp:764; h/tron/models/kv_cache.hpp:981 | your triage: done (b2010bee9) - 3-argument book/try_create forms default amx_mirror_eligible to false; tests pass the flag explicitly; node_base default follows_

#### `h/tron/models/kv_cache.hpp:772` R2-07 (A3)

```cpp
  772*   // The constructor that carries the mirror-eligibility decision: the
  773    // scheduler passes amx_mirror_eligible(plugin::attention_kernels), so a
  774    // model without an AMX-eligible attention shape allocates no mirror arena.
  775    book(size_t n_pages,
  776        size_t storage_slot_count,
  777        bool support_eagle,
  778        [[maybe_unused]] bool amx_mirror_eligible) noexcept
```

"The only constructor that carries the mirror-eligibility decision" - the adopt-constructor at :1005 carries it too, and the scheduler's path is `try_create` (`full.hpp:832`) into that one; nothing in production reaches this constructor (its sole caller is `t_amx_arena_leak.cpp:123`).  Same for the "see the 4-argument constructor" pointer at :972.  Fix the comments, or the code.  b2010bee9 dropped "only" but kept "the scheduler passes": the scheduler still goes `try_create` (`full.hpp:833`) into the adopt-constructor at :1013, and all nine callers of this constructor are in `t/` - as :766 above now says itself.  s/the scheduler passes/callers pass/ here, and point the "(see the 4-argument constructor)" at :984 at the adopt-constructor, or drop it.

**Suggested fix** (added at your request)

Replace lines 772-774 with:

```suggestion
  // The constructor that carries the mirror-eligibility decision: callers
  // pass amx_mirror_eligible(plugin::attention_kernels) (the scheduler's path
  // is try_create into the adopt-constructor below), so a model without an
  // AMX-eligible attention shape allocates no mirror arena.
```

_Fix note: Only needed if the R2-03 single-constructor variant is not taken (that variant replaces this comment). The '(see the 4-argument constructor)' pointer at :984-985 should then point at the adopt-constructor (:1013) or go._

_Verification: round 2 (R2-07), partial: 'only' was dropped (:772), but the sentence still says the scheduler passes the flag into this constructor; the scheduler's path is try_create (full.hpp:833-834) into the adopt-constructor (:1013-1028), which carries the same flag. The pointer '(see the 4-argument constructor)' at :984-985 is unchanged. The 'sole caller' fact has changed: the 4-argument public constructor is now called from t_llama_unit.cpp (272, 339, 478, 480, 1080, 1082) and t_amx_arena_leak.cpp (79, 125, 133); no production caller (grep for direct book construction in h/tron/scheduler, h/tron/models, src finds none). | evidence: h/tron/models/kv_cache.hpp:772; h/tron/models/kv_cache.hpp:773; h/tron/models/kv_cache.hpp:984_

#### `h/tron/models/kv_cache.hpp:778` R2-04 (B4)

```cpp
  775    book(size_t n_pages,
  776        size_t storage_slot_count,
  777        bool support_eagle,
  778*       [[maybe_unused]] bool amx_mirror_eligible) noexcept
  779    : n_pages(n_pages)
```

`model.hpp` spells this `tron_maybe_unused` two lines from your other change; same here (and at :1005)?

_Verification: round 2 (R2-04), not addressed | evidence: h/tron/models/kv_cache.hpp:778; h/tron/models/kv_cache.hpp:1018; h/tron/models/model.hpp:2773_

#### `h/tron/models/kv_cache.hpp:1050` R3-03 (B7/A7)

```cpp
 1045    std::unique_ptr<uint8_t[], mirror_delete> mirror_arena_;
 1046    // The storage offset selected by set_storage_view(), or nullopt when no
 1047    // view is active. The mirror arena has no shifted base pointer of its own,
 1048    // so mirror() consults this to follow the view the way kv_block() follows
 1049    // kv_blocks_alias. See Note [K mirror coherence].
 1050*   std::optional<kv_storage_offset> mirror_view_offset_;
 1051  
```

So the view now lives in two members that must move together (`kv_blocks_alias` and `mirror_view_offset_`), set and cleared in two places, with no statement or assert that they agree.  The layout Note at :495 already describes the design for this: views "preselect their base pointer when the view changes".  A `mirror_alias` set next to `kv_blocks_alias` would make `mirror()` textually `kv_block()` on the other arena - no optional, no branch, one view to keep in sync.  Whichever stays, say here who writes it (the work_queue thread around `state.forward`, `full.hpp:1729-1740`) and who reads it (the RX and attention workers that forward dispatches), since that dispatch is what publishes a plain store to them - the same contract `kv_blocks_alias` has never written down either.

_Verification: round 3 (R3-03), not addressed | evidence: h/tron/models/kv_cache.hpp:1050; h/tron/models/kv_cache.hpp:1046; h/tron/models/kv_cache.hpp:843_

#### `h/tron/models/kv_cache.hpp:1057` R1-21 (A6/A3)

```cpp
 1057*     if (!amx_mirror_eligible || !amx_attn::available()) return;
 1058      size_t const bytes =
 1059          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1060              .kv_bytes /
 1061          2;
 1062      mirror_arena_.reset(static_cast<uint8_t*>(
 1063          ::operator new[](bytes, std::align_val_t(64), std::nothrow)));
 1064      // On failure the arena stays null and consumers fall back;
 1065      // see Note [K mirror parallel arena].
```

If `available()` is true and this `new` fails, we run a K_MIRROR build with no AMX QK at all (the canonical kernel is `#else`'d out in `apply_page_tok`) and nothing says so - silent bad performance instead of a loud error.  At least `spdlog::warn` once; better, keep `qk_canonical_128x4` as the fallback in the mirror build.  Also, `kv_bytes/2` of host RAM per book appears in neither `log_kv_footprint` nor `dma_size_bytes()`, and main's `Note [DMA-sized KV books]` (9076993a0) now says every buffer a book owns fits one DMA allocation - that Note needs the arena as an exception when you rebase.

_Verification: round 1 (R1-21), not addressed | evidence: h/tron/models/kv_cache.hpp:1057; h/tron/models/kv_cache.hpp:1063; h/tron/models/kv_cache.hpp:1064 | refuter: Status and new_line stand; only the snippet range needs correction: 1052-1065 is 14 lines, over the 2-10 rule. Use 1057-1065 (9 lines): :1057 '    if (!amx_mirror_eligible || !amx_attn::available()) return;' (R5:1055 identical, +2), :1058-1061 the kv_bytes/2 size, :1062-1063 '::operator new[](bytes, std::align_val_t(64), std::nothrow)', :1064-1065 '// On failure the arena stays null and consumers fall back; see Note [K mirror parallel arena].'. All 'remaining' sentences verified: grep spdlog in kv_cache.hpp hits only :482 and :1482; grep qk_canonical_128x4 in self_attention.hpp hits only :1578, inside '#else' :1576 of '#ifdef TRON_AMX_K_MIRROR' :1558, and :1562-1564 say 'nullptr (arena absent) falls through / to the dotter loop below, did_amx stays false'. dma_size_bytes :826-831 returns sizes->total_bytes, and :1117 computes total_bytes as checked_add(kv_bytes, x_storage_bytes, total_bytes) - no arena term - and log_kv_footprint (:464-483) is fed only dma_size_bytes() at :800/:804/:1031. 'Note [DMA' greps in HEAD and BASE h/ src/ doc/ hit only 'Note [DMA fault injection seam]' (memory.hpp:251). Commit 9076993a0 ('Bound KV books by DMA allocation size') exists in the repo, adds '// Note [DMA-sized KV books]', and is an ancestor of neither 3fa11d911 nor 1407f48dd, so 'main-side note, not yet rebased in' is right. No triage entry._

#### `h/tron/models/kv_cache.hpp:1060` R1-22 (A5)

```cpp
 1058      size_t const bytes =
 1059          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1060*             .kv_bytes /
 1061          2;
```

This `/ 2`, and the two in `mirror_at_storage`, are the `kv_block_planes` you just introduced, written as a literal.  Use it, or `static_assert(kv_block_planes == 2)` next to them, so the two can't drift.

_Verification: round 1 (R1-22), not addressed | evidence: h/tron/models/kv_cache.hpp:1060; h/tron/models/kv_cache.hpp:1061; h/tron/models/kv_cache.hpp:1244_

#### `h/tron/models/kv_cache.hpp:1235` R1-23 (B4/A5)

```cpp
 1235*   bf16* mirror_at_storage(
 1236        kv_storage_offset offset, size_t kv_head, size_t pg) noexcept {
 1237      if (!mirror_arena_) return nullptr;
 1238      constexpr size_t plane_bytes = page_size * geometry.head_size * sizeof(bf16);
 1239      TRON_ASSERT_LT(pg, n_pages);
 1240      TRON_ASSERT_LT(kv_head, geometry.n_kv_heads);
 1241      size_t byte_base;
 1242      if (offset.i < logical_slot_count()) {
 1243        byte_base = n_pages * (layout_t::offsets.values[offset.i] / 2);
 1244      } else {
```

`kv_block_at_storage` asserts `slot_matches<geometry>` and the EAGLE offset; this copy of its `byte_base` branch asserts nothing, so a mismatched geometry silently computes `plane_bytes` for the wrong head size and can run off the end of the arena.  Factor one `storage_byte_base<geometry>(offset)` helper used by both, so the mirror inherits the asserts.  The eagle-offset assert arrived; `slot_matches<geometry>` on the logical branch did not, and the two `byte_base` branches are still a copy of each other.  The shared helper would give both.

_Verification: round 1 (R1-23), partial: Unchanged since round 1's partial state: the EAGLE-offset assert is present (:1246), but the logical branch (:1243-1244) still has no `slot_matches<geometry>` assert (which `kv_block_at_storage` has at :1206) and no `geometry == primary_geometry` assert on the EAGLE branch (:1212 in the original); `storage_byte_base` helper does not exist (grep: none). Anchor shifted 1233->1235 (+2). | evidence: h/tron/models/kv_cache.hpp:1235; h/tron/models/kv_cache.hpp:1243; h/tron/models/kv_cache.hpp:1244 | refuter: Status PARTIAL and new_line 1235 stand ('  bf16* mirror_at_storage(' = R5:1233, +2); only the snippet range needs correction: 1235-1249 is 15 lines, over the 2-10 rule. Use 1235-1244 (10 lines), which ends on the unasserted logical branch :1243 '    if (offset.i < logical_slot_count()) {' / :1244 '      byte_base = n_pages * (layout_t::offsets.values[offset.i] / 2);'. Evidence verified: EAGLE-branch assert present at :1246 'TRON_ASSERT(has_eagle_storage() && offset == eagle_storage_offset(),'; the only asserts before the branch are :1239 TRON_ASSERT_LT(pg, n_pages) and :1240 TRON_ASSERT_LT(kv_head, geometry.n_kv_heads); no slot_matches on the logical branch (slot_matches hits: :1164 def, :1206 in kv_block_at_storage, :1291) and no 'geometry == layout_t::primary_geometry' assert (only :1212 in kv_block_at_storage); 'grep storage_byte_base': exit 1. No triage entry. followup_voice checks out: single question, 'we', backticks, no tags, and both facts it states (two byte_base branches :1204-1215 vs :1242-1249; logical branch asserts nothing) hold at HEAD._

#### `h/tron/models/kv_cache.hpp:1515` R1-26 (A3)

```cpp
 1515*   // Raw pair-interleaved V storage of one (slot, kv_head) for this page,
 1516    // consumed as-is by the AMX PV kernel (TRON_AMX_DISPATCH).
 1517    template <kv_geometry geometry>
 1518      requires(book_t::template declares_geometry<geometry>())
 1519    TRON(nodiscard, inline, pure)
 1520    const bf16* v_data(kv_slot_id slot, size_t kv_head) const noexcept
 1521        TRON(this_lifetimebound)
 1522    {
 1523      return kv_block<geometry>(slot, kv_head).v_base();
 1524    }
```

This accessor (and `v_base()` at :2100) exists in every build, but the layout it describes exists only under `TRON_CHUNK_SIZE == 16`; the `#else` branch is plain `[p][i/C][i%C]`.  Guard the accessors the same way, or say so in the comment.

_Verification: round 1 (R1-26), not addressed | evidence: h/tron/models/kv_cache.hpp:1515; h/tron/models/kv_cache.hpp:1523; h/tron/models/kv_cache.hpp:2146_

#### `h/tron/models/kv_cache.hpp:1882` R1-27 (A7/B1)

```cpp
 1881  #ifdef TRON_AMX_K_MIRROR
 1882*       // Rebuild the mirror for the copied tokens from the destination's
 1883        // just-copied canonical K. This is THE defrag/page-move coherence
 1884        // site. See Note [K mirror coherence].
 1885        if (bf16* plane = book.template mirror_at_storage<geometry>(
 1886                storage_offset, kv_head, pageno())) {
 1887          for (size_t i = 0; i < count; ++i) {
 1888            detail::scatter_k_mirror<page_size, geometry.head_size>(
 1889                plane, dst_begin + i, dst + i * geometry.head_size);
 1890          }
```

One sentence here on who runs this and why concurrent readers are safe (scheduler thread under `tree_lock`; only fresh tokens at or past `tok_ct`; the mirror's only reader needs all 64 tokens live).  The 16-tokens-per-line layout means these stores touch lines that also hold live tokens' columns, which is exactly what the next reader will worry about.

_Verification: round 1 (R1-27), not addressed | evidence: h/tron/models/kv_cache.hpp:1882; h/tron/models/kv_cache.hpp:1883; h/tron/models/kv_cache.hpp:1884 | refuter: Status and new_line stand: :1882 '      // Rebuild the mirror for the copied tokens from the destination's' (R5:1880 identical, +2), and diff of R5:1880-1884 against HEAD:1882-1886 is empty. Only the snippet range needs correction: 1881-1892 is 12 lines, over the 2-10 rule; use 1881-1890 (10 lines: '#ifdef TRON_AMX_K_MIRROR' :1881, the three comment lines, the mirror_at_storage if at :1885-1886, the scatter_k_mirror loop :1887-1890). 'remaining' verified: the comment :1882-1884 says only 'This is THE defrag/page-move coherence site. See Note [K mirror coherence].'; that Note (:588-620) names copy_storage_slot as a write site but says nothing about the calling thread, a lock, tok_ct, or reader safety; 'grep tree_lock' in kv_cache.hpp: exit 1 (tree_lock is defined in scheduler/token_cache_policy.hpp:90); tok_ct appears in kv_cache.hpp only as the counter (:795, :885, :893-901), not in this function. The enclosing function is copy_storage_slot (:1865-1866), called from :1917 and :1926 inside kv_cache.hpp. No triage entry._

### h/tron/models/model.hpp

#### `h/tron/models/model.hpp:2764` R2-08 (A3)

```cpp
 2763  #ifdef TRON_AMX_K_MIRROR
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

_Verification: round 2 (R2-08), not addressed | evidence: file unchanged since 234c02bde_

#### `h/tron/models/model.hpp:2771` R1-28 (A1/A8/B7)

```cpp
 2769        constexpr bool k_mirror_shape_ok =
 2770            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 2771*       const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();
 2772  #endif
 2773        tron_maybe_unused const bool has_legacy_hardware_binding =
 2774            geometry == self_attn_t::legacy_geometry &&
 2775            operation_has_legacy_hardware_binding(operation);
```

This gates the write-through on `available()` only, but the only reader is behind `head_size == 128 && kv_mul == 4`.  On an AMX host running any other geometry (or any non-matching slot of a mixed layout) the RX worker pays the scatter (and `copy_storage_slot` the rebuild) and the book the `kv_bytes/2`, for planes nobody reads.  Gate the write, the rebuild, and the arena on the same predicate as the reader.  Also, `set_k_mirror` already no-ops on a null plane, so as written `k_mirror_on` is redundant with the arena condition rather than a correctness guard; the comment should say which it is.  And `model.hpp` calls `amx_attn::available()` without including its header.  Good on the gate.  Inside the `if constexpr`, `k_mirror_on` is just `available()`, and that is still redundant with the null check in `set_k_mirror`; say it is an early-out, or drop it.  Also, for an ineligible geometry `k_mirror_on` is now an unused local in a K_MIRROR build - `has_legacy_hardware_binding` two lines down needed `tron_maybe_unused` for exactly this shape; move the bool inside the `if constexpr`.  And `model.hpp` still doesn't include `amx_attn_iface.hpp` itself.

_Verification: round 1 (R1-28), not addressed | evidence: file unchanged since 234c02bde_

### h/tron/models/self_attention.hpp

#### `h/tron/models/self_attention.hpp:19` R1-29 (B15/B4)

```cpp
   12  #include <vector>
   13  
   14  #include "common/assert.hpp"
   15  #include "common/numerics/fp16.hpp"
   16  #include "common/util.hpp"
   17  #include "libpos.hpp"
   18  #include "spdlog/spdlog.h"
   19* #include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free; used when TRON_AMX_DISPATCH
   20  #include "tron/kernels/dotter.hpp"
```

`kv_cache.hpp` guards its include of `amx_attn_iface.hpp` under the flag; here both new headers are unconditional.  Pick one convention.  Also, `<cstdint>` is now used directly (`uint16_t`, `uint64_t`) and not included.  The include convention is now 'unconditional in both', fine.  `<cstdint>` is still not included here.

_Verification: round 1 (R1-29), not addressed | evidence: h/tron/models/self_attention.hpp:19; h/tron/models/self_attention.hpp:3; h/tron/models/self_attention.hpp:1361_

#### `h/tron/models/self_attention.hpp:1361` R1-31 (A1/B7)

```cpp
 1361*       thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          // resize() zero-fills new slots and the packers write only the 4
 1369          // live columns/rows of each slot, so the padding they rely on stays
 1370          // zero for the thread's lifetime (see the pack contracts).
 1371          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1372          amx_attn::begin_region();
 1373        }
```

Why lazy?  Packing all `items.size()` groups once before the page loop is at most `max_minibatch_size` 512-byte copies and deletes the bitmap and the per-(page, token) test-and-set.  If a cache is really wanted, `attn_accum` is already per worker, per token and 64B-aligned; a growable `thread_local std::vector` is neither aligned (see the header contract) nor bounded the way the mask next to it is.  Also, `resize()` here zero-fills the new tail every time `items.size()` grows past the previous call's, and the pack (`pack_q_group_128x4`, or `pack_q_rows_128x4` in the mirror build) then writes the same 4 KB again - and it is 4 KB out per group, not the 512 B I wrote above.  Fixed `alignas(64)` storage sized by `max_minibatch_size` would settle this, the alignment contract, and the bitmap in one move; if the vector stays, at least `if (amx_qpack.size() < n) amx_qpack.resize(n)`.

_Verification: round 1 (R1-31), not addressed | evidence: h/tron/models/self_attention.hpp:1361; h/tron/models/self_attention.hpp:1366; h/tron/models/self_attention.hpp:1371_

#### `h/tron/models/self_attention.hpp:1361` **reply** to Codex comment 3858305367 (C2/A3)

```cpp
 1359            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 1360        const bool amx_on = amx_shape_ok && amx_attn::available();
 1361*       thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
```

> jeremyconner1975 (Codex): The kernel interface requires each packed-Q buffer to be 64-byte aligned, but `std::vector<uint16_t>` guarantees only `alignof(uint16_t)`. Since each slice is exactly 4096 bytes, every query inherits the base misalignment and TILELOADD can repeatedly straddle cache lines. Could this use a 64-byte-aligned allocator or aligned fixed storage?
> 
> - Codex review, submitted at Jeremy's request

Codex has a point about the alignment, and it's the same one as my question at `amx_attn_iface.hpp:102`: `amx_qpack` is a `std::vector<uint16_t>`, so every 4 KB slice inherits whatever `malloc` handed us (16 mod 64 in nearly every allocation when I tried it on glibc; 0 mod 64 only by accident).  The other two 64B contracts (`o` at :123, `s` at :163) are honored by `alignas(64)` storage at `self_attention.hpp:1568` and `:1652`; this is the only one that isn't.  Let's either give it `alignas(64)` storage or drop "64B-aligned" from the contract (:102 and :156); whether the split rows actually cost anything is a per-page timing with the pack at 0 vs 16 mod 64, not something to assert either way.

_Verification: round 5 (R5-03), not addressed | evidence: h/tron/models/self_attention.hpp:1361; h/tron/kernels/amx_attn_iface.hpp:102; h/tron/kernels/amx_attn_iface.hpp:160_

#### `h/tron/models/self_attention.hpp:1366` R1-32 (A5)

```cpp
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366*       uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          // resize() zero-fills new slots and the packers write only the 4
 1369          // live columns/rows of each slot, so the padding they rely on stays
 1370          // zero for the thread's lifetime (see the pack contracts).
 1371          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1372          amx_attn::begin_region();
 1373        }
```

The comment says `items.size() <= max_minibatch_size`; who enforces it?  (`batch_evenly` does, `model.hpp:326`, but it's a long way from here - a `TRON_ASSERT_LE(items.size(), max_minibatch_size)` next to the mask costs nothing.)

_Verification: round 1 (R1-32), not addressed | evidence: h/tron/models/self_attention.hpp:1365; h/tron/models/self_attention.hpp:1366; h/tron/models/model.hpp:326_

#### `h/tron/models/self_attention.hpp:1367` R1-34 (B6/A12)

```cpp
 1367*       if (amx_on) {
 1368          // resize() zero-fills new slots and the packers write only the 4
 1369          // live columns/rows of each slot, so the padding they rely on stays
 1370          // zero for the thread's lifetime (see the pack contracts).
 1371          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1372          amx_attn::begin_region();
 1373        }
```

We have `tron::finally` (`h/common/util.hpp:73`, used in `gof.hpp:221`) for exactly this bracket; `tron::finally release([&] { if (amx_on) amx_attn::end_region(); });` makes the pairing structural.  Not a bug today (the function is `noexcept` and there is no return in between), your choice.

_Verification: round 1 (R1-34), not addressed | evidence: h/tron/models/self_attention.hpp:1367; h/tron/models/self_attention.hpp:1372; h/tron/models/self_attention.hpp:1468_

#### `h/tron/models/self_attention.hpp:1367` **reply** to Codex comment 3858305362 (C2/A1)

```cpp
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367*       if (amx_on) {
 1368          // resize() zero-fills new slots and the packers write only the 4
 1369          // live columns/rows of each slot, so the padding they rely on stays
 1370          // zero for the thread's lifetime (see the pack contracts).
 1371          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1372          amx_attn::begin_region();
 1373        }
```

> jeremyconner1975 (Codex): `amx_on` only checks geometry and CPU support, so every eligible page range executes LDTILECFG/TILERELEASE and packs each query before the dense-page predicate is evaluated. Partial pages, masked/sliding-window pages, and null-mirror fallbacks therefore pay AMX setup plus a 4 KB pack even though every page uses AVX. Could we lazily begin the region and pack Q only when the first page actually satisfies the dense predicate?
> 
> - Codex review, submitted at Jeremy's request

Codex is right on the facts - `begin_region()` runs and each token's first visible in-window page pays a 1 KB-in / 4 KB-out pack (not the 512 B I wrote at :1361) before any page has passed the dense test, and PV only runs `if (did_amx)`, so a token whose range has no dense page uses its pack nowhere.  Two precisions: wholly masked or out-of-window pages skip at :1389/:1392 before the pack, and a null mirror with `amx_on` true means the arena allocation failed (`kv_cache.hpp:1055`, `:1060`).  I'd still go the other way from what Codex asks: the region pair is ~229 cycles against 686-1250 ns per dense page, so pack all `items.size()` groups up front and delete the bitmap.  If the calls with no dense page matter in the served shapes, count them per decode step first, before adding a second lazy mechanism inside `apply_page_tok`.  Two corrections to my own reply: since 35b3f3cae the pack writes 1 KB, not 4 KB (`pack_q_group_128x4` fills columns 0..3 only, `amx_attn.cpp:99-110`; `pack_q_rows_128x4` is one 1 KB `memcpy`, :229; `resize()` at :1371 zeroes the padding once), and since b2010bee9 a null plane with `amx_on` true no longer means the allocation failed - the 3-argument `book`/`try_create` forms (`kv_cache.hpp:770`, `:981`) never allocate the arena.  The first makes the eager version cheaper still, so the bitmap at :1366/:1419/:1434 has even less to defend.

_Verification: round 5 (R5-04), not addressed | evidence: h/tron/models/self_attention.hpp:1360; h/tron/models/self_attention.hpp:1366; h/tron/models/self_attention.hpp:1367 | refuter: Status NOT_ADDRESSED is right for the ask the reply carries (eager pack, delete bitmap): HEAD :1366 'uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};', :1419 'if (!((amx_packed_mask[batch_job_ix >> 6] >> (batch_job_ix & 63)) & 1)) {', :1434 'amx_packed_mask[batch_job_ix >> 6] |= 1ull << (batch_job_ix & 63);' unchanged; no triage entry. Structure claims verified at HEAD: :1360 'const bool amx_on = amx_shape_ok && amx_attn::available();', :1367 'if (amx_on) {' (same line as R5 and as the Codex comment's line 1367), :1371 resize / :1372 begin_region / :1468 end_region, skips :1392 and :1395-1397, pack :1424/:1429 before :1440 apply_page_tok, dense predicate :1555-1557, PV under :1625 'if (did_amx) {'. Pack-size correction verified: HEAD amx_attn.cpp has no memset (grep empty); :102-107 write HEAD_SIZE/DIM_STEP=4 steps x DIM_STEP/2=16 dim-pairs x GROUP_HEADS=4 x 2 = 512 bf16 = 1 KB; :229 'std::memcpy(padded, q_group, GROUP_HEADS * HEAD_SIZE * sizeof(uint16_t));' = 1 KB. Nit: R5 :236-237 was a 3 KB memset ('(TILE_ROWS - GROUP_HEADS) * HEAD_SIZE * sizeof(uint16_t)'), not 4 KB as 'remaining' says; only R5 :109 was 4 KB. '~229 cycles': grep over every PR-touched file finds no '229' (only iface :51 mentions TILERELEASE), so 'unverified' stands. Missed stale fact: 'a null plane with amx_on true only via the nothrow allocation' is now incomplete. b2010bee9 made the 3-argument forms pass false - kv_cache.hpp:770 ': book(n_pages, storage_slot_count, support_eagle, /*amx_mirror_eligible=*/false) {}' and :981 '/*amx_mirror_eligible=*/false);' - so :1057 'if (!amx_mirror_eligible || !amx_attn::available()) return;' leaves the arena null and :1237 'if (!mirror_arena_) return nullptr;' yields a null plane with amx_on true. The scheduler path (full.hpp:833-834 'book::try_create(bk_pages, storage_kv_slots, support_eagle, amx_mirror_eligible)', :1457) still passes the computed eligibility, so the claim holds for production, but the original reply's 'a null mirror with amx_on true means the arena allocation failed' is no longer exact and the followup should carry both corrections. Snippet 1360-1373 is 14 lines; use 1366-1373. followup_voice: facts right, but the rule gives followup_voice to PARTIAL only, and it omits the second correction._

#### `h/tron/models/self_attention.hpp:1493` R1-35 (A12/A9)

```cpp
 1490          const token_range* range_hint,
 1491          int sliding_window_size,
 1492          bool run_visible_in_software,
 1493*         const uint16_t* amx_q_packed = nullptr) {
 1494        constexpr size_t operation_kv_mul = geometry.kv_mul();
 1495        constexpr size_t operation_head_size = geometry.kv.head_size;
```

The default is never used (the one caller always passes `amx_qp`), and in a build without the flag the parameter is unreferenced - does the default build now warn under `-Wextra`?  CI didn't run, so I can't tell.  Drop the default, and I'd rather the OFF build's `apply_page_tok` were textually unchanged (parameter and `did_amx` under the flag).

_Verification: round 1 (R1-35), not addressed | evidence: h/tron/models/self_attention.hpp:1493; h/tron/models/self_attention.hpp:1442; h/tron/models/self_attention.hpp:1411_

#### `h/tron/models/self_attention.hpp:1511` R1-36 (A8/A3)

```cpp
 1510          using scalar_t = typename btensor_t<operation_head_size>::element;
 1511*         for (size_t offset = 0; offset < operation_kv_mul; ++offset)
 1512            s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f);
 1513          // `dotter` binds to a view at construction and has no default
 1514          // constructor, so we can't declare a std::array<dotter,...> and fill
 1515          // it in a loop. Pack-expand `kv_mul` constructor calls inside the
 1516          // array initializer instead. Worth the syntax because `kv_mul` is a
 1517          // compile-time constant and this is the per-page hot path, so we
 1518          // avoid the heap allocation a std::vector<dotter> would incur.
 1519          std::array<dotter<scalar_t, operation_head_size>, operation_kv_mul> dot_q =
```

On the pages AMX takes, the four `dotter` constructions here (16 zmm loads) and the `-inf` init of `s_pages` are dead work per (page, token); moving them under `if (!did_amx)` is free.  Also, "share the bf16 -> fp32 conversion" describes `dotter<float, 128>`; the `dotter<bf16, 128>` used here converts nothing.  Pre-existing, but you're touching it.  The comment is gone, good; the four `dotter` constructions at :1519 and the `-inf` fill at :1511 still run on every page AMX takes, since `did_amx` is only decided at :1574 - shall we hoist the AMX test above them, or construct `dot_q` inside the `if (!did_amx)` at :1586?

_Verification: round 1 (R1-36), partial: The wrong comment line is gone (R5 :1510 '// share the bf16 -> fp32 conversion across the page' has no counterpart at HEAD; the block opens at :1509 and goes straight to `using scalar_t` at :1510). The -inf fill (:1511-1512) and the four `dotter` constructions (:1519-1524) still run unconditionally before the AMX block sets `did_amx` at :1574; only the dotter LOOP is under `if (!did_amx)` (:1586). Moving the fill and the constructions is not done. | evidence: h/tron/models/self_attention.hpp:1509; h/tron/models/self_attention.hpp:1510; h/tron/models/self_attention.hpp:1511 | refuter: Status PARTIAL holds. Triage 'partial' (275fa89a0) verified: R5 self_attention.hpp:1510 '// share the bf16 -> fp32 conversion across the page' has no counterpart at HEAD; HEAD :1509 '{' is followed directly by :1510 'using scalar_t = typename btensor_t<operation_head_size>::element;'. git show --stat 275fa89a0: 'h/tron/models/self_attention.hpp | 19 +++++--------------'; message: 'the "share the bf16 -> fp32 conversion" line described dotter<float, 128>, not the dotter<bf16, 128> used there.' Still open: HEAD :1511-1512 'for (size_t offset = 0; offset < operation_kv_mul; ++offset) / s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f);' and :1519 'std::array<dotter<scalar_t, operation_head_size>, operation_kv_mul> dot_q =' run before :1574 'did_amx = true;' (mirror build; :1581 canonical); :1586 'if (!did_amx) {' wraps only the loop. dot_q's sole use is :1607 's_pages[offset][i] = dot_q[offset](k);' and the memcpy at :1571-1572 overwrites all operation_kv_mul*page_size elements of s_pages, so both are dead work on AMX pages - the ask stands. new_line 1511 is right. Only correction: snippet 1508-1524 is 17 lines, rule is 2-10; use 1510-1519 (shows the -inf fill and the dot_q declaration). followup_voice line refs (:1519, :1511, :1574, :1586) all check out at HEAD. | your triage: partial (275fa89a0) - the wrong 'share the bf16 -> fp32 conversion' clause is removed; moving the dotter constructions and the -inf init under if (!did_amx) is not done._

#### `h/tron/models/self_attention.hpp:1571` R1-37 (A4/A8)

```cpp
 1565              if (const bf16* mplane =
 1566                      page.template k_mirror_data<geometry.kv>(slot, kv_head)) {
 1567                alignas(
 1568                    64) thread_local float qk_s[amx_attn::TILE_ROWS_16 * page::page_size];
 1569                amx_attn::qk_mirror_128x4(
 1570                    reinterpret_cast<const uint16_t*>(mplane), amx_q_packed, qk_s);
 1571*               std::memcpy(&s_pages[0][0], qk_s,
 1572                    operation_kv_mul * page::page_size * sizeof(float));
 1573                relevant_k_tokens = page::page_size;
 1574                did_amx = true;
```

So the mirror path pays a 1 KB copy per page that the canonical path doesn't, and the `amxqk` bench variant behind the 686 ns figure stores straight into a 16-row `S` with no copy.  Either size `s_pages` for 16 rows in the mirror build, or note the copy's cost next to the 300 ns claim.  Also, when `mplane` is null in this build we fall all the way to the dotter although `qk_canonical_128x4` is compiled into the same binary - why not fall back to it?  The bench half is settled with the file.  The rest stands: `qk_mirror_128x4` still lands in `qk_s` and we `memcpy` 1 KB into `s_pages` per page, while the ~560 ns at `amx_attn_iface.hpp:137` (1250 vs 686) was measured on a path that never paid that copy - either size `s_pages` for 16 rows in the mirror build, or say so next to the number?

_Verification: round 1 (R1-37), not addressed | evidence: h/tron/models/self_attention.hpp:1567; h/tron/models/self_attention.hpp:1568; h/tron/models/self_attention.hpp:1571 | refuter: Status NOT_ADDRESSED holds: no triage entry; R5 :1572-1573 == HEAD :1571-1572 'std::memcpy(&s_pages[0][0], qk_s, / operation_kv_mul * page::page_size * sizeof(float));' (4 x 64 x 4 B = 1 KB per page); :1506 'tensor<operation_kv_mul, page::page_size> s_pages;' and :1568 'thread_local float qk_s[amx_attn::TILE_ROWS_16 * page::page_size];' unchanged. amx_attn_iface.hpp:139-140 quoted verbatim ('// through memory and transpose it - a ~560 ns/page whole-path cost at' / '// width 4 (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19;'); grep -i copy over that header hits only :148 'a second, derived copy of K' - the memcpy is not mentioned. Null mplane: :1565 'if (const bf16* mplane =' has no else; the dotter loop at :1586 is the only fallthrough; qk_canonical_128x4 is called only under '#else' (:1576-1579) but amx_attn.cpp has no #ifdef around its definition (:117), so it is compiled into the mirror binary as the comment says. fused-sweep-v2.txt:30 'Nq=4 variant=amxqk pages=1 iters=200000 per_page_ns=686.0' confirmed. Corrections: snippet 1565-1575 is 11 lines; use 1565-1574 (mplane test through 'did_amx = true;'). new_line 1571 (the memcpy) is acceptable; the by-content shift of the R5 anchor :1566 (mplane) is :1565 - either is fine since the snippet covers both. Also, in extra_observations the 1249.9 amx44 figure is fused-sweep-v2.txt line 14 ('Nq=4 variant=amx44 pages=1 iters=200000 per_page_ns=1249.9'), not line 12 (line 12 is 'Nq=2 variant=amx44 ... per_page_ns=914.7')._

#### `h/tron/models/self_attention.hpp:1621` R1-38 (B11/B6)

```cpp
 1617        // When the dense AMX QK path ran, do the weights-times-values (PV)
 1618        // product for all four grouped heads in one tile call (see
 1619        // Note [AMX attention dispatch]). Pass 1 mirrors the per-head
 1620        // scale/max/exp math below exactly; pass 2 applies the same v*/s*/m*
 1621*       // updates, but from the AMX PV output instead of scaled_v. The
 1622        // `if constexpr` keeps this 4-head/128-dim block out of every other
 1623        // geometry's instantiation.
 1624        if constexpr (amx_shape_ok) {
 1625          if (did_amx) {
 1626            float corr_arr[operation_kv_mul], m_new_arr[operation_kv_mul],
```

This paragraph is justifying the code to the reviewer; "`if constexpr` so other geometries don't instantiate this block" is the whole content.  Flush the rest.  Also, pass 1 is a second copy of the per-head scale/softcap/max/exp/sum math below (I diffed them; identical today) - that is how they drift.  Pull the per-head part into a helper both loops call.  Comment is the right length now.  The scale/softcap/max/exp block at :1631-1641 is still a copy of :1675-1685 - shall we pull the per-head part into one helper both loops call, so they can't drift?

_Verification: round 1 (R1-38), partial: The justifying paragraph (R5 :1624-1631, 'The if-constexpr is runtime-redundant with did_amx ... COMPILED into every other geometry's instantiation as dead code ...') is replaced by one sentence at HEAD :1621-1623. Pass 1 (:1628-1643: softcap/scale, max, was_valid max, exp, sum) is still a second copy of the per-head math in the AVX loop (:1670-1685); no shared helper exists. | evidence: h/tron/models/self_attention.hpp:1621; h/tron/models/self_attention.hpp:1622; h/tron/models/self_attention.hpp:1623 | your triage: partial (275fa89a0) - the justifying paragraph is flushed (one fact kept); pulling the duplicated per-head scale/softcap/max/exp/sum math into a shared helper is not done._

#### `h/tron/models/self_attention.hpp:1654` R1-39 (A8)

```cpp
 1652              scratchpad_ref<geometry> head_sp = sp[kv_head * operation_kv_mul + offset];
 1653              tensor<operation_head_size> scratch;
 1654*             std::memcpy(&scratch[0], amx_o + offset * operation_head_size,
 1655                  operation_head_size * sizeof(float));
 1656              if (was_valid) {
 1657                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1658                head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
 1659                head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
 1660              } else {
 1661                head_sp.v_star.set(scratch);
```

Any reason not to point a `const_view<float, true, false, seq<128>>` at `amx_o + offset * 128` instead of copying 512 B per head into `scratch`?  The AVX path feeds `fma` an expression for the same reason.

_Verification: round 1 (R1-39), not addressed | evidence: h/tron/models/self_attention.hpp:1653; h/tron/models/self_attention.hpp:1654; h/tron/models/self_attention.hpp:1655 | refuter: Status NOT_ADDRESSED holds: no triage entry; R5 :1659-1661 == HEAD :1653-1655 'tensor<operation_head_size> scratch; / std::memcpy(&scratch[0], amx_o + offset * operation_head_size, / operation_head_size * sizeof(float));' (128 x 4 B = 512 B per head), consumed at :1658 'head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));' and :1661 'head_sp.v_star.set(scratch);'. view.hpp:361-362 quoted verbatim ('struct const_view<T, aligned, dma, seq<d0>, sseq<s0>> final' / ': expr<const_view<T, aligned, dma, seq<d0>, sseq<s0>>, d0> {'); :370 'T const* data;' shows the 1-D const_view wraps a raw pointer, so the comment's alternative exists. new_line 1654 (memcpy) acceptable; the by-content shift of the R5 anchor :1659 ('scratch') is :1653 - either is fine. Correction: snippet 1651-1663 is 13 lines; use 1652-1661 (head_sp, scratch, memcpy, fma, else set(scratch))._

#### `h/tron/models/self_attention.hpp:1657` R1-40 (A5)

```cpp
 1656              if (was_valid) {
 1657*               auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1658                head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
 1659                head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
```

`constant<page::page_size>` (64 wide) as the multiplier in a 128-wide `fma` only works because `constant::chunk(i)` ignores `i`.  Pre-existing at :1685, but let's not copy it: `constant<operation_head_size>`.

_Verification: round 1 (R1-40), not addressed | evidence: h/tron/models/self_attention.hpp:1657; h/tron/models/self_attention.hpp:1658; h/tron/models/self_attention.hpp:1689_

### h/tron/scheduler/full.hpp

#### `h/tron/scheduler/full.hpp:1457` R2-10 (B3)

```cpp
 1451        const size_t logical_kv_slots =
 1452            cache_t::logical_slot_count_for_layers(max_layers);
 1453        const size_t storage_kv_slots =
 1454            cache_t::storage_slot_count_for_layers(max_layers, cfg->support_eagle);
 1455        root = std::make_shared<node_t>(logical_kv_slots, storage_kv_slots,
 1456            cfg->support_eagle,
 1457*           amx_mirror_eligible(model_t::plugin_t::attention_kernels));
 1458      }
```

`amx_mirror_eligible` is now the name of the predicate over kernels, a `node_base` member, and two constructor parameters.  Inside `node` methods the member shadows the function.  `has_amx_attention_shape(kernels)` for the predicate would keep them apart.

_Verification: round 2 (R2-10), not addressed | evidence: h/tron/scheduler/full.hpp:1457; h/tron/scheduler/full.hpp:311; h/tron/scheduler/full.hpp:712_

### src/tron/CMakeLists.txt

#### `src/tron/CMakeLists.txt:174` R1-41 (A3)

```cmake
  170  # TODO(jhan): no CI configuration compiles or runs the code behind these two
  171  # options (https://github.com/positron-ai/tron/issues/3997). Until the CI team
  172  # adds one, verify both configurations on an AMX host before pushing; the
  173  # recipe is in the issue.
  174* option(TRON_AMX_DISPATCH "Enable AMX software-attention dispatch (Granite Rapids)" OFF)
```

AMX-BF16 is Sapphire Rapids and later, and the code gates on CPUID bits, not the model.  s/(Granite Rapids)/(requires AMX-BF16)/.

_Verification: round 1 (R1-41), not addressed | evidence: src/tron/CMakeLists.txt:174_

#### `src/tron/CMakeLists.txt:188` R1-42 (A1)

```cmake
  185  if(TRON_AMX_DISPATCH)
  186    target_sources(tron PRIVATE kernels/amx_attn.cpp)
  187    set_source_files_properties(kernels/amx_attn.cpp PROPERTIES
  188*     COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
  189    target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)
  190    if(TRON_AMX_K_MIRROR)
  191      target_compile_definitions(tron PUBLIC TRON_AMX_K_MIRROR)
  192    endif()
  193  endif()
```

Only `-mamx-tile -mamx-bf16` are new for this TU; the `-mavx512*`/`-mavx2`/`-mfma` are already PUBLIC on `tron` (:234-237) unless `AVX512=OFF`, in which case this would be the only AVX-512 code in a non-AVX-512 binary.  Is that build meant to exist?  If not, trim the list; if so, say so.

_Verification: round 1 (R1-42), not addressed | evidence: src/tron/CMakeLists.txt:188; src/tron/CMakeLists.txt:238; src/tron/CMakeLists.txt:239_

### src/tron/kernels/amx_attn.cpp

#### `src/tron/kernels/amx_attn.cpp:35` R1-46 (B3/B12)

```cpp
   34  // TDPBF16PS consumes the head dim in 32-dim steps (16 bf16 pairs per step).
   35* constexpr int DIM_STEP = 32;
   36  // Query heads per KV head - the GQA group width, the "x4" in the kernel names.
   37  constexpr int GROUP_HEADS = int(GROUP_HEADS_4);
```

`DIM_STEP` is documented as 32 head dims per k-step, but at :210 it means 32 tokens per PV k-step and at :211 it means 16 dims x 2 paired tokens per V tile column.  Three quantities with the same numeral shouldn't share a constant; name the other two.  Also, the `4` at :251 is `PAGE / TILE_ROWS`.

_Verification: round 1 (R1-46), not addressed | evidence: src/tron/kernels/amx_attn.cpp:34; src/tron/kernels/amx_attn.cpp:35; src/tron/kernels/amx_attn.cpp:206_

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

_Verification: round 1 (R1-59), not addressed | evidence: t/t_amx_arena_leak.cpp:46; t/t_amx_arena_leak.cpp:49; t/t_amx_arena_leak.cpp:7 | refuter: Status right: HEAD t/t_amx_arena_leak.cpp:46-70 (global aligned array new[]/delete[] replacements, :49 `void* operator new[](std::size_t n, std::align_val_t al) {`) and the header :7-8 (`// leaked arena or a mismatched allocation/deallocation form fails` / `// deterministically, without a sanitizer build.`) are byte-identical to R5; the delta touches only :75-84 and :124-138. src/pos/memperf.cpp:74 `void* operator new[](size_t size, std::align_val_t alignment) {` and :85-86 (nothrow form) still replace the same forms. No triage entry. Line: lines 1-70 did not move, so the R5 anchor 48 (`// stays pair-compatible with every other.`) is where the GitHub thread stays; the verifier's 49 is a drift its own remaining contradicts ('Lines unchanged from R5'). Keep 48; snippet 46-53 unchanged._

#### `t/t_amx_arena_leak.cpp:92` R2-11 (A3)

```cpp
   90    if (tron::amx_attn::available()) {
   91      // The arena allocation actually ran (maybe_allocate_mirror_arena is
   92*     // gated on available()), so the balance above covered it.
   93      REQUIRE(alloc_delta >= 1);
   94    } else {
   95      WARN("AMX unavailable on this host - the mirror arena never allocates, so "
   96           "only the trivial balance was checked");
   97    }
```

s/gated on available()/gated on the eligibility flag (true through the 3-argument form) and available()/.  s/gated on available()/gated on the eligibility flag (which this test now passes explicitly) and available()/.  And :78 has the other half: "Eligible, so the arena is allocated" is not so on a host without AMX, as the WARN at :95 says.  :129-130 already says it right; one sentence naming both conditions of `maybe_allocate_mirror_arena` covers both.

**Suggested fix** (added at your request)

1. Name both conditions of `maybe_allocate_mirror_arena` once, in each of the two comments that currently name one.

`t/t_amx_arena_leak.cpp`:77-79 - the leak-balance book's comment

```suggestion
    // The small uniform book shape t_llama_unit uses (2 layers, 1 KV head,
    // head size 128); 4 pages keeps the arena real but tiny. Eligible (the flag
    // below) and, when this host has AMX, allocated: maybe_allocate_mirror_arena
    // needs both; the 3-argument form passes false and allocates none.
```

`t/t_amx_arena_leak.cpp`:91-92 - the assertion's comment

```suggestion
    // The arena allocation actually ran (maybe_allocate_mirror_arena is gated
    // on the eligibility flag, passed above, and on available()), so the
    // balance above covered it.
```

_Fix note: Comment-only; line counts change by +1 and +1, so R1-60's `>= 1` moves to :95 if both are applied._

_Verification: round 2 (R2-11), not addressed | evidence: t/t_amx_arena_leak.cpp:91; t/t_amx_arena_leak.cpp:92; t/t_amx_arena_leak.cpp:81_

#### `t/t_amx_arena_leak.cpp:93` R1-60 (A10)

```cpp
   90    if (tron::amx_attn::available()) {
   91      // The arena allocation actually ran (maybe_allocate_mirror_arena is
   92      // gated on available()), so the balance above covered it.
   93*     REQUIRE(alloc_delta >= 1);
   94    } else {
   95      WARN("AMX unavailable on this host - the mirror arena never allocates, so "
   96           "only the trivial balance was checked");
   97    }
```

Can we tighten this to `== 1`?  With an example this small the count is predictable.  The new case does `== 1` (:133); this one still says `>= 1`.  Ditto.

_Verification: round 1 (R1-60), not addressed | evidence: t/t_amx_arena_leak.cpp:93; t/t_amx_arena_leak.cpp:136_

#### `t/t_amx_arena_leak.cpp:107` R2-12 (A3/B6)

```cpp
  105    // llama-3.3-70b (head 128, ratio 8) fails the ratio; qwen/llama-3.1
  106    // (ratio 4, head 128) pass.
  107*   static_assert(!tron::amx_attn::shape_ok(64, 8));
  108    static_assert(!tron::amx_attn::shape_ok(64, 4));
  109    static_assert(!tron::amx_attn::shape_ok(128, 8));
  110    static_assert(tron::amx_attn::shape_ok(128, 4));
```

These four evaluate `128 == 128 && 4 == 4` in four spellings; they can only fail if someone edits `shape_ok`.  If the point is that the registry shapes classify correctly, read them from `named_llama_configs::llama_3p2_1b` / `llama_3p1_8b` / `llama_3p1_70b` so the test follows the tree - and s/llama-3.3-70b/`llama_3p1_70b`/, which is the config that has this geometry.  gpt-oss and qwen-3-4b have no C++ geometry here, so say so or drop them.

_Verification: round 2 (R2-12), not addressed | evidence: t/t_amx_arena_leak.cpp:105; t/t_amx_arena_leak.cpp:107; t/t_amx_arena_leak.cpp:110_

#### `t/t_amx_arena_leak.cpp:125` R2-13 (A10/B14)

```cpp
  120    // A head-64 book built the way the scheduler builds it for an ineligible
  121    // model: the 4-argument constructor with amx_mirror_eligible=false must
  122    // perform no arena allocation, whether or not this host has AMX.
  123    const long long before_ineligible = aligned_array_allocs.load();
  124    {
  125*     tron::book<2, 1, 64, 0> cache(/*n_pages=*/4, /*storage_slot_count=*/2,
  126          /*support_eagle=*/false, /*amx_mirror_eligible=*/false);
  127      REQUIRE(aligned_array_allocs.load() - before_ineligible == 0);
  128    }
```

"built the way the scheduler builds it" - the scheduler goes through `try_create` (`full.hpp:832`) into the adopt-constructor, which this doesn't touch; this constructor's only caller is this test.  Can both arms run through `book_t::try_create(4, 2, false, false)` / `(4, 2, false, true)`, so the pair differs only in the flag and the plumbing we ship is what gets tested?  And a `static_assert(amx_mirror_eligible(llama<...>::attention_kernels))` on a real plugin array would test what the case name says.  Also, on a non-AMX host the `== 0` at :125 holds for either flag value, so the only discriminating half is the one we `WARN` past - where does this run with AMX?  The pair now differs only in the flag.  Can both arms still go through `book_t::try_create`, so the adopt-constructor (`kv_cache.hpp:1028`, the path `full.hpp:833` ships) is what gets exercised, and can one `static_assert(amx_mirror_eligible(...))` use a real plugin array instead of the hand-built ones?

_Verification: round 2 (R2-13), partial: Met: the two arms now differ only in the flag (both are `book<2, 1, 64, 0>(4, 2, false, <flag>)`, :125-126 vs :134-135), and 'where does this run with AMX?' is answered by the TODO at src/tron/CMakeLists.txt:170-173, the PR body 'Validation and CI coverage' section and issue #3997 (OPEN). Not met: both arms still go through the 4-argument constructor (kv_cache.hpp:775-797), not `book_t::try_create(...)` -> adopt-constructor (kv_cache.hpp:988-1006, :1013-1028), which is the path full.hpp:833-834 ships; no `static_assert(amx_mirror_eligible(<real plugin>::attention_kernels))` - :111-118 still use hand-built arrays. The comment still says 'built the way the scheduler builds it' (:120). Note the R2 premise 'this constructor's only caller is this test' no longer holds: t_llama_unit.cpp:273, :340, :479, :481, :1081, :1083 now call the 4-argument constructor too. Anchor moved 123 -> 125. | evidence: t/t_amx_arena_leak.cpp:120; t/t_amx_arena_leak.cpp:121; t/t_amx_arena_leak.cpp:125_

### t/t_amx_logit_ab.cpp

#### `t/t_amx_logit_ab.cpp:6` R4-01 (B17/A3)

```cpp
    1  // AMX-vs-AVX A/B logit dump: run force_generate on a LONG synthetic token
    2  // sequence and dump every recorded step's logits to the file named by
    3  // AMX_LOGIT_OUT. This is a tool, not a test - it asserts nothing about AMX -
    4  // so its ctest entry is DISABLED (t/CMakeLists.txt) and nothing in CI runs it.
    5  // Run the binary by hand, twice, and compare the two dumps offline:
    6* //   AMX_LOGIT_OUT=/tmp/avx.bin TRON_AMX_DISABLE=1 gen/t_amx_logit_ab
    7  //   AMX_LOGIT_OUT=/tmp/amx.bin TRON_AMX_DISABLE=0 gen/t_amx_logit_ab
    8  // Optional: AMX_MODEL=<model id> (default ingested-llama-3.1-8b, so the
    9  // binary exists only with BUILD_INGEST_MODELS=ON) and AMX_TOKENS=<file> in
   10  // extract_logits --save-tokens format to align steps with an HF reference.
   11  // The long sequence matters: the AMX fast path engages only on full 64-token
   12  // pages, which the 21-token canned-prompt golden tests never reach.
```

Both commands run the AVX path on a default build - `TRON_AMX_DISPATCH` is OFF (`src/tron/CMakeLists.txt:170`) and the dispatch site is `#ifdef`'d (`self_attention.hpp:1352`) - so the two dumps agree for the wrong reason.  Let's start the recipe with the `-DTRON_AMX_DISPATCH=ON` configure (and `-DTRON_AMX_K_MIRROR=ON` for the mirror arm).

_Verification: round 4 (R4-01), not addressed | evidence: file unchanged since 234c02bde_

### t/t_amx_mirror.cpp

#### `t/t_amx_mirror.cpp:28` R1-61 (A11/B6/B8)

```cpp
   26  template <size_t page_size, size_t head_size>
   27  void require_mirror_matches(const uint16_t* flat_k, const uint16_t* plane) {
   28*   for (size_t s = 0; s < head_size / 32; ++s) {
   29      for (size_t c = 0; c < page_size / 16; ++c) {
   30        for (size_t dp = 0; dp < 16; ++dp) {
   31          for (size_t t = 0; t < 16; ++t) {
   32            for (size_t j = 0; j < 2; ++j) {
   33              const size_t mi = (((s * (page_size / 16) + c) * 16 + dp) * 16 + t) * 2 + j;
```

The reference here is the implementation's own index formula, so a layout change applied to both passes; the only test that ties the plane to its consumer (`qk_mirror_128x4`) is hardware-gated.  A scalar model of the kernel's panel addressing would pin the layout to the reader on any host.  Also, this is the fourth copy of the formula (Note, `scatter_k_mirror`, here, `t_llama_unit.cpp:440`); a `require_mirror_matches` in a `t/` header used by both tests would leave two.  Now six full copies plus two hand-expanded column forms (`t_llama_unit.cpp:370`, `:1128`, `:1135`, `:1140`), and two lambdas that are `require_mirror_matches` again.  `testutil.hpp` is already included there; a whole-plane and a one-token overload in it would serve `t_amx_mirror`, `:522`, `:360` and `:1118`.

_Verification: round 1 (R1-61), not addressed | evidence: file unchanged since 234c02bde_

#### `t/t_amx_mirror.cpp:80` R1-62 (B18)

```cpp
   78  TEST_CASE("K mirror is byte-equivalent to canonical K", "[kv_data][amx_mirror]") {
   79    run_case<128>();  // qwen/llama head size (the AMX fast-path shape)
   80*   run_case<64>();   // smaller-head geometry
   81  }
```

Which consumer reads a head-64 plane?  Dispatch requires head 128, so this is 8192 `REQUIRE`s guarding data nobody reads - the same point as the write-through gate in `model.hpp`: don't maintain planes no kernel consumes, and this case goes away.  Still here.  Through the scheduler a head-64 book no longer has a plane at all, so this case now tests a layout only the legacy constructor can produce - one more reason to flush that constructor.

_Verification: round 1 (R1-62), not addressed | evidence: file unchanged since 234c02bde_

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
    9  // exactly-rounded weight reference for PV) within an envelope computed from
   10  // the inputs, so any regression outside (a)/(b) - wrong element indexing, a
   11  // dropped token or dim block, a changed accumulation precision - fails.
```

Nice - a real reference on both sides, in double.

_Verification: round 1 (R1-63), not addressed | evidence: t/t_amx_numerics.cpp:1; t/t_amx_numerics.cpp:8; t/t_amx_numerics.cpp:9_

#### `t/t_amx_numerics.cpp:33` R1-65 (B3/B15)

```cpp
   31  // The kernel shape, from the interface header.
   32  constexpr size_t PAGE = tron::amx_attn::PAGE_TOKENS_64;
   33* constexpr size_t HD = tron::amx_attn::HEAD_SIZE_128;
   34  constexpr size_t NQ = tron::amx_attn::GROUP_HEADS_4;  // query heads per KV head
   35  constexpr size_t ROWS = tron::amx_attn::TILE_ROWS_16;
```

We renamed this `HEAD_SIZE` in the kernel TU; same here (and in the bench)?  Also `std::make_unique` without `<memory>`.  `HD` is now an alias of `HEAD_SIZE_128`; the alias could just be `head_size`.  And `NQ`/`ROWS` are a third spelling of `GROUP_HEADS`/`TILE_ROWS` - one vocabulary, please.  The bench still has its own `HD = 128`.  The bench's `HD = 128` went with the file, so that part is done.  Still: `HD`/`NQ`/`ROWS` at :33-35 remain a third spelling of the kernel TU's `HEAD_SIZE`/`GROUP_HEADS`/`TILE_ROWS`, and `std::make_unique` at :80 and :122 still has no `<memory>`.

_Verification: round 1 (R1-65), partial: Bench half settled earlier (bench file deleted). Still open at HEAD: (1) `HD`/`NQ`/`ROWS` at :33-35 remain a third spelling of the kernel TU's `HEAD_SIZE`/`GROUP_HEADS`/`TILE_ROWS` (amx_attn.cpp:25,:37,:29); (2) `std::make_unique` at :80 and :122 with no `#include <memory>` - includes at :12-17 are cmath, cstddef, cstdint, cstring, random, vector; `grep -n memory t/t_amx_numerics.cpp` returns nothing. Delta 275fa89a0/35b3f3cae touched :85, :125, :138, :145-147 only. | evidence: t/t_amx_numerics.cpp:33; t/t_amx_numerics.cpp:34; t/t_amx_numerics.cpp:35_

#### `t/t_amx_numerics.cpp:108` R1-64 (A11/A13)

```cpp
  100          // Both engines sum the same 128 exact bf16xbf16 products in fp32;
  101          // only the accumulation order differs. Envelope: a small multiple
  102          // of fp32 epsilon times the absolute-product mass.
  103          double abs_mass = 0;
  104          for (size_t d = 0; d < HD; ++d) {
  105            abs_mass += std::fabs(double(bf16_to_float(in->q[qi * HD + d])) *
  106                                  double(bf16_to_float(in->k[t * HD + d])));
  107          }
  108*         const double tol = 1e-4 * abs_mass + 1e-6;
  109          REQUIRE(std::fabs(double(s_amx[qi][t]) - double(s_avx)) <= tol);
```

The reorder bound for 128 exact products summed in fp32 is 127 ulp = 7.6e-6 of the mass, so 1e-4 is 13x looser than the math allows, and the comment calls it "a small multiple of fp32 epsilon" (it's ~1700).  Where does 1e-4 come from?  Tighten to a few times the bound, or state the measured maximum and why the margin.  Ditto :209.

_Verification: round 1 (R1-64), not addressed | evidence: t/t_amx_numerics.cpp:101; t/t_amx_numerics.cpp:102; t/t_amx_numerics.cpp:108_

### t/t_llama_unit.cpp

#### `t/t_llama_unit.cpp:310` R3-05 (5.2/A3)

```cpp
  308      WARN("mirror arena absent (AMX unavailable) - mirror view check not run");
  309    } else {
  310*     alignas(64) std::array<bf16, 128> row;
  311      row.fill(static_cast<bf16>(1.0f));
  312      page->template set_k_mirror<geometry>(slot, 0, 0, row.data());  // validator's row
  313      cache.set_storage_view(cache.eagle_storage_offset());
```

Every check in this block is implied by the coherence case below (:374-:380 read different values at the same index through the two views, which proves the planes are distinct memory).  Flush it - or, if the parallel with `page->k` above is worth keeping, say that these rows are markers and mirror == scatter(canonical) is deliberately not maintained here; dims 1..127 of canonical K are uninitialized at this point.

_Verification: round 3 (R3-05), not addressed | evidence: t/t_llama_unit.cpp:310; t/t_llama_unit.cpp:312; t/t_llama_unit.cpp:315_

#### `t/t_llama_unit.cpp:348` R3-06 (A10/B14)

```cpp
  347    // Like save_k: store the canonical row, then write it through to the mirror.
  348*   auto save_k = [&](size_t i_page, float base) {
  349      auto k = page->k(slot, 0, i_page);
  350      for (size_t d = 0; d < geometry.head_size; ++d)
  351        k[d] = static_cast<bf16>(base + static_cast<float>(d));
  352      page->template set_k_mirror<geometry>(slot, 0, i_page, k.data);
  353    };
```

The lambda mimics `save_k_impl`, but nothing in `t/` calls the real one (`model.hpp:2793`) under the view, and the scenario I described ends in the parent's `qk_mirror_128x4` read.  Was an EAGLE (parent, child) run done with `TRON_AMX_K_MIRROR=ON` and its greedy output compared to the canonical build, the way the qwen A/B in the description was?  Record it in the PR.

_Verification: round 3 (R3-06), not addressed | evidence: t/t_llama_unit.cpp:347; t/t_llama_unit.cpp:348; t/t_llama_unit.cpp:352_

#### `t/t_llama_unit.cpp:362` R3-07 (B6)

```cpp
  360    // Compare the whole plane against the canonical K of the currently selected
  361    // physical slot, byte-exactly (same index map as the append test below).
  362*   auto require_plane_matches_canonical = [&] {
  363      const auto* mirror = reinterpret_cast<const uint16_t*>(
  364          page->template k_mirror_data<geometry>(slot, 0));
  365      for (size_t i = 0; i < book_t::page_size; ++i) {
```

Ditto (`t_amx_mirror.cpp:28`): this lambda and `require_mirror_column_matches` at :1118 are `require_mirror_matches` again, and the plane's K rows are contiguous, so the existing helper already covers the whole-plane case.

_Verification: round 3 (R3-07), not addressed | evidence: t/t_llama_unit.cpp:362; t/t_llama_unit.cpp:372; t/t_llama_unit.cpp:373_

#### `t/t_llama_unit.cpp:516` R1-68 (B14/A10)

```cpp
  516* #ifdef TRON_AMX_K_MIRROR
  517    // After fill_random and append (the defrag rebuild path), the K mirror
  518    // plane must stay byte-equivalent to canonical K for every token;
  519    // see Note [K mirror coherence].
  520    // The plane lives in the book's parallel arena, which exists only when AMX
  521    // is available at runtime - skip (with a visible note) on non-AMX hosts.
  522    if (destination_page->template k_mirror_data<geometry_128>(kv_slot_id(1), 1) ==
  523        nullptr) {
  524      WARN("mirror arena absent (AMX unavailable) - mirror coherence not checked");
  525    } else {
  526      const auto* mirror = reinterpret_cast<const uint16_t*>(
  527          destination_page->template k_mirror_data<geometry_128>(kv_slot_id(1), 1));
  528      for (size_t i = 0; i < cache_t::page_size; ++i) {
```

IIUC only token 0 of this page came through `copy_storage_slot` (append copied 64 tokens into page 0 and one into page 1, and `destination` never advanced `tok_ct`); tokens 1..63 here were rebuilt by `fill_random`.  So the defrag rebuild is checked for `i == 0, dst_begin == 0` only - a dropped `dst_begin + i` or a wrong `dst + i * head_size` stride passes.  Check page 0 too, and do one append into a destination whose `tok_ct` is not a multiple of 64.  The new EAGLE append check covers the moved token in both views - good; this test still checks page 1 only.  Still page 1 only: `destination_page` is `page_of(target_token)` with `target_token == page_size` (:485, :510), so the 64-token copy into page 0 - the only `copy_storage_slot` call with `count > 1` that any mirror check reaches - is still unchecked; can we check that page too?

_Verification: round 1 (R1-68), partial: Unchanged since R5 (R5 :512 -> HEAD :516, shift +4 from the two wrapped constructors at :478-481). The mirror check still runs only on `destination_page = page_of(target_token)` with `target_token == page_size`, i.e. page 1; page 0 is not checked, and no append into a destination whose `tok_ct` is not a multiple of 64 exists in this test (`destination` never calls `increment_tokens_used`, :482-508). The EAGLE append case at :1100-1150 still covers the moved token in both views (the part settled earlier). | evidence: t/t_llama_unit.cpp:485; t/t_llama_unit.cpp:486; t/t_llama_unit.cpp:510_

#### `t/t_llama_unit.cpp:1139` R3-08 (B7)

```cpp
 1138        require_mirror_column_matches();  // validator's plane vs. physical slot 0
 1139*       REQUIRE(
 1140            float(page->template k_mirror_data<geometry_64>(kv_slot_id(0),
 1141                0)[((offset / 16) * 16 * 16 + (offset % 16)) * 2]) == source_token + 1);
 1142        destination.set_storage_view(destination.eagle_storage_offset());
 1143        require_mirror_column_matches();  // draft's plane vs. physical slot L
 1144        REQUIRE(
 1145            float(page->template k_mirror_data<geometry_64>(kv_slot_id(0),
 1146                0)[((offset / 16) * 16 * 16 + (offset % 16)) * 2]) == source_token + 11);
 1147        destination.reset_storage_view();
```

Both of these are implied by `require_mirror_column_matches()` together with :1099 and :1103 (its s = dp = j = 0 iteration is exactly this index, and `row[0]` is already required equal to `source_token + 1` / `+ 11`).  Flush them; if a literal-value check is wanted, take the index from the helper instead of expanding it by hand a third way.

_Verification: round 3 (R3-08), not addressed | evidence: t/t_llama_unit.cpp:1139; t/t_llama_unit.cpp:1141; t/t_llama_unit.cpp:1146_

#### `t/t_llama_unit.cpp:1353` R1-69 (B14/A10)

```cpp
 1352    constexpr size_t head_size = 128;
 1353*   constexpr size_t n_heads = 16;
 1354    constexpr size_t dim = head_size * n_heads;
 1355    constexpr size_t hidden_dim = 1024;
 1356    constexpr size_t n_layers = 2;
 1357    constexpr size_t n_kv_heads = 8;
 1358    constexpr size_t kv_mul = n_heads / n_kv_heads;
 1359    constexpr size_t n_q_tokens = 8;
```

I worked through the dense predicate and I believe it (token 0 is the binding window case; the `tok_hi` check on offset 63 covers the range).  But nothing in `t/` ever reaches it: this test uses `n_heads = 16`, `n_kv_heads = 8`, so `kv_mul == 2` and `amx_qp` is always null.  Can we have a `kv_mul == 4` case (n_heads 32 - the llama-3.1-8b shape) so the whole AMX QK + PV path is compared against `emulation::compute_attention`?  On non-AMX hosts it degrades to the AVX path and still passes.  Ideally with sub-cases for a mask range ending inside the page and the window edge (`sliding_window_size` 64 vs 65 for a query at position 127).

_Verification: round 1 (R1-69), not addressed | evidence: t/t_llama_unit.cpp:1352; t/t_llama_unit.cpp:1353; t/t_llama_unit.cpp:1357_

## 4. Checked and clean in the delta

| area | what was verified | source |
|---|---|---|
| 35b3f3cae: the padding invariant | pack_q_group_128x4 writes offsets 0..7 of every 32-element panel row (amx_attn.cpp:105; 512 writes, all live); pack_q_rows_128x4 is one 1 KB memcpy of rows 0..3 (:229); grep amx_qpack: declared :1361, resized :1371, sliced :1416 - nothing else writes it; std::vector::resize value-initializes appended elements, shrink leaves the prefix, reallocation copies then value-initializes; one packer per build (#ifdef TRON_AMX_K_MIRROR at :1420), same 4x128 shape for every instantiation (shape_ok), so no stale-live-becomes-padding path; test buffers `= {}` at t_amx_numerics.cpp:85, :125, :138 (per-seed loop); P buffer precedent `alignas(64) thread_local uint16_t P[TILE_ROWS][PAGE] = {}` (amx_attn.cpp:186-197) | src/tron/kernels/amx_attn.cpp:98-110,186-197,227-230; h/tron/models/self_attention.hpp:1361-1442; t/t_amx_numerics.cpp:85,125,138 |
| 3fa11d911: TRON_AMX_DISABLE exactly "1" | amx_attn.cpp:57-58 `off != nullptr && std::strcmp(off, "1") == 0` is the TRON_NO_RTM form (mwaitx.cpp:37-38) and the TRON_USE_ARENA_ALLOCATOR form (memory.cpp:90); every statement of the switch agrees (iface:32, :96; t_amx_logit_ab.cpp:6-7; PR body); values other than 1 are ignored without a log line - the B17 half R1-48 mentioned, not asked | src/tron/kernels/amx_attn.cpp:54-58; src/system/mwaitx.cpp:34-39; src/system/memory.cpp:87-91 |
| b2010bee9: default false is safe for production and for every mirror test | the scheduler reaches the book only through the 4-argument try_create (full.hpp:833-834) with amx_mirror_eligible(model_t::plugin_t::attention_kernels) from :1457; every k_mirror_data / set_k_mirror use in t/ belongs to a test whose book passes true (t_llama_unit.cpp 272-273, 339-340, 478-481, 1080-1083; t_amx_arena_leak.cpp 80-81, 134-135); the remaining 3-argument callers read canonical K or count DMA allocations only (the arena is ::operator new[], not DMA); node_base has one constructor and both node constructors forward the flag | h/tron/scheduler/full.hpp:306-322,709-727,833-834,1457; t/t_llama_unit.cpp; t/t_amx_arena_leak.cpp; h/tron/models/kv_cache.hpp:1062-1063 |
| b2010bee9: the t_amx_arena_leak literal storage_slot_count=2 equals the old default | book<2, 1, 128, 0>'s default layout is uniform_kv_slot_specs<2> -> n_slots = 2 (kv_cache.hpp:696-725) | h/tron/models/kv_cache.hpp:696-725; t/t_amx_arena_leak.cpp:80-81,134-135 |
| 35b3f3cae: cvtne2ps_pbh argument order (R1-50) | _mm512_cvtne2ps_pbh(a, b): words 0..15 from b, 16..31 from a - so (hi, lo) keeps tokens c..c+31 in order; a finder compiled and ran the intrinsic on this host (avx512_bf16) and saw exactly that | src/tron/kernels/amx_attn.cpp:191-196 |
| 275fa89a0: the trims match the threads they answer | `>> 6 / & 63` re-explanation gone (R1-33), static_assert prose gone (R1-45), 'share the bf16 -> fp32 conversion' gone (R1-36 first half), softmax-update paragraph reduced to one sentence (R1-38 first half), <atomic> removed and unused (R1-43), the system-level byte-identical check sentence gone (R1-67); Note [AMX attention dispatch] still names t_amx_numerics (iface:46-47) | h/tron/models/self_attention.hpp:1417-1418,1509-1512,1621-1623; src/tron/kernels/amx_attn.cpp:1-12,31-33; t/t_amx_numerics.cpp:145-151 |
| 298dbad0f: TODO form (B10) | TODO(owner) with a filed-issue URL at the two options a reader flips; issue #3997 is OPEN, assigned to jhan-positron, and carries the interim recipe the TODO points to | src/tron/CMakeLists.txt:170-173; gh issue view 3997 |
| Delta scope (A9) and commit messages | all nine files are the PR's AMX files; every hunk is named in a commit message; b2010bee9's '8 mirror-test sites' = 6 in t_llama_unit + 2 in t_amx_arena_leak (:126 already passed false); 35b3f3cae's description of the thread_local vector and the `= {}` buffers matches the code | delta.diff; git show b2010bee9 35b3f3cae 3fa11d911 |
| PR body mechanism sentences | 'save_k writes through' (model.hpp:2793-2795), 'every consumer null-checks and fails soft to the AVX path' (self_attention.hpp:1565-1575, kv_cache.hpp:1237), 'Validation and CI coverage' facts (options OFF at src/tron/CMakeLists.txt:174/:181; no TRON_AMX in .github, ci/, CMakePresets.json, flake.nix; the three tests SUCCEED in the default build), the archive link and #3997 all hold; still undescribed: kv_block_planes, v_data/v_base, the two #error lines, the fill_random rebuild, the amx_mirror_eligible plumbing (grep -c = 0 each) | pr_body.md; h/tron/models/model.hpp:2769-2795; h/tron/models/self_attention.hpp:1556-1590; src/tron/CMakeLists.txt:170-190 |
| CI and the Codex threads | isDraft=true, labels=[], reviewDecision=REVIEW_REQUIRED; check-runs: 3fa11d911 0, 35b3f3cae 0, 275fa89a0 0, 298dbad0f 0; exactly two Codex comments (3858305362 at :1367, 3858305367 at :1361), no replies, one COMMENTED review | gh pr view 3879; gh api commits/<sha>/check-runs; gh api pulls/3879/comments |
| Re-anchoring | kv_cache.hpp 2471 -> 2473 lines (hunks 764-772, 980-986: +1 after :772, +2 after :986); self_attention.hpp +3 at :1368, -3 at :1414-1418, -1 at :1510, -5 at :1618-1623; amx_attn.cpp -7/-8 from the header and static_assert trims, +2 at the cvtne2ps comment; amx_attn_iface.hpp +2 after :96 and +3 after :156; src/tron/CMakeLists.txt +4 from :170; t_amx_arena_leak.cpp +2 after :78; t_llama_unit.cpp +1/+2/+4/+6 from the four wrapped constructors; every anchor confirmed by a content quote | diff wt-r5 wt-head per file |
| Triage claims that hold | R1-16, R1-33, R1-45, R1-15 (applied - but see R1-15's new problem), R1-67, R1-43, R1-49, R1-50, R2-03 (as stated), R1-48 done; R1-36, R1-38 partial as stated; R1-47's reason (no helper for the XGETBV and arch_prctl steps; mwaitx.hpp has only cpuid_bit) and R1-58's reason (TODO at the options, #3997 OPEN, PR body section) are factually right | PR3879/triage.json vs the tree; h/system/mwaitx.hpp:22-44; gh issue view 3997 |
| Triage claim that does not hold | R1-14 'done' (ff7269a9f, 901f30d8e): those commits predate round 5; :137-145 are untouched since; the date 2026-08-19 at :140 contradicts the sweep header 2026-08-18T18:34:53Z and exec/logs/p0-fused-sweep.log (both sweeps on 08-18); no record or command is named - status PARTIAL | h/tron/kernels/amx_attn_iface.hpp:137-145; exec/results/slot1/fused-sweep-v2.txt:1; exec/logs/p0-fused-sweep.log |
| R2-05 (question): what the tree says | both in-tree plugins declare a single-kernel attention_kernels array (llama.hpp:191-193, mock.hpp:113-115), so 'no in-tree plugin is mixed today' holds; copy_storage_slot's rebuild has no shape gate (kv_cache.hpp:1881-1889); Option 1 in your kv_cache-hpp-1199.html 4.1 (comment the consequence, add the Note sentence, a two-kernel static_assert) is what the comment asks for and is not applied | h/tron/plugins/llama.hpp:191-193; h/tron/plugins/mock.hpp:113-115; h/tron/models/kv_cache.hpp:176-190,554,1881-1889 |

## 5. Glossary

- **canonical-K** - Project shorthand: K kept in today's original single-copy row-major storage and read as-is by the AVX dotter, the FPGA DMA and the canonical AMX kernel.
- **mirror / k_vnni** - A second, derived copy of K in the pair-interleaved (VNNI) layout the AMX B operand wants. The mirror formulation originates from Bill's PR #2934 (k_vnni); the parallel-arena implementation and all numbers in PR #3879 are ours (jhan-amx-p0).
- **parallel arena** - Ordinary (non-DMA) RAM owned by the book, sized kv_bytes/2, one mirror plane per (storage slot, kv_head, page). Not the book's DMA arena_data.
- **shape gate / amx_attn::shape_ok** - head_size == 128 && kv_mul == 4 in one function, used by the dispatch, the save_k write-through and (via amx_mirror_eligible) the arena allocation.
- **amx_mirror_eligible** - (a) a constexpr function over a plugin's attention_kernels (true if any kernel passes the shape gate); (b) a bool carried on every node_base and passed to book::try_create; (c) a constructor parameter of book. The 3-argument book/try_create forms default it to true (blocker R2-03).
- **storage view / kv_blocks_alias** - book::set_storage_view() repoints kv_blocks_alias so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; since 96b5a6c72 the mirror accessors follow it through mirror_view_offset_.
- **EAGLE** - Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots.
- **ready / pending pass** - Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after upstream_kvs_ready.wait() over pages being written this forward (pending).
- **RX worker** - Per-card driver thread running DMA completion callbacks; rope_k/save_k execute there.
- **work region** - One begin_region()/end_region() bracket = one LDTILECFG/TILERELEASE pair, held for one apply_page_range call (~229 cycles measured for the pair).
- **whole-path benchmark / amx_fused_bench.cpp** - A stand-alone program (deleted in ff7269a9f, in history up to d176c88b3) that timed scores + softmax + PV of one 64-token page on hand-written copies of the kernels. Its recorded sweep (exec/results/slot1/fused-sweep-v2.txt in the campaign workspace, outside the tron tree) is the source of the 1250 / 686 ns figures.
- **Codex review** - An automated review posted on 2026-08-25 by jeremyconner1975 (“Review performed by Codex at Jeremy’s request”) with two inline comments on self_attention.hpp. Alexey answers bot findings rather than ignoring them (persona C2); his replies are in section 4 marked reply.
- **Run CI label** - Draft PRs skip the build/test jobs of cmake-single-platform.yml unless the PR carries the Run CI label at the next push (Note [Draft PR Filtering and Label Override]).
- **Note [Title]** - GHC-style named long comment, checked by make lint-notes.
- **A3, B6, ... tags** - Item numbers from ~/workspace/reviewers/alexey.md section 1; shown only in the verification line, never in the comment text.

## 6. Method and limits

- Target: PR head 3fa11d911 (checked out clean in ~/workspace/tron-amx, verified by the generator). Round 5 reviewed 234c02bde. Delta: six commits - b2010bee9, b85fd2789, 298dbad0f (yours from the round-5 follow-up) and 275fa89a0, 35b3f3cae, 3fa11d911 - 9 files, +70/−66.
- The author's decision record PR3879/triage.json (31 decisions) was handed to every status verifier: done/partial claims were checked against the tree (one 'done' did not hold: R1-14), ignore/defer items (R1-47, R1-58) were not re-raised and carry his predicted reply instead (section 2a), the question item (R2-05) stays open with the tree's answer in its verification line.
- 66 items sit in files the delta touched; 8 status verifiers re-anchored them by content and 8 adversarial refuters re-derived every line and quote (13 line/wording corrections applied, no status overturned). The 7 items in unchanged files carry their round-5 lines and text.
- Finders: 4 independent agents over the delta only (code correctness of the padding invariant, the kill-switch parse and the default flip; comment/contract accuracy; tests, CI and PR description; design and scope). 8 candidates, one adversarial refuter each: 5 stand (one new comment, four folded into existing threads as follow-ups), 3 refuted as restatements of open items. The padding invariant of 35b3f3cae was checked to the index formula: the live writes never touch the padding, the thread_local vector is written by nothing else, and shrink-then-grow value-initializes the tail.
- Suggested fixes (added at your request): the R2-03 single-constructor variant was applied to a scratch copy of 3fa11d911 and syntax-checked with the build's compile commands (0 errors on both tests and the scheduler TU; exec/review-pipeline/r6/fix/); the comment replacements were not compiled.
- CI: gh api commits/<sha>/check-runs returns 0 for 3fa11d911, 35b3f3cae, 275fa89a0 and 298dbad0f; the PR is a draft without the Run CI label, so the earlier lint-only runs are still all CI has done. The two Codex threads still have no reply (they are answered by R5-03/R5-04 here).
- Written 2026-08-26. Voice from ~/workspace/reviewers/alexey.md; the persona's most common review is an empty approval, so nothing was added that his lenses would not raise. The hand-written background block for R1-47 from round 5 is carried under its row in section 2a. Format note: the verdict body is broken into paragraphs and a list with comment ids at your request; he writes review bodies as one prose paragraph (bullet lists in 5 of 365 bodies).
