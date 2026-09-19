#!/usr/bin/env bash
# Queue the vnnik-20260914 campaign on delphi-3bda (run ON delphi-3bda). Idempotent.
# A tiny waiter polls the CI lease (clear on 3 polls 60 s apart) and only then starts
# campaign.sh, so the campaign file can still be edited until the lease clears (bash reads
# a running script incrementally from NFS; a waiting campaign could not be edited). The
# campaign resolves the branch tip at build time (VNNIK_TIP overrides).
EXEC=/home/jhan/workspace/intel-AMX/exec
if pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign[.]sh$' >/dev/null || pgrep -f 'vnnik-20260914 waiter' >/dev/null; then
  echo "already queued/running: $(pgrep -af 'vnnik-20260914' | grep -v pgrep | cut -c1-80 | tr '\n' ';')"; exit 0
fi
mkdir -p "$EXEC/logs"
echo "$(date -u +%FT%TZ) queued: vnnik-20260914 waiter polls the CI lease" >"$EXEC/logs/vnnik-20260914.status"
setsid nohup bash -c ': vnnik-20260914 waiter; source /home/jhan/workspace/intel-AMX/exec/lib-guard.sh; n=0; while :; do if ci_lease_busy; then n=0; else n=$((n+1)); [ "$n" -ge 3 ] && break; fi; sleep 60; done; exec bash /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh' >/dev/null 2>&1 &
sleep 2
echo "queued: $(pgrep -af 'vnnik-20260914' | grep -v pgrep | cut -c1-100 | tr '\n' ';')"; cat "$EXEC/logs/vnnik-20260914.status" 2>/dev/null
