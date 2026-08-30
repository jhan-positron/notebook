#!/usr/bin/env bash
# Poll delphi-3bda for the CI lease file through tonight's window; capture the
# first real lease content verbatim and test ci_lease_busy's logic against it.
OUT=~/workspace/intel-AMX/exec/results/lease-capture-2026-08-20.txt
for i in $(seq 1 18); do
  now=$(date -u +%H%M)
  [ "$now" -ge 0930 ] && [ "$now" -lt 2000 ] && break
  content=$(ssh -o ConnectTimeout=15 delphi-3bda 'cat /run/lock/systems-test-ci.lease 2>/dev/null')
  if [ -n "$content" ]; then
    { echo "captured $(date -u +%FT%TZ)"; echo "$content"; } > "$OUT"
    verdict=$(python3 - <<PY
import json, re, time
raw = '''$content'''
state, exp = '', 0.0
try:
    d = json.loads(raw)
    state = str(d.get('state', '')).strip().lower()
    exp = float(d.get('expires_at_epoch', 0))
except Exception:
    m = re.search(r'state["\s:=]+([A-Za-z_-]+)', raw)
    if m: state = m.group(1).lower()
    m = re.search(r'expires_at_epoch["\s:=]+(\d+(?:\.\d+)?)', raw)
    if m: exp = float(m.group(1))
print(f"parsed state={state!r} expires={exp} busy={state=='busy' and time.time()<exp}")
PY
)
    echo "$verdict" >> "$OUT"
    echo "LEASE CAPTURED: $verdict"
    exit 0
  fi
  sleep 1200
done
echo "LEASE-ABSENT-ALL-WINDOW $(date -u +%FT%TZ)" | tee "$OUT"
