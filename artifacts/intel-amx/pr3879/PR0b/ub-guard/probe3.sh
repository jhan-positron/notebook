#!/bin/bash
# Compile probe.cpp with the FRESH compile command recorded in the PR2 worktree's compile_commands.json
# (same base a80b102c18, fresh perfetto v57.2 fetch), but with the PR 1 tree's headers prepended (-I$T/h),
# so the 2-argument log_kv_footprint of main is what gets compiled. Shadow dir "fixed" carries the one-line fix.
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
echo "compiler: $CXX"; echo "perfetto -I in fresh command: $(echo "$REST" | grep -o '[^ ]*perfetto[^ ]*' | head -1)"
echo "headers tree: $T at $(git -C $T rev-parse --short=10 HEAD); line 454: $(sed -n 454p $T/h/tron/models/kv_cache.hpp | tr -s ' ')"
build() { name=$1; shift; echo; echo "### $name  (prepended: $*)"; rm -f $M/probe_$name.o $M/probe_$name
  eval "$CXX" "$@" -I$T/h "$REST" -c $M/probe.cpp -o $M/probe_$name.o 2> $M/probe_$name.err; rc=$?
  echo "compile rc=$rc, diagnostics: $(grep -c -E 'warning:|error:' $M/probe_$name.err)"; grep -m3 'error:' $M/probe_$name.err | sed 's/\x1b\[[0-9;]*m//g'; [ $rc -ne 0 ] && return
  $CXX $M/probe_$name.o -o $M/probe_$name src/tron/libtron.a src/system/libsystem.a _deps/spdlog-build/libspdlog.a $(ls _deps/perfetto-build/*.a 2>/dev/null) -ltbb -lnuma -lpthread -ldl 2> $M/probe_$name.link.err; rc=$?
  echo "link rc=$rc"; grep -m3 -E 'undefined reference|error:' $M/probe_$name.link.err | sed 's/\x1b\[[0-9;]*m//g'
  if [ -x $M/probe_$name ]; then $M/probe_$name 2>&1 | head -4; echo "run exit=${PIPESTATUS[0]}"; fi; }
build old_noassert
build old_assert -D_GLIBCXX_ASSERTIONS
build fixed_assert -D_GLIBCXX_ASSERTIONS -I$M/fixed
