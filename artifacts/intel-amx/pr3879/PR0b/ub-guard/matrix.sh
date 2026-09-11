#!/bin/bash
# Compile the minimal throttle copy (repro.cpp) with one compiler under several guard settings.
CXX=$1; shift
cd "$(dirname "$0")"
echo "compiler: $CXX"; $CXX --version 2>&1 | head -1
echo "std lib include dirs:"; $CXX -v -E -x c++ /dev/null 2>&1 | grep -m2 -E '/c\+\+/(v1|[0-9]+)$|/c\+\+/[0-9.]+$'
run() { name=$1; shift; echo "### $name"; echo "\$ $CXX $*"; rm -f bin_$name; $CXX "$@" -o bin_$name repro.cpp 2>&1 | grep -v '^$' | head -8; if [ -x bin_$name ]; then ./bin_$name 2>&1 | head -4; echo "exit=${PIPESTATUS[0]}"; fi; echo; }
TRON="-std=gnu++23 -O2 -g -DNDEBUG -Wall -Wpedantic -Wextra -Wno-shadow -O3"
run tron_flags $TRON
run tron_flags_Weverything $TRON -Weverything -Wno-c++98-compat -Wno-c++98-compat-pedantic -Wno-unsafe-buffer-usage -Wno-global-constructors
run O0_Wall -std=gnu++23 -O0 -Wall -Wextra
run glibcxx_assert_OLD $TRON -D_GLIBCXX_ASSERTIONS
run glibcxx_assert_FIXED $TRON -D_GLIBCXX_ASSERTIONS -DORDER=std::memory_order_relaxed
run tsan_OLD -std=gnu++23 -O1 -g -fsanitize=thread
run ubsan_OLD -std=gnu++23 -O1 -g -fsanitize=undefined
if echo '#include <atomic>' | $CXX -stdlib=libc++ -x c++ -fsyntax-only - 2>/dev/null; then run libcxx_OLD -std=gnu++23 -O2 -stdlib=libc++ -Wall; else echo "### libc++: not available with this compiler"; echo; fi
echo "### codegen old vs fixed (tron flags), function throttled:"
$CXX $TRON -S -o old.s repro.cpp 2>/dev/null; $CXX $TRON -S -DORDER=std::memory_order_relaxed -o new.s repro.cpp 2>/dev/null
if diff -q old.s new.s >/dev/null; then echo "IDENTICAL assembly"; else echo "differs:"; diff old.s new.s | head -8; fi
awk '/^_Z9throttledll:/,/ret/' old.s | grep -v -E '^\s*\.|^#' | head -14
if command -v clang-tidy-19 >/dev/null; then echo; echo "### clang-tidy-19 -checks=*"; clang-tidy-19 -checks='*' repro.cpp -- -std=gnu++23 2>&1 | grep -i -E 'memory.?order|atomic' | head -6; echo "(end clang-tidy)"; fi
