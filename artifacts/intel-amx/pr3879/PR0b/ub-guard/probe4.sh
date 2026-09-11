#!/bin/bash
# (1) assembly diff of probe.cpp with the REAL kv_cache.hpp, old vs fixed, using the recorded compile command;
# (2) relink the old+assertions object with lld (tron's linker) and run it.
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
echo "### (1) -S old vs fixed, real header (flags: recorded rinzler.cpp command, -g dropped so debug metadata does not mask instruction changes)"
R2=$(echo "$REST" | sed 's/ -g / /; s/ -gdwarf-4//; s/ -gz//')
eval "$CXX" -I$T/h "$R2" -S $M/probe.cpp -o $M/probe_old.s 2>/dev/null; echo "old rc=$?"
eval "$CXX" -I$M/fixed -I$T/h "$R2" -S $M/probe.cpp -o $M/probe_fixed.s 2>/dev/null; echo "fixed rc=$?"
if diff -q $M/probe_old.s $M/probe_fixed.s >/dev/null; then echo "IDENTICAL assembly ($(wc -l < $M/probe_old.s) lines)"; else echo "assembly differs; diff (first 20 lines):"; diff $M/probe_old.s $M/probe_fixed.s | head -20; echo "instruction-only diff (strip labels/directives/comments):"; diff <(grep -vE '^\s*[.#]|^[A-Za-z_.$0-9]+:' $M/probe_old.s) <(grep -vE '^\s*[.#]|^[A-Za-z_.$0-9]+:' $M/probe_fixed.s) | head -10; echo "(end)"; fi
echo; echo "### (2) relink probe_old_assert.o with lld and run"
LLD=""; for l in lld-19 lld ld.lld; do command -v $l >/dev/null && { LLD=$l; break; }; done; echo "lld found: ${LLD:-none}"
$CXX -fuse-ld=lld $M/probe_old_assert.o -o $M/probe_old_assert_lld src/tron/libtron.a src/system/libsystem.a _deps/spdlog-build/libspdlog.a -ltbb -lnuma -lpthread -ldl 2>&1 | head -3; echo "link rc=${PIPESTATUS[0]}"
readelf -p .comment $M/probe_old_assert_lld 2>/dev/null | grep -i -m1 lld || echo "(no lld tag in .comment)"
$M/probe_old_assert_lld 2>&1 | head -2; echo "run exit=${PIPESTATUS[0]}"
