#!/usr/bin/env python3
"""Build jeremy-tasks-plan.html (single-theme light, self-contained) from the evidence and the inline SVG figures."""
import html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = json.load(open(os.path.join(HERE, "..", "figs", "figs.json"), encoding="utf-8"))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/rampup/jeremy-tasks-plan.html"
REQ = open(os.path.join(HERE, "requests.txt"), encoding="utf-8").read()

def q(name):
    """Verbatim quote of one message from requests.txt."""
    marker = {"original": "=== MESSAGE 1", "deadline": "=== MESSAGE 2", "latest": "=== MESSAGE 3"}[name]
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
.chip.reboot{background:#fdf3ee;color:#9a3d12;border-color:#f5c4ad}.chip.kernel{background:#fdf0f0;color:#9c1f1f;border-color:#f0b8b8}
.chip.jeremy{background:#fff6dc;color:#6b4e00;border-color:#f4dc8c}.chip.gray{background:#f3f3f0;color:var(--sec);border-color:var(--grid)}
ul,ol{padding-left:22px;margin:6px 0}li{margin:3px 0}
.phase{background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:12px 16px;margin:14px 0}
.phase h3{margin:0 0 4px}.phase .meta{color:var(--sec);font-size:13px;margin-bottom:8px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}
.stat{flex:1 1 230px;background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:10px 16px;min-width:200px}
.stat .v{font-size:26px;font-weight:600;line-height:1.1}.stat .l{color:var(--sec);font-size:12.5px}
footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--grid);margin-top:40px;padding-top:12px}
@media print{body{background:#fff}main{max-width:none}}
"""

def chip(kind, label):
    return f'<span class="chip {kind}">{html.escape(label)}</span>'

DONE = chip("done", "✔ done"); LIVE = chip("live", "● root, no reboot"); REBOOT = chip("reboot", "↻ root + reboot")
KERNEL = chip("kernel", "✖ needs another kernel"); UNK = chip("gray", "? unknown")
NA = chip("gray", "– not needed"); PART = chip("gray", "◑ partly"); NOTDONE = chip("gray", "○ not done")

# ----------------------------------------------------------------------------------------------- content
parts = []
A = parts.append

A("""<header class="top">
<h1>Jeremy's requests for phoenix-crb: what they mean, where they stand, and the plan</h1>
<p class="sub">Written for Jibin on 21 October 2026 and revised the same evening at 19:40 PDT (22 October 02:40 UTC) after a verification pass by 20 independent agents. Host phoenix-crb (192.168.2.45, Linux hostname <code>ubuntu</code>) was checked read-only as <code>positron-perf</code> between 21 October 23:42 UTC and 22 October 02:00 UTC. No setting, file or service on the host was changed by this check. The three messages are quoted verbatim in section 1.</p>
<nav class="toc"><a href="#short">Short version</a><a href="#words">Words used here</a><a href="#s1">1 Requests, quoted</a><a href="#s2">2 In plain English</a><a href="#s3">3 Where each ask stands</a><a href="#s4">4 Do we need Jeremy?</a><a href="#s5">5 Host check findings</a><a href="#s6">6 Action plan</a><a href="#s7">7 Acceptance checks</a><a href="#s8">8 Evidence and limits</a></nav>
</header>""")

A("""<section id="short" class="short">
<p><strong>Short version.</strong> Jeremy's account, toolchain and disk are ready on phoenix-crb, and the first latency job run there (21 October) was voided by the simulated device thread's mean lateness, 6.2 µs against a 2.5 µs limit.</p>
<p>The host side can set the performance governor tonight without a reboot and isolate cores with one reboot on Thursday, but nohz_full needs a rebuilt kernel from Arm, and the host's clock alone does not explain the lateness (measured), so Monday's counted runs also depend on an SDK-side change: pinning that thread.</p>
<p>Six questions for Jeremy and eleven for the administrator are listed with defaults, so the host work can start now.</p>
</section>
<div class="danger"><strong>Security finding, to fix before any root use of these tools.</strong> 347 files installed by the vendor package <code>linux-tools</code> are owned by the test account <code>positron-perf</code>, among them <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code> and the <code>cpupower.service</code> unit file. The test account could replace a program that root later runs. This plan sets the governor through sysfs only and never runs <code>sudo cpupower</code> or <code>sudo perf</code>. Step P1d changes the ownership to root.</div>
<div class="note">Changes on the host during this analysis: a second administrator account, <code>jhan</code> (user id 1002, group sudo), was created on 22 October at 01:19 UTC from Jibin's workstation, and it logged in from the workstation and from alpha. The isolation, governor, timer and boot settings were unchanged at 01:55 UTC. The plan assumes <code>jhan</code> is Jibin's own account (question A1).</div>""")

# ---- glossary
terms = [
    ("phoenix-crb", "The Arm server at 192.168.2.45. Its firmware names it “Phoenix Reference Server”, maker Arm Limited, build stage EVT0 (first engineering validation build), BIOS “AGI-CPU-CRB-v0.7.2”. CRB is read as “customer reference board” from that BIOS string."),
    ("Jibin", "The reader of this plan (jhan@positron.ai). Jibin's workstation is 192.168.2.136 (claude-agentsrv) and runs in Pacific time (PDT, UTC−7, until 1 November, then PST, UTC−8)."),
    ("Jeremy", "The SDK-side requester. His git commit on the host carries the time zone −0400 (US Eastern, EDT, until 1 November, then EST, UTC−5)."),
    ("SDK", "Software development kit: Positron's runtime, compiler and tests. The copy on the host is the repository <code>~/positron/src/phoenix-int</code>."),
    ("positron-perf", "The unprivileged test account (user id 1001) that Jeremy asked for. It has no usable sudo."),
    ("arm (account)", "The administrator account on phoenix-crb (user id 1000, group sudo). Root steps below are run from it or from <code>jhan</code>."),
    ("jhan (account)", "A second administrator account (user id 1002, group sudo) created on phoenix-crb on 22 October 01:19 UTC from Jibin's workstation while this analysis ran."),
    ("alpha", "The LAN host 192.168.1.200 (name alpha.positron.internal). It staged the SDK workspace on 21 October, held long <code>arm</code> sessions on 20 and 21 October, and logged in as <code>jhan</code> minutes after that account was created. It is used from Jibin's side. Whether the staging was done by Jibin's side on Jeremy's behalf or by Jeremy is question A2."),
    ("sw-dev-01", "The SDK team's development host. Its LAN address is 192.168.2.39 (sw-dev-01.positron.internal) and its Tailscale address 100.124.2.53. It logged in to phoenix-crb as positron-perf four times on 21 October."),
    ("Asimov cards", "Positron's accelerator boards. None is attached to phoenix-crb, and Jeremy's tests do not need one."),
    ("LSF", "A batch job scheduler whose shared worker hosts Jeremy calls too noisy for timing. phoenix-crb runs no LSF."),
    ("pass thread", "The one runtime thread, named <code>positron-pass</code>, that plans and issues each forward pass (one model step). The SDK pins it to the CPU given as <code>pass_thread_core</code>."),
    ("fake device / null_timing", "The SDK's simulated device backend. One “fake device” thread sleeps until 100 µs before each pass's retirement time, then spins and posts the completion. Its lateness is measured against a band. The SDK does not pin this thread."),
    ("lateness band / void", "The allowed mean lateness of the fake device: 0.2% of the shortest pass period, 2.5 µs in the run seen here. A record whose mean lateness passes the band is “void”, and the latency judge reports INFRA (no measurement). The rule uses the mean, not the maximum."),
    ("latency judge / churn label", "The SDK tools (<code>tools/conformance/churn.py</code> and <code>latency_judge.py</code>) that run the per-user latency gate named <code>per-user-latency.qwen3_5_0_8b.P-TP1</code> and judge the record. They require only that the pass thread is pinned. They record whether the pass core is in isolcpus but do not require it."),
    ("perf lane", "A different SDK tool (<code>tools/perf/perf_lane.py</code>, <code>records.py</code>) for the TPS gate's host timing and the timed compile. It refuses any host that has no online core in both isolcpus and nohz_full. TPS means tokens per second."),
    ("D21, U1 p99, U5 waking, D17 lane", "SDK names used in its design documents: D21 is the set of per-user latency targets, U1 p99 the 99th-percentile per-user latency target, U5 waking the consumer-wake target, and the D17 lane the tool lane that measures them. The design says U1 p99 and U5 waking “count only from an isolated host”."),
    ("counted run", "A run whose numbers go into the 5 November demo, as opposed to a trial run."),
    ("isolcpus", "A kernel boot argument. With the <code>domain</code> flag the listed CPUs leave the scheduler's load balancing: a thread placed there stays there, and no other thread is moved there automatically. With <code>managed_irq</code> the kernel keeps kernel-managed device interrupts off them when the queue has other CPUs to use. It takes effect only at boot and cannot be undone without another reboot."),
    ("nohz_full", "A kernel feature (build option CONFIG_NO_HZ_FULL) that stops the periodic scheduler tick on a CPU running a single task. The running kernel was built without it."),
    ("rcu_nocbs", "A kernel boot argument that moves RCU callback work (deferred kernel clean-up, RCU = read-copy-update) off the listed CPUs. It needs the build option RCU_NOCB_CPU, which a NO_HZ_FULL kernel includes."),
    ("expedited RCU grace period", "A fast form of RCU synchronisation that sends a function-call IPI to every busy CPU on the host. A sandboxed service start or a namespace teardown triggers one. The kernel setting <code>rcu_normal=1</code> turns them into normal, slower grace periods without IPIs."),
    ("tick / HZ", "The periodic scheduler interrupt. The running kernel has HZ = 250, one tick every 4 ms on a busy CPU."),
    ("IRQ / managed IRQ", "A hardware interrupt request. A managed IRQ is one whose CPU assignment the kernel controls (here the NVMe disk queues, one queue per CPU). It cannot be moved by writing to /proc/irq."),
    ("IPI", "Inter-processor interrupt: one CPU asking another to do something (for example a function call or a reschedule). No isolation setting removes all of them."),
    ("cpufreq governor", "The kernel policy that picks a CPU's clock. <code>schedutil</code> (today) follows CPU utilization. <code>performance</code> always requests the highest clock."),
    ("boost", "A clock above the nominal maximum. phoenix-crb's firmware exposes no boost range: the highest level equals the nominal 2.8 GHz, so there is nothing to disable."),
    ("CPPC / feedback_ctrs / AMU", "Collaborative Processor Performance Control, the firmware interface behind the <code>cppc_cpufreq</code> driver. Its feedback counters (read from the CPU's Activity Monitors Unit, AMU) are readable by any user and give the delivered clock: delivered performance = 50 × Δdelivered / Δreference, and one performance unit is 20 MHz on this host. Each read sends two IPIs to the CPU being read."),
    ("scaling_cur_freq", "The sysfs file that reports the governor's last clock request for a CPU, not the delivered clock. Reading it costs no IPI."),
    ("timer slack", "The kernel's allowed lateness for a sleeping thread's wake-up, 50 µs by default. A thread can lower its own slack with <code>prctl(PR_SET_TIMERSLACK)</code> without privilege. The SDK's waker thread does this (1 µs). The fake device thread does not."),
    ("vendor kernel", "The running kernel <code>7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858</code>, built on 16 September 2026 by an Arm engineer (package maintainer address at arm.com) with workarounds for this A0 silicon, installed from a local package on 28 September."),
    ("stock kernel", "Ubuntu's <code>6.8.0-147-generic</code>, installed automatically by unattended-upgrades on 15 October 2026 but never booted on this board as far as the host records show."),
    ("linux-tools (package)", "The vendor package that ships <code>perf</code>, <code>cpupower</code> and <code>bpftool</code> for the running kernel. Its files are owned by user id 1001, which on this host is positron-perf."),
    ("GRUB drop-in", "A file under <code>/etc/default/grub.d/</code> that adds boot settings. <code>update-grub</code> then regenerates the boot menu."),
    ("cpuset isolated partition", "A cgroup v2 setting (cgroup v2 is the kernel's resource-control tree) that removes CPUs from scheduler load balancing while the system runs. It needs root but no reboot. It does not stop the tick and does not show in <code>/sys/devices/system/cpu/isolated</code>."),
    ("unattended-upgrades / apt timers", "Ubuntu's automatic package updater and the systemd timers that drive it. The timers are active on the host and installed two kernels in October."),
    ("hiccup, isol.py", "Scratch tools left in <code>~/positron/runs/</code>: a probe of the fake device's wait pattern (hiccup), and a snapshot/sampler of isolation, governors and per-CPU thread placement (isol.py). This check re-ran hiccup (section 5.3)."),
    ("churn-r1, govtest-1, govtest-2", "Run tags. churn-r1 is the run of 21 October. govtest-1 and govtest-2 are the proposed re-runs after the governor change and after the reboot."),
    ("launcher", "The shell and Python processes that start Jeremy's job (<code>ev3-churn-job.sh</code>, <code>churn.py</code>, the judge). Where they first land decides where their threads stay once cores are isolated."),
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
<li>He observed that the governor is schedutil today and that no cores are isolated. Both observations match the host.</li>
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
    ("Account positron-perf with SSH key login", DONE, "Account exists (uid 1001). Three keys installed: Jibin's workstation key, <code>jeremy@sw-dev-01</code>, <code>jeremy@DESKTOP-V2B1166</code>. Used from alpha (about 50 sessions, 17:07–18:58 UTC 21 Oct) and from sw-dev-01 (4 sessions).", "no", "no", "no", "nice: which key he uses (the laptop key is untested)"),
    ("Reachable from Jeremy's laptop or via sw-dev-01", DONE, "sw-dev-01 (192.168.2.39 on the LAN) logged in as positron-perf four times on 21 Oct. The laptop path is untested.", "no", "no", "no", "nice"),
    ("clang 18, CMake ≥ 3.25, Ninja, Python ≥ 3.11 + headers", DONE, "User-level toolchain under <code>~/positron/toolchains/sdk-ci-2026-10</code>: clang 18.1.8, CMake 3.31.6, Ninja 1.13.2, gcc 13.3.0, plus Python 3.12.3 with headers from Ubuntu. No sudo used. For the perf lane the toolchain is missing from the account's non-interactive PATH (user-level fix).", "no", "no", "no", "nice (perf lane only)"),
    ("About 100 GB of disk", DONE, "1.7 TB free on the root filesystem, which holds /home. No quota. The workspace uses 7.7 GB. One churn run writes about 271 MB.", "no", "no", "no", "no"),
    ("No sudo for the account", DONE, "No usable sudo: password locked, no password-free sudo rule. A 49-byte file <code>/etc/sudoers.d/positron-perf-setup</code> exists (created 21 Oct 05:12 UTC) and grants nothing usable today. The administrator should read it (A4).", "no", "no", "no", "no"),
    ("No outbound network needed", NA, "The host has outbound network and the staging used it. Nothing to do.", "no", "no", "no", "nice: keep it"),
    ("Fixed clock: no boost", DONE, "No boost range exists. Firmware highest performance level 140 = nominal level 140 = 2.8 GHz.", "no", "no", "no", "no"),
    ("Fixed clock: performance governor", LIVE, "All 128 policies run schedutil. <code>performance</code> is available. Each CPU is its own policy. A live write by root through sysfs changes it (never through <code>sudo cpupower</code>, see P1d). A boot argument and a boot-time unit make it survive the reboot.", "yes", "no", "no", "nice: all 128 CPUs or only 120–127 (default: all)"),
    ("Isolated cores (isolcpus) with IRQs kept off", REBOOT, "Nothing isolated today. isolcpus works after one reboot. “IRQs kept off” is only partly achievable: the timer tick and IPIs stay, the per-CPU NVMe queue interrupts cannot be moved and fire only for disk I/O issued from that CPU, and default device interrupts already sit on CPU 0.", "yes", "yes", "no", "yes: D3 (which CPUs, and the job's launch command)"),
    ("nohz_full on the isolated cores", KERNEL, "Running kernel: <code># CONFIG_NO_HZ_FULL is not set</code>. A busy CPU takes the 250 Hz tick (1,261 timer interrupts in 5 s measured). The installed stock 6.8 kernel has the feature but has never booted on this board.", "yes", "yes", "yes", "yes: D1, D2"),
    ("rcu_nocbs on the isolated cores", KERNEL, "Not available on the running kernel (no RCU_NOCB_CPU). A kernel built with NO_HZ_FULL brings it, and nohz_full CPUs get it automatically.", "yes", "yes", "yes", "no (follows D1)"),
    ("Nothing else running during timed runs, nightly window", PART, "The host is near idle. 17 systemd timers exist (14 active) plus a benchmark server. apt-daily-upgrade fires next on Thu 22 Oct 06:28 UTC (Wed 23:28 PDT) and can install packages. Root can pause them tonight (P1b).", "yes", "no", "no", "yes: D4 (windows in UTC)"),
    ("One job at a time", PART, "No host mechanism. The perf lane holds a lock. The churn script does not. A marker-file rule is proposed in D4.", "no", "no", "no", "yes: D4 (reservation rule)"),
    ("Account and one isolated core by Friday 23 Oct", REBOOT, "Achievable with the current kernel, without nohz_full: governor tonight, isolcpus reboot on Thursday 22 Oct. “Friday” in Jeremy's time zone ends Fri 23 Oct 21:00 UTC (14:00 PDT).", "yes", "yes", "no", "yes: D1"),
    ("Counted runs from Monday 26 Oct", UNK, "The host setup is achievable. Validity is unproven: the first run was voided by the device thread's mean lateness, and the host clock alone does not explain it (measured). A pinned device thread (D5) or a re-run that proves otherwise is needed.", "yes", "yes", "depends on D2", "yes: D2, D5"),
    ("Test 2: sampling unit tests on Arm", UNK, "No test run is recorded. The build job built three targets only, and no ctest or pytest log exists under <code>~/positron</code>.", "no", "no", "no", "nice: Q9"),
    ("Test 3: timed compile", NOTDONE, "The <code>compile-0.8b</code> gate runs on the perf lane, which the SDK README says “does not run it yet”. No compile wall time is recorded.", "no", "no", "depends on D2", "nice: Q9"),
]
A("""<section id="s3"><h2>3. Where each ask stands today</h2>
<p>Status chips: <span class="chip done">✔ done</span> <span class="chip live">● root, no reboot</span> <span class="chip reboot">↻ root + reboot</span> <span class="chip kernel">✖ needs another kernel</span> <span class="chip gray">◑ partly</span> <span class="chip gray">○ not done</span> <span class="chip gray">? unknown</span> <span class="chip gray">– not needed</span>. Root means the administrator accounts <code>arm</code> or <code>jhan</code>.</p>
<table><tr><th style="width:21%">Ask</th><th style="width:12%">Status</th><th>What the host shows</th><th>Root</th><th>Reboot</th><th>Other kernel</th><th>Jeremy's input</th></tr>""")
for ask, st, ev, r, rb, k, j in rows:
    A(f"<tr><td>{ask}</td><td>{st}</td><td>{ev}</td><td>{r}</td><td>{rb}</td><td>{k}</td><td>{j}</td></tr>")
A("</table></section>")

# ---- section 4: decisions
A("""<section id="s4"><h2>4. Do we need input from Jeremy to proceed?</h2>
<p><strong>Not to start.</strong> The governor change, the pausing of timers, the ownership fix, the GRUB change and Thursday's reboot can all be done from an administrator account without Jeremy. His input is needed before Monday's counted runs, for six decisions. Each has a default that applies if he does not answer by Thursday 22 October 14:00 UTC (07:00 PDT, 10:00 EDT). The reboot slot proposed below is one hour later.</p>
<table><tr><th style="width:4%">#</th><th style="width:24%">Decision</th><th>Why it matters</th><th style="width:26%">Default if no answer</th></tr>
<tr><td>D1</td><td>Which message is newer, does Friday stand, and is a Friday setup without nohz_full and rcu_nocbs acceptable?</td><td>Message 2 asks for Friday, message 3 says “whenever you have a moment”, and their order is uncertain. The running kernel cannot provide nohz_full. A busy isolated CPU keeps one timer interrupt every 4 ms (1 µs to 2 µs each, est.) until a rebuilt kernel is installed. Message 2 allows “the rest of the list” to follow later, but it named the reboot as the example, not the missing kernel feature.</td><td>Friday stands. Proceed on the current kernel. Treat nohz_full as a parallel kernel task (plan step P4).</td></tr>
<tr><td>D2</td><td>Which SDK path produces the counted numbers: the latency judge (churn label) or the perf lane?</td><td>The latency judge runs on the current kernel and needs only a pinned pass thread. The perf lane refuses a host with no core in both isolcpus and nohz_full, which puts the kernel rebuild on the critical path before 5 November. The SDK README says the per-user figures “count only from the perf host”, and the design says U1 p99 and U5 waking count only from an isolated host. That is policy, not code, so Jeremy must say which host state makes a judge-path run count.</td><td>Assume the latency judge. Keep the kernel task running in parallel.</td></tr>
<tr><td>D3</td><td>Which CPUs to isolate, and the matching change to the job's launch command.</td><td>On isolcpus CPUs the scheduler does no load balancing. Jeremy's job pins the pass thread to CPU 127 and lets its other threads float over 120–126, where they moved across all seven CPUs in the first run. If all eight are isolated and the threads are not pinned one by one, they stay wherever they first land. With only 126–127 isolated and the job's <code>taskset -c 120-127</code> unchanged, the launcher's shell and Python can land on an isolated CPU and never leave (the kernel places them on any CPU of the mask). The choice is irreversible without another reboot.</td><td>Isolate 126–127. The job runs the label with the CPU set 120-125,127 and starts it as <code>taskset -c 120-125 taskset -c 120-125,127 …</code>. CPU 126 stays free for a pinned fake-device thread. One-core variant: isolate 127 only.</td></tr>
<tr><td>D4</td><td>Run windows in UTC, the reservation rule, and the clock pass rule.</td><td>The host runs UTC. US clocks change on Sunday 1 November (Jeremy at 06:00 UTC, Jibin at 09:00 UTC), inside the run period. No host mechanism serialises jobs, and Jibin's own logins count. The acceptance rule for “fixed clock” is not stated anywhere.</td><td>Windows Mon–Fri 13:00–21:00 UTC. Jeremy's job writes <code>/tmp/positron-perf.RUNNING</code> (start, end, pid, tag) and removes it at the end, counted windows are announced 2 h ahead, one job at a time, and nobody touches the host while the marker exists. Clock rule: delivered clock on the pass core ≥ 2,772 MHz (99% of 2,800 MHz) from one feedback-counter pair read before and after the run, no polling during it.</td></tr>
<tr><td>D5</td><td>Will Jeremy pin the fake device thread to its own CPU (126) and give it a 1 µs timer slack before Monday? Has any churn run ever recorded <code>void = false</code>? Is the band itself the item to change?</td><td>The first run was voided by that thread's mean lateness (6.2 µs against 2.5 µs). The SDK pins the pass thread and keeps workers off it but sets no affinity for the device thread, which shared CPUs 120–126 with the other threads at 1.6 GHz. The host clock alone does not reproduce the lateness (section 5.3). Its placement is harness code on Jeremy's side, and it decides whether runs count.</td><td>Jeremy decides. CPU 126 is kept free for it. The governor-only re-run (govtest-1) shows how much the clock contributes.</td></tr>
<tr><td>D6</td><td>May Jibin re-run <code>~/positron/runs/ev3-churn-job.sh</code> in the positron-perf account (govtest-1 after the governor change, govtest-2 after the reboot, about 3 min each)?</td><td>The re-runs give before/after evidence for the device's mean lateness. They run inside Jeremy's account and workspace. If the staging and scripts were made by Jibin's side on Jeremy's behalf (question A2), no permission is needed.</td><td>No, unless A2 says the scripts are Jibin's side's. Validation then uses Jibin's own probes (hiccup and feedback counters).</td></tr>
</table>
<p><strong>Useful but not blocking</strong> (asked at the end of the message):</p>
<ul>
<li>Q7: performance governor on all 128 CPUs (default) or on 120–127 only. The churn job's threads run on 120–126, the perf lane's on 0–119, so host-wide fits both.</li>
<li>Q8: whether the clock pass rule in D4 is acceptable as the definition of “fixed clock”.</li>
<li>Q9: status of the sampling unit tests and the timed compile, and whether they need a slot.</li>
<li>Q10: if the perf lane is the path, three user-level gaps on the host need Jeremy's side: clang and ninja are not on the account's non-interactive PATH and <code>perf_job.sh</code> does not source the toolchain script, the directories <code>~/positron/fetchcontent</code>, <code>~/positron/artifacts</code> and <code>~/positron/work/sdk-v2</code> do not exist, and the lane's ssh alias <code>phoenix-perf</code> must exist on his operator machine. Also whether smartd, rsyslog and sysstat may stay (the spec says “no persistent service installed” on the perf host).</li>
<li>Q11: which login paths and keys he uses (sw-dev-01 and alpha were seen, the laptop key was not), and whether to keep outbound internet (default: keep).</li>
<li>Q12: the hiccup outputs from 18:40 UTC on 21 Oct, whether the 1,300 to 7,700 interrupts per second per worker CPU during churn-r1 (the threads' own timed sleeps) are intended, and whether the record writer (three JSON files of about 86 MB) stays off the pass core.</li>
</ul>
<h3>Questions for the administrator (Jibin), none of them blocking the host work</h3>
<table><tr><th style="width:4%">#</th><th style="width:30%">Question</th><th>Why</th></tr>
<tr><td>A1</td><td>Is <code>jhan</code> (uid 1002, sudo, created 22 Oct 01:19 UTC from 192.168.2.136) your account, and is <code>arm</code> yours too?</td><td>The hand-off must record who holds root and which account made Thursday's changes.</td></tr>
<tr><td>A2</td><td>Is alpha (192.168.1.200) your machine? Were the staging sessions from alpha (17:07–18:58 UTC 21 Oct), the toolchain README (“approved by Jeremy that day”) and the churn-r1 run done by your side on Jeremy's behalf?</td><td>Decides D6 (re-runs need no permission) and who else must know the reservation rule. A further admin address, 192.168.2.213, used <code>arm</code> on 29 Sep.</td></tr>
<tr><td>A3</td><td>Is there out-of-band access (BMC address and credentials, or physical access) before the reboot? What is EFI boot entry 0010 (first in BootOrder while BootCurrent is 0001)? Is the second disk nvme1n1 (200 MB vfat plus 1.7 TB xfs, Boot0002) another operating system?</td><td>The three planned boot arguments cannot fail the boot (bad values are warned about and dropped), but any other boot fault needs console access. An ASPEED BMC chip is present, but no <code>/dev/ipmi*</code> device exists and the GRUB menu is on the EFI console.</td></tr>
<tr><td>A4</td><td>What does <code>/etc/sudoers.d/positron-perf-setup</code> (49 bytes, 21 Oct 05:12 UTC) grant? <code>sudo cat</code> it and run <code>sudo visudo -cf</code> on it.</td><td>It grants nothing usable today. If it was meant to give cpupower or governor control, it must not reference <code>/usr/bin/cpupower</code> while that file is owned by positron-perf.</td></tr>
<tr><td>A5</td><td>Fix the <code>linux-tools</code> ownership (step P1d) before any root use of perf, cpupower or bpftool.</td><td>Security: 347 files under /usr, /etc and /lib are owned by uid 1001.</td></tr>
<tr><td>A6</td><td>Is there a channel to Arm's software validation kit (SVK) team to ask for the kernel tree at <code>4dbc8bb88858</code> with its config, or for a build with <code>CONFIG_NO_HZ_FULL=y</code>? What date is realistic?</td><td>The package maintainer is an arm.com address (<code>avadnaik@2paltra-216.5g.ast.arm.com</code>). The source is not on the host. Secure Boot is off, so a local build needs no signing.</td></tr>
<tr><td>A7</td><td>Reboot slot Thursday 22 Oct 15:00 UTC (08:00 PDT, 11:00 EDT), 10 to 15 minutes: agreed? The idle <code>arm</code> console session on tty1 (since 20 Oct 19:31 UTC) ends with the reboot.</td><td>Fallback slot: Friday 13:00 UTC. Who announces it to alpha's users and to Jeremy?</td></tr>
<tr><td>A8</td><td>Three optional live settings: (1) <code>rcu_normal=1</code> (removes function-call IPIs to the pass core from service starts and namespace teardowns, makes expedited grace periods normal ones, milliseconds slower for mounts), (2) <code>CPUAffinity=0-119</code> in <code>/etc/systemd/system.conf</code> (keeps every service off 120–127 now, needs <code>daemon-reexec</code>), (3) keep <code>sysstat-collect.timer</code> for 10-minute sar history as quiet-window evidence, or disable it.</td><td>Each is reversible. The plan includes (1) and keeps (3) by default.</td></tr>
<tr><td>A9</td><td>Hardening, not a demo blocker: sshd allows root password login (<code>PermitRootLogin yes</code>, <code>PasswordAuthentication yes</code> in the main file and three drop-ins). Should the kernel meta-packages be held (<code>apt-mark hold linux-image-virtual linux-headers-virtual linux-virtual</code>) so apt never installs kernels again?</td><td>Root password login is a second privileged path that the reservation rule cannot see.</td></tr>
<tr><td>A10</td><td>Close the “which key did Jeremy use” question from the system journal: <code>sudo journalctl _COMM=sshd -g "Accepted publickey for positron-perf" --since 2026-10-21 -o short-iso</code>.</td><td>The account's own journal does not contain the “Accepted” lines.</td></tr>
<tr><td>A11</td><td>Do you accept that the Friday promise excludes nohz_full and rcu_nocbs, and that Monday's runs may still be void for SDK-side reasons, so that the message to Jeremy says so explicitly?</td><td>The message below says both.</td></tr>
</table>
<h3>Draft message to Jeremy (send tonight)</h3>
<blockquote><pre>Jeremy, status on phoenix-crb (the Phoenix CRB, 192.168.2.45), 21 Oct evening:

1. Your account, keys, toolchain and disk are in place. The churn-r1 run from today is on the host.
2. The performance governor needs root but no reboot. I plan to set it on all 128 CPUs tonight.
3. isolcpus needs one reboot of the current kernel. Proposed slot: Thu 22 Oct 15:00 UTC (11:00 EDT), about
   15 minutes down. Default (non-managed) interrupts are kept off cores 120-127. The per-CPU NVMe completion
   interrupts stay and fire only for disk I/O issued from those cores.
4. nohz_full and rcu_nocbs are not possible on the running kernel (built without CONFIG_NO_HZ_FULL) and are
   not expected by Friday. They need a rebuilt kernel, which I am requesting from Arm. Until then a busy
   isolated core keeps the 250 Hz timer tick (one interrupt every 4 ms, about 1-2 us each).
5. churn-r1 was voided because the fake device's MEAN lateness (6.25 us) exceeded the 2.5 us band, not by
   missing isolation. The host clock alone does not explain it: your hiccup probe in sleep mode on an idle
   core under schedutil gives mean lateness 0.02 us (0 of 2000 cycles over 2.5 us). During churn-r1 the device
   thread shared cores 120-126 with the other threads, those cores sat at 1.6 GHz, and they took 1,300-7,700
   interrupts/s (the threads' own timed sleeps).
6. The host has outbound internet, and your pip install used it (wheels downloaded on the host). I will keep it.

Questions (one line each is enough; defaults apply if I hear nothing by Thu 22 Oct 10:00 EDT):
Q1 Which of your notes is newest? Does Friday 23 Oct still stand, and is a Friday host WITHOUT nohz_full and
   rcu_nocbs acceptable for Monday's counted runs? Default: Friday stands, yes.
Q2 Which path produces the numbers that count on 5 Nov: the churn label + latency judge (runs on the current
   kernel, needs only a pinned pass thread) or tools/perf (refuses any host without isolcpus AND nohz_full)?
   Default: the judge.
Q3 Which cores: 127 only, 126-127 (my default: 127 for the pass thread, 126 free for a pinned device thread),
   or all of 120-127 (only if you pin every thread, since isolated cores get no load balancing)? Irreversible
   without another reboot. With 126-127 your job must run the label with CPU set 120-125,127 and start it as
   `taskset -c 120-125 taskset -c 120-125,127 prlimit ... bash tools/ci/run_scheduled_gate.sh churn ...`
   so that nothing lands on an isolated core by chance. Default: 126-127 with that change.
Q4 Will you pin the fake device thread to its own core (126) and give it a 1 us timer slack, as the waker has,
   before Monday? Has any churn run ever recorded device.void=false, and with what late_mean? Default: you
   decide; 126 stays free.
Q5 Run windows 26 Oct-5 Nov in UTC only (US clocks change Sun 1 Nov), and this reservation rule: your job
   writes /tmp/positron-perf.RUNNING (start, end, pid, tag) and removes it at the end, you announce counted
   windows 2 h ahead, one job at a time, and we touch nothing while the marker exists. Default: Mon-Fri
   13:00-21:00 UTC, rule accepted.
Q6 May I re-run ~/positron/runs/ev3-churn-job.sh in the positron-perf account (tags govtest-1 after the
   governor change, govtest-2 after the reboot, about 3 min each) for before/after late_mean evidence?
   Default: no.
Nice to have: governor host-wide (default) or 120-127 only. Clock pass rule = delivered clock >= 2772 MHz from
one CPPC counter pair read before and after the run on core 127 (no polling during a run). Status of the
sampling tests and the timed compile. If tools/perf is your path: clang and ninja are not on the account's
non-interactive PATH, and ~/positron/fetchcontent, artifacts and work/sdk-v2 do not exist yet.</pre></blockquote>
</section>""")

# ---- section 5: findings
A("""<section id="s5"><h2>5. What the host check found</h2>
<h3>5.1 The host</h3>
<table><tr><th style="width:24%">Item</th><th>Observed value</th><th style="width:34%">Effect on the plan</th></tr>
<tr><td>Machine</td><td>Arm Limited “Phoenix Reference Server”, EVT0, Quanta motherboard, BIOS AGI-CPU-CRB-v0.7.2 (8 Sep 2026). 128 CPUs, one socket, one memory region (NUMA node), no hyper-threading (SMT), so each CPU is its own core. 377 GiB RAM, no swap. Two 1.7 TB NVMe disks. The second disk holds a 200 MB EFI partition and a 1.7 TB xfs partition and is EFI boot option 2, so it is probably another operating system, not a spare.</td><td>Early silicon: the vendor kernel's workarounds matter (5.2). Do not repurpose the second disk.</td></tr>
<tr><td>OS and kernel</td><td>Ubuntu 24.04.5 LTS, kernel 7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 (a preemptible multi-processor build, HZ = 250), up since 20 Oct 19:06 UTC. Host time zone UTC, NTP synchronized.</td><td>All windows below are given in UTC with PDT/EDT equivalents.</td></tr>
<tr><td>Accounts and sessions</td><td>Three human accounts: <code>arm</code> (admin), <code>positron-perf</code>, and since 22 Oct 01:19 UTC <code>jhan</code> (admin). <code>arm</code> has an idle console session (tty1) since 20 Oct 19:31 UTC, and logged in from alpha for 2–4 h stretches on 1, 20 and 21 Oct, from Jibin's workstation on 21 Oct 00:24–05:14 UTC and 22 Oct 00:51–01:18 UTC, and from 192.168.2.213 on 29 Sep (install day). Reboots: 29 Sep (×2), 3 Oct, 5 Oct, 20 Oct.</td><td>The reboot must be agreed with every root holder. The reservation rule must cover Jibin's own logins.</td></tr>
<tr><td>Remote login policy</td><td>sshd permits root login and password login (<code>PermitRootLogin yes</code>, <code>PasswordAuthentication yes</code> in the main file and three drop-ins written by the Arm installer). The positron-perf password is locked, so that account accepts keys only.</td><td>Hardening question A9. Not a demo blocker.</td></tr>
</table>
<h3>5.2 Isolation and kernel</h3>
<ul>
<li>Nothing is isolated: <code>/sys/devices/system/cpu/isolated</code> is empty, the <code>nohz_full</code> file does not exist, and the boot line is <code>BOOT_IMAGE=/vmlinuz-7.1.3-… root=UUID=… ro console=tty1 console=ttyAMA0</code>.</li>
<li>The running kernel's build options: <code># CONFIG_NO_HZ_FULL is not set</code>, <code>CONFIG_NO_HZ_IDLE=y</code>, no <code>CONFIG_RCU_NOCB_CPU</code> line, <code>CONFIG_CPU_ISOLATION=y</code>, <code>CONFIG_CPUSETS=y</code>, <code>CONFIG_PREEMPT=y</code>, <code>CONFIG_HZ=250</code>. So isolcpus and irqaffinity work after a reboot. nohz_full and rcu_nocbs cannot work on this kernel.</li>
<li>What the kernel does with the unsupported arguments: <code>nohz_full=</code> is parsed, refused with “Housekeeping: nohz unsupported. Build with CONFIG_NO_HZ_FULL”, and then also listed under “Unknown kernel command line parameters”. <code>rcu_nocbs=</code> has no handler at all and gets only the unknown-parameter notice. The flag form <code>isolcpus=nohz,…</code> is worse: the kernel drops the whole isolcpus setting with it. None of the three has any effect.</li>
<li>A second kernel is installed: Ubuntu's 6.8.0-147-generic, which unattended-upgrades installed on 15 Oct 06:16 UTC (after -142 and -146). Its build has <code>CONFIG_NO_HZ_FULL=y</code> and <code>CONFIG_RCU_NOCB_CPU=y</code>. GRUB's saved entry pins the vendor kernel, so reboots keep the vendor kernel. The login records (since 29 Sep) show every boot on the vendor kernel.</li>
<li>The vendor kernel logs two silicon-specific workarounds at boot: “GICv3: Arm AGI CPU A0 detected, enabling GIC erratum workaround” and “CPU features: detected: Broken broadcast TLBI completion” (GIC is the Arm interrupt controller, TLBI the translation-cache invalidate instruction, A0 the first silicon revision). The GIC quirk exists only in the vendor tree. The TLBI workaround (erratum 4118414 family) is upstream code that Ubuntu backported into 6.8.0-146, so the stock kernel probably has it. Two further vendor-only errata options are not active on this board (one needs a boot parameter that is not set, the other targets a different CPU). Booting the stock kernel on this board therefore lacks at least the GIC quirk and has never been tried here. It stays an untested risk, not a plan.</li>
<li>The vendor kernel's source is not on the host (only headers, which match upstream 7.1.3 for the isolation code). Its package maintainer is an Arm engineer (<code>avadnaik@2paltra-216.5g.ast.arm.com</code>), and the package was installed from a local file on 28 Sep 17:25 UTC. Secure Boot is off (no lockdown), so a rebuilt kernel needs no signing. The Arm SVK installer left a gcc-14 toolchain in <code>/opt/arm-svk</code> with <code>KERNEL_MCPU=neoverse-v3ae</code> set, which suggests kernel builds for this board are a supported workflow.</li>
<li>Both the running vendor kernel and Ubuntu's 6.8 are of the generation where a cpuset isolated partition updates the kernel's housekeeping masks at run time, but only boot-time isolcpus CPUs appear in <code>/sys/devices/system/cpu/isolated</code>, the file the SDK tools read.</li>
</ul>
<h3>5.3 The clock</h3>
<p>Driver <code>cppc_cpufreq</code>, 128 policies with one CPU each, governor schedutil everywhere, limits 1.6–2.8 GHz. The CPPC table says highest = nominal = 140 performance units = 2,800 MHz, lowest 80 units = 1,600 MHz, reference 50 units. One unit is 20 MHz. No boost range exists. schedutil runs in fast-switch mode (no governor threads), so a clock change is a plain register write from the scheduler.</p>
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
<p>What this means for hypothesis H1 of the first draft (“the 1.6 GHz sleep-pattern clock causes the fake device's lateness”): <strong>not supported as a sufficient cause</strong>. On a dedicated idle CPU at the low clock the same wait pattern is late by 0.02 µs on average, 300 times below the 2.5 µs band. The clock does matter for the tick's cost: at the low clock a tick stall exceeds 2.5 µs in 1.2% of spin windows (max 5.8 µs), at 2.79 GHz in 0.3% (p99 1.99 µs), and the rare 8 µs to 11 µs stalls occur at both clocks. So the performance governor shortens the typical tick stall by about the clock ratio but cannot by itself turn a 6.2 µs mean into less than 2.5 µs.</p>
<p>Remaining hypotheses for churn-r1's 6.2 µs mean, each with the measurement that decides it:</p>
<ul>
<li><strong>H2, CPU sharing.</strong> The device thread is unpinned and shared CPUs 120–126 with the harness's other threads and the launcher's Python, so its wake-up could have to preempt a running thread. Those CPUs took 1,300 to 7,700 interrupts per second from the threads' own timed sleeps (Figure 2). Measurement: a re-run with the device thread pinned to an otherwise idle CPU (D5), comparing <code>late_mean_s</code>.</li>
<li><strong>H3, the retire path's own work.</strong> In <code>fake_device.cpp</code> the thread writes the pass's drain rows and pushes the completion before it computes the lateness, so <code>late_mean</code> includes that work. If that cost scales with the clock, the governor cuts 6.25 µs to about 3.6 µs (est., 1.6/2.8 of it), still above the band. Measurement: govtest-1 (governor only, before the reboot).</li>
<li><strong>H4, the 50 µs timer slack.</strong> The thread's sleep ends about 53 µs after the requested time, so only about 47 µs of the 100 µs spin window remain for absorbing a late wake-up. A 1 µs slack (one prctl call, no privilege) widens that margin. Measurement: hiccup with and without the slack, then the SDK change (D5).</li>
</ul>
""")
A(fig("fig_churn_r1", "Figure 2. Jeremy's run churn-r1, per reserved CPU: requested clock over the 34 samples (left) and interrupts per second during the 172.9 s job (right). Only the pass core requested 2.8 GHz. The CPUs that hosted the other harness threads stayed at 1.6 GHz and took the most interrupts, from those threads' own timed sleeps. Sources: ~/positron/runs/churn-r1/isol.samples.jsonl and phoenix-crb-round4.txt."))
A("""<p>How to read the clock without disturbing a run: <code>scaling_cur_freq</code> is the governor's request and costs nothing. The CPPC feedback counters give the delivered clock but each read sends two IPIs to the CPU being read (measured: 10 reads added 20 function-call interrupts), and root's <code>cpuinfo_cur_freq</code> sends four. The reference counter runs at 1,000 MHz only while the CPU is not idle, so the counter pair over a run measures the delivered clock during the active time. Rule for counted runs: one counter pair on the pass core before and after the run, no polling in between. Wake-up latency is favourable: no cpuidle driver is registered (“driver: none”), so idle CPUs wait in the shallow wait-for-interrupt state (WFI) and wake in about 3 µs (measured as overshoot minus slack).</p>
<h3>5.4 Interrupts and the timer tick on CPUs 120–127</h3>
""")
A(fig("fig_ticks", "Figure 3. Timer interrupts received by one CPU in 5 s: 10 when idle, 1,261 when running a pinned spin (CPU 125: 1,258). That is the HZ = 250 scheduler tick. nohz_full would remove it from a CPU that runs a single task (a residual once-per-second tick runs on a housekeeping CPU instead). Nothing on the running kernel can."))
A("""<table><tr><th>What reaches CPUs 120–127</th><th class="num">Since boot (31 h at 01:14 UTC)</th><th>What removes it</th></tr>
<tr><td>Scheduler tick (arch_timer, IRQ 12), 250 per second on a busy CPU, est. 1 µs to 2 µs of handler time each</td><td class="num">5,327,444 (97.1%)</td><td>Only nohz_full (needs another kernel). The performance governor shortens each tick's stall but not its count.</td></tr>
<tr><td>Function-call IPIs (IPI1)</td><td class="num">123,695</td><td>Partly: <code>rcu_normal=1</code> removes the ones from expedited RCU grace periods, which every sandboxed service start or stop triggers (26 IPIs to a busy CPU per start, measured). Any unprivileged user can trigger them too (<code>unshare</code>). Reading the CPPC counters of a CPU sends two.</td></tr>
<tr><td>Rescheduling IPIs (IPI0)</td><td class="num">2,032</td><td>Isolation reduces them (no load balancing onto the CPU).</td></tr>
<tr><td>NVMe queue interrupts nvme0q119–126 and nvme1q119–126 (one queue per CPU per disk, managed)</td><td class="num">33,539 (nvme0q124 alone: 22,045)</td><td>Nothing moves them: each queue's mask holds one CPU, so <code>isolcpus=managed_irq</code> has no effect here, and a write to /proc/irq returns “Operation not permitted”. They fire only for disk I/O issued from that CPU. After isolation the page-cache writeback runs on housekeeping CPUs, so only I/O issued synchronously from the pass core (direct writes, fsync) lands there.</td></tr>
<tr><td>Network queues (128 lines on two ports), other device IRQs</td><td class="num">0</td><td>Already elsewhere: every network interrupt is effectively serviced on CPU 0. <code>irqaffinity=0-119</code> only guards against future devices.</td></tr>
<tr><td>Unbound kernel workers (kworker/u…), writeback flushers (seen on CPUs 124 and 127 during churn-r1), unbound kernel threads such as RCU's</td><td class="num">not counted</td><td><code>isolcpus=domain</code> excludes the CPUs from unbound workqueues and unbound kernel threads, and stops the per-CPU vmstat update there. Per-CPU work queued from the CPU itself stays.</td></tr>
</table>
<p>Of all interrupts these eight CPUs took since boot, 91.3% (5,010,908 of 5,487,292) fell inside the 172.9 s of churn-r1 and are the job's own timer wake-ups, not host noise (Figure 2). irqbalance is not installed. No per-CPU watchdog timer runs (the lockup detectors are not built), no broadcast timer exists, and there are no deep idle states. TLB invalidation on this Arm host is a hardware broadcast, not an IPI, so no isolation setting removes it.</p>
""")
A(fig("fig_lanes", "Figure 4. Who does what, when, on one reserved CPU: the fake device thread sleeps and then spins before each pass retirement. Its sleep overshoots the requested wake by 53 µs (the 50 µs default timer slack plus wake-up latency), so about 47 µs of the 100 µs spin window remain. The scheduler tick lands every 4 ms. The band that voids a record is a mean lateness of 2.5 µs, thinner than a pixel here. The worst single lateness in churn-r1 was 220 µs. Durations are to scale (1 ms = 100 px). The tick's own length was not measured, and the late completion's position is schematic."))
A("""<h3>5.5 Background work and timers</h3>
<p>From <code>systemctl list-timers --all</code> at 01:53 UTC on 22 Oct. Next firings are in UTC. The proposed run window is 13:00–21:00 UTC.</p>
<table><tr><th style="width:26%">Service or timer</th><th>When</th><th>Risk for a timed run</th><th>Action (P1b)</th></tr>
<tr><td>apt-daily-upgrade.timer</td><td>daily 06:00 UTC + up to 60 min. Next: Thu 22 Oct 06:28 UTC (Wed 23:28 PDT)</td><td>Installs packages, including kernels (9 and 15 Oct). Automatic reboot is not enabled. <code>unattended-upgrades.service</code> itself is only a shutdown hook.</td><td>Disable tonight, before 06:28 UTC.</td></tr>
<tr><td>apt-daily.timer (package lists)</td><td>06:00 and 18:00 UTC + up to 12 h random, so any hour. Last: 21:57 UTC 21 Oct</td><td>Network and CPU bursts at unpredictable times.</td><td>Disable.</td></tr>
<tr><td>fwupd-refresh.timer</td><td>hourly + up to 1 h random</td><td>Firmware metadata refresh, a sandboxed service start (IPIs to busy CPUs) inside every window.</td><td>Disable.</td></tr>
<tr><td>motd-news.timer, man-db.timer, update-notifier-motd.timer</td><td>twice daily at random, daily 00:00–12:00 UTC, weekly</td><td>Short sandboxed service starts.</td><td>Disable.</td></tr>
<tr><td>update-notifier-download.timer, systemd-tmpfiles-clean.timer</td><td>boot + 5 min and boot + 15 min, then daily. After a 15:00 UTC reboot: about 15:05 and 15:15 UTC daily, inside the window</td><td>Short.</td><td>Disable the first, mask the second (it is a static unit).</td></tr>
<tr><td>fstrim.timer</td><td>weekly: Mon 26 Oct 00:27 UTC (Sun 25 Oct 17:27 PDT, 20:27 EDT), then Mon 2 Nov 00:00–02:40 UTC</td><td>The root filesystem is mounted with <code>discard</code>, and the kernel's “already trimmed” marks are lost at reboot, so the first run after the reboot re-discards all 1.7 TB of free space.</td><td>Disable until 6 Nov.</td></tr>
<tr><td>logrotate.timer, dpkg-db-backup.timer, e2scrub_all.timer</td><td>00:00–01:00 UTC daily (17:00 PDT, 20:00 EDT), weekly Sun 03:10 UTC</td><td>Seconds of disk activity, outside the window. e2scrub does nothing here (no LVM).</td><td>Disable (harmless either way).</td></tr>
<tr><td>sysstat-collect.timer, sysstat-summary.timer</td><td>every 10 min, daily 00:07 UTC</td><td>One short sampler on a housekeeping CPU. It is collecting (the cron path is disabled, the systemd path is not), so <code>sar -P 120-127 -f /var/log/sysstat/saDD</code> gives independent 10-minute per-CPU history, which already shows churn-r1 on CPU 127.</td><td>Keep by default (A8). Cron's sysstat and cron.daily entries are no-ops.</td></tr>
<tr><td>netperf.service (a “network benchmark” server, <code>netserver</code>, started at boot from an init script)</td><td>always on</td><td>Idle unless someone runs netperf against the host. Then heavy CPU and network on CPU 0 and wherever the process runs.</td><td>Stop and disable, then confirm with <code>pgrep -a netserver</code>.</td></tr>
<tr><td>snapd.socket</td><td>on demand</td><td>Any <code>snap</code> command starts snapd, which tries and fails to mount a snap. Two of this analysis's own checks triggered it.</td><td>Do not run snap commands. Optionally disable the socket.</td></tr>
<tr><td>ua-timer, snapd.snap-repair, apport-autoreport</td><td>never (conditions false)</td><td>None.</td><td>Leave.</td></tr>
<tr><td>smartmontools, rsyslog, ModemManager, udisks2, cron, ssh, systemd-networkd/resolved/timesyncd</td><td>always on</td><td>Light. smartd polls the disks every 30 min through the admin queues on CPU 0.</td><td>Leave. They run on housekeeping CPUs once isolation is active.</td></tr>
</table>
<p>Re-enabling a <code>Persistent=true</code> timer after the demo runs its missed jobs at once (apt-daily-upgrade within 1 h, apt-daily within 12 h), so the restore step belongs outside any run window. No LSF, continuous-integration runner, Docker or container runtime runs on the host. The positron-perf user manager runs one timer of its own (<code>launchpadlib-cache-clean.timer</code>, 5 min after login, then daily) on housekeeping CPUs, which Jeremy can mask without root.</p>
<h3>5.6 Account, access, tools and storage</h3>
<table><tr><th style="width:24%">Item</th><th>Observed</th><th style="width:30%">Effect</th></tr>
<tr><td>Account</td><td><code>positron-perf</code>, uid 1001, groups positron-perf and users. Password locked. <code>sudo -n</code> says a password is required, and there is no password-free sudo rule. A 49-byte <code>/etc/sudoers.d/positron-perf-setup</code> exists (created 21 Oct 05:12 UTC while three <code>arm</code> sessions were open) and cannot be read by the account.</td><td>Meets “no sudo”. The administrator reads the drop-in (A4).</td></tr>
<tr><td>Keys</td><td>Jibin's workstation key (comment rewritten to positron-perf@phoenix), jeremy@sw-dev-01, jeremy@DESKTOP-V2B1166. The key file was last changed 21 Oct 16:53 UTC.</td><td>Jeremy's keys are in place.</td></tr>
<tr><td>Login sources (the account's own journal)</td><td>alpha 192.168.1.200: 101 journal lines (about 50 sessions), 17:07–18:58 UTC 21 Oct (the staging). sw-dev-01 at 192.168.2.39: 4 sessions, 17:07–18:27 UTC. Jibin's workstation 192.168.2.136: this check. The journal's “Accepted publickey” lines are root-only, so which key each session used is unknown.</td><td>sw-dev-01 reaches the host. Who operated alpha is question A2.</td></tr>
<tr><td>Vendor tool files owned by the account</td><td>347 files from the <code>linux-tools</code> package are owned by uid 1001: <code>/usr/bin/perf</code>, <code>/usr/bin/cpupower</code>, <code>/usr/sbin/bpftool</code>, <code>/usr/libexec/cpupower</code>, <code>libcpupower.so</code>, <code>/usr/lib/systemd/system/cpupower.service</code>, <code>/etc/cpupower-service.conf</code> and more. The package was evidently built without fakeroot, so the builder's uid was kept.</td><td>Security finding. Fix in P1d before any root use of these tools.</td></tr>
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
<tr><td>Not present</td><td>No ctest or pytest log (test 2 unverified). No perf-lane layout: <code>~/positron/fetchcontent</code>, <code>~/positron/artifacts</code>, <code>~/positron/work/sdk-v2</code> and the lane's lock file do not exist, and the lane's job script does not source the toolchain.</td></tr>
</table>
<h3>5.8 What the SDK's own tools require</h3>
<ul>
<li><strong>churn.py / latency judge</strong> (the per-user latency gate run on the host): the judge's isolation check passes whenever <code>pass_thread_core</code> is an integer, that is when the pass thread was pinned. It records <code>core_isolated</code> (pass core in <code>/sys/devices/system/cpu/isolated</code>) and the isolated CPU list as facts and never reads nohz_full. The record is void when the fake device's mean lateness passes the band.</li>
<li><strong>tools/perf/records.py and perf_lane.py</strong> (the host timing of the TPS gate and the timed compile): refuse a host with “no online core in both isolcpus and nohz_full”, require the run to be the dedicated local user on bare-metal aarch64, flag a one-minute load above 0.5, other users' processes at 5% CPU or more, and any CI-runner process. The workers, the client and the fake device run on the non-isolated CPUs in this tool. The lane holds a lock while its job runs.</li>
<li><strong>Policy in the SDK's documents:</strong> the README says the per-user figures “count only from the perf host”, and the design says U1 p99 and U5 waking count only from an isolated host. The code of the judge does not enforce that. Whether a judge-path run counts is Jeremy's decision (D2).</li>
<li><strong>Thread placement in the runtime</strong>: the pass thread pins itself to <code>pass_thread_core</code>. Worker threads remove the pass CPU from their mask and otherwise keep the job's mask. No code sets the fake device thread's affinity. Only the waker thread lowers its timer slack (to 1 µs). Nothing uses SCHED_FIFO or mlockall.</li>
<li><strong>Consequence for the no-reboot route</strong>: a cpuset isolated partition never shows in <code>/sys/devices/system/cpu/isolated</code>, so churn.py would record <code>core_isolated: false</code> and the perf lane would still refuse the host. The SDK tooling forces the boot-argument route.</li>
</ul>
</section>""")

# ---- section 6: plan
A("""<section id="s6"><h2>6. Action plan</h2>""")
A(fig("fig_timeline", "Figure 5. Timeline from 21 October to the 5 November demo. The reboot is proposed for Thursday 22 October 15:00 UTC. The kernel rebuild runs in parallel and does not block Friday. The bottom row marks the host timers that can disturb a run until they are paused, the two weekly fstrim runs, and the US clock change on Sunday 1 November."))
A("""<div class="phase"><h3>P0. Tonight, Wednesday 21 October (PDT): decide and write</h3><div class="meta">Owner: Jibin. Needs: nothing on the host.</div>
<ul>
<li>Send Jeremy the draft message in section 4 (status, corrections, six questions with defaults).</li>
<li>Answer A1 and A2 for the record (who holds <code>arm</code> and <code>jhan</code>, who operates alpha, whether the staging was Jibin's side's work).</li>
<li>Ask Arm's SVK contact (A6) for the kernel tree at commit <code>4dbc8bb88858</code> with its config, or for a build with <code>CONFIG_NO_HZ_FULL=y</code>.</li>
<li>Agree the reboot slot (A7) with every root holder.</li>
</ul></div>
<div class="phase"><h3>P1. Tonight or Thursday morning: live root changes, no reboot</h3><div class="meta">Owner: an administrator account (<code>arm</code> or <code>jhan</code>). Reboot: no. Reversible in seconds. P1b must happen before Thu 22 Oct 06:28 UTC (Wed 23:28 PDT), when apt-daily-upgrade fires next.</div>
<p><strong>P1a. Performance governor on all 128 CPUs</strong> (or on 120–127 only, if Jeremy prefers, as each CPU is its own policy). Use sysfs only. Do not use <code>sudo cpupower</code> until P1d is done.</p>""")
A(code("""# as the administrator on phoenix-crb
who; ps -u positron-perf -o pid,etime,cmd | grep -v sshd           # nobody mid-run, no positron-perf job
for p in /sys/devices/system/cpu/cpufreq/policy*; do echo performance | sudo tee "$p/scaling_governor" >/dev/null; done
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c      # expect: 128 performance
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq | sort | uniq -c      # expect: 128 x 2800000 (the request, kHz)"""))
A("""<p>This write does not survive a reboot (the kernel's default governor is schedutil). Persistence comes from the boot argument <code>cpufreq.default_governor=performance</code> in P2 and, as a second safety, a boot-time unit. In a systemd unit <code>$$</code> is the spelling of a literal dollar sign, and the loop waits up to 60 s for the cpufreq driver module, which udev loads with no ordering guarantee:</p>""")
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
A("""<p><strong>P1c. Remove the expedited-RCU IPIs now</strong> (optional, A8, reversible with <code>echo 0</code>). It makes every service start and namespace teardown stop sending function-call interrupts to busy CPUs:</p>""")
A(code("""echo 1 | sudo tee /sys/kernel/rcu_normal          # persistent form: rcupdate.rcu_normal=1 in the P2 drop-in
cat /sys/kernel/rcu_normal                        # expect: 1"""))
A("""<p><strong>P1d. Fix the ownership of the vendor tool files</strong> (security, A5). Do this before any root use of perf, cpupower or bpftool, and never enable <code>cpupower.service</code> before it:</p>""")
A(code("""dpkg -S /usr/bin/cpupower                                               # expect: linux-tools: /usr/bin/cpupower
find /usr /etc /lib /opt /var /boot -xdev -user positron-perf | wc -l     # today: 347
dpkg -L linux-tools | xargs -d '\\n' sudo chown -h root:root
find /usr /etc /lib /opt /var /boot -xdev -user positron-perf | wc -l     # expect: 0
ls -l /usr/bin/perf /usr/bin/cpupower /usr/lib/systemd/system/cpupower.service   # expect: root root"""))
A("""<p><strong>P1e. Governor-only re-run of Jeremy's job, before the reboot</strong> (only with D6 answered yes, or if A2 says the scripts are Jibin's side's). It separates the clock effect from the isolation effect and tests hypothesis H3. Run as <code>positron-perf</code>, with the script unchanged:</p>""")
A(code("""cd ~/positron/runs && ./ev3-churn-job.sh govtest-1                 # about 3 min; writes runs/churn-govtest-1/
python3 ~/positron/runs/readrec.py ~/positron/runs/churn-govtest-1/record     # prints the device lateness and the verdict
python3 -c "import json; print(json.load(open('/home/positron-perf/positron/runs/churn-govtest-1/record/churn/churn.record.json'))['device'])"
# compare with churn-r1: late_mean_s 6.246e-06, late_max_s 2.20e-04, lateness_band_s 2.502e-06, void True"""))
A("""</div>
<div class="phase"><h3>P2. Thursday 22 October 15:00 UTC (08:00 PDT, 11:00 EDT): reboot into isolcpus, about 15 minutes of downtime</h3><div class="meta">Owner: an administrator account, with Jibin. Reboot: yes, once. Agree the time with every root holder and with Jeremy first. Fallback slot: Friday 13:00 UTC.</div>
<p>Add one drop-in. The cloud-image drop-in <code>50-cloudimg-settings.cfg</code> overrides <code>GRUB_CMDLINE_LINUX_DEFAULT</code>, so the new arguments go on <code>GRUB_CMDLINE_LINUX</code>, which nothing else sets. The CPU list is decision D3 and cannot be changed later without another reboot:</p>""")
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
A("""<p>Do not add <code>nohz_full=</code>, <code>rcu_nocbs=</code> or the <code>isolcpus=nohz</code> flag on this kernel (section 5.2). The three planned arguments cannot fail the boot: a bad value is reported in dmesg and dropped. <code>isolcpus=managed_irq</code> changes nothing for the single-CPU NVMe queues and is kept only for future devices. <code>irqaffinity=0-119</code> keeps default device interrupts off the whole reserved group. After the reboot, these checks need no root and can be run by <code>positron-perf</code> (expected values are for variant A):</p>""")
A(code("""cat /proc/cmdline                                                      # carries the new arguments
cat /sys/devices/system/cpu/isolated                                   # 126-127
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor | sort | uniq -c      # 128 performance
dmesg | grep -E 'Housekeeping|Invalid flag|Skipped unknown flag|Unknown kernel command line|workqueue: Restricting' | grep -v 'Kernel command line'
                                                                       # must print nothing
cat /sys/devices/virtual/workqueue/cpumask                             # 3fffffff,ffffffff,ffffffff,ffffffff (bits 126-127 clear)
cat /sys/devices/virtual/workqueue/cpumask_isolated                    # c0000000,00000000,00000000,00000000
cat /proc/irq/default_smp_affinity                                     # 00ffffff,ffffffff,ffffffff,ffffffff (CPUs 0-119)
grep Cpus_allowed_list /proc/1/status /proc/$(pgrep -x rcu_preempt)/status   # 0-125 for both (variant B: 0-119)
taskset -c 127 true && echo "a job can still be placed on 127"
cat /sys/kernel/rcu_normal                                             # 1 if rcupdate.rcu_normal=1 was kept
uname -r; uptime; who"""))
A(fig("fig_cpu_alloc", "Figure 6. The proposed split of the 128 CPUs and what reaches each reserved CPU today. Variant A isolates 126–127 within the reserved group of eight, with 120–125 kept free by agreement for the job's other threads. Variant B isolates all eight."))
A("""</div>
<div class="phase"><h3>P3. Thursday 22 to Friday 23 October: validate, then hand off</h3><div class="meta">Owner: Jibin with Jeremy. Deadline: Friday 23 October 21:00 UTC (Jeremy's end of day).</div>
<ul>
<li>Run Jeremy's job again on the isolated setup (<code>govtest-2</code>, only with D6 or A2 allowing it), with the launch line changed so that nothing lands on an isolated CPU by chance. The current line 24 of <code>ev3-churn-job.sh</code> and its replacement:</li>
</ul>""")
A(code("""# today:
taskset -c 120-127 prlimit --data=51539607552 timeout --signal=TERM --kill-after=5m 45m bash tools/ci/run_scheduled_gate.sh churn $R/record
# after the reboot (variant A): land the launcher on a balanced CPU first, then widen the set to include the pass core 127
taskset -c 120-125 taskset -c 120-125,127 prlimit --data=51539607552 timeout --signal=TERM --kill-after=5m 45m bash tools/ci/run_scheduled_gate.sh churn $R/record
# churn.py then pins the pass thread to the set's last CPU (127) and gives the other threads 120-125; CPU 126 stays empty."""))
A("""<ul>
<li>Compare with churn-r1 and govtest-1: the judge verdict, the device's mean lateness against the band, the pass bind p99 and maximum, and isol.py's samples (every harness, python and bash thread must show <code>psr</code> 120–125 or 127, never 126).</li>
<li>Delivered clock, without root and without disturbing the run: one feedback-counter pair on the pass core before and after the run.</li>
</ul>""")
A(code("""# as positron-perf: once before and once after a run; each read sends 2 IPIs to CPU 127, so never poll during a run
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R0> del:<D0>
# ... the run ...
cat /sys/devices/system/cpu/cpu127/acpi_cppc/feedback_ctrs            # ref:<R1> del:<D1>
# delivered MHz = 50 * (D1 - D0) / (R1 - R0) * 20.  Pass: >= 2772 MHz (99% of 2800). A 3 s spin measured 2796 MHz (139.8 units)."""))
A("""<ul>
<li>Hand-off note to Jeremy: kernel version, exact boot line, isolated CPU list, governor state, the counter pair, the expected sysfs values from P2, the paused timers, the reservation rule, the launch-line change, the known limitation (no nohz_full: 250 Hz tick on a busy isolated CPU, expedited-RCU IPIs only if rcu_normal is off), and the pre-run checklist from section 7.</li>
</ul></div>
<div class="phase"><h3>P4. In parallel: a kernel with nohz_full</h3><div class="meta">Owner: Arm (the kernel's builder), then the administrator. Reboot: a second one. Target: before 5 November if D2 says the perf lane counts, otherwise after the demo.</div>""")
A(fig("fig_kernel_paths", "Figure 7. Friday's hand-off runs on the current kernel. nohz_full needs one of three kernel paths. Rebuilding the vendor kernel from its source is preferred. Booting the installed stock 6.8 kernel is not recommended on this A0 silicon."))
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
<li>Change the drop-in to identical CPU lists, which the kernel requires: <code>isolcpus=domain,managed_irq,126-127 nohz_full=126-127 rcu_nocbs=126-127 irqaffinity=0-119 cpufreq.default_governor=performance</code>. Then check <code>cat /sys/devices/system/cpu/nohz_full</code> (126-127), <code>cat /sys/devices/system/cpu/housekeeping</code> (0-125, printed only when the feature works) and <code>dmesg | grep -E 'NO_HZ|Offload RCU|Housekeeping'</code> for “NO_HZ: Full dynticks CPUs: 126-127” and “Offload RCU callbacks from CPUs: 126-127”.</li>
<li>Rules on a nohz_full kernel: the isolated CPU must run a single task (a second runnable thread brings the tick back), and that task must not use POSIX CPU timers. The pass thread meets both today. <code>cpuinfo_avg_freq</code> stops working for those CPUs, so the counter pair stays the clock evidence.</li>
<li>Time needed: insufficient data. It depends on Arm's response (A6).</li>
</ul></div>
<div class="phase"><h3>P5. Monday 26 October to Thursday 5 November: counted runs</h3><div class="meta">Owner: Jeremy runs. Jibin keeps the host ready.</div>
<ul>
<li>Windows (D4 default): Mon–Fri 13:00–21:00 UTC. That is 06:00–14:00 PDT and 09:00–17:00 EDT until 31 October, and 05:00–13:00 PST and 08:00–16:00 EST from 2 November. State every window in UTC.</li>
<li>Reservation rule: Jeremy's job writes <code>/tmp/positron-perf.RUNNING</code> at start and removes it at the end, windows are announced 2 h ahead, one job at a time, and nobody (Jibin's sessions included) runs work, service restarts, <code>snap</code>, <code>unshare</code>, <code>podman</code> or <code>systemd-run</code> while the marker exists. The host has no technical lock. The SDK's perf lane has its own.</li>
<li>Before each window: the checklist in section 7 (two minutes, no root).</li>
<li>The second weekly fstrim would fall on Mon 2 Nov 00:00–02:40 UTC. It stays disabled.</li>
<li>After Friday 6 November, outside any run window: re-enable the timers and netperf (or leave netperf off), expect an immediate apt catch-up run, and decide whether to keep the governor and isolation.</li>
</ul>""")
A(code("""# restore, after 6 Nov, outside any run window
sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer fwupd-refresh.timer motd-news.timer man-db.timer \\
    update-notifier-download.timer update-notifier-motd.timer fstrim.timer e2scrub_all.timer logrotate.timer dpkg-db-backup.timer
sudo systemctl unmask systemd-tmpfiles-clean.timer && sudo systemctl start systemd-tmpfiles-clean.timer"""))
A("""</div>
<h3>If the reboot cannot happen by Friday: a no-reboot fallback</h3>
<p>Root can create a cgroup v2 cpuset “isolated partition” for the chosen CPUs while the system runs. On this kernel it gives the scheduler-isolation part of isolcpus and also removes the CPUs from unbound workqueues, unbound kernel threads and the timer-migration hierarchy. It does not give nohz_full, does not move the managed NVMe interrupts, does not persist across reboot, and does not show in <code>/sys/devices/system/cpu/isolated</code>, so Jeremy's tools record <code>core_isolated: false</code> and the perf lane still refuses the host. Three more limits: positron-perf cannot move its own processes into the partition (root must write the process id, or delegate the cgroup), one process cannot straddle the partition and the rest (so Jeremy's one-process layout needs the whole job inside, or an untested threaded-cgroup variant), and systemd 255 can drop a hand-enabled cpuset controller when it next re-realizes the root slice with a new controller set. Use it only if the reboot slips, tell Jeremy what it lacks (decision D1 then includes it), and test it once before offering it.</p>""")
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
<li>Governor: <code>echo schedutil</code> into every policy's <code>scaling_governor</code>, and disable the unit.</li>
<li>Timers: the restore commands in P5.</li>
<li>Boot arguments: remove <code>/etc/default/grub.d/60-positron-isolation.cfg</code>, run <code>update-grub</code>, reboot. In an emergency the GRUB menu lists every entry, but it shows on the EFI console (serial mirroring unverified) and a failed boot retries the saved entry after 10 s, so console access (A3) is the real safety net.</li>
<li>Kernel: keep the current entry. The saved-entry setting selects it until changed, and <code>grub-reboot</code> trials return to it.</li>
<li><code>rcu_normal</code>: <code>echo 0</code> into <code>/sys/kernel/rcu_normal</code>, and drop the boot argument.</li>
</ul>
</section>""")

# ---- section 7: acceptance
A("""<section id="s7"><h2>7. Acceptance checks</h2>
<h3>Friday 23 October: the host is ready when</h3>
<table><tr><th style="width:24%">Check</th><th>Evidence to keep</th><th style="width:34%">Ready means</th></tr>
<tr><td>Boot arguments took effect</td><td><code>/proc/cmdline</code>, <code>/sys/devices/system/cpu/isolated</code>, the filtered dmesg grep from P2, the workqueue masks, <code>/proc/irq/default_smp_affinity</code>, PID 1's allowed CPUs</td><td>The isolated list equals the agreed CPUs (D3), the dmesg grep prints nothing, and the masks match the expected values in P2.</td></tr>
<tr><td>Clock</td><td>128 × performance, and one feedback-counter pair on the pass core around the govtest-2 run</td><td>Delivered clock on the pass core ≥ 2,772 MHz (D4). <code>scaling_cur_freq</code> reads 2,800,000 kHz on 120–127 in every isol.py sample.</td></tr>
<tr><td>Interrupts and workers off the isolated CPUs</td><td><code>/proc/interrupts</code> difference on 126–127 during the run, workqueue masks, isol.py samples, <code>ps -o time</code> of <code>kworker/127:*</code></td><td>On 126–127 only the timer tick and IPIs remain (NVMe completions only if the pass thread writes files), and 120–125 carry their own threads' interrupts. The per-CPU kworkers on 127 gain no CPU time.</td></tr>
<tr><td>Thread placement</td><td>isol.py samples of govtest-2</td><td>Pass thread on 127, every other harness, python and bash thread on 120–125, nothing on 126.</td></tr>
<tr><td>Jeremy's job on the new setup</td><td>govtest-2 verdict, device <code>late_mean_s</code> against <code>lateness_band_s</code>, bind p99 and maximum, compared with churn-r1 and govtest-1</td><td><code>void = false</code> (mean lateness below 2.5 µs), or the remaining gap is explicit and Jeremy has accepted it or taken the SDK-side change (D5).</td></tr>
<tr><td>Quiet host</td><td><code>systemctl list-timers --all</code>, <code>who</code>, <code>pgrep -a netserver</code>, isol.py snapshot, sar history</td><td>No apt, fwupd, motd, man-db, update-notifier, tmpfiles or fstrim timer active. netserver gone. Nobody else logged in during the window (an idle arm console may remain).</td></tr>
<tr><td>Ownership fixed</td><td><code>find … -user positron-perf | wc -l</code></td><td>0 files outside /home owned by positron-perf.</td></tr>
<tr><td>Hand-off note sent</td><td>The note itself</td><td>Jeremy has the configuration record, the launch-line change, the reservation rule and the limitation (no nohz_full).</td></tr>
</table>
<h3>Before each counted run (Monday onward, two minutes, no root)</h3>""")
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
<li>All host facts come from read-only commands run as <code>positron-perf</code>. The first inspection ran on 21 October 2026 between 23:42 and 23:57 UTC with follow-ups until 22 October 00:17 UTC. The verification pass (20 agents: three paraphrases and a judge, five analysts, ten adversarial verifiers, one completeness critic) re-ran read-only checks between 00:38 and 01:24 UTC and checked the kernel claims against the 7.1 and 6.8 sources and the systemd 255 source. Jibin's session re-ran the hiccup probe at 01:57 UTC. The scripts and complete outputs are in the folder <code>phoenix-crb-evidence-2026-10-21/</code> next to this file: <code>phoenix-crb-inspection.txt</code>, <code>-followup.txt</code>, <code>-round3.txt</code> to <code>-round6.txt</code>, the subfolder <code>verification-2026-10-22/</code> (the verifiers' raw outputs, the hiccup re-run, and the digests of the verdicts, corrections and the critic's findings), the scripts that produced them, and the figure generator.</li>
<li>Load placed on the host by this analysis: a 3 s pinned spin on CPU 121 (clock), 5 s pinned spins on CPUs 121 and 125 (tick count), three 4 s pinned spins on CPU 121 and one 1 s spin on CPU 124 (the verifiers' IPI and ramp tests), hiccup runs of 3.8 s on CPUs 124, 125 and 126, 30 reads of CPPC counters (60 IPIs to the CPUs read), three unprivileged <code>unshare -Urm true</code> calls, three <code>timedatectl</code> calls (which started systemd-timedated) and two <code>snap list</code> calls (which started snapd for a few seconds). No file was written on the host, no sudo was used, and no setting changed.</li>
<li>The one earlier document, <code>jeremy-tasks.html</code> (inspection 21:08 UTC), did not see the second kernel, the staged workspace, the login sources, the clock measurement or the SDK tool rules. This plan supersedes its action plan. The first draft of this plan (21 October 17:30 PDT) attributed the lateness to the clock (hypothesis H1) and the void to the maximum lateness. Both were corrected by the verification pass and by the hiccup re-run.</li>
<li>Jeremy's frequency samples (Figure 1) were taken by his probes. Their sampling interval and CPU are not recorded in the files. The clock samples of Figure 2 are governor requests, not delivered clocks.</li>
</ul>
<h3>Insufficient data</h3>
<ul>
<li>Who at Arm can provide the vendor kernel's source at <code>4dbc8bb88858</code> or a NO_HZ_FULL build, and by when. Source: the SVK contact (A6).</li>
<li>Whether the performance governor plus a pinned device thread brings the device's mean lateness under 2.5 µs. Measurement: govtest-1 and govtest-2, then a run with the SDK-side change (D5).</li>
<li>Clock stability over a full run under the performance governor. Measurement: the feedback-counter pair in P3 around a 3-minute run.</li>
<li>Console or BMC access for the reboot, the meaning of EFI boot entry 0010, and whether the second disk holds another operating system. Source: the administrator (A3).</li>
<li>What <code>/etc/sudoers.d/positron-perf-setup</code> grants. Source: the administrator (A4).</li>
<li>Who operated alpha during the staging, and which key each of Jeremy's sessions used. Sources: Jibin (A2) and the system journal (A10).</li>
<li>Whether the sampling unit tests were ever run on the host, and the timed compile's wall time. Source: Jeremy (Q9).</li>
<li>Whether booting the stock 6.8.0-147 kernel on this board works. Not recommended to test before the demo.</li>
<li>Hypothesis, not measured: transparent huge pages are set to “always” with a background collapse scan every 10 s, which can stall a faulting harness thread for hundreds of microseconds on a housekeeping CPU. Measurement: the <code>thp_collapse_alloc</code> counter in <code>/proc/vmstat</code> before and after a run. Mitigation on Jeremy's side: <code>prctl(PR_SET_THP_DISABLE)</code> in the harness, no root needed.</li>
</ul>
</section>""")

A("""<footer>Prepared for Jibin on 21 October 2026, revised 22 October 02:40 UTC. Standalone HTML, light theme, inline SVG figures. Figures follow the dataviz palette (categorical blue/orange, ordinal blue ramp validated for light surfaces). No message has been sent to Jeremy by this document. The draft in section 4 is for Jibin to send.</footer>""")

doc = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Jeremy's phoenix-crb tasks: plan</title><style>" + CSS + "</style></head><body><main>" + "\n".join(parts) + "</main></body></html>\n"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print("wrote", OUT, len(doc), "bytes")
