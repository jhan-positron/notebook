# hostfacts.sh - read-only facts of CRB for hypothesis H3/H4 (no write, no setting change). Sent on stdin of one ssh login.
if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi
echo "## utc $(date -u +%FT%TZ) loadavg $(cat /proc/loadavg) logins $(who | wc -l)"
uname -a
echo "## cmdline"; cat /proc/cmdline
echo "## nodes"; ls /sys/devices/system/node/ | tr '\n' ' '; echo; cat /sys/devices/system/node/online; for n in /sys/devices/system/node/node*; do echo "$n cpus $(cat $n/cpulist) $(grep -E 'MemTotal|MemFree' $n/meminfo | tr -s ' ' | tr '\n' ' ')"; done
echo "## sysctl (read)"; for f in kernel/numa_balancing kernel/numa_balancing_promote_rate_limit_MBps kernel/perf_event_paranoid kernel/sched_autogroup_enabled kernel/timer_migration vm/stat_interval vm/compaction_proactiveness vm/zone_reclaim_mode vm/swappiness kernel/watchdog kernel/nmi_watchdog kernel/watchdog_thresh kernel/sched_rt_runtime_us; do printf '%s = ' $f; cat /proc/sys/$f 2>&1; done
echo "## debugfs sched numa"; ls /sys/kernel/debug/sched/numa_balancing 2>&1 | head; for f in /sys/kernel/debug/sched/numa_balancing/*; do printf '%s = ' $f; cat $f 2>&1; done
echo "## thp"; for f in enabled defrag khugepaged/defrag khugepaged/scan_sleep_millisecs khugepaged/alloc_sleep_millisecs khugepaged/pages_to_scan khugepaged/full_scans khugepaged/pages_collapsed use_zero_page; do printf '%s = ' $f; cat /sys/kernel/mm/transparent_hugepage/$f 2>&1; done
echo "## lru_gen"; cat /sys/kernel/mm/lru_gen/enabled 2>&1; cat /sys/kernel/mm/lru_gen/min_ttl_ms 2>&1
echo "## ksm"; cat /sys/kernel/mm/ksm/run 2>&1
echo "## cpu"; grep -m1 -A8 '^processor' /proc/cpuinfo; lscpu 2>&1 | head -40
echo "## cpufreq cpu2 cpu41"; for c in 2 41; do for f in scaling_governor scaling_driver scaling_cur_freq cpuinfo_max_freq cpuinfo_min_freq; do printf 'cpu%s %s = ' $c $f; cat /sys/devices/system/cpu/cpu$c/cpufreq/$f 2>&1; done; done
echo "## cpuidle cpu2"; for d in /sys/devices/system/cpu/cpu2/cpuidle/state*; do echo "$d $(cat $d/name 2>&1) disable=$(cat $d/disable 2>&1) usage=$(cat $d/usage 2>&1)"; done; cat /sys/devices/system/cpu/cpuidle/current_driver 2>&1
echo "## isolated / nohz_full"; cat /sys/devices/system/cpu/isolated /sys/devices/system/cpu/nohz_full 2>&1
echo "## cache cpu2"; for d in /sys/devices/system/cpu/cpu2/cache/index*; do echo "$d L$(cat $d/level) $(cat $d/type) $(cat $d/size) ways=$(cat $d/ways_of_associativity 2>&1) sets=$(cat $d/number_of_sets 2>&1) line=$(cat $d/coherency_line_size 2>&1) shared=$(cat $d/shared_cpu_list)"; done
echo "## pmu devices"; ls /sys/bus/event_source/devices/
for p in /sys/bus/event_source/devices/armv8_pmuv3_0; do echo "type $(cat $p/type) cpus $(cat $p/cpus 2>&1) slots $(cat $p/caps/slots 2>&1) pmuver $(cat $p/caps/pmuver 2>&1) bus_slots $(cat $p/caps/bus_slots 2>&1)"; for e in $p/events/*; do printf '%s %s\n' "$(basename $e)" "$(cat $e)"; done; done
echo "## vmstat numa/thp/migrate/compact"; grep -E '^(numa_|pgmigrate|thp_|compact_|pgfault|pgmajfault|nr_anon_transparent|khugepaged)' /proc/vmstat
echo "## timers/tick"; grep -E 'CONFIG_HZ|CONFIG_NO_HZ|CONFIG_NUMA_BALANCING|CONFIG_PREEMPT|CONFIG_LRU_GEN|CONFIG_ARM64_.*PAGES|CONFIG_TRANSPARENT' /boot/config-$(uname -r) 2>&1 | head -40
echo "## interrupts cpu2 cpu41 (nonzero rows)"; awk 'NR==1{print "hdr"} NR>1 { if ($4+0>0 || $43+0>0) print $1, $4, $43, $NF }' /proc/interrupts | head -60
echo "## ps threads on cpu 2 and 41"; ps -eLo psr,pid,comm,pcpu --sort=psr | awk '$1==2 || $1==41' | head -40
echo "## numactl / perf present"; command -v numactl perf taskset chrt 2>&1
echo "## ulimit -l (memlock, kB)"; ulimit -l; echo "## hugetlb"; grep -i huge /proc/meminfo
echo "## end"
