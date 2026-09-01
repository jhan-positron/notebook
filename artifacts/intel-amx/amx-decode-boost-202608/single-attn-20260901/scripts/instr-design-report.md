# Attention phase probe ("single attention"): design report

Words used here:
- tron: the inference program under test; runtron: its command-line tool.
- unit: one call of `apply_page_tok`, i.e. one KV head of one 64-token KV page applied to one query token.
- TSC: the CPU cycle counter read by the `rdtsc` instruction.
- kvwait probe: the existing mmap stamp writer (`h/system/kvwait_probe.hpp`), records (t0, dur, tag) uint64 triples when `TRON_KVWAIT_FILE` is set.
- worker 0: the attention worker with `worker_ix == 0`; it already emits stamp 7605 (its own attention wall, TSC cycles, summed over the 36 attention operations of one token).
- AMX path / dotter path: `apply_page_tok` with `did_amx == true` (AMX QK and PV kernels) / `did_amx == false` (AVX-512 dotter loop for QK and `page.scaled_v` for PV).
- fence round 3: `exec/results/fence3-20260901/`, the uninstrumented reference numbers (`medians-7605.json`).

All line numbers refer to the current files in `/home/jhan/workspace/tron-fence-amx` (branch jhan-amx-fence, head 245502cb88) and were read on 2026-09-01. No repository file was edited; the two patch scripts were dry-run on copies only.

## 1. Phases and cost

### 1.1 Facts the design rests on

- `apply_page_tok` (`h/tron/models/self_attention.hpp:1491-1720`) is `TRON(inline)` = `inline __attribute__((always_inline))` (`h/common/attributes.hpp:78`) and has exactly one caller, `apply_page_range:1452`. Anything added to it is inlined into `apply_page_range`.
- `hardware::system::rdtsc()` (`h/system/system.hpp:304-306`) is `asm volatile("rdtsc")`: not serializing, no memory clobber. `kvwait_probe::state_t::now()` uses `__rdtsc()`, the same counter.
- `page.scaled_v(...)` is eager. The `scaled_v_expr` constructor computes the whole PV product (weights times V, 64 tokens, 128 lanes) into the caller's `scratch` tensor (`h/tron/models/kv_cache.hpp:2101-2135`). The `fma(...)` that consumes it only reads `scratch`. This is what allows the dotter-path PV to be timed without touching arithmetic.
- One attention worker runs all 36 attention operations of a token in a single `run_attention_worker` call on one thread (gen header `gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp:1749-1753`, one `enqueue_to` per worker index). So per-thread counters reset at worker start and read at worker end are exact for that token and that worker.
- `run_attention_job` (`self_attention.hpp:833-895`) already reads TSC at lines 862, 864, 867, 868, 874, 875, 878, 893 to form `attn_elapsed` (what 7605 sums) and `compute_elapsed` (fed to the speedometer). The patch names these reads and keeps both values bit-identical.
- `self_attn_state` is a public member of the model state (`h/tron/models/model.hpp:1086` public label, `:1130` declaration); `record_attention_time` is at `:2163`. The gen header and `self_attention.hpp` are both inside `namespace tron`.

### 1.2 Phase boundaries

| Phase | Path | Opens at | Closes at | TSC reads |
|---|---|---|---|---|
| unit open (`t_u0`) | both | after `bool did_amx = false;` (line 1512) | | 1 |
| (a) QK | AMX | `t_u0` | after the `if (!did_amx) {...}` block closes (1625); covers `s_pages` fill, `dot_q` construction, `qk_*_128x4` call and the `s_pages` memcpy | 1 (`t_qk`) |
| (a) QK | dotter | `t_u0` | same point; covers the dotter loop; empty units (relevant_k_tokens == 0) are counted here too | shared with above |
| (b) softmax | AMX | `t_qk` | after the scale/max/exp/sum/corr loop (1655) | 1 |
| (c) PV | AMX | | after `weights_times_v_128x4` (1662) | 1 |
| (d) state | AMX | | before `return` (1677); includes the four 512-byte `amx_o` memcpys, the v_star fma, s_star, m_star | 1 |
| (b)+(d) common | dotter | per head: previous mark .. after `exp(s_page - m_page)` (1697) | | 1 per head |
| (c) PV | dotter | per head: after the named `scaled_v` construction | | 1 per head |
| (b)+(d) tail | dotter | last head's PV end .. before `return` (1710); covers the last head's fma/s_star/m_star | | 1 |
| (f) Q pack | range | after the `static_assert` (1428) .. after `amx_packed_mask |=` (1445) | | 2 per pack |
| (f) region | range | around `begin_region` (1382) and `end_region` (1481) | | 4 per range, AMX on only |
| range wall | range | after `if (page_range.empty()) return;` (1339) .. function end (1484) | | 2 per range |
| sections ready / pending | operation | existing reads at 862 and 868 (ready); 874 and one new read after the pending `run_sections` (878) | | 1 new |
| (i) upstream wait | operation | existing read at 868 .. existing read at 874 | | 0 new |
| (g) joins | operation | around `run_joins` (885-886) | | 2 |
| (h) barrier | operation | before `arrive_and_wait` (892) .. existing final read (893) | | 1 new |

On the dotter path, softmax (b) and state (d) are not separated; they are both common work and the AMX path separates them. The dotter "common" phase for head h is (state of head h-1) + (softmax of head h); the tail read closes the last head's state.

Dotter-path choice: per-head timing, not a cross-head reordering. The only non-probe edit is naming the eager `scaled_v` result (`const auto pv = page.template scaled_v<...>(...)`) before the `fma` argument list. Reordering the four heads' softmax ahead of the PV (like the AMX block does) would also be bit-identical, but it changes register pressure and cache access order of the dotter arm, which is the thing being measured. Per-head timing costs more reads, and that cost is measurable and correctable (1.4).

### 1.3 TSC reads and estimated overhead

| Unit kind | reads | added cycles (25 per read) | share of an 8000-11000 cycle unit |
|---|---|---|---|
| AMX unit | 5 | 125 | 1.1-1.6% |
| dotter unit, non-empty | 11 | 275 | 2.5-3.5% |
| dotter unit, empty | 2 | 50 | n/a |
| per Q pack | 2 | 50 | |
| per range (AMX on) | 6 | 150 | |
| per range (AMX off) | 2 | 50 | |
| per operation | 4 new | 100 | 36 operations per token: 3600 cycles |

The 25 cycles per read is the assumed Granite Rapids `rdtsc` cost; it is measured, not assumed, in 1.4.

Total reads per token for worker 0: R = 5·units_amx + 11·units_dotter + 2·units_empty + 2·qpacks + 2·ranges + 4·ranges_with_amx + 4·36. All terms except ranges_with_amx are exported counters; ranges_with_amx = ranges on the AMX arms and 0 on the disable arm.

Cost with the probe disabled (env var unset): every check is a load of the global `attn_phase::enabled` plus a never-taken branch, 5 per AMX unit, 11 per dotter unit, about one cycle each, under 0.15% of a unit. The branch points also split basic blocks and limit instruction scheduling across them; that part cannot be quantified by reading. With the env var unset no stamps exist, so the disabled cost is visible only in the "average tok/s" line of `cell.log` compared with fence round 3.

### 1.4 Overhead measurement method

1. Build the instrumented binaries (same three arms as fence round 3: canonical, mirror, kill switch).
2. Run the same nine cells as `exec/fence-20260831/run-fence3.sh` (fcanon, fmirror, disable × prompt length 256, 2048, 8192; 256 generated tokens; one user), with `TRON_KVWAIT_FILE` set.
3. Extract 7605 with `exec/fence-20260831/extract7605.py` and compare per cell with `exec/results/fence3-20260901/medians-7605.json` key `attn` (microseconds, TSC 2.7 GHz):

| cell | fence3 attn median (us) | p10..p90 (us) |
|---|---|---|
| fcanon-256 | 631 | 592..677 |
| fcanon-2048 | 1375 | 1318..1421 |
| fcanon-8192 | 4790 | 4731..4879 |

4. Expected inflation per token = R × c_rd / 2700 microseconds. Solve for c_rd from the measured delta (instrumented 7605 median minus fence3 median). A value of 15-40 cycles means the reads explain the delta; anything larger means the branch points themselves cost time and the per-phase numbers need that caveat.
5. Internal consistency checks per window: (cyc_sections_ready + cyc_sections_pending) − Σ cyc_range = per-section overhead outside `apply_page_range`; cyc_range − Σ unit phases − cyc_qpack − cyc_region = page-loop bookkeeping (visibility test, sliding-window test, mark_valid), which divided by `pages` is the per-page bookkeeping cost. Both must be non-negative and small; a negative value means a boundary is misplaced.
6. Also run the disable arm once with the env var unset and compare tok/s with fence3 `cell.log` for the disabled-branch cost.

## 2. Export design

Recommendation: per token, from worker 0, immediately after stamp 7605, one stamp per counter with tag 7606 + index. Payload is the `dur` field, `t0` = now, same convention as 7605. 22 stamps per token. The existing decode-window filter (exactly one 7601, 7602, 7603, 7604, 7605 between consecutive 7600 ends) still holds and extends to the new tags, which also appear exactly once per token. Per-operation emission would multiply records by 36 and need a layer number in the tag; it is not needed for per-unit costs.

### 2.1 Tags and payload semantics

All payloads are for worker 0, one token, summed over the 36 attention operations. Cycles are TSC ticks (2.7 GHz on delphi-3bda).

| tag | counter | payload | unit |
|---|---|---|---|
| 7606 | units_amx | units that took the AMX QK path | count |
| 7607 | units_dotter | dotter-path units with relevant_k_tokens > 0 | count |
| 7608 | units_empty | dotter-path units with relevant_k_tokens == 0 (early return after QK) | count |
| 7609 | k_tokens_dotter | Σ relevant_k_tokens over dotter-path units (AMX units are always 64) | KV tokens |
| 7610 | pages | page-loop iterations in `apply_page_range` | count |
| 7611 | ranges | `apply_page_range` calls with a non-empty page range | count |
| 7612 | qpacks | Q group packs (`pack_q_rows_128x4` or `pack_q_group_128x4` calls) | count |
| 7613 | cyc_qk_amx | AMX units: unit open .. QK kernel and `s_pages` copy done | cycles |
| 7614 | cyc_softmax_amx | AMX units: scale, max, exp, sum, corr, m_new loop over 4 heads | cycles |
| 7615 | cyc_pv_amx | AMX units: `weights_times_v_128x4` call | cycles |
| 7616 | cyc_state_amx | AMX units: `amx_o` copies + v_star fma, s_star, m_star, 4 heads | cycles |
| 7617 | cyc_qk_dotter | dotter units (incl. empty): unit open .. dotter loop done | cycles |
| 7618 | cyc_common_dotter | dotter units: softmax pieces + v_star/s_star/m_star update, all heads | cycles |
| 7619 | cyc_pv_dotter | dotter units: `page.scaled_v` PV product, all heads | cycles |
| 7620 | cyc_qpack | time inside the Q pack calls | cycles |
| 7621 | cyc_region | `amx_attn::begin_region` + `end_region` | cycles |
| 7622 | cyc_range | `apply_page_range` wall, non-empty ranges | cycles |
| 7623 | cyc_sections_ready | `run_sections(pending=false)` wall (same read pair as the first `attn_elapsed` segment) | cycles |
| 7624 | cyc_sections_pending | `run_sections(pending=true)` wall | cycles |
| 7625 | cyc_upstream_wait | `upstream_kvs_ready[slot].wait()` | cycles |
| 7626 | cyc_joins | `run_joins` wall | cycles |
| 7627 | cyc_barrier | `attn_done_barrier.arrive_and_wait` | cycles |

### 2.2 Storage and accessor API

Storage: `namespace tron::attn_phase` at namespace scope in `self_attention.hpp`, before `struct self_attention`:

```cpp
enum idx : size_t { units_amx, ..., cyc_barrier, n_counters };  // order = tag - 7606
struct counters { uint64_t v[n_counters] = {}; };
inline thread_local counters tls;
inline const bool enabled = kvwait_probe::state().enabled;  // read once at static init
```

Accessors, static members of `self_attention::state` (placed next to `enclosing_state` at line 460; `state` members are public):

```cpp
static attn_phase::counters probe_take() noexcept;  // copy the calling thread's counters, then zero them
static void probe_reset() noexcept;                 // zero the calling thread's counters
```

Gen header call sites (both added by the patcher):
- `outer_state.self_attn_state.probe_reset();` right after `uint64_t attn_elapsed = 0;` at the start of `run_attention_worker`, executed by every worker. This makes the counters exact even if the worker-to-thread mapping were to change between tokens.
- Inside the worker-0 block after operation 35, inside `if (kvp.enabled) {`, after the 7605 add:

```cpp
{
  const tron::attn_phase::counters pcs = outer_state.self_attn_state.probe_take();
  for (size_t i = 0; i < tron::attn_phase::n_counters; ++i)
    kvp.add(kvwait_probe::state_t::now(), pcs.v[i], 7606 + i);
}
```

## 3. Applying the two patch scripts

Files (scratchpad, not yet copied into the repositories):
- `/tmp/claude-0/-home-jhan-workspace-intel-AMX/2549245f-706d-4cdd-bc17-40d5d5064a07/scratchpad/patch-self-attn-phase.py`: 14 exact OLD → NEW string replacements in `h/tron/models/self_attention.hpp` (this is the source-tree change; commit it on jhan-amx-fence).
- `/tmp/claude-0/-home-jhan-workspace-intel-AMX/2549245f-706d-4cdd-bc17-40d5d5064a07/scratchpad/patch-gen-stamps.py`: replacement for `~/workspace/intel-AMX/exec/fence-20260831/patch-gen-stamps.py`; stamps 7601, 7603, 7604/7605, 7606-7627 and the `probe_reset` line into the generated plugin header.

Order:
1. Copy `patch-gen-stamps.py` over `~/workspace/intel-AMX/exec/fence-20260831/patch-gen-stamps.py`.
2. Run `python3 patch-self-attn-phase.py` (default path = the fence worktree file). Commit on jhan-amx-fence.
3. Configure the fence worktree (cmake) as usual, then run `python3 ~/workspace/intel-AMX/exec/fence-20260831/patch-gen-stamps.py`, then ninja inside `nix develop` (never `cmake --build` outside nix; see the build-env memory).
4. Re-run step 3's patcher after every configure; the generated header is rewritten by the ingest generator.

Idempotency and what the dry-runs proved (copies in the scratchpad, `self_attention.copy.hpp`, `gen.today.hpp`, `gen.pristine.hpp`):
- self_attention patcher: all 14 anchors matched exactly once; a second run prints `already patched` and changes nothing.
- gen patcher on a copy of today's header (already carrying 7601-7605): applied only `7606-7627` and `probe_reset`; the 7604/7605 block text is untouched (the diff shows additions only). Second run prints `already stamped`.
- gen patcher on a reconstructed pristine header (today's stamps reversed, zero `kvwait` mentions): applied all five stages; the result is byte-identical (`cmp`) to the result from today's header. So the 7604/7605 text the new patcher writes equals today's header text exactly, and a regenerated header ends up identical to an upgraded one.
- Each stage checks its own marker (`site 7601`, `site 7603`, `site 7604`, `sites 7606`, `probe_reset`) and asserts anchor count == 1, so a partially stamped header is upgraded rather than rejected.

Not done here: compiling. Two points to watch in the first nix build: `fma(head_sp.v_star, exp_m_star_minus_m_, pv)` now receives a const lvalue `scaled_v_expr` instead of a prvalue (if `fma` takes it by value, `scaled_v_expr` is copyable: const members plus a reference member); and `pc.v[...] += static_cast<uint64_t>(relevant_k_tokens)` avoids a sign-conversion warning.

## 4. Extraction outline (Python reader)

Base it on `exec/fence-20260831/extract7605.py`.

1. Load: first uint64 is the record count; then (t0, dur, tag) uint64 triples; sort by t0.
2. Decode windows: F3 ends = t0 + dur of 7600 records. A window is (F3 end i-1, F3 end i]. Keep it only if every tag in 7601..7627 occurs exactly once inside it. (The prompt-parsing window and any window with a dropped record are excluded.)
3. Cycles to microseconds: × 1e6 / 2.7e9 (accept `--tsc-ghz=`).
4. Per window compute:
   - AMX per unit: `cyc_qk_amx / units_amx`, `cyc_softmax_amx / units_amx`, `cyc_pv_amx / units_amx`, `cyc_state_amx / units_amx`. Per KV token: divide by 64 again. Arm-specific AMX = qk + pv; common AMX = softmax + state.
   - Dotter per unit: `cyc_qk_dotter / (units_dotter + units_empty)` for QK (or subtract the empty units' share if `units_empty` is material), `cyc_pv_dotter / units_dotter`, `cyc_common_dotter / units_dotter`. Per KV token: divide by `k_tokens_dotter`. Arm-specific dotter = qk + pv; common dotter = common.
   - Bookkeeping per page: `(cyc_range − cyc_qk_amx − cyc_softmax_amx − cyc_pv_amx − cyc_state_amx − cyc_qk_dotter − cyc_common_dotter − cyc_pv_dotter − cyc_qpack − cyc_region) / pages`.
   - Per range: `cyc_qpack / qpacks`, `cyc_region / ranges`, section overhead `(cyc_sections_ready + cyc_sections_pending − cyc_range) / ranges`.
   - Per token: `cyc_upstream_wait`, `cyc_joins`, `cyc_barrier`, and residual `7605 − cyc_sections_ready − cyc_sections_pending − cyc_joins − cyc_barrier` (channel handshakes, `free_scratchpads_barrier.done`, `post_attention`).
   - Overhead correction: R from 1.3 and c_rd from 1.4; subtract one read (c_rd) per boundary from each phase, i.e. per AMX unit one c_rd from each of qk, softmax, pv, state; per dotter unit one from qk, and (per head) one from common and one from pv.
5. Aggregate per cell (arm × context) as median, p10, p90 over windows, as today. Emit JSON with the same shape as `medians-7605.json` plus the new keys.
6. Scope note for the report: counts and cycles are worker 0's share of the token. Whole-token totals need multiplying by the attention worker count, valid only if the speedometer balanced the work; state that as an assumption.

## 5. Risks

- (i) `rdtsc` is not serializing. Sums over thousands of units are reliable; a single boundary can shift by tens of cycles under out-of-order execution. The smallest phase (AMX state, a few hundred cycles per unit) carries the largest relative error. Report it with that caveat; do not read differences of a few percent in it as real.
- (ii) `inline thread_local` variable in a header: legal C++17; precedent in the same file for function-local `thread_local` at lines 1370 (`amx_qpack`) and 1583 (`qk_s`). Counters are touched only when the probe is on. `attn_phase::enabled` is dynamically initialized at static-init time by calling `kvwait_probe::state()`, which opens the mmap then; the env var is already set at exec, and no static initializer runs attention before `main`. The TLS access in an executable is a single fs-relative load.
- (iii) Dotter-path numerics. The only ordering change is that the eager `scaled_v` constructor now runs before `std::exp(head_sp.m_star - m_page)` in the was_valid branch. The two have disjoint inputs (V page and `exp_s_minus_m` versus `m_star` and `m_page`) and disjoint outputs (`scratch` versus a local float); each head's arithmetic sequence is otherwise unchanged; v_star, s_star, m_star are written afterwards as before; `sum(exp_s_minus_m)` still runs after `scaled_v`, as before. So the result bits are identical by construction. Confirm with an A/A run under the runtron determinism recipe (pay-for-determinism, temperature 0, `USE_HW_ATTN=0`, one prompt, force-feed token file): instrumented versus uninstrumented disable arm must give bit-identical logits. Also run `t_amx_numerics` and `t_llama_unit`. The pre-existing `pure` attribute on `scaled_v` (kv_cache.hpp:1761) is unaffected by naming the result.
- (iv) The generated header is rewritten at every configure. The new patcher is staged and idempotent; re-run it after each configure, before ninja. The `self_attention.hpp` change lives in the source tree and is unaffected by regeneration. NFS attribute-cache trap: after editing on one host, verify the file content on the build host before building.
- (v) Compile not verified here (see section 3). Names `probe` and `pc` are introduced in three functions; no existing identifiers with those names were found in `run_attention_job`, `apply_page_range` or `apply_page_tok`.
- (vi) The probe changes basic-block structure inside an always-inline hot function even when disabled. That is why the 7605 comparison against fence round 3 (section 1.4) is part of the protocol, not optional, and why the disable-arm tok/s with the env var unset should also be compared.
- (vii) `cyc_range` counts only non-empty ranges, while `cyc_sections_*` include calls with empty page ranges; the difference is a few dozen cycles per empty call and is part of the "section overhead" term.
