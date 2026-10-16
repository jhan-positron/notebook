#!/usr/bin/env bash
# Poll the pr1b-20261010 chain on delphi-3bda every 120 s from claude-box: print each new STEP line, exit when
# chain.done exists (exit 0) or when the chain process is gone without chain.done (exit 1).
seen=0
while :; do
  out=$(ssh -o ConnectTimeout=15 -o BatchMode=yes delphi-3bda bash -s <<'REMOTE' 2>/dev/null
R=~/workspace/intel-AMX/exec/results/pr1b-20261010
echo "STEPS $(wc -l < $R/steps.txt 2>/dev/null || echo 0)"
cat $R/steps.txt 2>/dev/null
echo "DONE $(cat $R/chain.done 2>/dev/null)"
echo "PROC $(pgrep -u jhan -f 'pr1-20261010/chain3.sh' | wc -l)"
echo "STATUS $(tail -1 ~/workspace/intel-AMX/exec/logs/pr1b-20261010-chain.log 2>/dev/null | cut -c1-200)"
REMOTE
  ) || { echo "$(date -u +%FT%TZ) ssh failed, retrying"; sleep 120; continue; }
  n=$(sed -n 's/^STEPS //p' <<<"$out"); done=$(sed -n 's/^DONE //p' <<<"$out"); proc=$(sed -n 's/^PROC //p' <<<"$out")
  if [ "${n:-0}" -gt "$seen" ]; then grep '^20' <<<"$out" | tail -n $((n - seen)); seen=$n; fi
  [ -n "$done" ] && { echo "$(date -u +%FT%TZ) CHAIN DONE: $done"; exit 0; }
  [ "${proc:-0}" = 0 ] && { echo "$(date -u +%FT%TZ) CHAIN PROCESS GONE without chain.done; last log: $(sed -n 's/^STATUS //p' <<<"$out")"; exit 1; }
  sleep 120
done
