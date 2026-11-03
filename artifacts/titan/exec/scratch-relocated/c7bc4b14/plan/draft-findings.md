# Draft findings and plan for phoenix-crb (to be attacked by verifiers)

Written 2026-10-21 ~17:00 PDT (2026-10-22 00:00 UTC) by the orchestrating agent from read-only SSH inspections of
positron-perf@192.168.2.45 at 23:42–23:57 UTC on 2026-10-21. Every claim below is numbered so that analysts and
verifiers can cite, confirm, correct or refute it. Evidence files (raw command output) are in
/tmp/claude-0/-home-jhan-workspace-titan-rampup/c7bc4b14-f908-49ab-9a48-bf71f129d499/scratchpad/inspect/ :
  phoenix-crb-inspection.txt  (main inspection, 1220 lines, sections marked "=== name ===")
  phoenix-crb-followup.txt    (staged workspace, toolchain, 3 s pinned spin clock measurement, dmesg, timers)
  phoenix-crb-round3.txt      (key fingerprints, toolchain README, Jeremy's job scripts and results, residual tick)
  phoenix-crb-round4.txt      (Jeremy's churn-r1 job log, latency judge summary, isolation snapshot, SDK CI scripts)
  phoenix-crb-round5.txt      (SDK source grep: thread pinning, SCHED_FIFO use, what voids a record, perf-lane rules)
  inspect.sh / followup.sh / round3.sh / round4.sh  (the scripts that produced them)
Jeremy's three messages verbatim: ../plan/requests.txt

## Names used

- phoenix-crb: the host at 192.168.2.45 (Linux hostname "ubuntu"). Firmware identifies it as "Phoenix Reference
  Server", vendor Arm Limited, EVT0, Quanta motherboard, BIOS "AGI-CPU-CRB-v0.7.2" dated 2026-09-08.
- Jibin: the user I work for (jhan@positron.ai, workstation claude-agentsrv = 192.168.2.136, timezone PDT, UTC-7).
- Jeremy: the SDK-side requester. His git commit on the host is authored "Jeremy Conner" with timezone -0400
  (US Eastern), 2026-10-21 14:20:48 -0400 = 18:20 UTC.
- positron-perf: the unprivileged test account (uid 1001) that Jeremy asked for. I log in to it with Jibin's key.
- arm: the administrator account (uid 1000, member of group sudo). Logged in on tty1 (console) since 2026-10-20 19:31 UTC.
- The vendor kernel: 7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 (running). The stock kernel: 6.8.0-147-generic (installed, not running).

## A. Host facts (measured)

F1. OS Ubuntu 24.04.5 LTS, aarch64, 128 CPUs (1 socket, 1 NUMA node, no SMT: each CPU is its own core), 377 GiB RAM,
    no swap. Running kernel 7.1.3-arm-agi-20260916-v0.7.2 (SMP PREEMPT, built 2026-09-16, HZ=250). Uptime since
    2026-10-20 19:06 UTC. Host timezone UTC, NTP synchronized (systemd-timesyncd). [inspection: identity, cpu_summary, sysctl_limits]
F2. Running kernel config: "# CONFIG_NO_HZ_FULL is not set", CONFIG_NO_HZ_IDLE=y, "# CONFIG_RCU_EXPERT is not set",
    no CONFIG_RCU_NOCB_CPU line at all, CONFIG_CPU_ISOLATION=y, CONFIG_CPUSETS=y (v1 off), CONFIG_PREEMPT=y,
    CONFIG_HZ=250, CONFIG_ARM64_AMU_EXTN=y, CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y, CONFIG_CPU_FREQ_GOV_PERFORMANCE=y,
    CONFIG_ACPI_CPPC_CPUFREQ=m, CONFIG_CPU_IDLE=y but no cpuidle driver registered ("driver: none"). [inspection: kernel_config, cpufreq]
F3. A second kernel is installed: 6.8.0-147-generic (Ubuntu stock, auto-installed by unattended-upgrades on
    2026-10-15 06:16 UTC; earlier -142 and -146 came the same way). Its /boot config has CONFIG_NO_HZ_FULL=y,
    CONFIG_RCU_NOCB_CPU=y, HZ=1000, PREEMPT_DYNAMIC. /boot/vmlinuz symlink points at it, but GRUB_DEFAULT=saved and
    grubenv saved_entry pins the vendor kernel, so reboots keep the vendor kernel. [inspection: kernel_config, boot_and_kernels; followup: services_detail apt history]
F4. There is NO evidence the stock 6.8 kernel has ever booted on this board (wtmp begins 2026-09-29, all 5 reboots
    since are the vendor kernel). The vendor kernel's dmesg shows silicon-specific workarounds: "GICv3: Arm AGI CPU A0
    detected, enabling GIC erratum workaround" and "CPU features: detected: Broken broadcast TLBI completion". Claim:
    booting the stock kernel on this EVT0 board is an untested, risky path and should not be the plan of record.
    [inspection: logins; followup: dmesg_greps]
F5. Nothing is isolated today: /sys/devices/system/cpu/isolated is empty, nohz_full file absent, cmdline is
    "BOOT_IMAGE=/vmlinuz-7.1.3-... root=UUID=... ro console=tty1 console=ttyAMA0". cgroup v2; root cpuset.cpus.isolated
    empty; cpuset controller is NOT in cgroup.subtree_control (only cpu memory pids). [inspection: cpu_summary, cgroups]
F6. cpufreq: driver cppc_cpufreq, 128 policies, one CPU per policy (related_cpus = the CPU itself, freqdomain_cpus=120
    for policy120), governor schedutil on all 128, available "ondemand userspace performance schedutil", limits
    1.6–2.8 GHz, boost 0 (disabled), transition_latency 0. cpuinfo_cur_freq is root-only (0400). acpi_cppc/feedback_ctrs
    is world-readable (0444); cpuinfo_avg_freq is 0444 but returns EAGAIN on an idle CPU. perf_limited reads an
    implausible value (2095059446). CPPC: highest_perf=nominal_perf=140, lowest_perf=80, reference_perf=50,
    nominal_freq=2800, lowest_freq=1600 (so 1 perf unit = 20 MHz). [inspection: cpufreq; followup: cpufreq_extra]
F7. Measured clock under load with schedutil: a 3 s spin pinned to CPU 121 went from 1.6 GHz to 2.8 GHz within the
    first 0.3 s sample (samples: 1758203 then 2800000 x9 kHz); CPPC feedback counters over the 3.01 s gave delivered
    perf 139.8 of 140 = est. 2796 MHz; cpuinfo_avg_freq read 2797265 kHz afterwards. The reference counter advanced at
    est. 999 MHz, matching "arch_timer: cp15 timer running at 1000.00MHz". So: the test account CAN measure delivered
    clock without root, via feedback_ctrs deltas. No thermal or power cap was seen in 3 s; longer runs not measured. [followup: cpufreq_extra]
F8. Jeremy's own frequency samples (files in ~/positron/runs/hiccup and logits-bench, 2026-10-21 18:40–18:43 UTC):
    freq.sleep.txt "89 x 1600000, 1 x 1711718" (a sleep-then-spin wait pattern keeps the CPU at 1.6 GHz under schedutil);
    freq.spin.txt "75 x 2800000, 14 x 1600000, 1 x 1873046"; freq.hot.txt "11 x 2800000, 1 x 1600000"; freq.idle.txt "12 x 1600000".
    Hypothesis H1 (not proven): the fake device thread, which sleeps until 100 us before each retirement and then spins
    (backends/null_timing/null_timing.cpp kSpinNs = 100'000), runs at 1.6 GHz under schedutil, and this contributes
    to its lateness; the performance governor would remove it. Measurement to confirm: run ~/positron/runs/hiccup/hiccup
    on an idle CPU in "sleep" mode with schedutil vs performance and compare lateness/stall statistics. [round3: freq_files; round5]
F9. Residual timer tick: on CPU 121, 10 arch_timer interrupts in 5 s while idle, 1261 in 5 s while running a pinned
    spin (CPU 125: 1258). That is the HZ=250 scheduler tick, one interrupt every 4 ms on a busy CPU. nohz_full would
    stop it for a CPU running a single task; nothing on the current kernel can. [round3: residual_tick_under_load]
F10. Interrupts touching CPUs 120–127: only the managed NVMe queue interrupts (nvme0q119–126, nvme1q119–126; one queue
    per CPU; effective affinity = that CPU) plus timer and IPIs. The 64 network TxRx queues of enP7p1s0f0np0 (bnxt_en)
    sit on CPUs 0–63; 196 other IRQs have effective affinity CPU 0; default_smp_affinity is all CPUs. Since boot, CPU
    120–127 received 5.33 M arch_timer, 123,695 function-call IPIs (IPI1), 2,032 rescheduling IPIs, and e.g. 22,045 on
    nvme0q124. irqbalance is not installed. [inspection: interrupts]
F11. Background: CPUs 120–127 were 100% idle in a 5 s sample; load average 0.00–0.47. Running services include
    netperf.service (an LSB "network benchmark" server started at boot), unattended-upgrades (active, enabled), cron,
    smartmontools, rsyslog, ModemManager, udisks2, ssh, systemd-networkd/resolved/timesyncd. Timers: apt-daily
    (OnCalendar 6,18:00 UTC + up to 12 h random delay), apt-daily-upgrade (6:00 UTC + up to 60 min), sysstat-collect
    every 10 min, logrotate and dpkg-db-backup daily 00:00 UTC, fstrim weekly (next Mon 2026-10-26 00:27 UTC),
    man-db, motd-news, fwupd-refresh, update-notifier, e2scrub_all (Sun 03:10 UTC; no LVM so a no-op). Automatic reboot
    by unattended-upgrades is not enabled (no uncommented Automatic-Reboot line). Unbound workqueue cpumask allows all
    128 CPUs; /sys/devices/virtual/workqueue/cpumask_isolated exists. No docker, LSF, Slurm, or CI runner found.
    [inspection: background; followup: services_detail]
F12. Account positron-perf: uid 1001, groups positron-perf and users; password locked ("L"); `sudo -n true` and
    `sudo -n -l` both say "a password is required" (so no password-free sudo rule and no usable password), i.e. no
    usable sudo. /etc/sudoers.d/positron-perf-setup exists (49 bytes, created 2026-10-21 05:12 UTC, unreadable by the
    account). The only sudo-group member is arm. Limits: real-time priority hard limit 0 (SCHED_FIFO refused: "chrt -f 1
    true" fails), nice hard limit 0, max locked memory 49 GB, perf_event_paranoid=2 (user-space counters cycles:u and
    instructions:u work; no system-wide perf). dmesg is readable (dmesg_restrict=0). [inspection: network_access, sysctl_limits; followup: perf_rt_checks, services_detail]
F13. SSH keys on the account: three ed25519 keys: Jibin's workstation key (comment rewritten to "positron-perf@phoenix",
    fingerprint 0ZKrsw…, the one I log in with), "jeremy@sw-dev-01", "jeremy@DESKTOP-V2B1166" (authorized_keys mtime
    2026-10-21 16:53 UTC). sshd allows password authentication and root login (a drop-in 01-arm-svk-password-auth.conf). [round3: authorized_key_fingerprints; inspection: network_access]
F14. Jeremy's side has already used the account: ~/positron (7.7 GB) was created 2026-10-21 18:11–18:57 UTC with a
    README stating "Set up 2026-10-21 for positron-perf, approved by Jeremy that day ("user-only toolchain on Phoenix")
    … no sudo was used"; the SDK source ~/positron/src/phoenix-int is a git bundle checkout at commit ead1e9a authored
    Jeremy Conner "local integration for Phoenix evidence, never pushed". Non-interactive SSH sessions do not appear in
    `last`, so which of Jeremy's two keys/paths was used is unknown (the system journal is not readable by the account). [round3: toolchain_readme, git_state]
F15. Toolchain requirement is already met at user level: ~/positron/toolchains/sdk-ci-2026-10 (conda-forge via
    micromamba 2.9.0) has clang 18.1.8, ninja 1.13.2, cmake 3.31.6, gcc 13.3.0; venvs on /usr/bin/python3.12 (3.12.3,
    headers present) with numpy 2.5.3 and the positron-compiler package; deps vendored (googletest, nlohmann_json,
    nanobind 3.0.1); Qwen3.5-0.8B weights (1.7 GB) staged. System-wide: gcc 14.2/13.3, cmake 3.28.3, python 3.12.3+dev,
    git, perf, taskset, chrt, numactl, stress-ng, cpupower; no clang-18/ninja in system PATH (apt candidates clang-18
    1:18.1.3-1ubuntu1 and ninja-build 1.11.1-2 exist, would need sudo). [round3; inspection: tools]
F16. Storage: / (ext4, also holds /home) 1.7 TB with 1.7 TB free (41 GB used); no quota tool; /home/positron-perf uses
    7.7 GB. The "about 100 GB" ask is covered; ~/positron/work exists (Jeremy's layout), ~/work does not. [inspection: storage]
F17. Network: the host has outbound internet (DNS 8.8.8.8, HTTPS 200 from pypi.org and ports.ubuntu.com, TCP to
    GitHub). The host cannot resolve sw-dev-01. From Jibin's workstation, sw-dev-01 resolves via Tailscale to
    100.124.2.53 (sw-dev-01.porgy-gecko.ts.net) and port 22 is reachable. Whether sw-dev-01 can reach 192.168.2.45:22 is
    NOT verified (needs one check from sw-dev-01). [inspection: network_access; local check]
F18. Jeremy's first job on the host (ev3-churn-job.sh, run "churn-r1", 2026-10-21 18:32–18:35 UTC, 168 s, label rc=3):
    the whole label was run under `taskset -c 120-127`; churn.py pinned the pass thread to CPU 127 and the other threads
    to 120–126; the latency judge verdict was INFRA with problems "the fake device's lateness voids the record" (and the
    same for the u6 fault-timing run); isolation recorded as core_isolated=false, isolated_cpus=[]. Busy share during
    the job: CPU 127 76%, 122 12%, 123 8%, others 1.5–5%; CPUs 0–119 0.02%. The run's bind summary: device late_mean
    6.2 us, late_max 220 us, lateness_band 2.5 us, void=true; pass bind p99 67.5 us, max 1482.5 us (budget 100 us, 50 over). [round4; round3: check/r1]
F19. SDK code facts (read-only grep of ~/positron/src/phoenix-int): the runtime pins threads with sched_setaffinity /
    pthread_setaffinity_np only; it does not call sched_setscheduler, SCHED_FIFO, mlockall (so no rtprio/memlock limit
    change is needed for the current code). churn.py records core_isolated = (pass core in /sys/devices/system/cpu/isolated),
    i.e. isolcpus alone satisfies that field. BUT tools/perf/records.py / perf_lane.py require "an online core in both
    isolcpus and nohz_full: where the pass thread may run" and report "no online core is in both isolcpus and nohz_full
    (§12.2 l.2049)" otherwise; the perf lane "is advisory, and its figures count only from the perf host". Which of
    these tools produces the demo's counted numbers is NOT known from the host. [round5]
F20. Coordination facts: user arm has an active console session (tty1, seat0) since 2026-10-20 19:31 UTC; arm logged
    in today from 192.168.2.136 (Jibin's workstation address) at 00:24–00:24, 00:55–03:55, 05:03–05:14 UTC and from
    192.168.1.200 (19:32 Oct 20 – 08:03 Oct 21 UTC, several sessions). The positron-perf home was created 00:56 UTC and
    the sudoers drop-in 05:12 UTC during those arm sessions. Reboots: Sep 29 (x2), Oct 3, Oct 5, Oct 20. [inspection: logins; followup: services_detail]

## B. Linux-semantics claims (need checking against kernel docs/source for a 7.1 kernel)

S1. On the running kernel, boot args `nohz_full=` and `rcu_nocbs=` are NOT registered (their __setup handlers exist only
    under CONFIG_NO_HZ_FULL / CONFIG_RCU_NOCB_CPU), so they would be reported as unknown parameters and ignored.
S2. `isolcpus=domain,managed_irq,120-127` DOES work on the running kernel (CONFIG_CPU_ISOLATION=y). The `nohz` flag of
    isolcpus must NOT be used on this kernel: housekeeping_setup() refuses the whole isolcpus setting with
    "Housekeeping: nohz unsupported. Build with CONFIG_NO_HZ_FULL" when the kernel lacks NO_HZ_FULL.
S3. `irqaffinity=0-119` works on any kernel (generic irq core) and sets the default affinity for non-managed IRQs;
    managed IRQs (the NVMe queues) are handled by `isolcpus=managed_irq` (best effort: a managed IRQ whose whole mask
    is isolated CPUs still runs there). Writing /proc/irq/N/smp_affinity for a managed IRQ fails (EIO/EPERM); per-queue
    NVMe interrupts only fire on CPU N for I/O submitted from CPU N.
S4. Without reboot and with root, the same scheduler isolation can be obtained with a cgroup v2 cpuset "isolated"
    partition (enable cpuset in /sys/fs/cgroup/cgroup.subtree_control, create a child cgroup with cpuset.cpus=120-127 and
    cpuset.cpus.partition=isolated); since Linux 6.7 isolated partitions also remove those CPUs from unbound workqueues
    (the cpumask_isolated sysfs file on this host indicates that code is present). It gives no nohz_full and does not
    move managed IRQs. systemd (Ubuntu 24.04, systemd 255) does not manage cpuset.cpus.partition itself; it must be
    written by hand and may be lost on reboot unless scripted.
S5. The governor can be changed live by root (write "performance" to each policy's scaling_governor). Since each CPU
    is its own policy/domain here, performance can be set on 120–127 only, or host-wide. Persistence options: the
    kernel boot parameter `cpufreq.default_governor=performance` (Linux >= 5.9, applies when the cpufreq core registers
    the driver, including the modular cppc_cpufreq), and/or a systemd oneshot unit at boot. There is no cpufrequtils/
    ondemand/tuned/power-profiles-daemon on the host that would fight the setting (all "not-found"/inactive).
S6. CONFIG_NO_HZ_FULL=y in Kconfig selects RCU_NOCB_CPU, so a vendor kernel rebuilt with NO_HZ_FULL enabled also gets
    rcu_nocbs support; NO_HZ_FULL is incompatible with nothing in the current config (HZ=250 and PREEMPT=y are fine)
    but it requires CONFIG_VIRT_CPU_ACCOUNTING_GEN (selected automatically) and is only selectable when
    "NO_HZ_FULL" depends are met (SMP, HAVE_CONTEXT_TRACKING_USER, HAVE_VIRT_CPU_ACCOUNTING_GEN; arm64 has them).
S7. `nohz_full=120-127` on a NO_HZ_FULL kernel implies those CPUs are also isolated from the scheduler domains only if
    isolcpus is also given (nohz_full alone does not set the domain flag in recent kernels), and nohz_full CPUs are
    automatically rcu_nocbs CPUs. The tick still fires once per second on a nohz_full CPU (residual 1 Hz tick).
S8. The GRUB drop-in /etc/default/grub.d/50-cloudimg-settings.cfg overrides GRUB_CMDLINE_LINUX_DEFAULT (so edits to
    /etc/default/grub's DEFAULT line are ignored); appending to GRUB_CMDLINE_LINUX (which no drop-in sets) in a new
    drop-in such as /etc/default/grub.d/60-positron-isolation.cfg, then `update-grub`, puts the args on every menu entry
    including the vendor kernel. GRUB_DEFAULT=saved with saved_entry already selects the vendor kernel.

## C. Status of each of Jeremy's asks (my reading)

A1 account positron-perf with SSH key login: DONE (keys installed; Jeremy's side has staged 7.7 GB and run a job). Open: which path (laptop direct or via sw-dev-01) he uses; sw-dev-01 -> 192.168.2.45 unverified.
A2 "or run a script we send": moot; the account exists.
A3 clang 18 / CMake >= 3.25 / Ninja / Python >= 3.11 + headers: DONE at user level by Jeremy's side (approved by Jeremy). No admin action needed.
A4 ~100 GB disk: available (1.7 TB free), no quota. DONE.
A5 no sudo / no outbound: the account has no sudo (as asked); the host has outbound anyway (not a blocker).
A6 fixed CPU clock (performance governor, no boost): NOT DONE. Needs root, NO reboot. Boost is already disabled. Under schedutil a busy CPU does reach 2.8 GHz, but a mostly-sleeping thread sits at 1.6 GHz (F7, F8).
A7 isolated cores (isolcpus) with IRQs kept off: NOT DONE. Possible on the current kernel with root + reboot (isolcpus=domain,managed_irq + irqaffinity), or partially without reboot (cpuset isolated partition + IRQ affinity writes).
A8 nohz_full (+ rcu_nocbs): NOT POSSIBLE on the running kernel. Needs a kernel with CONFIG_NO_HZ_FULL=y: rebuild the vendor kernel (source commit 4dbc8bb88858, provider = whoever supplies the arm-agi kernel; the host has the Arm SVK gcc-14 toolchain at /opt/arm-svk with KERNEL_CC/KERNEL_MCPU=neoverse-v3ae set up by the installer, so building on the box is plausible), or get a build from the provider; the stock 6.8 kernel is installed but untested on this silicon (F4).
A9 nothing else running during a timed run / nightly window: host is near idle, but apt/unattended-upgrades timers, sysstat, fstrim (Mon 00:27 UTC), logrotate (00:00 UTC) and the netperf server exist; needs root to pause and a reservation rule with user arm.
A10 "one isolated core by Fri 10-23, counted runs Mon 10-26": achievable WITHOUT nohz_full (governor + isolcpus reboot or cpuset partition). With nohz_full only if a rebuilt kernel is available and installed before Friday (unlikely; depends on the kernel provider).

## D. Does the work need Jeremy's input to proceed?

Not to start. Everything in Phase 1–2 below can begin today with the arm account. Jeremy's input is needed before
counted runs for four decisions:
D1. Accept a Friday setup WITHOUT nohz_full/rcu_nocbs (isolcpus + irqaffinity + performance governor on the current
    kernel), with the 250 Hz tick remaining on busy isolated CPUs (F9), or wait for a rebuilt kernel. He pre-approved
    workarounds ("tell me and we'll work around it"), so informing him and asking for a yes/no suffices.
D2. Which tool gates the counted runs: churn/latency judge (needs isolcpus only for core_isolated) or tools/perf
    perf_lane (needs a core in BOTH isolcpus and nohz_full) (F19).
D3. CPU map: which CPUs need full isolation (pass thread; maybe the fake device thread) vs. merely reserved for the
    run's other threads. With isolcpus=domain on all of 120–127 the scheduler does no load balancing among them, so his
    threads restricted to 120–126 as a group are not spread automatically; either pin each thread to its own CPU, or
    isolate only the pass-thread CPU(s) (e.g. 126–127) and leave 120–125 as ordinary CPUs reserved by agreement.
D4. Run windows and timezone (host UTC, Jibin PDT, Jeremy EDT), and the clock-stability acceptance rule (what spread
    of delivered MHz counts as "fixed").
Nice-to-have from Jeremy: confirm which login path he uses; whether the sampling unit tests and timed compile still
need scheduling; whether he wants host-wide performance governor or only 120–127.

## E. Action plan (draft)

P0 Today (Jibin, no root): send Jeremy the status and D1–D4; ask the vendor-kernel provider for the kernel source
   or a NO_HZ_FULL build (Jibin knows the contact; the host does not say who).
P1 Today or Thu 22 Oct, live, root (arm account), no reboot:
   P1a performance governor on all 128 policies (or 120–127); verify with scaling_governor and a feedback_ctrs sample.
   P1b stop netperf.service; `systemctl disable --now` (or mask) apt-daily.timer, apt-daily-upgrade.timer and
       unattended-upgrades.service until after 5 Nov, so no package or kernel changes and no CPU bursts during runs;
       optionally stop sysstat-collect.timer during windows.
   P1c (optional, if the reboot cannot happen by Friday) cpuset isolated partition for 120–127 + write
       /proc/irq/default_smp_affinity=0-119 + move movable IRQs; record it as a reversible, non-persistent setting.
P2 Thu 22 Oct (arm account, reboot, ~15 min outage, coordinated with user arm's console session and the 192.168.1.200
   user): new drop-in /etc/default/grub.d/60-positron-isolation.cfg with
       GRUB_CMDLINE_LINUX="isolcpus=domain,managed_irq,120-127 irqaffinity=0-119 cpufreq.default_governor=performance"
   (no nohz_full/rcu_nocbs on this kernel; S1, S2), `update-grub`, check the generated entry for the vendor kernel,
   reboot, then verify: /proc/cmdline, /sys/devices/system/cpu/isolated = 120-127, governors = performance, dmesg has no
   "Unknown kernel command line parameters", IRQ effective affinities, workqueue cpumask (isolcpus=domain also excludes
   the CPUs from unbound workqueues? — verify), then re-run Jeremy's ev3-churn-job.sh and compare the judge verdict,
   device late_max and bind max to churn-r1 (F18).
P3 Fri 23 Oct (Jibin + Jeremy): hand-off note with kernel version, exact cmdline, isolated list, governor evidence,
   feedback_ctrs clock samples during a run, known limitation (no nohz_full: 250 Hz tick on busy isolated CPUs),
   reservation rule, and the pre-run checklist (Jeremy's isol.py snap already records most of it).
P4 In parallel (kernel provider + arm account): obtain/build the vendor kernel with CONFIG_NO_HZ_FULL=y (which brings
   RCU_NOCB_CPU), install as an additional menu entry (keep the current one), second reboot with
   nohz_full=120-127 rcu_nocbs=120-127 added; verify dmesg "NO_HZ: Full dynticks CPUs: 120-127" and
   /sys/devices/system/cpu/nohz_full. Target: before the 5 Nov demo if Jeremy needs the perf lane (D2); otherwise after.
P5 Mon 26 Oct onward: counted runs in reserved windows; keep apt timers off until 5 Nov; restore afterwards.
Rollback: remove the drop-in, update-grub, reboot (or select the entry without the args at the GRUB menu, 10 s timeout,
serial console ttyAMA0 and tty1 available); governor back to schedutil live.

## F. Open gaps (Insufficient data)

G1. Who provides the arm-agi kernel and whether its source at 4dbc8bb88858 is available to Positron.
G2. Whether sw-dev-01 can reach 192.168.2.45:22 (one command from sw-dev-01).
G3. Whether the 1.6 GHz sleep-pattern clock (F8) is the cause of the fake device lateness (H1) — measurable with hiccup.
G4. Contents of /etc/sudoers.d/positron-perf-setup (what the admin intended for the account).
G5. Clock stability over a full run (only 3 s measured by me; Jeremy's samples are 1–2 min).
G6. Which of Jeremy's two keys/paths was used for the 18:xx UTC staging (system journal not readable).
