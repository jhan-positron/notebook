# Merged record: Jeremy's Phoenix CRB work and our cache/DRAM benchmark runs

Short version: Neither `sudo dmidecode -t 17` nor a live change of `kernel.perf_event_paranoid` touches anything the documents say Jeremy's counted runs depend on. The only documented way either action can hurt him is the login and process activity itself during an announced block (weekdays 13:00-21:00 UTC, marked by `/tmp/positron-perf.RUNNING`). The documents never discuss shared L3 or DRAM traffic between CPUs 0-119 and 126-127, so that risk is covered only by the whole-host quiet rule during blocks.

## Words used here

- CRB / phoenix-crb: the Arm "Phoenix Reference Server" at 192.168.2.45, hostname `ubuntu`, 128 CPUs [jeremy-tasks.html:6] [jeremy-tasks-plan.html:23].
- Jibin: the host administrator. The documents state that `jhan` (jhan@positron.ai, the current user) is Jibin's own account [jeremy-tasks-plan.html:24] [jeremy-tasks-plan.html:29].
- positron-perf: Jeremy's unprivileged test account (uid 1001, SSH keys, no usable sudo) [jeremy-tasks-plan.html:27].
- arm: the shared admin account of the other engineers [jeremy-tasks-plan.html:135] [phoenix-crb-evidence-2026-10-21/t3-access-details-2026-10-22.txt:6].
- churn run: Jeremy's counted latency test, `tools/conformance/churn.py` plus `latency_judge.py`, gate name `per-user-latency.qwen3_5_0_8b.P-TP1` [jeremy-tasks-plan.html:38].
- block: a reserved whole-host window in which Jeremy runs measurements and one churn run [jeremy-tasks-plan.html:276].
- RUNNING file: `/tmp/positron-perf.RUNNING`, present for the whole block [jeremy-tasks-plan.html:276].
- IPI: inter-processor interrupt, a cross-CPU interrupt. A login sends two to every core (measured) [jeremy-tasks-plan.html:245] [jeremy-tasks-plan.html:421].
- CPPC feedback_ctrs: firmware clock counters read via sysfs, not Linux perf [jeremy-tasks-plan.html:51].
- isolcpus: a boot setting that keeps the scheduler off listed CPUs; here 126-127 [jeremy-tasks-plan.html:519].
- SMBIOS / DMI: firmware tables that describe the hardware; `dmidecode -t 17` prints the memory-device table.
- perf_event_paranoid: the sysctl that controls who may open hardware performance counters; value 2 on this host [jeremy-tasks-plan.html:445].

## Document precedence

Timestamps: jeremy-tasks.html (21 Oct 18:40) < phoenix-crb-for-jeremy-2026-10-22.html (22 Oct 11:55) < jeremy-tasks-plan.html (22 Oct 12:11). Where they disagree, jeremy-tasks-plan.html wins, then for-jeremy, then jeremy-tasks. The `phoenix-crb-evidence-2026-10-21/` text files are source material cited where the HTML files lack a fact.

## A. Who Jeremy is, what he runs, where it is pinned

- Jeremy Conner is the SDK-side requester. His messages are written by "Jeremy's Claude" [jeremy-tasks-plan.html:25] [jeremy-tasks-plan.html:78].
- Account: positron-perf, uid 1001, no usable sudo [jeremy-tasks-plan.html:27] [phoenix-crb-for-jeremy-2026-10-22.html:8]. Conflict: the reply to Jeremy says "both user ID positron-perf and arm have sudo access" [phoenix-crb-evidence-2026-10-21/reply-to-jeremy-2026-10-22.txt:8-9]. The newer HTML (tasks-plan) says no usable sudo, so this record keeps "no sudo" and flags the sentence in the reply as a likely error.
- Counted job: the churn label, launched by `taskset -c 120-125 taskset -c 120-125,127 ... bash tools/ci/run_scheduled_gate.sh churn` [jeremy-tasks-plan.html:67] [jeremy-tasks-plan.html:547-549]. One churn run takes about 3 min [jeremy-tasks-plan.html:510]; churn-r1 took 172.9 s [jeremy-tasks-plan.html:455].
- Since 22 Oct a block also includes an import-hf build, a timed compile, memory-bandwidth, hashing and fio disk steps, then the churn run [jeremy-tasks-plan.html:457]. Block measurements run on CPUs 0-125, 126-127 untouched, up to 32 GiB of temp files [jeremy-tasks-plan.html:276].
- Pinning: pass thread on CPU 127, fake-device thread on CPU 126, other harness threads on 120-125 [jeremy-tasks-plan.html:231-233] [jeremy-tasks-plan.html:261]. Builds and untimed tests on cores 0-95 at any time outside a RUNNING file [jeremy-tasks-plan.html:263].
- Superseded: jeremy-tasks.html proposed isolating 120-127 with the pass thread on 120 [jeremy-tasks.html:9] [jeremy-tasks.html:89]. The applied state is isolcpus 126-127 [jeremy-tasks-plan.html:519] [phoenix-crb-for-jeremy-2026-10-22.html:20].
- Linux perf is not in the counted path. "tools/perf" in the documents is an SDK directory for a later host-timing gate, not 5 Nov [jeremy-tasks-plan.html:260] [phoenix-crb-evidence-2026-10-21/requests.txt:41].
- Deadline: demo Thursday 5 November 2026 [jeremy-tasks-plan.html:595].

## B. Schedule and the quiet-host rule

- First counted block: Fri 23 Oct 13:00-16:00 UTC [jeremy-tasks-plan.html:276].
- Further blocks: "one next week, then one or two before 5 Nov", each posted at least 2 h ahead in the phoenix-crb channel [jeremy-tasks-plan.html:263]. Exact dates are not in any document.
- Standing window: counted runs only Mon-Fri 13:00-21:00 UTC (06:00-14:00 PDT until Fri 30 Oct, 05:00-13:00 PST from Mon 2 Nov). "No announcement means no block." [jeremy-tasks-plan.html:342-345].
- Rule during a block: do not log in at all. Stop builds, screen and tmux sessions, log out. If the RUNNING file exists, start nothing and log out. Do not remove the file [jeremy-tasks-plan.html:346-350].
- Why: any activity, even a login, disturbs a run. A login sends two IPIs to every core [jeremy-tasks-plan.html:245] [jeremy-tasks-plan.html:421].
- Pre-run checklist Jeremy's side uses: load below 0.5, no other user above 5% CPU [jeremy-tasks-plan.html:636] [jeremy-tasks-plan.html:643].
- Outside blocks the host is free as usual [jeremy-tasks-plan.html:350].
- Superseded: jeremy-tasks.html said "A nightly window is fine" and counted runs from 26 Oct [jeremy-tasks.html:55] [jeremy-tasks.html:11]. The newer rule (weekday daytime UTC blocks) wins.
- Jibin was away 22 Oct to about 29 Oct [jeremy-tasks-plan.html:356]. Today is 30 Oct, so that period has ended.

## C. perf, PMU, perf_event_paranoid, DMI in the documents

- `kernel.perf_event_paranoid = 2` is recorded as an inspection fact: "user-space counters work, no system-wide profiling" [jeremy-tasks-plan.html:445] [phoenix-crb-evidence-2026-10-21/phoenix-crb-inspection.txt:853].
- The same line says the SDK runtime uses only affinity calls and one timer-slack call, "so no limit change is needed today" [jeremy-tasks-plan.html:445] [jeremy-tasks-plan.html:463].
- No document says any Jeremy tool reads perf_event_paranoid or opens a perf event. The clock check is one CPPC pair before and after a run, nothing read during it [phoenix-crb-evidence-2026-10-21/requests.txt:45] [jeremy-tasks-plan.html:292].
- `/usr/bin/perf` is installed; its ownership was fixed to root on 22 Oct [jeremy-tasks-plan.html:446] [jeremy-tasks-plan.html:20]. The plan "never runs sudo cpupower or sudo perf" [jeremy-tasks-plan.html:20]. That was a precaution before the ownership fix; the documents do not restate it as a rule for others.
- dmidecode, SMBIOS, /sys/firmware/dmi: no plan text mentions them. The inspection has a "firmware (dmi)" inventory block only [phoenix-crb-evidence-2026-10-21/phoenix-crb-inspection.txt:523-524]. jeremy-tasks.html and for-jeremy.html have no match for perf_event, paranoid, PMU, dmi, smbios.

## D. Rules for other accounts and the contact path

- Do not change boot settings, install packages, re-enable timers or reboot. A reboot keeps the settings but kills a run [jeremy-tasks-plan.html:353-354].
- Never pin anything to 126-127 [jeremy-tasks-plan.html:351] [phoenix-crb-for-jeremy-2026-10-22.html:70].
- Do not run snap, unshare, podman, systemd-run or any service restart during a counted run [jeremy-tasks-plan.html:646] [phoenix-crb-for-jeremy-2026-10-22.html:38].
- Do not read `feedback_ctrs` or `cpuinfo_cur_freq` of CPU 126 or 127 during a run (two to four IPIs per read) [phoenix-crb-for-jeremy-2026-10-22.html:38].
- "Nothing on the host changes before" the 5 Nov demo [jeremy-tasks-plan.html:595]. Promise to Jeremy: "nothing expires, nothing changes" [phoenix-crb-evidence-2026-10-21/reply-to-jeremy-2026-10-22.txt:21].
- No document names sysctl changes, governor changes by others, or memory traffic as forbidden.
- Contact: the phoenix-crb channel [jeremy-tasks-plan.html:184] [jeremy-tasks-plan.html:356]. Whether the note to other users was posted is not in the documents (T2/T3 "to do" as of 22 Oct 18:30 UTC) [jeremy-tasks-plan.html:13-14].
- Superseded: jeremy-tasks.html had no rule for other accounts and no channel name [jeremy-tasks.html:33] [jeremy-tasks.html:150].

## E. Jibin and the jhan account

- jhan is a second administrator account (uid 1002, group sudo), confirmed as Jibin's own [jeremy-tasks-plan.html:29] [phoenix-crb-for-jeremy-2026-10-22.html:8]. All root steps of 22 Oct ran from jhan [jeremy-tasks-plan.html:28].
- Superseded: jeremy-tasks.html recorded "sudo: a password is required" for jhan and linked Jibin to jhan only by juxtaposition [jeremy-tasks.html:228-233] [jeremy-tasks.html:24]. The sudo group membership is the newer fact.
- So the current user (jhan) is the host administrator who wrote these documents and set these rules.

## F. Cache, memory bandwidth, other load

- Jeremy's own block includes memory-bandwidth and fio disk steps on CPUs 0-125, run before the churn run, not concurrently [jeremy-tasks-plan.html:457] [jeremy-tasks-plan.html:276].
- STREAM, DRAM latency, L3 sharing: not in any document. "cache" appears only as a TLB definition [jeremy-tasks-plan.html:55] and as inventory (L3 128 MiB, 1 instance) [phoenix-crb-evidence-2026-10-21/phoenix-crb-inspection.txt:75-78].
- The noise model in all three documents is CPU scheduling, interrupts, timers, clock frequency, logins [jeremy-tasks.html:64] [jeremy-tasks-plan.html:245].
- Conflict: jeremy-tasks.html treats LSF workers as noise on the host [jeremy-tasks.html:43]; tasks-plan says no LSF, CI runner, Docker or container runtime runs on the host [jeremy-tasks-plan.html:438]. Newer wins: the LSF workers are elsewhere.
- netperf was stopped 22 Oct; stress-ng is installed system-wide [jeremy-tasks-plan.html:434] [jeremy-tasks-plan.html:446].

## G. Root changes made and who may make more

- All by Jibin from jhan on 22 Oct UTC: linux-tools chown ~05:25; 11 timers disabled and netperf stopped 05:30-05:33; `rcu_normal=1` and systemd `CPUAffinity=0-119` drop-in 05:34; performance governor on all 128 policies 05:36; GRUB drop-in `isolcpus=domain,managed_irq,126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1`, update-grub, reboot 05:43 [jeremy-tasks-plan.html:189-194] [jeremy-tasks-plan.html:519].
- No sysctl file change is recorded; perf_event_paranoid stayed 2 [jeremy-tasks-plan.html:445].
- Superseded: jeremy-tasks.html says no change was made [jeremy-tasks.html:37]; that was true on 21 Oct only.
- Rule: boot settings, packages, timers, reboot are off limits until after 6 Nov [jeremy-tasks-plan.html:353-354] [jeremy-tasks-plan.html:596-601]. No document assigns or forbids live sysctl writes.

## Verdict: would `sudo dmidecode -t 17` or relaxing perf_event_paranoid impact Jeremy?

### (1) What the documents literally support

- No document ties Jeremy's counted path to SMBIOS, DMI, Linux perf, PMU counters, or perf_event_paranoid [jeremy-tasks-plan.html:38] [jeremy-tasks-plan.html:445] [jeremy-tasks-plan.html:463].
- The value 2 is recorded as a fact with "no limit change is needed today", not as a requirement [jeremy-tasks-plan.html:445].
- The host-state checks Jeremy's side re-verifies are the boot line, isolated list, governor, rcu_normal, timers and the RUNNING file [jeremy-tasks-plan.html:17] [jeremy-tasks-plan.html:578]. A sysctl is not among them.
- The forbidden list for others is boot settings, package installs, timers, reboot, and any login or process during a block [jeremy-tasks-plan.html:353-354] [jeremy-tasks-plan.html:346-350]. A sysctl write and a dmidecode read are not on it.
- The one documented impact mechanism is the login itself: two IPIs on every core per ssh login, forbidden during a block [jeremy-tasks-plan.html:245] [jeremy-tasks-plan.html:346].
- Two softer statements apply: "nothing expires, nothing changes" [phoenix-crb-evidence-2026-10-21/reply-to-jeremy-2026-10-22.txt:21] and "Nothing on the host changes before" the demo [jeremy-tasks-plan.html:595]. A persistent perf_event_paranoid change is within the spirit of those, though outside the letter.

Literal answer: outside an announced block, no documented impact. During a block, both are forbidden because they need a login.

### (2) Inference from general Linux knowledge (labelled as such)

- Inference: `dmidecode -t 17` reads the SMBIOS tables through `/sys/firmware/dmi/tables` and writes nothing. It runs for well under a second. It changes no kernel state. Its only footprint is the login and one short process on a CPU in 0-119 (login shells are pinned to 0-119 by the systemd drop-in [jeremy-tasks-plan.html:180]).
- Inference: writing `kernel.perf_event_paranoid` changes only the permission check inside `perf_event_open`. It changes no scheduling, tick, interrupt routing, governor or isolation state. A write via `sysctl -w` does not survive a reboot. A file under `/etc/sysctl.d/` does survive and is a persistent configuration change; that is closer to "boot settings" in spirit, so post it in the channel if done.
- Inference, the real caution: the risk is not the sysctl but how we then use perf. A system-wide session (`perf stat -a`, `perf record -a`, or uncore/CMN PMU events for L3 and DRAM counters) installs events on every CPU, including 126-127, and sends IPIs to them at start, stop and each read. A per-task session on processes pinned to 0-119 touches only those CPUs. Value 2 already allows per-task user-space counters; a change to 0 or -1 is needed only for system-wide or uncore counters. So: keep perf per-task, or run system-wide perf only outside blocks.
- Inference: the ownership fix on 22 Oct makes `/usr/bin/perf` root-owned [jeremy-tasks-plan.html:503], so the "never sudo perf" precaution in the plan no longer has its original reason. Running perf as jhan with the relaxed sysctl, without sudo, is the lower-risk form.

## Constraints for our cache/DRAM benchmark runs

Time windows to avoid:
- Any announced block, Mon-Fri 13:00-21:00 UTC (05:00-13:00 PST from Mon 2 Nov) [jeremy-tasks-plan.html:342-345]. Blocks are announced 2 h ahead in the phoenix-crb channel; "one or two before 5 Nov" remain, dates unknown [jeremy-tasks-plan.html:263].
- Before any work, run `ls /tmp/positron-perf.RUNNING`. If it exists, start nothing and log out [jeremy-tasks-plan.html:588].
- Our runs must be stoppable with 2 h notice, since the rule is "before a block starts, stop or finish anything of yours still running ... and log out" [jeremy-tasks-plan.html:346-348]. Someone must watch the channel while a long sweep runs.
- Safest window: weekdays 21:00-13:00 UTC and weekends, where no counted run can occur [jeremy-tasks-plan.html:342].

CPUs to avoid:
- 126-127: isolated, never pin to them [jeremy-tasks-plan.html:351]. Login shells are already restricted to 0-119 [jeremy-tasks-plan.html:180].
- 120-125: not forbidden outside a block, but they are Jeremy's harness CPUs during one [jeremy-tasks-plan.html:261]. The user's choice of 0-119 is consistent with the documents.
- Builds on 0-95 are shared with other engineers [jeremy-tasks-plan.html:322]; an all-core sweep on 0-119 will slow their builds. The documents do not forbid this.

Things not to do:
- Do not change boot settings, install packages, re-enable timers, or reboot [jeremy-tasks-plan.html:353-354].
- Do not change the cpufreq governor (performance on all 128 CPUs, also on the boot line) [jeremy-tasks-plan.html:519].
- Do not read `feedback_ctrs` or `cpuinfo_cur_freq` of 126 or 127 during a run [phoenix-crb-for-jeremy-2026-10-22.html:38].
- Do not run snap, unshare, podman, systemd-run or service restarts during a counted run [jeremy-tasks-plan.html:646].
- Do not remove the RUNNING file [jeremy-tasks-plan.html:349].
- Inference: do not run system-wide perf (`-a`, uncore events) during a block, even if we are otherwise off the host; it would IPI 126-127.

Announcements to make:
- Post in the phoenix-crb channel [jeremy-tasks-plan.html:184]. The documents require announcements from Jeremy, not from us, but Jeremy's pre-run check needs load below 0.5 and no other user above 5% CPU [jeremy-tasks-plan.html:636] [jeremy-tasks-plan.html:643]. A long sweep that overlaps his planned start blocks him. Posting our sweep times avoids that.
- Inference: post a one-line note if perf_event_paranoid is changed, with the old value (2) and the restore plan, to honour "nothing changes" [phoenix-crb-evidence-2026-10-21/reply-to-jeremy-2026-10-22.txt:21]. Restore 2 after our runs, or at the latest before 5 Nov.

Memory and cache traffic interfering with Jeremy's latency runs:
- The documents do not address shared L3 or DRAM between CPUs 0-119 and 126-127. The noise model is CPU scheduling, IPIs, timers and clock only [jeremy-tasks-plan.html:245] [jeremy-tasks.html:64].
- The whole-host quiet rule during a block makes the question moot for counted runs: we are off the host then [jeremy-tasks-plan.html:346-350].
- Jeremy's own block runs memory-bandwidth steps on 0-125 before the churn run, not during it [jeremy-tasks-plan.html:457]. So his own design keeps DRAM traffic out of the counted 3 min, which supports (inference) that an all-core sweep on 0-119 concurrent with a churn run would disturb it through the single 128 MiB L3 and DRAM.
- Insufficient data: whether Jeremy runs uncounted timing runs outside blocks (smoke runs on CPUs 0-7 are recorded [jeremy-tasks-plan.html:66]) that he still reads for trends. A sweep concurrent with those would skew them. The channel is the way to find out.