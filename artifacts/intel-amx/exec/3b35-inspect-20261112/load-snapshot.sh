#!/usr/bin/env bash
# load-snapshot.sh - system load record to attach to every perf report.
#
# Read-only: reads /proc, /sys and runs ps/who/ls. Writes only to stdout.
# Needs no root. Takes SAMPLE_S seconds (default 10) plus about 2 s.
#
# Usage (from the agent server):
#   ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh' > load-before.txt
#
# OUR_APP / OUR_DEV default to what "--instance 1,2" selects for server type
# granite_rapids_6962p in /opt/positron/config/resource-map.yaml
# (slices 4-7: tron_cores, dev_cores). Override them for another instance.
#
# Not measured here: memory bandwidth in GB/s. That needs root on this host
# (kernel.perf_event_paranoid=4 blocks uncore counters, resctrl is not mounted).
# Section 6 gives the unprivileged substitute: who runs threads on our socket.

set -u
SAMPLE_S=${SAMPLE_S:-10}
OUR_APP=${OUR_APP:-96-143,223-230}
OUR_DEV=${OUR_DEV:-75-78}
OUR_NODE=${OUR_NODE:-1}
HZ=$(getconf CLK_TCK)

# "a-b,c" -> one cpu number per line
expand() { echo "$1" | tr ',' '\n' | awk -F- '{ if (NF==2) for (i=$1;i<=$2;i++) print i; else print $1 }'; }

# one line per thread: pid tid cpu_ticks last_cpu state
threads() {
  awk '{ s=$0; sub(/^.*\) /,"",s); split(s,f," "); split(FILENAME,p,"/");
         print p[3], p[5], f[12]+f[13], f[37], f[1] }' /proc/[0-9]*/task/[0-9]*/stat 2>/dev/null
}
cpustat() { grep -E '^cpu[0-9]+ ' /proc/stat; }

echo "=== load snapshot: $(hostname) $(date -u +%Y-%m-%dT%H:%M:%SZ) sample=${SAMPLE_S}s ==="
echo "SYSTEM_CONFIG=[${SYSTEM_CONFIG:-}] OUR_APP=$OUR_APP OUR_DEV=$OUR_DEV OUR_NODE=$OUR_NODE kernel=$(uname -r)"

echo; echo "--- 1. load average (1/5/15 min, runnable/total threads) ---"
cat /proc/loadavg
echo "logged in: $(who | awk '{print $1}' | sort | uniq -c | awk '{printf "%s x%s  ", $2, $1}')"

# ---- timed sample -------------------------------------------------------
PKG=$(for c in /sys/devices/system/cpu/cpu[0-9]*; do echo "${c##*cpu} $(cat "$c/topology/physical_package_id")"; done)
OWN=$(stat -c '%n %U' /proc/[0-9]* 2>/dev/null | sed 's|/proc/||')
NUMA_A=$(cat /sys/devices/system/node/node"$OUR_NODE"/numastat)
CA=$(cpustat); TA=$(threads)
sleep "$SAMPLE_S"
CB=$(cpustat); TB=$(threads)
NUMA_B=$(cat /sys/devices/system/node/node"$OUR_NODE"/numastat)

echo; echo "--- 2. CPU utilisation over ${SAMPLE_S}s from /proc/stat (100% = every CPU of the group busy) ---"
{ echo "#PKG"; echo "$PKG"; echo "#APP"; expand "$OUR_APP"; echo "#DEV"; expand "$OUR_DEV"
  echo "#A"; echo "$CA"; echo "#B"; echo "$CB"; } | awk '
  /^#/ { sec=$1; next }
  sec=="#PKG" { pkg[$1]=$2; next }
  sec=="#APP" { grp[$1]="our-app-cores"; next }
  sec=="#DEV" { grp[$1]="our-dev-cores"; next }
  { c=substr($1,4); tot=0; for (i=2;i<=9;i++) tot+=$i; idle=$5+$6
    if (sec=="#A") { ta[c]=tot; ia[c]=idle } else { dt[c]=tot-ta[c]; di[c]=idle-ia[c] } }
  END {
    for (c in dt) { k="socket" pkg[c]; T[k]+=dt[c]; I[k]+=di[c]; N[k]++
                    if (c in grp) { k=grp[c]; T[k]+=dt[c]; I[k]+=di[c]; N[k]++ }
                    if (dt[c]>0 && (dt[c]-di[c])/dt[c] > 0.5) { B["socket" pkg[c]]++; if (c in grp) B[grp[c]]++ } }
    printf "%-16s %5s %9s %14s\n", "group", "cpus", "busy_pct", "cpus_over_50pct"
    n=split("socket0 socket1 our-app-cores our-dev-cores", o, " ")
    for (j=1;j<=n;j++) { k=o[j]; if (N[k]) printf "%-16s %5d %8.1f%% %14d\n", k, N[k], 100*(T[k]-I[k])/T[k], B[k]+0 } }'

echo; echo "--- 3. CPU per user over ${SAMPLE_S}s, in CPUs (1.00 = one CPU fully busy), split by socket of the last CPU used ---"
{ echo "#PKG"; echo "$PKG"; echo "#OWN"; echo "$OWN"; echo "#A"; echo "$TA"; echo "#B"; echo "$TB"; } | awk -v hz="$HZ" -v s="$SAMPLE_S" '
  /^#/ { sec=$1; next }
  sec=="#PKG" { pkg[$1]=$2; next }
  sec=="#OWN" { own[$1]=$2; next }
  sec=="#A" { a[$2]=$3; next }
  { if (!($2 in a)) next; d=$3-a[$2]; if (d<=0) next
    u=(($1 in own)?own[$1]:"?"); cpu[u,pkg[$4]]+=d/hz/s; tot[u]+=d/hz/s }
  END { printf "%-14s %9s %9s %9s\n", "user", "socket0", "socket1", "total"
        for (u in tot) if (tot[u]>=0.01) printf "%-14s %9.2f %9.2f %9.2f\n", u, cpu[u,0], cpu[u,1], tot[u] }' | { read -r h; echo "$h"; sort -k4 -rn; }

echo; echo "--- 4. threads that used more than 0.5 CPU in the sample (user, command, last CPU, affinity) ---"
{ echo "#OWN"; echo "$OWN"; echo "#A"; echo "$TA"; echo "#B"; echo "$TB"; } | awk -v hz="$HZ" -v s="$SAMPLE_S" '
  /^#/ { sec=$1; next }
  sec=="#OWN" { own[$1]=$2; next }
  sec=="#A" { a[$2]=$3; next }
  { if (($2 in a) && ($3-a[$2])/hz/s > 0.5) print own[$1], $1, $4 }' | sort | awk '
  { k=$1" "$2; n[k]++; l[k]=l[k] (l[k]?",":"") $3 } END { for (k in n) print k, n[k], l[k] }' | while read -r u p n cpus; do
    echo "user=$u pid=$p comm=$(cat /proc/"$p"/comm 2>/dev/null) busy_threads=$n last_cpus=$cpus process_affinity=$(taskset -cp "$p" 2>/dev/null | sed 's/.*: //')"
  done

echo; echo "--- 5. tron-family processes (any user) ---"
ps -eo user:12,pid,psr,pcpu,nlwp,etime,args --no-headers | grep -E '/(rinzler|runtron|tron|t_[a-z_0-9]+)( |$)' | grep -v grep | cut -c1-260
echo "FPGA cards in use (sysfs enable=1 means a process holds the device open):"
for d in /sys/bus/pci/devices/*; do
  [ "$(cat "$d/vendor")" = "0x8200" ] && echo "  ${d##*/} numa=$(cat "$d/numa_node") enable=$(cat "$d/enable")"
done

echo; echo "--- 6. memory activity on node $OUR_NODE (substitute for memory bandwidth, see header) ---"
{ echo "$NUMA_A"; echo "#B"; echo "$NUMA_B"; } | awk -v s="$SAMPLE_S" '
  /^#B/ { b=1; next } !b { a[$1]=$2; next } { printf "%s_per_s=%.0f  ", $1, ($2-a[$1])/s } END { print "(4 KiB pages)" }'
grep -E 'MemFree|FilePages|AnonPages|Dirty' /sys/devices/system/node/node"$OUR_NODE"/meminfo | awk '{printf "%s %s %s  ", $3, $4, $5} END {print ""}'

echo; echo "--- 7. 1 GiB hugepages ---"
for n in /sys/devices/system/node/node[0-9]*; do
  h=$n/hugepages/hugepages-1048576kB
  echo "${n##*/}: total=$(cat "$h/nr_hugepages") free=$(cat "$h/free_hugepages")"
done
ls -la --time-style=long-iso /dev/hugepages/ | sed 1d

echo; echo "=== end $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
