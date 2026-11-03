#!/bin/sh
# poll the lab share (via delphi-3bda, read-only ls) until membench-jibin-003 has a README and is stable
D=/home/jzhang/dev/emuMemBenchBox/results/jibin/membench-jibin-003
i=0
while [ $i -lt 120 ]; do
  s=$(ssh -o BatchMode=yes -o ConnectTimeout=15 delphi-3bda "ls -la $D/README.md $D/SHA256SUMS 2>/dev/null | wc -l; find $D -type f 2>/dev/null | wc -l" 2>/dev/null | tr '\n' ' ')
  case "$s" in
    "2 "*) n1=${s#2 }; sleep 300
           s2=$(ssh -o BatchMode=yes -o ConnectTimeout=15 delphi-3bda "find $D -type f 2>/dev/null | wc -l" 2>/dev/null)
           [ "$n1" = "$s2 " ] || [ "$n1" = "$s2" ] && { echo "membench-jibin-003 ready: $s2 files, README and SHA256SUMS present, stable 5 min ($(date -u +%H:%M) UTC)"; exit 0; } ;;
  esac
  i=$((i+1)); sleep 300
done
echo "watch003 gave up after 10 h"
