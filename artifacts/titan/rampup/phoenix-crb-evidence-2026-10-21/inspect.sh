#!/bin/bash
# Read-only host inspection. Creates no files on the host, changes no settings.
export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0 PAGER=cat
T() { timeout 20 "$@" 2>&1; }
sec() { printf '\n=== %s ===\n' "$1"; }
R=120; RH=127

sec identity
date -u; hostname; uname -a; head -3 /etc/os-release; uptime; echo "cmdline: $(cat /proc/cmdline)"; id; echo "HOME=$HOME SHELL=$SHELL"; echo "PATH=$PATH"
T timedatectl 2>&1 | head -8

sec logins
who; echo ---; T last -n 25 -F 2>&1 | head -30; echo ---; echo "local users (uid>=1000):"; getent passwd | awk -F: '$3>=1000 && $3<65534 {print $1, $3, $6, $7}'; echo "--- group members"; getent group sudo adm docker 2>&1

sec cpu_summary
T lscpu
echo ---; for f in online offline isolated nohz_full possible present; do printf '%s: ' $f; cat /sys/devices/system/cpu/$f 2>&1; done
echo ---; echo "smt control: $(cat /sys/devices/system/cpu/smt/control 2>&1) active: $(cat /sys/devices/system/cpu/smt/active 2>&1)"

sec topology_120_127
for c in $(seq $R $RH); do d=/sys/devices/system/cpu/cpu$c/topology; echo "cpu$c pkg=$(cat $d/physical_package_id) core=$(cat $d/core_id) cluster=$(cat $d/cluster_id 2>/dev/null) siblings=$(cat $d/thread_siblings_list) core_cpus=$(cat $d/core_cpus_list 2>/dev/null) cluster_cpus=$(cat $d/cluster_cpus_list 2>/dev/null) node=$(ls -d /sys/devices/system/cpu/cpu$c/node* 2>/dev/null | xargs -n1 basename)"; done
echo "--- caches cpu120"; for i in /sys/devices/system/cpu/cpu120/cache/index*; do echo "$(basename $i) L$(cat $i/level) $(cat $i/type) $(cat $i/size) shared=$(cat $i/shared_cpu_list)"; done
echo "--- numa"; ls /sys/devices/system/node/ 2>&1 | tr '\n' ' '; echo; for n in /sys/devices/system/node/node[0-9]*; do echo "$(basename $n): cpus=$(cat $n/cpulist) $(grep MemTotal $n/meminfo)"; done
echo "--- cluster_id distribution (count cpus-per-cluster -> how many clusters)"; for c in /sys/devices/system/cpu/cpu[0-9]*; do cat $c/topology/cluster_id 2>/dev/null; done | sort -n | uniq -c | awk '{print $1}' | sort -n | uniq -c
echo "--- package distribution"; for c in /sys/devices/system/cpu/cpu[0-9]*; do cat $c/topology/physical_package_id; done | sort -n | uniq -c
echo "--- core_id for cpus 0-3 and 120-127"; for c in 0 1 2 3 $(seq $R $RH); do printf 'cpu%s:core%s ' $c $(cat /sys/devices/system/cpu/cpu$c/topology/core_id); done; echo

sec kernel_config
if [ -r /proc/config.gz ]; then echo "source: /proc/config.gz"; zcat /proc/config.gz | grep -E '^(# )?CONFIG_(NO_HZ|HZ|RCU_NOCB|RCU_EXPERT|RCU_BOOST|RCU_LAZY|RCU_NOCB_CPU|CPU_ISOLATION|CPUSETS|CGROUPS|PREEMPT|SCHED_|IRQ_TIME|VIRT_CPU|TICK|CONTEXT_TRACKING|CPU_FREQ|ARM_CPPC|ACPI_CPPC|CPU_IDLE|ARM_PSCI_CPUIDLE|TASKS_RCU|TASKS_TRACE|HIGH_RES_TIMERS|ARM64_PSEUDO_NMI|GENERIC_IRQ_MIGRATION|HOTPLUG_CPU|NUMA|TRANSPARENT_HUGEPAGE|KSM|LOCALVERSION|MODULE_SIG|DEBUG_INFO|KASAN|UBSAN|LOCKDEP|PROVE_LOCKING|DEBUG_PREEMPT|FTRACE|FUNCTION_TRACER|PERF_EVENTS|WATCHDOG|SOFTLOCKUP|HARDLOCKUP|DETECT_HUNG|ARM64_AMU|ARM_ARCH_TIMER|ACPI=|ACPI_PROCESSOR|CPU_FREQ_GOV|CPU_FREQ_DEFAULT|ARM_SCMI|VMAP_STACK|RT_GROUP|UCLAMP|ENERGY_MODEL)' ; else echo "/proc/config.gz not readable"; fi
echo "--- /boot configs"; ls -la /boot/config-* 2>&1; for k in /boot/config-*; do [ -r "$k" ] && echo "$k: $(grep -E '^(# )?CONFIG_NO_HZ_FULL\b' $k 2>&1) | $(grep -E '^(# )?CONFIG_RCU_NOCB_CPU\b' $k 2>&1) | $(grep -E '^(# )?CONFIG_RCU_EXPERT\b' $k 2>&1) | $(grep -E '^CONFIG_HZ=' $k 2>&1) | $(grep -E '^CONFIG_PREEMPT(_NONE|_VOLUNTARY|_DYNAMIC|_RT|)=y' $k 2>&1 | tr '\n' ' ')"; done

sec boot_and_kernels
ls -la /boot/ 2>&1; echo "--- /boot/efi"; ls -la /boot/efi/EFI 2>&1 | head; echo "--- modules"; ls /lib/modules/ 2>&1; echo "--- kernel packages"; T dpkg -l 2>/dev/null | awk '/^ii/ && $2 ~ /linux-(image|headers|modules|generic|arm|agi)/ {print $2, $3}'; echo "--- grub default"; cat /etc/default/grub 2>&1; echo; for f in /etc/default/grub.d/*; do echo "## $f"; cat $f 2>&1; done; echo "--- grub.cfg"; ls -la /boot/grub/grub.cfg 2>&1; grep -nE "^(menuentry|submenu|\s+linux|set default|set timeout)" /boot/grub/grub.cfg 2>&1 | head -40; echo "--- grubenv"; cat /boot/grub/grubenv 2>&1 | grep -v '^#' | head; echo "--- efibootmgr"; T efibootmgr -v 2>&1 | head -20; echo "--- update-grub / kernelstub"; ls -la /usr/sbin/update-grub /usr/sbin/grub-mkconfig 2>&1; echo "--- kernel source hints"; ls -d /usr/src/* 2>&1 | head; ls -la /boot/vmlinuz* 2>&1; echo "--- uname version string"; cat /proc/version

sec cpufreq
d=/sys/devices/system/cpu/cpufreq; echo "policies: $(ls -d $d/policy* | wc -l)"; echo "governors: $(cat $d/policy*/scaling_governor | sort | uniq -c | tr '\n' ';')"; echo "drivers: $(cat $d/policy*/scaling_driver | sort | uniq -c | tr '\n' ';')"; echo "avail governors: $(cat $d/policy120/scaling_available_governors)"; echo "scaling min/max: $(paste -d/ $d/policy*/scaling_min_freq $d/policy*/scaling_max_freq | sort | uniq -c | tr '\n' ';')"; echo "cpuinfo min/max: $(paste -d/ $d/policy*/cpuinfo_min_freq $d/policy*/cpuinfo_max_freq | sort | uniq -c | tr '\n' ';')"; echo "global boost: $(cat $d/boost 2>&1)"; echo "policy120 boost: $(cat $d/policy120/boost 2>&1)"; echo "related/affected 120: $(cat $d/policy120/related_cpus) / $(cat $d/policy120/affected_cpus)"; echo "transition_latency: $(cat $d/policy120/cpuinfo_transition_latency 2>&1)"; echo "policy120 files: $(ls $d/policy120/ | tr '\n' ' ')"; echo "--- scaling_cur_freq samples 120-127 (3 samples 1 s apart)"; for i in 1 2 3; do for c in $(seq $R $RH); do printf '%s ' $(cat $d/policy$c/scaling_cur_freq); done; echo; sleep 1; done; echo "--- scaling_cur_freq distribution all CPUs"; cat $d/policy*/scaling_cur_freq | sort -n | uniq -c; echo "cpuinfo_cur_freq policy120: $(cat $d/policy120/cpuinfo_cur_freq 2>&1)"; echo "perms: $(ls -la $d/policy120/cpuinfo_cur_freq $d/policy120/scaling_governor 2>&1)"; echo "--- stats"; ls $d/policy120/stats 2>&1 | tr '\n' ' '; echo; cat $d/policy120/stats/time_in_state 2>&1 | head; echo "trans_table: $(head -c 300 $d/policy120/stats/trans_table 2>&1)"; echo "--- schedutil tunables"; ls $d/policy120/schedutil 2>&1; cat $d/policy120/schedutil/* 2>&1; echo "--- cpuidle"; echo "driver: $(cat /sys/devices/system/cpu/cpuidle/current_driver 2>&1) governor: $(cat /sys/devices/system/cpu/cpuidle/current_governor 2>&1) available: $(cat /sys/devices/system/cpu/cpuidle/available_governors 2>&1)"; for s in /sys/devices/system/cpu/cpu120/cpuidle/state*; do echo "$(basename $s): $(cat $s/name) desc='$(cat $s/desc)' latency=$(cat $s/latency)us residency=$(cat $s/residency)us disable=$(cat $s/disable 2>&1) usage=$(cat $s/usage) time=$(cat $s/time)us"; done; echo "--- acpi_cppc cpu120"; ls /sys/devices/system/cpu/cpu120/acpi_cppc 2>&1 | tr '\n' ' '; echo; for f in /sys/devices/system/cpu/cpu120/acpi_cppc/*; do printf '%s=%s\n' $(basename $f) "$(cat $f 2>&1)"; done; echo "--- cpu120 dir"; ls /sys/devices/system/cpu/cpu120/ 2>&1 | tr '\n' ' '; echo; echo "--- thermal"; ls /sys/class/thermal/ 2>&1 | tr '\n' ' '; echo; for t in /sys/class/thermal/thermal_zone*; do echo "$(basename $t): $(cat $t/type 2>&1) temp=$(cat $t/temp 2>&1)"; done; echo "--- hwmon"; for h in /sys/class/hwmon/hwmon*; do echo "$(basename $h): $(cat $h/name 2>&1) files: $(ls $h 2>&1 | tr '\n' ' ')"; done; echo "--- power"; ls /sys/class/power_supply /sys/class/powercap 2>&1 | tr '\n' ' '; echo; echo "--- firmware (dmi)"; for f in sys_vendor product_name product_version board_vendor board_name board_version bios_vendor bios_version bios_date; do printf '%s=%s ' $f "$(cat /sys/class/dmi/id/$f 2>&1)"; done; echo; echo "--- device-tree model"; cat /proc/device-tree/model 2>&1 | tr -d '\0'; echo; echo "--- MIDR"; grep -m1 -E 'CPU implementer|CPU part|CPU variant|CPU revision' /proc/cpuinfo; grep -E 'CPU implementer|CPU part' /proc/cpuinfo | sort | uniq -c

sec interrupts
echo "default_smp_affinity: $(cat /proc/irq/default_smp_affinity 2>&1)"; echo "irq dirs: $(ls -d /proc/irq/[0-9]* | wc -l)"; first=$(ls /proc/irq | grep -E '^[0-9]+$' | sort -n | head -1); echo "readability irq$first: smp_affinity_list=$(cat /proc/irq/$first/smp_affinity_list 2>&1) effective=$(cat /proc/irq/$first/effective_affinity_list 2>&1)"; echo "--- smp_affinity_list distribution (all IRQ dirs)"; for i in /proc/irq/[0-9]*; do cat $i/smp_affinity_list 2>/dev/null; done | sort | uniq -c | sort -rn | head -20; echo "--- effective_affinity_list distribution"; for i in /proc/irq/[0-9]*; do cat $i/effective_affinity_list 2>/dev/null; done | sort | uniq -c | sort -rn | head -20
echo "--- IRQs whose effective affinity includes any of 120-127 (irq effective_list name)"
for i in /proc/irq/[0-9]*; do e=$(cat $i/effective_affinity_list 2>/dev/null); n=$(basename $i); nm=$(ls $i 2>/dev/null | grep -vE '^(smp_affinity|smp_affinity_list|effective_affinity|effective_affinity_list|node|spurious)$' | tr '\n' ','); echo "$n $e $nm"; done | python3 -c '
import sys
def expand(s):
    r=set()
    for p in s.split(","):
        p=p.strip()
        if not p: continue
        if "-" in p:
            a,b=p.split("-"); r.update(range(int(a),int(b)+1))
        else: r.add(int(p))
    return r
hits=0; total=0
for line in sys.stdin:
    parts=line.split(None,2)
    if len(parts)<2: continue
    total+=1
    try: e=expand(parts[1])
    except Exception: continue
    if e & set(range(120,128)):
        hits+=1
        if hits<=60: print(line.rstrip())
print("TOTAL irq dirs parsed:", total, "with effective affinity touching 120-127:", hits)
'
echo "--- /proc/interrupts: per-IRQ totals and totals on CPUs 120-127 (top 45 by total)"
awk 'NR==1{for(i=1;i<=NF;i++){cpu[i]=$i}; n=NF; next} {name=$1; sub(":","",name); tot=0; hi=0; for(i=2;i<=n+1;i++){v=$i+0; tot+=v; c=cpu[i-1]; sub("CPU","",c); if(c+0>=120 && c+0<=127) hi+=v}; desc=""; for(i=n+2;i<=NF;i++) desc=desc" "$i; printf "%s total=%d on120_127=%d%s\n", name, tot, hi, desc}' /proc/interrupts | sort -t= -k2 -rn | head -45
echo "--- /proc/interrupts: entries with any count on 120-127 (all, sorted by on120_127)"
awk 'NR==1{for(i=1;i<=NF;i++){cpu[i]=$i}; n=NF; next} {name=$1; sub(":","",name); tot=0; hi=0; for(i=2;i<=n+1;i++){v=$i+0; tot+=v; c=cpu[i-1]; sub("CPU","",c); if(c+0>=120 && c+0<=127) hi+=v}; desc=""; for(i=n+2;i<=NF;i++) desc=desc" "$i; if(hi>0) printf "%s total=%d on120_127=%d%s\n", name, tot, hi, desc}' /proc/interrupts | sort -t= -k3 -rn | head -40
echo "--- interrupt deltas on 120-127 over 5 s (name delta)"
snap() { awk 'NR==1{for(i=1;i<=NF;i++){cpu[i]=$i}; n=NF; next} {name=$1; hi=0; for(i=2;i<=n+1;i++){v=$i+0; c=cpu[i-1]; sub("CPU","",c); if(c+0>=120 && c+0<=127) hi+=v}; print name, hi}' /proc/interrupts; }
A=$(snap); sleep 5; B=$(snap)
awk 'NR==FNR{a[$1]=$2; next} {d=$2-a[$1]; if(d>0) print $1, d}' <(echo "$A") <(echo "$B") | sort -k2 -rn | head -20
echo "--- per-CPU interrupt deltas 120-127 over the same 5 s (sum over all IRQ lines)"
awk 'NR==1{for(i=1;i<=NF;i++){cpu[i]=$i}; n=NF; next} {for(i=2;i<=n+1;i++){c=cpu[i-1]; sub("CPU","",c); if(c+0>=120&&c+0<=127) s[c]+=$i}} END{for(c=120;c<=127;c++) printf "cpu%d=%d ", c, s[c]; print ""}' /proc/interrupts
echo "--- softirqs totals on 120-127"
awk 'NR==1{for(i=1;i<=NF;i++){cpu[i]=$i}; n=NF; next}{name=$1; hi=0; for(i=2;i<=n+1;i++){c=cpu[i-1]; sub("CPU","",c); if(c+0>=120&&c+0<=127) hi+=$i}; print name, hi}' /proc/softirqs

sec background
echo "--- running services"; T systemctl list-units --type=service --state=running --no-pager --no-legend 2>&1 | awk '{print $1}' | tr '\n' ' '; echo; echo "--- timers (next 30)"; T systemctl list-timers --all --no-pager --no-legend 2>&1 | awk '{print $NF, $(NF-1)}' | head -30 | tr '\n' ';'; echo; echo "--- is-active"; for s in irqbalance tuned power-profiles-daemon thermald cpupower cpufrequtils ondemand unattended-upgrades apt-daily.timer apt-daily-upgrade.timer fwupd snapd cron docker containerd chrony chronyd systemd-timesyncd ntp lsfd ssh; do printf '%s=%s ' $s "$(systemctl is-active $s 2>&1)"; done; echo; echo "--- is-enabled"; for s in irqbalance tuned power-profiles-daemon unattended-upgrades apt-daily.timer apt-daily-upgrade.timer snapd docker cpufrequtils ondemand; do printf '%s=%s ' $s "$(systemctl is-enabled $s 2>&1)"; done; echo
echo "--- top processes by CPU"; ps -eo pid,psr,pcpu,pmem,rss,user,comm --sort=-pcpu | head -20
echo "--- process count by user"; ps -eo user | sort | uniq -c | sort -rn | head
echo "--- non-kernel threads currently on CPUs 120-127"; ps -eLo pid,tid,psr,pcpu,user,comm | awk '$3>=120 && $3<=127 && $5!="root"' | head -40; echo "--- all threads on 120-127 by comm (count)"; ps -eLo psr,comm | awk '$1>=120 && $1<=127 {print $2}' | sort | uniq -c | sort -rn | head -40
echo "--- rcu kernel threads"; ps -eo pid,psr,comm | grep -E ' rcu' | head -20; for p in $(ps -eo pid,comm | awk '$2 ~ /^rcu/ {print $1}' | head -6); do echo "pid $p: $(cat /proc/$p/comm) allowed=$(grep Cpus_allowed_list /proc/$p/status | awk '{print $2}')"; done
echo "--- workqueue cpumask: $(cat /sys/devices/virtual/workqueue/cpumask 2>&1)"; echo "unbound workqueues: $(ls /sys/devices/virtual/workqueue/ 2>&1 | tr '\n' ' ')"
echo "--- ksoftirqd/kworker allowed cpus sample"; for p in 2 $(pgrep ksoftirqd | head -2) $(pgrep -f 'kworker/u' | head -2) $(pgrep -f 'kworker/120' | head -2); do echo "pid $p $(cat /proc/$p/comm 2>&1): $(grep Cpus_allowed_list /proc/$p/status 2>&1 | awk '{print $2}')"; done
echo "--- containers"; T docker ps 2>&1 | head -3; T podman ps 2>&1 | head -2
echo "--- LSF / CI runners / schedulers"; pgrep -af 'lim$|sbatchd|mbatchd|jenkins|buildkite|actions.runner|Runner.Listener|gitlab-runner|slurmd|munged' 2>&1 | head; ls -d /etc/lsf* /opt/lsf* /usr/share/lsf* /opt/ibm/lsf* 2>/dev/null; echo "LSF_ENVDIR=${LSF_ENVDIR:-unset}"
echo "--- cron"; ls -la /etc/cron.d /etc/cron.daily 2>&1 | head -30; crontab -l 2>&1 | head -5
echo "--- systemd user sessions / other logged in users' processes"; loginctl list-sessions --no-legend 2>&1; ps -eo user,pid,etime,comm --sort=user | awk '$1!="root" && $1!~/^(systemd|message|dbus|syslog|_|polkit|rtkit|avahi|colord|kernoops|whoopsie|tss|snap|usbmux|uuidd|cups|lp|gdm|sddm|nobody|daemon)/' | head -40

sec cgroups
echo "cgroup fs: $(stat -fc %T /sys/fs/cgroup 2>&1)"; echo "controllers: $(cat /sys/fs/cgroup/cgroup.controllers 2>&1)"; echo "subtree_control: $(cat /sys/fs/cgroup/cgroup.subtree_control 2>&1)"; echo "root cpuset.cpus.effective: $(cat /sys/fs/cgroup/cpuset.cpus.effective 2>&1)"; echo "root cpuset.cpus.isolated: $(cat /sys/fs/cgroup/cpuset.cpus.isolated 2>&1)"; for s in system.slice user.slice init.scope machine.slice; do echo "$s: cpus='$(cat /sys/fs/cgroup/$s/cpuset.cpus 2>&1)' partition='$(cat /sys/fs/cgroup/$s/cpuset.cpus.partition 2>&1)' effective='$(cat /sys/fs/cgroup/$s/cpuset.cpus.effective 2>&1)'"; done; echo "self cgroup: $(cat /proc/self/cgroup)"; echo "self Cpus_allowed_list: $(grep Cpus_allowed_list /proc/self/status | awk '{print $2}')"; echo "systemd AllowedCPUs in config: $(grep -rE '^(AllowedCPUs|CPUAffinity)' /etc/systemd/system.conf /etc/systemd/system.conf.d/ /etc/systemd/system/ 2>/dev/null | head -5)"

sec sysctl_limits
for k in kernel.sched_rt_runtime_us kernel.sched_rt_period_us kernel.perf_event_paranoid kernel.timer_migration kernel.dmesg_restrict kernel.kptr_restrict kernel.randomize_va_space kernel.numa_balancing kernel.watchdog kernel.nmi_watchdog kernel.soft_watchdog kernel.watchdog_thresh kernel.hung_task_timeout_secs vm.stat_interval vm.swappiness vm.nr_hugepages vm.overcommit_memory kernel.sched_autogroup_enabled kernel.yama.ptrace_scope kernel.sched_schedstats; do printf '%s = %s\n' $k "$(sysctl -n $k 2>&1)"; done
echo "--- ulimit"; ulimit -a | grep -E 'real-time|locked|nice|open files|processes|stack'; echo "--- limits.conf (non-comment)"; grep -hv '^\s*#' /etc/security/limits.conf /etc/security/limits.d/* 2>/dev/null | grep -v '^\s*$'
echo "--- clocksource: $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>&1) available: $(cat /sys/devices/system/clocksource/clocksource0/available_clocksource 2>&1)"
echo "--- time sync"; T timedatectl show 2>&1 | tr '\n' ' '; echo; T chronyc tracking 2>&1 | head -6
echo "--- THP: enabled=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>&1) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag 2>&1) khugepaged_defrag=$(cat /sys/kernel/mm/transparent_hugepage/khugepaged/defrag 2>&1) ksm_run=$(cat /sys/kernel/mm/ksm/run 2>&1)"
echo "--- memory"; free -g; grep -E 'MemTotal|MemAvailable|HugePages_Total|Hugepagesize|SwapTotal' /proc/meminfo
echo "--- dmesg access: $(T dmesg 2>&1 | head -1)"; echo "--- debugfs: $(ls /sys/kernel/debug 2>&1 | head -1) tracefs: $(ls /sys/kernel/tracing 2>&1 | head -1)"
echo "--- /proc/timer_list: $(head -c 80 /proc/timer_list 2>&1 | tr '\n' ' ')"

sec tools
for t in clang clang-18 clang-17 clang-19 clang-20 clang++ gcc g++ cc c++ cmake ninja ninja-build make python3 python3.11 python3.12 python3.13 pip3 git perf taskset chrt numactl cyclictest stress-ng hwloc-ls lstopo turbostat cpupower sudo rsync tmux screen jq lld ld.lld llvm-config llvm-config-18 ccache mold curl wget docker; do printf '%-14s %s\n' $t "$(command -v $t 2>/dev/null || echo 'not in PATH')"; done
echo "--- versions"; T clang --version 2>&1 | head -1; T gcc --version 2>&1 | head -1; T cmake --version 2>&1 | head -1; echo "ninja: $(T ninja --version 2>&1)"; T python3 --version; echo "INCLUDEPY=$(python3 -c 'import sysconfig;print(sysconfig.get_config_var("INCLUDEPY"))' 2>&1) Python.h=$(ls /usr/include/python3*/Python.h 2>&1 | tr '\n' ' ')"; T git --version; echo "make: $(T make --version 2>&1 | head -1)"
echo "--- llvm/clang installs"; ls -d /usr/lib/llvm-* /opt/llvm* /opt/clang* /usr/local/llvm* /usr/local/clang* /opt/* /usr/local/bin/* 2>/dev/null | head -40; ls /usr/bin/clang* /usr/bin/ninja* /usr/bin/python3* /usr/bin/lld* 2>/dev/null | tr '\n' ' '; echo
echo "--- installed packages of interest"; T dpkg -l 2>/dev/null | awk '/^ii/ {print $2, $3}' | grep -E '^(clang|llvm|lld|ninja|cmake|python3(\.[0-9]+)?(-dev|-venv)?|python3-dev|python3-pip|python3-venv|libpython3|gcc|g\+\+|build-essential|git |rt-tests|linux-tools|hwloc|numactl|stress-ng|cpufrequtils|linux-cpupower|irqbalance|tuned|libc6-dev|libstdc\+\+)' | head -60
echo "--- apt candidates (does the apt index know them)"; for p in clang-18 ninja-build python3.11 python3.11-dev cmake rt-tests; do echo "$p: $(apt-cache policy $p 2>&1 | grep -E 'Candidate' | awk '{print $2}')"; done; echo "apt sources: $(grep -rhE '^(deb|URIs)' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null | head -5 | tr '\n' ';')"
echo "--- python modules"; for m in numpy pybind11 torch; do python3 -c "import $m; print('$m', $m.__version__)" 2>&1 | tail -1; done; pip3 --version 2>&1 | head -1; python3 -m venv --help >/dev/null 2>&1 && echo "venv ok" || echo "venv missing"; python3 -m ensurepip --version 2>&1 | tail -1

sec network_access
echo "ips: $(hostname -I 2>&1)"; ip -br addr 2>&1 | head; echo "--- routes"; ip route 2>&1 | head -5; echo "--- dns"; grep -v '^#' /etc/resolv.conf 2>&1 | head -5; echo "--- /etc/hosts matches"; grep -iE 'sw-dev|phoenix|positron|delphi|andoria' /etc/hosts 2>&1; echo "--- outbound checks (5 s timeouts)"; echo "dns github.com: $(getent hosts github.com 2>&1 | head -1)"; echo "dns pypi.org: $(getent hosts pypi.org 2>&1 | head -1)"; timeout 5 bash -c 'echo > /dev/tcp/8.8.8.8/53' 2>/dev/null && echo "tcp 8.8.8.8:53 reachable" || echo "tcp 8.8.8.8:53 unreachable"; timeout 5 bash -c 'echo > /dev/tcp/140.82.112.3/443' 2>/dev/null && echo "tcp 140.82.112.3:443 (github ip) reachable" || echo "tcp 140.82.112.3:443 unreachable"; echo "https pypi: $(timeout 8 curl -sS -o /dev/null -w '%{http_code}' https://pypi.org/simple/pip/ 2>&1 | tail -c 120)"; echo "https ubuntu archive: $(timeout 8 curl -sS -o /dev/null -w '%{http_code}' http://ports.ubuntu.com/ubuntu-ports/ 2>&1 | tail -c 120)"; echo "proxy env: $(env | grep -i proxy | tr '\n' ' ')"; echo "apt proxy: $(grep -rhi proxy /etc/apt/apt.conf /etc/apt/apt.conf.d/ 2>/dev/null | head -3 | tr '\n' ' ')"
echo "--- sshd"; grep -hiE '^(PasswordAuthentication|PubkeyAuthentication|AllowUsers|AllowGroups|Port|PermitRootLogin|KbdInteractiveAuthentication)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/* 2>&1 | sort | uniq; ls /etc/ssh/sshd_config.d/ 2>&1 | tr '\n' ' '; echo
echo "--- authorized keys ($(wc -l < ~/.ssh/authorized_keys 2>/dev/null) lines)"; awk '{print NR": "$1, substr($2,1,16)"...", $3, $4}' ~/.ssh/authorized_keys 2>&1; ls -la ~/.ssh 2>&1
echo "--- sudo: $(sudo -n true 2>&1 | head -1)"; echo "sudo -l: $(sudo -n -l 2>&1 | head -2 | tr '\n' ' ')"; echo "groups: $(groups)"; echo "sudoers.d: $(ls /etc/sudoers.d 2>&1 | tr '\n' ' ')"

sec storage
df -h / /home /tmp /var /opt /dev/shm 2>&1; echo "--- all filesystems (no tmpfs)"; df -hT 2>&1 | grep -vE 'tmpfs|efivarfs|overlay|squashfs'; echo "--- /home mount"; findmnt -no SOURCE,FSTYPE,OPTIONS /home 2>&1; findmnt -no SOURCE,FSTYPE,OPTIONS / 2>&1; echo "--- home dir"; ls -la ~ 2>&1; echo "home usage: $(du -sh ~ 2>/dev/null | cut -f1)"; ls -la ~/work 2>&1 | head -5; echo "--- quota: $(T quota -s 2>&1 | head -3 | tr '\n' ' ')"; echo "--- candidate dirs"; ls -ld /scratch /data /work /opt /mnt/* /home/* /srv 2>&1; echo "--- disks"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>&1 | head -30

sec devices
echo "--- lspci (first 40)"; T lspci 2>&1 | head -40; echo "--- lspci positron/accelerator match"; T lspci -nn 2>&1 | grep -iE 'positron|asimov|accel|processing|co-processor|1ded|fpga|xilinx|altera' ; echo "--- /dev matches: $(ls /dev/ 2>&1 | grep -iE 'asimov|positron|accel|dri|xdma|fpga' | tr '\n' ' ')"; echo "--- modules (first 40)"; lsmod 2>&1 | awk 'NR>1{print $1}' | head -60 | tr '\n' ' '; echo

sec cpu_activity
echo "--- /proc/stat per-cpu 120-127 (user nice system idle iowait irq softirq steal guest)"; grep -E '^cpu(12[0-7]) ' /proc/stat
echo "--- 5-second idle fraction for 120-127"; A=$(grep -E '^cpu(12[0-7]) ' /proc/stat); sleep 5; B=$(grep -E '^cpu(12[0-7]) ' /proc/stat); awk 'NR==FNR{for(i=2;i<=NF;i++)a[$1,i]=$i; next}{tot=0; idle=0; for(i=2;i<=NF;i++){d=$i-a[$1,i]; tot+=d; if(i==5||i==6) idle+=d}; printf "%s idle=%.1f%% busy_ticks=%d total_ticks=%d\n", $1, (tot>0?100*idle/tot:0), tot-idle, tot}' <(echo "$A") <(echo "$B")
echo "--- whole-host 5 s"; cat /proc/loadavg; echo "nr_running/procs: $(awk '/procs_running|procs_blocked|ctxt|intr /{printf "%s=%s ", $1, $2}' /proc/stat)"
echo "--- 1-second context switches and interrupts (host)"; A=$(awk '/^ctxt|^intr /{print $2}' /proc/stat | tr '\n' ' '); sleep 1; B=$(awk '/^ctxt|^intr /{print $2}' /proc/stat | tr '\n' ' '); echo "before: $A after: $B"
echo "--- sched tunables"; ls /proc/sys/kernel/ | grep sched | tr '\n' ' '; echo; echo "sched_debug: $(ls /sys/kernel/debug/sched 2>&1 | head -1)"; echo "/proc/sched_debug: $(head -c 60 /proc/sched_debug 2>&1 | tr '\n' ' ')"

sec staging_state
ls -la ~ ~/.local ~/.cache 2>&1 | head -40; echo "--- ~/.bashrc / profile customizations (non-default lines mentioning PATH/LD/clang/ninja)"; grep -hE 'PATH|LD_LIBRARY|clang|ninja|module ' ~/.bashrc ~/.profile ~/.bash_profile 2>/dev/null | grep -v '^#' | head -10; echo "--- /etc/profile.d"; ls /etc/profile.d/ 2>&1 | tr '\n' ' '; echo; echo "--- modules (environment-modules/lmod)"; command -v module 2>&1; ls /etc/modulefiles /usr/share/modulefiles /opt/modulefiles 2>&1 | head -5

sec end
date -u; echo DONE
