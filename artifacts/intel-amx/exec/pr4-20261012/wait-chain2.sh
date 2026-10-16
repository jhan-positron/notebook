#!/usr/bin/env bash
# Poll the pr4-20261012 chain on delphi-3bda every 120 s from claude-box: print each new STEP line, exit when chain.done
# exists (exit 0) or when the chain process is gone without chain.done (exit 1). The pgrep pattern uses "chain2?[.]sh" so
# that it cannot match its own command line (the PR-1 trap); the remote script is sent on stdin, not on the ssh command line.
# WAIT_FOR=run1 (default final): run 1's marker "our-half-done ..." counts as done. With the default, that marker is ignored
# (run 2, the whole-machine run, writes the final chain.done).
# Fork of exec/pr3-20261012/wait-chain2.sh (PR4-handoff.md step 6, edit 17).
WAIT_FOR=${WAIT_FOR:-final}
seen=0
while :; do
  out=$(ssh -o ConnectTimeout=15 -o BatchMode=yes delphi-3bda bash -s <<'REMOTE' 2>/dev/null
R=~/workspace/intel-AMX/exec/results/pr4-20261012
echo "STEPS $(wc -l < $R/steps.txt 2>/dev/null || echo 0)"
cat $R/steps.txt 2>/dev/null
echo "DONE $(cat $R/chain.done 2>/dev/null)"
echo "PROC $(pgrep -u jhan -f 'pr4-20261012/chain2?[.]sh' | wc -l)"
echo "STATUS $(tail -1 ~/workspace/intel-AMX/exec/logs/pr4-20261012-chain.log 2>/dev/null | cut -c1-200)"
REMOTE
  ) || { echo "$(date -u +%FT%TZ) ssh failed, retrying"; sleep 120; continue; }
  n=$(sed -n 's/^STEPS //p' <<<"$out"); done=$(sed -n 's/^DONE //p' <<<"$out"); proc=$(sed -n 's/^PROC //p' <<<"$out")
  if [ "$WAIT_FOR" != run1 ]; then case $done in our-half-done*) done="";; esac; fi
  if [ "${n:-0}" -gt "$seen" ]; then grep '^20' <<<"$out" | tail -n $((n - seen)); seen=$n; fi
  [ -n "$done" ] && { echo "$(date -u +%FT%TZ) CHAIN DONE: $done"; exit 0; }
  [ "${proc:-0}" = 0 ] && { echo "$(date -u +%FT%TZ) CHAIN PROCESS GONE without chain.done; last log: $(sed -n 's/^STATUS //p' <<<"$out")"; exit 1; }
  sleep 120
done
