# Machine code of the software K scoring loop: PR 4956 head vs PR 5047 head

Date: 2026-10-21. Host: claude-box (no nix, no cmake). Compiler: zig clang 19.1.7 with the
mirrored nix headers from /home/jhan/workspace/ai-runs/lcheck.

## Short version

The head (PR 5047, ade89a9d9c) scores a 64-token KV page in two passes instead of one, and
this costs 5 more instructions per scored token (97 instead of 92, +5.4 %) while the vector
work stays identical and the number of load operations falls from 20 to 9 per token. The
measured kill-switch prefill loss (+2.247 s) is 5.2 % of the 43.5 s that the software scoring
path costs above the AMX path in the same campaign, which matches the +5.4 % instruction
count if the loop is limited by instruction issue and retirement. Nothing else in the hot
path changed: no call is left un-inlined, the per-visit stack traffic is the same, and the PV
loop is byte-for-byte the same.

## Words used here

- base: worktree /home/jhan/workspace/ai-runs/tron-split-pr1 at a5697f86d3 (PR 4956 head).
- head: worktree /home/jhan/workspace/ai-runs/tron-pr5047 at ade89a9d9c (PR 5047 head).
- TU (translation unit): one .cpp file compiled to one object file.
- apply_page_range: the function in h/tron/models/self_attention.hpp that scores one KV
  page (64 tokens) against one query and updates the running softmax state.
- dotter: the helper in h/tron/kernels/dotter.hpp that holds one 128-element bf16 query
  head in four 512-bit registers and computes its dot product with one 128-element K row.
- vdpbf16ps: the AVX-512 instruction that multiplies 32 bf16 pairs and accumulates into 16
  floats. One dotter call issues 4 of them. One token visit (4 query heads) issues 16.
- kill-switch cell: TRON_AMX_DISABLE=1, so every K token takes this software scoring loop.
- live mask: a 64-bit integer with one bit per token of the page that must be scored.
- s_pages: the 4 x 64 float array on the stack that receives the scores for one page.
- visit: one (query token, KV page, KV head group) call into the scoring code.
- zmm: a 512-bit vector register. There are 32 (zmm0 to zmm31).
- uop (micro-operation): the unit of work the CPU back end executes. One instruction with a
  memory operand is one fused uop that occupies both a load port and a vector port.

## 1. What was compiled

### 1.1 The translation unit

flags.txt in /home/jhan/workspace/ai-runs/lcheck lists only one production (src/tron) TU:
src/tron/kernels/amx_attn.cpp. It does not instantiate the llama model. The runtron binary
gets the llama attention path from a file that CMake generates at configure time:
gen/src/tron/model_llama_3p1_8b.cpp. Its content is six lines and is written verbatim by
src/tron/CMakeLists.txt lines 116 to 123 (head worktree):

```
#define TRON_MODEL_ARCHITECTURE_FILTER
#define TRON_MODEL_ARCHITECTURE_llama_3p1_8b
#include "tron/plugins/llama.hpp"
#define TRON_MODEL_PLUGIN_HEADER_INCLUDED
#include "tron/models/load.hpp"
#include "models_x.hpp"
```

I reproduced that file at ksroot/tu/model_llama_3p1_8b.cpp and compiled it for both
worktrees. It instantiates all 7 llama-3.1-8b executors (host, perm_tp1, perm_tp2, perm_tp4,
tp1, tp2, tp4); the measured cell is tp2. I also compiled a tp2-only subset
(ksroot/tu/model_llama_3p1_8b_tp2only.cpp, same includes, only the three tp2
instantiations). The tp2 apply_page_range code in the full TU object and in the tp2-only
object is the same instruction sequence (5 differing lines out of 2166 and 2151, all
relocation annotations). So the fallback TU t/t_llama_unit.cpp was NOT needed.

### 1.2 The flags

The generated model TU is not in flags.txt. I used the flags line of the only production
TU present (gen src/tron/kernels/amx_attn.cpp), because src/tron/CMakeLists.txt gives the
model objects the same option set (target tron_model_compile_config: -O3 -DTRON_IGNORE_NAN
-DTRON_IGNORE_FTZ, the AVX-512 and AMX -m flags, -DTRON_AMX_DISPATCH) plus -flto=thin.
Differences from the 3bda build, in order of importance:

- No -flto=thin: the 3bda link step re-optimizes with ThinLTO. Cross-TU inlining can change
  code around apply_page_range, but apply_page_range and everything it calls live in headers
  included by this TU, so the loop itself has all its callees visible already.
- Debug flags removed (-g, -gdwarf-4, -gz): they do not change code.
- -fcolor-diagnostics and -fmacro-prefix-map removed: no code effect.
- The generated headers (model-definitions.i) come from the lcheck mirror taken on
  2026-09-24 from /var/tmp/jhan/tron-issue4525; the llama_3p1_8b rows are present.
- TRON_K_VNNI is undefined (not on the amx_attn.cpp line, and CMake default OFF). This
  matches the kill-switch cell (option-off binaries).

Exact flags used (after cleanup):
`-DSPDLOG_COMPILED_LIB -DTRON_AMX_DISPATCH -DTRON_AVX512_ENABLED -DYAML_CPP_STATIC_DEFINE
-O2 -DNDEBUG -std=gnu++23 -fPIC -Wno-deprecated-declarations -fno-omit-frame-pointer
-ffunction-sections -fdata-sections -Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed -msse4.2
-mavx -mbmi2 -mfma -mavx2 -mclflushopt -ftree-vectorize -funroll-loops -mavx512f -mavx512dq
-mavx512bw -mavx512vl -mavx512vbmi2 -mavx512vpopcntdq -mavx512vp2intersect -mavx512bf16 -O3
-DTRON_IGNORE_NAN -DTRON_IGNORE_FTZ -mamx-tile -mamx-bf16 -mavx512f -mavx512bw -mavx512vl
-mavx512dq -mavx512bf16 -mavx2 -mfma` (the last -O wins: -O3).

Script: ksroot/objcompile.sh (copy of lcheck.sh with the worktree as argument and
`-c -o <out>` in place of `-fsyntax-only`). Runner: ksroot/run_all.sh. Compile times: full
TU 237 s (base) and 239 s (head), tp2-only 77 s and 78 s. Logs: ksroot/log/. Both
compiles ended with 0 warnings and 0 errors.

### 1.3 Files

| file | content |
|---|---|
| ksroot/obj/{base,head}/model_llama_3p1_8b.o | full production TU object, 32.9 MB each |
| ksroot/obj/{base,head}/model_llama_3p1_8b_tp2only.o | tp2-only object, 7.07 MB each |
| ksroot/obj/{base,head}/model_llama_3p1_8b_tp2only.dis | objdump -d --no-show-raw-insn of the tp2-only object |
| ksroot/obj/{base,head}/apply_page_range.short.dis | the tp2 apply_page_range function only, jump labels shortened to `<+offset>` |
| ksroot/obj/{base,head}/apply_page_range.fullTU.short.dis | the same function taken from the full TU object |
| ksroot/obj/base/model_llama_3p1_8b.dis | full-TU disassembly of the base (140 MB) |

Files directly under ksroot/obj/ (base.asm, base_llama_unit.o, ocompile.sh, count.py and
similar) were written by another task that shares this directory. They are not mine.

## 2. Symbols

The scoring loop is inlined into one function at both heads. No `score_k`, `dotter` or
`k_vnni` symbol exists in either object (nm --defined-only), so page::score_k at the head
and the dotter calls at both heads are fully inlined (TRON(inline) expands to
`__attribute__((always_inline))`, h/common/attributes.hpp:78).

Mangled name of the tp2 apply_page_range (same at both heads; it is a weak symbol):

```
_ZN4tron14self_attentionINS_5modelINS_3llmIXtlNS_17llm_configurationELNS_10model_typeE0ELm4096ELm14336ELm32ELm32ELm8ELm128256ELm128ELf3db504f3ELm1ELm1ELm0ELNS_12rope_scalingE1EEENS_17make_llm_executorILb0ENS_8hardware16tp2_min1k_tensorENS7_7btensorENS7_7dtensorEEEEEEEE5stateINSD_5stateELm32EE16apply_page_rangeIXtlNS_18attention_geometryELm32EtlNS_11kv_geometryELm8ELm128EEEENS_14indexed_vectorINS_12token_job_idENS7_9dmatensorINS_4bf16ELm4096EJEEEEESt6vectorINS_7page_idESaISS_EEEEvRKSR_ISM_SaISM_EERKNS_30attention_operation_descriptorERT0_mmmRKT1_NS_15work_estimate_tERKNS_6mask_tILm4096EEEbbmm
```

Demangled: `tron::self_attention<model<llm<llama_3p1_8b config, make_llm_executor<false,
hardware::tp2_min1k_tensor, ...>>>::state<..., 32>::apply_page_range<attention_geometry{32,
kv_geometry{8, 128}}, indexed_vector<token_job_id, dmatensor<bf16, 4096>>, vector<page_id>>`.

Whole-function size: base 2166 instructions (12406 bytes), head 2151 instructions (12323
bytes). Both contain 32 vdpbf16ps: 16 in the K scoring loop and 16 in two copies of the PV
loop.

## 3. The scoring loop, side by side

Counts are per scored token (one token of one page against the 4 query heads of one KV
head), taken by hand from the listings in section 4, along the path for a visible,
in-window token with no range-hint advance.

| item | base (a5697f86d3) | head (ade89a9d9c) |
|---|---|---|
| loop structure | one pass: select the token, then score it, in the same iteration | pass 1 selects tokens into a 64-bit live mask, pass 2 walks the set bits (tzcnt + blsr) and scores |
| instructions per token | 92 | 97 (23 in pass 1 + 74 in pass 2) |
| vdpbf16ps per token | 16 | 16 |
| other vector uops per token (reduction + store) | 4 x (9 + 1) = 40 | 40 |
| vxorps zero idioms per token | 8 | 8 |
| load uops per token | 20: the K row is read 16 times as vdpbf16ps memory operands (4 rows x 4 heads, 1024 bytes of L1 reads for a 256-byte row) + 4 scalar loads (page end, q position, window, token counter) | 9: 4 vmovaps load the K row once into zmm16-zmm19 + 5 scalar loads |
| K row kept in registers across the 4 heads | no (re-read from L1 per head) | yes (zmm16-19) |
| Q (4 heads x 4 zmm) kept in registers across the page | yes (zmm0-15, loaded once per visit) | yes (zmm0-15, loaded once per visit, after pass 1, only if the mask is non-zero) |
| stores per token | 5: 4 vmovss scores to s_pages + 1 store of the token counter at 0x78(%rsp) | 5: 4 vmovss + 1 store of the token counter at 0x60(%rsp) |
| loop-carried scalar chain | inc %r8 (1 cycle) | lea/and on the mask then tzcnt (est. 4 cycles) |
| unrolling across tokens | none (one token per iteration) | none |
| inner 4-head loop | fully unrolled | fully unrolled |
| calls inside the loop | 0 | 0 |
| bounds check per token | cmp $0x40,%r8 / jae (index < 64) | none (index comes from tzcnt) |

Per-visit work outside the loop (same at both heads):

- s_pages fill with -inf: 16 stores of 64 bytes (base 0x1442 to 0x14b2, head 0x146a to
  0x14e2). 1 KB of stack writes per visit.
- Q load: 16 vmovdqa64 / vmovaps of 64 bytes straight from the q tensor (base 0x1507 to
  0x157f, head 0x19f9 to 0x1a70). No stack copy of the dotter array at either head.
- K block lookup (slot to storage offset, two multiplications by magic constants): base
  0x1810 to 0x18bf, done lazily on the first scored token; head 0x193c to 0x19e4, done after
  pass 1 when the mask is non-zero. Same instruction count within 3.

The head's +5 instructions per token are: tzcnt, mov, shl (index to byte offset) and the
lea/and pair of the blsr idiom in pass 2, plus the bts in pass 1, minus the base's bounds
check pair and index shift. The vector work is identical.

## 4. Annotated excerpts

Addresses are offsets inside apply_page_range of the tp2-only object. The full-TU object has
the same instruction sequence.

### 4.1 Base: one-pass loop (0x15e9 to 0x1a9e)

```
15e9: mov    %r14,%r13            ; loop head: i += 1, i < end ?
15ec: inc    %r8
15ef: cmp    %rdi,%r8
15f2: jae    1abf                  ; page done
15f8: lea    (%r8,%r10,1),%r9      ; kv_idx = page.lo + i
15fc: cmp    0x8(%r13),%r9         ; kv_idx >= range_hint->tok_hi ?
1600: jae    1610                  ;   (range advance, not on the steady path)
1602: mov    %r13,%r14
1605: test   $0x1,%dl              ; query_visible ?
1608: je     15c0                  ;   skip to next range
160a: jmp    17e0
...
17e0: mov    0x30(%rsp),%rdx       ; sliding-window test
17e5: add    %r8d,%edx
17e8: mov    %ecx,%r9d
17eb: sub    %edx,%r9d
17ee: mov    $0x1,%dl
17f0: cmp    0x84(%rsp),%r9d
17f8: jge    15e9                  ; outside window: next token
17fe: test   %r11,%r11             ; keys.valid() ?
1801: je     1810                  ;   (lazy K block lookup, once per page)
...
18c5: cmp    $0x40,%r8             ; bounds check i < 64
18c9: jae    2d5f
18cf: mov    %r8,%r9
18d2: shl    $0x8,%r9              ; byte offset of K row = i * 256
18d6: vxorps %xmm16,%xmm16,%xmm16
18dc: vdpbf16ps (%r11,%r9,1),%zmm0,%zmm16      ; head 0: K row read from memory, 4 times
18e3: vxorps %xmm17,%xmm17,%xmm17
18e9: vdpbf16ps 0x40(%r11,%r9,1),%zmm1,%zmm17
18f1: vdpbf16ps 0x80(%r11,%r9,1),%zmm2,%zmm16
18f9: vdpbf16ps 0xc0(%r11,%r9,1),%zmm3,%zmm17
1901: vaddps %zmm17,%zmm16,%zmm16              ; 9-instruction horizontal reduction
1907: vextractf64x4 $0x1,%zmm16,%ymm17
190e: vaddps %zmm17,%zmm16,%zmm16
1914: vextractf32x4 $0x1,%ymm16,%xmm17
191b: vaddps %xmm17,%xmm16,%xmm16
1921: vshufpd $0x1,%xmm16,%xmm16,%xmm17
1928: vaddps %xmm17,%xmm16,%xmm16
192e: vmovshdup %xmm16,%xmm17
1934: vaddss %xmm17,%xmm16,%xmm16
193a: vmovss %xmm16,0x980(%rsp,%r8,4)          ; s_pages[0][i]
1945: ... same 16 instructions for head 1 with zmm4-7, store to 0xa80(%rsp,%r8,4)
19b4: ... head 2 with zmm8-11, store to 0xb80(%rsp,%r8,4)
1a23: ... head 3 with zmm12-15 (the K row is read from memory a 4th time)
1a4e: mov    0x78(%rsp),%rsi       ; relevant_k_tokens++ in memory
1a53: inc    %esi
1a55: mov    %rsi,0x78(%rsp)
...
1a93: vmovss %xmm16,0xc80(%rsp,%r8,4)
1a9e: jmp    15e9
```

### 4.2 Head: pass 1, token selection into the live mask (0x155a to 0x179e)

```
155a: mov    %r11,%rsi            ; loop head: i += 1, i < end ?
155d: inc    %r9
1560: cmp    %r8,%r9
1563: jae    1919                  ; selection done -> go to pass 2
1569: lea    (%r9,%r10,1),%rbx     ; kv_idx = page.lo + i
156d: cmp    0x8(%rsi),%rbx        ; kv_idx >= range_hint->tok_hi ?
1571: jae    1590                  ;   (range advance, not on the steady path)
1573: mov    %rsi,%r11
1576: test   $0x1,%r15b            ; query_visible ?
157a: je     1530
157c: jmp    1770
...
1770: mov    0xb0(%rsp),%rcx       ; sliding-window test
1778: add    %r9d,%ecx
177b: mov    0x28(%rsp),%edx
177f: sub    %ecx,%edx
1781: mov    $0x1,%r15b
1784: cmp    0x6c(%rsp),%edx
1788: jge    155a
178e: mov    0x60(%rsp),%rcx       ; relevant_k_tokens++ in memory
1793: inc    %ecx
1795: mov    %rcx,0x60(%rsp)
179a: bts    %r9,%rdi              ; live |= 1 << i
179e: jmp    155a
```

### 4.3 Head: pass 2, score the set bits (0x1919 to 0x1c50)

```
1919: mov    %rsi,0x120(%rsp)
1921: test   %rdi,%rdi             ; live == 0 ? skip everything
...
1936: je     1c56
193c: ... K block lookup (slot -> storage offset), 0x193c to 0x19e4
19f9: vmovaps (%rdx,%rcx,1),%zmm0  ; Q: 4 heads x 4 zmm, loaded once per visit
...
1a70: vmovaps 0x3c0(%rdx,%rcx,1),%zmm15
1a80: tzcnt  %rdi,%rcx             ; i = index of lowest set bit
1a85: mov    %ecx,%edx
1a87: shl    $0x8,%edx             ; byte offset = i * 256
1a8a: vmovaps (%rax,%rdx,1),%zmm19 ; K row loaded ONCE into zmm16-19
1a91: vmovaps 0x40(%rax,%rdx,1),%zmm18
1a99: vmovaps 0x80(%rax,%rdx,1),%zmm17
1aa1: vmovaps 0xc0(%rax,%rdx,1),%zmm16
1aa9: vxorps %xmm20,%xmm20,%xmm20
1aaf: vdpbf16ps %zmm19,%zmm0,%zmm20   ; head 0, register-to-register
1ab5: vxorps %xmm21,%xmm21,%xmm21
1abb: vdpbf16ps %zmm18,%zmm1,%zmm21
1ac1: vdpbf16ps %zmm17,%zmm2,%zmm20
1ac7: vdpbf16ps %zmm16,%zmm3,%zmm21
1acd: vaddps ... 9-instruction reduction, identical to the base
1b06: vmovss %xmm20,0x980(%rsp,%rcx,4)   ; s_pages[0][i]
1b11: ... head 1 (zmm4-7), store to 0xa80(%rsp,%rcx,4)
1b79: ... head 2 (zmm8-11), store to 0xb80
1be1: ... head 3 (zmm12-15), store to 0xc80
1c49: lea    -0x1(%rdi),%rcx       ; live &= live - 1 (clear lowest bit)
1c4d: and    %rcx,%rdi
1c50: jne    1a80
```

### 4.4 The PV loop is unchanged

Both objects hold two copies of a 24-instruction loop with 8 vdpbf16ps (base 0x2070 to
0x2101 and 0x2440 to 0x24d1, head 0x21e0 to 0x2271 and 0x25b0 to 0x2641). It packs two
scores per iteration into one broadcast register and multiplies them against two V rows
(8 accumulators of 16 floats = 128 dims). The instruction sequences are identical.

## 5. Other code touched by PR 5047

- save_k_impl (model.hpp, the K store at prefill and decode): 670 instructions at the base,
  645 at the head. The diff is register renaming and one movslq; no new call, no new loop.
  It runs once per saved token, not once per (query, page) visit, so it cannot carry a
  percent-level prefill change.
- full.hpp lines 2748 to 2756: the FPGA K row provider now always copies the row into
  `dest` (get_k_row) instead of returning a pointer into the page. The measured cells use
  CPU attention, so this code does not run there. It would matter for FPGA-attention cells.
- The AMX gate in apply_page_range: apply_dense_amx_page now returns bool and the
  `!k_vnni::layout_on` compile-time guard moved into try_score_k_amx. Under the kill switch
  amx_q_packed is null and the gate short-circuits before any of this at both heads.

## 6. Hypotheses the machine code supports or refutes

H1 (supported): the two-pass structure adds 5 instructions per scored token (+5.4 %). The
campaign gives a direct scale for this: the kill-switch prefill (78.793 s) exceeds the
AMX-on prefill (35.258 s) by 43.5 s, and that difference is the cost of the software QK
path (the PV path and the rest of the forward pass are common). +2.247 s is 5.2 % of
43.5 s. The two percentages match if the loop is limited by instruction issue and
retirement rather than by the vector ports. The vector-port model gives 52 vector uops per
token on 2 ports = 26 cycles (est.), the issue model gives 97 instructions / 6 per cycle =
16 cycles (est.). Under the vector-port model the +5 instructions cost nothing and the match
would be a coincidence. Under the issue model they cost +5.4 %. Which limit holds is a
measurement question (section 7).

H2 (refuted): "the head reads K more times". The opposite is true: the head loads the
256-byte K row once (4 vmovaps), the base reads it four times through vdpbf16ps memory
operands (16 load uops). Load-port pressure falls from 20 to 9 uops per token.

H3 (refuted): "score_k or the dotter is no longer inlined". No such symbol exists in either
object, and there are 0 calls inside both scoring loops.

H4 (refuted): "the head spills the dotter array or Q to the stack". Both keep Q in
zmm0-15 across the page, both load it straight from the q tensor, 16 loads per visit.

H5 (refuted): "the s_pages fill or the per-visit stack traffic grew". Both write 16 x 64
bytes of -inf per visit and both keep relevant_k_tokens in memory (3 instructions per
token).

H6 (open): in the base, the first touch of each K row happens inside the selection
iteration, so the hardware prefetcher sees the K stream while the scalar select logic runs.
In the head, pass 1 touches no K memory, and pass 2 issues the K loads in a 74-instruction
loop whose address depends on a 4-cycle (est.) tzcnt chain. If the K page (16 KB) comes
from L2 or L3 rather than L1, the head exposes more of that latency per page. The listing
cannot settle this.

H7 (not testable here): ThinLTO on 3bda could inline differently around the function.
The loop body is header code with all callees visible, so the loop itself should be the
same, but the final binary was not inspected.

## 7. What would settle it

On delphi-3bda, kill-switch cell, prefill phase only, both binaries, attention worker
threads: `perf stat -e cycles,instructions,uops_dispatched.port_0,uops_dispatched.port_5,
uops_dispatched.port_2_3_10,mem_load_retired.l2_miss,mem_load_retired.l1_miss`. If
instructions rise about 5 % and cycles rise about the same with the port_0 + port_5 counts
unchanged, H1 holds. If L1 or L2 miss counts rise per instruction, H6 holds. A 20-line
microbenchmark that calls apply_page_range on a dense 64-token page in a loop
(t/t_llama_unit.cpp already builds the page) would give the same answer without the
whole-machine lease.
