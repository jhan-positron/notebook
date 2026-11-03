sents = {
 "header": "Written for Jibin on 21 October 2026 and revised three times on 22 October (UTC): at 02:40 after a verification pass by 20 independent agents, at 05:05 with Jibin's answers to the administrator questions (section 4), and at 06:00 as the as-built record after Jibin made the host changes from the jhan account between 05:26 and 05:43 UTC, each verified read-only from positron-perf.",
 "short2": "The host side is done: on 22 October Jibin set the performance governor, paused the housekeeping timers and rebooted at 05:43 UTC with cores 126–127 isolated (verified at 05:44 UTC), but nohz_full still needs a rebuilt kernel from Arm.",
 "short3": "Monday's counted runs therefore also need Jeremy to pin that thread, and six questions for him carry defaults, so the message in section 4 is the next step (it waits on question A11).",
 "A3": "Entry 0010 and the second disk stay unknown, and neither blocks the reboot: the planned boot arguments cannot fail the boot, the GRUB saved entry still names the vendor kernel, and the host booted the vendor kernel at each of its last three boots (3, 5 and 20 October) as recorded by last.",
 "A5": "Done by Jibin at about 05:25 UTC on 22 October and verified from positron-perf at 05:26 UTC: /usr/bin/perf, /usr/bin/cpupower, /usr/sbin/bpftool and the cpupower unit are root-owned, every file of the package is root:root, and no file outside /home belongs to positron-perf (count 347 → 0).",
 "A7state": "State at 04:41 UTC on 22 October: no positron-perf process, load 0.00, and the arm session on tty1 is an idle shell under /bin/login with 0.05 s of CPU time in 33 hours, that is a console left logged in, not a job.",
 "A7order": "Jibin runs the reboot (I cannot, see A5), in this order: P1b (before 06:28 UTC, when apt-daily-upgrade fires), P1d, the A8 drop-in, the P2 drop-in and update-grub, the reboot, then the P2 checks.",
 "whatran": "What Jibin ran on 22 October (UTC), each verified read-only from positron-perf (commands in section 6): P1d ownership fix (verified 05:26), P1b timers and netperf (05:30–05:33), P1c rcu_normal and the A8 CPUAffinity drop-in (05:34), P1a governor loop (05:36), the P2 drop-in, update-grub and the reboot (05:43, back by 05:44, checks 05:44–05:48).",
 "sec4intro": "The reboot happened on 22 October at 05:43 UTC with the D3 default (126–127 isolated), and a different core set needs another reboot, which Jibin can run at any idle moment.",
 "P1a": "Persistence comes from the boot argument cpufreq.default_governor=performance in P2, which proved sufficient (128 × performance after the reboot), so the boot-time unit below was not installed and stays as a fallback.",
 "P1head": "The command blocks below are the record of what was run, and each result was verified read-only from positron-perf.",
 "gov row": "Done 22 Oct 05:36 UTC by a sysfs write from jhan, and persistent through the boot argument cpufreq.default_governor=performance: 128 × performance after the 05:43 UTC reboot, request 2,800 MHz on every CPU (verified).",
 "54logins": "Five ssh logins in a 25 s window then produced 10 function-call IPIs on each of the two CPUs, that is two broadcast IPIs per login even with rcu_normal=1, plus 6 and 1 timer ticks.",
 "55intro": "On 22 October at 05:30–05:33 UTC Jibin applied the Action column: every unit listed for disabling or masking is now inactive, netperf is stopped and disabled, and the sysstat timers were kept (verified).",
 "A8_2": "(2) Went in at 05:34 UTC as a drop-in, /etc/systemd/system.conf.d/60-positron-cpuaffinity.conf with [Manager] and CPUAffinity=0-119, which the reboot applies to every service and login shell.",
 "sec8": "As-built verification, 22 October 05:26–05:52 UTC: read-only checks from positron-perf after each of Jibin's changes and after the reboot, saved as verification-2026-10-22/postreboot-0545.txt and ipi-attribution-0552.txt.",
 "P2meta": "Reboot: done once (first proposed for Thursday 15:00 UTC, moved forward when Jibin approved any idle moment).",
 "A2": "Jibin's best guess is that the alpha sessions were Jeremy driving agents, after Jibin set up the login and messaged him at 10:03 PDT (17:03 UTC) on 21 October.",
 "A2b": "Consequences: alpha is a shared machine (Jibin logs in from it too), the staging and churn-r1 are Jeremy's side's work, D6 stays no, and Q6 stays in the message.",
}
for k,v in sents.items():
    print(f"{len(v.split()):3d} words :: {k}")
