#!/bin/bash
# Syntax-only matrix over the PR-1 scratch tree (probe HEAD 76a0160b72 = L+R+G+B).
# Cells: tree gen (TRON_AMX_DISPATCH on) / gen-amxoff (off) x TRON_K_VNNI on/off x TU.
# usage: W=<worktree> [O=<output dir>] bash run.sh   (38 cells; lcheck-vnni.sh is taken from ../probe/ next to this script)
D=$(cd "$(dirname "$0")" && pwd)
W=${W:?W=<worktree to check> is required}; O=${O:-$D/out}; mkdir -p $O; rm -f $O/summary.txt
echo "checked commit: $(git -C "$W" rev-parse HEAD 2>/dev/null) worktree: $W" > $O/commit.txt
run() {
  local T=$1 V=$2 F=$3 SC=/home/jhan/workspace/ai-runs/lcheck/lcheck.sh
  [ "$V" = on ] && SC=$D/../probe/lcheck-vnni.sh
  local N="$T-vnni$V-$(basename $F .cpp)"
  ERRLIM=0 timeout 900 $SC $T $F $W > $O/$N.log 2>&1; local rc=$?
  echo "$N rc=$rc errors=$(grep -c 'error:' $O/$N.log) warnings=$(grep -c 'warning:' $O/$N.log) first=$(grep -m1 'error:' $O/$N.log | sed "s#$W/##" | cut -c1-160)" >> $O/summary.txt
}
export -f run; export D W O
{
for T in gen gen-amxoff; do for V in off on; do
  for F in t/t_llama_unit.cpp t/t_k_vnni_layout.cpp t/t_amx_dispatch_dtype.cpp t/t_amx_numerics.cpp t/heterogeneous_scheduler_compile.cpp src/tron/scheduler/full.cpp src/tron/gof.cpp t/t_gof_dma.cpp t/t_kv_oom_subcases.cpp; do
    echo "$T $V $F"; done; done; done
echo "gen off src/tron/kernels/amx_attn.cpp"; echo "gen on src/tron/kernels/amx_attn.cpp"
} | xargs -P 6 -L 1 bash -c 'run $0 $1 $2'
sort $O/summary.txt
EXPECTED=${EXPECTED:-38}
n=$(wc -l < $O/summary.txt); bad=$(grep -v -c ' rc=0 errors=0 ' $O/summary.txt)
if [ "$n" -eq "$EXPECTED" ] && [ "$bad" -eq 0 ]; then echo "MATRIX OK: $n cells, rc=0 and errors=0 everywhere"; exit 0; else echo "MATRIX FAILED: $n of $EXPECTED cells, $bad cells with rc!=0 or errors!=0"; exit 1; fi
