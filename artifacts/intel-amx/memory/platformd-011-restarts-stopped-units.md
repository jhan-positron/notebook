---
name: platformd-011-restarts-stopped-units
description: "platformd 0.11 (delphi-3bda since 2026-09-21) restarts rinzler@N units stopped with systemctl within about a minute; whole-machine takeovers must go through POST /api/inference/down (lib-guard.sh rinzler_stop_serving, 2026-09-22); the agent session's classifier denies campaign launches on 3bda ('Modify Shared Resources'), jhan launches by hand"
metadata:
  type: project
  originSessionId: d431f4bb-1f10-45d3-99fe-097238cabbde
---

Observed 2026-09-22 16:36 UTC: lib-guard.sh rinzler_takeover_if_idle stopped rinzler@0..3 with `systemctl stop`; platformd
0.11 re-added the engines at 16:37:08 ("inference Adding server engine=default-0 ... Waiting for external health check"),
the q4b-rt8u campaign's watcher saw the units active and stopped our runtron run (WATCH-STOP), then the 6-hour "someone
started them" latch blocked every later takeover.

Fix (same day): lib-guard.sh rinzler_stop_serving() = when `curl -s -m 5 http://localhost:8080/api/inference/status`
answers, `POST /api/inference/down` and wait <= 180 s for every unit to leave active; else the old systemctl stop.
GUARD_STOP_VIA names the path in the failure message (the test test-takeover.sh expects "systemctl stop returned nonzero").
Backup lib-guard.sh.bak-20260922. Tests: lib-guard-tests/test-takeover.sh 45 pass, test-wait-clear.sh 6 pass.
dut.sh serving-down/serving-up (exec/q4b-fpga-20260921/) already used the platformd API and were never affected.

**Why:** platformd 0.11 supervises engines explicitly (named engines default-N); stopping a unit behind its back is undone.
**How to apply:** any whole-machine takeover or "stop serving" step on 3bda goes through platformd's API; bring production
back with POST /api/inference/up (dut.sh serving-up). Also: the auto-mode classifier denied `ssh delphi-3bda ... nohup bash
campaign.sh &` launches at 16:4x UTC ("Modify Shared Resources") although the 07:00 UTC launch had been allowed; when denied,
hand jhan the exact one-line command for `! ssh ...`. Related: [[3bda-nightly-rinzler-cleanup]], [[q4b-fpga-20260921-campaign]].
