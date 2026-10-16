---
name: libstdcxx-assertions-memorder-guard
description: "2026-09-08 verified: only -D_GLIBCXX_ASSERTIONS catches the PR 0b release-load UB under tron's clang 19 + libstdc++ (no warning, clang-tidy, TSan, UBSan; identical asm); a per-target DEFINES Catch2 test fails on main / passes with the fix; lefthook regex; cost-data gate"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1e24c926-ae4f-4ee5-aa42-dbf9460dfa15
  modified: 2026-09-08T04:36:34.474Z
---

Question jhan asked 2026-09-08: can a unit test guard the memory_order bug PR 0b fixes
(kv_cache.hpp:454 `last_print_bytes.load(std::memory_order_release)` in `tron::log_kv_footprint`)?

Verified facts (delphi-3bda, tron's nix clang 19.1.7 + libstdc++ 14.3, and Ubuntu clang 19 + libstdc++ 12):
- Wrong and fixed line compile to IDENTICAL instructions (assembly diff on the real header, 1114 lines), so
  no output-observing test can fail. tron's warning set, -Weverything, clang-tidy (all checks), TSan and
  UBSan are all silent. GCC's -Winvalid-memory-model exists but is hidden as a system-header warning.
- `-D_GLIBCXX_ASSERTIONS` aborts at the first bad load (`atomic_base.h:498 ... Assertion '__b !=
  memory_order_release' failed`, exit 134), works with -DNDEBUG -O3, is ABI-neutral (object with the define
  links against libtron.a/libspdlog.a built without it). GCC 14.3 does NOT enable it at -O0 (GCC 15 does).
- `TRON(inline)` = `inline __attribute__((always_inline))` (h/common/attributes.hpp:78), so a Catch2 test
  target with `DEFINES _GLIBCXX_ASSERTIONS` gets its own checked copy: draft t_kv_footprint_memorder.cpp
  (fork child calls `tron::log_kv_footprint(1, 0)`, REQUIRE(sig == 0); `#ifndef _GLIBCXX_ASSERTIONS #error`)
  FAILS on main (`6 == 0`, SIGABRT) and PASSES with e2f22c7a09, built with tron's clang 19 + lld. Call the
  function directly: the book-constructor route is unreliable (linker may keep the library's unchecked copy).
  Put the define on the target, not `#define` in the file (precompiled-header trap).
- lefthook rule (like no-cassert): load regex `\.load\(\s*std::memory_order(_|::)(release|acq_rel)\s*\)`
  hits only kv_cache.hpp:454; store regex must anchor the store's own last argument
  (`\.store\(([^()]|\([^()]*\))*,\s*std::memory_order(_|::)(acquire|consume|acq_rel)\s*\)`), else
  shard.hpp:178/193 false-positive. CI lint runs lefthook over the whole tree -> rule lands with/after PR 0b.
- Gates: a new test binary needs config/test-benchmarks.json entries (bin/slice bench --check). Unmeasured
  (C9): what else fires tree-wide under the define (needs a Debug build + bin/slice run --filter=host).
- Trap: lld-linked binaries built by hand in `nix develop` lack the nix rpath; set LD_LIBRARY_PATH for the
  binary only (a global export breaks sed/grep with GLIBC_2.38 errors).

**Why:** jhan wants regression protection for the UB, and the naive answer ("write a Catch2 test") cannot
fail without the libstdc++ instrument; this note saves re-deriving which guards work under tron's toolchain.

**How to apply:** page PR3879/new-PRs/PR0b/ub-guard.html + evidence in PR0b/ub-guard/ (draft test, scripts,
verification-workflow JSON, chain logs). LANDED 2026-09-08: #4265 head 7a7699b338 (dc5d496d06 test with DEFINES on
the target, 7a7699b338 cost data 0.7 s / 8 MB); the project chain proved pass-on-branch and fail-on-main. Guard B
(lefthook regex) is NOT added; it can only land with or after PR 0b. Trap seen: Catch2's signal handler also fires
inside the forked child (a "SIGABRT" FAILED line at the fork helper), the real assertion is the parent's REQUIRE.
Related: [[pr3879-split-progress]], [[breakup-pr3879-plan]], [[claude-box-tron-build-env]].
