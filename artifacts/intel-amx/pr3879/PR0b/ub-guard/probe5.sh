#!/bin/bash
# Build the proposed Catch2 test t_kv_footprint_memorder.cpp with tron's recorded compile command
# (clang 19 + libstdc++ 14.3, lld), against the PR 1 tree's headers (old line) and the shadow "fixed" copy.
set -u
T=/home/jhan/workspace/tron-amx; M=/var/tmp/jhan/memorder; P=/var/tmp/jhan/tron-split-PR2-on
cd $P/gen
CMD=$(python3 - <<'PY'
import json,shlex
cc=json.load(open('compile_commands.json'))
for e in cc:
    if e['file'].endswith('src/rinzler.cpp'):
        toks=shlex.split(e.get('command') or ' '.join(e['arguments']))
        out=[];i=0
        while i<len(toks):
            t=toks[i]
            if t=='-o': i+=2; continue
            if t.endswith('src/rinzler.cpp') or t=='-c': i+=1; continue
            out.append(t); i+=1
        print(shlex.join(out)); break
PY
)
CXX=${CMD%% *}; REST=${CMD#* }
C2INC="-I_deps/catch2-src/src -I_deps/catch2-build/generated-includes"
C2LIB="_deps/catch2-build/src/libCatch2Main.a _deps/catch2-build/src/libCatch2.a"
echo "catch2 present: $(ls _deps/catch2-src/src/catch2/catch_test_macros.hpp _deps/catch2-build/generated-includes/catch2/catch_user_config.hpp $C2LIB 2>&1 | grep -c -v 'No such')/4 files"
echo "headers tree: $T at $(git -C $T rev-parse --short=10 HEAD); line 454: $(sed -n 454p $T/h/tron/models/kv_cache.hpp | tr -s ' ')"
build() { name=$1; shift; echo; echo "### $name  (prepended: $*)"; rm -f $M/t_$name.o $M/t_$name
  eval "$CXX" "$@" -I$T/h $C2INC "$REST" -c $M/t_kv_footprint_memorder.cpp -o $M/t_$name.o 2> $M/t_$name.err; rc=$?
  echo "compile rc=$rc, diagnostics: $(grep -c -E 'warning:|error:' $M/t_$name.err)"; grep -m2 'error:' $M/t_$name.err | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200; [ $rc -ne 0 ] && return
  $CXX -fuse-ld=lld $M/t_$name.o -o $M/t_$name $C2LIB src/tron/libtron.a src/system/libsystem.a _deps/spdlog-build/libspdlog.a -ltbb -lnuma -lpthread -ldl 2> $M/t_$name.link.err; rc=$?
  echo "link rc=$rc (lld)"; grep -m3 -E 'undefined reference|error:' $M/t_$name.link.err | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200
  if [ -x $M/t_$name ]; then $M/t_$name 2>&1 | grep -v '^\s*$' | tail -8; echo "catch2 exit=${PIPESTATUS[0]}"; fi; }
build nodefine_OLD
build assert_OLD   -D_GLIBCXX_ASSERTIONS
build assert_FIXED -D_GLIBCXX_ASSERTIONS -I$M/fixed
