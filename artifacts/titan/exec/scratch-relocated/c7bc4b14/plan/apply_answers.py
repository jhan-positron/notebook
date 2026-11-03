import re, sys
p = "build_plan.py"
s = open(p, encoding="utf-8").read()
n_before = len(s)

def rep(old, new, count=1):
    global s
    c = s.count(old)
    assert c == count, f"expected {count} match(es), found {c} for: {old[:70]!r}"
    s = s.replace(old, new)

# R1 header revision line
rep("revised the same evening at 19:40 PDT (22 October 02:40 UTC) after a verification pass by 20 independent agents.",
    "revised the same evening at 19:40 PDT (22 October 02:40 UTC) after a verification pass by 20 independent agents, and again at 21:50 PDT (22 October 04:50 UTC) with Jibin's answers to the administrator questions in section 4.")

# R2 short version, sentence 2
rep("<p>The host side can set the performance governor tonight and isolate cores with one reboot on Thursday, but nohz_full needs a rebuilt kernel from Arm.</p>",
    "<p>The host side can set the performance governor and isolate cores with one reboot tonight (Jibin approved a reboot at any idle moment on 22 October), but nohz_full needs a rebuilt kernel from Arm.</p>")

# R3 note callout
rep("The plan assumes <code>jhan</code> is Jibin's own account (question A1).</div>",
    "Jibin confirmed on 22 October that <code>jhan</code> is Jibin's own account and that <code>arm</code> is shared by every engineer on the phoenix-crb project (question A1).</div>")

# R4 glossary
rep('("jhan (account)", "A second administrator account (user id 1002, group sudo) created on phoenix-crb on 22 October 01:19 UTC from Jibin\'s workstation while this analysis ran."),',
    '("jhan (account)", "A second administrator account (user id 1002, group sudo) created on phoenix-crb on 22 October 01:19 UTC from Jibin\'s workstation while this analysis ran. Confirmed as Jibin\'s own account on 22 October (A1)."),')
rep('("arm (account)", "The administrator account on phoenix-crb (user id 1000, group sudo). Root steps below are run from it or from <code>jhan</code>."),',
    '("arm (account)", "The shared administrator account on phoenix-crb (user id 1000, group sudo), used by every engineer on the phoenix-crb project (A1, confirmed 22 October). Root steps below are run from it or from <code>jhan</code>."),')

# R11 chip style for open items
m = re.search(r"\.chip\.kernel\{[^}]*\}", s)
assert m, "chip.kernel css not found"
s = s[:m.end()] + ".chip.open{background:#fbdccd;color:#7a3410}" + s[m.end():]
rep('NA = chip("gray", "– not needed"); PART = chip("gray", "◑ partly"); NOTDONE = chip("gray", "○ not done")',
    'NA = chip("gray", "– not needed"); PART = chip("gray", "◑ partly"); NOTDONE = chip("gray", "○ not done")\n'
    'CLOSED = chip("done", "✔ closed"); OPENQ = chip("open", "○ open"); PARTQ = chip("open", "◑ partly open"); TODOQ = chip("open", "● to do (Jibin)")')

# R5 + R6: replace the admin table and the draft message
start = s.index("<h3>Questions for the administrator (Jibin), none of them blocking the host work</h3>")
end_marker = "</pre></blockquote>\n</section>\"\"\")"
end = s.index(end_marker, start) + len("</pre></blockquote>\n")
old_block = s[start:end]
assert old_block.count("<tr><td>A11</td>") == 1 and "Draft message to Jeremy" in old_block

rows = [
 ("A1", "Is <code>jhan</code> (uid 1002, sudo, created 22 Oct 01:19 UTC from 192.168.2.136) your account, and is <code>arm</code> yours too?",
  "The hand-off must record who holds root and which account made Thursday's changes.",
  "CLOSED", "Yes on both counts: <code>jhan</code> is Jibin's account, and <code>arm</code> is a shared account used by every engineer on the phoenix-crb project. Consequence: the reservation rule (D4) must reach every <code>arm</code> user, and the hand-off records the changes as made from <code>jhan</code>."),
 ("A2", "Is alpha (192.168.1.200) your machine? Were the staging sessions from alpha (17:07–18:58 UTC 21 Oct), the toolchain README (“approved by Jeremy that day”) and the churn-r1 run done by your side on Jeremy's behalf?",
  "Decides D6 (re-runs need no permission) and who else must know the reservation rule. A further admin address, 192.168.2.213, used <code>arm</code> on 29 Sep.",
  "OPENQ", "Jibin asked whether this matters. It does, in two ways, and it is not blocking. (1) About 50 <code>positron-perf</code> sessions from alpha staged the SDK workspace and ran churn-r1 on 21 October between 17:07 and 18:32 UTC, while sw-dev-01 (Jeremy's machine) opened four sessions in the same window [phoenix-crb-round6.txt]. If the alpha sessions were an agent on Jibin's side acting on Jeremy's instructions, Jibin may re-run the job (D6 becomes yes), Q6 drops out of the message, and that run's hiccup outputs are already on Jibin's side. (2) If they were Jeremy working through alpha, Jeremy holds an account on alpha, and alpha's users must get the reservation rule. One sentence answers it: who ran the ssh sessions from alpha on 21 October between 17:07 and 18:32 UTC?"),
 ("A3", "Is there out-of-band access (BMC address and credentials, or physical access) before the reboot? What is EFI boot entry 0010 (first in BootOrder while BootCurrent is 0001)? Is the second disk nvme1n1 (200 MB vfat plus 1.7 TB xfs, Boot0002) another operating system?",
  "The three planned boot arguments cannot fail the boot (bad values are warned about and dropped), but any other boot fault needs console access. A BMC chip is present (ASPEED AST1150), but no <code>/dev/ipmi*</code> device exists, and the GRUB menu is on the EFI console.",
  "PARTQ", "BMC access exists and Jibin has it, which is the console path the reboot needed. Entry 0010 and the second disk stay unknown, and neither blocks the reboot: the planned boot arguments cannot fail the boot, the GRUB saved entry still names the vendor kernel, and the host booted the vendor kernel at each of its last three boots (3, 5 and 20 October) as recorded by <code>last</code>. Suggested: open the BMC console before the reboot and watch the boot."),
 ("A4", "What does <code>/etc/sudoers.d/positron-perf-setup</code> (49 bytes, 21 Oct 05:12 UTC) grant? <code>sudo cat</code> it and run <code>sudo visudo -cf</code> on it.",
  "It grants nothing usable today. If it was meant to give cpupower or governor control, it must not reference <code>/usr/bin/cpupower</code> while that file is owned by positron-perf.",
  "CLOSED", "Content: <code>arm ALL=(positron-perf) NOPASSWD: /usr/bin/bash</code>, and it parses. It lets the <code>arm</code> account open a shell as positron-perf without a password. It grants positron-perf nothing and does not reference cpupower, so nothing needs to change. Side effect worth knowing: every <code>arm</code> user can read and change Jeremy's workspace through it."),
 ("A5", "Fix the <code>linux-tools</code> ownership (step P1d) before any root use of perf, cpupower or bpftool.",
  "Security: 347 files under /usr, /etc and /lib are owned by uid 1001.",
  "TODOQ", "Jibin runs it. I cannot: my access is the <code>positron-perf</code> account, which has no sudo, and my rule for this host is read-only. At 04:41 UTC on 22 October <code>/usr/bin/perf</code> and <code>/usr/bin/cpupower</code> were still owned by positron-perf. After the change I verify from positron-perf with <code>ls -l /usr/bin/perf /usr/bin/cpupower</code> (expect root root)."),
 ("A6", "Is there a channel to Arm's software validation kit (SVK) team to ask for the kernel tree at <code>4dbc8bb88858</code> with its config, or for a build with <code>CONFIG_NO_HZ_FULL=y</code>? What date is realistic?",
  "The package maintainer is an arm.com address (<code>avadnaik@2paltra-216.5g.ast.arm.com</code>). The source is not on the host. Secure Boot is off, so a local build needs no signing.",
  "OPENQ", "Jibin has asked Arm. Is it blocking? It blocks only nohz_full and rcu_nocbs. It does not block Friday: the account, the isolated core and the governor come from the current kernel. It blocks the 5 November demo only if Jeremy answers D2 with the perf lane, which refuses a host without nohz_full. If Jeremy picks the latency judge (the default), the rebuilt kernel is wanted but not required before the demo."),
 ("A7", "Reboot slot Thursday 22 Oct 15:00 UTC (08:00 PDT, 11:00 EDT), 10 to 15 minutes: agreed? The idle <code>arm</code> console session on tty1 (since 20 Oct 19:31 UTC) ends with the reboot.",
  "Fallback slot: Friday 13:00 UTC. Who announces it to alpha's users and to Jeremy?",
  "CLOSED", "Reboot approved for any time the host is idle, so tonight. State at 04:41 UTC on 22 October: no positron-perf process, load 0.00, and the <code>arm</code> session on tty1 is an idle shell under <code>/bin/login</code> with 0.05 s of CPU time in 33 hours, that is a console left logged in, not a job. Jibin runs the reboot (I cannot, see A5), in this order: P1b (before 06:28 UTC, when apt-daily-upgrade fires), P1d, the A8 drop-in, the P2 drop-in and <code>update-grub</code>, the reboot, then the P2 checks. The P1a service is unnecessary when the boot argument <code>cpufreq.default_governor=performance</code> is used: the performance governor is built into this kernel (<code>CONFIG_CPU_FREQ_GOV_PERFORMANCE=y</code>), and the parameter exists (<code>/sys/module/cpufreq/parameters/default_governor</code>). Figure 5 (the timeline) still shows the Thursday slot and will be redrawn as the as-built record after the reboot."),
 ("A8", "Three optional live settings: (1) <code>rcu_normal=1</code> (removes function-call IPIs to the pass core from service starts and namespace teardowns, makes expedited grace periods normal ones, milliseconds slower for mounts), (2) <code>CPUAffinity=0-119</code> in <code>/etc/systemd/system.conf</code> (keeps every service off 120–127 now, needs <code>daemon-reexec</code>), (3) keep <code>sysstat-collect.timer</code> for 10-minute sar history as quiet-window evidence, or disable it.",
  "Each is reversible. The plan includes (1) and keeps (3) by default.",
  "CLOSED", "All three accepted. (1) <code>rcu_normal=1</code> goes live in P1c and persists through the P2 boot argument. (2) Goes in as a drop-in, <code>/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf</code> with <code>[Manager]</code> and <code>CPUAffinity=0-119</code>, which the reboot applies to every service and login shell. It keeps admin sessions and services off the job's six worker CPUs as well as off 126–127. After it, the P2 check of PID 1 shows <code>0-119</code> instead of <code>0-125</code>. Jeremy's <code>taskset</code> still works: an explicit affinity call may name CPUs outside the inherited mask. (3) The sysstat timers stay for the 10-minute history."),
 ("A9", "Hardening, not a demo blocker: sshd allows root password login (<code>PermitRootLogin yes</code>, <code>PasswordAuthentication yes</code> in the main file and three drop-ins). Should the kernel meta-packages be held (<code>apt-mark hold linux-image-virtual linux-headers-virtual linux-virtual</code>) so apt never installs kernels again?",
  "Root password login is a second privileged path that the reservation rule cannot see.",
  "CLOSED", "Deferred by Jibin: not a demo blocker, so no change now. Mitigation already in the plan: the apt timers are disabled in P1b, so apt installs no kernel during the run period."),
 ("A10", "Close the “which key did Jeremy use” question from the system journal: <code>sudo journalctl _COMM=sshd -g \"Accepted publickey for positron-perf\" --since 2026-10-21 -o short-iso</code>.",
  "The account's own journal does not contain the “Accepted” lines.",
  "CLOSED", "Yes, that answers it. Both keys are Jeremy's (laptop = <code>jeremy@DESKTOP-V2B1166</code>, and <code>jeremy@sw-dev-01</code>), and both logins worked. The journal query is no longer needed. Still open for the record: whether alpha's sessions were Jeremy's (A2)."),
 ("A11", "Do you accept that the Friday promise excludes nohz_full and rcu_nocbs, and that Monday's runs may still be void for SDK-side reasons, so that the message to Jeremy says so explicitly?",
  "The message below says both.",
  "OPENQ", "Jibin will answer after reading the plan. It does not block the host work. It gates the message: items 4 and 5 of the draft below are the two statements, and the draft assumes yes."),
]
# keep the original question/why text verbatim: check each against the old block
for qid, qtext, why, chipname, status in rows:
    assert f"<tr><td>{qid}</td><td>{qtext}</td><td>{why}</td></tr>" in old_block, f"row {qid} text drifted"

tbl = ['<h3>Questions for the administrator (Jibin), none of them blocking the host work</h3>',
       '<p>Jibin answered these on 22 October at about 04:30 UTC. The fourth column records the answer and whether the question is still open.</p>',
       '<table><tr><th style="width:4%">#</th><th style="width:25%">Question</th><th style="width:24%">Why</th><th>Answer and status (22 Oct)</th></tr>']
for qid, qtext, why, chipname, status in rows:
    tbl.append(f'<tr><td>{qid}</td><td>{qtext}</td><td>{why}</td><td>{{{chipname}}} {status}</td></tr>')
tbl.append('</table>')
tbl.append('<p><strong>What Jibin runs tonight, in this order</strong> (the commands are in section 6): P1b timers and netperf (before 06:28 UTC, when apt-daily-upgrade fires), P1d ownership fix, P1c <code>rcu_normal</code>, the A8 CPUAffinity drop-in, P1a governor loop (covers Friday if the reboot slips), the P2 drop-in and <code>update-grub</code>, the reboot with the BMC console open, the P2 checks, then the message below.</p>')
tbl.append('<h3>Draft message to Jeremy (send tonight, after the reboot)</h3>')
tbl.append('<p>Updated 22 October 04:50 UTC with Jibin\'s answers. Lines in square brackets are notes to Jibin and must be removed before sending.</p>')
msg = r"""Jeremy, status on phoenix-crb (the Phoenix CRB, 192.168.2.45), 22 Oct:

1. Your account, keys, toolchain and disk are in place, and your logins from the laptop and from sw-dev-01
   worked. The churn-r1 run from 21 Oct is on the host.
2. Done tonight (22 Oct UTC): the performance governor on all 128 CPUs, the housekeeping timers paused until
   6 Nov (apt, fstrim, fwupd, man-db, motd, logrotate and the rest), the netperf server stopped, and
   rcu_normal=1 (removes the cross-CPU interrupts that service starts send to busy cores).
3. Done tonight: one reboot with cores 126-127 isolated (isolcpus=domain,managed_irq,126-127), default device
   interrupts kept off cores 120-127 (irqaffinity=0-119), and the governor fixed on the boot line. Cores
   120-125 are not isolated, so your harness's other threads still get load-balanced across them. The per-CPU
   NVMe completion interrupts stay and fire only for disk I/O issued from those cores. Check from your account:
     cat /sys/devices/system/cpu/isolated                              -> 126-127
     cat /sys/devices/system/cpu/cpufreq/policy127/scaling_governor    -> performance
     cat /proc/cmdline                                                 -> carries the arguments above
   [Jibin: send after the reboot. If it slipped, put items 2 and 3 in the future tense and say when.]
4. nohz_full and rcu_nocbs are not possible on the running kernel (built without CONFIG_NO_HZ_FULL) and are
   not expected by Friday. They need a rebuilt kernel, which I have requested from Arm. Until then a busy
   isolated core keeps the 250 Hz timer tick (one interrupt every 4 ms, about 1-2 us each).
5. churn-r1 was voided because the fake device's MEAN lateness (6.25 us) exceeded the 2.5 us band, not by
   missing isolation. The host clock alone does not explain it: your hiccup probe in sleep mode on an idle
   core under schedutil gives mean lateness 0.02 us (0 of 2000 cycles over 2.5 us). During churn-r1 the device
   thread shared cores 120-126 with the other threads, those cores sat at 1.6 GHz, and they took 1,300-7,700
   interrupts/s (the threads' own timed sleeps). So the host changes above may not make Monday's runs count
   by themselves. See Q4.
   [Jibin: items 4 and 5 are the two statements of question A11.]
6. The host has outbound internet, and your pip install used it (wheels downloaded on the host). I will keep it.
7. The host is shared: the arm account is used by every engineer on the phoenix-crb project. The reservation
   rule in Q5 is how we keep everyone off the host during your windows.

Needed change to your launch line, now that 126-127 are isolated: isolated cores get no load balancing, so a
process that lands on one stays there. Run the label with the CPU set 120-125,127 and start it as
  taskset -c 120-125 taskset -c 120-125,127 prlimit ... bash tools/ci/run_scheduled_gate.sh churn ...
so that the shell and Python never land on 126 or 127. churn.py then pins the pass thread to 127 (the last CPU
of the set), and 126 stays free for a pinned device thread.

Questions (one line each is enough; defaults apply if I hear nothing by Fri 23 Oct 12:00 EDT):
Q1 Which of your notes is newest? Does Friday 23 Oct still stand, and is a Friday host WITHOUT nohz_full and
   rcu_nocbs acceptable for Monday's counted runs? Default: Friday stands, yes.
Q2 Which path produces the numbers that count on 5 Nov: the churn label + latency judge (runs on the current
   kernel, needs only a pinned pass thread) or tools/perf (refuses any host without isolcpus AND nohz_full)?
   Default: the judge. If tools/perf, the rebuilt kernel is on the critical path and Arm's date decides.
Q3 Cores: I isolated 126-127 (127 for the pass thread, 126 free for a pinned device thread). If you want 127
   only, or all of 120-127 (only if you pin every thread), say so and I reboot again while the host is idle.
   Default: keep 126-127 with the launch-line change above.
Q4 Will you pin the fake device thread to its own core (126) and give it a 1 us timer slack, as the waker has,
   before Monday? Has any churn run ever recorded device.void=false, and with what late_mean? Default: you
   decide; 126 stays free.
Q5 Run windows 26 Oct-5 Nov in UTC only (US clocks change Sun 1 Nov), and this reservation rule: your job
   writes /tmp/positron-perf.RUNNING (start, end, pid, tag) and removes it at the end, you announce counted
   windows 2 h ahead, one job at a time, and we touch nothing while the marker exists. Default: Mon-Fri
   13:00-21:00 UTC, rule accepted.
Q6 May I re-run ~/positron/runs/ev3-churn-job.sh in the positron-perf account (tag govtest-1, about 3 min)
   for a before/after late_mean comparison with churn-r1? Default: no.
   [Jibin: drop Q6 if the 21 Oct staging and churn-r1 were run from your side (question A2).]
Nice to have: is this clock pass rule acceptable: delivered clock >= 2772 MHz from one CPPC counter pair read
before and after the run on core 127 (no polling during a run)? Status of the sampling tests and the timed
compile. If tools/perf is your path: clang and ninja are not on the account's non-interactive PATH, and
~/positron/fetchcontent, artifacts and work/sdk-v2 do not exist yet."""
tbl.append('<blockquote><pre>' + msg + '</pre></blockquote>\n')
new_block = "\n".join(tbl)
s = s[:start] + new_block + s[end:]

# R7, R8: P0 bullets
rep("<li>Answer A1 and A2 for the record (who holds <code>arm</code> and <code>jhan</code>, who operates alpha, whether the staging was Jibin's side's work).</li>",
    "<li>Answer A1 and A2 for the record. A1 was answered on 22 October (<code>jhan</code> is Jibin's, <code>arm</code> is shared). A2 (who operates alpha and did the staging) is still open.</li>")
rep("<li>Agree the reboot slot (A7) with every root holder.</li>",
    "<li>Reboot slot (A7): Jibin approved rebooting as soon as the host is idle, which it was at 04:41 UTC on 22 October. P2 can run tonight, after P1b and P1d.</li>")
# R9: P2 heading
rep("<h3>P2. Thursday 22 October 15:00 UTC (08:00 PDT, 11:00 EDT): reboot into isolcpus, about 15 minutes of downtime</h3>",
    "<h3>P2. Reboot into isolcpus, about 15 minutes of downtime (approved by Jibin on 22 October for any idle moment, so tonight; first proposed for Thursday 15:00 UTC)</h3>")
# R10: footer
rep("Prepared for Jibin on 21 October 2026, revised 22 October 02:40 UTC.",
    "Prepared for Jibin on 21 October 2026, revised 22 October 02:40 UTC and 04:50 UTC.")

open(p, "w", encoding="utf-8").write(s)
print("ok: bytes", n_before, "->", len(s))
# stale-spot report
for pat in ["Thu 22 Oct 10:00 EDT", "14:00 UTC", "Thursday", "Thu 22 Oct 15:00", "15:00 UTC"]:
    print(f"{pat!r}: {len(re.findall(re.escape(pat), s))} occurrences")
