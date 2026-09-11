# Draft reply to Wade (PR 4265, discussion r3970127694), version 3 with measured numbers

The hash 4b98dc134a is the local commit and changes if it is amended before the push. Source of the numbers: exec/logs/wade-exp.txt (delphi-3bda, 2026-09-09 18:08 UTC).

---

Short version: yes. I will move the test into `t_llama_unit` and delete the standalone binary. Moved in 4b98dc134a. I measured what the define does to the rest of `t_llama_unit` first: no other check aborts, the run time grows by about 2 %, peak memory is unchanged. Numbers at the end.

The move:

- `t/CMakeLists.txt`: `DEFINES _GLIBCXX_ASSERTIONS` on the `t_llama_unit` target. This is libstdc++'s switch for run-time precondition checks (an abort when a library call gets an argument the standard forbids, such as a release memory order on a load). The define is per-target, so libtron stays as built today. libstdc++ documents these checks as "ABI compatible with normal mode" and says the macro "must not cause changes to the linkage names, sizes or layout of types" (GCC wiki, LibstdcxxDebugMode); only `_GLIBCXX_DEBUG` changes container sizes and restricts mixing. The standalone binary already links a checked object against the unchecked library.
- `t/t_llama_unit.cpp`: the `#ifndef _GLIBCXX_ASSERTIONS` / `#error` guard at the top, so a dropped define is a build error rather than a test that compiles but can no longer fail. Plus one case, declared before the existing ones, reusing the file's `assertion_signal` fork helper:

  ```cpp
  // Declared first on purpose. With a wrong memory order, the book
  // constructions in the later cases abort the whole process; this
  // fork-isolated case reports the contract by name before that happens.
  TEST_CASE("log_kv_footprint uses valid atomic memory orders", "[kv_data]") {
    // Any call runs the load under test. One byte stays below the default
    // 1 GiB print granularity, so nothing is logged.
    REQUIRE(assertion_signal([] { log_kv_footprint(1, 0); }) == 0);
  }
  ```

- Delete `t/t_kv_footprint_memorder.cpp`, its `add_catch_test`, and its row in `config/test-benchmarks.json`. Refresh the `t_llama_unit` row for the platform I can measure (`granite_rapids_6962p`, `bin/slice bench --update t_llama_unit`). The other three platform rows keep their values; `bench --check` only requires that a row exists.
- History: two commits (the fix; the test in `t_llama_unit` plus the bench row), so the standalone file never appears.

Why the define reaches the load: `book` is a class template, so every constructor `t_llama_unit` uses is instantiated in `t_llama_unit.cpp` itself. `log_kv_footprint` is always-inline (`TRON(inline)`), so with the define on the target the checked load is compiled into those instantiations. You are right that the existing book cases then detect the bug too: with main's line the process aborts with SIGABRT (the abort signal) at the first book construction. The explicit case is the smallest reproducer and gives the failure a name; it costs four lines. `t_llama_unit` is also in `TEST_INSTALL_TARGETS`, so the check ships with the installed tests; the standalone target did not.

Measured on delphi-3bda (Xeon 6962P, socket 1, `--instance 1,2`), PR head 7a7699b338 with `t_llama_unit.cpp` recompiled under the define and relinked with the recorded link line:

- Other precondition checks that abort: none. All 27 cases pass with the define (120,054 assertions), the same as without it.
- Run time, mean of three runs each, same placement: 6.38 s without the define, 6.51 s with it (+0.13 s, about +2 %; the run-to-run spread without the define was 0.26 s). Peak memory: 655,340 KB in all six runs.
- With main's `kv_cache.hpp` and the define: the whole binary aborts in the second case ("attention operations resolve to typed KV slots") with `atomic_base.h:498: Assertion '__b != memory_order_release' failed`. Run one at a time, 13 of the 27 cases abort. The control build (main's header, no define) passes all 27, so the define is the detector, not the header swap.
- Symbols on this build: 14 `book` constructor instantiations in the test object, 6 in `libtron.a`, none shared; the linker map shows all 14 taken from the test object.
