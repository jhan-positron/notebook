---
name: 3bda-shared-with-bill
description: "Bill shares delphi-3bda with jhan 2026-09-05..07 (Sat-Mon); Sunday 2026-09-06 PDT is a full blackout (jhan promised Bill no use at all); guard = other_user_active + blackout_active (file /var/tmp/jhan/3bda-blackout) in exec/lib-guard.sh"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a757d7f-8c84-4b08-a4b0-595e23118332
  modified: 2026-09-05T03:43:39.188Z
---

jhan, Fri 2026-09-05 20:36 PDT: Bill (account `bill` on delphi-3bda, uid 1062305141, a
directory-service account) will split delphi-3bda with jhan on Saturday, Sunday and Monday
(2026-09-06 to 09-08). Rule: in addition to the CI lease, check whether Bill is ACTIVELY using
the machine before taking it; an open but idle login (shell, tmux, editor) is fine to take over.

Implementation (exec/lib-guard.sh, 2026-09-05, backup lib-guard.sh.bak-20260905):
- `other_user_active`: samples utime+stime of every process owned by a uid >= 1000 over
  GUARD_OTHER_SAMPLE_SEC (default 10 s); ACTIVE if > GUARD_OTHER_CPU_SEC (default 2.0 CPU-s,
  i.e. 0.2 core) or if the user owns a tron/build process (rinzler, runtron*, gen*/ test
  binaries amx_*/t_*, ninja, cmake, make, cc1plus, ld, clang, gcc, perf). Users are discovered
  from process ownership because `getent passwd` cannot enumerate directory accounts.
  Excluded by default: jhan, nobody, positron, packer (GUARD_EXCLUDE_USERS); processes inside a
  rinzler@*.service cgroup are skipped (covered by the lease and rinzler_active). One report
  line per user to stderr ("GUARD other-user bill: ACTIVE (...)" / "idle (...)").
- `campaign_guard_acquire` refuses when other_user_active is true.
- `ci_took_dut` (used between runs by ~30 campaign scripts) now = ci_lease_busy || other_user_active;
  `dut_contended` is the same by a truthful name; `wait_for_dut_free` polls both.
- Verified live 2026-09-05 03:55 UTC: nobody-present path, idle-login path (positron sshd/bash),
  CPU path (1-core burner as jhan -> ACTIVE), heavy-name path (process named runtron.guardtest
  -> ACTIVE), and recovery after the test processes ended.

**Why:** Bill's work (single-K measurements per his note) and jhan's PR-split campaigns both need
the AMX host; a guard that only knows about CI would launch on top of his runs.
**How to apply:** nothing new to call: source lib-guard.sh, use campaign_guard_acquire, re-check
ci_took_dut between runs as before. If Bill's idle session holds hugepages or a stopped rinzler,
the guard will not see it (it looks at CPU and process names only); check `ps -u bill` by hand
before long campaigns. Related: [[delphi-3bda-hardware]], [[breakup-pr3879-plan]].

UPDATE 2026-09-05 05:30 UTC (jhan): "I told Bill I will not use 3bda tomorrow, Sunday." Read as
Sunday 2026-09-06 Pacific = 2026-09-06T07:00Z to 2026-09-07T07:00Z (calendar check: 2026-09-04 is
a Friday, so Sat = 09-05, Sun = 09-06, Mon = 09-07; the plan page's "Fri 09-05" labels are off by one).
Mechanism: lib-guard.sh `blackout_active` reads /var/tmp/jhan/3bda-blackout ("start_epoch end_epoch
note" lines); it is part of ci_took_dut/dut_contended (wait loops wait) and campaign_guard_acquire
(refuses). The Sunday window is registered there. exec/sunday-killer-20260906.sh (running on 3bda,
setsid) TERMs/KILLs the split chain's process group at 07:00Z 09-06 and writes
exec/logs/split-SUNDAY-STOP.marker. The monitor makes no ssh liveness checks during the window.
Delete the blackout file after Monday if no other window is wanted.

CORRECTION 2026-09-05 05:40 UTC (jhan): "my bad, I meant Saturday which is tomorrow ... please hold using the
machine. I will sync with Bill tomorrow night." So: NO use of delphi-3bda from now (Sat 2026-09-05 PDT) until
jhan says so. The split chain was killed before it built anything; the Sunday stopper was removed; the blackout
file now reads start=now, end=2026-09-07T07:00Z (placeholder; jhan lifts it). Resume with
exec/split-relaunch.sh after deleting/shortening /var/tmp/jhan/3bda-blackout on 3bda.

UPDATE 2026-09-06 05:50 UTC: jhan lifted the hold conditionally (Sat 22:4x PDT): use 3bda after the 2026-09-06 nightly CI ends
if people-check.sh (exec/people-check.sh, procedure in ~/workspace/notebook/handoffs/share-3bda-with-bill.md) says FREE.
The Sunday blackout line is to be deleted at that point. Bill's state at 05:42Z: one idle python3 prompt, tty idle 6 h 43 min.

UPDATE 2026-09-06 21:3x UTC (jhan): "stop the monitor, we are to use new strategy". The people-check procedure (share-3bda-with-bill.md)
and the blackout file are superseded; the new sharing scheme is jhan's to state. Until then: no launches on 3bda. Bill ran eoe_engine
load (8 then 4 processes, all hugepages) from ~15:56Z through at least 21:25Z on Sunday 2026-09-06.

UPDATE 2026-09-06 22:25 UTC — NEW SCHEME (jhan, via ~/workspace/notebook/handoffs/delphi-3bda-guard.md): the machine is split by
halves, no time-sharing. Bill = first four FPGA cards (10:00.0, 13:00.0, 38:00.0, 3b:00.0) = socket 0 = slices 0-3 = cpus 0-71,144-215.
jhan = second four cards (90, 93, b9, bc) = socket 1 = slices 4-7 = cpus 72-143,216-287 = SYSTEM_CONFIG="--instance 1,2" (set by
~/delphi-3bda-setup.sh, sourced by every ssh shell incl. non-interactive). Whole-machine measurements only when Bill is not using the
machine. Two fixes named by the doc: (1) 30 exec/*.sh campaign scripts pass `--instance 0,4 --devices 10:00.0,13:00.0` (Bill's cards) —
NOT yet changed (list: grep -l -- '--devices 10:00.0,13:00.0' exec/*.sh); change to `--instance 2,4 --devices 90:00.0,93:00.0` before
reuse. (2) DONE 2026-09-06 22:20Z: `export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"` appended to ~/delphi-3bda-setup.sh
(backup .bak-20260906), so other_user_active ignores Bill; CI lease and third persons still block.
Consequences learned for the split chain (exec/split-verify3.sh, split-bench3.sh, split-relaunch3.sh): pin builds/tests to socket 1
(taskset -c 72-143,216-287); run `fake` tests WITH SYSTEM_CONFIG="--instance 1,2" (pos_fake's pos_startup only parses it for the core
set; no hugepage file is touched — the real driver's pos_heap_setup would, and WITHOUT an instance it deletes every unlocked
/dev/hugepages/slice-*-of-8 file: never run a real-driver tron binary on 3bda without --instance); `bin/slice bench --update` launches
tests under --instance i,n for every slot (both sockets), so it is a whole-machine measurement: run it only when Bill is idle (bench3 uses
the default GUARD_EXCLUDE_USERS). Advisory pre-CI hold in the chain: no step starts between 02:10 and 03:45 UTC (prep 02:45, lease ~03:37).

CORRECTION 2026-09-07 (verified in tron src/pos/driver.cpp pos_startup_host + src/system/system.cpp system_parse_env at 9723d56f62): the
guard doc's claim "a command-line --instance wins over SYSTEM_CONFIG" is wrong for placement. runtron applies argv first, then SYSTEM_CONFIG
unconditionally; "--instance 1,2" from the login env replaces --devices/--app-cores/--dev-cores/--numa. Consequences: (1) scripts that pin
cards/cores on the command line must `env -u SYSTEM_CONFIG`; (2) the 30 campaign scripts pinning Bill's cards would silently be re-placed onto
our half (instance 1,2, 4 cards) since fix 2 exported the variable. Tell jhan; fix the doc sentence.

UPDATE 2026-09-15 (jhan + Bill, Slack DM D0AVD4EG675 10:19-11:03 PDT; jhan confirmed the two open points 2026-09-15 ~16:05 PDT):
MARKER-FILE PROTOCOL for the half split. Bill: "Starting this weekend, I've been using your box less. I'll only continue to use [instance
0,2] if you're not using it at all." jhan: "my harness is configured to use 2nd half. If I need whole machine, I will request to you."
Bill: "create a file /bill-has-instance-0,2? I'll tell my agent to avoid using it if its not there." Rules:
- marker /bill-has-instance-0,2 present on delphi-3bda = Bill's agent may use the first half (instance 0 of 2); absent = whole machine ours.
- Our second-half campaigns ignore the marker. Whole-machine work only after jhan says so; Claude never removes the marker on its own.
- "take" (remove the marker) is refused while Bill is active, judged by the EXISTING lib-guard.sh other_user_active restricted to user bill
  (jhan's choice, not by asking him first); then jhan asks Bill. After our whole-machine work ends WE re-create the marker ("release").
- Tool: exec/bill-share.sh status|take|release (run on 3bda, e.g. `ssh delphi-3bda bash ~/workspace/intel-AMX/exec/bill-share.sh status`);
  log exec/logs/bill-share.log; tests exec/lib-guard-tests/test-bill-share.sh (11 cases). Needs passwordless sudo for touch/rm in /.
- STATE 2026-09-16 03:59 UTC: marker CREATED by jhan (`! ssh delphi-3bda bash ~/workspace/intel-AMX/exec/bill-share.sh release`, logged
  in exec/logs/bill-share.log). Claude's own attempt was refused by the auto-mode classifier ("Modify Shared Resources"), so marker
  changes on 3bda are for jhan to run by hand; Claude checks with `status` (read-only) and reports.
- delphi-3bda was down 2026-09-15 ~22:3x-23:54 UTC (no shutdown record in `last -x`, so a hard reset or power event after 12.9 days up);
  jhan asked #hardware-systems (C076BH9TB2L) at 15:46 PDT; keveritt logged in at 23:56 UTC; jhan marked the outage resolved 2026-09-16 04:1x UTC. After the reboot:
  no lease file, rinzler@0-3 inactive, HugePages_Total 264 (512 was seen while the nightly ran, so CI may set it itself).


Index detail moved here 2026-09-18 (was only in MEMORY.md): 2026-09-15 MARKER PROTOCOL: /bill-has-instance-0,2 present = Bill may use first half; exec/bill-share.sh status|take|release (take refused while other_user_active says bill ACTIVE; jhan decides whole-machine; we re-create after); marker not yet created (3bda down). NEW SCHEME 2026-09-06: half split (Bill cards 10/13/38/3b + socket 0; jhan cards 90/93/b9/bc + socket 1 = --instance 1,2); GUARD_EXCLUDE_USERS includes bill (applied); bench = whole-machine -> only when Bill idle; 30 campaign scripts still pin Bill's cards; never run a real-driver tron without --instance (deletes unlocked slice files)
