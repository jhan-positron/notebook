#!/usr/bin/env bash
# Inner part of wade-exp-20260909.sh (see that header for E1-E4). Runs inside
# `nix develop` (clang++-19, lld-19, ninja on PATH). Arguments: WT X BASE OUT LOGS.
set -u
WT=$1; X=$2; BASE=$3; OUT=$4; LOGS=$5
OUR_CPUS=72-143,216-287
PIN="nice -n10 taskset -c $OUR_CPUS"
cd "$WT" || exit 1
TIMEBIN=/usr/bin/time; [ -x $TIMEBIN ] || TIMEBIN=

# runN <n> <label> <binary> [catch2 args...]: n runs from the repo root (ctest's
# working directory); records rc, wall time, max RSS, Catch2 summary, any
# libstdc++ assertion message.
runN() {
  local n=$1 label=$2 bin=$3; shift 3
  local i rc o sum asrt
  for i in $(seq 1 $n); do
    o=$LOGS/wade-exp-$label-$i.out
    if [ -n "$TIMEBIN" ]; then
      $TIMEBIN -f "TIME %e s RSS %M KB" -o $o.time $PIN timeout -k 30 1200 "$bin" "$@" >$o 2>&1; rc=$?
    else
      local t0=$(date +%s.%N)
      $PIN timeout -k 30 1200 "$bin" "$@" >$o 2>&1; rc=$?
      echo "TIME $(echo "$(date +%s.%N) - $t0" | bc) s RSS ? KB" >$o.time
    fi
    sum=$(grep -E "^(All tests passed|test cases:|assertions:)" $o | tr '\n' ' ' | cut -c1-200)
    asrt=$(grep -h -m1 -E "Assertion .* failed|terminated by signal|SIGABRT" $o $o.time 2>/dev/null | head -1 | cut -c1-200)
    echo "$label run$i rc=$rc $(grep TIME $o.time 2>/dev/null) | ${sum:-<no summary>} | ${asrt:-}" >>"$OUT"
  done
}

echo "--- E1 baseline: binaries as the PR builds them" >>"$OUT"
runN 3 e1-llama gen/t_llama_unit
runN 3 e1-memorder gen/t_kv_footprint_memorder

# Recorded compile and link lines (ninja -t commands does not build).
cd gen
CC_LLAMA=$(ninja -t commands t_llama_unit | grep -F -- "t_llama_unit.cpp.o -c ")
LD_LLAMA=$(ninja -t commands t_llama_unit | tail -1)
CC_MEM=$(ninja -t commands t_kv_footprint_memorder | grep -F -- "t_kv_footprint_memorder.cpp.o -c ")
LD_MEM=$(ninja -t commands t_kv_footprint_memorder | tail -1)
cd ..
{ echo "CC_LLAMA: $CC_LLAMA"; echo "LD_LLAMA: $LD_LLAMA"; echo "CC_MEM: $CC_MEM"; echo "LD_MEM: $LD_MEM"; } >$LOGS/wade-exp-commands.txt

# variant <target> <name> <cc line> <ld line> <flags inserted right after the compiler>
# Compiles the target's one source file into $X/<name>/ and links gen/<target>.<name>
# (same directory as the original, so the $ORIGIN rpath still works).
variant() {
  local tgt=$1 name=$2 cc=$3 ld=$4 extra=$5
  mkdir -p $X/$name
  local obj="t/CMakeFiles/$tgt.dir/$tgt.cpp.o"
  cc=$(printf '%s\n' "$cc" | sed -E "s#(clang\+\+-19) #\1 $extra #; s#-o $obj -c #-o $X/$name/$tgt.cpp.o -c #")
  ld=$(printf '%s\n' "$ld" | sed -E "s#$obj#$X/$name/$tgt.cpp.o#; s#-o $tgt #-o $tgt.$name -Wl,-Map=$X/$name/link.map #; s# && :\$##")
  printf '%s\n' "$cc" >$X/$name/cc.sh; printf '%s\n' "$ld" >$X/$name/ld.sh
  (cd gen && $PIN bash $X/$name/cc.sh) >$X/$name/cc.log 2>&1 || { echo "$name compile FAILED (see $X/$name/cc.log): $(tail -3 $X/$name/cc.log | tr '\n' ' ' | cut -c1-300)" >>"$OUT"; return 1; }
  (cd gen && $PIN bash $X/$name/ld.sh) >$X/$name/ld.log 2>&1 || { echo "$name link FAILED (see $X/$name/ld.log): $(tail -3 $X/$name/ld.log | tr '\n' ' ' | cut -c1-300)" >>"$OUT"; return 1; }
  echo "$name built: gen/$tgt.$name ($(stat -c %s gen/$tgt.$name) bytes); compile warnings: $(grep -c "warning:" $X/$name/cc.log)" >>"$OUT"
}

echo "--- E2 fold cost: t_llama_unit.cpp compiled with -D_GLIBCXX_ASSERTIONS, fixed header" >>"$OUT"
variant t_llama_unit e2 "$CC_LLAMA" "$LD_LLAMA" "-D_GLIBCXX_ASSERTIONS" && runN 3 e2-llama gen/t_llama_unit.e2

echo "--- E3 detection: main's kv_cache.hpp ($BASE, the release load) first on the include path" >>"$OUT"
mkdir -p $X/override/tron/models
git show $BASE:h/tron/models/kv_cache.hpp >$X/override/tron/models/kv_cache.hpp
echo "header diff base vs PR: $(diff $X/override/tron/models/kv_cache.hpp h/tron/models/kv_cache.hpp | grep '^[<>]' | sed 's/^ *//' | cut -c1-110 | tr '\n' ' ')" >>"$OUT"
if variant t_llama_unit e3 "$CC_LLAMA" "$LD_LLAMA" "-I$X/override -D_GLIBCXX_ASSERTIONS"; then
  runN 1 e3-llama-all gen/t_llama_unit.e3
  gen/t_llama_unit.e3 --list-tests -r xml >$X/e3-list.xml 2>/dev/null
  python3 - "$X/e3-list.xml" >$X/e3-names.txt <<'EOF'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
for tc in root.iter('TestCase'):
    n = tc.find('Name')
    if n is not None and n.text: print(n.text)
EOF
  echo "E3 per-case runs ($(wc -l <$X/e3-names.txt) cases; rc=134 means the child of timeout died of SIGABRT):" >>"$OUT"
  i=0
  while IFS= read -r name; do
    i=$((i+1)); o=$LOGS/wade-exp-e3-case-$i.out
    spec=$(printf '%s' "$name" | sed 's/[][,\\*]/\\&/g')
    $PIN timeout -k 10 600 gen/t_llama_unit.e3 "$spec" >$o 2>&1; rc=$?
    a=$(grep -m1 -oE "Assertion '[^']*' failed" $o)
    echo "  e3 case $i rc=$rc ${a:-} | $name" >>"$OUT"
  done <$X/e3-names.txt
fi
variant t_llama_unit e3ctl "$CC_LLAMA" "$LD_LLAMA" "-I$X/override" && runN 1 e3ctl-llama gen/t_llama_unit.e3ctl
variant t_kv_footprint_memorder e3 "$CC_MEM" "$LD_MEM" "-I$X/override" && runN 1 e3-memorder gen/t_kv_footprint_memorder.e3

echo "--- E4 symbols: book constructor instantiations (COMDAT copies) and who provides them" >>"$OUT"
if [ -f $X/e2/t_llama_unit.cpp.o ]; then
  nm -C $X/e2/t_llama_unit.cpp.o | grep -E " [WwTtVv] tron::book<.*>::book\(" | sed -E 's/^[0-9a-f]+ //' | sort -u >$X/e2.ctors
  nm -C gen/src/tron/libtron.a | grep -E " [WwTtVv] tron::book<.*>::book\(" | sed -E 's/^[0-9a-f]+ //' | sort -u >$X/lib.ctors
  comm -12 $X/e2.ctors $X/lib.ctors >$X/both.ctors
  echo "book ctor instantiations: t_llama_unit.cpp.o(e2)=$(wc -l <$X/e2.ctors) libtron.a=$(wc -l <$X/lib.ctors) in both=$(wc -l <$X/both.ctors)" >>"$OUT"
  short() { sed -E 's/^[WwTtVv] //; s/tron::book<([0-9]+)ul, ([0-9]+)ul, ([0-9]+)ul, ([0-9]+)ul,.*>::book\((.*)\)$/book<\1,\2,\3,\4> \5/; s/ .*adopt_t.*$/ adopt/; s/ unsigned long.*$/ public/' | sort -u; }
  echo "  test object: $(short <$X/e2.ctors | tr '\n' ';')" >>"$OUT"
  echo "  libtron.a:   $(short <$X/lib.ctors | tr '\n' ';')" >>"$OUT"
  echo "  in both:     $(short <$X/both.ctors | tr '\n' ';')" >>"$OUT"
  echo "  link map (e2): input files providing .text._ZN4tron4bookI...C[12]E sections:" >>"$OUT"
  grep -E "\.text\._ZN4tron4bookI.*C[12]E" $X/e2/link.map | awk '{print $NF}' | sed -E 's/:\(.*$//' | sort | uniq -c | sed 's/^/    /' >>"$OUT"
  cp $X/e2.ctors $X/lib.ctors $X/both.ctors $LOGS/ 2>/dev/null; for f in e2 lib both; do mv $LOGS/$f.ctors $LOGS/wade-exp-$f.ctors 2>/dev/null; done
fi
echo "--- inner done $(date -u +%FT%TZ)" >>"$OUT"
