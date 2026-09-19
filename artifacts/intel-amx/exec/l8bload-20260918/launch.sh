#!/usr/bin/env bash
# Start the l8bload-20260918 campaign ON delphi-3bda, detached (run from any host with ssh access).
# Idempotent: refuses when an instance is already running there (pgrep anchored on the interpreter
# and the full path, so this launcher and editors that name the file do not count).
C=/home/jhan/workspace/intel-AMX/exec/l8bload-20260918
ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda bash -s <<'EOF'
C=/home/jhan/workspace/intel-AMX/exec/l8bload-20260918
if pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/l8bload-20260918/campaign[.]sh$' >/dev/null; then
  echo "campaign already running on $(hostname): $(pgrep -a -f 'l8bload-20260918/campaign[.]sh$' | cut -c1-100)"; exit 0
fi
setsid nohup bash "$C/campaign.sh" >/dev/null 2>&1 < /dev/null &
sleep 2
echo "launched on $(hostname) pid $(pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/l8bload-20260918/campaign[.]sh$' | head -1); status: /home/jhan/workspace/intel-AMX/exec/logs/l8bload-20260918.status"
EOF
