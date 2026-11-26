#!/bin/bash
# One reboot of CRB, then record the module count. Arg: try number.
N=$1; H="ssh -o BatchMode=yes -o ConnectTimeout=15 jhan@192.168.2.45"
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi;'
OLD=$($H "$M who | grep -v '^jhan' | head -3; ps -eo user:20,comm --no-headers | awk '\$1!=\"root\" && \$1!=\"jhan\" && \$1!~/^(systemd|message|syslog|_|polkit|chrony|uuidd|daemon|avahi|rtkit|nobody|www|lp)/' | head -5; echo BID=\$(cat /proc/sys/kernel/random/boot_id)") || { echo "pre-check failed: $OLD"; exit 3; }
echo "pre: $OLD"; OB=$(echo "$OLD" | sed -n 's/^BID=//p'); [ -n "$OB" ] || exit 4
T0=$(date +%s); $H "$M sudo -n systemctl reboot" ; sleep 150
for i in $(seq 1 40); do
  NB=$($H 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null)
  if [ -n "$NB" ] && [ "$NB" != "$OB" ]; then break; fi; sleep 10
done
[ -n "$NB" ] && [ "$NB" != "$OB" ] || { echo "no new boot after $(( $(date +%s)-T0 )) s"; exit 5; }
echo "try $N: back after $(( $(date +%s)-T0 )) s"
$H "$M cd ~/cache-perf/dimm7200-20261117 && { date -u +%FT%TZ; cat /proc/sys/kernel/random/boot_id; uptime; grep MemTotal /proc/meminfo; sudo -n dmesg | grep 'DIMM sockets'; echo modules=\$(sudo -n dmidecode -t 17 | grep -c 'Size: 32 GB'); sudo -n dmidecode -t 17 | grep 'Configured Memory Speed' | sort | uniq -c; echo hwerr=\$(sudo -n dmesg | grep -c 'Hardware error from APEI'); sudo -n dmesg | grep -m3 'event severity'; } | tee try$N.txt"
