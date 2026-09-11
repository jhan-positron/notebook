# Claims to verify: can a test guard the memory_order bug fixed by PR 0b?

## Context (established facts)

- Bug: `h/tron/models/kv_cache.hpp:454` on main a80b102c18 (same text at origin/main b6f09db0d2 and at
  branch jhan-amx-p0 fcc78573b0): `last_print_bytes.load(std::memory_order_release)` inside
  `tron::log_kv_footprint(int64_t delta_bytes, int64_t delta_books)` (kv_cache.hpp:441-462), a throttled
  "KV cache footprint" log line. The C++ standard ([atomics.types.operations]) gives `atomic<T>::load` the
  precondition that the order is neither `memory_order::release` nor `memory_order::acq_rel`, so the call
  is undefined behaviour. The store two lines later keeps release order.
- Fix: PR 0b = commit e2f22c7a09 on branch `jhan-kv-footprint-memorder` (draft PR positron-ai/tron#4265):
  the load becomes `std::memory_order_relaxed`. One line.
- Callers of `log_kv_footprint` (main): `book` constructors at kv_cache.hpp:692 and :901, the `book`
  destructor at :696. Every KV book creation and destruction calls it.
- Toolchain tron builds with (compile_commands.json of ~/workspace/tron-amx, and the nix store on
  delphi-3bda): clang 19.1.7 via the nix wrapper
  `/nix/store/nzk8s2vc3k10mp4xcimvhq7r6w6kiwjv-clang19-wrappers/bin/clang++-19`, using GCC 14.3.0's
  libstdc++ (`/nix/store/kzq78n13l8w24jn8bx4djj79k5j717f1-gcc-14.3.0/include/c++/14.3.0`). Flags for
  src/rinzler.cpp: `-std=gnu++23 -O2 -g -DNDEBUG -Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed
  -Wno-deprecated-declarations ... -O3` plus AVX-512 -m flags. No `-Werror`. `--rtlib=compiler-rt`.
- Build presets (CMakePresets.json): `native` = RelWithDebInfo (the CI lane, `.github/workflows/
  cmake-single-platform.yml:365`), `asan`/`tsan`/`coverage` = Debug (manual; `coverage` runs weekly,
  `cpp-coverage.yml` cron Saturday 05:00 UTC). Sanitizer flags: CMakeLists.txt:575-586 (options ASAN, TSAN,
  MSAN, UBSAN at lines 39-42). Warning flags: CMakeLists.txt:606-609. No `_GLIBCXX_ASSERTIONS` or
  `_GLIBCXX_DEBUG` in any CMake file.
- Pre-commit hooks: `lefthook.yml` has grep-style rules (e.g. `no-cassert`: fail if any header includes
  `<cassert>`), clang-format, whitespace.
- Memory-order usage in h/ src/ t/: relaxed 431, acquire 133, release 104, acq_rel 32 occurrences. The
  only load with release/acq_rel order is kv_cache.hpp:454. A naive regex for invalid store orders
  matched h/tron/shard.hpp:178 and :193, but those stores use release; the match came from the
  `word.load(std::memory_order_acquire)` inside the store's value argument (false positive).
- Tests: `add_catch_test(...)` in t/CMakeLists.txt:109 registers Catch2 tests (NAME, LIBRARIES,
  PROPERTIES LABELS ...). `t_llama_unit` (t/CMakeLists.txt:582, LIBRARIES tron pos_fake, LABELS fake, needs
  model references) has try_create cases at t/t_llama_unit.cpp:1181-1196. 17 test files include
  kv_cache.hpp or create books (t_kv_*, t_memory_pressure*, t_concurrency_*, t_llama_unit, t_system, ...).

## Experiments (files in this directory)

`repro.cpp` = verbatim copy of the throttle (static atomic, load with ORDER, release store); `matrix.sh`
compiles it under several settings; `probe.cpp` includes the REAL `tron/models/kv_cache.hpp` and calls
`tron::log_kv_footprint` twice; `probe3.sh` compiles it with the exact recorded compile command of
rinzler.cpp from a fresh build directory (same base a80b102c18), PR 1 headers prepended, shadow dir
`fixed/` holding kv_cache.hpp with only line 454 changed to relaxed. All runs on delphi-3bda unless noted.

### matrix-nix.txt (tron's nix clang 19.1.7 + libstdc++ 14.3.0)
| row | flags | compile diagnostics | run |
|---|---|---|---|
| tron_flags | `-std=gnu++23 -O2 -g -DNDEBUG -Wall -Wpedantic -Wextra -Wno-shadow -O3` | none | throttled=0, exit 0 |
| tron_flags_Weverything | same + `-Weverything` (minus c++98-compat, unsafe-buffer-usage, global-constructors) | none about atomics | exit 0 |
| O0_Wall | `-O0 -Wall -Wextra` | none | exit 0 |
| glibcxx_assert_OLD | tron flags + `-D_GLIBCXX_ASSERTIONS` | none | `atomic_base.h:498: ... load(memory_order) ...: Assertion '__b != memory_order_release' failed.` exit 134 |
| glibcxx_assert_FIXED | + `-DORDER=std::memory_order_relaxed` | none | exit 0 |
| tsan_OLD | `-O1 -g -fsanitize=thread` | none | exit 0, no report |
| ubsan_OLD | `-O1 -g -fsanitize=undefined` | none | exit 0, no report |
| libcxx_OLD | `-stdlib=libc++` | link error: no libc++ in the toolchain | n/a |
| codegen | `-S` old vs fixed | differ only in `#DEBUG_VALUE: load:__m <- 3` vs `<- 0` and DWARF bytes; instruction sequence of `throttled()` identical (plain `movq` load) | |

### matrix-sysclang.txt (Ubuntu clang 19.1.7 + libstdc++ 12 on delphi-3bda): same outcomes row by row
(assertion at atomic_base.h:485).

### probe3 (real header, tron toolchain, run 2026-09-08 03:57 UTC)
```
compiler: /nix/store/nzk8s2vc3k10mp4xcimvhq7r6w6kiwjv-clang19-wrappers/bin/clang++-19
headers tree: /home/jhan/workspace/tron-amx at fcc78573b0; line 454: ... load(std::memory_order_release) ...
### old_noassert    compile rc=0, diagnostics: 0   link rc=0
[info] KV cache footprint: 2.00 GB in 1 books / probe: both calls returned / run exit=0
### old_assert (-D_GLIBCXX_ASSERTIONS)   compile rc=0, diagnostics: 0   link rc=0
.../gcc-14.3.0/include/c++/14.3.0/bits/atomic_base.h:498: __int_type std::__atomic_base<long>::load(memory_order) const [_ITp = long]: Assertion '__b != memory_order_release' failed.
run exit=134
### fixed_assert (-D_GLIBCXX_ASSERTIONS -I fixed/)   compile rc=0, diagnostics: 0   link rc=0
[info] KV cache footprint: 2.00 GB in 1 books / probe: both calls returned / run exit=0
```

### host g++ 11.4 (Ubuntu 22.04, this container), repro.cpp
- `-O2 -Wall -Wextra -Wpedantic` and `-O0`: no diagnostic.
- `-O2 -Wall -Wsystem-headers`: `atomic_base.h:488:31: warning: invalid memory model for '__atomic_load'
  [-Winvalid-memory-model]` (hidden by default because the location is inside a system header).
- `-D_GLIBCXX_ASSERTIONS`: old aborts (exit 134), fixed runs.
- `-fsanitize=thread` (GCC libtsan, ASLR disabled): `FATAL: ThreadSanitizer CHECK failed:
  tsan_interface_atomic.cpp:223 "((IsLoadOrder(mo))) != (0)"`.
- `-fsanitize=undefined`: silent.
- `-O2 -S` old vs fixed: same instructions, one `movq` scheduled 3 lines apart.

## Claims (verify or refute each)

- C1. No behavioural unit test can detect this bug: with tron's compiler the old and the fixed line compile
  to the same instructions, so any Catch2 assertion on program outputs passes on both versions.
- C2. tron's compiler emits no diagnostic for the bad load at any warning level and any -O level, because
  libstdc++ passes the order through a function parameter (`__atomic_load_n(&_M_i, int(__m))`), so clang's
  `-Watomic-memory-ordering` never sees a constant at the builtin call. GCC's `-Winvalid-memory-model`
  would fire after inlining but is suppressed as a system-header warning; tron requires clang anyway.
- C3. Under clang, TSan and UBSan do not detect it: clang lowers a load whose order is release to a
  monotonic (relaxed) load in IR before sanitizer instrumentation, and UBSan has no memory-order check.
  (GCC's libtsan runtime does check `IsLoadOrder`, which is why the host g++ TSan run failed; irrelevant to
  tron, which builds with clang.)
- C4. `-D_GLIBCXX_ASSERTIONS` turns the bug into a hard failure at the first call, via libstdc++'s
  `__glibcxx_assert(__b != memory_order_release)` in `__atomic_base::load` (GCC 14.3 atomic_base.h:498;
  GCC 12 :485; GCC 11 :485). It works with `-DNDEBUG` present (independent macro) and with -O3. Verified on
  the real header with tron's toolchain (probe3).
- C5. `_GLIBCXX_ASSERTIONS` does not change the libstdc++ ABI or container layouts (unlike
  `_GLIBCXX_DEBUG`), so it can be turned on for the tron targets without rebuilding or mismatching
  prebuilt static dependencies; its cost is extra precondition and bounds checks, acceptable in Debug or
  sanitizer builds, not wanted in the production RelWithDebInfo build.
- C6. Because `book` construction and destruction call `log_kv_footprint`, the existing tests that create
  a KV book would have failed under an assertions build on the old code with no new test written. A small
  dedicated Catch2 test (construct one book, or call `log_kv_footprint` directly) documents the intent and
  runs without model files, but the detection mechanism is the define, not the test's own assertions.
- C7. The cheapest guard for this exact pattern is a lefthook pre-commit grep rule, like `no-cassert`,
  that fails on `.load(` with `memory_order_release` or `memory_order_acq_rel` as its argument, and on
  `.store(` whose own order argument is acquire, consume or acq_rel. Today the only hit is kv_cache.hpp:454.
  Limits: it only catches literal spellings; orders passed through variables or wrappers escape it.
- C8. Where the define belongs: a CMake option (default OFF) enabled in the asan/tsan/coverage presets or
  in a CI lane. Today CI has no Debug lane on pull requests; the weekly coverage lane is the only Debug
  build that runs tests.
- C9. Insufficient data: whether other pre-existing precondition violations in tron or its dependencies
  would fire under `_GLIBCXX_ASSERTIONS`. The measurement is a full build plus the host test set with the
  define on main; not run because delphi-3bda was executing the nightly CI (lease busy, load 127) and a
  full build is not light work.

## Addendum (2026-09-08 04:0x UTC)
- clang-tidy 19.1.7 from tron's nix dev shell, `-checks='*'` on repro.cpp: no diagnostic about the memory
  order or the atomic (only unrelated style checks such as llvmlibc-restrict-system-libc-headers). So
  clang-tidy offers no check for this pattern either.
- The repo does not use `_GLIBCXX_ASSERTIONS` or `_GLIBCXX_DEBUG` anywhere (grep over the tree excluding
  gen/ and lib/); the only hardening-related lines are CMakeLists.txt:365-371 (disable _FORTIFY_SOURCE for
  some targets because of a clang 19 issue). Debug builds only add `-O0` (src/tron/CMakeLists.txt:259) and
  `CMAKE_CXX_FLAGS_DEBUG_INIT "-O0 -g3 -ggdb3 -gcolumn-info -gembed-source"` (CMakeLists.txt:79).
