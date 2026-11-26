# Part B (AMX attention, head 256, 4 query heads per KV head): what must change

Short version: the 128x4 shape is hardcoded in 8 files (2 kernel files, self_attention.hpp, 1 comment in v_vnni.hpp, 3 tests, 1 CMake comment). K and V storage, the softmax step, the running-sum update and the attention statistics are already generic in the head size, so Part B needs 3 new kernels, 2 new constants, a second gate, a larger packed-query slot, and test additions. Recommended form: a second interface namespace `tron::amx_attn_h256g4` with non-template `_256x4` entry points.

Root of the code under study: `/home/jhan/workspace/ai-runs/tron-qwen35-4b` (commit 72e1191804). Paths below are relative to it unless absolute.

## 0. How the model instantiates attention

Generated plugin `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp`:
- line 37-39: `n_heads = 16; n_kv_heads = 4; head_size = 256;`
- line 45: 8 cache slots, each `tron::kv_slot_spec{tron::kv_geometry{4, 256}, tron::kv_slot_retention::full_history()}`; line 46 `using cache_t = tron::heterogeneous_kv_cache<cache_slot_specs, ...>`
- line 49 `attn_softcapping = false`; line 51 `force_hw_attn = true`; line 58 `max_minibatch_size = 1024`
- line 60: one kernel, `tron::attention_geometry{16, tron::kv_geometry{4, 256}}`; line 61: no sinks
- line 62: 8 operations at model layers 3, 7, 11, 15, 19, 23, 27, 31 (KV slots 0..7), all `attention_hardware_capability::kv_slot_candidate`, scale `6.25e-2f`
- line 996 / 1002: query buffer `cat` and output `sdpa` are `btensor_t<4096>` (16 x 256)
- lines 7120-7141: `outer_state.template run_attention_job<tron::attention_geometry{16, tron::kv_geometry{4, 256}}, N>(q_batch->outer_batch, cat, q_batch->cat_channel, sdpa, ...)`

Derived in `h/tron/models/kv_cache.hpp:190-211`: `geometry.kv_mul()` = 16 / 4 = 4, `geometry.kv.head_size` = 256. Call path: `model.hpp:2642 run_attention_job` -> `self_attention.hpp:771` -> `run_sections<geometry>` (1148) -> `apply_page_range<geometry>` (1166, 1453) -> `apply_page_tok<geometry>` (1635, 1829). The campaign runs executor tp4 (`exec/gdn-20261120/run-one.sh:24`), whose activation scalar is bf16, so `query_scalar_ok` holds. Only `shape_ok` rejects the model today.

Run-log evidence (`/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/rt/q35-tp4-1u-p4096__on__rep1.log:232-238`): `"amx_compiled":true,"amx_available":true,"kv_mul":4,"head_size":256` and every layer reads `amx/avx/fpga = 0/N/0`.

## 1. Every place that hardcodes 128x4

### h/tron/kernels/amx_attn_iface.hpp
| Line | Text | Needs for 256x4 |
|---|---|---|
| 13-15 | "The kernels serve one shape: head size 128 and kv_mul 4, hence the namespace name amx_attn_h128g4" | reword: two shapes |
| 19-31 | Note [AMX attention dispatch]: "head size 128 and kv_mul 4 ... 4096 bytes: four panels" | add 256x4: 8 panels, 8192 bytes |
| 55-67 | contract diagram "q (4 heads x 128 bf16) ... qk_rowmajor_128x4 ... O[4][128]" | add the 256 names |
| 91-107 | Note [Tile stores write 16 rows]: "16 rows of 128 fp32 (8192 bytes)" | 16 x 256 fp32 = 16384 bytes |
| 115 | `namespace tron::amx_attn_h128g4 {` | second namespace (section 8) |
| 137-139 | `PAGE_TOKENS_64 = 64; HEAD_SIZE_128 = 128; GROUP_HEADS_4 = 4;` | new `HEAD_SIZE_256`; the other two are shared |
| 143-144 | `Q_PACK_ELEMS_2048 = TILE_ROWS_16 * HEAD_SIZE_128; static_assert(... == 2048 ...)` | new `Q_PACK_ELEMS_4096` |
| 149-151 | `shape_ok`: `model_head_size == HEAD_SIZE_128 && model_kv_mul == GROUP_HEADS_4` | second `shape_ok` for 256 |
| 163-166 | `eligible<query_scalar_t>(head, kv_mul)` = `shape_ok && query_scalar_ok` | second `eligible` |
| 187 | `void pack_q_group_128x4(const bf16* q_group, bf16* packed) noexcept;` (raw pointers: the type does not carry the shape) | `pack_q_group_256x4` |
| 222-225 | `void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_packed, float* s, size_t s_stride_floats) noexcept;` | `qk_rowmajor_256x4` |
| 234-238 | `void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page, const float* exp_rows, size_t row_stride_floats, float* o) noexcept;` | `weights_times_v_256x4` |

Shape-independent and reusable as they are: `TILE_ROWS_16`, `TILE_ROW_BYTES_64` (130-131), `PAGE_TOKENS_64`, `GROUP_HEADS_4`, `query_scalar_ok` (159-160), `available()` (171), `begin_region()` / `end_region()` (242-243).

### src/tron/kernels/amx_attn.cpp
| Line | Text | Needs |
|---|---|---|
| 31-32, 101, 278 | namespace + unnamed namespace nested inside `tron::amx_attn_h128g4` | 256 code needs access to the tile constants (38-67) |
| 64 | `PV_TILES_PER_HALF_4 = 4` ("two 64-dim halves") | 256 has 4 groups of 64 dims |
| 69-73 | `BF16_ROW_BYTES = HEAD_SIZE_128 * sizeof(bf16)` (256 B), `V_PAIR_ROW_BYTES = 2 * HEAD_SIZE_128 * sizeof(bf16)` (512 B), `O_ROW_BYTES = HEAD_SIZE_128 * sizeof(float)` (512 B) | 512 B, 1024 B, 1024 B |
| 129-143 | packer: `step < HEAD_SIZE_128 / DIM_STEP_32` (4 panels), source index `q_head * HEAD_SIZE_128 + ...` | 8 panels, `q_head * 256` |
| 162-177 | QK loop: `step < HEAD_SIZE_128 / DIM_STEP_32`, K loads at `k_rows + blk * TILE_ROWS_16 * HEAD_SIZE_128 + step * DIM_STEP_32`, stride `BF16_ROW_BYTES` | 8 steps, row length 256, stride 512 B |
| 157, 178-215 | `s_transposed[64*16]`, 4 stores, transpose of rows 0..3 | shape-independent, reusable unchanged |
| 232-241 | `thread_local uint16_t P[TILE_ROWS_16][PAGE_TOKENS_64]`, fp32 -> bf16 by `_mm512_cvtne2ps_pbh` | shape-independent |
| 243 | `for (int half = 0; half < 2; half++)` | 4 groups |
| 251-268 | V loads at `v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2 + (half * PV_TILES_PER_HALF_4 + i) * DIM_STEP_32`, stride `V_PAIR_ROW_BYTES` | 256 and stride 1024 B |
| 271-274 | `_tile_stored(ACC_i, o + half * 64 + {0,16,32,48}, O_ROW_BYTES)` (literals 64/16/32/48) | same literals, group 0..3, stride 1024 B |

### h/tron/models/self_attention.hpp (all inside `#ifdef TRON_AMX_DISPATCH` except 1626 and 1841)
| Line | Text | Needs |
|---|---|---|
| 259-261 | `struct alignas(64) amx_qpack_slot { bf16 v[amx_attn_h128g4::Q_PACK_ELEMS_2048]; };` (state level, not per geometry) | 4096 elements for a 256x4 model |
| 284 | `std::vector<amx_qpack_slot> amx_qpack;` in `attn_accum` | no edit |
| 479 | `facts.amx_available = amx_attn_h128g4::available();` | shape-independent, no edit |
| 1533-1536 | `constexpr bool amx_eligible = amx_attn_h128g4::eligible<typename model::activation_scalar>(geometry.kv.head_size, geometry.kv_mul()); const bool amx_on = amx_eligible && amx_attn_h128g4::available();` | OR with the 256 gate |
| 1552-1553, 1558 | `amx_qpack.resize(items.size()); amx_attn_h128g4::begin_region();` / `end_region()` | no edit |
| 1628-1632 | `if constexpr (amx_eligible) { if (amx_on) amx_qp = packed_amx_query<geometry>(amx_qpack[batch_job_ix].v, ...) }` | no edit |
| 1690-1694 | `static_assert(amx_attn_h128g4::query_scalar_ok<...>)`; `amx_attn_h128g4::pack_q_group_128x4(q.data + kv_head * geometry.kv_mul() * geometry.kv.head_size, slot);` | select the packer by shape; assert the slot is large enough |
| 1741-1745 | `static_assert(amx_attn_h128g4::eligible<...>(operation_head_size, operation_kv_mul), ...)`; `static_assert(amx_attn_h128g4::PAGE_TOKENS_64 == page::page_size, ...)` | combined gate |
| 1760-1761 | `amx_attn_h128g4::qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size);` | select by shape |
| 1786-1789 | `alignas(64) float amx_o[amx_attn_h128g4::TILE_ROWS_16 * operation_head_size]; amx_attn_h128g4::weights_times_v_128x4(pg.template v_packed<geometry.kv>(slot, kv_head), &s_pages[0][0], page::page_size, amx_o);` | select by shape; `amx_o` already scales with the head size |
| 1877-1878 | `if constexpr (amx_attn_h128g4::eligible<typename model::activation_scalar>(operation_head_size, operation_kv_mul))` | combined gate |
| comments 255-258, 1526, 1537-1539, 1681, 1750, 1754-1756, 1783-1785 | "4096 bytes", "head-128 / kv_mul-4", "128-dim rows" | reword |

### Other files
- `h/tron/tensor/v_vnni.hpp:46`: comment names `amx_attn_h128g4::weights_times_v_128x4` as one of "the two layout-specific kernels"; with a second PV kernel the count in lines 48-50 and 65-66 changes too. Comment only.
- `t/t_amx_numerics.cpp`: lines 37-40 (using), 69-72, 92-113, 122-137, 149-188, 196-268.
- `t/t_amx_dispatch_dtype.cpp`: lines 57, 72-76, 228-257, 262.
- `t/t_llama_unit.cpp`: lines 101, 106 (requires-probes), 512-519 (type aliases).
- `t/CMakeLists.txt:685-686`: comment "Defines CPU fakes for every amx_attn_h128g4 entry point".
- `ingest/` and `config/`: no hit for any of the six names. `config/tests.core.txt:1-2` and `config/test-benchmarks.json:151-152, 496-497` only list the two test binaries.

## 2. K and V page layout for head 256

- `h/tron/models/kv_cache.hpp:2416-2459` `detail::kv_block<page_size, head_size>`:
  - `alignas(kv_block_alignment) bf16 k[page_size * head_size];` (2420), "k is indexed as [p * head_size + i], one row of head_size bf16 values per token". For head 256: 64 x 256 bf16 = 32 KiB, row-major, row stride 512 bytes.
  - `using v_storage = v_vnni_tensor<page_size, head_size>; alignas(kv_block_alignment) v_storage v;` (2425, 2430), `static_assert(sizeof(k) == sizeof(v));` (2433). For head 256: 32 KiB. One kv_block = 64 KiB.
- V is VNNI pair-interleaved for every head size in every build. `kv_cache.hpp`, `v_vnni.hpp` and `kv_cache_fwd.hpp` contain no `#if` and no `TRON_AMX` test. The layout is not keyed on `shape_ok` or on `TRON_AMX_DISPATCH`. A head-256 model stores exactly this layout today.
- Formula, `h/tron/tensor/v_vnni.hpp:33-46` (Note [VNNI Packed V layout]): "The V plane of a kv_block stores token pairs interleaved: for each dimension d, the values of tokens 2p and 2p + 1 sit next to each other. With D dimensions per token, element (token, d) is at `plane[(token / 2) * (2 * D) + 2 * d + token % 2]` (in bf16 elements) so one "pair row" of 2 * D bf16 holds two whole tokens. One 64-byte vector load at pair_base + 2 * 16 * i yields dims [16 * i, 16 * i + 16) of both tokens. In every 32-bit lane the even token sits in the low 16 bits and the odd token in the high 16 bits." Code: `pair_base(token) = data_ + (token / 2) * (2 * Cols)` (v_vnni.hpp:119-121), `at()` = `pair_base(token)[2 * dim + token % 2]` (103). For D = 256 a pair row is 512 bf16 = 1024 bytes; 32 pair rows per page.
- Typed views: K is `const_native_k_view<Rows, Cols>` = `const_view<bf16, true, false, integer_sequence<size_t, Rows, Cols>, integer_sequence<ptrdiff_t, Cols, 1>>` (`kv_cache_fwd.hpp:48-53`). `page::k<geometry.kv>(slot, kv_head)` (kv_cache.hpp:1944-1950) returns `kv_block<geometry>(slot, kv_head).k_view()`. `page::v_packed<geometry.kv>(slot, kv_head)` (2029-2036) returns `v_vnni_view<const bf16, page_size, geometry.head_size>`. Both already carry 256.
- Writers: K by `pg.template k<geometry.kv>(slot, kv_head, j).set(kout)` (`model.hpp:3555`); V by `pg.template set_v<geometry.kv>(...)` (`model.hpp:3620`) -> `append_v_row` (`v_vnni.hpp:239-263`). An even token zeroes its odd partner.
- AVX reader of V: `detail::scaled_v_expr<page_size, head_size>` (`kv_cache.hpp:2246-2410`), called from `self_attention.hpp:1961-1967`. Constructor `requires(head_size == 64 || head_size == 128 || head_size == 256 || head_size == 512)` (2340-2341). Head 256 runs `accumulate_16_chunks<0>(end)` (2387-2388; body 2268-2309): per token pair `tile = data + i * head_size + 2 * chunk_size * chunk_offset`, 16 loads of 64 bytes, `_mm512_dpbf16_ps(t_j, load, scale)` into 16 accumulators. `scale = interleave_bf16_ps(scales[i], scales[i + 1])` truncates fp32 to bf16 (2400-2405). `end = (count + 1) / 2 * 2`.
- AVX reader of K: `dotter<bf16, 256, aligned>` exists (`h/tron/kernels/dotter.hpp:226-297`): 8 loads of 32 bf16, two accumulators, `_mm512_dpbf16_ps`, `reduce_sum(sum1 + sum2)`.

## 3. Per-worker buffers and what doubles

| Buffer | Where | 128x4 | 256x4 |
|---|---|---|---|
| packed query slot `amx_qpack_slot` | self_attention.hpp:259-261; one per token job, `amx_qpack.resize(items.size())` at 1552 | 2048 bf16 = 4096 B | 4096 bf16 = 8192 B (doubles; needs a code change) |
| raw query group read by the packer | 1693-1694 | 512 bf16 = 1024 B | 1024 bf16 = 2048 B |
| `s_pages` `tensor<operation_kv_mul, page::page_size>` | 1753, 1892 | 4 x 64 fp32 = 1024 B | same |
| `s_transposed` (inside QK kernel) | amx_attn.cpp:157 | 64 x 16 fp32 = 4096 B | same |
| `P` (inside PV kernel, thread_local) | amx_attn.cpp:232 | 16 x 64 u16 = 2048 B | same |
| `amx_o` | self_attention.hpp:1786, `TILE_ROWS_16 * operation_head_size` floats | 8192 B | 16384 B (doubles automatically) |
| `scratch` `tensor<operation_head_size>` | 1794, 1957 | 512 B | 1024 B (automatic) |
| `corr_arr`, `m_new_arr`, `sum_arr` | 1764-1765 | 4 floats each | same |
| K page / V page | kv_cache.hpp:2420, 2430 | 16 KiB each | 32 KiB each |
| K tile-load stride / V pair-row stride / O row stride | amx_attn.cpp:69-73 | 256 / 512 / 512 B | 512 / 1024 / 1024 B |
| tile work per (query token, page, KV head) | amx_attn.cpp:162-181, 243-275 | QK: 16 products, 20 loads, 4 stores. PV: 16 products, 20 loads, 8 stores | QK: 32 products, 40 loads, 4 stores. PV: 32 products, 40 loads, 16 stores (matches design 5.5) |

Existing and unchanged for this model: `v_stars` is `std::array<btensor_t<scratch_query_width>, max_minibatch_size>` (270), with `scratch_query_width` = 4096 and 1024 token slots.

Measured context for the slot array: a prefill forward of the baseline holds 1024 token jobs (`rt/q35-tp4-8u-p4096__off__rep3.log:218`: `"forwards":32 ... "token_jobs":32768`). With 8192-byte slots that is 8 MiB of packed queries per attention worker (4 MiB with 4096-byte slots).

## 4. Softmax and update code between QK and PV

- `self_attention.hpp:1764-1782`: per query head `offset < operation_kv_mul`: `s_page = s_page * operation_scale` (or the tanh softcap), `m_page = max(s_page)`, `if (was_valid) m_page = std::max(head_sp.m_star, m_page)`, `s_page = exp(s_page - m_page)`, `sum_arr[offset] = sum(s_page)`, `corr_arr[offset] = was_valid ? std::exp(head_sp.m_star - m_page) : 0.f`. It works on `tensor<page::page_size>` only. No head-size dependence.
- `1791-1806`: `tensor<operation_head_size> scratch; std::memcpy(&scratch[0], amx_o + offset * operation_head_size, operation_head_size * sizeof(float));` then `head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch))` or `.set(scratch)`. Generic. `constant<page::page_size>(corr_arr[offset])` is a broadcast: `constant<N>::chunk(i)` returns the same vector for every i (`expr.hpp:310-313`) and `fma_expr` takes its size from X (`expr.hpp:517`). The AVX path uses the same construct for head 256 today (1960-1963).
- One implicit contract: row `offset` of `amx_o` starts at `offset * operation_head_size` floats. The 256 PV kernel must store with a row stride of 256 floats (1024 bytes).
- Verdict: head-size generic. Only the two kernel calls and the two static_asserts name the shape.

## 5. Attention statistics on the AMX path

- Hooks: `apply_page_range` copies `stats_enabled` once (1471-1479); per visit `stats_tally.record(visit.served, relevant_k_tokens, page::page_size); path_bits[tok_ix.i] |= attn_stats::path_bit(visit.served);` (1640-1643); per call `stats_ref.add_visits(stats_worker, binding.model_layer.i, stats_tally, pending ? PASS_PENDING_1 : PASS_READY_0)` (1670-1675).
- The AMX path returns `{range_hint, int(page::page_size), attn_stats::visit_path::amx}` (1888); AVX returns `visit_path::avx` (1972); empty returns `visit_path::empty` (1940).
- `attn_stats.hpp:115` `enum class visit_path : uint8_t { empty = 0, avx = 1, amx = 2 };` `visit_tally::record` (208-216) uses only the path, the K token count and the page size. `avx_full_page_visits` (200-205) counts AVX visits that scored a whole page.
- Header facts (`self_attention.hpp:476-485`): `amx_compiled`, `amx_available = amx_attn_h128g4::available()`, `n_kv_heads`, `kv_mul`, `head_size`, `n_layers`, `page_size`. They report CPU, OS and kill-switch state, not shape eligibility. Rows are keyed on `binding.model_layer.i` (layers 3, 7, ... 31 for this model).
- Verdict: shape-generic. No code change for Part B. The summary line already prints `"kv_mul":4,"head_size":256`.
- Expected signal after Part B, from the baseline: prefill `ready_avx_visits` 32505856 = `ready_avx_full_page_visits` 32505856, pending 1572864 visits of which 540672 full pages (`rt/q35-tp4-8u-p4096__off__rep3.log:217`). Per attn_stats.hpp:202-204 the kill-switch run's `avx_full_page_visits` equals the AMX-on run's amx visits plus its own `avx_full_page_visits`.

## 6. Why this model has no FPGA attention

- The check: `h/tron/models/model.hpp:835-845` `model_shape_is_hwattn_eligible()`: `return has_candidate && valid_uniform_hardware_attention_scale(plugin_t::attention_operations) && (head_size == 128 || head_size == 64) && n_kv_heads <= hardware::HW_MAX_KV_HEADS && (n_kv_heads > 0 && (n_heads / n_kv_heads) <= hardware::HW_MAX_GQA);` (line 842 fails for 256).
- Effect: `configure_hw_attention` returns at `model.hpp:1895-1899` with "HW-attention not available for this model. Will use SW-only path."; the block `if constexpr (model_shape_is_hwattn_eligible())` (1906) is not compiled; `hw_attn_eligible` stays false (set only at 1951); `compute_operation_uses_hw` (self_attention.hpp:506-514) is false, so `uses_hw = false` and `run_visible_in_software = true` (1502-1503).
- Related limits: `h/libpos.hpp:72` `HW_BAKED_HEAD_SIZE = 128`; `h/pos/hwattention.hpp:775` "Caller is responsible for kv_head_size <= HW_BAKED_HEAD_SIZE"; `hwattention.hpp:795` `TRON_ASSERT(head_size == 128, "shuffle_k_head requires head_size be 128")`.
- The plugin's `force_hw_attn = true` (plugin line 51) and the `kv_slot_candidate` flags have no effect, because the shape gate comes first.
- Log proof: `rt/q35-tp4-1u-p4096__on__rep1.log:190-191`: `hw_attn_params { kv_head_size: 256 n_kv_heads: 4 n_heads: 16 gqa: 4 pre_attn_scalar: 0.0625 hw_slots: 0 }` and "HW-attention not available for this model. Will use SW-only path."

## 7. Tests

### t/t_amx_numerics.cpp (links the real kernels; `add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake ...)`, t/CMakeLists.txt:684)
- Gate test (87-114): `query_scalar_ok` for bf16 / float / fp16 and executor aliases; `eligible<bf16>(128, 4)` true; `(128, 2)` and `(64, 4)` false.
- Packer layout test (116-146): distinct bit patterns `0x3f80u + i`; checks `packed[((step * 16 + dim_pair) * 16 + col) * 2 + j] == q[col * 128 + step * 32 + 2 * dim_pair + j]` for col < 4 and `== 0` for the padding columns. Runs on every host.
- QK band test (148-192): skipped with WARN when `available()` is false. 4 seeds, uniform [-1, 1] rounded to bf16. Compares `qk_rowmajor_128x4` with `dotter<bf16, 128>` per (head, token): `tol = 1e-4 * abs_mass + 1e-6`, `abs_mass` = sum of |q*k| in double.
- PV band test (194-280): fills a real `v_vnni_tensor<64, 128>` through `append_v_row`, weights `exp(u)` with u in [-10, 0]. In double: `ref_rne` (weights rounded to nearest even), `ref_avx` (weights truncated), `acc_slack = 1e-4 * abs_mass + 1e-6`, `envelope = sum |p_rne - p_avx| * |v|`. Requires `|got - ref_rne| <= acc_slack`, `|got - ref_avx| <= envelope + acc_slack`, and `total_rounding_gap > 0`. `o_amx` holds `TILE_ROWS_16 * HEAD_SIZE_128` floats.

### t/t_amx_dispatch_dtype.cpp (fakes)
- Mechanism: link-time replacement by strong definitions. Lines 228-257 define all six entry points of `tron::amx_attn_h128g4` in the test's own translation unit (`available`, `begin_region`, `end_region`, `pack_q_group_128x4`, `qk_rowmajor_128x4`, `weights_times_v_128x4`). `tron` is a static library (`src/tron/CMakeLists.txt:187 add_library(tron STATIC`), and amx_attn.cpp is one member of it (219). The linker extracts an archive member only to resolve an undefined symbol, so the real object is never extracted. No `--wrap`, no weak symbol, no CMake exclusion. File header lines 4-8 state this.
- The fakes are outside `#ifdef TRON_AMX_DISPATCH` (the test case at 259-283 is inside).
- What it drives: the production `apply_page_range<geometry>` on `model<llm<config, executor_t>>` with `head_size = 128, n_heads = 4, n_kv_heads = 1` (72-76), executors host_bf16 / host / host_fp16, full page, 63-token page, repeat call, and `available()` false. It checks the fakes' call counts and the stats tallies (185-216).
- Link rule after Part B: it keeps linking with zero edits if (a) the binary references no symbol that only amx_attn.cpp's object defines, and (b) `available` / `begin_region` / `end_region` keep their qualified names. The binary instantiates only the 128x4 geometry, so the `if constexpr` branches for 256 are discarded and no 256 symbol is referenced. If any referenced AMX symbol is left undefined by the test, the linker extracts the real object and its `amx_attn_h128g4::available()` etc. collide with the fakes (duplicate-definition link error).

### t/t_llama_unit.cpp
- 97-107: `amx_qk_accepts<K>` / `amx_pv_accepts<V>` are `requires` probes on `amx_attn_h128g4::qk_rowmajor_128x4(k, q, s, size_t{0})` and `weights_times_v_128x4(v, weights, size_t{0}, out)`. Compile-time only.
- 509-531: STATIC_REQUIREs that QK takes only the native K view and PV only the packed V view, with aliases built from `PAGE_TOKENS_64` and `HEAD_SIZE_128`.
- 4546-4577: "append_v_row matches the independent packed-V formula" at rows 64, cols 128 only. 1930-1937: "scaled_v supports wide values" covers 256 and 512. 1544: the registry test already uses `attention_geometry{16, kv_geometry{4, 256}}` with scale 0.0625f.

### CI and cost data
- `README.ci.md:586-594`: the CMake CI lane builds with `-DTRON_AMX_DISPATCH=ON` (`.github/workflows/cmake-single-platform.yml:355`); the kernel cases execute only on a Granite Rapids runner and skip with a warning elsewhere. `deb` preset sets the option ON (`CMakePresets.json:68`).
- `bin/slice bench --check` (workflow 358-361) checks `config/test-benchmarks.json`. New cases inside the two existing binaries need no new row. A new test binary needs rows and an entry in `config/tests.core.txt`.

## 8. Concrete minimal change list for 256x4

### Form: second namespace, not templates
Recommendation: add `namespace tron::amx_attn_h256g4` to `amx_attn_iface.hpp` with non-template `_256x4` entry points. Reasons, tied to the call sites:
1. The entry points must be out-of-line functions defined in the one translation unit that has `-mamx-tile -mamx-bf16` (`src/tron/CMakeLists.txt:219-221`); the header has no intrinsics. A header template cannot hold the body.
2. Every existing name states its value (`_128x4`, `HEAD_SIZE_128`, `Q_PACK_ELEMS_2048` with `static_assert(... "the constant's name states its value")`, namespace `h128g4`). A parameterized kernel inside `amx_attn_h128g4` contradicts the namespace name; renaming it touches 8 files.
3. The fakes in t_amx_dispatch_dtype.cpp are plain definitions in `tron::amx_attn_h128g4`. They stay valid untouched. Explicitly instantiated templates would force the fakes to become explicit specializations.
4. `pack_q_group` takes raw `const bf16*`, so the type cannot select the shape. It needs its own name in any case.
5. The call sites are already compile-time gated per geometry (`if constexpr`), so the selection costs one `if constexpr` at 3 calls plus one combined gate.
The one advantage of templates (3 call sites without `if constexpr`, HEAD deduced from the typed K and V views) does not outweigh points 2 to 4. Inside amx_attn.cpp the implementer may still share bodies through a file-local template or helper; the exported symbols stay non-template. Leaving the three 128 bodies byte-for-byte unchanged is the lower-risk choice (their bits were measured in earlier campaigns).

### amx_attn_iface.hpp: new declarations
```cpp
namespace tron::amx_attn_h256g4 {
using amx_attn_h128g4::TILE_ROWS_16;
using amx_attn_h128g4::TILE_ROW_BYTES_64;
using amx_attn_h128g4::PAGE_TOKENS_64;
using amx_attn_h128g4::GROUP_HEADS_4;
using amx_attn_h128g4::query_scalar_ok;
inline constexpr size_t HEAD_SIZE_256 = 256;
inline constexpr size_t Q_PACK_ELEMS_4096 = TILE_ROWS_16 * HEAD_SIZE_256;
static_assert(Q_PACK_ELEMS_4096 == 4096, "the constant's name states its value");
constexpr bool shape_ok(size_t model_head_size, size_t model_kv_mul) noexcept {
  return model_head_size == HEAD_SIZE_256 && model_kv_mul == GROUP_HEADS_4;
}
template <typename query_scalar_t>
constexpr bool eligible(size_t model_head_size, size_t model_kv_mul) noexcept {
  return shape_ok(model_head_size, model_kv_mul) && query_scalar_ok<query_scalar_t>;
}
// packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
//   == q_group[q_head * 256 + step * 32 + 2 * dim_pair + j], step 0..7
// packed: Q_PACK_ELEMS_4096 bf16 (8192 bytes), 64-byte aligned, columns 4..15 zero.
void pack_q_group_256x4(const bf16* q_group, bf16* packed) noexcept;
void qk_rowmajor_256x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_256> k_page,
    const bf16* q_packed, float* s, size_t s_stride_floats) noexcept;
// o MUST hold 16 * 256 fp32 (16384 bytes, 64-byte aligned, row stride 256 floats).
void weights_times_v_256x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_256> v_page,
    const float* exp_rows, size_t row_stride_floats, float* o) noexcept;
}
```
`available()`, `begin_region()`, `end_region()` stay declared once in `amx_attn_h128g4` and keep being called by that name (lines 479, 1536, 1553, 1558 unchanged).

### amx_attn.cpp: new constants and loops
New constants (row strides in bytes): K row 512 (`HEAD_SIZE_256 * sizeof(bf16)`), V pair row 1024 (`2 * HEAD_SIZE_256 * sizeof(bf16)`), O row 1024 (`HEAD_SIZE_256 * sizeof(float)`), PV output groups 4 (`HEAD_SIZE_256 / 64`). Reuse `DIM_STEP_32`, `TILE_FP32S`, `V_PAIR_TOKENS_2`, the tile register numbers, and the transposing store (amx_attn.cpp:186-215).

QK (8 dim steps of 32 into the same 4 accumulator tiles):
```
zero tiles 0..3
for step in 0..7:                                   // 256 / 32
  load Q_TILE_6 <- q_packed + step*16*32, stride 64
  for blk in 0..3 (tiles 4,5,4,5 as today):
    load K tile <- k_rows + blk*16*256 + step*32, stride 512
    tile_dpbf16ps(ACC_blk, K tile, Q_TILE_6)
store ACC_0..3 -> s_transposed + blk*256 floats, stride 64
transpose rows 0..3 -> s[head][token]              // unchanged code
```
Totals: 32 products, 40 loads (8 Q + 32 K), 4 stores.

PV (4 groups of 64 output dims):
```
P[q][0..63] <- cvtne2ps_pbh(exp_rows[q])            // unchanged, rows 4..15 stay zero
for group in 0..3:                                  // 256 / 64
  zero tiles 0..3
  for s in 0..1:                                    // 32 tokens = 16 pair rows
    load P_TILE_4 <- &P[0][s*32], stride 128
    for i in 0..3 (tiles 5,6,5,6 as today):
      load V tile <- v_pairs + s*16*256*2 + (group*4 + i)*32, stride 1024
      tile_dpbf16ps(ACC_i, P_TILE_4, V tile)
  for i in 0..3: store ACC_i -> o + group*64 + i*16, stride 1024
```
Totals: 32 products, 40 loads (8 P + 32 V), 16 stores.

Packer: same triple loop as amx_attn.cpp:133-142 with `step < 8` and `q_head * 256`.

### self_attention.hpp: dispatch edits
1. Slot size (259-261). Size it from the model's kernels so 128-only models keep 4096-byte slots, for example a class-level constant of `self_attention<model>`:
```cpp
static constexpr size_t amx_q_pack_elems = [] {
  size_t elems = amx_attn_h128g4::Q_PACK_ELEMS_2048;
  for (auto const& kernel : plugin::attention_kernels)
    if (amx_attn_h256g4::shape_ok(kernel.geometry.kv.head_size, kernel.geometry.kv_mul()))
      elems = amx_attn_h256g4::Q_PACK_ELEMS_4096;
  return elems;
}();
```
and `bf16 v[amx_q_pack_elems];`. Every plugin has `attention_kernels` (model.hpp:705). Do not size from `model::head_size`: a model can register several kernel geometries (kv_cache.hpp:186-188).
2. Gate (1533-1535, 1741-1743, 1877-1878): `h128g4::eligible<S>(head, mul) || h256g4::eligible<S>(head, mul)`; write it once as a helper (for example two variable templates `amx_shape_128x4<geometry>` / `amx_shape_256x4<geometry>` and their OR) and use it at the three sites.
3. `packed_amx_query` (1690-1694): `if constexpr (256 shape) amx_attn_h256g4::pack_q_group_256x4(q.data + kv_head * geometry.kv_mul() * geometry.kv.head_size, slot); else amx_attn_h128g4::pack_q_group_128x4(...)`. Add a `static_assert` that the slot holds the shape's element count.
4. `apply_dense_amx_page` (1760-1761, 1787-1789): `if constexpr` between `qk_rowmajor_256x4` / `qk_rowmajor_128x4` and between `weights_times_v_256x4` / `weights_times_v_128x4`. Arguments are unchanged; `pg.template k<geometry.kv>` and `v_packed<geometry.kv>` already have the 256 types; `amx_o` already has `TILE_ROWS_16 * operation_head_size` floats.
5. No edit: 479, 1536 (`available`), 1541-1559, 1626-1637, `is_dense_amx_page` (1707-1719), the softmax step, the update, the stats hooks, kv_cache.hpp, v_vnni.hpp code.
6. Comments: iface header lines 13-15, 19-31, 55-67, 91-107; self_attention.hpp 255-258, 1526, 1537-1539, 1681, 1750; v_vnni.hpp 44-50; t/CMakeLists.txt 685-686.

### Buffer sizes for 256x4 (bytes)
packed query slot 8192; `amx_o` 16384; `scratch` 1024; `s_pages` 1024; `s_transposed` 4096; `P` 2048; K page 32768; V page 32768.

### Test edits
- t_amx_numerics.cpp: add 256 versions of all four cases (helper templates on the head size are the smallest form). Gate: `h256g4::eligible<bf16>(256, 4)` true; float / fp16 false; `(256, 2)` and `(128, 4)` false for h256g4; `h128g4::eligible<bf16>(256, 4)` false. Packer: 8 steps, padding columns zero, buffer `Q_PACK_ELEMS_4096`. QK band against `dotter<bf16, 256>` with K fixture 64 x 256. PV band with `v_vnni_tensor<64, 256>`, `v_source_row<256>`, `o_amx[16 * 256]`. Same tolerances.
- t_amx_dispatch_dtype.cpp: no edit is required for linking. To cover the 256 dispatch, make `exercise_page` take the head size, add a config with `.dim = 1024, .n_heads = 4, .n_kv_heads = 1, .head_size = 256, .attention_scale = 0.0625f`, and add fakes for the three `amx_attn_h256g4` entry points (fake pack fills `Q_PACK_ELEMS_4096`, fake PV fills `16 * 256` floats, `probe.q` grows to 1024 floats). All three fakes must be defined in the same commit that references them.
- t_llama_unit.cpp: optional mirror of the probes at 97-107 and 509-531 for the 256 kernels (the 256 K view is accepted by `qk_rowmajor_256x4` and rejected by `qk_rowmajor_128x4`, and the reverse); optional 256-column case of the packed-V formula test (4546).
- No change: t_attn_stats.cpp, config/tests.core.txt, config/test-benchmarks.json (no new binary).

## Files read
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/kernels/amx_attn_iface.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/kernels/amx_attn.cpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/self_attention.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/kv_cache.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/heterogeneous_kv_cache.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/model.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/models/attn_stats.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/tensor/v_vnni.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/tensor/kv_cache_fwd.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/kernels/dotter.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/kernels/expr.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/h/tron/plugins/llama.hpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_amx_numerics.cpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_amx_dispatch_dtype.cpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/t_llama_unit.cpp
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/t/CMakeLists.txt
- /home/jhan/workspace/ai-runs/tron-qwen35-4b/src/tron/CMakeLists.txt
- /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp
- /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/rt/q35-tp4-1u-p4096__on__rep1.log and q35-tp4-8u-p4096__off__rep3.log
- /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/design.txt (section 5.5, 5.6)

Not found: any reference to the six searched names in `ingest/` or `config/`; any build tree or generated plugin header for other models inside the worktree; any existing 256x4 hand-written model config (gemma_2_2b and gemma_2_9b have head 256 with 2 query heads per KV head, llama.hpp:1687-1688).