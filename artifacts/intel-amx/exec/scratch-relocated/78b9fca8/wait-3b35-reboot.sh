#!/bin/bash
# Wait until delphi-3b35 has rebooted (boot time differs from OLD_BOOT) and has
# then stayed up for STABLE_S seconds. Read-only: runs only `uptime -s` there.
OLD_BOOT="2026-08-24 16:12:16"
STABLE_S=900
DEADLINE=$(( $(date +%s) + 11*3600 ))
last=""
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  b=$(timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=10 delphi-3b35 'uptime -s' 2>/dev/null | tail -1)
  now=$(date '+%F %T %Z')
  if [ -z "$b" ]; then
    [ "$last" != "down" ] && echo "$now  no answer from delphi-3b35 (rebooting or unreachable)"
    last="down"
  elif [ "$b" != "$OLD_BOOT" ]; then
    up=$(( $(date +%s) - $(date -d "$b" +%s) ))
    [ "$last" != "$b" ] && echo "$now  new boot time: $b (up ${up}s)"
    last="$b"
    if [ "$up" -ge "$STABLE_S" ]; then
      echo "$now  REBOOTED and up ${up}s since $b: stable"
      exit 0
    fi
  else
    [ "$last" != "old" ] && echo "$now  still the old boot ($OLD_BOOT)"
    last="old"
  fi
  sleep 60
done
echo "$(date '+%F %T %Z')  DEADLINE reached, no stable reboot seen (last state: $last)"
exit 3
