import re
p="build_plan.py"; s=open(p,encoding="utf-8").read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(s.count(old),old[:70]); s=s.replace(old,new)
def repline(prefix,newline):
    """replace the single source line that starts with prefix"""
    global s
    m=[ln for ln in s.split("\n") if ln.startswith(prefix)]
    assert len(m)==1,(prefix,len(m)); s=s.replace(m[0],newline)

# header, short version, footer
rep("Written for Jibin on 21 October 2026 and revised the same evening at 19:40 PDT (22 October 02:40 UTC) after a verification pass by 20 independent agents, and again at 22:05 PDT (22 October 05:05 UTC) with Jibin's answers to the administrator questions in section 4.",
    "Written for Jibin on 21 October 2026 and revised three times on 22 October (UTC): at 02:40 after a verification pass by 20 independent agents, at 05:05 with Jibin's answers to the administrator questions (section 4), and at 06:00 as the as-built record after Jibin made the host changes from the <code>jhan</code> account between 05:26 and 05:43 UTC, each verified read-only from <code>positron-perf</code>.")
rep("No setting, file or service on the host was changed by this check.",
    "No setting, file or service on the host was changed by these checks. The changes of 22 October were made by Jibin.")
rep("<p>The host side can set the performance governor and isolate cores with one reboot tonight (Jibin approved a reboot at any idle moment on 22 October), but nohz_full needs a rebuilt kernel from Arm.</p>",
    "<p>The host side is done: on 22 October Jibin set the performance governor, paused the housekeeping timers and rebooted at 05:43 UTC with cores 126–127 isolated (verified at 05:44 UTC), but nohz_full still needs a rebuilt kernel from Arm.</p>")
rep("<p>Monday's counted runs therefore also need Jeremy to pin that thread, and six questions for him (plus eleven for the administrator) carry defaults, so the host work starts now.</p>",
    "<p>Monday's counted runs therefore also need Jeremy to pin that thread, and six questions for him carry defaults, so the message in section 4 is the next step (it waits on question A11).</p>")
rep("revised 22 October 02:40 UTC and 05:05 UTC.", "revised 22 October 02:40, 05:05 and 06:00 UTC (as-built).")

# section 3 rows
repline('    ("Fixed clock: performance governor", LIVE,',
        '    ("Fixed clock: performance governor", DONE, "Done 22 Oct 05:36 UTC by a sysfs write from <code>jhan</code>, and persistent through the boot argument <code>cpufreq.default_governor=performance</code>: 128 × performance after the 05:43 UTC reboot, request 2,800 MHz on every CPU (verified).", "yes", "no", "no", "nice: all 128 CPUs or only 120–127 (all 128 applied)"),')
repline('    ("Isolated cores (isolcpus) with IRQs kept off", REBOOT,',
        '    ("Isolated cores (isolcpus) with IRQs kept off", DONE, "Done at the 22 Oct 05:43 UTC reboot: isolated list 126-127, default interrupt mask CPUs 0-119, workqueues off 126-127, no kernel warning (verified 05:44 UTC). “IRQs kept off” is only partly achievable: the timer tick and IPIs stay, and the per-CPU NVMe queue interrupts cannot be moved (they fire only for disk I/O issued from that CPU). Section 5.4 has the idle-host interrupt counts after the reboot.", "yes", "yes", "no", "yes: D3 (which CPUs, and the job\'s launch command); 126-127 applied by default"),')
repline('    ("Nothing else running during timed runs, nightly window", PART,',
        '    ("Nothing else running during timed runs, nightly window", PART, "Host side done 22 Oct 05:30–05:33 UTC: 11 timers disabled, tmpfiles-clean masked, netperf stopped and disabled (sysstat kept, A8). The host is near idle. The reservation rule and the windows (D4) are still Jeremy\'s to accept.", "yes", "no", "no", "yes: D4 (windows in UTC)"),')
repline('    ("Account and one isolated core by Friday 23 Oct", REBOOT,',
        '    ("Account and one isolated core by Friday 23 Oct", DONE, "Done on 22 Oct, one day early, without nohz_full: the account since 21 Oct, CPUs 126-127 isolated and the performance governor since the 05:43 UTC reboot. “Friday” in Jeremy\'s time zone ends Fri 23 Oct 21:00 UTC (14:00 PDT).", "yes", "yes", "no", "yes: D1"),')
repline('    ("No sudo for the account", DONE,',
        '    ("No sudo for the account", DONE, "No usable sudo: password locked, no password-free sudo rule. The 49-byte file <code>/etc/sudoers.d/positron-perf-setup</code> (created 21 Oct 05:12 UTC) lets the <code>arm</code> account open a shell as positron-perf and grants positron-perf nothing (A4, read by Jibin 22 Oct).", "no", "no", "no", "no"),')

# section 4 intro, admin table cells, tonight paragraph, draft bracket
rep("the GRUB change and tonight's reboot can all be done from an administrator account without Jeremy.",
    "the GRUB change and the reboot were all done by Jibin on 22 October without Jeremy.")
a=s.index('""" + TODOQ + """ Jibin runs it.'); b=s.index("(expect root root).</td></tr>",a)+len("(expect root root).</td></tr>")
s=s[:a]+'""" + CLOSED + """ Done by Jibin at about 05:25 UTC on 22 October and verified from positron-perf at 05:26 UTC: <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code> and the cpupower unit are root-owned, every file of the package is root:root, and no file outside /home belongs to positron-perf (count 347 → 0).</td></tr>'+s[b:]
rep("Figure 5 (the timeline) still shows the Thursday slot and will be redrawn as the as-built record after the reboot.",
    "Outcome: Jibin rebooted at 05:43 UTC on 22 October, the host was back by 05:44 UTC, and every P2 check passed (evidence file <code>verification-2026-10-22/postreboot-0545.txt</code>).")
rep("All three accepted. (1) <code>rcu_normal=1</code> goes live in P1c and persists through the P2 boot argument. (2) Goes in as a drop-in,",
    "All three accepted and done. (1) <code>rcu_normal=1</code> went live at 05:34 UTC and persists through the boot argument (reads 1 after the reboot). (2) Went in at 05:34 UTC as a drop-in,")
rep("<p><strong>What Jibin runs tonight, in this order</strong> (the commands are in section 6): P1b timers and netperf (before 06:28 UTC, when apt-daily-upgrade fires), P1d ownership fix, P1c <code>rcu_normal</code>, the A8 CPUAffinity drop-in, P1a governor loop (covers Friday if the reboot slips), the P2 drop-in and <code>update-grub</code>, the reboot with the BMC console open, the P2 checks, then the message below.</p>",
    "<p><strong>What Jibin ran on 22 October (UTC)</strong>, each verified read-only from <code>positron-perf</code> (commands in section 6): P1d ownership fix (verified 05:26), P1b timers and netperf (05:30–05:33), P1c <code>rcu_normal</code> and the A8 CPUAffinity drop-in (05:34), P1a governor loop (05:36), the P2 drop-in, <code>update-grub</code> and the reboot (05:43, back by 05:44, checks 05:44–05:48). Still to do: the message below (waits on A11) and Arm's answer on the kernel (A6).</p>")
rep("   [Jibin: send after the reboot. If it slipped, put items 2 and 3 in the future tense and say when.]\n", "   I verified these at 05:44 UTC, right after the reboot.\n")
rep("The two lines in square brackets are notes to Jibin and must be removed before sending.</p>",
    "The one line in square brackets is a note to Jibin and must be removed before sending.</p>")
rep("<h3>Draft message to Jeremy (send tonight, after the reboot)</h3>", "<h3>Draft message to Jeremy (ready to send once A11 is answered)</h3>")

# 5.5 intro
rep("<p>From <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct. Next firings are in UTC. The proposed run window is 13:00–21:00 UTC.</p>",
    "<p>State on 21 October, from <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct. Next firings are in UTC. The proposed run window is 13:00–21:00 UTC. On 22 October at 05:30–05:33 UTC Jibin applied the Action column: every unit listed for disabling or masking is now inactive, netperf is stopped and disabled, and the sysstat timers were kept (verified).</p>")

# figure 5 caption, P0, P1, P2, P3
rep("Figure 5. Timeline from 21 October to the 5 November demo. The reboot is proposed for Thursday 22 October 15:00 UTC. The kernel rebuild runs in parallel and does not block Friday.",
    "Figure 5. Timeline from 21 October to the 5 November demo, as built. The live root changes (05:26–05:36 UTC) and the reboot (05:43 UTC) were done on 22 October, one day before the Friday deadline. The kernel rebuild runs in parallel and does not block Friday.")
rep("The bottom row marks the host timers that can disturb a run until they are paused, the two weekly fstrim runs, and the US clock change on Sunday 1 November.",
    "The bottom row marks the host timers, which fired until they were paused at 05:30 UTC on 22 October (gray marks show when they would have fired), the two weekly fstrim runs (paused), and the US clock change on Sunday 1 November.")
rep("<li>Reboot slot (A7): Jibin approved rebooting as soon as the host is idle, which it was at 04:41 UTC on 22 October. P2 can run tonight, after P1b and P1d.</li>",
    "<li>Reboot slot (A7): Jibin approved rebooting as soon as the host is idle, and rebooted at 05:43 UTC on 22 October, after P1b and P1d.</li>")
rep("<h3>P1. Tonight or Thursday morning: live root changes, no reboot</h3><div class=\"meta\">Owner: an administrator account (<code>arm</code> or <code>jhan</code>). Reboot: no. Reversible in seconds. P1b must happen before Thu 22 Oct 06:28 UTC (Wed 23:28 PDT), when apt-daily-upgrade fires next.</div>",
    "<h3>P1. Done 22 October 05:26–05:36 UTC: live root changes, no reboot</h3><div class=\"meta\">Owner: Jibin, from the <code>jhan</code> account. Reboot: no. Reversible in seconds. P1b was done at 05:30 UTC, before the 06:28 UTC apt run. The command blocks below are the record of what was run, and each result was verified read-only from <code>positron-perf</code>.</div>")
rep("<p>This write does not survive a reboot (the kernel's default governor is schedutil). Persistence comes from the boot argument <code>cpufreq.default_governor=performance</code> in P2 and, as a second safety, a boot-time unit.",
    "<p>Result: done at 05:36 UTC, 128 × performance. This write does not survive a reboot (the kernel's default governor is schedutil). Persistence comes from the boot argument <code>cpufreq.default_governor=performance</code> in P2, which proved sufficient (128 × performance after the reboot), so the boot-time unit below was not installed and stays as a fallback.")
rep("<h3>P2. Reboot into isolcpus, about 15 minutes of downtime (approved by Jibin on 22 October for any idle moment, so tonight; first proposed for Thursday 15:00 UTC)</h3><div class=\"meta\">Owner: an administrator account, with Jibin. Reboot: yes, once. Agree the time with every root holder and with Jeremy first. Fallback slot: Friday 13:00 UTC.</div>",
    "<h3>P2. Done 22 October 05:43 UTC: reboot into isolcpus (host back by 05:44 UTC)</h3><div class=\"meta\">Owner: Jibin, from the <code>jhan</code> account, with the BMC console available. Reboot: done once (first proposed for Thursday 15:00 UTC, moved forward when Jibin approved any idle moment). Every check below passed at 05:44 UTC. Evidence: <code>verification-2026-10-22/postreboot-0545.txt</code>.</div>")
rep("<h3>P3. Thursday 22 to Friday 23 October: validate, then hand off</h3>",
    "<h3>P3. 22 to 23 October: validate (host checks passed 22 Oct 05:44 UTC), then hand off</h3>")
# P2 results paragraph after the check block (anchor: the figure 6 call)
rep('A(fig("fig_cpu_alloc", "Figure 6.',
    'A("""<p><strong>Result, 22 October 05:44–05:48 UTC</strong> (read-only, as <code>positron-perf</code>): the boot line carries the four arguments and both console settings. The isolated list is 126-127. All 128 policies run performance at a 2,800 MHz request. <code>rcu_normal</code> reads 1 and dmesg says “No expedited grace period (rcu_normal)”. The workqueue mask excludes 126-127 and the isolated mask holds exactly them. The default interrupt mask is CPUs 0-119. PID 1 is allowed 0-119 (the A8 drop-in, not the kernel), <code>rcu_preempt</code> 0-125. <code>taskset -c 127 true</code> works. The filtered dmesg grep printed nothing. The eleven timers are disabled, tmpfiles-clean is masked, netperf is inactive and netserver is gone. Only Jibin was logged in (the console session on tty1 ended with the reboot). In a 10 s idle window at 05:46 UTC, CPUs 126 and 127 took no interrupt at all and were 100% idle.</p>""")\nA(fig("fig_cpu_alloc", "Figure 6.')

# section 7 table: add a status column
rep('<table><tr><th style="width:24%">Check</th><th>Evidence to keep</th><th style="width:34%">Ready means</th></tr>',
    '<table><tr><th style="width:20%">Check</th><th>Evidence to keep</th><th style="width:28%">Ready means</th><th style="width:24%">Status 22 Oct 05:48 UTC</th></tr>')
status7 = {
 "Boot arguments took effect": '""" + DONE + """ Passed: isolated 126-127, dmesg grep empty, masks as expected, PID 1 on 0-119 (A8 drop-in).',
 "Clock": '""" + PARTQ + """ 128 × performance verified. The counter pair around a run is still pending (needs Jeremy\'s run or Q6).',
 "Interrupts and workers off the isolated CPUs": '""" + PARTQ + """ Idle host: zero interrupts on 126-127 in 10 s. The run-time difference is pending.',
 "Thread placement": '""" + OPENQ + """ Pending: needs a run on the new setup (Q6 or Jeremy\'s own run).',
 "Jeremy's job on the new setup": '""" + OPENQ + """ Pending: Q6, or Jeremy\'s first run next week.',
 "Quiet host": '""" + DONE + """ Timers off, netserver gone, only Jibin logged in (verified 05:48 UTC).',
 "Ownership fixed": '""" + DONE + """ 0 files (verified 05:26 UTC).',
 "Hand-off note sent": '""" + OPENQ + """ Draft ready in section 4, waits on A11.',
}
for key,cell in status7.items():
    i=s.index(f"<tr><td>{key}</td>"); j=s.index("</tr>",i)
    s=s[:j]+f"<td>{cell}</td>"+s[j:]

# section 8: evidence bullet and insufficient-data edits
rep("<h3>Insufficient data</h3>\n<ul>\n<li>Who at Arm can provide the vendor kernel's source at <code>4dbc8bb88858</code> or a NO_HZ_FULL build, and by when. Source: the SVK contact (A6).</li>",
    "<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks from <code>positron-perf</code> after each of Jibin's changes and after the reboot, saved as <code>verification-2026-10-22/postreboot-0545.txt</code> and <code>ipi-attribution-0552.txt</code>.</li>\n<h3>Insufficient data</h3>\n<ul>\n<li>Who at Arm can provide the vendor kernel's source at <code>4dbc8bb88858</code> or a NO_HZ_FULL build, and by when. Source: the SVK contact, asked by Jibin on 22 October (A6).</li>")
rep("<li>Console or BMC access for the reboot, the meaning of EFI boot entry 0010, and whether the second disk holds another operating system. Source: the administrator (A3).</li>",
    "<li>The meaning of EFI boot entry 0010, and whether the second disk holds another operating system (A3, not blocking: the reboot of 22 October came up on the vendor kernel as before).</li>")
rep("<li>What <code>/etc/sudoers.d/positron-perf-setup</code> grants. Source: the administrator (A4).</li>\n", "")
open(p,"w",encoding="utf-8").write(s); print("as-built patch applied")
for pat in ["Thursday", "tonight", "Tonight", "15:00 UTC"]:
    print(f"{pat!r}: {len(re.findall(pat, s))} left")
