---
name: 3bda-platformd-sst-dev-build-2026-10-07
description: delphi-3bda runs John Mark Wilkinson's unmerged platformd dev build 0.11.0+sst.88b2d3da (PR 570) since 2026-10-07 18:44 UTC, installed with jhan's permission; his Oct 8 helper run switched Speed Select core-power from disabled to enabled/ordered between the 10-08 and 10-09 nightlies
metadata:
  type: project
---

Checked 2026-10-13 after Rhys asked whether jhan upgraded "platform version 0.11.0+sst.88b2d3da" on Oct 7. jhan and Claude did not.

- Who/when: John Mark Wilkinson (platformd maintainer) asked jhan by Slack DM on 2026-10-07 11:16 PDT for an Intel machine; jhan handed over delphi-3bda at 11:23 PDT ("All yours") and John Mark said he was done at 15:30 PDT. He worked as user `positron` via non-interactive ssh from 192.168.2.213 with his RSA key `jwilkinson@jmw-l` (auth.log; no pts login, so `last` shows nothing). Install command at 18:44:26 UTC: `apt-get --allow-downgrades --reinstall install -y /tmp/platformd_0.11.0+sst.88b2d3da_amd64.deb` (apt history, Requested-By positron). Full bringup forced at 18:47:46 (bringup-done moved away), restart 18:57:23; platformd has run that build since.
- Build: commit 88b2d3da = branch `jm-intel-speed-select-quirk`, PR positron-ai/platformd#570 "Apply Intel Speed Select during first-boot bringup", open and not on main as of 2026-10-13. Not in the apt repo: `apt-get -s upgrade` keeps platformd back, so the nightly's `apt-get upgrade -y` will not replace it. Prior version was 0.11.0 (testing channel).
- Follow-ups by the same key: 2026-10-08 21:56:47 UTC installed `/usr/bin/positron-intel-speed-select` and ran it (high list 112 cores, low list 48 cores). Before/after captures in /tmp/platformd-sst-core-power-20261008 show core-power enable-status disabled -> enabled and priority proportional -> ordered on all 6 domains; CLOS configs and the 224/64 associations unchanged and equal to jhan's September policy. 2026-10-09 17:57-17:58 UTC re-installed the helper and /etc/sudoers.d/platformd-intel-speed-select (no SST state change, per his remote-results.json). Verified 2026-10-13 17:06 UTC: still enabled/ordered, associations still 224/64.
- Before all of this (2026-10-07 18:39 UTC capture) core-power was disabled: jhan's boot script issues `core-power disable` by design (July finding: the enable bit is hygiene only, CLOS caps stay enforced).

**Why:** the enable/ordered switch at 2026-10-08 21:56 UTC is the only known machine-state change between the normal 10-08 nightly and the regressed 10-09 nightly (TTFT-only, see [[ci-amx-regression-20261009]]); the pending A/B there should include an SST core-power disable/enable arm.

**How to apply:** when a nightly report shows an unexpected platformd version, read /var/log/apt/history.log (Requested-By) and the sudo lines in auth.log; positron-account work with key jwilkinson@jmw-l is John Mark. Do not uninstall his build without asking him. Related: [[platformd-amx-sst-brief-2026-10-05]], [[3bda-ci-amx-shape-models-2026-09-18]].
