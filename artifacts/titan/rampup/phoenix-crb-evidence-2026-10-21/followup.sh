#!/bin/bash
export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0 PAGER=cat
T() { timeout 20 "$@" 2>&1; }
sec() { printf '\n=== %s ===\n' "$1"; }
sec date; date -u

sec home_positron
ls -la ~/positron; echo "--- du per entry"; du -sh ~/positron/* 2>/dev/null; echo "--- depth-2 listing (dirs only)"; find ~/positron -maxdepth 2 -type d 2>/dev/null | head -60; echo "--- top-level files in ~/positron and README/run scripts"; find ~/positron -maxdepth 2 -type f \( -iname 'README*' -o -iname '*.md' -o -iname '*.sh' -o -iname '*.toml' -o -iname '*.yaml' -o -iname '*.yml' -o -iname 'CMakeLists.txt' -o -iname 'pyproject.toml' -o -iname 'environment*.yml' \) 2>/dev/null | head -40; echo "--- git repos"; for d in ~/positron/*/; do [ -d "$d/.git" ] && echo "$d: $(git -C "$d" remote get-url origin 2>&1) @ $(git -C "$d" rev-parse --short HEAD 2>&1) ($(git -C "$d" log -1 --format=%cd --date=short 2>&1))"; done; echo "--- newest 15 files under ~/positron"; find ~/positron -type f -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort -r | head -15

sec conda_mamba
ls -la ~/.conda ~/.mamba 2>&1; cat ~/.conda/environments.txt 2>&1; echo "--- envs"; ls ~/.mamba/envs 2>&1; for e in ~/.mamba/envs/* ~/positron/*/.venv ~/positron/*/venv; do [ -d "$e" ] && echo "$e: clang=$(ls $e/bin/clang* 2>/dev/null | head -3 | tr '\n' ' ') ninja=$(ls $e/bin/ninja 2>/dev/null) cmake=$(ls $e/bin/cmake 2>/dev/null) python=$($e/bin/python --version 2>&1)"; done; echo "--- micromamba/mamba/conda binaries"; command -v micromamba mamba conda 2>&1; ls ~/bin ~/.local/bin 2>&1 | head; find ~ -maxdepth 3 -type f \( -name micromamba -o -name mamba -o -name conda \) 2>/dev/null | head; echo "--- pip cache size"; du -sh ~/.cache/pip ~/.cache/conda 2>/dev/null

sec toolchain_profile
cat /etc/profile.d/99-gcc14-arm-agi-cpu-toolchain.sh 2>&1; echo "--- /opt/arm-svk"; ls -la /opt/arm-svk 2>&1 | head -20; find /opt/arm-svk -maxdepth 2 2>/dev/null | head -40; echo "--- /usr/lib/llvm-18"; ls -la /usr/lib/llvm-18 /usr/lib/llvm-18/bin 2>&1 | head -20; echo "--- llvm/clang packages"; dpkg -l 2>/dev/null | awk '/^ii/ {print $2, $3}' | grep -iE 'llvm|clang'

sec cpufreq_extra
d=/sys/devices/system/cpu/cpufreq/policy120; for f in cpuinfo_avg_freq auto_select auto_act_window energy_performance_preference_val perf_limited freqdomain_cpus scaling_setspeed; do printf '%s: perms=%s value=%s\n' $f "$(stat -c %a $d/$f 2>&1)" "$(cat $d/$f 2>&1)"; done; echo "cpu_capacity cpu0=$(cat /sys/devices/system/cpu/cpu0/cpu_capacity) cpu120=$(cat /sys/devices/system/cpu/cpu120/cpu_capacity)"; echo "sched_energy_aware=$(cat /proc/sys/kernel/sched_energy_aware)"; echo "acpi_cppc perms: $(stat -c '%a %n' /sys/devices/system/cpu/cpu120/acpi_cppc/feedback_ctrs)"
echo "--- 3 s pinned spin on CPU 121 (schedutil): delivered clock from CPPC feedback counters"
fb() { cat /sys/devices/system/cpu/cpu$1/acpi_cppc/feedback_ctrs; }
echo "idle cpu121 before: fb=$(fb 121) scaling_cur=$(cat /sys/devices/system/cpu/cpufreq/policy121/scaling_cur_freq) avg=$(cat /sys/devices/system/cpu/cpufreq/policy121/cpuinfo_avg_freq 2>&1)"
A=$(fb 121); A_t=$(date +%s.%N)
taskset -c 121 timeout 3 bash -c 'while :; do :; done' 2>/dev/null
B=$(fb 121); B_t=$(date +%s.%N)
echo "after spin: fb=$B scaling_cur=$(cat /sys/devices/system/cpu/cpufreq/policy121/scaling_cur_freq) avg=$(cat /sys/devices/system/cpu/cpufreq/policy121/cpuinfo_avg_freq 2>&1)"
python3 - "$A" "$B" "$A_t" "$B_t" <<'PY'
import sys,re
a,b,ta,tb=sys.argv[1:5]
def p(s):
    m=re.search(r'ref:(\d+)\s+del:(\d+)',s); return int(m.group(1)),int(m.group(2))
ra,da=p(a); rb,db=p(b); dr=rb-ra; dd=db-da; dt=float(tb)-float(ta)
ref_perf=50; nominal_perf=140; nominal_mhz=2800
print(f"delta ref={dr} delta del={dd} wall={dt:.2f}s")
if dr>0:
    delivered_perf=ref_perf*dd/dr
    print(f"delivered perf = {delivered_perf:.1f} units -> est. {delivered_perf*nominal_mhz/nominal_perf:.0f} MHz (reference counter rate est. {dr/dt/1e6:.1f} MHz)")
PY
echo "--- sampled scaling_cur_freq on cpu121 during a second 3 s spin (10 samples)"
( taskset -c 121 timeout 3 bash -c 'while :; do :; done' & ) ; for i in $(seq 1 10); do printf '%s ' "$(cat /sys/devices/system/cpu/cpufreq/policy121/scaling_cur_freq)"; sleep 0.3; done; echo; sleep 0.5
echo "--- 3 s spin on CPU 122 with before/after cpuinfo_avg_freq only"; echo "before: $(cat /sys/devices/system/cpu/cpufreq/policy122/cpuinfo_avg_freq 2>&1)"; taskset -c 122 timeout 3 bash -c 'while :; do :; done'; echo "after: $(cat /sys/devices/system/cpu/cpufreq/policy122/cpuinfo_avg_freq 2>&1) scaling_cur=$(cat /sys/devices/system/cpu/cpufreq/policy122/scaling_cur_freq)"

sec dmesg_greps
T dmesg 2>&1 | grep -iE 'NO_HZ|nohz|rcu:|isolcpus|Unknown kernel command line|Kernel command line|cppc|cpufreq|scmi|arch_timer|psci|cpuidle|LPI|idle states|Performance Events|PMU|SPE|GICv3|CPU features|boot CPU|MIDR|smp: Brought up|Linux version' | head -60

sec services_detail
echo "--- netperf.service"; T systemctl cat netperf.service 2>&1 | head -25; T systemctl show netperf.service -p ExecStart -p ActiveEnterTimestamp 2>&1; echo "--- smartmontools"; grep -vE '^\s*#|^\s*$' /etc/smartd.conf 2>&1 | head -5; grep -hE 'interval|-i ' /etc/default/smartmontools 2>&1 | head; echo "--- sysstat"; cat /etc/cron.d/sysstat 2>&1 | grep -v '^#'; T systemctl cat sysstat-collect.timer 2>&1 | grep -E 'OnCalendar|Accuracy'; echo "--- apt timers"; T systemctl cat apt-daily.timer apt-daily-upgrade.timer 2>&1 | grep -E 'OnCalendar|Randomized|Persistent'; echo "--- unattended-upgrades config"; grep -hE 'Automatic-Reboot|Unattended-Upgrade "|Package-Blacklist|Update-Package-Lists' /etc/apt/apt.conf.d/20auto-upgrades /etc/apt/apt.conf.d/50unattended-upgrades 2>&1 | grep -v '^//' | head -12; echo "--- fstrim timer"; T systemctl cat fstrim.timer 2>&1 | grep -E 'OnCalendar|Accuracy|Randomized'; echo "--- next timer firings (UTC)"; T systemctl list-timers --no-pager 2>&1 | head -25; echo "--- apt history: kernel installs"; grep -hE 'Start-Date|linux-image' /var/log/apt/history.log 2>&1 | grep -B1 'linux-image' | head -20; echo "--- dpkg log kernel installs"; grep -hE 'install linux-image|upgrade linux-image' /var/log/dpkg.log* 2>&1 | head -10; echo "--- journal boots"; ls /var/log/journal 2>&1 | head -3; T journalctl --list-boots --no-pager 2>&1 | head -8
echo "--- sudoers.d listing"; ls -la /etc/sudoers.d/ 2>&1; echo "--- password for positron-perf set? (passwd -S)"; T passwd -S 2>&1

sec perf_rt_checks
echo "perf stat as user: $(T perf stat -e task-clock,cycles,instructions true 2>&1 | grep -E 'cycles|instructions|not supported|Permission' | head -3 | tr '\n' ';')"; echo "chrt -f 1 test: $(T chrt -f 1 true 2>&1 | head -1; echo rc=$?)"; echo "rtprio hard limit: $(ulimit -H -r)"; echo "nice hard limit: $(ulimit -H -e)"; echo "memlock hard: $(ulimit -H -l)"; echo "clock_gettime resolution: $(python3 -c 'import time;print(time.get_clock_info("monotonic"))')"; echo "cntfrq: $(T dmesg 2>&1 | grep -iE 'arch_timer.*(MHz|Hz)' | head -2 | tr '\n' ';')"

sec sw_dev_01_from_host
echo "dns sw-dev-01: $(getent hosts sw-dev-01 2>&1 | head -1)"; grep -iE 'sw-dev' /etc/hosts ~/.ssh/config 2>&1 | head -3

sec end; date -u; echo DONE
