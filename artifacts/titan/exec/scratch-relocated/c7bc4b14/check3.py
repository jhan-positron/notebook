import html
raw = html.unescape(open('/home/jhan/workspace/titan/rampup/jeremy-tasks-plan.html', encoding='utf-8').read())
qs = [
 "Written for Jibin on 21 October 2026 and revised three times on 22 October (UTC): at 02:40 after a verification pass by 20 independent agents, at 05:05 with Jibin's answers to the administrator questions (section 4), and at 06:00 as the as-built record after Jibin made the host changes from the",
 "The host side is done: on 22 October Jibin set the performance governor, paused the housekeeping timers and rebooted at 05:43 UTC with cores 126–127 isolated (verified at 05:44 UTC), but",
 "Monday's counted runs therefore also need Jeremy to pin that thread, and six questions for him carry defaults, so the message in section 4 is the next step (it waits on question A11).",
 "and the cpupower unit are root-owned, every file of the package is root:root, and no file outside",
 ", and persistent through the boot argument",
 "Entry 0010 and the second disk stay unknown, and neither blocks the reboot:",
 "Useful but not blocking (asked at the end of the message):",
 "Reboot: done once (first proposed for Thursday 15:00 UTC, moved forward when Jibin approved any idle moment).",
 "The fourth column records the answer and whether the question is still open.",
 "are the proposed re-runs after the governor change and after the reboot.",
 "(2) Went in at 05:34 UTC as a drop-in,",
 "Item 1 of the message asks Jeremy to confirm in passing.",
 "Remove the expedited-RCU IPIs now",
 "Do this before any root use of perf, cpupower or bpftool, and never enable",
 "Ask Arm's SVK contact (A6) for the kernel tree at commit",
 "P1e. Governor-only re-run of Jeremy's job, before the reboot",
 "Persistence comes from the boot argument",
 "the arm session on tty1 is an idle shell under",
 "Only Jibin was logged in (the console session on tty1 ended with the reboot).",
 "Done 22 Oct 05:36 UTC by a sysfs write from",
 "your logins from the laptop and from sw-dev-01",
 "and both logins worked.",
 "Compare with churn-r1 and govtest-1: the judge verdict",
 "compared with churn-r1 and govtest-1",
 "Hand-off note to Jeremy, with these items:",
 "The proposed split of the 128 CPUs and what reaches each reserved CPU today.",
 "Rollback",
 "Governor: echo",
]
for q in qs:
    print(raw.count(q), "::", q[:90])
