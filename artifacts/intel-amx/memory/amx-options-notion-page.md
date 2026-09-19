---
name: amx-options-notion-page
description: 2026-09-16 Notion sub-page "AMX and VNNI options (PR 3879, PR 4424)" under Daily notes (34bd132d3cfd801eb0f5d3d98c582e6b): page id 3ddd132d3cfd81ec8b97f46aec9ebbe9; source status/amx-options-page/page.md; fact-checked by wf_9f6ce61c-76e (60 findings applied); verified code fact: the AMX gate does not test hardware attention
metadata:
  type: project
---

Page: https://app.notion.com/p/3ddd132d3cfd81ec8b97f46aec9ebbe9 (parent "Daily notes", sibling of
"Intel AMX" 3bfd132d3cfd80b2bcc4e05bc623291f). Skeleton from jhan: build time (CMake based, nix based),
run time (environment variables, execution logic: model shape 128 x 4); brief first, details after.
Local source: VNNIed-K-in-place/status/amx-options-page/page.md (v1 = page.v1.md; fact-check results
verify-page.json; sources pr3879-body.md, amx_software_attention.md (notebook), pr-body.final5.md).
Line citations are at tron ff680c8020.

Verified code facts worth reusing (all at ff680c8020):
- Options: CMakeLists.txt:48-49; AMX flags only on kernels/amx_attn.cpp + PUBLIC define
  (src/tron/CMakeLists.txt:193-198); TRON_K_VNNI FATAL_ERROR without AMX + PUBLIC define (209-214);
  #error guards self_attention.hpp:30-35 / kv_cache.hpp:35-39; NO preset and NO nix file sets them
  (nix/cmake-tron-test-build.nix:79-103 fixed flag list); deb preset -> shipped packages have no AMX.
- TRON_AMX_DISABLE exact "1", probed once at the FIRST ATTENTION DISPATCH (not process start):
  amx_attn.cpp:60-74 (CPUID 7.0 EDX bits 22/24, XCR0 bits 17-18, arch_prctl), 78-88 (static cache).
- USE_HW_ATTN (hw_attn_config.cpp:19-33): unset -> hardware attention only for plugins with
  force_hw_attn (only generated plugins, TronCpp.hs:232) AND only if FPGA devices present
  (model.hpp:1443-1447, else "no POS devices available" -> software); <=0/unparsable -> off for all;
  N>0 -> on for every eligible model from engagement point = N rounded UP to k*128-1, floor 127
  (POS_PER_PAGE=128, MIN_TOK_IDX_FOR_HWATTN=127, libpos.hpp:77,90).
- THE AMX GATE HAS NO HARDWARE-ATTENTION TERM: run_visible_in_software = sliding_window <
  illegal || !uses_hw (self_attention.hpp:1220-1221); under hw attention query_visible =
  sw_required (1535-1536); amx_on = eligible && available() (1236-1239); gate = packed Q &&
  is_dense_amx_page (1546-1551). Scheduler marks queries below the engagement point and the causal
  tail as software-required (full.hpp:1936-1965) -> dense pages of those pairs take the AMX path
  even with USE_HW_ATTN unset. Code reading only; a counter probe (TRON_PAGE_SHARE_COUNTERS or a
  call counter on apply_dense_amx_page) would confirm. The notebook doc's "hardware attention not
  affected" is about FPGA-scored pairs only.
- TRON_K_VNNI_BLOCK/STRIPE switches: added 0b54de7a10, removed ab94854999 (rebased hashes).

**How to apply:** when writing about AMX/VNNI runtime behaviour, never say "AMX needs USE_HW_ATTN=0";
say "a pair that software attention scores". Re-fetch the Notion page before editing (cache trap,
[[notion-questions-keep-verbatim]]). Related: [[vnnied-k-in-place-project]], [[pr3879-split-progress]],
[[amx-ci-coverage-facts]], [[runtron-determinism-recipe]].
