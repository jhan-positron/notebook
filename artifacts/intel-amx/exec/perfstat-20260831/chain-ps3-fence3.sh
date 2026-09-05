#!/usr/bin/env bash
# Sequential chain, 2026-09-01 evening window: perf-stat round 3, then fence round 3.
bash ~/workspace/intel-AMX/exec/perfstat-20260831/run-perfstat3.sh
m=$(cat ~/workspace/intel-AMX/exec/logs/perfstat3-20260901.done 2>/dev/null)
echo "chain: perfstat3 marker=$m" >> ~/workspace/intel-AMX/exec/logs/chain-20260901.log
case "$m" in ok|check-output) bash ~/workspace/intel-AMX/exec/fence-20260831/run-fence3.sh ;; 
  *) echo "chain: fence3 skipped (perfstat3 marker=$m)" >> ~/workspace/intel-AMX/exec/logs/chain-20260901.log ;; esac
