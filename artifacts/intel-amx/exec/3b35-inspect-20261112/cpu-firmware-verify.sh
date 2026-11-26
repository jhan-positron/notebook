#!/bin/bash
# read-only verification commands (light)
echo "## host $(hostname) date $(date -u +%FT%TZ)"
echo "## uptime"; uptime; uname -r
echo "## cmdline"; cat /proc/cmdline
echo "## ident"; grep -E '^(model name|cpu family|model|stepping|microcode)\s' /proc/cpuinfo | sort | uniq -c
echo "## microcode sysfs"; cat /sys/devices/system/cpu/cpu0/microcode/version; cat /sys/devices/system/cpu/cpu*/microcode/version | sort | uniq -c
echo "## flags count"; grep -m1 '^flags' /proc/cpuinfo | cut -d: -f2 | tr ' ' '\n' | grep -v '^$' | sort | wc -l
echo "## distinct flags lines"; grep '^flags' /proc/cpuinfo | sort | uniq -c | awk '{print $1}'
echo "## dmi"; for f in bios_vendor bios_version bios_date bios_release sys_vendor product_name product_sku product_version product_family board_vendor board_name board_version chassis_type chassis_version chassis_vendor modalias ec_firmware_release; do printf '%s=' $f; cat /sys/class/dmi/id/$f 2>&1 | od -c | head -3 | tr '\n' '|'; echo; done
echo "## cpuidle"; cat /sys/devices/system/cpu/cpuidle/current_driver /sys/devices/system/cpu/cpuidle/current_governor 2>&1
for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do echo "$(basename $s) name=$(cat $s/name) latency=$(cat $s/latency) residency=$(cat $s/residency) disable_cpu0=$(cat $s/disable) default_status=$(cat $s/default_status 2>/dev/null) usage=$(cat $s/usage) time=$(cat $s/time)"; done
for n in 0 1 2 3 4; do echo "state$n disable counts: $(cat /sys/devices/system/cpu/cpu*/cpuidle/state$n/disable 2>/dev/null | sort | uniq -c | tr '\n' ' ')"; done
echo "## pm_qos"; ls -la /dev/cpu_dma_latency; cat /sys/devices/system/cpu/cpu0/power/pm_qos_resume_latency_us; cat /sys/devices/system/cpu/cpu*/power/pm_qos_resume_latency_us | sort | uniq -c
echo "## intel_idle params"; cat /sys/module/intel_idle/parameters/* 2>&1; grep -H . /sys/module/intel_idle/parameters/* 2>&1
echo "## cpufreq"; cat /sys/devices/system/cpu/cpufreq/policy0/scaling_driver; cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c; cat /sys/devices/system/cpu/cpufreq/policy*/energy_performance_preference 2>/dev/null| sort | uniq -c; cat /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_max_freq | sort | uniq -c; cat /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_min_freq | sort | uniq -c; cat /sys/devices/system/cpu/cpufreq/policy*/scaling_max_freq | sort | uniq -c;cat /sys/devices/system/cpu/cpufreq/policy*/scaling_min_freq | sort | uniq -c; cat /sys/devices/system/cpu/cpufreq/policy*/base_frequency 2>/dev/null | sort | uniq -c
grep -H . /sys/devices/system/cpu/intel_pstate/* 2>&1
echo "## epb"; cat /sys/devices/system/cpu/cpu*/power/energy_perf_bias 2>/dev/null | sort | uniq -c
echo "## smt/online"; cat /sys/devices/system/cpu/smt/control /sys/devices/system/cpu/smt/active /sys/devices/system/cpu/online /sys/devices/system/cpu/isolated /sys/devices/system/cpu/possible
echo "## numa"; for n in /sys/devices/system/node/node*; do echo "$(basename $n) $(cat $n/cpulist)"; done
echo "## lscpu"; lscpu | grep -Ev '^Flags'
echo "## lscpu -C"; lscpu -C
echo "## uncore"; ls /sys/devices/system/cpu/intel_uncore_frequency/ 2>&1 | head; for d in /sys/devices/system/cpu/intel_uncore_frequency/*/; do echo "$d $(grep -H . $d/* 2>/dev/null | sed 's|.*/||' | tr '\n' ' ')"; done 2>/dev/null | head -20
echo "## who sets idle"; systemctl is-active tuned 2>&1; ls /etc/systemd/system | grep -iE 'idle|cstate|c6|perf|tune' ; ls /etc/tmpfiles.d /etc/udev/rules.d 2>/dev/null
echo "## vulnerabilities"; grep -H . /sys/devices/system/cpu/vulnerabilities/* | sed 's|.*/||'
echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled
echo "## amx sysfs / xstate"; grep -o 'amx[a-z0-9_]*' /proc/cpuinfo | sort | uniq -c
echo "## mhz now (cpuinfo)"; awk -F: '/^cpu MHz/{s+=$2;n++; if($2>m)m=$2} END{print "avg",s/n,"max",m,"n",n}' /proc/cpuinfo
