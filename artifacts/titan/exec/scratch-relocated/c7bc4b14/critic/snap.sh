export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0
date -u; cat /proc/loadavg
echo '--- who'; who
echo '--- last 8'; last -n 8 -F 2>&1 | head -9
echo '--- accounts'; getent passwd jhan arm positron-perf; getent group sudo adm
echo '--- state'; cat /proc/cmdline; echo "isolated='$(cat /sys/devices/system/cpu/isolated)'"; cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c | tr '\n' ' '; echo
ls -la --time-style=full-iso /etc/sudoers.d/ /etc/default/grub.d/ 2>&1
echo '--- timers/services'; for u in apt-daily.timer apt-daily-upgrade.timer fwupd-refresh.timer netperf.service snapd.socket sysstat-collect.timer; do printf '%s=%s ' $u "$(systemctl is-active $u 2>&1)"; done; echo
echo '--- rcu knobs'; ls -l /sys/kernel/rcu_normal /sys/kernel/rcu_expedited 2>&1; echo "rcu_normal=$(cat /sys/kernel/rcu_normal 2>&1) rcu_expedited=$(cat /sys/kernel/rcu_expedited 2>&1)"
echo '--- linux-tools ownership'; stat -c '%U:%G %a %n' /usr/bin/cpupower /usr/bin/perf /usr/sbin/bpftool /usr/libexec/cpupower /usr/lib/systemd/system/cpupower.service /etc/cpupower-service.conf /usr/lib/libcpupower.so.1.0.1 2>&1
dpkg -s linux-tools 2>/dev/null | grep -E '^(Package|Version|Maintainer)'
echo '--- files owned by uid 1001 outside /home (count, then top dirs, then anything root might execute)'
timeout 20 find /usr /etc /lib /opt /var /boot -xdev -user positron-perf 2>/dev/null > /tmp/.uid1001.$$ ; wc -l < /tmp/.uid1001.$$
sed 's|/[^/]*$||' /tmp/.uid1001.$$ | sort | uniq -c | sort -rn | head -12
grep -E '^/(etc|usr/lib/systemd|lib/systemd|usr/lib/udev|etc/cron|usr/sbin|usr/bin|usr/libexec)' /tmp/.uid1001.$$ | head -30
rm -f /tmp/.uid1001.$$
echo '--- sudoers hint for the account'; sudo -n -l 2>&1 | head -2
echo '--- perf-lane layout present?'; ls -d ~/positron/artifacts ~/positron/work/sdk-v2 ~/positron/fetchcontent ~/positron/perf-lane.lock 2>&1
echo '--- ctest/pytest artefacts under ~/positron'; find ~/positron -maxdepth 4 \( -iname 'LastTest.log' -o -iname '*ctest*' -o -iname '*pytest*' -o -iname 'CTestTestfile.cmake' \) 2>/dev/null | head -5
echo '--- README gate lines'; grep -n -E 'compile-0\.8b|count only from the perf host' ~/positron/src/phoenix-int/tools/conformance/README.md | cut -c1-260
date -u
