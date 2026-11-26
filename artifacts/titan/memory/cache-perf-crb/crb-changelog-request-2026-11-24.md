---
name: crb-changelog-request-2026-11-24
description: "User wants one shared changelog of all changes to CRB, owned by Jeremy, the user and whoever works on CRB (asked 2026-11-24). My proposal, the facts behind it, the changes on record so far, and what I must do after any change to CRB"
metadata:
  node_type: memory
  type: project
  originSessionId: 9b54dcc5-d417-461d-9dcc-1710acea784e
  modified: 2026-11-26T01:05:21.024Z
---

User, 2026-11-24 (third message after the hardware-record work): "We have done changes to CRB, we should maintain a changelog of all the changes, and Jeremy and I and whoever working on CRB need to own it. Please suggest a solution".

State at the end of that session: I gave a proposal in the chat. The user has not chosen yet. Nothing was created or posted in Slack.

**Why:** changes to CRB were recorded in three ways so far: a channel message, only the user's private files, or nowhere. The admin account `arm` on CRB is shared (password in 1Password, user's Slack message of 2026-10-22), so Linux cannot name the person.

**How to apply:** after any change that I make on CRB (root command that changes state, firmware setting, reboot, package, file outside the home folder, per-boot state such as `chmod` of a device file or telemetry switched on), write down time (UTC), command, reason, how long it lasts and how to undo it, and report it to the user as a changelog entry. Once the user has chosen the place, write the entry there. Do not post in `#phoenix-crb` and do not create a canvas without the user's word.

My proposal (my design, not agreed):
- Notice = record: one message in `#phoenix-crb` (id C0C1R7XEVU6) before the change, first words `CRB change:`, fields what / why / until / undo. Slack adds author and time.
- One Slack canvas "CRB changelog" as the list: a table "State now" and a table "Log" (one row per notice, with the fields repeated and a link).
- A no-root state check at each session start (boot time, boot line, MemTotal, firmware version, device list, access rights of `/dev/scmi`, timers, packages) that finds changes without a notice. Not built.
- Owner of an entry: who makes the change. Owners of the rule: the user and Jeremy, each through the standing instructions of their agent.
- Not chosen: a file on CRB (not readable when the board is off or during a block), a shared git repository (none exists for CRB; hardware people would have to commit), NetBox (company inventory with a reservation system; Mitchell Stokes proposed on 2026-11-06 to add CRB; not checked whether it is in).

Facts read on 2026-11-25 05:2x UTC:
- `#phoenix-crb` is a public channel, created 2026-09-14 by Dan McDermott. No pinned message, no message with "changelog". People who post about the board: Jeremy Conner (blocks, through his Claude), the user, adam, Jacob Geldbach, John Mark Wilkinson, Dan McDermott, William Baumann, Mitchell Stokes.
- Slack still shows a message of 2026-04-14, so there is no 90-day limit on history. The canvas tool says "Not available on free teams". Whether a canvas can be created was not tried.
- `jhan` on CRB has `sudo` without a password since 2026-11-02 (`crb/plan-2026-11-02.md` line 203).

Changes on record (sources in brackets), as given to the user:
- 2026-10-22 05:25 to 05:43 UTC, the user: boot line (`isolcpus=...126-127`, `irqaffinity=0-119`, governor `performance`, `rcu_normal=1`), systemd `CPUAffinity=0-119`, 11 timers disabled, netperf stopped, owner of linux-tools fixed, one reboot (`crb/jeremy-plan-constraints-2026-10-30.md` line 82). Timers "paused until 6 Nov" (Slack 2026-10-22): no record after that.
- 2026-11-02: passwordless `sudo` for `jhan`.
- 2026-11-06 to 11-09, adam: three network cards tried, board lost power, host not reachable (Slack).
- 2026-11-17 about 03:45 to 04:20 UTC, my session with approval: firmware "CPU TXREQ Throttle" changed and set back, 4 reboots (`~/workspace/machines/arm-crb/DIMM-flaky-report.md` lines 139 to 140).
- 2026-11-17 19:43 UTC: "DIMM Frequency" 8000 to 7200 MT/s, 6 reboots, left in force (same report, lines 171 to 173 and 238).
- 2026-11-19 01:04 UTC: a reboot, by whom not on record (see [[crb-whole-chip-rerun-7200-2026-11-17]]).
- 2026-11-23 about 20:00 UTC, adam and Jacob Geldbach: network card tried again with Arm's workaround, "did not work" (Slack). Card state and boot after it: no record.
- Read on CRB on 2026-11-26: the present boot started 2026-11-23 20:04:08 (boot id a8535c1e-56cc-42a8-85b7-426bf569d3c9). That is 4 minutes after the start of Jeremy's block of that day and during the card trial. Who started it is not on record.
- 2026-11-26 00:58:26 UTC, my session with the user's approval: `chmod 666` on `/dev/scmi/tlm_0` and `tlm_1`, through Arm's script `setup_arm_agi_cpu_telemetry.sh --interface ioctl`. It lasts until the next reboot. Undo: `sudo chmod 600` on both files. No change of the firmware: its telemetry is on from boot (kernel log), and the state after our tools was byte-equal to the state before. The user decided on 2026-11-25 that no message to Jeremy is needed ("Add the 3 steps. So no need to ping Jeremy."). I gave the entry to the user in the chat. The place of the changelog is still not chosen (see [[crb-hw-record-2026-11-24]]).

Related: [[crb-ssh-login-first-command]], [[crb-hw-record-2026-11-24]], [[crb-memory-module-count-varies-per-boot]].
