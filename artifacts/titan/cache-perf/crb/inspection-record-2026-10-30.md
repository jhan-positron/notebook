# CRB inspection record — 2026-10-30

Scope: read-only inspection of CRB (ssh jhan@192.168.2.45). No benchmark, perf run beyond one `perf stat -e cycles true`, or write was performed on CRB. Benchmarks are blocked until the user approves a sharing policy.

Source note: the `local-tooling` probe text supplied to this step was truncated after its item 6a (Asimov notes grep). Section 7 covers only items 1-5 of that probe. Section 8 was filled by a local read-only grep run in this step.

## 1. Machine identity

| Item | Value | Supporting command |
|---|---|---|
| Hostname | `ubuntu` | [`ssh jhan@192.168.2.45 'hostname'`] |
| Kernel | `7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 #1 SMP PREEMPT`, built 2026-09-16 by avadnaik@2paltra-216, gcc-14; stock `6.8.0-147` kernel also in /boot | [`uname -a; ls /boot; dmesg \| grep 'Linux version'`] |
| OS | Ubuntu 24.04.5 LTS | [`cat /etc/issue`] |
| Firmware/boot | EFI v2.7 by EDK II, ACPI (OEM ID ARMLTD), no device tree | [`dmesg \| grep -E 'efi:\|ACPI:'; ls /proc/device-tree` (absent)] |
| System vendor / product | Arm Limited / Phoenix Reference Server / family AGI-CPU-CRB / version EVT0 | [`cat /sys/class/dmi/id/{sys_vendor,product_name,product_family,product_version}`] |
| Board | Quanta Computer Inc. / Motherboard / A1DI0 | [`cat /sys/class/dmi/id/{board_vendor,board_name,board_version}`] |
| BIOS | Arm Limited AGI-CPU-CRB-v0.7.2, 2026-09-08 | [`cat /sys/class/dmi/id/{bios_vendor,bios_version,bios_date}`] |
| CPU implementer / part / variant / revision | 0x41 / 0xd83 / 0x0 / 2 (r0p2), identical on all 128 CPUs | [`grep -E 'implementer\|part\|variant\|revision' /proc/cpuinfo \| sort \| uniq -c`] |
| MIDR_EL1 / REVIDR_EL1 | 0x00000000410fd832 / 0x1f | [`cat /sys/devices/system/cpu/cpu0/regs/identification/{midr_el1,revidr_el1}`] |
| Public-table name | Part 0xd83 is labelled `ARM_CPU_PART_NEOVERSE_V3AE` in the Linux kernel header table on CRB (three header trees). No firmware, dmesg, lscpu (`Model name: -`) or gcc (`-mcpu=native` empty) output prints a product name. Keep MIDR 0x410fd832 as the primary identifier. | [`grep -n -i 0xd83 /usr/src/linux-headers-*/arch/arm64/include/asm/cputype.h; lscpu; gcc -mcpu=native -Q --help=target \| grep mcpu`] |
| Core count | 128 CPUs online (0-127), 1 socket, 1 thread per core (no SMT), 128 single-CPU clusters, physical_package_id 36 on all | [`nproc --all; cat /sys/devices/system/cpu/online; lscpu; cat /sys/devices/system/cpu/cpu*/topology/cluster_id \| sort -n \| uniq -c`] |
| Frequencies | min 1,600,000 kHz (1.6 GHz), max 2,800,000 kHz (2.8 GHz), scaling_cur_freq 2,800,000 kHz on all 128, cpuinfo_avg_freq 2,797,265 kHz, boost=0 (disabled) | [`cat /sys/devices/system/cpu/cpu0/cpufreq/{cpuinfo_min_freq,cpuinfo_max_freq,scaling_cur_freq,cpuinfo_avg_freq}; cat /sys/devices/system/cpu/cpufreq/boost`] |
| Governor / driver | `performance` on all 128 (kernel cmdline `cpufreq.default_governor=performance`), driver `cppc_cpufreq`, one policy per CPU | [`cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor \| sort \| uniq -c; cat .../scaling_driver; cat /proc/cmdline`] |
| cpuidle | current_driver = `none`; cpu0/cpuidle directory absent. Meaning: Linux does not request firmware-defined idle states. (Verifier correction: this does not prove cores never enter a low-power state; the default idle path still executes WFI.) | [`cat /sys/devices/system/cpu/cpuidle/current_driver; ls /sys/devices/system/cpu/cpu0/cpuidle`] |
| CPU features of note | sve, sve2, svebf16, i8mm, bf16, ls64, rng, bti, ecv, afp, wfxt, MPAM, PMUv3, SPE | [`head -12 /proc/cpuinfo; dmesg \| grep 'CPU features'`] |
| Kernel-flagged errata | `Broken broadcast TLBI completion`, `SSBS not fully self-synchronizing` | [`dmesg \| grep 'CPU features'`] |
| Uptime | 8 days 11 h since reboot 2026-10-22 05:43 UTC | [`uptime; last reboot \| head -5`] |

## 2. Cache hierarchy

All values from sysfs (kernel's parse of ACPI PPTT); cpu0, cpu1, cpu64, cpu127 identical except private-cache ids. [`for d in /sys/devices/system/cpu/cpu0/cache/index*; do cat $d/{level,type,size,ways_of_associativity,number_of_sets,coherency_line_size,shared_cpu_list,allocation_policy,write_policy,id}; done`]

| Level | Type | Size per instance | Instances | Ways | Line | Sets | Sharing | Alloc / write policy | Arithmetic check |
|---|---|---|---|---|---|---|---|---|---|
| L1d (index0) | Data | 64 KiB | 128 | 4 | 64 B | 256 | private, 1 CPU | ReadWriteAllocate / WriteBack | 64x4x256 = 65,536 B |
| L1i (index1) | Instruction | 64 KiB | 128 | 4 | 64 B | 256 | private, 1 CPU | ReadAllocate / WriteBack | 64x4x256 = 65,536 B |
| L2 (index2) | Unified | 2 MiB (2048 KiB) | 128 | 8 | 64 B | 4096 | private, 1 CPU (128 distinct shared_cpu_list values) | ReadWriteAllocate / WriteBack | 64x8x4096 = 2,097,152 B |
| L3 (index3) | Unified | 128 MiB (131072 KiB) | 1 (id=1) | 16 | 64 B | 131072 | CPUs 0-127 on every CPU | ReadWriteAllocate / WriteBack | 64x16x131072 = 134,217,728 B |

Totals per lscpu: L1d 8 MiB (128 instances), L1i 8 MiB (128), L2 256 MiB (128), L3 128 MiB (1). [`lscpu; lscpu -C`]

Extra facts:
- `physical_line_partition` does not exist for any index. [`cat .../index*/physical_line_partition`]
- I-cache is PIPT on all CPUs. [`dmesg \| grep 'Detected PIPT'`]
- PPTT puts every CPU in its own cluster (128 clusters), so no multi-core DSU-style cluster is described. [`cat /sys/devices/system/cpu/cpu*/topology/cluster_cpus_list \| sort -u \| wc -l`]
- core_id values are non-sequential (cpu0=2, cpu127=137; cluster_id step 48). Hypothesis (verifier): these are PPTT byte offsets; cannot verify because PPTT is root-only. [`cat /sys/devices/system/cpu/cpu{0,127}/topology/core_id`]

L4 / system-level cache / memory-side cache:
- sysfs: no index4 on any CPU; cpu0/cache holds index0..index3 only. So firmware describes exactly three cache levels. [`ls /sys/devices/system/cpu/cpu0/cache/; ls -d /sys/devices/system/cpu/cpu*/cache/index4` (No such file)]
- PMU: two `arm_cmn` devices (ARMHC003:00/:01, driver arm-cmn, identifier `43e05`) each export 545 events including `hns_slc_*`, `hns_sf_*`, `hns_cache_fill_*`, `hns_cache_miss_*`. The presence of SLC (system level cache) and SF (snoop filter) event names shows the CMN home nodes carry a system-level cache. [`ls /sys/bus/event_source/devices/arm_cmn_0/events \| grep -E 'hns_(slc\|sf\|cache)'; cat /sys/bus/event_source/devices/arm_cmn_0/identifier`]
- Hypothesis: the sysfs "L3" (128 MiB, shared by all 128 CPUs) is the CMN SLC. No readable output states this literally. Confirming measurement: compare `armv8_pmuv3_0/ll_cache_rd` against `arm_cmn/hns_slc_sf_cache_access_all` under a controlled load (needs CAP_PERFMON or root).
- DT/ACPI: no device tree; PPTT (17,024 bytes) is mode 0400 root-only, so its raw cache tree cannot be dumped. HMAT and MPAM tables absent. [`ls -l /sys/firmware/acpi/tables/PPTT; ls /sys/firmware/acpi/tables`]
- No `arm_dsu*` PMU device. `arm_dsu_pmu.ko` exists on disk as a module but is not loaded. [`ls /sys/bus/event_source/devices \| grep dsu; lsmod \| grep dsu; modinfo -n arm_dsu_pmu`]
- CMN mesh dimensions, number of SLC slices, HN-S/SN-F/CCG node counts: Insufficient data. Resolved by `cat /sys/kernel/debug/arm-cmn/*` as root (debugfs is Permission denied for jhan). [`ls /sys/kernel/debug`]

## 3. DRAM

| Item | Value | Supporting command |
|---|---|---|
| MemTotal | 329,332,576 kB (314.1 GiB visible to kernel); boot log: 334,981,392 kB present, 5,677,856 kB reserved | [`grep MemTotal /proc/meminfo; dmesg \| grep 'Memory:'`] |
| Installed | 10 DIMMs x 32,768 MB = 327,680 MB (320 GiB); 10/10 slots populated | [`cat /sys/devices/system/edac/mc/mc0/size_mb; for d in .../mc0/dimm*; do cat $d/size; done; dmesg \| grep 'Memory slots'`] |
| DIMM labels | two labelled banks of five: DIMM_BANK_CP0 (DIMM_CP0_0..4), DIMM_BANK_CP1 (DIMM_CP1_0..4). "CP" is not expanded anywhere readable. Channel count is NOT implied by these labels (verifier correction). | [`for d in /sys/devices/system/edac/mc/mc0/dimm*; do cat $d/dimm_label $d/dimm_location; done`] |
| DIMM type / device type / speed | mem_type=Unknown, dev_type=Unknown; speed not exported | [`cat .../dimm0/{dimm_mem_type,dimm_dev_type}`] |
| ECC | SECDED, ce_count=0, ue_count=0; EDAC provider is ghes_edac (firmware-first) | [`cat .../dimm*/dimm_edac_mode; cat .../mc0/mc_name; dmesg \| grep ghes_edac`] |
| NUMA | 1 node (node0), CPUs 0-127, 321,613 MB, SLIT distance 10, one memory tier | [`numactl -H; cat /sys/devices/system/node/node0/{cpulist,distance}`] |
| SRAT | single PXM 0; RAM range 0x2009cc00000-0x2507fffffff; 128 MPIDR entries 0x20000..0x230000 step 0x10000 | [`dmesg \| grep -E 'SRAT\|NUMA:'`] |
| Zones | one zone (DMA): 83,745,348 pages present (319.5 GiB), 82,333,144 managed (314.1 GiB) | [`grep -E '^Node\|present\|managed' /proc/zoneinfo`] |
| Memory blocks | block_size 0x8000000 (128 MiB); 2557 blocks (319.6 GiB) | [`cat /sys/devices/system/memory/block_size_bytes; ls /sys/devices/system/memory \| grep -c memory`] |
| Hugetlb | HugePages_Total 0; default 2048 kB; sizes supported: 64 KiB, 2 MiB, 32 MiB, 1 GiB | [`grep -i huge /proc/meminfo; ls /sys/kernel/mm/hugepages/`] |
| THP | enabled=[always], defrag=[madvise]; CONFIG_TRANSPARENT_HUGEPAGE_ALWAYS=y. Meaning: anonymous benchmark buffers get 2 MiB pages by default. | [`cat /sys/kernel/mm/transparent_hugepage/{enabled,defrag}; grep THP /boot/config-$(uname -r)`] |
| NUMA balancing | CONFIG_NUMA_BALANCING_DEFAULT_ENABLED=y (single node, so no migration target) | [`grep NUMA_BALANCING /boot/config-$(uname -r)`] |
| HMAT bandwidth/latency | NONE. No HMAT in /sys/firmware/acpi/tables, `dmesg \| grep -ic hmat` = 0, no node0/access* directories. Firmware provides no DRAM latency or bandwidth numbers. | [`ls /sys/firmware/acpi/tables; dmesg \| grep -i -c hmat; ls -d /sys/devices/system/node/node0/access*`] |
| Swap | none | [`cat /proc/swaps`] |
| Free at inspection | MemFree 276,592,496 kB (263 GiB), MemAvailable 325,048,236 kB (310 GiB) | [`grep -E 'MemFree\|MemAvailable' /proc/meminfo`] |
| Memory controller device | no platform device named ddr/dmc/mem; 40 `arm_cspmu_mc_*` PMUs exist with empty events dir ("mc" is the APMT node name) | [`ls /sys/bus/platform/devices \| grep -iE 'ddr\|dmc\|mem'; ls /sys/bus/event_source/devices \| grep -c arm_cspmu_mc`] |

Not obtainable without root:
- DDR generation, MT/s, manufacturer, part number (SMBIOS type 17): `/sys/firmware/dmi/tables/smbios_entry_point` Permission denied; `/sys/firmware/dmi/entries` absent (CONFIG_DMI_SYSFS off). [`dmidecode -t 17; ls /sys/firmware/dmi/entries`]
- Memory channel count: no readable source. Needs `sudo dmidecode -t 17` or vendor documentation.
- Physical address ranges in /proc/iomem (zeroed for non-root). [`head -40 /proc/iomem`]
- Raw SRAT/SLIT/APMT/DSDT contents (mode 0400). [`ls -l /sys/firmware/acpi/tables`]

## 4. PMUs

Inventory (105 entries under /sys/bus/event_source/devices). [`ls /sys/bus/event_source/devices; for d in ...; do cat $d/type $d/cpumask; ls $d/events \| wc -l; done`]

| PMU | Count | perf type | cpumask | Named events | Identifier | Notes |
|---|---|---|---|---|---|---|
| armv8_pmuv3_0 | 1 | 11 | 0-127 | 73 | (none) | 6 programmable counters + cycle counter (`7 (0,8000003f)`) [`dmesg \| grep 'hw perfevents'`] |
| arm_cmn_0 / arm_cmn_1 | 2 | 9 / 10 | 0 | 545 each | 43e05 | ACPI ARMHC003, driver arm-cmn; prefixes: 294 hns, 74 mxp, 37 ccha, 26 ccra, 26 dn, 22 rnid, 19 hni, 18 sbsx, 15 hnp, 11 ccla, 2 watchpoint, 1 dtc |
| arm_cspmu_mc_* | 40 (0-45 minus 10,11,22,23,34,35) | 30-69 | 0 (mc_0..21), 64 (mc_24..45) | 0 (empty) | 9c30043b | from APMT, driver arm-cs-arch-pmu; format event/filter/filter2/filter3 |
| arm_bmu_* | 38 (0-39 minus 5,11) | 70-107 | 0 | none (no dir) | 9c30043b | ACPI ARMHB001, driver arm-bmu; raw config only |
| arm_spe_0 | 1 | 109 | 0-127 | n/a | | SPEv1.2, max_record_sz 64 [`dmesg \| grep spe`] |
| smmuv3_pmcg_* | 18 | 12-29 | 1 | cycles, tlb_miss, transaction, ... | | |
| cs_etm, breakpoint, software, tracepoint, uprobe | | 108, 5, 1, 2, 8 | | | | |
| arm_dsu* | 0 | | | | | module on disk, not loaded |

Example events:
- Core: `l1d_cache l1d_cache_refill l1d_cache_lmiss_rd l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_lmiss_rd l2d_cache_wb l3d_cache l3d_cache_refill l3d_cache_lmiss_rd ll_cache_rd ll_cache_miss_rd mem_access remote_access bus_access bus_cycles stall_backend_mem dtlb_walk l1d_tlb_refill l2d_tlb_refill`. [`ls /sys/bus/event_source/devices/armv8_pmuv3_0/events`]
- CMN: `hns_cache_fill_{all,rnf,rni,hbt,lbt,ccgrn,ccglcn}`, `hns_cache_miss_all` (type=0x200,eventid=0x1), `hns_slc_sf_cache_access_all`, `hns_slc_eviction_*`, `hns_sf_hit_*`, `hns_mc_reqs_local_{all,home,sn}`, `hns_mc_reqs_remote_*`, `hns_pocq_reqs_recvd_{read,write,...}`, `mxp_{n,s,e,w,p0,p1}_{req,rsp,snp,dat}_txflit_{valid,stall}`, `sbsx_rd_req`, `sbsx_wr_req`, `dtc_cycles`. [`ls /sys/bus/event_source/devices/arm_cmn_0/events`]

Access:
- `perf_event_paranoid=2`, `kptr_restrict=1`. Meaning: an unprivileged user may count user-mode events on own processes only; kernel-mode and all system-wide (uncore) PMUs need root or CAP_PERFMON. [`cat /proc/sys/kernel/{perf_event_paranoid,kptr_restrict}`]
- Unprivileged perf works: `perf stat -e cycles true` exit 0, 113,023 cycles:u (probe) / 97,659 cycles:u (verifier rerun), about 0.4 ms wall; event auto-restricted to `:u`; bare `cycles` also matched `smmuv3_pmcg_1c0030/cycles/` (not supported), so pin events to `armv8_pmuv3_0/.../`. [`perf stat -e cycles true`]
- perf version 7.1.3.g4dbc8bb88858 matches kernel; `perf list` prints 1755 lines including metric groups (Branch_Effectiveness, Cycle_Accounting, DTLB_Effectiveness, ...). [`perf --version; perf list \| wc -l; perf list metricgroup`]
- Kernel config: CONFIG_ARM_CMN=y, CONFIG_ARM_PMUV3=y, CONFIG_ARM_DSU_PMU=m, CONFIG_ARM_SPE_PMU=m, CONFIG_ARM_CORESIGHT_PMU_ARCH_SYSTEM_PMU=y, CONFIG_ARM_SMMU_V3_PMU=y, CONFIG_PREEMPT=y, CONFIG_HZ=250, CONFIG_ARM64_PA_BITS=52. [`grep -E 'CONFIG_ARM_CMN\|CONFIG_ARM_DSU_PMU\|...' /boot/config-$(uname -r)`]

## 5. Toolchain on CRB

| Tool | Status | Supporting command |
|---|---|---|
| gcc / g++ / cc | gcc (Ubuntu 14.2.0-4ubuntu2~24.04.1) 14.2.0 | [`gcc --version`] |
| gcc -march=native | `armv8-a+rng+flagm+lse+dotprod+rdma+crc+fp16fml+rcpc+i8mm+bf16+sve2-aes+sve2-bitperm+sve2-sha3+sve2-sm4+sb+pauth`; `-mcpu=native` resolves to empty (core unknown to gcc 14.2) | [`gcc -march=native -Q --help=target \| grep -E 'march\|mcpu'`] |
| clang / clang++ | absent | [`which clang`] |
| make / cmake / git / perl | present; ninja absent | [`which make cmake ninja git perl`] |
| python3 | 3.12.3, pip3 and venv present, numpy absent system-wide | [`python3 --version; python3 -c 'import numpy'`] |
| perf | /usr/bin/perf, version 7.1.3 | [`which perf; perf --version`] |
| numactl | 2.0.18 present | [`which numactl; dpkg -l \| grep numactl`] |
| sysbench / stress-ng | 1.0.20 / 0.17.06 present | [`dpkg -l \| grep -E 'sysbench\|stress-ng'`] |
| hwloc (hwloc-ls, lstopo, hwloc-info) | absent | [`which hwloc-ls lstopo hwloc-info`] |
| likwid (perfctr, bench, topology) | absent | [`which likwid-perfctr likwid-bench likwid-topology`] |
| lmbench / lat_mem_rd / bw_mem / tinymembench / stream / mlc | absent | [`which lmbench lat_mem_rd bw_mem tinymembench stream mlc`] |
| environment modules | absent | [`which module; module avail`] |
| sudo | jhan is in group 27(sudo), but `sudo -n true` -> "a password is required" (exit 1). No passwordless sudo. | [`id; sudo -n true`] |
| $HOME | /home/jhan on local NVMe ext4, 1.7 TB free, dotfiles only; /dev/shm 158 GB tmpfs | [`df -h $HOME /dev/shm; stat -f -c %T $HOME; ls -la $HOME`] |
| /opt | /opt/arm-svk (local-packages/, toolchains/, root-owned, 2026-09-29) | [`ls /opt /opt/arm-svk`] |

Consequence: a latency/bandwidth microbenchmark must be compiled from source with gcc 14.2 on CRB. Nothing was built.

## 6. Sharing constraints

- Accounts: arm (uid 1000), positron-perf (uid 1001, GECOS "SDK performance tests"), jhan (uid 1002). Home dirs mode 750. [`awk -F: '$3>=1000' /etc/passwd; ls -la /home`]
- Logins since 2026-09-29: arm 15 sessions (last 2026-10-22 00:51), "positron" 5 sessions (last 2026-10-23 22:17; `last` truncates to 8 characters, so very likely positron-perf, not literally shown), jhan 6. Nobody but jhan since 2026-10-23. [`last -n 30; last \| awk '{print $1}' \| sort \| uniq -c`]
- At inspection (2026-10-30 17:22 UTC): jhan only user, load average 0.00/0.00/0.00, no process above 0.1 % CPU, zero processes owned by arm or positron-perf. [`who; w; ps -eo user,pid,pcpu,comm --sort=-pcpu \| head; ps -eo user \| grep -c -E 'positron\|arm'`]
- sysstat history 2026-10-22..10-30: minimum %idle per day 98.46, 98.45, 92.90, 98.38, 100.00, 92.21, 93.78, 83.07, 96.49. Busiest: 2026-10-23 13:10-14:50 UTC (about 17 % user, roughly 21 of 128 CPUs), 2026-10-28 12:10-13:00 UTC (5-6 % nice). Who ran them: not recorded. [`sar -u -f /var/log/sysstat/saNN`]
- Running services: stock Ubuntu only (cron, ssh, rsyslog, smartmontools, unattended-upgrades, udisks2, ModemManager, polkit, systemd-*). No CI runner, docker, podman, k3s, kubelet, slurm. [`systemctl list-units --type=service --state=running; which docker podman k3s kubelet slurmd srun sinfo`]
- Timers: sysstat-collect every 10 min, sysstat-summary daily 00:07. [`systemctl list-timers`]
- cron: no jhan crontab; /etc/cron.d has e2scrub_all and sysstat only. [`crontab -l; ls -la /etc/cron.d`]
- cgroup: session at `/user.slice/user-1002.slice/session-NNNN.scope`; memory.max=max at all levels; cpu and cpuset controllers not enabled below root; root cpuset.cpus.effective=0-127. No cgroup CPU or memory limit on jhan. [`cat /proc/self/cgroup; cat /sys/fs/cgroup/cpuset.cpus.effective; cat /sys/fs/cgroup/user.slice/memory.max`]
- Why nproc=120: PID 1 and every descendant have Cpus_allowed_list 0-119, set by `/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf` (root, 28 bytes, 2026-10-22 05:34): `[Manager]` / `CPUAffinity=0-119`. Kernel cmdline: `isolcpus=domain,managed_irq,126-127 irqaffinity=0-119`. So: CPUs 0-119 usable by logins; 120-125 online, not isolated, IRQ-free, outside inherited affinity; 126-127 scheduler-isolated. Purpose of 120-127 is not documented. [`nproc; grep Cpus_allowed_list /proc/self/status /proc/1/status; cat /etc/systemd/system.conf.d/60-positron-cpuaffinity.conf; cat /proc/cmdline; cat /sys/devices/system/cpu/isolated`]
- Thermal: no thermal_zone entries; hwmon0/hwmon1 are bnxt_en (NIC) only. CPU temperature not readable from userspace. [`ls /sys/class/thermal; cat /sys/class/hwmon/hwmon*/name`]
- motd/policy: no /etc/motd, /etc/issue = "Ubuntu 24.04.5 LTS", stock update-motd.d, no README or .md policy file in /, /opt, /opt/*, /home/*. [`cat /etc/motd /etc/issue; ls /etc/update-motd.d; ls /*.md /opt/*/README* /home/*/README*`]
- Reboots: 2026-09-29, 10-03, 10-05, 10-20, 10-22 (five in 31 days, no visible schedule). [`last reboot \| head -5`]
- journal: not readable by jhan (not in adm/systemd-journal); dmesg readable. [`journalctl -n 1; dmesg \| head -2`]
- ulimits: open files 1024, stack 8192 kB, max locked memory 41,166,572 kB, max user processes 1,286,820. [`ulimit -a`]

## 7. Local tooling (this x86_64 host)

- Host: x86_64, 32 logical CPUs, gcc 11.4.0 (Ubuntu 22.04), clang absent. A local native build produces x86_64 binaries that cannot run on CRB. [`uname -m; nproc; gcc --version; clang --version`]
- aarch64 cross compiler: none (no aarch64-linux-gnu-gcc, no gcc-aarch64-linux-gnu package). [`which aarch64-linux-gnu-gcc; dpkg -l \| grep -i aarch64`]
- docker/podman: absent; binfmt_misc empty; qemu-aarch64 absent. No emulation or container path for arm64 builds. [`which docker podman qemu-aarch64; ls /proc/sys/fs/binfmt_misc/`]
- Benchmark sources on disk: none (lmbench, tinymembench, likwid, STREAM, pmbw, membench, mlc not found under ~/workspace depth 4 or locate). [`find ~/workspace -maxdepth 4 -type d -iname '*lmbench*' ...; locate -i lmbench`]
- Working dir ~/workspace/titan/cache-perf: empty, owned by root, created 2026-10-30 10:05. Writes may need a permission change. [`ls -la ~/workspace/titan/cache-perf`]
- Local tools: numactl, hwloc-ls, lstopo, lscpu, make 4.3, cmake present; perf, likwid, mlc, stream absent. [`which perf numactl hwloc-ls lstopo lscpu likwid-perfctr mlc stream make cmake`]
- Internet: github.com reachable (HTTP/2 200); pip 22.0.2 / Python 3.10. Fetching benchmark sources later is feasible. [`curl -sI --max-time 8 https://github.com \| head -1; pip3 --version`]
- Practical build path: write C source locally, copy to CRB, compile with CRB's gcc 14.2 (needs user approval to write under /home/jhan on CRB).

## 8. Asimov context notes found locally

Source directory: /home/jhan/workspace/notebook/artifacts/asimov-spec-study (README.md, spm-meta-data-model.md, sal/spm/svl-c1nano-software-view.html, spm-meta-data-structure.svg). [`ls ~/workspace/notebook/artifacts/asimov-spec-study; grep -ril -E 'dsu\|on-chip\|ocm\|sram' ...`]

- Topology: "DSU x5 — RN-F", "2x C1-Nano per DSU", "shared L2 / L3, 2x128b VPU", "CME 'Griffin' (SME2), 1 per DSU" [spm-c1nano-software-view.html:196-201; sal-c1nano-software-view.html:164-166]. Note: this contradicts the user's description ("L1 shared between 2 cores, L2 and L3 private"); which is right needs the Asimov spec or the box itself.
- SLC: "SLC 5 MiB · RN-F x5 (DSUs)" on the CMN [spm-c1nano-software-view.html:209].
- On-chip memory: per-DSU ACP target select "A=OCM, B=DRAM"; `cfg_acp_ocm_base[core_idx]` for 10 cores (`core_idx = 2*acp_dsu_sel + acp_core_sel`) [spm-meta-data-model.md:67,147-149].
- SPM (vector memory): 16 MiB, slave on CMN via four 256-bit AXI4 ports, "Aggregate bandwidth is 256 GB/s", 4 CMN DMA engines [spm-c1nano-software-view.html:316].
- ACP stash path: SPM delivers 46-byte records as two 32 B ACP writes into one 64 B slot, "already stashed in that core's L2" [spm-meta-data-model.md:22; svl-c1nano-software-view.html:279].
- Access details for the Asimov box: not in these notes; user said they will come from Jesse.

## 9. Verifier contradictions and corrections (verbatim)

Contradictions:
1. "dram probe 'Device tree' item quotes \"ls: cannot access '/sys/firmware/devicetree': No such file or directory\", while the cpu-cache probe item 9 says '/sys/firmware/devicetree: empty directory'. Re-run: '/sys/firmware/devicetree' exists and is an empty directory (drwxr-xr-x, total 0). The cpu-cache probe is right; the dram probe's quoted output does not match the box (likely a transcription error of the /proc/device-tree line)."
2. "cpu-cache probe item 6 states the mechanism setting the 0-119 affinity 'was not identified' and labels it a hypothesis, while the sharing probe item 4 identifies it as /etc/systemd/system.conf.d/60-positron-cpuaffinity.conf with CPUAffinity=0-119. Re-run confirms the sharing probe; the cpu-cache hypothesis is resolved, not contradicted in fact."
3. "cpu-cache probe item 2 says the 0xD83 define is in 'both the running 7.1.3 kernel's headers and the stock Ubuntu 6.8.0-147 headers' (two trees). Re-run shows three header trees match (6.8.0-147, 6.8.0-147-generic, 7.1.3-arm-agi). Count differs; content identical."

Corrections:
1. Claim: "No cpuidle driver ('none'), so cores do not enter deep idle states." Corrected: "The output only shows that no cpuidle driver is registered with the kernel. It does not show what power state a core enters when idle (the arm64 default idle path still executes WFI, and firmware may act on that). 'Cores do not enter deep idle states' is an inference beyond the output; state it as 'no cpuidle driver is registered, so Linux does not request firmware-defined idle states'."
2. Claim: the CPU 'is' Neoverse V3AE. Corrected: "The literal on-box identifier is MIDR 0x410fd832 (implementer 0x41, part 0xd83, r0p2). The product name comes only from the Linux kernel header's part-number table; no firmware, dmesg, lscpu or gcc output on CRB prints a product name. Phrase it as 'part 0xd83, which the Linux cputype.h table labels ARM_CPU_PART_NEOVERSE_V3AE', and keep the MIDR as the primary identifier."
3. Claim: core_id values 'means PPTT node offsets'. Corrected: "The non-sequential ids are an observation. That they are PPTT byte offsets is a plausible hypothesis consistent with the regular step of 48 in cluster_id, but it cannot be verified without reading the PPTT, which is root-only. Label as hypothesis."
4. Claim: arm_cmn identifier 'is the CMN periph-id/part value'; two CMNs 'suggest a two-die/two-mesh part, matching the two DIMM banks CP0/CP1'. Corrected: "The output literally gives two PMU devices named arm_cmn_0 and arm_cmn_1 with identifier string '43e05'. What the identifier encodes, and whether two CMN PMUs imply two dies or two meshes, is not stated by any readable output. The probe already labels the two-die statement as inference; the periph-id statement should carry the same label. The link to the DIMM labels CP0/CP1 is unsupported (ghes_edac reports mem_type and dev_type 'Unknown', and 'CP' is never expanded anywhere readable)."
5. Claim: 'positron' in last output 'is most likely the positron-perf account'. Corrected: "The probe already marks this 'not confirmed'. Keep it that way: 'last' truncates usernames to 8 characters, and positron-perf is the only account whose name starts with 'positron', so the mapping is very likely but not literally shown."
6. Claim: 'The CP0/CP1 naming suggests two groups of 5 channels'. Corrected: "The labels show two groups of five DIMM slots. 'Channels' is not supported: a slot label does not say how many memory channels each group has or whether 'CP' means channel, controller or something else. Say 'two labelled banks of five DIMMs each' and leave channel count as not obtainable without root (dmidecode) or vendor documentation."

Note on the uncore probe: it states "Per the public Linux driver drivers/perf/arm-cmn.c, part 0x43e is PART_CMN_S3". That is an external-source claim not checked on the box; treat as hypothesis until the driver source is read.

## 10. Open questions for the user (deduplicated)

Writes and runs on CRB:
1. May we create a working directory under /home/jhan on CRB (source, binary, logs)? Yes/No.
2. May we run a single-core pointer-chase latency sweep (under 60 s) on CRB once the policy is confirmed? Yes/No.
3. May we run an all-core STREAM-style bandwidth sweep (a few minutes, tens of GiB allocated, up to 120 threads)? Yes/No.
4. Is pinning our own threads with taskset/numactl (no /sys change) acceptable? Yes/No.

CPU placement:
5. Should the benchmark stay inside CPUs 0-119, or also use reserved CPUs 120-127 via sched_setaffinity? Choice: 0-119 only / include 120-127.

Coordination:
6. Who owns accounts `arm` and `positron-perf`, and is there a channel or calendar to announce a benchmark window? (single answer: name/channel)
7. Should we ask the admin whether unattended-upgrades could run during the window, or accept the risk? Choice: ask / accept.

Privileged data (one-time, by someone with root):
8. Can an admin run `sudo dmidecode -t 17` once and share the output (DDR type, MT/s, part numbers)? Yes/No.
9. Can an admin either lower perf_event_paranoid to 0 or -1, grant CAP_PERFMON to jhan, or run the uncore counter collection (`perf stat -e arm_cmn/hns_slc_sf_cache_access_all/`) and `cat /sys/kernel/debug/arm-cmn/*` as root? Choice: lower paranoid / CAP_PERFMON / root-run / none (user-mode counters only).
10. Should the admin load `arm_dsu_pmu` (needs root)? Yes/No.
11. Is a spec sheet for the Phoenix Reference Server (AGI-CPU-CRB, Quanta A1DI0) available internally for channel count and DDR speed? Yes/No.

Reporting:
12. May the report cite the Linux cputype.h header label `ARM_CPU_PART_NEOVERSE_V3AE` for part 0xd83, or should it use the hex identifier only? Choice: cite header / hex only.