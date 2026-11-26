---
name: crb-ssh-login-first-command
description: "How to reach CRB by ssh from the agent session (it runs as root, so name the user and the key), and what the first read-only command of a login must check"
metadata:
  node_type: memory
  type: reference
  originSessionId: b662db86-cbfe-4b4a-a59a-37f11dacb0e7
  modified: 2026-11-25T05:37:05.172Z
---

The agent session on the Linux server runs as root with HOME=/home/jhan. A plain `ssh 192.168.2.45` tries `root@` and fails with "Permission denied". This command worked on 2026-11-20:

`ssh -o BatchMode=yes -o ConnectTimeout=10 -i /home/jhan/.ssh/id_ed25519 jhan@192.168.2.45 '<commands>'`

Before the login: read Slack #phoenix-crb (id C0C1R7XEVU6) for a block announced by Jeremy Conner ("Jeremy's Claude here: CRB block ..."). His notices came 1 h to 5.5 h before the block start (five notices, 2026-11-13 to 2026-11-19). During a block: no login at all.

First command of a login, all without sudo:
- `ls /tmp/positron-perf.RUNNING` (Jeremy's run marker; if it exists, start nothing and log out)
- `cat /proc/loadavg` and `ps -eo user= | sort | uniq -c` (Jeremy's account is `positron-perf`)
- `grep MemTotal /proc/meminfo` (12 modules: about 395392804 kB), see [[crb-check-dimm-count-every-use]]
- `uptime -s` and `cat /proc/sys/kernel/random/boot_id` (tells whether the board rebooted since the last session)

Root: the account `jhan` has `sudo` without a password since 2026-11-02 (`crb/plan-2026-11-02.md` line 203: "Jibin made sudo passwordless"; the inspection record of 2026-10-30 still says that a password is needed). So `sudo -n` works from a session, but each root command still needs the user's approval for the task. The five block notices of 2026-11-23 and 2026-11-24 came 1.2 h to 7.6 h before the block start, and blocks also run at night (for example 04:00 to 07:32 UTC), so read the channel right before each login.

A login shell there is limited to CPUs 0-119 (`Cpus_allowed_list`), so `nproc` prints 120, not 128. This is not a change of the boot options.

Rules for sharing the board: `crb/jeremy-plan-constraints-2026-10-30.md`. A CRB login needs the user's authorization, see [[minor-design-readings-decide-not-ask]]. Related: [[crb-pcie-die-crossing-request-2026-11-20]].
