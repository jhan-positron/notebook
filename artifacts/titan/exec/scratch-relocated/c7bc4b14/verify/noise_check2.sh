#!/bin/bash
# Read-only verification, round 2. No writes, no sudo, no settings changed. One 4 s single-CPU spin at most.
export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0 PAGER=cat
T() { timeout 15 "$@" 2>&1; }
sec() { printf '\n=== %s ===\n' "$1"; }
sec date; date -u; cat /proc/loadavg

sec sysstat_why
T systemctl cat sysstat-collect.service | grep -E '^(ExecStart|Environment|EnvironmentFile|Description)'
T systemctl cat sysstat.service 2>&1 | grep -E '^(ExecStart|Description|ConditionPath)'
echo "--- /etc/default/sysstat (non-comment)"; grep -vE '^\s*#|^\s*$' /etc/default/sysstat
echo "--- debian-sa1 head"; sed -n 1,25p /usr/lib/sysstat/debian-sa1
echo "--- sa files newest"; ls -la --time-style=full-iso /var/log/sysstat | tail -3
echo "--- sar per-CPU 120-127 around Jeremy's job (sa21, 18:20-18:50 UTC), %user %system %idle"
T sar -f /var/log/sysstat/sa21 -P 122,124,127 -s 18:20:00 -e 18:50:00 2>&1 | head -24

sec arm_sessions
who -u 2>&1
T last -n 6 -F arm 2>&1 | head -8

sec user_timer
T systemctl --user cat launchpadlib-cache-clean.timer 2>&1 | grep -vE '^\s*#|^\s*$'
T systemctl --user show launchpadlib-cache-clean.timer -p TimersMonotonic -p TimersCalendar -p Persistent -p RandomizedDelayUSec 2>&1 | tr '\n' ' '; echo
T systemctl --user cat launchpadlib-cache-clean.service 2>&1 | grep -E '^ExecStart'

sec sdk_source
sed -n 22,31p /home/positron-perf/positron/src/phoenix-int/tools/perf/host_facts.sh | cut -c1-200
S=/home/positron-perf/positron/src/phoenix-int
echo "--- null_timing.cpp around the FakeDevice construction (poll_ns argument)"
grep -nE 'poll|Poll|kSpinNs|FakeDevice\(|fake_device' $S/backends/null_timing/null_timing.cpp 2>&1 | head -12 | cut -c1-220
echo "--- fake_device.cpp sleep/poll lines"; grep -nE 'poll_ns|nanosleep|sleep_for|sleep_until|clock_nanosleep|wait_for|wait_until' $S/backends/null_timing/fake_device.cpp 2>&1 | head -12 | cut -c1-220
echo "--- timed waits in runtime/ and tools/harness (count per file)"
T grep -rlE 'wait_for\(|wait_until\(|sleep_for\(|sleep_until\(|nanosleep\(|clock_nanosleep\(|FUTEX_WAIT|poll\(|epoll_wait\(|timerfd' $S/runtime $S/tools/harness $S/backends --include='*.cpp' --include='*.h' --include='*.c' 2>/dev/null | head -20
echo "--- the lines (first 25)"
T grep -rnE 'wait_for\(|wait_until\(|sleep_for\(|sleep_until\(|nanosleep\(|clock_nanosleep\(|FUTEX_WAIT|epoll_wait\(|timerfd' $S/runtime $S/tools/harness $S/backends --include='*.cpp' --include='*.h' --include='*.c' 2>/dev/null | head -25 | cut -c1-230

sec flush_kworkers
ps -o pid,lstart,etime,psr,comm -p 14638,30692,31738 2>&1
echo "--- job python3 pid 14570 start (if still alive) / adjacent pids"; ps -o pid,lstart,etime,psr,comm -p 14570,14474 2>&1

sec exp_gp_ipi_check
ipi1() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1=="IPI1:"{print $(k+1)}' /proc/interrupts; }
tick() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1=="12:"{print $(k+1)}' /proc/interrupts; }
load=$(cut -d' ' -f1 /proc/loadavg); jobs=$(ps -u positron-perf -o comm= | grep -vcE '^(sshd|bash|systemd|\(sd-pam\)|ps|grep|awk|cut|sleep|timeout|cat)$')
echo "guard: load1=$load foreign_positron_perf_procs=$jobs"
if awk -v l="$load" 'BEGIN{exit !(l<0.5)}' && [ "$jobs" -eq 0 ]; then
  echo "unshare test (unprivileged user+mount namespace, torn down at exit): $(timeout 5 unshare -Urm true 2>&1; echo rc=$?)"
  a=$(ipi1 121); t0=$(tick 121); taskset -c 121 timeout 4 bash -c 'while :; do :; done'; b=$(ipi1 121); t1=$(tick 121)
  echo "control spin 4 s on cpu121: IPI1_delta=$((b-a)) arch_timer_delta=$((t1-t0))"
  a=$(ipi1 121); t0=$(tick 121); taskset -c 121 timeout 4 bash -c 'while :; do :; done' & sleep 1; for i in 1 2 3; do timeout 5 unshare -Urm true 2>/dev/null; sleep 0.3; done; wait; b=$(ipi1 121); t1=$(tick 121)
  echo "spin 4 s on cpu121 with 3x 'unshare -Urm true' from another CPU: IPI1_delta=$((b-a)) arch_timer_delta=$((t1-t0))"
  a=$(ipi1 121); sleep 3; b=$(ipi1 121); echo "idle cpu121 3 s: IPI1_delta=$((b-a))"
else
  echo "skipped spin: host not idle"
fi

sec end; date -u; cat /proc/loadavg; echo DONE
