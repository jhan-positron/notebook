#!/usr/bin/env bash
# gdn-20261120: ONE runtron run on OUR half of delphi-3b35 (FPGA cards 90/93/b9/bc, socket 1), with the load
# snapshot the machine rule asks for taken first. runtron = tron's command-line tool; tron = the inference program.
#
# The machine is shared: other users hold the first half of the cards. So every run
#   - uses SYSTEM_CONFIG="--instance 1,2" (our half; tron derives cards, CPUs, NUMA node and huge page files from it),
#   - refuses to start when one of our four cards is already open or when our CPUs are busy,
#   - removes its own unmapped huge page files afterwards.
# It needs no root. It never touches a process of another user.
#
# Inputs (environment):
#   RUN      run name, used for the log file name (required), e.g. q35-tp4-8u-p1024__on__rep1
#   MODEL    tron model slug with executor suffix (default ingested-qwen-3.5-4b-tp4)
#   USERS    number of concurrent users (default 1); PROMPT prompt length in tokens (default 1024)
#   LEN      generated tokens per user (default 256)
#   ARMENV   extra environment for the run, e.g. "TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1" (default "TRON_ATTN_STATS=1")
#   EXTRA    extra runtron arguments (default none), e.g. "--trace-gen /var/tmp/jhan/traces/x.perfetto-trace --trace-passes 1-40"
#   TAG      build tag: the binary is /var/tmp/jhan/b35-gdn-$TAG/gen/runtron (default base)
#   TMO      timeout in seconds (default 2400); NAME results folder name (default gdn-20261120)
# Outputs: exec/results/$NAME/rt/$RUN.log (full runtron output), exec/results/$NAME/load/$RUN.txt (load snapshot),
#          one block appended to exec/results/$NAME/rt-results.txt. Exit code 0 only when the run printed its TPS line.
set -u
RUN=${RUN:?RUN=<run name> is required}
MODEL=${MODEL:-ingested-qwen-3.5-4b-tp4}
USERS=${USERS:-1}
PROMPT=${PROMPT:-1024}
LEN=${LEN:-256}
ARMENV=${ARMENV-TRON_ATTN_STATS=1}
EXTRA=${EXTRA:-}
TAG=${TAG:-base}
TMO=${TMO:-2400}
NAME=${NAME:-gdn-20261120}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/$NAME
WT=/var/tmp/jhan/b35-gdn-$TAG
BIN=$WT/gen/runtron
OUR_CARDS="0000:90:00.0 0000:93:00.0 0000:b9:00.0 0000:bc:00.0"
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only (here: $(hostname))"; exit 1; }
[ -x "$BIN" ] || { echo "$BIN missing"; exit 1; }
mkdir -p "$RES/rt" "$RES/load"
rlog=$RES/rt/$RUN.log
grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) $RUN already done"; exit 0; }
exec {RUN_LOCK_FD}>"/var/tmp/jhan/$NAME.run.lock"
flock -n "$RUN_LOCK_FD" || { echo "$(ts) another run-one.sh holds /var/tmp/jhan/$NAME.run.lock"; exit 1; }
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed huge page file $f (unmapped, ours)"
  done
  return 0
}
# 1. load snapshot (10 s sample). The run is refused when our half is not free.
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/load/$RUN.txt" 2>&1
s1=$(awk '$1=="socket1"{print $3}' "$RES/load/$RUN.txt"); s0=$(awk '$1=="socket0"{print $3}' "$RES/load/$RUN.txt")
ours=$(awk '$1=="our-app-cores"{print $3}' "$RES/load/$RUN.txt")
open=""
for c in $OUR_CARDS; do [ "$(cat /sys/bus/pci/devices/$c/enable 2>/dev/null)" = 1 ] && open="$open $c"; done
loadline="load: socket0_busy=${s0:-?} socket1_busy=${s1:-?} our_app_cores_busy=${ours:-?} our_cards_open=[${open# }] loadavg=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free_node1=$(cat /sys/devices/system/node/node1/hugepages/hugepages-1048576kB/free_hugepages 2>/dev/null)"
hdr="### run=$RUN model=$MODEL users=$USERS prompt=$PROMPT len=$LEN armenv=[$ARMENV] extra=[$EXTRA] bin=$BIN tip=$(git -C "$WT" rev-parse --short HEAD) $(ts)"
{ echo "$hdr"; echo "$loadline"; } >>"$RES/rt-results.txt"
if [ -n "$open" ]; then echo "RUN-REFUSED one of our cards is already open:$open" | tee -a "$RES/rt-results.txt"; exit 3; fi
case ${ours%\%} in ''|*[!0-9.]*) ;; *) awk -v b="${ours%\%}" 'BEGIN{exit !(b > 5.0)}' && { echo "RUN-REFUSED our app cores are ${ours} busy (limit 5 %)" | tee -a "$RES/rt-results.txt"; exit 3; } ;; esac
# 2. a runtron killed before its unmount leaves its FUSE stats mount; the next run at the same instance would fail
for m in "$WT"/stats/instance-*; do
  [ -d "$m" ] && mountpoint -q "$m" && ! pgrep -u "$(id -u)" -f "^$BIN " >/dev/null && { fusermount3 -u "$m" 2>/dev/null || fusermount -u "$m" 2>/dev/null; echo "$(ts) unmounted a stale FUSE mount $m"; }
done
# 3. the run
t0=$(date +%s)
( cd "$WT" && exec {RUN_LOCK_FD}>&- && env -u TRON_AMX_DISABLE -u USE_HW_ATTN SYSTEM_CONFIG="--instance 1,2" $ARMENV TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
    timeout -k 60 "$TMO" "$BIN" stream-generate-text -m "$MODEL" -o --prompt-length "$PROMPT" -l "$LEN" -u "$USERS" --dont-stop $EXTRA ) >"$rlog.attempt" 2>&1
rc=$?
wall=$(( $(date +%s) - t0 ))
remove_our_slice_files
res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s|s TTFT and" "$rlog.attempt" 2>/dev/null | cut -c1-400)
if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
  { echo "RUN-FAILED rc=$rc wall=${wall}s (full output: $rlog.attempt)"; echo "$res"; grep -i -m6 -E "error|abort|assert|exception|terminate|not found|unknown model|fatal" "$rlog.attempt" | cut -c1-300; } | tee -a "$RES/rt-results.txt"
  exit 1
fi
mv "$rlog.attempt" "$rlog"
{ echo "$res"; echo "RUN-OK rc=$rc wall=${wall}s attn_stats_lines=$(grep -c '^\[attn-stats\]' "$rlog")"; } | tee -a "$RES/rt-results.txt"
exit 0
