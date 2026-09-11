// Guards the atomic memory-order preconditions of tron::log_kv_footprint
// (h/tron/models/kv_cache.hpp). A release-ordered atomic load is undefined
// behaviour ([atomics.types.operations]); with tron's compiler it produces the
// same instructions as a valid load, so the only detector is libstdc++'s
// precondition check, enabled by _GLIBCXX_ASSERTIONS on THIS target
// (add_catch_test ... DEFINES _GLIBCXX_ASSERTIONS). log_kv_footprint is
// always-inline, so this translation unit gets its own checked copy.
#ifndef _GLIBCXX_ASSERTIONS
#error "t_kv_footprint_memorder needs _GLIBCXX_ASSERTIONS (add_catch_test DEFINES); without it the test cannot fail"
#endif
#include <signal.h>
#include <unistd.h>

#include <catch2/catch_test_macros.hpp>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/wait.h>

#include "tron/models/kv_cache.hpp"

// Fork a child that calls fn(), return the signal that killed it (0 if exited
// normally). Same pattern as t_heap_guard.cpp: a failed libstdc++ assertion
// calls std::abort() (SIGABRT).
static int fork_and_get_signal(void (*fn)()) {
  pid_t pid = fork();
  REQUIRE(pid >= 0);
  if (pid == 0) {
    prctl(PR_SET_DUMPABLE, 0, 0, 0, 0);
    fn();
    _exit(0);
  }
  int status = 0;
  waitpid(pid, &status, 0);
  if (WIFSIGNALED(status)) return WTERMSIG(status);
  return 0;
}

TEST_CASE("log_kv_footprint satisfies the atomic memory-order preconditions",
    "[kv_cache][memory_order]") {
  // 1 byte is below the print granularity (1 GiB by default): the load on the
  // throttle line executes and nothing is logged.
  int sig = fork_and_get_signal([] { tron::log_kv_footprint(1, 0); });
  REQUIRE(sig == 0);
}
