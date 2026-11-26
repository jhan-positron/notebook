#!/usr/bin/env bash
# gdn-impl-20261121, E4B check, part 2: do the Gemma 4 E4B generation tests of the tron repository pass at the
# Part B head on an AMX machine?
# Runs ON delphi-3b35, on OUR half (SYSTEM_CONFIG="--instance 1,2"; FPGA cards 90/93/b9/bc). No root.
#
# Why: Part B makes the 35 sliding-window attention layers of E4B take AMX kernels (e4b-check.sh shows that). The
# four tests t_generate_ingest_1_gemma_4_e4b_* feed a fixed text through the model and compare the scores of the
# next token with stored scores, inside a tolerance. They are the tests of the repository that reach those layers.
# How: every test runs twice, once with AMX on and once with TRON_AMX_DISABLE=1 (AMX off at run time). The second
# run tells whether a failure comes from the AMX kernels. A skipped test case counts as "not run", never as passed.
# Words: tron = the inference program; AMX = Intel tile-matrix instructions; Part B = the AMX attention kernels
# for 256-wide heads.
# Usage (on 3b35): [TAG=e4b] [TESTS='<test> ...'] bash e4b-tests.sh
# Output: exec/results/gdn-e4b-20261122/tests/<test>__<arm>.txt (full output), tests/summary.txt, load/test-*.txt
# (load snapshot before every run); marker e4b-tests.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-e4b-20261122
RES=$EXEC/results/$NAME
OUT=$RES/tests
TAG=${TAG:-e4b}
WT=/var/tmp/jhan/b35-gdn-$TAG
TESTS=${TESTS:-"t_generate_ingest_1_gemma_4_e4b_fpga t_generate_ingest_1_gemma_4_e4b_tp2_fpga t_generate_ingest_1_gemma_4_e4b_tp4_fpga t_generate_ingest_1_gemma_4_e4b_permuted_fpga"}
ARMS_ALL=$'on|
off|TRON_AMX_DISABLE=1'
ARMS=${ARMS:-"on off"}
TMO=${TMO:-1200}
OUR_CARDS="0000:90:00.0 0000:93:00.0 0000:b9:00.0 0000:bc:00.0"
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
mkdir -p "$OUT" "$RES/load"
rm -f "$RES/e4b-tests.done"
exec {RUN_LOCK_FD}>"/var/tmp/jhan/$NAME.run.lock"
flock -n "$RUN_LOCK_FD" || { echo "$(ts) another run holds /var/tmp/jhan/$NAME.run.lock"; exit 1; }
arm_field() { local line; line=$(grep -m1 "^$1|" <<<"$ARMS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed huge page file $f (unmapped, ours)"
  done
  return 0
}
{
  echo "# Gemma 4 E4B generation tests at $(git -C "$WT" rev-parse --short=10 HEAD) on delphi-3b35, started $(ts)"
  echo "# command per run: SYSTEM_CONFIG=\"--instance 1,2\" [switch] ./gen/<test> --skip-benchmarks"
  echo "# format: test | arm | result | load before the run"
  for t in $TESTS; do
    for arm in $ARMS; do
      f=$OUT/${t}__${arm}.txt
      [ -x "$WT/gen/$t" ] || { echo "$t | $arm | missing binary |"; continue; }
      # load snapshot (10 s sample); the run is refused when our half is not free
      snap=$RES/load/test-${t}__${arm}.txt
      bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$snap" 2>&1
      s0=$(awk '$1=="socket0"{print $3}' "$snap"); s1=$(awk '$1=="socket1"{print $3}' "$snap")
      ours=$(awk '$1=="our-app-cores"{print $3}' "$snap")
      load="socket0_busy=${s0:-?} socket1_busy=${s1:-?} our_app_cores_busy=${ours:-?} loadavg=$(cut -d' ' -f1-3 /proc/loadavg)"
      open=""
      for c in $OUR_CARDS; do [ "$(cat /sys/bus/pci/devices/$c/enable 2>/dev/null)" = 1 ] && open="$open $c"; done
      [ -n "$open" ] && { echo "$t | $arm | REFUSED: one of our cards is already open:$open | $load"; continue; }
      case ${ours%\%} in ''|*[!0-9.]*) ;; *) awk -v b="${ours%\%}" 'BEGIN{exit !(b > 5.0)}' && { echo "$t | $arm | REFUSED: our app cores are ${ours} busy (limit 5 %) | $load"; continue; } ;; esac
      ( cd "$WT" && exec {RUN_LOCK_FD}>&- && env -u TRON_AMX_DISABLE -u USE_HW_ATTN SYSTEM_CONFIG="--instance 1,2" $(arm_field "$arm" 2) \
          timeout -k 60 "$TMO" "./gen/$t" --skip-benchmarks ) >"$f" 2>&1
      rc=$?
      remove_our_slice_files >>"$f" 2>&1
      line=$(grep -aE "^(All tests passed|test cases:|assertions:)" "$f" | tr -s ' ' | tr '\n' ' ')
      skips=$(grep -ac "SKIPPED" "$f")
      if [ $rc -eq 0 ] && [ -n "$line" ]; then result="rc=0 [$line] skipped-lines=$skips"; else result="FAILED rc=$rc [$line] skipped-lines=$skips"; fi
      echo "$t | $arm | $result | $load"
      sleep 3
    done
  done
} 2>&1 | tee "$OUT/summary.txt"
echo "done $(ts)" >"$RES/e4b-tests.done"
