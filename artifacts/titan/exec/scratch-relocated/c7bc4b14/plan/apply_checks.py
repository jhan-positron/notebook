import re, sys
p="build_plan.py"; s=open(p,encoding="utf-8").read()
R=[]  # (old, new)
def rep(old,new): R.append((old,new))

# header / short version / note / security box
rep("Written for Jibin on 21 October 2026 and revised three times on 22 October (UTC): at 02:40 after a verification pass by 20 independent agents, at 05:05 with Jibin's answers to the administrator questions (section 4), and at 06:00 as the as-built record after Jibin made the host changes from the <code>jhan</code> account between 05:26 and 05:43 UTC, each verified read-only from <code>positron-perf</code>.",
    "Written for Jibin on 21 October 2026. Revised three times on 22 October (UTC). The 02:40 revision followed a verification pass by 20 independent agents. The 05:05 revision added Jibin's answers to the administrator questions (section 4). The 06:00 revision is the as-built record: Jibin made the host changes from the <code>jhan</code> account between about 05:25 and 05:43 UTC, and each change was verified read-only from <code>positron-perf</code>.")
rep("was checked read-only as <code>positron-perf</code> between 21 October 23:42 UTC and 22 October 02:00 UTC.",
    "was checked read-only as <code>positron-perf</code> between 21 October 23:42 UTC and 22 October 02:00 UTC, and again on 22 October between 05:26 and 05:52 UTC after each of Jibin's changes.")
rep("<p>The host side is done: on 22 October Jibin set the performance governor, paused the housekeeping timers and rebooted at 05:43 UTC with cores 126–127 isolated (verified at 05:44 UTC), but nohz_full still needs a rebuilt kernel from Arm.</p>",
    "<p>On 22 October Jibin set the performance governor, paused the housekeeping timers and rebooted at 05:43 UTC with cores 126–127 isolated (verified at 05:44 UTC). One host item remains: nohz_full needs a rebuilt kernel from Arm.</p>")
rep("so the message in section 4 is the next step (it waits on question A11).</p>",
    "so the message in section 4 is the next step (it waits on Jibin's yes to question A11, the two statements it makes about nohz_full and about Monday's runs).</p>")
rep("The isolation, governor, timer and boot settings were unchanged at 01:55 UTC.",
    "The isolation, governor, timer and boot settings were unchanged at 01:55 UTC. Jibin then changed all four between about 05:25 and 05:43 UTC (section 6).")
rep("Security finding, to fix before any root use of these tools.", "Security finding, fixed by Jibin at about 05:25 UTC on 22 October (step P1d, verified 05:26 UTC).")
rep("are owned by the test account", "were owned by the test account until 22 October")
rep("Step P1d changes the ownership to root.", "Step P1d changed the ownership to root (verified 05:26 UTC: 0 files outside /home owned by positron-perf, down from 347).")
# glossary
rep("Root steps below are run from it or from <code>jhan</code>.", "The root steps of 22 October were all run from <code>jhan</code>.")
rep("(today) follows CPU utilization", "(the governor until 22 October 05:36 UTC) follows CPU utilization")
rep("Its files are owned by user id 1001, which on this host is positron-perf.", "Its files were owned by user id 1001, which on this host is positron-perf, until Jibin changed them to root at about 05:25 UTC on 22 October (step P1d).")
rep("The timers are active on the host and installed two kernels in October.", "The timers installed two kernels in October. Jibin disabled them at 05:30 UTC on 22 October (step P1b).")
rep("are the proposed re-runs after the governor change and after the reboot.", "were the proposed re-runs after the governor change (govtest-1, no longer possible because the reboot came first) and after the reboot (govtest-2, pending on Q6).")
# section 2
rep("Both observations match the host.", "Both observations matched the host on 21 October. Since the 22 October 05:43 UTC reboot the governor is performance and CPUs 126–127 are isolated.")
# section 3
rep("The host setup is achievable. Validity is unproven:", "The host setup is done (22 October), without nohz_full. Validity is unproven:")
rep("launch command); 126-127 applied by default", "launch command). 126-127 applied by default at the 22 Oct reboot")
rep("Done 22 Oct 05:36 UTC by a sysfs write from <code>jhan</code>, and persistent through the boot argument <code>cpufreq.default_governor=performance</code>: 128 × performance after the 05:43 UTC reboot, request 2,800 MHz on every CPU (verified).",
    "Done 22 Oct 05:36 UTC by a sysfs write from <code>jhan</code>. It persists through the boot argument <code>cpufreq.default_governor=performance</code>. After the 05:43 UTC reboot: 128 × performance, request 2,800 MHz on every CPU (verified).")
# section 4 intro and tables
rep("The reboot happened on 22 October at 05:43 UTC with the D3 default (126–127 isolated), and a different core set needs another reboot, which Jibin can run at any idle moment.",
    "The reboot happened on 22 October at 05:43 UTC with the D3 default (126–127 isolated). A different core set needs another reboot. Jibin can run it at any idle moment.")
rep("<p><strong>Useful but not blocking</strong> (asked at the end of the message):</p>",
    "<p><strong>Useful but not blocking.</strong> Q8, Q9 and part of Q10 are in the message's “Nice to have” paragraph. Q7 is moot (the governor is on all 128 CPUs). Q11 is answered by A10 and by item 6 of the message. Q12 is not asked yet:</p>")
rep("The governor-only re-run (govtest-1) shows how much the clock contributes.", "A re-run on the as-built host (Q6, if Jeremy allows it) shows the combined effect of the clock and the isolation. A governor-only run is no longer possible: the reboot came before any re-run.")
rep("(govtest-1 after the governor change, govtest-2 after the reboot, about 3 min each)?", "(govtest-2 on the as-built host, about 3 min)?")
rep("The re-runs give before/after evidence for the device's mean lateness.", "The re-run gives before/after evidence for the device's mean lateness (govtest-1, the governor-only run, is no longer possible since the reboot came first).")
rep("The fourth column records the answer and whether the question is still open.", "The fourth column records the answer, what was done afterwards (up to 05:48 UTC), and whether the question is still open.")
rep("Item 1 of the message asks Jeremy to confirm in passing.", "Item 1 of the message asks Jeremy to confirm this.")
rep("Entry 0010 and the second disk stay unknown, and neither blocks the reboot: the planned boot arguments cannot fail the boot, the GRUB saved entry still names the vendor kernel, and the host booted the vendor kernel at each of its last three boots (3, 5 and 20 October) as recorded by <code>last</code>. Suggested: open the BMC console before the reboot and watch the boot.",
    "Entry 0010 and the second disk stay unknown. Neither blocked the reboot of 22 October: the boot arguments could not fail the boot, the GRUB saved entry still names the vendor kernel, and the host booted the vendor kernel at each of its last four boots (3, 5, 20 and 22 October). Both stay unknown and block nothing now.")
rep("Security: 347 files under /usr, /etc and /lib are owned by uid 1001.", "Security: 347 files under /usr, /etc and /lib were owned by uid 1001 until step P1d on 22 October.")
rep("and the cpupower unit are root-owned, every file of the package is root:root, and no file outside /home belongs to positron-perf (count 347 → 0).",
    "and the cpupower unit are root-owned. Every file of the package is root:root. No file outside /home belongs to positron-perf (count 347 → 0).")
rep("Fallback slot: Friday 13:00 UTC. Who announces it to alpha's users and to Jeremy?", "The fallback slot (Friday 13:00 UTC) was not needed: the reboot ran at 05:43 UTC on 22 October.")
rep("and the <code>arm</code> session on tty1 is an idle shell under <code>/bin/login</code> with 0.05 s of CPU time in 33 hours, that is a console left logged in, not a job. Jibin runs the reboot (I cannot, see A5), in this order: P1b (before 06:28 UTC, when apt-daily-upgrade fires), P1d, the A8 drop-in, the P2 drop-in and <code>update-grub</code>, the reboot, then the P2 checks.",
    "and the <code>arm</code> session on tty1 was an idle shell under <code>/bin/login</code> with 0.05 s of CPU time in 33 hours, that is a console left logged in, not a job. Jibin ran the steps in this order: P1d (about 05:25 UTC), P1b (05:30–05:33), P1c and the A8 drop-in (05:34), P1a (05:36), then the P2 drop-in, <code>update-grub</code> and the reboot (05:43), then the P2 checks.")
rep("(2) Went in at 05:34 UTC as a drop-in,", "(2) Added at 05:34 UTC as a drop-in,")
rep("Yes, that answers it. Both keys are Jeremy's", "Yes, that answers it from Jibin's own knowledge, so the journal query was not run. Both keys are Jeremy's")
rep("<p><strong>What Jibin ran on 22 October (UTC)</strong>, each verified read-only from <code>positron-perf</code> (commands in section 6): P1d ownership fix (verified 05:26), P1b timers and netperf (05:30–05:33), P1c <code>rcu_normal</code> and the A8 CPUAffinity drop-in (05:34), P1a governor loop (05:36), the P2 drop-in, <code>update-grub</code> and the reboot (05:43, back by 05:44, checks 05:44–05:48). Still to do: the message below (waits on A11) and Arm's answer on the kernel (A6).</p>",
    "<p><strong>What Jibin ran on 22 October (UTC)</strong>, each verified read-only from <code>positron-perf</code> (commands in section 6):</p>\n<ul>\n<li>P1d ownership fix, about 05:25 (verified 05:26).</li>\n<li>P1b timers and netperf, 05:30–05:33.</li>\n<li>P1c <code>rcu_normal</code> and the A8 CPUAffinity drop-in, 05:34.</li>\n<li>P1a governor loop, 05:36.</li>\n<li>P2 drop-in, <code>update-grub</code> and the reboot, 05:43. Host back by 05:44. Checks 05:44–05:52.</li>\n</ul>\n<p>Still to do: the message below (waits on A11) and Arm's answer on the kernel (A6).</p>")
rep("Updated 22 October 05:05 UTC with Jibin's answers. The one line in square brackets", "Updated 22 October 06:00 UTC with Jibin's answers and the as-built state. The one line in square brackets")
# draft message
rep("2. Done tonight (22 Oct UTC): the performance governor on all 128 CPUs, the housekeeping timers paused until\n   6 Nov (apt, fstrim, fwupd, man-db, motd, logrotate and the rest), the netperf server stopped, and\n   rcu_normal=1 (removes the cross-CPU interrupts that service starts send to busy cores).",
    "2. Done 22 Oct 05:30-05:36 UTC (01:30-01:36 EDT): the performance governor on all 128 CPUs, the housekeeping\n   timers paused until 6 Nov (apt, fstrim, fwupd, man-db, motd, logrotate and the rest), the netperf server\n   stopped, and rcu_normal=1 (removes the expedited-RCU cross-CPU interrupts that service starts send to\n   busy cores).")
rep("3. Done tonight: one reboot with cores 126-127 isolated (isolcpus=domain,managed_irq,126-127), default device\n   interrupts kept off cores 120-127 (irqaffinity=0-119), and the governor fixed on the boot line. Cores\n   120-125 are not isolated, so your harness's other threads still get load-balanced across them. The per-CPU\n   NVMe completion interrupts stay and fire only for disk I/O issued from those cores. Check from your account:",
    "3. Done 22 Oct 05:43 UTC (01:43 EDT): one reboot with cores 126-127 isolated (isolcpus=domain,managed_irq,126-127),\n   default device interrupts kept off cores 120-127 (irqaffinity=0-119), and the governor fixed on the boot\n   line. Cores 120-125 are not isolated, so your harness's other threads still get load-balanced across them.\n   Since the reboot every login shell starts with CPU affinity 0-119 (a systemd setting that keeps services\n   and admin sessions off 120-127). Your taskset calls still place threads on 120-127. The per-CPU NVMe\n   completion interrupts stay and fire only for disk I/O issued from those cores. Check from your account:")
rep("Questions (one line each is enough; defaults apply if I hear nothing by Fri 23 Oct 12:00 EDT):", "Questions (one line each is enough). Defaults apply if I hear nothing by Fri 23 Oct 12:00 EDT:")
rep("   windows 2 h ahead, one job at a time, and we touch nothing while the marker exists. Default: Mon-Fri\n   13:00-21:00 UTC, rule accepted.",
    "   windows 2 h ahead, one job at a time, and we touch nothing while the marker exists (each ssh login sends\n   two interrupts to every core, measured). Default: Mon-Fri 13:00-21:00 UTC, rule accepted.")
rep("Q6 May I re-run ~/positron/runs/ev3-churn-job.sh in the positron-perf account (tag govtest-1, about 3 min)", "Q6 May I re-run ~/positron/runs/ev3-churn-job.sh in the positron-perf account (tag govtest-2, about 3 min)")
# section 5
rep("up since 20 Oct 19:06 UTC.", "up since 20 Oct 19:06 UTC at the time of the check (rebooted 22 Oct 05:43 UTC).")
rep("has an idle console session (tty1) since 20 Oct 19:31 UTC.", "had an idle console session (tty1) from 20 Oct 19:31 UTC until the reboot of 22 Oct 05:43 UTC ended it.")
rep("Reboots: 29 Sep (×2), 3 Oct, 5 Oct, 20 Oct.", "Reboots: 29 Sep (×2), 3 Oct, 5 Oct, 20 Oct, and 22 Oct 05:43 UTC (this plan's reboot).")
rep("The reboot must be agreed with every root holder.", "The reboot was agreed with Jibin (A7) and done on 22 Oct 05:43 UTC.")
rep("Nothing is isolated:", "State on 21 October, before the reboot. Nothing was isolated:")
rep("governor schedutil everywhere, limits 1.6–2.8 GHz.", "governor schedutil everywhere at the time of the check (performance everywhere since 22 October 05:36 UTC), limits 1.6–2.8 GHz.")
rep("Measurement: govtest-1 (governor only, before the reboot).", "Measurement: no longer separable, because the reboot of 05:43 UTC came before any re-run. A re-run on the new setup (Q6) measures the clock and the isolation together.")
rep("Since boot (31 h at 01:14 UTC)", "Since boot (30 h at 01:14 UTC)")
rep("one NVMe queue probe interrupt each", "two NVMe queue probe interrupts each (one per disk)")
rep("<p>State on 21 October, from <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct.", "<p>State before Jibin's changes, from <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct.")
rep("They run on housekeeping CPUs once isolation is active.", "They run on housekeeping CPUs now that isolation is active (since the 22 October reboot).")
rep("Optionally disable the socket.", "Optionally disable the socket (not done on 22 October).")
rep("The administrator reads the drop-in (A4).", "The administrator read the drop-in on 22 October (A4): it lets <code>arm</code> open a shell as positron-perf and grants positron-perf nothing.")
rep("package are owned by uid 1001:", "package were owned by uid 1001 until 22 October 05:25 UTC:")
rep("Fix in P1d before any root use of these tools.", "Fixed in P1d by Jibin at about 05:25 UTC on 22 October (verified 05:26 UTC: 0 files outside /home owned by positron-perf).")
# section 6
rep("The live root changes (05:26–05:36 UTC)", "The live root changes (about 05:25–05:36 UTC)")
rep("<li>Ask Arm's SVK contact (A6) for the kernel tree at commit", "<li>Asked on 22 October (A6, answer pending): Arm's SVK contact, for the kernel tree at commit")
rep("<h3>P1. Done 22 October 05:26–05:36 UTC: live root changes, no reboot</h3>", "<h3>P1. Done 22 October about 05:25–05:36 UTC (P1a to P1d, P1e did not run): live root changes, no reboot</h3>")
rep("The command blocks below are the record of what was run, and each result was verified read-only from <code>positron-perf</code>.", "The command blocks below show the commands. The Result lines and section 4 (A5, A8) say which ones were run, and each result was verified read-only from <code>positron-perf</code>.")
rep("Do not use <code>sudo cpupower</code> until P1d is done.", "Do not use <code>sudo cpupower</code> until P1d is done (P1d was done first, at about 05:25 UTC).")
rep("which proved sufficient (128 × performance after the reboot), so the boot-time unit below was not installed and stays as a fallback.", "which proved sufficient (128 × performance after the reboot). The boot-time unit below was therefore not installed. It stays as a fallback.")
rep("<p><strong>P1c. Remove the expedited-RCU IPIs now</strong> (optional, A8, reversible with <code>echo 0</code>).", "<p><strong>P1c. Expedited-RCU IPIs removed, done 05:34 UTC</strong> (A8, reversible with <code>echo 0</code>, reads 1 after the reboot).")
rep("<p><strong>P1d. Fix the ownership of the vendor tool files</strong> (security, A5). Do this before any root use of perf, cpupower or bpftool, and never enable", "<p><strong>P1d. Fix the ownership of the vendor tool files</strong> (security, A5). Done at about 05:25 UTC, verified 05:26 UTC (count 347 → 0). It had to come before any root use of perf, cpupower or bpftool. Never enable")
rep("<p><strong>P1e. Governor-only re-run of Jeremy's job, before the reboot</strong> (only if Jeremy answers Q6 with yes, since A2 says the scripts are his side's).", "<p><strong>P1e. Governor-only re-run of Jeremy's job, before the reboot</strong> (not run, and no longer possible: the reboot came first, so any re-run is govtest-2 in P3, and the clock and isolation effects can no longer be separated).")
rep("moved forward when Jibin approved any idle moment). Every check below passed at 05:44 UTC.", "moved earlier when Jibin approved any idle moment). Every check below passed at 05:44 UTC, and the saved record was taken at 05:46 UTC.")
rep("<p>Add one drop-in. The cloud-image drop-in", "<p>One drop-in was added at 05:43 UTC. The cloud-image drop-in")
rep("The three planned arguments cannot fail the boot:", "The four arguments could not fail the boot:")
rep("# 0-125 for both (variant B: 0-119)", "# PID 1: 0-119 (A8 drop-in), rcu_preempt: 0-125 (variant B: 0-119)")
rep("In a 10 s idle window at 05:46 UTC, CPUs 126 and 127 took no interrupt at all and were 100% idle.</p>", "In a 10 s idle window at 05:46 UTC, CPUs 126 and 127 took no interrupt at all and were 100% idle (the saved 60 s window at 05:50 UTC in <code>ipi-attribution-0552.txt</code> shows the same).</p>")
rep("Figure 6. The proposed split of the 128 CPUs and what reaches each reserved CPU today.", "Figure 6. The split of the 128 CPUs as applied at the 22 October 05:43 UTC reboot (variant A), and what reached each reserved CPU before that reboot (section 5.4 has the counts after it).")
rep("<li>Compare with churn-r1 and govtest-1: the judge verdict", "<li>Compare with churn-r1 (govtest-1 never ran): the judge verdict")
rep("(and expedited-RCU IPIs, if rcu_normal stays off)", "(and two broadcast IPIs per ssh login even with rcu_normal=1, measured 05:50 UTC)")
rep("nohz_full=126-127 rcu_nocbs=126-127 irqaffinity=0-119 cpufreq.default_governor=performance", "nohz_full=126-127 rcu_nocbs=126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1")
rep("If the reboot cannot happen by Friday: a no-reboot fallback", "A no-reboot fallback (not needed: the reboot happened on 22 October 05:43 UTC, kept for the record)")
rep("Use it only if the reboot slips", "The reboot did not slip, so this was not used. Use it only if isolation must change without a reboot")
rep("and disable the unit.", "and, for the next boot, remove <code>cpufreq.default_governor=performance</code> from the GRUB drop-in and run <code>update-grub</code> (no unit was installed).")
rep(", and drop the boot argument.</li>", ", and drop the boot argument. Service CPU affinity: remove <code>/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf</code> and run <code>systemctl daemon-reexec</code>, or reboot.</li>")
# section 7 and 8
rep("compared with churn-r1 and govtest-1", "compared with churn-r1")
rep("No file was written on the host, no sudo was used, and no setting changed.", "No file was written on the host, no sudo was used, and no setting was changed by these checks. The as-built verification of 22 October (05:44–05:52 UTC) added five ssh logins as positron-perf and three interrupt-count windows (10 s, 60 s and 25 s).")
rep("<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks from <code>positron-perf</code> after each of Jibin's changes and after the reboot, saved as", "<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks ran from <code>positron-perf</code> after each of Jibin's changes. The post-reboot results are saved as")
rep("<li>Which key each of Jeremy's sessions used is unrecorded, and that alpha's sessions were Jeremy's agents is Jibin's inference from timing, not a log entry. Sources that would settle both: the root-only sshd journal lines, and Jeremy's reply to item 1 of the message.</li>",
    "<li>That alpha's sessions were Jeremy's agents is Jibin's inference from timing, not a log entry (A10 closed the key question: both of Jeremy's keys logged in). Source that would settle it: Jeremy's reply to item 1 of the message.</li>")
rep("the laptop key was not), and whether to keep outbound internet", "the laptop login worked too, A10), and whether to keep outbound internet")

miss=[(o,s.count(o)) for o,n in R if s.count(o)!=1]
if miss:
    print("NOT APPLIED. mismatches:")
    for o,c in miss: print(f"  count={c}: {o[:110]!r}")
    sys.exit(1)
for o,n in R: s=s.replace(o,n)
open(p,"w",encoding="utf-8").write(s); print(f"applied {len(R)} replacements")
