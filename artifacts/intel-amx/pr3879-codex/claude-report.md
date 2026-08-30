# Claude's work log on codex's PR #3879 review

One entry per codex finding: verdict, evidence, fix, tests, verification status.
Companion pages: `verify-codex-p1.html` (full verification of P1).
Repo: `~/workspace/tron-amx`, branch `jhan-amx-p0` (NFS-shared with delphi-3bda).

## P1 — Require bf16 queries before enabling AMX (`self_attention.hpp:1358-1360`)

**Verdict: agree.** Confirmed 2026-08-28 by code trace, a standalone harness against
the real pack functions, and codex's own test built and run at HEAD 609dabba:
fp32 Q packs as `0x0000` (expected `0x3F80`), fp16 Q as `0x3C00`; both pack
variants identical. Ten-agent adversarial workflow: 3 claims × 2 refuters, none
refuted. Two precision notes on the comment (neither changes the verdict):

- the corruption is larger than "half of Q": the per-KV-head offset is also in
  16-bit units, so KV head *k* packs float heads 2k–2k+1 instead of 4k–4k+3;
- `host_fp16` exists only in the experimental `llama-3-8b-host-precision`
  variant (not in a default `--tags test` build); the `host` half is in the
  default build (`llama-3-8b-host`, `llama-3.1-8b-instruct-host`,
  `mixtral-8x7b-instruct-v0.1-host`, `ingested-granite-3.3-8b-host`, …).

**Fix (option A — gate, not convert).** Converting fp32 Q to bf16 would give the
`host` executor (the fp32 reference path) a third numerics difference the
contract does not cover, and would mix two Q precisions inside one query's
softmax (partial pages stay on the AVX loop). Instead the eligibility predicate
gains the executor's activation scalar and is applied at every gate:

| file | change |
|---|---|
| `h/tron/kernels/amx_attn_iface.hpp` | `query_scalar_ok<T> = is_same_v<T, bf16>`; `eligible<T>(head_size, kv_mul) = shape_ok && query_scalar_ok<T>`; Note [AMX attention dispatch] gains the executor condition (safety-chain step 2); pack contracts state "caller guarantees bf16, no conversion" |
| `h/tron/models/self_attention.hpp` | `apply_page_range` and `apply_page_tok` use `eligible<model::activation_scalar>`; `static_assert(query_scalar_ok<…>)` at the pack site |
| `h/tron/models/model.hpp` | `save_k_impl` mirror write-through uses the same predicate (no wasted scatter for `host` models) |
| `h/tron/models/kv_cache.hpp` | `amx_mirror_eligible<query_scalar_t>(kernels)` (no arena for `host` models); notes updated |
| `h/tron/scheduler/full.hpp` | passes `model_t::activation_scalar` |

**Why existing tests missed it.**

1. The eligibility predicate was geometry-only, so the only compile-time checks
   (`t_amx_arena_leak.cpp:117-118`) asserted geometry — there was no statement of
   *which executors* may take the path.
2. The kernel tests (`t_amx_numerics`) build bf16 buffers themselves; they test
   the kernels, not the dispatch's handling of the model's Q type.
3. The one dispatch-level test on the `host` executor (`t_llama_unit` "apply and
   join page ranges") uses 16 heads / 8 KV heads (kv_mul 2), so `shape_ok` is
   false and every AMX block is compiled out — that test cannot reach the AMX
   path for any executor.
4. System tests that would catch it exist (`t_generate_host`: `llama-3-8b-host`,
   400 tokens = 6 dense pages, HF golden logits; also `t_generate_host_2`,
   `t_concurrency_load`) but need an AMX host with the opt-in build and weights,
   and were not in the PR's hand-run list (`t_amx_*` + `t_llama_unit`); no CI
   lane builds `TRON_AMX_DISPATCH`.
5. The kernel API is untyped (`const uint16_t*`), so the type system could not
   object to the `reinterpret_cast`.

**Tests added (all compile-time or hardware-independent; run on any host).**

- `t/t_amx_numerics.cpp` — "AMX dispatch is limited to executors that store
  activations as bf16": `query_scalar_ok` / `eligible` for `bf16`, `float`,
  `fp16` and through `tp1`, `host_bf16`, `host`, `host_fp16::btensor_t<128>::element`;
  shape and scalar halves both required.
- `t/t_amx_numerics.cpp` — "AMX Q packers move bf16 bit patterns to the documented
  positions": the VNNI and row-pack layout contracts, every element, padding
  untouched (gap 2: the layout was only checked indirectly, on AMX hosts).
- `t/t_llama_unit.cpp` — "AMX eligibility follows the executor's activation
  scalar": `model<llm<32/8/128 config, host | host_bf16 | host_fp16>>` — the
  predicate the dispatch, `save_k` and the scheduler evaluate, at model level
  (gap 1 and 3).
- `t/t_amx_arena_leak.cpp` — `amx_mirror_eligible<float|fp16>(qwen_kernels)`
  negatives next to the existing bf16 asserts (gap 1).
- `self_attention.hpp` — `static_assert` at the pack site (gap 5).
- Codex's test ("AMX Q packing preserves non-bf16 host queries") is replaced: it
  performs the caller's `reinterpret_cast` itself and asserts a conversion the
  `const uint16_t*` packers never had, so it stays red after any correct fix
  (gate, convert-at-call-site, or typed overloads). Its byte-level facts are
  recorded above and in `verify-codex-p1.html`.

**Dispatch-level test (closes the gap first listed as deferred).** `t/t_amx_dispatch_dtype.cpp`
(commit `e217f518e0`): CPU fakes for every `amx_attn` entry point in the test's own TU (so
`libtron`'s `amx_attn.cpp.o` is never linked; `available()` fakes true), then the production
`apply_page_range` on a 4/1/128 model per executor — `host_bf16` packs exactly once with the
exact query values, `host` and `host_fp16` never reach the packer. Runs on any host (518
assertions here). Shape and technique from codex's `t_amx_dispatch_dtype` probe; the
post-fix expectations are ours. Still open: a dispatch-level *numerics* test of the bf16
path against `emulation::compute_attention` on an AMX host (tolerance to be measured on
delphi-3bda).

**Verification.**

- claude-box (AMD, no AMX), 2026-08-28 04:40Z, `gen/` native preset with
  `TRON_AMX_DISPATCH=ON TRON_AMX_K_MIRROR=ON` (`BUILD_INGEST_MODELS=OFF` on this
  box: the gated gemma exports need HF auth that this environment lacks):
  `t_amx_numerics` 4109 assertions / 5 cases (kernel cases skip without AMX),
  `t_amx_arena_leak` 3 / 2, `t_amx_mirror` 24576 / 1, `t_llama_unit` 120021 / 24
  (new case: 7 assertions) — all passed; `runtron` links (compiles the
  scheduler's `amx_mirror_eligible<activation_scalar>` call).
- delphi-3bda (Xeon 6 6962P, AMX), `exec/p3-q-scalar-gate.sh 323b9d5499 609dabba83`,
  launched 2026-08-28 05:03Z (no CI lease held, so it started at once), isolated
  worktree `/var/tmp/jhan/tron-p3-q-scalar-gate`, `BUILD_INGEST_MODELS=OFF`
  (`t_amx_logit_ab` therefore not built — skipped). Results
  (`exec/logs/p3-q-scalar-gate.txt`):
  - mirror config (`TRON_AMX_K_MIRROR=ON`), 05:06Z: `t_amx_arena_leak` 5 / 2,
    `t_amx_mirror` 24576 / 1, `t_amx_numerics` **6414 / 5** (the QK/PV kernel
    precision cases ran on AMX), `t_llama_unit` **144875 / 26** (mirror coherence
    cases ran), **`t_generate_host` 2929 / 2 passed** — `llama-3-8b-host`, 400 tokens
    = 6 dense pages, HF golden logits, with AMX enabled: the `host` executor now
    stays on the AVX path.
  - canonical config (`TRON_AMX_K_MIRROR=OFF`), 05:08Z: `t_amx_numerics` 6158 / 4,
    `t_llama_unit` 120027 / 24, `t_generate_host` 2929 / 2 passed.
  - negative control (the five gate headers from 609dabba83, `t_generate_host`
    must fail), 05:11Z–05:34Z: the unfixed build **aborted** — apport recorded
    signal 6 (SIGABRT) for `t_generate_host` and spent ~25 min writing a 6 GB core
    to `/var/crash` (deleted afterwards). The script discarded stderr, so no Catch2
    summary was captured, and its `ok` marker was a false positive (the verdict
    grep matched the word "failed" in the script's own annotation line) — both
    script defects fixed in `exec/p3-q-scalar-gate.sh` (stderr kept, `ulimit -c 0`,
    20 min bound, exit code recorded, verdict reads only the result line). The
    exact failure, captured by `exec/p3c-prefix-abort-message.sh` on the pre-fix
    commit 609dabba83 (05:39–06:00Z, stdout+stderr kept): `t_generate_host`
    ("Generate 400 tokens … LLaMa 3 8B (2 layers)", model `llama-3-8b-host`, AMX on)
    dies with SIGABRT from `tron_abort` inside
    `self_attention<model<llm<llama_3_8b, make_llm_executor<false, tensor, tensor,
    tensor>>>>::state::run_attention_job` — the four-argument assertion at
    `self_attention.hpp:1735-1738`, "Encountered -inf m_star in a valid scratchpad.
    KV_head {}, to worker {}, from worker {}, batch_job_ix {}" (the misread Q drives
    the page maxima to −inf). The same unfixed binary with `TRON_AMX_DISABLE=1`
    passes (2805 assertions), so the AMX path alone is the cause. Two apport core
    dumps (3.9 GB and 3.85 GB, ~20 min each — the kernel's core pipe ignores
    `ulimit -c 0`) were deleted from `/var/crash`; both worktrees removed. Conclusion so far: before the fix the `host` executor's AMX path does
    not merely produce wrong logits on this input, it trips an assertion; after
    the fix the same test passes with AMX enabled.
  - unit-level negative control on claude-box (05:31Z): with the gate temporarily
    reverted to `shape_ok` only (and the pack-site `static_assert` removed, since it
    would otherwise stop compilation), `t_amx_dispatch_dtype` fails exactly its
    `host` and `host_fp16` sections (`probe.pack_calls == 0` expected, the pack ran):
    2 failed / 516 passed; restored, all 518 pass. The tree was restored and
    rebuilt (`git status` clean at `e217f518e0`).

**Commits (pushed to `origin/jhan-amx-p0`).**
`02208bebcf` "AMX dispatch: gate on the executor's activation scalar, not geometry alone";
`62bc343923` "t_amx_numerics, t_llama_unit: pin the AMX query-scalar gate and the Q pack layout".

## P2 — Keep the scheduler within the advertised cache factory contract (`full.hpp:833-834`)

**Verdict: agree.** `sequence_cache_behavior` (kv_cache.hpp:1350-1376) requires only
`T::try_create(n_pages, storage_slot_count, support_eagle)`, while the PR made
`full_scheduler::node::kv_location_for_tokens` call the new four-argument overload
unconditionally, so a cache type that satisfies the public concept no longer compiles
with the scheduler. Only `book` implements `sequence_cache` today, so nothing shipped
breaks; it is a contract mismatch. Codex offered "add the overload to the concept" or
"feature-detect and fall back". I took the second: the mirror flag is an AMX-specific
extension, and a cache without a mirror arena is already correct by the fail-soft
design (every mirror consumer null-checks).

**Fix.** `kv_cache.hpp`: `amx_mirror_aware_cache<T>` (optional extension: the
four-argument factory) and `create_sequence_cache<T>(n_pages, slots, eagle,
amx_mirror_eligible)`, which passes the flag when `T` accepts it and calls the
three-argument factory otherwise. `full.hpp:834` uses it.

**Why existing tests missed it.** `sequence_cache` was asserted only for `book`
instantiations (`t_llama_unit.cpp:434-436`, `heterogeneous_scheduler_compile.cpp:207`)
and never for a cache that has *only* the advertised surface; nothing instantiated
the scheduler's factory call against a non-`book` cache.

**Tests added.** `t_llama_unit.cpp` "the scheduler's cache factory call stays within
the sequence_cache contract": a declaration-only `three_argument_sequence_cache`
(codex's pattern) satisfies `sequence_cache`, is not `amx_mirror_aware_cache`, and
`create_sequence_cache` is well-formed for it (compile-time); `book` still receives
the flag through the same call and allocates (runtime).

**Verification.** claude-box 2026-08-28 04:55Z: `t_llama_unit` 120027 assertions / 25
cases (new case 6), `t_amx_*` unchanged, `runtron` links. No AMX hardware needed.

**Commit (pushed).** `840106b44a` "scheduler: create KV books through the
sequence_cache factory contract".

## P1 (second) — Populate mirrors based on the slot's AMX consumers (`model.hpp:2769-2771`)

**Verdict: agree (latent).** `valid_attention_operation_descriptors` (kv_cache.hpp:305-308)
allows one writer plus read-only consumers of *other* query-head counts on a slot
(only the KV half of the geometry is compared, :326-328). `save_k_impl` gated the
write-through on the writer's own `kv_mul`; `amx_mirror_eligible` allocates on any
eligible kernel; the reader null-checks only the arena. A ratio-8 writer + ratio-4
read-only consumer on one head-128 slot → arena allocated, never written, read on
every dense page. Five-agent adversarial workflow: not refuted (0.92); no registered
plugin has a shared slot or a read-only operation (Loopy always emits a writer;
TronCheck and the IR permit read-only ops), so it is permitted-but-unused today.

**Fix.** `amx_attn::mirror_write_ok<T>(head_size) = head_size == 128 &&
query_scalar_ok<T>` replaces `eligible` in `save_k_impl` (codex's second remedy,
"populate every head-128 slot whenever its mirror exists"). Correct by construction:
a consumer reads a plane only if it is eligible, the slot's writer shares the slot's
KV geometry (head 128) and the model's single activation scalar, so its rows are
mirrored; whether the plane exists is `set_k_mirror`'s null check. Not taken:
deriving the gate from the slot's consumers (needs two code paths — the generated
`save_k<geometry, op>` has a constexpr operation index, the legacy one a runtime
binding — for no shipped benefit). Cost: single-kernel head-128 models with
`kv_mul != 4` now compile the write-through in and pay two branches per (row, KV head)
on AMX hosts only, always taking the no-arena path; hoist a per-book check only if a
3bda profile shows it.

**Why existing tests missed it.** Every registered plugin and every test configuration
has exactly one operation per slot, all writers; no test constructs a read-only
consumer, and the write-through and the reader were tested only with a single shared
geometry.

**Tests added.** `t_llama_unit.cpp` "K mirror write-through does not depend on the
writer's query ratio": the shared-slot configuration is valid, mirror-eligible through
the consumer, the writer's ratio fails `eligible`, and `mirror_write_ok` holds for its
rows (plus float/fp16 and head-64 negatives). Compile-time, any host.

**Verification.** claude-box 2026-08-28 05:10Z: `t_llama_unit` 120034 assertions / 26
cases, `t_amx_*` unchanged, `runtron` links. AMX-host run: covered by the queued
`exec/p3-q-scalar-gate.sh` (mirror and canonical configs, `t_generate_host`).

**Commit (pushed).** `323b9d5499` "K mirror write-through: fill every bf16 head-128 plane, not
only the writer's ratio".

## P1 (codex #4) — Include the K mirror in host-memory pressure accounting (`kv_cache.hpp:1054-1059`)

**Verdict: agree on the gap, disagree on the remedy and the severity (P2).**
Confirmed (seven-agent workflow, accounting claim not refuted at 0.95/0.93): the
arena (`kv_bytes/2` of ordinary RAM via nothrow `operator new[]`) is counted by
nothing — `dma_size_bytes()` is DMA by contract (EAGLE's `x_data` is counted there
because it is DMA), every scheduler byte gauge derives from it, the arena-mode
governor reads hugepage-pool counters only, and the footprint log printed DMA only.
Refuted as stated: (a) the consequence — cache targets are hugepage-pool budgets
(legacy `n_hugepages/2`, arena ~95% of the pool), books come from the pre-reserved
pool, so the arena total is bounded by pool/2 and no target setting pushes it toward
physical/cgroup capacity; on delphi-3bda (1.5 TiB RAM, 512 × 1 GiB hugepages, no
`MemoryMax`) the worst case has 3.8× headroom — production racks: Insufficient data;
(b) the remedy — feeding a cache-owned total into "memory-pressure and reclamation
decisions" is a no-op in arena mode (no book-byte input) and a unit-mixing capacity
cut in legacy mode (`--kv-cache-gb` is a DMA budget; counting heap bytes against it
retains 2/3 of the configured KV while relieving no pool pressure). The nothrow
allocation not being fail-soft under overcommit is correct as a hypothesis (not
demonstrated in-repo).

**Fix (visibility, not policy).** `book::mirror_arena_bytes()`; process-wide
`amx_attn::k_mirror_arena_live_bytes` (in the intrinsics-free interface header so
the app layer reads it without model headers); footprint log prints "DMA + K mirror";
FUSE gauge `/rinzler/stats/memory_pressure/k_mirror_arena_bytes` (both allocator
modes) + manifest entry; Note [K mirror parallel arena] "Accounting" bullet and a
governor-doc paragraph (units rule, pool/2 bound, provisioning rule, overcommit).

**Why existing tests missed it.** No test asserted anything about the arena's size
or its visibility; the accounting cross-check tests compare scheduler gauges with
the DMA shadow map, which is DMA-only by design, and the arena never allocated on the
non-AMX hosts that run the fake lane.

**Tests added.** `t_amx_arena_leak` now link-wraps `amx_attn::available()` to true
(codex's technique; `t/CMakeLists.txt`), so the arena path runs on any host: the two
former "AMX unavailable" skips became real checks, and "K mirror arena bytes are
visible to accounting" pins `mirror_arena_bytes() == dma_size_bytes()/2 ==` bytes
actually allocated `==` live-counter delta, and back to the baseline on destruction;
the 3-argument (ineligible) book reports 0.

**Verification.** claude-box 2026-08-28 05:20Z: `t_amx_arena_leak` 12 assertions / 3
cases (no skips), `t_llama_unit` 120034 / 26, `t_amx_numerics` 4109 / 5,
`t_amx_mirror` 24576 / 1, `runtron` and `rinzler` link; footprint line observed as
"KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 1 books" (tiny test books).
`t_tronstats_convention` needs a live FUSE mount (no `/dev/fuse` in this container);
run on delphi-3bda as `exec/p3b-mirror-accounting.sh f9b678e5d0` (isolated worktree,
mirror config, 05:35–05:37Z): **`t_tronstats_convention` 1149 assertions / 29 cases
passed** (the new `k_mirror_arena_bytes` manifest entry matches its on-disk
descriptor), `t_amx_arena_leak` 12 / 3, `t_amx_numerics` 6414 / 5, `t_llama_unit`
144875 / 26 — all passed (`exec/logs/p3b-mirror-accounting.txt`).

**Commit (pushed).** `f9b678e5d0` "K mirror arena: make its RAM visible (accessor, footprint
log, FUSE gauge)".
