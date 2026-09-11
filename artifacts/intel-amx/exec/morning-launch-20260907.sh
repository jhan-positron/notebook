#!/usr/bin/env bash
# Start the pieces of jhan's plan of 2026-09-07 on delphi-3bda (run from any host
# with ssh access; each piece is detached on the machine; idempotent):
#   1. exec/bill-watch.sh          side monitor (runs until killed); Bill's work or the
#                                  CI/serving stops OUR whole-machine jobs
#   2. exec/qwen8u8k-prep.sh       builds the two runtron binaries on our half
#   3. exec/qwen8u8k-pr1-half.sh   qwen re-run on OUR half (cards 90/93, socket 1);
#                                  needs only the pre-build, the lease and serving down
#   4. exec/qwen8u8k-pr1.sh        qwen re-run in the August placement (Bill's cards);
#                                  waits for the cost-data steps and the monitor's CLEAR
# The chain (split-relaunch3d.sh) is already queued and is not touched.
# Running-check: `pgrep -fx "bash exec/<script>"` matches the detached process's exact
# command line and not this ssh shell (whose command line also contains the names).
set -u
ssh -o ConnectTimeout=20 delphi-3bda '
cd ~/workspace/intel-AMX || exit 1
start() {  # start <script> ; skip if that exact command line is already running, or if its work is done
  local s=$1
  if [ "$s" = qwen8u8k-prep.sh ] && [ "$(cat exec/logs/qwen8u8k-prep.done 2>/dev/null)" = ok ]; then echo "$s: already done (marker ok)"; return; fi
  if pgrep -fx "bash exec/$s" >/dev/null; then echo "$s: already running ($(pgrep -fx "bash exec/$s" | tr "\n" " "))"; return; fi
  { setsid nohup bash "exec/$s"; } >/dev/null 2>&1 </dev/null & disown
  sleep 1; echo "$s: started ($(pgrep -fx "bash exec/$s" | tr "\n" " "))"
}
for s in bill-watch.sh qwen8u8k-prep.sh qwen8u8k-pr1-half.sh qwen8u8k-pr1.sh; do start "$s"; done
echo "chain: $(pgrep -af "split-verif[y]3|split-benc[h]3" | grep -c bash) processes"
sleep 2; tail -1 exec/logs/bill-watch.log 2>/dev/null; tail -1 exec/logs/qwen8u8k-prep.log 2>/dev/null
'
