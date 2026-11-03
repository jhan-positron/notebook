#!/bin/bash
# Read-only verification for the interrupts/noise dimension. No writes, no sudo, no settings changed.
export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0 PAGER=cat
T() { timeout 15 "$@" 2>&1; }
sec() { printf '\n=== %s ===\n' "$1"; }
sec date; date -u; cat /proc/uptime

sec kallsyms
for s in housekeeping_nohz_full_setup housekeeping_isolcpus_setup housekeeping_setup housekeeping_update housekeeping_cpumask \
  tmigr_init_isolation tmigr_isolated_exclude_cpumask tmigr_cpu_isolate wq_isolated_cpumask workqueue_unbound_housekeeping_update \
  kthread_affine_preferred kthreads_online_cpu kthreads_update_housekeeping cpc_read_ffh cpu_read_corecnt cpu_read_constcnt arch_freq_get_on_cpu \
  show_feedback_ctrs cppc_get_perf_ctrs rcu_exp_handler synchronize_rcu_expedited rcu_nocb_setup rcu_init_nohz rcu_nocb_mask \
  tick_nohz_full_setup tick_nohz_full_running context_tracking_enabled arm64_repeat_tlbi_list irq_can_set_affinity_usr write_irq_affinity \
  kick_all_cpus_sync vmstat_update quiet_vmstat lru_add_drain_all lru_add_drain_per_cpu irq_affinity_adjust print_cpus_isolated \
  sugov_work sugov_kthread_create namespace_unlock synchronize_net khugepaged_do_scan vmstat_shepherd pci_probe_flush_workqueue \
  mem_cgroup_flush_workqueue vmstat_flush_workqueue housekeeping_test_cpu; do
  if grep -qE " [tTdDbBrR] ${s}$" /proc/kallsyms; then echo "present $s"; else echo "ABSENT  $s"; fi
done
echo "any ipi_flush_tlb / flush_tlb_ipi symbols: $(grep -cE 'ipi_flush_tlb|flush_tlb_ipi|tlb_flush_ipi' /proc/kallsyms)"

sec interrupts_now
awk 'NR==1{for(i=1;i<=NF;i++){c=$i; sub("CPU","",c); col[i]=c}; n=NF; next}
 $1=="12:"||$1 ~ /^IPI[0-9]:/ {name=$1; s=0; line=""; for(i=2;i<=n+1;i++){c=col[i-1]; if(c+0>=120&&c+0<=127){s+=$i; line=line" cpu"c"="$i}}; print name, "on120_127="s, line}' /proc/interrupts
echo "--- nvme lines with any count on 120-127"
awk 'NR==1{for(i=1;i<=NF;i++){c=$i; sub("CPU","",c); col[i]=c}; n=NF; next}
 /nvme/ {s=0; for(i=2;i<=n+1;i++){c=col[i-1]; if(c+0>=120&&c+0<=127) s+=$i}; if(s>0) print $1, "on120_127="s, $NF}' /proc/interrupts
echo "--- nvme0q0 / nvme1q0 admin queue: columns with nonzero counts"
awk 'NR==1{for(i=1;i<=NF;i++){c=$i; sub("CPU","",c); col[i]=c}; n=NF; next}
 /nvme[01]q0$/ {line=$1; for(i=2;i<=n+1;i++){ if($i+0>0) line=line" cpu"col[i-1]"="$i}; print line}' /proc/interrupts
echo "--- IPI lines present"; awk '$1 ~ /^IPI/ {print $1, $(NF-2), $(NF-1), $NF}' /proc/interrupts

sec nvme_queues
for d in nvme0 nvme1; do echo "$d queue_count=$(cat /sys/class/nvme/$d/queue_count 2>&1) model=$(cat /sys/class/nvme/$d/model 2>&1)"; done
echo "nvme0n1 mq dirs: $(ls /sys/block/nvme0n1/mq 2>&1 | wc -l)"
for h in 0 1 118 119 120 121 122 123 124 125 126 127; do printf 'hctx%s:%s ' $h "$(cat /sys/block/nvme0n1/mq/$h/cpu_list 2>&1)"; done; echo
for i in 176 183 304 311; do echo "irq $i smp_affinity_list=$(cat /proc/irq/$i/smp_affinity_list 2>&1) effective=$(cat /proc/irq/$i/effective_affinity_list 2>&1) actions=$(cat /sys/kernel/irq/$i/actions 2>&1) chip=$(cat /sys/kernel/irq/$i/chip_name 2>&1) perms=$(stat -c %a /proc/irq/$i/smp_affinity_list 2>&1)"; done
echo "--- bnxt TxRx effective affinities (sample)"
for i in 378 381 385 399 409 420 432 440; do echo "irq $i $(cat /sys/kernel/irq/$i/actions 2>&1) smp=$(cat /proc/irq/$i/smp_affinity_list 2>&1) eff=$(cat /proc/irq/$i/effective_affinity_list 2>&1)"; done
echo "--- effective_affinity_list distribution top 6"; for d in /proc/irq/[0-9]*; do cat $d/effective_affinity_list 2>/dev/null; done | sort | uniq -c | sort -rn | head -6

sec timers
T systemctl list-timers --all --no-pager
for t in apt-daily.timer apt-daily-upgrade.timer fwupd-refresh.timer man-db.timer motd-news.timer ua-timer.timer update-notifier-download.timer update-notifier-motd.timer snapd.snap-repair.timer apport-autoreport.timer fstrim.timer logrotate.timer dpkg-db-backup.timer sysstat-collect.timer sysstat-summary.timer e2scrub_all.timer systemd-tmpfiles-clean.timer; do
  echo "$t active=$(systemctl is-active $t 2>&1) enabled=$(systemctl is-enabled $t 2>&1) $(systemctl show $t -p Persistent -p TimersCalendar -p TimersMonotonic -p RandomizedDelayUSec 2>&1 | tr '\n' ' ')"
done
echo "--- unattended-upgrades.service"; T systemctl cat unattended-upgrades.service | grep -E '^(Description|ExecStart|ExecStop)'
echo "--- fwupd-refresh"; T systemctl cat fwupd-refresh.timer | grep -E 'OnCalendar|Randomized|Persistent'; T systemctl cat fwupd-refresh.service | grep -E 'ExecStart|ProtectSystem|ProtectHome|PrivateTmp'
echo "--- systemd-timedated sandbox"; T systemctl cat systemd-timedated.service | grep -E 'PrivateTmp|ProtectHome|ProtectSystem'
echo "--- man-db nice"; T systemctl cat man-db.service | grep -E 'Nice|IOSched|ExecStart'
echo "--- motd-news, ua-timer, snap-repair, apport schedules"; for t in motd-news.timer ua-timer.timer snapd.snap-repair.timer apport-autoreport.timer update-notifier-download.timer update-notifier-motd.timer man-db.timer logrotate.timer dpkg-db-backup.timer sysstat-summary.timer e2scrub_all.timer systemd-tmpfiles-clean.timer; do echo "$t: $(systemctl cat $t 2>&1 | grep -E 'OnCalendar|OnUnitActiveSec|OnBootSec|OnStartupSec|Randomized|Persistent' | tr '\n' ' ')"; done

sec daemons_cron_sysstat
pgrep -a netserver; pgrep -a smartd
echo "netperf: $(systemctl show netperf.service -p ActiveState -p UnitFileState 2>&1 | tr '\n' ' ')"
grep -E '^ENABLED' /etc/default/sysstat 2>&1; ls -la /var/log/sysstat 2>&1 | tail -n +2
echo "cron.hourly: $(ls -A /etc/cron.hourly 2>&1 | tr '\n' ' ')"
grep -lE 'run/systemd/system' /etc/cron.daily/* 2>&1; echo "apport guard: $(grep -n 'var/crash' /etc/cron.daily/apport 2>&1)"
echo "--- debian-sa1 guard"; grep -nE 'ENABLED|systemd|exit' /usr/lib/sysstat/debian-sa1 2>&1 | head -8
echo "--- cron.d active lines"; grep -hvE '^\s*#|^\s*$' /etc/cron.d/sysstat /etc/cron.d/e2scrub_all 2>&1
echo "--- /etc/crontab"; grep -vE '^\s*#|^\s*$' /etc/crontab 2>&1
echo "snap list: $(timeout 5 snap list 2>&1 | head -2 | tr '\n' ' ')"; ls /dev/mapper 2>&1 | tr '\n' ' '; echo

sec rcu_kthreads
for p in 15 16 17 100 181 262 343 424 505 586 680 681; do echo "pid $p $(cat /proc/$p/comm 2>&1) psr=$(awk '{print $39}' /proc/$p/stat 2>&1) $(grep Cpus_allowed_list /proc/$p/status 2>&1)"; done
echo "--- rcuo kthreads: $(ps -eo comm | grep -cE '^rcuo[pg]/')"

sec threads_on_120_127
ps -eLo tid,psr,user,comm --no-headers | awk '$2>=120&&$2<=127' | sort -k2n -k4
echo "--- count by class"; ps -eLo psr,comm --no-headers | awk '$1>=120&&$1<=127{ if($2 ~ /^kworker\/u/) u++; else if($2 ~ /^kworker\/[0-9]/) p++; else if($2 ~ /^(cpuhp|ksoftirqd|migration)\//) c++; else if($2 ~ /^kworker\/R/) r++; else o++ } END{print "unbound_kworkers="u+0, "percpu_kworkers="p+0, "cpuhp_ksoftirqd_migration="c+0, "rescuers="r+0, "other="o+0}'
echo "--- flush kworker 14642"; ps -o pid,lstart,etime,psr,comm -p 14642 2>&1
echo "--- sugov kthreads: $(ps -eo comm | grep -c '^sugov')"; ps -eo pid,psr,cls,rtprio,comm | grep sugov | head -3
echo "--- cpufreq policy120 files"; ls /sys/devices/system/cpu/cpufreq/policy120/ | tr '\n' ' '; echo
echo "--- per-cpu kworkers on 127 CPU time (utime+stime ticks)"; for t in $(ps -eLo tid,comm --no-headers | awk '$2 ~ /^kworker\/127:/ {print $1}'); do echo "tid $t $(cat /proc/$t/comm) ticks=$(awk '{print $14+$15}' /proc/$t/stat) ctxt=$(grep -E 'ctxt_switches' /proc/$t/status | tr '\n' ' ')"; done
for t in $(ps -eLo tid,comm --no-headers | awk '$2 ~ /^(ksoftirqd|migration)\/127$/ {print $1}'); do echo "tid $t $(cat /proc/$t/comm) ticks=$(awk '{print $14+$15}' /proc/$t/stat) $(grep -E 'ctxt_switches' /proc/$t/status | tr '\n' ' ')"; done

sec sched_files
echo "/proc/self/sched: $(grep -E '^(nr_switches|nr_voluntary_switches|nr_involuntary_switches|se.nr_migrations)' /proc/self/sched 2>&1 | tr '\n' ' ')"
grep -E 'ctxt_switches' /proc/self/status
echo "schedstat: $(head -c 40 /proc/schedstat 2>&1)"
echo "vm.stat_interval=$(cat /proc/sys/vm/stat_interval) khugepaged scan_sleep_ms=$(cat /sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs) pages_collapsed=$(cat /sys/kernel/mm/transparent_hugepage/khugepaged/pages_collapsed) defrag=$(cat /sys/kernel/mm/transparent_hugepage/khugepaged/defrag) thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
grep -E '^(thp_fault_alloc|thp_collapse_alloc|pgmigrate_success|compact_success|compact_stall) ' /proc/vmstat
echo "cpuidle driver: $(cat /sys/devices/system/cpu/cpuidle/current_driver 2>&1) governor: $(cat /sys/devices/system/cpu/cpuidle/current_governor 2>&1)"
echo "dmesg AMU: $(dmesg 2>/dev/null | grep -iE 'activity monitor|AMU' | head -2 | tr '\n' ';')"
echo "dmesg unknown params: $(dmesg 2>/dev/null | grep -icE 'Unknown kernel command line')"
echo "dmesg housekeeping: $(dmesg 2>/dev/null | grep -icE 'Housekeeping')"
echo "isolated=$(cat /sys/devices/system/cpu/isolated) wq cpumask=$(cat /sys/devices/virtual/workqueue/cpumask) isolated_mask=$(cat /sys/devices/virtual/workqueue/cpumask_isolated 2>&1)"

sec feedback_ctrs_ipi_test
# read-only: 10 sysfs reads of CPU 121's CPPC feedback counters; count IPI1 on CPU 121 before/after (idle CPU)
ipi1() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1=="IPI1:"{print $(k+1)}' /proc/interrupts; }
a=$(ipi1 121); for i in $(seq 10); do cat /sys/devices/system/cpu/cpu121/acpi_cppc/feedback_ctrs >/dev/null; done; b=$(ipi1 121)
echo "IPI1 on cpu121 across 10 feedback_ctrs reads: $((b-a))"
a=$(ipi1 121); for i in $(seq 10); do cat /sys/devices/system/cpu/cpufreq/policy121/scaling_cur_freq >/dev/null; done; b=$(ipi1 121)
echo "IPI1 on cpu121 across 10 scaling_cur_freq reads: $((b-a))"
a=$(ipi1 121); sleep 2; b=$(ipi1 121); echo "IPI1 on cpu121 across 2 s of nothing: $((b-a))"

sec sdk_rules
grep -nE 'others=|load1=|runner=' /home/positron-perf/positron/src/phoenix-int/tools/perf/host_facts.sh 2>&1 | cut -c1-240
grep -nE '^LOAD_MAX|LOAD_MAX =' /home/positron-perf/positron/src/phoenix-int/tools/perf/records.py 2>&1
grep -nE 'poll_ns|kPollNs|poll_ns_' /home/positron-perf/positron/src/phoenix-int/backends/null_timing/null_timing.cpp 2>&1 | head -5 | cut -c1-200

sec sessions
echo "epoch 1792524689 = $(date -u -d @1792524689 2>&1)"
T loginctl show-session 4 -p TTY -p Remote -p Type -p IdleHint -p IdleSinceHint -p State 2>&1 | tr '\n' ' '; echo
ps -u arm -o pid,etime,stat,pcpu,comm 2>&1
echo "--- positron-perf user timers"; T systemctl --user list-timers --all --no-pager 2>&1 | head -5; T systemctl --user cat launchpadlib-cache-clean.timer 2>&1 | grep -E 'OnCalendar|Randomized|Persistent|AccuracySec'
echo "--- home perms, arm groups"; stat -c '%a %U:%G %n' /home/positron-perf; id arm 2>&1

sec end; date -u; echo DONE
