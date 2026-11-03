#!/usr/bin/env bash
# pr5047-20261020 follow-up cell (runs ON delphi-3bda, detached, AFTER chain.done = ok): the kill-switch arms on llama-3.1-8b at
# prompt 8192. With TRON_AMX_DISABLE=1 every page takes the software scoring loop that commit 1 restructured (AVX share of K
# tokens 100 % instead of 3 %), so a dotter-path cost behind the +0.5 % prefill delta of the option-OFF pair is amplified
# about 35 times. Arms baseoff / headoff = the option-OFF binaries with the kill switch. Same campaign.sh, same NAME, one
# extra cell appended to rt-results.txt; gen_report.py and gen_page.py know the pair headoff:baseoff.
# Usage (on 3bda): setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr5047-20261020/killswitch.sh >/dev/null 2>&1 </dev/null &
set -u
C=/home/jhan/workspace/intel-AMX/exec/pr5047-20261020
RES=/home/jhan/workspace/intel-AMX/exec/results/pr5047-20261020
LOG=/home/jhan/workspace/intel-AMX/exec/logs/pr5047-20261020-killswitch.log
exec >>"$LOG" 2>&1
echo "=== killswitch cell started $(date -u +%FT%TZ) pid $$ ==="
[ "$(cat "$RES/chain.done" 2>/dev/null)" = ok ] || { echo "chain.done is not ok ($(cat "$RES/chain.done" 2>/dev/null)); not starting"; exit 1; }
pgrep -f 'pr5047-20261020/(chain|campaign|smoke|tests)[.]sh' >/dev/null && { echo "a pr5047-20261020 script still runs; not starting"; exit 1; }
mv -f /home/jhan/workspace/intel-AMX/exec/logs/pr5047-20261020.done /home/jhan/workspace/intel-AMX/exec/logs/pr5047-20261020.done.main 2>/dev/null
env NAME=pr5047-20261020 REPS=${REPS:-4} ARMS="baseoff headoff" \
  CELLS_ALL='l8b-tp2-8u-p8192-off|llama-3.1-8b-instruct-good-tp2|2|8|8192|cpu|256|baseoff headoff' \
  bash "$C/campaign.sh"
echo "=== killswitch cell finished $(date -u +%FT%TZ): $(cat /home/jhan/workspace/intel-AMX/exec/logs/pr5047-20261020.done 2>/dev/null) ==="
python3 "$C/gen_report.py" "$RES" >"$RES/results.md" 2>"$RES/gen_report.err" && echo "report regenerated"
