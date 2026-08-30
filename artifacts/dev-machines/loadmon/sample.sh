#!/bin/bash
# Sample host load every INTERVAL seconds for DURATION seconds.
# Output: CSV in same dir named <hostname>.csv
INTERVAL=${INTERVAL:-300}
DURATION=${DURATION:-86400}
DIR=$(cd "$(dirname "$0")" && pwd)
OUT="$DIR/$(hostname).csv"
NCPU=$(nproc)
END=$(( $(date +%s) + DURATION ))
echo "ts,epoch,host,ncpu,load1,load5,load15,cpu_busy_pct,mem_used_gb,mem_avail_gb,users,top_user,top_pcpu,top_cmd" >> "$OUT"
read -r _ pu pn ps pi pw pq ps2 pst _ < /proc/stat
while [ "$(date +%s)" -lt "$END" ]; do
  sleep "$INTERVAL"
  read -r _ u n s i w q s2 st _ < /proc/stat
  dt=$(( (u+n+s+i+w+q+s2+st) - (pu+pn+ps+pi+pw+pq+ps2+pst) ))
  di=$(( (i+w) - (pi+pw) ))
  busy=$(awk -v dt="$dt" -v di="$di" 'BEGIN{ if (dt>0) printf "%.1f", 100*(dt-di)/dt; else print "" }')
  pu=$u; pn=$n; ps=$s; pi=$i; pw=$w; pq=$q; ps2=$s2; pst=$st
  read -r l1 l5 l15 _ < /proc/loadavg
  read -r mu ma < <(free -g | awk '/^Mem:/{print $3, $7}')
  users=$(who | awk '{print $1}' | sort -u | wc -l)
  read -r tu tp tc < <(ps -eo user:20,pcpu,comm --sort=-pcpu | sed -n 2p)
  echo "$(date -Is),$(date +%s),$(hostname),$NCPU,$l1,$l5,$l15,$busy,$mu,$ma,$users,$tu,$tp,$tc" >> "$OUT"
done
