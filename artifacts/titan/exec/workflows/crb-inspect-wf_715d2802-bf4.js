export const meta = {
  name: 'crb-inspect',
  description: 'Read-only inspection of CRB (ARM64 server) cache/memory hierarchy, toolchain, and sharing constraints',
  phases: [
    { title: 'Inspect', detail: 'parallel read-only ssh probes of CRB + local toolchain check' },
    { title: 'Verify', detail: 'cross-check key facts' },
    { title: 'Synthesize', detail: 'merge into one inspection record' },
  ],
}

const RULES = `
HARD RULES (shared machine, user said "do not change anything on CRB, feel free to inspect"):
- Run ONLY read-only commands on CRB. Do NOT create, write, touch, mkdir, redirect to, or modify ANY file on CRB, not even in /tmp or $HOME. Do NOT install packages. Do NOT run sudo. Do NOT run any benchmark or CPU-heavy program on CRB. Do NOT change cpufreq, governors, sysctl, or anything in /sys or /proc.
- Access: ssh -o BatchMode=yes jhan@192.168.2.45 '<cmd>'  (key auth works; the box hostname is "ubuntu", kernel 7.1.3-arm-agi, Ubuntu 24.04, aarch64, 128 CPUs, 320 GB RAM).
- Commands that may need root: run them, note "permission denied" as a fact, move on. Never retry with sudo.
- Keep each ssh invocation short and bounded (use head/timeout). Do not run anything that could hang (no interactive tools).
- Return RAW FACTS with the exact command and its output excerpt. Mark anything you could not obtain as "not obtainable without root" or "tool absent". Do not guess values. Do not infer micro-architecture names unless an identifier (MIDR/implementer/part number, device-tree compatible string, dmesg line) literally says so; quote the identifier.
`

const FACTS = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'object', properties: {
      topic: { type: 'string' },
      command: { type: 'string' },
      output_excerpt: { type: 'string' },
      interpretation: { type: 'string' },
    }, required: ['topic', 'command', 'output_excerpt', 'interpretation'] } },
    blocked: { type: 'array', items: { type: 'string' }, description: 'things not obtainable and why' },
    questions_for_user: { type: 'array', items: { type: 'string' } },
  },
  required: ['facts', 'blocked', 'questions_for_user'],
}

const PROBES = [
  { key: 'cpu-cache', prompt: `${RULES}
TASK: Determine the CPU identity and the exact cache geometry of CRB.
Collect:
1. /proc/cpuinfo first block (CPU implementer, CPU architecture, CPU variant, CPU part, CPU revision) and count distinct 'CPU part' values across all CPUs.
2. /sys/devices/system/cpu/cpu0/regs/identification/midr_el1 and revidr_el1 if present. Decode implementer and part number in hex (do NOT name a product unless you can cite a well-known table and say you are citing it; give the hex).
3. For cpu0 AND cpu1 AND cpu64: every /sys/devices/system/cpu/cpuN/cache/index*/{level,type,size,ways_of_associativity,number_of_sets,coherency_line_size,shared_cpu_list,allocation_policy,write_policy}. Note which indexes are shared with which CPUs (this answers whether L2 is private, and how L3 is shared).
4. /sys/devices/system/cpu/cpu0/topology/{core_siblings_list,cluster_cpus_list,package_cpus_list,core_id,cluster_id,physical_package_id} and the same for a few other cpus to see cluster structure (DSU/clusters).
5. cpufreq: /sys/devices/system/cpu/cpu0/cpufreq/{scaling_governor,scaling_cur_freq,cpuinfo_min_freq,cpuinfo_max_freq,scaling_driver,scaling_available_governors} and whether governor differs across cpus (uniq over all cpus).
6. Why does 'nproc' report 120 while lscpu reports 128 online? Check: taskset -p $$ , cat /proc/self/status | grep -i cpus_allowed, cat /sys/fs/cgroup/cpuset.cpus.effective and /sys/fs/cgroup/user.slice/cpuset.cpus.effective, ulimit -a. Report which CPUs are allowed for an interactive ssh session as jhan. Also check /proc/cmdline for isolcpus/nohz_full/rcu_nocbs.
7. lscpu -e=CPU,CORE,SOCKET,CLUSTER,NODE,L1d,L1i,L2,L3 | head -20 and | tail -5.
8. dmesg | grep -i -E 'cache|cpu|dsu|cmn|neoverse|cortex' | head -40 (may be permission denied; note it). Also check /sys/kernel/debug access (likely denied).
9. /proc/device-tree: ls /proc/device-tree; cat /proc/device-tree/compatible and /proc/device-tree/model (tr '\\0' ' '); ls /proc/device-tree/cpus | head; and find any cache-related nodes (find /proc/device-tree -maxdepth 3 -iname '*cache*' | head). If ACPI instead of DT: ls /sys/firmware/acpi/tables and note PPTT presence (PPTT describes cache topology); do NOT try to dump tables if it needs root.
Return all facts with commands and excerpts.` },

  { key: 'dram', prompt: `${RULES}
TASK: Determine CRB's DRAM configuration: channels, speed, type, capacity, NUMA, and any memory-controller identifiers.
Collect:
1. /proc/meminfo (MemTotal, Hugepagesize, HugePages_Total, Transparent hugepage settings: /sys/kernel/mm/transparent_hugepage/{enabled,defrag}).
2. dmidecode -t memory and dmidecode -t 17 (will likely be permission denied; note that). Also try: ls -l /sys/firmware/dmi/tables (may be denied) and /sys/firmware/dmi/entries listing (names only). Try 'cat /sys/class/dmi/id/{sys_vendor,product_name,board_name,bios_version,bios_date}' (world-readable).
3. NUMA: numactl -H if present; ls /sys/devices/system/node; cat /sys/devices/system/node/node*/meminfo | head; cat /sys/devices/system/node/node0/distance.
4. /proc/iomem (may be masked as 0s for non-root; note); /proc/zoneinfo summary (just 'grep -E "Node|present|managed"').
5. Memory controller / DDR identifiers: ls /sys/bus/platform/devices | grep -i -E 'ddr|mem|dmc|edac|smmu|cmn' ; ls /sys/devices/system/edac/ ; ls /sys/bus/edac/devices 2>&1; dmesg | grep -i -E 'ddr|dram|memory|edac|dmc|mc[0-9]' | head -40 (note if denied).
6. Device tree: if /proc/device-tree exists, cat /proc/device-tree/memory*/reg | xxd | head and any node with 'memory' or 'ddr' in name: find /proc/device-tree -maxdepth 2 -iname '*mem*' -o -maxdepth 2 -iname '*ddr*' | head -20; print 'compatible' of each (tr '\\0' ' ').
7. If ACPI: ls /sys/firmware/acpi/tables (SRAT/HMAT/SLIT presence). HMAT would carry latency/bandwidth numbers from firmware; note whether it exists and whether readable (likely not without root). Also check /sys/devices/system/node/node0/access0/initiators/{read_bandwidth,read_latency,write_bandwidth,write_latency} and access1 variants: these are exported by the kernel from HMAT and ARE world-readable if present. This is high value: report exact values with units (kernel exports bandwidth in MB/s and latency in ns).
8. lshw -C memory (if present, non-root gives partial), and 'cat /sys/devices/system/memory/block_size_bytes'.
Return all facts with commands and excerpts.` },

  { key: 'toolchain', prompt: `${RULES}
TASK: Find out what tooling exists on CRB to build and run memory-hierarchy microbenchmarks later (DO NOT run any benchmark now), and whether hardware performance counters are accessible to an unprivileged user.
Collect:
1. Compilers: which gcc g++ clang clang++ cc; gcc --version | head -1; clang --version | head -1; gcc -march=native -Q --help=target 2>/dev/null | grep -E '^\\s+-march=|-mcpu=' | head -3 (read-only query, prints the detected CPU name - this is a legitimate way to identify the core; quote it). Also 'gcc -mcpu=native -Q --help=target | grep mcpu'.
2. Build tools: which make cmake ninja git python3 perl; python3 --version; python3 -c 'import numpy; print(numpy.__version__)' (just an import test).
3. Benchmark tools already installed: which perf likwid-perfctr likwid-bench likwid-topology lmbench lat_mem_rd bw_mem tinymembench stream mlc sysbench stress-ng hwloc-ls lstopo hwloc-info numactl; dpkg -l | grep -i -E 'lmbench|likwid|hwloc|numactl|linux-tools|linux-perf|stress-ng|sysbench' | awk '{print $2,$3}'. Also ls /usr/lib/linux-tools* /usr/lib/linux-tools-*/perf 2>&1 | head.
4. perf: perf --version; perf list 2>/dev/null | head -40; perf list | grep -i -E 'cache|l1d|l2d|l3d|ll_cache|bus|mem' | head -40 ; cat /proc/sys/kernel/perf_event_paranoid; cat /proc/sys/kernel/kptr_restrict; cat /proc/sys/kernel/nmi_watchdog 2>&1; ls /sys/bus/event_source/devices/ ; for each device print its 'type' and list events dir names (ls /sys/bus/event_source/devices/*/events | head -80). Especially look for arm_cmn*, arm_dsu*, armv8_pmuv3*, ddr/dmc PMUs. Check 'perf stat -e cycles true' as a 1-ms test (this executes 'true' only; acceptable) and report whether counters are readable without root. Only run that single 'perf stat -e cycles true'; nothing heavier.
5. Where can we run from later: echo $HOME; df -h $HOME /tmp /dev/shm; ls -la $HOME | head; cat ~/.bashrc | grep -i -E 'module|export' | head (do not modify); whether $HOME is on NFS (stat -f -c %T $HOME). Is there a 'module' system (which module; module avail 2>&1 | head)?
6. Kernel config: ls /boot; cat /boot/config-$(uname -r) 2>/dev/null | grep -E 'CONFIG_ARM_CMN|CONFIG_ARM_DSU_PMU|CONFIG_HW_PERF_EVENTS|CONFIG_ARM_PMU|CONFIG_PREEMPT|CONFIG_HZ=|CONFIG_NUMA|CONFIG_ARM64_PA_BITS|CONFIG_TRANSPARENT_HUGEPAGE'; or /proc/config.gz (zcat | grep same).
7. Does the user jhan have sudo? 'sudo -n true 2>&1' prints a message without doing anything if passwordless sudo is absent; run exactly 'sudo -n true' once and report the message. (It performs no change.)
Return all facts with commands and excerpts.` },

  { key: 'sharing', prompt: `${RULES}
TASK: Establish who else uses CRB and what resource limits/constraints apply, so the user can decide a sharing policy for benchmark runs.
Collect:
1. who; w; last -n 30 2>&1 | head -40 (user logins over time: which usernames, how often); ls /home.
2. ps -eo user,pid,pcpu,pmem,etime,comm --sort=-pcpu | head -30; ps -eo user --no-headers | sort | uniq -c | sort -rn | head; any long-running non-root user processes (ps -eo user,pid,etime,args --no-headers | awk '$1!="root"' | head -40).
3. systemd services that look like CI runners, schedulers, docker, kubernetes, slurm: systemctl list-units --type=service --state=running 2>&1 | head -60; which docker podman k3s kubelet slurmd srun sinfo; docker ps 2>&1 | head (will likely be denied; note).
4. cgroup limits on our session: cat /proc/self/cgroup; the cpuset.cpus.effective, cpu.max, memory.max at each level of our cgroup path under /sys/fs/cgroup (walk up the path). Report whether jhan is confined to a CPU subset (we know nproc=120 vs 128 online).
5. crontab -l 2>&1; ls /etc/cron.d; cat /etc/motd /etc/issue 2>/dev/null; ls /etc/update-motd.d; any README or policy files in / or /opt or /home: ls / /opt /srv /data /mnt 2>&1 | head -40.
6. Thermal/power: cat /sys/class/thermal/thermal_zone*/{type,temp} 2>&1 | head; ls /sys/class/hwmon/; for h in /sys/class/hwmon/hwmon*; do cat $h/name; done 2>&1; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor.
7. Uptime and recent reboots: uptime; last reboot | head -5.
Return all facts with commands and excerpts, and list questions the user should answer before we run benchmarks (e.g. whether writing files to $HOME is acceptable, whether using all 128 cores for a few minutes is acceptable, whether pinning/governor changes are off-limits).` },

  { key: 'uncore', prompt: `${RULES}
TASK: Identify the interconnect / uncore / system-level cache structure of CRB (mesh, system-level cache, memory-side cache, any L4-like cache), and all hardware PMUs that could expose cache/memory counters.
Collect:
1. ls -la /sys/bus/event_source/devices/; for every device: cat type, cat cpumask if present, ls events | tr '\\n' ' ' (bounded with head -c 4000), ls format. Pay special attention to arm_cmn (Arm CMN mesh: its events include hnf_* for system-level-cache/HN-F, and the presence of arm_cmn tells us there is a CMN mesh with SLC), arm_dsu (DSU cluster L3), armv8_pmuv3 (core), any ddr/dmc/mc PMU, any 'smmu'. Record the exact device names.
2. Device tree or ACPI identification of interconnect: find /proc/device-tree -maxdepth 2 -iname '*cmn*' -o -maxdepth 2 -iname '*interconnect*' -o -maxdepth 2 -iname '*noc*' -o -maxdepth 2 -iname '*dsu*' -o -maxdepth 2 -iname '*cluster*' 2>/dev/null | head -20; print 'compatible' of each. ls /sys/bus/platform/devices | grep -i -E 'cmn|dsu|noc|cache|hnf|slc|l3|l4' ; for each matching device print the 'modalias' and 'of_node/compatible' if present.
3. Cache levels beyond L3: check if any cpu has cache/index4 (ls /sys/devices/system/cpu/cpu0/cache/); check /sys/devices/system/cpu/cpu0/cache/index3/{size,shared_cpu_list,type,level}; grep -r . /sys/devices/system/cpu/cpu0/cache/index3/ 2>&1 | head -20.
4. Kernel modules loaded: lsmod | head -60 ; lsmod | grep -i -E 'cmn|dsu|pmu|edac|ddr'.
5. dmesg lines about pmu/cmn/dsu/cache/memory-side (may be denied; note): dmesg 2>&1 | grep -i -E 'pmu|cmn|dsu|mesh|slc|system cache|l3|l4' | head -40.
6. /sys/firmware/acpi/tables listing (names only) and whether PPTT/HMAT/SRAT exist. ls /sys/firmware/devicetree/base 2>&1 | head.
7. Is this CPU an Arm Neoverse? The MIDR decodes to implementer 0x41 = Arm. Part numbers table (cite as 'Arm MIDR part-number table, public'): 0xd0c Neoverse N1, 0xd49 Neoverse N2, 0xd40 Neoverse V1, 0xd4f Neoverse V2, 0xd84 Neoverse V3, 0xd83 Neoverse V3AE, 0xd8e Neoverse N3, 0xd85 Cortex-X925, 0xd87 Cortex-A725, 0xd88 Cortex-A520, 0xd8a Cortex-A320(?), 0xd8b Cortex-A720AE(?). Read /proc/cpuinfo 'CPU part' and midr_el1 and give the raw hex, then the table lookup ONLY as 'per public table'. Flag if the part number is NOT in that table (then say unknown).
Return all facts with commands and excerpts.` },

  { key: 'local-tooling', prompt: `
TASK (LOCAL machine only, no ssh): Find what is available locally to prepare memory-hierarchy microbenchmarks for an aarch64 target, so that we can later copy a binary or source to CRB once the user approves.
Do not modify anything outside the scratchpad directory. Read-only checks only:
1. Local arch: uname -m; nproc; gcc --version | head -1; clang --version 2>&1 | head -1.
2. Cross compilers: which aarch64-linux-gnu-gcc aarch64-linux-gnu-g++ aarch64-none-linux-gnu-gcc; ls /usr/bin | grep -i aarch64 | head; dpkg -l 2>/dev/null | grep -i -E 'aarch64|arm64' | awk '{print $2}' | head -20.
3. Containers: which docker podman; docker --version 2>&1; 'docker buildx ls 2>&1 | head' and 'docker run --rm --platform linux/arm64 alpine uname -m 2>&1' is NOT allowed (no running containers now); only report whether docker is present and whether binfmt_misc for qemu-aarch64 is registered: ls /proc/sys/fs/binfmt_misc/ 2>&1.
4. Benchmark sources already on disk: locate or find in ~/workspace for lmbench, tinymembench, likwid, STREAM, pmbw, 'lat_mem_rd', 'bw_mem', 'membench', 'x86-simd-sort' NOT needed; search: find ~/workspace -maxdepth 4 -type d \\( -iname '*lmbench*' -o -iname '*tinymembench*' -o -iname '*likwid*' -o -iname '*stream*' -o -iname '*pmbw*' -o -iname '*membench*' -o -iname '*mlc*' \\) 2>/dev/null | head -20; also ls ~/workspace and ~/workspace/titan.
5. Internet access from local machine for fetching sources later: curl -sI --max-time 8 https://github.com | head -1; and pip index availability: pip3 --version.
6. Existing notes in ~/workspace/notebook about Asimov cache structure (DSU, L1 shared between 2 cores, private L2/L3, on-chip SRAM): grep -ril -E 'dsu|on-chip|ocm|sram|shared l1|L1 shared' ~/workspace/notebook/artifacts/asimov-spec-study 2>/dev/null | head; and extract from README.md of that dir the first 60 lines. This gives context for the later Asimov phase; summarize cache-related facts you find with file:line citations.
Return raw facts with commands and excerpts.` },
]

phase('Inspect')
const results = await parallel(PROBES.map(p => () =>
  agent(p.prompt, { label: `probe:${p.key}`, phase: 'Inspect', schema: FACTS })
    .then(r => ({ key: p.key, ...r }))))
const ok = results.filter(Boolean)
log(`inspect: ${ok.length}/${PROBES.length} probes returned`)

phase('Verify')
const allFacts = ok.flatMap(r => r.facts.map(f => ({ probe: r.key, ...f })))
const CHECK = {
  type: 'object',
  properties: {
    contradictions: { type: 'array', items: { type: 'string' } },
    corrections: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, command: { type: 'string' }, output_excerpt: { type: 'string' }, corrected_interpretation: { type: 'string' } },
      required: ['claim', 'command', 'output_excerpt', 'corrected_interpretation'] } },
    confirmed_key_facts: { type: 'array', items: { type: 'string' } },
  },
  required: ['contradictions', 'corrections', 'confirmed_key_facts'],
}
const verify = await agent(`${RULES}
You are a skeptical verifier. Below are facts collected by five probe agents about CRB. Re-run (read-only, via ssh) the commands behind the 8 most consequential claims: CPU part number / MIDR, L1d/L2/L3 sizes and sharing (shared_cpu_list) per cache index, whether there is an index4 (L4), DRAM HMAT-derived bandwidth/latency under /sys/devices/system/node/node0/access*/initiators (if claimed present or absent), perf_event_paranoid and whether 'perf stat -e cycles true' works unprivileged, the list of /sys/bus/event_source/devices, the CPU affinity/cpuset that limits nproc to 120, and whether sudo is available ('sudo -n true' only). Confirm or correct each. Also flag any interpretation that goes beyond what the output literally supports (e.g. naming a product without an identifier). Do NOT run anything heavier than 'perf stat -e cycles true'.

FACTS:
${JSON.stringify(allFacts, null, 1).slice(0, 60000)}
`, { label: 'verify', phase: 'Verify', schema: CHECK })

phase('Synthesize')
const report = await agent(`You are writing an INSPECTION RECORD (not a user-facing message; raw structured markdown is fine) about CRB, an ARM64 Linux server, from the probe facts and verifier output below. The goal of the overall project: measure best-case latency and maximum throughput of every cache level (L1/L2/L3, L4 if any) and DRAM on CRB. We have NOT run any benchmark yet and must not until the user approves a sharing policy.

Write these sections, with every claim followed by the command that supports it in brackets:
1. Machine identity (hostname, kernel, OS, firmware vendor/board if readable, CPU implementer/part hex and the public-table name if the hex is in the table, core count, frequencies, governor).
2. Cache hierarchy table: for each level: size per instance, instances, associativity, line size, sets, sharing (which CPUs share one instance), write/allocation policy if exported. State explicitly whether an L4 / system-level cache / memory-side cache exists according to sysfs, PMU devices (arm_cmn presence), DT/ACPI. If unknown say "Insufficient data" and what would resolve it.
3. DRAM: total, NUMA nodes, hugepage/THP settings, any HMAT-exported bandwidth/latency numbers (with units), any DDR/channel/speed facts, and explicit "not obtainable without root" items.
4. PMUs available (device names, example cache/memory events), perf_event_paranoid, whether unprivileged perf works.
5. Toolchain available on CRB (compilers with versions, make/cmake, python, numactl/hwloc/likwid/lmbench presence) and whether sudo is available.
6. Sharing constraints: who else logs in, running non-root processes, cgroup/cpuset limits on jhan (why nproc=120), thermal readouts, motd/policy text.
7. Local tooling available for preparing benchmarks (cross compiler, docker, sources on disk, internet).
8. Asimov context notes found locally (cache-related facts with file citations), kept short.
9. Verifier contradictions/corrections, verbatim.
10. Open questions for the user before benchmarks can run (dedupe across probes; make each one a yes/no or a single choice).

PROBE RESULTS:
${JSON.stringify(ok, null, 1).slice(0, 90000)}

VERIFIER:
${JSON.stringify(verify, null, 1)}
`, { label: 'synthesize', phase: 'Synthesize' })

return { report, verify, blocked: ok.flatMap(r => r.blocked.map(b => `[${r.key}] ${b}`)), questions: ok.flatMap(r => r.questions_for_user) }