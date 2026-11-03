#!/usr/bin/env python3
"""Build jeremy-tasks-plan.html (single-theme light, self-contained) from the evidence and the inline SVG figures."""
import html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = json.load(open(os.path.join(HERE, "..", "figs", "figs.json"), encoding="utf-8"))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/rampup/jeremy-tasks-plan.html"
REQ = open(os.path.join(HERE, "requests.txt"), encoding="utf-8").read()
REPLY = open(os.path.join(HERE, "reply-to-jeremy-2026-10-22.txt"), encoding="utf-8").read().rstrip("\n")
NOTE = open(os.path.join(HERE, "note-to-arm-users-2026-10-22.txt"), encoding="utf-8").read().rstrip("\n")
ACCESS = open(os.path.join(HERE, "t3-access-details-2026-10-22.txt"), encoding="utf-8").read().rstrip("\n")

def q(name):
    """Verbatim quote of one message from requests.txt."""
    marker = {"original": "=== MESSAGE 1", "deadline": "=== MESSAGE 2", "latest": "=== MESSAGE 3", "reply": "=== MESSAGE 4", "second": "=== MESSAGE 5"}[name]
    i = REQ.index(marker); i = REQ.index("\n", i) + 1
    j = REQ.find("\n=== MESSAGE", i)
    return REQ[i: j if j > 0 else len(REQ)].strip("\n")

def code(s):
    return "<pre class=\"code\"><code>" + html.escape(s) + "</code></pre>"

def fig(key, caption):
    return f'<figure>{FIGS[key]}<figcaption>{caption}</figcaption></figure>'

CSS = """
:root{--ink:#0b0b0b;--sec:#52514e;--muted:#898781;--grid:#e1e0d9;--base:#c3c2b7;--surf:#fcfcfb;--page:#f9f9f7;
--blue:#2a78d6;--blue100:#cde2fb;--orange:#eb6834;--orangew:#fbdccd;--good:#0ca30c;--goodtext:#006300;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b}
*{box-sizing:border-box}html{color-scheme:light}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 16px 64px}
header.top{border-bottom:1px solid var(--grid);padding-bottom:14px;margin-bottom:18px}
h1{font-size:26px;line-height:1.25;margin:0 0 6px}h2{font-size:20px;margin:40px 0 10px;padding-top:8px;border-top:1px solid var(--grid)}
h3{font-size:16px;margin:22px 0 8px}p{margin:8px 0}.sub{color:var(--sec);font-size:13.5px;margin:0}
.short{background:#eaf2fc;border-left:4px solid var(--blue);padding:12px 16px;border-radius:4px;margin:16px 0}
.short p{margin:4px 0}.callout{background:var(--surf);border:1px solid var(--grid);border-left:4px solid var(--orange);padding:10px 14px;border-radius:4px;margin:12px 0}
.danger{background:#fdf0f0;border:1px solid #f0b8b8;border-left:4px solid var(--crit);padding:10px 14px;border-radius:4px;margin:12px 0}
.note{background:var(--surf);border:1px solid var(--grid);padding:10px 14px;border-radius:4px;margin:12px 0;color:var(--sec);font-size:13.5px}
nav.toc{font-size:13.5px;color:var(--sec);margin:10px 0 0}nav.toc a{margin-right:12px;white-space:nowrap}
a{color:#1c5cab}table{border-collapse:collapse;width:100%;margin:10px 0 16px;font-size:13.5px;background:var(--surf)}
th,td{border:1px solid var(--grid);padding:6px 8px;vertical-align:top;text-align:left}th{background:#f3f3f0;font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}tr.sep td{border-top:2px solid var(--base)}
blockquote{margin:10px 0;padding:0}blockquote pre{white-space:pre-wrap;background:var(--surf);border:1px solid var(--grid);border-left:4px solid var(--base);padding:12px 14px;border-radius:4px;font:13.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin:0}
pre.code{background:#f3f3f0;border:1px solid var(--grid);padding:10px 12px;border-radius:4px;overflow:auto;font:12.5px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin:8px 0 12px}
code{font:0.95em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}p code,li code,td code{background:#f3f3f0;padding:0 4px;border-radius:3px}
figure{margin:16px 0 22px;background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:10px 12px 6px}figure svg{max-width:100%;height:auto;display:block}
figcaption{color:var(--sec);font-size:13px;margin:6px 2px 4px}
.chip{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.chip.done{background:#e6f6e6;color:var(--goodtext);border-color:#b7e2b7}.chip.live{background:#eaf2fc;color:#1c5cab;border-color:#b7d3f6}
.chip.reboot{background:#fdf3ee;color:#9a3d12;border-color:#f5c4ad}.chip.kernel{background:#fdf0f0;color:#9c1f1f;border-color:#f0b8b8}.chip.open{background:#fbdccd;color:#7a3410}
.chip.jeremy{background:#fff6dc;color:#6b4e00;border-color:#f4dc8c}.chip.gray{background:#f3f3f0;color:var(--sec);border-color:var(--grid)}
ul,ol{padding-left:22px;margin:6px 0}li{margin:3px 0}
.phase{background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:12px 16px;margin:14px 0}
.phase h3{margin:0 0 4px}.phase .meta{color:var(--sec);font-size:13px;margin-bottom:8px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}
.stat{flex:1 1 230px;background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:10px 16px;min-width:200px}
.stat .v{font-size:26px;font-weight:600;line-height:1.1}.stat .l{color:var(--sec);font-size:12.5px}
footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--grid);margin-top:40px;padding-top:12px}
.contents{background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:10px 18px 8px;margin:14px 0 4px;font-size:13.5px}
.contents h2{border:0;margin:0 0 6px;padding:0;font-size:15px}.contents ol{margin:0;padding-left:22px}.contents ol ol{padding-left:20px;margin:2px 0 4px;color:var(--sec)}
.contents li{margin:2px 0}.contents a{text-decoration:none}.contents a:hover{text-decoration:underline}
@media print{body{background:#fff}main{max-width:none}}
"""

def chip(kind, label):
    return f'<span class="chip {kind}">{html.escape(label)}</span>'

DONE = chip("done", "✔ done"); LIVE = chip("live", "● root, no reboot"); REBOOT = chip("reboot", "↻ root + reboot")
KERNEL = chip("kernel", "✖ needs another kernel"); UNK = chip("gray", "? unknown")
NA = chip("gray", "– not needed"); PART = chip("gray", "◑ partly"); NOTDONE = chip("gray", "○ not done")
CLOSED = chip("done", "✔ closed"); OPENQ = chip("open", "○ open"); PARTQ = chip("open", "◑ partly open"); TODOQ = chip("open", "● to do (Jibin)")
JSIDE = chip("jeremy", "● Jeremy's side"); NOTICE = chip("gray", "ℹ notice")

# ----------------------------------------------------------------------------------------------- today's actions (shown twice: top of page and P5)
TODAY = ("""<table><tr><th style="width:4%">#</th><th>Action</th><th style="width:9%">Owner</th><th style="width:10%">On the host?</th><th style="width:17%">Status</th></tr>
<tr><td>T1</td><td>Send Jeremy the reply (section 4, Jibin's version) with two corrections: say that <code>arm</code> has sudo and positron-perf does not, and do not share the positron-perf login (proofread version of 22 October).</td><td>Jibin</td><td>no</td><td>""" + DONE + """ sent 22 Oct</td></tr>
<tr><td>T2</td><td>Post the note (section 4) in the phoenix-crb channel: the Friday block, the weekday windows, the RUNNING-file rule, the isolated cores, what not to change, the away dates.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T3</td><td>Post the <code>arm</code> login details and the BMC access in the phoenix-crb channel (item 2 of the reply). Not the positron-perf login.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T4</td><td>Send Jeremy the summary doc <code>phoenix-crb-for-jeremy-2026-10-22.html</code> (host record, rules, answers, the 21 October arithmetic, open items, checks he can run).</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T5</td><td>Jeremy's block notices must reach the other users while Jibin is away. Jeremy is in the phoenix-crb channel (Jibin, 22 October), so his notices and the note reach the same people.</td><td>nobody</td><td>no</td><td>""" + CLOSED + """</td></tr>
<tr class="sep"><td>T6</td><td>On the host: nothing. No root step, no reboot, no file to create. The state was re-verified read-only at 17:56 UTC (boot line, isolated list, 128 × performance, rcu_normal, timers off, no RUNNING file, zero interrupts on 126–127 in 10 s). Friday's block needs nothing from Jibin.</td><td>nobody</td><td>no</td><td>""" + DONE + """ verified 17:56 UTC</td></tr>
<tr><td>T7</td><td>Kernel rebuild and Arm's GitHub access (A6): no action. Deferred to after the demo (P4).</td><td>Jibin, later</td><td>no</td><td>""" + NA + """</td></tr>
<tr><td>T8</td><td>Record: Jeremy's two replies, the reply, the note, the generator sources and the host check are saved in the evidence folder, and this page and the summary doc are rebuilt.</td><td>agent</td><td>no</td><td>""" + DONE + """</td></tr>
</table>""")

# ----------------------------------------------------------------------------------------------- content
parts = []
A = parts.append

A("""<header class="top">
<h1>Jeremy's requests for phoenix-crb: what they mean, where they stand, and the plan</h1>
<p class="sub">Written for Jibin on 21 October 2026. Revised four times on 22 October (UTC), the last at about 18:30 UTC after Jeremy's two replies and Jibin's change of plan (away from 22 October to about 29 October). The 02:40 revision followed a verification pass by 20 independent agents. The 05:05 revision added Jibin's answers to the administrator questions (section 4). The 06:00 revision is the as-built record: Jibin made the host changes from the <code>jhan</code> account between about 05:25 and 05:43 UTC, and each change was verified read-only from <code>positron-perf</code>. Host phoenix-crb (192.168.2.45, Linux hostname <code>ubuntu</code>) was checked read-only as <code>positron-perf</code> between 21 October 23:42 UTC and 22 October 02:00 UTC, and again on 22 October between 05:26 and 05:52 UTC after each of Jibin's changes. No setting, file or service on the host was changed by these checks. The changes of 22 October were made by Jibin. The three requests are quoted verbatim in section 1, Jeremy's two replies of 22 October in section 4.</p>
<!--TOC-->
</header>""")

A("""<section id="short" class="short">
<p><strong>Short version.</strong> The host work for Jeremy is complete and he accepted every default on 22 October: cores 126–127 isolated, the performance governor, the timers paused, no nohz_full before 5 November, the latency judge as the path, and the reservation and clock rules.</p>
<p>His data settles the 21 October void: 2,132 passes that write a logits row were each about 109 µs late, so the host clock alone cannot make a run count and his 12× faster write (not yet on Phoenix) is the fix (Figure 8).</p>
<p>His first counted block is Friday 23 October 13:00–16:00 UTC, Jibin is away from 22 to about 29 October, and today's actions are in the table right below: the reply to Jeremy went out, three messages remain for Jibin, none of them on the host.</p>
</section>
<section id="today"><h2>Today, Thursday 22 October: what to do before Jibin logs out</h2>
<p>Nothing on the host. The reply to Jeremy was sent on 22 October. Three items remain for Jibin, all messages, with their texts ready in section 4 and in the evidence folder. The same table is phase P5 in section 6.</p>
""" + TODAY + """
</section>
<div class="danger"><strong>Security finding, fixed by Jibin at about 05:25 UTC on 22 October (step P1d, verified 05:26 UTC).</strong> 347 files installed by the vendor package <code>linux-tools</code> were owned by the test account until 22 October <code>positron-perf</code>, among them <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code> and the <code>cpupower.service</code> unit file. The test account could replace a program that root later runs. This plan sets the governor through sysfs only and never runs <code>sudo cpupower</code> or <code>sudo perf</code>. Step P1d changed the ownership to root (verified 05:26 UTC: 0 files outside /home owned by positron-perf, down from 347).</div>
<div class="note">Changes on the host during this analysis: a second administrator account, <code>jhan</code> (user id 1002, group sudo), was created on 22 October at 01:19 UTC from Jibin's workstation, and it logged in from the workstation and from alpha. The isolation, governor, timer and boot settings were unchanged at 01:55 UTC. Jibin then changed all four between about 05:25 and 05:43 UTC (section 6). Jibin confirmed on 22 October that <code>jhan</code> is Jibin's own account and that <code>arm</code> is shared by every engineer on the phoenix-crb project (question A1).</div>""")

# ---- glossary
terms = [
    ("phoenix-crb", "The Arm server at 192.168.2.45. Its firmware names it “Phoenix Reference Server”, maker Arm Limited, build stage EVT0 (first engineering validation build), BIOS “AGI-CPU-CRB-v0.7.2”. CRB is read as “customer reference board” from that BIOS string."),
    ("Jibin", "The reader of this plan (jhan@positron.ai). Jibin's workstation is 192.168.2.136 (claude-agentsrv) and runs in Pacific time (PDT, UTC−7, until 1 November, then PST, UTC−8)."),
    ("Jeremy", "The SDK-side requester. His git commit on the host carries the time zone −0400 (US Eastern, EDT, until 1 November, then EST, UTC−5)."),
    ("SDK", "Software development kit: Positron's runtime, compiler and tests. The copy on the host is the repository <code>~/positron/src/phoenix-int</code>."),
    ("positron-perf", "The unprivileged test account (user id 1001) that Jeremy asked for. It has no usable sudo."),
    ("arm (account)", "The shared administrator account on phoenix-crb (user id 1000, group sudo), used by every engineer on the phoenix-crb project (A1, confirmed 22 October). The root steps of 22 October were all run from <code>jhan</code>."),
    ("jhan (account)", "A second administrator account (user id 1002, group sudo) created on phoenix-crb on 22 October 01:19 UTC from Jibin's workstation while this analysis ran. Confirmed as Jibin's own account on 22 October (A1)."),
    ("Dan", "Jibin's colleague who asked Arm on 22 October to grant Jibin access to Arm's GitHub, for the kernel source (A6)."),
    ("alpha", "The LAN host 192.168.1.200 (name alpha.positron.internal). It staged the SDK workspace on 21 October and held long <code>arm</code> sessions on 20 and 21 October. It logged in as <code>jhan</code> minutes after that account was created, so Jibin uses it too. Jibin's answer to A2 (22 October): the staging sessions were most likely Jeremy driving agents. The timing fits: Jibin's message to Jeremy went out at 17:03 UTC, and the first sessions from sw-dev-01 and from alpha started at 17:07 UTC."),
    ("sw-dev-01", "The SDK team's development host. Its LAN address is 192.168.2.39 (sw-dev-01.positron.internal) and its Tailscale address 100.124.2.53. It logged in to phoenix-crb as positron-perf four times on 21 October."),
    ("Asimov cards", "Positron's accelerator boards. None is attached to phoenix-crb, and Jeremy's tests do not need one."),
    ("LSF", "A batch job scheduler whose shared worker hosts Jeremy calls too noisy for timing. phoenix-crb runs no LSF."),
    ("pass thread", "The one runtime thread, named <code>positron-pass</code>, that plans and issues each forward pass (one model step). The SDK pins it to the CPU given as <code>pass_thread_core</code>."),
    ("fake device / null_timing", "The SDK's simulated device backend. One “fake device” thread sleeps until 100 µs before each pass's retirement time, then spins and posts the completion. Its lateness is measured against a band. The SDK does not pin this thread."),
    ("lateness band / void", "The allowed mean lateness of the fake device: 0.2% of the shortest pass period, 2.5 µs in the run seen here. A record whose mean lateness passes the band is “void”, and the latency judge reports INFRA (no measurement). The rule uses the mean, not the maximum."),
    ("latency judge / churn label", "The SDK tools (<code>tools/conformance/churn.py</code> and <code>latency_judge.py</code>) that run the per-user latency gate named <code>per-user-latency.qwen3_5_0_8b.P-TP1</code> and judge the record. They require only that the pass thread is pinned. They record whether the pass core is in isolcpus but do not require it."),
    ("perf lane", "A different SDK tool (<code>tools/perf/perf_lane.py</code>, <code>records.py</code>) for the TPS gate's host timing and the timed compile. It refuses any host that has no online core in both isolcpus and nohz_full. TPS means tokens per second."),
    ("D21, U1 p99, U5 waking, D17 lane", "SDK names used in its design documents. D21 is the set of per-user latency targets. U1 p99 is the 99th-percentile per-user latency target. U5 waking is the consumer-wake target. The D17 lane is the tool lane that measures them. The design says U1 p99 and U5 waking “count only from an isolated host”."),
    ("counted run", "A run whose numbers go into the 5 November demo, as opposed to a trial run."),
    ("isolcpus", "A kernel boot argument. With the <code>domain</code> flag the listed CPUs leave the scheduler's load balancing: a thread placed there stays there, and no other thread is moved there automatically. With <code>managed_irq</code> the kernel keeps kernel-managed device interrupts off them when the queue has other CPUs to use. It takes effect only at boot and cannot be undone without another reboot."),
    ("nohz_full", "A kernel feature (build option CONFIG_NO_HZ_FULL) that stops the periodic scheduler tick on a CPU running a single task. The running kernel was built without it."),
    ("rcu_nocbs", "A kernel boot argument that moves RCU callback work (deferred kernel clean-up, RCU = read-copy-update) off the listed CPUs. It needs the build option RCU_NOCB_CPU, which a NO_HZ_FULL kernel includes."),
    ("expedited RCU grace period", "A fast form of RCU synchronisation that sends a function-call IPI to every busy CPU on the host. A sandboxed service start or a namespace teardown triggers one. The kernel setting <code>rcu_normal=1</code> turns them into normal, slower grace periods without IPIs."),
    ("tick / HZ", "The periodic scheduler interrupt. The running kernel has HZ = 250, one tick every 4 ms on a busy CPU."),
    ("IRQ / managed IRQ", "A hardware interrupt request. A managed IRQ is one whose CPU assignment the kernel controls (here the NVMe disk queues, one queue per CPU). It cannot be moved by writing to /proc/irq."),
    ("IPI", "Inter-processor interrupt: one CPU asking another to do something (for example a function call or a reschedule). No isolation setting removes all of them."),
    ("cpufreq governor", "The kernel policy that picks a CPU's clock. <code>schedutil</code> (the governor until 22 October 05:36 UTC) follows CPU utilization. <code>performance</code> always requests the highest clock."),
    ("boost", "A clock above the nominal maximum. phoenix-crb's firmware exposes no boost range: the highest level equals the nominal 2.8 GHz, so there is nothing to disable."),
    ("CPPC / feedback_ctrs / AMU", "Collaborative Processor Performance Control, the firmware interface behind the <code>cppc_cpufreq</code> driver. Its feedback counters (read from the CPU's Activity Monitors Unit, AMU) are readable by any user and give the delivered clock: delivered performance = 50 × Δdelivered / Δreference, and one performance unit is 20 MHz on this host. Each read sends two IPIs to the CPU being read."),
    ("scaling_cur_freq", "The sysfs file that reports the governor's last clock request for a CPU, not the delivered clock. Reading it costs no IPI."),
    ("timer slack", "The kernel's allowed lateness for a sleeping thread's wake-up, 50 µs by default. A thread can lower its own slack with <code>prctl(PR_SET_TIMERSLACK)</code> without privilege. The SDK's waker thread does this (1 µs). The fake device thread does not."),
    ("vendor kernel", "The running kernel <code>7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858</code>. It was built on 16 September 2026 by an Arm engineer (the package maintainer address is at arm.com) with workarounds for this A0 silicon (A0 is the first silicon revision). It was installed from a local package on 28 September."),
    ("GIC, TLB, TLBI", "GIC is the Arm interrupt controller. TLB is the translation lookaside buffer, the CPU's cache of address translations, and TLBI the instruction that invalidates it."),
    ("SVK", "Arm's software validation kit: the installer that set up this board on 29 September and left its toolchain in <code>/opt/arm-svk</code>."),
    ("BMC, EFI", "BMC: the board's management controller, a small separate computer for remote console and power control (an ASPEED chip is present on the board, but no driver device exists). EFI: the firmware's boot interface, which keeps the boot entries."),
    ("SCHED_FIFO, POSIX CPU timers", "SCHED_FIFO is Linux's real-time scheduling policy. POSIX CPU timers are per-process timers that count CPU time. Both matter only for the nohz_full rules in P4."),
    ("PATH, PID, LTS, LVM, NTP, DNS, CI", "Common system terms: PATH is the shell's program search list, PID a process id, LTS Ubuntu's long-term-support release, LVM the logical volume manager (not used here), NTP network time synchronisation, DNS name lookup, CI continuous integration."),
    ("stock kernel", "Ubuntu's <code>6.8.0-147-generic</code>, installed automatically by unattended-upgrades on 15 October 2026 but never booted on this board as far as the host records show."),
    ("linux-tools (package)", "The vendor package that ships <code>perf</code>, <code>cpupower</code> and <code>bpftool</code> for the running kernel. Its files were owned by user id 1001, which on this host is positron-perf, until Jibin changed them to root at about 05:25 UTC on 22 October (step P1d)."),
    ("GRUB drop-in", "A file under <code>/etc/default/grub.d/</code> that adds boot settings. <code>update-grub</code> then regenerates the boot menu."),
    ("cpuset isolated partition", "A cgroup v2 setting (cgroup v2 is the kernel's resource-control tree) that removes CPUs from scheduler load balancing while the system runs. It needs root but no reboot. It does not stop the tick and does not show in <code>/sys/devices/system/cpu/isolated</code>."),
    ("unattended-upgrades / apt timers", "Ubuntu's automatic package updater and the systemd timers that drive it. The timers installed two kernels in October. Jibin disabled them at 05:30 UTC on 22 October (step P1b)."),
    ("hiccup, isol.py", "Scratch tools left in <code>~/positron/runs/</code>: a probe of the fake device's wait pattern (hiccup), and a snapshot/sampler of isolation, governors and per-CPU thread placement (isol.py). This check re-ran hiccup (section 5.3)."),
    ("churn-r1, govtest-1, govtest-2", "Run tags. churn-r1 is the run of 21 October. govtest-1 and govtest-2 were the proposed re-runs after the governor change (govtest-1, no longer possible because the reboot came first) and after the reboot (govtest-2, moot since 22 October: Jeremy's own counted blocks replace it)."),
    ("launcher", "The shell and Python processes that start Jeremy's job (<code>ev3-churn-job.sh</code>, <code>churn.py</code>, the judge). Where they first land decides where their threads stay once cores are isolated."),
    ("logits row", "One pass's output scores, one per vocabulary entry, which the fake device thread writes into the record for the passes that need it. Jeremy's reply of 22 October: 2,132 of churn-r1's 37,275 passes wrote one, and those were the late passes."),
    ("the twins", "Jeremy's term (22 October) for churn runs that have no fake device thread. Not defined further in his message."),
    ("block (of runs)", "Jeremy's word for one reserved stretch of counted runs, announced at least 2 h ahead, with the RUNNING file present throughout. The first one is Friday 23 October 13:00–16:00 UTC."),
    ("RUNNING file", "<code>/tmp/positron-perf.RUNNING</code>, written by Jeremy's run script at the start of a block (start, end, pid, tag, commit) and removed at the end. His script refuses to start if the file exists or if the run would end after 21:00 UTC. His build script stops a build when the file appears. For everyone else the rule is: while the file exists, stay off the host."),
    ("measure-job, smoke-setup, phxship, phx-isol.py", "Jeremy's scripts seen on the host on 22 October: the measurement job for a block (CPU, memory, disk and compile steps, then the churn run), its two smoke runs on CPUs 0–7, the build of commit <code>fa7f715f</code> on CPUs 0–95, and a sampler that reads no per-CPU file of CPUs 120–127 during a run."),
    ("fio", "A disk benchmark program. Jeremy's block runs it with direct I/O on up to 32 GiB of temporary files under his home."),
    ("host-timing gate", "The later SDK gate that uses tools/perf and is the only user of nohz_full (Jeremy, 22 October). Not part of the 5 November demo."),
]
A('<section id="words"><h2>Words used here</h2><table><tr><th style="width:22%">Term</th><th>Meaning in this document</th></tr>')
for t, d in terms:
    A(f"<tr><td><strong>{t}</strong></td><td>{d}</td></tr>")
A("</table></section>")

# ---- section 1: quotes
A(f"""<section id="s1"><h2>1. Jeremy's requests, quoted</h2>
<p>The three messages are reproduced verbatim from <code>jeremy-tasks.html</code>, section 1, in the order they were supplied there: the original request, the follow-up with the deadline, and the latest request dated 21 October 2026 (morning). Wording and punctuation are unchanged.</p>
<h3>Message 1: original request (undated, “no rush”)</h3>
<blockquote><pre>{html.escape(q('original'))}</pre></blockquote>
<h3>Message 2: follow-up with the Friday and Monday dates (undated)</h3>
<blockquote><pre>{html.escape(q('deadline'))}</pre></blockquote>
<h3>Message 3: latest request, 21 October 2026, morning</h3>
<blockquote><pre>{html.escape(q('latest'))}</pre></blockquote>
<div class="note">Order of messages 2 and 3: message 2 says “one update since this morning” and message 3 is dated “this morning” and says “whenever you have a moment”, so message 2 may be the later of the two. The plan uses the union of both and asks Jeremy which is newer (decision D1). The target group is CPUs 120–127. At least one isolated core and the account must be ready by Friday 23 October, and the rest may follow later.</div>
</section>""")

# ---- section 2: plain English
A("""<section id="s2"><h2>2. The requests in plain English</h2>
<h3>Message 1: what Jeremy's team wants to run, and what the host needs</h3>
<ul>
<li>Jeremy's Claude (an AI assistant writing for Jeremy) asks to run three kinds of SDK tests on phoenix-crb. The tests use only the host CPUs. No Asimov card is needed.</li>
<li>They run one job at a time. This is a promise about load, not a request for a host-side lock.</li>
<li>Test 1 is a timing test. The runtime drives a simulated device. The test measures the host software's added time per step, the gaps between output tokens, the time to the first token, and the time to wake a waiting reader thread.</li>
<li>Test 2 is the SDK's sampling unit tests (tests of the code that picks the next token), run natively on the Arm CPU.</li>
<li>Test 3 is a timed compile of a small model. The SDK's gate list names it <code>compile-0.8b</code>, the wall time of the Qwen3.5-0.8B compile.</li>
<li>Host need 1: at least one CPU, better two, isolated with isolcpus and nohz_full, ideally rcu_nocbs too, with device interrupts kept off it. The other CPUs stay with the operating system and the SDK's worker threads.</li>
<li>Host need 2: a fixed CPU clock, meaning the performance governor and no boost, if the board allows it.</li>
<li>Host need 3: nothing else running during a timed run. A reserved night-time window is acceptable.</li>
<li>Host need 4: clang 18, CMake 3.25 or newer, Ninja, and Python 3.11 or newer with development headers.</li>
<li>Host need 5: about 100 GB of disk. The account needs no sudo and no outbound network. They copy everything in.</li>
<li>Ask A: a local account named positron-perf with SSH key login, reachable from Jeremy's laptop directly or through sw-dev-01.</li>
<li>Ask B, the alternative: if an account is not wanted, Jibin runs a script that Jeremy sends.</li>
</ul>
<h3>Message 2: the dates</h3>
<ul>
<li>There is now a date. The per-user latency runs for the demo on Thursday 5 November need a quiet host. Jeremy says the shared LSF workers are too noisy for them.</li>
<li>Ask: the positron-perf account and one isolated core ready by Friday 23 October. Counted runs would then start on Monday 26 October.</li>
<li>The rest of message 1's list can follow later.</li>
<li>If a step is a problem, for example the reboot that isolcpus needs, Jeremy wants to be told, and both sides will work around it together.</li>
<li>Implicitly, the message asks for a status reply.</li>
</ul>
<h3>Message 3: the concrete host settings</h3>
<ul>
<li>For the SDK's latency runs, Jeremy asks for a few isolated cores for the runtime's pass thread. His example is isolcpus, nohz_full and rcu_nocbs on cores 120–127, which is eight cores.</li>
<li>He also asks for the performance cpufreq governor. The aim is a clock that stays fixed.</li>
<li>He believes both changes need root and a reboot.</li>
<li>He observed that the governor is schedutil today and that no cores are isolated. Both observations matched the host on 21 October. Since the 22 October 05:43 UTC reboot the governor is performance and CPUs 126–127 are isolated.</li>
</ul>
<h3>Where Jeremy's statements differ from the host</h3>
<ul>
<li><strong>“Both need root and a reboot.”</strong> The governor needs root but no reboot: it is a live kernel setting. isolcpus needs root and one reboot. nohz_full and rcu_nocbs need more than a reboot: the running kernel was built without them, so a rebuilt kernel is required.</li>
<li><strong>“No boost.”</strong> Already true, by firmware. The highest performance level equals the nominal 2.8 GHz, so there is no boost range to disable.</li>
<li><strong>“The clock stays fixed.”</strong> The performance governor requests the highest clock permanently. A busy core already reaches 2.8 GHz under schedutil, 14 ms to 110 ms after it becomes busy (measured). A thread that sleeps between short bursts, the fake device's pattern, stays at a 1.6 GHz request and an effective 1.4 GHz (measured, section 5.3). The delivered clock over a whole run is still unmeasured.</li>
<li><strong>“No outbound network; we copy everything in.”</strong> The host has outbound network, and the staging of the SDK workspace on 21 October downloaded packages on the host (pip wheels at 44.8 MB/s). The requirement reads as “not needed”, not “must be blocked”. Nobody should block it to match the sentence.</li>
<li><strong>“Ubuntu 24.04's packages cover these.”</strong> Partly. CMake 3.28.3 and Python 3.12.3 with headers are installed system-wide. clang-18 and ninja-build are not installed (they exist in the package index). The staging solved this with a user-level toolchain under the account, so no package install is needed.</li>
<li><strong>How many cores.</strong> Message 1 asks for one or two, message 2 for one, message 3 for cores 120–127 (eight). This is an inconsistency to settle, not an error (decision D3).</li>
<li><strong>“Isolated cores for the pass thread.”</strong> The pass thread is not what voided the first run. The record was voided because the fake device thread's mean lateness passed the band, and the SDK does not pin that thread. The host's clock alone does not explain that lateness (section 5.3). The thread's placement is the first fix, and isolation of the pass core is the second (decision D5).</li>
<li><strong>“One job at a time.”</strong> No host mechanism enforces it. The SDK's perf lane holds a lock while it runs. Jeremy's churn job script holds none. Jibin's own logins count as well (decision D4).</li>
</ul>
</section>""")

# ---- section 3: status matrix
rows = [
    ("Account positron-perf with SSH key login", DONE, "Account exists (uid 1001). Three keys installed: Jibin's workstation key, <code>jeremy@sw-dev-01</code>, <code>jeremy@DESKTOP-V2B1166</code>. Used from alpha (about 50 sessions, 17:07–18:58 UTC 21 Oct) and from sw-dev-01 (4 sessions).", "no", "no", "no", "no (A10: both keys are his, both logins worked)"),
    ("Reachable from Jeremy's laptop or via sw-dev-01", DONE, "sw-dev-01 (192.168.2.39 on the LAN) logged in as positron-perf four times on 21 Oct. Jibin confirmed on 22 Oct that the laptop login worked too (A10).", "no", "no", "no", "nice"),
    ("clang 18, CMake ≥ 3.25, Ninja, Python ≥ 3.11 + headers", DONE, "User-level toolchain under <code>~/positron/toolchains/sdk-ci-2026-10</code>: clang 18.1.8, CMake 3.31.6, Ninja 1.13.2, gcc 13.3.0, plus Python 3.12.3 with headers from Ubuntu. No sudo used. For the perf lane the toolchain is missing from the account's non-interactive PATH (user-level fix).", "no", "no", "no", "nice (perf lane only)"),
    ("About 100 GB of disk", DONE, "1.7 TB free on the root filesystem, which holds /home. No quota. The workspace uses 7.7 GB. One churn run writes about 271 MB.", "no", "no", "no", "no"),
    ("No sudo for the account", DONE, "No usable sudo: password locked, no password-free sudo rule. The 49-byte file <code>/etc/sudoers.d/positron-perf-setup</code> (created 21 Oct 05:12 UTC) lets the <code>arm</code> account open a shell as positron-perf and grants positron-perf nothing (A4, read by Jibin 22 Oct).", "no", "no", "no", "no"),
    ("No outbound network needed", NA, "The host has outbound network and the staging used it. Nothing to do.", "no", "no", "no", "answered 22 Oct: used only for pinned package installs, never during a timed run"),
    ("Fixed clock: no boost", DONE, "No boost range exists. Firmware highest performance level 140 = nominal level 140 = 2.8 GHz.", "no", "no", "no", "no"),
    ("Fixed clock: performance governor", DONE, "Done 22 Oct 05:36 UTC by a sysfs write from <code>jhan</code>. It persists through the boot argument <code>cpufreq.default_governor=performance</code>. After the 05:43 UTC reboot: 128 × performance, request 2,800 MHz on every CPU (verified).", "yes", "no", "no", "nice: all 128 CPUs or only 120–127 (all 128 applied)"),
    ("Isolated cores (isolcpus) with IRQs kept off", DONE, "Done at the 22 Oct 05:43 UTC reboot: isolated list 126-127, default interrupt mask CPUs 0-119, workqueues off 126-127, no kernel warning (verified 05:44 UTC). “IRQs kept off” is only partly achievable: the timer tick and IPIs stay, and the per-CPU NVMe queue interrupts cannot be moved (they fire only for disk I/O issued from that CPU). Section 5.4 has the idle-host interrupt counts after the reboot.", "yes", "yes", "no", "answered 22 Oct: keep 126-127 (D3 closed), launch line adopted"),
    ("nohz_full on the isolated cores", KERNEL, "Running kernel: <code># CONFIG_NO_HZ_FULL is not set</code>. A busy CPU takes the 250 Hz tick (1,261 timer interrupts in 5 s measured). The installed stock 6.8 kernel has the feature but has never booted on this board. Deferred on 22 Oct: Jeremy says only the later tools/perf host-timing gate needs it, not 5 Nov, and he will say before they need it (Q2).", "yes", "yes", "yes", "answered 22 Oct: not needed before 5 Nov"),
    ("rcu_nocbs on the isolated cores", KERNEL, "Not available on the running kernel (no RCU_NOCB_CPU). A kernel built with NO_HZ_FULL brings it, and nohz_full CPUs get it automatically.", "yes", "yes", "yes", "answered 22 Oct: not needed before 5 Nov"),
    ("Nothing else running during timed runs, nightly window", DONE, "Host side done 22 Oct 05:30–05:33 UTC: 11 timers disabled, tmpfiles-clean masked, netperf stopped and disabled (sysstat kept, A8). Jeremy accepted the windows and the reservation rule on 22 Oct (D4 closed). His run script writes the RUNNING file and refuses to start a run that would end after 21:00 UTC (his reply). The other <code>arm</code> users get the rule from Jibin today (A14).", "yes", "no", "no", "answered 22 Oct: accepted"),
    ("One job at a time", DONE, "No host mechanism, by design. Jeremy's run script creates <code>/tmp/positron-perf.RUNNING</code> and refuses to start while it exists, and his build script stops a build when the file appears (seen on the host 22 Oct, <code>runs/phxship-fa7f715f5f86/build-job.sh</code>).", "no", "no", "no", "answered 22 Oct: accepted"),
    ("Account and one isolated core by Friday 23 Oct", DONE, "Done on 22 Oct, one day early, without nohz_full: the account since 21 Oct, CPUs 126-127 isolated and the performance governor since the 05:43 UTC reboot. “Friday” in Jeremy's time zone ends Fri 23 Oct 21:00 UTC (14:00 PDT).", "yes", "yes", "no", "answered 22 Oct: yes (Q1)"),
    ("Counted runs from Monday 26 Oct", PART, "The host setup is done, and the first counted block comes earlier: Fri 23 Oct 13:00–16:00 UTC (Jeremy's notice, 22 Oct). Whether a churn run counts depends on Jeremy's side: the 21 Oct void came from 2,132 logits-row passes each about 109 µs late (his data), the host clock alone cannot bring the mean under 2.5 µs (Figure 8), and his 12× faster write is not on Phoenix yet.", "yes", "yes", "no", "answered 22 Oct: judge path, device thread to 126, blocks announced 2 h ahead"),
    ("Test 2: sampling unit tests on Arm", NA, "Jeremy, 22 Oct: they run on GitHub's native Arm runners on every C++ change, not on Phoenix yet, need no isolation, and will run on cores 0–95 later. Not needed for Monday.", "no", "no", "no", "answered 22 Oct"),
    ("Test 3: timed compile", NOTDONE, "Jeremy, 22 Oct: not ready on his side and not needed for Monday. His measurement plan seen on the host the same day runs an import-hf build through a script named <code>timed_compile.py</code>; whether that is this test is not stated.", "no", "no", "no", "answered 22 Oct"),
]
A("""<section id="s3"><h2>3. Where each ask stands today</h2>
<p>Status chips: <span class="chip done">✔ done</span> <span class="chip live">● root, no reboot</span> <span class="chip reboot">↻ root + reboot</span> <span class="chip kernel">✖ needs another kernel</span> <span class="chip gray">◑ partly</span> <span class="chip gray">○ not done</span> <span class="chip gray">? unknown</span> <span class="chip gray">– not needed</span>. Root means the administrator accounts <code>arm</code> or <code>jhan</code>.</p>
<table><tr><th style="width:21%">Ask</th><th style="width:12%">Status</th><th>What the host shows</th><th>Root</th><th>Reboot</th><th>Other kernel</th><th>Jeremy's input</th></tr>""")
for ask, st, ev, r, rb, k, j in rows:
    A(f"<tr><td>{ask}</td><td>{st}</td><td>{ev}</td><td>{r}</td><td>{rb}</td><td>{k}</td><td>{j}</td></tr>")
A("</table></section>")

# ---- section 4: decisions
A("""<section id="s4"><h2>4. Jeremy's input: the six decisions, his replies of 22 October, and the messages</h2>
<p><strong>All six decisions are closed.</strong> Jeremy answered on 22 October (his replies are quoted below) and took every default. The table keeps the reasoning for the record and adds his answer in the last column. The second table holds the administrator questions, with five new ones from his replies (A12 to A16), three of them for Jibin today.</p>
<table><tr><th style="width:4%">#</th><th style="width:20%">Decision</th><th>Why it matters</th><th style="width:20%">Default if no answer</th><th style="width:24%">Jeremy's answer, 22 Oct</th></tr>
<tr><td>D1</td><td>Which message is newer, does Friday stand, and is a Friday setup without nohz_full and rcu_nocbs acceptable?</td><td>Message 2 asks for Friday, message 3 says “whenever you have a moment”, and their order is uncertain. The running kernel cannot provide nohz_full. A busy isolated CPU keeps one timer interrupt every 4 ms (1 µs to 2 µs each, est.) until a rebuilt kernel is installed. Message 2 allows “the rest of the list” to follow later, but it named the reboot as the example, not the missing kernel feature.</td><td>Friday stands. Proceed on the current kernel. Treat nohz_full as a parallel kernel task (plan step P4).</td><td>""" + CLOSED + """ Q1: yes. The 250 Hz tick costs at most about 0.05% of a busy core, inside the limits he judges. Friday stood and was met on 22 October.</td></tr>
<tr><td>D2</td><td>Which SDK path produces the counted numbers: the latency judge (churn label) or the perf lane?</td><td>The latency judge runs on the current kernel and needs only a pinned pass thread. The perf lane refuses a host with no core in both isolcpus and nohz_full, which puts the kernel rebuild on the critical path before 5 November. The SDK README says the per-user figures “count only from the perf host”, and the design says U1 p99 and U5 waking count only from an isolated host. That is policy, not code, so Jeremy must say which host state makes a judge-path run count.</td><td>Assume the latency judge. Keep the kernel task running in parallel.</td><td>""" + CLOSED + """ Q2: the churn label and the latency judge on the current kernel. tools/perf is for a later host-timing gate, not 5 November, and is the only user of nohz_full; he will say before they need it. The kernel task is deferred (P4).</td></tr>
<tr><td>D3</td><td>Which CPUs to isolate, and the matching change to the job's launch command.</td><td>On isolcpus CPUs the scheduler does no load balancing. Jeremy's job pins the pass thread to CPU 127 and lets its other threads float over 120–126, where they moved across all seven CPUs in the first run. If all eight are isolated and the threads are not pinned one by one, they stay wherever they first land. With only 126–127 isolated and the job's <code>taskset -c 120-127</code> unchanged, the launcher's shell and Python can land on an isolated CPU and never leave (the kernel places them on any CPU of the mask). The choice is irreversible without another reboot.</td><td>Isolate 126–127. The job runs the label with the CPU set 120-125,127 and starts it as <code>taskset -c 120-125 taskset -c 120-125,127 …</code>. CPU 126 stays free for a pinned fake-device thread. One-core variant: isolate 127 only.</td><td>""" + CLOSED + """ Q3: keep 126–127, no reboot: 127 for the pass thread, 126 for the device thread, his other threads on 120–125. His next run uses the double taskset line; the inner set becomes 120–127 once the device thread pins itself (fine, with the outer call kept: A16).</td></tr>
<tr><td>D4</td><td>Run windows in UTC, the reservation rule, and the clock pass rule.</td><td>The host runs UTC. US clocks change on Sunday 1 November (Jeremy at 06:00 UTC, Jibin at 09:00 UTC), inside the run period. No host mechanism serialises jobs, and Jibin's own logins count. The acceptance rule for “fixed clock” is not stated anywhere.</td><td>Windows Mon–Fri 13:00–21:00 UTC. Jeremy's job writes <code>/tmp/positron-perf.RUNNING</code> (start, end, pid, tag) and removes it at the end, counted windows are announced 2 h ahead, one job at a time, and nobody touches the host while the marker exists. Clock rule: delivered clock on the pass core ≥ 2,772 MHz (99% of 2,800 MHz) from one feedback-counter pair read before and after the run, no polling during it.</td><td>""" + CLOSED + """ Q5 and the clock rule accepted: Mon–Fri 13:00–21:00 UTC, 2 h notice, the RUNNING file (start, end, pid, tag, commit), no run that would end after 21:00 UTC. Clock: 2,772 MHz from one CPPC pair before and after, read on 126 and 127, nothing read during; a miss voids the run. Only a few blocks: one next week, one or two before 5 November. His question back: builds and untimed tests on 0–95 outside the window (A15: yes).</td></tr>
<tr><td>D5</td><td>Will Jeremy pin the fake device thread to its own CPU (126) and give it a 1 µs timer slack before Monday? Has any churn run ever recorded <code>void = false</code>? Is the band itself the item to change?</td><td>The first run was voided by that thread's mean lateness (6.2 µs against 2.5 µs). The SDK pins the pass thread and keeps workers off it but sets no affinity for the device thread, which shared CPUs 120–126 with the other threads at 1.6 GHz. The host clock alone does not reproduce the lateness (section 5.3). Its placement is harness code on Jeremy's side, and it decides whether runs count.</td><td>Jeremy decides. CPU 126 is kept free for it. Jeremy's own first run on the as-built host shows the combined effect of the clock and the isolation. A governor-only run is no longer possible: the reboot came before any re-run.</td><td>""" + CLOSED + """ Q4: yes, the device thread goes to 126 with 1 µs slack; change in progress, aim before Monday, else 126 stays idle. No churn run with a device thread has been non-void yet. The 21 October lateness came entirely from the 2,132 logits-row passes (105–111 µs late each at 1.6 GHz); the write is 12× faster on main (about 5 µs against a 26.6 µs window on LSF hosts), not yet on Phoenix. Figure 8.</td></tr>
<tr><td>D6</td><td>May Jibin re-run <code>~/positron/runs/ev3-churn-job.sh</code> in the positron-perf account (govtest-2 on the as-built host, about 3 min)?</td><td>The re-run gives before/after evidence for the device's mean lateness (govtest-1, the governor-only run, is no longer possible since the reboot came first). They run inside Jeremy's account and workspace. A2 (answered 22 October) says the staging was most likely Jeremy's side, so permission is needed.</td><td>No, and Jibin dropped the question from the message on 22 October. Validation uses Jibin's own probes (hiccup and feedback counters) and Jeremy's own first run.</td><td>""" + CLOSED + """ Item 1: the alpha sessions and churn-r1 were his side's. No re-run by Jibin. His Friday block is the first run on the as-built host.</td></tr>
</table>
<p><strong>The side questions, after 22 October.</strong> Q7 is moot (the governor is on all 128 CPUs). Q8 answered: the clock rule is accepted, and his tool reads the counter pair on 126 and 127. Q9 answered: the sampling tests run on GitHub's Arm runners and need no isolation, the timed compile is not ready, and neither is needed for Monday. Q10 answered: nothing needed, they bring clang and ninja and create the directories. Q11 answered: outbound access is used only for pinned package installs, never during a timed run. Q12 was not asked; its second item is answered by his data (the lateness came from the logits-row writes, not from the interrupts). The list stays for the record:</p>
<ul>
<li>Q7: performance governor on all 128 CPUs (default) or on 120–127 only. The churn job's threads run on 120–126, the perf lane's on 0–119, so host-wide fits both.</li>
<li>Q8: whether the clock pass rule in D4 is acceptable as the definition of “fixed clock”.</li>
<li>Q9: status of the sampling unit tests and the timed compile, and whether they need a slot.</li>
<li>Q10: if the perf lane is the path, three user-level gaps on the host need Jeremy's side. clang and ninja are not on the account's non-interactive PATH, and <code>perf_job.sh</code> does not source the toolchain script. The directories <code>~/positron/fetchcontent</code>, <code>~/positron/artifacts</code> and <code>~/positron/work/sdk-v2</code> do not exist. The lane's ssh alias <code>phoenix-perf</code> must exist on his operator machine. Also: may smartd, rsyslog and sysstat stay? The spec says “no persistent service installed” on the perf host.</li>
<li>Q11: which login paths and keys he uses (sw-dev-01 and alpha were seen, the laptop login worked too, A10), and whether to keep outbound internet (default: keep).</li>
<li>Q12: three small items. The hiccup outputs from 18:40 UTC on 21 Oct. Whether the 1,300 to 7,700 interrupts per second per worker CPU during churn-r1 (the threads' own timed sleeps) are intended. Whether the record writer (three JSON files of about 86 MB) stays off the pass core.</li>
</ul>
<h3>Questions for the administrator (Jibin), none of them blocking the host work</h3>
<p>Jibin answered A1 to A11 on 22 October between 04:30 and 06:35 UTC. A12 to A16 come from Jeremy's two replies later that day. The fourth column records the answer, what was done afterwards, and whether the question is still open.</p>
<table><tr><th style="width:4%">#</th><th style="width:25%">Question</th><th style="width:24%">Why</th><th>Answer and status (22 Oct)</th></tr>
<tr><td>A1</td><td>Is <code>jhan</code> (uid 1002, sudo, created 22 Oct 01:19 UTC from 192.168.2.136) your account, and is <code>arm</code> yours too?</td><td>The hand-off must record who holds root and which account made Thursday's changes.</td><td>""" + CLOSED + """ Yes on both counts: <code>jhan</code> is Jibin's account, and <code>arm</code> is a shared account used by every engineer on the phoenix-crb project. Consequence: the reservation rule (D4) must reach every <code>arm</code> user, and the hand-off records the changes as made from <code>jhan</code>.</td></tr>
<tr><td>A2</td><td>Is alpha (192.168.1.200) your machine? Were the staging sessions from alpha (17:07–18:58 UTC 21 Oct), the toolchain README (“approved by Jeremy that day”) and the churn-r1 run done by your side on Jeremy's behalf?</td><td>Decides D6 (re-runs need no permission) and who else must know the reservation rule. A further admin address, 192.168.2.213, used <code>arm</code> on 29 Sep.</td><td>""" + CLOSED + """ Answered on 22 October: Jibin's best guess is that the alpha sessions were Jeremy driving agents, after Jibin set up the login and messaged him at 10:03 PDT (17:03 UTC) on 21 October. The timing fits: the first positron-perf sessions from sw-dev-01 and from alpha both started at 17:07 UTC, four minutes after that message [phoenix-crb-round6.txt]. Consequences: alpha is a shared machine (Jibin logs in from it too), the staging and churn-r1 are Jeremy's side's work, D6 stays no, and Q6 was later dropped from the message. Item 1 of the message asked Jeremy to confirm this, and he did on 22 October: the sessions from alpha and the churn-r1 run were his side's.</td></tr>
<tr><td>A3</td><td>Is there out-of-band access (BMC address and credentials, or physical access) before the reboot? What is EFI boot entry 0010 (first in BootOrder while BootCurrent is 0001)? Is the second disk nvme1n1 (200 MB vfat plus 1.7 TB xfs, Boot0002) another operating system?</td><td>The three planned boot arguments cannot fail the boot (bad values are warned about and dropped), but any other boot fault needs console access. A BMC chip is present (ASPEED AST1150), but no <code>/dev/ipmi*</code> device exists, and the GRUB menu is on the EFI console.</td><td>""" + PARTQ + """ BMC access exists and Jibin has it, which is the console path the reboot needed. Entry 0010 and the second disk stay unknown. Neither blocked the reboot of 22 October: the boot arguments could not fail the boot, the GRUB saved entry still names the vendor kernel, and the host booted the vendor kernel at each of its last four boots (3, 5, 20 and 22 October). Both stay unknown and block nothing now.</td></tr>
<tr><td>A4</td><td>What does <code>/etc/sudoers.d/positron-perf-setup</code> (49 bytes, 21 Oct 05:12 UTC) grant? <code>sudo cat</code> it and run <code>sudo visudo -cf</code> on it.</td><td>It grants nothing usable today. If it was meant to give cpupower or governor control, it must not reference <code>/usr/bin/cpupower</code> while that file is owned by positron-perf.</td><td>""" + CLOSED + """ Content: <code>arm ALL=(positron-perf) NOPASSWD: /usr/bin/bash</code>, and it parses. It lets the <code>arm</code> account open a shell as positron-perf without a password. It grants positron-perf nothing and does not reference cpupower, so nothing needs to change. Side effect worth knowing: every <code>arm</code> user can read and change Jeremy's workspace through it.</td></tr>
<tr><td>A5</td><td>Fix the <code>linux-tools</code> ownership (step P1d) before any root use of perf, cpupower or bpftool.</td><td>Security: 347 files under /usr, /etc and /lib were owned by uid 1001 until step P1d on 22 October.</td><td>""" + CLOSED + """ Done by Jibin at about 05:25 UTC on 22 October and verified from positron-perf at 05:26 UTC: <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code> and the cpupower unit are root-owned. Every file of the package is root:root. No file outside /home belongs to positron-perf (count 347 → 0).</td></tr>
<tr><td>A6</td><td>Is there a channel to Arm's software validation kit (SVK) team to ask for the kernel tree at <code>4dbc8bb88858</code> with its config, or for a build with <code>CONFIG_NO_HZ_FULL=y</code>? What date is realistic?</td><td>The package maintainer is an arm.com address (<code>avadnaik@2paltra-216.5g.ast.arm.com</code>). The source is not on the host. Secure Boot is off, so a local build needs no signing.</td><td>""" + OPENQ + """ Dan asked Arm to grant Jibin access to Arm's GitHub, so that Jibin can rebuild the kernel from source (answer pending). Is it blocking? It blocks only nohz_full and rcu_nocbs. It does not block Friday: the account, the isolated core and the governor come from the current kernel. It blocks the 5 November demo only if Jeremy answers D2 with the perf lane, which refuses a host without nohz_full. Jeremy picked the latency judge on 22 October and said tools/perf, the only user of nohz_full, is for a later gate, so the rebuilt kernel is deferred (P4) and nothing blocks the demo. Arm's answer is still pending, and nothing waits on it this week.</td></tr>
<tr><td>A7</td><td>Reboot slot Thursday 22 Oct 15:00 UTC (08:00 PDT, 11:00 EDT), 10 to 15 minutes: agreed? The idle <code>arm</code> console session on tty1 (since 20 Oct 19:31 UTC) ends with the reboot.</td><td>The fallback slot (Friday 13:00 UTC) was not needed: the reboot ran at 05:43 UTC on 22 October.</td><td>""" + CLOSED + """ Reboot approved for any time the host is idle. State at 04:41 UTC on 22 October: no positron-perf process, load 0.00, and the <code>arm</code> session on tty1 was an idle shell under <code>/bin/login</code> with 0.05 s of CPU time in 33 hours, that is a console left logged in, not a job. Jibin ran the steps in this order: P1d (about 05:25 UTC), P1b (05:30–05:33), P1c and the A8 drop-in (05:34), P1a (05:36), then the P2 drop-in, <code>update-grub</code> and the reboot (05:43), then the P2 checks. The P1a service is unnecessary when the boot argument <code>cpufreq.default_governor=performance</code> is used: the performance governor is built into this kernel (<code>CONFIG_CPU_FREQ_GOV_PERFORMANCE=y</code>), and the parameter exists (<code>/sys/module/cpufreq/parameters/default_governor</code>). Outcome: Jibin rebooted at 05:43 UTC on 22 October, the host was back by 05:44 UTC, and every P2 check passed (evidence file <code>verification-2026-10-22/postreboot-0545.txt</code>).</td></tr>
<tr><td>A8</td><td>Three optional live settings: (1) <code>rcu_normal=1</code> (removes function-call IPIs to the pass core from service starts and namespace teardowns, makes expedited grace periods normal ones, milliseconds slower for mounts), (2) <code>CPUAffinity=0-119</code> in <code>/etc/systemd/system.conf</code> (keeps every service off 120–127 now, needs <code>daemon-reexec</code>), (3) keep <code>sysstat-collect.timer</code> for 10-minute sar history as quiet-window evidence, or disable it.</td><td>Each is reversible. The plan includes (1) and keeps (3) by default.</td><td>""" + CLOSED + """ All three accepted and done. (1) <code>rcu_normal=1</code> went live at 05:34 UTC and persists through the boot argument (reads 1 after the reboot). (2) Added at 05:34 UTC as a drop-in, <code>/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf</code> with <code>[Manager]</code> and <code>CPUAffinity=0-119</code>, which the reboot applies to every service and login shell. It keeps admin sessions and services off the job's six worker CPUs as well as off 126–127. After it, the P2 check of PID 1 shows <code>0-119</code> instead of <code>0-125</code>. Jeremy's <code>taskset</code> still works: an explicit affinity call may name CPUs outside the inherited mask. (3) The sysstat timers stay for the 10-minute history.</td></tr>
<tr><td>A9</td><td>Hardening, not a demo blocker: sshd allows root password login (<code>PermitRootLogin yes</code>, <code>PasswordAuthentication yes</code> in the main file and three drop-ins). Should the kernel meta-packages be held (<code>apt-mark hold linux-image-virtual linux-headers-virtual linux-virtual</code>) so apt never installs kernels again?</td><td>Root password login is a second privileged path that the reservation rule cannot see.</td><td>""" + CLOSED + """ Deferred by Jibin: not a demo blocker, so no change now. Mitigation already in the plan: the apt timers are disabled in P1b, so apt installs no kernel during the run period.</td></tr>
<tr><td>A10</td><td>Close the “which key did Jeremy use” question from the system journal: <code>sudo journalctl _COMM=sshd -g "Accepted publickey for positron-perf" --since 2026-10-21 -o short-iso</code>.</td><td>The account's own journal does not contain the “Accepted” lines.</td><td>""" + CLOSED + """ Yes, that answers it from Jibin's own knowledge, so the journal query was not run. Both keys are Jeremy's (laptop = <code>jeremy@DESKTOP-V2B1166</code>, and <code>jeremy@sw-dev-01</code>), and both logins worked. The journal query is no longer needed. A2 adds that the alpha sessions were most likely Jeremy's agents.</td></tr>
<tr><td>A11</td><td>Do you accept that the Friday promise excludes nohz_full and rcu_nocbs, and that Monday's runs may still be void for SDK-side reasons, so that the message to Jeremy says so explicitly?</td><td>The message below says both.</td><td>""" + CLOSED + """ Accepted by Jibin on 22 October at about 06:35 UTC. Items 4 and 5 of the draft below carry the two statements, item 4 in Jibin's own words.</td></tr>
<tr class="sep"><td>A12</td><td>May Jeremy keep running counted blocks under the same rule while Jibin is away (23 to about 29 Oct), and who is the contact if the host needs attention? (Jeremy's second message, item 2.)</td><td>Jibin alone has the BMC console (A3). The other <code>arm</code> users have root for everything else.</td><td>""" + CLOSED + """ Answered by Jibin on 22 October in the reply: yes, same rule. The contact is the phoenix-crb channel (the chat channel of the host's users), and Jibin posts the login details and the BMC access there, so a boot problem no longer waits for Jibin's return. Two corrections to the reply are suggested below it.</td></tr>
<tr><td>A13</td><td>Were the three interactive positron-perf logins from 192.168.2.136 (21 Oct 05:15 and 23:37, 22 Oct 00:51 UTC) Jibin's? (Jeremy's first reply, item 1.)</td><td>Jeremy wants to know who else enters his account.</td><td>""" + CLOSED + """ Yes. 192.168.2.136 is Jibin's workstation. The host's login record shows each lasted 3 to 5 s. The first came a minute after the account was created from the same address (<code>arm</code> sessions 05:03–05:14 UTC, sudoers file 05:12 UTC). The third was followed within seconds by a 27-minute <code>arm</code> session from the same address that created the <code>jhan</code> account. They were Jibin's own test logins and the agent's read-only checks [verification-2026-10-22/state-1756.txt].</td></tr>
<tr><td>A14</td><td>Tell the other <code>arm</code> users the rule, the Friday block and the away week.</td><td>Jibin promised it in Q5 of the message. Nobody else will do it while Jibin is away.</td><td>""" + TODOQ + """ Today, before Jibin leaves: Jibin posts the note at the end of this section in the phoenix-crb channel.</td></tr>
<tr><td>A15</td><td>Builds and untimed tests on cores 0–95 outside the window: OK? (Jeremy, Q5.)</td><td>Those cores are shared with the other engineers' work.</td><td>""" + CLOSED + """ Answered in Jibin's reply: yes, at any time, with the note that build times vary when the other engineers are busy.</td></tr>
<tr><td>A16</td><td>Keep CPU 126 in the inner taskset set (120–127) once the device thread pins itself? (Jeremy, launch line.)</td><td>A taskset call whose new set does not contain its current CPU is moved by the kernel to any CPU of the new set, isolated ones included. That is why the outer <code>taskset -c 120-125</code> exists.</td><td>""" + CLOSED + """ Answered in Jibin's reply: yes, as long as the outer call stays. With it, the inner call already runs inside its set and nothing moves, and threads created later never land on 126 or 127 by themselves.</td></tr>
</table>
<p><strong>What Jibin ran on 22 October (UTC)</strong>, each verified read-only from <code>positron-perf</code> (commands in section 6):</p>
<ul>
<li>P1d ownership fix, about 05:25 (verified 05:26).</li>
<li>P1b timers and netperf, 05:30–05:33.</li>
<li>P1c <code>rcu_normal</code> and the A8 CPUAffinity drop-in, 05:34.</li>
<li>P1a governor loop, 05:36.</li>
<li>P2 drop-in, <code>update-grub</code> and the reboot, 05:43. Host back by 05:44. Checks 05:44–05:52.</li>
</ul>
<p>Done since: the message below was sent on 22 October and Jeremy replied the same day (quoted after it). Still to do today: the reply and the note at the end of this section.</p>
<h3>Message sent to Jeremy on 22 October (for the record)</h3>
<p>Final text as sent by Jibin on 22 October. Jeremy answered it the same day; his reply follows.</p>
<blockquote><pre>Jeremy, status on phoenix-crb (the Phoenix CRB, 192.168.2.45), 22 Oct:

1. Your account, keys, toolchain and disk are in place, and your logins from the laptop and from sw-dev-01
   worked. I take the 21 Oct sessions from alpha (192.168.1.200), and the run of the churn latency label they
   made (record directory ~/positron/runs/churn-r1), to be yours as well. Tell me if not.
2. Done 22 Oct 05:30-05:36 UTC (21 Oct 22:30-22:36 PDT, 22 Oct 01:30-01:36 EDT): the performance governor on
   all 128 CPUs, the housekeeping timers paused until 6 Nov (apt, fstrim, fwupd, man-db, motd, logrotate and
   the rest), the netperf server stopped, and rcu_normal=1 (removes the expedited-RCU cross-CPU interrupts
   that service starts send to busy cores).
3. Done 22 Oct 05:43 UTC (21 Oct 22:43 PDT, 22 Oct 01:43 EDT): one reboot with cores 126-127 isolated
   (isolcpus=domain,managed_irq,126-127), default device interrupts kept off cores 120-127 (irqaffinity=0-119),
   and the governor fixed on the boot line. Cores 120-125 are not isolated, so your harness's other threads
   still get load-balanced across them. Since the reboot every login shell starts with CPU affinity 0-119
   (a systemd setting that keeps services and admin sessions off 120-127). Your taskset calls still place
   threads on 120-127. The per-CPU NVMe completion interrupts stay and fire only for disk I/O issued from
   those cores. Check from your account:
     cat /sys/devices/system/cpu/isolated                              -> 126-127
     cat /sys/devices/system/cpu/cpufreq/policy127/scaling_governor    -> performance
     cat /proc/cmdline                                                 -> carries the arguments above
   I verified these at 05:44 UTC (22:44 PDT, 01:44 EDT), right after the reboot.
4. nohz_full and rcu_nocbs are not possible on the running kernel (built without CONFIG_NO_HZ_FULL). We need to
   rebuild the custom kernel. Dan requested ARM to grant me access to their github. Until we rebuild a new
   kernel, a busy isolated core keeps the 250 Hz timer tick (one interrupt every 4 ms, about 1-2 us each).
5. That 21 Oct run did not count: your tool marked it void because the fake device thread was late by
   6.25 us on average, above the 2.5 us limit. Missing isolation was not the cause. The host clock alone does
   not explain it either: your hiccup probe in sleep mode on an idle core under schedutil was late by only
   0.02 us on average (0 of 2000 cycles over 2.5 us). During that run the device thread shared cores 120-126
   with the other threads, those cores ran at 1.6 GHz, and they took 1,300-7,700 interrupts/s (the threads'
   own timed sleeps). So the host changes above may not make Monday's runs count by themselves. See Q4.
6. The host has outbound internet, and your pip install used it (wheels downloaded on the host). I will keep it.
7. The host is shared: other engineers use it through the arm account. The rule in Q5 keeps them off the
   host while one of your runs is in progress.

Needed change to your launch line, now that 126-127 are isolated: isolated cores get no load balancing, so a
process that lands on one stays there. Run the label with the CPU set 120-125,127 and start it as
  taskset -c 120-125 taskset -c 120-125,127 prlimit ... bash tools/ci/run_scheduled_gate.sh churn ...
so that the shell and Python never land on 126 or 127. churn.py then pins the pass thread to 127 (the last CPU
of the set), and 126 stays free for a pinned device thread.

Questions (one line each is enough). Defaults apply if I hear nothing by Fri 23 Oct 12:00 EDT (09:00 PDT, 16:00 UTC):
Q1 Is a host WITHOUT nohz_full and rcu_nocbs acceptable for Monday's counted runs? Default: yes.
Q2 Which path produces the numbers that count on 5 Nov: the churn label + latency judge (runs on the current
   kernel, needs only a pinned pass thread) or tools/perf (refuses any host without isolcpus AND nohz_full)?
   Default: the judge. If tools/perf, the rebuilt kernel is on the critical path and Arm's date decides.
Q3 Cores: I isolated 126-127 (127 for the pass thread, 126 free for a pinned device thread). If you want 127
   only, or all of 120-127 (only if you pin every thread), say so and I reboot again while the host is idle.
   Default: keep 126-127 with the launch-line change above.
Q4 Will you pin the fake device thread to its own core (126) and give it a 1 us timer slack, as the waker has,
   before Monday? Has any churn run ever recorded device.void=false, and with what late_mean? Default: you
   decide; 126 stays free.
Q5 A timed run needs the host to itself: any other activity, even a login, disturbs it (a login sends two
   interrupts to every core, measured). Other engineers use this host too, so I propose this rule: you run
   Mon-Fri 13:00-21:00 UTC (06:00-14:00 PDT, 09:00-17:00 EDT until 31 Oct, then 05:00-13:00 PST, 08:00-16:00
   EST after the US clock change on Sun 1 Nov), you announce each counted run 2 h ahead, your job writes
   /tmp/positron-perf.RUNNING (start, end, pid, tag) while it runs and removes it at the end, and nobody else
   touches the host while that file exists. I will give the other users the same rule. Default: accepted.
Nice to have: is this clock pass rule acceptable: delivered clock >= 2772 MHz from one CPPC counter pair read
before and after the run on core 127 (no polling during a run)? Status of the sampling tests and the timed
compile. If tools/perf is your path: clang and ninja are not on the account's non-interactive PATH, and
~/positron/fetchcontent, artifacts and work/sdk-v2 do not exist yet.</pre></blockquote>
<h3>Jeremy's reply, 22 October (quoted)</h3>
<blockquote><pre>""" + html.escape(q('reply')) + """</pre></blockquote>
<h3>Jeremy's second message, 22 October, later the same day (quoted)</h3>
<blockquote><pre>""" + html.escape(q('second')) + """</pre></blockquote>
<h3>What the two replies say, in plain English</h3>
<p>Every line of the two messages, what it means for the host, and what changes. Chips: """ + CLOSED + """ settled, """ + JSIDE + """ Jeremy's side is doing it, """ + TODOQ + """ Jibin's action today, """ + NOTICE + """ information only.</p>
<table><tr><th style="width:4%">#</th><th style="width:28%">Jeremy wrote</th><th style="width:30%">In plain English</th><th>What changes, and where it stands</th></tr>
<tr><td>R1</td><td>The 21 Oct sessions from 192.168.1.200 and the churn-r1 run were ours. The interactive positron-perf logins from 192.168.2.136 were not. Were those you?</td><td>He confirms that the staging from alpha and the first run were his side's work, and asks who made three short logins from Jibin's workstation.</td><td>""" + CLOSED + """ A2 and D6 closed (no re-run by Jibin). A13 answers the logins: Jibin's own tests and the agent's read-only checks, 3 to 5 s each. Item 3 of the reply says so.</td></tr>
<tr><td>R2</td><td>Thanks for keeping outbound access. We only use it to install pinned package versions, and never during a timed run.</td><td>The host keeps its internet access. He downloads packages only between runs.</td><td>""" + CLOSED + """ Q11 closed. Nothing to do.</td></tr>
<tr><td>R3</td><td>Q1: Yes. The 250 Hz tick costs at most about 0.05% of a busy core, well inside the limits we judge.</td><td>A host without nohz_full is acceptable for the counted runs. His estimate matches this plan's: 250 ticks per second at 1 to 2 µs each is 0.025% to 0.05% of a core.</td><td>""" + CLOSED + """ D1 closed. The Friday deadline was met on 22 October.</td></tr>
<tr><td>R4</td><td>Q2: The churn label + latency judge, on the current kernel. tools/perf is for a later host-timing gate, not 5 Nov, and it's the only thing that needs nohz_full. I'll let you know before we need it.</td><td>The numbers that count come from the latency judge, which runs on the kernel as it is. The tool that refuses a host without nohz_full is not part of the demo.</td><td>""" + CLOSED + """ D2 closed. The kernel rebuild (A6, P4) is deferred until he asks; Arm's GitHub access is no longer on any path before 5 November.</td></tr>
<tr><td>R5</td><td>Q3: Keep 126-127, no reboot needed: 127 for the pass thread, 126 for the device thread, the rest of our threads on 120-125.</td><td>The core split as built is what he wants. No second reboot.</td><td>""" + CLOSED + """ D3 closed. Figure 6 shows the split.</td></tr>
<tr><td>R6</td><td>Q4: Yes, we'll pin the device thread to 126 with 1 us timer slack. No churn run with a device thread has been non-void yet (only the twins, which have none).</td><td>He takes the SDK-side change this plan asked for. No churn run that has a fake device thread has ever produced a valid record, on any host.</td><td>""" + JSIDE + """ D5 closed on his side: change in progress, aim before Monday 26 October; if not ready, his runs use the double taskset line and 126 stays idle.</td></tr>
<tr><td>R7</td><td>The 21 Oct run was the closest at 6.25 us mean, and all of it came from the 2,132 passes that write a logits row, each about 105-111 us late at 1.6 GHz; none of the other 35,143 passes was late.</td><td>The cause of the void is now known: a specific piece of work on the device thread (writing the pass's output scores) takes longer than its window on 5.7% of the passes. The other 94.3% were on time.</td><td>""" + CLOSED + """ Hypothesis H3 of section 5.3 is confirmed; H2 and H4 did not contribute to the mean. The arithmetic matches the record (2,132 × 109 µs / 37,275 = 6.25 µs). Figure 8 gives the budget: each of those passes may be at most 43.7 µs late for the mean to stay at 2.5 µs.</td></tr>
<tr><td>R8</td><td>That write is now about 12x faster on main (about 5 us against its 26.6 us window on our LSF hosts), but it isn't on Phoenix yet.</td><td>The fix exists in his main branch and is not yet in the code on this host.</td><td>""" + JSIDE + """ This is what makes a run count. The governor alone would leave each late pass 51 to 109 µs late (est.), still over the budget (Figure 8). Whether the tree built on the host today (commit fa7f715f) carries the fix is not stated.</td></tr>
<tr><td>R9</td><td>Q5: Accepted: counted runs only Mon-Fri 13:00-21:00 UTC, 2 h notice, and the RUNNING file. We only need a few blocks of runs: one next week, then one or two before 5 Nov. I'll post each block's times here at least 2 h before it starts.</td><td>He agrees to the reservation rule, and expects two or three blocks in total before the demo. He announces each one in the channel of this conversation.</td><td>""" + CLOSED + """ D4 closed. The announcements reach the channel where Jibin and Jeremy talk; the other <code>arm</code> users get the rule through the phoenix-crb channel (A14). Jeremy is in that channel (Jibin, 22 October), so his notices reach the other users.</td></tr>
<tr><td>R10</td><td>Builds and untimed tests stay on cores 0-95 and never overlap a RUNNING file. Are those OK outside the window?</td><td>He asks whether he may build and run untimed tests at any hour, on the first 96 cores, as long as no timed run is in progress.</td><td>""" + CLOSED + """ A15, answered in Jibin's reply: yes (item 4). Those cores are shared with the other engineers' work.</td></tr>
<tr><td>R11</td><td>Clock rule: Yes, 2772 MHz from one CPPC pair before and after, nothing read during the run. We'll read it on 126 as well as 127. A miss voids the run rather than failing it.</td><td>He accepts the clock pass rule and extends it to the device core. A run whose clock was too low is discarded, not reported as a failure.</td><td>""" + CLOSED + """ Q8 closed. His tool already records the rule (seen in the smoke-run summary on the host: “delivered MHz ≥ 2772 on every measured CPU, one CPPC pair before and after the block”).</td></tr>
<tr><td>R12</td><td>Launch line: our next run uses yours. Once the device thread pins itself, the inner set becomes 120-127 so our tool can give it 126; the outer taskset still starts the shell and Python on 120-125. Tell me if you'd rather keep 126 out of the set.</td><td>He adopts the double taskset line, and asks whether the inner set may include CPU 126 later.</td><td>""" + CLOSED + """ A16, answered in Jibin's reply: yes, as long as the outer call stays (item 5 gives the reason).</td></tr>
<tr><td>R13</td><td>RUNNING file: our run script creates /tmp/positron-perf.RUNNING (start, end, pid, tag, plus our commit), refuses to start if the file exists or if the run would end after 21:00 UTC, and removes it when it exits. If a run is ever killed hard and leaves the file behind, we remove it only after checking its pid is gone.</td><td>His script enforces the rule on his side, including the end of the window.</td><td>""" + CLOSED + """ Seen on the host on 22 October: his build job refuses to start while the file exists and stops a build when it appears; his measurement summary records the file and the block end.</td></tr>
<tr><td>R14</td><td>Before Monday we'll copy in the latest code and rebuild on 0-95, outside any counted run.</td><td>A fresh build of the SDK on the host, on the housekeeping cores.</td><td>""" + CLOSED + """ Done 22 October 16:19 UTC: commit fa7f715f built on CPUs 0–95 at nice 10 with 32 jobs, log ends <code>BUILD-DONE rc=0</code> (section 5.7).</td></tr>
<tr><td>R15</td><td>Sampling tests: they run on GitHub's native Arm runners on every C++ change, but not on Phoenix yet. They don't need isolation, so we'll run them on 0-95 later. The timed compile isn't ready on our side yet. Neither is needed for Monday.</td><td>Test 2 happens elsewhere for now. Test 3 is not ready. Nothing of either is needed for the first runs.</td><td>""" + CLOSED + """ Q9 closed. Section 3 rows updated.</td></tr>
<tr><td>R16</td><td>tools/perf setup: nothing needed. We bring our own clang and ninja and create those directories ourselves.</td><td>The three user-level gaps this plan listed for the perf lane are his side's to fill, when that lane is used.</td><td>""" + CLOSED + """ Q10 closed.</td></tr>
<tr class="sep"><td>R17</td><td>We'll run our first counted block tomorrow, Fri 23 Oct, 13:00-16:00 UTC: CPU, memory and disk measurements on CPUs 0-125 (126-127 untouched; up to 32 GiB of temporary files under our home, deleted at the end), then one churn latency run. /tmp/positron-perf.RUNNING is present for the whole block.</td><td>This is the 2 h notice the rule asks for, one day ahead. It is a notice, not a question and not a host task. For three hours the whole host is his, except the two isolated cores, which his measurements leave alone.</td><td>""" + NOTICE + """ Nothing to do on the host. The disk fits: 1.7 TB free, his own setup log puts the block's peak at about 39 GB. The block is 06:00–09:00 PDT, before most Pacific-time colleagues start. Jibin's part: tell the other users (A14) and acknowledge (item 1 of the reply).</td></tr>
<tr><td>R18</td><td>While you're out next week, is it OK if we keep running counted blocks under the same rule (weekdays 13:00-21:00 UTC, notice here, the RUNNING file)? And who should we contact if the host needs attention?</td><td>He asks for permission to continue without Jibin, and for a contact.</td><td>""" + CLOSED + """ A12, answered in Jibin's reply (item 2): yes, same rule; the contact is the phoenix-crb channel, where Jibin posts the login details and the BMC access.</td></tr>
</table>
""")
A(fig("fig_lateness_budget", "Figure 8. Where churn-r1's mean lateness came from (left) and how late each logits-row pass may be (right). Left: 2,132 of the 37,275 passes wrote a logits row and were late, the other 35,143 were on time (Jeremy's data, 22 October). Right: the measured 105 to 111 µs per late pass at 1.6 GHz, the estimate for the performance governor alone (51 µs if the write scales with the clock, 109 µs if it does not), and the estimate with the 12× faster write (inside the 26.6 µs window, so not late). The dashed red line is the budget: 43.7 µs per late pass keeps the mean at 2.5 µs. The governor alone cannot reach it. The estimates assume the window is 26.6 µs on Phoenix too."))
A("""<table><tr><th style="width:44%">Quantity</th><th class="num">Value</th><th>How it is known</th></tr>
<tr><td>Passes in churn-r1 (Jeremy's count: 2,132 late + 35,143 on time)</td><td class="num">37,275</td><td>Jeremy, 22 Oct. The record's bind summary counts 37,282, seven more; the difference does not change the result.</td></tr>
<tr><td>Mean lateness of one logits-row pass, 6.25 µs × 37,275 / 2,132</td><td class="num">109.3 µs</td><td>Computed; Jeremy says 105 to 111 µs, so the two agree.</td></tr>
<tr><td>Budget per late pass for a 2.5 µs mean, 2.5 µs × 37,275 / 2,132</td><td class="num">43.7 µs</td><td>Computed, assuming every other pass stays on time.</td></tr>
<tr><td>Lateness per late pass at 2.8 GHz, governor alone</td><td class="num">51 to 109 µs est.</td><td>Lower bound: the write (26.6 + 109.3 = 135.9 µs) scales with the clock, 135.9 × 1.6 / 2.8 = 77.6 µs, minus the window. Upper bound: no scaling. Mean 2.9 to 6.25 µs: void either way.</td></tr>
<tr><td>Write time with the 12× faster code on Phoenix</td><td class="num">6 to 11 µs est.</td><td>135.9 / 12 and 77.6 / 12. Both inside the 26.6 µs window, so these passes stop being late. Measured on LSF hosts: about 5 µs (Jeremy).</td></tr>
</table>
<h3>Reply to Jeremy, sent by Jibin on 22 October</h3>
<p>Sent on 22 October after the proofread (the saved file holds Jibin's last version before it; the corrections below were applied by Jibin while sending). Jibin's edit of the draft. It acknowledges the Friday block, answers his five questions (items 1 to 5), says what stays as it is during the away week, and gives him the arithmetic above. Jibin's changes: the contact is the phoenix-crb channel, and Jibin posts the login details and the BMC access there (A12). Saved as <code>reply-to-jeremy-2026-10-22.txt</code> in the evidence folder, the earlier draft as <code>reply-to-jeremy-2026-10-22-draft.txt</code>.</p>
<div class="callout"><strong>Two corrections flagged before sending.</strong> (1) Item 2 says that positron-perf has sudo access. It does not: its password is locked, <code>sudo -n</code> asks for a password, it is in no sudo group, and the only sudo rule that names it lets <code>arm</code> open a shell as positron-perf (A4; re-checked read-only on 22 October 18:28 UTC). Jeremy asked for an account without sudo. Suggested wording: “the arm account has sudo; positron-perf does not”. (2) Sharing positron-perf's login details with the channel lets other engineers into Jeremy's account, which he asked about in item 1 of his reply. The <code>arm</code> users can already open a shell in it through the sudoers rule, so nothing is gained by sharing his login. Jeremy is in the phoenix-crb channel, so no extra line about where to post his notices is needed.</div>
<blockquote><pre>""" + html.escape(REPLY) + """</pre></blockquote>
<h3>Note to the other users of phoenix-crb (to send today)</h3>
<p>For the phoenix-crb channel, where the engineers who use the <code>arm</code> account are, and Jeremy (A14, action T2). Jibin posts it today. Three independent reviewers checked this text and the next one on 22 October (facts against the evidence, credential handling, plain English); their findings were applied: the Pacific times after the 1 November clock change, the block announcements as the signal instead of a file that only a login can show, stopping one's own work before a block, and the meaning of “isolated” and “governor”. One mark <code>&lt;&lt;Jibin: …&gt;&gt;</code> to fill in. Saved as <code>note-to-arm-users-2026-10-22.txt</code>.</p>
<blockquote><pre>""" + html.escape(NOTE) + """</pre></blockquote>
<h3>Access details for the phoenix-crb channel (T3, to post today)</h3>
<p>The follow-up message with the <code>arm</code> account and the BMC access (action T3). Jibin shortened it on 22 October and added two facts: the BMC is at <code>https://192.168.1.119</code> with a “SOL console” button for the serial console, and the <code>arm</code> password is in 1Password. The text below is Jibin's version after a proofread (nine fixes, among them the warning never to boot 6.8.0-147-generic and the safe key-adding command). The long reviewed draft is kept as <code>t3-access-details-2026-10-22-long.txt</code>. The reviewers' changes to that draft were: a safe way to add a key to the shared account (append with <code>&gt;&gt;</code>, public key only, done by a named colleague), the BMC password kept in a password manager with a second holder instead of “ask me”, a post-before-you-touch-it rule for the BMC, no claim that the BMC console shows the boot menu (unverified), and no recipe for entering Jeremy's account in the channel he reads. Jibin fills in the BMC details and the colleague's name at the <code>&lt;&lt;Jibin: …&gt;&gt;</code> marks. Saved as <code>t3-access-details-2026-10-22.txt</code>.</p>
<blockquote><pre>""" + html.escape(ACCESS) + """</pre></blockquote>
</section>""")

# ---- section 5: findings
A("""<section id="s5"><h2>5. What the host check found</h2>
<h3>5.1 The host</h3>
<table><tr><th style="width:24%">Item</th><th>Observed value</th><th style="width:34%">Effect on the plan</th></tr>
<tr><td>Machine</td><td>Arm Limited “Phoenix Reference Server”, EVT0, Quanta motherboard, BIOS AGI-CPU-CRB-v0.7.2 (8 Sep 2026). 128 CPUs, one socket, one memory region (NUMA node), no hyper-threading (SMT), so each CPU is its own core. 377 GiB RAM, no swap. Two 1.7 TB NVMe disks. The second disk holds a 200 MB EFI partition and a 1.7 TB xfs partition and is EFI boot option 2, so it is probably another operating system, not a spare.</td><td>Early silicon: the vendor kernel's workarounds matter (5.2). Do not repurpose the second disk.</td></tr>
<tr><td>OS and kernel</td><td>Ubuntu 24.04.5 LTS, kernel 7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 (a preemptible multi-processor build, HZ = 250), up since 20 Oct 19:06 UTC at the time of the check (rebooted 22 Oct 05:43 UTC). Host time zone UTC, NTP synchronized.</td><td>All windows below are given in UTC with PDT/EDT equivalents.</td></tr>
<tr><td>Accounts and sessions</td><td>Three human accounts: <code>arm</code> (admin), <code>positron-perf</code>, and since 22 Oct 01:19 UTC <code>jhan</code> (admin). <code>arm</code> had an idle console session (tty1) from 20 Oct 19:31 UTC until the reboot of 22 Oct 05:43 UTC ended it. Its remote sessions came from alpha (2–4 h stretches on 1, 20 and 21 Oct), from Jibin's workstation (21 Oct 00:24–05:14 UTC and 22 Oct 00:51–01:18 UTC) and from 192.168.2.213 (29 Sep, install day). Reboots: 29 Sep (×2), 3 Oct, 5 Oct, 20 Oct, and 22 Oct 05:43 UTC (this plan's reboot).</td><td>The reboot was agreed with Jibin (A7) and done on 22 Oct 05:43 UTC. The reservation rule must cover Jibin's own logins.</td></tr>
<tr><td>Remote login policy</td><td>sshd permits root login and password login (<code>PermitRootLogin yes</code>, <code>PasswordAuthentication yes</code> in the main file and three drop-ins written by the Arm installer). The positron-perf password is locked, so that account accepts keys only.</td><td>Hardening question A9. Not a demo blocker.</td></tr>
</table>
<h3>5.2 Isolation and kernel</h3>
<ul>
<li>State on 21 October, before the reboot. Nothing was isolated: <code>/sys/devices/system/cpu/isolated</code> is empty, the <code>nohz_full</code> file does not exist, and the boot line is <code>BOOT_IMAGE=/vmlinuz-7.1.3-… root=UUID=… ro console=tty1 console=ttyAMA0</code>.</li>
<li>The running kernel's build options: <code># CONFIG_NO_HZ_FULL is not set</code>, <code>CONFIG_NO_HZ_IDLE=y</code>, no <code>CONFIG_RCU_NOCB_CPU</code> line, <code>CONFIG_CPU_ISOLATION=y</code>, <code>CONFIG_CPUSETS=y</code>, <code>CONFIG_PREEMPT=y</code>, <code>CONFIG_HZ=250</code>. So isolcpus and irqaffinity work after a reboot. nohz_full and rcu_nocbs cannot work on this kernel.</li>
<li>What the kernel does with the unsupported arguments: <code>nohz_full=</code> is parsed, refused with “Housekeeping: nohz unsupported. Build with CONFIG_NO_HZ_FULL”, and then also listed under “Unknown kernel command line parameters”. <code>rcu_nocbs=</code> has no handler at all and gets only the unknown-parameter notice. The flag form <code>isolcpus=nohz,…</code> is worse: the kernel drops the whole isolcpus setting with it. None of the three has any effect.</li>
<li>A second kernel is installed: Ubuntu's 6.8.0-147-generic, which unattended-upgrades installed on 15 Oct 06:16 UTC (after -142 and -146). Its build has <code>CONFIG_NO_HZ_FULL=y</code> and <code>CONFIG_RCU_NOCB_CPU=y</code>. GRUB's saved entry pins the vendor kernel, so reboots keep the vendor kernel. The login records (since 29 Sep) show every boot on the vendor kernel.</li>
<li>The vendor kernel logs two silicon-specific workarounds at boot: “GICv3: Arm AGI CPU A0 detected, enabling GIC erratum workaround” and “CPU features: detected: Broken broadcast TLBI completion”. The GIC quirk exists only in the vendor tree. The TLBI workaround (erratum 4118414 family) is upstream code that Ubuntu backported into 6.8.0-146, so the stock kernel probably has it. Two further vendor-only errata options are not active on this board (one needs a boot parameter that is not set, the other targets a different CPU). Booting the stock kernel on this board therefore lacks at least the GIC quirk and has never been tried here. It stays an untested risk, not a plan.</li>
<li>The vendor kernel's source is not on the host (only headers, which match upstream 7.1.3 for the isolation code). Its package maintainer is an Arm engineer (<code>avadnaik@2paltra-216.5g.ast.arm.com</code>), and the package was installed from a local file on 28 Sep 17:25 UTC. Secure Boot is off (no lockdown), so a rebuilt kernel needs no signing. The Arm SVK installer left a gcc-14 toolchain in <code>/opt/arm-svk</code> with <code>KERNEL_MCPU=neoverse-v3ae</code> set, which suggests kernel builds for this board are a supported workflow.</li>
<li>Both the running vendor kernel and Ubuntu's 6.8 are recent enough that a cpuset isolated partition updates the kernel's housekeeping masks at run time. Only boot-time isolcpus CPUs appear in <code>/sys/devices/system/cpu/isolated</code>, the file the SDK tools read.</li>
</ul>
<h3>5.3 The clock</h3>
<p>Driver <code>cppc_cpufreq</code>, 128 policies with one CPU each, governor schedutil everywhere at the time of the check (performance everywhere since 22 October 05:36 UTC), limits 1.6–2.8 GHz. The CPPC table says highest = nominal = 140 performance units = 2,800 MHz, lowest 80 units = 1,600 MHz, reference 50 units. One unit is 20 MHz. No boost range exists. schedutil runs in fast-switch mode (no governor threads), so a clock change is a plain register write from the scheduler.</p>
<div class="stats"><span class="stat"><div class="v">2,796 MHz est.</div><div class="l">delivered clock on CPU 121 during a 3 s pinned spin under schedutil, from CPPC feedback counters (139.8 of 140 units)</div></span>
<span class="stat"><div class="v">14 to 110 ms</div><div class="l">time for a spinning thread's request to reach 2.8 GHz under schedutil: 14 ms when forked from a busy parent, about 100 ms when it arrives after a sleep (measured in 8.8 ms windows)</div></span>
<span class="stat"><div class="v">1,435 MHz est.</div><div class="l">effective clock of CPU 125 while running the fake device's sleep-then-spin pattern (hiccup, sleep mode, 3.8 s): the request stays 1.6 GHz, the counters show less</div></span>
<span class="stat"><div class="v">0.02 µs</div><div class="l">mean lateness of that sleep-then-spin pattern on an idle CPU under schedutil, 0 of 2,000 cycles over 2.5 µs (this check, 22 Oct 01:57 UTC)</div></span></div>
""")
A(fig("fig_clock_patterns", "Figure 1. Share of frequency samples at each requested level, by workload pattern, all under schedutil. A thread that sleeps most of the time and spins only for the last 100 µs before each deadline (the fake device's pattern) stays at 1.6 GHz. A continuously busy thread reaches 2.8 GHz. Sources: Jeremy's files freq.idle.txt, freq.sleep.txt, freq.spin.txt, freq.hot.txt in ~/positron/runs (sampling interval not recorded, so the bars show shares of samples, not of time), and this check's 3 s spin."))
A("""<table><tr><th style="width:30%">hiccup probe, 2,000 cycles each, 22 Oct 01:57 UTC</th><th>sleep mode on idle CPU 125 (fake-device pattern)</th><th>spin mode on CPU 126 (never idle)</th></tr>
<tr><td>Lateness of the completion (what the void rule measures)</td><td>mean 0.02 µs, p99 0.05 µs, max 1.0 µs, 0 cycles over 2.5 µs</td><td>mean 0.01 µs, p99 0.03 µs, max 0.0 µs, 0 over 2.5 µs</td></tr>
<tr><td>Longest stall inside the 100 µs spin (the tick and other interrupts)</td><td>p99 2.61 µs, max 5.8 µs, 24 cycles over 2.5 µs (1.2%)</td><td>p99 1.99 µs, max 9.0 µs, 6 cycles over 2.5 µs (0.3%)</td></tr>
<tr><td>Wake-up overshoot of the sleep</td><td>mean 52.7 µs, max 57.9 µs (50 µs default timer slack plus about 3 µs wake-up latency)</td><td>none (no sleep)</td></tr>
<tr><td>Effective clock from the CPPC counters over the 3.8 s</td><td>1,435 MHz est. (71.7 units), CPU active 2.9% of the time</td><td>2,790 MHz est. (139.5 units)</td></tr>
</table>
<p>What this means for hypothesis H1 of the first draft (“the 1.6 GHz sleep-pattern clock causes the fake device's lateness”): <strong>not supported as a sufficient cause</strong>. On a dedicated idle CPU at the low clock the same wait pattern is late by 0.02 µs on average, 300 times below the 2.5 µs band. The clock does matter for the tick's cost. At the low clock a tick stall exceeds 2.5 µs in 1.2% of spin windows (max 5.8 µs). At 2.79 GHz it does so in 0.3% (p99 1.99 µs). The rare 8 µs to 11 µs stalls occur at both clocks. So the performance governor shortens the typical tick stall by about the clock ratio but cannot by itself turn a 6.2 µs mean into less than 2.5 µs.</p>
<p>Remaining hypotheses for churn-r1's 6.2 µs mean, each with the measurement that decides it:</p>
<ul>
<li><strong>H2, CPU sharing.</strong> The device thread is unpinned and shared CPUs 120–126 with the harness's other threads and the launcher's Python, so its wake-up could have to preempt a running thread. Those CPUs took 1,300 to 7,700 interrupts per second from the threads' own timed sleeps (Figure 2). Measurement: a re-run with the device thread pinned to an otherwise idle CPU (D5), comparing <code>late_mean_s</code>.</li>
<li><strong>H3, the retire path's own work.</strong> In <code>fake_device.cpp</code> the thread writes the pass's drain rows and pushes the completion before it computes the lateness, so <code>late_mean</code> includes that work. If that cost scales with the clock, the governor cuts 6.25 µs to about 3.6 µs (est., 1.6/2.8 of it), still above the band. Measurement: no longer separable, because the reboot of 05:43 UTC came before any re-run. Jeremy's first run on the new setup measures the clock and the isolation together.</li>
<li><strong>H4, the 50 µs timer slack.</strong> The thread's sleep ends about 53 µs after the requested time, so only about 47 µs of the 100 µs spin window remain for absorbing a late wake-up. A 1 µs slack (one prctl call, no privilege) widens that margin. Measurement: hiccup with and without the slack, then the SDK change (D5).</li>
</ul>
<div class="callout"><strong>Settled on 22 October by Jeremy's data.</strong> H3 is the cause: all of churn-r1's lateness came from the 2,132 passes that write a logits row, each 105 to 111 µs late at 1.6 GHz, and none of the other 35,143 passes was late. H2 and H4 did not contribute to the mean (they can still add tail latency, which the pin to 126 and the 1 µs slack address). The arithmetic and the budget per late pass are in Figure 8 (section 4). The write is 12× faster on main and not yet on Phoenix, so the clock alone cannot make a run count (2.9 µs mean est. at best).</div>
""")
A(fig("fig_churn_r1", "Figure 2. Jeremy's run churn-r1, per reserved CPU: requested clock over the 34 samples (left) and interrupts per second during the 172.9 s job (right). Only the pass core requested 2.8 GHz. The CPUs that hosted the other harness threads stayed at 1.6 GHz and took the most interrupts, from those threads' own timed sleeps. Sources: ~/positron/runs/churn-r1/isol.samples.jsonl and phoenix-crb-round4.txt."))
A("""<p>How to read the clock without disturbing a run: <code>scaling_cur_freq</code> is the governor's request and costs nothing. The CPPC feedback counters give the delivered clock but each read sends two IPIs to the CPU being read (measured: 10 reads added 20 function-call interrupts), and root's <code>cpuinfo_cur_freq</code> sends four. The reference counter runs at 1,000 MHz only while the CPU is not idle, so the counter pair over a run measures the delivered clock during the active time. Rule for counted runs: one counter pair on the pass core before and after the run, no polling in between. Wake-up latency is favourable: no cpuidle driver is registered (“driver: none”), so idle CPUs wait in the shallow wait-for-interrupt state (WFI) and wake in about 3 µs (measured as overshoot minus slack).</p>
<h3>5.4 Interrupts and the timer tick on CPUs 120–127</h3>
""")
A(fig("fig_ticks", "Figure 3. Timer interrupts received by one CPU in 5 s: 10 when idle, 1,261 when running a pinned spin (CPU 125: 1,258). That is the HZ = 250 scheduler tick. nohz_full would remove it from a CPU that runs a single task (a residual once-per-second tick runs on a housekeeping CPU instead). Nothing on the running kernel can."))
A("""<table><tr><th>What reaches CPUs 120–127</th><th class="num">Since boot (30 h at 01:14 UTC)</th><th>What removes it</th></tr>
<tr><td>Scheduler tick (arch_timer, IRQ 12), 250 per second on a busy CPU, est. 1 µs to 2 µs of handler time each</td><td class="num">5,327,444 (97.1%)</td><td>Only nohz_full (needs another kernel). The performance governor shortens each tick's stall but not its count.</td></tr>
<tr><td>Function-call IPIs (IPI1)</td><td class="num">123,695</td><td>Partly: <code>rcu_normal=1</code> removes the ones from expedited RCU grace periods, which every sandboxed service start or stop triggers (26 IPIs to a busy CPU per start, measured). Any unprivileged user can trigger them too (<code>unshare</code>). Reading the CPPC counters of a CPU sends two. Measured after the reboot with <code>rcu_normal=1</code>: none in a quiet minute, two per ssh login (section text below).</td></tr>
<tr><td>Rescheduling IPIs (IPI0)</td><td class="num">2,032</td><td>Isolation reduces them (no load balancing onto the CPU).</td></tr>
<tr><td>NVMe queue interrupts nvme0q119–126 and nvme1q119–126 (one queue per CPU per disk, managed)</td><td class="num">33,539 (nvme0q124 alone: 22,045)</td><td>Nothing moves them: each queue's mask holds one CPU, so <code>isolcpus=managed_irq</code> has no effect here, and a write to /proc/irq returns “Operation not permitted”. They fire only for disk I/O issued from that CPU. After isolation the page-cache writeback runs on housekeeping CPUs, so only I/O issued synchronously from the pass core (direct writes, fsync) lands there.</td></tr>
<tr><td>Network queues (128 lines on two ports), other device IRQs</td><td class="num">0</td><td>Already elsewhere: every network interrupt is effectively serviced on CPU 0. <code>irqaffinity=0-119</code> only guards against future devices.</td></tr>
<tr><td>Unbound kernel workers (kworker/u…), writeback flushers (seen on CPUs 124 and 127 during churn-r1), unbound kernel threads such as RCU's</td><td class="num">not counted</td><td><code>isolcpus=domain</code> excludes the CPUs from unbound workqueues and unbound kernel threads, and stops the per-CPU vmstat update there. Per-CPU work queued from the CPU itself stays.</td></tr>
</table>
<p>Of all interrupts these eight CPUs took since boot, 91.3% (5,010,908 of 5,487,292) fell inside the 172.9 s of churn-r1 and are the job's own timer wake-ups, not host noise (Figure 2). irqbalance is not installed. No per-CPU watchdog timer runs (the lockup detectors are not built), no broadcast timer exists, and there are no deep idle states. TLB invalidation on this Arm host is a hardware broadcast, not an IPI, so no isolation setting removes it.</p>
""")
A("""<p><strong>After the reboot (22 October, as built).</strong> Counts on CPUs 126 and 127 in the first five minutes after boot, boot activity included: timer ticks 136 and 133, two NVMe queue probe interrupts each (one per disk), rescheduling IPIs 4 and 3, function-call IPIs 557 on each (the identical counts mean broadcasts to every CPU). In a quiet minute at 05:50 UTC with no new login, neither CPU took a single interrupt. Five ssh logins in a 25 s window then produced 10 function-call IPIs on each of the two CPUs, that is two broadcast IPIs per login even with <code>rcu_normal=1</code>, plus 6 and 1 timer ticks. So a login during a counted run costs the pass core two interrupts, which is what the reservation rule in D4 prevents [verification-2026-10-22/ipi-attribution-0552.txt].</p>""")
A(fig("fig_lanes", "Figure 4. Who does what, when, on one reserved CPU: the fake device thread sleeps and then spins before each pass retirement. Its sleep overshoots the requested wake by 53 µs (the 50 µs default timer slack plus wake-up latency), so about 47 µs of the 100 µs spin window remain. The scheduler tick lands every 4 ms. The band that voids a record is a mean lateness of 2.5 µs, thinner than a pixel here. The worst single lateness in churn-r1 was 220 µs. Durations are to scale (1 ms = 100 px). The tick's own length was not measured, and the late completion's position is schematic."))
A("""<h3>5.5 Background work and timers</h3>
<p>State before Jibin's changes, from <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct. Next firings are in UTC. The proposed run window is 13:00–21:00 UTC. On 22 October at 05:30–05:33 UTC Jibin applied the Action column: every unit listed for disabling or masking is now inactive, netperf is stopped and disabled, and the sysstat timers were kept (verified).</p>
<table><tr><th style="width:26%">Service or timer</th><th>When</th><th>Risk for a timed run</th><th>Action (P1b)</th></tr>
<tr><td>apt-daily-upgrade.timer</td><td>daily 06:00 UTC + up to 60 min. Next: Thu 22 Oct 06:28 UTC (Wed 23:28 PDT)</td><td>Installs packages, including kernels (9 and 15 Oct). Automatic reboot is not enabled. <code>unattended-upgrades.service</code> itself is only a shutdown hook.</td><td>Disabled 22 Oct 05:30 UTC, before the 06:28 UTC run.</td></tr>
<tr><td>apt-daily.timer (package lists)</td><td>06:00 and 18:00 UTC + up to 12 h random, so any hour. Last: 21:57 UTC 21 Oct</td><td>Network and CPU bursts at unpredictable times.</td><td>Disable.</td></tr>
<tr><td>fwupd-refresh.timer</td><td>hourly + up to 1 h random</td><td>Firmware metadata refresh, a sandboxed service start (IPIs to busy CPUs) inside every window.</td><td>Disable.</td></tr>
<tr><td>motd-news.timer, man-db.timer, update-notifier-motd.timer</td><td>twice daily at random, daily 00:00–12:00 UTC, weekly</td><td>Short sandboxed service starts.</td><td>Disable.</td></tr>
<tr><td>update-notifier-download.timer, systemd-tmpfiles-clean.timer</td><td>boot + 5 min and boot + 15 min, then daily (after the 05:43 UTC reboot they would fire at 05:48 and 05:58 UTC, outside the window). Both off since 22 Oct 05:30 UTC</td><td>Short.</td><td>Disable the first, mask the second (it is a static unit).</td></tr>
<tr><td>fstrim.timer</td><td>weekly: Mon 26 Oct 00:27 UTC (Sun 25 Oct 17:27 PDT, 20:27 EDT), then Mon 2 Nov 00:00–02:40 UTC</td><td>The root filesystem is mounted with <code>discard</code>, and the kernel's “already trimmed” marks are lost at reboot, so the first run after the reboot re-discards all 1.7 TB of free space.</td><td>Disable until 6 Nov.</td></tr>
<tr><td>logrotate.timer, dpkg-db-backup.timer, e2scrub_all.timer</td><td>00:00–01:00 UTC daily (17:00 PDT, 20:00 EDT), weekly Sun 03:10 UTC</td><td>Seconds of disk activity, outside the window. e2scrub does nothing here (no LVM).</td><td>Disable (harmless either way).</td></tr>
<tr><td>sysstat-collect.timer, sysstat-summary.timer</td><td>every 10 min, daily 00:07 UTC</td><td>One short sampler on a housekeeping CPU. It is collecting (the cron path is disabled, the systemd path is not), so <code>sar -P 120-127 -f /var/log/sysstat/saDD</code> gives independent 10-minute per-CPU history, which already shows churn-r1 on CPU 127.</td><td>Keep by default (A8). Cron's sysstat and cron.daily entries are no-ops.</td></tr>
<tr><td>netperf.service (a “network benchmark” server, <code>netserver</code>, started at boot from an init script)</td><td>always on</td><td>Idle unless someone runs netperf against the host. Then heavy CPU and network on CPU 0 and wherever the process runs.</td><td>Stop and disable, then confirm with <code>pgrep -a netserver</code>.</td></tr>
<tr><td>snapd.socket</td><td>on demand</td><td>Any <code>snap</code> command starts snapd, which tries and fails to mount a snap. Two of this analysis's own checks triggered it.</td><td>Do not run snap commands. Optionally disable the socket (not done on 22 October).</td></tr>
<tr><td>ua-timer, snapd.snap-repair, apport-autoreport</td><td>never (conditions false)</td><td>None.</td><td>Leave.</td></tr>
<tr><td>smartmontools, rsyslog, ModemManager, udisks2, cron, ssh, systemd-networkd/resolved/timesyncd</td><td>always on</td><td>Light. smartd polls the disks every 30 min through the admin queues on CPU 0.</td><td>Leave. They run on housekeeping CPUs now that isolation is active (since the 22 October reboot).</td></tr>
</table>
<p>Re-enabling a <code>Persistent=true</code> timer after the demo runs its missed jobs at once (apt-daily-upgrade within 1 h, apt-daily within 12 h), so the restore step belongs outside any run window. No LSF, continuous-integration runner, Docker or container runtime runs on the host. The positron-perf user manager runs one timer of its own (<code>launchpadlib-cache-clean.timer</code>, 5 min after login, then daily) on housekeeping CPUs, which Jeremy can mask without root.</p>
<h3>5.6 Account, access, tools and storage</h3>
<table><tr><th style="width:24%">Item</th><th>Observed</th><th style="width:30%">Effect</th></tr>
<tr><td>Account</td><td><code>positron-perf</code>, uid 1001, groups positron-perf and users. Password locked. <code>sudo -n</code> says a password is required, and there is no password-free sudo rule. A 49-byte <code>/etc/sudoers.d/positron-perf-setup</code> exists (created 21 Oct 05:12 UTC while three <code>arm</code> sessions were open) and cannot be read by the account.</td><td>Meets “no sudo”. The administrator read the drop-in on 22 October (A4): it lets <code>arm</code> open a shell as positron-perf and grants positron-perf nothing.</td></tr>
<tr><td>Keys</td><td>Jibin's workstation key (comment rewritten to positron-perf@phoenix), jeremy@sw-dev-01, jeremy@DESKTOP-V2B1166. The key file was last changed 21 Oct 16:53 UTC.</td><td>Jeremy's keys are in place.</td></tr>
<tr><td>Login sources (the account's own journal)</td><td>alpha 192.168.1.200: 101 journal lines (about 50 sessions), 17:07–18:58 UTC 21 Oct (the staging). sw-dev-01 at 192.168.2.39: 4 sessions, 17:07–18:27 UTC. Jibin's workstation 192.168.2.136: this check. The journal's “Accepted publickey” lines are root-only, so which key each session used is unknown.</td><td>sw-dev-01 reaches the host. Jibin's A2 answer: alpha's sessions were most likely Jeremy's agents, and the timing fits.</td></tr>
<tr><td>Vendor tool files owned by the account</td><td>347 files from the <code>linux-tools</code> package were owned by uid 1001 until 22 October 05:25 UTC: <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code>, <code>/usr/libexec/cpupower</code>, <code>libcpupower.so</code>, <code>/usr/lib/systemd/system/cpupower.service</code>, <code>/etc/cpupower-service.conf</code> and more. The package was evidently built without fakeroot, so the builder's uid was kept.</td><td>Security finding. Fixed in P1d by Jibin at about 05:25 UTC on 22 October (verified 05:26 UTC: 0 files outside /home owned by positron-perf).</td></tr>
<tr><td>Limits that could matter</td><td>Real-time priority hard limit 0 (SCHED_FIFO refused), nice hard limit 0, locked memory 47.1 GiB, perf_event_paranoid 2 (user-space counters work, no system-wide profiling), dmesg readable. Default timer slack 50 µs.</td><td>The SDK runtime uses affinity calls and one timer-slack call only, no SCHED_FIFO or mlockall, so no limit change is needed today. The SDK design mentions SCHED_FIFO for a future lane, which would need a limits change then.</td></tr>
<tr><td>System tools</td><td>gcc 14.2 and 13.3, CMake 3.28.3, Python 3.12.3 with headers, git, perf, taskset, chrt, numactl, stress-ng, cpupower. No clang-18 or ninja system-wide (apt candidates exist).</td><td>Nothing to install. The user-level toolchain covers the asks.</td></tr>
<tr><td>Network</td><td>Outbound works (DNS, HTTPS to pypi.org and ports.ubuntu.com, TCP to GitHub) and the staging used it. The host uses a public resolver, so internal names such as sw-dev-01 do not resolve there.</td><td>Not a blocker.</td></tr>
<tr><td>Storage</td><td>Root filesystem ext4, 1.7 TB, 41 GB used, 1.7 TB free, mounted with <code>discard</code>. /home is on it. No quota. <code>/boot</code> has 713 MB free. ~/positron uses 7.7 GB.</td><td>“About 100 GB” is covered. Room for one more kernel.</td></tr>
</table>
<h3>5.7 What Jeremy's side already did on the host</h3>
<table><tr><th style="width:26%">Path under ~/positron</th><th>Content</th></tr>
<tr><td>tools/README-toolchain.md, tools/sdk-toolchain.sh, toolchains/sdk-ci-2026-10</td><td>A conda-forge toolchain installed with micromamba 2.9.0 on 21 Oct 18:11–18:19 UTC: clang 18.1.8, CMake 3.31.6, Ninja 1.13.2, gcc 13.3.0, matching sw-dev-01's lock of 6 Oct. The README says “approved by Jeremy that day (user-only toolchain on Phoenix) … no sudo was used”. The approval is self-reported there.</td></tr>
<tr><td>venvs/phoenix-int-base, venvs/sdk-v2-phoenix</td><td>Python 3.12.3 virtual environments with numpy 2.5.3 and the SDK compiler package, downloaded on the host.</td></tr>
<tr><td>src/phoenix-int</td><td>The SDK repository from a git bundle, commit ead1e9a “local integration for Phoenix evidence, never pushed”, author Jeremy Conner, 21 Oct 14:20 EDT. Built in release mode with clang on CPUs 0–95, three targets only (<code>_positron_core</code>, <code>positron-harness</code>, <code>positron-cpuref</code>).</td></tr>
<tr><td>weights/qwen3_5_0_8b, deps/</td><td>Qwen3.5-0.8B weights (1.7 GB), and the libraries googletest, nlohmann_json and nanobind 3.0.1.</td></tr>
<tr><td>runs/ev3-churn-job.sh, runs/churn-r1</td><td>The churn label of the per-user latency gate, run 18:32–18:35 UTC under <code>taskset -c 120-127</code>. The pass thread pinned itself to CPU 127 after one sample on CPU 122. The harness's other threads (four unnamed ones, including the fake device thread, plus a scrub thread) moved across all of 120–126, most often 122, 123, 124 and 126. The label's own Python ran on CPUs 122–123 inside the same set. Verdict INFRA: “the fake device's lateness voids the record”. Device: mean lateness 6.25 µs, maximum 220 µs, band 2.50 µs, <code>void = true</code> (the rule is <code>late_mean &gt; band</code> in <code>pass_log.cpp</code>). Pass bind time, summary over 37,282 passes: p99 67.5 µs, 50 over the 100 µs budget, and a maximum of 1,482.5 µs over the 37,238 passes that did not wait for an input. During the job CPU 127 was 76% busy, CPU 122 12%, the others 1.5–8%. CPUs 0–119 were idle. The record is three JSON files of about 86 MB each.</td></tr>
<tr><td>runs/hiccup, runs/hiccup.c, runs/isol.py, runs/lag*.py, runs/readrec.py, runs/logits-bench</td><td>Probes written after that run: hiccup (the fake device's wait pattern on one CPU), isol.py (isolation snapshot, 5 s sampler, before/after diff), readrec.py (prints a record's device lateness, bind summary and verdict), lag analyses of late passes, and the frequency samples in Figure 1.</td></tr>
<tr><td>runs/phxship-fa7f715f5f86, work/fa7f715f5f86, runs/measure, measure/, tools/fio-3.43, runs/phx-isol.py (22 Oct 16:19–16:48 UTC)</td><td>Seen on 22 October after Jeremy's first reply, read-only: a new tree at commit <code>fa7f715f</code> built on CPUs 0–95 at nice 10 with 32 jobs by <code>build-job.sh</code>, which refuses to start while the RUNNING file exists and stops the build if it appears (log ends <code>BUILD-DONE rc=0</code>). A measurement job with groups A, C and B: an import-hf build and a timing table run through <code>timed_compile.py</code>, memory-bandwidth, hashing and <code>fio</code> disk steps (direct I/O, io_uring), then the churn run. Two smoke runs on CPUs 0–7 at 16:23 and 16:30 UTC passed; their summary records the clock rule (“delivered MHz ≥ 2772 on every measured CPU, one CPPC pair before and after the block”), the RUNNING file and the block end. Their setup log puts a block's peak disk use at about 39 GB (32 GiB of fio files plus 6.6 GB of artifacts) against 1,690 GiB free. <code>phx-isol.py</code> is isol.py changed to read no per-CPU sysfs file of CPUs 120–127 during a run, because such a read can interrupt the isolated core (the effect this check measured as two IPIs per counter read). No positron-perf process was running at 17:56 UTC [verification-2026-10-22/state-1756.txt].</td></tr>
<tr><td>Not present</td><td>No ctest or pytest log (test 2 unverified). No perf-lane layout: <code>~/positron/fetchcontent</code>, <code>~/positron/artifacts</code>, <code>~/positron/work/sdk-v2</code> and the lane's lock file do not exist, and the lane's job script does not source the toolchain.</td></tr>
</table>
<h3>5.8 What the SDK's own tools require</h3>
<ul>
<li><strong>churn.py / latency judge</strong> (the per-user latency gate run on the host): the judge's isolation check passes whenever <code>pass_thread_core</code> is an integer, that is when the pass thread was pinned. It records <code>core_isolated</code> (pass core in <code>/sys/devices/system/cpu/isolated</code>) and the isolated CPU list as facts and never reads nohz_full. The record is void when the fake device's mean lateness passes the band.</li>
<li><strong>tools/perf/records.py and perf_lane.py</strong> (the host timing of the TPS gate and the timed compile): refuse a host with “no online core in both isolcpus and nohz_full”. They require the run to be the dedicated local user on bare-metal aarch64. They flag a one-minute load above 0.5, other users' processes at 5% CPU or more, and any CI-runner process. The workers, the client and the fake device run on the non-isolated CPUs in this tool. The lane holds a lock while its job runs.</li>
<li><strong>Policy in the SDK's documents:</strong> the README says the per-user figures “count only from the perf host”, and the design says U1 p99 and U5 waking count only from an isolated host. The code of the judge does not enforce that. Whether a judge-path run counts is Jeremy's decision (D2).</li>
<li><strong>Thread placement in the runtime</strong>: the pass thread pins itself to <code>pass_thread_core</code>. Worker threads remove the pass CPU from their mask and otherwise keep the job's mask. No code sets the fake device thread's affinity. Only the waker thread lowers its timer slack (to 1 µs). Nothing uses SCHED_FIFO or mlockall.</li>
<li><strong>Consequence for the no-reboot route</strong>: a cpuset isolated partition never shows in <code>/sys/devices/system/cpu/isolated</code>, so churn.py would record <code>core_isolated: false</code> and the perf lane would still refuse the host. The SDK tooling forces the boot-argument route.</li>
</ul>
</section>""")

# ---- section 6: plan
A("""<section id="s6"><h2>6. Action plan, revised 22 October after Jeremy's replies</h2>""")
A(fig("fig_timeline", "Figure 5. Timeline from 21 October to the 5 November demo, revised 22 October. The live root changes and the reboot were done on 22 October, the message went out and Jeremy replied the same day, and his side built new code on the host that afternoon. His first counted block is Friday 23 October 13:00–16:00 UTC, his device-thread change aims at Monday 26 October, and his remaining blocks fall between then and the demo. Jibin is away from 22 to about 29 October (dates approximate). The kernel rebuild is deferred to after the demo. The bottom row marks the host timers, paused since 22 October 05:30 UTC (gray marks show when they would have fired), and the US clock change on Sunday 1 November."))
A("""<div class="phase"><h3>P0. Done 21 to 22 October: decide, write, send</h3><div class="meta">Owner: Jibin. Needs: nothing on the host.</div>
<ul>
<li>The message in section 4 was sent on 22 October, and Jeremy answered the same day, taking every default.</li>
<li>Answer A1 and A2 for the record. A1 was answered on 22 October (<code>jhan</code> is Jibin's, <code>arm</code> is shared). A2 was answered later the same day: the alpha sessions were most likely Jeremy driving agents.</li>
<li>Kernel source (A6): Dan asked Arm on 22 October to grant Jibin access to Arm's GitHub, so that the vendor kernel at commit <code>4dbc8bb88858</code> can be rebuilt with <code>CONFIG_NO_HZ_FULL=y</code>. Answer pending.</li>
<li>Reboot slot (A7): Jibin approved rebooting as soon as the host is idle, and rebooted at 05:43 UTC on 22 October, after P1b and P1d.</li>
</ul></div>
<div class="phase"><h3>P1. Done 22 October about 05:25–05:36 UTC (P1a to P1d, P1e did not run): live root changes, no reboot</h3><div class="meta">Owner: Jibin, from the <code>jhan</code> account. Reboot: no. Reversible in seconds. P1b was done at 05:30 UTC, before the 06:28 UTC apt run. The command blocks below show the commands. The Result lines and section 4 (A5, A8) say which ones were run, and each result was verified read-only from <code>positron-perf</code>.</div>
<p><strong>P1a. Performance governor on all 128 CPUs</strong> (or on 120–127 only, if Jeremy prefers, as each CPU is its own policy). Use sysfs only. Do not use <code>sudo cpupower</code> until P1d is done (P1d was done first, at about 05:25 UTC).</p>""")
A(code("""# as the administrator on phoenix-crb
who; ps -u positron-perf -o pid,etime,cmd | grep -v sshd           # nobody mid-run, no positron-perf job
for p in /sys/devices/system/cpu/cpufreq/policy*; do echo performance | sudo tee "$p/scaling_governor" >/dev/null; done
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c      # expect: 128 performance
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq | sort | uniq -c      # expect: 128 x 2800000 (the request, kHz)"""))
A("""<p>Result: done at 05:36 UTC, 128 × performance. This write does not survive a reboot (the kernel's default governor is schedutil). Persistence comes from the boot argument <code>cpufreq.default_governor=performance</code> in P2, which proved sufficient (128 × performance after the reboot). The boot-time unit below was therefore not installed. It stays as a fallback. In a systemd unit <code>$$</code> is the spelling of a literal dollar sign, and the loop waits up to 60 s for the cpufreq driver module, which udev loads with no ordering guarantee:</p>""")
A(code("""# /etc/systemd/system/positron-governor.service
[Unit]
Description=Positron latency runs: performance cpufreq governor on every CPU
After=multi-user.target
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for i in $$(seq 1 60); do [ -e /sys/devices/system/cpu/cpufreq/policy127/scaling_governor ] && break; sleep 1; done; for p in /sys/devices/system/cpu/cpufreq/policy*; do echo performance > "$$p/scaling_governor"; done'
[Install]
WantedBy=multi-user.target

# then: sudo systemctl daemon-reload && sudo systemctl enable --now positron-governor.service
#       systemctl status positron-governor.service        # expect: active (exited), no error"""))
A("""<p><strong>P1b. Pause the timers and the benchmark server until 6 November.</strong> <code>disable --now</code> survives the reboot. <code>systemd-tmpfiles-clean.timer</code> is a static unit and must be masked instead.</p>""")
A(code("""sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer fwupd-refresh.timer motd-news.timer man-db.timer \\
    update-notifier-download.timer update-notifier-motd.timer fstrim.timer e2scrub_all.timer logrotate.timer dpkg-db-backup.timer
sudo systemctl mask --now systemd-tmpfiles-clean.timer
sudo systemctl disable --now netperf.service; pgrep -a netserver || echo "netserver gone"
# optional (A8): sudo systemctl disable --now sysstat-collect.timer sysstat-summary.timer   # loses the 10-min sar history
# optional:      sudo systemctl disable --now snapd.socket snapd.service                    # snap commands would start snapd
systemctl list-timers --all --no-pager        # expect: sysstat-collect/summary and the three never-firing timers only
systemctl is-active apt-daily-upgrade.timer apt-daily.timer fwupd-refresh.timer netperf.service   # expect: inactive x4"""))
A("""<p><strong>P1c. Expedited-RCU IPIs removed, done 05:34 UTC</strong> (A8, reversible with <code>echo 0</code>, reads 1 after the reboot). It makes every service start and namespace teardown stop sending function-call interrupts to busy CPUs:</p>""")
A(code("""echo 1 | sudo tee /sys/kernel/rcu_normal          # persistent form: rcupdate.rcu_normal=1 in the P2 drop-in
cat /sys/kernel/rcu_normal                        # expect: 1"""))
A("""<p><strong>P1d. Fix the ownership of the vendor tool files</strong> (security, A5). Done at about 05:25 UTC, verified 05:26 UTC (count 347 → 0). It had to come before any root use of perf, cpupower or bpftool. Never enable <code>cpupower.service</code> before it:</p>""")
A(code("""dpkg -S /usr/bin/cpupower                                               # expect: linux-tools: /usr/bin/cpupower
find /usr /etc /lib /opt /var /boot -xdev -user positron-perf | wc -l     # today: 347
dpkg -L linux-tools | xargs -d '\\n' sudo chown -h root:root
find /usr /etc /lib /opt /var /boot -xdev -user positron-perf | wc -l     # expect: 0
ls -l /usr/bin/perf /usr/bin/cpupower /usr/lib/systemd/system/cpupower.service   # expect: root root"""))
A("""<p><strong>P1e. Governor-only re-run of Jeremy's job, before the reboot</strong> (not run, and no longer possible: the reboot came first, so any re-run is govtest-2 in P3, and the clock and isolation effects can no longer be separated). It separates the clock effect from the isolation effect and tests hypothesis H3. Run as <code>positron-perf</code>, with the script unchanged:</p>""")
A(code("""cd ~/positron/runs && ./ev3-churn-job.sh govtest-1                 # about 3 min; writes runs/churn-govtest-1/
python3 ~/positron/runs/readrec.py ~/positron/runs/churn-govtest-1/record     # prints the device lateness and the verdict
python3 -c "import json; print(json.load(open('/home/positron-perf/positron/runs/churn-govtest-1/record/churn/churn.record.json'))['device'])"
# compare with churn-r1: late_mean_s 6.246e-06, late_max_s 2.20e-04, lateness_band_s 2.502e-06, void True"""))
A("""</div>
<div class="phase"><h3>P2. Done 22 October 05:43 UTC: reboot into isolcpus (host back by 05:44 UTC)</h3><div class="meta">Owner: Jibin, from the <code>jhan</code> account, with the BMC console available. Reboot: done once (first proposed for Thursday 15:00 UTC, moved earlier when Jibin approved any idle moment). Every check below passed at 05:44 UTC, and the saved record was taken at 05:46 UTC. Evidence: <code>verification-2026-10-22/postreboot-0545.txt</code>.</div>
<p>One drop-in was added at 05:43 UTC. The cloud-image drop-in <code>50-cloudimg-settings.cfg</code> overrides <code>GRUB_CMDLINE_LINUX_DEFAULT</code>, so the new arguments go on <code>GRUB_CMDLINE_LINUX</code>, which nothing else sets. The CPU list is decision D3 and cannot be changed later without another reboot:</p>""")
A(code("""# Variant A, the default (D3): isolate 126-127; CPU 127 for the pass thread, CPU 126 free for a pinned device thread
sudo tee /etc/default/grub.d/60-positron-isolation.cfg >/dev/null <<'EOF'
# Positron latency runs for Jeremy (Oct-Nov 2026): CPUs 126-127 isolated for the SDK's timing threads, fixed clock request.
GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX isolcpus=domain,managed_irq,126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1"
EOF
# One-core variant (message 2):           isolcpus=domain,managed_irq,127 irqaffinity=0-119 ...
# Variant B, Jeremy's literal request (only if his job pins every thread): isolcpus=domain,managed_irq,120-127 irqaffinity=0-119 ...
# rcupdate.rcu_normal=1 is optional (A8); remove it if you prefer.

sudo update-grub
sudo grep -c 'isolcpus=domain' /boot/grub/grub.cfg      # > 0: the 7.1.3-arm-agi entries carry the arguments
sudo grub-editenv list                                  # saved_entry must still name the 7.1.3-arm-agi kernel
who; pgrep -a netserver; ps -u positron-perf -o pid,cmd | grep -v sshd      # nobody mid-task, no marker file in /tmp
sudo systemctl reboot"""))
A("""<p>Do not add <code>nohz_full=</code>, <code>rcu_nocbs=</code> or the <code>isolcpus=nohz</code> flag on this kernel (section 5.2). The four arguments could not fail the boot: a bad value is reported in dmesg and dropped. <code>isolcpus=managed_irq</code> changes nothing for the single-CPU NVMe queues and is kept only for future devices. <code>irqaffinity=0-119</code> keeps default device interrupts off the whole reserved group. After the reboot, these checks need no root and can be run by <code>positron-perf</code> (expected values are for variant A):</p>""")
A(code("""cat /proc/cmdline                                                      # carries the new arguments
cat /sys/devices/system/cpu/isolated                                   # 126-127
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c      # 128 performance
dmesg | grep -E 'Housekeeping|Invalid flag|Skipped unknown flag|Unknown kernel command line|workqueue: Restricting' | grep -v 'Kernel command line'
                                                                       # must print nothing
cat /sys/devices/virtual/workqueue/cpumask                             # 3fffffff,ffffffff,ffffffff,ffffffff (bits 126-127 clear)
cat /sys/devices/virtual/workqueue/cpumask_isolated                    # c0000000,00000000,00000000,00000000
cat /proc/irq/default_smp_affinity                                     # 00ffffff,ffffffff,ffffffff,ffffffff (CPUs 0-119)
grep Cpus_allowed_list /proc/1/status /proc/$(pgrep -x rcu_preempt)/status   # PID 1: 0-119 (A8 drop-in), rcu_preempt: 0-125 (variant B: 0-119)
taskset -c 127 true && echo "a job can still be placed on 127"
cat /sys/kernel/rcu_normal                                             # 1 if rcupdate.rcu_normal=1 was kept
uname -r; uptime; who"""))
A("""<p><strong>Result, 22 October 05:44–05:48 UTC</strong> (read-only, as <code>positron-perf</code>): the boot line carries the four arguments and both console settings. The isolated list is 126-127. All 128 policies run performance at a 2,800 MHz request. <code>rcu_normal</code> reads 1 and dmesg says “No expedited grace period (rcu_normal)”. The workqueue mask excludes 126-127 and the isolated mask holds exactly them. The default interrupt mask is CPUs 0-119. PID 1 is allowed 0-119 (the A8 drop-in, not the kernel), <code>rcu_preempt</code> 0-125. <code>taskset -c 127 true</code> works. The filtered dmesg grep printed nothing. The eleven timers are disabled, tmpfiles-clean is masked, netperf is inactive and netserver is gone. Only Jibin was logged in (the console session on tty1 ended with the reboot). In a 10 s idle window at 05:46 UTC, CPUs 126 and 127 took no interrupt at all and were 100% idle (the saved 60 s window at 05:50 UTC in <code>ipi-attribution-0552.txt</code> shows the same).</p>""")
A(fig("fig_cpu_alloc", "Figure 6. The split of the 128 CPUs as applied at the 22 October 05:43 UTC reboot (variant A), and what reached each reserved CPU before that reboot (section 5.4 has the counts after it). Variant A isolates 126–127 within the reserved group of eight, with 120–125 kept free by agreement for the job's other threads. Variant B isolates all eight."))
A("""</div>
<div class="phase"><h3>P3. Done 22 October: validation and the hand-off message</h3><div class="meta">Owner: Jibin with Jeremy. The Friday deadline was met on 22 October: the host checks passed at 05:44 UTC, the message went out, and Jeremy replied the same day. The notes below stay for the record.</div>
<ul>
<li>No re-run by Jibin: Jeremy's own blocks are the runs on the as-built host (D6 closed). The launch line below is the one his next run uses; the inner set widens to 120–127 once the device thread pins itself (A16):</li>
</ul>""")
A(code("""# today:
taskset -c 120-127 prlimit --data=51539607552 timeout --signal=TERM --kill-after=5m 45m bash tools/ci/run_scheduled_gate.sh churn $R/record
# after the reboot (variant A): land the launcher on a balanced CPU first, then widen the set to include the pass core 127
taskset -c 120-125 taskset -c 120-125,127 prlimit --data=51539607552 timeout --signal=TERM --kill-after=5m 45m bash tools/ci/run_scheduled_gate.sh churn $R/record
# churn.py then pins the pass thread to the set's last CPU (127) and gives the other threads 120-125; CPU 126 stays empty."""))
A("""<ul>
<li>Compare with churn-r1 (govtest-1 never ran): the judge verdict, the device's mean lateness against the band, and the pass bind p99 and maximum. In isol.py's samples every harness, python and bash thread must show <code>psr</code> 120–125 or 127, never 126.</li>
<li>Delivered clock, without root and without disturbing the run: one feedback-counter pair on the pass core before and after the run.</li>
</ul>""")
A(code("""# as positron-perf: once before and once after a run; each read sends 2 IPIs to CPU 127, so never poll during a run
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R0> del:<D0>
# ... the run ...
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R1> del:<D1>
# delivered MHz = 50 * (D1 - D0) / (R1 - R0) * 20.  Pass: >= 2772 MHz (99% of 2800). A 3 s spin measured 2796 MHz (139.8 units)."""))
A("""<ul>
<li>Hand-off note to Jeremy, with these items:<ul><li>kernel version, exact boot line, isolated CPU list, governor state, and the counter pair</li><li>the expected sysfs values from P2 and the paused timers</li><li>the reservation rule and the launch-line change</li><li>the known limitation: no nohz_full, so a busy isolated CPU keeps the 250 Hz tick (and two broadcast IPIs per ssh login even with rcu_normal=1, measured 05:50 UTC)</li><li>the pre-run checklist from section 7</li></ul></li>
</ul></div>
<div class="phase"><h3>P4. Deferred to after the demo: a kernel with nohz_full, only when Jeremy asks for the tools/perf host-timing gate</h3><div class="meta">Owner: Jibin, once Arm grants the GitHub access that Dan requested on 22 October (path A below), then the administrator for the install. Reboot: a second one. Target: after 5 November. Jeremy said on 22 October that tools/perf is the only user of nohz_full, is not needed for the demo, and that he will say before they need it (Q2). Nothing here runs during the away week.</div>""")
A(fig("fig_kernel_paths", "Figure 7. The counted runs use the current kernel. nohz_full, deferred on 22 October until Jeremy asks for the tools/perf gate, needs one of three kernel paths. Rebuilding the vendor kernel from its source is preferred. Booting the installed stock 6.8 kernel is not recommended on this A0 silicon."))
A("""<ul>
<li>Obtain the vendor kernel's source at commit <code>4dbc8bb88858</code> with its config, or a build, with <code>CONFIG_NO_HZ_FULL=y</code>. The option sits in a choice with <code>NO_HZ_IDLE</code>, so the builder disables one and enables the other, then checks the result:</li>
</ul>""")
A(code("""cp /boot/config-7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 .config
scripts/config --disable NO_HZ_IDLE --enable NO_HZ_FULL --set-str LOCALVERSION -positron-nohz
make olddefconfig
grep -E '^(CONFIG_NO_HZ_FULL|CONFIG_RCU_NOCB_CPU|CONFIG_VIRT_CPU_ACCOUNTING_GEN|CONFIG_CONTEXT_TRACKING_USER|CONFIG_CPU_ISOLATION)=y|^# CONFIG_NO_HZ_IDLE is not set' .config
# all six lines must appear; build a .deb with fakeroot so its files are owned by root; a distinct version string keeps the vendor files intact"""))
A("""<ul>
<li>Install it as an additional menu entry. Trial-boot it once with <code>grub-reboot</code> (one-shot, works because /boot is plain ext4), so a failed boot returns to the vendor kernel. Secure Boot is off, so no signing is needed.</li>
<li>Change the drop-in to identical CPU lists, which the kernel requires: <code>isolcpus=domain,managed_irq,126-127 nohz_full=126-127 rcu_nocbs=126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1</code>. Then check <code>cat /sys/devices/system/cpu/nohz_full</code> (126-127), <code>cat /sys/devices/system/cpu/housekeeping</code> (0-125, printed only when the feature works) and <code>dmesg | grep -E 'NO_HZ|Offload RCU|Housekeeping'</code> for “NO_HZ: Full dynticks CPUs: 126-127” and “Offload RCU callbacks from CPUs: 126-127”.</li>
<li>Rules on a nohz_full kernel: the isolated CPU must run a single task (a second runnable thread brings the tick back), and that task must not use POSIX CPU timers. The pass thread meets both today. <code>cpuinfo_avg_freq</code> stops working for those CPUs, so the counter pair stays the clock evidence.</li>
<li>Time needed: insufficient data. It depends on Arm's response (A6).</li>
</ul></div>
<div class="phase"><h3>P5. Thursday 22 October, before Jibin logs out: the messages, nothing on the host</h3><div class="meta">Owner: Jibin. Needs: nothing on the host. The host is in its final state for the demo, and nothing expires while Jibin is away. The host check of 17:56 UTC is saved as <code>verification-2026-10-22/state-1756.txt</code> (Jeremy's build finished with <code>BUILD-DONE rc=0</code>, no positron-perf process).</div>
""" + TODAY + """
</div>
<div class="phase"><h3>P6. Friday 23 October 13:00–16:00 UTC (06:00–09:00 PDT, 09:00–12:00 EDT): Jeremy's first counted block, Jibin absent</h3><div class="meta">Owner: Jeremy. Host: unattended, nothing to do. Nobody else on the host for the whole block.</div>
<ul>
<li>What runs, from his notice and his measurement plan on the host: CPU, memory and disk measurements on CPUs 0–125 (an import-hf build and timing table, memory bandwidth, hashing, <code>fio</code> with up to 32 GiB of temporary files under his home, deleted at the end), then one churn latency run. The RUNNING file is present throughout, and his script refuses to start a run that would end after 21:00 UTC.</li>
<li>Disk: 1.7 TB free on the root file system. His own setup log puts the block's peak at about 39 GB. The root file system discards freed blocks online, so the deletion costs nothing later.</li>
<li>Cores 126–127 stay untouched by the measurements. The churn run uses the double taskset line unless the device-thread pin is already on Phoenix, in which case the device thread goes to 126.</li>
<li>What to read afterwards (Jeremy's side, or Jibin on return): the judge verdict and the <code>void</code> flag, the device's <code>late_mean_s</code> against the band, which passes were late (the logits-row passes again, or none), and the clock pair on 126 and 127 (≥ 2,772 MHz). A void from the logits-row write is expected until the 12× faster write is on Phoenix (Figure 8).</li>
</ul></div>
<div class="phase"><h3>P7. 23 to about 29 October: Jibin away, Jeremy's blocks continue under the rule</h3><div class="meta">Owner: Jeremy for the runs, the other <code>arm</code> users for anything else, the contact named in the reply for problems. Host: unattended.</div>
<ul>
<li>Jeremy's side, by his reply: the device thread pinned to 126 with 1 µs slack (aim: before Monday 26 October, else 126 stays idle), the RUNNING-file script (in place, seen on the host), the rebuilt tree (done 22 October 16:19 UTC), one block of counted runs next week announced 2 h ahead, builds and untimed tests on cores 0–95 outside the blocks.</li>
<li>The other <code>arm</code> users: run <code>ls /tmp/positron-perf.RUNNING</code> before any work. If the file exists, stay off the host (even a login sends two interrupts to every core). Do not change boot settings, install packages, re-enable timers or reboot. If a reboot is unavoidable, the settings persist (they are on the boot line and in enabled units), but it kills any run in progress.</li>
<li>If the host needs attention: the phoenix-crb channel is the contact (A12). The <code>arm</code> users have root, and Jibin posts the BMC access in the channel, so a boot problem can be handled there too. The settings live in the GRUB and systemd drop-ins, not in the kernel image, and the saved GRUB entry boots the vendor kernel.</li>
<li>No action for Jibin and none for this analysis. Read-only checks resume on request after Jibin returns.</li>
</ul></div>
<div class="phase"><h3>P8. About 29 October to Thursday 5 November: Jibin back, the last blocks, the demo</h3><div class="meta">Owner: Jeremy runs. Jibin keeps the host ready and reviews.</div>
<ul>
<li>On return: read Jeremy's block results (verdicts, void reasons, clock pairs) and the host's login record for the away week, then re-run the read-only state check and save it next to <code>state-1756.txt</code>.</li>
<li>Jeremy's one or two remaining blocks before 5 November, same rule. The checklist in section 7 stays valid for anyone who runs on the host.</li>
<li>Windows (D4): Mon–Fri 13:00–21:00 UTC. That is 06:00–14:00 PDT and 09:00–17:00 EDT until 31 October, and 05:00–13:00 PST and 08:00–16:00 EST from 2 November. The second weekly fstrim would fall on Mon 2 Nov 00:00–02:40 UTC; it stays disabled.</li>
<li>Thursday 5 November: the demo. Nothing on the host changes before it.</li>
</ul></div>
<div class="phase"><h3>P9. After Friday 6 November: restore the host</h3><div class="meta">Owner: Jibin, outside any run window.</div>
<ul>
<li>Re-enable the timers and netperf (or leave netperf off), expect an immediate apt catch-up run, and decide with Jeremy whether the governor and the isolation stay. They cost nothing while nobody needs cores 126–127, and the tools/perf gate would later need the nohz_full kernel of P4 as well.</li>
</ul>""")
A(code("""# restore, after 6 Nov, outside any run window
sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer fwupd-refresh.timer motd-news.timer man-db.timer \\
    update-notifier-download.timer update-notifier-motd.timer fstrim.timer e2scrub_all.timer logrotate.timer dpkg-db-backup.timer
sudo systemctl unmask systemd-tmpfiles-clean.timer && sudo systemctl start systemd-tmpfiles-clean.timer"""))
A("""</div>
<h3>A no-reboot fallback (not needed: the reboot happened on 22 October 05:43 UTC, kept for the record)</h3>
<p>Root can create a cgroup v2 cpuset “isolated partition” for the chosen CPUs while the system runs. On this kernel it gives the scheduler-isolation part of isolcpus and also removes the CPUs from unbound workqueues, unbound kernel threads and the timer-migration hierarchy. It does not give nohz_full, does not move the managed NVMe interrupts, and does not persist across reboot. It does not show in <code>/sys/devices/system/cpu/isolated</code>, so Jeremy's tools record <code>core_isolated: false</code> and the perf lane still refuses the host. Three more limits:</p>
<ul><li>positron-perf cannot move its own processes into the partition. Root must write the process id, or delegate the cgroup.</li>
<li>One process cannot straddle the partition and the rest. Jeremy's one-process layout then needs the whole job inside, or an untested threaded-cgroup variant.</li>
<li>systemd 255 can drop a hand-enabled cpuset controller when it next re-realizes the root slice with a new controller set.</li></ul>
<p>The reboot did not slip, so this was not used. Use it only if isolation must change without a reboot, tell Jeremy what it lacks (decision D1 then includes it), and test it once before offering it.</p>""")
A(code("""# root; no reboot; lost at the next reboot
echo +cpuset > /sys/fs/cgroup/cgroup.subtree_control
mkdir /sys/fs/cgroup/positron-isolated
echo 126-127 > /sys/fs/cgroup/positron-isolated/cpuset.cpus
echo isolated > /sys/fs/cgroup/positron-isolated/cpuset.cpus.partition
cat /sys/fs/cgroup/positron-isolated/cpuset.cpus.partition      # expect: isolated (anything else names the reason)
chown positron-perf /sys/fs/cgroup/positron-isolated /sys/fs/cgroup/positron-isolated/cgroup.procs   # lets the job join it
# the job then runs:  echo $$ > /sys/fs/cgroup/positron-isolated/cgroup.procs  before taskset
# guard against systemd removing the controller: systemctl set-property --runtime system.slice AllowedCPUs=0-127
# weaker alternative without a partition (keeps services off the group, no isolation): systemctl set-property --runtime system.slice AllowedCPUs=0-119"""))
A("""<h3>Rollback</h3>
<ul>
<li>Governor: <code>echo schedutil</code> into every policy's <code>scaling_governor</code>, and, for the next boot, remove <code>cpufreq.default_governor=performance</code> from the GRUB drop-in and run <code>update-grub</code> (no unit was installed).</li>
<li>Timers: the restore commands in P5.</li>
<li>Boot arguments: remove <code>/etc/default/grub.d/60-positron-isolation.cfg</code>, run <code>update-grub</code>, reboot. In an emergency the GRUB menu lists every entry. It shows on the EFI console (serial mirroring unverified), and a failed boot retries the saved entry after 10 s. Console access (A3) is the real safety measure.</li>
<li>Kernel: keep the current entry. The saved-entry setting selects it until changed, and <code>grub-reboot</code> trials return to it.</li>
<li><code>rcu_normal</code>: <code>echo 0</code> into <code>/sys/kernel/rcu_normal</code>, and drop the boot argument. Service CPU affinity: remove <code>/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf</code> and run <code>systemctl daemon-reexec</code>, or reboot.</li>
</ul>
</section>""")

# ---- section 7: acceptance
A("""<section id="s7"><h2>7. Acceptance checks</h2>
<h3>Friday 23 October: the host is ready when</h3>
<table><tr><th style="width:20%">Check</th><th>Evidence to keep</th><th style="width:28%">Ready means</th><th style="width:24%">Status 22 Oct 05:48 UTC</th></tr>
<tr><td>Boot arguments took effect</td><td><code>/proc/cmdline</code>, <code>/sys/devices/system/cpu/isolated</code>, the filtered dmesg grep from P2, the workqueue masks, <code>/proc/irq/default_smp_affinity</code>, PID 1's allowed CPUs</td><td>The isolated list equals the agreed CPUs (D3), the dmesg grep prints nothing, and the masks match the expected values in P2.</td><td>""" + DONE + """ Passed: isolated 126-127, dmesg grep empty, masks as expected, PID 1 on 0-119 (A8 drop-in).</td></tr>
<tr><td>Clock</td><td>128 × performance, and one feedback-counter pair on the pass core around the govtest-2 run</td><td>Delivered clock on the pass core ≥ 2,772 MHz (D4). <code>scaling_cur_freq</code> reads 2,800,000 kHz on 120–127 in every isol.py sample.</td><td>""" + PARTQ + """ 128 × performance verified (again 17:56 UTC). The counter pair comes from Jeremy's own script on 126 and 127 around each block, first on Fri 23 Oct.</td></tr>
<tr><td>Interrupts and workers off the isolated CPUs</td><td><code>/proc/interrupts</code> difference on 126–127 during the run, workqueue masks, isol.py samples, <code>ps -o time</code> of <code>kworker/127:*</code></td><td>On 126–127 only the timer tick and IPIs remain (NVMe completions only if the pass thread writes files), and 120–125 carry their own threads' interrupts. The per-CPU kworkers on 127 gain no CPU time.</td><td>""" + PARTQ + """ Idle host: zero interrupts on 126-127 in 10 s (05:46 and 17:56 UTC). The run-time difference comes from Jeremy's phx-isol.py samples of his blocks.</td></tr>
<tr><td>Thread placement</td><td>isol.py samples of govtest-2</td><td>Pass thread on 127, every other harness, python and bash thread on 120–125, nothing on 126.</td><td>""" + OPENQ + """ Pending: Jeremy's Friday block. His sampler phx-isol.py records thread placement without reading per-CPU files of 120–127.</td></tr>
<tr><td>Jeremy's job on the new setup</td><td>govtest-2 verdict, device <code>late_mean_s</code> against <code>lateness_band_s</code>, bind p99 and maximum, compared with churn-r1</td><td><code>void = false</code> (mean lateness below 2.5 µs), or the remaining gap is explicit and Jeremy has accepted it or taken the SDK-side change (D5).</td><td>""" + OPENQ + """ Pending: the churn run in the Friday block, then the first run with the 12× faster write on Phoenix. Expectation from his data: void until that write lands (Figure 8).</td></tr>
<tr><td>Quiet host</td><td><code>systemctl list-timers --all</code>, <code>who</code>, <code>pgrep -a netserver</code>, isol.py snapshot, sar history</td><td>No apt, fwupd, motd, man-db, update-notifier, tmpfiles or fstrim timer active. netserver gone. Nobody else logged in during the window (an idle arm console may remain).</td><td>""" + DONE + """ Timers off, netserver gone, only Jibin logged in (verified 05:48 UTC).</td></tr>
<tr><td>Ownership fixed</td><td><code>find … -user positron-perf | wc -l</code></td><td>0 files outside /home owned by positron-perf.</td><td>""" + DONE + """ 0 files (verified 05:26 UTC).</td></tr>
<tr><td>Hand-off note sent</td><td>The note itself</td><td>Jeremy has the configuration record, the launch-line change, the reservation rule and the limitation (no nohz_full).</td><td>""" + DONE + """ Sent 22 Oct; Jeremy replied the same day and accepted every default. Today's reply adds the contact and the answers to his questions.</td></tr>
</table>
<h3>Before each counted run (from Friday 23 October onward, two minutes, no root; Jeremy's script covers most of it)</h3>""")
A(code("""who; cat /proc/loadavg                                   # only your own session (an idle arm tty1 console may remain); load below 0.5
ls /tmp/positron-perf.RUNNING 2>/dev/null                # must not exist before you start; create it when you start, remove it at the end
cat /sys/devices/system/cpu/isolated                     # 126-127
cat /proc/cmdline | tr ' ' '\\n' | grep -E 'isolcpus|irqaffinity|cpufreq|rcu_normal'
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c   # 128 performance
cat /sys/kernel/rcu_normal                               # 1 (if kept)
systemctl list-timers --no-pager | grep -E 'apt|fwupd|motd|man-db|fstrim|update-notifier|tmpfiles' || echo "no risky timers active"
ps -eo user,pcpu,psr,comm --sort=-pcpu | head -5         # nothing of another user above 5% CPU
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs   # record once; read again after the run; never during it
python3 ~/positron/runs/isol.py snap ~/positron/runs/pre-$(date -u +%Y%m%dT%H%MZ).json
# do not run snap, unshare, podman or systemd-run during a counted run; they start services or send IPIs to busy CPUs"""))
A("</section>")

# ---- section 8: evidence and limits
A("""<section id="s8"><h2>8. Evidence and limits</h2>
<ul>
<li>All host facts come from read-only commands run as <code>positron-perf</code>. The first inspection ran on 21 October 2026 between 23:42 and 23:57 UTC with follow-ups until 22 October 00:17 UTC. The verification pass used 20 agents: three paraphrases and a judge, five analysts, ten adversarial verifiers and one completeness critic. They re-ran read-only checks between 00:38 and 01:24 UTC and checked the kernel claims against the 7.1 and 6.8 sources and the systemd 255 source. Jibin's session re-ran the hiccup probe at 01:57 UTC. The scripts and complete outputs are in the folder <code>phoenix-crb-evidence-2026-10-21/</code> next to this file. It holds <code>phoenix-crb-inspection.txt</code>, <code>-followup.txt</code>, <code>-round3.txt</code> to <code>-round6.txt</code>, the scripts that produced them, and the figure generator. Its subfolder <code>verification-2026-10-22/</code> holds the verifiers' raw outputs, the hiccup re-run, and the digests of the verdicts, corrections and the critic's findings.</li>
<li>Load placed on the host by this analysis:<ul><li>a 3 s pinned spin on CPU 121 (clock) and 5 s pinned spins on CPUs 121 and 125 (tick count)</li><li>three 4 s pinned spins on CPU 121 and one 1 s spin on CPU 124 (the verifiers' IPI and ramp tests)</li><li>hiccup runs of 3.8 s on CPUs 124, 125 and 126</li><li>30 reads of CPPC counters (60 IPIs to the CPUs read)</li><li>three unprivileged <code>unshare -Urm true</code> calls, three <code>timedatectl</code> calls (which started systemd-timedated) and two <code>snap list</code> calls (which started snapd for a few seconds)</li></ul>No file was written on the host, no sudo was used, and no setting was changed by these checks. The as-built verification of 22 October (05:44–05:52 UTC) added five ssh logins as positron-perf and three interrupt-count windows (10 s, 60 s and 25 s).</li>
<li>The one earlier document, <code>jeremy-tasks.html</code> (inspection 21:08 UTC), did not see the second kernel, the staged workspace, the login sources, the clock measurement or the SDK tool rules. This plan supersedes its action plan. The first draft of this plan (21 October 17:30 PDT) attributed the lateness to the clock (hypothesis H1) and the void to the maximum lateness. Both were corrected by the verification pass and by the hiccup re-run.</li>
<li>Jeremy's frequency samples (Figure 1) were taken by his probes. Their sampling interval and CPU are not recorded in the files. The clock samples of Figure 2 are governor requests, not delivered clocks.</li>
<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks ran from <code>positron-perf</code> after each of Jibin's changes. The post-reboot results are saved as <code>verification-2026-10-22/postreboot-0545.txt</code> and <code>ipi-attribution-0552.txt</code>. A further read-only check at 17:56 UTC, after Jeremy's replies, is saved as <code>state-1756.txt</code> (zero interrupts on 126–127 in 10 s, Jeremy's build log ending in <code>BUILD-DONE rc=0</code>, no RUNNING file, no positron-perf process). Jeremy's two replies are quoted in section 4 and kept in <code>requests.txt</code> as messages 4 and 5.</li>
</ul>
<h3>Insufficient data</h3>
<ul>
<li>When Arm grants the GitHub access that Dan requested on 22 October, and whether the tree at <code>4dbc8bb88858</code> with its config is in it (A6).</li>
<li>Whether the 12× faster logits-row write brings the device's mean lateness under 2.5 µs on Phoenix (the governor alone cannot, Figure 8). Measurement: the first churn run with that write on Phoenix. Whether commit <code>fa7f715f</code>, built on the host on 22 October, carries it is not stated.</li>
<li>Clock stability over a full run under the performance governor. Measurement: Jeremy's counter pairs on 126 and 127 around the Friday block.</li>
<li>The meaning of EFI boot entry 0010, and whether the second disk holds another operating system (A3, not blocking: the reboot of 22 October came up on the vendor kernel as before).</li>
<li>What “the twins” are (Jeremy's term for churn runs without a device thread), and whether the Friday block's <code>timed_compile.py</code> steps are the test-3 timed compile. Source: Jeremy.</li>
<li>Whether booting the stock 6.8.0-147 kernel on this board works. Not recommended to test before the demo.</li>
<li>Hypothesis, not measured: transparent huge pages are set to “always” with a background collapse scan every 10 s, which can stall a faulting harness thread for hundreds of microseconds on a housekeeping CPU. Measurement: the <code>thp_collapse_alloc</code> counter in <code>/proc/vmstat</code> before and after a run. Mitigation on Jeremy's side: <code>prctl(PR_SET_THP_DISABLE)</code> in the harness, no root needed.</li>
</ul>
</section>""")

A("""<footer>Prepared for Jibin on 21 October 2026, revised 22 October 02:40, 05:05, 06:00 (as-built), 06:20 and about 18:30 UTC (Jeremy's replies, the revised plan, the table of contents). Standalone HTML, light theme, inline SVG figures. Figures follow the dataviz palette (categorical blue/orange, ordinal blue ramp validated for light surfaces). No message is sent by this document. The reply and the note in section 4 are for Jibin to send.</footer>""")

import re
def add_toc(body):
    """Give every h3 an id, collect the h2 and h3 titles, and put the table of contents at the placeholder."""
    items, state = [], {"sec": None, "n3": 0}
    strip = lambda t: re.sub(r"<[^>]+>", "", t)
    def sub(m):
        if m.group(1):
            state["sec"], state["n3"] = m.group(1), 0
            return m.group(0)
        if m.group(2) is not None:
            items.append((2, state["sec"], strip(m.group(2))))
            return m.group(0)
        state["n3"] += 1
        hid = f'{state["sec"]}-{state["n3"]}'
        items.append((3, hid, strip(m.group(3))))
        return f'<h3 id="{hid}">{m.group(3)}</h3>'
    body = re.sub(r'<section id="([^"]+)"[^>]*>|<h2>(.*?)</h2>|<h3>(.*?)</h3>', sub, body, flags=re.S)
    out = ['<nav class="contents" aria-label="Table of contents"><h2>Contents</h2><ol>', '<li><a href="#short">Short version</a></li>']
    open2 = open3 = False
    for lvl, hid, title in items:
        if lvl == 2:
            if open3: out.append("</ol>"); open3 = False
            if open2: out.append("</li>")
            out.append(f'<li><a href="#{hid}">{title}</a>'); open2 = True
        else:
            if not open3: out.append("<ol>"); open3 = True
            out.append(f'<li><a href="#{hid}">{title}</a></li>')
    if open3: out.append("</ol>")
    if open2: out.append("</li>")
    out.append("</ol></nav>")
    assert body.count("<!--TOC-->") == 1
    return body.replace("<!--TOC-->", "".join(out))

body = add_toc("\n".join(parts))
doc = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Jeremy's phoenix-crb tasks: plan</title><style>" + CSS + "</style></head><body><main>" + body + "</main></body></html>\n"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print("wrote", OUT, len(doc), "bytes")
