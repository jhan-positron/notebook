#!/usr/bin/env python3
"""Build the summary document for Jeremy (standalone light-theme HTML) from the same sources as the plan page."""
import html, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/rampup/phoenix-crb-for-jeremy-2026-10-22.html"
FIGS = json.load(open(os.path.join(HERE, "..", "figs", "figs.json"), encoding="utf-8"))
CSS = re.search(r'CSS = """(.*?)"""', open(os.path.join(HERE, "build_plan.py"), encoding="utf-8").read(), re.S).group(1)
REPLY = open(os.path.join(HERE, "reply-to-jeremy-2026-10-22.txt"), encoding="utf-8").read().rstrip("\n")
NOTE = re.sub(r" I <<Jibin:[^>]*>>\.", "", open(os.path.join(HERE, "note-to-arm-users-2026-10-22.txt"), encoding="utf-8").read().rstrip("\n"))
def code(s): return '<pre class="code"><code>' + html.escape(s) + "</code></pre>"
def fig(key, caption): return f"<figure>{FIGS[key]}<figcaption>{caption}</figcaption></figure>"
P = []
A = P.append
A("""<header class="top"><h1>phoenix-crb for the SDK latency runs: host record, rules and answers</h1>
<p class="sub">From Jibin (jhan@positron.ai) for Jeremy, 22 October 2026. Host: phoenix-crb, 192.168.2.45, Linux hostname <code>ubuntu</code>. Times are UTC with PDT and EDT equivalents. Jibin is away from 22 October to about 29 October. Everything here was checked read-only from the <code>positron-perf</code> account on 22 October at 05:44 UTC (after the reboot) and again at 17:56 UTC.</p>
<nav class="toc"><a href="#short">Short version</a><a href="#words">Words used here</a><a href="#a">1 Answers</a><a href="#h">2 The host as it is</a><a href="#r">3 Rules for counted runs</a><a href="#l">4 The 21 Oct run</a><a href="#w">5 While Jibin is away</a><a href="#o">6 Open items</a><a href="#c">7 Checks</a></nav></header>
<section id="short" class="short"><p><strong>Short version.</strong> The host is ready and nothing on it changes while Jibin is away: cores 126–127 are isolated, device interrupts stay off cores 120–127, all 128 cores run the performance governor, the housekeeping timers are paused until 6 November, and all of it is on the boot line.</p>
<p>Your Friday block (23 October 13:00–16:00 UTC) is acknowledged, the other users of the host are told, and counted blocks may continue next week under the same rule.</p>
<p>Section 1 answers your five questions, section 4 has the arithmetic on the 21 October run (the host clock alone cannot make a run count, your faster logits-row write can), and section 6 lists what is still open and who owns it.</p></section>""")
terms = [
    ("positron-perf", "Your account on the host (user id 1001, keys only, no sudo)."),
    ("arm (account)", "The shared administrator account used by the other engineers of the phoenix-crb project. Jibin's own administrator account is <code>jhan</code>."),
    ("block", "Your word for one reserved stretch of counted runs, announced at least 2 h ahead, with the RUNNING file present throughout."),
    ("RUNNING file", "<code>/tmp/positron-perf.RUNNING</code>, created by your run script at the start of a block and removed at its end. For everyone else: while it exists, stay off the host."),
    ("isolcpus", "The kernel boot argument that takes CPUs 126–127 out of scheduler load balancing. A thread reaches them only through an explicit affinity call (taskset or sched_setaffinity)."),
    ("nohz_full, rcu_nocbs", "Kernel features that stop the periodic tick and move RCU callbacks off a CPU. The running kernel was built without them. Deferred: you said only the tools/perf host-timing gate needs them, not the 5 November demo."),
    ("CPPC pair", "Two reads of a CPU's <code>acpi_cppc/feedback_ctrs</code> file (reference and delivered counters), one before and one after a run. Delivered MHz = 50 × Δdelivered / Δreference × 20. Each read sends two interrupts to that CPU, so never read it during a run."),
    ("logits row", "One pass's output scores, which the fake device thread writes for some passes. In the 21 October run these passes were the late ones."),
    ("latency judge, churn label", "Your SDK tools that run the per-user latency gate and judge the record. They need only a pinned pass thread, and they run on the current kernel."),
]
A('<section id="words"><h2>Words used here</h2><table><tr><th style="width:22%">Term</th><th>Meaning</th></tr>' + "".join(f"<tr><td><strong>{t}</strong></td><td>{d}</td></tr>" for t, d in terms) + "</table></section>")
A("""<section id="a"><h2>1. Answers to your questions of 22 October</h2>
<table><tr><th style="width:36%">You asked</th><th>Answer</th></tr>
<tr><td>Your first counted block, Fri 23 Oct 13:00–16:00 UTC, CPUs 0–125, up to 32 GiB of temporary files, then one churn run.</td><td>Acknowledged. The host is yours for the whole block (06:00–09:00 PDT, 09:00–12:00 EDT). The other users are told. The files fit: 1.7 TB free on the root file system, which also holds your home. Nothing is needed from Jibin on the host.</td></tr>
<tr><td>May you keep running counted blocks next week, and who is the contact if the host needs attention?</td><td>Yes, same rule: weekdays 13:00–21:00 UTC, notice at least 2 h ahead, the RUNNING file. Contact: the phoenix-crb channel, the chat channel of the host's users. Jibin posts the login details and the BMC access there, so the users can handle a boot problem too. The other engineers have root through the <code>arm</code> account.</td></tr>
<tr><td>Were the three interactive positron-perf logins from 192.168.2.136 (21 Oct 05:15 and 23:37, 22 Oct 00:51 UTC) Jibin's?</td><td>Yes. 192.168.2.136 is Jibin's workstation. They were Jibin's own test logins and Jibin's agent's read-only checks, 3 to 5 s each. Nothing in your account was changed.</td></tr>
<tr><td>Builds and untimed tests on cores 0–95 outside the window: OK?</td><td>Yes, at any time, as long as no RUNNING file exists. You share those cores with the other engineers' work, so build times may vary.</td></tr>
<tr><td>Keep CPU 126 in the inner taskset set (120–127) once the device thread pins itself?</td><td>Yes, as long as the outer <code>taskset -c 120-125</code> stays. A taskset call whose new set does not contain the CPU it runs on is moved by the kernel to any CPU of the new set, isolated ones included. With the outer call first, the inner call already runs inside its set and nothing moves. Threads created later never land on 126 or 127 by themselves, because isolated cores get no load balancing, so only your two pinned threads reach them.</td></tr>
<tr><td>Outbound access (your item 6).</td><td>It stays. Pinned package installs between runs are fine.</td></tr>
</table></section>""")
A("""<section id="h"><h2>2. The host as it is since 22 October 05:43 UTC</h2>
<table><tr><th style="width:28%">Item</th><th>Value</th><th style="width:30%">Meaning for your runs</th></tr>
<tr><td>Kernel</td><td><code>7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858</code> (Arm's vendor kernel, HZ = 250, built without NO_HZ_FULL)</td><td>A busy isolated core keeps one timer interrupt every 4 ms, 1 to 2 µs each (est.), about 0.05% of the core, as you judged.</td></tr>
<tr><td>Boot line additions</td><td><code>isolcpus=domain,managed_irq,126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1</code></td><td>Persistent across reboots. No second reboot is planned.</td></tr>
<tr><td>Isolated cores</td><td><code>/sys/devices/system/cpu/isolated</code> = 126-127</td><td>127 for the pass thread, 126 for the device thread, your other threads on 120–125 (your Q3).</td></tr>
<tr><td>Device interrupts</td><td>Default interrupt mask CPUs 0–119. Each core 120–127 keeps one NVMe completion queue per disk, which fires only for disk I/O issued from that core.</td><td>Keep file writes off 126 and 127, or accept their completion interrupts there.</td></tr>
<tr><td>Clock</td><td>Performance governor on all 128 cores, request 2,800 MHz. No boost range exists (highest = nominal). Measured: 2,796 MHz est. on a busy core.</td><td>Your clock rule (≥ 2,772 MHz from one CPPC pair before and after, on 126 and 127) is the acceptance test.</td></tr>
<tr><td>Cross-CPU interrupts</td><td><code>rcu_normal=1</code>: service starts no longer send function-call interrupts to busy cores. Measured after the reboot: zero interrupts on 126 and 127 in a quiet minute, and two broadcast interrupts per ssh login on every core.</td><td>A login during a run costs the pass core two interrupts. That is why the rule keeps everyone else off the host.</td></tr>
<tr><td>Services and login shells</td><td>systemd <code>CPUAffinity=0-119</code>: every service and login shell starts with CPU affinity 0–119.</td><td>Your taskset calls still place threads on 120–127 (an explicit affinity call may name CPUs outside the inherited mask).</td></tr>
<tr><td>Housekeeping</td><td>11 timers disabled until 6 November (apt, fwupd, fstrim, man-db, motd, logrotate, update-notifier, dpkg-db-backup, e2scrub, tmpfiles-clean), netperf stopped. sysstat still samples every 10 min on a housekeeping core.</td><td>No package installs and no disk trims during the run period.</td></tr>
<tr><td>Disk</td><td>Root file system ext4, 1.7 TB free, mounted with online discard. Your home is on it (7.9 GB used on 22 October).</td><td>Your 32 GiB of temporary files fit; deleting them costs nothing later.</td></tr>
<tr><td>Verified</td><td>22 October 05:44 UTC after the reboot, and again 17:56 UTC: boot line, isolated list, 128 × performance, rcu_normal, timers, no RUNNING file, zero interrupts on 126–127 in 10 s, your build log ending in <code>BUILD-DONE rc=0</code>.</td><td>Nothing changes while Jibin is away.</td></tr>
</table>""")
A(fig("fig_cpu_alloc", "Figure 1. The split of the 128 cores as built on 22 October: 0–119 housekeeping, 120–125 your harness's other threads, 126 and 127 isolated for the device thread and the pass thread."))
A("""</section>
<section id="r"><h2>3. The rules for counted runs, as agreed on 22 October</h2>
<ul>
<li><strong>Windows:</strong> Mon–Fri 13:00–21:00 UTC. That is 06:00–14:00 PDT and 09:00–17:00 EDT until 31 October, and 05:00–13:00 PST and 08:00–16:00 EST from 2 November (US clocks change on Sunday 1 November). Your script refuses a run that would end after 21:00 UTC.</li>
<li><strong>Notice:</strong> at least 2 h ahead, in the phoenix-crb channel, where the other users of the host see it.</li>
<li><strong>RUNNING file:</strong> <code>/tmp/positron-perf.RUNNING</code> for the whole block. While it exists, nobody else logs in or runs anything. Outside blocks the host is shared as usual: builds and untimed tests on cores 0–95 at any time.</li>
<li><strong>Launch line:</strong> start the label with the outer <code>taskset -c 120-125</code> so that the shell and Python land on a balanced core, then widen the set. Once the device thread pins itself, the inner set may be 120–127.</li>
</ul>""")
A(code("""taskset -c 120-125 taskset -c 120-125,127 prlimit ... bash tools/ci/run_scheduled_gate.sh churn ...   # until the device-thread pin lands
taskset -c 120-125 taskset -c 120-127     prlimit ... bash tools/ci/run_scheduled_gate.sh churn ...   # after it: 127 pass thread, 126 device thread"""))
A("""<ul>
<li><strong>Clock rule:</strong> one CPPC pair on 126 and on 127, read before and after the block, never during it. Pass: delivered ≥ 2,772 MHz (99% of 2,800). A miss voids the run.</li>
<li><strong>Do not run during a block:</strong> <code>snap</code>, <code>unshare</code>, <code>podman</code>, <code>systemd-run</code> or any service restart (they send interrupts to busy cores). Do not read <code>feedback_ctrs</code> or <code>cpuinfo_cur_freq</code> of 126 or 127 during a run (two to four interrupts per read). Your <code>phx-isol.py</code> already avoids this.</li>
</ul>""")
A(code("""# as positron-perf, once before and once after a block, for CPU 126 and 127
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R0> del:<D0>
# ... the block ...
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R1> del:<D1>
# delivered MHz = 50 * (D1 - D0) / (R1 - R0) * 20      pass: >= 2772"""))
A("""</section>
<section id="l"><h2>4. The 21 October run, with your numbers</h2>
<p>Your breakdown settles the cause of the void. The arithmetic below uses your counts and the record's mean. One number is new: the budget per late pass.</p>""")
A(fig("fig_lateness_budget", "Figure 2. Left: 2,132 of the 37,275 passes wrote a logits row and were late, the other 35,143 were on time. Right: the measured 105 to 111 µs per late pass at 1.6 GHz, the estimate for the performance governor alone, and the estimate with the 12× faster write. The dashed red line is the budget: 43.7 µs per late pass keeps the mean at 2.5 µs. The estimates assume the window is 26.6 µs on Phoenix too."))
A("""<table><tr><th style="width:46%">Quantity</th><th class="num">Value</th><th>How it is known</th></tr>
<tr><td>Mean lateness of one logits-row pass, 6.25 µs × 37,275 / 2,132</td><td class="num">109.3 µs</td><td>Computed; you measured 105 to 111 µs.</td></tr>
<tr><td>Budget per late pass for a 2.5 µs mean, 2.5 µs × 37,275 / 2,132</td><td class="num">43.7 µs</td><td>Computed, if every other pass stays on time.</td></tr>
<tr><td>Lateness per late pass at 2.8 GHz with the current write</td><td class="num">51 to 109 µs est.</td><td>51 µs if the write (26.6 + 109.3 µs) scales with the clock, 109 µs if it does not. Mean 2.9 to 6.25 µs: void either way. So the governor alone cannot make a run count.</td></tr>
<tr><td>Write time with the 12× faster code on Phoenix</td><td class="num">6 to 11 µs est.</td><td>Inside the 26.6 µs window, so these passes stop being late. You measured about 5 µs on LSF hosts. The first run with that code on Phoenix measures it.</td></tr>
</table>
<p>Also measured here on 22 October: your hiccup probe in sleep mode on an idle core at 1.6 GHz is late by 0.02 µs on average (0 of 2,000 cycles over 2.5 µs), so the wait pattern itself is fine on this host. The pin to 126 with 1 µs slack removes the remaining tail: the sleep's wake-up overshoot of about 53 µs (50 µs default slack plus 3 µs wake-up latency) and any sharing of the core.</p>
</section>""")
A("""<section id="w"><h2>5. While Jibin is away, 22 to about 29 October</h2>
<ul>
<li><strong>Nothing changes on the host.</strong> The settings are on the boot line and in enabled units. The timers stay paused. Nobody installs packages or edits boot settings.</li>
<li><strong>Your blocks continue</strong> under the rule in section 3. Announce each block at least 2 h ahead.</li>
<li><strong>The other users</strong> of the host were given the note below. They check for the RUNNING file before any work and stay off the host while it exists.</li>
<li><strong>If the host needs attention:</strong> the phoenix-crb channel. The <code>arm</code> users have root, and the BMC access is posted there, so a host that does not come back from a reboot can be handled from the channel as well.</li>
<li><strong>If a reboot ever happens:</strong> the settings persist, but the run in progress is lost, and the RUNNING file stays behind. Remove it only after checking that its pid is gone (your rule).</li>
</ul>
<p>The note sent to the other users of the host:</p>
<blockquote><pre>""" + html.escape(NOTE) + """</pre></blockquote>
</section>
<section id="o"><h2>6. Open items and owners</h2>
<table><tr><th style="width:44%">Item</th><th style="width:16%">Owner</th><th>Status</th></tr>
<tr><td>Device thread pinned to 126 with 1 µs timer slack, on Phoenix</td><td>Jeremy</td><td>In progress, aim before Monday 26 October. Until then the double taskset line, 126 idle.</td></tr>
<tr><td>The 12× faster logits-row write on Phoenix</td><td>Jeremy</td><td>Not on Phoenix yet (your reply). Until it is, a churn run with a device thread is expected to stay void (section 4).</td></tr>
<tr><td>First counted block</td><td>Jeremy</td><td>Fri 23 October 13:00–16:00 UTC. Acknowledged.</td></tr>
<tr><td>Further blocks: one next week, one or two before 5 November</td><td>Jeremy</td><td>Same rule. Announce 2 h ahead.</td></tr>
<tr><td>Contact while Jibin is away</td><td>the phoenix-crb channel</td><td>Login details and BMC access posted there by Jibin.</td></tr>
<tr><td>nohz_full and rcu_nocbs (kernel rebuild with CONFIG_NO_HZ_FULL)</td><td>Jibin, after Arm grants access to the kernel source</td><td>Deferred: only the tools/perf host-timing gate needs them, not 5 November. Tell Jibin before you need them.</td></tr>
<tr><td>Restore the housekeeping timers</td><td>Jibin</td><td>After Friday 6 November, outside any run window.</td></tr>
<tr><td>Sampling tests and the timed compile on Phoenix</td><td>Jeremy</td><td>Later, on cores 0–95, no isolation needed (your reply). Not needed for Monday.</td></tr>
</table></section>
<section id="c"><h2>7. Checks you can run from your account (no root, no interrupts to 126–127)</h2>""")
A(code("""cat /proc/cmdline | tr ' ' '\\n' | grep -E 'isolcpus|irqaffinity|cpufreq|rcu_normal'   # the four arguments
cat /sys/devices/system/cpu/isolated                                                    # 126-127
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c           # 128 performance
cat /sys/kernel/rcu_normal                                                              # 1
systemctl list-timers --no-pager | grep -E 'apt|fwupd|fstrim|man-db|motd|update-notifier|tmpfiles' || echo "no risky timers"
who; cat /proc/loadavg; ls /tmp/positron-perf.RUNNING 2>/dev/null                       # only you; load near 0; no file before you start
# scaling_cur_freq of 120-127 is the governor's request and costs no interrupt; feedback_ctrs and cpuinfo_cur_freq do"""))
A("""</section>
<footer>Written by Jibin's agent from read-only checks of 21 and 22 October 2026 and from Jeremy's two replies of 22 October. The host's changes were made by Jibin on 22 October between 05:25 and 05:43 UTC. Figures use the same validated light palette as Jibin's plan page. Estimates are marked est. and listed with their assumptions.</footer>""")
doc = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>phoenix-crb for Jeremy: host record and rules</title><style>" + CSS + "</style></head><body><main>" + "\n".join(P) + "</main></body></html>\n"
open(OUT, "w", encoding="utf-8").write(doc)
print("wrote", OUT, len(doc), "bytes")
