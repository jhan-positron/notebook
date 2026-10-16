---
name: delphi-3bda-hardware
description: "Measured hardware facts for delphi-3bda (Xeon 6 6962P test server), incl. AMX quirks"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-08-16T19:34:07.511Z
---

delphi-3bda (ssh as jhan@, NOT root@), measured 2026-08-16:
2× Intel Xeon 6962P (Granite Rapids), 72 P-cores/socket, HT on (288 CPUs), max 4.4 GHz,
L2 2MB/core, L3 432MB/socket, 2 NUMA nodes (SNC off), ~1.5TB DDR5-6400 (≈614 GB/s/socket
theoretical at 12ch), 512×1GB hugepages, kernel 6.8.0-124, governor=performance.
AMX: amx_tile/amx_bf16/amx_int8 in cpuinfo; AMX-FP16 supported per CPUID(7,1).EAX[21]=1 but
deliberately HIDDEN from /proc/cpuinfo (empty display name in kernel cpufeatures.h) — detect
via raw CPUID. AMX-COMPLEX=0. Palette 1: 8 tiles ×1KB (16 rows×64B), TMUL maxK=16 maxN=64.
Machine runs nightly CI and can carry heavy load (seen loadavg 125) — check `uptime` before
perf runs; only light tasks during CI window. Related: [[amx-tron-softattn-project]].

CROSS-SESSION LOCK (adopted 2026-08-19, from trace-sync-points session): before launching a
campaign on 3bda, flock /var/tmp/jhan/3bda-campaign.lock (file exists since Aug 17) + launch
guard (no runtron running, no campaign root younger than 3 min). That session's quoted CI
window (02:30-11:30 UTC) does NOT match jhan's confirmed schedule (prep 03:30Z, done ~09:30Z);
jhan's schedule is authoritative - discrepancy flagged to them.

CI-BUSY DETECTION (AUTHORITATIVE 2026-08-19, Rhys systems_test PR #180): DUT lease file
/run/lock/systems-test-ci.lease - busy ONLY if exists AND state=="busy" AND now <
expires_at_epoch; else CI not holding (rinzler/hugepage cleanup + FPGA claiming allowed).
Clock windows now ADVISORY only. Use exec/lib-guard.sh (campaign_guard_acquire = lease +
flock + no-runtron; ci_took_dut between runs; wait_for_ci_release). Lease format: verify
against a real nightly file (parser handles JSON + key=value). Peer sessions informed.

RINZLER POLICY NUANCE (2026-08-19 evening): the trace-sync-points peakbw harness legitimately
RESTORES live rinzler serving after its campaigns (stop-and-restore design). jhan's
never-restart rule governs OUR post-CI cleanup of lingering rinzlers, not their restore path.
slice-*-of-8 hugepage files = rinzler working files when serving is active (mapped, leave
them); only remove fuser-clean ones with serving down. lib-guard.sh v3: guard refuses next to
active serving unless --allow-serving (script must implement stop-and-restore); dynamic-fd
flock (v2, fd-9 collision fix).

SERVING CONFIG FACT (from trace-sync-points, 2026-08-19): normal production serving =
rinzler@0..3 (4 systemd instances/processes) serving a TRIO of models verified via /v1/models
(llama-3.2-3b-fast, llama-3.1-8b-good, llama-3.3-70b-good), mapping 8 slice-*-of-8 hugepage
files. "4 processes / 3 models / 8 slices" is the intended healthy state - do not read the
4-vs-3 mismatch as a bug.

Lease-format verification status (2026-08-20): 04:00Z capture = file ABSENT (parser
correctly not-busy; fail-open case verified). BUSY format still unverified - either CI did
not start by then or the lease writer (Rhys PR #180) is not deployed yet. Poller re-armed
for the 2026-08-20 window; if it never appears, ask Rhys whether the writer is live before
trusting lease-based scheduling.

SSH access (2026-08-20): agent-based auth is GONE (23 ssh-agents killed during pid-exhaustion
mitigation in claude-box; agent-held forwarded keys unrecoverable). Access now via
~/.ssh/config Host delphi-3bda -> User jhan + local id_ed25519 key file (verified working).
Plain `ssh delphi-3bda` works again for all sessions in the container.
