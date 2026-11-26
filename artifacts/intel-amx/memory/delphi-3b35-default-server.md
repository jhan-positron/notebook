---
name: delphi-3b35-default-server
description: "delphi-3b35 = default AMX test server since 2026-11-12 (jhan); rules, measured differences vs delphi-3bda (no TSX, no flat-freq service, C6 on, no sudo), copied tooling, traps"
metadata:
  node_type: memory
  type: project
  originSessionId: 8b11d4b6-1ed4-4d16-bdbe-73ebcb291d84
  modified: 2026-11-13T05:46:01.878Z
---

jhan, 2026-11-12 (input-2-ai/delphi-3b35.md): the default Atlas server is delphi-3b35.
Do not use delphi-3bda unless jhan names it. ~/.claude/CLAUDE.md "machine" section was
rewritten the same day (backup CLAUDE.md.bak-20261112).

RULES (jhan's words, restated):
- 3b35 is NOT a CI machine: tests may run at any time on our 4 FPGA cards. No lease check.
- We hold the 2nd half of the cards: SYSTEM_CONFIG="--instance 1,2" (in ~/delphi-3b35-setup.sh,
  printed by a non-interactive ssh too). Verified from tron source + resource-map.yaml
  (server type granite_rapids_6962p on both hosts): slices 4-7 = cards 90:00.0 93:00.0 b9:00.0
  bc:00.0, app CPUs 96-143,223-230, driver CPUs 75-78, node 1, files slice-4..7-of-8.
- Linux is shared. Brian Hamon (account bhamon; his server runs as uid disagg 992) has the
  first half. Before EVERY perf test measure load and put it in the report:
  `ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh'`
  (12 s, no root; per-socket busy %, per-user CPUs, FPGA cards open, hugepages).
  Load average alone is useless there: it reads a flat 31.00 = his 31 spin-waiting threads.
- Driving model unchanged: agent on a Linux server (agentsrv), `ssh delphi-3b35` (Host entry
  added to ~/.ssh/config in claude-box 2026-11-12, user jhan, id_ed25519).

MEASURED 2026-11-13 05:3x UTC, 3b35 vs 3bda (raw files exec/3b35-inspect-20261112/, page
delphi-3b35-vs-3bda.html there). Same: 2x Xeon 6962P stepping 1, 288 CPUs, NUMA/SNC layout,
caches, 24x64 GB DDR5-6400 (17 of 24 DIMM speeds readable on 3b35), 512x1G hugepages, governor,
EPP/EPB, RAPL 500/600 W, uncore limits, AMX CPUID bits and tile palette, kernel config.
DIFFERENT and able to change AMX numbers:
1. TSX off on 3b35 (no tsx=on in cmdline or grub.cfg; rtm/hle flags absent). tron
   src/system/mwaitx.cpp:76 warns the non-RTM wait fallback "costs 13-30% decode" (source
   comment, not our measurement). Hits AMX-on and AMX-off arms.
2. No flat-frequency service on 3b35 (no intel-speed-select binary/unit; platformd 0.10.7 vs
   0.11.3). Busy CPUs there read exactly 2700 MHz; on 3bda fast-range CPUs read 3600-4100 MHz.
   SST class readback on 3b35 needs root (hypothesis: BIOS boot-default clamp). July work on
   3bda measured prefill +16-18 %, decode +5-8 % from the fix.
3. C6/C6P idle states enabled on 3b35 (driver default_status enabled), disabled on 3bda.
4. BIOS 92011800 (1.18, 2026-06-01) vs 92011500 (1.15, 2026-03-27); microcode 0x1000423
   (BIOS-loaded) vs 0x1000405. Effect not measured.
5. Kernel 6.8.0-136 vs -138: changelog has only CVE fixes (net/sctp/KVM/eventpoll/RDMA);
   next boot of 3b35 = -138, still without tsx=on.
OPERATIONAL differences:
- jhan has NO root sudo on 3b35 (only `(disagg) NOPASSWD`). So no perf (paranoid=4), turbostat,
  intel-speed-select, prlimit memlock raise (limit 188.8 GiB), apt, systemctl. ~100 of 462
  exec scripts call sudo. numactl, cpuid, rdmsr not installed.
- 7 FPGA cards only: 3b:00.0 (first half) absent, so a whole-machine `--instance 0,1` probably
  fails (not tested).
- Brian's rinzler has affinity mask 27-34,75-82: 12 idle threads may sit on OUR driver CPUs
  75-78. Check section 4 of the load snapshot.
- /dev/hugepages/slice-4..7-of-8 exist, owner bhamon, 4 GiB each, stale since 2026-10-23, group
  positron rw. tron would open + flock + ftruncate them (source reading; not run). Ask Brian
  before the first run.
- Installed tron package on 3b35 is 2026-08-17 (no AMX kernels); use our own builds only.
- lib-guard.sh: lock name still /var/tmp/jhan/3bda-campaign.lock; other_user_active skips
  uid < 1000 so it cannot see the disagg server; rinzler takeover block must never run on 3b35.
  ~/delphi-3b35-setup.sh has no GUARD_EXCLUDE_USERS / GUARD_RUNTRON_USER yet (not edited).

COPIED 2026-11-13 to 3b35:/var/tmp/jhan (2.0 GB): seed-traces/b47f (188M, newest ingest/traces,
17 models), seed-traces/pr4 (199M), st-venv + uv-python (same absolute paths, python 3.12.13
runs), from-3bda/ (44M: top-level bench sources/configs + qkbench pfbench perf-model-bin blk
amx-tile-const amx-tile-names memorder; rebuild binaries before timing).
NOT copied on purpose: /var/tmp/jhan/tron-* (1.3 TiB build worktrees), old campaign data
(td, ef-inv, dd ...), locks/marks, Bill marker.
TRAP: 98 worktrees of the shared ~/workspace/tron/.git point at 3bda-local /var/tmp/jhan/tron-*;
from 3b35 they all look prunable. Never `git worktree prune` (see [[worktree-prune-nfs-trap]]),
and create 3b35 worktrees under NEW names (e.g. /var/tmp/jhan/b35-<name>).

Related: [[delphi-3bda-hardware]], [[3bda-shared-with-bill]].
