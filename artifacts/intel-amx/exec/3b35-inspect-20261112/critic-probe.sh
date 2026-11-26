#!/bin/bash
# read-only probe, light
echo "## host"; hostname; date -u; cat /proc/loadavg
echo "## flags amx/xsave/split"; grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^(amx|xsave|xfd|xgetbv|split_lock|bus_lock|avx512_fp16|avx512_bf16|avx512_vnni|avx_vnni|tme|pconfig|la57|hfi|ibt|user_shstk|cat_|cqm|mba|rdt_a|cdp|sgx|tdx|arch_lbr|serialize|tsxldtrk|waitpkg|pku|ospke)' | sort | tr '\n' ' '; echo
echo "## bugs"; grep -m1 '^bugs' /proc/cpuinfo
echo "## vulnerabilities"; grep -H . /sys/devices/system/cpu/vulnerabilities/* 2>&1
echo "## L3 topology"; for c in 0 71 72 143; do echo "cpu$c L3 shared_cpu_list=$(cat /sys/devices/system/cpu/cpu$c/cache/index3/shared_cpu_list) size=$(cat /sys/devices/system/cpu/cpu$c/cache/index3/size) L2=$(cat /sys/devices/system/cpu/cpu$c/cache/index2/size) L1d=$(cat /sys/devices/system/cpu/cpu$c/cache/index0/size)"; done
echo "distinct L3 groups: $(cat /sys/devices/system/cpu/cpu*/cache/index3/shared_cpu_list | sort -u | wc -l)"
echo "## acpi_cppc"; for c in 0 7 24 54 72 100; do echo -n "cpu$c: "; for f in highest_perf nominal_perf lowest_nonlinear_perf lowest_perf guaranteed_perf nominal_freq reference_perf; do echo -n "$f=$(cat /sys/devices/system/cpu/cpu$c/acpi_cppc/$f 2>&1) "; done; echo; done
echo "highest_perf histogram:"; cat /sys/devices/system/cpu/cpu*/acpi_cppc/highest_perf 2>&1 | sort -n | uniq -c
echo "guaranteed_perf histogram:"; cat /sys/devices/system/cpu/cpu*/acpi_cppc/guaranteed_perf 2>&1 | sort -n | uniq -c
echo "nominal_perf histogram:"; cat /sys/devices/system/cpu/cpu*/acpi_cppc/nominal_perf 2>&1 | sort -n | uniq -c
echo "## cpufreq base/max histogram"; cat /sys/devices/system/cpu/cpu*/cpufreq/base_frequency 2>&1 | sort -n | uniq -c; cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq | sort -n | uniq -c; cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq | sort -n | uniq -c;  cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq | sort -n | uniq -c
echo "## intel_pstate"; grep -H . /sys/devices/system/cpu/intel_pstate/* 2>&1
echo "## platform_profile"; cat /sys/firmware/acpi/platform_profile 2>&1; cat /sys/firmware/acpi/pm_profile 2>&1
echo "## acpi tables"; ls /sys/firmware/acpi/tables 2>&1 | tr '\n' ' '; echo
echo "## split lock / bus lock"; cat /proc/sys/kernel/split_lock_mitigate 2>&1; grep -o 'split_lock_detect[^ ]*' /proc/cmdline
echo "## memory tiering / CXL / demotion"; ls /sys/bus/cxl/devices 2>&1 | head; cat /sys/kernel/mm/numa/demotion_enabled 2>&1; cat /proc/sys/kernel/numa_balancing 2>&1; ls /sys/devices/system/node | grep -c '^node[0-9]'
echo "## THP / ksm"; cat /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag /sys/kernel/mm/ksm/run 2>&1
echo "## scheduler knobs"; for f in sched_autogroup_enabled sched_rt_runtime_us sched_cfs_bandwidth_slice_us timer_migration numa_balancing watchdog nmi_watchdog perf_event_paranoid kptr_restrict randomize_va_space sched_energy_aware sched_schedstats; do echo "$f=$(cat /proc/sys/kernel/$f 2>&1)"; done
for f in /sys/kernel/debug/sched/features; do cat $f 2>&1 | head -2; done
echo "## isolated/nohz"; grep -H . /sys/devices/system/cpu/{isolated,nohz_full,offline,online,possible,smt/control,smt/active} 2>&1
echo "## resctrl"; mount | grep resctrl; ls /sys/fs/resctrl 2>&1 | head -20
echo "## cgroup cpuset for user"; cat /proc/self/cgroup; cat /proc/self/status | grep -E 'Cpus_allowed_list|Mems_allowed_list'
echo "## ulimits"; ulimit -a 2>&1 | grep -E 'locked|open files|processes|stack|core file'
echo "## xstate via cpuid python present?"; ls /proc/sys/abi 2>&1; 
echo "## arch_prctl xstate perm"; python3 - <<'PY'
import ctypes,os
libc=ctypes.CDLL(None,use_errno=True)
v=ctypes.c_ulong(0)
for name,code in (("ARCH_GET_XCOMP_SUPP",0x1021),("ARCH_GET_XCOMP_PERM",0x1022)):
    r=libc.syscall(158,code,ctypes.byref(v))
    print(name,"ret",r,"mask",hex(v.value),"XTILEDATA(bit18)",(v.value>>18)&1,"XTILECFG(bit17)",(v.value>>17)&1)
PY
echo "## journal xstate (may be denied)"; journalctl -k -b --no-pager 2>&1 | grep -i -E 'xstate|x86/fpu|split lock|tsx|microcode' | head -20; journalctl -k -b --no-pager 2>&1 | head -2
echo "## dmesg"; dmesg 2>&1 | head -2
echo "## hwmon fans/power"; for h in /sys/class/hwmon/hwmon*; do echo "$h $(cat $h/name 2>/dev/null)"; done | head -40
echo "## glibc / tunables"; ldd --version | head -1; echo "GLIBC_TUNABLES=$GLIBC_TUNABLES"
echo "## os release"; grep -E 'PRETTY_NAME|VERSION_ID' /etc/os-release
echo "## kernel config amx/tsx related"; grep -E 'CONFIG_X86_INTEL_TSX_MODE|CONFIG_HZ=|CONFIG_PREEMPT_DYNAMIC|CONFIG_NO_HZ_FULL=|CONFIG_X86_SGX=|CONFIG_INTEL_TDX|CONFIG_TRANSPARENT_HUGEPAGE_MADVISE|CONFIG_NUMA_BALANCING_DEFAULT' /boot/config-$(uname -r) 2>&1
echo "## preempt mode"; cat /sys/kernel/debug/sched/preempt 2>&1
echo "## irqbalance / tuned / services"; systemctl is-active irqbalance tuned thermald power-profiles-daemon numad 2>&1 | tr '\n' ' '; echo
echo "## SNC hint: node count per package"; grep -H . /sys/devices/system/node/node*/cpulist; cat /sys/devices/system/cpu/cpu0/topology/{physical_package_id,die_id,die_cpus_list} 2>&1
echo "## perf AMX event sysfs"; ls /sys/devices/cpu/events 2>&1 | tr '\n' ' '; echo; cat /sys/devices/cpu/caps/pmu_name 2>&1
echo "## KVM / VMs"; lsmod | grep -E '^kvm|^msr|^intel_rapl|^isst|^intel_uncore|^tpmi|^intel_sdsi|^pfr|^idxd|^qat' ; pgrep -c qemu
