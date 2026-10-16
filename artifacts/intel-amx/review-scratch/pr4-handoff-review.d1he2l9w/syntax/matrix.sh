#!/bin/bash
# usage: W=<worktree> [P=<dir with lcheck-vnni.sh>] bash matrix.sh <label>  -> runs the 22-cell lcheck matrix on W, writes $P/out/<label>/*.log and summary.txt (cell, error count, first error)
P=${P:-$(cd "$(dirname "$0")" && pwd)}   # directory of this script: holds lcheck-vnni.sh and out/
W=${W:?W=<worktree to check> is required}
L=$1; O=$P/out/$L; mkdir -p $O
run() { # tree vnni file
  local T=$1 V=$2 F=$3 S=/tmp/pr4-handoff-review.d1he2l9w/syntax/lcheck.sh
  [ "$V" = on ] && S=$P/lcheck-vnni.sh
  local N="$T-vnni$V-$(basename $F .cpp)"
  ERRLIM=0 timeout 900 $S $T $F $W > $O/$N.log 2>&1; local rc=$?
  # rc is the compiler's exit status (0 = the translation unit parsed and instantiated). A failed launch
  # (missing uvx, missing mirror, timeout) gives rc != 0 with no 'error:' line, and must not count as clean.
  echo "$N rc=$rc errors=$(grep -c 'error:' $O/$N.log) first=$(grep -m1 -E 'error:|rror|not found|No such' $O/$N.log | sed "s#$W/##" | cut -c1-160)" >> $O/summary.txt
}
export -f run; export P W O
rm -f $O/summary.txt
{
for T in gen gen-amxoff; do for V in off on; do
  for F in t/t_llama_unit.cpp t/t_k_vnni_layout.cpp t/t_amx_dispatch_dtype.cpp t/t_amx_numerics.cpp t/heterogeneous_scheduler_compile.cpp; do
    echo "$T $V $F"; done; done; done
echo "gen off src/tron/kernels/amx_attn.cpp"; echo "gen on src/tron/kernels/amx_attn.cpp"
} | xargs -P 8 -L 1 bash -c 'run $0 $1 $2'
sort $O/summary.txt
# Verdict: every expected cell present, every rc=0, every errors=0. Exit 1 otherwise (callers must check $?).
EXPECTED=${EXPECTED:-22}
n=$(wc -l < $O/summary.txt); bad=$(grep -v -c ' rc=0 errors=0 ' $O/summary.txt)
if [ "$n" -eq "$EXPECTED" ] && [ "$bad" -eq 0 ]; then echo "MATRIX OK: $n cells, rc=0 and errors=0 everywhere"; exit 0; else echo "MATRIX FAILED: $n of $EXPECTED cells, $bad cells with rc!=0 or errors!=0"; exit 1; fi
