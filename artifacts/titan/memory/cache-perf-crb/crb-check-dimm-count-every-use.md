---
name: crb-check-dimm-count-every-use
description: "Standing instruction: at the start of every CRB session, check the memory module count (must be 12) and the memory speed, and report it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 405492c8-bb52-418d-ab08-c4ac8ac9980e
  modified: 2026-11-18T04:18:11.756Z
---

Each time CRB (192.168.2.45) is used, check the memory module count first. Expected: 12 modules at 7200 MT/s.

Commands:
- `grep MemTotal /proc/meminfo` (12 modules: about 395392808 kB; 10 modules: about 329 million kB; needs no sudo)
- `sudo dmesg | grep "DIMM sockets"` (prints 12 or 10)
- `sudo dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c` (speed; sudo use needs the user's approval for the task)
- Speed without sudo (used on 2026-11-17): `cat /proc/sys/kernel/random/boot_id` and compare with a boot whose speed is on record. `crb/results/dimm7200-20261117/try6.txt` records boot id 3bfc57a1-e235-4fe5-8c09-a94642f9b60b with 12 x "Configured Memory Speed: 7200 MT/s". An equal boot id proves the same boot; state the limit "speed not read during the run". After any reboot this proof is gone, and the speed needs sudo again.

**Why:** the user said on 2026-11-17: "each time we use CRB, check DIMM count". The DIMM problem is regarded as fixed since the change to 7200 MT/s on 2026-11-17 (6 of 6 boots with 12 modules), unless it comes back. A boot with 10 modules lowers whole-chip read rates by up to 23 % and makes comparisons invalid. See [[crb-memory-module-count-varies-per-boot]].

**How to apply:** do the check in the first ssh command of a session and after every reboot. State the count with every CRB performance report. If the count is not 12, or the speed is not 7200 MT/s, stop and tell the user before running tests; also add the boot to `~/workspace/machines/arm-crb/DIMM-flaky-report.md` as new evidence (my interpretation of the follow-up, not the user's words).
