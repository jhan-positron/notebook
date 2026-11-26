#!/bin/bash
# read-only collection for the cpu-firmware dimension
D=/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112
H=$(hostname -s)
P=$D/cpu-firmware-$H
{ date -u; uptime; uname -r; } > $P-uptime.txt 2>&1
lscpu > $P-lscpu.txt 2>&1
lscpu -C > $P-lscpu-C.txt 2>&1
lscpu -e=CPU,NODE,SOCKET,CORE,ONLINE,MAXMHZ,MINMHZ > $P-lscpu-e.txt 2>&1
grep -m1 '^flags' /proc/cpuinfo | cut -d: -f2 | tr ' ' '\n' | grep . | sort > $P-flags.txt
grep -m1 '^bugs' /proc/cpuinfo > $P-bugs.txt
grep -m1 '^vmx flags' /proc/cpuinfo | cut -d: -f2 | tr ' ' '\n' | grep . | sort > $P-vmxflags.txt
grep -E '^(microcode|model name|cpu family|model|stepping|address sizes)' /proc/cpuinfo | sort | uniq -c > $P-cpuinfo-ident.txt
{ for f in online offline possible present isolated; do echo "$f: $(cat /sys/devices/system/cpu/$f 2>&1)"; done
  echo "smt/active: $(cat /sys/devices/system/cpu/smt/active 2>&1)"; echo "smt/control: $(cat /sys/devices/system/cpu/smt/control 2>&1)"
  for n in /sys/devices/system/node/node*; do echo "$(basename $n) cpulist: $(cat $n/cpulist)  distance: $(cat $n/distance)  $(grep MemTotal $n/meminfo)"; done
  echo "cmdline: $(cat /proc/cmdline)"
  echo "microcode sysfs cpu0: $(cat /sys/devices/system/cpu/cpu0/microcode/version 2>&1)"
  echo "cpufreq cpu0: driver=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>&1) gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>&1) max=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq 2>&1) min=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq 2>&1) base=$(cat /sys/devices/system/cpu/cpu0/cpufreq/base_frequency 2>&1)"
  echo "governors: $(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c | tr '\n' ' ')"
  echo "intel_pstate: status=$(cat /sys/devices/system/cpu/intel_pstate/status 2>&1) no_turbo=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>&1)"
} > $P-topology.txt 2>&1
{ for f in bios_vendor bios_version bios_date bios_release ec_firmware_release product_name product_version product_family product_sku board_name board_version board_vendor sys_vendor chassis_type chassis_vendor chassis_version modalias; do echo "$f: $(cat /sys/class/dmi/id/$f 2>&1)"; done; } > $P-dmi.txt
grep -r . /sys/devices/system/cpu/vulnerabilities/ > $P-vulnerabilities.txt 2>&1
{ echo "which cpuid: $(which cpuid 2>&1)"; echo "which ipmitool: $(which ipmitool 2>&1)"; echo "which dmidecode: $(which dmidecode 2>&1)"; ls -l /dev/cpu/0/cpuid /dev/ipmi0 2>&1; echo "sudo -n true: $(sudo -n true 2>&1; echo rc=$?)"
  ls /sys/class/ipmi/ 2>&1; for f in /sys/class/ipmi/ipmi0/device/bmc/{firmware_revision,ipmi_version,manufacturer_id,product_id,aux_firmware_revision}; do echo "$f: $(cat $f 2>&1)"; done; } > $P-tools.txt 2>&1
python3 - > $P-cpuid.txt 2>&1 <<'PY'
import struct,os
def cpuid(leaf,sub,cpu=0):
    fd=os.open('/dev/cpu/%d/cpuid'%cpu,os.O_RDONLY)
    try: return struct.unpack('<4I',os.pread(fd,16,(sub<<32)|leaf))
    finally: os.close(fd)
try:
    for l,s in [(0,0),(1,0),(7,0),(7,1),(7,2),(0xd,0),(0xd,1),(0xd,17),(0xd,18),(0x1d,0),(0x1d,1),(0x1e,0),(0x1e,1),(0x16,0),(0x24,0)]:
        a,b,c,d=cpuid(l,s); print('leaf 0x%x sub %d: eax=%08x ebx=%08x ecx=%08x edx=%08x'%(l,s,a,b,c,d))
    a,b,c,d=cpuid(7,1); print('AMX-FP16 CPUID(7,1).EAX[21] =',(a>>21)&1); print('AMX-COMPLEX CPUID(7,1).EDX[8] =',(d>>8)&1)
    a,b,c,d=cpuid(7,0); print('AMX-BF16 (7,0).EDX[22]=%d AMX-TILE EDX[24]=%d AMX-INT8 EDX[25]=%d'%((d>>22)&1,(d>>24)&1,(d>>25)&1))
except Exception as e: print('ERROR',repr(e))
PY
which cpuid >/dev/null 2>&1 && cpuid -1 -r > $P-cpuid-tool-raw.txt 2>&1
echo done $H
